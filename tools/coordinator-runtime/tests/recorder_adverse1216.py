"""Explicit recorder development control; deliberately fails, never discovered.

Select Adverse1216.runTest only for the recorder's adverse development encounter.
Its nonzero result is required evidence, not a target behavior regression or a
passing qualification. Every byte, trace and original remains retained.
"""
from pathlib import Path
import sqlite3
import tempfile
import unittest


class Adverse1216(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='adverse1216-', dir='/fixtures'))
        self.connection = sqlite3.connect(self.area / 'failed.sqlite')
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA wal_autocheckpoint=0')
        self.connection.execute('CREATE TABLE oracle(value TEXT)')
        self.connection.commit()
        self.connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.connection.execute("INSERT INTO oracle VALUES('intentional-failed-state1216')")
        self.connection.commit()

    def runTest(self):
        self.assertEqual(self.connection.execute('SELECT value FROM oracle').fetchall(),
                         [('intentional-failed-state1216',)])
        self.fail('intentional recorder adverse control1216; preserve failure and exact pre-close oracle')

    def tearDown(self):
        self.connection.close()
