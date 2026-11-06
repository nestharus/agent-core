"""Producer regression tests in fresh positive-mount fiction only.

Run with /fixtures writable and the public SDK mounted /sdk. Model answers,
principals and native turn receipts are authored fiction, never independent QA
or a native encounter. Existing eight duties and seven Work targets remain.
"""
import asyncio
import copy
import json
from pathlib import Path
import unittest

import _receiving485_fixtures as f
from coordinator_runtime import branches, local_integration as local
from coordinator_runtime import processing, reviews, review_returns, service, software
from coordinator_runtime.contracts import Refusal, digest, encode


class ReportTransport(f.FictionalNativeTransport):
    partial = True

    async def call(self, *args, **kwargs):
        code, receipt, raw = await super().call(*args, **kwargs)
        answer = json.loads(raw)
        answer['semantic'] = 'PARTIAL' if self.partial else 'DONE'
        answer['report'] = 'Mira: independent dissent; Chen: distinct counterevidence; U17: unknown owner.'
        answer['coverage']['core_files_not_read'] = ['unavailable-core.py']
        answer['coverage']['limits'] = ['Unexamined core and original source limitations retained']
        return code, receipt, encode(answer)


class ReportModels(f.NativeModels):
    async def run(self, store, attempt, prompt, spec, schema):
        a = store.attempt(attempt)
        e = store.event(a['event']) if a['event'] else None
        if a['kind'] == 'classifier' and e['kind'] == 'response':
            self.t.initial[e['id']] = 'reviews-integrator' if e['role'] == 'Reviews' else 'work-proposer'
        out = await super().run(store, attempt, prompt, spec, schema)
        if a['kind'] == 'task':
            j = store.job(a['job'])
            if j['task'] == 'reviews-integrator':
                out['result']['category'] = getattr(self.t, 'report_category', 'consolidated')
            out['result']['findings'] = [
                {'source': store.event(m['event']), 'hash': m['hash']}
                for m in json.loads(j['members'])]
        return out


