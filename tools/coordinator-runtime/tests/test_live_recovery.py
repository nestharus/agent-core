"""Decision9: observed group/label shapes and owner-bound recovery, synthetic effects.

The real safe controls are exercised separately by the task witness script. These
portable fixtures use their shapes, never open production paths or replay duties.
"""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, queued, result, collect
import test_writer_custody as writers
import test_corrections as processes
from coordinator_runtime import custody
from coordinator_runtime.contracts import (Refusal, artifact_paths, task_result,
    task_result_issues, handoff_delivery_kind, ident)
from coordinator_runtime.dispatcher import Dispatcher, RESULT_SCHEMA, job_prompt
from coordinator_runtime.store import Store
from coordinator_runtime.cli import main


def handoff(kind='catalog-proposal',recipient='Work'):
    return {'recipient':recipient,'kind':kind,'text':'Preserve original failures, accepted CREATEs and owners; no replay.',
            'ref':'owned synthetic report#bounded-target','required':'settled'}


class NestedContract(unittest.TestCase):
    def test_observed_groups_and_arbitrary_labels_preserve_meaning(self):
        answer={**result(),'artifacts':[{'kind':'canonical-preconditions','common':{'before_only':True},
            'files':[{'path':'/synthetic/report','sha256':'f'*64,'read_extent':'bounded selected fields'}]}],
            'handoffs':[handoff(k) for k in ['bounded-execution','integration-and-follow-through',
                                          'custody-and-downstream-dependency','catalog-proposal']]}
        before=copy.deepcopy(answer)
        self.assertIs(task_result(answer),answer)
        self.assertEqual(artifact_paths(answer['artifacts']),['/synthetic/report'])
        self.assertEqual([handoff_delivery_kind(h) for h in answer['handoffs']],['question']*4)
        self.assertEqual(answer,before)

    def test_malformed_item_clarification_conserves_full_original_and_valid_prefix(self):
        good={'path':'/synthetic/report','meaning':'must remain exact'}
        bad={'kind':'source','meaning':'Missing path cannot be guessed'}
        original={**result(),'artifacts':[good,bad],'handoffs':[{**handoff(),'required':'acknowledged'}]}
        self.assertTrue(any('artifact leaf' in i for i in task_result_issues(original)))
        final={**result(),'artifacts':[good], 'handoffs':[handoff()],
            'findings':[*original['findings'],{'kind':'outer-contract-original','fields':{
                'artifacts':original['artifacts'],'handoffs':original['handoffs']}}]}
        self.assertIs(task_result(final,original),final)
        with self.assertRaisesRegex(Refusal,'must conserve original'):
            task_result({**final,'findings':original['findings']},original)
        with self.assertRaisesRegex(Refusal,'rewrote original artifacts'):
            task_result({**final,'artifacts':[]},original)

    def test_relative_ambiguous_empty_and_unbounded_groups_are_repairable_errors(self):
        for artifacts in [[{'files':[]}],[{'files':['/x'],'path':'/ambiguous'}],['relative'],
                          [{'files':['/x']*65}],[{'files':'not a list'}]]:
            with self.subTest(artifacts=artifacts):
                self.assertTrue(task_result_issues({**result(),'artifacts':artifacts}))


