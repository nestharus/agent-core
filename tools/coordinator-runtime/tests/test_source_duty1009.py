"""Decision1009: fictional protocol, real Executor/resource/receiver behavior.

The seven legacy contrasts run unchanged on an independently supported source:
the existing explicit-null software path, pinned public caller, and disjoint
read ceiling from985. Original packaged /usr/bin/false tests remain untouched.
No provider, live journal, private store or retention removal is exercised.
"""
import asyncio
import copy
import json
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_native_footprint985 import ActiveSource985
import test_native_footprint985 as active_fixture
from test_native_return820 import NativeReturn
from test_native_preflight826 import Preflight
from test_native_reacquisition836 import Reacquisition836
from _receiving485_fixtures import FictionalNativeTransport
from coordinator_runtime import resource_scopes, reviews, prospective
from coordinator_runtime.contracts import Refusal, digest, encode


class SupportedReturn1009(ActiveSource985):
    # The existing test method bodies and their negative oracles are reused.
    test_whole_return = NativeReturn.test_whole_native_return_and_real_integrator_transport
    test_stale_held_uncollected_forged_orphan = NativeReturn.test_stale_held_uncollected_forged_method_and_orphan_refuse
    test_orphan_before_bodies = Preflight.test_orphan_lease_refuses_before_all_protected_reads
    test_mapped_root_before_bodies = Preflight.test_mapped_root_refuses_before_all_protected_reads
    check_physical_traps = Preflight.check_physical_traps


class SupportedRetry1009(SupportedReturn1009):
    def configure_fixture(self):
        super().configure_fixture()
        self.config['local_integration']['tasks'].pop('reviews-integrator')

    def configure_selection(self, selected):
        super().configure_selection(selected)
        selected['metadata_lookup']['tasks'].remove('reviews-integrator')

    frozen = Reacquisition836.frozen
    conflict = Reacquisition836.conflict
    traps = Reacquisition836.traps
    test_frozen_retry = Reacquisition836.test_public_frozen_retry_after_pool_failure_refuses_before_body
    test_async_preparation = Reacquisition836.test_async_preparation_after_start_refuses_before_body
    test_spawned_preparation = Reacquisition836.test_spawned_preparation_after_start_refuses_before_body
    test_resume = Reacquisition836.test_frozen_resume_without_conflict_preserves_source


class Unsupported1009(NativeReturn):
    def test_original_packaged_false_caller_is_still_opaque(self):
        self.source()
        with self.assertRaisesRegex(Refusal, 'standalone'):
            resource_scopes.original_modes(self.store, dict(id=self.original['id'], task=self.original['task']))
        self.assertTrue(resource_scopes.blocked(self.store, self.row))


class ClosingTransport(FictionalNativeTransport):
    async def call(self, runtime, attempt, policy, context, directory, text, commands, **options):
        if not options.get('close'):
            return await super().call(runtime, attempt, policy, context, directory, text, commands, **options)
        # An explicit fictional original close through production Executor.close.
        # No physical/native command is invoked and no output is removed.
        directory.mkdir(parents=True)
        receipt = dict(class_='closed', run=context['run'], physical_close=True, root='ended',
            account_errors=[], collection=dict(eof=True, errors=[]),
            front_door_terminal=dict(run=context['run'], entry_status=87, exit=87,
                collection_errors=[], killed=False, retire=dict(ok=True, stop='closed'),
                live=dict(backlog_dropped_total=0)),
            owner_terminal=dict(status='closed'),
            async_=dict(errors=[], unsettled=0, undelivered=[]))
        receipt['class'] = receipt.pop('class_')
        receipt['async'] = receipt.pop('async_')
        return 0, receipt, None


class GatedAnsweredTransport(FictionalNativeTransport):
    async def call(self, *args, **kwargs):
        runtime, attempt = args[:2]
        with runtime.tx():
            runtime.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?", (attempt,))
        answer = await super().call(*args, **kwargs)
        self.pending = asyncio.Future()
        self.started = True
        await self.pending
        return answer


