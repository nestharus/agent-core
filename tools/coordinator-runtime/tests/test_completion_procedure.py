"""Q5-01/Q5-02: current obligation protocol and actual canonical file discipline."""
import asyncio
import gzip
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_writer_custody as fixtures
from coordinator_runtime import publication
from coordinator_runtime.board import module_at
from coordinator_runtime.contracts import Refusal
from coordinator_runtime.cleanup import sweep
from coordinator_runtime import custody


class CompletionProcedure(unittest.IsolatedAsyncioTestCase):
    include_root=True
    asyncSetUp=fixtures.WriterCustody.asyncSetUp
    run_writer=fixtures.WriterCustody.run_writer
    settle_routine=fixtures.WriterCustody.settle_routine

    async def test_expected_controller_duty_is_owned_without_erasing_unknown_history(self):
        original='Controller publication, byte custody and acceptance remain unestablished by this local staged result.'
        job,attempt=await self.run_writer(answer_extra={'unknowns':[original]},plan_extra={'completion_mode':'legacy-deferred'})
        row=self.store.attempt(attempt);answer=json.loads(row['result']);detail=json.loads(row['detail'])
        self.assertTrue(detail['readiness_clarification'])
        self.assertEqual(answer['unknowns'],[original]);self.assertEqual(detail['prior_turn_result']['unknowns'],[original])
        receipt=json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(receipt['local_readiness']['subsequent_duties'][0]['actual_owner'],self.config['actor'])
        self.assertEqual(json.loads(self.target.read_text())['total'],12)
        await self.settle_routine(job)
        self.assertEqual(self.store.job(job['id'])['state'],'closed')
        next_job,next_attempt=await self.run_writer()
        self.assertNotEqual(attempt,next_attempt)
        self.assertEqual(self.store.job(next_job['id'])['effects'],'reconciled')

    async def test_resolved_failure_claim_requires_linked_report_and_actual_verification(self):
        history='Resolved verifier/report mismatch; retained original failed assertion and repair history.'
        job,attempt=await self.run_writer(answer_extra={'failures':[history]},tool={'exitCode':1,'status':'failed'},plan_extra={'completion_mode':'legacy-resolved'})
        row=self.store.attempt(attempt);detail=json.loads(row['detail'])
        self.assertEqual(json.loads(row['result'])['failures'],[history])
        self.assertEqual(detail['prior_turn_result']['failures'],[history])
        self.assertTrue(detail['tool_completion']['nonzero_completions'])
        self.assertIn(1,[r['exit_code'] for r in detail['tool_completion']['items']])
        proof=json.loads(self.store.job(job['id'])['effect_receipt'])['local_readiness']
        self.assertEqual(proof['original_failures'],[history]);self.assertEqual(proof['resolved_history'][0]['index'],0)
        self.assertIn('producer-attested',proof['qualification'])
        await self.settle_routine(job)
        self.assertEqual(self.store.job(job['id'])['state'],'closed')

    async def test_any_later_zero_does_not_resolve_an_unlinked_failure(self):
        job,attempt=await self.run_writer(answer_extra={'failures':['Verifier failed, resolution claim requires evidence']},
            tool={'exitCode':1,'status':'failed'},plan_extra={'completion_mode':'legacy-resolved','bad_verification_item':True})
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        self.assertTrue(json.loads(self.store.attempt(attempt)['detail'])['tool_completion']['nonzero_completions'])

    async def test_false_report_hash_cannot_waive_original_failure(self):
        job,attempt=await self.run_writer(answer_extra={'failures':['Report check failed']},tool={'exitCode':1,'status':'failed'},
            plan_extra={'completion_mode':'legacy-resolved','bad_resolution_hash':True})
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertIsNotNone(self.store.job(job['id'])['response'])

    async def test_clarification_may_not_silently_erase_failure_history(self):
        original='Actual failed verifier remains part of source history.'
        job,attempt=await self.run_writer(answer_extra={'failures':[original]},tool={'exitCode':1,'status':'failed'},
            plan_extra={'completion_mode':'legacy-resolved','erase_history':True})
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(json.loads(self.store.attempt(attempt)['detail'])['prior_turn_result']['failures'],[original])
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    async def test_genuine_local_blocker_stays_held_despite_DONE(self):
        proof={'version':1,'local':'blocked','failures':[],
            'unknowns':[{'index':0,'status':'unresolved','owner':'producer','duty':'verification','reason':'Current staged invariant still fails.'}],'tools':[]}
        job,attempt=await self.run_writer(answer_extra={'unknowns':['Current local invariant unresolved'],'completion':proof},plan_extra={'completion_mode':'explicit'})
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='effect-request'"))

    async def test_canonical_inode_mode_owner_and_before_gzip_are_preserved(self):
        self.target.chmod(0o640);before=self.target.read_bytes();identity=self.target.stat()
        job,attempt=await self.run_writer()
        after=self.target.stat()
        self.assertEqual((after.st_dev,after.st_ino,after.st_mode,after.st_uid,after.st_gid),
                         (identity.st_dev,identity.st_ino,identity.st_mode,identity.st_uid,identity.st_gid))
        backup=self.store.one('SELECT * FROM canonical_backups')
        self.assertEqual(gzip.decompress(Path(backup['path']).read_bytes()),before)
        self.assertTrue(backup['path'].endswith('.before.gz'))
        self.assertEqual(self.store.one('SELECT temp FROM file_publications')['temp'],None)
        receipt=json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertIn('same-inode',receipt['publication'][0]['method'])
        await self.settle_routine(job)
        self.store.set_hold(self.store.job(job['id'])['response'],'later backup consumer')
        with patch.object(self.store,'clock',return_value=self.store.clock()+172800):sweep(self.store)
        self.assertTrue(Path(backup['path']).is_file())

    async def test_partial_same_inode_write_keeps_durable_original_and_unknown_effects(self):
        before=self.target.read_bytes();inode=self.target.stat().st_ino
        def interrupted(fd,body):
            os.write(fd,b'BROKEN');os.fsync(fd);raise OSError('actual synthetic partial write')
        with patch('coordinator_runtime.publication.write_same_inode',interrupted):job,attempt=await self.run_writer()
        self.assertEqual(self.target.stat().st_ino,inode)
        self.assertNotEqual(self.target.read_bytes(),before)
        backup=Path(self.store.one('SELECT path FROM canonical_backups')['path'])
        self.assertEqual(gzip.decompress(backup.read_bytes()),before)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.one('SELECT state FROM file_publications')['state'],'intent')
        broken=self.target.read_bytes();self.runtime.try_finish(job['id'])
        self.assertEqual(self.target.read_bytes(),broken)  # No blind replay/rollback.
        with patch.object(self.store,'clock',return_value=self.store.clock()+172800):sweep(self.store)
        self.assertTrue(backup.is_file())

    async def test_selected_snapshot_lock_contention_does_not_launch_another_writer(self):
        library=self.config['canonical_publication']['library']
        code="import importlib.util,sys; s=importlib.util.spec_from_file_location('fixture_retention',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);ctx=m.snapshot_lock();ctx.__enter__();print('LOCKED',flush=True);sys.stdin.readline();ctx.__exit__(None,None,None)"
        # Hold only during publication (initial preimage acquisition must also cooperate).
        from coordinator_runtime.appserver import AppServer
        original=AppServer.run;child=None
        async def locked(adapter,*args,**kwargs):
            nonlocal child
            value=await original(adapter,*args,**kwargs)
            child=await asyncio.create_subprocess_exec(sys.executable,'-c',code,str(Path(library)/'retention.py'),stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE)
            self.assertEqual(await asyncio.wait_for(child.stdout.readline(),10),b'LOCKED\n')
            return value
        try:
            with patch.object(AppServer,'run',locked):job,attempt=await self.run_writer()
            self.assertEqual(json.loads(self.target.read_text())['total'],0)
            self.assertIsNotNone(self.store.attempt(attempt)['collected'])
            self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        finally:
            if child:
                child.stdin.close();self.assertEqual(await asyncio.wait_for(child.wait(),10),0)
        self.runtime.reconcile_completed()
        self.assertEqual(json.loads(self.target.read_text())['total'],12)
        self.assertEqual([r['id'] for r in self.store.rows('SELECT id FROM attempts WHERE job=?',(job['id'],))],[attempt])

    def test_opaque_exclusion_precedes_even_path_metadata(self):
        path=str(Path(self.temp.name)/'opaque-source')
        self.config['artifact_exclusions']=[path]
        with patch('coordinator_runtime.custody.safe_path',side_effect=AssertionError('metadata reached')):
            with self.assertRaisesRegex(Refusal,'before metadata'):
                custody.capture(self.store,'unneeded-attempt',path+'/anything',self.config['tasks']['work-integrator'])
