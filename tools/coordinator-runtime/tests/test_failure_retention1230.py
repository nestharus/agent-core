"""DECISION1228 QP: ordinary failed conservation must not consume its oracle.

New fictional SQLite fixtures only; no historical fixture or current journal.
The bytes, live connection, failed attempts and separate readbacks are retained.
"""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import fixture_conservation as fc
import focused_qualification1216 as fq


class FailureRetention1230(unittest.TestCase):
    def setUp(self):
        fc.capacity(Path('/fixtures'))
        self.area = Path(tempfile.mkdtemp(prefix='retention1230-', dir='/fixtures'))

    def oracle(self, root, factory=sqlite3.Connection):
        fc.directory(root)
        connection = sqlite3.connect(root/'journal.sqlite', factory=factory)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA wal_autocheckpoint=0')
        connection.execute('CREATE TABLE oracle(value TEXT)')
        connection.commit()
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        connection.execute("INSERT INTO oracle VALUES('required-preclose1230')")
        connection.commit()
        return connection, {p.name: fc.body(p) for p in root.iterdir()}

    def test_close_gate_keeps_WAL_SHM_and_live_owner_after_copy_and_fsync_failures(self):
        original = self.area/'original'
        connection, expected = self.oracle(original)
        closed = []
        def close():
            closed.append(True)
            connection.close()
        gate = fc.CloseGate(original, self.area/'saved', close)
        real_write = fc.write
        failed = []
        def fail(path, value):
            if len(failed) == 0 and path.name.endswith('-wal'):
                failed.append(str(path))
                raise OSError('injected ordinary WAL copy failure')
            if len(failed) == 1 and path.name.endswith('-shm'):
                failed.append(str(path))
                with patch.object(fc.os, 'fsync', side_effect=OSError('injected fsync failure')):
                    return real_write(path, value)
            return real_write(path, value)
        with patch.object(fc, 'write', side_effect=fail):
            with self.assertRaises(OSError): gate.preserve()
            self.assertIsNone(gate.record)
            self.assertIn(gate, fc.CloseGate.pending)
            with self.assertRaises(OSError): gate.close()
            self.assertFalse(closed)
            self.assertEqual(connection.execute('SELECT 1').fetchall(), [(1,)])
            self.assertEqual({p.name: fc.body(p) for p in original.iterdir()}, expected)
            residues = {str(p): fc.body(p) for n in (1,2)
                        for p in fc.files(self.area/('saved-attempt-'+str(n)))}
            gate.close()  # Same live owner, resources restored, verified bytes before close.
        record = gate.record
        self.assertEqual(closed, [True])
        self.assertNotIn(gate, fc.CloseGate.pending)
        self.assertEqual({p.name: fc.body(p) for p in Path(record['physical']).iterdir()}, expected)
        self.assertEqual({p: fc.body(Path(p)) for p in residues}, residues)
        self.assertEqual(fc.verify(record), len(expected))
        result = fc.readback(record, self.area/'readback')
        self.assertEqual(result['databases'][0]['rows']['oracle'], 1)
        self.assertEqual(fc.body(Path(record['physical'])/'journal.sqlite-shm'), expected['journal.sqlite-shm'])

    def test_recorder_failed_snapshot_retries_before_close_and_handback(self):
        original_root, output = self.area/'originals', self.area/'record'
        fc.directory(original_root); fc.directory(output)
        recorder = fq.Recorder(output, original_root)
        case = unittest.FunctionTestCase(lambda: None)
        recorder.startTest(case)
        with patch.object(sqlite3, 'connect', new=recorder.connect):
            connection, expected = self.oracle(original_root/'oracle')
        real_conserve = fq.conserve
        attempts = []
        def fail(root, target):
            attempts.append(str(target))
            if len(attempts) <= 2:
                # Actual partial artifact creation precedes the ordinary failure.
                fc.directory(target)
                fc.write(target/'failed-prefix', b'partial is not the oracle')
                raise OSError('injected conservation unavailable')
            return real_conserve(root, target)
        with patch.object(fq, 'conserve', side_effect=fail):
            with self.assertRaises(OSError): recorder.snapshot(case)
            self.assertFalse(recorder.snapshotted)
            with self.assertRaises(OSError): connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            self.assertTrue(recorder.conservation_pending)
            self.assertEqual({p.name: fc.body(p) for p in (original_root/'oracle').iterdir()}, expected)
            connection.close()
        self.assertEqual(len(attempts), 3)
        self.assertTrue(recorder.snapshotted)
        self.assertFalse(recorder.conservation_pending)
        self.assertEqual({p.name: fc.body(p) for p in Path(recorder.physical[-1]['physical']).iterdir()}, expected)
        for target in attempts[:2]:
            self.assertEqual(fc.body(Path(target)/'failed-prefix'), b'partial is not the oracle')
        recorder.addSuccess(case); recorder.stopTest(case); recorder.stream.close()
        self.assertEqual(json.loads((output/'case-1.json').read_text())['outcome'], 'PASS')
