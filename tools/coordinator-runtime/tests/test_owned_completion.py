"""Fictional protocol controls: owned admission, terminal conservation, handoff.

Uses no shared test support, account/session configuration, native or provider.
The stream transport is in memory unless explicitly testing a plain Python pipe.
"""
import asyncio
import json
from pathlib import Path
import sys
import unittest

from coordinator_runtime.appserver import AppServer, Peer, end_owned
from coordinator_runtime.contracts import Refusal

THREAD = '00000000-0000-4000-8000-000000000010'
FOREIGN = '00000000-0000-4000-8000-000000000099'
TURNS = ['00000000-0000-4000-8000-000000000011', '00000000-0000-4000-8000-000000000012']
SCHEMA = {'properties': {'payload_json': {'type': 'string'}}}


def answer():
    return {'semantic': 'PARTIAL', 'category': 'blocker', 'summary': 'Fictional scoped gap',
            'findings': [{'meaning': 'Keep dissent'}], 'failures': ['Fictional first failed check'],
            'unknowns': ['Command correspondence unavailable'], 'artifacts': [], 'handoffs': [],
            'no_handoff_reason': 'Question belongs to the original controller.'}


def final(text='{"owned":true}', identity='fictional-final'):
    return {'id': identity, 'type': 'agentMessage', 'phase': 'final_answer', 'text': text}


class BodyGuard(dict):
    def get(self, key, *args):
        if key in {'text', 'command', 'aggregatedOutput', 'error'}:
            raise AssertionError('Unentitled body was acquired: ' + key)
        return super().get(key, *args)


class MemoryPipe:
    """In-memory transport, including fake wait0; never an OS/native END."""
    def __init__(self, plans=()):
        self.stdin = self
        self.stdout = asyncio.StreamReader()
        self.plans, self.starts, self.prompts = plans, [], []
        self.closed, self.returncode, self.idle = False, None, True
        self.on_idle, self.tail, self.hold_pipe = None, [], False

    def write(self, raw):
        self.request = json.loads(raw)

    async def drain(self):
        r = self.request
        method, params = r['method'], r['params']
        if method == 'turn/start':
            index = len(self.starts)
            turn = TURNS[index]
            self.starts.append(turn)
            self.prompts.append(params['input'][0]['text'] if 'input' in params else '')
            result = {'turn': {'id': turn}}
        elif method == 'thread/read':
            if self.on_idle:
                self.on_idle()
            result = {'thread': {'id': THREAD, 'status': {'type': 'idle' if self.idle else 'active'}}}
        elif method == 'turn/interrupt':
            result = {}
        else:
            raise AssertionError(method)
        # Reply and frames share the same reader scheduling interval: admission
        # must happen before resolving the waiting RPC, not after it resumes.
        await self.peer.frame({'id': r['id'], 'result': result})
        if method == 'turn/interrupt':
            self.item(TURNS[0], final(self.plans[0]['race']))
            self.end(TURNS[0])
        if method == 'turn/start' and index < len(self.plans):
            plan = self.plans[index]
            for tool in plan.get('tools', []):
                self.item(turn, tool)
            if plan.get('no_end'):
                return
            self.item(turn, final(plan.get('text', json.dumps(answer()))))
            self.end(turn)

    def item(self, turn, item, thread=THREAD):
        self.peer.notification({'method': 'item/completed', 'params': {
            'threadId': thread, 'turnId': turn, 'item': item}})

    def end(self, turn=TURNS[0], status='completed', thread=THREAD, items=(), error=None):
        self.peer.notification({'method': 'turn/completed', 'params': {'threadId': thread,
            'turn': {'id': turn, 'status': status, 'items': list(items), 'error': error}}})

    def close(self):
        if not self.closed:
            self.closed = True
            for frame in self.tail:
                self.stdout.feed_data((json.dumps(frame) + '\n').encode())
            if not self.hold_pipe:
                self.stdout.feed_eof()

    def is_closing(self):
        return self.closed

    async def wait(self):
        self.returncode = 0
        return 0


