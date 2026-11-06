"""Decision13 one-shot genuine-owner pointers; only owned fixtures/fake RPC/CLI.

No installed daemon/native context, actual profile or conversation is probed.
Optional steer helper source is absent from this baseline; mocks test the adapter
contract, not compatibility/arrival of another owner's uncommitted helper.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_continuing as fixtures
from support import ident
from coordinator_runtime.contracts import Refusal,digest
from coordinator_runtime.owner_control import load_helper


class OwnerControl(unittest.TestCase):
    setUp=fixtures.Continuing.setUp

    def delivery(self,recipient='Branch',kind='question'):
        with self.store.tx():
            key=self.store._outbox('Work',recipient,kind,{'reason':'Actual owner reads durable failure; no repeated business execution',
                'unknowns':['Independent effect/publication/consumer duties remain'],'source':'owned synthetic report'},key=ident())
        outbox=self.store.one('SELECT * FROM outboxes WHERE id=?',(key,))
        receipt=self.boards['Work'].post_delivery(self.store,outbox)
        self.store.delivery_observed(key,receipt)
        return key

    def select(self,recipient='Branch',mode='queue-existing',**extra):
        target=self.config['roles'][recipient]
        pins={'queue_transport.py':hashlib.sha256((Path(self.config['board_library'])/'queue_transport.py').read_bytes()).hexdigest()}
        if mode=='active-only-steer':pins.update({'active_transport.py':'0'*64,'active_rpc.py':'0'*64})
        return {'intent':ident(),'mode':mode,'recipient':target['owner'],'profile':target['profile'],
            'scope':'delivery-control-only','evidence':['Synthetic actual caller selection, not independent authentication'],
            'binding':{'context':target['owner'],'profile':target['profile'],'state':'active',
                'turn':ident() if mode=='active-only-steer' else None,'valid_until':time.time()+900,
                'evidence':['Owned synthetic context/profile applicability receipt, not UUID alone']},
            'helper_sources':pins,**extra}

    def prepare(self,delivery,selection):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            return self.boards['Work'].control_prepare(self.store,delivery,selection)

    def send(self,intent,helper=None):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            if helper:
                with patch('coordinator_runtime.owner_control.load_helper',return_value=helper):
                    return self.boards['Work'].control_send(self.store,intent)
            return self.boards['Work'].control_send(self.store,intent)

    def read(self,intent,recipient='Branch'):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles'][recipient]['owner']}):
            return self.boards['Work'].control_show(intent)

    def proof(self,record,recipient='Branch'):
        return {'kind':'existing-context-control','intent':record['id'],'attempt':record['attempt'],
            'client_message_id':record['client_message'],'turn_id':record['selection']['binding']['turn'],
            'received_by':self.config['roles'][recipient]['owner'],'profile':record['profile'],
            'full_read':record['payload_hash'],'state':'processed','evidence':['Synthetic genuine full-read and context/turn association'],
            'disposition':'Input control processed; independent native/business/effect duties remain separately owned'}

    def steer(self,selection,mode='accepted',calls=None):
        def request(recipient,profile,pointer,*,client_message_id,record):
            if calls is not None:calls.append((recipient,profile,pointer,client_message_id))
            if mode=='idle':return SimpleNamespace(status='failed',queue_message_id=None,returncode=None,reason='recipient_not_active')
            record('STEER_INTENT',selection['binding']['turn'],'17')
            seen=self.read(selection['intent'])
            self.assertEqual(seen['state'],'inflight')
            self.assertEqual(seen['steps'][0]['rpc_id'],'17')
            self.assertIn(client_message_id,seen['pointer'])
            if mode=='unknown':raise TimeoutError('owned fake RPC after possible effect')
            record('STEER_ACCEPTED',selection['binding']['turn'],None)
            return SimpleNamespace(status='queued',queue_message_id=None,returncode=0,reason='steer_accepted')
        return SimpleNamespace(steer_notice=request)

    def test_prepare_keeps_full_source_membership_ACK_and_grants_without_native_effect(self):
        key=self.delivery();selection=self.select()
        outbox=self.store.one('SELECT * FROM outboxes WHERE id=?',(key,))
        with self.substrate.database(str(self.path)) as conn:
            member=dict(conn.execute('SELECT * FROM sessions WHERE session=?',(selection['recipient'],)).fetchone())
            notice=dict(conn.execute('SELECT * FROM notification_outbox WHERE post_seq=?',(json.loads(outbox['board_receipt'])['post'],)).fetchone())
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('prepare must not transport')):
            record=self.prepare(key,selection)
        self.assertEqual(record['state'],'prepared');self.assertEqual(record['steps'],[])
        self.assertEqual(record['caller'],self.config['roles']['Work']['owner'])
        self.assertEqual(record['payload_hash'],digest(json.loads(outbox['payload'])))
        self.assertIn('No original input ACK/replay',record['pointer'])
        self.assertEqual(self.store.one('SELECT * FROM outboxes WHERE id=?',(key,)),outbox)
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(dict(conn.execute('SELECT * FROM sessions WHERE session=?',(selection['recipient'],)).fetchone()),member)
            self.assertEqual(dict(conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?',(notice['notification_id'],)).fetchone()),notice)

    def test_actual_baseline_queue_parser_owned_fake_process_and_pre_effect_intent(self):
        key=self.delivery();selection=self.select();prepared=self.prepare(key,selection)
        helper=load_helper(self.boards['Work'],selection);qid=ident()
        observed=[]
        def runner(argv,env,timeout,limit):
            current=self.read(prepared['id']);self.assertEqual(current['state'],'inflight')
            self.assertIn(prepared['attempt'],argv[-1]);self.assertIn(prepared['client_message'],argv[-1])
            self.assertNotIn('--resume',argv);observed.append(argv)
            child=subprocess.run([sys.executable,'-c','print('+repr('Queued message '+qid)+')'],capture_output=True,text=True)
            self.assertEqual(child.returncode,0)
            return helper.CommandOutcome(child.returncode,child.stdout)
        transport=SimpleNamespace(queue_notice=lambda *a,**kw:helper.queue_notice(*a,runner=runner,**kw))
        with patch.object(helper,'_profile_home',return_value=Path(self.temp.name)):
            record=self.send(prepared['id'],transport)
        self.assertEqual(record['state'],'accepted');self.assertEqual(record['result']['queue_message_id'],qid)
        self.assertEqual(len(observed),1)
        self.assertEqual(self.send(prepared['id'],SimpleNamespace()),record)
        self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(key,))['processed_at'])

    def test_steer_requires_explicit_missing_source_interface_not_fallback(self):
        for mode in ['active-only-steer']:
            with self.subTest(mode=mode):
                record=self.prepare(self.delivery(),self.select(mode=mode))
                with self.assertRaises(Refusal):self.send(record['id'])
                kept=self.read(record['id'])
                self.assertEqual(kept['state'],'refused');self.assertEqual(kept['result']['helper_status'],'not-called')
                self.assertEqual(kept['steps'],[])

    def test_queue_resume_preserves_original_binding_receipt_and_one_shot_claim(self):
        key=self.delivery();selection=self.select(mode='queue-resume-existing')
        prepared=self.prepare(key,selection);helper=load_helper(self.boards['Work'],selection)
        qid=ident();calls=[]
        def runner(argv,env,timeout,limit):
            current=self.read(prepared['id'])
            self.assertEqual(current['state'],'inflight')
            self.assertEqual(argv,['codex','queue','--thread',selection['recipient'],
                '--message',current['pointer'],'--resume'])
            self.assertIn(prepared['attempt'],current['pointer'])
            self.assertIn(prepared['client_message'],current['pointer'])
            self.assertEqual(env['CODEX_HOME'],str(Path(self.temp.name)/selection['profile']))
            calls.append(argv)
            return helper.CommandOutcome(0,'Queued message '+qid+'\nWarning: resume unavailable')
        transport=SimpleNamespace(queue_notice=lambda *a,**kw:helper.queue_notice(*a,runner=runner,**kw))
        with patch.object(helper,'_profile_home',return_value=Path(self.temp.name)/selection['profile']):
            record=self.send(prepared['id'],transport)
        self.assertEqual(record['state'],'accepted')
        self.assertEqual(record['result']['queue_message_id'],qid)
        self.assertEqual(record['result']['reason'],'queue_accepted_resume_warning')
        self.assertEqual(self.send(prepared['id'],SimpleNamespace()),record)
        self.assertEqual(len(calls),1)
        self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(key,))['processed_at'])
        with patch.dict(os.environ,{'CODEX_SESSION_ID':selection['recipient']}):
            board=self.boards['Work']
            board.delivery_stage(key,'picked-up',{'evidence':['Fictional full durable read']})
            with self.assertRaisesRegex(Refusal,'queue ID'):
                board.delivery_stage(key,'processed',{'evidence':['Resume warning is not processing']})
            processed=board.delivery_stage(key,'processed',{'evidence':['Fictional actual consumer processing'],
                'transport':{'queue_message_id':qid,'state':'processed','evidence':['Owned queue consumed exact pointer']}})
        self.assertEqual(processed['state'],'processed')

    def test_same_intent_idempotence_and_no_new_intent_over_uncertain_effect(self):
        key=self.delivery();selection=self.select(mode='active-only-steer');record=self.prepare(key,selection)
        self.assertEqual(self.prepare(key,selection),record)
        calls=[];unknown=self.send(record['id'],self.steer(selection,'unknown',calls))
        self.assertEqual(unknown['state'],'unknown');self.assertEqual(len(calls),1)
        self.assertEqual(self.send(record['id'],self.steer(selection,'accepted',calls)),unknown)
        self.assertEqual(len(calls),1)
        with self.assertRaisesRegex(Refusal,'no blind retry'):self.prepare(key,{**selection,'intent':ident()})
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            with self.assertRaisesRegex(Refusal,'cannot be cancelled'):self.boards['Work'].control_cancel(record['id'])

    def test_accepted_steer_no_queue_ID_requires_actual_separate_full_read_disposition_proof(self):
        key=self.delivery();selection=self.select(mode='active-only-steer');prepared=self.prepare(key,selection)
        record=self.send(prepared['id'],self.steer(selection))
        self.assertEqual(record['state'],'accepted');self.assertIsNone(record['result']['queue_message_id'])
        self.assertEqual([s['phase'] for s in record['steps']],['STEER_INTENT','STEER_ACCEPTED'])
        owner=selection['recipient'];board=self.boards['Work']
        with patch.dict(os.environ,{'CODEX_SESSION_ID':owner}):
            full=board.show_delivery(key);self.assertIn('Independent effect',full['payload']['unknowns'][0])
            board.delivery_stage(key,'picked-up',{'evidence':['Actual synthetic full private delivery read']})
            with self.assertRaises(Refusal):board.delivery_stage(key,'processed',{'evidence':['Steer accepted']})
            with self.assertRaisesRegex(Refusal,'no queue ID'):
                board.delivery_stage(key,'processed',{'evidence':['fake queue claim'],'transport':{'queue_message_id':ident(),'state':'processed','evidence':['not a queue']}})
            proof=self.proof(record)
            with self.assertRaises(Refusal):board.delivery_stage(key,'processed',{'evidence':['wrong turn'],'control':{**proof,'turn_id':ident()}})
            board.delivery_stage(key,'processed',{'evidence':['Substantive actual synthetic control disposition'],'control':proof})
            settled=board.delivery_stage(key,'settled',{'evidence':['Bounded control duty settled; no business acceptance'],
                'resolution':'Read/disposed exactly this control, all other duties independent','control':proof})
        self.assertEqual(settled['state'],'settled')
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])

    def test_managed_control_queue_still_requires_real_consumer_queue_proof(self):
        key=self.delivery();selection=self.select();prepared=self.prepare(key,selection);qid=ident()
        helper=SimpleNamespace(queue_notice=lambda *a,**kw:SimpleNamespace(status='queued',queue_message_id=qid,returncode=0,reason='queue_accepted'))
        record=self.send(prepared['id'],helper)
        with patch.dict(os.environ,{'CODEX_SESSION_ID':selection['recipient']}):
            board=self.boards['Work'];board.delivery_stage(key,'picked-up',{'evidence':['Own full read']})
            with self.assertRaisesRegex(Refusal,'queue ID'):board.delivery_stage(key,'processed',{'evidence':['Board ACK only']})
            with self.assertRaises(Refusal):board.delivery_stage(key,'processed',{'evidence':['Wrong consumer'],'transport':{'queue_message_id':ident(),'state':'processed','evidence':['wrong']}})
            processed=board.delivery_stage(key,'processed',{'evidence':['Real synthetic consumer evidence'],
                'transport':{'queue_message_id':qid,'state':'processed','evidence':['Owned fake queue actually consumed this pointer']}})
        self.assertEqual(processed['state'],'processed');self.assertEqual(record['state'],'accepted')

    def test_active_only_refuses_idle_unloaded_unknown_and_changed_actual_turn(self):
        for state in ['idle','unloaded','unknown']:
            selection=self.select(mode='active-only-steer');selection['binding']['state']=state
            with self.assertRaisesRegex(Refusal,'active-only'):self.prepare(self.delivery(),selection)
        selection=self.select(mode='active-only-steer');record=self.prepare(self.delivery(),selection)
        def wrong(*a,record,**kw):record('STEER_INTENT',ident(),'18')
        result=self.send(record['id'],SimpleNamespace(steer_notice=wrong))
        self.assertEqual(result['state'],'unknown');self.assertEqual(result['steps'],[])

    def test_no_enrollment_fabrication_foreign_caller_profile_or_work_execution(self):
        key=self.delivery();selection=self.select()
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.root}):
            with self.assertRaises(Refusal):self.boards['Work'].control_prepare(self.store,key,selection)
        with self.assertRaises(Refusal):self.prepare(key,{**selection,'profile':'.codex4'})
        with self.assertRaises(Refusal):self.prepare(self.delivery(kind='work'),selection)
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Reviews'")
        with self.assertRaises(Refusal):self.prepare(self.delivery(recipient='Reviews'),self.select('Reviews'))
        with self.assertRaisesRegex(Refusal,'post/notice IDs'):self.prepare('18486',selection)

    def test_recipient_revocation_or_membership_change_fences_native_effect(self):
        key=self.delivery();selection=self.select();record=self.prepare(key,selection)
        with patch.dict(os.environ,{'CODEX_SESSION_ID':selection['recipient']}):
            self.boards['Branch'].revoke(self.store.enrollment('Branch')['grant_id'])
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('no transport after revocation')):
            with self.assertRaisesRegex(Refusal,'current role enrollment'):self.send(record['id'])

    def test_unattempted_cancel_and_fresh_selection_never_cancel_inflight_or_acceptance(self):
        key=self.delivery();selection=self.select();record=self.prepare(key,selection)
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            cancelled=self.boards['Work'].control_cancel(record['id'])
        self.assertEqual(cancelled['state'],'refused');self.assertEqual(cancelled['result']['helper_status'],'not-called')
        with self.assertRaisesRegex(Refusal,'no blind retry'):self.prepare(key,{**selection,'intent':ident()})
        fresh={**selection,'intent':ident(),'evidence':['New explicit caller selection after before-effect withdrawal']}
        self.assertEqual(self.prepare(key,fresh)['state'],'prepared')

    def test_fresh_unchanged_violation_intervals_keep_distinct_pointer_intents(self):
        self.store.record_operational_error('unchanged',{'error':'same violation'},'Work')
        deliveries=[]
        for _ in range(2):
            alerts=self.store.emit_alerts()
            row=self.store.one('SELECT * FROM outboxes WHERE alert=?',(alerts[0]['id'],))
            receipt=self.boards['Work'].post_delivery(self.store,row);self.store.delivery_observed(row['id'],receipt)
            selection=self.select('Work');record=self.prepare(row['id'],selection)
            deliveries.append((row['id'],record['id']))
        self.assertNotEqual(deliveries[0][0],deliveries[1][0]);self.assertNotEqual(deliveries[0][1],deliveries[1][1])
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts WHERE subject=?',('unchanged',))),2)

    def test_pinned_helpers_use_exact_loaded_source_not_other_root_module_cache(self):
        root=Path(self.temp.name)/'owned-public-helper-fixture';root.mkdir()
        bodies={'queue_transport.py':"TOKEN='selected-queue'\n",
            'active_rpc.py':"TOKEN='selected-rpc'\n",
            'active_transport.py':"import queue_transport\nimport active_rpc\nTOKENS=(queue_transport.TOKEN,active_rpc.TOKEN)\ndef steer_notice(recipient,profile,pointer,*,client_message_id,record): pass\n"}
        for name,body in bodies.items():(root/name).write_text(body)
        selection=self.select(mode='active-only-steer')
        selection['helper_sources']={name:hashlib.sha256(body.encode()).hexdigest() for name,body in bodies.items()}
        original=sys.modules.get('queue_transport')
        helper=load_helper(SimpleNamespace(library=str(root)),selection)
        self.assertEqual(helper.TOKENS,('selected-queue','selected-rpc'))
        self.assertIs(sys.modules.get('queue_transport'),original)
        (root/'active_rpc.py').write_text("TOKEN='different'\n")
        with self.assertRaisesRegex(Refusal,'source pin changed'):load_helper(SimpleNamespace(library=str(root)),selection)

    def test_original_grant_scope_is_not_rebound_to_a_new_current_grant(self):
        key=self.delivery();selection=self.select()
        with self.substrate.database(str(self.path)) as conn:
            with self.substrate.write(conn):
                conn.execute('UPDATE coordinator_deliveries_v1 SET grant_id=? WHERE id=?',(ident(),key))
        with self.assertRaisesRegex(Refusal,'no custody transfer'):self.prepare(key,selection)

    def test_public_control_interface_unknown_intent_and_send_without_execute_are_refused(self):
        from coordinator_runtime.cli import operate,parser
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            for method in [lambda:self.boards['Work'].control_show(ident()),
                           lambda:self.boards['Work'].control_cancel(ident()),
                           lambda:self.boards['Work'].control_send(self.store,ident())]:
                with self.assertRaises(Refusal):method()
            args=parser().parse_args(['control-send','Work',ident()])
            with self.assertRaisesRegex(Refusal,'--execute'):operate(args,self.store)

    def test_expired_binding_and_queue_acceptance_without_real_ID_never_become_processing(self):
        selection=self.select();selection['binding']['valid_until']=time.time()-1
        with self.assertRaisesRegex(Refusal,'fresh finite'):self.prepare(self.delivery(),selection)
        selection=self.select();record=self.prepare(self.delivery(),selection)
        helper=SimpleNamespace(queue_notice=lambda *a,**kw:SimpleNamespace(status='queued',queue_message_id=None,returncode=0,reason='queue_accepted'))
        unknown=self.send(record['id'],helper)
        self.assertEqual(unknown['state'],'unknown');self.assertIsNone(unknown['result']['queue_message_id'])

    def test_send_claim_crash_stays_inflight_no_replay_or_acceptance_inference(self):
        selection=self.select(mode='active-only-steer');record=self.prepare(self.delivery(),selection)
        def interrupted(*a,record,**kw):
            record('STEER_INTENT',selection['binding']['turn'],'19')
            raise KeyboardInterrupt('Owned fixture interrupted after durable native intent')
        with self.assertRaises(KeyboardInterrupt):self.send(record['id'],SimpleNamespace(steer_notice=interrupted))
        current=self.read(record['id']);self.assertEqual(current['state'],'inflight')
        self.assertIsNone(current['result']);self.assertEqual(len(current['steps']),1)
        self.assertEqual(self.send(record['id'],SimpleNamespace()),current)
