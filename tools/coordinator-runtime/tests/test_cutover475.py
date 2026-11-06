"""Fictional principals/meaning/transports, production SDK and execution paths.

Run only in the positive-mount bwrap envelope. Every generated input/output is
owned fiction. Numeric model/native results below are declared transport seams,
not OS/provider END evidence. The QA adapter really runs and waits its tools.
"""
import asyncio
import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import config_at, result, ident
import test_software_consumption as software
from coordinator_runtime import (processing, metadata_lookup as lookup, local_integration as local,
    local_native, publication, prospective, ordinary, branches, reviews, service)
from coordinator_runtime.contracts import Refusal, digest, encode, validate_config, LUNA


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Cutover(unittest.IsolatedAsyncioTestCase):
    def fixture_config(self, cfg, area):
        cfg['canonical_publication']['library'] = '/sdk'
        self.catalog = area/'assignments.json'
        self.catalog.write_text(encode({'assignments':[{'id':k,'state':'old','owner':'accepted-'+k,
            'history':['retain'], 'unknown':{'null':None}} for k in ['one','related','unrelated']],
            'packet_coordination':{'rollout':{'status':'RUNNING','owner':'actual-fictional-owner'}}, 'mixed-root':'preserve'}))
        self.peers=[self.catalog]+[area/n for n in ['assignments.md','register.json','now.json','now.md','root.md']]
        for p in self.peers[1:]:
            p.write_text(encode({'records':[{'id':k,'state':'old','owner':'accepted-'+k} for k in ['one','related','unrelated']],
                'mixed-root':{'not-work':42}}) if p.suffix=='.json' else 'Historical consumer text\n')
        self.log=area/'WORK_LOG.md';self.log.write_text('Old log text\n'*20)
        names=['work-proposer','work-integrator','branch-proposer','reviews-integrator','qa-execution']
        point={'kind':'item','line':'neutral-coordination','incarnation':'delivery-before-native',
            'bindings':[{'target':str(self.catalog),'path':['assignments',{'field':'id','value':'one'}]}],
            'resources':[],'protected':['id','owner','history','unknown'],'writable':['state']}
        cfg['local_integration']={'max_inflight':8,'points':{'one':point},'tasks':{t:{'capacity':5,'discovery_batch':4,
            'points':['one'] if t.startswith('work-') else [],'authority':'Fictional genuine delegated routine scope',
            'method':cfg['tasks'][t]['templates'][0]} for t in names}}
        self.file_scope={'prefix':'known:','member_field':'id','point':{**copy.deepcopy(point),
            'bindings':[{'target':str(self.catalog),'path':['assignments']}]}}
        for t in ['work-proposer','work-integrator']:
            cfg['local_integration']['tasks'][t]['lookup_scopes']=[copy.deepcopy(self.file_scope)]
        if self._testMethodName=='test_exact_template_provenance_and_identical_continuation':
            y=copy.deepcopy(self.file_scope);y['point']['bindings'][0]['path']=['private-selected-parent']
            d=json.loads(self.catalog.read_text());d['private-selected-parent']=[{'id':'y','state':'secret'}];self.catalog.write_text(encode(d))
            cfg['local_integration']['tasks']['work-integrator']['lookup_scopes'].append(y)
        wi=cfg['tasks']['work-integrator']
        wi.update(effects='owner-reconcile',sandbox='workspace-write',routine_completion={
            'kind':'catalog-bounded-log-v1','targets':[str(p) for p in self.peers]+[str(self.log)],
            'bounded_log':{'target':str(self.log),'max_lines':12,'max_bytes':8192,'max_entry_bytes':16384}})
        wi['effect_authority'].update(operations=['read-reports','write-role-records'],
            write_roots=[str(p) for p in self.peers]+[str(self.log)])
        cfg['deadlines']['task']=30
        return cfg

    async def asyncSetUp(self):
        from coordinator_runtime.board import Board, module_at
        from coordinator_runtime.store import Store
        self.area=Path('/fixtures')/self._testMethodName/ident();self.area.mkdir(parents=True)
        cfg=config_at(self.area)
        shared=cfg['roles']['Work']['board_id']
        for role in cfg['roles'].values():role['board_id']=shared
        cfg['software_delegation']={'grantor':cfg['roles']['Work']['owner'],
            'authority':'Fictional user delegates bounded roles to genuine fictional Work issuer','boundary':'new-journal-only'}
        cfg['delivery']={'recipients':{r:{'session':v['owner'],'profile':v['profile'],'board_role':v['board_role']} for r,v in cfg['roles'].items()}}
        for t in cfg['tasks'].values():t.update(delivery_required=True,allowed_handoffs=list(cfg['roles']))
        cfg['tasks']['reviews-integrator']['publish_internal_results']=True
        self.config=self.fixture_config(cfg,self.area);validate_config(self.config)
        substrate=module_at(cfg['board_library'],'board_store');catalog=module_at(cfg['board_library'],'catalog')
        home=Path(cfg['board_home'])
        with catalog.catalog(home) as cat:
            entry=catalog.create(cat,home,'cutover475','Owned fictional SDK fixture',board_id=shared,temporary_test=True)
        self.path=Path(entry['db_path'])
        with substrate.database(str(self.path)) as conn:
            substrate.bind_board(conn,shared,initialize=True)
            for selected in cfg['roles'].values():
                args=substrate.parser().parse_args(['register','--session',selected['owner'],'--role',selected['board_role'],
                    '--route','managed','--profile',selected['profile']])
                with software.fixture_actor(substrate,selected['owner']):substrate.register(conn,args)
        self.store=Store(cfg);self.addCleanup(self.store.close)
        self.boards={r:Board(cfg,r) for r in cfg['roles']}
        for role,b in self.boards.items():
            with software.fixture_actor(b.store,cfg['software_delegation']['grantor']):
                grant=b.grant_software(self.store,cfg['software_delegation']['authority'])
            self.store.enroll(role,grant)
            self.store.reconcile_legacy(role,cfg['roles'][role]['owner'],
                {'collector':'Fictional original fixture custodian','evidence':['No historical debt in fixture'],'remaining_holds':[]})
        self.now=100000.;self.store.clock=lambda:self.now
        # All-five hot fixture pool. Nothing under an actual profile is mounted.
        Path(self.config['execution_pool_routes']).write_text('[rotation]\nstate_dir = '+encode(str(self.area/'pool-state'))+
            '\n[providers.codex]\npool = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n'+
            'manual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n')
        for role,b in self.boards.items():
            with software.fixture_actor(b.store,self.config['roles'][role]['owner']):
                b.revoke(self.store.enrollment(role)['grant_id'])
        with self.store.tx():self.store.db.execute('UPDATE enrollments SET intake=0')
        self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for b in self.boards.values():b.runtime=self.store
        self.selection={'basis':processing.basis(self.store,self.boards,future_only=True),
            'authority':'Fictional genuine Work source-only processing selection','retained_events':[],
            'recover_controls':{},'future_intake':True,'tasks':list(self.config['tasks']),
            'metadata_lookup':{'tasks':list(self.config['local_integration']['tasks']),
                'authority':'Fictional bounded metadata lookup; no owner consent/effects','max_points':16,'max_bytes':60000},
            'work_coordination':{'authority':'Fictional independent Work coordination','tasks':['work-proposer','work-integrator'],
                'source_roles':['Branch','Reviews','QA']},
            'max_shared_rows':1000,'max_shared_payload_bytes':1048576,'max_runtime_rows':100,
            'service':{'max_inflight':8,'reviews':{},'legacy_resources':{}}}
        self.selection_config(self.selection)
        with software.fixture_actor(self.boards['Work'].store,self.config['roles']['Work']['owner']):
            self.key=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.key,self.boards)
        self.initial={};self.choices={};self.hints={};self.calls=[];self.task_hook=None;self.after_snapshot=None
        self.dispatch=processing.ProcessingDispatcher(self.store,SimpleNamespace(run=self.model),self.boards)

    def selection_config(self, selection):
        pass

    async def asyncTearDown(self):
        (self.area/'account.json').write_text(encode({'calls':[{k:v for k,v in c.items() if k!='prompt'} for c in self.calls],
            'errors':self.store.rows('SELECT * FROM operational_errors'),
            'attempts':self.store.rows('SELECT id,kind,state,begin,ended,exit,collected,error FROM attempts'),
            'tools':self.store.rows('SELECT record FROM ordinary_tool_records')}))
        self.assertFalse(self.dispatch.active,'every owned coroutine must be collected')

    def post(self,text='Existing work one',role='Work',package=None,body=None,topic='fictional475'):
        b=self.boards[role];author=self.config['roles']['Work']['owner']
        args=['post','--session',author,'--to',self.config['roles'][role]['owner'],'--kind','proposal',
            '--topic',topic,'--text',encode(body) if body is not None else text]
        if package:args+=['--ref',package]
        args=b.store.parser().parse_args(args)
        with b.opened() as conn:
            with software.fixture_actor(b.store,author):seq=b.store.post(conn,args)
            e=b._event(conn,{'seq':seq,'notification_id':None},b._grant(conn,self.store),self.store)
        self.store.ingest(e)
        return e

    async def drain(self):
        while self.dispatch.active:await asyncio.gather(*list(self.dispatch.active))

    async def phase(self,name):
        getattr(self.dispatch,name)();await self.drain()

    async def classify(self,e,task):
        self.initial[e['id']]=task
        for _ in range(12):
            await self.phase('schedule_classifications')
            if self.store.one('SELECT state FROM events WHERE id=?',(e['id'],))['state']=='queued':return
        self.fail('source did not reach durable queued responsibility')

    async def mapping(self,e):
        with patch.object(self.dispatch,'schedule_job',lambda:None):
            for _ in range(8):
                await self.dispatch.tick();await self.drain()
                r=self.store.input_resolution(e['id'])
                if r:return r
        self.fail('no mapping: '+encode(self.store.rows('SELECT * FROM operational_errors')))

    async def model(self,store,attempt,prompt,spec,schema):
        a=store.attempt(attempt)
        self.calls.append({'attempt':attempt,'kind':a['kind'],'event':a['event'],'prompt':prompt,'bytes':len(prompt.encode()),'profile':a['profile']})
        store.begin(attempt,{'fictional475_model_transport':True});store.session(attempt,ident())
        if a['kind']=='classifier':
            e=store.routing_event(a['event']);r=e.get('owner_resolution')
            answer={'event_id':e['id'],'task':r['receipt']['task'] if r else self.initial.get(e['id'],e['allowed_tasks'][0]),
                'package':e.get('package'),'reason':'Fictional source-grounded LOW choice'}
        elif a['kind']=='input-locator':
            req=json.loads(store.one('SELECT request FROM input_locators WHERE attempt=?',(attempt,))['request'])
            hints={t:{k:self.hints.get(a['event'],['one']) for k in v['scopes']} for t,v in req.items()}
            answer={'semantic':'DONE','summary':'Fictional source stable ID hints, no existence/revision/Work decision',
                'decision_json':encode({'hints':hints})}
            self.assertIsNone(store.input_resolution(a['event']))
        elif a['kind']=='input-mapping':
            snaps=json.loads(store.one('SELECT snapshot FROM input_lookups WHERE attempt=?',(attempt,))['snapshot'])
            task=next(iter(snaps));snap=snaps[task]
            request=self.choices.get(a['event'])
            if request is None:request={'state':'known','reads':list(snap['points']),'writes':[]}
            if callable(request):request=request(snap)
            answer={'semantic':'DONE','summary':'Fictional Work meaning grounded in authentic preceding observation',
                'decision_json':encode({'task':task,'integration':request,'reason':'Fictional specific-work interpretation',
                    'evidence':['original fixture source '+a['event']],'remaining_obligations':[]})}
            if self.after_snapshot:self.after_snapshot(snap)
        elif a['kind']=='task':
            job=store.job(a['job']);category='consolidated' if job['role']=='Reviews' or job['phase']=='execution' else 'qualification' if job['phase']=='cleanup' else 'complete'
            answer={**result(category=category),'handoffs':[],'no_handoff_reason':'Fictional owned local result; no omitted required handoff',
                'completion':{'version':1,'local':'ready','tools':[],'failures':[],'unknowns':[],
                    'integration_steps':[{'step':s,'evidence':'Fictional independent expected '+s} for s in local.STEPS]}}
            if job['role']=='Reviews':
                answer['findings'].append({'source':'original-review','full':store.event(json.loads(job['members'])[0]['event'])['body']})
            if self.task_hook:self.task_hook(job,attempt,prompt,answer)
        else:raise AssertionError('unexpected model kind '+a['kind'])
        items=[{'id':'fictional-staging-tool','exit_code':0,'status':'completed'}] if a['job'] and publication.stages(store,attempt) else []
        return {'exit':0,'result':answer,'capture':'complete','cleanup':'done','error':None,
            'detail':{'tool_completion':{'complete':True,'items':items,'nonzero_completions':[],'unknown_types':[]}}}

    async def test_exact_template_provenance_and_identical_continuation(self):
        # Different allowed parents in the SAME permitted file, equal prefixes.
        # The second task selects only X; an A/Y observation must not confer Y.
        e=self.post();await self.classify(e,'work-integrator')
        self.choices[e['id']]=lambda snap:{'state':'known','reads':[next(k for k,p in snap['points'].items()
            if p['definition']['bindings'][0]['path'][0]=='private-selected-parent')],'writes':[]}
        r=await self.mapping(e);key=r['receipt']['integration']['reads'][0]
        self.assertNotIn(key,local.allowed_points(self.store,'work-proposer'))
        self.assertIn(key,local.allowed_points(self.store,'work-integrator'))
        # Identical selected X shares X, regardless of a longer overlapping Y prefix.
        target=self.post('X continuation');await self.classify(target,'work-integrator')
        self.choices[target['id']]=lambda snap:{'state':'known','reads':[next(k for k,p in snap['points'].items()
            if k!='one' and p['definition']['bindings'][0]['path'][-1]=={'field':'id','value':'related'})],'writes':[]}
        r=await self.mapping(target);self.assertIn(r['receipt']['integration']['reads'][0],local.allowed_points(self.store,'work-proposer'))

    async def test_old_unheld_and_unknown_birth_excluded_before_payload(self):
        old=self.post('old retained source');await self.classify(old,'work-integrator')
        missing=self.post('unknown logical birth');await self.classify(missing,'work-integrator')
        # Adversarial ended fixture rows: preserve payload/queue/classifier, alter
        # only the selection frontier and missing position, never renew a birth.
        selection=json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.key,))['selection'])
        selection['basis']['event_boundary']=processing.source_boundary(self.store)
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',(encode(selection),self.key))
        self.store.db.execute('DELETE FROM processing_source_positions WHERE event=?',(missing['id'],))
        before=self.store.rows('SELECT id,hash,payload,classifier FROM events')
        original=self.store.event
        def sentinel(key):
            if key in {old['id'],missing['id']}:raise AssertionError('excluded old body acquired')
            return original(key)
        with patch.object(self.store,'event',side_effect=sentinel):
            self.assertIsNone(lookup.claim(self.store))
        self.assertEqual(before,self.store.rows('SELECT id,hash,payload,classifier FROM events'))

    async def test_execute_entry_revocation_collects_truthful_no_start(self):
        e=self.post();await self.classify(e,'work-integrator');claimed=lookup.claim(self.store)
        self.assertIsNotNone(claimed)
        before=self.store.one('SELECT starts FROM processing_capabilities WHERE id=?',(self.key,))['starts']
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.now,self.key))
        with patch.object(self.store,'event',side_effect=AssertionError('revoked startup must not reacquire source')):
            await lookup.execute(self.dispatch,*claimed)
        row=self.store.attempt(claimed[1]);self.assertEqual(row['state'],'not-started')
        self.assertIsNone(row['begin']);self.assertIsNone(row['ended']);self.assertIsNone(row['exit']);self.assertIsNotNone(row['collected'])
        self.assertEqual(before,self.store.one('SELECT starts FROM processing_capabilities WHERE id=?',(self.key,))['starts'])
        self.assertFalse(any(c['attempt']==claimed[1] for c in self.calls))

    async def test_candidate_authority_refusal_does_not_starve_sibling(self):
        # The real receiving-intent composition is exercised by Mixed below.
        # Here the same per-candidate failure is held at the actual Access.event
        # boundary; no mapper implementation/SQL/scheduler is patched.
        bad=self.post('earlier bad');await self.classify(bad,'work-integrator')
        self.now += 1
        good=self.post('later good');await self.classify(good,'work-integrator')
        original=self.store.processing.event
        def refused(e):
            if e['id']==bad['id']:raise Refusal('held invalid fictional receiving grant')
            return original(e)
        with patch.object(self.store.processing,'event',side_effect=refused):
            with patch.object(self.dispatch,'schedule_job',lambda:None):
                await self.dispatch.tick();await self.drain()
        self.assertIsNotNone(self.store.input_resolution(good['id']))
        self.assertIsNone(self.store.input_resolution(bad['id']))
        self.assertTrue(self.store.one('SELECT active FROM operational_errors WHERE subject=?',(bad['id'],))['active'])


