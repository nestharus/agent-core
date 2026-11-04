"""Finite source controls, no stock fixtures, providers or pool allocation.

Run with python -B this_file.py --fixtures /absolute/owned/root. Import only
integration/contracts. Compile selected, unchanged production Store/Recovery
methods from AST in memory, avoiding unrelated import-time public pool loading.
Use their actual SQLite schemas/transactions and a fictional allocation adapter.
This is affected-interface evidence, not full Store/CLI/service qualification.
--full-store uses the inspected production import graph and also checks its
constructor in an explicitly owned fictional directory. Pool I/O stays fake.
"""
import argparse
import ast
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.integration import IntegrationJournal, SCHEMA as INTEGRATION_SCHEMA


def tree(name):
    return ast.parse((ROOT/'coordinator_runtime'/name).read_text())


def schema(name):
    return next(ast.literal_eval(n.value) for n in tree(name).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='SCHEMA' for t in n.targets))


def methods(name, original, selected):
    node = next(n for n in tree(name).body if isinstance(n, ast.ClassDef) and n.name==original)
    chosen = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in selected]
    assert {n.name for n in chosen} == set(selected)
    node.bases=[];node.decorator_list=[];node.body=chosen
    space={'json':json, 'contextmanager':contextmanager, 'Refusal':Refusal, 'encode':encode, 'digest':digest, 'ident':ident}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT/'coordinator_runtime'/name), 'exec'), space)
    return space[original]


SelectedStore = methods('store.py', 'Store', ['tx','one','rows','job','attempt','event','enrollment',
    'require_active_sources','source_roles','_input_member','_members','_capacity','execution_complete',
    '_reserve_first','_reserve_candidate','reserve','_attempt','start_job','authorize_launch','begin',
    'session','observe_semantic','collect','claim_recovery','diagnosis_attempt','_handoff','finish_job','adopt_collected'])
SelectedRecovery = methods('recovery.py', 'RecoveryJournal', ['request_recovery','consume_recovery_request','retain_recovery_disposition'])
FULL_STORE = '--full-store' in sys.argv
if FULL_STORE:
    from coordinator_runtime.store import Store
    BaseJournal = Store
else:
    BaseJournal = type('SelectedJournal', (IntegrationJournal, SelectedStore, SelectedRecovery), {})


