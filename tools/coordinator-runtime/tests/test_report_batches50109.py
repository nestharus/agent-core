"""New owned public Board fiction for exact Reviews composition boundaries."""
import copy
import json
import time
import unittest
from test_qa629_repairs import Fixture, actor
from support import result, collect
from coordinator_runtime import processing, prospective, service, report_scope, resource_scopes
from coordinator_runtime.contracts import Refusal, digest, encode


class ReportBatches(Fixture):
    def setUp(self):
        self.bootstrap(self.configure)
        self.issuer = self.config['roles']['Work']['owner']
        for r,b in self.boards.items():
            with actor(b.store,self.issuer): b.revoke_software(self.store,self.store.enrollment(r)['grant_id'])
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(r,))
        self.store.db.execute("UPDATE enrollments SET legacy_hold='Reviews UNKNOWN' WHERE role='Reviews'")
        self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for b in self.boards.values(): b.runtime=self.store
        n=160000 if 'large' in self._testMethodName else 32
        self.reports=[dict(reference='report-'+str(i),collector=self.issuer,actual_END=0,
            reports=[dict(name='Source',body='x'*n+' \" dissent Ω')],history='Whole fictional history',
            method_pin='fiction HIGH',coverage=dict(status='PARTIAL',unread=['family9']),effects='known-report-only') for i in range(2)]
        self.selection=dict(basis=processing.basis(self.store,self.boards),authority='Fictional Work finite report scope',
            retained_events=[],recover_controls={},future_intake=True,tasks=list(self.config['tasks']),
            max_shared_rows=1000,max_shared_payload_bytes=1000000,max_runtime_rows=1000,
            service=dict(max_inflight=8,reviews={},report_tasks=['reviews-integrator'],legacy_resources={'Reviews':dict(
                original_hold='Reviews UNKNOWN',roots=[],unbounded=True,evidence='Unrelated debts retained',
                reviews_report=dict(version='reviews-report-v1',authority='Fictional exact report choice',expires=time.time()+600,
                    task='reviews-integrator',task_sha256=digest(self.config['tasks']['reviews-integrator']),
                    reports=[dict(reference=r['reference'],sha256=digest(r)) for r in self.reports]))}))
        with actor(self.boards['Work'].store,self.issuer): self.cap=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        self.runtime.boards=self.boards
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Fictional exact no-effect choice',
            expires=time.time()+600,processing_capability=self.cap,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))

    def configure(self):
        self.config['limits']['max_result_bytes']=262144
        t=self.config['tasks']['reviews-integrator']; t.update(effects='owned-artifacts',sandbox='workspace-write')
        t['effect_authority'].update(operations=['read-reports','consolidate-reports','write-owned-artifacts'],write_roots=[])

    def admit(self,reports):
        ids=[service.ingest_report(self.store,self.issuer,'reviews-integrator',r)['event'] for r in reports]
        self.classify()
        return ids

    def complete(self,job):
        envelopes=report_scope.conserved_inputs(self.store,job)
        answer=result(category='consolidated'); answer['findings']=[dict(collected_reports=envelopes)]
        self.assertLessEqual(len(encode(answer).encode()),self.config['limits']['max_result_bytes'])
        attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Reviews'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        response=self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.event(response)['body'],answer)
        return [r['event'] for r in envelopes]

    def test_large_valid_reports_split_complete_and_conserve(self):
        ids=self.admit(self.reports)
        exact=[dict(event=e,sha256=digest(self.store.event(e)),original=self.store.event(e)['body']) for e in ids]
        answer=result(category='consolidated');answer['findings']=[dict(collected_reports=exact)]
        self.assertGreater(len(encode(answer).encode()),262144)
        finished=[]
        for _ in ids:
            job=self.store.reserve();self.assertIsNotNone(job)
            self.assertEqual(len(json.loads(job['members'])),1)
            finished+=self.complete(job)
        self.assertEqual(finished,ids)
        for e,r in zip(ids,self.reports):self.assertEqual(self.store.event(e)['body']['original'],r)

    def test_mixed_distinct_invalid_neighbor_cannot_freeze_valid(self):
        bad=copy.deepcopy(self.reports[1]);bad['history']='Changed unselected whole history'
        ids=self.admit([self.reports[0],bad])
        badrow=self.store.one('SELECT * FROM queue WHERE event=?',(ids[1],))
        self.assertTrue(resource_scopes.blocked(self.store,badrow))
        job=self.store.reserve();self.assertIsNotNone(job)
        self.assertEqual([m['event'] for m in json.loads(job['members'])],[ids[0]])
        self.assertEqual(self.complete(job),[ids[0]])
        self.assertEqual(self.store.one('SELECT state,job FROM queue WHERE event=?',(ids[1],)),dict(state='queued',job=None))
        self.assertEqual(self.store.event(ids[1])['body']['original'],bad)
        self.assertIsNone(self.store.reserve())

    def test_small_all_valid_compose_and_single(self):
        ids=self.admit(self.reports)
        job=self.store.reserve();self.assertEqual(len(json.loads(job['members'])),2)
        self.assertEqual(self.complete(job),ids)

    def test_changed_current_authority_refuses_original_unchanged(self):
        ids=self.admit(self.reports)
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.event(ids[0])['body']['original'],self.reports[0])

    def test_single_complete_return_boundary_counts_json_overhead(self):
        # Selected intake limit is unchanged. Actual minimal result includes
        # escaped JSON, envelope, source digest and every required result field.
        r=copy.deepcopy(self.reports[0]);r['reports'][0]['body']='z'
        from coordinator_runtime.report_scope import complete_return
        def envelope(n):
            r['reports'][0]['body']='z'*n
            body=dict(kind='attributed-report',original=r,native_owner_execution=False,
                meaning='Work testimony and whole report input; not persistent Reviews owner collection or native liveness')
            event=dict(id=digest(dict(attributed_report=dict(collector=self.issuer,reference=r['reference']))),role='Reviews',
                recipient=self.config['roles']['Reviews']['owner'],kind='response',author=self.issuer,
                allowed_tasks=['reviews-integrator'],package=None,processing_report=self.cap,body=body)
            return dict(event=event['id'],sha256=digest(event),original=body)
        n=262144-len(encode(complete_return([envelope(0)])).encode())
        self.assertEqual(len(encode(complete_return([envelope(n)])).encode()),262144)
        r['reports'][0]['body']='z'*(n+1)
        before=self.store.one('SELECT COUNT(*) AS n FROM events')['n']
        with self.assertRaisesRegex(Refusal,'complete return'):service.ingest_report(self.store,self.issuer,'reviews-integrator',r)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM events')['n'],before)
        # Exact boundary intake and complete typed collection both succeed under
        # a genuine new Work policy, selected BEFORE this new receipt intake.
        r['reports'][0]['body']='z'*n
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        with actor(self.boards['Work'].store,self.issuer):
            processing.revoke(self.store,self.boards,self.cap)
            self.selection['basis']=processing.basis(self.store,self.boards)
            self.selection['service']['legacy_resources']['Reviews']['reviews_report']['reports']=[dict(reference=r['reference'],sha256=digest(r))]
            self.cap=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Fictional new exact boundary report choice',
            expires=time.time()+600,processing_capability=self.cap,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))
        e=service.ingest_report(self.store,self.issuer,'reviews-integrator',r)['event']
        self.assertEqual(self.store.event(e)['body']['original'],r)
        self.classify();q=self.store.one('SELECT * FROM queue WHERE event=?',(e,))
        self.assertFalse(resource_scopes.blocked(self.store,q))
        job=self.store.reserve();self.assertIsNotNone(job)
        answer=complete_return(report_scope.conserved_inputs(self.store,job))
        self.assertEqual(len(encode(answer).encode()),262144)
        attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Reviews'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        response=self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.event(response)['body'],answer)
