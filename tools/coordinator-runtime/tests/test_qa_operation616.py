"""Migrated616 API controls for Work-selected generic operation policy.

The obsolete two-key wrapper and FINAL590 constants confer no authority.
Attribution is inert evidence; current Work selects a separate exact policy.
All original adverse gates remain exercised against that policy.
"""
import copy
from pathlib import Path
from unittest.mock import patch

from coordinator_runtime import resource_scopes as resources
from coordinator_runtime.contracts import Refusal, digest, encode
from test_qa_operation620 import OperationFixture620


class Operation616(OperationFixture620):
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
        actual = copy.deepcopy(self.record)
        actual['qa_operation']['statement'] = copy.deepcopy(self.genuine)
        actual['qa_operation']['policy']['statement_sha256'] = digest(self.genuine)
        # Body locators are inert; attribution is selected by Work, not a
        # magic trusted-body checksum or a claim of native authorship.
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('inert evidence')):
            self.assertEqual(resources.qa_observation(self.store, 'QA', actual), self.genuine)
        actual['qa_operation']['statement']['custodian'] = 'forged'
        with self.assertRaises(Refusal):
            resources.qa_observation(self.store, 'QA', actual)
        obsolete = copy.deepcopy(actual)
        del obsolete['qa_operation']['policy']
        with self.assertRaises(Refusal):
            resources.qa_observation(self.store, 'QA', obsolete)

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
        self.git('update-ref','refs/heads/source',self.parents[0],self.head)
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
