#!/usr/bin/env python3
"""Shared local message-board CLI. Content commands require --board UUID or alias."""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import uuid

import active_listener
import board_store
import catalog as cat
import multi_board_watch


CONTENT_WHEN_RETIRED = frozenset({"read", "thread", "thread-read", "threads", "search", "inbox",
                                  "notifications", "deliveries", "attempts", "sessions",
                                  "membership-events", "scope-transfers", "profile-changes", "ack", "ack-notice",
                                  "recover", "leave", "heartbeat"})
CONTENT_WHEN_ARCHIVED = frozenset({"read", "thread", "thread-read", "threads", "search", "inbox",
                                   "notifications", "deliveries", "attempts", "sessions",
                                   "membership-events", "scope-transfers", "profile-changes"})


def _readonly(path: str, *, immutable: bool = False):
    if not Path(path).is_file():
        raise cat.CatalogError("board database file is missing")
    suffix = "?mode=ro&immutable=1" if immutable else "?mode=ro"
    return sqlite3.connect(Path(path).resolve().as_uri() + suffix, uri=True)


def _schema(path: str, *, immutable: bool = False) -> int:
    with closing(_readonly(path, immutable=immutable)) as db:
        return db.execute("PRAGMA user_version").fetchone()[0]


def _identity(path: str, board_id: str, *, immutable: bool = False) -> None:
    with closing(_readonly(path, immutable=immutable)) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='board_meta'").fetchone() is None:
            raise cat.CatalogError("board database lacks embedded ID; run boards migrate")
        rows = db.execute("SELECT board_id FROM board_meta").fetchall()
        if len(rows) != 1 or rows[0][0] != board_id:
            raise cat.CatalogError("board database ID does not match catalog")


def _counts(db: sqlite3.Connection) -> dict[str, int]:
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("sessions", "posts", "threads", "thread_posts", "subscriptions",
                          "attachments", "notification_outbox", "notification_attempts",
                          "membership_events", "scope_transfers")
            if table in names}


def _fingerprints(source: sqlite3.Connection, candidate: sqlite3.Connection) -> bool:
    """Compare every preexisting data column and row across a migration."""
    for table in _counts(source):
        columns = [row[1] for row in source.execute(f"PRAGMA table_info({table})")]
        selected = ",".join('"' + name.replace('"', '""') + '"' for name in columns)
        statement = f"SELECT {selected} FROM {table} ORDER BY rowid"
        old_rows = source.execute(statement)
        new_rows = candidate.execute(statement)
        while True:
            old_row = old_rows.fetchone()
            new_row = new_rows.fetchone()
            if old_row is None or new_row is None:
                if old_row != new_row:
                    return False
                break
            if tuple(old_row) != tuple(new_row):
                return False
    return True


def _snapshot(source: str, destination: Path) -> tuple[str, dict[str, int]]:
    if destination.exists():
        raise cat.CatalogError("snapshot path already exists")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".board-snapshot-", suffix=".sqlite3", dir=destination.parent)
    os.close(fd)
    try:
        with closing(_readonly(source)) as original, closing(sqlite3.connect(temporary)) as copy:
            original.backup(copy)
            if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise cat.CatalogError("snapshot integrity check failed")
            if copy.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise cat.CatalogError("snapshot foreign key check failed")
            original_counts = _counts(original)
            copy_counts = _counts(copy)
            if original_counts != copy_counts:
                raise cat.CatalogError("snapshot row counts differ from source")
        with Path(temporary).open("rb") as snapshot:
            digest = hashlib.file_digest(snapshot, "sha256").hexdigest()
        os.replace(temporary, destination)
        return digest, copy_counts
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def _owner_active(path: str) -> bool:
    with closing(_readonly(path)) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
        if "owner" in columns:
            return db.execute("SELECT 1 FROM sessions WHERE owner=1 AND status='active' "
                              "LIMIT 1").fetchone() is not None
        return False


def _unresolved(path: str) -> list[tuple[int, str]]:
    with closing(_readonly(path)) as source:
        return [(row[0], row[1]) for row in source.execute(
            "SELECT notification_id,delivery_state FROM notification_outbox "
            "WHERE delivery_state!='acknowledged' ORDER BY notification_id")]


