"""Explicit fictional software controls; no native identities, cleanup or pool I/O.

Run directly with --fixtures ABSOLUTE_NEW_OWNED_ROOT under caller isolation.
Production Store constructor/imports/methods and prompt builders are used.
Only allocation is fictional; closure/recovery facts are explicitly seeded
software premises, never actual controller/model/effect evidence.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coordinator_runtime.store import Store
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import job_prompt, recovery_prompt
from coordinator_runtime import publication
from coordinator_runtime.cleanup import eligible_event


class FictionalAllocation:
    def allocate(self):
        return {'profile': 'fictional-allocation', 'fixture': True}


@unittest.skipUnless(__name__ == '__main__', 'requires explicit owned --fixtures root')
class Controls(unittest.TestCase):
    serial = 0

    def setUp(self):
        Controls.serial += 1
        self.root = FIXTURES / str(Controls.serial)
        self.root.mkdir(mode=0o700)
        self.cfg = {'actor': 'fictional-software-actor', 'state_dir': str(self.root/'state'),
            'execution_pool_routes': str(self.root/'not-opened-routes'),
            'profiles': ['fictional-allocation'], 'deadlines': {'bind': 2},
            'limits': {'max_result_bytes': 2*1024*1024, 'max_jobs': 32, 'max_events': 100,
                       'max_attempts': 100, 'max_bytes': 8*1024*1024, 'max_files': 1000},
            'roles': {'Work': {'owner': 'fictional-owner', 'profile': 'fictional-allocation'}},
            'diagnosis': {'binding': {}, 'profile': 'fictional-allocation'},
            'tasks': {'integrate': {'role': 'Work', 'phase': 'integrator', 'binding': {},
                'profile': 'fictional-allocation', 'templates': [], 'purpose': 'configured general purpose',
                'authority': 'fictional software only', 'effect_authority': {}, 'effects': 'owner-reconcile'}}}
        self.s = self.open()
        self.addCleanup(self.s.close)
        self.insert('enrollments', {'role':'Work','owner':'fictional-owner','profile':'fictional-allocation',
            'grant_id':'fictional-grant','cutover':0,'intake':1})
        for n in ['old-input', 'next-input', 'later-input']:
            self.insert('events', {'id':n,'role':'Work','payload':encode({'id':n,'body':'fictional pending input'}),
                'hash':n,'received':1 if n=='old-input' else 10,'state':'queued','ack':'done'})
            self.insert('queue', {'id':n+'-q','event':n,'role':'Work','phase':'integrator','task':'integrate'})
        self.insert('jobs', {'id':'old','role':'Work','phase':'integrator','task':'integrate',
            'members':encode([self.s._input_member(self.s.one("SELECT * FROM queue WHERE event='old-input'"))]),
            'controller':'fictional-closed-controller','token':'old-token','created':1,'state':'held',
            'active_attempt':'old-a','effects':'unknown','hold_reason':'PARTIAL null primary, effects UNKNOWN'})
        self.s.db.execute("UPDATE queue SET state='reserved',job='old' WHERE event='old-input'")
        self.insert('attempts', {'id':'old-a','kind':'task','job':'old','controller':'fictional-closed-controller',
            'profile':'fictional-allocation','binding':'{}','created':1,'begin':2,'ended':3,'exit':7,'collected':4,
            'state':'collected','semantic':'PARTIAL','error':'retained adverse original'})
        self.insert('results', {'attempt':'old-a','job':'old','error':'null primary','exit':7,'capture':'incomplete','created':4})
        self.insert('outboxes', {'id':'old-outbox','role':'Work','job':'old','event':'old-input',
            'producer':'fictional-producer','recipient':'Work','kind':'question','required':'settled',
            'payload':'{"effects":"UNKNOWN"}','state':'sent','created':5})
        self.insert('file_publications', {'attempt':'old-a','target':'fictional-target','state':'intent','error':'UNKNOWN'})
        self.insert('artifact_custody', {'attempt':'old-a','path':'fictional-source','kind':'report',
            'owner':'fictional-old-custodian','witness':'{}','sha256':'fictional'})
        basis = self.s.integration_closure_basis('old','old-token')
        self.s.retire_integration('old','old-token','fictional-owner', {'basis':basis,
            'reason':'fictional closed execution, all duties held', 'controllers':[
                {'controller':c,'collector':'fictional-collector','end':7,'collected':True,
                 'writers_closed':True,'evidence':['fictional scoped closure premise']} for c in basis['controllers']]})
        self.s.db.execute('VACUUM INTO ?', (str(self.root/'before.sqlite3'),))

    def open(self):
        s = Store(self.cfg, controller='fictional-controller', clock=lambda:100.0)
        s.execution_pool = FictionalAllocation()
        trace = (self.root/('trace-'+threading.current_thread().name+'-'+str(len(list(self.root.glob('trace-*'))))+'.sql')).open('x')
        self.addCleanup(trace.close)
        s.db.set_trace_callback(lambda sql: trace.write(sql+'\n'))
        return s

    def insert(self, table, values):
        self.s.db.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')', tuple(values.values()))

    def snapshot(self):
        return {r['name']: self.s.rows('SELECT * FROM '+r['name']+' ORDER BY rowid')
                for r in self.s.rows("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

    def refused(self, fn):
        before = self.snapshot()
        with self.assertRaises(Refusal):fn()
        self.assertEqual(before, self.snapshot())

    def select(self, events=None):
        receipt = {'basis':self.s.integration_window_basis('integrate',events or ['next-input']),
            'target':'TARGET75 selected pending scope','why':'WHY75 keep coordination available',
            'conflict_evidence':['fictional exact peers qualified'],
            'custodian_evidence':['fictional old custodian retains UNKNOWNs and original duties']}
        return self.s.select_integration_window('fictional-owner',receipt)

    def reserve(self):
        self.select()
        return self.s.reserve()

    def withdrawal(self, job):
        return {'basis':self.s.integration_prestart_basis(job['id'],job['token']),
            'reason':'stale before attempt allocation; conserve pending scope',
            'no_launch_evidence':['fictional original controller: no attempt or unrepresented writer launched']}

    def withdraw(self, job, receipt=None):
        return self.s.withdraw_integration_prestart(job['id'],job['token'],'fictional-owner',receipt or self.withdrawal(job))

    def test_stale_prestart_conservation_and_second_window(self):
        j=self.reserve();s=self.s;before=self.snapshot()
        s.db.execute("UPDATE outboxes SET error='late UNKNOWN' WHERE id='old-outbox'")
        self.refused(lambda:s.start_job(j['id'],j['token']))
        adverse=self.snapshot();old_window=s.one('SELECT * FROM integration_windows WHERE job=?',(j['id'],))
        self.withdraw(j)
        for table in adverse:
            if table not in {'jobs','queue','integration_prestart_dispositions'}:
                self.assertEqual(adverse[table],self.snapshot()[table],table)
        self.assertEqual(old_window,s.one('SELECT * FROM integration_windows WHERE job=?',(j['id'],)))
        self.assertEqual([],s.rows('SELECT * FROM attempts WHERE job=?',(j['id'],)))
        self.assertIsNone(s.reserve())  # no fresh selection
        permit=self.select(['later-input','next-input']);successor=s.reserve()
        self.assertEqual(['later-input','next-input'],[m['event'] for m in json.loads(successor['members'])])
        self.assertIn('prestart_disposition',permit and json.loads(permit['receipt'])['basis']['debt'][1])
        a=s.start_job(successor['id'],successor['token']);s.authorize_launch(a)
        self.assertIsNone(s.reserve())
        self.assertEqual(before['results'],self.snapshot()['results'])
        self.assertEqual('unknown',s.job('old')['effects'])
        self.assertTrue(all(r['processed_at'] is None for r in self.snapshot()['events']))
        self.assertTrue(s.execution_complete(s.job(j['id'])))
        self.refused(lambda:s.start_job(j['id'],j['token']))
        self.assertIsNone(s.claim_recovery(j['id']))
        self.refused(lambda:publication.publish(s,None,s.job(j['id']),None,None,None))

    def test_wrong_owner_token_missing_evidence_and_replay(self):
        j=self.reserve();r=self.withdrawal(j);s=self.s
        self.refused(lambda:s.withdraw_integration_prestart(j['id'],j['token'],'foreign-owner',r))
        self.refused(lambda:s.withdraw_integration_prestart(j['id'],'wrong-token','fictional-owner',r))
        bad=copy.deepcopy(r);bad['no_launch_evidence']=[]
        self.refused(lambda:self.withdraw(j,bad))
        self.withdraw(j,r);self.refused(lambda:self.withdraw(j,r))

    def test_changed_disposition_basis_refuses(self):
        j=self.reserve();r=self.withdrawal(j)
        self.s.db.execute("UPDATE events SET hold='new source hold' WHERE id='next-input'")
        self.refused(lambda:self.withdraw(j,r))

    def test_held_source_stays_pending_and_ineligible(self):
        j=self.reserve();self.s.set_hold('next-input','privacy hold')
        self.withdraw(j)
        self.refused(lambda:self.select())
        self.assertEqual('privacy hold',self.s.one("SELECT hold FROM events WHERE id='next-input'")['hold'])
        self.assertEqual('queued',self.s.one("SELECT state FROM queue WHERE event='next-input'")['state'])

    def test_any_allocated_attempt_refuses_even_without_begin(self):
        j=self.reserve();a=self.s.start_job(j['id'],j['token'])
        self.assertIsNone(self.s.attempt(a)['begin'])
        self.refused(lambda:self.withdraw(j))
        self.assertFalse(self.s.execution_complete(self.s.job(j['id'])))

    def test_orphan_attempt_and_changed_queue_ownership_refuse(self):
        j=self.reserve()
        self.s.db.execute("UPDATE queue SET job='old' WHERE event='next-input'")
        self.refused(lambda:self.withdraw(j))
        self.s.db.execute("UPDATE queue SET job=? WHERE event='next-input'",(j['id'],))
        self.insert('attempts',{'id':'orphan','kind':'task','job':j['id'],'controller':'fictional-controller',
            'profile':'fictional-allocation','binding':'{}','created':1})
        self.refused(lambda:self.withdraw(j))

    def test_enrollment_change_requires_current_owner(self):
        j=self.reserve();r=self.withdrawal(j)
        self.s.db.execute("UPDATE enrollments SET owner='fictional-new-owner'")
        self.refused(lambda:self.withdraw(j,r))
        r['basis']=self.s.integration_prestart_basis(j['id'],j['token'])
        self.s.withdraw_integration_prestart(j['id'],j['token'],'fictional-new-owner',r)

    def test_start_wins_then_withdrawal_cannot_release(self):
        j=self.reserve();r=self.withdrawal(j);self.s.start_job(j['id'],j['token'])
        self.refused(lambda:self.withdraw(j,r))

    def test_withdrawal_wins_then_start_cannot_allocate(self):
        j=self.reserve();self.withdraw(j)
        self.refused(lambda:self.s.start_job(j['id'],j['token']))

    def test_competing_connections_reserve_one_after_withdrawal(self):
        j=self.reserve();self.withdraw(j);self.select()
        peer=self.open();self.addCleanup(peer.close)
        reserved=self.s.reserve();self.assertIsNotNone(reserved)
        self.assertIsNone(peer.reserve())

    def test_concurrent_start_and_withdrawal_have_one_winner(self):
        j=self.reserve();receipt=self.withdrawal(j)
        barrier=threading.Barrier(2);outcomes=[];errors=[]
        def contend(mode):
            s=None
            try:
                s=self.open();barrier.wait(timeout=5)
                try:
                    if mode=='start':s.start_job(j['id'],j['token'])
                    else:s.withdraw_integration_prestart(j['id'],j['token'],'fictional-owner',receipt)
                    outcomes.append((mode,'selected'))
                except Refusal:outcomes.append((mode,'refused'))
            except BaseException as exc:errors.append(repr(exc))
            finally:
                if s:s.close()
        threads=[threading.Thread(target=contend,args=(mode,),name=mode) for mode in ['start','withdraw']]
        for t in threads:t.start()
        for t in threads:t.join(timeout=10)
        self.assertTrue(all(not t.is_alive() for t in threads));self.assertEqual([],errors)
        self.assertEqual(1,sum(result=='selected' for mode,result in outcomes))
        self.assertEqual(1,sum(result=='refused' for mode,result in outcomes))
        self.assertEqual(1,int(bool(self.s.integration_retired(j['id'])))+
                            int(bool(self.s.job(j['id'])['active_attempt'])))

    def test_reselection_still_checks_source_debt_and_lifetime_bounds(self):
        j=self.reserve();self.withdraw(j);self.select()
        self.s.db.execute("UPDATE events SET payload='{}' WHERE id='next-input'")
        self.assertIsNone(self.s.reserve())
        self.select()
        self.assertIsNotNone(self.s.reserve())
        self.s.config['limits']['max_jobs']=2
        self.refused(lambda:self.select(['later-input']))

    def test_budget_refusal_retains_reservation(self):
        j=self.reserve();r=self.withdrawal(j)
        self.s.config['limits']['max_bytes']=1
        # Backpressure is a Refusal subclass; no record/queue release commits.
        self.refused(lambda:self.withdraw(j,r))

    def test_withdrawal_is_not_processing_later_processing_and_retention_are_separate(self):
        j=self.reserve()
        self.insert('outboxes', {'id':'prestart-duty','role':'Work','job':j['id'],
            'producer':'fictional-owner','recipient':'Work','kind':'question','required':'settled',
            'payload':'{"pending":"owner duty"}','state':'sent','created':5})
        self.withdraw(j);self.select();successor=self.s.reserve()
        self.s.complete_events()
        self.assertIsNone(self.s.one("SELECT processed_at FROM events WHERE id='next-input'")['processed_at'])
        # Controlled software processing premise, not an actual result/consumer.
        self.s.db.execute("UPDATE jobs SET state='closed',effects='reconciled' WHERE id=?",(successor['id'],))
        self.s.db.execute("UPDATE queue SET state='done' WHERE job=?",(successor['id'],))
        self.s.complete_events()  # still blocked by the withdrawn job's duty
        self.assertIsNone(self.s.one("SELECT processed_at FROM events WHERE id='next-input'")['processed_at'])
        self.s.db.execute("UPDATE outboxes SET state='settled',processed_at=100 WHERE id='prestart-duty'")
        self.s.complete_events()
        event=self.s.one("SELECT * FROM events WHERE id='next-input'")
        self.assertEqual(100,event['processed_at'])
        self.assertFalse(eligible_event(self.s,event))
        self.s.clock=lambda:86501.0
        self.assertTrue(eligible_event(self.s,event))
        self.s.set_hold('next-input','fictional retained privacy hold')
        self.assertFalse(eligible_event(self.s,self.s.one("SELECT * FROM events WHERE id='next-input'")))
        self.assertTrue(self.s.integration_retired(j['id']))
        self.refused(lambda:self.s.start_job(j['id'],j['token']))

    def recovered(self, j, a):
        s=self.s
        # Explicit fictional collected/non-DONE/effect-reconciled premises.
        detail=json.loads(s.attempt(a)['detail']);detail.pop('integration_window',None)
        detail['resume_disposition']='unavailable in fictional software fixture'
        s.db.execute("UPDATE attempts SET state='collected',begin=101,ended=102,collected=103,exit=1,semantic='PARTIAL',error='fictional failure',detail=? WHERE id=?",(encode(detail),a))
        s.db.execute("UPDATE jobs SET state='held',effects='reconciled',hold_reason=NULL,recovery_owner=NULL,recovery_state=NULL,recovery_count=0 WHERE id=?",(j['id'],))
        self.assertIsNotNone(s.claim_recovery(j['id']))
        diagnosis=s.diagnosis_attempt(j['id'])
        prompt=recovery_prompt(s,s.job(j['id']))
        self.assertIn('TARGET75',prompt);self.assertIn('WHY75',prompt)
        choice={'profile':'fictional-allocation','remaining':'deliberately omits selected markers','rationale':'fictional diagnosis'}
        s.db.execute("UPDATE attempts SET state='collected',begin=104,ended=105,collected=106,exit=0,capture='complete',result=? WHERE id=?",(encode(choice),diagnosis))
        return s.handoff(j['id'],diagnosis)

    def test_recovery_target_reason_through_two_successors_and_reopen(self):
        j=self.reserve();a=self.s.start_job(j['id'],j['token'])
        original=self.s.integration_context(j['id'])
        for unused in range(2):
            a=self.recovered(j,a);self.s.authorize_launch(a)
            self.assertEqual(original,json.loads(self.s.attempt(a)['detail'])['integration_window'])
            prompt=job_prompt(self.s,self.s.job(j['id']))
            self.assertIn('TARGET75',prompt);self.assertIn('WHY75',prompt)
        peer=self.open();self.addCleanup(peer.close)
        self.assertEqual(original,peer.integration_context(j['id']))
        self.assertIn('TARGET75',job_prompt(peer,peer.job(j['id'])))
        self.assertFalse(Path(self.cfg['execution_pool_routes']).exists())

    def test_recovered_currentness_and_publication_fences_remain(self):
        j=self.reserve();a=self.s.start_job(j['id'],j['token']);a=self.recovered(j,a)
        self.s.db.execute("UPDATE outboxes SET error='new adverse duty'")
        self.refused(lambda:self.s.authorize_launch(a))
        class FictionalBoard:
            def completion_authority(self,*args):return {'id':'fictional-grant'}
        self.refused(lambda:publication.locked_publish(self.s,FictionalBoard(),self.s.job(j['id']),self.s.attempt(a),{'grant_id':'fictional-grant'},None))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixtures',required=True)
    args,rest=p.parse_known_args();FIXTURES=Path(args.fixtures)
    if not FIXTURES.is_absolute():raise ValueError('absolute owned fixtures required')
    FIXTURES.mkdir(mode=0o700,parents=True,exist_ok=False)
    unittest.main(argv=[sys.argv[0],*rest],verbosity=2)
