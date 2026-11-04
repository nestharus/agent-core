"""Finite combined journal boundaries; explicit own fixtures and kernel RO required.

No native identity is assigned. The fixture uses Store methods without its
constructor, literal production schemas with only profile NOT NULL relaxed,
NULL profile allocation, and fictional authority/closure/clocks. No pool opens.
This is neither full Store initialization nor operating qualification.
"""
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coordinator_runtime import cli, store, windows
from coordinator_runtime.contracts import Refusal, encode
from coordinator_runtime.dispatcher import job_prompt


class NullAllocation:
    def allocate(self):
        return {'profile': None, 'fictional_no_native_identity': True}


class Fixture(store.Store):
    def __init__(self, root, recurring=True):
        check_headroom(root.name)
        self.home = root
        root.mkdir()
        self.path = root / 'fictional.sqlite'
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=PERSIST')
        self.db.execute('PRAGMA synchronous=FULL')
        schemas = [store.SCHEMA, store.DELIVERY_SCHEMA, store.CUSTODY_SCHEMA,
                   store.ROUTINE_SCHEMA, store.STORAGE_SCHEMA, store.PUBLICATION_SCHEMA,
                   store.RECOVERY_SCHEMA, store.INPUT_SCHEMA, store.INTEGRATION_SCHEMA]
        schemas += [m.SCHEMA for m in (store.prospective, store.ordinary, store.capacity,
                                       store.admitted, store.windows, store.custodian_service)]
        self.db.executescript(''.join(schemas).replace('profile TEXT NOT NULL', 'profile TEXT'))
        self.trace = (root / 'trace.sql').open('x')
        self.db.set_trace_callback(lambda sql: self.trace.write(sql + '\n'))
        self.controller = 'fictional-controller'
        self.clock = lambda: 100.0
        self.launch_authorizer = self.task_launch_authorizer = None
        self.execution_pool = NullAllocation()
        self.config = {'actor': 'fictional-producer', 'profiles': [None],
                       'state_dir': str(root), 'deadlines': {'bind': 2},
                       'limits': {'max_bytes': 8*1024*1024, 'max_files': 1000,
                                  'max_events': 100, 'max_jobs': 32, 'max_attempts': 100,
                                  'max_alerts': 16, 'max_result_bytes': 2*1024*1024},
                       'diagnosis': {'binding': {}, 'profile': None}, 'roles': {}, 'tasks': {}}
        for role in ('Work', 'Branch', 'Reviews', 'QA'):
            phases = ('execution', 'cleanup') if role == 'QA' else ('proposer', 'integrator')
            names = [role + '-' + phase for phase in phases]
            self.config['roles'][role] = {'owner': 'fictional-' + role, 'routes': names}
            self.insert('enrollments', {'role': role, 'owner': 'fictional-' + role,
                                       'profile': None, 'grant_id': 'fictional-grant', 'cutover': 0, 'intake': 1})
            for name, phase in zip(names, phases):
                self.config['tasks'][name] = {'role': role, 'phase': phase, 'binding': {},
                                             'profile': None, 'templates': [], 'purpose': 'fictional purpose',
                                             'authority': 'fictional software only', 'effect_authority': {},
                                             'effects': 'owner-reconcile'}
        if recurring:
            self.config['window_service'] = {'tasks': list(self.config['tasks']),
                                             'max_new_inputs': 100, 'max_decisions': 32, 'batch_size': 2}
            with self.tx():
                windows.initialize(self)

    def insert(self, table, values):
        self.db.execute('INSERT INTO ' + table + '(' + ','.join(values) + ') VALUES(' +
                        ','.join('?' for _ in values) + ')', tuple(values.values()))

    def add(self, event, task='Work-integrator', package=None):
        role, phase = task.split('-')
        self.insert('events', {'id': event, 'role': role, 'payload': encode({'id': event}),
                               'hash': event, 'received': 10, 'state': 'queued', 'ack': 'done'})
        self.insert('queue', {'id': event + '-q', 'event': event, 'role': role,
                              'phase': phase, 'task': task, 'package': package})

    def snapshot(self, label):
        check_headroom(label)
        image = {r['name']: self.rows('SELECT * FROM ' + r['name'] + ' ORDER BY rowid')
                 for r in self.rows("SELECT name FROM sqlite_master WHERE type='table'")}
        (self.home / (label + '.json')).write_text(encode(image))
        return image

    def old_debt(self):
        self.add('old-input')
        row = self.one("SELECT * FROM queue WHERE event='old-input'")
        self.insert('jobs', {'id': 'old', 'role': 'Work', 'phase': 'integrator', 'task': 'Work-integrator',
                             'members': encode([self._input_member(row)]), 'controller': self.controller,
                             'token': 'old-token', 'created': 1, 'state': 'held', 'active_attempt': 'old-a',
                             'effects': 'unknown', 'hold_reason': 'fictional adverse original'})
        self.db.execute("UPDATE queue SET state='reserved',job='old' WHERE event='old-input'")
        self.insert('attempts', {'id': 'old-a', 'kind': 'task', 'job': 'old', 'controller': self.controller,
                                 'profile': None, 'binding': '{}', 'created': 1, 'begin': 2, 'ended': 3,
                                 'exit': 7, 'collected': 4, 'state': 'collected', 'semantic': 'PARTIAL'})
        self.insert('outboxes', {'id': 'old-outbox', 'role': 'Work', 'job': 'old', 'event': 'old-input',
                                 'producer': 'fictional-producer', 'recipient': 'Work', 'kind': 'question',
                                 'required': 'settled', 'payload': '{}', 'state': 'sent', 'created': 5})
        self.insert('file_publications', {'attempt': 'old-a', 'target': 'fictional-target',
                                          'state': 'intent', 'error': 'UNKNOWN'})
        basis = self.integration_closure_basis('old', 'old-token')
        self.retire_integration('old', 'old-token', 'fictional-Work', {'basis': basis,
            'reason': 'fictional closed execution; all semantic duties held', 'controllers': [
                {'controller': c, 'collector': 'fictional-collector', 'end': 7, 'collected': True,
                 'writers_closed': True, 'evidence': ['fictional scoped closure premise']}
                for c in basis['controllers']]})

    def select(self, events):
        return self.select_integration_window('fictional-Work', {
            'basis': self.integration_window_basis('Work-integrator', events),
            'target': 'TARGET158 selected exact scope', 'why': 'WHY158 continuing coordination',
            'conflict_evidence': ['fictional peer-safe scope'],
            'custodian_evidence': ['fictional retained original duties']})

    def close(self):
        self.snapshot('final')
        self.db.close()
        self.trace.close()


