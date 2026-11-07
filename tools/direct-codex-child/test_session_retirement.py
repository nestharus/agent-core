"""Source-only fake-clock, fake CLI and owned stdio-server qualification."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import session_retirement as sr
import test_launch as launch_tests

ROOT = '00000000-0000-4000-8000-000000000001'
CALLER = '00000000-0000-4000-8000-000000000002'
CURRENT = '00000000-0000-4000-8000-000000000003'
CHILD = '00000000-0000-4000-8000-000000000004'
T = 1000


class Crash(BaseException):
    pass


class Server:
    calls = []
    failure = None
    def __init__(self, binding):
        self.binding = binding
    def call(self, method, params, request_id):
        self.calls.append((self.binding.copy(), method, params))
        if method == 'initialize':
            return {'codexHome': self.binding['codex_home']}
        if self.failure:
            raise TimeoutError('lost ACK')
        return {}
    def send(self, value):
        pass
    def close(self):
        return 0


class RetirementTest(unittest.TestCase):
    def setUp(self):
        # Fixtures are conserved, including failures, in private qualification TMPDIR.
        self.root = Path(tempfile.mkdtemp(prefix='retirement-fixture-'))
        self.binding = dict(profile='.codex2', codex_home='/original/.codex2',
                            binary='/public/codex', binary_sha256='qualified-test-binary',
                            account_binding='original-account-receipt', route_ref='original-route',
                            route_digest='route-hash', ephemeral=False)
        self.receipt = dict(owner='owner', custodian='custodian', collector='collector',
                            caller_session_id=CALLER, account_binding='original-account-receipt',
                            context_ref='builder-or-oneoff-context',
                            required_closures={'processing':'owner', 'context':'owner', 'consumer':'consumer'},
                            hold_owners={k:k+'-owner' for k in sr.HOLDS})
        self.m = sr.bootstrap(self.root, self.receipt, self.binding, 'oneoff')
        self.record('metadata', {'qualified':True, 'count':1, 'thread_id':ROOT})
        self.record('end', 0)
        self.record('collect', {'handle':'original-terminal', 'receipt':'actual-END'}, 'collector')
        for name, actor in self.receipt['required_closures'].items():
            self.record('close', dict(name=name, at=T, receipt=name+'-receipt'), actor)
        for name in sr.HOLDS:
            self.record('hold', dict(name=name, refs=[], receipt=name+'-clear'), name+'-owner')
        self.c = dict(exclusive=True, coverage='complete', generation=0,
                      invocation_id=self.m['invocation_id'], binding_digest=sr.digest(self.binding),
                      active_callers=[], unknown_descendants=[], receipt='exclusive-owner-receipt',
                      members={ROOT:self.member()}, edges=[])
        self.record('custody', self.c, 'custodian')
        Server.calls = []
        Server.failure = None

    def member(self):
        return dict(custodian='custodian', active=False, end=0, collection_receipt='original-END',
                    closure_receipt='real-context-close', processed_at=T, context_closed_at=T)

    def record(self, kind, value, actor='owner', generation=0):
        sr.edit(self.root, actor, generation, kind, value, now=T+100)

    def visit(self, now=T+86400, **kw):
        return sr.retire(self.root, 'owner', self.binding, CURRENT, now=now, factory=Server, **kw)

    def assertHeld(self, **kw):
        with self.assertRaises(ValueError):
            self.visit(**kw)
        self.assertEqual(Server.calls, [])

    def test_boundary_ack_restart_and_original_pool_binding(self):
        self.assertHeld(now=T+86399)
        # No current pool is consulted; disabled/reordered profiles cannot retarget.
        with patch.dict(os.environ, {'CURRENT_POOL':'.codex5,.codex3'}):
            self.assertEqual(self.visit()['state'], 'ack')
        self.assertEqual(self.visit()['state'], 'ack')
        self.assertEqual(len(Server.calls), 2)
        self.assertEqual(Server.calls[-1][0], self.binding)
        self.assertEqual(Server.calls[-1][2], {'threadId':ROOT})
        self.assertEqual(sr.read(self.root)[1]['operation']['adapter_end'], 0)

    def test_each_independent_hold_and_immutable_closures(self):
        before = sr.read(self.root)[1]['closures']
        for name in sr.HOLDS:
            self.record('hold', dict(name=name, refs=['actual-obligation'], receipt='hold'), name+'-owner')
            self.assertHeld()
            self.record('hold', dict(name=name, refs=[], receipt='actual-clear'), name+'-owner')
        self.assertEqual(sr.read(self.root)[1]['closures'], before)
        with self.assertRaises(ValueError):
            self.record('close', dict(name='processing', at=T+1, receipt='retime'))

    def test_later_consumer_close_and_missing_root_metadata(self):
        # Independent actual consumer close participates in the max timestamp.
        m, state, _ = sr.read(self.root)
        state['closures'].pop('consumer')
        # Exercise eligibility directly on a prospective owner state, no writes.
        with self.assertRaises(ValueError):
            sr.eligible(m, state, self.binding, CURRENT, T+86400)
        state['closures']['consumer'] = dict(name='consumer', at=T+100, receipt='later-consumer')
        with self.assertRaises(ValueError):
            sr.eligible(m, state, self.binding, CURRENT, T+86499)
        self.assertEqual(sr.eligible(m, state, self.binding, CURRENT, T+86500)[1], T+86500)
        for md in (None, dict(qualified=False, count=0, thread_id=None),
                   dict(qualified=True, count=1, thread_id='wrong-uuid')):
            state['metadata'] = md
            with self.assertRaises(ValueError):
                sr.eligible(m, state, self.binding, CURRENT, T+86500)

    def test_end_does_not_close_processing_or_reusable_context(self):
        self.record('reopen', 'actual-owner-reopened')
        s = sr.read(self.root)[1]
        self.assertEqual(s['end'], 0)
        self.assertEqual(s['generation'], 1)
        self.assertHeld()
        with self.assertRaises(ValueError):
            self.record('close', dict(name='processing', at=T, receipt='stale'))
        self.assertEqual(sr.read(self.root)[1]['closures'], {})
        # Reusable lifetime uses the same explicit context closure requirement.
        other = self.root/'reusable'; other.mkdir()
        sr.bootstrap(other, self.receipt, self.binding, 'reusable')
        self.assertEqual(sr.read(other)[0]['lifetime'], 'reusable')
        with self.assertRaises(ValueError):
            sr.retire(other, 'owner', self.binding, CURRENT, now=T+86400, factory=Server)

    def test_later_descendant_close_moves_due_time(self):
        self.c['members'][CHILD] = self.member()
        self.c['members'][CHILD]['context_closed_at'] = T+100
        self.c['edges'] = [dict(parent=ROOT, child=CHILD, receipt='actual-spawn-edge')]
        self.record('custody', self.c, 'custodian')
        self.assertHeld(now=T+86499)
        self.assertEqual(self.visit(now=T+86500)['state'], 'ack')

    def test_wrong_identity_custody_coverage_current_and_ephemeral(self):
        for key in self.binding:
            bad = dict(self.binding, **{key:'wrong'})
            with self.assertRaises(ValueError):
                sr.retire(self.root, 'owner', bad, CURRENT, now=T+86400, factory=Server)
        with self.assertRaises(ValueError):
            sr.retire(self.root, 'foreign', self.binding, CURRENT, now=T+86400, factory=Server)
        for current in (ROOT, CALLER, None):
            with self.assertRaises((ValueError, TypeError, AttributeError)):
                sr.retire(self.root, 'owner', self.binding, current, now=T+86400, factory=Server)
        variants = [('unknown_descendants', ['unknown']), ('coverage', 'unknown'),
                    ('active_callers', ['active']), ('generation', 1), ('invocation_id', 'foreign'),
                    ('binding_digest', 'wrong'), ('exclusive', False)]
        for key, value in variants:
            c = dict(self.c, **{key:value})
            self.record('custody', c, 'custodian'); self.assertHeld()
        for change in ({'active':True}, {'custodian':'foreign'}, {'end':None}, {'processed_at':None}):
            c = copy.deepcopy(self.c); c['members'][ROOT].update(change)
            self.record('custody', c, 'custodian'); self.assertHeld()
        c = copy.deepcopy(self.c); c['members'][CHILD] = self.member()
        self.record('custody', c, 'custodian'); self.assertHeld()  # no edge coverage
        self.assertEqual(Server.calls, [])

    def test_crashes_and_fence(self):
        def crash_at(point):
            def check(value):
                if value == point:
                    raise Crash()
            return check
        with self.assertRaises(Crash):
            self.visit(checkpoint=crash_at('before_intent'))
        self.assertIsNone(sr.read(self.root)[1]['operation'])
        with self.assertRaises(Crash):
            self.visit(checkpoint=crash_at('before_possible_send'))
        self.assertEqual(sr.read(self.root)[1]['operation']['state'], 'unsent')
        self.assertEqual(Server.calls, [])
        with self.assertRaises(ValueError):
            self.record('reopen', 'cannot cross fence')
        self.record('release-unsent', 'owner verified no possible send')
        with self.assertRaises(Crash):
            self.visit(checkpoint=crash_at('after_possible_send'))
        self.assertEqual(self.visit()['state'], 'possible-send')
        self.assertEqual([c[1] for c in Server.calls], ['initialize'])
        with self.assertRaises(ValueError):
            self.record('release-unsent', 'cannot waive unknown')

    def test_unsent_retry_is_requalified_and_generation_fence_blocks_mutation(self):
        class WrongProfile(Server):
            def call(self, method, params, request_id):
                self.calls.append((self.binding, method, params))
                return {'codexHome':'/wrong'}
        result = sr.retire(self.root, 'owner', self.binding, CURRENT, now=T+86400, factory=WrongProfile)
        self.assertEqual(result['state'], 'unsent')
        self.assertEqual(len(Server.calls), 1)
        self.record('release-unsent', 'actual-owner-unsent-release')
        self.record('hold', dict(name='privacy', refs=['new-exclusion'], receipt='hold'), 'privacy-owner')
        Server.calls = []
        self.assertHeld()

    def test_lost_ack_is_not_replayed(self):
        Server.failure = True
        self.assertEqual(self.visit()['state'], 'possible-send')
        self.visit()
        self.assertEqual(len(Server.calls), 2)

    def test_crash_after_durable_ack_never_repeats(self):
        def crash(point):
            if point == 'after_ack':
                raise Crash()
        with self.assertRaises(Crash):
            self.visit(checkpoint=crash)
        self.assertEqual(self.visit()['state'], 'ack')
        self.assertEqual(len(Server.calls), 2)

    def test_stdio_exact_handshake_and_rpc(self):
        stub = self.root/'stub'
        stub.write_text('''#!/usr/bin/python3
import json, os, sys
for line in sys.stdin:
 r=json.loads(line)
 with open(os.environ['STUB_CALLS'],'a') as f: f.write(json.dumps(r)+'\\n')
 if r['method']=='initialize': result={'codexHome':os.environ['CODEX_HOME']}
 elif r['method']=='initialized': continue
 else:
  assert r['method']=='thread/delete' and set(r['params'])=={'threadId'}
  result={}
 print(json.dumps({'id':r['id'],'result':result}),flush=True)
''')
        stub.chmod(0o700)
        b = dict(self.binding, binary=str(stub), binary_sha256=hashlib.sha256(stub.read_bytes()).hexdigest())
        with patch.object(sr, 'QUALIFIED_BINARY_SHA256', b['binary_sha256']), patch.dict(os.environ, {'STUB_CALLS':str(self.root/'rpc')}):
            server = sr.Stdio(b)
            try:
                self.assertEqual(server.call('initialize', {'clientInfo':{'name':'test','version':'1'}}, 'init')['codexHome'], b['codex_home'])
                server.send({'method':'initialized'})
                self.assertEqual(server.call('thread/delete', {'threadId':ROOT}, 'delete'), {})
            finally:
                self.assertEqual(server.close(), 0)
        self.assertEqual([json.loads(x)['method'] for x in (self.root/'rpc').read_text().splitlines()], ['initialize','initialized','thread/delete'])


class ProspectiveTest(unittest.TestCase):
    setUp = launch_tests.LauncherTest.setUp
    run_launcher = launch_tests.LauncherTest.run_launcher
    calls_readback = launch_tests.LauncherTest.calls_readback
    exec_args = launch_tests.LauncherTest.exec_args
    # Reuse only fixture helpers; do not inherit and rerun the whole old suite.
    def test_future_metadata_before_cap(self):
        receipt = dict(owner='owner', custodian='custodian', collector='collector', caller_session_id=CALLER,
                       account_binding='original-account', context_ref='actual-context',
                       required_closures={'processing':'owner','context':'owner'},
                       hold_owners={k:k+'-owner' for k in sr.HOLDS})
        path = self.root/'owner.json'; path.write_text(json.dumps(receipt))
        fake = self.bin/'codex'
        text = fake.read_text().replace('prompt = sys.stdin.read()', '''prompt = sys.stdin.read()
if '--json' in args:
    for _ in range(100): print(json.dumps({'type':'item.completed','item':{}}))
    print(json.dumps({'type':'thread.started','thread_id':'00000000-0000-4000-8000-000000000001'}))
    sys.stdout.flush()
''').replace('print("live: " + prompt.strip())', 'print(json.dumps({"type":"turn.completed"}))')
        fake.write_text(text)
        result = self.run_launcher('.codex2', '--session-lifecycle','oneoff','--session-owner-receipt',str(path),'--log-max-bytes','64')
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = next(self.runs.iterdir())
        m, state, _ = sr.read(attempt)
        self.assertTrue(state['metadata']['qualified'])
        self.assertEqual(state['end'], 0)
        self.assertEqual(state['closures'], {})
        self.assertEqual(m['binding']['profile'], '.codex2')
        self.assertEqual((attempt/'log.txt').stat().st_size, 64)
        self.assertIn('--json', self.exec_args())

    def test_dispatch_forwards_lifecycle_without_changing_binding(self):
        import importlib.util
        path = Path(__file__).parent.parent/'direct-child'/'dispatch.py'
        spec = importlib.util.spec_from_file_location('retirement_dispatch', path)
        dispatch = importlib.util.module_from_spec(spec); spec.loader.exec_module(dispatch)
        args = dispatch.parse_args(['--cwd', '/fixture', '--prompt', '/prompt', '--runs-dir', '/runs',
                                    '--id', 'future', '--session-lifecycle', 'reusable',
                                    '--session-owner-receipt', '/owner.json'])
        command = dispatch.codex_command(args, {'model':'literal-model','effort':'high','profile_source':'explicit'}, '.codex4', {})
        self.assertEqual(command[command.index('--model')+1], 'literal-model')
        self.assertEqual(command[command.index('--profile')+1], '.codex4')
        self.assertEqual(command[-4:], ['--session-lifecycle','reusable','--session-owner-receipt','/owner.json'])

    def test_typed_missing_duplicate_and_oversized_are_held(self):
        for data in (b'{}\n', (json.dumps({'type':'thread.started','thread_id':ROOT})+'\n').encode()*2,
                     b'x'*70000+b'\n'):
            target=Path(tempfile.mkdtemp(prefix='metadata-fixture-'))
            receipt=dict(owner='owner',custodian='custodian',collector='collector',caller_session_id=CALLER,
                         account_binding='a',context_ref='c',required_closures={'processing':'owner','context':'owner'},
                         hold_owners={k:'owner' for k in sr.HOLDS})
            sr.bootstrap(target,receipt,dict(binary='/fake',codex_home='/fake-home',account_binding='a'),'oneoff')
            result=subprocess.run([sys.executable,str(Path(sr.__file__)),'intercept','--attempt',str(target)],input=data,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,data)
            self.assertFalse(sr.read(target)[1]['metadata']['qualified'])


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(RetirementTest))
    for name in ('test_future_metadata_before_cap','test_dispatch_forwards_lifecycle_without_changing_binding','test_typed_missing_duplicate_and_oversized_are_held'):
        suite.addTest(ProspectiveTest(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
