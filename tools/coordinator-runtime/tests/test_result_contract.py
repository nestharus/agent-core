"""Q7-01: outer contract, faithful single clarification and genuine holds."""
import copy
import json
from pathlib import Path
import unittest

import test_writer_custody as fixtures
import test_corrections as process_fixtures
from support import result
from coordinator_runtime import readiness
from coordinator_runtime.contracts import Refusal, task_result, task_result_issues, task_result_instructions
from coordinator_runtime.dispatcher import RESULT_SCHEMA


def ready():return {'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[]}


def carry(fields):return {'kind':'outer-contract-original','fields':fields}


class OuterContract(unittest.TestCase):
    def test_unsupported_is_distinct_from_missing_and_never_mutates_the_original(self):
        answer={**result(),'completion':ready(),'dissent':[]};before=copy.deepcopy(answer)
        self.assertEqual(task_result_issues(answer),['unsupported task-result fields: dissent'])
        self.assertTrue(readiness.needs_clarification(answer,[]))
        with self.assertRaisesRegex(Refusal,'unsupported task-result fields: dissent'):task_result(answer)
        self.assertEqual(answer,before)

    def test_missing_types_categories_arrays_and_optional_types_have_precise_diagnostics(self):
        missing=result();del missing['summary']
        self.assertEqual(task_result_issues(missing),['missing required task-result fields: summary'])
        malformed={**result(),'summary':17,'category':['complete'],'findings':{},'failures':'failure',
            'unknowns':None,'artifacts':{},'handoffs':'Root','completion':[],'no_handoff_reason':False}
        issues=task_result_issues(malformed)
        for key in ['summary','category','findings','failures','unknowns','artifacts','handoffs','completion','no_handoff_reason']:
            with self.subTest(key=key):self.assertTrue(any(issue.startswith(key) for issue in issues))
        self.assertFalse(any('missing' in issue for issue in issues))
        self.assertTrue(readiness.needs_clarification(malformed,[]))
        self.assertEqual(task_result_issues(['actual malformed original']),['task result must be a JSON object'])

    def test_dissent_is_attributed_finding_data_not_a_new_authority_key(self):
        answer={**result(),'findings':[{'kind':'dissent','author':'original synthetic reviewer',
            'meaning':'Real doubt remains recorded','source':'owned fixture report'}]}
        self.assertIs(task_result(answer),answer)
        instructions=task_result_instructions()
        self.assertIn('dissent as attributed entries in findings',instructions)
        self.assertIn('No other outer keys',instructions)

    def test_nonempty_handoff_allows_original_null_reason_without_projection(self):
        answer={**result(),'handoffs':[{'recipient':'Root','kind':'question','text':'Actual recipient duty',
            'ref':None,'required':'settled'}],'no_handoff_reason':None}
        self.assertIs(task_result(answer),answer);self.assertIsNone(answer['no_handoff_reason'])
        with self.assertRaisesRegex(Refusal,'null is allowed only with nonempty handoffs'):
            task_result({**answer,'handoffs':[]})

    def test_generic_extra_data_and_original_findings_must_survive_model_repair(self):
        old={**result(),'findings':[{'kind':'dissent','meaning':'Existing finding remains exact'}],
             'new_provider_field':{'detail':['nonempty consequential data']}}
        repaired={**result(),'findings':copy.deepcopy(old['findings'])}
        with self.assertRaisesRegex(Refusal,'must conserve original extra'):task_result(repaired,old)
        repaired['findings'].append(carry({'new_provider_field':old['new_provider_field']}))
        self.assertIs(task_result(repaired,old),repaired)
        repaired['findings'][0]={'kind':'dissent','meaning':'Silently rewritten'}
        with self.assertRaisesRegex(Refusal,'rewrote original findings'):task_result(repaired,old)

    def test_malformed_unknown_cannot_be_fabricated_empty_during_clarification(self):
        old={**result(),'unknowns':'A real unresolved local condition'}
        repaired={**result(),'findings':[*copy.deepcopy(old['findings']),carry({'unknowns':old['unknowns']})]}
        with self.assertRaisesRegex(Refusal,'rewrote original unknowns'):task_result(repaired,old)
        repaired['unknowns']=[old['unknowns']]
        self.assertIs(task_result(repaired,old),repaired)

    def test_ready_blocked_partial_and_adverse_rules_stay_distinct(self):
        answer={**result(),'completion':ready()}
        self.assertFalse(readiness.needs_clarification(answer,[]))
        blocked={**answer,'unknowns':['Unresolved local verification'], 'completion':{
            **ready(),'local':'blocked','unknowns':[{'index':0,'status':'unresolved','owner':'producer',
                'duty':'verification','reason':'The current local invariant still fails.'}]}}
        self.assertFalse(readiness.needs_clarification(blocked,[]))  # Valid proof of blocked, never ready.
        partial=result('PARTIAL','blocker')
        self.assertEqual(task_result_issues(partial),[])
        self.assertFalse(readiness.needs_clarification(partial,[]))  # Ordinary remaining-work continuation handles it.
        empty={**partial,'failures':[],'unknowns':[]}
        self.assertTrue(readiness.needs_clarification(empty,[]))
        self.assertTrue(readiness.needs_clarification(answer,[{'id':'actual-adverse','exit_code':1,'status':'failed'}]))


class OwnedOuterClarification(unittest.IsolatedAsyncioTestCase):
    include_root=True
    asyncSetUp=fixtures.WriterCustody.asyncSetUp
    run_writer=fixtures.WriterCustody.run_writer
    settle_routine=fixtures.WriterCustody.settle_routine

    def answers(self):
        first={**result(),'findings':[{'source':'owned synthetic input','meaning':'Existing finding preserved'}],
            'artifacts':[str(self.target)],'completion':ready(),'handoffs':[],
            'no_handoff_reason':'Internal synthetic role result; no external effect.',
            'dissent':[{'author':'original synthetic reviewer','source':'owned fixture',
                        'meaning':'Conserve this nonempty dissent without granting effect authority.'}]}
        final={k:copy.deepcopy(v) for k,v in first.items() if k!='dissent'}
        final['findings'].append(carry({'dissent':copy.deepcopy(first['dissent'])}))
        return first,final

    async def run_pair(self,first,final,**plan):
        return await self.run_writer(answer_extra=first,plan_extra={
            'completion_mode':'explicit','write_once':True,'second_result':final,**plan})

    async def test_one_owned_outer_clarification_publishes_then_progresses_with_external_duty_unsettled(self):
        first,final=self.answers()
        for answer in [first,final]:
            answer['unknowns']=['Required external synthetic consumption is pending.']
            answer['completion']['unknowns']=[{'index':0,'status':'deferred','owner':'Root','duty':'consume report',
                'reason':'The necessary real synthetic recipient has not settled its duty.'}]
            answer['handoffs']=[{'recipient':'Root','kind':'question','text':'Select future consumption independently.',
                                'ref':'owned fresh synthetic report','required':'settled'}]
            answer['no_handoff_reason']=''
        record=Path(self.temp.name)/'stage-write-record'
        job,attempt=await self.run_pair(first,final,stage_write_record=str(record))
        row=self.store.attempt(attempt);detail=json.loads(row['detail'])
        self.assertEqual(row['exit'],0);self.assertIsNone(row['error']);self.assertIsNotNone(row['collected'])
        self.assertEqual(detail['result_contract_issues'],['unsupported task-result fields: dissent'])
        self.assertEqual(detail['prior_turn_result'],first)
        self.assertEqual(json.loads(row['result']),final)
        self.assertEqual(len(detail['tool_completion']['items']),2)
        self.assertEqual(len(record.read_text().splitlines()),1)
        self.assertEqual(json.loads(self.target.read_text())['total'],12)
        await self.settle_routine(job)
        self.assertEqual(self.store.job(job['id'])['state'],'awaiting-delivery')
        source=json.loads(job['members'])[0]['event']
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source,))['processed_at'])
        next_job,next_attempt=await self.run_writer(plan_extra={'target_contents':{'total':29}})
        self.assertNotEqual(attempt,next_attempt)
        self.assertEqual(self.store.job(next_job['id'])['effects'],'reconciled')
        self.assertEqual(json.loads(self.target.read_text())['total'],29)
        self.assertNotEqual(self.store.job(job['id'])['state'],'closed')

    async def test_general_extra_and_category_summary_mismatches_are_clarified_together(self):
        first,final=self.answers()
        first.pop('dissent');final['findings']=copy.deepcopy(first['findings'])
        first.update(summary='',category='blocked',future_extension={'original':'nonempty exact data'})
        final['findings'].append(carry({'future_extension':first['future_extension']}))
        job,attempt=await self.run_pair(first,final)
        detail=json.loads(self.store.attempt(attempt)['detail'])
        self.assertEqual(len(detail['result_contract_issues']),3)
        self.assertEqual(self.store.job(job['id'])['effects'],'reconciled')

    async def test_a_second_bad_outer_return_stays_held_without_another_clarification(self):
        first,_=self.answers()
        job,attempt=await self.run_pair(first,first)
        row=self.store.attempt(attempt);detail=json.loads(row['detail'])
        self.assertEqual(json.loads(row['result']),first)
        self.assertEqual(detail['prior_turn_result'],first)
        self.assertIn('unsupported task-result fields: dissent',row['error']);self.assertNotIn('missing',row['error'])
        self.assertEqual(len(detail['tool_completion']['items']),2)
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertIsNotNone(self.store.job(job['id'])['response'])

    async def test_simply_dropping_dissent_cannot_publish_or_settle(self):
        first,final=self.answers();final['findings']=copy.deepcopy(first['findings'])
        job,attempt=await self.run_pair(first,final)
        row=self.store.attempt(attempt)
        self.assertIn('must conserve original extra',row['error'])
        self.assertEqual(json.loads(row['detail'])['prior_turn_result']['dissent'],first['dissent'])
        self.assertEqual(json.loads(row['result']),final)
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertEqual(json.loads(self.target.read_text())['total'],0)

    async def test_genuine_local_blocker_stays_held_after_outer_repair(self):
        first,final=self.answers()
        for answer in [first,final]:
            answer['unknowns']=['Unresolved local staged invariant']
            answer['completion'].update(local='blocked',unknowns=[{'index':0,'status':'unresolved','owner':'producer',
                'duty':'verification','reason':'Still fails; not downstream work.'}])
        job,attempt=await self.run_pair(first,final)
        self.assertEqual(json.loads(self.store.attempt(attempt)['result'])['unknowns'],first['unknowns'])
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='effect-request'"))

    async def test_true_partial_and_adverse_history_survive_outer_repair_and_a_later_zero(self):
        first,final=self.answers()
        for answer in [first,final]:
            answer.update(semantic='PARTIAL',category='blocker',failures=['Actual unresolved local verification failure'])
            answer['completion'].update(local='blocked')
        job,attempt=await self.run_pair(first,final,tool_metadata={'exitCode':1,'status':'failed'},
                                      second_tool_metadata={'exitCode':0,'status':'completed'})
        row=self.store.attempt(attempt);detail=json.loads(row['detail'])
        self.assertEqual(row['semantic'],'PARTIAL');self.assertEqual(json.loads(row['result'])['failures'],first['failures'])
        self.assertEqual([r['exit_code'] for r in detail['tool_completion']['items']],[1,0])
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['state'],'held')

    async def test_unknown_tool_end_is_not_waived_by_valid_outer_repair_or_later_zero(self):
        first,final=self.answers()
        job,attempt=await self.run_pair(first,final,tool_metadata={'exitCode':None},second_tool_metadata={'exitCode':0})
        detail=json.loads(self.store.attempt(attempt)['detail'])
        # Selected stricter contract: an incomplete original prevents the second turn.
        self.assertEqual([r['exit_code'] for r in detail['tool_completion']['items']],[None])
        self.assertFalse(detail['tool_completion']['complete'])
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')


