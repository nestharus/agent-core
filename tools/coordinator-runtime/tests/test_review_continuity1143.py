"""Owned protocol fiction. No opaque provider, native root or method completion.

The route executor is exercised through its real Store/Executor boundaries and
real harmless caller subprocesses. Provider responses remain explicit seams.
"""
import asyncio
from contextlib import nullcontext
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from coordinator_runtime import reviews
from coordinator_runtime.contracts import Refusal, encode
from coordinator_runtime.execution_pool import ExecutionPool
import test_oneoff1077 as previous

OPAQUE = {'model': 'gpt-xhigh', 'provider': 'opaque', 'effort': 'opaque'}


class OpaqueBoundary(unittest.TestCase):
    def setUp(self):
        self.f = previous.Recovery(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    @staticmethod
    def select_owner(store):
        store.config['tasks']['reviews-proposer'].update(execution='owner', binding=dict(OPAQUE))

    def test_selection_refuses_before_caller_or_method_acquisition(self):
        runtime = SimpleNamespace(config={'tasks': {'source': {
            'role': 'Reviews', 'phase': 'proposer', 'effects': 'none',
            'execution': 'owner', 'binding': dict(OPAQUE)}}})
        with patch.object(reviews, 'caller_current', side_effect=AssertionError('caller acquired')), \
             patch.object(reviews, 'method_files', side_effect=AssertionError('method acquired')):
            with self.assertRaisesRegex(Refusal, 'opaque gpt-xhigh'):
                reviews.validate(runtime, {'source': {}})

    def test_opaque_binding_without_owner_marker_is_not_a_concrete_route_binding(self):
        with self.assertRaisesRegex(Refusal, 'opaque gpt-xhigh'):
            reviews.route_binding({'binding': dict(OPAQUE)})
        self.assertEqual(reviews.route_binding({'binding': dict(reviews.BINDING)}), reviews.BINDING)

    def test_store_refuses_before_allocation_and_preserves_reserved_job(self):
        store, runtime, job, packet, policy, acquired, transport = self.f.native_fixture()
        self.select_owner(store)
        before = store.rows('SELECT * FROM attempts')
        original = copy.deepcopy(store.job(job['id']))
        with patch.object(store, '_attempt', side_effect=AssertionError('new allocation')):
            with self.assertRaisesRegex(Refusal, 'opaque gpt-xhigh'):
                store.start_job(job['id'], job['token'])
        self.assertEqual(store.job(job['id']), original)
        self.assertEqual(store.rows('SELECT * FROM attempts'), before)
        self.assertEqual(store.config['tasks']['reviews-proposer']['binding'], OPAQUE)
        self.assertEqual(transport.inputs, 0)

    def test_executor_rechecks_task_before_material_or_fake_transport(self):
        store, runtime, job, packet, policy, acquired, transport = self.f.native_fixture()
        attempt = store.start_job(job['id'], job['token'])
        self.select_owner(store)
        with patch.object(reviews, 'material', side_effect=AssertionError('source acquired')):
            with self.assertRaisesRegex(Refusal, 'opaque gpt-xhigh'):
                asyncio.run(runtime.reviews.execute(store.job(job['id']), attempt, policy, packet))
        self.assertEqual(transport.inputs, 0)
        self.assertIsNone(store.one('SELECT * FROM review_calls'))

    def test_rewritten_historical_binding_cannot_certify_selected_opaque_task(self):
        store, runtime, job, attempt, policy, transport = self.f.run_native_selected()
        original = store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,))
        self.assertEqual(json.loads(store.attempt(attempt)['binding']), reviews.BINDING)
        self.select_owner(store)
        with self.assertRaisesRegex(Refusal, 'opaque gpt-xhigh'):
            reviews.collected_proof(store, store.job(job['id']), store.attempt(attempt))
        self.assertEqual(store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,)), original)
        self.assertEqual(len(transport.answers), 2)

    def test_unselected_owner_report_path_is_not_a_route_call(self):
        store, runtime, job, packet, policy, acquired, transport = self.f.native_fixture()
        self.select_owner(store)
        store.processing.review_task = lambda task: False
        attempt = store.start_job(job['id'], job['token'])
        self.assertEqual(json.loads(store.attempt(attempt)['binding']), OPAQUE)
        self.assertEqual(transport.inputs, 0)
        self.assertIsNone(store.attempt(attempt)['begin'])


