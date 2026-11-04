"""Decision19 supplied counterpaths and held-success shape, owned fixtures only.

The frozen incident is already evidence. Authored fixture state is not a live
reproduction/history edit; no real helper/model/native/board context is called.
"""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch

import test_control_recovery as controls
import test_live_recovery as recovery
from support import collect,ident
from coordinator_runtime.contracts import LUNA,Refusal,encode
from coordinator_runtime.dispatcher import Dispatcher,job_prompt
from coordinator_runtime.store import Store


class ReceiptConservation(unittest.TestCase):
    setUp=controls.AutomaticControls.setUp
    select=controls.AutomaticControls.select
    prepare=controls.AutomaticControls.prepare
    send=controls.AutomaticControls.send
    callback_source=controls.AutomaticControls.callback_source

    def prepared_result(self):
        job,_,source=self.callback_source()
        outbox=self.store.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        board=self.boards['Work'];board.post_delivery(self.store,outbox)
        intent=self.prepare(outbox['id'],self.select('Work'))
        return board,outbox,intent,source

    def receive(self,board,key,receipt):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.config['roles']['Work']['owner']}):
            return board.control_receipt(key,receipt)

    def direct(self,intent):
        return {'evidence':[{'source':'owned full-read witness','disposition':'Actual same-owner control read and processed'}],
            'control':{'kind':'owner-control-disposition','intent':intent['id'],'full_read':intent['payload_hash'],
                       'disposition':'Direct processing before any native send','evidence':['Actual full source read, no native claim']}}

    def test_complete_supplied_queue_receipt_is_retained_and_changed_evidence_is_immutable(self):
        board,outbox,intent,_=self.prepared_result();qid=ident()
        helper=SimpleNamespace(queue_notice=lambda *a,**kw:SimpleNamespace(status='queued',queue_message_id=qid,returncode=0,reason='queue_accepted'))
        self.send(intent['id'],helper);self.runtime.pump_deliveries()
        supplied={'evidence':[{'full_read':intent['payload_hash'],'source':'Owned genuine full-read/disposition witness'}],
            'disposition':{'action':'Actual control processing only','remaining':['Independent source/effect/consumer duties']},
            'transport':{'queue_message_id':qid,'state':'processed','evidence':['Distinct exact consumer witness']}}
        got=self.receive(board,outbox['id'],supplied)
        self.assertEqual(got['control_receipt']['receipt']['supplied_receipt'],supplied)
        self.assertEqual(got['control_receipt']['receipt']['transport'],supplied['transport'])
        self.assertFalse(got['control_receipt']['pending']);self.assertIsNotNone(got['processed_at'])
        self.assertEqual(self.receive(board,outbox['id'],copy.deepcopy(supplied)),got)
        for changed in [{**supplied,'evidence':['Different full-read evidence']},{**supplied,'disposition':{'action':'Different admitted meaning'}}]:
            with self.assertRaisesRegex(Refusal,'immutable'):self.receive(board,outbox['id'],changed)
        self.assertEqual(board.delivery_status(outbox['id']),got)

    def test_direct_disposition_during_preflight_prevents_claim_call_and_keeps_legitimate_callback(self):
        board,outbox,intent,_=self.prepared_result();calls=[]
        def preflight(*args):
            self.assertIsNone(board.delivery_status(outbox['id'])['substantive_processed_at'])
            self.receive(board,outbox['id'],self.direct(intent))
            def timeout(*args,**kwargs):
                calls.append('unexpected native effect')
                return SimpleNamespace(status='ambiguous',queue_message_id=None,returncode=None,reason='sender_timeout')
            return SimpleNamespace(queue_notice=timeout)
        with patch('coordinator_runtime.owner_control.load_helper',side_effect=preflight):
            with self.assertRaisesRegex(Refusal,'processed during preflight'):self.send(intent['id'])
        self.assertEqual(calls,[])
        with self.substrate.database(str(self.path)) as conn:
            ctrl=conn.execute('SELECT state,result FROM coordinator_controls_v1 WHERE id=?',(intent['id'],)).fetchone()
        self.assertEqual(tuple(ctrl),('prepared',None))
        self.runtime.pump_deliveries();got=board.delivery_status(outbox['id'])
        self.assertEqual(got['state'],'settled');self.assertFalse(got['control_receipt']['pending'])
        self.assertFalse(got['processing']['genuine_owner_full_read'])
        self.assertFalse(got['control_receipt']['receipt']['native_receipt_claimed'])
        self.assertEqual(got['control_receipt']['receipt']['supplied_receipt'],self.direct(intent))

    def test_retained_bad_interleaving_cannot_hide_unknown_or_inflight_send_behind_direct_receipt(self):
        board,outbox,intent,source=self.prepared_result()
        self.receive(board,outbox['id'],self.direct(intent))
        # Incoming shape supplied by O16-PREFLIGHT-RACE, never a production state edit.
        with self.substrate.database(str(self.path)) as conn:
            conn.execute("UPDATE coordinator_controls_v1 SET state='unknown',result=? WHERE id=?",
                (encode({'helper_status':'ambiguous','queue_message_id':None,'reason':'sender_timeout'}),intent['id']))
        self.runtime.pump_deliveries()
        for state in ['unknown','inflight']:
            with self.substrate.database(str(self.path)) as conn:conn.execute('UPDATE coordinator_controls_v1 SET state=? WHERE id=?',(state,intent['id']))
            got=board.delivery_status(outbox['id']);self.store.delivery_observed(outbox['id'],got)
            self.assertEqual(got['state'],'settled');self.assertTrue(got['control_receipt']['pending'])
            self.assertTrue(got['control_receipt']['unresolved_send']);self.assertIsNone(got['processed_at'])
            self.assertFalse(self.store.delivery_satisfied(self.store.one('SELECT * FROM outboxes WHERE id=?',(outbox['id'],))))
            self.assertTrue(self.store.dependency_hold(source['id']))


