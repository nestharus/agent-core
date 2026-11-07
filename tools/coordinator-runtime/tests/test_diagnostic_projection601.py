"""Decision601: the full public diagnostic boundary, using own fictional stores.

QA596-D1's executed failure supplies the red signal. These tests carry its
writer/API path forward, without providers, native processes or live Boards.
Expected non-disclosure/conservation comes from ACTUAL-WORK-DECISION.json.
"""
from contextlib import contextmanager
import json
import unittest

import test_collected_report593 as reports
from coordinator_runtime import metadata_lookup, processing
from coordinator_runtime.contracts import Refusal, SOL, encode
from coordinator_runtime.dispatcher import Dispatcher


class DiagnosticProjection(unittest.TestCase):
    def setUp(self):
        self.fixture = reports.Reports('runTest')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.store = self.fixture.store
        self.fixture.processing_mode()
        _, self.producer, self.event, _ = self.fixture.producer()
        self.key = self.fixture.key
        self.controller = self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',
                              (self.controller, self.key, 'owned', 1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
                              (self.controller, self.key, 'fictional-no-socket', 'serving', 1000., None, 'fixture'))

    @contextmanager
    def changed(self, table, keyfield, key, **values):
        before = self.store.one('SELECT * FROM '+table+' WHERE '+keyfield+'=?', (key,))
        def update(row):
            self.store.db.execute('UPDATE '+table+' SET '+','.join(k+'=?' for k in values)+' WHERE '+keyfield+'=?',
                                  (*(row[k] for k in values), key))
        update(values)
        try:
            yield
        finally:
            update(before)

    def diagnostic(self):
        # The entire own runtime journal, including raw historical errors,
        # collectors, holds, grants and accounting, must be unchanged by reads.
        before = tuple(self.store.db.iterdump())
        try:
            return processing.source_diagnostics(self.store, self.fixture.boards, self.key, self.event['id'])
        finally:
            self.assertEqual(tuple(self.store.db.iterdump()), before)

    def dependency(self, reason, stage='mapping', attempt=None):
        metadata_lookup.dependency(self.store, self.event['id'], stage, Refusal(reason), attempt)
        return self.diagnostic()['dependency']

    def test_QA596_D1_full_return_withholds_writer_exception_and_preserves_history(self):
        with self.changed('attempts', 'id', self.producer['active_attempt'], capture='incomplete'):
            dispatcher = Dispatcher(self.store, models=object(), boards=self.fixture.boards)
            with dispatcher.phase('schedule_job'):
                dispatcher.schedule_job()
            self.assertEqual(dispatcher.phase_errors, {})
            self.assertEqual(dispatcher.active, set())
            before = self.diagnostic()
            self.assertTrue(before['reservation']['still_queued'])
            self.assertTrue(before['reservation']['same_controller'])
            self.assertFalse(before['processing_complete'])
            sentinel = 'FICTIONAL_SOURCE_BODY_SENTINEL596'
            view = self.dependency(sentinel)
            after = self.diagnostic()
            self.assertNotIn(sentinel, encode(after))
            self.assertFalse(view['detail']['reason_known'])
            self.assertEqual(view['stage'], 'mapping')
            self.assertIn('outside bounded public vocabulary', view['detail']['dependency'])
            stored = self.store.one('SELECT detail FROM input_dependencies WHERE event=?', (self.event['id'],))
            self.assertEqual(json.loads(stored['detail'])['dependency'], sentinel)
            self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',
                                             (self.event['id'],))['processed_at'])
            self.assertFalse(after['processing_complete'])

    def test_known_public_reasons_and_unknown_suffix_are_discriminated(self):
        cases = (
            ('observation', 'lookup parent requires its explicitly selected stable member representation'),
            ('locator', 'locator hints need their actual complete original software collection; no replay'),
            ('mapping', 'unresolved locator relationships cannot authorize new business'),
        )
        for stage, reason in cases:
            with self.subTest(stage=stage):
                view = self.dependency(reason, stage)
                self.assertEqual(view['stage'], stage)
                self.assertEqual(view['detail']['dependency'], reason)
                self.assertTrue(view['detail']['reason_known'])
                self.assertEqual(view['observed'], 1000.)
                unknown = self.dependency(reason+' FICTIONAL_BODY601', stage)
                self.assertFalse(unknown['detail']['reason_known'])
                self.assertNotIn('FICTIONAL_BODY601', encode(self.diagnostic()))

    def test_unadmitted_stage_attempt_and_extra_detail_never_become_public(self):
        self.dependency('FICTIONAL_ERROR601', 'FICTIONAL_STAGE601', 'FICTIONAL_ATTEMPT601')
        row = self.store.one('SELECT detail FROM input_dependencies WHERE event=?', (self.event['id'],))
        detail = {**json.loads(row['detail']), 'extra': {'body': 'FICTIONAL_EXTRA601'}}
        with self.changed('input_dependencies', 'event', self.event['id'], detail=encode(detail)):
            view = self.diagnostic()
            self.assertNotIn('FICTIONAL_', encode(view))
            self.assertEqual(view['dependency']['stage'], 'unknown')
            self.assertIsNone(view['dependency']['detail']['attempt'])
            self.assertEqual(view['dependency']['detail']['attempt_scope'], 'unavailable-current-source-controller')
        # Malformed/legacy storage is an unknown, not raw JSON or an API crash.
        for detail in ('FICTIONAL_NOT_JSON601', 'null', '[]', '{"dependency":{"body":"FICTIONAL_NESTED601"}}'):
            with self.subTest(detail=detail), self.changed('input_dependencies', 'event', self.event['id'], detail=detail):
                view = self.diagnostic()
                self.assertNotIn('FICTIONAL_', encode(view))
                self.assertFalse(view['dependency']['detail']['reason_known'])

    def test_attempt_requires_real_same_source_controller_and_metadata_kind(self):
        with self.store.tx():
            attempt = self.store._attempt('input-mapping', self.event['id'], None, SOL, '.codex5')
        view = self.dependency('unknown fixture refusal', attempt=attempt)
        self.assertEqual(view['detail']['attempt'], attempt)
        # Original601 passed this synthetic structural join. No lookup record
        # or metadata delegation was claimed, so current handoff is unknown.
        self.assertEqual(view['detail']['attempt_scope'], 'structurally-linked-currentness-unknown')
        for field, value in (('controller', 'FICTIONAL_OTHER601'), ('event', json.loads(self.producer['members'])[0]['event']),
                             ('kind', 'classifier')):
            with self.subTest(field=field), self.changed('attempts', 'id', attempt, **{field: value}):
                view = self.diagnostic()['dependency']['detail']
                self.assertIsNone(view['attempt'])
                self.assertEqual(view['attempt_scope'], 'unavailable-current-source-controller')
        view = self.dependency('unknown fixture refusal', stage='locator', attempt=attempt)
        self.assertIsNone(view['detail']['attempt'])
        view = self.dependency('unknown fixture refusal')
        self.assertEqual(view['detail']['attempt_scope'], 'unrecorded')

    def test_dependency_requires_exact_source_hash_capability_and_current_controller(self):
        self.dependency('FICTIONAL_BODY601')
        for field in ('capability', 'source_hash', 'controller'):
            with self.subTest(field=field), self.changed('input_dependencies', 'event', self.event['id'],
                                                        **{field: 'FICTIONAL_WRONG601'}):
                self.assertIsNone(self.diagnostic()['dependency'])
        # No fallback to a dependency belonging to another event.
        with self.changed('input_dependencies', 'event', self.event['id'], event=json.loads(self.producer['members'])[0]['event']):
            self.assertIsNone(self.diagnostic()['dependency'])

    def test_full_API_retains_currentness_and_controller_refusals(self):
        self.dependency('FICTIONAL_BODY601')
        with self.changed('processing_capabilities', 'id', self.key, revoked=1001.):
            with self.assertRaises(Refusal):
                self.diagnostic()
        with self.changed('service_runs', 'controller', self.controller, state='stopped'):
            with self.assertRaisesRegex(Refusal, 'one current original service controller required'):
                self.diagnostic()
        with self.changed('events', 'id', self.event['id'], hash='wrong-current-hash'):
            with self.assertRaises(Refusal):
                self.diagnostic()
        boundary = json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',
                                             (self.key,))['selection'])['basis']['event_boundary']
        with self.changed('processing_source_positions', 'event', self.event['id'], position=boundary):
            with self.assertRaisesRegex(Refusal, 'exact current prospective source frontier'):
                self.diagnostic()


if __name__ == '__main__':
    unittest.main()
