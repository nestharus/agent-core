#!/usr/bin/env python3
"""Metadata-only OpenCode session inventory and explicitly selected full reset."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import subprocess
import sys


BASE = {"session", "message", "part"}
EVENTS = {"event", "event_sequence"}
PROTECTED = re.compile(
    r"project|workspace|account|credential|auth|config|setting|"
    r"permission|user|provider|model|key|token|secret", re.I
)


def fail(message):
    raise RuntimeError(message)


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def db_path(raw):
    path = Path(raw).absolute()
    if path.name != "opencode.db" or ".." in path.parts:
        fail("select a direct opencode.db path")
    if any(part.lower() in {"source", "capture", "captures"} for part in path.parts):
        fail("protected Source/capture namespace is outside this tool")
    parent = Path("/")
    for component in path.parts[1:-1]:
        parent /= component
        if not stat.S_ISDIR(parent.lstat().st_mode):
            fail("database path has a symlinked or non-directory parent")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
        fail("database must be an owned, regular, single-link file (no symlink)")
    for companion in (Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        try:
            companion_info = companion.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISREG(companion_info.st_mode) or companion_info.st_nlink != 1
                or companion_info.st_uid != os.getuid()):
            fail("database companion must be an owned, regular, single-link file")
    return path, (info.st_dev, info.st_ino)


def allocated(path):
    return sum(
        p.lstat().st_blocks * 512 for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"))
        if p.exists()
    )


def assert_idle(path, allow_self=False):
    if not shutil.which("pgrep") or not shutil.which("fuser"):
        fail("pgrep and fuser are required for a reset")
    running = subprocess.run(["pgrep", "-x", "opencode"], capture_output=True, check=False)
    if running.returncode not in (0, 1):
        fail("cannot determine whether OpenCode is running")
    if running.returncode == 0:
        fail("OpenCode is running; reset refused")
    paths = [str(p) for p in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")) if p.exists()]
    users = subprocess.run(["fuser", *paths], capture_output=True, check=False)
    if users.returncode not in (0, 1):
        fail("cannot determine database consumers")
    pids = {int(value) for value in re.findall(rb"\b\d+\b", users.stdout)}
    if allow_self:
        pids.discard(os.getpid())
    if pids:
        fail("database has an open consumer; reset refused")


def connect(path, write=False):
    mode = "rw" if write else "ro"
    connection = sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=2)
    connection.execute("PRAGMA busy_timeout=2000")
    if not write:
        connection.execute("PRAGMA query_only=ON")
    return connection


def inspect(connection):
    rows = connection.execute(
        "SELECT name, type, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    tables = {name for name, kind, _, _ in rows if kind == "table"}
    if not BASE <= tables:
        fail("unsupported OpenCode session schema: session/message/part missing")
    foreign = {
        table: {row[2] for row in connection.execute("PRAGMA foreign_key_list(" + quoted(table) + ")")}
        for table in tables
    }
    selected = set(BASE)
    while True:
        more = {table for table in tables - selected - EVENTS if foreign[table] & selected}
        if not more:
            break
        selected |= more
    if any(PROTECTED.search(table) for table in selected):
        fail("session foreign-key closure reaches protected non-session table")
    if any(foreign[table] & selected for table in tables & EVENTS):
        fail("event table has a session foreign key; unsupported schema")
    if any(foreign[table] & EVENTS for table in tables - EVENTS):
        fail("event table has dependent rows; unsupported schema")
    if any(kind == "trigger" and owner in selected | EVENTS for _, kind, owner, _ in rows):
        fail("session/event trigger requires separate schema review")
    for table in tables & EVENTS:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(" + quoted(table) + ")")}
        if "aggregate_id" not in columns:
            fail("event table lacks aggregate_id")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        fail("database has existing foreign-key violations")
    counts = {table: connection.execute("SELECT COUNT(*) FROM " + quoted(table)).fetchone()[0]
              for table in sorted(selected)}
    event_counts = {
        table: connection.execute(
            "SELECT COUNT(*) FROM " + quoted(table)
            + " WHERE aggregate_id GLOB 'ses_*' OR aggregate_id IN (SELECT id FROM session)"
        ).fetchone()[0]
        for table in sorted(tables & EVENTS)
    }
    protected_counts = {
        table: connection.execute("SELECT COUNT(*) FROM " + quoted(table)).fetchone()[0]
        for table in sorted(tables - selected - EVENTS)
    }
    schema = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    return {"session_tables": sorted(selected), "session_rows": counts,
            "session_event_rows": event_counts, "other_table_rows": protected_counts,
            "schema_sha256": schema}


def write_receipt(stream, phase, **fields):
    stream.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(),
                             "phase": phase, **fields}, sort_keys=True) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def reset(path, identity, receipt_path):
    assert_idle(path)
    if shutil.disk_usage(path.parent).free < path.stat().st_size + 64 * 1024 * 1024:
        fail("insufficient free space for SQLite VACUUM")
    connection = connect(path, write=True)
    receipt = None
    try:
        connection.execute("PRAGMA locking_mode=EXCLUSIVE")
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN EXCLUSIVE")
        if db_path(path)[1] != identity:
            fail("database identity changed")
        assert_idle(path, allow_self=True)
        before = inspect(connection)
        receipt_fd = os.open(receipt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        receipt = os.fdopen(receipt_fd, "w")
        write_receipt(receipt, "intent", database=str(path), identity=identity,
                      schema_sha256=before["schema_sha256"],
                      session_rows=before["session_rows"],
                      session_event_rows=before["session_event_rows"])
        bytes_before = allocated(path)
        for table in sorted(before["session_event_rows"]):
            connection.execute(
                "DELETE FROM " + quoted(table)
                + " WHERE aggregate_id GLOB 'ses_*' OR aggregate_id IN (SELECT id FROM session)"
            )
        for table in sorted(set(before["session_tables"]) - {"session"}):
            connection.execute("DELETE FROM " + quoted(table))
        connection.execute('DELETE FROM "session"')
        connection.commit()
        write_receipt(receipt, "rows_committed")
        connection.execute("VACUUM")
        checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint and checkpoint[0] != 0:
            fail("WAL checkpoint could not complete")
        connection.execute("PRAGMA foreign_keys=ON")
        after = inspect(connection)
        if any(after["session_rows"].values()) or any(after["session_event_rows"].values()):
            fail("session rows remain after reset")
        if before["other_table_rows"] != after["other_table_rows"]:
            fail("non-session table row counts changed")
        if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            fail("SQLite quick_check failed")
        bytes_after = allocated(path)
        result = {"database": str(path), "session_rows_removed": before["session_rows"],
                  "session_event_rows_removed": before["session_event_rows"],
                  "other_table_counts_unchanged": True, "quick_check": "ok",
                  "allocated_bytes_before": bytes_before, "allocated_bytes_after": bytes_after,
                  "allocated_bytes_reclaimed": max(0, bytes_before - bytes_after)}
        write_receipt(receipt, "complete", **result)
        return result
    except BaseException as error:
        if connection.in_transaction:
            connection.rollback()
        if receipt is not None:
            write_receipt(receipt, "error", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        connection.close()
        if receipt is not None:
            receipt.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser("inventory", help="read session metadata only")
    inventory.add_argument("--db", required=True)
    apply = sub.add_parser("reset", help="explicit full OpenCode session reset")
    apply.add_argument("--db", required=True)
    apply.add_argument("--receipt", required=True, help="new JSONL receipt path")
    apply.add_argument("--full-sessions", action="store_true")
    apply.add_argument("--apply", action="store_true")
    apply.add_argument("--exclusive-maintenance", action="store_true")
    args = parser.parse_args()
    try:
        path, identity = db_path(args.db)
        if args.command == "inventory":
            with connect(path) as connection:
                print(json.dumps({"database": str(path), "identity": identity,
                                  "allocated_bytes": allocated(path), **inspect(connection)}, sort_keys=True))
        else:
            if not (args.full_sessions and args.apply and args.exclusive_maintenance):
                fail("reset requires --full-sessions --apply --exclusive-maintenance")
            print(json.dumps(reset(path, identity, Path(args.receipt).absolute()), sort_keys=True))
    except (OSError, sqlite3.Error, RuntimeError) as error:
        print(f"session-maintenance: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
