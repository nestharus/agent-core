"""Isolated synthetic software receipts; no provider/native qualification.

Only worker UUID validation is a declared seam (native fields remain NULL).
All source, collection, capability, shape and transaction guards run normally.
"""
import hashlib
import json
import unittest
from unittest.mock import patch

import test_processing206 as fixtures
from coordinator_runtime import processing
from coordinator_runtime.contracts import Refusal, digest, encode


class MarkerTests(unittest.TestCase):
    setUp = fixtures.ProtocolTests.setUp
    tearDown = fixtures.ProtocolTests.tearDown
    authority = fixtures.ProtocolTests.authority
    event = fixtures.ProtocolTests.event
    classify = fixtures.ProtocolTests.classify
    control = fixtures.ProtocolTests.control

    def receipt(self, source):
        return dict(source_hash=digest(source), mode='control', task='@control', package=None,
                    related_event=None, related_job=None,
                    reason='No second review, new work, native procedure or acceptance',
                    evidence=['Fictional exact board status and classifier ACK observation'],
                    remaining_obligations=['Old report and holds remain with their owners',
                                           'Classifier ACK done is distinct from processed control'])

    def original(self):
        source = self.event('marker789', 'Reviews', 'ri', queued=False)
        self.classify(source, '@control')
        self.runtime.ack_state(source['id'], 'done')
        attempt, result = self.control(source)
        return source, attempt, result

    def apply(self, source, attempt):
        # Synthetic worker identity seam only; this is not a real model return.
        with patch('coordinator_runtime.processing.canonical_uuid', return_value=None):
            return processing.apply_control(self.runtime, source['id'], attempt)

    def test_collected_marker_derives_only_task_preserves_raw_and_old_obligations(self):
        source, attempt, result = self.original()
        raw = self.runtime.attempt(attempt)
        receipt = json.loads(result['decision_json'])
        with self.assertRaisesRegex(Refusal, 'processed control is board input only'):
            self.runtime.validate_input_selection(source, receipt)
        resolution = self.apply(source, attempt)
        self.assertEqual(resolution['receipt'], {**receipt, 'task': None})
        self.assertEqual(self.runtime.attempt(attempt), raw)
        self.assertEqual(resolution['receipt']['remaining_obligations'], receipt['remaining_obligations'])
        proof = resolution['prior']['software_processing']
        self.assertFalse(proof['native_owner_receipt'])
        derivation = proof['syntax_derivation']
        self.assertEqual(derivation['version'], 'software-control-queue-marker-v1')
        self.assertEqual(derivation['raw_result_sha256'], hashlib.sha256(raw['result'].encode()).hexdigest())
        self.assertEqual(derivation['source_hash'], digest(source))
        self.assertEqual(derivation['controller'], self.runtime.controller)
        self.assertEqual(derivation['capability'], self.key)
        self.assertEqual(derivation['binding'], json.loads(raw['binding']))
        returned = self.runtime.event(self.runtime.one('SELECT response FROM processing_control_returns')['response'])
        self.assertEqual(returned['body']['actual_worker_return'], result)
        self.assertFalse(returned['body']['native_owner_receipt'])
        self.runtime.complete_events()
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?', (source['id'],))['processed_at'])
        self.assertEqual(self.runtime.one('SELECT ack FROM events WHERE id=?', (source['id'],))['ack'], 'done')
        self.assertEqual(self.runtime.rows('SELECT * FROM jobs'), [])
        self.assertEqual(self.runtime.rows('SELECT * FROM admissions'), [])

    def test_refuses_invalid_binding_source_collection_and_semantics(self):
        source, attempt, result = self.original()
        original = self.runtime.attempt(attempt)
        cases = [('controller', 'foreign-controller'), ('collected', None), ('capture', 'partial'),
                 ('exit', 1), ('error', 'fictional failure'), ('binding', encode({'model': 'other'}))]
        for column, value in cases:
            with self.subTest(column=column):
                self.runtime.db.execute('UPDATE attempts SET '+column+'=? WHERE id=?', (value, attempt))
                with self.assertRaises(Refusal):
                    self.apply(source, attempt)
                self.runtime.db.execute('UPDATE attempts SET '+column+'=? WHERE id=?', (original[column], attempt))
        for semantic in ('UNKNOWN', 'PARTIAL', 'FAILED', 'legacy DONE'):
            changed = {**result, 'semantic': semantic}
            self.runtime.db.execute('UPDATE attempts SET result=? WHERE id=?', (encode(changed), attempt))
            with self.assertRaises(Refusal):
                self.apply(source, attempt)
        self.runtime.db.execute('UPDATE attempts SET result=? WHERE id=?', (original['result'], attempt))
        self.runtime.set_hold(source['id'], 'fictional retained source hold')
        with patch.object(self.runtime, 'event', side_effect=AssertionError('held body acquired')):
            with self.assertRaises(Refusal):
                self.apply(source, attempt)
        self.runtime.set_hold(source['id'], None)
        self.runtime.db.execute('UPDATE processing_controls SET source_hash=?', ('wrong',))
        with self.assertRaises(Refusal):
            self.apply(source, attempt)
        self.assertIsNone(self.runtime.input_resolution(source['id']))

    def test_malformed_fields_other_modes_and_native_claims_are_not_normalized(self):
        source, attempt, result = self.original()
        original = self.runtime.attempt(attempt)
        receipt = json.loads(result['decision_json'])
        changes = [dict(task='ri'), dict(package='invented'), dict(related_event='invented'),
                   dict(related_job='invented'), dict(mode='route', task='@control'),
                   dict(mode='coalesce'), dict(mode='notification'),
                   dict(mode='notification', task=None, remaining_obligations=[],
                        evidence=['Invented notification coverage']), dict(native_owner_receipt=True)]
        for change in changes:
            with self.subTest(change=change):
                malformed = {**receipt, **change}
                changed = {**result, 'decision_json': encode(malformed)}
                self.runtime.db.execute('UPDATE attempts SET result=? WHERE id=?', (encode(changed), attempt))
                with self.assertRaises(Refusal):
                    self.apply(source, attempt)
                self.assertIsNone(self.runtime.input_resolution(source['id']))
        self.runtime.db.execute('UPDATE attempts SET result=? WHERE id=?', (original['result'], attempt))
        genuine_route = {**receipt, 'mode': 'route', 'task': 'ri'}
        if hasattr(processing, 'control_receipt'):
            unchanged, derivation = processing.control_receipt(self.runtime, source['id'], original, result, genuine_route)
            self.assertEqual(unchanged, genuine_route)
            self.assertIsNone(derivation)

    def test_wrong_queue_capability_and_source_bytes_refuse(self):
        source, attempt, result = self.original()
        for change in (dict(task='@unresolved'), dict(state='done'), dict(phase='proposer')):
            column, value = next(iter(change.items()))
            queue = self.runtime.one('SELECT * FROM queue WHERE event=?', (source['id'],))
            self.runtime.db.execute('UPDATE queue SET '+column+'=? WHERE event=?', (value, source['id']))
            with self.assertRaises(Refusal):
                self.apply(source, attempt)
            self.runtime.db.execute('UPDATE queue SET '+column+'=? WHERE event=?', (queue[column], source['id']))
        self.runtime.db.execute('UPDATE events SET payload=? WHERE id=?', (encode({**source, 'body': 'changed'}), source['id']))
        with self.assertRaises(Refusal):
            self.apply(source, attempt)
        self.runtime.db.execute('UPDATE events SET payload=? WHERE id=?', (encode(source), source['id']))
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE id=?', (self.key,))
        with self.assertRaises(Refusal):
            self.apply(source, attempt)
        self.assertIsNone(self.runtime.input_resolution(source['id']))

    def test_native_owner_and_forged_derived_evidence_are_not_rewritten(self):
        source, attempt, result = self.original()
        receipt = json.loads(result['decision_json'])
        with self.assertRaisesRegex(Refusal, 'processed control is board input only'):
            self.runtime.resolve_input(source['id'], self.runtime.enrollment('Reviews')['owner'], receipt)
        forged = {**receipt, 'task': None, 'evidence': ['Invented notification coverage or native receipt']}
        with patch('coordinator_runtime.processing.canonical_uuid', return_value=None):
            with self.assertRaisesRegex(Refusal, 'differs from its original'):
                self.runtime.processing.control_proof(source['id'], attempt, forged)
        raw = self.runtime.attempt(attempt)
        wrong = {**result, 'decision_json': encode({**receipt, 'source_hash': 'wrong'})}
        self.runtime.db.execute('UPDATE attempts SET result=? WHERE id=?', (encode(wrong), attempt))
        with self.assertRaises(Refusal):
            self.apply(source, attempt)
        self.assertIsNone(self.runtime.input_resolution(source['id']))
        self.runtime.db.execute('UPDATE attempts SET result=? WHERE id=?', (raw['result'], attempt))
