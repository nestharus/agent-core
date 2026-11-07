"""Owned fictional report/local overlap; no provider or actual state access.

Principals, Board membership, collection testimony and SDK answers are fiction.
The real reservation, dispatcher, authority and whole-return checks run against
new isolated journals. Producer tests establish no independent acceptance.
"""
import asyncio
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

import test_report_batches50109 as batches
import test_local444 as native_cases
from support import collect, event, ident, result
from coordinator_runtime import local_integration as local, local_native, prospective
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import job_prompt


class ReportLocal(batches.ReportBatches):
    def configure(self):
        super().configure()
        task = self.config['tasks']['reviews-integrator']
        point = dict(kind='item', line='Reviews', incarnation='fictional-delivery',
                     resources=[], protected=[], writable=[])
        self.config['local_integration'] = dict(max_inflight=8, points={}, tasks={
            'reviews-integrator': dict(capacity=5, discovery_batch=4, points=[],
                authority='Fictional native point authority, never report authority',
                method=task['templates'][0], lookup_scopes=[
                    dict(prefix='branch:', member_field=None,
                         point={**point, 'bindings':[dict(native='branch', id='$source')]}),
                    dict(prefix='review:', member_field=None,
                         point={**point, 'bindings':[dict(native='review', component='$source')]})])})
        if 'shared_local' in self._testMethodName:
            self.config['local_integration']['max_inflight'] = 1
            self.config['local_integration']['tasks']['work-proposer'] = dict(capacity=5, discovery_batch=4,
                points=[], authority='Fictional other local residency', method=self.config['tasks']['work-proposer']['templates'][0])

    def record(self):
        # Retain only our new fictional fixture evidence; no process inventory.
        (self.area/'reached.json').write_text(encode(dict(methods=self.methods))+'\n')

    def no_native(self):
        stack = self.enterContext(patch.multiple(local_native,
            authorize=forbidden('native authorization'),
            authorize_scope=forbidden('native scope'), snapshot=forbidden('native snapshot')))
        return stack

    def assert_refused(self):
        try:
            self.assertIsNone(self.store.reserve())
        except Refusal:
            pass

    def start(self, job):
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        self.boards['Reviews'].bind_software_attempt(self.store, job, attempt, None)
        local.prepare_input_basis(self.store, job, attempt, self.config['tasks'][job['task']])
        return job, attempt

    def test_dispatcher_conserves_whole_reports_without_native_context(self):
        self.no_native()
        ids = self.admit(self.reports)
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertIsNone(local.scope_for(self.store, job))
        answer = result(category='consolidated')
        from coordinator_runtime.report_scope import conserved_inputs
        exact = conserved_inputs(self.store, job)
        answer['findings'] = [dict(collected_reports=exact)]
        prompts = []

        async def fictional_sdk(attempt, prompt, spec, schema):
            self.store.authorize_launch(attempt)
            prompts.append(prompt)
            context = json.loads(prompt.split('TASK_CONTEXT=', 1)[1].split('\n', 1)[0])
            self.assertEqual(context['collected_reports'], exact)
            self.assertIsNone(context['local_integration'])
            self.assertIsNone(context['admission'])
            self.assertEqual(context['staged_targets'], {})
            self.store.begin(attempt, dict(fictional_sdk=True))
            self.store.session(attempt, ident())
            return dict(exit=0, capture='complete', cleanup='done', result=answer, error=None,
                        detail=dict(tool_completion=dict(complete=True, items=[], nonzero_completions=[])))

        attempt = self.store.start_job(job['id'], job['token'])
        with patch.object(self.runtime, 'run_model', side_effect=fictional_sdk):
            asyncio.run(self.runtime.execute(job['id'], attempt))
        self.assertEqual(len(prompts), 1)
        finished = self.store.job(job['id'])
        self.assertIsNotNone(finished['response'])
        response = self.store.event(finished['response'])
        self.assertEqual(response['body'], answer)
        self.assertEqual(response['source_members'], json.loads(job['members']))
        self.assertNotIn('branch_binding', response)
        self.assertNotIn('integration', response)
        for table in ('local_bases', 'local_commits', 'local_lookup_points', 'input_resolutions',
                      'branch_contexts', 'review_contexts', 'ordinary_runs', 'ordinary_resources', 'file_publications'):
            self.assertEqual(self.store.rows('SELECT * FROM '+table), [], table)
        self.assertEqual(self.store.enrollment('Reviews')['legacy_hold'], 'Reviews UNKNOWN')
        self.assertEqual([self.store.event(e)['body']['original'] for e in ids], self.reports)

    def test_central_single_capacity_is_preserved_with_local_capacity_five(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        second = self.admit([self.reports[1]])[0]
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?', (second,))['state'], 'queued')
        self.complete(job)
        self.assertIsNotNone(self.store.reserve())

    def test_shared_local_residency_capacity_is_preserved(self):
        self.admit([self.reports[0]])
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects) "
                              "VALUES('other-local','Work','proposer','work-proposer','[]','fictional-other',?,0,'reserved','none')", (ident(),))
        self.assertIsNone(self.store.reserve())
        outcome = self.store.one('SELECT predicate,outcome FROM reservation_outcomes')
        self.assertEqual(outcome, dict(predicate='local-capacity', outcome='false'))
        self.assertEqual(self.store.job('other-local')['state'], 'reserved')

    def test_source_and_frozen_permission_failures_remain_queued(self):
        self.no_native()
        key = self.admit([self.reports[0]])[0]
        original = self.store.event(key)
        mutations = [
            ('events', 'hold', 'fictional privacy hold'),
            ('processing_source_positions', 'position', 0),
        ]
        for table, field, changed in mutations:
            column = 'id' if table == 'events' else 'event'
            old = self.store.one('SELECT '+field+' FROM '+table+' WHERE '+column+'=?', (key,))[field]
            with self.subTest(table=table, field=field):
                self.store.db.execute('UPDATE '+table+' SET '+field+'=? WHERE '+column+'=?', (changed, key))
                self.assert_refused()
                self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])
                self.store.db.execute('UPDATE '+table+' SET '+field+'=? WHERE '+column+'=?', (old, key))
        for field in ('source_hash', 'receipt_hash', 'capability'):
            with self.subTest(immutable_permission=field), self.assertRaises(sqlite3.IntegrityError):
                self.store.db.execute('UPDATE processing_report_inputs SET '+field+'=? WHERE event=?',
                                      ('foreign-permission', key))
        self.assertEqual(self.store.event(key), original)
        self.assertIsNotNone(self.store.reserve())

    def test_post_reservation_hold_and_source_change_refuse_start(self):
        key = self.admit([self.reports[0]])[0]
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.store.set_hold(key, 'fictional original hold')
        with self.assertRaises(Refusal): self.store.start_job(job['id'], job['token'])
        self.store.set_hold(key, None)
        original = self.store.event(key)
        changed = copy.deepcopy(original)
        changed['body']['original']['history'] += ' unauthorized revision'
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(changed), digest(changed), key))
        with self.assertRaises(Refusal): self.store.start_job(job['id'], job['token'])
        self.assertEqual(self.store.rows('SELECT * FROM attempts WHERE kind=\'task\''), [])

    def test_replaced_epoch_cannot_adopt_frozen_report_job(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        selection = json.loads(self.store.one('SELECT selection FROM prospective_authorities WHERE id=?',
                                             (self.epoch['id'],))['selection'])
        for field in ('grantor', 'job_birth'): selection.pop(field)
        selection['authority'] += ' replacement'
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        prospective.select(self.store, self.issuer, selection)
        with self.assertRaises(Refusal): self.store.start_job(job['id'], job['token'])

    def test_replaced_epoch_refuses_prepared_prompt_and_whole_return(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        job, attempt = self.start(job)
        from coordinator_runtime.report_scope import complete_return, conserved_inputs
        answer = complete_return(conserved_inputs(self.store, job))
        selection = json.loads(self.store.one('SELECT selection FROM prospective_authorities WHERE id=?',
                                             (self.epoch['id'],))['selection'])
        for field in ('grantor', 'job_birth'): selection.pop(field)
        selection['authority'] += ' replacement after preparation'
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        prospective.select(self.store, self.issuer, selection)
        with self.assertRaises(Refusal): job_prompt(self.store, job)
        collect(self.store, attempt, answer, tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        with self.assertRaises(Refusal): self.store.finish_job(job['id'], job['token'])
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_revoked_epoch_refuses_prompt_launch_and_result(self):
        self.no_native()
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        job, attempt = self.start(job)
        self.assertIsNone(local.context(self.store, job))
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        with self.assertRaises(Refusal): job_prompt(self.store, job)
        with self.assertRaises(Refusal): self.store.authorize_launch(attempt)
        collect(self.store, attempt, result(category='consolidated'),
                tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        with self.assertRaises(Refusal): self.store.finish_job(job['id'], job['token'])
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_missing_whole_return_is_refused(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        job, attempt = self.start(job)
        collect(self.store, attempt, result(category='consolidated'),
                tool_completion=dict(complete=True, items=[], nonzero_completions=[]))
        with self.assertRaisesRegex(Refusal, 'whole original'): self.store.finish_job(job['id'], job['token'])
        self.assertIsNone(self.store.job(job['id'])['response'])

    def test_method_configuration_mismatch_does_not_refresh_job(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.config['tasks']['reviews-integrator']['templates'] = [str(self.area/'unselected-method.md')]
        with self.assertRaises(Refusal): self.store.start_job(job['id'], job['token'])

    def test_policy_expiry_refuses_even_without_legacy_hold(self):
        self.admit([self.reports[0]])
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.store.db.execute("UPDATE enrollments SET legacy_hold=NULL WHERE role='Reviews'")
        expires = self.selection['service']['legacy_resources']['Reviews']['reviews_report']['expires']
        with patch.object(self.store, 'clock', return_value=expires+1):
            with self.assertRaises(Refusal): self.store.start_job(job['id'], job['token'])

    def test_task_selection_alone_does_not_grant_report_route(self):
        # Ordinary ingress still needs its real point mapping. Merely naming
        # the same selected task, or copying an attributed body, grants none.
        self.store.db.execute("UPDATE enrollments SET legacy_hold=NULL WHERE role='Reviews'")
        source = event(self.config, 'ordinary-native-input', 'Reviews', 'reviews-integrator')
        source['body'] = dict(kind='attributed-report', original=self.reports[0], native_owner_execution=False)
        with self.assertRaises(Refusal): self.store.ingest(source)
        self.post('Reviews', 'reviews-integrator', None)
        self.assertIsNone(self.store.reserve())
        self.assertIn('missing metadata', self.store.one('SELECT detail FROM operational_errors')['detail'])
        self.assertEqual(self.store.rows('SELECT * FROM local_jobs'), [])


def forbidden(label):
    def call(*args, **kwargs):
        raise AssertionError('unexpected '+label+' in finite report route')
    return call


class NativeBoundaries(unittest.TestCase):
    """Native branch/reviewer originals keep their existing point checks."""
    # Reuse only the owned fixture operations. The original protocol tests
    # remain separate checks, including their separately retained failures.
    setUp = native_cases.NativeProtocol.setUp
    tearDown = native_cases.NativeProtocol.tearDown
    authority = native_cases.NativeProtocol.authority
    event = native_cases.NativeProtocol.event
    receipt = native_cases.NativeProtocol.receipt
    classify = native_cases.NativeProtocol.classify
    fixture_configuration = native_cases.NativeProtocol.fixture_configuration
    boards = native_cases.NativeProtocol.boards
    fresh = native_cases.NativeProtocol.fresh
    configure = native_cases.NativeProtocol.configure
    repository = native_cases.NativeProtocol.repository
    review_selection = native_cases.NativeProtocol.review_selection

    def test_native_review_with_report_text_still_needs_real_point_anchor(self):
        self.review_selection()
        source = dict(id='ordinary-review-report-text', role='Reviews', recipient='fictional-logical-Reviews',
                      kind='board', post=11, package=None, allowed_tasks=['rp'],
                      body=dict(kind='attributed-report', review=dict(component='component'),
                                native_owner_execution=False))
        self.runtime.ingest(source)
        self.classify(source, 'rp')
        with patch.object(local_native, 'snapshot', side_effect=forbidden('unanchored native acquisition')):
            self.assertIsNone(self.runtime.reserve())
        self.assertEqual(self.runtime.rows('SELECT * FROM local_jobs'), [])
        self.assertIn('missing metadata', self.runtime.one('SELECT detail FROM operational_errors')['detail'])
        self.assertEqual(self.runtime.one('SELECT state FROM review_contexts')['state'], 'live')

    def test_native_review_anchor_keeps_native_basis_and_collector_fence(self):
        self.review_selection()
        source = dict(id='ordinary-review-anchored', role='Reviews', recipient='fictional-logical-Reviews',
                      kind='board', post=11, package=None, allowed_tasks=['rp'], body=dict(review=dict(component='component')),
                      integration=dict(reads=['review'], writes=[], versions=dict(review=local.version(self.runtime, 'review', {}))))
        self.runtime.ingest(source)
        self.classify(source, 'rp')
        job = self.runtime.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(local.scope_for(self.runtime, job)['lane'], 'anchored')
        attempt = self.runtime.start_job(job['id'], job['token'])
        job = self.runtime.job(job['id'])
        local.prepare_input_basis(self.runtime, job, attempt, self.runtime.config['tasks']['rp'])
        self.assertEqual(local.context(self.runtime, job)['basis']['scope']['lane'], 'anchored')
        self.runtime.db.execute("UPDATE review_contexts SET collector='fictional-foreign' WHERE component='component'")
        with self.assertRaisesRegex(Refusal, 'collector'): local.current_job(self.runtime, job)
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'), [])
