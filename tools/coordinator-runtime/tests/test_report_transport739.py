"""Owned fictional report transport; real task/collection/response/receive path.

No provider, external Board, referenced artifact, live journal or native review.
QA629_FIXTURES must name this invocation's explicit retained fixture root.
"""
import asyncio
import copy
import json
from pathlib import Path
import sys
import unittest
import time
from types import SimpleNamespace
from unittest.mock import patch

from test_qa629_repairs import Fixture, actor
import test_report_batches50109 as batches
from support import collect, ident, result
from coordinator_runtime import report_scope, software, processing, prospective
from coordinator_runtime.contracts import Refusal, collected_task_result, digest, encode, task_result
from coordinator_runtime.dispatcher import job_prompt
from coordinator_runtime.appserver import AppServer


class ReportTransport(Fixture):
    def configure(self):
        batches.ReportBatches.configure(self)
        self.config['tasks']['reviews-integrator']['allowed_handoffs'] = ['Work']

    admit = batches.ReportBatches.admit

    def setUp(self):
        batches.ReportBatches.setUp(self)
        if 'large' in self._testMethodName:
            history = dict(semantic='UNKNOWN', exit=1, findings=['original dissent Ω'],
                failures=['original failed command'], unknowns=['delivery unknown'],
                artifacts=[dict(path='/fictional/unacquired/original-report.json', sha256='f'*64)],
                handoffs=[dict(recipient='Work', required='settled', text='original unsent duty')],
                native_history=[dict(collector='fictional original', method='fictional HIGH',
                    answer_json=json.dumps(dict(collected_reports=[dict(history='older exact history',
                        status='PARTIAL', failures=['older failure'], unknowns=['older unread'])]), indent=3))])
            self.reports[0]['reports'].append(dict(name='Original native history and duties', body=json.dumps(history, indent=3)))
            # A fresh explicit policy selects these fictional bytes before intake.
            prospective.revoke(self.store, self.issuer, self.epoch['id'])
            with actor(self.boards['Work'].store, self.issuer):
                processing.revoke(self.store, self.boards, self.cap)
                self.selection['basis'] = processing.basis(self.store, self.boards)
                self.selection['service']['legacy_resources']['Reviews']['reviews_report']['reports'] = [
                    dict(reference=r['reference'], sha256=digest(r)) for r in self.reports]
                self.cap = processing.select(self.store, self.boards, self.selection)['capability']
            self.store.processing = processing.Access(self.store, self.cap, self.boards)
            self.epoch = prospective.select(self.store, self.issuer, dict(configuration=digest(self.config),
                authority='Fictional recursive report input selection before any intake', expires=time.time()+600,
                processing_capability=self.cap, grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
                tasks={t:dict(task_hash=digest(v), software_handoffs={}, ordinary_effects=False)
                       for t,v in self.config['tasks'].items()}))

    def start(self, reports=None):
        ids = self.admit(self.reports if reports is None else reports)
        job = self.store.reserve()
        self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        self.boards['Reviews'].bind_software_attempt(self.store, job, attempt, None)
        return job, attempt, ids

    def answer(self, job, semantic='DONE'):
        reports = report_scope.conserved_inputs(self.store, job)
        analysis = dict(**report_scope.integration_protocol(self.store, job, reports),
            method='Applied the supplied current method: preserve dissent, compare source coverage, assign remaining duties.',
            analysis='The original PARTIAL coverage is evidence of an unresolved Source duty. This consolidation neither repairs it nor accepts effects.',
            decision='Return attributed evidence to Work for independent disposition; original custodians retain all unresolved duties.',
            coverage=[dict(**pin, extent='whole', limits=['Underlying referenced evidence remains unacquired.'])
                      for pin in report_scope.source_pins(reports)])
        answer = result(semantic=semantic, category='consolidated')
        answer.update(findings=[analysis], handoffs=[],
                      no_handoff_reason='The configured complete report response goes to Work; no new independent intent.')
        return answer

    def finish(self, job, attempt, answer, code=0, **details):
        collect(self.store, attempt, answer, code=code,
                tool_completion=dict(complete=True, items=[], nonzero_completions=[]), **details)
        response = self.store.finish_job(job['id'], job['token'])
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']), answer)
        self.assertEqual(json.loads(self.store.one('SELECT result FROM results WHERE attempt=?', (attempt,))['result']), answer)
        response = response or self.store.job(job['id'])['response']
        return self.store.event(response) if response else None

    def test_large_recursive_original_and_small_model_result_reach_work_once(self):
        # Original JSON strings, including noncanonical whitespace, native history,
        # failed outcomes, unknowns and inert handoffs all stay exact. No paths are opened.
        self.assertGreater(len(self.reports[0]['reports'][0]['body']), 150000)
        job, attempt, ids = self.start([self.reports[0]])
        before = encode(self.store.event(ids[0]))
        answer = self.answer(job)
        answer['findings'].append(dict(author='new fictional integrator', assertion='New disagreement remains attributed separately.'))
        self.assertLess(len(encode(answer).encode()), 4000)
        exact = report_scope.conserved_inputs(self.store, job)
        response = self.finish(job, attempt, answer)
        self.assertEqual(response['body'], answer)
        self.assertEqual(encode(response['report_custody']['collected_reports']), encode(exact))
        self.assertEqual(response['report_custody']['model_result_sha256'], digest(answer))
        self.assertLess(len(encode(response).encode()), 262144)
        self.assertEqual(encode(self.store.event(ids[0])), before)
        self.assertNotIn('collected_reports', encode(answer))
        self.assertTrue(software.collected_report(self.store, self.store.job(job['id']), 'work-proposer'))
        self.classify()
        receiving = self.store.reserve()
        self.assertEqual(receiving['task'], 'work-proposer')
        receiving_attempt = self.store.start_job(receiving['id'], receiving['token'])
        self.boards['Work'].bind_software_attempt(self.store, self.store.job(receiving['id']), receiving_attempt, None)
        prompt = job_prompt(self.store, self.store.job(receiving['id']))
        context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
        incoming = context['events'][0]
        self.assertEqual(incoming['body'], answer)
        self.assertEqual(incoming['report_custody'], response['report_custody'])
        marker = self.reports[0]['reports'][0]['body']
        self.assertEqual(prompt.count(encode(marker)[1:-1]), 1)
        recurrent = report_scope.conserved_inputs(self.store, self.store.job(receiving['id']))
        self.assertEqual(recurrent[0]['report_custody'], response['report_custody'])
        self.assertEqual(recurrent[0]['original'], answer)
        # Collection of Reviews never supplies the receiving Work completion.
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (response['id'],))['processed_at'])

    def test_prompt_supplies_each_original_once_and_explicit_protocol(self):
        job, attempt, _ = self.start()
        prompt = job_prompt(self.store, job)
        context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
        self.assertEqual(context['collected_reports'], report_scope.conserved_inputs(self.store, job))
        self.assertEqual(context['report_integration'], report_scope.integration_protocol(self.store, job, context['collected_reports']))
        for index, event in enumerate(context['events']):
            self.assertNotIn('body', event)
            self.assertEqual(event['body_from'], 'collected_reports['+str(index)+'].original')
        self.assertIn('REPORT TRANSPORT:', prompt)
        self.finish(job, attempt, self.answer(job))

    def test_dispatcher_collects_small_model_result_and_custody_without_artifact_adoption(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        answers = []
        async def fictional_model(key, prompt, spec, schema):
            self.store.authorize_launch(key)
            answer = self.answer(self.store.job(job['id']))
            answers.append(copy.deepcopy(answer))
            self.store.begin(key, dict(fictional_sdk=True))
            self.store.session(key, ident())
            return dict(exit=0, capture='complete', cleanup='done', result=answer, error=None,
                        detail=dict(tool_completion=dict(complete=True, items=[], nonzero_completions=[])))
        with patch.object(self.runtime, 'run_model', side_effect=fictional_model):
            asyncio.run(self.runtime.execute(job['id'], attempt))
        response = self.store.event(self.store.job(job['id'])['response'])
        self.assertEqual(response['body'], answers[0])
        self.assertEqual(self.store.rows('SELECT * FROM artifacts'), [])
        self.assertEqual(response['report_custody']['attempt'], attempt)

    def wire(self, clarify=False):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        answer = self.answer(self.store.job(job['id']))
        plan = dict(result=answer)
        if clarify:
            original = copy.deepcopy(answer)
            original['new_original_field'] = dict(dissent='Prior model adverse assertion stays exact.')
            answer['findings'].append(dict(kind='outer-contract-original', fields=dict(
                new_original_field=copy.deepcopy(original['new_original_field']))))
            plan = dict(result=original, second_result=answer)
        path = self.area/'owned-model-plan.json'
        path.write_text(encode(plan))
        self.runtime.models = AppServer(self.config, [sys.executable,
            str(Path(__file__).with_name('fixture_appserver.py')), str(path)])
        asyncio.run(self.runtime.execute(job['id'], attempt))
        actual = self.store.attempt(attempt)
        self.assertEqual(actual['exit'], 0)
        self.assertIsNotNone(actual['ended'])
        self.assertIsNotNone(actual['collected'])
        self.assertEqual(actual['capture'], 'complete')
        self.assertIsNone(actual['error'])
        self.assertEqual(collected_task_result(actual), answer)
        response = self.store.event(self.store.job(job['id'])['response'])
        self.assertEqual(response['body'], answer)
        self.assertEqual(response['report_custody']['collected_reports'], report_scope.conserved_inputs(self.store, job))
        if clarify:
            self.assertEqual(json.loads(actual['detail'])['prior_turn_result'], original)

    def test_large_real_appserver_wire_small_new_analysis(self):
        self.wire()

    def test_real_appserver_clarification_retains_own_original(self):
        self.wire(clarify=True)

    def test_invented_coverage_and_missing_current_analysis_refused(self):
        job, attempt, _ = self.start()
        good = self.answer(job)
        mutations = [lambda a: a['findings'][0].update(analysis=''),
                     lambda a: a['findings'][0].pop('method'),
                     lambda a: a['findings'][0].update(task_sha256='0'*64),
                     lambda a: a['findings'][0]['sources'].reverse(),
                     lambda a: a['findings'][0]['coverage'].pop(),
                     lambda a: a['findings'][0]['coverage'][0].update(sha256='0'*64),
                     lambda a: a['findings'][0]['coverage'][0].update(extent='unread'),
                     lambda a: a['findings'][0]['coverage'][0].update(extent='native-review-complete')]
        for mutate in mutations:
            changed = copy.deepcopy(good)
            mutate(changed)
            with self.subTest(answer=changed), self.assertRaises(Refusal):
                report_scope.validate_result(self.store, job, task_result(changed))
        missing = result(category='consolidated')
        with self.assertRaisesRegex(Refusal, 'whole original'):
            report_scope.validate_result(self.store, job, missing)
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_changed_original_refused_before_template_read_and_effect(self):
        job, attempt, ids = self.start()
        original = self.store.event(ids[0])
        changed = copy.deepcopy(original)
        changed['body']['original']['history'] = 'unauthorized replacement'
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(changed), digest(changed), ids[0]))
        with patch('coordinator_runtime.dispatcher.template_text', side_effect=AssertionError('source acquired')):
            with self.assertRaisesRegex(Refusal, 'original whole report member changed|authority/resources changed'):
                job_prompt(self.store, job)
        self.assertIsNone(self.store.job(job['id'])['response'])
        self.assertEqual(self.store.rows('SELECT * FROM artifacts'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(original), digest(original), ids[0]))
        self.finish(job, attempt, self.answer(job))

    def incomplete(self, semantic, code=0):
        # A separate reserved original is used for each case by the test runner.
        job, attempt, _ = self.start([self.reports[0]])
        answer = self.answer(job, semantic)
        if semantic != 'DONE':
            answer['findings'][0]['coverage'][0].update(extent='partial', limits=['Current analysis unfinished.'])
        response = self.finish(job, attempt, answer, code=code)
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertFalse(software.collected_report(self.store, self.store.job(job['id']), 'work-proposer'))
        self.assertEqual(response['body']['original_result'], answer)
        self.assertEqual(response['body']['report_custody']['collected_reports'], report_scope.conserved_inputs(self.store, job))
        self.assertEqual(self.store.attempt(attempt)['exit'], code)
        self.assertEqual(self.store.attempt(attempt)['semantic'], semantic)

    def test_partial_retains_duties(self):
        self.incomplete('PARTIAL')

    def test_unknown_retains_duties(self):
        self.incomplete('UNKNOWN')

    def test_failed_retains_duties(self):
        self.incomplete('FAILED')

    def test_exit1_retains_duties(self):
        self.incomplete('DONE', code=1)

    def test_typed_new_handoff_retains_custody_and_requires_receiving_settlement(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        handoff = dict(recipient='Work', kind='result', text='Independently disposition the attributed open findings.',
                       ref=None, required='settled')
        answer.update(handoffs=[handoff], no_handoff_reason=None)
        response = self.finish(job, attempt, answer)
        self.assertEqual(response['body'], answer)
        self.assertEqual(self.store.job(job['id'])['state'], 'awaiting-delivery')
        outboxes = self.store.rows('SELECT * FROM outboxes WHERE job=?', (job['id'],))
        self.assertEqual(len(outboxes), 1)
        self.assertEqual(outboxes[0]['required'], 'settled')
        payload = json.loads(outboxes[0]['payload'])
        self.assertEqual(payload['source_result'], answer)
        self.assertEqual(payload['original_handoff'], handoff)
        self.assertEqual(payload['report_custody'], response['report_custody'])
        self.assertFalse(self.store.deliveries_settled(job['id']))
        self.assertIsNone(outboxes[0]['processed_at'])

    def test_large_legacy_partial_already_contains_exact_original_membership(self):
        job, attempt, _ = self.start([self.reports[0]])
        answer = result('PARTIAL', 'consolidated')
        answer['findings'] = [dict(collected_reports=report_scope.conserved_inputs(self.store, job))]
        self.assertGreater(len(encode(answer).encode()), 150000)
        response = self.finish(job, attempt, answer)
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertEqual(response['body']['original_result'], answer)
        self.assertNotIn('report_custody', response['body'])
        self.assertIsNone(report_scope.incomplete_custody(self.store, job, answer))

    def test_custody_keeps_producing_collector_when_read_by_another_controller(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        response = self.finish(job, attempt, answer)
        reader = SimpleNamespace(controller='different fictional receiving collector', config=self.config)
        expected = report_scope.source_custody(reader, job, answer, report_scope.conserved_inputs(self.store, job))
        self.assertEqual(response['report_custody'], expected)
        self.assertEqual(expected['collector'], job['controller'])

    def test_incomplete_capture_is_not_qualified_by_valid_analysis(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        response = self.finish(job, attempt, answer, capture='incomplete')
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertEqual(response['body']['capture'], 'incomplete')
        self.assertEqual(response['body']['original_result'], answer)
        self.assertEqual(response['body']['report_custody']['collected_reports'], report_scope.conserved_inputs(self.store, job))
        self.assertFalse(software.collected_report(self.store, self.store.job(job['id']), 'work-proposer'))

    def test_custody_tampering_refuses_independent_report_transfer(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        response = self.finish(job, attempt, answer)
        good = copy.deepcopy(response)
        for mutate in [lambda e: e.pop('report_custody'),
                       lambda e: e['report_custody']['collected_reports'][0]['original']['original'].pop('history'),
                       lambda e: e['report_custody'].update(model_result_sha256='0'*64)]:
            changed = copy.deepcopy(good)
            mutate(changed)
            self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(changed), digest(changed), changed['id']))
            with self.assertRaises(Refusal):
                software.collected_report(self.store, self.store.job(job['id']), 'work-proposer')
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(good), digest(good), good['id']))

    def test_clarification_conserves_new_assertions_and_all_old_custody(self):
        job, attempt, _ = self.start()
        old = self.answer(job, 'PARTIAL')
        current = copy.deepcopy(old)
        current['findings'].append(copy.deepcopy(current['findings'][0]))
        current['findings'][-1]['analysis'] = 'New analysis finished; earlier partial assertion and Source unknowns remain attributed.'
        current.update(semantic='DONE')
        task_result(current, old)
        response = self.finish(job, attempt, current, prior_turn_result=old)
        self.assertEqual(response['body']['findings'][0], old['findings'][0])
        self.assertEqual(response['body']['failures'], old['failures'])
        self.assertEqual(response['report_custody']['collected_reports'], report_scope.conserved_inputs(self.store, job))
        changed = copy.deepcopy(current)
        changed['findings'][0]['analysis'] = 'Erased original meaning'
        with self.assertRaisesRegex(Refusal, 'rewrote original findings'):
            task_result(changed, old)

    def test_actual_output_budget_cannot_substitute_for_analysis_validity(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        answer['findings'][0]['analysis'] = 'Ω'*32768
        # Text is valid at65536 UTF-8 bytes; the whole composed result still
        # must obey the existing selected limit without expanding it.
        report_scope.validate_result(self.store, job, answer)
        budget_only = SimpleNamespace(controller=self.store.controller, config=dict(limits=dict(max_result_bytes=1024)))
        with self.assertRaisesRegex(Refusal, 'exceed selected result budget'):
            report_scope.source_custody(budget_only, job, answer, report_scope.conserved_inputs(self.store, job))
        self.assertIsNone(self.store.job(job['id'])['response'])


if __name__ == '__main__':
    unittest.main()
