"""Current cooperating creation, original continuation and evidence-gap controls.

Only owned fixture processes run. Authority callbacks, public control files,
SQLite and capture are real mechanisms; provider/method replies are fiction.
"""
import asyncio
from contextlib import asynccontextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from coordinator_runtime import opaque_review
from coordinator_runtime.appserver import Originals
from coordinator_runtime.execution_pool import ExecutionPool
from coordinator_runtime.contracts import Refusal
from test_opaque_review1157 import public_module, THREAD
import run_opaque_review1157 as historical


def usable():
    path=Path(__file__).parents[1]/'qualify_opaque_usable1172.py'
    spec=importlib.util.spec_from_file_location('composed_qualification1183',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


class CurrentCallers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.home=Path(tempfile.mkdtemp(prefix='composition1183-',dir=os.environ['ONEOFF1077_FIXTURES']))
        self.routes=self.home/'routes.toml'
        self.routes.write_text('[rotation]\nstate_dir = '+json.dumps(str(self.home/'control'))+
            '\n[providers.codex]\npool = [".codex2", ".codex3", ".codex4", ".codex5"]\n'+
            'manual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n')
        self.pool=ExecutionPool(dict(profiles=['.codex','.codex2','.codex3','.codex4','.codex5'],
            deadlines={'bind':1},execution_pool_routes=str(self.routes)))
        self.module=public_module(); self.originals=Originals(); self.ends=[];self.argv=[]
        self.authorized=True;self.checks=0
        self.owner=self.module.Context(self.home/'context','.codex2','original',30,self.originals,
            executable='/usr/bin/false')
        self.spawn=asyncio.create_subprocess_exec

    def authority(self):
        self.checks+=1
        if not self.authorized:raise Refusal('current invoking authority revoked')

    async def standin(self,*argv,**kwargs):
        self.argv.append((argv,kwargs.pop('env')))
        events=[dict(type='thread.started',thread_id=THREAD),
                dict(type='item.completed',item=dict(type='error',message='fixture warning')),
                dict(type='item.completed',item=dict(type='agent_message',text='fictional answer')),
                dict(type='turn.completed')]
        body='import sys\nsys.stdin.read()\n'+'\n'.join('print('+repr(json.dumps(e))+',flush=True)' for e in events)
        return await self.spawn(sys.executable,'-c',body,**kwargs)

    async def turn(self,name,**options):
        return await opaque_review.qualification_turn(self.owner,self.pool,self.home/name,
            [('history',b'nonsecret current fixture')],'fixture',current_authority=self.authority,
            publish=self.ends.append,maximum=4096,capture_max=8192,shutdown=.1,**options)

    async def test_creation_and_original_continuation_preserve_dependency_diagnostics_and_custody(self):
        with patch('asyncio.create_subprocess_exec',side_effect=self.standin):
            first=await self.turn('first'); created=self.owner.created
            self.pool.pool.set([])
            second=await self.turn('continued')
        self.assertTrue(first[1]['answered']);self.assertTrue(second[1]['answered'])
        self.assertEqual(len(first[1]['diagnostics']),1)
        self.assertTrue(all(r['capture_complete'] for r in [first[1],second[1]]))
        self.assertEqual([e['exit'] for e in self.ends],[0,0]);self.assertFalse(self.originals.owned)
        self.assertEqual(self.owner.created,created);self.assertEqual(self.owner.profile,'.codex2')
        self.assertEqual(self.argv[1][0][self.argv[1][0].index('resume')+1],THREAD)
        self.assertEqual([v[0][0] for v in self.argv],['/usr/bin/false']*2)
        self.assertEqual([v[1]['CODEX_HOME'] for v in self.argv],['/home/nes/.codex2']*2)
        self.authorized=False
        with self.assertRaisesRegex(Refusal,'revoked'):await self.turn('revoked')
        self.assertFalse((self.home/'revoked').exists())
        self.assertTrue(self.owner.close('original')['local_owner_closed'])

    async def test_hot_removal_after_export_is_fenced_at_actual_creation(self):
        export=self.module.export
        def remove(*args):
            value=export(*args);self.pool.pool.set(['.codex3','.codex4','.codex5']);return value
        spawn=AsyncMock(side_effect=AssertionError('disabled original must never spawn'))
        with patch.object(self.module,'export',side_effect=remove),patch('asyncio.create_subprocess_exec',spawn):
            with self.assertRaisesRegex(Refusal,'disabled'):await self.turn('removed-during-preparation')
        spawn.assert_not_called();self.assertFalse(self.originals.owned)
        self.assertEqual(self.owner.state,'interrupted')

    async def test_removed_codex_is_refused_at_both_actual_qualification_entrypoints(self):
        caller=usable();spawn=AsyncMock(side_effect=AssertionError('removed profile cannot start'))
        with patch('asyncio.create_subprocess_exec',spawn):
            value=await historical.actual(self.home,'.codex',executable='/usr/bin/false',
                pool=self.pool,current_authority=self.authority)
            self.assertEqual(value['pending_originals'],0)
            self.assertFalse(value['turns'])
            area=self.home/'usable-removed';area.mkdir()
            with patch.multiple(caller,ROOT=area,EXE='/usr/bin/false',PROFILE='.codex',COLLECTOR='current'):
                await caller.actual(pool=self.pool,current_authority=self.authority)
            value=json.loads((area/'actual1172.json').read_text())
            self.assertEqual(value['pending_originals'],0);self.assertFalse(value['turns'])
        spawn.assert_not_called()

    async def test_both_actual_entrypoints_reach_owned_capture_and_refuse_assertion_only_protection(self):
        # Exact emitted command/source/audit claims are still only assertions.
        # This stand-in performs no denied operations and must never unlock method input.
        calls=[]
        async def assertions(*argv,**kwargs):
            calls.append(argv);env=kwargs.pop('env');directory=Path(env['TMPDIR']).parent
            nonce=(directory/'material/0000.txt').read_text()
            if (directory/'material/0001.txt').exists():
                command='/usr/bin/python3 '+str(directory/'material/0001.txt')
                output=dict(allowed=nonce,read={'errno':13},write={'errno':13},
                    material_write={'errno':30},network={'errno':13},
                    audit_events=['open']*4+['socket.__new__','socket.connect'])
            else:
                command='/usr/bin/python3 -c fixture'
                output=dict(allowed=nonce,denied_read=13,denied_write=30,denied_network=13)
            events=[dict(type='thread.started',thread_id=THREAD),
                dict(type='item.completed',item=dict(type='command_execution',command=command,
                    exit_code=0,aggregated_output=json.dumps(output))),
                dict(type='item.completed',item=dict(type='agent_message',text='fictional boundary answer')),
                dict(type='turn.completed')]
            body='import sys\nsys.stdin.read()\n'+'\n'.join('print('+repr(json.dumps(e))+',flush=True)' for e in events)
            return await self.spawn(sys.executable,'-c',body,**kwargs)
        caller=usable()
        with patch('asyncio.create_subprocess_exec',side_effect=assertions):
            value=await historical.actual(self.home,'.codex2',executable='/usr/bin/false',
                pool=self.pool,current_authority=self.authority)
            self.assertEqual(value['original_numeric_ENDs'],[0]);self.assertEqual(value['pending_originals'],0)
            self.assertIn('independent applicable operation evidence',value['gap'])
            self.assertEqual(len(value['turns']),1);self.assertTrue(value['local_close']['local_owner_closed'])
            area=self.home/'usable-assertions';area.mkdir()
            with patch.multiple(caller,ROOT=area,EXE='/usr/bin/false',PROFILE='.codex2',COLLECTOR='current'), \
                 patch.object(caller,'method_material',side_effect=AssertionError('method must stay withheld')):
                await caller.actual(pool=self.pool,current_authority=self.authority)
            value=json.loads((area/'actual1172.json').read_text())
            self.assertEqual(value['pending_originals'],0);self.assertEqual(len(value['turns']),1)
            self.assertTrue(value['boundary_evidence']['assertions_match']);self.assertFalse(value['boundary'])
            self.assertTrue(value['local_close']['local_owner_closed'])
        self.assertEqual(len(calls),2)

    async def test_current_authority_revocation_inside_admission_prevents_creation(self):
        admission=self.pool.admission
        @asynccontextmanager
        async def revoke(profile):
            async with admission(profile):
                self.authorized=False
                yield
        spawn=AsyncMock(side_effect=AssertionError('revoked caller must never spawn'))
        with patch.object(self.pool,'admission',side_effect=revoke),patch('asyncio.create_subprocess_exec',spawn):
            with self.assertRaisesRegex(Refusal,'revoked'):await self.turn('revoked-in-admission')
        spawn.assert_not_called();self.assertFalse(self.originals.owned)


class Invocation(unittest.TestCase):
    def setUp(self):
        self.home=Path(tempfile.mkdtemp(prefix='authority1183-',dir=os.environ['ONEOFF1077_FIXTURES']))
        self.source=self.home/'selected.txt';self.source.write_text('original positive fixture')
        self.clock=[100.]
        self.authority=opaque_review.InvocationAuthority([self.source],'.codex2','/usr/bin/false',
            clock=lambda:self.clock[0])

    def test_changed_selected_source_cannot_continue_under_stale_authority(self):
        self.authority()
        self.source.write_text('different selected fixture')
        with self.assertRaisesRegex(Refusal,'source changed'):self.authority()

    def test_revoke_and_original_deadline_never_renew_qualification_authority(self):
        self.clock[0]=7299.;self.authority()
        self.clock[0]=7300.
        with self.assertRaisesRegex(Refusal,'elapsed'):self.authority()
        self.clock[0]=100.
        with self.assertRaises(KeyboardInterrupt):self.authority.revoke()
        with self.assertRaisesRegex(Refusal,'revoked'):self.authority()
