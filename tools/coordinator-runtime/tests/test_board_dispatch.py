"""Real board API on newly owned synthetic SQLite fixtures; no live board access."""

import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, result, collect, queued
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import LUNA, Refusal, encode, ident
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


class BoardFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordinator-board-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.home = Path(self.config["board_home"])
        self.substrate = module_at(self.config["board_library"], "board_store")
        self.catalog = module_at(self.config["board_library"], "catalog")
        self.owner, self.sender = self.config["roles"]["Work"]["owner"], ident()
        with self.catalog.catalog(self.home) as conn:
            entry = self.catalog.create(conn, self.home, "fixture", "Synthetic isolated fixture",
                board_id=self.config["roles"]["Work"]["board_id"], temporary_test=True)
        self.path = Path(entry["db_path"])
        with self.substrate.database(str(self.path)) as conn:
            self.substrate.bind_board(conn, entry["board_id"], initialize=True)
            self.register(conn, self.owner, "work")
            self.register(conn, self.sender, "fixture-sender")
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.board = Board(self.config, "Work")
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.owner}):
            grant = self.board.grant(self.store, "Synthetic fixture owner grants only this test")
        self.store.enroll("Work", grant)

    def register(self, conn, session, role):
        args = self.substrate.parser().parse_args(["register", "--session", session, "--role", role,
                                                  "--profile", ".codex", "--route", "managed"])
        with patch.dict(os.environ, {"CODEX_SESSION_ID": session}):
            self.substrate.register(conn, args)

    def post(self, *, plain=False, text="Actual fixture finding"):
        command = ["post" if plain else "open", "--session", self.sender, "--topic", "fixture",
                   "--kind", "finding", "--text", text, "--to", self.owner]
        if not plain:
            command += ["--title", "Owned fixture", "--no-push"]
        args = self.substrate.parser().parse_args(command)
        with self.substrate.database(str(self.path)) as conn:
            with patch.dict(os.environ, {"CODEX_SESSION_ID": self.sender}):
                return self.substrate.post(conn, args) if plain else self.substrate.open_thread(conn, args)

    def intake(self):
        message = self.board.scan(self.store)[0]
        self.store.ingest(message, cursor=message["post"])
        return message

    def classify(self, message):
        attempt, actual = self.store.claim_classification()
        collect(self.store, attempt, {"event_id": actual["id"], "task": "work-integrator", "package": None, "reason": "fixture finding"})
        self.store.commit_classification(attempt)
        return attempt

    def scalar(self, sql, values=()):
        with sqlite3.connect(self.path) as conn:
            return conn.execute(sql, values).fetchone()[0]

    def test_A03_genuine_delegated_receipt_requires_durable_pair_real_actor_no_cursor(self):
        self.post()
        message = self.intake()
        self.assertRaises(Refusal, self.board.receipt, self.store, message["id"])
        self.assertEqual(self.scalar("SELECT delivery_state FROM notification_outbox"), "managed_pending")
        classifier = self.classify(message)
        # Actual automation actor deliberately is not a board member or the owner.
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.config["actor"]}):
            receipt = self.board.receipt(self.store, message["id"])
        self.assertEqual(receipt["owner"], self.owner)
        self.assertEqual(receipt["controller_actor"], self.config["actor"])
        self.assertEqual(receipt["classifier_actor"], self.store.attempt(classifier)["session"])
        self.assertEqual(receipt["kind"], "delegated-notice-receipt")
        self.assertEqual(self.scalar("SELECT delivery_state FROM notification_outbox"), "acknowledged")
        self.assertEqual(self.scalar("SELECT ack_seq FROM sessions WHERE session=?", (self.owner,)), 0)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM sessions"), 2)

    def test_A04_commit_before_ACK_restart_and_lost_ACK_reply_reconcile_once(self):
        self.post()
        message = self.intake()
        self.classify(message)
        restarted = Store(self.config)
        self.addCleanup(restarted.close)
        self.assertEqual(len(restarted.rows("SELECT * FROM queue")), 1)
        # Simulate actual board commit followed by controller loss before outcome recording.
        receipt = self.board.receipt(restarted, message["id"])
        self.assertEqual(restarted.one("SELECT ack FROM events")["ack"], "ready")
        runtime = Dispatcher(restarted, models=object(), boards={"Work": self.board})
        runtime.receipts()
        self.assertEqual(restarted.one("SELECT ack FROM events")["ack"], "done")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM coordinator_receipts_v1"), 1)
        self.assertEqual(len(restarted.rows("SELECT * FROM queue")), 1)
        self.assertEqual(json.loads(restarted.one("SELECT ack_receipt FROM events")["ack_receipt"]), receipt)

    def test_A04_actual_crash_after_durable_pair_before_ACK(self):
        self.post()
        message = self.intake()
        config_path = Path(self.temp.name) / "configuration.json"
        config_path.write_text(encode(self.config))
        script = """import json,os,sys
from coordinator_runtime.store import Store
from support import collect
s=Store(json.load(open(sys.argv[1])))
a,e=s.claim_classification()
collect(s,a,{'event_id':e['id'],'task':'work-integrator','package':None,'reason':'fixture classification'})
s.commit_classification(a)
os._exit(74)
"""
        pythonpath = os.pathsep.join([str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)])
        run = subprocess.run([sys.executable, "-c", script, str(config_path)], env={**os.environ, "PYTHONPATH": pythonpath})
        self.assertEqual(run.returncode, 74)
        self.assertEqual(len(self.store.rows("SELECT * FROM queue")), 1)
        self.assertEqual(self.scalar("SELECT delivery_state FROM notification_outbox"), "managed_pending")
        receipt = self.board.receipt(self.store, message["id"])
        self.assertEqual(receipt["post"], message["post"])

    def test_plain_posts_get_distinct_processing_receipt_not_notice_ACK(self):
        self.post(plain=True)
        message = self.intake()
        self.assertIsNone(message["notice"])
        self.classify(message)
        receipt = self.board.receipt(self.store, message["id"])
        self.assertEqual(receipt["kind"], "plain-post-receipt")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM notification_outbox"), 0)

    def test_A04_crash_inside_classification_queue_transaction_rolls_back_both(self):
        self.post()
        message = self.intake()
        a, actual = self.store.claim_classification()
        collect(self.store, a, {"event_id": actual["id"], "task": "work-integrator", "package": None, "reason": "fixture"})
        config_path = Path(self.temp.name) / "crash-config.json"
        config_path.write_text(encode(self.config))
        script = """import json,os,sys
from coordinator_runtime.store import Store
s=Store(json.load(open(sys.argv[1])))
original=s.db
class Crash:
 def __getattr__(self,k): return getattr(original,k)
 def execute(self,sql,args=()):
  if sql.startswith('UPDATE events SET classification='): os._exit(76)
  return original.execute(sql,args)
s.db=Crash()
s.commit_classification(sys.argv[2])
"""
        run = subprocess.run([sys.executable, "-c", script, str(config_path), a],
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])})
        self.assertEqual(run.returncode, 76)
        self.assertEqual(self.store.rows("SELECT * FROM queue"), [])
        self.assertIsNone(self.store.one("SELECT classification FROM events")["classification"])
        self.assertEqual(self.scalar("SELECT delivery_state FROM notification_outbox"), "managed_pending")
        # Reuse the actual durable collected answer, not a redundant classifier/model.
        restarted = Store(self.config)
        self.addCleanup(restarted.close)
        runtime = Dispatcher(restarted, models=object(), boards={"Work": self.board})
        runtime.reconcile_classifications()
        runtime.receipts()
        self.assertEqual(len(restarted.rows("SELECT * FROM queue")), 1)
        self.assertEqual(self.scalar("SELECT delivery_state FROM notification_outbox"), "acknowledged")

    def test_A04_actual_crash_after_board_ACK_commit_is_reconciled_by_audit(self):
        self.post()
        message = self.intake()
        self.classify(message)
        config_path = Path(self.temp.name) / "ack-crash.json"
        config_path.write_text(encode(self.config))
        script = """import json,os,sys
from coordinator_runtime.store import Store
from coordinator_runtime.board import Board
c=json.load(open(sys.argv[1])); s=Store(c)
Board(c,'Work').receipt(s,sys.argv[2])
os._exit(75)
"""
        run = subprocess.run([sys.executable, "-c", script, str(config_path), message["id"]],
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])})
        self.assertEqual(run.returncode, 75)
        self.assertEqual(self.scalar("SELECT delivery_state FROM notification_outbox"), "acknowledged")
        self.assertEqual(self.store.one("SELECT ack FROM events")["ack"], "ready")
        runtime = Dispatcher(self.store, models=object(), boards={"Work": self.board})
        runtime.receipts()
        self.assertEqual(self.store.one("SELECT ack FROM events")["ack"], "done")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM coordinator_receipts_v1"), 1)

    def test_grant_revocation_identity_profile_private_access_and_sending_hold(self):
        self.post()
        message = self.intake()
        self.classify(message)
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE notification_outbox SET delivery_state='sending'")
        self.assertRaises(Refusal, self.board.receipt, self.store, message["id"])
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE notification_outbox SET delivery_state='managed_pending'")
            conn.execute("UPDATE sessions SET profile='.codex3' WHERE session=?", (self.owner,))
        self.assertRaises(Refusal, self.board.scan, self.store)
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE sessions SET profile='.codex' WHERE session=?", (self.owner,))
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.owner}):
            self.board.revoke(self.store.enrollment("Work")["grant_id"])
        self.assertRaises(Refusal, self.board.receipt, self.store, message["id"])


