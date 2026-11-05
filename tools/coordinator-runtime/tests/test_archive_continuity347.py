"""Supported custody/episode/release lifecycle in isolated private fixtures.

Public schemas, conservation files and retirement/release operations execute.
Clocks, actual-custodian testimony and NULL-native collection are fiction: these
tests establish neither real elapsed 24h nor any actual archive/consumer release.
"""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordinator_runtime import capacity, retirement
from coordinator_runtime.cleanup import sweep
from coordinator_runtime.contracts import Refusal, digest, encode
from test_corrections304 import PublicCustody
import test_integration343 as combined


class ArchiveContinuity(PublicCustody):
    def conserved(self):
        board, key, post, receipt = self.setup_delivery()
        self.runtime.db.execute('UPDATE outboxes SET board_receipt=? WHERE id=?',
                                (encode({'fixture': 'shared custody required'}), key))
        # The changed exact outbox needs fresh recipient consent and basis.
        receipt = self.custody_receipt(board, key)
        result = board.retire_shared_custody(self.runtime, key, receipt)
        path = Path(result['canonical_archive'])
        self.assertTrue(path.is_file())
        self.assertIsNone(board.conn.execute('SELECT seq FROM posts WHERE seq=?', (post,)).fetchone())
        return board, key, result, path

    def retire_original(self):
        current = retirement.basis(self.runtime, 'fictional-episode-0')
        retirement.apply(self.runtime, current['root'], 'fictional-issuer', self._retirement_receipt(current))
        self.assertEqual(self.runtime.rows('SELECT * FROM events'), [])
        self.assertEqual(self.runtime.rows('SELECT * FROM outboxes'), [])

    def test_original_first_preserves_exact_binding_reconciliation_and_later_release(self):
        board, key, result, path = self.conserved()
        intent = self.runtime.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (key,))
        raw = path.read_bytes()
        self.retire_original()
        self.assertEqual(self.runtime.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (key,)), intent)
        self.assertEqual(board.reconcile_shared_custody(self.runtime, key), result)
        # A copy's consumer can finish later than conservation/original retirement.
        completed = result['conserved_at'] + 120.
        self.runtime.clock = lambda: completed + capacity.RETENTION
        receipt = self.release(result, completed)
        released = board.release_shared_archive(self.runtime, key, receipt)
        self.assertEqual(released['original_witness'], json.loads(raw))
        self.assertEqual(released['receipt'], receipt)
        self.assertFalse(path.exists())
        self.assertEqual(self.runtime.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (key,)), intent)

    def test_copy_first_still_allows_qualified_original_retirement(self):
        board, key, result, path = self.conserved()
        self.runtime.clock = lambda: result['conserved_at'] + capacity.RETENTION
        board.release_shared_archive(self.runtime, key, self.release(result, result['conserved_at']))
        self.assertFalse(path.exists())
        self.retire_original()

    def test_original_first_release_refuses_insufficient_held_young_foreign_and_changed_copy(self):
        board, key, result, path = self.conserved()
        self.retire_original()
        raw = path.read_bytes()
        intent = self.runtime.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (key,))
        self.assertIsNotNone(intent)
        completed = result['conserved_at'] + 120.
        self.runtime.clock = lambda: completed + capacity.RETENTION
        good = self.release(result, completed)
        bad_receipts = []
        for hold in capacity.HOLDS:
            bad = copy.deepcopy(good); bad['holds'][hold] = ['fictional unresolved original duty']
            bad_receipts.append(bad)
        for change in ({'hash': 'foreign-copy-hash'}, {'originals': {}},
                       {'custodian': 'fictional-foreign-custodian'},
                       {'qualified_at': self.runtime.clock() - 61},
                       {'processing': {'completed_at': result['conserved_at'] - 1, 'evidence': 'fictional invalid clock'}},
                       {'processing': {'completed_at': completed + 1, 'evidence': 'fictional young consumer'}}):
            bad_receipts.append({**good, **change})
        bad = copy.deepcopy(good)
        next(iter(bad['originals'].values()))['hash'] = 'foreign-original-hash'
        bad_receipts.append(bad)
        for index, bad in enumerate(bad_receipts):
            with self.subTest(case=index):
                with self.assertRaises(Refusal): board.release_shared_archive(self.runtime, key, bad)
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(self.runtime.one('SELECT * FROM shared_custody_intents WHERE delivery=?', (key,)), intent)
        # An otherwise valid witness for another exact delivery cannot select it.
        with self.assertRaises(Refusal): board.release_shared_archive(self.runtime, 'fictional-foreign-delivery', good)
        with patch.object(board.store, 'acting_session', side_effect=Refusal('fictional foreign issuer')):
            with self.assertRaises(Refusal): board.release_shared_archive(self.runtime, key, good)
        changed = json.loads(raw); changed['custody']['conservation'] = 'fictional changed copy'
        path.write_text(encode(changed))
        changed_raw = path.read_bytes()
        with self.assertRaises(Refusal): board.release_shared_archive(self.runtime, key, good)
        self.assertEqual(path.read_bytes(), changed_raw)