class NativeContinuity(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='native1143-', dir=os.environ['ONEOFF1077_FIXTURES']))
        routes = self.home/'pool.toml'
        routes.write_text('[rotation]\nstate_dir='+json.dumps(str(self.home/'pool'))+
                          '\n[providers.codex]\npool=[]\nmanual_profiles='+
                          json.dumps(['.codex', '.codex2', '.codex3', '.codex4', '.codex5'])+'\n')
        config = {'profiles': ['.codex', '.codex2', '.codex3', '.codex4', '.codex5'],
                  'execution_pool_routes': str(routes), 'deadlines': {'bind': 1, 'shutdown': 1},
                  'limits': {'max_result_bytes': 65536}}
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE review_calls(attempt TEXT,state TEXT)')
        self.db.execute("INSERT INTO review_calls VALUES('owned-attempt','prepared')")
        self.ends = []
        self.runtime = SimpleNamespace(config=config, controller='fictional-collector',
            execution_pool=ExecutionPool(config), db=self.db, tx=nullcontext,
            clock=lambda: 100., admit_artifact_write=Mock(), authorize_launch=Mock(),
            attempt=lambda attempt: {'begin': 1},
            record_original_end=lambda attempt, observation: self.ends.append((attempt, observation)))
        # This caller deliberately produces an incomplete public receipt. END0
        # proves collection of this harmless Python process, never a live root.
        caller = self.home/'caller.py'
        caller.write_text('#!/usr/bin/python3\nimport json,pathlib,sys\n'
            'out=pathlib.Path(sys.argv[sys.argv.index("--out")+1]);out.mkdir()\n'
            '(out/"result.json").write_text(json.dumps({"class":"incomplete","fixture":True}))\n'
            'print("owned harmless caller",flush=True)\n')
        caller.chmod(0o700)
        handle = self.home/'declared-handle'
        handle.write_text(encode({'v': 1, 'uid': os.getuid(), 'run': 'fictional-root',
            'socket': '/fixtures/not-a-real-socket', 'token': 'fictional-not-a-credential'}))
        handle.chmod(0o600)
        self.context = {'profile': '.codex2', 'route': 'fictional-two', 'handle': str(handle),
                        'run': 'fictional-root', 'created': 100.}
        self.policy = {'caller': str(caller), 'caller_sha256': reviews.sha(caller.read_bytes()),
                       'routes': {'.codex2': 'fictional-two'}, 'deadline': 1}
        self.native = reviews.Native()

    async def call(self, name, **kwargs):
        return await self.native.call(self.runtime, 'owned-attempt', self.policy, self.context,
                                      self.home/name, 'fictional input', [], **kwargs)

    async def test_empty_future_pool_does_not_move_or_block_owned_continuation(self):
        original = copy.deepcopy(self.context)
        with patch.object(self.runtime.execution_pool, 'admission',
                          side_effect=AssertionError('continuation allocated as new work')):
            code, receipt, answer = await self.call('continuation')
        self.assertEqual(code, 0)
        self.assertEqual(receipt['class'], 'incomplete')
        self.assertIsNone(answer)
        self.assertEqual(self.context, original)
        original = json.loads((self.home/'continuation/original.json').read_text())
        self.assertEqual(original['actual_END'], 0)
        self.assertTrue(original['capture_complete'])
        self.assertIn('--root', original['argv'])
        self.assertIn(self.context['handle'], original['argv'])
        self.assertNotIn('--route', original['argv'])
        self.assertEqual(len(self.ends), 1)
        self.assertEqual(self.native.original_status(), [])

    async def test_empty_future_pool_still_blocks_new_root_before_spawn(self):
        with patch('coordinator_runtime.reviews.asyncio.create_subprocess_exec',
                   side_effect=AssertionError('new root launched')):
            with self.assertRaisesRegex(Refusal, 'empty'):
                await self.call('opening', opening=True)
        self.assertEqual(self.ends, [])

    async def test_new_allocations_use_all_five_then_continuation_keeps_original(self):
        profiles = self.runtime.config['profiles']
        self.runtime.execution_pool.pool.set(profiles)
        self.policy['routes'] = {p: 'fictional-route-'+str(i) for i, p in enumerate(profiles)}
        observed = []
        for index in range(5):
            chosen = self.runtime.execution_pool.allocate()['profile']
            observed.append(chosen)
            self.context.update(profile=chosen, route=self.policy['routes'][chosen])
            code, receipt, answer = await self.call('new-'+str(index), opening=True)
            self.assertEqual(code, 0)
            self.assertEqual(receipt['class'], 'incomplete')
        self.assertEqual(observed, profiles)
        # Keep the first owned account; future allocation can now choose only5.
        self.context.update(profile=profiles[0], route=self.policy['routes'][profiles[0]])
        self.runtime.execution_pool.pool.set([profiles[-1]])
        turn = self.runtime.execution_pool.pool.status()['turn']
        code, receipt, answer = await self.call('same-original')
        self.assertEqual(code, 0)
        self.assertEqual(self.context['profile'], profiles[0])
        self.assertEqual(self.runtime.execution_pool.pool.status()['turn'], turn)
        self.assertEqual(self.runtime.execution_pool.allocate()['profile'], profiles[-1])
        self.assertEqual(len(self.ends), 6)

    async def test_revoked_current_authority_still_blocks_continuation(self):
        self.runtime.authorize_launch.side_effect = Refusal('fictional revoked grant')
        with patch('coordinator_runtime.reviews.asyncio.create_subprocess_exec',
                   side_effect=AssertionError('revoked input launched')):
            with self.assertRaisesRegex(Refusal, 'revoked grant'):
                await self.call('revoked')
        self.assertEqual(self.ends, [])

    async def test_route_change_and_original_handle_change_refuse_without_spawn(self):
        for changed in ('route', 'run'):
            with self.subTest(changed=changed):
                value = self.context[changed]
                self.context[changed] = 'different-fixture-identity'
                with patch('coordinator_runtime.reviews.asyncio.create_subprocess_exec',
                           side_effect=AssertionError('changed context launched')):
                    with self.assertRaises(Refusal):
                        await self.call('changed-'+changed)
                self.context[changed] = value
        self.assertEqual(self.ends, [])

    async def test_elapsed_root_lifetime_does_not_restart_with_new_pool_turn(self):
        self.runtime.clock = lambda: 102.
        with patch('coordinator_runtime.reviews.asyncio.create_subprocess_exec',
                   side_effect=AssertionError('expired root launched')):
            with self.assertRaisesRegex(Refusal, 'whole-root lifetime elapsed'):
                await self.call('elapsed')
        self.assertEqual(self.ends, [])

    async def test_close_drains_ownership_with_pool_empty_but_does_not_fabricate_closure(self):
        self.runtime.authorize_launch.side_effect = AssertionError('close admitted new task')
        code, receipt, answer = await self.call('close', close=True)
        self.assertEqual(code, 0)
        self.assertFalse(reviews.closed(code, receipt, self.context['run']))
        self.assertEqual(len(self.ends), 1)
        original = json.loads((self.home/'close/original.json').read_text())
        self.assertIn('--close', original['argv'])
        self.assertNotIn('--prompt-file', original['argv'])