class Scale(Cutover):
    def fixture_config(self,cfg,area):
        cfg=super().fixture_config(cfg,area)
        # Fictional retained-journal capacity selected at construction, not an
        # actual runtime/configuration change. The 100MB adverse run is retained.
        # Source and model-context caps are unchanged; publication needs room
        # for its original snapshots/stages/custody, beyond the lookup context.
        cfg['limits']['max_bytes']=256*1024**2
        # Three realistic 6–10 MiB mixed roots; 1053 string id/state assignments.
        # Large unrelated history is purposefully absent from model context.
        data=json.loads(self.catalog.read_text());data['assignments'] += [
            {'id':'work-'+str(i),'state':'running','history':['unrelated retained history '+('x'*9500)]}
            for i in range(1050)]
        self.catalog.write_text(encode(data))
        for p in [self.peers[2],self.peers[3]]:
            d=json.loads(p.read_text());d['mixed-large-nonwork']=['kept-'+('z'*7000) for _ in range(1000)]
            p.write_text(encode(d))
        li=cfg['local_integration'];li['points']={}
        scopes=[]
        for p in [self.catalog,self.peers[2],self.peers[3]]:
            s=copy.deepcopy(self.file_scope);s['query']=True;s['prefix']='known:'+p.stem+':'
            s['point']['bindings']=[{'target':str(p),'path':['assignments' if p==self.catalog else 'records']}]
            scopes.append(s)
        for t in ['work-proposer','work-integrator']:
            li['tasks'][t]['points']=[];li['tasks'][t]['lookup_scopes']=copy.deepcopy(scopes)
        return cfg

    async def test_targeted_large_sources_related_views_seven_semantics_and_burst(self):
        self.assertEqual(len(json.loads(self.catalog.read_text())['assignments']),1053)
        self.assertTrue(all(6*1024**2 < p.stat().st_size < 11*1024**2 for p in [self.catalog,self.peers[2],self.peers[3]]))
        original={str(p):p.read_bytes() for p in self.peers};old_log=self.log.read_bytes()
        e=self.post('Specific work one; include related work related')
        self.hints[e['id']]=['one','related']
        self.choices[e['id']]=lambda snap:{'state':'known',
            'reads':[k for k,v in snap['points'].items() if v['definition']['bindings'][0]['path'][-1]['value']=='related'],
            'writes':[k for k,v in snap['points'].items() if v['definition']['bindings'][0]['path'][-1]['value']=='one']}
        await self.classify(e,'work-integrator')
        self.dispatch.receipts();ack=self.store.one('SELECT ack_receipt FROM events WHERE id=?',(e['id'],))['ack_receipt']
        birth=self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(e['id'],))
        r=await self.mapping(e)
        self.assertIsNotNone(self.store.one('SELECT hints FROM input_locators WHERE event=?',(e['id'],))['hints'])
        self.assertEqual(len(r['receipt']['integration']['reads']),3);self.assertEqual(len(r['receipt']['integration']['writes']),3)
        await self.classify(e,'work-integrator')
        def stage(job,attempt,prompt,answer):
            # Actual Work decision reads the service's current selected values
            # and revision BEFORE its proposal. No full catalog model package.
            basis=json.loads(self.store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))['basis'])
            self.assertEqual(len(basis['observed_values']),6)
            self.assertIn('observed_values',prompt);self.assertNotIn('unrelated retained history',prompt)
            for target,path in publication.stages(self.store,attempt).items():
                if target.endswith('.json'):
                    d=json.loads(Path(path).read_text());arr=d['assignments' if target==str(self.catalog) else 'records']
                    next(v for v in arr if v['id']=='one')['state']='reviewed'
                    Path(path).write_text(encode(d))
                elif target==str(self.log):Path(path).write_text('Work one reviewed; related preserved\n')
                else:Path(path).write_text('Work one reviewed\n'+Path(target).read_text())
        self.task_hook=stage
        await self.phase('schedule_job')
        self.assertEqual(len(self.store.rows("SELECT * FROM file_publications WHERE state='published'")),7,
            encode(self.store.rows('SELECT id,state,hold_reason FROM jobs')))
        for p in [self.catalog,self.peers[2],self.peers[3]]:
            before=json.loads(original[str(p)]);after=json.loads(p.read_text());key='assignments' if p==self.catalog else 'records'
            expected=copy.deepcopy(before);next(v for v in expected[key] if v['id']=='one')['state']='reviewed'
            self.assertEqual(after,expected)
        for p in [self.peers[1],self.peers[4],self.peers[5]]:
            self.assertEqual(p.read_bytes(),b'Work one reviewed\n'+original[str(p)])
        self.assertTrue(self.log.read_bytes().endswith(old_log))
        self.assertEqual(self.store.one('SELECT ack_receipt FROM events WHERE id=?',(e['id'],))['ack_receipt'],ack)
        self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(e['id'],)),birth)
        # A small subsequent burst must not union earlier derived observations.
        for member in ['related','unrelated','one']:
            source=self.post('Specific work '+member);self.hints[source['id']]=[member]
            await self.classify(source,'work-proposer');await self.mapping(source)
            snap=json.loads(self.store.one('SELECT snapshot FROM input_lookups WHERE event=?',(source['id'],))['snapshot'])['work-proposer']
            self.assertEqual(len(snap['points']),3)
            self.assertTrue(all(p['definition']['bindings'][0]['path'][-1]['value']==member for p in snap['points'].values()))
        self.assertTrue(all(c['bytes'] < 60000 for c in self.calls))
        self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'),[])


