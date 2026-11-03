"""A01-A14 from the collected concurrency return. No real model/board service."""

import asyncio
import copy
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, result, collect, queued, ended_job
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.cleanup import register_artifact, conserve, retire_artifact, sweep
from coordinator_runtime.contracts import Backpressure, Refusal, encode, ident, validate_config
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


def race_reserve(config, barrier, pipe):
    store = Store(config)
    barrier.wait()
    job = store.reserve()
    if not job:
        pipe.send(None)
        store.close()
        return
    attempt = store.start_job(job["id"], job["token"])
    child = subprocess.Popen([sys.executable, "-c", "raise SystemExit(0)"])
    store.begin(attempt, {"fixture_pid_information_only": child.pid})
    store.session(attempt, ident())
    code = child.wait()
    store.collect(attempt, {"exit": code, "capture": "complete", "cleanup": "done", "result": result(), "error": None})
    pipe.send(job["id"])
    store.close()


def race_recovery(config, job, barrier, pipe):
    store = Store(config)
    barrier.wait()
    claimed = store.claim_recovery(job)
    pipe.send(store.controller if claimed else None)
    store.close()


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordinator-fixture-")
        self.addCleanup(self.temp.cleanup)  # Synthetic fixture data: explicitly disposable at test completion.
        self.config = config_at(self.temp.name)
        self.now = 100000.0
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)

    def test_A01_redelivery_is_one_but_distinct_unchanged_events_survive(self):
        message = event(self.config)
        self.assertTrue(self.store.ingest(message))
        self.assertFalse(self.store.ingest(message))
        second = {**message, "id": "another-occurrence"}
        self.assertTrue(self.store.ingest(second))
        self.assertEqual(len(self.store.rows("SELECT * FROM events")), 2)
        a, actual = self.store.claim_classification()
        collect(self.store, a, {"event_id": actual["id"], "task": "work-integrator", "package": None, "reason": "finding"})
        self.store.commit_classification(a)
        self.assertRaises(Refusal, self.store.commit_classification, a)
        self.assertEqual(len(self.store.rows("SELECT * FROM queue")), 1)

    def test_A02_invalid_partial_wrong_event_capacity_and_competitors_do_not_ACK(self):
        variants = [None, {}, {"event_id": "wrong", "task": "work-integrator", "package": None, "reason": "x"},
                    {"event_id": "unused", "task": "arbitrary-shell", "package": None, "reason": "x"}]
        for i, answer in enumerate(variants):
            message = event(self.config, str(i))
            self.store.ingest(message)
            a, actual = self.store.claim_classification()
            collect(self.store, a, answer)
            self.assertRaises((Refusal, TypeError), self.store.commit_classification, a)
            self.store.classification_failed(a, "invalid output")
        message = event(self.config, "capacity")
        self.store.ingest(message)
        a, _ = self.store.claim_classification()
        collect(self.store, a, None, code=1, error="capacity")
        self.assertRaises(Refusal, self.store.commit_classification, a)
        self.assertEqual(self.store.rows("SELECT * FROM queue"), [])
        self.assertFalse(any(r["ack"] == "done" for r in self.store.rows("SELECT ack FROM events")))

    def test_A04_real_controller_crash_before_commit_preserves_unACKed_input(self):
        message = event(self.config)
        self.store.ingest(message)
        config_path = Path(self.temp.name) / "config.json"
        config_path.write_text(encode(self.config))
        script = """import json,os,sys
from coordinator_runtime.store import Store
s=Store(json.load(open(sys.argv[1])))
s.db.execute('BEGIN IMMEDIATE')
s.db.execute("UPDATE events SET state='classifying'")
os._exit(73)
"""
        child = subprocess.run([sys.executable, "-c", script, str(config_path)],
                               env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])})
        self.assertEqual(child.returncode, 73)
        row = self.store.one("SELECT * FROM events")
        self.assertEqual((row["state"], row["ack"]), ("received", "pending"))

    def test_A05_frozen_batch_and_arrivals_revisions_are_next_batch(self):
        first, second = event(self.config, "first"), event(self.config, "second")
        queued(self.store, first)
        queued(self.store, second)
        job = self.store.reserve()
        frozen = json.loads(job["members"])
        self.assertEqual({m["event"] for m in frozen}, {first["id"], second["id"]})
        third = event(self.config, "third-revision")
        queued(self.store, third)
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.job(job["id"])["members"], job["members"])
        ended_job(self.store, job)
        next_job = self.store.reserve()
        self.assertEqual([m["event"] for m in json.loads(next_job["members"])], [third["id"]])

    def test_A06_two_actual_controller_processes_reserve_and_launch_once(self):
        queued(self.store, event(self.config))
        context = multiprocessing.get_context("fork")
        barrier = context.Barrier(2)
        left, right = context.Pipe(False), context.Pipe(False)
        workers = [context.Process(target=race_reserve, args=(self.config, barrier, pipe[1])) for pipe in (left, right)]
        for worker in workers:
            worker.start()
        answers = [pipe[0].recv() for pipe in (left, right)]
        for worker in workers:
            worker.join(10)
            self.assertEqual(worker.exitcode, 0)
        self.assertEqual(sum(a is not None for a in answers), 1)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")), 1)
        self.assertIsNone(self.store.reserve())  # Actual exit alone did not close its slot.
        queued(self.store, event(self.config, "independent", "Branch"))
        self.assertEqual(self.store.reserve()["role"], "Branch")

    def test_A07_five_QA_packages_sixth_pending_and_cleanup_separate(self):
        for i in range(6):
            package = f"package-{i}"
            self.store.admit(package, self.config["roles"]["Branch"]["owner"], {"actual_fixture_owner": package})
            queued(self.store, event(self.config, package, "QA", "qa-execution", package))
        jobs = [self.store.reserve() for _ in range(5)]
        self.assertEqual(len({j["package"] for j in jobs}), 5)
        self.assertTrue(all(len(json.loads(j["members"])) == 1 for j in jobs))
        self.assertIsNone(self.store.reserve())
        ended_job(self.store, jobs[0], result(category="consolidated"))
        sixth = self.store.reserve()
        self.assertIsNotNone(sixth)
        claimed = self.store.claim_classification()
        a, actual = claimed
        collect(self.store, a, {"event_id": actual["id"], "task": "qa-cleanup", "package": actual["package"], "reason": "cleanup same package"})
        self.store.commit_classification(a)
        self.store.ack_state(actual["id"], "internal")
        cleanup = self.store.reserve()
        self.assertEqual(cleanup["phase"], "cleanup")
        self.assertEqual(cleanup["package"], jobs[0]["package"])
        self.assertEqual(len(json.loads(cleanup["members"])), 1)

    def test_A08_response_provenance_reviews_to_Work_and_QA_acceptance(self):
        original = event(self.config, role="Reviews")
        queued(self.store, original)
        job = self.store.reserve()
        attempt = ended_job(self.store, job, result(category="consolidated"))
        response = self.store.event(self.store.job(job["id"])["response"])
        self.assertEqual(response["role"], "Work")
        self.assertEqual(response["author"], self.store.attempt(attempt)["session"])
        self.assertEqual(response["source_attempt"], attempt)
        self.assertEqual(response["source_members"][0]["event"], original["id"])
        self.assertEqual(response["allowed_tasks"], ["work-proposer"])
        self.assertIsNone(self.store.one("SELECT processed_at FROM events WHERE id=?", (original["id"],))["processed_at"])
        bad = copy.deepcopy(self.config)
        bad["roles"]["Root"] = bad["roles"]["Work"]
        self.assertRaises(Refusal, validate_config, bad)
        self.assertRaises(Refusal, self.store.ingest, {**original, "recipient": ident(), "id": "wrong"})

    def test_A09_capacity_or_late_original_cannot_close_replacement(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        old = self.store.start_job(job["id"], job["token"])
        collect(self.store, old, result("PARTIAL"), code=1, error="capacity error after possible effects")
        self.store.finish_job(job["id"], job["token"])
        self.assertEqual(self.store.job(job["id"])["state"], "held")
        self.assertRaises(Refusal, self.store.collect, old,
                          {"exit": 0, "result": result(), "capture": "complete", "cleanup": "done"})
        self.assertEqual(self.store.attempt(old)["exit"], 1)
        self.assertEqual(len(self.store.rows("SELECT * FROM results WHERE attempt=?", (old,))), 1)
        self.assertIsNone(self.store.reserve())

    def test_A11_restart_lost_handle_or_PID_does_not_free_slot(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        self.store.begin(attempt, {"pid_information_only": 1, "stale_file": "DONE"})
        restarted = Store(self.config)
        self.addCleanup(restarted.close)
        self.assertIsNone(restarted.reserve())
        self.assertRaises(Refusal, restarted.finish_job, job["id"], job["token"])
        self.assertIsNone(self.store.attempt(attempt)["ended"])

    def test_A12_exclusive_recovery_requires_real_end_effects_and_context(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        old = self.store.start_job(job["id"], job["token"])
        collect(self.store, old, result("PARTIAL"), code=1)
        self.store.finish_job(job["id"], job["token"])
        second = Store(self.config)
        self.addCleanup(second.close)
        self.assertIsNotNone(second.claim_recovery(job["id"]))
        self.assertIsNone(self.store.claim_recovery(job["id"]))
        diagnosis = second.diagnosis_attempt(job["id"])
        collect(second, diagnosis, {"profile": ".codex3", "remaining": "complete only remaining finding", "rationale": "explicit capacity handoff"})
        self.assertRaises(Refusal, second.handoff, job["id"], diagnosis)
        self.store.reconcile_effects(job["id"], job["token"], self.config["roles"]["Work"]["owner"],
                                     {"evidence": ["actual fixture end and no effects"], "unknown_effects": []})
        replacement = second.handoff(job["id"], diagnosis)
        current = second.attempt(replacement)
        self.assertEqual(current["profile"], ".codex3")
        context = json.loads(current["detail"])
        self.assertEqual(context["prior_session"], self.store.attempt(old)["session"])
        self.assertEqual(context["prior_attempt"], old)
        self.assertFalse(context["native_resume"])
        second.begin(replacement, {"fixture_process_began": True})
        self.assertEqual(json.loads(second.attempt(replacement)["detail"])["prior_attempt"], old)
        self.assertRaises(Refusal, self.store.collect, old,
                          {"exit": 0, "capture": "complete", "cleanup": "done", "result": result()})
        self.assertIsNone(second.attempt(replacement)["ended"])
        self.assertEqual(second.job(job["id"])["active_attempt"], replacement)
        self.assertRaises(Refusal, self.store.finish_job, job["id"], job["token"])
        self.assertRaises(Refusal, second.handoff, job["id"], diagnosis)

    def test_A13_healthy_no_alert_unchanged_violations_recur_recovery_one_owner(self):
        self.assertEqual(self.store.emit_alerts(), [])
        self.store.ingest(event(self.config))
        self.now += 100
        first, second = self.store.emit_alerts(), self.store.emit_alerts()
        self.assertEqual({a["kind"] for a in first}, {"ack-lag", "backlog"})
        self.assertEqual({a["kind"] for a in second}, {"ack-lag", "backlog"})
        self.assertFalse({a["id"] for a in first} & {a["id"] for a in second})

    def test_A12_A13_actual_recovery_controller_race_has_one_owner(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        collect(self.store, attempt, result("PARTIAL"), code=1)
        self.store.finish_job(job["id"], job["token"])
        context = multiprocessing.get_context("fork")
        barrier = context.Barrier(2)
        pipes = [context.Pipe(False), context.Pipe(False)]
        workers = [context.Process(target=race_recovery, args=(self.config, job["id"], barrier, pipe[1])) for pipe in pipes]
        for worker in workers:
            worker.start()
        answers = [pipe[0].recv() for pipe in pipes]
        for worker in workers:
            worker.join(10)
            self.assertEqual(worker.exitcode, 0)
        winner = [a for a in answers if a]
        self.assertEqual(len(winner), 1)
        self.assertEqual(self.store.job(job["id"])["recovery_owner"], winner[0])
        self.assertEqual(self.store.job(job["id"])["recovery_count"], 1)

    def test_A14_processed_plus_24h_holds_exact_cleanup_and_no_symlink_follow(self):
        original = event(self.config)
        queued(self.store, original)
        job = self.store.reserve()
        self.now += 500
        attempt = ended_job(self.store, job)
        processed = self.store.one("SELECT processed_at FROM events WHERE id=?", (original["id"],))["processed_at"]
        self.assertEqual(processed, self.now)
        root = self.store.home / "artifacts" / attempt
        root.mkdir(parents=True, mode=0o700)
        target = root / "owned.txt"
        target.write_text("conserved fixture evidence")
        register_artifact(self.store, attempt, target)
        conserve(self.store, target, self.config["roles"]["Work"]["owner"], {"consumer": "fixture", "kept_meaning": True})
        self.now = processed+86399
        sweep(self.store)
        self.assertTrue(target.exists())
        self.now += 1
        self.store.set_hold(original["id"], "consumer not finished")
        sweep(self.store)
        self.assertTrue(target.exists())
        self.store.set_hold(original["id"], None)
        external = Path(self.temp.name) / "foreign.txt"
        external.write_text("never delete")
        target.unlink()
        target.symlink_to(external)
        receipts = sweep(self.store)
        self.assertTrue(external.is_file())
        self.assertTrue(any(r["state"] == "partial-held" for r in receipts))
        self.assertEqual(sweep(self.store)[0]["state"], "artifact-held")  # No replay of errored deletion.

    def test_storage_backpressure_and_legacy_holds_conserve_pending(self):
        self.store.db.execute("UPDATE enrollments SET legacy_hold='actual unknown original' WHERE role='Work'")
        queued(self.store, event(self.config))
        self.assertIsNone(self.store.reserve())
        self.config["limits"]["max_events"] = 1
        self.assertRaises(Backpressure, self.store.ingest, event(self.config, "held-second"))
        self.assertEqual(len(self.store.rows("SELECT * FROM events")), 1)


class Processes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordinator-process-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)

    def adapter(self, plan):
        path = Path(self.temp.name) / f"plan-{ident()}.json"
        path.write_text(encode(plan))
        return AppServer(self.config, [sys.executable, str(Path(__file__).with_name("fixture_appserver.py")), str(path)])

    async def run_task(self, plan):
        queued(self.store, event(self.config, ident()))
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        outcome = await self.adapter(plan).run(self.store, attempt, "bounded fixture task", self.config["tasks"]["work-integrator"])
        self.store.collect(attempt, outcome)
        return job, attempt, outcome

    async def test_A10_actual_DONE_before_process_exit_cannot_release(self):
        queued(self.store, event(self.config))
        job = self.store.reserve()
        attempt = self.store.start_job(job["id"], job["token"])
        observed = asyncio.Event()
        original_observer = self.store.observe_semantic
        def semantic_observer(attempt_id, semantic):
            original_observer(attempt_id, semantic)
            observed.set()
        self.store.observe_semantic = semantic_observer
        task = asyncio.create_task(self.adapter({"result": result(), "exit_delay": 0.3}).run(
            self.store, attempt, "fixture", self.config["tasks"]["work-integrator"]))
        await asyncio.wait_for(observed.wait(), 2)
        self.assertFalse(task.done())
        self.assertEqual(self.store.attempt(attempt)["semantic"], "DONE")
        self.assertIsNone(self.store.attempt(attempt)["ended"])
        self.assertRaises(Refusal, self.store.finish_job, job["id"], job["token"])
        outcome = await task
        self.assertEqual(outcome["exit"], 0)
        self.assertEqual(outcome["result"]["semantic"], "DONE")
        self.assertEqual(outcome["cleanup"], "done")
        self.store.collect(attempt, outcome)
        self.store.finish_job(job["id"], job["token"])
        self.assertEqual(self.store.job(job["id"])["state"], "closed")

    async def test_A10_nonzero_plus_report_zero_invalid_and_capture_failure_stay_held(self):
        job, attempt, outcome = await self.run_task({"result": result(), "exit": 7})
        self.assertEqual(outcome["exit"], 7)
        self.assertEqual(outcome["result"]["semantic"], "DONE")
        self.store.finish_job(job["id"], job["token"])
        self.assertEqual(self.store.job(job["id"])["state"], "held")
        # Separate role so the held Work slot cannot be accidentally reused.
        queued(self.store, event(self.config, "invalid", "Branch"))
        branch = self.store.reserve()
        a = self.store.start_job(branch["id"], branch["token"])
        bad = await self.adapter({"raw_final": "{invalid", "result": {}}).run(self.store, a, "fixture", self.config["tasks"]["branch-integrator"])
        self.assertEqual(bad["exit"], 0)
        self.assertIsNotNone(bad["error"])
        self.store.collect(a, bad)
        self.store.finish_job(branch["id"], branch["token"])
        self.assertEqual(self.store.job(branch["id"])["state"], "held")

    async def test_A12_real_owned_supported_same_session_continuation(self):
        self.config["deadlines"]["task"] = 0.1
        job, attempt, outcome = await self.run_task({"result": result(), "hang_first": True})
        self.assertEqual(outcome["exit"], 0)
        self.assertIsNone(outcome["error"])
        self.assertTrue(json.loads(self.store.attempt(attempt)["detail"])["resume_attempted"])
        self.assertIn("same-session", outcome["detail"]["resume_disposition"])
        self.store.finish_job(job["id"], job["token"])
        self.assertEqual(self.store.job(job["id"])["state"], "closed")

    async def test_role_model_mismatch_and_ephemeral_refusal_have_actual_exits(self):
        job, attempt, outcome = await self.run_task({"result": result(), "model": "wrong-model"})
        self.assertEqual(outcome["exit"], 0)
        self.assertIn("binding differs", outcome["error"])
        self.assertIsNone(outcome["result"])
        self.assertNotEqual(outcome["cleanup"], "done")


if __name__ == "__main__":
    unittest.main()