class Journal(BaseJournal):
    serial=0

    def __init__(self):
        Journal.serial+=1
        self.path=FIXTURES/f'case-{Journal.serial}.sqlite3'
        self.db=sqlite3.connect(self.path, isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.set_trace_callback(lambda sql: self.trace.write(sql+'\n'))
        self.trace=(FIXTURES/f'case-{Journal.serial}.sql').open('w')
        self.db.executescript(''.join(schema(n) for n in ['store.py','delivery.py','custody.py','publication.py','recovery.py'])+INTEGRATION_SCHEMA)
        self.controller='fictional-new-controller'
        self.clock=lambda:100.0
        self.launch_authorizer=None;self.task_launch_authorizer=None
        self.config={'limits':{'max_result_bytes':2*1024*1024,'max_jobs':12},
            'profiles':['fictional-account-label'], 'roles':{'Work':{'owner':'fictional-work-owner'}},
            'tasks':{'integrate':{'role':'Work','phase':'integrator','effects':'owner-reconcile',
                                 'binding':{},'profile':'fictional-account-label'}}}
        class FictionalAllocation:
            def allocate(self):return {'profile':'fictional-account-label','fixture':True}
        self.execution_pool=FictionalAllocation()
        self.db.execute("INSERT INTO enrollments VALUES('Work','fictional-work-owner','fictional-account-label','fictional-grant',0,1,NULL,NULL)")
        self.insert('events', {'id':'old-input','role':'Work','payload':encode({'id':'old-input','original':'ACK is not processing'}),
            'hash':'original-hash','received':1,'state':'queued','ack':'done'})
        member={'event':'old-input','queue':'old-queue','hash':digest(self.event('old-input')),'package':None}
        self.insert('jobs', {'id':'old','role':'Work','phase':'integrator','task':'integrate','members':encode([member]),
            'controller':'fictional-original-controller','token':'original-token','created':1,'state':'held',
            'active_attempt':'old-attempt','effects':'unknown','hold_reason':'malformed PARTIAL primary null'})
        self.insert('queue',{'id':'old-queue','event':'old-input','role':'Work','phase':'integrator','task':'integrate','state':'reserved','job':'old'})
        for aid,kind,controller in [('old-attempt','task','fictional-original-controller'),('diagnosis','diagnosis','fictional-diagnosis-controller')]:
            self.insert('attempts',{'id':aid,'kind':kind,'job':'old','controller':controller,'profile':'fictional-account-label','binding':'{}',
                'state':'collected','created':2,'begin':3,'ended':4,'exit':0,'collected':5,
                'semantic':'PARTIAL','capture':'incomplete','cleanup':'unknown','result':None,'error':'adverse original',
                'detail':encode({'primary':None,'typed':{'semantic':'PARTIAL','unknowns':['effects UNKNOWN']},'late':'retained'})})
            self.insert('results',{'attempt':aid,'job':'old','result':None,'error':'adverse original','exit':0,'capture':'incomplete','created':5})
        self.insert('outboxes', {'id':'old-outbox','role':'Work','job':'old','event':'old-input','producer':'original-producer',
            'recipient':'Work','kind':'question','required':'settled','payload':'{"unknown":"delivery"}','state':'sent','created':6})
        self.insert('file_publications',{'attempt':'old-attempt','target':'fictional-target','state':'intent','error':'effect UNKNOWN'})
        self.insert('artifact_custody',{'attempt':'old-attempt','path':'fictional-source','kind':'report','owner':'original-custodian','witness':'{}','sha256':'fictional'})
        for name in ['next-input','later-input']:self.queued(name)
        self.db.execute('VACUUM INTO ?', (str(FIXTURES/f'case-{Journal.serial}-before.sqlite3'),))

    def insert(self, table, values):
        self.db.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))

    def queued(self, name):
        self.insert('events',{'id':name,'role':'Work','payload':encode({'id':name,'source':'fictional'}),'hash':name,'received':10,'state':'queued','ack':'done'})
        self.insert('queue',{'id':name+'-queue','event':name,'role':'Work','phase':'integrator','task':'integrate'})

    def budget(self, *args):pass  # Fixture is finite; production cumulative accounting is outside this control.
    def input_resolution(self,*args):return None
    def closure(self):
        basis=self.integration_closure_basis('old','original-token')
        return {'basis':basis,'reason':'fictional closed malformed batch; preserve all duties',
            'controllers':[{'controller':c,'collector':'fictional-owning-collector','end':0,'collected':True,'writers_closed':True,
                            'evidence':['fictional original handle END and explicit scoped writer closure']} for c in basis['controllers']]}
    def retire(self):return self.retire_integration('old','original-token','fictional-work-owner',self.closure())
    def selection(self,events=None):
        return {'basis':self.integration_window_basis('integrate',events or ['next-input']),
            'target':'independent fictional next batch','why':'continue without replaying held originals',
            'conflict_evidence':['fictional current peers: this action has no overlap with held target'],
            'custodian_evidence':['fictional original custodian retains effect/publication/source/delivery UNKNOWNs']}
    def select(self):return self.select_integration_window('fictional-work-owner',self.selection())
    def conserved(self):
        return {t:self.rows('SELECT * FROM '+t+' ORDER BY rowid') for t in
            ['jobs','attempts','results','events','queue','outboxes','file_publications','artifact_custody','recovery_requests']}
    def close(self):self.db.close();self.trace.close()


