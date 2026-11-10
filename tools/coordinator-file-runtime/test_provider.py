"""Decision06 consequences with fixed public processes, SQL imports disabled.

No provider/account operations, fake HOME, copied source, cleanup or real roles.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_runtime as fixtures
from test_runtime import call, TOKENS, Held, _pool, _fast, _sql_attempts
from provider import Codex, Redactor, run_provider

TOKENS['root'] = 'synthetic-external-root-token'
FIXED = r'''
import json, os, signal, sys, time
args = sys.argv[1:]
if 'mcp' in args:
    if any('enabled=false' in x for x in args):
        rows = [{'name':'alpha','enabled':False}, {'name':'openaiDeveloperDocs','enabled':False}]
        if '--bad-mcp' in args:
            rows[0]['enabled'] = True
    else:
        rows = [{'name':'alpha','enabled':True}]
    print(json.dumps(rows)); sys.exit(0)
request = json.load(sys.stdin)
mode = request.get('mode')
if mode == 'timeout':
    time.sleep(10)
if mode == 'signal':
    os.kill(os.getpid(), signal.SIGTERM)
if mode == 'overflow':
    os.write(1, b'x'*100000)
if mode == 'multiple':
    print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'{}'}}))
final = request.get('final', {'done': True})
if mode == 'inspect':
    final = {'args':args, 'env_keys':sorted(os.environ), 'prompt':request}
if mode == 'secrets':
    final = {'value':'public-declared-secret', 'escaped':'synthetic-work-token'}
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps(final)}}))
sys.exit(17 if mode == 'failure' else 0)
'''


class ProviderTrial(unittest.TestCase):
    # Reuse only fixture construction and explicit synthetic-state helpers.
    setUp = fixtures.Trial.setUp
    ingest = fixtures.Trial.ingest
    classify = fixtures.Trial.classify
    raw = fixtures.Trial.raw
    reserve = fixtures.Trial.reserve
    collect = fixtures.Trial.collect

    def prepare(self, event='task', actor='work', mode=None, final=None):
        self.classify(event, owner=actor)
        reserved = self.reserve(event, actor=actor)
        self.script = self.root / 'fixed_public.py'
        self.script.write_text(FIXED)
        self.adapter = Codex([sys.executable, '-I', str(self.script)])
        # Static synthetic bindings; initialized before this fixture's runtime
        # binding is renewed only by construction, never on operating state.
        return {**{k: reserved[k] for k in ('attempt', 'collector')},
                'prompt': json.dumps({'mode': mode, 'final': final or {'done': True}}),
                'cwd': str(self.root), 'output_limit': 8192, 'timeout': 2, 'declared_secrets': []}

    def setUp(self):
        # Trial initializes from this exact synthetic input; append the route
        # schema before create via a fixture-only input writer hook.
        original = Path.write_text
        def write(path, value, *args, **kwargs):
            if path.name == 'routes.toml':
                value += ('[routes.explore]\nprovider="codex"\nmodel="public-luna"\neffort="max"\n'
                          '[routes.refine]\nprovider="codex"\nmodel="public-sol"\neffort="high"\n')
                value = value.replace('manual_profiles =', 'efforts = ["low", "xhigh"]\nmanual_profiles =')
            return original(path, value, *args, **kwargs)
        with patch.object(Path, 'write_text', write):
            fixtures.Trial.setUp(self)

    def run_entry(self, request, actor='work'):
        return run_provider(self.rt, actor, TOKENS[actor], request, adapter=self.adapter)

    def adopt_root(self):
        call(self.rt, 'invite', target='root', role='Root', invitation_token=TOKENS['root'], basis='Decision06 external implementation holder')
        call(self.rt, 'adopt', 'root', basis='synthetic external holder self-adoption')

    def test_external_root_addressed_work_result_failure_and_recovery(self):
        self.adopt_root()
        self.classify('routing')
        call(self.rt, 'send', packet='to-root', event='routing', recipient='root', payload={'known': 'repair'})
        self.assertEqual(call(self.rt, 'inbox', 'root')['packets'][0]['id'], 'to-root')
        with self.assertRaises(Held):
            call(self.rt, 'receipt', 'branch', packet='to-root', stage='picked-up', evidence='wrong actor')
        for stage in ['picked-up', 'processed', 'settled']:
            call(self.rt, 'receipt', 'root', packet='to-root', stage=stage, evidence='external holder ' + stage)
        request = self.prepare('repair', 'root', mode='failure')
        result = self.run_entry(request, 'root')
        self.assertEqual(result['end'], 17)
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0, 17])
        recovered = call(self.rt, 'recover', 'root')['attempts'][0]
        self.assertEqual(recovered['collector'], request['collector'])
        with self.assertRaises(Held):
            call(self.rt, 'reconcile', attempt='a', collector=request['collector'], evidence='borrow root collector')
        call(self.rt, 'reconcile', 'root', attempt='a', collector=request['collector'], evidence='actual END17, no external effects')
        call(self.rt, 'send', 'root', packet='result', event='repair', recipient='work', payload={'failure_end': 17})
        self.assertEqual(call(self.rt, 'inbox')['packets'][0]['payload'], {'failure_end': 17})
        self.assertEqual(self.raw()['attempts']['a']['end'], 17)
        for op, args in [('invite', dict(target='other',role='QA',invitation_token='other-token',basis='bad')),
                         ('branch', dict(branch='b',repository='r',ref='r',incarnation='i',root='root',basis='bad')),
                         ('package', dict(package='p',event='repair',scope='s',basis='bad'))]:
            with self.assertRaises(Held):
                call(self.rt, op, 'root', **args)

    def test_real_creation_guards_reserved_turn_and_clean_environment(self):
        with patch('provider.shutil.which', return_value='/public/bin/codex'):
            self.assertEqual(Codex().command, ['/public/bin/codex'])
        with patch('provider.shutil.which', return_value=None):
            with self.assertRaises(Held): Codex()
        request = self.prepare(mode='inspect')
        before = (self.root / 'rotation/codex.counter').read_text()
        popen = subprocess.Popen
        boundaries = []
        def guarded(*args, **kw):
            with self.assertRaises(ValueError):
                _fast.set_policy('false', self.root / 'fast-tier')
            with self.assertRaises(_pool.PoolBusy):
                with _pool.Pool(self.routes).admission('.codex2', blocking=False): pass
            with self.assertRaises(Held):
                call(self.rt, 'status')
            self.assertEqual(kw['env']['HOME'], str(Path.home()))
            self.assertEqual(kw['env']['CODEX_HOME'], str(Path.home() / self.raw()['attempts']['a']['pool']['profile']))
            self.assertNotIn('COORDINATOR_TOKEN', kw['env'])
            boundaries.append(args[0])
            return popen(*args, **kw)
        with patch.dict(os.environ, {'COORDINATOR_TOKEN':TOKENS['work'], 'PARENT_SECRET':'must-not-inherit'}):
            with patch('provider.subprocess.Popen', guarded):
                self.run_entry(request)
        self.assertEqual(len(boundaries), 3)
        self.assertEqual((self.root / 'rotation/codex.counter').read_text(), before)
        a = self.raw()['attempts']['a']
        self.assertTrue(a['provider_report']['final_complete'])
        self.assertNotIn('PARENT_SECRET', a['result']['env_keys'])
        self.assertIn('model_reasoning_effort="xhigh"', a['result']['args'])
        self.assertIn('service_tier="fast"', a['result']['args'])
        self.assertNotIn('-o', a['result']['args'])

    def test_low_result_supports_durable_responsibility_before_ack(self):
        self.ingest('incoming')
        h = self.raw()['events']['incoming']['source_hash']
        r = call(self.rt, 'reserve', attempt='low',event='incoming',phase='classifier',resources={},basis={})
        self.script = self.root / 'fixed_public.py'; self.script.write_text(FIXED)
        self.adapter = Codex([sys.executable,'-I',str(self.script)])
        request = dict(attempt='low',collector=r['collector'],prompt=json.dumps({'final':{'event_hash':h,'classification':'known'}}),
                       cwd=str(self.root),output_limit=8192,timeout=2,declared_secrets=[])
        self.run_entry(request)
        with self.assertRaises(Held):
            call(self.rt, 'ack',event='incoming')
        call(self.rt,'classify',event='incoming',attempt='low',collector=r['collector'],classification='known',owner='work',needs=['outcome'])
        self.assertTrue(call(self.rt,'ack',event='incoming')['ack'])
        self.assertEqual([p.returncode for p in self.adapter.originals],[0,0,0])

    def test_mcp_refusal_is_unstarted_and_cancellable_without_refund(self):
        r = self.prepare()
        self.adapter.command.append('--bad-mcp')
        with self.assertRaises(Held): self.run_entry(r)
        a = self.raw()['attempts']['a']
        self.assertEqual(a['state'],'not-started')
        self.assertIsNone(a['end'])
        self.assertEqual([p.returncode for p in self.adapter.originals],[0,0])
        call(self.rt,'cancel',attempt='a',collector=r['collector'],evidence='actual MCP refusal before task')

    def test_controls_and_revocation_between_preflight_and_task(self):
        for change in ['pool','fast','static','revoked']:
            with self.subTest(change=change):
                # Independent fresh purpose within the same suite allocation.
                self.setUp()
                r = self.prepare()
                create = self.adapter.create
                def changed(*args, **kw):
                    if self.adapter.stage == 'task':
                        if change == 'pool': _pool.Pool(self.routes).set([])
                        if change == 'fast': _fast.set_policy('false',self.root/'fast-tier')
                        if change == 'static': self.routes.write_text(self.routes.read_text()+'\n# changed static bytes\n')
                        if change == 'revoked':
                            # Synthetic Work can be revoked only as direct fixture
                            # input here; no real-role or production bypass exists.
                            with self.rt.files.transaction() as s: s['actors']['work']['active']=False
                    return create(*args,**kw)
                self.adapter.create = changed
                with self.assertRaises(Held): self.run_entry(r)
                self.assertEqual(self.raw()['attempts']['a']['state'],'not-started')
                self.assertEqual([p.returncode for p in self.adapter.originals],[0,0])

    def test_declared_secrets_before_prompt_result_and_state_publication(self):
        r = self.prepare(mode='secrets')
        r['declared_secrets']=['public-declared-secret']
        r['prompt'] = json.dumps({'mode':'secrets','value':'public-declared-secret', 'runtime':TOKENS['work'], 'collector':r['collector']})
        self.run_entry(r)
        published = json.dumps(self.raw()['attempts']['a']['result'])
        for value in r['declared_secrets']+[TOKENS['work'],r['collector']]: self.assertNotIn(value,published)
        self.assertIn('[REDACTED]',published)
        for split in range(1,25):
            redactor=Redactor(['public-declared-secret'])
            raw=b'before public-declared-secret after'
            out=b''.join(redactor.feed(raw[i:i+split]) for i in range(0,len(raw),split))+redactor.feed(b'',True)
            self.assertEqual(out,b'before [REDACTED] after')

    def test_overflow_timeout_signal_and_numeric_end_stay_distinct(self):
        for mode in ['overflow','timeout','signal']:
            with self.subTest(mode=mode):
                self.setUp();r=self.prepare(mode=mode);r['output_limit']=1024;r['timeout']=1
                self.run_entry(r)
                a=self.raw()['attempts']['a']
                self.assertIsInstance(a['end'],int)
                self.assertFalse(a['provider_report']['final_complete'])
                self.assertEqual(a['result'],{'provider_incomplete':True})
                self.assertFalse(a['reconciled'])
                if mode=='signal': self.assertEqual(a['end'],-signal.SIGTERM)
                self.assertTrue(all(p.returncode is not None for p in self.adapter.originals))

    def test_ambiguous_creation_and_lost_publication_never_replay(self):
        r=self.prepare()
        with patch('provider.subprocess.Popen',side_effect=OSError('synthetic ambiguous creation')):
            with self.assertRaises(Held): self.run_entry(r)
        self.assertEqual(self.raw()['attempts']['a']['state'],'launching')
        with self.assertRaises(Held): call(self.rt,'cancel',attempt='a',collector=r['collector'],evidence='no proof')
        with self.assertRaises(Held): self.run_entry(r)
        self.assertIsNone(self.raw()['attempts']['a']['end'])
        self.assertEqual(_sql_attempts, [])

    def test_lost_report_reply_retains_actual_end_without_inventing_collection(self):
        r = self.prepare()
        original = self.rt.call
        def lost(op, *args, **kw):
            result = original(op, *args, **kw)
            if op == 'provider_report': raise Held('synthetic reply lost after commit')
            return result
        with patch.object(self.rt, 'call', lost):
            with self.assertRaises(Held): self.run_entry(r)
        a = self.raw()['attempts']['a']
        self.assertEqual(a['state'], 'launching')
        self.assertIsNone(a['end'])
        self.assertEqual(a['provider_report']['processes'][-1]['end'], 0)
        self.assertEqual([p.returncode for p in self.adapter.originals], [0,0,0])
        with self.assertRaises(Held): self.run_entry(r)

    def test_unsupported_reviews_entry_is_explicitly_unstarted(self):
        call(self.rt,'branch','branch',branch='b',repository='public',ref='r',incarnation='i',root='external',basis='synthetic')
        call(self.rt,'review','reviews',review='review',component='c',branch='b',opaque_contract='gpt-xhigh',context='original',history='h')
        self.classify('review-event',owner='reviews')
        r=call(self.rt,'reserve','reviews',attempt='a',event='review-event',phase='review',
               resources={'review:review':'write','branch:b':'read'},basis={'review:review':0,'branch:b':0},review='review')
        self.adapter=Codex([sys.executable,'-I','unused-public-process'])
        request=dict(attempt='a',collector=r['collector'],prompt='public',cwd=str(self.root),output_limit=1024,timeout=1,declared_secrets=[])
        with self.assertRaises(Held): self.run_entry(request,'reviews')
        self.assertEqual(self.raw()['attempts']['a']['state'],'not-started')
        self.assertFalse(self.adapter.originals)

    def test_capture_io_failure_collects_original_and_refuses_task(self):
        import provider
        r=self.prepare()
        real_drain=provider.drain
        def failed_read(*args,**kw):
            with patch('provider.os.read',side_effect=OSError('synthetic pipe read fault')):
                return real_drain(*args,**kw)
        with patch('provider.drain',failed_read):
            with self.assertRaises(Held): self.run_entry(r)
        a=self.raw()['attempts']['a']
        self.assertEqual(a['state'],'not-started')
        self.assertTrue(a['provider_report']['processes'][0]['io_error'])
        self.assertIsInstance(self.adapter.originals[0].returncode,int)

    def test_cancellation_after_task_creation_collects_same_original(self):
        r=self.prepare(mode='timeout')
        create=self.adapter.create
        def cancelled(*args,**kw):
            p=create(*args,**kw)
            if self.adapter.stage=='task': self.adapter.cancel(signal.SIGTERM,None)
            return p
        self.adapter.create=cancelled
        self.run_entry(r)
        a=self.raw()['attempts']['a']
        self.assertEqual(a['end'],-signal.SIGTERM)
        self.assertFalse(a['provider_report']['final_complete'])
        self.assertEqual([p.returncode for p in self.adapter.originals],[0,0,-signal.SIGTERM])

    def test_missing_unbounded_or_ambiguous_final_cannot_be_published_as_complete(self):
        for mode,final in [('multiple',{}),(None,{'large':'x'*5000})]:
            with self.subTest(mode=mode):
                self.setUp();r=self.prepare(mode=mode,final=final)
                self.run_entry(r)
                a=self.raw()['attempts']['a']
                self.assertEqual(a['end'],0)
                self.assertFalse(a['provider_report']['final_complete'])
                self.assertEqual(a['result'],{'provider_incomplete':True})

    def test_owner_integrates_independently_validated_delta_with_incomplete_result(self):
        request = self.prepare(mode='multiple')
        self.run_entry(request)
        before = self.raw()['attempts']['a']
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0, 0])
        self.assertEqual(before['end'], 0)
        self.assertFalse(before['provider_report']['final_complete'])
        self.assertEqual(before['result'], {'provider_incomplete': True})

        # The owner checks current material, full basis and admitted footprint
        # against independent fixture evidence, then records that provenance.
        state = self.raw()
        delta = {'point:task': {'value': 'independently verified'}}
        self.assertEqual(state['versions'].get('point:task', 0), 0)
        self.assertEqual(before['basis'], {'point:task': 0})
        self.assertEqual(before['resources'], {'point:task': 'write'})
        call(self.rt, 'send', packet='validation', event='task', recipient='branch',
             payload={'basis': before['basis'], 'footprint': before['resources'],
                      'evidence': 'independent fixture material verification'})
        outcome = call(self.rt, 'integrate', attempt='a', collector=request['collector'], writes=delta)
        self.assertEqual(outcome, {'versions': {'point:task': 1}, 'external_effects': False})
        after = self.raw()['attempts']['a']
        self.assertEqual(after['result'], before['result'])
        self.assertEqual(after['provider_report'], before['provider_report'])
        self.assertEqual(after['end'], 0)
        self.assertEqual(after['delta'], delta)
        self.assertFalse(self.raw()['events']['task']['finished'])
        packet = call(self.rt, 'inbox', 'branch')['packets'][0]
        self.assertEqual(packet['payload']['evidence'], 'independent fixture material verification')

    def test_cli_provider_command_with_fixed_public_process_and_sql_blocker(self):
        r=self.prepare()
        directory=Path(__file__).resolve().parent
        wrapper='''
import builtins, pathlib, runpy, sys
directory, script, state = sys.argv[1:]
original_import = builtins.__import__
def no_sql(name, *args, **kwargs):
    if name.split('.')[0] in {'sqlite3','_sqlite3'}: raise RuntimeError('SQL forbidden')
    return original_import(name,*args,**kwargs)
builtins.__import__=no_sql
sys.path.insert(0,directory)
import provider
factory=provider.Codex
provider.Codex=lambda:factory([sys.executable,'-I',script])
sys.argv=[str(pathlib.Path(directory)/'coordinator.py'),'--state',state,'--actor','work','run-provider']
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        p=subprocess.Popen([sys.executable,'-I','-c',wrapper,str(directory),str(self.script),str(self.path)],
                           env={**os.environ,'COORDINATOR_TOKEN':TOKENS['work']},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        print('ORIGINAL_CLI_PROCESS',p.pid,flush=True)
        out,err=p.communicate(json.dumps(r).encode(),timeout=10)
        print('CLI_END',p.pid,p.returncode,flush=True)
        self.assertEqual(p.returncode,0,err)
        self.assertEqual(json.loads(out)['result']['end'],0)
        self.assertEqual(len(self.raw()['attempts']['a']['provider_report']['processes']),3)


if __name__ == '__main__':
    fixtures.check_capacity(fixtures.ARTIFACTS.parent, 8 * 1024**2, 2048)
    fixtures.ARTIFACTS.mkdir(mode=0o700, parents=True, exist_ok=False)
    unittest.main(verbosity=2)
