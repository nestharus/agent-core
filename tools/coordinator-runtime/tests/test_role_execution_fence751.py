"""Exact stopped software-grant management on newly owned SQLite/Board fixtures.

No provider/account/runtime acquisition. Reservation tests explicitly supply an
intake-enable seam; this fence does not itself restart stopped software grants.
"""
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, event, result
import test_management406 as existing
from coordinator_runtime import cli, integration_management as management, local_integration as local
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.integration import ROLE_EXECUTION_CLOSURE
from coordinator_runtime.store import Store


class RoleFence751(unittest.TestCase):
    insert = existing.Management.insert
    call = existing.Management.call
    conserved = existing.Management.conserved

    def setUp(self):
        # Retain owned fixtures with their qualification attempt, including failures.
        self.home = Path(tempfile.mkdtemp(prefix='role-fence751-'))
        self.config = config_at(self.home)
        self.owner = self.config['roles']['Work']['owner']
        self.config['software_delegation'] = {'grantor':self.owner, 'authority':'Synthetic original Work software delegation', 'boundary':'new-journal-only'}
        self.config['delivery'] = {'recipients':{r:dict(session=s['owner'],profile=s['profile'],board_role=s['board_role']) for r,s in self.config['roles'].items()}}
        self.config_path = self.home/'config.json'; self.config_path.write_text(encode(self.config))
        self.store = Store(self.config, clock=lambda:1000.)
        self.addCleanup(self.store.close)
        self.boards = {}
        catalog = module_at(self.config['board_library'], 'catalog')
        substrate = module_at(self.config['board_library'], 'board_store')
        for role, selected in self.config['roles'].items():
            with catalog.catalog(Path(self.config['board_home'])) as conn:
                entry = catalog.create(conn, Path(self.config['board_home']), 'synthetic-'+role.lower(), 'Synthetic fence751', board_id=selected['board_id'], temporary_test=True)
            with substrate.database(entry['db_path']) as conn:
                substrate.bind_board(conn, selected['board_id'], initialize=True)
                args = substrate.parser().parse_args(['register','--session',selected['owner'],'--role',selected['board_role'],'--profile',selected['profile'],'--route','managed'])
                with patch.dict(os.environ, {'CODEX_SESSION_ID':selected['owner']}): substrate.register(conn,args)
            board = Board(self.config,role)
            with patch.dict(os.environ, {'CODEX_SESSION_ID':self.owner}):
                grant = board.grant_software(self.store,self.config['software_delegation']['authority'])
            self.store.enroll(role,grant); self.boards[role] = board
            self.store.reconcile_legacy(role, selected['owner'], {'collector':'fictional prior collector','evidence':['fictional closed'],'remaining_holds':[]})
        for role,board in self.boards.items():
            with patch.dict(os.environ, {'CODEX_SESSION_ID':self.owner}):
                board.revoke_software(self.store,self.store.enrollment(role)['grant_id'])
        self.store.db.execute('UPDATE enrollments SET intake=0')
        self.role, self.phase = ('QA','execution') if 'QA_same_package' in self._testMethodName else ('Branch','proposer') if 'Branch_proposer' in self._testMethodName else ('Reviews','integrator')
        self.make_job()

    def make_job(self):
        role,phase = self.role,self.phase
        self.task = role.lower()+'-'+phase
        self.source = event(self.config,'old751',role=role,task=self.task)
        self.next = event(self.config,'new751',role=role,task=self.task)
        for e in (self.source,self.next):
            self.insert('events',dict(id=e['id'],role=role,payload=encode(e),hash=digest(e),received=1 if e==self.source else 10,state='queued',ack='done'))
        self.insert('queue',dict(id='old-queue751',event=self.source['id'],role=role,phase=phase,task=self.task,state='reserved',job='old-job751'))
        self.insert('queue',dict(id='new-queue751',event=self.next['id'],role=role,phase=phase,task=self.task))
        self.insert('jobs',dict(id='old-job751',role=role,phase=phase,task=self.task,members=encode([dict(queue='old-queue751',event=self.source['id'],hash=digest(self.source),package=None)]),controller='original-controller751',token='old-token751',created=2,state='held',active_attempt='old-attempt751',hold_reason='UNKNOWN remains owned'))
        self.insert('attempts',dict(id='old-attempt751',kind='task',job='old-job751',controller='original-controller751',profile='fiction',binding='{}',state='collected',created=2,begin=3,ended=4,collected=5,exit=0,semantic='UNKNOWN',capture='complete',result=encode(result('UNKNOWN')),detail='{"opaque":"unacquired"}'))
        self.insert('outboxes',dict(id='old-outbox751',role=role,job='old-job751',producer='original-controller751',recipient='Work',kind='question',required='settled',payload='{"unknown":true}',state='sent',created=6))
        self.authority = management.basis(self.store,sorted({'Work',role}),self.owner,'Synthetic current rollout management','Permanent exact execution fence only',metadata_only=True)

    def selection(self, command):
        return dict(basis=self.authority, expires=1100.,operation=command,target=dict(job='old-job751',token='old-token751',role=self.role,phase=self.phase),records=dict(jobs=['old-job751'],events=[self.source['id']]))

    def managed(self, command, receipt=None, selection=None, actor=None, expected=0):
        path=self.home/'choice751.json';path.write_text(encode(selection or self.selection(command)))
        argv=[command,'old-job751','--token','old-token751','--role',self.role,'--phase',self.phase,'--management',str(path)]
        if receipt is not None:
            p=self.home/'receipt751.json';p.write_text(encode(receipt));argv+=['--receipt',str(p)]
        return self.call(*argv,actor=actor,expected=expected)

    def receipt(self):
        basis=self.managed('role-execution-closure-basis')
        return dict(basis=basis,reason='Actual synthetic original collection and writer closure; all duties retained',controllers=[dict(controller=c,collector='synthetic-actual-original-collector',end=0,collected=True,writers_closed=True,evidence=['Synthetic actual controller and descendants END; launch-capable writers closed']) for c in basis['controllers']])

    def fence(self):
        return self.managed('fence-role-execution',self.receipt())

    @contextmanager
    def metadata_only(self):
        # Main opens the same real DB with this authorizer. Capture equality is
        # the only permitted capture access; its raw enum is never returned.
        original=existing.Store
        denied=[]
        forbidden={'results':None,'outboxes':None,'file_publications':None,'artifact_custody':None,'artifact_blobs':None,
                   'jobs':{'response','effect_receipt','hold_reason','collection_handoff'},
                   'attempts':{'result','detail','error','semantic','cleanup','binding','profile','session','turn'},
                   'events':{'payload','hash','classification','classifier','error','hold','ack_receipt'},
                   'enrollments':{'legacy_hold','reconciliation'},'recovery_requests':{'receipt','result'}}
        def authorize(action,table,column,db,caller):
            if action==sqlite3.SQLITE_READ and table in forbidden and (forbidden[table] is None or column in forbidden[table]):
                denied.append((table,column));return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        def store(*a,**kw):
            value=original(*a,**kw);value.db.set_authorizer(authorize);return value
        with patch.object(existing,'Store',side_effect=store): yield
        self.assertEqual(denied,[])

    def duties(self):
        data = {k:v for k,v in self.conserved().items() if k not in {'integration_retirements','integration_management_operations'}}
        for table in ('ordinary_resources','review_contexts','review_calls','branch_turns','branch_contexts','service_windows','service_window_allocations','qa_package_owners','admissions'):
            data[table] = self.store.rows('SELECT * FROM '+table+' ORDER BY rowid')
        return data

    def test_production_cli_metadata_conservation_capacity_and_permanent_callbacks(self):
        with patch.object(self.store,'role_enabled',return_value=True):
            self.assertIsNone(self.store.reserve())
        self.insert('review_contexts',dict(component='context751',capability='fiction',profile='fiction',route='fiction',handle='native751',collector='original-controller751',state='closed',history_hash='opaque-history',created=1))
        self.insert('review_calls',dict(attempt='old-attempt751',component='context751',collector='original-controller751',packet='opaque-original-packet',state='collected'))
        before=self.duties()
        with self.metadata_only():
            receipt=self.receipt(); self.assertEqual(receipt['basis']['schema'],ROLE_EXECUTION_CLOSURE)
            self.managed('fence-role-execution',receipt)
        self.assertEqual(before,self.duties())
        # Other-role bodies never enter Work's legacy integration debt acquisition.
        with patch.object(self.store,'job',side_effect=AssertionError('foreign-role body acquisition')):
            self.assertEqual(self.store.integration_debt(),[])
        from coordinator_runtime import service_recovery
        disposition=dict(basis='unacquired',activity='inactive',evidence='fiction',custodian='original',remaining_holds=['all original duties'],history_hash='opaque-history')
        with self.assertRaisesRegex(Refusal,'execution retired'):
            service_recovery.recover_review(self.store,self.owner,'context751',disposition)
        old=self.store.job('old-job751');self.assertEqual((old['state'],old['effects']),('held','unknown'))
        self.assertEqual(self.store.attempt('old-attempt751')['semantic'],'UNKNOWN')
        self.assertTrue(self.store.execution_complete(old))
        self.assertEqual(self.store.one('SELECT state,job FROM queue WHERE id=?',('old-queue751',)),dict(state='reserved',job='old-job751'))
        for method,args in [(self.store.start_job,('old-job751','old-token751')),(self.store.begin,('old-attempt751',{})),(self.store.session,('old-attempt751','late')),(self.store.collect,('old-attempt751',{})),(self.store.request_recovery,('old-job751','old-token751','old-attempt751',self.owner,{}))]:
            with self.subTest(method=method.__name__),self.assertRaisesRegex(Refusal,'execution retired'): method(*args)
        with patch.object(self.store,'role_enabled',return_value=True):
            fresh=self.store.reserve()
        self.assertIsNotNone(fresh);self.assertNotEqual(fresh['id'],old['id'])
        self.assertEqual(json.loads(fresh['members'])[0]['event'],self.next['id'])
        self.assertEqual(self.store.job('old-job751'),old)

    def test_live_unknown_capture_end_and_pending_recovery_refuse(self):
        mutations=[('attempts','begin',None),('attempts','ended',None),('attempts','collected',None),('attempts','exit',None),('attempts','exit','UNKNOWN'),('attempts','capture','incomplete'),('attempts','capture','artifact-inventory-incomplete'),('attempts','state','running'),('attempts','controller','foreign'),('attempts','ended',2),('jobs','recovery_state','diagnosing')]
        for table,field,value in mutations:
            old=self.store.one('SELECT '+field+' FROM '+table)[field]
            self.store.db.execute('UPDATE '+table+' SET '+field+'=?',(value,))
            with self.subTest(table=table,field=field,value=value): self.managed('role-execution-closure-basis',expected=2)
            self.store.db.execute('UPDATE '+table+' SET '+field+'=?',(old,))
        self.insert('recovery_requests',dict(id='pending751',job='old-job751',attempt='old-attempt751',actor=self.owner,receipt='{}',state='pending',created=6))
        self.managed('role-execution-closure-basis',expected=2)
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'),[])

    def test_foreign_owner_exact_role_token_source_and_original_grants(self):
        self.managed('role-execution-closure-basis',actor=self.config['roles']['Reviews']['owner'],expected=2)
        for mutate in [lambda s:s['target'].update(role='Branch'),lambda s:s['target'].update(token='wrong'),lambda s:s['basis'].update(configuration='stale'),lambda s:s['records'].update(events=[]),lambda s:s['basis']['roles'].pop('Reviews')]:
            selection=self.selection('role-execution-closure-basis');mutate(selection)
            self.managed('role-execution-closure-basis',selection=selection,expected=2)
        for table,field,expr in [('coordinator_grants_v1','revoked','NULL'),('coordinator_grants_v1','runtime_ino','runtime_ino+1'),('coordinator_software_grants_v1','configuration',"'stale'"),('sessions','status',"'paused'")]:
            with sqlite3.connect(self.boards['Reviews'].path) as conn:
                old=conn.execute('SELECT rowid,'+field+' FROM '+table).fetchall()
                conn.execute('UPDATE '+table+' SET '+field+'='+expr);conn.commit()
                self.managed('role-execution-closure-basis',expected=2)
                conn.executemany('UPDATE '+table+' SET '+field+'=? WHERE rowid=?',[(v,k) for k,v in old]);conn.commit()
        with self.assertRaises(Refusal): self.store.role_execution_closure_basis('old-job751','old-token751',self.owner,self.role,self.phase)

    def test_stale_revision_and_missing_writer_collector_refuse(self):
        receipt=self.receipt()
        for field,value in [('end',None),('writers_closed',False),('collected',False),('collector',''),('evidence',[])]:
            bad=copy.deepcopy(receipt);bad['controllers'][0][field]=value
            self.managed('fence-role-execution',bad,expected=2)
        self.store.db.execute("UPDATE attempts SET detail='{}'")
        self.managed('fence-role-execution',receipt,expected=2)
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'),[])

    def test_all_related_diagnoses_require_capture_end_and_controller_closure(self):
        self.insert('attempts',dict(id='diagnosis751',kind='diagnosis',job='old-job751',controller='diagnosis-controller751',profile='fiction',binding='{}',state='collected',created=5,begin=6,ended=7,collected=8,exit=19,capture='incomplete'))
        self.managed('role-execution-closure-basis',expected=2)
        self.store.db.execute("UPDATE attempts SET capture='complete' WHERE id='diagnosis751'")
        receipt=self.receipt();self.assertEqual(len(receipt['controllers']),2)
        bad=copy.deepcopy(receipt);bad['controllers'].pop()
        self.managed('fence-role-execution',bad,expected=2)
        self.managed('fence-role-execution',receipt)

    def test_local_point_and_ordinary_resource_conflicts_survive_execution_release(self):
        self.fence()
        target=self.home/'material751.json';target.write_text('{"a":0,"b":0}')
        self.store.config['local_integration']=dict(max_inflight=1,tasks={self.task:dict(points=['a','b'])},points={k:dict(bindings=[dict(target=str(target),path=[k])],resources=[]) for k in ['a','b']})
        prior=dict(lane='anchored',reads=['a'],writes=[],sources=[self.source['id']])
        self.store.db.execute('INSERT INTO local_jobs VALUES(?,?,?)',('old-job751','fictional-policy',encode(prior)))
        row=self.store.one('SELECT * FROM queue WHERE id=?',('new-queue751',));member=dict(event=self.next['id'])
        scope=dict(lane='anchored',reads=[],writes=['a'],versions={},sources=[self.next['id']])
        with patch.object(local,'packet',return_value=scope): self.assertFalse(local.available(self.store,row,[member]))
        scope['writes']=['b']
        with patch.object(local,'packet',return_value=scope): self.assertTrue(local.available(self.store,row,[member]))
        self.store.config['local_integration']['points']['b']['resources']=['lease751']
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)',('lease751','old-attempt751'))
        with patch.object(local,'packet',return_value=scope): self.assertFalse(local.available(self.store,row,[member]))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[dict(resource='lease751',attempt='old-attempt751')])

    def test_Branch_proposer_exact_phase_and_unknown_duties(self):
        before=self.duties()
        self.fence()
        self.assertEqual(before,self.duties())
        self.assertTrue(self.store.execution_complete(self.store.job('old-job751')))
        self.assertRaises(Refusal,self.store.start_job,'old-job751','old-token751')

    def test_QA_same_package_stays_fenced_and_distinct_package_can_reserve(self):
        # This test receives its own exact QA fixture from setUp.
        self.store.db.execute("UPDATE jobs SET package='qa751'")
        self.store.db.execute("UPDATE queue SET package='qa751'")
        self.insert('admissions',dict(package='qa751',owner=self.config['roles']['Branch']['owner'],receipt='{}'))
        self.fence()
        with patch.object(self.store,'role_enabled',return_value=True): self.assertIsNone(self.store.reserve())
        self.insert('admissions',dict(package='disjoint751',owner=self.config['roles']['Branch']['owner'],receipt='{}'))
        self.store.db.execute("UPDATE queue SET package='disjoint751' WHERE id='new-queue751'")
        with patch.object(self.store,'role_enabled',return_value=True): fresh=self.store.reserve()
        self.assertIsNotNone(fresh);self.assertEqual(fresh['package'],'disjoint751')


if __name__=='__main__': unittest.main(verbosity=2)
