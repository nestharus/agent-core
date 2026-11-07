"""Owned offline Reviews boundary witnesses; no provider/native acceptance.

CurrentConfiguration supplies NULL-native Board/configuration/membership seams.
Executor, package narrowing, material Git reads and reader run unchanged. Launch
authority/attempt advice are explicit seams, never genuine Work authorization.
"""
import asyncio
from contextlib import asynccontextmanager
import copy
import json
from pathlib import Path
import shlex
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from coordinator_runtime import configuration, local_native, reviews, service_recovery
from coordinator_runtime.contracts import Refusal, digest, encode
import test_configuration308 as fixture


class ReachedFacade(Exception):
    pass


class ReviewsCeiling(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        engine, store = fixture.engine_config, fixture.Store
        def config(directory):
            value = engine(directory)
            value['tasks']['rp'] = {**copy.deepcopy(value['tasks']['wp']), 'role':'Reviews'}
            return value
        def runtime(value, **kwargs):
            neutral = Path(value['state_dir']).parent/'neutral'; neutral.mkdir()
            task = value['tasks']['rp']
            task.update(cwd=str(neutral), startup='explicit-packet', network=False,
                        scope_roots=[str(Path(value['state_dir']).parent)])
            task['effect_authority']['read_roots'] = [str(neutral)]
            task['effect_authority']['operations'] = ['read-source']
            for role, selected in value['roles'].items():
                selected['routes'] = [n for n,t in value['tasks'].items() if t['role'] == role]
            return store(value, **kwargs)
        # Extend the ancestor's explicit NULL-native schema projection to
        # review contexts; production schema and native identities stay intact.
        with patch.object(fixture,'engine_config',side_effect=config), patch.object(fixture,'Store',side_effect=runtime):
            with patch.object(reviews,'SCHEMA',reviews.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT')):
                self.f.setUp()
        self.s = self.f.runtime
        self.repo = self.f.directory/'external'; self.repo.mkdir()
        self.git('init','-q')
        self.allowed = 'A[1].py' if self._testMethodName == 'test_exact_filename_cannot_expand_as_git_pathspec' else 'A.py'
        (self.repo/self.allowed).write_text('admitted_public_A = True\n')
        (self.repo/'B.py').write_text('owned_outside_ceiling_B = True\n')
        (self.repo/'A1.py').write_text('owned_outside_ceiling_pathspec_neighbor = True\n')
        self.git('add',self.allowed,'B.py','A1.py')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                 '-c','commit.gpgsign=false','commit','-qm','owned public sentinel fixture')
        self.head = self.git('rev-parse','HEAD').strip()
        self.method = self.f.directory/'procedure.md'; self.method.write_text('Owned bounded fixture procedure.\n')
        entry = {'configuration':digest(self.s.config),'role_owner':'fictional-Reviews',
                 'original_grant':'fictional-grant-Reviews','authority':'fictional Work selection',
                 'source_authority':'fictional owner exact public A binding',
                 'read_roots':[str(self.repo/self.allowed)], 'repository_reads':[str(self.repo)],
                 'components':{'component':[self.allowed]},'safe_files':{},
                 'source':{'repository':str(self.repo),'commit':self.head,
                           'files':{self.allowed:reviews.sha((self.repo/self.allowed).read_bytes())}}}
        self.s.config = configuration.candidate(self.s,str(self.f.directory/'extended.json'),[],
                                scope_options={'read_ceiling_extensions':{'rp':entry}})
        self.s.db.executescript(reviews.SCHEMA + service_recovery.SCHEMA)
        self.s.processing = SimpleNamespace(key='fictional-processing-proof-seam')
        self.authorized = Mock(); self.s.authorize_launch = self.authorized
        self.s.attempt = lambda attempt:{'begin':1,'profile':None}
        self.policy = {'method':str(self.method),'method_files':{str(self.method):reviews.sha(self.method.read_bytes())},
                       'routes':{None:'fictional-route'},'deadline':2,
                       'components':{'component':{'repository':str(self.repo),'origin':'fixture-origin',
                           'paths':[self.allowed],'history':str(self.s.home/'review-history/component'),
                           'authority':'fictional source statement cannot expand roots'}}}
        self.packet = {'component':'component','origin':'fixture-origin','base':self.head,
                       'head':self.head,'previous':None,'answered_ids':[]}
        self.job = {'task':'rp','package':'fictional-package'}
        self.admission = {'receipt':encode({'task_scopes':{'rp':{
            'cwd':self.s.config['tasks']['rp']['cwd'],'read_roots':[str(self.repo/self.allowed)],
            'write_roots':[],'repository_reads':[str(self.repo)],'network':False,
            'procedure':str(self.method),'resource_evidence':'fictional package owner evidence'}}})}
        self.s.db.execute('INSERT INTO admissions(package,owner,receipt,accepted) VALUES(?,?,?,NULL)',
                          ('fictional-package','fictional-package-owner',self.admission['receipt']))

    def git(self,*args):
        result = subprocess.run(['/usr/bin/git','-C',str(self.repo),*args],capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr.decode()); return result.stdout.decode()

    def execute(self, transport=None):
        return asyncio.run(reviews.Executor(self.s,transport).execute(self.job,'fictional-attempt',self.policy,self.packet))

    def positive(self, scoped=False):
        self.s.config['tasks']['rp']['require_package_scope'] = scoped
        case = self
        class Probe:
            async def call(inner,runtime,attempt,policy,context,directory,text,commands,**kwargs):
                manifest = json.loads(Path(shlex.split(commands[0])[-1]).read_text())
                case.assertEqual(set(manifest['source']),{case.head+':'+case.allowed})
                case.assertIn('READ_COMMAND=',text)
                labels = []
                for _ in range(8):
                    r = subprocess.run(shlex.split(commands[0]),capture_output=True,timeout=15)
                    case.assertEqual(r.returncode,0,r.stderr.decode())
                    chunk = json.loads(r.stdout)
                    if chunk.get('end_of_material'): break
                    labels.append(chunk['source'])
                    if chunk['source'].endswith(':'+case.allowed):
                        case.assertIn('admitted_public_A',chunk['text'])
                else: case.fail('facade did not reach end_of_material')
                case.assertIn(case.head+':'+case.allowed,labels)
                raise ReachedFacade()
        with self.assertRaises(ReachedFacade): self.execute(Probe())
        self.authorized.assert_called_with('fictional-attempt')

    def negative(self, scoped=False, path='B.py', relationship=False):
        self.s.config['tasks']['rp']['require_package_scope'] = scoped
        selected = self.policy['components']['component']
        selected['relationship_paths' if relationship else 'paths'] = [path]
        with patch.object(reviews,'material',side_effect=AssertionError('material metadata/body acquired')) as acquire:
            with patch.object(reviews,'git',side_effect=AssertionError('source Git metadata/body acquired')):
                with self.assertRaisesRegex(Refusal,'outside current delegated task read authority'):
                    self.execute()
        acquire.assert_not_called()

    def test_unscoped_exact_A_reaches_real_material_and_read_facade(self): self.positive()
    def test_exact_filename_cannot_expand_as_git_pathspec(self): self.positive()
    def test_unscoped_B_refuses_before_material_metadata_or_body(self): self.negative()
    def test_unscoped_directory_refuses_before_recursive_listing(self): self.negative(path='.')
    def test_unscoped_relationship_B_refuses_before_material(self): self.negative(relationship=True)
    def test_scoped_exact_A_reaches_real_material_and_read_facade(self): self.positive(scoped=True)
    def test_scoped_B_refuses_before_material_metadata_or_body(self): self.negative(scoped=True)

    def test_missing_package_admission_refuses_before_material(self):
        self.s.config['tasks']['rp']['require_package_scope'] = True
        self.job['package'] = 'missing'
        with patch.object(reviews,'material',side_effect=AssertionError('material acquired')) as acquire:
            with self.assertRaisesRegex(Refusal,'actual package procedure'): self.execute()
        acquire.assert_not_called()

    def test_native_identity_operand_is_distinct_from_file_permission(self):
        for scoped in (False, True):
            self.s.config['tasks']['rp']['require_package_scope'] = scoped
            local_native.source_roots(self.s,self.job,str(self.repo),repository=True)
            local_native.source_roots(self.s,self.job,str(self.repo/'A.py'))
            with self.assertRaisesRegex(Refusal,'outside genuine role read authority'):
                local_native.source_roots(self.s,self.job,str(self.repo/'B.py'))

    def test_actual_native_wrapper_invokes_only_owned_failure_producer(self):
        writer = self.f.directory/'caller'
        writer.write_text('''#!/usr/bin/python3
import json,pathlib,shlex,subprocess,sys
args=sys.argv
allow=json.loads(pathlib.Path(args[args.index('--allow-file')+1]).read_text())
labels=[]
for i in range(8):
 r=subprocess.run(shlex.split(allow[0]),capture_output=True,timeout=15,check=True)
 chunk=json.loads(r.stdout)
 if chunk.get('end_of_material'):break
 labels.append(chunk['source'])
else:raise SystemExit(8)
out=pathlib.Path(args[args.index('--out')+1]);out.mkdir()
(out/'result.json').write_text(json.dumps({'class':'incomplete','fixture':True}))
(out/'final.md').write_text(json.dumps(labels))
print('owned caller fixture only; no native root',flush=True)
raise SystemExit(7)
''')
        writer.chmod(0o700)
        self.policy.update(caller=str(writer),caller_sha256=reviews.sha(writer.read_bytes()))
        @asynccontextmanager
        async def admission(profile):
            self.assertIsNone(profile)
            yield  # Explicit no-account admission seam, no real allocation.
        self.s.execution_pool = SimpleNamespace(admission=admission)
        with self.assertRaisesRegex(Refusal,'actual native root identity missing'):
            self.execute()
        directory = self.s.home/'artifacts/fictional-attempt/review-call-0'
        original = json.loads((directory/'original.json').read_text())
        self.assertEqual(original['actual_END'],7)
        self.assertEqual(original['capture_errors'],[])
        self.assertIn(self.head+':A.py',json.loads((directory/'native/final.md').read_text()))
        self.assertIn('owned caller fixture only',(directory/'caller.stdout').read_text())
