"""Offline caller/launch/control outcomes; no real account or provider access."""

import asyncio
from concurrent.futures import ProcessPoolExecutor
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, queued, collect, result
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.contracts import Refusal, LUNA
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.execution_pool import _module
from coordinator_runtime.store import Store

POOL = ['.codex2', '.codex3', '.codex5']


def reserve_in_process(routes):
    return _module.Pool(routes).allocate()


class ExecutionPool(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='execution-pool-owned-fixture-')
        self.addCleanup(self.temp.cleanup)  # These synthetic fixtures have no consumer/effect holds.
        self.home = Path(self.temp.name)
        self.config = config_at(self.home)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.pool = _module.Pool(self.config['execution_pool_routes'])

    def adapter(self, plan=None):
        path = self.home/'plan.json'
        path.write_text(json.dumps(plan or {'result': result()}))
        return AppServer(self.config, [sys.executable, str(Path(__file__).with_name('fixture_appserver.py')), str(path)])

    async def test_allocation_across_classifier_task_diagnosis_and_successor_conserves_original(self):
        message = event(self.config)
        source = copy.deepcopy(message)
        grants = self.store.rows('SELECT * FROM enrollments')
        classifier = queued(self.store, message)
        job = self.store.reserve()
        # Explicit runtime choices are allocation advice, even when disabled.
        old = self.store.start_job(job['id'], job['token'], profile='.codex4')
        collect(self.store, old, result('PARTIAL'), code=1)
        self.store.finish_job(job['id'], job['token'])
        self.store.reconcile_effects(job['id'], job['token'], self.config['roles']['Work']['owner'],
                                    {'evidence': ['owned fixture effects accounted'], 'unknown_effects': []})
        self.store.claim_recovery(job['id'])
        diagnosis = self.store.diagnosis_attempt(job['id'])
        advice = {'profile': '.codex3', 'remaining': 'same original remainder', 'rationale': 'same purpose and evidence'}
        collect(self.store, diagnosis, advice)
        originals = [self.store.attempt(a) for a in (classifier, old, diagnosis)]
        successor = self.store.handoff(job['id'], diagnosis)
        self.assertEqual([self.store.attempt(a)['profile'] for a in (classifier, old, diagnosis, successor)],
                         ['.codex2', '.codex3', '.codex5', '.codex2'])
        context = json.loads(self.store.attempt(successor)['detail'])
        self.assertEqual(context['choice'], advice)
        self.assertEqual(context['prior_attempt'], old)
        self.assertEqual([self.store.attempt(a) for a in (classifier, old, diagnosis)], originals)
        self.assertEqual(self.store.event(message['id']), source)
        self.assertEqual(self.store.rows('SELECT * FROM enrollments'), grants)
        self.assertEqual(self.config['roles']['Work']['profile'], '.codex')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (message['id'],))['processed_at'])
        self.assertEqual(json.loads(self.store.attempt(old)['detail'])['profile_advice'], '.codex4')
        self.assertEqual(json.loads(self.store.attempt(diagnosis)['binding']), LUNA)

    async def test_reclassification_recovery_is_also_a_new_pool_turn(self):
        self.store.ingest(event(self.config))
        failed, _ = self.store.claim_classification()
        collect(self.store, failed, None, code=1, error='owned fixture failure')
        self.store.classification_failed(failed, 'no valid classification')
        diagnosis, _ = self.store.claim_classification_recovery()
        self.assertEqual(self.store.attempt(failed)['profile'], '.codex2')
        self.assertEqual(self.store.attempt(diagnosis)['profile'], '.codex3')
        self.assertEqual(json.loads(self.store.attempt(diagnosis)['detail'])['prior_classifier'], failed)

    async def test_disabling_old_eligible_reservation_after_preflight_blocks_actual_process(self):
        # Simulates either excluded account having been eligible at reservation.
        for profile in ('.codex', '.codex4'):
            self.pool.set([profile])
            self.store.ingest(event(self.config, profile))
            attempt, _ = self.store.claim_classification()
            adapter = self.adapter()
            original_command = adapter.command
            async def changed_after_preflight(*args):
                command = await original_command(*args)
                self.pool.set(POOL)
                return command
            adapter.command = changed_after_preflight
            with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',
                       side_effect=AssertionError('disabled account must never start')):
                outcome = await adapter.run(self.store, attempt, 'fixture', {'cwd': str(self.home), 'sandbox': 'read-only'})
            self.assertTrue(outcome['detail']['known_not_started'])
            self.assertIn('disabled before launch', outcome['error'])
            self.assertIsNone(self.store.attempt(attempt)['begin'])
            self.assertEqual(self.store.attempt(attempt)['profile'], profile)
            self.store.collect(attempt, outcome)

    async def test_real_fixture_launches_rotate_and_post_begin_exclusion_does_not_move_call(self):
        attempts = []
        self.store.launch_authorizer = lambda roles: None
        for number in range(3):
            self.store.ingest(event(self.config, str(number)))
            attempt, _ = self.store.claim_classification()
            attempts.append(attempt)
        adapter = self.adapter({'result': {'fixture': 'not a classification'}})
        outcomes = await asyncio.wait_for(asyncio.gather(*[
            adapter.run(self.store, a, 'fixture', {'cwd': str(self.home), 'sandbox': 'read-only'}) for a in attempts]), 10)
        for attempt, outcome in zip(attempts, outcomes):
            self.assertEqual(outcome['exit'], 0, outcome)
            row = self.store.attempt(attempt)
            self.assertIsNotNone(row['begin'])
            self.assertEqual(json.loads(row['detail'])['execution_pool_admission']['profile'], row['profile'])
        before = [self.store.attempt(a) for a in attempts]
        self.pool.set([])
        self.assertEqual([self.store.attempt(a) for a in attempts], before)
        self.assertEqual([r['profile'] for r in before], POOL)

    async def test_operator_update_waits_through_process_creation_and_BEGIN_then_preserves_live_original(self):
        self.store.ingest(event(self.config))
        attempt, _ = self.store.claim_classification()
        adapter = self.adapter({'result': {'fixture': True}, 'exit_delay': .15})
        entering, release = asyncio.Event(), asyncio.Event()
        started_update = threading.Event()
        actual_spawn = asyncio.create_subprocess_exec
        async def delayed_spawn(*args, **kwargs):
            entering.set()
            await release.wait()
            return await actual_spawn(*args, **kwargs)
        def update():
            started_update.set()
            return self.pool.set(['.codex3', '.codex5'])
        with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec', delayed_spawn):
            running = asyncio.create_task(adapter.run(self.store, attempt, 'fixture', {'cwd': str(self.home), 'sandbox': 'read-only'}))
            await asyncio.wait_for(entering.wait(), 3)
            changing = asyncio.create_task(asyncio.to_thread(update))
            await asyncio.to_thread(started_update.wait, 3)
            self.assertFalse(changing.done())
            self.assertIsNone(self.store.attempt(attempt)['begin'])
            release.set()
            change = await asyncio.wait_for(changing, 3)
            original = self.store.attempt(attempt)
            self.assertIsNotNone(original['begin'])
            self.assertEqual(original['profile'], '.codex2')
            self.assertNotIn(original['profile'], change['enabled'])
            outcome = await asyncio.wait_for(running, 3)
        self.assertEqual(outcome['exit'], 0)
        self.assertEqual(self.store.attempt(attempt)['profile'], original['profile'])
        self.assertEqual(self.store.attempt(attempt)['controller'], original['controller'])

    async def test_empty_invalid_unavailable_and_unauthorized_have_no_attempt_or_fallback(self):
        self.store.ingest(event(self.config))
        self.pool.set([])
        with self.assertRaisesRegex(Refusal, 'empty'):
            self.store.claim_classification()
        self.assertEqual(self.store.rows('SELECT * FROM attempts'), [])
        path = Path(self.config['execution_pool_routes'])
        valid = path.read_text()
        for broken in ('not toml', valid.replace('pool = []', 'pool = [".codex7"]')):
            path.write_text(broken)
            with self.assertRaises(Refusal): self.store.claim_classification()
        path.unlink()
        with self.assertRaises(Refusal): self.store.claim_classification()
        path.write_text(valid)
        self.pool.set(POOL)
        # Authorization is separate and must not be silently expanded/intersected.
        self.store.execution_pool.authorized = ['.codex3']
        with self.assertRaisesRegex(Refusal, 'authorization'): self.store.claim_classification()
        self.assertEqual(self.store.rows('SELECT * FROM attempts'), [])
        self.assertEqual(self.pool.status()['turn'], 0)

    async def test_concurrent_reservation_fairness_restart_and_shared_parent_counter(self):
        with ProcessPoolExecutor(max_workers=6) as workers:
            choices = list(workers.map(reserve_in_process, [self.config['execution_pool_routes']]*24))
        ordered = sorted(choices, key=lambda c: c['turn'])
        self.assertEqual([c['turn'] for c in ordered], list(range(24)))
        self.assertEqual([c['profile'] for c in ordered], POOL*8)
        restarted = Store(self.config)
        self.addCleanup(restarted.close)
        # Parent API and reopened runtime share a single counter, not fixed pins.
        parent = reserve_in_process(self.config['execution_pool_routes'])
        restarted.ingest(event(self.config))
        attempt, _ = restarted.claim_classification()
        self.assertEqual(parent['profile'], '.codex2')
        self.assertEqual(restarted.attempt(attempt)['profile'], '.codex3')
        self.assertEqual(self.pool.status()['turn'], 26)

    async def test_operator_interface_conserves_other_settings_and_next_turn(self):
        path = Path(self.config['execution_pool_routes'])
        before = _module.tomllib.loads(path.read_text())
        cli = str(_module.__file__)
        changed = subprocess.run([sys.executable, cli, '--routes', str(path), 'set', '.codex3', '.codex5'],
                                 capture_output=True, text=True)
        self.assertEqual(changed.returncode, 0, changed.stdout)
        after = _module.tomllib.loads(path.read_text())
        before['providers']['codex']['pool'] = ['.codex3', '.codex5']
        self.assertEqual(after, before)
        status = subprocess.run([sys.executable, cli, '--routes', str(path), 'status'], capture_output=True, text=True)
        self.assertEqual(status.returncode, 0)
        self.assertEqual(json.loads(status.stdout)['profile'], '.codex3')
        self.assertEqual(self.pool.status()['turn'], 0)
        self.assertEqual(self.pool.allocate()['profile'], '.codex3')
        self.assertEqual(self.pool.allocate()['profile'], '.codex5')

    async def test_pool_unavailability_keeps_frozen_job_retryable_without_task_replay(self):
        queued(self.store, event(self.config))
        runtime = Dispatcher(self.store, models=object(), boards={})
        runtime.execute = lambda *args: asyncio.sleep(0)
        self.pool.set([])
        with self.assertRaisesRegex(Refusal, 'empty'): runtime.schedule_job()
        job = self.store.one('SELECT * FROM jobs')
        self.assertIsNone(job['active_attempt'])
        self.pool.set(POOL)
        runtime.schedule_job()
        await asyncio.gather(*runtime.active)
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')), 1)
        self.assertIsNotNone(self.store.job(job['id'])['active_attempt'])


if __name__ == '__main__':
    unittest.main()
