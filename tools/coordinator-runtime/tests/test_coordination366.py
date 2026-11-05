"""Bounded fictional timing discriminators; no provider or authority efficacy."""
import asyncio
import json
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from coordinator_runtime.appserver import Peer
from coordinator_runtime.contracts import Refusal
from coordinator_runtime.dispatcher import Dispatcher


class Pipe:
    def __init__(self, delay=0, blocked=False):
        self.stdout = asyncio.StreamReader()
        self.stdin = self
        self.delay = delay
        self.release = asyncio.Event()
        self.entered = asyncio.Event()
        self.blocked = blocked
        self.frames = []

    def write(self, data):
        self.frames.append(json.loads(data))

    async def drain(self):
        self.entered.set()
        if self.blocked:
            await self.release.wait()
        await asyncio.sleep(self.delay)

    def respond(self, result=None):
        self.stdout.feed_data((json.dumps({'id': self.frames[-1]['id'], 'result': result or {'ok': True}})+'\n').encode())


class Coordination(unittest.IsolatedAsyncioTestCase):
    async def close_peer(self, peer):
        peer.reader.cancel()
        await asyncio.gather(peer.reader, return_exceptions=True)

    async def test_blocked_drain_uses_existing_RPC_budget_and_late_response_cannot_settle(self):
        child = Pipe(blocked=True)
        peer = Peer(child, 4096)
        call = asyncio.create_task(peer.rpc('thread/start', {}, timeout=.04))
        try:
            await child.entered.wait()
            await asyncio.sleep(.10)
            observed = call.done()
            print('DRAIN_OBSERVATION='+json.dumps({'done_before_release': observed, 'progress': peer.progress}))
            self.assertTrue(observed, 'RPC budget must cover blocked drain')
            with self.assertRaises(asyncio.TimeoutError):
                await call
            self.assertEqual(peer.pending, {})
            self.assertEqual(peer.progress[-1]['state'], 'timeout')
            child.respond({'thread': {'id': 'fictional-late-root'}})
            await asyncio.sleep(0)
            self.assertIsNone(peer.thread)
            self.assertEqual(peer.progress[-1]['state'], 'timeout')
        finally:
            child.release.set()
            child.respond()
            await asyncio.gather(call, return_exceptions=True)
            await self.close_peer(peer)

    async def test_send_and_response_share_one_budget(self):
        child = Pipe(delay=.06)
        peer = Peer(child, 4096)
        async def response():
            await child.entered.wait()
            await asyncio.sleep(.12)
            child.respond()
        responder = asyncio.create_task(response())
        try:
            with self.assertRaises(asyncio.TimeoutError):
                await peer.rpc('config/read', {}, timeout=.09)
            self.assertEqual(peer.pending, {})
            self.assertEqual(peer.progress[-1]['state'], 'timeout')
            print('SHARED_BUDGET_OBSERVATION='+json.dumps(peer.progress))
        finally:
            await responder
            await self.close_peer(peer)

    async def test_real_tick_yields_to_matching_reader_and_control_between_phases(self):
        child = Pipe()
        peer = Peer(child, 4096)
        dispatcher = Dispatcher.__new__(Dispatcher)
        phases, cleared, errors, control_seen, reader_seen = [], [], [], [], []
        dispatcher.store = SimpleNamespace(clear_operational_error=cleared.append,
            record_operational_error=lambda subject, detail: errors.append(subject))
        names = ('receipts', 'reconcile_completed', 'intake', 'schedule_classifications',
                 'schedule_classification_recovery', 'schedule_job', 'schedule_recovery',
                 'custodian_progress', 'automatic_cleanup')
        def phase(name):
            def operation():
                phases.append(name)
                if peer.progress[-1]['state'] == 'succeeded':
                    reader_seen.append(name)
                time.sleep(.01)  # Finite synchronous phase; never interrupt/skip its checks.
                if name == 'intake':
                    raise Refusal('fictional held intake')
            operation.__name__ = name
            return operation
        for name in names:
            setattr(dispatcher, name, phase(name))
        async def pump():
            phases.append('pump')
        dispatcher.pump_deliveries_async = pump
        call = asyncio.create_task(peer.rpc('thread/start', {}, timeout=1))
        try:
            await child.entered.wait()
            child.respond({'thread': {'id': 'fictional-owned-root'}})
            asyncio.get_running_loop().call_soon(lambda: control_seen.append(len(phases)))
            with patch('coordinator_runtime.dispatcher.capacity.deliver_pending', lambda store: phases.append('capacity')):
                await dispatcher.tick()
            response = await call
            print('PHASE_OBSERVATION='+json.dumps({'control_seen_after_phases': control_seen,
                'reader_seen': reader_seen, 'phases': phases, 'cleared': cleared, 'errors': errors, 'RPC': peer.progress}))
            self.assertEqual(response['thread']['id'], 'fictional-owned-root')
            self.assertLess(control_seen[0], len(names), 'control callback must run before all synchronous phases')
            self.assertTrue(reader_seen, 'matching response must be collected between phases')
            self.assertEqual(phases, list(names)+['capacity', 'pump'])
            self.assertEqual(errors, ['dispatcher-phase:intake'])
            self.assertEqual(len(cleared), 8)
            self.assertEqual(peer.progress[-1]['state'], 'succeeded')
        finally:
            await asyncio.gather(call, return_exceptions=True)
            await self.close_peer(peer)

    async def test_rpc_cancellation_clears_pending_without_claiming_response(self):
        child = Pipe(blocked=True)
        peer = Peer(child, 4096)
        call = asyncio.create_task(peer.rpc('thread/start', {}, timeout=1))
        try:
            await child.entered.wait()
            call.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await call
            self.assertEqual(peer.pending, {})
            self.assertEqual(peer.progress[-1]['failure'], 'CancelledError')
            self.assertEqual(peer.progress[-1]['state'], 'failed')
        finally:
            await self.close_peer(peer)
