"""DECISION1157 mechanism controls; provider answers here are explicit fiction.

Real subprocess END, capture, ownership and controller routes are exercised.
Only the separately selected public qualification can supply opaque evidence.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime import reviews, opaque_review
from coordinator_runtime.appserver import Originals
from coordinator_runtime.contracts import Refusal, encode
import test_oneoff1077 as previous

THREAD = '00000000-0000-4000-8000-000000001157'  # fictional, never provider proof


def public_module():
    return opaque_review.launcher({'launcher_sha256': reviews.sha(opaque_review.launcher_path().read_bytes())})


class Material(unittest.TestCase):
    def setUp(self):
        self.module = public_module()
        self.home = Path(tempfile.mkdtemp(prefix='material1157-', dir=os.environ['ONEOFF1077_FIXTURES']))

    def test_export_uses_generated_names_and_preserves_complete_bytes(self):
        body = 'exact source α\n'.encode()
        items = [('untrusted label: ../../not-an-operand', body), ('history', b'')]
        manifest = self.module.export(self.home/'material', items)
        self.assertEqual((self.home/'material/0000.txt').read_bytes(), body)
        self.assertEqual(manifest[0]['bytes'], len(body))
        self.assertEqual(manifest[0]['sha256'], reviews.sha(body))
        self.assertEqual(len(manifest), 2)
        self.assertEqual((self.home/'material/0000.txt').stat().st_mode & 0o222, 0)

    def test_alias_parent_and_nontext_are_refused(self):
        (self.home/'alias').symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(self.module.ReviewRefusal, 'alias'):
            self.module.positive_directory(self.home/'alias')
        with self.assertRaises(UnicodeError):
            self.module.export(self.home/'nontext', [('raw forbidden test fixture', b'\xff')])

    def test_argv_preserves_opaque_reference_and_separates_permissions_from_legacy_sandbox(self):
        argv = self.module.command('.codex4', self.home, self.home/'material', THREAD)
        self.assertEqual(argv[argv.index('--model')+1], 'gpt-xhigh')
        self.assertIn('--ignore-user-config', argv)
        self.assertIn('--ignore-rules', argv)
        self.assertIn('--no-daemon', argv)
        self.assertEqual(argv[argv.index('resume')+1], THREAD)
        self.assertIn('approval_policy="never"', argv)
        self.assertIn('permissions.review-material.network.enabled=false', argv)
        self.assertTrue(any(':root' in v and 'deny' in v and ':minimal' in v for v in argv))
        self.assertNotIn('--sandbox', argv)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', argv)
        self.assertNotIn('--ephemeral', argv)  # continuation needs its own retained history
        self.assertNotIn('--last', argv)
        self.assertNotIn('-o', argv)  # one bounded event stream, no unbounded final sidecar
        self.assertFalse(any('model_reasoning_effort' in v for v in argv))

    def test_changed_launcher_and_unselected_or_concrete_binding_refuse(self):
        with self.assertRaisesRegex(Refusal, 'launcher changed'):
            opaque_review.launcher({'launcher_sha256': '0'*64})
        with self.assertRaises(Refusal):
            opaque_review.binding({'binding': reviews.BINDING})
        with self.assertRaises(Refusal):
            reviews.execution_binding({'execution': 'owner', 'binding': opaque_review.BINDING}, {})

    def test_situated_prompt_keeps_challengeable_context_without_expected_answers(self):
        acquired = {'situation': {'actors': 'operators', 'environment': 'owned fixture',
            'goals': 'preserve recoverable work', 'conflicts': 'latency and attention',
            'constraints': 'read-only positive source'}, 'commands': ['secret-not-input']}
        prompt = opaque_review.prompt({}, acquired)
        self.assertIn('preserve recoverable work', prompt)
        self.assertIn('challenge', prompt)
        self.assertNotIn('secret-not-input', prompt)
        self.assertNotIn('Goals/acceptance/repair hints are deliberately outside', prompt)


class SharedOwnership(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = public_module()
        self.home = Path(tempfile.mkdtemp(prefix='owned1157-', dir=os.environ['ONEOFF1077_FIXTURES']))
        self.originals = Originals()
        self.context = self.module.Context(self.home/'context', '.codex4', 'fictional-collector', 30, self.originals, executable='/usr/bin/false')
        self.ends, self.argv = [], []
        self.actual_spawn = asyncio.create_subprocess_exec
        self.child_body = (
            'import json,sys\nsys.stdin.read()\n'
            f'print(json.dumps({{"type":"thread.started","thread_id":{THREAD!r}}}),flush=True)\n'
            'print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"fictional answer"}}),flush=True)\n'
            'print(json.dumps({"type":"turn.completed"}),flush=True)\n')

    async def standin(self, *argv, **kwargs):
        self.argv.append((argv, copy.deepcopy(kwargs.get('env'))))
        kwargs.pop('env', None)
        return await self.actual_spawn(sys.executable, '-c', self.child_body, **kwargs)

    async def turn(self, name, **overrides):
        options = dict(collector='fictional-collector', profile='.codex4', current_authority=lambda: None,
                       current_profiles=['.codex4'], publish=self.ends.append, maximum=4096,
                       capture_max=8192, shutdown=1)
        options.update(overrides)
        with patch.object(self.module.asyncio, 'create_subprocess_exec', side_effect=self.standin):
            return await self.context.turn(self.home/name, [('history', b'owned nonsecret fixture')],
                                           'mechanism test; no actual opaque evidence', **options)

    async def test_same_thread_and_account_survive_empty_future_pool_without_new_allocation(self):
        first = await self.turn('first')
        self.assertTrue(first[1]['answered'])
        created = self.context.created
        second = await self.turn('second', current_profiles=[])
        self.assertTrue(second[1]['answered'])
        self.assertEqual(second[1]['input'], 1)
        self.assertEqual(self.context.created, created)
        self.assertNotIn('resume', self.argv[0][0])
        self.assertEqual(self.argv[1][0][self.argv[1][0].index('resume')+1], THREAD)
        self.assertEqual([v[1]['CODEX_HOME'] for v in self.argv], ['/home/nes/.codex4']*2)
        self.assertEqual([e['exit'] for e in self.ends], [0, 0])
        self.assertFalse(self.originals.owned)

    async def test_new_context_empty_pool_and_revoked_authority_refuse_before_export_or_spawn(self):
        with self.assertRaisesRegex(self.module.ReviewRefusal, 'membership'):
            await self.turn('excluded', current_profiles=[])
        self.assertFalse((self.home/'excluded').exists())
        def revoked():
            raise Refusal('actual-current-authority revoked')
        with self.assertRaisesRegex(Refusal, 'revoked'):
            await self.turn('revoked', current_authority=revoked)
        self.assertFalse(self.argv)

    async def test_continuation_refuses_changed_thread_account_collector_and_expired_lifetime(self):
        await self.turn('first')
        for field, value in [('profile', '.codex5'), ('collector', 'different-owner')]:
            with self.subTest(field=field), self.assertRaises(self.module.ReviewRefusal):
                await self.turn(field, **{field: value})
        self.context.created -= 31
        with self.assertRaisesRegex(self.module.ReviewRefusal, 'lifetime'):
            await self.turn('elapsed')
        self.assertEqual(len(self.argv), 1)

    async def test_mismatched_public_thread_is_partial_and_never_replayed(self):
        await self.turn('first')
        self.child_body = self.child_body.replace(THREAD, '00000000-0000-4000-8000-000000009999')
        code, receipt, answer = await self.turn('changed')
        self.assertFalse(receipt['answered'])
        self.assertIn('public thread identity missing/changed', receipt['errors'])
        with self.assertRaisesRegex(self.module.ReviewRefusal, 'interrupted'):
            await self.turn('no-fallback')
        self.assertEqual(len(self.argv), 2)
        self.assertFalse(self.originals.owned)

    async def test_capture_overflow_retains_prefix_numeric_end_and_interrupted_owner(self):
        self.child_body = 'import sys\nsys.stdin.read()\nprint("x"*10000,flush=True)\n'
        code, receipt, _ = await self.turn('overflow', maximum=1024, capture_max=2048)
        self.assertIsInstance(code, int)
        self.assertEqual((self.home/'overflow/stdout.jsonl').stat().st_size, 2048)
        self.assertFalse(receipt['capture_complete'])
        self.assertFalse(receipt['answered'])
        self.assertEqual(self.context.state, 'interrupted')
        self.assertFalse(self.originals.owned)

    async def test_deadline_stops_and_collects_original_without_inferred_provider_closure(self):
        self.context.lifetime = 1
        self.child_body = 'import sys,time\nsys.stdin.read()\ntime.sleep(30)\n'
        code, receipt, _ = await self.turn('deadline')
        self.assertIsInstance(code, int)
        self.assertTrue(receipt['lifetime_exceeded'])
        self.assertFalse(receipt['answered'])
        self.assertFalse(receipt['processing_completion'])
        self.assertEqual(len(self.ends), 1)
        self.assertFalse(self.originals.owned)

    async def test_nonzero_end_and_unexpected_tool_cannot_certify_answer(self):
        self.child_body += 'raise SystemExit(7)\n'
        code, receipt, _ = await self.turn('nonzero')
        self.assertEqual(code, 7)
        self.assertFalse(receipt['answered'])
        self.assertTrue(receipt['capture_complete'])

    async def test_unexpected_external_tool_activity_is_held_and_not_reported_as_read_only_success(self):
        self.child_body = ('import json,sys\nsys.stdin.read()\n'
            'print(json.dumps({"type":"item.completed","item":{"type":"mcp_tool_call"}}),flush=True)\n')
        code, receipt, _ = await self.turn('unexpected-tool')
        self.assertIsInstance(code, int)
        self.assertFalse(receipt['answered'])
        self.assertTrue(any('unexpected' in error for error in receipt['errors']))
        self.assertEqual(self.context.state, 'interrupted')

    async def test_close_fences_owner_without_archive_delete_or_manufactured_process_end(self):
        await self.turn('first')
        receipt = self.context.close('fictional-collector')
        self.assertTrue(receipt['local_owner_closed'])
        self.assertEqual(receipt['provider_storage'], 'retained and unmeasured')
        self.assertNotIn('actual_END', receipt)
        self.assertEqual(len(self.argv), 1)
        with self.assertRaisesRegex(self.module.ReviewRefusal, 'closed'):
            await self.turn('no-reopen')


class SelectedController(unittest.TestCase):
    def setUp(self):
        self.fixture = previous.Recovery(methodName='runTest')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def public_case(self, semantic, close):
        store, runtime, job, packet, policy, acquired, unused = self.fixture.native_fixture()
        store.config['tasks']['reviews-proposer'].update(execution='owner', binding=dict(opaque_review.BINDING))
        policy.update(transport=opaque_review.VERSION, executable='/usr/bin/false',
                      launcher_sha256=reviews.sha(opaque_review.launcher_path().read_bytes()))
        # Fictional method/source/authority seam, as in scoped29. This tests
        # controller routing, not public method incorporation or real provider.
        class Transport:
            def __init__(self):
                self.calls = []
            async def call(inner, runtime, attempt, policy, context, directory, text, commands, opening=False, close=False):
                if close:
                    return None, dict(transport=opaque_review.VERSION, local_owner_closed=True,
                                      caller_processes_collected=True, run=THREAD), None
                if not inner.calls:
                    runtime.begin(attempt, {'fictional_boundary': True})
                stage = 'architecture' if not inner.calls else 'complete'
                answer = encode(dict(semantic=semantic, summary='fictional bounded account', report='fictional full report',
                    history_entry='fictional history', stage=stage,
                    coverage=dict(families={f:'partial' for f in reviews.FAMILIES}, core_files_not_read=['fixture'],
                                  observations=[], answered_ids=[], limits=['fictional provider and authority'])))
                receipt = dict(transport=opaque_review.VERSION, actual_END=0, answered=True, capture_complete=True,
                    errors=[], thread=THREAD, run=THREAD, turn_completed=1, turn_failed=False,
                    lifetime_exceeded=False, input=len(inner.calls), profile=context['profile'], collector=context['collector'])
                inner.calls.append((text, answer))
                return 0, receipt, answer
        transport = Transport()
        executor = reviews.Executor(store, transport)
        attempt = store.start_job(job['id'], job['token'])
        self.assertEqual(json.loads(store.attempt(attempt)['binding']), opaque_review.BINDING)
        with patch.object(reviews, 'material', return_value={**acquired, 'situation': {'goals': 'authentic fixture goal'}}):
            outcome = asyncio.run(executor.execute(store.job(job['id']), attempt, policy, packet))
        store.collect(attempt, outcome)
        self.assertEqual(len(transport.calls), 2 if semantic == 'DONE' else 1)
        self.assertIn('authentic fixture goal', transport.calls[0][0])
        self.assertEqual(outcome['result']['category'], 'proposal')
        self.assertEqual(outcome['result']['handoffs'], [])
        self.assertIn('sole Reviews integration', outcome['result']['no_handoff_reason'])
        proof = reviews.collected_proof(store, store.job(job['id']), store.attempt(attempt))
        self.assertEqual(proof['kind'], 'selected-opaque-cli-review')
        self.assertFalse(proof['native_owner_execution'])
        if close:
            asyncio.run(executor.close('fictional-component', policy))
            self.assertEqual(store.one('SELECT state FROM review_contexts')['state'], 'closed')
            self.assertIsNone(json.loads(store.one('SELECT receipt FROM review_calls')['receipt'])[-1]['close_actual_END'])
        return store, job, attempt, outcome

    def test_explicit_public_selection_keeps_opaque_attempt_and_sole_proposal_route(self):
        self.public_case('DONE', True)

    def test_partial_original_uses_distinct_cli_receipt_and_cannot_be_restamped(self):
        from coordinator_runtime import review_returns
        store, job, attempt, outcome = self.public_case('PARTIAL', False)
        selection = store.processing.current()[1]
        selection['tasks'] = list(store.config['tasks'])
        selection['service']['report_tasks'] = ['reviews-integrator']
        store.processing.boards = {'Reviews': SimpleNamespace(
            _software_job_grant=lambda *args: None, software_authority=lambda *args: None)}
        identity = review_returns.identity(store, store.job(job['id']), store.attempt(attempt), outcome)
        self.assertEqual(identity['routes'], ['reviews-integrator'])
        self.assertEqual(identity['execution_kind'], 'selected-opaque-cli-review')
        self.assertFalse(identity['native_owner_execution'])
        self.assertIn('fictional provider', encode(outcome['result']['unknowns']))
        changed = copy.deepcopy(outcome)
        changed['detail']['original_review_calls'] = []
        with self.assertRaisesRegex(Refusal, 'whole original'):
            review_returns.identity(store, store.job(job['id']), store.attempt(attempt), changed)

    def test_real_snapshot_adapter_and_process_collection_without_fictional_native_receipts(self):
        store, runtime, job, packet, policy, acquired, unused = self.fixture.native_fixture()
        area = Path(policy['components'][packet['component']]['repository'])
        body = b'nonsecret owned public-interface fixture\n'
        (area/'fiction.txt').write_bytes(body)
        subprocess.run(['git', 'init', '-q', str(area)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(area), 'add', '--', 'fiction.txt'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(area), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '--no-gpg-sign', '-qm', 'nonsecret qualification fixture'], check=True, capture_output=True)
        head = subprocess.check_output(['git', '-C', str(area), 'rev-parse', 'HEAD']).decode().strip()
        packet.update(base=head, head=head)
        acquired.update(source={head+':fiction.txt':dict(bytes=len(body), sha256=reviews.sha(body))}, situation={'goals':'fixture custody'})
        policy.update(transport=opaque_review.VERSION, executable='/usr/bin/false',
            launcher_sha256=reviews.sha(opaque_review.launcher_path().read_bytes()), method_closure='unified-definitions-v1')
        store.config['tasks']['reviews-proposer'].update(execution='owner', binding=dict(opaque_review.BINDING))
        transport = reviews.Native()
        executor = reviews.Executor(store, transport)
        attempt = store.start_job(job['id'], job['token'])
        native_spawn = asyncio.create_subprocess_exec
        calls = []

        async def harmless(*argv, **kwargs):
            self.assertEqual(argv[0], '/usr/bin/false')
            self.assertEqual(argv[argv.index('--model')+1], 'gpt-xhigh')
            self.assertNotIn('--route', argv)
            self.assertNotIn('--root', argv)
            self.assertEqual(kwargs.pop('env')['CODEX_HOME'], '/home/nes/' + store.attempt(attempt)['profile'])
            calls.append(argv)
            reply = dict(semantic='DONE', summary='fictional source-account', report='fictional full report',
                history_entry='fictional method seam', stage='architecture' if len(calls)==1 else 'complete',
                coverage=dict(families={f:'partial' for f in reviews.FAMILIES}, core_files_not_read=['fixture'],
                              observations=[], answered_ids=[], limits=['method/authority/provider are fiction']))
            events = [dict(type='thread.started', thread_id=THREAD),
                      dict(type='item.completed', item=dict(type='agent_message', text=encode(reply))),
                      dict(type='turn.completed')]
            program = 'import sys\nsys.stdin.read()\n' + '\n'.join('print('+repr(encode(event))+',flush=True)' for event in events)
            return await native_spawn(sys.executable, '-c', program, **kwargs)

        with patch.object(reviews, 'material', return_value=acquired), \
             patch.object(reviews, 'method_files', return_value=policy['method_files']), \
             patch('asyncio.create_subprocess_exec', side_effect=harmless):
            outcome = asyncio.run(executor.execute(store.job(job['id']), attempt, policy, packet))
        store.collect(attempt, outcome)
        self.assertIsNone(outcome['error'])
        self.assertEqual(len(calls), 2)
        self.assertNotIn('resume', calls[0])
        self.assertEqual(calls[1][calls[1].index('resume')+1], THREAD)
        proof = reviews.collected_proof(store, store.job(job['id']), store.attempt(attempt))
        self.assertEqual(proof['kind'], 'selected-opaque-cli-review')
        self.assertFalse(proof['native_owner_execution'])
        for turn in proof['calls']:
            receipt = turn['receipt']
            self.assertEqual(turn['actual_END'], 0)
            self.assertTrue(receipt['capture_complete'])
            self.assertNotIn('turn', receipt)  # no manufactured native ACK/turn-end
            material = receipt['material']
            self.assertTrue(any(item['label'] == 'source:'+head+':fiction.txt' for item in material))
        self.assertEqual(transport.original_status(), [])
        asyncio.run(executor.close('fictional-component', policy))
        self.assertEqual(len(calls), 2)  # local close never launches or deletes a provider session
        self.assertEqual(store.one('SELECT state FROM review_contexts')['state'], 'closed')

