"""Stopped-before-launch recovery in newly owned, retained software fiction.

Real Board grants/revocation, processing selection/admission, Store transactions
and Dispatcher selection/collection are exercised. Only SDK caller identity,
service lifecycle/parent testimony and model answers are synthetic. No socket,
provider, native session, ordinary QA procedure or external state is accessed.
"""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from unittest.mock import AsyncMock, patch

from test_qa629_repairs import Fixture, actor
from coordinator_runtime import processing, processing_admission
from coordinator_runtime.contracts import Refusal, encode, ident
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.store import Store


class TypedClassifier:
    def __init__(self, case, *, invalid=False):
        self.case, self.invalid, self.calls = case, invalid, []

    async def run(self, store, attempt, prompt, spec, schema):
        self.calls.append((attempt, prompt, copy.deepcopy(spec)))
        store.begin(attempt, {'fictional_typed_answer': True})
        # No fake session/native identity: this is a typed-return seam only.
        return dict(exit=0, capture='complete', cleanup='fictional-no-child',
            result={} if self.invalid else dict(event_id=self.case.message['id'],
                task='qa-execution', package='recovery703-one', reason='Exact admitted fictional QA source'))


class PrelaunchRecovery(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bootstrap(self.configure)
        self._asyncioRunner.get_loop().set_debug(False)
        # Real stopped enrollment and grant revocation in the isolated Board.
        for role, board in self.boards.items():
            with actor(board.store, self.config['roles']['Work']['owner']):
                board.revoke_software(self.store, self.store.enrollment(role)['grant_id'])
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?', (role,))
        self.store.db.execute("UPDATE enrollments SET legacy_hold='original QA global UNKNOWN' WHERE role='QA'")
        self.boards = {r: processing.ProcessingBoard(self.config, r) for r in self.config['roles']}
        for board in self.boards.values():
            board.runtime = self.store
        scope = dict(submitters=[self.source_sender], package_prefix='recovery703-',
            task_scopes={'qa-execution': self.scope}, evidence='Fictional Work exact QA procedure scope')
        self.selection = dict(basis=processing.basis(self.store, self.boards),
            authority='Fictional actual Work continuing software authority', retained_events=[],
            recover_controls={}, future_intake=True, tasks=list(self.config['tasks']),
            max_shared_rows=1000, max_shared_payload_bytes=1000000, max_runtime_rows=1000,
            software_admission=dict(authority='Typed future QA package selection', max_packages=2,
                scopes={'recovery703': scope}),
            service=dict(max_inflight=3, reviews={}, legacy_resources={'QA': dict(
                original_hold='original QA global UNKNOWN', roots=[], unbounded=True,
                evidence='Original global effect unknown retained; classification grants no QA execution')}))
        with actor(self.boards['Work'].store, self.config['roles']['Work']['owner']):
            self.cap = processing.select(self.store, self.boards, self.selection)['capability']
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        self.service_record(self.store)
        self.model = TypedClassifier(self)
        self.runtime = Dispatcher(self.store, models=self.model, boards=self.boards)
        self.message = self.source()
        processing_admission.admit(self.store, self.message['id'])
        self.admission = self.store.one('SELECT * FROM admissions WHERE package=?', ('recovery703-one',))
        self.resolution = self.store.one('SELECT * FROM processing_admission_resolutions WHERE event=?', (self.message['id'],))
        self.original, actual = self.store.claim_classification()
        self.assertEqual(actual['id'], self.message['id'])
        # Stop wins between reservation and launch. Dispatcher, not a row edit,
        # establishes the known-not-started proof and failed classification.
        if self._testMethodName in {'test_collected_failure_keeps_diagnosis',
                                   'test_diagnosis_preparation_rechecks_before_prior_result724'}:
            self.store.begin(self.original, {'fictional_executed_classifier': True})
            self.store.collect(self.original, dict(exit=1, capture='complete', cleanup='fictional-no-child',
                result=None, error='Fictional collected classifier failure'))
            self.store.classification_failed(self.original, 'Fictional collected classifier failure')
        else:
            self.runtime.stopping.set()
            await self.runtime.classify(self.original, actual)
        self.assertEqual(self.model.calls, [])
        self.old_store = self.store
        self.old_controller = self.store.controller
        with self.store.tx():
            self.store.db.execute("UPDATE service_runs SET state='returned-awaiting-parent-END',returned=?,receipt=? WHERE controller=?",
                (self.store.clock(), encode({'fixture_only': 'dispatcher stopped before model start'}), self.old_controller))
        # Explicit fictional parent testimony, never an actual service END claim.
        with actor(self.boards['Work'].store, self.config['roles']['Work']['owner']):
            processing.release(self.store, self.boards, self.cap, self.old_controller,
                dict(actual_END=0, evidence=['Fictional parent collected this original service']))
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        for board in self.boards.values():
            board.runtime = self.store
        self.service_record(self.store)
        self.runtime = Dispatcher(self.store, models=self.model, boards=self.boards)
        self.before = self.conserved()

    def configure(self):
        self.config['tasks']['qa-execution'].update(require_package_scope=True, scope_roots=[str(self.area)])
        procedure = self.area / 'procedure.md'
        procedure.write_text('Fictional exact QA procedure; never executed by this classifier test.\n')
        self.scope = dict(cwd=str(self.area), read_roots=[str(procedure)], write_roots=[],
            network=False, procedure=str(procedure), resource_evidence='Fictional Work issued scope')
        # Make the classifier/diagnosis policy distinction observable.
        diagnosis = self.area / 'diagnosis'
        diagnosis.mkdir()
        self.config['diagnosis']['cwd'] = str(diagnosis)

    def service_record(self, store):
        # Service/parent lifecycle is seeded fiction; no socket or process probe.
        with store.tx():
            store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',
                (store.controller, self.cap, 'owned', store.clock()))
            store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,NULL,NULL)',
                (store.controller, self.cap, 'fictional-no-socket', 'serving', store.clock()))

    def source(self):
        board = self.boards['QA']
        args = board.store.parser().parse_args(['open', '--session', self.source_sender,
            '--topic', 'recovery703', '--kind', 'finding', '--text', 'Fresh fictional QA request',
            '--to', self.config['roles']['QA']['owner'], '--title', 'prelaunch case',
            '--ref', 'recovery703-one', '--no-push'])
        with board.store.database(str(self.board_path)) as conn:
            with actor(board.store, self.source_sender):
                board.store.open_thread(conn, args)
        messages = board.scan(self.store)
        self.assertEqual(len(messages), 1)
        self.store.ingest(messages[0], cursor=messages[0]['post'])
        return messages[0]

    def conserved(self):
        with self.boards['QA'].store.database(str(self.board_path)) as conn:
            grants = [dict(r) for r in conn.execute('SELECT * FROM coordinator_grants_v1 ORDER BY role')]
        return dict(original=self.store.attempt(self.original),
            result=self.store.one('SELECT * FROM results WHERE attempt=?', (self.original,)),
            source=self.store.event(self.message['id']),
            enrollments=self.store.rows('SELECT * FROM enrollments ORDER BY role'), grants=grants,
            admission=self.store.one('SELECT * FROM admissions WHERE package=?', ('recovery703-one',)),
            resolution=self.store.one('SELECT * FROM processing_admission_resolutions WHERE event=?', (self.message['id'],)),
            old_run=self.store.one('SELECT * FROM processing_runs WHERE controller=?', (self.old_controller,)),
            old_service=self.store.one('SELECT * FROM service_runs WHERE controller=?', (self.old_controller,)))

    async def test_one_fresh_classifier_after_released_original_never_started(self):
        prior = self.store.attempt(self.original)
        self.assertEqual(prior['state'], 'not-started')
        for field in ['begin', 'ended', 'exit', 'session', 'turn', 'result']:
            self.assertIsNone(prior[field], field)
        self.assertIsNotNone(prior['collected'])
        self.assertEqual(prior['capture'], 'not-started')
        self.assertEqual(prior['cleanup'], 'no-session-created')
        self.assertTrue(all(r['intake'] == 0 for r in self.before['enrollments']))
        self.assertTrue(all(r['revoked'] is not None for r in self.before['grants']))
        starts = self.store.one('SELECT starts FROM processing_capabilities WHERE id=?', (self.cap,))['starts']
        self.runtime.schedule_classification_recovery()
        self.assertEqual(len(self.runtime.active), 1)
        self.runtime.schedule_classification_recovery()
        self.assertEqual(len(self.runtime.active), 1)
        await asyncio.gather(*list(self.runtime.active))
        self.assertEqual(len(self.model.calls), 1)
        attempt, prompt, spec = self.model.calls[0]
        fresh = self.store.attempt(attempt)
        self.assertEqual(fresh['kind'], 'classifier')
        self.assertEqual(fresh['controller'], self.store.controller)
        self.assertEqual(json.loads(fresh['binding']), self.config['classifier']['binding'])
        self.assertEqual(json.loads(fresh['detail'])['prior_classifier'], self.original)
        self.assertEqual(json.loads(fresh['detail'])['processing_capability'], self.cap)
        self.assertNotIn('BOUNDED DIAGNOSIS', prompt)
        self.assertEqual(spec['sandbox'], 'read-only')
        self.assertEqual(spec['cwd'], self.config['classifier']['cwd'])
        event = self.store.one('SELECT * FROM events WHERE id=?', (self.message['id'],))
        self.assertEqual((event['state'], event['recovery_count'], event['ack']), ('queued', 1, 'ready'))
        self.assertIsNone(event['processed_at'])
        self.assertEqual(self.store.one('SELECT task,package FROM queue WHERE event=?', (self.message['id'],)),
            dict(task='qa-execution', package='recovery703-one'))
        self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.conserved(), self.before)
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities WHERE id=?', (self.cap,))['starts'], starts + 1)
        self.assertIsNone(self.store.claim_classification_recovery())
        self.assertEqual(len(self.store.rows('SELECT id FROM attempts')), 2)

    def assert_denied(self):
        before = {table: self.store.rows('SELECT * FROM ' + table)
                  for table in ('attempts', 'results', 'events', 'processing_capabilities', 'queue')}
        self.assertIsNone(self.store.claim_classification_recovery())
        self.assertEqual({table: self.store.rows('SELECT * FROM ' + table) for table in before}, before)
        self.assertEqual(self.model.calls, [])

    async def test_inconsistent_unknown_running_uncollected_and_foreign_proofs_denied(self):
        original = self.store.attempt(self.original)
        details = json.loads(original['detail'])
        mutations = [dict(state=s) for s in ['reserved', 'running', 'unknown', 'collected']]
        mutations += [{field: value} for field, value in [
            ('begin', 1), ('ended', 1), ('exit', 0), ('collected', None),
            ('session', 'fictional-contradictory-session'), ('turn', 'fictional-contradictory-turn'),
            ('result', '{}'), ('semantic', 'DONE'), ('capture', 'unknown'), ('cleanup', 'unknown'),
            ('kind', 'diagnosis'), ('event', 'fictional-foreign-event')]]
        mutations += [dict(detail=encode({**details, 'known_not_started': v})) for v in [False, 1, None]]
        mutations += [dict(detail=encode({**details, 'processing_capability': 'fictional-foreign-cap'}))]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                columns = list(mutation)
                self.store.db.execute('UPDATE attempts SET ' + ','.join(k + '=?' for k in columns) + ' WHERE id=?',
                    (*[mutation[k] for k in columns], self.original))
                self.assert_denied()
                self.store.db.execute('UPDATE attempts SET ' + ','.join(k + '=?' for k in columns) + ' WHERE id=?',
                    (*[original[k] for k in columns], self.original))
        self.assertEqual(self.conserved(), self.before)

    async def test_old_and_new_original_lifecycle_and_same_capability_required(self):
        old_run = self.before['old_run']
        mutations = [
            ('processing_runs', self.old_controller, {'state': 'owned'}),
            ('processing_runs', self.old_controller, {'state': '{}'}),
            ('processing_runs', self.old_controller, {'state': '[]'}),
            ('processing_runs', self.old_controller, {'state': encode({'parent_END': {'actual_END': None, 'evidence': ['unknown']}})}),
            ('processing_runs', self.old_controller, {'state': encode({'parent_END': {'actual_END': True, 'evidence': ['not numeric']}})}),
            ('processing_runs', self.old_controller, {'state': encode({'parent_END': {'actual_END': 0, 'evidence': []}})}),
            ('processing_runs', self.old_controller, {'capability': 'fictional-foreign-cap'}),
            ('service_runs', self.old_controller, {'state': 'serving'}),
            ('service_runs', self.old_controller, {'returned': None}),
            ('service_runs', self.old_controller, {'capability': 'fictional-foreign-cap'}),
            ('processing_runs', self.store.controller, {'state': old_run['state']}),
            ('processing_runs', self.store.controller, {'capability': 'fictional-foreign-cap'}),
            ('service_runs', self.store.controller, {'state': 'returned-awaiting-parent-END'}),
            ('service_runs', self.store.controller, {'returned': 1}),
            ('service_runs', self.store.controller, {'capability': 'fictional-foreign-cap'})]
        for table, controller, mutation in mutations:
            with self.subTest(table=table, controller=controller, mutation=mutation):
                saved = self.store.one('SELECT * FROM ' + table + ' WHERE controller=?', (controller,))
                columns = list(mutation)
                sql = 'UPDATE ' + table + ' SET ' + ','.join(k + '=?' for k in columns) + ' WHERE controller=?'
                self.store.db.execute(sql, (*[mutation[k] for k in columns], controller))
                self.assert_denied()
                self.store.db.execute(sql, (*[saved[k] for k in columns], controller))
        self.assertEqual(self.conserved(), self.before)

    async def test_released_old_original_cannot_claim_its_own_prelaunch_recovery(self):
        self.assertIsNone(self.old_store.claim_classification_recovery())
        self.assertEqual(self.conserved(), self.before)
        self.assertEqual(len(self.store.rows('SELECT id FROM attempts')), 1)

    async def test_same_role_and_task_without_current_future_source_authority_denied(self):
        saved = self.store.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.cap,))['selection']
        for future, frontier in [(False, None), (True, self.message['post'])]:
            selected = json.loads(saved)
            selected['future_intake'] = future
            if frontier is not None:
                selected['basis']['roles']['QA']['future_after'] = frontier
            self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selected), self.cap))
            self.assertTrue(self.store.role_enabled('QA'))
            self.assert_denied()
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (saved, self.cap))
        self.assertEqual(self.conserved(), self.before)

    async def test_held_processed_and_excluded_sources_skipped_before_body(self):
        for column, value in [('hold', 'explicit fictional source hold'), ('processed_at', 1)]:
            self.store.db.execute('UPDATE events SET ' + column + '=? WHERE id=?', (value, self.message['id']))
            with patch.object(self.store, 'event', side_effect=AssertionError('held source body acquired')):
                self.assert_denied()
            self.store.db.execute('UPDATE events SET ' + column + '=NULL WHERE id=?', (self.message['id'],))
        # Exact SQL exclusion seam; exercise production selector ordering before
        # any source acquisition. Existing configuration boundary tests cover
        # construction of this predicate independently.
        with patch('coordinator_runtime.configuration.event_candidate_scope', return_value=('0', ())):
            with patch.object(self.store, 'event', side_effect=AssertionError('excluded body acquired')):
                self.assert_denied()
        self.assertEqual(self.conserved(), self.before)

    async def test_revoked_capability_and_changed_source_pin_refuse_without_reservation(self):
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?', (self.store.clock(), self.cap))
        with self.assertRaises(Refusal):
            self.store.claim_classification_recovery()
        self.store.db.execute('UPDATE processing_capabilities SET revoked=NULL WHERE id=?', (self.cap,))
        saved = self.store.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.cap,))['selection']
        changed = json.loads(saved)
        changed['basis']['implementation'] = {}
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(changed), self.cap))
        with self.assertRaises(Refusal):
            self.store.claim_classification_recovery()
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (saved, self.cap))
        self.assertEqual(self.conserved(), self.before)
        self.assertEqual(len(self.store.rows('SELECT id FROM attempts')), 1)

    async def test_two_connections_claim_exactly_one_recovery_transaction(self):
        barrier = Barrier(2)
        def claim():
            # Two DB handles for the same newly owned fictional collector.
            contender = Store(self.config, controller=self.store.controller)
            try:
                contender.processing = processing.Access(contender, self.cap, self.boards)
                barrier.wait(timeout=10)
                return contender.claim_classification_recovery()
            finally:
                contender.close()
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(claim) for _ in range(2)]
            claims = [f.result(timeout=20) for f in futures]
        self.assertEqual(sum(item is not None for item in claims), 1)
        self.assertEqual(len(self.store.rows('SELECT id FROM attempts')), 2)
        self.assertEqual(self.conserved(), self.before)

    async def test_collected_failure_keeps_diagnosis(self):
        self.runtime.schedule_classification_recovery()
        await asyncio.gather(*list(self.runtime.active))
        self.assertEqual(len(self.model.calls), 1)
        attempt, prompt, spec = self.model.calls[0]
        self.assertEqual(self.store.attempt(attempt)['kind'], 'diagnosis')
        self.assertIn('BOUNDED DIAGNOSIS', prompt)
        self.assertEqual(spec['cwd'], self.config['diagnosis']['cwd'])
        self.assertEqual(self.store.one('SELECT state FROM events WHERE id=?', (self.message['id'],))['state'], 'queued')
        self.assertEqual(self.conserved(), self.before)

    async def test_failed_fresh_classifier_consumes_only_recovery_and_retains_prior(self):
        self.model.invalid = True
        self.runtime.schedule_classification_recovery()
        await asyncio.gather(*list(self.runtime.active))
        current = self.store.one('SELECT state,ack,recovery_count FROM events WHERE id=?', (self.message['id'],))
        self.assertEqual(current, dict(state='classification-held', ack='pending', recovery_count=1))
        self.assertEqual(self.store.rows('SELECT * FROM queue'), [])
        self.assertIsNone(self.store.claim_classification_recovery())
        self.assertEqual(self.conserved(), self.before)
        self.assertEqual(len(self.model.calls), 1)

    def hold_from_other_connection(self, reason='fictional late source hold'):
        owner = Store(self.config)
        try:
            owner.set_hold(self.message['id'], reason)
        finally:
            owner.close()

    async def test_diagnosis_preparation_rechecks_before_prior_result724(self):
        attempt, event = self.store.claim_classification_recovery()
        self.assertEqual(self.store.attempt(attempt)['kind'], 'diagnosis')
        self.hold_from_other_connection()
        actual = self.store.attempt
        def permitted(key):
            if key == self.original:
                raise AssertionError('held prior classifier result acquired')
            return actual(key)
        with patch.object(self.store, 'attempt', side_effect=permitted):
            await self.runtime.classify(attempt, event)
        self.assertEqual(self.model.calls, [])
        self.assertEqual(self.store.attempt(attempt)['state'], 'not-started')
        self.assert_late_hold_conserved()

    def assert_late_hold_conserved(self):
        self.assertEqual(self.conserved(), self.before)
        self.assertEqual(self.store.one('SELECT ack,recovery_count,processed_at FROM events WHERE id=?',
            (self.message['id'],)), dict(ack='pending', recovery_count=1, processed_at=None))
        self.assertEqual(self.store.rows('SELECT * FROM queue'), [])
        self.assertIsNone(self.store.claim_classification_recovery())

    async def test_hold_after_claim_refuses_dispatch_without_model_or_ack(self):
        attempt, event = self.store.claim_classification_recovery()
        starts = self.store.processing.current()[0]['starts']
        self.hold_from_other_connection()
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')), \
             patch.object(self.store, 'routing_event', side_effect=AssertionError('held routing acquired')):
            await self.runtime.classify(attempt, event)
            self.runtime.receipts()
        current = self.store.attempt(attempt)
        self.assertEqual(self.model.calls, [])
        self.assertEqual(current['state'], 'not-started')
        self.assertIsNone(current['begin'])
        self.assertIsNone(current['ended'])
        self.assertIsNone(current['exit'])
        self.assertEqual(self.store.processing.current()[0]['starts'], starts)
        self.assert_late_hold_conserved()

    async def test_hold_before_begin_refuses_without_changing_reservation(self):
        attempt, _ = self.store.claim_classification_recovery()
        before = self.store.attempt(attempt)
        # Even a non-null empty reason is a hold, as in the claim predicate.
        self.hold_from_other_connection('')
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')):
            with self.assertRaises(Refusal):
                self.store.begin(attempt, {'fictional': True})
        self.assertEqual(self.store.attempt(attempt), before)
        self.assert_late_hold_conserved()

    async def test_hold_after_begin_preserves_collection_but_refuses_commit_and_ack(self):
        attempt, _ = self.store.claim_classification_recovery()
        self.store.begin(attempt, {'fictional_typed_answer': True})
        self.hold_from_other_connection()
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')), \
             patch.object(self.store, 'routing_event', side_effect=AssertionError('held routing acquired')):
            self.store.collect(attempt, dict(exit=0, capture='complete', cleanup='fictional-no-child',
                result=dict(event_id=self.message['id'], task='qa-execution', package='recovery703-one',
                            reason='Fictional answer acquired before hold')))
            before = self.store.attempt(attempt), self.store.one('SELECT * FROM results WHERE attempt=?', (attempt,))
            with self.assertRaises(Refusal): self.store.commit_classification(attempt)
            self.runtime.receipts()
        self.assertEqual((self.store.attempt(attempt), self.store.one('SELECT * FROM results WHERE attempt=?', (attempt,))), before)
        self.assert_late_hold_conserved()

    async def test_appserver_rechecks_hold_after_preflight_before_creation(self):
        attempt, _ = self.store.claim_classification_recovery()
        adapter = AppServer(self.config)
        async def preflight(*args):
            self.hold_from_other_connection()
            return ['fictional-never-created'], {}
        with patch.object(adapter, 'command', side_effect=preflight), \
             patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec', new_callable=AsyncMock,
                   side_effect=AssertionError('fictional creation gate crossed')) as create:
            outcome = await adapter.run(self.store, attempt, 'fictional prompt',
                dict(cwd=str(self.area), sandbox='read-only'), {})
        create.assert_not_called()
        self.assertIn('source', outcome['error'])
        self.assertIsNone(outcome['exit'])
        self.assertIsNone(self.store.attempt(attempt)['begin'])
        self.assert_late_hold_conserved()

    async def test_appserver_rechecks_hold_after_admission_before_disclosure(self):
        attempt, _ = self.store.claim_classification_recovery()
        adapter = AppServer(self.config)
        @asynccontextmanager
        async def admission(profile):
            self.hold_from_other_connection()
            with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')):
                yield {}
        with patch.object(self.store.execution_pool, 'admission', admission), \
             patch.object(adapter, 'start_turn', new_callable=AsyncMock,
                   side_effect=AssertionError('fictional disclosure gate crossed')) as disclose:
            with self.assertRaises(Refusal):
                await adapter.turn(object(), self.store, attempt, ident(), 'fictional prompt',
                    dict(cwd=str(self.area), sandbox='read-only'), self.config['classifier']['binding'], {}, {})
        disclose.assert_not_called()
        self.assert_late_hold_conserved()

    async def test_changed_current_source_selection_after_claim_refuses(self):
        attempt, _ = self.store.claim_classification_recovery()
        row = self.store.processing.current()[0]
        selection = json.loads(row['selection'])
        selection['future_intake'] = False
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selection), self.cap))
        with self.assertRaises(Refusal): self.store.authorize_launch(attempt)
        self.assertEqual(self.model.calls, [])
        self.assert_late_hold_conserved()

    async def test_launch_rechecks_current_capability_after_recovery_claim(self):
        attempt, event = self.store.claim_classification_recovery()
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?', (self.store.clock(), self.cap))
        await self.runtime.classify(attempt, event)
        self.assertEqual(self.model.calls, [])
        fresh = self.store.attempt(attempt)
        self.assertEqual(fresh['state'], 'not-started')
        self.assertIsNone(fresh['begin'])
        self.assertIsNone(fresh['ended'])
        self.assertIsNone(fresh['exit'])
        self.assertIsNone(fresh['session'])
        self.assertEqual(self.conserved(), self.before)
        self.assertEqual(self.store.one('SELECT recovery_count FROM events WHERE id=?', (event['id'],))['recovery_count'], 1)

    async def test_launch_rechecks_original_grant_without_native_reenrollment(self):
        attempt, event = self.store.claim_classification_recovery()
        with self.boards['QA'].store.database(str(self.board_path)) as conn:
            conn.execute("UPDATE coordinator_grants_v1 SET actor='fictional-foreign' WHERE role='QA'")
        await self.runtime.classify(attempt, event)
        self.assertEqual(self.model.calls, [])
        fresh = self.store.attempt(attempt)
        self.assertEqual(fresh['state'], 'not-started')
        self.assertIsNone(fresh['begin'])
        self.assertIsNone(fresh['ended'])
        self.assertIsNone(fresh['exit'])
        self.assertIsNone(fresh['session'])
        self.assertIsNone(self.store.claim_classification_recovery())
        self.assertTrue(all(r['intake'] == 0 for r in self.store.rows('SELECT intake FROM enrollments')))


