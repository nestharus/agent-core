"""Decision37 public remainder capability on retained owned fixture journals.

COORDINATOR_REMAINDER_FIXTURES must name an explicit owned absolute directory.
Owner/Board/collector/business/protocol records are synthetic seams. The one
owned construction subprocess END is separately retained, never a model END.
No identity environment, client, shared control or provider access is needed.
"""
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from support import config_at, enrolled, event, queued, collect, result
from coordinator_runtime import cli, custody, publication, routine
from coordinator_runtime.completion import Completion
from coordinator_runtime.contracts import LUNA, Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


class QualifiedBoard(Completion):
    """Real completion-policy method, synthetic enrollment/authority seam."""
    role = 'Work'

    def __init__(self, config, grant):
        self.config, self.grant, self.expired = config, grant, False
        import sqlite3
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(routine.BOARD_SCHEMA)
        policies = {name: task.get('routine_completion') for name, task in config['tasks'].items() if task['role'] == self.role}
        self.conn.execute('INSERT INTO coordinator_completion_grants_v1 VALUES(?,?,?)',
                          (grant['id'], encode(policies), 'Synthetic explicit routine delegation'))

    @contextlib.contextmanager
    def opened(self):
        yield self.conn

    def _grant(self, conn, store):
        if self.expired:
            raise Refusal('synthetic current authority expired')
        return dict(self.grant)

    def verify_authority(self, store):
        return self._grant(self.conn, store)


