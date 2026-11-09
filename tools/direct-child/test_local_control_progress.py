"""Local control failure outcomes over real, newly owned Python subprocesses.

No provider or native context runs. Retain every fixture; require an explicit
owned REVIEW_FIXTURE_ROOT. These controls test unsuccessful finalization and
local close, separately from protection, receiving or whole processing.
"""
import asyncio
import errno
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

import continuing_review as cr
import review_context as rc
sys.path.insert(0, str(Path(__file__).absolute().parents[1] / 'coordinator-runtime'))
from coordinator_runtime import appserver


def capacity(parent):
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        v = os.fstatvfs(fd)
        if v.f_bavail*v.f_frsize-2*1024**3 < 100*1024**3 or v.f_favail-32000 < 1000000:
            raise RuntimeError('full local-control phase allowance unavailable')
    finally:
        os.close(fd)


class LocalControlProgress(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        parent = Path(os.environ['REVIEW_FIXTURE_ROOT'])
        capacity(parent)
        self.root = parent / str(uuid4())
        self.root.mkdir(mode=0o700)
        self.book, self.published = appserver.Originals(), []
        self.context = SimpleNamespace(originals=self.book.scope(), account_home=str(self.root),
            profile='.codex5', created=time.monotonic(), lifetime=60, clock=time.monotonic,
            workspace=self.root, busy=False, collector='fixture-collector', state='interrupted')
        self.protection = cr.SandboxProtection(self.root, '/usr/bin/python3', ['/usr'], capacity)

    async def asyncTearDown(self):
        capacity(self.root)
        rc.private_write(self.root/'observations.json', json.dumps(dict(published=self.published,
            pending=[self.book.observation(k) for k in self.book.owned])).encode(), capacity)

    async def run_control(self, script='print(\'{"fixture":"local"}\')', publish=None):
        return await self.protection._run(self.context, self.root, 'control',
            ['/usr/bin/python3', '-c', script], publish or self.published.append)

    def receipt(self, name='control.original.json'):
        return json.loads((self.root/name).read_text())

    def collected_failure(self, row, stdout_eof=False):
        self.assertIs(type(row['actual_END']), int)
        self.assertEqual(row['evidence']['stdout_eof'], stdout_eof)
        self.assertTrue(row['evidence']['stderr_eof'])
        self.assertFalse(row['evidence']['capture_complete'])
        self.assertTrue(row['evidence']['errors'])
        self.assertTrue(self.published[-1]['evidence_complete'])
        self.assertFalse(self.book.pending)
        self.assertFalse(self.context.originals.owned)
        closed = rc.Context.close(self.context, 'fixture-collector')
        self.assertTrue(closed['local_owner_closed'])
        self.assertFalse(closed['processing_completion'])
        self.assertFalse(self.protection.proofs)

    async def test_success_retains_actual_EOF_and_persisted_original(self):
        self.assertEqual(await self.run_control(), {'fixture':'local'})
        row = self.receipt()
        self.assertEqual(row['actual_END'], 0)
        self.assertTrue(row['evidence']['stdout_eof'])
        self.assertTrue(row['evidence']['stderr_eof'])
        self.assertTrue(row['evidence']['capture_complete'])
        self.assertEqual(self.published[-1]['evidence']['receipt'], 'control.original.json')
        self.assertFalse(self.book.owned)
        self.assertFalse(self.protection.proofs)  # One local result is not a qualification.

    async def test_capture_admission_failure_finalizes_unsuccessfully_without_replay(self):
        checks = []
        def check(parent):
            capacity(parent)
            checks.append(parent)
            if len(checks) == 2:
                raise OSError(errno.ENOSPC, 'authored capture admission fault')
        self.protection.capacity_check = check
        with self.assertRaises(cr.Refusal):
            await self.run_control()
        self.collected_failure(self.receipt())
        self.assertIn('stdout capture failed: OSError', self.receipt()['evidence']['errors'])
        self.assertFalse((self.root/'control.stdout').exists())

    async def test_capture_open_failure_keeps_unknown_EOF_and_allows_local_close(self):
        real_open = Path.open
        def fail(path, *args, **kwargs):
            if path == self.root/'control.stdout' and args == ('xb',):
                raise OSError(errno.EIO, 'authored open fault')
            return real_open(path, *args, **kwargs)
        with patch.object(Path, 'open', new=fail), self.assertRaises(cr.Refusal):
            await self.run_control()
        self.collected_failure(self.receipt())

    async def test_read_failure_preserves_prefix_and_does_not_invent_EOF(self):
        spawn = cr.asyncio.create_subprocess_exec
        async def wrapped(*args, **kwargs):
            child = await spawn(*args, **kwargs)
            reader = child.stdout
            class Reader:
                calls = 0
                async def read(self, amount):
                    self.calls += 1
                    if self.calls > 1:
                        raise OSError(errno.EIO, 'authored pipe read fault')
                    return await reader.read(amount)
            child.stdout = Reader()
            return child
        with patch.object(cr.asyncio, 'create_subprocess_exec', side_effect=wrapped), self.assertRaises(cr.Refusal):
            await self.run_control()
        self.assertEqual((self.root/'control.stdout').read_bytes(), b'{"fixture":"local"}\n')
        self.collected_failure(self.receipt())

    async def capture_write_fault(self, after_eof=False):
        real_open = Path.open
        class Stream:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args):
                result = self.stream.__exit__(*args)
                if after_eof: raise OSError(errno.EIO, 'authored close/flush fault')
                return result
            def write(self, body):
                if after_eof: return self.stream.write(body)
                self.stream.write(body[:7]); self.stream.flush()
                raise OSError(errno.EIO, 'authored partial capture write')
        def fail(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            return Stream(stream) if path == self.root/'control.stdout' and args == ('xb',) else stream
        with patch.object(Path, 'open', new=fail), self.assertRaises(cr.Refusal):
            await self.run_control()
        self.collected_failure(self.receipt(), stdout_eof=after_eof)
        return (self.root/'control.stdout').read_bytes()

    async def test_partial_capture_write_retains_actual_failed_bytes(self):
        self.assertEqual(await self.capture_write_fault(), b'{"fixtu')

    async def test_real_EOF_can_coexist_with_failed_capture_flush(self):
        self.assertEqual(await self.capture_write_fault(after_eof=True), b'{"fixture":"local"}\n')

    async def test_receipt_failures_retain_same_original_prefixes_and_publish_only_retry(self):
        real_write = cr.private_write
        failed = []
        deliveries = []
        def persist(path, body, check):
            if '.original' in path.name and len(failed) < 2:
                failed.append(path)
                check(path.parent)
                with path.open('xb') as stream:
                    stream.write(body[:19])
                raise OSError(errno.ENOSPC, 'authored partial evidence write')
            return real_write(path, body, check)
        def publish(row):
            deliveries.append(row)
            if row['evidence_complete'] and sum(r['evidence_complete'] for r in deliveries) == 1:
                raise OSError(errno.EIO, 'authored publication failure')
            self.published.append(row)
        with patch.object(cr, 'private_write', side_effect=persist):
            with self.assertRaises(appserver.CollectionPending) as first:
                await self.run_control(publish=publish)
            key = first.exception.original
            entry = self.book.owned[key]
            self.assertIs(type(entry['exit']), int)
            self.assertFalse(entry['evidence_done'])
            with self.assertRaises(rc.ReviewRefusal): rc.Context.close(self.context, 'fixture-collector')
            with self.assertRaises(appserver.CollectionPending) as second:
                await self.book.finish(key, 3)
            self.assertEqual(second.exception.original, key)
            self.assertIs(self.book.owned[key], entry)
            residues = [p.read_bytes() for p in failed]
            with self.assertRaises(appserver.CollectionPending): await self.book.finish(key, 3)
            final_path = self.root/'control.original-2.json'
            final_bytes = final_path.read_bytes()
            self.assertTrue(entry['evidence_done'])
            self.assertEqual(await self.book.finish(key, 3), entry['exit'])
        self.assertEqual([p.read_bytes() for p in failed], residues)
        self.assertEqual(final_path.read_bytes(), final_bytes)
        self.assertFalse((self.root/'control.original-3.json').exists())
        self.assertEqual({r['original'] for r in deliveries}, {key})
        self.assertEqual(self.receipt(final_path.name)['receipt_attempts'],
            ['control.original.json', 'control.original-1.json', 'control.original-2.json'])
        self.assertEqual({r['stage'] for r in self.published[-1]['failures']}, {'evidence','delivery'})
        self.assertTrue(rc.Context.close(self.context, 'fixture-collector')['local_owner_closed'])

    async def test_failed_capture_and_receipt_then_same_original_unsuccessful_finalization(self):
        checks = []
        def check(parent):
            capacity(parent)
            checks.append(parent)
            if len(checks) == 2:
                raise OSError(errno.ENOSPC, 'authored capture admission fault')
        self.protection.capacity_check = check
        real_write = cr.private_write
        failed = []
        def persist(path, body, check):
            if not failed:
                failed.append(path)
                check(path.parent)
                with path.open('xb') as stream: stream.write(body[:11])
                raise OSError(errno.EIO, 'authored incomplete receipt')
            return real_write(path, body, check)
        owner = dict(vars(self.context))
        with patch.object(cr, 'private_write', side_effect=persist):
            with self.assertRaises(appserver.CollectionPending) as caught: await self.run_control()
            key = caught.exception.original
            entry = self.book.owned[key]
            self.assertFalse(entry['evidence']['stdout_eof'])
            self.assertFalse(entry['evidence']['capture_complete'])
            self.assertFalse(entry['evidence']['receipt_persisted'])
            residue = failed[0].read_bytes()
            code = await self.book.finish(key, 3)
        self.assertEqual(failed[0].read_bytes(), residue)
        row = self.receipt('control.original-1.json')
        self.assertEqual(row['original'], key)
        self.assertEqual(row['actual_END'], code)
        self.assertEqual(vars(self.context), owner)
        self.assertTrue(self.published[-1]['evidence']['receipt_persisted'])
        self.collected_failure(row)

    async def test_persistent_storage_refusal_remains_pending_until_same_owner_can_persist(self):
        def refuse(path, body, check):
            raise OSError(errno.ENOSPC, 'authored persistent evidence storage refusal')
        with patch.object(cr, 'private_write', side_effect=refuse):
            with self.assertRaises(appserver.CollectionPending) as caught: await self.run_control()
            key = caught.exception.original
            with self.assertRaises(appserver.CollectionPending): await self.book.finish(key, 3)
            self.assertFalse(self.book.owned[key]['evidence_done'])
            self.assertIs(self.book.pending[key], self.book.owned[key])
            with self.assertRaises(rc.ReviewRefusal): rc.Context.close(self.context, 'fixture-collector')
        await self.book.finish(key, 3)
        self.assertFalse(self.book.owned)
        self.assertTrue(self.receipt('control.original-2.json')['evidence']['capture_complete'])

    async def test_unknown_END_cannot_discharge_original_even_with_complete_capture(self):
        spawn = cr.asyncio.create_subprocess_exec
        actual = []
        async def wrapped(*args, **kwargs):
            child = await spawn(*args, **kwargs)
            actual.append((child, child.wait))
            async def unavailable_wait():
                raise OSError(errno.EIO, 'authored wait observation unavailable')
            child.wait = unavailable_wait
            return child
        try:
            with patch.object(cr.asyncio, 'create_subprocess_exec', side_effect=wrapped):
                with self.assertRaises(appserver.CollectionPending) as caught: await self.run_control()
            key = caught.exception.original
            self.assertIsNone(self.book.owned[key]['exit'])
            self.assertTrue(self.book.owned[key]['evidence_done'])
            self.assertIsNone(self.receipt()['actual_END'])
            with self.assertRaises(rc.ReviewRefusal): rc.Context.close(self.context, 'fixture-collector')
        finally:
            for child, wait in actual: child.wait = wait
            await self.book.collect_pending(3)
        self.assertIs(type(self.receipt('control.original-1.json')['actual_END']), int)
        self.assertFalse(self.book.owned)

    async def test_nonzero_and_stderr_are_still_refusals_after_collection(self):
        with self.assertRaises(cr.Refusal):
            await self.run_control('import sys;print("adverse",file=sys.stderr);sys.exit(7)')
        row = self.receipt()
        self.assertEqual(row['actual_END'], 7)
        self.assertTrue(row['evidence']['capture_complete'])
        self.assertEqual((self.root/'control.stderr').read_bytes(), b'adverse\n')
        self.assertFalse(self.book.owned)
        self.assertFalse(self.protection.proofs)

    async def test_oversized_capture_refuses_and_retains_the_bound(self):
        with self.assertRaises(cr.Refusal):
            await self.run_control('import os;os.write(1,b"x"*70000)')
        row = self.receipt()
        self.assertIs(type(row['actual_END']), int)
        self.assertFalse(row['evidence']['capture_complete'])
        self.assertIn('bounded capture exceeded', row['evidence']['errors'])
        self.assertLessEqual((self.root/'control.stdout').stat().st_size, 65536)
        self.assertFalse(self.book.owned)


if __name__ == '__main__': unittest.main()
