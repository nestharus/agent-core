"""DECISION1218 controls; newly owned, retained, explicitly fictional transport.

Only the receipt tests start processes: a local non-provider Python fixture.
Canary-shaped records test interpretation, never qualify an actual provider.
"""
import asyncio
import errno
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

import continuing_review as cr
import review_context as rc
from opaque_dialogue import Reply, Refusal
sys.path.insert(0, str(Path(__file__).absolute().parents[1] / 'coordinator-runtime'))
from coordinator_runtime.appserver import Originals, CollectionPending

GOOD = dict(allowed={'read':'owned-allowed-canary'}, outside={'error':errno.ENOENT},
            write={'error':errno.EROFS}, network={'error':errno.EPERM})


def event(command='exact canary', result=None, **overrides):
    item = dict(type='command_execution', command=command, exit_code=0,
                status='completed', aggregated_output=json.dumps(GOOD if result is None else result))
    item.update(overrides)
    return json.dumps(dict(type='item.completed', item=item))


def capacity(parent):
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        v = os.fstatvfs(fd)
    finally:
        os.close(fd)
    if v.f_bavail*v.f_frsize-1073741824 < 107374182400 or v.f_favail-20000 < 1000000:
        raise RuntimeError('full 1218 phase headroom unavailable')


class CanaryEvidence(unittest.TestCase):
    def test_one_exact_favorable_with_unrelated_failure(self):
        """One exact favorable operation qualifies; unrelated failures are retained, not silently relabeled."""
        capture = event('unrelated', exit_code=1) + '\n' + event()
        self.assertEqual(cr.acting_proof(capture, 'exact canary'), GOOD)

    def test_adverse_exact_before_favorable_is_rejected(self):
        """Retained adverse exact evidence cannot disappear beside a favorable exact result."""
        bad = {**GOOD, 'write':'succeeded'}
        with self.assertRaises(Refusal):
            cr.acting_proof(event(result=bad)+'\n'+event(), 'exact canary')

    def test_adverse_exact_after_favorable_is_rejected(self):
        """Evidence order cannot hide the contradictory exact operation."""
        bad = {**GOOD, 'outside':{'read':'outside bytes'}}
        with self.assertRaises(Refusal):
            cr.acting_proof(event()+'\n'+event(result=bad), 'exact canary')

    def test_duplicate_exact_even_failed_or_malformed_is_rejected(self):
        """Uniqueness counts exact commands before result interpretation, including unsuccessful attempts."""
        for extra in [event(), event(exit_code=1), event(status='failed'),
                      event(aggregated_output='not JSON'), event(exit_code=False)]:
            with self.subTest(extra=extra), self.assertRaises(Refusal):
                cr.acting_proof(event()+'\n'+extra, 'exact canary')

    def test_one_adverse_or_badly_typed_exact_never_qualifies(self):
        """Every required operation has discriminating structured evidence; malformed types refuse precisely."""
        for result in [[], None, {'allowed':[]}, {**GOOD,'network':{'error':True}},
                       {**GOOD,'write':'succeeded'}, {**GOOD,'allowed':{'read':'wrong'}}]:
            with self.subTest(result=result), self.assertRaises(Refusal):
                cr.acting_proof(event(aggregated_output=json.dumps(result)), 'exact canary')


