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
        if self._testMethodName != 'test_dispatcher_reaches_all_four_role_producers_and_restart_recovers':
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
