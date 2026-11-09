"""Owned MOCK mechanics only. No real provider, listener, canary or Work scope. One check uses a real local stdlib process.

Run with --fixtures POSITIVELY_NEW_BUILDER_DIRECTORY --runtime PINNED_RUNTIME.
No fixture cleanup is performed. Transport and helper acceptance are fiction;
source loading, program dual-pass reading, pool operations, checks, snapshots,
capture parsing, original finalization and exclusive publication are real code.
"""
import argparse
import asyncio
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unittest
from unittest.mock import patch

import driver

ROOT = RUNTIME = None
SEQUENCE = 0


def guard(parent):
    fd = driver.directory(parent)
    try:
        s = os.fstatvfs(fd)
    finally:
        os.close(fd)
    if s.f_bavail * s.f_frsize - 2 * 1024**3 < 100 * 1024**3 or s.f_favail - 32000 < 1000000:
        raise RuntimeError('whole BUILDER allowance lacks headroom')


def put(path, body, replace=False):
    guard(path.parent)
    flags = os.O_WRONLY | os.O_NOFOLLOW | (os.O_TRUNC if replace else os.O_CREAT | os.O_EXCL)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(body)
        out.flush()
        os.fsync(out.fileno())


def fresh(parent, name):
    guard(parent)
    path = parent / name
    path.mkdir(mode=0o700)
    return path


class MockListener:
    """No socket is opened; never provider enforcement evidence."""
    sockets = ()

    def __init__(self):
        self.sockets = [self]
        self.closed = False

    def getsockname(self):
        return ('127.0.0.1', 32123)

    def close(self):
        self.closed = True

    async def wait_closed(self):
        assert self.closed


class MockInput:
    def __init__(self, finish):
        self.body, self.finish = b'', finish

    def write(self, data):
        self.body += data

    async def drain(self):
        await asyncio.sleep(0)

    def close(self):
        self.finish(self.body)


class MockProcess:
    def __init__(self, output=None, receive=None):
        self.stdout, self.stderr = asyncio.StreamReader(), asyncio.StreamReader()
        self.returncode = None
        self.done = asyncio.Event()
        self.stdin = MockInput(lambda text: self.complete(receive(text) if text else b'')) if receive else None
        if output is not None:
            self.complete(output)

    def complete(self, output):
        if self.returncode is not None:
            return
        self.stdout.feed_data(output)
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.returncode = 0
        self.done.set()

    async def wait(self):
        await self.done.wait()
        return self.returncode

    def terminate(self):
        self.complete(b'')

    kill = terminate


