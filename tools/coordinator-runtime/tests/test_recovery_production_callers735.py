"""Real reconciliation/request/scheduler callers in retained owned fiction.

Principals, model answers and discovery-neighbor registration are synthetic.
Holds use a second Store connection; no provider, live journal or handle runs.
"""
from contextlib import contextmanager
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from coordinator_runtime import dispatcher, processing, service, windows
from coordinator_runtime.contracts import LUNA, Refusal
from coordinator_runtime.store import Store
from test_hold_recovery_retention731 import Recovery
from test_retained_catalog717 import CatalogCase


class ProductionRecovery(CatalogCase, unittest.IsolatedAsyncioTestCase):
    bound_job = Recovery.bound_job
    hold = Recovery.hold
    neighbor = Recovery.neighbor
    failed = Recovery.failed
    request = Recovery.request
    model = Recovery.model
    deny_new_context = Recovery.deny_new_context

    @contextmanager
    def reconciliation_guard(self):
        with self.deny_new_context(), \
             patch.object(self.store, 'attempt', side_effect=AssertionError('old attempt body acquired')), \
             patch.object(self.store, 'failure_delivery', side_effect=AssertionError('new failure payload')):
            yield
        self.assertEqual(self.read_violations, [])

    def foreign_dispatcher(self):
        # A genuinely distinct fixture controller, never a borrowed identity.
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        self.runtime = dispatcher.Dispatcher(self.store, models=object(), boards=self.boards)

    def snapshot(self):
        return dict(job=self.store.job(self.job['id']),
            attempts=self.store.rows('SELECT * FROM attempts WHERE job=? ORDER BY rowid', (self.job['id'],)),
            requests=self.store.rows('SELECT * FROM recovery_requests WHERE job=? ORDER BY rowid', (self.job['id'],)),
            allocation=windows.current(self.store))

    async def reconciliation(self, kind):
        self.failed()
        if kind == 'finite':
            self.runtime = processing.ProcessingDispatcher(self.store, models=object(), boards=self.boards)
        elif kind == 'continuing':
            self.runtime = service.Dispatcher(self.store, self.boards, models=object())
        neighbor = self.neighbor()
        async def run(store, attempt, prompt, spec, schema):
            self.assertFalse(store.db.in_transaction)
            store.begin(attempt, {'fictional': True})
            self.hold(neighbor, '')
            # Real outer caller while the admitted original diagnosis is live.
            with self.reconciliation_guard():
                self.runtime.reconcile_completed()
            return dict(exit=0, capture='complete', cleanup='done',
                result=dict(profile='@owner', remaining='Actual fixture owner choice', rationale='Retain duty'),
                detail=dict(binding_readback=LUNA, root_identity_observed=True))
        self.runtime.models = Mock(run=AsyncMock(side_effect=run))
        await self.runtime.recover(self.job)
        self.runtime.models.run.assert_awaited_once()
        diagnosis = self.store.one("SELECT * FROM attempts WHERE job=? AND kind='diagnosis'", (self.job['id'],))
        self.assertEqual(diagnosis['state'], 'collected')  # Hold did not block lawful collection.
        self.assertEqual(diagnosis['exit'], 0)
        pending = self.snapshot()
        self.assertEqual(pending['job']['recovery_state'], 'awaiting-disposition')
        self.assertEqual(self.store.attempt(self.attempt), self.original)
        self.assertEqual(self.store.rows('SELECT * FROM recovery_dispositions'), [])
        self.assertEqual(self.store.rows("SELECT * FROM outboxes WHERE kind='question'"), [])
        for held in (True, False):
            if not held: self.hold(neighbor, None)
            with self.reconciliation_guard():
                for _ in range(3): self.runtime.reconcile_completed()
            self.assertEqual(self.snapshot(), pending)
        # Supported explicit owner consumption, through this production caller.
        request = self.request('defer')
        self.runtime.reconcile_recovery_requests()
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?', (request['id'],))['state'], 'consumed')
        self.assertEqual(self.store.job(self.job['id'])['recovery_state'], 'owner-deferred')
        self.assertEqual(self.store.attempt(self.attempt), self.original)

    async def test_generic_reconciliation_live_collection_and_pending_ticks(self):
        await self.reconciliation('generic')

    async def test_finite_reconciliation_live_collection_and_pending_ticks(self):
        await self.reconciliation('finite')

    async def test_continuing_reconciliation_live_collection_and_pending_ticks(self):
        await self.reconciliation('continuing')

    async def test_collected_failure_before_claim_refuses_each_real_caller_and_finish(self):
        self.bound_job()
        from support import collect, result
        collect(self.store, self.attempt, result('FAILED'), code=1, error='fictional failure')
        before = self.snapshot()
        for event in (self.source['id'], self.neighbor()):
            self.hold(event, '')
            for runtime in (self.runtime,
                    processing.ProcessingDispatcher(self.store, models=object(), boards=self.boards),
                    service.Dispatcher(self.store, self.boards, models=object())):
                with self.reconciliation_guard():
                    runtime.reconcile_completed()
                    runtime.try_finish(self.job['id'])
                self.assertEqual(self.snapshot(), before)
            self.hold(event, None)
        # The unheld production path still creates the owed failure payload.
        self.runtime.reconcile_completed()
        self.assertEqual(self.store.job(self.job['id'])['state'], 'held')
        self.assertTrue(self.store.rows('SELECT id FROM outboxes WHERE job=?', (self.job['id'],)))

    async def collected_request(self, mode='defer'):
        self.failed()
        self.model()
        await self.runtime.recover(self.job)
        return self.request(mode)

    async def test_pending_foreign_request_hold_before_transfer_preserves_all_custody(self):
        request = await self.collected_request()
        neighbor = self.neighbor()
        self.foreign_dispatcher()
        before = self.snapshot()
        authorize = self.runtime.authorize_roles
        def boundary(roles):
            authorize(roles)
            self.hold(neighbor, '')  # Commit after caller authority, before request transaction.
        with patch.object(self.runtime, 'authorize_roles', side_effect=boundary), self.reconciliation_guard():
            self.runtime.reconcile_recovery_requests()
        self.assertEqual(self.snapshot(), before)
        self.hold(neighbor, None)
        self.runtime.reconcile_recovery_requests()
        row = self.store.job(self.job['id'])
        self.assertEqual(row['controller'], self.store.controller)
        self.assertEqual(row['recovery_owner'], before['job']['recovery_owner'])
        self.assertEqual(row['recovery_count'], before['job']['recovery_count'])
        self.assertEqual(row['recovery_state'], 'owner-deferred')
        self.assertEqual(self.store.attempt(self.attempt), self.original)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?', (request['id'],))['state'], 'consumed')

    async def test_later_request_refusal_rolls_back_closure_transfer(self):
        await self.collected_request('remaining-work')
        self.foreign_dispatcher()
        before = self.snapshot()
        with patch.object(self.store, 'remaining_work_fence', side_effect=Refusal('fictional later disposition refusal')):
            self.runtime.reconcile_recovery_requests()
        self.assertEqual(self.snapshot(), before)

    async def test_retained_diagnosis_keeps_explicit_numeric_END_continuity_checks(self):
        self.failed(selected=True)
        self.held_event = self.neighbor()
        self.model(profile='.codex3', hold=True)
        try:
            await self.runtime.recover(self.job)
        finally:
            if hasattr(self, 'context_guard'): self.context_guard.__exit__(None, None, None)
        self.hold(self.held_event, None)
        diagnosis = self.store.one("SELECT * FROM attempts WHERE kind='diagnosis'")
        continuity = dict(scope='closure-only-after-owned-restart', from_controller=self.store.controller,
            service_actor=self.config['actor'], service_end=0, service_collected=True,
            evidence=['Fictional genuine owner supplied actual original service collection'])
        for invalid in (None, True):
            with self.assertRaises(Refusal):
                self.request('use-diagnosis', diagnosis=diagnosis['id'], selection=self.selection_request['id'],
                    collector_continuity={**continuity, 'service_end':invalid})
        request = self.request('use-diagnosis', diagnosis=diagnosis['id'], selection=self.selection_request['id'],
            collector_continuity=continuity)
        previous = self.store.controller
        self.foreign_dispatcher()
        self.runtime.execute = AsyncMock()  # Successor allocation is real; no provider runs.
        self.runtime.reconcile_recovery_requests()
        await asyncio.gather(*self.runtime.active)
        self.runtime.execute.assert_awaited_once()
        row = self.store.job(self.job['id'])
        self.assertEqual(row['controller'], self.store.controller)
        self.assertEqual(row['recovery_owner'], previous)
        self.assertEqual(row['recovery_count'], 1)
        self.assertEqual(row['recovery_state'], 'handed-off')
        self.assertEqual(self.store.attempt(self.attempt), self.original)
        self.assertEqual(self.store.attempt(diagnosis['id']), diagnosis)
        consumed = self.store.one('SELECT * FROM recovery_requests WHERE id=?', (request['id'],))
        self.assertEqual(consumed['state'], 'consumed')
        self.assertIsNotNone(json.loads(consumed['result'])['collector_continuity'])

    async def test_generic_foreign_claim_preallocation_hold_then_supported_owner_recovery(self):
        # Failure becomes visible after B's reconciliation phase. The ordinary
        # scheduler really commits a foreign claim before its coroutine runs.
        self.bound_job()
        owner = self.store
        original = owner.attempt(self.attempt)
        self.foreign_dispatcher()
        self.runtime.reconcile_completed()
        from support import collect, result
        collect(owner, self.attempt, result('FAILED'), code=1, error='fictional late failure')
        owner.hold_job(self.job['id'], 'fictional late failure')
        owner.reconcile_effects(self.job['id'], self.job['token'], self.config['roles']['Work']['owner'],
            dict(evidence=['fictional original effects accounted for'], unknown_effects=[]))
        self.original = owner.attempt(self.attempt)
        self.assertEqual(self.original['controller'], original['controller'])
        self.runtime.schedule_recovery()
        claimed = self.store.job(self.job['id'])
        self.assertNotEqual(claimed['controller'], self.store.controller)
        self.assertEqual(claimed['recovery_owner'], self.store.controller)
        self.assertEqual(claimed['recovery_state'], 'claimed')
        self.hold(reason='fictional after foreign claim')
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('held diagnosis launched')))
        with self.deny_new_context():
            await asyncio.gather(*self.runtime.active)
        self.assertEqual(self.read_violations, [])
        self.assertEqual(self.runtime.runtime_errors, {})
        self.runtime.models.run.assert_not_called()
        suspended = self.store.job(self.job['id'])
        self.assertEqual(suspended['controller'], claimed['controller'])
        self.assertEqual(suspended['recovery_owner'], claimed['recovery_owner'])
        self.assertEqual(suspended['recovery_state'], 'awaiting-disposition')
        self.assertEqual(suspended['recovery_count'], 1)
        self.assertEqual(self.store.rows("SELECT id FROM attempts WHERE kind='diagnosis'"), [])
        marker = self.store.one('SELECT detail FROM operational_errors WHERE subject=?', ('recovery-admission:'+self.job['id'],))
        self.assertIsNone(json.loads(marker['detail'])['diagnosis'])
        self.hold(reason=None)
        with self.reconciliation_guard(): self.runtime.reconcile_completed()
        self.runtime.schedule_recovery()
        self.assertEqual(len(self.runtime.active), 0)  # Spent automatic claim stays spent.
        request = self.request('remaining-work')  # Genuine role owner, existing public API.
        self.model()
        self.runtime.reconcile_recovery_requests()
        await asyncio.gather(*self.runtime.active)
        self.runtime.models.run.assert_awaited_once()
        current = self.store.job(self.job['id'])
        self.assertEqual(current['controller'], self.store.controller)
        self.assertEqual(current['recovery_owner'], self.store.controller)
        self.assertEqual(current['recovery_count'], 2)
        self.assertEqual(current['recovery_state'], 'awaiting-disposition')
        self.assertEqual(current['token'], claimed['token'])
        self.assertEqual(self.store.attempt(self.attempt), self.original)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?', (request['id'],))['state'], 'consumed')
        self.assertEqual(len(self.store.rows('SELECT * FROM recovery_dispositions')), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
