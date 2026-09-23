#!/usr/bin/env python3
"""Per-board posts and durable delivery state; opened through board.py."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queue_transport
import active_listener


SCHEMA_VERSION = 4
KINDS = ("blocker", "decision", "handoff", "finding", "status", "question", "proposal")
STATUSES = ("active", "paused", "completed")
DEFAULT_STALE_AFTER = 300
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
INLINE_FANOUT_LIMIT = 32
MIN_RECOVER_AGE_SECONDS = 120
DELIVERY_STATES = ("pending", "sending", "queued", "acknowledged", "failed", "ambiguous",
                   "managed_pending")
SAFE_TRANSPORT_REASONS = frozenset({"queue_accepted", "queue_rejected", "sender_timeout",
                                    "unrecognized_queue_response", "runner_launch_failed",
                                    "sender_exception"})
SESSION_MUTATIONS = frozenset({"register", "heartbeat", "leave", "post", "open", "reply",
                               "subscribe", "unsubscribe", "ack", "ack-notice", "watch",
                               "scope-transfer"})
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|secret)\s*[:=]\s*['\"]?(?!redacted\b|none\b|null\b|example\b)[^\s'\"]+", re.IGNORECASE),
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{10,}|sk_(?:live|test)_[A-Za-z0-9_]{10,}|sk-[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{16})\b"),
    re.compile(r"://[^/\s:@]+:[^@\s/]+@"),
)


class UserError(Exception):
    """Expected input or board-state error, safe to print without a traceback."""


def scrub(value: str) -> str:
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def safe_record(record: dict) -> dict:
    return {key: scrub(value) if isinstance(value, str) else value
            for key, value in record.items()}


def session_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise UserError("session must be a UUID") from None


def acting_session(value: str) -> str:
    """Guard accidental cross-session writes in the trusted local account."""
    session = session_uuid(value)
    process_session = os.environ.get("CODEX_SESSION_ID")
    try:
        if process_session is None or str(uuid.UUID(process_session)) != process_session:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise UserError("CODEX_SESSION_ID must be a canonical UUID for session mutations") from None
    if session != process_session:
        raise UserError("session does not match CODEX_SESSION_ID")
    return session


def bounded(value: str | None, label: str, maximum: int, *, optional: bool = False,
            multiline: bool = False) -> str | None:
    if value is None and optional:
        return None
    if value is None or not value.strip() or len(value) > maximum:
        raise UserError(f"{label} must contain 1 to {maximum} characters")
    allowed = "\n\t" if multiline else ""
    if any(ord(ch) < 32 and ch not in allowed for ch in value) or "\x7f" in value:
        raise UserError(f"{label} contains a control character")
    if scrub(value) != value:
        raise UserError(f"{label} looks like a credential; do not put secrets on the board")
    return value


def nonnegative(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from None
    if number < 0 or number > 9_223_372_036_854_775_807:
        raise argparse.ArgumentTypeError("must be a nonnegative 64-bit integer")
    return number


def positive(value: str) -> int:
    number = nonnegative(value)
    if number == 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@contextmanager
def database(path_text: str, *, readonly: bool = False):
    if readonly:
        path = Path(path_text).resolve(strict=True)
        conn = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=15)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=15000")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
        finally:
            conn.close()
        return
    schema_lock = None
    if path_text != ":memory:":
        Path(path_text).expanduser().parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path_text = str(Path(path_text).expanduser())
        if not Path(path_text).exists():
            try:
                descriptor = os.open(path_text, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(descriptor)
            except FileExistsError:
                pass
        schema_lock = open(path_text + ".schema.lock", "a+")
        fcntl.flock(schema_lock, fcntl.LOCK_EX)
    try:
        conn = sqlite3.connect(path_text, timeout=15, isolation_level=None)
    except BaseException:
        if schema_lock is not None:
            fcntl.flock(schema_lock, fcntl.LOCK_UN)
            schema_lock.close()
        raise
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                conn.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS sessions (
                        session TEXT PRIMARY KEY,
                        campaign TEXT NOT NULL CHECK(length(campaign) BETWEEN 1 AND 128),
                        role TEXT NOT NULL CHECK(length(role) BETWEEN 1 AND 128),
                        profile TEXT CHECK(profile IS NULL OR length(profile) BETWEEN 1 AND 64),
                        status TEXT NOT NULL CHECK(status IN ('active','paused','completed')),
                        work TEXT CHECK(work IS NULL OR length(work) BETWEEN 1 AND 2000),
                        registered_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL,
                        ack_seq INTEGER NOT NULL DEFAULT 0 CHECK(ack_seq >= 0)
                    );
                    CREATE TABLE IF NOT EXISTS posts (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        author TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                        recipient TEXT REFERENCES sessions(session) ON DELETE RESTRICT,
                        topic TEXT NOT NULL CHECK(length(topic) BETWEEN 1 AND 128),
                        kind TEXT NOT NULL CHECK(kind IN ('blocker','decision','handoff','finding','status','question','proposal')),
                        text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 8000),
                        ref TEXT CHECK(ref IS NULL OR length(ref) BETWEEN 1 AND 512),
                        reply_to INTEGER REFERENCES posts(seq) ON DELETE RESTRICT,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS posts_topic_seq ON posts(topic, seq);
                    CREATE INDEX IF NOT EXISTS posts_recipient_seq ON posts(recipient, seq);
                    CREATE TRIGGER IF NOT EXISTS posts_no_update BEFORE UPDATE ON posts
                      BEGIN SELECT RAISE(ABORT, 'board posts are immutable'); END;
                    CREATE TRIGGER IF NOT EXISTS posts_no_delete BEFORE DELETE ON posts
                      BEGIN SELECT RAISE(ABORT, 'board posts are immutable'); END;
                    PRAGMA user_version=1;
                    COMMIT;
                """)
                version = 1
            if version == 1:
                conn.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS threads (
                        thread_id INTEGER PRIMARY KEY REFERENCES posts(seq) ON DELETE RESTRICT,
                        title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
                        topic TEXT NOT NULL CHECK(length(topic) BETWEEN 1 AND 128),
                        opener TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS thread_posts (
                        post_seq INTEGER PRIMARY KEY REFERENCES posts(seq) ON DELETE RESTRICT,
                        thread_id INTEGER NOT NULL REFERENCES threads(thread_id) ON DELETE RESTRICT
                    );
                    CREATE INDEX IF NOT EXISTS thread_posts_thread_seq ON thread_posts(thread_id, post_seq);
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        thread_id INTEGER NOT NULL REFERENCES threads(thread_id) ON DELETE RESTRICT,
                        session TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                        subscribed_at TEXT NOT NULL,
                        PRIMARY KEY(thread_id, session)
                    );
                    CREATE TABLE IF NOT EXISTS attachments (
                        post_seq INTEGER NOT NULL REFERENCES posts(seq) ON DELETE RESTRICT,
                        position INTEGER NOT NULL CHECK(position BETWEEN 1 AND 10),
                        reference TEXT NOT NULL CHECK(length(reference) BETWEEN 1 AND 512),
                        PRIMARY KEY(post_seq, position)
                    );
                    CREATE TABLE IF NOT EXISTS notification_outbox (
                        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recipient TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                        thread_id INTEGER NOT NULL REFERENCES threads(thread_id) ON DELETE RESTRICT,
                        post_seq INTEGER NOT NULL REFERENCES posts(seq) ON DELETE RESTRICT,
                        event TEXT NOT NULL CHECK(event IN ('open','reply')),
                        title TEXT NOT NULL,
                        sender TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                        created_at TEXT NOT NULL,
                        UNIQUE(recipient, post_seq)
                    );
                    CREATE INDEX IF NOT EXISTS notification_recipient_id
                      ON notification_outbox(recipient, notification_id);
                    CREATE TRIGGER IF NOT EXISTS threads_no_update BEFORE UPDATE ON threads
                      BEGIN SELECT RAISE(ABORT, 'threads are immutable'); END;
                    CREATE TRIGGER IF NOT EXISTS threads_no_delete BEFORE DELETE ON threads
                      BEGIN SELECT RAISE(ABORT, 'threads are immutable'); END;
                    CREATE TRIGGER IF NOT EXISTS thread_posts_no_update BEFORE UPDATE ON thread_posts
                      BEGIN SELECT RAISE(ABORT, 'thread links are immutable'); END;
                    CREATE TRIGGER IF NOT EXISTS thread_posts_no_delete BEFORE DELETE ON thread_posts
                      BEGIN SELECT RAISE(ABORT, 'thread links are immutable'); END;
                    CREATE TRIGGER IF NOT EXISTS attachments_no_update BEFORE UPDATE ON attachments
                      BEGIN SELECT RAISE(ABORT, 'attachments are immutable'); END;
                    CREATE TRIGGER IF NOT EXISTS attachments_no_delete BEFORE DELETE ON attachments
                      BEGIN SELECT RAISE(ABORT, 'attachments are immutable'); END;
                    PRAGMA user_version=2;
                    COMMIT;
                """)
                version = 2
            if version == 2:
                conn.executescript("""
                    BEGIN IMMEDIATE;
                    ALTER TABLE notification_outbox ADD COLUMN delivery_state TEXT NOT NULL DEFAULT 'pending'
                      CHECK(delivery_state IN ('pending','sending','queued','acknowledged','failed','ambiguous'));
                    ALTER TABLE notification_outbox ADD COLUMN queue_message_id TEXT;
                    ALTER TABLE notification_outbox ADD COLUMN state_changed_at TEXT;
                    ALTER TABLE notification_outbox ADD COLUMN attempted_at TEXT;
                    ALTER TABLE notification_outbox ADD COLUMN queued_at TEXT;
                    ALTER TABLE notification_outbox ADD COLUMN acknowledged_at TEXT;
                    ALTER TABLE notification_outbox ADD COLUMN claim_token TEXT;
                    ALTER TABLE notification_outbox ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0;
                    UPDATE notification_outbox SET state_changed_at=created_at;
                    CREATE INDEX notification_delivery_state_id
                      ON notification_outbox(delivery_state, notification_id);
                    PRAGMA user_version=3;
                    COMMIT;
                """)
                version = 3
            if version == 3:
                conn.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE notification_attempts (
                        notification_id INTEGER NOT NULL REFERENCES notification_outbox(notification_id),
                        attempt_number INTEGER NOT NULL CHECK(attempt_number > 0),
                        profile TEXT,
                        acting_session TEXT,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        result TEXT NOT NULL CHECK(result IN ('sending','queued','failed','ambiguous')),
                        reason TEXT NOT NULL,
                        recovered_by TEXT,
                        recovered_at TEXT,
                        PRIMARY KEY(notification_id, attempt_number)
                    );
                    PRAGMA user_version=4;
                    COMMIT;
                """)
                version = 4
            if version != SCHEMA_VERSION:
                raise UserError(f"unsupported board schema version {version}; expected {SCHEMA_VERSION}")
            # Early schema-4 boards had attempt provenance but no recipient route.
            # Repair them in place, preserving every schema-3 row as a queue route.
            if "route" not in {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}:
                conn.execute("ALTER TABLE sessions ADD COLUMN route TEXT NOT NULL DEFAULT 'queue' "
                             "CHECK(route IN ('queue','managed'))")
            if "route" not in {row[1] for row in conn.execute("PRAGMA table_info(notification_outbox)")}:
                conn.execute("PRAGMA foreign_keys=OFF")
                try:
                    conn.executescript("""
                        BEGIN IMMEDIATE;
                        CREATE TABLE notification_outbox_new (
                            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            recipient TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                            thread_id INTEGER NOT NULL REFERENCES threads(thread_id) ON DELETE RESTRICT,
                            post_seq INTEGER NOT NULL REFERENCES posts(seq) ON DELETE RESTRICT,
                            event TEXT NOT NULL CHECK(event IN ('open','reply')),
                            title TEXT NOT NULL,
                            sender TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                            created_at TEXT NOT NULL,
                            delivery_state TEXT NOT NULL DEFAULT 'pending'
                              CHECK(delivery_state IN ('pending','sending','queued','acknowledged',
                                                       'failed','ambiguous','managed_pending')),
                            queue_message_id TEXT, state_changed_at TEXT, attempted_at TEXT,
                            queued_at TEXT, acknowledged_at TEXT, claim_token TEXT,
                            attempt_count INTEGER NOT NULL DEFAULT 0,
                            route TEXT NOT NULL DEFAULT 'queue' CHECK(route IN ('queue','managed')),
                            UNIQUE(recipient, post_seq)
                        );
                        INSERT INTO notification_outbox_new
                          (notification_id,recipient,thread_id,post_seq,event,title,sender,created_at,
                           delivery_state,queue_message_id,state_changed_at,attempted_at,queued_at,
                           acknowledged_at,claim_token,attempt_count,route)
                        SELECT notification_id,recipient,thread_id,post_seq,event,title,sender,created_at,
                               delivery_state,queue_message_id,state_changed_at,attempted_at,queued_at,
                               acknowledged_at,claim_token,attempt_count,'queue'
                          FROM notification_outbox;
                        DROP TABLE notification_outbox;
                        ALTER TABLE notification_outbox_new RENAME TO notification_outbox;
                        CREATE INDEX notification_recipient_id
                          ON notification_outbox(recipient, notification_id);
                        CREATE INDEX notification_delivery_state_id
                          ON notification_outbox(delivery_state, notification_id);
                        COMMIT;
                    """)
                    if conn.execute("PRAGMA foreign_key_check").fetchone():
                        raise UserError("board migration foreign key check failed")
                finally:
                    conn.execute("PRAGMA foreign_keys=ON")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
            for name, definition in (
                ("parent_session", "TEXT"), ("scope", "TEXT"), ("expires_at", "TEXT"),
                ("owner", "INTEGER NOT NULL DEFAULT 0 CHECK(owner IN (0,1))"),
            ):
                if name not in columns:
                    conn.execute(f"ALTER TABLE sessions ADD COLUMN {name} {definition}")
            conn.execute("""CREATE TABLE IF NOT EXISTS membership_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                event TEXT NOT NULL CHECK(event IN ('register','heartbeat','leave')),
                role TEXT NOT NULL, status TEXT NOT NULL, route TEXT NOT NULL,
                parent_session TEXT, scope TEXT, expires_at TEXT, owner INTEGER NOT NULL,
                happened_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS scope_transfers (
                transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session TEXT NOT NULL REFERENCES sessions(session) ON DELETE RESTRICT,
                parent_session TEXT NOT NULL, scope TEXT NOT NULL,
                reason TEXT NOT NULL, transferred_at TEXT NOT NULL
            )""")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        if schema_lock is not None:
            fcntl.flock(schema_lock, fcntl.LOCK_UN)
            schema_lock.close()
            schema_lock = None
        yield conn
    finally:
        conn.close()
        if schema_lock is not None:
            fcntl.flock(schema_lock, fcntl.LOCK_UN)
            schema_lock.close()