class Reports(unittest.TestCase):
    setUp = f.Native.setUp
    setup = f.Native.setup
    post = f.Native.post
    git = f.Native.git
    start_auto = f.Native.start_auto
    init_native = f.Native.init_native
    source_event = f.Native.source_event
    drain = f.Native.drain
    phase = f.Native.phase
    until = f.Native.until

    def configure_fixture(self):
        f.Native.configure_fixture(self)
        self.method = Path('/method/unified-reviewer.prompt.md')
        for task in self.config['tasks'].values():
            task['templates'] = [str(self.method)]
        for task in self.config['local_integration']['tasks'].values():
            task['method'] = str(self.method)
        self.config['tasks']['reviews-integrator']['responses'].update(
            scope=['work-proposer'], blocker=['work-proposer'])

    def configure_selection(self, selection):
        original_method = self.method
        self.method = self.area / 'method.md'
        try:
            f.Native.configure_selection(self, selection)
        finally:
            self.method = original_method
        selection['service']['report_tasks'] = ['reviews-integrator']
        policy = selection['service']['reviews']['reviews-proposer']
        policy['method'] = str(self.method)
        policy['method_closure'] = 'unified-definitions-v1'
        policy['method_files'] = reviews.method_files(str(self.method), policy['method_closure'])

    def source(self, partial=True):
        self.init_native()
        self.models = ReportModels(self)
        self.transport = ReportTransport()
        self.transport.partial = partial
        self.dispatch = service.Dispatcher(self.store, self.boards, self.models, self.transport)
        self.e = self.source_event()
        self.initial[self.e['id']] = 'reviews-proposer'
        asyncio.run(self.phase('schedule_classifications'))
        job = self.store.reserve()
        policy = self.store.processing.current()[1]['service']['reviews']['reviews-proposer']
        selected = branches.review_policy(self.store, job, policy, self.e['body']['review'])
        self.history = Path(selected['components']['component']['history'])
        self.history.parent.mkdir(parents=True, exist_ok=True)
        self.prefix = b'Original prior history: Lin remains distinct; U17 remains unknown.\n'
        self.history.write_bytes(self.prefix)
        attempt = self.store.start_job(job['id'], job['token'])
        asyncio.run(self.dispatch.execute_review(job, attempt, self.e['body']['review']))
        self.original = self.store.job(job['id'])
        self.attempt = self.store.attempt(attempt)
        self.report = self.store.event(digest({'incomplete_ordinary_review': attempt})) if partial else None
        return self.report

    def flow(self, category='consolidated'):
        self.report_category = category
        self.source()
        before = digest(self.config)
        targets = {str(p): p.read_bytes() for p in map(Path, self.targets)}
        asyncio.run(self.until(lambda: self.store.one(
            "SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt "
            "WHERE j.task='work-proposer' AND a.collected IS NOT NULL"), n=20))
        self.assertEqual(len(self.config['tasks']), 8)
        self.assertEqual(len(self.targets), 7)
        self.assertEqual(digest(self.config), before)
        self.assertEqual(targets, {str(p): p.read_bytes() for p in map(Path, self.targets)})
        for task in ['reviews-integrator', 'work-proposer']:
            job = self.store.one('SELECT * FROM jobs WHERE task=?', (task,))
            a = self.store.attempt(job['active_attempt'])
            self.assertIsNotNone(a['collected'])
            scope = local.scope_for(self.store, job)
            self.assertEqual(scope['lane'], 'anchored')
            bindings = [b for key in scope['reads'] for b in local.point_definitions(self.store)[key]['bindings']]
            self.assertEqual({b['native'] for b in bindings}, {'branch', 'review'})
            result = json.loads(a['result'])
            for finding in result['findings']:
                self.assertEqual(finding['source'], self.store.event(finding['source']['id']))
                self.assertEqual(finding['hash'], digest(finding['source']))
            self.assertIn('unavailable-core.py', encode(result))
            self.assertIn('independent dissent', encode(result))
        self.assertEqual(self.store.job(self.original['id'])['state'], 'held')
        self.assertIsNone(software.clean_processing(self.store, self.store.job(self.original['id'])))
        self.assertFalse(self.store.execution_complete(self.store.job(self.original['id'])))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.e['id'],))['processed_at'])
        self.assertEqual(self.store.attempt(self.attempt['id']), self.attempt)
        self.assertTrue(self.history.read_bytes().startswith(self.prefix))
        self.assertEqual(self.store.one('SELECT state FROM review_contexts')['state'], 'live')
        self.assertEqual(len(self.transport.calls), 1)
        self.assertEqual(self.attempt['cleanup'], 'continuing-context-held')

    def test_partial_reaches_real_local_native_mapping_and_Work(self):
        self.flow()

    def test_scope_return_reaches_Work_through_sole_integrator(self):
        self.flow('scope')

    def test_blocker_return_reaches_Work_through_sole_integrator(self):
        self.flow('blocker')

    def test_full_uses_unchanged_clean_path(self):
        self.source(partial=False)
        asyncio.run(self.until(lambda: self.store.one(
            "SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt "
            "WHERE j.task='work-proposer' AND a.collected IS NOT NULL"), n=20))
        self.assertEqual(self.store.rows('SELECT * FROM review_report_returns'), [])
        self.assertTrue(software.clean_processing(self.store, self.store.job(self.original['id'])))
        self.assertEqual(len(self.transport.calls), 2)
        self.assertIsNotNone(local.scope_for(self.store, self.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")))

    def test_envelope_substitution_and_business_routes_refuse(self):
        event = self.source()
        changes = [lambda e: e.update(source_job='unknown-original'),
                   lambda e: e.update(source_attempt='stale-attempt'),
                   lambda e: e.update(author='other-collector'),
                   lambda e: e.update(source_members=[]),
                   lambda e: e.update(branch_binding='unrelated-branch'),
                   lambda e: e.update(allowed_tasks=['branch-proposer']),
                   lambda e: e['body'].update(status='DONE'),
                   lambda e: e['body']['full_original_outcome']['result'].update(unknowns=[]),
                   lambda e: e['body']['full_original_call'].update(collector='substituted')]
        for change in changes:
            forged = copy.deepcopy(event)
            change(forged)
            with self.assertRaises(Refusal):
                review_returns.proof(self.store, forged, 'reviews-integrator')
        for task in ['work-proposer', 'branch-proposer', 'qa-execution']:
            with self.assertRaises(Refusal):
                review_returns.proof(self.store, event, task)
        invented = copy.deepcopy(event)
        invented['id'] = 'message-authored-report'
        self.assertIsNone(review_returns.proof(self.store, invented, 'reviews-integrator'))
        self.store.ingest(invented)
        with self.assertRaises(Refusal):
            local.input_authority(self.store, invented, 'reviews-integrator', 'pkg')

    def test_once_only_emission_and_collection(self):
        event = self.source()
        outcome = event['body']['full_original_outcome']
        counts = {t: len(self.store.rows('SELECT * FROM '+t)) for t in ['events','attempts','review_report_returns']}
        self.dispatch.review_failure_return(self.original, self.attempt['id'], outcome)
        self.assertEqual(counts, {t: len(self.store.rows('SELECT * FROM '+t)) for t in counts})
        self.assertEqual(self.store.event(event['id']), event)
        with self.assertRaises(Refusal):
            self.store.collect(self.attempt['id'], outcome)
        changed = copy.deepcopy(outcome)
        changed['detail']['unobserved-new-claim'] = True
        with self.assertRaises(Refusal):
            self.dispatch.review_failure_return(self.original, self.attempt['id'], changed)
        self.assertEqual(self.store.event(event['id']), event)

    def test_existing_unreceipted_input_cannot_be_regranted(self):
        event = self.source()
        # Deliberate newly owned historical-shape fault, never an old store.
        self.store.db.execute('DELETE FROM review_report_returns WHERE event=?', (event['id'],))
        with self.assertRaises(Refusal):
            self.dispatch.review_failure_return(self.original, self.attempt['id'],
                                                event['body']['full_original_outcome'])
        self.assertEqual(self.store.rows('SELECT * FROM review_report_returns'), [])
        self.assertEqual(self.store.event(event['id']), event)

    def test_current_revocation_preserves_custody_and_refuses_mapping(self):
        event = self.source()
        with f.actor(self.boards['Work'].store, self.config['roles']['Work']['owner']):
            processing.revoke(self.store, self.boards, self.key)
        with self.assertRaises(Refusal):
            local.input_authority(self.store, event, 'reviews-integrator', 'pkg')
        self.assertEqual(self.store.attempt(self.attempt['id']), self.attempt)
        self.assertEqual(self.store.job(self.original['id'])['state'], 'held')
        self.assertIsNone(self.store.one("SELECT id FROM jobs WHERE task='reviews-integrator'"))

    def test_withdrawn_package_permission_refuses_before_native_acquisition(self):
        event = self.source()
        admission = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('pkg',))['receipt'])
        admission['task_scopes']['reviews-proposer']['read_roots'] = []
        self.store.admit('pkg', self.config['roles']['Branch']['owner'], admission)
        with self.assertRaises(Refusal):
            local.input_authority(self.store, event, 'reviews-integrator', 'pkg')
        self.assertEqual(self.store.attempt(self.attempt['id']), self.attempt)

    def test_capture_call_collector_frozen_member_and_receipt_truth_refuse(self):
        event = self.source()
        probes = [
            ("UPDATE attempts SET capture='unknown' WHERE id=?", (self.attempt['id'],)),
            ("UPDATE attempts SET collected=NULL WHERE id=?", (self.attempt['id'],)),
            ("UPDATE attempts SET controller='other' WHERE id=?", (self.attempt['id'],)),
            ("UPDATE review_calls SET packet='{}' WHERE attempt=?", (self.attempt['id'],)),
            ("UPDATE review_history_commits SET state='prepared' WHERE attempt=?", (self.attempt['id'],)),
            ("UPDATE review_call_contexts SET context='{}' WHERE attempt=?", (self.attempt['id'],)),
            ("UPDATE events SET hold='unknown-source' WHERE id=?", (self.e['id'],)),
            ("UPDATE jobs SET members='[]' WHERE id=?", (self.original['id'],)),
            ("UPDATE review_report_returns SET payload_hash='substituted' WHERE event=?", (event['id'],))]
        for sql, args in probes:
            self.store.db.execute('SAVEPOINT fault512')
            try:
                self.store.db.execute(sql, args)
                with self.assertRaises(Refusal):
                    local.input_authority(self.store, event, 'reviews-integrator', 'pkg')
            finally:
                self.store.db.execute('ROLLBACK TO fault512')
                self.store.db.execute('RELEASE fault512')

    def test_receipt_does_not_release_write_or_unknown_scope_fences(self):
        event = self.source()
        row = {'task':'reviews-integrator', 'role':'Reviews', 'phase':'integrator'}
        members = [{'event':event['id']}]
        read = {'lane':'anchored', 'reads':['known-point'], 'writes':[]}
        self.assertTrue(review_returns.observes_source(self.store, row, members, read, self.original))
        self.assertFalse(review_returns.observes_source(self.store, row, members,
                         {**read, 'writes':['known-point']}, self.original))
        self.assertFalse(review_returns.observes_source(self.store, row, members, read,
                         {**self.original, 'id':'unrelated-held-Source'}))
        self.assertFalse(review_returns.observes_source(self.store, row,
                         members+[{'event':self.e['id']}], read, self.original))


if __name__ == '__main__':
    unittest.main(verbosity=2)
