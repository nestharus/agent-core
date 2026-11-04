"""Decision16: owned source/grant/collector fixtures; no real native operation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_owner_control as bridge
import test_live_recovery as recovery
from support import collect,event,ident,queued,result
from coordinator_runtime.contracts import Refusal,digest
from coordinator_runtime.store import Store


class AutomaticControls(unittest.TestCase):
    setUp=bridge.OwnerControl.setUp
    delivery=bridge.OwnerControl.delivery
    select=bridge.OwnerControl.select
    prepare=bridge.OwnerControl.prepare
    send=bridge.OwnerControl.send
    read=bridge.OwnerControl.read

    def policy(self,recipient='Branch',**extra):
        target=self.config['roles'][recipient]
        return {'scope':'delivery-control-only','recipients':{recipient:{'context':target['owner'],'profile':target['profile'],
            'mode':'queue-existing','availability':'unknown','evidence':['Actual synthetic existing-context identity; native activity UNKNOWN']}},
            'kinds':['question','alert','effect-request','result'],
            'helper_sources':{'queue_transport.py':hashlib.sha256((Path(self.config['board_library'])/'queue_transport.py').read_bytes()).hexdigest()},
            'valid_until':time.time()+86400,'evidence':['Actual synthetic prospective source-owner delegation to distinct service actor'],**extra}

    def delegate(self,policy=None):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            return self.boards['Work'].delegate_control(self.store,policy or self.policy(),'Decision16 synthetic service authority')

    def helper(self,calls,*,status='queued',reason='queue_accepted',qid=True):
        def send(recipient,profile,pointer,**kw):
            with self.substrate.database(str(self.path)) as conn:
                kept=dict(conn.execute('SELECT * FROM coordinator_controls_v1 WHERE pointer=?',(pointer,)).fetchone())
            self.assertEqual(kept['state'],'inflight');self.assertEqual(kept['caller'],self.config['actor'])
            self.assertNotEqual(kept['caller'],self.config['roles']['Work']['owner'])
            calls.append((recipient,profile,pointer,kw,os.environ.get('CODEX_SESSION_ID')))
            return SimpleNamespace(status=status,queue_message_id=ident() if qid else None,returncode=0,reason=reason)
        return SimpleNamespace(queue_notice=send)

    def test_dispatcher_automatically_sends_digest_failure_control_as_service_with_unknown_availability(self):
        cap=self.delegate();key=self.delivery()
        # Genuine runtime failures commonly use digest keys, not UUIDs.
        with self.store.tx():
            digest_key=self.store._outbox('Work','Branch','question',{'original':'Collected failure; effect/publication duties remain'},key=digest({'synthetic-failure':key}))
        calls=[];actual=os.environ.get('CODEX_SESSION_ID')
        with patch('coordinator_runtime.owner_control.load_helper',return_value=self.helper(calls)):
            self.runtime.pump_deliveries();self.runtime.pump_deliveries();self.runtime.pump_deliveries()
        self.assertEqual(len(calls),2);self.assertTrue(all(c[-1]==actual for c in calls))
        with self.substrate.database(str(self.path)) as conn:
            rows=conn.execute('SELECT * FROM coordinator_controls_v1 ORDER BY created').fetchall()
        self.assertEqual({r['delivery'] for r in rows},{key,digest_key})
        self.assertTrue(all(json.loads(r['selection'])['delegation']==cap['id'] for r in rows))
        self.assertTrue(all(json.loads(r['selection'])['binding']['state']=='unknown' for r in rows))
        self.assertTrue(all(json.loads(self.store.one('SELECT board_receipt FROM outboxes WHERE id=?',(r['delivery'],))['board_receipt'])['control_receipt']['pending'] for r in rows))

    def test_no_implicit_capability_old_notice_replay_or_unenrolled_recipient(self):
        old=self.delivery();calls=[]
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('no implicit capability')):
            self.runtime.pump_deliveries()
        self.delegate()
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('no old replay')):
            self.runtime.pump_deliveries()
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Reviews'")
        with self.assertRaises(Refusal):self.delegate(self.policy('Reviews'))
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.root}):
            with self.assertRaises(Refusal):self.boards['Work'].delegate_control(self.store,self.policy(),'foreign')
        self.assertEqual(calls,[]);self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(old,))['processed_at'])

    def test_revocation_profile_kind_scope_and_policy_expiry_prevent_effect(self):
        cap=self.delegate();key=self.delivery()
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            self.boards['Work'].revoke_control(self.store,cap['id'])
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('revoked capability')):self.runtime.pump_deliveries()
        for change in [{'kinds':['work']},{'valid_until':time.time()-1}]:
            with self.assertRaises(Refusal):self.delegate(self.policy(**change))
        bad=self.policy();bad['recipients']['Branch']['profile']='.codex4'
        with self.assertRaises(Refusal):self.delegate(bad)
        self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(key,))['processed_at'])

    def test_one_new_call_per_pass_unknown_idempotence_and_fresh_interval_alerts_repeat(self):
        self.delegate(self.policy('Work'));self.store.record_operational_error('same violation',{'error':'unchanged'},'Work')
        for _ in range(2):self.store.emit_alerts()
        calls=[]
        with patch('coordinator_runtime.owner_control.load_helper',return_value=self.helper(calls,status='ambiguous',qid=False)):
            self.runtime.pump_deliveries();self.assertEqual(len(calls),1)
            self.runtime.pump_deliveries();self.assertEqual(len(calls),2)
            self.runtime.pump_deliveries();self.assertEqual(len(calls),2)
        self.assertEqual(len(self.store.rows("SELECT * FROM alerts WHERE subject='same violation'")),2)
        self.assertTrue(all(o['processed_at'] is None for o in self.store.rows("SELECT * FROM outboxes WHERE kind='alert'")))

    def test_explicit_resume_warning_keeps_unknown_availability_and_no_arrival_claim(self):
        policy=self.policy();policy['recipients']['Branch']['mode']='queue-resume-existing'
        self.delegate(policy);key=self.delivery();calls=[]
        with patch('coordinator_runtime.owner_control.load_helper',return_value=self.helper(calls,reason='queue_accepted_resume_warning')):
            self.runtime.pump_deliveries()
        self.assertEqual(calls[0][3],{'resume':True})
        with self.substrate.database(str(self.path)) as conn:ctrl=dict(conn.execute('SELECT * FROM coordinator_controls_v1 WHERE delivery=?',(key,)).fetchone())
        self.assertEqual(ctrl['state'],'accepted')
        self.assertEqual(json.loads(ctrl['result'])['reason'],'queue_accepted_resume_warning')
        self.assertTrue(self.boards['Work'].delivery_status(key)['control_receipt']['pending'])

    def test_retained_093_control_without_new_tables_still_requires_real_consumer_proof(self):
        key=self.delivery();record=self.prepare(key,self.select());qid=ident()
        self.send(record['id'],SimpleNamespace(queue_notice=lambda *a,**kw:SimpleNamespace(status='queued',queue_message_id=qid,returncode=0,reason='queue_accepted')))
        with self.substrate.database(str(self.path)) as conn:
            conn.execute('DROP TABLE coordinator_control_requirements_v1');conn.execute('DROP TABLE coordinator_control_receipts_v1')
        board=self.boards['Work'];self.assertTrue(board.delivery_status(key)['control_receipt']['pending'])
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Branch']['owner']}):
            with self.assertRaises(Refusal):board.control_receipt(key,{'evidence':['Acceptance alone']})
            got=board.control_receipt(key,{'evidence':['Actual owned consumer'],
                'transport':{'queue_message_id':qid,'state':'processed','evidence':['Exact owned consumer receipt']}})
        self.assertFalse(got['control_receipt']['pending'])

    def callback_source(self):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            self.boards['Work'].extend_completion(self.store,'Actual synthetic routine delegation')
        source=event(self.config);queued(self.store,source);job=self.store.reserve()
        attempt=self.store.start_job(job['id'],job['token'])
        collect(self.store,attempt,{**result(),'handoffs':[],'no_handoff_reason':'Synthetic result has no independent external handoff'})
        self.store.finish_job(job['id'],job['token'])
        queued(self.store,self.store.event(self.store.job(job['id'])['response']))
        return job,attempt,source

    def test_routine_result_and_effect_substance_complete_while_independent_queue_receipt_is_pending(self):
        self.delegate(self.policy('Work'));job,attempt,source=self.callback_source()
        with self.store.tx():
            self.store.db.execute("UPDATE jobs SET effects='reconciled',effect_receipt=? WHERE id=?",(json.dumps({'actual':'Owned synthetic effect reconciliation'}),job['id']))
            self.store._outbox('Work','Work','effect-request',{'reason':'Already reconciled synthetic effect; independent receipt required'},job=job['id'])
            response=self.store.gate_result_delivery(self.store.job(job['id']),self.store.attempt(attempt),{'reason':'Honest new effect notice'})
        queued(self.store,self.store.event(response))
        calls=[]
        with patch('coordinator_runtime.owner_control.load_helper',return_value=self.helper(calls)):
            self.runtime.pump_deliveries();self.runtime.pump_deliveries()
        rows=self.store.rows('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        self.assertEqual({r['kind'] for r in rows},{'result','effect-request'})
        for row in rows:
            receipt=json.loads(row['board_receipt'])
            self.assertEqual(row['state'],'settled');self.assertTrue(receipt['control_receipt']['pending'])
            self.assertFalse(receipt['processing']['genuine_owner_full_read']);self.assertFalse(receipt['processing']['native_receipt'])
            self.assertIsNone(row['processed_at']);self.assertFalse(self.store.delivery_satisfied(row))
        self.store.complete_events();self.assertTrue(self.store.dependency_hold(source['id']))
        for row in rows:
            with self.substrate.database(str(self.path)) as conn:
                ctrl=dict(conn.execute('SELECT * FROM coordinator_controls_v1 WHERE delivery=?',(row['id'],)).fetchone())
            qid=json.loads(ctrl['result'])['queue_message_id']
            before=self.boards['Work'].delivery_status(row['id'])['processing']
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
                got=self.boards['Work'].control_receipt(row['id'],{'evidence':['Actual owned fixture full read/disposition and consumer'],
                    'transport':{'queue_message_id':qid,'state':'processed','evidence':['Owned fake consumer processed exact pointer']}})
            self.assertFalse(got['control_receipt']['pending']);self.assertEqual(got['processing'],before)
            self.assertGreaterEqual(got['processed_at'],got['control_receipt']['processed_at'])
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('no replay after owner proof')):self.runtime.pump_deliveries()
        self.assertTrue(all(self.store.delivery_satisfied(r) for r in self.store.rows('SELECT * FROM outboxes WHERE job=?',(job['id'],))))

    def test_inflight_callback_preserves_substance_and_does_not_invent_owner_or_native_receipt(self):
        job,attempt,_=self.callback_source();outbox=self.store.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        board=self.boards['Work'];board.post_delivery(self.store,outbox)
        selection=self.select('Work');record=self.prepare(outbox['id'],selection)
        with self.substrate.database(str(self.path)) as conn:conn.execute("UPDATE coordinator_controls_v1 SET state='inflight' WHERE id=?",(record['id'],))
        self.runtime.pump_deliveries()
        got=board.delivery_status(outbox['id']);self.assertEqual(got['state'],'settled')
        self.assertTrue(got['control_receipt']['pending']);self.assertIsNone(got['processed_at'])
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            with self.assertRaises(Refusal):board.control_receipt(outbox['id'],{'evidence':['Callback is not consumer proof']})

    def test_unknown_callback_keeps_independent_duty_and_cannot_use_direct_disposition_as_waiver(self):
        job,_,_=self.callback_source();outbox=self.store.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        board=self.boards['Work'];board.post_delivery(self.store,outbox)
        record=self.prepare(outbox['id'],self.select('Work'))
        self.send(record['id'],SimpleNamespace(queue_notice=lambda *a,**kw:SimpleNamespace(status='ambiguous',queue_message_id=None,returncode=None,reason='sender_timeout')))
        self.runtime.pump_deliveries();got=board.delivery_status(outbox['id'])
        self.assertEqual(got['state'],'settled');self.assertTrue(got['control_receipt']['pending'])
        proof={'kind':'owner-control-disposition','intent':record['id'],'full_read':record['payload_hash'],
            'evidence':['Actual durable full read'],'disposition':'Cannot waive unknown queue consumer duty'}
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            with self.assertRaisesRegex(Refusal,'cannot waive attempted'):board.control_receipt(outbox['id'],{'evidence':['Direct read only'],'control':proof})
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)

    def test_preflight_failure_keeps_required_duty_and_explicit_actual_owner_disposition_is_honest(self):
        self.delegate(self.policy('Work'));job,_,_=self.callback_source()
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=Refusal('Owned public helper unavailable')):self.runtime.pump_deliveries()
        outbox=self.store.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        self.assertEqual(outbox['state'],'settled');self.assertIsNone(outbox['processed_at']);self.assertIsNotNone(outbox['error'])
        with self.substrate.database(str(self.path)) as conn:ctrl=dict(conn.execute('SELECT * FROM coordinator_controls_v1').fetchone())
        self.assertEqual(ctrl['state'],'refused')
        proof={'kind':'owner-control-disposition','intent':ctrl['id'],'full_read':ctrl['payload_hash'],
            'disposition':'Actual owner read through supported durable path and disposed this control only','evidence':['Owned synthetic full delivery/intent read']}
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            got=self.boards['Work'].control_receipt(outbox['id'],{'evidence':['Actual direct owner processing'],'control':proof})
        self.assertFalse(got['control_receipt']['pending']);self.assertFalse(got['control_receipt']['receipt']['native_receipt_claimed'])

    def test_expired_capability_cannot_hide_required_control_behind_completed_callback(self):
        self.delegate(self.policy('Work'));job,_,_=self.callback_source()
        with patch('coordinator_runtime.automatic_control.time.time',return_value=time.time()+86401), patch(
                'coordinator_runtime.owner_control.load_helper',side_effect=AssertionError('no expired control effect')):
            self.runtime.pump_deliveries()
        outbox=self.store.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        self.assertEqual(outbox['state'],'settled');self.assertIsNone(outbox['processed_at'])
        status=json.loads(outbox['board_receipt'])['control_receipt']
        self.assertTrue(status['pending']);self.assertIsNone(status['intent'])
        # Fresh explicit source-owner preparation can bind the outstanding duty;
        # this is not an automatic renewal, native call or business replay.
        prepared=self.prepare(outbox['id'],self.select('Work'))
        self.assertEqual(prepared['state'],'prepared')


class LegacyDiagnoses(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=recovery.OwnerRecovery.asyncSetUp
    held=recovery.OwnerRecovery.held
    request=recovery.OwnerRecovery.request

    def legacy(self,**extra):
        job,task=self.held(result('UNKNOWN'),**extra)
        self.store.claim_recovery(job['id']);diag=self.store.diagnosis_attempt(job['id'])
        collect(self.store,diag,{'profile':'.codex3','remaining':'Old diagnosis is not replay authority','rationale':'Original semantic/effect gaps retained'})
        detail=json.loads(self.store.attempt(diag)['detail']);detail.pop('prior_task_attempt');detail.pop('owner_selection')
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(json.dumps(detail),diag))
        return self.store.job(job['id']),task,diag

    async def test_incomplete_capture_legacy_zero_is_recognized_only_for_owner_disposition(self):
        job,task,diag=self.legacy(capture='incomplete',error='missing matching turn completion')
        original=self.store.attempt(task);historical=self.store.attempt(diag)
        current=self.store.current_diagnosis(job)
        self.assertEqual(current['legacy_lineage']['task'],task)
        self.assertRaises(Refusal,self.store.diagnosis_choice,job,current)
        self.runtime.advance_recovery(job['id'],diag)
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'awaiting-disposition')
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.attempt(task),original);self.assertEqual(self.store.attempt(diag),historical)
        self.assertEqual(self.request(job,task)['state'],'pending');self.assertFalse(self.runtime.active)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)

    async def test_handoff_and_inventory_errors_stay_original_after_legacy_recognition(self):
        job,task,diag=self.legacy(capture='artifact-inventory-incomplete',error='clarification erased or rewrote original handoffs; inventory refused')
        before=self.store.attempt(task)
        request=self.request(job,task)
        self.assertEqual(request['state'],'pending');self.assertEqual(self.store.attempt(task),before)
        self.assertEqual(self.store.job(job['id'])['hold_reason'],job['hold_reason'])
        self.assertEqual(self.store.attempt(diag)['semantic'],None)
        self.assertNotIn('prior_task_attempt',json.loads(self.store.attempt(diag)['detail']))

    async def test_foreign_request_can_queue_but_cannot_dispose_or_collect_legacy(self):
        job,task,diag=self.legacy(error='clarification erased original handoffs')
        other=Store(self.config);self.addCleanup(other.close)
        receipt={'mode':'redispose','reason':'Actual role owner requests exact collected disposition','evidence':['synthetic permitted source'],'remaining':None}
        request=other.request_recovery(job['id'],job['token'],task,self.owner,receipt)
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'diagnosing')
        with self.assertRaisesRegex(Refusal,'original collector'):other.consume_recovery_request(request['id'])
        self.assertEqual(self.store.consume_recovery_request(request['id'])['receipt'],receipt)
        self.assertEqual(self.store.job(job['id'])['recovery_owner'],job['recovery_owner'])
        self.assertEqual(self.store.job(job['id'])['active_attempt'],task)
        self.assertIsNone(self.store.job(job['id'])['collection_handoff'])

    async def test_ambiguous_collector_or_missing_END_lineage_is_precise_question_not_success(self):
        job,task,diag=self.legacy()
        self.store.db.execute('UPDATE attempts SET exit=NULL WHERE id=?',(diag,))
        with self.assertRaisesRegex(Refusal,'actual collected END/controller'):self.request(job,task)
        self.store.db.execute('UPDATE attempts SET exit=0 WHERE id=?',(diag,))
        duplicate=self.store._attempt('diagnosis',None,job['id'],self.config['diagnosis']['binding'],self.config['diagnosis']['profile'])
        collect(self.store,duplicate,{'profile':'@owner','remaining':'Ambiguous original','rationale':'No inferred closure'})
        with self.assertRaisesRegex(Refusal,'ambiguous legacy diagnosis lineage'):self.request(job,task)
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'diagnosing')
        self.assertFalse(self.runtime.active)
