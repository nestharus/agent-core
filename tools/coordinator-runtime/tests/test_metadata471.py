"""Owned fictional principals/models/native collection; real SDK and scheduler.

Never an actual native, profile, source collector or acceptance qualification.
Run only inside the positive-mount bwrap harness with private owned fixtures.
"""
import asyncio
import copy
import json
import time
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import patch

from support import config_at, collect, result, ident
import test_software_consumption as software
import test_ordinary_effects as effects
from test_local466 import Ingress
from coordinator_runtime import processing, local_integration as local, routine, publication, ordinary, prospective, branches
from coordinator_runtime.contracts import Refusal, digest, encode, validate_config, scoped_task


class Automatic(unittest.IsolatedAsyncioTestCase):
    post = Ingress.post
    git = effects.OrdinaryEffects.git
    admission = effects.OrdinaryEffects.admission

    async def asyncSetUp(self):
        def configured(path):
            cfg = config_at(path)
            cfg['deadlines']['task']=15
            self.catalog = Path(path)/'catalog.json'
            self.catalog.write_text(encode({'items':{k:{'id':k,'owner':'independent-existing-owner','state':'old'}
                                                       for k in ('a','b','late')}, 'untouched':['keep']}))
            self.peers = [self.catalog]+[Path(path)/p for p in ('assignments.md','register.json','now.json','now.md','root.md')]
            for p in self.peers[1:]:
                p.write_text(self.catalog.read_text() if p.suffix == '.json' else 'Retained peer history\n')
            self.log = Path(path)/'WORK_LOG.md'; self.log.write_text('Retained old log\n'*20)
            cfg['canonical_publication']['library']='/sdk'
            point = {'kind':'item','line':'Main','incarnation':'delivery-one', 'bindings':[{'target':str(self.catalog),'path':['items']}],
                     'resources':[],'protected':['id','owner'],'writable':['state']}
            names = ['work-proposer','work-integrator','qa-execution','branch-proposer','reviews-integrator']
            cfg['local_integration']={'max_inflight':8,'points':{
                k:{**copy.deepcopy(point),'bindings':[{'target':str(p),'path':['items',k]} for p in self.peers if p.suffix=='.json']} for k in ('a','b')},
                'tasks':{t:{'capacity':5,'discovery_batch':4,'points':['a','b'] if t.startswith('work-') else [],
                           'authority':'fictional independent existing selected role scope', 'method':cfg['tasks'][t]['templates'][0]}
                         for t in names}}
            for t in ('work-proposer','work-integrator'):
                cfg['local_integration']['tasks'][t]['lookup_scopes']=[{'prefix':'known:','point':copy.deepcopy(point),'member_field':None}]
            native = {'kind':'item','line':'QA-delivery','incarnation':'stable-delivery',
                      'bindings':[{'native':'execution','package':'$source','task':'qa-execution'}],
                      'resources':[],'protected':[],'writable':[]}
            cfg['local_integration']['tasks']['qa-execution']['lookup_scopes']=[{'prefix':'qa-known:','point':native,'member_field':None}]
            for t in ('branch-proposer','reviews-integrator'):
                cfg['local_integration']['tasks'][t]['lookup_scopes']=[{'prefix':'branch-known:',
                    'point':{**copy.deepcopy(native),'line':'Branch-delivery','bindings':[{'native':'branch','id':'$source'}]},'member_field':None}]
            cfg['tasks']['branch-proposer']['responses']['proposal']=['reviews-integrator']
            cfg['tasks']['branch-proposer']['software_handoffs']={'QA':['qa-execution']}
            for t in ('branch-integrator','qa-execution'):
                cfg['tasks'][t].update(effects='owner-reconcile',require_package_scope=True,scope_roots=[str(path)],network=True)
                cfg['tasks'][t]['effect_authority']['operations']=['execute-admitted-qa' if t=='qa-execution' else 'organize-authorized-refs']
            task=cfg['tasks']['work-integrator']
            task.update(effects='owner-reconcile',sandbox='workspace-write',routine_completion={
                'kind':'catalog-bounded-log-v1','targets':[str(p) for p in self.peers]+[str(self.log)],
                'bounded_log':{'target':str(self.log),'max_lines':12,'max_bytes':8192,'max_entry_bytes':16384}})
            task['effect_authority'].update(operations=['read-reports','write-role-records'],write_roots=[str(p) for p in self.peers]+[str(self.log)])
            return cfg
        with patch.object(software,'config_at',side_effect=configured):
            await software.SoftwareConsumption.asyncSetUp(self)
        self.board_path=str(self.path)
        self.now=100000.0; self.store.clock=lambda:self.now
        self.repo=self.area/'repo'; self.repo.mkdir()
        self.git('init','--initial-branch=source')
        self.git('remote','add','origin','https://example.invalid/owned-fiction')
        (self.repo/'source.txt').write_text('first\n')
        self.git('add','source.txt'); self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','owned first')
        self.old=self.git('rev-parse','HEAD'); self.head=self.old
        self.git('branch','destination')
        self.procedure=self.area/'procedure.md'; self.procedure.write_text('Independent fixture intent: read frozen source.txt first\\n; run and read back only admitted marker. Acceptance separate.\n')
        self.acceptor=ident()
        with self.store.tx(): self.store.db.execute('UPDATE enrollments SET intake=0')
        for role,board in self.boards.items():
            with software.fixture_actor(board.store,self.config['roles'][role]['owner']):
                board.revoke(self.store.one('SELECT grant_id FROM enrollments WHERE role=?',(role,))['grant_id'])
        self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for board in self.boards.values():board.runtime=self.store
        self.selection={'basis':processing.basis(self.store,self.boards,future_only=True),
            'authority':'fictional genuine Work issuer selects prospective unchanged roles','retained_events':[],
            'recover_controls':{},'future_intake':True,'tasks':list(self.config['tasks']),
            'metadata_lookup':{'tasks':['work-proposer','work-integrator','qa-execution','branch-proposer','reviews-integrator'],
                'authority':'fictional explicit metadata only; no native-owner disposition or package consent', 'max_points':16,'max_bytes':65536},
            'max_shared_rows':1000,'max_shared_payload_bytes':1048576,'max_runtime_rows':100,
            'service':{'max_inflight':8,'reviews':{},'legacy_resources':{}}}
        with software.fixture_actor(self.boards['Work'].store,self.config['roles']['Work']['owner']):
            self.key=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.key,self.boards)
        self.dispatcher=processing.ProcessingDispatcher(self.store,models=object(),boards=self.boards)
        self.decisions={}; self.classifications={}; self.calls=[]
        async def model(store,attempt,prompt,spec,schema):
            row=self.store.attempt(attempt)
            self.assertIs(store,self.store)
            self.store.begin(attempt,{'fictional_model_transport':True}); self.store.session(attempt,ident())
            self.calls.append((row['kind'],row['event'],prompt))
            if row['kind']=='classifier':
                source=self.store.routing_event(row['event'])
                answer={'event_id':source['id'],'task':self.classifications.get(source['id'],source['allowed_tasks'][0]),
                        'package':source.get('package'),'reason':'fictional actual per-message LOW classification'}
                self.assertEqual(json.loads(row['binding']),self.config['classifier']['binding'])
            else:
                self.assertEqual(row['kind'],'input-mapping')
                record=self.store.one('SELECT snapshot FROM input_lookups WHERE attempt=?',(attempt,))
                self.assertIn('observed_before_model',prompt)
                answer=self.decisions[row['event']](json.loads(record['snapshot']))
            return {'result':answer,'exit':0,'capture':'complete','cleanup':'done','error':None,
                    'detail':{'tool_completion':{'complete':True,'items':[],'nonzero_completions':[]}}}
        # Only the external model transport/semantic answer is fictional.
        # Dispatcher.run_model and its actual launch authorization stay real.
        self.dispatcher.models=SimpleNamespace(run=model)

    async def drain(self):
        while self.dispatcher.active:
            await asyncio.gather(*list(self.dispatcher.active))

    async def classified(self,source,task):
        self.classifications[source['id']]=task
        while True:
            before=len(self.calls)
            self.dispatcher.schedule_classifications(); await self.drain()
            state=self.store.one('SELECT * FROM events WHERE id=?',(source['id'],))
            if state['state'] != 'received':break
            self.assertGreater(len(self.calls),before,'fresh source must advance or retain an explicit failure')
        self.assertEqual(state['state'],'queued',state['error'])
        self.assertIsNotNone(self.store.one('SELECT * FROM queue WHERE event=?',(source['id'],)))
        return state['classifier']

    def choice(self,source,task,key=None,state='known',writes=False,mutate=None):
        def answer(snapshots):
            snapshot=snapshots[task]
            selected=key
            if state=='known' and selected is None:
                selected=next(k for k,p in snapshot['points'].items()
                              if p['definition']['bindings'][0].get('path',[])[-1:] == ['late'])
            integration={'state':state}
            if state=='known':integration.update(reads=[] if writes else [selected],writes=[selected] if writes else [])
            if mutate: mutate(snapshot)
            return {'semantic':'DONE','summary':'fictional bounded metadata account grounded in supplied original',
                'decision_json':encode({'task':task,'integration':integration,'reason':'independent fixture identity/novelty intent',
                                      'evidence':['actual supplied original and service snapshot'], 'remaining_obligations':['all native acceptance remains independent']})}
        self.decisions[source['id']]=answer

    async def mapped(self,source):
        # Drive the production phase engine itself. Prevent task effects while
        # explicitly inspecting the before-first-reservation boundary.
        with patch.object(self.dispatcher,'schedule_job',lambda:None):
            await self.dispatcher.tick()
            await self.drain()
        row=self.store.one('SELECT * FROM input_lookups WHERE event=?',(source['id'],))
        self.assertIsNotNone(row,'ordinary production tick must instantiate metadata lookup without owner mapping: '+encode(self.store.rows('SELECT * FROM operational_errors')))
        self.assertIsNone(row['error'],row['error'])
        self.assertIsNotNone(row['resolution'],encode(self.dispatcher.runtime_errors))
        return self.store.input_resolution(source['id'])

    async def test_automatic_sdk_queue_ACK_lookup_frozen_revision_and_parallel_existing(self):
        source=self.post(text='Existing late item; title is data, identity comes from permitted catalog')
        original=copy.deepcopy(source); birth=self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(source['id'],))
        with self.assertRaises(Refusal): self.boards['Work'].receipt(self.store,source['id'])
        classifier=await self.classified(source,'work-proposer')
        self.dispatcher.receipts()
        receipt=json.loads(self.store.one('SELECT ack_receipt FROM events WHERE id=?',(source['id'],))['ack_receipt'])
        self.assertIsNotNone(receipt)
        self.assertIsNone(self.store.reserve())
        self.choice(source,'work-proposer')
        mapped=await self.mapped(source)
        self.assertEqual(mapped['actor'],self.config['actor'])
        self.assertNotEqual(mapped['actor'],self.config['roles']['Work']['owner'])
        self.assertFalse(mapped['prior']['software_processing']['native_owner_receipt'])
        key=mapped['receipt']['integration']['reads'][0]
        self.assertTrue(key.startswith('known:'))
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'),[])
        self.assertEqual(self.store.event(source['id']),original)
        self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?',(source['id'],)),birth)
        self.assertIsNone(self.store.reserve())  # mapping requires fresh LOW
        second_classifier=await self.classified(source,'work-proposer')
        self.assertNotEqual(classifier,second_classifier)
        self.assertEqual(json.loads(self.store.one('SELECT ack_receipt FROM events WHERE id=?',(source['id'],))['ack_receipt']),receipt)
        first=self.store.reserve(); self.assertIsNotNone(first)
        other=self.post(text='Independent b in the same running capability')
        await self.classified(other,'work-proposer'); self.choice(other,'work-proposer','b')
        await self.mapped(other); await self.classified(other,'work-proposer')
        second=self.store.reserve(); self.assertIsNotNone(second)
        self.assertEqual(local.scope_for(self.store,second)['reads'],['b'])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM processing_capabilities')['n'],1)
        self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'),[])
        self.assertTrue(all(r['intake']==0 for r in self.store.rows('SELECT intake FROM enrollments')))
        (self.area/'automatic-receipt.json').write_text(encode({'source':source,'original_classifier':classifier,'fresh_classifier':second_classifier,
              'receipt':receipt,'mapping':mapped,'jobs':[first,second]}))

    async def test_snapshot_is_before_model_and_never_restamped_after_result(self):
        source=self.post(); await self.classified(source,'work-proposer')
        def mutate(snapshot):
            before=snapshot['points']['a']['version']
            data=json.loads(self.catalog.read_text()); data['items']['a']['state']='later';self.catalog.write_text(encode(data))
            self.assertNotEqual(before,local.version(self.store,'a',{str(p):p.read_bytes() for p in self.peers if p.suffix=='.json'}))
        self.choice(source,'work-proposer','a',mutate=mutate)
        mapped=await self.mapped(source); await self.classified(source,'work-proposer')
        job=self.store.reserve()
        self.assertIsNotNone(job,encode({'errors':self.store.rows('SELECT * FROM operational_errors'),'jobs':self.store.rows('SELECT id,state,task FROM jobs'),'queue':self.store.rows('SELECT * FROM queue')}))
        attempt=self.store.start_job(job['id'],job['token']); job=self.store.job(job['id'])
        local.prepare_input_basis(self.store,job,attempt,self.config['tasks'][job['task']])
        basis=json.loads(self.store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))['basis'])
        self.assertEqual(basis['scope']['mode'],'reconcile')
        self.assertNotEqual(basis['versions']['a'],mapped['prior']['integration_observation']['packet']['versions']['a'])
        collect(self.store,attempt,result(),tool_completion={'complete':True,'items':[]})

    async def test_unknown_is_owned_and_only_positive_new_enters_discovery(self):
        unknown=self.post(text='Ambiguous existing identity')
        await self.classified(unknown,'@unresolved'); self.choice(unknown,'work-proposer',state='unresolved-existing')
        await self.mapped(unknown); await self.classified(unknown,'work-proposer')
        self.assertIsNone(self.store.reserve())
        question=self.store.one("SELECT * FROM outboxes WHERE event=? AND kind='question'",(unknown['id'],))
        self.assertIsNotNone(question)
        self.assertEqual(question['recipient'],'Work')
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'),[])
        new=self.post(text='Independent fixture positively new business request')
        await self.classified(new,'work-proposer'); self.choice(new,'work-proposer',state='new')
        await self.mapped(new); await self.classified(new,'work-proposer')
        job=self.store.reserve(); self.assertEqual(local.scope_for(self.store,job)['lane'],'discovery')
        self.assertEqual(local.scope_for(self.store,job)['reads'],[])

    async def test_holds_permissions_and_original_source_refuse_before_acquisition(self):
        from coordinator_runtime import metadata_lookup, custody, local_native
        source=self.post();await self.classified(source,'work-proposer')
        count=len(self.store.rows('SELECT * FROM attempts'))
        self.store.set_hold(source['id'],'fictional privacy hold')
        with patch.object(self.store,'event',side_effect=AssertionError('held source read')):
            self.dispatcher.schedule_input_mappings()
        self.assertEqual(len(self.store.rows('SELECT * FROM attempts')),count)
        self.store.set_hold(source['id'],None)
        for task,package in [('qa-execution',None),('branch-integrator',None)]:
            with (patch.object(custody,'read_file',side_effect=AssertionError('unauthorized material')),
                  patch.object(local_native,'snapshot',side_effect=AssertionError('unauthorized native'))):
                with self.assertRaises(Refusal):
                    metadata_lookup.observe(self.store,source,task,package,self.selection['metadata_lookup'])
        with self.boards['Work'].opened(settlement=True) as conn:
            conn.execute("UPDATE sessions SET status='paused' WHERE session=?",(self.config['roles']['Work']['owner'],))
        with patch.object(custody,'read_file',side_effect=AssertionError('paused owner material')):
            self.assertIsNone(metadata_lookup.claim(self.store))
        self.assertEqual(len(self.store.rows('SELECT * FROM attempts')),count)
        self.assertEqual(self.store.rows('SELECT * FROM input_resolutions'),[])

    async def test_capability_and_model_handoff_changes_do_not_borrow_owner_authority(self):
        from coordinator_runtime import metadata_lookup
        source=self.post();await self.classified(source,'work-proposer')
        self.choice(source,'work-proposer','a')
        claimed=metadata_lookup.claim(self.store);self.assertIsNotNone(claimed)
        attempt=claimed[1]
        with self.store.tx():
            self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.now,self.key))
        outcome=await self.dispatcher.run_model(attempt,'unread fictional prompt',{'sandbox':'read-only'},metadata_lookup.RESULT_SCHEMA)
        self.assertTrue(outcome['detail']['known_not_started'])
        self.assertIsNone(outcome['exit'])
        # Actual known not started, with NO invented numeric END/refund/replay.
        self.store.collect(attempt,outcome)
        row=self.store.attempt(attempt);self.assertEqual(row['state'],'not-started');self.assertIsNone(row['ended'])
        self.assertEqual(self.store.rows('SELECT * FROM input_resolutions'),[])
        self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'),[])

    async def test_positive_mounts_and_native_profile_schema_are_real(self):
        import errno,os
        for path in ('/tools/coordinator-runtime/coordinator_runtime/store.py','/sdk/retention.py'):
            with self.assertRaises(OSError) as refusal:os.open(path,os.O_WRONLY)
            self.assertEqual(refusal.exception.errno,errno.EROFS)
        columns=self.store.rows('PRAGMA table_info(attempts)')
        self.assertEqual(next(c['notnull'] for c in columns if c['name']=='profile'),1)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM attempts WHERE profile IS NULL')['n'],0)

    async def test_model_cannot_forge_revision_points_or_generic_owner_control(self):
        from coordinator_runtime import metadata_lookup
        source=self.post();await self.classified(source,'work-proposer')
        self.choice(source,'work-proposer','a')
        def forged(_):
            return {'semantic':'DONE','summary':'fictional forged metadata', 'decision_json':encode({
                'task':'work-proposer','integration':{'state':'known','reads':['unobserved'],'writes':[], 'versions':{'unobserved':'forged'}},
                'reason':'forged','evidence':['fixture negative'],'remaining_obligations':[]})}
        self.decisions[source['id']]=forged
        self.dispatcher.schedule_input_mappings();await self.drain()
        record=self.store.one('SELECT * FROM input_lookups WHERE event=?',(source['id'],))
        self.assertIsNotNone(record['error']);self.assertIsNone(self.store.input_resolution(source['id']))
        self.dispatcher.schedule_input_mappings();await self.drain()
        self.assertEqual(len([c for c in self.calls if c[0]=='input-mapping']),1)
        self.assertEqual(self.store.rows('SELECT * FROM local_lookup_points'),[])
        with self.assertRaises(Refusal):
            self.store.resolve_input(source['id'],self.config['roles']['Work']['owner'],{
                'integration':{'state':'known','reads':['a'],'writes':[]}},mapping_attempt=record['attempt'])

    async def test_late_accepted_branch_alternative_and_member_hold_before_native_read(self):
        from coordinator_runtime import local_native
        self.admission()
        owner=self.config['roles']['Work']['owner']
        receipt={'id':'owned-late-branch','repository':str(self.repo),'origin':'https://example.invalid/owned-fiction',
            'ref':'refs/heads/destination','incarnation':'genuine-fictional-branch-life','scope':'package',
            'root':owner,'authority':'fictional independently selected actual branch assignment'}
        branches.register(self.store,owner,receipt)
        branches.accept(self.store,receipt['id'],owner,'fictional actual registered owner accepts this exact branch')
        admission=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))['receipt'])
        for task in ('branch-proposer','reviews-integrator'):
            admission['task_scopes'][task]={'branch_binding':receipt['id']}
        self.store.admit('package',self.config['roles']['Branch']['owner'],admission)
        source=self.post('Branch',package='package');await self.classified(source,'branch-proposer')
        def choose(task):
            def answer(snapshots):
                key=next(iter(snapshots[task]['points']))
                point=snapshots[task]['points'][key]['definition']
                self.assertEqual(point['native_incarnations'],[receipt['incarnation']])
                self.assertEqual(point['incarnation'],'stable-delivery')
                return {'semantic':'DONE','summary':'fictional source-related accepted branch observation', 'decision_json':encode({
                    'task':task,'integration':{'state':'known','reads':[key],'writes':[]},'reason':'existing accepted branch',
                    'evidence':['original current admitted branch association'], 'remaining_obligations':['Source original stays separate']})}
            return answer
        self.decisions[source['id']]=choose('branch-proposer');await self.mapped(source);await self.classified(source,'branch-proposer')
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token']);job=self.store.job(job['id'])
        self.boards['Branch'].bind_software_attempt(self.store,job,attempt,self.store.one('SELECT * FROM admissions WHERE package=?',('package',)))
        local.prepare_input_basis(self.store,job,attempt,self.config['tasks'][job['task']])
        answer=result(category='proposal');answer.update(handoffs=[],no_handoff_reason='fictional internal sole integrator route')
        answer['completion']={'integration_steps':[{'step':s,'evidence':'fictional branch account '+s} for s in local.STEPS]}
        collect(self.store,attempt,answer,tool_completion={'complete':True,'items':[],'nonzero_completions':[]})
        returned=self.store.event(self.store.finish_job(job['id'],job['token']))
        # Original service-created anchor continues unchanged. This does not
        # force primary Source to predict a run, nor fabricate a Source Act.
        self.assertIn('integration',returned)
        await self.classified(returned,'reviews-integrator')
        self.dispatcher.schedule_input_mappings();await self.drain()
        self.assertIsNone(self.store.one('SELECT * FROM input_lookups WHERE event=?',(returned['id'],)))
        # Before any new point material, EVERY original member is protected.
        self.store.set_hold(source['id'],'fictional upstream member privacy hold')
        row={'event':returned['id'],'task':'reviews-integrator','package':'package'}
        with patch.object(local_native,'snapshot',side_effect=AssertionError('held upstream native read')):
            with self.assertRaises(Refusal):local.packet(self.store,row)
        self.assertEqual(self.store.rows('SELECT * FROM review_contexts'),[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])

    async def test_first_QA_late_admission_identity_before_slot_and_real_runner(self):
        # The permission was selected before the admission receipt/native
        # lifecycle existed. This supported original admission does not mutate
        # config or capability. All operations here are OWNED FICTION.
        admission=self.admission(kind='local-qa')
        epoch=prospective.select(self.store,self.config['roles']['Work']['owner'],{
            'configuration':digest(self.config),'authority':'fictional separate prospective ordinary adapter authorization',
            'processing_capability':self.key,
            'expires':self.now+100,'grants':{'QA':self.store.enrollment('QA')['grant_id']},
            'tasks':{'qa-execution':{'task_hash':digest(self.config['tasks']['qa-execution']),'software_handoffs':{},'ordinary_effects':True}}})
        source=self.post('QA',package='package'); await self.classified(source,'qa-execution')
        self.assertIsNone(self.store.reserve()); self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])
        def choose(snapshots):
            key=next(iter(snapshots['qa-execution']['points']))
            definition=snapshots['qa-execution']['points'][key]['definition']
            actual=self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))['receipt']
            self.assertEqual(definition['native_incarnations'],[digest(actual)])
            self.assertEqual(definition['incarnation'],'stable-delivery')
            return {'semantic':'DONE','summary':'fictional observed late actual admission', 'decision_json':encode({
                'task':'qa-execution','integration':{'state':'known','reads':[key],'writes':[]},
                'reason':'independent admitted QA task intent','evidence':['original SDK QA ref plus actual permitted admission snapshot'],
                'remaining_obligations':['independent semantic acceptance']})}
        self.decisions[source['id']]=choose
        await self.mapped(source)
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        await self.classified(source,'qa-execution')
        job=self.store.reserve(); self.assertIsNotNone(job)
        attempt=self.store.start_job(job['id'],job['token']);job=self.store.job(job['id'])
        self.boards['QA'].bind_software_attempt(self.store,job,attempt,self.store.one('SELECT * FROM admissions WHERE package=?',('package',)))
        task=scoped_task(job['task'],self.config['tasks'][job['task']],self.store.one('SELECT * FROM admissions WHERE package=?',('package',)))
        local.prepare_input_basis(self.store,job,attempt,task)
        answer=result(category='consolidated');answer.update(handoffs=[],no_handoff_reason='fixture external acceptance stays owed')
        answer['completion']={'integration_steps':[{'step':s,'evidence':'fictional method '+s} for s in local.STEPS]}
        collect(self.store,attempt,answer,tool_completion={'complete':True,'items':[],'nonzero_completions':[]})
        self.store.finish_job(job['id'],job['token'])
        self.assertTrue(await ordinary.perform(self.store,self.boards['QA'],job))
        self.assertEqual((self.area/'qa-output/actual-run.txt').read_text(),'actually executed')
        self.assertFalse(ordinary.accepted_package(self.store,'package'))
        row=self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?',(attempt,))
        (self.area/'qa-receipt.json').write_text(encode({'source':source,'epoch':epoch,'run':row,'mapping':self.store.input_resolution(source['id'])}))

    async def test_distinct_future_QA_packages_lookup_only_their_own_native_reference(self):
        for package in ('package','other-package'):
            self.admission(package=package,kind='local-qa')
            source=self.post('QA',package=package);await self.classified(source,'qa-execution')
            def answer(snapshots):
                points=snapshots['qa-execution']['points']
                self.assertEqual(len(points),1)
                key,point=next(iter(points.items()))
                self.assertEqual(point['definition']['bindings'][0]['package'],package)
                return {'semantic':'DONE','summary':'fictional source-specific native reference', 'decision_json':encode({
                    'task':'qa-execution','integration':{'state':'known','reads':[key],'writes':[]},'reason':'independent scoped original',
                    'evidence':['permitted current source admission'], 'remaining_obligations':['no execution or acceptance claimed']})}
            self.decisions[source['id']]=answer
            await self.mapped(source)
            await self.classified(source,'qa-execution')
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM processing_capabilities')['n'],1)
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])

    async def test_addressed_handoff_automatically_maps_receiver_and_preserves_all_originals(self):
        from coordinator_runtime import local_native, metadata_lookup
        self.admission(kind='local-qa')
        qa=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))['receipt'])
        self.admission()
        admitted=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))['receipt'])
        admitted['task_scopes'].update(qa['task_scopes'])
        self.store.admit('package',self.config['roles']['Branch']['owner'],admitted)
        owner=self.config['roles']['Work']['owner']
        branch={'id':'handoff-owned-branch','repository':str(self.repo),'origin':'https://example.invalid/owned-fiction',
            'ref':'refs/heads/destination','incarnation':'handoff-branch-life','scope':'package','root':owner,
            'authority':'fictional separate branch assignment, never actual Root'}
        branches.register(self.store,owner,branch);branches.accept(self.store,branch['id'],owner,'fictional registered assigned coordinator acceptance')
        admitted['task_scopes']['branch-proposer']={'branch_binding':branch['id']}
        self.store.admit('package',self.config['roles']['Branch']['owner'],admitted)
        prospective.select(self.store,owner,{'configuration':digest(self.config),'processing_capability':self.key,
            'authority':'fictional exact future addressed handoff and separate QA ordinary authority','expires':self.now+100,
            'grants':{r:self.store.enrollment(r)['grant_id'] for r in ('Branch','QA')},
            'tasks':{t:{'task_hash':digest(self.config['tasks'][t]),
                'software_handoffs':copy.deepcopy(self.config['tasks'][t].get('software_handoffs',{})),
                'ordinary_effects':t=='qa-execution'} for t in ('branch-proposer','qa-execution')}})
        def choose(task):
            def answer(snapshots):
                key=next(iter(snapshots[task]['points']))
                return {'semantic':'DONE','summary':'fictional actual permitted receiver identity', 'decision_json':encode({
                    'task':task,'integration':{'state':'known','reads':[key],'writes':[]},'reason':'independent selected receiving duty',
                    'evidence':['original scoped source and its service observation'],'remaining_obligations':['original effect and acceptance stay owed']})}
            return answer
        source=self.post('Branch',package='package');await self.classified(source,'branch-proposer')
        self.decisions[source['id']]=choose('branch-proposer');await self.mapped(source);await self.classified(source,'branch-proposer')
        sender=self.store.reserve();attempt=self.store.start_job(sender['id'],sender['token']);sender=self.store.job(sender['id'])
        self.boards['Branch'].bind_software_attempt(self.store,sender,attempt,self.store.one('SELECT * FROM admissions WHERE package=?',('package',)))
        local.prepare_input_basis(self.store,sender,attempt,self.config['tasks']['branch-proposer'])
        answer=result(category='proposal');answer['handoffs']=[{'recipient':'QA','kind':'work','ref':'package',
            'required':'settled','text':'Original actual fixture QA duty; nested sender metadata does not grant QA authority'}]
        answer['completion']={'integration_steps':[{'step':s,'evidence':'fictional source account '+s} for s in local.STEPS]}
        collect(self.store,attempt,answer,tool_completion={'complete':True,'items':[],'nonzero_completions':[]})
        self.store.finish_job(sender['id'],sender['token'])
        while self.store.one("SELECT id FROM events WHERE state='received'"):
            self.dispatcher.schedule_classifications();await self.drain()
        self.dispatcher.pump_deliveries()
        delivery=self.store.one("SELECT payload FROM events WHERE role='QA'")
        self.assertIsNotNone(delivery,encode({'outboxes':self.store.rows('SELECT id,kind,state,error FROM outboxes'),'errors':self.store.rows('SELECT * FROM operational_errors')}))
        received=json.loads(delivery['payload'])
        self.assertNotIn('integration',received);self.assertIn('source_result',received['body'])
        original=copy.deepcopy(received)
        await self.classified(received,'qa-execution')
        self.assertIsNone(self.store.reserve());self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        self.store.set_hold(source['id'],'fictional exact upstream hold')
        with patch.object(local_native,'snapshot',side_effect=AssertionError('held original native acquisition')):
            self.assertIsNone(metadata_lookup.claim(self.store))
        self.assertIsNone(self.store.one('SELECT * FROM input_lookups WHERE event=?',(received['id'],)))
        self.store.set_hold(source['id'],None)
        self.decisions[received['id']]=choose('qa-execution')
        await self.mapped(received);await self.classified(received,'qa-execution')
        receiver=self.store.reserve();self.assertEqual(receiver['task'],'qa-execution')
        self.assertEqual(self.store.event(received['id']),original)
        self.assertEqual(json.loads(self.store.job(sender['id'])['members'])[0]['hash'],digest(source))
        self.assertEqual(received['body']['source_members'],json.loads(sender['members']))
        self.boards['QA'].receiving_intent(self.store,received)
        (self.area/'automatic-handoff.json').write_text(encode({'source':source,'sender':sender,'receiver':receiver,
            'received':received,'mapping':self.store.input_resolution(received['id'])}))

    async def test_automatic_Work_seven_actual_fixture_consumers(self):
        source=self.post(text='Independent fixture a state update with all seven joined duties')
        before=json.loads(self.catalog.read_text()); old_log=self.log.read_text()
        await self.classified(source,'work-integrator');self.choice(source,'work-integrator','a',writes=True)
        await self.mapped(source);await self.classified(source,'work-integrator')
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token']);job=self.store.job(job['id'])
        self.boards['Work'].bind_software_attempt(self.store,job,attempt,None)
        (self.store.home/'artifacts'/attempt).mkdir(parents=True,mode=0o700)
        routine.prepare(self.store,self.boards['Work'],job,attempt,self.config['tasks'][job['task']])
        stages=publication.stages(self.store,attempt)
        data=json.loads(Path(stages[str(self.catalog)]).read_text());data['items']['a']['state']='updated'
        Path(stages[str(self.catalog)]).write_text(encode(data))
        for p in self.peers[1:]:
            if p.suffix=='.json':
                value=json.loads(p.read_text());value['items']['a']['state']='updated';Path(stages[str(p)]).write_text(encode(value))
            else:Path(stages[str(p)]).write_text('Fixture a updated\n'+p.read_text())
        Path(stages[str(self.log)]).write_text('Fixture a updated\n')
        publication.conserve_stages(self.store,attempt,self.config['tasks'][job['task']])
        answer=result();answer.update(handoffs=[],no_handoff_reason='fictional joined consumer obligation only')
        answer['completion']={'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[],
            'integration_steps':[{'step':s,'evidence':'fictional independent intent account '+s} for s in local.STEPS]}
        collect(self.store,attempt,answer,tool_completion={'complete':True,'items':[{'id':'fictional-tool','exit_code':0,'status':'completed'}]})
        self.assertTrue(routine.reconcile(self.store,self.boards['Work'],job))
        consumers=self.store.rows('SELECT * FROM file_publications WHERE attempt=?',(attempt,))
        self.assertEqual({r['target'] for r in consumers},{str(p) for p in self.peers}|{str(self.log)})
        self.assertTrue(all(r['state']=='published' for r in consumers))
        actual=json.loads(self.catalog.read_text()); expected=copy.deepcopy(before);expected['items']['a']['state']='updated'
        self.assertEqual(actual,expected);self.assertEqual(self.log.read_text(),'Fixture a updated\n'+old_log)
        for p in self.peers[1:]:
            if p.suffix=='.json':self.assertEqual(json.loads(p.read_text()),expected)
            else:self.assertIn('a updated',p.read_text())
        (self.area/'seven-consumer-receipts.json').write_text(encode(consumers))


