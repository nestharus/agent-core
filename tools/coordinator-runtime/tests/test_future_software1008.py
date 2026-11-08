"""Owned four-role fiction: real admission/repair/wake/intake controllers.

Only authenticated principals, public release pins and clock/END facts are
fictional seams. No model, provider, live QA, deletion or actual adoption.
"""
import asyncio
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from test_source_continuity688 import Continuity
from test_qa629_repairs import Fixture, actor
from support import collect
from coordinator_runtime import processing, prospective, service, configuration, windows, cli, processing_admission
from coordinator_runtime import report_repair as repair
from coordinator_runtime.contracts import Refusal, Backpressure, digest, encode, ident
from coordinator_runtime.service_wake import ServiceWake


def at(value):
    return datetime.fromisoformat('2026-11-08T'+value+'+00:00').timestamp()


class Future1008(Continuity):
    def configure(self):
        super().configure()
        self.config['limits']['max_bytes'] = 2*1024**3
        self.config['window_service'] = dict(tasks=list(self.config['tasks']),max_new_inputs=40,batch_size=8,max_decisions=100)

    def select(self, service_policy=None):
        service_policy['wake'] = dict(protocol='managed-hint-v1',roles=list(self.config['roles']),until=at('07:43:35'))
        service_policy['admission'].update(until=at('07:43:35'))
        service_policy['legacy_resources']['Reviews']['reviews_report']['expires'] = at('10:44:25')
        service_policy['allocations'] = dict(basis={},target='Original bounded future software',reason='Keep all original custody',
            evidence='Fictional original genuine Work allocation',custody={r:dict(owner=v['owner'],evidence='Original custodian') for r,v in self.config['roles'].items()},
            expires=at('07:43:35'),max_windows=35)
        original = processing.select
        def select(runtime,boards,selection):
            runtime.clock = lambda:at('07:30:00')
            selection['service']['allocations']['basis'] = windows.basis(runtime)
            return original(runtime,boards,selection)
        with patch.object(processing,'select',side_effect=select):
            return Fixture.select(self,service_policy)

    def setUp(self):
        pins=json.loads(Path('/public/production-pins.json').read_text())
        self.bootstrap(self.configure)
        self.store.clock=lambda:at('07:30:00')
        self.issuer=self.config['roles']['Work']['owner']
        self.enterContext(patch.object(processing,'implementation',return_value=pins['original']))
        self.report=dict(reference='fictional-original-QA-report1008',collector=self.issuer,actual_END=0,
            reports=[dict(name='QA',body='Whole fictional QA report and dissent; original duties retained')],
            history='Whole fictional original collector history',method_pin='fictional public reviewed method',
            coverage=dict(status='PARTIAL',unread=['actual native Source']),effects='known-report-only')
        policy=dict(version='reviews-report-v1',authority='Original fictional framework report right',expires=at('10:44:25'),
            task='reviews-integrator',task_sha256=digest(self.config['tasks']['reviews-integrator']),
            reports=[dict(reference=self.report['reference'],sha256=digest(self.report))])
        original=processing.select
        def select(runtime,boards,selection):
            selection['software_admission']=dict(authority='Original fictional QA admission',max_packages=2,
                scopes=dict(fixture=dict(submitters=[self.source_sender],package_prefix='fictional-',
                    task_scopes={'qa-execution':self.scope},evidence='Original fictional QA scope')))
            return original(runtime,boards,selection)
        with patch.object(processing,'select',side_effect=select):
            self.select(dict(max_inflight=4,reviews={},report_tasks=['reviews-integrator'],
                admission=dict(until=at('07:43:35'),pause_bytes=90000000,max_new_inputs=20),
                legacy_resources={'Reviews':dict(original_hold=None,roots=[],unbounded=True,
                    evidence='Original unresolved report custody',reviews_report=policy)}))
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),
            authority='Original fictional prospective authority',expires=at('10:44:25'),processing_capability=self.cap,
            grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))
        # A real reserved/failed original Source job remains held. Its partial
        # CLI transport is an explicit fixture seam, not native terminal proof.
        self.source_event=self.post('Reviews','reviews-proposer',None)
        self.source_job=self.store.reserve();self.assertIsNotNone(self.source_job)
        self.assertEqual(self.source_job['task'],'reviews-proposer')
        source_attempt=self.store.start_job(self.source_job['id'],self.source_job['token'])
        collect(self.store,source_attempt,None,code=6,capture='incomplete',error='Fictional incomplete original Source capture')
        self.assertIsNone(self.store.finish_job(self.source_job['id'],self.source_job['token']))
        self.assertEqual(self.store.job(self.source_job['id'])['state'],'held')
        self.classify()
        self.pending_work=self.post('Work','work-proposer',None)
        self.board_source=self.post('QA','qa-execution','fictional-original-package')
        processing_admission.admit(self.store,self.board_source['id'])
        self.report_id=service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)['event']
        self.classify();self.events=sorted([self.board_source['id'],self.report_id])
        self.controller=self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.controller,self.cap,'owned',self.store.clock()))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.controller,self.cap,'fictional-unused','returned-awaiting-parent-END',self.store.clock(),self.store.clock(),'Fictional service return'))
        with actor(self.boards['Work'].store,self.issuer):
            processing.release(self.store,self.boards,self.cap,self.controller,dict(actual_END=0,evidence=['Fictional original parent END0']))
        self.original_impl=pins['original'];self.new_impl=pins['candidate']
        self.modules=sorted(n for n in self.new_impl if self.new_impl[n] != self.original_impl[n])
        self.assertLessEqual(set(self.modules),repair.SOURCE_MODULES)
        self.assertEqual(self.new_impl['reviews.py'],self.original_impl['reviews.py'])
        root='/fictional-same-installed-public-release';prefix=root+'/tools/coordinator-runtime/coordinator_runtime/'
        self.old_release=dict(root=root,pool_control=self.store.execution_pool.pool.control_binding(Path(self.config['execution_pool_routes']).read_bytes()),
            files={prefix+n:h for n,h in self.original_impl.items()})
        self.new_release=copy.deepcopy(self.old_release)
        for name in self.modules:self.new_release['files'][prefix+name]=self.new_impl[name]
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        transition=dict(basis=dict(release=self.old_release,tasks=self.config['tasks'],
            processing=dict(roles={r:dict(original=dict(binding=v['original']['binding'])) for r,v in raw['basis']['roles'].items()})),
            event_boundary=0,jobs=[],outboxes=[],alert_boundary=0)
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
            ('fictional-previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.issuer,self.store.clock()))
        self.enterContext(patch.object(configuration,'release',return_value=self.new_release))
        self.enterContext(patch.object(processing,'implementation',return_value=self.new_impl))
        # Actual source-v1 APIs establish the exact reviewed pins first. No
        # historical producer/control pair exists or is constructed.
        self.source_request = Continuity.request(self)
        self.source_receipt = Continuity.apply(self,self.source_request)
        # Original 34 charged windows: real charge/append APIs, not rewritten
        # authority or new journal. Retain every used row and original hash.
        with self.store.tx():
            for _ in range(34*40+1):
                windows.charge(self.store,'events',new_input=True)
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],34)
        self.now = at('08:15:00'); self.store.clock = lambda:self.now
        self.store.controller = ident()
        self.plan = dict(**{'from':self.now},until=at('10:30:00'),lease_seconds=1800,max_starts=512,
            max_new_inputs=8192,max_windows=35,pause_bytes=1056964608)
        self.plan_file=self.area/'future-plan.json';self.plan_file.write_text(encode(self.plan))
        self.before=self.untouched()
        self.windows_before=self.store.rows('SELECT * FROM service_windows')
        self.allocations_before=self.store.rows('SELECT * FROM service_window_allocations')

    def command(self,argv,issuer=None):
        principal=issuer or self.issuer
        with patch.dict('os.environ',{'CODEX_SESSION_ID':principal}), actor(self.boards['Work'].store,principal):
            return cli.operate(cli.parser().parse_args(argv),self.store)

    def future_request(self):
        selected=self.command(['future-software-basis',self.cap,'--controller',self.controller,
            '--purpose','Fictional explicit finite future software; same original QA and debts','--plan',str(self.plan_file)])
        self.assertEqual(self.store.rows('SELECT * FROM future_software_plans_v1'),[])
        return dict(schema=repair.SOFTWARE_VERSION,basis=selected,plan=self.plan,
            authority='Fictional genuine Work explicit future software decision',evidence=['Fictional independent public source review; no acceptance claim'])

    def future_apply(self,request=None):
        request=self.future_request() if request is None else request
        p=self.area/'future-selection.json';p.write_text(encode(request))
        return self.command(['select-future-software','--selection',str(p)])

    def test_current_source_v1_then_finite_future_wakes_and_new_intake(self):
        with self.assertRaises(Backpressure):service.admit_input(self.store)
        self.assertEqual(repair.source_receipt(self.cap,self.source_request['basis']),self.source_receipt)
        self.assertIsNone(repair.lease_record(self.store,self.cap))
        self.assertEqual(self.store.rows('SELECT * FROM processing_controls'),[])
        selected=self.future_request();receipt=self.future_apply(selected)
        self.assertEqual(self.before,self.untouched())
        self.assertEqual(self.windows_before,self.store.rows('SELECT * FROM service_windows'))
        self.assertEqual(receipt['source_receipt_hash'],digest(self.source_request))
        self.assertEqual(receipt['plan'],self.plan)
        self.assertFalse(receipt['native_rights_renewed'])
        self.assertIsNone(receipt['acceptance'])
        service.admit_input(self.store)
        raw=json.loads(self.before['processing_capabilities'][0]['selection'])
        scope=raw['software_admission']['scopes']['fixture']
        resolved=processing_admission.resolved(self.store,self.board_source['package'],'fixture',digest(scope))
        self.assertEqual(digest(resolved),self.before['processing_admission_resolutions'][0]['admission_hash'])
        async def wakes():
            dispatcher=SimpleNamespace(wakeup=asyncio.Event())
            wake=ServiceWake(self.store,self.boards,dispatcher)
            try:
                wake.start();self.assertEqual(wake.state,'bound')
                self.assertEqual(set(wake.roles),{'Work','Reviews','QA','Branch'})
                self.assertEqual(len(wake.receivers),4)
                handles=[x[0].fileno() for x in wake.receivers]
                self.now=at('08:45:00');wake._expired()
                self.assertEqual(wake.state,'bound');self.assertEqual(wake.until,at('09:15:00'))
                self.assertEqual([x[0].fileno() for x in wake.receivers],handles)
                # Actual new managed Board post/scan/ingest/classification path.
                fresh=self.post('Work','work-proposer',None)
                self.assertGreater(self.store.one('SELECT position FROM processing_source_positions WHERE event=?',(fresh['id'],))['position'],
                    selected['basis']['counters']['new_inputs'])
                self.assertIsNotNone(self.store.one('SELECT * FROM queue WHERE event=?',(fresh['id'],)))
                # Exercise the existing producer's real managed hint path and
                # intake for all four recipients in the owned Board fiction.
                for role,task,package in [('Work','work-proposer',None),('Reviews','reviews-proposer',None),
                        ('QA','qa-execution','fictional-next-QA-package'),('Branch','branch-proposer','fictional-next-Branch-package')]:
                    event=self.post(role,task,package)
                    receiver,board,identity,helper=next(row for row in wake.receivers if row[1].role==role)
                    prior=wake.hints
                    with board.opened() as conn:helper.signal_post(conn,event['post'])
                    await asyncio.sleep(0);await asyncio.sleep(0)
                    self.assertGreater(wake.hints,prior)
                    self.assertIsNotNone(self.store.one('SELECT * FROM queue WHERE event=?',(event['id'],)))
                # Original pending sources, QA admission and source births survive.
                for table in ('processing_admissions','processing_admission_resolutions','admissions'):
                    self.assertEqual(self.store.rows('SELECT * FROM '+table),self.before[table])
                for row in self.before['queue']:
                    self.assertEqual(self.store.one('SELECT * FROM queue WHERE id=?',(row['id'],)),row)
                for table,key in (('jobs','id'),('attempts','id'),('processing_source_positions','event')):
                    for row in self.before[table]:
                        self.assertEqual(self.store.one('SELECT * FROM '+table+' WHERE '+key+'=?',(row[key],)),row)
                self.assertEqual(self.store.rows('SELECT * FROM service_window_allocations'),self.allocations_before)
                self.now=at('10:30:00');wake._expired()
                self.assertEqual(wake.state,'expired');self.assertEqual(wake.receivers,[])
                with self.assertRaises(Refusal):service.admit_input(self.store)
            finally:wake.close()
        asyncio.run(wakes())
        self.assertEqual(self.store.one('SELECT selection FROM processing_capabilities')['selection'],self.before['processing_capabilities'][0]['selection'])
        self.assertEqual(self.store.rows('SELECT * FROM prospective_authorities'),self.before['prospective_authorities'])

    def test_fresh_basis_refuses_changed_counters_or_pending_holders(self):
        request=self.future_request()
        with self.store.tx():
            self.store.db.execute('UPDATE processing_capabilities SET starts=starts+1 WHERE id=?',(self.cap,))
        with self.assertRaisesRegex(Refusal,'basis changed'):self.future_apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM future_software_plans_v1'),[])
        request=self.future_request()
        self.store.db.execute("UPDATE queue SET job='fictional-pending-holder',state='reserved' WHERE event=?",(self.board_source['id'],))
        with self.assertRaisesRegex(Refusal,'basis changed'):self.future_apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM future_software_plans_v1'),[])

    def test_wrong_owner_cap_config_source_epoch_grant_running_and_uncollected_refuse(self):
        with self.assertRaises(Refusal):self.command(['future-software-status',self.cap],ident())
        changes=[('processing_capabilities','issuer',self.cap,'id',ident()),
            ('processing_capabilities','revoked',self.cap,'id',self.now),
            ('prospective_authorities','revoked',self.epoch['id'],'id',self.now),
            ('enrollments','grant_id','QA','role',ident()),
            ('processing_runs','state',self.controller,'controller','owned'),
            ('service_runs','state',self.controller,'controller','serving'),
            ('attempts','collected',self.before['attempts'][0]['id'],'id',None)]
        for table,column,key,idcol,value in changes:
            with self.subTest(table=table,column=column), actor(self.boards['Work'].store,self.issuer), self.store.tx():
                self.store.db.execute('SAVEPOINT fault1008')
                try:
                    self.store.db.execute('UPDATE '+table+' SET '+column+'=? WHERE '+idcol+'=?',(value,key))
                    with patch.object(self.store,'event',side_effect=AssertionError('source body before metadata guard')):
                        with self.assertRaises(Refusal):repair.software_basis(self.store,self.boards,self.cap,self.controller,self.issuer,'Fictional guarded future basis',self.plan)
                finally:
                    self.store.db.execute('ROLLBACK TO fault1008');self.store.db.execute('RELEASE fault1008')
        with patch.object(configuration,'release',return_value={**self.new_release,'root':'/wrong-public-source'}):
            with self.assertRaises(Refusal):self.future_request()
        self.config['actor']='changed-config'
        with self.assertRaises(Refusal):self.future_request()

    def test_typed_legacy_paths_and_ordinary_epoch_are_unchanged(self):
        request=self.future_request();self.future_apply(request)
        for consumer in (repair.apply_source,repair.apply_pair,repair.apply_lease,repair.apply_amendment):
            with self.assertRaises(Refusal):consumer(self.store,self.boards,self.issuer,request)
        self.assertIsNone(repair.lease_record(self.store,self.cap))
        with self.assertRaises(Refusal):self.command(['owner-lease-status',self.cap])
        with actor(self.boards['Work'].store,self.issuer), self.assertRaises(Refusal):
            repair.lease_metadata(self.store,self.boards,self.cap,'absent-report','absent-control',self.controller,
                self.issuer,sorted(repair.LEASE_MODULES),'Fictional historical path',self.plan)
        with actor(self.boards['Work'].store,self.issuer), self.assertRaises(Refusal):repair.stop_lease(self.store,self.boards,self.issuer,self.cap,'No old lease exists')
        for version in (repair.SOURCE_VERSION,repair.PAIR_VERSION,repair.LEASE_VERSION):
            with self.assertRaises(Refusal):repair.apply_software(self.store,self.boards,self.issuer,dict(schema=version))
        # New software authority never extends the ordinary epoch. At the exact
        # original 10:44:25 expiry even framework prospective permission refuses.
        self.now=at('10:44:25')
        with self.assertRaises(Refusal):prospective.current(self.store,'qa-execution',ordinary_effects=True)
        self.assertEqual(json.loads(self.store.one('SELECT selection FROM prospective_authorities')['selection'])['expires'],at('10:44:25'))
        self.assertEqual(self.store.rows('SELECT * FROM prospective_authorities'),self.before['prospective_authorities'])

    def test_start_input_window_and_time_exhaustion_without_resets(self):
        self.future_apply()
        with self.store.tx():
            for _ in range(40-windows.current(self.store)['new_inputs']):windows.charge(self.store,'events',new_input=True)
            windows.charge(self.store,'events',new_input=True)
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],35)
        self.assertEqual(self.store.rows('SELECT * FROM service_windows WHERE number<35'),self.windows_before[:34])
        self.store.db.execute('UPDATE processing_capabilities SET starts=512 WHERE id=?',(self.cap,))
        self.store.processing.current()  # Read/old obligations remain available.
        attempts=self.store.rows('SELECT * FROM attempts')
        with self.store.tx(),self.assertRaises(Refusal):
            self.store._attempt('input-control',self.board_source['id'],None,{},'.codex')
        self.assertEqual(self.store.rows('SELECT * FROM attempts'),attempts)
        with self.store.tx():
            for _ in range(40-windows.current(self.store)['new_inputs']):windows.charge(self.store,'events',new_input=True)
        with self.assertRaises(Refusal):windows.preflight_input(self.store)
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],35)
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities')['starts'],512)

    def test_original_birth_boundary_input_exhaustion_and_byte_pause(self):
        raw=json.loads(self.before['processing_capabilities'][0]['selection'])
        count=self.store.one('SELECT COUNT(*) n FROM processing_source_positions WHERE position>?',(raw['basis']['event_boundary'],))['n']
        self.plan['max_new_inputs']=count+1;self.plan_file.write_text(encode(self.plan))
        self.future_apply()
        usage=self.store.usage()
        # Synthetic pressure value is the resource seam; the actual admission
        # controller must refuse before another Board scan or source allocation.
        with patch.object(self.store,'usage',return_value={**usage,'bytes':self.plan['pause_bytes']}):
            with self.assertRaises(Refusal):service.admit_input(self.store)
        self.post('Work','work-proposer',None)
        with self.assertRaises(Backpressure):service.admit_input(self.store)
        positions=self.store.rows('SELECT * FROM processing_source_positions')
        with self.assertRaises(Backpressure):
            service.ingest_report(self.store,self.issuer,'reviews-integrator',{**self.report,'reference':'another-future-report'})
        self.assertEqual(self.store.rows('SELECT * FROM processing_source_positions'),positions)
        for row in self.before['processing_source_positions']:
            self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(row['event'],)),row)
        self.assertEqual(self.store.rows('SELECT * FROM processing_admission_resolutions'),self.before['processing_admission_resolutions'])

    def test_current_identity_guards_and_hot_pool_membership_remain_effective(self):
        with self.assertRaises(Refusal):
            self.command(['future-software-basis',ident(),'--controller',self.controller,'--purpose','Wrong cap','--plan',str(self.plan_file)])
        self.future_apply()
        routes=Path(self.config['execution_pool_routes']);before=routes.read_bytes()
        self.assertEqual(set(self.store.execution_pool.status()['enabled']),{'.codex','.codex2','.codex3','.codex4','.codex5'})
        routes.write_bytes(self.store.execution_pool.pool.__class__.control_binding.__globals__['replace_membership'](before,['.codex4']))
        self.store.processing.current()
        self.assertEqual(self.store.execution_pool.allocate()['profile'],'.codex4')
        routes.write_bytes(before)
        self.assertEqual(set(self.store.execution_pool.status()['enabled']),{'.codex','.codex2','.codex3','.codex4','.codex5'})
        for sql,args in [
            ('UPDATE enrollments SET grant_id=? WHERE role=?',(ident(),'QA')),
            ('UPDATE enrollments SET owner=? WHERE role=?',(ident(),'QA')),
            ('UPDATE enrollments SET intake=1 WHERE role=?',('QA',)),
            ('UPDATE enrollments SET cutover=cutover+1 WHERE role=?',('QA',)),
            ('UPDATE prospective_authorities SET revoked=? WHERE id=?',(self.now,self.epoch['id'])),
            ('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.now,self.cap)),
        ]:
            self.store.db.execute('SAVEPOINT current1008')
            try:
                self.store.db.execute(sql,args)
                with self.assertRaises(Refusal):self.store.processing.current()
            finally:
                self.store.db.execute('ROLLBACK TO current1008');self.store.db.execute('RELEASE current1008')
        with patch.object(processing,'implementation',return_value={**self.new_impl,'report_repair.py':'wrong-public-pin'}):
            with self.assertRaises(Refusal):self.store.processing.current()
        with patch.object(configuration,'release',return_value={**self.new_release,'root':'/wrong-release'}):
            with self.assertRaises(Refusal):self.store.processing.current()

    def test_plan_limits_stop_and_no_default_or_receipt_conversion(self):
        request=self.future_request()
        for field,value in [('max_starts',request['basis']['counters']['starts']),('max_new_inputs',2),
                ('max_windows',34),('max_windows',36),('pause_bytes',4096),('until',at('10:44:26')),
                ('from',self.now-61),('until',self.now),('lease_seconds',3601)]:
            with self.subTest(field=field,value=value):
                changed=copy.deepcopy(request);changed['plan'][field]=value
                with self.assertRaises(Refusal):self.future_apply(changed)
        self.future_apply(request)
        self.command(['stop-future-software',self.cap,'--reason','Fictional genuine Work stops future intake'])
        with self.assertRaises(Refusal):service.admit_input(self.store)
        self.assertEqual(self.store.rows('SELECT * FROM processing_capabilities'),self.before['processing_capabilities'])
        self.assertEqual(self.store.rows('SELECT * FROM processing_admissions'),self.before['processing_admissions'])


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(Future1008(n) for n in Future1008.__dict__ if n.startswith('test_'))
