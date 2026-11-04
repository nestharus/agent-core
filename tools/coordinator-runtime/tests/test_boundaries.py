"""Protection of observable boundaries beyond the A01-A14 minimal paths."""

import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, result, collect, queued, ended_job
from coordinator_runtime.appserver import AppServer, Peer, preflight
from coordinator_runtime.cleanup import conserve, eligible_event, register_artifact, retire_artifact, sweep
from coordinator_runtime.contracts import Refusal, classification, encode, ident, validate_config, parse_json
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


class Retention(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordinator-retention-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.now = 100000.0
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)

    def completed_artifact(self):
        message = event(self.config)
        queued(self.store, message)
        job = self.store.reserve()
        attempt = ended_job(self.store, job)
        root = self.store.home / "artifacts" / attempt
        root.mkdir(mode=0o700, parents=True)
        path = root / "synthetic.txt"
        path.write_text("synthetic evidence; exact consumer has conserved its meaning")
        register_artifact(self.store, attempt, path)
        conserve(self.store, path, self.config["roles"]["Work"]["owner"], {"conserved": "fixture-only"})
        return message, path

    def test_A14_successful_retirement_keeps_results_and_deduplication(self):
        message, path = self.completed_artifact()
        self.now += 86400
        receipts = sweep(self.store)
        self.assertFalse(path.exists())
        self.assertTrue(any(r["state"] == "removed" for r in receipts))
        self.assertEqual(self.store.one("SELECT state FROM events")["state"], "retired")
        self.assertGreater(len(self.store.rows("SELECT * FROM results")), 0)
        self.assertFalse(self.store.ingest(message))
        self.assertEqual(sweep(self.store), [])

    def test_A14_new_hold_after_eligibility_and_foreign_conservation(self):
        message, path = self.completed_artifact()
        self.now += 86400
        row = self.store.one("SELECT * FROM events")
        self.assertTrue(eligible_event(self.store, row))
        self.store.set_hold(message["id"], "actual consumer added hold after candidate selection")
        artifact = self.store.one("SELECT * FROM artifacts")
        receipt = retire_artifact(self.store, artifact)
        self.assertEqual(receipt["state"], "held")
        self.assertTrue(path.exists())
        self.assertRaises(Refusal, conserve, self.store, path, ident(), {"wrong_owner": True})

    def test_A14_parent_symlink_and_changed_file_are_retained(self):
        message, path = self.completed_artifact()
        self.now += 86400
        old_root = path.parent
        renamed = old_root.with_name(old_root.name+"-preserved")
        old_root.rename(renamed)
        foreign = Path(self.temp.name) / "foreign"
        foreign.mkdir()
        (foreign / path.name).write_text("foreign must survive")
        old_root.symlink_to(foreign, target_is_directory=True)
        receipt = retire_artifact(self.store, self.store.one("SELECT * FROM artifacts"))
        self.assertEqual(receipt["state"], "partial-held")
        self.assertTrue((foreign / path.name).exists())
        self.assertTrue((renamed / path.name).exists())

    def test_alert_consumer_processing_plus_24h_not_emission_is_retention(self):
        self.store.ingest(event(self.config))
        self.now += 100
        alert = self.store.emit_alerts()[0]
        self.now += 86400
        sweep(self.store)
        self.assertIsNotNone(self.store.one("SELECT * FROM alerts WHERE id=?", (alert["id"],)))
        self.store.process_alert(alert["id"], self.config["roles"]["Work"]["owner"], {"processed_by_consumer": True})
        self.now += 86399
        sweep(self.store)
        self.assertIsNotNone(self.store.one("SELECT * FROM alerts WHERE id=?", (alert["id"],)))
        self.now += 1
        sweep(self.store)
        self.assertIsNone(self.store.one("SELECT * FROM alerts WHERE id=?", (alert["id"],)))

    def test_A08_QA_qualification_requires_actual_accepted_package(self):
        package = "per-package-admission"
        owner = self.config["roles"]["Branch"]["owner"]
        self.store.admit(package, owner, {"actual_resource_owner": "fixture"})
        message = event(self.config, role="QA", task="qa-cleanup", package=package)
        queued(self.store, message)
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        collect(self.store, attempt, result(category="qualification"))
        self.assertRaises(Refusal, self.store.finish_job, job["id"], job["token"])
        self.store.admit(package, owner, {"actual_resource_owner": "fixture"}, {"accepted_bounded_result": "fixture"})
        response = self.store.finish_job(job["id"], job["token"])
        delivered = self.store.event(response)
        self.assertEqual(delivered["role"], "Branch")
        self.assertEqual(delivered["package"], package)
        self.assertEqual(delivered["body"]["findings"], result()["findings"])

    def test_A08_message_shell_and_effect_escalation_are_not_typed_routes(self):
        message = event(self.config)
        self.assertRaises(Refusal, classification,
            {"event_id": message["id"], "task": "work-integrator", "package": None,
             "reason": "chosen", "command": "touch arbitrary"}, message, self.config)
        config = copy.deepcopy(self.config)
        config["tasks"]["work-integrator"]["effect_authority"]["operations"] = ["arbitrary-shell"]
        self.assertRaises(Refusal, validate_config, config)

    def test_A02_duplicate_JSON_keys_and_nonJSON_numeric_constants_are_invalid(self):
        self.assertRaises(Refusal, parse_json, '{"task":"work-integrator","task":"arbitrary-shell"}')
        self.assertRaises(Refusal, parse_json, '{"invalid":NaN}')

    def test_Work_scope_question_holds_for_actual_Decider_without_model_self_loop(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        a = self.store.start_job(job["id"], job["token"])
        collect(self.store, a, result(category="blocker"))
        runtime = Dispatcher(self.store, models=object(), boards={})
        runtime.try_finish(job["id"])
        runtime.schedule_recovery()
        held = self.store.job(job["id"])
        self.assertEqual(held["state"], "held")
        self.assertEqual(held["recovery_count"], 0)
        question = self.store.event(held["response"])
        self.assertEqual(question["kind"], "outgoing-response")
        self.assertEqual(question["allowed_tasks"], ["@delivery"])
        self.assertEqual(len(self.store.rows("SELECT * FROM events")), 2)
        self.assertEqual(self.store.one("SELECT kind FROM outboxes")["kind"], "question")

    def test_collected_closure_handoff_is_distinct_from_foreign_handle_takeover(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        a = self.store.start_job(job["id"], job["token"])
        collect(self.store, a, result())
        restarted = Store(self.config)
        self.addCleanup(restarted.close)
        runtime = Dispatcher(restarted, models=object(), boards={})
        runtime.reconcile_completed()
        closed = restarted.job(job["id"])
        self.assertEqual(closed["state"], "closed")
        handoff = json.loads(closed["collection_handoff"])
        self.assertEqual(handoff["original_collector"], self.store.controller)
        self.assertEqual(restarted.attempt(a)["controller"], self.store.controller)
        self.assertEqual(restarted.violations(), [])
        self.assertRaises(Refusal, self.store.finish_job, job["id"], job["token"])


class ProtocolAndCapacity(unittest.IsolatedAsyncioTestCase):
    async def test_A09_actual_late_final_preserves_findings_and_cannot_route_twice(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-late-final-fixture-") as temp:
            config = config_at(temp)
            store = enrolled(config)
            self.addCleanup(store.close)
            queued(store, event(config))
            job = store.reserve()
            attempt = store.start_job(job["id"], job["token"])
            late = result("PARTIAL", summary="Late original contains another actionable failure")
            plan = Path(temp)/"late.json"
            plan.write_text(encode({"result": result(), "late_result": late}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            outcome = await adapter.run(store, attempt, "fixture", config["tasks"]["work-integrator"])
            self.assertEqual(outcome["exit"], 0)
            self.assertEqual(outcome["capture"], "late-final-needs-reconciliation")
            self.assertEqual(outcome["detail"]["late_or_conflicting_returns"][0]["typed_return"], late)
            store.collect(attempt, outcome)
            store.finish_job(job["id"], job["token"])
            self.assertEqual(store.job(job["id"])["state"], "held")
            notification = store.event(store.job(job["id"])["response"])
            self.assertEqual(notification["kind"], "outgoing-response")
            self.assertEqual(notification["allowed_tasks"], ["@delivery"])
            self.assertIsNone(store.reserve())
            stored = json.loads(store.attempt(attempt)["detail"])
            self.assertEqual(stored["late_or_conflicting_returns"][0]["typed_return"]["failures"], late["failures"])

    async def test_one_fresh_Luna_low_diagnosis_recovers_collected_classifier_failure(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-classifier-recovery-fixture-") as temp:
            config = config_at(temp)
            store = enrolled(config)
            self.addCleanup(store.close)
            message = event(config)
            store.ingest(message)
            original, _ = store.claim_classification()
            collect(store, original, None, code=1, error="fixture original model capacity failure")
            store.classification_failed(original, "capacity")
            answer = {"event_id": message["id"], "task": "work-integrator", "package": None, "reason": "bounded diagnosis of original capacity error"}
            plan = Path(temp)/"diagnosis.json"
            plan.write_text(encode({"result": answer}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            runtime = Dispatcher(store, models=adapter, boards={})
            runtime.schedule_classification_recovery()
            await asyncio.gather(*runtime.active)
            self.assertEqual(runtime.runtime_errors, {})
            self.assertEqual(len(store.rows("SELECT * FROM queue")), 1)
            current = store.one("SELECT * FROM events")
            self.assertEqual(current["recovery_count"], 1)
            self.assertNotEqual(current["classifier"], original)
            diagnosed = store.attempt(current["classifier"])
            self.assertEqual(diagnosed["kind"], "diagnosis")
            self.assertEqual(diagnosed["profile"], '.codex3')
            self.assertEqual(json.loads(diagnosed['detail'])['profile_advice'], config['diagnosis']['profile'])
            self.assertEqual(json.loads(diagnosed["detail"])["prior_classifier"], original)
            self.assertEqual(json.loads(diagnosed["binding"])["effort"], "low")
            self.assertEqual(store.attempt(original)["exit"], 1)
            self.assertIsNone(store.claim_classification_recovery())

    async def test_failed_classifier_diagnosis_is_bounded_unACKed_and_conserved(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-classifier-held-fixture-") as temp:
            config = config_at(temp)
            store = enrolled(config)
            self.addCleanup(store.close)
            store.ingest(event(config))
            original, _ = store.claim_classification()
            collect(store, original, {}, error="fixture invalid original output")
            store.classification_failed(original, "invalid")
            plan = Path(temp)/"invalid-diagnosis.json"
            plan.write_text(encode({"result": {}}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            runtime = Dispatcher(store, models=adapter, boards={})
            runtime.schedule_classification_recovery()
            await asyncio.gather(*runtime.active)
            self.assertIsNone(store.claim_classification_recovery())
            self.assertEqual(len(store.rows("SELECT * FROM results")), 2)
            self.assertEqual(store.rows("SELECT * FROM queue"), [])
            self.assertEqual(store.one("SELECT ack FROM events")["ack"], "pending")

    async def test_owned_artifact_report_task_writes_and_inventories_exact_new_output(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-report-fixture-") as temp:
            config = config_at(temp)
            task = config["tasks"]["reviews-integrator"]
            task["effects"], task["sandbox"] = "owned-artifacts", "workspace-write"
            task["effect_authority"]["operations"].append("write-owned-artifacts")
            validate_config(config)
            store = enrolled(config)
            self.addCleanup(store.close)
            queued(store, event(config, role="Reviews"))
            plan = Path(temp)/"report-plan.json"
            plan.write_text(encode({"result": result(category="consolidated"), "write_file": "report.md"}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            runtime = Dispatcher(store, models=adapter, boards={})
            runtime.schedule_job()
            await asyncio.gather(*runtime.active)
            self.assertEqual(runtime.runtime_errors, {})
            job = store.one("SELECT * FROM jobs")
            self.assertEqual(job["state"], "closed")
            artifact = store.one("SELECT * FROM artifacts")
            self.assertTrue(Path(artifact["path"]).is_relative_to(store.home/"artifacts"/job["active_attempt"]))
            conservation=json.loads(artifact['conserved'])
            self.assertEqual(conservation['basis'],'exact durable artifact_blobs custody')
            source=store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(artifact['sha256'],))
            self.assertEqual(source['body'],Path(artifact['path']).read_bytes())
            response = store.event(job["response"])
            self.assertEqual(response["body"]["artifacts"][0]["path"], artifact["path"])
            self.assertEqual(response["artifact_witnesses"][0]["sha256"], artifact["sha256"])

    async def test_actual_fixture_final_capture_bound_stays_held(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-capture-fixture-") as temp:
            config = config_at(temp)
            config["limits"]["max_result_bytes"] = 32
            store = enrolled(config)
            self.addCleanup(store.close)
            # Intake can be conserved; this case reserves a classifier so a task cannot start.
            store.ingest(event(config))
            attempt, message = store.claim_classification()
            plan = Path(temp)/"oversize-plan.json"
            plan.write_text(encode({"result": {"event_id": message["id"], "task": "work-integrator", "package": None, "reason": "x"*1000}}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            outcome = await adapter.run(store, attempt, "fixture classifier", {"cwd": temp, "sandbox": "read-only"})
            self.assertEqual(outcome["exit"], 0)
            self.assertNotEqual(outcome["capture"], "complete")
            self.assertIsNotNone(outcome["error"])
            store.collect(attempt, outcome)
            self.assertRaises(Refusal, store.commit_classification, attempt)
            self.assertEqual(store.rows("SELECT * FROM queue"), [])

    async def test_effective_MCP_readback_every_account_no_false_delegation_claim(self):
        calls = []
        async def fake_metadata(argv, env, limit=1048576):
            calls.append((argv, env["CODEX_HOME"]))
            if "--version" in argv:
                return "codex-cli fixture"
            if "features" in argv:
                disabled = "features.multi_agent=false" in argv
                return f"multi_agent stable {'false' if disabled else 'true'}\n"
            disabled = "mcp_servers.private_server.enabled=false" in argv
            return encode([{"name": "private_server", "enabled": not disabled},
                           {"name": "openaiDeveloperDocs", "enabled": not disabled}])
        with patch("coordinator_runtime.appserver.metadata", fake_metadata):
            for profile in (".codex", ".codex2", ".codex3", ".codex4", ".codex5"):
                flags, receipt = await preflight("fake-codex", profile, "codex-cli fixture")
                self.assertIn("mcp_servers.private_server.enabled=false", flags)
                self.assertEqual(receipt["mcp"], "all-effective-disabled")
                self.assertEqual(receipt["delegation_capability"], "not-established")
        self.assertEqual(len({profile for _, profile in calls}), 5)

    async def test_A07_five_real_fixture_processes_independent_sixth_waits(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-five-process-fixture-") as temp:
            config = config_at(temp)
            store = enrolled(config)
            self.addCleanup(store.close)
            for i in range(6):
                package = f"actual-fixture-package-{i}"
                store.admit(package, config["roles"]["Branch"]["owner"], {"per_package": package})
                queued(store, event(config, package, "QA", "qa-execution", package))
            plan = Path(temp)/"plan.json"
            plan.write_text(encode({"result": result(category="consolidated"), "exit_delay": 0.4}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            runtime = Dispatcher(store, models=adapter, boards={})
            for _ in range(6):
                runtime.schedule_job()
            await asyncio.sleep(0.15)
            attempts = store.rows("SELECT * FROM attempts WHERE kind='task'")
            self.assertEqual(len(attempts), 5)
            self.assertTrue(all(a["begin"] is not None and a["ended"] is None for a in attempts))
            self.assertEqual(len(store.rows("SELECT * FROM queue WHERE state='queued'")), 1)
            await asyncio.gather(*runtime.active)
            self.assertEqual(runtime.runtime_errors, {})
            runtime.schedule_job()
            self.assertEqual(len(store.rows("SELECT * FROM attempts WHERE kind='task'")), 6)
            await asyncio.gather(*runtime.active)
            self.assertEqual(len(store.rows("SELECT * FROM jobs WHERE state='closed'")), 6)
            self.assertEqual(len(store.rows("SELECT * FROM events WHERE parent IS NOT NULL")), 6)

    async def test_A09_actual_capacity_RPC_error_keeps_exit_model_and_cleanup_separate(self):
        with tempfile.TemporaryDirectory(prefix="coordinator-capacity-fixture-") as temp:
            config = config_at(temp)
            store = enrolled(config)
            self.addCleanup(store.close)
            queued(store, event(config))
            job = store.reserve()
            attempt = store.start_job(job["id"], job["token"])
            plan = Path(temp)/"capacity.json"
            plan.write_text(encode({"capacity": True}))
            adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(plan)])
            outcome = await adapter.run(store, attempt, "fixture", config["tasks"]["work-integrator"])
            self.assertTrue(outcome["detail"]["capacity_error"])
            self.assertEqual(outcome["exit"], 0)
            self.assertIsNone(outcome["result"])
            self.assertNotEqual(outcome["cleanup"], "done")
            store.collect(attempt, outcome)
            store.finish_job(job["id"], job["token"])
            self.assertEqual(store.job(job["id"])["state"], "held")
            self.assertIsNone(store.reserve())


if __name__ == "__main__":
    unittest.main()
