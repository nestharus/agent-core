"""Prospective archive exclusions precede acquisition in isolated fiction.

Supported conservation/configuration/authority protocols execute; inherited
NULL-native actors, clocks and custody assertions prove no actual consent/24h.
"""
from contextlib import ExitStack
import errno
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from coordinator_runtime import capacity, configuration, processing
from coordinator_runtime.contracts import Refusal, digest, encode
from test_archive_continuity347 import GroupArchiveContinuity


class ArchiveExclusions(unittest.TestCase):
    def setUp(self):
        self.group = GroupArchiveContinuity(methodName='runTest')
        self.addCleanup(self.group.doCleanups)
        self.fixture, self.row, self.event, self.result, self.path, self.witness = self.group.conserved()

    def narrow(self, excluded):
        f, old = self.fixture.f, self.fixture.s
        intent = old.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (self.row['id'],))
        previous = digest(old.config)
        processing.revoke(old, f.boards, self.fixture.key)
        f.value = configuration.candidate(old, str(f.directory/'narrowed.json'), ['bi', 'qe'],
                                          scope_options={'exclusions': [str(excluded)]})
        Path(f.value['operator_config']).write_text(encode(f.value))
        _, transition = f.transition()
        store = f.runtime
        store.clock = lambda: self.fixture.n.now
        self.fixture.s = self.fixture.c.s = self.fixture.n.s = store
        self.fixture.n.board = f.boards['Work']
        self.fixture.key = self.fixture.c.issue(self.fixture.c.selection(max_windows=8))
        self.assertEqual(transition['previous'], previous)
        self.assertIn(str(excluded), store.config['artifact_exclusions'])
        self.assertEqual(store.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (self.row['id'],)), intent)
        self.assertTrue(self.fixture.n.board.verify_authority(store))
        self.assertTrue(store.processing.current())
        self.assertIsNotNone(old.one('SELECT revoked FROM processing_capabilities WHERE id=?', (self.fixture.n.key,))['revoked'])
        return store, self.fixture.n.board

    def release_receipt(self, store):
        return {'hash': digest(self.witness), 'qualified_at': store.clock(),
                'holds': {h: [] for h in capacity.HOLDS},
                'evidence': 'fictional independently eligible archive copy',
                'custodian': 'fictional-archive-custodian',
                'processing': {'completed_at': self.result['conserved_at'],
                               'evidence': 'fictional completed copy processing'},
                'originals': {name: {'hash': digest(value), 'custodian': 'fictional-original-custodian',
                                     'evidence': 'fictional full original conservation'}
                              for name, value in self.witness['original']['material'].items()}}

    def assert_excluded_without_acquisition(self, store, operation):
        before = self.fixture.snap()
        shared = list(self.fixture.f.conn.iterdump())
        attempts = []
        # Fail on the first attempted metadata/body/removal of this synthetic
        # path. Exact exclusion must refuse lexically, before these sentinels.
        def denied(*args, **kwargs):
            attempts.append(True)
            raise AssertionError('excluded archive acquisition/removal reached')
        with ExitStack() as stack:
            for name in ('stat', 'lstat', 'open', 'read_text', 'read_bytes', 'unlink',
                         'exists', 'is_file', 'is_symlink'):
                original = getattr(Path, name)
                def guarded(path, *args, _original=original, **kwargs):
                    if path == self.path:
                        return denied()
                    return _original(path, *args, **kwargs)
                stack.enter_context(patch.object(Path, name, guarded))
            with self.assertRaisesRegex(Refusal, 'excluded store before metadata'):
                operation()
        self.assertEqual(attempts, [])
        self.assertEqual(self.fixture.snap(), before)
        self.assertEqual(list(self.fixture.f.conn.iterdump()), shared)

    def test_new_exact_exclusion_blocks_retired_and_lost_return_entries_before_acquisition(self):
        raw, info = self.path.read_bytes(), self.path.stat()
        # Existing archive was lawful under the previous configuration.
        self.assertEqual(self.fixture.n.board.reconcile_shared_custody(self.fixture.s, self.row['id']), self.result)
        store, board = self.narrow(self.path)
        self.fixture.n.now += capacity.RETENTION
        release = self.release_receipt(store)
        self.assert_excluded_without_acquisition(store, lambda: board.reconcile_shared_custody(store, self.row['id']))
        self.assert_excluded_without_acquisition(store, lambda: board.release_shared_archive(store, self.row['id'], release))
        # The retirement-only reader must retain the same pre-acquisition fence.
        self.assert_excluded_without_acquisition(store, lambda: board.conserved_receiving_material(store, self.fixture.f.conn, self.row['id']))
        # Simulate the already-supported lost local return; old intent remains
        # charged and cannot authorize acquisition under the new selection.
        store.db.execute("UPDATE shared_custody_intents SET state='prepared',receipt=NULL WHERE delivery=?", (self.row['id'],))
        self.assert_excluded_without_acquisition(store, lambda: board.reconcile_shared_custody(store, self.row['id']))
        # External fixture observer only: production above made zero accesses.
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(self.path.stat(), info)

    def test_unrelated_exclusion_preserves_reconcile_release_and_configuration_chronology(self):
        store, board = self.narrow(self.path.parent/'fictional-unrelated-copy')
        self.assertEqual(board.reconcile_shared_custody(store, self.row['id']), self.result)
        # Fresh prospective authority cannot launder the old software consumer
        # into new retirement authority after the configuration boundary.
        before = self.fixture.snap()
        from coordinator_runtime import retirement
        with self.assertRaises(Refusal):
            retirement.apply(store, self.event['id'], 'fictional-Work', self.fixture.receipt(self.event['id']))
        self.assertEqual(self.fixture.snap(), before)
        self.fixture.n.now += capacity.RETENTION
        released = board.release_shared_archive(store, self.row['id'], self.release_receipt(store))
        self.assertEqual(released['original_witness'], self.witness)
        self.assertFalse(self.path.exists())
        self.assertEqual(store.one('SELECT state FROM shared_custody_intents WHERE delivery=?', (self.row['id'],))['state'], 'retired')

    def test_kernel_source_readonly_fixture_writable_network_isolated(self):
        with self.assertRaises(OSError) as refused:
            Path(__file__).open('ab')
        self.assertEqual(refused.exception.errno, errno.EROFS)
        own = self.fixture.s.home/'fictional-isolation-witness'
        own.write_text('private fixture only')
        self.assertEqual(own.read_text(), 'private fixture only')
        with socket.socket() as connection:
            with self.assertRaises(OSError) as refused:
                connection.connect(('192.0.2.1', 9))
        self.assertEqual(refused.exception.errno, errno.ENETUNREACH)


if __name__ == '__main__':
    unittest.main(verbosity=2)
