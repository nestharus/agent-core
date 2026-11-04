"""Contained Decision31 boundaries; synthetic authority is not live acceptance.

Set COORDINATOR_COHERENT_FIXTURES to an owned absolute act witness directory.
No HOME, account or session identity substitution; all fixtures are retained.
"""
import asyncio
from contextlib import contextmanager, asynccontextmanager
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from support import config_at, enrolled, event, queued, collect, result
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.automatic_control import AutomaticControl, SCHEMA as CONTROL_SCHEMA
from coordinator_runtime.board_delivery import BoardDelivery, SCHEMA as DELIVERY_SCHEMA
from coordinator_runtime.completion import Completion
from coordinator_runtime.contracts import Refusal, digest, encode, ident, scoped_task
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.execution_pool import _module as public_pool
from coordinator_runtime.routine import BOARD_SCHEMA as COMPLETION_SCHEMA
from coordinator_runtime.software import Software, BOARD_SCHEMA as SOFTWARE_SCHEMA


class FixtureBoard(Software, Completion, BoardDelivery, AutomaticControl):
    """Real policy/callback methods on owned SQLite; no membership/auth claim."""
    def __init__(self, config, role, conn, grant):
        self.config, self.role, self.conn, self.grant = config, role, conn, grant
        self.selected, self.identity = config['roles'][role], 'synthetic-shared-board'
        self.store = SimpleNamespace(write=self.write, utc_now=lambda: 'synthetic-clock')

    @contextmanager
    def opened(self, **kwargs):
        yield self.conn

    @staticmethod
    @contextmanager
    def write(conn):
        conn.execute('BEGIN IMMEDIATE')
        try:
            yield
            conn.execute('COMMIT')
        except BaseException:
            conn.execute('ROLLBACK')
            raise

    def _grant(self, conn, runtime):
        if self.grant.get('revoked'):
            raise Refusal('synthetic grant revoked')
        return self.grant

    def verify_authority(self, runtime):
        return self._grant(self.conn, runtime)

    def _delivery_grant(self, conn, runtime, outbox):
        return self._grant(conn, runtime), self.config['roles'][outbox['recipient']]


