"""Work-selected explicit-null Source; native transport and principals are fiction.

Production validation, preflight, authentication, custody and consolidation run.
No provider, live state, native efficacy, acceptance or old-history credit.
"""
import copy
from unittest.mock import patch

from _receiving485_fixtures import FictionalNativeTransport, NativeModels
from test_native_preflight826 import Preflight
from coordinator_runtime import native_review_scope, processing_admission, report_scope, service
from coordinator_runtime.contracts import Refusal, digest, encode


class Unpackaged889(Preflight):
    component889 = 'synthetic-maker889-source-component'

    def configure_fixture(self):
        super().configure_fixture()
        # This fixture selects the existing native unpackaged task path. It
        # does not grant a package-scoped task an exemption from scoped_task.
        self.config['tasks']['reviews-proposer']['require_package_scope'] = False

    def packet889(self):
        return dict(component=self.component889,
                    origin='https://example.invalid/fictional.git',
                    base=self.head, head=self.head, previous=None, answered_ids=[])

    def configure_selection(self, selected):
        super().configure_selection(selected)
        policy = selected['service']['reviews']['reviews-proposer']
        policy['components'][self.component889] = policy['components'].pop('component')
        policy['components'][self.component889]['history'] = str(
            self.store.home / 'review-history' / (self.component889 + '.md'))
        selection = selected['service']['legacy_resources']['Reviews']['native_review_return']
        selection.update(package=None, component=self.component889,
                         packet_sha256=digest(self.packet889()),
                         review_policy_sha256=digest(policy))

    def init_native(self, bound=False):
        # No software admission, branch association, owner impersonation or
        # manufactured ancestry for this genuine synthetic Source job.
        self.start_auto()
        self.transport = FictionalNativeTransport()
        self.models = NativeModels(self)
        self.dispatch = service.Dispatcher(self.store, self.boards, self.models, self.transport)

    def source_event(self, bound=False):
        return self.post(encode(dict(review=self.packet889())), 'Reviews',
                         topic='synthetic-maker889-unpackaged-source')

    def source(self):
        returned = super().source()
        self.row['package'] = None
        self.assertIsNone(self.e['package'])
        self.assertEqual(set(self.e['body']), {'review'})
        self.assertEqual(set(self.e['body']['review']),
                         {'component', 'origin', 'base', 'head', 'previous', 'answered_ids'})
        self.assertIsNone(self.original['package'])
        self.assertIsNone(returned['package'])
        self.assertEqual(self.store.rows('SELECT * FROM admissions'), [])
        self.assertEqual(self.store.rows('SELECT * FROM processing_admissions'), [])
        self.assertEqual(self.store.rows('SELECT * FROM branch_associations'), [])
        return returned

    def test_explicit_null_real_source_consolidation(self):
        self.test_whole_native_return_and_real_integrator_transport()
        consumer = self.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        self.assertIsNone(consumer['package'])
        self.assertEqual(self.store.rows('SELECT * FROM admissions'), [])
        self.assertEqual(self.store.rows('SELECT * FROM processing_admissions'), [])
        self.assertEqual(self.record['native_review_return']['component'], self.component889)
        self.assertEqual(native_review_scope.preflight(self.store, self.row, self.record), [])
        self.assertEqual(native_review_scope.eligible(self.store, self.row, self.record), [])

    def test_null_is_explicit_and_blank_is_refused(self):
        self.source()
        native_review_scope.validate(self.store, 'Reviews', self.record)
        for value in ('', '   ', False, 0, [], {}):
            with self.subTest(package=value):
                changed = copy.deepcopy(self.record)
                changed['native_review_return']['package'] = value
                with self.assertRaises(Refusal):
                    native_review_scope.validate(self.store, 'Reviews', changed)
        changed = copy.deepcopy(self.record)
        del changed['native_review_return']['package']
        with self.assertRaises(Refusal):
            native_review_scope.validate(self.store, 'Reviews', changed)

    def test_wrong_nonnull_consumer_refuses_before_body(self):
        self.source()
        with patch.object(self.store, 'event', side_effect=AssertionError('protected body read')):
            with self.assertRaisesRegex(Refusal, 'same-case'):
                native_review_scope.preflight(self.store, dict(self.row, package='synthetic-maker889-other'), self.record)

    def test_wrong_nonnull_selection_refuses(self):
        self.source()
        selected = copy.deepcopy(self.store.processing.current()[1])
        record = selected['service']['legacy_resources']['Reviews']
        record['native_review_return']['package'] = 'synthetic-maker889-other'
        # Valid nonempty selection still requires an exactly matching consumer.
        native_review_scope.validate(self.store, 'Reviews', record, selected)
        with patch.object(self.store.processing, 'current', return_value=(self.store.processing.current()[0], selected)):
            with self.assertRaisesRegex(Refusal, 'same-case'):
                native_review_scope.preflight(self.store, self.row, record)

    def test_original_source_identity_and_epoch_refuse(self):
        self.source()
        faults = [
            ("UPDATE jobs SET package='synthetic-maker889-other' WHERE id=?", (self.original['id'],)),
            ("UPDATE jobs SET task='branch-proposer' WHERE id=?", (self.original['id'],)),
            ("UPDATE processing_source_positions SET position=0 WHERE event=?", (self.e['id'],)),
            ("UPDATE attempts SET detail=json_remove(detail,'$.software_authority.prospective_epoch') WHERE id=?", (self.a['id'],)),
        ]
        for sql, args in faults:
            with self.subTest(sql=sql):
                self.store.db.execute('SAVEPOINT maker889')
                try:
                    self.store.db.execute(sql, args)
                    with self.assertRaises(Refusal):
                        native_review_scope.preflight(self.store, self.row, self.record)
                finally:
                    self.store.db.execute('ROLLBACK TO maker889')
                    self.store.db.execute('RELEASE maker889')

    def test_original_source_and_consumer_unchanged_proof(self):
        self.test_explicit_null_real_source_consolidation()
        for event in (self.e, self.returned):
            self.store.db.execute('SAVEPOINT maker889')
            try:
                self.store.db.execute("UPDATE events SET payload=json_set(payload,'$.package','synthetic-maker889-other') WHERE id=?", (event['id'],))
                with self.assertRaises(Refusal):
                    native_review_scope.eligible(self.store, self.row, self.record)
            finally:
                self.store.db.execute('ROLLBACK TO maker889')
                self.store.db.execute('RELEASE maker889')
        row = self.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        attempt = row['active_attempt']
        # Recheck the actual fully bound consumer after production collection;
        # every subsequent acquisition still requires its original authority.
        native_review_scope.preflight(self.store, row, self.record)
        for sql, args in [
            ("UPDATE jobs SET package='synthetic-maker889-other' WHERE id=?", (row['id'],)),
            ("UPDATE jobs SET hold_reason='synthetic-maker889-hold' WHERE id=?", (row['id'],)),
            ("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','synthetic-maker889-forged') WHERE id=?", (attempt,)),
        ]:
            self.store.db.execute('SAVEPOINT maker889')
            try:
                self.store.db.execute(sql, args)
                with self.assertRaises(Refusal):
                    native_review_scope.preflight(self.store, self.store.job(row['id']), self.record)
            finally:
                self.store.db.execute('ROLLBACK TO maker889')
                self.store.db.execute('RELEASE maker889')

    def test_unrelated_admissions_and_original_holds_conserved(self):
        self.source()
        self.store.admit('synthetic-maker889-independent-qa', self.config['roles']['Branch']['owner'],
                         {'task_scopes': {}, 'resource_evidence': 'Independent synthetic QA/Branch; no Source authority'})
        admissions = self.store.rows('SELECT * FROM admissions')
        roles = self.store.rows('SELECT * FROM enrollments ORDER BY role')
        original_attempt = self.store.attempt(self.a['id'])
        selected = copy.deepcopy(self.store.processing.current()[1])
        self.assertEqual(native_review_scope.eligible(self.store, self.row, self.record), [])
        report_scope.integration_inputs(self.store, self.row)
        self.assertEqual(self.store.rows('SELECT * FROM admissions'), admissions)
        self.assertEqual(self.store.rows('SELECT * FROM processing_admissions'), [])
        self.assertEqual(self.store.rows('SELECT * FROM enrollments ORDER BY role'), roles)
        self.assertEqual(self.store.attempt(self.a['id']), original_attempt)
        self.assertEqual(self.store.processing.current()[1], selected)
        self.assertTrue(self.record['unbounded'])

    def test_exact_method_task_grant_component_and_packet_pins(self):
        self.source()
        cap, selected = self.store.processing.current()
        for field, value in [('source_task_sha256', '0'*64), ('task_sha256', '0'*64),
                             ('review_policy_sha256', '0'*64), ('grant', 'synthetic-maker889-forged'),
                             ('component', 'synthetic-maker889-other'), ('packet_sha256', '0'*64)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(selected)
                record = changed['service']['legacy_resources']['Reviews']
                record['native_review_return'][field] = value
                with patch.object(self.store.processing, 'current', return_value=(cap, changed)):
                    with self.assertRaises(Refusal):
                        native_review_scope.eligible(self.store, self.row, record)

    def test_null_selection_does_not_expand_software_admission(self):
        self.source()
        selection = copy.deepcopy(self.store.processing.current()[1])
        selection['software_admission'] = dict(authority='Synthetic Work maker889', max_packages=1,
            scopes={'synthetic-maker889-forbidden': dict(submitters=[self.config['roles']['Work']['owner']],
                package_prefix='synthetic-maker889-', evidence='Synthetic scope rejection',
                task_scopes={'reviews-proposer': {}})})
        with self.assertRaisesRegex(Refusal, 'Branch/QA'):
            processing_admission.validate(self.store, selection)
        selection['work_coordination']['tasks'] = ['reviews-integrator']
        with self.assertRaisesRegex(Refusal, 'Work tasks'):
            processing_admission.validate_coordination(self.store, selection)
        from coordinator_runtime.contracts import scoped_task
        scoped = dict(self.config['tasks']['reviews-proposer'], require_package_scope=True)
        with self.assertRaisesRegex(Refusal, 'task scope'):
            scoped_task('reviews-proposer', scoped, None)
