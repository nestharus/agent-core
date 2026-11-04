"""Selected pre-teardown handoffs; fictional in-memory protocol only."""
import asyncio
import copy
import json
from pathlib import Path
import unittest

from coordinator_runtime.appserver import AppServer, Peer
from coordinator_runtime.contracts import Refusal
from test_owned_completion import MemoryPipe, Store, THREAD, TURNS, SCHEMA, answer, final


class RefusalHandoff(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pipes = []
        self.adapter = AppServer({'deadlines': {'task': .1, 'shutdown': .1}})

    async def asyncTearDown(self):
        for p in self.pipes:
            p.close()
            await p.peer.reader

    async def refused(self, mode, schema=SCHEMA, prior=None):
        p = MemoryPipe()
        p.peer = Peer(p, 65536, attempt='fictional-handoff62')
        p.peer.thread = THREAD
        self.pipes.append(p)
        original_drain = p.drain

        async def drain():
            await original_drain()
            if p.request['method'] == 'turn/start':
                if mode == 'stale':
                    p.end(TURNS[1], status='interrupted')
                    p.item(TURNS[0], final(json.dumps(answer())))
                p.end()
        p.drain = drain
        out = {'result': None, 'error': None, 'exit': None, 'detail': {}}
        if prior is not None:
            out.update(copy.deepcopy(prior))
        message = 'no final answer' if mode == 'missing' else 'foreign or stale completion'
        with self.assertRaisesRegex(Refusal, message):
            await self.adapter.turn(p.peer, Store(), 'fictional-handoff62', THREAD,
                'Fictional work', {'sandbox': 'read-only'},
                {'model': 'unused', 'effort': 'unused'}, schema, out)
        return p, out

    def check_handoff(self, p, out, reason):
        self.assertFalse(p.closed)  # Question exists before teardown begins.
        self.assertIsNone(out['result'])
        self.assertEqual(len(p.starts), 1)
        self.assertIn('completion_refusal_handoff', out['detail'])
        h = out['detail']['completion_refusal_handoff']
        self.assertEqual(h['state'], 'blocked; original refusal retained')
        self.assertEqual(h['reason'], reason)
        self.assertEqual((h['attempt'], h['thread'], h['requested_turn']),
                         ('fictional-handoff62', THREAD, TURNS[0]))
        self.assertIn('Actual Work owner and original controller/collector', h['owner_question'])
        self.assertIn('effect/artifact/delivery custodian', h['owner_question'])
        self.assertIn('No completion', h['owner_question'])
        self.assertIn('snapshot', h['scope'])
        Path('/fictional/'+self._testMethodName+'-before.json').write_text(json.dumps({
            'outcome': out, 'turn_history': p.peer.turn_history,
            'final_returns': p.peer.final_returns, 'starts': p.starts,
            'transport': 'fictional in-memory; fake wait is not an OS END'}, indent=2)+'\n')
        return h

    async def test_missing_final_has_precise_question_before_teardown(self):
        p, out = await self.refused('missing')
        h = self.check_handoff(p, out, 'missing-final')
        self.assertIn('final discriminator', h['owner_question'])
        self.assertEqual(h['terminal']['collection'], 'missing-final-refused')
        self.assertEqual(out['error'], 'completed turn has no final answer')
        self.assertEqual(p.peer.final_returns, [])
        await self.adapter.teardown(p, p.peer, out)
        self.assertEqual(out['detail']['turn_completion_history'][0], h['terminal'])
        self.assertIsNone(out['result'])
        self.assertIn('completed-without-final', out['detail']['capture_history'])
        Path('/fictional/missing-after.json').write_text(json.dumps(out, indent=2)+'\n')

    async def test_stale_does_not_select_later_owned_completion(self):
        p, out = await self.refused('stale')
        h = self.check_handoff(p, out, 'foreign-or-stale')
        self.assertEqual(h['terminal']['turn']['id'], TURNS[1])
        self.assertEqual(h['terminal']['collection'], 'foreign-or-stale-refused')
        self.assertIn('uncollected', h['owner_question'])
        self.assertEqual(p.peer.turn_history[1]['collection'], 'uncollected')
        self.assertEqual(p.peer.final_returns[0]['text'], json.dumps(answer()))
        self.assertIn(TURNS[0], p.peer.finals)
        await self.adapter.teardown(p, p.peer, out)
        self.assertIsNone(out['result'])
        self.assertIsNotNone(out['error'])
        self.assertEqual(len(out['detail']['turn_completion_history']), 2)
        Path('/fictional/stale-after.json').write_text(json.dumps(out, indent=2)+'\n')

    async def test_non_task_refusal_also_returns_question(self):
        p, out = await self.refused('missing', schema=None)
        self.check_handoff(p, out, 'missing-final')

    async def test_prior_progress_error_and_return_are_conserved(self):
        prior = {'error': 'fictional original decode failure', 'detail': {
            'completion_progress': {'state': 'owned-turn-observed; awaiting-completion',
                'owner_question': 'fictional original progress question'},
            'prior_turn_result': answer()}}
        p, out = await self.refused('missing', prior=prior)
        self.check_handoff(p, out, 'missing-final')
        self.assertEqual(out['error'], prior['error'])
        for key, value in prior['detail'].items():
            self.assertEqual(out['detail'][key], value)
        # The run-level safety net may see the same refusal. Keep the first
        # snapshot rather than replacing it with a later capture state.
        h = copy.deepcopy(out['detail']['completion_refusal_handoff'])
        p.peer.capture = 'fictional-later-hold'
        self.adapter.refusal_handoff(p.peer, 'fictional-handoff62', None, out)
        self.assertEqual(out['detail']['completion_refusal_handoff'], h)

    async def test_late_drain_is_conserved_without_future_snapshot_claim(self):
        p, out = await self.refused('missing')
        self.check_handoff(p, out, 'missing-final')
        h = copy.deepcopy(out['detail']['completion_refusal_handoff'])
        p.tail.append({'method': 'turn/completed', 'params': {'threadId': THREAD,
            'turn': {'id': TURNS[0], 'status': 'failed', 'error': {'code': 500}}}})
        await self.adapter.teardown(p, p.peer, out)
        self.assertEqual(out['detail']['completion_refusal_handoff'], h)
        self.assertEqual([e['turn']['status'] for e in out['detail']['turn_completion_history']],
                         ['completed', 'failed'])
        self.assertIn('observed-adverse-terminal', out['detail']['capture_history'])
        self.assertEqual(out['error'], 'completed turn has no final answer')
        Path('/fictional/late-after.json').write_text(json.dumps(out, indent=2)+'\n')

    async def test_positive_completion_has_no_refusal_handoff(self):
        p = MemoryPipe([{'text': '{"positive":true}'}])
        p.peer = Peer(p, 65536, attempt='fictional-positive62')
        p.peer.thread = THREAD
        self.pipes.append(p)
        out = {'result': None, 'error': None, 'exit': None, 'detail': {}}
        result = await self.adapter.turn(p.peer, Store(), 'fictional-positive62', THREAD,
            'Fictional positive', {'sandbox': 'read-only'},
            {'model': 'unused', 'effort': 'unused'}, None, out)
        self.assertEqual(result, {'positive': True})
        self.assertEqual(len(p.starts), 1)
        self.assertNotIn('completion_refusal_handoff', out['detail'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
