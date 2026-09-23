"""One session's durable notice feed across explicitly selected shared boards."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import selectors
import socket
import sqlite3
import time

import active_listener
import board_store
import catalog


class WatchError(Exception):
    """The selected feed cannot be trusted to continue."""


RECHECK_SECONDS = 2.0


class BoardFeed:
    def __init__(self, home: Path, session: str, keys: list[str] | None = None,
                 *, all_joined: bool = False, limit: int = 100,
                 include_details: bool = False):
        active_listener._linux()
        self.home = home
        self.session = board_store.acting_session(session)
        if bool(keys) == all_joined:
            raise WatchError("select --board at least once or --all-joined")
        if limit < 1 or limit > board_store.MAX_LIMIT:
            raise WatchError("invalid notice limit")
        self.keys = keys or []
        self.all_joined = all_joined
        self.limit = limit
        self.include_details = include_details
        self.stack = ExitStack()
        self.selector = selectors.DefaultSelector()
        self.boards: list[dict] = []

    def __enter__(self):
        try:
            with catalog.catalog(self.home) as db:
                if self.all_joined:
                    entries = [dict(row) for row in db.execute(
                        "SELECT * FROM boards WHERE state='active' ORDER BY board_id")]
                else:
                    entries = [catalog.board(db, key) for key in self.keys]
            ids = [entry["board_id"] for entry in entries]
            if len(ids) != len(set(ids)):
                raise WatchError("board selected more than once")
            # Every selected listener is bound before the caller scans any outbox.
            for entry in entries:
                board = self._open(entry, optional_member=self.all_joined)
                if board is not None:
                    self.boards.append(board)
            if not self.boards:
                raise WatchError("no active joined boards")
            return self
        except BaseException:
            self.close()
            raise

    def _open(self, entry: dict, *, optional_member: bool) -> dict | None:
        if entry["state"] != "active":
            raise WatchError(f"board {entry['board_id']} is not active")
        path = Path(entry["db_path"])
        if not path.is_file() or path.is_symlink():
            raise WatchError(f"board {entry['board_id']} file missing or replaced")
        conn = None
        installed = False
        try:
            conn = sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro",
                                   uri=True, timeout=2, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            # A schema-3 board in an older catalog may be unrelated to this
            # session. Membership is a raw legacy table, so check it before
            # demanding schema-4 or binding metadata from that board.
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == 3:
                member = conn.execute("SELECT status FROM sessions WHERE session=?",
                                      (self.session,)).fetchone()
            else:
                member = conn.execute("SELECT status,expires_at FROM sessions WHERE session=?",
                                      (self.session,)).fetchone()
            if member is None or member["status"] != "active" or (version != 3 and
                    member["expires_at"] and member["expires_at"] <= board_store.utc_now()):
                if optional_member:
                    conn.close()
                    return None
                raise WatchError(f"session is not an active unexpired member of {entry['board_id']}")
            if version != board_store.SCHEMA_VERSION:
                raise WatchError(f"board {entry['board_id']} requires migration")
            rows = conn.execute("SELECT board_id FROM board_meta").fetchall()
            if len(rows) != 1 or rows[0][0] != entry["board_id"]:
                raise WatchError(f"board {entry['board_id']} ID binding failed")
            identity = active_listener._db_identity(conn)
            receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            try:
                receiver.bind(active_listener._address(self.session, identity))
                receiver.setblocking(False)
            except OSError as exc:
                receiver.close()
                raise WatchError(f"listener conflict for {entry['board_id']}") from exc
            board = {"entry": entry, "conn": conn, "identity": identity,
                     "receiver": receiver, "cursor": 0}
            self.stack.callback(receiver.close)
            self.stack.callback(conn.close)
            self.selector.register(receiver, selectors.EVENT_READ, board)
            installed = True
            return board
        except (sqlite3.Error, OSError, active_listener.ListenerError) as exc:
            raise WatchError(f"cannot open board {entry['board_id']}: {exc}") from exc
        finally:
            if not installed and conn is not None:
                conn.close()

    def _check(self, board: dict) -> None:
        entry = board["entry"]
        ident = entry["board_id"]
        try:
            with catalog.lifecycle_lock(entry, self.home, exclusive=False):
                with catalog.catalog(self.home) as db:
                    current = catalog.board(db, ident)
                if current["state"] != "active":
                    raise WatchError(f"board {ident} is no longer active")
                if current["db_path"] != entry["db_path"]:
                    raise WatchError(f"board {ident} path changed")
                conn = board["conn"]
                if active_listener._db_identity(conn) != board["identity"]:
                    raise WatchError(f"board {ident} file changed")
                rows = conn.execute("SELECT board_id FROM board_meta").fetchall()
                if len(rows) != 1 or rows[0][0] != ident:
                    raise WatchError(f"board {ident} ID binding changed")
                board_store.require_active_session(conn, self.session)
        except (catalog.CatalogError, board_store.UserError, active_listener.ListenerError,
                sqlite3.Error, OSError) as exc:
            raise WatchError(f"board {ident} is unavailable: {exc}") from exc

    def scan(self) -> list[dict]:
        notices = []
        for board in self.boards:
            self._check(board)
            try:
                rows = board["conn"].execute("""
                    SELECT notification_id,thread_id,post_seq,event,title FROM notification_outbox
                    WHERE recipient=? AND notification_id>? AND delivery_state!='acknowledged'
                    ORDER BY notification_id LIMIT ?
                """, (self.session, board["cursor"], self.limit)).fetchall()
            except sqlite3.Error as exc:
                raise WatchError(f"board {board['entry']['board_id']} outbox failed") from exc
            # A transition or membership change during the read must suppress wake.
            self._check(board)
            for row in rows:
                notice = {"board_id": board["entry"]["board_id"],
                          "notification_id": row["notification_id"],
                          "thread_id": row["thread_id"], "post_seq": row["post_seq"]}
                if self.include_details:
                    notice.update(event=row["event"], title=row["title"])
                notices.append(notice)
            if rows:
                board["cursor"] = rows[-1]["notification_id"]
        return notices

    def wait(self, timeout: float) -> list[dict]:
        if timeout < 0:
            raise WatchError("negative timeout")
        deadline = time.monotonic() + timeout
        while True:
            found = self.scan()
            if found:
                return found
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return []
            for key, _ in self.selector.select(min(remaining, RECHECK_SECONDS)):
                board = key.data
                try:
                    packet = board["receiver"].recv(256)
                except OSError as exc:
                    raise WatchError("listener read failed") from exc
                if packet != active_listener._packet(board["identity"]):
                    raise WatchError("malformed or wrong-board socket hint")

    def close(self) -> None:
        self.selector.close()
        self.stack.close()

    def __exit__(self, *_):
        self.close()