class Harness:
    def __init__(self, case, local_state=False):
        global SEQUENCE
        SEQUENCE += 1
        self.area = fresh(ROOT, '%02d-%s' % (SEQUENCE, case))
        if local_state:
            local = fresh(self.area, '.local')
            state = fresh(local, 'state')
            self.state = fresh(state, 'public-pool')
        else:
            self.state = fresh(self.area, 'pool-state')
        self.routes = self.area / 'routes.toml'
        raw = (RUNTIME / 'tools/direct-child/routes.toml').read_bytes()
        raw = re.sub(rb'(?m)^state_dir\s*=.*$', ('state_dir = ' + json.dumps(str(self.state))).encode(), raw)
        raw = re.sub(rb'(?ms)(^\[providers\.codex\][^\[]*?^pool\s*=\s*)\[[^\]]*\]',
                     lambda m: m[1] + b'[".codex2", ".codex3", ".codex4", ".codex5"]', raw)
        put(self.routes, raw)
        self.fast = self.area / 'global-fast'
        put(self.fast, b'true\n')
        self.program = self.area / 'mock-program'
        put(self.program, b'#!/bin/sh\nexit 0\n')
        guard(self.program.parent)
        self.program.chmod(0o700)
        self.material = self.area / 'selected-source.txt'
        put(self.material, b'MOCK selected source: an own synthetic engineering fixture.\n')
        pins = json.loads(Path(__file__).with_name('runtime-pins.json').read_text())
        caller = Path(driver.__file__)
        # Actual builder invocation identity, never a pretend Work or ID override.
        self.owner = os.environ['CODEX_THREAD_ID']
        self.scope = dict(owner=self.owner, operations=[
            'prepare', 'source', 'dependencies', 'allocate', 'control', 'qualify',
            'analysis', 'material', 'collect', 'publish'],
            revoked=False, expires_at=time.time() + 3600, custody_allowed=True,
            write_roots=[str(self.area / 'synthetic-question')],
            pool_write_parents=[str(self.state)],
            read_files=[str(RUNTIME / p) for p in pins['files']] +
                [str(p) for p in (caller, self.routes, self.fast, self.program, self.material,
                                  Path('/usr/bin/python3.12'))],
            runtime_directories=['/usr/lib/python3.12', '/usr/lib/x86_64-linux-gnu', '/usr/lib64'])
        self.scope['control_effects'] = list(driver.CONTROL_EFFECTS)
        self.scope['questions'] = ['MOCK first causal question', 'MOCK continuation question']
        self.scope['materials'] = [dict(label='own synthetic selected source', path=str(self.material),
            bytes=self.material.stat().st_size, sha256=driver.digest(self.material.read_bytes()))]
        self.authentication_checks, self.actions = 0, []
        self.principal = self.owner
        self.q = driver.Question(owner=self.owner, authenticate=self.authenticate,
            current=self.current, home=self.area / 'synthetic-question',
            runtime=RUNTIME, pins=pins, caller_pins={str(caller): driver.digest(caller.read_bytes())},
            program=dict(path=str(self.program), bytes=self.program.stat().st_size,
                         max_bytes=4096, sha256=driver.digest(self.program.read_bytes())),
            helper=dict(path='/usr/bin/python3.12', bytes=1, max_bytes=4096,
                        sha256='0' * 64, startup='python-isolated-no-site-no-bytecode',
                        runtime_directories=self.scope['runtime_directories']),
            runtime_reads=['/usr/bin/python3.12', *self.scope['runtime_directories']],
            pool_control=dict(routes=str(self.routes), static_sha256='pending'),
            fast_control=dict(path=str(self.fast), helper_sha256=pins['files']['tools/direct-child/fast_tier.py']),
            exclusions=[str(self.area / 'held')], io_budget=64 * 1024**2)
        runtime_capacity = self.q.capacity
        def capacity(parent):
            guard(parent)  # whole 2GiB/32000 BUILDER, nesting question allowance
            runtime_capacity(parent)
        self.q.capacity = capacity
        runtime_pool_guard = self.q.pool_guard
        def pool_guard():
            guard(self.state)
            guard(self.routes.parent)
            runtime_pool_guard()
        self.q.pool_guard = pool_guard
        self.provider_calls, self.commands, self.prompts, self.listeners = 0, [], [], []
        self.probe_mode = 'good'
        self.after_qualification = None
        self.after_control = None
        self.scope['binding'] = json.loads(json.dumps(self.q.binding))
        # Import/bootstrap and all runtime source pin checks are actual. The
        # canonical system helper is deliberately NOT qualified in this build.
        self.q.runtime.load()
        self.q.pool_control = self.q.runtime.direct.execution_pool.Pool(self.routes).control_binding(raw)
        self.q.binding = self.q.describe_binding()
        self.scope['binding'] = json.loads(json.dumps(self.q.binding))

    def authenticate(self):
        self.authentication_checks += 1
        if self.principal != self.owner:
            raise driver.Refusal('actual MOCK builder principal changed')
        # None after checking is the normal checker convention.

    def current(self, action):
        self.actions.append(action)
        return self.scope

    def create(self):
        with patch.object(self.q.runtime, 'load', return_value=self.q.runtime), \
             patch.object(self.q.runtime.public_runtime, 'check_helper', return_value={'MOCK': True}):
            return self.q.create()

    @staticmethod
    def denied():
        return dict(allowed={'read': 'owned-allowed-canary'}, outside={'error': errno.EACCES},
                    write={'error': errno.EACCES}, network={'error': errno.EPERM})

    async def listener(self, *args, **kwargs):
        server = MockListener()
        self.listeners.append(server)
        return server

    async def spawn(self, *argv, **kwargs):
        await asyncio.sleep(0)
        if 'exec' in argv:
            self.provider_calls += 1
            self.commands.append(list(argv))
            return MockProcess(receive=self.receive)
        protected = len(argv) > 1 and argv[1] == 'sandbox'
        if protected:
            output = self.denied()
            if self.after_control:
                self.after_control()
        else:
            output = dict(allowed={'read': 'owned-allowed-canary'},
                          outside={'read': 'owned-outside-canary'}, write='succeeded', network='succeeded')
        return MockProcess(output=json.dumps(output).encode())

    def receive(self, body):
        text = body.decode()
        self.prompts.append(text)
        thread = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'  # explicitly synthetic
        rows = [dict(type='thread.started', thread_id=thread)]
        if self.provider_calls == 1:
            expected = text.split('short factual account.\n', 1)[1].split('\nSelected immutable material', 1)[0]
            item = dict(type='command_execution', command=expected, status='completed',
                        exit_code=0, aggregated_output=json.dumps(self.denied()))
            if self.probe_mode == 'adverse':
                item['aggregated_output'] = json.dumps(dict(self.denied(), network='succeeded'))
            if self.probe_mode != 'missing':
                rows.append(dict(type='item.completed', item=item))
            if self.probe_mode == 'duplicate':
                rows.append(dict(type='item.completed', item=dict(item, exit_code=3)))
            if self.after_qualification:
                self.after_qualification()
        rows += [dict(type='item.completed', item=dict(type='agent_message', text='MOCK authored transport answer')),
                 dict(type='turn.completed')]
        return b''.join(json.dumps(r).encode() + b'\n' for r in rows)

    async def run(self):
        with patch.object(self.q.runtime.public_runtime, 'check_helper', return_value={'MOCK': True}), \
             patch.object(asyncio, 'start_server', side_effect=self.listener), \
             patch.object(asyncio, 'create_subprocess_exec', side_effect=self.spawn):
            return await self.q.run('MOCK first causal question', 'MOCK continuation question', [
                driver.Material('own synthetic selected source', str(self.material), self.material.stat().st_size,
                                driver.digest(self.material.read_bytes()))])


