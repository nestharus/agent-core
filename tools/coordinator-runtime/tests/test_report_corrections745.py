"""Owned real-caller correction fixtures; no actual runtime or external effects.

Original model/collector answers and SDK principals are explicit fiction. All
fixtures and failed invocations stay in this run's private QA629_FIXTURES root.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_report_transport739 as transport_cases
import test_qa_branch672 as sequence_cases
from test_qa629_repairs import Fixture, actor
from support import collect, ident, result
from coordinator_runtime import configuration, ordinary, processing, report_scope, software
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import job_prompt
from coordinator_runtime.store import Store


TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
QA_SHA256 = '353b886b8ca6646a34200447f7c3e14493a74dc3724ddfca4f0bf205d73197bd'


class Reviews745(Fixture):
    setUp = transport_cases.ReportTransport.setUp
    admit = transport_cases.ReportTransport.admit
    start = transport_cases.ReportTransport.start
    answer = transport_cases.ReportTransport.answer
    finish = transport_cases.ReportTransport.finish

    def configure(self):
        transport_cases.ReportTransport.configure(self)
        selected = self.area / 'reviews-selected.md'
        selected.write_bytes((TEMPLATES / 'reviews-selected.md').read_bytes())
        self.config['tasks']['reviews-integrator']['templates'] = [str(selected)]

    def reject_source_reads(self, members):
        original = self.store.event
        def read(key):
            if key in members:
                self.fail('new member body read before all current metadata was admitted')
            return original(key)
        return patch.object(self.store, 'event', side_effect=read)

    def test_after_await_later_member_hold_blocks_all_custody_and_failure_callers(self):
        job, attempt, ids = self.start()
        self.assertEqual(len(ids), 2)
        job_prompt(self.store, job)  # Lawful initial admission before await.
        answer = self.answer(job)
        before = {key: encode(self.store.event(key)) for key in ids}
        async def original():
            self.store.begin(attempt, dict(fictional_sdk=True))
            self.store.session(attempt, ident())
            await asyncio.sleep(0)
            self.store.set_hold(ids[-1], 'new hold after original launch')
            # Actual original collection remains lawful after the hold.
            self.store.collect(attempt, dict(exit=0, result=answer, capture='complete',
                cleanup='done', error=None, detail=dict(tool_completion=dict(
                    complete=True, items=[], nonzero_completions=[]))))
        asyncio.run(original())
        collected = self.store.attempt(attempt)
        job_before = self.store.job(job['id'])
        with self.reject_source_reads(ids):
            for name, call in [
                ('finish', lambda: self.store.finish_job(job['id'], job['token'])),
                ('custody', lambda: report_scope.transport_custody(self.store, job, answer)),
                ('incomplete', lambda: report_scope.incomplete_custody(self.store, job, answer)),
                ('owner-question', lambda: self.store.owner_question(job, collected, 'current hold')),
                ('failure', lambda: self.store.failure_delivery(job, collected,
                    self.config['tasks'][job['task']], 'current hold')),
                ('handoff', lambda: self.store._task_handoff(job, collected,
                    self.config['tasks'][job['task']], answer, dict(recipient='Work', kind='result',
                    text='New analysis only', ref=None, required='settled'), 0)),
                ('queue-source', lambda: report_scope.source_events(self.store, dict(
                    event=ids[-1], role='Reviews', task='reviews-integrator'))),
            ]:
                with self.subTest(caller=name), self.assertRaises(Refusal):
                    call()
            # Dispatcher retains a safe refusal without trying to reconstruct
            # a source body just to report that custody could not be acquired.
            self.runtime.try_finish(job['id'])
        self.assertEqual(self.store.attempt(attempt), collected)
        self.assertEqual(json.loads(collected['result']), answer)
        self.assertEqual(collected['exit'], 0)
        self.assertIsNotNone(collected['ended'])
        self.assertIsNotNone(collected['collected'])
        # The combined735 outer admission guard defers before any finish or
        # informative-failure mutation. It preserves the exact original job.
        self.assertEqual(self.store.job(job['id']), job_before)
        self.assertIsNone(self.store.job(job['id'])['response'])
        self.assertEqual(self.store.rows('SELECT * FROM outboxes'), [])
        self.assertIn('admission changed', self.runtime.runtime_errors[job['id']])
        # Explicit fixture custodian releases its own hold solely to compare
        # bytes; no production hold or actual receipt is involved.
        self.store.set_hold(ids[-1], None)
        self.assertEqual({key: encode(self.store.event(key)) for key in ids}, before)

    def test_dispatcher_real_await_collects_original_then_refuses_new_source_read(self):
        ids = self.admit(self.reports)
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        answer = self.answer(job)
        held = False
        original_event = self.store.event
        def event(key):
            if held and key in ids:
                self.fail('dispatcher reacquired a source after await and hold')
            return original_event(key)
        async def model(key, prompt, spec, schema):
            nonlocal held
            self.store.authorize_launch(key)
            self.store.begin(key, dict(fictional_sdk=True))
            self.store.session(key, ident())
            await asyncio.sleep(0)
            self.store.set_hold(ids[-1], 'post-await fixture hold')
            held = True
            return dict(exit=0, result=answer, capture='complete', cleanup='done', error=None,
                detail=dict(tool_completion=dict(complete=True, items=[], nonzero_completions=[])))
        with patch.object(self.store, 'event', side_effect=event), patch.object(self.runtime, 'run_model', side_effect=model):
            asyncio.run(self.runtime.execute(job['id'], attempt))
        actual = self.store.attempt(attempt)
        self.assertEqual(json.loads(actual['result']), answer)
        self.assertEqual(actual['exit'], 0)
        self.assertIsNotNone(actual['collected'])
        self.assertIsNotNone(actual['ended'])
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_changed_later_member_metadata_refuses_before_first_body(self):
        job, _, ids = self.start()
        job_prompt(self.store, job)
        self.store.db.execute('UPDATE events SET hash=? WHERE id=?', ('0'*64, ids[-1]))
        with self.reject_source_reads(ids), self.assertRaisesRegex(Refusal, 'member changed'):
            report_scope.conserved_inputs(self.store, job)

    def test_current_source_and_task_authority_refuse_before_any_body(self):
        job, _, ids = self.start()
        with self.reject_source_reads(ids):
            with patch.object(configuration, 'event_allowed', side_effect=lambda runtime, source: source['id'] != ids[-1]):
                with self.assertRaisesRegex(Refusal, 'current authority'):
                    report_scope.conserved_inputs(self.store, job)
            with patch.object(configuration, 'processing_tasks', return_value=[]):
                with self.assertRaisesRegex(Refusal, 'current source authority'):
                    report_scope.conserved_inputs(self.store, job)
            cap, selected = self.store.processing.current()
            selected = copy.deepcopy(selected)
            selected['service']['legacy_resources']['Reviews']['reviews_report']['reports'].pop()
            with patch.object(self.store.processing, 'current', return_value=(cap, selected)):
                with self.assertRaisesRegex(Refusal, 'finite source selection'):
                    report_scope.conserved_inputs(self.store, job)
        # The receipt table is immutable by construction. Change the active
        # service-local capability handle, retaining current() as an explicit
        # fixture seam, to exercise the metadata mismatch without rewriting it.
        current = self.store.processing.current()
        with patch.object(self.store.processing, 'key', ident()), patch.object(
                self.store.processing, 'current', return_value=current), self.reject_source_reads(ids), self.assertRaisesRegex(Refusal, 'collection authority'):
            report_scope.conserved_inputs(self.store, job)

    def test_revoked_processing_authority_refuses_before_body(self):
        job, attempt, ids = self.start()
        answer = self.answer(job)
        with actor(self.boards['Work'].store, self.issuer):
            processing.revoke(self.store, self.boards, self.cap)
        # Original collection is still lawful; current source acquisition is not.
        collect(self.store, attempt, answer, tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        with self.reject_source_reads(ids), self.assertRaises(Refusal):
            self.store.finish_job(job['id'], job['token'])
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']), answer)

    def test_existing_transfer_and_processing_check_all_holds_before_body(self):
        job, attempt, ids = self.start()
        answer = self.answer(job)
        event = self.finish(job, attempt, answer)
        job = self.store.job(job['id'])
        self.store.set_hold(ids[-1], '')  # Non-NULL empty holds are holds too.
        with self.reject_source_reads([*ids, event['id']]):
            self.assertFalse(software.collected_report(self.store, job, 'work-proposer'))
            with self.assertRaises(Refusal):
                software.report_delivery(self.store, job, dict(kind='result', payload=encode(event)))
            with self.assertRaises(Refusal):
                report_scope.execution_report(self.store, event, job, 'work-proposer')

    def successor(self, job):
        successor = Store(self.config)
        self.addCleanup(successor.close)
        successor.processing = processing.Access(successor, self.cap, self.boards)
        successor.adopt_collected(job['id'])
        return successor, successor.job(job['id'])

    def test_original_collector_survives_adoption_before_response_composition(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        collect(self.store, attempt, answer, tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        successor, adopted = self.successor(job)
        response = successor.event(successor.finish_job(adopted['id'], adopted['token']))
        self.assertNotEqual(adopted['controller'], job['controller'])
        self.assertEqual(response['report_custody']['collector'], self.store.attempt(attempt)['controller'])
        self.assertEqual(response['body'], answer)
        handoff = json.loads(adopted['collection_handoff'])
        self.assertEqual(handoff['original_collector'], response['report_custody']['collector'])
        self.assertEqual(handoff['to_controller'], successor.controller)

    def test_unchanged_response_custody_remains_valid_after_closure_adoption(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        answer['handoffs'] = [dict(recipient='Work', kind='result', text='Independent disposition owed.', ref=None, required='settled')]
        response = self.finish(job, attempt, answer)
        self.assertEqual(self.store.job(job['id'])['state'], 'awaiting-delivery')
        before = encode(response)
        successor, adopted = self.successor(job)
        report_scope.validate_transport(successor, adopted, response, answer)
        custody = report_scope.incomplete_custody(successor, adopted, answer)
        self.assertEqual(custody, response['report_custody'])
        self.assertEqual(encode(successor.event(response['id'])), before)
        self.assertEqual(successor.attempt(attempt)['controller'], job['controller'])
        # Unchanged older actual-processing/controller and effect/acceptance
        # checks still apply; custody validation is a separate claim.
        self.assertFalse(software.collected_report(successor, adopted, 'work-proposer'))
        self.assertFalse(successor.deliveries_settled(job['id']))

    def test_reviews_actual_template_and_prompt_select_new_transport(self):
        job, attempt, _ = self.start()
        prompt = job_prompt(self.store, job)
        context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
        self.assertIn('report_integration', context)
        self.assertIn('REPORT TRANSPORT:', prompt)
        self.assertIn((TEMPLATES / 'reviews-selected.md').read_text(), prompt)
        answer = self.answer(job)
        response = self.finish(job, attempt, answer)
        self.assertEqual(response['body'], answer)
        self.assertEqual(response['report_custody']['collected_reports'], context['collected_reports'])


class LegacyQA745(Fixture, unittest.IsolatedAsyncioTestCase):
    package_count = 1
    asyncSetUp = sequence_cases.Sequence672.asyncSetUp
    source = sequence_cases.Sequence672.source
    prepared = sequence_cases.Sequence672.prepared
    package = sequence_cases.Sequence672.package
    select_software = sequence_cases.Sequence672.select_software
    admitted = sequence_cases.Sequence672.admitted
    accepted = sequence_cases.Sequence672.accepted
    qa = sequence_cases.Sequence672.qa
    branch_account = sequence_cases.Sequence672.branch_account
    branch = sequence_cases.Sequence672.branch

    def configure(self):
        sequence_cases.Sequence672.configure(self)
        content = (TEMPLATES / 'qa-package.md').read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), QA_SHA256)
        template = self.area / 'qa-package.md'
        template.write_bytes(content)
        self.config['tasks']['qa-cleanup']['templates'] = [str(template)]

    async def test_exact_legacy_QA_template_prompt_validation_and_accepted_sequence(self):
        self.admitted()
        await self.qa()
        await self.branch()
        job = self.store.reserve()
        self.assertEqual(job['task'], 'qa-cleanup')
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        admission = self.store.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
        self.boards['QA'].bind_software_attempt(self.store, job, attempt, admission)
        prompt = job_prompt(self.store, job)
        context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
        self.assertNotIn('report_integration', context)
        self.assertNotIn('REPORT TRANSPORT:', prompt)
        self.assertNotIn('do not retransmit these bodies', prompt)
        self.assertIn((TEMPLATES / 'qa-package.md').read_text(), prompt)
        reports = context['collected_reports']
        self.assertEqual(reports, report_scope.conserved_inputs(self.store, job))
        answer = result(category='qualification')
        answer['findings'].append(dict(collected_reports=copy.deepcopy(reports)))
        report_scope.validate_result(self.store, job, answer)
        new = result(category='qualification')
        new['findings'] = [dict(**report_scope.integration_protocol(self.store, job, reports),
            analysis='New reasoning', decision='Return to Work', method='Applied current method',
            coverage=[dict(**pin, extent='whole', limits=[]) for pin in report_scope.source_pins(reports)])]
        with self.assertRaisesRegex(Refusal, 'exact whole original'):
            report_scope.validate_result(self.store, job, new)
        collect(self.store, attempt, answer, tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        await ordinary.qualification(self.store, job)
        response = self.store.event(self.store.finish_job(job['id'], job['token']))
        self.assertEqual(response['body'], answer)
        self.assertNotIn('report_custody', response)
        self.assertEqual(response['allowed_tasks'], ['work-proposer'])
        self.assertTrue(ordinary.qualification_current(self.store, job))
        self.assertEqual({r['task'] for r in ordinary.accepted_runs(self.store, self.key)},
                         {'qa-execution', 'branch-integrator'})


if __name__ == '__main__':
    unittest.main()
