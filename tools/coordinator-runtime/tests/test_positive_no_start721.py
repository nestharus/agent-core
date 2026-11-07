"""Positive no-start retirement in owned catalog-shaped software fiction.

Only fictional Board journals and owned targets are used. Dispatcher execute,
collect, try_finish and failure_delivery are real; no provider/process is run.
"""
import asyncio
import copy
import json
import os
from contextlib import contextmanager, ExitStack
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import test_management406 as fixture
from support import config_at, event
from coordinator_runtime import cli, integration_management as management, local_integration, publication, routine, selected_source
from coordinator_runtime.contracts import Refusal, digest, encode, ident, validate_config
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.integration import METADATA_NO_START
from coordinator_runtime.store import Store


class PositiveNoStart721(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        def configured(home):
            config = config_at(home)
            # All paths/principals are substituted BEFORE validation/metadata.
            raw = Path(__file__).with_name('no_start_catalog721.json').read_text()
            shape = json.loads(raw.replace('$FIXTURE', str(home)).replace(
                '$WORK_OWNER', config['roles']['Work']['owner']))
            self.shape = shape
            task = shape['work_integrator']
            config['tasks']['work-integrator'] = task
            config['local_integration'] = dict(max_inflight=8,
                tasks={'work-integrator':shape['local_policy']}, points=shape['points'])
            config['delivery'] = {'recipients': {r:dict(session=v['owner'],profile=v['profile'],board_role=v['board_role'])
                for r,v in config['roles'].items()}}
            config['delivery']['recipients']['Root'] = dict(session=ident(),profile='.codex3',board_role='root')
            for name in task['templates']:
                path = Path(name); path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('Fictional bounded catalog method. Preserve all duties.\n')
            Path(task['cwd']).mkdir(parents=True,exist_ok=True)
            # Only the seventh surface exists: actual routine.prepare refuses
            # before launch, then unpatched try_finish creates the response.
            log = Path(task['routine_completion']['bounded_log']['target'])
            log.parent.mkdir(parents=True,exist_ok=True); log.write_text('Fictional retained history\n')
            return validate_config(config)
        self.f = fixture.Management('runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.configure = lambda: self.f.config['delivery']['recipients'].update(
            Root=dict(session=ident(),profile='.codex3',board_role='root'))
        with patch.object(fixture, 'config_at', side_effect=configured): self.f.setUp()
        self._asyncioRunner.get_loop().set_debug(False)
        self.store, self.owner = self.f.store, self.f.owner
        self.store.controller = 'fictional-controller721'
        # Discard only the builder's authored seed rows, before this case's
        # real reservation. This is fixture construction, never retirement.
        for table in ('file_publications','artifact_custody','results','delivery_wakeups','outboxes','attempts','queue','jobs','events'):
            self.store.db.execute('DELETE FROM '+table)
        for board in self.f.boards.values():
            with sqlite3.connect(board.path) as conn:
                conn.execute('UPDATE coordinator_grants_v1 SET revoked=NULL')
        self.store.db.execute('UPDATE enrollments SET intake=1')
        self.store.reconcile_legacy('Work',self.owner,dict(collector='fictional original custodian',
            evidence=['fictional empty initial obligations'],remaining_holds=[]))
        self.message = event(self.f.config, 'fictional-positive-no-start721')
        points = self.shape['points']
        reads = list(points); writes = [k for k,p in points.items() if p['writable']]
        self.message['integration'] = dict(reads=reads,writes=writes,versions={k:'fictional-original-version' for k in reads})
        self.f.insert('events',dict(id=self.message['id'],role='Work',payload=encode(self.message),hash=digest(self.message),
            received=1.,state='queued',ack='internal'))
        self.f.insert('queue',dict(id='fictional-queue721',event=self.message['id'],role='Work',phase='integrator',task='work-integrator'))
        self.job = self.store.reserve()
        self.assertIsNotNone(self.job)
        self.job_id,self.token = self.job['id'],self.job['token']
        self.attempt = self.store.start_job(self.job_id,self.token)
        model = AsyncMock(); model.run.side_effect = AssertionError('model/provider must never start')
        self.runtime = Dispatcher(self.store,models=model,boards=self.f.boards)
        await self.runtime.execute(self.job_id,self.attempt)
        self.assertEqual(model.run.await_count,0)
        self.assertEqual(self.store.attempt(self.attempt)['state'],'not-started')
        self.assertIsNotNone(self.store.job(self.job_id)['response'])
        self.assertTrue(self.store.rows('SELECT id FROM outboxes WHERE job=?',(self.job_id,)))
        # Real recovery allocation and collection, with a fictional numeric
        # read-only child return seam. No diagnosis END is lent to the task.
        self.assertIsNotNone(self.store.claim_recovery(self.job_id))
        self.diagnosis = self.store.diagnosis_attempt(self.job_id)
        self.store.begin(self.diagnosis,{'fictional_readonly_return':True})
        self.store.collect(self.diagnosis,dict(exit=0,capture='complete',cleanup='owned-ephemeral-lifecycle-observed',
            result={'profile':'@owner','remaining':'retain original duties','rationale':'fictional no replay'},detail={}))
        self.store.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?",(self.job_id,))
        self.snapshot_files = {p:Path(p).read_bytes() for p in self.shape['work_integrator']['routine_completion']['targets'] if Path(p).exists()}
        self.authority = None

    def pause(self):
        for role,board in self.f.boards.items():
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):
                board.revoke_software(self.store,self.store.enrollment(role)['grant_id'])
        self.store.db.execute('UPDATE enrollments SET intake=0')
        self.authority = management.basis(self.store,['Work'],self.owner,
            'Fictional current Work closure choice','Execution retirement only; old source remains reserved',metadata_only=True)

    def call(self,command,receipt=None,selection=None,actor=None):
        args=[command,self.job_id,'--token',self.token]
        if self.authority is not None:
            choice=selection or dict(basis=self.authority,expires=1100.,operation=command,
                target=dict(job=self.job_id,token=self.token),records=dict(jobs=[self.job_id],events=[self.message['id']]))
            path=self.f.home/'selection721.json';path.write_text(encode(choice));args+=['--management',str(path)]
        if receipt is not None:
            path=self.f.home/'receipt721.json';path.write_text(encode(receipt));args+=['--receipt',str(path)]
        with patch.dict(os.environ,{'CODEX_SESSION_ID':actor or self.owner}):
            return cli.operate(cli.parser().parse_args(args),self.store)

    def basis(self):return self.call('integration-metadata-closure-basis')

    def receipt(self):
        basis=self.basis()
        return dict(basis=basis,reason='Fictional current Work retires only this positively unlaunched execution',
            controllers=[dict(controller=c,collector='fictional-actual-parent-collector',end=0,collected=True,
                writers_closed=True,no_task_launch=True,evidence=['Fictional scoped original/child/publisher/callback writers closed; task never launched'])
                for c in basis['controllers']])

    def retire(self,receipt=None):return self.call('retire-integration-metadata',receipt or self.receipt())

    def conserved(self):
        tables=['jobs','queue','attempts','results','events','outboxes','file_publications','routine_runs','routine_stages',
            'artifact_custody','artifact_blobs','local_jobs','local_bases','local_commits','local_point_commits',
            'local_material_commits','recovery_requests','recovery_dispositions','processing_capabilities','processing_runs',
            'service_windows','service_window_allocations','enrollments','job_resource_policies']
        return {t:self.store.rows('SELECT * FROM '+t+' ORDER BY rowid') for t in tables}

    @contextmanager
    def metadata_only(self):
        denied=[]
        forbidden={'results':None,'outboxes':None,'artifact_custody':None,'artifact_blobs':None,
            'jobs':{'response','hold_reason'}, 'attempts':{'result','error','binding','profile'},
            'events':{'payload','classification','error','ack_receipt'},
            'routine_runs':{'before_files'},'routine_stages':{'path'},
            'recovery_requests':{'receipt','result'},'recovery_dispositions':{'reason'}}
        # Null/equality tests on result/effect_receipt are permission-scoped SQL
        # predicates, never returned body acquisition. SQLite authorizers cannot
        # distinguish a projection from a predicate; deny all other body reads
        # and assert returned records contain none of these fictional sentinels.
        forbidden['attempts'].remove('result')
        def authorize(action,table,column,db,caller):
            if action==sqlite3.SQLITE_READ and table in forbidden and (forbidden[table] is None or column in forbidden[table]):
                denied.append((table,column));return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        with ExitStack() as stack:
            for name in ('job','attempt','event','source_roles','integration_debt','usage','budget'):
                stack.enter_context(patch.object(self.store,name,side_effect=AssertionError('old body method: '+name)))
            stack.enter_context(patch('coordinator_runtime.custody.safe_path',side_effect=AssertionError('canonical metadata acquired')))
            stack.enter_context(patch('coordinator_runtime.custody.read_file',side_effect=AssertionError('canonical body acquired')))
            self.store.db.set_authorizer(authorize)
            try:yield
            finally:self.store.db.set_authorizer(None)
        self.assertEqual(denied,[])

    async def test_full_dispatcher_response_conservation_and_execution_only_retirement(self):
        before=self.conserved()
        with self.metadata_only():
            basis=self.basis();self.assertEqual(basis['schema'],METADATA_NO_START)
            fence=self.retire()
        self.assertEqual(before,self.conserved())
        self.assertEqual(fence['job'],self.job_id)
        self.assertTrue(self.store.execution_complete(self.store.job(self.job_id)))
        self.assertIsNone(self.store.attempt(self.attempt)['ended'])
        self.assertEqual(self.store.job(self.job_id)['state'],'held')
        self.assertEqual(self.store.one('SELECT state,job FROM queue WHERE id=?',('fictional-queue721',)),dict(state='reserved',job=self.job_id))
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.snapshot_files,{p:Path(p).read_bytes() for p in self.snapshot_files})
        self.store.complete_events()
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(self.message['id'],))['processed_at'])

    async def test_stopped_management_and_audit_rollback(self):
        self.pause();receipt=self.receipt();before=self.conserved()
        original=selected_source.custody_budget;calls=[]
        def fail_audit(runtime,incoming):
            calls.append(incoming)
            if len(calls)==2:raise Refusal('fictional audit capacity refusal')
            return original(runtime,incoming)
        with self.metadata_only(),patch.object(selected_source,'custody_budget',side_effect=fail_audit):
            with self.assertRaisesRegex(Refusal,'audit capacity'):self.retire(receipt)
        self.assertEqual(before,self.conserved());self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'),[])
        with self.metadata_only():self.retire(receipt)
        self.assertEqual(before,self.conserved());self.assertEqual(len(self.store.rows('SELECT id FROM integration_management_operations')),1)

    async def test_bad_proof_and_diagnosis_refuse_without_mutation(self):
        original=self.store.attempt(self.attempt)
        cases=[dict(begin=1),dict(ended=1),dict(exit=0),dict(session='fictional'),dict(turn='fictional'),
            dict(semantic='DONE'),dict(result='{}'),dict(capture='unknown'),dict(cleanup='pending'),dict(collected=None),
            dict(collected=-1),dict(state='unknown'),dict(kind='future'),dict(controller='foreign')]
        cases += [dict(detail=encode({'known_not_started':v,'resume_disposition':'fictional'})) for v in [False,1,'true',None]]
        cases += [dict(detail=encode({'known_not_started':True,'resume_disposition':v})) for v in ['', '   ',True,{},None]]
        for change in cases:
            with self.subTest(change=change):
                fields=list(change);sql='UPDATE attempts SET '+','.join(k+'=?' for k in fields)+' WHERE id=?'
                self.store.db.execute(sql,(*[change[k] for k in fields],self.attempt));before=self.conserved()
                try:
                    with self.metadata_only(),self.assertRaises(Refusal):self.basis()
                    self.assertEqual(before,self.conserved())
                finally:self.store.db.execute(sql,(*[original[k] for k in fields],self.attempt))
        for field,value in [('ended',None),('begin',1001),('exit',None),('collected',None),('cleanup','pending'),('state','unknown')]:
            old=self.store.attempt(self.diagnosis)[field]
            self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(value,self.diagnosis))
            try:
                with self.metadata_only(),self.assertRaises(Refusal):self.basis()
            finally:self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(old,self.diagnosis))

    async def test_stale_opaque_revision_and_bad_controller_receipts(self):
        receipt=self.receipt()
        for change in [lambda r:r['controllers'][0].pop('no_task_launch'),lambda r:r['controllers'][0].update(no_task_launch=False),
                lambda r:r['controllers'][0].update(end=None),lambda r:r['controllers'][0].update(end=True),
                lambda r:r['controllers'][0].update(writers_closed=False),lambda r:r.update(controllers=[]),
                lambda r:r['controllers'].append(copy.deepcopy(r['controllers'][0]))]:
            bad=copy.deepcopy(receipt);change(bad)
            with self.metadata_only(),self.assertRaises(Refusal):self.retire(bad)
        original=self.store.one('SELECT response FROM jobs WHERE id=?',(self.job_id,))['response']
        self.store.db.execute('UPDATE jobs SET response=? WHERE id=?',('OPAQUE-CHANGED-721',self.job_id))
        self.store.db.execute('UPDATE jobs SET response=? WHERE id=?',(original,self.job_id))
        with self.metadata_only(),self.assertRaisesRegex(Refusal,'basis changed'):self.retire(receipt)
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'),[])

    async def test_stale_callbacks_refuse_before_old_body_acquisition(self):
        job=self.store.job(self.job_id)
        class OpaqueAttempt(dict):
            def __getitem__(self,key):raise AssertionError('retained attempt field acquired after fence: '+key)
        attempt=OpaqueAttempt()
        self.retire();before=self.conserved()
        with self.metadata_only():
            for name,fn in [
                ('hold',lambda:self.store.hold_job(self.job_id,'late callback')),
                ('begin',lambda:self.store.begin(self.attempt,{})),
                ('session',lambda:self.store.session(self.attempt,'late')),
                ('semantic',lambda:self.store.observe_semantic(self.attempt,'DONE')),
                ('collection',lambda:self.store.collect(self.attempt,{})),
                ('capture',lambda:self.store.capture_gap(self.attempt,'late')),
                ('recheck',lambda:self.store.recheck_artifact_capture(self.attempt)),
                ('retry-hold',lambda:self.store.retry_disposition_hold(self.job_id)),
                ('invalid-diagnosis',lambda:self.store.finish_invalid_diagnosis(job)),
                ('launch',lambda:self.store.authorize_launch(self.attempt)),
                ('start',lambda:self.store.start_job(self.job_id,self.token)),
                ('finish-store',lambda:self.store.finish_job(self.job_id,self.token)),
                ('routine',lambda:routine.prepare(self.store,None,job,self.attempt,self.shape['work_integrator'])),
                ('publication',lambda:publication.publish(self.store,None,job,None,None,None)),
                ('inventory',lambda:self.runtime.inventory_artifacts(self.attempt,{})),
                ('failure',lambda:self.store.failure_delivery(job,attempt,self.shape['work_integrator'],'late')),
                ('gate',lambda:self.store.gate_result_delivery(job,attempt,{})),
                ('question',lambda:self.store.owner_question(job,attempt,'late')),
                ('report',lambda:self.store.owner_report(job,attempt,{})),
                ('handoffs',lambda:self.store.prepare_handoffs(job,attempt,self.shape['work_integrator'],{}))]:
                with self.subTest(callback=name),self.assertRaises(Refusal):fn()
            self.runtime.try_finish(self.job_id)
            await self.runtime.execute(self.job_id,self.attempt)
        self.assertEqual(before,self.conserved())


    @contextmanager
    def rollback_case(self):
        self.store.db.execute('SAVEPOINT fictional721')
        try:yield
        finally:
            self.store.db.execute('ROLLBACK TO fictional721')
            self.store.db.execute('RELEASE fictional721')

    async def test_scope_policy_source_actor_recovery_and_effect_refusals(self):
        job=self.store.job(self.job_id)
        scope=local_integration.scope_for(self.store,job)
        task=self.shape['work_integrator']
        mutations=[
            ("UPDATE jobs SET effects='unknown'",()),
            ("UPDATE jobs SET effect_receipt='OPAQUE721'",()),
            ("UPDATE jobs SET package='foreign-package'",()),
            ("UPDATE jobs SET active_attempt=?",(self.diagnosis,)),
            ("UPDATE jobs SET recovery_state='diagnosing'",()),
            ("UPDATE jobs SET recovery_count=0",()),
            ("UPDATE jobs SET controller='foreign'",()),
            ("UPDATE local_jobs SET policy='stale'",()),
            ("UPDATE local_jobs SET scope=?",(encode({**scope,'lane':'discovery'}),)),
            ("UPDATE local_jobs SET scope=?",(encode({**scope,'reads':['foreign-point']}),)),
            ("UPDATE local_jobs SET scope=?",(encode({**scope,'sources':['foreign-source']}),)),
            ("UPDATE queue SET state='queued'",()),
            ("UPDATE queue SET event=?",(job['response'],)),
            ("UPDATE events SET hash='changed' WHERE id=?",(self.message['id'],)),
            ("INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)",(self.attempt,self.job_id,'fictional','{}','{}','intent',None)),
            ("INSERT INTO ordinary_resources VALUES(?,?)",('fictional-resource721',self.attempt)),
            ("INSERT INTO local_commits VALUES(?,?,?)",(self.attempt,'intent','OPAQUE721')),
            ("INSERT INTO file_publications(attempt,target,state) VALUES(?,?,?)",(self.attempt,'fictional-intent721','intent')),
            ("INSERT INTO recovery_requests(id,job,attempt,actor,receipt,state,created) VALUES(?,?,?,?,?,?,?)",
                ('fictional-pending721',self.job_id,self.attempt,self.owner,'OPAQUE721','pending',1000.))]
        for sql,args in mutations:
            with self.subTest(sql=sql),self.rollback_case():
                self.store.db.execute(sql,args);before=self.conserved()
                with self.metadata_only(),self.assertRaises(Refusal):
                    self.store.integration_metadata_closure_basis(self.job_id,self.token,self.owner)
                self.assertEqual(before,self.conserved())
        for change in [lambda c:c['tasks']['work-integrator'].update(network=True),
                lambda c:c['tasks']['work-integrator'].update(sandbox='read-only'),
                lambda c:c['tasks']['work-integrator'].update(execution='owner'),
                lambda c:c['tasks']['work-integrator']['routine_completion'].update(kind='file-witness'),
                lambda c:c['local_integration']['points'][next(iter(scope['reads']))].update(resources=['foreign-resource']),
                lambda c:c['local_integration']['points'][next(iter(scope['reads']))].update(bindings=[dict(native='branch',id='foreign')])]:
            config=copy.deepcopy(self.store.config);change(config)
            # Frozen task policy remains immutable. Config-only drift cannot
            # convert the old job into a newly convenient task shape.
            with self.rollback_case(),patch.object(self.store,'config',config):
                self.store.db.execute('UPDATE local_jobs SET policy=?',(digest(config['local_integration']),))
                with self.metadata_only(),self.assertRaises(Refusal):
                    self.store.integration_metadata_closure_basis(self.job_id,self.token,self.owner)
        with self.metadata_only(),self.assertRaises(Refusal):self.call('integration-metadata-closure-basis',actor='foreign-owner')
        with self.metadata_only(),self.assertRaises(Refusal):
            self.store.integration_metadata_closure_basis(self.job_id,'wrong-token',self.owner)
        with patch.object(self.store,'processing',object()),self.assertRaises(Refusal):
            self.store.integration_metadata_closure_basis(self.job_id,self.token,self.owner)
        # The response-bearing old withdrawal route remains inadmissible.
        with self.assertRaises(Refusal):self.store.integration_no_start_basis(self.job_id,self.token)

    async def test_every_controller_and_positive_no_start_diagnosis(self):
        self.store.db.execute('UPDATE attempts SET controller=? WHERE id=?',('fictional-diagnosis-controller721',self.diagnosis))
        self.store.db.execute('UPDATE jobs SET recovery_owner=? WHERE id=?',('fictional-recovery-controller721',self.job_id))
        receipt=self.receipt();self.assertEqual(len(receipt['controllers']),3)
        for c in receipt['controllers']:
            bad=copy.deepcopy(receipt);bad['controllers']=[v for v in bad['controllers'] if v!=c]
            with self.metadata_only(),self.assertRaises(Refusal):self.retire(bad)
        # A separately collected no-start diagnosis also qualifies. Existing
        # begun diagnosis history is retained without alteration.
        with self.store.tx():
            diagnosis=self.store._attempt('diagnosis',None,self.job_id,
                self.f.config['diagnosis']['binding'],self.f.config['diagnosis']['profile'])
        self.store.collect(diagnosis,dict(exit=None,result=None,capture='not-started',cleanup='no-session-created',
            detail=dict(known_not_started=True,resume_disposition='fictional no diagnosis process created')))
        before=self.conserved()
        with self.metadata_only():self.retire()
        self.assertEqual(before,self.conserved())

    async def test_only_execution_overlap_releases_without_successor_or_refund(self):
        incoming=event(self.f.config,'fictional-new-current-decision721')
        incoming['body']='Fictional distinct current coordination decision; all original source duties retained'
        incoming['integration']=copy.deepcopy(self.message['integration'])
        self.f.insert('events',dict(id=incoming['id'],role='Work',payload=encode(incoming),hash=digest(incoming),
            received=1001.,state='queued',ack='internal'))
        self.f.insert('queue',dict(id='fictional-future-queue721',event=incoming['id'],role='Work',phase='integrator',task='work-integrator'))
        row=self.store.one('SELECT * FROM queue WHERE id=?',('fictional-future-queue721',))
        members=[self.store._input_member(row)]
        self.assertFalse(local_integration.available(self.store,row,members))
        before=self.conserved();self.retire()
        self.assertTrue(local_integration.available(self.store,row,members))
        self.assertEqual(before,self.conserved())
        self.assertEqual(len(self.store.rows('SELECT id FROM jobs')),1)
        self.assertEqual(self.store.job(self.job_id)['effects'],'none')

    async def test_owed_outbox_observation_remains_lawful_after_retirement(self):
        delivery=self.store.one('SELECT * FROM outboxes WHERE job=?',(self.job_id,))
        self.retire();job=self.store.job(self.job_id);events=self.store.rows('SELECT * FROM events')
        self.store.delivery_observed(delivery['id'],dict(id=delivery['id'],state='settled',processed_at=1000.,
            recipient=self.owner,settlement={'evidence':['fictional recipient settles original question only']}))
        observed=self.store.one('SELECT * FROM outboxes WHERE id=?',(delivery['id'],))
        self.assertEqual(observed['state'],'settled');self.assertEqual(observed['processed_at'],1000.)
        self.assertEqual(observed['payload'],delivery['payload'])
        self.assertEqual(self.store.job(self.job_id),job);self.assertEqual(self.store.rows('SELECT * FROM events'),events)
        self.store.complete_events()
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(self.message['id'],))['processed_at'])

    async def test_final_fresh_basis_check_rolls_back_opaque_mutation(self):
        receipt=self.receipt();before=self.conserved();original=selected_source.custody_budget
        def change(runtime,incoming):
            original(runtime,incoming)
            runtime.db.execute("UPDATE outboxes SET error='fictional late opaque duty721'")
        with self.metadata_only(),patch.object(selected_source,'custody_budget',side_effect=change):
            with self.assertRaisesRegex(Refusal,'revision changed'):self.retire(receipt)
        self.assertEqual(before,self.conserved());self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'),[])

    async def test_callback_and_retirement_serialize_on_actual_journal_boundary(self):
        # Existing connections are opened before the basis: their initialization
        # is itself a revision change and may not be smuggled past selection.
        pool=ThreadPoolExecutor(max_workers=2)
        self.addCleanup(pool.shutdown)
        ready=Barrier(3);go=Barrier(3)
        def local_contend(index):
            store=Store(self.f.config,controller=self.store.controller,clock=lambda:1000.)
            try:
                ready.wait(timeout=10);go.wait(timeout=10)
                try:
                    if index==0:store.retire_integration_metadata(self.job_id,self.token,self.owner,selected[0])
                    else:store.session(self.attempt,'fictional-contradictory-late-session')
                except Refusal:return 'refused'
                return 'selected'
            finally:store.close()
        selected=[]
        futures=[pool.submit(local_contend,i) for i in range(2)]
        ready.wait(timeout=10);selected.append(self.receipt());go.wait(timeout=10)
        outcomes=[f.result(timeout=15) for f in futures]
        self.assertEqual(sorted(outcomes),['refused','selected'])
        self.assertEqual(int(bool(self.store.integration_retirement_recorded(self.job_id)))+
            int(bool(self.store.attempt(self.attempt)['session'])),1)


if __name__=='__main__':unittest.main(verbosity=2)
