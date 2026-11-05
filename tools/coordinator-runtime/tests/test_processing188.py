"""Fictional protocol/engine tests; native profile/session/turn fields are NULL.

Run only in the documented positive-mount kernel sandbox. No provider, real
Board membership, native owner, actual worker return or live cutover is simulated.
"""
from contextlib import contextmanager
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import processing
from coordinator_runtime.contracts import Refusal, LUNA, SOL, digest, encode
from coordinator_runtime.store import Store
from coordinator_runtime import store as store_module
from coordinator_runtime.dispatcher import Dispatcher
from test_retained168 import Runtime, ControlledBoard


class ProtocolRuntime(Runtime):
    def __init__(self, directory):
        super().__init__(directory)
        self.db.executescript(processing.SCHEMA + '''CREATE TABLE cursors(role,seq);
          INSERT INTO cursors VALUES('Work',0);''')
        self.config['tasks'] = {'work-proposer': {'role': 'Work', 'phase': 'proposer', 'effects': 'none'}}
        self.source = {'id': 'fictional-input', 'role': 'Work', 'recipient': 'fictional-logical-owner',
                       'kind': 'board', 'post': 1, 'body': 'fictional retained purpose', 'allowed_tasks': ['work-proposer']}
        self.db.execute('UPDATE events SET payload=?,hash=?', (encode(self.source), digest(self.source)))
        self.db.commit()

    @contextmanager
    def tx(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def budget(self, *args, **kwargs):
        pass  # Fixture storage budget; production capacity tests use Store below.

    def event(self, name):
        return json.loads(self.one('SELECT payload FROM events WHERE id=?', (name,))['payload'])


class TestBoard(processing.ProcessingBoard, ControlledBoard):
    def __init__(self, runtime, directory):
        ControlledBoard.__init__(self, runtime, directory)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.runtime = ProtocolRuntime(self.directory)
        self.board = TestBoard(self.runtime, self.directory)
        self.boards = {'Work': self.board}

    def tearDown(self):
        self.board.conn.close()
        self.runtime.db.close()  # All fixture files retained, including failures.

    def selection(self, **changes):
        value = {'basis': processing.basis(self.runtime, self.boards), 'authority': 'fictional selected software duty',
                 'expires': self.runtime.now + 60, 'retained_events': ['fictional-input'], 'recover_controls': {},
                 'future_intake': False, 'tasks': ['work-proposer'], 'max_starts': 3,
                 'max_shared_rows': 1000, 'max_shared_payload_bytes': 1048576, 'max_runtime_rows': 512}
        return {**value, **changes}

    def issue(self, **changes):
        key = processing.select(self.runtime, self.boards, self.selection(**changes))['capability']
        self.runtime.processing = processing.Access(self.runtime, key)
        return key

    def test_stopped_grant_usable_only_through_explicit_processing_adapter(self):
        self.issue()
        grant = self.board.verify_authority(self.runtime)
        self.assertIsNotNone(grant['revoked'])
        self.assertEqual(self.runtime.one('SELECT intake FROM enrollments')['intake'], 0)
        self.assertTrue(self.runtime.processing.event(self.runtime.source))
        self.assertFalse(self.runtime.processing.event({**self.runtime.source, 'id': 'fictional-other', 'post': 9}))

    def test_explicit_future_boundary_does_not_relabel_old_input(self):
        self.board.conn.execute('INSERT INTO posts(seq) VALUES(20)')
        self.issue(future_intake=True, retained_events=[])
        self.assertFalse(self.runtime.processing.event(self.runtime.source))
        self.assertFalse(self.runtime.processing.event({**self.runtime.source, 'id': 'fictional-gap', 'post': 20}))
        self.assertTrue(self.runtime.processing.event({**self.runtime.source, 'id': 'fictional-new', 'post': 21}))
        self.assertEqual(self.runtime.one('SELECT seq FROM cursors')['seq'], 0)

    def test_no_implicit_renewal_unrevocation_or_entitlement_expansion(self):
        key = self.issue()
        with self.assertRaises(Refusal):
            self.issue()
        self.runtime.now += 61
        with self.assertRaises(Refusal):
            self.board.verify_authority(self.runtime)
        processing.revoke(self.runtime, self.boards, key)
        self.runtime.now = 1000
        with self.assertRaises(Refusal):
            self.board.verify_authority(self.runtime)
        with self.assertRaises(Refusal):
            self.issue(max_runtime_rows=513)

    def test_wrong_issuer_and_changed_source_or_binding_refuse(self):
        policy = self.selection()
        self.board.store.actor = 'fictional-wrong-issuer'
        with self.assertRaises(Refusal):
            processing.select(self.runtime, self.boards, policy)
        self.board.store.actor = 'fictional-issuer'
        self.runtime.outbox('fictional-new-source')
        with self.assertRaises(Refusal):
            processing.select(self.runtime, self.boards, policy)
        self.issue()
        with self.assertRaises(Refusal):
            self.runtime.processing.event({**self.runtime.source, 'body': 'changed'})
        self.board.conn.execute('UPDATE coordinator_grants_v1 SET runtime_ino=runtime_ino+1')
        with self.assertRaises(Refusal):
            self.board.verify_authority(self.runtime)

    def test_shared_residency_and_logical_rows_are_distinct(self):
        self.issue(max_shared_rows=1000, max_runtime_rows=1)
        self.board.conn.execute("INSERT INTO coordinator_deliveries_v1(id,grant_id,payload) VALUES('fictional-foreign','fictional-foreign-grant','held')")
        self.board._delivery_capacity(self.board.conn, {'payload': 'new'})
        self.board.conn.execute("INSERT INTO coordinator_deliveries_v1(id,grant_id,payload) VALUES('fictional-own','fictional-grant','held')")
        with self.assertRaises(Refusal):
            self.board._delivery_capacity(self.board.conn, {'payload': 'new'})

    def test_recovery_release_requires_original_end_and_collected_attempts(self):
        key = self.issue()
        self.runtime.db.executescript('CREATE TABLE attempts(id,controller,collected);')
        self.runtime.db.execute("INSERT INTO processing_runs VALUES('fictional-controller',?,'owned',1000)", (key,))
        self.runtime.db.execute("INSERT INTO attempts VALUES('fictional-original','fictional-controller',NULL)")
        self.runtime.db.commit()
        receipt = {'actual_END': 7, 'evidence': ['fictional parent END observation; not a live worker']}
        with self.assertRaises(Refusal):
            processing.release(self.runtime, self.boards, key, 'fictional-controller', receipt)
        self.runtime.db.execute('UPDATE attempts SET collected=1001')
        self.runtime.db.commit()
        result = processing.release(self.runtime, self.boards, key, 'fictional-controller', receipt)
        self.assertFalse(result['processing_or_effects_complete'])
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM attempts')['n'], 1)

    def test_cli_has_concrete_parent_operations(self):
        from coordinator_runtime.cli import parser
        args = parser().parse_args(['processing-run', 'fictional-capability', '--seconds', '30', '--enable-models'])
        self.assertTrue(args.enable_models)
        self.assertEqual(args.capability, 'fictional-capability')


class FixturePool:
    def allocate(self):
        return {'profile': None, 'fixture': True}  # No synthetic account/native identity.


def engine_config(directory):
    def task(role, phase, **extra):
        return {'role': role, 'phase': phase, 'binding': SOL, 'profile': None,
                'effects': 'none', 'capacity': 5, **extra}
    tasks = {'wp': task('Work', 'proposer'), 'wi': task('Work', 'integrator'),
             'bi': task('Branch', 'integrator'), 'ri': task('Reviews', 'integrator', execution='owner'),
             'qe': task('QA', 'execution'), 'qc': task('QA', 'cleanup')}
    return {'state_dir': str(directory / 'state'), 'profiles': [None], 'tasks': tasks,
            'actor': 'fictional-software-actor', 'classifier': {'binding': LUNA, 'profile': None, 'cwd': '/fixtures'},
            'roles': {r: {'owner': 'fictional-logical-' + r, 'profile': None, 'legacy_hold': None} for r in ('Work', 'Branch', 'Reviews', 'QA')},
            'limits': {'max_events': 100, 'max_attempts': 100, 'max_jobs': 100, 'max_alerts': 100,
                       'max_result_bytes': 65536, 'max_files': 1000, 'max_bytes': 8388608},
            'deadlines': {'bind': 1, 'shutdown': 2}, 'delivery': {'recipients': {}}, 'classification_capacity': 5}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        # Production schema requires real enrolled profiles. This explicit SQL
        # projection permits NULL for protocol-only engine tests; it neither
        # changes production schema nor fabricates native enrollment identities.
        with patch.object(store_module, 'SCHEMA', store_module.SCHEMA.replace('profile TEXT NOT NULL', 'profile TEXT')):
            self.runtime = Store(engine_config(self.directory), controller='fictional-controller', clock=lambda: 1000.)
        self.runtime.execution_pool = FixturePool()
        self.events = []
        for role in self.runtime.config['roles']:
            self.runtime.db.execute('INSERT INTO enrollments VALUES(?,?,?,?,?,0,NULL,NULL)',
                                    (role, 'fictional-logical-' + role, None, 'fictional-grant-' + role, 0))
        self.key = self.authority()

    def tearDown(self):
        self.runtime.close()

    def authority(self, starts=100):
        sources = [{'id': e['id'], 'hash': digest(e)} for e in self.events]
        selection = {'basis': {'configuration': digest(self.runtime.config), 'implementation': processing.implementation(),
                               'roles': {r: {'original': {'events': sources}, 'future_after': 10} for r in self.runtime.config['roles']}},
                     'retained_events': [e['id'] for e in self.events], 'recover_controls': {}, 'future_intake': True,
                     'tasks': list(self.runtime.config['tasks']), 'expires': 1060., 'max_starts': starts}
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE revoked IS NULL')
        key = 'fictional-cap-' + str(len(self.events))
        self.runtime.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)', (key, encode(selection), 'fictional-issuer', 1000.))
        self.runtime.processing = processing.Access(self.runtime, key)
        return key

    def event(self, name, role, task, package=None, queued=True):
        event = {'id': name, 'role': role, 'recipient': 'fictional-logical-' + role, 'kind': 'board',
                 'post': 11, 'body': 'fictional specific purpose ' + name, 'allowed_tasks': [task], 'package': package}
        self.events.append(event)
        self.runtime.ingest(event)
        if queued:
            self.runtime.db.execute("UPDATE events SET state='queued',ack='done' WHERE id=?", (name,))
            phase = self.runtime.config['tasks'][task]['phase']
            self.runtime.db.execute("INSERT INTO queue VALUES(?,?,?,?,?,?,?,NULL)", (name, name, role, phase, task, package, 'queued'))
        return event

    def test_fresh_classifier_reserves_on_stopped_enrollment_without_rewriting_it(self):
        self.event('fictional-message', 'Work', 'wp', queued=False)
        attempt, event = self.runtime.claim_classification()
        self.assertEqual(json.loads(self.runtime.attempt(attempt)['binding']), LUNA)
        self.assertIsNone(self.runtime.attempt(attempt)['session'])
        self.assertIsNone(self.runtime.attempt(attempt)['profile'])
        self.assertEqual(self.runtime.one("SELECT intake FROM enrollments WHERE role='Work'")['intake'], 0)
        self.assertEqual(event['id'], 'fictional-message')

    def test_parallel_proposals_survive_effect_hold_but_integrator_remains_held(self):
        self.runtime.db.execute("UPDATE enrollments SET legacy_hold='fictional original effect uncertainty' WHERE role='Work'")
        self.event('fictional-held-integrator', 'Work', 'wi')
        self.event('fictional-proposal-a', 'Work', 'wp')
        self.event('fictional-proposal-b', 'Work', 'wp')
        first, second = self.runtime.reserve(), self.runtime.reserve()
        self.assertEqual((first['phase'], second['phase']), ('proposer', 'proposer'))
        self.assertIsNone(self.runtime.reserve())
        self.assertIsNotNone(self.runtime.one("SELECT legacy_hold FROM enrollments WHERE role='Work'")['legacy_hold'])

    def test_integrators_are_one_per_role_and_freeze_current_batch(self):
        self.event('fictional-work-a', 'Work', 'wi')
        self.event('fictional-work-b', 'Work', 'wi')
        first = self.runtime.reserve()
        self.event('fictional-work-later', 'Work', 'wi')
        self.event('fictional-branch', 'Branch', 'bi')
        second = self.runtime.reserve()
        self.assertEqual(len(json.loads(first['members'])), 2)
        self.assertEqual(second['role'], 'Branch')
        self.assertIsNone(self.runtime.reserve())

    def test_selected_opaque_reviews_is_dependency_not_fake_task_or_global_barrier(self):
        self.event('fictional-review', 'Reviews', 'ri')
        self.event('fictional-independent', 'Work', 'wp')
        job = self.runtime.reserve()
        self.assertEqual(job['role'], 'Work')
        self.assertEqual(self.runtime.one("SELECT state FROM queue WHERE event='fictional-review'")['state'], 'queued')

    def test_qa_has_five_separate_execution_packages_no_combined_batches(self):
        for n in range(6):
            package = 'fictional-package-' + str(n)
            self.runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)', (package, 'fictional-owner', encode({'package': package})))
            self.event('fictional-qa-' + str(n), 'QA', 'qe', package)
        jobs = [self.runtime.reserve() for _ in range(5)]
        self.assertTrue(all(len(json.loads(j['members'])) == 1 for j in jobs))
        self.assertEqual(len({j['package'] for j in jobs}), 5)
        self.assertIsNone(self.runtime.reserve())

    def test_control_exit0_without_actual_worker_never_resolves_or_processes(self):
        event = self.event('fictional-control', 'Work', 'wp', queued=False)
        with self.runtime.tx():
            attempt = self.runtime._attempt('input-control', event['id'], None, SOL, None)
            self.runtime.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',
                                    (event['id'], self.key, attempt, digest(event)))
        self.runtime.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created', 'result': {'semantic': 'DONE', 'summary': 'fictional return', 'decision_json': 'null'},
                                      'detail': {'tool_completion': {'complete': True}}})
        with self.assertRaises(Refusal):
            processing.apply_control(self.runtime, event['id'], attempt)
        self.assertIsNone(self.runtime.input_resolution(event['id']))
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events')['processed_at'])

    def test_delegated_control_keeps_one_responsibility_without_recursive_questions(self):
        event = self.event('fictional-owned-control', 'Work', 'wp', queued=False)
        self.runtime.queue_input_control(event, {'task': '@control', 'package': None})
        self.assertEqual(self.runtime.one('SELECT state FROM queue')['state'], 'awaiting-owner')
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM outboxes')['n'], 0)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events')['processed_at'])

    def test_qa_consolidation_waits_for_executions_then_uses_one_slot(self):
        package = 'fictional-qa-package'
        self.runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)', (package, 'fictional-owner', '{}'))
        self.event('fictional-execution', 'QA', 'qe', package)
        execution = self.runtime.reserve()
        self.event('fictional-consolidate-a', 'QA', 'qc', package)
        self.event('fictional-consolidate-b', 'QA', 'qc', package)
        self.assertIsNone(self.runtime.reserve())
        # A fictional engine transition, not a native worker/processing receipt.
        self.runtime.db.execute("UPDATE jobs SET state='closed' WHERE id=?", (execution['id'],))
        cleanup = self.runtime.reserve()
        self.assertEqual(cleanup['phase'], 'cleanup')
        self.assertIsNone(self.runtime.reserve())

    def test_start_budget_expiry_and_native_owner_path_are_not_silently_bypassed(self):
        self.event('fictional-start-a', 'Work', 'wp', queued=False)
        self.runtime.db.execute('UPDATE processing_capabilities SET starts=100')
        with self.assertRaises(Refusal):
            self.runtime.claim_classification()
        self.assertEqual(self.runtime.one("SELECT COUNT(*) AS n FROM attempts")['n'], 0)
        self.runtime.processing = None
        with self.assertRaises(Refusal):
            self.runtime.enrollment('Work')


if __name__ == '__main__':
    unittest.main(verbosity=2)
