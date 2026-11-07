"""Same-evaluation conflict witnesses, only newly authored synthetic operands."""
import json
import unittest
from unittest.mock import patch

import test_management406 as fixture
from coordinator_runtime import local_integration as local, reservation
from coordinator_runtime.contracts import Refusal, encode


class ReservationConflict671(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Management(methodName='runTest')
        self.addCleanup(self.f.doCleanups); self.f.setUp()
        self.store = self.f.store
        self.target = self.f.home/'synthetic-material671.json'
        self.target.write_text('{"item":{"state":"retained"}}')
        self.points = {k:{'bindings':[{'target':str(self.target),'path':['item']}], 'resources':[]}
                       for k in ('a','alias','b')}
        # Supplied fictional scope resolver below isolates the diagnostic seam;
        # production conflict/material/resource helpers and SQLite remain real.
        self.store.config['local_integration'] = {'max_inflight':5,
            'tasks':{'work-integrator':{'points':list(self.points)}}, 'points':self.points}
        self.row = self.store.one('SELECT * FROM queue WHERE event=?', (self.f.next['id'],))
        self.member = {'event':self.f.next['id']}
        self.scope = {'lane':'anchored','reads':[],'writes':['a'],'versions':{},'sources':[self.f.next['id']]}
        self.prior = {'lane':'anchored','reads':['a'],'writes':[],'sources':[self.f.source['id']]}

    def evaluate(self, *, observe=True):
        self.store.db.execute('INSERT OR REPLACE INTO local_jobs VALUES(?,?,?)',
                             ('synthetic-held','fictional-policy',encode(self.prior)))
        with patch.object(local, 'packet', return_value=self.scope), reservation.Evaluation(self.store,self.row) as evaluation:
            available = local.available(self.store,self.row,[self.member], observe=evaluation.at,
                                       conflict_observe=evaluation.conflict if observe else None)
            self.assertFalse(available)
            evaluation.finish('false')
        return self.view()

    def view(self):
        source = self.store.one('SELECT hash,role FROM events WHERE id=?', (self.f.next['id'],))
        responsibility = self.store.one('SELECT task,phase,state,job FROM queue WHERE event=?', (self.f.next['id'],))
        return reservation.view(self.store,None,self.f.next['id'],source,responsibility,self.store.controller)

    def test_point_access_short_circuits_material_and_prior_resources(self):
        with patch.object(local, 'binding_conflict', side_effect=AssertionError('skipped material helper')):
            view = self.evaluate()
        self.assertEqual(view['local_conflict'], {'schema_version':1,'job':'synthetic-held','arm':'point-access'})
        self.assertEqual((view['predicate'],view['outcome']), ('local-scope-conflict','false'))
        self.assertTrue(view['current'])

    def test_alias_material_arm_uses_existing_operand_evaluation(self):
        self.prior['reads'] = ['alias']
        with patch.object(local, 'resources', wraps=local.resources) as resources:
            view = self.evaluate()
        self.assertEqual(view['local_conflict']['arm'], 'bound-material')
        self.assertEqual(resources.call_count,1)  # Incoming resources only; OR short-circuits prior.

    def test_shared_resource_arm_with_two_readers(self):
        self.scope.update(reads=['a'],writes=[])
        self.prior.update(reads=['b'],writes=[])
        self.points['a']['resources'] = self.points['b']['resources'] = ['synthetic-resource671']
        with patch.object(local, 'resources', wraps=local.resources) as resources:
            view = self.evaluate()
        self.assertEqual(view['local_conflict']['arm'], 'shared-resource')
        self.assertEqual(resources.call_count,2)

    def test_diagnostic_adds_no_scope_material_or_resource_operand_reads(self):
        self.prior['reads'] = ['alias']
        sequences = []
        for enabled in (False,True):
            trace = []; self.store.db.set_trace_callback(trace.append)
            try: self.evaluate(observe=enabled)
            finally: self.store.db.set_trace_callback(None)
            # Observation writes differ; all existing read operands are equal.
            sequences.append([sql for sql in trace if sql.startswith('SELECT')
                              and 'reservation_conflicts' not in sql])
        self.assertEqual(sequences[0],sequences[1])

    def test_helper_refusal_keeps_unknown_arm_and_no_raw_error(self):
        self.prior['reads'] = ['alias']
        with patch.object(local,'binding_conflict',side_effect=Refusal('PRIVATE_HELPER_BODY_671')):
            with self.assertRaises(Refusal): self.evaluate()
        view = self.view()
        self.assertEqual((view['outcome'],view['predicate']), ('refusal','local-scope-conflict'))
        self.assertEqual(view['local_conflict'], {'schema_version':1,'job':None,'arm':'unknown'})
        self.assertNotIn('PRIVATE_HELPER_BODY',encode(view))

    def test_stale_context_and_invalid_enum_withhold_conflicting_identity(self):
        view = self.evaluate(); self.assertEqual(view['local_conflict']['job'],'synthetic-held')
        self.store.db.execute("UPDATE reservation_outcomes SET controller='foreign-controller'")
        self.assertEqual(self.view()['outcome'],'stale')
        self.assertNotIn('synthetic-held',encode(self.view()))
        self.evaluate()
        self.store.db.execute("UPDATE reservation_conflicts SET arm='PRIVATE_BODY_671'")
        self.assertEqual(self.view()['local_conflict']['arm'],'unknown')
        self.assertIsNone(self.view()['local_conflict']['job'])
        self.assertNotIn('PRIVATE_BODY',encode(self.view()))

    def test_observation_replacement_and_fingerprint_prevent_old_witness_reuse(self):
        self.evaluate()
        self.store.db.execute("UPDATE reservation_conflicts SET observation='wrong-evaluation'")
        self.assertIsNone(self.view()['local_conflict']['job'])
        self.evaluate()
        with reservation.Evaluation(self.store,self.row) as evaluation:
            evaluation.failed('role-enabled')
        self.assertNotIn('local_conflict',self.view())
        self.assertEqual(self.store.rows('SELECT event FROM reservation_conflicts'),[])

    def test_read_only_old_journal_without_diagnostic_table_remains_compatible(self):
        self.evaluate(observe=False)
        self.store.db.execute('DROP TABLE reservation_conflicts')
        self.assertEqual(self.view()['local_conflict'], {'schema_version':1,'job':None,'arm':'unknown'})


if __name__ == '__main__': unittest.main(verbosity=2)