class Lifetime1009(SupportedReturn1009):
    def test_native_preparation_without_call_map_stays_unknown_after_collection(self):
        self.init_native()
        prospective.select(self.store, self.config['roles']['Work']['owner'], dict(
            configuration=digest(self.config), authority='Fictional original failed preparation authority',
            expires=self.store.clock()+600, processing_capability=self.key,
            grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={n:dict(task_hash=digest(t),software_handoffs={},ordinary_effects=False)
                   for n,t in self.config['tasks'].items()}))
        event = self.source_event()
        self.initial[event['id']] = 'reviews-proposer'
        asyncio.run(self.phase('schedule_classifications'))
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        with patch.object(reviews, 'material', side_effect=Refusal('fictional original material unavailable')):
            asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        original = self.store.job(job['id'])
        self.assertEqual((original['state'], original['effects']), ('held', 'none'))
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])
        self.assertEqual(self.store.rows('SELECT attempt FROM review_calls'), [])
        with self.assertRaises(Refusal):
            resource_scopes.original_modes(self.store, dict(id=job['id'], task=job['task']))
        self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))

    def returned(self):
        self.source()
        self.identity = dict(id=self.original['id'], task=self.original['task'])
        self.history = Path(self.store.one('SELECT path FROM review_history_commits')['path'])
        self.facade = self.store.home/'review-inputs'/digest(self.component889)/'material.json'
        return self.modes()

    def physical_close(self):
        transport = ClosingTransport()
        transport.run = self.transport.run
        self.dispatch.reviews.transport = transport
        policy = self.store.processing.current()[1]['service']['reviews']['reviews-proposer']
        asyncio.run(self.dispatch.reviews.close(self.component889, policy))

    def test_one_original_active_architecture_answered_continuing_context(self):
        with patch.object(active_fixture, 'SuspendedTransport', GatedAnsweredTransport), self.active():
            history = Path(self.store.one('SELECT json_extract(packet,\'$.history\') AS path FROM review_calls')['path'])
            self.assertIn(history, self.modes()[1])
            first = self.transport.pending
            first.set_result(None)
            async def until_second():
                for _ in range(100):
                    await asyncio.sleep(0)
                    if self.transport.pending is not first:
                        return
                    if self.source_running.done():
                        await self.source_running
                self.fail('second original turn not reached')
            self.source_loop.run_until_complete(until_second())
            self.assertIn(history, self.modes()[1])
            self.assertEqual(len(self.transport.calls), 2)
            self.transport.pending.set_result(None)
            self.source_loop.run_until_complete(self.source_running)
            attempt = self.store.attempt(self.attempt_id)
            self.assertEqual((attempt['state'], attempt['exit'], attempt['capture']), ('collected', 0, 'complete'))
            self.assertNotIn(history, self.modes()[1])
            context = self.store.one('SELECT state,run FROM review_contexts')
            self.assertEqual(context, dict(state='live', run=self.transport.run))
            self.assertIn(self.repo, self.modes()[0])
            self.assertFalse(resource_scopes.blocked(self.store, self.candidate('QA')))

    def test_answer_reconciles_executor_history_but_holds_native_and_original_ceiling(self):
        reads, writes, staging = self.returned()
        self.assertIn(self.repo, reads)
        self.assertIn(self.method, reads)
        self.assertNotIn(self.history, writes)
        self.assertIn(self.history, reads)
        self.assertIn(self.facade.with_suffix('.cursor'), writes)
        self.assertEqual(staging, [self.store.home/'artifacts'/self.a['id']])
        for role in ('QA', 'Work', 'Branch'):
            self.assertFalse(resource_scopes.blocked(self.store, self.candidate(role)))
        task = copy.deepcopy(self.config['tasks']['work-integrator'])
        task.pop('routine_completion', None)
        task['effect_authority']['read_roots'] = [str(self.facade)]
        self.assertTrue(resource_scopes.blocked(self.store, self.candidate(), task))

    def test_pending_history_publication_and_orphan_survive_apparent_completion(self):
        self.returned()
        self.physical_close()
        self.store.db.execute('SAVEPOINT tails1009')
        try:
            self.store.db.execute("UPDATE review_history_commits SET state='prepared'")
            self.assertIn(self.history, self.modes()[1])
            self.store.db.execute('ROLLBACK TO tails1009')
            self.store.db.execute("UPDATE review_history_commits SET after_hash='unknown'")
            self.assertIn(self.history, self.modes()[1])
            self.store.db.execute('ROLLBACK TO tails1009')
            pending = str(self.independent/'pending-publication')
            self.store.db.execute("INSERT INTO file_publications(attempt,target,temp,state) VALUES(?,?,?,'prepared')",
                (self.a['id'], str(self.catalog), pending))
            self.assertIn(Path(pending), self.modes()[1])
            self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
            self.store.db.execute('ROLLBACK TO tails1009')
            self.store.db.execute("UPDATE review_history_commits SET state='prepared'")
            self.assertIn(self.history, self.modes()[1])
            self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped1009','orphan1009')")
            self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))
        finally:
            self.store.db.execute('ROLLBACK TO tails1009')
            self.store.db.execute('RELEASE tails1009')

    def test_closed_label_without_original_receipt_is_not_release(self):
        self.returned()
        self.store.db.execute("UPDATE review_contexts SET state='closed',closed_at=?", (self.store.clock(),))
        with self.assertRaisesRegex(Refusal, 'physical close'):
            self.modes()
        self.assertTrue(resource_scopes.blocked(self.store, self.candidate()))

    def test_genuine_close_releases_only_settled_native_resources(self):
        self.returned()
        old_call = self.store.one('SELECT packet,answer FROM review_calls')
        self.physical_close()
        self.assertEqual(self.modes(), ([], [], []))
        self.assertFalse(resource_scopes.blocked(self.store, self.candidate()))
        self.assertEqual(old_call, self.store.one('SELECT packet,answer FROM review_calls'))
        self.assertTrue(self.store.one('SELECT legacy_hold FROM enrollments WHERE role=\'Reviews\'')['legacy_hold'])
        self.assertIsNotNone(self.store.job(self.original['id'])['response'])
        # Resource release grants no Source success, adoption or renewal.
        self.assertTrue(self.record['unbounded'])

    def test_root_absent_close_is_interrupted_unknown_and_fully_held(self):
        self.returned()
        class UnknownClose(ClosingTransport):
            async def call(inner, runtime, attempt, policy, context, directory, text, commands, **options):
                directory.mkdir(parents=True)
                return 11, dict(run=context['run'], **{'class': 'root-absent'}), None
        self.dispatch.reviews.transport = UnknownClose()
        policy = self.store.processing.current()[1]['service']['reviews']['reviews-proposer']
        with self.assertRaisesRegex(Refusal, 'incomplete'):
            asyncio.run(self.dispatch.reviews.close(self.component889, policy))
        self.assertEqual(self.store.one('SELECT state FROM review_contexts')['state'], 'interrupted')
        self.assertEqual(self.store.job(self.original['id'])['effects'], 'none')
        self.assertIn(self.history, self.modes()[1])
        self.assertIn(self.facade, self.modes()[1])
        self.assertTrue(self.modes()[2])

    def test_protocol_damage_or_unknown_async_account_never_releases(self):
        self.returned()
        for path, value in [('$.receipt.turn.turn_end.child', None),
                            ('$.receipt.transport.attached.backlog_dropped_total', 1),
                            ('$.actual_END', False)]:
            with self.subTest(path=path):
                self.store.db.execute('SAVEPOINT protocol1009')
                try:
                    turns = json.loads(self.store.one('SELECT receipt FROM review_calls')['receipt'])
                    target = turns[-1]
                    keys = path[2:].split('.')
                    for key in keys[:-1]: target = target[key]
                    target[keys[-1]] = value
                    self.store.db.execute('UPDATE review_calls SET receipt=?', (encode(turns),))
                    self.assertIn(self.history, self.modes()[1])
                finally:
                    self.store.db.execute('ROLLBACK TO protocol1009')
                    self.store.db.execute('RELEASE protocol1009')
        self.physical_close()
        turns = json.loads(self.store.one('SELECT receipt FROM review_calls')['receipt'])
        turns[-1]['receipt']['async']['unsettled'] = 1
        self.store.db.execute('UPDATE review_calls SET receipt=?', (encode(turns),))
        with self.assertRaisesRegex(Refusal, 'physical close'):
            self.modes()


