"""Local catalog for independent, file-backed message boards.

Catalog reads never open a board database. In particular, registering a legacy
RFQ path cannot migrate or otherwise write that database.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import sqlite3
import stat
import uuid


ALIAS = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
ARTIFACT_TYPES = frozenset({"repository", "project", "epic", "campaign", "company", "session", "other"})
STATES = ("pending_migration", "migrating", "active", "retired", "archived",
          "purging", "tombstoned")

BOARDS_DDL = """CREATE TABLE {name} (
    board_id TEXT PRIMARY KEY, alias TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('pending_migration','migrating','active',
                                         'retired','archived','purging','tombstoned')),
    db_path TEXT NOT NULL UNIQUE, temporary_test INTEGER NOT NULL DEFAULT 0,
    purge_allowed INTEGER NOT NULL DEFAULT 0, retention_hold INTEGER NOT NULL DEFAULT 0,
    membership_policy TEXT NOT NULL DEFAULT 'open' CHECK(membership_policy IN ('open','invited')),
    allowed_routes TEXT NOT NULL DEFAULT 'queue,managed',
    created_at TEXT NOT NULL, changed_at TEXT NOT NULL,
    snapshot_path TEXT, snapshot_sha256 TEXT, purged_at TEXT,
    migration_backup TEXT, migration_sha256 TEXT
)"""


class CatalogError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def home_path(explicit: str | None = None) -> Path:
    value = explicit or os.environ.get("MESSAGE_BOARD_HOME")
    if value:
        path = Path(value).expanduser()
    else:
        path = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "message-board"
    if not path.is_absolute():
        raise CatalogError("board home must be an absolute path")
    return path.resolve()


def canonical_uuid(value: str) -> str:
    try:
        parsed = str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise CatalogError("board ID must be a UUID") from None
    if value != parsed:
        raise CatalogError("board ID must be a canonical UUID")
    return parsed


@contextmanager
def catalog(home: Path):
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    if stat.S_IMODE(home.stat().st_mode) & 0o077:
        raise CatalogError("board home must be private; choose a dedicated directory with mode 700")
    path = home / "catalog.sqlite3"
    if not path.exists():
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        except FileExistsError:
            pass
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
        """ + BOARDS_DDL.format(name="IF NOT EXISTS boards") + ";" + """
            CREATE TABLE IF NOT EXISTS artifact_links (
                board_id TEXT NOT NULL REFERENCES boards(board_id),
                artifact_type TEXT NOT NULL,
                identifier TEXT NOT NULL,
                linked_at TEXT NOT NULL,
                PRIMARY KEY(board_id, artifact_type, identifier)
            );
            CREATE INDEX IF NOT EXISTS artifact_to_boards
                ON artifact_links(artifact_type, identifier, board_id);
            CREATE TABLE IF NOT EXISTS invitations (
                board_id TEXT NOT NULL REFERENCES boards(board_id),
                session TEXT NOT NULL,
                invited_at TEXT NOT NULL,
                PRIMARY KEY(board_id, session)
            );
            CREATE TABLE IF NOT EXISTS changes (
                change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id TEXT NOT NULL REFERENCES boards(board_id),
                event TEXT NOT NULL,
                detail TEXT NOT NULL,
                happened_at TEXT NOT NULL
            );
        """)
        definition = conn.execute("SELECT sql FROM sqlite_master WHERE name='boards'").fetchone()[0]
        if "pending_migration" not in definition:
            # Older catalogs have a restrictive state CHECK. Rebuild atomically before
            # any caller can publish the new lifecycle states.
            conn.execute("PRAGMA foreign_keys=OFF")
            try:
                conn.execute("BEGIN EXCLUSIVE")
                conn.execute(BOARDS_DDL.format(name="boards_new"))
                columns = [row[1] for row in conn.execute("PRAGMA table_info(boards)")]
                names = ",".join(columns)
                conn.execute(f"INSERT INTO boards_new ({names}) SELECT {names} FROM boards")
                conn.execute("DROP TABLE boards")
                conn.execute("ALTER TABLE boards_new RENAME TO boards")
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("""CREATE TABLE IF NOT EXISTS notice_dispositions (
            board_id TEXT NOT NULL REFERENCES boards(board_id),
            notification_id INTEGER NOT NULL,
            delivery_state TEXT NOT NULL,
            reason TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            PRIMARY KEY(board_id,notification_id)
        )""")
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise CatalogError("catalog foreign key check failed")
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise


def record(conn: sqlite3.Connection, board_id: str, event: str, detail: str = ""):
    conn.execute("INSERT INTO changes(board_id,event,detail,happened_at) VALUES(?,?,?,?)",
                 (board_id, event, detail, now()))


def board(conn: sqlite3.Connection, key: str) -> dict:
    row = conn.execute("SELECT * FROM boards WHERE board_id=? OR alias=?", (key, key)).fetchone()
    if row is None:
        raise CatalogError("unknown board ID or alias")
    return dict(row)