class FictionalNative:
    """Fresh run generated at opening, never a preminted context/owner."""
    def __init__(self):self.run=None;self.calls=[]
    async def call(self,runtime,attempt,policy,context,directory,text,commands,opening=False,close=False):
        if opening:
            assert context['run'] is None and self.run is None
            self.run=ident();runtime.begin(attempt,{'fictional475_native_transport':True})
        assert self.run
        n=len(self.calls);self.calls.append({'opening':opening,'run':self.run,'context':copy.deepcopy(context)})
        receipt={'class':'answered','run':self.run,'handle':context['handle'],
            'turn':{'input':n,'admitted':True,'answer_present':True,'linked_messages':1,'ack':{'message_id':'fictional-'+str(n)},
                'turn_end':{'event':'turn-end','input':n,'stop_reason':'end_turn'},'root_ended':None,'refused':None,'rejected':None,'ref':'fictional-ref'},
            'transport':{'errors':[],'attached':{'frontdoor':'attached','run':self.run,'backlog_dropped_total':0,'interrupted_records_total':0}},
            'collection':{'errors':[],'stdout_eof':True,'stderr_eof':True,'exit':0}}
        answer={'semantic':'DONE','summary':'Fictional Source observation, no decision','report':'FULL-FICTIONAL-SOURCE475-'+str(n),
            'history_entry':'Original bounded fictional history '+str(n),'stage':'architecture' if opening else 'complete',
            'coverage':{'families':{f:'partial' for f in reviews.FAMILIES},'core_files_not_read':['unread-fixture'],
                'observations':[{'id':'fictional475-'+str(n)}],'answered_ids':[],'limits':['No real Source efficacy/native protocol qualification']}}
        return 0,receipt,encode(answer)


