"""Public declarations and NULL-native journal fiction; no provider protocol runs.

Actual control set/status/allocation/admission and configuration/Access execute.
Native creation is a seam to a harmless owned process, never a native caller.
Thread-input probes stop at the RPC boundary without manufacturing any IDs.
"""
import asyncio
import copy
import errno
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing, reviews
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.contracts import Refusal, encode, digest
from coordinator_runtime.execution_pool import ExecutionPool, _module
import test_configuration308 as previous

KNOWN = ['.codex', '.codex2', '.codex3', '.codex4', '.codex5']
TODAY = ['.codex2', '.codex3', '.codex5']


class InputBoundary(Exception):
    pass


class HotMembership(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.f = previous.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        original_engine = previous.engine_config
        def original(directory):
            value = original_engine(directory)
            # Public prospective authorization, separate from all NULL native
            # role/attempt identities in the underlying protocol fixture.
            value['profiles'] = ['.codex', '.codex2', '.codex3', '.codex5']
            value['deadlines']['shutdown']=2  # Original local pipe collection bound.
            return value
        with patch.object(previous, 'engine_config', side_effect=original):
            self.f.setUp()
        self.routes = Path(self.f.original['execution_pool_routes'])
        raw = Path('/src/tools/direct-child/routes.toml').read_text()
        raw = raw.replace('~/.local/state/direct-child', str(self.f.directory/'pool-state'))
        self.routes.write_text(raw)
        self.pool = _module.Pool(self.routes)
        self.before_config = copy.deepcopy(self.f.original)
        self.before_grants = [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_software_grants_v1')]
        self.f.transition()
        self.key = self.f.issue()
        self.runtime = self.f.runtime
        self.runtime.execution_pool = ExecutionPool(self.runtime.config, runtime=self.runtime)
        self.counter = self.pool.read()[2]
        self.original_rows = {t: self.runtime.rows('SELECT * FROM '+t) for t in ('attempts','events','outboxes','enrollments','configuration_transitions')}

    def unchanged_history(self):
        self.assertEqual(self.before_config, self.f.original)
        self.assertEqual(self.before_grants, [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_software_grants_v1')])
        self.assertEqual(self.runtime.one("SELECT value FROM meta WHERE key='configuration'")['value'], digest(self.before_config))
        for table, rows in self.original_rows.items():
            self.assertEqual(self.runtime.rows('SELECT * FROM '+table), rows, table)
        for row in self.runtime.rows('SELECT profile,session,turn FROM attempts'):
            self.assertEqual(dict(row), {'profile':None,'session':None,'turn':None})

    def current(self):
        row, selection = self.runtime.processing.current()
        self.assertEqual(row['id'], self.key)
        self.assertEqual(selection['basis']['configuration'], digest(self.runtime.config))
        return row

    async def test_live_order_repeated_updates_pause_and_future_four_keep_capability_and_history(self):
        self.assertEqual(self.runtime.config['profiles'], KNOWN)
        self.assertEqual(self.pool.read()[1], TODAY)
        self.assertFalse(self.counter.exists(), 'release selection must not touch counter')
        first = self.runtime.execution_pool.allocate()
        self.assertEqual((first['turn'],first['profile']), (0,'.codex2'))
        counter_inode = self.counter.stat().st_ino
        lock_inode = self.counter.with_suffix('.pool.lock').stat().st_ino
        count = 1
        static = configuration.selected(self.runtime)['basis']['release']['pool_control']
        for enabled in (['.codex5','.codex3'], ['.codex5','.codex3'], ['.codex3','.codex5'], [], ['.codex4'], ['.codex'], TODAY):
            # Exercise the existing operator process, with real collection and
            # owned-only file effects, rather than editing TOML to imitate set.
            changed = subprocess.run([sys.executable, str(_module.__file__), '--routes',str(self.routes),'set',*enabled], capture_output=True, text=True)
            self.assertEqual(changed.returncode, 0, changed.stdout+changed.stderr)
            witness = json.loads(changed.stdout)
            self.assertEqual(witness['turn'], count)
            self.current()
            self.assertEqual(configuration.release(self.runtime,self.runtime.config)['pool_control'], static)
            if enabled:
                choice = self.runtime.execution_pool.allocate()
                self.assertEqual((choice['profile'],choice['turn']), (enabled[count%len(enabled)], count))
                async with self.runtime.execution_pool.admission(choice['profile']) as admitted:
                    self.assertEqual(admitted['profile'], choice['profile'])
                    self.assertEqual(admitted['next_reservation_turn'], count+1)
                count += 1
            else:
                self.assertEqual(self.runtime.execution_pool.status()['state'], 'held')
                with self.assertRaisesRegex(Refusal,'empty'):
                    self.runtime.execution_pool.allocate()
            self.assertEqual(int(self.counter.read_text()),count)
            self.assertEqual(self.counter.stat().st_ino,counter_inode)
            self.assertEqual(self.counter.with_suffix('.pool.lock').stat().st_ino,lock_inode)
            self.unchanged_history()
        self.assertEqual(self.pool.read()[1],TODAY)

    async def test_membership_can_change_between_transition_basis_and_selection(self):
        # A second prospective config file creates an actual delta; the same
        # selection can survive membership-only changes while source stays fixed.
        f = self.f
        processing.revoke(self.runtime,f.boards,self.key)
        value = configuration.candidate(self.runtime,str(f.directory/'next.json'),[])
        Path(value['operator_config']).write_text(encode(value))
        basis = configuration.basis(self.runtime,f.boards,value,list(value['tasks']))
        self.pool.set([])
        result = configuration.apply(self.runtime,f.boards,value,{'basis':basis,'authority':'fictional selected next config and why'})
        self.assertEqual(result['configuration'],digest(value))
        self.assertEqual(self.pool.status()['state'],'empty')

    async def test_all_static_bindings_and_other_control_bytes_remain_guarded(self):
        self.pool.status()
        before = self.routes.read_bytes()
        count = self.counter.read_bytes()
        changes = [
            ('manual_profiles = [".codex",', 'manual_profiles = ['),
            ('model = "gpt-6.1-sol"','model = "unselected-model"'),
            ('effort = "high"','effort = "low"'),
            ('provider = "codex"','provider = "claude"'),
            ('"sol-high-codex4"','"unselected-site"'),
            ('default = "native"','default = "direct"'),
            ('caller = "/opt/','caller = "/unselected/'),
            (str(self.f.directory/'pool-state'),str(self.f.directory/'unselected-state')),
            ('route = "direction"','route = "refine"'),
            ('# Contextual direct-dispatch bindings:', '# changed static control comment:')]
        for old,new in changes:
            with self.subTest(static=old):
                self.assertIn(old.encode(),before)
                self.routes.write_bytes(before.replace(old.encode(),new.encode(),1))
                with self.assertRaises(Refusal):self.current()
                # These checks run independently of Access.current, including
                # before touching a tampered rotation state path.
                with self.assertRaises(Refusal):self.runtime.execution_pool.allocate()
                with self.assertRaises(Refusal):
                    async with self.runtime.execution_pool.admission('.codex2'):pass
                self.assertEqual(self.counter.read_bytes(),count)
                self.assertFalse((self.f.directory/'unselected-state').exists())
                self.routes.write_bytes(before)
        self.current();self.unchanged_history()

    async def test_static_control_is_rechecked_after_wait_before_creation(self):
        entered = asyncio.Event()
        original_sleep = asyncio.sleep
        lock = self.pool.locked()
        lock.__enter__()
        async def waiting(_):
            entered.set()
            await original_sleep(0)
        async def admission():
            with self.assertRaisesRegex(Refusal,'static execution pool control changed'):
                async with self.runtime.execution_pool.admission('.codex2'):
                    self.fail('changed static control admitted')
        with patch('coordinator_runtime.execution_pool.asyncio.sleep', side_effect=waiting):
            pending = asyncio.create_task(admission())
            await entered.wait()
            self.routes.write_bytes(self.routes.read_bytes()+b'\n# unselected static control\n')
            lock.__exit__(None,None,None)
            await pending
        self.unchanged_history()

    async def test_control_path_and_operator_config_tamper_refuse_without_new_state(self):
        other = self.f.directory/'other-routes.toml'
        other.write_bytes(self.routes.read_bytes())
        self.runtime.execution_pool.pool = _module.Pool(other)
        with self.assertRaisesRegex(Refusal,'static execution pool control changed'):
            self.runtime.execution_pool.allocate()
        self.assertFalse(self.counter.exists())
        self.runtime.execution_pool.pool = self.pool
        path = Path(self.runtime.config['operator_config'])
        saved = path.read_bytes()
        path.write_bytes(saved+b'\n')  # Even unselected static formatting remains pinned.
        with self.assertRaisesRegex(Refusal,'public release/dependencies changed'):self.current()
        path.write_bytes(saved)
        self.current();self.unchanged_history()

    async def test_unsupported_authority_deltas_do_not_enter_prospective_draft(self):
        original = self.f.original
        runtime = SimpleNamespace(config=original)
        value = configuration.candidate(runtime,str(self.f.directory/'other.json'),[])
        for mutate in (lambda v:v.update(profiles=KNOWN[:-1]),
                       lambda v:v['roles']['Work'].update(profile='.codex4'),
                       lambda v:v['tasks']['wp'].update(binding={'model':'changed','provider':'openai','effort':'high'}),
                       lambda v:v.update(execution_pool_routes=str(self.f.directory/'other.toml'))):
            changed=copy.deepcopy(value);mutate(changed)
            # Admit NULL native role fields at the existing fixture boundary;
            # let the production exact-delta check reject authority tampering.
            with patch.object(configuration,'validate_config',return_value=None):
                with self.assertRaises(Refusal):configuration.validate_changes(runtime,changed,list(value['tasks']))
        self.unchanged_history()

    async def test_empty_unknown_corrupt_and_missing_controls_keep_narrow_truthful_holds(self):
        saved=self.routes.read_bytes()
        self.pool.set([]);self.current()
        with self.assertRaisesRegex(Refusal,'empty'):self.runtime.execution_pool.allocate()
        self.routes.write_bytes(saved.replace(b'pool = [".codex2", ".codex3", ".codex5"]',b'pool = [".codex7"]'))
        with self.assertRaises(Refusal):self.runtime.execution_pool.allocate()
        self.routes.write_bytes(saved)
        self.counter.write_text('unknown\n')
        self.current()  # A corrupt counter is capacity/state, not source drift.
        with self.assertRaisesRegex(Refusal,'malformed'):self.runtime.execution_pool.allocate()
        self.assertEqual(self.counter.read_text(),'unknown\n')
        self.routes.unlink()
        with self.assertRaises(Refusal):self.current()
        self.unchanged_history()

    async def test_bound_appserver_inputs_gate_current_membership_without_rpc_or_ids(self):
        adapter=AppServer(self.runtime.config)
        # Explicit boundary seam maps NULL fixture-native identity to a public
        # bound-account declaration. No profile/session/turn enters the journal.
        real_pool=self.runtime.execution_pool
        bound=SimpleNamespace(admission=lambda unused:real_pool.admission('.codex2'))
        async def input_boundary(*args,**kwargs):raise InputBoundary('admitted local input boundary only')
        class Peer:
            async def rpc(self,method,params):
                assert method=='thread/read'
                return {'thread':{'id':None,'status':{'type':'idle'}}}
        name='fictional-original-attempt'
        with patch.object(self.runtime,'authorize_launch',side_effect=lambda unused:self.current()), \
             patch.object(self.runtime,'execution_pool',bound), \
             patch.object(adapter,'start_turn',side_effect=input_boundary) as start:
            with self.assertRaises(InputBoundary):
                await adapter.turn(Peer(),self.runtime,name,None,'fixture input',{}, {},None,{'detail':{}})
            self.pool.set(['.codex3'])
            with self.assertRaisesRegex(Refusal,'disabled before launch'):
                await adapter.turn(Peer(),self.runtime,name,None,'fixture input',{}, {},None,{'detail':{}})
            with self.assertRaisesRegex(Refusal,'disabled before launch'):
                await adapter.continue_idle(Peer(),self.runtime,name,None,None,{}, {},None)
            self.assertEqual(start.call_count,1)
        self.unchanged_history()

    async def test_excluded_reservation_refuses_appserver_creation_before_preflight(self):
        reserved=self.runtime.execution_pool.allocate()
        frozen=copy.deepcopy(reserved)
        self.pool.set(['.codex3','.codex5'])
        real_pool=self.runtime.execution_pool
        declaration=SimpleNamespace(admission=lambda unused:real_pool.admission(reserved['profile']))
        adapter=AppServer(self.runtime.config)
        with patch.object(self.runtime,'execution_pool',declaration), \
             patch.object(self.runtime,'authorize_launch',side_effect=lambda unused:self.current()), \
             patch.object(adapter,'command',side_effect=AssertionError('no provider preflight')), \
             patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=AssertionError('no creation')):
            outcome=await adapter.run(self.runtime,'fictional-original-attempt','fixture',{'cwd':'/fixtures','sandbox':'read-only'})
        self.assertTrue(outcome['detail']['known_not_started'])
        self.assertIn('disabled before launch',outcome['error'])
        self.assertEqual(reserved,frozen)
        self.assertEqual(self.pool.status()['turn'],1)
        self.unchanged_history()

    async def test_review_creation_exclusion_running_custody_and_close_drain(self):
        # A selected policy/context declaration, never an observed native identity.
        context={'profile':'.codex2','route':'public-declared-sol-two','handle':str(self.f.directory/'declared-control-handle'),'run':None,'created':self.runtime.clock()}
        policy={'caller':'/usr/bin/true','caller_sha256':reviews.sha(Path('/usr/bin/true').read_bytes()),'routes':{'.codex2':context['route']},'deadline':1}
        native=reviews.Native()
        children=[]
        spawned=asyncio.Event()
        actual_spawn=asyncio.create_subprocess_exec
        async def harmless_spawn(*argv,**kwargs):
            self.assertEqual(argv[0],'/usr/bin/true')
            self.assertIn(str(context['handle']),argv)
            # Real harmless owned child/END, no native/provider protocol or IDs.
            child=await actual_spawn(sys.executable,'-c','import sys; sys.stdin.read()',stdin=asyncio.subprocess.PIPE,**kwargs)
            children.append((child,argv));spawned.set();return child
        name='fictional-original-attempt'
        with patch.object(self.runtime,'authorize_launch',side_effect=lambda unused:self.current()), \
             patch.object(self.runtime,'begin',return_value=None), \
             patch('coordinator_runtime.reviews.asyncio.create_subprocess_exec',side_effect=harmless_spawn):
            running=asyncio.create_task(native.call(self.runtime,name,policy,context,self.f.directory/'call-one','fixture input',[],opening=True))
            await asyncio.wait_for(spawned.wait(),2)
            self.pool.set([])
            frozen=copy.deepcopy(context)
            self.assertIsNone(children[0][0].returncode)
            children[0][0].stdin.close()
            code,receipt,answer=await running
            self.assertEqual(code,0)
            self.assertEqual(receipt['class'],'incomplete')
            self.assertIsNone(answer)
            self.assertEqual(context,frozen)
            with self.assertRaisesRegex(Refusal,'empty'):
                await native.call(self.runtime,name,policy,context,self.f.directory/'excluded-input','future input',[],opening=True)
            self.assertEqual(len(children),1)
            # Fictional owned handle for the harmless close subprocess; no native run.
            Path(context['handle']).write_text(encode({'v':1,'uid':os.getuid(),'run':'fictional-protocol-run',
                'socket':'/fixtures/fictional-unused.sock','token':'fictional-not-a-credential'}))
            Path(context['handle']).chmod(0o600)
            spawned.clear()
            draining=asyncio.create_task(native.call(self.runtime,name,policy,context,self.f.directory/'close-one','',[],close=True))
            await asyncio.wait_for(spawned.wait(),2)
            self.assertIn('--close',children[1][1])
            self.assertNotIn('--prompt-file',children[1][1])
            children[1][0].stdin.close()
            code,receipt,answer=await draining
            self.assertEqual(code,0)
            self.assertEqual(receipt['class'],'incomplete','local exit cannot fabricate native close success')
        self.unchanged_history()

    async def test_unavailable_review_route_refuses_without_borrowing_or_affecting_other_work(self):
        context={'profile':'.codex4','route':None,'handle':str(self.f.directory/'declaration'),'run':None,'created':self.runtime.clock()}
        policy={'caller':'/usr/bin/true','caller_sha256':reviews.sha(Path('/usr/bin/true').read_bytes()),'routes':{'.codex3':'declared-three'},'deadline':1}
        self.pool.set(['.codex4'])
        with patch.object(self.runtime,'authorize_launch',side_effect=lambda unused:self.current()), \
             patch('coordinator_runtime.reviews.asyncio.create_subprocess_exec',side_effect=AssertionError('no substitute')):
            with self.assertRaisesRegex(Refusal,'route unavailable/changed'):
                await reviews.Native().call(self.runtime,'fictional-original-attempt',policy,context,self.f.directory/'unknown-route','fixture',[])
        self.assertEqual(self.runtime.execution_pool.allocate()['profile'],'.codex4')
        self.current();self.unchanged_history()

    async def test_partial_review_route_declarations_do_not_require_unenabled_accounts(self):
        policy={'caller':'/usr/bin/true','caller_sha256':reviews.sha(Path('/usr/bin/true').read_bytes()),'routes':{'.codex3':'public-declared-three'},'deadline':1,
                'method':'fixture-method','method_files':{},'components':{}}
        runtime=SimpleNamespace(config={'profiles':KNOWN,'tasks':{'review':{'role':'Reviews','phase':'proposer','effects':'none'}}})
        with patch.object(reviews,'method_files',return_value={}):
            reviews.validate(runtime,{'review':policy})
            for routes in ({'.codex7':'unknown'},{'.codex4':''}):
                with self.assertRaises(Refusal):reviews.validate(runtime,{'review':{**policy,'routes':routes}})
        self.unchanged_history()


class Namespace(unittest.TestCase):
    def test_public_sources_read_only_owned_fixtures_writable_no_real_home(self):
        source=Path('/src/tools/direct-child/execution_pool.py')
        self.assertTrue(os.statvfs(source).f_flag & os.ST_RDONLY)
        with self.assertRaises(OSError) as failure:source.open('ab')
        self.assertEqual(failure.exception.errno,errno.EROFS)
        self.assertFalse(Path('/home/nes').exists())
        (Path('/fixtures')/'owned-write-proof').write_text('owned fiction only')


if __name__=='__main__':unittest.main()
