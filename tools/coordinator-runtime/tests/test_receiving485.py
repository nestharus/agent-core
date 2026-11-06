"""Bounded independent QA477 failure adaptation; explicit authored semantics."""
from _receiving485_fixtures import *
from coordinator_runtime import prospective, frontier
from coordinator_runtime import ordinary, configuration

class ContinuingTransport(FictionalNativeTransport):
 async def call(self,runtime,attempt,policy,context,directory,text,commands,opening=False,close=False):
  first=not any(c.get('attempt')==attempt for c in self.calls)
  result=await super().call(runtime,attempt,policy,context,directory,text,commands,opening,close)
  self.calls[-1]['attempt']=attempt
  if first:
   if runtime.attempt(attempt)['begin'] is None:runtime.begin(attempt,{'fictional_QA485_continuing_input':True})
   answer=json.loads(result[2]);answer['stage']='architecture';result=(result[0],result[1],encode(answer))
  return result

class Controls(Native):
 def test_withdrawal(self):
  self.init_native(); self.dispatch.reviews.transport=reviews.Native()
  e=self.source_event(); self.initial[e['id']]='reviews-proposer'
  asyncio.run(self.phase('schedule_classifications'))
  j=self.store.reserve(); a=self.store.start_job(j['id'],j['token'])
  b=self.boards['Reviews']; bind=b.bind_software_attempt
  def withdraw(*args):
   bind(*args)
   receipt=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('pkg',))['receipt'])
   receipt['task_scopes']['reviews-proposer']['read_roots']=[]
   receipt['task_scopes']['reviews-proposer']['write_roots']=[]
   self.store.admit('pkg',self.config['roles']['Branch']['owner'],receipt)
  with patch.object(b,'bind_software_attempt',new=withdraw), patch.object(reviews,'material',wraps=reviews.material) as acquire, patch('asyncio.create_subprocess_exec',side_effect=AssertionError('native start prohibited')) as start:
   asyncio.run(self.dispatch.execute_review(j,a,e['body']['review']))
  out=self.store.attempt(a)
  self.assertIsNone(out['begin']); self.assertIsNone(out['exit']); self.assertIsNotNone(out['collected'])
  self.assertTrue(json.loads(out['detail'])['known_not_started']); acquire.assert_not_called(); start.assert_not_called()
  self.assertIn('authority/admission differs',out['error'])
  self.save('withdrawal485', {'outcome':out, 'material_calls':acquire.call_count, 'native_starts':start.call_count})

 def test_narrow_initial_scope(self):
  self.init_native(); e=self.source_event(); self.initial[e['id']]='reviews-proposer'
  receipt=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('pkg',))['receipt'])
  receipt['task_scopes']['reviews-proposer']['read_roots']=[str(self.method)]
  self.store.admit('pkg',self.config['roles']['Branch']['owner'],receipt)
  asyncio.run(self.phase('schedule_classifications')); j=self.store.reserve(); a=self.store.start_job(j['id'],j['token'])
  with patch.object(reviews,'material',wraps=reviews.material) as acquire:
   asyncio.run(self.dispatch.execute_review(j,a,e['body']['review']))
  out=self.store.attempt(a); acquire.assert_not_called(); self.assertIsNone(out['begin']); self.assertIsNone(out['exit'])
  self.assertIn('outside current delegated task read authority',out['error'])
  self.save('narrow485', {'outcome':out,'material_calls':acquire.call_count})

 def test_exact_source_path_scope(self):
  self.init_native(); e=self.source_event(); self.initial[e['id']]='reviews-proposer'
  receipt=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('pkg',))['receipt'])
  receipt['task_scopes']['reviews-proposer']['read_roots']=[str(self.repo/'code.py')]
  self.store.admit('pkg',self.config['roles']['Branch']['owner'],receipt)
  asyncio.run(self.until(lambda:len(self.transport.calls)==2,n=12))
  self.assertEqual(len(self.transport.calls),2)
  self.save('exact-path485',{'native_calls':self.transport.calls})

 def test_collector_result(self):
  self.init_native(); e=self.source_event(); self.initial[e['id']]='reviews-proposer'
  def settled():
   return self.store.one("SELECT id FROM outboxes WHERE kind='result' AND role='Reviews' AND recipient='Reviews' AND state='settled' AND processed_at IS NOT NULL")
  with patch.object(self.boards['Reviews'],'collect_owner_return',wraps=self.boards['Reviews'].collect_owner_return) as external:
   asyncio.run(self.until(settled,n=18))
   external.assert_not_called()
  row=self.store.one("SELECT * FROM outboxes WHERE kind='result' AND role='Reviews' AND recipient='Reviews'")
  receipt=json.loads(row['board_receipt']); s=receipt['settlement']
  self.assertFalse(s['native_receipt']); self.assertFalse(s['genuine_owner_full_read'])
  self.assertEqual(s['evidence']['result_hash'],digest(json.loads(self.store.attempt(s['evidence']['attempt'])['result'])))
  self.assertNotIn('result',s); self.assertIsNone(row['error'])
  self.save('collector485',{'outbox':row,'receipt':receipt,'native_calls':self.transport.calls})

