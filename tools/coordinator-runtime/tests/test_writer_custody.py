"""L01-L05: collected qualification2 failures, fresh owned synthetic evidence."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, queued, event, result
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import Dispatcher, RESULT_SCHEMA
from coordinator_runtime.cleanup import sweep
from coordinator_runtime import custody


class WriterCustody(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='correction3-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.config=config_at(self.temp.name)
        self.config['session_storage']={'mode':'producer-owned'}
        self.target=Path(self.temp.name)/'canonical.json'
        self.target.write_text('{"total":0}')
        task=self.config['tasks']['work-integrator']
        task.update(effects='owner-reconcile',sandbox='workspace-write',network=False,
                    routine_completion={'kind':'file-witness','targets':[str(self.target)]},delivery_required=True,allowed_handoffs=[])
        task['effect_authority'].update(write_roots=[str(self.target)],operations=['read-reports','write-role-records'])
        if getattr(self,'include_second_target',False):
            self.second_target=Path(self.temp.name)/'canonical-second.json';self.second_target.write_text('{"total":0}')
            task['routine_completion']['targets'].append(str(self.second_target))
            task['effect_authority']['write_roots'].append(str(self.second_target))
        self.owner=self.config['roles']['Work']['owner']
        self.sender=ident()
        self.config['delivery']={'recipients':{'Work':{'session':self.owner,'profile':'.codex','board_role':'work'}},'alert_role':'Work','alert_recipient':'Work'}
        if getattr(self,'include_root',False):
            self.root=ident()
            self.config['delivery']['recipients']['Root']={'session':self.root,'profile':'.codex2','board_role':'execution-manager'}
            task['allowed_handoffs']=['Root']
        from coordinator_runtime.store import Store
        self.store=Store(self.config)
        self.addCleanup(self.store.close)
        self.substrate=module_at(self.config['board_library'],'board_store')
        catalog=module_at(self.config['board_library'],'catalog')
        home=Path(self.config['board_home'])
        with catalog.catalog(home) as cat:
            entry=catalog.create(cat,home,'custody','Owned L01-L05 test',board_id=self.config['roles']['Work']['board_id'],temporary_test=True)
        self.path=Path(entry['db_path'])
        with self.substrate.database(str(self.path)) as conn:
            self.substrate.bind_board(conn,entry['board_id'],initialize=True)
            actors=[(self.owner,'work','.codex'),(self.sender,'sender','.codex')]
            if getattr(self,'include_root',False):actors.append((self.root,'execution-manager','.codex2'))
            for actor,role,profile in actors:
                args=self.substrate.parser().parse_args(['register','--session',actor,'--role',role,'--profile',profile,'--route','managed'])
                with patch.dict(os.environ,{'CODEX_SESSION_ID':actor}):self.substrate.register(conn,args)
        self.board=Board(self.config,'Work')
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):
            grant=self.board.grant(self.store,'Synthetic genuine-owner routine delegation',delivery=True,completion=True)
        self.store.enroll('Work',grant)
        self.store.reconcile_legacy('Work',self.owner,{'collector':self.owner,'evidence':['synthetic closed original'],'remaining_holds':[]})
        self.runtime=Dispatcher(self.store,models=object(),boards={'Work':self.board})

    async def run_writer(self, artifacts=None, tool=None, storage_bad=False, answer_extra=None, plan_extra=None):
        queued(self.store,event(self.config,ident()))
        job=self.store.reserve()
        attempt=self.store.start_job(job['id'],job['token'])
        config={'history':{'persistence':'none'},'feedback':{'enabled':False},'features':{'shell_snapshot':False}}
        if storage_bad:config['history']['persistence']='save-all'
        answer={**result(),'artifacts':artifacts if artifacts is not None else [str(self.target)],
                'handoffs':[],'no_handoff_reason':'Internal owned role result consumed by delegated collector; no external handoff.'}
        plan={'result':answer,'target':str(self.target),'target_contents':{'total':12},
              'tool_metadata':{'exitCode':0} if tool is None else tool,'storage_config':config,'completion_mode':'auto'}
        if artifacts == 'runtime':
            plan.update(write_file='report.txt',artifact_strings=True)
        if answer_extra:plan['result'].update(answer_extra)
        if plan_extra:plan.update(plan_extra)
        plan_path=Path(self.temp.name)/(attempt+'.json');plan_path.write_text(encode(plan))
        self.runtime.models=AppServer(self.config,[sys.executable,str(Path(__file__).with_name('fixture_appserver.py')),str(plan_path)])
        await self.runtime.execute(job['id'],attempt)
        return job,attempt

    async def settle_routine(self, job):
        current=self.store.job(job['id'])
        queued(self.store,self.store.event(current['response']))  # Fresh synthetic classifier result, no manual role effect approval.
        self.runtime.receipts();self.runtime.pump_deliveries();self.runtime.reconcile_completed()

    async def test_L01_normal_writer_drains_with_actual_service_grant_and_file_evidence(self):
        job,attempt=await self.run_writer()
        current=self.store.job(job['id'])
        self.assertEqual(current['effects'],'reconciled')
        proof=json.loads(current['effect_receipt'])
        self.assertEqual(proof['actor'],self.config['actor'])
        self.assertEqual(proof['delegated_by'],self.owner)
        self.assertEqual(proof['worker'],self.store.attempt(attempt)['session'])
        self.assertNotEqual(proof['before'][str(self.target)]['sha256'],proof['after'][str(self.target)]['sha256'])
        await self.settle_routine(job)
        self.assertEqual(self.store.job(job['id'])['state'],'closed')
        receipt=json.loads(self.store.one('SELECT board_receipt FROM outboxes')['board_receipt'])
        self.assertEqual(receipt['settlement']['actor'],self.config['actor'])
        self.assertEqual(receipt['settlement']['delegated_by'],self.owner)
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        queued(self.store,event(self.config,'next-independent'))
        self.assertIsNotNone(self.store.reserve())

    async def test_L01_unknown_command_completion_preserves_real_effect_hold(self):
        job,attempt=await self.run_writer(tool={'exitCode':None})
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        await self.settle_routine(job)
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='effect-request' AND state!='settled'"))
        self.assertFalse(json.loads(self.store.attempt(attempt)['detail'])['tool_completion']['complete'])

    async def test_L01_revocation_does_not_become_a_fabricated_routine_owner_receipt(self):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):self.board.revoke(self.store.enrollment('Work')['grant_id'])
        job,attempt=await self.run_writer()
        self.assertNotEqual(self.store.job(job['id'])['effects'],'reconciled')
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertIsNone(self.store.attempt(attempt)['ended'])  # No task process was created; no fake END.

    async def test_L02_role_strings_and_structured_artifacts_have_custody_never_delete_canonical(self):
        job,attempt=await self.run_writer(artifacts=[str(self.target),{'path':str(self.target),'meaning':'same canonical target'}])
        row=self.store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?',(attempt,str(self.target)))
        self.assertEqual(row['kind'],'role-owned')
        self.assertEqual(self.store.rows('SELECT * FROM artifacts WHERE path=?',(str(self.target),)),[])
        # The returned canonical reference is an input snapshot. Publication
        # conserves the distinct postimage at the mapped stage and in receipts.
        self.assertEqual(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(row['sha256'],))['body'],b'{"total":0}')
        from coordinator_runtime.publication import stages
        stage=stages(self.store,attempt)[str(self.target)]
        held=self.store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt,stage))
        self.assertEqual(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(held['sha256'],))['body'],self.target.read_bytes())
        await self.settle_routine(job)
        with patch.object(self.store,'clock',return_value=self.store.clock()+86401):sweep(self.store)
        self.assertTrue(self.target.is_file())
        self.assertIsNotNone(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(row['sha256'],)))

    async def test_L02_outside_root_artifact_is_held_instead_of_silently_skipped(self):
        job,attempt=await self.run_writer(artifacts=['/unselected/foreign-report'])
        self.assertEqual(self.store.attempt(attempt)['capture'],'artifact-inventory-incomplete')
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertIn('/unselected/foreign-report',self.store.attempt(attempt)['result'])
        self.assertEqual(self.store.rows('SELECT * FROM artifact_custody WHERE path=?',('/unselected/foreign-report',)),[])
        self.assertTrue(self.store.rows('SELECT * FROM artifact_custody'))  # Exact staged recovery meaning survives the bad declaration.

    async def test_L02_runtime_string_report_is_conserved_before_exact_file_retirement(self):
        job,attempt=await self.run_writer(artifacts='runtime')
        report=self.store.home/'artifacts'/attempt/'report.txt'
        body=report.read_bytes()
        row=self.store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?',(attempt,str(report)))
        self.assertEqual(row['kind'],'runtime-owned')
        await self.settle_routine(job)
        response=self.store.job(job['id'])['response']
        self.store.set_hold(response,'later consumer needs exact report')
        future=self.store.clock()+86401
        with patch.object(self.store,'clock',return_value=future):sweep(self.store)
        self.assertTrue(report.exists())
        with patch.object(self.store,'clock',return_value=future):self.store.set_hold(response,None)
        with patch.object(self.store,'clock',return_value=future+86400):sweep(self.store)
        self.assertFalse(report.exists())
        self.assertEqual(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(row['sha256'],))['body'],body)

    async def test_Q3_producer_outputs_later_hold_and_processed_plus_24h(self):
        job,attempt=await self.run_writer(artifacts='runtime')
        path=self.store.home/'artifacts'/attempt/'report.txt'
        self.assertEqual(self.store.rows('SELECT * FROM attempt_storage'),[])
        self.assertFalse((self.store.home/'sessions').exists())
        detail=json.loads(self.store.attempt(attempt)['detail'])
        self.assertEqual(detail['session_residuals']['state'],'unqualified-held')
        self.assertFalse(detail['session_residuals']['automatic_store_deletion'])
        await self.settle_routine(job)
        source=json.loads(job['members'])[0]['event']
        processed=self.store.one('SELECT processed_at FROM events WHERE id=?',(source,))['processed_at']
        self.store.set_hold(source,'later recovery needs exact producer output')
        with patch.object(self.store,'clock',return_value=processed+172801):sweep(self.store)
        self.assertTrue(path.exists())
        release=processed+172801
        with patch.object(self.store,'clock',return_value=release):self.store.set_hold(source,None)
        with patch.object(self.store,'clock',return_value=release+86399):sweep(self.store)
        self.assertTrue(path.exists())
        with patch.object(self.store,'clock',return_value=release+86400):sweep(self.store)
        self.assertFalse(path.exists())
        self.assertTrue(self.target.exists())

    async def test_L04_settings_mismatch_refuses_before_any_model_turn(self):
        job,attempt=await self.run_writer(storage_bad=True)
        self.assertEqual(json.loads(self.target.read_text())['total'],0)
        self.assertIn('producer setting',self.store.attempt(attempt)['error'])
        self.assertIsNone(self.store.attempt(attempt)['turn'])
        self.assertEqual(self.store.attempt(attempt)['exit'],0)  # Actual fake control process, no task turn.
        self.assertEqual(self.store.attempt(attempt)['cleanup'],'no-session-created')

    async def test_L04_capacity_guard_stops_only_its_owned_fixture_process(self):
        from coordinator_runtime.storage import guard
        from coordinator_runtime.store import Store
        folder=Path(self.temp.name)/'bounded-guard';folder.mkdir()
        config=config_at(folder);config['limits']['max_bytes']=1
        bounded=Store(config)
        self.addCleanup(bounded.close)
        child=await asyncio.create_subprocess_exec(sys.executable,'-c','import time; time.sleep(10)')
        outcome={'error':None,'detail':{}}
        await guard(bounded,child,outcome)
        code=await child.wait()
        self.assertIsInstance(code,int)
        self.assertNotEqual(code,0)
        self.assertIn('capacity',outcome['detail']['storage_capacity_hold'])

    async def test_L02_frozen_declared_source_survives_later_canonical_change(self):
        job,attempt=await self.run_writer()
        witness=custody.witnesses(self.store,attempt)[0]
        original=self.target.read_bytes()
        self.target.write_text('{"total":999}')  # New synthetic canonical version, old meaning still needed.
        await self.settle_routine(job)
        queued(self.store,event(self.config,'consumer'))
        consumer=self.store.reserve()
        later=self.store.start_job(consumer['id'],consumer['token'])
        (self.store.home/'artifacts'/later).mkdir(parents=True)
        files=custody.materialize(self.store,[{'artifact_witnesses':[witness]}],later)
        self.assertEqual(Path(files[0]['frozen_path']).read_bytes(),original)
        self.assertNotEqual(Path(files[0]['frozen_path']).read_bytes(),self.target.read_bytes())

    async def test_Q3_legacy_namespace_is_not_inspected_or_deleted_at_any_age(self):
        job,attempt=await self.run_writer(artifacts='runtime')
        await self.settle_routine(job)
        root=self.store.home/'sessions'/attempt
        root.mkdir(parents=True)
        (root/'mixed-placeholder').write_text('synthetic foreign logical content; never inspected')
        link=root/'foreign-link';link.symlink_to(self.target)
        info=root.stat()
        with self.store.tx():
            self.store.db.execute('INSERT INTO attempt_storage VALUES(?,?,?,?,?,?,NULL,NULL)',
                (attempt,str(root),info.st_dev,info.st_ino,'{}','effective-paths-verified'))
        def forbidden(*args,**kwargs):raise AssertionError('legacy namespace touched')
        # Strong boundary: no storage filesystem operation is needed at all.
        with patch('coordinator_runtime.storage.os',create=True) as fs:
            fs.stat=fs.scandir=fs.listdir=fs.open=fs.unlink=forbidden
            with patch.object(self.store,'clock',return_value=self.store.clock()+86401):sweep(self.store)
        self.assertEqual(self.store.one('SELECT state FROM attempt_storage')['state'],'opaque-ownership-held')
        self.assertTrue(root.exists())
        self.assertTrue(link.is_symlink())
        self.assertTrue(self.target.is_file())
        self.assertEqual(self.store.job(job['id'])['state'],'closed')
        self.assertEqual(self.store.one('SELECT state FROM events WHERE id=?',(json.loads(job['members'])[0]['event'],))['state'],'retired')

    async def test_L05_supported_command_metadata_omits_raw_bodies_and_OS_ownership(self):
        job,attempt=await self.run_writer()
        detail=json.loads(self.store.attempt(attempt)['detail'])
        item=detail['tool_completion']['items'][0]
        self.assertEqual(item['exit_code'],0)
        self.assertEqual(item['provider_process_id'],'provider-label-only')
        self.assertFalse(item['OS_handle_owned'])
        self.assertNotIn('private command body',encode(detail))
        self.assertNotIn('private output',encode(detail))

    async def test_L05_known_settled_nonzero_probe_is_conserved_without_inventing_live_uncertainty(self):
        job,attempt=await self.run_writer(tool={'exitCode':1,'status':'failed'})
        detail=json.loads(self.store.attempt(attempt)['detail'])
        self.assertEqual(detail['tool_completion']['items'][0]['exit_code'],1)
        self.assertTrue(detail['tool_completion']['nonzero_completions'])
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')  # Settled process is known, but its local resolution is not attested.

    async def test_L03_actual_paused_interval_source_without_notice_is_owner_bound(self):
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):self.board.revoke(self.store.enrollment('Work')['grant_id'])
        with self.substrate.database(str(self.path)) as conn:
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):
                args=self.substrate.parser().parse_args(['heartbeat','--session',self.owner,'--status','paused'])
                self.substrate.heartbeat(conn,args)
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.sender}):
                args=self.substrate.parser().parse_args(['open','--session',self.sender,'--topic','test','--kind','finding',
                    '--text','Unique paused interval finding','--to',self.owner,'--title','During pause','--no-push'])
                with patch.object(sys,'path',[self.config['board_library'],*sys.path]):
                    post=self.substrate.open_thread(conn,args)
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):
                args=self.substrate.parser().parse_args(['register','--session',self.owner,'--role','work','--profile','.codex','--route','queue','--status','active'])
                self.substrate.register(conn,args)
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.sender}):
            self.assertRaises(Exception,self.board.owner_catchup,self.store,0,post)
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):
            recovered=self.board.owner_catchup(self.store,0,post)
        self.assertEqual(recovered['sources'][0]['post']['text'],'Unique paused interval finding')
        self.assertIsNone(recovered['sources'][0]['notice'])
        self.assertFalse(recovered['membership_or_cursor_changed'])