class OrdinaryLateHold(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from support import event
        self.bootstrap(lambda: None)
        self.message = event(self.config, 'ordinary-late-hold', task='work-proposer')
        self.store.ingest(self.message)
        self.attempt, self.source = self.store.claim_classification()

    async def test_ordinary_classifier_hold_refuses_launch_and_begin(self):
        self.store.set_hold(self.message['id'], 'fictional ordinary hold')
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')):
            with self.assertRaises(Refusal): self.store.authorize_launch(self.attempt)
            with self.assertRaises(Refusal): self.store.begin(self.attempt, {})
        self.assertIsNone(self.store.attempt(self.attempt)['begin'])

    async def test_ordinary_collected_classifier_hold_refuses_commit_before_body(self):
        from support import collect
        collect(self.store, self.attempt, dict(event_id=self.message['id'], task='work-proposer', package=None,
            reason='Fictional ordinary answer'))
        original = self.store.attempt(self.attempt)
        self.store.set_hold(self.message['id'], 'fictional ordinary hold')
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')):
            with self.assertRaises(Refusal): self.store.commit_classification(self.attempt)
            self.runtime.receipts()
        self.assertEqual(self.store.attempt(self.attempt), original)
        self.assertEqual(self.store.rows('SELECT * FROM queue'), [])
        self.assertEqual(self.store.one('SELECT ack,processed_at FROM events WHERE id=?', (self.message['id'],)),
            dict(ack='pending', processed_at=None))


if __name__ == '__main__':
    unittest.main()