class RetainedDiagnosis(unittest.IsolatedAsyncioTestCase):
    held=recovery.OwnerRecovery.held
    request=recovery.OwnerRecovery.request

    async def asyncSetUp(self):
        await recovery.OwnerRecovery.asyncSetUp(self)
        self.job,self.original=self.held()
        self.store.reconcile_effects(self.job['id'],self.job['token'],self.owner,
            {'evidence':['Actual owned fixture original effects accounted; publication remains independently gated'],'unknown_effects':[]})
        self.store.claim_recovery(self.job['id']);self.failed=self.store.diagnosis_attempt(self.job['id'])
        collect(self.store,self.failed,None,error='Historical turn/interrupt RPC error')
        self.runtime.advance_recovery(self.job['id'],self.failed)
        self.original_collector=self.store.controller
        # Existing supported closure-only transfer, preserving original collector/END.
        self.store=Store(self.config);self.addCleanup(self.store.close)
        self.store.adopt_collected(self.job['id']);self.runtime=Dispatcher(self.store,models=object(),boards={})
        self.selection=self.request(self.job,self.original,'remaining-work',
            remaining='Same reservation peer-compatible staged remainder; preserve 17 artifacts, 7 targets, 5 UNSENT duties and current peers')
        self.store.consume_recovery_request(self.selection['id']);self.diagnosis=self.store.diagnosis_attempt(self.job['id'])
        self.choice={'profile':'.codex3','remaining':'Only peer-compatible staged construction in SAME job, fresh preimages; no old-stage replay or send',
                     'rationale':'Existing owner selection remains current; source/effects/Root/Branch/acceptance/retention duties stay independent'}
        collect(self.store,self.diagnosis,self.choice,binding_readback=LUNA,root_identity_observed=True)
        # Frozen Work928 supplied state; exact live interleaving was not traced.
        self.store.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?",(self.job['id'],))

    def receipt(self,**extra):
        return {'mode':'use-diagnosis','reason':'Actual same-role owner reaffirms captured remaining target and WHY are still current',
            'evidence':['Owned full qualified diagnosis/consumed selection read; no intervening purpose or cancellation'],
            'remaining':None,'diagnosis':self.diagnosis,'selection':self.selection['id'],**extra}

    def reaffirm(self,**extra):
        return self.store.request_recovery(self.job['id'],self.job['token'],self.original,self.owner,self.receipt(**extra))

    async def test_same_job_consumes_qualified_success_once_without_new_diagnosis_or_history_rewrite(self):
        original=self.store.attempt(self.original);diagnosis=self.store.attempt(self.diagnosis)
        selection=self.store.one('SELECT * FROM recovery_requests WHERE id=?',(self.selection['id'],))
        closure=self.store.job(self.job['id'])['collection_handoff']
        request=self.reaffirm();self.assertEqual(self.reaffirm(),request)
        result=self.store.consume_recovery_request(request['id']);new=result['successor']
        self.assertIsNone(self.store.consume_recovery_request(request['id']))
        self.assertEqual(self.store.attempt(self.original),original);self.assertEqual(self.store.attempt(self.diagnosis),diagnosis)
        self.assertIsNone(diagnosis['semantic']);self.assertEqual(diagnosis['exit'],0)
        self.assertEqual(self.store.one('SELECT * FROM recovery_requests WHERE id=?',(selection['id'],)),selection)
        self.assertEqual(self.store.job(self.job['id'])['collection_handoff'],closure)
        self.assertEqual(json.loads(closure)['original_collector'],self.original_collector)
        context=json.loads(self.store.attempt(new)['detail'])
        self.assertEqual(context['choice'],self.choice);self.assertEqual(context['diagnosis'],self.diagnosis)
        self.assertEqual(context['owner_remaining_selection']['id'],selection['id'])
        self.assertEqual(context['retained_diagnosis_request']['id'],request['id'])
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')),1)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),2)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='diagnosis'")),2)
        self.assertIsNone(self.store.attempt(new)['begin']);self.assertIsNone(self.store.reserve())
        self.assertIn(self.choice['remaining'],job_prompt(self.store,self.store.job(self.job['id'])))

    async def test_dispatcher_schedules_only_retained_successor_and_never_equivalent_Luna(self):
        request=self.reaffirm()
        self.runtime.execute=AsyncMock();self.runtime.recover=AsyncMock(side_effect=AssertionError('No second diagnosis'))
        self.runtime.reconcile_recovery_requests()
        if self.runtime.active:await __import__('asyncio').gather(*self.runtime.active)
        self.runtime.reconcile_recovery_requests()
        self.runtime.execute.assert_awaited_once();self.runtime.recover.assert_not_awaited()
        record=json.loads(self.store.one('SELECT result FROM recovery_requests WHERE id=?',(request['id'],))['result'])
        self.assertEqual(self.runtime.execute.await_args.args,(self.job['id'],record['successor']))

    async def test_foreign_collector_cannot_adopt_or_consume_reaffirmation(self):
        request=self.reaffirm();before=self.store.job(self.job['id'])
        other=Store(self.config);self.addCleanup(other.close)
        with self.assertRaisesRegex(Refusal,'original collector'):other.consume_recovery_request(request['id'])
        runtime=Dispatcher(other,models=object(),boards={});runtime.reconcile_recovery_requests()
        self.assertEqual(self.store.job(self.job['id']),before);self.assertFalse(runtime.active)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')

    async def test_newer_owner_choice_or_current_question_stays_binding(self):
        raw=self.store.attempt(self.diagnosis)['result']
        self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',
            (encode({**self.choice,'profile':'@owner','remaining':'Resolve a new current owner question'}),self.diagnosis))
        with self.assertRaisesRegex(Refusal,'actual owner disposition'):self.reaffirm()
        self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',(raw,self.diagnosis))
        latest=self.request(self.job,self.original,'redispose',reason='Actual newer owner choice, not the old captured purpose')
        self.store.consume_recovery_request(latest['id'])
        with self.assertRaisesRegex(Refusal,'newer owner choice'):self.reaffirm()

    async def test_defer_unknown_effect_source_hold_and_unrelated_hold_are_not_overridden(self):
        source=json.loads(self.store.job(self.job['id'])['members'])[0]['event']
        mutations=[('jobs','recovery_state','owner-deferred','exact held awaiting-disposition'),
                   ('jobs','effects','unknown','reconciled effects'),
                   ('jobs','hold_reason','Independent actual custodian hold','unrelated job hold')]
        for table,field,value,reason in mutations:
            previous=self.store.job(self.job['id'])[field]
            self.store.db.execute(f'UPDATE {table} SET {field}=? WHERE id=?',(value,self.job['id']))
            with self.assertRaisesRegex(Refusal,reason):self.reaffirm()
            self.store.db.execute(f'UPDATE {table} SET {field}=? WHERE id=?',(previous,self.job['id']))
        self.store.set_hold(source,'Independent original source hold')
        with self.assertRaises(Refusal):self.reaffirm()
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)

    async def test_changed_qualification_after_owner_request_prevents_consumption(self):
        request=self.reaffirm();original=self.store.job(self.job['id'])['active_attempt']
        self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',
            (encode({**self.choice,'rationale':'Changed since actual owner read; must not be silently accepted'}),self.diagnosis))
        with self.assertRaisesRegex(Refusal,'changed since owner'):self.store.consume_recovery_request(request['id'])
        self.assertEqual(self.store.job(self.job['id'])['active_attempt'],original)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')

    async def test_changed_original_source_after_reaffirmation_is_not_silently_used(self):
        request=self.reaffirm()
        original=json.loads(self.store.attempt(self.original)['result'])
        self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',
            (encode({**original,'summary':'Changed source after actual owner reaffirmation'}),self.original))
        with self.assertRaisesRegex(Refusal,'changed since owner'):self.store.consume_recovery_request(request['id'])
        self.assertEqual(self.store.job(self.job['id'])['active_attempt'],self.original)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)

    async def test_missing_identity_or_END_and_newer_pending_diagnosis_cannot_reuse_success(self):
        old=self.store.attempt(self.diagnosis)
        for field,value in [('ended',None),('exit',None),('capture','incomplete'),('binding',encode({**LUNA,'effort':'high'}))]:
            self.store.db.execute(f'UPDATE attempts SET {field}=? WHERE id=?',(value,self.diagnosis))
            with self.assertRaisesRegex(Refusal,'bound Luna LOW'):self.reaffirm()
            self.store.db.execute(f'UPDATE attempts SET {field}=? WHERE id=?',(old[field],self.diagnosis))
        pending=self.store._attempt('diagnosis',None,self.job['id'],LUNA,self.config['diagnosis']['profile'])
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',
            (encode({'prior_task_attempt':self.original,'owner_selection':self.selection['id']}),pending))
        with self.assertRaisesRegex(Refusal,'current exact explicit diagnosis'):self.reaffirm()
        self.store.db.execute("UPDATE jobs SET recovery_state='diagnosing' WHERE id=?",(self.job['id'],))
        self.runtime.advance_recovery(self.job['id'],self.failed)
        self.assertEqual(self.store.job(self.job['id'])['recovery_state'],'diagnosing')
        with self.assertRaisesRegex(Refusal,'newer current/pending'):
            with self.store.tx():self.store.retain_recovery_disposition(self.store.job(self.job['id']),self.store.attempt(self.failed),'Late old RPC failure')
