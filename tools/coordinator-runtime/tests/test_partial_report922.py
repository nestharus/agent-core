"""Finite automatic PARTIAL report admission; every actor/native receipt is fiction.

The optional released answer is data, never recovery or replay of its old attempt.
All journals, grants, catalogs, resources and methods belong to fresh fixtures.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from _receiving485_fixtures import Models
from test_source_report897 import SourceReport897, startup_return
from test_unpackaged_native889 import Unpackaged889
from coordinator_runtime import native_review_scope as scope, report_scope, resource_scopes
from coordinator_runtime.contracts import Refusal, digest, encode


class PartialReport922(unittest.TestCase):
    def setUp(self):
        class Case(Unpackaged889):
            def configure_selection(self, selected):
                super().configure_selection(selected)
                selected['service']['report_tasks'] = ['reviews-integrator']
                selected['service']['legacy_resources']['Reviews']['native_review_return']['version'] = getattr(self, 'report_version', scope.PARTIAL_REPORT)
        self.f = Case(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    source = SourceReport897.source

    def assert_flow(self):
        f = self.f
        self.assertIsNone(f.a['error'], f.a['error'])
        self.assertEqual(f.a['semantic'], 'PARTIAL')
        self.assertEqual(f.original['state'], 'held')
        self.assertEqual(f.original['hold_reason'], scope.SOURCE_REPORT_HOLD)
        before = {table: f.store.rows('SELECT * FROM '+table) for table in
                  ('review_calls', 'review_contexts', 'review_history_commits', 'review_report_returns', 'enrollments')}
        original = f.store.job(f.original['id'])
        attempt = f.store.attempt(f.a['id'])
        selection = copy.deepcopy(f.store.processing.current())
        self.assertFalse(resource_scopes.blocked(f.store, f.row))
        reports = report_scope.integration_inputs(f.store, f.row)
        self.assertEqual(reports[0]['original'], f.returned['body'])
        self.assertEqual(f.returned['body']['full_original_call']['answer'], self.raw)
        self.assertEqual(json.loads(self.raw)['coverage']['observations'], [])
        self.assertEqual(set(json.loads(self.raw)['coverage']['families'].values()), {'unread'})

        def answer(job, out):
            if job['task'] == 'reviews-integrator':
                incoming = report_scope.integration_inputs(f.store, job)
                protocol = report_scope.integration_protocol(f.store, job, incoming)
                out['category'] = 'consolidated'
                out['findings'] = [dict(**protocol, analysis='Preserve all unread duties and dissent',
                    decision='Consolidation only; Source remains incomplete', method='Fictional fixture',
                    coverage=[dict(**pin, extent='whole', limits=['No Source approval']) for pin in protocol['sources']])]
        f.task_result = answer
        f.mapping_readonly = True
        f.models = Models(f)
        f.dispatch.models = f.models
        asyncio.run(f.until(lambda: f.store.one(
            "SELECT id FROM jobs WHERE task='reviews-integrator' AND response IS NOT NULL"), n=18))
        consumer = f.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        response = f.store.event(consumer['response'])
        self.assertEqual(response['report_custody']['collected_reports'], reports)
        self.assertEqual(response['body']['semantic'], 'DONE')  # Only the integrator's own job.
        self.assertEqual(f.store.job(original['id']), original)
        self.assertEqual(f.store.attempt(attempt['id']), attempt)
        for table, rows in before.items():
            self.assertEqual(f.store.rows('SELECT * FROM '+table), rows)
        cap, selected = f.store.processing.current()
        self.assertEqual(selected, selection[1])
        self.assertEqual({k: v for k, v in cap.items() if k != 'starts'},
                         {k: v for k, v in selection[0].items() if k != 'starts'})
        self.assertGreater(cap['starts'], selection[0]['starts'])
        self.assertTrue(f.record['unbounded'])
        self.assertEqual(len(f.transport.calls), 1)
        self.assertIsNone(consumer['package'])
        self.assertEqual(f.store.rows('SELECT * FROM admissions'), [])
        self.assertEqual(f.store.rows('SELECT * FROM processing_admissions'), [])

    def test_structured_partial_automatic_whole_integration_retains_unbounded_hold(self):
        self.source()
        self.assert_flow()

    @unittest.skipUnless(os.environ.get('SOURCE897_RELEASED_FAILURE'), 'released answer data not selected')
    def test_exact_released_partial_automatic_integration(self):
        released = json.loads(Path(os.environ['SOURCE897_RELEASED_FAILURE']).read_text())
        self.source(raw=released['original_review_calls'][0]['full_answer'])
        self.assert_flow()

    def test_completed_policy_still_refuses_same_partial(self):
        self.f.report_version = 'native-collected-review-v1'
        self.source()
        f = self.f
        self.assertTrue(resource_scopes.blocked(f.store, f.row))
        with self.assertRaises(Refusal):
            scope.eligible(f.store, f.row, f.record)
        self.assertTrue(f.record['unbounded'])

    @unittest.skipUnless(os.environ.get('SOURCE897_RELEASED_FAILURE'), 'released answer data not selected')
    def test_completed_policy_refuses_exact_released_partial(self):
        self.f.report_version = 'native-collected-review-v1'
        released = json.loads(Path(os.environ['SOURCE897_RELEASED_FAILURE']).read_text())
        self.source(raw=released['original_review_calls'][0]['full_answer'])
        self.assertEqual(self.f.a['semantic'], 'PARTIAL')
        self.assertTrue(resource_scopes.blocked(self.f.store, self.f.row))

    def test_partial_variant_does_not_replace_completed_native_policy(self):
        self.f.source()  # Existing two-turn DONE fixture, without the PARTIAL seam.
        self.assertEqual(self.f.a['semantic'], 'DONE')
        self.assertEqual(self.f.store.rows('SELECT * FROM review_report_returns'), [])
        self.assertTrue(resource_scopes.blocked(self.f.store, self.f.row))

    def test_explicit_null_and_sole_route_cannot_expand_admission(self):
        self.source()
        f = self.f
        cap, selected = f.store.processing.current()
        for mutate in [lambda p: p.pop('package'), lambda p: p.update(package=''),
                       lambda p: p.update(task='qa-execution')]:
            changed = copy.deepcopy(f.record)
            mutate(changed['native_review_return'])
            with self.assertRaises(Refusal):
                scope.validate(f.store, 'Reviews', changed, selected)
        for tasks in ([], ['reviews-integrator', 'work-integrator'], ['work-integrator']):
            changed = copy.deepcopy(selected)
            changed['service']['report_tasks'] = tasks
            record = changed['service']['legacy_resources']['Reviews']
            with patch.object(f.store.processing, 'current', return_value=(cap, changed)), \
                 patch.object(f.store, 'event', side_effect=AssertionError('pre-admission body')):
                self.assertTrue(resource_scopes.blocked(f.store, f.row))
        # The existing software admission and Work coordination selectors still
        # reject attempts to turn explicit-null report authority into execution.
        from coordinator_runtime import processing_admission
        changed = copy.deepcopy(selected)
        changed['software_admission'] = dict(authority='Fictional forbidden expansion', max_packages=1,
            scopes={'fictional-forbidden': dict(submitters=[f.config['roles']['Work']['owner']],
                package_prefix='fictional-', evidence='No execution grant', task_scopes={'reviews-proposer': {}})})
        with self.assertRaises(Refusal):
            processing_admission.validate(f.store, changed)
        changed['work_coordination']['tasks'] = ['reviews-integrator']
        with self.assertRaises(Refusal):
            processing_admission.validate_coordination(f.store, changed)

    def test_bound_consumer_members_and_current_rights_refuse_before_body(self):
        self.source()
        self.assert_flow()
        f = self.f
        consumer = f.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        members = json.loads(consumer['members'])
        faults = [
            ("UPDATE jobs SET members=? WHERE id=?", (encode(members+members), consumer['id'])),
            ("UPDATE jobs SET hold_reason='held' WHERE id=?", (consumer['id'],)),
            ("UPDATE jobs SET package='foreign' WHERE id=?", (consumer['id'],)),
            ("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','foreign') WHERE id=?", (consumer['active_attempt'],)),
            ("UPDATE prospective_authorities SET revoked=1", ()),
            ("UPDATE enrollments SET grant_id='foreign' WHERE role='Reviews'", ()),
        ]
        for sql, args in faults:
            with self.subTest(sql=sql):
                f.store.db.execute('SAVEPOINT consumer922')
                try:
                    f.store.db.execute(sql, args)
                    with patch.object(f.store, 'event', side_effect=AssertionError('pre-admission event read')), \
                         patch.object(f.store, 'attempt', side_effect=AssertionError('pre-admission attempt read')):
                        self.assertTrue(resource_scopes.blocked(f.store, f.store.job(consumer['id'])))
                finally:
                    f.store.db.execute('ROLLBACK TO consumer922')
                    f.store.db.execute('RELEASE consumer922')

    def test_metadata_faults_refuse_before_protected_reads(self):
        self.source()
        f = self.f
        faults = [
            ("UPDATE attempts SET collected=NULL WHERE id=?", (f.a['id'],)),
            ("UPDATE attempts SET ended=NULL WHERE id=?", (f.a['id'],)),
            ("UPDATE attempts SET capture='incomplete' WHERE id=?", (f.a['id'],)),
            ("UPDATE attempts SET exit=1 WHERE id=?", (f.a['id'],)),
            ("UPDATE attempts SET controller='foreign' WHERE id=?", (f.a['id'],)),
            ("UPDATE attempts SET detail=json_remove(detail,'$.software_authority.prospective_epoch') WHERE id=?", (f.a['id'],)),
            ("UPDATE jobs SET hold_reason='unrelated hold' WHERE id=?", (f.original['id'],)),
            ("UPDATE jobs SET effects='UNKNOWN' WHERE id=?", (f.original['id'],)),
            ("UPDATE jobs SET package='foreign' WHERE id=?", (f.original['id'],)),
            ("UPDATE jobs SET task='branch-proposer' WHERE id=?", (f.original['id'],)),
            ("UPDATE events SET hold='held' WHERE id=?", (f.e['id'],)),
            ("UPDATE events SET hold='held' WHERE id=?", (f.returned['id'],)),
            ("UPDATE events SET hash='changed' WHERE id=?", (f.returned['id'],)),
            ("UPDATE processing_source_positions SET position=0 WHERE event=?", (f.returned['id'],)),
            ("DELETE FROM review_report_returns WHERE attempt=?", (f.a['id'],)),
            ("UPDATE events SET payload=json_remove(payload,'$.source_job') WHERE id=?", (f.returned['id'],)),
            ("UPDATE events SET payload=json_set(payload,'$.source_attempt','forged') WHERE id=?", (f.returned['id'],)),
        ]
        for sql, args in faults:
            with self.subTest(sql=sql), f.store.tx():
                f.store.db.execute('SAVEPOINT negative922')
                try:
                    f.store.db.execute(sql, args)
                    with patch.object(f.store, 'event', side_effect=AssertionError('pre-admission event read')), \
                         patch.object(f.store, 'attempt', side_effect=AssertionError('pre-admission attempt read')):
                        self.assertTrue(resource_scopes.blocked(f.store, f.row))
                finally:
                    f.store.db.execute('ROLLBACK TO negative922')
                    f.store.db.execute('RELEASE negative922')

    def test_current_selection_pins_and_rights_refuse(self):
        self.source()
        f = self.f
        cap, selected = f.store.processing.current()
        for field, value in [('version', 'partial'), ('expires', 0), ('package', 'foreign'),
                ('source_task_sha256', '0'*64), ('task_sha256', '0'*64), ('grant', 'foreign'),
                ('component', 'foreign'), ('review_policy_sha256', '0'*64), ('packet_sha256', '0'*64)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(selected)
                record = changed['service']['legacy_resources']['Reviews']
                record['native_review_return'][field] = value
                with patch.object(f.store.processing, 'current', return_value=(cap, changed)):
                    self.assertTrue(resource_scopes.blocked(f.store, f.row))
        changed_cap = dict(cap, issuer='foreign')
        with patch.object(f.store.processing, 'current', return_value=(changed_cap, selected)), \
             patch.object(f.store, 'event', side_effect=AssertionError('pre-admission body')):
            self.assertTrue(resource_scopes.blocked(f.store, f.row))
        for row in [dict(f.row, package='foreign'), dict(f.row, task='work-integrator')]:
            with self.assertRaises(Refusal):
                scope.preflight(f.store, row, f.record)

    def test_original_proof_mutations_refuse(self):
        self.source()
        f = self.f
        faults = [
            ("UPDATE review_contexts SET state='interrupted'", ()),
            ("UPDATE review_contexts SET history_hash='changed'", ()),
            ("UPDATE review_history_commits SET state='pending'", ()),
            ("UPDATE review_calls SET state='launch-intent'", ()),
            ("UPDATE review_calls SET receipt=json_set(receipt,'$[0].receipt.transport.attached.run','foreign')", ()),
            ("UPDATE review_calls SET receipt=json_set(receipt,'$[0].receipt.transport.attached.backlog_dropped_total',1)", ()),
            ("UPDATE review_report_returns SET binding='{}'", ()),
            ("UPDATE events SET payload=json_set(payload,'$.body.status','DONE') WHERE id=?", (f.returned['id'],)),
            ("UPDATE events SET payload=json_set(payload,'$.body.full_original_outcome.result.semantic','DONE') WHERE id=?", (f.returned['id'],)),
        ]
        for sql, args in faults:
            with self.subTest(sql=sql):
                f.store.db.execute('SAVEPOINT proof922')
                try:
                    f.store.db.execute(sql, args)
                    self.assertTrue(resource_scopes.blocked(f.store, f.row))
                finally:
                    f.store.db.execute('ROLLBACK TO proof922')
                    f.store.db.execute('RELEASE proof922')

    def test_orphan_lease_refuses_before_all_protected_reads(self):
        self.source()
        self.f.install_conflict = lambda: self.f.store.db.execute(
            "INSERT INTO ordinary_resources VALUES('opaque-orphan','foreign-attempt')")
        self.f.check_physical_traps()

    def test_actual_physical_overlap_refuses_before_all_protected_reads(self):
        self.f.resource_conflict = True
        self.source()
        self.f.install_conflict = lambda: None
        self.f.check_physical_traps()


if __name__ == '__main__':
    unittest.main()
