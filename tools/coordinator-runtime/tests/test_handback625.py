"""Fresh public consumer qualification, retained fiction; no provider/native IO.

Only Board acting_session and classifier meaning are explicit fictional seams.
Selection, admission, original collector, publications, delivery and reservation
use production methods; no current-response validator is patched or bypassed.
"""
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, collect, ident
from coordinator_runtime import processing, processing_admission, readiness, software
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, collected_capture, collected_task_result, digest, encode, validate_config
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


@contextmanager
def actor(substrate, identity):
    def authenticated(expected):
        if expected != identity:
            raise AssertionError('Fictional authentication mismatch')
        return identity
    with patch.object(substrate, 'acting_session', side_effect=authenticated):
        yield


class Consumers625(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        root = Path(os.environ['COORDINATOR_625_FIXTURES'])
        assert root.is_absolute() and root.is_dir() and not root.is_symlink()
        self.area = Path(tempfile.mkdtemp(prefix=self._testMethodName+'-', dir=root))
        self.config = config_at(self.area)
        self.config['session_storage'] = {'mode': 'producer-owned'}
        self.targets = [self.area / ('consumer'+str(n)+'.json') for n in range(7)]
        for target in self.targets:
            target.write_text(encode({'consumer': target.stem, 'verified': 0}))
        self.link = 'delivery_link' in self._testMethodName
        self.task = 'branch-integrator'
        producer = self.config['tasks'][self.task]
        producer.update(effects='owner-reconcile', sandbox='workspace-write', network=False,
            delivery_required=True, require_package_scope=True, scope_roots=[str(self.area)],
            routine_completion={'kind': 'file-witness', 'targets': list(map(str, self.targets))},
            allowed_handoffs=['Work'], software_handoffs={'Work': ['work-proposer']})
        producer['effect_authority'].update(operations=['read-reports', 'write-role-records'],
            write_roots=list(map(str, self.targets)))
        if not self.link:
            producer['responses']['complete'] = ['work-proposer']
            producer['publish_internal_results'] = True
        self.config['tasks']['work-proposer'].update(delivery_required=True, allowed_handoffs=[])
        shared = self.config['roles']['Work']['board_id']
        for role in self.config['roles'].values():
            role['board_id'] = shared
        self.issuer = self.config['roles']['Work']['owner']
        self.config['software_delegation'] = {'grantor': self.issuer,
            'authority': 'Owned625 fictional independent Work software authority', 'boundary': 'new-journal-only'}
        self.config['delivery'] = {'recipients': {r: {'session': v['owner'], 'profile': v['profile'], 'board_role': v['board_role']}
            for r, v in self.config['roles'].items()}}
        validate_config(self.config)
        substrate = module_at(self.config['board_library'], 'board_store')
        catalog = module_at(self.config['board_library'], 'catalog')
        home = Path(self.config['board_home'])
        with catalog.catalog(home) as cat:
            entry = catalog.create(cat, home, 'owned625', 'Retained625 public consumer fiction', board_id=shared, temporary_test=True)
        with substrate.database(entry['db_path']) as conn:
            substrate.bind_board(conn, shared, initialize=True)
            for role in self.config['roles'].values():
                args = substrate.parser().parse_args(['register', '--session', role['owner'], '--role', role['board_role'],
                    '--profile', role['profile'], '--route', 'managed'])
                with actor(substrate, role['owner']):
                    substrate.register(conn, args)
        self.store = Store(self.config)
        self.addCleanup(self.store.close)  # Close only; preserve all successful and failed fixtures.
        boards = {r: Board(self.config, r) for r in self.config['roles']}
        for role, board in boards.items():
            with actor(board.store, self.issuer):
                grant = board.grant_software(self.store, self.config['software_delegation']['authority'])
            self.store.enroll(role, grant)
            self.store.reconcile_legacy(role, self.config['roles'][role]['owner'],
                {'collector': 'Owned625 fictional original custodian', 'evidence': ['Fresh empty fictional journal'], 'remaining_holds': []})
            with actor(board.store, self.config['roles'][role]['owner']):
                board.revoke(grant['id'])
        with self.store.tx():
            self.store.db.execute('UPDATE enrollments SET intake=0')
        self.boards = {r: processing.ProcessingBoard(self.config, r) for r in self.config['roles']}
        for board in self.boards.values():
            board.runtime = self.store
        procedure = self.area / 'procedure.md'
        procedure.write_text('Verify the seven fictional stages once and conserve protocol uncertainty.\n')
        scope = {'cwd': str(self.area), 'read_roots': [str(self.area)], 'write_roots': list(map(str, self.targets)),
            'procedure': str(procedure), 'resource_evidence': 'Owned625 fictional exact stage authority', 'network': False}
        self.selection = {'basis': processing.basis(self.store, self.boards), 'authority': 'Owned625 fictional finite processing',
            'expires': self.store.clock()+300, 'retained_events': [], 'recover_controls': {}, 'future_intake': True,
            'tasks': list(self.config['tasks']), 'max_starts': 100, 'max_shared_rows': 1000,
            'max_shared_payload_bytes': 1048576, 'max_runtime_rows': 100,
            'software_admission': {'authority': 'Owned625 fictional future Branch execution admission', 'max_packages': 2,
                'scopes': {'owned625': {'submitters': [self.issuer], 'package_prefix': 'owned625-',
                    'task_scopes': {self.task: scope}, 'evidence': 'Owned625 fictional original resource authority'}}},
            'work_coordination': {'authority': 'Owned625 separate fictional Work coordination',
                'tasks': ['work-proposer'], 'source_roles': ['Branch']}}
        with actor(self.boards['Work'].store, self.issuer):
            self.key = processing.select(self.store, self.boards, self.selection)['capability']
        self.store.processing = processing.Access(self.store, self.key, self.boards)
        self.dispatch = Dispatcher(self.store, models=object(), boards=self.boards)
        self.ends = []
        self.addCleanup(self.save)

    def save(self):
        (self.area / 'observations.json').write_text(encode({'owned_transports': self.ends,
            'attempts': self.store.rows('SELECT id,kind,begin,ended,collected,exit,capture,error FROM attempts'),
            'jobs': self.store.rows('SELECT id,task,state,effects,hold_reason FROM jobs'),
            'errors': self.store.rows('SELECT * FROM operational_errors')}))
        self.assertFalse(self.dispatch.active)

    def classify(self):
        while claimed := self.store.claim_classification():
            attempt, source = claimed
            route = self.task if source['id'] == getattr(self, 'source', {}).get('id') else source['allowed_tasks'][0]
            collect(self.store, attempt, {'event_id': source['id'], 'task': route, 'package': source['package'],
                'reason': 'Owned625 explicit fictional classifier meaning'})
            self.store.commit_classification(attempt)
            self.store.ack_state(source['id'], 'internal')
        self.dispatch.receipts()

    async def produce(self, **faults):
        board = self.boards['Branch']
        args = board.store.parser().parse_args(['post', '--session', self.issuer, '--to', board.selected['owner'],
            '--kind', 'proposal', '--topic', 'owned625', '--text', encode({'topic': 'owned625'}), '--ref', 'owned625-package'])
        with board.opened() as conn:
            with actor(board.store, self.issuer):
                seq = board.store.post(conn, args)
            self.source = board._event(conn, {'seq': seq, 'notification_id': None}, board._grant(conn, self.store), self.store)
        self.store.ingest(self.source)
        processing_admission.admit(self.store, self.source['id'])
        self.classify()
        self.job = self.store.reserve()
        self.assertIsNotNone(self.job)
        self.assertEqual(self.job['task'], self.task)
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])
        plan = {'evidence': str(self.store.home/'artifacts'/self.attempt/'causal625.json'),
            'trace': str(self.area/'producer-turns.jsonl'), 'writes': str(self.area/'stage-writes.txt'), **faults}
        if self.link:
            plan['handoffs'] = [{'kind': 'work', 'recipient': 'Work', 'text': 'Consume this exact seven-stage report.',
                'ref': self.source['package'], 'required': 'settled'}]
        path = self.area / 'producer-plan.json'
        path.write_text(encode(plan))
        self.dispatch.models = AppServer(self.config, [sys.executable, str(Path(__file__).with_name('fixture_handback625.py')), str(path)])
        await self.dispatch.execute(self.job['id'], self.attempt)
        self.row = self.store.attempt(self.attempt)
        self.detail = json.loads(self.row['detail'])
        self.ends.append({'attempt': self.attempt, 'END': self.row['exit'], 'ended': self.row['ended'], 'collected': self.row['collected']})
        self.assertEqual(self.row['exit'], 0)
        self.assertIsNotNone(self.row['ended']); self.assertIsNotNone(self.row['collected'])
        self.assertEqual(self.detail['teardown'], 'actual-owned-process-exit-collected')
        self.assertEqual(len((self.area/'stage-writes.txt').read_text().splitlines()), 1)

    async def consume(self, job):
        attempt = self.store.start_job(job['id'], job['token'])
        path = self.area / 'consumer-plan.json'
        path.write_text(encode({'consumer': True, 'trace': str(self.area/'consumer-turns.jsonl')}))
        self.dispatch.models = AppServer(self.config, [sys.executable, str(Path(__file__).with_name('fixture_handback625.py')), str(path)])
        await self.dispatch.execute(job['id'], attempt)
        row = self.store.attempt(attempt)
        self.ends.append({'attempt': attempt, 'END': row['exit'], 'ended': row['ended'], 'collected': row['collected']})
        self.assertEqual(row['exit'], 0); self.assertIsNotNone(row['ended']); self.assertIsNotNone(row['collected'])
        self.assertIsNone(row['error'], row['error'])

    def progress(self):
        self.classify()
        self.dispatch.pump_deliveries()
        self.dispatch.reconcile_completed()
        self.store.complete_events()

    async def finished(self, **faults):
        await self.produce(**faults)
        self.assertTrue(collected_capture(self.row), self.detail)
        self.assertIsNone(self.row['error'], self.row['error'])
        original = self.detail.get('prior_terminal_returns', [{}])[-1].get('typed_return', self.detail.get('prior_turn_result'))
        answer = collected_task_result(self.row)
        self.assertEqual(answer['unknowns'], original['unknowns'])
        self.assertEqual(original['completion']['unknowns'][0]['status'], 'unresolved')
        self.assertEqual(len(readiness.assess(self.store, self.row)['resolved_local_unknowns']), 1)
        publications = self.store.rows('SELECT * FROM file_publications WHERE attempt=?', (self.attempt,))
        self.assertEqual({p['target'] for p in publications}, set(map(str, self.targets)))
        self.assertTrue(all(p['state'] == 'published' for p in publications))
        for target in self.targets:
            self.assertEqual(json.loads(target.read_text()), {'consumer': target.stem, 'verified': 625})
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])
        for _ in range(3): self.progress()
        queue = self.store.one("SELECT * FROM queue WHERE task='work-proposer'")
        self.assertIsNotNone(queue)
        self.assertTrue(processing_admission.permits(self.store, queue))
        self.assertTrue(self.store.processing.task(queue))
        receiving = self.store.event(queue['event'])
        self.assertEqual(bool(receiving.get('source_delivery')), self.link)
        self.assertEqual(bool(receiving.get('source_job')), not self.link)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])
        consumer = self.store.reserve()
        self.assertIsNotNone(consumer)
        self.assertEqual(consumer['task'], 'work-proposer')
        await self.consume(consumer)
        for _ in range(4): self.progress()
        self.assertEqual(self.store.job(consumer['id'])['state'], 'closed')
        self.assertEqual(self.store.job(self.job['id'])['state'], 'closed')
        self.assertTrue(all(o['state'] == 'settled' and o['processed_at'] is not None
            for o in self.store.rows('SELECT * FROM outboxes')))
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])
        self.assertEqual(self.store.attempt(self.attempt), self.row)
        return queue

    async def test_source_job_normal_delivery_and_coordination_finish(self):
        await self.finished()
        self.assertEqual(self.row['capture'], 'conflicting-final')
        self.assertEqual(len(self.detail['terminal_return_evidence']), 3)
        self.assertFalse(self.detail['prior_terminal_returns'][0]['valid_json'])

    async def test_delivery_link_normal_delivery_and_coordination_finish(self):
        await self.finished()
        self.assertEqual(self.row['capture'], 'conflicting-final')

    async def test_legacy_complete_capture_still_finishes(self):
        await self.finished(legacy=True)
        self.assertEqual(self.row['capture'], 'complete')

    async def test_unresolved_local_unknown_remains_held(self):
        await self.produce(unresolved=True)
        self.assertEqual(self.store.job(self.job['id'])['state'], 'held')
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assertEqual(collected_task_result(self.row)['semantic'], 'PARTIAL')

    async def test_competing_current_response_remains_held(self):
        await self.produce(competing=True)
        self.assertFalse(collected_capture(self.row))
        self.assertEqual(self.store.job(self.job['id'])['state'], 'held')
        self.assertNotIn('handback_receipt', self.detail)

    async def test_late_current_response_remains_held(self):
        await self.produce(late=True)
        self.assertFalse(collected_capture(self.row))
        self.assertEqual(self.store.job(self.job['id'])['state'], 'held')

    async def test_missing_tool_closure_remains_held(self):
        await self.produce(missing_close=True)
        self.assertFalse(collected_capture(self.row))
        self.assertEqual(self.store.job(self.job['id'])['state'], 'held')
        self.assertEqual(len((self.area/'producer-turns.jsonl').read_text().splitlines()), 1)

    async def admission_guards(self):
        await self.produce()
        for _ in range(3): self.progress()
        queue = self.store.one("SELECT * FROM queue WHERE task='work-proposer'")
        self.assertIsNotNone(queue)
        self.assertTrue(processing_admission.permits(self.store, queue))
        self.assertIsNone(queue['job'])
        observed_attempt = self.store.attempt
        variants = []
        for name, change in [('missing-END', {'ended': None}), ('uncollected', {'collected': None}),
                ('unknown-END', {'exit': None}), ('failed-END', {'exit': 1}), ('error', {'error': 'original uncertainty'})]:
            variants.append((name, {**self.row, **change}))
        for name in ['old-capture', 'tampered-receipt', 'unknown-tool', 'competing']:
            detail = copy.deepcopy(self.detail)
            if name == 'old-capture':
                detail.pop('handback_receipt'); detail.pop('handback_boundary')
            elif name == 'tampered-receipt':
                detail['handback_receipt']['result_hash'] = '0'*64
            elif name == 'unknown-tool':
                detail['tool_completion']['complete'] = False
            else:
                rival = copy.deepcopy(detail['terminal_return_evidence'][-1])
                rival['item'] = 'extra-rival-625'; rival['typed_return']['summary'] = 'Competing current response'
                detail['terminal_return_evidence'].append(rival)
            variants.append((name, {**self.row, 'detail': encode(detail)}))
        for name, row in variants:
            with self.subTest(ancestry=name), patch.object(self.store, 'attempt',
                    side_effect=lambda key: row if key == self.attempt else observed_attempt(key)):
                try: allowed = processing_admission.permits(self.store, queue)
                except Refusal: allowed = False
                self.assertFalse(allowed)
        for changed in [{**queue, 'package': 'foreign-package'}, {**queue, 'task': 'work-integrator'}]:
            self.assertFalse(processing_admission.permits(self.store, changed))
        observed_job = self.store.job
        members = json.loads(self.store.job(self.job['id'])['members'])
        members.append({**members[0], 'hash': 'bad-later-member'})
        with patch.object(self.store, 'job', side_effect=lambda key, *args:
                {**observed_job(key, *args), 'members': encode(members)} if key == self.job['id'] else observed_job(key, *args)):
            self.assertFalse(processing_admission.permits(self.store, queue))
        self.store.set_hold(self.source['id'], 'Owned625 injected original source hold; no automatic clearance')
        self.assertFalse(processing_admission.permits(self.store, queue))
        self.assertIsNone(self.store.reserve())
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])

    async def test_source_job_admission_guards_preserve_ancestry_and_unknowns(self):
        await self.admission_guards()

    async def test_delivery_link_admission_guards_preserve_ancestry_and_unknowns(self):
        await self.admission_guards()

    async def test_completion_receipt_effect_payload_and_transport_guards(self):
        await self.produce()
        self.classify()
        board = self.boards['Branch']
        outbox = self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Branch'", (self.job['id'],))
        board.post_delivery(self.store, outbox)
        self.assertIsNone(board.delivery_status(outbox['id'])['processing'])
        actual_attempt = self.store.attempt
        detail = copy.deepcopy(self.detail); detail.pop('handback_receipt')
        bad = {**self.row, 'detail': encode(detail)}
        with patch.object(self.store, 'attempt', side_effect=lambda key: bad if key == self.attempt else actual_attempt(key)):
            with self.assertRaises(Refusal): board.complete_own_delivery(self.store, outbox)
        actual_job = self.store.job
        for change in [{'effects': 'unknown'}, {'hold_reason': 'Owned625 actual effect uncertainty'}]:
            with self.subTest(job_guard=change), patch.object(self.store, 'job',
                    side_effect=lambda key, *args: {**actual_job(key, *args), **change}):
                self.assertIsNone(board.complete_own_delivery(self.store, outbox))
        with self.assertRaisesRegex(Refusal, 'exact service/role/source grant'):
            board.complete_own_delivery(self.store, {**outbox, 'payload': '{}'})
        with board.opened() as conn:
            conn.execute('UPDATE coordinator_deliveries_v1 SET transport_started=1 WHERE id=?', (outbox['id'],))
        with self.assertRaisesRegex(Refusal, 'transport consumer'):
            board.complete_own_delivery(self.store, outbox)
        self.assertIsNone(board.delivery_status(outbox['id'])['processing'])
        self.assertEqual(self.store.job(self.job['id'])['state'], 'awaiting-delivery')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])

    async def test_revoked_processing_authority_cannot_consume_valid_response(self):
        await self.produce()
        self.classify()
        board = self.boards['Branch']
        outbox = self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Branch'", (self.job['id'],))
        board.post_delivery(self.store, outbox)
        with actor(self.boards['Work'].store, self.issuer):
            processing.revoke(self.store, self.boards, self.key)
        self.assertIsNone(board.complete_own_delivery(self.store, outbox))
        self.assertIsNone(board.delivery_status(outbox['id'])['processing'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])
