"""Focused O01–O10/Q01–Q10 consequences, fresh synthetic fixtures only.

Oracles: collected assessment/findings.json, qualification/RESULT.json (including
the actual provider400) and CONSEQUENCE-DECISION.json. No observer repro script
is replayed, and no existing fixture/source/evidence is changed.
"""

import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, result, collect, queued, ended_job
from coordinator_runtime.appserver import AppServer, preflight, safe_error
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.cleanup import register_artifact, conserve, sweep
from coordinator_runtime.cli import stop_budget
from coordinator_runtime.contracts import Refusal, digest, encode, ident, scoped_task, validate_config
from coordinator_runtime.dispatcher import Dispatcher, RESULT_SCHEMA
from coordinator_runtime.store import Store

PROVIDER400 = "Invalid schema for response_format 'codex_output_schema': 'schema.properties.artifacts.items.properties' is required for object schemas."


class ProcessCorrections(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="correction1-process-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)

    def adapter(self, plan):
        path = Path(self.temp.name)/f"plan-{ident()}.json"
        path.write_text(encode(plan))
        return AppServer(self.config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(path)])

    def task(self):
        queued(self.store, event(self.config, ident()))
        job = self.store.reserve()
        return job, self.store.start_job(job["id"], job["token"])

    async def test_O01_valid_final_survives_unsubscribe_failure_and_is_durable(self):
        job, attempt = self.task()
        expected = result(summary="Unique consequential finding must survive unsubscribe")
        outcome = await self.adapter({"result": expected, "unsubscribe_error": True}).run(
            self.store, attempt, "fixture task", self.config["tasks"]["work-integrator"], RESULT_SCHEMA)
        self.assertEqual(outcome["result"], expected)
        self.assertIsNone(outcome["error"])
        self.assertEqual(outcome["exit"], 0)
        self.assertEqual(outcome["detail"]["unsubscribe"], "failed-or-unknown")
        self.assertNotEqual(outcome["cleanup"], "done")
        self.store.collect(attempt, outcome)
        self.assertEqual(json.loads(self.store.one("SELECT result FROM results WHERE attempt=?", (attempt,))["result"]), expected)
        self.assertEqual(self.store.attempt(attempt)["semantic"], "DONE")

    async def test_Q02_closed_provider_wire_preserves_rich_actual_task_result(self):
        self.assertEqual(RESULT_SCHEMA["required"], ["payload_json"])
        self.assertEqual(RESULT_SCHEMA["properties"], {"payload_json": {"type": "string"}})
        self.assertFalse(RESULT_SCHEMA["additionalProperties"])
        job, attempt = self.task()
        expected = result()
        expected["findings"] = [{"condition": {"stage": 7}, "confidence": "bounded", "every_occurrence": [1, 2], "meaning": "retain arbitrary source detail"}]
        outcome = await self.adapter({"result": expected}).run(self.store, attempt, "fixture", self.config["tasks"]["work-integrator"], RESULT_SCHEMA)
        self.assertEqual(outcome["result"], expected)
        self.assertEqual(outcome["detail"]["session_reclamation"], "not-qualified")
        self.assertEqual(outcome["cleanup"], "owned-ephemeral-lifecycle-observed")
        cause = safe_error({"message": PROVIDER400, "code": "invalid_json_schema", "http_status": 400, "param": "text.format.schema"})
        self.assertEqual(cause["http_status"], 400)
        self.assertEqual(cause["schema_path"], "schema.properties.artifacts.items.properties")

    async def test_O01_teardown_capture_failure_keeps_final_and_actual_collected_exit(self):
        job, attempt = self.task()
        adapter = self.adapter({"result": result()})
        actual_teardown = adapter.teardown
        async def failed_after_collection(child, peer, outcome):
            await actual_teardown(child, peer, outcome)
            raise OSError("synthetic post-collection teardown failure")
        adapter.teardown = failed_after_collection
        outcome = await adapter.run(self.store, attempt, "fixture", self.config["tasks"]["work-integrator"], RESULT_SCHEMA)
        self.assertEqual(outcome["result"], result())
        self.assertEqual(outcome["exit"], 0)
        self.assertEqual(outcome["detail"]["teardown"], "actual-owned-process-exit-collected")
        self.assertEqual(outcome["detail"]["teardown_failure"], "OSError")
        self.assertEqual(outcome["cleanup"], "owned-teardown-needs-reconciliation")
        self.store.collect(attempt, outcome)
        self.assertEqual(self.store.attempt(attempt)["semantic"], "DONE")

    async def test_O06_Q05_proved_no_start_recovers_without_a_process_END(self):
        self.store.ingest(event(self.config))
        original, message = self.store.claim_classification()
        adapter = AppServer(self.config, [str(Path(self.temp.name)/"deliberately-nonexistent-executable")])
        outcome = await adapter.run(self.store, original, "fixture", {"cwd": self.temp.name, "sandbox": "read-only"})
        self.assertTrue(outcome["detail"]["known_not_started"])
        self.store.collect(original, outcome)
        self.store.classification_failed(original, outcome["error"])
        row = self.store.attempt(original)
        self.assertEqual(row["state"], "not-started")
        self.assertIsNone(row["begin"])
        self.assertIsNone(row["ended"])
        self.assertIsNone(row["exit"])
        self.assertIsNotNone(row["collected"])
        runtime = Dispatcher(self.store, models=self.adapter({"result": {"event_id": message["id"], "task": "work-integrator", "package": None, "reason": "bounded no-start diagnosis"}}), boards={})
        runtime.schedule_classification_recovery()
        await asyncio.gather(*runtime.active)
        self.assertEqual(len(self.store.rows("SELECT * FROM queue")), 1)
        self.assertIsNone(self.store.claim_classification_recovery())

    async def test_Q01_feature_omission_is_not_failure_or_capability_proof(self):
        async def metadata(argv, env, limit=1048576):
            if "--version" in argv:
                return "codex-cli fixture"
            if "features" in argv:
                return "" if "features.multi_agent=false" in argv else "multi_agent stable true\nmulti_agent_v2 stable true\n"
            return encode([{"name": "openaiDeveloperDocs", "enabled": False}])
        with patch("coordinator_runtime.appserver.metadata", metadata):
            flags, readback = await preflight("fake", ".codex3", "codex-cli fixture")
        self.assertIn("features.multi_agent=false", flags)
        self.assertEqual(readback["feature_names_omitted"], ["multi_agent", "multi_agent_v2"])
        self.assertEqual(readback["delegation_capability"], "not-established")

    async def test_Q03_Q04_failed_provider_turn_preserves_cause_and_systemError_guard(self):
        job, attempt = self.task()
        outcome = await self.adapter({"turn_error": {"message": PROVIDER400, "code": "invalid_json_schema", "http_status": 400,
                                                 "param": "text.format.schema"}, "read_status": "systemError"}).run(
            self.store, attempt, "fixture", self.config["tasks"]["work-integrator"], RESULT_SCHEMA)
        self.assertIn("idle", outcome["error"])
        self.assertEqual(outcome["exit"], 0)
        self.assertEqual(outcome["detail"]["prior_turn_failure"]["schema_path"], "schema.properties.artifacts.items.properties")
        self.assertEqual(outcome["detail"]["prior_turn_failure"]["http_status"], 400)
        self.assertEqual(outcome["detail"]["unsubscribe"], "unsubscribed")
        self.assertNotEqual(outcome["cleanup"], "done")

    async def test_O02_no_new_classifier_diagnosis_or_replacement_after_revocation(self):
        self.store.ingest(event(self.config))
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Work'")
        self.assertIsNone(self.store.claim_classification())
        self.store.db.execute("UPDATE enrollments SET intake=1 WHERE role='Work'")
        a, _ = self.store.claim_classification()
        collect(self.store, a, {}, error="invalid prior classifier")
        self.store.classification_failed(a, "invalid")
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Work'")
        self.assertIsNone(self.store.claim_classification_recovery())
        self.store.db.execute("UPDATE enrollments SET intake=1 WHERE role='Work'")
        self.store.ingest(event(self.config, "job"))
        queued(self.store, self.store.event(event(self.config, "job")["id"]))
        job = self.store.reserve()
        old = self.store.start_job(job["id"], job["token"])
        collect(self.store, old, result("PARTIAL"), code=1)
        self.store.finish_job(job["id"], job["token"])
        self.store.claim_recovery(job["id"])
        diagnosis = self.store.diagnosis_attempt(job["id"])
        collect(self.store, diagnosis, {"profile": ".codex3", "remaining": "bounded", "rationale": "explicit choice"})
        self.store.db.execute("UPDATE jobs SET effects='none' WHERE id=?", (job["id"],))
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Work'")
        self.assertRaises(Refusal, self.store.handoff, job["id"], diagnosis)
        self.assertEqual(self.store.job(job["id"])["active_attempt"], old)


