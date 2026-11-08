"""Real async callers in retained fiction; never a provider or live journal.

Holds commit through a second Store at explicit await/scheduling boundaries.
The model answer and principal authentication are synthetic. Ordinary Git
effects/readbacks execute only in the newly owned fixture repository.
"""
from contextlib import ExitStack
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import AsyncMock, Mock, patch

from coordinator_runtime import dispatcher, ordinary
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.store import Store
from support import collect, config_at, enrolled, event, queued, result
from test_hold_recovery_retention731 import Recovery
from test_ordinary_effects import OrdinaryEffects


class ContextFixture:
    deny_new_context = Recovery.deny_new_context

    def hold(self, event_id, reason=''):
        owner = Store(self.config)
        try:
            owner.set_hold(event_id, reason)
        finally:
            owner.close()

    def neighbor(self, job=None):
        # Only discovery registration is synthetic, as in the735 fixture.
        message = event(self.config, ident())
        self.store.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',
            (message['id'], message['role'], encode(message), digest(message), self.store.clock()))
        queue_id = ident()
        self.store.db.execute('INSERT INTO queue(id,event,role,phase,task) VALUES(?,?,?,?,?)',
            (queue_id, message['id'], message['role'], 'integrator', 'work-integrator'))
        member = self.store._input_member(self.store.one('SELECT * FROM queue WHERE id=?', (queue_id,)))
        self.store.db.execute('INSERT INTO local_jobs VALUES(?,?,?)',
            ((job or self.job)['id'], digest(self.config.get('local_integration')),
             encode(dict(lane='report', report_route=None, neighbors=[member]))))
        return message['id']

    def member(self):
        return json.loads(self.job['members'])[0]['event']

    def target(self, kind):
        if kind.startswith('dependency-'):
            return (self.neighbor(self.effect_job) if kind == 'dependency-neighbor'
                    else json.loads(self.effect_job['members'])[0]['event'])
        return self.neighbor() if kind == 'neighbor' else self.member()


class PostModel(ContextFixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.area = Path(os.environ['QA629_FIXTURES']) / self._testMethodName / ident()
        self.area.mkdir(mode=0o700, parents=True)
        self.config = config_at(self.area)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        queued(self.store, event(self.config, ident()))
        self.job = self.store.reserve()
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])
        self.job = self.store.job(self.job['id'])
        self.boards = {r:Mock() for r in self.config['roles']}
        self.runtime = dispatcher.Dispatcher(self.store, models=object(), boards=self.boards)

    async def execute(self, kind=None):
        held_event = self.target(kind) if kind else None
        admitted, release = asyncio.Event(), asyncio.Event()
        async def model(store, attempt, prompt, spec, schema):
            self.assertFalse(store.db.in_transaction)
            store.begin(attempt, {'fictional': True})
            store.session(attempt, ident())
            admitted.set()
            await release.wait()
            return dict(exit=0, capture='complete', cleanup='done', result=result(),
                        detail=dict(tool_completion=dict(complete=True, items=[], nonzero_completions=[])))
        self.runtime.models = Mock(run=AsyncMock(side_effect=model))
        inventory = self.runtime.inventory_artifacts
        with ExitStack() as stack:
            def inventoried(*args):
                # Collection and inventory belong to the admitted original.
                value = inventory(*args)
                if held_event:
                    stack.enter_context(self.deny_new_context())
                return value
            stack.enter_context(patch.object(self.runtime, 'inventory_artifacts', side_effect=inventoried))
            child = asyncio.create_task(self.runtime.execute(self.job['id'], self.attempt))
            try:
                await asyncio.wait_for(admitted.wait(), 5)
                if held_event:
                    self.hold(held_event)
                release.set()
                await child
            finally:
                release.set()
                await asyncio.gather(child, return_exceptions=True)
        self.runtime.models.run.assert_awaited_once()
        attempt = self.store.attempt(self.attempt)
        self.assertEqual(attempt['exit'], 0)
        self.assertIsNotNone(attempt['ended'])
        self.assertIsNotNone(attempt['collected'])
        self.assertEqual(attempt['capture'], 'complete')
        self.assertEqual(attempt['semantic'], 'DONE')
        self.assertEqual(attempt['controller'], self.store.controller)
        self.assertEqual(json.loads(attempt['result']), result())
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'), [])
        if held_event:
            self.assertEqual(self.read_violations, [])
            current = self.store.job(self.job['id'])
            self.assertEqual(current['state'], 'held')
            self.assertIn('admission changed', current['hold_reason'])
            self.assertEqual(current['active_attempt'], self.attempt)
            self.assertEqual(self.store.rows('SELECT * FROM outboxes'), [])
            # Real explicit owner disposition, never a replay or a new model.
            self.hold(held_event, None)
            request = self.store.request_recovery(current['id'], current['token'], self.attempt,
                self.config['roles']['Work']['owner'], dict(mode='redispose', remaining=None,
                    reason='Fixture source released; finish the collected original',
                    evidence=['Original numeric END0 and no effects; no new worker']))
            self.runtime.reconcile_recovery_requests()
            self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',
                (request['id'],))['state'], 'consumed')
        self.assertEqual(self.store.job(self.job['id'])['state'], 'closed', self.store.job(self.job['id'])['hold_reason'])
        for key in ('result', 'exit', 'ended', 'collected', 'controller', 'session'):
            self.assertEqual(self.store.attempt(self.attempt)[key], attempt[key])

    async def test_plain_no_epoch_member_hold_after_model_admission(self):
        await self.execute('member')

    async def test_plain_no_epoch_neighbor_hold_after_model_admission(self):
        await self.execute('neighbor')

    async def test_plain_no_epoch_unheld_positive(self):
        await self.execute()

    async def test_direct_whole_detail_counterexample_and_allowed_metadata(self):
        collect(self.store, self.attempt, result())
        self.hold(self.member())
        # This hypothetical harmful caller discards its direct full-detail read
        # before reaching the actual production guard. No snapshots change.
        actual = self.runtime.reconcile_collected
        def harmful(job):
            self.store.one('SELECT detail FROM attempts WHERE id=?', (job['active_attempt'],))
            actual(job)
        with self.deny_new_context():
            with self.assertRaises(sqlite3.DatabaseError):
                harmful(self.job)
        self.assertEqual(self.read_violations, [('attempts', 'detail')])
        with self.deny_new_context():
            self.assertEqual(self.store.one("SELECT id,json_extract(detail,'$.prior_task_attempt') AS prior "
                'FROM attempts WHERE id=?', (self.attempt,)), dict(id=self.attempt, prior=None))
            self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM attempts "
                "WHERE json_extract(detail,'$.prior_task_attempt') IS NULL AND id=?", (self.attempt,)), dict(n=1))
        self.assertEqual(self.read_violations, [])
        for sql in ('SELECT detail AS context FROM attempts WHERE id=?',
                    "SELECT detail,json_extract(detail,'$.prior_task_attempt') FROM attempts WHERE id=?"):
            with self.subTest(sql=sql), self.deny_new_context():
                with self.assertRaises(sqlite3.DatabaseError):
                    self.store.one(sql, (self.attempt,))
            self.assertEqual(self.read_violations, [('attempts', 'detail')])


