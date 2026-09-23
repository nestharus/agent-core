"""Focused integration checks; all SQLite files live in a temporary directory."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from types import SimpleNamespace
import unittest
from unittest import mock

import board_store
import board as board_cli
import catalog
import queue_transport


CLI = Path(__file__).with_name("board.py")
A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
C = "33333333-3333-4333-8333-333333333333"
D = "44444444-4444-4444-8444-444444444444"


class BoardCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "board home"

    def run_board(self, *args, actor=None, ok=True):
        env = os.environ.copy()
        env.pop("CODEX_SESSION_ID", None)
        if actor:
            env["CODEX_SESSION_ID"] = actor
        proc = subprocess.run([sys.executable, str(CLI), "--home", str(self.home), *map(str, args)],
                              text=True, capture_output=True, env=env, timeout=20)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stderr)
        else:
            self.assertEqual(proc.returncode, 2, (proc.stdout, proc.stderr))
            self.assertNotIn("Traceback", proc.stderr)
        return proc

    def obj(self, *args, actor=None):
        return json.loads(self.run_board(*args, "--json", actor=actor).stdout)

    def run_in_process(self, *args, actor=A):
        with mock.patch.dict(os.environ, {"CODEX_SESSION_ID": actor}), redirect_stdout(io.StringIO()):
            return board_cli.main(["--home", str(self.home), *map(str, args)])

    def test_list_missing_catalog_has_no_side_effects(self):
        self.assertEqual(self.obj("boards", "list"), [])
        self.assertFalse(self.home.exists())
        self.home.mkdir(mode=0o700)
        self.assertEqual(self.obj("boards", "list", "--artifact-type", "repository",
                                  "--artifact", "/abs/repo"), [])
        self.assertEqual(list(self.home.iterdir()), [])
        entry = self.create("listed")
        self.assertEqual([row["board_id"] for row in self.obj("boards", "list")],
                         [entry["board_id"]])

    def create(self, alias, *, temporary=True, invited=False):
        args = ["boards", "create", "--alias", alias, "--name", alias.title()]
        if temporary:
            args.append("--temporary-test")
        if invited:
            args += ["--membership", "invited"]
        return self.obj(*args)

    def join(self, board, session, *, role="root", route="queue", extra=()):
        if route == "queue" and "--profile" not in extra:
            extra = (*extra, "--profile", ".codex")
        return self.run_board("--board", board, "register", "--session", session,
                              "--role", role, "--route", route, *extra, actor=session)

    def test_labels_are_board_local_and_do_not_claim_activity(self):
        one = self.create("labels-one")
        two = self.create("labels-two")
        first, second = one["board_id"], two["board_id"]
        self.join(first, A, extra=("--label", "Review coordinator", "--work", "Long\nwork"))
        self.join(second, A, extra=("--label", "Writer"))
        with sqlite3.connect(one["db_path"]) as db:
            before = db.execute("SELECT last_seen_at FROM sessions WHERE session=?", (A,)).fetchone()[0]
            events = db.execute("SELECT COUNT(*) FROM membership_events WHERE session=?", (A,)).fetchone()[0]
        self.run_board("--board", first, "label", "--session", A, "--label", "Triage lead", actor=A)
        row = self.obj("--board", first, "sessions")[0]
        self.assertEqual((row["label"], row["work"], row["last_seen_at"]),
                         ("Triage lead", "Long\nwork", before))
        display = self.run_board("--board", first, "sessions").stdout
        self.assertIn(f"{A} active", display)
        self.assertIn("role=root label=Triage lead", display)
        self.assertIn("  work: Long\n        work", display)
        self.assertEqual(self.obj("--board", second, "sessions")[0]["label"], "Writer")
        self.run_board("--board", first, "register", "--session", A, "--role", "root",
                       "--label", "Wrong path", actor=A, ok=False)
        self.assertEqual(self.obj("--board", first, "sessions")[0]["label"], "Triage lead")
        self.run_board("--board", first, "label", "--session", A, "--clear", actor=A)
        self.assertIsNone(self.obj("--board", first, "sessions")[0]["label"])
        self.assertIn("label=(none)", self.run_board("--board", first, "sessions").stdout)
        self.assertEqual(self.obj("--board", second, "sessions")[0]["label"], "Writer")
        with sqlite3.connect(one["db_path"]) as db:
            self.assertEqual(db.execute("SELECT last_seen_at FROM sessions WHERE session=?", (A,))
                             .fetchone()[0], before)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM membership_events WHERE session=?", (A,))
                             .fetchone()[0], events)

    def test_label_permissions_validation_and_retired_board(self):
        entry = self.create("label-state")
        board = entry["board_id"]
        self.join(board, A, extra=("--label", "Original A"))
        self.join(board, B, extra=("--label", "Original B"))
        self.join(board, D, extra=("--label", "Original D"))

        def rejected_without_persisted_change(*args, actor):
            with sqlite3.connect(entry["db_path"]) as db:
                before = (db.execute("SELECT * FROM sessions ORDER BY session").fetchall(),
                          db.execute("SELECT * FROM membership_events ORDER BY event_id").fetchall())
            self.run_board("--board", board, "label", *args, actor=actor, ok=False)
            with sqlite3.connect(entry["db_path"]) as db:
                after = (db.execute("SELECT * FROM sessions ORDER BY session").fetchall(),
                         db.execute("SELECT * FROM membership_events ORDER BY event_id").fetchall())
            self.assertEqual(after, before)

        for value in (" ", "x" * 81, "Two\nlines", "Two\u2028lines", "api_key=secret123"):
            rejected_without_persisted_change("--session", A, "--label", value, actor=A)
        rejected_without_persisted_change("--session", A, "--clear", actor=B)
        rejected_without_persisted_change("--session", C, "--label", "Unknown", actor=C)
        self.run_board("--board", board, "heartbeat", "--session", B, "--status", "paused", actor=B)
        rejected_without_persisted_change("--session", B, "--label", "Paused", actor=B)
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00Z' WHERE session=?", (D,))
        rejected_without_persisted_change("--session", D, "--clear", actor=D)
        self.run_board("boards", "retire", "--board", board)
        self.run_board("--board", board, "label", "--session", A, "--label", "Wind-down",
                       actor=A)
        self.assertEqual(self.obj("--board", board, "sessions")[0]["label"], "Wind-down")
        self.run_board("--board", board, "leave", "--session", A, actor=A)
        self.run_board("--board", board, "label", "--session", A, "--clear", actor=A, ok=False)
        self.run_board("boards", "archive", "--board", board)
        self.run_board("--board", board, "label", "--session", A, "--clear", actor=A, ok=False)
        self.assertEqual(self.obj("--board", board, "sessions")[0]["label"], "Wind-down")

    def test_old_schema4_active_repair_and_archived_label_read(self):
        active = self.create("old-active-label")
        self.join(active["board_id"], A)
        with sqlite3.connect(active["db_path"]) as db:
            db.execute("ALTER TABLE sessions DROP COLUMN label")
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 4)
        self.join(active["board_id"], B, extra=("--label", "New member"))
        self.assertEqual({row["session"]: row["label"] for row in
                          self.obj("--board", active["board_id"], "sessions")},
                         {A: None, B: "New member"})
        archived = self.create("old-archive-label")
        self.join(archived["board_id"], A)
        with sqlite3.connect(archived["db_path"]) as db:
            db.execute("ALTER TABLE sessions DROP COLUMN label")
        self.run_board("boards", "retire", "--board", archived["board_id"])
        self.run_board("boards", "archive", "--board", archived["board_id"])
        snapshot = self.obj("boards", "show", "--board", archived["board_id"])["snapshot_path"]
        self.assertIsNone(self.obj("--board", archived["board_id"], "sessions")[0]["label"])
        self.assertIn("label=(none)", self.run_board("--board", archived["board_id"], "sessions").stdout)
        with sqlite3.connect(snapshot) as db:
            self.assertNotIn("label", {row[1] for row in db.execute("PRAGMA table_info(sessions)")})

    def test_old_schema4_opener_rechecks_after_raw_registration_repairs_label(self):
        entry = self.create("old-label-first-touch")
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("ALTER TABLE sessions DROP COLUMN label")
        owner = sqlite3.connect(entry["db_path"], isolation_level=None)
        self.addCleanup(owner.close)
        owner.row_factory = sqlite3.Row
        owner.execute("PRAGMA foreign_keys=ON")
        owner_args = SimpleNamespace(session=B, role="root", profile=".codex",
                                     profile_change_reason=None, work=None, campaign="general",
                                     status="active", route="managed", parent_session=None,
                                     scope=None, expires_at=None, owner=True,
                                     disposed_notice_ids=set())
        original_check = board_store.has_label_column
        interleaved = False

        def check_with_raw_registration(conn):
            nonlocal interleaved
            present = original_check(conn)
            if not interleaved and not present:
                interleaved = True
                with mock.patch.dict(os.environ, {"CODEX_SESSION_ID": B}):
                    board_store.register(owner, owner_args)
            return present

        with mock.patch.object(board_store, "has_label_column", side_effect=check_with_raw_registration):
            with board_store.database(entry["db_path"]) as opener:
                self.assertTrue(board_store.has_label_column(opener))
                self.assertEqual(tuple(opener.execute(
                    "SELECT label,route,owner FROM sessions WHERE session=?", (B,)).fetchone()),
                    (None, "managed", 1))
        self.assertTrue(interleaved)

    def open(self, board, author=A, *, title="Question"):
        return self.run_board("--board", board, "open", "--session", author,
                              "--topic", "work", "--title", title, "--text", "Body",
                              "--no-push", actor=author)

    def legacy_file(self, name):
        path = Path(self.temp.name) / name
        with board_store.database(str(path)):
            pass
        with sqlite3.connect(path) as db:
            db.execute("DROP TABLE notification_attempts")
            db.execute("ALTER TABLE notification_outbox DROP COLUMN route")
            db.execute("ALTER TABLE sessions DROP COLUMN route")
            db.execute("PRAGMA user_version=3")
        return path

    def schema3_source(self, name):
        """Build the pre-route column layout for a portable copied-board fixture."""
        path = Path(self.temp.name) / name
        with sqlite3.connect(path) as conn:
            conn.executescript("""
                CREATE TABLE sessions (
                    session TEXT PRIMARY KEY, campaign TEXT NOT NULL, role TEXT NOT NULL,
                    profile TEXT, status TEXT NOT NULL, work TEXT, registered_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL, ack_seq INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE posts (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT NOT NULL,
                    recipient TEXT, topic TEXT NOT NULL, kind TEXT NOT NULL,
                    text TEXT NOT NULL, ref TEXT, reply_to INTEGER, created_at TEXT NOT NULL);
                CREATE TABLE threads (
                    thread_id INTEGER PRIMARY KEY, title TEXT NOT NULL, topic TEXT NOT NULL,
                    opener TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE thread_posts (post_seq INTEGER PRIMARY KEY, thread_id INTEGER NOT NULL);
                CREATE TABLE subscriptions (
                    thread_id INTEGER NOT NULL, session TEXT NOT NULL, subscribed_at TEXT NOT NULL,
                    PRIMARY KEY(thread_id, session));
                CREATE TABLE attachments (
                    post_seq INTEGER NOT NULL, position INTEGER NOT NULL, reference TEXT NOT NULL,
                    PRIMARY KEY(post_seq, position));
                CREATE TABLE notification_outbox (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL, thread_id INTEGER NOT NULL, post_seq INTEGER NOT NULL,
                    event TEXT NOT NULL, title TEXT NOT NULL, sender TEXT NOT NULL,
                    created_at TEXT NOT NULL, delivery_state TEXT NOT NULL DEFAULT 'pending',
                    queue_message_id TEXT, state_changed_at TEXT, attempted_at TEXT,
                    queued_at TEXT, acknowledged_at TEXT, claim_token TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0, UNIQUE(recipient, post_seq));
                PRAGMA user_version=3;
            """)
        return path

    def test_many_to_many_links_and_alias_never_reassigned(self):
        one = self.create("one")
        two = self.create("two")
        self.assertNotEqual(one["board_id"], two["board_id"])
        for board in (one, two):
            self.run_board("boards", "associate", "--board", board["alias"], "--type",
                           "repository", "--id", "/repo/common")
        self.run_board("boards", "associate", "--board", "one", "--type",
                       "repository", "--id", "/repo/second")
        rows = self.obj("boards", "list", "--artifact-type", "repository",
                        "--artifact", "/repo/common")
        self.assertEqual({row["board_id"] for row in rows}, {one["board_id"], two["board_id"]})
        self.assertEqual(len(self.obj("boards", "show", "--board", "one")["artifacts"]), 2)
        self.run_board("boards", "disassociate", "--board", "two", "--type",
                       "repository", "--id", "/repo/common")
        self.assertEqual(len(self.obj("boards", "list", "--artifact-type", "repository",
                                      "--artifact", "/repo/common")), 1)
        self.run_board("boards", "retire", "--board", "one")
        self.run_board("boards", "archive", "--board", "one")
        self.run_board("boards", "purge", "--board", "one", "--confirm-id",
                       one["board_id"], "--irreversible")
        tombstone = self.obj("boards", "show", "--board", one["board_id"])
        self.assertEqual(tombstone["state"], "tombstoned")
        self.assertFalse(tombstone["detail_available"])
        self.run_board("boards", "create", "--alias", "one", "--name", "Replacement", ok=False)
        self.run_board("--board", "one", "read", ok=False)

    def test_memberships_routes_cursors_subscriptions_and_expiry_are_board_local(self):
        one = self.create("member-one")
        two = self.create("member-two")
        for board in (one, two):
            self.join(board["board_id"], A)
        self.join(one["board_id"], B, role="reviewer", route="managed",
                  extra=("--parent-session", A, "--scope", "review artifacts",
                         "--expires-at", "2030-01-01T00:00:00Z"))
        self.run_board("--board", one["board_id"], "register", "--session", B,
                       "--role", "reviewer", actor=B)
        updated = self.obj("--board", one["board_id"], "sessions")[1]
        self.assertEqual((updated["route"], updated["parent_session"], updated["expires_at"]),
                         ("managed", A, "2030-01-01T00:00:00.000000Z"))
        self.join(two["board_id"], B, role="scribe", route="queue")
        self.open(one["board_id"])
        self.open(two["board_id"])
        d1 = self.obj("--board", one["board_id"], "deliveries")
        d2 = self.obj("--board", two["board_id"], "deliveries")
        self.assertEqual((d1[0]["post_seq"], d2[0]["post_seq"]), (1, 1))
        self.assertEqual((d1[0]["route"], d1[0]["delivery_state"]), ("managed", "managed_pending"))
        self.assertEqual((d2[0]["route"], d2[0]["delivery_state"]), ("queue", "pending"))
        self.assertEqual(d1[0]["board_id"], one["board_id"])
        self.run_board("--board", one["board_id"], "ack", "--session", B, "--through", 1, actor=B)
        self.assertEqual(self.obj("--board", one["board_id"], "sessions")[1]["ack_seq"], 1)
        self.assertEqual(self.obj("--board", two["board_id"], "sessions")[1]["ack_seq"], 0)
        self.run_board("--board", one["board_id"], "subscribe", "--session", B,
                       "--thread", 1, actor=B)
        with sqlite3.connect(one["db_path"]) as first, sqlite3.connect(two["db_path"]) as second:
            self.assertEqual(first.execute("SELECT COUNT(*) FROM subscriptions WHERE session=?", (B,))
                             .fetchone()[0], 1)
            self.assertEqual(second.execute("SELECT COUNT(*) FROM subscriptions WHERE session=?", (B,))
                             .fetchone()[0], 0)
        self.assertEqual(self.obj("--board", one["board_id"], "notifications", "--session", B)[0]
                         ["board_id"], one["board_id"])
        with sqlite3.connect(one["db_path"]) as conn:
            conn.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00.000000Z' WHERE session=?", (B,))
        self.open(one["board_id"], title="After expiry")
        self.assertEqual(len(self.obj("--board", one["board_id"], "deliveries")), 1)
        self.run_board("--board", one["board_id"], "watch", "--session", B,
                       "--timeout", 1, actor=B, ok=False)
        self.run_board("boards", "dispose-notices", "--board", one["board_id"],
                       "--notice-id", 1, "--reason", "Expired member; retain pending delivery")
        self.run_board("--board", one["board_id"], "leave", "--session", B, actor=B)
        self.assertEqual(self.obj("--board", one["board_id"], "sessions")[1]["status"], "completed")
        events = self.obj("--board", one["board_id"], "membership-events", "--session", B)
        self.assertEqual([item["event"] for item in events], ["register", "register", "leave"])
        self.assertEqual(events[0]["parent_session"], A)
        self.assertEqual(self.obj("--board", two["board_id"], "sessions")[1]["status"], "active")
        with sqlite3.connect(two["db_path"]) as conn:
            conn.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00.000000Z' WHERE session=?", (B,))
        with board_store.database(two["db_path"]) as conn:
            self.assertIsNone(board_store.claim_next(conn, attempted_ids=set(), post_seq=None,
                              thread_id=None, recipient=None, actor=A))
            self.assertEqual(conn.execute("SELECT attempt_count FROM notification_outbox").fetchone()[0], 0)
        self.run_board("--board", one["board_id"], "register", "--session", B,
                       "--role", "retry", actor=B, ok=False)
        self.run_board("--board", one["board_id"], "heartbeat", "--session", B,
                       "--status", "paused", actor=B, ok=False)

    def test_board_qualified_notice_reads_through_shared_reader(self):
        entry = self.create("pointer")
        self.join(entry["board_id"], A)
        self.open(entry["board_id"], title="Owner question")
        notice = queue_transport.render_new_thread(1, "Owner question", 1,
                      board_id=entry["board_id"], board_home=self.home)
        self.assertIn("board ID: " + entry["board_id"], notice)
        self.assertNotIn("rfq_swarm.py", notice)
        read = next(line.removeprefix("Read: ") for line in notice.splitlines()
                    if line.startswith("Read: "))
        proc = subprocess.run(shlex.split(read) + ["--json"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)[0]["board_id"], entry["board_id"])
        self.run_board("thread", "--id", 1, ok=False)

    def test_queue_acceptance_attempt_and_recipient_ack_remain_distinct(self):
        entry = self.create("delivery")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B)
        self.open(board)
        sent = []

        def sender(recipient, profile, notice):
            sent.append((recipient, profile, notice))
            return queue_transport.EnqueueResult("queued", B, 0, "Queued message", reason="queue_accepted")

        with board_store.database(entry["db_path"]) as conn:
            processed = board_store.dispatch_notices(
                conn, actor=A, limit=5, board_id=board,
                board_home=str(self.home), sender=sender)
        self.assertEqual(processed, [(1, 1)])
        self.assertEqual(len(sent), 1)
        self.assertIn("board ID: " + board, sent[0][2])
        delivery = self.obj("--board", board, "deliveries")[0]
        self.assertEqual((delivery["route"], delivery["delivery_state"]), ("queue", "queued"))
        self.assertIsNone(delivery["acknowledged_at"])
        attempts = self.obj("--board", board, "attempts", "--notification", 1)
        self.assertEqual((attempts[0]["board_id"], attempts[0]["result"]), (board, "queued"))
        self.run_board("--board", board, "ack-notice", "--session", B,
                       "--notification", 1, actor=B)
        self.assertEqual(self.obj("--board", board, "deliveries")[0]["delivery_state"],
                         "acknowledged")

    def test_ack_and_profile_change_wait_for_fake_sender_to_settle(self):
        entry = self.create("inflight-profile")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B)
        self.open(board)

        def sender(recipient, profile, notice):
            self.assertEqual((recipient, profile), (B, ".codex"))
            self.assertIn("board ID: " + board, notice)
            ack = self.run_board("--board", board, "ack-notice", "--session", B,
                                 "--notification", 1, actor=B, ok=False)
            self.assertIn("retry ack-notice after the attempt settles", ack.stderr)
            change = self.run_board("--board", board, "register", "--session", B,
                                    "--role", "root", "--profile", ".codex2",
                                    "--profile-change-reason", "Correct home",
                                    actor=B, ok=False)
            self.assertIn("settle in-flight queue attempts", change.stderr)
            with sqlite3.connect(entry["db_path"]) as db:
                state = db.execute("SELECT delivery_state,claim_token,acknowledged_at "
                                   "FROM notification_outbox WHERE notification_id=1").fetchone()
                self.assertEqual(state[0], "sending")
                self.assertIsNotNone(state[1])
                self.assertIsNone(state[2])
                self.assertEqual(db.execute("SELECT profile FROM sessions WHERE session=?", (B,))
                                 .fetchone()[0], ".codex")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM profile_changes").fetchone()[0], 0)
            return queue_transport.EnqueueResult("queued", D, 0, "Queued message",
                                                 reason="queue_accepted")

        with board_store.database(entry["db_path"]) as conn:
            self.assertEqual(board_store.dispatch_notices(
                conn, actor=A, limit=1, board_id=board, board_home=str(self.home),
                sender=sender), [(1, 1)])
        delivery = self.obj("--board", board, "deliveries")[0]
        self.assertEqual((delivery["delivery_state"], delivery["queue_message_id"]),
                         ("queued", D))
        self.assertIsNone(delivery["acknowledged_at"])
        self.assertEqual(self.obj("--board", board, "attempts", "--notification", 1)[0]
                         ["result"], "queued")
        self.run_board("--board", board, "ack-notice", "--session", B,
                       "--notification", 1, actor=B)
        self.run_board("--board", board, "register", "--session", B, "--role", "root",
                       "--profile", ".codex2", "--profile-change-reason", "Correct home",
                       actor=B)
        self.assertEqual(self.obj("--board", board, "deliveries")[0]["delivery_state"],
                         "acknowledged")
        self.assertEqual(self.obj("--board", board, "profile-changes")[0]["old_profile"],
                         ".codex")

    def test_interrupted_sending_claim_can_recover_then_be_acknowledged(self):
        entry = self.create("interrupted-ack")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B)
        self.open(board)
        with board_store.database(entry["db_path"]) as conn:
            claim = board_store.claim_next(conn, attempted_ids=set(), post_seq=None,
                                           thread_id=None, recipient=None, actor=A)
            self.assertIsNotNone(claim)
        self.run_board("--board", board, "ack-notice", "--session", B,
                       "--notification", 1, actor=B, ok=False)
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("UPDATE notification_outbox SET attempted_at=? WHERE notification_id=1",
                       ("2000-01-01T00:00:00.000000Z",))
        self.run_board("--board", board, "recover", "--acting-session", A,
                       "--older-than", 120, actor=A)
        self.assertEqual(self.obj("--board", board, "deliveries")[0]["delivery_state"],
                         "ambiguous")
        self.run_board("--board", board, "ack-notice", "--session", B,
                       "--notification", 1, actor=B)
        self.assertEqual(self.obj("--board", board, "deliveries")[0]["delivery_state"],
                         "acknowledged")
        self.assertEqual(self.obj("--board", board, "attempts", "--notification", 1)[0]
                         ["result"], "ambiguous")

    def test_late_recovered_sender_receipt_survives_ack_and_profile_change(self):
        entry = self.create("recovered-late-receipt")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B)
        self.open(board)

        def sender(recipient, profile, notice):
            self.assertEqual((recipient, profile), (B, ".codex"))
            self.assertIn("board ID: " + board, notice)
            with sqlite3.connect(entry["db_path"]) as db:
                db.execute("UPDATE notification_outbox SET attempted_at=? "
                           "WHERE notification_id=1 AND delivery_state='sending'",
                           ("2000-01-01T00:00:00.000000Z",))
            self.run_board("--board", board, "recover", "--acting-session", A,
                           "--older-than", 120, actor=A)
            recovered = self.obj("--board", board, "attempts", "--notification", 1)[0]
            self.assertEqual((recovered["result"], recovered["profile"],
                              recovered["recovered_by"]), ("ambiguous", ".codex", A))
            self.run_board("--board", board, "ack-notice", "--session", B,
                           "--notification", 1, actor=B)
            self.run_board("--board", board, "register", "--session", B,
                           "--role", "root", "--profile", ".codex2",
                           "--profile-change-reason", "Correct recipient home", actor=B)
            delivery = self.obj("--board", board, "deliveries")[0]
            self.assertEqual(delivery["delivery_state"], "acknowledged")
            self.assertIsNone(delivery["queue_message_id"])
            self.assertIsNone(delivery["queued_at"])
            self.assertIsNotNone(delivery["acknowledged_at"])
            with sqlite3.connect(entry["db_path"]) as db:
                self.assertIsNone(db.execute("SELECT claim_token FROM notification_outbox "
                                             "WHERE notification_id=1").fetchone()[0])
            return queue_transport.EnqueueResult("queued", D, 0, "Queued message",
                                                 reason="queue_accepted")

        with board_store.database(entry["db_path"]) as conn:
            self.assertEqual(board_store.dispatch_notices(
                conn, actor=A, limit=1, board_id=board, board_home=str(self.home),
                sender=sender), [(1, 1)])
        delivery = self.obj("--board", board, "deliveries")[0]
        self.assertEqual((delivery["delivery_state"], delivery["queue_message_id"]),
                         ("acknowledged", D))
        self.assertIsNotNone(delivery["queued_at"])
        self.assertIsNotNone(delivery["acknowledged_at"])
        self.assertLessEqual(delivery["acknowledged_at"], delivery["queued_at"])
        self.assertEqual(delivery["state_changed_at"], delivery["acknowledged_at"])
        self.assertEqual(delivery["attempt_count"], 1)
        attempt = self.obj("--board", board, "attempts", "--notification", 1)[0]
        self.assertEqual((attempt["attempt_number"], attempt["profile"], attempt["result"],
                          attempt["reason"], attempt["recovered_by"]),
                         (1, ".codex", "queued", "queue_accepted", A))
        self.assertIsNotNone(attempt["recovered_at"])
        self.assertEqual(self.obj("--board", board, "profile-changes", "--session", B)[0]
                         ["new_profile"], ".codex2")

    def test_recipient_profile_overrides_actor_home_and_mixed_fanout(self):
        entry = self.create("mixed-profiles")
        board = entry["board_id"]
        self.join(board, A, extra=("--profile", ".codex5"))
        self.join(board, B, extra=("--profile", ".codex"))
        self.join(board, C, extra=("--profile", ".codex2"))
        self.open(board)
        sent = []

        def sender(recipient, profile, notice):
            sent.append((recipient, profile))
            return queue_transport.EnqueueResult("queued", D, 0, "Queued message",
                                                 reason="queue_accepted")

        with board_store.database(entry["db_path"]) as conn, \
             mock.patch.dict(os.environ, {"CODEX_HOME": str(queue_transport.profile_root() / ".codex5")}):
            board_store.dispatch_notices(conn, actor=A, limit=5, board_id=board,
                                         board_home=str(self.home), sender=sender)
        self.assertEqual(sent, [(B, ".codex"), (C, ".codex2")])
        self.assertEqual([self.obj("--board", board, "attempts", "--notification", item)[0]["profile"]
                          for item in (1, 2)], [".codex", ".codex2"])
        self.assertEqual([item["delivery_state"] for item in self.obj("--board", board,
                                                                         "deliveries")],
                         ["queued", "queued"])

    def test_missing_recipient_profile_fails_before_claim_and_inline_content(self):
        entry = self.create("missing-profile")
        board = entry["board_id"]
        self.join(board, A, extra=("--profile", ".codex5"))
        self.run_board("--board", board, "register", "--session", B, "--role", "root",
                       actor=B, ok=False)
        self.join(board, B)
        self.run_board("--board", board, "open", "--session", A, "--topic", "work",
                       "--title", "Question", "--text", "Body", "--to", B, "--no-push",
                       actor=A)
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("UPDATE sessions SET profile=NULL WHERE session=?", (B,))
        sent = []
        with board_store.database(entry["db_path"]) as conn:
            with self.assertRaisesRegex(board_store.UserError, "no registered profile"):
                board_store.dispatch_notices(conn, actor=A, limit=5, board_id=board,
                                             board_home=str(self.home), sender=lambda *x: sent.append(x))
        self.assertEqual(sent, [])
        with sqlite3.connect(entry["db_path"]) as db:
            self.assertEqual(db.execute("SELECT delivery_state,attempt_count FROM notification_outbox")
                             .fetchone(), ("pending", 0))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM notification_attempts").fetchone()[0], 0)
        for command in (("open", "--session", A, "--topic", "work", "--title", "Again",
                         "--text", "Body", "--to", B),
                        ("reply", "--session", A, "--thread", 1, "--text", "Again")):
            with self.subTest(command=command[0]):
                failed = self.run_board("--board", board, *command, actor=A, ok=False)
                self.assertIn("no registered profile", failed.stderr)
        with sqlite3.connect(entry["db_path"]) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM notification_outbox").fetchone()[0], 1)
            db.execute("UPDATE sessions SET profile='.codex6' WHERE session=?", (B,))
        with board_store.database(entry["db_path"]) as conn:
            with self.assertRaisesRegex(board_store.UserError, "invalid or unavailable"):
                board_store.dispatch_notices(conn, actor=A, limit=5, board_id=board,
                                             board_home=str(self.home), sender=lambda *x: sent.append(x))
        self.assertEqual(sent, [])
        with sqlite3.connect(entry["db_path"]) as db:
            self.assertEqual(db.execute("SELECT delivery_state,attempt_count FROM notification_outbox")
                             .fetchone(), ("pending", 0))
            db.execute("UPDATE sessions SET profile=NULL WHERE session=?", (B,))
        self.run_board("--board", board, "register", "--session", B, "--role", "root",
                       "--profile", ".codex", "--profile-change-reason", "Correct legacy profile",
                       actor=B)
        changes = self.obj("--board", board, "profile-changes", "--session", B)
        self.assertEqual([(x["old_profile"], x["new_profile"], x["reason"]) for x in changes],
                         [(None, ".codex", "Correct legacy profile")])

    def test_invalid_profile_blocks_unfiltered_claim_but_not_targeted_recipient(self):
        entry = self.create("targeted-profile")
        board = entry["board_id"]
        for session in (A, B, C):
            self.join(board, session)
        self.open(board)
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("UPDATE sessions SET profile='.codex6' WHERE session=?", (B,))
        sent = []

        def sender(recipient, profile, _notice):
            sent.append((recipient, profile))
            return queue_transport.EnqueueResult("queued", D, 0, "Queued message")

        with board_store.database(entry["db_path"]) as conn:
            with self.assertRaisesRegex(board_store.UserError, "invalid or unavailable"):
                board_store.dispatch_notices(conn, actor=A, limit=2, board_id=board,
                                             board_home=str(self.home), sender=sender)
            self.assertEqual(board_store.dispatch_notices(
                conn, actor=A, limit=2, board_id=board, board_home=str(self.home),
                recipient=C, sender=sender), [(1, 1)])
        self.assertEqual(sent, [(C, ".codex")])
        self.assertEqual([(item["recipient"], item["delivery_state"])
                          for item in self.obj("--board", board, "deliveries")],
                         [(B, "pending"), (C, "queued")])

    def test_profile_change_needs_reason_and_retains_attempt_profiles(self):
        entry = self.create("profile-change")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B)
        self.open(board)
        with board_store.database(entry["db_path"]) as conn:
            board_store.dispatch_notices(
                conn, actor=A, limit=1, board_id=board, board_home=str(self.home),
                sender=lambda *_: queue_transport.EnqueueResult("failed", None, 1, "no rollout",
                                                                reason="queue_rejected"))
        self.run_board("--board", board, "register", "--session", B, "--role", "root",
                       "--profile", ".codex2", actor=B, ok=False)
        self.run_board("--board", board, "register", "--session", B, "--role", "root",
                       "--profile", ".codex2", "--profile-change-reason", "Session moved",
                       actor=B)
        with board_store.database(entry["db_path"]) as conn:
            board_store.dispatch_notices(
                conn, actor=A, limit=1, board_id=board, board_home=str(self.home),
                sender=lambda *_: queue_transport.EnqueueResult("queued", D, 0, "Queued message"))
        self.assertEqual([x["profile"] for x in self.obj("--board", board, "attempts",
                                                        "--notification", 1)],
                         [".codex", ".codex2"])
        self.assertEqual(self.obj("--board", board, "profile-changes")[0]["reason"],
                         "Session moved")

        self.run_board("--board", board, "open", "--session", A, "--topic", "work",
                       "--title", "Second", "--text", "Body", "--to", B, "--no-push",
                       actor=A)
        with board_store.database(entry["db_path"]) as conn:
            board_store.dispatch_notices(
                conn, actor=A, limit=1, board_id=board, board_home=str(self.home), post_seq=2,
                sender=lambda *_: queue_transport.EnqueueResult("ambiguous", None, 1,
                                                                 "uncertain response"))
        self.run_board("--board", board, "register", "--session", B, "--role", "root",
                       "--profile", ".codex5", "--profile-change-reason", "New home",
                       actor=B)
        sent = []
        with board_store.database(entry["db_path"]) as conn:
            board_store.dispatch_notices(conn, actor=A, limit=1, board_id=board,
                                         board_home=str(self.home), post_seq=2,
                                         sender=lambda *x: sent.append(x))
        self.assertEqual(sent, [])
        self.assertEqual(self.obj("--board", board, "deliveries", "--post", 2)[0]
                         ["delivery_state"], "ambiguous")
        self.assertEqual(len(self.obj("--board", board, "attempts", "--notification", 2)), 1)

    def test_definite_no_rollout_and_uncertain_queue_results_stay_distinct(self):
        no_rollout = queue_transport.queue_notice(
            B, ".codex", "Notice", runner=lambda *_: queue_transport.CommandOutcome(
                1, "unable to enqueue message: no rollout found for thread id"))
        uncertain = queue_transport.queue_notice(
            B, ".codex", "Notice", runner=lambda *_: queue_transport.CommandOutcome(
                1, "transport failed after request"))
        self.assertEqual((no_rollout.status, no_rollout.reason), ("failed", "queue_rejected"))
        self.assertEqual((uncertain.status, uncertain.reason),
                         ("ambiguous", "unrecognized_queue_response"))

    def test_queue_profile_uses_current_account_and_exact_allowed_path(self):
        account = Path(self.temp.name) / "account"
        foreign = Path(self.temp.name) / "foreign"
        profile = account / ".codex2"
        profile.mkdir(parents=True)
        foreign.mkdir()
        (account / ".codex3").symlink_to(profile, target_is_directory=True)
        sent = []

        def runner(argv, env, timeout, capture_bytes):
            sent.append((argv, env["CODEX_HOME"]))
            return queue_transport.CommandOutcome(0, f"Queued message {B}")

        with mock.patch.object(queue_transport.pwd, "getpwuid",
                               return_value=SimpleNamespace(pw_dir=str(account))), \
             mock.patch.dict(os.environ, {"HOME": str(foreign),
                                       "CODEX_HOME": str(profile)}):
            result = queue_transport.queue_notice(A, ".codex2", "Board notice", runner=runner)
            self.assertEqual((result.status, result.queue_message_id), ("queued", B))
            self.assertEqual(sent[0][1], str(profile))
            self.assertEqual(sent[0][0][:4], ["codex", "queue", "--thread", A])
            with self.assertRaisesRegex(ValueError, "does not exist"):
                queue_transport.queue_notice(A, ".codex3", "Board notice", runner=runner)
            with self.assertRaisesRegex(ValueError, "allowed local"):
                queue_transport.queue_notice(A, ".codex6", "Board notice", runner=runner)
        self.assertEqual(len(sent), 1)

    def test_lifecycle_snapshot_owner_hold_and_purge_guards(self):
        entry = self.create("lifecycle")
        board = entry["board_id"]
        self.join(board, A, extra=("--owner", "--expires-at", "2030-01-01T00:00:00Z"))
        self.open(board)
        with sqlite3.connect(entry["db_path"]) as conn:
            conn.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00.000000Z' WHERE session=?", (A,))
        self.run_board("boards", "archive", "--board", board, ok=False)
        self.run_board("boards", "retire", "--board", board)
        self.open_failure = self.run_board("--board", board, "post", "--session", A,
                                           "--topic", "x", "--kind", "status", "--text", "x",
                                           actor=A, ok=False)
        self.assertIn("retired board", self.open_failure.stderr)
        self.run_board("boards", "archive", "--board", board, ok=False)
        self.run_board("--board", board, "leave", "--session", A, actor=A)
        self.run_board("boards", "archive", "--board", board)
        archived = self.obj("boards", "show", "--board", board)
        snapshot = Path(archived["snapshot_path"])
        self.assertTrue(snapshot.is_file())
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), archived["snapshot_sha256"])
        with sqlite3.connect(entry["db_path"]) as conn:
            conn.execute("INSERT INTO posts(author,topic,kind,text,created_at) "
                         "VALUES (?,'x','status','Uncataloged later write','2030-01-01T00:00:00Z')", (A,))
        self.assertEqual(len(self.obj("--board", board, "read")), 1)
        self.run_board("--board", board, "ack", "--session", A, "--through", 1,
                       actor=A, ok=False)
        self.run_board("--board", board, "watch", "--session", A, "--timeout", 1,
                       actor=A, ok=False)
        self.run_board("--board", board, "dispatch", "--acting-session", A,
                       actor=A, ok=False)
        self.run_board("boards", "purge", "--board", board, "--confirm-id", B,
                       "--irreversible", ok=False)
        self.run_board("boards", "hold", "--board", board, "--enabled", "yes")
        self.run_board("boards", "purge", "--board", board, "--confirm-id", board,
                       "--irreversible", ok=False)
        self.run_board("boards", "hold", "--board", board, "--enabled", "no")
        self.run_board("boards", "purge", "--board", board, "--confirm-id", board,
                       "--irreversible")
        self.assertFalse(snapshot.exists())
        self.assertFalse(Path(entry["db_path"]).exists())

    def test_invited_policy_and_non_test_purge_prohibition(self):
        entry = self.create("invited", temporary=False, invited=True)
        board = entry["board_id"]
        self.run_board("--board", board, "register", "--session", A, "--role", "root",
                       actor=A, ok=False)
        self.run_board("boards", "invite", "--board", board, "--session", A)
        self.join(board, A)
        self.open(board)
        self.run_board("--board", board, "read", ok=False)
        scoped = self.obj("--board", board, "read", actor=A)
        self.assertEqual(scoped[0]["board_id"], board)
        self.run_board("boards", "retire", "--board", board)
        self.run_board("boards", "archive", "--board", board)
        self.run_board("boards", "purge", "--board", board, "--confirm-id", board,
                       "--irreversible", ok=False)

    def test_board_route_policy_rejects_forbidden_member_route(self):
        entry = self.obj("boards", "create", "--alias", "queue-only", "--name", "Queue only",
                         "--routes", "queue")
        self.run_board("--board", entry["board_id"], "register", "--session", A,
                       "--role", "root", "--route", "managed", actor=A, ok=False)
        self.join(entry["board_id"], A)

    def test_existing_shared_home_is_rejected_without_changing_permissions(self):
        shared = Path(self.temp.name) / "shared"
        shared.mkdir(mode=0o755)
        shared.chmod(0o755)
        before = shared.stat().st_mode & 0o777
        proc = subprocess.run([sys.executable, str(CLI), "--home", str(shared),
                               "boards", "list"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("board home must be private", proc.stderr)
        self.assertEqual(shared.stat().st_mode & 0o777, before)

    def test_default_storage_uses_xdg_data_home(self):
        xdg = Path(self.temp.name) / "xdg"
        env = os.environ.copy()
        env.pop("MESSAGE_BOARD_HOME", None)
        env["XDG_DATA_HOME"] = str(xdg)
        proc = subprocess.run([sys.executable, str(CLI), "boards", "create", "--alias",
                               "xdg-board", "--name", "XDG board", "--json"],
                              text=True, capture_output=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        entry = json.loads(proc.stdout)
        self.assertTrue(Path(entry["db_path"]).is_relative_to(xdg / "message-board"))
        self.assertTrue(Path(entry["db_path"]).is_file())

    def test_legacy_registration_is_read_only_then_explicit_migration_preserves_rows(self):
        path = Path(self.temp.name) / "legacy.sqlite3"
        with board_store.database(str(path)) as conn:
            conn.execute("INSERT INTO sessions(session,campaign,role,status,registered_at,last_seen_at) "
                         "VALUES (?,'rfq','owner','active','2025-01-01T00:00:00Z','2025-01-01T00:00:00Z')", (A,))
            conn.execute("INSERT INTO sessions(session,campaign,role,status,registered_at,last_seen_at) "
                         "VALUES (?,'rfq','reviewer','active','2025-01-01T00:00:00Z','2025-01-01T00:00:00Z')", (B,))
            conn.execute("INSERT INTO posts(seq,author,topic,kind,text,created_at) "
                         "VALUES (7,?,'migration','question','Historical body','2025-01-01T00:00:00Z')", (A,))
            conn.execute("INSERT INTO threads(thread_id,title,topic,opener,created_at) "
                         "VALUES (7,'Historical title','migration',?,'2025-01-01T00:00:00Z')", (A,))
            conn.execute("INSERT INTO thread_posts(post_seq,thread_id) VALUES(7,7)")
            conn.execute("INSERT INTO notification_outbox(notification_id,recipient,thread_id,post_seq,event,title,"
                         "sender,created_at,delivery_state,state_changed_at,attempt_count) "
                         "VALUES (9,?,7,7,'open','Historical title',?,'2025-01-01T00:00:00Z',"
                         "'ambiguous','2025-01-01T00:00:00Z',1)", (B, A))
        with sqlite3.connect(path) as conn:
            conn.execute("DROP TABLE notification_attempts")
            conn.execute("ALTER TABLE notification_outbox DROP COLUMN route")
            conn.execute("ALTER TABLE sessions DROP COLUMN route")
            conn.execute("PRAGMA user_version=3")
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        sidecars_before = {file.name for file in path.parent.glob(path.name + "*")}
        entry = self.obj("boards", "register-path", "--alias", "rfq-copy", "--name", "RFQ Copy",
                         "--db", path)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        self.assertEqual({file.name for file in path.parent.glob(path.name + "*")}, sidecars_before)
        self.assertEqual(self.obj("boards", "show", "--board", "rfq-copy")["db_path"], str(path))
        self.run_board("--board", "rfq-copy", "thread", "--id", 7, ok=False)
        backup = Path(self.temp.name) / "before.sqlite3"
        self.run_board("boards", "migrate", "--board", "rfq-copy", "--backup", backup)
        with sqlite3.connect(path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 4)
            self.assertEqual(conn.execute("SELECT board_id FROM board_meta").fetchone()[0], entry["board_id"])
            self.assertEqual(conn.execute("SELECT route,delivery_state FROM notification_outbox "
                                          "WHERE notification_id=9").fetchone(), ("queue", "ambiguous"))
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM notification_attempts").fetchone()[0], 0)
            self.assertIsNone(conn.execute("SELECT profile FROM sessions WHERE session=?", (B,))
                              .fetchone()[0])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM profile_changes").fetchone()[0], 0)
        with sqlite3.connect(backup) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)
        posts = self.obj("--board", "rfq-copy", "thread", "--id", 7)
        self.assertEqual((posts[0]["seq"], posts[0]["text"]), (7, "Historical body"))
        self.assertEqual(self.obj("--board", "rfq-copy", "notifications", "--session", B)[0]
                         ["notification_id"], 9)
        notice = queue_transport.render_new_thread(7, "Historical title", 9,
                      board_id=entry["board_id"], board_home=self.home)
        read = next(line.removeprefix("Read: ") for line in notice.splitlines()
                    if line.startswith("Read: "))
        proc = subprocess.run(shlex.split(read) + ["--json"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)[0]["seq"], 7)

    def test_managed_only_migrated_board_blocks_queue_cli_before_claim_or_post(self):
        source = self.schema3_source("historical-source.sqlite3")
        path = Path(self.temp.name) / "historical-copy.sqlite3"
        with sqlite3.connect(source) as conn:
            for session, status in ((A, "active"), (B, "active"), (C, "paused")):
                conn.execute("INSERT INTO sessions(session,campaign,role,status,registered_at,last_seen_at) "
                             "VALUES (?,'rfq','root',?,'2025-01-01T00:00:00Z','2025-01-01T00:00:00Z')",
                             (session, status))
            conn.execute("INSERT INTO posts(seq,author,topic,kind,text,created_at) "
                         "VALUES (7,?,'rfq','question','Historical body','2025-01-01T00:00:00Z')", (A,))
            conn.execute("INSERT INTO threads(thread_id,title,topic,opener,created_at) "
                         "VALUES (7,'Historical title','rfq',?,'2025-01-01T00:00:00Z')", (A,))
            conn.execute("INSERT INTO thread_posts(post_seq,thread_id) VALUES (7,7)")
            conn.execute("INSERT INTO subscriptions(thread_id,session,subscribed_at) "
                         "VALUES (7,?,'2025-01-01T00:00:00Z')", (B,))
            for notice_id, recipient, state in ((3, B, "pending"), (5, C, "ambiguous")):
                conn.execute("INSERT INTO notification_outbox "
                             "(notification_id,recipient,thread_id,post_seq,event,title,sender,"
                             "created_at,delivery_state,state_changed_at,attempt_count) "
                             "VALUES (?,?,7,7,'open','Historical title',?,"
                             "'2025-01-01T00:00:00Z',?,'2025-01-01T00:00:00Z',0)",
                             (notice_id, recipient, A, state))
        shutil.copy2(source, path)
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),
                         hashlib.sha256(path.read_bytes()).digest())
        with sqlite3.connect(path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual([row[1] for row in conn.execute("PRAGMA table_info(sessions)")],
                             ["session", "campaign", "role", "profile", "status", "work",
                              "registered_at", "last_seen_at", "ack_seq"])
            self.assertEqual(len(list(conn.execute("PRAGMA table_info(notification_outbox)"))), 16)
        entry = self.obj("boards", "register-path", "--alias", "historical-copy",
                         "--name", "Historical copy", "--db", path, "--routes", "managed")
        backup = Path(self.temp.name) / "historical-backup.sqlite3"
        self.run_board("boards", "migrate", "--board", entry["board_id"], "--backup", backup)
        self.assertEqual(self.obj("boards", "show", "--board", entry["board_id"])
                         ["allowed_routes"], "managed")
        with sqlite3.connect(path) as conn:
            self.assertEqual(conn.execute("SELECT status,route FROM sessions ORDER BY session").fetchall(),
                             [("active", "queue"), ("active", "queue"), ("paused", "queue")])
            original = conn.execute("SELECT notification_id,route,delivery_state,attempt_count "
                                    "FROM notification_outbox ORDER BY notification_id").fetchall()
            self.assertEqual(original, [(3, "queue", "pending", 0),
                                        (5, "queue", "ambiguous", 0)])
        sent = []
        def sender(*args):
            sent.append(args)
            return queue_transport.EnqueueResult("queued", "fake-id", 0, "Queued message")

        with mock.patch.object(queue_transport, "queue_notice", side_effect=sender):
            for command in (("dispatch", "--acting-session", A),
                            ("open", "--session", A, "--topic", "rfq", "--title", "New",
                             "--text", "Body"),
                            ("reply", "--session", A, "--thread", "7", "--text", "Reply")):
                with self.subTest(command=command[0]), self.assertRaisesRegex(
                        catalog.CatalogError, "queue delivery is forbidden by board policy"):
                    self.run_in_process("--board", entry["board_id"], *command)
            self.assertEqual(sent, [])
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT notification_id,route,delivery_state,attempt_count "
                                              "FROM notification_outbox ORDER BY notification_id").fetchall(),
                                 original)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM notification_attempts")
                                 .fetchone()[0], 0)

            # No-push commits the ordinary route-specific outbox. Historical queue
            # rows remain pending; a newly enrolled managed owner can still poll.
            self.join(entry["board_id"], D, route="managed")
            self.assertEqual(self.run_in_process("--board", entry["board_id"], "open",
                                                 "--session", A, "--topic", "rfq",
                                                 "--title", "Managed work", "--text", "Body",
                                                 "--no-push"), 0)
            self.assertEqual(self.run_in_process("--board", entry["board_id"], "reply",
                                                 "--session", A, "--thread", 7, "--text", "Reply",
                                                 "--cc", D, "--no-push"), 0)
            self.assertEqual(self.run_in_process("--board", entry["board_id"], "recover",
                                                 "--acting-session", A), 0)
            self.assertEqual(sent, [])
        with sqlite3.connect(path) as conn:
            self.assertEqual(conn.execute("SELECT notification_id,route,delivery_state,attempt_count "
                                          "FROM notification_outbox WHERE notification_id IN (3,5) "
                                          "ORDER BY notification_id").fetchall(), original)
            self.assertEqual(conn.execute("SELECT route,delivery_state FROM notification_outbox "
                                          "WHERE post_seq IN (8,9) ORDER BY post_seq,recipient").fetchall(),
                             [("queue", "pending"), ("managed", "managed_pending"),
                              ("queue", "pending"), ("managed", "managed_pending")])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM notification_attempts").fetchone()[0], 0)

    def test_queue_allowed_board_keeps_dispatch_and_inline_delivery(self):
        entry = self.create("queue-allowed")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B)
        sent = []
        def sender(*args):
            sent.append(args)
            return queue_transport.EnqueueResult("queued", "fake-id", 0, "Queued message")

        with mock.patch.object(queue_transport, "queue_notice", side_effect=sender):
            self.assertEqual(self.run_in_process("--board", board, "open", "--session", A,
                                                 "--topic", "work", "--title", "Deferred",
                                                 "--text", "Body", "--to", B, "--no-push"), 0)
            self.assertEqual(sent, [])
            self.assertEqual(self.run_in_process("--board", board, "dispatch",
                                                 "--acting-session", A), 0)
            self.assertEqual(self.run_in_process("--board", board, "open", "--session", A,
                                                 "--topic", "work", "--title", "Immediate",
                                                 "--text", "Body", "--to", B), 0)
            self.assertEqual(self.run_in_process("--board", board, "reply", "--session", A,
                                                 "--thread", 2, "--text", "Reply"), 0)
        self.assertEqual([call[0] for call in sent], [B, B, B])
        self.assertEqual([row["delivery_state"] for row in self.obj("--board", board,
                                                                       "deliveries")],
                         ["queued", "queued", "queued"])

    def test_notice_disposition_gates_retire_and_archive_without_acknowledgment(self):
        entry = self.create("notice-retire")
        self.join(entry["board_id"], A)
        self.join(entry["board_id"], B)
        self.open(entry["board_id"])
        rejected = self.run_board("boards", "retire", "--board", entry["board_id"], ok=False)
        self.assertIn("unresolved notices", rejected.stderr)
        self.run_board("boards", "dispose-notices", "--board", entry["board_id"],
                       "--notice-id", 99, "--reason", "wrong", ok=False)
        self.run_board("boards", "dispose-notices", "--board", entry["board_id"],
                       "--notice-id", 1, "--reason", "Recipient unreachable; owner retains follow-up")
        self.run_board("boards", "retire", "--board", entry["board_id"])
        self.run_board("boards", "archive", "--board", entry["board_id"])
        archived = self.obj("boards", "show", "--board", entry["board_id"])
        with sqlite3.connect(self.home / "catalog.sqlite3") as db:
            disposition = db.execute("SELECT notification_id,delivery_state,reason FROM notice_dispositions")
            self.assertEqual(disposition.fetchone(), (1, "pending", "Recipient unreachable; owner retains follow-up"))
            self.assertIn('"count": 1', db.execute("SELECT detail FROM changes WHERE event='notices_disposed'").fetchone()[0])
        with sqlite3.connect(archived["snapshot_path"]) as db:
            self.assertEqual(db.execute("SELECT delivery_state FROM notification_outbox").fetchone()[0], "pending")

    def test_membership_departure_requires_exact_notice_settlement(self):
        for route in ("queue", "managed"):
            with self.subTest(route=route):
                entry = self.create(f"departure-{route}")
                board = entry["board_id"]
                self.join(board, A)
                self.join(board, B, route=route)
                self.open(board)
                self.open(board, title="Second notice")
                with sqlite3.connect(entry["db_path"]) as db:
                    states = [row[0] for row in db.execute(
                        "SELECT delivery_state FROM notification_outbox ORDER BY notification_id")]
                self.assertEqual(states, ["pending" if route == "queue" else "managed_pending"] * 2)
                for command in (("leave", "--session", B),
                                ("heartbeat", "--session", B, "--status", "completed"),
                                ("register", "--session", B, "--role", "root", "--status", "completed")):
                    rejected = self.run_board("--board", board, *command, actor=B, ok=False)
                    self.assertIn("unresolved incoming notices", rejected.stderr)
                self.run_board("boards", "dispose-notices", "--board", board,
                               "--notice-id", 1, "--reason", "Recipient departure; explicit owner follow-up")
                rejected = self.run_board("--board", board, "leave", "--session", B,
                                          actor=B, ok=False)
                self.assertIn("[2]", rejected.stderr)
                self.run_board("boards", "dispose-notices", "--board", board,
                               "--notice-id", 2, "--reason", "Recipient departure; second notice follow-up")
                self.run_board("--board", board, "leave", "--session", B, actor=B)
                with sqlite3.connect(entry["db_path"]) as db:
                    self.assertEqual([row[0] for row in db.execute(
                        "SELECT delivery_state FROM notification_outbox ORDER BY notification_id")],
                        states)

    def test_archived_read_verifies_hash_and_purge_resume_after_partial_delete(self):
        entry = self.create("purge-recover")
        board = entry["board_id"]
        self.run_board("boards", "retire", "--board", board)
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("DROP TABLE scope_transfers")  # archived pre-transfer schema
        self.run_board("boards", "archive", "--board", board)
        self.assertEqual(self.obj("--board", board, "scope-transfers"), [])
        archived = self.obj("boards", "show", "--board", board)
        snapshot = Path(archived["snapshot_path"])
        with snapshot.open("ab") as handle:
            handle.write(b"tamper")
        self.assertIn("hash mismatch", self.run_board("--board", board, "read", ok=False).stderr)
        # Simulate interruption after durable purge_started and the first unlink.
        with catalog.catalog(self.home) as db, catalog.transaction(db):
            db.execute("UPDATE boards SET state='purging' WHERE board_id=?", (board,))
        Path(entry["db_path"]).unlink()
        self.run_board("boards", "hold", "--board", board, "--enabled", "yes", ok=False)
        self.run_board("boards", "purge", "--board", board, "--confirm-id", board,
                       "--irreversible")
        self.assertEqual(self.obj("boards", "show", "--board", board)["state"], "tombstoned")
        self.assertFalse(snapshot.exists())

    def test_registration_rejects_bound_uuid_and_hardlink_and_stages_legacy(self):
        entry = self.create("bound")
        self.run_board("boards", "register-path", "--alias", "wrong-id", "--name", "Wrong",
                       "--db", entry["db_path"], ok=False)
        alias = Path(self.temp.name) / "hardlink.sqlite3"
        os.link(entry["db_path"], alias)
        self.run_board("boards", "register-path", "--alias", "hardlink", "--name", "Hardlink",
                       "--db", alias, "--id", entry["board_id"], ok=False)
        legacy = self.legacy_file("legacy-pending.sqlite3")
        pending = self.obj("boards", "register-path", "--alias", "pending", "--name", "Pending",
                           "--db", legacy)
        self.assertEqual(pending["state"], "pending_migration")
        self.run_board("--board", "pending", "read", ok=False)
        backup = Path(self.temp.name) / "pending-backup.sqlite3"
        self.run_board("boards", "migrate", "--board", "pending", "--backup", backup)
        migrated = self.obj("boards", "show", "--board", "pending")
        self.assertEqual(migrated["state"], "active")
        self.assertEqual(migrated["migration_backup"], str(backup))

    def test_staged_migration_resume_and_rollback(self):
        legacy = self.legacy_file("staged.sqlite3")
        entry = self.obj("boards", "register-path", "--alias", "staged", "--name", "Staged",
                         "--db", legacy)
        backup = Path(self.temp.name) / "stage-backup.sqlite3"
        # Simulate interruption immediately after catalog staging.
        digest, _ = board_cli._snapshot(str(legacy), backup)
        with catalog.catalog(self.home) as db, catalog.transaction(db):
            db.execute("UPDATE boards SET state='migrating',migration_backup=?,migration_sha256=? "
                       "WHERE board_id=?", (str(backup), digest, entry["board_id"]))
        self.run_board("--board", "staged", "read", ok=False)
        self.run_board("boards", "migrate", "--board", "staged", "--resume")
        self.assertEqual(self.obj("boards", "show", "--board", "staged")["state"], "active")
        with catalog.catalog(self.home) as db, catalog.transaction(db):
            db.execute("UPDATE boards SET state='migrating' WHERE board_id=?", (entry["board_id"],))
        self.run_board("boards", "migrate-rollback", "--board", "staged")
        self.assertEqual(self.obj("boards", "show", "--board", "staged")["state"], "pending_migration")
        with sqlite3.connect(legacy) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)

    def test_single_watch_releases_lifecycle_lock_during_wait(self):
        entry = self.create("watch-retire")
        self.join(entry["board_id"], A)
        env = os.environ.copy()
        env["CODEX_SESSION_ID"] = A
        watcher = subprocess.Popen([sys.executable, str(CLI), "--home", str(self.home),
                                    "--board", entry["board_id"], "watch", "--session", A,
                                    "--timeout", "4"], env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            time.sleep(0.3)
            started = time.monotonic()
            self.run_board("boards", "retire", "--board", entry["board_id"])
            self.assertLess(time.monotonic() - started, 2)
            _, stderr = watcher.communicate(timeout=5)
            self.assertEqual(watcher.returncode, 2, stderr)
        finally:
            if watcher.poll() is None:
                watcher.kill()
                watcher.communicate()

    def test_child_scope_requires_expiry_and_parent_settlement(self):
        entry = self.create("child-scope")
        board = entry["board_id"]
        self.join(board, A)
        self.run_board("--board", board, "register", "--session", B, "--role", "child",
                       "--parent-session", A, "--scope", "review", actor=B, ok=False)
        self.join(board, B, role="child", extra=("--parent-session", A, "--scope", "review",
                                                  "--expires-at", "2030-01-01T00:00:00Z"))
        self.run_board("--board", board, "leave", "--session", A, actor=A, ok=False)
        self.run_board("--board", board, "heartbeat", "--session", B,
                       "--status", "paused", actor=B)
        self.run_board("--board", board, "leave", "--session", A, actor=A, ok=False)
        self.run_board("--board", board, "scope-transfer", "--session", B, "--child", A,
                       "--reason", "Invalid child claim", actor=B, ok=False)
        self.run_board("--board", board, "scope-transfer", "--session", A, "--child", B,
                       "--reason", "Independent campaign owner accepts this membership", actor=A)
        transfers = self.obj("--board", board, "scope-transfers", "--session", B)
        self.assertEqual((transfers[0]["parent_session"], transfers[0]["scope"]), (A, "review"))
        self.run_board("--board", board, "leave", "--session", A, actor=A)
        with sqlite3.connect(entry["db_path"]) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM scope_transfers").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT role,parent_session,scope FROM sessions WHERE session=?",
                                        (B,)).fetchone(), ("root", None, None))
        self.run_board("--board", board, "heartbeat", "--session", B,
                       "--status", "active", actor=B)

    def test_child_cannot_reactivate_after_parent_departure(self):
        entry = self.create("child-expiry")
        board = entry["board_id"]
        self.join(board, A)
        self.join(board, B, role="child", extra=("--parent-session", A, "--scope", "task",
                                                  "--expires-at", "2030-01-01T00:00:00Z"))
        with sqlite3.connect(entry["db_path"]) as db:
            db.execute("UPDATE sessions SET status='paused', expires_at='2000-01-01T00:00:00Z' "
                       "WHERE session=?", (B,))
        self.run_board("--board", board, "leave", "--session", A, actor=A)
        self.run_board("--board", board, "heartbeat", "--session", B,
                       "--status", "active", actor=B, ok=False)
        self.run_board("--board", board, "register", "--session", B, "--role", "child",
                       "--expires-at", "2030-01-01T00:00:00Z", actor=B, ok=False)

    def test_lifecycle_lock_serializes_catalog_writes_and_rechecks_state(self):
        cases = [
            ("invite", ["--session", B], "retired", "only active"),
            ("associate", ["--type", "campaign", "--id", "late"], "archived", "only active or retired"),
            ("hold", ["--enabled", "yes"], "purging", "cannot change holds"),
        ]
        for index, (action, extra, next_state, error) in enumerate(cases):
            entry = self.create(f"lock-{index}")
            env = os.environ.copy()
            env.pop("CODEX_SESSION_ID", None)
            with catalog.lifecycle_lock(entry, self.home, exclusive=True):
                proc = subprocess.Popen([sys.executable, str(CLI), "--home", str(self.home),
                                         "boards", action, "--board", entry["board_id"], *extra],
                                        env=env, text=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                time.sleep(0.15)
                self.assertIsNone(proc.poll(), action)
                with catalog.catalog(self.home) as db, catalog.transaction(db):
                    db.execute("UPDATE boards SET state=? WHERE board_id=?",
                               (next_state, entry["board_id"]))
            _, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 2, stderr)
            self.assertIn(error, stderr)

    def test_existing_catalog_schema_upgrades_without_losing_links(self):
        entry = self.create("old-catalog")
        self.run_board("boards", "associate", "--board", entry["board_id"],
                       "--type", "campaign", "--id", "retain")
        # Recreate the prior restrictive state CHECK with its existing columns.
        with sqlite3.connect(self.home / "catalog.sqlite3") as db:
            db.execute("PRAGMA foreign_keys=OFF")
            db.execute("CREATE TABLE boards_old AS SELECT * FROM boards")
            db.execute("DROP TABLE boards")
            db.execute("""CREATE TABLE boards (
                board_id TEXT PRIMARY KEY, alias TEXT UNIQUE, display_name TEXT,
                state TEXT CHECK(state IN ('active','retired','archived','tombstoned')),
                db_path TEXT UNIQUE, temporary_test INTEGER, purge_allowed INTEGER,
                retention_hold INTEGER, membership_policy TEXT, allowed_routes TEXT,
                created_at TEXT, changed_at TEXT, snapshot_path TEXT,
                snapshot_sha256 TEXT, purged_at TEXT)""")
            db.execute("""INSERT INTO boards SELECT board_id,alias,display_name,state,db_path,
                temporary_test,purge_allowed,retention_hold,membership_policy,allowed_routes,
                created_at,changed_at,snapshot_path,snapshot_sha256,purged_at FROM boards_old""")
            db.execute("DROP TABLE boards_old")
        upgraded = self.obj("boards", "show", "--board", entry["board_id"])
        self.assertEqual(upgraded["artifacts"][0]["identifier"], "retain")
        self.assertIn("migration_backup", upgraded)


if __name__ == "__main__":
    unittest.main()
