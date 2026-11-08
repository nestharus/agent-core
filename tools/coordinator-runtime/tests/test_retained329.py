"""Recorded-origin/witness controls. All bytes and custody are owned fiction.

Run only in the positive source-RO bwrap view. Identity parsing is an explicit
logical entitlement seam; no native/provider/profile/session/turn encounter.
"""
import base64
import copy
import hashlib
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import cli, custody, publication, bounded_log
from coordinator_runtime.contracts import Refusal, encode
from test_repair324 import Export


class Retained(unittest.TestCase):
    def setUp(self):
        self.f = Export()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.s = self.f.store

    def record(self, path, attempt='fiction-prior'):
        self.s.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                          (attempt, str(path), 'role-owned', 'fiction-prior-owner',
                           encode({'sha256':self.f.sha, 'size':len(self.f.body)}), self.f.sha))

    def no_body(self, operation):
        reads = []
        def authorize(action, table, column, *unused):
            if action == sqlite3.SQLITE_READ and table == 'artifact_blobs' and column == 'body':
                reads.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.s.db.set_authorizer(authorize)
        try:
            with patch.object(cli.hashlib, 'sha256', side_effect=AssertionError('premature hash')), \
                 patch.object(cli.base64, 'b64encode', side_effect=AssertionError('premature export')), \
                 patch.object(Path, 'stat', side_effect=AssertionError('origin metadata acquisition')):
                with self.assertRaises(Refusal):
                    operation()
            self.assertEqual(reads, [])
        finally:
            self.s.db.set_authorizer(None)

    def export_refuses(self):
        before = self.s.rows('SELECT * FROM artifact_custody')
        for caller in ('fiction-owner', 'fiction-consumer'):
            with self.subTest(caller=caller):
                self.no_body(lambda:self.f.export(caller))
        self.assertEqual(self.s.rows('SELECT * FROM artifact_custody'), before)
        self.assertEqual(self.s.one('SELECT body FROM artifact_blobs')['body'], self.f.body)

    def test_second_custody_path_retains_excluded_stage_target(self):
        held = str(self.f.area/'fiction-excluded-target')
        stage = str(self.f.area/'fiction-old-stage')
        self.record(stage)
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)', ('fiction-stage', held, stage))
        self.s.config['artifact_exclusions'] = [held]
        self.export_refuses()
        self.no_body(lambda:custody.frozen_body(self.s, self.f.sha, path=self.f.path))
        witness = {'path':self.f.path, 'sha256':self.f.sha, 'custody':'artifact_blobs'}
        self.no_body(lambda:custody.materialize(self.s, [{'artifact_witnesses':[witness]}], 'fiction-input'))
        # Construct a current owned job/attempt through the fixture's real
        # reservation path before testing publication's body-access boundary.
        from coordinator_runtime.contracts import digest
        self.f.selection['basis']['configuration'] = digest(self.s.config)
        self.s.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',
                          (encode(self.f.selection), 'fictional-current-capability'))
        _, attempt = self.f.job('Work', 'wi')
        self.no_body(lambda:publication.prepare(self.s, attempt,
                     {self.f.path:{'exists':True, 'sha256':self.f.sha}}))
        self.assertFalse((self.s.home/'artifacts'/'fiction-input').exists())
        # The older snapshot representation must carry the same stage target.
        self.s.db.execute("DELETE FROM artifact_custody WHERE attempt='fiction-prior'")
        self.s.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                          ('fiction-preimage', 'wi', 'fiction-grant', '{}',
                           encode({stage:{'exists':True, 'sha256':self.f.sha}}), 'prepared'))
        self.export_refuses()

    def test_transitive_stage_and_cycle_cannot_hide_current_log_or_exclusion(self):
        first, second = (str(self.f.area/name) for name in ('fiction-first', 'fiction-second'))
        self.record(first)
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)', ('fiction-a', second, first))
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)', ('fiction-cycle', first, second))
        # A harmless recorded cycle terminates and preserves legitimate bytes.
        self.assertEqual(base64.b64decode(self.f.export('fiction-owner')['body_base64']), self.f.body)
        for target in (str(self.f.area/'WORK_LOG.md'), str(self.f.area/'fiction-custom-log'),
                       str(self.f.area/'fiction-excluded'/'target')):
            with self.subTest(target=target):
                self.s.config['tasks']['wi']['routine_completion'] = {'bounded_log':{'target':str(self.f.area/'fiction-custom-log')}}
                self.s.config['artifact_exclusions'] = [str(self.f.area/'fiction-excluded')]
                self.s.db.execute('INSERT OR REPLACE INTO routine_stages VALUES(?,?,?)', ('fiction-b', target, second))
                self.export_refuses()

    def test_invalid_witness_is_not_custody_and_is_never_repaired(self):
        valid = {'sha256':self.f.sha, 'size':len(self.f.body)}
        invalid = ['{invalid-json', '[]', 'null', '{}',
                   encode({**valid, 'sha256':'0'*64}), encode({**valid, 'size':True}),
                   encode({**valid, 'size':-1}), encode({**valid, 'size':'24'}),
                   '{"sha256":"'+self.f.sha+'","size":1,"size":2}',
                   '{"sha256":"'+self.f.sha+'","size":NaN}']
        for witness in invalid:
            with self.subTest(witness=witness):
                self.s.db.execute('UPDATE artifact_custody SET witness=?', (witness,))
                self.export_refuses()
                self.no_body(lambda:custody.frozen_body(self.s, self.f.sha, path=self.f.path))
        self.s.db.execute('UPDATE artifact_custody SET witness=?', (encode(valid),))
        self.record(self.f.area/'fiction-corrupt-origin')
        self.s.db.execute("UPDATE artifact_custody SET witness='{invalid-json' WHERE attempt='fiction-prior'")
        self.export_refuses()

    def test_invalid_path_policy_hash_and_preimage_metadata_refuse_early(self):
        for path in ('relative-report', '/fixtures/../fiction-report', '/fixtures/fiction\x00report'):
            with self.subTest(path=path):
                self.s.db.execute('INSERT OR REPLACE INTO routine_stages VALUES(?,?,?)', ('fiction-bad', path, self.f.path))
                self.export_refuses()
        self.s.db.execute('DELETE FROM routine_stages')
        self.s.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                          ('fiction-corrupt', 'wi', 'fiction-grant', '{invalid-json', '{invalid-json', 'prepared'))
        self.export_refuses()
        self.s.db.execute("UPDATE routine_runs SET before_files='{}'")
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',
                          ('fiction-corrupt', str(self.f.area/'fiction-ordinary-target'), self.f.path))
        self.export_refuses()
        self.s.db.execute('DELETE FROM routine_stages')
        self.s.db.execute('DELETE FROM routine_runs')
        self.s.db.execute("UPDATE artifact_custody SET sha256='not-a-blob'")
        self.export_refuses()

    def test_lawful_bounded_entry_and_ordinary_source_preserve_attribution(self):
        stage = str(self.f.area/'fiction-bounded-entry')
        target = str(self.f.area/'WORK_LOG.md')
        self.record(stage)
        policy = {'kind':bounded_log.KIND, 'targets':[target, *[str(self.f.area/('fiction-peer-'+str(i))) for i in range(6)]],
                  'bounded_log':{'target':target, 'max_lines':12, 'max_bytes':8192, 'max_entry_bytes':16384}}
        for task in ({'role':'Reviews', 'phase':'integrator'}, {'role':'Work', 'phase':'proposer'}):
            with self.assertRaises(Refusal):
                bounded_log.validate(task, policy)
        self.s.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                          ('fiction-entry', 'wi', 'fiction-grant', encode(policy), '{}', 'prepared'))
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)', ('fiction-entry', target, stage))
        before = self.s.rows('SELECT * FROM artifact_custody')
        for caller in ('fiction-owner', 'fiction-consumer'):
            exported = self.f.export(caller)
            self.assertEqual(base64.b64decode(exported.pop('body_base64')), self.f.body)
            self.assertEqual(exported, before[0])
        self.assertEqual(self.s.rows('SELECT * FROM artifact_custody'), before)
        # Removing today's task must not invent a new historical role or erase
        # the lawful entry representation conserved by the original policy.
        del self.s.config['tasks']['wi']
        for caller in ('fiction-owner', 'fiction-consumer'):
            self.assertEqual(base64.b64decode(self.f.export(caller)['body_base64']), self.f.body)
        # Entry metadata cannot waive current exclusions or corrupt policy.
        self.s.config['artifact_exclusions'] = [target]
        self.export_refuses()
        self.s.config['artifact_exclusions'] = []
        bad = copy.deepcopy(policy); bad['bounded_log'].pop('max_lines')
        self.s.db.execute('UPDATE routine_runs SET policy=?', (encode(bad),))
        self.export_refuses()
        bad = copy.deepcopy(policy); bad['targets'] = 'abcdefg'
        self.s.db.execute('UPDATE routine_runs SET policy=?', (encode(bad),))
        self.export_refuses()

    def test_frozen_checks_all_current_tasks_and_preexisting_input_copy(self):
        self.s.config['tasks']['ri']['routine_completion'] = {'bounded_log':{'target':self.f.path}}
        root = self.s.home/'artifacts'/'fiction-existing'/'inputs'
        root.mkdir(parents=True)
        (root/self.f.sha).write_bytes(b'FICTION unrelated preexisting copy')
        witness = {'path':self.f.path, 'sha256':self.f.sha, 'custody':'artifact_blobs'}
        self.no_body(lambda:custody.frozen_body(self.s, self.f.sha, path=self.f.path))
        self.no_body(lambda:custody.materialize(self.s, [{'artifact_witnesses':[witness]}], 'fiction-existing'))
        self.assertEqual((root/self.f.sha).read_bytes(), b'FICTION unrelated preexisting copy')

    def test_utf8_binary_bounds_entitlement_and_witness_length(self):
        for body in ('FICTION Unicode: λ雪\n'.encode(), b'FICTION binary\x00\xff'):
            self.s.db.execute('DELETE FROM artifact_blobs')
            self.f.body = body; self.f.sha = hashlib.sha256(body).hexdigest()
            self.s.db.execute('INSERT INTO artifact_blobs VALUES(?,?)', (self.f.sha, body))
            self.s.db.execute('UPDATE artifact_custody SET sha256=?,witness=?',
                              (self.f.sha, encode({'sha256':self.f.sha, 'size':len(body)})))
            self.s.db.execute('UPDATE outboxes SET payload=?', (encode({'artifact_witnesses':[
                {'source_attempt':self.f.args.attempt, 'path':self.f.path, 'sha256':self.f.sha}]}),))
            self.s.config['limits']['max_artifact_bytes'] = len(body)
            for caller in ('fiction-owner', 'fiction-consumer'):
                self.assertEqual(base64.b64decode(self.f.export(caller)['body_base64']), body)
            self.no_body(lambda:self.f.export('fiction-unrelated'))
            self.s.config['limits']['max_artifact_bytes'] -= 1
            original_one = self.s.one
            def metadata_only(query, *args):
                self.assertNotIn('SELECT body', query)
                return original_one(query, *args)
            with patch.object(self.s, 'one', side_effect=metadata_only), \
                 patch.object(cli.hashlib, 'sha256', side_effect=AssertionError('oversize hash')), \
                 patch.object(cli.base64, 'b64encode', side_effect=AssertionError('oversize export')):
                with self.assertRaisesRegex(Refusal, 'export bound'): self.f.export('fiction-owner')
            self.s.config['limits']['max_artifact_bytes'] += 1
            self.s.db.execute('UPDATE artifact_custody SET witness=?',
                              (encode({'sha256':self.f.sha, 'size':len(body)+1}),))
            with patch.object(self.s, 'one', side_effect=metadata_only), \
                 patch.object(cli.hashlib, 'sha256', side_effect=AssertionError('mismatched size hashed')), \
                 patch.object(cli.base64, 'b64encode', side_effect=AssertionError('mismatched size exported')):
                with self.assertRaisesRegex(Refusal, 'body size'): self.f.export('fiction-owner')


class Isolation(unittest.TestCase):
    def test_positive_source_readonly_and_private_environment(self):
        self.assertEqual(str(Path.home()), '/fixtures/home')
        self.assertEqual(os.environ['XDG_CONFIG_HOME'], '/fixtures/config')
        self.assertEqual(os.environ['TMPDIR'], '/fixtures/tmp')
        self.assertFalse(Path('/home/nes').exists())
        self.assertFalse(Path('/src/.git').exists())
        with self.assertRaises(OSError):
            with open('/src/tools/coordinator-runtime/coordinator_runtime/custody.py', 'ab'):
                pass
        with self.assertRaises(OSError):
            os.open('/not-owned', os.O_CREAT | os.O_WRONLY, 0o600)
        Path('/fixtures/fiction-owned-write').write_bytes(b'FICTION isolated positive write')


if __name__ == '__main__':
    unittest.main()