class Retained(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        parent = Path(os.environ['REVIEW_FIXTURE_ROOT'])
        capacity(parent)
        self.root = parent / str(uuid4())
        self.root.mkdir(mode=0o700)
        self.book, self.published = Originals(), []

    async def asyncTearDown(self):
        rows = dict(published=self.published,
                    pending=[self.book.observation(key) for key in self.book.owned])
        self.write(self.root/'originals.json', json.dumps(rows,indent=2).encode())

    def write(self, path, body):
        capacity(path.parent)
        path.write_bytes(body)

    def review(self):
        """Fictional endpoint supplies owned canary-shaped output, with no CLI or provider execution."""
        root = self.root
        case = self
        class Endpoint:
            capacity_check = staticmethod(capacity)
            receipts = []
            def __init__(self):
                self.root = root
                self.inputs = []
            async def open(self, owner):
                return self
            async def exchange(self, handle, owner, thread, text, channel):
                self.inputs.append((text, channel.manifest()))
                if len(self.inputs) == 1:
                    directory = root / 'turn-0'
                    capacity(directory.parent)
                    directory.mkdir()
                    case.write(directory/'stdout.jsonl', event(text.split('Return a short factual account.\n', 1)[1]).encode())
                    self.receipts.append(dict(answered=True, capture_complete=True))
                return Reply('fictional-thread', 'fictional response', True)
            async def close(self, handle, owner):
                return dict(fixture_closed=True)
        endpoint = Endpoint()
        return cr.ContinuingReview(endpoint, 'gpt-xhigh', '.codex5', 'fixture-owner', lambda o:None)

    async def test_failed_qualification_persistence_withholds_catch_and_reuse(self):
        """An actual post-create fsync exception leaves residue, no qualified state, no substantive delivery or replay."""
        review = self.review()
        real_write = cr.private_write
        def fail(path, body, check):
            if path.name == 'acting-proof.json':
                with patch.object(rc.os, 'fsync', side_effect=OSError(errno.EIO,'injected fsync')):
                    return real_write(path, body, check)
            return real_write(path, body, check)
        with patch.object(cr, 'private_write', side_effect=fail), self.assertRaises(OSError):
            await review.qualify()
        self.assertTrue((self.root/'turn-0/acting-proof.json').exists())
        self.assertFalse(review.status['protection_qualified'])
        with self.assertRaises(Refusal):
            await review.turn('substantive', {'source':b'source'})
        with self.assertRaises(Refusal):
            await review.qualify()
        self.assertEqual(len(review.endpoint.inputs),1)
        self.assertTrue((await review.close())['fixture_closed'])

    async def test_successful_qualification_then_same_owned_followon(self):
        """Qualification is committed only after its receipt; the subsequent call retains ownership and lifetime."""
        review = self.review()
        owner = review.ownership
        self.assertEqual(await review.qualify(), GOOD)
        self.assertEqual(json.loads((self.root/'turn-0/acting-proof.json').read_text()),GOOD)
        self.assertTrue(review.status['protection_qualified'])
        self.assertTrue((await review.turn('follow on', {'source':b'nonsecret'})).complete)
        self.assertIs(review.ownership,owner)
        self.assertEqual(len(review.endpoint.inputs),2)
        await review.close()

    async def test_no_admission_while_qualification_persistence_is_running(self):
        """The next-input gate remains closed during the fallible persistence boundary."""
        review = self.review()
        real_write = cr.private_write
        def inspect(path, body, check):
            if path.name == 'acting-proof.json':
                self.assertFalse(review.status['protection_qualified'])
            return real_write(path, body, check)
        with patch.object(cr,'private_write',side_effect=inspect):
            await review.qualify()
        await review.close()

    async def test_listener_finalization_failure_cannot_commit_qualification(self):
        """A later listener-close error also leaves admission unqualified, despite a persisted favorable proof."""
        review = self.review()
        class Socket:
            def getsockname(self):return ('127.0.0.1',1)
        class Server:
            sockets=[Socket()]
            def close(self):return None
            async def wait_closed(self):raise OSError(errno.EIO,'injected listener finalization')
        with patch.object(cr.asyncio,'start_server',return_value=Server()), self.assertRaises(OSError):
            await review.qualify()
        self.assertFalse(review.status['protection_qualified'])
        with self.assertRaises(Refusal):await review.turn('source',{'source':b'nonsecret'})
        self.assertEqual(len(review.endpoint.inputs),1)
        await review.close()

    async def execute(self, publish=None):
        out = self.root/'capture'
        capacity(out.parent)
        out.mkdir()
        script = ('import sys\nsys.stdin.read()\n'
                  'print(\'{"type":"thread.started","thread_id":"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}\')\n'
                  'print(\'{"type":"turn.completed"}\')\n')
        return await rc.execute(['/usr/bin/python3','-c',script],{'PATH':'/usr/bin:/bin'},'',out,
            self.book,publish or self.published.append,10,3,65536,65536,None,lambda:None,
            capacity_check=capacity)

    async def receipt_failure(self, stage):
        real_write, fdopen = rc.private_write, rc.os.fdopen
        fired = []
        class Stream:
            def __init__(self, stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def write(self, body):
                if stage == 'write':
                    self.stream.write(body[:17])
                    raise OSError(errno.EIO,'injected partial write')
                return self.stream.write(body)
            def flush(self):
                self.stream.flush()
                if stage == 'flush':raise OSError(errno.EIO,'injected flush')
        def fail(path, body, check):
            if path.name.startswith('original-') and not fired:
                fired.append(str(path))
                if stage == 'precreate':raise OSError(errno.ENOSPC,'injected before create')
                if stage == 'fsync':
                    with patch.object(rc.os,'fsync',side_effect=OSError(errno.EIO,'injected fsync')):
                        return real_write(path,body,check)
                with patch.object(rc.os,'fdopen',side_effect=lambda *a,**k:Stream(fdopen(*a,**k))):
                    return real_write(path,body,check)
            return real_write(path,body,check)
        try:
            with patch.object(rc,'private_write',side_effect=fail):
                await self.execute()
        except CollectionPending as exc:
            key = exc.original
        else:
            self.fail('injected persistence failure must retain exact ownership')
        self.assertEqual(self.book.owned[key]['exit'],0)
        self.assertFalse(self.book.owned[key]['evidence_done'])
        self.assertIs(self.book.pending[key],self.book.owned[key])
        old = self.root/'capture/original-0.json'
        residue = old.read_bytes() if old.exists() else None
        self.assertEqual(await self.book.finish(key,3),0)
        self.assertFalse(self.book.owned)
        self.assertFalse(self.book.pending)
        self.assertEqual(old.read_bytes() if old.exists() else None,residue)
        receipt = json.loads((self.root/'capture/original-1.json').read_text())
        self.assertEqual(receipt['actual_END'],0)
        self.assertTrue(receipt['evidence']['stdout_eof'])
        self.assertTrue(receipt['evidence']['stderr_eof'])
        self.assertEqual(self.published[-1]['original'],key)
        self.assertTrue(self.published[-1]['evidence_complete'])
        self.assertTrue(any(f['stage']=='evidence' for f in self.published[-1]['failures']))

    async def test_postcreate_partial_write_retry_preserves_residue(self):
        """After partial write failure, same original finalizes into a new receipt without changing the failed bytes."""
        await self.receipt_failure('write')

    async def test_postcreate_flush_retry_preserves_residue(self):
        """After flush failure, normal exact-owner retry progresses and preserves the occupied original pathname."""
        await self.receipt_failure('flush')

    async def test_postcreate_fsync_retry_preserves_residue(self):
        """Known END and EOF survive fsync failure; restored persistence allows same-owner collection."""
        await self.receipt_failure('fsync')

    async def test_precreate_failure_retry_has_no_false_receipt(self):
        """Pre-create capacity failure leaves no first receipt and still permits bounded same-owner finalization."""
        await self.receipt_failure('precreate')

    async def test_capture_failure_does_not_become_EOF_or_answer(self):
        """Successful evidence publication can retain numeric END with explicitly incomplete capture and no answer."""
        real_open = Path.open
        def fail_stdout(path, *args, **kwargs):
            if path.name == 'stdout.jsonl' and args and args[0] == 'xb':
                raise OSError(errno.EIO,'injected capture open failure')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',new=fail_stdout):
            code, receipt, answer = await self.execute()
        self.assertIs(type(code),int)
        self.assertEqual(self.published[-1]['exit'],code)
        self.assertTrue(self.published[-1]['evidence_complete'])
        self.assertFalse(receipt['stdout_eof'])
        self.assertFalse(receipt['capture_complete'])
        self.assertFalse(receipt['answered'])
        self.assertTrue(receipt['errors'])
        self.assertFalse(self.book.owned)

    async def test_repeated_receipt_failure_retains_each_attempt_then_progresses(self):
        """Repeated persistence failures keep one original and all failed bytes; restored storage permits progress."""
        real_write = rc.private_write
        paths=[]
        def fail(path, body, check):
            if path.name.startswith('original-') and len(paths) < 2:
                paths.append(path)
                with patch.object(rc.os,'fsync',side_effect=OSError(errno.EIO,'injected fsync')):
                    return real_write(path,body,check)
            return real_write(path,body,check)
        with patch.object(rc,'private_write',side_effect=fail):
            with self.assertRaises(CollectionPending) as first:await self.execute()
            key=first.exception.original
            with self.assertRaises(CollectionPending) as second:await self.book.finish(key,3)
            self.assertEqual(second.exception.original,key)
            residues=[p.read_bytes() for p in paths]
            self.assertEqual(await self.book.finish(key,3),0)
        self.assertEqual([p.read_bytes() for p in paths],residues)
        self.assertEqual([p.name for p in paths],['original-0.json','original-1.json'])
        last=json.loads((self.root/'capture/original-2.json').read_text())
        self.assertEqual(last['actual_END'],0)
        self.assertTrue(last['evidence']['stdout_eof'])
        self.assertEqual(self.published[-1]['original'],key)
        self.assertEqual(sum(f['stage']=='evidence' for f in self.published[-1]['failures']),2)
        self.assertFalse(self.book.owned)

    async def test_publication_only_retry_does_not_rewrite_receipt(self):
        """Publication-only failure retains ownership and retries delivery without another evidence write."""
        observations=[]
        def publish(row):
            observations.append(row)
            if len(observations)==1:raise OSError(errno.EIO,'injected publication failure')
        with self.assertRaises(CollectionPending) as caught:await self.execute(publish)
        key=caught.exception.original
        path=self.root/'capture/original-0.json'
        before=path.read_bytes()
        self.assertEqual(await self.book.finish(key,3),0)
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse((self.root/'capture/original-1.json').exists())
        self.assertEqual([x['original'] for x in observations],[key,key])
        self.assertFalse(self.book.owned)


if __name__ == '__main__':unittest.main()