class FakeModels:
    """Deterministic model doubles, with explicit fresh invocation/actor records."""
    def __init__(self):
        self.calls = []

    async def run(self, store, attempt, prompt, spec, schema=None):
        row = store.attempt(attempt)
        store.begin(attempt, {"fake_model": True})
        session = ident()
        store.session(attempt, session)
        self.calls.append({"attempt": attempt, "session": session, "kind": row["kind"], "prompt": prompt,
                           "binding": json.loads(row["binding"])})
        if row["kind"] == "classifier":
            message = store.event(row["event"])
            answer = {"event_id": message["id"], "task": message["allowed_tasks"][0],
                      "package": message["package"], "reason": "fake selects typed meaningful route"}
        elif row["kind"] == "task":
            job = store.job(row["job"])
            category = "proposal" if job["phase"] == "proposer" else "complete"
            if job["role"] == "Reviews" and job["phase"] == "integrator":
                category = "consolidated"
            answer = result(category=category)
        else:
            answer = {"profile": ".codex3", "remaining": "explicit held work", "rationale": "fixture diagnosis"}
        await asyncio.sleep(0)
        return {"exit": 0, "result": answer, "capture": "complete", "cleanup": "done", "error": None,
                "detail": {"fixture": True, "resume_disposition": "unavailable-after-ephemeral-owner-exit"}}


