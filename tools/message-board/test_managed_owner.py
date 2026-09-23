"""Temporary shared-board integration tests for the managed app-server owner."""

import asyncio
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

import active_listener
import board_store
import catalog
import managed_owner as mo

CLI = Path(__file__).with_name("board.py")
FAKE = r'''#!/usr/bin/env python3
import json, os, re, sys, threading, time, uuid
thread = None
turns = []
active = False
state_path = os.environ["FAKE_STATE_PATH"]
lock = threading.Lock()
def send(obj):
    with lock:
        print(json.dumps(obj), flush=True)
def save():
    with open(state_path, "w") as state:
        json.dump({"thread":thread,"turns":turns}, state)
def finish(turn, prompt):
    global active
    time.sleep(float(os.environ.get("FAKE_DELAY", ".04")))
    marker = re.search(r"BOARD-(?:BOOTSTRAP-[A-F0-9]+|NOTICE-[0-9a-f-]+-[A-F0-9]+)", prompt)
    answer = marker.group() if marker else "HUMAN-COMPLETE"
    if os.environ.get("FAKE_NO_MARKER") and marker and "NOTICE" in marker.group():
        answer = "MISSING-MARKER"
    turn.update(status="completed", items=[{"type":"agentMessage", "phase":"final_answer", "text":answer}])
    active = False
    save()
    if not os.environ.get("FAKE_NO_COMPLETION"):
        send({"method":"turn/completed", "params":{"threadId":thread,"turn":turn}})
for line in sys.stdin:
    req = json.loads(line)
    if "id" not in req:
        continue
    mid, method = req["id"], req["method"]
    if method == "initialize":
        result = {"codexHome":os.environ["CODEX_HOME"]}
    elif method == "thread/start":
        thread = str(uuid.uuid4())
        save()
        result = {"thread":{"id":thread,"sessionId":thread}}
    elif method == "thread/resume":
        with open(state_path) as state:
            stored = json.load(state)
        if req["params"]["threadId"] != stored["thread"]:
            send({"id":mid,"error":{"message":"wrong thread"}})
            continue
        thread, turns = stored["thread"], stored["turns"]
        result = {"thread":{"id":thread,"status":{"type":"idle"},"turns":turns}}
    elif method == "thread/read":
        history = json.loads(json.dumps(turns))
        if os.environ.get("FAKE_HIDE_HISTORY"):
            history = []
        result = {"thread":{"id":thread,"status":{"type":"active" if active else "idle"},"turns":history}}
    elif method == "turn/start":
        prompt = req["params"]["input"][0]["text"]
        if os.environ.get("FAKE_DROP_START") and "BOOTSTRAP" not in prompt:
            sys.exit(0)
        if active:
            send({"id":mid,"error":{"message":"overlap"}})
            continue
        active = True
        turn = {"id":str(uuid.uuid4()),"status":"inProgress","items":[],"prompt":prompt}
        turns.append(turn)
        save()
        send({"id":mid,"result":{"turn":turn.copy()}})
        threading.Thread(target=finish,args=(turn,prompt),daemon=True).start()
        continue
    else:
        send({"id":mid,"error":{"message":method}})
        continue
    send({"id":mid,"result":result})
'''


class ManagedOwnerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 10

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shared-owner-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "board-home"
        self.journal = self.root / "owner.sqlite3"
        self.fake = self.root / "fake_codex"
        self.fake.write_text(FAKE)
        self.fake.chmod(0o700)
        self.state = self.root / "fake-state.json"
        self.writer = str(uuid.uuid4())
        self.items = [self.create("one"), self.create("two")]
        for item in self.items:
            self.cli("--board", item["board_id"], "register", "--session", self.writer,
                     "--role", "writer", actor=self.writer)
        self.env = patch.dict(os.environ, {"FAKE_STATE_PATH": str(self.state), "FAKE_DELAY": ".04"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def cli(self, *args, actor=None, ok=True):
        env = os.environ.copy()
        env.pop("CODEX_SESSION_ID", None)
        if actor:
            env["CODEX_SESSION_ID"] = actor
        result = subprocess.run([sys.executable, str(CLI), "--home", str(self.home), *map(str,args)],
                                text=True, capture_output=True, env=env, timeout=15)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stderr)
        return result

    def create(self, alias, *, invited=False):
        return json.loads(self.cli("boards", "create", "--alias", alias, "--name", alias,
                                   "--temporary-test", *( ["--membership", "invited"] if invited else []),
                                   "--json").stdout)

    def conn(self, item):
        return sqlite3.connect(item["db_path"])

    def owner(self, boards=None):
        return mo.ManagedOwner(home=self.home, boards=boards or [item["board_id"] for item in self.items],
            journal=self.journal, profile=".codex2", cwd=self.root, campaign="test", role="owner",
            codex=str(self.fake), recheck=.04, verify=False)

    async def wait_for(self, predicate, timeout=12):
        end = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < end:
            if predicate():
                return
            await asyncio.sleep(.02)
        self.fail("condition did not arrive")

    async def start(self, boards=None):
        owner = self.owner(boards)
        task = asyncio.create_task(owner.run())
        await self.wait_for(lambda: task.done() or owner.server is not None)
        if task.done():
            await task
        return owner, task

    async def stop(self, owner, task):
        await asyncio.to_thread(mo.control, self.journal, "stop")
        await asyncio.wait_for(task, 5)
        owner.close()

    def turns(self):
        with sqlite3.connect(self.journal) as db:
            return db.execute("SELECT seq,kind,state,board_id,notice_id,prompt FROM turns ORDER BY seq").fetchall()

    def notices(self):
        with sqlite3.connect(self.journal) as db:
            return db.execute("SELECT board_id,id,state,recipient_ack_at FROM notices ORDER BY board_id,id").fetchall()

    def post(self, item, recipient, title="Question"):
        result = self.cli("--board", item["board_id"], "open", "--session", self.writer,
                          "--topic", "work", "--title", title, "--text", "Body " + title,
                          "--to", recipient, "--no-push", actor=self.writer)
        with self.conn(item) as db:
            return db.execute("SELECT max(notification_id) FROM notification_outbox").fetchone()[0]

    async def test_bootstrap_before_registration_and_two_colliding_notices(self):
        owner, task = await self.start()
        with sqlite3.connect(self.journal) as db:
            bootstrap = db.execute("SELECT state,final_text FROM turns WHERE kind='bootstrap'").fetchone()
        self.assertEqual(bootstrap[0], "completed")
        self.assertIn("BOARD-BOOTSTRAP", bootstrap[1])
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='app_server_codex_home'").fetchone()[0],
                             str(Path.home() / ".codex2"))
        for item in self.items:
            with self.conn(item) as db:
                row = db.execute("SELECT route,owner,status FROM sessions WHERE session=?",
                                 (owner.thread_id,)).fetchone()
                self.assertEqual(row, ("managed", 1, "active"))
                self.assertEqual(db.execute("SELECT event FROM membership_events WHERE session=?",
                                            (owner.thread_id,)).fetchone()[0], "register")
            self.cli("--board", item["board_id"], "register", "--session", owner.thread_id,
                     "--role", "root", "--route", "queue", actor=owner.thread_id, ok=False)
            self.assertEqual(self.post(item, owner.thread_id), 1)
        await self.wait_for(lambda: len([row for row in self.turns() if row[1] == "notice" and row[2] == "completed"]) == 2)
        self.assertEqual({(row[0], row[1]) for row in self.notices()},
                         {(item["board_id"], 1) for item in self.items})
        for item in self.items:
            with self.conn(item) as db:
                row = db.execute("SELECT route,delivery_state,attempt_count,acknowledged_at "
                                 "FROM notification_outbox WHERE notification_id=1").fetchone()
                self.assertEqual(row, ("managed", "managed_pending", 0, None))
        self.assertTrue(all(row[3] in row[5] and "board.py" in row[5]
                            for row in self.turns() if row[1] == "notice"))
        self.cli("--board", self.items[0]["board_id"], "ack-notice", "--session", owner.thread_id,
                 "--notification", "1", actor=owner.thread_id)
        await self.wait_for(lambda: any(row[0] == self.items[0]["board_id"] and row[3]
                                         for row in self.notices()))
        self.assertIsNone([row[3] for row in self.notices() if row[0] == self.items[1]["board_id"]][0])
        await self.stop(owner, task)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='last_app_server_exit_code'").fetchone()[0],
                             "-15")

    async def test_active_deferral_idle_wake_and_human_fairness(self):
        with patch.dict(os.environ, {"FAKE_DELAY": ".8"}):
            owner, task = await self.start()
            await asyncio.to_thread(mo.control, self.journal, "prompt", "First human")
            await self.wait_for(lambda: owner.active is not None)
            self.post(self.items[0], owner.thread_id, "first notice")
            self.post(self.items[1], owner.thread_id, "second notice")
            await asyncio.to_thread(mo.control, self.journal, "prompt", "Second human")
            self.assertEqual(len([row for row in self.turns() if row[1] == "notice"]), 0)
            await self.wait_for(lambda: len([row for row in self.turns() if row[2] == "completed"]) >= 5)
        with self.state.open() as state:
            started = json.load(state)["turns"]
        kinds = [("bootstrap" if "BOOTSTRAP" in turn["prompt"] else
                  "notice" if "NOTICE" in turn["prompt"] else "human") for turn in started]
        self.assertEqual(kinds, ["bootstrap", "human", "notice", "human", "notice"])
        human_prompts = [turn["prompt"] for turn in started if "Owner-operator task:" in turn["prompt"]]
        self.assertEqual(len(human_prompts), 2)
        self.assertTrue(all("paraphrases or inferred answers" in prompt and
                            "authorizes transfer for both audiences" in prompt
                            for prompt in human_prompts))
        await self.stop(owner, task)

    async def test_restart_exact_history_and_add_board(self):
        owner, task = await self.start([self.items[0]["board_id"]])
        self.post(self.items[0], owner.thread_id)
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "completed" for row in self.turns()))
        ident = owner.thread_id
        await self.stop(owner, task)
        self.assertEqual(self.post(self.items[0], ident, "offline notice"), 2)
        owner2, task2 = await self.start()
        self.assertEqual(owner2.thread_id, ident)
        with self.conn(self.items[1]) as db:
            self.assertEqual(db.execute("SELECT route FROM sessions WHERE session=?", (ident,)).fetchone()[0], "managed")
        self.assertEqual(self.post(self.items[1], ident), 1)
        await self.wait_for(lambda: len([row for row in self.turns() if row[1] == "notice" and row[2] == "completed"]) == 3)
        await self.stop(owner2, task2)
        with patch.dict(os.environ, {"FAKE_HIDE_HISTORY": "1"}):
            owner3 = self.owner()
            with self.assertRaises(mo.OwnerError):
                await owner3.run()
            owner3.close()

    async def test_retired_board_and_one_listener_conflict_fail_closed(self):
        owner, task = await self.start()
        self.cli("boards", "retire", "--board", self.items[1]["board_id"])
        with self.assertRaises(mo.OwnerError):
            await asyncio.wait_for(task, 3)
        owner.close()
        # A fresh journal has no permission to start on a retired board.
        with self.assertRaises(mo.OwnerError):
            self.owner()

    async def test_listener_conflict_and_uncertain_turn(self):
        owner, task = await self.start()
        self.post(self.items[0], owner.thread_id)
        await self.wait_for(lambda: owner.active is not None)
        item = self.items[1]
        with self.conn(item) as db:
            identity = active_listener._db_identity(db)
        import socket
        blocker = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        blocker.bind(active_listener._address(owner.thread_id, identity))
        try:
            with self.assertRaises(mo.ListenerConflict):
                await asyncio.wait_for(task, 3)
            self.assertEqual([row[2] for row in self.turns() if row[1] == "notice"], ["completed"])
            with sqlite3.connect(self.journal) as db:
                self.assertIsNotNone(db.execute("SELECT value FROM meta WHERE key='reconcile_required'").fetchone())
        finally:
            blocker.close()
            owner.close()

    async def test_uncertain_start_preserves_notice(self):
        with patch.dict(os.environ, {"FAKE_DROP_START": "1"}):
            owner, task = await self.start()
            self.post(self.items[0], owner.thread_id)
            with self.assertRaises(mo.OwnerError):
                await asyncio.wait_for(task, 3)
            self.assertEqual([row[2] for row in self.notices()], ["unconfirmed"])
            owner.close()

    async def test_missing_marker_blocks_pointer_receipt(self):
        with patch.dict(os.environ, {"FAKE_NO_MARKER": "1"}):
            owner, task = await self.start()
            self.post(self.items[0], owner.thread_id)
            with self.assertRaises(mo.OwnerError):
                await asyncio.wait_for(task, 3)
            self.assertEqual([row[2] for row in self.notices()], ["unconfirmed"])
            owner.close()

    async def test_completed_turn_and_notice_receipt_roll_back_together(self):
        owner, task = await self.start()
        original = owner._set_meta
        def fail_receipt(key, value):
            if key == "last_notice_board":
                raise OSError("journal receipt fault")
            return original(key, value)
        owner._set_meta = fail_receipt
        self.post(self.items[0], owner.thread_id)
        with self.assertRaises(OSError):
            await asyncio.wait_for(task, 3)
        with sqlite3.connect(self.journal) as db:
            turn = db.execute("SELECT state,final_text FROM turns WHERE kind='notice'").fetchone()
            notice = db.execute("SELECT state FROM notices").fetchone()
        self.assertEqual(turn, ("unconfirmed", None))
        self.assertEqual(notice, ("unconfirmed",))
        owner.close()

    async def test_explicit_leave_required_for_omitted_board(self):
        owner, task = await self.start()
        ident = owner.thread_id
        await self.stop(owner, task)
        with self.assertRaises(mo.OwnerError):
            self.owner([self.items[0]["board_id"]])
        self.cli("--board", self.items[1]["board_id"], "leave", "--session", ident, actor=ident)
        owner2, task2 = await self.start([self.items[0]["board_id"]])
        self.assertEqual(owner2.thread_id, ident)
        await self.stop(owner2, task2)

    async def test_invited_board_waits_for_exact_new_thread_invitation(self):
        invited = self.create("private", invited=True)
        owner = self.owner([invited["board_id"]])
        with self.assertRaises(mo.InvitationRequired):
            await owner.run()
        ident = owner.thread_id
        self.assertIsNotNone(ident)
        self.assertEqual(self.turns()[0][2], "completed")
        with self.conn(invited) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sessions WHERE session=?", (ident,)).fetchone())
        owner.close()
        self.cli("boards", "invite", "--board", invited["board_id"], "--session", ident)
        owner2, task2 = await self.start([invited["board_id"]])
        self.assertEqual(owner2.thread_id, ident)
        await self.stop(owner2, task2)

    async def test_offline_recipient_ack_is_recorded_without_pointer_turn(self):
        owner, task = await self.start()
        ident = owner.thread_id
        await self.stop(owner, task)
        self.post(self.items[0], ident)
        self.cli("--board", self.items[0]["board_id"], "ack-notice", "--session", ident,
                 "--notification", "1", actor=ident)
        owner2, task2 = await self.start()
        await self.wait_for(lambda: len(self.notices()) == 1)
        self.assertEqual(self.notices()[0][2], "recipient_acknowledged")
        self.assertIsNotNone(self.notices()[0][3])
        self.assertFalse(any(row[1] == "notice" for row in self.turns()))
        await self.stop(owner2, task2)

    async def test_cross_board_notice_order_rotates_with_backlog(self):
        owner, task = await self.start()
        ident = owner.thread_id
        await self.stop(owner, task)
        self.post(self.items[0], ident, "A first")
        self.post(self.items[0], ident, "A second")
        self.post(self.items[1], ident, "B first")
        owner2, task2 = await self.start()
        await self.wait_for(lambda: len([row for row in self.turns() if row[1] == "notice"
                                         and row[2] == "completed"]) == 3)
        order = [row[3] for row in self.turns() if row[1] == "notice"]
        self.assertEqual(order, [self.items[0]["board_id"], self.items[1]["board_id"],
                                 self.items[0]["board_id"]])
        await self.stop(owner2, task2)

    async def test_three_board_backlogs_each_get_a_turn_before_repeat(self):
        third = self.create("three")
        self.cli("--board", third["board_id"], "register", "--session", self.writer,
                 "--role", "writer", actor=self.writer)
        selected = [item["board_id"] for item in (*self.items, third)]
        owner, task = await self.start(selected)
        ident = owner.thread_id
        await self.stop(owner, task)
        for item, title in ((self.items[0], "A1"), (self.items[0], "A2"),
                            (self.items[1], "B1"), (self.items[1], "B2"), (third, "C1")):
            self.post(item, ident, title)
        owner2, task2 = await self.start(selected)
        await self.wait_for(lambda: len([row for row in self.turns() if row[1] == "notice"
                                         and row[2] == "completed"]) == 5)
        order = [row[3] for row in self.turns() if row[1] == "notice"]
        self.assertEqual(order[0], self.items[0]["board_id"])
        self.assertEqual(set(order[:3]), set(selected))
        await self.stop(owner2, task2)

    async def test_restart_rejects_copied_home_and_replaced_board_file(self):
        owner, task = await self.start()
        await self.stop(owner, task)
        copied = self.root / "copied-home"
        shutil.copytree(self.home, copied)
        with self.assertRaises(mo.OwnerError):
            mo.ManagedOwner(home=copied, boards=[item["board_id"] for item in self.items],
                journal=self.journal, profile=".codex2", cwd=self.root, campaign="test",
                role="owner", codex=str(self.fake), verify=False)
        path = Path(self.items[0]["db_path"])
        replacement = self.root / "replacement.sqlite3"
        with sqlite3.connect(path) as source, sqlite3.connect(replacement) as target:
            source.backup(target)
        os.replace(replacement, path)
        with self.assertRaises(mo.OwnerError):
            self.owner()

    async def test_same_file_notice_content_divergence_stops_restart(self):
        owner, task = await self.start()
        ident = owner.thread_id
        self.post(self.items[0], ident, "Original")
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "completed"
                                        for row in self.turns()))
        await self.stop(owner, task)
        with self.conn(self.items[0]) as db:
            db.execute("DROP TRIGGER posts_no_update")
            db.execute("UPDATE posts SET text='Restored divergent body' WHERE seq=1")
        owner2 = self.owner()
        with self.assertRaisesRegex(mo.OwnerError, "differs from journal"):
            await owner2.run()
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT state FROM turns WHERE kind='notice'").fetchone()[0],
                             "completed")
            self.assertIsNotNone(db.execute("SELECT value FROM meta WHERE key='reconcile_required'").fetchone())
        owner2.close()

    async def test_same_file_thread_link_divergence_stops_restart(self):
        owner, task = await self.start()
        self.post(self.items[0], owner.thread_id)
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "completed"
                                        for row in self.turns()))
        await self.stop(owner, task)
        with self.conn(self.items[0]) as db:
            db.execute("DROP TRIGGER thread_posts_no_delete")
            db.execute("DELETE FROM thread_posts WHERE post_seq=1")
        owner2 = self.owner()
        with self.assertRaisesRegex(mo.OwnerError, "not linked to thread"):
            await owner2.run()
        owner2.close()

    async def test_reply_reader_root_admission_divergence_stops_restart(self):
        item = self.items[0]
        self.cli("--board", item["board_id"], "open", "--session", self.writer,
                 "--topic", "topic", "--title", "Public root", "--text", "Initial context",
                 "--no-push", actor=self.writer)
        owner, task = await self.start()
        ident = owner.thread_id
        self.cli("--board", item["board_id"], "subscribe", "--session", ident,
                 "--thread", "1", actor=ident)
        self.cli("--board", item["board_id"], "reply", "--session", self.writer,
                 "--thread", "1", "--text", "Reply for owner", "--no-push", actor=self.writer)
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "completed"
                                        for row in self.turns()))
        await self.stop(owner, task)
        with self.conn(item) as db:
            db.execute("DROP TRIGGER posts_no_update")
            db.execute("UPDATE posts SET recipient=? WHERE seq=1", (self.writer,))
        owner2 = self.owner()
        with self.assertRaisesRegex(mo.OwnerError, "differs from journal"):
            await owner2.run()
        owner2.close()

    async def test_lost_acknowledgment_stops_restart_without_replaying_notice(self):
        owner, task = await self.start()
        ident = owner.thread_id
        await self.stop(owner, task)
        self.post(self.items[0], ident)
        self.cli("--board", self.items[0]["board_id"], "ack-notice", "--session", ident,
                 "--notification", "1", actor=ident)
        owner2, task2 = await self.start()
        await self.wait_for(lambda: self.notices() and self.notices()[0][2] == "recipient_acknowledged")
        await self.stop(owner2, task2)
        with self.conn(self.items[0]) as db:
            db.execute("UPDATE notification_outbox SET delivery_state='managed_pending', "
                       "acknowledged_at=NULL WHERE notification_id=1")
        owner3 = self.owner()
        with self.assertRaisesRegex(mo.OwnerError, "lost acknowledgment"):
            await owner3.run()
        self.assertFalse(any(row[1] == "notice" for row in self.turns()))
        with sqlite3.connect(self.journal) as db:
            self.assertIsNotNone(db.execute("SELECT value FROM meta WHERE key='reconcile_required'").fetchone())
        owner3.close()

    async def test_omitted_board_notice_metadata_divergence_blocks_restart(self):
        owner, task = await self.start()
        ident = owner.thread_id
        self.post(self.items[1], ident)
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "completed"
                                        for row in self.turns()))
        await self.stop(owner, task)
        self.cli("boards", "dispose-notices", "--board", self.items[1]["board_id"],
                 "--notice-id", "1", "--reason", "Retain pointer without recipient acknowledgment")
        self.cli("--board", self.items[1]["board_id"], "leave", "--session", ident, actor=ident)
        with self.conn(self.items[1]) as db:
            db.execute("UPDATE notification_outbox SET title='Divergent restored title' "
                       "WHERE notification_id=1")
        with self.assertRaisesRegex(mo.OwnerError, "differs from journal"):
            self.owner([self.items[0]["board_id"]])

    async def test_explicit_leave_records_late_acknowledgment_in_journal(self):
        owner, task = await self.start()
        ident = owner.thread_id
        self.post(self.items[1], ident)
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "completed"
                                        for row in self.turns()))
        await self.stop(owner, task)
        self.cli("--board", self.items[1]["board_id"], "ack-notice", "--session", ident,
                 "--notification", "1", actor=ident)
        self.cli("--board", self.items[1]["board_id"], "leave", "--session", ident, actor=ident)
        owner2, task2 = await self.start([self.items[0]["board_id"]])
        with sqlite3.connect(self.journal) as db:
            state, acknowledged = db.execute("SELECT state,recipient_ack_at FROM notices "
                "WHERE board_id=? AND id=1", (self.items[1]["board_id"],)).fetchone()
        self.assertEqual(state, "pointer_completed")
        self.assertIsNotNone(acknowledged)
        await self.stop(owner2, task2)

    async def test_explicit_leave_journals_first_seen_acknowledged_notice(self):
        owner, task = await self.start()
        ident = owner.thread_id
        await self.stop(owner, task)
        self.post(self.items[1], ident)
        self.cli("--board", self.items[1]["board_id"], "ack-notice", "--session", ident,
                 "--notification", "1", actor=ident)
        self.cli("--board", self.items[1]["board_id"], "leave", "--session", ident, actor=ident)
        owner2, task2 = await self.start([self.items[0]["board_id"]])
        with sqlite3.connect(self.journal) as db:
            row = db.execute("SELECT state,recipient_ack_at FROM notices WHERE board_id=? AND id=1",
                             (self.items[1]["board_id"],)).fetchone()
        self.assertEqual(row[0], "recipient_acknowledged")
        self.assertIsNotNone(row[1])
        self.assertFalse(any(row[1] == "notice" for row in self.turns()))
        await self.stop(owner2, task2)

    async def test_lifecycle_rebind_after_completed_turn_requires_reconciliation(self):
        owner, task = await self.start()
        original_arm = owner._arm
        def fail_after_completion():
            if owner.db.execute("SELECT 1 FROM turns WHERE kind='notice' "
                                "AND state='completed'").fetchone():
                raise mo.SelectionInactive("board retired during turn handoff")
            return original_arm()
        owner._arm = fail_after_completion
        self.post(self.items[0], owner.thread_id)
        with self.assertRaises(mo.SelectionInactive):
            await asyncio.wait_for(task, 3)
        self.assertEqual([row[2] for row in self.turns() if row[1] == "notice"], ["completed"])
        with sqlite3.connect(self.journal) as db:
            self.assertIsNotNone(db.execute("SELECT value FROM meta WHERE key='reconcile_required'").fetchone())
        owner.close()

    async def test_known_idle_retirement_then_explicit_leave_restores_other_board(self):
        owner, task = await self.start()
        ident = owner.thread_id
        self.cli("boards", "retire", "--board", self.items[1]["board_id"])
        with self.assertRaises(mo.SelectionInactive):
            await asyncio.wait_for(task, 3)
        owner.close()
        self.cli("--board", self.items[1]["board_id"], "leave", "--session", ident, actor=ident)
        owner2, task2 = await self.start([self.items[0]["board_id"]])
        self.assertEqual(owner2.thread_id, ident)
        await self.stop(owner2, task2)

    async def test_ack_during_queued_notice_allows_explicit_leave(self):
        owner, task = await self.start()
        ident = owner.thread_id
        original = owner._thread
        acknowledged = False
        async def ack_during_read():
            nonlocal acknowledged
            if not acknowledged and owner.db.execute(
                    "SELECT 1 FROM turns WHERE kind='notice' AND state='queued'").fetchone():
                acknowledged = True
                self.cli("--board", self.items[1]["board_id"], "ack-notice",
                         "--session", ident, "--notification", "1", actor=ident)
            return await original()
        owner._thread = ack_during_read
        self.post(self.items[1], ident)
        await self.wait_for(lambda: any(row[1] == "notice" and row[2] == "skipped_acknowledged"
                                        for row in self.turns()))
        await self.stop(owner, task)
        self.cli("--board", self.items[1]["board_id"], "leave", "--session", ident, actor=ident)
        owner2, task2 = await self.start([self.items[0]["board_id"]])
        self.assertEqual(owner2.thread_id, ident)
        await self.stop(owner2, task2)

    async def test_late_reply_reader_targets_the_triggering_post(self):
        owner, task = await self.start()
        ident = owner.thread_id
        await self.stop(owner, task)
        self.post(self.items[0], ident, "Long thread")
        with self.conn(self.items[0]) as db:
            thread_id = db.execute("SELECT max(thread_id) FROM threads").fetchone()[0]
            last_seq = 0
            for index in range(105):
                last_seq = db.execute("INSERT INTO posts(author,recipient,topic,kind,text,created_at) "
                    "VALUES(?,?,?,?,?,?)", (self.writer, ident, "work", "status",
                                         f"reply-{index}", board_store.utc_now())).lastrowid
                db.execute("INSERT INTO thread_posts(post_seq,thread_id) VALUES(?,?)",
                           (last_seq, thread_id))
            db.execute("INSERT INTO notification_outbox(recipient,thread_id,post_seq,event,title,"
                "sender,created_at,state_changed_at,route,delivery_state) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)", (ident, thread_id, last_seq, "reply", "Long thread",
                    self.writer, board_store.utc_now(), board_store.utc_now(), "managed", "managed_pending"))
        owner2, task2 = await self.start()
        await self.wait_for(lambda: len([row for row in self.turns() if row[1] == "notice" and row[2] == "completed"]) == 2)
        with sqlite3.connect(self.journal) as db:
            command = db.execute("SELECT read_cmd FROM notices WHERE board_id=? AND post_seq=?",
                                 (self.items[0]["board_id"], last_seq)).fetchone()[0]
        self.assertIn(f"--after {last_seq - 1} --limit 1", command)
        output = self.cli("--board", self.items[0]["board_id"], "thread", "--id", thread_id,
                          "--session", ident, "--after", last_seq - 1, "--limit", "1", actor=ident).stdout
        self.assertIn("reply-104", output)
        self.assertNotIn("reply-0\n", output)
        await self.stop(owner2, task2)
