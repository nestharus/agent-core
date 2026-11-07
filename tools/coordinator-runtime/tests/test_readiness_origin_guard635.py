"""Owned synthetic reader invariants, not an admitted exploit/reachability proof.

No Board, provider, native session or child process. Real custody writers,
SQLite origin traversal, readiness, same-inode publisher and delivery callback
run here. The small journal/delegate supplies explicit fictional outer authority,
current-job/resource checks and lock; it proves no live authority or concurrency.
All files, SQLite and observations are retained under the required owned root.
"""
from contextlib import contextmanager, nullcontext
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from support import result
from coordinator_runtime import custody, publication, readiness, routine
from coordinator_runtime.cleanup import register_artifact
from coordinator_runtime.completion import Completion
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.store import SCHEMA


class Journal:
    """Synthetic outer authority; production SQL tables and artifact writers."""
    def __init__(self, area):
        self.home = area / 'state'
        self.home.mkdir(mode=0o700)
        self.controller = 'fictional-original-collector'
        self.config = {'actor': 'fictional-service', 'artifact_exclusions': [],
            'roles': {'Work': {'owner': 'fictional-owner'}},
            'limits': {'max_bytes': 4*1024*1024, 'max_artifact_bytes': 1024*1024}}
        self.task = {'role': 'Work', 'effects': 'owner-reconcile', 'network': False,
            'effect_authority': {'read_roots': [str(area)], 'write_roots': [str(area)],
                'operations': ['read-reports', 'write-role-records']},
            'routine_completion': {'kind': 'file-witness', 'targets': []}}
        self.config['tasks'] = {'owned': self.task}
        self.db = sqlite3.connect(self.home/'synthetic.sqlite3', isolation_level=None, cached_statements=0)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA + custody.SCHEMA + routine.SCHEMA + publication.SCHEMA +
            'CREATE TABLE local_commits(attempt TEXT,state TEXT);')
        self.events = []
        self.db.set_authorizer(self.authorize_sql)
        self.row = {'id': 'own-attempt', 'job': 'own-job', 'capture': 'complete',
            'controller': self.controller, 'session': 'fictional-producer', 'ended': 1,
            'collected': 2, 'exit': 0, 'error': None}
        self.jobrow = {'id': 'own-job', 'task': 'owned', 'role': 'Work', 'token': 'fictional-token',
            'active_attempt': self.row['id'], 'controller': self.controller, 'members': '[]',
            'effects': 'unknown', 'hold_reason': None, 'effect_receipt': None}
        root = self.home/'artifacts'/self.row['id']
        root.mkdir(parents=True, mode=0o700)
        self.path = root/'evidence.json'

    def authorize_sql(self, action, table, column, database, trigger):
        if action == sqlite3.SQLITE_READ:
            self.events.append(['read', table, column])
        return sqlite3.SQLITE_OK

    def one(self, sql, values=()):
        row = self.db.execute(sql, values).fetchone()
        return dict(row) if row else None

    def rows(self, sql, values=()):
        return [dict(row) for row in self.db.execute(sql, values)]

    @contextmanager
    def tx(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def budget(self, *args):
        pass  # Fixed tiny fixture; no live resource-admission claim.

    def attempt(self, attempt):
        assert attempt == self.row['id']
        return self.row

    def job(self, job, token=None):
        assert job == self.jobrow['id']
        assert token is None or token == self.jobrow['token']
        return self.jobrow

    def require_execution_open(self, job):
        assert job == self.jobrow['id']  # Fictional outer ownership seam.

    def authorize_launch(self, attempt):
        assert attempt == self.row['id']  # No actual launch.

    def clock(self):
        return 3

    def prepare_answer(self):
        unknown = 'Verify this owned fictional local duty.'
        prior = {'status': 'unresolved', 'owner': 'producer', 'duty': 'verify', 'reason': unknown}
        binding = {'id': 'verify-command', 'thread': self.row['session'], 'turn': 'owned-turn',
            'command_sha256': hashlib.sha256(b'fictional verification').hexdigest(),
            'command_bytes': len(b'fictional verification'), 'exit_code': 0, 'status': 'completed'}
        resolution = {**prior, 'status': 'resolved', 'prior_disposition': prior,
            'verification_items': [binding['id']], 'command_bindings': [binding],
            'causal_reason': 'Fictional command/evidence verifies this synthetic duty; no semantic oracle.'}
        manifest = {'version': 1, 'resolutions': [{'subject': {'kind': 'unknown', 'index': 0,
            'original_hash': digest(unknown), 'prior_disposition': prior},
            **{k: resolution[k] for k in ('verification_items', 'command_bindings', 'causal_reason')}}]}
        body = encode(manifest).encode()
        self.path.write_bytes(body)
        self.sha = hashlib.sha256(body).hexdigest()
        # Admitted source writer sequence for permitted evidence, not a forged witness.
        custody.capture(self, self.row['id'], str(self.path), self.task)
        ref = {'path': str(self.path), 'sha256': self.sha}
        resolution.update(evidence=[ref], causal_evidence={**ref, 'entry': 0})
        old = {**result('PARTIAL'), 'failures': [], 'unknowns': [unknown], 'artifacts': [ref],
            'completion': {'version': 1, 'local': 'blocked', 'failures': [],
                'unknowns': [{'index': 0, **prior}], 'tools': []}}
        answer = {**old, 'semantic': 'DONE', 'completion': {**old['completion'], 'local': 'ready',
            'unknowns': [{'index': 0, **resolution}]}}
        detail = {'tool_completion': {'complete': True, 'items': [{**binding,
            'type': 'commandExecution', 'completed_notification': True}]}, 'prior_turn_result': old}
        self.row.update(result=encode(answer), detail=encode(detail))
        self.original = copy.deepcopy(self.row)
        return body

    def origin(self, path, sha=None, witness=None):
        # Seeded metadata neighbor only: no claim that a live admitted job can reach it.
        sha = sha or self.sha
        witness = witness or {'sha256': sha, 'size': self.path.stat().st_size}
        self.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
            ('seeded-origin', str(path), 'role-owned', 'fictional-owner', encode(witness), sha))


