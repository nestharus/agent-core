"""Synthetic identities/clock/wire answers; all production authority guards real.

The immutable old pin manifest models the released historical code at the same
location. No live owner, source, capture, service or adoption is represented.
"""
import copy, hashlib, json, os, time, unittest
from pathlib import Path
from unittest.mock import patch
from test_report_transport739 import ReportTransport
from test_qa629_repairs import actor
from support import collect
from coordinator_runtime import configuration, processing, prospective, report_repair as repair
from coordinator_runtime.contracts import Refusal, SOL, digest, encode

class Authentic794(ReportTransport):
    def bootstrap(self, configure):
        super().bootstrap(configure)
        self.store.clock=lambda:1000.

    def configure(self):
        super().configure()
        root=Path('/src'); directory=root/'tools/coordinator-runtime'
        self.config.update(operator_cli=str(directory/'coordinator'),operator_config=str(self.area/'operator.json'),
            control_receive=dict(mode='cooperative',instructions=str(directory/'templates/coordinator-receive.md')))
        Path(self.config['operator_config']).write_text(encode(self.config))

    def setUp(self):
        history=Path('/fixtures')/(self._testMethodName+'.history.json')
        if os.environ.get('PHASE794')=='consume':
            state=json.loads(history.read_text())
            for name,value in state.items():setattr(self,name,Path(value) if name in {'area','board_path'} else value)
            from coordinator_runtime.store import Store
            from coordinator_runtime.dispatcher import Dispatcher
            self.store=Store(self.config,clock=lambda:1000.);self.addCleanup(self.store.close)
            self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
            for b in self.boards.values():b.runtime=self.store
            self.store.processing=processing.Access(self.store,self.cap,self.boards)
            self.runtime=Dispatcher(self.store,models=object(),boards=self.boards)
            old=json.loads(Path('/src/old-implementation794.json').read_text());current=processing.implementation()
            self.modules=sorted(n for n in old if old[n]!=current[n]);self.assertEqual(set(self.modules),repair.LEASE_MODULES if os.environ.get("QUALIFICATION801_OWNER_LEASE") else repair.PAIR_MODULES)
            return
        with patch.object(time,'time',return_value=1000.):
            super().setUp()
        job, attempt, members=self.start([self.reports[0]])
        self.producer=job['id']; self.producer_attempt=attempt; self.members=members
        self.response=self.finish(job,attempt,self.answer(job))
        self.work_event=self.response['id']; self.classify()
        # A real Board source, classified to @control by the collected wire answer.
        board=self.boards['Reviews']
        args=board.store.parser().parse_args(['open','--session',self.source_sender,'--topic','fixture',
            '--kind','finding','--text','Whole fictional Board status; original duties remain',
            '--to',self.config['roles']['Reviews']['owner'],'--title','Fictional control','--no-push'])
        with board.store.database(str(self.board_path)) as conn, actor(board.store,self.source_sender):
            board.store.open_thread(conn,args)
        message=board.scan(self.store)[0]; self.store.ingest(message,cursor=message['post'])
        while claimed:=self.store.claim_classification():
            key,event=claimed
            collect(self.store,key,dict(event_id=event['id'],task='@control',package=None,reason='Fictional control status'))
            self.store.commit_classification(key)
        self.runtime.receipts(); self.control_event=message['id']
        with self.store.tx():
            key=self.store._attempt('input-control',self.control_event,None,SOL,'.codex')
            self.store.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',(self.control_event,self.cap,key,digest(message)))
        receipt=dict(source_hash=digest(message),mode='control',task='@control',package=None,related_event=None,related_job=None,
            reason='Whole original fictional control decision',evidence=['Original status remains attributed'],
            remaining_obligations=['v4 UNKNOWN','v5 held','Work430 UNKNOWN','unpublished7','outbox/effect/privacy/custody/retention duties'])
        self.control_attempt=key
        collect(self.store,key,dict(semantic='DONE',summary='Fictional control only',decision_json=json.dumps(receipt,indent=2)),
            tool_completion=dict(complete=True,items=[],nonzero_completions=[],unknown_types=[]))
        self.controller=self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.controller,self.cap,'owned',1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',(self.controller,self.cap,'fictional-unused','returned-awaiting-parent-END',1000.,1001.,'fictional return'))
        with actor(self.boards['Work'].store,self.issuer):
            processing.release(self.store,self.boards,self.cap,self.controller,dict(actual_END=0,evidence=['SYNTHETIC parent END; no actual operational proof']))
        # The old generation records its actual source pins before candidate startup.
        selection=json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.cap,))['selection'])
        before=configuration.release(self.store,self.config)
        transition=dict(basis=dict(release=before,tasks=list(self.config['tasks']),processing=dict(roles={
            r:dict(original=dict(binding=s['original']['binding'])) for r,s in selection['basis']['roles'].items()})),
            event_boundary=0,jobs=[],outboxes=[],alert_boundary=0)
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
            ('fictional-previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.issuer,1000.))

        fields=['config','area','board_path','methods','source_sender','issuer','cap','epoch','reports','producer','producer_attempt','members','response','work_event','control_event','control_attempt','controller']
        history.write_text(json.dumps({n:str(getattr(self,n)) if n in {'area','board_path'} else getattr(self,n) for n in fields}))

    def lease_plan801(self):
        return dict(**{'from':self.store.clock()},until=1600.,lease_seconds=600,
                    max_starts=100,max_new_inputs=256,max_windows=31,pause_bytes=805306368)

    def basis794(self):
        if os.environ.get('QUALIFICATION801_OWNER_LEASE'):
            with actor(self.boards['Work'].store,self.issuer),configuration.stopped(self.store),self.store.tx():
                return repair.lease_basis(self.store,self.boards,self.cap,self.work_event,self.control_event,self.controller,self.issuer,
                    self.modules,'Fictional independent final lease source qualification',self.lease_plan801())
        with actor(self.boards['Work'].store,self.issuer),configuration.stopped(self.store),self.store.tx():
            return repair.pair_basis(self.store,self.boards,self.cap,self.work_event,self.control_event,self.controller,self.issuer,
                self.modules,'Fictional independent exact source qualification')

    def request794(self):
        if os.environ.get('QUALIFICATION801_OWNER_LEASE'):
            return dict(schema=repair.LEASE_VERSION,basis=self.basis794(),plan=self.lease_plan801(),
                authority='SYNTHETIC Work finite plan',evidence=['Fixture exact final tree assertion'])
        return dict(schema=repair.PAIR_VERSION,basis=self.basis794(),authority='SYNTHETIC Work selection',evidence=['Fixture review assertion; no actual adoption approval'])

    def apply794(self, request):
        with actor(self.boards['Work'].store,self.issuer):
            apply=repair.apply_lease if os.environ.get('QUALIFICATION801_OWNER_LEASE') else repair.apply_pair
            return apply(self.store,self.boards,self.issuer,request)

    def snapshot794(self):
        return '\n'.join(self.store.db.iterdump())

    def test_positive_actual_pair_and_distinct_applier(self):
        before=self.snapshot794(); raw=self.store.attempt(self.control_attempt); producer=self.store.attempt(self.producer_attempt)
        request=self.request794(); self.assertEqual(before,self.snapshot794())
        self.apply794(request); self.store.processing.current()
        self.assertEqual(self.apply794(request),repair.pair_receipt(self.cap,request['basis']))
        self.assertIsNone(self.store.one('SELECT job FROM queue WHERE event=?',(self.work_event,))['job'])
        self.assertTrue(self.store.processing.task(self.store.one('SELECT * FROM queue WHERE event=?',(self.work_event,))))
        from coordinator_runtime.store import Store
        other=Store(self.config,clock=lambda:1000.); self.addCleanup(other.close)
        other.processing=processing.Access(other,self.cap,self.boards)
        self.assertNotEqual(other.controller,self.controller)
        resolution=processing.apply_control(other,self.control_event,self.control_attempt)
        self.assertIsNone(resolution['receipt']['task'])
        self.assertEqual(resolution['receipt']['remaining_obligations'],json.loads(json.loads(raw['result'])['decision_json'])['remaining_obligations'])
        proof=resolution['prior']['software_processing']; self.assertEqual(proof['controller'],self.controller)
        self.assertEqual(proof['applier_controller'],other.controller); self.assertFalse(proof['native_owner_receipt'])
        self.assertEqual(other.attempt(self.control_attempt),raw); self.assertEqual(other.attempt(self.producer_attempt),producer)
        returned=other.event(other.one('SELECT response FROM processing_control_returns')['response'])
        self.assertEqual(returned['body']['actual_worker_return'],json.loads(raw['result']))
        self.assertEqual(processing.apply_control(other,self.control_event,self.control_attempt),resolution)
        self.assertEqual(len(other.rows('SELECT * FROM processing_control_returns')),1)
        for event in (self.work_event,self.control_event): self.assertIsNone(other.one('SELECT processed_at FROM events WHERE id=?',(event,))['processed_at'])
        self.assertEqual(other.rows('SELECT * FROM admissions'),[])
        self.assertEqual(other.rows('SELECT * FROM ordinary_runs'),[])

    def test_negative_metadata_matrix_atomic_before_bodies(self):
        request=self.request794()
        cases=[('events','hold','held','id',self.work_event),('events','hold','held','id',self.members[0]),
            ('events','hash','wrong','id',self.members[0]),('queue','job','frozen','event',self.work_event),
            ('queue','state','held','event',self.work_event),('queue','role','QA','event',self.work_event),('queue','phase','integrator','event',self.work_event),('processing_capabilities','issuer','wrong','id',self.cap),
            ('jobs','hold_reason','held','id',self.producer),('jobs','effects','unknown','id',self.producer),('jobs','role','QA','id',self.producer),
            ('jobs','controller','wrong','id',self.producer),('jobs','response','wrong','id',self.producer),
            ('attempts','collected',None,'id',self.control_attempt),('attempts','capture','incomplete','id',self.control_attempt),
            ('attempts','binding','{}','id',self.control_attempt),('attempts','controller','wrong','id',self.control_attempt),
            ('processing_controls','source_hash','wrong','event',self.control_event),
            ('processing_capabilities','starts',44,'id',self.cap),('processing_capabilities','revoked',1000.,'id',self.cap),
            ('prospective_authorities','revoked',1000.,'id',self.epoch['id']),('processing_runs','state','owned','controller',self.controller),
            ('enrollments','grant_id','wrong','role','Work')]
        for table,column,value,key,identity in cases:
            with self.subTest(table=table,column=column):
                original=self.store.one(f'SELECT {column} FROM {table} WHERE {key}=?',(identity,))[column]
                try:
                    self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(value,identity))
                    before=self.snapshot794()
                    with patch.object(self.store,'event',side_effect=AssertionError('wrong body read')),self.assertRaises(Refusal):self.apply794(request)
                    self.assertEqual(before,self.snapshot794())
                finally:self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(original,identity))

    def test_negative_full_bytes_and_expiry_atomic(self):
        request=self.request794()
        for target,mutate in [('response',lambda x:x['report_custody'].update(collector='wrong')),
            ('response',lambda x:x.update(source_attempt='wrong')),('response',lambda x:x['body'].update(summary='forged')),
            ('control',lambda x:x.update(semantic='UNKNOWN')),('control',lambda x:x.update(decision_json=x['decision_json']+' '))]:
            with self.subTest(target=target,mutation=repr(mutate)):
                table,column,key,identity=('events','payload','id',self.work_event) if target=='response' else ('attempts','result','id',self.control_attempt)
                original=self.store.one(f'SELECT {column} FROM {table} WHERE {key}=?',(identity,))[column]
                try:
                    value=json.loads(self.store.one(f'SELECT {column} FROM {table} WHERE {key}=?',(identity,))[column]);mutate(value)
                    self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(encode(value),identity))
                    before=self.snapshot794()
                    with self.assertRaises(Refusal):self.apply794(request)
                    self.assertEqual(before,self.snapshot794())
                finally:self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(original,identity))
        self.store.clock=lambda:1599.999
        self.basis794()  # Explicit synthetic just-before-expiry; no real rights claim.
        for now in (1600.,1601.):
            self.store.clock=lambda:now
            before=self.snapshot794()
            with patch.object(self.store,'event',side_effect=AssertionError('expired body read')),self.assertRaises(Refusal):self.apply794(request)
            self.assertEqual(before,self.snapshot794())
        self.store.clock=lambda:1000.

    def test_negative_original_chain_and_request_pins(self):
        request=self.request794()
        cases=[('attempts','collected',None,'id',self.producer_attempt),('attempts','capture','incomplete','id',self.producer_attempt),
            ('attempts','exit',1,'id',self.producer_attempt),('attempts','binding','{}','id',self.producer_attempt),
            ('attempts','error','unknown','id',self.producer_attempt),('results','result','{}','attempt',self.producer_attempt),
            ('jobs','members','[]','id',self.producer),('events','hold','held','id',self.control_event),
            ('queue','task','@unresolved','event',self.control_event),('queue','package','invented','event',self.control_event),
            ('processing_controls','capability','wrong','event',self.control_event),
            ('service_runs','returned',None,'controller',self.controller)]
        for table,column,value,key,identity in cases:
            with self.subTest(table=table,column=column):
                original=self.store.one(f'SELECT {column} FROM {table} WHERE {key}=?',(identity,))[column]
                try:
                    self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(value,identity));before=self.snapshot794()
                    with self.assertRaises(Refusal):self.apply794(request)
                    self.assertEqual(before,self.snapshot794())
                finally:self.store.db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(original,identity))
        for key in ['configuration','selection_hash','configuration_version','controller','old_implementation','implementation','release','prospective','grants','starts','revision']:
            bad=copy.deepcopy(request);bad['basis'][key]='wrong';before=self.snapshot794()
            with self.subTest(key=key),self.assertRaises(Refusal):self.apply794(bad)
            self.assertEqual(before,self.snapshot794())
        # Frozen membership cannot be hidden by clearing queue.job.
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects) VALUES('frozen794','Work','proposer','work-proposer',?,'other','token',1000,'held','unknown')",
            (encode([dict(event=self.work_event,hash=digest(self.response))]),))
        with patch.object(self.store,'event',side_effect=AssertionError('frozen body read')),self.assertRaises(Refusal):self.apply794(request)

    def test_closed_actual_source_delta_and_v1_limits(self):
        request=self.request794();b=request['basis'];old=b['old_implementation'];new=b['implementation'];before=b['old_release'];after=b['release']
        self.assertEqual(repair.source_compatible(before,after,old,new,self.modules,_ceiling=repair.LEASE_MODULES if os.environ.get('QUALIFICATION801_OWNER_LEASE') else repair.PAIR_MODULES),b['changed'])
        with self.assertRaises(Refusal):repair.source_compatible(before,after,old,new,self.modules)
        for field in ['root','pool_control','qualification']:
            bad=copy.deepcopy(after);bad[field]='swapped'
            with self.assertRaises(Refusal):repair.source_compatible(before,bad,old,new,self.modules,_ceiling=repair.LEASE_MODULES if os.environ.get('QUALIFICATION801_OWNER_LEASE') else repair.PAIR_MODULES)
        for module in ['configuration.py','contracts.py','execution_pool.py','ordinary.py']:
            bad=copy.deepcopy(after);impl=copy.deepcopy(new);impl[module]='0'*64;bad['files']['/src/tools/coordinator-runtime/coordinator_runtime/'+module]='0'*64
            with self.assertRaises(Refusal):repair.source_compatible(before,bad,old,impl,sorted(self.modules+[module]),_ceiling=repair.LEASE_MODULES if os.environ.get('QUALIFICATION801_OWNER_LEASE') else repair.PAIR_MODULES)
        for path in ['/src/tools/coordinator-runtime/templates/coordinator-receive.md','/src/tools/message-board/board_store.py','/src/tools/direct-child/execution_pool.py']:
            bad=copy.deepcopy(after);bad['files'][path]='0'*64
            with self.assertRaises(Refusal):repair.source_compatible(before,bad,old,new,self.modules,_ceiling=repair.LEASE_MODULES if os.environ.get('QUALIFICATION801_OWNER_LEASE') else repair.PAIR_MODULES)
        self.apply794(request)
        table='owner_lease_plans' if os.environ.get('QUALIFICATION801_OWNER_LEASE') else 'same_authority_report_control_repairs_v2'
        for query in ['UPDATE '+table+' SET issuer=issuer','DELETE FROM '+table]:
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute(query)
        with actor(self.boards['Work'].store,self.issuer),self.assertRaises(Refusal):repair.source_basis(self.store,self.boards,self.cap,[self.work_event],self.controller,self.issuer,['report_repair.py'],'No stacking')

    def test_return_failure_rolls_back_resolution_and_child(self):
        self.apply794(self.request794())
        from coordinator_runtime.store import Store
        other=Store(self.config,clock=lambda:1000.);self.addCleanup(other.close)
        other.processing=processing.Access(other,self.cap,self.boards)
        before='\n'.join(other.db.iterdump());budget=other.budget
        def failing(table,*args,**kwargs):
            if table=='events':
                self.assertIsNotNone(other.input_resolution(self.control_event))
                raise Refusal('Injected durable return write failure')
            return budget(table,*args,**kwargs)
        with patch.object(other,'budget',side_effect=failing),self.assertRaisesRegex(Refusal,'Injected durable'):
            processing.apply_control(other,self.control_event,self.control_attempt)
        self.assertEqual(before,'\n'.join(other.db.iterdump()))

    def test_stale_between_groups_rolls_back_without_wrong_body(self):
        request=self.request794();actual=self.store.event;reads=[]
        def read(event):
            reads.append(event)
            if event==self.control_event:raise AssertionError('held control body read')
            value=actual(event)
            if event==self.work_event:self.store.db.execute('UPDATE events SET hold=? WHERE id=?',('stale-group',self.control_event))
            return value
        before=self.snapshot794()
        with patch.object(self.store,'event',side_effect=read),self.assertRaises(Refusal):self.apply794(request)
        self.assertEqual(before,self.snapshot794());self.assertNotIn(self.control_event,reads)

class Kernel794(unittest.TestCase):
    def test_source_and_sdk_snapshots_readonly(self):
        import errno
        sources=[Path(__file__),Path('/src/tools/coordinator-runtime/coordinator_runtime/processing.py')]
        sources += [Path('/src/tools/coordinator-runtime/tests/fixture_snapshot')/n for n in ('queue_transport.py','active_listener.py','catalog.py','board_store.py','retention.py')]
        for path in sources:
            self.assertTrue(path.is_file());self.assertTrue(os.statvfs(path).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as caught:os.open(path,os.O_WRONLY)
            self.assertEqual(caught.exception.errno,errno.EROFS)
        self.assertEqual(os.environ['TMPDIR'],'/fixtures/tmp')
