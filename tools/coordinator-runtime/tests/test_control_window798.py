"""Owned synthetic actors, native/wire fields and clock; real protocol guards."""
import copy, json, os, subprocess, sys, time
from pathlib import Path
from unittest.mock import patch
from test_authentic_control794 import Authentic794
from coordinator_runtime import processing, report_repair as repair, windows
from coordinator_runtime.contracts import Refusal, Backpressure, digest, encode

class Window798(Authentic794):
    def configure(self):
        super().configure()
        self.config['limits'].update(max_bytes=1073741824,max_events=8192,max_attempts=16384,max_jobs=4096,max_outboxes=8192,max_files=16384,max_alerts=4096,max_alert_debt=8192)
        self.config['window_service']=dict(batch_size=8,max_decisions=16,max_new_inputs=40,tasks=list(self.config['tasks']))
        Path(self.config['operator_config']).write_text(encode(self.config))

    def bootstrap(self, configure):
        super().bootstrap(configure)
        self.store.db.execute('UPDATE service_windows SET number=28,used=?,new_inputs=13',
            (encode(dict(attempts=38,decisions=6,events=18,jobs=2,outboxes=2)),))

    def setUp(self):
        if os.environ.get('PHASE794')=='consume':
            return super().setUp()
        original=processing.select
        def select(runtime,boards,request):
            request['service'].update(admission=dict(until=1600.,pause_bytes=805306368,max_new_inputs=256),
                wake=dict(protocol='managed-hint-v1',roles=list(self.config['roles']),until=1600.),
                allocations=dict(basis=windows.basis(runtime),target='Owned synthetic future coordination',
                    reason='Actual-policy shape qualification',evidence='Synthetic closed fixture',
                    custody={r:dict(owner=v['owner'],evidence='Original fixture custodian') for r,v in self.config['roles'].items()},
                    expires=1600.,max_windows=31))
            return original(runtime,boards,request)
        with patch.object(processing,'select',side_effect=select):super().setUp()
        # Synthetic historical charge, recorded by the old generation only.
        self.store.db.execute('UPDATE processing_capabilities SET starts=starts+40 WHERE id=?',(self.cap,))

    def charged(self):
        return dict(cap=self.store.one('SELECT * FROM processing_capabilities WHERE id=?',(self.cap,)),
            windows=self.store.rows('SELECT * FROM service_windows ORDER BY number'),
            allocations=self.store.rows('SELECT * FROM service_window_allocations ORDER BY number'),
            epoch=self.store.one('SELECT * FROM prospective_authorities WHERE id=?',(self.epoch['id'],)),
            sources=self.store.rows('SELECT * FROM processing_source_positions ORDER BY position'),
            original_bytes=self.store.rows('SELECT id,hash,payload FROM events ORDER BY id'),
            attempts=self.store.rows('SELECT * FROM attempts ORDER BY id'))

    def test_continuing_policy_conservation_and_deadlines(self):
        before=self.charged();self.assertGreaterEqual(before['cap']['starts'],40)
        self.assertEqual(before['windows'][0]['number'],28)
        self.assertGreaterEqual(before['windows'][0]['new_inputs'],13)
        policy=json.loads(before['cap']['selection'])['service']
        self.assertEqual(policy['allocations']['max_windows'],31)
        self.assertEqual(policy['allocations']['basis']['allocation']['used'],encode(dict(attempts=38,decisions=6,events=18,jobs=2,outboxes=2)))
        request=self.request794();self.assertEqual(before,self.charged())
        self.store.clock=lambda:1599.999
        self.basis794()  # Fresh authentic basis immediately before all original deadlines.
        for now in [1600.,1601.]:
            self.store.clock=lambda:now;snap=self.snapshot794()
            with patch.object(self.store,'event',side_effect=AssertionError('expired body')),self.assertRaisesRegex(Refusal,'finite.*expired|finite owner plan|lease plan exhausted'):
                self.basis794()
            self.assertEqual(snap,self.snapshot794())
        self.store.clock=lambda:1000.
        self.apply794(request);self.assertEqual(before,self.charged())
        self.store.clock=lambda:1600.;snap=self.snapshot794()
        with patch.object(self.store,'event',side_effect=AssertionError('expired selected body')),self.assertRaisesRegex(Refusal,'finite.*expired|finite owner plan|lease plan exhausted'):
            processing.apply_control(self.store,self.control_event,self.control_attempt)
        self.assertEqual(snap,self.snapshot794())
        self.store.clock=lambda:1000.

    def test_near_admission_and_allocation_exhaustion(self):
        from coordinator_runtime import service
        self.apply794(self.request794())
        original=self.charged();anchor=copy.deepcopy(original['windows'][0])
        self.assertGreater(service.admit_input(self.store),0)
        # Charge all 31 delegated successor windows with the actual accounting API.
        for ordinal in range(31):
            row=windows.current(self.store)
            remaining=40-row['new_inputs']
            with self.store.tx():
                for _ in range(remaining):windows.charge(self.store,'events',new_input=True)
                windows.charge(self.store,'events',new_input=True)
            self.assertEqual(windows.current(self.store)['number'],29+ordinal)
        row=windows.current(self.store)
        with self.store.tx():
            for _ in range(40-row['new_inputs']):windows.charge(self.store,'events',new_input=True)
        before=self.snapshot794()
        with self.assertRaises(Backpressure),self.store.tx():windows.charge(self.store,'events',new_input=True)
        self.assertEqual(before,self.snapshot794())
        self.assertEqual(len(self.store.rows('SELECT * FROM service_window_allocations')),31)
        oldest=self.store.one('SELECT * FROM service_windows WHERE number=28')
        self.assertEqual(oldest['new_inputs'],40)
        for k in ['configuration','actor','receipt','created']:self.assertEqual(oldest[k],anchor[k])
        self.assertEqual(self.store.one('SELECT starts FROM processing_capabilities WHERE id=?',(self.cap,))['starts'],original['cap']['starts'])
        self.assertEqual(self.store.rows('SELECT * FROM processing_source_positions ORDER BY position'),original['sources'])
        self.store.clock=lambda:1599.999
        repair.pair_finite(self.store,json.loads(original['cap']['selection']))
        self.store.clock=lambda:1600.
        with self.assertRaises(Refusal if os.environ.get('QUALIFICATION801_OWNER_LEASE') else Backpressure):service.admit_input(self.store)
        with self.assertRaises(Refusal),self.store.tx():windows.allocation(self.store,'events',new_input=True)

    def cli798(self,*args,session=None,now=1000.,expected=0):
        env=dict(os.environ,CODEX_SESSION_ID=session or self.issuer)
        code='import time,sys; time.time=lambda:'+repr(now)+'; from coordinator_runtime.cli import main; sys.exit(main())'
        p=subprocess.run([sys.executable,'-B','-c',code,'--config',self.config['operator_config'],*args],env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        self.assertLess(len(p.stdout)+len(p.stderr),4*1024*1024)
        (self.area/('cli-'+str(time.time_ns())+'.json')).write_text(encode(dict(args=args,END=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())))
        self.assertEqual(p.returncode,expected,p.stdout.decode()+p.stderr.decode())
        return json.loads(p.stdout)

    def test_public_cli_basis_select_apply_two_anchors(self):
        before=self.charged();original=self.store.attempt(self.control_attempt)
        args=['same-authority-report-control-repair-basis',self.cap,'--work-report',self.work_event,
            '--board-control',self.control_event,'--controller',self.controller,'--purpose','Synthetic public CLI qualification']
        for module in self.modules:args+=['--module',module]
        lease=bool(os.environ.get('QUALIFICATION801_OWNER_LEASE'))
        if lease:
            plan=self.area/'cli-plan801.json';plan.write_text(encode(self.lease_plan801()))
            args[0]='owner-lease-basis';args+=['--plan',str(plan)]
        basis=self.cli798(*args);self.assertEqual(before,self.charged())
        self.assertEqual([a['kind'] for a in basis['sources']],['work-report','board-control'])
        selection=self.area/'cli-selection.json';selection.write_text(encode(dict(schema=repair.PAIR_VERSION,basis=basis,
            authority='Synthetic fixture Work',evidence=['Synthetic independent source assertion'])))
        if lease:
            request=json.loads(selection.read_text());request.update(schema=repair.LEASE_VERSION,plan=self.lease_plan801());selection.write_text(encode(request))
        self.cli798('select-owner-lease' if lease else 'select-same-authority-report-control-repair','--selection',str(selection))
        self.assertEqual(before,self.charged())
        denied=self.cli798('processing-apply-control',self.cap,self.control_event,'--attempt',self.control_attempt,now=1600.,expected=2)
        self.assertIn('lease plan exhausted' if lease else 'finite',denied['error'])
        if not lease:self.assertIn('expired',denied['error'])
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])
        self.assertEqual(before,self.charged())
        resolution=self.cli798('processing-apply-control',self.cap,self.control_event,'--attempt',self.control_attempt,now=1599.999)
        self.assertIsNone(resolution['receipt']['task'])
        self.assertEqual(self.store.attempt(self.control_attempt),original)
        self.assertEqual(resolution['prior']['software_processing']['controller'],self.controller)
        self.assertNotEqual(resolution['prior']['software_processing']['applier_controller'],self.controller)
        self.assertEqual(self.cli798('processing-apply-control',self.cap,self.control_event,'--attempt',self.control_attempt),resolution)
        self.assertEqual(len(self.store.rows('SELECT * FROM processing_control_returns')),1)
        child=self.store.event(self.store.one('SELECT response FROM processing_control_returns')['response'])
        self.assertEqual(child['body']['actual_worker_return'],json.loads(original['result']))
        after=self.charged()
        self.assertEqual(before['cap'],after['cap'])
        self.assertEqual(before['epoch'],after['epoch'])
        for key in ['original_bytes','attempts','sources']:
            for row in before[key]:self.assertIn(row,after[key])
        self.assertEqual(before['allocations'],after['allocations'])
        for prior,current in zip(before['windows'],after['windows']):
            self.assertEqual(prior['number'],current['number'])
            self.assertGreaterEqual(current['new_inputs'],prior['new_inputs'])
            for key,value in json.loads(prior['used']).items():self.assertGreaterEqual(json.loads(current['used'])[key],value)

    def test_fresh_basis_rejects_bad_upstream_before_body(self):
        cases=[('jobs','role','QA','id',self.producer),('jobs','controller','wrong','id',self.producer),
            ('attempts','collected',None,'id',self.producer_attempt),
            ('events','hold','held','id',self.members[0]),
            ('enrollments','grant_id','wrong','role','Work'),
            ('jobs','members','[]','id',self.producer),
            ('events','role','QA','id',self.members[0])]
        for table,column,value,key,identity in cases:
            with self.subTest(table=table,column=column):
                old=self.store.one(f'SELECT {column} FROM {table} WHERE {key}=?',(identity,))[column]
                try:
                    self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(value,identity));before=self.snapshot794()
                    with patch.object(self.store,'event',side_effect=AssertionError('bad source body')),self.assertRaises(Refusal):self.basis794()
                    self.assertEqual(before,self.snapshot794())
                finally:self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(old,identity))
        self.store.clock=lambda:1600.
        with patch.object(self.store,'event',side_effect=AssertionError('expired source body')),self.assertRaises(Refusal):self.basis794()

    def test_midgroup_queue_and_hash_refuse_before_control_body(self):
        request=self.request794()
        for table,column,value,key in [('queue','task','@unresolved','event'),('events','hash','changed','id')]:
            actual=self.store.event;actual_attempt=self.store.attempt;reads=[];before=self.snapshot794()
            def read(event):
                reads.append(event)
                if event==self.control_event:raise AssertionError('changed control body')
                result=actual(event)
                if event==self.work_event:self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(value,self.control_event))
                return result
            def attempt(identity):
                if identity==self.control_attempt:raise AssertionError('changed control result body')
                return actual_attempt(identity)
            with self.subTest(column=column),patch.object(self.store,'event',side_effect=read),patch.object(self.store,'attempt',side_effect=attempt),self.assertRaises(Refusal):self.apply794(request)
            self.assertEqual(before,self.snapshot794());self.assertNotIn(self.control_event,reads)
