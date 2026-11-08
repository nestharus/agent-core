"""Decision1107 behavior controls on owned fiction; no real operating rights.

Initial journal faults must collect the same actual original before a test's
cleanup can act. Finite fairness preserves the entire independent source set;
no historical stride is used as a current oracle.
"""
import asyncio
import json
import sqlite3
import sys
import unittest
from unittest.mock import patch

from coordinator_runtime import ordinary
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
from test_ref_resources749 import RefResources
import test_windows76 as windows


class OrdinaryCollection1107(RefResources):
    async def fault(self, kind):
        self.boundary()
        policy = self.admission()
        job, attempt = self.prepared()
        # The real tool preflight/authority/source checks remain active. This
        # dedicated ordinary intent is a fictional tool encounter, no CAS or
        # semantic acceptance claim. No original handle is adopted.
        self.store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',
            (attempt, job['id'], 'fictional-current-tool', digest(self.store.one(
                'SELECT receipt FROM admissions WHERE package=?', (job['package'],))['receipt']),
             encode(policy), 'intent', '{}'))
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', ('fictional1107-held-resource', attempt))
        create = asyncio.create_subprocess_exec
        originals = []
        async def launch(*args, **kwargs):
            proc = await create(*args, **kwargs)
            originals.append(proc)
            return proc
        budget = self.store.budget
        failed = []
        def finite(*args, **kwargs):
            if originals and not failed:
                failed.append(True)
                raise Backpressure('fictional actual postspawn journal budget exhausted')
            return budget(*args, **kwargs)
        def deny(action, table, column, *unused):
            if action == sqlite3.SQLITE_INSERT and table == 'ordinary_tool_records':
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        if kind == 'sqlite':
            self.store.db.set_authorizer(deny)
        manager = patch.object(self.store, 'budget', side_effect=finite) if kind == 'budget' else patch.object(
            ordinary, 'append_tool', side_effect=sqlite3.OperationalError('fictional journal transaction unavailable'))
        if kind == 'sqlite':
            manager = patch.object(self.store, 'budget', wraps=budget)
        try:
            with patch.object(asyncio, 'create_subprocess_exec', side_effect=launch), manager:
                with self.assertRaises(Refusal) as refused:
                    await ordinary.tool(self.store, attempt, 'owned-fault1107',
                        [sys.executable, '-B', '-c', 'import time; print("owned original",flush=True); time.sleep(30)'],
                        str(self.repo), policy)
            # These assertions precede cleanup: the implementation, not a
            # finally block in this fixture, must already have waited it.
            self.assertEqual(len(originals), 1)
            self.assertIsNotNone(originals[0].returncode)
            record = refused.exception.collection_record
            self.assertEqual(record['pid'], originals[0].pid)
            self.assertEqual(record['exit'], originals[0].returncode)
            self.assertIsInstance(record['exit'], int)
            (self.area/'ORIGINAL-COLLECTION1107.json').write_text(encode(record)+'\n')
            self.assertFalse(record['complete'])
            self.assertIn('capture_error', record)
            self.assertEqual(self.store.one('SELECT state FROM ordinary_runs')['state'], 'intent')
            self.assertTrue(self.store.rows('SELECT * FROM ordinary_resources'))
            self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])
            self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
            if kind != 'budget':
                self.assertIn('journal_error', record)
        finally:
            self.store.db.set_authorizer(None)
            # Failure-only safety: never used to satisfy the assertions above.
            for proc in originals:
                if proc.returncode is None:
                    await ordinary.stop_and_wait(proc)

    async def test_initial_budget_failure_collects_same_original_before_test_cleanup(self):
        await self.fault('budget')

    async def test_initial_SQLite_insert_and_recovery_journal_failure_collects_original(self):
        await self.fault('sqlite')

    async def test_initial_transaction_failure_collects_original_with_explicit_journal_debt(self):
        await self.fault('transaction')


class FiniteFairness1107(windows.Controls):
    def test_full_finite_backlog_original_END_conservation_and_CLI(self):
        self.worker()
        store = self.store()
        self.alerts(store, 20)
        originals = store.rows('SELECT * FROM alerts ORDER BY id')
        class Board:
            def verify_authority(_, runtime):
                pass  # Explicit fictional current Board authority only.
        async def run():
            from coordinator_runtime.dispatcher import Dispatcher
            dispatcher = Dispatcher(store, models=object(), boards={'Work': Board()})
            for _ in originals:
                dispatcher.custodian_progress()
                await dispatcher.custodian_service.close()
            visits = store.rows('SELECT * FROM custodian_visits ORDER BY rowid')
            self.assertEqual(len(visits), len(originals))
            self.assertEqual({v['occurrence'] for v in visits}, {v['id'] for v in originals})
            self.assertTrue(all(v['pid'] and v['numeric_end'] == 0 and v['state'] == 'held' for v in visits))
            self.assertEqual(store.rows('SELECT * FROM alerts ORDER BY id'), originals)
        asyncio.run(run())
        from coordinator_runtime import cli
        self.assertIn('window-basis', cli.parser()._subparsers._group_actions[0].choices)


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for name in ('test_initial_budget_failure_collects_same_original_before_test_cleanup',
                 'test_initial_SQLite_insert_and_recovery_journal_failure_collects_original',
                 'test_initial_transaction_failure_collects_original_with_explicit_journal_debt'):
        suite.addTest(OrdinaryCollection1107(name))
    suite.addTest(FiniteFairness1107('test_full_finite_backlog_original_END_conservation_and_CLI'))
    return suite