class CoherentCutover(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        base = Path(os.environ['COORDINATOR_COHERENT_FIXTURES'])
        if not base.is_absolute() or base.is_symlink() or not base.is_dir():
            raise AssertionError('explicit owned absolute witness directory required')
        self.area = base / (self._testMethodName + '-' + ident())
        self.area.mkdir(mode=0o700)
        self.config = config_at(self.area)
        self.config['software_delegation'] = {
            'grantor': self.config['roles']['Work']['owner'],
            'authority': 'Synthetic Decision31 fixture; no real grant', 'boundary': 'new-journal-only'}
        task = self.config['tasks']['branch-integrator']
        task.update(require_package_scope=True, scope_roots=[str(self.area)],
                    software_handoffs={'QA': ['qa-execution']})
        self.runtime = enrolled(self.config)
        self.addCleanup(self.runtime.close)
        self.conn = sqlite3.connect(self.area / 'synthetic-board.sqlite3', isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        self.conn.executescript(SOFTWARE_SCHEMA + DELIVERY_SCHEMA + COMPLETION_SCHEMA + CONTROL_SCHEMA + '''
            CREATE TABLE notification_outbox(notification_id INTEGER PRIMARY KEY,route TEXT,
                delivery_state TEXT,acknowledged_at TEXT,state_changed_at TEXT,queue_message_id TEXT);
        ''')
        self.boards = {}
        for role, selected in self.config['roles'].items():
            grant = {'id': self.runtime.enrollment(role)['grant_id'], 'owner': selected['owner'],
                     'issued_by': self.config['software_delegation']['grantor'],
                     'authority': self.config['software_delegation']['authority']}
            board = FixtureBoard(self.config, role, self.conn, grant)
            self.conn.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?,?)',
                              (grant['id'], encode(board.software_policies()), digest(self.config)))
            policies = {n: t.get('routine_completion') for n, t in self.config['tasks'].items() if t['role'] == role}
            self.conn.execute('INSERT INTO coordinator_completion_grants_v1 VALUES(?,?,?)',
                              (grant['id'], encode(policies), grant['authority']))
            self.boards[role] = board
        self.dispatcher = Dispatcher(self.runtime, models=object(), boards=self.boards)
        self.pool = public_pool.Pool(self.config['execution_pool_routes'])
        self.process_ends = []

    async def asyncTearDown(self):
        (self.area / 'process-ends.json').write_text(encode(self.process_ends) + '\n')

    def admission(self, label='original'):
        return {'task_scopes': {'branch-integrator': {
            'procedure': label, 'resource_evidence': ['synthetic independent resource owner'],
            'cwd': str(self.area), 'read_roots': [str(self.area)], 'write_roots': [], 'network': False}}}

    def admit(self, label='original'):
        self.runtime.admit('package', self.config['roles']['Branch']['owner'], self.admission(label))
        return self.runtime.one('SELECT * FROM admissions WHERE package=?', ('package',))

    def job(self, *, bind=True):
        admission = self.admit()
        queued(self.runtime, event(self.config, ident(), role='Branch', task='branch-integrator', package='package'))
        job = self.runtime.reserve()
        attempt = self.runtime.start_job(job['id'], job['token'])
        job = self.runtime.job(job['id'])
        scoped_task(job['task'], self.config['tasks'][job['task']], admission)
        if bind:
            self.boards['Branch'].bind_software_attempt(self.runtime, job, attempt, admission)
        return job, attempt, admission

    def completed(self):
        job, attempt, _ = self.job()
        collect(self.runtime, attempt, {**result(), 'handoffs': [], 'no_handoff_reason': 'synthetic local witness'},
                tool_completion={'complete': True, 'items': [], 'nonzero_completions': []})
        self.runtime.db.execute("UPDATE jobs SET state='awaiting-delivery',effects='none' WHERE id=?", (job['id'],))
        return self.runtime.job(job['id']), attempt

    def delivery(self, job, recipient='Branch', state='pending', transport=0):
        key = ident()
        grant = self.boards['Branch'].grant
        outbox = {'id': key, 'job': job['id'], 'recipient': recipient, 'kind': 'result',
                  'producer': self.runtime.attempt(job['active_attempt'])['session'],
                  'payload': encode({'text': 'synthetic exact result', 'package': 'package'}),
                  'event': json.loads(job['members'])[0]['event']}
        notice = self.conn.execute('SELECT COUNT(*)+1 FROM notification_outbox').fetchone()[0]
        self.conn.execute('INSERT INTO notification_outbox VALUES(?,?,?,?,?,?)',
                          (notice, 'managed', state, None, None, None))
        self.conn.execute('''INSERT INTO coordinator_deliveries_v1
            (id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created,transport_started)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (key, grant['id'], grant['owner'], self.config['actor'], outbox['producer'],
             self.config['roles'][recipient]['owner'], 'result', 'settled', outbox['payload'],
             notice, notice, 'posted', 'synthetic-clock', transport))
        return outbox

    def board_state(self, outbox):
        return [dict(self.conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()),
                dict(self.conn.execute('SELECT * FROM notification_outbox WHERE notification_id=(SELECT notice FROM coordinator_deliveries_v1 WHERE id=?)',
                                       (outbox['id'],)).fetchone())]

    async def test_admission_replacement_between_scoping_and_binding_refuses(self):
        job, attempt, original = self.job(bind=False)
        self.admit('replacement')
        with self.assertRaisesRegex(Refusal, 'changed while scoping'):
            self.boards['Branch'].bind_software_attempt(self.runtime, job, attempt, original)
        self.assertNotIn('software_authority', json.loads(self.runtime.attempt(attempt)['detail']))

    async def test_exact_current_admission_then_changed_final_guard(self):
        job, attempt, _ = self.job()
        self.runtime.authorize_launch(attempt)
        self.admit('replacement')
        with self.assertRaisesRegex(Refusal, 'authority/admission differs'):
            self.runtime.authorize_launch(attempt)
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])
        with self.assertRaises(Refusal):
            self.boards['Branch']._software_job_grant(self.runtime, self.runtime.job(job['id']))

    async def test_dispatcher_binds_the_scope_passed_to_its_actual_model_boundary(self):
        job, attempt, admission = self.job(bind=False)
        seen = []
        async def observe(runtime, actual, prompt, spec, schema):
            self.assertEqual(actual, attempt)
            runtime.authorize_launch(actual)
            proof = json.loads(runtime.attempt(actual)['detail'])['software_authority']
            self.assertEqual(proof['admission_hash'], digest(admission))
            self.assertEqual(spec['effect_authority']['read_roots'], [str(self.area)])
            self.assertEqual(spec['cwd'], str(self.area))
            seen.append(actual)
            self.admit('changed-at-model-boundary')
            with self.assertRaises(Refusal): runtime.authorize_launch(actual)
            return {'exit': None, 'capture': 'not-started', 'cleanup': 'no-session-created',
                    'result': None, 'error': 'synthetic changed authority; no process created',
                    'detail': {'known_not_started': True}}
        self.dispatcher.models = SimpleNamespace(run=observe)
        with patch.object(self.dispatcher, 'try_finish'):
            await self.dispatcher.execute(job['id'], attempt)
        self.assertEqual(seen, [attempt])
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])

    async def test_successor_keeps_old_evidence_and_needs_its_own_current_binding(self):
        job, original, _ = self.job()
        collect(self.runtime, original, {**result('PARTIAL'), 'handoffs': [],
                'no_handoff_reason': 'synthetic remaining work'}, code=1)
        self.runtime.finish_job(job['id'], job['token'])
        self.runtime.reconcile_effects(job['id'], job['token'], self.config['roles']['Branch']['owner'],
                                      {'evidence': ['synthetic accounted effects'], 'unknown_effects': []})
        self.runtime.claim_recovery(job['id'])
        diagnosis = self.runtime.diagnosis_attempt(job['id'])
        choice = {'profile': '.codex3', 'remaining': 'same bounded remainder', 'rationale': 'preserve source and current admission'}
        collect(self.runtime, diagnosis, choice)
        originals = [self.runtime.attempt(a) for a in [original, diagnosis]]
        self.pool.set(['.codex5'])
        successor = self.runtime.handoff(job['id'], diagnosis)
        self.assertEqual(self.runtime.attempt(successor)['profile'], '.codex5')
        self.assertEqual(json.loads(self.runtime.attempt(successor)['detail'])['choice'], choice)
        with self.assertRaises(Refusal): self.runtime.authorize_launch(successor)
        admission = self.admit('current-successor')
        current = self.runtime.job(job['id'])
        scoped_task(current['task'], self.config['tasks'][current['task']], admission)
        self.boards['Branch'].bind_software_attempt(self.runtime, current, successor, admission)
        self.runtime.authorize_launch(successor)
        self.admit('changed-after-successor-binding')
        with self.assertRaises(Refusal): self.runtime.authorize_launch(successor)
        self.assertEqual([self.runtime.attempt(a) for a in [original, diagnosis]], originals)
        self.assertIsNone(self.runtime.attempt(successor)['begin'])

    async def test_missing_proof_checker_revocation_and_stale_attempt_refuse(self):
        job, attempt, admission = self.job(bind=False)
        with self.assertRaises(Refusal): self.runtime.authorize_launch(attempt)
        self.boards['Branch'].bind_software_attempt(self.runtime, job, attempt, admission)
        checker = self.runtime.task_launch_authorizer
        self.runtime.task_launch_authorizer = None
        with self.assertRaisesRegex(Refusal, 'checker'): self.runtime.authorize_launch(attempt)
        self.runtime.task_launch_authorizer = checker
        self.boards['Branch'].grant['revoked'] = True
        with self.assertRaisesRegex(Refusal, 'revoked'): self.runtime.authorize_launch(attempt)
        self.boards['Branch'].grant.pop('revoked')
        self.runtime.db.execute('UPDATE jobs SET active_attempt=NULL WHERE id=?', (job['id'],))
        with self.assertRaisesRegex(Refusal, 'current owned'): self.runtime.authorize_launch(attempt)

    async def change_cannot_spawn(self, during):
        _, attempt, _ = self.job()
        adapter = AppServer(self.config, [sys.executable, '-c', 'pass'])
        original_command = adapter.command
        async def command(*args):
            value = await original_command(*args)
            if during == 'preflight': self.admit('changed-preflight')
            return value
        adapter.command = command
        original_admission = self.runtime.execution_pool.admission
        calls = 0
        @asynccontextmanager
        async def delayed_admission(profile):
            nonlocal calls
            calls += 1
            if calls == 2 and during == 'pool-wait':
                await asyncio.sleep(0)
                self.admit('changed-while-waiting')
            async with original_admission(profile) as witness:
                yield witness
        with patch.object(self.runtime.execution_pool, 'admission', delayed_admission), patch(
                'coordinator_runtime.appserver.asyncio.create_subprocess_exec',
                side_effect=AssertionError('stale admission must not spawn')):
            outcome = await adapter.run(self.runtime, attempt, 'synthetic', {'cwd': str(self.area), 'sandbox': 'read-only'})
        self.assertTrue(outcome['detail']['known_not_started'], outcome)
        self.assertIn('authority/admission differs', outcome['error'])
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])
        self.runtime.collect(attempt, outcome)

    async def test_change_during_preflight_cannot_spawn(self):
        await self.change_cannot_spawn('preflight')

    async def test_change_during_pool_wait_cannot_spawn(self):
        await self.change_cannot_spawn('pool-wait')

    async def test_changed_admission_refuses_initial_turn_and_idle_continuation(self):
        _, attempt, _ = self.job()
        adapter = AppServer(self.config)
        start = AsyncMock(side_effect=AssertionError('stale authority must not start a turn'))
        adapter.start_turn = start
        self.admit('changed-before-turn')
        with self.assertRaises(Refusal):
            await adapter.turn(object(), self.runtime, attempt, ident(), 'synthetic', {}, {}, None, {'detail': {}})
        self.admit()
        thread = ident()
        async def read(method, params):
            self.assertEqual(method, 'thread/read')
            self.admit('changed-during-idle-read')
            return {'thread': {'id': thread, 'status': {'type': 'idle'}}}
        with self.assertRaises(Refusal):
            await adapter.continue_idle(SimpleNamespace(rpc=read), self.runtime, attempt, thread, ident(), {}, {}, None)
        start.assert_not_awaited()

    async def test_changed_during_initialize_cannot_create_thread(self):
        _, attempt, _ = self.job()
        profile = self.runtime.attempt(attempt)['profile']
        async def initialize(method, params):
            self.assertEqual(method, 'initialize')
            self.admit('changed-during-initialize')
            return {'codexHome': str(Path.home() / profile)}  # Value only; no profile operation.
        peer = SimpleNamespace(rpc=initialize, send=AsyncMock(), owned_storage=None)
        with self.assertRaises(Refusal):
            await AppServer(self.config).session(peer, self.runtime, attempt, 'synthetic', {}, {}, profile, None, {'detail': {}})

    async def test_current_authority_and_pool_admit_owned_python_process(self):
        _, attempt, _ = self.job()
        adapter = AppServer(self.config, [sys.executable, '-c', 'pass'])
        async def session(peer, *args):
            await peer.child.wait()
            return {'synthetic': 'process boundary only'}
        adapter.session = session
        with patch('coordinator_runtime.appserver.environment', return_value={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'}):
            outcome = await adapter.run(self.runtime, attempt, 'synthetic', {'cwd': str(self.area), 'sandbox': 'read-only'})
        self.process_ends.append({'kind': 'owned-python', 'END': outcome['exit']})
        self.assertEqual(outcome['exit'], 0, outcome)
        self.assertIsNotNone(self.runtime.attempt(attempt)['begin'])
        self.assertEqual(json.loads(self.runtime.attempt(attempt)['detail'])['execution_pool_admission']['profile'],
                         self.runtime.attempt(attempt)['profile'])

    async def test_own_callback_preserves_ambiguous_sending_and_started_custody(self):
        job, _ = self.completed()
        for state, started in [('ambiguous', 0), ('sending', 0), ('pending', 1), ('acknowledged', 1), ('ambiguous', 1)]:
            with self.subTest(state=state, started=started):
                outbox = self.delivery(job, state=state, transport=started)
                before = self.board_state(outbox)
                with self.assertRaisesRegex(Refusal, 'unsettled send'):
                    self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
                self.assertEqual(self.board_state(outbox), before)

    async def test_clean_own_callback_settles_but_existing_native_requirement_masks_processing(self):
        job, _ = self.completed()
        outbox = self.delivery(job)
        self.conn.execute('INSERT INTO coordinator_control_requirements_v1 VALUES(?,?)', (outbox['id'], 1))
        self.assertTrue(self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards))
        record = self.boards['Branch']._delivery_record(self.conn, self.board_state(outbox)[0])
        self.assertEqual(record['state'], 'settled')
        self.assertIsNotNone(record['substantive_processed_at'])
        self.assertIsNone(record['processed_at'])
        self.assertTrue(record['control_receipt']['pending'])

    async def test_cross_role_final_recheck_preserves_transport_started_after_intake(self):
        job, _ = self.completed()
        outbox = self.delivery(job, recipient='QA')
        self.assertTrue(self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards))
        intent = self.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (outbox['id'],)).fetchone()
        queued(self.runtime, json.loads(intent['payload']))
        ingest = self.runtime.ingest
        def changed_intake(message):
            value = ingest(message)
            self.conn.execute('UPDATE coordinator_deliveries_v1 SET transport_started=1 WHERE id=?', (outbox['id'],))
            return value
        with patch.object(self.runtime, 'ingest', changed_intake):
            with self.assertRaisesRegex(Refusal, 'attempted foreign send'):
                self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        row, notice = self.board_state(outbox)
        self.assertEqual(row['transport_started'], 1)
        self.assertIsNone(row['processing'])
        self.assertIsNone(row['settlement'])
        self.assertEqual(notice['delivery_state'], 'pending')

    async def test_pool_and_delegated_receiver_wait_for_exact_collected_consumption(self):
        job, source_attempt = self.completed()
        outbox = self.delivery(job, recipient='QA')
        self.assertTrue(self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards))
        intent = self.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (outbox['id'],)).fetchone()
        message = json.loads(intent['payload'])
        self.assertIsNone(self.board_state(outbox)[0]['processed_at'])
        queued(self.runtime, message)
        self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        self.assertIsNone(self.board_state(outbox)[0]['settlement'])
        self.pool.set(['.codex5'])
        consumer = self.runtime.reserve()
        self.assertEqual(consumer['role'], 'QA')
        attempt = self.runtime.start_job(consumer['id'], consumer['token'])
        consumer = self.runtime.job(consumer['id'])
        admission = self.runtime.one('SELECT * FROM admissions WHERE package=?', ('package',))
        self.boards['QA'].bind_software_attempt(self.runtime, consumer, attempt, admission)
        self.runtime.authorize_launch(attempt)
        self.assertEqual(self.runtime.attempt(attempt)['profile'], '.codex5')
        self.assertIsNone(self.board_state(outbox)[0]['settlement'])
        collect(self.runtime, attempt, {**result(), 'handoffs': [], 'no_handoff_reason': 'synthetic receiver'},
                tool_completion={'complete': True, 'items': [], 'nonzero_completions': []})
        self.runtime.db.execute("UPDATE jobs SET state='awaiting-delivery',effects='none' WHERE id=?", (consumer['id'],))
        self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        proof = json.loads(self.board_state(outbox)[0]['settlement'])
        self.assertEqual(proof['consumer_job'], consumer['id'])
        self.assertEqual(proof['processing']['attempt'], attempt)
        self.assertEqual(proof['processing']['collector'], self.runtime.controller)
        self.assertNotEqual(attempt, source_attempt)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?', (message['id'],))['processed_at'])

    def oversized_counter(self, digits=5000):
        counter = self.pool.read()[2]
        counter.parent.mkdir(exist_ok=True)
        counter.write_text('9' * digits + '\n')
        return counter, counter.read_bytes()

    async def test_oversized_counter_refuses_preview_status_allocate_admission_and_set(self):
        counter, before = self.oversized_counter()
        routes = Path(self.config['execution_pool_routes']).read_bytes()
        for operation in [self.pool.preview, self.pool.status, self.pool.allocate, lambda: self.pool.set(['.codex5'])]:
            with self.assertRaisesRegex(public_pool.PoolError, 'supported integer conversion'): operation()
            self.assertEqual(counter.read_bytes(), before)
            self.assertEqual(Path(self.config['execution_pool_routes']).read_bytes(), routes)
        with self.assertRaises(public_pool.PoolError):
            with self.pool.admission('.codex2'): self.fail('malformed counter must not admit')
        self.assertEqual(self.runtime.execution_pool.status()['state'], 'held')
        self.runtime.ingest(event(self.config))
        with self.assertRaises(Refusal): self.runtime.claim_classification()
        self.assertEqual(self.runtime.rows('SELECT * FROM attempts'), [])

    async def test_counter_increment_conversion_refuses_before_writing(self):
        counter, before = self.oversized_counter(sys.get_int_max_str_digits())
        self.pool.preview()  # The current value fits; its successor does not.
        with self.assertRaisesRegex(public_pool.PoolError, 'next rotation counter'): self.pool.allocate()
        self.assertEqual(counter.read_bytes(), before)

    def process(self, argv):
        completed = subprocess.run(argv, cwd=self.area, capture_output=True, text=True,
                                   env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.process_ends.append({'argv': list(map(str, argv)), 'END': completed.returncode,
                                  'stdout': completed.stdout, 'stderr': completed.stderr})
        return completed

    async def test_public_oversized_status_exec_and_parent_preview_are_clear_refusals(self):
        counter, before = self.oversized_counter()
        tool = Path(public_pool.__file__)
        base = [sys.executable, '-X', 'int_max_str_digits=4300', str(tool), '--routes', self.config['execution_pool_routes']]
        status = self.process(base + ['status'])
        self.assertEqual(status.returncode, 2, status.stderr)
        self.assertEqual(json.loads(status.stdout)['state'], 'held')
        self.assertNotIn('Traceback', status.stderr)
        marker, receipt = self.area/'must-not-exist', self.area/'admission.json'
        execute = self.process(base + ['exec', '--profile', '.codex2', '--receipt', str(receipt), '--',
                                      sys.executable, '-c',
                                      'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("unexpected")', str(marker)])
        self.assertEqual(execute.returncode, 2)
        self.assertEqual(json.loads(receipt.read_text())['state'], 'not-started')
        self.assertFalse(marker.exists())
        # Full public parent dry-run with explicit owned controls, no helper/model.
        routes = (tool.parent/'routes.toml').read_text()
        import re
        routes = re.sub(r'(?m)^state_dir\s*=.*$', 'state_dir = '+json.dumps(str(counter.parent)), routes)
        parent_routes = self.area/'parent-routes.toml'
        parent_routes.write_text(routes)
        parent = self.process([sys.executable, '-X', 'int_max_str_digits=4300', str(tool.parent/'dispatch.py'),
            '--dry-run', '--cwd', str(self.area), '--prompt', str(self.area/'fixture-template.md'),
            '--runs-dir', str(self.area/'uncreated-runs'), '--id', 'oversized-counter', '--config', str(parent_routes)])
        self.assertEqual(parent.returncode, 2, parent.stdout + parent.stderr)
        self.assertIn('supported integer conversion', parent.stderr)
        self.assertNotIn('Traceback', parent.stderr)
        self.assertFalse((self.area/'uncreated-runs').exists())
        self.assertEqual(counter.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
