"""Decision610: full API against real fictional claim/handoff/writer paths.

QA605-F1/F2 supplied the failures; these are candidate consequence checks, not
live reproduction or independent QA. All stores and principals are own fixtures.
"""
from contextlib import contextmanager
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

import test_collected_report593 as reports
from support import queued
from test_software_consumption import fixture_actor
from coordinator_runtime import metadata_lookup, processing
from coordinator_runtime.contracts import Refusal, encode, ident
from coordinator_runtime.dispatcher import Dispatcher


class DiagnosticAttribution610(unittest.TestCase):
    def setUp(self):
        self.fixture = reports.Reports('runTest')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.store = self.fixture.store
        select = processing.select

        def selected(store, boards, selection):
            selection = copy.deepcopy(selection)
            selection['metadata_lookup'] = {
                'tasks': ['work-proposer'], 'authority': 'Fictional Decision610 metadata only',
                'max_points': 16, 'max_bytes': 65536}
            return select(store, boards, selection)

        with patch.object(processing, 'select', side_effect=selected):
            self.fixture.processing_mode()
        self.key = self.fixture.key
        self.controller = self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',
                              (self.controller, self.key, 'owned', 1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
                              (self.controller, self.key, 'fictional-no-endpoint', 'serving', 1000., None, 'fixture'))
        args = ['post', '--session', self.fixture.actor, '--topic', 'fixture', '--kind', 'finding',
                '--text', 'Fictional existing a requires metadata interpretation',
                '--to', self.fixture.config['roles']['Work']['owner']]
        with self.fixture.substrate.database(self.fixture.board_path) as conn, fixture_actor(
                self.fixture.substrate, self.fixture.actor):
            self.fixture.substrate.post(conn, self.fixture.substrate.parser().parse_args(args))
        self.event = self.fixture.boards['Work'].scan(self.store)[0]
        queued(self.store, self.event, {'event_id': self.event['id'], 'task': 'work-proposer',
                                      'package': None, 'reason': 'Fictional fresh classification'})
        self.claimed = metadata_lookup.claim(self.store)
        self.assertIsNotNone(self.claimed, 'real metadata claim required; no vacuous positive')
        self.assertEqual(self.claimed[0], self.event['id'])
        self.attempt = self.claimed[1]
        self.assertIsNone(self.store.attempt(self.attempt)['begin'])
        metadata_lookup.authorize(self.store, self.store.attempt(self.attempt))
        self.store.processing.authorize(self.store.attempt(self.attempt))
        self.store.authorize_launch(self.attempt)  # Real read-only pre-handoff fence, no launch.

    @contextmanager
    def changed(self, table, field, key, **values):
        before = self.store.one('SELECT * FROM '+table+' WHERE '+field+'=?', (key,))
        def update(data):
            self.store.db.execute('UPDATE '+table+' SET '+','.join(k+'=?' for k in values)+' WHERE '+field+'=?',
                                  (*(data[k] for k in values), key))
        update(values)
        try:
            yield
        finally:
            update(before)

    def diagnostic(self):
        before = tuple(self.store.db.iterdump())
        statements = []
        self.store.db.set_trace_callback(statements.append)
        writes = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                  sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_TRANSACTION}
        self.store.db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in writes else sqlite3.SQLITE_OK)
        try:
            return processing.source_diagnostics(self.store, self.fixture.boards, self.key, self.event['id'])
        finally:
            self.store.db.set_authorizer(None)
            self.store.db.set_trace_callback(None)
            self.assertEqual(tuple(self.store.db.iterdump()), before)
            self.assertTrue(statements)
            self.assertTrue(all(s.lstrip().upper().startswith('SELECT') for s in statements), statements)

    def detail(self):
        if not self.store.one('SELECT event FROM input_dependencies WHERE event=?', (self.event['id'],)):
            metadata_lookup.dependency(self.store, self.event['id'], 'mapping',
                                       Refusal('original metadata handoff binding changed'), self.attempt)
        return self.diagnostic()['dependency']['detail']

    def test_real_claim_preserves_matching_current_context_without_execution_claim(self):
        detail = self.detail()
        self.assertEqual(detail['attempt'], self.attempt)
        self.assertEqual(detail['attempt_scope'], 'current-handoff-context-observed')
        self.assertEqual(self.diagnostic()['mapping']['attempt_scope'], 'current-handoff-context-observed')
        self.assertIsNone(self.store.attempt(self.attempt)['begin'])
        self.assertFalse(self.diagnostic()['processing_complete'])

    def test_QA605_F1_processing_capability_and_lookup_bindings_are_not_current_by_join(self):
        row = self.store.attempt(self.attempt)
        missing = json.loads(row['detail']); missing.pop('processing_capability')
        wrong = {**json.loads(row['detail']), 'processing_capability': ident()}
        cases = [('attempts', 'id', self.attempt, {'detail': encode(v)}) for v in (missing, wrong)]
        cases += [('input_lookups', 'attempt', self.attempt, {field: ident()})
                  for field in ('capability', 'source_hash')]
        snapshot = json.loads(self.store.one('SELECT snapshot FROM input_lookups WHERE attempt=?', (self.attempt,))['snapshot'])
        stale = copy.deepcopy(snapshot)
        stale['work-proposer']['binding']['enrollment'] = 'old-fictional-epoch'
        cases += [('input_lookups', 'attempt', self.attempt, {'snapshot': encode(stale)})]
        for table, field, key, values in cases:
            with self.subTest(table=table, values=values), self.changed(table, field, key, **values):
                with self.assertRaises(Refusal):
                    self.store.authorize_launch(self.attempt)
                detail = self.detail()
                self.assertEqual(detail['attempt'], self.attempt, 'truthful structural identity retained')
                self.assertEqual(detail['attempt_scope'], 'structurally-linked-currentness-unknown')
        self.assertEqual(self.detail()['attempt_scope'], 'current-handoff-context-observed')

    def test_actual_enrollment_epoch_change_disagrees_with_handoff_and_stays_observational(self):
        enrollment = self.store.enrollment('Work')
        with self.changed('enrollments', 'role', 'Work', cutover=enrollment['cutover']+1):
            with self.assertRaises(Refusal):
                self.store.authorize_launch(self.attempt)
            self.assertEqual(self.detail()['attempt_scope'], 'structurally-linked-currentness-unknown')
        self.assertEqual(self.detail()['attempt_scope'], 'current-handoff-context-observed')

    def test_QA605_F2_actual_writer_never_exports_unmatched_controller_content(self):
        # Authentic writer, not a hand-constructed public projection.
        queue = self.store.one('SELECT id,task FROM queue WHERE event=?', (self.event['id'],))
        base = {'dependency': 'input mapping awaits original collected upstream processing',
                'capability': self.key, 'source_hash': self.store.one('SELECT hash FROM events WHERE id=?',
                                                                    (self.event['id'],))['hash'],
                'queue': queue['id'], 'task': queue['task']}
        for controller in ('FICTIONAL_HOSTILE_CONTROLLER610', {'body': 'FICTIONAL_NESTED_CONTROLLER610'},
                           ident(), '', None, 12, ['FICTIONAL_LIST610']):
            with self.subTest(controller=controller):
                stored = {**base, 'controller': controller}
                self.store.record_operational_error(self.event['id'], stored, 'Work', 'local-integration-dependency')
                view = self.diagnostic()
                self.assertFalse(view['reservation']['available'])
                self.assertIsNone(view['reservation']['controller'])
                self.assertNotIn('FICTIONAL_', encode(view))
                self.assertEqual(json.loads(self.store.one('SELECT detail FROM operational_errors WHERE subject=?',
                                                           (self.event['id'],))['detail']), stored)
        self.store.record_operational_error(self.event['id'], {**base, 'controller': self.controller},
                                            'Work', 'local-integration-dependency')
        view = self.diagnostic()['reservation']
        self.assertTrue(view['available'])
        self.assertTrue(view['same_controller'])
        self.assertEqual(view['controller'], self.controller)
        for raw in ('not-json-FICTIONAL610', 'null', '[]', '12'):
            with self.subTest(raw=raw), self.changed('operational_errors', 'subject', self.event['id'], detail=raw):
                view = self.diagnostic()['reservation']
                self.assertFalse(view['available'])
                self.assertIsNone(view['controller'])
        self.store.record_operational_error(self.event['id'], {'dependency': base['dependency']},
                                            'Work', 'local-integration-dependency')
        legacy = self.diagnostic()['reservation']
        self.assertTrue(legacy['available'])
        self.assertIsNone(legacy['controller'])
        self.assertIsNone(legacy['same_controller'])
        self.assertIn('currentness unknown', legacy['meaning'])

    def test_refused_full_API_paths_are_SELECT_only_and_preserve_originals(self):
        cases = [('processing_capabilities', 'id', self.key, {'revoked': 1001.}),
                 ('service_runs', 'controller', self.controller, {'state': 'stopped'}),
                 ('events', 'id', self.event['id'], {'hash': 'fictional-changed-hash'})]
        for table, field, key, values in cases:
            with self.subTest(table=table), self.changed(table, field, key, **values):
                with self.assertRaises(Refusal):
                    self.diagnostic()

    def test_real_scheduler_reservation_refusal_still_has_current_controller(self):
        # The metadata lookup still has no resolution, so the real scheduler
        # retains the queued source and writes its actual reservation refusal.
        dispatcher = Dispatcher(self.store, models=object(), boards=self.fixture.boards)
        with dispatcher.phase('schedule_job'):
            dispatcher.schedule_job()
        self.assertFalse(dispatcher.active)
        self.assertEqual(dispatcher.phase_errors, {})
        view = self.diagnostic()['reservation']
        self.assertTrue(view['available'])
        self.assertTrue(view['same_controller'])
        self.assertTrue(view['still_queued'])


if __name__ == '__main__':
    unittest.main()
