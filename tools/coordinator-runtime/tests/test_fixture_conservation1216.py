"""Independent DECISION1216 oracles: WAL-only data and owner-route adversity.

These are owned fictional fixtures. They create no provider or current rights.
All directories and failed/partial states remain available after each case.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import opaque_review, reviews
from coordinator_runtime.contracts import Refusal
from fixture_conservation import conserve, readback, verify, body, CloseGate
import test_historical_verification1041 as historical


class Conservation1216(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='conservation1216-', dir='/fixtures'))

    def test_WAL_only_row_and_exact_SHM_survive_readback_and_original_close(self):
        original = self.area / 'original'
        original.mkdir()
        connection = sqlite3.connect(original / 'journal.sqlite')
        gate = CloseGate(original, self.area / 'conserved', connection.close)
        try:
            self.assertEqual(connection.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
            connection.execute('PRAGMA wal_autocheckpoint=0')
            connection.execute('CREATE TABLE oracle(value TEXT)')
            connection.commit()
            connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            connection.execute("INSERT INTO oracle VALUES('independent-WAL-only-oracle1216')")
            connection.commit()
            expected = {p.name: body(p) for p in original.iterdir()}
            self.assertIn('journal.sqlite-wal', expected)
            self.assertIn('journal.sqlite-shm', expected)
            self.assertGreater(len(expected['journal.sqlite-wal']), 0)
            record = gate.preserve()
            result = readback(record, self.area / 'logical')
            reader = sqlite3.connect((self.area / 'logical/journal.sqlite').as_uri() + '?mode=ro', uri=True)
            try:
                self.assertEqual(reader.execute('SELECT value FROM oracle').fetchall(),
                                 [('independent-WAL-only-oracle1216',)])
            finally:
                reader.close()
            self.assertEqual(result['databases'][0]['rows']['oracle'], 1)
            self.assertEqual(result['databases'][0]['integrity'], [('ok',)])
            self.assertEqual({p.name: body(p) for p in Path(record['physical']).iterdir()}, expected)
        finally:
            gate.close()  # Retries before close; failed attempts and live ownership stay.
        self.assertEqual(verify(record), len(expected))
        self.assertEqual(body(Path(record['physical']) / 'journal.sqlite-shm'), expected['journal.sqlite-shm'])

    def test_digest_without_bytes_and_tampered_copy_are_not_conservation(self):
        original = self.area / 'original'
        original.mkdir()
        (original / 'oracle.txt').write_bytes(b'failed-state-oracle1216')
        record = conserve(original, self.area / 'conserved')
        changed = copy.deepcopy(record)
        changed['physical'] = str(self.area / 'nonexistent-bytes')
        with self.assertRaises(FileNotFoundError):
            verify(changed)
        # Deliberately corrupt a separate control copy; retain both states.
        other = conserve(original, self.area / 'adverse')
        path = Path(other['physical']) / 'oracle.txt'
        path.chmod(0o600)
        path.write_bytes(b'changed-oracle')
        with self.assertRaisesRegex(RuntimeError, 'conserved bytes changed'):
            verify(other)
        self.assertEqual(verify(record), 1)
        self.assertEqual((original / 'oracle.txt').read_bytes(), b'failed-state-oracle1216')


class Compatibility1216(unittest.TestCase):
    def test_route_only_owner_refuses_before_task_attempt_allocation(self):
        fixture = historical.Historical1041('test_existing_unrecorded_revoked_source_supported_without_renewal')
        original = historical.original_review_policy
        def legacy(caller):
            policy = original(caller)
            del policy['transport']
            return policy
        try:
            with patch.object(historical, 'original_review_policy', legacy):
                with self.assertRaisesRegex(Refusal, 'route-only Reviews'):
                    fixture.setUp()
            self.assertEqual(fixture.s.one("SELECT COUNT(*) n FROM attempts WHERE kind='task'")['n'], 0)
        finally:
            fixture.doCleanups()

    def test_supported_owner_binding_keeps_network_write_and_route_guards(self):
        task = dict(execution='owner', binding=dict(opaque_review.BINDING), role='Reviews', phase='proposer',
                    effects='none', sandbox='read-only', network=False, effect_authority={'write_roots': []})
        policy = {'transport': opaque_review.VERSION}
        self.assertEqual(reviews.execution_binding(task, policy), opaque_review.BINDING)
        with self.assertRaisesRegex(Refusal, 'route-only Reviews'):
            reviews.execution_binding(task, {})
        for change in (dict(network=True), dict(effects='owned-artifacts'),
                       dict(binding=dict(reviews.BINDING)), dict(effect_authority={'write_roots': ['/fictional']})):
            with self.subTest(change=change), self.assertRaisesRegex(Refusal, 'exact selected read-only owner'):
                reviews.execution_binding({**task, **change}, policy)
