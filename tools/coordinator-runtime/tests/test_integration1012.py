"""Same-cap native Source retention plus finite future software, all fiction.

Public controllers and Executor run; identities, clock, reviewed-release claims,
transport/END and physical facts are owned fixture seams, never live evidence.
"""
import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_retained_source995 import Retained995
from test_future_software1008 import Future1008, at
from test_source_continuity688 import Continuity
from test_qa629_repairs import actor
from coordinator_runtime import processing, processing_admission, prospective
from coordinator_runtime import configuration, resource_scopes, service, windows
from coordinator_runtime import report_repair as repair
from coordinator_runtime.contracts import Refusal, Backpressure, digest, encode, ident
from coordinator_runtime.service_wake import ServiceWake


class Integration1012(Retained995):
    command = Future1008.command
    future_request = Future1008.future_request
    future_apply = Future1008.future_apply
    basis = Continuity.basis

    def configure_fixture(self):
        super().configure_fixture()
        self.config['limits']['max_bytes'] = 2*1024**3
        self.config['window_service'] = dict(tasks=list(self.config['tasks']),max_new_inputs=40,batch_size=8,max_decisions=100)
        self.config['tasks']['qa-execution'].update(require_package_scope=True,scope_roots=[str(self.independent)])
        self.scope = dict(cwd=str(self.independent),read_roots=[str(self.independent)],write_roots=[],
            procedure=str(self.method),resource_evidence='Independent fictional original QA scope')

    def configure_selection(self, selected):
        super().configure_selection(selected)
        selected['service'].update(
            wake=dict(protocol='managed-hint-v1',roles=list(self.config['roles']),until=at('07:43:35')),
            admission=dict(until=at('07:43:35'),pause_bytes=90000000,max_new_inputs=20),
            allocations=dict(basis=windows.basis(self.store),target='Original finite future software',
                reason='Conserve original duties',evidence='Fictional original Work selection',
                custody={r:dict(owner=v['owner'],evidence='Original custodian') for r,v in self.config['roles'].items()},
                expires=at('07:43:35'),max_windows=35))
        selected['service']['legacy_resources']['Reviews']['native_review_return']['expires'] = at('10:44:25')
        selected['software_admission'] = dict(authority='Original fictional QA admission',max_packages=2,
            scopes=dict(fixture=dict(submitters=[self.config['roles']['Work']['owner']],package_prefix='fictional-',
                task_scopes={'qa-execution':self.scope},evidence='Original independent QA scope')))

    def snapshot(self):
        tables = ('processing_capabilities','prospective_authorities','enrollments','admissions',
            'processing_admissions','processing_admission_resolutions','processing_source_positions',
            'queue','jobs','attempts','job_resource_policies','review_calls','review_call_contexts',
            'review_contexts','review_history_commits','file_publications','ordinary_resources',
            'service_windows','service_window_allocations')
        return {t:self.store.rows('SELECT * FROM '+t) for t in tables}

    def managed_post(self, role, package):
        board = self.boards[role]
        sender = self.config['roles']['Branch' if role=='Work' else 'Work']['owner']
        args = ['open','--session',sender,'--to',board.selected['owner'],'--topic','fixture',
                '--kind','finding','--text','Fresh finite input','--title','Fictional integration1012','--no-push']
        if package:args += ['--ref',package]
        with board.opened() as conn, actor(board.store,sender):
            seq = board.store.open_thread(conn,board.store.parser().parse_args(args))
        found = None
        for event in board.scan(self.store):
            self.store.ingest(event,cursor=event['post'])
            if event['post']==seq:found = event
        self.assertIsNotNone(found)
        return found

    def test_same_cap_native_incomplete_source_future_software_boundary(self):
        pins = json.loads(Path('/public/production-pins.json').read_text())
        self.store.clock = lambda:at('07:30:00')
        original_select = prospective.select
        def original_epoch(runtime, issuer, selection):
            selection['expires'] = at('10:44:25')
            return original_select(runtime,issuer,selection)
        with patch.object(processing,'implementation',return_value=pins['original']), \
                patch.object(prospective,'select',side_effect=original_epoch), self.active():
            self.cap = self.key
            self.issuer = self.config['roles']['Work']['owner']
            active_modes = self.modes()
            self.return_interrupted()
            self.assertEqual(self.modes(),active_modes)
            self.assertIsNone(self.store.job(self.job['id'])['response'])
            # Production public Board, software admission and classification.
            qa = self.post('Original independently admitted QA','QA','fictional-original-package',topic='fixture')
            processing_admission.admit(self.store,qa['id'])
            work = self.post('Original pending Work','Work')
            self.initial[work['id']] = 'work-proposer'
            # The public scheduler admits one classifier per phase. Three
            # pending originals may precede QA at this equal fictional clock.
            for _ in range(3):asyncio.run(self.phase('schedule_classifications'))
            self.events = [qa['id']]
            self.assertIsNotNone(self.store.one('SELECT * FROM queue WHERE event=?',(qa['id'],)))
            controller = self.store.controller
            self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(controller,self.cap,'owned',self.store.clock()))
            self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
                (controller,self.cap,'fictional-unused','returned-awaiting-parent-END',self.store.clock(),self.store.clock(),'Fictional original return'))
            with actor(self.boards['Work'].store,self.issuer):
                processing.release(self.store,self.boards,self.cap,controller,dict(actual_END=0,evidence=['Fictional parent collected original END0']))
            self.controller = controller
            self.original_impl = pins['original'];self.new_impl = pins['candidate']
            self.modules = sorted(n for n in self.new_impl if self.new_impl[n] != self.original_impl[n])
            self.assertEqual(set(self.modules),{'cli.py','report_repair.py','store.py','resource_scopes.py'})
            self.assertLessEqual(set(self.modules),repair.SOURCE_MODULES)
            self.assertEqual(self.new_impl['reviews.py'],self.original_impl['reviews.py'])
            prefix = '/fictional-same-public-release/tools/coordinator-runtime/coordinator_runtime/'
            old_release = dict(root='/fictional-same-public-release',
                pool_control=self.store.execution_pool.pool.control_binding(Path(self.config['execution_pool_routes']).read_bytes()),
                files={prefix+n:h for n,h in self.original_impl.items()})
            new_release = copy.deepcopy(old_release)
            for n in self.modules:new_release['files'][prefix+n] = self.new_impl[n]
            raw = json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
            transition = dict(basis=dict(release=old_release,tasks=self.config['tasks'],
                processing=dict(roles={r:dict(original=dict(binding=v['original']['binding'])) for r,v in raw['basis']['roles'].items()})),
                event_boundary=0,jobs=[],outboxes=[],alert_boundary=0)
            self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
                ('fictional-previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.issuer,self.store.clock()))
            with patch.object(configuration,'release',return_value=new_release), \
                    patch.object(processing,'implementation',return_value=self.new_impl):
                request = Continuity.request(self)
                source_receipt = Continuity.apply(self,request)
                self.assertIsNone(source_receipt['acceptance'])
                # Real cumulative window charges preserve the original boundary.
                with self.store.tx():
                    for _ in range(34*40+1):windows.charge(self.store,'events',new_input=True)
                self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],34)
                self.now = at('08:15:00');self.store.clock = lambda:self.now
                # Basis names the released original; the observing controller
                # is fresh and cannot stand in for that original END receipt.
                self.store.controller = ident()
                self.plan = dict(**{'from':self.now},until=at('10:30:00'),lease_seconds=1800,
                    max_starts=512,max_new_inputs=8192,max_windows=35,pause_bytes=1056964608)
                self.plan_file = self.area/'future-plan.json';self.plan_file.write_text(encode(self.plan))
                with self.assertRaises(Backpressure):service.admit_input(self.store)
                before = self.snapshot()
                future = self.future_request();receipt = self.future_apply(future)
                self.assertEqual(before,self.snapshot())
                self.assertFalse(receipt['native_rights_renewed']);self.assertIsNone(receipt['acceptance'])
                self.assertEqual(self.modes(),active_modes)
                # This is the actual current-cap mapper, including the original
                # proof created before source repair and the effective plan.
                with self.store.tx():
                    resource_scopes.original_resources(self.store,self.identity,self.config['tasks']['reviews-proposer'])
                self.store.db.execute('SAVEPOINT pressure1012')
                try:
                    self.store.db.execute('UPDATE processing_capabilities SET starts=512 WHERE id=?',(self.cap,))
                    attempts = self.store.rows('SELECT * FROM attempts')
                    with self.assertRaises(Refusal):self.store._attempt('input-control',qa['id'],None,{},'.codex')
                    self.assertEqual(self.store.rows('SELECT * FROM attempts'),attempts)
                    self.assertEqual(self.modes(),active_modes)
                finally:
                    self.store.db.execute('ROLLBACK TO pressure1012');self.store.db.execute('RELEASE pressure1012')
                usage = self.store.usage()
                with patch.object(self.store,'usage',return_value={**usage,'bytes':self.plan['pause_bytes']}):
                    with self.assertRaises(Refusal):service.admit_input(self.store)
                for role in ('QA','Work'):
                    row = dict(self.candidate(role),package='fictional-original-package' if role=='QA' else None)
                    self.assertFalse(resource_scopes.blocked(self.store,row))
                held = active_modes[1][0]
                overlapping = copy.deepcopy(self.config['tasks']['work-integrator'])
                overlapping.pop('routine_completion',None)
                overlapping['effect_authority']['read_roots'] = [str(held)]
                self.assertTrue(resource_scopes.blocked(self.store,self.candidate(),overlapping))
                for sql,args in [
                    ("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','wrong') WHERE id=?",(self.attempt_id,)),
                    ("UPDATE review_contexts SET state='unknown' WHERE component=?",(self.component889,)),
                    ("INSERT INTO ordinary_resources VALUES('opaque1012','missing1012')",()),
                ]:
                    self.store.db.execute('SAVEPOINT fault1012')
                    try:
                        self.store.db.execute(sql,args)
                        self.assertTrue(resource_scopes.blocked(self.store,self.candidate()))
                    finally:
                        self.store.db.execute('ROLLBACK TO fault1012');self.store.db.execute('RELEASE fault1012')
                async def wakes():
                    wake = ServiceWake(self.store,self.boards,SimpleNamespace(wakeup=asyncio.Event()))
                    try:
                        wake.start();self.assertEqual(wake.state,'bound');self.assertEqual(len(wake.receivers),4)
                        self.now = at('08:45:00');wake._expired()
                        self.assertEqual(wake.until,at('09:15:00'))
                        for role,task,package in [('Work','work-proposer',None),('Reviews','reviews-proposer',None),
                                ('QA','qa-execution','fictional-next-QA'),('Branch','branch-proposer',None)]:
                            prior = wake.hints
                            event = self.managed_post(role,package)
                            self.initial[event['id']] = task
                            _,board,_,helper = next(row for row in wake.receivers if row[1].role==role)
                            with board.opened() as conn:helper.signal_post(conn,event['post'])
                            await asyncio.sleep(0);await asyncio.sleep(0)
                            self.assertGreater(wake.hints,prior)
                            self.assertIsNotNone(self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(event['id'],)))
                        # Reserve one genuine new classifier before expiry.
                        # Collection is owed even when new intake later stops.
                        owed, owed_event = self.store.claim_classification()
                        self.store.begin(owed,{'fictional_owed_classifier':True})
                        self.store.session(owed,ident())
                        self.now = at('10:30:00');wake._expired()
                        self.assertEqual(wake.state,'expired');self.assertEqual(wake.receivers,[])
                        with self.assertRaises(Refusal):service.admit_input(self.store)
                        answer = dict(event_id=owed_event['id'],task=self.initial[owed_event['id']],
                            package=owed_event.get('package'),reason='Fictional owed completion across expiry')
                        self.store.collect(owed,dict(exit=0,capture='complete',cleanup='done',error=None,
                            result=answer,detail={'fictional_owed_classifier':True}))
                        self.assertIsNotNone(self.store.attempt(owed)['collected'])
                        # Decision1014 separates prospective end from authentic
                        # owned routing within the unchanged original epoch.
                        self.store.commit_classification(owed)
                        self.assertIsNotNone(self.store.one('SELECT * FROM queue WHERE event=?',(owed_event['id'],)))
                        self.owed_completion = dict(attempt=owed,collected=True,commit='committed within original epoch',
                            meaning='Old owned routing uses real remaining allocation; future intake stays stopped')
                    finally:wake.close()
                routes = Path(self.config['execution_pool_routes']);pool = routes.read_bytes()
                self.assertEqual(len(self.store.execution_pool.status()['enabled']),5)
                routes.write_bytes(self.store.execution_pool.pool.__class__.control_binding.__globals__['replace_membership'](pool,['.codex4']))
                self.assertEqual(self.store.execution_pool.allocate()['profile'],'.codex4')
                routes.write_bytes(pool)
                asyncio.run(wakes())
                # All original rows survive; newly born sources may append.
                for table,key in [('queue','id'),('jobs','id'),('attempts','id'),('processing_source_positions','event')]:
                    for row in before[table]:self.assertEqual(self.store.one('SELECT * FROM '+table+' WHERE '+key+'=?',(row[key],)),row)
                cap_after = self.store.one('SELECT * FROM processing_capabilities')
                self.assertEqual(cap_after,{**before['processing_capabilities'][0],
                    'starts':before['processing_capabilities'][0]['starts']+1})
                for table in ('prospective_authorities','admissions','processing_admissions',
                        'processing_admission_resolutions','job_resource_policies','review_calls','review_call_contexts',
                        'review_contexts','review_history_commits','file_publications','ordinary_resources','service_window_allocations'):
                    self.assertEqual(self.store.rows('SELECT * FROM '+table),before[table])
                self.assertEqual(self.store.one('SELECT state FROM review_contexts')['state'],'interrupted')
                self.assertIsNone(self.store.job(self.job['id'])['response'])
                self.command(['stop-future-software',self.cap,'--reason','Fictional Work stop conserves all original duties'])
                with self.assertRaises(Refusal):service.admit_input(self.store)
                self.now = at('10:44:25')
                with self.assertRaises(Refusal):self.modes()
                with self.assertRaises(Refusal):prospective.current(self.store,'qa-execution',ordinary_effects=True)
                (self.area/'combined-boundary.json').write_text(encode(dict(cap=self.cap,
                    native_attempt=self.attempt_id,source_receipt=source_receipt,future_receipt=receipt,
                    modules=self.modules,owed_completion=self.owed_completion,physical_terminal='UNKNOWN fictional incomplete transport',
                    original_snapshot=before,final_snapshot=self.snapshot()))+'\n')


def load_tests(loader,tests,pattern):
    return unittest.TestSuite([Integration1012('test_same_cap_native_incomplete_source_future_software_boundary')])
