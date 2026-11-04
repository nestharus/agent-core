"""Isolated software controls; no profiles, Board, provider, CI or real queues.

Run directly with --fixtures ABSOLUTE_FRESH_DIRECTORY. --kernel-ro requires
the caller's read-only mounts and network/PID namespace before product imports.
All protocol owners/originals/processing/effect receipts here are FICTIONAL.
SQLite connections remain referenced until os._exit to retain WAL/SHM files;
no fixture cleanup, file deletion or session/home substitution is performed.
"""
import argparse
import asyncio
import contextlib
import errno
import hashlib
import json
import os
from pathlib import Path
import resource
import socket
import sys
import time
import traceback
import unittest
from unittest.mock import patch

ARGS = None
STORES = []
CASES = []
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def imports():
    global Store, Refusal, Backpressure, validate_config, encode, digest, LUNA, SOL
    global windows, capacity, custody, publication, routine, Dispatcher, Service, cli
    from coordinator_runtime.store import Store
    from coordinator_runtime.contracts import Refusal, Backpressure, validate_config, encode, digest, LUNA, SOL
    from coordinator_runtime import windows, capacity, custody, publication, routine, cli
    from coordinator_runtime.dispatcher import Dispatcher
    from coordinator_runtime.custodian_service import Service


ROLES = ('Work', 'Branch', 'Reviews', 'QA')
OWNERS = {r: '00000000-0000-4000-8000-' + str(i + 1).zfill(12) for i, r in enumerate(ROLES)}
ACTOR = '00000000-0000-4000-8000-000000000099'
TASKS = ('work-proposer', 'work-integrator', 'branch-proposer', 'branch-integrator',
         'reviews-proposer', 'reviews-integrator', 'qa-execution', 'qa-cleanup')


