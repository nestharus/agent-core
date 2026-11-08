"""Retained original rights; all transport, principals and ENDs are fictional."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from test_native_footprint985 import ActiveSource985
from test_source_continuity688 import Continuity
from coordinator_runtime import processing, report_scope, resource_scopes
from coordinator_runtime.contracts import Refusal, digest


class Retained995(ActiveSource985):
    def return_interrupted(self):
        # Complete only the fictional transport through the real Executor and
        # service collection path. No synthetic replacement context or receipt.
        self.transport.pending.set_result((6, {'class': 'incomplete'}, None))
        self.source_loop.run_until_complete(self.source_running)
        attempt = self.store.attempt(self.attempt_id)
        self.assertEqual((attempt['state'], attempt['exit'], attempt['capture']),
                         ('collected', 6, 'incomplete'))
        self.assertIsNotNone(attempt['collected'])
        self.assertEqual(self.store.job(self.job['id'])['state'], 'held')
        self.assertEqual(self.store.job(self.job['id'])['effects'], 'none')
        self.assertEqual(self.store.one('SELECT state FROM review_contexts')['state'], 'interrupted')

    def test_returned_interrupted_full_footprint_and_no_promotion(self):
        with self.active():
            original = self.modes()
            self.return_interrupted()
            before = self.store.one('SELECT state,effects,response,active_attempt FROM jobs WHERE id=?', (self.job['id'],))
            attempt = self.store.attempt(self.attempt_id)
            context = self.store.one('SELECT * FROM review_contexts')
            with self.no_bodies():
                self.assertEqual(self.modes(), original)
                for role in ('QA', 'Work', 'Branch'):
                    self.assertFalse(resource_scopes.blocked(self.store, self.candidate(role)))
                reads, writes, staging = original
                for held in dict.fromkeys(writes + [staging[0].parent, self.repo, self.method]):
                    for mode in ('read', 'write'):
                        if mode == 'read' and held in (self.repo, self.method):
                            continue
                        task = copy.deepcopy(self.config['tasks']['work-integrator'])
                        task.pop('routine_completion', None)
                        task['effect_authority']['read_roots'] = [str(self.independent)] + ([str(held)] if mode == 'read' else [])
                        task['effect_authority']['write_roots'] = [str(held)] if mode == 'write' else []
                        with self.subTest(held=str(held), mode=mode):
                            self.assertTrue(resource_scopes.blocked(self.store, self.candidate(), task))
            self.store.db.execute('SAVEPOINT effects995')
            try:
                self.store.db.execute("UPDATE jobs SET effects='reconciled' WHERE id=?", (self.job['id'],))
                task = copy.deepcopy(self.config['tasks']['work-integrator'])
                task['effect_authority']['read_roots'] = [str(writes[0])]
                self.assertTrue(resource_scopes.blocked(self.store, self.candidate(), task))
            finally:
                self.store.db.execute('ROLLBACK TO effects995')
                self.store.db.execute('RELEASE effects995')
            with self.assertRaises(Refusal):
                report_scope.integration_inputs(self.store, dict(role='Reviews', phase='integrator',
                    task='reviews-integrator', package=None, event=self.e['id']))
            self.assertEqual(before, self.store.one('SELECT state,effects,response,active_attempt FROM jobs WHERE id=?', (self.job['id'],)))
            self.assertEqual(attempt, self.store.attempt(self.attempt_id))
            self.assertEqual(context, self.store.one('SELECT * FROM review_contexts'))
            self.assertIsNone(before['response'])

    def test_returned_publication_history_orphan_and_later_opaque_holder(self):
        with self.active():
            self.return_interrupted()
            self.assertFalse(resource_scopes.blocked(self.store, self.candidate()))
            history = self.independent/'retained-history-intent.md'
            temp = self.independent/'retained-publication.tmp'
            self.store.db.execute('SAVEPOINT tails995')
            try:
                self.store.db.execute("INSERT INTO review_history_commits VALUES(?,?,?,?,?,?,?,?)",
                    (self.attempt_id, self.component889, str(history), 'before', 'after',
                     'Fictional retained append; never applied', self.head, 'prepared'))
                for state in ('prepared', 'applied'):
                    self.store.db.execute('UPDATE review_history_commits SET state=? WHERE attempt=?', (state, self.attempt_id))
                    self.assertIn(history, self.modes()[1])
                    self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
                self.store.db.execute('ROLLBACK TO tails995')
                self.store.db.execute("INSERT INTO file_publications(attempt,target,temp,state) VALUES(?,?,?,'prepared')",
                    (self.attempt_id, str(self.catalog), str(temp)))
                self.assertIn(temp, self.modes()[1])
                self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
                self.store.db.execute('ROLLBACK TO tails995')
                self.store.db.execute("INSERT INTO ordinary_resources VALUES('unknown995','orphan995')")
                self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
                self.store.db.execute('ROLLBACK TO tails995')
                self.store.db.execute("INSERT INTO jobs(id,role,phase,task,state,token,members,effects,created,controller) SELECT 'opaque-source853',role,phase,task,state,token,members,'unknown',created,controller FROM jobs WHERE id=?", (self.job['id'],))
                self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
            finally:
                self.store.db.execute('ROLLBACK TO tails995')
                self.store.db.execute('RELEASE tails995')

    def test_interrupted_missing_changed_context_and_unknown_hold_refuse(self):
        with self.active():
            self.return_interrupted()
            self.modes()
            self.assertFalse(resource_scopes.blocked(self.store, self.candidate()))
            faults = [
                ("UPDATE review_contexts SET state='unknown' WHERE component=?", self.component889),
                ("UPDATE review_contexts SET handle='/unbound-handle' WHERE component=?", self.component889),
                ("UPDATE review_contexts SET route='wrong' WHERE component=?", self.component889),
                ("UPDATE review_contexts SET collector='wrong' WHERE component=?", self.component889),
                ("UPDATE jobs SET hold_reason='unknown retained hold' WHERE id=?", self.job['id']),
                ("UPDATE events SET hold='unknown' WHERE id=?", self.e['id']),
                ("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','wrong') WHERE id=?", self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.prospective_epoch','wrong') WHERE id=?", self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.grant_id','wrong') WHERE id=?", self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.task_hash','wrong') WHERE id=?", self.attempt_id),
                ("UPDATE jobs SET members=json_set(members,'$[0].hash','wrong') WHERE id=?", self.job['id']),
                ("UPDATE review_calls SET packet=json_set(packet,'$.selected_task','wrong') WHERE attempt=?", self.attempt_id),
            ]
            for sql, key in faults:
                with self.subTest(fault=sql):
                    self.store.db.execute('SAVEPOINT fault995')
                    try:
                        self.store.db.execute(sql, (key,))
                        with self.no_bodies(), self.assertRaises(Refusal):
                            self.modes()
                        with self.no_bodies():
                            self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
                    finally:
                        self.store.db.execute('ROLLBACK TO fault995')
                        self.store.db.execute('RELEASE fault995')
            original_one = self.store.one
            def missing(sql, args=()):
                if sql.startswith('SELECT component,capability,collector,profile,route,handle,state,created FROM review_contexts'):
                    return None
                return original_one(sql, args)
            with patch.object(self.store, 'one', side_effect=missing), self.no_bodies():
                with self.assertRaises(Refusal): self.modes()
                self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
            def opaque_before_packet(sql, args=()):
                if '$.body.review' in sql:
                    raise AssertionError('opaque hold acquired factual packet')
                return original_one(sql, args)
            self.store.db.execute('SAVEPOINT opaque995')
            try:
                self.store.db.execute("UPDATE jobs SET hold_reason='unknown custody' WHERE id=?", (self.job['id'],))
                with patch.object(self.store, 'one', side_effect=opaque_before_packet):
                    with self.assertRaises(Refusal): self.modes()
                    self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
            finally:
                self.store.db.execute('ROLLBACK TO opaque995')
                self.store.db.execute('RELEASE opaque995')


class Deploy995(Continuity):
    def setUp(self):
        # Frozen original704 implementation is the synthetic installed origin.
        pins = json.loads(Path('/public/production-pins.json').read_text())
        actual = processing.implementation()
        self.assertEqual(pins['candidate'], actual)
        self.enterContext(patch.object(processing, 'implementation', return_value=pins['original']))
        super().setUp()
        # Preserve fixture patch object identities and immutable origin records.
        self.new_impl.clear()
        self.new_impl.update(pins['candidate'])
        self.assertEqual(self.original_impl['reviews.py'], self.new_impl['reviews.py'])
        self.modules = sorted(n for n in self.new_impl if self.new_impl[n] != self.original_impl[n])
        self.assertEqual(self.modules, ['resource_scopes.py'])
        root = self.old_release['root'] + '/tools/coordinator-runtime/coordinator_runtime/'
        self.new_release.clear()
        self.new_release.update(copy.deepcopy(self.old_release))
        for n in self.modules: self.new_release['files'][root+n] = self.new_impl[n]

    def test_actual_v1_controller_admits_exact_production_delta(self):
        # Parent test exercises source_basis, apply_source, Access, readback,
        # unchanged cap/epoch/grants/admission, replay and a reopened Store.
        self.test_real_admitted_board_and_whole_attributed_report_keep_same_authority()

    def test_actual_v1_controller_refuses_reviews_delta(self):
        self.new_impl['reviews.py'] = digest('fictional forbidden reviews delta')
        root = self.old_release['root'] + '/tools/coordinator-runtime/coordinator_runtime/'
        self.new_release['files'][root+'reviews.py'] = self.new_impl['reviews.py']
        self.modules = ['resource_scopes.py', 'reviews.py']
        before = self.untouched()
        with self.assertRaisesRegex(Refusal, 'source-repair-v1'):
            self.request()
        self.assertEqual(before, self.untouched())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([*(Retained995(n) for n in Retained995.__dict__ if n.startswith('test_')),
                              *(Deploy995(n) for n in Deploy995.__dict__ if n.startswith('test_'))])
