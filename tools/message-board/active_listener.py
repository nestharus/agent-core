"""One active-turn, event-driven local wait for durable swarm outbox notices."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import sqlite3
import sys
import time


class ListenerError(Exception):
    """A watcher cannot safely continue."""


MAX_RECHECK_SECONDS = 2.0


def _linux() -> None:
    if sys.platform != "linux" or not hasattr(socket, "AF_UNIX"):
        raise ListenerError("active watch requires Linux Unix sockets")


def _db_path(conn: sqlite3.Connection) -> Path:
    rows = conn.execute("PRAGMA database_list").fetchall()
    paths = [row[2] for row in rows if row[1] == "main"]
    if len(paths) != 1 or not paths[0]:
        raise ListenerError("active watch requires a file-backed board")
    return Path(paths[0])


def _db_identity(conn: sqlite3.Connection) -> bytes:
    path = _db_path(conn)
    try:
        resolved = path.resolve(strict=True)
        st = resolved.stat()
    except OSError as exc:
        raise ListenerError("board identity is unavailable") from exc
    identity = f"{resolved}\0{st.st_dev}\0{st.st_ino}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest().encode("ascii")


def _address(session: str, identity: bytes) -> bytes:
    """One local watcher address per session *and* SQLite board identity."""
    digest = hashlib.sha256(session.encode("ascii") + b"\0" + identity).hexdigest()[:32]
    return f"\0message-board-watch-v1-{os.getuid()}-{digest}".encode("ascii")


def _packet(identity: bytes) -> bytes:
    return b"MESSAGE-BOARD-WATCH/1:" + identity


def _pending(conn: sqlite3.Connection, session: str, limit: int) -> list[dict]:
    rows = conn.execute("""
        SELECT notification_id, thread_id, post_seq, event, title
        FROM notification_outbox
        WHERE recipient=? AND delivery_state!='acknowledged'
          AND recipient IN (SELECT session FROM sessions WHERE status='active')
        ORDER BY notification_id LIMIT ?
    """, (session, limit)).fetchall()
    return [dict(row) for row in rows]


def signal_post(conn: sqlite3.Connection, post_seq: int) -> None:
    """Best-effort hint after commit. Delivery and content remain in SQLite."""
    try:
        _linux()
        identity = _db_identity(conn)
        recipients = [row[0] for row in conn.execute(
            "SELECT recipient FROM notification_outbox WHERE post_seq=?", (post_seq,))]
    except (ListenerError, sqlite3.Error, OSError):
        # The post and its outbox already committed. Losing this optional hint
        # must not make open/reply report an error for a successful write.
        return
    if not recipients:
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
            for recipient in recipients:
                try:
                    sender.sendto(_packet(identity), _address(recipient, identity))
                except OSError:
                    # A missing/full watcher loses only this hint. Its next
                    # board check finds the committed outbox row.
                    pass
    except OSError:
        # Socket construction/close may fail after the post committed. This
        # optional hint must never change the reported write outcome.
        return


def watch(conn: sqlite3.Connection, session: str, timeout: int, limit: int) -> list[dict]:
    """Block in one caller-owned tool turn; return on durable notice or timeout."""
    _linux()
    if timeout < 1 or timeout > 86400:
        raise ListenerError("watch timeout must be between 1 and 86400 seconds")
    expected_identity = _db_identity(conn)
    expected_packet = _packet(expected_identity)
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
        try:
            receiver.bind(_address(session, expected_identity))
        except OSError as exc:
            raise ListenerError("session already has a watcher or socket bind failed") from exc
        # Binding first closes the commit-versus-watch race.
        if _db_identity(conn) != expected_identity:
            raise ListenerError("board identity changed while binding")
        pending = _pending(conn, session, limit)
        if pending:
            return pending
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                if _db_identity(conn) != expected_identity:
                    raise ListenerError("board identity changed while watching")
                return _pending(conn, session, limit)
            receiver.settimeout(min(remaining, MAX_RECHECK_SECONDS))
            try:
                data = receiver.recv(256)
            except socket.timeout:
                if _db_identity(conn) != expected_identity:
                    raise ListenerError("board identity changed while watching")
                # The socket is a hint. Recheck the durable outbox at a
                # bounded interval even when the caller requested a long wait.
                pending = _pending(conn, session, limit)
                if pending:
                    return pending
                continue
            except InterruptedError as exc:
                raise ListenerError("watch interrupted") from exc
            if data != expected_packet:
                raise ListenerError("malformed or wrong-board local signal")
            if _db_identity(conn) != expected_identity:
                raise ListenerError("board identity changed while watching")
            pending = _pending(conn, session, limit)
            if pending:
                return pending