def config(root):
    tasks = {}
    for i, name in enumerate(TASKS):
        role, phase = ROLES[i // 2], name.split('-', 1)[1]
        effects = ('owner-reconcile' if name in {'work-integrator', 'branch-integrator', 'qa-execution'} else
                   'owned-artifacts' if name in {'reviews-integrator', 'qa-cleanup'} else 'none')
        responses = {'scope': ['work-proposer'], 'blocker': ['work-proposer']}
        if phase == 'proposer':
            responses['proposal'] = [name.replace('proposer', 'integrator')]
        if name == 'reviews-proposer':
            responses['consolidated'] = ['reviews-integrator']
        if name == 'reviews-integrator':
            responses['consolidated'] = ['work-proposer']
        if name == 'qa-execution':
            responses['consolidated'] = ['qa-cleanup']
        if name == 'qa-cleanup':
            responses['qualification'] = ['branch-proposer']
        tasks[name] = {'role': role, 'phase': phase, 'profile': '.codex2', 'binding': SOL,
            'effects': effects, 'sandbox': 'read-only' if effects == 'none' else 'workspace-write',
            'cwd': str(root), 'templates': [str(Path(__file__).resolve())],
            'authority': 'FICTIONAL isolated software only', 'purpose': 'FICTIONAL target and WHY',
            'capacity': 5, 'responses': responses, 'delivery_required': True,
            'allowed_handoffs': list(ROLES) + ['Root'] if role not in {'Reviews', 'QA'} else
                                ['Work'] if role == 'Reviews' else ['Branch', 'Work'],
            'effect_authority': {'owner': OWNERS[role], 'read_roots': [str(root)],
                'write_roots': [str(root)] if effects == 'owner-reconcile' else [],
                'operations': ['read-source'] + (['write-role-records'] if effects == 'owner-reconcile' else
                                                ['write-owned-artifacts'] if effects == 'owned-artifacts' else [])}}
        if name in {'branch-integrator', 'qa-execution'}:
            tasks[name].update(require_package_scope=True, scope_roots=[str(root)])
    tasks['reviews-proposer'].update(execution='owner', binding={'model': 'gpt-xhigh', 'provider': 'opaque', 'effort': 'opaque'})
    tasks['work-integrator']['routine_completion'] = {'kind': 'file-witness', 'targets': [str(root / 'fictional-work.json')]}
    return {'version': 1, 'actor': ACTOR, 'state_dir': str(root / 'state'), 'profiles': ['.codex2'],
        'execution_pool_routes': str(root / 'NEVER-READ-pool.toml'),
        'classifier': {'binding': LUNA, 'profile': '.codex2', 'cwd': str(root)},
        'diagnosis': {'binding': LUNA, 'profile': '.codex2', 'cwd': str(root)},
        'roles': {r: {'owner': OWNERS[r], 'profile': '.codex2', 'board_id': OWNERS[r], 'board_role': r,
            'legacy_hold': 'FICTIONAL legacy not live', 'package_admission_required': r == 'QA',
            'routes': [n for n in TASKS if tasks[n]['role'] == r] + (['work-proposer'] if r != 'Work' else [])} for r in ROLES},
        'tasks': tasks, 'canonical_publication': {'method': 'retention-same-inode-v1', 'library': str(root / 'NEVER-IMPORTED-retention.py')},
        'limits': {'max_events': 300, 'max_jobs': 32, 'max_attempts': 500, 'max_outboxes': 300,
            'max_alerts': 80, 'max_alert_debt': 80, 'max_bytes': 16 * 1024 * 1024, 'max_files': 1000,
            'max_result_bytes': 65536, 'max_artifact_bytes': 65536, 'max_owner_corrections': 4},
        'deadlines': {k: v for k, v in [('classify', 10), ('task', 60), ('ack', 30), ('backlog', 100),
            ('bind', 5), ('interrupt', 2), ('shutdown', 2), ('alert_interval', 300)]},
        'alert_cadences': {'root-capacity': 300, 'stale-branch-worktree': 3600, 'acceptance-request': 86400},
        'recheck_seconds': .01,
        'window_service': {'tasks': list(TASKS), 'max_new_inputs': 40, 'batch_size': 8, 'max_decisions': 16},
        'delivery': {'alert_role': 'Work', 'alert_recipient': 'Work', 'recipients':
            {r: {'session': OWNERS.get(r, ACTOR), 'profile': '.codex2', 'board_role': r} for r in (*ROLES, 'Root')}}}


class FictionalPool:
    def allocate(self):
        return {'profile': '.codex2', 'meaning': 'FICTIONAL no pool files/counters or native account access'}

    def status(self):
        return {'state': 'FICTIONAL-inert'}


class Controls(unittest.TestCase):
    def setUp(self):
        self.started = time.monotonic()
        self.root = ARGS.fixtures / self._testMethodName
        self.root.mkdir(mode=0o700)
        self.now = 1000.0
        self.c = config(self.root)
        self.trace = (self.root / 'SQL-TRACE.txt').open('x')

    def tearDown(self):
        self.trace.flush()
        CASES.append({'case': self._testMethodName, 'seconds': time.monotonic() - self.started})

    def store(self):
        validate_config(self.c)
        s = Store(self.c, controller='FICTIONAL-software-controller', clock=lambda: self.now)
        s.execution_pool = FictionalPool()
        s.db.set_trace_callback(lambda sql: self.trace.write(sql + '\n'))
        STORES.append(s)
        for role in ROLES:
            s.enroll(role, {'owner': OWNERS[role], 'actor': ACTOR, 'id': 'FICTIONAL-grant-' + role, 'cutover': 0})
            s.reconcile_legacy(role, OWNERS[role], {'collector': 'FICTIONAL', 'evidence': 'software fixture', 'remaining_holds': []})
        return s

    def event(self, s, role='Work', task='work-proposer', package=None):
        self.now += 1
        event = {'id': 'FICTIONAL-event-' + str(s.one('SELECT COUNT(*) AS n FROM events')['n'] + 1),
            'role': role, 'recipient': OWNERS[role], 'kind': 'board', 'allowed_tasks': s.config['roles'][role]['routes'],
            'body': {'meaning': 'FICTIONAL software task'}, 'package': package, 'notice': None, 'post': int(self.now), 'grant': None}
        s.ingest(event, cursor=event['post'])
        self.classify(s, event['id'], task)
        return event['id']

    def classify(self, s, event, task):
        claimed = s.claim_classification()
        self.assertIsNotNone(claimed)
        attempt, source = claimed
        self.assertEqual(source['id'], event)
        with self.assertRaises(Refusal):
            s.ack_state(event, 'done', {'FICTIONAL': 'before classification'})
        s.begin(attempt, {'fixture': 'FICTIONAL no model/session'})
        s.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
            'result': {'event_id': event, 'task': task, 'package': source.get('package'), 'reason': 'FICTIONAL meaning-based selection'}})
        s.commit_classification(attempt)
        s.ack_state(event, 'internal' if source['kind'] != 'board' else 'plain', {'FICTIONAL': 'receipt only'})
        self.assertIsNone(s.one('SELECT processed_at FROM events WHERE id=?', (event,))['processed_at'])

    def reserve(self, s, name):
        with s.tx():
            q = s.one("SELECT * FROM queue WHERE task=? AND state='queued' ORDER BY rowid", (name,))
            return s._reserve_candidate(q) if q else None

    def result(self, category='complete', artifacts=None):
        return {'semantic': 'DONE', 'category': category, 'summary': 'FICTIONAL complete bounded task',
            'findings': [], 'failures': [], 'unknowns': [], 'artifacts': artifacts or [], 'handoffs': [],
            'no_handoff_reason': 'FICTIONAL owner report and configured response are the necessary returns',
            'completion': {'version': 1, 'local': 'ready', 'failures': [], 'unknowns': [], 'tools': []}}

    def collect(self, s, job, category='complete', artifacts=None):
        attempt = s.start_job(job['id'], job['token'])
        directory = s.home / 'artifacts' / attempt
        directory.mkdir(parents=True, mode=0o700)
        s.begin(attempt, {'fixture': 'FICTIONAL no process/session'})
        answer = self.result(category, artifacts)
        s.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created', 'result': answer,
            'detail': {'resume_disposition': 'FICTIONAL no native session', 'tool_completion': {'complete': True,
                'nonzero_completions': 0, 'items': [{'id': 'FICTIONAL-protocol-item', 'type': 'commandExecution',
                    'exit_code': 0, 'status': 'completed', 'completed_notification': True}]}}})
        return attempt

    def settle(self, s, job):
        for row in s.rows("SELECT id FROM events WHERE classification IS NULL ORDER BY received,id"):
            event = s.event(row['id'])
            self.classify(s, row['id'], event['allowed_tasks'][0])
        for row in s.rows('SELECT * FROM outboxes WHERE job=?', (job['id'],)):
            s.delivery_observed(row['id'], {'id': row['id'], 'state': 'settled', 'recipient': OWNERS[row['recipient']],
                'processed_at': self.now, 'processing': {'FICTIONAL': 'substantive consumer processing'},
                'settlement': {'FICTIONAL': 'settled'}, 'control_receipt': {'pending': False}})

    def finish(self, s, job, category='complete', reconcile=True):
        attempt = self.collect(s, job, category)
        if reconcile and s.config['tasks'][job['task']]['effects'] == 'owner-reconcile':
            s.reconcile_effects(job['id'], job['token'], OWNERS[job['role']], {'evidence': 'FICTIONAL effects reconciled', 'unknown_effects': []})
        s.finish_job(job['id'], job['token'])
        self.settle(s, job)
        s.finish_job(job['id'], job['token'])
        return attempt

    def advance(self, s):
        with s.tx():
            basis = windows.basis(s)
        return windows.advance(s, OWNERS['Work'], {'basis': basis, 'target': 'FICTIONAL next window',
            'reason': 'continuing real shapes without terminal substitution', 'evidence': 'FICTIONAL Work boundary review',
            'custody': {r: {'owner': OWNERS[r], 'evidence': 'FICTIONAL unchanged original duties and holds retained'} for r in ROLES}})

    def admit(self, s, package, accepted=True):
        s.admit(package, OWNERS['Branch'], {'FICTIONAL': 'Branch package/resource scope', 'task_scopes': {
            name: {'cwd': str(self.root), 'read_roots': [str(self.root)], 'write_roots': [str(self.root)],
                   'procedure': 'FICTIONAL', 'resource_evidence': 'FICTIONAL'} for name in ('qa-execution', 'branch-integrator')}},
            accepted={'FICTIONAL': 'independent accepted fixture package'} if accepted else None)

    def test_actual_eight_shapes_and_mixed_role_before_ack(self):
        s = self.store()
        for role in ROLES:
            event = self.event(s, role, 'work-proposer')
            q = s.one('SELECT * FROM queue WHERE event=?', (event,))
            self.assertEqual(q['role'], 'Work')
            self.assertIsNone(s.one('SELECT processed_at FROM events WHERE id=?', (event,))['processed_at'])
        self.assertEqual(s.one("SELECT COUNT(*) AS n FROM attempts WHERE kind='classifier'")['n'], 4)
        bad = json.loads(json.dumps(self.c)); bad['window_service']['tasks'].pop()
        with self.assertRaises(Refusal):
            validate_config(bad)

    def test_two_successive_batched_windows_and_real_fixture_publication(self):
        s = self.store()
        target = self.root / 'fictional-work.json'
        target.write_text('{"FICTIONAL":"before"}')
        inode = target.stat().st_ino
        class Board:
            def completion_authority(_, store, task):
                return {'id': 'FICTIONAL-grant-Work', 'issued_by': OWNERS['Work'], 'owner': OWNERS['Work'], 'authority': 'FICTIONAL fixture only'}
        with patch.object(publication, 'snapshot_lock', lambda store: contextlib.nullcontext()):
            for window in (1, 2):
                for _ in range(2):
                    self.event(s)
                for _ in range(2):
                    job = self.reserve(s, 'work-proposer')
                    self.finish(s, job, 'proposal')
                job = self.reserve(s, 'work-integrator')
                self.assertEqual(len(json.loads(job['members'])), 2)
                self.assertIsNone(self.reserve(s, 'work-integrator'))
                attempt = s.start_job(job['id'], job['token'])
                directory = s.home / 'artifacts' / attempt
                directory.mkdir(parents=True, mode=0o700)
                routine.prepare(s, Board(), job, attempt, self.c['tasks']['work-integrator'])
                stage = Path(publication.stages(s, attempt)[str(target)])
                stage.write_text(json.dumps({'FICTIONAL': window}))
                s.begin(attempt, {'fixture': 'FICTIONAL no native model'})
                s.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
                    'result': self.result(artifacts=[str(stage)]), 'detail': {'tool_completion': {'complete': True,
                        'items': [{'id': 'FICTIONAL-write', 'type': 'commandExecution', 'exit_code': 0,
                            'completed_notification': True, 'status': 'completed'}]}}})
                custody.capture(s, attempt, str(stage), self.c['tasks']['work-integrator'])
                self.assertTrue(routine.reconcile(s, Board(), s.job(job['id'])))
                s.finish_job(job['id'], job['token']); self.settle(s, job); s.finish_job(job['id'], job['token'])
                self.assertEqual(s.job(job['id'])['state'], 'closed')
                self.assertEqual(target.stat().st_ino, inode)
                self.assertEqual(json.loads(target.read_text())['FICTIONAL'], window)
                if window == 1:
                    self.assertEqual(self.advance(s)['window'], 2)
            self.assertEqual(s.one('SELECT COUNT(*) AS n FROM canonical_backups')['n'], 2)
            self.assertEqual(s.one('SELECT COUNT(*) AS n FROM jobs')['n'], 6)
            self.assertTrue(windows.basis(s)['journal_sha256'])  # Includes actual BLOB custody.

    def test_branch_reviews_owner_and_qa_response_cycles(self):
        s = self.store(); self.admit(s, 'FICTIONAL-P')
        self.event(s, 'Branch', 'branch-proposer', 'FICTIONAL-P')
        self.finish(s, self.reserve(s, 'branch-proposer'), 'proposal')
        self.finish(s, self.reserve(s, 'branch-integrator'))
        self.event(s, 'Reviews', 'reviews-proposer')
        job = self.reserve(s, 'reviews-proposer')
        s.delegate_owner_job(job['id'])
        self.assertEqual(s.job(job['id'])['state'], 'awaiting-owner')
        out = s.one("SELECT * FROM outboxes WHERE job=? AND kind='work'", (job['id'],))
        receipt = {'id': out['id'], 'state': 'settled', 'recipient': OWNERS['Reviews'], 'processed_at': self.now,
            'control_receipt': {'pending': False}, 'settlement': {'result': self.result('consolidated'),
                'actual_originals': [{'collector': OWNERS['Reviews'], 'actual_end': 0, 'reference': 'FICTIONAL modelled original, no native process'}],
                'method_pin': 'FICTIONAL method', 'coverage_frontier': 'FICTIONAL complete selected fixture scope',
                'effects': {'evidence': 'FICTIONAL no remaining report effects', 'unknown_effects': []}}}
        s.delivery_observed(out['id'], receipt)
        response = s.job(job['id'])['response']; self.classify(s, response, 'reviews-integrator')
        self.finish(s, self.reserve(s, 'reviews-integrator'), 'consolidated')
        self.event(s, 'QA', 'qa-execution', 'FICTIONAL-P')
        self.finish(s, self.reserve(s, 'qa-execution'), 'consolidated')
        self.finish(s, self.reserve(s, 'qa-cleanup'), 'qualification')
        self.assertEqual(s.one("SELECT COUNT(*) AS n FROM jobs WHERE role='QA' AND state='closed'")['n'], 2)
        self.assertTrue(s.one("SELECT id FROM queue WHERE task='branch-proposer' AND state='queued'"))
        self.assertEqual({r['task'] for r in s.rows('SELECT task FROM jobs')}, set(TASKS) - {'work-proposer', 'work-integrator'})

    def test_qa_five_separate_packages_then_one_cleanup(self):
        s = self.store()
        for i in range(6):
            package = 'FICTIONAL-Q' + str(i); self.admit(s, package)
            self.event(s, 'QA', 'qa-execution', package)
        jobs = [self.reserve(s, 'qa-execution') for _ in range(5)]
        self.assertTrue(all(jobs)); self.assertIsNone(self.reserve(s, 'qa-execution'))
        self.assertTrue(all(len(json.loads(j['members'])) == 1 for j in jobs))
        self.event(s, 'QA', 'qa-cleanup', 'FICTIONAL-Q0')
        self.assertIsNone(self.reserve(s, 'qa-cleanup'))

    def test_window_pressure_rollback_no_ack_recycling_and_conserved_prestart(self):
        self.c['window_service']['max_new_inputs'] = 1
        s = self.store(); event = self.event(s)
        job = self.reserve(s, 'work-proposer')
        before = s.rows('SELECT * FROM events')
        next_event = {**s.event(event), 'id': 'FICTIONAL-next', 'post': 9999}
        with self.assertRaises(Backpressure): s.ingest(next_event, cursor=9999)
        self.assertEqual(s.rows('SELECT * FROM events'), before)
        self.assertNotEqual(s.one("SELECT seq FROM cursors WHERE role='Work'")['seq'], 9999)
        s.set_hold(event, 'FICTIONAL stale prestart source')
        self.advance(s)
        self.assertEqual(s.job(job['id'])['state'], 'reserved')
        self.assertIsNone(s.job(job['id'])['active_attempt'])
        self.assertEqual(s.one('SELECT hold FROM events WHERE id=?', (event,))['hold'], 'FICTIONAL stale prestart source')
        s.ingest(next_event)
        self.assertEqual(s.one('SELECT COUNT(*) AS n FROM events')['n'], 2)

    def test_historical_counts_and_owner_decisions_continue_by_boundary(self):
        self.c['limits']['max_jobs'] = 1
        s = self.store()
        for _ in range(3):
            self.event(s, 'Branch', 'branch-proposer')
            self.finish(s, self.reserve(s, 'branch-proposer'))
            self.advance(s)
        self.assertEqual(s.one('SELECT COUNT(*) AS n FROM jobs')['n'], 3)
        self.assertEqual(s.one('SELECT COUNT(*) AS n FROM service_windows')['n'], 4)
        event = self.event(s)
        for i in range(6):
            s.resolve_input(event, OWNERS['Work'], {'source_hash': digest(s.event(event)), 'mode': 'route',
                'task': 'work-proposer', 'package': None, 'related_event': None, 'related_job': None,
                'reason': 'FICTIONAL corrected meaning ' + str(i), 'evidence': ['FICTIONAL owner source'],
                'remaining_obligations': ['FICTIONAL still unresolved']})
        self.assertEqual(s.input_resolution(event)['version'], 6)

    def test_stale_integrator_boundary_keeps_one_slot_and_pending_members(self):
        s = self.store()
        first = self.event(s, 'Work', 'work-integrator')
        reserved = self.reserve(s, 'work-integrator')
        second = self.event(s, 'Work', 'work-integrator')
        s.set_hold(first, 'FICTIONAL stale prestart source; lifecycle75 owns disposition')
        before = s.job(reserved['id'])
        self.advance(s)
        self.assertEqual(s.job(reserved['id']), before)
        self.assertIsNone(self.reserve(s, 'work-integrator'))
        self.assertEqual(s.one('SELECT state FROM queue WHERE event=?', (second,))['state'], 'queued')
        self.assertIsNone(s.one('SELECT processed_at FROM events WHERE id=?', (first,))['processed_at'])

    def test_stale_boundary_and_unknown_effects_refuse(self):
        s = self.store(); self.event(s, 'Branch', 'branch-integrator', 'FICTIONAL-no-admission')
        self.assertIsNone(self.reserve(s, 'branch-integrator'))
        self.admit(s, 'FICTIONAL-no-admission')
        job = self.reserve(s, 'branch-integrator'); self.collect(s, job)
        s.finish_job(job['id'], job['token'])
        self.assertEqual(s.job(job['id'])['effects'], 'unknown')
        self.assertEqual(s.job(job['id'])['state'], 'held')
        with s.tx(): basis = windows.basis(s)
        s.set_hold(json.loads(job['members'])[0]['event'], 'FICTIONAL hold')
        with self.assertRaises(Refusal):
            windows.advance(s, OWNERS['Work'], {'basis': basis, 'target': 'FICTIONAL', 'reason': 'FICTIONAL',
                'evidence': 'FICTIONAL', 'custody': {r: {'owner': OWNERS[r], 'evidence': 'FICTIONAL'} for r in ROLES}})
        self.advance(s)
        self.assertEqual(s.job(job['id'])['effects'], 'unknown')
        self.assertEqual(s.job(job['id'])['state'], 'held')

    def test_exact_alert_debt_repeated_cadences_and_no_violation(self):
        self.c['limits']['max_alerts'] = 1
        s = self.store()
        self.assertEqual(capacity.capture(s), [])
        for kind in self.c['alert_cadences']:
            s.record_operational_error('FICTIONAL-' + kind, {'FICTIONAL': 'unchanged violation'}, kind=kind)
        self.now += 300
        self.assertEqual(capacity.capture(s), [])  # Atomic cohort, exact debt retained.
        debt = s.rows('SELECT * FROM alert_debt'); self.assertEqual(len(debt), 3)
        self.now += 300; capacity.capture(s)
        self.assertEqual(s.one('SELECT (SELECT COUNT(*) FROM alert_debt)+(SELECT COUNT(*) FROM alerts) AS n')['n'], 4)
        self.now += 3600; capacity.capture(s)
        kinds = [r['kind'] for r in s.rows('SELECT kind FROM alert_debt UNION ALL SELECT kind FROM alerts')]
        self.assertEqual(kinds.count('acceptance-request'), 1)
        self.assertEqual(kinds.count('stale-branch-worktree'), 2)
        self.assertEqual(kinds.count('root-capacity'), 3)
        self.assertEqual(s.rows('SELECT * FROM alert_debt')[:3], debt)
        self.now += 86400; capacity.capture(s)
        self.assertEqual(s.one("SELECT COUNT(*) AS n FROM alert_debt WHERE kind='acceptance-request'")['n'], 2)
        self.assertTrue(capacity.service(s)['gap_since'])

    def alerts(self, s, n):
        for i in range(n):
            with s.tx():
                identity = 'FICTIONAL-alert-' + str(i)
                s.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)', (identity, identity, 'FICTIONAL-held', self.now, encode({'id': identity})))
                s._outbox('Work', 'Work', 'alert', {'id': identity}, alert=identity)

    def worker(self, mode='held', timeout=.3):
        # Inspected source; only /fixtures inputs/output and process-local time.
        body = """import json,sys,time,pathlib,os
r=json.load(sys.stdin)
p=pathlib.Path(sys.argv[2]);p.mkdir(exist_ok=True)
(p/(r['visit']+'.intent.json')).write_text(json.dumps(r))
mode=sys.argv[1]
if mode=='timeout': time.sleep(3)
if mode=='invalid': print('{"unbound":true}',flush=True);sys.exit(0)
a={k:r[k] for k in ('visit','owner','basis')}
a.update(status='held',effect_state='not-attempted',intent_reference=str(p/(r['visit']+'.intent.json')),result_reference=str(p/(r['visit']+'.result.json')))
(p/(r['visit']+'.result.json')).write_text(json.dumps(a))
print(json.dumps(a),flush=True)
"""
        path = self.root / 'FICTIONAL-worker.py'; path.write_text(body)
        self.c['custodian_service'] = {'Work': {'argv': [sys.executable, str(path), mode, str(self.root / 'owner-evidence')],
            'authority': 'FICTIONAL owner qualified software worker only', 'timeout_seconds': timeout}}

    def test_recurring_worker_fair_held_prefix_and_cli_wiring(self):
        self.worker(); s = self.store(); self.alerts(s, 20)
        class Board:
            def verify_authority(_, store): pass  # FICTIONAL existing grant assertion only.
        async def run():
            d = Dispatcher(s, models=object(), boards={'Work': Board()})
            d.custodian_progress(); await d.custodian_service.close()
            d.custodian_progress(); await d.custodian_service.close()
            visits = s.rows('SELECT * FROM custodian_visits ORDER BY rowid')
            self.assertEqual([v['occurrence'] for v in visits], ['FICTIONAL-alert-0', 'FICTIONAL-alert-16'])
            self.assertTrue(all(v['pid'] and v['numeric_end'] == 0 and v['state'] == 'held' for v in visits))
            self.assertEqual(s.one('SELECT COUNT(*) AS n FROM alerts')['n'], 20)
        asyncio.run(run())
        self.assertIn('window-basis', cli.parser()._subparsers._group_actions[0].choices)

    def test_worker_timeout_is_responsive_collected_and_not_replayed(self):
        self.worker('timeout', .2); s = self.store(); self.alerts(s, 1)
        async def run():
            service = Service(s, lambda roles: None)  # FICTIONAL grants only.
            service.schedule()
            beats = 0
            while not all(t.done() for t in service.active.values()):
                await asyncio.sleep(.01); beats += 1
            await service.close()
            self.assertGreater(beats, 5)
            visit = s.one('SELECT * FROM custodian_visits')
            self.assertIsInstance(visit['numeric_end'], int)
            self.assertEqual(visit['state'], 'unknown')
            self.now += 100
            service.schedule(); await service.close()
            self.assertEqual(s.one('SELECT COUNT(*) AS n FROM custodian_visits')['n'], 1)
            restarted = Service(s, lambda roles: None)
            restarted.schedule(); await restarted.close()
            self.assertEqual(s.one('SELECT COUNT(*) AS n FROM custodian_visits')['n'], 1)
            self.assertIsNone(s.one('SELECT processed_at FROM alerts')['processed_at'])
        asyncio.run(run())

    def test_unbound_worker_result_and_missing_owner_are_held(self):
        self.worker('invalid'); s = self.store(); self.alerts(s, 1)
        async def run():
            service = Service(s, lambda roles: None)
            service.schedule(); await service.close()
            self.assertEqual(s.one('SELECT state FROM custodian_visits')['state'], 'unknown')
            self.assertEqual(s.one('SELECT numeric_end FROM custodian_visits')['numeric_end'], 0)
        asyncio.run(run())

    def test_processing_age_all_holds_and_intent_result_failure_custody(self):
        from coordinator_runtime.progress import OwnerAlertCustodian
        s = self.store(); self.alerts(s, 2)
        receipts = {}
        for out in s.rows('SELECT * FROM outboxes'):
            receipts[out['alert']] = {'id': out['id'], 'state': 'settled', 'recipient': OWNERS['Work'],
                'processed_at': self.now, 'processing': {'FICTIONAL': 'actual modelled consumer processing'},
                'settlement': {'FICTIONAL': 'settled'}, 'control_receipt': {'pending': False},
                'transport': {'route': 'FICTIONAL', 'delivery_state': 'acknowledged'}}
            s.delivery_observed(out['id'], receipts[out['alert']])
        held = None; sink_mode = None; originals = []
        def qualify(store, alert, outbox, basis):
            return {'basis': basis, 'holds': {name: ['FICTIONAL held'] if name == held else [] for name in capacity.HOLDS},
                    'evidence': 'FICTIONAL full custodian qualification', 'qualified_at': self.now}
        def sink(record):
            originals.append(record)
            (self.root / ('BEFORE-AND-RESULT-' + str(len(originals)) + '.json')).write_text(encode(record))
            if sink_mode == 'intent' and 'retirement_intent' in record: raise OSError('FICTIONAL intent sink failure')
            if sink_mode == 'result' and 'retirement_result' in record: raise OSError('FICTIONAL result sink failure after effect')
            return 'FICTIONAL-durable-original-' + str(len(originals))
        class Board:
            def retire_alert(_, store, occurrence, receipt):
                return capacity.retire(store, occurrence, OWNERS['Work'], receipt, receipts[occurrence])
        adapter = OwnerAlertCustodian(Board(), qualify, sink)
        with self.assertRaises(Refusal): adapter.progress_alert(s, 'FICTIONAL-alert-0')
        self.now += 86401
        for name in capacity.HOLDS:
            held = name
            with self.assertRaises(Refusal): adapter.progress_alert(s, 'FICTIONAL-alert-0')
        held = None; sink_mode = 'intent'
        with self.assertRaises(OSError): adapter.progress_alert(s, 'FICTIONAL-alert-0')
        self.assertIsNotNone(s.one("SELECT id FROM alerts WHERE id='FICTIONAL-alert-0'"))
        sink_mode = 'result'
        with self.assertRaises(OSError): adapter.progress_alert(s, 'FICTIONAL-alert-0')
        self.assertIsNone(s.one("SELECT id FROM alerts WHERE id='FICTIONAL-alert-0'"))
        self.assertTrue(any('retirement_intent' in row for row in originals))
        sink_mode = None
        result = adapter.progress_alert(s, 'FICTIONAL-alert-1')
        self.assertEqual(result['retired_alert'], 'FICTIONAL-alert-1')

    def test_failed_execution_keeps_owner_recovery_beyond_four_corrections(self):
        s = self.store(); event = self.event(s, 'Branch', 'branch-proposer')
        job = self.reserve(s, 'branch-proposer'); attempt = s.start_job(job['id'], job['token'])
        s.begin(attempt, {'fixture': 'FICTIONAL original execution'})
        answer = self.result('blocker'); answer.update(semantic='PARTIAL', unknowns=['FICTIONAL uncompleted local work'])
        s.collect(attempt, {'exit': 7, 'result': answer, 'capture': 'complete', 'cleanup': 'no-session-created',
                           'detail': {'resume_disposition': 'FICTIONAL resume unavailable'}})
        s.finish_job(job['id'], job['token'])
        self.assertEqual(s.job(job['id'])['state'], 'held')
        for i in range(6):
            request = s.request_recovery(job['id'], job['token'], attempt, OWNERS['Branch'],
                {'mode': 'defer', 'reason': 'FICTIONAL owner unresolved choice ' + str(i),
                 'evidence': ['FICTIONAL owner original custody'], 'remaining': None})
            s.consume_recovery_request(request['id'])
        self.assertEqual(s.one('SELECT COUNT(*) AS n FROM recovery_requests')['n'], 6)
        self.assertEqual(s.job(job['id'])['active_attempt'], attempt)
        self.assertIsNone(s.one('SELECT processed_at FROM events WHERE id=?', (event,))['processed_at'])
        self.assertEqual(json.loads(s.attempt(attempt)['result'])['unknowns'], answer['unknowns'])


