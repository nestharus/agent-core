"""Owned four-Board software fiction; authentic queue/producer/control APIs.

Actor identity, model collections, release/code pins and original process END
are explicit synthetic seams. No provider/native execution or live adoption.
"""
import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_qa629_repairs import Fixture, actor
from test_report_transport739 import ReportTransport
from support import collect, result
from coordinator_runtime import processing, prospective, service, report_repair as repair, configuration, windows, cli
from coordinator_runtime.contracts import Refusal, Backpressure, SOL, digest, encode, ident
from coordinator_runtime.service_wake import ServiceWake


class OwnerLease(Fixture):
    def configure(self):
        self.config['limits']['max_result_bytes'] = 262144
        self.config['window_service'] = dict(tasks=list(self.config['tasks']), max_new_inputs=40,batch_size=8,max_decisions=100)
        task = self.config['tasks']['reviews-integrator']
        task.update(effects='owned-artifacts',sandbox='workspace-write')
        task['effect_authority'].update(operations=['read-reports','consolidate-reports','write-owned-artifacts'],write_roots=[])

    def setUp(self):
        self.bootstrap(self.configure)
        self.now = 1000.
        self.store.clock = lambda:self.now
        self.issuer = self.config['roles']['Work']['owner']
        self.controller = self.store.controller
        self.new_impl = processing.implementation()
        self.modules = sorted(repair.LEASE_MODULES)
        self.old_impl = getattr(self, 'historical_implementation', None) or {k:('0'*64 if k in self.modules else v) for k,v in self.new_impl.items()}
        self.report = dict(reference='original797',collector=self.issuer,actual_END=0,
            reports=[dict(name='whole',body='Original dissent, UNKNOWN effects, retained duties Ω.')],history='Whole original history',
            method_pin='synthetic method',coverage=dict(status='PARTIAL',unread=['native source']),effects='known-report-only')
        policy = dict(version='reviews-report-v1',authority='Synthetic original finite report right',expires=1500.,
            task='reviews-integrator',task_sha256=digest(self.config['tasks']['reviews-integrator']),
            reports=[dict(reference=self.report['reference'],sha256=digest(self.report))])
        original_select=processing.select
        def current_allocation(runtime,boards,selection):
            selection['service']['allocations']['basis']=windows.basis(runtime)
            return original_select(runtime,boards,selection)
        with patch.object(processing,'implementation',return_value=self.old_impl), patch.object(processing,'select',side_effect=current_allocation):
            self.select(dict(max_inflight=5,reviews={},report_tasks=['reviews-integrator'],
                admission=dict(until=1500.,pause_bytes=90000000,max_new_inputs=40),
                wake=dict(protocol='managed-hint-v1',roles=list(self.config['roles']),until=1500.),
                allocations=dict(**dict(basis=windows.basis(self.store),target='finite remaining work',reason='retain original debts',
                    evidence='synthetic owner bounded windows',custody={r:dict(owner=v['owner'],evidence='same original custodian') for r,v in self.config['roles'].items()}),expires=1500.,max_windows=4),
                legacy_resources={'Reviews':dict(original_hold=None,roots=[],unbounded=True,evidence='original report custody',reviews_report=policy)}))
            self.epoch = prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Synthetic finite epoch',
                expires=1500.,processing_capability=self.cap,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
                tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))
            self.input = service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)['event']
            self.classify()
            job = self.store.reserve(); self.assertEqual(job['task'],'reviews-integrator')
            attempt = self.store.start_job(job['id'],job['token']); job=self.store.job(job['id'])
            self.boards['Reviews'].bind_software_attempt(self.store,job,attempt,None)
            self.producer_result = ReportTransport.answer(self,job)
            collect(self.store,attempt,self.producer_result,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
            self.work = self.store.finish_job(job['id'],job['token']); self.assertIsNotNone(self.work)
            self.classify()
            self.control = self.post('Reviews','@control',None)['id']
            with self.store.tx():
                self.control_attempt = self.store._attempt('input-control',self.control,None,SOL,'.codex3')
                self.store.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',(self.control,self.cap,self.control_attempt,digest(self.store.event(self.control))))
            receipt=dict(source_hash=digest(self.store.event(self.control)),mode='control',task='@control',package=None,
                related_event=None,related_job=None,reason='Keep whole original Work debt; no repeated review or native acceptance',
                evidence=['Synthetic collected original status'],remaining_obligations=['Old Work consumer and all holds remain'])
            collect(self.store,self.control_attempt,dict(semantic='DONE',summary='Original collected control',decision_json=encode(receipt)),
                tool_completion=dict(complete=True,items=[],nonzero_completions=[],unknown_types=[]))
            self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.controller,self.cap,'owned',1000.))
            self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',(self.controller,self.cap,'synthetic-unused',
                'returned-awaiting-parent-END',1000.,1001.,'synthetic service return'))
            with actor(self.boards['Work'].store,self.issuer):
                processing.release(self.store,self.boards,self.cap,self.controller,dict(actual_END=0,evidence=['Synthetic original END0']))
        root='/same-public-release'; prefix=root+'/tools/coordinator-runtime/coordinator_runtime/'
        self.old_release=dict(root=root,pool_control=self.store.execution_pool.pool.control_binding(Path(self.config['execution_pool_routes']).read_bytes()),files={prefix+k:v for k,v in self.old_impl.items()})
        self.new_release=dict(root=root,pool_control=self.store.execution_pool.pool.control_binding(Path(self.config['execution_pool_routes']).read_bytes()),files={prefix+k:v for k,v in self.new_impl.items()})
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        transition=dict(basis=dict(release=self.old_release,tasks=self.config['tasks'],processing=dict(roles={r:dict(original=dict(binding=v['original']['binding'])) for r,v in raw['basis']['roles'].items()})),
                        event_boundary=0,jobs=[],outboxes=[],alert_boundary=0)
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
            ('synthetic-previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.issuer,1000.))
        self.enterContext(patch.object(configuration,'release',return_value=self.new_release))
        self.now=1600.  # All original finite policies elapsed before owner selection.
        self.plan=dict(**{'from':1600.},until=2200.,lease_seconds=300,max_starts=100,max_new_inputs=80,max_windows=6,pause_bytes=90000000)
        self.plan_file=self.area/'plan.json';self.plan_file.write_text(encode(self.plan))
        self.before={t:self.store.rows('SELECT * FROM '+t) for t in ('processing_capabilities','prospective_authorities','events','queue','attempts','processing_source_positions','service_windows','processing_runs','service_runs')}
        self.store.controller=ident()  # New applier, never original collector impersonation.

    def classify(self,task=None,package=None):
        from coordinator_runtime.inputs import input_routes
        while claimed := self.store.claim_classification():
            attempt,message=claimed
            route=task if message['kind']=='board' and task else input_routes(message,self.config)[0]
            collect(self.store,attempt,dict(event_id=message['id'],task=route,package=message.get('package'),reason='Synthetic classifier chooses actual typed route'))
            self.store.commit_classification(attempt)
        self.runtime.receipts()

    def command(self,argv):
        with patch.dict('os.environ',{'CODEX_SESSION_ID':self.issuer}), actor(self.boards['Work'].store,self.issuer):
            return cli.operate(cli.parser().parse_args(argv),self.store)

    def request(self):
        args=['owner-lease-basis',self.cap,'--work-report',self.work,'--board-control',self.control,'--controller',self.controller,
              '--purpose','Synthetic reviewed continuing framework authority','--plan',str(self.plan_file)]
        for module in self.modules:args+=['--module',module]
        basis=self.command(args)
        self.assertEqual(self.store.rows('SELECT * FROM owner_lease_plans'),[])
        self.assertEqual(self.store.rows('SELECT * FROM owner_lease_activations'),[])
        return dict(schema=repair.LEASE_VERSION,basis=basis,plan=self.plan,authority='Synthetic genuine Work selection seam',evidence=['Synthetic independent exact-code review assertion; no actual acceptance'])

    def apply(self,request=None):
        request=self.request() if request is None else request
        path=self.area/'selection.json';path.write_text(encode(request))
        return self.command(['select-owner-lease','--selection',str(path)])

    def test_public_cutoff_continuation_whole_original_and_control_once(self):
        with self.assertRaises(Refusal):self.store.processing.current()
        request=self.request(); receipt=self.apply(request)
        for table,rows in self.before.items():self.assertEqual(self.store.rows('SELECT * FROM '+table),rows,table)
        self.assertEqual(receipt['original_controller'],self.controller)
        self.assertIsNone(receipt['acceptance'])
        self.assertEqual(self.store.event(self.work)['body'],self.producer_result)
        resolution=self.command(['processing-apply-control',self.cap,self.control,'--attempt',self.control_attempt])
        self.assertEqual(resolution,self.command(['processing-apply-control',self.cap,self.control,'--attempt',self.control_attempt]))
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM processing_control_returns')['n'],1)
        proof=resolution['prior']['software_processing'];self.assertEqual(proof['controller'],self.controller)
        self.assertEqual(proof['applier_controller'],self.store.controller);self.assertFalse(proof['native_owner_receipt'])
        self.classify()
        self.assertTrue(self.store.processing.task(self.store.one('SELECT * FROM queue WHERE event=?',(self.work,))))
        old_starts=self.store.one('SELECT starts FROM processing_capabilities')['starts']
        job=self.store.reserve();self.assertEqual(job['task'],'work-proposer')
        attempt=self.store.start_job(job['id'],job['token']);self.assertIsNotNone(attempt)
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities')['starts'],old_starts+1)
        self.boards['Work'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        collect(self.store,attempt,result(category='proposal',summary='Useful bounded new Work analysis; original dissent and debt remain'),tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        self.assertIsNotNone(self.store.finish_job(job['id'],job['token']))
        self.assertEqual(self.store.event(self.input)['body']['original'],self.report)
        self.assertEqual(self.store.rows('SELECT * FROM prospective_authorities'),self.before['prospective_authorities'])
        used=copy.deepcopy(windows.current(self.store));self.now=1900.
        service.admit_input(self.store)
        self.assertEqual(windows.current(self.store),used)
        future=self.post('Reviews','@control',None)
        self.assertGreater(self.store.one('SELECT position FROM processing_source_positions WHERE event=?',(future['id'],))['position'],request['basis']['sources'][1]['position'])
        self.assertEqual([r['ordinal'] for r in self.store.rows('SELECT * FROM owner_lease_activations ORDER BY ordinal')],[1,2])
        self.now=2200.
        with self.assertRaises(Refusal):service.admit_input(self.store)

    def test_refusal_matrix_metadata_before_body_and_no_selection(self):
        mutations=[('events','hold',self.work,'id','held'),('events','hold',self.input,'id','held'),
            ('attempts','collected',self.control_attempt,'id',None),
            ('attempts','collected',self.store.job(self.store.event(self.work)['source_job'])['active_attempt'],'id',None),
            ('processing_capabilities','issuer',self.cap,'id',ident()),
            ('enrollments','grant_id','Work','role',ident()),('processing_capabilities','revoked',self.cap,'id',1600.),
            ('prospective_authorities','revoked',self.epoch['id'],'id',1600.)]
        for table,column,key,idcol,value in mutations:
            old=self.store.one('SELECT '+column+' FROM '+table+' WHERE '+idcol+'=?',(key,))[column]
            self.store.db.execute('UPDATE '+table+' SET '+column+'=? WHERE '+idcol+'=?',(value,key))
            with patch.object(self.store,'event',side_effect=AssertionError('body before guard')):
                with self.assertRaises(Refusal):self.request()
            self.store.db.execute('UPDATE '+table+' SET '+column+'=? WHERE '+idcol+'=?',(old,key))
        request=self.request()
        for changed in [dict(request,authority=''),dict(request,plan={**self.plan,'max_starts':10000}),dict(request,schema=repair.PAIR_VERSION)]:
            with self.assertRaises(Refusal):self.apply(changed)
        self.assertEqual(self.store.rows('SELECT * FROM owner_lease_plans'),[])

    def test_stop_budget_and_original_policies_never_reset(self):
        self.apply();raw=self.store.one('SELECT selection FROM processing_capabilities')['selection']
        self.store.db.execute('UPDATE processing_capabilities SET starts=100 WHERE id=?',(self.cap,))
        with self.assertRaises(Refusal):self.store.processing.reserve('uncreated',self.work,None)
        self.command(['stop-owner-lease',self.cap,'--reason','Synthetic sudden Work stop'])
        with self.assertRaises(Refusal):self.store.processing.current()
        self.assertEqual(self.store.one('SELECT selection FROM processing_capabilities')['selection'],raw)
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities')['starts'],100)
        for table in ('owner_lease_plans','owner_lease_activations','owner_lease_stops'):
            with self.assertRaises(Exception):self.store.db.execute('DELETE FROM '+table)

    def test_owned_wake_future_timer_and_foreign_endpoint_refusal(self):
        self.apply()
        async def exercise():
            dispatcher=SimpleNamespace(wakeup=asyncio.Event())
            wake=ServiceWake(self.store,self.boards,dispatcher);wake.start()
            self.assertEqual(wake.state,'bound');handles=[x[0].fileno() for x in wake.receivers]
            foreign=ServiceWake(self.store,self.boards,dispatcher)
            with self.assertRaises(Refusal):foreign.start()
            self.assertEqual([x[0].fileno() for x in wake.receivers],handles)
            self.now=1900.;wake._expired()
            self.assertEqual(wake.state,'bound');self.assertEqual(wake.until,2200.)
            self.assertEqual([x[0].fileno() for x in wake.receivers],handles)
            self.now=2200.;wake._expired();self.assertEqual(wake.state,'expired');self.assertEqual(wake.receivers,[])
        asyncio.run(exercise())

    def test_changed_source_config_task_custody_and_peer_refuse(self):
        request=self.request()
        with patch.object(configuration,'release',return_value={**self.new_release,'root':'/foreign-release'}):
            with patch.object(self.store,'event',side_effect=AssertionError('source before code guard')):
                with self.assertRaises(Refusal):self.apply(request)
        task=self.config['tasks']['work-proposer'];old=task['authority'];task['authority']='changed task'
        with patch.object(self.store,'event',side_effect=AssertionError('source before config guard')):
            with self.assertRaises(Refusal):self.apply(request)
        task['authority']=old
        peer=ident();self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(peer,self.cap,'owned',1600.))
        with patch.object(self.store,'event',side_effect=AssertionError('source before collector guard')):
            with self.assertRaises(Refusal):self.request()
        self.store.db.execute('DELETE FROM processing_runs WHERE controller=?',(peer,))
        value=self.store.event(self.work);changed=copy.deepcopy(value);changed['report_custody']['collector']='foreign'
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?',(encode(changed),self.work))
        with self.assertRaises(Refusal):self.apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM owner_lease_plans'),[])
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?',(encode(value),self.work))
        self.assertEqual(self.store.event(self.input)['body']['original'],self.report)

    def test_no_lease_and_total_input_window_and_native_effect_bounds(self):
        with self.assertRaises(Refusal):service.admit_input(self.store)
        request=self.request();self.apply(request)
        self.now=1900.;self.store.processing.current()
        self.assertEqual(windows.current(self.store)['number'],1)
        # Fill existing allocation through actual charge API, retaining used debit.
        with self.store.tx():
            for _ in range(self.config['window_service']['max_new_inputs']-windows.current(self.store)['new_inputs']):
                windows.charge(self.store,'events',new_input=True)
        with self.store.tx():windows.charge(self.store,'events',new_input=True)
        self.assertEqual(windows.current(self.store)['number'],2)
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],1)
        self.assertEqual(self.store.one('SELECT new_inputs FROM service_windows WHERE number=1')['new_inputs'],40)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])
        self.assertFalse(prospective.current(self.store,'qa-execution')['policy']['ordinary_effects'])
        self.now=2200.
        with self.assertRaises(Refusal):windows.preflight_input(self.store)
