"""Real release pins/CLI/old endpoint in positive mounts; all authority is fiction.

The Board identity seam calls the real actual_actor checker with a fictional
UUID, never a native membership/provider. Dispatcher work is an explicit seam;
an owned stdio child must actually exit before the fictional service returns.
Run the same tests against immutable def41 to preserve the failed correction.
"""
import asyncio
import contextlib
import copy
import io
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event
from coordinator_runtime import cli, configuration, processing, processing_admission, service
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.store import Store


class OwnedDrain555(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(dir='/fixtures', prefix='drain555-'))
        self.config = config_at(self.area)
        self.owner = self.config['roles']['Work']['owner']
        self.key = 'fictional-service555'
        self.config['software_delegation'] = {'grantor': self.owner}
        self.config['operator_cli'] = '/src/tools/coordinator-runtime/coordinator'
        self.config['operator_config'] = str(self.area / 'operator.json')
        self.config['board_library'] = '/src/tools/message-board'
        self.config['control_receive'] = {'instructions': '/src/tools/coordinator-runtime/templates/coordinator-receive.md'}
        self.config['artifact_exclusions'] = [str(self.area / 'opaque-capture')]
        self.bounds = self.area / 'public-bounds.md'
        self.bounds.write_text('Fictional inherited exclusions remain in force.\n')
        self.config['tasks']['work-proposer']['templates'].append(str(self.bounds))
        Path(self.config['operator_config']).write_text(encode(self.config))
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.release = configuration.release(self.store, self.config)
        binding = digest(self.config)
        self.store.db.execute('INSERT INTO configuration_transitions VALUES(1,?,?,?,?,?,?,0)',
            (binding, binding, binding, encode(self.config), encode({'basis': {'release': self.release}}), self.owner))
        self.selection = {'basis': {'configuration': binding, 'implementation': processing.implementation()},
                          'service': {'max_inflight': 1, 'reviews': {}, 'legacy_resources': {}},
                          'future_intake': True, 'tasks': []}
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,0,NULL,0)',
                              (self.key, encode(self.selection), self.owner))
        source = event(self.config, 'conserved555')
        self.store.ingest(source)
        self.store.db.execute("UPDATE events SET ack='done',hold='fictional source/effect uncertainty'")
        self.store.db.execute("UPDATE enrollments SET intake=0,legacy_hold='fictional retained resources555'")
        self.ready, self.stopped, self.finish = asyncio.Event(), asyncio.Event(), asyncio.Event()
        self.worker_exits, self.messages = [], []
        outer = self

        class Board:
            def __init__(self, *args):
                self.store = SimpleNamespace(acting_session=cli.actual_actor)
            def verify_authority(self, runtime):
                return {'fixture_only': True}
        self.board_type = Board
        self.serving_module = service
        old_service = os.environ.get('COORDINATOR_DRAIN555_OLD_SERVICE')
        if old_service:
            # Caller supplies one immutable public source file, never discovery.
            spec = importlib.util.spec_from_file_location('coordinator_runtime.fixture_def41_service555', old_service)
            self.serving_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.serving_module)

        async def run(dispatcher, emit):
            # Real OS child, owned by this exact coroutine, with held stdin.
            child = await asyncio.create_subprocess_exec(sys.executable, '-c',
                "import sys; print('ready', flush=True); sys.stdin.read()",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
            try:
                outer.assertEqual(await child.stdout.readline(), b'ready\n')
                outer.ready.set()
                await dispatcher.stopping.wait()
                outer.stopped.set()
                await outer.finish.wait()
            finally:
                child.stdin.close()
                outer.worker_exits.append(await child.wait())
        self.enterContext(patch.object(self.serving_module.Dispatcher, 'run', run))
        self.enterContext(patch.object(self.serving_module.Dispatcher, 'recover_originals',
            lambda d: {'collector': d.store.controller, 'uncollected': [], 'fixture_work_seam': True}))
        # Synthetic identity is confined to this isolated test interpreter.
        self.enterContext(patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}))
        self.original = None

    async def asyncTearDown(self):
        if self.original:
            self.finish.set()
            if not self.original.done():
                # Own test-only teardown, including immutable-baseline failures.
                await service.control(self.store, self.key, 'stop')
            await asyncio.wait_for(self.original, 3)

    def invoke(self, operation='stop', key=None, component=None):
        output = io.StringIO()
        argv = ['--config', self.config['operator_config'], 'processing-service-control', key or self.key, operation]
        if component is not None:
            argv.extend(['--component', component])
        # Config shape/native Board validation are explicit seams. Release
        # acquisition, currentness, actor checking, Store and socket are real.
        with patch.object(cli, 'load_config', return_value=self.config), patch.object(
                processing, 'ProcessingBoard', self.board_type), contextlib.redirect_stdout(output):
            code = cli.main(argv)
        return code, json.loads(output.getvalue())

    async def start(self):
        self.original = asyncio.create_task(self.serving_module.serve(self.store, {'Work': self.board_type()}, self.key,
                                                          self.messages.append, models=object()))
        await asyncio.wait_for(self.ready.wait(), 3)

    def change_dependency(self):
        self.bounds.write_text(self.bounds.read_text() + 'Additional fictional capture privacy hold; never remove.\n')
        self.assertNotEqual(configuration.release(self.store, self.config), self.release)
        with self.assertRaisesRegex(Refusal, 'selected public release/dependencies changed'):
            processing.Access(self.store, self.key).current()

    def conserved(self):
        return {t: self.store.rows('SELECT * FROM ' + t) for t in
                ('events', 'queue', 'outboxes', 'enrollments', 'admissions', 'attempts',
                 'configuration_transitions', 'processing_capabilities', 'processing_runs', 'service_runs')}

    async def test_changed_real_dependency_owner_drains_without_release_or_END_claim(self):
        await self.start()
        self.change_dependency()
        before = self.conserved()
        for op in ('status', 'recover', 'close-review'):
            code, answer = await asyncio.to_thread(self.invoke, op)
            self.assertEqual(code, 2, answer)
            self.assertIn('selected public release/dependencies changed', answer['error'])
        blocker = sqlite3.connect(self.store.path, isolation_level=None)
        blocker.execute('BEGIN IMMEDIATE')
        try:
            code, answer = await asyncio.wait_for(asyncio.to_thread(self.invoke), 3)
            self.assertEqual(code, 0, answer)
            await asyncio.wait_for(self.stopped.wait(), 1)
            self.assertTrue(blocker.in_transaction)
            self.assertEqual(answer['controller'], self.store.controller)
            self.assertIn('draining', answer['state'])
            self.assertIsNone(answer['process_END'])
            self.assertFalse(answer['processing_complete'])
            self.assertIn('not established', answer['release_currentness'])
            self.assertFalse(self.original.done())
            self.assertEqual(self.worker_exits, [])
            self.assertEqual(before, self.conserved())
            self.assertIn('Additional fictional capture privacy hold', self.bounds.read_text())
            self.assertNotIn('software_admission', json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection']))
            self.assertTrue(all(row['intake'] == 0 and row['legacy_hold'] for row in self.store.rows('SELECT * FROM enrollments')))
        finally:
            blocker.rollback()
            blocker.close()
        # Only actual wait on this fixture's owned child establishes its exit.
        self.finish.set()
        await asyncio.wait_for(self.original, 3)
        self.assertEqual(self.worker_exits, [0])
        self.assertEqual(self.store.one('SELECT state FROM service_runs')['state'], 'returned-awaiting-parent-END')
        self.assertEqual(self.store.one('SELECT state FROM processing_runs')['state'], 'owned')
        code, answer = await asyncio.to_thread(self.invoke)
        self.assertEqual(code, 2, answer)  # Returned is neither serving nor parent END.

    async def test_unchanged_release_owner_stop_still_works(self):
        await self.start()
        code, answer = await asyncio.to_thread(self.invoke)
        self.assertEqual(code, 0, answer)
        self.assertIn('draining', answer['state'])

    async def test_changed_implementation_cannot_authorize_work_but_owner_can_stop(self):
        await self.start()
        selection = copy.deepcopy(self.selection)
        selection['basis']['implementation'] = {'obsolete-fixture-source.py': '0' * 64}
        self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(selection),))
        with self.assertRaisesRegex(Refusal, 'source/configuration changed'):
            processing.Access(self.store, self.key).current()
        code, answer = await asyncio.to_thread(self.invoke)
        self.assertEqual(code, 0, answer)

    async def test_stop_does_not_admit_source_reserve_launch_or_create_report(self):
        await self.start()
        self.change_dependency()
        before = self.conserved()
        access = self.store.processing = processing.Access(self.store, self.key)
        checks = [lambda: access.event({'id': 'fictional-new-source555'}),
                  lambda: access.task({'task': 'work-proposer'}),
                  lambda: access.reserve(None, None, None),
                  lambda: access.authorize({'detail': '{}'}),
                  lambda: processing_admission.admit(self.store, 'fictional-source555'),
                  lambda: service.ingest_report(self.store, self.owner, 'fictional-report555', {})]
        for check in checks:
            with self.assertRaisesRegex(Refusal, 'selected public release/dependencies changed'):
                check()
        code, answer = await asyncio.to_thread(self.invoke)
        self.assertEqual(code, 0, answer)
        for check in checks:
            with self.assertRaisesRegex(Refusal, 'selected public release/dependencies changed'):
                check()
        self.assertEqual(before, self.conserved())

    async def test_identity_capability_revocation_config_and_run_refusals_precede_socket(self):
        await self.start()
        self.change_dependency()
        # All negatives must refuse before even opening the original endpoint.
        with patch.object(asyncio, 'open_unix_connection', side_effect=AssertionError('no endpoint acquisition')):
            for actor in ('', '00000000-0000-4000-8000-000000000555'):
                with patch.dict(os.environ, {'CODEX_SESSION_ID': actor}):
                    self.assertEqual((await asyncio.to_thread(self.invoke))[0], 2)
            self.assertEqual((await asyncio.to_thread(self.invoke, key='absent555'))[0], 2)
            self.assertEqual((await asyncio.to_thread(self.invoke, component='unrelated555'))[0], 2)
            statements = [
                ("UPDATE processing_capabilities SET revoked=1", "UPDATE processing_capabilities SET revoked=NULL"),
                ("UPDATE processing_capabilities SET issuer='foreign555'", "UPDATE processing_capabilities SET issuer=?", (self.owner,)),
                ("UPDATE processing_runs SET state='released'", "UPDATE processing_runs SET state='owned'"),
                ("UPDATE service_runs SET returned=1", "UPDATE service_runs SET returned=NULL"),
                ("UPDATE service_runs SET capability='foreign555'", "UPDATE service_runs SET capability=?", (self.key,)),
            ]
            for statement in statements:
                with self.subTest(statement=statement[0]):
                    self.store.db.execute(statement[0])
                    self.assertEqual((await asyncio.to_thread(self.invoke))[0], 2)
                    self.store.db.execute(statement[1], statement[2] if len(statement) == 3 else ())
            for selection in ({**self.selection, 'service': None}, {**self.selection, 'basis': {'configuration': 'obsolete'}}):
                # A finite capability is not extended into a service.
                self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(selection),))
                self.assertEqual((await asyncio.to_thread(self.invoke))[0], 2)
                if selection.get('service') is None:
                    selection.pop('service')
                    self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(selection),))
                    self.assertEqual((await asyncio.to_thread(self.invoke))[0], 2)
            self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(self.selection),))
            changed = copy.deepcopy(self.config)
            self.config['enabled'] = True
            self.assertEqual((await asyncio.to_thread(self.invoke))[0], 2)
            self.config.clear(); self.config.update(changed)

    async def test_peer_wrong_UID_or_late_revocation_refuses_before_send(self):
        # No real endpoint: transport seam distinguishes connect from sending.
        await self.start()
        self.change_dependency()
        writer = SimpleNamespace(get_extra_info=lambda key: SimpleNamespace(getsockopt=lambda *a: struct.pack('3i', 1, os.getuid() + 1, 1)),
                                 write=lambda b: self.fail('must not send'), close=lambda: None,
                                 wait_closed=self.noop)
        async def connect(*args, **kwargs):
            return None, writer
        with patch.object(asyncio, 'open_unix_connection', connect):
            self.assertEqual((await asyncio.to_thread(self.invoke))[0], 2)
        async def revoke_on_connect(*args, **kwargs):
            self.store.db.execute('UPDATE processing_capabilities SET revoked=1')
            writer.get_extra_info = lambda key: SimpleNamespace(getsockopt=lambda *a: struct.pack('3i', 1, os.getuid(), 1))
            return None, writer
        # Use direct operate in the event-loop thread so SQLite stays owned.
        with patch.object(asyncio, 'open_unix_connection', revoke_on_connect):
            with self.assertRaises(Refusal):
                await service.control(self.store, self.key, 'stop', stop_owner=self.owner)

    async def noop(self):
        pass

    async def test_bad_reply_is_uncertain_failure_and_never_success_or_END(self):
        # Recorded original exists, but a fictional endpoint returns bad identity.
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,0)', ('original555', self.key, 'owned'))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,0,NULL,NULL)',
                              ('original555', self.key, service.endpoint(self.store, self.key), 'serving'))
        self.change_dependency()
        for response in ({'controller': 'foreign555', 'state': 'draining; parent still owes this original numeric END'}, {'error': 'stop refused'},
                         {'controller': 'original555', 'state': 'returned'}, []):
            async def connection(reader, writer):
                request = json.loads(await reader.readline())
                self.assertEqual(request, {'capability': self.key, 'operation': 'stop'})
                writer.write((encode(response) + '\n').encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            server = await asyncio.start_unix_server(connection, path=service.endpoint(self.store, self.key))
            try:
                code, answer = await asyncio.to_thread(self.invoke)
                self.assertEqual(code, 2, answer)
                self.assertIn('acknowledgement absent/mismatched', answer['error'])
            finally:
                server.close()
                await server.wait_closed()
        self.assertEqual(self.store.one('SELECT state FROM processing_runs')['state'], 'owned')


if __name__ == '__main__':
    unittest.main()
