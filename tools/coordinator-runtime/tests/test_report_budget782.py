"""Owned synthetic production-path regressions for separate report budgets."""
import copy
import json
from unittest.mock import patch

import test_report_transport739 as transport
from coordinator_runtime import report_scope, software, service
from coordinator_runtime.contracts import Backpressure, Refusal, encode
from coordinator_runtime.dispatcher import job_prompt


class ReportBudget782(transport.ReportTransport):
    def test_782_large_full_custody_reaches_actual_work_prompt_and_outbox(self):
        job, attempt, ids = self.start()
        self.assertEqual(len(ids), 2)
        reports = report_scope.conserved_inputs(self.store, job)
        self.assertGreater(len(encode(reports).encode()), 262144)
        self.assertFalse(report_scope.fits_return(self.store, reports))
        self.assertTrue(report_scope.fits_return(self.store, reports, transport=True))
        answer = self.answer(job)
        answer['findings'][0]['analysis'] = 'Ω' * 12094
        answer.update(handoffs=[dict(recipient='Work', kind='result', text='Disposition all original qualifications.',
                                    ref=None, required='settled')], no_handoff_reason=None)
        self.assertLess(len(encode(answer).encode()), 262144)
        response = self.finish(job, attempt, answer)
        self.assertGreater(len(encode(response).encode()), 262144)
        self.assertEqual(response['report_custody']['collected_reports'], reports)
        outbox = self.store.one('SELECT * FROM outboxes WHERE job=?', (job['id'],))
        self.assertGreater(len(outbox['payload'].encode()), 262144)
        self.assertEqual(json.loads(outbox['payload'])['report_custody'], response['report_custody'])
        # Re-ingestion is the actual software receiver's persisted-intent path.
        self.assertFalse(self.store.ingest(response))
        self.classify()
        receiving = self.store.reserve()
        self.assertEqual(receiving['task'], 'work-proposer')
        receiving_attempt = self.store.start_job(receiving['id'], receiving['token'])
        receiving = self.store.job(receiving['id'])
        self.boards['Work'].bind_software_attempt(self.store, receiving, receiving_attempt, None)
        prompt = job_prompt(self.store, receiving)
        context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
        self.assertEqual(context['events'][0]['report_custody']['collected_reports'], reports)
        self.assertEqual(context['events'][0]['body'], answer)
        for receipt in self.reports:
            marker = receipt['reports'][0]['body']
            # These fixture sources intentionally have identical body strings;
            # every distinct attributed source remains once, without deduplication.
            self.assertEqual(prompt.count(encode(marker)[1:-1]), 2)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (response['id'],))['processed_at'])

    def test_782_large_analysis_overcap_and_legacy_whole_copy_refuse(self):
        job, attempt, _ = self.start()
        reports = report_scope.conserved_inputs(self.store, job)
        answer = self.answer(job)
        answer['findings'].append(dict(new_analysis='x'*262144))
        with self.assertRaisesRegex(Refusal, 'selected result budget'):
            report_scope.validate_result(self.store, job, answer)
        legacy = report_scope.complete_return(reports)
        self.assertGreater(len(encode(legacy).encode()), 262144)
        from support import collect
        collect(self.store, attempt, legacy, tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        self.assertIsNone(self.store.attempt(attempt)['result'])
        self.assertEqual(self.store.attempt(attempt)['capture'], 'incomplete')

    def test_782_large_actual_wrapper_artifact_and_global_ceiling_refuse(self):
        job, attempt, _ = self.start()
        answer = self.answer(job)
        reports = report_scope.conserved_inputs(self.store, job)
        # Change only this explicit synthetic measurement configuration; no live
        # configuration or source selection is altered.
        from types import SimpleNamespace
        for key in ('max_artifact_bytes', 'max_bytes'):
            limits = dict(self.config['limits'], max_artifact_bytes=33554432)
            limits[key] = 262144
            bounded = SimpleNamespace(config=dict(limits=limits), one=self.store.one)
            with self.assertRaisesRegex(Refusal, 'artifact/global ceiling'):
                report_scope.source_custody(bounded, job, answer, reports)
        usage = self.store.usage()
        usage['bytes'] = self.config['limits']['max_bytes']
        with patch.object(self.store, 'usage', return_value=usage), self.assertRaises(Backpressure):
            self.store.budget(None, len(encode(reports).encode()))
        custody = report_scope.source_custody(self.store, job, answer, reports)
        bounded = SimpleNamespace(config=dict(limits=dict(self.config['limits'], max_artifact_bytes=262144)))
        with self.assertRaisesRegex(Refusal, 'artifact/global ceiling'):
            report_scope.validate_envelope(bounded, dict(report_custody=custody, wrapper='x'))
        exact = len(encode(dict(body=answer, report_custody=custody)).encode())
        with patch.object(report_scope, 'transport_limit', return_value=exact), self.assertRaises(Refusal):
            self.store._outbox('Reviews', 'Work', 'result', dict(body=answer, report_custody=custody,
                               additional_wrapper='must also fit'), job=job['id'])
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_782_large_holds_authority_and_wrong_collector_still_refuse(self):
        job, attempt, ids = self.start()
        response = self.finish(job, attempt, self.answer(job))
        current = self.store.job(job['id'])
        self.store.db.execute('UPDATE events SET hold=? WHERE id=?', ('synthetic current hold', ids[0]))
        with self.assertRaises(Refusal):
            report_scope.validate_large_event(self.store, response)
        self.store.db.execute('UPDATE events SET hold=NULL WHERE id=?', (ids[0],))
        altered = copy.deepcopy(response)
        altered['report_custody']['collector'] = 'wrong original collector'
        with self.assertRaises(Refusal):
            report_scope.validate_large_event(self.store, altered)
        from coordinator_runtime import prospective
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        with self.assertRaises(Refusal):
            software.collected_report(self.store, current, 'work-proposer')

    def test_782_large_single_selected_intake_exceeds_model_cap_losslessly(self):
        import time
        from coordinator_runtime import processing, prospective
        from coordinator_runtime.contracts import digest
        from test_qa629_repairs import actor
        self.assertFalse(report_scope.selected_intake(self.store, dict(body=dict(original=[]))))
        receipt = self.reports[0]
        receipt['reports'][0]['body'] += 'Original adverse qualification Ω. '*6000
        self.assertGreater(len(encode(receipt).encode()), 262144)
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        with actor(self.boards['Work'].store, self.issuer):
            processing.revoke(self.store, self.boards, self.cap)
            self.selection['basis'] = processing.basis(self.store, self.boards)
            self.selection['service']['legacy_resources']['Reviews']['reviews_report']['reports'] = [
                dict(reference=receipt['reference'], sha256=digest(receipt))]
            self.cap = processing.select(self.store, self.boards, self.selection)['capability']
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        self.epoch = prospective.select(self.store, self.issuer, dict(configuration=digest(self.config),
            authority='Fictional exact larger report choice before intake', expires=time.time()+600,
            processing_capability=self.cap, grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v), software_handoffs={}, ordinary_effects=False)
                   for t,v in self.config['tasks'].items()}))
        job, attempt, ids = self.start([receipt])
        self.assertGreater(len(encode(self.store.event(ids[0])).encode()), 262144)
        response = self.finish(job, attempt, self.answer(job))
        self.assertEqual(response['report_custody']['collected_reports'][0]['original']['original'], receipt)

    def test_782_large_admission_reserves_full_analysis_allowance(self):
        from types import SimpleNamespace
        reports = [dict(original='x'*10000)]
        runtime = SimpleNamespace(controller=self.store.controller, config=dict(limits=dict(
            max_result_bytes=262144, max_artifact_bytes=270000, max_bytes=1073741824)))
        self.assertTrue(report_scope.fits_return(runtime, reports))
        self.assertFalse(report_scope.fits_return(runtime, reports, transport=True))


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromNames([
        __name__+'.ReportBudget782.'+name for name in ReportBudget782.__dict__ if name.startswith('test_782')])
