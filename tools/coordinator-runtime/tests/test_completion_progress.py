"""Bounded future completion contract; ordinary in-memory protocol only.

No shared support, native fixture process, profile or session environment changes.
All protocol identities here are explicitly fictional test data.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import unittest

from coordinator_runtime.appserver import AppServer, Peer
from coordinator_runtime.contracts import Refusal, task_result
from coordinator_runtime import readiness
from coordinator_runtime.delivery import DeliveryJournal


THREAD = '00000000-0000-4000-8000-000000000010'
TURNS = ['00000000-0000-4000-8000-000000000011', '00000000-0000-4000-8000-000000000012']
SCHEMA = {'properties': {'payload_json': {'type': 'string'}}}


def answer(semantic='PARTIAL'):
    return {'semantic': semantic, 'category': 'blocker' if semantic == 'PARTIAL' else 'complete',
        'summary': 'Fictional bounded integration', 'findings': [{'meaning': 'Conserved dissent'}],
        'failures': ['Original local check failed'] if semantic == 'PARTIAL' else [],
        'unknowns': [], 'artifacts': [], 'handoffs': [],
        'no_handoff_reason': 'Fictional local control only.'}


def tool(identity, code=1):
    return {'id': identity, 'type': 'commandExecution', 'status': 'completed', 'exitCode': code,
            'command': 'PRIVATE COMMAND CANARY', 'aggregatedOutput': 'PRIVATE OUTPUT CANARY'}


class BodyGuard(dict):
    def get(self, key, *default):
        if key in {'command', 'aggregatedOutput', 'output', 'stdout', 'stderr'}:
            raise AssertionError('command/output acquisition forbidden')
        return super().get(key, *default)


class Store:
    def __init__(self):
        self.calls, self.sessions, self.revoked = 0, [], False
        self.config = {'actor': 'fictional-controller'}
        self.home = Path('/fixtures/fictional-store')

    def rows(self, *args):
        return []

    def authorize_launch(self, attempt):
        self.calls += 1
        if self.revoked:
            raise Refusal('fictional current source revoked')

    def attempt(self, attempt):
        return {'kind': 'task'}

    def session(self, *args):
        self.sessions.append(args)


class MemoryChild:
    """No OS process. Requests/replies are in-memory protocol messages."""
    def __init__(self, plans):
        self.stdout = asyncio.StreamReader()
        self.stdin = self
        self.plans, self.prompts, self.started = plans, [], []
        self.idle, self.closed, self.waited = True, False, 0
        self.returncode = None
        self.on_idle = None

    def write(self, data):
        self.request = json.loads(data)

    async def drain(self):
        request = self.request
        method, params = request['method'], request['params']
        if method == 'thread/read':
            if self.on_idle:
                self.on_idle()
            result = {'thread': {'id': THREAD, 'status': {'type': 'idle' if self.idle else 'active'}}}
        elif method == 'turn/start':
            index = len(self.started)
            turn = TURNS[index]  # A third start is a test failure, never a new budget.
            self.started.append(turn)
            self.prompts.append(params['input'][0]['text'])
            result = {'turn': {'id': turn}}
        elif method == 'turn/interrupt':
            result = {}
        else:
            raise AssertionError(method)
        await self.peer.frame({'id': request['id'], 'result': result})
        if method == 'turn/interrupt':
            self.peer.final_item(TURNS[0], {'id': 'fictional-raced-final', 'type': 'agentMessage',
                'phase': 'final_answer', 'text': self.plans[0]['race_text']})
            self.peer.notification({'method': 'turn/completed', 'params': {
                'threadId': THREAD, 'turn': {'id': TURNS[0], 'status': 'completed', 'error': None}}})
        if method == 'turn/start':
            plan = self.plans[index]
            for item in plan.get('tools', []):
                self.peer.notification({'method': 'item/completed', 'params': {
                    'threadId': THREAD, 'turnId': turn, 'item': item}})
            if plan.get('no_end'):
                return
            texts = plan.get('texts', [json.dumps({'payload_json': json.dumps(plan.get('answer', answer()))})])
            for n, text in enumerate(texts):
                self.peer.final_item(turn, {'id': 'fictional-final-'+str(index)+'-'+str(n),
                    'type': 'agentMessage', 'phase': 'final_answer', 'text': text})
            self.peer.notification({'method': 'turn/completed', 'params': {
                'threadId': THREAD, 'turn': {'id': turn, 'status': 'completed', 'error': None}}})

    def close(self):
        self.closed = True
        self.stdout.feed_eof()

    def is_closing(self):
        return self.closed

    async def wait(self):
        self.waited += 1
        self.returncode = 0
        return 0  # In-memory handle result, never an actual native/process END.


class CompletionProgress(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.children = []

    async def asyncTearDown(self):
        for child in self.children:
            child.close()
            await child.peer.reader

    def setup_case(self, plans):
        child = MemoryChild(plans)
        child.peer = Peer(child, 65536)
        child.peer.thread = THREAD
        self.children.append(child)
        store = Store()
        adapter = AppServer({'deadlines': {'task': 0.04, 'classify': 0.04, 'interrupt': 0.04, 'shutdown': 0.04}})
        outcome = {'result': None, 'error': None, 'exit': None, 'detail': {}}
        spec = {'sandbox': 'read-only', 'routine_completion': True}
        return child, store, adapter, outcome, spec

    async def run_case(self, case):
        child, store, adapter, outcome, spec = case
        return await adapter.turn(child.peer, store, 'fictional-attempt', THREAD,
            'Fictional bounded work', spec, {'model': 'unused', 'effort': 'unused'}, SCHEMA, outcome)

    async def test_blocked_partial_receives_safe_observations_without_relabel_or_body_acquisition(self):
        first = answer()
        case = self.setup_case([{'answer': first, 'tools': [BodyGuard(tool('fictional-adverse'))]}, {'answer': first}])
        child, store, _, outcome, _ = case
        result = await self.run_case(case)
        self.assertEqual(result, first)
        self.assertEqual(result['semantic'], 'PARTIAL')
        self.assertEqual(outcome['detail']['prior_turn_result'], first)
        record = outcome['detail']['completion_progress']
        self.assertEqual(record['observation']['items'][0]['id'], 'fictional-adverse')
        self.assertEqual(record['observation']['items'][0]['turn'], TURNS[0])
        self.assertIn('unobserved', record['observation']['command_correspondence'])
        self.assertIn('Actual Work owner and original controller/collector', record['owner_question'])
        self.assertNotIn('PRIVATE', child.prompts[1])
        self.assertIn('OBSERVED_ADVERSE_PROTOCOL_IDS=["fictional-adverse"]', child.prompts[1])
        self.assertEqual(len(store.sessions), 2)
        self.assertEqual(record['continuation_turn'], TURNS[1])

    async def test_remaining_verification_uses_genuine_ids_and_conserved_meaning(self):
        first = answer()
        # Independent numerical invariant and real own evidence bytes; this is
        # a narrow proof/link check, not semantic acceptance of arbitrary tests.
        report = Path('/fixtures/progress-verification.txt')
        report.write_text('sum(2,3,5)=10; original bad expectation 11 rejected\n')
        self.assertEqual(sum([2, 3, 5]), 10)
        ref = {'path': str(report), 'sha256': hashlib.sha256(report.read_bytes()).hexdigest()}
        final = {**copy.deepcopy(first), 'semantic': 'DONE', 'category': 'complete', 'artifacts': [str(report)],
            'completion': {'version': 1, 'local': 'ready', 'unknowns': [],
                'failures': [{'index': 0, 'status': 'resolved', 'evidence': [ref], 'verification_items': ['fictional-check']}],
                'tools': [{'id': 'fictional-adverse', 'status': 'resolved', 'reason': 'Corrected numerical expectation; selected check verifies it.',
                    'evidence': [ref], 'verification_items': ['fictional-check']}]}}
        case = self.setup_case([{'answer': first, 'tools': [tool('fictional-adverse')]},
            {'answer': final, 'tools': [tool('fictional-check', 0)]}])
        result = await self.run_case(case)
        self.assertEqual(task_result(result, first), final)
        def witness(value):
            self.assertEqual(value, ref)
            self.assertEqual(hashlib.sha256(Path(value['path']).read_bytes()).hexdigest(), value['sha256'])
        items = list(case[0].peer.tools.values())
        self.assertEqual(readiness.inspect(result, items, check_ref=witness)[2], [])
        wrong = copy.deepcopy(result)
        wrong['completion']['tools'][0]['verification_items'] = ['visible-label']
        self.assertTrue(readiness.inspect(wrong, items, check_ref=witness)[2])
        self.assertEqual(len(case[3]['detail']['completion_progress']['observation']['items']), 1)
        self.assertEqual(len(items), 2)  # Later observations were not in the first snapshot.

    async def test_outer_and_inner_parser_failure_get_one_context_and_keep_original_failure(self):
        for text in ['{broken outer', json.dumps({'payload_json': '{broken inner'}),
                     '{"duplicate":1,"duplicate":2}', '{"payload_json":17}']:
            with self.subTest(text=text):
                case = self.setup_case([{'texts': [text], 'tools': [tool('fictional-adverse')]}, {'answer': answer()}])
                result = await self.run_case(case)
                child, _, _, outcome, _ = case
                self.assertEqual(result['semantic'], 'PARTIAL')
                self.assertIn('owned final decode failed', outcome['error'])
                self.assertEqual(child.peer.final_returns[0]['text'], text)
                self.assertIn('invalid-final-needs-reconciliation', child.peer.capture_history)
                self.assertEqual(len(child.started), 2)
                self.assertIn('OBSERVED_TOOL_METADATA', child.prompts[1])
                self.assertEqual(outcome['detail']['prior_final_decode_failure']['turn'], TURNS[0])

    async def test_invalid_first_valid_conflict_is_evidence_not_last_json_selection(self):
        conflict = {**answer(), 'summary': 'Later valid conflict; never select by lastness'}
        case = self.setup_case([{'texts': ['{invalid first', json.dumps(conflict)]}, {'answer': answer()}])
        result = await self.run_case(case)
        self.assertEqual(result, answer())
        self.assertEqual(case[0].peer.late_finals[0]['typed_return'], conflict)
        self.assertEqual(case[0].peer.final_returns[0]['text'], '{invalid first')
        self.assertIn('conflicting-final', case[0].peer.capture_history)
        self.assertIn('invalid-final-needs-reconciliation', case[0].peer.capture_history)

    async def test_interrupt_raced_partial_and_parse_failure_use_same_observation_contract(self):
        for text in [json.dumps(answer()), '{raced invalid']:
            with self.subTest(text=text):
                case = self.setup_case([{'no_end': True, 'race_text': text, 'tools': [tool('fictional-raced-adverse')]},
                    {'answer': answer()}])
                self.assertEqual(await self.run_case(case), answer())
                child, _, _, outcome, _ = case
                self.assertEqual(child.peer.final_returns[0]['text'], text)
                self.assertEqual(len(child.started), 2)
                self.assertIn('fictional-raced-adverse', child.prompts[1])
                self.assertEqual(outcome['detail']['completion_progress']['observation']['prior_turn'], TURNS[0])

    async def test_ready_valid_routine_result_needs_no_extra_turn(self):
        first = {**answer('DONE'), 'completion': {'version': 1, 'local': 'ready',
            'failures': [], 'unknowns': [], 'tools': []}}
        case = self.setup_case([{'answer': first}])
        self.assertEqual(await self.run_case(case), first)
        self.assertEqual(len(case[0].started), 1)
        self.assertNotIn('completion_progress', case[3]['detail'])

    async def test_non_task_decode_failure_does_not_gain_a_new_continuation(self):
        child, store, adapter, outcome, spec = self.setup_case([{'texts': ['{non-task invalid']}])
        with self.assertRaisesRegex(Refusal, 'owned final decode failed'):
            await adapter.turn(child.peer, store, 'fictional-attempt', THREAD,
                'Fictional non-task', spec, {'model': 'unused', 'effort': 'unused'}, None, outcome)
        self.assertEqual(len(child.started), 1)
        self.assertNotIn('completion_progress', outcome['detail'])

    async def test_second_parse_failure_is_finite_with_actionable_owner_question(self):
        case = self.setup_case([{'texts': ['{first invalid']}, {'texts': ['{second invalid']}])
        with self.assertRaisesRegex(Refusal, 'owned final decode failed'):
            await self.run_case(case)
        child, _, _, outcome, _ = case
        self.assertEqual(len(child.started), 2)
        self.assertEqual([r['text'] for r in child.peer.final_returns], ['{first invalid', '{second invalid'])
        record = outcome['detail']['completion_progress']
        self.assertEqual(record['failure_class'], 'FinalDecodeFailure')
        self.assertIn('genuine protocol-ID-to-command/verification witness', record['owner_question'])
        self.assertNotIn('qualification separate', record['state'])

    async def test_idle_and_current_authority_fences_leave_question_before_teardown(self):
        for mode in ['active', 'revoked']:
            with self.subTest(mode=mode):
                case = self.setup_case([{'answer': answer()}, {'answer': answer()}])
                child, store, _, outcome, _ = case
                if mode == 'active':
                    child.idle = False
                else:
                    child.on_idle = lambda: setattr(store, 'revoked', True)
                with self.assertRaises(Refusal):
                    await self.run_case(case)
                self.assertEqual(len(child.started), 1)
                self.assertIn('owner_question', outcome['detail']['completion_progress'])
                self.assertNotIn('continuation_turn', outcome['detail']['completion_progress'])

    async def test_continuation_timeout_has_no_third_turn_and_conserves_original(self):
        case = self.setup_case([{'answer': answer()}, {'no_end': True}])
        with self.assertRaises(asyncio.TimeoutError):
            await self.run_case(case)
        self.assertEqual(len(case[0].started), 2)
        self.assertEqual(case[3]['detail']['prior_turn_result'], answer())
        self.assertEqual(case[3]['detail']['completion_progress']['failure_class'], 'TimeoutError')

    async def test_conflict_late_capture_and_exact_final_history_survive_teardown(self):
        first, conflict = answer(), {**answer(), 'summary': 'Conflicting future evidence'}
        case = self.setup_case([{'texts': [json.dumps(first), json.dumps(conflict)]}, {'answer': first}])
        child, _, adapter, outcome, _ = case
        self.assertEqual(await self.run_case(case), first)
        child.peer.final_item(TURNS[0], {'id': 'fictional-late', 'type': 'agentMessage',
            'phase': 'final_answer', 'text': '{late invalid'})
        await adapter.teardown(child, child.peer, outcome)
        self.assertEqual(child.waited, 1)
        self.assertTrue(child.closed)
        self.assertEqual(outcome['detail']['late_or_conflicting_returns'][0]['typed_return'], conflict)
        self.assertEqual(len(outcome['detail']['final_returns']), 4)
        self.assertIn('conflicting-final', outcome['detail']['capture_history'])
        self.assertIn('late-final-needs-reconciliation', outcome['detail']['capture_history'])
        self.assertEqual(len(outcome['detail']['turn_completion_history']), 2)

    async def test_changed_tool_completion_cannot_erase_adverse_history(self):
        case = self.setup_case([{'answer': answer(), 'tools': [tool('same-fictional-id', 1)]},
            {'answer': answer(), 'tools': [tool('same-fictional-id', 0)]}])
        await self.run_case(case)
        peer = case[0].peer
        self.assertEqual([r['exit_code'] for r in peer.tool_history], [1, 0])
        self.assertEqual(peer.tools['same-fictional-id']['exit_code'], 1)
        self.assertIn('conflicting-tool-observation', peer.capture_history)

    async def test_foreign_completion_cannot_supply_owned_observations(self):
        case = self.setup_case([])
        peer = case[0].peer
        peer.notification({'method': 'item/completed', 'params': {
            'threadId': 'foreign-fictional-thread', 'turnId': TURNS[0], 'item': BodyGuard(tool('foreign'))}})
        self.assertEqual(peer.tools, {})
        self.assertEqual(peer.tool_history, [])
        self.assertEqual(peer.capture, 'foreign-tool-completion')
        peer.events.put_nowait({'method': 'turn/completed', 'threadId': 'foreign-fictional-thread',
            'turn': {'id': TURNS[0], 'status': 'completed', 'error': None}})
        with self.assertRaisesRegex(Refusal, 'foreign or stale'):
            await peer.completion(THREAD, TURNS[0], 0.04)
        self.assertEqual(peer.completed_turns, set())

    async def test_return_and_observation_limits_stay_finite_and_unqualified(self):
        case = self.setup_case([])
        peer = case[0].peer
        for n in range(17):
            peer.final_item(TURNS[0], {'id': 'same-fictional-final', 'type': 'agentMessage',
                'phase': 'final_answer', 'text': json.dumps({'variant': n})})
        self.assertEqual(len(peer.final_returns), 16)
        self.assertEqual(peer.capture, 'final-count-exceeded-bound')
        for n in range(256):
            peer.notification({'method': 'item/completed', 'params': {
                'threadId': THREAD, 'turnId': TURNS[0], 'item': tool('same-fictional-tool', n)}})
        with self.assertRaisesRegex(Refusal, 'observation history exhausted'):
            peer.notification({'method': 'item/completed', 'params': {
                'threadId': THREAD, 'turnId': TURNS[0], 'item': tool('same-fictional-tool', 999)}})
        self.assertEqual(len(peer.tool_history), 256)
        self.assertNotEqual(peer.capture, 'complete')

    async def test_existing_owner_question_routes_full_conserved_context_to_Work(self):
        case = self.setup_case([{'texts': ['{first invalid']}, {'answer': answer()}])
        await self.run_case(case)
        child, _, adapter, outcome, _ = case
        await adapter.teardown(child, child.peer, outcome)
        class Journal:
            def _outbox(self, role, target, kind, payload, **kwargs):
                self.sent = (role, target, kind, payload, kwargs)
                return 'fictional-outbox'
        journal = Journal()
        attempt = {'id': 'fictional-attempt', 'session': THREAD, 'result': json.dumps(answer()),
            'detail': json.dumps(outcome['detail']), 'exit': None}
        job = {'id': 'fictional-job', 'role': 'Work', 'token': 'fictional-reservation',
            'package': None, 'members': json.dumps([{'event': 'fictional-source'}])}
        DeliveryJournal.owner_question(journal, job, attempt, 'Scoped blocked completion')
        role, target, kind, payload, _ = journal.sent
        self.assertEqual((role, target, kind), ('Work', 'Work', 'question'))
        self.assertEqual(payload['causal_detail'], outcome['detail'])
        self.assertIsNone(payload['exit'])  # No process END is manufactured.
        self.assertEqual(payload['causal_detail']['final_returns'][0]['text'], '{first invalid')


if __name__ == '__main__':
    unittest.main()
