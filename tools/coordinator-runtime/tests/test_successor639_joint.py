"""Joint producer qualification; two owned journals with an explicit scope bridge.

The public QA scope decision is passed to the reader fixture consumer gate.
Outer consumer authority/locking remains the documented 635 fictional seam.
No native execution, external acceptance, or single-journal reachability claim.
"""
from contextlib import nullcontext
import json
from pathlib import Path
from unittest.mock import patch

from coordinator_runtime import publication, resource_scopes, routine
from coordinator_runtime.contracts import Refusal
from test_qa629_repairs import CrossRole
from test_readiness_origin_guard635 import OriginGuard635


class Joint639(CrossRole):
    def consumer(self):
        reader = OriginGuard635('test_permitted_publication_and_delivery_consumers')
        reader.setUp()
        self.addCleanup(reader.doCleanups)
        target, delegate = reader.setup_consumers()
        return reader, target, delegate

    def reconcile_joint(self, reader, delegate):
        decision = resource_scopes.blocked
        with patch('coordinator_runtime.configuration.require_current_job'), \
             patch.object(resource_scopes, 'blocked', side_effect=lambda *_: decision(self.store, self.qa)), \
             patch.object(publication, 'snapshot_lock', side_effect=lambda _: nullcontext()), \
             patch('coordinator_runtime.local_integration.rebase', side_effect=lambda s,j,a,r,t: (r,None)):
            return routine.reconcile(reader.s, delegate, reader.s.jobrow)

    def complete_consumer(self, reader, target, delegate):
        self.assertTrue(self.reconcile_joint(reader, delegate))
        self.assertEqual(target.read_bytes(), b'{"verified":true}')
        run = reader.s.one('SELECT * FROM routine_runs WHERE attempt=?', (reader.s.row['id'],))
        reader.s.jobrow.update(effects='reconciled', effect_receipt=run['receipt'])
        self.assertEqual(reader.deliver(delegate)['state'], 'settled')
        # Recheck current acquisition rights, never cached successful readiness.
        reader.s.config['artifact_exclusions'] = [str(reader.s.path)]
        reader.s.events.clear()
        self.assertIsNone(reader.deliver(delegate))
        self.assertEqual(reader.body_reads(), [])
        self.assertEqual(json.loads(reader.s.row['result'])['unknowns'],
                         json.loads(reader.s.original['result'])['unknowns'])

    def test_joint_overlap_readonly_release_then_guarded_consumption(self):
        job = self.branch()
        reader, target, delegate = self.consumer()
        reader.s.events.clear()
        self.assertTrue(resource_scopes.blocked(self.store, self.qa))
        self.assertFalse(self.reconcile_joint(reader, delegate))
        self.assertEqual(reader.body_reads(), [])
        self.assertEqual(target.read_bytes(), b'{"verified":false}')
        self.assertEqual(reader.s.rows('SELECT * FROM file_publications'), [])
        from support import result
        self.run_job(job, result())
        self.assertEqual(self.store.job(job['id'])['effects'], 'none')
        self.complete_consumer(reader, target, delegate)
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'], 'fictional global UNKNOWN')

    def test_joint_disjoint_unknown_preserved_during_guarded_consumption(self):
        job = self.branch()
        reader, target, delegate = self.consumer()
        self.complete_consumer(reader, target, delegate)
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertIsNone(self.store.job(job['id'])['active_attempt'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [])
