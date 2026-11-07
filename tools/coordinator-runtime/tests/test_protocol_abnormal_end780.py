"""Owned NULL-native service-row fiction; no actual service or parent END.

Exercise real Store collection and supported processing-release, including END2.
Run only in the selected source-only sandbox with private /fixtures and TMPDIR.
The public-package/version fixture is inherited fiction, not native qualification.
"""
import copy
import json
import unittest

from coordinator_runtime import configuration, processing
from coordinator_runtime.contracts import Refusal, encode
import test_protocol_upgrade774 as protocol


class ProtocolAbnormalEND(unittest.TestCase):
    def setUp(self):
        self.p = protocol.ProtocolUpgrade(methodName='runTest')
        self.addCleanup(self.p.doCleanups)
        self.p.setUp()
        self.s = self.p.s
        self.boards = self.p.f.boards
        self.controller = self.s.controller

    def original(self, returned=False):
        key = processing.select(self.s, self.boards, self.p.f.processing_selection())['capability']
        self.s.db.execute('INSERT INTO processing_runs VALUES(?,?,?,1000)',
                          (self.controller, key, 'owned'))
        self.s.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,1000,?,?)',
                          (self.controller, key, 'fictional-unused-endpoint',
                           'returned-awaiting-parent-END' if returned else 'serving',
                           1001 if returned else None, 'FICTION: reconciliation UNKNOWN'))
        processing.revoke(self.s, self.boards, key)
        return key

    def attempt(self, name='fictional-owned-attempt'):
        self.s.db.execute("INSERT INTO attempts(id,kind,controller,profile,binding,created) "
                          "VALUES(?,'classifier',?,NULL,'{}',1000)", (name, self.controller))
        return name

    def collect(self, attempt):
        self.s.collect(attempt, {'exit':2, 'result':None, 'capture':'incomplete',
                                'cleanup':'unknown', 'error':'FICTION: old effect UNKNOWN'})

    def release(self, key, end=2):
        return processing.release(self.s, self.boards, key, self.controller,
                                  {'actual_END':end, 'evidence':['FICTION: same original parent collected numeric END']})

    def apply(self):
        value = self.p.draft()
        return configuration.apply(self.s, self.boards, value, self.p.selection(value))

    def snapshot(self):
        # The fixture owns this exact database. Compare all original duties;
        # exclude only the appended transition and normal allocation mutation
        # witnesses advanced by basis capture (as in the source-only fixture).
        return {r['name']:self.s.rows('SELECT * FROM "'+r['name']+'"')
                for r in self.s.rows("SELECT name FROM sqlite_master WHERE type='table'")
                if r['name'] not in {'configuration_transitions', 'sqlite_sequence',
                                     'allocation_revision', 'allocation_revision_tokens'}}

    def test_abnormal_END2_serving_null_upgrades_without_changing_old_unknowns(self):
        key = self.original()
        attempt = self.attempt()
        with self.assertRaisesRegex(Refusal, 'uncollected'):
            self.release(key)
        self.collect(attempt)
        self.assertFalse(self.release(key)['processing_or_effects_complete'])
        before = self.snapshot()
        grants = list(self.p.f.conn.iterdump())
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            configuration.source_originals_stopped(self.s)
        result = self.apply()
        self.assertFalse(result['historical_recovery'])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(grants, list(self.p.f.conn.iterdump()))
        self.assertEqual(self.s.one('SELECT state,returned FROM service_runs'),
                         {'state':'serving', 'returned':None})
        self.assertEqual(self.s.job('fictional-old-job')['effects'], 'unknown')

    def test_normal_service_return_and_parent_END_remain_supported(self):
        key = self.original(returned=True)
        self.release(key, 0)
        configuration.source_originals_stopped(self.s)
        self.apply()

    def test_active_or_returned_without_actual_parent_release_refuses(self):
        self.original()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()
        self.s.db.execute("UPDATE service_runs SET state='returned-awaiting-parent-END',returned=1001")
        with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()

    def test_invalid_parent_END_evidence_refuses(self):
        key = self.original()
        for receipt in ({'actual_END':True,'evidence':['fiction']},
                        {'actual_END':None,'evidence':['fiction']},
                        {'actual_END':2,'evidence':[]},
                        {'actual_END':2,'evidence':[' ']}):
            with self.subTest(receipt=receipt):
                with self.assertRaises(Refusal):
                    processing.release(self.s, self.boards, key, self.controller, receipt)
                with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()

    def test_uncollected_attempt_after_release_still_refuses(self):
        key = self.original(); self.release(key)
        attempt = self.attempt()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()
        self.collect(attempt)
        self.apply()

    def test_foreign_original_or_issuer_cannot_supply_release(self):
        key = self.original()
        receipt = {'actual_END':2, 'evidence':['FICTION: foreign identity is not this original']}
        with self.assertRaisesRegex(Refusal, 'exact original'):
            processing.release(self.s, self.boards, key, 'fictional-foreign', receipt)
        self.boards['Work'].store.actor = 'fictional-foreign'
        with self.assertRaises(Refusal): self.release(key)
        self.boards['Work'].store.actor = 'fictional-Work'
        with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()

    def test_mismatched_service_capability_refuses_even_after_parent_release(self):
        key = self.original(); self.release(key)
        self.s.db.execute("UPDATE service_runs SET capability='fictional-foreign-capability'")
        with self.assertRaisesRegex(Refusal, 'generation'): self.apply()

    def test_current_generation_and_implementation_checks_remain(self):
        key = self.original(); self.release(key)
        saved = json.loads(self.s.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection'])
        for field in ('position', 'source_selection'):
            changed = copy.deepcopy(saved)
            changed['basis']['configuration_transition'][field] = 999
            self.s.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(changed), key))
            with self.assertRaisesRegex(Refusal, 'generation'): self.apply()
        changed = copy.deepcopy(saved)
        changed['basis']['implementation']['store.py'] = 'fictional-foreign-source'
        self.s.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(changed), key))
        with self.assertRaisesRegex(Refusal, 'generation'): self.apply()


if __name__ == '__main__': unittest.main()
