"""Decision1092 outcomes on owned fiction. No actual rights or effects.

Normal Store.finish_job/failure_delivery and retirement.apply run without
replacement. Retirement's continuing issuer/selection is an explicit fiction;
all source/consumer/effect attestations are fictional, not actual grants.
"""
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, queued, result, collect
from coordinator_runtime import oneoff, cleanup, retirement, capacity
from coordinator_runtime.contracts import Refusal, Backpressure, digest, encode
from coordinator_runtime.store import Store


TABLES = ('oneoff_recovery', 'oneoff_terminal_recovery',
          'oneoff_collection_recovery', 'oneoff_progress_recovery')


class Correction(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='fiction1092-', dir=os.environ['ONEOFF1077_FIXTURES']))
        self.now = 100000.
        self.config = config_at(self.area)
        self.s = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.s.close)

    def reserve(self, name='original'):
        message = event(self.config, name)
        queued(self.s, message)
        job = self.s.reserve()
        self.assertIsNotNone(job)
        attempt = self.s.start_job(job['id'], job['token'])
        # Synthetic current-origin stamp BEFORE launch and original collection.
        row = self.s.attempt(attempt)
        detail = {**json.loads(row['detail']), 'processing_capability':'fictional1092'}
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), attempt))
        oneoff.prepare(self.s, attempt, 'Recover exact fictional purpose '+name,
                       {'cwd':str(self.area), 'effects':'none'}, {'type':'object'})
        return message, job, attempt

    def alias(self, semantic='PARTIAL', **outcome):
        message, job, attempt = self.reserve()
        original = result(semantic, 'blocked', 'Retain unresolved independent finding')
        collect(self.s, attempt, original, **outcome)
        sealed = self.bundle(attempt)
        self.s.finish_job(job['id'], job['token'])
        return message, job, attempt, original, sealed

    def bundle(self, attempt):
        # Independent complete record inventory, not the proposed API's output.
        return {table:self.s.rows('SELECT * FROM '+table+' WHERE attempt=?'+
                                  (' ORDER BY sequence' if table.endswith('progress_recovery') else ''),
                                  (attempt,)) for table in TABLES}

    def database(self):
        return {row['name']:self.s.rows('SELECT * FROM "'+row['name']+'"')
                for row in self.s.rows("SELECT name FROM sqlite_master WHERE type='table'")}

    def assert_alias(self, semantic, **outcome):
        message, job, attempt, original, sealed = self.alias(semantic, **outcome)
        view = oneoff.snapshot(self.s, attempt)
        self.assertEqual(json.loads(view['original_collection']['result']), original)
        self.assertEqual(self.bundle(attempt)['oneoff_collection_recovery'][0]['original'],
                         sealed['oneoff_collection_recovery'][0]['original'])
        self.assertEqual(view['collection_hash'], sealed['oneoff_recovery'][0]['collection_hash'])
        self.assertEqual(json.loads(view['collection']['detail'])['contract_normalization']['projection'], 'blocker')
        self.assertFalse(oneoff.recovery_hold(self.s, self.s.attempt(attempt)))
        self.assertEqual(self.s.job(job['id'])['state'], 'held')
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(message['id'],))['processed_at'])
        self.assertFalse(view['permission_to_replay'])
        progress = self.bundle(attempt)['oneoff_progress_recovery']
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]['collector'], self.s.controller)
        self.assertEqual(progress[0]['before_hash'], view['collection_hash'])
        self.assertNotEqual(progress[0]['after_hash'], progress[0]['before_hash'])
        self.assertEqual(self.s.rows('PRAGMA foreign_key_check'), [])

    def test_partial_alias_normal_finish_preserves_original_and_recovery(self):
        self.assert_alias('PARTIAL')

    def test_failed_alias_capture_failure_still_has_useful_recovery(self):
        self.assert_alias('FAILED', code=7, error='fictional nonzero return')

    def test_unknown_alias_normalization_is_idempotent(self):
        _, job, attempt, original, _ = self.alias('UNKNOWN')
        before = self.bundle(attempt)
        self.s.finish_job(job['id'], job['token'])
        self.assertEqual(self.bundle(attempt), before)
        self.assertEqual(json.loads(oneoff.snapshot(self.s, attempt)['original_collection']['result']), original)

    def test_unregistered_alias_keeps_existing_delivery_contract(self):
        message = event(self.config, 'unregistered-alias')
        queued(self.s, message)
        job = self.s.reserve(); attempt = self.s.start_job(job['id'], job['token'])
        original = result('PARTIAL', 'blocked')
        collect(self.s, attempt, original)
        self.s.finish_job(job['id'], job['token'])
        row = self.s.attempt(attempt)
        self.assertEqual(json.loads(row['result']), original)
        self.assertEqual(json.loads(row['detail'])['contract_normalization']['projection'], 'blocker')
        self.assertFalse(any(self.bundle(attempt).values()))
        self.assertEqual(self.s.job(job['id'])['state'], 'held')

    def test_alias_progress_capacity_failure_keeps_factual_detail_and_gap(self):
        _, job, attempt = self.reserve()
        original = result('PARTIAL', 'blocked')
        collect(self.s, attempt, original)
        retained = self.bundle(attempt)['oneoff_collection_recovery'][0]['original']
        budget = self.s.budget
        def finite(kind, *args, **kwargs):
            if kind is None:
                raise Backpressure('fictional finite progress evidence capacity')
            return budget(kind, *args, **kwargs)
        with patch.object(self.s, 'budget', side_effect=finite):
            self.s.finish_job(job['id'], job['token'])
        current = self.bundle(attempt)
        self.assertEqual(current['oneoff_collection_recovery'][0]['original'], retained)
        self.assertIn('finite progress', current['oneoff_collection_recovery'][0]['error'])
        self.assertIn('contract_normalization', json.loads(self.s.attempt(attempt)['detail']))
        self.assertTrue(oneoff.recovery_hold(self.s, self.s.attempt(attempt)))
        self.assertRaises(Refusal, oneoff.snapshot, self.s, attempt)

    def completed(self, name='retire'):
        message, job, attempt = self.reserve(name)
        self.s.begin(attempt, {'fictional_original_creation':True})
        self.s.session(attempt, 'fictional-owned1092')
        answer = result()
        oneoff.checkpoint(self.s, attempt, {'result':answer}, {'external_effects':'none-fictional'})
        self.s.collect(attempt, {'result':answer,'exit':0,'capture':'complete','cleanup':'done',
                                'error':None,'detail':{}})
        self.s.finish_job(job['id'], job['token'])
        self.assertEqual(self.s.job(job['id'])['state'], 'closed')
        with self.s.tx():
            detail = {**json.loads(self.s.attempt(attempt)['detail']), 'fictional_derived':'consumer observed'}
            oneoff.advance(self.s, attempt, {'detail':encode(detail)}, 'fictional consumer observation')
        return message, job, attempt

    def admission(self):
        # Current issuer/read scope is fictional, while local eligibility,
        # dependency, all-hold, receipt, conservation and SQL paths stay real.
        for row in self.s.rows("SELECT id,detail FROM attempts WHERE kind='classifier'"):
            self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',
                              (encode({**json.loads(row['detail']),'processing_capability':'fictional1092'}),row['id']))
        self.s.processing = SimpleNamespace(current=lambda:({'id':'fictional1092','issuer':'fictional-issuer'},
                                                            {'service':{}}), retirement_event=lambda *a:True)
        self.addCleanup(setattr, self.s, 'processing', None)

    def age(self, message):
        self.now += 86400
        outcome = cleanup.retire_event(self.s, self.s.one('SELECT * FROM events WHERE id=?',(message['id'],)))
        self.assertEqual(outcome['state'], 'retired')

    def receipt(self, message):
        current = retirement.basis(self.s, message['id'])
        names = ['sources','results'] + (['recovery'] if current.get('recovery') else [])
        return {'basis':current['basis'],'qualified_at':self.now,'holds':{h:[] for h in capacity.HOLDS},
                'evidence':'fictional all custodians; no actual consent',
                **{name:{key:{'hash':value,'custodian':'fictional-original-custodian',
                              'evidence':'owned fictional exact archive and consumer settlement',
                              'disposition':'conserved-at-original-source'} for key,value in current[name].items()}
                   for name in names}}

    def refuse(self, message, receipt=None):
        before = self.database()
        self.assertRaises(Refusal, retirement.apply, self.s, message['id'], 'fictional-issuer',
                          receipt if receipt is not None else self.receipt(message))
        self.assertEqual(self.database(), before, 'refusal must roll back the whole logical cohort')

    def test_final_apply_conserves_full_recovery_and_foreign_cohort_with_FKs(self):
        message, job, attempt = self.completed()
        other, other_job, other_attempt = self.completed('unrelated-required-consumer')
        unrelated = self.bundle(other_attempt)
        required = self.bundle(attempt)
        self.assertTrue(all(required[t] for t in TABLES))
        archive = self.area/'required-recovery.json'
        archive.write_text(encode(required))
        original_bytes = archive.read_bytes()
        self.age(message)
        self.admission()
        current = retirement.basis(self.s, message['id'])
        if 'recovery' in current:
            self.assertEqual(current['recovery'][attempt], digest(required))
        receipt = self.receipt(message)
        returned = retirement.apply(self.s, message['id'], 'fictional-issuer', receipt)
        self.assertEqual(returned['retired']['members']['jobs'], [job['id']])
        self.assertIsNone(self.s.one('SELECT id FROM attempts WHERE id=?',(attempt,)))
        self.assertTrue(all(not self.bundle(attempt)[t] for t in TABLES))
        self.assertEqual(self.bundle(other_attempt), unrelated)
        self.assertIsNotNone(self.s.job(other_job['id']))
        self.assertEqual(archive.read_bytes(), original_bytes)
        self.assertEqual(json.loads(original_bytes), required)
        self.assertEqual(self.s.db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
        self.assertEqual(self.s.rows('PRAGMA foreign_key_check'), [])
        path = self.s.path
        self.s.close()
        self.s.db = sqlite3.connect(path, isolation_level=None)
        self.s.db.row_factory = sqlite3.Row
        self.s.db.execute('PRAGMA foreign_keys=ON')
        self.assertEqual(self.s.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(self.bundle(other_attempt), unrelated)
        self.assertIsNone(self.s.one('SELECT id FROM events WHERE id=?',(message['id'],)))

    def test_recovery_conservation_receipt_is_required_and_exact(self):
        message, _, attempt = self.completed(); self.age(message); self.admission()
        good = self.receipt(message)
        self.assertIn('recovery', good, 'launch/terminal/original/progress need their own conservation evidence')
        for replacement in (None, {}, {attempt:{**good['recovery'][attempt],'hash':'changed'}},
                            {attempt:{**good['recovery'][attempt],'disposition':'canonical-delete'}}):
            bad = copy.deepcopy(good)
            if replacement is None:
                bad.pop('recovery')
            else:
                bad['recovery'] = replacement
            self.refuse(message, bad)

    def test_checkpoint_and_progress_mutation_invalidate_prepared_retirement(self):
        message, _, attempt = self.completed(); self.age(message); self.admission()
        good = self.receipt(message)
        before = retirement.basis(self.s, message['id'])['basis']
        self.s.db.execute('UPDATE oneoff_progress_recovery SET basis=? WHERE attempt=?',
                          ('fictional changed evidence after qualification',attempt))
        self.assertNotEqual(retirement.basis(self.s, message['id'])['basis'], before)
        self.refuse(message, good)
        # A fresh all-holds claim cannot override a corrupted checkpoint, even
        # after queue material retired and task lookup no longer joins it.
        self.s.db.execute("UPDATE oneoff_terminal_recovery SET body='{}' WHERE attempt=?",(attempt,))
        self.refuse(message)

    def test_new_hold_reopen_and_young_generation_refuse_final_apply(self):
        message, job, _ = self.completed()
        self.admission()
        self.now += 86399
        self.refuse(message)
        self.now += 1
        retired = cleanup.retire_event(self.s, self.s.one('SELECT * FROM events WHERE id=?',(message['id'],)))
        self.assertEqual(retired['state'], 'retired')
        good = self.receipt(message)
        for hold in capacity.HOLDS:
            bad = copy.deepcopy(good); bad['holds'][hold] = ['fictional consumer still needs original']
            self.refuse(message, bad)
        self.s.set_hold(message['id'], 'fictional privacy and current use')
        self.refuse(message)
        self.s.set_hold(message['id'], None)
        self.s.db.execute("UPDATE jobs SET state='held',effects='unknown' WHERE id=?",(job['id'],))
        self.refuse(message)

    def test_capsule_retirement_SQL_failure_rolls_back_recovery_and_parent_rows(self):
        message, _, _ = self.completed(); self.age(message); self.admission()
        before = self.database()
        receipt = self.receipt(message)
        self.s.db.execute("CREATE TEMP TRIGGER fictional_stop1092 BEFORE DELETE ON attempts "
                          "BEGIN SELECT RAISE(ABORT,'fictional interruption after child deletion'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'fictional interruption'):
            retirement.apply(self.s, message['id'], 'fictional-issuer', receipt)
        self.assertEqual(self.database(), before)
        self.assertEqual(self.s.rows('PRAGMA foreign_key_check'), [])

    def test_non_capsule_cohort_keeps_existing_conservation_contract(self):
        message = event(self.config, 'unregistered-retirement')
        queued(self.s, message)
        job = self.s.reserve(); attempt = self.s.start_job(job['id'], job['token'])
        collect(self.s, attempt, result())
        self.s.finish_job(job['id'], job['token'])
        row = self.s.attempt(attempt)
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',
                          (encode({**json.loads(row['detail']),'processing_capability':'fictional1092'}),attempt))
        self.age(message); self.admission()
        receipt = self.receipt(message)
        self.assertNotIn('recovery', receipt)
        retirement.apply(self.s, message['id'], 'fictional-issuer', receipt)
        self.assertIsNone(self.s.one('SELECT id FROM attempts WHERE id=?',(attempt,)))
        self.assertEqual(self.s.rows('PRAGMA foreign_key_check'), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
