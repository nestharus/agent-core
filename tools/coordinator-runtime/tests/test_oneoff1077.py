"""Decision1077 recovery/retention outcomes on owned fiction; no account calls.

Real producer launch/collection/processing APIs and SQLite are exercised. The
model return and enrollment are explicit fictional seams, not actual receipts.
All fixture files, including failed runs, remain under ONEOFF1077_FIXTURES.
"""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from support import config_at, enrolled, queued, event, result, collect
from coordinator_runtime import oneoff, cleanup
from coordinator_runtime.contracts import Refusal, encode
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


class Recovery(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='fiction1077-', dir=os.environ['ONEOFF1077_FIXTURES']))
        self.now = 100000.
        self.config = config_at(self.area)
        if self._testMethodName not in {'test_dispatcher_reaches_all_four_role_producers_and_restart_recovers',
                                       'test_durable_interrupted_checkpoint_survives_restart_without_collection'}:
            import sqlite3
            connect = sqlite3.connect
            connection = patch('coordinator_runtime.store.sqlite3.connect',
                               side_effect=lambda *args, **kwargs: connect(':memory:', isolation_level=None))
            connection.start()
            self.addCleanup(connection.stop)
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.runtime = Dispatcher(self.store, models=object(), boards={})

    def reservation(self, role='Work'):
        task = 'qa-execution' if role == 'QA' else role.lower()+'-integrator'
        message = event(self.config, role, role=role, task=task,
                        package='fictional-package' if role == 'QA' else None)
        queued(self.store, message)
        if role == 'QA':
            # Independent fixture enrollment/admission, no real package owner.
            self.store.admit('fictional-package', self.config['roles']['Branch']['owner'],
                             {'evidence':'fictional package admission'})
        job = self.store.reserve()
        self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'], job['token'])
        return message, job, attempt

    def prepare(self, attempt, **spec):
        oneoff.prepare(self.store, attempt, 'exact fictional purpose and source context',
                       {'cwd': str(self.area), 'sandbox': 'read-only', **spec}, {'type':'object'})

    def completed(self):
        message, job, attempt = self.reservation()
        self.prepare(attempt)
        collect(self.store, attempt, result())
        self.store.finish_job(job['id'], job['token'])
        return message, job, attempt

    def test_dispatcher_reaches_all_four_role_producers_and_restart_recovers(self):
        for role in ('Work', 'Branch', 'Reviews', 'QA'):
            message, job, attempt = self.reservation(role)
            async def fake_model(store, original, prompt, spec, schema):
                self.assertIsNotNone(store.one('SELECT attempt FROM oneoff_recovery WHERE attempt=?', (original,)))
                store.begin(original, {'fixture':True})
                return {'result':result(), 'exit':0, 'capture':'complete', 'cleanup':'done', 'error':None, 'detail':{}}
            self.runtime.models = type('Model', (), {'run':staticmethod(fake_model)})()
            outcome = asyncio.run(self.runtime.run_model(attempt, 'durable '+role, {'cwd':str(self.area)}, {}))
            self.store.collect(attempt, outcome)
            self.store.finish_job(job['id'], job['token'])
            restarted = Store(self.config, controller='fictional-successor', clock=lambda:self.now)
            try:
                recovered = oneoff.snapshot(restarted, attempt)
                self.assertEqual(recovered['launch']['prompt'], 'durable '+role)
                self.assertEqual(recovered['collection']['controller'], self.store.controller)
                self.assertFalse(recovered['permission_to_replay'])
            finally:
                restarted.close()

    def test_classifier_snapshot_binds_original_collection(self):
        # Classifier is a real reservation. Mapping/diagnosis call-site closure
        # is source-reviewed separately; this is not a fabricated cohort claim.
        message = event(self.config, 'classifier')
        self.store.ingest(message)
        attempt, source = self.store.claim_classification()
        self.prepare(attempt)
        collect(self.store, attempt, {'event_id':source['id'],'task':source['allowed_tasks'][0],
                'package':None,'reason':'fictional meaning'})
        self.assertIsNotNone(oneoff.snapshot(self.store, attempt)['collection_hash'])

    def test_exact_session_requirement_refuses_before_model_or_creation(self):
        _, _, attempt = self.reservation()
        outcome = asyncio.run(self.runtime.run_model(attempt, 'needs continuation',
                              {'exact_session_after_exit':True}, {}))
        self.assertTrue(outcome['detail']['known_not_started'])
        self.assertIn('unsupported', outcome['error'])
        self.assertIsNone(self.store.attempt(attempt)['begin'])
        self.assertIsNone(self.store.one('SELECT attempt FROM oneoff_recovery'))

    def test_original_and_duplicate_launch_cannot_be_manufactured(self):
        _, _, attempt = self.reservation()
        original = self.store.controller
        self.store.controller = 'fictional-foreign'
        self.assertRaises(Refusal, self.prepare, attempt)
        self.store.controller = original
        self.prepare(attempt)
        self.assertRaises(Refusal, self.prepare, attempt)
        collect(self.store, attempt, {**result(), 'oneoff_recovery':{'attempt':'arbitrary'}})
        self.assertEqual(len(self.store.rows('SELECT attempt FROM oneoff_recovery')), 1)
        self.assertRaises(Refusal, oneoff.snapshot, self.store, 'arbitrary')

    def test_processing_clock_uses_whole_completion_not_END_or_DONE(self):
        message, job, attempt = self.reservation()
        self.prepare(attempt)
        collect(self.store, attempt, result())
        self.now += 90000
        self.assertEqual(oneoff.retirement_state(self.store, attempt), 'held-processing-24h-or-dependencies')
        self.store.finish_job(job['id'], job['token'])
        self.assertEqual(oneoff.retirement_state(self.store, attempt), 'held-processing-24h-or-dependencies')
        self.now += 86399
        self.assertEqual(oneoff.retirement_state(self.store, attempt), 'held-processing-24h-or-dependencies')
        self.now += 1
        self.assertEqual(oneoff.retirement_state(self.store, attempt), 'processing-window-qualified-custodian-still-required')

    def test_reopen_consumer_effect_and_current_use_holds_survive(self):
        message, job, attempt = self.completed()
        self.now += 86400
        self.assertTrue(cleanup.eligible_event(self.store, oneoff.event_metadata(self.store, message['id'])))
        self.store.set_hold(message['id'], 'human/current-use/privacy/recovery hold')
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))
        self.store.set_hold(message['id'], None)
        self.store.db.execute("UPDATE jobs SET state='held',effects='unknown' WHERE id=?", (job['id'],))
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))
        self.store.db.execute("UPDATE jobs SET state='closed',effects='none',closed_at=? WHERE id=?", (self.now,job['id']))
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))
        self.now += 86400
        self.assertNotIn('held', oneoff.retirement_state(self.store, attempt))

    def test_changed_and_partial_collection_retain_durable_original(self):
        _, _, attempt = self.completed()
        self.now += 86400
        original = self.store.one('SELECT * FROM oneoff_recovery WHERE attempt=?', (attempt,))
        self.store.db.execute("UPDATE attempts SET capture='incomplete',error='fictional capture gap' WHERE id=?", (attempt,))
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)
        self.assertEqual(self.store.one('SELECT * FROM oneoff_recovery WHERE attempt=?', (attempt,)), original)

    def test_budget_refusal_precedes_launch_and_retains_existing_source(self):
        _, _, attempt = self.reservation()
        with patch.object(self.store, 'budget', side_effect=Refusal('finite fictional capacity exhausted')):
            outcome = asyncio.run(self.runtime.run_model(attempt, 'retained input', {}, {}))
        self.assertTrue(outcome['detail']['known_not_started'])
        self.assertIsNone(self.store.attempt(attempt)['begin'])
        self.assertIsNone(self.store.one('SELECT attempt FROM oneoff_recovery'))

    def test_adapter_checkpoints_before_teardown_and_collects_after_checkpoint_failure(self):
        from coordinator_runtime.appserver import AppServer
        from types import SimpleNamespace
        _, _, attempt = self.reservation()
        self.prepare(attempt)
        adapter = AppServer(self.config)
        peer = SimpleNamespace(progress=[], tools={}, capture_issues=[], progress_dropped=0,
                               correlation_dropped=0, command_inputs={}, command_input_bytes=0)
        child = SimpleNamespace(pid=1, returncode=None)
        async def session(*args):
            return result()
        async def teardown(child, peer, outcome):
            row = self.store.one('SELECT body FROM oneoff_terminal_recovery WHERE attempt=?',(attempt,))
            self.assertEqual(json.loads(row['body'])['result']['semantic'], 'DONE')
            outcome.update(exit=0, capture='complete', cleanup='done')
        with patch.object(adapter, 'command', AsyncMock(return_value=(['fictional-noexec'],{}))), \
             patch.object(adapter, 'session', session), patch.object(adapter, 'unsubscribe', AsyncMock()), \
             patch.object(adapter, 'teardown', teardown), \
             patch('coordinator_runtime.appserver.Peer', return_value=peer), \
             patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec', AsyncMock(return_value=child)):
            outcome = asyncio.run(adapter.run(self.store, attempt, 'fictional prompt', {'cwd':str(self.area)}, {}))
        self.store.collect(attempt, outcome)
        recovered = oneoff.snapshot(self.store, attempt)
        self.assertEqual(recovered['pre_teardown']['result']['semantic'], 'DONE')
        self.assertEqual(oneoff.reserved_bytes(self.store), 0)
        _, _, failed = self.reservation('Branch')
        self.prepare(failed)
        async def failed_teardown(child, peer, outcome):
            self.assertEqual(outcome['detail']['recovery_checkpoint'], 'unqualified-held')
            outcome.update(exit=0, capture='complete', cleanup='done')
        with patch.object(adapter, 'command', AsyncMock(return_value=(['fictional-noexec'],{}))), \
             patch.object(adapter, 'session', session), patch.object(adapter, 'unsubscribe', AsyncMock()), \
             patch.object(adapter, 'teardown', failed_teardown), \
             patch('coordinator_runtime.oneoff.checkpoint', side_effect=OSError('fictional full device')), \
             patch('coordinator_runtime.appserver.Peer', return_value=peer), \
             patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec', AsyncMock(return_value=child)):
            failed_outcome = asyncio.run(adapter.run(self.store, failed, 'fictional prompt', {'cwd':str(self.area)}, {}))
        self.store.collect(failed, failed_outcome)
        self.assertIsNotNone(self.store.attempt(failed)['collected'])
        self.assertIsNotNone(self.store.attempt(failed)['error'])
        self.assertIn('held', oneoff.retirement_state(self.store, failed))

    def test_terminal_reservation_rejects_oversize_and_foreign_checkpoint(self):
        _, _, attempt = self.reservation()
        self.prepare(attempt)
        self.store.begin(attempt, {'fictional_process_creation':True})
        self.assertGreater(oneoff.reserved_bytes(self.store), 0)
        self.assertRaises(Refusal, oneoff.checkpoint, self.store, attempt,
                          {'result':'x'*(oneoff.terminal_reserve(self.store)+1)})
        self.assertIsNone(self.store.one('SELECT body FROM oneoff_terminal_recovery')['body'])
        original = self.store.controller
        self.store.controller = 'fictional-foreign'
        self.assertRaises(Refusal, oneoff.checkpoint, self.store, attempt, {'result':result()})
        self.store.controller = original
        oneoff.checkpoint(self.store, attempt, {'result':result('PARTIAL')})
        first = self.store.one('SELECT body FROM oneoff_terminal_recovery')['body']
        oneoff.checkpoint(self.store, attempt, {'result':result('DONE')})
        self.assertEqual(first, self.store.one('SELECT body FROM oneoff_terminal_recovery')['body'])
        self.store.collect(attempt, {'result':result(), 'exit':0, 'capture':'complete',
                                    'cleanup':'done','error':None,'detail':{}})
        self.store.db.execute("UPDATE oneoff_terminal_recovery SET body='{}'")
        self.assertTrue(oneoff.recovery_hold(self.store, self.store.attempt(attempt)))

    def test_known_root_handoff_never_grants_cascade_auxiliary_or_deletion(self):
        _, _, attempt = self.completed()
        handoff = oneoff.residual_handoff(self.store, attempt)
        self.assertIsNone(handoff['record'])  # Synthetic session string alone is insufficient.
        self.assertFalse(handoff['automatic_delete'])
        self.assertEqual(handoff['physical_reclamation'], 'unknown')
        row = self.store.attempt(attempt)
        detail = json.loads(row['detail'])
        detail.update(thread_start='owned-root-observed', session_residuals={'known_thread':row['session']})
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),attempt))
        handoff = oneoff.residual_handoff(self.store, attempt)
        self.assertEqual(handoff['record'], row['session'])
        self.assertFalse(handoff['automatic_delete'])
        self.assertIn('held', handoff['processing'])  # Changed collector evidence invalidates old snapshot.


    def test_current_ordinary_writers_preserve_original_and_allow_retirement(self):
        from coordinator_runtime import ordinary
        from types import SimpleNamespace
        _, job, attempt = self.completed()
        before = oneoff.snapshot(self.store, attempt)['original_collection']
        ordinary.wait_for_acceptance(self.store, self.store.job(job['id']))
        receipt = {'job': job['id'], 'attempt': attempt, 'receipt': encode({'after': {'fixture': 'same'}}),
                   'acceptance': {'independent': 'fictional semantic decision'}}
        with patch.object(ordinary, 'accepted_runs', return_value=[receipt]), \
             patch.object(ordinary, 'selected', return_value=True), \
             patch.object(ordinary.prospective, 'board', return_value=SimpleNamespace(_software_job_grant=lambda *a: None)), \
             patch.object(ordinary, 'policy_for', return_value=({}, {'kind': 'fictional-no-external-effect'})), \
             patch.object(ordinary, 'source', AsyncMock(return_value={'fixture': 'same'})):
            asyncio.run(ordinary.qualification(self.store, self.store.job(job['id'])))
        view = oneoff.snapshot(self.store, attempt)
        self.assertEqual(view['original_collection'], before)
        self.assertNotEqual(view['collection']['detail'], before['detail'])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM oneoff_progress_recovery')['n'], 3)
        self.now += 86400
        self.assertEqual(oneoff.retirement_state(self.store, attempt), 'processing-window-qualified-custodian-still-required')
        self.store.db.execute("UPDATE oneoff_collection_recovery SET original='{}' WHERE attempt=?", (attempt,))
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))

    def test_normal_publication_wait_and_inventory_recheck_preserve_seal(self):
        _, job, attempt = self.reservation()
        self.prepare(attempt)
        collect(self.store, attempt, result())
        sealed = oneoff.snapshot(self.store, attempt)['original_collection']
        with patch.object(self.runtime, 'admit_collected_context', return_value=True), \
             patch.object(self.store, 'finish_job', side_effect=BlockingIOError('fictional publication busy')):
            self.runtime.try_finish(job['id'])
        self.assertIn('canonical_lock_wait_since', json.loads(oneoff.snapshot(self.store, attempt)['collection']['detail']))
        self.store.capture_gap(attempt, 'fictional owned leaf unavailable')
        self.assertEqual(oneoff.snapshot(self.store, attempt)['collection']['capture'], 'artifact-inventory-incomplete')
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))
        self.store.recheck_artifact_capture(attempt)
        self.assertEqual(oneoff.snapshot(self.store, attempt)['collection']['capture'], 'complete')
        self.assertEqual(oneoff.snapshot(self.store, attempt)['original_collection'], sealed)
        self.store.finish_job(job['id'], job['token'])
        self.now += 86400
        self.assertEqual(oneoff.retirement_state(self.store, attempt), 'processing-window-qualified-custodian-still-required')

    def test_routine_reconcile_uses_attributed_progress_without_resealing(self):
        from coordinator_runtime import routine
        from coordinator_runtime.contracts import digest
        from types import SimpleNamespace
        area = self.area/'routine'; area.mkdir()
        config = config_at(area)
        target = area/'owned-fiction.txt'; target.write_text('original fictional content')
        task = config['tasks']['work-integrator']
        task.update(effects='owner-reconcile', routine_completion={'kind':'file-witness','targets':[str(target)]})
        task['effect_authority'].update(operations=['write-role-records'], write_roots=[str(area)])
        store = enrolled(config, clock=lambda:self.now); self.addCleanup(store.close)
        message = event(config, 'routine'); queued(store, message)
        job = store.reserve(); attempt = store.start_job(job['id'], job['token'])
        oneoff.prepare(store, attempt, 'fictional routine purpose', {}, {})
        collect(store, attempt, result(), tool_completion={'complete':True,'items':[{'fictional':'owned-file-write'}]})
        sealed = oneoff.snapshot(store, attempt)['original_collection']
        witness = {'exists': True, 'sha256':digest('owned fiction')}
        store.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                         (attempt, job['task'], 'fictional-grant', encode(task['routine_completion']),
                          encode({str(target):witness}), 'prepared'))
        board = SimpleNamespace(completion_authority=lambda *a:{'id':'fictional-grant','issued_by':'fictional-owner',
                                'owner':config['roles']['Work']['owner'], 'authority':'owned synthetic target only'})
        with patch.object(routine.readiness, 'assess', return_value={'ready':True,'fictional':True}), \
             patch.object(routine.publication, 'publish', return_value=[{'target':str(target),'witness':encode(witness)}]):
            self.assertTrue(routine.reconcile(store, board, store.job(job['id'])))
        self.assertEqual(oneoff.snapshot(store, attempt)['original_collection'], sealed)
        self.assertIn('local_readiness', json.loads(store.attempt(attempt)['detail']))
        self.assertFalse(oneoff.recovery_hold(store, store.attempt(attempt)))
        self.assertEqual(store.job(job['id'])['effects'], 'reconciled')

    def test_checkpoint_is_readable_before_collection_without_adopting_original(self):
        _, job, attempt = self.reservation()
        self.prepare(attempt)
        self.store.begin(attempt, {'fictional_owned_process': True})
        oneoff.checkpoint(self.store, attempt, {'result':result('PARTIAL')}, {'external_effects':'unknown-held'})
        self.store.controller = 'fictional-lawful-current-reader'
        view = oneoff.snapshot(self.store, attempt)
        self.assertEqual(view['collection_status'], 'uncollected-original-held')
        self.assertIsNone(view['collection'])
        self.assertEqual(view['pre_teardown']['result']['semantic'], 'PARTIAL')
        self.assertFalse(view['permission_to_adopt_original'])
        self.assertFalse(view['permission_to_replay'])
        self.assertIsNone(self.store.attempt(attempt)['collected'])
        self.assertIn('held', oneoff.retirement_state(self.store, attempt))
        self.assertRaises(Refusal, self.store.adopt_collected, job['id'])
        self.store.set_hold(json.loads(job['members'])[0]['event'], 'fictional current privacy hold')
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)

    def test_completed_classifier_recovery_is_current_read_only(self):
        message = event(self.config, 'completed-classifier'); self.store.ingest(message)
        attempt, source = self.store.claim_classification(); self.prepare(attempt)
        collect(self.store, attempt, {'event_id':source['id'],'task':source['allowed_tasks'][0],
                                     'package':None,'reason':'fictional independent task meaning'})
        self.store.commit_classification(attempt)
        view = oneoff.snapshot(self.store, attempt)
        self.assertEqual(view['collection_status'], 'collected')
        self.assertRaises(Refusal, self.store.authorize_preparation, attempt)
        self.assertRaises(Refusal, self.store.commit_classification, attempt)
        self.store.set_hold(source['id'], 'fictional privacy/recovery hold')
        with patch.object(self.store, 'attempt', side_effect=AssertionError('body before hold admission')):
            self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)

    def test_unreceipted_changes_foreign_progress_and_budget_failures_stay_held(self):
        _, _, attempt = self.completed()
        sealed = oneoff.snapshot(self.store, attempt)['original_collection']
        with self.store.tx():
            self.store.controller = 'fictional-foreign-writer'
            self.assertRaises(Refusal, oneoff.advance, self.store, attempt, {'detail':'{}'}, 'foreign fiction')
        self.store.controller = sealed['controller']
        with patch.object(self.store, 'budget', side_effect=Refusal('fictional full retained journal')):
            with self.assertRaises(Refusal), self.store.tx():
                oneoff.advance(self.store, attempt, {'detail':'{}'}, 'owned capacity refusal')
        self.assertEqual(oneoff.snapshot(self.store, attempt)['original_collection'], sealed)
        self.store.db.execute("UPDATE attempts SET detail='{}' WHERE id=?", (attempt,))
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)
        self.assertTrue(oneoff.recovery_hold(self.store, self.store.attempt(attempt)))


    def test_changed_collection_flag_cannot_turn_sealed_original_into_uncollected_view(self):
        _, _, attempt = self.completed()
        self.store.db.execute('UPDATE attempts SET collected=NULL WHERE id=?', (attempt,))
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)
        self.assertTrue(oneoff.recovery_hold(self.store, self.store.attempt(attempt)))

    def test_collection_budget_refusal_keeps_original_outcome_and_explicit_recovery_gap(self):
        _, _, attempt = self.reservation(); self.prepare(attempt)
        with patch.object(self.store, 'budget', side_effect=Refusal('fictional collection recovery capacity refusal')):
            collect(self.store, attempt, result())
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])
        self.assertIsNotNone(self.store.one('SELECT result FROM results WHERE attempt=?',(attempt,))['result'])
        self.assertIsNotNone(self.store.one('SELECT error FROM oneoff_collection_recovery WHERE attempt=?',(attempt,))['error'])
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)
        self.assertTrue(oneoff.recovery_hold(self.store, self.store.attempt(attempt)))

    def test_progress_backpressure_retains_actual_inventory_failure_and_all_holds(self):
        from coordinator_runtime.contracts import Backpressure
        _, _, attempt = self.completed()
        original = oneoff.snapshot(self.store, attempt)['original_collection']
        with patch.object(self.store, 'budget', side_effect=Backpressure('fictional retained progress capacity')):
            self.store.capture_gap(attempt, 'fictional inventory failure must remain visible')
        row = self.store.attempt(attempt)
        self.assertEqual(row['capture'], 'artifact-inventory-incomplete')
        self.assertIn('fictional inventory failure', row['error'])
        retained = self.store.one('SELECT * FROM oneoff_collection_recovery WHERE attempt=?',(attempt,))
        self.assertEqual(json.loads(retained['original']), original)
        self.assertIn('fictional retained progress capacity', retained['error'])
        self.assertRaises(Refusal, oneoff.snapshot, self.store, attempt)
        self.assertTrue(oneoff.recovery_hold(self.store, row))

    def execute_role_path(self, role):
        from types import SimpleNamespace
        message, job, attempt = self.reservation(role)
        self.runtime.boards[role] = SimpleNamespace(verify_authority=lambda *a:None)
        self.runtime.models = FictionalAdapter()
        asyncio.run(self.runtime.execute(job['id'], attempt))
        self.assertEqual(self.store.job(job['id'])['state'], 'closed',
                         {'job': self.store.job(job['id']), 'attempt':self.store.attempt(attempt)})
        view = oneoff.snapshot(self.store, attempt)
        self.assertEqual(view['launch']['job'], job['id'])
        self.assertEqual(view['launch']['members'], json.loads(job['members']))
        self.assertIn(message['body'], view['launch']['prompt'])
        self.assertEqual(view['pre_teardown']['result']['semantic'], 'DONE')
        self.assertIsNotNone(oneoff.event_metadata(self.store, message['id'])['processed_at'])
        self.now += 86400
        self.assertTrue(cleanup.eligible_event(self.store, oneoff.event_metadata(self.store, message['id'])))

    def test_work_execution_path_keeps_launch_result_and_processing_window(self):
        self.execute_role_path('Work')

    def test_branch_execution_path_keeps_launch_result_and_processing_window(self):
        self.execute_role_path('Branch')

    def test_qa_execution_path_keeps_launch_result_and_processing_window(self):
        self.execute_role_path('QA')

    def test_durable_interrupted_checkpoint_survives_restart_without_collection(self):
        _, job, attempt = self.reservation()
        self.prepare(attempt)
        self.store.begin(attempt, {'fictional_creation':True})
        oneoff.checkpoint(self.store, attempt, {'result':result('PARTIAL')}, {'unknown_effect':'held'})
        original = self.store.controller
        self.store.close()
        reader = Store(self.config, controller='fictional-lawful-restart-reader', clock=lambda:self.now)
        self.addCleanup(reader.close)
        recovered = oneoff.snapshot(reader, attempt)
        self.assertEqual(recovered['launch']['collector'], original)
        self.assertEqual(recovered['pre_teardown']['evidence'], {'unknown_effect':'held'})
        self.assertEqual(recovered['collection_status'], 'uncollected-original-held')
        self.assertIsNone(reader.attempt(attempt)['exit'])
        self.assertRaises(Refusal, reader.adopt_collected, job['id'])
        self.assertRaises(Refusal, reader.collect, attempt, {'result':result(), 'exit':0,'capture':'complete','cleanup':'done'})
        with patch.object(reader, 'require_attempt_execution_open', side_effect=Refusal('fictional current execution fence')):
            self.assertRaises(Refusal, oneoff.snapshot, reader, attempt)

    def native_fixture(self, interrupted=False):
        from coordinator_runtime import reviews, service, processing
        from coordinator_runtime.contracts import digest
        from types import SimpleNamespace, MethodType
        area = self.area/'native'; area.mkdir()
        config = config_at(area)
        config['tasks']['reviews-proposer']['binding'] = dict(reviews.BINDING)
        store = enrolled(config, clock=lambda:self.now); self.addCleanup(store.close)
        method = area/'fictional-procedure.md'; method.write_text('Fictional complete procedure operand, no actual role efficacy claimed.\n')
        policy = {'method':str(method), 'method_files':{str(method):reviews.sha(method.read_bytes())},
                  'routes':{p:'fictional-route' for p in config['profiles']}, 'deadline':2,
                  'components':{'fictional-component':{'repository':str(area),'paths':['fiction.txt'],
                    'history':str(store.home/'review-history/fictional-component'),'authority':'synthetic source only'}}}
        packet = {'component':'fictional-component','origin':'fictional-origin','base':'1'*40,
                  'head':'1'*40,'previous':None,'answered_ids':[]}
        selected = {'service':{'reviews':{'reviews-proposer':policy},'legacy_resources':{}}}
        access = SimpleNamespace(key='fictional-current-capability', current=lambda:({},selected),
                                 reserve=lambda *a:'fictional-current-capability', authorize=lambda *a:None,
                                 role=lambda *a:True, event=lambda *a:True)
        access.review_task = MethodType(processing.Access.review_task, access)
        message = event(config, 'native-source', role='Reviews', task='reviews-proposer')
        message['body'] = {'review':packet}; queued(store, message)
        job = store.reserve()
        store.processing = access
        self.addCleanup(setattr, store, 'processing', None)
        store.authorize_launch = lambda *a:None  # Explicit current Board/grant seam, not an actual right.
        board = SimpleNamespace(verify_authority=lambda *a:None, bind_software_attempt=lambda *a:None)
        transport = FictionalReviewTransport(interrupted)
        runtime = service.Dispatcher(store, {'Reviews':board}, review_transport=transport)
        acquired = {'packet':packet,'repository':str(area),'source':{'fiction.txt':{'bytes':7}},
                    'method_files':policy['method_files'],'history':policy['components'][packet['component']]['history'],
                    'history_sha256':reviews.sha(b''),'prior_histories':{},'correction_diff':'','commands':[],
                    'read_authority':'owned fiction'}
        return store, runtime, job, packet, policy, acquired, transport

    def run_native_selected(self, interrupted=False):
        from coordinator_runtime import reviews, local_integration
        store, runtime, job, packet, policy, acquired, transport = self.native_fixture(interrupted)
        pending = []
        runtime.spawn = pending.append
        runtime.try_finish = lambda *a:None  # Processing consumers remain owed; this test qualifies producer custody.
        with patch.object(reviews, 'material', return_value=acquired), \
             patch.object(local_integration, 'prepare_input_basis'):
            self.assertTrue(runtime.schedule_candidate(job))
            self.assertEqual(len(pending), 1)
            asyncio.run(pending[0])
        attempt = store.job(job['id'])['active_attempt']
        return store, runtime, job, attempt, policy, transport

    def test_selected_service_native_reviews_retains_full_calls_and_exact_close_hold(self):
        from coordinator_runtime import reviews
        store, runtime, job, attempt, policy, transport = self.run_native_selected()
        row = store.attempt(attempt)
        self.assertIsNotNone(row['collected'])
        self.assertIsNone(row['error'])
        self.assertEqual(row['cleanup'], 'continuing-context-held')
        self.assertIsNone(store.one('SELECT attempt FROM oneoff_recovery WHERE attempt=?', (attempt,)))
        store.authorize_preparation(attempt)
        proof = reviews.collected_proof(store, store.job(job['id']), row)
        self.assertEqual(len(proof['calls']), 2)
        self.assertEqual(proof['calls'][0]['full_answer'], transport.answers[0])
        self.assertEqual(proof['collector'], store.controller)
        self.assertEqual(proof['run'], 'fictional-native-root')
        self.assertFalse(cleanup.eligible_event(store, oneoff.event_metadata(store, json.loads(job['members'])[0]['event'])))
        original = store.one('SELECT packet,answer FROM review_calls WHERE attempt=?', (attempt,))
        asyncio.run(runtime.reviews.close('fictional-component', policy))
        self.assertEqual(store.attempt(attempt)['cleanup'], 'done')
        self.assertEqual(store.one('SELECT packet,answer FROM review_calls WHERE attempt=?', (attempt,)), original)
        self.assertEqual(store.one('SELECT state FROM review_contexts')['state'], 'closed')
        self.assertIsNone(oneoff.event_metadata(store, json.loads(job['members'])[0]['event'])['processed_at'])
        self.assertFalse(cleanup.eligible_event(store, oneoff.event_metadata(store, json.loads(job['members'])[0]['event'])))

    def test_interrupted_native_reviews_preserves_original_and_refuses_fresh_fallback(self):
        from coordinator_runtime import reviews
        store, runtime, job, attempt, policy, transport = self.run_native_selected(interrupted=True)
        row = store.attempt(attempt)
        self.assertIsNotNone(row['error'])
        self.assertEqual(store.one('SELECT state FROM review_contexts')['state'], 'interrupted')
        retained = store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,))
        self.assertEqual(json.loads(retained['receipt'])[0]['full_answer'], transport.answers[0])
        self.assertEqual(retained['collector'], store.controller)
        count = transport.inputs
        with self.assertRaisesRegex(Refusal, 'original live context/collector unavailable'):
            asyncio.run(runtime.reviews.execute(store.job(job['id']), attempt, policy,
                                               {'component':'fictional-component'}))
        self.assertEqual(transport.inputs, count)
        self.assertEqual(store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,)), retained)
        self.assertIsNone(reviews.collected_proof(store, store.job(job['id']), row))  # No completed-call proof for an interrupted original.


