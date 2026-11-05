"""Owned retained fictional journals; no shared fixtures, accounts or models.

Run via the supplied isolated controller with CAPACITY48_FIXTURES naming an
explicit new own directory. No TemporaryDirectory cleanup or identity changes.
Receipt injection below is a software protocol seam, never a real consumer.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import unittest

from coordinator_runtime import capacity
from coordinator_runtime.cleanup import sweep
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store

OWNER = '00000000-0000-4000-8000-000000000001'
ACTOR = '00000000-0000-4000-8000-000000000002'


class NoModels:
    async def run(self, *args, **kwargs):
        raise AssertionError('no model/provider/native invocation is in scope')


class Channel:
    """Already-addressed receipt seam, no Board/native/provider instances."""
    def __init__(self):
        self.visits = []

    def scan(self, store):
        return []

    def post_delivery(self, store, outbox):
        self.visits.append(outbox['id'])
        return self.delivery_status(outbox['id'])

    def reconcile_delivery(self, store, outbox):
        return None

    def delivery_status(self, key):
        return {'id': key, 'state': 'acknowledged', 'processed_at': None}


class Capacity48(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.root = Path(os.environ['CAPACITY48_FIXTURES']) / self._testMethodName
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.now = 1000.0
        self.config = {'actor': ACTOR, 'profiles': ['.codex2'],
                       'state_dir': str(self.root / 'state'),
                       'execution_pool_routes': str(self.root / 'unused-fictional-routes.toml'),
                       'roles': {'Work': {'owner': OWNER, 'profile': '.codex2', 'legacy_hold': None}}, 'tasks': {},
                       'limits': {'max_events': 100, 'max_jobs': 100, 'max_attempts': 100,
                                  'max_alerts': 12, 'max_outboxes': 2, 'max_bytes': 16*1024*1024,
                                  'max_files': 100, 'max_result_bytes': 4096},
                       'deadlines': {'alert_interval': 60, 'ack': 30, 'backlog': 60,
                                     'bind': 10, 'task': 60},
                       'delivery': {'alert_role': 'Work', 'alert_recipient': 'Work',
                                    'recipients': {'Work': {'session': OWNER}}}}
        if self._testMethodName in {'test_alert_count_pressure_has_owned_gap_and_no_silent_prefix',
                                    'test_alert_and_exact_debt_exhaustion_refuses_with_durable_owned_gap'}:
            self.config['limits']['max_alerts'] = 1
            # Two due occurrences per cadence, two cadences retained in debt.
            # Production capacities stay unchanged. Exhaustion is separate.
            self.config['limits']['max_alert_debt'] = (4 if self._testMethodName ==
                'test_alert_count_pressure_has_owned_gap_and_no_silent_prefix' else 1)
        if self._testMethodName == 'test_byte_pressure_and_late_poll_are_explicit_no_backfill':
            self.config['limits']['max_bytes'] = 1
        if self._testMethodName == 'test_exact_debt_materializes_only_as_whole_cohort_after_qualified_reclamation':
            self.config['limits'].update(max_alerts=2, max_alert_debt=2)
        self.store = Store(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.store.enroll('Work', {'owner': OWNER, 'actor': ACTOR, 'id': 'fictional-grant', 'cutover': 0})
        self.store.reconcile_legacy('Work', OWNER, {'collector': 'fictional prior',
                                                 'evidence': ['fictional completed'], 'remaining_holds': []})
        self.trace = (self.root / 'sql-trace.txt').open('w')
        self.addCleanup(self.trace.close)
        self.store.db.set_trace_callback(lambda sql: self.trace.write(sql + '\n'))
        self.store.record_operational_error('unchanged', {'error': 'fictional persistent violation'})

    def runtime(self, boards=None):
        return Dispatcher(self.store, models=NoModels(), boards={} if boards is None else boards)

    def save_before(self, label):
        rows = {t: self.store.rows('SELECT * FROM ' + t) for t in
                ('alerts', 'outboxes', 'delivery_wakeups', 'operational_errors', 'alert_service')}
        (self.root / (label + '.json')).write_text(encode(rows))
        return rows

    def settled(self, occurrence, *, at=None):
        at = self.now if at is None else at
        outbox = self.store.one('SELECT * FROM outboxes WHERE alert=?', (occurrence,))
        delivery = {'id': outbox['id'], 'state': 'settled', 'recipient': OWNER,
                    'processed_at': at, 'processing': {'evidence': 'fictional actual processing'},
                    'settlement': {'evidence': 'fictional all substantive duties completed'},
                    'control_receipt': {'pending': False, 'required': False},
                    'transport': {'route': 'managed', 'delivery_state': 'acknowledged'}}
        self.store.delivery_observed(outbox['id'], delivery)
        self.store.process_alert(occurrence, OWNER, {'evidence': 'fictional substantive processing'})
        return delivery

    def release(self, occurrence):
        return {'basis': capacity.retirement_basis(self.store, occurrence)[2],
                'holds': {name: [] for name in capacity.HOLDS}, 'qualified_at': self.now,
                'evidence': 'fictional same source/consumer custodian qualifies all nine hold scopes'}

    async def test_pressure_conserves_occurrences_and_restarts_without_duplicates(self):
        originals = []
        for _ in range(4):
            originals.extend(self.store.emit_alerts())
            self.now += 60
        self.assertEqual(len(originals), 4)
        self.assertEqual(len(self.store.rows('SELECT * FROM outboxes')), 2)
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 4)
        payloads = self.store.rows('SELECT id,payload,created FROM alerts ORDER BY id')
        self.save_before('before-reopen')
        self.store.close()
        self.store = Store(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.rows('SELECT id,payload,created FROM alerts ORDER BY id'), payloads)
        await self.runtime().alerts(lambda _: None)
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 5)
        self.assertEqual(self.store.one('SELECT active FROM operational_errors WHERE subject=?', ('unchanged',))['active'], 1)
        await self.runtime().alerts(lambda _: self.fail('restart must respect durable cadence'))
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 5)

    async def test_alert_count_pressure_has_owned_gap_and_no_silent_prefix(self):
        self.store.record_operational_error('second', {'error': 'fictional second violation'})
        self.assertEqual(self.store.emit_alerts(), [])
        self.assertEqual(self.store.rows('SELECT * FROM alerts'), [])
        state = capacity.service(self.store)
        self.assertEqual(state['custodian'], OWNER)
        self.assertEqual((state['gap_since'], state['gap_through'], state['unrepresented']), (1000, 1000, 2))
        self.assertTrue(state['scope'])
        first = self.store.rows('SELECT * FROM alert_debt ORDER BY id')
        self.assertEqual(len(first), 2)
        self.assertEqual({r['subject'] for r in first}, {'unchanged', 'second'})
        self.assertTrue(all(json.loads(r['payload'])['id'] == r['id'] and r['created'] == self.now for r in first))
        self.now += 60
        await self.runtime().guarded_tick(lambda _: None)
        self.assertGreaterEqual(capacity.service(self.store)['unrepresented'], 4)
        self.assertEqual([self.store.one('SELECT * FROM alert_debt WHERE id=?',(r['id'],)) for r in first], first)
        self.assertEqual(len(self.store.rows('SELECT * FROM alert_debt')), 4)
        self.save_before('retained-unmet-gap')

    async def test_alert_and_exact_debt_exhaustion_refuses_with_durable_owned_gap(self):
        self.store.record_operational_error('second', {'error': 'fictional second violation'})
        with self.assertRaises(Backpressure) as refusal:
            self.store.emit_alerts()
        self.assertEqual(self.store.rows('SELECT * FROM alerts'), [])
        self.assertEqual(self.store.rows('SELECT * FROM alert_debt'), [])
        state = capacity.service(self.store)
        self.assertEqual(state['custodian'], OWNER)
        self.assertEqual((state['gap_since'],state['gap_through'],state['unrepresented']), (1000,1000,2))
        self.assertEqual(state['latest'], refusal.exception.observation)
        self.assertEqual(state['latest']['representation'], 'unavailable')
        self.assertEqual(state['latest']['due_count'], 2)
        self.assertEqual(self.store.rows('SELECT * FROM alert_cadence'), [])
        self.assertTrue(self.store.one("SELECT * FROM operational_errors WHERE subject='unchanged' AND active=1"))
        self.save_before('retained-explicit-exhaustion')

    async def test_exact_debt_materializes_only_as_whole_cohort_after_qualified_reclamation(self):
        first=self.store.emit_alerts()[0]['id']
        current=self.settled(first)
        self.store.record_operational_error('second', {'error':'fictional second unchanged violation'})
        self.now+=60
        self.assertEqual(self.store.emit_alerts(),[])
        original=self.store.rows('SELECT * FROM alert_debt ORDER BY id')
        self.assertEqual(len(original),2)
        self.assertEqual([r['id'] for r in self.store.rows('SELECT * FROM alerts')],[first])
        self.assertEqual(capacity.deliver_pending(self.store),0)
        self.assertEqual(self.store.rows('SELECT * FROM alert_debt ORDER BY id'),original)
        self.now=1000+86400
        capacity.retire(self.store,first,OWNER,self.release(first),current)
        self.assertEqual(capacity.deliver_pending(self.store),2)
        self.assertEqual(self.store.rows('SELECT id,created,payload FROM alerts ORDER BY id'),
                         [{k:r[k] for k in ('id','created','payload')} for r in original])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM alert_debt WHERE represented=1')['n'],2)
        receipts={r['id']:self.settled(r['id']) for r in original}
        self.now+=86400
        for row in original:
            capacity.retire(self.store,row['id'],OWNER,self.release(row['id']),receipts[row['id']])
        self.assertEqual(self.store.rows('SELECT * FROM alert_debt'),[])
        self.assertTrue(self.store.one("SELECT * FROM operational_errors WHERE subject='unchanged' AND active=1"))
        self.save_before('retained-whole-debt-reclamation')

    async def test_partial_delivery_batch_retains_both_due_occurrence_identities(self):
        self.store.record_operational_error('second', {'error': 'fictional second violation'})
        first = self.store.emit_alerts()
        self.now += 60
        second = self.store.emit_alerts()
        self.assertEqual((len(first), len(second)), (2, 2))
        self.assertEqual(len(self.store.rows('SELECT * FROM outboxes')), 2)
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 4)
        self.assertEqual({r['id'] for r in self.store.rows('SELECT id FROM alerts')},
                         {r['id'] for r in first+second})
        self.save_before('both-cohorts-originals')

    async def test_reporting_sink_failure_never_retries_same_due_cohort(self):
        runtime = self.runtime()
        def failed_sink(occurrence):
            raise OSError('fictional publication sink unavailable')
        await runtime.guarded_tick(failed_sink)
        self.assertTrue(self.store.one("SELECT * FROM operational_errors WHERE subject='alert-reporting' AND active=1"))
        original = self.store.rows('SELECT id,created,payload FROM alerts')
        await runtime.guarded_tick(lambda _: self.fail('same due cohort cannot be replayed'))
        self.assertEqual(self.store.rows('SELECT id,created,payload FROM alerts'), original)

    async def test_prospective_intake_count_refusal_preserves_cursor_and_originals(self):
        for n in range(100):
            self.store.ingest({'id': str(n), 'role': 'Work', 'recipient': OWNER,
                               'kind': 'response', 'body': 'fictional bounded source'}, cursor=n)
        before = self.store.rows('SELECT * FROM events ORDER BY id')
        with self.assertRaises(Backpressure):
            self.store.ingest({'id': 'overflow', 'role': 'Work', 'recipient': OWNER,
                               'kind': 'response', 'body': 'fictional refused source'}, cursor=100)
        self.assertEqual(self.store.one("SELECT seq FROM cursors WHERE role='Work'")['seq'], 99)
        self.assertEqual(self.store.rows('SELECT * FROM events ORDER BY id'), before)

    async def test_byte_pressure_and_late_poll_are_explicit_no_backfill(self):
        with self.assertRaises(Backpressure) as refusal:
            self.store.emit_alerts()
        self.assertEqual(capacity.service(self.store)['unrepresented'], 1)
        self.assertEqual(capacity.service(self.store)['latest'], refusal.exception.observation)
        self.assertEqual(capacity.service(self.store)['latest']['representation'], 'unavailable')
        self.assertEqual(self.store.rows('SELECT * FROM alert_debt'), [])
        self.assertEqual(self.store.rows('SELECT * FROM alerts'), [])

    async def test_late_poll_and_clock_regression_do_not_fabricate_history(self):
        first = self.store.emit_alerts()[0]
        self.now += 240
        second = self.store.emit_alerts()[0]
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 2)
        self.assertEqual(capacity.service(self.store)['gap_since'], 1060)
        self.assertIn('historical population unknown', capacity.service(self.store)['reason'])
        self.now = 900
        self.assertEqual(self.store.emit_alerts(), [])

    async def test_owed_delivery_and_processing_advance_despite_phase_refusal(self):
        original = self.store.emit_alerts()[0]
        channel = Channel()
        runtime = self.runtime({'Work': channel})
        def fail():
            raise Backpressure('fictional scheduling pressure')
        runtime.schedule_job = fail  # Explicit adverse phase seam, not real model scheduling.
        await runtime.guarded_tick(lambda _: None)
        row = self.store.one('SELECT * FROM outboxes WHERE alert=?', (original['id'],))
        self.assertEqual(row['state'], 'acknowledged')
        self.assertIsNone(row['processed_at'])
        self.assertTrue(channel.visits)
        self.assertTrue(self.store.one("SELECT * FROM operational_errors WHERE subject='dispatcher-phase:fail' AND active=1"))
        # Independent already-owed internal control processing: actual production
        # complete_events on a deliberately preclassified fixture boundary.
        event = {'id': 'owned-control', 'role': 'Work', 'recipient': OWNER, 'kind': 'response',
                 'body': 'fictional already-owed control', 'parent': None}
        self.store.ingest(event)
        self.store.db.execute("UPDATE events SET ack='internal',state='classified' WHERE id='owned-control'")
        self.store.db.execute("INSERT INTO queue(id,event,role,phase,task,state) VALUES('q','owned-control','Work','delivery','@delivery','done')")
        self.store.complete_events()
        self.assertEqual(self.store.one("SELECT state FROM events WHERE id='owned-control'")['state'], 'processed')
        self.assertTrue(self.store.one("SELECT * FROM operational_errors WHERE subject='unchanged' AND active=1"))

    async def test_numeric_end_ack_and_sweep_cannot_retire(self):
        occurrence = self.store.emit_alerts()[0]['id']
        outbox = self.store.one('SELECT * FROM outboxes WHERE alert=?', (occurrence,))
        receipt = {'id': outbox['id'], 'state': 'acknowledged', 'processed_at': None,
                   'exit': 0, 'semantic': 'DONE', 'control_receipt': {'pending': False}}
        self.store.delivery_observed(outbox['id'], receipt)
        self.now += 90000
        self.save_before('before-ack-refusal')
        with self.assertRaises(Refusal):
            capacity.retire(self.store, occurrence, OWNER, self.release(occurrence), receipt)
        sweep(self.store)
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 1)
        self.assertEqual(len(self.store.rows('SELECT * FROM outboxes')), 1)

    async def test_every_hold_stale_basis_foreign_and_retention_refuse(self):
        occurrence = self.store.emit_alerts()[0]['id']
        current = self.settled(occurrence)
        before = self.save_before('before-retirement-refusals')
        with self.assertRaises(Refusal):
            capacity.retire(self.store, occurrence, OWNER, self.release(occurrence), current)
        self.now += 86400
        release = self.release(occurrence)
        for name in sorted(capacity.HOLDS):
            held = copy.deepcopy(release)
            held['holds'][name] = ['fictional retained hold']
            with self.subTest(hold=name), self.assertRaises(Refusal):
                capacity.retire(self.store, occurrence, OWNER, held, current)
        for actor, changed in [(ACTOR, release), (OWNER, {**release, 'basis': 'stale'}),
                               (OWNER, {**release, 'qualified_at': self.now-61}),
                               (OWNER, {**release, 'qualified_at': float('nan')})]:
            with self.assertRaises(Refusal):
                capacity.retire(self.store, occurrence, actor, changed, current)
        self.assertEqual({t: self.store.rows('SELECT * FROM '+t) for t in before}, before)
        self.store.db.execute("UPDATE outboxes SET hold='fictional new recovery hold'")
        with self.assertRaises(Refusal):
            capacity.retire(self.store, occurrence, OWNER, release, current)

    async def test_lawful_retirement_reuses_capacity_without_losing_pending_ids(self):
        first = self.store.emit_alerts()[0]['id']
        current = self.settled(first)
        self.now += 60
        second = self.store.emit_alerts()[0]['id']
        self.now += 60
        pending = self.store.emit_alerts()[0]['id']
        self.assertIsNone(self.store.one('SELECT id FROM outboxes WHERE alert=?', (pending,)))
        self.now = 1000+86400
        self.save_before('before-qualified-retirement')
        result = capacity.retire(self.store, first, OWNER, self.release(first), current)
        (self.root/'retirement-original.json').write_text(encode(result))
        self.assertEqual(result['retired_alert'], first)
        self.assertEqual(capacity.deliver_pending(self.store), 1)
        self.assertTrue(self.store.one('SELECT id FROM outboxes WHERE alert=?', (pending,)))
        self.assertTrue(self.store.one('SELECT id FROM alerts WHERE id=?', (second,)))
        self.assertEqual(len(self.store.rows('SELECT * FROM outboxes')), 2)
        self.assertTrue(self.store.one("SELECT * FROM operational_errors WHERE subject='unchanged' AND active=1"))

    async def test_changed_control_transport_future_processing_and_scoped_error_refuse(self):
        occurrence = self.store.emit_alerts()[0]['id']
        initial = self.settled(occurrence)
        self.now += 86400
        outbox = self.store.one('SELECT * FROM outboxes WHERE alert=?', (occurrence,))
        self.save_before('before-adverse-lifetime')
        for changed in [
                {**initial, 'control_receipt': {'pending': True}},
                {**initial, 'transport': {'route': 'queue', 'delivery_state': 'acknowledged', 'queue_message_id': 'fictional-id'}},
                {**initial, 'processed_at': 999},
                {**initial, 'processed_at': self.now},
                {**initial, 'processing': None}]:
            self.store.delivery_observed(outbox['id'], changed)
            with self.assertRaises(Refusal):
                capacity.retire(self.store, occurrence, OWNER, self.release(occurrence), changed)
        self.store.delivery_observed(outbox['id'], initial)
        self.store.record_operational_error(outbox['id'], {'error': 'fictional scoped uncertainty'})
        with self.assertRaises(Refusal):
            capacity.retire(self.store, occurrence, OWNER, self.release(occurrence), initial)
        self.assertEqual(len(self.store.rows('SELECT * FROM alerts')), 1)
        self.assertEqual(len(self.store.rows('SELECT * FROM outboxes')), 1)

    async def test_cli_and_current_owner_adapter_wiring_with_refused_grant(self):
        # Exercise actual parser/owner entry without opening Board, native or
        # private identity. Only a narrow in-memory current-grant refusal seam.
        from contextlib import contextmanager
        from coordinator_runtime.board import Board
        from coordinator_runtime.cli import parser
        args = parser().parse_args(['retire-alert', 'Work', 'fictional-occurrence', '--receipt', '/fixtures/receipt.json'])
        self.assertEqual((args.command, args.role), ('retire-alert', 'Work'))
        calls = []
        class OwnerProtocol:
            def acting_session(self, expected):
                calls.append(('genuine-owner-interface', expected))
                return OWNER  # Fixture protocol only; no environment assignment.
            @contextmanager
            def write(self, conn):
                yield
        board = object.__new__(Board)  # No constructor, dynamic helper or real Board store.
        board.selected = {'owner': OWNER}
        board.store = OwnerProtocol()
        @contextmanager
        def opened():
            yield None
        board.opened = opened
        def refused(conn, runtime):
            calls.append(('current-grant', 'refused'))
            raise Refusal('fictional revoked current grant')
        board._grant = refused
        before = self.save_before('before-revoked-grant')
        with self.assertRaisesRegex(Refusal, 'revoked'):
            board.retire_alert(self.store, 'fictional-occurrence', {})
        self.assertEqual(calls, [('genuine-owner-interface', OWNER), ('current-grant', 'refused')])
        self.assertEqual({t: self.store.rows('SELECT * FROM '+t) for t in before}, before)

    async def test_finite_recurrence_envelope_beyond_retention_with_row_reuse(self):
        # 25h controlled time, one unchanged violation/minute, immediate
        # fictional processing, all holds released at 24h, one retirement/min.
        # Runtime count bounds fixed before its new store is opened.
        self.store.close()
        self.config['state_dir'] = str(self.root/'envelope-state')
        self.config['limits'].update(max_alerts=1441, max_outboxes=1441)
        self.store = Store(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.store.db.set_trace_callback(lambda sql: self.trace.write(sql+'\n'))
        self.store.enroll('Work', {'owner': OWNER, 'actor': ACTOR, 'id': 'envelope-grant', 'cutover': 0})
        self.store.reconcile_legacy('Work', OWNER, {'collector': 'fictional', 'evidence': ['closed'], 'remaining_holds': []})
        self.store.record_operational_error('unchanged', {'error': 'same violation'})
        current = {}
        created = retired = incoming = 0
        high = 0
        for minute in range(1501):
            self.now = 1000 + minute*60
            if minute % 300 == 0:
                # Explicit already-classified internal-control boundary; no
                # classifier/provider claim. Real intake and completion APIs.
                key = 'control-'+str(minute)
                self.store.ingest({'id': key, 'role': 'Work', 'recipient': OWNER,
                                   'kind': 'response', 'body': 'fictional already-owed control'}, cursor=minute)
                self.store.db.execute("UPDATE events SET ack='internal',state='classified' WHERE id=?", (key,))
                self.store.db.execute("INSERT INTO queue(id,event,role,phase,task,state) VALUES(?,?,'Work','delivery','@delivery','done')", ('q-'+key,key))
                self.store.complete_events()
                self.assertEqual(self.store.one('SELECT state FROM events WHERE id=?', (key,))['state'], 'processed')
                incoming += 1
            for key, record in list(current.items()):
                if record['processed_at'] <= self.now-86400:
                    alert, outbox, _ = capacity.retirement_basis(self.store, key)
                    (self.root/('before-retirement-'+str(minute)+'.json')).write_text(
                        encode({'alert': alert, 'outbox': outbox}))
                    result = capacity.retire(self.store, key, OWNER, self.release(key), record)
                    (self.root/('retirement-'+str(minute)+'.json')).write_text(encode(result))
                    del current[key]
                    retired += 1
            occurrences = self.store.emit_alerts()
            self.assertEqual(len(occurrences), 1)
            key = occurrences[0]['id']
            self.assertNotIn(key, current)
            current[key] = self.settled(key)
            created += 1
            high = max(high, len(current))
        usage = self.store.usage()
        self.assertEqual((created, retired, len(current), high), (1501, 61, 1440, 1440))
        self.assertEqual((usage['alerts'], usage['outboxes']), (1440, 1440))
        self.assertEqual(incoming, 6)
        self.assertEqual(len(self.store.rows("SELECT * FROM events WHERE state='processed'")), 6)
        self.assertLess(usage['bytes'], self.config['limits']['max_bytes'])
        self.assertIsNone(capacity.service(self.store)['gap_since'])
        (self.root/'envelope.json').write_text(encode({'created': created, 'retired': retired,
             'retained': len(current), 'peak': high, 'usage': usage, 'incoming_internal_controls': incoming,
             'limits': self.config['limits'], 'simulated_seconds': 90000,
             'scope': 'controlled software time and fictional consumer/hold proof; no real rates or Board'}))


if __name__ == '__main__':
    unittest.main()
