"""Operation-relative policy tests. All actors, journals, leases and data are fiction.

The real prospective admission writer and resource guard run against an isolated
SQLite journal. Current Work/Board/source authority is an explicit fixture seam;
no native identity, provider, original QA procedure or semantic acceptance runs.
"""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime import processing_admission, resource_scopes as scopes
from coordinator_runtime.contracts import Refusal, digest, encode


WORK = '11111111-1111-4111-8111-111111111111'
QA = '22222222-2222-4222-8222-222222222222'
ACTOR = '33333333-3333-4333-8333-333333333333'


class Journal:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE enrollments(role TEXT, owner TEXT, legacy_hold TEXT);
            CREATE TABLE admissions(package TEXT PRIMARY KEY, owner TEXT, receipt TEXT, expires REAL);
            CREATE TABLE processing_admissions(package TEXT PRIMARY KEY, capability TEXT, event TEXT,
                scope TEXT, receipt TEXT, created REAL);
            CREATE TABLE events(id TEXT, hold TEXT, hash TEXT);
            CREATE TABLE processing_source_positions(event TEXT, position INTEGER);
            CREATE TABLE jobs(id TEXT, role TEXT, task TEXT, package TEXT, effects TEXT, active_attempt TEXT);
            CREATE TABLE job_resource_policies(job TEXT, task TEXT, admission TEXT);
            CREATE TABLE ordinary_resources(resource TEXT, attempt TEXT);
            CREATE TABLE ordinary_runs(attempt TEXT, job TEXT, policy TEXT);
            CREATE TABLE ordinary_acceptance(attempt TEXT, decision TEXT);
        ''')

    def one(self, sql, args=()):
        row = self.db.execute(sql, args).fetchone()
        return dict(row) if row else None

    def rows(self, sql, args=()):
        return [dict(row) for row in self.db.execute(sql, args)]

    def event(self, key):
        return copy.deepcopy(self.source) if key == self.source['id'] else {}

    def budget(self, *args):
        pass

    def clock(self):
        return 1000

    @contextmanager
    def tx(self):
        with self.db:
            yield


class OperationScope(unittest.TestCase):
    def setUp(self):
        self.s = Journal()
        self.addCleanup(self.s.db.close)
        self.hold = 'FICTION retained unknown original activity; prospective resource conflict only'
        self.s.db.execute('INSERT INTO enrollments VALUES(?,?,?)', ('QA', QA, self.hold))
        self.s.db.execute('INSERT INTO enrollments VALUES(?,?,?)', ('Branch', WORK, self.hold))
        self.s.config = {'actor': ACTOR, 'roles': {'Work': {'owner': WORK}, 'QA': {'owner': QA},
                          'Branch': {'owner': WORK}}, 'tasks': {}, 'artifact_exclusions': ['/fixtures/excluded']}
        self.bound = {}
        for name, (role, phase) in scopes.QA_TASKS.items():
            execution = phase == 'execution'
            task = {'role': role, 'phase': phase, 'effects': 'owner-reconcile' if execution else 'none',
                    'require_package_scope': True, 'scope_roots': ['/fixtures/local'], 'network': False,
                    'cwd': '/fixtures/local/repo', 'effect_authority': {'owner': QA if role == 'QA' else WORK,
                    'operations': ['execute-admitted-qa'] if execution else ['read-source', 'consolidate-reports'],
                    'read_roots': ['/fixtures/local/repo'], 'write_roots': ['/fixtures/local/output'] if execution else []}}
            if not execution:
                task['package_narrowing'] = True
            scope = {'cwd': '/fixtures/local/repo' if execution else '/fixtures/local/repo/neutral',
                     'read_roots': ['/fixtures/local/repo'] if execution else ['/fixtures/local/repo/source'],
                     'write_roots': ['/fixtures/local/output'] if execution else [], 'network': False,
                     'procedure': '/fixtures/local/repo/procedure' if execution else '/fixtures/local/repo/source/template',
                     'resource_evidence': ['FICTION original explicitly narrowed access']}
            if name == 'branch-proposer':
                scope['branch_binding'] = 'fiction-original-qa-association'
            self.s.config['tasks'][name] = task
            self.bound[name] = {'policy': copy.deepcopy(task), 'scope': scope}
        p = {'kind': 'local-qa', 'repository': '/fixtures/local/repo', 'git': '/usr/bin/git',
             'git_sha256': 'a'*64, 'source_ref': 'refs/heads/fiction-fixed', 'source_head': 'b'*40,
             'procedure_sha256': 'c'*64, 'resources': [{'key': 'fiction-output', 'owner': WORK,
             'authority': 'FICTION current finite output custody', 'expires': 2000}],
             'acceptor': WORK, 'acceptance_authority': 'FICTION independent acceptance remains required',
             'timeout': 30, 'max_output': 4096, 'known_exits': [0, 1],
             'source_capture': {'bwrap': '/usr/bin/bwrap', 'sha256': 'd'*64, 'max_bytes': 4096, 'max_files': 4}}
        for name in ('command', 'readback'):
            p[name] = {'argv': ['/usr/bin/python3.12', '-B', '/fixtures/local/repo/'+name+'.py'],
                       'executable_sha256': 'e'*64, 'script_sha256': 'f'*64,
                       'stdout': 'FICTION complete\n' if name == 'readback' else ''}
        self.bound['qa-execution']['scope']['ordinary_effects'] = p
        self.s.source = {'id': 'fiction-source', 'role': 'QA', 'kind': 'board', 'post': 2,
                         'package': 'fiction-qa-original', 'author': WORK, 'body': {'topic': 'fiction-exact'},
                         'allowed_tasks': ['qa-execution']}
        self.s.db.execute('INSERT INTO events VALUES(?,?,?)', (self.s.source['id'], None, digest(self.s.source)))
        self.s.db.execute('INSERT INTO processing_source_positions VALUES(?,?)', (self.s.source['id'], 2))
        self.selection = {'tasks': list(scopes.QA_TASKS), 'future_intake': True, 'retained_events': [],
                          'basis': {'event_boundary': 1, 'roles': {'QA': {'future_after': 1}}},
                          'software_admission': {'authority': 'FICTION Work freezes exact prospective scope',
                          'max_packages': 1, 'scopes': {'fiction-exact': {'submitters': [WORK],
                          'package_prefix': 'fiction-qa-', 'task_scopes': {n: b['scope'] for n, b in self.bound.items()},
                          'evidence': 'FICTION original source and independent resource authority'}}}}
        self.cap = {'id': 'fiction-current-cap', 'issuer': WORK}
        self.source_permitted = True
        self.s.processing = SimpleNamespace(current=lambda: (self.cap, self.selection),
            event=lambda event: self.source_permitted,
            boards={'QA': SimpleNamespace(verify_authority=lambda runtime: None)})
        self.record = {'original_hold': self.hold, 'roots': [], 'unbounded': True,
            'evidence': 'FICTION original unknown history remains held', 'operation_observation': {
            'kind': scopes.OBSERVATION_KIND, 'account': {'author': QA, 'reference': 'FICTION public QA account',
            'observed_at': '2026-11-06T22:16:53Z', 'disposition': 'no-positive-current-own-conflict',
            'additional_relevant_roots': []}, 'package': self.s.source['package'],
            'source': {'scope': 'fiction-exact', 'submitter': WORK}, 'tasks': copy.deepcopy(self.bound)}}
        self.selection['service'] = {'legacy_resources': {'QA': self.record}}
        self.row = {'role': 'QA', 'phase': 'execution', 'task': 'qa-execution', 'package': self.s.source['package']}
        # The qualifier is frozen BEFORE real admission. A guessed future
        # event hash is neither needed nor allowed as selection authority.
        scopes.validate(self.s, {'QA': self.record})
        self.assertTrue(self.blocked())
        admitted = processing_admission.admit(self.s, self.s.source['id'])
        self.assertFalse(admitted['acceptance_inferred'])
        self.assertFalse(admitted['native_owner_consent'])

    def blocked(self, row=None):
        return scopes.blocked(self.s, row or self.row)

    def admission(self):
        return self.s.one('SELECT * FROM admissions WHERE package=?', (self.row['package'],))

    def change_receipt(self, change):
        admission = self.admission()
        receipt = json.loads(admission['receipt'])
        change(receipt)
        self.s.db.execute('UPDATE admissions SET receipt=?', (encode(receipt),))

    def owner(self, same=True, frozen=True, role='Branch', effects='unknown'):
        self.s.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)',
            ('other', role, 'qa-execution', 'fiction-prior-package', effects, 'prior-attempt'))
        if frozen:
            bound = copy.deepcopy(self.bound['qa-execution'])
            if not same:
                bound = json.loads(encode(bound).replace('/fixtures/local/', '/fixtures/disjoint/'))
                bound['policy']['scope_roots'] = ['/fixtures/disjoint']
            bound['scope']['ordinary_effects']['resources'][0]['key'] = 'fiction-prior-output'
            admission = {'receipt': encode({'task_scopes': {'qa-execution': bound['scope']}})}
            self.s.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',
                             ('other', encode(bound['policy']), encode(admission)))
            return bound

    def test_matching_operation_and_separate_cleanup_preserve_all_old_debt(self):
        before = self.s.rows('SELECT * FROM enrollments')
        scopes.validate(self.s, {'QA': self.record})
        self.assertFalse(self.blocked())
        self.assertFalse(self.blocked({**self.row, 'phase': 'cleanup', 'task': 'qa-cleanup'}))
        self.assertEqual(self.s.rows('SELECT * FROM enrollments'), before)
        self.assertEqual((self.record['roots'], self.record['unbounded']), ([], True))
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_acceptance'), [])
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_resources'), [])

    def test_absent_and_malformed_observation_refuse(self):
        observation = self.record.pop('operation_observation')
        self.assertTrue(self.blocked())
        for bad in (None, {}, 'FICTION no current jobs', {'kind': scopes.OBSERVATION_KIND}):
            self.record['operation_observation'] = bad
            self.assertTrue(self.blocked())
        self.record['operation_observation'] = observation
        self.record['unbounded'] = False
        with self.assertRaises(Refusal):
            scopes.validate(self.s, {'QA': self.record})

    def test_attribution_and_source_hash_alone_supply_no_admission(self):
        self.s.db.execute('DELETE FROM processing_admissions')
        self.assertTrue(self.blocked())
        self.assertEqual(self.admission()['owner'], ACTOR)
        self.s.db.execute('DELETE FROM admissions')
        self.assertTrue(self.blocked())

    def test_changed_package_role_phase_and_current_work_refuse(self):
        for change in ({'package': 'fiction-other'}, {'role': 'Branch', 'phase': 'integrator'},
                       {'role': 'QA', 'phase': 'integrator'}, {'task': 'qa-cleanup'}):
            self.assertTrue(self.blocked({**self.row, **change}))
        self.cap['issuer'] = QA
        self.assertTrue(self.blocked())

    def test_changed_account_owner_or_positive_root_refuses(self):
        account = self.record['operation_observation']['account']
        account['author'] = WORK
        self.assertTrue(self.blocked())
        account['author'] = QA
        account['additional_relevant_roots'] = ['/fixtures/local/repo']
        self.assertTrue(self.blocked())

    def test_procedure_command_readback_source_output_and_scope_drift_refuse(self):
        original = self.admission()['receipt']
        changes = [lambda r: r['task_scopes']['qa-execution'].update(procedure='/fixtures/local/new-method'),
                   lambda r: r['task_scopes']['qa-execution'].update(cwd='/fixtures/local/new-cwd'),
                   lambda r: r['task_scopes']['qa-execution']['write_roots'].append('/fixtures/local/new-output'),
                   lambda r: r['task_scopes']['qa-execution']['read_roots'].append('/fixtures/local/new-read')]
        for key, value in [('source_ref', 'refs/heads/other'), ('source_head', '0'*40),
                           ('procedure_sha256', '0'*64), ('command', {}), ('readback', {}),
                           ('source_capture', {}), ('resources', [])]:
            changes.append(lambda r, k=key, v=value: r['task_scopes']['qa-execution']['ordinary_effects'].update({k: v}))
        changes += [lambda r: r['task_scopes']['qa-execution']['ordinary_effects']['command']['argv'].append('--different'),
                    lambda r: r['task_scopes']['qa-execution']['ordinary_effects']['readback'].update(stdout='FICTION other oracle'),
                    lambda r: r['task_scopes']['qa-execution']['ordinary_effects']['command'].update(script_sha256='0'*64),
                    lambda r: r['task_scopes']['qa-execution']['ordinary_effects']['resources'][0].update(expires=3000),
                    lambda r: r['task_scopes']['qa-execution']['ordinary_effects']['resources'][0].update(authority='FICTION changed authority'),
                    lambda r: r['task_scopes']['qa-cleanup']['write_roots'].append('/fixtures/local/output')]
        for change in changes:
            self.s.db.execute('UPDATE admissions SET receipt=?', (original,))
            self.change_receipt(change)
            self.assertTrue(self.blocked())

    def test_changed_source_or_missing_current_source_authority_refuses(self):
        self.s.source['body']['topic'] = 'fiction-other'
        self.assertTrue(self.blocked())
        self.s.source['body']['topic'] = 'fiction-exact'
        self.source_permitted = False
        self.assertTrue(self.blocked())

    def test_new_capability_or_selected_admission_drift_cannot_reuse_old_original(self):
        self.cap['id'] = 'fiction-other-capability'
        self.assertTrue(self.blocked())
        self.cap['id'] = 'fiction-current-cap'
        self.selection['software_admission']['scopes']['fiction-exact']['evidence'] = 'FICTION replacement authority'
        self.assertTrue(self.blocked())

    def test_different_real_source_cannot_replace_once_admitted_original(self):
        self.s.source['id'] = 'fiction-source-replacement'
        self.s.source['post'] = 3
        self.s.db.execute('INSERT INTO events VALUES(?,?,?)', (self.s.source['id'], None, digest(self.s.source)))
        self.s.db.execute('INSERT INTO processing_source_positions VALUES(?,?)', (self.s.source['id'], 3))
        with self.assertRaisesRegex(Refusal, 'no replacement or replay'):
            processing_admission.admit(self.s, self.s.source['id'])
        self.assertTrue(self.blocked())

    def test_cleanup_and_receiver_cannot_acquire_procedure_output_or_bookkeeping(self):
        for name in ('qa-cleanup', 'branch-proposer'):
            for path in ('/fixtures/local/output', '/fixtures/local/repo/procedure', '/fixtures/local/standing-record'):
                original = copy.deepcopy(self.record['operation_observation']['tasks'][name]['scope'])
                self.record['operation_observation']['tasks'][name]['scope']['read_roots'].append(path)
                self.assertTrue(self.blocked())
                self.record['operation_observation']['tasks'][name]['scope'] = original

    def test_output_and_execution_procedure_are_outside_source_cleanup_even_with_broader_ceiling(self):
        for name in ('qa-cleanup', 'branch-proposer'):
            original = copy.deepcopy(self.record['operation_observation']['tasks'][name])
            self.s.config['tasks'][name]['effect_authority']['read_roots'] = ['/fixtures/local']
            self.record['operation_observation']['tasks'][name]['policy'] = copy.deepcopy(self.s.config['tasks'][name])
            for path in ('/fixtures/local/output', '/fixtures/local/repo/procedure'):
                self.record['operation_observation']['tasks'][name]['scope']['read_roots'] = [path]
                with self.assertRaisesRegex(Refusal, 'source-only'):
                    scopes.validate(self.s, {'QA': self.record})
            self.s.config['tasks'][name] = original['policy']
            self.record['operation_observation']['tasks'][name] = original

    def test_network_ref_and_receiver_effect_authority_refuse_even_reselected(self):
        for name, change in [('qa-execution', {'network': True}),
                             ('qa-execution', {'effect_authority': {'operations': ['organize-authorized-refs']}}),
                             ('qa-cleanup', {'effect_authority': {'operations': ['write-role-records']}})]:
            original = copy.deepcopy(self.s.config['tasks'][name])
            self.s.config['tasks'][name].update(change)
            self.record['operation_observation']['tasks'][name]['policy'] = copy.deepcopy(self.s.config['tasks'][name])
            self.assertTrue(self.blocked())
            self.s.config['tasks'][name] = original
            self.record['operation_observation']['tasks'][name]['policy'] = copy.deepcopy(original)

    def test_known_conflicting_and_unmapped_current_local_owners_refuse(self):
        self.owner(role='Branch')
        self.assertTrue(self.blocked())
        self.s.db.execute('DELETE FROM job_resource_policies')
        self.assertTrue(self.blocked())

    def test_disjoint_original_frozen_owner_does_not_require_global_census(self):
        self.owner(same=False, role='Reviews')
        self.assertFalse(self.blocked())

    def test_known_conflicting_and_unmapped_leases_refuse_even_after_effect_settlement(self):
        bound = self.owner(same=True, effects='reconciled')
        self.s.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', ('fiction-prior-output', 'prior-attempt'))
        self.assertTrue(self.blocked())
        self.s.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?)',
                          ('prior-attempt', 'other', encode(bound['scope']['ordinary_effects'])))
        self.assertTrue(self.blocked())

    def test_disjoint_mapped_lease_and_changed_mapping(self):
        bound = self.owner(same=False, effects='reconciled')
        self.s.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', ('fiction-prior-output', 'prior-attempt'))
        self.s.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?)',
                          ('prior-attempt', 'other', encode(bound['scope']['ordinary_effects'])))
        self.assertFalse(self.blocked())
        self.s.db.execute("UPDATE ordinary_runs SET policy='{}'")
        self.assertTrue(self.blocked())

    def test_lease_expiry_does_not_follow_observation(self):
        self.s.clock = lambda: 2001
        self.assertTrue(self.blocked())

    def test_exclusion_precedes_metadata_and_symlink_is_not_independence(self):
        observation = self.record['operation_observation']
        observation['tasks']['qa-execution']['scope']['read_roots'] = ['/fixtures/excluded/secret']
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('excluded path metadata')):
            self.assertTrue(self.blocked())
        observation['tasks']['qa-execution']['scope']['read_roots'] = ['/fixtures/local/repo']
        with patch.object(Path, 'is_symlink', return_value=True):
            self.assertTrue(self.blocked())

    def test_existing_job_requires_unchanged_frozen_original_scope(self):
        row = {**self.row, 'id': 'current', 'active_attempt': 'current-attempt'}
        self.assertTrue(self.blocked(row))
        self.s.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',
            ('current', encode(self.bound['qa-execution']['policy']), encode(self.admission())))
        self.assertFalse(self.blocked(row))
        self.s.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', ('fiction-output', 'current-attempt'))
        self.s.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?)',
            ('current-attempt', 'current', encode(self.bound['qa-execution']['scope']['ordinary_effects'])))
        self.assertFalse(self.blocked(row))
        self.change_receipt(lambda r: r.update(resource_evidence='FICTION replacement'))
        self.assertTrue(self.blocked(row))

    def test_old_four_fields_keep_original_meaning(self):
        self.record.pop('operation_observation')
        self.assertTrue(self.blocked())
        self.record.update(roots=['/fixtures/disjoint/old'], unbounded=False)
        scopes.validate(self.s, {'QA': self.record})
        self.assertFalse(self.blocked())
        self.record['roots'] = []
        with self.assertRaises(Refusal):
            scopes.validate(self.s, {'QA': self.record})


if __name__ == '__main__':
    unittest.main()