class FictionalAdapter:
    async def run(self, store, attempt, prompt, spec, schema):
        store.begin(attempt, {'fictional_model_boundary':True})
        store.session(attempt, 'fictional-owned-ephemeral-session')
        outcome = {'result':result(), 'exit':0, 'capture':'complete','cleanup':'done','error':None,'detail':{}}
        oneoff.checkpoint(store, attempt, outcome, {'fictional':'no external effects'})
        return outcome


class FictionalReviewTransport:
    """Independent public response-contract fiction; never invokes a native caller."""
    def __init__(self, interrupted):
        self.interrupted, self.inputs, self.answers = interrupted, 0, []

    async def call(self, store, attempt, policy, context, directory, text, commands, opening=False, close=False):
        if close:
            return 0, self.close_receipt(), ''
        self.inputs += 1
        with store.tx():
            store.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?", (attempt,))
        if self.inputs == 1:
            store.begin(attempt, {'fictional_native_caller':True})
        if self.interrupted and self.inputs == 2:
            raise RuntimeError('fictional interrupted original second call; no substitute')
        from coordinator_runtime import reviews
        answer = encode({'semantic':'DONE','summary':'fictional source report','report':'Retain the fictional located finding.',
            'history_entry':'fictional original encounter','stage':'architecture' if self.inputs==1 else 'complete',
            'coverage':{'families':{k:'partial' for k in reviews.FAMILIES},'core_files_not_read':['fictional wider source'],
                        'observations':[],'answered_ids':[],'limits':['synthetic source and native response seams']}})
        self.answers.append(answer)
        return 0, self.answer_receipt(self.inputs-1), answer

    @staticmethod
    def answer_receipt(index):
        run = 'fictional-native-root'
        return {'class':'answered','run':run,'consumer_errors':[],
            'turn':{'input':index,'admitted':True,'answer_present':True,'linked_messages':1,
                    'ack':{'message_id':'fictional-message'},'turn_end':{'event':'turn-end','input':index,'stop_reason':'end_turn'},
                    'root_ended':None,'refused':None,'rejected':None,'ref':'fictional-original-ref'},
            'transport':{'errors':[],'attached':{'frontdoor':'attached','run':run,'backlog_dropped_total':0}},
            'collection':{'errors':[],'stdout_eof':True,'stderr_eof':True,'exit':0}}

    @staticmethod
    def close_receipt():
        return {'class':'closed','run':'fictional-native-root','physical_close':True,'root':'ended','consumer_errors':[],
                'account_errors':[],'collection':{'eof':True,'errors':[]},
                'front_door_terminal':{'run':'fictional-native-root','entry_status':87,'exit':87,'collection_errors':[],
                    'killed':False,'retire':{'ok':True,'stop':'observed'},'live':{'backlog_dropped_total':0}},
                'owner_terminal':{'status':'closed'},'async':{'errors':[],'unsettled':0,'undelivered':[]}}


class PublicInterfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        import sys
        sys.path.insert(0, str(root/'direct-child'))
        cls.dispatch = cls.load(root/'direct-child/dispatch.py', 'dispatch1077')
        cls.cleaner = cls.load(root/'codex-session-cleanup/cleanup.py', 'cleanup1077')

    @staticmethod
    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_direct_selected_capabilities_reach_actual_command_builder(self):
        args = self.dispatch.parse_args(['--cwd','/fiction','--prompt','/fiction/p',
            '--runs-dir','/fiction/r','--id','fiction','--ephemeral','--log-max-bytes','1024'])
        record = {'provider':'codex','transport':'direct','model':'fiction','effort':'high','profile_source':'explicit'}
        self.dispatch.capture_selection(args, record)
        command = self.dispatch.codex_command(args, record, '.codex2', {})
        self.assertIn('--ephemeral', command)
        self.assertEqual(command[command.index('--log-max-bytes')+1], '1024')
        self.assertRaises(self.dispatch.Refusal, self.dispatch.capture_selection, args, {**record,'transport':'native'})
        self.assertRaises(self.dispatch.Refusal, self.dispatch.capture_selection, args, {**record,'provider':'claude'})
        args.log_max_bytes = 0
        self.assertRaises(self.dispatch.Refusal, self.dispatch.capture_selection, args, record)

    def test_installed_schema_is_declaration_and_version_mismatch_still_refuses(self):
        root = Path(os.environ['ONEOFF1077_SCHEMA'])
        params = json.loads((root/'ThreadDeleteParams.json').read_text())
        response = json.loads((root/'ThreadDeleteResponse.json').read_text())
        self.assertEqual(params['required'], ['threadId'])
        self.assertEqual(response.get('properties', {}), {})
        start = json.loads((root/'ThreadStartParams.json').read_text())
        thread = json.loads((root/'ThreadStartResponse.json').read_text())['definitions']['Thread']
        from coordinator_runtime.appserver import thread_request
        from coordinator_runtime.contracts import SOL
        request = thread_request({'cwd':'/fiction','sandbox':'read-only'}, SOL)
        self.assertIs(request['ephemeral'], True)
        self.assertIn('boolean', start['properties']['ephemeral']['type'])
        self.assertNotIn('sourceParentThreadId', thread['properties'])
        self.assertRaises(Refusal, thread_request,
                          {'exact_session_after_exit':True}, SOL)
        self.assertEqual(self.cleaner.VERSION, '0.166.0')
        from types import SimpleNamespace
        with patch.object(self.cleaner.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='codex-cli 0.167.0\n')):
            self.assertRaises(self.cleaner.Refuse, self.cleaner.check_cli, 'fictional-codex')

    def test_native_option_refusal_precedes_pool_allocation_in_actual_dispatcher(self):
        import contextlib
        import io
        with patch.object(self.dispatch, 'load_config', return_value=({}, 'fictional-pin')), \
             patch.object(self.dispatch, 'resolve', return_value={'provider':'codex'}), \
             patch.object(self.dispatch, 'check_paths'), \
             patch.object(self.dispatch, 'resolve_transport', return_value={'transport':'native'}), \
             patch.object(self.dispatch.execution_pool, 'Pool') as pool, \
             contextlib.redirect_stderr(io.StringIO()):
            code = self.dispatch.main(['--cwd','/fiction','--prompt','/fiction/p',
                '--runs-dir','/fiction/r','--id','fiction','--ephemeral'])
        self.assertEqual(code, 2)
        pool.assert_not_called()


if __name__ == '__main__':
    unittest.main()
