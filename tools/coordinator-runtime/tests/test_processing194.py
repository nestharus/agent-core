"""Owned fictional protocol controls; NULL native fields, no provider workers.

Requires positive-mount kernel isolation; retains every SQLite fixture. Board
membership/transport and successful source processing are explicit test seams,
never evidence of actual worker efficacy, native consent or live capacity.
"""
from contextlib import contextmanager
import json
import sqlite3
import unittest
from unittest.mock import patch

import test_processing188 as fixtures
from test_retained168 import BoardShell
from coordinator_runtime import processing
from coordinator_runtime.contracts import Refusal, digest, encode, SOL


class FictionalBoard(processing.ProcessingBoard):
    def __init__(self, runtime, role, conn, identity):
        self.runtime, self.config, self.role = runtime, runtime.config, role
        self.selected = self.config['roles'][role]
        self.store, self.conn, self.identity = BoardShell(), conn, identity

    @contextmanager
    def opened(self, **kwargs):
        yield self.conn  # Fictional membership only; production binding logic runs.

    def _delivery_grant(self, conn, runtime, outbox):
        return self._grant(conn, runtime), {'session': None}  # Native field absent.


class CorrectionTests(unittest.TestCase):
    setUp = fixtures.EngineTests.setUp
    tearDown = fixtures.EngineTests.tearDown
    authority = fixtures.EngineTests.authority
    event = fixtures.EngineTests.event

    def fixture_configuration(self):
        row = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))
        selection = json.loads(row['selection'])
        selection['basis']['configuration'] = digest(self.runtime.config)
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selection), self.key))

    def boards(self):
        runtime = self.runtime
        runtime.config['software_delegation'] = {'grantor': 'fictional-issuer', 'authority': 'fictional-prior-authority'}
        for role, selected in runtime.config['roles'].items():
            selected.update(board_id='fictional-board', routes=[t for t, v in runtime.config['tasks'].items() if v['role'] == role])
        path = self.directory / 'board.sqlite3'
        conn = sqlite3.connect(path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        conn.executescript('''
          CREATE TABLE coordinator_grants_v1(id,board_id,role,owner,actor,runtime,runtime_dev,runtime_ino,issued_by,authority,revoked);
          CREATE TABLE coordinator_software_grants_v1(grant_id,configuration);
          CREATE TABLE coordinator_software_deliveries_v1(delivery PRIMARY KEY,source_grant,receiver_grant,event,payload);
          CREATE TABLE coordinator_deliveries_v1(id PRIMARY KEY,grant_id,actor,producer,recipient,payload,notice,post,transport_started,kind);
          CREATE TABLE notification_outbox(notification_id PRIMARY KEY,route,delivery_state);
          CREATE TABLE posts(seq PRIMARY KEY);
        ''')
        stat = runtime.path.stat()
        boards = {}
        for role, selected in runtime.config['roles'].items():
            runtime.db.execute('INSERT INTO cursors VALUES(?,0)', (role,))
            conn.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                         ('fictional-grant-' + role, 'fictional-board', role, selected['owner'], runtime.config['actor'],
                          str(runtime.path), stat.st_dev, stat.st_ino, 'fictional-issuer', 'fictional-prior-authority', 'fictional-revocation'))
            conn.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?)', ('fictional-grant-' + role, digest(runtime.config)))
            boards[role] = FictionalBoard(runtime, role, conn, (path.stat().st_dev, path.stat().st_ino))
        self.fixture_configuration()  # Fixture setup only, before production selection.
        return boards, conn

    def bind(self, boards, requests=()):
        # Production selection/issuance executes; issuer authentication remains
        # the explicit fictional BoardShell seam, never native consent.
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE revoked IS NULL')
        selection = {'basis': processing.basis(self.runtime, boards), 'authority': 'fictional exact correction test',
                     'expires': 1060., 'retained_events': [e['id'] for e in self.events], 'recover_controls': {},
                     'future_intake': True, 'tasks': list(self.runtime.config['tasks']), 'max_starts': 100,
                     'max_shared_rows': 1000, 'max_shared_payload_bytes': 1048576, 'max_runtime_rows': 100,
                     'owner_operations': list(requests)}
        self.key = processing.select(self.runtime, boards, selection)['capability']
        self.runtime.processing = processing.Access(self.runtime, self.key, boards)

    def receipt(self, source, mode='control', remaining=()):
        return {'source_hash': digest(source), 'mode': mode, 'task': None, 'package': None,
                'related_event': None, 'related_job': None, 'reason': 'fictional exact input disposition',
                'evidence': ['fictional source meaning'], 'remaining_obligations': list(remaining)}

    def classify(self, event, task):
        attempt, view = self.runtime.claim_classification()
        self.assertEqual(view['id'], event['id'])
        self.assertIsNone(self.runtime.attempt(attempt)['session'])
        self.assertIsNone(self.runtime.attempt(attempt)['profile'])
        self.runtime.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
                                      'result': {'event_id': event['id'], 'task': task, 'package': view.get('package'),
                                                 'reason': 'fictional direct classification response'}})
        return self.runtime.commit_classification(attempt)

    def test_retained_derived_control_and_unresolved_preserve_original_and_debt(self):
        source = self.event('fictional-retained', 'Work', 'wp', queued=False)
        self.authority()  # Now an exact retained source, not prospective-only.
        self.runtime.resolve_input(source['id'], 'fictional-logical-Work', self.receipt(source, remaining=['actual external holder still needed']))
        self.classify(source, '@control')
        self.assertEqual(self.runtime.one('SELECT state FROM queue')['state'], 'awaiting-owner')
        self.runtime.resolve_input(source['id'], 'fictional-logical-Work', self.receipt(source, remaining=['different unresolved authority']))
        self.classify(source, '@unresolved')
        self.assertEqual(self.runtime.one('SELECT state FROM queue')['state'], 'awaiting-owner')
        self.assertEqual(self.runtime.event(source['id']), source)
        self.assertEqual(self.runtime.one('SELECT hash FROM events')['hash'], digest(source))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM outboxes')['n'], 0)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events')['processed_at'])
        with self.assertRaises(Refusal):
            self.runtime.processing.event({**source, 'body': 'tampered original'})

    def handoff(self):
        boards, conn = self.boards()
        self.runtime.config['tasks']['wi']['software_handoffs'] = {'Branch': ['bi']}
        # Bind the fixture grant to the final immutable task configuration.
        conn.execute('UPDATE coordinator_software_grants_v1 SET configuration=?', (digest(self.runtime.config),))
        self.fixture_configuration()
        self.event('fictional-work', 'Work', 'wi')
        self.bind(boards)
        job = self.runtime.reserve()
        with self.runtime.tx():
            attempt = self.runtime._attempt('task', None, job['id'], SOL, None)
        self.runtime.db.execute('UPDATE jobs SET active_attempt=? WHERE id=?', (attempt, job['id']))
        payload = encode({'ref': None, 'text': 'fictional same-journal Branch handoff'})
        self.runtime.db.execute("INSERT INTO outboxes(id,role,producer,recipient,kind,required,payload,event,job,state,created) VALUES(?,?,?,?,?,?,?,?,?,'pending',1000)",
                                ('fictional-delivery', 'Work', 'fictional-producer', 'Branch', 'work', 'settled', payload, 'fictional-work', job['id']))
        outbox = self.runtime.one("SELECT * FROM outboxes WHERE id='fictional-delivery'")
        conn.execute('INSERT INTO coordinator_deliveries_v1 VALUES(?,?,?,?,?,?,?,?,0,?)',
                     (outbox['id'], 'fictional-grant-Work', self.runtime.config['actor'], outbox['producer'],
                      'fictional-logical-Branch', payload, 1, 12, outbox['kind']))
        conn.execute("INSERT INTO notification_outbox VALUES(1,'managed','managed_pending')")
        # Positive source processing is deliberately substituted; no fabricated
        # native worker/session or assertion of substantive model processing.
        with patch.object(boards['Work'], '_software_job_grant', return_value=boards['Work']._grant(conn, self.runtime)), \
             patch('coordinator_runtime.software.clean_processing', return_value={'fixture': True}):
            self.assertTrue(boards['Work'].software_delivery(self.runtime, outbox, boards))
        intent = conn.execute('SELECT * FROM coordinator_software_deliveries_v1').fetchone()
        return boards, conn, intent, outbox

    def test_supported_handoff_ingests_classifies_and_reserves_exact_receiving_source(self):
        boards, conn, intent, outbox = self.handoff()
        received = self.runtime.event(intent['event'])
        self.assertEqual(received['processing_capability'], self.key)
        self.assertEqual(received['source_delivery']['id'], outbox['id'])
        self.assertFalse(self.runtime.ingest(received))  # Lost ingest reply does not duplicate.
        self.classify(received, 'bi')
        self.runtime.ack_state(received['id'], 'internal')  # Fictional protocol only.
        job = self.runtime.reserve()
        self.assertEqual(job['role'], 'Branch')
        self.assertEqual(json.loads(job['members'])[0]['event'], received['id'])
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 2)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?', (received['id'],))['processed_at'])
        for replacement in ({'body': 'changed'}, {'recipient': 'fictional-other'}, {'allowed_tasks': ['wi']}):
            with self.assertRaises(Refusal):
                self.runtime.ingest({**received, **replacement})
        conn.execute("UPDATE notification_outbox SET delivery_state='ambiguous'")
        with self.assertRaises(Refusal):
            self.runtime.processing.event(received)
        conn.execute("UPDATE notification_outbox SET delivery_state='managed_pending'")
        conn.execute('CREATE TABLE coordinator_control_requirements_v1(delivery,created)')
        conn.execute('INSERT INTO coordinator_control_requirements_v1 VALUES(?,1000)', (outbox['id'],))
        with self.assertRaises(Refusal):
            self.runtime.processing.event(received)

    def test_marker_without_persisted_intent_does_not_admit(self):
        boards, conn = self.boards()
        self.bind(boards)
        with self.assertRaises(Refusal):
            self.runtime.ingest({'id': 'fictional-forgery', 'role': 'Branch', 'recipient': 'fictional-logical-Branch',
                                 'kind': 'response', 'processing_capability': self.key, 'allowed_tasks': ['bi']})
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 0)

    def test_existing_published_response_keeps_original_bytes_in_new_intent(self):
        boards, conn, intent, outbox = self.handoff()
        # Explicit fixture preparation: an already-published response without
        # the new marker, not a mutation performed by the adapter under test.
        original = self.runtime.event(intent['event'])
        original.pop('processing_capability')
        self.runtime.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(original), digest(original), original['id']))
        self.events.append(original)
        conn.execute('DELETE FROM coordinator_software_deliveries_v1')
        self.runtime.db.execute("UPDATE outboxes SET kind='result',payload=? WHERE id=?", (encode(original), outbox['id']))
        conn.execute("UPDATE coordinator_deliveries_v1 SET payload=?,kind='result' WHERE id=?", (encode(original), outbox['id']))
        self.bind(boards)
        selected = self.runtime.one('SELECT * FROM outboxes WHERE id=?', (outbox['id'],))
        with patch.object(boards['Work'], '_software_job_grant', return_value=boards['Work']._grant(conn, self.runtime)), \
             patch('coordinator_runtime.software.clean_processing', return_value={'fixture': True}):
            self.assertTrue(boards['Work'].software_delivery(self.runtime, selected, boards))
        self.assertEqual(self.runtime.event(original['id']), original)
        self.assertEqual(self.runtime.one('SELECT hash FROM events WHERE id=?', (original['id'],))['hash'], digest(original))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 2)

    def test_exact_qa_admission_needs_owner_and_preserves_revocation_and_frozen_jobs(self):
        boards, conn = self.boards()
        request = {'kind': 'admit-package', 'role': 'Branch', 'target': 'fictional-qa-package', 'prior': None,
                   'receipt': {'admission': {'source': 'fictional Branch admitted package'}, 'accepted': None}}
        self.bind(boards, [request])
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-issuer')
        changed = {**request, 'target': 'fictional-unselected'}
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, changed, 'fictional-logical-Branch')
        result = processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Branch')
        self.assertFalse(result['acceptance_inferred'])
        self.assertTrue(processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Branch')['already_recorded'])
        self.event('fictional-qa', 'QA', 'qe', request['target'])
        self.assertEqual(self.runtime.reserve()['role'], 'QA')
        next_request = {**request, 'prior': self.runtime.one('SELECT * FROM admissions')}
        with self.assertRaises(Refusal):
            processing.owner_request(self.runtime, next_request)
        self.assertTrue(all(r['intake'] == 0 for r in self.runtime.rows('SELECT intake FROM enrollments')))
        self.assertTrue(all(r['revoked'] is not None for r in conn.execute('SELECT revoked FROM coordinator_grants_v1')))

    def test_original_effect_owner_records_remaining_hold_then_exact_clearance(self):
        boards, conn = self.boards()
        hold = 'fictional original effect uncertainty'
        self.runtime.db.execute("UPDATE enrollments SET legacy_hold=? WHERE role='Work'", (hold,))
        receipt = {'collector': 'fictional original collector', 'evidence': ['fictional collected effect evidence'], 'remaining_holds': ['external effect unknown']}
        request = {'kind': 'legacy-disposition', 'role': 'Work', 'target': 'Work', 'prior': hold, 'receipt': receipt}
        clear = {**request, 'receipt': {**receipt, 'remaining_holds': []}}
        self.bind(boards, [request, clear])
        self.event('fictional-held', 'Work', 'wi')
        self.assertFalse(processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Work')['hold_cleared'])
        self.assertIsNone(self.runtime.reserve())
        self.event('fictional-independent', 'Branch', 'bi')
        self.assertEqual(self.runtime.reserve()['role'], 'Branch')
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, clear, 'fictional-logical-Branch')
        self.assertTrue(processing.apply_owner(self.runtime, boards, self.key, clear, 'fictional-logical-Work')['hold_cleared'])
        self.assertEqual(self.runtime.reserve()['role'], 'Work')
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_owner_operations')['n'], 2)
        self.assertIn(hold, self.runtime.one("SELECT reconciliation FROM enrollments WHERE role='Work'")['reconciliation'])

    def test_native_owner_input_disposition_uses_current_cap_without_unrevoking(self):
        boards, conn = self.boards()
        source = self.event('fictional-qa-control', 'QA', 'qe', queued=False)
        request = {'kind': 'resolve-input', 'role': 'QA', 'target': source['id'],
                   'prior': {'source_hash': digest(source), 'resolution': None}, 'receipt': self.receipt(source, remaining=['actual QA admission not supplied'])}
        self.bind(boards, [request])
        result = processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-QA')
        self.assertTrue(result['fresh_classification_required'])
        self.classify(source, '@unresolved')
        self.assertEqual(self.runtime.event(source['id']), source)
        self.assertEqual(self.runtime.one("SELECT intake FROM enrollments WHERE role='QA'")['intake'], 0)
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE id=?', (self.key,))
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-QA')

    def test_owner_clearance_cannot_waive_unknown_original_job_or_publication(self):
        boards, conn = self.boards()
        self.event('fictional-original-job', 'Work', 'wi')
        self.bind(boards)
        job = self.runtime.reserve()
        with self.runtime.tx():
            attempt = self.runtime._attempt('task', None, job['id'], SOL, None)
        self.runtime.db.execute('UPDATE jobs SET active_attempt=? WHERE id=?', (attempt, job['id']))
        self.runtime.hold_job(job['id'], 'fictional original effect uncertainty')
        self.runtime.db.execute("UPDATE enrollments SET legacy_hold='fictional old debt' WHERE role='Work'")
        request = {'kind': 'legacy-disposition', 'role': 'Work', 'target': 'Work', 'prior': 'fictional old debt',
                   'receipt': {'collector': 'fictional original collector', 'evidence': ['fictional exact effect evidence'], 'remaining_holds': []}}
        self.bind(boards, [request])
        snapshot = self.runtime.job(job['id'])
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Work')
        self.assertEqual(self.runtime.job(job['id']), snapshot)
        self.runtime.collect(attempt, {'exit': 7, 'capture': 'complete', 'cleanup': 'no-session-created', 'error': 'fictional failed original'})
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Work')
        self.runtime.db.execute("INSERT INTO file_publications(attempt,target,state) VALUES(?,?,'prepared')", (attempt, 'fictional-target'))
        with self.assertRaises(Refusal):
            self.runtime.reconcile_effects(job['id'], job['token'], 'fictional-logical-Work', {'evidence': ['fictional'], 'unknown_effects': []})
        # An explicit fixture transition stands for external custodian recovery;
        # it is never a producer operation against a real publication.
        self.runtime.db.execute("UPDATE file_publications SET state='published'")
        self.runtime.reconcile_effects(job['id'], job['token'], 'fictional-logical-Work', {'evidence': ['fictional resolved exact effect'], 'unknown_effects': []})
        snapshot = self.runtime.job(job['id'])
        self.assertTrue(processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Work')['hold_cleared'])
        self.assertEqual(self.runtime.job(job['id']), snapshot)
        self.assertEqual(self.runtime.job(job['id'])['state'], 'held')

    def test_owner_source_cli_and_stale_operation_are_bounded(self):
        from coordinator_runtime.cli import parser
        boards, conn = self.boards()
        request = {'kind': 'admit-package', 'role': 'Branch', 'target': 'fictional-package', 'prior': None,
                   'receipt': {'admission': {'source': 'fictional exact package'}, 'accepted': None}}
        self.bind(boards, [request])
        source = processing.owner_source(self.runtime, boards, self.key, 'Branch', 'admit-package', request['target'])
        self.assertIsNone(source['prior'])
        args = parser().parse_args(['processing-owner-apply', self.key, '--request', '/fixtures/request.json'])
        self.assertEqual(args.command, 'processing-owner-apply')
        self.runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)', (request['target'], 'fictional-logical-Branch', '{}'))
        with self.assertRaises(Refusal):
            processing.apply_owner(self.runtime, boards, self.key, request, 'fictional-logical-Branch')
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_owner_operations')['n'], 0)
        self.assertEqual(self.runtime.one('SELECT receipt FROM admissions')['receipt'], '{}')

    def test_control_never_takes_over_uncollected_original_classifier(self):
        self.event('fictional-uncollected-classifier', 'Work', 'wp', queued=False)
        original, source = self.runtime.claim_classification()
        self.runtime.db.execute("UPDATE events SET state='classification-held'")
        dispatcher = processing.ProcessingDispatcher(self.runtime, boards={})
        with patch.object(dispatcher, 'spawn') as spawn:
            dispatcher.schedule_classification_recovery()
            spawn.assert_not_called()
        self.assertIsNone(self.runtime.attempt(original)['collected'])
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_controls')['n'], 0)

    def test_controls_obey_shared_nonjob_capacity_and_keep_original_attempt(self):
        source = self.event('fictional-control-capacity', 'Work', 'wp', queued=False)
        self.runtime.db.execute("UPDATE events SET state='classification-held'")
        self.runtime.config['classification_capacity'] = 1
        self.authority()
        with self.runtime.tx():
            original = self.runtime._attempt('classifier', source['id'], None, SOL, None)
        dispatcher = processing.ProcessingDispatcher(self.runtime, boards={})
        with patch.object(dispatcher, 'spawn') as spawn:
            dispatcher.schedule_classification_recovery()
            spawn.assert_not_called()
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM attempts')['n'], 1)
        self.assertEqual(self.runtime.attempt(original)['state'], 'reserved')
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_controls')['n'], 0)
        self.runtime.collect(original, {'exit': 7, 'capture': 'complete', 'cleanup': 'no-session-created', 'error': 'fictional failure'})
        marker = object()
        with patch.object(dispatcher, 'control', new=lambda *args: marker), patch.object(dispatcher, 'spawn') as spawn:
            dispatcher.schedule_classification_recovery()
            spawn.assert_called_once_with(marker)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_controls')['n'], 1)
        self.assertEqual(self.runtime.attempt(original)['exit'], 7)
        control = self.runtime.one('SELECT attempt FROM processing_controls')['attempt']
        self.assertIsNone(self.runtime.attempt(control)['session'])
        self.assertIsNone(self.runtime.attempt(control)['profile'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