@unittest.skipUnless(__name__ == '__main__', 'requires explicit owned --fixtures root; no implicit writable fixture ecosystem')
class Controls(unittest.TestCase):
    def setUp(self):self.s=Journal();self.addCleanup(self.s.close)
    def refused(self,callback):
        before=self.s.conserved()
        with self.assertRaises(Refusal):callback()
        self.assertEqual(before,self.s.conserved())

    def test_closed_unknown_debt_continues_exactly_once(self):
        s=self.s;before=s.conserved()
        self.assertIsNone(s.reserve())
        s.retire();self.assertEqual(before,s.conserved())
        self.assertTrue(s.execution_complete(s.job('old')))
        self.assertIsNone(s.reserve())  # retirement alone cannot admit a window
        permit=s.select();job=s.reserve()
        self.assertEqual(['next-input'],[m['event'] for m in json.loads(job['members'])])
        attempt=s.start_job(job['id'],job['token'])
        self.assertEqual(permit['id'],s.one('SELECT id FROM integration_windows WHERE job=?',(job['id'],))['id'])
        self.assertEqual('unknown',s.job('old')['effects'])
        self.assertIsNone(s.one("SELECT processed_at FROM events WHERE id='old-input'")['processed_at'])
        self.assertEqual(s.integration_debt(),json.loads(s.attempt(attempt)['detail'])['integration_window']['basis']['debt'])
        self.assertIsNone(s.reserve())
        self.refused(lambda:s.start_job(job['id'],job['token']))
        for table in ['results','outboxes','file_publications','artifact_custody']:
            self.assertEqual(before[table],s.rows('SELECT * FROM '+table+' ORDER BY rowid'))

    def test_missing_related_end_is_not_closed(self):
        self.s.db.execute("UPDATE attempts SET ended=NULL WHERE id='diagnosis'")
        self.refused(self.s.retire)

    def test_null_exit_is_not_numeric(self):
        self.s.db.execute("UPDATE attempts SET exit=NULL WHERE id='old-attempt'")
        self.refused(self.s.retire)

    def test_uncollected_is_not_closed(self):
        self.s.db.execute("UPDATE attempts SET collected=NULL WHERE id='diagnosis'")
        self.refused(self.s.retire)

    def test_controller_end_without_writer_closure_refuses(self):
        r=self.s.closure();r['controllers'][0]['writers_closed']=False
        self.refused(lambda:self.s.retire_integration('old','original-token','fictional-work-owner',r))

    def test_conflicting_controller_list_refuses(self):
        r=self.s.closure();r['controllers'][0]['controller']='foreign-controller'
        self.refused(lambda:self.s.retire_integration('old','original-token','fictional-work-owner',r))

    def test_stale_closure_refuses(self):
        r=self.s.closure();self.s.db.execute("UPDATE attempts SET error='late adverse' WHERE id='old-attempt'")
        self.refused(lambda:self.s.retire_integration('old','original-token','fictional-work-owner',r))

    def test_owner_and_token_fences(self):
        r=self.s.closure()
        self.refused(lambda:self.s.retire_integration('old','original-token','foreign-owner',r))
        self.refused(lambda:self.s.retire_integration('old','foreign-token','fictional-work-owner',r))

    def test_retirement_and_window_replay_refuse(self):
        self.s.retire();self.refused(self.s.retire)
        r=self.s.selection();self.s.select_integration_window('fictional-work-owner',r)
        self.refused(lambda:self.s.select_integration_window('fictional-work-owner',r))

    def test_stale_debt_before_reserve_retains_everything(self):
        s=self.s;s.retire();s.select()
        s.db.execute("UPDATE outboxes SET error='late delivery UNKNOWN' WHERE id='old-outbox'")
        self.assertIsNone(s.reserve())
        self.assertIsNone(s.one('SELECT job FROM integration_windows')['job'])
        s.select();self.assertIsNotNone(s.reserve())

    def test_stale_debt_before_start_refuses(self):
        s=self.s;s.retire();s.select();job=s.reserve()
        s.db.execute("UPDATE file_publications SET error='new uncertainty'")
        self.refused(lambda:s.start_job(job['id'],job['token']))
        self.assertIsNone(s.job(job['id'])['active_attempt'])

    def test_two_controllers_one_reservation(self):
        s=self.s;s.retire();s.select()
        peer=object.__new__(Journal);peer.__dict__=s.__dict__.copy()
        peer.controller='fictional-competing-controller'
        peer.db=sqlite3.connect(s.path,isolation_level=None);peer.db.row_factory=sqlite3.Row
        self.addCleanup(peer.db.close)
        job=s.reserve();self.assertIsNone(peer.reserve())
        self.refused(lambda:peer.start_job(job['id'],job['token']))

    def test_stale_callbacks_cannot_reopen_or_publish(self):
        s=self.s;s.retire()
        self.assertIsNone(s.claim_recovery('old'))
        for call in [lambda:s.diagnosis_attempt('old'),lambda:s.start_job('old','original-token'),
            lambda:s.authorize_launch('old-attempt'),lambda:s.authorize_launch('diagnosis'),lambda:s.finish_job('old','original-token'),lambda:s.adopt_collected('old'),
            lambda:s.request_recovery('old','original-token','old-attempt','fictional-work-owner',{}),
            lambda:s.begin('old-attempt',{}),lambda:s.session('old-attempt','fictional-session'),
            lambda:s.observe_semantic('old-attempt','DONE'),lambda:s.collect('old-attempt',{'exit':0}),
            lambda:s.require_execution_open('old')]:self.refused(call)
        with s.tx():
            with self.assertRaises(Refusal):s._handoff('old','diagnosis')

    def test_changed_successor_source_and_hold_refuse_start(self):
        s=self.s;s.retire();s.select();job=s.reserve()
        s.db.execute("UPDATE events SET hold='source privacy hold' WHERE id='next-input'")
        self.refused(lambda:s.start_job(job['id'],job['token']))
        s.db.execute("UPDATE events SET hold=NULL,payload='{}' WHERE id='next-input'")
        self.refused(lambda:s.start_job(job['id'],job['token']))

    @unittest.skipUnless(FULL_STORE, 'actual effect entrypoints only in separately selected production-import run')
    def test_retired_effect_entrypoints_refuse_before_io(self):
        import asyncio
        from coordinator_runtime import publication, routine, ordinary
        s=self.s;s.retire();job=s.job('old');attempt=s.attempt('old-attempt')
        for call in [lambda:publication.publish(s,None,job,attempt,None,None),
            lambda:publication.locked_publish(s,None,job,attempt,None,None),lambda:routine.reconcile(s,None,job),
            lambda:asyncio.run(ordinary.perform(s,None,job))]:self.refused(call)

    def test_old_reserved_input_cannot_be_successor_member(self):
        s=self.s;s.retire()
        self.refused(lambda:s.integration_window_basis('integrate',['old-input']))
        self.refused(lambda:s.integration_window_basis('integrate',['next-input','next-input']))

    def test_missing_peer_custodian_evidence_and_bound(self):
        s=self.s;s.retire();r=s.selection();r['conflict_evidence']=[]
        self.refused(lambda:s.select_integration_window('fictional-work-owner',r))
        r=s.selection();r['custodian_evidence']=[]
        self.refused(lambda:s.select_integration_window('fictional-work-owner',r))
        s.config['limits']['max_jobs']=1;s.select()
        self.refused(lambda:s.select_integration_window('fictional-work-owner',s.selection(['later-input'])))

    @unittest.skipUnless(FULL_STORE, 'constructor only in separately selected production-import run')
    def test_production_constructor_preserves_schema_and_reopens(self):
        cfg=copy.deepcopy(self.s.config)
        cfg.update(actor='fictional-software-actor',state_dir=str(FIXTURES/'constructor-state'),
                   execution_pool_routes=str(FIXTURES/'never-accessed-fictional-routes'),deadlines={'bind':1})
        for repeat in range(2):
            s=Store(cfg,controller='fictional-constructor-controller')
            try:
                self.assertEqual([],s.rows('SELECT * FROM integration_retirements'))
                self.assertEqual([],s.rows('SELECT * FROM integration_windows'))
                self.assertEqual(digest(cfg),s.one("SELECT value FROM meta WHERE key='configuration'")['value'])
            finally:s.close()
        self.assertFalse(Path(cfg['execution_pool_routes']).exists())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixtures',required=True);p.add_argument('--full-store',action='store_true')
    args,remaining=p.parse_known_args();FIXTURES=Path(args.fixtures)
    FIXTURES.mkdir(mode=0o700,parents=True,exist_ok=False)
    unittest.main(argv=[sys.argv[0],*remaining],verbosity=2)
