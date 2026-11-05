"""Source-only recovery controls. All accounts/results/authority are fiction.

Real owned stdio children, Unix sockets and WAL locks execute in the isolated
fixture namespace. No model semantic inference or actual service is exercised.
"""
import asyncio
import contextlib
import copy
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event
from coordinator_runtime import cli, processing, service
from coordinator_runtime.appserver import AppServer, Peer
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


class Startup(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.config = config_at(self.area)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)

    def adapter(self, plan):
        path = self.area / ('plan-' + str(len(list(self.area.glob('plan-*')))) + '.json')
        path.write_text(encode(plan))
        return AppServer(self.config, [sys.executable, str(Path(__file__).with_name('fixture_appserver.py')), str(path)])

    async def test_same_timeout_label_identifies_each_new_RPC_stage_without_inventing_old_stage(self):
        original_rpc = Peer.rpc
        async def short_rpc(peer, method, params, timeout=20):
            return await original_rpc(peer, method, params, timeout=.15)
        for method in ('initialize', 'config/read', 'thread/start', 'turn/start'):
            with self.subTest(method=method):
                # This test's configuration is bound before each fresh journal.
                area = Path(tempfile.mkdtemp(dir='/fixtures'))
                config = config_at(area)
                config['session_storage'] = {'mode': 'producer-owned'}
                store = enrolled(config)
                self.addCleanup(store.close)
                message = event(config, method)
                store.ingest(message)
                attempt, _ = store.claim_classification()
                settings = {'features': {'shell_snapshot': False}, 'feedback': {'enabled': False},
                            'history': {'persistence': 'none'}}
                path = area / 'plan.json'
                path.write_text(encode({'stall_rpc': method, 'storage_config': settings}))
                adapter = AppServer(config, [sys.executable, str(Path(__file__).with_name('fixture_appserver.py')), str(path)])
                with patch.object(Peer, 'rpc', short_rpc):
                    outcome = await adapter.run(store, attempt, 'fictional classifier input',
                                                {'cwd': str(area), 'sandbox': 'read-only'})
                self.assertEqual(outcome['error'], 'adapter error: TimeoutError')
                self.assertEqual(outcome['exit'], 0)
                self.assertIsNone(outcome['result'])
                progress = outcome['detail']['protocol_progress']
                failures = [p for p in progress if p['state'] == 'timeout']
                self.assertEqual([p['method'] for p in failures], [method])
                self.assertTrue(all(type(p['elapsed_ms']) is int and p['elapsed_ms'] >= 0 for p in progress))
                public_fields = {'method', 'state', 'elapsed_ms', 'failure', 'sequence', 'budget_ms',
                                 'exchange_entered_ms', 'send_drain_ms', 'correlated_reply_ms',
                                 'cancellation_delivered_ms', 'boundary', 'budget_overrun_ms', 'observation_sequence'}
                self.assertTrue(all(set(p) <= public_fields for p in progress))
                for p in progress:
                    self.assertTrue(all(type(value) is int and value >= 0 for key, value in p.items()
                                        if key.endswith('_ms') or key == 'sequence'))
                self.assertEqual(failures[0]['boundary'], 'awaiting-response')
                self.assertIn('send_drain_ms', failures[0])
                self.assertNotIn('correlated_reply_ms', failures[0])
                expected = 'not-requested' if method in {'initialize', 'config/read'} else (
                    'requested-uncertain' if method == 'thread/start' else 'owned-root-observed')
                self.assertEqual(outcome['detail']['thread_start'], expected)
                print('STARTUP_RPC_OBSERVATION=' + encode({'fixture': method, 'exit': outcome['exit'],
                    'error': outcome['error'], 'capture': outcome['capture'], 'thread_start': expected,
                    'progress': progress}))
                store.collect(attempt, outcome)
                with self.assertRaises(Refusal): store.commit_classification(attempt)
                self.assertEqual(store.one('SELECT ack FROM events')['ack'], 'pending')

    async def test_typed_proposer_and_integrator_selections_and_invalid_output_consequences(self):
        cases = [('propose', 'work-proposer'), ('integrate', 'work-integrator'),
                 ('unparsed', None), ('wrong-event', None), ('unauthorized-task', None)]
        for label, task in cases:
            with self.subTest(label=label):
                message = event(self.config, label)
                message.update(body='fictional ' + label, allowed_tasks=['work-proposer', 'work-integrator'])
                self.store.ingest(message)
                attempt, actual = self.store.claim_classification()
                answer = {'event_id': actual['id'], 'task': task or 'work-integrator', 'package': None,
                          'reason': 'fixture-selected proposal or integration meaning'}
                plan = {'result': answer}
                if label == 'unparsed': plan['raw_final'] = 'not JSON'
                if label == 'wrong-event': answer['event_id'] = 'fictional-other-event'
                if label == 'unauthorized-task': answer['task'] = 'arbitrary-shell'
                dispatcher = Dispatcher(self.store, models=self.adapter(plan), boards={})
                await dispatcher.classify(attempt, actual)
                row = self.store.one('SELECT * FROM events WHERE id=?', (message['id'],))
                recorded = self.store.attempt(attempt)
                self.assertEqual(recorded['exit'], 0)
                if task:
                    self.assertEqual(json.loads(row['classification'])['task'], task)
                    self.assertEqual(self.store.one('SELECT task FROM queue WHERE event=?', (message['id'],))['task'], task)
                    self.assertIsNone(recorded['error'])
                else:
                    self.assertEqual(row['state'], 'classification-held')
                    self.assertEqual(row['ack'], 'pending')
                    self.assertIsNone(self.store.one('SELECT * FROM queue WHERE event=?', (message['id'],)))
                    self.assertTrue(row['error'])
                print('ROUTING_OBSERVATION=' + encode({'fixture': label, 'exit': recorded['exit'],
                    'state': row['state'], 'ack': row['ack'], 'selected_task': task,
                    'adapter_error': recorded['error'], 'classification_error': row['error']}))
                # Do not let this deliberately held event become the next case.
                self.store.db.execute("UPDATE events SET hold='fixture independent-case fence' WHERE id=?", (message['id'],))