class Controls(unittest.TestCase):
    def fixture(self, label, recurring=True):
        s = Fixture(ROOT / label, recurring)
        self.addCleanup(s.close)
        return s

    def refused(self, s, fn):
        before = s.snapshot('before-refusal')
        with self.assertRaises(Refusal):
            fn()
        self.assertEqual(before, s.snapshot('after-refusal'))

    def test_selected_no_start_with_recurring_accounts(self):
        s = self.fixture('no-start')
        s.old_debt()
        for event in ('a', 'b', 'c'):
            s.add(event)
        self.refused(s, lambda: s.select(['a', 'b', 'c']))
        selected = s.select(['a'])
        job = s.reserve()
        attempt = s.start_job(job['id'], job['token'])
        self.refused(s, lambda: s.integration_no_start_basis(job['id'], job['token']))
        s.db.execute("UPDATE outboxes SET error='fictional later UNKNOWN' WHERE id='old-outbox'")
        self.refused(s, lambda: s.authorize_launch(attempt))
        s.collect(attempt, {'exit': None, 'result': None, 'error': 'fictional no process creation',
            'capture': 'not-started', 'cleanup': 'no-session-created',
            'detail': {'known_not_started': True, 'resume_disposition': 'fictional original collected no-start'}})
        s.hold_job(job['id'], 'fictional retained duty')
        s.insert('file_publications', {'attempt': attempt, 'target': 'fictional-unresolved', 'state': 'intent'})
        basis = s.integration_no_start_basis(job['id'], job['token'])
        receipt = {'basis': basis, 'reason': 'fictional successor needed', 'controllers': [
            {'controller': c, 'collector': 'fictional-collector', 'writers_closed': True, 'no_launch': True,
             'evidence': ['fictional affirmative scoped no-launch premise']} for c in basis['controllers']]}
        before = s.snapshot('before-withdrawal')
        s.withdraw_integration_no_start(job['id'], job['token'], 'fictional-Work', receipt)
        after = s.snapshot('after-withdrawal')
        for table in before:
            if table not in {'jobs', 'queue', 'integration_prestart_dispositions'}:
                self.assertEqual(before[table], after[table], table)
        self.assertEqual(selected['receipt'], s.one('SELECT receipt FROM integration_windows WHERE job=?', (job['id'],))['receipt'])
        self.assertIsNone(s.reserve())
        s.select(['b', 'a'])
        successor = s.reserve()
        self.assertEqual(['b', 'a'], [m['event'] for m in json.loads(successor['members'])])
        next_attempt = s.start_job(successor['id'], successor['token'])
        s.authorize_launch(next_attempt)
        self.assertIsNone(s.reserve())
        prompt = job_prompt(s, s.job(successor['id']))
        self.assertIn('TARGET158', prompt)
        self.assertIn('WHY158', prompt)
        self.refused(s, lambda: s.authorize_launch(attempt))
        self.assertIsNotNone(s.withdrawn_integration_hold('a'))
        self.assertTrue(all(e['processed_at'] is None for e in s.rows('SELECT * FROM events')))
        self.assertTrue(all(a['profile'] is None and a['session'] is None and a['turn'] is None
                            for a in s.rows('SELECT * FROM attempts')))
        self.assertEqual(2, json.loads(windows.current(s)['used'])['jobs'])
        self.assertEqual(2, json.loads(windows.current(s)['used'])['attempts'])

    def test_eight_forms_per_role_batch_and_qa_capacity(self):
        s = self.fixture('forms')
        for role in ('Work', 'Branch', 'Reviews'):
            s.add(role + '-proposal', role + '-proposer')
            for n in range(3):
                s.add(role + '-input-' + str(n), role + '-integrator')
        for n in range(6):
            package = 'fictional-package-' + str(n)
            s.insert('admissions', {'package': package, 'owner': 'fictional-QA', 'receipt': '{}'})
            s.add('qa-exec-' + str(n), 'QA-execution', package)
        s.add('qa-clean', 'QA-cleanup', 'fictional-package-0')
        s.db.execute("UPDATE events SET received=20 WHERE id='qa-clean'")
        s.db.execute("UPDATE events SET received=30 WHERE id='qa-exec-5'")
        jobs = []
        while (job := s.reserve()) is not None:
            jobs.append(job)
        self.assertEqual(11, len(jobs))
        self.assertEqual(5, sum(j['phase'] == 'execution' for j in jobs))
        for role in ('Work', 'Branch', 'Reviews'):
            batch = next(j for j in jobs if j['role'] == role and j['phase'] == 'integrator')
            self.assertEqual(2, len(json.loads(batch['members'])))
        self.assertEqual(3, len({j['role'] for j in jobs if j['phase'] == 'integrator'}))
        before = s.snapshot('before-renewal')
        result = windows.advance(s, 'fictional-Work', {'basis': windows.basis(s),
            'target': 'fictional continue', 'reason': 'fictional allocations only', 'evidence': 'fictional currentness',
            'custody': {r: {'owner': 'fictional-' + r, 'evidence': 'fictional unchanged custody'}
                        for r in s.config['roles']}})
        self.assertEqual(2, result['window'])
        after = s.snapshot('after-renewal')
        for table in before:
            if table != 'service_windows':
                self.assertEqual(before[table], after[table], table)
        self.assertIsNone(s.reserve())
        # Fictional execution-complete premise; no native END or semantic/effect discharge.
        for j in jobs:
            if j['role'] == 'QA':
                s.db.execute("UPDATE jobs SET state='closed' WHERE id=?", (j['id'],))
        cleanup = s.reserve()
        self.assertEqual('cleanup', cleanup['phase'])
        self.assertIsNone(s.reserve())
        self.assertEqual(8, len({(j['role'], j['phase']) for j in jobs + [cleanup]}))

    def test_initial_no_window_route_remains_excluded(self):
        s = self.fixture('initial')
        s.add('initial')
        job = s.reserve()
        attempt = s.start_job(job['id'], job['token'])
        s.collect(attempt, {'exit': None, 'result': None, 'capture': 'not-started',
            'cleanup': 'no-session-created', 'detail': {'known_not_started': True,
            'resume_disposition': 'fictional explicit no-start collection'}})
        with self.assertRaisesRegex(Refusal, 'exact consumed integration window'):
            s.integration_no_start_basis(job['id'], job['token'])

    def test_cli_both_command_families_keep_authority(self):
        s = self.fixture('cli')
        class DeniedBoard:
            def __init__(self, config, role):
                self.role = role
            def verify_authority(self, target):
                raise Refusal('fictional authority refusal')
        commands = [cli.parser().parse_args(['integration-no-start-basis', 'fictional-job', '--token', 'fictional-token']),
                    cli.parser().parse_args(['window-basis'])]
        with patch.object(cli, 'actual_actor', return_value='fictional-Work'), patch.object(cli, 'Board', DeniedBoard):
            for args in commands:
                with self.assertRaisesRegex(Refusal, 'fictional authority refusal'):
                    cli.operate(args, s)
        class AllowedBoard(DeniedBoard):
            def verify_authority(self, target):
                return None
        with patch.object(cli, 'actual_actor', return_value='fictional-Work'), patch.object(cli, 'Board', AllowedBoard):
            with patch.object(s, 'integration_no_start_basis', return_value={'fictional': 'route'}) as call:
                self.assertEqual({'fictional': 'route'}, cli.operate(commands[0], s))
                call.assert_called_once_with('fictional-job', 'fictional-token')
            self.assertEqual(windows.basis(s), cli.operate(commands[1], s))


def check_headroom(label):
    files = [p for p in ROOT.parent.rglob('*') if p.is_file()]
    used = sum(p.stat().st_size for p in files) + RETAINED['bytes']
    available = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    memory = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                      if line.startswith('MemAvailable:'))) * 1024
    assert used + 8*1024**2 < 128*1024**2 and len(files) + RETAINED['files'] + 150 < 5000
    assert available >= 40*1024**3 and memory >= 4*1024**3
    with (ROOT.parent / 'headroom.jsonl').open('a') as out:
        out.write(encode({'before': label, 'cumulative_bytes': used, 'free': available,
                          'MemAvailable': memory, 'retained_previous': RETAINED}) + '\n')


if __name__ == '__main__':
    ROOT = Path(sys.argv.pop(1))
    RETAINED = json.loads(sys.argv.pop(1))
    if not ROOT.is_absolute() or not ROOT.is_dir() or any(ROOT.iterdir()):
        raise ValueError('explicit fresh owned fixture directory required')
    unittest.main(verbosity=2, failfast=True)