class Mixed(Cutover):
    compatibility = False
    def git(self,*args):
        cmd=['/usr/bin/git','-c','gc.auto=0','-c','maintenance.auto=false','-C',str(self.repo),*args]
        r=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'})
        with (self.repo.parent/'git-ENDs.jsonl').open('a') as f:f.write(encode({'argv':cmd,'END':r.returncode,'stderr':r.stderr})+'\n')
        self.assertEqual(r.returncode,0,r.stderr);return r.stdout.strip()

    def native_scope(self,kind):
        b={'native':kind,{'branch':'id','review':'component','execution':'package'}[kind]:'$source'}
        if kind=='execution':b['task']='qa-execution'
        return {'prefix':'native-'+kind+':','member_field':None,'point':{'kind':'item','line':'neutral-delivery',
            'incarnation':'delivery-before-native','bindings':[b],'resources':[],'protected':[],'writable':[]}}

    def fixture_config(self,cfg,area):
        cfg=super().fixture_config(cfg,area)
        self.repo=area/'repo';self.repo.mkdir();self.git('init','--initial-branch=source')
        self.git('remote','add','origin','https://example.invalid/fictional475.git')
        (self.repo/'source.txt').write_text('independent fixture source\n')
        self.git('add','source.txt');self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
            '-c','commit.gpgsign=false','commit','-m','Owned fictional source')
        self.head=self.git('rev-parse','HEAD');self.git('branch','destination')
        self.procedure=area/'procedure.md';self.procedure.write_text('Independent intended fixture: read frozen source, execute runner once, verify marker; accept separately.\n')
        li=cfg['local_integration'];li['points']={}
        for t in ['work-proposer','work-integrator']:
            li['tasks'][t]['points']=[]
            s=copy.deepcopy(self.file_scope);s['query']=True
            li['tasks'][t]['lookup_scopes']=[s]+[self.native_scope(k) for k in ['branch','review','execution']]
            if self.compatibility:
                li['tasks'][t]['lookup_scopes']=[self.native_scope(k) for k in ['branch','review']]
        li['tasks']['branch-proposer']['lookup_scopes']=[self.native_scope('branch')]
        li['tasks']['reviews-integrator']['lookup_scopes']=[self.native_scope(k) for k in ['branch','review']]
        li['tasks']['qa-execution']['lookup_scopes']=[self.native_scope('execution')]
        # Software cleanup is explicitly NARROWED, not exempt from admission.
        # It retains ordinary consolidation, independently scoped file output.
        for t in ['qa-execution','branch-integrator']:
            cfg['tasks'][t].update(require_package_scope=True,scope_roots=[str(area)])
        cfg['tasks']['qa-execution'].update(effects='owner-reconcile',network=False)
        cfg['tasks']['qa-execution']['effect_authority']['operations']=['execute-admitted-qa']
        cfg['tasks']['qa-cleanup']['responses']['qualification']=['branch-integrator']
        cfg['tasks']['qa-cleanup']['software_handoffs']={}
        cfg['tasks']['qa-execution']['software_handoffs']={'Work':['work-proposer']}
        cfg['tasks']['branch-proposer']['software_handoffs']={'Work':['work-proposer'],'QA':['qa-execution']}
        cfg['tasks']['reviews-integrator']['software_handoffs']={'Work':['work-proposer']}
        self.cleanup_file=area/'cleanup'/'summary.json';self.cleanup_file.parent.mkdir();self.cleanup_file.write_text('{}')
        cfg['tasks']['qa-cleanup'].update(effects='owner-reconcile',sandbox='workspace-write',
            routine_completion={'kind':'file-witness','targets':[str(self.cleanup_file)]})
        cfg['tasks']['qa-cleanup']['effect_authority'].update(operations=['read-reports','consolidate-reports','write-role-records'],
            write_roots=[str(self.cleanup_file.parent)])
        from coordinator_runtime import configuration
        if self.compatibility:
            cfg['tasks']['qa-cleanup'].update(require_package_scope=True,scope_roots=[str(area)])
        else:
            configuration.apply_scope_options(copy.deepcopy(cfg),cfg,{'package_scoped_cleanup':['qa-cleanup']})
        self.qa_task_scopes=self.qa_scopes(cfg,area)
        return cfg

    def selection_config(self,s):
        history=self.store.home/'review-history'/'fresh-component'
        self.method=self.area/'source-method.md';self.method.write_text('Fictional method input; explicit nine partial families, architecture then remaining, whole reports/history.\n')
        s['service']['reviews']={'reviews-proposer':{'caller':'/usr/bin/true','caller_sha256':sha('/usr/bin/true'),
            'routes':{p:'fictional-'+p for p in self.config['profiles']},'deadline':30,'method':str(self.method),
            'method_files':reviews.method_files(str(self.method)),'components':{'fresh-component':{'repository':str(self.repo),
                'origin':'https://example.invalid/fictional475.git','paths':['source.txt'],'history':str(history),
                'authority':'Fictional independently selected read-only primary Source scope'}}}}
        s['software_admission']={'authority':'Fictional genuine Work admits selected future QA and separately scoped receiving', 'max_packages':2,
            'scopes':{'fictional475':{'submitters':[self.config['roles']['Work']['owner']], 'package_prefix':'qa475-',
                'task_scopes':self.qa_task_scopes,'evidence':'Fictional exact execution, narrower cleanup and separate Branch receiving authority'}}}

    def qa_scopes(self,cfg,area):
        output=area/'qa-output';output.mkdir()
        runner=area/'runner';readback=area/'readback'
        runner.write_text('#!/usr/bin/python3 -B\nfrom pathlib import Path\nassert Path("source.txt").read_text()=="independent fixture source\\n"\nPath('+repr(str(output/'marker'))+').write_text("source actually executed")\n')
        readback.write_text('#!/usr/bin/python3 -B\nfrom pathlib import Path\nassert Path('+repr(str(output/'marker'))+').read_text()=="source actually executed"\nprint("VERIFIED475")\n')
        runner.chmod(0o700);readback.chmod(0o700)
        acceptor=cfg['roles']['Work']['owner']
        p={'kind':'local-qa','git':'/usr/bin/git','git_sha256':sha('/usr/bin/git'),'repository':str(self.repo),
            'source_ref':'refs/heads/source','source_head':self.head,'procedure_sha256':sha(self.procedure),
            'resources':[{'key':'fictional-qa-resource475','owner':acceptor,'authority':'Fictional bounded independent resource lease','expires':103600.}],
            'acceptor':acceptor,'acceptance_authority':'Fictional Work selected independent intended outcome owner',
            'timeout':20,'max_output':32768,'command':{'argv':[str(runner)],'executable_sha256':sha(runner),'stdout':None},
            'readback':{'argv':[str(readback)],'executable_sha256':sha(readback),'stdout':'VERIFIED475\n'},'known_exits':[0,1],
            'source_capture':{'bwrap':'/usr/bin/bwrap','sha256':sha('/usr/bin/bwrap'),'max_bytes':1048576,'max_files':100}}
        return {'qa-execution':{'cwd':str(self.repo),'read_roots':[str(area)],'write_roots':[str(output)],
            'network':False,'procedure':str(self.procedure),'resource_evidence':['Fictional execution resource permission'],'ordinary_effects':p},
            'qa-cleanup':{'cwd':str(self.repo),'read_roots':[str(self.repo),str(output),str(self.procedure)],
            'write_roots':[str(self.cleanup_file.parent)],'network':False,'procedure':str(self.procedure),
            'resource_evidence':['Separate narrow fictional cleanup authority; no execution/resource access']},
            'branch-integrator':{'cwd':str(self.repo),'read_roots':[str(self.repo),str(self.procedure),str(self.cleanup_file.parent)],
                'write_roots':[],'network':False,'procedure':str(self.procedure),'resource_evidence':['Separate fictional receiving scope only']}}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.transport=FictionalNative();self.dispatch=service.Dispatcher(self.store,self.boards,SimpleNamespace(run=self.model),self.transport)
        self.branch='fictional-accepted-branch475';owner=self.config['roles']['Work']['owner']
        scopes={t:{'cwd':str(self.repo),'read_roots':[str(self.area)],'write_roots':[],'network':False,
            'procedure':str(self.procedure),'resource_evidence':['Fictional original Branch owner scope'],'branch_binding':self.branch}
            for t in ['branch-proposer','reviews-proposer','reviews-integrator','work-proposer','work-integrator']}
        scopes.update(self.qa_task_scopes)
        self.store.admit('native-pkg',self.config['roles']['Branch']['owner'],{'task_scopes':scopes})
        branches.register(self.store,owner,{'id':self.branch,'repository':str(self.repo),'origin':'https://example.invalid/fictional475.git',
            'ref':'refs/heads/destination','incarnation':'actual-fictional-ref-life','scope':'native-pkg','root':owner,
            'authority':'Fictional member assignment separate from software/controller/worker'})
        branches.accept(self.store,self.branch,owner,'Fictional actual registered member accepts its bounded branch')

    async def model(self,store,attempt,prompt,spec,schema):
        a=store.attempt(attempt)
        if a['kind']=='input-locator':
            e=store.event(a['event']);self.hints[a['event']]=['one'] if e['kind']=='board' and not e.get('source_delivery') else []
        if a['kind']=='input-mapping':
            self.choices[a['event']]=lambda snap:{'state':'known','reads':list(snap['points']),'writes':[]}
        return await super().model(store,attempt,prompt,spec,schema)

    async def ticks(self,predicate,n=24):
        for _ in range(n):
            await self.dispatch.tick();await self.drain()
            if predicate():return
        self.fail('normal tick target not reached: '+encode({'jobs':self.store.rows('SELECT id,task,state,hold_reason FROM jobs'),
            'errors':self.store.rows('SELECT * FROM operational_errors'),'runtime':self.dispatch.runtime_errors}))

    async def test_bound_source_open_history_reviews_work_and_mixed_inbox(self):
        configuration=digest(self.config);key=self.key
        packet={'component':'fresh-component','origin':'https://example.invalid/fictional475.git','base':self.head,'head':self.head,'previous':None,'answered_ids':[]}
        e=self.post(role='Reviews',package='native-pkg',body={'review':packet,'branch_binding':self.branch})
        self.initial[e['id']]='reviews-proposer'
        await self.ticks(lambda:self.store.one("SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt WHERE j.task='work-proposer' AND a.collected IS NOT NULL"))
        self.assertEqual(len(self.transport.calls),2)
        self.assertEqual([c['opening'] for c in self.transport.calls],[True,False])
        self.assertTrue(all(c['run']==self.transport.run for c in self.transport.calls))
        source=self.store.one("SELECT * FROM jobs WHERE task='reviews-proposer'");attempt=self.store.attempt(source['active_attempt'])
        self.assertEqual(attempt['session'],self.transport.run);self.assertEqual(attempt['capture'],'complete')
        self.assertEqual(json.loads(attempt['detail'])['software_authority']['admission_hash'],digest(self.store.one('SELECT * FROM admissions WHERE package=?',('native-pkg',))))
        self.assertTrue(self.store.rows("SELECT * FROM review_history_commits WHERE state='applied'"))
        for task in ['reviews-integrator','work-proposer']:
            j=self.store.one('SELECT * FROM jobs WHERE task=?',(task,))
            prompt=next(c['prompt'] for c in self.calls if c['attempt']==j['active_attempt'])
            self.assertIn('FULL-FICTIONAL-SOURCE475-0',prompt);self.assertIn('FULL-FICTIONAL-SOURCE475-1',prompt)
        # Same config admits a Branch source and ordinary Work input; review and
        # execution templates are non-applicable, never global dependencies.
        b=self.post('Bound Branch return',role='Branch',package='native-pkg')
        self.initial[b['id']]='branch-proposer'
        await self.classify(b,'branch-proposer');await self.mapping(b)
        bp=self.store.input_resolution(b['id'])['receipt']['integration']['reads'];self.assertTrue(bp)
        await self.classify(b,'branch-proposer')
        w=self.post('Ordinary Work about one');await self.classify(w,'work-proposer');await self.mapping(w)
        wp=self.store.input_resolution(w['id'])['receipt']['integration']['reads'];self.assertTrue(wp)
        self.assertTrue(all('target' in local.point_definitions(self.store)[k]['bindings'][0] for k in wp))
        # Native lifetime != fixed delivery namespace; replaced run refuses.
        point=next(json.loads(r['definition']) for r in self.store.rows('SELECT * FROM local_lookup_points') if r['point'].startswith('native-review:'))
        self.assertEqual(point['incarnation'],'delivery-before-native');self.assertEqual(point['native_incarnations'],[self.transport.run])
        component=point['bindings'][0]['component'];self.store.db.execute('UPDATE review_contexts SET run=? WHERE component=?',(ident(),component))
        consumer=self.store.one("SELECT * FROM jobs WHERE task='work-proposer'")
        with self.assertRaisesRegex(Refusal,'incarnation'):local.point_value(point,{},store=self.store,job=consumer)
        self.assertEqual(digest(self.config),configuration);self.assertEqual(self.key,key)

    async def test_software_qa_execution_independent_work_acceptance_cleanup_qualification(self):
        # Scope and software-admission templates are selected before the source.
        # The controller/worker/software actor are different real fixture UUIDs
        # from the Work owner, who is explicitly selected as independent acceptor.
        output=self.area/'qa-output'
        acceptor=self.config['roles']['Work']['owner']
        tasks=['qa-execution','qa-cleanup','work-proposer']
        prospective.select(self.store,acceptor,{'configuration':digest(self.config),'authority':'Fictional selected ordinary QA resources and cleanup',
            'expires':self.now+3600,'grants':{r:self.store.enrollment(r)['grant_id'] for r in ['QA','Work']},'tasks':{
                t:{'task_hash':digest(self.config['tasks'][t]),'software_handoffs':self.config['tasks'][t].get('software_handoffs',{}),'ordinary_effects':t=='qa-execution'} for t in tasks},
            'processing_capability':self.key})
        e=self.post('Run independent specified fixture','QA','qa475-one');self.initial[e['id']]='qa-execution'
        def cleanup(job,attempt,prompt,answer):
            if job['task']=='qa-execution':
                answer['handoffs']=[{'recipient':'Work','kind':'result','ref':'qa475-one','required':'settled',
                    'text':'Fictional execution report; original tool/effect receipt follows, independent acceptance still required'}]
                answer.pop('no_handoff_reason')
            if job['task']=='qa-cleanup':
                self.assertIn('source actually executed', (output/'marker').read_text())
                self.assertIn('ordinary_effects',prompt)
                self.assertTrue(ordinary.accepted_package(self.store,'qa475-one'))
                Path(publication.stages(self.store,attempt)[str(self.cleanup_file)]).write_text(encode({'package':'qa475-one','status':'qualified','source':self.head}))
        self.task_hook=cleanup
        await self.ticks(lambda:self.store.one('SELECT attempt FROM ordinary_runs'))
        run=self.store.one('SELECT * FROM ordinary_runs');receipt=json.loads(run['receipt'])
        self.assertEqual(run['state'],'reconciled');self.assertEqual((output/'marker').read_text(),'source actually executed')
        self.assertEqual(receipt['outcome']['actual_exit'],0);self.assertFalse(ordinary.accepted_package(self.store,'qa475-one'))
        evidence={'execution_hash':digest(receipt),'rationale':'Independent specified frozen source and marker/readback verified','unknowns':[]}
        for actor in [self.config['actor'],self.store.controller,receipt['worker']]:
            with self.assertRaises(Refusal):await ordinary.accept(self.store,actor,run['attempt'],'accepted',evidence)
        await ordinary.accept(self.store,acceptor,run['attempt'],'accepted',evidence)
        await self.ticks(lambda:self.store.one("SELECT id FROM jobs WHERE task='qa-cleanup' AND state='closed'"))
        cleanup_job=self.store.one("SELECT * FROM jobs WHERE task='qa-cleanup'")
        self.assertTrue(ordinary.qualification_current(self.store,cleanup_job))
        self.assertEqual(json.loads(self.cleanup_file.read_text()),{'package':'qa475-one','status':'qualified','source':self.head})
        # Same fixed Work configuration maps this genuine QA return, and sees
        # only execution metadata, not unrelated branch/reviewer contexts.
        await self.ticks(lambda:self.store.one("SELECT id FROM jobs WHERE task='branch-integrator' AND state='closed'"))
        await self.ticks(lambda:self.store.one("SELECT id FROM jobs WHERE task='work-proposer' AND package='qa475-one'"))
        q=self.store.one("SELECT * FROM processing_admissions WHERE package='qa475-one'")
        self.assertIsNotNone(q);self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'),[])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM qa_package_owners')['n'],1)

    async def test_real_receiving_refusal_keeps_valid_qa_progress(self):
        tasks=['branch-proposer','qa-execution','work-proposer']
        prospective.select(self.store,self.config['roles']['Work']['owner'],{'configuration':digest(self.config),
            'authority':'Fictional actual receiver-specific handoff authority','expires':self.now+3600,
            'grants':{r:self.store.enrollment(r)['grant_id'] for r in ['Branch','QA','Work']},
            'tasks':{t:{'task_hash':digest(self.config['tasks'][t]),'software_handoffs':
                self.config['tasks'][t].get('software_handoffs',{}),'ordinary_effects':t=='qa-execution'} for t in tasks},
            'processing_capability':self.key})
        e=self.post('Branch supplies independent Work and QA duties','Branch','native-pkg')
        await self.classify(e,'branch-proposer');await self.mapping(e);await self.classify(e,'branch-proposer')
        def handoffs(job,attempt,prompt,answer):
            if job['task']=='branch-proposer':
                answer['handoffs']=[{'recipient':r,'kind':'work','ref':'native-pkg','required':'settled',
                    'text':'Fictional genuine '+r+' duty; preserve the exact original result'} for r in ['Work','QA']]
                answer.pop('no_handoff_reason')
        self.task_hook=handoffs
        await self.phase('schedule_job')
        # Establish both production receiving intents and their fresh LOWs,
        # before either mapper is allowed to act. No queue/intent is fabricated.
        with patch.object(self.dispatch,'schedule_input_mappings',lambda:None),patch.object(self.dispatch,'schedule_job',lambda:None):
            await self.ticks(lambda:self.store.one("SELECT COUNT(*) AS n FROM processing_delivery_links l JOIN events e ON e.id=l.event WHERE e.role IN ('Work','QA') AND e.state='queued'")['n']==2)
        rows=self.store.rows("SELECT e.id,e.role,l.delivery FROM processing_delivery_links l JOIN events e ON e.id=l.event WHERE e.role IN ('Work','QA')")
        receivers={r['role']:r for r in rows};w=receivers['Work'];q=receivers['QA']
        original=self.store.event(w['id']);good=self.store.event(q['id'])
        self.assertTrue(self.boards['QA'].receiving_intent(self.store,good))
        with self.boards['Work'].opened() as conn:
            conn.execute("UPDATE coordinator_software_deliveries_v1 SET receiver_grant='forged-owned-Work-grant475' WHERE delivery=?",(w['delivery'],))
        # Deterministically exercise invalid Work BEFORE QA, using scheduling
        # metadata only; preserve both source bodies, birth and original LOWs.
        self.store.db.execute('UPDATE events SET received=? WHERE id=?',(self.now-1,w['id']))
        before=self.store.rows('SELECT id,hash,classifier FROM events WHERE id IN (?,?)',(w['id'],q['id']))
        with patch.object(self.dispatch,'schedule_job',lambda:None):
            await self.dispatch.tick();await self.drain()
        self.assertIsNotNone(self.store.input_resolution(q['id']))
        self.assertIsNone(self.store.input_resolution(w['id']))
        self.assertEqual(self.store.event(w['id']),original)
        self.assertEqual(before,self.store.rows('SELECT id,hash,classifier FROM events WHERE id IN (?,?)',(w['id'],q['id'])))
        self.assertTrue(self.boards['QA'].receiving_intent(self.store,good))

    async def test_five_distinct_first_phase_slots_and_same_package_fence(self):
        original_repo=self.repo
        for i in range(6):
            root=self.area/('slot-'+str(i));root.mkdir();self.repo=root/'repo';self.repo.mkdir()
            self.git('init','--initial-branch=source');(self.repo/'source.txt').write_text('independent fixture source\n')
            self.git('add','source.txt');self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                '-c','commit.gpgsign=false','commit','-m','Separate bounded slot fixture')
            head=self.git('rev-parse','HEAD');output=root/'output';output.mkdir()
            runner=root/'runner';runner.write_text('#!/usr/bin/python3 -B\nfrom pathlib import Path\nassert Path("source.txt").read_text()=="independent fixture source\\n"\nPath('+repr(str(output/'marker'))+').write_text("slot")\n');runner.chmod(0o700)
            readback=root/'readback';readback.write_text('#!/usr/bin/python3 -B\nfrom pathlib import Path\nassert Path('+repr(str(output/'marker'))+').read_text()=="slot"\nprint("SLOT")\n');readback.chmod(0o700)
            scope=copy.deepcopy(self.qa_task_scopes['qa-execution'])
            scope.update(cwd=str(self.repo),read_roots=[str(root),str(self.procedure)],write_roots=[str(output)])
            p=scope['ordinary_effects'];p.update(repository=str(self.repo),source_head=head,
                command={'argv':[str(runner)],'executable_sha256':sha(runner),'stdout':None},
                readback={'argv':[str(readback)],'executable_sha256':sha(readback),'stdout':'SLOT\n'})
            p['resources'][0]['key']='independent-slot-resource-'+str(i)
            package='native-slot-'+str(i)
            self.store.admit(package,self.config['roles']['Branch']['owner'],{'task_scopes':{'qa-execution':scope}})
            e=self.post('Genuine separate first-phase fixture','QA',package,topic='original-owner-slot')
            await self.classify(e,'qa-execution');await self.mapping(e);await self.classify(e,'qa-execution')
        self.repo=original_repo
        jobs=[self.store.reserve() for _ in range(5)]
        self.assertTrue(all(jobs));self.assertEqual(len({j['package'] for j in jobs}),5)
        self.assertIsNone(self.store.reserve(),'sixth first-phase job must retain its queue without a slot')
        duplicate=self.post('Same-package later update','QA',jobs[0]['package'],topic='original-owner-slot')
        await self.classify(duplicate,'qa-execution');await self.mapping(duplicate);await self.classify(duplicate,'qa-execution')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM qa_package_owners')['n'],5)
        self.assertFalse(self.store.rows('SELECT * FROM ordinary_runs'))