def _require_settled(db: sqlite3.Connection, entry: dict) -> None:
    pending = _unresolved(entry["db_path"])
    covered = {row[0] for row in db.execute(
        "SELECT notification_id FROM notice_dispositions WHERE board_id=?", (entry["board_id"],))}
    missing = [ident for ident, _ in pending if ident not in covered]
    if missing:
        raise cat.CatalogError(f"unresolved notices require acknowledgment or explicit disposition: {missing}")


def _verify_snapshot(entry: dict) -> None:
    path = Path(entry["snapshot_path"] or "")
    if not path.is_file() or not entry["snapshot_sha256"]:
        raise cat.CatalogError("archive snapshot or hash is missing")
    with path.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != entry["snapshot_sha256"]:
        raise cat.CatalogError("archive snapshot hash mismatch")


def _verify_backup(entry: dict) -> Path:
    backup = Path(entry["migration_backup"] or "")
    if not backup.is_file() or not entry["migration_sha256"]:
        raise cat.CatalogError("recorded migration backup is missing")
    with backup.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != entry["migration_sha256"] or _schema(str(backup), immutable=True) != 3:
        raise cat.CatalogError("recorded migration backup is invalid")
    return backup


def _board_args(argv: list[str]):
    p = argparse.ArgumentParser(prog="board boards")
    sub = p.add_subparsers(dest="action", required=True)
    c = sub.add_parser("create")
    c.add_argument("--alias", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--temporary-test", action="store_true")
    c.add_argument("--membership", choices=("open", "invited"), default="open")
    c.add_argument("--routes", choices=("both", "queue", "managed"), default="both")
    c = sub.add_parser("register-path", help="catalog an existing database without SQLite writes")
    c.add_argument("--alias", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--db", required=True)
    c.add_argument("--id", help="existing embedded UUID for a schema-4 database")
    c.add_argument("--membership", choices=("open", "invited"), default="open")
    c.add_argument("--routes", choices=("both", "queue", "managed"), default="both")
    c = sub.add_parser("list")
    c.add_argument("--state", choices=cat.STATES)
    c.add_argument("--artifact-type", choices=sorted(cat.ARTIFACT_TYPES))
    c.add_argument("--artifact")
    c.add_argument("--session")
    c = sub.add_parser("show")
    c.add_argument("--board", required=True)
    c.add_argument("--session")
    for action in ("associate", "disassociate"):
        c = sub.add_parser(action)
        c.add_argument("--board", required=True)
        c.add_argument("--type", required=True, choices=sorted(cat.ARTIFACT_TYPES))
        c.add_argument("--id", required=True)
    for action in ("retire", "archive"):
        c = sub.add_parser(action)
        c.add_argument("--board", required=True)
    c = sub.add_parser("dispose-notices", help="record unresolved notice IDs and reason without acknowledging")
    c.add_argument("--board", required=True)
    c.add_argument("--notice-id", type=board_store.positive, action="append", required=True)
    c.add_argument("--reason", required=True)
    c = sub.add_parser("purge")
    c.add_argument("--board", required=True)
    c.add_argument("--confirm-id", required=True)
    c.add_argument("--irreversible", action="store_true", required=True)
    c = sub.add_parser("migrate")
    c.add_argument("--board", required=True)
    mode = c.add_mutually_exclusive_group(required=True)
    mode.add_argument("--backup", help="new SQLite backup path outside the board file")
    mode.add_argument("--resume", action="store_true", help="resume a staged migration")
    c = sub.add_parser("migrate-rollback", help="restore the recorded schema-3 backup")
    c.add_argument("--board", required=True)
    c = sub.add_parser("hold")
    c.add_argument("--board", required=True)
    c.add_argument("--enabled", choices=("yes", "no"), required=True)
    c = sub.add_parser("invite")
    c.add_argument("--board", required=True)
    c.add_argument("--session", required=True)
    for action in sub.choices.values():
        action.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def _member(path: str, session: str, *, immutable: bool = False) -> dict | None:
    with closing(_readonly(path, immutable=immutable)) as db:
        db.row_factory = sqlite3.Row
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='sessions'").fetchone() is None:
            return None
        row = db.execute("SELECT * FROM sessions WHERE session=?", (session,)).fetchone()
        return dict(row) if row else None


def _format(result, json_output: bool):
    if json_output:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    elif isinstance(result, list):
        for row in result:
            print(f"{row['board_id']} {row['alias']} {row['state']} {row['display_name']}")
    else:
        print(f"{result['board_id']} {result['alias']} {result['state']} {result['display_name']}")


def boards(argv: list[str], home: Path) -> int:
    args = _board_args(argv)
    if args.action == "list" and not (home / "catalog.sqlite3").exists():
        if home.exists() and home.stat().st_mode & 0o077:
            raise cat.CatalogError("board home must be private; choose a dedicated directory with mode 700")
        if bool(args.artifact_type) != bool(args.artifact):
            raise cat.CatalogError("artifact type and identifier must be supplied together")
        if args.artifact_type:
            cat.artifact_identifier(args.artifact_type, args.artifact)
        if args.session:
            board_store.session_uuid(args.session)
        _format([], args.json)
        return 0
    with cat.catalog(home) as db:
        if args.action in ("create", "register-path"):
            if args.action == "create":
                board_id = str(uuid.uuid4())
                path = home / "boards" / f"{board_id}.sqlite3"
                if path.exists():
                    raise cat.CatalogError("new board database path already exists")
                try:
                    with board_store.database(str(path)) as board_db:
                        board_store.bind_board(board_db, board_id, initialize=True)
                    entry = cat.create(db, home, args.alias, args.name, db_path=str(path),
                                       board_id=board_id, initialized_new_file=True,
                                       temporary_test=args.temporary_test,
                                       membership_policy=args.membership,
                                       allowed_routes="queue,managed" if args.routes == "both" else args.routes)
                except BaseException:
                    # No catalog row was published for this generated file.
                    for suffix in ("", "-wal", "-shm", ".schema.lock"):
                        Path(str(path) + suffix).unlink(missing_ok=True)
                    raise
            else:
                entry = cat.create(db, home, args.alias, args.name, db_path=args.db,
                                   board_id=args.id,
                                   membership_policy=args.membership,
                                   allowed_routes="queue,managed" if args.routes == "both" else args.routes)
            _format(entry, args.json)
            return 0
        if args.action == "list":
            if bool(args.artifact_type) != bool(args.artifact):
                raise cat.CatalogError("artifact type and identifier must be supplied together")
            query = "SELECT DISTINCT b.* FROM boards b"
            values = []
            clauses = []
            if args.artifact_type:
                query += " JOIN artifact_links l ON l.board_id=b.board_id"
                clauses += ["l.artifact_type=?", "l.identifier=?"]
                values += [args.artifact_type, cat.artifact_identifier(args.artifact_type, args.artifact)]
            if args.state:
                clauses.append("b.state=?")
                values.append(args.state)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            entries = [dict(row) for row in db.execute(query + " ORDER BY b.alias", values)]
            if args.session:
                session = board_store.session_uuid(args.session)
                joined = []
                for row in entries:
                    if row["state"] not in ("active", "retired", "archived"):
                        continue
                    archived = row["state"] == "archived"
                    if archived:
                        _verify_snapshot(row)
                    if _member(row["snapshot_path"] if archived else row["db_path"], session,
                               immutable=archived) is not None:
                        joined.append(row)
                entries = joined
            _format(entries, args.json)
            return 0
        entry = cat.board(db, args.board)
        board_id = entry["board_id"]
        if args.action == "show":
            entry["artifacts"] = cat.links(db, board_id)
            if args.session and entry["state"] in ("active", "retired", "archived"):
                if entry["state"] == "archived":
                    _verify_snapshot(entry)
                entry["membership"] = _member(
                    entry["snapshot_path"] if entry["state"] == "archived" else entry["db_path"],
                    board_store.session_uuid(args.session), immutable=entry["state"] == "archived")
            if entry["state"] in ("tombstoned", "purging"):
                entry["detail_available"] = False
            _format(entry, args.json)
            return 0
        if args.action in ("associate", "disassociate"):
            with cat.lifecycle_lock(entry, home, exclusive=True):
                cat.associate(db, board_id, args.type, args.id, remove=args.action == "disassociate")
        elif args.action == "invite":
            with cat.lifecycle_lock(entry, home, exclusive=True):
                if cat.board(db, board_id)["state"] != "active":
                    raise cat.CatalogError("only active boards accept invitations")
                session = board_store.session_uuid(args.session)
                with cat.transaction(db):
                    db.execute("INSERT OR IGNORE INTO invitations VALUES(?,?,?)", (board_id, session, cat.now()))
                    cat.record(db, board_id, "invited", session)
        elif args.action == "hold":
            with cat.lifecycle_lock(entry, home, exclusive=True):
                if cat.board(db, board_id)["state"] in ("purging", "tombstoned"):
                    raise cat.CatalogError("purging or tombstoned board cannot change holds")
                with cat.transaction(db):
                    db.execute("UPDATE boards SET retention_hold=?,changed_at=? WHERE board_id=?",
                               (int(args.enabled == "yes"), cat.now(), board_id))
                    cat.record(db, board_id, "retention_hold", args.enabled)
        elif args.action in ("retire", "archive", "purge", "migrate", "migrate-rollback", "dispose-notices"):
            with cat.lifecycle_lock(entry, home, exclusive=True):
                entry = cat.board(db, board_id)
                if args.action == "retire":
                    if entry["state"] != "active":
                        raise cat.CatalogError("only active boards can retire")
                    _require_settled(db, entry)
                    with cat.transaction(db):
                        db.execute("UPDATE boards SET state='retired',changed_at=? WHERE board_id=?",
                                   (cat.now(), board_id))
                        cat.record(db, board_id, "retired")
                elif args.action == "archive":
                    if entry["state"] != "retired":
                        raise cat.CatalogError("board must be retired before archive")
                    if _schema(entry["db_path"]) != board_store.SCHEMA_VERSION:
                        raise cat.CatalogError("legacy board must migrate before archive")
                    _identity(entry["db_path"], board_id)
                    _require_settled(db, entry)
                    if _owner_active(entry["db_path"]):
                        raise cat.CatalogError("active owner must leave before archive")
                    destination = home / "archives" / f"{board_id}.sqlite3"
                    digest, counts = _snapshot(entry["db_path"], destination)
                    try:
                        with cat.transaction(db):
                            db.execute("UPDATE boards SET state='archived',snapshot_path=?,"
                                       "snapshot_sha256=?,changed_at=? WHERE board_id=?",
                                       (str(destination), digest, cat.now(), board_id))
                            cat.record(db, board_id, "archived", json.dumps(counts, sort_keys=True))
                    except BaseException:
                        destination.unlink(missing_ok=True)
                        raise
                elif args.action == "purge":
                    if entry["state"] not in ("archived", "purging") or not entry["temporary_test"] or not entry["purge_allowed"]:
                        raise cat.CatalogError("purge is limited to archived temporary test boards")
                    if args.confirm_id != board_id:
                        raise cat.CatalogError("purge confirmation must be the exact board UUID")
                    if entry["state"] == "archived":
                        if entry["retention_hold"] or _owner_active(entry["db_path"]):
                            raise cat.CatalogError("retention hold or active owner prevents purge")
                        with cat.transaction(db):
                            db.execute("UPDATE boards SET state='purging',changed_at=? WHERE board_id=?",
                                       (cat.now(), board_id))
                            cat.record(db, board_id, "purge_started", "detail paths retained for retry")
                    for path in (entry["db_path"], entry["db_path"] + "-wal", entry["db_path"] + "-shm",
                                 entry["snapshot_path"]):
                        if path:
                            Path(path).unlink(missing_ok=True)
                    with cat.transaction(db):
                        db.execute("UPDATE boards SET state='tombstoned',snapshot_path=NULL,"
                                   "snapshot_sha256=NULL,purged_at=?,changed_at=? WHERE board_id=?",
                                   (cat.now(), cat.now(), board_id))
                        cat.record(db, board_id, "purged", "detailed evidence unavailable")
                elif args.action == "dispose-notices":
                    if entry["state"] not in ("active", "retired"):
                        raise cat.CatalogError("notice disposition requires an active or retired board")
                    reason = args.reason.strip()
                    if not reason or len(reason) > 2000:
                        raise cat.CatalogError("disposition reason must contain 1 to 2000 characters")
                    requested = args.notice_id
                    if len(requested) != len(set(requested)):
                        raise cat.CatalogError("duplicate notice ID")
                    pending = dict(_unresolved(entry["db_path"]))
                    if any(ident not in pending for ident in requested):
                        raise cat.CatalogError("disposition IDs must be currently unresolved notices")
                    with cat.transaction(db):
                        for ident in requested:
                            db.execute("INSERT INTO notice_dispositions VALUES(?,?,?,?,?) "
                                       "ON CONFLICT(board_id,notification_id) DO UPDATE SET "
                                       "delivery_state=excluded.delivery_state,reason=excluded.reason,"
                                       "recorded_at=excluded.recorded_at",
                                       (board_id, ident, pending[ident], reason, cat.now()))
                        cat.record(db, board_id, "notices_disposed", json.dumps(
                            {"ids": requested, "count": len(requested), "reason": reason}, sort_keys=True))
                elif args.action == "migrate":
                    if args.resume:
                        if entry["state"] != "migrating":
                            raise cat.CatalogError("only a staged migration can resume")
                        backup = _verify_backup(entry)
                        digest = entry["migration_sha256"]
                    else:
                        if entry["state"] != "pending_migration":
                            raise cat.CatalogError("migration requires a pending schema-3 board")
                        backup = Path(args.backup).expanduser().resolve()
                        if backup in (Path(entry["db_path"]).resolve(), home / "catalog.sqlite3"):
                            raise cat.CatalogError("backup must be separate from board and catalog")
                        digest, _ = _snapshot(entry["db_path"], backup)
                        with cat.transaction(db):
                            db.execute("UPDATE boards SET state='migrating',migration_backup=?,"
                                       "migration_sha256=?,changed_at=? WHERE board_id=?",
                                       (str(backup), digest, cat.now(), board_id))
                            cat.record(db, board_id, "migration_staged", f"backup={backup} sha256={digest}")
                    with closing(_readonly(str(backup), immutable=True)) as original:
                        if _schema(entry["db_path"]) == 3:
                            with board_store.database(entry["db_path"]) as board_db:
                                board_store.bind_board(board_db, board_id, initialize=True)
                        with closing(_readonly(entry["db_path"])) as board_db:
                            _identity(entry["db_path"], board_id)
                            if not _fingerprints(original, board_db):
                                raise cat.CatalogError("migration changed preexisting rows; backup retained")
                    with cat.transaction(db):
                        db.execute("UPDATE boards SET state='active',changed_at=? WHERE board_id=?",
                                   (cat.now(), board_id))
                        cat.record(db, board_id, "migrated", f"backup={backup} sha256={digest}")
                else:
                    if entry["state"] != "migrating":
                        raise cat.CatalogError("rollback requires a staged migration")
                    backup = _verify_backup(entry)
                    temporary = Path(entry["db_path"] + ".rollback")
                    if temporary.exists():
                        raise cat.CatalogError("rollback temporary path already exists")
                    try:
                        shutil.copy2(backup, temporary)
                        for suffix in ("-wal", "-shm"):
                            Path(entry["db_path"] + suffix).unlink(missing_ok=True)
                        os.replace(temporary, entry["db_path"])
                    finally:
                        temporary.unlink(missing_ok=True)
                    with cat.transaction(db):
                        db.execute("UPDATE boards SET state='pending_migration',changed_at=? WHERE board_id=?",
                                   (cat.now(), board_id))
                        cat.record(db, board_id, "migration_rolled_back", f"backup={backup}")
        _format(cat.board(db, board_id), args.json)
    return 0


def content(argv: list[str], home: Path, key: str | None) -> int:
    if not key:
        raise cat.CatalogError("content commands require --board UUID or alias")
    if not argv or argv[0].startswith("-"):
        raise cat.CatalogError("content command is required")
    command = argv[0]
    if "--db" in argv or "--board" in argv:
        raise cat.CatalogError("content database is resolved only from the catalog")
    with cat.catalog(home) as db:
        entry = cat.board(db, key)
    if command == "watch":
        args = board_store.parser().parse_args(argv)
        if args.timeout < 1 or args.timeout > 86400 or args.limit > board_store.MAX_LIMIT:
            raise cat.CatalogError("watch timeout or limit is out of range")
        with multi_board_watch.BoardFeed(home, args.session, [entry["board_id"]],
                                         limit=args.limit, include_details=True) as feed:
            result = feed.wait(args.timeout)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            for item in result:
                print(f"board={item['board_id']} #{item['notification_id']} {item['event']} "
                      f"thread=#{item['thread_id']} post=#{item['post_seq']} title={item['title']}")
        return 0 if result else 3
    with cat.lifecycle_lock(entry, home, exclusive=False):
        disposed_notice_ids = set()
        with cat.catalog(home) as db:
            entry = cat.board(db, entry["board_id"])
            if entry["state"] in ("purging", "tombstoned"):
                raise cat.CatalogError("board is purging or purged; detailed evidence is unavailable")
            if entry["state"] in ("pending_migration", "migrating"):
                raise cat.CatalogError("board migration is pending or staged")
            if entry["state"] == "retired" and command not in CONTENT_WHEN_RETIRED:
                raise cat.CatalogError("retired board does not accept new content, dispatch or wake")
            if entry["state"] == "archived" and command not in CONTENT_WHEN_ARCHIVED:
                raise cat.CatalogError("archived board is read-only")
            archived = entry["state"] == "archived"
            content_path = entry["snapshot_path"] if archived else entry["db_path"]
            if archived and not content_path:
                raise cat.CatalogError("archive snapshot is missing")
            if archived:
                _verify_snapshot(entry)
            if _schema(content_path, immutable=archived) < board_store.SCHEMA_VERSION:
                raise cat.CatalogError("legacy board requires explicit boards migrate before content use")
            _identity(content_path, entry["board_id"], immutable=archived)
            if command == "register":
                parsed = board_store.parser().parse_args(argv)
                existing = _member(entry["db_path"], board_store.session_uuid(parsed.session))
                selected_route = parsed.route or (existing["route"] if existing else "queue")
                if selected_route not in entry["allowed_routes"].split(","):
                    raise cat.CatalogError("member route is forbidden by board policy")
            if "queue" not in entry["allowed_routes"].split(","):
                if command == "dispatch":
                    raise cat.CatalogError("queue delivery is forbidden by board policy")
                if command in ("open", "reply"):
                    parsed = board_store.parser().parse_args(argv)
                    if not parsed.no_push:
                        raise cat.CatalogError(
                            "queue delivery is forbidden by board policy; use --no-push")
            if command in ("register", "heartbeat", "leave"):
                disposed_notice_ids = {row[0] for row in db.execute(
                    "SELECT notification_id FROM notice_dispositions WHERE board_id=?",
                    (entry["board_id"],))}
            if entry["membership_policy"] == "invited":
                actor = board_store.acting_session(os.environ.get("CODEX_SESSION_ID", ""))
                if command == "register":
                    if board_store.session_uuid(parsed.session) != actor:
                        raise cat.CatalogError("invited registration must be for the current session")
                    if db.execute("SELECT 1 FROM invitations WHERE board_id=? AND session=?",
                                  (entry["board_id"], actor)).fetchone() is None:
                        raise cat.CatalogError("session was not invited to this board")
                else:
                    member = _member(entry["snapshot_path"] if entry["state"] == "archived"
                                     else entry["db_path"], actor,
                                     immutable=entry["state"] == "archived")
                    if member is None:
                        raise cat.CatalogError("current session is not a board member")
                    if command in ("read", "search", "thread", "thread-read", "threads"):
                        if "--session" in argv:
                            if argv[argv.index("--session") + 1] != actor:
                                raise cat.CatalogError("member-scoped read must use current session")
                        else:
                            argv = [*argv, "--session", actor]
                    elif "--session" in argv and argv[argv.index("--session") + 1] != actor:
                        raise cat.CatalogError("member-scoped command must use current session")
        return board_store.main(argv, db_path=content_path, board_id=entry["board_id"],
                                board_home=str(home), readonly=archived,
                                disposed_notice_ids=disposed_notice_ids)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    home_arg = None
    board_key = None
    offset = 0
    while offset < len(argv) and argv[offset] in ("--home", "--board"):
        if offset + 1 >= len(argv):
            raise cat.CatalogError(f"{argv[offset]} requires a value")
        if argv[offset] == "--home":
            home_arg = argv[offset + 1]
        else:
            board_key = argv[offset + 1]
        offset += 2
    remaining = argv[offset:]
    if not remaining or remaining == ["--help"]:
        print(__doc__)
        print("Usage: board.py [--home DIR] boards ACTION ...")
        print("       board.py [--home DIR] --board UUID-or-alias CONTENT_COMMAND ...")
        return 0 if remaining else 2
    home = cat.home_path(home_arg)
    if remaining[0] == "boards":
        return boards(remaining[1:], home)
    return content(remaining, home, board_key)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (cat.CatalogError, board_store.UserError, active_listener.ListenerError,
            multi_board_watch.WatchError) as exc:
        print(f"message-board: {exc}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("message-board: interrupted", file=sys.stderr)
        sys.exit(130)
    except (sqlite3.Error, OSError) as exc:
        print(f"message-board: storage operation failed: {exc}", file=sys.stderr)
        sys.exit(2)
