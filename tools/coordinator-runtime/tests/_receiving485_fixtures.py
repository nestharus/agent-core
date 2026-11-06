"""Owned fictional receiving fixtures adapted from closed QA477's exact
source-withdrawal477 -> native477 -> models477 -> base477 dependencies.
Principals, semantics and native receipts are fiction; schemas/guards/tools run.
No previous stores, results, raw captures or private provider inputs are used.
Run only in an explicitly isolated owned test namespace with the public SDK.
"""
"""Independent fictional QA477 setup. No actual principals or role environment."""
import asyncio,copy,json,unittest,sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import catalog,board_store
from support import fixture_publication
from coordinator_runtime.contracts import *
from coordinator_runtime.store import Store
from coordinator_runtime.board import Board
from coordinator_runtime import processing,local_integration as local
@contextmanager
def actor(module,who):
 def check(value):
  assert value==who;return canonical_uuid(value)
 with patch.object(module,'acting_session',side_effect=check):yield
class Base(unittest.TestCase):
 def setUp(self):
  self.area=Path('/fixtures')/('case-'+ident());self.area.mkdir();self.method=self.area/'method.md';self.method.write_text('Fictional QA477: retain independent source evidence and current scope.');self.catalog=self.area/'ASSIGNMENTS.json';self.log=self.area/'WORK_LOG.md';self.peers=[self.area/n for n in ['ASSIGNMENTS.md','CONSOLIDATION_REGISTER.json','WORK_NOW_20261030.json','WORK_NOW_20261030.md','ROOT_NEXT.md']]
  self.catalog.write_text(encode({'assignments':[{'id':'a','state':'pending','owner':'fictional-accepted-owner','history':['retain'],'unknown':{'x':None}},{'id':'b','state':'pending'}],'unknown-peer':{'retain':True}})+'\n')
  for p in self.peers:p.write_text(encode({'items':[],'unknown':'retain'})+'\n' if p.suffix=='.json' else 'Original historical text\n')
  self.log.write_text('old log\n');self.targets=[str(self.catalog),*[str(p) for p in self.peers],str(self.log)]
  home=self.area/'board';home.mkdir()
  with catalog.catalog(home) as c:entry=catalog.create(c,home,'qa477','Fictional isolated QA477',temporary_test=True)
  with board_store.database(entry['db_path']) as c:board_store.bind_board(c,entry['board_id'],initialize=True)
  self.config={'version':1,'enabled':True,'actor':ident(),'state_dir':str(self.area/'state'),'board_home':str(home),'board_library':'/sdk','profiles':['.codex','.codex2','.codex3','.codex4','.codex5'],'classifier':{'binding':LUNA,'profile':'.codex3','cwd':str(self.area)},'diagnosis':{'binding':LUNA,'profile':'.codex3','cwd':str(self.area)},'roles':{},'tasks':{},'classification_capacity':5,'limits':{'max_events':10000,'max_attempts':30000,'max_jobs':10000,'max_alerts':10000,'max_bytes':536870912,'max_result_bytes':262144,'max_artifact_bytes':33554432,'max_files':50000,'max_outboxes':10000,'max_board_deliveries':10000},'deadlines':{k:60 for k in ['classify','task','ack','backlog','bind','interrupt','shutdown','alert_interval']},'recheck_seconds':1,'codex':'/usr/bin/false','protocol_cli_version':'fictional-no-provider','protocol_qualification':str(self.area/'no-provider'),'session_storage':{'mode':'producer-owned'},'canonical_publication':{'method':'retention-same-inode-v1','library':'/sdk'},'delivery':{'recipients':{},'alert_role':'Work','alert_recipient':'Work'}}
  for role in ['Work','Branch','Reviews','QA']:
   who=ident();phases=['execution','cleanup'] if role=='QA' else ['proposer','integrator'];names=[role.lower()+'-'+p for p in phases]
   self.config['roles'][role]={'owner':who,'profile':'.codex3','board_id':entry['board_id'],'board_role':role.lower(),'legacy_hold':'fictional original duties remain owned','legacy_hold_phases':[],'routes':names,'package_admission_required':True}
   self.config['delivery']['recipients'][role]={'session':who,'profile':'.codex3','board_role':role.lower(),'active':True}
   with board_store.database(entry['db_path']) as c:
    a=board_store.parser().parse_args(['register','--session',who,'--role',role.lower(),'--profile','.codex3','--route','managed'])
    with actor(board_store,who):board_store.register(c,a)
   for name,phase in zip(names,phases):
    t={'role':role,'phase':phase,'profile':'.codex3','binding':SOL,'cwd':str(self.area),'sandbox':'read-only','effects':'none','network':False,'capacity':2,'templates':[str(self.method)],'purpose':'Fictional isolated ingress verification','authority':'Independent fictional QA477 task authority','effect_authority':{'owner':who,'operations':['read-reports','prepare-intents','consolidate-reports'],'read_roots':[str(self.area)],'write_roots':[]},'responses':{},'delivery_required':True,'allowed_handoffs':['Work']}
    self.config['tasks'][name]=t
  t=self.config['tasks']['work-integrator'];t.update(sandbox='workspace-write',effects='owner-reconcile',routine_completion={'kind':'catalog-bounded-log-v1','targets':self.targets,'bounded_log':{'target':str(self.log),'max_lines':12,'max_bytes':8192,'max_entry_bytes':16384}});t['effect_authority'].update(write_roots=self.targets,operations=['read-reports','prepare-intents','consolidate-reports','write-role-records'])
  self.config['software_delegation']={'grantor':self.config['roles']['Work']['owner'],'authority':'Fictional Work grants only this newly created fixture journal','boundary':'new-journal-only'}
  def point(binding):return {'kind':'item','line':'fictional-neutral','incarnation':'fictional-delivery-life','bindings':[binding],'resources':[],'protected':['id','owner','history'],'writable':['state']}
  self.config['local_integration']={'tasks':{},'points':{'a':point({'target':str(self.catalog),'path':['assignments',{'field':'id','value':'a'}]}),'b':point({'target':str(self.catalog),'path':['assignments',{'field':'id','value':'b'}]})},'max_inflight':4}
  for task in ['work-integrator','work-proposer']:
   self.config['local_integration']['tasks'][task]={'capacity':2,'discovery_batch':4,'points':['a','b'],'authority':'Fictional exact selected catalog authority','method':str(self.method),'ownership_fields':['owner']}
  routes=self.area/'routes.toml';routes.write_text('[rotation]\nstate_dir = '+encode(str(self.area/'pool-state'))+'\n[providers.codex]\npool = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\nmanual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n');self.config['execution_pool_routes']=str(routes)
  self.config['canonical_publication']=fixture_publication()
  self.configure_fixture();validate_config(self.config);self.store=Store(self.config);self.addCleanup(self.store.close)
 def configure_fixture(self):pass
 def setup(self):
  boards={r:Board(self.config,r) for r in self.config['roles']}
  for r,b in boards.items():
   with actor(b.store,self.config['roles']['Work']['owner']):g=b.grant_software(self.store,self.config['software_delegation']['authority'])
   self.store.enroll(r,g)
   with actor(b.store,self.config['roles']['Work']['owner']):b.revoke_software(self.store,g['id'])
   self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(r,))
  self.boards={r:processing.ProcessingBoard(self.config,r) for r in boards}
  s={'basis':processing.basis(self.store,self.boards),'authority':'Fictional Work selects bounded future fixture processing','expires':self.store.clock()+3600,'retained_events':[],'recover_controls':{},'future_intake':True,'tasks':list(self.config['tasks']),'max_starts':256,'max_shared_rows':10000,'max_shared_payload_bytes':1048576,'max_runtime_rows':10000,'metadata_lookup':{'tasks':['work-integrator'],'authority':'Fictional prospective metadata only','max_points':16,'max_bytes':60000}}
  s.pop('expires');s.pop('max_starts');s['service']={'max_inflight':8,'reviews':{},'legacy_resources':{r:{'original_hold':self.config['roles'][r]['legacy_hold'],'roots':['/fixtures/fictional-unrelated-legacy-'+r],'unbounded':False,'evidence':'Explicit fictional prior owned roots are disjoint; no debt disposed'} for r in self.config['roles']}}
  self.configure_selection(s)
  with actor(self.boards['Work'].store,self.config['roles']['Work']['owner']):self.key=processing.select(self.store,self.boards,s)['capability']
  self.store.processing=processing.Access(self.store,self.key,self.boards)
  for b in self.boards.values():b.runtime=self.store
 def configure_selection(self,s):pass
 def post(self,text,role='Work',package=None,topic='qa477'):
  b=self.boards[role];who=self.config['roles']['Branch']['owner'] if role=='Work' else self.config['roles']['Work']['owner'];args=['post','--session',who,'--to',self.config['roles'][role]['owner'],'--topic',topic,'--kind','proposal','--text',text]
  if package:args+=['--ref',package]
  with b.opened() as c:
   with actor(b.store,who):seq=b.store.post(c,b.store.parser().parse_args(args))
   e=b._event(c,{'seq':seq,'notification_id':None},b._grant(c,self.store),self.store)
  self.store.ingest(e);return e
 async def drain(self):
  while self.dispatch.active:await asyncio.gather(*list(self.dispatch.active))
 async def phase(self,n):getattr(self.dispatch,n)();await self.drain()

