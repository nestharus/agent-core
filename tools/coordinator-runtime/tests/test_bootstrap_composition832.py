"""Composite production paths; identities, model answers and native wire are fiction."""
import asyncio
import json
from unittest.mock import patch
from test_native_return820 import NativeReturn
from test_source_amendment822 import OutsideReview
from coordinator_runtime import local_integration as local, report_repair, native_review_scope


class NativeToWork(NativeReturn):
    def configure_fixture(self):
        super().configure_fixture()
        for task in ('reviews-integrator','work-proposer'):
            self.config['local_integration']['tasks'][task].update(points=['a'], lookup_scopes=[])
        work = self.config['tasks']['work-proposer']
        workdir = self.area/'work-reader'
        workdir.mkdir()
        work['cwd'] = str(workdir)
        work['effect_authority']['read_roots'] = [str(self.catalog),str(self.method)]

    def test_native_whole_integrator_return_maps_real_work_point(self):
        self.mapping_readonly = True
        self.test_whole_native_return_and_real_integrator_transport()
        job = self.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        event = self.store.event(job['response'])
        original = {t:self.store.rows('SELECT * FROM '+t) for t in
                    ('events','attempts','results','processing_source_positions','review_calls')}
        observed = local.packet(self.store, dict(event=event['id'],task='work-proposer',package='pkg'))
        self.assertEqual(observed['reads'], ['a'])
        for table, rows in original.items():
            self.assertEqual(rows, self.store.rows('SELECT * FROM '+table), table)
        # Continue through the real delegated mapping and Work task collection.
        self.mapping_readonly = True
        self.initial[event['id']] = 'work-proposer'
        def traced(function):
            def invoke(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except Exception as exc:
                    print('NATIVE_WORK_DIAGNOSTIC', function.__name__, str(exc), flush=True)
                    raise
            return invoke
        with patch.object(native_review_scope,'preflight',traced(native_review_scope.preflight)), \
             patch.object(native_review_scope,'_authenticate',traced(native_review_scope._authenticate)):
            asyncio.run(self.until(lambda:self.store.one("SELECT j.id FROM jobs j JOIN attempts a "
                "ON a.id=j.active_attempt WHERE j.task='work-proposer' AND a.collected IS NOT NULL"), n=4))
        work = self.store.one("SELECT * FROM jobs WHERE task='work-proposer'")
        call = next(c for c in self.models.calls if c['attempt']==work['active_attempt'])
        self.assertIn('QA472-FULL-NATIVE-REPORT', call['prompt'])
        self.assertEqual(len(self.transport.calls), 2)


class CompositeAmendment(OutsideReview):
    def setUp(self):
        super().setUp()
        self.delta = sorted(k for k in self.original_impl.keys() | self.candidate_impl.keys()
                            if self.original_impl.get(k) != self.candidate_impl.get(k))

    def test_actual_composite_cli_all_changed_modules(self):
        self.assertIn('resource_scopes.py', self.delta)
        self.assertTrue({'plain_control.py','native_review_scope.py'} <= set(self.delta))
        self.assertTrue(set(self.delta) <= report_repair.AMEND_MODULES)
        self.test_real_cli_basis_external_safe5_work_collection_and_selection()
