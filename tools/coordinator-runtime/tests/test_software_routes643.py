"""Real public Board/SQLite/Git/ordinary routes in retained owned fiction.

Only SDK caller identity and collected model answers are synthetic. No provider,
native session, external Board, current operating config or historical adoption.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import time
import unittest

from test_qa629_repairs import Fixture, actor, sha
from support import collect, result
from coordinator_runtime import processing, processing_admission, prospective, ordinary, resource_scopes, service, report_scope
from coordinator_runtime.contracts import Refusal, digest, encode, ident


class SoftwareRoutes643(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.packages = {}
        self.bootstrap(self.configure)
        self.select_software()
        self._asyncioRunner.get_loop().set_debug(False)

    def configure(self):
        self.config['limits']['max_result_bytes'] = 262144
        self.config['deadlines']['task'] = 60
        self.now = time.time()
        self.issuer = self.config['roles']['Work']['owner']
        self.config['tasks']['qa-cleanup'].update(effects='owned-artifacts',sandbox='workspace-write',require_package_scope=True,
            package_narrowing=True,scope_roots=[str(self.area)])
        self.config['tasks']['qa-cleanup']['effect_authority'].update(read_roots=[str(self.area)],write_roots=[],
            operations=['read-reports','consolidate-reports','write-owned-artifacts'])
        self.config['tasks']['qa-execution'].update(effects='owner-reconcile',require_package_scope=True,scope_roots=[str(self.area)])
        self.config['tasks']['qa-execution']['effect_authority']['operations']=['execute-admitted-qa']
        ri=self.config['tasks']['reviews-integrator']
        reportdir=self.area/'review-output';reportdir.mkdir()
        ri.update(effects='owned-artifacts',sandbox='workspace-write',cwd=str(reportdir))
        ri['effect_authority'].update(read_roots=[str(reportdir)],write_roots=[],
            operations=['read-reports','consolidate-reports','write-owned-artifacts'])
        self.report=dict(reference='fresh-review-643',collector=self.issuer,actual_END=0,
            reports=[dict(name='Source',body='Original source=fiction, context=none. method HIGH. Verdict PARTIAL. Dissent O1. unread=family9.'),
                     dict(name='correction',body='O1 remains; qualification is partial; collector is the original fictional Work.')],
            history='Whole first fictional encounter; no native adoption',method_pin='fiction-method-HIGH',
            coverage={'read':['architecture'],'unread':['family9'],'qualification':'PARTIAL'},effects='known-report-only')
        self.scopes={};self.operations=[]
        for i in range(1,6): self.package(i)

    def package(self, i):
        key=f'future-qa-{i}'
        root=self.area/key;root.mkdir();self.repo=root/'repo';self.repo.mkdir()
        self.git('init','--initial-branch=source')
        self.git('remote','add','origin','https://example.invalid/owned-fiction.git')
        (self.repo/'source.txt').write_text('candidate '+key+'\n')
        self.git('add','source.txt');self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
            '-c','commit.gpgsign=false','commit','-m','owned candidate')
        head=self.git('rev-parse','HEAD');tree=self.git('rev-parse','HEAD^{tree}')
        procedure=root/'procedure.md';procedure.write_text('Run exact candidate source check; independent readback verifies output, package and source.\n')
        out=root/'out';out.mkdir();clean=root/'cleanup';clean.mkdir()
        runner=root/'runner.py';readback=root/'readback.py'
        runner.write_text('from pathlib import Path\nassert Path("source.txt").read_text() == '+repr('candidate '+key+'\n')+'\nPath('+repr(str(out/'actual.txt'))+').write_text('+repr(key+' '+head)+')\n')
        readback.write_text('from pathlib import Path\nassert Path('+repr(str(out/'actual.txt'))+').read_text() == '+repr(key+' '+head)+'\nprint('+repr('VERIFIED '+key+' '+head)+')\n')
        exe='/usr/bin/python3.12'
        p=dict(kind='local-qa',git='/usr/bin/git',git_sha256=sha('/usr/bin/git'),repository=str(self.repo),
            source_ref='refs/heads/source',source_head=head,procedure_sha256=sha(procedure),timeout=15,max_output=32768,
            resources=[dict(key=key,owner=self.config['roles']['QA']['owner'],authority='Fictional exact package resource',expires=self.now+600)],
            acceptor=self.issuer,acceptance_authority='Actual fictional Work independently checks exact run',
            known_exits=[0,1],source_capture=dict(bwrap='/usr/bin/bwrap',sha256=sha('/usr/bin/bwrap'),max_bytes=1048576,max_files=100),
            public_executables={label:dict(path=exe,bytes=Path(exe).stat().st_size,sha256=sha(exe)) for label in ['command','readback']})
        for label,path in [('command',runner),('readback',readback)]:
            p[label]=dict(argv=[exe,'-B',str(path)],executable_sha256=sha(exe),script_sha256=sha(path),
                stdout='VERIFIED '+key+' '+head+'\n' if label=='readback' else None)
        execution=dict(cwd=str(self.repo),read_roots=[str(self.repo),str(procedure),str(runner),str(readback)],write_roots=[str(out)],
            network=False,procedure=str(procedure),resource_evidence='Fictional current independent package',ordinary_effects=p)
        cleanup=dict(cwd=str(clean),read_roots=[str(procedure)],write_roots=[],network=False,
            procedure=str(procedure),resource_evidence='Consolidation only of exact accepted original report')
        scope=dict(submitters=[self.issuer],package_prefix=key,task_scopes={'qa-execution':execution,'qa-cleanup':cleanup},
            evidence='Work issued exact finite package and procedure rights; no native consent asserted')
        topic='topic-'+key;self.scopes[topic]=scope
        statement={'fixture_only':True,'known':'no current relevant conflicting original in new owned fiction','old':'global unknown unchanged'}
        self.operations.append(dict(statement=statement,binding=dict(task='qa-execution',package=key,topic=topic,scope_sha256=digest(scope)),
            policy=dict(version='qa-operation-v1',custodian=self.config['roles']['QA']['owner'],reference=key,
                statement_sha256=digest(statement),authority='Actual fictional Work selects exact package operation',expires=self.now+600,
                scope=execution,source=dict(common_git=str(self.repo/'.git'),tree=tree,parents=[]),
                inputs=[dict(path=str(path),sha256=sha(path)) for path in [procedure,runner,readback]],relevant_roots=[]),
            cleanup=dict(task='qa-cleanup',scope=cleanup,procedure_sha256=sha(procedure))))
        self.packages[key]=dict(scope=scope,topic=topic,repo=self.repo,head=head,p=p)

    def select_software(self):
        for role,board in self.boards.items():
            with actor(board.store,self.issuer):board.revoke_software(self.store,self.store.enrollment(role)['grant_id'])
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(role,))
        for role in ['QA','Reviews']:
            self.store.db.execute('UPDATE enrollments SET legacy_hold=? WHERE role=?',(role+' global UNKNOWN',role))
        self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for board in self.boards.values():board.runtime=self.store
        records={r:dict(original_hold=r+' global UNKNOWN',roots=[],unbounded=True,evidence='Public bounded known/unknown account') for r in ['QA','Reviews']}
        records['QA']['qa_operations']=self.operations
        records['Reviews']['reviews_report']=dict(version='reviews-report-v1',authority='Actual fictional Work report integration',expires=self.now+600,
            task='reviews-integrator',task_sha256=digest(self.config['tasks']['reviews-integrator']),
            reports=[dict(reference=self.report['reference'],sha256=digest(self.report))])
        self.selection=dict(basis=processing.basis(self.store,self.boards),authority='Actual fictional Work finite duties',
            retained_events=[],recover_controls={},future_intake=True,tasks=list(self.config['tasks']),
            max_shared_rows=1000,max_shared_payload_bytes=1000000,max_runtime_rows=1000,
            software_admission=dict(authority='Typed finite Work topic/scope/procedure authority',max_packages=5,scopes=self.scopes),
            work_coordination=dict(authority='Genuine Work consumes actual role reports',tasks=['work-proposer','work-integrator'],source_roles=['QA','Reviews','Branch']),
            service=dict(max_inflight=8,reviews={},report_tasks=['reviews-integrator'],legacy_resources=records))
        with actor(self.boards['Work'].store,self.issuer):
            self.cap=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Actual fictional Work future duties',
            expires=self.now+600,processing_capability=self.cap,
            grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects='admitted-v1' if t=='qa-execution' else False)
                for t,v in self.config['tasks'].items()}))
        self.runtime.boards=self.boards

    def source(self,key):
        board=self.boards['QA'];topic=self.packages[key]['topic']
        args=board.store.parser().parse_args(['open','--session',self.issuer,'--topic',topic,'--kind','finding',
            '--text','Fictional exact selected QA package','--to',self.config['roles']['QA']['owner'],'--title',key,'--ref',key,'--no-push'])
        with board.store.database(str(self.board_path)) as conn:
            with actor(board.store,self.issuer):board.store.open_thread(conn,args)
        messages=board.scan(self.store);self.assertEqual(len(messages),1)
        message=messages[0];self.store.ingest(message,cursor=message['post'])
        processing_admission.admit(self.store,message['id'])
        self.classify(task='qa-execution',package=key)
        return message

    def prepared(self,job,answer):
        attempt=self.store.start_job(job['id'],job['token'])
        job=self.store.job(job['id'])
        admission=self.store.one('SELECT * FROM admissions WHERE package=?',(job['package'],))
        self.boards[job['role']].bind_software_attempt(self.store,job,attempt,admission)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        return self.store.job(job['id']),attempt

    async def execute(self,key,accept=True):
        job=self.store.reserve();self.assertIsNotNone(job);self.assertEqual(job['package'],key)
        job,attempt=self.prepared(job,result(category='consolidated'))
        self.assertTrue(await ordinary.perform(self.store,self.boards['QA'],job))
        self.assertFalse(ordinary.accepted_package(self.store,key))
        if accept:
            receipt=json.loads(self.store.one('SELECT receipt FROM ordinary_runs WHERE attempt=?',(attempt,))['receipt'])
            await ordinary.accept(self.store,self.issuer,attempt,'accepted',dict(execution_hash=digest(receipt),rationale='Independent exact candidate/output/readback checked',unknowns=[]))
        response=self.store.finish_job(job['id'],job['token'])
        return job,attempt,response

    async def cleanup(self,key,response):
        self.classify()
        queued=self.store.one("SELECT * FROM queue WHERE event=?",(response,))
        self.assertFalse(resource_scopes.blocked(self.store,queued))
        job=self.store.reserve();self.assertIsNotNone(job);self.assertEqual(job['task'],'qa-cleanup');self.assertEqual(job['package'],key)
        answer=result(category='qualification');answer['findings'].append(dict(collected_reports=report_scope.conserved_inputs(self.store,job)))
        job,attempt=self.prepared(job,answer)
        await ordinary.qualification(self.store,job)
        routed=self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.event(routed)['role'],'Branch')
        self.assertEqual(self.store.event(routed)['body'],answer)
        self.assertTrue(ordinary.qualification_current(self.store,job))
        return job

    async def test_first_and_fifth_actual_execute_accept_cleanup_without_native_bootstrap(self):
        for key in self.packages:self.source(key)
        self.assertEqual(len(self.store.rows('SELECT * FROM admissions')),5)
        self.assertNotIn(self.cap,str(self.selection))
        responses = {}
        for key in self.packages:
            _,_,responses[key]=await self.execute(key)
        for key,response in responses.items():
            await self.cleanup(key,response)
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'QA global UNKNOWN')
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_acceptance')),5)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])
        with self.assertRaises(Exception):self.store.db.execute("UPDATE processing_admission_resolutions SET scope_hash='forged'")

    async def test_execution_done_without_acceptance_does_not_admit_cleanup(self):
        key='future-qa-1';self.source(key)
        _,_,response=await self.execute(key,False)
        self.classify()
        queued=self.store.one('SELECT * FROM queue WHERE event=?',(response,))
        self.assertTrue(resource_scopes.blocked(self.store,queued));self.assertIsNone(self.store.reserve())

    async def test_genuine_reviews_collection_sole_consolidation_and_Work_report(self):
        e=service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)['event']
        self.classify()
        job=self.store.reserve();self.assertIsNotNone(job);self.assertEqual(job['task'],'reviews-integrator')
        answer=result(category='consolidated');answer['findings']=[dict(collected_reports=report_scope.conserved_inputs(self.store,job))]
        job,attempt=self.prepared(job,answer)
        from coordinator_runtime.dispatcher import job_prompt
        packet=json.JSONDecoder().raw_decode(job_prompt(self.store,job).split('TASK_CONTEXT=',1)[1])[0]
        self.assertEqual(packet['collected_reports'],answer['findings'][0]['collected_reports'])
        response=self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.event(response)['role'],'Work')
        self.assertEqual(self.store.event(response)['body']['findings'],answer['findings'])
        self.assertEqual(self.store.event(e)['body']['original'],self.report)
        self.assertEqual(self.store.enrollment('Reviews')['legacy_hold'],'Reviews global UNKNOWN')
        self.classify();work=self.store.reserve();self.assertEqual(work['task'],'work-proposer')
        self.assertEqual(self.store.rows('SELECT * FROM review_contexts'),[])

    async def test_tamper_cross_package_unknown_lease_and_revocation_stay_blocked(self):
        key='future-qa-1';message=self.source(key)
        row=self.store.one("SELECT * FROM queue WHERE event=?",(message['id'],))
        self.assertFalse(resource_scopes.blocked(self.store,row))
        self.assertTrue(resource_scopes.blocked(self.store,{**row,'package':'future-qa-5'}))
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped','unknown-original')")
        self.assertTrue(resource_scopes.blocked(self.store,row))
        self.store.db.execute("DELETE FROM ordinary_resources WHERE attempt='unknown-original'")
        self.assertFalse(resource_scopes.blocked(self.store,row))
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        self.assertTrue(resource_scopes.blocked(self.store,row))

    async def test_report_pointer_forgery_and_omission_cannot_launder_authority(self):
        bad=copy.deepcopy(self.report);bad['reports'][0]['body']='forged'
        event=service.ingest_report(self.store,self.issuer,'reviews-integrator',bad)['event']
        self.classify();row=self.store.one('SELECT * FROM queue WHERE event=?',(event,))
        self.assertTrue(resource_scopes.blocked(self.store,row));self.assertIsNone(self.store.reserve())

    async def test_cleanup_cross_binding_tampered_report_and_missing_whole_result_refuse(self):
        for key in ['future-qa-1','future-qa-5']:self.source(key)
        _,a1,r1=await self.execute('future-qa-1')
        _,a5,r5=await self.execute('future-qa-5')
        self.classify()
        q1=self.store.one('SELECT * FROM queue WHERE event=?',(r1,))
        self.assertFalse(resource_scopes.blocked(self.store,q1))
        self.assertTrue(resource_scopes.blocked(self.store,{**q1,'package':'future-qa-5'}))
        forged=copy.deepcopy(self.store.event(r1));forged['body']['summary']='forged report'
        with self.assertRaises(Refusal):self.store.ingest(forged)
        job=self.store.reserve();self.assertEqual(job['task'],'qa-cleanup')
        job,attempt=self.prepared(job,result(category='qualification'))
        await ordinary.qualification(self.store,job)
        with self.assertRaisesRegex(Refusal,'whole original report'):self.store.finish_job(job['id'],job['token'])
        # Genuine accepted execution still cannot qualify changed retained bytes.
        export=self.store.home/'artifacts'/a5/'qa-source'/'source.txt'
        export.write_text('tampered candidate after acceptance')
        q5=self.store.one('SELECT * FROM queue WHERE event=?',(r5,))
        self.assertTrue(resource_scopes.blocked(self.store,q5))

    async def test_original_exclusion_and_unknown_cross_role_reservation_stay_held(self):
        key='future-qa-1';message=self.source(key)
        row=self.store.one('SELECT * FROM queue WHERE event=?',(message['id'],))
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('unknown-writer','Branch','integrator','branch-integrator','old','[]','original','original',1,'unknown')")
        self.assertTrue(resource_scopes.blocked(self.store,row))
        self.assertIsNone(self.store.job('unknown-writer')['active_attempt'])
        self.assertEqual(self.store.job('unknown-writer')['effects'],'unknown')

    async def test_Reviews_consolidation_must_preserve_whole_dissent_and_current_grants(self):
        service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)
        self.classify();job=self.store.reserve();self.assertIsNotNone(job)
        job,attempt=self.prepared(job,result(category='consolidated'))
        with self.assertRaisesRegex(Refusal,'whole original report'):self.store.finish_job(job['id'],job['token'])
        self.assertIsNone(self.store.job(job['id'])['response'])
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        self.assertTrue(resource_scopes.blocked(self.store,job))


class BranchRoutes643(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bootstrap(self.configure)
        self.issuer=self.config['roles']['Work']['owner']
        for role,board in self.boards.items():
            with actor(board.store,self.issuer):board.revoke_software(self.store,self.store.enrollment(role)['grant_id'])
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(role,))
        self.store.db.execute("UPDATE enrollments SET legacy_hold='Branch original UNKNOWN' WHERE role='Branch'")
        self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for b in self.boards.values():b.runtime=self.store
        scope=dict(submitters=[self.issuer],package_prefix='branch-',task_scopes={'branch-integrator':self.scope},evidence='Work exact future local-ref operation rights')
        selection=dict(basis=processing.basis(self.store,self.boards),authority='Actual fictional Work Branch selection',
            retained_events=[],recover_controls={},future_intake=True,tasks=list(self.config['tasks']),max_shared_rows=1000,
            max_shared_payload_bytes=1000000,max_runtime_rows=1000,software_admission=dict(authority='Actual typed finite topic authority',max_packages=1,scopes={'branch-topic':scope}),
            service=dict(max_inflight=8,reviews={},legacy_resources={}))
        with actor(self.boards['Work'].store,self.issuer):self.cap=processing.select(self.store,self.boards,selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Work exact Branch operation',expires=time.time()+600,
            processing_capability=self.cap,grants={'Branch':self.store.enrollment('Branch')['grant_id']},
            tasks={'branch-integrator':dict(task_hash=digest(self.config['tasks']['branch-integrator']),software_handoffs={},ordinary_effects='admitted-v1')}))
        board=self.boards['Branch']
        args=board.store.parser().parse_args(['open','--session',self.issuer,'--topic','branch-topic','--kind','finding','--text','Exact new localref duty',
            '--to',self.config['roles']['Branch']['owner'],'--title','Branch fixture','--ref','branch-one','--no-push'])
        with board.store.database(str(self.board_path)) as conn:
            with actor(board.store,self.issuer):board.store.open_thread(conn,args)
        message=board.scan(self.store)[0];self.store.ingest(message,cursor=message['post'])
        processing_admission.admit(self.store,message['id'])
        from coordinator_runtime import branches
        branches.register(self.store,self.issuer,dict(id='binding',repository=str(self.repo),origin='https://example.invalid/fiction.git',ref='refs/heads/destination',
            incarnation='new-owned-incarnation',scope='branch-one',root=self.issuer,authority='Work exact association; accepted separately'))
        branches.accept(self.store,'binding',self.issuer,'Actual fictional Work accepts this bounded coordinator responsibility')
        self.runtime.boards=self.boards;self.classify(task='branch-integrator',package='branch-one')
        self.row=self.store.one('SELECT * FROM queue')
        self._asyncioRunner.get_loop().set_debug(False)

    def configure(self):
        self.config['deadlines']['task']=60
        self.repo=self.area/'repo';self.repo.mkdir();self.git('init','--initial-branch=source')
        self.git('remote','add','origin','https://example.invalid/fiction.git')
        (self.repo/'source.txt').write_text('old\n');self.git('add','source.txt')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','old')
        self.before=self.git('rev-parse','HEAD');self.git('branch','destination')
        (self.repo/'source.txt').write_text('new\n');self.git('add','source.txt')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','new')
        self.head=self.git('rev-parse','HEAD')
        procedure=self.area/'ref-procedure.md';procedure.write_text('CAS only owned destination from before to exact source; no other effects.\n')
        task=self.config['tasks']['branch-integrator'];task.update(effects='owner-reconcile',require_package_scope=True,scope_roots=[str(self.area)],network=True)
        task['effect_authority']['operations']=['organize-authorized-refs']
        p=dict(kind='local-ref',git='/usr/bin/git',git_sha256=sha('/usr/bin/git'),repository=str(self.repo),source_ref='refs/heads/source',source_head=self.head,
            ref='refs/heads/destination',before=self.before,target=self.head,procedure_sha256=sha(procedure),timeout=15,max_output=32768,
            resources=[dict(key='fixture-ref',owner=self.config['roles']['Branch']['owner'],authority='Exact owned local-ref resource',expires=time.time()+600)],
            acceptor=self.config['roles']['Work']['owner'],acceptance_authority='Actual fictional independent Work',)
        self.scope=dict(cwd=str(self.repo),read_roots=[str(self.repo),str(procedure)],write_roots=[str(self.repo)],network=False,
            procedure=str(procedure),resource_evidence='Bounded new owned refs only',ordinary_effects=p,branch_binding='binding')

    def qualify(self):
        from coordinator_runtime import ref_scope
        basis=ref_scope.material(self.store,'branch-integrator','branch-one')
        receipt=dict(authority_kind='work-selected-local-ref-v1',basis=basis,authority='Actual Work exact prospective operation, no historical/native consent assertion',
            originals=[],activity_scope=dict(original_hold=basis['original_hold'],operation=digest(dict(operation=basis['operation'],repository=basis['common_repository'],refs=basis['local_refs'])),
                no_active_writers=True,evidence='Only owned fixture repository, current original maps/turns/leases checked; no external history claim'),
            remaining_holds=[basis['original_hold']],past_effects=['All original collector/capture/effect debt stays unchanged'])
        return ref_scope.account(self.store,self.issuer,receipt)

    async def test_Work_selected_typed_ref_CAS_without_native_owner_adoption(self):
        self.assertTrue(resource_scopes.blocked(self.store,self.row));self.qualify()
        self.assertFalse(resource_scopes.blocked(self.store,self.row))
        job=self.store.reserve();self.assertIsNotNone(job)
        job,attempt=SoftwareRoutes643.prepared(self,job,result())
        self.assertTrue(await ordinary.perform(self.store,self.boards['Branch'],job))
        self.assertEqual(self.git('rev-parse','destination'),self.head)
        run=self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?',(attempt,));receipt=json.loads(run['receipt'])
        await ordinary.accept(self.store,self.issuer,attempt,'accepted',dict(execution_hash=digest(receipt),rationale='Exact owned destination/source CAS independently checked',unknowns=[]))
        self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.enrollment('Branch')['legacy_hold'],'Branch original UNKNOWN')

    async def test_unmapped_current_lease_and_unknown_job_do_not_become_no_conflict(self):
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unknown','foreign-original')")
        with self.assertRaisesRegex(Refusal,'unmapped original resource'):self.qualify()
        self.assertTrue(resource_scopes.blocked(self.store,self.row))
        self.store.db.execute("DELETE FROM ordinary_resources WHERE attempt='foreign-original'")
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('unmapped','QA','execution','qa-execution','other','[]','original','original',1,'unknown')")
        with self.assertRaisesRegex(Refusal,'cross-role original writer'):self.qualify()
        self.assertTrue(resource_scopes.blocked(self.store,self.row))

    async def test_disjoint_original_ref_map_preserves_uncollected_debt(self):
        # Explicit seeded fictional prior, with an original frozen/executed map.
        # Missing END stays NULL; it is not rewritten or certified closed.
        from coordinator_runtime import branches
        policy=copy.deepcopy(self.scope['ordinary_effects'])
        policy.update(source_ref='refs/heads/old-source',ref='refs/heads/old-destination')
        scope={**self.scope,'ordinary_effects':policy}
        admission=dict(package='old-package',owner=self.config['roles']['Branch']['owner'],
            receipt=encode(dict(task_scopes={'branch-integrator':scope})),accepted=None)
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('original','Branch','integrator','branch-integrator','old-package','[]','old-collector','old-token',1,'unknown')")
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',('original',encode(self.config['tasks']['branch-integrator']),encode(admission)))
        self.store.db.execute("INSERT INTO attempts(id,kind,job,controller,profile,binding,created) VALUES('original-attempt','task','original','old-collector','.codex5','{}',1)")
        dev,ino=branches.repository_identity(self.repo)
        receipt=dict(before=dict(common_repository=dict(dev=dev,ino=ino)))
        self.store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',('original-attempt','original','old-epoch','old-admission',encode(policy),'intent',encode(receipt)))
        self.qualify();self.assertFalse(resource_scopes.blocked(self.store,self.row))
        self.assertIsNone(self.store.attempt('original-attempt')['ended'])
        self.assertEqual(self.store.job('original')['effects'],'unknown')
        self.assertEqual(self.store.job('original')['controller'],'old-collector')