@contextmanager
def write(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def bind_board(conn: sqlite3.Connection, board_id: str, *, initialize: bool = False) -> None:
    """Reject a replaced board file; initialize identity only at create/migrate."""
    conn.execute("CREATE TABLE IF NOT EXISTS board_meta (board_id TEXT NOT NULL PRIMARY KEY)")
    rows = conn.execute("SELECT board_id FROM board_meta").fetchall()
    if not rows and initialize:
        conn.execute("INSERT INTO board_meta(board_id) VALUES(?)", (board_id,))
        rows = conn.execute("SELECT board_id FROM board_meta").fetchall()
    if len(rows) != 1 or rows[0][0] != board_id:
        raise UserError("board database identity does not match catalog; migration may be required")


def expires(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise UserError("expires-at must be an ISO-8601 UTC timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise UserError("expires-at must be an ISO-8601 UTC timestamp")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def require_active_session(conn: sqlite3.Connection, session: str) -> None:
    row = conn.execute("SELECT status,expires_at FROM sessions WHERE session=?", (session,)).fetchone()
    if row is None or row["status"] != "active" or (row["expires_at"] and row["expires_at"] <= utc_now()):
        raise UserError("session is not an active, unexpired board member")


def record_membership(conn: sqlite3.Connection, session: str, event: str) -> None:
    conn.execute("""INSERT INTO membership_events
        (session,event,role,status,route,parent_session,scope,expires_at,owner,happened_at)
        SELECT session,?,role,status,route,parent_session,scope,expires_at,owner,?
        FROM sessions WHERE session=?""", (event, utc_now(), session))


def require_session(conn: sqlite3.Connection, session: str) -> None:
    if conn.execute("SELECT 1 FROM sessions WHERE session=?", (session,)).fetchone() is None:
        raise UserError("session is not registered")


def require_settled_children(conn: sqlite3.Connection, session: str) -> None:
    child = conn.execute("SELECT session FROM sessions WHERE parent_session=? AND status IN ('active','paused') "
                         "AND (expires_at IS NULL OR expires_at>?) LIMIT 1",
                         (session, utc_now())).fetchone()
    if child:
        raise UserError("unexpired delegated child must leave or transfer scope before parent leaves")


def require_settled_notices(conn: sqlite3.Connection, session: str,
                            disposed: set[int]) -> None:
    unresolved = [row[0] for row in conn.execute(
        "SELECT notification_id FROM notification_outbox WHERE recipient=? "
        "AND delivery_state!='acknowledged' ORDER BY notification_id", (session,))
        if row[0] not in disposed]
    if unresolved:
        raise UserError(f"unresolved incoming notices require acknowledgment or explicit disposition: {unresolved}")


def register(conn: sqlite3.Connection, args: argparse.Namespace) -> dict:
    session = acting_session(args.session)
    role = bounded(args.role, "role", 128)
    profile = bounded(args.profile, "profile", 64, optional=True)
    if profile is not None and profile not in queue_transport.PROFILE_NAMES:
        raise UserError("profile must be an exact allowed Codex profile name")
    work_text = bounded(args.work, "work", 2000, optional=True, multiline=True)
    supplied_scope = bounded(args.scope, "scope", 1000, optional=True)
    supplied_parent = session_uuid(args.parent_session) if args.parent_session else None
    if bool(supplied_parent) != bool(supplied_scope):
        raise UserError("parent-session and scope must be supplied together")
    with write(conn):
        prior = conn.execute("SELECT status,parent_session,scope,expires_at,route,campaign "
                             "FROM sessions WHERE session=?",
                             (session,)).fetchone()
        status = args.status or (prior["status"] if prior else "active")
        campaign = bounded(args.campaign or (prior["campaign"] if prior else "general"),
                           "campaign", 128)
        route = args.route or (prior["route"] if prior else "queue")
        if prior and prior["status"] == "active" and prior["route"] == "managed" and route != "managed":
            raise UserError("active managed route cannot be downgraded to queue")
        parent = supplied_parent if supplied_parent is not None else (
            prior["parent_session"] if prior else None)
        scope = supplied_scope if supplied_scope is not None else (prior["scope"] if prior else None)
        expiry = expires(args.expires_at) if args.expires_at else (prior["expires_at"] if prior else None)
        if parent and not expiry:
            raise UserError("delegated child membership requires expires-at")
        if expiry and expiry <= utc_now() and status != "completed":
            raise UserError("expires-at must be in the future")
        if prior and prior["status"] == "completed":
            raise UserError("retired membership cannot be registered again")
        if prior and (prior["parent_session"] != parent or prior["scope"] != scope):
            raise UserError("membership parent and scope cannot be reassigned")
        if parent and status != "completed":
            require_active_session(conn, parent)
        if status == "completed":
            require_settled_children(conn, session)
            require_settled_notices(conn, session, args.disposed_notice_ids)
        now = utc_now()
        conn.execute("""
            INSERT INTO sessions(session,campaign,role,profile,status,work,registered_at,last_seen_at,
                                 route,parent_session,scope,expires_at,owner)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(session) DO UPDATE SET
              campaign=excluded.campaign, role=excluded.role,
              profile=COALESCE(excluded.profile, sessions.profile),
              status=excluded.status, work=COALESCE(excluded.work, sessions.work),
              route=excluded.route, parent_session=excluded.parent_session,
              scope=excluded.scope, expires_at=excluded.expires_at,
              owner=max(sessions.owner, excluded.owner),
              last_seen_at=max(sessions.last_seen_at, excluded.last_seen_at)
        """, (session, campaign, role, profile, status, work_text, now, now,
              route, parent, scope, expiry, int(args.owner)))
        record_membership(conn, session, "register")
    return {"session": session, "status": status}


def heartbeat(conn: sqlite3.Connection, args: argparse.Namespace) -> dict:
    session = acting_session(args.session)
    work_text = bounded(args.work, "work", 2000, optional=True, multiline=True)
    with write(conn):
        require_session(conn, session)
        row = conn.execute("SELECT status,expires_at FROM sessions WHERE session=?", (session,)).fetchone()
        if row["status"] == "completed" and args.status not in (None, "completed"):
            raise UserError("retired membership cannot be reactivated")
        if args.status == "completed":
            require_settled_children(conn, session)
            require_settled_notices(conn, session, args.disposed_notice_ids)
        if args.status == "active" and row["expires_at"] and row["expires_at"] <= utc_now():
            raise UserError("expired membership cannot be reactivated without a new expiry")
        now = utc_now()
        conn.execute("""
            UPDATE sessions SET last_seen_at=max(last_seen_at, ?),
              work=COALESCE(?, work), status=COALESCE(?, status)
            WHERE session=?
        """, (now, work_text, args.status, session))
        row = conn.execute("SELECT status, last_seen_at FROM sessions WHERE session=?", (session,)).fetchone()
        record_membership(conn, session, "heartbeat")
    return {"session": session, "status": row["status"], "last_seen_at": row["last_seen_at"]}


def leave(conn: sqlite3.Connection, args: argparse.Namespace) -> dict:
    session = acting_session(args.session)
    with write(conn):
        require_session(conn, session)
        require_settled_children(conn, session)
        require_settled_notices(conn, session, args.disposed_notice_ids)
        conn.execute("UPDATE sessions SET status='completed', last_seen_at=? WHERE session=?",
                     (utc_now(), session))
        record_membership(conn, session, "leave")
    return {"session": session, "status": "completed"}


def scope_transfer(conn: sqlite3.Connection, args: argparse.Namespace) -> dict:
    parent = acting_session(args.session)
    session = session_uuid(args.child)
    reason = bounded(args.reason, "reason", 2000)
    with write(conn):
        require_active_session(conn, parent)
        row = conn.execute("SELECT parent_session,scope,status,expires_at FROM sessions WHERE session=?",
                           (session,)).fetchone()
        if row is None or row["status"] not in ("active", "paused") or row["parent_session"] != parent:
            raise UserError("scope transfer requires this active parent and its delegated child")
        if row["expires_at"] and row["expires_at"] <= utc_now():
            raise UserError("expired child cannot transfer scope")
        conn.execute("INSERT INTO scope_transfers(session,parent_session,scope,reason,transferred_at) "
                     "VALUES(?,?,?,?,?)", (session, parent, row["scope"], reason, utc_now()))
        conn.execute("UPDATE sessions SET parent_session=NULL,scope=NULL,role='root' WHERE session=?",
                     (session,))
    return {"session": session, "parent_session": None, "scope": None}


def sessions(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = []
    for row in conn.execute("SELECT * FROM sessions ORDER BY campaign, session"):
        item = dict(row)
        seen = datetime.fromisoformat(item["last_seen_at"].replace("Z", "+00:00"))
        item["stale"] = (now - seen).total_seconds() > args.stale_after
        result.append(safe_record(item))
    return result


def post(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    author = acting_session(args.session)
    recipient = None if args.to == "all" else session_uuid(args.to)
    topic = bounded(args.topic, "topic", 128)
    body = bounded(args.text, "text", 8000, multiline=True)
    ref = bounded(args.ref, "ref", 512, optional=True)
    attachments = checked_attachments(args.attach)
    with write(conn):
        require_active_session(conn, author)
        if recipient is not None:
            require_session(conn, recipient)
        if args.reply_to is not None:
            parent = conn.execute("SELECT topic, recipient, author FROM posts WHERE seq=?", (args.reply_to,)).fetchone()
            if parent is None:
                raise UserError("reply target does not exist")
            if parent["topic"] != topic:
                raise UserError("reply topic must match the parent topic")
            if parent["recipient"] not in (None, author) and parent["author"] != author:
                raise UserError("reply target is not visible to this session")
            if conn.execute("SELECT 1 FROM thread_posts WHERE post_seq=?", (args.reply_to,)).fetchone():
                raise UserError("use reply --thread for a titled thread")
            if parent["recipient"] is not None and recipient not in (parent["author"], parent["recipient"]):
                raise UserError("a private reply must stay between the original participants")
        cur = conn.execute("""
            INSERT INTO posts(author,recipient,topic,kind,text,ref,reply_to,created_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, (author, recipient, topic, args.kind, body, ref, args.reply_to, utc_now()))
        seq = cur.lastrowid
        add_attachments(conn, seq, attachments)
    return seq


def checked_attachments(values: list[str] | None) -> list[str]:
    values = values or []
    if len(values) > 10:
        raise UserError("at most 10 attachment references are allowed")
    result = []
    for value in values:
        value = bounded(value, "attachment", 512)
        if not (value.startswith("/") or value.startswith("https://") or value.startswith("http://")):
            raise UserError("attachment must be an absolute local path or HTTP(S) URL")
        result.append(value)
    return result


def add_attachments(conn: sqlite3.Connection, seq: int, values: list[str]) -> None:
    conn.executemany("INSERT INTO attachments(post_seq,position,reference) VALUES(?,?,?)",
                     ((seq, index, value) for index, value in enumerate(values, 1)))


def thread_info(conn: sqlite3.Connection, thread_id: int, session: str | None = None) -> sqlite3.Row:
    row = conn.execute("""
        SELECT threads.*, posts.recipient FROM threads
        JOIN posts ON posts.seq=threads.thread_id
        WHERE threads.thread_id=?
    """, (thread_id,)).fetchone()
    if row is None:
        raise UserError("thread does not exist")
    if session is not None and row["recipient"] is not None and session not in (row["opener"], row["recipient"]):
        raise UserError("thread is not visible to this session")
    return row


def notify(conn: sqlite3.Connection, recipients: set[str], thread_id: int, post_seq: int,
           event: str, title: str, sender: str) -> None:
    now = utc_now()
    targets = sorted(recipients - {sender})
    if not targets:
        return
    routed = conn.execute("SELECT session,route FROM sessions WHERE status='active' "
                          "AND (expires_at IS NULL OR expires_at>?) AND session IN (" +
                          ",".join("?" for _ in targets) + ") ORDER BY session", (now, *targets))
    conn.executemany("""
        INSERT OR IGNORE INTO notification_outbox
          (recipient,thread_id,post_seq,event,title,sender,created_at,state_changed_at,
           route,delivery_state)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, ((recipient, thread_id, post_seq, event, title, sender, now, now,
           route, "managed_pending" if route == "managed" else "pending")
          for recipient, route in routed))


def sender_profile(explicit: str | None) -> str:
    """Use an exact allowed sender home; never infer one from the recipient."""
    if explicit is None:
        home = os.environ.get("CODEX_HOME")
        if not home:
            raise UserError("set CODEX_HOME or --sender-profile before pushing")
        path = Path(home).expanduser()
        root = queue_transport.profile_root()
        profiles = [name for name in queue_transport.PROFILE_NAMES
                    if path == root / name]
        if len(profiles) != 1:
            raise UserError("CODEX_HOME must be an exact allowed sender profile path")
        explicit = profiles[0]
    if explicit not in queue_transport.PROFILE_NAMES:
        raise UserError("sender profile must be an allowed Codex profile name")
    path = queue_transport.profile_root() / explicit
    if not path.is_dir() or path.is_symlink():
        raise UserError("sender profile directory does not exist or is a symlink")
    return explicit


def open_thread(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    author = acting_session(args.session)
    recipient = None if args.to == "all" else session_uuid(args.to)
    title = bounded(args.title, "title", 160)
    try:
        queue_transport._safe_text(title, "title", queue_transport.MAX_TITLE_CHARS)
    except ValueError:
        raise UserError("title contains characters unsafe for a push notice") from None
    topic = bounded(args.topic, "topic", 128)
    body = bounded(args.text, "text", 8000, multiline=True)
    ref = bounded(args.ref, "ref", 512, optional=True)
    attachments = checked_attachments(args.attach)
    with write(conn):
        require_active_session(conn, author)
        if recipient is not None:
            require_session(conn, recipient)
        now = utc_now()
        cur = conn.execute("""
            INSERT INTO posts(author,recipient,topic,kind,text,ref,reply_to,created_at)
            VALUES(?,?,?,?,?,?,NULL,?)
        """, (author, recipient, topic, args.kind, body, ref, now))
        thread_id = cur.lastrowid
        conn.execute("INSERT INTO threads(thread_id,title,topic,opener,created_at) VALUES(?,?,?,?,?)",
                     (thread_id, title, topic, author, now))
        conn.execute("INSERT INTO thread_posts(post_seq,thread_id) VALUES(?,?)", (thread_id, thread_id))
        add_attachments(conn, thread_id, attachments)
        conn.execute("INSERT INTO subscriptions(thread_id,session,subscribed_at) VALUES(?,?,?)",
                     (thread_id, author, now))
        if recipient is None:
            targets = {row[0] for row in conn.execute(
                "SELECT session FROM sessions WHERE status='active' "
                "AND (expires_at IS NULL OR expires_at>?)", (now,))}
        else:
            targets = {recipient}
            conn.execute("INSERT OR IGNORE INTO subscriptions(thread_id,session,subscribed_at) VALUES(?,?,?)",
                         (thread_id, recipient, now))
        notify(conn, targets, thread_id, thread_id, "open", title, author)
    active_listener.signal_post(conn, thread_id)
    return thread_id


def reply_thread(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    author = acting_session(args.session)
    body = bounded(args.text, "text", 8000, multiline=True)
    ref = bounded(args.ref, "ref", 512, optional=True)
    attachments = checked_attachments(args.attach)
    cc = {session_uuid(value) for value in args.cc}
    with write(conn):
        require_active_session(conn, author)
        thread = thread_info(conn, args.thread, author)
        for target in cc:
            require_session(conn, target)
            thread_info(conn, args.thread, target)
        recipient = None if thread["recipient"] is None else (
            thread["recipient"] if author == thread["opener"] else thread["opener"])
        if args.reply_to is not None:
            parent = conn.execute("SELECT 1 FROM thread_posts WHERE post_seq=? AND thread_id=?",
                                  (args.reply_to, args.thread)).fetchone()
            if parent is None:
                raise UserError("reply target is not in this thread")
        now = utc_now()
        cur = conn.execute("""
            INSERT INTO posts(author,recipient,topic,kind,text,ref,reply_to,created_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, (author, recipient, thread["topic"], args.kind, body, ref, args.reply_to or args.thread, now))
        seq = cur.lastrowid
        conn.execute("INSERT INTO thread_posts(post_seq,thread_id) VALUES(?,?)", (seq, args.thread))
        add_attachments(conn, seq, attachments)
        targets = {row[0] for row in conn.execute(
            "SELECT session FROM subscriptions WHERE thread_id=?", (args.thread,))}
        notify(conn, targets | cc, args.thread, seq, "reply", thread["title"], author)
    active_listener.signal_post(conn, seq)
    return seq


def subscribe(conn: sqlite3.Connection, args: argparse.Namespace, *, remove: bool = False) -> dict:
    session = acting_session(args.session)
    with write(conn):
        require_active_session(conn, session)
        thread_info(conn, args.thread, session)
        if remove:
            conn.execute("DELETE FROM subscriptions WHERE thread_id=? AND session=?", (args.thread, session))
        else:
            conn.execute("INSERT OR IGNORE INTO subscriptions(thread_id,session,subscribed_at) VALUES(?,?,?)",
                         (args.thread, session, utc_now()))
    return {"session": session, "thread_id": args.thread, "subscribed": not remove}


def notifications(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    session = session_uuid(args.session)
    require_session(conn, session)
    rows = conn.execute("""
        SELECT notification_id, thread_id, post_seq, event, title, sender, created_at,
               delivery_state, queue_message_id, state_changed_at, attempted_at,
               queued_at, acknowledged_at, attempt_count, route
        FROM notification_outbox WHERE recipient=? AND notification_id>?
        ORDER BY notification_id LIMIT ?
    """, (session, args.after, args.limit))
    return [safe_record(dict(row)) for row in rows]


def deliveries(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    recipient = session_uuid(args.recipient) if args.recipient else None
    if recipient:
        require_session(conn, recipient)
    clauses = ["notification_id > ?"]
    values: list[object] = [args.after]
    for column, value in (("thread_id", args.thread), ("post_seq", args.post),
                          ("recipient", recipient), ("delivery_state", args.state)):
        if value is not None:
            clauses.append(f"{column}=?")
            values.append(value)
    values.append(args.limit)
    rows = conn.execute("SELECT notification_id, recipient, thread_id, post_seq, event, "
                        "title, sender, created_at, delivery_state, queue_message_id, "
                        "state_changed_at, attempted_at, queued_at, acknowledged_at, "
                        "attempt_count, route FROM notification_outbox WHERE " +
                        " AND ".join(clauses) + " ORDER BY notification_id LIMIT ?", values)
    return [safe_record(dict(row)) for row in rows]


def delivery_counts(conn: sqlite3.Connection, post_seq: int) -> dict[str, int]:
    counts = {state: 0 for state in DELIVERY_STATES}
    for row in conn.execute("SELECT delivery_state, COUNT(*) AS n FROM notification_outbox "
                            "WHERE post_seq=? GROUP BY delivery_state", (post_seq,)):
        counts[row["delivery_state"]] = row["n"]
    return counts


def claim_next(conn: sqlite3.Connection, *, attempted_ids: set[int], post_seq: int | None,
               thread_id: int | None, recipient: str | None,
               profile: str, actor: str) -> dict | None:
    """One short transaction claims one row; the network call happens afterward."""
    with write(conn):
        clauses = ["route='queue'", "delivery_state IN ('pending','failed')"]
        values: list[object] = []
        if attempted_ids:
            clauses.append("notification_id NOT IN (" + ",".join("?" for _ in attempted_ids) + ")")
            values.extend(sorted(attempted_ids))
        for column, value in (("post_seq", post_seq), ("thread_id", thread_id),
                              ("recipient", recipient)):
            if value is not None:
                clauses.append(f"{column}=?")
                values.append(value)
        row = conn.execute("SELECT notification_id, recipient, thread_id, post_seq, event, "
                           "title, attempt_count FROM notification_outbox WHERE " + " AND ".join(clauses) +
                           " AND recipient IN (SELECT session FROM sessions WHERE status='active' "
                           "AND (expires_at IS NULL OR expires_at>?))" +
                           " ORDER BY CASE delivery_state WHEN 'pending' THEN 0 ELSE 1 END, "
                           "attempt_count, "
                           "notification_id LIMIT 1", (*values, utc_now())).fetchone()
        if row is None:
            return None
        token = str(uuid.uuid4())
        now = utc_now()
        conn.execute("UPDATE notification_outbox SET delivery_state='sending', "
                     "claim_token=?, attempted_at=?, state_changed_at=?, "
                     "attempt_count=attempt_count+1 WHERE notification_id=?",
                     (token, now, now, row["notification_id"]))
        attempt_number = row["attempt_count"] + 1
        conn.execute("INSERT INTO notification_attempts "
                     "(notification_id,attempt_number,profile,acting_session,started_at,result,reason) "
                     "VALUES (?,?,?,?,?,'sending','claimed')",
                     (row["notification_id"], attempt_number, profile, actor, now))
        return {**dict(row), "claim_token": token, "attempt_number": attempt_number}


def finish_claim(conn: sqlite3.Connection, claim: dict,
                 result: queue_transport.EnqueueResult | None,
                 reason: str | None = None) -> None:
    state = ("ambiguous" if result is None or result.status in ("timeout", "ambiguous")
             else result.status)
    now = utc_now()
    if reason is None:
        if result is not None and result.reason in SAFE_TRANSPORT_REASONS:
            reason = result.reason
        else:
            reason = {"queued": "queue_accepted", "failed": "sender_definite_failure",
                      "timeout": "sender_timeout", "ambiguous": "sender_uncertain_result"}.get(
                          result.status if result else None, "sender_exception")
    with write(conn):
        conn.execute("UPDATE notification_outbox SET delivery_state=?, queue_message_id=?, "
                     "queued_at=?, state_changed_at=?, claim_token=NULL "
                     "WHERE notification_id=? AND claim_token=? "
                     "AND delivery_state IN ('sending','ambiguous')",
                     (state, result.queue_message_id if result else None,
                      now if state == "queued" else None, now,
                      claim["notification_id"], claim["claim_token"]))
        conn.execute("UPDATE notification_attempts SET result=?, reason=?, finished_at=? "
                     "WHERE notification_id=? AND attempt_number=?",
                     (state, reason, now, claim["notification_id"], claim["attempt_number"]))


def dispatch_notices(conn: sqlite3.Connection, *, profile: str, actor: str, limit: int,
                     board_id: str, board_home: str,
                     post_seq: int | None = None, thread_id: int | None = None,
                     recipient: str | None = None,
                     sender=None) -> list[tuple[int, int]]:
    sender = sender or queue_transport.queue_notice
    processed: list[tuple[int, int]] = []
    attempted_ids: set[int] = set()
    while len(processed) < limit:
        claim = claim_next(conn, attempted_ids=attempted_ids, post_seq=post_seq,
                           thread_id=thread_id, recipient=recipient,
                           profile=profile, actor=actor)
        if claim is None:
            break
        # A definite failure is retryable on a later dispatch, not twice here.
        attempted_ids.add(claim["notification_id"])
        reason = None
        try:
            if claim["event"] == "open":
                notice = queue_transport.render_new_thread(
                    claim["thread_id"], claim["title"], claim["notification_id"],
                    board_id=board_id, board_home=board_home)
            else:
                notice = queue_transport.render_reply(
                    claim["thread_id"], claim["title"], claim["notification_id"],
                    claim["post_seq"], board_id=board_id, board_home=board_home)
            queue_transport._safe_text(notice, "notice", queue_transport.MAX_NOTICE_CHARS,
                                       multiline=True)
        except Exception:
            # All of these steps are local; the sender has not been called.
            result = queue_transport.EnqueueResult("failed", None, None, "")
            reason = "local_pre_send_failure"
        else:
            try:
                result = sender(claim["recipient"], profile, notice)
            except Exception:
                # Once entered, a sender may have reached codex queue.
                result = None
                reason = "sender_exception"
        finish_claim(conn, claim, result, reason)
        processed.append((claim["thread_id"], claim["post_seq"]))
    return processed


def ack_notice(conn: sqlite3.Connection, args: argparse.Namespace) -> dict:
    session = acting_session(args.session)
    with write(conn):
        require_session(conn, session)
        row = conn.execute("SELECT recipient, thread_id FROM notification_outbox "
                           "WHERE notification_id=?", (args.notification,)).fetchone()
        if row is None or row["recipient"] != session:
            raise UserError("notification does not belong to this session")
        now = utc_now()
        conn.execute("UPDATE notification_outbox SET delivery_state='acknowledged', "
                     "acknowledged_at=COALESCE(acknowledged_at, ?), state_changed_at=?, "
                     "claim_token=NULL WHERE notification_id=?",
                     (now, now, args.notification))
    return {"notification_id": args.notification, "thread_id": row["thread_id"],
            "session": session}


def recover_sending(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if args.older_than < MIN_RECOVER_AGE_SECONDS:
        raise UserError(f"older-than must be at least {MIN_RECOVER_AGE_SECONDS} seconds")
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=args.older_than)).isoformat(
        timespec="microseconds").replace("+00:00", "Z")
    actor = acting_session(args.acting_session)
    with write(conn):
        rows = conn.execute("SELECT notification_id, attempt_count, attempted_at FROM "
                            "notification_outbox WHERE delivery_state='sending' "
                            "AND attempted_at<=?", (cutoff,)).fetchall()
        now = utc_now()
        for row in rows:
            conn.execute("UPDATE notification_outbox SET delivery_state='ambiguous', "
                         "state_changed_at=? WHERE notification_id=?",
                         (now, row["notification_id"]))
            cur = conn.execute("UPDATE notification_attempts SET result='ambiguous', "
                               "reason='interrupted_claim_recovered', finished_at=?, "
                               "recovered_by=?, recovered_at=? WHERE notification_id=? "
                               "AND attempt_number=? AND result='sending'",
                               (now, actor, now, row["notification_id"], row["attempt_count"]))
            if cur.rowcount == 0:
                # Schema-3 claims had no per-attempt record. Preserve that
                # uncertainty explicitly instead of inventing a sender.
                conn.execute("INSERT OR IGNORE INTO notification_attempts "
                             "(notification_id,attempt_number,started_at,finished_at,result,reason,"
                             "recovered_by,recovered_at) VALUES (?,?,?,?,'ambiguous',"
                             "'legacy_interrupted_claim_recovered',?,?)",
                             (row["notification_id"], row["attempt_count"],
                              row["attempted_at"], now, actor, now))
    return len(rows)


def attempts(conn: sqlite3.Connection, notification_id: int) -> list[dict]:
    if conn.execute("SELECT 1 FROM notification_outbox WHERE notification_id=?",
                    (notification_id,)).fetchone() is None:
        raise UserError("notification does not exist")
    return [dict(row) for row in conn.execute(
        "SELECT notification_id, attempt_number, profile, acting_session, started_at, "
        "finished_at, result, reason, recovered_by, recovered_at "
        "FROM notification_attempts WHERE notification_id=? ORDER BY attempt_number",
        (notification_id,))]


def list_threads(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    session = session_uuid(args.session) if args.session else None
    if session is not None:
        require_session(conn, session)
    rows = conn.execute("""
        SELECT t.thread_id, t.title, t.topic, t.opener, t.created_at,
               p.recipient, MAX(tp.post_seq) AS latest_seq
        FROM threads t JOIN posts p ON p.seq=t.thread_id
        JOIN thread_posts tp ON tp.thread_id=t.thread_id
        WHERE t.thread_id>? AND (? IS NULL OR p.recipient IS NULL OR p.recipient=? OR t.opener=?)
        GROUP BY t.thread_id ORDER BY t.thread_id LIMIT ?
    """, (args.after, session, session, session, args.limit))
    result = []
    for row in rows:
        item = dict(row)
        item["to"] = item.pop("recipient") or "all"
        result.append(safe_record(item))
    return result


def read_thread(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    session = session_uuid(args.session) if args.session else None
    if session is not None:
        require_session(conn, session)
    thread_info(conn, args.id, session)
    return query_posts(conn, session=None, after=args.after, topic=None, kind=None,
                       limit=args.limit, thread_id=args.id)


def search(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    session = session_uuid(args.session) if args.session else None
    if session is not None:
        require_session(conn, session)
    query = bounded(args.query, "query", 256)
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return query_posts(conn, session=session, after=args.after, topic=None, kind=None,
                       limit=args.limit, search_term=f"%{escaped}%",
                       include_thread_members=True)


def query_posts(conn: sqlite3.Connection, *, session: str | None, after: int,
                topic: str | None, kind: str | None, limit: int,
                thread_id: int | None = None, search_term: str | None = None,
                include_thread_members: bool = False) -> list[dict]:
    clauses = ["posts.seq > ?"]
    values: list[object] = [after]
    if session is not None:
        if include_thread_members:
            clauses.append("(posts.recipient IS NULL OR posts.recipient = ? OR "
                           "(threads.thread_id IS NOT NULL AND "
                           "(threads.opener = ? OR thread_root.recipient = ?)))")
            values.extend((session, session, session))
        else:
            clauses.append("(posts.recipient IS NULL OR posts.recipient = ?)")
            values.append(session)
    if topic is not None:
        clauses.append("posts.topic = ?")
        values.append(topic)
    if kind is not None:
        clauses.append("posts.kind = ?")
        values.append(kind)
    if thread_id is not None:
        clauses.append("thread_posts.thread_id = ?")
        values.append(thread_id)
    if search_term is not None:
        clauses.append("(posts.text LIKE ? ESCAPE '\\' OR posts.topic LIKE ? ESCAPE '\\' OR threads.title LIKE ? ESCAPE '\\')")
        values.extend((search_term, search_term, search_term))
    values.append(limit)
    sql = ("SELECT posts.*, thread_posts.thread_id, threads.title AS thread_title "
           "FROM posts LEFT JOIN thread_posts ON thread_posts.post_seq=posts.seq "
           "LEFT JOIN threads ON threads.thread_id=thread_posts.thread_id "
           "LEFT JOIN posts AS thread_root ON thread_root.seq=threads.thread_id WHERE "
           + " AND ".join(clauses) + " ORDER BY posts.seq LIMIT ?")
    result = []
    for row in conn.execute(sql, values):
        item = dict(row)
        item["to"] = item.pop("recipient") or "all"
        item["attachments"] = [scrub(reference[0]) for reference in conn.execute(
            "SELECT reference FROM attachments WHERE post_seq=? ORDER BY position", (item["seq"],))]
        result.append(safe_record(item))
    return result


def read(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    session = session_uuid(args.session) if args.session else None
    if session is not None:
        require_session(conn, session)
    topic = bounded(args.topic, "topic", 128, optional=True)
    return query_posts(conn, session=session, after=args.after, topic=topic,
                       kind=args.kind, limit=args.limit)


def ack(conn: sqlite3.Connection, args: argparse.Namespace) -> dict:
    session = acting_session(args.session)
    with write(conn):
        require_session(conn, session)
        latest = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM posts").fetchone()[0]
        if args.through > latest:
            raise UserError(f"cannot acknowledge future sequence; latest is {latest}")
        conn.execute("UPDATE sessions SET ack_seq=max(ack_seq, ?) WHERE session=?",
                     (args.through, session))
        cursor = conn.execute("SELECT ack_seq FROM sessions WHERE session=?", (session,)).fetchone()[0]
    return {"session": session, "ack_seq": cursor}


def inbox(conn: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    session = session_uuid(args.session)
    row = conn.execute("SELECT ack_seq FROM sessions WHERE session=?", (session,)).fetchone()
    if row is None:
        raise UserError("session is not registered")
    return query_posts(conn, session=session, after=row[0], topic=None, kind=None, limit=args.limit)


def output_posts(items: list[dict], as_json: bool, board_id: str) -> None:
    items = [{"board_id": board_id, **item} for item in items]
    if as_json:
        print(json.dumps(items, ensure_ascii=False, sort_keys=True))
        return
    if not items:
        print("(no posts)")
    for item in items:
        suffix = f" reply-to={item['reply_to']}" if item["reply_to"] is not None else ""
        suffix += f" ref={item['ref']}" if item["ref"] is not None else ""
        if item["thread_id"] is not None:
            suffix += f" thread=#{item['thread_id']} title={item['thread_title']}"
        print(f"{board_id}#{item['seq']} {item['created_at']} [{item['kind']}] {item['topic']} "
              f"{item['author']} -> {item['to']}{suffix}")
        for line in item["text"].splitlines():
            print(f"  {line}")
        for reference in item["attachments"]:
            print(f"  attachment: {reference}")


def print_delivery_report(conn: sqlite3.Connection, thread_id: int, post_seq: int,
                          board_id: str) -> bool:
    counts = delivery_counts(conn, post_seq)
    rows = conn.execute("SELECT notification_id, delivery_state FROM notification_outbox "
                        "WHERE post_seq=? ORDER BY notification_id", (post_seq,)).fetchall()
    report_states = DELIVERY_STATES if counts["managed_pending"] else DELIVERY_STATES[:-1]
    print(f"board={board_id} thread={thread_id} post={post_seq} " +
          " ".join(f"{state}={counts[state]}" for state in report_states))
    print("notices: " + (" ".join(f"{board_id}#{row['notification_id']}={row['delivery_state']}"
                                for row in rows) if rows else "(none)"))
    return counts["pending"] == counts["sending"] == counts["failed"] == counts["ambiguous"] == 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    def command(name: str, help_text: str) -> argparse.ArgumentParser:
        child = sub.add_parser(name, help=help_text)
        return child

    c = command("register", "register or update a self-reported session")
    c.add_argument("--session", required=True)
    c.add_argument("--campaign")
    c.add_argument("--role", required=True)
    c.add_argument("--profile")
    c.add_argument("--status", choices=STATUSES)
    c.add_argument("--work")
    c.add_argument("--route", choices=("queue", "managed"))
    c.add_argument("--parent-session")
    c.add_argument("--scope")
    c.add_argument("--expires-at")
    c.add_argument("--owner", action="store_true", help="mark an active owner for purge protection")

    c = command("heartbeat", "refresh last-seen and optionally update work/status")
    c.add_argument("--session", required=True)
    c.add_argument("--work")
    c.add_argument("--status", choices=STATUSES)

    c = command("leave", "explicitly retire this board membership")
    c.add_argument("--session", required=True)

    c = command("scope-transfer", "record a delegated child's transition to independent root scope")
    c.add_argument("--session", required=True)
    c.add_argument("--child", required=True)
    c.add_argument("--reason", required=True)

    c = command("sessions", "list self-reported sessions and heartbeat-age stale marker")
    c.add_argument("--stale-after", type=nonnegative, default=DEFAULT_STALE_AFTER,
                   metavar="SEC", help=f"staleness window in seconds (default {DEFAULT_STALE_AFTER})")
    c.add_argument("--json", action="store_true")

    c = command("membership-events", "read retained membership changes")
    c.add_argument("--session")
    c.add_argument("--after", type=nonnegative, default=0, metavar="ID")
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    c = command("scope-transfers", "read retained delegated scope transfers")
    c.add_argument("--session")
    c.add_argument("--json", action="store_true")

    c = command("post", "append a flat board post (no push; use open/reply for new cross-slice questions)")
    c.description = ("Append a flat board post. This does not push a notice; "
                     "use open/reply for new cross-slice questions.")
    c.add_argument("--session", required=True)
    c.add_argument("--topic", required=True)
    c.add_argument("--kind", required=True, choices=KINDS)
    c.add_argument("--text", required=True)
    c.add_argument("--to", default="all", metavar="SESSION_OR_ALL")
    c.add_argument("--ref")
    c.add_argument("--attach", action="append", metavar="PATH_OR_URL")
    c.add_argument("--reply-to", type=positive, metavar="SEQ")

    c = command("open", "open a titled thread and queue title/ID notifications")
    c.add_argument("--session", required=True)
    c.add_argument("--topic", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--kind", choices=KINDS, default="question")
    c.add_argument("--text", required=True)
    c.add_argument("--to", default="all", metavar="SESSION_OR_ALL")
    c.add_argument("--ref")
    c.add_argument("--attach", action="append", metavar="PATH_OR_URL")
    c.add_argument("--no-push", action="store_true", help="commit outbox only (offline/tests)")
    c.add_argument("--sender-profile", help="exact allowed Codex sender profile name")

    c = command("reply", "reply in a thread and notify subscribers/CCs")
    c.add_argument("--session", required=True)
    c.add_argument("--thread", type=positive, required=True, metavar="ID")
    c.add_argument("--kind", choices=KINDS, default="status")
    c.add_argument("--text", required=True)
    c.add_argument("--ref")
    c.add_argument("--attach", action="append", metavar="PATH_OR_URL")
    c.add_argument("--reply-to", type=positive, metavar="SEQ")
    c.add_argument("--cc", action="append", default=[], metavar="SESSION")
    c.add_argument("--no-push", action="store_true", help="commit outbox only (offline/tests)")
    c.add_argument("--sender-profile", help="exact allowed Codex sender profile name")

    c = command("dispatch", "send bounded pending/failed outbox notices")
    c.add_argument("--acting-session", required=True, metavar="UUID")
    c.add_argument("--sender-profile", help="exact allowed Codex sender profile name")
    c.add_argument("--thread", type=positive, metavar="ID")
    c.add_argument("--post", type=positive, metavar="SEQ")
    c.add_argument("--recipient", metavar="SESSION")
    c.add_argument("--limit", type=positive, default=INLINE_FANOUT_LIMIT, metavar="N")

    c = command("recover", "mark old interrupted sending claims ambiguous without resending")
    c.add_argument("--acting-session", required=True, metavar="UUID")
    c.add_argument("--older-than", type=positive, default=120, metavar="SEC")

    c = command("attempts", "read per-attempt notice provenance without notice content")
    c.add_argument("--notification", type=positive, required=True, metavar="ID")
    c.add_argument("--json", action="store_true")

    c = command("ack-notice", "explicitly acknowledge a notice as its recipient")
    c.add_argument("--session", required=True)
    c.add_argument("--notification", type=positive, required=True, metavar="ID")

    c = command("deliveries", "coordinator view of notice delivery states")
    c.add_argument("--thread", type=positive, metavar="ID")
    c.add_argument("--post", type=positive, metavar="SEQ")
    c.add_argument("--recipient", metavar="SESSION")
    c.add_argument("--state", choices=DELIVERY_STATES)
    c.add_argument("--after", type=nonnegative, default=0, metavar="ID")
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    c = command("threads", "list titled threads without reading bodies")
    c.add_argument("--session")
    c.add_argument("--after", type=nonnegative, default=0, metavar="ID")
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    for name in ("thread", "thread-read"):
        c = command(name, "read full posts in one titled thread")
        c.add_argument("--id", type=positive, required=True, metavar="ID")
        c.add_argument("--session")
        c.add_argument("--after", type=nonnegative, default=0, metavar="SEQ")
        c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
        c.add_argument("--json", action="store_true")

    c = command("search", "search full board history by title, topic, or text")
    c.add_argument("--query", required=True)
    c.add_argument("--session")
    c.add_argument("--after", type=nonnegative, default=0, metavar="SEQ")
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    for name, help_text in (("subscribe", "subscribe to replies in a visible thread"),
                            ("unsubscribe", "stop reply notifications for a thread")):
        c = command(name, help_text)
        c.add_argument("--session", required=True)
        c.add_argument("--thread", type=positive, required=True, metavar="ID")

    c = command("notifications", "list queued title/ID notices (never message bodies)")
    c.add_argument("--session", required=True)
    c.add_argument("--after", type=nonnegative, default=0, metavar="ID")
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    c = command("watch", "wait in this active turn for an outbox notice")
    c.add_argument("--session", required=True)
    c.add_argument("--timeout", type=positive, required=True, metavar="SEC")
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    c = command("read", "read board posts without changing the ack cursor")
    c.add_argument("--session")
    c.add_argument("--after", type=nonnegative, default=0, metavar="SEQ")
    c.add_argument("--topic")
    c.add_argument("--kind", choices=KINDS)
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")

    c = command("ack", "advance a session's explicit board cursor")
    c.add_argument("--session", required=True)
    c.add_argument("--through", type=nonnegative, required=True, metavar="SEQ")

    c = command("inbox", "read posts beyond a session's ack cursor")
    c.add_argument("--session", required=True)
    c.add_argument("--limit", type=positive, default=DEFAULT_LIMIT, metavar="N")
    c.add_argument("--json", action="store_true")
    return p


def main(argv: list[str], *, db_path: str, board_id: str, board_home: str,
         readonly: bool = False, disposed_notice_ids: set[int] | None = None) -> int:
    args = parser().parse_args(argv)
    args.disposed_notice_ids = disposed_notice_ids if disposed_notice_ids is not None else set()
    if hasattr(args, "limit") and args.limit > MAX_LIMIT:
        raise UserError(f"limit cannot exceed {MAX_LIMIT}")
    if args.command in SESSION_MUTATIONS:
        acting_session(args.session)
    if args.command in ("dispatch", "recover"):
        args.acting_session = acting_session(args.acting_session)
    profile = None
    if args.command in ("open", "reply") and not args.no_push or args.command == "dispatch":
        profile = sender_profile(args.sender_profile)
    with database(db_path, readonly=readonly) as conn:
        if not readonly:
            bind_board(conn, board_id)
        if args.command == "register":
            result = register(conn, args)
            print(f"registered {result['session']} ({result['status']})")
        elif args.command == "heartbeat":
            result = heartbeat(conn, args)
            print(f"heartbeat {result['session']} ({result['status']}) {result['last_seen_at']}")
        elif args.command == "leave":
            result = leave(conn, args)
            print(f"retired membership {result['session']} board={board_id}")
        elif args.command == "scope-transfer":
            result = scope_transfer(conn, args)
            print(f"independent membership {result['session']} board={board_id}")
        elif args.command == "sessions":
            result = sessions(conn, args)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif not result:
                print("(no sessions)")
            else:
                for item in result:
                    stale = " stale" if item["stale"] else ""
                    print(f"{item['session']} {item['status']}{stale} last-seen={item['last_seen_at']} "
                          f"campaign={item['campaign']} role={item['role']} ack={item['ack_seq']}")
                    if item["work"]:
                        for index, line in enumerate(item["work"].splitlines()):
                            print(f"  {'work: ' if index == 0 else '      '}{line}")
        elif args.command == "membership-events":
            query = "SELECT * FROM membership_events WHERE event_id>?"
            values: list[object] = [args.after]
            if args.session:
                query += " AND session=?"
                values.append(session_uuid(args.session))
            result = [{"board_id": board_id, **dict(row)} for row in conn.execute(
                query + " ORDER BY event_id LIMIT ?", (*values, args.limit))]
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                for item in result:
                    print(f"{board_id} membership-event=#{item['event_id']} {item['event']} "
                          f"session={item['session']} status={item['status']} route={item['route']}")
        elif args.command == "scope-transfers":
            query = "SELECT * FROM scope_transfers"
            values = ()
            if args.session:
                query += " WHERE session=?"
                values = (session_uuid(args.session),)
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                  "AND name='scope_transfers'").fetchone()
            result = ([{"board_id": board_id, **dict(row)} for row in conn.execute(
                query + " ORDER BY transfer_id", values)] if exists else [])
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                for item in result:
                    print(f"{board_id} scope-transfer=#{item['transfer_id']} "
                          f"session={item['session']} parent={item['parent_session']} "
                          f"scope={item['scope']} reason={item['reason']}")
        elif args.command == "post":
            print(post(conn, args))
            print("message-board: warning: flat post does not push; use open/reply for new "
                  "cross-slice questions", file=sys.stderr)
        elif args.command == "open":
            thread_id = open_thread(conn, args)
            print(thread_id, flush=True)
            if not args.no_push:
                dispatch_notices(conn, profile=profile, actor=session_uuid(args.session),
                                 board_id=board_id, board_home=board_home,
                                 limit=INLINE_FANOUT_LIMIT, post_seq=thread_id)
            complete = print_delivery_report(conn, thread_id, thread_id, board_id)
            if not complete and not args.no_push:
                return 1
        elif args.command == "reply":
            post_seq = reply_thread(conn, args)
            thread_id = args.thread
            print(post_seq, flush=True)
            if not args.no_push:
                dispatch_notices(conn, profile=profile, actor=session_uuid(args.session),
                                 board_id=board_id, board_home=board_home,
                                 limit=INLINE_FANOUT_LIMIT, post_seq=post_seq)
            complete = print_delivery_report(conn, thread_id, post_seq, board_id)
            if not complete and not args.no_push:
                return 1
        elif args.command == "dispatch":
            require_active_session(conn, args.acting_session)
            recipient = session_uuid(args.recipient) if args.recipient else None
            if recipient:
                require_session(conn, recipient)
            processed = dispatch_notices(conn, profile=profile, actor=args.acting_session,
                                         board_id=board_id, board_home=board_home,
                                         limit=args.limit,
                                         post_seq=args.post, thread_id=args.thread,
                                         recipient=recipient)
            print(f"dispatched={len(processed)}")
            touched = set(processed)
            if args.post is not None and not touched:
                row = conn.execute("SELECT thread_id FROM notification_outbox WHERE post_seq=?",
                                   (args.post,)).fetchone()
                if row:
                    touched.add((row[0], args.post))
            complete = True
            for thread_id, post_seq in sorted(touched):
                complete &= print_delivery_report(conn, thread_id, post_seq, board_id)
            if not complete:
                return 1
        elif args.command == "recover":
            require_active_session(conn, args.acting_session)
            print(f"recovered-ambiguous={recover_sending(conn, args)}")
        elif args.command == "attempts":
            result = attempts(conn, args.notification)
            result = [{"board_id": board_id, **item} for item in result]
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif not result:
                print("(no recorded attempts)")
            else:
                for item in result:
                    print(f"notice=#{item['notification_id']} attempt={item['attempt_number']} "
                          f"profile={item['profile'] or '-'} actor={item['acting_session'] or '-'} "
                          f"started={item['started_at']} finished={item['finished_at'] or '-'} "
                          f"result={item['result']} reason={item['reason']} "
                          f"recovered-by={item['recovered_by'] or '-'}")
        elif args.command == "ack-notice":
            item = ack_notice(conn, args)
            print(f"acknowledged notice={item['notification_id']} thread={item['thread_id']} "
                  f"session={item['session']}")
        elif args.command == "deliveries":
            result = deliveries(conn, args)
            result = [{"board_id": board_id, **item} for item in result]
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif not result:
                print("(no deliveries)")
            else:
                for item in result:
                    print(f"{board_id}#{item['notification_id']} {item['delivery_state']} "
                          f"thread=#{item['thread_id']} post=#{item['post_seq']} "
                          f"recipient={item['recipient']} route={item['route']} "
                          f"queue-id={item['queue_message_id'] or '-'} "
                          f"queued-at={item['queued_at'] or '-'} ack-at={item['acknowledged_at'] or '-'}")
        elif args.command == "threads":
            result = list_threads(conn, args)
            result = [{"board_id": board_id, **item} for item in result]
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif not result:
                print("(no threads)")
            else:
                for item in result:
                    print(f"{board_id}#{item['thread_id']} {item['created_at']} {item['title']} "
                          f"topic={item['topic']} opener={item['opener']} "
                          f"to={item['to']} latest=#{item['latest_seq']}")
        elif args.command in ("thread", "thread-read"):
            output_posts(read_thread(conn, args), args.json, board_id)
        elif args.command == "search":
            output_posts(search(conn, args), args.json, board_id)
        elif args.command == "subscribe":
            result = subscribe(conn, args)
            print(f"subscribed {result['session']} to thread #{result['thread_id']}")
        elif args.command == "unsubscribe":
            result = subscribe(conn, args, remove=True)
            print(f"unsubscribed {result['session']} from thread #{result['thread_id']}")
        elif args.command == "notifications":
            result = notifications(conn, args)
            result = [{"board_id": board_id, **item} for item in result]
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            elif not result:
                print("(no notifications)")
            else:
                for item in result:
                    print(f"board={board_id} #{item['notification_id']} {item['created_at']} "
                          f"{item['event']} thread=#{item['thread_id']} post=#{item['post_seq']} "
                          f"sender={item['sender']} title={item['title']}")
        elif args.command == "watch":
            require_active_session(conn, args.session)
            result = [safe_record(row) for row in active_listener.watch(
                conn, args.session, args.timeout, args.limit)]
            result = [{"board_id": board_id, **item} for item in result]
            if args.json:
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                for item in result:
                    print(f"board={board_id} #{item['notification_id']} {item['event']} "
                          f"thread=#{item['thread_id']} post=#{item['post_seq']} "
                          f"title={item['title']}")
            if not result:
                return 3
        elif args.command == "read":
            output_posts(read(conn, args), args.json, board_id)
        elif args.command == "ack":
            result = ack(conn, args)
            print(f"ack {result['session']} through {result['ack_seq']}")
        elif args.command == "inbox":
            output_posts(inbox(conn, args), args.json, board_id)
    return 0