class OwnedNestedWire(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=processes.ProcessCorrections.asyncSetUp
    adapter=processes.ProcessCorrections.adapter
    task=processes.ProcessCorrections.task

    async def test_missing_leaf_path_gets_one_owned_idle_clarification_with_original_data(self):
        _,attempt=self.task()
        bad={'kind':'input-group','files':[{'meaning':'genuinely unavailable source path'}]}
        first={**result(),'artifacts':[bad]}
        final={**result('PARTIAL','blocker'),'artifacts':[],
               'findings':[*first['findings'],{'kind':'outer-contract-original','fields':{'artifacts':[bad]}}]}
        outcome=await self.adapter({'result':first,'second_result':final,'tool_metadata':{'exitCode':0}}).run(
            self.store,attempt,'synthetic missing-path task',self.config['tasks']['work-integrator'],RESULT_SCHEMA)
        self.assertEqual(outcome['exit'],0);self.assertIsNone(outcome['error'])
        self.assertEqual(outcome['result'],final)
        self.assertEqual(outcome['detail']['prior_turn_result'],first)
        self.assertEqual(len(outcome['detail']['tool_completion']['items']),2)


class GroupedWriter(unittest.IsolatedAsyncioTestCase):
    include_root=True
    asyncSetUp=writers.WriterCustody.asyncSetUp
    run_writer=writers.WriterCustody.run_writer
    settle_routine=writers.WriterCustody.settle_routine

    async def test_grouped_writer_keeps_external_question_while_next_batch_progresses(self):
        group={'kind':'staged-catalog','common':{'meaning':'current owned output'},'files':[str(self.target)]}
        job,attempt=await self.run_writer(artifacts=[group],answer_extra={'handoffs':[handoff('bounded-execution','Root')]})
        row=self.store.attempt(attempt)
        self.assertEqual(row['exit'],0);self.assertIsNone(row['error'])
        self.assertNotIn('prior_turn_result',json.loads(row['detail']))
        self.assertEqual(json.loads(row['result'])['artifacts'],[group])
        outgoing=self.store.one("SELECT * FROM outboxes WHERE recipient='Root'")
        self.assertEqual(outgoing['kind'],'question')
        self.assertEqual(json.loads(outgoing['payload'])['original_handoff'],handoff('bounded-execution','Root'))
        await self.settle_routine(job)
        self.assertEqual(self.store.job(job['id'])['state'],'awaiting-delivery')
        next_job,_=await self.run_writer(plan_extra={'target_contents':{'total':29}})
        self.assertNotEqual(job['id'],next_job['id'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',
            (json.loads(job['members'])[0]['event'],))['processed_at'])

    async def test_redisposition_keeps_canonical_conflict_independent_of_labels(self):
        # Stop immediately before publication, then install a genuine synthetic peer update.
        with patch.object(self.runtime,'try_finish'):
            job,attempt=await self.run_writer(answer_extra={'handoffs':[handoff('bounded-execution','Root')]})
        self.target.write_text('{"total":77,"peer":"must survive"}')
        self.runtime.try_finish(job['id'])
        self.assertIn('canonical bytes changed',self.store.job(job['id'])['hold_reason'])
        original=self.store.attempt(attempt)['result']
        receipt={'mode':'redispose','reason':'Retry only representation/disposition after contract update',
                 'evidence':['synthetic original collected0; peer update still held'],'remaining':None}
        config_path=Path(self.temp.name)/'request-config.json';config_path.write_text(json.dumps(self.config))
        receipt_path=Path(self.temp.name)/'owner-request.json';receipt_path.write_text(json.dumps(receipt))
        argv=['--config',str(config_path),'request-recovery',job['id'],'--token',job['token'],
              '--attempt',attempt,'--receipt',str(receipt_path)]
        with patch.dict(os.environ,{'CODEX_SESSION_ID':ident()}),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv),2)
        self.assertEqual(self.store.rows('SELECT * FROM recovery_requests'),[])
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv),0)
        self.runtime.reconcile_recovery_requests()
        self.assertEqual(self.store.attempt(attempt)['result'],original)
        self.assertEqual(json.loads(self.target.read_text())['total'],77)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        self.assertEqual(self.store.rows('SELECT * FROM canonical_backups'),[])
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    async def test_owner_effect_receipt_cannot_waive_peer_conflict_or_unfinished_publication(self):
        with patch.object(self.runtime,'try_finish'):
            job,attempt=await self.run_writer()
        self.target.write_text('{"total":88,"peer":"conserved"}')
        self.runtime.try_finish(job['id'])
        self.store.reconcile_effects(job['id'],job['token'],self.owner,{
            'evidence':['Synthetic actual owner reconciled effects, but peer bytes differ'],'unknown_effects':[]})
        self.runtime.try_finish(job['id'])
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertIn('publication remains incomplete',self.store.job(job['id'])['hold_reason'])
        self.assertEqual(json.loads(self.target.read_text())['total'],88)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])


