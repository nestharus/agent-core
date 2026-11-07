"""Owned fictional originals only; closure testimony is never a real census."""
from contextlib import contextmanager, ExitStack
import copy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import support
import test_management406 as fixture
import test_metadata_closure671 as metadata_fixture
from coordinator_runtime import integration_management as management, local_integration as local
from coordinator_runtime import reservation, selected_source
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.integration import METADATA_READ_FENCE


class AnchoredReader691(unittest.TestCase):
    call = metadata_fixture.MetadataClosure671.call
    selection = metadata_fixture.MetadataClosure671.selection
    receipt = metadata_fixture.MetadataClosure671.receipt

    def setUp(self):
        self.f = fixture.Management(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        with patch.object(fixture, 'config_at', side_effect=self.configuration):
            self.f.setUp()
        self.store, self.owner = self.f.store, self.f.owner
        self.job, self.token = 'synthetic-held', 'synthetic-token'
        self.store.db.execute("UPDATE jobs SET phase='proposer',task='work-proposer',effects='none'")
        self.store.db.execute("UPDATE queue SET phase='proposer',task='work-proposer' WHERE job=?", (self.job,))
        self.store.db.execute('DELETE FROM file_publications')
        frozen = {**self.store.config['tasks']['work-proposer'],'unselected':'UNACQUIRED_FROZEN_BODY691'}
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,NULL)', (self.job,encode(frozen)))
        self.prior = {'lane':'anchored','reads':['a'],'writes':[], 'versions':{'a':'UNACQUIRED_VERSION691'},
                      'sources':['UNACQUIRED_SCOPE_SOURCE691']}
        self.store.db.execute('INSERT INTO local_jobs VALUES(?,?,?)', (self.job,'frozen-local-policy691',encode(self.prior)))
        self.authority = management.basis(self.store,['Work'],self.owner,'Synthetic genuine Work',
                                          'Synthetic closed anchored reader only',metadata_only=True)
        self.incoming = self.store.one('SELECT * FROM queue WHERE event=?', (self.f.next['id'],))
        self.scope = {'lane':'anchored','reads':[],'writes':['a'],'versions':{},'sources':[self.f.next['id']]}

    def configuration(self, home):
        config = support.config_at(home)
        self.target = Path(home)/'synthetic-points691.json'
        self.target.write_text('{"item":{"state":"held"}}')
        config['tasks']['work-integrator'].update(sandbox='workspace-write',effects='owner-reconcile',
            routine_completion={'kind':'file-witness','targets':[str(self.target)]})
        config['tasks']['work-integrator']['effect_authority']['write_roots'] = [str(home)]
        config['local_integration'] = {'max_inflight':5,'points':{
            k:{'kind':'item','line':'synthetic691','incarnation':'fictional691',
               'bindings':[{'target':str(self.target),'path':['item']}], 'resources':[],
               'protected':[],'writable':['state']} for k in ('a','alias','b')},
            'tasks':{name:{'capacity':5,'discovery_batch':1,'points':['a','alias','b'],
                          'authority':'Synthetic current Work routine authority',
                          'method':config['tasks'][name]['templates'][0]}
                     for name in ('work-proposer','work-integrator')}}
        return config

    def basis(self):
        return self.call('work-read-metadata-closure-basis')

    def fence(self, receipt=None, **kwargs):
        return self.call('fence-work-proposer-metadata', receipt=receipt if receipt is not None else self.receipt(), **kwargs)

    @contextmanager
    def metadata_only(self):
        # SQLite still evaluates selected JSON paths internally; Python never
        # receives the frozen task/scope/members or unselected retained bodies.
        denied = []
        forbidden = {'results':None,'artifact_custody':None,'artifact_blobs':None,'outboxes':None,
            'attempts':{'result','detail','error','capture','semantic','cleanup','binding','profile','session','turn'},
            'jobs':{'effect_receipt','response','hold_reason','collection_handoff'},
            'events':{'payload','hash','classification','classifier','error','hold','ack_receipt'},
            'enrollments':{'legacy_hold','reconciliation'},'recovery_requests':{'receipt','result'},
            'recovery_dispositions':{'reason'},'file_publications':{'target','state','error','receipt'},
            'local_commits':{'state','receipt'},'local_material_commits':{'footprints'}}
        def authorize(action, table, column, db, caller):
            if action == sqlite3.SQLITE_READ and table in forbidden and (
                    forbidden[table] is None or column in forbidden[table]):
                denied.append((table,column)); return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        originals = self.store.one, self.store.rows
        def projected(method):
            def check(sql, *args):
                if sql.lstrip().upper().startswith('SELECT'):
                    for table in forbidden:
                        self.assertNotIn('SELECT * FROM '+table.upper(), sql.upper())
                    self.assertNotIn('SELECT TASK FROM JOB_RESOURCE_POLICIES', sql.upper())
                    self.assertNotIn('SELECT SCOPE FROM LOCAL_JOBS', sql.upper())
                return method(sql,*args)
            return check
        with ExitStack() as stack:
            for method in ('job','attempt','event','source_roles','integration_debt','usage','budget'):
                stack.enter_context(patch.object(self.store,method,side_effect=AssertionError('old body acquisition: '+method)))
            for name, method in zip(('one','rows'),originals):
                stack.enter_context(patch.object(self.store,name,side_effect=projected(method)))
            self.store.db.set_authorizer(authorize)
            try: yield
            finally: self.store.db.set_authorizer(None)
        self.assertEqual(denied,[])

    @contextmanager
    def mutation(self, sql):
        # Only this newly constructed fictional database; permit real public
        # management transactions without nested test savepoints or FK edits.
        saved = sqlite3.connect(':memory:')
        self.store.db.backup(saved)
        try:
            if sql.startswith('UPDATE job_resource_policies '):
                # Model corrupted/replaced policy bytes only in this owned
                # fiction. Restore the production immutable trigger afterward.
                self.store.db.execute('DROP TRIGGER job_resource_policies_no_update')
            self.store.db.execute(sql)
            yield
        finally:
            saved.backup(self.store.db)
            saved.close()

    def coexists(self):
        return self.store.work_read_coexists(self.incoming,self.scope,{'id':self.job})

    def available(self):
        with patch.object(local,'packet',return_value=self.scope), reservation.Evaluation(self.store,self.incoming) as evaluation:
            result = local.available(self.store,self.incoming,[{'event':self.f.next['id']}],
                                     observe=evaluation.at,conflict_observe=evaluation.conflict)
            if not result: evaluation.finish('false')
        return result

    def test_point_access_changes_only_after_qualified_fence_and_conserves_old_duties(self):
        self.assertFalse(self.available())
        witness = self.store.one('SELECT job,arm FROM reservation_conflicts WHERE event=?', (self.f.next['id'],))
        self.assertEqual(witness,{'job':self.job,'arm':'point-access'})
        before = self.f.conserved()
        with self.metadata_only():
            basis = self.basis()
            self.assertEqual(basis['schema'],METADATA_READ_FENCE)
            self.assertNotIn('UNACQUIRED_',encode(basis))
            self.assertNotIn(digest(self.f.source),encode(basis))
            self.fence(self.receipt(basis))
            self.assertTrue(self.coexists())  # Own append changes the global revision.
        after = self.f.conserved()
        for table in before:
            if table != 'integration_management_operations': self.assertEqual(before[table],after[table],table)
        self.assertTrue(self.available())
        self.assertFalse(self.store.execution_complete(self.store.job(self.job)))
        self.assertEqual(self.store.job(self.job)['effects'],'none')
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'),[])
        self.assertEqual(len(self.store.rows('SELECT job FROM work_read_fences')),1)
        for action,args in [(self.store.require_execution_open,(self.job,)),
                (self.store.start_job,(self.job,self.token)), (self.store.finish_job,(self.job,self.token)),
                (self.store.request_recovery,(self.job,self.token,'synthetic-attempt',self.owner,{}))]:
            with self.assertRaisesRegex(Refusal,'execution retired'): action(*args)

    def test_new_reservation_records_fence_and_current_job_revalidates_without_old_job_body(self):
        self.fence()
        fresh = {'id':'synthetic-future691','role':'Work','task':'work-integrator','phase':'integrator',
                 'members':encode([{'event':self.f.next['id']}])}
        with patch.object(local,'packet',return_value=self.scope): local.record_job(self.store,fresh)
        scope = json.loads(self.store.one('SELECT scope FROM local_jobs WHERE job=?',(fresh['id'],))['scope'])
        self.assertEqual(scope['read_fences'],[self.job])
        # Isolate existing incoming member checks, retaining the real fence check.
        fresh['members'] = '[]'
        with self.metadata_only(): local.current_job(self.store,fresh)
        with self.mutation("UPDATE attempts SET controller='new-controller691'"), self.assertRaisesRegex(Refusal,'read fence'):
            local.current_job(self.store,fresh)

    def test_stable_fence_survives_unrelated_and_omitted_private_changes_without_claiming_integrity(self):
        self.fence()
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable original job resources'):
            self.store.db.execute("UPDATE job_resource_policies SET task='forbidden'")
        for sql in ["UPDATE events SET received=received+1", "UPDATE attempts SET error='UNACQUIRED new defect'",
                    "UPDATE results SET result='UNACQUIRED new return'", "UPDATE jobs SET hold_reason='UNACQUIRED hold'",
                    "UPDATE job_resource_policies SET task=json_set(task,'$.purpose','UNACQUIRED purpose')",
                    "UPDATE local_jobs SET scope=json_set(scope,'$.versions.a','UNACQUIRED version')"]:
            with self.subTest(sql=sql), self.mutation(sql), self.metadata_only(): self.assertTrue(self.coexists())

    def test_new_controller_attempt_recovery_policy_scope_and_write_duties_invalidate_at_use(self):
        self.fence()
        changes = ["UPDATE jobs SET state='running'", "UPDATE jobs SET effects='unknown'",
            "UPDATE jobs SET token='other-token'", "UPDATE jobs SET controller='other-controller'",
            "UPDATE jobs SET active_attempt='missing'", "UPDATE attempts SET ended=ended+1",
            "UPDATE attempts SET state='ended'", "UPDATE jobs SET recovery_owner='other',recovery_state='diagnosing',recovery_count=1",
            "UPDATE job_resource_policies SET task=json_set(task,'$.sandbox','workspace-write')",
            "UPDATE job_resource_policies SET task=json_set(task,'$.effect_authority.write_roots',json('[\"/fiction\"]'))",
            "UPDATE local_jobs SET scope=json_set(scope,'$.writes',json('[\"a\"]'))",
            "UPDATE local_jobs SET scope=json_set(scope,'$.reads',json('[\"b\"]'))",
            "UPDATE local_jobs SET policy='new-policy'", "DELETE FROM local_jobs",
            "UPDATE queue SET phase='integrator' WHERE job='synthetic-held'",
            "INSERT INTO recovery_requests(id,job,attempt,actor,receipt,state,created) VALUES('pending691','synthetic-held','synthetic-attempt','synthetic','UNREAD','pending',1)",
            "INSERT INTO file_publications(attempt,target,state,error) VALUES('synthetic-attempt','UNREAD','intent','UNREAD')",
            "INSERT INTO local_commits VALUES('synthetic-attempt','intent','UNREAD')",
            "INSERT INTO local_point_commits VALUES('a',1,'synthetic-attempt')",
            "INSERT INTO local_material_commits(attempt,footprints) VALUES('synthetic-attempt','UNREAD')",
            "INSERT INTO attempts(id,kind,job,controller,profile,binding,state,created) VALUES('new691','diagnosis','synthetic-held','new-controller','fiction','UNREAD','running',1)"]
        for sql in changes:
            with self.subTest(sql=sql), self.mutation(sql), self.metadata_only(): self.assertFalse(self.coexists())
        with self.mutation("UPDATE jobs SET effects='unknown'"):
            self.assertFalse(self.available())
            self.assertEqual(self.store.one('SELECT arm FROM reservation_conflicts WHERE event=?',(self.f.next['id'],))['arm'],'point-access')

    def test_unqualified_active_writing_unknown_scope_and_publication_refuse_basis(self):
        changes = ["UPDATE jobs SET state='running'", "UPDATE jobs SET effects='unknown'",
            "UPDATE attempts SET begin=NULL", "UPDATE attempts SET ended=NULL", "UPDATE attempts SET collected=NULL",
            "UPDATE attempts SET exit='unknown'", "UPDATE attempts SET exit=0.5", "UPDATE attempts SET kind='diagnosis'",
            "UPDATE attempts SET controller='other'", "UPDATE jobs SET recovery_count=1",
            "UPDATE jobs SET recovery_state='owner-deferred'", "UPDATE jobs SET recovery_state='unknown',recovery_owner='other',recovery_count=1",
            "UPDATE job_resource_policies SET task=json_set(task,'$.network',json('true'))",
            "UPDATE job_resource_policies SET task=json_set(task,'$.execution',json('{}'))",
            "UPDATE job_resource_policies SET task=json_set(task,'$.routine_completion',json('true'))",
            "UPDATE job_resource_policies SET task=json_set(task,'$.role',json('{}'))",
            "UPDATE job_resource_policies SET task=json_set(task,'$.effect_authority.write_roots',json('{}'))",
            "UPDATE local_jobs SET scope=json_set(scope,'$.lane','discovery')", "DELETE FROM local_jobs",
            "UPDATE local_jobs SET scope=json_set(scope,'$.writes',json('[\"a\"]'))",
            "UPDATE local_jobs SET scope=json_set(scope,'$.reads',json('[{}]'))",
            "INSERT INTO local_commits VALUES('synthetic-attempt','intent','UNREAD')",
            "INSERT INTO file_publications(attempt,target,state,error) VALUES('synthetic-attempt','UNREAD','unknown','UNREAD')"]
        for sql in changes:
            with self.subTest(sql=sql), self.mutation(sql), self.metadata_only(), self.assertRaises(Refusal): self.basis()

    def test_all_related_numeric_originals_and_every_controller_writer_attestation(self):
        self.f.insert('attempts',{'id':'diagnosis691','kind':'diagnosis','job':self.job,'controller':'diagnoser691',
            'profile':'fiction','binding':'UNREAD','state':'collected','created':1,'begin':2,'ended':3,'collected':4,'exit':19})
        self.store.db.execute("UPDATE jobs SET recovery_owner='recovery691',recovery_state='owner-deferred',recovery_count=1")
        with self.metadata_only():
            receipt = self.receipt()
            self.assertEqual(len(receipt['basis']['controllers']),3)
            for change in [lambda r:r.update(controllers=[]),lambda r:r['controllers'].pop(),
                    lambda r:r['controllers'][0].update(writers_closed=False),lambda r:r['controllers'][0].update(end=True),
                    lambda r:r['controllers'][0].update(end=None),lambda r:r['controllers'][0].update(collected=False),
                    lambda r:r['controllers'][0].update(collector=''),lambda r:r['controllers'][0].update(evidence=[]),
                    lambda r:r['controllers'][0].update(controller='foreign')]:
                bad = copy.deepcopy(receipt); change(bad)
                with self.assertRaises(Refusal): self.fence(bad)
            self.fence(receipt)

    def test_stale_global_basis_and_same_transaction_mutation_refuse_append(self):
        receipt = self.receipt()
        self.store.db.execute("UPDATE attempts SET error='UNACQUIRED changed' ")
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'basis changed'): self.fence(receipt)
        receipt = self.receipt()
        before = self.f.conserved()
        original = selected_source.custody_budget
        def mutate(runtime,incoming):
            self.assertTrue(runtime.db.in_transaction)
            original(runtime,incoming)
            runtime.db.execute("UPDATE attempts SET error='UNACQUIRED same transaction'")
        with self.metadata_only(), patch.object(selected_source,'custody_budget',side_effect=mutate):
            with self.assertRaisesRegex(Refusal,'revision changed'): self.fence(receipt)
        self.assertEqual(before,self.f.conserved())
        self.assertEqual(self.store.rows('SELECT job FROM work_read_fences'),[])

    def test_exact_authority_token_role_scope_and_version_before_acquisition(self):
        command = 'work-read-metadata-closure-basis'
        for change in [lambda s:s['target'].update(token='wrong'),lambda s:s['records'].update(jobs=[]),
                lambda s:s['records'].update(events=[]),lambda s:s.update(operation='fence-work-proposer-metadata'),
                lambda s:s['basis'].pop('schema'),lambda s:s['basis'].update(configuration='stale'),
                lambda s:s.update(expires=1000.)]:
            choice = self.selection(command); change(choice)
            with self.metadata_only(), self.assertRaises(Refusal): self.call(command,selection=choice)
        with self.metadata_only(), self.assertRaises(Refusal): self.call(command,actor='foreign')
        self.token = 'wrong'
        with self.metadata_only(), patch.object(self.store,'integration_metadata_sources',side_effect=AssertionError('acquired before token')):
            with self.assertRaises(Refusal): self.basis()
        self.token = 'synthetic-token'
        self.store.db.execute("UPDATE events SET role='Branch' WHERE id=?",(self.f.source['id'],))
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'source roles'): self.basis()
        self.authority = management.basis(self.store,['Work','Branch'],self.owner,'Synthetic authority','Exact sources',metadata_only=True)
        with self.metadata_only(): self.fence()

    def test_ordinary_active_grant_and_paused_refusal_processing_and_budget(self):
        with self.metadata_only(), self.assertRaises(Refusal): self.call('work-read-metadata-closure-basis',ordinary=True)
        with patch.object(self.store,'processing',object()), self.assertRaisesRegex(Refusal,'processing'):
            self.store.work_read_metadata_closure_basis(self.job,self.token,self.owner)
        with self.metadata_only(), patch.object(selected_source,'custody_budget',side_effect=Refusal('capacity full')):
            with self.assertRaisesRegex(Refusal,'capacity full'): self.fence()
        for board in self.f.boards.values():
            with sqlite3.connect(board.path) as conn: conn.execute('UPDATE coordinator_grants_v1 SET revoked=NULL')
        self.store.db.execute('UPDATE enrollments SET intake=1')
        with self.metadata_only():
            basis = self.call('work-read-metadata-closure-basis',ordinary=True)
            self.fence(self.receipt(basis),ordinary=True)

    def test_native_and_wrong_incoming_contract_never_coexist(self):
        self.fence()
        point = self.store.config['local_integration']['points']['a']
        with patch.dict(point,bindings=[{'native':{'fiction':'no native acquisition'}}]):
            self.assertFalse(self.coexists())
        # Only the old read is native; the incoming point is still a file.
        self.scope['writes'] = ['b']
        with patch.dict(point,bindings=[{'native':{'fiction':'no native acquisition'}}]), self.metadata_only():
            self.assertFalse(self.coexists())
            with self.assertRaisesRegex(Refusal,'file-only'):
                self.store._work_read_metadata_stable(self.job)
        for change in [dict(role='Branch'),dict(phase='execution'),dict(task='work-proposer')]:
            with patch.dict(self.incoming,change): self.assertFalse(self.coexists())
        self.scope.update(lane='discovery')
        self.assertFalse(self.coexists())

    def test_readonly_incoming_and_legacy_fence_cannot_qualify_known_scope(self):
        with self.metadata_only(), patch.object(local,'point_definitions',side_effect=AssertionError('unqualified helper acquisition')):
            self.assertFalse(self.coexists())
        self.store.db.execute('INSERT INTO work_read_fences VALUES(?,?,?,?,?)',
            (self.job,self.owner,'{}','UNACQUIRED legacy receipt',1000.))
        with self.metadata_only(): self.assertFalse(self.coexists())
        self.store.db.execute('DELETE FROM work_read_fences')
        self.fence()
        self.incoming.update(task='work-proposer',phase='proposer')
        self.scope.update(reads=['a'],writes=[])
        with self.metadata_only(): self.assertTrue(self.coexists())

    def test_legacy_unknown_and_nonlocal_reader_remain_compatible(self):
        self.store.db.execute('DELETE FROM local_jobs')
        # The unmodified legacy contract still admits a genuinely unknown scope.
        authority = management.basis(self.store,['Work'],self.owner,'Synthetic legacy authority','Legacy scope only')
        self.authority = authority
        basis = self.call('work-read-closure-basis')
        self.call('fence-work-proposer',receipt=self.receipt(basis))
        self.assertTrue(self.available())
        self.assertTrue(self.coexists())
        self.assertFalse(self.store.execution_complete(self.store.job(self.job)))


if __name__ == '__main__': unittest.main(verbosity=2)
