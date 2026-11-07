"""Fictional same-config selection, using owned source copies and SQLite stores.

Native actor/config validation and allocation are the explicit NULL-native 308
fixture seams. __file__ selects a freshly owned release copy: release() measures
real files, not fabricated hashes. Edited code is not executed or independently
accepted here; semantic review remains the genuine Work decision seam.
"""
import copy
import fcntl
import os
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing, retained
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.integration import METADATA_READ_FENCE
import test_configuration308 as protocol
from test_release_acquisition673 import Fixture, SOURCE


class SourceSelection(unittest.TestCase):
    def setUp(self):
        self.f = protocol.CurrentConfiguration()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.copy = Fixture()
        for name in ('work-catalog.md', 'branch-repository.md', 'reviews-selected.md', 'qa-package.md'):
            target = self.copy.directory/'templates'/name
            target.write_bytes((SOURCE/'templates'/name).read_bytes())
        self.location = patch.object(configuration, '__file__', str(self.copy.modules/'configuration.py'))
        self.location.start(); self.addCleanup(self.location.stop)
        self.f.value = configuration.candidate(self.f.runtime, str(self.f.directory/'selected.json'), ['bi', 'qe'])
        self.copy.operator = self.f.directory/'selected.json'
        self.copy.operator.write_text(encode(self.f.value))
        self.f.transition()
        self.runtime = self.f.runtime
        # Fictional original parent receipt, through the supported release API.
        # No actual native END or real runtime collection is asserted.
        processing.release(self.runtime, self.f.boards, self.f.oldkey, 'fictional-old-collector',
                           {'actual_END': 0, 'evidence': ['fictional original parent collection']})
        self.original = copy.deepcopy(self.runtime.config)
        self.before_release = configuration.selected(self.runtime)['basis']['release']
        self.baseline = configuration.latest(self.runtime)

    def change(self, name='configuration.py', suffix='reviewed fictional code correction'):
        path = self.copy.modules/name
        path.write_bytes(path.read_bytes() +
                         ('\ndef fictional_reviewed_decision707():\n    return ' + repr(suffix) + '\n').encode())

    def selection(self, value=None, tasks=None):
        value = self.runtime.config if value is None else value
        return {'basis': configuration.basis(self.runtime, self.f.boards, value,
                                             list(value['tasks']) if tasks is None else tasks),
                'authority': 'fictional Work reviewed this exact source delta; semantics remain an owner decision'}

    def apply(self, selected=None, value=None):
        return configuration.apply(self.runtime, self.f.boards,
                                   self.runtime.config if value is None else value,
                                   self.selection(value) if selected is None else selected)

    def snapshot(self):
        # Only this fixture's tables. No platform/private store inventory.
        return {r['name']: self.runtime.rows('SELECT * FROM "' + r['name'] + '"')
                for r in self.runtime.rows("SELECT name FROM sqlite_master WHERE type='table'")
                if r['name'] not in {'configuration_source_selections', 'allocation_revision',
                                     'allocation_revision_tokens', 'sqlite_sequence'}}

    def test_changed_release_same_config_appends_and_preserves_original_state(self):
        self.change()
        selection = self.selection()
        before, grants = self.snapshot(), list(self.f.conn.iterdump())
        inode = self.runtime.path.stat().st_ino
        result = self.apply(selection)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(grants, list(self.f.conn.iterdump()))
        self.assertEqual(inode, self.runtime.path.stat().st_ino)
        self.assertEqual(self.original, self.runtime.config)
        self.assertEqual(result['configuration'], result['previous'])
        self.assertEqual(result['source_only']['previous_release'], digest(self.before_release))
        self.assertEqual(result['source_only']['changed'], [str(self.copy.modules/'configuration.py')])
        self.assertEqual(configuration.latest(self.runtime)['source_selection'], 1)
        self.assertEqual(configuration.version_metadata(self.runtime)['source_selection'], 1)
        self.assertEqual(configuration.current_binding(self.runtime)['current'], digest(self.original))
        configuration.assert_release(self.runtime)
        self.assertEqual(configuration.task_for_job(self.runtime, self.runtime.job('fictional-old-job')),
                         self.f.original['tasks']['wp'])
        self.assertFalse(configuration.event_allowed(self.runtime, self.f.originals[0]))
        self.assertFalse(configuration.outbox_allowed(self.runtime, self.runtime.one('SELECT * FROM outboxes LIMIT 1')))
        self.assertEqual(self.runtime.job('fictional-old-job')['effects'], 'unknown')
        for sql in ('DELETE FROM configuration_source_selections',
                    "UPDATE configuration_source_selections SET issuer='fictional-foreign'"):
            with self.assertRaises(sqlite3.IntegrityError): self.runtime.db.execute(sql)
        # Startup binding remains exact; old grants/caps are not revived.
        self.runtime._check_config()
        with self.assertRaises(Refusal): processing.Access(self.runtime, self.f.oldkey, self.f.boards).current()
        self.f.issue()
        configuration.assert_release(self.runtime)

    def test_identical_release_cannot_bootstrap_or_select_or_replay(self):
        with patch.object(configuration, 'selected', return_value=None):
            with self.assertRaisesRegex(Refusal, 'existing immutable'):
                configuration.source_change(self.runtime, self.before_release, list(self.original['tasks']))
        with self.assertRaisesRegex(Refusal, 'different runtime code'): self.selection()
        self.change(); selection = self.selection(); self.apply(selection)
        with self.assertRaises(Refusal): self.apply(selection)
        with self.assertRaisesRegex(Refusal, 'different runtime code'): self.selection()
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM configuration_source_selections')['n'], 1)

    def test_second_source_selection_and_later_config_change(self):
        self.change(); self.apply()
        self.change('processing.py'); self.apply()
        self.assertEqual(configuration.latest(self.runtime)['source_selection'], 2)
        value = configuration.candidate(self.runtime, str(self.f.directory/'next.json'), ['bi', 'qe'])
        self.f.directory.joinpath('next.json').write_text(encode(value))
        self.apply(value=value)
        self.assertNotIn('source_selection', configuration.latest(self.runtime))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM configuration_transitions')['n'], 2)

    def test_populated_metadata_reader_fence_stays_valid_without_rewriting(self):
        policy = {'max_inflight': 5, 'points': {'fictional-point': {
            'kind': 'item', 'line': 'fictional707', 'incarnation': 'fictional707',
            'bindings': [{'target': str(self.f.directory/'point.json'), 'path': ['item']}],
            'resources': [], 'protected': [], 'writable': []}},
            'tasks': {'wp': {'capacity': 5, 'discovery_batch': 1, 'points': ['fictional-point'],
                            'authority': 'fictional original reader policy',
                            'method': self.original['tasks']['wp']['templates'][0]}}}
        # A genuine policy delta in this fiction precedes the source-only case.
        self.f.value = configuration.candidate(self.runtime, str(self.f.directory/'reader.json'),
                                               ['bi', 'qe'], scope_options={'local_integration': policy})
        self.f.directory.joinpath('reader.json').write_text(encode(self.f.value))
        self.f.transition(); self.runtime = self.f.runtime
        event = self.f.originals[0]['id']
        members = encode([{'queue': 'fictional-reader-queue', 'event': event}])
        self.runtime.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects,active_attempt) VALUES('fictional-reader','Work','proposer','wp',?,'fictional-reader-controller','fictional-reader-token',900,'held','none','fictional-reader-attempt')", (members,))
        self.runtime.db.execute("INSERT INTO queue(id,event,role,phase,task,state,job) VALUES('fictional-reader-queue',?,'Work','proposer','wp','reserved','fictional-reader')", (event,))
        self.runtime.db.execute("INSERT INTO attempts(id,kind,job,controller,profile,binding,created,begin,ended,collected,exit,state) VALUES('fictional-reader-attempt','task','fictional-reader','fictional-reader-controller',NULL,'{}',900,901,902,903,0,'collected')")
        self.runtime.db.execute("INSERT INTO job_resource_policies VALUES('fictional-reader',?,NULL)", (encode(self.runtime.config['tasks']['wp']),))
        self.runtime.db.execute("INSERT INTO local_jobs VALUES('fictional-reader','fictional-frozen-policy',?)", (encode({'lane': 'anchored', 'reads': ['fictional-point'], 'writes': []}),))
        # Seed an already qualified fictional fence. Its stable witness is
        # evaluated by production code; fence-owner authentication is tested691.
        stable = self.runtime._work_read_metadata_stable('fictional-reader')
        self.runtime.db.execute("INSERT INTO work_read_fences VALUES('fictional-reader','fictional-Work',?,'{}',904)",
                                (encode({'schema': METADATA_READ_FENCE, 'stable': stable}),))
        fence = self.runtime.one("SELECT * FROM work_read_fences WHERE job='fictional-reader'")
        scope = {'lane': 'anchored', 'reads': ['fictional-point'], 'writes': []}
        incoming = {'role': 'Work', 'phase': 'proposer', 'task': 'wp'}
        self.assertTrue(self.runtime.work_read_coexists(incoming, scope, {'id': 'fictional-reader'}))
        self.change(); self.apply()
        self.assertEqual(fence, self.runtime.one("SELECT * FROM work_read_fences WHERE job='fictional-reader'"))
        self.assertEqual(stable, self.runtime._work_read_metadata_stable('fictional-reader'))
        self.assertTrue(self.runtime.work_read_coexists(incoming, scope, {'id': 'fictional-reader'}))

    def test_source_exclusion_guard_precedes_processing_code_acquisition(self):
        with patch.object(configuration, 'release', side_effect=Refusal('fictional exclusion guard')), \
             patch.object(processing, 'implementation', side_effect=AssertionError('premature source acquisition')):
            with self.assertRaisesRegex(Refusal, 'exclusion guard'): self.selection()

    def test_static_dependencies_file_extent_and_task_allowlist_are_frozen(self):
        self.change()
        paths = [self.copy.directory/'templates/coordinator-receive.md',
                 self.copy.root/'tools/message-board/board_store.py',
                 self.copy.root/'tools/direct-child/execution_pool.py',
                 self.copy.directory/'final-release-risk.md']
        for path in paths:
            with self.subTest(path=path.name):
                body = path.read_bytes()
                try:
                    path.write_bytes(body + b'\n# unselected static change\n')
                    with self.assertRaises(Refusal): self.selection()
                finally: path.write_bytes(body)
        body = self.copy.operator.read_text()
        self.copy.operator.write_text(encode({**self.original, 'enabled': True}))
        with self.assertRaises(Refusal): self.selection()
        self.copy.operator.write_text(body)
        added = self.copy.modules/'unselected707.py'
        added.write_text('# owned extra module\n')
        with self.assertRaisesRegex(Refusal, 'file extent'): self.selection()
        added.unlink()  # Exactly owned fixture file, not operational output retirement.
        with self.assertRaisesRegex(Refusal, 'task allowlist'): self.selection(tasks=['wp'])
        with self.assertRaisesRegex(Refusal, 'static dependencies'):
            configuration.source_change(self.runtime, {**self.before_release, 'root': '/fictional-other'}, list(self.original['tasks']))
        routes = self.f.directory/'routes.toml'
        body = routes.read_text()
        routes.write_text(body.replace('fictional-pool-state', 'unapproved-pool-state'))
        with self.assertRaises(Refusal): self.selection()

    def test_owner_basis_lock_and_all_revocations_remain_required(self):
        self.change(); selected = self.selection()
        self.f.boards['Work'].store.actor = 'fictional-foreign'
        with self.assertRaises(Refusal): self.apply(selected)
        self.f.boards['Work'].store.actor = 'fictional-Work'
        self.runtime.db.execute("UPDATE cursors SET seq=8 WHERE role='Work'")
        with self.assertRaisesRegex(Refusal, 'basis changed'): self.apply(selected)
        fd = os.open(self.runtime.home/'service.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(Refusal, 'owns its lock'): self.apply()
        finally: os.close(fd)
        key = processing.select(self.runtime, self.f.boards, self.f.processing_selection())['capability']
        with self.assertRaisesRegex(Refusal, 'revoke'): self.apply()
        processing.revoke(self.runtime, self.f.boards, key)
        # Existing prospective and retained revocation predicates see real rows.
        self.runtime.db.execute("INSERT INTO prospective_authorities(id,selection,event_boundary,job_boundary,created) VALUES('fictional-prospective','{}',0,0,1000)")
        with self.assertRaisesRegex(Refusal, 'revoke'): self.apply()
        self.runtime.db.execute("UPDATE prospective_authorities SET revoked=1000")
        grant = 'fictional-grant-Work'
        self.f.conn.executescript(retained.SCHEMA)
        self.f.conn.execute("INSERT INTO coordinator_retained_caps_v1(id,source_grant,configuration,binding,policy,issuer,created) VALUES('fictional-retained',?,'fictional-config','{}','{}','fictional-Work',1000)", (grant,))
        with self.assertRaisesRegex(Refusal, 'revoke'): self.apply()
        self.f.conn.execute("UPDATE coordinator_retained_caps_v1 SET revoked=1000")
        self.apply()

    def test_original_end_service_and_uncollected_attempt_are_not_inferred(self):
        self.change()
        released = self.runtime.one('SELECT state FROM processing_runs')['state']
        for state in ('owned', '{}', '{"parent_END":{"actual_END":true,"evidence":["fictional"]}}'):
            self.runtime.db.execute('UPDATE processing_runs SET state=?', (state,))
            with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()
        self.runtime.db.execute('UPDATE processing_runs SET state=?', (released,))
        self.runtime.db.execute("INSERT INTO service_runs VALUES('fictional-old-collector',?,'fictional.sock','running',900,NULL,NULL)", (self.f.oldkey,))
        with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()
        self.runtime.db.execute("UPDATE service_runs SET state='returned-awaiting-parent-END',returned=1000")
        self.runtime.db.execute("UPDATE attempts SET controller='fictional-old-collector'")
        with self.assertRaisesRegex(Refusal, 'numeric parent END'): self.apply()

    def test_policy_change_cannot_enter_source_only_path_and_budget_failure_rolls_back(self):
        self.change()
        value = copy.deepcopy(self.original); value['tasks']['wp']['effect_authority']['write_roots'].append('/fixtures')
        with self.assertRaises(Refusal): self.selection(value)
        selected = self.selection()
        with patch.object(self.runtime, 'budget', side_effect=Refusal('fictional exhausted budget')):
            with self.assertRaisesRegex(Refusal, 'budget'): self.apply(selected)
        self.assertEqual(configuration.latest(self.runtime), self.baseline)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM configuration_source_selections')['n'], 0)


if __name__ == '__main__':
    unittest.main()
