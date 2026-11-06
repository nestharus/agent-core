"""Selector behavior in fresh fictional stores; no campaign/test-fixture imports.

Each test retains its own mkdtemp directory (never automatic cleanup). Set
SELECTOR510_FIXTURES to an absolute owned output directory for bounded runs.
Board adapters below are fictional original-owner facts, not Board execution.
"""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coordinator_runtime import configuration
from coordinator_runtime.contracts import LUNA, SOL, Refusal, digest, encode, validate_config
from coordinator_runtime.retention_dependency import FILES
from coordinator_runtime.store import Store


def identity(number):
    return f'00000000-0000-4000-8000-{number:012d}'


class FictionalBoard:
    def __init__(self, owner, issuer):
        self.original = {'binding': {'issued_by': issuer, 'owner': owner},
                         'continuation': None, 'revoked': True}
        self.store = SimpleNamespace(acting_session=lambda selected: issuer if selected == issuer else None)

    def prospective_basis(self, runtime):
        return copy.deepcopy(self.original)

    def future_frontier(self):
        return 17


def fictional_config(root):
    """All paths/identities are invented; catalog targets are never created/read."""
    template = root / 'procedure.md'
    template.write_text('Fictional bounded procedure. Preserve existing rights and holds.\n')
    provider = root / 'retention'
    provider.mkdir()
    for name in FILES:
        (provider / name).write_text('# fictional pinned dependency; never executed\n')
    pool = root / 'pool.toml'
    pool.write_text('[providers.codex]\npool = []\nmanual_profiles = [".codex2"]\n'
                    f'[rotation]\nstate_dir = "{root / "unused-rotation"}"\n')
    roles, tasks = {}, {}
    for index, role in enumerate(('Work', 'Branch', 'Reviews', 'QA'), 1):
        phases = ('execution', 'cleanup') if role == 'QA' else ('proposer', 'integrator')
        names = [role.lower() + '-' + phase for phase in phases]
        roles[role] = {'owner': identity(index), 'profile': '.codex2',
                       'board_id': identity(index + 10), 'board_role': role,
                       'legacy_hold': 'Fictional unresolved historical custody.', 'routes': names,
                       'package_admission_required': role == 'QA'}
        for name, phase in zip(names, phases):
            tasks[name] = {'role': role, 'phase': phase, 'binding': copy.deepcopy(SOL),
                           'profile': '.codex2', 'cwd': str(root), 'templates': [str(template)],
                           'authority': 'Fictional original bounds. No new rights.\nKeep every hold.',
                           'purpose': 'Fictional generic phase purpose.', 'effects': 'none',
                           'sandbox': 'read-only', 'network': False, 'capacity': 1,
                           'effect_authority': {'owner': identity(index), 'operations': ['read-reports'],
                                                'read_roots': [str(template)], 'write_roots': []},
                           'allowed_handoffs': ['Work'], 'responses': {}}
    consumers = [str(root / 'catalog' / name) for name in
                 ('ASSIGNMENTS.json', 'ASSIGNMENTS.md', 'CONSOLIDATION_REGISTER.json',
                  'WORK_NOW_FICTIONAL.json', 'WORK_NOW_FICTIONAL.md', 'ROOT_NEXT.md', 'WORK_LOG.md')]
    integrator = tasks['work-integrator']
    integrator.update(effects='owner-reconcile', sandbox='workspace-write')
    integrator['effect_authority']['write_roots'] = consumers
    integrator['routine_completion'] = {
        'kind': 'catalog-bounded-log-v1', 'targets': consumers,
        'bounded_log': {'target': consumers[-1], 'max_lines': 12, 'max_bytes': 8192, 'max_entry_bytes': 16384}}
    directory = Path(configuration.__file__).resolve().parents[1]
    return {'version': 1, 'actor': identity(20), 'state_dir': str(root / 'state'),
            'roles': roles, 'tasks': tasks,
            'profiles': ['.codex', '.codex2', '.codex3', '.codex4', '.codex5'],
            'classifier': {'binding': copy.deepcopy(LUNA), 'profile': '.codex2', 'cwd': str(directory.parents[1])},
            'diagnosis': {'binding': copy.deepcopy(LUNA), 'profile': '.codex2', 'cwd': str(directory.parents[1])},
            'operator_cli': str(directory / 'coordinator'),
            'operator_config': str(root / 'original.json'), 'board_library': str(directory.parent / 'message-board'),
            'control_receive': {'instructions': str(directory / 'templates/coordinator-receive.md')},
            'canonical_publication': {'method': 'retention-same-inode-v1', 'library': str(provider)},
            'execution_pool_routes': str(pool),
            'software_delegation': {'grantor': identity(1), 'authority': 'Fictional text-only selection.',
                                    'boundary': 'new-journal-only'},
            'artifact_exclusions': [str(root / 'never-access-held')],
            'delivery': {'recipients': {'Work': {'session': identity(1), 'profile': '.codex2', 'board_role': 'Work'}}},
            'limits': {'max_events': 32, 'max_attempts': 32, 'max_jobs': 32, 'max_alerts': 32,
                       'max_alert_debt': 32, 'max_result_bytes': 65536, 'max_bytes': 32 * 1024 * 1024},
            'deadlines': {key: 5 for key in ('classify', 'task', 'ack', 'backlog', 'bind', 'interrupt', 'shutdown', 'alert_interval')}}


