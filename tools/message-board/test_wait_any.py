"""Temporary two-board feed and foreground child integration tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import catalog
import multi_board_watch


HERE = Path(__file__).parent
SESSION = "11111111-1111-4111-8111-111111111111"
AUTHOR = "22222222-2222-4222-8222-222222222222"


class WaitAnyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "boards"
        self.one = self.board("first")
        self.two = self.board("second")
        for board in (self.one, self.two):
            self.cli("--board", board["board_id"], "register", "--session", SESSION,
                     "--role", "watcher", actor=SESSION)
            self.cli("--board", board["board_id"], "register", "--session", AUTHOR,
                     "--role", "writer", actor=AUTHOR)

    def cli(self, *args, actor=None, expected=0):
        env = os.environ.copy()
        env.pop("CODEX_SESSION_ID", None)
        if actor:
            env["CODEX_SESSION_ID"] = actor
        result = subprocess.run([sys.executable, str(HERE / "board.py"), "--home",
                                 str(self.home), *map(str, args)], capture_output=True,
                                text=True, env=env, timeout=15)
        self.assertEqual(result.returncode, expected, (result.stdout, result.stderr))
        return result

    def board(self, alias):
        return json.loads(self.cli("boards", "create", "--alias", alias, "--name", alias,
                                   "--temporary-test", "--json").stdout)

    def notice(self, board):
        self.cli("--board", board["board_id"], "open", "--session", AUTHOR,
                 "--topic", "work", "--title", "Notice", "--text", "Body",
                 "--no-push", actor=AUTHOR)

    def feed(self, *keys, all_joined=False):
        os.environ["CODEX_SESSION_ID"] = SESSION
        self.addCleanup(os.environ.pop, "CODEX_SESSION_ID", None)
        return multi_board_watch.BoardFeed(self.home, SESSION, list(keys),
                                            all_joined=all_joined)

    def test_event_orders_and_exact_board_ids(self):
        with self.feed("second", self.one["board_id"]) as feed:
            self.notice(self.two)
            self.notice(self.one)
            first = feed.wait(1)
            self.assertEqual([row["board_id"] for row in first],
                             [self.two["board_id"], self.one["board_id"]])
            self.assertEqual([(row["notification_id"], row["thread_id"], row["post_seq"])
                              for row in first], [(1, 1, 1), (1, 1, 1)])
            self.notice(self.one)
            self.assertEqual([row["board_id"] for row in feed.wait(1)], [self.one["board_id"]])
            self.assertEqual(feed.scan(), [])

    def test_lost_hint_and_all_joined(self):
        os.environ["CODEX_SESSION_ID"] = SESSION
        self.addCleanup(os.environ.pop, "CODEX_SESSION_ID", None)
        ready = threading.Event()
        result = []

        def waiting():
            try:
                with multi_board_watch.BoardFeed(self.home, SESSION, all_joined=True) as feed:
                    ready.set()  # both sockets are bound and initial setup completed
                    result.append(feed.wait(4))
            except BaseException as exc:
                result.append(exc)
                ready.set()

        thread = threading.Thread(target=waiting)
        thread.start()
        self.assertTrue(ready.wait(2))
        self.assertEqual(result, [])
        # Direct durable insert emits no socket hint. The timed rescan finds it.
        with sqlite3.connect(self.one["db_path"]) as db:
            db.execute("""INSERT INTO posts(author,recipient,topic,kind,text,created_at)
                          VALUES(?,?,?,?,?,?)""", (AUTHOR, SESSION, "work", "status", "body",
                                               catalog.now()))
            seq = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute("INSERT INTO threads(thread_id,title,topic,opener,created_at) "
                       "VALUES(?,?,?,?,?)", (seq, "Lost hint", "work", AUTHOR, catalog.now()))
            db.execute("INSERT INTO thread_posts VALUES(?,?)", (seq, seq))
            db.execute("""INSERT INTO notification_outbox
                (recipient,thread_id,post_seq,event,title,sender,created_at,state_changed_at,
                 route,delivery_state) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (SESSION, seq, seq, "open", "Lost hint", AUTHOR, catalog.now(),
                 catalog.now(), "queue", "pending"))
        thread.join(6)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(result[0], list, result[0])
        self.assertEqual(result[0][0]["board_id"], self.one["board_id"])

    def test_expiry_leave_retire_archive_and_conflict(self):
        with self.feed("first", "second") as feed:
            with self.assertRaisesRegex(multi_board_watch.WatchError, "listener conflict"):
                with self.feed("first"):
                    pass
            self.cli("--board", self.one["board_id"], "leave", "--session", SESSION,
                     actor=SESSION)
            with self.assertRaisesRegex(multi_board_watch.WatchError, "active, unexpired"):
                feed.scan()
        with self.assertRaisesRegex(multi_board_watch.WatchError, "active unexpired"):
            with self.feed("first"):
                pass
        # Retired boards cannot produce a fresh wake, including from old outbox rows.
        with self.feed("second") as feed:
            self.notice(self.two)
            self.cli("boards", "dispose-notices", "--board", "second", "--notice-id", "1",
                     "--reason", "Watcher test retires with pending pointer")
            self.cli("boards", "retire", "--board", "second")
            with self.assertRaisesRegex(multi_board_watch.WatchError, "no longer active"):
                feed.scan()
        with self.assertRaisesRegex(multi_board_watch.WatchError, "not active"):
            with self.feed("second"):
                pass
        self.cli("boards", "archive", "--board", "second")
        with self.assertRaisesRegex(multi_board_watch.WatchError, "not active"):
            with self.feed("second"):
                pass

    def test_all_joined_skips_unrelated_legacy_before_schema_validation(self):
        legacy = Path(self.temp.name) / "unrelated.sqlite3"
        with sqlite3.connect(legacy) as db:
            db.execute("CREATE TABLE sessions(session TEXT PRIMARY KEY,status TEXT)")
            db.execute("PRAGMA user_version=3")
        self.cli("boards", "register-path", "--alias", "unrelated", "--name", "Unrelated",
                 "--db", legacy)
        with self.feed(all_joined=True) as feed:
            self.assertEqual(len(feed.boards), 2)
        # An older catalog could still mark a legacy board active. Nonmembers
        # must be skipped before its missing schema-4 metadata is inspected.
        with catalog.catalog(self.home) as db, catalog.transaction(db):
            db.execute("UPDATE boards SET state='active' WHERE alias='unrelated'")
        with self.feed(all_joined=True) as feed:
            self.assertEqual(len(feed.boards), 2)
        with sqlite3.connect(legacy) as db:
            db.execute("INSERT INTO sessions VALUES(?, 'active')", (SESSION,))
        with self.assertRaisesRegex(multi_board_watch.WatchError, "requires migration"):
            with self.feed(all_joined=True):
                pass

    def test_expired_membership_and_binding(self):
        with sqlite3.connect(self.one["db_path"]) as db:
            db.execute("UPDATE sessions SET expires_at=? WHERE session=?",
                       ("2000-01-01T00:00:00.000000Z", SESSION))
        with self.assertRaisesRegex(multi_board_watch.WatchError, "active unexpired"):
            with self.feed("first"):
                pass
        with sqlite3.connect(self.two["db_path"]) as db:
            db.execute("UPDATE board_meta SET board_id=?", (self.one["board_id"],))
        with self.assertRaisesRegex(multi_board_watch.WatchError, "ID binding"):
            with self.feed("second"):
                pass

    def test_deleted_board_file_fails_closed(self):
        with self.feed("first") as feed:
            Path(self.one["db_path"]).unlink()
            with self.assertRaisesRegex(multi_board_watch.WatchError, "unavailable"):
                feed.scan()

    def test_child_output_and_exit_with_board_notice(self):
        log = Path(self.temp.name) / "child.log"
        env = {**os.environ, "CODEX_SESSION_ID": SESSION}
        command = [sys.executable, str(HERE / "wait_any.py"), "--home", str(self.home),
                   "--session", SESSION, "--board", "first", "--board", "second",
                   "run", "--log", str(log), "--", sys.executable, "-c",
                   "import os,sys,time; print('start', os.environ.get('CODEX_SESSION_ID')); sys.stdout.flush(); "
                   "time.sleep(0.5); sys.stderr.buffer.write(b'\\x00err\\xff'); "
                   "sys.stderr.flush(); time.sleep(0.5); print('done'); sys.exit(7)"]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env)
        time.sleep(0.25)
        self.notice(self.two)
        stdout, stderr = proc.communicate(timeout=15)
        self.assertEqual(proc.returncode, 7, stderr)
        frames = [json.loads(line.split(b" ", 1)[1]) for line in stdout.splitlines()]
        self.assertTrue(any(row["event"] == "BOARD" and
                            row["board_id"] == self.two["board_id"] for row in frames))
        self.assertEqual(frames[-1]["event"], "EXIT")
        self.assertEqual(frames[-1]["returncode"], 7)
        records = []
        data = log.read_bytes()
        at = 0
        while at < len(data):
            stream = data[at:at + 1]
            size = struct.unpack("!I", data[at + 1:at + 5])[0]
            records.append((stream, data[at + 5:at + 5 + size]))
            at += 5 + size
        self.assertEqual(b"".join(chunk for stream, chunk in records if stream == b"O"),
                         b"start None\ndone\n")
        self.assertEqual(b"".join(chunk for stream, chunk in records if stream == b"E"),
                         b"\x00err\xff")
        self.assertEqual(json.loads(Path(str(log) + ".status.json").read_text()),
                         {"returncode": 7, "log_offset": len(data)})


if __name__ == "__main__":
    unittest.main()
