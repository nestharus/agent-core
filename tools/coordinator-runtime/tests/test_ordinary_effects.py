"""Contained real Git/owned QA commands; synthetic identities/policy/model seams.

Require an explicit retained fixture root. No HOME/profile migration, real
provider, native collector, board service, product repository or CI operation.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from support import config_at, event, result, queued, collect, ended_job
from coordinator_runtime import ordinary, prospective
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OrdinaryEffects(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        base = Path(os.environ['COORDINATOR_ORDINARY_FIXTURES'])
        if not base.is_absolute() or 'ordinary-effects33' not in base.parts or base.is_symlink():
            raise AssertionError('explicit owned retained ordinary-effects33 fixtures required')
        self.area = base / self._testMethodName / ident()
        self.area.mkdir(mode=0o700, parents=True)
        self.now = 100000.0
        self.repo = self.area / 'repo'
        self.repo.mkdir()
        self.git('init', '--initial-branch=source')
        self.git('remote', 'add', 'origin', 'https://fixture.invalid/owned-source')
        (self.repo / 'source.txt').write_text('first\n')
        self.git('add', 'source.txt')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-m', 'owned first')
        self.old = self.git('rev-parse', 'HEAD')
        self.git('branch', 'destination')
        (self.repo / 'source.txt').write_text('second\n')
        self.git('add', 'source.txt')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-m', 'owned second')
        self.head = self.git('rev-parse', 'HEAD')
        self.config = config_at(self.area)
        self.config['deadlines']['task'] = 15
        shared = self.config['roles']['Work']['board_id']
        for v in self.config['roles'].values():
            v['board_id'] = shared
        for name in ['branch-integrator', 'qa-execution']:
            task = self.config['tasks'][name]
            task.update(effects='owner-reconcile', require_package_scope=True, scope_roots=[str(self.area)], network=True)
            task['effect_authority']['operations'] = ['organize-authorized-refs' if name.startswith('branch') else 'execute-admitted-qa']
        self.config['delivery'] = {'recipients': {r: {'session': v['owner'], 'profile': v['profile'], 'board_role': v['board_role']}
            for r, v in self.config['roles'].items()}}
        for task in self.config['tasks'].values():
            task['allowed_handoffs'] = list(self.config['roles'])
        substrate = module_at(self.config['board_library'], 'board_store')
        catalog = module_at(self.config['board_library'], 'catalog')
        home = Path(self.config['board_home'])
        with catalog.catalog(home) as cat:
            entry = catalog.create(cat, home, 'ordinary-fixture', 'Retained owned fixture', board_id=shared, temporary_test=True)
        self.board_path = entry['db_path']
        with substrate.database(self.board_path) as conn:
            substrate.bind_board(conn, shared, initialize=True)
            for selected in self.config['roles'].values():
                args = substrate.parser().parse_args(['register', '--session', selected['owner'], '--role', selected['board_role'],
                    '--route', 'managed', '--profile', selected['profile']])
                # Identity API seam only, never a real owner/authentication claim.
                with patch.object(substrate, 'acting_session', side_effect=lambda expected: expected):
                    substrate.register(conn, args)
        self.store = Store(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        self.boards = {r: Board(self.config, r) for r in self.config['roles']}
        for role, board in self.boards.items():
            with patch.object(board.store, 'acting_session', side_effect=lambda expected: expected):
                grant = board.grant(self.store, 'Synthetic native fixture authority', delivery=True)
            self.store.enroll(role, grant)
            self.store.reconcile_legacy(role, self.config['roles'][role]['owner'],
                {'collector': 'synthetic prior collector', 'evidence': ['fixture only'], 'remaining_holds': []})
        self.acceptor = ident()
        self.procedure = self.area / 'procedure.md'
        self.procedure.write_text('Independent fixture intent: advance only destination to source; QA exit1 is known failure, not acceptance.\n')

    def git(self, *args):
        command = ['/usr/bin/git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(self.repo), *args]
        completed = subprocess.run(command, capture_output=True, text=True,
            env={**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'})
        with (self.area / 'fixture-git-ends.jsonl').open('a') as ledger:
            ledger.write(encode({'argv': command, 'end': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr}) + '\n')
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout.strip()

    def boundary(self, tasks=None):
        tasks = tasks or ['branch-integrator', 'qa-execution', 'qa-cleanup', 'branch-proposer']
        selection = {'configuration': digest(self.config), 'authority': 'Synthetic Decision33 user/Work future authority',
            'expires': self.now + 100, 'grants': {self.config['tasks'][t]['role']: self.store.enrollment(self.config['tasks'][t]['role'])['grant_id'] for t in tasks},
            'tasks': {t: {'task_hash': digest(self.config['tasks'][t]), 'software_handoffs': {},
                         'ordinary_effects': t in {'branch-integrator', 'qa-execution'}} for t in tasks}}
        return prospective.select(self.store, self.config['roles']['Work']['owner'], selection)

    def admission(self, package='package', kind='local-ref', code=0, readback_ok=True):
        p = {'kind': kind, 'git': '/usr/bin/git', 'git_sha256': sha('/usr/bin/git'), 'repository': str(self.repo),
             'source_ref': 'refs/heads/source', 'source_head': self.head, 'procedure_sha256': sha(self.procedure),
             'resources': [{'key': 'fixture-exclusive-resource', 'owner': self.acceptor, 'authority': 'Synthetic owned lease/disjoint legacy scope', 'expires': self.now + 90}],
             'acceptor': self.acceptor, 'acceptance_authority': 'Independent fixture specification owner', 'timeout': 10, 'max_output': 32768}
        if kind == 'local-ref':
            p.update(ref='refs/heads/destination', before=self.old, target=self.head)
        else:
            output = self.area / 'qa-output'
            output.mkdir(exist_ok=True)
            runner, readback = self.area / 'runner', self.area / 'readback'
            runner.write_text('#!/usr/bin/python3\nfrom pathlib import Path\nPath('+repr(str(output / 'actual-run.txt'))+').write_text("actually executed")\nraise SystemExit('+str(code)+')\n')
            readback.write_text('#!/usr/bin/python3\nfrom pathlib import Path\nassert Path('+repr(str(output / 'actual-run.txt'))+').read_text() == "actually executed"\nprint("SETTLED")\n')
            runner.chmod(0o700)
            readback.chmod(0o700)
            p.update(command={'argv': [str(runner)], 'executable_sha256': sha(runner), 'stdout': None},
                readback={'argv': [str(readback)], 'executable_sha256': sha(readback), 'stdout': 'SETTLED\n' if readback_ok else 'wrong\n'}, known_exits=[0, 1], source_capture={'bwrap': '/usr/bin/bwrap', 'sha256': sha('/usr/bin/bwrap'), 'max_bytes': 1048576, 'max_files': 100})
        task = 'branch-integrator' if kind == 'local-ref' else 'qa-execution'
        scope = {'cwd': str(self.repo), 'read_roots': [str(self.area)], 'write_roots': [str(self.repo)] + ([str(output)] if kind == 'local-qa' else []), 'network': False,
                 'procedure': str(self.procedure), 'resource_evidence': ['owned fixture lease/oracle, no actual resource authority'], 'ordinary_effects': p}
        self.store.admit(package, self.config['roles']['Branch']['owner'], {'task_scopes': {task: scope}})
        return p

    def prepared(self, role='Branch', package='package', name='future', answer=None):
        task = 'branch-integrator' if role == 'Branch' else 'qa-execution'
        queued(self.store, event(self.config, name, role, task, package))
        job = self.store.reserve()
        self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        self.boards[role].bind_software_attempt(self.store, job, attempt, self.store.one("SELECT * FROM admissions WHERE package=?", (job["package"],)))
        collect(self.store, attempt, answer or result(), tool_completion={'complete': True, 'items': [], 'nonzero_completions': []})
        return self.store.job(job['id']), attempt

    async def test_actual_git_CAS_capture_readback_and_independent_acceptance(self):
        self.boundary()
        self.admission()
        job, attempt = self.prepared()
        proof = json.loads(self.store.attempt(attempt)['detail'])['software_authority']
        self.assertEqual(proof['issued_by'], self.config['roles']['Branch']['owner'])
        self.assertEqual(proof['delegated_by'], self.config['roles']['Work']['owner'])
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
        self.assertTrue(await ordinary.perform(self.store, self.boards['Branch'], job))
        self.assertEqual(self.git('rev-parse', 'destination'), self.head)
        run = self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt,))
        receipt = json.loads(run['receipt'])
        self.assertTrue(any(r['complete'] and 'update-ref' in r['argv'] for r in receipt['tools']))
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))
        evidence = {'execution_hash': digest(receipt), 'rationale': 'Independent intended ref/source outcome verified', 'unknowns': []}
        with self.assertRaises(Refusal):
            await ordinary.accept(self.store, receipt['worker'], attempt, 'accepted', evidence)
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
        self.assertTrue(ordinary.accepted_package(self.store, 'package'))
        # Reconciliation is idempotent, never repeats the CAS.
        before = self.store.rows('SELECT * FROM ordinary_tool_records')
        await ordinary.perform(self.store, self.boards['Branch'], self.store.job(job['id']))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'), before)

    async def test_real_QA_failure_can_finish_reporting_but_cannot_be_accepted(self):
        self.boundary()
        self.admission(kind='local-qa', code=1)
        job, attempt = self.prepared(role='QA', answer=result(category='consolidated'))
        await ordinary.perform(self.store, self.boards['QA'], job)
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(receipt['outcome']['status'], 'failed')
        self.assertTrue((self.area / 'qa-output/actual-run.txt').is_file())
        evidence = {'execution_hash': digest(receipt), 'rationale': 'Actual failed oracle requires correction', 'unknowns': []}
        with self.assertRaises(Refusal):
            await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
        await ordinary.accept(self.store, self.acceptor, attempt, 'rejected', evidence)
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))
        self.store.finish_job(job['id'], job['token'])
        response = self.store.event(self.store.job(job['id'])['response'])
        self.assertEqual(response['effect_observation']['outcome']['actual_exit'], 1)

    async def test_stale_ref_partial_and_unknown_runs_refuse_without_replay(self):
        self.boundary()
        self.admission()
        job, attempt = self.prepared()
        self.git('update-ref', 'refs/heads/source', self.old, self.head)
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)
        self.git('update-ref', 'refs/heads/source', self.head, self.old)
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)

    async def test_wrong_QA_readback_retains_original_resources(self):
        self.boundary()
        self.admission(kind='local-qa', readback_ok=False)
        job, _ = self.prepared(role='QA')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)

    async def test_missing_stale_partial_and_forged_evidence_are_not_execution(self):
        epoch = self.boundary()
        self.admission()
        job, attempt = self.prepared()
        with self.store.tx():
            self.store.db.execute("UPDATE attempts SET capture='partial' WHERE id=?", (attempt,))
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        with self.assertRaises(Refusal):
            await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', {'execution_hash': 'fake', 'unknowns': []})
        prospective.revoke(self.store, self.config['roles']['Work']['owner'], epoch['id'])
        with self.assertRaises(Refusal):
            self.boards['Branch']._software_job_grant(self.store, job)
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)

    async def test_boundary_conserves_old_ACK_queue_jobs_grants_outbox_and_writers(self):
        # Exact synthetic snapshot shape. Direct inserts are fixture state, not actual ACK/collection proof.
        for n in range(235):
            e = event(self.config, 'old-' + str(n), 'Work', 'work-proposer')
            self.store.ingest(e)
            with self.store.tx():
                self.store.db.execute("UPDATE events SET ack='done',state='queued',classification=? WHERE id=?",
                    (encode({'event_id': e['id'], 'task': 'work-proposer', 'package': None, 'reason': 'synthetic old classification'}), e['id']))
                self.store.db.execute("INSERT INTO queue(id,event,role,phase,task,state) VALUES(?,?,'Work','proposer','work-proposer','awaiting-owner')", (ident(), e['id']))
        with self.store.tx():
            for n in range(12):
                role = 'Branch' if n == 0 else 'Work'
                self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects,hold_reason) VALUES(?,?,'integrator',?,'[]',?,?,?,'held','unknown','original uncertainty')",
                    (ident(), role, role.lower() + '-integrator', ident(), ident(), self.now))
            self.store._outbox('Work', 'Branch', 'effect-request', {'original': 'unknown'}, key='old-outbox')
            self.store.db.execute("INSERT INTO ordinary_resources VALUES('old-exclusive-resource','old-original')")
            self.store.db.execute('INSERT INTO source_custody VALUES(?,?,?,?)', (e['id'], 'original', 'actual old collector', 'old binding'))
            self.store.db.execute('INSERT INTO file_publications VALUES(?,?,?,?,?,?,?)',
                ('old-original', str(self.area / 'old-target'), 'intent', 'old-sha', str(self.area / 'old-temporary'), None, 'original uncertainty'))
            self.store.db.execute('INSERT INTO qa_package_owners VALUES(?,?,?)', ('old-package', 'old-admission', 'old-original'))
            original = ident()
            old_job = self.store.one("SELECT id FROM jobs WHERE role='Branch'")['id']
            self.store.db.execute('INSERT INTO attempts(id,kind,job,controller,profile,binding,state,created,detail) VALUES(?,?,?,?,?,?,?,?,?)',
                (original, 'task', old_job, 'synthetic-original-collector', '.codex5', encode(self.config['tasks']['branch-integrator']['binding']),
                 'unknown', self.now, encode({'native_original_unknown': True, 'do_not_borrow_END': True})))
            self.store.db.execute('UPDATE jobs SET active_attempt=? WHERE id=?', (original, old_job))
        tables = ['meta', 'enrollments', 'cursors', 'events', 'queue', 'jobs', 'attempts', 'outboxes', 'source_custody', 'file_publications', 'ordinary_resources', 'qa_package_owners']
        before = {t: self.store.rows('SELECT * FROM ' + t) for t in tables}
        identity = (self.store.path.stat().st_dev, self.store.path.stat().st_ino)
        with self.boards['Branch'].opened() as conn:
            grants_before = [dict(r) for r in conn.execute('SELECT * FROM coordinator_grants_v1 ORDER BY id')]
        self.boundary()
        self.assertEqual({t: self.store.rows('SELECT * FROM ' + t) for t in tables}, before)
        self.assertEqual((self.store.path.stat().st_dev, self.store.path.stat().st_ino), identity)
        with self.boards['Branch'].opened() as conn:
            self.assertEqual([dict(r) for r in conn.execute('SELECT * FROM coordinator_grants_v1 ORDER BY id')], grants_before)
        self.assertEqual(len(self.store.rows("SELECT id FROM events WHERE ack='done' AND processed_at IS NULL")), 235)
        self.assertEqual(len(self.store.rows("SELECT id FROM jobs WHERE state!='closed'")), 12)
        # Future work still sees the old writer singleton in the same journal.
        self.admission()
        queued(self.store, event(self.config, 'new', 'Branch', 'branch-integrator', 'package'))
        self.assertIsNone(self.store.reserve())
        old = self.store.rows('SELECT * FROM jobs')[0]
        self.assertIsNone(prospective.for_job(self.store, old))

    async def test_old_queued_members_never_acquire_future_authority(self):
        self.admission()
        queued(self.store, event(self.config, 'old', 'Branch', 'branch-integrator', 'package'))
        self.boundary()
        queued(self.store, event(self.config, 'new', 'Branch', 'branch-integrator', 'package'))
        job = self.store.reserve()
        a = self.store.start_job(job['id'], job['token'])
        with self.assertRaises(Refusal):
            self.boards['Branch'].bind_software_attempt(self.store, self.store.job(job['id']), a, self.store.one("SELECT * FROM admissions WHERE package=?", (job["package"],)))
        self.assertEqual(len(json.loads(job['members'])), 2)

    async def test_QA_five_plus_one_and_recurring_alerts_remain(self):
        self.boundary()
        for i in range(6):
            self.admission(package='qa-' + str(i), kind='local-qa')
            queued(self.store, event(self.config, 'qa-' + str(i), 'QA', 'qa-execution', 'qa-' + str(i)))
        jobs = [self.store.reserve() for _ in range(5)]
        self.assertTrue(all(j and j['phase'] == 'execution' for j in jobs))
        self.assertIsNone(self.store.reserve())
        # Separate cleanup slot, no claim this is semantic acceptance.
        self.store.admit('cleanup-only', self.config['roles']['Branch']['owner'], {'fixture': 'separate package'})
        queued(self.store, event(self.config, 'cleanup', 'QA', 'qa-cleanup', 'cleanup-only'))
        self.assertEqual(self.store.reserve()['phase'], 'cleanup')
        self.assertIsNone(self.store.reserve())
        self.now += 1000
        first = self.store.emit_alerts()
        originals = self.store.rows('SELECT * FROM alerts ORDER BY id')
        self.assertEqual(self.store.emit_alerts(), [])
        self.now += self.config['deadlines']['alert_interval']
        second = self.store.emit_alerts()
        self.assertTrue(all(row in self.store.rows('SELECT * FROM alerts ORDER BY id') for row in originals))
        self.assertTrue(first)
        self.assertTrue(second)
        self.assertTrue({a['id'] for a in first}.isdisjoint({a['id'] for a in second}))

    async def test_qualification_requires_real_acceptance_and_fresh_ref(self):
        self.boundary()
        self.admission()
        job, attempt = self.prepared()
        await ordinary.perform(self.store, self.boards['Branch'], job)
        # A legacy supplied accepted JSON must not qualify the new interface.
        with self.store.tx():
            self.store.db.execute('UPDATE admissions SET accepted=? WHERE package=?', (encode({'accepted': True}), 'package'))
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))
        # This changes the full admission and so invalidates the original launch proof.
        with self.assertRaises(Refusal):
            await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', {'execution_hash': 'fake', 'rationale': 'not proof', 'unknowns': []})
        with self.store.tx():
            self.store.db.execute('UPDATE admissions SET accepted=NULL WHERE package=?', ('package',))
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted',
            {'execution_hash': digest(receipt), 'rationale': 'Independent accepted fixture outcome', 'unknowns': []})
        await ordinary.qualification(self.store, self.store.job(job['id']))
        self.assertTrue(ordinary.qualification_current(self.store, self.store.job(job['id'])))
        self.git('update-ref', 'refs/heads/destination', self.old, self.head)
        with self.assertRaises(Refusal):
            await ordinary.qualification(self.store, self.store.job(job['id']))
        self.assertFalse(ordinary.qualification_current(self.store, self.store.job(job['id'])))

    async def test_current_resource_and_procedure_not_silent_JSON(self):
        self.boundary()
        self.admission(kind='local-qa')
        job, attempt = self.prepared(role='QA')
        self.procedure.write_text('changed procedure')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertFalse((self.area / 'qa-output/actual-run.txt').exists())
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    def github_fixture(self, event_name='pull_request', status='completed'):
        # Owned executable returning synthetic API records. This is deliberately
        # not a GitHub/CI execution or actual event/currentness qualification.
        self.admission(kind='local-qa')
        row = self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))
        admission = json.loads(row['receipt'])
        scope = admission['task_scopes']['qa-execution']
        p = scope['ordinary_effects']
        for key in ['command', 'readback', 'known_exits', 'source_capture']:
            del p[key]
        executable = self.area / 'synthetic-gh'
        run = {'id': 42, 'run_attempt': 2, 'head_sha': self.head, 'event': event_name,
               'path': '.github/workflows/ci.yml', 'repository': {'full_name': 'fixture/project'},
               'status': status, 'conclusion': 'success' if status == 'completed' else None}
        jobs = {'total_count': 1, 'jobs': [{'id': 501, 'name': 'fixture assertions', 'status': 'completed', 'conclusion': 'success'}]}
        executable.write_text('#!/usr/bin/python3\nimport json,sys\nprint(json.dumps('+repr(jobs)+' if "/jobs?" in sys.argv[-1] else '+repr(run)+'))\n')
        executable.chmod(0o700)
        p.update(kind='github-run', gh=str(executable), gh_sha256=sha(executable), repository_slug='fixture/project',
                 run_id=42, run_attempt=2, event='pull_request', workflow='.github/workflows/ci.yml', job_ids=[501])
        scope['network'] = True  # Policy seam only; executable has no network code.
        self.store.admit('package', self.config['roles']['Branch']['owner'], admission)

    async def test_owned_CI_API_seam_matches_exact_run_event_jobs(self):
        self.boundary()
        self.github_fixture()
        job, attempt = self.prepared(role='QA')
        await ordinary.perform(self.store, self.boards['QA'], job)
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(receipt['outcome']['run']['run_attempt'], 2)
        self.assertEqual(receipt['outcome']['jobs'][0]['id'], 501)
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))

    async def test_wrong_CI_event_is_unknown_not_accepted(self):
        self.boundary()
        self.github_fixture(event_name='workflow_dispatch')
        job, attempt = self.prepared(role='QA')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)

    async def test_incomplete_CI_stays_with_original_monitor(self):
        self.boundary()
        self.github_fixture(status='in_progress')
        job, attempt = self.prepared(role='QA')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)

    async def test_actual_delegated_callback_consumes_known_failed_reporting(self):
        self.boundary()
        self.admission(kind='local-qa', code=1)
        job, attempt = self.prepared(role='QA')
        await ordinary.perform(self.store, self.boards['QA'], job)
        self.store.owner_report(self.store.job(job['id']), self.store.attempt(attempt), result())
        self.store.finish_job(job['id'], job['token'])
        outbox = self.store.one('SELECT * FROM outboxes WHERE job=? AND kind=\'result\'', (job['id'],))
        board = self.boards['QA']
        # Only this owned board's notification signal is stubbed; no real socket.
        with patch.object(board.store.active_listener, 'signal_post', return_value=None):
            board.post_delivery(self.store, outbox)
        returned = board.complete_own_delivery(self.store, outbox)
        self.assertIsNotNone(returned)
        self.assertIsNotNone(returned['processed_at'])
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))

    async def test_dispatcher_uses_owned_tools_after_collected_preparation(self):
        self.boundary()
        self.admission()
        queued(self.store, event(self.config, 'dispatch', 'Branch', 'branch-integrator', 'package'))
        job = self.store.reserve()
        a = self.store.start_job(job['id'], job['token'])
        runtime = Dispatcher(self.store, models=object(), boards=self.boards)
        async def model(attempt, prompt, spec, schema):
            self.assertIn('ORDINARY PREPARATION ONLY', prompt)
            self.assertEqual(spec['sandbox'], 'read-only')
            self.assertFalse(spec['network'])
            self.assertEqual(spec['effect_authority']['write_roots'], [])
            self.store.begin(attempt, {'synthetic': 'model seam only'})
            self.store.session(attempt, ident())
            return {'result': result(), 'exit': 0, 'capture': 'complete', 'cleanup': 'done', 'error': None,
                    'detail': {'tool_completion': {'complete': True, 'items': [], 'nonzero_completions': []}}}
        runtime.run_model = model
        await runtime.execute(job['id'], a)
        self.assertEqual(self.git('rev-parse', 'destination'), self.head)
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs WHERE attempt=?', (a,))['state'], 'reconciled')
