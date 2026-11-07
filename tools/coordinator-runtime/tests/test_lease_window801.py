"""Final-tree lease body-boundary regressions; all actor/clock/wire data synthetic."""
import copy
from unittest.mock import patch
from test_control_window798 import Window798
from coordinator_runtime import processing, report_repair as repair, report_scope
from coordinator_runtime.contracts import Refusal

class LeaseWindow801(Window798):
    def test_effective_lease_expires_between_body_groups(self):
        request=self.request794();actual=self.store.event;actual_attempt=self.store.attempt;reads=[]
        def event(identity):
            reads.append(identity)
            if identity==self.control_event:raise AssertionError('expired control event body')
            value=actual(identity)
            return value
        def attempt(identity):
            if identity==self.control_attempt:raise AssertionError('expired control result body')
            return actual_attempt(identity)
        checked=report_scope.execution_report
        def report_checked(*args,**kwargs):
            value=checked(*args,**kwargs);self.store.clock=lambda:1600.;return value
        before=self.snapshot794()
        with patch.object(report_scope,'execution_report',side_effect=report_checked),patch.object(self.store,'event',side_effect=event),patch.object(self.store,'attempt',side_effect=attempt),self.assertRaisesRegex(Refusal,'lease plan exhausted'):
            self.apply794(request)
        self.assertEqual(before,self.snapshot794());self.assertNotIn(self.control_event,reads)

    def test_plan_clock_and_issuer_guards_before_body(self):
        for change in [dict(lease_seconds=0),dict(until=float('inf')),dict(max_starts=40),dict(max_new_inputs=1),dict(max_windows=0),dict(pause_bytes=1),{'from':900.},dict(until=999.)]:
            plan={**self.lease_plan801(),**change};before=self.snapshot794()
            from test_qa629_repairs import actor
            from coordinator_runtime import configuration
            with actor(self.boards['Work'].store,self.issuer),configuration.stopped(self.store),self.store.tx(),patch.object(self.store,'event',side_effect=AssertionError('invalid plan body')),self.assertRaises(Refusal):
                repair.lease_basis(self.store,self.boards,self.cap,self.work_event,self.control_event,self.controller,self.issuer,self.modules,'Invalid plan qualification',plan)
            self.assertEqual(before,self.snapshot794())
