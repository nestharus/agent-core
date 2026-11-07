"""Owned synthetic consumer qualification. Production release remains refused.

The release flag alone is an explicit test seam. Grants, finite selections,
intake, reserve, collection, finish, response and prompts use production APIs.
No held original, provider, native acceptance or owner recovery is exercised.
"""
import copy
import json
import time
from unittest.mock import patch

from test_qa629_repairs import Fixture, actor
from test_report_transport739 import ReportTransport
import test_report_batches50109 as batches
from support import collect, result
from coordinator_runtime import report_scope, report_reference as refs, processing, prospective, custody
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import job_prompt
from coordinator_runtime.cleanup import eligible_event


class ReferenceConsumers(Fixture):
    def configure(self):
        ReportTransport.configure(self)
        self.config['artifact_exclusions'] = ['/fictional/excluded']
    admit = ReportTransport.admit
    start = ReportTransport.start
    finish = ReportTransport.finish

    def setUp(self):
        self.enterContext(patch.object(refs, 'RELEASED', True))
        batches.ReportBatches.setUp(self)
        self.reports[0]['reports'].append(dict(name='Distinctive exact adverse values', body=json.dumps(dict(
            failures=['COMMAND_FAILED_768'], dissent='Different conclusion Ω', unknowns=['UNKNOWN_768'],
            inert_intents=[dict(recipient='Branch', text='Unsent original duty')],
            string_bytes=' { "whitespace" : "\\u03a9" }\n', values=[False, 0, 1.0, None]))))
        if 'legacy_negative' in self._testMethodName:
            self.reports[0]['reports'][0]['body'] = 'z'*242000
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        with actor(self.boards['Work'].store, self.issuer):
            processing.revoke(self.store, self.boards, self.cap)
            self.selection['basis'] = processing.basis(self.store, self.boards)
            report_policy = self.selection['service']['legacy_resources']['Reviews']['reviews_report']
            report_policy['reports'] = [dict(reference=r['reference'], sha256=digest(r)) for r in self.reports]
            if 'legacy_negative' not in self._testMethodName:
                report_policy['transport'] = dict(
                    version=refs.VERSION, max_model_bytes=200000 if 'wrapper_overflow' in self._testMethodName else 65536,
                    max_origins=32, max_read_bytes=2000000)
            self.cap = processing.select(self.store, self.boards, self.selection)['capability']
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        self.epoch = prospective.select(self.store, self.issuer, dict(configuration=digest(self.config),
            authority='Owned fictional forward reference consumer authority', expires=time.time()+600,
            processing_capability=self.cap, grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v), software_handoffs={}, ordinary_effects=False)
                   for t,v in self.config['tasks'].items()}))

    def answer(self, job, semantic='DONE'):
        value = ReportTransport.answer(self, job, semantic)
        value['findings'].append(dict(kind=refs.READ_KIND,
            sources=report_scope.source_pins(refs.inputs(self.store, job)), closure='whole', limits=[]))
        return value

    def receive(self, response):
        self.classify()
        job = self.store.reserve()
        self.assertEqual(job['task'], 'work-proposer')
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        self.boards['Work'].bind_software_attempt(self.store, job, attempt, None)
        return job, attempt

    def test_release_gate_refuses_actual_selection_before_any_reference_body(self):
        job, attempt, _ = self.start()
        with patch.object(refs, 'RELEASED', False), patch.object(self.store, 'event', side_effect=AssertionError('body acquired')):
            with self.assertRaisesRegex(Refusal, 'not release-qualified'):
                job_prompt(self.store, job)

    def test_large_roundtrip_real_finish_response_and_next_prompt(self):
        job, attempt, ids = self.start([self.reports[0]])
        original = copy.deepcopy(self.store.event(ids[0]))
        prompt = job_prompt(self.store, job)
        context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
        material = context['report_reference_inputs']['frozen_inputs']
        self.assertEqual(len(material), 1)
        from pathlib import Path
        self.assertEqual(Path(material[0]['frozen_path']).read_bytes(), encode(original).encode())
        answer = self.answer(job)
        response = self.finish(job, attempt, answer)
        self.assertEqual(response['body'], answer)
        self.assertEqual(response['report_custody']['model_result_sha256'], digest(answer))
        self.assertLess(len(encode(response).encode()), 10000)
        self.assertNotIn('collected_reports', response['report_custody'])
        receiver, receiving_attempt = self.receive(response)
        next_prompt = job_prompt(self.store, receiver)
        next_context = json.loads(next_prompt.split('TASK_CONTEXT=',1)[1].split('\n',1)[0])
        acquired = next_context['report_reference_inputs']['frozen_inputs']
        self.assertEqual(len(acquired), 2)
        recovered = {a['report_origin']['event']: json.loads(Path(a['frozen_path']).read_bytes()) for a in acquired}
        self.assertEqual(recovered[ids[0]], original)
        self.assertEqual(recovered[response['id']], response)
        self.assertNotIn('x'*1000, next_prompt)

    def test_current_later_member_hold_blocks_actual_prompt_before_body(self):
        job, _, ids = self.start()
        self.store.db.execute('UPDATE events SET hold=? WHERE id=?', ('later held', ids[-1]))
        with patch.object(self.store, 'event', side_effect=AssertionError('body acquired')):
            with self.assertRaisesRegex(Refusal, 'held'):
                job_prompt(self.store, job)

    def test_foreign_recipient_blocks_actual_prompt_before_body(self):
        job, _, ids = self.start()
        original = self.store.event(ids[0])
        original['recipient'] = 'foreign'
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?', (encode(original), ids[0]))
        with patch.object(self.store, 'event', side_effect=AssertionError('body acquired')):
            with self.assertRaisesRegex(Refusal, 'recipient'):
                job_prompt(self.store, job)

    def test_transitive_hold_blocks_receiver_before_templates_and_blobs(self):
        job, attempt, ids = self.start([self.reports[0]])
        response = self.finish(job, attempt, self.answer(job))
        receiver, _ = self.receive(response)
        self.store.db.execute('UPDATE events SET hold=? WHERE id=?', ('origin held', ids[0]))
        with patch.object(self.store, 'event', side_effect=AssertionError('body acquired')), \
             patch('coordinator_runtime.dispatcher.template_text', side_effect=AssertionError('template read')):
            with self.assertRaisesRegex(Refusal, 'held'):
                job_prompt(self.store, receiver)

    def test_naked_blob_and_unread_closure_are_refused(self):
        job, _, _ = self.start()
        origin = refs.inputs(self.store, job)[0]
        with self.assertRaisesRegex(Refusal, 'whole-group'):
            custody.frozen_body(self.store, origin['sha256'])
        answer = self.answer(job)
        answer['findings'][-1].update(closure='unread', limits=['No whole body acquisition'])
        with self.assertRaisesRegex(Refusal, 'cannot become DONE'):
            report_scope.validate_result(self.store, job, answer)

    def test_actual_handoff_and_informative_failure_keep_reference_custody(self):
        job, attempt, _ = self.start()
        answer = self.answer(job, 'PARTIAL')
        answer['findings'][-1].update(closure='partial', limits=['Actual synthetic frontier'])
        answer.update(handoffs=[dict(recipient='Work', kind='result', text='Retain original dissent, failure and UNKNOWN',
                                    ref=None, required='settled')], no_handoff_reason=None)
        response = self.finish(job, attempt, answer)
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertEqual(response['body']['original_result'], answer)
        self.assertEqual(response['body']['report_custody']['version'], refs.VERSION)
        payloads = [json.loads(r['payload']) for r in self.store.rows('SELECT payload FROM outboxes WHERE job=?',(job['id'],))]
        self.assertTrue(any(p.get('informative_failure',{}).get('report_custody',{}).get('version') == refs.VERSION for p in payloads))
        self.assertTrue(any(p.get('report_custody',{}).get('version') == refs.VERSION for p in payloads))

    def test_producer_origin_and_blob_retained_after_fake_time_with_downstream_hold(self):
        job, attempt, ids = self.start([self.reports[0]])
        response = self.finish(job, attempt, self.answer(job))
        self.store.db.execute('UPDATE events SET hold=? WHERE id=?', ('downstream unread', response['id']))
        self.store.clock = lambda: time.time()+172800
        origin = self.store.one('SELECT * FROM events WHERE id=?', (ids[0],))
        self.assertFalse(eligible_event(self.store, origin))
        self.assertTrue(refs.origin_pinned(self.store, ids[0]))
        context, path = refs.identity(self.store, ids[0])
        record = self.store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?', (context,path))
        self.assertIsNotNone(record)
        self.assertIsNotNone(self.store.one('SELECT sha256 FROM artifact_blobs WHERE sha256=?', (record['sha256'],)))

    def test_after_await_reentry_rechecks_current_scope(self):
        import asyncio
        job, _, ids = self.start()
        job_prompt(self.store, job)
        async def changed_scope():
            await asyncio.sleep(0)
            self.store.db.execute('UPDATE events SET hold=? WHERE id=?', ('post-await hold',ids[-1]))
            with patch.object(self.store, 'event', side_effect=AssertionError('body acquired')):
                with self.assertRaisesRegex(Refusal,'held'):
                    job_prompt(self.store, job)
        asyncio.run(changed_scope())

    def test_current_expiry_and_transitive_exclusion_refuse_actual_prompt(self):
        job, _, _ = self.start()
        self.store.clock = lambda: time.time()+1000
        with patch.object(self.store, 'event', side_effect=AssertionError('body acquired')):
            with self.assertRaisesRegex(Refusal, 'expired|authority/resources|finite Reviews report policy'):
                job_prompt(self.store, job)

    def test_legacy_negative_fit_admission_overflow_actual_finish_preserves_collected(self):
        job, attempt, ids = self.start([self.reports[0]])
        self.assertTrue(report_scope.fits_return(self.store, report_scope.conserved_inputs(self.store,job)))
        answer = ReportTransport.answer(self, job)
        answer['findings'][0]['analysis'] = 'A'*24188
        collect(self.store, attempt, answer, tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        with self.assertRaisesRegex(Refusal, 'whole report custody and new analysis exceed'):
            self.store.finish_job(job['id'],job['token'])
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']),answer)
        self.assertIsNone(self.store.job(job['id'])['response'])
        self.assertEqual(self.store.event(ids[0])['body']['original'],self.reports[0])

    def test_transitive_excluded_alias_blocks_real_prompt_before_event_body(self):
        job, _, _ = self.start()
        ref = refs.inputs(self.store, job)[0]
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
            ('owner:fictional-alias','/fictional/excluded/alias','role-owned',ref['owner'],
             encode(dict(sha256=ref['sha256'],size=ref['bytes'])),ref['sha256']))
        with patch.object(self.store, 'event', side_effect=AssertionError('body acquired')):
            with self.assertRaisesRegex(Refusal,'excluded'):
                job_prompt(self.store,job)

    def test_direct_cli_report_export_refused_before_blob_read(self):
        from coordinator_runtime.cli import operate
        from types import SimpleNamespace
        job, _, _ = self.start()
        ref = refs.inputs(self.store, job)[0]
        context,path=refs.identity(self.store,ref['event'])
        with patch('coordinator_runtime.custody.frozen_body',side_effect=AssertionError('blob read')):
            with self.assertRaisesRegex(Refusal,'direct artifact-source is unsupported'):
                operate(SimpleNamespace(command='artifact-source',attempt=context,path=path,delivery=None),self.store)

    def test_large_serial_real_consumers_grow_unique_bodies_and_immediate_links(self):
        from pathlib import Path
        job,attempt,ids=self.start([self.reports[0]])
        original=copy.deepcopy(self.store.event(ids[0]))
        job_prompt(self.store,job)
        first=self.finish(job,attempt,self.answer(job))
        work,worker=self.receive(first)
        job_prompt(self.store,work)
        answer=result(category='proposal')
        answer['findings']=[dict(analysis='New Work analysis retains earlier adverse values in separate custody'),
            dict(kind=refs.READ_KIND,sources=report_scope.source_pins(refs.inputs(self.store,work)),closure='whole',limits=[])]
        second=self.finish(work,worker,answer)
        self.assertEqual(second['body'],answer)
        self.assertEqual(second['report_custody']['model_result_sha256'],digest(answer))
        self.assertEqual(len(second['report_custody']['sources']),1)
        self.classify()
        nextjob=self.store.reserve()
        self.assertEqual(nextjob['task'],'work-integrator')
        nextattempt=self.store.start_job(nextjob['id'],nextjob['token'])
        nextjob=self.store.job(nextjob['id'])
        self.boards['Work'].bind_software_attempt(self.store,nextjob,nextattempt,None)
        prompt=job_prompt(self.store,nextjob)
        context=json.loads(prompt.split('TASK_CONTEXT=',1)[1].split('\n',1)[0])
        material=context['report_reference_inputs']['frozen_inputs']
        self.assertEqual(len(material),3)
        restored={w['report_origin']['event']:json.loads(Path(w['frozen_path']).read_bytes()) for w in material}
        self.assertEqual(restored[ids[0]],original)
        self.assertEqual(restored[first['id']],first)
        self.assertEqual(restored[second['id']],second)
        bodies=self.store.one('SELECT SUM(length(body)) AS n FROM artifact_blobs')['n']
        self.assertLess(bodies,len(encode(original).encode())+30000)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM artifact_custody WHERE kind=?",(refs.ORIGIN_KIND,))['n'],3)

    def test_wrapper_overflow_informative_handoff_preserves_original_and_reports_refusal(self):
        job,attempt,_=self.start()
        answer=self.answer(job,'PARTIAL')
        answer['findings'].append(dict(padding='Ω'*55000))
        answer.update(handoffs=[dict(recipient='Work',kind='result',text='Exact new synthetic handoff',ref=None,required='settled')],
                      no_handoff_reason=None)
        response=self.finish(job,attempt,answer)
        self.assertEqual(response['body']['original_result'],answer)
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']),answer)
        payloads=[json.loads(r['payload']) for r in self.store.rows('SELECT payload FROM outboxes WHERE job=?',(job['id'],))]
        self.assertTrue(any('actual report response/handoff/failure wrapper exceeds' in p.get('reason','') for p in payloads))
