"""Maker618: fictional Peer/owned provider boundary/real dispatcher readiness.

Never replays actual Work, inspects captures or uses a provider/native runtime.
Original adverse evidence and all fixture setup errors remain test outcomes.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_writer_custody as fixtures
from support import event, queued, ident, result
from coordinator_runtime import readiness
from coordinator_runtime.appserver import AppServer, Peer, HandbackFailure
from coordinator_runtime.contracts import Refusal

THREAD = '00000000-0000-4000-8000-000000000001'
TURN = '00000000-0000-4000-8000-000000000002'


class AuthoritativePeer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        stream = asyncio.StreamReader()
        self.peer = Peer(SimpleNamespace(stdout=stream, returncode=None), 65536)
        self.peer.thread = THREAD
        self.peer.owned_turns.add(TURN)

    async def asyncTearDown(self):
        self.peer.child.stdout.feed_eof()
        await self.peer.reader

    def final(self, value, identity='answer', thread=THREAD, turn=TURN, raw=False):
        self.peer.notification({'method': 'item/completed', 'params': {'threadId': thread, 'turnId': turn,
            'item': {'type': 'agentMessage', 'phase': 'final_answer', 'id': identity,
                     'text': value if raw else json.dumps(value)}}})

    def completed(self, thread=THREAD, turn=TURN, items=()):
        self.peer.notification({'method': 'turn/completed', 'params': {'threadId': thread,
            'turn': {'id': turn, 'status': 'completed', 'items': list(items)}}})

    async def test_exact_duplicates_and_equivalent_typed_finals_are_not_material_conflicts(self):
        value = result()
        self.final(value)
        self.final(value)
        self.final(dict(reversed(list(value.items()))), 'same-meaning')
        self.completed()
        self.assertEqual(await self.peer.completion(THREAD, TURN, 1), value)
        self.assertEqual(self.peer.capture, 'complete')
        self.assertEqual(len(self.peer.final_records), 2)

    async def test_same_item_changed_or_distinct_competing_final_never_selects_last(self):
        for identity in ['answer', 'different']:
            with self.subTest(identity=identity):
                # Each iteration has a distinct owned turn and independent facts.
                turn = str(__import__('uuid').uuid4())
                self.peer.owned_turns.add(turn)
                self.final(result(summary='First adverse account'), turn=turn)
                self.final(result(summary='Competing account'), identity, turn=turn)
                self.completed(turn=turn)
                with self.assertRaises(HandbackFailure):
                    await self.peer.completion(THREAD, turn, 1)
        self.assertEqual(self.peer.capture, 'conflicting-final')
        self.assertEqual(len(self.peer.final_records), 4)

    async def test_json_boolean_and_number_are_materially_different(self):
        self.final({'value': True})
        self.final({'value': 1}, 'numeric')
        self.completed()
        with self.assertRaises(HandbackFailure):
            await self.peer.completion(THREAD, TURN, 1)

    async def test_nonterminal_status_cannot_prove_original_completion(self):
        self.final(result())
        self.peer.notification({'method': 'turn/completed', 'params': {'threadId': THREAD,
            'turn': {'id': TURN, 'status': 'inProgress'}}})
        with self.assertRaisesRegex(Refusal, 'terminal status'):
            await self.peer.completion(THREAD, TURN, 1)
        self.assertNotIn(TURN, self.peer.completed_turns)

    async def test_invalid_first_and_typed_partial_both_survive_without_raw_reconstruction(self):
        self.final('{fictional invalid', raw=True)
        partial = result('PARTIAL', 'blocker')
        self.final(partial, 'typed-partial')
        self.completed()
        with self.assertRaises(HandbackFailure):
            await self.peer.completion(THREAD, TURN, 1)
        records = self.peer.final_records
        self.assertFalse(records[0]['valid_json'])
        self.assertEqual(records[0]['typed_return'], {'error': 'invalid final JSON', 'bytes': 18})
        self.assertEqual(records[1]['typed_return'], partial)
        self.assertNotIn('{fictional invalid', json.dumps(records))

    async def test_turn_aggregate_cannot_supply_missing_item_authority(self):
        item = {'type': 'agentMessage', 'phase': 'final_answer', 'id': 'aggregate', 'text': json.dumps(result())}
        self.completed(items=[item])
        with self.assertRaises(Refusal):
            await self.peer.completion(THREAD, TURN, 1)
        self.assertIn('aggregate-final-without-matching-authority', self.peer.capture_issues)
        self.assertEqual(self.peer.final_records[0]['authority'], 'turn-aggregate')

    async def test_foreign_thread_same_turn_cannot_satisfy_final(self):
        self.final(result(), thread='foreign')
        self.completed()
        with self.assertRaises(Refusal):
            await self.peer.completion(THREAD, TURN, 1)
        self.assertEqual(self.peer.capture, 'foreign-final-completion')
        self.assertEqual(self.peer.final_records, [])

    async def test_foreign_turn_event_is_refused_and_capture_hold_is_monotone(self):
        self.final(result())
        self.completed(turn='foreign')
        with self.assertRaises(Refusal):
            await self.peer.completion(THREAD, TURN, 1)
        self.peer.hold_capture('incomplete')
        self.assertEqual(self.peer.capture, 'foreign-turn-completion')
        self.assertIn('incomplete', self.peer.capture_issues)

    async def test_late_final_and_reused_item_in_other_turn_do_not_disappear(self):
        self.final(result())
        self.completed()
        await self.peer.completion(THREAD, TURN, 1)
        self.final(result(summary='Late competing claim'), 'late')
        next_turn = str(__import__('uuid').uuid4())
        self.peer.owned_turns.add(next_turn)
        self.final(result(), turn=next_turn)
        self.assertEqual(len(self.peer.final_records), 3)
        self.assertEqual(self.peer.capture, 'late-final-needs-reconciliation')

    async def test_actual_command_fingerprint_and_completed_tool_authority(self):
        command = 'sed -n 1,240p /fiction/runtime/local-integration.md'
        item = {'type': 'commandExecution', 'id': 'command', 'status': 'completed', 'exitCode': 0, 'command': command}
        params = {'threadId': THREAD, 'turnId': TURN, 'item': item}
        self.peer.notification({'method': 'item/completed', 'params': params})
        self.peer.notification({'method': 'item/started', 'params': params})
        row = self.peer.tools['command']
        self.assertEqual(row['command_sha256'], hashlib.sha256(command.encode()).hexdigest())
        self.assertTrue(self.peer.tool_inventory_complete())
        self.assertNotIn('command', row)
        self.peer.notification({'method': 'item/completed', 'params': {**params, 'item': {**item, 'exitCode': 2}}})
        self.assertEqual(self.peer.tools['command']['exit_code'], 0)
        self.assertFalse(self.peer.tool_inventory_complete())

    async def test_foreign_or_unowned_tool_cannot_establish_complete_inventory(self):
        for thread, turn in [('foreign', TURN), (THREAD, 'unowned')]:
            self.peer.notification({'method': 'item/completed', 'params': {'threadId': thread, 'turnId': turn,
                'item': {'type': 'commandExecution', 'id': turn, 'status': 'completed', 'exitCode': 0}}})
        self.assertFalse(self.peer.tool_inventory_complete())

    async def test_extra_unowned_final_turn_is_held_even_with_matching_terminal_result(self):
        self.final(result(), turn='unowned')
        self.final(result())
        self.completed()
        await self.peer.completion(THREAD, TURN, 1)
        self.assertEqual(self.peer.capture, 'foreign-final-turn')

    async def test_closed_owner_and_exhausted_budget_are_not_resumed(self):
        self.peer.completed_turns.add(TURN)
        adapter = AppServer({})
        for exhausted, code in [(True, None), (False, 0)]:
            with self.subTest(exhausted=exhausted, code=code):
                self.peer.continuation_used = exhausted
                self.peer.child.returncode = code
                with self.assertRaisesRegex(Refusal, 'single continuation'):
                    await adapter.continue_idle(self.peer, None, None, THREAD, TURN, {}, {}, None)


class OwnedBoundary(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.WriterCustody.asyncSetUp

    async def run_boundary(self, **changes):
        queued(self.store, event(self.config, ident()))
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        base = Path(self.temp.name)
        self.plan = {'target': str(self.target), 'report': str(self.store.home/'artifacts'/attempt/'verification.txt'),
            'record': str(base/'turns.jsonl'), 'writes': str(base/'writes.txt'), **changes}
        path = base/'transport-plan.json'
        path.write_text(json.dumps(self.plan))
        self.runtime.models = AppServer(self.config, [sys.executable,
            str(Path(__file__).with_name('fixture_handback618.py')), str(path)])
        await self.runtime.execute(job['id'], attempt)
        self.row = self.store.attempt(attempt)
        self.detail = json.loads(self.row['detail'])
        self.records = [json.loads(line) for line in Path(self.plan['record']).read_text().splitlines()]
        self.assertEqual(self.row['exit'], 0)
        self.assertIsNotNone(self.row['ended'])
        self.assertIsNotNone(self.row['collected'])
        self.assertEqual(self.detail['teardown'], 'actual-owned-process-exit-collected')
        self.assertEqual(len(Path(self.plan['writes']).read_text().splitlines()), 1)
        stage = Path(Path(self.plan['writes']).read_text().strip())
        self.assertEqual(stage.read_text(), '{"total":12}')
        return job, attempt

    def assert_held(self, job, turns):
        self.assertEqual(len(self.records), turns)
        self.assertEqual(json.loads(self.target.read_text()), {'total': 0})
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    async def test_unique_owned_clarification_uses_exact_ids_and_prepared_stage_without_replay(self):
        job, attempt = await self.run_boundary()
        self.assertEqual(len(self.records), 2)
        self.assertEqual(self.row['capture'], 'complete')
        self.assertIsNone(self.row['error'])
        self.assertEqual(self.store.job(job['id'])['effects'], 'reconciled')
        self.assertEqual(json.loads(self.target.read_text()), {'total': 12})
        answer = json.loads(self.row['result'])
        self.assertEqual(answer['failures'], self.detail['prior_turn_result']['failures'])
        self.assertEqual([r['verification_items'] for r in answer['completion']['tools']], [['tool-2'], ['tool-3']])
        self.assertEqual(self.detail['tool_completion']['nonzero_completions'], ['tool-0', 'tool-1'])
        self.assertNotIn('THIS OUTPUT MUST NEVER BE CAPTURED', json.dumps(self.detail))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    async def test_invalid_conflict_gets_one_typed_feedback_but_no_capture_upgrade(self):
        job, attempt = await self.run_boundary(conflict=True, partial=True)
        self.assert_held(job, 2)
        self.assertEqual(self.row['capture'], 'conflicting-final')
        originals = self.detail['prior_terminal_returns']
        self.assertEqual(len(originals), 2)
        self.assertFalse(originals[0]['valid_json'])
        self.assertEqual(originals[1]['typed_return']['semantic'], 'PARTIAL')
        self.assertEqual(json.loads(self.row['result'])['failures'], originals[1]['typed_return']['failures'])
        self.assertIn('ORIGINAL_TERMINAL_RETURNS=', self.records[1]['prompt'])
        self.assertIn('OBSERVED_ADVERSE_PROTOCOL_IDS=["tool-0","tool-1"]', self.records[1]['prompt'])
        self.assertEqual(len(self.detail['terminal_return_evidence']), 3)

    async def test_second_conflict_exhausts_original_single_budget(self):
        job, attempt = await self.run_boundary(conflict=True, partial=True, second_conflict=True)
        self.assert_held(job, 2)
        self.assertEqual(self.row['capture'], 'conflicting-final')
        self.assertEqual(len(self.detail['terminal_return_evidence']), 4)

    async def test_true_protocol_unknown_remains_partial_after_id_feedback(self):
        job, attempt = await self.run_boundary(partial=True)
        self.assert_held(job, 2)
        self.assertEqual(self.row['semantic'], 'PARTIAL')
        answer = json.loads(self.row['result'])
        self.assertEqual(answer['unknowns'], self.detail['prior_turn_result']['unknowns'])
        self.assertEqual(answer['completion']['local'], 'blocked')
        # The missing grammar is explicit, not an invented production change.
        answer['semantic'] = 'DONE'
        answer['completion']['local'] = 'ready'
        answer['completion']['unknowns'][0]['status'] = 'resolved'
        issues = readiness.inspect(answer, self.detail['tool_completion']['items'])[2]
        self.assertIn('unresolved/unsupported local unknown remains held', issues)

    async def test_busy_idle_readback_prohibits_second_turn(self):
        job, attempt = await self.run_boundary(conflict=True, partial=True, read_status='active')
        self.assert_held(job, 1)
        self.assertIn('idle', self.detail['handback_clarification_failure'])

    async def test_incomplete_tool_capture_prohibits_feedback_continuation(self):
        job, attempt = await self.run_boundary(conflict=True, partial=True, incomplete_tool=True)
        self.assert_held(job, 1)
        self.assertFalse(self.detail['tool_completion']['complete'])

    async def test_foreign_final_prohibits_continuation_and_publication(self):
        job, attempt = await self.run_boundary(foreign_final=True)
        self.assert_held(job, 1)
        self.assertEqual(self.row['capture'], 'foreign-final-completion')

    async def test_aggregate_only_final_is_held_without_reconstruction(self):
        job, attempt = await self.run_boundary(aggregate_only=True)
        self.assert_held(job, 1)
        self.assertEqual(self.row['capture'], 'aggregate-final-without-matching-authority')

    async def test_late_answer_during_idle_readback_prevents_new_turn(self):
        job, attempt = await self.run_boundary(late_on_read=True)
        self.assert_held(job, 1)
        self.assertEqual(self.row['capture'], 'late-final-needs-reconciliation')

    async def test_launch_source_revocation_prevents_new_turn(self):
        original = AppServer.continue_idle
        async def revoke(adapter, peer, store, *args, **kwargs):
            with patch.object(store, 'authorize_launch', side_effect=Refusal('fictional current source/point guard revoked')):
                return await original(adapter, peer, store, *args, **kwargs)
        with patch.object(AppServer, 'continue_idle', revoke):
            job, attempt = await self.run_boundary()
        self.assert_held(job, 1)
        self.assertIn('source/point guard revoked', self.row['error'])

    async def test_timeout_and_no_idle_proof_keep_owned_original_held(self):
        self.config['deadlines']['task'] = 0.05
        job, attempt = await self.run_boundary(hang_first=True, read_status='active')
        self.assert_held(job, 1)


class ReleaseDocumentation(unittest.TestCase):
    def test_exact_public_hints_name_the_authorized_release_root(self):
        text = (Path(__file__).parents[1]/'templates/work-catalog.md').read_text()
        for name in ['local-integration.md', 'bounded-catalog.md']:
            self.assertIn(name + ' beside the coordinator', text)
        self.assertIn('runtime release root', text)
