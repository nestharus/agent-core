"""Real public policy/admission/resource APIs, contained owned Git fixtures.

The genuine public QA JSON is tested unmodified without following its paths.
Executable cases translate its paths/pins into fiction and patch ONLY the
trusted statement/file/oracle constants. Grants are explicit logical seams;
no real QA admission, owner, provider, native or procedure execution is claimed.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import config_at, enrolled
from coordinator_runtime import resource_scopes as resources, processing, prospective
from coordinator_runtime.contracts import Refusal, digest, encode, ident


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Operation616(unittest.TestCase):
    def setUp(self):
        self.area = Path('/fixtures') / ident()
        self.area.mkdir()
        self.now = 1000.
        self.repo = self.area / 'repo'
        self.repo.mkdir()
        self.git('init', '--initial-branch=source')
        (self.repo / 'source.txt').write_text('first\n')
        self.git('add', 'source.txt')
        self.commit('first')
        parent = self.git('rev-parse', 'HEAD')
        (self.repo / 'source.txt').write_text('second\n')
        self.git('add', 'source.txt')
        self.commit('second')
        self.head = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.config = config_at(self.area)
        task = self.config['tasks']['qa-execution']
        task.update(effects='owner-reconcile', require_package_scope=True,
                    scope_roots=[str(self.area)])
        task['effect_authority']['operations'] = ['execute-admitted-qa']
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.store.db.execute("UPDATE enrollments SET legacy_hold='old global UNKNOWN' WHERE role='QA'")
        self.genuine = json.loads(Path(__file__).with_name('test_qa_operation616_statement.json').read_text())
        self.statement = copy.deepcopy(self.genuine)
        self.statement['custodian'] = 'Existing QA' + self.config['roles']['QA']['owner']
        self.procedure = self.area / 'procedure.md'
        self.procedure.write_text('Fictional bounded ordinary procedure, never executed.\n')
        self.selected = self.area / 'selected'
        self.selected.mkdir()
        self.files = {}
        for filename in ['qa_selected_tests.py','qa_resource_readback.py','TEST-SELECTION.json']:
            path = self.selected / filename
            path.write_text('{}\n' if filename.endswith('.json') else 'raise SystemExit(0)\n')
            self.files[filename] = sha(path)
        self.output = self.area / 'output'
        self.output.mkdir()
        op = self.statement['final_operations_as_reported']
        op['fixed_source'].update(repository=str(self.repo), common_Git_READONLY=str(self.repo / '.git'),
                                  source_ref='refs/heads/source', commit=self.head, tree=self.tree, parent=parent)
        op['prepared_operands'].update(selected_root=str(self.selected), procedure=str(self.procedure),
                                       procedure_Work_reported_SHA256=sha(self.procedure))
        self.scope = dict(cwd=str(self.repo), read_roots=[str(self.repo), str(self.procedure),
                          *[str(self.selected / f) for f in self.files]],
                          write_roots=[str(self.output)], network=False, procedure=str(self.procedure),
                          resource_evidence='Fictional independently admitted finite scope')
        op['qa_execution_four_field_scope_projection'].update({k:self.scope[k] for k in ('cwd','read_roots','write_roots','procedure')})
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
                                 stdout='FIXTURE COMPLETE\n' if label == 'readback' else None)
        self.scope['ordinary_effects'] = self.p
        self.admit()
        admission = self.store.one('SELECT * FROM admissions WHERE package=?', ('fictional-package',))
        self.record = dict(original_hold='old global UNKNOWN', roots=[], unbounded=True,
                           evidence='Positive operation-relative set empty; global original custody UNKNOWN',
                           qa_operation=dict(statement=self.statement, binding=dict(task='qa-execution',
                               package='fictional-package', admission_sha256=digest(admission))))
        self.selection = dict(basis=dict(configuration=digest(self.config), implementation=processing.implementation(),
                              roles={r:dict(original=dict(events=[]), future_after=0) for r in self.config['roles']}),
                              retained_events=[], recover_controls={}, future_intake=True,
                              tasks=list(self.config['tasks']), service=dict(max_inflight=2,reviews={},legacy_resources={'QA':self.record}))
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,1000,NULL,0)',
                              ('fixture-cap', encode(self.selection), self.config['roles']['Work']['owner']))
        boards = {r:SimpleNamespace(verify_authority=lambda store:None) for r in self.config['roles']}
        self.store.processing = processing.Access(self.store, 'fixture-cap', boards)
        self.epoch = prospective.select(self.store, self.config['roles']['Work']['owner'], dict(
            configuration=digest(self.config), authority='Fictional explicit bounded Work decision', expires=1100.,
            processing_capability='fixture-cap', grants={'QA':self.store.enrollment('QA')['grant_id']},
            tasks={'qa-execution':dict(task_hash=digest(task), software_handoffs={}, ordinary_effects='admitted-v1')}))
        self.pending = dict(role='QA', phase='execution', task='qa-execution', package='fictional-package')
        for name,value in [('FINAL590_QA_OBSERVATION',digest(self.statement)), ('FINAL590_FILES',self.files),
                           ('FINAL590_STDOUT',hashlib.sha256(b'FIXTURE COMPLETE\n').hexdigest())]:
            patcher = patch.object(resources, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

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
                              (encode(self.selection),'fixture-cap'))

    def blocked(self):
        return resources.blocked(self.store,self.pending)

    def test_public_api_matching_operation_is_read_only_and_preserves_global_unknown(self):
        resources.validate(self.store, {'QA':self.record})
        before = '\n'.join(self.store.db.iterdump())
        self.assertFalse(self.blocked())
        self.assertEqual(before,'\n'.join(self.store.db.iterdump()))
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'old global UNKNOWN')
        self.assertTrue(self.record['unbounded'])
        self.assertEqual(self.record['roots'],[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'),[])

    def test_genuine_statement_unpatched_pin_and_forgery(self):
        # Logical fictional enrollment uses the attributed UUID solely for this
        # pure evidence-recognition test; no actual owner operation follows.
        self.store.db.execute("UPDATE enrollments SET owner=? WHERE role='QA'",(self.genuine['custodian'][11:],))
        actual = copy.deepcopy(self.record)
        actual['qa_operation']['statement'] = self.genuine
        with patch.object(resources,'FINAL590_QA_OBSERVATION','3c9f85e9f9ddfef96ee8010d41dcb3b307d4d2bdab0505576817701f446023ef'):
            self.assertEqual(resources.qa_observation(self.store,'QA',actual),self.genuine)
            actual['qa_operation']['statement']['lead_disposition']['additional_positively_bound_relevant_retained_roots'] = ['/invented']
            with self.assertRaises(Refusal):resources.qa_observation(self.store,'QA',actual)

    def test_changed_malformed_forged_evidence_and_global_clearance_refuse(self):
        original = copy.deepcopy(self.record)
        for change in [lambda r:r['qa_operation'].update(statement={}),
                       lambda r:r['qa_operation']['statement'].update(custodian='forged'),
                       lambda r:r['qa_operation']['statement'].update(kind='forged'),
                       lambda r:r.update(unbounded=False),
                       lambda r:r['qa_operation']['binding'].update(admission_sha256='0'*64),
                       lambda r:r['qa_operation'].update(extra=True)]:
            with self.subTest(change=change):
                self.record.clear(); self.record.update(copy.deepcopy(original));change(self.record);self.save()
                self.assertTrue(self.blocked())

    def test_other_role_phase_package_and_cleanup_have_no_borrowed_authority(self):
        for key,value in [('role','Branch'),('phase','cleanup'),('task','qa-cleanup'),('package','other')]:
            row={**self.pending,key:value}
            if key == 'role':
                self.store.db.execute("UPDATE enrollments SET legacy_hold='own Branch debt' WHERE role='Branch'")
            self.assertTrue(resources.blocked(self.store,row))
        with self.assertRaises(Refusal):resources.qa_observation(self.store,'Branch',self.record)

    def test_changed_admission_command_output_network_source_or_binding_refuses(self):
        original = copy.deepcopy(self.scope)
        changes=[lambda s:s['ordinary_effects'].update(source_ref='refs/heads/other'),
                 lambda s:s['ordinary_effects'].update(source_head='0'*40),
                 lambda s:s['ordinary_effects']['command']['argv'].append('extra'),
                 lambda s:s['ordinary_effects']['readback'].update(stdout='forged'),
                 lambda s:s['ordinary_effects'].update(procedure_sha256='0'*64),
                 lambda s:s.update(write_roots=[str(self.area)]), lambda s:s.update(network=True),
                 lambda s:s.update(procedure=str(self.area/'other'))]
        for change in changes:
            with self.subTest(change=change):
                self.scope=copy.deepcopy(original);change(self.scope)
                # Simulate a tampered row, then even rebind its digest. The
                # observation ceiling and fixed pins independently refuse.
                self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',
                                      (encode(dict(task_scopes={'qa-execution':self.scope})),'fictional-package'))
                self.record['qa_operation']['binding']['admission_sha256']=digest(self.store.one('SELECT * FROM admissions'))
                self.save();self.assertTrue(self.blocked())

    def test_current_source_drift_refuses_without_metadata_oracle_substitution(self):
        self.assertFalse(self.blocked())
        self.git('update-ref','refs/heads/source',self.statement['final_operations_as_reported']['fixed_source']['parent'],self.head)
        self.assertTrue(self.blocked())

    def test_expiry_revocation_grant_and_missing_admission_refuse(self):
        self.assertFalse(self.blocked())
        self.now=1100.;self.assertTrue(self.blocked());self.now=1000.
        self.store.db.execute('UPDATE prospective_authorities SET revoked=1001')
        self.assertTrue(self.blocked())
        self.store.db.execute('UPDATE prospective_authorities SET revoked=NULL')
        self.store.db.execute("UPDATE enrollments SET grant_id='different' WHERE role='QA'")
        self.assertTrue(self.blocked())
        self.store.db.execute('DELETE FROM admissions');self.assertTrue(self.blocked())

    def test_excluded_paths_refuse_before_any_metadata(self):
        self.config['artifact_exclusions']=[str(self.repo)]
        # Refresh only the fictional config pin; no production guard is stubbed.
        self.selection['basis']['configuration']=digest(self.config);self.save()
        with patch.object(Path,'is_symlink',side_effect=AssertionError('metadata must not run')):
            self.assertTrue(self.blocked())

    def test_procedure_script_symlink_and_nonregular_inputs_refuse(self):
        self.assertFalse(self.blocked())
        self.procedure.write_text('changed')
        self.assertTrue(self.blocked())
        self.procedure.write_text('Fictional bounded ordinary procedure, never executed.\n')
        script=self.selected/'qa_selected_tests.py'
        original=script.read_bytes();script.unlink();script.symlink_to(self.procedure)
        self.assertTrue(self.blocked())
        script.unlink();script.mkdir()
        self.assertTrue(self.blocked())
        script.rmdir();script.write_bytes(original)
        self.assertFalse(self.blocked())

    def test_unmapped_or_conflicting_current_lease_refuses_and_owner_is_retained(self):
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped','foreign-original')")
        self.assertTrue(self.blocked())
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[dict(resource='unmapped',attempt='foreign-original')])

    def test_real_reservation_uses_observation_without_clearing_flag_or_starting_worker(self):
        source=dict(id='fixture-source',role='QA',recipient=self.config['roles']['QA']['owner'],
                    kind='board',post=1,body='Fictional final operation',allowed_tasks=['qa-execution'],
                    package='fictional-package')
        self.store.ingest(source)
        # Collected classifier result is an explicit fixture seam; no model.
        self.store.db.execute("UPDATE events SET state='queued',ack='done' WHERE id='fixture-source'")
        self.store.db.execute("INSERT INTO queue VALUES('fixture-queue','fixture-source','QA','execution','qa-execution','fictional-package','queued',NULL)")
        observation=self.record.pop('qa_operation');self.save()
        self.assertIsNone(self.store.reserve())
        self.record['qa_operation']=observation;self.save()
        self.assertFalse(self.blocked())
        queued=self.store.one('SELECT * FROM queue')
        self.assertFalse(resources.blocked(self.store,queued))
        self.assertTrue(self.store.processing.task(queued))
        self.assertIsNone(self.store.one('SELECT hold FROM events')['hold'])
        job=self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['package'],'fictional-package')
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'old global UNKNOWN')
        self.assertIsNone(job['active_attempt'])
        self.assertEqual(self.store.rows('SELECT * FROM attempts'),[])

    def test_mapped_conflicting_original_lease_and_frozen_scope_refuse(self):
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('old','QA','execution','qa-execution','old-package','[]','old-collector','old-token',900,'unknown')")
        old_admission=dict(package='old-package',owner=self.config['roles']['Branch']['owner'],
                           receipt=encode(dict(task_scopes={'qa-execution':self.scope})),accepted=None)
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',
                              ('old',encode(self.config['tasks']['qa-execution']),encode(old_admission)))
        self.store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',
                              ('old-attempt','old','old-epoch','old-admission',encode(self.p),'intent',None))
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('fixture-output','old-attempt')")
        before='\n'.join(self.store.db.iterdump())
        self.assertTrue(self.blocked())
        self.assertEqual(before,'\n'.join(self.store.db.iterdump()))

    def test_disjoint_original_local_scope_does_not_invent_global_empty(self):
        other=self.area/'other';other.mkdir()
        prior=copy.deepcopy(self.config['tasks']['qa-cleanup'])
        prior.update(require_package_scope=True,scope_roots=[str(self.area)])
        scope=dict(cwd=str(other),read_roots=[str(other)],write_roots=[],network=False,
                   procedure=str(other/'procedure.md'),resource_evidence='Fictional original bounded report scope')
        old_admission=dict(package='old-package',owner=self.config['roles']['Branch']['owner'],
                           receipt=encode(dict(task_scopes={'qa-cleanup':scope})),accepted=None)
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('old','QA','cleanup','qa-cleanup','old-package','[]','old-collector','old-token',900,'unknown')")
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',('old',encode(prior),encode(old_admission)))
        self.assertFalse(self.blocked())
        self.assertEqual(self.store.job('old')['effects'],'unknown')
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'old global UNKNOWN')

    def test_unresolved_local_owner_without_original_scope_refuses(self):
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('old','QA','execution','qa-execution','old-package','[]','old-collector','old-token',900,'unknown')")
        self.assertTrue(self.blocked())
        self.assertEqual(self.store.job('old')['controller'],'old-collector')
        self.assertEqual(self.store.job('old')['effects'],'unknown')

    def test_original_global_four_field_unknown_account_still_blocks(self):
        del self.record['qa_operation'];self.save()
        resources.validate(self.store,{'QA':self.record})
        self.assertTrue(self.blocked())
        self.record['unbounded']=False
        with self.assertRaises(Refusal):resources.validate(self.store,{'QA':self.record})