class Control(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.config = config_at(self.area)
        self.config['software_delegation'] = {'grantor': 'fictional-Work-owner'}
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.key = 'fictional-service-capability'
        selection = {'basis': {'configuration': digest(self.config), 'implementation': processing.implementation()},
                     'service': {'max_inflight': 3, 'reviews': {}, 'legacy_resources': {}},
                     'future_intake': True, 'tasks': []}
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,0,NULL,0)',
                              (self.key, encode(selection), 'fictional-Work-owner'))
        self.actor_calls = []
        outer = self
        class Board:
            def __init__(self, config=None, role=None):
                self.store = SimpleNamespace(acting_session=self.acting_session)
            def acting_session(self, actor):
                outer.actor_calls.append(actor)
                if actor != 'fictional-Work-owner': raise Refusal('fictional actor mismatch')
                return actor  # Explicit identity seam; no native session environment is set.
            def verify_authority(self, runtime): return {'fictional': True}
        self.board_type = Board

    def invoke(self, key=None, operation='status'):
        output = io.StringIO()
        with patch.object(cli, 'load_config', return_value=self.config), patch.object(
                processing, 'ProcessingBoard', self.board_type), contextlib.redirect_stdout(output):
            code = cli.main(['--config', 'fictional-config', 'processing-service-control', key or self.key, operation])
        return code, json.loads(output.getvalue())

    def test_normal_CLI_controls_reach_original_during_owned_worker_and_WAL_write_activity(self):
        async def check():
            worker_ready = asyncio.Event()
            worker_codes = []
            async def activity(dispatcher, emit):
                child = await asyncio.create_subprocess_exec(sys.executable, '-c',
                    "import sys; print('fixture ready',flush=True); sys.stdin.read()",
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
                self.assertEqual(await child.stdout.readline(), b'fixture ready\n')
                worker_ready.set()
                try:
                    await dispatcher.stopping.wait()
                finally:
                    child.stdin.close()
                    worker_codes.append(await child.wait())
            with patch.object(service.Dispatcher, 'run', activity), patch.object(
                    service.Dispatcher, 'recover_originals', lambda d: {'collector': d.store.controller,
                    'uncollected': [], 'fictional_workflow_tick_seam': True}):
                original = asyncio.create_task(service.serve(self.store, {'Work': self.board_type()}, self.key,
                                                             lambda value: None, models=object()))
                await asyncio.wait_for(worker_ready.wait(), 2)
                blocker = sqlite3.connect(self.store.path, isolation_level=None)
                blocker.execute('BEGIN IMMEDIATE')
                try:
                    started = time.monotonic()
                    code, observed = await asyncio.to_thread(self.invoke)
                    duration = time.monotonic() - started
                    self.assertEqual(code, 0, observed)
                    self.assertEqual(observed['runs'][0]['controller'], self.store.controller)
                    self.assertIsNone(observed['runs'][0]['returned'])
                    self.assertLess(duration, 2, 'isolated fixture deadline, not a production SLA')
                    self.assertFalse(original.done())
                    self.assertEqual(worker_codes, [])
                    stop_started = time.monotonic()
                    code, stopped = await asyncio.to_thread(self.invoke, operation='stop')
                    stop_duration = time.monotonic() - stop_started
                    self.assertEqual(code, 0, stopped)
                    self.assertIn('draining', stopped['state'])
                    self.assertEqual(blocker.in_transaction, True)
                    print('CONTROL_OBSERVATION=' + encode({'status_exit': 0, 'status_seconds': duration,
                        'stop_exit': code, 'stop_seconds': stop_duration, 'writer_transaction_open': True,
                        'worker_exit_before_stop': None, 'workflow_ticks': 'explicit fixture seam'}))
                finally:
                    blocker.rollback()
                    blocker.close()
                    # Ensure baseline failures also drain the exact original.
                    if not original.done(): await service.control(self.store, self.key, 'stop')
                    await asyncio.wait_for(original, 2)
                self.assertEqual(worker_codes, [0])
                self.assertEqual(self.actor_calls, ['fictional-Work-owner', 'fictional-Work-owner'])
        asyncio.run(check())

    def test_control_view_refuses_missing_changed_revoked_source_and_actor_before_socket(self):
        with patch.object(service, 'control', side_effect=AssertionError('must refuse before socket')):
            changed = copy.deepcopy(self.config)
            self.config['enabled'] = True
            self.assertEqual(self.invoke()[0], 2)
            self.config.clear(); self.config.update(changed)
            self.assertEqual(self.invoke('fictional-absent-capability')[0], 2)
            self.store.db.execute('UPDATE processing_capabilities SET revoked=1')
            self.assertEqual(self.invoke()[0], 2)
            self.store.db.execute('UPDATE processing_capabilities SET revoked=NULL')
            row = self.store.one('SELECT selection FROM processing_capabilities')
            selected = json.loads(row['selection']); selected['basis']['implementation'] = {}
            self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(selected),))
            self.assertEqual(self.invoke()[0], 2)
            self.store.db.execute('UPDATE processing_capabilities SET selection=?', (row['selection'],))
            with patch.object(self.board_type, 'acting_session', side_effect=Refusal('fictional actor mismatch')):
                self.assertEqual(self.invoke()[0], 2)
        absent = copy.deepcopy(self.config); absent['state_dir'] = str(self.area / 'never-created')
        with self.assertRaises((Refusal, OSError)): Store(absent, read_only=True)
        self.assertFalse(Path(absent['state_dir']).exists())
        view = Store(self.config, read_only=True)
        try:
            with self.assertRaises(sqlite3.OperationalError): view.db.execute("INSERT INTO meta VALUES('forbidden','write')")
        finally:
            view.close()


if __name__ == '__main__':
    unittest.main()
