"""Decision10: supplied Q9 adverse choices and genuine control/proof distinctions.

Only isolated synthetic sources, grants, subprocesses and boards are operated.
No repeated real-model reproduction or production resource/source access.
"""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from support import config_at,enrolled,event,queued,collect,result,ident
import test_live_recovery as recovery_fixtures
import test_continuing as board_fixtures
from coordinator_runtime.contracts import Refusal,digest,classification
from coordinator_runtime.dispatcher import Dispatcher,recovery_prompt,classifier_prompt,job_prompt
from coordinator_runtime.store import Store
from coordinator_runtime.cli import main
from coordinator_runtime.appserver import AppServer
from coordinator_runtime import publication


BAD_CHOICE={'profile':'No replacement profile authorized',
    'remaining':'Obtain independent future-use selection and preserve canonical publication uncertainty.',
    'rationale':'External selection is unanswered; no blind original replay.'}


def selection(store,source,mode='route',task=None,package=None,**extra):
    return {'source_hash':digest(source),'mode':mode,'task':task,'package':package,
        'related_event':None,'related_job':None,'reason':'Actual same-role owner selected meaning and purpose',
        'evidence':['genuine synthetic source read and current responsibility check'],
        'remaining_obligations':[],**extra}


class RecoveryInputs(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=recovery_fixtures.OwnerRecovery.asyncSetUp
    held=recovery_fixtures.OwnerRecovery.held
    request=recovery_fixtures.OwnerRecovery.request

    def selected_diagnosis(self):
        job,attempt=self.held()
        self.store.reconcile_effects(job['id'],job['token'],self.owner,{'evidence':['collected effects only'],'unknown_effects':[]})
        request=self.request(job,attempt,'remaining-work')
        self.store.consume_recovery_request(request['id'])
        diagnosis=self.store.diagnosis_attempt(job['id'])
        return job,attempt,request,diagnosis

    async def test_authentic_remaining_why_and_evidence_reach_diagnosis_before_handoff(self):
        job,attempt,request,diag=self.selected_diagnosis()
        text=recovery_prompt(self.store,self.store.job(job['id']))
        data=json.loads(text.split('\n',1)[1])
        self.assertEqual(data['owner_remaining_selection']['receipt'],json.loads(request['receipt']))
        self.assertEqual(data['owner_remaining_selection']['actor'],self.owner)
        self.assertIn('independently admitted',text)
        self.assertIn('necessary external future-use choice',text)
        self.assertEqual(json.loads(self.store.attempt(diag)['detail'])['owner_selection'],request['id'])
        self.assertEqual(self.store.job(job['id'])['active_attempt'],attempt)

    async def test_supplied_invalid_profile_retains_original_and_public_next_request(self):
        job,attempt,request,diag=self.selected_diagnosis()
        original=self.store.attempt(attempt)
        collect(self.store,diag,copy.deepcopy(BAD_CHOICE))
        raw=self.store.attempt(diag)['result']
        self.runtime.advance_recovery(job['id'],diag)
        held=self.store.job(job['id'])
        self.assertEqual(held['active_attempt'],attempt);self.assertEqual(held['recovery_state'],'awaiting-disposition')
        self.assertEqual(self.store.attempt(diag)['result'],raw)
        self.assertEqual(self.store.attempt(attempt),original)
        question=self.store.one("SELECT * FROM outboxes WHERE kind='question'")
        self.assertEqual(question['recipient'],'Work')
        self.assertIn('No forced profile',json.loads(question['payload'])['next'])
        again=self.request(job,attempt,'remaining-work',reason='Authentic local reconciliation remains admitted; external choice stays open')
        self.assertEqual(again['state'],'pending')
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)

    async def test_public_request_can_reopen_old_collected_invalid_diagnosing_state(self):
        job,attempt,request,diag=self.selected_diagnosis()
        collect(self.store,diag,copy.deepcopy(BAD_CHOICE))
        # Candidate351's already-recorded bad state: no new red execution needed.
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'diagnosing')
        new=self.request(job,attempt,'remaining-work',reason='Reaffirm actual target/WHY with useful old reports and peer evidence')
        self.assertEqual(new['state'],'pending')
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'awaiting-disposition')
        self.assertTrue(self.store.one('SELECT * FROM recovery_dispositions WHERE diagnosis=?',(diag,)))

    async def test_failed_diagnosis_is_owned_next_step_and_unknown_diagnosis_cannot_be_released(self):
        job,attempt,request,diag=self.selected_diagnosis()
        collect(self.store,diag,None,code=1,error='bounded synthetic diagnosis failure',capture='incomplete')
        self.runtime.advance_recovery(job['id'],diag)
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'awaiting-disposition')
        self.request(job,attempt,'remaining-work',reason='Explicit next diagnosis after real failure evidence')
        self.store.db.execute("UPDATE jobs SET recovery_state='diagnosing' WHERE id=?",(job['id'],))
        self.store.db.execute('UPDATE attempts SET collected=NULL,ended=NULL WHERE id=?',(diag,))
        with self.assertRaisesRegex(Refusal,'existing recovery'):self.request(job,attempt)

    async def test_explicit_defer_remains_owned_without_automatic_diagnosis_or_processing(self):
        job,attempt=self.held()
        request=self.request(job,attempt,'defer',remaining=None)
        self.runtime.reconcile_recovery_requests()
        self.runtime.schedule_recovery();self.runtime.reconcile_completed()
        self.assertEqual(self.store.job(job['id'])['recovery_state'],'owner-deferred')
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertFalse(self.runtime.active)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    async def test_fresh_matching_diagnosis_can_select_new_work_but_never_replay_old_selection(self):
        job,attempt,request,diag=self.selected_diagnosis()
        collect(self.store,diag,{'profile':'.codex3','remaining':'Peer-safe reconciliation only','rationale':'Owner selected local target; external choice remains open'})
        new=self.store.handoff(job['id'],diag)
        self.assertNotEqual(new,attempt)
        detail=json.loads(self.store.attempt(new)['detail'])
        self.assertEqual(detail['owner_remaining_selection']['id'],request['id'])
        self.assertRaises(Refusal,self.store.handoff,job['id'],diag)

    async def test_late_diagnosis_disposition_cannot_hold_a_successor_reservation(self):
        job,attempt,request,diag=self.selected_diagnosis()
        collect(self.store,diag,{'profile':'.codex3','remaining':'Selected peer-safe work','rationale':'Original effects retained'})
        old=self.store.job(job['id']);new=self.store.handoff(job['id'],diag)
        with self.assertRaisesRegex(Refusal,'successor recovery'):
            with self.store.tx():self.store.retain_recovery_disposition(old,self.store.attempt(diag),'Late callback')
        self.assertEqual(self.store.job(job['id'])['active_attempt'],new)
        self.assertEqual(self.store.job(job['id'])['state'],'running')