"""Declared in-process fictional semantic transport; not provider-process ENDs."""
from coordinator_runtime import publication
class Models:
 def __init__(self,t):self.t=t;self.calls=[]
 async def run(self,store,attempt,prompt,spec,schema):
  t=self.t;a=store.attempt(attempt);e=store.event(a['event']) if a['event'] else None
  self.calls.append({'attempt':attempt,'kind':a['kind'],'event':a['event'],'prompt_bytes':len(prompt.encode()),'prompt':prompt,'binding':json.loads(a['binding']),'profile':a['profile']})
  store.begin(attempt,{'fictional_QA477_semantic_transport':True});store.session(attempt,ident())
  if a['kind']=='classifier':
   resolution=store.input_resolution(e['id']);task=resolution['receipt']['task'] if resolution else ('@delivery' if e['kind']=='outgoing-response' else t.initial.get(e['id'],'@unresolved'))
   out={'event_id':e['id'],'task':task,'package':e.get('package'),'reason':'Independent fictional QA477 meaning'}
  elif a['kind']=='input-locator':
   request=json.loads(store.one('SELECT request FROM input_locators WHERE attempt=?',(attempt,))['request']);members=t.members.get(e['id'],['a'])
   hints={task:{scope:members for scope in v['scopes']} for task,v in request.items()}
   assert 'BACKING-PADDING-SENTINEL' not in prompt
   out={'semantic':'DONE','summary':'Only explicit fictional source IDs; no existence/novelty decision','decision_json':encode({'hints':hints})}
   if getattr(t,'after_locator',None):t.after_locator(e)
  elif a['kind']=='input-mapping':
   snapshots=json.loads(store.one('SELECT snapshot FROM input_lookups WHERE attempt=?',(attempt,))['snapshot']);task=t.targets_by_event.get(e['id'],next(iter(snapshots)));pts=snapshots[task]['points'];t.mapping_seen(e,pts) if hasattr(t,'mapping_seen') else None
   pts=t.choose_points(e,pts) if hasattr(t,'choose_points') else pts
   state=t.dispositions.get(e['id'],'known');request={'state':state,'reads':[],'writes':list(pts)} if state=='known' else {'state':state}
   if getattr(t,'mapping_readonly',False) and state=='known':request={'state':state,'reads':list(pts),'writes':[]}
   if hasattr(t,'semantic_request'):request=t.semantic_request(e,request)
   out={'semantic':'DONE','summary':'Independent fictional known/unresolved/new decision','decision_json':encode({'task':task,'integration':request,'reason':'Independent explicit fictional source business meaning','evidence':['original fictional source '+e['id']],'remaining_obligations':[]})}
   assert encode(snapshots) in prompt
   if getattr(t,'after_mapping',None):t.after_mapping(e)
  elif a['kind']=='task':
   j=store.job(a['job']);out={'semantic':'DONE','summary':'Fictional complete bounded consumer reconciliation','findings':[],'failures':[],'unknowns':[],'artifacts':[],'category':'consolidated' if j['role']=='QA' else 'complete','handoffs':[],'no_handoff_reason':'No additional fictional duty','completion':{'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[],'integration_steps':[{'step':x,'evidence':'Explicit fictional QA477 '+x+' preserves identities and rationale'} for x in local.STEPS]}}
   if getattr(t,'task_result',None):t.task_result(j,out)
   stages=publication.stages(store,attempt)
   if stages:t.edit_stages(j,stages)
  else:raise AssertionError('Unimplemented fictional seam '+a['kind'])
  detail={'fictional_QA477_semantic_transport':True,'tool_completion':{'complete':True,'items':[],'nonzero_completions':[],'unknown_types':[]}}
  if a['job']:
   detail['software_authority']=json.loads(store.attempt(attempt)['detail']).get('software_authority')
   if publication.stages(store,attempt):detail['tool_completion']['items']=[{'id':'fictional-stage-operation','exit_code':0,'status':'completed'}]
  return {'exit':0,'result':out,'capture':'complete','cleanup':'done','error':None,'detail':detail}
class Auto(Base):
 def start_auto(self):
  self.setup();self.initial={};self.members={};self.targets_by_event={};self.dispositions={};self.models=Models(self);self.dispatch=processing.ProcessingDispatcher(self.store,self.models,self.boards)
 async def until(self,predicate,n=18):
  for _ in range(n):
   await self.dispatch.tick();await self.drain()
   if predicate():return
  raise AssertionError('focused predicate unreached '+repr(self.dispatch.runtime_errors))
 def save(self,name,extra=None):
  calls=[{k:v for k,v in c.items() if k!='prompt'} for c in self.models.calls]
  (Path('/fixtures')/(name+'.json')).write_text(json.dumps({'calls':calls,'attempts':self.store.rows('SELECT id,kind,state,begin,exit,collected,profile,error FROM attempts'),'events':self.store.rows('SELECT id,state,hold,ack,processed_at FROM events'),'lookups':self.store.rows('SELECT * FROM input_lookups'),'locators':self.store.rows('SELECT * FROM input_locators'),'jobs':self.store.rows('SELECT id,task,state,package,effects,hold_reason FROM jobs'),'errors':self.store.rows('SELECT * FROM operational_errors'),'extra':extra},indent=2))

import subprocess,hashlib
from coordinator_runtime import reviews,service,branches,local_native
class FictionalNativeTransport:
 """Transport receipts are explicit fiction; Executor/lifecycle/history are production."""
 def __init__(self):self.run=None;self.calls=[]
 async def call(self,runtime,attempt,policy,context,directory,text,commands,opening=False,close=False):
  runtime.authorize_launch(attempt)
  async with runtime.execution_pool.admission(context['profile']):
   runtime.authorize_launch(attempt)
  if opening:
   assert self.run is None and context['run'] is None
   # Birth is deliberately unknowable at config/selection, generated at opening.
   self.run=ident();runtime.begin(attempt,{'fictional_native_transport':True})
  assert self.run
  i=len(self.calls);self.calls.append({'opening':opening,'run':self.run,'input':i,'commands':commands,'context_before':copy.deepcopy(context)})
  receipt={'class':'answered','run':self.run,'handle':context['handle'],'turn':{'input':i,'admitted':True,'answer_present':True,'linked_messages':1,'ack':{'message_id':'fictional-message-'+str(i)},'turn_end':{'event':'turn-end','input':i,'stop_reason':'end_turn'},'root_ended':None,'refused':None,'rejected':None,'ref':'fictional-admitted-ref'},'transport':{'errors':[],'attached':{'frontdoor':'attached','run':self.run,'backlog_dropped_total':0,'interrupted_records_total':0}},'collection':{'errors':[],'stdout_eof':True,'stderr_eof':True,'exit':0}}
  answer={'semantic':'DONE','summary':'Fictional Source architecture' if opening else 'Fictional Source complete','report':'QA472-FULL-NATIVE-REPORT-'+str(i),'history_entry':'Explicit fictional history '+str(i),'stage':'architecture' if opening else 'complete','coverage':{'families':{f:'partial' for f in reviews.FAMILIES},'core_files_not_read':['fictional-unread'],'observations':[{'id':'fictional-observation-'+str(i)}],'answered_ids':[],'limits':['fictional transport, no real semantic coverage']}}
  return 0,receipt,encode(answer)
class NativeModels(Models):
 async def run(self,store,attempt,prompt,spec,schema):
  t=self.t;a=store.attempt(attempt)
  if a['kind']=='classifier':
   e=store.event(a['event'])
   if not store.input_resolution(e['id']):
    t.initial[e['id']]=('reviews-proposer' if e['role']=='Reviews' and e['kind']=='board' else e['allowed_tasks'][0])
  if a['kind']=='input-mapping':t.mapping_readonly=True
  out=await super().run(store,attempt,prompt,spec,schema)
  if a['kind']=='task':
   j=store.job(a['job'])
   # Fictional consolidation retains the whole authentic fixture source; no upstream verdict invented.
   out['result']['findings']=[{'source':store.event(m['event'])} for m in json.loads(j['members'])]
   if j['task']=='reviews-integrator':
    out['result']['category']='consolidated'
  return out
class Native(Auto):
 def git(self,*args):
  p=subprocess.run(['git','-C',str(self.repo),*args],capture_output=True,text=True);self.gitends.append({'args':args,'END':p.returncode,'stderr':p.stderr});assert p.returncode==0,p.stderr;return p.stdout.strip()
 def configure_fixture(self):
  self.gitends=[];self.repo=self.area/'repository';self.repo.mkdir();self.git('init','-b','fixture');(self.repo/'code.py').write_text('print("fictional frozen source")\n');self.git('add','code.py');self.git('-c','user.name=Fictional QA477','-c','user.email=qa477@example.invalid','commit','-m','Fictional source');self.git('remote','add','origin','https://example.invalid/fictional.git');self.head=self.git('rev-parse','HEAD')
  t=self.config['tasks']['reviews-proposer'];t.update(execution='owner',binding={'model':'gpt-xhigh','provider':'opaque','effort':'opaque'},require_package_scope=True,scope_roots=[str(self.area)],responses={'proposal':['reviews-integrator']})
  self.config['tasks']['reviews-integrator'].update(effects='none',sandbox='read-only',publish_internal_results=True,responses={'consolidated':['work-proposer']})

  def scope(kind):return {'prefix':'known-'+kind+':','member_field':None,'point':{'kind':'item','line':'fictional-neutral-delivery','incarnation':'delivery-before-native-birth','bindings':[{'native':kind,'component' if kind=='review' else 'id':'$source'}],'resources':[],'protected':[],'writable':[]}}
  for task in ['reviews-integrator','work-proposer','branch-proposer']:
   self.config['local_integration']['tasks'][task]={'capacity':2,'discovery_batch':4,'points':[],'authority':'Fictional selected native metadata; no native owner/adoption power','method':str(self.method),'ownership_fields':[],'lookup_scopes':[scope('branch'),scope('review')] if task!='branch-proposer' else [scope('branch')]}
 def configure_selection(self,s):
  s['metadata_lookup']['tasks']=['reviews-integrator','work-proposer','branch-proposer'];s['work_coordination']={'tasks':['work-proposer'],'source_roles':['Branch','Reviews','QA'],'authority':'Separate fictional Work coordination authority'}
  s['service']['reviews']={'reviews-proposer':{'caller':'/usr/bin/false','caller_sha256':hashlib.sha256(Path('/usr/bin/false').read_bytes()).hexdigest(),'routes':{p:'fictional-'+p for p in self.config['profiles']},'deadline':60,'method':str(self.method),'method_files':reviews.method_files(str(self.method)),'components':{'component':{'repository':str(self.repo),'origin':'https://example.invalid/fictional.git','paths':['code.py'],'history':str(self.store.home/'review-history'/'component.md'),'authority':'Explicit fictional source read/history custody'}}}}
 def init_native(self,bound=True):
  self.start_auto();self.transport=FictionalNativeTransport();self.models=NativeModels(self);self.dispatch=service.Dispatcher(self.store,self.boards,self.models,self.transport)
  issuer=self.config['roles']['Work']['owner'];receipt={'id':'fictional-accepted-branch','repository':str(self.repo),'origin':'https://example.invalid/fictional.git','ref':'refs/heads/fixture','incarnation':'fixture-ref-life','scope':'pkg','root':issuer,'authority':'Explicit fictional accepted association; no actual Root consent'}
  self.store.admit('pkg',self.config['roles']['Branch']['owner'],{'task_scopes':{},'resource_evidence':'Fictional original package before branch registration'})
  branches.register(self.store,issuer,receipt);branches.accept(self.store,receipt['id'],issuer,'Fictional SDK member genuinely accepts fixture association');self.branchid=receipt['id']
  adm={'task_scopes':{}}
  for task in ['branch-proposer','reviews-proposer','reviews-integrator']:
   adm['task_scopes'][task]={'cwd':str(self.repo),'read_roots':[str(self.area)],'write_roots':[],'network':False,'procedure':str(self.method),'resource_evidence':['explicit fictional original Branch owner']}
   if bound:adm['task_scopes'][task]['branch_binding']=self.branchid
  self.store.admit('pkg',self.config['roles']['Branch']['owner'],adm)
 def source_event(self,bound=True):
  packet={'component':'component','origin':'https://example.invalid/fictional.git','base':self.head,'head':self.head,'previous':None,'answered_ids':[]};body={'review':packet}
  if bound:body['branch_binding']=self.branchid
  return self.post(encode(body),'Reviews','pkg')
 def test_bound_source(self):
  self.init_native();e=self.source_event()
  try:
   with patch.object(processing,'map_input',side_effect=AssertionError('manual mapping forbidden')):asyncio.run(self.until(lambda:self.store.one("SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt WHERE j.task='work-proposer' AND a.collected IS NOT NULL"),n=18))
   self.assertEqual(len(self.transport.calls),2);self.assertEqual([x['opening'] for x in self.transport.calls],[True,False]);self.assertTrue(all(x['run']==self.transport.run for x in self.transport.calls))
   for task in ['reviews-integrator','work-proposer']:
    j=self.store.one('SELECT * FROM jobs WHERE task=?',(task,));call=next(c for c in self.models.calls if c['attempt']==j['active_attempt']);self.assertIn('QA472-FULL-NATIVE-REPORT',call['prompt']);self.assertIn(self.transport.run,call['prompt'])
   commits=self.store.rows("SELECT * FROM review_history_commits WHERE state='applied'");self.assertEqual(len(commits),1);self.assertIn('Explicit fictional history',Path(commits[0]['path']).read_text())
  finally:self.save('bound-source',{'native_calls':self.transport.calls,'review_contexts':self.store.rows('SELECT * FROM review_contexts'),'review_calls':self.store.rows('SELECT attempt,state FROM review_calls'),'history':self.store.rows('SELECT * FROM review_history_commits'),'git_ENDs':self.gitends})
