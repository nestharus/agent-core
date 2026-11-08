"""Decision1114 actual AppServer originals; synthetic sessions, no provider.

Production unsubscribe/teardown and real SQLite faults are exercised. Numeric
waits are recorded before cleanup, which is an independent last-resort duty.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

from coordinator_runtime import appserver
from coordinator_runtime.contracts import Refusal
from support import result
from test_oneoff1077 import Recovery


class Collection1114(unittest.IsolatedAsyncioTestCase):
    setUp = Recovery.setUp
    reservation = Recovery.reservation
    prepare = Recovery.prepare

    async def original(self, fault):
        _, _, attempt = self.reservation()
        self.prepare(attempt)
        self.config['deadlines']['shutdown'] = .1
        adapter = appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12', '-B', '-c',
            'import sys; sys.stdin.buffer.read(); raise SystemExit(0)'])
        child = None
        waits = []
        spawned = asyncio.create_subprocess_exec
        end_owned = appserver.end_owned
        begin = self.store.begin

        async def create(*args, **kwargs):
            nonlocal child
            child = await spawned(*args, **kwargs)
            return child

        async def observed_wait(original, grace):
            self.assertIs(original, child)
            code = await end_owned(original, grace)
            self.assertIsInstance(code, int)
            waits.append(code)
            return code

        def fail_read(action, table, column, database, trigger):
            return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ and table == 'attempts' else sqlite3.SQLITE_OK

        def begin_fault(*args):
            self.store.db.set_authorizer(fail_read)
            raise sqlite3.OperationalError('fictional postspawn begin journal unavailable')

        async def session(peer, store, owned, *args):
            if fault == 'read':
                # Real session fact exists before a real SQLite read refusal.
                store.session(owned, '11111111-1111-4111-8111-111111111114')
                store.db.set_authorizer(fail_read)
            return result()

        try:
            with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec', side_effect=create), \
                 patch('coordinator_runtime.appserver.environment', return_value={'PATH':'/usr/bin:/bin'}), \
                 patch('coordinator_runtime.appserver.storage.prepare', return_value=None), \
                 patch('coordinator_runtime.appserver.end_owned', side_effect=observed_wait), \
                 patch.object(adapter, 'session', side_effect=session):
                if fault == 'begin':
                    self.store.begin = begin_fault
                if fault == 'checkpoint':
                    with patch('coordinator_runtime.oneoff.checkpoint', side_effect=OSError('fictional capsule unavailable')):
                        outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
                elif fault == 'evidence':
                    # Keep production numeric wait; only its subsequent evidence
                    # validator fails. Unsubscribe is never replaced.
                    with patch.object(appserver.Peer, 'validate_turn_correlation', side_effect=OSError('fictional capture evidence unavailable')):
                        outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
                elif fault == 'debt':
                    with patch('coordinator_runtime.appserver.end_owned', side_effect=OSError('fictional wait API unavailable')):
                        outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
                    self.assertIsNone(outcome['exit'])
                    self.assertIs(adapter.pending_collections[attempt][0], child)
                    self.assertIn('collection_debt', outcome['detail'])
                    await adapter.collect_pending()
                else:
                    outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
            self.assertIsNotNone(child)
            self.assertTrue(waits, 'production collector must wait before cleanup')
            self.assertEqual(outcome['exit'], waits[-1])
            self.assertEqual(adapter.pending_collections, {})
            if fault == 'read':
                self.assertEqual(outcome['detail']['unsubscribe_failure'], 'DatabaseError')
                self.assertEqual(outcome['detail']['unsubscribe'], 'failed-or-unknown')
            if fault in {'read', 'begin', 'checkpoint'}:
                self.assertEqual(outcome['detail']['recovery_checkpoint'], 'unqualified-held')
            if fault == 'evidence':
                self.assertEqual(outcome['detail']['teardown_failure'], 'OSError')
                self.assertEqual(outcome['cleanup'], 'owned-teardown-needs-reconciliation')
            self.assertEqual(outcome['detail']['session_residuals']['state'], 'unqualified-held')
            (self.area/'ORIGINAL-COLLECTION1114.json').write_text(json.dumps({
                'fault':fault, 'numeric_waits_before_cleanup':waits, 'outcome':outcome,
                'same_original':True, 'actual_acceptance':False, 'processing_completion':False}))
            print('ORIGINAL1114 '+json.dumps({'fault':fault,'END':waits[-1],'before_cleanup':True}))
        finally:
            self.store.begin = begin
            self.store.db.set_authorizer(None)
            # Separate last-resort collection, never credited to production.
            if child is not None and child.returncode is None:
                code = await end_owned(child, .1)
                print('CLEANUP-ONLY1114 '+json.dumps({'END':code,'production_credit':False}))

    async def test_production_unsubscribe_SQLite_read_failure_collects_same_original(self):
        await self.original('read')

    async def test_postspawn_begin_and_unavailable_journal_collect_before_peer(self):
        await self.original('begin')

    async def test_checkpoint_failure_keeps_production_unsubscribe_and_collection(self):
        await self.original('checkpoint')

    async def test_postwait_evidence_failure_preserves_numeric_collection(self):
        await self.original('evidence')

    async def test_wait_API_failure_retains_capable_debt_and_collects_same_handle(self):
        await self.original('debt')

    async def test_caller_cancellation_during_production_unsubscribe_is_joined(self):
        _, _, attempt = self.reservation()
        self.prepare(attempt)
        self.config['deadlines']['shutdown'] = .1
        adapter = appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12','-B','-c','import sys; sys.stdin.buffer.read()'])
        boundary, release = asyncio.Event(), asyncio.Event()
        original_rpc = appserver.Peer.rpc
        original_end = appserver.end_owned
        waits = []
        async def rpc(peer, method, params):
            if method == 'thread/unsubscribe':
                boundary.set()
                await release.wait()
                return {'status':'unsubscribed'}
            return await original_rpc(peer, method, params)
        async def session(peer, store, owned, *args):
            store.session(owned, '11111111-1111-4111-8111-111111111114')
            return result()
        async def end(child, grace):
            code = await original_end(child, grace)
            waits.append(code)
            return code
        with patch('coordinator_runtime.appserver.environment',return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare',return_value=None), \
             patch.object(appserver.Peer,'rpc',rpc), patch.object(adapter,'session',side_effect=session), \
             patch('coordinator_runtime.appserver.end_owned',side_effect=end):
            running = asyncio.create_task(adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {}))
            try:
                await asyncio.wait_for(boundary.wait(), 3)
                running.cancel()
                await asyncio.sleep(0)
                release.set()
                with self.assertRaises(asyncio.CancelledError) as caught:
                    await running
                outcome = caught.exception.collection_outcome
                self.assertTrue(waits)
                self.assertEqual(outcome['exit'], waits[-1])
                self.assertEqual(outcome['detail']['unsubscribe'], 'unsubscribed')
                self.assertEqual(adapter.pending_collections, {})
                (self.area/'ORIGINAL-COLLECTION1114.json').write_text(json.dumps({
                    'fault':'caller-cancellation','numeric_waits_before_cleanup':waits,'outcome':outcome}))
                print('ORIGINAL1114 '+json.dumps({'fault':'caller-cancellation','END':waits[-1],'before_cleanup':True}))
            finally:
                release.set()
                await asyncio.gather(running, return_exceptions=True)
                await adapter.collect_pending()


    async def test_concurrent_admitted_originals_do_not_collect_each_other(self):
        _, _, first = self.reservation()
        self.prepare(first)
        _, _, second = self.reservation('Branch')
        self.prepare(second)
        self.config['deadlines']['shutdown'] = .1
        adapter = appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12','-B','-c','import sys; sys.stdin.buffer.read()'])
        first_ready, second_ready, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_end = appserver.end_owned
        waits = []
        async def session(peer, store, owned, *args):
            if owned == first:
                first_ready.set()
            else:
                self.assertIsNone(adapter.owned_collections[first][0].returncode)
                self.assertEqual(adapter.pending_collections, {})
                second_ready.set()
            await release.wait()
            return result()
        async def end(child, grace):
            code = await original_end(child, grace)
            waits.append(code)
            return code
        with patch('coordinator_runtime.appserver.environment',return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare',return_value=None), \
             patch.object(adapter,'session',side_effect=session), \
             patch('coordinator_runtime.appserver.end_owned',side_effect=end):
            a = asyncio.create_task(adapter.run(self.store, first, 'synthetic', {'cwd':str(self.area)}, {}))
            b = None
            try:
                await asyncio.wait_for(first_ready.wait(), 3)
                b = asyncio.create_task(adapter.run(self.store, second, 'synthetic', {'cwd':str(self.area)}, {}))
                await asyncio.wait_for(second_ready.wait(), 3)
                release.set()
                outcomes = await asyncio.gather(a,b)
                self.assertEqual(len(waits), 2)
                self.assertTrue(all(type(x['exit']) is int for x in outcomes))
                self.assertEqual(adapter.pending_collections, {})
                self.assertEqual(adapter.owned_collections, {})
                (self.area/'ORIGINAL-COLLECTION1114.json').write_text(json.dumps({
                    'fault':'concurrent-owned','numeric_waits_before_cleanup':waits,'outcomes':outcomes}))
                print('ORIGINAL1114 '+json.dumps({'fault':'concurrent-owned','ENDs':waits,'before_cleanup':True}))
            finally:
                release.set()
                await asyncio.gather(*[x for x in (a,b) if x is not None], return_exceptions=True)
                await adapter.collect_pending()
