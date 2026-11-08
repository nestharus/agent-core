"""Decision1014 outcome tests in retained, isolated four-role fiction.

Oracles come from the authentic joint Decision/Frame, not private runtime facts.
Real Store/CLI/source/report/control/delivery controllers run. Principals, clock,
reviewed release claims, collected wire answers and prior-retired history are
explicit fixture seams. No removal, provider, native invocation or live journal.
"""
import contextlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_future_software1008 import Future1008, at
from test_qa629_repairs import actor
from test_plain_control817 import Terminal817
from support import collect, result, event
from coordinator_runtime import cli, processing, processing_admission, service, prospective, local_integration
from coordinator_runtime import report_repair as repair
from coordinator_runtime.store import Store
from coordinator_runtime.contracts import Backpressure, Refusal, SOL, digest, encode, ident


class Boundaries1014(Future1008):
    fresh = Terminal817.fresh

    def serving_fixture(self):
        # Fictional original controller metadata only, not a running process,
        # model start, socket or activation. The CLI must use its real ro DB.
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',
            (self.store.controller,self.cap,'owned',self.now))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,NULL,NULL)',
            (self.store.controller,self.cap,'fictional-no-socket','serving',self.now))

    def configure(self):
        super().configure()
        task=self.config['tasks']['reviews-integrator']
        self.config['local_integration']=dict(max_inflight=8,points={},tasks={
            'reviews-integrator':dict(capacity=5,discovery_batch=4,points=[],
                authority='Original fictional local report method selection',method=task['templates'][0])})

    def count(self):
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        return repair.software_counters(self.store,self.cap,raw)['new_inputs']

    def select_remaining(self,remaining):
        self.plan['max_new_inputs']=self.count()+remaining
        self.plan_file.write_text(encode(self.plan))
        self.future_apply()

    def reserve_event(self,key):
        with self.store.tx():
            row=self.store.one('SELECT * FROM queue WHERE event=?',(key,))
            job=self.store._reserve_candidate(row)
        self.assertIsNotNone(job,'all actual reservation gates must admit this original')
        return job

    def snapshot(self):
        return list(self.store.db.iterdump())

    def test_query_only_cli_before_activation_and_rearm_is_observational(self):
        self.future_apply()
        self.assertEqual(repair.software_receipt(self.store,self.cap)['activations'],[])
        self.serving_fixture()
        original=Store
        readers=[]
        def opened(config,**options):
            self.assertTrue(options['read_only'])
            reader=original(config,clock=lambda:self.now,**options)
            self.assertEqual(reader.one('PRAGMA query_only')['query_only'],1)
            readers.append(reader)
            return reader
        for moment in ('08:15:00','08:45:00'):
            self.now=at(moment);before=self.snapshot()
            for flag in ('--diagnostics','--reservation-only'):
                output=io.StringIO()
                with patch.object(cli,'load_config',return_value=self.config),patch.object(cli,'Store',side_effect=opened), \
                        patch.dict('os.environ',{'CODEX_SESSION_ID':self.issuer}), \
                        actor(self.boards['Work'].store,self.issuer),contextlib.redirect_stdout(output):
                    code=cli.main(['--config','/fictional-owned-config','processing-source',self.cap,self.board_source['id'],flag])
                self.assertEqual(code,0,output.getvalue())
                self.assertNotEqual(json.loads(output.getvalue()).get('state'),'held')
            self.assertEqual(before,self.snapshot())
            self.assertEqual(repair.software_receipt(self.store,self.cap)['activations'],[])
        starts=self.store.one('SELECT starts FROM processing_capabilities')['starts']
        with self.store.tx():self.store.budget(None,16)
        activation=repair.software_receipt(self.store,self.cap)['activations']
        self.assertEqual([r['ordinal'] for r in activation],[2])
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities')['starts'],starts)

    def test_framework_frozen_job_before_apply_and_across_rearm(self):
        self.now=at('07:35:00')
        job=self.reserve_event(self.report_id)
        frozen=self.store.one('SELECT * FROM local_jobs WHERE job=?',(job['id'],))
        self.assertEqual(json.loads(frozen['scope'])['lane'],'report')
        route=json.loads(frozen['scope'])['report_route']
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        policy=raw['service']['legacy_resources']['Reviews']
        self.assertEqual(route['policy'],digest(policy))
        self.now=at('08:15:00');self.future_apply()
        for moment in ('08:15:00','08:45:00','10:30:01'):
            self.now=at(moment)
            local_integration.current_job(self.store,job)
            self.assertEqual(local_integration.report_route(self.store,job),route)
            self.assertEqual(self.store.one('SELECT * FROM local_jobs WHERE job=?',(job['id'],)),frozen)
            self.assertEqual(self.store.processing.current()[1]['service']['legacy_resources']['Reviews'],policy)
        self.now=at('10:44:25')
        with self.assertRaises(Refusal):local_integration.current_job(self.store,job)
        self.assertEqual(self.store.one('SELECT * FROM local_jobs WHERE job=?',(job['id'],)),frozen)

    def test_old_qa_control_report_source_after_stop_end_and_pressure(self):
        self.now=at('07:35:00')
        control,control_attempt,_=Terminal817.original(self)
        self.now=at('08:15:00');self.future_apply()
        self.serving_fixture()
        source=self.store.event(self.board_source['id'])
        raw=json.loads(self.before['processing_capabilities'][0]['selection'])
        scope=raw['software_admission']['scopes']['fixture']
        self.command(['stop-future-software',self.cap,'--reason','Original owned work keeps original finite rights'])
        for moment in ('08:15:00','10:30:01'):
            self.now=at(moment)
            with self.assertRaises(Backpressure):service.admit_input(self.store)
            self.assertTrue(self.store.processing.event(source))
            resolved=processing_admission.resolved(self.store,source['package'],'fixture',digest(scope))
            self.assertEqual(digest(resolved),self.before['processing_admission_resolutions'][0]['admission_hash'])
            self.command(['processing-source',self.cap,self.board_source['id'],'--diagnostics'])
            self.assertEqual(service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)['event'],self.report_id)
            processing.apply_control(self.store,control['id'],control_attempt)
            self.assertIsNotNone(self.store.input_resolution(control['id']))
            with self.store.tx():self.store.budget('attempts')
        usage=self.store.usage()
        with patch.object(self.store,'usage',return_value={**usage,'bytes':self.plan['pause_bytes']}):
            self.assertTrue(self.store.processing.event(source))
            with self.assertRaises(Backpressure):service.admit_input(self.store)
            with self.store.tx():self.store.budget('attempts')
        self.now=at('10:44:25')
        with self.assertRaises(Refusal):self.store.processing.event(source)
        with self.assertRaises(Refusal):processing_admission.resolved(self.store,source['package'],'fixture',digest(scope))
        with self.assertRaises(Refusal):service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)
        with self.assertRaises(Refusal):processing.apply_control(self.store,control['id'],control_attempt)

    def test_unbound_or_foreign_writer_cannot_borrow_original_plan(self):
        self.future_apply()
        access=self.store.processing
        before=self.snapshot()
        try:
            for other in (None,processing.Access(self.store,ident(),self.boards)):
                self.store.processing=other
                with self.assertRaisesRegex(Refusal,'explicit original future software capability'),self.store.tx():
                    self.store.budget('events')
                self.assertEqual(self.snapshot(),before)
        finally:self.store.processing=access

    def test_lifetime_frontier_with_already_retired_history_never_refunds(self):
        # Construct a lawful fictional preexisting history with a retained last
        # birth at8191 and a previously retired interior cohort. No row/artifact
        # is deleted, moved or rewritten to create that history.
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        marker=event(self.config,'fictional-surviving-birth8191')
        with self.store.tx():
            self.store.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',
                (marker['id'],'Work',encode(marker),digest(marker),self.now))
            self.store.db.execute('INSERT INTO processing_source_positions(position,event) VALUES(?,?)',
                (raw['basis']['event_boundary']+8191,marker['id']))
        self.assertEqual(self.count(),8191)
        self.assertLess(self.store.one('SELECT COUNT(*) n FROM processing_source_positions')['n'],8191)
        before=self.store.rows('SELECT * FROM processing_source_positions')
        self.future_apply()
        self.post('Work','work-proposer',None)
        self.assertEqual(self.count(),8192)
        with self.assertRaises(Backpressure):service.admit_input(self.store)
        with self.store.tx(),self.assertRaises(Backpressure):self.store.budget('events')
        for row in before:self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(row['event'],)),row)
        self.assertEqual(self.count(),8192)

    def writer_case(self,kind,ceiling):
        # Real already-collected original Source and pending Work job remain.
        self.now=at('07:35:00')
        if kind=='control':
            control,control_attempt,_=Terminal817.original(self)
        job=self.reserve_event(self.pending_work['id'])
        attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Work'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        answer=result(category='proposal')
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=0))
        job=self.store.job(job['id'])
        if kind=='delivery':
            with self.store.tx():self.store._outbox('Work','Work','result',dict(whole=answer),job=job['id'])
        self.now=at('08:15:00');self.select_remaining(1)
        if ceiling:
            self.post('Work','work-proposer',None)
        else:
            # Match a fresh CLI entry with no preattached Access. Stop may end
            # future intake while real original completion still has headroom.
            self.store.processing=None
            self.command(['stop-future-software',self.cap,'--reason','Keep original completion within original epoch'])
            self.now=at('10:30:01')
            with self.assertRaises(Backpressure):service.admit_input(self.store)
        before=self.count();originals=self.store.rows('SELECT * FROM attempts')
        original_jobs=self.store.rows('SELECT * FROM jobs')
        outboxes=self.store.rows('SELECT * FROM outboxes')
        queues=self.store.rows('SELECT * FROM queue')
        positions=self.store.rows('SELECT * FROM processing_source_positions')
        resolutions=self.store.rows('SELECT * FROM input_resolutions')
        source_attempt=self.store.job(self.source_job['id'])['active_attempt']
        stored_source=self.store.attempt(source_attempt)
        source_outcome={k:stored_source[k] for k in ('exit','capture','cleanup','error')}
        source_outcome['result']=json.loads(stored_source['result'] or 'null')
        def invoke():
            if kind=='producer':return self.store.finish_job(job['id'],job['token'])
            if kind=='delivery':return self.store.gate_result_delivery(job,self.store.attempt(attempt),answer)
            if kind=='control':
                return processing.apply_control(self.store,control['id'],control_attempt)
            if kind=='source':return service.Dispatcher.review_failure_return(SimpleNamespace(store=self.store,boards=self.boards,config=self.config),self.store.job(self.source_job['id']),source_attempt,source_outcome)
        if ceiling:
            with self.assertRaisesRegex(Backpressure,'universal future software birth'):invoke()
            self.assertEqual(self.store.rows('SELECT * FROM attempts'),originals)
            self.assertEqual(self.store.rows('SELECT * FROM jobs'),original_jobs)
            self.assertEqual(self.store.rows('SELECT * FROM outboxes'),outboxes)
            self.assertEqual(self.store.rows('SELECT * FROM queue'),queues)
            self.assertEqual(self.store.rows('SELECT * FROM processing_source_positions'),positions)
            self.assertEqual(self.store.rows('SELECT * FROM input_resolutions'),resolutions)
            self.assertEqual(self.count(),before)
        else:
            invoke();self.assertEqual(self.count(),before+1)
            self.assertEqual(self.store.rows('SELECT * FROM attempts'),originals)
        self.assertEqual(self.store.job(self.source_job['id'])['state'],'held')
        self.assertEqual(self.store.attempt(source_attempt)['exit'],6)
        self.assertEqual(self.store.attempt(source_attempt)['capture'],'incomplete')

    def test_direct_birth_pressure_retains_collected_source(self):
        self.future_apply()
        job=self.store.job(self.source_job['id']);attempt=self.store.attempt(job['active_attempt'])
        outcome={k:attempt[k] for k in ('exit','capture','cleanup','error')}
        outcome['result']=json.loads(attempt['result'] or 'null')
        dispatcher=SimpleNamespace(store=self.store,boards=self.boards,config=self.config)
        before=self.snapshot();usage=self.store.usage()
        for pressure in ({**usage,'bytes':self.plan['pause_bytes']},
                         {**usage,'alerts':self.config['limits']['max_alerts']}):
            with patch.object(self.store,'usage',return_value=pressure):
                with self.assertRaisesRegex(Backpressure,'universal future software birth'):
                    service.Dispatcher.review_failure_return(dispatcher,job,attempt['id'],outcome)
            self.assertEqual(self.snapshot(),before)
        count=self.count()
        service.Dispatcher.review_failure_return(dispatcher,job,attempt['id'],outcome)
        self.assertEqual(self.count(),count+1)
        self.assertEqual(self.store.attempt(attempt['id']),attempt)
        self.assertEqual(self.store.job(job['id']),job)

    def test_producer_below(self):self.writer_case('producer',False)
    def test_producer_ceiling_retains_original(self):self.writer_case('producer',True)
    def test_control_below(self):self.writer_case('control',False)
    def test_control_ceiling_retains_original(self):self.writer_case('control',True)
    def test_delivery_below(self):self.writer_case('delivery',False)
    def test_delivery_ceiling_retains_original(self):self.writer_case('delivery',True)
    def test_incomplete_source_below(self):self.writer_case('source',False)
    def test_incomplete_source_ceiling_retains_original(self):self.writer_case('source',True)



class EarlyReport1014(Boundaries1014):
    def select(self,service_policy=None):
        original=processing.select
        def before_selection(runtime,boards,selection):
            selection['service']['legacy_resources']['Reviews']['reviews_report']['expires']=at('08:55:00')
            return original(runtime,boards,selection)
        with patch.object(processing,'select',side_effect=before_selection):
            return super().select(service_policy)

    def test_original_report_expiry_is_independent_of_future_rearm(self):
        self.now=at('07:35:00');job=self.reserve_event(self.report_id)
        frozen=self.store.one('SELECT * FROM local_jobs WHERE job=?',(job['id'],))
        self.now=at('08:15:00');self.future_apply()
        self.now=at('08:45:00');local_integration.current_job(self.store,job)
        self.now=at('08:55:00')
        service.admit_input(self.store)  # Future intake is still independently valid.
        with self.assertRaisesRegex(Refusal,'finite Reviews report policy'):
            local_integration.current_job(self.store,job)
        self.assertEqual(self.store.one('SELECT * FROM local_jobs WHERE job=?',(job['id'],)),frozen)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(cls(n) for cls in (Boundaries1014,EarlyReport1014)
        for n in cls.__dict__ if n.startswith('test_'))