class InputDecisions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='coordinator-input10-');self.addCleanup(self.temp.cleanup)
        self.config=config_at(self.temp.name);self.store=enrolled(self.config);self.addCleanup(self.store.close)
        self.runtime=Dispatcher(self.store,models=object(),boards={})

    def source(self,role='Branch',**extra):
        source={**event(self.config,ident(),role=role,task=f'{role.lower()}-proposer' if role!='QA' else 'qa-execution'),
                'kind':'board','body':{'text':'Actual supplied source, immutable'},**extra}
        self.store.ingest(source)
        return source

    def classify(self,source,task,package=None):
        attempt,view=self.store.claim_classification()
        self.assertEqual(view['id'],source['id'])
        collect(self.store,attempt,{'event_id':source['id'],'task':task,'package':package,'reason':'Synthetic actual meaning selection'})
        self.store.commit_classification(attempt)
        self.store.ack_state(source['id'],'internal')
        return attempt

    def resolve(self,source,receipt):
        return self.store.resolve_input(source['id'],self.config['roles'][source['role']]['owner'],receipt)

    def test_null_QA_release_and_status_are_controls_without_package_or_execution(self):
        source=self.source('QA',body={'text':'Old RELEASE already handled; not a request to run native bodies'})
        original=copy.deepcopy(self.store.event(source['id']))
        self.classify(source,'@control')
        queue=self.store.one('SELECT * FROM queue WHERE event=?',(source['id'],))
        self.assertEqual(queue['phase'],'control');self.assertIsNone(self.store.reserve())
        outbox=self.store.one('SELECT * FROM outboxes WHERE event=?',(source['id'],))
        self.assertEqual(outbox['recipient'],'QA');self.assertEqual(outbox['kind'],'question')
        self.assertEqual(self.store.event(source['id']),original)
        self.assertEqual(self.store.rows('SELECT * FROM admissions'),[])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    def test_three_true_nonQA_proof_tasks_retain_actual_Branch_route_and_full_meaning(self):
        source=self.source(body={'text':'THREE final-C proof tasks: DAG a0c2; F09 491b; F10 fe794; not QA qualification'})
        receipt=selection(self.store,source,task='branch-proposer')
        self.resolve(source,receipt);self.classify(source,'branch-proposer')
        job=self.store.reserve();self.assertEqual(job['task'],'branch-proposer');self.assertIsNone(job['package'])
        attempt=self.store.start_job(job['id'],job['token'])
        prompt=job_prompt(self.store,self.store.job(job['id']))
        self.assertIn(source['body']['text'],prompt)
        self.assertIn('input_resolutions',prompt)
        self.assertEqual(self.store.rows('SELECT * FROM admissions'),[])
        self.assertEqual(self.store.event(source['id']),source)

    def test_actual_QA_package_binding_needs_existing_admission_then_fresh_classification(self):
        source=self.source('QA',body={'text':'Real one-pair execution request; missing original binding'})
        receipt=selection(self.store,source,task='qa-execution',package='real-case')
        with self.assertRaisesRegex(Refusal,'existing admission'):self.resolve(source,receipt)
        self.store.admit('real-case',self.config['roles']['Branch']['owner'],{'actual':'synthetic admission'})
        self.resolve(source,receipt)
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])
        self.classify(source,'qa-execution','real-case')
        self.assertEqual(self.store.reserve()['package'],'real-case')
        self.assertIsNone(self.store.event(source['id'])['package'])

    def test_coalescing_old_null_to_existing_completed_pair_never_starts_another_executor(self):
        self.store.admit('one-pair',self.config['roles']['Branch']['owner'],{'actual':'one synthetic admission'})
        current=self.source('QA',package='one-pair');self.classify(current,'qa-execution','one-pair')
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token']);collect(self.store,attempt,result())
        self.store.finish_job(job['id'],job['token'])
        old=self.source('QA',body={'text':'Original unexecuted null pair request; same purpose as authentic later admission'})
        receipt=selection(self.store,old,mode='coalesce',package='one-pair',related_event=current['id'],related_job=job['id'])
        self.resolve(old,receipt);self.classify(old,'@coalesce','one-pair')
        self.store.complete_events()
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')),1)
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.event(old['id']),old)
        self.assertEqual(self.store.attempt(attempt)['semantic'],'DONE')

    def test_coalescence_of_ended_but_unsettled_pair_retains_consumer_hold(self):
        self.store.admit('one-pair',self.config['roles']['Branch']['owner'],{'actual':'one synthetic admission'})
        current=self.source('QA',package='one-pair');self.classify(current,'qa-execution','one-pair')
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token']);collect(self.store,attempt,result())
        self.store.hold_job(job['id'],'actual delivery still pending')
        old=self.source('QA');self.resolve(old,selection(self.store,old,mode='coalesce',package='one-pair',related_event=current['id'],related_job=job['id']))
        self.classify(old,'@coalesce','one-pair');self.store.complete_events()
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(old['id'],))['processed_at'])
        self.assertIsNone(self.store.reserve())

    def test_original_source_ACK_and_failure_results_survive_derived_resolution(self):
        source=self.source('QA')
        attempt,view=self.store.claim_classification()
        collect(self.store,attempt,{'event_id':source['id'],'task':'qa-execution','package':None,'reason':'Old invalid package route'})
        with self.assertRaises(Refusal):self.store.commit_classification(attempt)
        self.store.classification_failed(attempt,'old missing package failure')
        old_result=self.store.attempt(attempt)
        self.resolve(source,selection(self.store,source,mode='control'))
        self.classify(source,'@control')
        self.assertEqual(self.store.attempt(attempt),old_result)
        prior=self.store.input_resolution(source['id'])['prior']
        self.assertEqual(prior['error'],'old missing package failure')
        self.assertEqual(prior['ack'],'pending')
        self.assertEqual(self.store.event(source['id']),source)

    def test_remaining_obligations_keep_control_source_unprocessed_after_owner_record(self):
        source=self.source('QA')
        self.resolve(source,selection(self.store,source,mode='control',remaining_obligations=['Independent Root stop/publication remains unsettled']))
        self.classify(source,'@control');self.store.complete_events()
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])

    def test_already_ACKed_control_resolution_never_reacks_or_changes_source_hold(self):
        source=self.source('QA');self.classify(source,'@control')
        self.store.ack_state(source['id'],'done',{'actual':'original acknowledged receipt'})
        self.store.set_hold(source['id'],'independent source hold')
        old=self.store.one('SELECT ack,ack_receipt,hold,hash,payload FROM events WHERE id=?',(source['id'],))
        self.resolve(source,selection(self.store,source,mode='control'))
        attempt,view=self.store.claim_classification()
        collect(self.store,attempt,{'event_id':source['id'],'task':'@control','package':None,'reason':'Owner evidence records input control scope only'})
        self.store.commit_classification(attempt);self.store.complete_events()
        self.assertEqual(self.store.one('SELECT ack,ack_receipt,hold,hash,payload FROM events WHERE id=?',(source['id'],)),old)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])

    def test_late_previous_classifier_failure_cannot_overwrite_fresh_owner_selection(self):
        source=self.source('QA');attempt,view=self.store.claim_classification()
        collect(self.store,attempt,{'event_id':source['id'],'task':'qa-execution','package':None,'reason':'Original missing binding'})
        self.resolve(source,selection(self.store,source,mode='control'))
        with self.assertRaises(Refusal):self.store.commit_classification(attempt)
        self.store.classification_failed(attempt,'Late refused old classifier')
        self.assertEqual(self.store.one('SELECT state FROM events WHERE id=?',(source['id'],))['state'],'received')
        self.classify(source,'@control')

    def test_foreign_stale_reserved_and_unknown_classifier_selections_are_refused(self):
        source=self.source()
        receipt=selection(self.store,source,task='branch-proposer')
        with self.assertRaisesRegex(Refusal,'actual enrolled owner'):self.store.resolve_input(source['id'],ident(),receipt)
        with self.assertRaisesRegex(Refusal,'stale input'):self.resolve(source,{**receipt,'source_hash':'wrong'})
        attempt,view=self.store.claim_classification()
        with self.assertRaisesRegex(Refusal,'unknown/live classifier'):self.resolve(source,receipt)
        collect(self.store,attempt,{'event_id':source['id'],'task':'branch-proposer','package':None,'reason':'proof'})
        self.store.commit_classification(attempt);self.store.reserve()
        with self.assertRaisesRegex(Refusal,'reserved/executed'):self.resolve(source,receipt)

    def test_valid_enum_does_not_allow_guessed_package_cross_role_or_missing_coalescence_authority(self):
        source=self.source('QA')
        with self.assertRaises(Refusal):classification({'event_id':source['id'],'task':'@coalesce','package':None,'reason':'guess'},source,self.config)
        with self.assertRaises(Refusal):self.resolve(source,selection(self.store,source,task='branch-proposer'))
        with self.assertRaises(Refusal):self.resolve(source,selection(self.store,source,task='qa-execution',package='invented'))


