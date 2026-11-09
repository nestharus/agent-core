"""DECISION1228 QF: real local Python pipes, authored fictional protocol only.

Malformed kinds/handler faults reject semantics but do not strand same-owner
normal evidence finalization. No provider/model/native/protection claim.
"""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import review_context as rc
import continuing_review as cr
from coordinator_runtime.appserver import CollectionPending
from test_review_realization import Retained, capacity, event

THREAD = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


class ProtocolFinalization1230(Retained):
    async def stream(self, rows, publish=None, check=capacity, name='capture'):
        out = self.root/name
        capacity(out.parent); out.mkdir()
        data = ('\n'.join(json.dumps(row) for row in rows)+'\n').encode()
        script = 'import os,sys\nsys.stdin.read()\nos.write(1,'+repr(data)+')\n'
        result = await rc.execute(['/usr/bin/python3','-c',script], {'PATH':'/usr/bin:/bin'},'',out,
            self.book, publish or self.published.append, 10, 3, 65536, 65536, None, lambda:None,
            capacity_check=check)
        self.assertEqual((out/'stdout.jsonl').read_bytes(), data)
        return result

    def rows(self, bad):
        return [dict(type='thread.started', thread_id=THREAD), bad,
                dict(type='item.completed', item=dict(type='agent_message', text='fictional later answer')),
                dict(type='turn.completed')]

    def rejected(self, code, receipt):
        self.assertIs(type(code), int)
        self.assertEqual(receipt['actual_END'], code)
        self.assertTrue(receipt['stdout_eof']); self.assertTrue(receipt['stderr_eof'])
        self.assertFalse(receipt['capture_complete']); self.assertFalse(receipt['answered'])
        self.assertTrue(receipt['turn_failed']); self.assertTrue(receipt['errors'])
        self.assertFalse(self.book.owned); self.assertFalse(self.book.pending)
        self.assertTrue(self.published[-1]['evidence_complete'])
        self.assertFalse(receipt['processing_completion'] if 'processing_completion' in receipt else False)

    async def test_decoded_invalid_kinds_retain_full_transcript_and_finalize_rejection(self):
        for index, kind in enumerate([17, [], {}, None]):
            with self.subTest(kind=kind):
                code, receipt, answer = await self.stream(self.rows(dict(type=kind)), name='kind-'+str(index))
                self.rejected(code, receipt)
                self.assertIsNone(answer)
                self.assertEqual(receipt['turn_completed'], 0)

    async def test_unhashable_item_kind_is_protocol_failure_with_actual_EOF(self):
        code, receipt, answer = await self.stream(self.rows(dict(type='item.completed', item=dict(type=[]))))
        self.rejected(code, receipt); self.assertIsNone(answer)

    async def test_handler_exception_drains_without_accepting_later_success(self):
        with patch.object(rc, 'diagnostic', side_effect=RuntimeError('injected handler fault')):
            code, receipt, answer = await self.stream(self.rows(dict(type='error', message='fictional diagnostic')))
        self.rejected(code, receipt); self.assertIsNone(answer)
        self.assertTrue(any('handler failed: RuntimeError' in e for e in receipt['errors']))

    async def test_failed_capture_task_can_finalize_without_false_EOF(self):
        calls = []
        def check(parent):
            capacity(parent); calls.append(parent)
            if len(calls) == 1: raise RuntimeError('injected capture handler boundary')
        # Failure before stdout reads leaves stdout EOF unknown, even if END is known.
        out = self.root/'capture'; capacity(out.parent); out.mkdir()
        code, receipt, _ = await rc.execute(['/usr/bin/python3','-c','import sys;sys.stdin.read()'],
            {'PATH':'/usr/bin:/bin'},'',out,self.book,self.published.append,10,3,65536,65536,None,
            lambda:None, capacity_check=check)
        self.assertIs(type(code),int); self.assertFalse(receipt['stdout_eof'])
        self.assertTrue(receipt['stderr_eof']); self.assertFalse(receipt['capture_complete'])
        self.assertFalse(receipt['answered']); self.assertFalse(self.book.owned)
        self.assertIn('capture task failed: RuntimeError',receipt['errors'])

    async def test_protocol_fault_storage_and_publication_retry_keep_same_original_and_failed_bytes(self):
        real_write = rc.private_write
        fired = []
        def fail(path, value, check):
            if path.name == 'original-0.json' and not fired:
                fired.append(path)
                with patch.object(rc.os, 'fsync', side_effect=OSError('injected receipt fsync')):
                    return real_write(path,value,check)
            return real_write(path,value,check)
        deliveries = []
        def publish(row):
            deliveries.append(row)
            if row['evidence_complete'] and sum(r['evidence_complete'] for r in deliveries)==1:
                raise OSError('injected publication failure')
            self.published.append(row)
        with patch.object(rc,'private_write',side_effect=fail):
            with self.assertRaises(CollectionPending) as first:
                await self.stream(self.rows(dict(type=17)), publish)
            key=first.exception.original
            original_entry=self.book.owned[key]
            residue=fired[0].read_bytes()
            self.assertIs(type(original_entry['exit']),int)
            self.assertFalse(original_entry['evidence_done'])
            with self.assertRaises(CollectionPending) as second: await self.book.finish(key,3)
            self.assertEqual(second.exception.original,key)
            self.assertIs(self.book.owned[key],original_entry)
            evidence=(self.root/'capture/original-1.json').read_bytes()
            self.assertEqual(await self.book.finish(key,3),original_entry['exit'])
        self.assertEqual(fired[0].read_bytes(),residue)
        self.assertEqual((self.root/'capture/original-1.json').read_bytes(),evidence)
        self.assertFalse((self.root/'capture/original-2.json').exists())
        row=json.loads(evidence)
        self.assertTrue(row['evidence']['stdout_eof']); self.assertTrue(row['evidence']['stderr_eof'])
        self.assertTrue(row['evidence']['errors']); self.assertFalse(self.book.owned)
        self.assertEqual({row['original'] for row in deliveries},{key})
        self.assertEqual({row['stage'] for row in self.published[-1]['failures']},{'evidence','delivery'})

    async def test_malformed_stream_cannot_qualify_even_with_favorable_and_adverse_exact_commands(self):
        rows=self.rows(dict(type=17))
        rows[2:2]=[json.loads(event(result={'write':'succeeded'})),json.loads(event())]
        code, receipt, _=await self.stream(rows)
        self.rejected(code,receipt)
        raw=(self.root/'capture/stdout.jsonl').read_text()
        self.assertIn('succeeded',raw)
        with self.assertRaises(cr.Refusal): cr.acting_proof(raw,'exact canary')