class Operand1009(unittest.TestCase):
    def traps(self):
        stack = ExitStack()
        for name in ('stat', 'lstat', 'is_symlink', 'resolve', 'exists', 'read_bytes', 'read_text'):
            stack.enter_context(patch.object(Path, name, side_effect=AssertionError('metadata/body before lexical refusal')))
        return stack

    def test_root_both_operands_double_root_ancestry_before_metadata(self):
        base = '/fixtures/synthetic-operand1009'
        cases = [(base+'/held', base+'/held'), (base, base+'/held'), (base+'/held/child', base+'/held'),
                 ('/'+base+'/held', base+'/held'), (base+'/held', '/'+base+'/held'),
                 (base+'/allowed', '/'+base+'/held'), ('/'+base+'/allowed', base+'/held')]
        for requested, excluded in cases:
            for metadata in (True, False):
                with self.subTest(requested=requested, excluded=excluded, metadata=metadata), self.traps():
                    with self.assertRaises(Refusal):
                        resource_scopes.root(requested, [excluded], metadata=metadata)

    def test_overlap_double_root_operands_before_identity(self):
        for left, right in [('//fixtures/synthetic-operand1009/a', '/fixtures/synthetic-operand1009/b'),
                            ('/fixtures/synthetic-operand1009/a', '//fixtures/synthetic-operand1009/b')]:
            with self.subTest(left=left), self.traps(), self.assertRaises(Refusal):
                resource_scopes.overlaps(Path(left), Path(right))

    def test_frozen_original_map_refuses_before_scoped_metadata(self):
        for where in ('cwd', 'read', 'exclusion', 'scope-root'):
            values = ['/fixtures/synthetic-operand1009/allowed', 'read-only', 'none', False,
                      None, False, ['/fixtures/synthetic-operand1009'], None, [], [], [],
                      ['/fixtures/synthetic-operand1009/allowed'], [], ['read-reports']]
            if where == 'cwd': values[0] = '//fixtures/synthetic-operand1009/allowed'
            if where == 'read': values[11] = ['//fixtures/synthetic-operand1009/allowed']
            if where == 'exclusion': values[8] = ['//fixtures/synthetic-operand1009/held']
            if where == 'scope-root': values[6] = ['//fixtures/synthetic-operand1009']
            frozen = dict(access=encode(values), completion=None, targets=None, scope=None,
                          ordinary=None, evidence=False)
            runtime = SimpleNamespace(db=SimpleNamespace(in_transaction=True),
                config=dict(artifact_exclusions=[], tasks={}), one=lambda *args: frozen)
            with self.subTest(where=where), self.traps(), \
                 patch.object(resource_scopes, 'scoped_task', side_effect=AssertionError('scoped metadata boundary crossed')):
                with self.assertRaises(Refusal):
                    resource_scopes.original_modes(runtime, dict(id='synthetic-original', task='example'))

    def test_initial_complete_map_lexical_before_first_metadata(self):
        task = dict(cwd='/fixtures/synthetic-operand1009/allowed', sandbox='read-only', effects='none',
            network=False, effect_authority=dict(operations=['read-reports'], write_roots=[],
                read_roots=['/fixtures/synthetic-operand1009/allowed', '//fixtures/synthetic-operand1009/held']))
        with self.traps(), self.assertRaises(Refusal):
            resource_scopes.access_modes(task, ['/fixtures/synthetic-operand1009/held'])

    def test_narrow_admission_does_not_acquire_excluded_ceiling_descendants(self):
        task = dict(cwd='/fixtures/synthetic-operand1009', require_package_scope=True,
            effect_authority=dict(read_roots=['/fixtures/synthetic-operand1009'], write_roots=[]),
            scope_roots=['/fixtures/synthetic-operand1009'])
        scope = dict(cwd='/fixtures/synthetic-operand1009/allowed',
                     read_roots=['/fixtures/synthetic-operand1009/allowed'], write_roots=[])
        runtime = SimpleNamespace(config=dict(tasks=dict(example=task),
            artifact_exclusions=['/fixtures/synthetic-operand1009/held']))
        with self.traps():
            self.assertFalse(resource_scopes.scope_excluded(runtime, 'example',
                dict(receipt=encode(dict(task_scopes=dict(example=scope))))))

    def test_initial_scope_and_exclusion_operands_are_lexical(self):
        task = dict(cwd='/fixtures/synthetic-operand1009/allowed', require_package_scope=True,
            effect_authority=dict(read_roots=[], write_roots=[]), scope_roots=['/fixtures/synthetic-operand1009'])
        for where in ('artifact', 'scope', 'requested', 'ceiling'):
            current = copy.deepcopy(task)
            excluded = ['/fixtures/synthetic-operand1009/held']
            scope = dict(cwd='/fixtures/synthetic-operand1009/held')
            if where == 'artifact': excluded = ['//fixtures/synthetic-operand1009/held']
            if where == 'scope': current['scope_exclusions'] = ['//fixtures/synthetic-operand1009/held']
            if where == 'requested': scope['cwd'] = '//fixtures/synthetic-operand1009/held'
            if where == 'ceiling': current['scope_roots'] = ['//fixtures/synthetic-operand1009']
            runtime = SimpleNamespace(config=dict(tasks=dict(example=current), artifact_exclusions=excluded))
            with self.subTest(where=where), self.traps():
                try:
                    self.assertTrue(resource_scopes.scope_excluded(runtime, 'example', dict(receipt=encode(dict(task_scopes=dict(example=scope))))))
                except Refusal:
                    pass


def load_tests(loader, tests, pattern):
    # Deliberate exact selection avoids inherited tests being run repeatedly.
    return unittest.TestSuite(cls(n) for cls in (SupportedReturn1009, SupportedRetry1009, Unsupported1009, Lifetime1009, Operand1009)
                              for n in cls.__dict__ if n.startswith('test_'))
