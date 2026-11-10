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
from types import SimpleNamespace
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
                                  Path('/usr/bin/python3.12'), Path('/lib64'))],
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



class NamespacePolicy(unittest.TestCase):
    def test_exact_entry_and_runtime_alias_without_ancestor_or_write_grant(self):
        h = Harness('namespace-policy')
        policy = h.q.runtime.direct.continuing_review.SandboxProtection(
            h.area, str(h.program), h.q.runtime_reads, guard, admit_read=h.q.admit_runtime_read).filesystem(
                h.area / 'material', h.area / 'workspace')
        self.assertEqual(policy[str(h.program)], 'read')
        self.assertNotIn(str(h.program.parent), policy)
        self.assertEqual(policy['/lib64'], 'read')
        self.assertEqual(policy[':root'], 'deny')
        self.assertTrue(all(value in {'deny', 'read'} for value in policy.values()))
        for path in ('/home', '/usr', '/lib', str(h.area / 'outside')):
            self.assertNotIn(path, policy)

    def test_changed_loader_alias_refuses_before_execution(self):
        h = Harness('namespace-alias-change')
        module = h.q.runtime.direct.continuing_review
        protection = module.SandboxProtection(h.area, str(h.program), h.q.runtime_reads, guard,
            admit_read=h.q.admit_runtime_read)
        with patch.object(module.os, 'readlink', return_value='different-runtime'):
            with self.assertRaises(module.Refusal):
                protection.filesystem(h.area / 'material', h.area / 'workspace')

    def test_alias_without_explicit_mediation_refuses_before_metadata(self):
        h = Harness('alias-unmediated')
        module = h.q.runtime.direct.continuing_review
        protection = module.SandboxProtection(h.area, str(h.program), h.q.runtime_reads, guard)
        with patch.object(Path, 'lstat', side_effect=AssertionError('unadmitted metadata')):
            with self.assertRaises(module.Refusal):
                protection.filesystem(h.area / 'material', h.area / 'workspace')

    def test_missing_alias_right_refuses_before_metadata(self):
        h = Harness('alias-no-right')
        module = h.q.runtime.direct.continuing_review
        h.scope['read_files'].remove('/lib64')
        protection = module.SandboxProtection(h.area, str(h.program), h.q.runtime_reads, guard,
            admit_read=h.q.admit_runtime_read)
        with patch.object(Path, 'lstat', side_effect=AssertionError('unadmitted metadata')):
            with self.assertRaises(driver.Refusal):
                protection.filesystem(h.area / 'material', h.area / 'workspace')

    def test_excluded_alias_refuses_before_metadata(self):
        h = Harness('alias-excluded')
        module = h.q.runtime.direct.continuing_review
        h.q.exclusions += ('/lib64',)
        protection = module.SandboxProtection(h.area, str(h.program), h.q.runtime_reads, guard,
            admit_read=h.q.admit_runtime_read)
        with patch.object(Path, 'lstat', side_effect=AssertionError('excluded metadata')):
            with self.assertRaises(driver.Refusal):
                protection.filesystem(h.area / 'material', h.area / 'workspace')

    def test_revocation_after_alias_metadata_prevents_readlink(self):
        h = Harness('alias-revoked-metadata')
        module = h.q.runtime.direct.continuing_review
        protection = module.SandboxProtection(h.area, str(h.program), h.q.runtime_reads, guard,
            admit_read=h.q.admit_runtime_read)
        lstat = Path.lstat
        def revoke(path):
            info = lstat(path)
            h.scope['revoked'] = True
            return info
        with patch.object(Path, 'lstat', revoke), patch.object(module.os, 'readlink') as link:
            with self.assertRaises(driver.Refusal):
                protection.filesystem(h.area / 'material', h.area / 'workspace')
            link.assert_not_called()

    def test_revocation_after_readlink_prevents_policy_admission(self):
        h = Harness('alias-revoked-policy')
        module = h.q.runtime.direct.continuing_review
        protection = module.SandboxProtection(h.area, str(h.program), h.q.runtime_reads, guard,
            admit_read=h.q.admit_runtime_read)
        def revoke(path):
            h.scope['revoked'] = True
            return 'usr/lib64'
        with patch.object(module.os, 'readlink', side_effect=revoke):
            with self.assertRaises(driver.Refusal):
                protection.filesystem(h.area / 'material', h.area / 'workspace')

    def test_alias_is_not_granted_for_undeclared_runtime(self):
        h = Harness('namespace-no-alias')
        module = h.q.runtime.direct.continuing_review
        policy = module.SandboxProtection(h.area, str(h.program),
            ['/usr/bin/python3.12'], guard).filesystem(h.area / 'material', h.area / 'workspace')
        self.assertNotIn('/lib64', policy)
        with self.assertRaises(module.Refusal):
            module.SandboxProtection(h.area, 'codex', ['/usr/bin/python3.12'], guard)

