"""Full CLI/config/Board entry in private PID/network/mount test namespaces.

/original is an immutable tracked def41 public export. All identities, records,
capabilities and peer responses are authored fiction. No live service is used.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from support import config_at
from coordinator_runtime import service
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode, ident, load_config
from coordinator_runtime.store import Store


class Withdrawal571(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='withdrawal571-', dir='/fixtures'))
        self.config = config_at(self.area)
        self.config['operator_cli'] = '/original/tools/coordinator-runtime/coordinator'
        self.config['board_library'] = '/original/tools/message-board'
        self.owner = self.config['roles']['Work']['owner']
        self.config['software_delegation'] = {'grantor': self.owner,
            'authority': 'Fictional original owner authority', 'boundary': 'new-journal-only'}
        for name in ('branch-proposer', 'reviews-proposer'):
            task = self.config['tasks'][name]
            task['repository_reads'] = ['/original']
            task['effect_authority']['operations'].append('read-source')
        self.path = self.area/'config.json'
        self.path.write_text(encode(self.config))
        # Build the entire journal with the old module closure, not new Store.
        setup = '''import json,sys
from coordinator_runtime.store import Store
from coordinator_runtime.contracts import digest,encode
c=json.load(open(sys.argv[1])); s=Store(c); owner=c['software_delegation']['grantor']
selection={'basis':{'configuration':digest(c),'implementation':{'obsolete':'old'}},'service':{},'future_intake':True,'tasks':[]}
s.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,0,NULL,0)',('fictional-stop571',encode(selection),owner))
s.db.execute("INSERT INTO processing_runs VALUES(?,?,'owned',0)",('fictional-original571','fictional-stop571'))
s.db.execute("INSERT INTO service_runs VALUES(?,?,'fictional-abstract-endpoint','serving',0,NULL,NULL)",('fictional-original571','fictional-stop571'))
s.close()
'''
        await self.child(['-c', setup, str(self.path)], old=True)
        # Real Board catalog and original public SDK acquisition; no Board mock.
        catalog = module_at(self.config['board_library'], 'catalog')
        substrate = module_at(self.config['board_library'], 'board_store')
        for role, selected in self.config['roles'].items():
            with catalog.catalog(Path(self.config['board_home'])) as conn:
                entry = catalog.create(conn, Path(self.config['board_home']), 'fictional-'+role.lower(),
                    'Owned isolated withdrawal test', board_id=selected['board_id'], temporary_test=True)
            with substrate.database(entry['db_path']) as conn:
                substrate.bind_board(conn, selected['board_id'], initialize=True)
            Board(self.config, role)
        self.key = 'fictional-stop571'
        self.store = Store(self.config, read_only=True)
        self.addCleanup(self.store.close)
        self.requests = []
        self.reply = {'controller':'fictional-original571',
            'state':'draining; parent still owes this original numeric END'}
        self.server = await asyncio.start_unix_server(self.handle, service.endpoint(self.store, self.key))
        self.handlers = []

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.handlers.append(task)
        try:
            self.requests.append(json.loads(await reader.readline()))
            if self.reply is not None:
                writer.write((encode(self.reply)+'\n').encode())
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()
        if self.handlers:
            await asyncio.gather(*self.handlers)

    async def child(self, argv, *, old=False, actor=None, expected=0):
        env = dict(os.environ)
        env['PYTHONPATH'] = '/original/tools/coordinator-runtime' if old else '/src/tools/coordinator-runtime'
        env['CODEX_SESSION_ID'] = actor or self.owner
        p = await asyncio.create_subprocess_exec(sys.executable, *argv, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(p.communicate(), 10)
        record = {'argv':argv, 'END':p.returncode, 'stdout':stdout.decode(), 'stderr':stderr.decode()}
        with (self.area/'originals.jsonl').open('a') as out:
            out.write(encode(record)+'\n')
        self.assertEqual(p.returncode, expected, record)
        return json.loads(stdout) if stdout else None

    async def invoke(self, operation='stop', *, actor=None, component=None, expected=0):
        argv = ['/src/tools/coordinator-runtime/coordinator', '--config', str(self.path),
                'processing-service-control', self.key, operation]
        if component is not None:
            argv.extend(['--component', component])
        return await self.child(argv, actor=actor, expected=expected)

    def journal(self):
        with sqlite3.connect(self.store.path) as conn:
            return '\n'.join(conn.iterdump())

    async def test_full_real_cli_loads_original_config_and_sdk_without_restamping_or_writes(self):
        with self.assertRaisesRegex(Refusal, 'exact release repository'):
            load_config(str(self.path))
        self.assertEqual(load_config(str(self.path), withdrawal_only=True), self.config)
        before, config_bytes = self.journal(), self.path.read_bytes()
        answer = await self.invoke()
        self.assertEqual(self.requests, [{'capability':self.key, 'operation':'stop'}])
        self.assertIsNone(answer['process_END'])
        self.assertFalse(answer['processing_complete'])
        self.assertIn('not established', answer['release_currentness'])
        self.assertEqual(self.journal(), before)
        self.assertEqual(self.path.read_bytes(), config_bytes)
        self.assertEqual(self.store.db.total_changes, 0)
        self.assertNotIn('CREATE TABLE work_read_fences', before)

    async def test_nonstop_and_component_controls_keep_normal_config_validation(self):
        for op in ('status', 'recover', 'close-review'):
            answer = await self.invoke(op, expected=2)
            self.assertIn('exact release repository', answer['error'])
        answer = await self.invoke(component='fictional-component', expected=2)
        self.assertIn('exact release repository', answer['error'])
        self.assertEqual(self.requests, [])

    async def test_original_repository_reference_is_still_validated(self):
        altered = copy.deepcopy(self.config)
        altered['tasks']['branch-proposer']['repository_reads'] = ['/unrelated']
        self.path.write_text(encode(altered))
        answer = await self.invoke(expected=2)
        self.assertIn('exact release repository', answer['error'])
        self.assertEqual(self.requests, [])

    async def test_writing_source_task_is_not_waived_for_withdrawal(self):
        altered = copy.deepcopy(self.config)
        altered['tasks']['branch-proposer']['effect_authority']['write_roots'] = ['/fixtures']
        self.path.write_text(encode(altered))
        answer = await self.invoke(expected=2)
        self.assertIn('exact release repository', answer['error'])
        self.assertEqual(self.requests, [])

    async def test_wrong_actual_actor_cannot_reach_endpoint(self):
        # Existing SDK reports UserError outside the CLI's structured Refusal
        # family. Preserve actual END1; no response or stop effect is inferred.
        await self.invoke(actor=ident(), expected=1)
        self.assertEqual(self.requests, [])

    async def test_revoked_capability_and_changed_configuration_refuse_before_send(self):
        with sqlite3.connect(self.store.path) as conn:
            conn.execute('UPDATE processing_capabilities SET revoked=1')
        answer = await self.invoke(expected=2)
        self.assertIn('unrevoked', answer['error'])
        self.assertEqual(self.requests, [])
        with sqlite3.connect(self.store.path) as conn:
            conn.execute('UPDATE processing_capabilities SET revoked=NULL')
        altered = copy.deepcopy(self.config)
        altered['limits']['max_events'] += 1
        self.path.write_text(encode(altered))
        answer = await self.invoke(expected=2)
        self.assertIn('journal', answer['error'])
        self.assertEqual(self.requests, [])

    async def test_lost_or_wrong_reply_preserves_possible_stop_uncertainty(self):
        before = self.journal()
        self.reply = None
        answer = await self.invoke(expected=2)
        self.assertIn('JSONDecodeError', answer['error'])
        self.assertEqual(len(self.requests), 1)  # No automatic retry.
        self.assertNotIn('process_END', answer)
        self.assertEqual(self.journal(), before)
        self.reply = {'controller':'foreign', 'state':'draining; parent still owes this original numeric END'}
        answer = await self.invoke(expected=2)
        self.assertIn('unknown', answer['error'])
        self.assertEqual(len(self.requests), 2)  # Distinct selected test call.
        self.assertEqual(self.journal(), before)


if __name__ == '__main__':
    unittest.main()