class Unbound(Controls):
 def configure_fixture(self):
  super().configure_fixture()
  self.config['local_integration']['tasks']['work-proposer']['points']=['a','b']
  self.config['tasks']['reviews-proposer']['require_package_scope']=False
 def test_independent_unbound(self):
  self.init_native(bound=False)
  packet={'component':'component','origin':'https://example.invalid/fictional.git','base':self.head,'head':self.head,'previous':None,'answered_ids':[]}
  e=self.post(encode({'review':packet}),'Reviews',None)
  self.initial[e['id']]='reviews-proposer'
  asyncio.run(self.until(lambda:len(self.transport.calls)==2,n=12))
  j=self.store.one("SELECT * FROM jobs WHERE task='reviews-proposer'")
  self.assertIsNone(j['package']); self.assertEqual(len(self.transport.calls),2)
  self.save('unbound485',{'job':j,'native_calls':self.transport.calls})

class Mixed(Controls):
 def configure_fixture(self):
  super().configure_fixture()
  self.config['local_integration']['tasks']['work-proposer']['points']=['a','b']
  self.output=self.area/'qa-output';self.output.mkdir()
  self.marker=self.output/'marker.json'
  # Independent fictional behavior: exact frozen source, read-only candidate,
  # separate output and independently checked value. No production oracle.
  runner='''from pathlib import Path
import errno,json
source=Path("code.py")
assert source.read_text() == 'print("fictional frozen source")\\n'
try: source.write_text("prohibited candidate mutation")
except OSError as e: assert e.errno == errno.EROFS
else: raise AssertionError("candidate was writable")
Path(MARKER).write_text(json.dumps({"value":485,"candidate_readonly":True}))
'''.replace('MARKER',repr(str(self.marker)))
  readback='''from pathlib import Path
import json
assert json.loads(Path(MARKER).read_text()) == {"value":485,"candidate_readonly":True}
print("verified-485")
'''.replace('MARKER',repr(str(self.marker)))
  (self.repo/'runner.py').write_text(runner);(self.repo/'readback.py').write_text(readback)
  self.git('add','runner.py','readback.py');self.git('-c','user.name=Fictional QA485','-c','user.email=qa485@example.invalid','commit','-m','Independent QA485 behavior procedure');self.head=self.git('rev-parse','HEAD')
  for name in ['qa-execution','qa-cleanup','branch-integrator']:
   t=self.config['tasks'][name];t.update(require_package_scope=True,scope_roots=[str(self.area)])
  self.config['tasks']['qa-execution'].update(effects='owner-reconcile',capacity=5,responses={'consolidated':['qa-cleanup']})
  self.config['tasks']['qa-cleanup'].update(responses={'qualification':['branch-integrator']},allowed_handoffs=['Branch'],publish_internal_results=True)
  self.config['tasks']['reviews-integrator']['software_handoffs']={'Work':['work-proposer']}
  self.config['tasks']['qa-cleanup']['software_handoffs']={'Branch':['branch-integrator']}
  self.config['tasks']['qa-execution']['software_handoffs']={'Work':['work-proposer']}
  self.config['tasks']['branch-proposer']['software_handoffs']={'Work':['work-proposer']}
  self.config['tasks']['branch-integrator']['software_handoffs']={'Work':['work-proposer']}
  configuration.apply_scope_options(copy.deepcopy(self.config),self.config,{'package_scoped_cleanup':['qa-cleanup']})
 def configure_selection(self,s):
  super().configure_selection(s)
  s['metadata_lookup']['tasks'].append('work-proposer') if 'work-proposer' not in s['metadata_lookup']['tasks'] else None
 def init_mixed(self):
  self.init_native()
  self.transport=ContinuingTransport();self.dispatch.reviews.transport=self.transport
  policies={n:{'task_hash':digest(t),'software_handoffs':t.get('software_handoffs',{}),'ordinary_effects':'admitted-v1' if n=='qa-execution' else False} for n,t in self.config['tasks'].items()}
  grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']}
  self.epoch=prospective.select(self.store,self.config['roles']['Work']['owner'],{'configuration':digest(self.config),'authority':'Fictional exact485 future receivers and QA effects; no live permission','expires':self.store.clock()+3600,'grants':grants,'tasks':policies,'processing_capability':self.key})
  sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
  python='/usr/bin/python3.12'
  def command(script,stdout):return {'argv':[python,'-B',str(self.repo/script)],'executable_sha256':sha(python),'script_sha256':sha(self.repo/script),'stdout':stdout}
  p={'kind':'local-qa','git':'/usr/bin/git','git_sha256':sha('/usr/bin/git'),'repository':str(self.repo),'source_ref':'refs/heads/fixture','source_head':self.head,'procedure_sha256':sha(self.method),'resources':[{'key':'fixture485-output','owner':self.config['roles']['Work']['owner'],'authority':'Fictional independent output lease','expires':self.store.clock()+3600}],'acceptor':self.config['roles']['Work']['owner'],'acceptance_authority':'Independent fictional Work checks QA485 behavior','timeout':30,'max_output':4096,'command':command('runner.py',''),'readback':command('readback.py','verified-485\n'),'known_exits':[0,1],'source_capture':{'bwrap':'/usr/bin/bwrap','sha256':sha('/usr/bin/bwrap'),'max_bytes':1048576,'max_files':16},'public_executables':{role:{'path':python,'bytes':Path(python).stat().st_size,'sha256':sha(python)} for role in ['command','readback']}}
  scopes={n:{'cwd':str(self.repo),'read_roots':[str(self.repo),str(self.method)],'write_roots':[str(self.output)] if n=='qa-execution' else [],'network':False,'procedure':str(self.method),'resource_evidence':['Fictional separately narrowed '+n]} for n in ['qa-execution','qa-cleanup','branch-integrator']}
  scopes['qa-execution']['ordinary_effects']=p
  self.store.admit('qa-485',self.config['roles']['Branch']['owner'],{'task_scopes':scopes})
  self.task_result=self.meaning
  self.pause_receivers=True;self.unknown=False
  schedule=self.dispatch.schedule_candidate
  def candidate(job):
   if self.pause_receivers and job['task'] in {'work-proposer','branch-integrator'}:return False
   return schedule(job)
  self.dispatch.schedule_candidate=candidate
 def meaning(self,j,out):
  if j['task']=='qa-cleanup':out['category']='qualification'
  if j['task'] in {'qa-execution','branch-proposer','branch-integrator'}:
   out['handoffs']=[{'recipient':'Work','kind':'work','text':'Read and account for exact fictional '+j['task']+' outcome; no acceptance or business execution delegated','ref':j['package'],'required':'settled'}]
   out['no_handoff_reason']=None
  if self.unknown and j['task']=='work-proposer':
   out['semantic']='UNKNOWN';out['unknowns']=['Fictional independent downstream question remains unanswered']
 async def step(self):
  await self.dispatch.tick();await self.drain()
 async def drive(self,predicate,n=32):
  for _ in range(n):
   await self.step()
   if predicate():return
  raise AssertionError('485 predicate unreached '+repr(self.dispatch.runtime_errors))
 def cross(self):
  return self.store.rows("SELECT o.* FROM outboxes o JOIN jobs j ON j.id=o.job WHERE o.kind='result' AND ((j.task='reviews-integrator' AND o.recipient='Work') OR (j.task='qa-cleanup' AND o.recipient='Branch'))")
 async def accept_qa(self):
  row=self.store.one("SELECT * FROM ordinary_runs WHERE state='reconciled'")
  self.assertIsNotNone(row)
  for actor_id in [self.config['actor'],self.store.controller,self.store.attempt(row['attempt'])['session']]:
   with self.assertRaises(Refusal):await ordinary.accept(self.store,actor_id,row['attempt'],'accepted',{'execution_hash':digest(json.loads(row['receipt'])),'rationale':'Independent fictional specification','unknowns':[]})
  return await ordinary.accept(self.store,self.config['roles']['Work']['owner'],row['attempt'],'accepted',{'execution_hash':digest(json.loads(row['receipt'])),'rationale':'Observed frozen source plus kernel EROFS and independent exact485 marker readback satisfy the authored procedure','unknowns':[]})
 def test_continuing_receiving(self):
  self.init_mixed();cfg=digest(self.config)
  source=self.source_event();self.initial[source['id']]='reviews-proposer'
  q=self.post('Execute independent exact485 QA procedure','QA','qa-485');self.initial[q['id']]='qa-execution'
  b=self.post('Bounded Branch handoff on original package','Branch','pkg');self.initial[b['id']]='branch-proposer'
  w=self.post('Independent ordinary Work read and account','Work');self.initial[w['id']]='work-proposer'
  async def run():
   await self.drive(lambda:self.store.one("SELECT * FROM ordinary_runs WHERE state='reconciled'"))
   self.assertFalse(ordinary.accepted_package(self.store,'qa-485'))
   self.assertFalse(self.store.one("SELECT id FROM jobs WHERE task='qa-cleanup'"))
   self.acceptance=await self.accept_qa()
   await self.drive(lambda:len(self.cross())==2 and all(self.store.one('SELECT event FROM processing_delivery_links WHERE delivery=?',(o['id'],)) for o in self.cross()))
   for o in self.cross():
    self.assertFalse(frontier.delivery(self.store,o['id'])['complete'])
    self.assertIsNone(o['processed_at']);self.assertNotEqual(o['state'],'settled')
   self.pause_receivers=False
   await self.drive(lambda:len(self.cross())==2 and all(o['state']=='settled' and o['processed_at'] is not None and self.store.one('SELECT processed_at FROM events WHERE id=?',(o['event'],))['processed_at'] is not None for o in self.cross()))
   for o in self.cross():
    link=self.store.one('SELECT event FROM processing_delivery_links WHERE delivery=?',(o['id'],))
    self.assertEqual(o['event'],link['event']);self.assertTrue(frontier.delivery(self.store,o['id'])['complete'])
    self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(link['event'],))['processed_at'])
    self.assertFalse(json.loads(o['board_receipt'])['settlement']['native_receipt'])
   # A continuing later input in the SAME config/epoch carries an actual
   # unanswered downstream result. Keep that adverse duty, don't clear it.
   self.unknown=True
   packet={'component':'component','origin':'https://example.invalid/fictional.git','base':self.head,'head':self.head,'previous':self.head,'answered_ids':[]}
   later=self.post(encode({'review':packet,'branch_binding':self.branchid}),'Reviews','pkg');self.initial[later['id']]='reviews-proposer'
   await self.drive(lambda:self.store.one("SELECT id FROM jobs WHERE task='work-proposer' AND state='held'"))
   unknowns=[self.store.attempt(j['active_attempt']) for j in self.store.rows("SELECT * FROM jobs WHERE task='work-proposer' AND state='held'") if j['active_attempt']]
   self.assertTrue(any(json.loads(a['result'])['semantic']=='UNKNOWN' and 'Fictional independent downstream question remains unanswered' in json.loads(a['result'])['unknowns'] for a in unknowns if a['result']))
   held=[o for o in self.cross() if not frontier.delivery(self.store,o['id'])['complete']]
   self.assertTrue(held);self.assertTrue(all(o['processed_at'] is None for o in held))
   self.assertEqual({a['profile'] for a in self.store.rows('SELECT profile FROM attempts')},set(self.config['profiles']))
   self.assertEqual(self.transport.run,self.store.one('SELECT run FROM review_contexts')['run'])
   self.assertEqual(len(self.transport.calls),4)
   for j in self.store.rows("SELECT * FROM jobs WHERE task='work-proposer' AND state='closed'"):
    answer=json.loads(self.store.attempt(j['active_attempt'])['result'])
    self.assertEqual([x['step'] for x in answer['completion']['integration_steps']],list(local.STEPS))
   self.assertEqual(cfg,digest(self.config));self.assertEqual(self.epoch['id'],self.store.one('SELECT id FROM prospective_authorities')['id'])
  try:asyncio.run(run())
  finally:self.save('mixed485',{'cross':self.cross(),'outboxes':self.store.rows('SELECT * FROM outboxes'),'acceptances':self.store.rows('SELECT * FROM ordinary_acceptance'),'ordinary_tools':self.store.rows('SELECT * FROM ordinary_tool_records'),'delivery_links':self.store.rows('SELECT * FROM processing_delivery_links'),'queues':self.store.rows('SELECT * FROM queue')})

 def test_missing_receiver_authority(self):
  # Authored omission is fixed BEFORE selection/source birth. A real absent
  # receiver policy must remain an operator return; no pickup/settlement minted.
  self.init_mixed()
  e=self.source_event();self.initial[e['id']]='reviews-proposer';self.pause_receivers=False
  async def run():
   await self.drive(lambda:bool(self.cross()) and any(o['error'] for o in self.cross()))
   o=self.cross()[0];self.assertIsNone(o['processed_at']);self.assertNotEqual(o['state'],'settled')
   self.assertFalse(self.store.one('SELECT event FROM processing_delivery_links WHERE delivery=?',(o['id'],)))
   receipt=self.boards['Reviews'].delivery_status(o['id']);self.assertIsNone(receipt['pickup']);self.assertIsNone(receipt['settlement'])
  try:asyncio.run(run())
  finally:self.save('missing-receiver485',{'cross':self.cross()})

 def test_qa_capacity(self):
  self.init_mixed()
  admission=json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('qa-485',))['receipt'])
  for i in range(1):
   package='capacity-'+str(i);self.store.admit(package,self.config['roles']['Branch']['owner'],admission)
   e=self.post('Fictional distinct first-phase package '+str(i),'QA',package);self.initial[e['id']]='qa-execution'
  async def classify():
   for _ in range(8):
    await self.phase('schedule_classifications');self.dispatch.reconcile_classifications();await self.phase('receipts')
  asyncio.run(classify())
  jobs=[self.store.reserve()];self.assertIsNotNone(jobs[0])
  # New source in the SAME package remains queued beside its frozen original.
  e=self.post('Second continuing source in existing capacity package','QA',jobs[0]['package']);self.initial[e['id']]='qa-execution'
  asyncio.run(self.phase('schedule_classifications'));self.assertIsNone(self.store.reserve())
  self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM jobs WHERE package=?',(jobs[0]['package'],))['n'],1)
  for i in range(1,6):
   package='capacity-'+str(i);self.store.admit(package,self.config['roles']['Branch']['owner'],admission)
   e=self.post('Distinct independent execution '+str(i),'QA',package);self.initial[e['id']]='qa-execution'
  asyncio.run(classify())
  jobs.extend(self.store.reserve() for _ in range(4))
  self.save('capacity485',{'execution_jobs':jobs,'queues':self.store.rows('SELECT * FROM queue')})
  self.assertTrue(all(jobs));self.assertEqual(len({j['package'] for j in jobs}),5);self.assertIsNone(self.store.reserve())
  # Narrow cleanup remains a separate slot while all five execution slots live.
  e=self.post('Separately admitted bounded cleanup metadata','QA','qa-485');self.initial[e['id']]='qa-cleanup'
  # The general native classifier defaults board posts to their first route;
  # this explicit future fictional source has only the cleanup route.
  classify_run=self.models.run
  async def route(store,attempt,prompt,spec,schema):
   out=await classify_run(store,attempt,prompt,spec,schema)
   a=store.attempt(attempt)
   if a['kind']=='classifier' and a['event']==e['id']:out['result']['task']='qa-cleanup'
   return out
  self.models.run=route
  asyncio.run(self.phase('schedule_classifications'))
  self.assertIsNone(self.store.reserve())
  self.save('capacity485',{'execution_jobs':jobs,'cleanup':'held behind unfinished first phase; actual cleanup execution is separately exercised by mixed485','meaning':'Reservations only; no worker/model/QA execution starts or fabricated collection'})

 def test_due_alerts(self):
  self.init_mixed();now=[self.store.clock()];self.store.clock=lambda:now[0]
  self.store.record_operational_error('fixture485-due',{'reason':'unchanged fictional violated duty'},'Work','fixture485')
  self.store.emit_alerts();first=self.store.one("SELECT COUNT(*) AS n FROM alerts WHERE subject='fixture485-due'")['n'];self.assertEqual(first,1)
  self.store.emit_alerts();self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM alerts WHERE subject='fixture485-due'")['n'],first)
  now[0]+=self.config['deadlines']['alert_interval']+0.1;self.store.emit_alerts();self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM alerts WHERE subject='fixture485-due'")['n'],first+1)
  self.store.clear_operational_error('fixture485-due');now[0]+=self.config['deadlines']['alert_interval']+0.1;self.store.emit_alerts();self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM alerts WHERE subject='fixture485-due'")['n'],first+1)
  self.save('cadence485',{'alerts':self.store.rows("SELECT * FROM alerts WHERE subject='fixture485-due'"),'meaning':'logical due clock and actual alert journal; no live transport claim'})

class MissingReceiver(Mixed):
 def configure_fixture(self):
  super().configure_fixture();self.config['tasks']['reviews-integrator']['software_handoffs']={}

def load_tests(loader, tests, pattern):
 """Select the bounded controls without rerunning inherited fixture methods."""
 return unittest.TestSuite(
  [Controls(n) for n in ['test_withdrawal','test_narrow_initial_scope',
   'test_exact_source_path_scope','test_collector_result','test_bound_source']]
  + [Unbound('test_independent_unbound'), Mixed('test_continuing_receiving'),
     MissingReceiver('test_missing_receiver_authority'), Mixed('test_qa_capacity'),
     Mixed('test_due_alerts')])

if __name__ == '__main__':
 unittest.main(verbosity=2)