class LocalCreationBoundary(unittest.IsolatedAsyncioTestCase):
    async def boundary(self, mode):
        h = Harness('local-creation-' + mode)
        h.create()
        module = h.q.runtime.direct.continuing_review
        out = fresh(h.area, 'local-control')
        origin = time.monotonic()
        context = SimpleNamespace(created=origin, lifetime=.025 if mode == 'cutoff' else 10,
            clock=time.monotonic, account_home=str(h.area), profile='owned-nonsecret',
            originals=h.q.originals)
        complete = h.q.identities
        completed = []
        def delayed_identity():
            complete()  # Actual complete owned program check; helper remains MOCK.
            if mode == 'expires':
                h.scope['expires_at'] = time.time() + .025
            time.sleep(.06)
            if mode == 'revoked':
                h.scope['revoked'] = True
            if mode == 'alias-right':
                h.scope['read_files'].remove('/lib64')
            if mode == 'alias-exclusion':
                h.q.exclusions += ('/lib64',)
            completed.append(mode)
        h.q.identities = delayed_identity
        protection = module.SandboxProtection(out, str(h.program), h.q.runtime_reads,
            guard, probe_helper=h.q.probe_helper)
        calls = []
        async def spawn(*argv, **kwargs):
            calls.append(argv)
            return MockProcess(output=json.dumps(dict(ok=True)).encode())
        with patch.object(h.q.runtime.public_runtime, 'check_helper', return_value={'MOCK': True}), \
             patch.object(asyncio, 'create_subprocess_exec', side_effect=spawn):
            if mode == 'valid':
                self.assertEqual(await protection._run(context, out, 'neighbor',
                    [str(h.program)], h.q.publisher), {'ok': True})
                self.assertEqual(len(calls), 1)
            else:
                with self.assertRaises((driver.Refusal, module.Refusal)):
                    await protection._run(context, out, 'neighbor', [str(h.program)], h.q.publisher)
                self.assertEqual(calls, [], 'creation itself must be withheld')
        self.assertEqual(completed, [mode])
        self.assertFalse(h.q.originals.owned)

    async def test_local_expiry_during_complete_identity_prevents_creation(self):
        await self.boundary('expires')

    async def test_local_revocation_during_complete_identity_prevents_creation(self):
        await self.boundary('revoked')

    async def test_local_fixed_cutoff_during_complete_identity_prevents_creation(self):
        await self.boundary('cutoff')

    async def test_local_alias_right_lost_during_identity_prevents_creation(self):
        await self.boundary('alias-right')

    async def test_local_alias_excluded_during_identity_prevents_creation(self):
        await self.boundary('alias-exclusion')

    async def test_local_delayed_complete_identity_valid_neighbor(self):
        await self.boundary('valid')


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
        def fail_proof(path, body, capacity, **kwargs):
            original(path, body, capacity, **kwargs)
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