class PeerSafeContinuation(unittest.IsolatedAsyncioTestCase):
    include_root=True
    asyncSetUp=recovery_fixtures.GroupedWriter.asyncSetUp
    run_writer=recovery_fixtures.GroupedWriter.run_writer

    async def test_selected_new_mapping_preserves_peer_and_external_duty_after_invalid_diagnosis(self):
        external=recovery_fixtures.handoff('bounded-execution','Root')
        answer={**result(),'unknowns':['Independent Root future-use selection remains unanswered'],
            'handoffs':[external],'no_handoff_reason':'',
            'completion':{'version':1,'local':'ready','failures':[],'tools':[],
                'unknowns':[{'index':0,'status':'deferred','owner':'Root','duty':'future-use-selection',
                    'reason':'Necessary settled handoff remains with actual synthetic Root'}]}}
        with patch.object(self.runtime,'try_finish'):
            job,old=await self.run_writer(answer_extra=answer,plan_extra={'completion_mode':'explicit'})
        old_stage=Path(publication.stages(self.store,old)[str(self.target)]).read_bytes()
        self.target.write_text('{"total":0,"peer":"latest genuine synthetic peer key"}')
        self.runtime.try_finish(job['id'])
        original=self.store.attempt(old)
        self.store.reconcile_effects(job['id'],job['token'],self.owner,{'evidence':['Synthetic original effects collected; peer conflict preserved'],'unknown_effects':[]})
        receipt={'mode':'remaining-work','reason':'Admitted peer-safe local reconciliation; Root future use remains independent',
            'evidence':['Exact original stages and peer change'],'remaining':'Reconcile total53 with fresh peer keys, preserve Root duty; never replay old stages'}
        request=self.store.request_recovery(job['id'],job['token'],old,self.owner,receipt)
        self.store.consume_recovery_request(request['id']);diag=self.store.diagnosis_attempt(job['id'])
        collect(self.store,diag,BAD_CHOICE);self.runtime.advance_recovery(job['id'],diag)
        request=self.store.request_recovery(job['id'],job['token'],old,self.owner,{**receipt,'reason':receipt['reason']+'; reaffirmed after invalid diagnosis'})
        self.store.consume_recovery_request(request['id']);diag=self.store.diagnosis_attempt(job['id'])
        self.assertIn('Root future use remains independent',recovery_prompt(self.store,self.store.job(job['id'])))
        collect(self.store,diag,{'profile':'.codex3','remaining':receipt['remaining'],'rationale':'Local target admitted; no external duty waiver'})
        successor=self.store.handoff(job['id'],diag)
        plan=Path(self.temp.name)/'fresh-peer-writer.json'
        plan.write_text(json.dumps({'result':{**answer,'artifacts':[str(self.target)]},'target':str(self.target),
            'target_contents':{'total':53,'peer':'latest genuine synthetic peer key'},'tool_metadata':{'exitCode':0},
            'completion_mode':'explicit','storage_config':{'history':{'persistence':'none'},'feedback':{'enabled':False},'features':{'shell_snapshot':False}}}))
        self.runtime.models=AppServer(self.config,[sys.executable,str(Path(__file__).with_name('fixture_appserver.py')),str(plan)])
        await self.runtime.execute(job['id'],successor)
        self.assertEqual(json.loads(self.target.read_text()),{'total':53,'peer':'latest genuine synthetic peer key'})
        before=json.loads(self.store.one('SELECT before_files FROM routine_runs WHERE attempt=?',(successor,))['before_files'])
        old_before=json.loads(self.store.one('SELECT before_files FROM routine_runs WHERE attempt=?',(old,))['before_files'])
        self.assertNotEqual(before[str(self.target)]['sha256'],old_before[str(self.target)]['sha256'])
        self.assertEqual(Path(publication.stages(self.store,old)[str(self.target)]).read_bytes(),old_stage)
        self.assertEqual(self.store.attempt(old),original)
        self.assertEqual(self.store.job(job['id'])['effects'],'reconciled')
        self.assertEqual(self.store.job(job['id'])['state'],'awaiting-delivery')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(json.loads(job['members'])[0]['event'],))['processed_at'])
        self.assertEqual(json.loads(self.store.attempt(successor)['result'])['unknowns'],answer['unknowns'])