class Acceptance(ContextFixture, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = OrdinaryEffects.asyncSetUp
    git = OrdinaryEffects.git
    boundary = OrdinaryEffects.boundary
    admission = OrdinaryEffects.admission
    prepared = OrdinaryEffects.prepared

    async def waiting(self):
        self.git('remote', 'set-url', 'origin', 'https://example.invalid/owned-fixture')
        self.boundary()
        self.policy = self.admission()
        self.effect_job, self.effect_attempt = self.prepared()
        await ordinary.perform(self.store, self.boards['Branch'], self.effect_job)
        receipt = json.loads(self.store.one('SELECT receipt FROM ordinary_runs WHERE attempt=?',
                                          (self.effect_attempt,))['receipt'])
        await ordinary.accept(self.store, self.acceptor, self.effect_attempt, 'accepted',
            dict(execution_hash=digest(receipt), rationale='Owned fixture destination matches exact intended source', unknowns=[]))
        queued(self.store, event(self.config, ident(), 'QA', 'qa-cleanup', 'package'))
        self.job = self.store.reserve()
        self.assertEqual(self.job['task'], 'qa-cleanup')
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])
        self.job = self.store.job(self.job['id'])
        collect(self.store, self.attempt, result(category='qualification'),
                tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        ordinary.wait_for_acceptance(self.store, self.job)
        self.original = self.store.attempt(self.attempt)
        self.effect_original = self.store.attempt(self.effect_attempt)
        self.effect_run = self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (self.effect_attempt,))
        self.runtime = dispatcher.Dispatcher(self.store, models=object(), boards=self.boards)

    async def drain(self):
        children = list(self.runtime.active)
        try:
            await asyncio.gather(*children)
        finally:
            await asyncio.gather(*children, return_exceptions=True)
        self.assertEqual(self.runtime.acceptance_active, set())

    def conserved(self):
        self.assertEqual(self.store.attempt(self.effect_attempt), self.effect_original)
        self.assertEqual(self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?',
            (self.effect_attempt,)), self.effect_run)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [])
        self.assertEqual(self.git('rev-parse', 'destination'), self.head)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM attempts WHERE kind='task'")['n'], 2)

    async def continuation(self, kind, boundary):
        await self.waiting()
        held_event = self.target(kind)
        before_tools = self.store.rows('SELECT * FROM ordinary_tool_records')
        with ExitStack() as stack:
            if boundary == 'scheduled':
                self.runtime.reconcile_collected(self.job)
                self.assertEqual(len(self.runtime.active), 1)
                self.hold(held_event)
                stack.enter_context(self.deny_new_context())
            elif boundary in {'readback', 'final-readback'}:
                # The real tool passes admission, starts its own child, then
                # yields while capturing that child's actual numeric END.
                capture = ordinary.capture_process
                captured = 0
                async def during_readback(process, maximum):
                    nonlocal captured
                    self.assertFalse(self.store.db.in_transaction)
                    captured += 1
                    if captured == (1 if boundary == 'readback' else 7):
                        self.hold(held_event)
                        stack.enter_context(self.deny_new_context())
                    return await capture(process, maximum)
                stack.enter_context(patch.object(ordinary, 'capture_process', side_effect=during_readback))
                self.runtime.reconcile_collected(self.job)
            else:
                # Actual qualification completes; the caller still starts a
                # new detail-mutation group after awaiting that coroutine.
                qualify = ordinary.qualification
                async def qualified(*args):
                    await qualify(*args)
                    self.hold(held_event)
                    stack.enter_context(self.deny_new_context())
                stack.enter_context(patch.object(ordinary, 'qualification', side_effect=qualified))
                self.runtime.reconcile_collected(self.job)
            await self.drain()
        self.assertEqual(self.read_violations, [])
        current = self.store.job(self.job['id'])
        self.assertIsNone(current['hold_reason'])
        self.assertNotEqual(current['state'], 'closed')
        self.assertIn(self.job['id'], self.runtime.runtime_errors)
        attempt = self.store.attempt(self.attempt)
        self.assertTrue(json.loads(attempt['detail'])['ordinary_awaiting_acceptance'])
        for key in ('result', 'exit', 'ended', 'collected', 'controller', 'session'):
            self.assertEqual(attempt[key], self.original[key])
        if boundary == 'scheduled':
            self.assertEqual(attempt, self.original)
            self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'), before_tools)
        elif boundary in {'readback', 'final-readback'}:
            fresh = self.store.rows('SELECT record FROM ordinary_tool_records WHERE seq>?',
                                    (before_tools[-1]['seq'],))
            self.assertEqual(len(fresh), 2 if boundary == 'readback' else 14)
            started, collected = [json.loads(r['record']) for r in fresh[-2:]]
            self.assertIsNone(started['exit'])
            self.assertEqual(collected['exit'], 0)
            self.assertTrue(collected['complete'])
            self.assertIn('ended', collected)
            self.assertEqual(collected['pid'], started['pid'])
            self.assertEqual(collected['collector'], self.store.controller)
            self.assertNotIn('ordinary_qualification', json.loads(attempt['detail']))
        self.assertEqual(self.store.rows('SELECT * FROM outboxes'), [])
        self.conserved()
        # The same original waiting duty resumes through the actual caller.
        self.hold(held_event, None)
        self.runtime.reconcile_collected(self.store.job(self.job['id']))
        await self.drain()
        self.assertEqual(self.store.job(self.job['id'])['state'], 'closed', self.store.job(self.job['id'])['hold_reason'])
        detail = json.loads(self.store.attempt(self.attempt)['detail'])
        self.assertNotIn('ordinary_awaiting_acceptance', detail)
        self.assertIn('ordinary_qualification', detail)
        self.conserved()

    async def test_member_hold_after_schedule_before_acceptance_starts(self):
        await self.continuation('member', 'scheduled')

    async def test_neighbor_hold_after_schedule_before_acceptance_starts(self):
        await self.continuation('neighbor', 'scheduled')

    async def test_member_hold_during_original_readback_collection(self):
        await self.continuation('member', 'readback')

    async def test_neighbor_hold_during_original_readback_collection(self):
        await self.continuation('neighbor', 'readback')

    async def test_member_hold_during_final_readback_before_qualification_detail(self):
        await self.continuation('member', 'final-readback')

    async def test_neighbor_hold_during_final_readback_before_qualification_detail(self):
        await self.continuation('neighbor', 'final-readback')

    async def test_dependency_member_hold_during_readback_retains_acceptance_duty(self):
        await self.continuation('dependency-member', 'readback')

    async def test_dependency_neighbor_hold_during_final_readback_retains_acceptance_duty(self):
        await self.continuation('dependency-neighbor', 'final-readback')

    async def test_member_hold_after_qualification_before_caller_detail_mutation(self):
        await self.continuation('member', 'caller')

    async def test_neighbor_hold_after_qualification_before_caller_detail_mutation(self):
        await self.continuation('neighbor', 'caller')

    async def test_unheld_acceptance_positive(self):
        await self.waiting()
        self.runtime.reconcile_collected(self.job)
        await self.drain()
        self.assertEqual(self.store.job(self.job['id'])['state'], 'closed')
        self.assertNotIn('ordinary_awaiting_acceptance', json.loads(self.store.attempt(self.attempt)['detail']))
        self.conserved()


if __name__ == '__main__':
    unittest.main()