def main():
    global ARGS
    p = argparse.ArgumentParser()
    p.add_argument('--fixtures', required=True, type=Path)
    p.add_argument('--kernel-ro', action='store_true')
    ARGS = p.parse_args()
    assert ARGS.fixtures.is_absolute()
    if ARGS.kernel_ro:
        assert os.statvfs(ROOT).f_flag & os.ST_RDONLY
        assert os.statvfs('/usr').f_flag & os.ST_RDONLY
        assert socket.if_nameindex() == [(1, 'lo')]
        try:
            (ROOT / 'FORBIDDEN-source-write').write_text('must fail before import')
        except OSError as exc:
            assert exc.errno == errno.EROFS
        else:
            raise AssertionError('source write unexpectedly allowed')
        print(json.dumps({'pre_import_kernel': 'source/controllers/dependencies RO; private devtmp; isolated PID+network',
                          'namespace_pid': os.getpid()}), flush=True)
    imports()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    report = {'cases': CASES, 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'maxrss_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'fixture_boundary': 'FICTIONAL owners/grants/consumer receipts/models and effect evidence; real imported Store and own SQLite/files/worker handles',
        'retention': 'all fixture files/SQL traces/worker originals retained, no cleanup or native identity assignment'}
    (ARGS.fixtures / 'RESULT.json').write_text(json.dumps(report, indent=2))
    for store in STORES:
        store.db.execute('PRAGMA wal_checkpoint(FULL)')
    print(json.dumps(report), flush=True)
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