class Store:
    def __init__(self):
        self.revoked, self.sessions = False, []

    def authorize_launch(self, attempt):
        if self.revoked:
            raise Refusal('fictional current authority revoked')

    def attempt(self, attempt):
        return {'kind': 'task'}

    def session(self, *args):
        self.sessions.append(args)


class OwnedCompletion(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pipes = []
        self.adapter = AppServer({'deadlines': {'task': .03, 'classify': .03, 'interrupt': .03, 'shutdown': .3}})

    async def asyncTearDown(self):
        for pipe in self.pipes:
            pipe.close()
            try:
                await pipe.peer.reader
            except asyncio.CancelledError:
                pass

    def pipe(self, plans=(), root=True):
        pipe = MemoryPipe(plans)
        pipe.peer = Peer(pipe, 65536)
        pipe.peer.attempt = 'fictional-attempt'
        if root:
            pipe.peer.thread = THREAD
        self.pipes.append(pipe)
        return pipe

    async def own_turn(self, pipe):
        await pipe.peer.rpc('turn/start', {'threadId': THREAD})

    async def collect(self, pipe):
        return await pipe.peer.completion(THREAD, TURNS[0], .1)

    async def teardown(self, pipe, result=None):
        outcome = {'result': result, 'error': None, 'exit': None, 'detail': {}}
        await self.adapter.teardown(pipe, pipe.peer, outcome)
        return outcome

    async def test_entitled_final_has_source_attribution(self):
        p = self.pipe()
        await self.own_turn(p)
        p.item(TURNS[0], final())
        p.end()
        self.assertEqual(await self.collect(p), {'owned': True})
        row = p.peer.final_returns[0]
        self.assertEqual((row.get('attempt'), row.get('thread'), row['turn']),
                         ('fictional-attempt', THREAD, TURNS[0]))

    async def test_foreign_body_cannot_satisfy_matching_owned_end(self):
        p = self.pipe()
        await self.own_turn(p)
        p.item(TURNS[0], final('{"foreign":true}'), FOREIGN)
        p.end()
        with self.assertRaises(Refusal):
            await self.collect(p)
        self.assertEqual(p.peer.final_returns, [])
        self.assertNotIn('foreign":true', json.dumps((await self.teardown(p))))

    async def test_preroot_and_unrequested_turn_reject_before_text_access(self):
        for root in (False, True):
            p = self.pipe(root=root)
            p.item(TURNS[0], BodyGuard(final()))
            self.assertEqual(p.peer.final_returns, [])
            self.assertNotEqual(p.peer.capture, 'complete')

    async def test_foreign_terminal_rejects_embedded_text_and_error_before_access(self):
        p = self.pipe()
        await self.own_turn(p)
        turn = BodyGuard({'id': TURNS[0], 'status': 'failed', 'items': [BodyGuard(final())], 'error': 'PRIVATE'})
        p.peer.notification({'method': 'turn/completed', 'params': {'threadId': FOREIGN, 'turn': turn}})
        with self.assertRaises(Refusal):
            await self.collect(p)
        self.assertEqual(p.peer.final_returns, [])
        history = (await self.teardown(p))['detail']['turn_completion_history']
        self.assertEqual(history[0]['threadId'], FOREIGN)
        self.assertIn('rejected', history[0]['admission'])
        self.assertNotIn('PRIVATE', json.dumps(history))

    async def test_missing_final_end_is_preserved_on_refusal(self):
        p = self.pipe()
        await self.own_turn(p)
        p.end()
        with self.assertRaisesRegex(Refusal, 'no final'):
            await self.collect(p)
        out = await self.teardown(p)
        self.assertEqual(out['detail']['turn_completion_history'][0]['turn']['status'], 'completed')
        self.assertNotEqual(out['capture'], 'complete')

    async def test_failure_after_success_survives_reader_drain_and_fake_zero(self):
        p = self.pipe()
        await self.own_turn(p)
        p.item(TURNS[0], final())
        p.end()
        result = await self.collect(p)
        p.tail.append({'method': 'turn/completed', 'params': {'threadId': THREAD,
            'turn': {'id': TURNS[0], 'status': 'failed', 'error': {'code': 400}}}})
        out = await self.teardown(p, result)
        history = out['detail']['turn_completion_history']
        self.assertEqual([r['turn']['status'] for r in history], ['completed', 'failed'])
        self.assertEqual(out['result'], {'owned': True})
        self.assertIsNotNone(out['error'])
        self.assertNotEqual(out['capture'], 'complete')
        self.assertEqual(out['exit'], 0)  # Explicitly fictional, never process proof.

    async def test_stale_end_is_preserved_with_identity_on_refusal(self):
        p = self.pipe()
        await self.own_turn(p)
        p.end(TURNS[1], status='interrupted')
        with self.assertRaisesRegex(Refusal, 'foreign or stale'):
            await self.collect(p)
        history = (await self.teardown(p))['detail']['turn_completion_history']
        self.assertEqual(history[0]['turn']['id'], TURNS[1])
        self.assertEqual(history[0]['turn']['status'], 'interrupted')

    async def test_history_and_queue_overflow_are_explicit_without_stopping_reader(self):
        p = self.pipe()
        await self.own_turn(p)
        for n in range(70):
            p.end(status='failed' if n >= 64 else 'completed')
        out = await self.teardown(p)
        summary = out['detail']['terminal_observations']
        self.assertEqual(len(out['detail']['turn_completion_history']), 64)
        self.assertEqual(summary['observed'], 70)
        self.assertEqual(summary['omitted'], 6)
        self.assertEqual(summary['adverse'], 6)
        self.assertGreater(summary['queue_overflow'], 0)
        self.assertFalse(summary['complete'])
        self.assertNotEqual(out['capture'], 'complete')

    async def test_unbound_tool_never_acquires_command_body(self):
        p = self.pipe(root=False)
        p.item(TURNS[0], BodyGuard({'id': 'fictional-tool', 'type': 'commandExecution', 'command': 'PRIVATE'}))
        self.assertEqual(p.peer.tools, {})
        self.assertNotEqual(p.peer.capture, 'complete')

    async def test_late_owned_final_retains_conflict_not_last_json(self):
        p = self.pipe()
        await self.own_turn(p)
        p.item(TURNS[0], final('{bad'))
        p.item(TURNS[0], final('{"later":true}', 'conflict'))
        p.end()
        with self.assertRaises(Refusal):
            await self.collect(p)
        p.item(TURNS[0], final('{late', 'late'))
        out = await self.teardown(p)
        self.assertEqual([r['text'] for r in out['detail']['final_returns']], ['{bad', '{"later":true}', '{late'])
        self.assertNotEqual(out['capture'], 'complete')

    async def test_final_and_tool_bounds_keep_originals_and_explicit_holds(self):
        p = self.pipe()
        await self.own_turn(p)
        for n in range(17):
            p.item(TURNS[0], final(json.dumps({'revision': n})))
        self.assertEqual(len(p.peer.final_returns), 16)
        self.assertEqual(p.peer.finals[TURNS[0]], '{"revision": 0}')
        self.assertIn('final-count-exceeded-bound', p.peer.capture_history)
        for n in range(256):
            p.item(TURNS[0], {'id': 'same-tool', 'type': 'commandExecution',
                'status': 'completed', 'exitCode': n+1})
        with self.assertRaisesRegex(Refusal, 'observation history exhausted'):
            p.item(TURNS[0], {'id': 'same-tool', 'type': 'commandExecution', 'exitCode': 0})
        self.assertEqual(len(p.peer.tool_history), 256)
        self.assertEqual(p.peer.tools['same-tool']['exit_code'], 1)
        out = await self.teardown(p)
        self.assertNotEqual(out['capture'], 'complete')
        self.assertEqual(len(out['detail']['final_returns']), 16)

    async def test_body_free_rejection_overflow_is_explicit(self):
        p = self.pipe(root=False)
        for n in range(70):
            p.item(TURNS[0], BodyGuard(final()))
        out = await self.teardown(p)
        self.assertEqual(len(out['detail']['rejected_observations']), 64)
        self.assertEqual(out['detail']['rejection_summary'], {'observed': 70, 'omitted': 6})
        self.assertEqual(out['detail']['final_returns'], [])
        self.assertNotEqual(out['capture'], 'complete')

    async def test_late_error_and_missing_final_are_not_qualified_by_zero(self):
        p = self.pipe()
        await self.own_turn(p)
        p.end()
        p.peer.notification({'method': 'error', 'params': {'threadId': THREAD,
            'turnId': TURNS[0], 'error': {'code': 500, 'details': 'FICTIONAL BODY NOT RETAINED'}}})
        out = await self.teardown(p)
        self.assertEqual(out['detail']['turn_completion_history'][0]['final_state'], 'unobserved')
        self.assertEqual(out['detail']['protocol_failures'][0]['turn'], TURNS[0])
        self.assertNotIn('FICTIONAL BODY', json.dumps(out))
        self.assertIsNotNone(out['error'])
        self.assertNotEqual(out['capture'], 'complete')

    async def test_pipe_closure_timeout_keeps_prefix_and_marks_incomplete(self):
        p = self.pipe()
        await self.own_turn(p)
        p.end(status='failed')
        p.hold_pipe = True
        adapter = AppServer({'deadlines': {'shutdown': .02}})
        out = {'result': None, 'error': None, 'exit': None, 'detail': {}}
        await adapter.teardown(p, p.peer, out)
        self.assertEqual(out['capture'], 'incomplete-owned-pipe-closure')
        self.assertFalse(out['detail']['terminal_observations']['complete'])
        self.assertEqual(out['detail']['terminal_observations']['stream'], 'cancelled-incomplete')
        self.assertEqual(out['detail']['turn_completion_history'][0]['turn']['status'], 'failed')
        self.assertIsNotNone(out['error'])

    async def test_cancelled_reader_keeps_terminal_prefix_and_incomplete_state(self):
        p = self.pipe()
        await self.own_turn(p)
        p.end(status='failed')
        # Give the reader its first scheduling interval, then cancel only this
        # in-memory fixture reader. The actual adapter must keep the prefix.
        await asyncio.sleep(0)
        p.peer.reader.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await p.peer.reader
        self.assertEqual(p.peer.terminal_summary['stream'], 'cancelled-incomplete')
        self.assertFalse(p.peer.terminal_summary['complete'])
        self.assertEqual(p.peer.turn_history[0]['turn']['status'], 'failed')
        # Replace no candidate code: asyncTearDown handles cancelled originals.

    async def test_real_owned_pipe_END_preserves_late_failure_and_foreign_projection(self):
        script = r"""
import json
import sys
thread = '00000000-0000-4000-8000-000000000010'
turn = '00000000-0000-4000-8000-000000000011'
def send(v):
    print(json.dumps(v), flush=True)
for raw in sys.stdin:
    req = json.loads(raw)
    send({'id': req['id'], 'result': {'turn': {'id': turn}}})
    send({'method':'item/completed','params':{'threadId':thread,'turnId':turn,
        'item':{'id':'pipe-final','type':'agentMessage','phase':'final_answer','text':'{"pipe":true}'}}})
    send({'method':'turn/completed','params':{'threadId':thread,'turn':{'id':turn,'status':'completed'}}})
send({'method':'turn/completed','params':{'threadId':thread,'turn':{'id':turn,'status':'failed','error':{'code':500}}}})
send({'method':'turn/completed','params':{'threadId':'fictional-foreign','turn':{'id':turn,'status':'interrupted',
    'items':[{'id':'foreign-final','type':'agentMessage','phase':'final_answer','text':'FICTIONAL FOREIGN CANARY'}]}}})
"""
        child = None
        record = {'process_END': None}
        try:
            child = await asyncio.create_subprocess_exec(sys.executable, '-B', '-u', '-c', script,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            record['original_asyncio_Process_pid_information_only'] = child.pid
            peer = Peer(child, 65536, attempt='fictional-pipe-attempt')
            peer.thread = THREAD
            await asyncio.wait_for(peer.rpc('turn/start', {'threadId': THREAD}), .5)
            self.assertEqual(await asyncio.wait_for(peer.completion(THREAD, TURNS[0], .5), .6), {'pipe': True})
            out = {'result': {'pipe': True}, 'exit': None, 'error': None, 'detail': {}}
            await self.adapter.teardown(child, peer, out)
            record['process_END'] = out['exit']
            record['outcome'] = out
            self.assertEqual(out['exit'], 0)
            self.assertEqual([e['turn']['status'] for e in out['detail']['turn_completion_history']],
                             ['completed', 'failed', 'interrupted'])
            self.assertEqual(out['detail']['terminal_observations']['stream'], 'eof-observed')
            self.assertEqual(out['detail']['terminal_observations']['rejected'], 1)
            self.assertEqual(len(out['detail']['final_returns']), 1)
            self.assertNotIn('FICTIONAL FOREIGN CANARY', json.dumps(out))
            self.assertIsNotNone(out['error'])
            self.assertNotEqual(out['capture'], 'complete')
        finally:
            if child is not None:
                record['finally_wait_END'] = await end_owned(child, .5)
            Path('/fictional/pipe-process-original.json').write_text(json.dumps(record, indent=2)+'\n')

    async def run_progress(self, plans, configure=None, schema=SCHEMA):
        p = self.pipe(plans)
        store = Store()
        if configure:
            configure(p, store)
        out = {'result': None, 'error': None, 'exit': None, 'detail': {}}
        try:
            result = await self.adapter.turn(p.peer, store, 'fictional-attempt', THREAD,
                'Fictional work', {'sandbox': 'read-only'}, {'model': 'unused', 'effort': 'unused'}, schema, out)
            return p, store, out, result
        finally:
            self.last_progress = p, store, out

    async def test_truthful_partial_gets_one_precise_question_without_body_mapping(self):
        p, store, out, result = await self.run_progress([{}, {}])
        self.assertEqual(result, answer())
        self.assertEqual(out['detail']['prior_turn_result'], answer())
        record = out['detail']['completion_progress']
        self.assertIn('Actual Work owner and original controller/collector', record['owner_question'])
        self.assertIn('unobserved', record['observation']['command_correspondence'])
        self.assertEqual(len(p.starts), 2)
        self.assertEqual(len(store.sessions), 2)

    async def test_decode_failures_and_second_failure_preserve_finite_question(self):
        for text in ('{broken', '{"payload_json":"{bad"}', '{"x":1,"x":2}', '{"payload_json":17}'):
            with self.subTest(text=text):
                with self.assertRaises(Refusal):
                    await self.run_progress([{'text': text}, {'text': '{second'}])
                p, _, out = self.last_progress
                self.assertEqual(len(p.starts), 2)
                self.assertEqual([r['text'] for r in p.peer.final_returns], [text, '{second'])
                self.assertIn('owner_question', out['detail']['completion_progress'])
                self.assertIn('owned final decode failed', out['error'])

    async def test_idle_revocation_timeout_controls_keep_question_and_single_budget(self):
        for mode in ('active', 'revoked', 'timeout'):
            def configure(p, store):
                if mode == 'active':
                    p.idle = False
                elif mode == 'revoked':
                    p.on_idle = lambda: setattr(store, 'revoked', True)
            with self.subTest(mode=mode):
                with self.assertRaises((Refusal, asyncio.TimeoutError)):
                    await self.run_progress([{}, {'no_end': True}], configure)
                p, _, out = self.last_progress
                self.assertEqual(len(p.starts), 2 if mode == 'timeout' else 1)
                self.assertIn('owner_question', out['detail']['completion_progress'])
                self.assertEqual(out['detail']['prior_turn_result'], answer())

    async def test_interrupt_raced_partial_and_invalid_keep_same_budget(self):
        for text in (json.dumps(answer()), '{race invalid'):
            with self.subTest(text=text):
                p, _, out, result = await self.run_progress([{'no_end': True, 'race': text}, {}])
                self.assertEqual(result, answer())
                self.assertEqual(len(p.starts), 2)
                self.assertEqual(len(p.peer.turn_history), 2)
                self.assertEqual(p.peer.final_returns[0]['text'], text)

    async def test_non_task_invalid_has_no_continuation(self):
        with self.assertRaises(Refusal):
            await self.run_progress([{'text': '{non-task'}], schema=None)
        p, _, out = self.last_progress
        self.assertEqual(len(p.starts), 1)
        self.assertNotIn('completion_progress', out['detail'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