class PreparedReadPolicy(unittest.IsolatedAsyncioTestCase):
    """Prepared argv survives supported awaits; its read rights must not.

    Provider processes, helper acceptance and loader shape are MOCK premises.
    The real Question, Context, admission, complete owned-program identity,
    registration, capture, receipts and publication code remain in the path.
    """
    async def boundary(self, phase, operand='alias', *, excluded=False, valid=False):
        from contextlib import asynccontextmanager
        h = Harness('prepared-policy-' + phase + '-' + operand)
        entered, changed, identities = [], [], []
        actual_admission = h.q.admission
        def path():
            return dict(alias='/lib64', program=str(h.program), helper=h.q.helper['path'],
                python='/usr/lib/python3.12', libraries='/usr/lib/x86_64-linux-gnu',
                loader='/usr/lib64', material=str(h.material),
                snapshot=str(h.q.home / 'context/turn-0/material'),
                workspace=str(h.q.home / 'context/workspace'))[operand]
        def withdraw():
            if changed or valid:
                return
            target = path()
            if excluded:
                h.q.exclusions += (target,)
            elif target in h.scope['read_files']:
                h.scope['read_files'].remove(target)
            else:
                h.scope['runtime_directories'].remove(target)
            changed.append(target)
        @asynccontextmanager
        async def admission(profile):
            async with actual_admission(profile) as witness:
                await asyncio.sleep(0)  # A supported suspension after policy preparation.
                entered.append(witness)
                if phase == 'admission':
                    withdraw()
                yield witness
        h.q.admission = admission
        h.create()
        h.scope['runtime_directories'] = list(h.scope['runtime_directories'])
        complete_identity = h.q.identities
        def identity():
            complete_identity()  # Real full dual-pass OWNED mock program; helper is mocked.
            if entered:
                identities.append(h.provider_calls)
                if (phase == 'identity-create' and h.provider_calls == 0
                        or phase == 'identity-feed' and h.provider_calls == 1):
                    withdraw()
        h.q.identities = identity
        spawn = h.spawn
        async def creation(*argv, **kwargs):
            child = await spawn(*argv, **kwargs)
            if 'exec' in argv and phase == 'creation':
                withdraw()
            return child
        h.spawn = creation
        def registered():
            self.assertEqual(len(h.q.originals.owned), 1)
            if phase == 'registration':
                withdraw()
        h.q.endpoint.started = registered
        if valid:
            result = await h.run()
            self.assertEqual(len(result['answers']), 2)
            self.assertEqual(len(h.prompts), 3)
            self.assertEqual(h.provider_calls, 3)
            self.assertTrue(all('resume' in argv for argv in h.commands[1:]))
            self.assertEqual(result['status']['state'], 'closed')
            self.assertEqual(result['ownership']['profile'], '.codex2')
            self.assertEqual(len(entered), 1, 'continuations keep the original admission/account')
        else:
            with self.assertRaises(driver.Refusal):
                await h.run()
            self.assertEqual(changed, [path()])
            self.assertEqual(h.provider_calls, 0 if phase in {'admission', 'identity-create'} else 1,
                             'withhold creation itself when permission is lost before spawn')
            self.assertEqual(h.prompts, [], 'a post-delivery refusal cannot unsend input')
            self.assertEqual(h.q.answers, [])
            self.assertFalse(h.q.review.status['protection_qualified'])
        self.assertTrue(entered)
        self.assertTrue(identities)
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
        self.assertTrue(all(server.closed for server in h.listeners))
        if h.provider_calls:
            receipt = json.loads((h.q.home / 'context/turn-0/original-0.json').read_text())
            self.assertIsInstance(receipt['actual_END'], int)
            self.assertTrue(receipt['evidence']['stdout_eof'])
            self.assertTrue(receipt['evidence']['stderr_eof'])

    async def test_alias_withdrawn_during_new_admission_withholds_creation(self):
        await self.boundary('admission')

    async def test_alias_excluded_during_new_admission_withholds_creation(self):
        await self.boundary('admission', excluded=True)

    async def test_every_external_policy_read_is_current_after_complete_identity(self):
        for phase in ('identity-create', 'identity-feed'):
            for operand in ('alias', 'program', 'helper', 'python', 'libraries', 'loader'):
                for excluded in (False, True):
                    with self.subTest(phase=phase, operand=operand, excluded=excluded):
                        await self.boundary(phase, operand, excluded=excluded)

    async def test_generated_read_roots_remain_exclusion_mediated(self):
        for phase in ('identity-create', 'identity-feed'):
            for operand in ('snapshot', 'workspace'):
                with self.subTest(phase=phase, operand=operand):
                    await self.boundary(phase, operand, excluded=True)

    async def test_snapshot_source_right_is_current_at_policy_use(self):
        for phase in ('identity-create', 'identity-feed'):
            with self.subTest(phase=phase):
                await self.boundary(phase, 'material')

    async def test_selective_alias_loss_during_awaited_creation_withholds_feed(self):
        await self.boundary('creation')

    async def test_selective_alias_loss_after_registration_withholds_feed(self):
        await self.boundary('registration')

    async def test_current_neighbor_keeps_original_continuation_useful(self):
        await self.boundary('identity-feed', valid=True)

    async def test_policy_validation_cost_cannot_outlive_the_original(self):
        for phase in ('creation', 'feed'):
            with self.subTest(phase=phase):
                h = Harness('policy-cost-' + phase)
                h.create()
                actual = h.q.endpoint.policy_authority
                completed = []
                def current(*args):
                    actual(*args)
                    if not completed and (phase == 'creation' or h.provider_calls):
                        context = h.q.endpoint.context
                        context.clock = lambda: context.created + context.lifetime
                        completed.append(phase)
                h.q.endpoint.policy_authority = current
                with self.assertRaises(h.q.runtime.direct.review_context.ReviewRefusal):
                    await h.run()
                self.assertEqual(completed, [phase])
                self.assertEqual(h.provider_calls, 0 if phase == 'creation' else 1)
                self.assertEqual(h.prompts, [])
                self.assertFalse(h.q.originals.owned)
                self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
                self.assertTrue(all(server.closed for server in h.listeners))

    async def test_additional_prepared_read_is_mediated_without_a_named_operand_list(self):
        from contextlib import asynccontextmanager
        h = Harness('additional-policy-read')
        extra = h.area / 'additional-owned-read.txt'
        put(extra, b'owned synthetic additional policy operand')
        h.scope['read_files'].append(str(extra))
        h.create()
        filesystem = h.q.endpoint.protection.filesystem
        def prepared(material, workspace):
            return dict(filesystem(material, workspace), **{str(extra): 'read'})
        h.q.endpoint.protection.filesystem = prepared
        entered, removed = [], []
        admission = h.q.admission
        @asynccontextmanager
        async def suspend(profile):
            async with admission(profile) as witness:
                await asyncio.sleep(0)
                entered.append(witness)
                yield witness
        h.q.endpoint.admission = suspend
        identity = h.q.identities
        def complete():
            identity()
            if entered and not removed:
                h.scope['read_files'].remove(str(extra))
                removed.append(str(extra))
        h.q.identities = complete
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(removed, [str(extra)])
        self.assertEqual(h.provider_calls, 0)
        self.assertEqual(h.prompts, [])
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
        self.assertTrue(all(server.closed for server in h.listeners))

    async def test_generated_exclusion_refreshed_by_scope_validation_withholds_creation(self):
        h = Harness('generated-exclusion-validation-tail')
        h.create()
        actual_policy = h.q.endpoint.policy_authority
        actual_current = h.q.current
        active, excluded = [], []
        def policy(*args):
            active.append(True)
            try:
                return actual_policy(*args)
            finally:
                active.pop()
        def current(action):
            scope = actual_current(action)
            if active and action == 'analysis' and not excluded:
                path = str(h.q.home / 'context/workspace')
                h.q.exclusions += (path,)
                excluded.append(path)
            return scope
        h.q.current = current
        h.q.endpoint.policy_authority = policy
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(len(excluded), 1)
        self.assertEqual(h.provider_calls, 0)
        self.assertEqual(h.prompts, [])
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
        self.assertTrue(all(server.closed for server in h.listeners))