class Scheduler(Ingress):
    async def test_supported_admission_change_refuses_before_any_classifier_reservation(self):
        self.qa_point()
        source=self.post('QA',package='package')
        self.resolve(source,'qa-execution','execution')
        original=self.store.event(source['id']);birth=self.store.one('SELECT received FROM events WHERE id=?',(source['id'],))
        admission=self.store.one('SELECT * FROM admissions WHERE package=?',('package',))
        self.store.admit('package',self.config['roles']['Branch']['owner'],json.loads(admission['receipt']),accepted={'fictional':'supported acceptance-only change'})
        attempts=self.store.rows('SELECT * FROM attempts')
        with patch.object(self.store.execution_pool,'allocate',wraps=self.store.execution_pool.allocate) as allocation:
            failure=None
            try: claimed=self.store.claim_classification()
            except Refusal as exc: failure=str(exc);claimed=None
            observed={'event':self.store.one('SELECT state,classifier,error FROM events WHERE id=?',(source['id'],)),
                      'attempts':self.store.rows('SELECT * FROM attempts'),'refusal':failure,'pool_allocations':allocation.call_count}
            (self.area/'scheduler-binding-change.json').write_text(encode(observed))
            self.assertIsNone(claimed)
            self.assertEqual(observed['attempts'],attempts,'stale binding must not strand an unspawned attempt')
            self.assertEqual(allocation.call_count,0)
        self.assertEqual(self.store.rows('SELECT * FROM attempts'),attempts)
        self.assertEqual(self.store.one('SELECT state,classifier FROM events WHERE id=?',(source['id'],)),{'state':'mapping-held','classifier':None})
        self.assertEqual(self.store.event(source['id']),original)
        self.assertEqual(self.store.one('SELECT received FROM events WHERE id=?',(source['id'],)),birth)
        unrelated=self.post(text='Unrelated ordinary Work must still classify')
        self.classify(unrelated,'work-proposer')
        self.resolve(source,'qa-execution','execution')  # authentic later remapping remains possible
        self.classify(source,'qa-execution')
        self.assertIsNotNone(self.store.reserve())
