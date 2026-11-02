import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
MAINTENANCE = HERE / "maintenance.py"
HANDOVER = HERE / "handover.py"


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True)


class SessionMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "opencode.db"
        with closing(sqlite3.connect(self.db)) as connection:
            connection.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE account(id TEXT PRIMARY KEY, credential TEXT);
                CREATE TABLE project(id TEXT PRIMARY KEY, name TEXT);
                CREATE TABLE workspace(id TEXT PRIMARY KEY, project_id TEXT REFERENCES project(id));
                CREATE TABLE session(id TEXT PRIMARY KEY, project_id TEXT REFERENCES project(id));
                CREATE TABLE message(id TEXT PRIMARY KEY, session_id TEXT REFERENCES session(id), body BLOB);
                CREATE TABLE part(id TEXT PRIMARY KEY, message_id TEXT REFERENCES message(id), body BLOB);
                CREATE TABLE session_note(id TEXT PRIMARY KEY, part_id TEXT REFERENCES part(id));
                CREATE TABLE event(id TEXT PRIMARY KEY, aggregate_id TEXT, body TEXT);
                CREATE TABLE event_sequence(aggregate_id TEXT PRIMARY KEY, value INTEGER);
                INSERT INTO account VALUES('acc_1', 'private-credential');
                INSERT INTO project VALUES('prj_1', 'important project');
                INSERT INTO workspace VALUES('wrk_1', 'prj_1');
                INSERT INTO session VALUES('ses_1', 'prj_1');
                INSERT INTO message VALUES('msg_1', 'ses_1', zeroblob(4194304));
                INSERT INTO part VALUES('prt_1', 'msg_1', zeroblob(4194304));
                INSERT INTO session_note VALUES('note_1', 'prt_1');
                INSERT INTO event VALUES('evt_s', 'ses_1', 'private-session-event');
                INSERT INTO event VALUES('evt_p', 'prj_1', 'project-event');
                INSERT INTO event_sequence VALUES('ses_1', 3);
                INSERT INTO event_sequence VALUES('prj_1', 5);
            """)

    def test_inventory_and_explicit_reset_preserve_unrelated_rows_and_compact(self):
        receipt = self.root / "receipt.jsonl"
        inventory = run(MAINTENANCE, "inventory", "--db", self.db)
        self.assertEqual(inventory.returncode, 0, inventory.stderr)
        self.assertEqual(json.loads(inventory.stdout)["session_rows"]["session"], 1)
        self.assertNotIn("private-credential", inventory.stdout)
        self.assertNotIn("private-session-event", inventory.stdout)
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM session").fetchone()[0], 1)
        incomplete = run(MAINTENANCE, "reset", "--db", self.db, "--receipt", receipt,
                         "--full-sessions", "--apply")
        self.assertEqual(incomplete.returncode, 2)
        self.assertFalse(receipt.exists())
        applied = run(MAINTENANCE, "reset", "--db", self.db, "--receipt", receipt,
                      "--full-sessions", "--apply", "--exclusive-maintenance")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        result = json.loads(applied.stdout)
        self.assertGreater(result["allocated_bytes_reclaimed"], 0)
        self.assertEqual(result["quick_check"], "ok")
        with closing(sqlite3.connect(self.db)) as connection:
            for table in ("session", "message", "part", "session_note"):
                self.assertEqual(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT credential FROM account").fetchone()[0],
                             "private-credential")
            self.assertEqual(connection.execute("SELECT name FROM project").fetchone()[0],
                             "important project")
            self.assertEqual(connection.execute("SELECT count(*) FROM workspace").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT body FROM event").fetchone()[0], "project-event")
            self.assertEqual(connection.execute("SELECT aggregate_id FROM event_sequence").fetchone()[0], "prj_1")
            self.assertEqual(connection.execute("PRAGMA freelist_count").fetchone()[0], 0)
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual([json.loads(line)["phase"] for line in receipt.read_text().splitlines()],
                         ["intent", "rows_committed", "complete"])
        self.assertNotIn("private-credential", receipt.read_text())
        replay = run(MAINTENANCE, "reset", "--db", self.db, "--receipt", receipt,
                     "--full-sessions", "--apply", "--exclusive-maintenance")
        self.assertEqual(replay.returncode, 2)

    def test_open_consumer_refuses_reset(self):
        holder = subprocess.Popen(
            [sys.executable, "-c", "import sys; f=open(sys.argv[1], 'rb'); print('ready', flush=True); sys.stdin.read()", str(self.db)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: holder.kill() if holder.poll() is None else None)
        self.addCleanup(holder.stdout.close)
        self.assertEqual(holder.stdout.readline().strip(), "ready")
        receipt = self.root / "busy.jsonl"
        result = run(MAINTENANCE, "reset", "--db", self.db, "--receipt", receipt,
                     "--full-sessions", "--apply", "--exclusive-maintenance")
        self.assertEqual(result.returncode, 2)
        self.assertIn("open consumer", result.stderr)
        self.assertFalse(receipt.exists())
        holder.stdin.close()
        holder.wait(timeout=5)

    def test_running_opencode_named_process_refuses_reset(self):
        holder = subprocess.Popen(
            [sys.executable, "-c",
             "import ctypes,sys; ctypes.CDLL(None).prctl(15,b'opencode',0,0,0); "
             "print('ready',flush=True); sys.stdin.read()"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: holder.kill() if holder.poll() is None else None)
        self.addCleanup(holder.stdout.close)
        self.assertEqual(holder.stdout.readline().strip(), "ready")
        receipt = self.root / "running.jsonl"
        result = run(MAINTENANCE, "reset", "--db", self.db, "--receipt", receipt,
                     "--full-sessions", "--apply", "--exclusive-maintenance")
        self.assertEqual(result.returncode, 2)
        self.assertIn("OpenCode is running", result.stderr)
        self.assertFalse(receipt.exists())
        holder.stdin.close()
        holder.wait(timeout=5)

    def test_wal_database_compacts_and_preserves_project(self):
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
        receipt = self.root / "wal.jsonl"
        result = run(MAINTENANCE, "reset", "--db", self.db, "--receipt", receipt,
                     "--full-sessions", "--apply", "--exclusive-maintenance")
        self.assertEqual(result.returncode, 0, result.stderr)
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("SELECT name FROM project").fetchone()[0],
                             "important project")
            self.assertEqual(connection.execute("PRAGMA freelist_count").fetchone()[0], 0)

    def test_protected_foreign_key_closure_refuses(self):
        with closing(sqlite3.connect(self.db)) as connection:
            connection.execute("CREATE TABLE account_session(id TEXT, session_id TEXT REFERENCES session(id))")
        result = run(MAINTENANCE, "inventory", "--db", self.db)
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected", result.stderr)

    def test_symlinked_database_and_capture_namespace_refuse(self):
        linked = self.root / "linked"
        linked.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(run(MAINTENANCE, "inventory", "--db", linked / "opencode.db").returncode, 2)
        capture = self.root / "Source"
        capture.mkdir()
        (capture / "opencode.db").symlink_to(self.db)
        result = run(MAINTENANCE, "inventory", "--db", capture / "opencode.db")
        self.assertEqual(result.returncode, 2)
        self.assertIn("protected Source/capture", result.stderr)

    def test_handover_requires_distinct_owner_milestones(self):
        directory = self.root / "handover"
        summary = self.root / "owner-summary.md"
        self.assertEqual(run(HANDOVER, "request", "--dir", directory,
                             "--old-label", "old interactive").returncode, 0)
        self.assertEqual(json.loads((directory / "state.json").read_text())["phase"], "request_prepared")
        self.assertEqual(run(HANDOVER, "adopted", "--dir", directory,
                             "--replacement-label", "new", "--owner-confirmed").returncode, 2)
        self.assertEqual(run(HANDOVER, "queued", "--dir", directory, "--owner-confirmed").returncode, 0)
        self.assertEqual(run(HANDOVER, "summary", "--dir", directory,
                             "--summary", summary, "--owner-confirmed").returncode, 2)
        summary.write_text("Owner-written current state and next actions\n")
        self.assertEqual(run(HANDOVER, "summary", "--dir", directory,
                             "--summary", summary, "--owner-confirmed").returncode, 0)
        self.assertEqual(run(HANDOVER, "adopted", "--dir", directory,
                             "--replacement-label", "new", "--owner-confirmed").returncode, 0)
        self.assertEqual(run(HANDOVER, "closed", "--dir", directory,
                             "--owner-confirmed").returncode, 0)
        self.assertEqual(json.loads((directory / "state.json").read_text())["phase"], "old_session_closed")
        self.assertEqual(run(HANDOVER, "closed", "--dir", directory,
                             "--owner-confirmed").returncode, 2)

    def test_native_store_refusal_precedes_any_metadata_lookup(self):
        code = """
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import maintenance
for prefix in ('.local/state/agent-bash', '.local/share/oulipoly-agent-runner',
               '.local/state/../state/agent-bash'):
    with patch.object(Path, 'lstat', side_effect=AssertionError('metadata accessed')):
        try:
            maintenance.db_path(Path.home() / prefix / 'opencode.db')
        except RuntimeError as error:
            assert 'protected native' in str(error)
        else:
            raise AssertionError('native path accepted')
"""
        checked = subprocess.run([sys.executable, "-c", code, str(HERE)],
                                 capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        native = Path.home() / '.local/state/agent-bash/new-handover'
        refused = run(HANDOVER, "status", "--dir", native)
        self.assertEqual(refused.returncode, 2)
        self.assertIn('protected native', refused.stderr)

    def test_handover_rejects_symlinked_directory_and_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual = root / "actual"
            actual.mkdir()
            alias = root / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            refused = run(HANDOVER, "request", "--dir", alias / "new",
                          "--old-label", "test")
            self.assertEqual(refused.returncode, 2)
            self.assertFalse((actual / "new").exists())
            outside = root / "outside.json"
            outside.write_text('{"phase":"request_prepared"}')
            (actual / "state.json").symlink_to(outside)
            self.assertEqual(run(HANDOVER, "status", "--dir", actual).returncode, 2)


if __name__ == "__main__":
    unittest.main()
