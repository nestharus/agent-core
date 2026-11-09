"""DECISION1171: real pool/SQLite/process/capture; fictional review and rights.

Expected: pool control progresses during an opening turn and finalization;
creation remains excluded by current membership; originals never migrate.
"""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from coordinator_runtime import opaque_review, reviews
from coordinator_runtime.appserver import CollectionPending
from coordinator_runtime.execution_pool import _module
from coordinator_runtime.contracts import Refusal, encode
import test_oneoff1077 as fixture
from test_opaque_review1157 import THREAD, public_module


class Responsive(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = fixture.Recovery(methodName='runTest')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.store, _, job, self.packet, self.policy, self.acquired, _ = self.fixture.native_fixture()
        self.pool = _module.Pool(self.store.config['execution_pool_routes'])
        self.pool.set(['.codex2', '.codex3', '.codex4', '.codex5'])
        self.store.config['tasks']['reviews-proposer'].update(execution='owner', binding=dict(opaque_review.BINDING))
        self.policy.update(transport=opaque_review.VERSION,
            launcher_sha256=reviews.sha(opaque_review.launcher_path().read_bytes()),
            method_closure='unified-definitions-v1')
        self.native = reviews.Native()
        self.executor = reviews.Executor(self.store, self.native)
        self.attempt = self.store.start_job(job['id'], job['token'])
        self.job = self.store.job(job['id'])
        self.profile = self.store.attempt(self.attempt)['profile']
        area = Path(self.acquired['repository'])
        (area/'fiction.txt').write_text('nonsecret positive source1171\n')
        for argv in (['init', '-q'], ['add', '--', 'fiction.txt'],
                     ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      '-c', 'commit.gpgsign=false', 'commit', '-qm', 'owned source1171']):
            subprocess.run(['git', '-C', str(area), *argv], check=True, capture_output=True)
        head = subprocess.check_output(['git', '-C', str(area), 'rev-parse', 'HEAD']).decode().strip()
        body = (area/'fiction.txt').read_bytes()
        self.packet.update(base=head, head=head)
        self.acquired.update(source={head+':fiction.txt': {'bytes':len(body), 'sha256':reviews.sha(body)}},
                             situation={'goals':'responsive control with conserved originals'})
        self.spawn = asyncio.create_subprocess_exec
        self.spawned = asyncio.Event()
        self.read_fd, self.write_fd = os.pipe()
        self.addCleanup(os.close, self.read_fd)
        self.addCleanup(os.close, self.write_fd)
        self.children, self.argv = [], []

    async def standin(self, *argv, **kwargs):
        self.argv.append(argv)
        if len(self.argv)==1:
            with self.assertRaises(_module.PoolBusy):
                self.pool.status(blocking=False)
        self.assertEqual(kwargs.pop('env')['CODEX_HOME'], '/home/nes/'+self.profile)
        reply = dict(semantic='DONE', summary='fictional', report='fictional whole report',
            history_entry='fictional history', stage='architecture' if len(self.argv)==1 else 'complete',
            coverage=dict(families={f:'partial' for f in reviews.FAMILIES}, core_files_not_read=['fixture'],
                          observations=[], answered_ids=[], limits=['fictional provider/method/rights']))
        events = [dict(type='thread.started', thread_id=THREAD),
                  dict(type='item.completed', item=dict(type='agent_message', text=encode(reply))),
                  dict(type='turn.completed')]
        program = 'import os,sys\nsys.stdin.read()\n'
        if len(self.argv)==1:
            program += f'os.read({self.read_fd},1)\n'
        program += '\n'.join('print('+repr(encode(e))+',flush=True)' for e in events)
        child = await self.spawn(sys.executable, '-c', program, pass_fds=(self.read_fd,), **kwargs)
        self.children.append(child)
        self.spawned.set()
        return child

    async def test_opening_turn_releases_control_but_conserves_context_and_original(self):
        with patch.object(reviews, 'material', return_value=self.acquired), \
             patch.object(reviews, 'method_files', return_value=self.policy['method_files']), \
             patch('asyncio.create_subprocess_exec', side_effect=self.standin):
            running = asyncio.create_task(self.executor.execute(self.job,self.attempt,self.policy,self.packet))
            try:
                await asyncio.wait_for(self.spawned.wait(), 2)
                # The child cannot complete until this test releases its pipe.
                await asyncio.sleep(0)
                owner = next(iter(self.native.public_contexts.values()))
                created = owner.created
                self.assertTrue(owner.busy)
                self.assertEqual(len(self.native.originals.owned), 1)
                self.assertIsNone(self.children[0].returncode)
                self.assertEqual(self.store.execution_pool.status()['state'], 'enabled')
                with self.assertRaisesRegex(ValueError, 'idle'):
                    owner.close(self.store.controller)
                # Separate nonblocking process uses the actual control lock.
                control = await self.spawn(sys.executable, '-c',
                    'import execution_pool,json,sys\np=execution_pool.Pool(sys.argv[1])\n'
                    'print(json.dumps(p.allocate(blocking=False)))', str(self.pool.routes),
                    env={'PATH':'/usr/bin:/bin', 'HOME':'/fixtures', 'PYTHONPATH':'/src/tools/direct-child', 'PYTHONDONTWRITEBYTECODE':'1'},
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                out, err = await asyncio.wait_for(control.communicate(),2)
                self.assertEqual(control.returncode,0,err)
                self.assertIn(json.loads(out)['profile'],['.codex2','.codex3','.codex4','.codex5'])
                # Nonblocking lock witness prevents a regression hanging set().
                with self.pool.locked(blocking=False):
                    pass
                self.pool.set([])
                self.assertEqual(self.pool.status(blocking=False)['state'],'empty')
                self.assertIn('empty',self.store.execution_pool.status()['error'])
                with self.assertRaisesRegex(Refusal,'empty'):
                    async with self.store.execution_pool.admission(self.profile):
                        self.fail('removed profile admitted')
                self.pool.set([p for p in ['.codex2','.codex3','.codex4','.codex5'] if p!=self.profile])
                with self.assertRaisesRegex(Refusal,'disabled'):
                    async with self.store.execution_pool.admission(self.profile):
                        self.fail('removed profile admitted')
                self.assertNotEqual(self.store.execution_pool.allocate()['profile'],self.profile)
                os.write(self.write_fd,b'x')
                outcome = await asyncio.wait_for(asyncio.shield(running),5)
            finally:
                if not running.done():
                    os.write(self.write_fd,b'x')
                    await running  # exact owned coroutine drains originals
        self.assertIsNone(outcome['error'],outcome)
        self.store.collect(self.attempt,outcome)
        self.assertEqual(owner.created,created)
        self.assertEqual(owner.profile,self.profile)
        self.assertEqual(owner.calls,2)
        self.assertEqual(self.argv[1][self.argv[1].index('resume')+1],THREAD)
        self.assertFalse(self.native.originals.owned)
        observed=json.loads(self.store.attempt(self.attempt)['detail'])['original_end_observations']
        self.assertEqual([o['exit'] for o in observed],[0,0])
        self.assertTrue(all(o['evidence']['stdout_eof'] and o['evidence']['stderr_eof'] for o in observed))
        self.assertFalse(reviews.collected_proof(self.store,self.job,self.store.attempt(self.attempt))['native_owner_execution'])
        await self.executor.close('fictional-component',self.policy)
        self.assertEqual(owner.state,'closed')
        self.assertEqual(len(self.argv),2)


class AdmissionTail(unittest.IsolatedAsyncioTestCase):
    def setup_owner(self):
        module=public_module()
        from coordinator_runtime.appserver import Originals
        import tempfile
        home=Path(tempfile.mkdtemp(dir=os.environ['ONEOFF1077_FIXTURES']))
        originals=Originals()
        owner=module.Context(home/'context','.codex4','owned-collector',30,originals)
        options=dict(collector='owned-collector',profile='.codex4',current_authority=lambda:None,
                     current_profiles=['.codex4'],publish=lambda e:None,maximum=1024,capture_max=2048,shutdown=.1)
        return module,home,owner,originals,options

    async def test_current_authority_rechecked_after_admission_before_spawn(self):
        module,home,owner,originals,options=self.setup_owner()
        authorized=[True]
        def authority():
            if not authorized[0]:raise Refusal('fresh authority revoked')
        @asynccontextmanager
        async def admission():
            authorized[0]=False
            yield
        options.update(current_authority=authority,admission=admission)
        from unittest.mock import AsyncMock
        spawn=AsyncMock(side_effect=AssertionError('no process may start'))
        with patch('asyncio.create_subprocess_exec',spawn):
            with self.assertRaisesRegex(Refusal,'revoked'):
                await owner.turn(home/'turn',[('source',b'nonsecret')],'fixture',**options)
        spawn.assert_not_called()
        self.assertFalse(originals.owned)
        self.assertEqual(owner.state,'interrupted')

    async def test_admission_wait_does_not_renew_whole_context_lifetime(self):
        module,home,owner,originals,options=self.setup_owner()
        clock=[10.]
        owner.clock=lambda:clock[0];owner.created=10.
        @asynccontextmanager
        async def admission():
            clock[0]=41.
            yield
        from unittest.mock import AsyncMock
        spawn=AsyncMock(side_effect=AssertionError('elapsed original cannot start'))
        with patch('asyncio.create_subprocess_exec',spawn):
            with self.assertRaisesRegex(ValueError,'lifetime'):
                await owner.turn(home/'turn',[('source',b'nonsecret')],'fixture',admission=admission,**options)
        spawn.assert_not_called()
        self.assertEqual(owner.created,10.)
        self.assertFalse(originals.owned)

    async def test_publication_failure_retains_same_numeric_original_and_no_replay(self):
        module,home,owner,originals,options=self.setup_owner()
        native_spawn=asyncio.create_subprocess_exec
        children=[];ends=[];available=[False]
        def publish(observation):
            if not available[0]:raise Refusal('fresh owned publication unavailable')
            ends.append(observation)
        async def harmless(*argv,**kwargs):
            kwargs.pop('env')
            events=[dict(type='thread.started',thread_id=THREAD),
                    dict(type='item.completed',item=dict(type='agent_message',text='fictional')),
                    dict(type='turn.completed')]
            body='import sys\nsys.stdin.read()\n'+'\n'.join('print('+repr(encode(e))+',flush=True)' for e in events)
            child=await native_spawn(sys.executable,'-c',body,**kwargs)
            children.append(child)
            return child
        options['publish']=publish
        with patch('asyncio.create_subprocess_exec',side_effect=harmless):
            with self.assertRaises(CollectionPending):
                await owner.turn(home/'turn',[('source',b'nonsecret')],'fixture',**options)
        key=next(iter(originals.owned))
        observation=originals.observation(key)
        self.assertEqual(observation['exit'],0)
        self.assertTrue(observation['evidence_complete'])
        self.assertTrue(observation['evidence']['stdout_eof'])
        self.assertTrue(observation['evidence']['stderr_eof'])
        self.assertEqual(observation['failures'],[dict(stage='delivery',type='Refusal')])
        with self.assertRaisesRegex(ValueError,'idle'):owner.close('owned-collector')
        with self.assertRaisesRegex(ValueError,'interrupted'):
            await owner.turn(home/'no-replay',[('source',b'nonsecret')],'fixture',**options)
        available[0]=True
        await originals.collect_pending(.1)
        self.assertEqual([e['original'] for e in ends],[key])
        self.assertFalse(originals.owned)
        self.assertFalse(originals.pending)
        self.assertEqual(len(children),1)
        self.assertTrue(owner.close('owned-collector')['local_owner_closed'])

    async def test_ownership_survives_admission_exit_failure(self):
        module=public_module()
        from coordinator_runtime.appserver import Originals
        originals=Originals(); ends=[]
        root=Path(os.environ['ONEOFF1077_FIXTURES'])
        import tempfile
        home=Path(tempfile.mkdtemp(dir=root))
        owner=module.Context(home/'context','.codex4','owned-collector',30,originals)
        spawn=asyncio.create_subprocess_exec
        async def harmless(*argv,**kwargs):
            kwargs.pop('env')
            return await spawn(sys.executable,'-c','import time;time.sleep(30)',**kwargs)
        @asynccontextmanager
        async def broken_exit():
            yield
            raise RuntimeError('owned admission exit failure')
        with patch('asyncio.create_subprocess_exec',side_effect=harmless):
            with self.assertRaisesRegex(RuntimeError,'exit failure'):
                await owner.turn(home/'turn',[('source',b'nonsecret')],'fixture',
                    collector='owned-collector',profile='.codex4',current_authority=lambda:None,
                    current_profiles=['.codex4'],publish=ends.append,maximum=1024,capture_max=2048,
                    shutdown=.1,admission=broken_exit)
        self.assertEqual(owner.state,'interrupted')
        self.assertFalse(originals.owned)
        self.assertEqual(len(ends),1)
        self.assertIsInstance(ends[0]['exit'],int)
        self.assertIn('capture setup incomplete; original retained',ends[0]['evidence']['errors'])

