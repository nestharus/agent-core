"""Decision1182 ordinary acquisition on owned nonsecret fiction.

Real Store reservation/start, current processing/source checks, resource maps,
retention pins/lock, SQLite, path reads and publication execute. Base's logical
Board/grant, selected capability, NULL native identity and clock remain seams.
No installed rights, private origin, historic incident or live job is modeled.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import patch

from coordinator_runtime import bounded_log, custody, local_integration, publication, routine
from coordinator_runtime.configuration import require_current_job
from coordinator_runtime.contracts import Refusal, digest, encode
from test_bounded311 import Base


class OrdinaryOrigin1182(Base):
    def configure(self):
        self.canonical = self.area/'canonical'
        self.canonical.mkdir()
        self.target = self.canonical/'report.bin'
        self.body = b'owned ordinary canonical body\x00\xff\n'
        self.target.write_bytes(self.body)
        self.sha = hashlib.sha256(self.body).hexdigest()
        # Never allocated or inspected: Q is outside effective roots and the
        # attempt artifact arena, not beneath the resource fixture's cwd.
        self.excluded = self.area/'fiction-excluded-origin'
        self.stage = str(self.area/'fiction-recorded-stage')
        self.config['artifact_exclusions'] = [str(self.excluded)]
        for task in self.config['tasks'].values():
            task['cwd'] = str(self.canonical)
            task['effect_authority']['read_roots'] = [str(self.canonical)]
            task['effect_authority']['write_roots'] = [str(self.canonical)]
        self.task = self.config['tasks']['wi']
        self.task.update(effects='owner-reconcile',
                         routine_completion={'kind':'file-witness', 'targets':[str(self.target)]})

    def record(self, path, attempt):
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
            (attempt, str(path), 'role-owned', 'fiction-original-owner',
             encode({'sha256':self.sha, 'size':len(self.body)}), self.sha))

    def restrict(self, older=False):
        self.record(self.target, 'fiction-known-canonical')
        if older:
            self.store.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                ('fiction-old-snapshot', 'wi', 'fiction-original-grant', '{}',
                 encode({self.stage:{'exists':True, 'sha256':self.sha}}), 'reconciled'))
        else:
            self.record(self.stage, 'fiction-second-custody')
        self.store.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',
                             ('fiction-old-stage', str(self.excluded), self.stage))

    def admitted(self):
        job, attempt = self.job('Work', 'wi')
        self.assertEqual(job['state'], 'running')
        self.assertTrue(self.store.artifact_root(attempt).is_dir())
        # These checks run unchanged and actually succeed before the test's
        # interception. They establish fixture admissions, not real grants.
        self.store.require_execution_open(job['id'])
        local_integration.current_sources(self.store, job)
        require_current_job(self.store, {**job, 'active_attempt':attempt})
        self.assertEqual(self.board.completion_authority(self.store, 'wi')['id'],
                         'fictional-grant-Work')
        with publication.snapshot_lock(self.store):
            local_integration.current_sources(self.store, job)
        self.assertFalse(self.store.db.in_transaction)
        return job, attempt

    def conserved(self):
        return {table:self.store.rows('SELECT * FROM '+table) for table in
                ('artifact_blobs', 'artifact_custody', 'routine_runs', 'routine_stages',
                 'file_publications', 'canonical_backups')}

    @contextmanager
    def no_acquisition(self, target):
        touched = []
        original_stat, original_lstat, original_open = Path.stat, Path.lstat, os.open
        forbidden = [Path(target), self.excluded]

        def allowed(path):
            if any(Path(path) == p or Path(path).is_relative_to(p) for p in forbidden):
                touched.append(str(path))
                raise AssertionError('prohibited target metadata/body acquired')

        def checked_stat(path, *args, **kwargs):
            allowed(path)
            return original_stat(path, *args, **kwargs)

        def checked_lstat(path, *args, **kwargs):
            allowed(path)
            return original_lstat(path, *args, **kwargs)

        def checked_open(path, *args, **kwargs):
            if isinstance(path, (str, bytes, os.PathLike)):
                allowed(os.fsdecode(path))
            return original_open(path, *args, **kwargs)

        def authorize(action, table, column, *unused):
            if action == sqlite3.SQLITE_READ and table == 'artifact_blobs' and column == 'body':
                raise AssertionError('retained body is no alternative acquisition')
            return sqlite3.SQLITE_OK

        self.store.db.set_authorizer(authorize)
        try:
            with patch.object(Path, 'stat', checked_stat), patch.object(Path, 'lstat', checked_lstat), \
                 patch.object(os, 'open', checked_open), \
                 patch.object(routine, 'read_file', side_effect=AssertionError('premature body/hash')):
                yield
            self.assertEqual(touched, [])
        finally:
            self.store.db.set_authorizer(None)

    def refusal(self, older=False):
        self.restrict(older)
        job, attempt = self.admitted()
        before, inode = self.conserved(), self.target.stat().st_ino
        with self.no_acquisition(self.target):
            with self.assertRaisesRegex(Refusal, 'opaque source excluded before acquisition'):
                routine.prepare(self.store, self.board, job, attempt, self.task)
        self.assertEqual(self.conserved(), before)
        self.assertEqual(self.target.read_bytes(), self.body)
        self.assertEqual(self.target.stat().st_ino, inode)
        self.assertFalse((self.store.artifact_root(attempt)/'staged').exists())
        self.assertFalse(self.store.db.in_transaction)
        self.assertIsNone(self.store.attempt(attempt)['session'])

    def test_known_second_custody_stage_refuses_ordinary_before_metadata(self):
        self.refusal()

    def test_known_older_snapshot_stage_refuses_ordinary_before_metadata(self):
        self.refusal(older=True)

    def test_new_restriction_after_policy_is_checked_before_snapshot_acquisition(self):
        job, attempt = self.admitted()
        actual = routine.snapshot
        calls = []

        def restricted_snapshot(store, targets):
            calls.append(list(targets))
            self.restrict()
            before = self.conserved()
            with self.no_acquisition(self.target):
                with self.assertRaisesRegex(Refusal, 'opaque source excluded before acquisition'):
                    actual(store, targets)
            self.assertEqual(self.conserved(), before)
            raise Refusal('fixture recorded restriction reached snapshot boundary')

        with patch.object(routine, 'snapshot', side_effect=restricted_snapshot), \
             patch.object(self.board, 'completion_authority', wraps=self.board.completion_authority) as grant:
            with self.assertRaisesRegex(Refusal, 'reached snapshot boundary'):
                routine.prepare(self.store, self.board, job, attempt, self.task)
        self.assertEqual(calls, [[str(self.target)]])
        grant.assert_called_once()
        self.assertIsNone(self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (attempt,)))
        self.assertFalse(self.store.db.in_transaction)

    def test_fitting_known_ordinary_graph_keeps_exact_preimage_and_prepared_custody(self):
        self.record(self.target, 'fiction-lawful-canonical')
        self.record(self.stage, 'fiction-lawful-other-copy')
        job, attempt = self.admitted()
        inode = self.target.stat().st_ino
        with patch.object(routine, 'read_file', wraps=custody.read_file) as read:
            routine.prepare(self.store, self.board, job, attempt, self.task)
        read.assert_called_once()
        run = self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (attempt,))
        self.assertEqual(run['state'], 'prepared')
        self.assertEqual(json.loads(run['before_files'])[str(self.target)]['sha256'], self.sha)
        stage = publication.stages(self.store, attempt)[str(self.target)]
        self.assertEqual(Path(stage).read_bytes(), self.body)
        publication.conserve_stages(self.store, attempt, self.task)
        self.assertIsNotNone(self.store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?',
                                           (attempt, stage)))
        self.assertEqual(self.target.read_bytes(), self.body)
        self.assertEqual(self.target.stat().st_ino, inode)
        self.assertFalse(self.store.db.in_transaction)

    def test_expired_authority_is_distinct_from_origin_refusal(self):
        job, attempt = self.admitted()
        self.board.expired = True
        with patch.object(routine, 'snapshot', side_effect=AssertionError('no body without authority')):
            with self.assertRaisesRegex(Refusal, 'expired role authority'):
                routine.prepare(self.store, self.board, job, attempt, self.task)
        self.assertIsNone(self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (attempt,)))

    def test_current_source_hold_precedes_ordinary_target_admission(self):
        job, attempt = self.admitted()
        self.store.db.execute('UPDATE events SET hold=?', ('fiction newly held source',))
        with patch.object(routine, 'guard_path', side_effect=AssertionError('no target admission under hold')), \
             patch.object(routine, 'snapshot', side_effect=AssertionError('no snapshot under hold')):
            with self.assertRaisesRegex(Refusal, 'currentness/admission changed'):
                routine.prepare(self.store, self.board, job, attempt, self.task)
        self.assertIsNone(self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (attempt,)))

    def test_hash_only_later_association_does_not_invent_prior_path_knowledge(self):
        # No recorded P->hash link exists before the owned P read. This is an
        # unknown association, not entitlement to a known forbidden derivative.
        self.record(self.excluded, 'fiction-only-hash-known')
        with patch.object(routine, 'read_file', wraps=custody.read_file) as read:
            before = routine.snapshot(self.store, [str(self.target)])
        read.assert_called_once()
        self.assertEqual(before[str(self.target)]['sha256'], self.sha)
        with self.assertRaisesRegex(Refusal, 'opaque source excluded before acquisition'):
            custody.guard_frozen(self.store, self.sha, path=str(self.target))

    def bounded(self):
        peers = [self.target, *[self.canonical/('peer-'+str(i)) for i in range(5)]]
        for p in peers[1:]:
            p.write_text('owned nonbounded peer\n')
        self.log = self.canonical/'WORK_LOG.md'
        self.log.write_bytes(b'owned bounded line\n'*20+b'owned tail\x00\xff')
        self.policy = {'kind':bounded_log.KIND, 'targets':[*map(str, peers), str(self.log)],
                       'bounded_log':{'target':str(self.log), 'max_lines':12,
                                      'max_bytes':8192, 'max_entry_bytes':16384}}
        self.task['routine_completion'] = self.policy
        bounded_log.validate(self.task, self.policy)
        self.selection['basis']['configuration'] = digest(self.config)
        self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(self.selection),))

    def test_nonbounded_peer_of_seven_target_policy_keeps_preacquisition_guard(self):
        self.bounded()
        self.refusal()

    def test_bounded_log_known_excluded_origin_refuses_before_prefix_or_metadata(self):
        self.bounded()
        self.record(self.log, 'fiction-known-log')
        self.record(self.excluded, 'fiction-known-log-origin')
        job, attempt = self.admitted()
        with self.no_acquisition(self.log):
            with self.assertRaisesRegex(Refusal, 'opaque source excluded before acquisition'):
                routine.prepare(self.store, self.board, job, attempt, self.task)
            with self.assertRaisesRegex(Refusal, 'opaque source excluded before acquisition'):
                bounded_log.observe(self.store, self.policy['bounded_log'])
        self.assertIsNone(self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (attempt,)))

    def test_unrestricted_bounded_prefix_remains_limited_without_whole_preimage(self):
        self.bounded()
        job, attempt = self.admitted()
        with patch.object(bounded_log, 'prefix', wraps=bounded_log.prefix) as prefix, \
             patch.object(routine, 'read_file', wraps=custody.read_file) as read:
            routine.prepare(self.store, self.board, job, attempt, self.task)
        self.assertEqual(read.call_count, 6)
        prefix.assert_called_once()
        before = json.loads(self.store.one('SELECT before_files FROM routine_runs WHERE attempt=?', (attempt,))['before_files'])
        self.assertEqual(len(before), 7)
        self.assertEqual(bytes.fromhex(before[str(self.log)]['bounded_prefix_hex']), b'owned bounded line\n'*12)
        self.assertIsNone(before[str(self.log)]['whole_log_hash'])
        self.assertNotIn('sha256', before[str(self.log)])
        self.assertFalse(self.store.rows('SELECT * FROM artifact_custody WHERE path=?', (str(self.log),)))
