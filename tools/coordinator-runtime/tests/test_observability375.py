"""Causal fixtures in positive mounts only; timings are not production evidence."""
import asyncio
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime import observations as obs, processing, service
from coordinator_runtime.appserver import Peer
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import Dispatcher
from test_coordination366 import Pipe
from test_processing188 import SelectionTests
from test_retained168 import ControlledBoard
from test_startup_control346 import Control


class Observability(unittest.IsolatedAsyncioTestCase):
    def workload(self, size):
        fixture = SelectionTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        runtime = fixture.runtime
        for number in range(size - 1):
            source = {**runtime.source, 'id': 'fictional-source-' + str(number),
                      'body': 'PAYLOAD_CANARY_NEVER_OBSERVE'}
            runtime.db.execute("INSERT INTO events VALUES(?, 'Work', ?, 'queued', NULL, NULL, 'done', NULL, NULL, NULL, ?)",
                               (source['id'], digest(source), encode(source)))
        runtime.db.commit()
        fixture.issue(future_intake=True)
        retained_area = fixture.directory / 'retained'
        retained_area.mkdir()
        fixture.retained = ControlledBoard(runtime, retained_area)
        self.addCleanup(fixture.retained.conn.close)
        board = fixture.retained
        policy = {'basis': board.retained_basis(runtime), 'authority': 'fictional bounded retained custody',
                  'expires': runtime.now + 60, 'max_shared_rows': 1024, 'max_shared_payload_bytes': 1048576,
                  'max_runtime_rows': 256, 'max_visits': 10}
        board.capability = board.delegate_retained(runtime, policy)['capability']
        return fixture

    async def close_peer(self, peer):
        peer.reader.cancel()
        await asyncio.gather(peer.reader, return_exceptions=True)

    async def test_retained_and_current_workloads_preserve_routes_and_identify_slow_source(self):
        for size in (1, 64):
            fixture = self.workload(size)
            runtime, board = fixture.runtime, fixture.retained
            before = {table: runtime.rows('SELECT * FROM ' + table)
                      for table in ('events', 'queue', 'outboxes', 'enrollments')}
            original = runtime.event
            def read(name):
                time.sleep(.001)  # Explicit per-source acquisition latency seam.
                return original(name)
            with obs.owning('service') as record, patch.object(runtime, 'event', read):
                with obs.span('intake'):
                    board.verify_authority(runtime)
                    fixture.board.verify_authority(runtime)
                    self.assertTrue(runtime.processing.event(runtime.source))
                    self.assertTrue(runtime.processing.event({**runtime.source, 'id': 'fictional-future', 'post': 1}))
                    self.assertFalse(runtime.processing.event({**runtime.source, 'id': 'fictional-old', 'post': 0}))
            view = record.snapshot()
            self.assertEqual(view['totals']['retained-events']['last_items'], size)
            self.assertEqual(view['totals']['retained-outboxes']['last_items'], 0)
            self.assertGreater(view['totals']['source-files']['last_items'], 0)
            self.assertGreaterEqual(view['totals']['retained-source']['max_ms'], size * .7)
            rows = {row['sequence']: row for row in view['recent']}
            source = next(row for row in rows.values() if row['phase'] == 'retained-source')
            self.assertEqual(rows[source['parent']]['phase'], 'retained-authority')
            self.assertNotIn('PAYLOAD_CANARY', encode(view))
            print('OBS375_WORKLOAD=' + encode({'events': size, 'source_ms': view['totals']['retained-source']['max_ms'],
                'current_ms': view['totals']['current']['max_ms'], 'owner': view['owner']}))
            self.assertEqual(before, {table: runtime.rows('SELECT * FROM ' + table) for table in before})
            # A current revocation must refuse before any source scan/replay.
            runtime.db.execute('UPDATE processing_capabilities SET revoked=1001')
            runtime.db.commit()
            with obs.owning('service') as refused:
                with self.assertRaises(Refusal):
                    fixture.board.verify_authority(runtime)
            self.assertEqual(refused.snapshot()['totals']['current']['failed'], 1)
            self.assertNotIn('source-files', refused.snapshot()['totals'])
            self.assertEqual(before, {table: runtime.rows('SELECT * FROM ' + table) for table in before})
            if size == 1:
                with obs.owning('service') as visit:
                    result = board.retained_step(runtime, board.capability)
                self.assertEqual(len(result['handled']), 1)
                self.assertEqual(visit.snapshot()['totals']['retained-step']['count'], 1)
                self.assertIsNone(runtime.one('SELECT processed_at FROM events')['processed_at'])
                self.assertEqual(before, {table: runtime.rows('SELECT * FROM ' + table) for table in before})
            runtime.db.execute("UPDATE events SET payload=? WHERE id=?", (encode({'body': 'PAYLOAD_CANARY_CHANGED'}), runtime.source['id']))
            runtime.db.commit()
            with obs.owning('service') as changed:
                with self.assertRaises(Refusal): board.verify_authority(runtime)
            self.assertEqual(changed.snapshot()['totals']['retained-source']['failed'], 1)
            self.assertNotIn('PAYLOAD_CANARY', encode(changed.snapshot()))
            self.assertIsNone(runtime.one('SELECT processed_at FROM events LIMIT 1')['processed_at'])

    async def test_synchronous_authority_delays_timeout_delivery_and_real_tick_continues_after_refusal(self):
        fixture = self.workload(64)
        runtime, board = fixture.runtime, fixture.retained
        child = Pipe()
        peer = Peer(child, 4096)
        self.addAsyncCleanup(self.close_peer, peer)
        dispatcher = Dispatcher.__new__(Dispatcher)
        errors, phases = [], []
        dispatcher.store = SimpleNamespace(clear_operational_error=lambda subject: None,
            record_operational_error=lambda subject, detail: errors.append(subject))
        names = ('receipts', 'reconcile_completed', 'intake', 'schedule_classifications',
                 'schedule_classification_recovery', 'schedule_job', 'schedule_recovery',
                 'custodian_progress', 'automatic_cleanup')
        def operation(name):
            def run():
                phases.append(name)
                if name == 'receipts': board.verify_authority(runtime)
                if name == 'intake': raise Refusal('PAYLOAD_CANARY_NEVER_OBSERVE')
            run.__name__ = name
            return run
        for name in names: setattr(dispatcher, name, operation(name))
        async def pump(): phases.append('delivery')
        dispatcher.pump_deliveries_async = pump
        original = runtime.event
        def read(name):
            time.sleep(.001)
            return original(name)
        with obs.owning('service') as record, patch.object(runtime, 'event', read), patch(
                'coordinator_runtime.dispatcher.capacity.deliver_pending', lambda store: phases.append('capacity')):
            call = asyncio.create_task(peer.rpc('thread/start', {'body': 'PAYLOAD_CANARY'}, timeout=.02))
            await child.entered.wait()
            await asyncio.sleep(0)
            self.assertTrue(any(row['phase'] == 'rpc-reply-wait' for row in record.snapshot()['active']))
            await dispatcher.tick()
            with self.assertRaises(asyncio.TimeoutError): await call
        row = peer.progress[-1]
        self.assertEqual(row['boundary'], 'awaiting-response')
        self.assertGreaterEqual(row['cancellation_delivered_ms'], 50)
        self.assertGreaterEqual(row['budget_overrun_ms'], 30)
        self.assertNotIn('correlated_reply_ms', row)
        self.assertEqual(peer.pending, {})
        self.assertEqual(peer.rpc_timings, {})
        self.assertEqual(phases, list(names) + ['capacity', 'delivery'])
        self.assertEqual(errors, ['dispatcher-phase:intake'])
        self.assertGreaterEqual(record.snapshot()['totals']['retained-source']['max_ms'], 50)
        self.assertEqual(record.snapshot()['totals']['intake']['failed'], 1)
        error_row = next(item for item in record.snapshot()['recent'] if item['phase'] == 'phase-error-report')
        self.assertEqual(next(item for item in record.snapshot()['recent'] if item['sequence'] == error_row['parent'])['phase'], 'intake')
        self.assertNotIn('PAYLOAD_CANARY', encode(record.snapshot()))
        method_row = next(item for item in record.snapshot()['recent'] if item['sequence'] == row['observation_sequence'])
        self.assertEqual(method_row['phase'], 'thread/start')
        self.assertEqual(method_row['state'], 'failed')
        child.respond({'thread': {'id': 'fictional-late-root'}})
        await asyncio.sleep(0)
        self.assertEqual(peer.progress[-1]['state'], 'timeout')
        self.assertIsNone(peer.thread)
        print('OBS375_DELAYED_TIMEOUT=' + encode(row))

    async def test_rpc_send_reply_failure_and_external_cancellation_are_separate(self):
        child = Pipe(blocked=True)
        peer = Peer(child, 4096)
        self.addAsyncCleanup(self.close_peer, peer)
        with self.assertRaises(asyncio.TimeoutError):
            await peer.rpc('thread/start', {'secret': 'PAYLOAD_CANARY'}, timeout=.02)
        blocked = peer.progress[-1]
        self.assertEqual(blocked['boundary'], 'sending')
        self.assertNotIn('send_drain_ms', blocked)
        self.assertNotIn('correlated_reply_ms', blocked)
        child.respond({'thread': {'id': 'fictional-late-root'}})
        await asyncio.sleep(0)
        child.blocked, child.delay = False, .02
        async def answer():
            await asyncio.sleep(.04)
            child.respond()
        responder = asyncio.create_task(answer())
        self.assertEqual(await peer.rpc('config/read', {}), {'ok': True})
        await responder
        success = peer.progress[-1]
        self.assertGreater(success['sequence'], blocked['sequence'])
        self.assertGreaterEqual(success['correlated_reply_ms'], success['send_drain_ms'])
        call = asyncio.create_task(peer.rpc('turn/start', {}, timeout=1))
        await asyncio.sleep(.04)
        call.cancel()  # Observed request here; no production request-time claim.
        time.sleep(.04)
        with self.assertRaises(asyncio.CancelledError): await call
        self.assertEqual(peer.progress[-1]['failure'], 'CancelledError')
        self.assertGreaterEqual(peer.progress[-1]['cancellation_delivered_ms'], 70)
        self.assertNotIn('budget_overrun_ms', peer.progress[-1])
        self.assertEqual(peer.pending, {})
        self.assertEqual(peer.rpc_timings, {})
        with patch.object(peer, 'send', side_effect=BrokenPipeError('PAYLOAD_CANARY')):
            with self.assertRaises(BrokenPipeError): await peer.rpc('untrusted-PAYLOAD_CANARY', {})
        self.assertEqual(peer.progress[-1]['method'], 'other')
        self.assertEqual(peer.progress[-1]['boundary'], 'sending')
        self.assertNotIn('PAYLOAD_CANARY', encode(peer.progress))

    async def test_bounded_lifetime_inflight_counts_and_numeric_saturation(self):
        self.assertIsNone(obs.snapshot())
        with obs.owning('service') as record:
            for number in range(1000):
                with obs.span('current'):
                    obs.count('source-files', obs.LIMIT)
            active = [record.begin('intake') for _ in range(65)]
            view = record.snapshot()
            self.assertEqual(len(view['recent']), 64)
            self.assertEqual(len(view['active']), 64)
            self.assertEqual(view['dropped'], 1)
            self.assertEqual(view['totals']['source-files']['items'], obs.LIMIT)
            self.assertLess(len(encode(view).encode()), 65536)
            for number in active: record.end(number, 'succeeded')
            with self.assertRaises(ValueError):
                with obs.span('PAYLOAD_CANARY'): pass
            self.assertNotIn('PAYLOAD_CANARY', encode(record.snapshot()))
        record.window_started -= obs.WINDOW_SECONDS
        expired = record.snapshot()
        self.assertEqual(expired['recent'], [])
        self.assertEqual(expired['active'], [])
        self.assertEqual(expired['totals'], {})
        with obs.owning('service') as crossing:
            with obs.span('intake'):
                crossing.window_started -= obs.WINDOW_SECONDS
                self.assertEqual(crossing.snapshot()['active'], [])
            self.assertEqual(crossing.snapshot()['dropped'], 1)
            self.assertEqual(crossing.snapshot()['totals'], {})
        with obs.owning('control-client') as fresh:
            self.assertEqual(fresh.snapshot()['totals'], {})
            self.assertEqual(fresh.owner, 'control-client')
        child = Pipe()
        peer = Peer(child, 4096)
        self.addAsyncCleanup(self.close_peer, peer)
        for number in range(100):
            with patch.object(peer, 'send', side_effect=BrokenPipeError):
                with self.assertRaises(BrokenPipeError): await peer.rpc('config/read', {})
        self.assertEqual(len(peer.progress), 64)
        self.assertEqual(peer.progress_dropped, 36)
        self.assertEqual(peer.rpc_timings, {})
        child.blocked = True
        calls = [asyncio.create_task(peer.rpc('thread/start', {}, timeout=1)) for _ in range(70)]
        await child.entered.wait()
        self.assertLessEqual(len(peer.rpc_timings), 64)
        self.assertEqual(peer.correlation_dropped, 6)
        for call in calls: call.cancel()
        await asyncio.gather(*calls, return_exceptions=True)
        self.assertEqual(peer.pending, {})
        self.assertEqual(peer.rpc_timings, {})

    async def test_normal_control_client_presocket_and_actual_fixture_custodian_are_distinct(self):
        fixture = Control()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        ready = asyncio.Event()
        returns = []
        def emit(value):
            returns.append(value)
            if value.get('state') == 'serving': ready.set()
        async def run(dispatcher, emit): await dispatcher.stopping.wait()
        with patch.object(service.Dispatcher, 'run', run), patch.object(service.Dispatcher, 'recover_originals',
                lambda dispatcher: {'collector': dispatcher.store.controller, 'uncollected': []}):
            original = asyncio.create_task(service.serve(fixture.store, {'Work': fixture.board_type()}, fixture.key, emit, models=object()))
            await asyncio.wait_for(ready.wait(), 2)
            try:
                read_bytes = Path.read_bytes
                def slow_source(path):
                    if path.name == 'observations.py': time.sleep(.04)
                    return read_bytes(path)
                with patch.object(Path, 'read_bytes', slow_source):
                    code, answer = await asyncio.to_thread(fixture.invoke)
                self.assertEqual(code, 0)
                client, custodian = answer['client_observations'], answer['service_observations']
                self.assertEqual(client['owner'], 'control-client')
                self.assertEqual(custodian['owner'], 'service')
                self.assertEqual(answer['controller'], fixture.store.controller)
                self.assertGreaterEqual(client['totals']['source-implementation']['max_ms'], 35)
                self.assertIn('store-open', client['totals'])
                self.assertIn('control-prepare', client['totals'])
                self.assertIn('control-reply', client['totals'])
                self.assertNotIn('control-reply', custodian['totals'])
                self.assertEqual(custodian['totals']['control-status']['count'], 1)
                with patch.object(service, 'control', side_effect=AssertionError('socket must remain unreached')):
                    code, refused = await asyncio.to_thread(fixture.invoke, 'fictional-absent')
                self.assertEqual(code, 2)
                self.assertEqual(refused['client_observations']['totals']['current']['failed'], 1)
                self.assertNotIn('control-connect', refused['client_observations']['totals'])
                self.assertNotIn('service_observations', refused)
                print('OBS375_CLIENT=' + encode({'source_ms': client['totals']['source-implementation']['max_ms'],
                    'reply_ms': client['totals']['control-reply']['max_ms'], 'client_owner': client['owner'], 'service_owner': custodian['owner']}))
            finally:
                await service.control(fixture.store, fixture.key, 'stop')
                await asyncio.wait_for(original, 2)
        self.assertEqual(returns[-1]['uncollected'], [])
        self.assertEqual(returns[-1]['service_observations']['owner'], 'service')

    async def test_control_socket_reply_delay_and_connection_failure_report_reached_boundaries(self):
        runtime = SimpleNamespace(path=Path('/fixtures/fictional-socket'), config={'limits': {'max_bytes': 65536}})
        async def connection(reader, writer):
            await reader.readline()
            await asyncio.sleep(.04)
            writer.write(b'{"fixture_reply":true}\n')
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        server = await asyncio.start_unix_server(connection, path=service.endpoint(runtime, 'fictional-key'))
        try:
            with obs.owning('control-client') as record:
                answer = await service.control(runtime, 'fictional-key', 'status')
            self.assertTrue(answer['fixture_reply'])
            self.assertNotIn('service_observations', answer)
            self.assertGreaterEqual(record.snapshot()['totals']['control-reply']['max_ms'], 35)
            self.assertEqual(record.snapshot()['totals']['control-send']['count'], 1)
        finally:
            server.close()
            await server.wait_closed()
        with obs.owning('control-client') as refused:
            with self.assertRaises(OSError): await service.control(runtime, 'fictional-key', 'status')
        self.assertEqual(refused.snapshot()['totals']['control-connect']['failed'], 1)
        self.assertNotIn('control-reply', refused.snapshot()['totals'])
