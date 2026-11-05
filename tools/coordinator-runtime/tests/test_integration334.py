"""331 receiving intent plus 332 finite allocations, in private fiction only.

The independent Work decision requires both outcomes on the joined source.
No native/provider/profile/session/turn encounter or actual held body is used.
"""
import json
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import processing, service, windows
from coordinator_runtime.contracts import Backpressure, Refusal, encode
import test_owed331 as owed
import test_allocation332 as allocation


class Joined(unittest.TestCase):
    def setUp(self):
        self.c = allocation.Continuing(methodName='runTest')
        self.addCleanup(self.c.doCleanups)
        original = allocation.fixture.Store

        def configured(value, **kwargs):
            value['delivery']['recipients'] = {'Work': {'session': 'fictional-Work',
                                                       'board_role': 'fictional', 'profile': None}}
            value['limits'].update(max_events=8, max_outboxes=128)
            value['limits']['max_artifact_bytes'] = 65536
            return original(value, **kwargs)

        with patch.object(allocation.fixture, 'Store', side_effect=configured):
            self.c.setUp()
            self.c.adopt()
        self.s = self.c.s
        self.boards = self.c.f.boards
        self.c.f.conn.execute('UPDATE coordinator_delivery_grants_v1 SET recipients=?,kinds=?',
            (encode({'Work': 'fictional-Work'}), encode(['alert', 'question', 'effect-request', 'work'])))
        selected = self.c.selection()
        selected['service']['admission'] = {'until': 1001., 'pause_bytes': 16000000, 'max_new_inputs': 1}
        self.key = self.c.issue(selected)
        self.f = owed.OwedControl(methodName='runTest')
        self.f.f, self.f.s, self.f.boards, self.f.number = self.c.f, self.s, self.boards, 0
        self.f.source = self.c.f.fresh('fictional-joined-source')
        with self.s.tx():
            used = json.loads(windows.current(self.s)['used'])
            used['events'] = 8
            self.s.db.execute('UPDATE service_windows SET new_inputs=40,used=? WHERE number=2', (encode(used),))
        self.old_window = windows.current(self.s)
        self.s.clock = lambda: 1001.
        self.positions = self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')

    def receive(self, kind='alert'):
        outbox = self.f.delivery(kind)
        self.boards['Work'].software_delivery(self.s, outbox, self.boards)
        intent = self.f.f.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',
                                       (outbox['id'],)).fetchone()
        return outbox, json.loads(intent['payload'])

    def test_owed_control_renews_bounded_window_under_upstream_pause_without_blob_query(self):
        # No artifact/key/presence/size read may participate in the boundary.
        def no_blobs(action, table, column, database, source):
            if action == sqlite3.SQLITE_READ and table == 'artifact_blobs':
                raise AssertionError('opaque artifact acquisition forbidden')
            return sqlite3.SQLITE_OK
        self.s.db.set_authorizer(no_blobs)
        try:
            with self.assertRaises(Backpressure):
                service.admit_input(self.s)
            outbox = self.f.delivery()
            # Creating this new outbox lawfully charges its original window.
            # The receiving event then needs a different bounded allocation.
            before = windows.current(self.s)
            self.boards['Work'].software_delivery(self.s, outbox, self.boards)
            event = json.loads(self.f.f.conn.execute(
                'SELECT payload FROM coordinator_software_deliveries_v1 WHERE delivery=?',
                (outbox['id'],)).fetchone()['payload'])
            self.assertTrue(self.s.processing.owed_control(event))
            self.assertFalse(self.s.ingest(event))
            with self.assertRaises(Backpressure):
                self.s.ingest({**self.f.source, 'id': 'fictional-new-upstream'})
        finally:
            self.s.db.set_authorizer(None)
        self.assertEqual(self.s.one('SELECT * FROM service_windows WHERE number=2'), before)
        self.c.assert_originals()
        current = windows.current(self.s)
        self.assertEqual((current['number'], current['new_inputs']), (3, 1))
        self.assertEqual(json.loads(current['used'])['events'], 1)
        self.assertEqual(self.s.one('SELECT capability FROM service_window_allocations WHERE number=3'),
                         {'capability': self.key})
        positions = self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')
        self.assertEqual(positions[:-1], self.positions)
        self.assertGreater(positions[-1]['position'], self.positions[-1]['position'])
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?', (event['id'],))['processed_at'])
        self.assertIsNone(self.s.one('SELECT processed_at FROM outboxes WHERE id=?', (outbox['id'],))['processed_at'])
        self.assertTrue(all(r['profile'] is None and r['session'] is None and r['turn'] is None
                            for r in self.s.rows('SELECT profile,session,turn FROM attempts')))

    def test_capacity_refusal_rolls_back_boundary_and_retains_same_control_intent(self):
        for kind in ('alert', 'question', 'effect-request'):
            self.receive(kind)
        # Force the next control to need a fresh window, then introduce actual
        # publication-reservation pressure. Event count is a per-window allocation bound
        # in this mode; it is not a cumulative residency ceiling.
        self.s.db.execute('UPDATE service_windows SET new_inputs=40 WHERE number=3')
        outbox = self.f.delivery()
        before = self.s.rows('SELECT * FROM service_windows ORDER BY number')
        links = self.s.rows('SELECT * FROM service_window_allocations ORDER BY number')
        positions = self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')
        original_ingest = self.s.ingest
        def pressure_after_intent(event):
            # Fictional already-owned publication intents reserve capacity
            # without acquiring bodies, keys, target presence or aliases.
            for number in range(512):
                self.s.db.execute('INSERT INTO file_publications VALUES(?,?,\'intent\',?,NULL,NULL,NULL)',
                    ('fictional-pending-'+str(number), '/fixtures/UNOPENED-'+str(number), 'fictional-unqueried-body'))
            return original_ingest(event)
        for attempt in range(2):
            if attempt == 0:
                with patch.object(self.s, 'ingest', side_effect=pressure_after_intent), self.assertRaises(Backpressure):
                    self.boards['Work'].software_delivery(self.s, outbox, self.boards)
            else:
                with self.assertRaises(Backpressure):
                    self.boards['Work'].software_delivery(self.s, outbox, self.boards)
            intent = self.f.f.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',
                                           (outbox['id'],)).fetchone()
            self.assertIsNotNone(intent)
            self.assertIsNone(self.s.one('SELECT id FROM events WHERE id=?', (intent['event'],)))
            self.assertEqual(self.s.rows('SELECT * FROM service_windows ORDER BY number'), before)
            self.assertEqual(self.s.rows('SELECT * FROM service_window_allocations ORDER BY number'), links)
            self.assertEqual(self.s.rows('SELECT * FROM processing_source_positions ORDER BY position'), positions)

    def test_owed_control_cannot_borrow_expired_allocation_authority(self):
        outbox = self.f.delivery()
        self.s.clock = lambda: 90000.
        before = self.s.rows('SELECT * FROM service_windows ORDER BY number')
        links = self.s.rows('SELECT * FROM service_window_allocations')
        with self.assertRaisesRegex(Refusal, 'expired'):
            self.boards['Work'].software_delivery(self.s, outbox, self.boards)
        self.assertEqual(self.s.rows('SELECT * FROM service_windows ORDER BY number'), before)
        self.assertEqual(self.s.rows('SELECT * FROM service_window_allocations'), links)
        intent = self.f.f.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',
                                       (outbox['id'],)).fetchone()
        self.assertIsNotNone(intent)
        self.assertIsNone(self.s.one('SELECT id FROM events WHERE id=?', (intent['event'],)))

    def test_work_admission_none_retains_finite_allocation_and_prior_source_positions(self):
        processing.revoke(self.s, self.boards, self.key)
        selected = self.c.selection()
        selected['service']['admission'] = None
        self.c.issue(selected)
        self.assertEqual(service.admit_input(self.s), 8)
        self.s.ingest(self.c.new_event('fictional-None-admission-source'))
        current = windows.current(self.s)
        self.assertEqual((current['number'], current['new_inputs']), (3, 1))
        self.assertEqual(json.loads(current['used'])['events'], 1)
        self.assertEqual(self.s.one('SELECT * FROM service_windows WHERE number=2'), self.old_window)
        self.assertEqual(self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')[:-1], self.positions)
        self.s.clock = lambda: 90000.
        with self.assertRaisesRegex(Refusal, 'expired'):
            service.admit_input(self.s)
        self.c.assert_originals()


if __name__ == '__main__':
    unittest.main()