class AutomaticDispatcher(unittest.IsolatedAsyncioTestCase):
    async def test_automatic_next_batches_and_fresh_response_classifications(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-dispatch-fixture-") as temp:
            config = config_at(temp)
            store = enrolled(config)
            self.addCleanup(store.close)
            models = FakeModels()
            runtime = Dispatcher(store, models=models, boards={})
            first = event(config, "first", task="work-proposer")
            store.ingest(first)
            for _ in range(12):
                await runtime.tick()
            second = event(config, "second", role="Reviews")
            store.ingest(second)
            for _ in range(35):
                await runtime.tick()
            await asyncio.gather(*runtime.active)
            await runtime.tick()
            self.assertEqual(runtime.runtime_errors, {})
            self.assertTrue(all(r["state"] == "closed" for r in store.rows("SELECT state FROM jobs")))
            self.assertTrue(all(r["processed_at"] is not None for r in store.rows("SELECT processed_at FROM events")))
            classified = [c for c in models.calls if c["kind"] == "classifier"]
            self.assertEqual(len(classified), len(store.rows("SELECT * FROM events")))
            self.assertTrue(all(c["binding"] == LUNA for c in classified))
            self.assertEqual(len({c["session"] for c in models.calls}), len(models.calls))
            self.assertTrue(any('source_attempt' in c["prompt"] for c in classified))
            self.assertTrue(any('Root code builders retain commit AND push' in c["prompt"] for c in models.calls))


if __name__ == "__main__":
    unittest.main()