class Mechanisms(unittest.IsolatedAsyncioTestCase):
    async def test_same_original_and_hot_policy_new_vs_continuing(self):
        h = Harness('same')
        h.create()
        ownership = h.q.review.ownership
        def change():
            put(h.fast, b'false\n', replace=True)
            guard(h.routes.parent)
            guard(h.state)
            h.q.pool.pool.set(['.codex3', '.codex4', '.codex5'])
        h.after_qualification = change
        result = await h.run()
        self.assertEqual(h.provider_calls, 3)
        self.assertEqual([a['input'] for a in result['answers']], [1, 2])
        self.assertIs(h.q.review.ownership, ownership)
        self.assertEqual(result['status']['thread'], 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        self.assertEqual(result['status']['state'], 'closed')
        self.assertEqual(result['pending_originals'], [])
        self.assertEqual(result['ownership']['profile'], '.codex2')
        self.assertTrue(all('service_tier="fast"' in argv for argv in h.commands))
        self.assertTrue(all('resume' in argv for argv in h.commands[1:]))
        self.assertNotIn('MOCK selected source', h.prompts[0])
        self.assertNotIn(str(RUNTIME), h.prompts[0])
        exported = h.q.home / 'context/turn-0/material'
        self.assertFalse(any(b'MOCK selected source' in p.read_bytes() for p in exported.iterdir()))
        self.assertTrue((h.q.home / 'context/turn-1/material/0000.txt').exists())
        self.assertTrue(all(s.closed for s in h.listeners))
        self.assertFalse(result['whole_processing'])
        self.assertFalse(result['acceptance'])
        self.assertEqual(result['answers'][0]['substantive'], 'UNASSESSED')
        self.assertGreater(h.authentication_checks, 10)
        self.assertTrue(list(h.q.home.glob('publication-*.json')))
        self.assertEqual(len(h.q.originals.keys), 9)  # six local controls, three provider originals
        for receipt in result['turn_receipts']:
            self.assertTrue(receipt['capture_complete'])
            self.assertTrue(receipt['stdout_eof'] and receipt['stderr_eof'])
            self.assertEqual(receipt['actual_END'], 0)

    async def test_missing_adverse_duplicate_probe_withholds_source_without_retry(self):
        for mode in ('missing', 'adverse', 'duplicate'):
            with self.subTest(mode=mode):
                h = Harness(mode)
                h.create()
                h.probe_mode = mode
                with self.assertRaises(ValueError):
                    await h.run()
                self.assertEqual(h.provider_calls, 1)
                self.assertFalse(h.q.review.status['protection_qualified'])
                self.assertEqual(h.q.answers, [])
                self.assertFalse((h.q.home / 'context/turn-1').exists())
                with self.assertRaises(driver.Refusal):
                    await h.run()
                self.assertTrue(all(s.closed for s in h.listeners))

    async def test_revoked_during_awaited_control_prevents_provider_spawn(self):
        h = Harness('revoked-after-await')
        h.create()
        h.after_control = lambda: h.scope.update(revoked=True)
        with self.assertRaises(ValueError):
            await h.run()
        self.assertEqual(h.provider_calls, 0)
        self.assertFalse(h.q.review.status['protection_qualified'])
        self.assertEqual(h.q.answers, [])

    async def test_material_right_lost_between_turns_blocks_next_use(self):
        h = Harness('lost-material-right')
        h.create()
        publisher = h.q.publisher
        def publish(observation):
            publisher(observation)
            if h.q.answers:
                h.scope['read_files'].remove(str(h.material))
                h.q.publisher = publisher
        publish.attempts = publisher.attempts
        h.q.publisher = publish
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 2)
        self.assertEqual(len(h.q.answers), 1)

    async def test_current_owner_and_expiry_checks_are_executed(self):
        h = Harness('identity-expiry')
        h.create()
        h.principal = 'unrelated'
        with self.assertRaises(driver.Refusal):
            h.q.check('analysis')
        h.principal = h.owner
        h.scope['expires_at'] = time.time() - 1
        with self.assertRaises(driver.Refusal):
            h.q.check('analysis')
        self.assertIsNone(h.q.check('collect').get('not-a-proof'))

    async def test_actual_program_change_refuses_before_call(self):
        h = Harness('program-changed')
        h.create()
        put(h.program, b'#!/bin/sh\nexit 1\n', replace=True)
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 0)

    async def test_full_program_io_insufficiency_precedes_read(self):
        h = Harness('io')
        h.q.io_remaining = 32
        with patch.object(h.q.runtime.program, 'identity') as identity:
            with self.assertRaises(driver.Refusal):
                h.q.identities()
            identity.assert_not_called()

    async def test_source_hash_mismatch_and_held_path_precede_import_or_metadata(self):
        h = Harness('pin')
        relative = 'tools/direct-child/fast_tier.py'
        h.q.runtime.pins[relative] = '0' * 64
        with self.assertRaises(driver.Refusal):
            h.q.runtime.body(relative)
        with patch.object(driver, 'directory') as opened:
            with self.assertRaises(driver.Refusal):
                driver.read(h.area / 'held/never-acquired', 10, [str(h.area / 'held')])
            opened.assert_not_called()

    async def test_pool_removal_prevents_new_spawn(self):
        h = Harness('pool-removal')
        h.create()
        guard(h.routes.parent)
        guard(h.state)
        h.q.pool.pool.set(['.codex3'])
        with self.assertRaises(h.q.runtime.pool_module.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 0)

    async def test_changed_snapshot_and_unqualified_snapshot_refuse(self):
        h = Harness('snapshot')
        h.create()
        with self.assertRaises(driver.Refusal):
            h.q.selected()
        h.after_qualification = lambda: put(h.material, b'changed', replace=True)
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 1)
        self.assertEqual(h.q.answers, [])

    async def test_publication_failure_keeps_original_and_exclusive_retry(self):
        h = Harness('publication')
        h.create()
        owner = h.q.originals
        finishes = []
        async def finish(entry):
            finishes.append(entry['exit'])
        first = True
        def publish(observation):
            nonlocal first
            if first:
                first = False
                with patch.object(driver.os, 'fsync', side_effect=OSError('MOCK fsync failed')):
                    h.q.publisher(observation)
            else:
                h.q.publisher(observation)
        child = MockProcess(output=b'')
        key = owner.own(child, 'owned-sandbox-control', finish, publish)
        with self.assertRaises(h.q.runtime.appserver.CollectionPending):
            await owner.finish(key, 1)
        self.assertIn(key, owner.pending)
        self.assertTrue(owner.owned[key]['evidence_done'])
        failed = h.q.home / 'publication-0000.json'
        before = failed.read_bytes()
        self.assertFalse(h.q.publisher.attempts[0]['persisted'])
        self.assertEqual(await owner.finish(key, 1), 0)
        self.assertEqual(finishes, [0])
        self.assertEqual(failed.read_bytes(), before)
        self.assertTrue((h.q.home / 'publication-0001.json').exists())
        self.assertNotIn(key, owner.owned)
        self.assertEqual(h.provider_calls, 0)

    async def test_current_resource_and_symlink_parent_refusal(self):
        h = Harness('capacity')
        h.create()
        with patch.object(driver.os, 'fstatvfs', return_value=type('Space', (),
                          dict(f_bavail=1, f_frsize=4096, f_favail=2000000))()):
            with self.assertRaises(driver.Refusal):
                h.q.budget.check(h.q.home)
        alias = h.area / 'link'
        guard(h.area)
        alias.symlink_to(h.q.home, target_is_directory=True)
        with self.assertRaises(OSError):
            driver.directory(alias)

    async def test_capture_overflow_keeps_partial_and_numeric_end_distinct(self):
        h = Harness('capture-overflow')
        h.create()
        h.q.endpoint.maximum = 64
        h.q.endpoint.capture_max = 128
        with self.assertRaises(ValueError):
            await h.run()
        receipt = h.q.endpoint.receipts[0]
        self.assertEqual(receipt['actual_END'], 0)
        self.assertFalse(receipt['capture_complete'])
        self.assertFalse(receipt['answered'])
        self.assertLessEqual((h.q.home / 'context/turn-0/stdout.jsonl').stat().st_size, 128)
        self.assertEqual(h.provider_calls, 1)
        self.assertFalse(h.q.review.status['protection_qualified'])

    async def test_proof_persistence_failure_withholds_next_material(self):
        h = Harness('proof-persistence')
        h.create()
        original = h.q.runtime.direct.continuing_review.private_write
        def fail_proof(path, body, capacity):
            original(path, body, capacity)
            if path.name == 'acting-proof.json':
                raise OSError('MOCK proof durability failure after physical write')
        with patch.object(h.q.runtime.direct.continuing_review, 'private_write', side_effect=fail_proof):
            with self.assertRaises(OSError):
                await h.run()
        self.assertTrue((h.q.home / 'context/turn-0/acting-proof.json').exists())
        self.assertFalse(h.q.review.status['protection_qualified'])
        self.assertEqual(h.provider_calls, 1)
        self.assertEqual(h.q.answers, [])

    async def test_new_context_off_snapshot_and_insufficient_material_right(self):
        h = Harness('new-off')
        put(h.fast, b'false\n', replace=True)
        h.create()
        self.assertFalse(h.q.force_fast)
        argv = h.q.runtime.direct.review_context.command(h.q.profile, h.area, h.area)
        prepared = h.q.endpoint.execution.prepare(argv, h.q.profile)
        self.assertNotIn('service_tier="fast"', prepared)
        h.scope['read_files'].remove(str(h.material))
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 0)

    async def test_real_current_scope_reader_observes_revocation_and_binding_change(self):
        h = Harness('scope-reader')
        h.create()
        path = h.area / 'own-current-scope.json'
        put(path, json.dumps(h.scope).encode())
        h.q.current = driver.scope_reader(path, h.owner, h.q.exclusions)
        self.assertEqual(h.q.check('analysis')['owner'], h.owner)
        changed = dict(h.scope, revoked=True)
        put(path, json.dumps(changed).encode(), replace=True)
        with self.assertRaises(driver.Refusal):
            h.q.check('analysis')
        self.assertTrue(h.q.check('collect')['custody_allowed'])
        changed = json.loads(json.dumps(h.scope))
        changed['binding']['fast_control']['path'] = str(h.area / 'copied-policy')
        put(path, json.dumps(changed).encode(), replace=True)
        with self.assertRaises(driver.Refusal):
            h.q.check('control')

    async def test_listener_finalization_failure_does_not_commit_protection(self):
        h = Harness('listener-finalization')
        h.create()
        original = h.listener
        async def listener(*args, **kwargs):
            server = await original(*args, **kwargs)
            if len(h.listeners) == 1:
                async def fail():
                    raise OSError('MOCK listener finalization failed')
                server.wait_closed = fail
            return server
        h.listener = listener
        with self.assertRaises(OSError):
            await h.run()
        self.assertTrue((h.q.home / 'context/turn-0/acting-proof.json').exists())
        self.assertFalse(h.q.review.status['protection_qualified'])
        self.assertEqual(h.provider_calls, 1)
        self.assertEqual(h.q.answers, [])

    async def test_exact_public_pool_parent_under_local_is_narrowly_admitted(self):
        h = Harness('public-pool-parent', local_state=True)
        with self.assertRaises(driver.Refusal):
            driver.positive(h.state)  # ordinary private-path admission stays denied
        h.create()
        self.assertEqual(h.q.profile, '.codex2')
        self.assertTrue((h.state / 'codex.counter').exists())
        h.scope['pool_write_parents'] = []
        with patch.object(driver, 'directory', wraps=driver.directory) as opened:
            with self.assertRaises(driver.Refusal):
                driver.Question.pool_guard(h.q)  # isolate code under test from builder's extra wrapper
            self.assertNotIn(h.state, [call.args[0] for call in opened.call_args_list])
            # Reading the admitted public routes is permitted; target state is not.


