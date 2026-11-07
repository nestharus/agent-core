"""Public entry and original-grant checks on newly owned synthetic fixtures.

Every identity/grant/record is generated here. No actual runtime, account,
provider, pool allocation, captured result or operating decision is acquired.
"""
from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, event, result
from coordinator_runtime import cli, configuration, processing
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.store import Store


class Management(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-management406-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = config_at(self.home)
        self.owner = self.config['roles']['Work']['owner']
        self.config['software_delegation'] = {'grantor': self.owner,
            'authority': 'Synthetic original user/Work delegation only', 'boundary': 'new-journal-only'}
        self.config['delivery'] = {'recipients': {r: {'session': s['owner'], 'profile': s['profile'],
            'board_role': s['board_role']} for r, s in self.config['roles'].items()}}
        if hasattr(self, 'configure'):
            self.configure()
        self.config_path = self.home/'config.json'
        self.config_path.write_text(encode(self.config))
        self.store = Store(self.config, clock=lambda: 1000.)
        self.addCleanup(self.store.close)
        self.boards = {}
        catalog = module_at(self.config['board_library'], 'catalog')
        substrate = module_at(self.config['board_library'], 'board_store')
        for role in ('Work', 'Branch'):
            selected = self.config['roles'][role]
            with catalog.catalog(Path(self.config['board_home'])) as conn:
                entry = catalog.create(conn, Path(self.config['board_home']), 'synthetic-'+role.lower(),
                    'Synthetic management test only', board_id=selected['board_id'], temporary_test=True)
            with substrate.database(entry['db_path']) as conn:
                substrate.bind_board(conn, selected['board_id'], initialize=True)
                args = substrate.parser().parse_args(['register', '--session', selected['owner'],
                    '--role', selected['board_role'], '--profile', selected['profile'], '--route', 'managed'])
                with patch.dict(os.environ, {'CODEX_SESSION_ID': selected['owner']}):
                    substrate.register(conn, args)
            board = Board(self.config, role)
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
                grant = board.grant_software(self.store, self.config['software_delegation']['authority'])
            self.store.enroll(role, grant)
            self.boards[role] = board
        self.source = event(self.config, 'synthetic-old')
        self.next = event(self.config, 'synthetic-next')
        self.insert('events', {'id': self.source['id'], 'role': 'Work', 'payload': encode(self.source),
            'hash': digest(self.source), 'received': 1., 'state': 'queued', 'ack': 'done'})
        self.insert('queue', {'id': 'synthetic-old-queue', 'event': self.source['id'], 'role': 'Work',
            'phase': 'integrator', 'task': 'work-integrator', 'state': 'reserved', 'job': 'synthetic-held'})
        self.insert('jobs', {'id': 'synthetic-held', 'role': 'Work', 'phase': 'integrator',
            'task': 'work-integrator', 'members': encode([{'queue': 'synthetic-old-queue',
                'event': self.source['id'], 'hash': digest(self.source), 'package': None}]),
            'controller': 'synthetic-original-controller', 'token': 'synthetic-token', 'created': 2.,
            'state': 'held', 'active_attempt': 'synthetic-attempt', 'hold_reason': 'synthetic unknown effects'})
        answer = result('PARTIAL', summary='Synthetic failure remains owned')
        answer['unknowns'] = [{'source': 'synthetic', 'meaning': 'effect not qualified'}]
        self.insert('attempts', {'id': 'synthetic-attempt', 'kind': 'task', 'job': 'synthetic-held',
            'controller': 'synthetic-original-controller', 'profile': 'synthetic-label', 'binding': '{}',
            'state': 'collected', 'created': 2., 'begin': 3., 'ended': 4., 'exit': 7, 'collected': 5.,
            'semantic': 'PARTIAL', 'capture': 'incomplete', 'error': 'synthetic original failure',
            'result': encode(answer)})
        self.insert('results', {'attempt': 'synthetic-attempt', 'job': 'synthetic-held',
            'result': encode(answer), 'error': 'synthetic failure', 'exit': 7, 'capture': 'incomplete', 'created': 5.})
        self.insert('outboxes', {'id': 'synthetic-outbox', 'role': 'Work', 'job': 'synthetic-held',
            'producer': 'synthetic-original-controller', 'recipient': 'Work', 'kind': 'question',
            'required': 'settled', 'payload': '{"unknown":"synthetic"}', 'state': 'sent', 'created': 6.})
        self.insert('file_publications', {'attempt': 'synthetic-attempt', 'target': 'synthetic-unacquired-target',
            'state': 'intent', 'error': 'synthetic unknown effect'})
        self.insert('artifact_custody', {'attempt': 'synthetic-attempt', 'path': 'synthetic-unacquired-artifact',
            'kind': 'report', 'owner': 'synthetic-original-custodian', 'witness': '{}', 'sha256': 'synthetic'})
        self.insert('events', {'id': self.next['id'], 'role': 'Work', 'payload': encode(self.next),
            'hash': digest(self.next), 'received': 10., 'state': 'queued', 'ack': 'done'})
        self.insert('queue', {'id': 'synthetic-next-queue', 'event': self.next['id'], 'role': 'Work',
            'phase': 'integrator', 'task': 'work-integrator'})
        # Capture a normal path before the intentional pause, then revoke through
        # the actual original software-owner protocol. No old grant is revived.
        self.normal_basis = self.call('integration-closure-basis', 'synthetic-held', '--token', 'synthetic-token')
        for role, board in self.boards.items():
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
                board.revoke_software(self.store, self.store.enrollment(role)['grant_id'])
        self.store.db.execute('UPDATE enrollments SET intake=0')
        self.basis = self.management_basis()

    def insert(self, table, values):
        self.store.db.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',
            tuple(values.values()))

    def call(self, *argv, actor=None, expected=0):
        out = io.StringIO()
        self.sql = []
        def runtime(config, **kwargs):
            value = Store(config, clock=lambda: 1000., **kwargs)
            value.db.set_trace_callback(self.sql.append)
            return value
        with patch.dict(os.environ, {'CODEX_SESSION_ID': actor or self.owner}), redirect_stdout(out), \
                patch.object(cli, 'Store', side_effect=runtime):
            code = cli.main(['--config', str(self.config_path), *argv])
        value = json.loads(out.getvalue())
        self.assertEqual(code, expected, value)
        return value

    def management_basis(self, roles=None):
        return self.call('integration-management-basis', '--roles', *(roles or ['Work']),
            '--authority', 'Synthetic current Work decision', '--purpose', 'Qualify synthetic ended integration while intake stays paused')

    def selection(self, command, *, basis=None, events=None):
        window = command in {'integration-window-basis', 'select-integration-window'}
        return {'basis': basis or self.basis, 'expires': 1100., 'operation': command,
            'target': {'task': 'work-integrator', 'events': events or [self.next['id']]} if window else
                      {'job': 'synthetic-held', 'token': 'synthetic-token'},
            'records': {'jobs': ['synthetic-held'],
                        'events': [self.source['id'], self.next['id']] if window else [self.source['id']]}}

    def managed(self, command, *, selection=None, receipt=None, expected=0, actor=None):
        path = self.home/'management.json'
        path.write_text(encode(selection or self.selection(command)))
        argv = [command]
        if command in {'integration-closure-basis', 'retire-integration'}:
            argv += ['synthetic-held', '--token', 'synthetic-token']
        if command == 'integration-window-basis':
            argv += ['work-integrator', '--events', self.next['id']]
        if receipt is not None:
            record = self.home/'receipt.json'; record.write_text(encode(receipt))
            argv += ['--receipt', str(record)]
        return self.call(*argv, '--management', str(path), expected=expected, actor=actor)

    def closure(self):
        basis = self.managed('integration-closure-basis')
        return {'basis': basis, 'reason': 'Synthetic closed execution, effects and duties conserved',
            'controllers': [{'controller': c, 'collector': 'synthetic-original-collector', 'end': 7,
                'collected': True, 'writers_closed': True, 'evidence': ['Synthetic explicit original closure witness']}
                for c in basis['controllers']]}

    def window(self):
        return {'basis': self.managed('integration-window-basis'), 'target': 'Synthetic fresh bounded batch',
            'why': 'Continue with exact conserved debt and independent current inputs',
            'conflict_evidence': ['Synthetic applicable peer qualification'],
            'custodian_evidence': ['Synthetic original custodian retains unknown publication/effect/source duties']}

    def conserved(self):
        tables = ['jobs', 'attempts', 'results', 'events', 'queue', 'outboxes', 'file_publications',
            'artifact_custody', 'recovery_requests', 'recovery_dispositions', 'enrollments', 'cursors',
            'processing_capabilities', 'processing_runs', 'processing_owner_operations', 'artifacts',
            'integration_retirements', 'integration_windows', 'integration_management_operations']
        data = {t: self.store.rows('SELECT * FROM '+t+' ORDER BY rowid') for t in tables}
        data['boards'] = {}
        for role, board in self.boards.items():
            with sqlite3.connect(board.path) as conn:
                data['boards'][role] = {t: conn.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall()
                    for t in ['coordinator_grants_v1', 'sessions', 'posts', 'notification_outbox']}
        return data

    def test_paused_public_management_preserves_duties_and_normal_path(self):
        self.call('integration-closure-basis', 'synthetic-held', '--token', 'synthetic-token', expected=2)
        before = self.conserved()
        receipt = self.closure()
        self.assertEqual(receipt['basis'], self.normal_basis)
        self.assertEqual(before, self.conserved())
        self.managed('retire-integration', receipt=receipt)
        window = self.window()
        self.managed('select-integration-window', receipt=window)
        after = self.conserved()
        for key in before:
            if key not in {'integration_retirements', 'integration_windows', 'integration_management_operations'}:
                self.assertEqual(before[key], after[key], key)
        self.assertEqual(len(after['integration_management_operations']), 2)
        self.assertTrue(self.store.execution_complete(self.store.job('synthetic-held')))
        self.assertIsNone(self.store.processing)
        self.assertIsNone(getattr(self.store, 'integration_management', None))
        self.assertRaises(Refusal, self.store.enrollment, 'Work')
        self.assertRaises(Refusal, self.store.ingest, event(self.config, 'synthetic-refused-intake'))
        self.assertIsNone(self.store.reserve())
        self.assertRaises(Refusal, self.store.require_execution_open, 'synthetic-held')
        self.assertEqual(self.store.rows('SELECT * FROM processing_capabilities'), [])
        self.assertFalse((self.home/'pool-state').exists())

    def test_wrong_actor_stale_binding_source_purpose_and_operation_refuse(self):
        before = self.conserved()
        self.managed('integration-closure-basis', actor=ident(), expected=2)
        mutations = [lambda s: s.update(expires=1000.), lambda s: s.update(expires=5000.),
            lambda s: s['basis'].update(authority=''), lambda s: s['basis'].update(purpose=''),
            lambda s: s['basis'].update(configuration='synthetic-stale'),
            lambda s: s['basis']['implementation'].update({'integration.py': 'synthetic-stale'}),
            lambda s: s['basis']['roles']['Work']['binding'].update(owner=ident()),
            lambda s: s.update(operation='retire-integration'),
            lambda s: s['target'].update(token='synthetic-wrong'),
            lambda s: s.update(processing_capability='synthetic-borrowed'),
            lambda s: s['records'].update(jobs=[]),
            lambda s: s['records'].update(events=[self.source['id'], self.next['id']])]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                selection = copy.deepcopy(self.selection('integration-closure-basis')); mutate(selection)
                self.managed('integration-closure-basis', selection=selection, expected=2)
                self.assertFalse(any('SELECT * FROM results' in sql for sql in self.sql))
                self.assertEqual(before, self.conserved())

    def test_original_protocol_and_membership_refuse_without_acquiring_old_results(self):
        board = self.boards['Work']
        for statement in ["UPDATE coordinator_grants_v1 SET runtime_ino=runtime_ino+1",
                          "UPDATE coordinator_grants_v1 SET revoked=NULL",
                          "UPDATE coordinator_software_grants_v1 SET configuration='synthetic-stale'",
                          "UPDATE sessions SET status='paused'"]:
            with self.subTest(statement=statement), sqlite3.connect(board.path) as conn:
                conn.execute(statement)
                conn.commit()
                # Save full small synthetic fixture values to restore below.
                self.managed('integration-closure-basis', expected=2)
                self.assertFalse(any('SELECT * FROM results' in sql for sql in self.sql))
                if 'runtime_ino' in statement:
                    conn.execute('UPDATE coordinator_grants_v1 SET runtime_ino=runtime_ino-1')
                elif 'revoked' in statement:
                    conn.execute("UPDATE coordinator_grants_v1 SET revoked='synthetic-revoked'")
                elif 'configuration' in statement:
                    conn.execute('UPDATE coordinator_software_grants_v1 SET configuration=?', (digest(self.config),))
                else:
                    conn.execute("UPDATE sessions SET status='active'")
                conn.commit()
                self.basis = self.management_basis()

    def test_related_source_requires_its_exact_original_enrollment(self):
        # The relationship header names another original source. A Work owner
        # token cannot silently admit that role or acquire its linked bodies.
        self.store.db.execute('UPDATE events SET role=? WHERE id=?', ('Branch', self.source['id']))
        self.managed('integration-closure-basis', expected=2)
        self.assertFalse(any('SELECT * FROM results' in sql for sql in self.sql))
        selection = self.selection('integration-closure-basis', basis=self.management_basis(['Work', 'Branch']))
        self.managed('integration-closure-basis', selection=selection)
        self.store.db.execute("UPDATE enrollments SET owner='synthetic-foreign' WHERE role='Branch'")
        self.managed('integration-closure-basis', selection=selection, expected=2)
        self.assertFalse(any('SELECT * FROM results' in sql for sql in self.sql))

    def test_reservation_token_and_audit_failure_remain_transactional(self):
        selection = self.selection('integration-closure-basis')
        selection['target']['token'] = 'synthetic-wrong'
        path = self.home/'wrong-token.json'; path.write_text(encode(selection))
        refused = self.call('integration-closure-basis', 'synthetic-held', '--token', 'synthetic-wrong',
            '--management', str(path), expected=2)
        self.assertIn('reservation fence', refused['error'])
        before = self.conserved()
        self.store.db.execute("CREATE TRIGGER synthetic_audit_failure BEFORE INSERT ON integration_management_operations BEGIN SELECT RAISE(ABORT,'synthetic audit unavailable'); END")
        refused = self.managed('retire-integration', receipt=self.closure(), expected=2)
        self.assertIn('synthetic audit unavailable', refused['error'])
        self.assertEqual(before, self.conserved())

    def test_missing_closure_stale_receipt_and_pending_recovery_refuse(self):
        good = self.closure()
        for field, value in [('ended', None), ('begin', None), ('collected', None), ('exit', None)]:
            old = self.store.attempt('synthetic-attempt')[field]
            self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?', (value, 'synthetic-attempt'))
            before = self.conserved()
            self.managed('retire-integration', receipt=good, expected=2)
            self.assertEqual(before, self.conserved())
            self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?', (old, 'synthetic-attempt'))
        for field, value in [('writers_closed', False), ('collected', False), ('collector', ''), ('evidence', [])]:
            receipt = copy.deepcopy(good); receipt['controllers'][0][field] = value
            before = self.conserved(); self.managed('retire-integration', receipt=receipt, expected=2)
            self.assertEqual(before, self.conserved())
        self.store.db.execute("UPDATE attempts SET error='synthetic later adverse' WHERE id='synthetic-attempt'")
        self.managed('retire-integration', receipt=good, expected=2)
        good = self.closure()
        self.insert('recovery_requests', {'id': 'synthetic-recovery', 'job': 'synthetic-held',
            'actor': self.owner, 'attempt': 'synthetic-attempt', 'receipt': '{}', 'state': 'pending', 'created': 900.})
        before = self.conserved(); self.managed('retire-integration', receipt=good, expected=2)
        self.assertEqual(before, self.conserved())

    def test_window_scope_currentness_conflicts_and_custody_remain_required(self):
        self.managed('retire-integration', receipt=self.closure())
        before = self.conserved()
        selection = self.selection('integration-window-basis'); selection['records']['jobs'] = []
        self.managed('integration-window-basis', selection=selection, expected=2)
        receipt = self.window()
        for field in ['target', 'why', 'conflict_evidence', 'custodian_evidence']:
            bad = copy.deepcopy(receipt); bad[field] = [] if field.endswith('evidence') else ''
            self.managed('select-integration-window', receipt=bad, expected=2)
        self.store.db.execute("UPDATE outboxes SET hold='synthetic later uncertainty' WHERE id='synthetic-outbox'")
        self.managed('select-integration-window', receipt=receipt, expected=2)
        self.store.db.execute("UPDATE outboxes SET hold=NULL WHERE id='synthetic-outbox'")
        self.assertEqual(before, self.conserved())


if __name__ == '__main__':
    unittest.main()
