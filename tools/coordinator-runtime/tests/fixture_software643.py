"""Two distinct no-network operations through unpatched production selection,
validation and reservation. Fictional logical SDK/clock/classifier seams only.
Owned fixtures are retained; no live operation or native authenticity claimed.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from contextlib import nullcontext
import unittest
from unittest.mock import patch

from support import config_at, enrolled
from coordinator_runtime import resource_scopes as resources, processing, prospective
from coordinator_runtime.contracts import Refusal, digest, encode, ident


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LogicalBoard:
    """Fictional SDK principal/grant seam; policy/admission checks stay real."""
    def __init__(self, fixture, role):
        self.fixture, self.role, self.store = fixture, role, self
        self.grant = fixture.store.enrollment(role)['grant_id']
        self.owner = fixture.config['roles'][role]['owner']

    def acting_session(self, expected):
        if self.fixture.actor != expected:
            raise Refusal('fictional SDK: caller is not actual selected Work')
        return self.fixture.actor

    def verify_authority(self, runtime):
        e = runtime.enrollment(self.role)
        if e['owner'] != self.owner or e['grant_id'] != self.grant or self.role in self.fixture.denied:
            raise Refusal('fictional SDK: current original role/grant unavailable')

    def retained_basis(self, runtime):
        return {'events': []}

    def future_frontier(self):
        return 0

    def opened(self, **kwargs):
        return nullcontext(None)

    def _original(self, conn, runtime):
        self.verify_authority(runtime)
        return {'issued_by': self.fixture.config['roles']['Work']['owner']}

    def _usage(self, conn, grant):
        return dict(shared_rows=0, shared_payload_bytes=0, runtime_rows=0)


class SoftwareFixture643(unittest.TestCase):
    variant = 'alpha'

    def setUp(self):
        self.area = Path(os.environ['COORDINATOR_TEST_FIXTURES']) / ident()
        self.area.mkdir()
        self.now = 1000.
        self.repo = self.area / 'repo'
        self.repo.mkdir()
        self.git('init', '--initial-branch=source')
        (self.repo / 'source.txt').write_text('first\n')
        self.git('add', 'source.txt')
        self.commit('first ' + self.variant)
        parent = self.git('rev-parse', 'HEAD')
        (self.repo / 'source.txt').write_text('second\n')
        self.git('add', 'source.txt')
        self.commit('second')
        self.head = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.parents = [parent]
        if self.variant == 'beta':
            # Different source topology as well as observation/commands/output.
            merged = self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                              'commit-tree',self.tree,'-p',self.head,'-p',parent,'-m','beta two parents')
            self.parents = [self.head,parent]
            self.git('update-ref','refs/heads/source',merged,self.head)
            self.head = merged
        self.config = config_at(self.area)
        task = self.config['tasks']['qa-execution']
        task.update(effects='owner-reconcile', require_package_scope=True,
                    scope_roots=[str(self.area)])
        task['effect_authority']['operations'] = ['execute-admitted-qa']
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.store.db.execute("UPDATE enrollments SET legacy_hold='old global UNKNOWN' WHERE role='QA'")
        self.genuine = {'fixture_only': True}
        self.statement = dict(observation=self.variant, fact='No additional positively bound relevant conflict; global UNKNOWN retained')
        self.procedure = self.area / 'procedure.md'
        self.procedure.write_text('Fictional bounded ordinary procedure, never executed.\n')
        self.selected = self.area / 'selected'
        self.selected.mkdir()
        self.files = {}
        for filename in ['qa_selected_tests.py','qa_resource_readback.py','TEST-SELECTION.json']:
            path = self.selected / filename
            path.write_text(json.dumps({'variant':self.variant})+'\n' if filename.endswith('.json') else '# '+self.variant+'\nraise SystemExit(0)\n')
            self.files[filename] = sha(path)
        self.output = self.area / 'output'
        self.output.mkdir()
        self.scope = dict(cwd=str(self.repo), read_roots=[str(self.repo), str(self.procedure),
                          *[str(self.selected / f) for f in self.files]],
                          write_roots=[str(self.output)], network=False, procedure=str(self.procedure),
                          resource_evidence='Fictional independently admitted finite scope')
        executable = '/usr/bin/python3.12'
        self.p = dict(kind='local-qa', git='/usr/bin/git', git_sha256=sha('/usr/bin/git'),
                      repository=str(self.repo), source_ref='refs/heads/source', source_head=self.head,
                      procedure_sha256=sha(self.procedure), timeout=1, max_output=4096,
                      resources=[dict(key='fixture-output', owner=self.config['roles']['QA']['owner'],
                                      authority='Fictional lease', expires=1100.)],
                      acceptor=ident(), acceptance_authority='Fictional independent acceptor', known_exits=[0,1],
                      source_capture=dict(bwrap='/usr/bin/bwrap', sha256=sha('/usr/bin/bwrap'), max_bytes=1024, max_files=10),
                      public_executables={label:dict(path=executable, bytes=Path(executable).stat().st_size,
                                                    sha256=sha(executable)) for label in ('command','readback')})
        for label, filename in [('command','qa_selected_tests.py'), ('readback','qa_resource_readback.py')]:
            self.p[label] = dict(argv=[executable, '-B', str(self.selected / filename)],
                                 executable_sha256=sha(executable), script_sha256=self.files[filename],
                                 stdout='FIXTURE '+self.variant+' COMPLETE\n' if label == 'readback' else None)
        self.scope['ordinary_effects'] = self.p
        self.admit()
        admission = self.store.one('SELECT * FROM admissions WHERE package=?', ('fictional-package',))
        self.record = dict(original_hold='old global UNKNOWN', roots=[], unbounded=True,
                           evidence='Positive operation-relative set empty; global original custody UNKNOWN',
                           qa_operation=dict(statement=self.statement, binding=dict(task='qa-execution',
                               package='fictional-package', admission_sha256=digest(admission))))
        self.record['qa_operation']['policy'] = dict(
            version='qa-operation-v1', custodian=self.config['roles']['QA']['owner'],
            reference='fictional owned observation ' + self.variant, statement_sha256=digest(self.statement),
            authority='Fictional Work accountable operation-relative choice; not native authentication', expires=1090.,
            scope=copy.deepcopy(self.scope), source=dict(common_git=str(self.repo/'.git'), tree=self.tree, parents=self.parents),
            inputs=[dict(path=str(self.selected/f),sha256=v) for f,v in self.files.items()], relevant_roots=[])
        self.actor = self.config['roles']['Work']['owner']
        self.denied = set()
        self.config['software_delegation'] = {'grantor':self.actor}
        self.boards = {r:LogicalBoard(self,r) for r in self.config['roles']}
        self.selection = dict(basis=processing.basis(self.store,self.boards),
            authority='Fictional Work issuance of exact whole scoped policy',
            retained_events=[], recover_controls={}, future_intake=True, tasks=list(self.config['tasks']),
            max_shared_rows=1000,max_shared_payload_bytes=1000000,max_runtime_rows=1000,
            service=dict(max_inflight=2,reviews={},legacy_resources={'QA':self.record}))
        self.cap = processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing = processing.Access(self.store,self.cap,self.boards)
        self.epoch = prospective.select(self.store, self.config['roles']['Work']['owner'], dict(
            configuration=digest(self.config), authority='Fictional explicit bounded Work decision', expires=1100.,
            processing_capability=self.cap, grants={'QA':self.store.enrollment('QA')['grant_id']},
            tasks={'qa-execution':dict(task_hash=digest(task), software_handoffs={}, ordinary_effects='admitted-v1')}))
        self.pending = dict(role='QA', phase='execution', task='qa-execution', package='fictional-package')

    def git(self, *args):
        command = ['/usr/bin/git','-C',str(self.repo),*args]
        result = subprocess.run(command, capture_output=True, text=True,
                                env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'})
        with (self.area / 'original-ends.jsonl').open('a') as target:
            target.write(encode(dict(argv=command, end=result.returncode, stdout=result.stdout, stderr=result.stderr))+'\n')
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout.strip()

    def commit(self, message):
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                 '-c','commit.gpgsign=false','commit','-m',message)

    def admit(self):
        self.store.admit('fictional-package',self.config['roles']['Branch']['owner'],
                         dict(task_scopes={'qa-execution':self.scope}))

    def save(self):
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',
                              (encode(self.selection),self.cap))

    def blocked(self):
        return resources.blocked(self.store,self.pending)
