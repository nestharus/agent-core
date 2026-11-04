"""Decision47 boundaries on retained owned files and fictional protocol records.

COORDINATOR_COHERENT_FIXTURES and COORDINATOR_REMAINDER_FIXTURES name owned
directories. No provider, account environment, live board or identity changes.
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from support import config_at, enrolled, event, queued, collect, result
from test_coherent_cutover import FixtureBoard
from test_publication_remainder import PublicationRemainder
from coordinator_runtime import prospective, publication, qa_source, routine
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.board import Board
from coordinator_runtime.board_delivery import SCHEMA as DELIVERY_SCHEMA
from coordinator_runtime.software import BOARD_SCHEMA as SOFTWARE_SCHEMA
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import Dispatcher


class ContinuingBoundaries(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        base = Path(os.environ['COORDINATOR_COHERENT_FIXTURES'])
        if not base.is_absolute() or not base.is_dir() or base.is_symlink():
            raise AssertionError('explicit owned retained fixture root required')
        self.area = base / (self._testMethodName + '-' + ident())
        self.area.mkdir(mode=0o700)
        self.config = config_at(self.area)
        task = self.config['tasks']['branch-integrator']
        task.update(require_package_scope=True, scope_roots=[str(self.area)], allowed_handoffs=['QA'])
        self.runtime = enrolled(self.config)
        self.addCleanup(self.runtime.close)
        self.conn = sqlite3.connect(self.area / 'fictional-board.sqlite3', isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        self.conn.executescript(SOFTWARE_SCHEMA + DELIVERY_SCHEMA + '''
            CREATE TABLE posts(seq INTEGER PRIMARY KEY,recipient TEXT,author TEXT,body TEXT,ref TEXT);
            CREATE TABLE thread_posts(post_seq INTEGER,thread_id INTEGER);
            CREATE TABLE notification_outbox(notification_id INTEGER PRIMARY KEY,post_seq INTEGER,
                recipient TEXT,route TEXT,delivery_state TEXT,acknowledged_at TEXT,
                state_changed_at TEXT,queue_message_id TEXT);
        ''')
        self.boards = {}
        for role, selected in self.config['roles'].items():
            grant = {'id': self.runtime.enrollment(role)['grant_id'], 'owner': selected['owner'],
                     'board_id': selected['board_id'], 'cutover': 0,
                     'issued_by': selected['owner'], 'authority': 'fictional native role grant'}
            board = FixtureBoard(self.config, role, self.conn, grant)
            board.scan = MethodType(Board.scan, board)
            board._event = MethodType(Board._event, board)
            # Visibility is an explicit fixture seam; selection/scan SQL is real.
            board.store.query_posts = self.visible
            self.boards[role] = board
        self.dispatcher = Dispatcher(self.runtime, models=object(), boards=self.boards)
        self.runtime.db.set_trace_callback(self.trace)
        self.trace_file = self.area / 'sql-trace.jsonl'

    def trace(self, statement):
        with self.trace_file.open('a') as stream:
            stream.write(json.dumps(statement) + '\n')

    def visible(self, conn, *, session, after, **kwargs):
        return [dict(row) for row in conn.execute(
            'SELECT * FROM posts WHERE seq>? AND recipient=? ORDER BY seq LIMIT 1', (after, session))]

    def select(self):
        tasks = {'branch-integrator': {'QA': ['qa-execution']}, 'qa-execution': {}}
        return prospective.select(self.runtime, self.config['roles']['Work']['owner'], {
            'configuration': digest(self.config), 'authority': 'fictional explicit prospective mandate',
            'expires': self.runtime.clock() + 600,
            'grants': {r: self.runtime.enrollment(r)['grant_id'] for r in ['Branch', 'QA']},
            'tasks': {name: {'task_hash': digest(self.config['tasks'][name]),
                            'software_handoffs': routes, 'ordinary_effects': False}
                      for name, routes in tasks.items()}})

    def admit(self, procedure='original'):
        self.runtime.admit('package', self.config['roles']['Branch']['owner'], {
            'task_scopes': {'branch-integrator': {'procedure': procedure,
                'resource_evidence': ['fictional independent resource owner'],
                'cwd': str(self.area), 'read_roots': [str(self.area)], 'write_roots': [], 'network': False}}})
        return self.runtime.one('SELECT * FROM admissions WHERE package=?', ('package',))

    def job(self, bind=True):
        admission = self.admit()
        queued(self.runtime, event(self.config, ident(), role='Branch', task='branch-integrator', package='package'))
        job = self.runtime.reserve()
        attempt = self.runtime.start_job(job['id'], job['token'])
        job = self.runtime.job(job['id'])
        if bind:
            self.boards['Branch'].bind_software_attempt(self.runtime, job, attempt, admission)
        return job, attempt

    def handoff(self):
        self.select()
        job, attempt = self.job()
        collect(self.runtime, attempt, result(), tool_completion={'complete': True, 'items': []})
        self.runtime.db.execute("UPDATE jobs SET state='awaiting-delivery',effects='none' WHERE id=?", (job['id'],))
        key = self.runtime._outbox('Branch', 'QA', 'work', {'package': 'package', 'text': 'one bounded QA duty'},
            job=job['id'], event=json.loads(job['members'])[0]['event'],
            producer=self.runtime.attempt(attempt)['session'])
        outbox = self.runtime.one('SELECT * FROM outboxes WHERE id=?', (key,))
        owner = self.config['roles']['QA']['owner']
        self.conn.execute('INSERT INTO posts VALUES(7,?,?,?,?)', (owner, outbox['producer'], 'handoff', 'package'))
        self.conn.execute('INSERT INTO posts VALUES(8,?,?,?,?)', (owner, ident(), 'later addressed input', 'package'))
        self.conn.execute("INSERT INTO notification_outbox VALUES(1,7,?,'managed','pending',NULL,NULL,NULL)", (owner,))
        self.conn.execute('''INSERT INTO coordinator_deliveries_v1
            (id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created,transport_started)
            VALUES(?,?,?,?,?,?,'work','settled',?,7,1,'posted','fictional-clock',0)''',
            (key, self.boards['Branch'].grant['id'], self.config['roles']['Branch']['owner'],
             self.config['actor'], outbox['producer'], owner, outbox['payload']))
        return outbox

    async def scanner_and_direct(self, direct_first):
        outbox = self.handoff()
        original = self.runtime.one('SELECT * FROM outboxes WHERE id=?', (outbox['id'],))
        board = self.boards['QA']
        item = board.scan(self.runtime)[0]
        self.assertNotIn('post', item)  # Original response bytes/identity stay intact.
        self.assertEqual(item['source_delivery']['post'], 7)
        if direct_first:
            self.assertTrue(self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards))
            queued(self.runtime, item)
        self.dispatcher.intake_role('QA', board)
        self.assertNotIn('QA', self.dispatcher.runtime_errors)
        self.assertEqual(self.runtime.one("SELECT seq FROM cursors WHERE role='QA'")['seq'], 8)
        if not direct_first:
            queued(self.runtime, item)
            self.assertTrue(self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards))
        self.assertEqual(self.runtime.event(item['id']), item)
        for _ in range(2):
            self.dispatcher.intake_role('QA', board)
            self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM queue WHERE event=?', (item['id'],))['n'], 1)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events WHERE id=?', (item['id'],))['n'], 1)
        self.assertEqual(original, self.runtime.one('SELECT * FROM outboxes WHERE id=?', (outbox['id'],)))
        delivery = dict(self.conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone())
        self.assertIsNone(delivery['processing'])
        self.assertIsNone(delivery['settlement'])
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?', (item['id'],))['processed_at'])
        self.assertIsNone(self.runtime.one('SELECT begin FROM attempts WHERE job IN (SELECT id FROM jobs WHERE role=?)', ('QA',)))
        later = self.runtime.one("SELECT payload FROM events WHERE role='QA' AND id!=?", (item['id'],))
        self.assertEqual(json.loads(later['payload'])['post'], 8)

    async def test_real_scanner_then_direct_preserves_one_duty_and_advances(self):
        await self.scanner_and_direct(False)

    async def test_direct_then_real_scanner_preserves_one_duty_and_advances(self):
        await self.scanner_and_direct(True)

    async def test_changed_delivery_is_refused_without_skipping_cursor_or_source(self):
        outbox = self.handoff()
        before = self.runtime.one('SELECT * FROM outboxes WHERE id=?', (outbox['id'],))
        self.conn.execute('UPDATE coordinator_deliveries_v1 SET payload=? WHERE id=?',
                          (encode({'package': 'package', 'text': 'changed source'}), outbox['id']))
        self.dispatcher.intake_role('QA', self.boards['QA'])
        self.assertIn('exact source delivery', self.dispatcher.runtime_errors['QA'])
        self.assertEqual(self.runtime.one("SELECT seq FROM cursors WHERE role='QA'")['seq'], 0)
        self.assertEqual(self.runtime.rows("SELECT * FROM events WHERE role='QA'"), [])
        self.assertEqual(before, self.runtime.one('SELECT * FROM outboxes WHERE id=?', (outbox['id'],)))

    async def test_scanned_handoff_has_one_finishable_consumer_with_original_accounting(self):
        outbox = self.handoff()
        source = self.runtime.job(outbox['job'])
        old_attempt = self.runtime.attempt(source['active_attempt'])
        old_members = source['members']
        self.dispatcher.intake_role('QA', self.boards['QA'])
        self.assertNotIn('QA', self.dispatcher.runtime_errors)
        self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        intent = self.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (outbox['id'],)).fetchone()
        item = json.loads(intent['payload'])
        queued(self.runtime, item)
        consumer = self.runtime.reserve()
        self.assertEqual(consumer['role'], 'QA')
        attempt = self.runtime.start_job(consumer['id'], consumer['token'])
        consumer = self.runtime.job(consumer['id'])
        self.boards['QA'].bind_software_attempt(self.runtime, consumer, attempt,
            self.runtime.one('SELECT * FROM admissions WHERE package=?', ('package',)))
        self.runtime.authorize_launch(attempt)
        delivery = lambda: dict(self.conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone())
        self.assertIsNone(delivery()['settlement'])
        collect(self.runtime, attempt, {**result(), 'handoffs': [], 'no_handoff_reason': 'fictional collected consumer'},
                tool_completion={'complete': True, 'items': []})
        self.runtime.db.execute("UPDATE jobs SET state='awaiting-delivery',effects='none' WHERE id=?", (consumer['id'],))
        self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        proof = json.loads(delivery()['settlement'])
        self.assertEqual(proof['consumer_job'], consumer['id'])
        self.assertEqual(proof['processing']['attempt'], attempt)
        self.assertEqual(proof['processing']['collector'], self.runtime.controller)
        for _ in range(2):
            self.dispatcher.intake_role('QA', self.boards['QA'])
            self.boards['Branch'].software_delivery(self.runtime, outbox, self.boards)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM jobs WHERE role=?', ('QA',))['n'], 1)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM attempts WHERE job=?', (consumer['id'],))['n'], 1)
        self.assertEqual(self.runtime.attempt(source['active_attempt']), old_attempt)
        self.assertEqual(self.runtime.job(source['id'])['members'], old_members)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?', (item['id'],))['processed_at'])
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM outboxes WHERE id=?', (outbox['id'],))['processed_at'])

    async def test_legacy_before_boundary_and_unrelated_task_keep_native_launch_path(self):
        old, attempt = self.job(bind=False)
        old_rows = self.runtime.rows('SELECT * FROM attempts')
        self.select()
        self.runtime.task_launch_authorizer = None
        self.runtime.authorize_launch(attempt)
        self.assertFalse(prospective.requires_authority(self.runtime, old))
        queued(self.runtime, event(self.config, ident(), role='Reviews', task='reviews-integrator'))
        other = self.runtime.reserve()
        other_attempt = self.runtime.start_job(other['id'], other['token'])
        self.runtime.authorize_launch(other_attempt)
        self.assertEqual([self.runtime.attempt(r['id']) for r in old_rows], old_rows)

    async def test_admission_change_and_epoch_revocation_refuse_final_launch(self):
        epoch = self.select()
        job, attempt = self.job()
        self.runtime.authorize_launch(attempt)
        original = self.runtime.attempt(attempt)
        self.admit('replaced')
        with self.assertRaisesRegex(Refusal, 'authority/admission differs'):
            self.runtime.authorize_launch(attempt)
        self.admit()
        self.runtime.authorize_launch(attempt)
        prospective.revoke(self.runtime, self.config['roles']['Work']['owner'], epoch['id'])
        # Revocation with no active epoch reports absent prospective authority.
        # Require the exact direct-checker refusal at the final guard as well.
        with self.assertRaises(Refusal) as direct:
            self.boards['Branch']._software_job_grant(self.runtime, self.runtime.job(job['id']))
        with self.assertRaises(Refusal) as final:
            self.runtime.authorize_launch(attempt)
        self.assertEqual(str(final.exception), str(direct.exception))
        self.assertEqual(self.runtime.attempt(attempt), original)

    async def test_expired_epoch_and_stale_attempt_fail_closed(self):
        self.select()
        job, attempt = self.job()
        self.runtime.authorize_launch(attempt)
        clock = self.runtime.clock
        self.runtime.clock = lambda: clock() + 601
        with self.assertRaisesRegex(Refusal, 'expired'):
            self.runtime.authorize_launch(attempt)
        self.runtime.clock = clock
        self.runtime.db.execute('UPDATE jobs SET active_attempt=NULL WHERE id=?', (job['id'],))
        with self.assertRaisesRegex(Refusal, 'current owned'):
            self.runtime.authorize_launch(attempt)
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])

    async def test_missing_proof_checker_and_revoked_unbound_duty_fail_closed(self):
        epoch = self.select()
        job, attempt = self.job(bind=False)
        with self.assertRaises(Refusal): self.runtime.authorize_launch(attempt)
        prospective.revoke(self.runtime, self.config['roles']['Work']['owner'], epoch['id'])
        self.assertTrue(prospective.requires_authority(self.runtime, job))
        with self.assertRaises(Refusal): self.runtime.authorize_launch(attempt)
        self.runtime.task_launch_authorizer = None
        with self.assertRaisesRegex(Refusal, 'checker'): self.runtime.authorize_launch(attempt)
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])

    async def test_pool_wait_change_refuses_before_process_or_environment_acquisition(self):
        self.select()
        _, attempt = self.job()
        adapter = AppServer(self.config)
        adapter.command = AsyncMock(return_value=(['/usr/bin/false'], {'fixture': True}))
        original = self.runtime.execution_pool.admission
        calls = 0
        @asynccontextmanager
        async def wait(profile):
            nonlocal calls
            calls += 1
            if calls == 2:
                await asyncio.sleep(0)
                self.admit('changed-during-owned-pool-wait')
            async with original(profile) as witness:
                yield witness
        with patch.object(self.runtime.execution_pool, 'admission', wait), patch(
                'coordinator_runtime.appserver.environment', side_effect=AssertionError('no account environment')), patch(
                'coordinator_runtime.appserver.asyncio.create_subprocess_exec', side_effect=AssertionError('no process')):
            outcome = await adapter.run(self.runtime, attempt, 'fixture', {'cwd': str(self.area), 'sandbox': 'read-only'})
        self.assertEqual(calls, 2)
        self.assertTrue(outcome['detail']['known_not_started'], outcome)
        self.assertIn('authority/admission differs', outcome['error'])
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])
        (self.area / 'refused-process-outcome.json').write_text(encode(outcome))

    async def test_thread_turn_and_continuation_recheck_current_authority(self):
        self.select()
        _, attempt = self.job()
        adapter = AppServer(self.config)
        profile = self.runtime.attempt(attempt)['profile']
        async def initialize(method, params):
            self.assertEqual(method, 'initialize')
            self.admit('changed-during-initialize')
            # Protocol field only; never an environment assignment or profile access.
            return {'codexHome': str(Path.home() / profile)}
        peer = SimpleNamespace(rpc=initialize, send=AsyncMock(), owned_storage=None)
        with self.assertRaises(Refusal):
            await adapter.session(peer, self.runtime, attempt, 'fixture', {}, {}, profile, None, {'detail': {}})
        adapter.start_turn = AsyncMock(side_effect=AssertionError('no turn'))
        with self.assertRaises(Refusal):
            await adapter.turn(object(), self.runtime, attempt, ident(), 'fixture', {}, {}, None, {'detail': {}})
        self.admit()
        thread = ident()
        async def read(method, params):
            self.assertEqual(method, 'thread/read')
            self.admit('changed-during-idle-read')
            return {'thread': {'id': thread, 'status': {'type': 'idle'}}}
        with self.assertRaises(Refusal):
            await adapter.continue_idle(SimpleNamespace(rpc=read), self.runtime, attempt, thread, ident(), {}, {}, None)
        adapter.start_turn.assert_not_awaited()


class RemainderExclusions(PublicationRemainder):
    async def test_policy_stage_and_published_targets_excluded_before_any_path_acquisition(self):
        baseline = self.retained()
        self.assertTrue(self.basis()['peers'])  # Positive qualified, nonexcluded path.
        policy_only = self.area / 'policy-only-excluded'
        for scope in ['target', 'stage', 'ancestor', 'policy-only']:
            with self.subTest(scope=scope):
                if scope == 'policy-only':
                    self.task['routine_completion']['targets'].append(str(policy_only))
                    # Give this explicit synthetic policy its matching grant,
                    # so grant mismatch cannot mask the exclusion assertion.
                    policies = {name: task.get('routine_completion') for name, task in self.config['tasks'].items()
                                if task['role'] == 'Work'}
                    self.board.conn.execute('UPDATE coordinator_completion_grants_v1 SET policies=?', (encode(policies),))
                excluded = {'target': str(self.target), 'stage': self.stage,
                            'ancestor': str(self.area), 'policy-only': str(policy_only)}[scope]
                self.config['artifact_exclusions'] = [excluded]
                with patch.object(Path, 'is_symlink', side_effect=AssertionError('no path metadata before exclusion')), \
                        patch.object(Path, 'stat', side_effect=AssertionError('no stat before exclusion')), \
                        patch.object(publication, 'read_file', side_effect=AssertionError('no body before exclusion')), \
                        patch.object(publication, 'snapshot_lock', side_effect=AssertionError('no lock/import before exclusion')):
                    with self.assertRaisesRegex(Refusal, 'excluded before metadata'):
                        self.basis()
                if scope == 'policy-only':
                    self.task['routine_completion']['targets'].pop()
        self.assertEqual(self.retained(), baseline)

    async def test_retained_published_target_excluded_before_other_target_validation(self):
        target = self.area / 'owned-published-exclusion'
        target.write_text('owned synthetic published peer\n')
        self.store.db.execute("INSERT INTO file_publications VALUES(?,?,'published',?,NULL,?,NULL)",
                             (self.original, str(target), 'a'*64, encode({'fictional': 'retained witness'})))
        baseline = self.retained()
        self.config['artifact_exclusions'] = [str(target)]
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('no metadata')), \
                patch.object(publication, 'read_file', side_effect=AssertionError('no body')):
            with self.assertRaisesRegex(Refusal, 'excluded before metadata'):
                self.basis()
        self.assertEqual(self.retained(), baseline)

    async def test_fresh_successor_preserves_original_and_peer_with_real_owned_files(self):
        old = self.retained()
        original = self.store.attempt(self.original)
        successor = self.consume(self.request())['successor']
        (self.store.home / 'artifacts' / successor).mkdir(parents=True)
        routine.prepare(self.store, self.board, self.store.job(self.job['id']), successor, self.task)
        stage = Path(publication.stages(self.store, successor)[str(self.target)])
        stage.write_text(stage.read_text() + 'new same-purpose remainder\n')
        publication.conserve_stages(self.store, successor, self.task)
        collect(self.store, successor, {**result(), 'completion': {
            'version': 1, 'local': 'ready', 'failures': [], 'unknowns': [], 'tools': []}},
            tool_completion={'complete': True, 'items': [{'id': 'fictional-success-item',
                'type': 'commandExecution', 'exit_code': 0, 'status': 'completed', 'completed_notification': True}]})
        inode = self.target.stat().st_ino
        self.assertTrue(routine.reconcile(self.store, self.board, self.store.job(self.job['id'])))
        self.assertEqual(self.target.stat().st_ino, inode)
        self.assertEqual(self.target.read_text(), 'current peer survives\nnew same-purpose remainder\n')
        self.assertEqual(self.store.attempt(self.original), original)
        self.assertEqual(self.store.rows('SELECT * FROM outboxes'), old['outboxes'])
        self.assertEqual(Path(self.stage).read_text(), 'old proposal; must never overwrite current peer\n')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        self.assertIsNone(self.store.reserve())
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")), 2)

    async def test_qa_association_requires_retained_candidate_and_original_runner(self):
        root = self.store.home / 'artifacts' / self.original / 'qa-source'
        root.mkdir()
        candidate = root / 'source.txt'
        candidate.write_bytes(b'owned candidate\n')
        item = {'path': 'source.txt', 'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
        runner = {'label': 'qa-runner', 'complete': True, 'exit': 0, 'fixture': 'not an executed QA runner'}
        association = {'method': 'git-blobs-readonly-namespace-v1', 'head': 'fictional-head',
            'tree': 'fictional-tree', 'root': str(root), 'files': [item], 'manifest': digest([item]),
            'runner_record': digest(runner)}
        receipt = {'before': {'head': 'fictional-head', 'tree': 'fictional-tree'},
                   'outcome': {'source_execution': association}, 'tools': [runner]}
        policy = {'source_head': 'fictional-head'}
        self.assertEqual(qa_source.verify(self.store, self.original, policy, receipt), association)
        with self.assertRaises(Refusal): qa_source.verify(self.store, self.original, policy, {})
        runner['exit'] = 1
        with self.assertRaisesRegex(Refusal, 'original runner'): qa_source.verify(self.store, self.original, policy, receipt)
        runner['exit'] = 0
        candidate.write_bytes(b'altered candidate\n')
        with self.assertRaises(Refusal): qa_source.verify(self.store, self.original, policy, receipt)


def load_tests(loader, tests, pattern):
    # Only locally defined cases, not every inherited integration fixture.
    return unittest.TestSuite(cls(name) for cls in [ContinuingBoundaries, RemainderExclusions]
                              for name in cls.__dict__ if name.startswith('test_'))