class GeneralTaskWire(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=process_fixtures.ProcessCorrections.asyncSetUp
    adapter=process_fixtures.ProcessCorrections.adapter
    task=process_fixtures.ProcessCorrections.task

    async def test_nonroutine_task_uses_same_outer_contract_and_conserves_data(self):
        job,attempt=self.task()
        first={**result(),'new_field':{'source':'genuine synthetic context','value':'meaning'}}
        final={**result(),'findings':[*copy.deepcopy(first['findings']),carry({'new_field':first['new_field']})]}
        outcome=await self.adapter({'result':first,'second_result':final,'tool_metadata':{'exitCode':0}}).run(
            self.store,attempt,'fresh synthetic task',self.config['tasks']['work-integrator'],RESULT_SCHEMA)
        self.assertIsNone(outcome['error']);self.assertEqual(outcome['result'],final)
        self.assertEqual(outcome['detail']['prior_turn_result'],first)
        self.assertEqual(len(outcome['detail']['tool_completion']['items']),2)
        self.store.collect(attempt,outcome);self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.job(job['id'])['state'],'closed')

    async def test_nonobject_inner_value_can_be_clarified_once_without_losing_original(self):
        job,attempt=self.task();first=['Malformed original value with an adverse claim']
        final={**result('PARTIAL','blocker'),'findings':[carry({'$result':first})]}
        outcome=await self.adapter({'result':first,'second_result':final}).run(
            self.store,attempt,'fresh synthetic task',self.config['tasks']['work-integrator'],RESULT_SCHEMA)
        self.assertEqual(outcome['detail']['prior_turn_result'],first);self.assertEqual(outcome['result'],final)
        self.assertIsNone(outcome['error']);self.assertEqual(outcome['exit'],0)

    async def test_still_invalid_semantic_type_keeps_precise_diagnostic_after_one_clarification(self):
        _,attempt=self.task();first={**result(),'semantic':['malformed type']}
        outcome=await self.adapter({'result':first,'second_result':first,'tool_metadata':{'exitCode':0}}).run(
            self.store,attempt,'fresh synthetic task',self.config['tasks']['work-integrator'],RESULT_SCHEMA)
        self.assertEqual(outcome['result'],first);self.assertEqual(outcome['detail']['prior_turn_result'],first)
        self.assertIn('semantic must be one of',outcome['error'])
        self.assertNotIn('TypeError',outcome['error']);self.assertFalse(outcome['detail']['capacity_error'])
        self.assertEqual(len(outcome['detail']['tool_completion']['items']),2)
        self.assertEqual(outcome['exit'],0)
