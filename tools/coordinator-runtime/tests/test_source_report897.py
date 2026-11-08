"""Source/report integration with fictional native transport and owned journals.

The optional exact released answer is data only: its original caller is never
attached, replayed or credited to the fictional invocation in this test.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import _receiving485_fixtures as native
import test_unpackaged_native889 as existing
from coordinator_runtime import local_integration, prospective, review_returns, reviews
from coordinator_runtime.contracts import Refusal, digest, encode


def startup_return():
    return dict(semantic='PARTIAL', summary='Startup acquisition incomplete; procedure unread',
        report=dict(attribution={'reviewer': 'fictional original root'},
            material_actually_read=[dict(source='permitted history', range='[0,36000)')],
            missing_material=['remaining history', 'method definitions', 'pinned source'],
            dissent={'unread': True, 'preserved': ['earlier adverse evidence']}),
        history_entry=dict(stage='architecture', status='PARTIAL',
            resume=dict(same_live_root_required=True, next_offset=36000),
            outstanding='Finish permitted acquisition before architecture analysis'),
        coverage=dict(families={f: 'unread' for f in reviews.FAMILIES},
            core_files_not_read=['fictional-core.py'], observations=[], answered_ids=[],
            limits=['end_of_material not reached; no acceptance']), stage='architecture')


def fixture_case():
    class Case(existing.Unpackaged889):
        def configure_selection(self, selected):
            super().configure_selection(selected)
            selected['service']['report_tasks'] = ['reviews-integrator']
            # The full native-return exception requires DONE architecture plus
            # complete stages. This fixture selects the existing informative
            # route with explicitly disjoint legacy resources instead.
            record = selected['service']['legacy_resources']['Reviews']
            record.pop('native_review_return')
            record['unbounded'] = False
    return Case(methodName='runTest')


class SourceReport897(unittest.TestCase):
    def setUp(self):
        self.f = fixture_case()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def source(self, returned=None, *, raw=None, damage=None):
        answer = raw if raw is not None else encode(returned or startup_return())
        original = native.FictionalNativeTransport.call
        async def call(transport, *args, **kwargs):
            code, receipt, _ = await original(transport, *args, **kwargs)
            if damage:
                damage(receipt)
            return code, receipt, answer
        with patch.object(native.FictionalNativeTransport, 'call', call):
            f = self.f
            f.init_native()
            prospective.select(f.store, f.config['roles']['Work']['owner'], dict(
                configuration=digest(f.config), authority='Fictional current finite report rights',
                expires=f.store.clock()+600, processing_capability=f.key,
                grants={r: f.store.enrollment(r)['grant_id'] for r in f.config['roles']},
                tasks={n: dict(task_hash=digest(t), software_handoffs={}, ordinary_effects=False)
                       for n, t in f.config['tasks'].items()}))
            f.e = f.source_event()
            f.initial[f.e['id']] = 'reviews-proposer'
            asyncio.run(f.phase('schedule_classifications'))
            job = f.store.reserve()
            self.assertEqual(job['task'], 'reviews-proposer')
            attempt = f.store.start_job(job['id'], job['token'])
            asyncio.run(f.dispatch.execute_review(job, attempt, f.e['body']['review']))
            f.original, f.a = f.store.job(job['id']), f.store.attempt(attempt)
            f.returned = f.store.event(digest({'incomplete_ordinary_review': attempt}))
            f.row = dict(role='Reviews', phase='integrator', task='reviews-integrator',
                         package=None, event=f.returned['id'])
            f.record = f.store.processing.current()[1]['service']['legacy_resources']['Reviews']
        self.raw = answer
        self.call = self.f.store.one('SELECT * FROM review_calls WHERE attempt=?', (self.f.a['id'],))
        self.assertEqual(self.call['answer'], answer)
        self.assertEqual(json.loads(self.call['receipt'])[0]['full_answer'], answer)
        self.assertEqual(json.loads(self.call['receipt'])[0]['actual_END'], 0)
        self.assertEqual(len(self.f.transport.calls), 1)
        self.assertIsNotNone(self.f.a['ended'])
        self.assertIsNotNone(self.f.a['collected'])
        return self.f.a

    def assert_informative(self):
        f = self.f
        self.assertIsNone(f.a['error'], f.a['error'])
        self.assertEqual(f.a['capture'], 'complete')
        self.assertEqual(f.a['semantic'], 'PARTIAL')
        self.assertEqual(f.original['state'], 'held')
        self.assertEqual(self.call['state'], 'collected')
        self.assertEqual(f.returned['body']['status'], 'PARTIAL')
        self.assertEqual(f.returned['body']['full_original_call']['answer'], self.raw)
        self.assertTrue(review_returns.proof(f.store, f.returned, 'reviews-integrator'))
        # The return value tracks attributed-report ancestry, not admission.
        # A genuine Source informative return needs no such external ancestry.
        local_integration.input_authority(f.store, f.returned, 'reviews-integrator', None)
        history = f.store.one('SELECT * FROM review_history_commits WHERE attempt=?', (f.a['id'],))
        self.assertEqual(history['state'], 'applied')
        self.assertEqual(json.loads(Path(history['path']).read_text())['turns'][0]['full_answer'], self.raw)
        frozen = copy.deepcopy(self.call)
        asyncio.run(f.until(lambda: f.store.one(
            "SELECT id FROM jobs WHERE task='reviews-integrator' AND response IS NOT NULL"), n=18))
        consumer = f.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        response = f.store.event(consumer['response'])
        self.assertEqual(response['body']['findings'][0]['source'], f.returned)
        self.assertEqual(f.store.one('SELECT * FROM review_calls WHERE attempt=?', (f.a['id'],)), frozen)
        self.assertEqual(f.store.job(f.original['id'])['state'], 'held')
        self.assertEqual(len(f.transport.calls), 1)  # No automatic Source continuation/replay.

    def test_structured_startup_partial_integrates_with_whole_original(self):
        self.source()
        self.assert_informative()

    @unittest.skipUnless(os.environ.get('SOURCE897_RELEASED_FAILURE'), 'exact released failure not selected')
    def test_exact_released_answer_integrates_without_original_replay(self):
        released = json.loads(Path(os.environ['SOURCE897_RELEASED_FAILURE']).read_text())
        raw = released['original_review_calls'][0]['full_answer']
        self.assertIsInstance(json.loads(raw)['report'], dict)
        self.assertIsInstance(json.loads(raw)['history_entry'], dict)
        self.source(raw=raw)
        self.assert_informative()

    def test_string_partial_preserves_original_wire(self):
        returned = startup_return()
        returned.update(report='Whole report: procedure unread', history_entry='PARTIAL; retain original')
        self.source(returned)
        self.assert_informative()

    def test_arbitrary_nested_lists_are_preserved(self):
        returned = startup_return()
        returned.update(report=[{'any key': [1, False, None, {'Ω': 'dissent'}]}],
                        history_entry=[{'unread': ['method', 'core']}])
        self.source(returned)
        self.assert_informative()

    def test_invalid_reports_preserve_failure_and_raw_answer(self):
        returned = startup_return()
        returned['report'] = None
        self.source(returned)
        self.assertIn('full reviewer report', self.f.a['error'])
        self.assertEqual(self.f.a['capture'], 'incomplete')
        self.assertEqual(self.f.store.rows('SELECT * FROM review_history_commits'), [])
        self.assertEqual(self.f.store.rows('SELECT * FROM review_report_returns'), [])

    def test_oversize_utf8_structured_report_preserves_failure(self):
        returned = startup_return()
        returned['report'] = {'body': 'Ω' * (self.f.config['limits']['max_result_bytes']//2)}
        self.source(returned)
        self.assertIn('full reviewer report', self.f.a['error'])
        self.assertEqual(self.f.store.rows('SELECT * FROM review_report_returns'), [])

    def test_invalid_history_entry_preserves_failure(self):
        returned = startup_return()
        returned['history_entry'] = []
        self.source(returned)
        self.assertIn('full reviewer history_entry', self.f.a['error'])
        self.assertEqual(self.f.store.rows('SELECT * FROM review_history_commits'), [])

    def test_incomplete_coverage_still_refuses_structured_report(self):
        returned = startup_return()
        returned['coverage']['families'].pop('purpose')
        self.source(returned)
        self.assertIn('all nine actual families', self.f.a['error'])
        self.assertEqual(self.f.store.rows('SELECT * FROM review_report_returns'), [])

    def test_changed_run_still_refuses_without_history_or_integration_proof(self):
        self.source(damage=lambda receipt: receipt['transport']['attached'].update(run='foreign-run'))
        self.assertIn('original native call incomplete', self.f.a['error'])
        self.assertEqual(self.f.store.rows('SELECT * FROM review_history_commits'), [])
        self.assertEqual(self.f.store.rows('SELECT * FROM review_report_returns'), [])

    def test_forged_original_collector_cannot_acquire_informative_rights(self):
        self.source()
        self.assertIsNone(self.f.a['error'], self.f.a['error'])
        self.f.store.db.execute("UPDATE attempts SET controller='foreign' WHERE id=?", (self.f.a['id'],))
        with self.assertRaises(Refusal):
            review_returns.proof(self.f.store, self.f.returned, 'reviews-integrator')
        self.assertEqual(self.f.store.one('SELECT answer FROM review_calls WHERE attempt=?',
                                        (self.f.a['id'],))['answer'], self.raw)


class ReportText897(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('SOURCE897_RELEASED_FAILURE'), 'exact released failure not selected')
    def test_actual_receipt_keeps_collection_and_correlation_refusals(self):
        released = json.loads(Path(os.environ['SOURCE897_RELEASED_FAILURE']).read_text())
        original = released['original_review_calls'][0]
        receipt, raw = original['receipt'], original['full_answer']
        run = receipt['run']
        self.assertTrue(reviews.answered(0, receipt, raw, run, opening=True))
        self.assertFalse(reviews.answered(1, receipt, raw, run, opening=True))
        self.assertFalse(reviews.answered(True, receipt, raw, run, opening=True))
        changes = [lambda r: r.update(consumer_errors=['incomplete capture']),
                   lambda r: r['collection'].update(stdout_eof=False),
                   lambda r: r['collection'].update(exit=None),
                   lambda r: r['transport']['attached'].update(run='foreign'),
                   lambda r: r['transport']['attached'].update(backlog_dropped_total=1),
                   lambda r: r['turn']['turn_end'].update(input=1),
                   lambda r: r['turn'].update(admitted=False)]
        for change in changes:
            changed = copy.deepcopy(receipt)
            change(changed)
            self.assertFalse(reviews.answered(0, changed, raw, run, opening=True))
        self.assertEqual(receipt, original['receipt'])

    def test_bounded_text_and_arbitrary_json_containers(self):
        for value in ('  full report Ω  ', {'arbitrary': [False, None, {'Ω': 2}]}, ['unread', {'core': True}]):
            text = reviews.report_text(value, 'full reviewer report', 1024)
            self.assertEqual(text, value if isinstance(value, str) else encode(value))
        for value in (None, False, 1, '', ' ', {}, [], {'invalid': float('nan')}):
            with self.subTest(value=value), self.assertRaises(Refusal):
                reviews.report_text(value, 'full reviewer report', 1024)
        value = {'Ω': 'Ω'}
        size = len(encode(value).encode())
        self.assertEqual(reviews.report_text(value, 'report', size), encode(value))
        with self.assertRaises(Refusal):
            reviews.report_text(value, 'report', size-1)

    def test_prompt_names_string_contract_and_honest_partial(self):
        text = reviews.prompt({'method': '/method'}, {}, '/read-facade')
        self.assertIn('report and history_entry must be nonempty strings', text)
        self.assertIn('UTF-8 bytes', text)
        self.assertIn('Mark partial/unread work explicitly', text)


if __name__ == '__main__':
    unittest.main()
