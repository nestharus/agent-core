"""Q6-01 representation/identity consequence; fresh synthetic contexts only."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_writer_custody as fixtures
from coordinator_runtime import readiness
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.contracts import Refusal


def duty(owner, name, status='deferred'):
    return {'status':status,'owner':owner,'duty':name,'reason':'Explicit remaining responsibility, not producer acceptance.'}


def proof():
    return {'version':1,'local':'ready','failures':[], 'unknowns':[
        {'index':0,**duty('Root','consume the required external report')},
        {'index':1,'duties':[duty('controller',v) for v in sorted(readiness.CONTROLLER_DUTIES)]},
        {'index':2,'duties':[duty('outside-workflow',v,'boundary') for v in ['review','acceptance']]}], 'tools':[]}


def original():
    # Analogous grammar, never an edited/replayed original qualification result.
    p=proof()
    p['unknowns'][1]={'index':1,**duty('controller','custody/collection/delivery/publication/effect reconciliation')}
    p['unknowns'][2]={'index':2,**duty('outside-workflow','review and acceptance outside this local result','boundary')}
    p['tools']=[{'id':'visible-success-label','status':'resolved','reason':'Producer visible check exited zero.'}]
    return {'semantic':'DONE','failures':[], 'unknowns':[
        {'owner':'Root','meaning':'External consumption still pending.'},
        'Expected later controller custody, collection, delivery and publication.',
        'Review and acceptance remain unclaimed.'], 'completion':p,
        'handoffs':[{'recipient':'Root','kind':'question','text':'Consume this required external handoff.',
                     'ref':'fresh synthetic responsibility','required':'settled'}]}


def command(identity='protocol-command', exit_code=0):
    return {'id':identity,'type':'commandExecution','exit_code':exit_code,
            'completed_notification':True,'status':'completed' if exit_code==0 else 'failed'}


class ContractGrammar(unittest.TestCase):
    def test_each_actual_representation_mismatch_requires_clarification_independently(self):
        bad=original();before=copy.deepcopy(bad)
        self.assertTrue(readiness.needs_clarification(bad,[command()]))
        self.assertEqual(bad,before)
        for key,index in [('unknowns',1),('unknowns',2),('tools',0)]:
            with self.subTest(key=key,index=index):
                answer={**bad,'completion':proof()}
                answer['completion'][key][index:index+1]=[before['completion'][key][index]]
                self.assertTrue(readiness.needs_clarification(answer,[command()]))
        repaired={**bad,'completion':proof()}
        self.assertFalse(readiness.needs_clarification(repaired,[command()]))

    def test_visible_success_claims_are_separate_and_cannot_resolve_actual_adversity(self):
        answer={**original(),'completion':proof()}
        claim={'namespace':'producer-visible','label':'visible-success-label','status':'reported-completed',
               'exit_code':0,'reason':'Uncorrelated producer statement retained.'}
        answer['completion']['reported_commands']=[claim]
        self.assertFalse(readiness.needs_clarification(answer,[command()]))
        self.assertTrue(readiness.needs_clarification(answer,[command(),command('actual-nonzero',1)]))
        answer['completion']['tools']=[{'id':'visible-success-label','status':'resolved','reason':'Not a protocol ID.',
            'evidence':[{'path':'/own/report','sha256':'0'*64}],'verification_items':['visible-success-label']}]
        issues=readiness.inspect(answer,[command(),command('actual-nonzero',1)])[2]
        self.assertTrue(any('ONLY' in issue for issue in issues));self.assertTrue(any('verification' in issue for issue in issues))

    def test_actual_failure_evidence_does_not_infer_resolution_from_any_later_zero(self):
        answer={**original(),'completion':proof()}
        answer['completion']['tools']=[{'id':'actual-nonzero','status':'resolved','reason':'Producer claim needs exact evidence.',
            'evidence':[{'path':'/own/report','sha256':'0'*64}],'verification_items':['protocol-command']}]
        def missing(ref):raise Refusal('resolution bytes unavailable')
        self.assertTrue(readiness.needs_clarification(answer,[command(),command('actual-nonzero',1)],check_ref=missing))

    def test_real_local_unknown_is_held_not_reclassified_as_a_later_duty(self):
        answer={**original(),'completion':proof()}
        answer['completion']['unknowns'][1]={'index':1,**duty('producer','failed staged invariant','unresolved')}
        self.assertTrue(readiness.needs_clarification(answer,[]))
        answer['completion']['local']='blocked'
        self.assertFalse(readiness.needs_clarification(answer,[]))  # Valid blocked contract never becomes ready.

    def test_external_owner_requires_selected_settled_handoff_and_typed_group(self):
        answer={**original(),'completion':proof()}
        for handoffs in [None,[],[{'recipient':'Root','required':'posted'}]]:
            with self.subTest(handoffs=handoffs):
                answer['handoffs']=handoffs
                self.assertTrue(readiness.needs_clarification(answer,[],task={'allowed_handoffs':['Root']}))
        answer['handoffs']=original()['handoffs']
        self.assertTrue(readiness.needs_clarification(answer,[],task={'allowed_handoffs':[]}))
        answer['completion']['unknowns'][1]['duties']=[duty('controller','publication')]*2
        self.assertTrue(readiness.needs_clarification(answer,[]))


class OwnedClarification(unittest.IsolatedAsyncioTestCase):
    include_root=True
    asyncSetUp=fixtures.WriterCustody.asyncSetUp
    run_writer=fixtures.WriterCustody.run_writer
    settle_routine=fixtures.WriterCustody.settle_routine

    def plan(self,final=None):
        write_record=Path(self.temp.name)/'stage-writes.txt'
        fixed=proof() if final is None else final
        fixed['reported_commands']=[{'namespace':'producer-visible','label':'visible-success-label',
            'status':'reported-completed','exit_code':0,'reason':'Retained producer label, no protocol/OS correlation.'}]
        return {'completion_mode':'representation-repair','clarified_completion':fixed,
                'write_once':True,'stage_write_record':str(write_record)}

    async def test_one_same_owned_clarification_allows_local_progress_without_settling_external_work(self):
        first=original();plan=self.plan()
        job,attempt=await self.run_writer(answer_extra=first,plan_extra=plan)
        row=self.store.attempt(attempt);detail=json.loads(row['detail']);answer=json.loads(row['result'])
        self.assertEqual(row['exit'],0);self.assertIsNotNone(row['collected'])
        self.assertTrue(detail['resume_attempted']);self.assertTrue(detail['readiness_clarification'])
        self.assertGreaterEqual(len(detail['readiness_issues']),3)
        self.assertEqual(detail['prior_turn_result']['completion'],first['completion'])
        self.assertEqual(answer['unknowns'],first['unknowns'])
        self.assertEqual(len(detail['tool_completion']['items']),2)
        self.assertEqual(len(Path(plan['stage_write_record']).read_text().splitlines()),1)
        self.assertEqual(json.loads(self.target.read_text())['total'],12)
        receipt=json.loads(self.store.job(job['id'])['effect_receipt'])['local_readiness']
        self.assertEqual(len(receipt['subsequent_duties']),7)
        self.assertEqual(receipt['clarification_origin']['completion'],first['completion'])
        self.assertEqual(receipt['reported_commands'][0]['label'],'visible-success-label')
        self.assertEqual(receipt['tool_dispositions'],[])
        await self.settle_routine(job)
        self.assertEqual(self.store.job(job['id'])['state'],'awaiting-delivery')
        source=json.loads(job['members'])[0]['event']
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source,))['processed_at'])
        pending=self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Root'",(job['id'],))
        self.assertNotEqual(pending['state'],'settled')
        next_job,next_attempt=await self.run_writer(plan_extra={'target_contents':{'total':19}})
        self.assertNotEqual(attempt,next_attempt)
        self.assertEqual(self.store.job(next_job['id'])['effects'],'reconciled')
        self.assertEqual(json.loads(self.target.read_text())['total'],19)
        self.assertNotEqual(self.store.job(job['id'])['state'],'closed')

    async def test_still_ambiguous_after_one_clarification_stays_held_and_causally_reported(self):
        first=original()
        job,attempt=await self.run_writer(answer_extra=first,plan_extra=self.plan(copy.deepcopy(first['completion'])))
        row=self.store.attempt(attempt);detail=json.loads(row['detail'])
        self.assertEqual(len(detail['tool_completion']['items']),2)
        self.assertEqual(json.loads(row['result'])['unknowns'],first['unknowns'])
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertIsNotNone(self.store.job(job['id'])['response'])
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='effect-request'"))

    async def test_live_declared_byte_check_selects_one_faithful_correction_before_collection(self):
        history='Retained original local verifier mismatch and its claimed repair.'
        job,attempt=await self.run_writer(answer_extra={'failures':[history]},
            plan_extra={'completion_mode':'live-evidence-repair','write_once':True})
        detail=json.loads(self.store.attempt(attempt)['detail'])
        self.assertIn('resolution artifact hash is not current exact own bytes',detail['readiness_issues'])
        self.assertEqual(detail['prior_turn_result']['failures'],[history])
        self.assertEqual(json.loads(self.store.attempt(attempt)['result'])['failures'],[history])
        self.assertEqual(len(detail['tool_completion']['items']),2)
        self.assertEqual(self.store.job(job['id'])['effects'],'reconciled')

    async def test_live_reference_scope_and_opaque_exclusion_precede_all_path_metadata(self):
        attempt='synthetic-preview-only'
        root=self.store.home/'artifacts'/attempt
        for path,exclusions,expected in [(root/'opaque-evidence',[str(root/'opaque-evidence')],'excluded before metadata'),
                                         (Path(self.temp.name)/'outside-attempt',[],'belong to this producer attempt')]:
            with self.subTest(path=path):
                self.config['artifact_exclusions']=exclusions
                answer={'semantic':'DONE','failures':['Claim needs an allowed byte witness'],'unknowns':[],
                    'artifacts':[str(path)],'completion':{'version':1,'local':'ready','unknowns':[],'tools':[],
                    'failures':[{'index':0,'status':'resolved','evidence':[{'path':str(path),'sha256':'0'*64}],
                                 'verification_items':['protocol-command']}]}}
                with patch('coordinator_runtime.custody.safe_path',side_effect=AssertionError('metadata reached')):
                    issues=readiness.live_issues(self.store,attempt,answer,[command()],self.config['tasks']['work-integrator'])
                self.assertTrue(any(expected in issue for issue in issues))

    async def fenced(self,fence):
        original_continue=AppServer.continue_idle
        async def guarded(adapter,*args,**kwargs):
            if fence=='revoked':
                with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):self.board.revoke(self.store.enrollment('Work')['grant_id'])
            return await original_continue(adapter,*args,**kwargs)
        plan=self.plan()
        if fence=='busy':plan['read_status']='active'
        with patch.object(AppServer,'continue_idle',guarded):job,attempt=await self.run_writer(answer_extra=original(),plan_extra=plan)
        detail=json.loads(self.store.attempt(attempt)['detail'])
        self.assertEqual(len(detail['tool_completion']['items']),1)
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertNotEqual(self.store.job(job['id'])['effects'],'reconciled')

    async def test_actual_idle_readback_still_required(self):await self.fenced('busy')

    async def test_current_actor_revocation_still_fences_clarification(self):await self.fenced('revoked')