class NotificationAndReceive(unittest.TestCase):
    setUp=board_fixtures.Continuing.setUp

    def test_unresolved_fixed_plan_has_actual_owner_question_and_fresh_lawful_next_classification(self):
        queued(self.store,event(self.config));job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token'])
        answer=self.work_answer();collect(self.store,attempt,answer)
        self.store.finish_job(job['id'],job['token'])
        response=self.store.event(self.store.job(job['id'])['response'])
        classifier,view=self.store.claim_classification()
        collect(self.store,classifier,{'event_id':response['id'],'task':'@unresolved','package':None,'reason':'Cannot interpret duty without actual owner context'})
        self.store.commit_classification(classifier)
        original=self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Root'",(job['id'],))
        self.assertEqual(original['state'],'classification-pending')
        question=self.store.one("SELECT * FROM outboxes WHERE event=? AND job IS NULL",(response['id'],))
        self.assertEqual(question['recipient'],'Work')
        self.runtime.pump_deliveries()
        self.assertIsNotNone(self.store.one('SELECT board_receipt FROM outboxes WHERE id=?',(question['id'],))['board_receipt'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(question['id'],))['processed_at'])
        decision=selection(self.store,response,task='@delivery',reason='Full immutable plan is truthful notification; original execution/effect/consumer duties remain pending')
        self.store.resolve_input(response['id'],self.config['roles']['Work']['owner'],decision)
        classifier,view=self.store.claim_classification()
        self.assertEqual(view['owner_resolution']['receipt'],decision)
        collect(self.store,classifier,{'event_id':response['id'],'task':'@delivery','package':None,'reason':'Actual owner clarified notice meaning; no acceptance'})
        self.store.commit_classification(classifier);self.runtime.pump_deliveries()
        posted=self.store.one('SELECT * FROM outboxes WHERE id=?',(original['id'],))
        self.assertEqual(posted['state'],'posted');self.assertIsNone(posted['processed_at'])
        self.assertEqual(json.loads(posted['payload'])['source_result'],answer)

    work_answer=board_fixtures.Continuing.work_answer

    def test_additional_diagnosis_notice_cannot_rewrite_previous_fixed_plan(self):
        queued(self.store,event(self.config));job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token'])
        collect(self.store,attempt,self.work_answer());self.store.finish_job(job['id'],job['token'])
        first=self.store.event(self.store.job(job['id'])['response']);old=copy.deepcopy(first)
        with self.store.tx():
            key=self.store._outbox('Work','Work','question',{'reason':'Later independent diagnosis duty'},job=job['id'])
            second_id=self.store.gate_result_delivery(self.store.job(job['id']),self.store.attempt(attempt),{'reason':'later diagnostic notification'})
        self.assertNotEqual(first['id'],second_id)
        self.assertEqual(self.store.event(first['id']),old)
        self.assertEqual([x['id'] for x in self.store.event(second_id)['delivery_plan']],[key])

    def test_owner_control_commands_use_genuine_actor_and_do_not_claim_native_wake(self):
        source={**event(self.config,'owner-input',role='Branch',task='branch-proposer'),'kind':'board'}
        self.store.ingest(source)
        receipt=selection(self.store,source,mode='control')
        config_path=Path(self.temp.name)/'owner-config.json';config_path.write_text(json.dumps(self.config))
        receipt_path=Path(self.temp.name)/'input-owner.json';receipt_path.write_text(json.dumps(receipt))
        args=['--config',str(config_path),'resolve-input',source['id'],'--receipt',str(receipt_path)]
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.root}),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(args),2)
        owner=self.config['roles']['Branch']['owner']
        with patch.dict(os.environ,{'CODEX_SESSION_ID':owner}),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(args),0)
        shown=self.store.owner_controls('Branch')
        self.assertIn('no native wake',shown['availability'])
        self.assertEqual(shown['inputs'][0]['id'],source['id'])
        self.assertEqual(self.store.event(source['id']),source)

    def test_QA_unknown_result_labels_notify_without_fabricating_accepted_qualification(self):
        task=self.config['tasks']['qa-execution'];task['allowed_handoffs']=['Branch','Work']
        job={'id':'synthetic-ended-pair','role':'QA','package':'one-actual-pair','members':'[]'}
        attempt={'id':'synthetic-collected-pair','session':ident()}
        answer={**result(category='qualification'),'unknowns':['Root publication, warning body UNKNOWN, later source not admitted']}
        original={'recipient':'Branch','kind':'qa-execution-result','text':'One actual paired case PASS; no new native effects or acceptance',
                  'ref':'exact original report','required':'settled'}
        with self.store.tx():self.store._task_handoff(job,attempt,task,answer,original,0)
        row=self.store.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        self.assertEqual(row['kind'],'question');self.assertTrue(json.loads(row['payload'])['notification_only'])
        self.assertEqual(json.loads(row['payload'])['original_handoff'],original)
        self.assertEqual(json.loads(row['payload'])['source_result']['unknowns'],answer['unknowns'])
        self.assertIsNone(row['processed_at']);self.assertEqual(self.store.rows('SELECT * FROM admissions'),[])