class OwnerRecovery(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='coordinator-recovery9-');self.addCleanup(self.temp.cleanup)
        self.config=config_at(self.temp.name)
        self.store=enrolled(self.config);self.addCleanup(self.store.close)
        self.runtime=Dispatcher(self.store,models=object(),boards={})
        self.owner=self.config['roles']['Work']['owner']

    def held(self,answer=None,**outcome):
        queued(self.store,event(self.config,ident()))
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token'])
        collect(self.store,attempt,answer or result(),**outcome)
        self.store.hold_job(job['id'],'synthetic disposition error')
        self.store.record_operational_error(job['id'],{'error':'synthetic disposition error'},'Work','task-disposition-error')
        return job,attempt

    def request(self,job,attempt,mode='redispose',actor=None,**extra):
        return self.store.request_recovery(job['id'],job['token'],attempt,actor or self.owner,{
            'mode':mode,'reason':'Exact current original needs bounded disposition','evidence':['synthetic actual collected state'],
            'remaining':None if mode=='redispose' else 'Reconcile original stages with current peer bytes; preserve accepted effects.',**extra})

    async def test_collected_DONE_disposition_failure_gets_one_diagnosis_without_replay(self):
        job,attempt=self.held()
        async def fake(*args):
            return {'exit':0,'capture':'complete','cleanup':'done','error':None,
                'result':{'profile':'.codex3','remaining':'Disposition only','rationale':'Retain completed work'},'detail':{}}
        self.runtime.run_model=fake
        self.runtime.schedule_recovery()
        await __import__('asyncio').gather(*self.runtime.active)
        row=self.store.job(job['id'])
        self.assertEqual(row['active_attempt'],attempt)
        self.assertEqual(row['recovery_state'],'awaiting-disposition')
        self.assertEqual(row['recovery_count'],1)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)
        self.runtime.schedule_recovery();self.assertFalse(self.runtime.active)
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='question'"))

    async def test_actual_owner_redisposes_old_group_gap_without_rewriting_original_results(self):
        source=Path(self.temp.name)/'report';source.write_text('accepted effects remain history')
        answer={**result(),'artifacts':[{'kind':'substantive-inputs','files':[str(source)]}]}
        job,attempt=self.held(answer)
        self.store.capture_gap(attempt,'old parser required group.path')
        original=dict(self.store.one('SELECT * FROM results WHERE attempt=?',(attempt,)))
        request=self.request(job,attempt)
        self.runtime.reconcile_recovery_requests()
        current=self.store.attempt(attempt)
        self.assertEqual(current['capture'],'complete');self.assertIsNone(current['error'])
        self.assertEqual(json.loads(current['result']),answer)
        self.assertEqual(self.store.one('SELECT * FROM results WHERE attempt=?',(attempt,)),original)
        self.assertIn('artifact_recheck',json.loads(current['detail']))
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'consumed')

    async def test_redispose_cannot_upgrade_incomplete_stream_or_unknown_semantics(self):
        job,attempt=self.held(result('UNKNOWN'),capture='incomplete',error='missing matching turn completion')
        self.request(job,attempt);self.runtime.reconcile_recovery_requests()
        self.assertEqual(self.store.attempt(attempt)['capture'],'incomplete')
        self.assertEqual(self.store.attempt(attempt)['semantic'],'UNKNOWN')
        self.assertEqual(self.store.job(job['id'])['state'],'held')

    async def test_owner_remaining_work_requires_effects_then_fresh_diagnosis_and_current_fences(self):
        job,attempt=self.held()
        with self.assertRaisesRegex(Refusal,'reconciled effects'):self.request(job,attempt,'remaining-work')
        self.store.reconcile_effects(job['id'],job['token'],self.owner,{'evidence':['synthetic no unresolved effects'],'unknown_effects':[]})
        request=self.request(job,attempt,'remaining-work')
        selected=self.store.consume_recovery_request(request['id'])
        self.assertEqual(selected['receipt']['mode'],'remaining-work')
        diag=self.store.diagnosis_attempt(job['id'])
        collect(self.store,diag,{'profile':'.codex3','remaining':'Current peer-safe reconciliation only','rationale':'Original effects not replayed'})
        successor=self.store.handoff(job['id'],diag)
        detail=json.loads(self.store.attempt(successor)['detail'])
        self.assertEqual(detail['prior_result'],self.store.attempt(attempt)['result'])
        self.assertEqual(detail['owner_remaining_selection']['id'],request['id'])
        prompt=job_prompt(self.store,self.store.job(job['id']))
        self.assertIn('Never copy an old stage over peer updates',prompt)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),2)

    async def test_foreign_owner_stale_attempt_and_unknown_original_are_refused(self):
        job,attempt=self.held()
        with self.assertRaisesRegex(Refusal,'actual enrolled'):self.request(job,attempt,actor=ident())
        self.store.db.execute('UPDATE attempts SET ended=NULL,collected=NULL WHERE id=?',(attempt,))
        with self.assertRaisesRegex(Refusal,'unknown/live'):self.request(job,attempt)

    async def test_request_does_not_transfer_foreign_collector_or_override_pending_recovery(self):
        job,attempt=self.held()
        request=self.request(job,attempt)
        other=Store(self.config);self.addCleanup(other.close)
        with self.assertRaisesRegex(Refusal,'original collector'):other.consume_recovery_request(request['id'])
        self.assertIsNone(self.store.claim_recovery(job['id']))
        self.store.consume_recovery_request(request['id'])
        self.store.claim_recovery(job['id'])
        with self.assertRaisesRegex(Refusal,'existing recovery'):self.request(job,attempt)

    async def test_group_source_hash_change_and_privacy_exclusion_still_hold(self):
        source=Path(self.temp.name)/'report';source.write_text('peer changed this report')
        answer={**result(),'artifacts':[{'kind':'sources','files':[{'path':str(source),'sha256':'0'*64}]}]}
        job,attempt=self.held(answer)
        with self.assertRaisesRegex(Refusal,'hash/bytes differ'):
            custody.inventory(self.store,attempt,answer,self.config['tasks']['work-integrator'])
        self.config['artifact_exclusions']=[str(source)]
        with patch('coordinator_runtime.custody.read_file',side_effect=AssertionError('must exclude before read')):
            with self.assertRaisesRegex(Refusal,'excluded before metadata'):
                custody.inventory(self.store,attempt,answer,self.config['tasks']['work-integrator'])

    async def test_restart_uses_only_existing_proved_closure_handoff_not_process_adoption(self):
        job,attempt=self.held()
        self.request(job,attempt)
        original_collector=self.store.attempt(attempt)['controller']
        other=Store(self.config);self.addCleanup(other.close)
        runtime=Dispatcher(other,models=object(),boards={})
        runtime.reconcile_recovery_requests()
        self.assertEqual(other.attempt(attempt)['controller'],original_collector)
        handoff=json.loads(other.job(job['id'])['collection_handoff'])
        self.assertEqual(handoff['original_attempt'],attempt)
        self.assertEqual(handoff['original_collector'],original_collector)

    async def test_unrelated_source_holds_and_request_budget_remain_binding(self):
        job,attempt=self.held()
        self.store.reconcile_effects(job['id'],job['token'],self.owner,{'evidence':['synthetic reconciled'],'unknown_effects':[]})
        source=json.loads(job['members'])[0]['event'];self.store.set_hold(source,'independent source hold')
        with self.assertRaisesRegex(Refusal,'source/legacy holds'):self.request(job,attempt,'remaining-work')
        self.store.set_hold(source,None)
        self.store.hold_job(job['id'],'independent readiness hold')
        with self.assertRaisesRegex(Refusal,'unrelated job hold'):self.request(job,attempt,'remaining-work')
        self.store.hold_job(job['id'],'synthetic disposition error')
        self.config['limits']['max_owner_corrections']=1
        request=self.request(job,attempt);self.store.consume_recovery_request(request['id'])
        with self.assertRaisesRegex(Refusal,'exhausted'):
            self.request(job,attempt,reason='Another selected request with distinct evidence')
