"""Q4 observed file-root/partial-delivery/category failures, fresh owned fixtures."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_writer_custody as fixtures
from support import event,queued,ident,result
from coordinator_runtime.appserver import AppServer,sandbox_policy
from coordinator_runtime.contracts import Refusal,task_result
from coordinator_runtime.dispatcher import execution_spec
from coordinator_runtime.cleanup import sweep
from coordinator_runtime import publication


class PartialBoundary(unittest.IsolatedAsyncioTestCase):
    include_root=True
    asyncSetUp=fixtures.WriterCustody.asyncSetUp
    run_writer=fixtures.WriterCustody.run_writer
    settle_routine=fixtures.WriterCustody.settle_routine

    async def test_directory_staging_publishes_exact_file_then_executes_next_independent_batch(self):
        self.target.chmod(0o640)
        probe=Path(self.temp.name)/'producer-observation.json'
        job,attempt=await self.run_writer(plan_extra={'probe_record':str(probe)})
        seen=json.loads(probe.read_text())
        self.assertEqual(seen['canonical_before_publication']['total'],0)
        self.assertNotEqual(seen['actual_write_path'],str(self.target))
        self.assertEqual(json.loads(self.target.read_text())['total'],12)
        self.assertEqual(self.target.stat().st_mode&0o777,0o640)
        self.assertEqual(self.store.one('SELECT state FROM file_publications')['state'],'published')
        spec=execution_spec(self.config['tasks']['work-integrator'],self.store.home/'artifacts'/attempt)
        self.assertEqual(sandbox_policy(spec)['writableRoots'],[str(self.store.home/'artifacts'/attempt)])
        self.assertNotIn(str(self.target),spec['effect_authority']['write_roots'])
        await self.settle_routine(job)
        next_job,next_attempt=await self.run_writer(plan_extra={'target_contents':{'total':51}})
        self.assertNotEqual(attempt,next_attempt)
        self.assertNotEqual(job['members'],next_job['members'])
        self.assertEqual(json.loads(self.target.read_text())['total'],51)
        await self.settle_routine(next_job)
        self.assertEqual(self.store.job(next_job['id'])['state'],'closed')

    def partial(self,category='blocked'):
        return {'semantic':'PARTIAL','category':category,'failures':['supplied sandbox command failure'],
            'unknowns':['canonical effects and required report not verified'],
            'handoffs':[{'recipient':'Root','kind':'result','text':'Calculated51; execution and required report remain incomplete.',
                         'ref':str(self.target),'required':'settled'}], 'no_handoff_reason':None}

    async def test_missing_report_partial_and_external_duty_route_without_successful_inventory(self):
        missing=str(Path(self.temp.name)/'missing-report.txt')
        job,attempt=await self.run_writer(artifacts=[missing,str(self.target)],answer_extra=self.partial())
        self.assertEqual(json.loads(self.target.read_text())['total'],0)  # No publication for PARTIAL.
        row=self.store.attempt(attempt)
        self.assertEqual(row['capture'],'artifact-inventory-incomplete')
        self.assertEqual(json.loads(row['detail'])['protocol_capture'],'complete')
        self.assertEqual(json.loads(row['result'])['category'],'blocked')
        self.assertEqual(json.loads(row['detail'])['contract_normalization']['projection'],'blocker')
        held=self.store.job(job['id'])
        self.assertEqual(held['effects'],'unknown');self.assertEqual(held['state'],'held')
        self.assertIsNotNone(held['response'])
        self.assertTrue(self.store.rows('SELECT * FROM artifact_custody WHERE attempt=?',(attempt,)))
        root=self.store.one("SELECT * FROM outboxes WHERE job=? AND recipient='Root'",(job['id'],))
        self.assertEqual(root['kind'],'question')
        self.assertEqual(root['state'],'classification-pending')
        self.assertIn('INCOMPLETE',json.loads(root['payload'])['text'])
        # One fresh fake-provider classifier routes the fixed informative plan.
        claimed=self.store.claim_classification();self.assertIsNotNone(claimed)
        classifier,source=claimed
        self.assertEqual(source['id'],held['response'])
        plan=Path(self.temp.name)/'response-classifier.json'
        plan.write_text(json.dumps({'result':{'event_id':source['id'],'task':'@delivery','package':None,'reason':'Partial failure needs actual recipient coordination'},'storage_config':{'history':{'persistence':'none'},'feedback':{'enabled':False},'features':{'shell_snapshot':False}}}))
        import sys
        self.runtime.models=AppServer(self.config,[sys.executable,str(Path(__file__).with_name('fixture_appserver.py')),str(plan)])
        await self.runtime.classify(classifier,source)
        self.runtime.receipts();self.runtime.pump_deliveries()
        posted=self.store.one('SELECT * FROM outboxes WHERE id=?',(root['id'],))
        self.assertEqual(posted['state'],'posted')  # Genuine synthetic service post, never recipient settlement.
        self.assertIsNone(posted['processed_at'])
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertTrue(all(e['processed_at'] is None for e in self.store.rows('SELECT processed_at FROM events')))
        # Independent incoming classification is admitted despite the held integration slot.
        incoming=event(self.config,'independent-arrival');self.store.ingest(incoming)
        claimed=self.store.claim_classification();self.assertEqual(claimed[1]['id'],incoming['id'])
        with patch.object(self.store,'clock',return_value=self.store.clock()+172800):sweep(self.store)
        self.assertTrue(Path(publication.stages(self.store,attempt)[str(self.target)]).exists())
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    async def test_malformed_category_retains_original_and_necessary_causal_delivery(self):
        job,attempt=await self.run_writer(answer_extra=self.partial('unsupported-category'))
        row=self.store.attempt(attempt)
        self.assertEqual(json.loads(row['result'])['category'],'unsupported-category')
        response=self.store.event(self.store.job(job['id'])['response'])
        self.assertTrue(response['body']['contract_errors'])
        self.assertEqual(self.store.one("SELECT kind FROM outboxes WHERE recipient='Root'")['kind'],'question')
        self.assertEqual(json.loads(self.target.read_text())['total'],0)

    async def test_nonstring_category_is_causal_failure_not_uncaught_exception(self):
        job,attempt=await self.run_writer(answer_extra=self.partial(['invalid-category']))
        self.assertEqual(json.loads(self.store.attempt(attempt)['result'])['category'],['invalid-category'])
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertIsNotNone(self.store.job(job['id'])['response'])
        self.assertEqual(self.store.one("SELECT kind FROM outboxes WHERE recipient='Root'")['kind'],'question')
        self.assertEqual(json.loads(self.target.read_text())['total'],0)

    async def test_missing_report_even_with_DONE_does_not_publish_or_deliver_completed_work(self):
        job,attempt=await self.run_writer(artifacts=[str(Path(self.temp.name)/'absent')],answer_extra={**self.partial(),'semantic':'DONE','category':'complete','failures':[],'unknowns':[]})
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        root=self.store.one("SELECT * FROM outboxes WHERE recipient='Root'")
        self.assertEqual(root['kind'],'question')
        self.assertEqual(json.loads(root['payload'])['source_result']['semantic'],'DONE')
        self.assertIn('incomplete',json.loads(root['payload'])['informative_failure']['disposition'])

    async def test_concurrent_canonical_change_is_not_overwritten(self):
        original=AppServer.run
        async def changed(adapter,*args,**kwargs):
            answer=await original(adapter,*args,**kwargs)
            self.target.write_text('{"total":999}')
            return answer
        with patch.object(AppServer,'run',changed):job,attempt=await self.run_writer()
        self.assertEqual(json.loads(self.target.read_text())['total'],999)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertIsNotNone(self.store.job(job['id'])['response'])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    async def test_revocation_after_collected_writer_still_fences_publication(self):
        original=AppServer.run
        async def revoked(adapter,*args,**kwargs):
            answer=await original(adapter,*args,**kwargs)
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):self.board.revoke(self.store.enrollment('Work')['grant_id'])
            return answer
        with patch.object(AppServer,'run',revoked):job,attempt=await self.run_writer()
        self.assertEqual(self.store.attempt(attempt)['exit'],0)
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    async def test_source_hold_added_during_writer_fences_publication(self):
        original=AppServer.run
        async def held(adapter,*args,**kwargs):
            answer=await original(adapter,*args,**kwargs)
            source=self.store.one('SELECT event FROM queue WHERE job=?',(self.store.attempt(args[1])['job'],))['event']
            self.store.set_hold(source,'real source/resource owner still needs recovery')
            return answer
        with patch.object(AppServer,'run',held):job,attempt=await self.run_writer()
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    async def test_publication_crash_retains_exact_intent_and_untouched_original(self):
        with patch('coordinator_runtime.publication.write_same_inode',side_effect=OSError('synthetic publication interruption')):
            job,attempt=await self.run_writer()
        row=self.store.one('SELECT * FROM file_publications')
        self.assertEqual(row['state'],'intent');self.assertIn('interruption',row['error'])
        self.assertTrue(Path(self.store.one('SELECT path FROM canonical_backups')['path']).is_file())
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertGreater(self.store.usage()['publication_reserved_bytes'],0)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        with self.assertRaisesRegex(Refusal,'publication intent'):
            self.store.reconcile_effects(job['id'],job['token'],self.owner,{'evidence':['generic effect receipt'],'unknown_effects':[]})
        self.runtime.try_finish(job['id'])
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        with patch.object(self.store,'clock',return_value=self.store.clock()+172800):sweep(self.store)
        self.assertTrue(Path(self.store.one('SELECT path FROM canonical_backups')['path']).is_file())  # Never canonical-parent purge.

    def test_category_alias_is_explicit_only_for_non_DONE_and_prompts_name_contract(self):
        raw={**result('PARTIAL','blocker'),'category':'blocked'}
        self.assertEqual(task_result(raw)['category'],'blocker');self.assertEqual(raw['category'],'blocked')
        with self.assertRaises(Refusal):task_result({**result(),'category':'blocked'})


class MultiFilePublication(unittest.IsolatedAsyncioTestCase):
    include_root=True
    include_second_target=True
    asyncSetUp=fixtures.WriterCustody.asyncSetUp
    run_writer=fixtures.WriterCustody.run_writer

    async def test_second_file_interruption_preserves_first_effect_and_both_source_holds(self):
        original=publication.write_same_inode
        def interrupted(fd,body):
            if os.fstat(fd).st_ino==self.second_target.stat().st_ino:raise OSError('synthetic second-file interruption')
            return original(fd,body)
        with patch('coordinator_runtime.publication.write_same_inode',interrupted):
            job,attempt=await self.run_writer(plan_extra={'additional_target':str(self.second_target),'additional_contents':{'total':78}})
        self.assertEqual(json.loads(self.target.read_text())['total'],12)
        self.assertEqual(json.loads(self.second_target.read_text())['total'],0)
        rows={r['target']:r for r in self.store.rows('SELECT * FROM file_publications')}
        self.assertEqual(rows[str(self.target)]['state'],'published')
        self.assertEqual(rows[str(self.second_target)]['state'],'intent')
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertIsNotNone(self.store.job(job['id'])['response'])
        source=json.loads(job['members'])[0]['event']
        with patch.object(self.store,'clock',return_value=self.store.clock()+172800):sweep(self.store)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source,))['processed_at'])
        self.assertTrue(Path(self.store.one('SELECT path FROM canonical_backups WHERE target=?',(str(self.second_target),))['path']).is_file())