class ConservationCorrections(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="correction1-custody-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.now = 100000.0
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)

    def test_O03_later_downstream_hold_preserves_upstream_report(self):
        source = event(self.config, role="Reviews")
        queued(self.store, source)
        job = self.store.reserve()
        a = ended_job(self.store, job, result(category="consolidated"))
        response_id = self.store.job(job["id"])["response"]
        queued(self.store, self.store.event(response_id))
        ended_job(self.store, self.store.reserve())
        root = self.store.home/"artifacts"/a
        root.mkdir(mode=0o700, parents=True)
        report = root/"needed-report.md"
        report.write_text("Unique report required by downstream recovery")
        register_artifact(self.store, a, report)
        conserve(self.store, report, self.config["roles"]["Reviews"]["owner"], {"evidence": "exact actual consumer conservation in fixture"})
        self.store.set_hold(response_id, "recovery needs original report")
        self.now += 86401
        sweep(self.store)
        self.assertTrue(report.exists())
        self.store.set_hold(response_id, None)
        sweep(self.store)
        self.assertTrue(report.exists())  # Actual later processing completion restarts the dependent minimum.
        self.now += 86400
        sweep(self.store)
        self.assertFalse(report.exists())

    def test_O08_unique_input_custody_survives_queue_retirement_without_duplication(self):
        source = event(self.config)
        source["body"] = {"unique_condition": "not present in any result", "attribution": "original producer"}
        queued(self.store, source)
        ended_job(self.store, self.store.reserve())
        self.now += 86400
        sweep(self.store)
        self.assertEqual(self.store.recover_source(source["id"]), source)
        self.assertEqual(self.store.one("SELECT basis FROM source_custody")["basis"], "local")
        self.assertEqual(self.store.rows("SELECT * FROM queue"), [])

    def test_O07_one_owner_per_admitted_QA_package_including_pending_cleanup(self):
        self.store.admit("package", self.config["roles"]["Branch"]["owner"], {"admission": "one"})
        queued(self.store, event(self.config, "first", "QA", "qa-execution", "package"))
        queued(self.store, event(self.config, "followup", "QA", "qa-execution", "package"))
        first = self.store.reserve()
        self.assertIsNone(self.store.reserve())
        ended_job(self.store, first, result(category="consolidated"))
        self.assertIsNone(self.store.reserve())
        self.assertEqual(len(self.store.rows("SELECT * FROM qa_package_owners")), 1)
        self.assertEqual(len(self.store.rows("SELECT * FROM queue WHERE state='queued'")), 1)

    def test_O10_service_budget_covers_task_and_continuation(self):
        self.assertGreater(stop_budget(self.config), 2*max(self.config["deadlines"]["task"], self.config["deadlines"]["classify"])+self.config["deadlines"]["interrupt"])

    def test_O04_admitted_real_task_scope_cannot_expand_to_foreign_roots(self):
        task = {**self.config["tasks"]["branch-integrator"], "require_package_scope": True,
                "scope_roots": [self.temp.name], "network": True}
        scope = {"cwd": self.temp.name, "write_roots": [self.temp.name], "read_roots": [], "network": True,
                 "procedure": "exact actual Branch organization procedure", "resource_evidence": ["existing owner"]}
        admission = {"receipt": encode({"task_scopes": {"branch-integrator": scope}})}
        self.assertEqual(scoped_task("branch-integrator", task, admission)["admitted_scope"], scope)
        scope["write_roots"] = ["/home/nes/.codex3"]
        self.assertRaises(Refusal, scoped_task, "branch-integrator", task, {"receipt": encode({"task_scopes": {"branch-integrator": scope}})})
        self.assertRaises(Refusal, scoped_task, "branch-integrator", task, None)

    def test_O04_selected_review_owner_return_keeps_binding_originals_and_coverage(self):
        # New immutable fixture config; no live Reviews reply/adoption inferred.
        path = Path(self.temp.name)/"selected-review"
        path.mkdir()
        config = config_at(path)
        config["tasks"]["reviews-proposer"].update(execution="owner", binding={"model": "gpt-xhigh", "provider": "opaque", "effort": "opaque"})
        config["tasks"]["reviews-proposer"]["responses"]["consolidated"] = ["reviews-integrator"]
        validate_config(config)
        with_store = enrolled(config)
        self.addCleanup(with_store.close)
        queued(with_store, event(config, role="Reviews", task="reviews-proposer"))
        job = with_store.reserve()
        with_store.delegate_owner_job(job["id"])
        self.assertIsNone(with_store.job(job["id"])["active_attempt"])
        outbox = with_store.one("SELECT * FROM outboxes")
        self.assertEqual(json.loads(outbox["payload"])["selected_binding"]["model"], "gpt-xhigh")
        receipt = {"id": outbox["id"], "recipient": config["roles"]["Reviews"]["owner"], "state": "settled", "processed_at": self.now,
                   "settlement": {"result": result(category="consolidated"), "actual_originals": [{"collector": config["roles"]["Reviews"]["owner"],
                    "actual_end": 0, "reference": "synthetic true original receipt"}], "method_pin": "e67a1de4", "coverage_frontier": {"full": ["architecture"], "unread": ["other required work"]},
                    "effects": {"evidence": ["collected fixture only"], "unknown_effects": []}}}
        with_store.delivery_observed(outbox["id"], receipt)
        response = with_store.event(with_store.job(job["id"])["response"])
        self.assertEqual(response["source_owner"], config["roles"]["Reviews"]["owner"])
        self.assertEqual(response["coverage_frontier"]["unread"], ["other required work"])
        self.assertIsNone(response["source_attempt"])
        queued(with_store, response)
        self.assertEqual(with_store.reserve()["task"], "reviews-integrator")
        queued(with_store, event(config, name="blocked-review", role="Reviews", task="reviews-proposer"))
        blocked = with_store.reserve()
        with_store.delegate_owner_job(blocked["id"])
        outgoing = with_store.one("SELECT * FROM outboxes WHERE job=?", (blocked["id"],))
        not_started = {**receipt, "id": outgoing["id"], "settlement": {
            **receipt["settlement"], "result": result("PARTIAL", category="blocker", summary="Actual procedure unavailable; Work retains choice"),
            "actual_originals": [], "no_start_evidence": ["actual fixture owner could not obtain compatible procedure"],
            "coverage_frontier": {"unread": ["all selected work"], "next_owner": "Work"}}}
        with_store.delivery_observed(outgoing["id"], not_started)
        frontier = with_store.event(with_store.job(blocked["id"])["response"])
        self.assertEqual(frontier["role"], "Work")
        self.assertEqual(frontier["source_originals"], [])
        self.assertTrue(frontier["source_no_start_evidence"])
        self.assertEqual(frontier["body"]["semantic"], "PARTIAL")


