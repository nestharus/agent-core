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


class OperationFixture620(unittest.TestCase):
    variant = 'alpha'

    def setUp(self):
        self.area = Path('/fixtures') / ident()
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
        self.genuine = json.loads(Path(__file__).with_name('test_qa_operation616_statement.json').read_text())
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



class Operation620(OperationFixture620):
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
                # whole selected scope independently refuses.
                self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',
                                      (encode(dict(task_scopes={'qa-execution':self.scope})),'fictional-package'))
                self.record['qa_operation']['binding']['admission_sha256']=digest(self.store.one('SELECT * FROM admissions'))
                self.save();self.assertTrue(self.blocked())

    def test_current_source_drift_refuses_without_metadata_oracle_substitution(self):
        self.assertFalse(self.blocked())
        self.git('update-ref','refs/heads/source',self.record['qa_operation']['policy']['source']['parents'][0],self.head)
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
        # A changed link identity is rejected by the real single-link reader.
        alias=self.area/'hardlink';os.link(script,alias)
        self.assertTrue(self.blocked())
        alias.unlink();self.assertFalse(self.blocked())

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
        (self.area/'positive.json').write_text(encode(dict(
            fixture_only=True,variant=self.variant,capability=self.cap,
            observation=digest(self.statement),scope=digest(self.scope),source=self.head,
            tree=self.tree,parents=self.parents,reserved=job['id'],
            ordinary_runs=self.store.rows('SELECT * FROM ordinary_runs'),
            global_hold=self.store.enrollment('QA')['legacy_hold'])))

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

    def test_unselected_forged_issuer_and_missing_Work_or_QA_grant_refuse(self):
        # A passed checksum and actor string do not select a policy.
        unselected = copy.deepcopy(self.record)
        unselected['qa_operation']['statement']['extra'] = 'caller assertion'
        unselected['qa_operation']['policy']['statement_sha256'] = digest(unselected['qa_operation']['statement'])
        with patch.object(Path,'is_symlink',side_effect=AssertionError('unselected path metadata')):
            with self.assertRaises(Refusal):
                resources.qa_operation(self.store,self.pending,unselected)
        for role in ('Work','QA'):
            self.denied.add(role)
            self.assertTrue(self.blocked())
            self.denied.clear()
        self.store.db.execute('UPDATE processing_capabilities SET issuer=? WHERE id=?',
                              (self.config['roles']['QA']['owner'],self.cap))
        self.assertTrue(self.blocked())
        self.store.db.execute('UPDATE processing_capabilities SET issuer=? WHERE id=?',(self.actor,self.cap))
        self.assertFalse(self.blocked())
        # Re-issuance traverses real processing.select and the fictional SDK.
        self.actor = self.config['roles']['QA']['owner']
        with self.assertRaises(Refusal):processing.select(self.store,self.boards,self.selection)

    def test_tampered_observation_and_selected_policy_expiry_refuse(self):
        original = copy.deepcopy(self.record)
        for change in [lambda r:r['qa_operation'].update(statement={}),
                       lambda r:r['qa_operation']['statement'].update(fact='forged'),
                       lambda r:r['qa_operation']['policy'].update(custodian=self.actor),
                       lambda r:r['qa_operation']['policy'].update(expires=1000.),
                       lambda r:r['qa_operation']['policy'].update(expires=float('inf')),
                       lambda r:r.update(unbounded=False),
                       lambda r:r['qa_operation']['binding'].update(admission_sha256='0'*64)]:
            self.record.clear();self.record.update(copy.deepcopy(original));change(self.record)
            if self.record['qa_operation']['policy']['expires'] == float('inf'):
                with self.assertRaises(Refusal):resources.qa_observation(self.store,'QA',self.record)
            else:
                self.save();self.assertTrue(self.blocked())
        self.record.clear();self.record.update(original);self.save()
        self.now=1090.;self.assertTrue(self.blocked())

    def test_scope_copy_changed_repository_cwd_reads_manifest_and_command_refuse(self):
        original=copy.deepcopy(self.scope)
        changes=[lambda s:s.update(cwd=str(self.area)),
                 lambda s:s.update(read_roots=s['read_roots']+[str(self.area)]),
                 lambda s:s['ordinary_effects'].update(repository=str(self.area)),
                 lambda s:s['ordinary_effects']['resources'][0].update(owner=self.actor),
                 lambda s:s['ordinary_effects'].update(kind='local-ref'),
                 lambda s:s['ordinary_effects']['source_capture'].update(max_files=11)]
        for change in changes:
            self.scope=copy.deepcopy(original);change(self.scope)
            self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',
                (encode(dict(task_scopes={'qa-execution':self.scope})),'fictional-package'))
            self.record['qa_operation']['binding']['admission_sha256']=digest(self.store.one('SELECT * FROM admissions'))
            self.save();self.assertTrue(self.blocked())
        self.scope=original
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',
            (encode(dict(task_scopes={'qa-execution':self.scope})),'fictional-package'))
        self.record['qa_operation']['binding']['admission_sha256']=digest(self.store.one('SELECT * FROM admissions'))
        self.save();self.assertFalse(self.blocked())
        (self.selected/'TEST-SELECTION.json').write_text('changed manifest')
        self.assertTrue(self.blocked())

    def test_tree_parents_common_topology_and_current_operating_HEAD_are_separate(self):
        policy=self.record['qa_operation']['policy'];source=copy.deepcopy(policy['source'])
        for key,value in [('tree','0'*40),('parents',[]),('parents',list(reversed(source['parents']))+source['parents']),
                          ('common_git',str(self.repo))]:
            policy['source']={**source,key:value};self.save();self.assertTrue(self.blocked())
        policy['source']=source;self.save();self.assertFalse(self.blocked())
        # A new operating HEAD is legitimate while the fixed source ref remains.
        self.git('checkout','-b','operating')
        (self.repo/'source.txt').write_text('operating checkout differs\n')
        self.git('add','source.txt');self.commit('operating')
        self.assertNotEqual(self.git('rev-parse','HEAD'),self.head)
        self.assertFalse(self.blocked())

    def test_relevant_positive_root_and_foreign_task_source_capability_refuse(self):
        self.record['qa_operation']['policy']['relevant_roots']=[str(self.output)]
        self.save();self.assertTrue(self.blocked())
        self.record['qa_operation']['policy']['relevant_roots']=[];self.save()
        self.assertFalse(self.blocked())
        self.selection['tasks'].remove('qa-execution');self.save();self.assertTrue(self.blocked())
        self.selection['tasks'].append('qa-execution');self.save()
        self.store.processing=processing.Access(self.store,'not-issued',self.boards)
        with self.assertRaises(Refusal):self.blocked()
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        self.selection['basis']['implementation']['resource_scopes.py']='0'*64;self.save()
        with self.assertRaises(Refusal):self.blocked()

    def test_real50057_whole_statement_uses_general_attribution_without_path_dereference(self):
        # Observation body remains inert. The policy names the logical fictional
        # enrolled custodian, explicitly accounting for the supplied attribution.
        record=copy.deepcopy(self.record)
        record['qa_operation']['statement']=self.genuine
        record['qa_operation']['policy']['statement_sha256']=digest(self.genuine)
        record['qa_operation']['policy']['reference']='Supplied genuine QA50057; compatibility schema only'
        with patch.object(Path,'read_bytes',side_effect=AssertionError('body locators must remain inert')):
            self.assertEqual(resources.qa_observation(self.store,'QA',record),self.genuine)
        record['qa_operation']['statement']=copy.deepcopy(self.genuine)
        record['qa_operation']['statement']['custodian']='forged'
        with self.assertRaises(Refusal):resources.qa_observation(self.store,'QA',record)

    def test_message_text_and_unselected_source_cannot_issue_operation_policy(self):
        source=dict(id='foreign-source',role='QA',recipient=self.config['roles']['QA']['owner'],
            kind='board',post=0,body={'qa_operation':self.record['qa_operation'],'actor':'Work'},
            allowed_tasks=['qa-execution'],package='fictional-package')
        with self.assertRaisesRegex(Refusal,'input outside explicit processing selection'):
            self.store.ingest(source)
        self.assertIsNone(self.store.one("SELECT id FROM events WHERE id='foreign-source'"))
        self.assertEqual(self.store.rows('SELECT * FROM queue'),[])
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])

    def test_generic_policy_preserves_installed_tools_even_after_explicit_selection(self):
        with self.assertRaises(Refusal):
            self.store.admit('forged-package',self.actor,{'task_scopes':{'qa-execution':self.scope}})
        self.assertIsNone(self.store.one("SELECT * FROM admissions WHERE package='forged-package'"))
        original=copy.deepcopy(self.p)
        for change in [lambda p:p.update(git=str(self.selected/'qa_selected_tests.py')),
                       lambda p:p.pop('public_executables'),
                       lambda p:p['public_executables'].pop('readback'),
                       lambda p:p['resources'][0].update(owner=self.actor)]:
            p=copy.deepcopy(original);change(p)
            self.scope['ordinary_effects']=p
            self.record['qa_operation']['policy']['scope']=copy.deepcopy(self.scope)
            self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',
                (encode(dict(task_scopes={'qa-execution':self.scope})),'fictional-package'))
            self.record['qa_operation']['binding']['admission_sha256']=digest(self.store.one('SELECT * FROM admissions'))
            self.save();self.assertTrue(self.blocked())



class SecondOperation620(OperationFixture620):
    variant='beta'

    def test_distinct_beta_operation_reaches_real_selection_validation_and_reservation(self):
        Operation620.test_public_api_matching_operation_is_read_only_and_preserves_global_unknown(self)
        Operation620.test_real_reservation_uses_observation_without_clearing_flag_or_starting_worker(self)
        source=self.record['qa_operation']['policy']['source']
        source['parents']=list(reversed(source['parents']));self.save()
        self.assertTrue(self.blocked())