class Delegate(Completion):
    """Fictional explicit delegate, no Board object or messaging transport."""
    def __init__(self, journal):
        self.runtime = journal
        self.config = journal.config
        self.role = 'Work'
        self.grant = {'id': 'fictional-grant', 'issued_by': 'fictional-owner', 'owner': 'fictional-owner',
            'authority': 'Synthetic delegate only'}
        self.store = self
        journal.db.executescript('''
            CREATE TABLE coordinator_deliveries_v1(id TEXT PRIMARY KEY,recipient TEXT,actor TEXT,owner TEXT,
                grant_id TEXT,payload TEXT,notice TEXT,transport_started INTEGER,pickup TEXT,processing TEXT,
                settlement TEXT,state TEXT,processed_at REAL);
            CREATE TABLE notification_outbox(notification_id TEXT PRIMARY KEY,route TEXT,delivery_state TEXT,
                acknowledged_at TEXT,state_changed_at TEXT);
        ''')
        journal.db.execute("""INSERT INTO coordinator_deliveries_v1 VALUES('delivery','fictional-owner',
            'fictional-service','fictional-owner','fictional-grant','payload','notice',0,NULL,NULL,NULL,'pending',NULL)""")
        journal.db.execute("INSERT INTO notification_outbox VALUES('notice','managed','pending',NULL,NULL)")

    def completion_authority(self, runtime, task):
        assert runtime is self.runtime and task == 'owned'
        return self.grant

    @contextmanager
    def opened(self):
        yield self.runtime.db

    def write(self, conn):
        assert conn is self.runtime.db
        return self.runtime.tx()

    def _grant(self, conn, runtime):
        return self.completion_authority(runtime, 'owned')

    def utc_now(self):
        return 'fictional-time'

    def _delivery_record(self, conn, row):
        return row