class PublicationRemainder(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        base = Path(os.environ['COORDINATOR_REMAINDER_FIXTURES'])
        if not base.is_absolute() or not base.is_dir() or base.is_symlink():
            raise AssertionError('explicit owned absolute fixture directory required')
        self.area = base / (self._testMethodName + '-' + ident())
        self.area.mkdir(mode=0o700)
        self.process_ends = []
        self.config = config_at(self.area)
        self.target = self.area/'canonical.json'
        self.second = self.area/'second.json'
        self.target.write_text('original canonical one\n')
        self.second.write_text('original canonical two\n')
        task = self.config['tasks']['work-integrator']
        task.update(effects='owner-reconcile', network=False,
                    routine_completion={'kind': 'file-witness', 'targets': [str(self.target), str(self.second)]})
        task['effect_authority'].update(write_roots=[str(self.target), str(self.second)],
                                        operations=['read-reports', 'write-role-records'])
        self.task = task
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.owner = self.config['roles']['Work']['owner']
        enrollment = self.store.enrollment('Work')
        self.board = QualifiedBoard(self.config, {'id': enrollment['grant_id'], 'owner': self.owner,
                    'issued_by': self.owner, 'authority': 'Synthetic bounded canonical duty'})
        self.addCleanup(self.board.conn.close)
        queued(self.store, event(self.config, ident()))
        self.job = self.store.reserve()
        self.original = self.store.start_job(self.job['id'], self.job['token'])
        (self.store.home/'artifacts'/self.original).mkdir(parents=True)
        routine.prepare(self.store, self.board, self.job, self.original, task)
        self.stage = publication.stages(self.store, self.original)[str(self.target)]
        Path(self.stage).write_text('old proposal; must never overwrite current peer\n')
        publication.conserve_stages(self.store, self.original, task)
        answer = {**result(), 'artifacts': list(publication.stages(self.store, self.original).values()),
                  'completion': {'version': 1, 'local': 'ready', 'failures': [], 'unknowns': [], 'tools': []}}
        collect(self.store, self.original, answer,
                tool_completion={'complete': True, 'items': [{'id': 'synthetic-command', 'type': 'commandExecution',
                    'exit_code': 0, 'status': 'completed', 'completed_notification': True}]})
        self.store.hold_job(self.job['id'], 'synthetic original disposition error')
        self.store.record_operational_error(self.job['id'], {'error': 'synthetic original disposition error'}, 'Work', 'task-disposition-error')
        self.store.reconcile_effects(self.job['id'], self.job['token'], self.owner,
                {'evidence': ['Synthetic actual owner accounted known original effects; publication independent'], 'unknown_effects': []})
        self.selection = self.store.request_recovery(self.job['id'], self.job['token'], self.original, self.owner,
                {'mode': 'remaining-work', 'reason': 'Same original target and WHY; peer-compatible construction only',
                 'evidence': ['Owned synthetic retained purpose'], 'remaining': 'Reconcile this same catalog purpose with current peers, preserve all old duties'})
        self.store.consume_recovery_request(self.selection['id'])
        self.diagnosis = self.store.diagnosis_attempt(self.job['id'])
        self.choice = {'profile': '.codex3', 'remaining': 'Same-purpose staged publication remainder only',
                       'rationale': 'Preserve current peers and retained accepted work; never replay old stages'}
        collect(self.store, self.diagnosis, self.choice, binding_readback=LUNA, root_identity_observed=True)
        # Supplied retained-success/awaiting shape; not an actual business diagnosis or runtime trace.
        self.store.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?", (self.job['id'],))
        self.store.hold_job(self.job['id'], publication.INCOMPLETE_HOLD)
        self.target.write_text('current peer survives\n')
        for n in range(8):
            self.store._outbox('Work', 'Work', 'question', {'synthetic': n, 'meaning': 'distinct retained journal duty'}, job=self.job['id'])
        self.runtime = Dispatcher(self.store, models=object(), boards={'Work': self.board})

    async def asyncTearDown(self):
        (self.area/'owned-process-ends.json').write_text(encode(self.process_ends))

    def basis(self):
        return self.store.publication_remainder_basis(self.job['id'], self.job['token'], self.original,
                                                      self.diagnosis, self.selection['id'], self.board)

    def receipt(self, basis=None):
        return {'mode': 'use-diagnosis', 'remaining': None, 'diagnosis': self.diagnosis,
                'selection': self.selection['id'], 'reason': 'Synthetic genuine-owner seam reaffirms SAME retained target AND WHY under current peers',
                'evidence': ['Synthetic owner full retained selection/diagnosis and current source/publication judgment'],
                'publication_remainder': self.basis() if basis is None else basis}

    def request(self, receipt=None, actor=None):
        return self.store.request_recovery(self.job['id'], self.job['token'], self.original, actor or self.owner,
                    receipt or self.receipt(), publication_board=self.board)

    def consume(self, request):
        return self.store.consume_recovery_request(request['id'], publication_board=self.board)

    def owner_cli(self, command):
        path = self.area/'config.json'
        path.write_text(encode(self.config))
        output = io.StringIO()
        # Explicit owner/current-Board seams, no fake environment ownership.
        with patch.object(cli, 'actual_actor', side_effect=lambda expected: self.owner if expected == self.owner else None), \
                patch.object(cli, 'Board', return_value=self.board), contextlib.redirect_stdout(output):
            end = cli.main(['--config', str(path), *command])
        return end, json.loads(output.getvalue())

    def retained(self):
        return {table: self.store.rows('SELECT * FROM '+table) for table in
                ['events', 'queue', 'outboxes', 'results', 'routine_runs', 'routine_stages', 'file_publications', 'canonical_backups', 'artifact_custody']}

    async def test_public_owner_basis_request_dispatch_and_fresh_publication_conserve_history(self):
        original, diagnosis = self.store.attempt(self.original), self.store.attempt(self.diagnosis)
        retained = self.retained()
        end, basis = self.owner_cli(['publication-remainder-basis', self.job['id'], '--token', self.job['token'],
                    '--attempt', self.original, '--diagnosis', self.diagnosis, '--selection', self.selection['id']])
        self.assertEqual(end, 0, basis)
        self.assertEqual(basis, self.basis())
        argv=[sys.executable,str(Path(__file__).resolve().parents[1]/'coordinator'),
              '--config',str(self.area/'config.json'),'publication-remainder-basis',self.job['id'],
              '--token',self.job['token'],'--attempt',self.original,'--diagnosis',self.diagnosis,
              '--selection',self.selection['id']]
        denied=subprocess.run(argv,cwd=self.area,capture_output=True,text=True)
        self.process_ends.append({'argv':argv,'END':denied.returncode,'stdout':denied.stdout,'stderr':denied.stderr,
                                 'meaning':'actual public CLI refusal with genuine unchanged environment; fixture owner is a synthetic seam'})
        self.assertEqual(denied.returncode,2,denied.stdout)
        self.assertEqual(json.loads(denied.stdout)['state'],'held')
        packet = self.area/'owner-request.json'
        packet.write_text(encode(self.receipt(basis)))
        end, request = self.owner_cli(['request-recovery', self.job['id'], '--token', self.job['token'],
                    '--attempt', self.original, '--receipt', str(packet)])
        self.assertEqual(end, 0, request)
        self.assertEqual(self.request(self.receipt(basis)), request)
        self.runtime.execute = AsyncMock()
        self.runtime.recover = AsyncMock(side_effect=AssertionError('no new diagnosis'))
        self.runtime.reconcile_completed()
        if self.runtime.active:
            await asyncio.gather(*self.runtime.active)
        new = self.store.job(self.job['id'])['active_attempt']
        self.runtime.execute.assert_awaited_once_with(self.job['id'], new)
        self.runtime.recover.assert_not_awaited()
        self.assertEqual(self.retained(), retained)
        self.assertEqual(self.store.attempt(self.original), original)
        self.assertEqual(self.store.attempt(self.diagnosis), diagnosis)
        self.assertEqual(self.store.job(self.job['id'])['members'], self.job['members'])
        self.assertEqual(self.store.job(self.job['id'])['token'], self.job['token'])
        self.assertIsNone(self.consume(request))
        self.runtime.reconcile_completed()
        self.runtime.execute.assert_awaited_once()
        current = self.store.job(self.job['id'])
        self.assertEqual(current['effects'], 'unknown')
        (self.store.home/'artifacts'/new).mkdir(parents=True)
        routine.prepare(self.store, self.board, current, new, self.task)
        newstage = publication.stages(self.store, new)[str(self.target)]
        self.assertEqual(Path(newstage).read_text(), 'current peer survives\n')
        argv = [sys.executable, '-c', 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+"same-purpose remainder\\n")', newstage]
        process = subprocess.run(argv, cwd=self.area, capture_output=True, text=True)
        self.process_ends.append({'argv': argv, 'END': process.returncode, 'stdout': process.stdout,
                                  'stderr': process.stderr, 'meaning': 'actual owned Python construction process, not a model/protocol END'})
        self.assertEqual(process.returncode, 0, process.stderr)
        publication.conserve_stages(self.store, new, self.task)
        answer = {**result(), 'completion': {'version': 1, 'local': 'ready', 'failures': [], 'unknowns': [], 'tools': []}}
        collect(self.store, new, answer, tool_completion={'complete': True, 'items': [
            {'id': 'synthetic-protocol-item', 'type': 'commandExecution', 'exit_code': 0, 'status': 'completed', 'completed_notification': True}]})
        inode = self.target.stat().st_ino
        self.assertTrue(routine.reconcile(self.store, self.board, self.store.job(self.job['id'])))
        self.assertEqual(self.target.read_text(), 'current peer survives\nsame-purpose remainder\n')
        self.assertEqual(self.target.stat().st_ino, inode)
        self.assertEqual(self.store.attempt(self.original), original)
        self.assertEqual(Path(self.stage).read_text(), 'old proposal; must never overwrite current peer\n')
        self.assertEqual(self.store.rows('SELECT * FROM outboxes'), retained['outboxes'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')), 1)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")), 2)
        self.assertIsNone(self.store.reserve())

    async def test_unrelated_hold_or_flag_only_or_unqualified_original_cannot_request(self):
        basis = self.basis()
        with self.assertRaises(Refusal):
            self.request(self.receipt({'version': 1}))
        self.store.hold_job(self.job['id'], 'Independent custodian duty')
        with self.assertRaisesRegex(Refusal, 'unrelated job hold'):
            self.request(self.receipt(basis))
        self.store.hold_job(self.job['id'], publication.INCOMPLETE_HOLD)
        self.store.db.execute('DELETE FROM routine_runs WHERE attempt=?', (self.original,))
        with self.assertRaisesRegex(Refusal, 'original incomplete delegated routine run'):
            self.request(self.receipt(basis))
        self.assertEqual(len(self.store.rows('SELECT * FROM recovery_requests')), 1)

    async def test_unknown_effects_closure_and_partial_intent_refuse_without_mutation(self):
        basis = self.basis()
        for field, value in [('effects', 'unknown'), ('effect_receipt', encode({'unknown_effects': ['unaccounted write']})),
                             ('effect_receipt', encode({'actor': ident(), 'evidence': ['wrong owner'], 'unknown_effects': []}))]:
            previous = self.store.job(self.job['id'])[field]
            self.store.db.execute('UPDATE jobs SET '+field+'=? WHERE id=?', (value, self.job['id']))
            with self.assertRaises(Refusal):
                self.request(self.receipt(basis))
            self.store.db.execute('UPDATE jobs SET '+field+'=? WHERE id=?', (previous, self.job['id']))
        old = self.store.attempt(self.original)
        self.store.db.execute('UPDATE attempts SET exit=NULL WHERE id=?', (self.original,))
        with self.assertRaisesRegex(Refusal, 'collected END'):
            self.request(self.receipt(basis))
        self.store.db.execute('UPDATE attempts SET exit=? WHERE id=?', (old['exit'], self.original))
        self.store.db.execute("INSERT INTO file_publications VALUES(?,?,'intent',?,NULL,NULL,NULL)", (self.original, str(self.target), 'f'*64))
        with self.assertRaisesRegex(Refusal, 'unresolved publication intent'):
            self.request(self.receipt(basis))
        self.assertEqual(self.target.read_text(), 'current peer survives\n')
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")), 1)

    async def test_stale_peer_after_request_prevents_allocation_and_after_allocation_prevents_staging(self):
        request = self.request()
        self.target.write_text('later peer must survive\n')
        with self.assertRaisesRegex(Refusal, 'basis changed'):
            self.consume(request)
        self.assertEqual(self.store.job(self.job['id'])['active_attempt'], self.original)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?', (request['id'],))['state'], 'pending')
        # A changed request requires an authentic new owner choice, never mutation of this pending receipt.
        self.assertEqual(self.target.read_text(), 'later peer must survive\n')

    async def test_peer_change_after_allocation_prevents_fresh_staging(self):
        new = self.consume(self.request())['successor']
        self.second.write_text('late peer update\n')
        (self.store.home/'artifacts'/new).mkdir(parents=True)
        with self.assertRaisesRegex(Refusal, 'peer preimages/grant changed'):
            routine.prepare(self.store, self.board, self.store.job(self.job['id']), new, self.task)
        self.assertEqual(publication.stages(self.store, new), {})
        self.assertEqual(self.second.read_text(), 'late peer update\n')

    async def test_invalid_source_owner_different_purpose_and_expired_grant_remain_protected(self):
        receipt = self.receipt()
        with self.assertRaisesRegex(Refusal, 'actual enrolled role owner'):
            self.request(receipt, actor=ident())
        self.board.expired = True
        with self.assertRaisesRegex(Refusal, 'authority expired'):
            self.request(receipt)
        self.board.expired = False
        source = json.loads(self.job['members'])[0]['event']
        self.store.set_hold(source, 'independent source hold')
        with self.assertRaisesRegex(Refusal, 'source/legacy holds'):
            self.request(receipt)
        self.store.set_hold(source, None)
        changed={**self.store.event(source),'body':'different source'}
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?', (encode(changed), source))
        with self.assertRaisesRegex(Refusal, 'source changed'):
            self.request(receipt)

    async def test_changed_purpose_choice_or_selection_cannot_be_silently_substituted(self):
        request = self.request()
        self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',
                (encode({**self.choice, 'remaining': 'different business purpose', 'rationale': 'different WHY'}), self.diagnosis))
        with self.assertRaisesRegex(Refusal, 'basis changed'):
            self.consume(request)
        self.assertEqual(self.store.job(self.job['id'])['active_attempt'], self.original)

    async def test_expiry_after_request_and_missing_completion_policy_refuse_consumption(self):
        request = self.request()
        self.board.expired = True
        with self.assertRaisesRegex(Refusal, 'authority expired'):
            self.consume(request)
        self.board.expired = False
        self.board.conn.execute('UPDATE coordinator_completion_grants_v1 SET policies=?', (encode({}),))
        with self.assertRaisesRegex(Refusal, 'not delegated'):
            self.consume(request)
        self.assertEqual(self.store.job(self.job['id'])['active_attempt'], self.original)

    async def test_old_result_fallback_and_second_successor_are_blocked(self):
        self.runtime.try_finish = lambda *args: self.fail('held original must never be redisposed')
        self.runtime.reconcile_completed()
        new = self.consume(self.request())['successor']
        with self.assertRaises(Refusal):
            self.request()
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")), 2)
        self.assertIsNone(self.store.attempt(new)['begin'])
        self.assertIsNone(self.store.reserve())

    async def test_changed_custody_and_exclusion_refuse_before_path_access(self):
        basis = self.basis()
        Path(self.stage).write_text('changed unconserved stage')
        with self.assertRaisesRegex(Refusal, 'durable staging custody'):
            self.request(self.receipt(basis))
        self.config['artifact_exclusions'] = [str(self.target)]
        with patch.object(publication, 'read_file', side_effect=AssertionError('excluded target must fence before reads')):
            with self.assertRaisesRegex(Refusal, 'excluded before metadata'):
                self.request(self.receipt(basis))

    async def test_known_published_subset_is_conserved_and_changed_published_effect_refuses(self):
        # Exact known no-op publication of second target; one target still needs new construction.
        run = self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (self.original,))
        before = json.loads(run['before_files'])[str(self.second)]
        self.store.db.execute("INSERT INTO file_publications VALUES(?,?,'published',?,NULL,?,NULL)",
                              (self.original, str(self.second), before['sha256'], encode(before)))
        request = self.request()
        published = self.store.rows('SELECT * FROM file_publications')
        self.second.write_text('changed known published peer\n')
        with self.assertRaisesRegex(Refusal, 'published effects changed'):
            self.consume(request)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), published)
        self.assertEqual(self.store.job(self.job['id'])['active_attempt'], self.original)

    async def test_owned_restart_continuity_allocation_failure_rolls_back_then_allocates_once(self):
        previous = self.store.controller
        before = self.store.job(self.job['id'])
        original, diagnosis = self.store.attempt(self.original), self.store.attempt(self.diagnosis)
        receipt = self.receipt()
        # Synthetic service-closure assertion, distinct from actual process END receipts.
        receipt['collector_continuity'] = {'scope': 'closure-only-after-owned-restart',
            'from_controller': previous, 'service_actor': self.config['actor'],
            'service_end': 0, 'service_collected': True, 'evidence': ['Synthetic old-service closure/collection seam']}
        request = self.request(receipt)
        other = Store(self.config)
        self.addCleanup(other.close)
        self.assertNotEqual(previous, other.controller)
        runtime = Dispatcher(other, models=object(), boards={'Work': self.board})
        runtime.execute = AsyncMock()
        runtime.recover = AsyncMock(side_effect=AssertionError('no equivalent diagnosis'))
        with patch.object(other, '_attempt', side_effect=Refusal('synthetic bounded allocation failure')):
            runtime.reconcile_recovery_requests()
        self.assertEqual(self.store.job(self.job['id']), before)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?', (request['id'],))['state'], 'pending')
        runtime.execute.assert_not_called()
        runtime.reconcile_recovery_requests()
        if runtime.active:
            await asyncio.gather(*runtime.active)
        job = self.store.job(self.job['id'])
        handoff = json.loads(job['collection_handoff'])
        self.assertEqual(handoff['original_collector'], previous)
        self.assertEqual(handoff['original_attempt'], self.original)
        self.assertEqual(handoff['actual_exit'], original['exit'])
        self.assertEqual(handoff['actual_collected_at'], original['collected'])
        self.assertEqual(self.store.attempt(self.original), original)
        self.assertEqual(self.store.attempt(self.diagnosis), diagnosis)
        runtime.execute.assert_awaited_once_with(self.job['id'], job['active_attempt'])
        runtime.reconcile_recovery_requests()
        runtime.execute.assert_awaited_once()
        runtime.recover.assert_not_awaited()

    async def test_known_published_subset_allows_only_new_successor_and_retains_original_rows(self):
        run = self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (self.original,))
        before = json.loads(run['before_files'])[str(self.second)]
        self.store.db.execute("INSERT INTO file_publications VALUES(?,?,'published',?,NULL,?,NULL)",
                              (self.original, str(self.second), before['sha256'], encode(before)))
        published = self.store.rows('SELECT * FROM file_publications')
        request = self.request()
        new = self.consume(request)['successor']
        self.assertNotEqual(new, self.original)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), published)
        self.assertIsNone(self.consume(request))

    async def test_peer_change_after_fresh_staging_still_refuses_canonical_publication(self):
        new = self.consume(self.request())['successor']
        (self.store.home/'artifacts'/new).mkdir(parents=True)
        routine.prepare(self.store, self.board, self.store.job(self.job['id']), new, self.task)
        newstage = publication.stages(self.store, new)[str(self.target)]
        Path(newstage).write_text('new proposal must not overwrite later peer')
        publication.conserve_stages(self.store, new, self.task)
        collect(self.store, new, result(), tool_completion={'complete': True, 'items': []})
        self.target.write_text('peer after fresh staging\n')
        run = self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (new,))
        with self.assertRaisesRegex(Refusal, 'canonical bytes changed'):
            publication.publish(self.store, self.board, self.store.job(self.job['id']), self.store.attempt(new), run, self.task)
        self.assertEqual(self.target.read_text(), 'peer after fresh staging\n')
        self.assertEqual(self.store.rows('SELECT * FROM file_publications WHERE attempt=?', (new,)), [])

    async def test_owner_cli_journal_open_retains_unsafe_path_refusals(self):
        original=self.target.read_bytes()
        for kind in ['symlink','directory','world-readable','multiple-links']:
            root=self.area/kind
            root.mkdir(mode=0o700)
            config=config_at(root)
            state=Path(config['state_dir'])
            state.mkdir(mode=0o700)
            db=state/'runtime.sqlite3'
            if kind=='symlink':db.symlink_to(self.target)
            elif kind=='directory':db.mkdir(mode=0o700)
            elif kind=='multiple-links':os.link(self.target,db)
            else:
                db.write_bytes(b'owned invalid database must not be opened')
                db.chmod(0o644)
            with self.assertRaisesRegex(Refusal,'private single-link runtime database'):
                Store(config)
        self.assertEqual(self.target.read_bytes(),original)