class TaskText510(unittest.TestCase):
    def setUp(self):
        parent = os.environ.get('SELECTOR510_FIXTURES')
        if parent and not Path(parent).is_absolute():
            raise ValueError('absolute owned fixture directory required')
        self.root = Path(tempfile.mkdtemp(prefix='selector510-', dir=parent))
        self.config = validate_config(fictional_config(self.root))
        self.original_bytes = encode(self.config).encode()
        Path(self.config['operator_config']).write_bytes(self.original_bytes)
        self.store = Store(self.config, controller=identity(30), clock=lambda: 12345.0)
        self.addCleanup(self.store.close)  # Close only; retain all fixture files.
        for role, selected in self.config['roles'].items():
            self.store.enroll(role, {'owner': selected['owner'], 'actor': self.config['actor'],
                                     'id': 'fictional-' + role, 'cutover': 0})
        self.boards = {role: FictionalBoard(selected['owner'], identity(1))
                       for role, selected in self.config['roles'].items()}
        self.text = {name: {'authority': task['authority'] + '\n\nFictional ' + name + ' phase clarification.',
                            'purpose': 'Fictional distinct ' + name + ' phase intent.'}
                     for name, task in self.config['tasks'].items()}

    def draft(self, options=None):
        return configuration.candidate(self.store, str(self.root / 'candidate.json'), [], scope_options=options)

    def save(self, value):
        Path(value['operator_config']).write_text(encode(value))

    def select_basis(self, value, tasks=None):
        self.save(value)
        return configuration.basis(self.store, self.boards, value, tasks or list(value['tasks']))

    def rows_except_transition(self):
        names = self.store.rows("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return {row['name']: self.store.rows('SELECT * FROM "' + row['name'] + '"')
                for row in names if row['name'] not in {'configuration_transitions', 'allocation_revision', 'sqlite_sequence'}}

    def test_draft_basis_selection_and_conservation(self):
        original = copy.deepcopy(self.config)
        # Invented historical responsibility and nonzero debt, never real input.
        with self.store.tx():
            self.store.db.execute('INSERT INTO alert_debt(id,subject,kind,created,payload) VALUES(?,?,?,?,?)',
                                  ('fictional-debt', 'fictional-held-input', 'backlog', 100, '{"unknown":true}'))
            self.store.db.execute('INSERT INTO events(id,role,payload,hash,received,hold) VALUES(?,?,?,?,?,?)',
                                  ('fictional-held-input', 'Work', '{}', digest({}), 100, 'fictional-effect-unknown'))
            self.store.db.execute('INSERT INTO jobs(id,role,phase,task,members,controller,token,created,hold_reason) VALUES(?,?,?,?,?,?,?,?,?)',
                                  ('fictional-held-job', 'Work', 'integrator', 'work-integrator', '[]',
                                   identity(30), 'fictional-token', 100, 'fictional-original-custody'))
        legacy = self.draft()
        candidate = self.draft({'task_text': self.text})
        self.assertEqual(len(candidate['tasks']), 8)
        self.assertEqual(len(candidate['tasks']['work-integrator']['routine_completion']['targets']), 7)
        expected = copy.deepcopy(legacy)
        expected['prospective_scope_selection'] = {'task_text': self.text}
        for name, fields in self.text.items():
            expected['tasks'][name].update(fields)
        self.assertEqual(candidate, expected)  # Every other parsed field conserved.
        self.assertEqual(self.config, original)
        before = self.rows_except_transition()
        inode = self.store.path.stat().st_ino
        basis = self.select_basis(candidate)
        self.assertEqual(basis['candidate'], digest(candidate))
        self.assertEqual(basis['release']['files'][candidate['operator_config']],
                         hashlib.sha256(encode(candidate).encode()).hexdigest())
        result = configuration.apply(self.store, self.boards, candidate,
                                     {'basis': basis, 'authority': 'Fictional owner selects phase clarification only.'})
        self.assertFalse(result['historical_recovery'])
        self.assertEqual(self.rows_except_transition(), before)
        self.assertEqual(Path(self.config['operator_config']).read_bytes(), self.original_bytes)
        self.assertEqual(self.store.one("SELECT value FROM meta WHERE key='configuration'")['value'], digest(original))
        reopened = Store(candidate, controller=identity(31))
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.path.stat().st_ino, inode)
        self.assertEqual(configuration.selected(reopened)['previous_configuration'], original)
        self.assertEqual(configuration.latest(reopened)['current'], digest(candidate))
        self.assertFalse(configuration.event_allowed(reopened, {'id': 'fictional-held-input'}))
        self.assertEqual(configuration.task_for_job(reopened, {'id': 'fictional-held-job', 'task': 'work-integrator'}),
                         original['tasks']['work-integrator'])
        configuration.assert_release(reopened)
        with self.assertRaisesRegex(Refusal, 'historical'):
            configuration.assert_current(self.store)
        # Reconstructing the already selected option is idempotent.
        next_draft = configuration.candidate(reopened, str(self.root / 'next.json'), [])
        configuration.validate_changes(reopened, next_draft, list(candidate['tasks']))

    def test_no_selector_and_empty_selector_preserve_text(self):
        legacy = self.draft()
        for options in (None, {}, {'task_text': {}}):
            with self.subTest(options=options):
                candidate = self.draft(options)
                self.assertEqual(candidate['tasks'], self.config['tasks'])
                candidate.pop('prospective_scope_selection', None)
                self.assertEqual(candidate, legacy)
                configuration.validate_changes(self.store, self.draft(options), list(self.config['tasks']))

    def test_purpose_only_authority_only_and_exact_byte_boundary(self):
        for fields in ({'purpose': 'é' * 8000}, {'authority': self.text['work-proposer']['authority']}):
            with self.subTest(fields=list(fields)):
                candidate = self.draft({'task_text': {'work-proposer': fields}})
                configuration.validate_changes(self.store, candidate, ['work-proposer'])
                self.assertEqual(candidate['tasks']['work-proposer']['purpose'], fields.get('purpose', self.config['tasks']['work-proposer']['purpose']))

    def test_malformed_and_unknown_selectors_refuse(self):
        invalid = [None, [], '', 1, {'unknown-task': {'purpose': 'Intent'}},
                   {'work-proposer': {}}, {'work-proposer': []}, {'work-proposer': {'new_field': 'Intent'}}]
        for selection in invalid:
            with self.subTest(selection=selection):
                with self.assertRaises(Refusal):
                    self.draft({'task_text': selection})

    def test_nontext_blank_and_oversize_values_refuse(self):
        for value in (None, 1, True, [], {}, '', ' \n', 'é' * 8001):
            for field in ('purpose', 'authority'):
                with self.subTest(field=field, value_type=type(value).__name__):
                    with self.assertRaises(Refusal):
                        self.draft({'task_text': {'work-proposer': {field: value}}})

    def test_authority_bounds_cannot_be_rewritten_or_shortened(self):
        old = self.config['tasks']['work-proposer']['authority']
        for authority in ('Replacement', old[:-1], old + ' appended without paragraph',
                          old + '\n\n \n', old.replace('No new rights.', 'New rights.') + '\n\nClarification'):
            with self.subTest(authority=authority):
                with self.assertRaisesRegex(Refusal, 'prior bounds'):
                    self.draft({'task_text': {'work-proposer': {'authority': authority}}})

    def test_missing_existing_purpose_cannot_be_created(self):
        del self.config['tasks']['work-proposer']['purpose']
        with self.assertRaisesRegex(Refusal, 'cannot add'):
            self.draft({'task_text': {'work-proposer': {'purpose': 'Intent'}}})

    def test_text_selection_requires_prospective_task_allowlist(self):
        candidate = self.draft({'task_text': self.text})
        with self.assertRaisesRegex(Refusal, 'task_text.*selected prospective task'):
            self.select_basis(candidate, ['work-proposer'])
        self.assertIsNone(configuration.latest(self.store))

    def test_unselected_or_tampered_text_refuses(self):
        for options in (None, {'task_text': {'work-proposer': self.text['work-proposer']}}):
            candidate = self.draft(options)
            candidate['tasks']['work-integrator']['purpose'] = 'Unselected changed purpose.'
            with self.assertRaisesRegex(Refusal, 'unsupported current configuration delta'):
                self.select_basis(candidate)
        self.assertIsNone(configuration.latest(self.store))

    def test_text_selector_cannot_select_rights_or_schema(self):
        for field in ('binding', 'profile', 'role', 'phase', 'effect_authority', 'effects',
                      'capacity', 'network', 'templates', 'scope_roots', 'allowed_handoffs'):
            with self.subTest(field=field):
                with self.assertRaisesRegex(Refusal, 'only existing authority/purpose'):
                    self.draft({'task_text': {'work-proposer': {field: 'arbitrary'}}})

    def test_typed_deltas_and_retention_capacity_changes_still_refuse(self):
        changes = [('limits', 'max_alert_debt', 33), ('delivery', 'extra', 'receiver'),
                   ('canonical_publication', 'method', 'other-method')]
        for section, field, replacement in changes:
            candidate = self.draft({'task_text': self.text})
            candidate[section][field] = replacement
            with self.subTest(section=section):
                with self.assertRaises(Refusal):
                    self.select_basis(candidate)
        for field, replacement in (('binding', copy.deepcopy(LUNA)), ('capacity', 2),
                                   ('effect_authority', {'owner': identity(2), 'operations': ['read-source'],
                                                         'read_roots': [str(self.root)], 'write_roots': []})):
            candidate = self.draft({'task_text': self.text})
            candidate['tasks']['branch-proposer'][field] = replacement
            with self.subTest(field=field):
                with self.assertRaises(Refusal):
                    self.select_basis(candidate)

    def test_stale_basis_refuses_changed_candidate_and_source(self):
        candidate = self.draft({'task_text': self.text})
        basis = self.select_basis(candidate)
        changed = self.draft({'task_text': {'work-proposer': {'purpose': 'Different selected intent.'}}})
        self.save(changed)
        with self.assertRaisesRegex(Refusal, 'basis changed'):
            configuration.apply(self.store, self.boards, changed, {'basis': basis, 'authority': 'Fictional decision.'})
        self.save(candidate)
        (self.root / 'procedure.md').write_text('Changed fictional source.\n')
        with self.assertRaisesRegex(Refusal, 'basis changed'):
            configuration.apply(self.store, self.boards, candidate, {'basis': basis, 'authority': 'Fictional decision.'})
        self.assertIsNone(configuration.latest(self.store))

    def test_active_capability_and_wrong_original_issuer_still_refuse(self):
        candidate = self.draft({'task_text': self.text})
        for board in self.boards.values():
            board.original['binding']['issued_by'] = identity(99)
        basis = self.select_basis(candidate)
        with self.assertRaisesRegex(Refusal, 'same genuine original Work issuer'):
            configuration.apply(self.store, self.boards, candidate, {'basis': basis, 'authority': 'Fictional decision.'})
        for board in self.boards.values():
            board.original['binding']['issued_by'] = identity(1)
        with self.store.tx():
            self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,?,?)',
                                  ('fictional-active', '{}', identity(1), 12345, None, 0))
        basis = self.select_basis(candidate)
        with self.assertRaisesRegex(Refusal, 'explicitly revoke'):
            configuration.apply(self.store, self.boards, candidate, {'basis': basis, 'authority': 'Fictional decision.'})
        self.assertIsNone(configuration.latest(self.store))


if __name__ == '__main__':
    unittest.main()