class CurrentExclusionCustody(unittest.IsolatedAsyncioTestCase):
    """Current handling and directory-grant contracts; owned nonsecret mocks.

    No backend exposure is assumed. A policy admitting an ancestor is itself
    inadmissible under the selected safe contract, irrespective of backend detail.
    """
    async def test_retained_budget_never_censuses_a_newly_held_workspace(self):
        h = Harness('current-budget-no-census')
        h.create()
        h.q.before_io(h.q.home / 'context', 'mkdir')
        h.q.budget.reserve(h.q.home / 'context/workspace/retained', 'create', 8193)
        retained = (h.q.budget.bytes, h.q.budget.entries)
        h.q.exclusions += (str(h.q.home / 'context/workspace'),)
        # Even enumeration of the enclosing owned home is unnecessary here.
        with patch.object(driver.os, 'listdir', side_effect=AssertionError('custody census')):
            h.q.capacity(h.q.home)
            h.q.publisher({'synthetic': 'denial remains receivable'})
        self.assertGreaterEqual(h.q.budget.bytes, retained[0])
        self.assertGreaterEqual(h.q.budget.entries, retained[1])
        self.assertIn('UNMEASURED', h.q.budget.last['actual_held_usage'])
        self.assertTrue(h.q.publisher.attempts[-1]['persisted'])

    async def test_preparation_denial_does_not_reacquire_held_metadata(self):
        h = Harness('current-denial-no-held-metadata')
        h.create()
        actual = h.q.endpoint.policy_authority
        held = h.q.home / 'context/workspace'
        changed = []
        def policy(*args):
            if not changed:
                h.q.exclusions += (str(held),)
                changed.append(True)
            return actual(*args)
        h.q.endpoint.policy_authority = policy
        directory = driver.directory
        def admitted(path):
            if Path(path) == held or Path(path).is_relative_to(held):
                raise AssertionError('held directory metadata acquired')
            return directory(path)
        with patch.object(driver, 'directory', side_effect=admitted), \
             patch.object(driver.os, 'listdir', side_effect=AssertionError('denial census')):
            with self.assertRaises(driver.Refusal):
                await h.run()
        self.assertEqual(h.provider_calls, 0)
        self.assertEqual(h.prompts, [])
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
        self.assertTrue(all(server.closed for server in h.listeners))

    async def descendant_boundary(self, root, turn, boundary):
        h = Harness('descendant-%s-%s-%s' % (root, turn, boundary))
        h.create()
        actual = h.q.endpoint.policy_authority
        changed = []
        def policy(filesystem, material, workspace):
            ready = (h.provider_calls == turn - (boundary == 'creation')
                     and h.q.endpoint.context.calls == turn - 1)
            if ready and not changed:
                held = (Path(material) if root == 'material' else Path(workspace)) / 'held-owned-descendant'
                h.q.exclusions += (str(held),)
                changed.append(str(held))
            return actual(filesystem, material, workspace)
        h.q.endpoint.policy_authority = policy
        with patch.object(driver.os, 'listdir', side_effect=AssertionError('held census')):
            with self.assertRaises(driver.Refusal):
                await h.run()
        self.assertEqual(len(changed), 1)
        self.assertEqual(h.provider_calls, turn - (boundary == 'creation'))
        self.assertEqual(len(h.prompts), turn - 1)
        self.assertEqual(len(h.q.answers), max(0, turn - 2))
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
        self.assertTrue(all(server.closed for server in h.listeners))
        if boundary == 'feed':
            receipt = json.loads((h.q.home / ('context/turn-%d/original-0.json' % (turn - 1))).read_text())
            self.assertEqual(receipt['actual_END'], 0)
            self.assertTrue(receipt['evidence']['stdout_eof'])
            self.assertTrue(receipt['evidence']['stderr_eof'])

    async def test_proper_descendant_hold_withholds_initial_creation_and_feed(self):
        for root in ('material', 'workspace'):
            for boundary in ('creation', 'feed'):
                with self.subTest(root=root, boundary=boundary):
                    await self.descendant_boundary(root, 1, boundary)

    async def test_proper_descendant_hold_withholds_substantive_continuation(self):
        for turn in (2, 3):
            for root in ('material', 'workspace'):
                for boundary in ('creation', 'feed'):
                    with self.subTest(turn=turn, root=root, boundary=boundary):
                        await self.descendant_boundary(root, turn, boundary)

    async def test_unrelated_new_hold_keeps_both_answers_and_same_original(self):
        h = Harness('unrelated-current-hold')
        h.create()
        h.q.exclusions += (str(h.q.home / 'unrelated-retained-output'),)
        with patch.object(driver.os, 'listdir', side_effect=AssertionError('unnecessary census')):
            result = await h.run()
        self.assertEqual(len(result['answers']), 2)
        self.assertEqual(h.provider_calls, 3)
        self.assertEqual(len(h.prompts), 3)
        self.assertTrue(all('resume' in argv for argv in h.commands[1:]))
        self.assertEqual(result['status']['state'], 'closed')
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))
        self.assertFalse(h.q.originals.owned)

    async def test_hold_during_capacity_refuses_exact_receipt_before_open(self):
        h = Harness('capacity-refresh-exact-file')
        h.create()
        module = h.q.runtime.direct.review_context
        path = h.q.home / 'new-receipt.json'
        def refresh(parent):
            h.q.exclusions += (str(path),)
            h.q.capacity(parent)
        with patch.object(module.os, 'open', wraps=module.os.open) as opened:
            with self.assertRaises(driver.Refusal):
                module.private_write(path, b'owned', refresh, before_io=h.q.before_io)
            self.assertFalse(any(c.args[0] == path for c in opened.call_args_list))
        self.assertFalse(path.exists())  # Own nonsecret oracle, not an actual hold inquiry.

    async def test_proof_read_is_refused_before_open_after_listener_finalization(self):
        h = Harness('held-proof-input')
        h.create()
        path = h.q.home / 'context/turn-0/stdout.jsonl'
        spawn = h.spawn
        async def intercepted(*args, **kwargs):
            child = await spawn(*args, **kwargs)
            if 'exec' in args:
                finish = child.complete
                def complete(output):
                    finish(output)
                    # All data/EOF are mocked; intervene after its capture has
                    # completed via the Originals publication callback below.
                child.complete = complete
            return child
        h.spawn = intercepted
        publisher = h.q.publisher
        def publish(observation):
            publisher(observation)
            if observation.get('kind') == 'opaque-cli-process':
                h.q.exclusions += (str(path),)
        h.q.endpoint.publish = publish
        # Context.execute receives this exact publisher and refreshes after its
        # registered original has finished, before qualification's proof read.
        with patch.object(Path, 'read_text', autospec=True, side_effect=lambda p, *a, **k:
                (_ for _ in ()).throw(AssertionError('held proof opened')) if p == path
                else Path.read_bytes(p).decode()):
            with self.assertRaises(driver.Refusal):
                await h.run()
        self.assertFalse(h.q.review.status['protection_qualified'])
        self.assertEqual(h.provider_calls, 1)
        self.assertFalse(h.q.originals.owned)

    async def test_capture_hold_keeps_numeric_end_and_pending_evidence(self):
        h = Harness('held-capture-pending')
        h.create()
        held = h.q.home / 'context/turn-0/stdout.jsonl'
        h.q.endpoint.started = lambda: setattr(h.q, 'exclusions', h.q.exclusions + (str(held),))
        module = h.q.runtime.direct.review_context
        real_open = Path.open
        def admitted(path, *args, **kwargs):
            if path == held:
                raise AssertionError('held capture opened')
            return real_open(path, *args, **kwargs)
        with patch.object(Path, 'open', admitted):
            with self.assertRaises(Exception):
                await h.run()
        self.assertEqual(h.provider_calls, 1)
        self.assertEqual(h.prompts, [])
        self.assertEqual(len(h.q.originals.pending), 1)
        entry = next(iter(h.q.originals.pending.values()))
        self.assertEqual(entry['exit'], 0)
        self.assertFalse(entry['evidence_done'])
        self.assertFalse(entry['evidence']['stdout_eof'])
        self.assertTrue(entry['evidence']['stderr_eof'])
        self.assertTrue(entry['evidence']['custody_blocked'])
        self.assertTrue(all(row['persisted'] for row in h.q.publisher.attempts))

    async def test_budget_is_cumulative_and_failed_exclusive_write_stays_charged(self):
        h = Harness('reservation-retention')
        h.create()
        p = h.q.home / 'collision.json'
        module = h.q.runtime.direct.review_context
        module.private_write(p, b'first', h.q.capacity, before_io=h.q.before_io)
        before = (h.q.budget.bytes, h.q.budget.entries)
        with self.assertRaises(FileExistsError):
            module.private_write(p, b'second', h.q.capacity, before_io=h.q.before_io)
        self.assertGreater(h.q.budget.bytes, before[0])
        self.assertGreater(h.q.budget.entries, before[1])
        h.q.exclusions += (str(p),)
        retained = h.q.budget.bytes
        h.q.capacity(h.q.home)
        self.assertEqual(h.q.budget.bytes, retained)
        with self.assertRaises(driver.Refusal):
            h.q.budget.reserve(h.q.home / 'cannot-fit', 'create', 512 * driver.MIB)
        self.assertEqual(h.q.budget.bytes, retained)

    async def test_scope_reader_rechecks_current_exclusions_before_metadata(self):
        h = Harness('current-scope-exclusions')
        path = h.area / 'own-scope.json'
        put(path, b'{"synthetic": true}')
        held = []
        current = driver.scope_reader(path, h.owner, lambda: tuple(held))
        self.assertEqual(current('collect'), {'synthetic': True})
        held.append(str(path))
        with patch.object(driver, 'directory', side_effect=AssertionError('held authority metadata')):
            with self.assertRaises(driver.Refusal):
                current('collect')


    async def test_publication_hold_preserves_attempt_and_allows_next_safe_name(self):
        h = Harness('held-publication-name')
        h.create()
        target = h.q.home / 'publication-0000.json'
        original = h.q.publisher.capacity
        refreshed = []
        def capacity(parent):
            if not refreshed:
                h.q.exclusions += (str(target),)
                refreshed.append(True)
            original(parent)
        h.q.publisher.capacity = capacity
        with self.assertRaises(driver.Refusal):
            h.q.publisher({'synthetic': 'blocked exact receiving name'})
        self.assertFalse(h.q.publisher.attempts[0]['persisted'])
        h.q.publisher({'synthetic': 'new lawful receiving name'})
        self.assertTrue(h.q.publisher.attempts[1]['persisted'])
        self.assertFalse(target.exists())  # Nonsecret synthetic test oracle only.

    async def test_public_counter_hold_is_checked_after_under_lock_routes_read(self):
        h = Harness('current-counter-read')
        h.create()
        pool = h.q.pool.pool
        read_counter = pool.read_counter
        held = h.state / 'codex.counter'
        reached = []
        def current(handle):
            h.q.exclusions += (str(held),)
            reached.append(True)
            # A current hold arrives after the descriptor was lawfully opened.
            with patch.object(driver.os, 'fstat', side_effect=AssertionError('held counter metadata')):
                return read_counter(handle)
        with patch.object(pool, 'read_counter', side_effect=current):
            with self.assertRaises(driver.Refusal):
                pool.allocate(list(driver.PROFILES), blocking=False,
                              expected_control=h.q.pool_control)
        self.assertEqual(reached, [True])
        self.assertEqual(h.provider_calls, 0)

    async def test_external_directory_descendant_refresh_is_checked_at_policy_tail(self):
        h = Harness('external-descendant-at-tail')
        h.create()
        current = h.q.current
        changed = []
        def refresh(action):
            scope = current(action)
            if action == 'analysis' and not changed:
                h.q.exclusions += ('/usr/lib/python3.12/owned-synthetic-hold',)
                changed.append(True)
            return scope
        h.q.current = refresh
        material, workspace = h.q.home / 'context/material', h.q.home / 'context/workspace'
        filesystem = {':root': 'deny', ':minimal': 'read', str(material): 'read',
                      str(workspace): 'read', '/usr/lib/python3.12': 'read'}
        with patch.object(driver, 'directory', side_effect=AssertionError('policy metadata')):
            with self.assertRaises(driver.Refusal):
                h.q.authorize_policy(filesystem, material, workspace)
        self.assertEqual(changed, [True])

    async def test_local_control_hold_after_helper_identity_withholds_creation(self):
        h = Harness('local-owned-read-refresh')
        h.create()
        protection = h.q.endpoint.protection
        helper = protection.probe_helper
        changed = []
        def complete():
            value = helper()
            if not changed:
                h.q.exclusions += (str(h.q.home / 'context/turn-0/protection/outside.txt'),)
                changed.append(True)
            return value
        protection.probe_helper = complete
        with self.assertRaises(driver.Refusal):
            await h.run()
        self.assertEqual(changed, [True])
        self.assertEqual(h.provider_calls, 0)
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(server.closed for server in h.listeners))


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


