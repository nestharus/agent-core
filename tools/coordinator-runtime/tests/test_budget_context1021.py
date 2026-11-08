"""Decision1021 joint outcomes in retained, network-isolated four-role fiction.

Real source-v1 selection, future selection, Store starts/direct births, window
rollover and filesystem custody run. Principals, clock, release/SDK pins and
collected END/answers are explicit fiction; no native/provider or live runtime.
"""
import gzip
import json
import sqlite3
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import patch

from test_future_software1008 import Future1008, at
from test_future_boundaries1014 import Boundaries1014
from support import collect, result
from coordinator_runtime import capacity, custody, processing, publication, routine, service
from coordinator_runtime import report_repair as repair
from coordinator_runtime import windows
from coordinator_runtime.contracts import Backpressure, Refusal, encode, ident
from coordinator_runtime.dispatcher import job_prompt


class Context1021(Future1008):
    reserve_event = Boundaries1014.reserve_event
    snapshot = Boundaries1014.snapshot

    def configure(self):
        super().configure()
        self.target = self.area/'fictional-role-record.json'
        self.target.write_bytes(b'{"original":true}\n')
        task = self.config['tasks']['work-proposer']
        task.update(effects='owner-reconcile', sandbox='workspace-write', network=False,
                    routine_completion=dict(kind='file-witness', targets=[str(self.target)]))
        task['effect_authority'].update(write_roots=[str(self.target)],
                                        operations=['read-reports','write-role-records'])

    def ready_result(self):
        return {**result(category='proposal'),
                'completion':dict(version=1,local='ready',failures=[],unknowns=[],tools=[])}

    def original_job(self, collected=False):
        self.now=at('07:35:00')
        job=self.reserve_event(self.pending_work['id'])
        if not collected:
            return job
        attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Work'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        # Establish the real delegated completion preconditions of a producer
        # response before testing its direct birth transaction. Equal stages
        # conserve the canonical preimage without changing its bytes/inode.
        (self.store.home/'artifacts'/attempt).mkdir(parents=True,exist_ok=True)
        task=self.config['tasks'][job['task']]
        routine.prepare(self.store,self.boards['Work'],self.store.job(job['id']),attempt,task)
        publication.conserve_stages(self.store,attempt,task)
        collect(self.store,attempt,self.ready_result(),
                tool_completion=dict(complete=True,items=[],nonzero_completions=0))
        self.assertTrue(routine.reconcile(self.store,self.boards['Work'],self.store.job(job['id'])))
        return self.store.job(job['id']),attempt

    def select_at(self, rearm=False):
        self.now=at('08:15:00');self.future_apply()
        if rearm:
            self.store.budget(None,16)
            self.assertEqual([r['ordinal'] for r in repair.software_receipt(self.store,self.cap)['activations']],[1])
            self.now=at('08:45:00')

    def fill_axis(self, kind):
        row=windows.current(self.store)
        cap=self.config['limits']['max_'+kind]
        with self.store.tx():
            # Explicit fictional occupied-axis prestate, increasing debit only.
            # The final credit and the subsequent rollover use real window APIs;
            # no allocation ceiling, cumulative start or birth frontier is reset.
            used=json.loads(row['used']);self.assertLess(used[kind],cap)
            used[kind]=cap-1
            self.store.db.execute('UPDATE service_windows SET used=? WHERE number=?',(encode(used),row['number']))
            windows.charge(self.store,kind)
        self.assertEqual(windows.current(self.store)['number'],row['number'])
        self.assertEqual(json.loads(windows.current(self.store)['used'])[kind],cap)
        return row['number']

    def rollover_start(self, rearm):
        job=self.original_job();self.select_at(rearm)
        window=self.fill_axis('attempts')
        starts=self.store.one('SELECT starts FROM processing_capabilities')['starts']
        held=self.store.job(self.source_job['id'])
        attempt=self.store.start_job(job['id'],job['token'])
        self.assertEqual(self.store.job(job['id'])['active_attempt'],attempt)
        self.assertEqual(self.store.job(job['id'])['state'],'running')
        self.assertEqual(windows.current(self.store)['number'],window+1)
        self.assertEqual(json.loads(windows.current(self.store)['used'])['attempts'],1)
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],35)
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities')['starts'],starts+1)
        self.assertEqual([r['ordinal'] for r in repair.software_receipt(self.store,self.cap)['activations']],
                         [1,2] if rearm else [1])
        self.assertEqual(self.store.job(self.source_job['id']),held)

    def rollover_birth(self, rearm):
        job,attempt=self.original_job(collected=True);self.select_at(rearm)
        window=self.fill_axis('events')
        source=self.store.attempt(attempt)
        before=repair.software_counters(self.store,self.cap,
            json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection']))
        # The producer response is a direct INSERT path, not ingest precharge.
        with self.store.tx():
            born=self.store._response(job,self.store.attempt(attempt),self.config['tasks'][job['task']],result(category='proposal'))
        self.assertIsNotNone(born)
        self.assertIsNotNone(self.store.one('SELECT id FROM events WHERE id=?',(born,)))
        self.assertEqual(windows.current(self.store)['number'],window+1)
        self.assertEqual(json.loads(windows.current(self.store)['used'])['events'],1)
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],35)
        after=repair.software_counters(self.store,self.cap,
            json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection']))
        self.assertEqual(after['new_inputs'],before['new_inputs']+1)
        self.assertEqual(after['starts'],before['starts'])
        self.assertEqual(self.store.attempt(attempt),source)
        self.assertEqual([r['ordinal'] for r in repair.software_receipt(self.store,self.cap)['activations']],
                         [1,2] if rearm else [1])

    def test_first_activation_start_rolls_real_available_window(self):self.rollover_start(False)
    def test_rearm_start_rolls_real_available_window(self):self.rollover_start(True)
    def test_first_activation_direct_birth_rolls_real_available_window(self):self.rollover_birth(False)
    def test_rearm_direct_birth_rolls_real_available_window(self):self.rollover_birth(True)

    def test_failed_outer_allocation_rolls_back_activation_and_window(self):
        job=self.original_job();self.select_at()
        self.fill_axis('attempts');before=self.snapshot()
        # Exercise failure AFTER nested window allocation, not only preflight.
        with patch.object(self.store.execution_pool,'allocate',side_effect=Refusal('fictional pool refusal after budget')):
            with self.assertRaises(Refusal):self.store.start_job(job['id'],job['token'])
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.store.job(job['id'])['state'],'reserved')
        self.assertEqual(repair.software_receipt(self.store,self.cap)['activations'],[])

    def test_exhausted_window_and_original_start_limit_keep_originals(self):
        job,attempt=self.original_job(collected=True);self.select_at()
        self.fill_axis('events')
        with self.store.tx():self.store._response(job,self.store.attempt(attempt),self.config['tasks'][job['task']],result(category='proposal'))
        self.fill_axis('events');self.now=at('08:45:00');before=self.snapshot()
        source=self.store.job(self.source_job['id']);original=self.store.attempt(source['active_attempt'])
        outcome={k:original[k] for k in ('exit','capture','cleanup','error')}
        outcome['result']=json.loads(original['result'] or 'null')
        with self.assertRaisesRegex(Refusal,'cumulative window ceiling'):
            service.Dispatcher.review_failure_return(SimpleNamespace(store=self.store,boards=self.boards,config=self.config),
                source,original['id'],outcome)
        self.assertEqual(self.snapshot(),before)
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])
        # Actual original start counter reaches the finite selection; no reset.
        self.store.db.execute('UPDATE processing_capabilities SET starts=? WHERE id=?',(self.plan['max_starts'],self.cap))
        before=self.snapshot()
        with self.assertRaisesRegex(Refusal,'cumulative start ceiling'),self.store.tx():
            self.store._attempt('task',None,job['id'],self.config['tasks'][job['task']]['binding'],'.codex2')
        self.assertEqual(self.snapshot(),before)

    def frozen_input(self):
        job,attempt=self.original_job(collected=True)
        # An actual conserved completed-producer artifact becomes a prior input
        # of a distinct running original job. No event/hash is rewritten.
        origin=self.area/'fictional-completed-producer.txt';origin.write_bytes(b'Whole retained producer bytes\n')
        custody.capture(self.store,attempt,str(origin),self.config['tasks'][job['task']],role_owned=True)
        witness=custody.witnesses(self.store,attempt)[0]
        peer=self.post('Branch','branch-proposer','fictional-frozen-consumer')
        consumer=self.reserve_event(peer['id'])
        active=self.store.start_job(consumer['id'],consumer['token'])
        detail=json.loads(self.store.attempt(active)['detail'])
        detail['prior_artifact_witnesses']=[witness]
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),active))
        (self.store.home/'artifacts'/active).mkdir(parents=True,exist_ok=True)
        return self.store.job(consumer['id']),active,witness,origin

    def test_real_job_prompt_materializes_frozen_input_outside_transaction(self):
        job,attempt,witness,origin=self.frozen_input();self.select_at()
        starts=self.store.one('SELECT starts FROM processing_capabilities')['starts']
        self.assertFalse(self.store.db.in_transaction)
        prompt=job_prompt(self.store,job)
        path=self.store.home/'artifacts'/attempt/'inputs'/witness['sha256']
        self.assertEqual(path.read_bytes(),origin.read_bytes());self.assertIn(str(path),prompt)
        artifact=self.store.one('SELECT * FROM artifacts WHERE path=?',(str(path),))
        self.assertEqual(artifact['sha256'],witness['sha256']);self.assertIsNotNone(artifact['conserved'])
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities')['starts'],starts)
        self.assertEqual([r['ordinal'] for r in repair.software_receipt(self.store,self.cap)['activations']],[1])
        original=path.stat();snapshot=self.snapshot()
        job_prompt(self.store,job)  # Existing exact copy does not consume another activation/start.
        self.assertEqual(path.stat().st_ino,original.st_ino);self.assertEqual(self.snapshot(),snapshot)
        self.assertFalse(self.store.db.in_transaction)

    def frozen_refusal(self, reason):
        job,attempt,witness,origin=self.frozen_input();self.select_at()
        before=self.snapshot();usage=self.store.usage()
        if reason=='bytes':
            context=patch.object(self.store,'usage',return_value={**usage,'bytes':self.config['limits']['max_bytes']-capacity.PRESSURE_RESERVE})
            error=Backpressure
        elif reason=='pins':
            context=patch.object(processing,'implementation',return_value={**self.new_impl,'store.py':'0'*64})
            error=Refusal
        elif reason=='epoch':
            self.now=at('10:44:25');context=patch.object(self.store,'clock',side_effect=lambda:self.now);error=Refusal
        else:raise AssertionError(reason)
        with context,self.assertRaises(error):job_prompt(self.store,job)
        self.assertEqual(self.snapshot(),before)
        self.assertFalse((self.store.home/'artifacts'/attempt/'inputs'/witness['sha256']).exists())
        self.assertEqual(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(witness['sha256'],))['body'],origin.read_bytes())
        self.assertEqual(self.store.job(job['id'])['state'],'running')
        self.assertFalse(self.store.db.in_transaction)

    def test_frozen_copy_real_byte_limit_retains_source(self):self.frozen_refusal('bytes')
    def test_frozen_copy_wrong_source_pins_retains_source(self):self.frozen_refusal('pins')
    def test_frozen_copy_original_epoch_refuses_and_retains_source(self):self.frozen_refusal('epoch')

    def running_routine(self):
        job=self.original_job();attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Work'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        (self.store.home/'artifacts'/attempt).mkdir(parents=True,exist_ok=True)
        self.select_at()
        return self.store.job(job['id']),attempt,self.config['tasks'][job['task']]

    def prepare_routine(self):
        job,attempt,task=self.running_routine()
        self.assertFalse(self.store.db.in_transaction)
        routine.prepare(self.store,self.boards['Work'],job,attempt,task)
        stages=publication.stages(self.store,attempt)
        self.assertEqual(set(stages),{str(self.target)})
        self.assertEqual(Path(stages[str(self.target)]).read_bytes(),self.target.read_bytes())
        self.assertEqual(self.store.one('SELECT state FROM routine_runs WHERE attempt=?',(attempt,))['state'],'prepared')
        return job,attempt,task,stages

    def test_real_routine_staging_and_backup_reconcile_outside_transaction(self):
        original=self.target.read_bytes();inode=self.target.stat().st_ino
        job,attempt,task,stages=self.prepare_routine()
        # Keep stage bytes equal: exercise genuine backup/publication custody
        # with a nonmutating canonical probe and no tool/provider invocation.
        publication.conserve_stages(self.store,attempt,task)
        collect(self.store,attempt,self.ready_result(),
                tool_completion=dict(complete=True,items=[],nonzero_completions=0))
        self.assertTrue(routine.reconcile(self.store,self.boards['Work'],self.store.job(job['id'])))
        backup=self.store.one('SELECT * FROM canonical_backups WHERE attempt=?',(attempt,))
        self.assertEqual(gzip.decompress(Path(backup['path']).read_bytes()),original)
        self.assertIsNotNone(self.store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?',(attempt,backup['path'])))
        self.assertEqual(self.target.read_bytes(),original);self.assertEqual(self.target.stat().st_ino,inode)
        self.assertEqual(self.store.job(job['id'])['effects'],'reconciled')
        self.assertFalse(self.store.db.in_transaction)

    def test_staging_real_byte_limit_keeps_prepared_debt_and_preimage(self):
        job,attempt,task=self.running_routine()
        original=self.target.read_bytes();budget=self.store.budget
        def capacity_at_stage(kind,incoming=0,**kwargs):
            if not self.store.db.in_transaction:
                usage=self.store.usage()
                with patch.object(self.store,'usage',return_value={**usage,'bytes':self.config['limits']['max_bytes']-capacity.PRESSURE_RESERVE}):
                    return budget(kind,incoming,**kwargs)
            return budget(kind,incoming,**kwargs)
        with patch.object(self.store,'budget',side_effect=capacity_at_stage),self.assertRaises(Backpressure):
            routine.prepare(self.store,self.boards['Work'],job,attempt,task)
        self.assertEqual(publication.stages(self.store,attempt),{})
        self.assertEqual(self.store.one('SELECT state FROM routine_runs WHERE attempt=?',(attempt,))['state'],'prepared')
        self.assertEqual(self.target.read_bytes(),original)
        self.assertFalse(self.store.db.in_transaction)

    def test_backup_real_byte_limit_keeps_stages_original_and_debt(self):
        original=self.target.read_bytes();job,attempt,task,stages=self.prepare_routine()
        publication.conserve_stages(self.store,attempt,task)
        collect(self.store,attempt,self.ready_result(),
                tool_completion=dict(complete=True,items=[],nonzero_completions=0))
        usage=self.store.usage()
        with patch.object(self.store,'usage',return_value={**usage,'bytes':self.config['limits']['max_bytes']-capacity.PRESSURE_RESERVE}),self.assertRaises(Backpressure):
            routine.reconcile(self.store,self.boards['Work'],self.store.job(job['id']))
        self.assertEqual(self.target.read_bytes(),original)
        self.assertEqual(self.store.rows('SELECT * FROM canonical_backups WHERE attempt=?',(attempt,)),[])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications WHERE attempt=?',(attempt,)),[])
        self.assertEqual(publication.stages(self.store,attempt),stages)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])
        self.assertFalse(self.store.db.in_transaction)

    def test_staging_changed_source_rights_keeps_canonical_and_original(self):
        job,attempt,task=self.running_routine();before=self.snapshot();original=self.target.read_bytes()
        with patch.object(processing,'implementation',return_value={**self.new_impl,'store.py':'0'*64}),self.assertRaises(Refusal):
            routine.prepare(self.store,self.boards['Work'],job,attempt,task)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(publication.stages(self.store,attempt),{})
        self.assertEqual(self.target.read_bytes(),original)

    def test_backup_original_epoch_keeps_collected_result_stages_and_preimages(self):
        job,attempt,task,stages=self.prepare_routine()
        publication.conserve_stages(self.store,attempt,task)
        collect(self.store,attempt,self.ready_result(),
                tool_completion=dict(complete=True,items=[],nonzero_completions=0))
        self.now=at('10:44:25');before=self.snapshot();original=self.target.read_bytes()
        with self.assertRaises(Refusal):
            routine.reconcile(self.store,self.boards['Work'],self.store.job(job['id']))
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(publication.stages(self.store,attempt),stages)
        self.assertEqual(self.target.read_bytes(),original)
        self.assertEqual(self.store.rows('SELECT * FROM canonical_backups WHERE attempt=?',(attempt,)),[])
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])

    def test_outside_byte_allocation_unbound_foreign_and_readonly_refuse(self):
        self.select_at();original=self.store.processing;before=self.snapshot()
        try:
            for access in (None,processing.Access(self.store,ident(),self.boards)):
                self.store.processing=access
                with self.assertRaisesRegex(Refusal,'explicit original future software capability'):
                    self.store.budget(None,16)
                self.assertEqual(self.snapshot(),before)
        finally:self.store.processing=original
        self.store.db.execute('PRAGMA query_only=ON')
        try:
            with self.assertRaises(sqlite3.OperationalError):self.store.budget(None,16)
            self.assertEqual(self.snapshot(),before)
        finally:self.store.db.execute('PRAGMA query_only=OFF')


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(Context1021(n) for n in Context1021.__dict__ if n.startswith('test_'))