class GroupArchiveContinuity(unittest.TestCase):
    def test_supported_group_conserve_original_retire_then_release_without_refund(self):
        fixture = combined.Combined(methodName='runTest')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        n, store = fixture.n, fixture.s
        board, conn, public = n.board, fixture.f.conn, fixture.f.public
        _, rows = n.capture()
        row = rows[0]
        # Use the same addressed-consumer protocol with a genuine generated
        # pointer marker at INSERT. Immutable public triggers stay enabled.
        def address(outbox):
            actor, key = store.config['actor'], outbox['id']
            post = conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,ref,created_at) VALUES(?,'fictional-Work','coordinator-runtime','handoff','fictional pointer',?,'fictional-time')", (actor, 'delivery:' + key)).lastrowid
            conn.execute('INSERT INTO threads VALUES(?,?,?,?,?)', (post, 'fictional', 'coordinator-runtime', actor, 'fictional-time'))
            conn.execute('INSERT INTO thread_posts VALUES(?,?)', (post, post))
            notice = conn.execute("INSERT INTO notification_outbox(recipient,post_seq,thread_id,event,title,sender,created_at,route) VALUES('fictional-Work',?,?,'open','fictional',?,'fictional-time','managed')", (post, post, actor)).lastrowid
            conn.execute("INSERT INTO coordinator_deliveries_v1(id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created) VALUES(?,'fictional-grant-Work','fictional-Work',?,?,'fictional-Work','alert','settled',?,?,?,'posted','fictional-time')", (key, actor, outbox['producer'], outbox['payload'], post, notice))
            board.software_delivery(store, outbox, fixture.f.boards)
            return store.event(store.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (key,))['event'])
        with patch.object(n, 'address', side_effect=address):
            event = n.consume(row)
        n.now = 88000.; sweep(store)
        current = board.shared_custody_basis(store, row['id'])
        common = {'basis': current['basis'], 'holds': {h: [] for h in capacity.HOLDS},
                  'qualified_at': n.now, 'evidence': 'fictional complete all-custodian testimony'}
        board.shared_custody_consent(store, row['id'], {**common, 'reply_route_closed': True,
                                                       'conservation': 'fictional full originals conserved'})
        # Only actor identity is projected; the public pointer retirement helper
        # and its exact transaction-scoped guard execute against the full schema.
        def retire_pointer(*args):
            with patch.object(public, 'acting_session', side_effect=board.store.acting_session):
                return public.retire_coordinator_pointer(*args)
        with patch.object(board.store, 'retire_coordinator_pointer', side_effect=retire_pointer, create=True):
            result = board.retire_shared_custody(store, row['id'], {**common,
                'custodian': 'fictional-archive-custodian', 'archive': str(store.home/'shared-custody'/row['id']),
                'archive_budget_bytes': 1048576, 'archive_existing_bytes': 0,
                'conservation': 'fictional original history and full occurrences conserved'})
        path = Path(result['canonical_archive']); witness = json.loads(path.read_text())
        self.assertEqual(witness['original']['material']['delivery']['payload'], row['payload'])
        self.assertTrue(witness['original']['material']['software'])
        self.assertIsNone(conn.execute('SELECT id FROM coordinator_deliveries_v1 WHERE id=?', (row['id'],)).fetchone())
        self.assertIsNone(conn.execute('SELECT delivery FROM coordinator_software_deliveries_v1 WHERE delivery=?', (row['id'],)).fetchone())
        charges = store.rows('SELECT * FROM service_windows')
        epochs = store.rows('SELECT * FROM prospective_authorities')
        sequences = store.rows('SELECT * FROM sqlite_sequence')
        receipt = fixture.receipt(event['id'])
        before = fixture.snap()
        try:
            retired = retirement.apply(store, event['id'], 'fictional-Work', receipt)
        except Refusal:
            # Preserve the real failure while checking that no partial local
            # retirement or copy removal occurred. Later assertions stay owed.
            self.assertEqual(fixture.snap(), before)
            self.assertTrue(path.is_file())
            raise
        self.assertEqual(set(retired['retired']['members']['occurrences']), set(receipt['occurrences']))
        self.assertIsNone(store.one('SELECT * FROM outboxes WHERE id=?', (row['id'],)))
        self.assertEqual(board.reconcile_shared_custody(store, row['id']), result)
        n.now += capacity.RETENTION
        released = board.release_shared_archive(store, row['id'], {
            'hash': digest(witness), 'qualified_at': n.now, 'holds': {h: [] for h in capacity.HOLDS},
            'evidence': 'fictional later eligible full copy release', 'custodian': 'fictional-archive-custodian',
            'processing': {'completed_at': result['conserved_at'], 'evidence': 'fictional whole-copy processing completed'},
            'originals': {name: {'hash': digest(value), 'custodian': 'fictional-original-custodian',
                                  'evidence': 'fictional full original conserved'} for name, value in witness['original']['material'].items()}})
        self.assertEqual(released['original_witness'], witness)
        self.assertFalse(path.exists())
        self.assertEqual(store.rows('SELECT * FROM service_windows'), charges)
        self.assertEqual(store.rows('SELECT * FROM prospective_authorities'), epochs)
        self.assertEqual(store.rows('SELECT * FROM sqlite_sequence'), sequences)
        n.conserved()


# Reuse fixture construction, without selecting unrelated inherited tests.
for name in dir(PublicCustody):
    if name.startswith('test_') and name not in ArchiveContinuity.__dict__:
        setattr(ArchiveContinuity, name, None)
del name, PublicCustody

if __name__ == '__main__': unittest.main(verbosity=2)
