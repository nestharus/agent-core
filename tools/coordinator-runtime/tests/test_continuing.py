"""R01-R03 use collected recheck signals, fresh synthetic source and boards.

No single-use recheck roots/scripts are replayed. Model returns are synthetic;
test_R02 additionally collects one actual owned fake-server OS process.
"""

import asyncio
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, event, queued, result, collect, ended_job
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.cleanup import sweep
from coordinator_runtime.cli import main
from coordinator_runtime.contracts import Refusal, digest, encode, ident, validate_config
from coordinator_runtime.dispatcher import Dispatcher, RESULT_SCHEMA
from coordinator_runtime.store import Store


class Continuing(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="correction2-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        shared = self.config["roles"]["Work"]["board_id"]
        for selected in self.config["roles"].values():
            selected["board_id"] = shared
        self.root = ident()
        recipients = {r: {"session": v["owner"], "profile": v["profile"], "board_role": v["board_role"]}
                      for r, v in self.config["roles"].items()}
        recipients["Root"] = {"session": self.root, "profile": ".codex2", "board_role": "execution-manager"}
        self.config["delivery"] = {"recipients": recipients, "alert_role": "Work", "alert_recipient": "Work"}
        self.config["tasks"]["work-integrator"].update(delivery_required=True, allowed_handoffs=["Root"])
        self.config["tasks"]["branch-integrator"].update(delivery_required=True, allowed_handoffs=["Root"],
                                                                       require_package_scope=True, scope_roots=[self.temp.name])
        self.config["tasks"]["reviews-proposer"].update(execution="owner", binding={"model": "gpt-xhigh", "provider": "opaque", "effort": "opaque"})
        self.config["tasks"]["reviews-proposer"]["responses"]["consolidated"] = ["reviews-integrator"]
        validate_config(self.config)
        substrate = self.substrate = module_at(self.config["board_library"], "board_store")
        catalog = module_at(self.config["board_library"], "catalog")
        home = Path(self.config["board_home"])
        with catalog.catalog(home) as cat:
            entry = catalog.create(cat, home, "correction2", "Fresh R01-R03 fixture", board_id=shared, temporary_test=True)
        self.path = Path(entry["db_path"])
        with substrate.database(str(self.path)) as conn:
            substrate.bind_board(conn, shared, initialize=True)
            for item in recipients.values():
                args = substrate.parser().parse_args(["register", "--session", item["session"], "--role", item["board_role"],
                                                      "--route", "managed", "--profile", item["profile"]])
                with patch.dict(os.environ, {"CODEX_SESSION_ID": item["session"]}):
                    substrate.register(conn, args)
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.boards = {}
        for role in ("Work", "Branch", "Reviews"):
            board = self.boards[role] = Board(self.config, role)
            owner = self.config["roles"][role]["owner"]
            with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
                grant = board.grant(self.store, "Actual synthetic owner delegation for R01-R03", delivery=True)
            self.store.enroll(role, grant)
            self.store.reconcile_legacy(role, owner, {"collector": owner, "evidence": ["synthetic prior closure"], "remaining_holds": []})
        self.runtime = Dispatcher(self.store, models=object(), boards=self.boards)

    def stage(self, role, delivery, actor, stage, **extra):
        with patch.dict(os.environ, {"CODEX_SESSION_ID": actor}):
            return self.boards[role].delivery_stage(delivery, stage, {"evidence": ["actual synthetic "+stage], **extra})

    def work_answer(self):
        return {**result(), "handoffs": [{"recipient": "Root", "kind": "work", "text": "Bounded independent work; commit AND push",
                "ref": "synthetic independent scope", "required": "settled"}], "no_handoff_reason": ""}

    def test_R01_originals_recur_without_alert_feedback_and_channel_recovers(self):
        board = self.boards["Work"]
        owner = self.config["roles"]["Work"]["owner"]
        grant = self.store.enrollment("Work")["grant_id"]
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            board.revoke(grant)
        self.store.record_operational_error("original-condition", {"error": "same continuing condition"})
        originals = []
        for cycle in range(8):
            emitted = self.store.emit_alerts()
            originals += [r["id"] for r in emitted if r["subject"] == "original-condition"]
            if cycle == 0:
                old = self.store.one("SELECT id FROM outboxes WHERE alert=?", (emitted[0]["id"],))["id"]
                self.store.record_operational_error(old, {"error": "old per-occurrence failure retained"}, kind="delivery-error")
            self.runtime.pump_deliveries()
            self.assertLessEqual(len(self.store.status()["operational_errors"]), 2)
            self.assertEqual(len(self.store.rows("SELECT * FROM alerts")), 1+2*cycle)
        self.assertEqual(len(set(originals)), 8)  # Recurrence is not deduplicated.
        self.assertFalse(self.store.one("SELECT active FROM operational_errors WHERE subject=?", (old,))["active"])
        channel = self.store.one("SELECT * FROM operational_errors WHERE subject='alert-channel:Work'")
        self.assertIn("revoked", json.loads(channel["detail"])["error"])
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='alert' AND error IS NOT NULL"))
        # Exact synthetic grant restoration models channel recovery, no new role/grant.
        with self.substrate.database(str(self.path)) as conn:
            conn.execute("UPDATE coordinator_grants_v1 SET revoked=NULL WHERE id=?", (grant,))
        self.runtime.pump_deliveries()
        self.assertFalse(self.store.one("SELECT * FROM operational_errors WHERE subject='alert-channel:Work'")["active"])
        self.store.clear_operational_error("original-condition")
        self.assertEqual(self.store.emit_alerts(), [])
        self.assertEqual(len(self.store.rows("SELECT * FROM alerts")), 15)
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE state!='settled'"))

    def test_R02_collected_execution_releases_slot_but_not_root_custody_or_source(self):
        source = event(self.config, "first")
        queued(self.store, source)
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        plan = Path(self.temp.name)/"owned-fake-server.json"
        plan.write_text(encode({"result": self.work_answer()}))
        adapter = AppServer(self.config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
        outcome = asyncio.run(adapter.run(self.store, attempt, "synthetic integrator", self.config["tasks"]["work-integrator"], RESULT_SCHEMA))
        self.assertEqual(outcome["exit"], 0)  # Actual owned subprocess.wait, not a stored label.
        self.store.collect(attempt, outcome)
        self.store.finish_job(job["id"], job["token"])
        response = self.store.event(self.store.job(job["id"])["response"])
        queued(self.store, response)
        self.runtime.pump_deliveries()
        root = self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Root'", (job["id"],))
        self.store.delivery_observed(root["id"], self.stage("Work", root["id"], self.root, "picked-up"))
        report = self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Work'", (job["id"],))
        for stage in ("picked-up", "processed", "settled"):
            self.store.delivery_observed(report["id"], self.stage("Work", report["id"], self.config["roles"]["Work"]["owner"], stage))
        queued(self.store, event(self.config, "next-independent"))
        next_job = self.store.reserve()
        self.assertIsNotNone(next_job)
        self.assertEqual(self.store.job(job["id"])["state"], "awaiting-delivery")
        self.assertTrue(self.store.execution_complete(self.store.job(job["id"])))
        self.assertEqual(self.store.one("SELECT state FROM outboxes WHERE id=?", (root["id"],))["state"], "picked-up")
        self.assertIsNone(self.store.one("SELECT processed_at FROM events WHERE id=?", (source["id"],))["processed_at"])
        self.assertTrue(self.store.dependency_hold(source["id"]))
        with patch.object(self.store, "clock", return_value=self.store.clock()+172801):
            sweep(self.store)
        self.assertEqual(self.store.recover_source(source["id"]), source)
        self.assertIsNotNone(self.store.one("SELECT * FROM queue WHERE event=?", (source["id"],)))
        status = {j["id"]: j for j in self.store.status()["slots"]}
        self.assertFalse(status[job["id"]]["execution_slot_held"])
        self.assertTrue(status[next_job["id"]]["execution_slot_held"])
        competitor = Store(self.config)
        self.addCleanup(competitor.close)
        self.assertIsNone(competitor.reserve())  # The new active slot still excludes other controllers.
        for stage in ("processed", "settled"):
            self.store.delivery_observed(root["id"], self.stage("Work", root["id"], self.root, stage))
        self.runtime.reconcile_completed()
        self.assertEqual(self.store.job(job["id"])["state"], "closed")

    def test_R02_unknown_lifecycle_effects_and_scoped_holds_keep_execution_slot(self):
        queued(self.store, event(self.config, "held"))
        job = self.store.reserve()
        ended_job(self.store, job, self.work_answer())
        original = self.store.job(job["id"])
        self.assertTrue(self.store.execution_complete(original))
        for field, value in [("ended", None), ("collected", None), ("exit", 7), ("capture", "incomplete"), ("semantic", "PARTIAL")]:
            with self.subTest(field=field):
                old = self.store.attempt(original["active_attempt"])[field]
                self.store.db.execute(f"UPDATE attempts SET {field}=? WHERE id=?", (value, original["active_attempt"]))
                self.assertFalse(self.store.execution_complete(self.store.job(job["id"])))
                self.store.db.execute(f"UPDATE attempts SET {field}=? WHERE id=?", (old, original["active_attempt"]))
        for field, value in [("effects", "unknown"), ("hold_reason", "actual scoped resource hold")]:
            self.store.db.execute(f"UPDATE jobs SET {field}=? WHERE id=?", (value, job["id"]))
            self.assertFalse(self.store.execution_complete(self.store.job(job["id"])))
            self.store.db.execute(f"UPDATE jobs SET {field}=? WHERE id=?", (original[field], job["id"]))

    def test_R02_legacy_and_same_package_fences_do_not_freeze_an_unrelated_package(self):
        owner = self.config["roles"]["Branch"]["owner"]
        for package in ("one", "other"):
            self.store.admit(package, owner, {"resource_evidence": "synthetic exact package admission"})
        queued(self.store, event(self.config, "first-scope", "Branch", "branch-integrator", "one"))
        first = self.store.reserve()
        ended_job(self.store, first, self.work_answer())
        queued(self.store, event(self.config, "same-scope", "Branch", "branch-integrator", "one"))
        self.assertIsNone(self.store.reserve())
        queued(self.store, event(self.config, "unrelated-scope", "Branch", "branch-integrator", "other"))
        self.store.db.execute("UPDATE enrollments SET legacy_hold='actual synthetic integration owner still active' WHERE role='Branch'")
        self.assertIsNone(self.store.reserve())
        self.store.reconcile_legacy("Branch", owner, {"collector": owner, "evidence": ["exact synthetic legacy collection"], "remaining_holds": []})
        next_job = self.store.reserve()
        self.assertEqual(next_job["package"], "other")
        self.assertEqual(self.store.job(first["id"])["state"], "awaiting-delivery")

    def rejected_review(self):
        queued(self.store, event(self.config, "selected-review", "Reviews", "reviews-proposer"))
        job = self.store.reserve()
        self.store.delegate_owner_job(job["id"])
        self.runtime.pump_deliveries()
        outbox = self.store.one("SELECT * FROM outboxes WHERE job=?", (job["id"],))
        owner = self.config["roles"]["Reviews"]["owner"]
        for stage in ("picked-up", "processed"):
            self.store.delivery_observed(outbox["id"], self.stage("Reviews", outbox["id"], owner, stage))
        returned = {"result": result(summary="Unique complete collected finding; category typo only"),
                    "actual_originals": [{"collector": owner, "actual_end": 0, "reference": "synthetic original report; never replay"}],
                    "method_pin": "e67a1de4", "coverage_frontier": {"full": ["synthetic selected material"], "unread": ["explicit real qualification"]},
                    "effects": {"evidence": ["actual synthetic owner reconciliation"], "unknown_effects": []}}
        original = self.stage("Reviews", outbox["id"], owner, "settled", **returned)
        self.runtime.pump_deliveries()
        self.assertEqual(self.store.job(job["id"])["state"], "awaiting-owner")
        self.assertIsNone(self.store.one("SELECT * FROM owner_results"))
        self.assertEqual(self.store.one("SELECT state FROM outboxes WHERE id=?", (outbox["id"],))["state"], "processed")
        return job, outbox, owner, original

    def correction(self, current, category="consolidated", reason="Correct routing category; no Source/reviewer replay"):
        settlement = copy.deepcopy(current["settlement"])
        settlement["result"]["category"] = category
        return {"supersedes": current["settlement_version"], "reason": reason, "settlement": settlement}

    def test_R03_actual_owner_corrects_rejected_route_once_without_replaying_review(self):
        job, outbox, owner, original = self.rejected_review()
        request = self.correction(original)
        config_path, receipt_path = Path(self.temp.name)/"config.json", Path(self.temp.name)/"correction.json"
        config_path.write_text(encode(self.config))
        receipt_path.write_text(encode(request))
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.root}):
            self.assertRaises(Refusal, self.boards["Reviews"].correct_owner_return, outbox["id"], request)
        altered = copy.deepcopy(request)
        altered["settlement"]["actual_originals"][0]["collector"] = self.root
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            self.assertRaises(Refusal, self.boards["Reviews"].correct_owner_return, outbox["id"], altered)
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--config", str(config_path), "delivery-correct", "Reviews", outbox["id"], "--receipt", str(receipt_path)])
            self.assertEqual(code, 0)
            repeated = self.boards["Reviews"].correct_owner_return(outbox["id"], request)
        self.assertEqual(len(repeated["owner_corrections"]), 1)
        self.assertEqual(repeated["original_settlement"], original["settlement"])
        self.runtime.pump_deliveries()
        self.assertEqual(self.store.job(job["id"])["state"], "closed")
        response = self.store.event(self.store.job(job["id"])["response"])
        self.assertEqual(response["owner_return_history"]["original"]["result"]["category"], "complete")
        self.assertEqual(response["body"]["findings"], original["settlement"]["result"]["findings"])
        self.assertEqual(response["source_originals"], original["settlement"]["actual_originals"])
        self.assertEqual(response["method_pin"], "e67a1de4")
        self.assertEqual(self.store.rows("SELECT * FROM attempts WHERE kind='task'"), [])
        queued(self.store, response)
        self.assertEqual(self.store.reserve()["task"], "reviews-integrator")
        self.assertEqual(self.config["tasks"]["reviews-proposer"]["binding"]["model"], "gpt-xhigh")
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            self.assertRaises(Refusal, self.boards["Reviews"].correct_owner_return, outbox["id"], self.correction(repeated, reason="already collected"))
        self.assertEqual(len(self.store.rows("SELECT * FROM owner_results")), 1)

    def test_R03_corrections_are_version_fenced_bounded_and_keep_every_rejected_return(self):
        job, outbox, owner, current = self.rejected_review()
        first = self.correction(current, category="complete", reason="First actual owner correction remains invalid")
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            for revision in range(4):
                request = self.correction(current, category="complete", reason="Actual owner correction "+str(revision))
                current = self.boards["Reviews"].correct_owner_return(outbox["id"], request)
                self.runtime.pump_deliveries()
            self.assertRaises(Refusal, self.boards["Reviews"].correct_owner_return, outbox["id"], first)
            self.assertRaises(Refusal, self.boards["Reviews"].correct_owner_return, outbox["id"], self.correction(current))
        self.assertEqual(len(current["owner_corrections"]), 4)
        self.assertEqual(self.store.job(job["id"])["state"], "awaiting-owner")
        self.assertTrue(self.store.dependency_hold(json.loads(job["members"])[0]["event"]))
        self.assertEqual(self.store.rows("SELECT * FROM attempts WHERE kind='task'"), [])

    def test_R03_local_collection_survives_board_receipt_commit_failure_without_replay(self):
        job, outbox, owner, original = self.rejected_review()
        board = self.boards["Reviews"]
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            corrected = board.correct_owner_return(outbox["id"], self.correction(original))
        actual_write = board.store.write
        @contextlib.contextmanager
        def fail_before_board_commit(conn):
            with actual_write(conn):
                yield
                raise OSError("synthetic board commit failure after durable local collection")
        with patch.object(board.store, "write", fail_before_board_commit):
            self.runtime.pump_deliveries()
        self.assertEqual(self.store.job(job["id"])["state"], "closed")
        response = self.store.job(job["id"])["response"]
        self.assertIsNotNone(self.store.one("SELECT error FROM outboxes WHERE id=?", (outbox["id"],))["error"])
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            self.assertRaises(Refusal, board.correct_owner_return, outbox["id"], self.correction(corrected, reason="late duplicate correction"))
        self.runtime.pump_deliveries()
        self.assertIsNone(self.store.one("SELECT error FROM outboxes WHERE id=?", (outbox["id"],))["error"])
        self.assertEqual(self.store.job(job["id"])["response"], response)
        self.assertEqual(len(self.store.rows("SELECT * FROM owner_results")), 1)
        self.assertEqual(self.store.rows("SELECT * FROM attempts WHERE kind='task'"), [])
