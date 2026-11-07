"""Fresh retained fixtures only; run in an empty network/PID/mount namespace.

Production board, Work selection, intake, model-attempt and receipt logic run.
Principal consent is fictional CODEX_SESSION_ID; models return deterministic
fiction, never provider/native evidence. No task executor or cleanup is run.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import config_at
from coordinator_runtime import processing, service, service_wake
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import LUNA, Refusal, ident, encode
from coordinator_runtime.store import Store


class Models:
    def __init__(self):
        self.calls = []

    async def run(self, store, attempt, prompt, spec, schema):
        row = store.attempt(attempt)
        assert row['kind'] == 'classifier', 'no task/model idle polling permitted'
        self.calls.append(attempt)
        store.begin(attempt, {'fictional_model': True})
        store.session(attempt, ident())
        event = store.event(row['event'])
        await asyncio.sleep(0)
        return dict(exit=0, capture='complete', cleanup='done', error=None,
                    result=dict(event_id=event['id'], task='work-proposer', package=None,
                                reason='Fresh fictional finding belongs to Work'),
                    detail={'fixture': True, 'resume_disposition': 'unavailable-after-ephemeral-owner-exit'})


class ManagedWake(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = Path('/fixtures') / self._testMethodName
        self.directory.mkdir()
        self.config = config_at(self.directory)
        shared = self.config['roles']['Work']['board_id']
        for selected in self.config['roles'].values():
            selected['board_id'] = shared
        self.owner = self.config['roles']['Work']['owner']
        self.sender, self.native = ident(), ident()
        self.config['delivery'] = {'recipients': {role: dict(session=item['owner'], profile=item['profile'],
                                    board_role=item['board_role']) for role, item in self.config['roles'].items()}}
        self.config['software_delegation'] = {'grantor': self.owner, 'authority': 'Fictional Work wake fixture'}
        self.config['recheck_seconds'] = .04
        self.helper = module_at(self.config['board_library'], 'active_listener')
        self.substrate = module_at(self.config['board_library'], 'board_store', imports={'active_listener': self.helper})
        catalog = module_at(self.config['board_library'], 'catalog')
        with catalog.catalog(Path(self.config['board_home'])) as cat:
            entry = catalog.create(cat, Path(self.config['board_home']), 'wake658', 'Owned wake fixture',
                                   board_id=shared, temporary_test=True)
        self.path = Path(entry['db_path'])
        with self.substrate.database(str(self.path)) as conn:
            self.substrate.bind_board(conn, shared, initialize=True)
            for selected in self.config['roles'].values():
                self.register(conn, selected['owner'], selected['board_role'], selected['profile'])
            self.register(conn, self.sender, 'fixture-sender', '.codex')
            self.register(conn, self.native, 'fixture-native', '.codex', route='queue')
        self.now = 1000.
        self.store = Store(self.config, clock=lambda: self.now)
        self.boards = {}
        for role in self.config['roles']:
            ordinary = Board(self.config, role)
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
                grant = ordinary.grant_software(self.store, self.config['software_delegation']['authority'])
            self.store.enroll(role, grant)
            self.store.reconcile_legacy(role, self.config['roles'][role]['owner'],
                {'collector': self.config['roles'][role]['owner'],
                 'evidence': ['Fresh fictional fixture has no prior originals or resource conflicts'],
                 'remaining_holds': []})
            # Explicit fictional stopped normal epoch, never live grant edits.
            with ordinary.opened() as conn:
                conn.execute('UPDATE coordinator_grants_v1 SET revoked=? WHERE id=?', ('fixture-stop', grant['id']))
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?', (role,))
            self.boards[role] = processing.ProcessingBoard(self.config, role)
        self.selection = dict(basis=processing.basis(self.store, self.boards, future_only=True),
                              authority='Fictional current Work selects finite managed service wake',
                              retained_events=[], recover_controls={}, future_intake=True,
                              tasks=list(self.config['tasks']), max_shared_rows=10000,
                              max_shared_payload_bytes=10000000, max_runtime_rows=10000,
                              service=dict(max_inflight=5, reviews={}, legacy_resources={},
                                           admission=dict(until=1060., pause_bytes=90000000, max_new_inputs=1000),
                                           wake=dict(protocol='managed-hint-v1', roles=list(self.config['roles']), until=1060.)))
        with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
            self.key = processing.select(self.store, self.boards, self.selection)['capability']
        self.store.processing = processing.Access(self.store, self.key, self.boards)
        self.models = Models()
        self.dispatcher = service.Dispatcher(self.store, self.boards, self.models)
        self.bridge = service_wake.ServiceWake(self.store, self.boards, self.dispatcher)
        self.dispatcher.wake = self.bridge

    async def asyncTearDown(self):
        self.bridge.close()
        await asyncio.gather(*self.dispatcher.active, return_exceptions=True)
        (self.directory / 'fixture-result.json').write_text(encode({
            'test': self.id(), 'model_calls': self.models.calls,
            'events': self.store.rows('SELECT id,role,ack,processed_at FROM events'),
            'attempts': self.store.rows('SELECT id,kind,binding,state,exit,collected FROM attempts'),
            'queue': self.store.rows('SELECT event,state FROM queue'),
            'wake': self.bridge.status(), 'capability': self.key,
            'seams': ['fictional CODEX_SESSION_ID principals', 'deterministic model returns',
                      'no task execution, provider, native send or semantic-response assertion']}))
        self.store.close()  # Retain every fixture, including adverse attempts.

    def register(self, conn, session, role, profile, route='managed'):
        args = self.substrate.parser().parse_args(['register', '--session', session, '--role', role,
                                                   '--profile', profile, '--route', route])
        with patch.dict(os.environ, {'CODEX_SESSION_ID': session}):
            self.substrate.register(conn, args)

    def post(self, *, plain=False, recipient=None, producer=None):
        producer = producer or self.substrate
        args = producer.parser().parse_args(['post' if plain else 'open', '--session', self.sender,
            '--to', recipient or self.owner, '--topic', 'fixture', '--kind', 'finding', '--text', 'New owned finding'] +
            ([] if plain else ['--title', 'Wake fixture', '--no-push']))
        with producer.database(str(self.path)) as conn:
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.sender}):
                return producer.post(conn, args) if plain else producer.open_thread(conn, args)

    def save_selection(self):
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',
                              (encode(self.selection), self.key))

    async def turn(self):
        self.dispatcher.intake()
        self.dispatcher.schedule_classifications()
        await asyncio.gather(*self.dispatcher.active)
        self.dispatcher.receipts()

    async def test_post_before_and_during_bind_initial_scan_closes_race(self):
        self.post()
        original = self.helper._db_identity
        calls = 0
        def identity(conn):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.post()
            return original(conn)
        with patch('coordinator_runtime.service_wake.module_at', return_value=self.helper), \
             patch.object(self.helper, '_db_identity', side_effect=identity):
            self.bridge.start()
        await self.turn()
        await self.turn()
        self.assertEqual(len(self.models.calls), 2)
        self.assertEqual(len(self.store.rows('SELECT * FROM queue')), 2)

    async def test_coalesced_duplicate_hints_classify_and_receipt_once(self):
        self.bridge.start()
        self.post()
        with self.substrate.database(str(self.path)) as conn:
            for _ in range(25):
                self.helper.signal_post(conn, 1)
        await asyncio.sleep(.01)
        self.assertTrue(self.dispatcher.wakeup.is_set())
        self.assertGreater(self.bridge.hints, 0)
        for _ in range(4):
            await self.turn()
        self.assertEqual(len(self.models.calls), 1)
        self.assertEqual(json.loads(self.store.one('SELECT binding FROM attempts')['binding']), LUNA)
        self.assertEqual(len(self.store.rows('SELECT * FROM queue')), 1)
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM coordinator_receipts_v1').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT delivery_state FROM notification_outbox').fetchone()[0], 'acknowledged')
            self.assertEqual(conn.execute('SELECT ack_seq FROM sessions WHERE session=?', (self.owner,)).fetchone()[0], 0)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    async def test_no_idle_model_attempts_and_timer_recovers_lost_hint_and_plain_post(self):
        self.bridge.start()
        for _ in range(3):
            await self.turn()
            await self.dispatcher.pause()
        self.assertEqual(self.models.calls, [])
        self.assertEqual(self.store.rows('SELECT * FROM attempts'), [])
        with patch.object(self.helper, 'signal_post', return_value=None):
            self.post()
        self.post(plain=True)
        await self.dispatcher.pause()  # No producer hint exists for either post.
        await self.turn()
        await self.turn()
        self.assertEqual(len(self.models.calls), 2)

    async def test_full_hint_queue_is_nonblocking_and_durable(self):
        self.bridge.start()
        real_socket = socket.socket
        class NonblockingSender:
            def __init__(self, *a, **k): self.sock = real_socket(*a, **k)
            def __enter__(self): return self
            def __exit__(self, *a): self.sock.close()
            def setblocking(self, value): self.sock.setblocking(value)
            def sendto(self, *args):
                assert not self.sock.getblocking(), 'full hint must never block a producer'
                return self.sock.sendto(*args)
        # No event-loop yield: the real kernel datagram queue fills here.
        with patch.object(self.helper.socket, 'socket', NonblockingSender):
            for _ in range(20): self.post()
        await self.turn()
        while len(self.models.calls) < 20: await self.turn()
        self.assertEqual(len(self.store.rows('SELECT * FROM queue')), 20)

    async def test_native_endpoint_is_separate_and_duplicate_service_refuses_without_unlink(self):
        with self.substrate.database(str(self.path)) as conn:
            identity = self.helper._db_identity(conn)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as native:
            native.bind(self.helper._address(self.owner, identity))
            native.setblocking(False)
            self.bridge.start()
            duplicate = service_wake.ServiceWake(self.store, self.boards, self.dispatcher)
            with self.assertRaisesRegex(Refusal, 'conflict'):
                duplicate.start()
            self.assertEqual(self.bridge.state, 'bound')
            self.post()
            self.assertEqual(native.recv(256), self.helper._packet(identity))
            await asyncio.sleep(.01)
            self.assertGreater(self.bridge.hints, 0)

    async def test_queue_recipient_never_receives_managed_service_hint(self):
        with self.substrate.database(str(self.path)) as conn:
            identity = self.helper._db_identity(conn)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
            receiver.bind(self.helper.managed_address(self.native, identity))
            receiver.setblocking(False)
            self.post(recipient=self.native)
            with self.assertRaises(BlockingIOError): receiver.recv(256)
        with self.boards['Work'].opened() as conn:
            conn.execute("UPDATE sessions SET route='queue' WHERE session=?", (self.owner,))
        with self.assertRaisesRegex(Refusal, 'native/queue'):
            self.bridge.start()

    async def test_wake_requires_explicit_selection_and_finite_exact_roles(self):
        policy = self.selection['service'].pop('wake')
        self.save_selection()
        self.bridge.start()
        self.assertEqual(self.bridge.state, 'disabled')
        for change in ({'roles': ['Root']}, {'roles': ['Work', 'Work']}, {'until': 1061.},
                       {'until': float('nan')}, {'protocol': 'other'}):
            candidate = copy.deepcopy(self.selection)
            candidate['service']['wake'] = {**policy, **change}
            with self.assertRaises(Refusal): service_wake.validate(self.store, candidate)
        self.selection['service']['wake'] = policy

    async def test_revoked_processing_stops_wake_and_guarded_intake_without_model(self):
        self.bridge.start()
        self.post()
        self.store.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE id=?', (self.key,))
        with self.assertRaises(Refusal): self.dispatcher.intake()
        self.assertEqual(self.bridge.state, 'authority-held')
        self.assertEqual(self.store.rows('SELECT * FROM events'), [])
        self.assertEqual(self.models.calls, [])

    async def test_expired_admission_preserves_originals_and_refuses_new_intake(self):
        self.bridge.start()
        self.post()
        await self.turn()
        before = self.store.rows('SELECT * FROM queue')
        self.now = 1061.
        self.post()
        with self.assertRaises(Refusal): self.bridge.check()
        self.dispatcher.intake()
        self.assertEqual(len(self.models.calls), 1)
        self.assertEqual(self.store.rows('SELECT * FROM queue'), before)
        self.assertEqual(len(self.store.rows('SELECT * FROM events')), 1)

    async def test_paused_intake_is_not_reopened_by_hint(self):
        self.bridge.start()
        self.selection['future_intake'] = False
        self.save_selection()
        self.post()
        with self.assertRaises(Refusal): self.dispatcher.intake()
        self.assertEqual(self.store.rows('SELECT * FROM events'), [])
        self.assertEqual(self.bridge.state, 'authority-held')
        self.assertEqual(self.models.calls, [])

    async def test_unauthorized_original_grant_cannot_acquire_from_hint(self):
        self.bridge.start()
        with self.boards['Work'].opened() as conn:
            conn.execute("UPDATE coordinator_grants_v1 SET issued_by='unauthorized' WHERE role='Work'")
        with self.assertRaises(Refusal): self.bridge.check()
        self.assertEqual(self.models.calls, [])
        self.assertEqual(self.bridge.state, 'authority-held')

    async def test_source_and_config_pins_fail_closed_before_binding(self):
        self.selection['basis']['implementation']['service_wake.py'] = 'changed'
        self.save_selection()
        with self.assertRaises(Refusal): self.bridge.start()
        self.selection['basis']['implementation'] = processing.implementation()
        self.save_selection()
        self.config['recheck_seconds'] = .05
        with self.assertRaises(Refusal): self.bridge.start()
        self.assertEqual(self.models.calls, [])

    async def test_hint_racing_scan_survives_pause_and_stop_interrupts_idle(self):
        self.config['recheck_seconds'] = 10
        turns = 0
        async def tick(emit):
            nonlocal turns
            turns += 1
            if turns == 1: self.dispatcher.wakeup.set()
            else: self.dispatcher.stopping.set()
        with patch.object(self.dispatcher, 'guarded_tick', side_effect=tick):
            await asyncio.wait_for(self.dispatcher.loop(lambda _: None), .5)
        self.assertEqual(turns, 2)
        self.assertEqual(self.models.calls, [])

    async def test_finite_pages_request_immediate_next_tick_and_preserve_other_roles(self):
        for _ in range(101): self.post()
        self.post(recipient=self.config['roles']['Branch']['owner'])
        self.dispatcher.intake()
        self.assertTrue(self.dispatcher.wakeup.is_set())
        self.assertEqual(len(self.store.rows('SELECT * FROM events')), 101)
        self.assertEqual(self.store.one("SELECT count(*) AS n FROM events WHERE role='Branch'")['n'], 1)
        self.dispatcher.intake()
        self.assertEqual(len(self.store.rows('SELECT * FROM events')), 102)
        self.assertEqual(self.models.calls, [])
        self.assertEqual(set(self.boards), {'Work', 'Branch', 'Reviews', 'QA'})
        self.assertEqual(len(self.config['tasks']), 8)

    async def test_public_producer_code_accepts_patched_helper_and_wakes_same_consumer(self):
        # Retention is outside this hint contract. No retention option is used;
        # substitute only its unrelated send-metadata callback, never read the
        # installed retention implementation or claim retention qualification.
        public = module_at('/public', 'board_store', imports={'active_listener': self.helper,
                           'retention': SimpleNamespace(declare_on_send=lambda *args: None)})
        self.bridge.start()
        self.post(producer=public)
        await asyncio.sleep(.01)
        self.assertGreater(self.bridge.hints, 0)
        await self.turn()
        self.assertEqual(len(self.models.calls), 1)

    async def test_expiry_releases_only_owned_endpoints_and_ignores_malformed_packets(self):
        self.selection['service']['admission']['until'] = 1000.02
        self.selection['service']['wake']['until'] = 1000.02
        self.save_selection()
        self.bridge.start()
        receiver, _, identity, _ = self.bridge.receivers[0]
        address = receiver.getsockname()
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
            sender.sendto(b'untrusted model payload', address)
            sender.sendto(self.helper._packet(b'wrong-board'), address)
        await asyncio.sleep(.01)
        self.assertEqual(self.bridge.hints, 0)
        await asyncio.sleep(.02)
        self.assertEqual(self.bridge.state, 'expired')
        self.assertEqual(self.bridge.receivers, [])
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as own:
            own.bind(address)  # Exact prior kernel handle is gone, no path unlink.
        self.assertEqual(self.models.calls, [])

    async def test_actual_service_loop_binds_scans_wakes_and_drains_original(self):
        emitted = []
        # Full service/dispatcher phases run except product tasks, cleanup and
        # external custodian work, which this fixture deliberately does not own.
        def schedule_job(self): pass
        def automatic_cleanup(self): pass
        def custodian_progress(self): pass
        with patch.object(service.Dispatcher, 'schedule_job', schedule_job), \
             patch.object(service.Dispatcher, 'automatic_cleanup', automatic_cleanup), \
             patch.object(service.Dispatcher, 'custodian_progress', custodian_progress):
            task = asyncio.create_task(service.serve_owned(self.store, self.boards, self.key,
                                                           emitted.append, self.models))
            try:
                async with asyncio.timeout(3):
                    while not emitted:
                        if task.done(): await task
                        await asyncio.sleep(.01)
                    state = await service.control(self.store, self.key, 'status')
                    self.assertEqual(state['wake']['state'], 'bound')
                    self.assertEqual(self.models.calls, [])
                    self.post()
                    while not self.store.one('SELECT id FROM events WHERE ack=\'done\''):
                        await asyncio.sleep(.01)
                    state = await service.control(self.store, self.key, 'status')
                    self.assertGreater(state['wake']['observed_hints'], 0)
                    self.assertEqual(len(self.models.calls), 1)
                    self.assertEqual(len(self.store.rows('SELECT * FROM queue')), 1)
            finally:
                if not task.done(): await service.control(self.store, self.key, 'stop')
                await asyncio.wait_for(task, 3)
        run = self.store.one('SELECT state,receipt FROM service_runs')
        self.assertEqual(run['state'], 'returned-awaiting-parent-END')
        self.assertEqual(json.loads(run['receipt'])['collector'], self.store.controller)
        self.assertEqual(len(self.models.calls), 1)


if __name__ == '__main__':
    unittest.main()
