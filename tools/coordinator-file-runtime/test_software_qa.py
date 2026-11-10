"""Synthetic software QA contracts; no real roles/provider/profile/Board effects.

Fresh fixtures are retained under the explicitly issued OS artifact root. Source
inputs use public Git blobs only; no fake HOME or private-store discovery.
"""
import ast
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

import software_qa as qa
from runtime import Runtime, create
from storage import Held, digest, encode, check_capacity

BASE = '8663898302f4439210f37361f41166512a91958d'
ARTIFACTS = Path(os.environ['COORDINATOR_TEST_ARTIFACTS'])
REPO = Path(__file__).absolute().parents[2]
TOKENS = {'synthetic-work': 'work-only-synthetic-credential', 'synthetic-peer': 'peer-only-synthetic-credential',
          'synthetic-acceptor': 'acceptor-only-synthetic-credential'}
CASES = ['test_runtime.Trial.test_' + n for n in ('one', 'two', 'three', 'four', 'five')] + ['test_provider.ProviderTrial.test_six']
FIXED_TESTS = '''import unittest
class Trial(unittest.TestCase):
    def test_one(self): self.assertEqual(2+2,4)
    def test_two(self): self.assertTrue(True)
    def test_three(self): self.assertEqual('a'.upper(),'A')
    def test_four(self): self.assertEqual(list(range(2)),[0,1])
    def test_five(self): self.assertEqual(sum([1,2]),3)
'''
FIXED_PROVIDER = '''import unittest
class ProviderTrial(unittest.TestCase):
    def test_six(self): self.assertEqual(3*3,9)
'''


class SoftwareQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qa.directory(ARTIFACTS)
        check_capacity(ARTIFACTS, 2*1024**2, 512)
        cls.git = ARTIFACTS / 'software-qa08-public-git'
        cls.git.mkdir(mode=0o700)
        cls.originals = []
        def git(*args, cwd=None):
            p = subprocess.Popen(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(cwd or cls.git), *args],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            cls.originals.append(p)
            print('ORIGINAL_SYNTHETIC_GIT', p.pid, flush=True)
            out, _ = p.communicate(timeout=10)
            print('SYNTHETIC_GIT_END', p.pid, p.returncode, flush=True)
            if p.returncode: raise AssertionError('fixture Git failed')
            return out
        cls.git_call = staticmethod(git)
        cls.hashes = {}
        for name in qa.PUBLIC:
            if name == qa.PREFIX + 'software_qa.py': raw = Path(qa.__file__).read_bytes()
            elif name == qa.PREFIX + 'test_runtime.py': raw = FIXED_TESTS.encode()
            elif name == qa.PREFIX + 'test_provider.py': raw = FIXED_PROVIDER.encode()
            else: raw = git('show', BASE + ':' + name, cwd=REPO)
            target = cls.git / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(raw)
            cls.hashes[name] = qa.sha(raw)
        # An untracked private-shaped sentinel is never exported/acquired.
        git('init', '--quiet')
        git('add', '--', *qa.PUBLIC)
        git('-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'fixed public test inputs')
        cls.commit = git('rev-parse', 'HEAD').decode().strip()
        (cls.git / 'untracked-sentinel').write_text('untracked synthetic marker')

    def setUp(self):
        self.root = ARTIFACTS / self._testMethodName
        self.root.mkdir(mode=0o700)
        check_capacity(self.root, 1024**2, 256)
        routes = self.root / 'routes.toml'
        routes.write_text('[providers.codex]\npool=[".codex2"]\nmanual_profiles=[".codex2",".codex3",".codex4",".codex5"]\n[rotation]\nstate_dir=' + json.dumps(str(self.root/'rotation')) + '\n')
        (self.root / 'fast-tier').write_text('true\n')
        create(self.root / 'state', 'synthetic-work', TOKENS['synthetic-work'], routes)
        self.rt = Runtime(self.root / 'state')
        for actor in ('synthetic-peer', 'synthetic-acceptor'):
            self.call('invite', target=actor, role='QA', invitation_token=TOKENS[actor], basis='synthetic issued identity')
        self.peer = qa.Peer(self.rt, 'synthetic-peer', TOKENS['synthetic-peer'])
        self.peer.adopt('synthetic actual executable encounter')
        self.call('adopt', 'synthetic-acceptor', basis='synthetic separate recipient')
        self.classify('work-intake', 'synthetic-work')
        self.classify('qa-event', 'synthetic-peer')
        self.call('package', package='synthetic-package', event='qa-event', scope='synthetic six fixed tests', basis='synthetic Work current authority')
        event = self.call('readback', kind='event', id='qa-event')['value']
        self.grant = {'schema': 1, 'job': 'synthetic-job', 'attempt': 'synthetic-original-attempt', 'event': 'qa-event',
            'event_source_hash': event['source_hash'], 'package': 'synthetic-package', 'scope': 'synthetic six fixed tests',
            'source': 'synthetic immutable public source', 'policy': 'synthetic bounded test policy', 'authority': 'synthetic Work current authority',
            'config_actor': 'synthetic-work', 'controller': 'synthetic-peer', 'workers': ['synthetic-peer']*5,
            'acceptor': 'synthetic-acceptor', 'commit': self.commit, 'inputs': self.hashes,
            'program_sha256': self.hashes[qa.PREFIX+'software_qa.py'], 'repository': str(self.git),
            'retained_root': str(self.root/'original-retained'), 'inventory': CASES,
            'partitions': [CASES[:2], *[[c] for c in CASES[2:]]], 'execute_attempt': 'qa-execution', 'consolidate_attempt': 'qa-consolidation',
            'resources': {'qa:synthetic-package': 'read'}, 'basis': {'qa:synthetic-package': 0},
            'limits': {'workers': 5, 'seconds': 10, 'capture_bytes': 65536, 'output_bytes': 1048576, 'output_entries': 256},
            'result_packet': 'qa-result', 'receive_packet': 'qa-grant', 'procedure': 'runtime-provider-unittest-v1'}
        self.issue()

    def call(self, op, actor='synthetic-work', **kw):
        return self.rt.call(op, actor, TOKENS[actor], **kw)

    def classify(self, event, owner):
        self.call('ingest', event=event, payload={'synthetic': event}, producer='synthetic', source_basis='fixture intent')
        e = self.call('readback', kind='event', id=event)['value']
        r = self.call('reserve', event=event, attempt='class-'+event, phase='classifier', resources={}, basis={})
        c = r['collector']
        s = self.call('start', attempt=r['attempt'], collector=c, substrate='owner-encounter', evidence='synthetic typed LOW only')
        self.call('collect', attempt=r['attempt'], collector=c, launch_id=s['launch_id'], end=0,
                  result={'event_hash':e['source_hash'],'classification':'known'}, evidence='synthetic classification; not actual operating LOW')
        self.call('classify', event=event, attempt=r['attempt'], collector=c, classification='known', owner=owner, needs=['outcome'])
        self.call('reconcile', attempt=r['attempt'], collector=c, evidence='synthetic no effects')
        self.call('ack', event=event)

    def issue(self):
        self.call('send', packet=self.grant['receive_packet'], event='work-intake', recipient='synthetic-peer', payload={'software_qa_grant':digest(self.grant)})

    def result(self):
        return qa.get(Path(self.grant['retained_root'])/'outputs/runner.json')

    def test_real_five_workers_separate_consolidation_digest_and_receipts(self):
        result = self.peer.run(self.grant)
        self.assertEqual(result['outcome'], 'success')
        record = self.result()
        self.assertEqual(result['digest'], digest(record))
        parts = record['partitions']
        self.assertEqual(len(parts), 5)
        self.assertEqual(len({p['collection']['pid'] for p in parts}), 5)
        driver = record['execution']['collection']['pid']
        self.assertTrue(all(p['controller_pid'] == driver and p['result']['controller_pid'] == driver for p in parts))
        self.assertEqual(len(self.peer.processes.originals[-2:]), 2)
        self.assertTrue(all(type(p.returncode) is int for p in self.peer.processes.originals))
        self.assertNotEqual(driver, record['consolidation']['collection']['pid'])
        self.assertEqual(record['inputs_after'], self.hashes)
        self.assertEqual(sorted(c['id'] for c in record['consolidation']['result']['cases']), sorted(CASES))
        inbox = self.call('inbox', 'synthetic-acceptor')['packets']
        self.assertEqual(inbox[0]['payload']['digest'], result['digest'])
        self.assertEqual(inbox[0]['stage'], 'pending')
        for stage in ('picked-up','processed','settled'):
            self.call('receipt', 'synthetic-acceptor', packet='qa-result', stage=stage, evidence='synthetic recipient own '+stage)
        e = self.call('readback', kind='event', id='qa-event')['value']
        self.assertIsNone(e['processed_at'])
        self.assertIn('source', e['holds'])
        self.assertFalse(inbox[0]['payload']['semantic_acceptance'])
        self.assertFalse((Path(self.grant['retained_root'])/'inputs/untracked-sentinel').exists())

    def test_settlement_retry_does_not_launch_or_replay(self):
        self.peer.run(self.grant)
        n = len(self.peer.processes.originals)
        with patch.object(subprocess, 'Popen', side_effect=AssertionError('metadata must not launch')):
            self.peer.settle(self.grant, self.result())
        self.assertEqual(n, len(self.peer.processes.originals))
        with self.assertRaises(Held): self.peer.run(self.grant)
        self.assertEqual(n, len(self.peer.processes.originals))

    def test_controller_workers_and_configuration_never_acceptor(self):
        for field in ('controller','config_actor'):
            g = copy.deepcopy(self.grant); g[field] = g['acceptor']
            with self.assertRaises(Held): qa.validate(g)
        g = copy.deepcopy(self.grant); g['workers'][0] = g['acceptor']
        with self.assertRaises(Held): qa.validate(g)
        self.assertEqual(self.peer.processes.originals, [])

    def test_complete_inventory_partition_and_grant_authority_refusals(self):
        for change in ('duplicate','drop','unknown','changed-authority'):
            g = copy.deepcopy(self.grant)
            if change == 'duplicate': g['partitions'][1][0] = g['partitions'][0][0]
            if change == 'drop': g['partitions'][-1] = []
            if change == 'unknown': g['procedure'] = 'arbitrary-shell'
            if change == 'changed-authority': g['authority'] = 'unissued'
            with self.assertRaises(Held): self.peer.run(g)
        self.assertEqual(self.peer.processes.originals, [])

    def test_sql_import_negative_control_and_cli_guard(self):
        with self.assertRaisesRegex(RuntimeError, 'SQLite unavailable'): __import__('sqlite3')
        with self.assertRaisesRegex(RuntimeError, 'SQLite unavailable'): __import__('_sqlite3')
        proc = qa.Processes()
        p = proc.popen([sys.executable, '-I', '-B', str(Path(qa.__file__).absolute()), '--help'], self.root, None, 'actual-entrypoint')
        row = qa.capture([p], 4096, 5, [TOKENS['synthetic-peer']])[0]
        self.assertEqual(row['end'], 0)
        self.assertTrue(row['complete'])
        self.assertIn(b'Bounded software QA', row['log'])

    def test_guarded_blob_export_read_only_full_manifest_and_tamper(self):
        m = qa.export(self.grant, self.peer.processes)
        self.assertEqual(set(m['files']), set(qa.PUBLIC))
        self.assertEqual(m['retained_root'], self.grant['retained_root'])
        self.assertEqual(qa.inputs(self.grant), self.hashes)
        target = Path(self.grant['retained_root'])/'inputs'/qa.PREFIX/'fixture_worker.py'
        target.chmod(0o600); target.write_text('changed')
        with self.assertRaises(Held): qa.inputs(self.grant)

    def test_nonwhitelisted_and_untracked_or_linked_inputs_refuse(self):
        g = copy.deepcopy(self.grant); g['inputs']['untracked-sentinel'] = '0'*64
        with self.assertRaises(Held): qa.validate(g)
        # Immutable Git mode 120000 is rejected before acquiring a target body.
        processes = qa.Processes(); real = processes.git
        def linked(repo, args, maximum=qa.MAX_SOURCE):
            if args[0] == 'ls-tree': return ('120000 blob '+'0'*40+'\t'+args[-1]+'\n').encode()
            return real(repo, args, maximum)
        with patch.object(processes, 'git', linked):
            with self.assertRaises(Held): qa.export(self.grant, processes)

    def test_original_objects_before_capture_timeout_overflow_and_secrets(self):
        processes = qa.Processes()
        p = processes.popen([sys.executable, '-I', '-c', "import os,time;os.write(1,b'public-secret');time.sleep(2)"], self.root, None, 'fixed-timeout')
        self.assertIs(processes.originals[0], p)
        row = qa.capture([p], 4096, .1, ['public-secret'])[0]
        self.assertTrue(row['timeout']); self.assertIsInstance(row['end'], int)
        self.assertNotIn(b'public-secret', row['log'])
        p = processes.popen([sys.executable, '-I', '-c', "import os;os.write(1,b'x'*100000)"], self.root, None, 'fixed-overflow')
        row = qa.capture([p], 4096, 2, [TOKENS['synthetic-peer']])[0]
        self.assertTrue(row['overflow']); self.assertFalse(row['complete']); self.assertLessEqual(len(row['log']),4096)

    def test_creation_ambiguity_retains_original_and_forbids_relaunch(self):
        real = self.peer.processes.popen
        def failed(command, cwd, payload, stage, guard=None):
            p = real(command, cwd, payload, stage, guard)
            if stage == 'execute':
                qa.kill(p); p.wait(timeout=5); p.stdin.close(); p.stdout.close()
                raise OSError('synthetic postcreation ambiguity')
            return p
        with patch.object(self.peer.processes, 'popen', failed):
            with self.assertRaises(OSError): self.peer.run(self.grant)
        a = self.call('readback','synthetic-peer',kind='attempt',id='qa-execution')['value']
        self.assertEqual(a['state'],'launching'); self.assertIsNone(a['end'])
        n=len(self.peer.processes.originals)
        with self.assertRaises(Held): self.peer.run(self.grant)
        self.assertEqual(n,len(self.peer.processes.originals))

    def test_partial_publication_collection_keeps_unreconciled_and_no_acceptance(self):
        real = qa.put
        def fail(path,value,mode=0o400):
            if path.name == 'execute.json': raise OSError('synthetic publication failure')
            return real(path,value,mode)
        with patch.object(qa,'put',fail):
            with self.assertRaises(OSError): self.peer.run(self.grant)
        a=self.call('readback','synthetic-peer',kind='attempt',id='qa-execution')['value']
        self.assertEqual(a['state'],'launching'); self.assertFalse(a['reconciled'])
        self.assertTrue(all(type(p.returncode) is int for p in self.peer.processes.originals))
        self.assertEqual(self.call('inbox','synthetic-acceptor')['packets'],[])

    def test_consolidation_consumes_exact_five_digests_and_truthful_failure(self):
        self.peer.run(self.grant)
        record = self.result(); out=Path(self.grant['retained_root'])/'outputs'
        m=record['manifest']
        part=qa.get(out/'partition-0.json')
        part['result']['cases'][0]['status']='failure'
        # A distinctly synthetic fault injection, with corresponding current
        # record digest updated. No actual earlier successful result is relabeled.
        path=out/'partition-0.json';path.chmod(0o600);path.write_bytes(encode(part))
        e=qa.get(out/'execute.json');e['result']['records'][0]=digest(part)
        path=out/'execute.json';path.chmod(0o600);path.write_bytes(encode(e))
        c=qa.consolidate(self.grant,m)
        self.assertEqual(c['outcome'],'failure');self.assertTrue(c['failures']);self.assertFalse(c['semantic_acceptance'])
        part['binding']['attempt']='different-attempt'
        path=out/'partition-0.json';path.write_bytes(encode(part))
        with self.assertRaises(Held):qa.consolidate(self.grant,m)

    def test_discovery_missing_and_skipped_cases_remain_unknown(self):
        self.peer.run(self.grant)
        out=Path(self.grant['retained_root'])/'outputs';r=self.result()
        part=qa.get(out/'partition-0.json');part['result']['cases'][0]['status']='skipped'
        part['result']['discovered']=[]
        p=out/'partition-0.json';p.chmod(0o600);p.write_bytes(encode(part))
        e=qa.get(out/'execute.json');e['result']['records'][0]=digest(part)
        p=out/'execute.json';p.chmod(0o600);p.write_bytes(encode(e))
        c=qa.consolidate(self.grant,r['manifest'])
        self.assertEqual(c['outcome'],'unknown');self.assertTrue(c['unknowns'])

    def revised_candidate(self, runtime_tests, provider_tests, inventory):
        g = copy.deepcopy(self.grant)
        for leaf, raw in [('test_runtime.py', runtime_tests), ('test_provider.py', provider_tests)]:
            (self.git / qa.PREFIX / leaf).write_bytes(raw)
            g['inputs'][qa.PREFIX + leaf] = qa.sha(raw)
        self.git_call('add', '--', qa.PREFIX+'test_runtime.py', qa.PREFIX+'test_provider.py')
        self.git_call('-c','user.name=Synthetic Fixture','-c','user.email=fixture@example.invalid',
                      '-c','commit.gpgsign=false','commit','--quiet','-m','new immutable fixed test condition')
        g['commit'] = self.git_call('rev-parse','HEAD').decode().strip()
        g['inventory'] = inventory
        g['partitions'] = [inventory[i::5] for i in range(5)]
        g['receive_packet'] = 'qa-revised-grant'
        self.grant = g
        self.issue()

    def test_actual_failed_test_and_separate_successful_consolidation_end(self):
        self.revised_candidate(FIXED_TESTS.replace('2+2,4','2+2,5').encode(), FIXED_PROVIDER.encode(), CASES)
        result = self.peer.run(self.grant)
        record = self.result()
        self.assertEqual(result['outcome'],'failure')
        self.assertEqual(record['consolidation']['collection']['end'],0)
        self.assertTrue(record['consolidation']['result']['failures'])
        self.assertFalse(result['semantic_acceptance'])

    def test_complete_current_core_regressions_through_actual_cli(self):
        runtime_tests = self.git_call('show',BASE+':'+qa.PREFIX+'test_runtime.py',cwd=REPO)
        provider_tests = self.git_call('show',BASE+':'+qa.PREFIX+'test_provider.py',cwd=REPO)
        inventory = []
        for module, raw, cls in [('test_runtime',runtime_tests,'Trial'),('test_provider',provider_tests,'ProviderTrial')]:
            tree = ast.parse(raw)
            for node in tree.body:
                if isinstance(node,ast.ClassDef) and node.name == cls:
                    inventory.extend(module+'.'+cls+'.'+f.name for f in node.body
                                     if isinstance(f,ast.FunctionDef) and f.name.startswith('test_'))
        self.assertEqual(len(inventory),52)
        self.revised_candidate(runtime_tests,provider_tests,sorted(inventory))
        self.grant['limits']['seconds'] = 120
        self.grant['limits']['output_bytes'] = 6*1024**2
        self.grant['limits']['output_entries'] = 2048
        self.grant['receive_packet'] = 'qa-full-current-grant'
        self.issue()
        p = subprocess.Popen([sys.executable,'-I','-B',str(Path(qa.__file__).absolute()),
                              '--state',str(self.rt.files.path),'--actor','synthetic-peer','run'],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1','COORDINATOR_TOKEN':TOKENS['synthetic-peer']},
                              start_new_session=True)
        self.peer.processes.originals.append(p)
        print('ORIGINAL_ACTUAL_SOFTWARE_CLI',p.pid,flush=True)
        p.stdin.write(encode({'grant':self.grant,'declared_secrets':[]}));p.stdin.flush()
        row = qa.capture([p],65536,150,[TOKENS['synthetic-peer']])[0]
        print('ACTUAL_SOFTWARE_CLI_END',row['end'],flush=True)
        self.assertEqual(row['end'],0,row['log'].decode())
        value=json.loads(row['log'])
        self.assertEqual(value['result']['outcome'],'success')
        record=self.result()
        cases=record['consolidation']['result']['cases']
        self.assertEqual(sorted(c['id'] for c in cases),sorted(inventory))
        self.assertTrue(all(c['status']=='success' for c in cases))
        qa.put(self.root/'current-core-summary.json',{'cases':cases,'runner_digest':value['result']['digest'],
               'runner':value['result']['runner'],'actual_cli_end':row['end'],'outcome':value['result']['outcome']})

    def test_current_revocation_stops_actual_creation(self):
        self.peer.accept_grant(self.grant)
        self.call('revoke',target='synthetic-peer',reason='synthetic current revocation')
        with self.assertRaises(Held):self.peer.run(self.grant)
        self.assertEqual(self.peer.processes.originals,[])


if __name__ == '__main__':
    unittest.main(verbosity=2)