class AdmissionComparator(Mixed):
    """698-compatible pre-source config; no locator/new cleanup option needed."""
    compatibility = True

    async def test_native_bound_original_admission_at_execute_entry(self):
        packet={'component':'fresh-component','origin':'https://example.invalid/fictional475.git',
            'base':self.head,'head':self.head,'previous':None,'answered_ids':[]}
        e=self.post(role='Reviews',package='native-pkg',body={'review':packet,'branch_binding':self.branch})
        await self.classify(e,'reviews-proposer');await self.phase('schedule_job')
        job=self.store.one("SELECT * FROM jobs WHERE task='reviews-proposer'")
        attempt=self.store.attempt(job['active_attempt'])
        self.assertEqual(attempt['capture'],'complete',attempt['error'])
        self.assertEqual(len(self.transport.calls),2)
        self.assertEqual(attempt['session'],self.transport.run)
        self.assertTrue(self.store.rows("SELECT * FROM review_history_commits WHERE state='applied'"))


class QueryProtocol(Cutover):
    def fixture_config(self,cfg,area):
        cfg=super().fixture_config(cfg,area)
        cfg['local_integration']['points']={}
        for t in ['work-proposer','work-integrator']:
            p=cfg['local_integration']['tasks'][t];p['points']=[];p['lookup_scopes'][0]['query']=True
        return cfg

    async def test_cleanup_narrowing_refuses_extra_reads_writes_and_execution(self):
        from coordinator_runtime import configuration
        from coordinator_runtime.contracts import scoped_task
        original=copy.deepcopy(self.config);candidate=copy.deepcopy(original)
        directory=self.area/'narrow-cleanup';directory.mkdir()
        task=candidate['tasks']['qa-cleanup'];task['effect_authority']['write_roots']=[str(directory)]
        configuration.apply_scope_options(copy.deepcopy(candidate),candidate,{'package_scoped_cleanup':['qa-cleanup']})
        scope={'cwd':str(self.area),'read_roots':[str(self.area)],'write_roots':[str(directory)],
            'procedure':candidate['tasks']['qa-cleanup']['templates'][0],'resource_evidence':['Fictional independently selected cleanup scope']}
        actual=scoped_task('qa-cleanup',task,{'receipt':encode({'task_scopes':{'qa-cleanup':scope}})})
        self.assertEqual(actual['admitted_scope'],scope)
        for change in [{'read_roots':['/etc']},{'write_roots':[str(self.area)]},{'ordinary_effects':{'kind':'local-qa'}}]:
            with self.assertRaises(Refusal):scoped_task('qa-cleanup',task,{'receipt':encode({'task_scopes':{'qa-cleanup':{**scope,**change}}})})

    async def test_positive_new_candidates_share_central_catalog_comparison_only(self):
        sources=[self.post('Explicit fictional NEW business '+str(i)) for i in range(2)]
        for e in sources:
            self.hints[e['id']]=[];self.choices[e['id']]={'state':'new'}
            self.initial[e['id']]='work-integrator'
        for e in sources:
            await self.classify(e,'work-integrator');await self.mapping(e);await self.classify(e,'work-integrator')
        def compare(job,attempt,prompt,answer):
            context=local.context(self.store,job)
            self.assertEqual(context['basis']['scope']['lane'],'discovery')
            self.assertEqual(len(json.loads(job['members']))+len(context['discovery_neighbors']),2)
            self.assertEqual(len(context['discovery_catalog_scopes']),1)
            self.assertIn(str(self.catalog),context['discovery_catalog_preimages'])
            staged=json.loads(Path(publication.stages(self.store,attempt)[str(self.catalog)]).read_text())
            self.assertEqual([v['id'] for v in staged['assignments']],['one','related','unrelated'])
            # Actual bounded source comparison is a declared semantic seam;
            # no old work is duplicated and no accepted owner is manufactured.
            self.assertIn('NOT an exhaustive catalog',prompt)
            answer['findings']=[{'source':'fictional central comparison','meaning':'Two positive new candidates compared to existing one/related/unrelated; no existing item duplication or accepted ownership'}]
            Path(publication.stages(self.store,attempt)[str(self.log)]).write_text('Two new business proposals compared with selected existing catalog\n')
        self.task_hook=compare
        await self.phase('schedule_job')
        self.assertEqual(len(self.store.rows("SELECT * FROM file_publications WHERE state='published'")),7)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'),[])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM jobs')['n'],1)


    async def test_locator_is_hint_then_current_observation_then_frozen_semantic_basis(self):
        e=self.post('Existing one');await self.classify(e,'work-proposer')
        from coordinator_runtime import custody
        original=custody.read_file
        reads=[]
        def read(path,*args,**kw):
            if str(path)==str(self.catalog):reads.append(str(path))
            return original(path,*args,**kw)
        with patch.object(custody,'read_file',side_effect=read):
            await self.phase('schedule_input_mappings')
            self.assertEqual(reads,[],'locator may not read the backing source')
            self.assertIsNone(self.store.input_resolution(e['id']))
            self.assertEqual(self.store.rows('SELECT * FROM local_lookup_points'),[])
            d=json.loads(self.catalog.read_text());d['assignments'][0]['state']='after-hint';self.catalog.write_text(encode(d))
            def later(snapshot):
                self.assertEqual(next(iter(snapshot['points'].values()))['value'][0]['value']['state'],'after-hint')
                d=json.loads(self.catalog.read_text());d['assignments'][0]['state']='after-semantic-observation';self.catalog.write_text(encode(d))
            self.after_snapshot=later
            await self.phase('schedule_input_mappings')
            self.assertTrue(reads)
        resolution=self.store.input_resolution(e['id']);self.assertIsNotNone(resolution)
        old=copy.deepcopy(resolution['prior']['integration_observation']['packet']['versions'])
        await self.classify(e,'work-proposer')
        def proposal(job,attempt,prompt,answer):
            basis=json.loads(self.store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))['basis'])
            self.assertEqual(basis['scope']['mode'],'reconcile')
            self.assertNotEqual(basis['versions'],old)
            self.assertEqual(next(iter(basis['observed_values'].values()))[0]['value']['state'],'after-semantic-observation')
            self.assertIn('after-semantic-observation',prompt)
        self.task_hook=proposal
        await self.phase('schedule_job')
        self.assertEqual(self.store.input_resolution(e['id'])['prior']['integration_observation']['packet']['versions'],old)

    async def test_unselected_locator_hint_refuses_without_acquisition_or_replay(self):
        e=self.post('No authorized scope for forged hint');await self.classify(e,'work-proposer')
        original=self.model
        async def forged(store,attempt,*args):
            out=await original(store,attempt,*args)
            out['result']['decision_json']=encode({'hints':{'work-proposer':{'unselected-template':['one']}}})
            return out
        self.dispatch.models=SimpleNamespace(run=forged)
        from coordinator_runtime import custody
        read=custody.read_file
        def no_backing(path,*args,**kw):
            if str(path)==str(self.catalog):raise AssertionError('forged query acquired target')
            return read(path,*args,**kw)
        with patch.object(custody,'read_file',side_effect=no_backing):
            await self.phase('schedule_input_mappings')
            before=len(self.calls);await self.phase('schedule_input_mappings');self.assertEqual(before,len(self.calls))
        row=self.store.one('SELECT * FROM input_locators WHERE event=?',(e['id'],))
        self.assertIsNotNone(row['error']);self.assertIsNone(row['hints']);self.assertIsNone(self.store.input_resolution(e['id']))
        self.assertEqual(self.store.rows('SELECT * FROM local_lookup_points'),[])

    async def test_unknown_does_not_become_new_or_acquire_a_catalog(self):
        e=self.post('Existing identity missing');self.hints[e['id']]=[]
        self.choices[e['id']]={'state':'unresolved-existing'}
        await self.classify(e,'work-proposer')
        from coordinator_runtime import custody
        read=custody.read_file
        def no_backing(path,*args,**kw):
            if str(path)==str(self.catalog):raise AssertionError('unknown operand acquired catalog')
            return read(path,*args,**kw)
        with patch.object(custody,'read_file',side_effect=no_backing):await self.mapping(e)
        self.assertIn('unresolved_existing',self.store.input_resolution(e['id'])['prior']['integration_observation']['packet'])
        self.assertIsNone(self.store.reserve());self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'),[])


