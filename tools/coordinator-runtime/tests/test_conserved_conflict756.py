"""Real local reservation over owned fiction; no provider or business result."""
from contextlib import contextmanager
import copy
import json
import unittest
from unittest.mock import patch

from coordinator_runtime import local_integration as local
from coordinator_runtime.contracts import digest, encode, validate_config
import test_role_execution_fence751 as fixture


class ConservedConflict756(unittest.TestCase):
    insert = fixture.RoleFence751.insert
    call = fixture.RoleFence751.call
    conserved = fixture.RoleFence751.conserved
    duties = fixture.RoleFence751.duties
    selection = fixture.RoleFence751.selection
    managed = fixture.RoleFence751.managed
    receipt = fixture.RoleFence751.receipt
    fence = fixture.RoleFence751.fence

    def setUp(self):
        original = fixture.config_at
        def configured(home):
            config = original(home)
            target = home / 'points756.json'
            target.write_text('{"a":0,"b":0}')
            points = {key: dict(kind='item', line='fixture756', incarnation='one',
                bindings=[dict(target=str(target), path=[key])], resources=[],
                protected=[], writable=[]) for key in ('a', 'b')}
            points['alias-a'] = copy.deepcopy(points['a'])
            task = config['tasks']['work-proposer']
            config['local_integration'] = dict(max_inflight=1, points=points,
                tasks={'work-proposer': dict(capacity=1, discovery_batch=1,
                    points=list(points), authority='Owned fictional exact file points',
                    method=task['templates'][0])})
            return validate_config(config)
        with patch.object(fixture, 'config_at', side_effect=configured):
            fixture.RoleFence751.setUp(self)

    def make_job(self):
        self.role, self.phase = 'Work', 'proposer'
        fixture.RoleFence751.make_job(self)
        self.set_source(self.source, reads=['a'])
        self.set_source(self.next, reads=['b'])
        local.record_job(self.store, self.store.job('old-job751'))
        self.store.db.execute('UPDATE events SET hold=? WHERE id=?',
                              ('Original source remains held', self.source['id']))
        self.assertEqual(self.store.rows('SELECT job FROM work_read_fences'), [])

    def set_source(self, source, *, reads=(), writes=(), branch=None):
        target = self.home / 'points756.json'
        bodies = {str(target): target.read_bytes()}
        source['integration'] = dict(reads=list(reads), writes=list(writes),
            versions={k:local.version(self.store, k, bodies) for k in set(reads) | set(writes)})
        if branch is not None:
            source['branch_binding'] = branch
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',
                              (encode(source), digest(source), source['id']))
        if source is self.source:
            members = json.loads(self.store.job('old-job751')['members'])
            members[0]['hash'] = digest(source)
            self.store.db.execute('UPDATE jobs SET members=? WHERE id=?',
                                  (encode(members), 'old-job751'))

    @contextmanager
    def no_old_body(self):
        original_event, original_one, original_rows = self.store.event, self.store.one, self.store.rows
        def event(key):
            if key == self.source['id']:
                raise AssertionError('held original body acquired')
            return original_event(key)
        def query(fn, sql, values=()):
            normalized = ' '.join(sql.lower().split())
            if self.source['id'] in values and ('payload' in normalized or 'select * from events' in normalized):
                raise AssertionError('held source payload SQL acquired')
            return fn(sql, values)
        with patch.object(self.store, 'event', side_effect=event), \
             patch.object(self.store, 'one', side_effect=lambda s,v=():query(original_one,s,v)), \
             patch.object(self.store, 'rows', side_effect=lambda s,v=():query(original_rows,s,v)):
            yield

    def reserve(self):
        # The stopped grant remains stopped; this explicitly models separately
        # authorized future intake, as in751. All local reservation code is real.
        with patch.object(self.store, 'role_enabled', return_value=True):
            return self.store.reserve()

    def test_held_known_scope_disjoint_real_reservation_without_body(self):
        self.fence()
        before = self.duties()
        with self.no_old_body():
            fresh = self.reserve()
        self.assertIsNotNone(fresh)
        self.assertEqual(json.loads(fresh['members'])[0]['event'], self.next['id'])
        # Compare retained original rows only; new reservation rows are lawful.
        after = self.duties()
        for table, rows in before.items():
            for row in rows:
                if table == 'queue' and row['id'] == 'new-queue751':
                    continue  # This incoming queue is precisely what was reserved.
                self.assertIn(row, after[table], table)
        self.assertEqual(self.store.attempt('old-attempt751')['semantic'], 'UNKNOWN')
        self.assertEqual(self.store.one('SELECT hold IS NOT NULL AS held FROM events WHERE id=?',
            (self.source['id'],)), {'held':1})

    def test_unheld_disjoint_real_reservation(self):
        self.store.db.execute('UPDATE events SET hold=NULL WHERE id=?', (self.source['id'],))
        self.fence()
        self.assertIsNotNone(self.reserve())

    def test_point_material_and_resource_conflicts_without_old_body(self):
        self.fence()
        for key, arm in [('a','point-access'), ('alias-a','bound-material')]:
            with self.subTest(arm=arm):
                self.set_source(self.next, writes=[key])
                with self.no_old_body():
                    self.assertIsNone(self.reserve())
                self.assertEqual(self.store.one('SELECT arm FROM reservation_conflicts WHERE event=?',
                    (self.next['id'],)), {'arm':arm})
        self.set_source(self.next, reads=['b'])
        for key in ('a','b'):
            self.config['local_integration']['points'][key]['resources'] = ['shared756']
        with self.no_old_body():
            self.assertIsNone(self.reserve())
        self.assertEqual(self.store.one('SELECT arm FROM reservation_conflicts WHERE event=?',
            (self.next['id'],)), {'arm':'shared-resource'})

    def test_branch_bound_request_refuses_necessary_held_body(self):
        self.set_source(self.next, reads=['b'], branch='branch756')
        self.fence()
        with self.no_old_body():
            self.assertIsNone(self.reserve())
        error = self.store.one('SELECT detail FROM operational_errors WHERE subject=?', (self.next['id'],))
        self.assertIn('held', json.loads(error['detail'])['dependency'])

    def test_unheld_same_branch_conflicts_and_distinct_branch_progresses(self):
        self.set_source(self.source, reads=['a'], branch='old-branch756')
        self.set_source(self.next, reads=['b'], branch='old-branch756')
        self.store.db.execute('UPDATE events SET hold=NULL WHERE id=?', (self.source['id'],))
        self.fence()
        self.assertIsNone(self.reserve())
        self.set_source(self.next, reads=['b'], branch='distinct-branch756')
        self.assertIsNotNone(self.reserve())


if __name__ == '__main__':
    unittest.main(verbosity=2)
