"""Synthetic current Source; physical refusal must precede protected acquisition."""
import asyncio
from contextlib import ExitStack
from unittest.mock import patch
from test_native_return820 import NativeReturn
from coordinator_runtime import resource_scopes, report_scope, native_review_scope, reviews
from coordinator_runtime.contracts import Refusal


class Preflight(NativeReturn):
    def check_physical_traps(self):
        # Establish a genuinely eligible, fully collected synthetic Source first.
        with patch.object(resource_scopes, 'overlaps', return_value=False):
            self.assertFalse(resource_scopes.blocked(self.store, self.row))
        asyncio.run(self.phase('schedule_classifications'))
        self.assertIsNotNone(self.store.one("SELECT event FROM queue WHERE task='reviews-integrator' AND state='queued'"))
        original_event, original_attempt, original_one = self.store.event, self.store.attempt, self.store.one
        def event(key):
            if key in (self.e['id'], self.returned['id']):
                raise AssertionError('protected Source/return body acquired before physical refusal')
            return original_event(key)
        def attempt(key, *args, **kwargs):
            if key == self.a['id']:
                raise AssertionError('protected native attempt/result acquired before physical refusal')
            return original_attempt(key, *args, **kwargs)
        def one(sql, args=()):
            if 'review_calls' in sql.lower():
                raise AssertionError('protected native packet/receipt/answer acquired before physical refusal')
            return original_one(sql, args)
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.store, 'event', side_effect=event))
            stack.enter_context(patch.object(self.store, 'attempt', side_effect=attempt))
            stack.enter_context(patch.object(self.store, 'one', side_effect=one))
            stack.enter_context(patch.object(reviews, 'collected_proof', side_effect=AssertionError('native proof acquired')))
            self.install_conflict()
            self.assertTrue(resource_scopes.blocked(self.store, self.row))
            for acquire in (lambda: report_scope.integration_inputs(self.store, self.row),
                            lambda: report_scope.bounded_members(self.store, self.row, [self.row]),
                            lambda: native_review_scope.eligible(self.store, self.row, self.record)):
                with self.assertRaises(Refusal):
                    acquire()
            self.assertIsNone(self.store.reserve())
            self.dispatch.schedule_job()
            self.assertFalse(self.dispatch.active)

    def test_orphan_lease_refuses_before_all_protected_reads(self):
        self.source()
        self.install_conflict = lambda: self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped-resource','orphan-attempt')")
        self.check_physical_traps()

    def test_mapped_root_refuses_before_all_protected_reads(self):
        # The selected relevant root overlaps the authentic consumer read map.
        self.resource_conflict = True
        self.source()
        self.install_conflict = lambda: None
        self.check_physical_traps()

    def test_native_singleton_transport_boundary(self):
        self.source()
        incoming = report_scope.integration_inputs(self.store, self.row)
        # Find the exact encoded custody + full selected analysis allowance.
        with patch.object(report_scope, 'transport_limit', return_value=0):
            self.assertFalse(report_scope.fits_return(self.store, incoming, transport=True))
        low, high = 0, 1 << 26
        while low < high:
            middle = (low + high) // 2
            with patch.object(report_scope, 'transport_limit', return_value=middle):
                fits = report_scope.fits_return(self.store, incoming, transport=True)
            if fits: high = middle
            else: low = middle + 1
        with patch.object(report_scope, 'transport_limit', return_value=low):
            self.assertEqual(report_scope.bounded_members(self.store, self.row, [self.row]), [self.row])
        with patch.object(report_scope, 'transport_limit', return_value=low - 1):
            with self.assertRaisesRegex(Refusal, 'analysis headroom'):
                report_scope.bounded_members(self.store, self.row, [self.row])
