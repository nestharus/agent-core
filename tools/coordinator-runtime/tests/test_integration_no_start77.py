"""Owned fictional protocol controls for Work48729, requiring explicit fixtures.

No native/Board/pool/session execution, HOME substitution, or file retirement.
Production journal, prompt and CLI interfaces are used under caller kernel RO.
Base75 helpers seed explicitly fictional collected old debt and allocation.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_integration_continuity75 as base
from coordinator_runtime import cli, publication
from coordinator_runtime.cleanup import eligible_event
from coordinator_runtime.contracts import Refusal, encode
from coordinator_runtime.dispatcher import job_prompt, recovery_prompt


class Controls(base.Controls):
    __unittest_skip__ = False

    def setUp(self):
        # CUMULATIVE retained bytes/files checked BEFORE each new fixture setup.
        files = [p for p in FIXTURES.parent.rglob('*') if p.is_file()]
        used = sum(p.stat().st_size for p in files)
        free = os.statvfs(FIXTURES).f_bavail * os.statvfs(FIXTURES).f_frsize
        mem = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))) * 1024
        observation = {'before_case': self._testMethodName, 'bytes': used, 'files': len(files),
            'remaining_bytes': 64*1024*1024-used, 'remaining_files': 2000-len(files),
            'next_case_envelope_bytes': 6*1024*1024, 'next_case_envelope_files': 32,
            'free_bytes': free, 'MemAvailable_bytes': mem}
        with (FIXTURES/'headroom.jsonl').open('a') as out:out.write(json.dumps(observation)+'\n')
        if used+6*1024*1024>64*1024*1024 or len(files)+32>2000 or free<40*1024**3 or mem<4*1024**3:
            raise RuntimeError('cumulative fixture/floor bound; retain everything and stop')
        super().setUp()
        self.s.db.execute('PRAGMA wal_autocheckpoint=16')

    def allocated(self, collect=True):
        j=self.reserve();a=self.s.start_job(j['id'],j['token'])
        if collect:self.no_start(a)
        return j,a

    def no_start(self,a):
        self.s.collect(a, {'exit':None, 'result':None, 'error':'fictional prelaunch currentness refusal',
            'capture':'not-started','cleanup':'no-session-created',
            'detail':{'known_not_started':True,'resume_disposition':'fictional collector confirms no process creation'}})
        self.s.hold_job(self.s.attempt(a)['job'],'fictional retained owner hold')

    def no_start_receipt(self,j):
        basis=self.s.integration_no_start_basis(j['id'],j['token'])
        return {'basis':basis,'reason':'fresh selection needed after qualified stale-prelaunch refusal',
            'controllers':[{'controller':c,'collector':'fictional actual collector', 'writers_closed':True,
                'no_launch':True,'evidence':['fictional scoped positive no-process and closed-launcher evidence']}
                for c in basis['controllers']]}

    def dispose(self,j,receipt=None,actor='fictional-owner'):
        return self.s.withdraw_integration_no_start(j['id'],j['token'],actor,receipt or self.no_start_receipt(j))

    def test77_allocated_stale_no_start_continues_and_conserves(self):
        j,a=self.allocated(False);s=self.s
        s.db.execute("UPDATE outboxes SET error='late adverse UNKNOWN' WHERE id='old-outbox'")
        self.refused(lambda:s.authorize_launch(a));self.no_start(a)
        before=self.snapshot();window=s.integration_context(j['id'])
        self.dispose(j)
        after=self.snapshot()
        for table in before:
            if table not in {'jobs','queue','integration_prestart_dispositions'}:self.assertEqual(before[table],after[table],table)
        job=s.job(j['id']);self.assertEqual('fictional retained owner hold',job['hold_reason'])
        self.assertEqual(before['jobs'][-1]['effects'],job['effects'])
        self.assertEqual(window,s.integration_context(j['id']))
        self.assertTrue(s.execution_complete(job));self.assertIsNone(s.reserve())
        selected=self.select(['later-input','next-input']);successor=s.reserve()
        self.assertEqual(['later-input','next-input'],[m['event'] for m in json.loads(successor['members'])])
        next_attempt=s.start_job(successor['id'],successor['token']);s.authorize_launch(next_attempt)
        self.assertIsNone(s.reserve())
        self.assertIn('TARGET75',job_prompt(s,s.job(successor['id'])));self.assertIn('WHY75',job_prompt(s,s.job(successor['id'])))
        self.assertTrue(all(e['processed_at'] is None for e in self.snapshot()['events']))
        self.assertEqual(before['attempts'],self.snapshot()['attempts'][:-1])
        debt=json.loads(selected['receipt'])['basis']['debt'];self.assertEqual(2,len(debt))
        self.assertEqual('unknown',s.job('old')['effects'])
        peer=self.open();self.addCleanup(peer.close)
        self.assertTrue(peer.integration_retired(j['id']));self.assertIsNone(peer.attempt(a)['ended'])
        self.assertIsNone(peer.attempt(a)['exit']);self.assertIsNone(peer.attempt(a)['session'])
        self.assertFalse(Path(self.cfg['execution_pool_routes']).exists())

    def test77_missing_begin_and_unknown_collection_never_qualify(self):
        j,a=self.allocated(False)
        self.refused(lambda:self.dispose(j))
        self.s.collect(a,{'exit':None,'result':None,'capture':'unknown','cleanup':'pending','detail':{}})
        self.refused(lambda:self.dispose(j))
        self.assertFalse(self.s.execution_complete(self.s.job(j['id'])))

    def test77_process_created_or_session_evidence_refuses(self):
        j,a=self.allocated(False);self.s.begin(a,{'fictional':'process created before begin'})
        self.s.collect(a,{'exit':None,'result':None,'capture':'unknown','cleanup':'pending',
            'detail':{'known_not_started':True,'resume_disposition':'contradictory no-start'}})
        self.refused(lambda:self.dispose(j))

    def test77_conflicting_native_fields_refuse(self):
        j,a=self.allocated();original=self.s.attempt(a)
        for field,value in [('begin',101),('ended',102),('exit',0),('session','fictional-invalid'),('turn','fictional-invalid'),('semantic','DONE'),('result','{}')]:
            with self.subTest(field=field):
                self.s.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(value,a))
                self.refused(lambda:self.dispose(j))
                self.s.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(original[field],a))

    def test77_exact_owner_token_basis_evidence_and_replay(self):
        j,a=self.allocated();r=self.no_start_receipt(j)
        self.refused(lambda:self.dispose(j,r,'foreign-owner'))
        self.refused(lambda:self.s.withdraw_integration_no_start(j['id'],'wrong','fictional-owner',r))
        for key,value in [('writers_closed',False),('no_launch',False),('evidence',[])]:
            bad=copy.deepcopy(r);bad['controllers'][0][key]=value
            self.refused(lambda:self.dispose(j,bad))
        bad=copy.deepcopy(r);bad['controllers']=[];self.refused(lambda:self.dispose(j,bad))
        bad=copy.deepcopy(r);bad['controllers'][0]['end']=0;self.refused(lambda:self.dispose(j,bad))
        self.s.db.execute("UPDATE events SET ack='pending' WHERE id='next-input'")
        self.refused(lambda:self.dispose(j,r))
        self.dispose(j);self.refused(lambda:self.dispose(j))

    def test77_recovery_claim_and_all_controllers_remain_accountable(self):
        j,a=self.allocated();peer=self.open();peer.controller='fictional-other-recovery-controller';self.addCleanup(peer.close)
        self.assertIsNotNone(peer.claim_recovery(j['id']))
        r=self.no_start_receipt(j);self.assertEqual(2,len(r['controllers']))
        bad=copy.deepcopy(r);bad['controllers'].pop();self.refused(lambda:self.dispose(j,bad))
        bad=copy.deepcopy(r);bad['controllers'][1]=bad['controllers'][0];self.refused(lambda:self.dispose(j,bad))
        self.dispose(j,r)
        self.assertEqual('claimed',self.s.job(j['id'])['recovery_state'])
        self.refused(lambda:self.s.diagnosis_attempt(j['id']))
        self.assertIsNone(self.s.claim_recovery(j['id']))

    def test77_uncollected_diagnosis_and_pending_selection_refuse(self):
        j,a=self.allocated();self.s.claim_recovery(j['id']);d=self.s.diagnosis_attempt(j['id'])
        self.refused(lambda:self.dispose(j))
        self.no_start(d)
        self.insert('recovery_requests',{'id':'pending-own-selection','job':j['id'],'attempt':a,
            'actor':'fictional-owner','receipt':'{}','state':'pending','created':100})
        self.refused(lambda:self.dispose(j))

    def test77_source_holds_and_new_debt_require_fresh_selection(self):
        j,a=self.allocated();r=self.no_start_receipt(j)
        self.s.set_hold('next-input','fictional source privacy hold')
        self.refused(lambda:self.dispose(j,r));self.dispose(j)
        self.refused(lambda:self.select())
        self.select(['later-input']);next_job=self.s.reserve()
        self.assertEqual(['later-input'],[m['event'] for m in json.loads(next_job['members'])])
        self.assertEqual('fictional source privacy hold',self.s.one("SELECT hold FROM events WHERE id='next-input'")['hold'])

    def test77_publication_outbox_effect_and_retention_duties_survive(self):
        j,a=self.allocated();s=self.s
        self.insert('file_publications',{'attempt':a,'target':'fictional-own-intent','state':'intent','error':'UNKNOWN'})
        self.insert('outboxes',{'id':'allocated-duty','role':'Work','job':j['id'],'producer':'fictional-owner',
            'recipient':'Work','kind':'question','required':'settled','payload':'{}','state':'sent','created':50})
        self.dispose(j);self.select();successor=s.reserve()
        # Controlled processing premise only; no native/model/consumer result claim.
        s.db.execute("UPDATE jobs SET state='closed',effects='reconciled' WHERE id=?",(successor['id'],))
        s.db.execute("UPDATE queue SET state='done' WHERE job=?",(successor['id'],))
        s.complete_events();self.assertIsNone(s.one("SELECT processed_at FROM events WHERE id='next-input'")['processed_at'])
        s.db.execute("UPDATE outboxes SET state='settled',processed_at=100 WHERE id='allocated-duty'")
        s.complete_events();self.assertIsNone(s.one("SELECT processed_at FROM events WHERE id='next-input'")['processed_at'])
        # Fictional original custodian settles intent, separately from unknown effects.
        s.db.execute("UPDATE file_publications SET state='published' WHERE attempt=?",(a,))
        s.complete_events();self.assertIsNone(s.one("SELECT processed_at FROM events WHERE id='next-input'")['processed_at'])
        s.db.execute("UPDATE jobs SET effects='reconciled' WHERE id=?",(j['id'],))
        s.complete_events();e=s.one("SELECT * FROM events WHERE id='next-input'")
        self.assertEqual(100,e['processed_at']);self.assertFalse(eligible_event(s,e))
        s.clock=lambda:86500.0;self.assertTrue(eligible_event(s,e))
        # Later adverse publication/effect/capture facts still block eligibility.
        s.db.execute("UPDATE file_publications SET state='intent' WHERE attempt=?",(a,));self.assertFalse(eligible_event(s,e))
        s.db.execute("UPDATE file_publications SET state='published' WHERE attempt=?",(a,))
        s.db.execute("UPDATE attempts SET cleanup='pending' WHERE id=?",(a,));self.assertFalse(eligible_event(s,e))
        s.db.execute("UPDATE attempts SET cleanup='no-session-created' WHERE id=?",(a,))
        s.set_hold('next-input','fictional retention hold');self.assertFalse(eligible_event(s,s.one("SELECT * FROM events WHERE id='next-input'")))

    def test77_late_callbacks_launch_publication_and_recovery_fenced(self):
        j,a=self.allocated();self.dispose(j);s=self.s
        for fn in [lambda:s.begin(a,{}), lambda:s.session(a,'fictional-late'),lambda:s.observe_semantic(a,'DONE'),
                lambda:s.authorize_launch(a),lambda:s.start_job(j['id'],j['token']),
                lambda:publication.publish(s,None,s.job(j['id']),None,None,None)]:self.refused(fn)
        self.assertIsNone(s.claim_recovery(j['id']))

    def test77_budget_and_lifetime_refusal_keep_duties(self):
        j,a=self.allocated();r=self.no_start_receipt(j)
        self.s.config['limits']['max_bytes']=1;self.refused(lambda:self.dispose(j,r))
        self.s.config['limits']['max_bytes']=8*1024*1024;self.dispose(j,r)
        self.s.config['limits']['max_jobs']=1;self.refused(lambda:self.select())

    def test77_serialized_competing_withdrawals_one_winner(self):
        j,a=self.allocated();r=self.no_start_receipt(j);barrier=threading.Barrier(2);results=[];errors=[]
        def contend():
            s=None
            try:
                s=self.open();barrier.wait(timeout=5)
                try:s.withdraw_integration_no_start(j['id'],j['token'],'fictional-owner',r);results.append('selected')
                except Refusal:results.append('refused')
            except BaseException as exc:errors.append(repr(exc))
            finally:
                if s:s.close()
        threads=[threading.Thread(target=contend,name='fictional-contender-'+str(i)) for i in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(timeout=10)
        self.assertTrue(all(not t.is_alive() for t in threads));self.assertEqual([],errors)
        self.assertEqual(['refused','selected'],sorted(results))
        self.select();peer=self.open();self.addCleanup(peer.close)
        self.assertIsNotNone(self.s.reserve());self.assertIsNone(peer.reserve())

    def test77_collected_diagnosis_does_not_strand_no_start_tasks(self):
        j,a=self.allocated();s=self.s;s.claim_recovery(j['id']);d=s.diagnosis_attempt(j['id'])
        # Explicit fictional real-run diagnosis closure, never an invented task END.
        s.begin(d,{'premise':'fictional read-only diagnosis process ran'})
        s.collect(d,{'exit':0,'capture':'complete','cleanup':'done','result':{'remaining':'fictional retained diagnosis'},'detail':{}})
        before=self.snapshot();self.dispose(j)
        self.assertEqual(before['attempts'],self.snapshot()['attempts'])
        self.assertEqual(before['results'],self.snapshot()['results'])
        self.assertIsNone(s.attempt(a)['ended']);self.assertEqual(0,s.attempt(d)['exit'])
        self.select();successor=s.reserve();new=s.start_job(successor['id'],successor['token']);s.authorize_launch(new)
        self.assertIsNone(s.reserve());self.refused(lambda:s.diagnosis_attempt(j['id']))

    def test77_changed_source_custody_requires_fresh_basis(self):
        j,a=self.allocated();r=self.no_start_receipt(j)
        self.insert('source_custody',{'event':'next-input','basis':'fictional-custody','owner':'fictional-custodian','binding':'{}'})
        self.refused(lambda:self.dispose(j,r));self.dispose(j)
        self.assertEqual('fictional-custodian',self.s.one("SELECT owner FROM source_custody WHERE event='next-input'")['owner'])

    def test77_callback_and_disposition_serialize_without_overlap(self):
        j,a=self.allocated();r=self.no_start_receipt(j);barrier=threading.Barrier(2);results=[];errors=[]
        def contend(mode):
            s=None
            try:
                s=self.open();barrier.wait(timeout=5)
                try:
                    if mode=='callback':s.session(a,'fictional-conflicting-native-observation')
                    else:s.withdraw_integration_no_start(j['id'],j['token'],'fictional-owner',r)
                    results.append((mode,'selected'))
                except Refusal:results.append((mode,'refused'))
            except BaseException as exc:errors.append(repr(exc))
            finally:
                if s:s.close()
        threads=[threading.Thread(target=contend,args=(m,),name='fictional-'+m) for m in ['callback','withdraw']]
        for t in threads:t.start()
        for t in threads:t.join(timeout=10)
        self.assertTrue(all(not t.is_alive() for t in threads));self.assertEqual([],errors)
        self.assertEqual(1,sum(result=='selected' for mode,result in results))
        self.assertEqual(1,sum(result=='refused' for mode,result in results))
        self.assertEqual(1,int(bool(self.s.integration_retired(j['id'])))+int(bool(self.s.attempt(a)['session'])))

    def test77_cli_authority_routes_before_journal_action(self):
        j,a=self.allocated();s=self.s
        args=argparse.Namespace(command='integration-no-start-basis',job=j['id'],token=j['token'])
        class FictionalBoard:
            def __init__(self,config,role):self.role=role
            def verify_authority(self,store):raise Refusal('fictional Board authority refused')
        with patch.object(cli,'actual_actor',return_value='fictional-owner'),patch.object(cli,'Board',FictionalBoard):
            self.refused(lambda:cli.operate(args,s))
        class FictionalAuthorizedBoard(FictionalBoard):
            def verify_authority(self,store):return None
        with patch.object(cli,'actual_actor',return_value='fictional-owner'),patch.object(cli,'Board',FictionalAuthorizedBoard):
            self.assertEqual(self.no_start_receipt(j)['basis'],cli.operate(args,s))
            args.command='withdraw-integration-no-start';args.receipt=str(self.root/'receipt.json')
            Path(args.receipt).write_text(encode(self.no_start_receipt(j)))
            cli.operate(args,s)
        self.assertTrue(s.integration_retired(j['id']))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',required=True);parser.add_argument('--cases',nargs='+')
    args=parser.parse_args();FIXTURES=Path(args.fixtures)
    if not FIXTURES.is_absolute():raise ValueError('absolute owned fixture root required')
    FIXTURES.mkdir(mode=0o700,parents=True,exist_ok=False);base.FIXTURES=FIXTURES
    names=args.cases or [n for n in dir(Controls) if n.startswith('test77_')]
    suite=unittest.TestSuite(Controls(n) for n in names)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    raise SystemExit(not result.wasSuccessful())