class DeliveryCorrections(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="correction1-board-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.owner = self.config["roles"]["Work"]["owner"]
        self.config["roles"]["Branch"]["board_id"] = self.config["roles"]["Work"]["board_id"]
        self.root = ident()
        self.config["delivery"] = {"recipients": {
            "Work": {"session": self.owner, "board_role": "work", "profile": ".codex"},
            "Root": {"session": self.root, "board_role": "root", "profile": ".codex"},
            "Branch": {"session": self.config["roles"]["Branch"]["owner"], "board_role": "branch", "profile": ".codex5"}}, "alert_role": "Work", "alert_recipient": "Work"}
        self.config["tasks"]["work-integrator"].update({"delivery_required": True, "allowed_handoffs": ["Root"]})
        library = self.config["board_library"]
        substrate, catalog = module_at(library, "board_store"), module_at(library, "catalog")
        self.substrate = substrate
        home = Path(self.config["board_home"])
        with catalog.catalog(home) as cat:
            entry = catalog.create(cat, home, "correction", "Synthetic correction", board_id=self.config["roles"]["Work"]["board_id"], temporary_test=True)
        self.path = Path(entry["db_path"])
        with substrate.database(str(self.path)) as conn:
            substrate.bind_board(conn, entry["board_id"], initialize=True)
            for actor, role in [(self.owner, "work"), (self.root, "root")]:
                args = substrate.parser().parse_args(["register", "--session", actor, "--role", role, "--route", "managed", "--profile", ".codex"])
                with patch.dict(os.environ, {"CODEX_SESSION_ID": actor}):
                    substrate.register(conn, args)
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.board = Board(self.config, "Work")
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.owner}):
            grant = self.board.grant(self.store, "Synthetic CF01 owner authority", delivery=True)
        self.store.enroll("Work", grant)
        self.store.reconcile_legacy("Work", self.owner, {"collector": self.owner, "evidence": ["fixture only"], "remaining_holds": []})
        self.runtime = Dispatcher(self.store, models=object(), boards={"Work": self.board})

    def stage(self, delivery, stage, actor=None, **extra):
        with patch.dict(os.environ, {"CODEX_SESSION_ID": actor or self.root}):
            receipt = self.board.delivery_stage(delivery, stage, {"evidence": ["actual synthetic recipient "+stage], **extra})
        self.store.delivery_observed(delivery, receipt)
        return receipt

    def test_O05_actual_addressed_work_and_owned_pickup_processing_settlement(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        answer = result()
        answer.update({"handoffs": [{"recipient": "Root", "kind": "work", "text": "Accepted bounded correction; commit AND push owned code", "ref": "fixture-scope", "required": "settled"}], "no_handoff_reason": ""})
        ended_job(self.store, job, answer)
        self.assertEqual(self.store.job(job["id"])["state"], "awaiting-delivery")
        self.runtime.pump_deliveries()
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 0)
        response = self.store.event(self.store.job(job["id"])["response"])
        queued(self.store, response)  # Fresh classifier commits the terminal outgoing response before any send.
        self.runtime.pump_deliveries()
        outbox = self.store.one("SELECT * FROM outboxes WHERE recipient='Root'")
        first = self.board.delivery_status(outbox["id"])
        self.runtime.pump_deliveries()
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 2)
            author = conn.execute("SELECT author,recipient FROM posts WHERE recipient=?", (self.root,)).fetchone()
            self.assertEqual(tuple(author), (self.config["actor"], self.root))
            self.assertNotEqual(author[0], self.owner)
        self.assertRaises(Refusal, self.stage, outbox["id"], "settled")
        self.stage(outbox["id"], "picked-up")
        self.assertIsNone(self.store.one("SELECT processed_at FROM events")["processed_at"])
        self.stage(outbox["id"], "processed")
        self.stage(outbox["id"], "settled")
        self.store.finish_job(job["id"], job["token"])
        self.assertEqual(self.store.job(job["id"])["state"], "awaiting-delivery")
        ownerbox = self.store.one("SELECT * FROM outboxes WHERE recipient='Work'")
        for stage in ("picked-up", "processed", "settled"):
            self.stage(ownerbox["id"], stage, actor=self.owner)
        self.store.finish_job(job["id"], job["token"])
        self.assertEqual(self.store.job(job["id"])["state"], "closed")
        self.assertEqual(self.board.delivery_status(outbox["id"])["post"], first["post"])
        self.assertNotIn("Root", self.config["roles"])

    def test_O09_errors_recur_durably_and_really_post_to_the_consumer(self):
        self.runtime.runtime_errors["intake fixture"] = "catalog identity changed: safe causal detail"
        emitted = []
        asyncio.run(self.runtime.alerts(emitted.append))
        self.assertTrue(self.store.status()["operational_errors"])
        alerts = self.store.rows("SELECT * FROM alerts")
        self.assertTrue(alerts)
        with self.substrate.database(str(self.path)) as conn:
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM posts WHERE recipient=?", (self.owner,)).fetchone()[0], 0)
        old_ids = {a["id"] for a in alerts}
        self.runtime.last_alert = 0
        asyncio.run(self.runtime.alerts(emitted.append))
        new_ids = {a["id"] for a in self.store.rows("SELECT * FROM alerts")}
        self.assertGreater(len(new_ids-old_ids), 0)
        self.assertTrue(any("catalog identity" in a["payload"] for a in self.store.rows("SELECT * FROM alerts")))

    def test_O02_revoked_actual_board_grant_fences_after_preflight(self):
        self.store.ingest(event(self.config))
        attempt, _ = self.store.claim_classification()
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.owner}):
            self.board.revoke(self.store.enrollment("Work")["grant_id"])
        self.assertRaises(Refusal, self.store.authorize_launch, attempt)

    def test_CF01_queue_ACK_cannot_settle_submission_processing(self):
        with self.store.tx():
            delivery = self.store._outbox("Work", "Root", "work", {"text": "exact synthetic responsibility"})
        self.runtime.pump_deliveries()
        receipt = self.board.delivery_status(delivery)
        with self.substrate.database(str(self.path)) as conn:
            conn.execute("UPDATE notification_outbox SET route='queue',delivery_state='acknowledged' WHERE notification_id=?", (receipt["notice"],))
        self.stage(delivery, "picked-up")
        self.assertRaises(Refusal, self.stage, delivery, "processed")
        with self.substrate.database(str(self.path)) as conn:
            conn.execute("UPDATE notification_outbox SET queue_message_id='fixture-original-queue-id' WHERE notification_id=?", (receipt["notice"],))
        proof = {"queue_message_id": "fixture-original-queue-id", "state": "processed", "evidence": ["exact fixture queue consumer receipt"]}
        self.stage(delivery, "processed", transport=proof)
        self.stage(delivery, "settled", transport=proof)
        self.assertEqual(self.store.one("SELECT state FROM outboxes WHERE id=?", (delivery,))["state"], "settled")

    def test_CF01_complete_cannot_silently_omit_necessary_delivery(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        collect(self.store, attempt, result())
        self.runtime.try_finish(job["id"])
        self.assertEqual(self.store.job(job["id"])["state"], "held")
        question = self.store.one("SELECT * FROM outboxes")
        self.assertEqual(question["recipient"], "Work")
        self.assertEqual(question["state"], "classification-pending")
        self.assertIn("handoff", json.loads(question["payload"])["reason"])

    def test_CF02_alert_retirement_obeys_real_delivery_and_consumer_holds(self):
        now = self.store.clock()
        self.store.record_operational_error("held-fixture", {"error": "consequential fixture"})
        occurrence = self.store.emit_alerts()[0]
        self.store.process_alert(occurrence["id"], self.owner, {"evidence": "consumer kept meaning"})
        with patch.object(self.store, "clock", return_value=now+172801):
            sweep(self.store)
        self.assertIsNotNone(self.store.one("SELECT id FROM alerts WHERE id=?", (occurrence["id"],)))
        self.runtime.pump_deliveries()
        delivery = self.store.one("SELECT id FROM outboxes WHERE alert=?", (occurrence["id"],))["id"]
        for stage in ("picked-up", "processed", "settled"):
            receipt = self.stage(delivery, stage, actor=self.owner)
        self.assertEqual(self.store.one("SELECT processed_at FROM alerts WHERE id=?", (occurrence["id"],))["processed_at"], receipt["processed_at"])
        with patch.object(self.store, "clock", return_value=receipt["processed_at"]+86401):
            sweep(self.store)
        self.assertIsNone(self.store.one("SELECT id FROM alerts WHERE id=?", (occurrence["id"],)))

    def test_CF01_committed_send_lost_reply_then_revocation_collects_without_replay(self):
        with self.store.tx():
            delivery = self.store._outbox("Work", "Root", "work", {"text": "lost receipt fixture"})
        outbox = self.store.one("SELECT * FROM outboxes WHERE id=?", (delivery,))
        original = self.board.post_delivery(self.store, outbox)  # Crash boundary: no runtime receipt yet.
        with patch.dict(os.environ, {"CODEX_SESSION_ID": self.owner}):
            self.board.revoke(self.store.enrollment("Work")["grant_id"])
        self.runtime.pump_deliveries()
        self.assertEqual(json.loads(self.store.one("SELECT board_receipt FROM outboxes WHERE id=?", (delivery,))["board_receipt"])["post"], original["post"])
        for stage in ("picked-up", "processed", "settled"):
            self.stage(delivery, stage)
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 1)

    def test_CF01_work_handoff_reenters_selected_recipient_actual_dispatch(self):
        owner = self.config["roles"]["Branch"]["owner"]
        with self.substrate.database(str(self.path)) as conn:
            args = self.substrate.parser().parse_args(["register", "--session", owner, "--role", "branch", "--route", "managed", "--profile", ".codex5"])
            with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
                self.substrate.register(conn, args)
        receiver = Board(self.config, "Branch")
        with patch.dict(os.environ, {"CODEX_SESSION_ID": owner}):
            grant = receiver.grant(self.store, "Exact synthetic Branch role delegation", delivery=True)
        self.store.enroll("Branch", grant)
        self.store.reconcile_legacy("Branch", owner, {"collector": owner, "evidence": ["fixture current owner"], "remaining_holds": []})
        with self.store.tx():
            delivery = self.store._outbox("Work", "Branch", "work", {"text": "Organize exact admitted stack", "package": "actual-fixture-package", "source_context": "full meaning"})
        self.runtime.pump_deliveries()
        messages = receiver.scan(self.store)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["package"], "actual-fixture-package")
        self.assertEqual(messages[0]["body"]["delivery"]["source_context"], "full meaning")
        queued(self.store, messages[0], {"event_id": messages[0]["id"], "task": "branch-integrator", "package": "actual-fixture-package", "reason": "actual addressed organization work"})
        receiver.receipt(self.store, messages[0]["id"])
        self.assertEqual(self.store.reserve()["task"], "branch-integrator")
        self.assertNotEqual(self.board.delivery_status(delivery)["state"], "settled")


if __name__ == "__main__":
    unittest.main()
