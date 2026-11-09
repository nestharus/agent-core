"""Decision1187 independent intent controls; fictional endpoint, real API effects.

No provider, profile, old fixture, installed service or foreign source is used.
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_pool import Pool, PoolError
from opaque_dialogue import Dialogue, MaterialChannel, Refusal, Reply


class ChannelTests(unittest.TestCase):
    def channel(self, **kwargs):
        return MaterialChannel({'history': b'prior\x00evidence', 'source': b'actual source bytes'}, lambda: None, **kwargs)

    def test_read_returns_exact_selected_bytes_and_attributable_operation(self):
        channel = self.channel()
        manifest = channel.manifest()
        self.assertEqual([r['label'] for r in manifest], ['history', 'source'])
        body = channel.request(dict(op='read', item='m0001', offset=7, limit=6))
        self.assertEqual(body, b'source')
        event = channel.events[-1]
        self.assertEqual((event['offset'], event['bytes']), (7, 6))
        self.assertEqual(event['sha256'], hashlib.sha256(body).hexdigest())
        with self.assertRaises(TypeError):
            event['bytes'] = 99

    def test_denied_paths_writes_network_shell_never_acquire_a_target(self):
        channel = self.channel()
        requests = [dict(op='read', path='/unadmitted-target'), dict(op='write', path='/unadmitted-target', body='x'),
                    dict(op='connect', address='127.0.0.1'), dict(op='shell', command='x'),
                    dict(op='read', item='../alias', offset=0, limit=1)]
        with patch('builtins.open', side_effect=AssertionError('target opened')), \
             patch('os.stat', side_effect=AssertionError('target statted')), \
             patch('os.lstat', side_effect=AssertionError('target lstat acquired')):
            for request in requests:
                with self.assertRaises(Refusal):
                    channel.request(request)
        self.assertEqual(len(channel.events), len(requests))
        self.assertTrue(all(dict(row) == dict(sequence=i, outcome='denied') for i, row in enumerate(channel.events)))

    def test_range_and_type_boundaries_are_not_coerced(self):
        channel = self.channel()
        for offset, limit in [(True, 1), (0, True), (-1, 2), (10000, 1), (0, 12001), (0, 0)]:
            with self.assertRaises(Refusal):
                channel.request(dict(op='read', item='m0000', offset=offset, limit=limit))
        self.assertEqual(channel.request(dict(op='read', item='m0000', offset=14, limit=1)), b'')

    def test_omitted_read_cannot_produce_an_actual_read_event(self):
        omitted, acted = self.channel(), self.channel()
        omission_report = 'read succeeded; writes and network denied'
        self.assertTrue(omission_report)
        self.assertEqual(omitted.events, ())
        actual = acted.request(dict(op='read', item='m0000', offset=0, limit=12000))
        self.assertEqual(actual, b'prior\x00evidence')
        self.assertEqual([r['outcome'] for r in acted.events], ['read'])

    def test_weakened_outside_reader_has_real_success_unavailable_at_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / 'outside'
            outside.write_bytes(b'outside-known-nonsecret-neighbor')
            weak_read = outside.read_bytes()  # Actual neighboring bypass succeeds.
            self.assertEqual(weak_read, b'outside-known-nonsecret-neighbor')
            channel = self.channel()
            with self.assertRaises(Refusal):
                channel.request(dict(op='read', path=str(outside)))
            self.assertNotIn(weak_read, [v for _, v in channel._items.values()])
            self.assertEqual(channel.events[-1]['outcome'], 'denied')

    def test_evidence_exhaustion_and_close_do_not_drop_or_reset_history(self):
        channel = self.channel(max_events=1)
        channel.request(dict(op='read', item='m0000', offset=0, limit=1))
        original = channel.events
        with self.assertRaises(Refusal):
            channel.manifest()
        channel.close()
        with self.assertRaises(Refusal):
            channel.request(dict(op='read', item='m0000', offset=1, limit=1))
        self.assertEqual(channel.events, original)

    def test_mutating_input_mapping_cannot_expand_admitted_material(self):
        source = {'original': b'admitted'}
        channel = MaterialChannel(source, lambda: None)
        source['original'] = b'changed'
        source['injected'] = b'outside'
        self.assertEqual(channel.request(dict(op='read', item='m0000', offset=0, limit=12)), b'admitted')
        with self.assertRaises(Refusal):
            channel.request(dict(op='read', item='m0001', offset=0, limit=12))


class Endpoint:
    """Fictional endpoint; exercises real channel and identity seam only."""
    def __init__(self):
        self.handle, self.opens, self.inputs, self.closed = object(), [], [], []
        self.reply_thread, self.complete, self.close_fails = 'owned-thread', True, False
        self.on_exchange = lambda: None

    async def open(self, ownership):
        self.opens.append(ownership)
        return self.handle

    async def exchange(self, handle, ownership, thread, text, channel):
        self.inputs.append((handle, ownership, thread, text, channel))
        self.on_exchange()
        body = channel.request(dict(op='read', item='m0000', offset=0, limit=12000))
        return Reply(self.reply_thread, body.decode(), self.complete)

    async def close(self, handle, ownership):
        self.closed.append((handle, ownership))
        if self.close_fails:
            raise OSError('fictional collection not delivered')
        return {'local_endpoint_collected': True, 'numeric_END': None, 'native_owner_execution': False}


class DialogueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.routes = Path(self.directory.name) / 'routes.toml'
        state = Path(self.directory.name) / 'control'
        self.routes.write_text('[providers.codex]\npool=[".codex5"]\nmanual_profiles=[".codex", ".codex5"]\n'
                               '[rotation]\nstate_dir=' + repr(str(state)) + '\n')
        self.pool, self.endpoint = Pool(self.routes), Endpoint()
        self.now, self.revoked, self.authorizations = [10.0], False, []

    def authority(self, ownership):
        self.authorizations.append(ownership)
        if self.revoked:
            raise Refusal('current authority revoked')

    @asynccontextmanager
    async def admission(self, profile):
        with self.pool.admission(profile, ['.codex', '.codex5'], blocking=False) as witness:
            yield witness

    def dialogue(self, **kwargs):
        return Dialogue(self.endpoint, '.codex5', 'original-collector', self.authority,
                        self.admission, clock=lambda: self.now[0], **kwargs)

    async def turn(self, dialogue, text='question'):
        return await dialogue.turn('original-collector', text, {'history': b'actual admitted material'})

    async def test_same_owned_handle_selector_account_collector_thread_and_origin_across_turns(self):
        dialogue = self.dialogue()
        ownership = dialogue.ownership
        await self.turn(dialogue, 'architecture first')
        self.now[0] += 2
        await self.turn(dialogue, 'substantive follow-on')
        self.assertEqual(len(self.endpoint.opens), 1)
        self.assertEqual([v[2] for v in self.endpoint.inputs], [None, 'owned-thread'])
        self.assertTrue(all(v[0] is self.endpoint.handle and v[1] is ownership for v in self.endpoint.inputs))
        self.assertEqual((ownership.selector, ownership.profile, ownership.collector, ownership.created, ownership.expires),
                         ('gpt-xhigh', '.codex5', 'original-collector', 10.0, 7210.0))
        self.assertTrue(all(value is ownership for value in self.authorizations))
        with self.assertRaises(Refusal):
            self.endpoint.inputs[0][-1].manifest()  # Old turn channel is closed.
        self.assertEqual(len(dialogue.operations), 2)
        await dialogue.close('original-collector')

    async def test_creation_uses_current_pool_fence_and_releases_before_exchange(self):
        dialogue = self.dialogue()
        self.endpoint.on_exchange = lambda: self.pool.set([])
        await self.turn(dialogue)
        self.assertEqual(self.pool.status()['enabled'], [])
        await self.turn(dialogue)  # Existing original continues after removal.
        fresh = self.dialogue()
        with self.assertRaises(PoolError):
            await self.turn(fresh)
        self.assertEqual(len(self.endpoint.opens), 1)
        self.assertEqual(fresh.status['creation'], 'not-attempted')

    async def test_authority_changed_during_admission_prevents_creation(self):
        @asynccontextmanager
        async def revoke(profile):
            self.revoked = True
            yield None
        dialogue = Dialogue(self.endpoint, '.codex5', 'original-collector', self.authority,
                            revoke, clock=lambda: self.now[0])
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(self.endpoint.opens, [])
        self.assertEqual(dialogue.status['state'], 'interrupted')

    async def test_authority_revocation_stops_next_actual_material_operation(self):
        dialogue = self.dialogue()
        self.endpoint.on_exchange = lambda: setattr(self, 'revoked', True)
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(dialogue.operations, ((),))
        self.assertEqual(dialogue.status['state'], 'interrupted')
        await dialogue.close('original-collector')
        self.assertEqual(len(self.endpoint.closed), 1)

    async def test_lifetime_includes_admission_wait_without_renewal(self):
        @asynccontextmanager
        async def delayed(profile):
            self.now[0] = 7210.0
            yield None
        dialogue = Dialogue(self.endpoint, '.codex5', 'original-collector', self.authority,
                            delayed, clock=lambda: self.now[0])
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(self.endpoint.opens, [])
        self.assertEqual(dialogue.ownership.expires, 7210.0)

    async def test_changed_thread_retains_return_and_fences_replay(self):
        dialogue = self.dialogue()
        await self.turn(dialogue)
        self.endpoint.reply_thread = 'foreign-thread'
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(dialogue.returns[-1].thread, 'foreign-thread')
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(len(self.endpoint.inputs), 2)

    async def test_partial_answer_is_preserved_and_not_success(self):
        self.endpoint.complete = False
        dialogue = self.dialogue()
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(dialogue.returns, (Reply('owned-thread', 'actual admitted material', False),))
        self.assertEqual(dialogue.status['turns'], 0)
        self.assertEqual(dialogue.status['state'], 'interrupted')

    async def test_original_collector_required_for_turn_and_close(self):
        dialogue = self.dialogue()
        with self.assertRaises(Refusal):
            await dialogue.turn('other', 'question', {'history': b'x'})
        with self.assertRaises(Refusal):
            await dialogue.close('other')
        self.assertEqual(self.endpoint.opens, [])

    async def test_admission_exit_failure_still_retains_exact_handle_for_close(self):
        @asynccontextmanager
        async def fail_exit(profile):
            yield None
            raise OSError('fictional guard exit failure')
        dialogue = Dialogue(self.endpoint, '.codex5', 'original-collector', self.authority,
                            fail_exit, clock=lambda: self.now[0])
        with self.assertRaises(OSError):
            await self.turn(dialogue)
        await dialogue.close('original-collector')
        self.assertIs(self.endpoint.closed[0][0], self.endpoint.handle)
        self.assertEqual(self.endpoint.inputs, [])

    async def test_failed_close_preserves_handle_for_collection_without_reopen(self):
        dialogue = self.dialogue()
        await self.turn(dialogue)
        self.endpoint.close_fails = True
        with self.assertRaises(OSError):
            await dialogue.close('original-collector')
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.endpoint.close_fails = False
        receipt = await dialogue.close('original-collector')
        self.assertIsNone(receipt['numeric_END'])
        self.assertEqual(await dialogue.close('original-collector'), receipt)
        self.assertEqual(len(self.endpoint.opens), 1)
        self.assertTrue(all(v[0] is self.endpoint.handle for v in self.endpoint.closed))

    async def test_endpoint_open_failure_is_unknown_creation_not_fresh_retry(self):
        async def failed(ownership):
            raise OSError('fictional lost creation return')
        self.endpoint.open = failed
        dialogue = self.dialogue()
        # The real pool wraps an OSError raised within its guard; retain the
        # causal chain rather than treating it as a different creation attempt.
        with self.assertRaises(PoolError) as caught:
            await self.turn(dialogue)
        self.assertIsInstance(caught.exception.__cause__, OSError)
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        receipt = await dialogue.close('original-collector')
        self.assertEqual(receipt['creation_effects'], 'unknown')

    async def test_overlapping_turn_refuses_while_original_is_live(self):
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.endpoint.exchange
        async def held(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        self.endpoint.exchange = held
        dialogue = self.dialogue()
        task = asyncio.create_task(self.turn(dialogue))
        await entered.wait()
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        release.set()
        await task

    async def test_cancelled_exchange_keeps_original_close_and_partial_operations(self):
        entered = asyncio.Event()
        async def held(handle, ownership, thread, text, channel):
            channel.request(dict(op='read', item='m0000', offset=0, limit=1))
            entered.set()
            await asyncio.Event().wait()
        self.endpoint.exchange = held
        dialogue = self.dialogue()
        task = asyncio.create_task(self.turn(dialogue))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(dialogue.status['state'], 'interrupted')
        self.assertEqual(dialogue.operations[0][0]['bytes'], 1)
        await dialogue.close('original-collector')
        self.assertIs(self.endpoint.closed[0][0], self.endpoint.handle)

    async def test_actual_timeout_fences_turn_and_closes_channel_without_new_origin(self):
        entered = asyncio.Event()
        async def held(*args):
            entered.set()
            await asyncio.Event().wait()
        self.endpoint.exchange = held
        # A real clock exercises wait_for at the actual async seam.
        dialogue = Dialogue(self.endpoint, '.codex5', 'original-collector', self.authority,
                            self.admission, lifetime=1)
        origin = dialogue.ownership
        with self.assertRaises(TimeoutError):
            await self.turn(dialogue)
        self.assertTrue(entered.is_set())
        self.assertIs(dialogue.ownership, origin)
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        await dialogue.close('original-collector')

    async def test_whole_dialogue_retention_limit_refuses_before_another_exchange(self):
        dialogue = self.dialogue()
        # Fixed whole-dialogue turn bound is independent of provider replies.
        for _ in range(128):
            await self.turn(dialogue)
        with self.assertRaises(Refusal):
            await self.turn(dialogue)
        self.assertEqual(len(self.endpoint.inputs), 128)
        self.assertEqual(len(dialogue.operations), 128)

    async def test_overlapping_close_refuses_without_duplicate_collection(self):
        dialogue = self.dialogue()
        await self.turn(dialogue)
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.endpoint.close
        async def held(*args):
            entered.set()
            await release.wait()
            return await original(*args)
        self.endpoint.close = held
        task = asyncio.create_task(dialogue.close('original-collector'))
        await entered.wait()
        with self.assertRaises(Refusal):
            await dialogue.close('original-collector')
        release.set()
        await task
        self.assertEqual(len(self.endpoint.closed), 1)


if __name__ == '__main__':
    unittest.main()