class HardDeadline(unittest.IsolatedAsyncioTestCase):
    """Delayed boundaries, including real local pipes; no provider protection claim."""
    async def identity_boundary(self, mode):
        h = Harness('identity-tail-' + mode)
        h.create()
        original = h.q.identities
        completed = []
        def identity():
            original()  # Real complete two-pass owned program; helper remains MOCK.
            if h.provider_calls == 1 and not completed:  # On the feed task, once.
                if mode == 'expires':
                    h.scope['expires_at'] = time.time() + .02
                time.sleep(.06)  # Block the event loop beyond the actual scope expiry.
                if mode == 'revoked':
                    h.scope['revoked'] = True
                completed.append(mode)
        h.q.identities = identity
        if mode == 'valid':
            result = await h.run()
            self.assertEqual(len(result['answers']), 2)
            self.assertEqual(len(h.prompts), 3)
        else:
            with self.assertRaises(driver.Refusal):
                await h.run()
            self.assertEqual(h.prompts, [], 'later refusal cannot unsend a prompt')
            self.assertFalse(h.q.review.status['protection_qualified'])
            self.assertEqual(h.q.answers, [])
        self.assertEqual(completed, [mode])
        self.assertFalse(h.q.originals.owned)
        self.assertTrue(all(p['persisted'] for p in h.q.publisher.attempts))
        self.assertTrue(all(s.closed for s in h.listeners))
        for p in h.q.home.glob('context/turn-0/original-*.json'):
            receipt = json.loads(p.read_text())
            self.assertIsInstance(receipt['actual_END'], int)
            self.assertTrue(receipt['evidence']['stdout_eof'])
            self.assertTrue(receipt['evidence']['stderr_eof'])

    async def test_scope_expiry_during_complete_identity_withholds_and_collects(self):
        await self.identity_boundary('expires')

    async def test_revocation_during_complete_identity_withholds_and_collects(self):
        await self.identity_boundary('revoked')

    async def test_complete_delayed_identity_with_valid_scope_still_works(self):
        await self.identity_boundary('valid')

    async def test_permission_validation_cost_cannot_outlive_scope(self):
        h = Harness('scope-validation-cost')
        h.create()
        describe = h.q.describe_binding
        def delayed_description():
            value = describe()
            time.sleep(.06)
            return value
        h.scope['expires_at'] = time.time() + .02
        with patch.object(h.q, 'describe_binding', side_effect=delayed_description):
            with self.assertRaises(driver.Refusal):
                h.q.check('analysis')
            # Continuing original custody is independent of processing expiry.
            self.assertTrue(h.q.check('collect')['custody_allowed'])
            self.assertTrue(h.q.check('publish')['custody_allowed'])

    async def pipe_boundary(self, mode):
        h = Harness('real-deadline-' + mode)
        out = fresh(h.area, 'actual-pipe')
        book = h.q.runtime.appserver.Originals().scope()
        rows, phases = [], []
        class DelayedText(str):
            def encode(self, *args, **kwargs):
                if mode == 'encoding':
                    phases.append('encoding')
                    time.sleep(.25)
                return super().encode(*args, **kwargs)
        def current():
            self.assertEqual(len(book.owned), 1)
            phases.append('authority')
            time.sleep(.25 if mode == 'authority' else .01)
        async def run():
            return await h.q.runtime.direct.review_context.execute(
                ['/usr/bin/python3', '-I', '-S', '-B', '-c',
                 'import sys,json;print(json.dumps(dict(type="turn.completed", byte_count=len(sys.stdin.buffer.read()))))'],
                {'PATH': '/usr/bin:/bin'}, DelayedText('owned nonsecret text'), out,
                book, rows.append, 3 if mode == 'valid' else .15, 3,
                65536, 65536, None, lambda: None,
                capacity_check=guard, before_feed=current)
        if mode == 'valid':
            await run()
            self.assertEqual(json.loads((out / 'stdout.jsonl').read_bytes())['byte_count'], 20)
        else:
            with self.assertRaises(h.q.runtime.direct.review_context.ReviewRefusal):
                await run()
            self.assertEqual(json.loads((out / 'stdout.jsonl').read_bytes())['byte_count'], 0)
        self.assertIn('authority', phases)
        if mode == 'encoding':
            self.assertEqual(phases, ['encoding', 'authority'])
        self.assertFalse(book.owned)
        self.assertIsInstance(rows[-1]['exit'], int)
        self.assertTrue(rows[-1]['evidence']['stdout_eof'])
        self.assertTrue(rows[-1]['evidence']['stderr_eof'])

    async def test_execute_expiry_during_blocked_authority_real_pipe(self):
        await self.pipe_boundary('authority')

    async def test_execute_expiry_during_encoding_real_pipe(self):
        await self.pipe_boundary('encoding')

    async def test_execute_delayed_valid_feed_real_pipe(self):
        await self.pipe_boundary('valid')

    async def test_context_original_deadline_survives_blocked_authority(self):
        h = Harness('real-context-deadline')
        module = h.q.runtime.direct.review_context
        book = h.q.runtime.appserver.Originals().scope()
        rows, checks = [], []
        context = module.Context(h.area / 'short-context', '.codex2', h.owner,
            1, book, executable='/usr/bin/python3', capacity_check=guard)
        def current():
            if book.owned:
                checks.append('feed')
                time.sleep(1.1)  # Real fixed original expires before callback returns.
        argv = ['/usr/bin/python3', '-I', '-S', '-B', '-c',
                'import sys,json;print(json.dumps(dict(type="turn.completed", byte_count=len(sys.stdin.buffer.read()))))']
        out = h.area / 'actual-turn'
        with patch.object(module, 'command', return_value=argv):
            with self.assertRaises(module.ReviewRefusal):
                await context.turn(out, [('nonsecret fixture', b'owned text')],
                    'owned nonsecret instruction', collector=h.owner, profile='.codex2',
                    current_authority=current, current_profiles=['.codex2'],
                    publish=rows.append, maximum=65536, capture_max=65536, shutdown=3)
        self.assertEqual(checks, ['feed'])
        self.assertEqual(json.loads((out / 'stdout.jsonl').read_bytes())['byte_count'], 0)
        self.assertEqual(context.state, 'interrupted')
        self.assertFalse(book.owned)
        self.assertTrue(rows[-1]['evidence']['stdout_eof'])
        self.assertTrue(rows[-1]['evidence']['stderr_eof'])
        self.assertTrue(context.close(h.owner)['caller_processes_collected'])


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
