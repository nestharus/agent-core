"""Fictional protocol tests in a positive-mount kernel read-only namespace.

No provider/Board operation or native identity is simulated. Native attempt
fields remain NULL. The explicitly patched control provenance seam tests local
transactions/consumer obligations, not a genuine successful worker encounter.
All fixtures and failed attempts remain retained under /fixtures.
"""
import errno
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_processing194 as earlier
from coordinator_runtime import processing, processing_admission
from coordinator_runtime.contracts import Refusal, SOL, classification, digest, encode
from coordinator_runtime.dispatcher import classifier_prompt
from coordinator_runtime.cleanup import eligible_event


class KernelIsolationTests(unittest.TestCase):
    def test_real_source_and_dependency_writes_are_kernel_denied(self):
        for source in (Path(__file__).resolve(), Path('/src/tools/direct-child/execution_pool.py')):
            self.assertTrue(source.is_file())
            self.assertTrue(os.statvfs(source).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as denied:
                os.open(source, os.O_WRONLY)  # No truncation or data write, even on an unexpected writable mount.
            self.assertEqual(denied.exception.errno, errno.EROFS)
        with (Path('/fixtures') / 'kernel-positive-writable.txt').open('a') as output:
            output.write('owned isolated output is writable\n')


class ProtocolTests(unittest.TestCase):
    setUp = earlier.CorrectionTests.setUp
    authority = earlier.CorrectionTests.authority
    event = earlier.CorrectionTests.event
    receipt = earlier.CorrectionTests.receipt
    classify = earlier.CorrectionTests.classify
    fixture_configuration = earlier.CorrectionTests.fixture_configuration
    boards = earlier.CorrectionTests.boards

    def tearDown(self):
        try:
            for attempt in self.runtime.rows('SELECT profile,session,turn FROM attempts'):
                self.assertEqual(attempt, {'profile': None, 'session': None, 'turn': None})
        finally:
            self.runtime.close()

    def test_null_package_qa_is_offered_control_routes_not_execution(self):
        source = self.event('fictional-qa-control', 'QA', 'qe', queued=False)
        prompt = classifier_prompt(source, self.runtime.config)
        choices = json.loads(prompt.split('ALLOWED_TASKS=', 1)[1].splitlines()[0])
        self.assertEqual(set(choices), {'@control', '@unresolved'})
        for route in choices:
            answer = {'event_id': source['id'], 'task': route, 'package': None, 'reason': 'fictional meaningful control'}
            self.assertEqual(classification(answer, source, self.runtime.config), answer)
        with self.assertRaises(Refusal):
            classification({**answer, 'task': 'qe'}, source, self.runtime.config)
        self.classify(source, '@control')
        self.assertEqual(self.runtime.one('SELECT state FROM queue')['state'], 'awaiting-owner')
        self.runtime.complete_events()
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events')['processed_at'])

    def test_real_package_choices_and_package_identity_remain_required(self):
        self.runtime.config['tasks']['qe']['authority'] = 'fictional bounded package execution'
        self.fixture_configuration()
        source = self.event('fictional-qa-execution', 'QA', 'qe', package='fictional-p', queued=False)
        self.assertIn('"qe":', classifier_prompt(source, self.runtime.config))
        answer = {'event_id': source['id'], 'task': 'qe', 'package': 'fictional-p', 'reason': 'actual declared package'}
        self.assertEqual(classification(answer, source, self.runtime.config), answer)
        with self.assertRaises(Refusal):
            classification({**answer, 'package': 'fictional-other'}, source, self.runtime.config)
        self.classify(source, 'qe')
        self.assertIsNone(self.runtime.reserve())  # Classification cannot mint admission.

    def control(self, source, semantic='DONE'):
        with self.runtime.tx():
            attempt = self.runtime._attempt('input-control', source['id'], None, SOL, None)
            self.runtime.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',
                                    (source['id'], self.key, attempt, digest(source)))
        result = {'semantic': semantic, 'summary': 'fictional interpretation, with no native read or acceptance',
                  'decision_json': encode(self.receipt(source))}
        self.runtime.begin(attempt, {'fixture': True})
        self.runtime.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
                                      'result': result, 'detail': {'tool_completion': {
                                          'complete': True, 'items': [], 'nonzero_completions': [], 'unknown_types': []}}})
        return attempt, result

    def test_control_wire_status_is_unambiguous_and_partial_is_never_success(self):
        self.assertEqual(processing.CONTROL_SCHEMA['properties']['semantic']['enum'], ['DONE', 'PARTIAL', 'FAILED', 'UNKNOWN'])
        source = self.event('fictional-control', 'QA', 'qe', queued=False)
        attempt, result = self.control(source)
        processing.validate_control_result(result, self.receipt(source))
        with self.assertRaisesRegex(Refusal, 'canonical UUID'):
            self.runtime.processing.control_proof(source['id'], attempt, self.receipt(source))
        for semantic in ('PARTIAL', 'FAILED', 'UNKNOWN'):
            with self.assertRaises(Refusal):
                processing.validate_control_result({**result, 'semantic': semantic}, self.receipt(source))
        with self.assertRaises(Refusal):
            processing.validate_control_result(result, None)

    def test_old_freetext_needs_exact_work_recognition_without_result_mutation(self):
        source = self.event('fictional-old-control', 'QA', 'qe', queued=False)
        attempt, result = self.control(source, 'CONTROL')
        original = self.runtime.attempt(attempt)
        with self.assertRaisesRegex(Refusal, 'genuine Work recognition'):
            self.runtime.processing.control_proof(source['id'], attempt, self.receipt(source))
        recognition = {'attempt': attempt, 'result_hash': digest(result),
                       'reason': 'fictional Work interprets this exact old status, not native consent',
                       'evidence': ['fictional original decision and summary read']}
        processing.validate_recognition(self.runtime, source['id'], attempt, recognition)
        with self.assertRaises(Refusal):
            processing.validate_recognition(self.runtime, source['id'], attempt, {**recognition, 'result_hash': 'changed'})
        self.assertEqual(self.runtime.attempt(attempt), original)

    def test_control_transaction_creates_one_work_return_and_consumer_blocks_completion(self):
        source = self.event('fictional-consumed-control', 'QA', 'qe', queued=False)
        attempt, result = self.control(source)
        original = self.runtime.attempt(attempt)
        # Explicit provenance seam: the NULL-native fixture cannot pass actual
        # worker UUID verification. No production worker identity is fabricated.
        with patch.object(self.runtime.processing, 'control_proof', return_value={'fixture_provenance_seam': True}):
            processing.apply_control(self.runtime, source['id'], attempt)
            processing.apply_control(self.runtime, source['id'], attempt)
        returned = self.runtime.one('SELECT * FROM processing_control_returns')
        response = self.runtime.event(returned['response'])
        self.assertEqual(response['body']['actual_worker_return'], result)
        self.assertEqual(self.runtime.attempt(attempt), original)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_control_returns')['n'], 1)
        self.assertTrue(self.runtime.processing.event(response))
        # Equal fixture timestamps intentionally permit either stable ID order.
        # Both still need actual fresh classifier commits before receipt.
        for _ in range(2):
            classifier, view = self.runtime.claim_classification()
            route = '@control' if view['id'] == source['id'] else 'wp'
            self.runtime.collect(classifier, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
                'result': {'event_id': view['id'], 'task': route, 'package': None, 'reason': 'fictional supplied meaning'}})
            self.runtime.commit_classification(classifier)
            self.runtime.ack_state(view['id'], 'internal')
        self.runtime.complete_events()
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?', (source['id'],))['processed_at'])
        self.assertIsNotNone(self.runtime.reserve())  # A real Work consumer reservation, not ACK-only processing.
        self.assertFalse(eligible_event(self.runtime, self.runtime.one('SELECT * FROM events WHERE id=?', (source['id'],))))

    def test_missing_return_consumer_rolls_back_resolution_but_keeps_original_worker(self):
        source = self.event('fictional-no-consumer', 'QA', 'qe', queued=False)
        attempt, _ = self.control(source)
        row = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))
        selection = json.loads(row['selection'])
        selection['tasks'].remove('wp')
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selection), self.key))
        original = self.runtime.attempt(attempt)
        with patch.object(self.runtime.processing, 'control_proof', return_value={'fixture_provenance_seam': True}):
            with self.assertRaisesRegex(Refusal, 'Work proposer consumer'):
                processing.apply_control(self.runtime, source['id'], attempt)
        self.assertIsNone(self.runtime.input_resolution(source['id']))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_control_returns')['n'], 0)
        self.assertEqual(self.runtime.attempt(attempt), original)

    def configure_admission(self, maximum=3, before=None):
        for task in ('bi', 'qe'):
            self.runtime.config['tasks'][task].update(require_package_scope=True, scope_roots=['/fixtures'],
                effect_authority={'read_roots': ['/fixtures'], 'write_roots': [], 'operations': ['read-source']})
        boards, conn = self.boards()
        if before:
            before()
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE revoked IS NULL')
        scope = {'cwd': str(self.directory), 'read_roots': [str(self.directory)], 'write_roots': [],
                 'procedure': str(self.directory / 'fictional-procedure.md'),
                 'resource_evidence': 'fictional pre-authorized read-only resource scope'}
        self.policy = {'authority': 'fictional Work delegated prospective software admission only', 'max_packages': maximum,
                       'scopes': {'fictional-new-work': {'submitters': ['fictional-author'], 'package_prefix': 'fictional-new-',
                            'task_scopes': {'bi': scope, 'qe': scope}, 'evidence': 'fictional bounded independent scope'}}}
        selection = {'basis': processing.basis(self.runtime, boards), 'authority': 'fictional continuing Act outcome',
                     'expires': 1060., 'retained_events': [], 'recover_controls': {}, 'future_intake': True,
                     'tasks': list(self.runtime.config['tasks']), 'max_starts': 100, 'max_shared_rows': 1000,
                     'max_shared_payload_bytes': 1048576, 'max_runtime_rows': 100, 'software_admission': self.policy}
        self.key = processing.select(self.runtime, boards, selection)['capability']
        self.runtime.processing = processing.Access(self.runtime, self.key, boards)
        return boards, conn

    def fresh(self, name, role='QA', **changes):
        event = {'id': name, 'role': role, 'recipient': 'fictional-logical-' + role, 'kind': 'board', 'post': 11,
                 'author': 'fictional-author', 'body': {'topic': 'fictional-new-work', 'text': 'fictional admitted work'},
                 'allowed_tasks': ['qe' if role == 'QA' else 'bi'], 'package': 'fictional-new-' + name, **changes}
        self.runtime.ingest(event)
        return event

    def test_software_admission_uses_real_selection_then_classifies_and_reserves_qa(self):
        boards, conn = self.configure_admission()
        source = self.fresh('qa')
        processing_admission.admit_pending(self.runtime)
        admission = self.runtime.one('SELECT * FROM admissions')
        self.assertEqual(admission['owner'], 'fictional-software-actor')
        self.assertIsNone(admission['accepted'])
        self.assertFalse(json.loads(admission['receipt'])['software_admission']['native_owner_consent'])
        self.assertTrue(processing_admission.admit(self.runtime, source['id'])['already_recorded'])
        self.classify(source, 'qe')
        job = self.runtime.reserve()
        self.assertEqual(job['package'], source['package'])
        self.assertEqual(job['role'], 'QA')
        self.assertTrue(all(row['revoked'] is not None for row in conn.execute('SELECT revoked FROM coordinator_grants_v1')))
        self.assertTrue(all(row['intake'] == 0 for row in self.runtime.rows('SELECT intake FROM enrollments')))
        self.assertEqual(self.runtime.event(source['id']), source)

    def test_envelope_does_not_mint_external_acceptance_or_clear_legacy_hold(self):
        self.configure_admission()
        self.runtime.db.execute("UPDATE enrollments SET legacy_hold='fictional original effect hold' WHERE role='Branch'")
        source = self.fresh('branch', 'Branch')
        processing_admission.admit(self.runtime, source['id'])
        self.classify(source, 'bi')
        self.assertIsNone(self.runtime.reserve())
        self.assertEqual(self.runtime.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'], 'fictional original effect hold')
        self.assertIsNone(self.runtime.one('SELECT accepted FROM admissions')['accepted'])

    def test_unauthorized_submitter_topic_namespace_hold_and_old_post_are_not_admission(self):
        self.configure_admission()
        for name, changes in [('author', {'author': 'fictional-foreign'}),
                              ('topic', {'body': {'topic': 'unselected'}}),
                              ('package', {'package': 'old-resource-renamed'})]:
            source = self.fresh(name, **changes)
            with self.assertRaises(Refusal):
                processing_admission.admit(self.runtime, source['id'])
        with self.assertRaises(Refusal):
            self.fresh('post', post=0)  # Outside intake selection, even before admission.
        source = self.fresh('held')
        self.runtime.set_hold(source['id'], 'fictional retained source hold')
        with self.assertRaises(Refusal):
            processing_admission.admit(self.runtime, source['id'])
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM admissions')['n'], 0)

    def test_capacity_and_existing_native_admission_are_not_silently_replaced(self):
        self.configure_admission(maximum=1)
        source = self.fresh('first')
        processing_admission.admit(self.runtime, source['id'])
        second = self.fresh('second')
        with self.assertRaisesRegex(Refusal, 'capacity exhausted'):
            processing_admission.admit(self.runtime, second['id'])
        third = self.fresh('existing')
        self.runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)', (third['package'], 'fictional-original-owner', '{}'))
        with self.assertRaisesRegex(Refusal, 'original authority'):
            processing_admission.admit(self.runtime, third['id'])
        self.assertEqual(self.runtime.one('SELECT owner FROM admissions WHERE package=?', (third['package'],))['owner'], 'fictional-original-owner')

    def test_new_admission_cannot_unlock_old_same_package_queue(self):
        old = self.event('fictional-old-source', 'QA', 'qe', package='fictional-new-new')
        self.configure_admission()
        source = self.fresh('new')
        processing_admission.admit(self.runtime, source['id'])
        self.assertFalse(processing_admission.permits(self.runtime, {'package': source['package'], 'event': old['id'], 'task': 'qe'}))
        self.assertTrue(processing_admission.permits(self.runtime, {'package': source['package'], 'event': source['id'], 'task': 'qe'}))
        with self.assertRaises(Refusal):
            processing_admission.admit(self.runtime, old['id'])

    def test_source_mutation_and_untyped_topic_cannot_supply_admission(self):
        self.configure_admission()
        changed = self.fresh('mutated')
        self.runtime.db.execute('UPDATE events SET payload=? WHERE id=?',
                               (encode({**changed, 'body': {**changed['body'], 'text': 'changed fixture'}}), changed['id']))
        with self.assertRaises(Refusal):
            processing_admission.admit(self.runtime, changed['id'])
        self.fresh('untyped-topic', body={'topic': ['fictional-new-work']})
        processing_admission.admit_pending(self.runtime)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM admissions')['n'], 0)

    def test_changed_scope_symlink_and_revocation_refuse_before_admission(self):
        self.configure_admission()
        source = self.fresh('changed')
        # Change the selected cwd on disk; the admitted paths must be checked
        # again on application, without following this fixture-owned symlink.
        target = self.directory / 'selected-child'
        target.mkdir()
        task_scope = self.policy['scopes']['fictional-new-work']['task_scopes']['qe']
        task_scope['read_roots'] = [str(target)]
        selected = json.loads(self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))['selection'])
        selected['software_admission'] = self.policy
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selected), self.key))
        target.rename(self.directory / 'conserved-selected-child')  # Preserve fixture bytes.
        target.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(Refusal):
            processing_admission.admit(self.runtime, source['id'])
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE id=?', (self.key,))
        with self.assertRaises(Refusal):
            processing_admission.admit(self.runtime, source['id'])
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM admissions')['n'], 0)

    def test_public_parent_admission_command(self):
        from coordinator_runtime.cli import parser
        args = parser().parse_args(['processing-admit-source', 'fictional-capability', 'fictional-source'])
        self.assertEqual((args.capability, args.event), ('fictional-capability', 'fictional-source'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