class CurrentUse(unittest.IsolatedAsyncioTestCase):
    async def test_revocation_during_process_creation_never_feeds_but_collects(self):
        h = Harness('revoke-during-creation')
        h.create()
        spawn = h.spawn
        async def revoke(*argv, **kwargs):
            child = await spawn(*argv, **kwargs)
            if 'exec' in argv:
                h.scope['revoked'] = True
            return child
        h.spawn = revoke
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 1)
        self.assertEqual(h.prompts, [])
        self.assertEqual(h.q.originals.owned, {})
        self.assertFalse(h.q.review.status['protection_qualified'])
        self.assertEqual(h.q.answers, [])
        self.assertTrue(all(p['persisted'] for p in h.q.publisher.attempts))

    async def test_revocation_after_registration_before_feed_never_delivers(self):
        h = Harness('revoke-after-registration')
        h.create()
        h.q.endpoint.started = lambda: h.scope.update(revoked=True)
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 1)
        self.assertEqual(h.prompts, [])
        self.assertEqual(h.q.originals.owned, {})

    async def test_pool_executes_the_admitted_byte_module_without_filesystem_loader(self):
        h = Harness('admitted-pool')
        with patch.object(h.q.runtime.pool_module, 'public_pool_module', side_effect=AssertionError('second loader')):
            h.create()
            self.assertIs(type(h.q.pool.pool), h.q.runtime.direct.execution_pool.Pool)
            self.assertIs(h.q.pool.pool_module, h.q.runtime.direct.execution_pool)
            result = await h.run()
        self.assertEqual(len(result['answers']), 2)

    async def test_material_chunk_rights_remain_current_without_rehashing_binaries(self):
        h = Harness('material-authorization')
        h.create()
        owner = h.q.review.ownership
        amount = h.q.io_remaining
        with patch.object(h.q, 'identities', wraps=h.q.identities) as identity:
            channel = h.q.runtime.direct.opaque_dialogue.MaterialChannel(
                {'fixture': b'x' * 524288}, lambda: h.q.authorize_material(owner))
            item = channel.manifest()[0]['item']
            for offset in range(0, 524288, 12000):
                channel.request(dict(op='read', item=item, offset=offset, limit=12000))
            identity.assert_not_called()
            h.scope['read_files'].remove(str(h.material))
            h.q.materials = (driver.Material('fixture', str(h.material), 1, 'unused'),)
            with self.assertRaises(driver.Refusal):
                channel.request(dict(op='read', item=item, offset=0, limit=1))
        self.assertLess(h.q.io_remaining, amount)  # source/control reads charged

    async def test_current_identity_is_still_checked_after_material_export(self):
        h = Harness('identity-before-feed')
        h.create()
        original = h.q.authorize_material
        def mutate(owner):
            original(owner)
            put(h.program, b'changed executable bytes', replace=True)
        # The dialogue owns the callback selected at construction.
        h.q.review._dialogue._material_authority = mutate
        with self.assertRaises(h.q.runtime.appserver.Refusal):
            await h.run()
        self.assertEqual(h.provider_calls, 0)
        self.assertEqual(h.prompts, [])

    async def test_routes_growth_refuses_before_body(self):
        h = Harness('oversized-routes')
        h.create()
        put(h.routes, b'x' * (driver.MIB + 1), replace=True)
        with self.assertRaises(h.q.runtime.direct.execution_pool.PoolError):
            h.q.pool.pool.read()
        # A growth after preflight is checked by the real public pool reader.
        self.assertEqual(h.provider_calls, 0)

    async def test_existing_counter_is_finite_and_never_reset(self):
        h = Harness('oversized-counter')
        h.create()
        counter = h.state / 'codex.counter'
        put(counter, b'7' * 4097, replace=True)
        before = h.q.io_remaining
        with self.assertRaises(h.q.runtime.direct.execution_pool.PoolError):
            h.q.pool.pool.allocate(list(driver.PROFILES))
        self.assertLessEqual(h.q.io_remaining, before - 4097)
        self.assertEqual(counter.read_bytes(), b'7' * 4097)

    async def test_pool_admission_rechecks_current_parent_rights_before_effects(self):
        h = Harness('admission-parent-rights')
        h.create()
        counter = h.state / 'codex.counter'
        before = counter.read_bytes()
        h.scope['pool_write_parents'] = []
        with self.assertRaises(driver.Refusal):
            async with h.q.pool.admission(h.q.profile):
                self.fail('lost placement authority admitted')
        self.assertEqual(counter.read_bytes(), before)
        self.assertEqual(h.provider_calls, 0)

    async def test_pool_admission_rejects_changed_static_destination_before_creation(self):
        h = Harness('admission-static-control')
        h.create()
        unissued = h.area / 'never-admitted-state'
        put(h.routes, h.routes.read_bytes().replace(str(h.state).encode(), str(unissued).encode()), replace=True)
        with self.assertRaises(h.q.runtime.appserver.Refusal):
            async with h.q.pool.admission(h.q.profile):
                self.fail('changed static control admitted')
        self.assertFalse(unissued.exists())
        self.assertEqual(h.provider_calls, 0)

    async def test_dispatch_reads_use_the_same_cumulative_budget(self):
        h = Harness('dispatch-budget')
        h.create()
        h.q.io_remaining = 1
        with self.assertRaises(driver.Refusal):
            h.q.runtime.direct.dispatch.open_opaque_execution(h.routes, 'gpt-xhigh', '.codex2',
                force_fast=True, config_reader=h.q.control_read)
        self.assertEqual(h.provider_calls, 0)

    async def test_real_local_pipe_is_closed_without_prompt_on_current_use_refusal(self):
        h = Harness('real-local-pipe')
        out = fresh(h.area, 'actual-pipe')
        book = h.q.runtime.appserver.Originals().scope()
        rows = []
        def denied():
            self.assertEqual(len(book.owned), 1)  # registered before use check
            raise driver.Refusal('actual current-use fixture refusal')
        # Actual OS child and pipes; only an owned nonsecret stdlib fixture.
        with self.assertRaises(driver.Refusal):
            await h.q.runtime.direct.review_context.execute(
                ['/usr/bin/python3', '-I', '-S', '-B', '-c',
                 'import sys;print(len(sys.stdin.read()))'],
                {'PATH': '/usr/bin:/bin'}, 'owned nonsecret withheld text', out,
                book, rows.append, 10, 3, 65536, 65536, None, lambda: None,
                capacity_check=guard, before_feed=denied)
        self.assertEqual((out / 'stdout.jsonl').read_bytes(), b'0\n')
        self.assertEqual((out / 'stderr.bin').read_bytes(), b'')
        self.assertFalse(book.owned)
        self.assertTrue(rows)
        self.assertTrue(rows[-1]['evidence_complete'])

    async def test_double_root_is_refused_before_directory_metadata(self):
        with patch.object(driver, 'directory') as opened:
            with self.assertRaises(driver.Refusal):
                driver.read('//owned/fixture', 16)
            opened.assert_not_called()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    RUNTIME = args.runtime
    guard(args.fixtures.parent)
    args.fixtures.mkdir(mode=0o700)
    ROOT = args.fixtures
    unittest.main(argv=[__file__, *remaining], verbosity=2)
