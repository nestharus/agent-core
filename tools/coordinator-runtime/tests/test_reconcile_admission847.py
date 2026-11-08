"""Fresh later native admission; all actors/native answers remain synthetic."""
import asyncio
from contextlib import ExitStack
from unittest.mock import patch
from test_native_reacquisition836 import Reacquisition836
from test_bootstrap_composition832 import CompositeAmendment
from coordinator_runtime import service, processing, ordinary, report_scope, report_repair
from coordinator_runtime.contracts import Refusal


class Reconcile847(Reacquisition836):
    def collected(self, post_await=False):
        job = self.frozen()
        from _receiving485_fixtures import Models
        def answer(current, out):
            reports = report_scope.integration_inputs(self.store, current)
            protocol = report_scope.integration_protocol(self.store, current, reports)
            out['category'] = 'consolidated'
            out['findings'] = [dict(**protocol, analysis='Fictional preserved analysis',
                decision='Report only', method='Fixture method', coverage=[dict(**pin,
                extent='whole', limits=['Fictional native transport']) for pin in protocol['sources']])]
            if post_await:
                self.conflict()
        self.task_result = answer
        self.models = Models(self)
        self.dispatch = service.Dispatcher(self.store, self.boards, self.models, self.transport)
        attempt = self.store.start_job(job['id'], job['token'])
        with patch.object(self.dispatch, 'try_finish'):
            asyncio.run(self.dispatch.execute(job['id'], attempt))
        current = self.store.job(job['id'])
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])
        self.assertIsNone(current['response'])
        if post_await:
            self.assertEqual(current['state'], 'held')
            self.assertTrue(current['hold_reason'])
        return current

    def later_traps(self):
        stack = ExitStack()
        attempt, event, one = self.store.attempt, self.store.event, self.store.one
        consumer = self.store.one("SELECT active_attempt FROM jobs WHERE task='reviews-integrator'")['active_attempt']
        def read_attempt(key, *args, **kwargs):
            if key == consumer:
                raise AssertionError('later consumer attempt/result/detail acquired before refusal')
            return attempt(key, *args, **kwargs)
        def read_event(key):
            if key in (self.e['id'], self.returned['id']):
                raise AssertionError('native Source/return body acquired before refusal')
            return event(key)
        def read_one(sql, args=()):
            if 'review_calls' in sql.lower():
                raise AssertionError('native receipt/answer acquired before refusal')
            return one(sql, args)
        stack.enter_context(patch.object(self.store, 'attempt', side_effect=read_attempt))
        stack.enter_context(patch.object(self.store, 'event', side_effect=read_event))
        stack.enter_context(patch.object(self.store, 'one', side_effect=read_one))
        return stack

    def assert_ticks_held(self, job):
        before = self.store.one('SELECT result,detail,collected FROM attempts WHERE id=?', (job['active_attempt'],))
        with self.later_traps():
            for dispatcher in (self.dispatch, processing.ProcessingDispatcher(self.store, self.models, self.boards)):
                dispatcher.reconcile_completed()
                self.assertIn('physical admission', dispatcher.runtime_errors[job['id']])
            self.assertIsNone(self.store.job(job['id'])['response'])
        self.assertEqual(before, self.store.one('SELECT result,detail,collected FROM attempts WHERE id=?', (job['active_attempt'],)))

    def test_periodic_orphan_after_original_collection(self):
        job = self.collected()
        self.conflict()
        self.assert_ticks_held(job)

    def test_post_await_refusal_next_tick_stays_before_body(self):
        job = self.collected(post_await=True)
        self.assert_ticks_held(job)
        # A recorded job hold independently prevents later acquisition.
        self.store.db.execute('DELETE FROM ordinary_resources')
        with self.later_traps():
            self.dispatch.reconcile_completed()
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_direct_finish_and_awaiting_acceptance(self):
        job = self.collected()
        self.conflict()
        with self.later_traps():
            with self.assertRaises(Refusal):
                self.store.finish_job(job['id'], job['token'])
            with self.assertRaises(Refusal):
                ordinary.awaiting_acceptance(self.store, job)
        self.assertFalse(self.store.db.in_transaction)

    def test_admitted_later_reads_join_transaction(self):
        job = self.collected()
        with self.store.tx():
            self.assertFalse(ordinary.awaiting_acceptance(self.store, job))
            self.assertTrue(self.store.db.in_transaction)
        self.store.finish_job(job['id'], job['token'])
        self.assertIsNotNone(self.store.job(job['id'])['response'])


class Amendment847(CompositeAmendment):
    def test_actual_composite_cli_all_changed_modules(self):
        self.assertEqual(len(self.delta), 15)
        self.assertIn('ordinary.py', self.delta)
        self.assertTrue(set(self.delta) <= report_repair.AMEND_MODULES)
        self.test_real_cli_basis_external_safe5_work_collection_and_selection()
