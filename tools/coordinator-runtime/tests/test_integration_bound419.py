"""Source/synthetic controls for Decision416/418; no runtime or pool access.

Run: python3 -B tools/coordinator-runtime/tests/test_integration_bound419.py
Uses an in-memory journal and selected unchanged Store methods compiled from
source. Transactions are real SQLite; configuration admission and cumulative
disk accounting are outside this control. Allocation is explicitly fictional.
No stock fixture startup, files, providers, Board, grants or cleanup are used.
"""
import ast
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.integration import IntegrationJournal, SCHEMA
from coordinator_runtime.integration_evidence import attempt_view, expand, fence_view
from coordinator_runtime import prospective


def source_tree(name):
    return ast.parse((ROOT / 'coordinator_runtime' / name).read_text())


def schema(name):
    return next(ast.literal_eval(n.value) for n in source_tree(name).body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCHEMA' for t in n.targets))


def selected_store():
    original = next(n for n in source_tree('store.py').body if isinstance(n, ast.ClassDef) and n.name == 'Store')
    names = {'one', 'rows', 'job', 'attempt', 'event', 'enrollment', 'role_enabled', 'source_roles',
             'require_active_sources', '_input_member', '_members', '_capacity', 'execution_complete',
             '_reserve_first', '_reserve_candidate', 'reserve', '_attempt', 'start_job', 'authorize_launch'}
    chosen = [n for n in original.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in chosen} == names
    original.bases = []; original.decorator_list = []; original.body = chosen
    namespace = {'__name__': 'coordinator_runtime.store', '__package__': 'coordinator_runtime', 'json': json, 'Refusal': Refusal,
                 'encode': encode, 'digest': digest, 'ident': ident, 'prospective': prospective}
    exec(compile(ast.Module(body=[original], type_ignores=[]), str(ROOT / 'coordinator_runtime/store.py'), 'exec'), namespace)
    return namespace['Store']


class Journal(IntegrationJournal, selected_store()):
    def __init__(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(''.join(schema(n) for n in ['store.py', 'delivery.py', 'custody.py',
            'publication.py', 'recovery.py', 'inputs.py', 'ref_scope.py']) + SCHEMA + prospective.SCHEMA)
        self.clock = lambda: 100.0
        self.controller = 'synthetic-successor-controller'
        self.processing = None
        self.launch_authorizer = self.task_launch_authorizer = None
        self.config = {'limits': {'max_result_bytes': 262144, 'max_jobs': 12},
            'profiles': ['synthetic-account'], 'roles': {'Work': {'owner': 'synthetic-owner'}},
            'tasks': {'integrate': {'role': 'Work', 'phase': 'integrator', 'effects': 'owner-reconcile',
                                  'profile': 'synthetic-account', 'binding': {}}}}
        self.allocations = 0
        self.budget_calls = []
        self.execution_pool = self
        self.insert('enrollments', {'role': 'Work', 'owner': 'synthetic-owner', 'profile': 'synthetic-account',
            'grant_id': 'synthetic-original-grant', 'cutover': 0, 'intake': 1})
        for name in ['old-input', 'next-input', 'later-input']:
            self.insert('events', {'id': name, 'role': 'Work', 'payload': encode({'id': name, 'body': 'Synthetic response evidence'}),
                'hash': name, 'received': 1, 'state': 'queued', 'ack': 'done'})
            self.insert('queue', {'id': name + '-q', 'event': name, 'role': 'Work', 'phase': 'integrator', 'task': 'integrate'})
        member = self._input_member(self.one("SELECT * FROM queue WHERE event='old-input'"))
        self.insert('jobs', {'id': 'old', 'role': 'Work', 'phase': 'integrator', 'task': 'integrate',
            'members': encode([member]), 'controller': 'synthetic-original-controller', 'token': 'old-token',
            'created': 1, 'state': 'held', 'active_attempt': 'old-a', 'effects': 'unknown',
            'hold_reason': 'PARTIAL primary null; incomplete capture, effects UNKNOWN'})
        self.db.execute("UPDATE queue SET state='reserved',job='old' WHERE event='old-input'")
        self.accounts = [{'domain': d, 'state': 'PARTIAL', 'questions': [3*d+i for i in range(3)],
                          'unknowns': ['R13 callback remains restricted', 'No actual availability proof'],
                          'handling': ['prior handling failure retained'], 'capture': ['incomplete'],
                          'oldtest': ['historical failed/unreached controls retained']} for d in range(9)]
        # Unique, attributed synthetic evidence, not copied production bodies or
        # filesystem filler. The historical snapshot is intentionally nested.
        observations = [{'question': q, 'sources': [
            {'source': f'synthetic-source-{q}-{i}', 'observation':
             f'Synthetic question {q}, source {i}: END does not settle processing; original custodian retains '
             'publication intent and incomplete capture. Counterevidence: execution fence prevents replay; effects remain UNKNOWN.'}
            for i in range(17)]} for q in range(27)]
        history = {'task': 'integrate', 'members': [member], 'debt': observations,
                   'enrollment': self.enrollment('Work')}
        old_window = {'basis': {**history, 'debt': [{'earlier_selection': {'basis': history}, 'same_retained_snapshot': history}]},
                      'target': 'Synthetic earlier integration', 'why': 'Retain independent duties',
                      'conflict_evidence': ['Synthetic target conflict remains owner-qualified'],
                      'custodian_evidence': ['Synthetic original custodian retains uncertainty']}
        detail = {'primary': None, 'all9': self.accounts, 'all27': list(range(27)),
                  'unknowns': ['effects UNKNOWN'], 'unrecognized_future_field': ['keep this too'],
                  'integration_window': old_window}
        self.insert('attempts', {'id': 'old-a', 'kind': 'task', 'job': 'old', 'controller': 'synthetic-original-controller',
            'profile': 'synthetic-account', 'binding': '{}', 'created': 1, 'begin': 2, 'ended': 3,
            'exit': 2, 'collected': 4, 'state': 'collected', 'semantic': 'PARTIAL', 'capture': 'incomplete',
            'cleanup': 'unknown', 'error': 'adverse original retained', 'detail': encode(detail)})
        self.insert('results', {'attempt': 'old-a', 'job': 'old', 'exit': 2, 'capture': 'incomplete',
            'created': 4, 'error': 'original structured failure retained'})
        self.insert('outboxes', {'id': 'old-outbox', 'role': 'Work', 'job': 'old', 'event': 'old-input',
            'producer': 'synthetic-producer', 'recipient': 'Work', 'kind': 'question', 'required': 'settled',
            'payload': '{"unknown":"delivery"}', 'state': 'sent', 'created': 5})
        self.insert('file_publications', {'attempt': 'old-a', 'target': 'synthetic-target', 'state': 'intent', 'error': 'UNKNOWN'})
        self.insert('artifact_custody', {'attempt': 'old-a', 'path': 'synthetic-report', 'kind': 'report',
            'owner': 'synthetic-original-custodian', 'witness': '{}', 'sha256': 'synthetic'})
        self.insert('source_custody', {'event': 'old-input', 'basis': 'result',
            'owner': 'synthetic-original-source-custodian', 'binding': '{"unknowns":["source retained"]}'})

    @contextmanager
    def tx(self):
        # Configuration transition/access checks deliberately not simulated.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def insert(self, table, values):
        self.db.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')', tuple(values.values()))

    def budget(self, kind, size=0, **kwargs):
        self.budget_calls.append((kind, size))  # Observes calls; does not qualify production disk accounting.

    def input_resolution(self, *args):
        return None  # No input-owner correction selected in this synthetic journal.

    def allocate(self):
        self.allocations += 1
        return {'profile': 'synthetic-account', 'fixture': True}

    def closure(self):
        basis = self.integration_closure_basis('old', 'old-token')
        return {'basis': basis, 'reason': 'Synthetic execution closed; every original duty retained',
                'controllers': [{'controller': c, 'collector': 'synthetic-collector', 'end': 2,
                    'collected': True, 'writers_closed': True, 'evidence': ['Synthetic original END2 and scoped writer closure']}
                    for c in basis['controllers']]}

    def retire(self):
        return self.retire_integration('old', 'old-token', 'synthetic-owner', self.closure())

    def selection(self):
        return {'basis': self.integration_window_basis('integrate', ['next-input', 'later-input']),
                'target': 'Synthetic independent response integration', 'why': 'Receive both completed proposals without old replay',
                'conflict_evidence': ['Synthetic peers qualified for this new target only'],
                'custodian_evidence': ['Synthetic original owner retains publication/recovery/effect debt']}

    def select(self):
        return self.select_integration_window('synthetic-owner', self.selection())

    def snapshot(self):
        tables = self.rows("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return {t['name']: self.rows('SELECT * FROM '+t['name']+' ORDER BY rowid') for t in tables}


class Controls(unittest.TestCase):
    def setUp(self):
        self.s = Journal()
        self.addCleanup(self.s.db.close)

    def refused(self, action):
        before = self.s.snapshot()
        with self.assertRaises(Refusal):
            action()
        self.assertEqual(before, self.s.snapshot())

    def test_nested_witness_fits_and_keeps_duties_through_selection_reservation_launch(self):
        s = self.s
        original = s.snapshot()
        fence = s.retire()
        self.assertGreater(len(fence['basis']) + len(fence['receipt']), 344291)
        self.assertEqual(original['attempts'], s.snapshot()['attempts'])
        self.assertEqual(original['jobs'], s.snapshot()['jobs'])
        self.assertIsNone(s.reserve())  # The fence alone grants no successor.
        selection = s.selection()
        debt = selection['basis']['debt'][0]
        self.assertLess(len(encode(selection).encode()), 262144)
        self.assertEqual('held', debt['current_job']['state'])
        self.assertEqual('unknown', debt['current_job']['effects'])
        attempt = debt['attempts'][0]
        self.assertEqual(('PARTIAL', 'incomplete', 'unknown'), (attempt['semantic'], attempt['capture'], attempt['cleanup']))
        self.assertEqual(s.accounts, attempt['detail']['all9'])
        self.assertEqual(list(range(27)), attempt['detail']['all27'])
        self.assertEqual(['effects UNKNOWN'], attempt['detail']['unknowns'])
        self.assertEqual(['keep this too'], attempt['detail']['unrecognized_future_field'])
        self.assertEqual('synthetic-original-custodian', debt['custody'][0]['owner'])
        self.assertEqual('intent', debt['publication'][0]['state'])
        self.assertEqual('sent', debt['outboxes'][0]['state'])
        self.assertEqual('synthetic-original-source-custodian', debt['source_custody'][0]['owner'])
        self.assertTrue(debt['retirement']['basis_matches_receipt'])
        self.assertEqual(fence['basis'], expand(debt['retirement']['basis'], fence))
        self.assertEqual(json.loads(fence['receipt'])['basis'], expand(debt['retirement']['receipt']['basis'], fence))
        old = s.attempt('old-a')
        self.assertEqual(old['detail'], expand(attempt['original_detail'], old))
        old_basis = json.loads(old['detail'])['integration_window']['basis']
        window_basis = attempt['detail']['integration_window']['basis']
        self.assertEqual(old_basis['debt'], expand(window_basis['debt'], old))
        for field in ['task', 'members', 'enrollment']:
            self.assertEqual(old_basis[field], window_basis[field])
        permit = s.select_integration_window('synthetic-owner', selection)
        self.assertTrue(s.budget_calls[-1][1] > 0)
        job = s.reserve()
        self.assertEqual(permit['id'], s.one('SELECT id FROM integration_windows WHERE job=?', (job['id'],))['id'])
        self.assertEqual(['next-input', 'later-input'], [m['event'] for m in json.loads(job['members'])])
        aid = s.start_job(job['id'], job['token'])
        s.authorize_launch(aid)
        self.assertEqual(1, s.allocations)
        self.assertEqual(selection, s.integration_context(job['id']))
        self.assertEqual(selection, json.loads(s.attempt(aid)['detail'])['integration_window'])
        self.assertEqual(original['attempts'][0], s.attempt('old-a'))
        for table in ['events', 'results', 'outboxes', 'artifact_custody', 'source_custody', 'file_publications']:
            self.assertEqual(original[table], s.snapshot()[table])
        self.assertIsNone(s.job('old')['effect_receipt'])
        self.assertIsNone(s.event('old-input').get('processed_at'))
        self.assertIsNone(s.reserve())
        for action in [lambda: s.require_execution_open('old'), lambda: s.start_job('old', 'old-token'),
                       lambda: s.authorize_launch('old-a'), lambda: s.start_job(job['id'], job['token'])]:
            self.refused(action)
        print('CONSTRUCTION', encode({'basis_chars': len(fence['basis']), 'receipt_chars': len(fence['receipt']),
            'window_basis_utf8': len(encode(selection['basis']).encode()), 'selection_utf8': len(encode(selection).encode()),
            'limit': 262144, 'new_members': 2, 'synthetic_allocations': s.allocations}))

    def test_owner_token_evidence_bounds_and_replay(self):
        s = self.s
        r = s.closure()
        self.refused(lambda: s.retire_integration('old', 'old-token', 'foreign-owner', r))
        self.refused(lambda: s.retire_integration('old', 'wrong-token', 'synthetic-owner', r))
        s.retire()
        self.refused(s.retire)
        r = s.selection()
        self.refused(lambda: s.select_integration_window('foreign-owner', r))
        for field in ['conflict_evidence', 'custodian_evidence']:
            invalid = copy.deepcopy(r); invalid[field] = []
            self.refused(lambda: s.select_integration_window('synthetic-owner', invalid))
        s.select_integration_window('synthetic-owner', r)
        self.refused(lambda: s.select_integration_window('synthetic-owner', r))
        self.refused(lambda: s.integration_window_basis('integrate', ['old-input']))
        self.refused(lambda: s.integration_window_basis('integrate', ['next-input', 'next-input']))
        self.refused(lambda: s.integration_window_basis('absent', ['next-input']))
        s.config['window_service'] = {'batch_size': 1}
        self.refused(s.selection)
        del s.config['window_service']
        s.config['limits']['max_jobs'] = 1
        self.refused(s.select)
        s.config['limits']['max_result_bytes'] = len(encode(r['basis']).encode()) - 1
        self.refused(s.selection)

    def test_prestart_withdrawal_keeps_frozen_history_and_requires_fresh_window(self):
        s = self.s; s.retire(); s.select(); job = s.reserve()
        basis = s.integration_prestart_basis(job['id'], job['token'])
        receipt = {'basis': basis, 'reason': 'Synthetic no allocation, no launch',
                   'no_launch_evidence': ['Synthetic original controller explicitly closed its writer']}
        original = s.snapshot()
        fence = s.withdraw_integration_prestart(job['id'], job['token'], 'synthetic-owner', receipt)
        debt = s.integration_debt()
        self.assertEqual(2, len(debt))
        self.assertEqual(basis, json.loads(expand(debt[1]['prestart_disposition']['basis'], fence)))
        self.assertEqual(original['attempts'], s.snapshot()['attempts'])
        self.assertEqual(original['integration_windows'], s.snapshot()['integration_windows'])
        self.assertIsNone(s.job(job['id'])['active_attempt'])
        self.assertEqual(0, s.allocations)
        self.assertIsNone(s.reserve())
        self.refused(lambda: s.start_job(job['id'], job['token']))
        s.select(); successor = s.reserve()
        aid = s.start_job(successor['id'], successor['token'])
        s.authorize_launch(aid)
        self.assertEqual(1, s.allocations)
        self.assertEqual(2, len(s.integration_debt()))

    def test_material_and_relationship_changes_refuse_selection_reservation_and_launch(self):
        s = self.s; s.retire()
        changes = [
            "UPDATE integration_retirements SET basis=basis||' '",
            "UPDATE integration_retirements SET receipt=receipt||' '",
            "UPDATE attempts SET detail=replace(detail,'synthetic-source-0-0','changed-source-0-0') WHERE id='old-a'",
            "UPDATE attempts SET error='later adverse' WHERE id='old-a'",
            "UPDATE attempts SET job=NULL WHERE id='old-a'",
            "UPDATE jobs SET hold_reason='new unknown duty' WHERE id='old'",
            "UPDATE jobs SET members='[]' WHERE id='old'",
            "UPDATE outboxes SET error='new delivery uncertainty'",
            "UPDATE file_publications SET error='new effect uncertainty'",
            "UPDATE artifact_custody SET owner='synthetic-new-custodian'",
            "UPDATE source_custody SET owner='synthetic-new-source-custodian'",
            "UPDATE queue SET job=NULL WHERE event='old-input'",
            "UPDATE events SET payload='{\"id\":\"changed\"}' WHERE id='old-input'",
            "UPDATE events SET payload='{\"id\":\"changed\"}' WHERE id='next-input'",
            "UPDATE events SET hold='synthetic source hold' WHERE id='next-input'",
            "UPDATE enrollments SET grant_id='synthetic-renewed-grant'",
            "INSERT INTO recovery_requests(job,attempt,actor,receipt,created,state) VALUES('old','old-a','synthetic-owner','{}',1,'pending')",
            "INSERT INTO recovery_dispositions VALUES('synthetic-diagnosis','old','old-a','unknown effects retained','synthetic-owner',1)",
        ]
        original = self.s
        for sql in changes:
            for phase in ['selection', 'reservation', 'start', 'authorization']:
                with self.subTest(sql=sql, phase=phase):
                    s = Journal(); self.s = s
                    try:
                        s.retire(); r = s.selection()
                        permit = s.select() if phase != 'selection' else None
                        job = s.reserve() if phase in {'start', 'authorization'} else None
                        aid = s.start_job(job['id'], job['token']) if phase == 'authorization' else None
                        s.db.execute(sql)
                        if phase == 'selection':
                            self.refused(lambda: s.select_integration_window('synthetic-owner', r))
                        elif phase == 'reservation':
                            before = s.snapshot()
                            self.assertIsNone(s.reserve())
                            self.assertEqual(before, s.snapshot())
                            self.assertIsNone(s.one('SELECT job FROM integration_windows WHERE id=?', (permit['id'],))['job'])
                        elif phase == 'start':
                            self.refused(lambda: s.start_job(job['id'], job['token']))
                            self.assertEqual(0, s.allocations)
                            self.assertIsNone(s.job(job['id'])['active_attempt'])
                        else:
                            self.refused(lambda: s.authorize_launch(aid))
                    finally:
                        s.db.close(); self.s = original

    def test_reference_expansion_missing_changed_and_exact_utf8(self):
        s = self.s; s.retire()
        row = s.integration_retired('old')
        view = fence_view(row, 'integration_retirements')
        self.refused(lambda: expand(view['basis'], None))
        self.refused(lambda: expand(view['basis'], {**row, 'job': 'foreign-job'}))
        self.refused(lambda: expand(view['basis'], {**row, 'basis': row['basis'] + ' '}))
        self.refused(lambda: expand(view['receipt']['basis'], {**row, 'receipt': '{}'}))
        changed = s.attempt('old-a')
        detail = json.loads(changed['detail']); detail['unknowns'].append('未知の効果')
        changed = {**changed, 'detail': encode(detail)}
        projection = attempt_view(changed)
        self.assertEqual(detail['unknowns'], projection['detail']['unknowns'])
        self.assertEqual(changed['detail'], expand(projection['original_detail'], changed))
        self.assertGreater(projection['original_detail']['encoded_bytes'], len(encode(changed['detail'])))

    def test_unknown_large_current_evidence_still_refuses_without_loss(self):
        s = self.s; s.retire()
        detail = json.loads(s.attempt('old-a')['detail'])
        history = detail['integration_window']['basis']
        detail['unrecognized_future_evidence'] = [history, history]
        s.db.execute("UPDATE attempts SET detail=? WHERE id='old-a'", (encode(detail),))
        projection = attempt_view(s.attempt('old-a'))
        self.assertEqual(detail['unrecognized_future_evidence'], projection['detail']['unrecognized_future_evidence'])
        self.refused(s.selection)
        self.assertEqual(262144, s.config['limits']['max_result_bytes'])
        self.assertEqual(0, s.allocations)

    def test_prestart_fence_and_unknown_shapes_preserve_evidence(self):
        row = {'job': 'synthetic-prestart', 'actor': 'synthetic-owner', 'created': 1,
               'basis': '{"job":{"state":"reserved"}}', 'receipt': encode({'basis': {'job': {'state': 'reserved'}},
                   'reason': 'No allocation; no END invented', 'no_launch_evidence': ['Synthetic scoped closure'],
                   'unknowns': ['Preserve future receipt extensions']})}
        view = fence_view(row, 'integration_prestart_dispositions')
        self.assertEqual(['Preserve future receipt extensions'], view['receipt']['unknowns'])
        self.assertEqual(row['basis'], expand(view['basis'], row))
        self.assertEqual(row['receipt'], expand(view['original_receipt'], row))
        conflict = {**row, 'receipt': encode({'basis': {'job': {'state': 'held'}}, 'unknowns': ['conflicting historical snapshot']})}
        self.assertFalse(fence_view(conflict, 'integration_prestart_dispositions')['basis_matches_receipt'])
        for body in ['not-json', '[]', '{"unknowns":["no known basis"]}', '{"basis":{},"basis":{"conflict":true}}']:
            candidate = {**row, 'receipt': body}
            self.assertEqual(body, fence_view(candidate, 'integration_prestart_dispositions')['receipt'])
        for body in ['not-json', '[]', '{"integration_window":["unexpected"]}',
                     '{"integration_window":{"unknowns":["no basis"]}}',
                     '{"integration_window":{"basis":{"unrecognized":"keep inline"}}}']:
            candidate = {**self.s.attempt('old-a'), 'detail': body}
            self.assertEqual(candidate, attempt_view(candidate))


if __name__ == '__main__':
    unittest.main(verbosity=2)