class FieldViews(QueryProtocol):
    def fixture_config(self,cfg,area):
        cfg=super().fixture_config(cfg,area)
        for t in ['work-proposer','work-integrator']:
            cfg['local_integration']['tasks'][t]['lookup_scopes'][0]['view']=['unknown','null']
        return cfg

    async def test_targeted_field_view_distinguishes_null_absence_and_protection(self):
        e=self.post('Existing one nullable view');await self.classify(e,'work-proposer');await self.mapping(e)
        record=json.loads(self.store.one('SELECT snapshot FROM input_lookups WHERE event=?',(e['id'],))['snapshot'])['work-proposer']
        key,point=next(iter(record['points'].items()))
        self.assertEqual(point['value'],[{'exists':True,'value':None}])
        d=json.loads(self.catalog.read_text());d['assignments'][0]['unknown'].pop('null');self.catalog.write_text(encode(d))
        value=local.point_value(point['definition'],{str(self.catalog):self.catalog.read_bytes()})
        self.assertEqual(value,[{'exists':False,'value':None}])
        self.assertNotEqual(local.version(self.store,key,{str(self.catalog):self.catalog.read_bytes()}),point['version'])
        with self.assertRaises(Refusal):local.validate_delta(None,'forged',point['definition'],point['definition']['bindings'][0])



class NestedTemplates(Cutover):
    def fixture_config(self,cfg,area):
        cfg=super().fixture_config(cfg,area)
        cfg['local_integration']['tasks']['work-integrator']['lookup_scopes'][1]['prefix']='known:nested:'
        return cfg


class AllKinds(Mixed):
    async def test_one_selection_serves_branch_reviews_qa_work_and_cleanup(self):
        key=self.key;configuration=digest(self.config)
        await self.test_bound_source_open_history_reviews_work_and_mixed_inbox()
        await self.test_software_qa_execution_independent_work_acceptance_cleanup_qualification()
        self.assertEqual(self.key,key);self.assertEqual(digest(self.config),configuration)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM processing_capabilities')['n'],1)
        self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'),[])