class OriginGuard635(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ['COORDINATOR_635_FIXTURES'])
        assert root.is_absolute() and root.is_dir() and not root.is_symlink()
        self.area = Path(tempfile.mkdtemp(prefix=self._testMethodName+'-', dir=root))
        self.s = Journal(self.area)
        self.addCleanup(self.s.db.close)
        self.addCleanup(self.save)
        self.body = self.s.prepare_answer()
        self.s.events.clear()

    def save(self):
        (self.area/'observations.json').write_text(encode({'test': self.id(), 'events': self.s.events,
            'qualification': 'synthetic reader invariant; outer authority seams; no live reachability claim'}))

    def acquire(self):
        real = custody.guard_frozen
        def guarded(*args, **kwargs):
            value = real(*args, **kwargs)
            self.s.events.append(['closure-permitted'])
            return value
        with patch.object(custody, 'guard_frozen', side_effect=guarded):
            return readiness.assess(self.s, self.s.row)

    def body_reads(self):
        # SQLite authorizer sees the body column for both length(body) and body.
        return [i for i, e in enumerate(self.s.events) if e == ['read', 'artifact_blobs', 'body']]

    def refused(self, message):
        self.s.events.clear()
        with self.assertRaisesRegex(Refusal, message):
            self.acquire()
        self.assertEqual(self.body_reads(), [], self.s.events)
        self.assertEqual(self.s.row, self.s.original)  # No unknown/failure/old evidence rewriting.

    def test_permitted_capture_registration_and_current_handback(self):
        local = self.acquire()
        self.assertEqual(local['original_unknowns'], json.loads(self.s.row['result'])['unknowns'])
        self.assertEqual(len(local['resolved_local_unknowns']), 1)
        self.assertTrue(self.s.one('SELECT path FROM artifacts WHERE path=?', (str(self.s.path),)))
        reads = self.body_reads()
        self.assertEqual(len(reads), 2)  # length, then body
        self.assertLess(self.s.events.index(['closure-permitted']), min(reads))

    def test_current_exclusion_of_own_path_precedes_length(self):
        self.s.config['artifact_exclusions'] = [str(self.s.path)]
        self.refused('excluded before acquisition')

    def test_recorded_hash_origin_policy_change_precedes_length(self):
        origin = self.area/'known-origin.json'
        self.s.origin(origin)
        self.acquire()  # Same-hash permitted origin is allowed.
        self.s.config['artifact_exclusions'] = [str(origin)]
        self.refused('excluded before acquisition')

    def test_current_bounded_log_policy_change_precedes_length(self):
        self.s.config['tasks']['new-policy'] = {'routine_completion': {'bounded_log': {'target': str(self.s.path)}}}
        self.refused('whole-log acquisition unavailable')

    def test_stage_target_closure_and_transitive_hash_precede_length(self):
        target = self.area/'seeded-target.json'
        held = self.area/'seeded-excluded-origin.json'
        other_hash = 'a'*64
        self.s.origin(held, other_hash, {'sha256': other_hash, 'size': 7})
        self.s.db.execute('INSERT INTO artifacts(path,attempt,dev,ino,size,mtime,sha256) VALUES(?,?,?,?,?,?,?)',
            (str(target), self.s.row['id'], 0, 0, 7, 0, other_hash))
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)', ('seeded-stage', str(target), str(self.s.path)))
        self.s.config['artifact_exclusions'] = [str(held)]
        self.refused('excluded before acquisition')

    def test_before_file_origin_precedes_length(self):
        origin = self.area/'seeded-before.json'
        self.s.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
            ('seeded-before', 'owned', 'fictional-grant', '{}', encode({str(origin): {'sha256': self.s.sha}}), 'prepared'))
        self.s.config['artifact_exclusions'] = [str(origin)]
        self.refused('excluded before acquisition')

    def test_malformed_origin_metadata_preserves_unknown(self):
        self.s.origin(self.area/'seeded-invalid.json', witness={'sha256': self.s.sha, 'size': 'unknown'})
        self.refused('exact hash and byte size')

    def test_unavailable_origin_metadata_preserves_unknown(self):
        self.s.db.execute('DROP TABLE routine_stages')
        self.refused('origin metadata unavailable or corrupt')

    def test_own_attempt_identity_and_expected_hash_precede_length(self):
        for mutation in ('foreign-path', 'foreign-attempt', 'wrong-hash'):
            with self.subTest(case=mutation):
                answer = json.loads(self.s.original['result'])
                ref = answer['completion']['unknowns'][0]['evidence'][0]
                if mutation == 'foreign-path':
                    ref['path'] = str(self.area/'foreign.json')
                elif mutation == 'foreign-attempt':
                    self.s.db.execute("UPDATE artifact_custody SET attempt='other-attempt'")
                else:
                    ref['sha256'] = 'b'*64
                self.s.row['result'] = encode(answer)
                self.s.events.clear()
                with self.assertRaises(Refusal):
                    self.acquire()
                self.assertEqual(self.body_reads(), [])
                self.s.db.execute('UPDATE artifact_custody SET attempt=?', (self.s.row['id'],))
        self.s.row = copy.deepcopy(self.s.original)

    def test_body_hash_corruption_is_refused_without_filesystem_fallback(self):
        self.s.db.execute('UPDATE artifact_blobs SET body=?', (b'x'*len(self.body),))
        with self.assertRaisesRegex(Refusal, 'evidence hash changed'):
            self.acquire()
        self.assertEqual(len(self.body_reads()), 2)
        self.assertEqual(self.s.row, self.s.original)

    def test_missing_blob_is_unmet_even_when_own_file_still_exists(self):
        self.s.db.execute('DELETE FROM artifact_blobs')
        with self.assertRaisesRegex(Refusal, 'bytes are not conserved'):
            self.acquire()
        self.assertEqual(self.s.path.read_bytes(), self.body)
        self.assertEqual(self.s.row, self.s.original)

    def test_original_failure_and_unknown_survive_current_refusal(self):
        answer = json.loads(self.s.row['result'])
        detail = json.loads(self.s.row['detail'])
        failure = {'error': 'Synthetic original failed verification remains a historical fact.'}
        answer['failures'] = [failure]
        detail['prior_turn_result']['failures'] = [failure]
        answer['completion']['failures'] = [{'index': 0, 'status': 'resolved',
            'evidence': [{'path': str(self.s.path), 'sha256': self.s.sha}],
            'verification_items': ['verify-command']}]
        self.s.row.update(result=encode(answer), detail=encode(detail))
        self.s.original = copy.deepcopy(self.s.row)
        local = self.acquire()
        self.assertEqual(local['original_failures'], [failure])
        self.assertEqual(local['original_unknowns'], answer['unknowns'])
        self.s.config['artifact_exclusions'] = [str(self.s.path)]
        self.refused('excluded before acquisition')

    def test_unsettled_tools_remain_unmet_before_evidence(self):
        detail = json.loads(self.s.row['detail'])
        detail['tool_completion']['complete'] = False
        self.s.row['detail'] = encode(detail)
        self.s.original = copy.deepcopy(self.s.row)
        self.refused('unsettled tool metadata')

    def test_export_bound_refuses_after_guard_and_length_before_body(self):
        self.s.config['limits']['max_artifact_bytes'] = 1
        with self.assertRaisesRegex(Refusal, 'source exceeds selected export bound'):
            self.acquire()
        self.assertEqual(len(self.body_reads()), 1)
        self.assertLess(self.s.events.index(['closure-permitted']), self.body_reads()[0])
        self.assertEqual(self.s.row, self.s.original)

    def test_fresh_registration_countercase_blocks_simple_trace(self):
        origin = self.area/'seeded-excluded-origin.json'
        self.s.origin(origin)
        self.s.config['artifact_exclusions'] = [str(origin)]
        fresh = self.s.path.parent/'fresh.json'
        fresh.write_bytes(self.body)
        self.s.events.clear()
        # capture reads the permitted fresh file, discovers the shared hash, then
        # real register_artifact rechecks closure and refuses inventory.
        with self.assertRaisesRegex(Refusal, 'excluded before acquisition'):
            custody.capture(self.s, self.s.row['id'], str(fresh), self.s.task)
        self.assertTrue(self.s.one('SELECT sha256 FROM artifact_custody WHERE path=?', (str(fresh),)))
        self.assertIsNone(self.s.one('SELECT path FROM artifacts WHERE path=?', (str(fresh),)))
        self.assertEqual(self.body_reads(), [])
        with self.assertRaisesRegex(Refusal, 'excluded before acquisition'):
            register_artifact(self.s, self.s.row['id'], fresh)

    def setup_consumers(self):
        target = self.area/'published.json'
        target.write_bytes(b'{"verified":false}')
        self.s.task['routine_completion']['targets'] = [str(target)]
        delegate = Delegate(self.s)
        before = routine.snapshot(self.s, [str(target)])
        run = {'attempt': self.s.row['id'], 'task': 'owned', 'grant_id': delegate.grant['id'],
            'policy': encode(self.s.task['routine_completion']), 'before_files': encode(before), 'state': 'prepared'}
        self.s.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
            (run['attempt'], run['task'], run['grant_id'], run['policy'], run['before_files'], run['state']))
        publication.prepare(self.s, self.s.row['id'], before)
        stage = Path(publication.stages(self.s, self.s.row['id'])[str(target)])
        stage.write_bytes(b'{"verified":true}')
        publication.conserve_stages(self.s, self.s.row['id'], self.s.task)
        return target, delegate

    def reconcile(self, delegate):
        # Explicit fictional outer current-job/resource/lock seams. Real local
        # readiness and publisher (including exact preimages/custody) stay active.
        with patch('coordinator_runtime.configuration.require_current_job'), \
             patch('coordinator_runtime.resource_scopes.blocked', return_value=False), \
             patch.object(publication, 'snapshot_lock', side_effect=lambda _: nullcontext()), \
             patch('coordinator_runtime.local_integration.rebase', side_effect=lambda s,j,a,r,t: (r,None)):
            return routine.reconcile(self.s, delegate, self.s.jobrow)

    def deliver(self, delegate):
        return delegate.complete_own_delivery(self.s, {'id': 'delivery', 'kind': 'result',
            'recipient': 'Work', 'job': self.s.jobrow['id'], 'payload': 'payload'})

    def test_permitted_publication_and_delivery_consumers(self):
        target, delegate = self.setup_consumers()
        self.assertTrue(self.reconcile(delegate))
        self.assertEqual(target.read_bytes(), b'{"verified":true}')
        publication_row = self.s.one('SELECT * FROM file_publications')
        self.assertEqual(publication_row['state'], 'published')
        run = self.s.one('SELECT * FROM routine_runs WHERE attempt=?', (self.s.row['id'],))
        self.s.jobrow.update(effects='reconciled', effect_receipt=run['receipt'])
        delivery = self.deliver(delegate)
        self.assertEqual(delivery['state'], 'settled')
        self.assertEqual(json.loads(delivery['settlement'])['local_readiness']['original_unknowns'],
            json.loads(self.s.original['result'])['unknowns'])
        # Later acquisition policy changes do not reuse previously ready status.
        self.s.config['artifact_exclusions'] = [str(self.s.path)]
        self.s.events.clear()
        self.assertIsNone(self.deliver(delegate))
        self.assertEqual(self.body_reads(), [])

    def test_refused_readiness_blocks_publication_and_delivery_before_body(self):
        target, delegate = self.setup_consumers()
        self.s.config['artifact_exclusions'] = [str(self.s.path)]
        self.s.events.clear()
        with self.assertRaisesRegex(Refusal, 'excluded before acquisition'):
            self.reconcile(delegate)
        self.assertEqual(self.body_reads(), [])
        self.assertEqual(target.read_bytes(), b'{"verified":false}')
        self.assertEqual(self.s.rows('SELECT * FROM file_publications'), [])
        self.s.jobrow['effects'] = 'reconciled'  # Seeded adverse neighbor, no authority/reachability claim.
        self.assertIsNone(self.deliver(delegate))
        self.assertEqual(self.body_reads(), [])
        self.assertEqual(self.s.one('SELECT state FROM coordinator_deliveries_v1')['state'], 'pending')
        self.assertEqual(self.s.row, self.s.original)


if __name__ == '__main__':
    unittest.main()