def create(conn: sqlite3.Connection, home: Path, alias: str, display_name: str, *,
           db_path: str | None = None, temporary_test: bool = False,
           membership_policy: str = "open", board_id: str | None = None,
           initialized_new_file: bool = False, allowed_routes: str = "queue,managed") -> dict:
    if not ALIAS.fullmatch(alias):
        raise CatalogError("alias must be lowercase letters, digits and internal hyphens")
    if (not display_name.strip() or len(display_name) > 160 or
            any(ord(char) < 32 or ord(char) == 127 for char in display_name)):
        raise CatalogError("display name must contain 1 to 160 characters")
    if membership_policy not in ("open", "invited"):
        raise CatalogError("membership policy must be open or invited")
    if allowed_routes not in ("queue", "managed", "queue,managed"):
        raise CatalogError("allowed routes must be queue, managed or both")
    ident = canonical_uuid(board_id) if board_id else str(uuid.uuid4())
    supplied_path = Path(db_path).expanduser() if db_path else home / "boards" / f"{ident}.sqlite3"
    if not supplied_path.is_absolute():
        raise CatalogError("board database path must be absolute")
    if supplied_path.is_symlink():
        raise CatalogError("board database path cannot be a symlink")
    path = supplied_path.resolve()
    if db_path is None and path.exists():
        raise CatalogError("new board database path already exists")
    if db_path is not None and not path.is_file():
        raise CatalogError("registered board database must already exist")
    version = None
    if db_path is not None:
        with path.open("rb") as existing:
            if existing.read(16) != b"SQLite format 3\x00":
                raise CatalogError("registered board path is not a SQLite database")
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
            version = source.execute("PRAGMA user_version").fetchone()[0]
            if version not in (3, 4):
                raise CatalogError("registered board must have schema 3 or 4")
            if version == 4:
                meta = source.execute("SELECT board_id FROM board_meta").fetchall()
                if len(meta) != 1 or meta[0][0] != ident:
                    raise CatalogError("schema-4 board is already bound to another ID")
    if path == home / "catalog.sqlite3":
        raise CatalogError("board database cannot be the catalog")
    stamp = now()
    with transaction(conn):
        identity = path.stat() if path.exists() else None
        for row in conn.execute("SELECT db_path FROM boards"):
            other = Path(row[0])
            if other.resolve() == path:
                raise CatalogError("board database path was already registered")
            try:
                existing = other.stat()
            except FileNotFoundError:
                continue
            if identity and (existing.st_dev, existing.st_ino) == (identity.st_dev, identity.st_ino):
                raise CatalogError("board database file is already registered through another path")
        try:
            conn.execute("""INSERT INTO boards
                (board_id,alias,display_name,state,db_path,temporary_test,purge_allowed,
                 membership_policy,allowed_routes,created_at,changed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (ident, alias, display_name,
                 "pending_migration" if version == 3 else "active", str(path), int(temporary_test),
                 int(temporary_test), membership_policy, allowed_routes, stamp, stamp))
        except sqlite3.IntegrityError as exc:
            raise CatalogError("board ID, alias or database path was already used") from exc
        record(conn, ident, "created" if db_path is None or initialized_new_file else "registered",
               str(path))
    return board(conn, ident)


def links(conn: sqlite3.Connection, board_id: str) -> list[dict]:
    return [dict(row) for row in conn.execute(
        "SELECT artifact_type,identifier,linked_at FROM artifact_links WHERE board_id=? "
        "ORDER BY artifact_type,identifier", (board_id,))]


def artifact_identifier(kind: str, identifier: str) -> str:
    if kind not in ARTIFACT_TYPES or not isinstance(identifier, str):
        raise CatalogError("invalid artifact type or identifier")
    if not identifier or identifier != identifier.strip() or len(identifier) > 1024 or any(
            ord(char) < 32 or ord(char) == 127 for char in identifier):
        raise CatalogError("artifact identifier must be a canonical nonempty string")
    if kind == "session":
        return canonical_uuid(identifier)
    if kind == "repository" and identifier.startswith("/"):
        return str(Path(identifier).resolve())
    if kind == "repository" and not identifier.startswith("https://"):
        raise CatalogError("repository identifier must be an absolute path or HTTPS URL")
    return identifier


def associate(conn: sqlite3.Connection, key: str, kind: str, identifier: str, *, remove=False):
    entry = board(conn, key)
    if entry["state"] not in ("active", "retired"):
        raise CatalogError("only active or retired boards can change links")
    identifier = artifact_identifier(kind, identifier)
    with transaction(conn):
        if remove:
            cur = conn.execute("DELETE FROM artifact_links WHERE board_id=? AND artifact_type=? "
                               "AND identifier=?", (entry["board_id"], kind, identifier))
            if cur.rowcount == 0:
                raise CatalogError("artifact link does not exist")
        else:
            conn.execute("INSERT OR IGNORE INTO artifact_links VALUES(?,?,?,?)",
                         (entry["board_id"], kind, identifier, now()))
        record(conn, entry["board_id"], "disassociated" if remove else "associated",
               f"{kind}:{identifier}")


@contextmanager
def lifecycle_lock(entry: dict, home: Path, *, exclusive: bool):
    path = home / "locks" / f"{entry['board_id']}.lock"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
