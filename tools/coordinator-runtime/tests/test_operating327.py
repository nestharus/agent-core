"""Isolated service/ordinary composition, with explicitly synthetic logical actors.

Native/profile/session/turn/provider encounters remain unobserved NULL. Public
source is RO, only private owned fixtures are writable, and network is absent.
Original membership/config validation/allocation seams come from configuration308;
no production effect, source, authority, acceptance or routing validator is patched.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from coordinator_runtime import branches, capacity, cli, configuration, ordinary, processing, prospective, qa_source, ref_scope, service
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
from coordinator_runtime.dispatcher import job_prompt
import test_configuration308 as fixture

ACCEPTOR = '11111111-1111-4111-8111-111111111111'  # synthetic semantic actor, no native identity


class Composition(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        original_engine = fixture.engine_config
        def original_config(directory):
            value = original_engine(directory)
            for name, old in [('branch-integrator', 'bi'), ('qa-execution', 'qe')]:
                value['tasks'][name] = {**copy.deepcopy(value['tasks'][old]), 'require_package_scope': True,
                                       'scope_roots': ['/fixtures'], 'effects': 'owner-reconcile'}
            value['tasks']['ri'].update(execution='model', responses={'consolidated': ['wp']}, delivery_required=True)
            # Genuine production recipient checks use these synthetic memberships.
            value['delivery']['recipients'] = {'Work': {'session': 'fictional-Work'}}
            return value
        original_store = fixture.Store
        def original_runtime(value, **kwargs):
            value['delivery']['recipients'] = {'Work': {'session':'fictional-Work','board_role':'fictional','profile':None},
                'Root': {'session':'synthetic-existing-root','board_role':'execution-manager','profile':None}}
            value['delivery']['recipients'].update({r:{'session':'fictional-'+r,'board_role':'fictional','profile':None} for r in value['roles']})
            value['deadlines']['task'] = 10
            value['limits'].update(max_alerts=64, max_alert_debt=128)
            for task in value['tasks'].values(): task['templates']=[]
            value['tasks']['branch-integrator']['effect_authority']['operations'].append('organize-authorized-refs')
            report_cwd=Path(value['state_dir']).parent/'new-report-work';report_cwd.mkdir()
            value['tasks']['ri'].update(cwd=str(report_cwd))
            value['tasks']['ri']['effect_authority']['read_roots']=[str(report_cwd)]
            value['tasks']['qa-execution']['responses']={'consolidated':['qc']}
            value['tasks']['qc'].update(cwd=str(report_cwd), responses={'qualification':['bi']})
            value['tasks']['qc']['effect_authority']['read_roots']=[str(report_cwd)]
            return original_store(value, **kwargs)
        with patch.object(fixture, 'engine_config', side_effect=original_config), patch.object(fixture, 'Store', side_effect=original_runtime):
            self.f.setUp()
        f = self.f
        # No config transition is needed to test the bridge: all original grant
        # configuration bytes remain identical, stopped, and immutable.
        self.s = f.runtime
        self.boards = f.boards
        for board in self.boards.values():board.store.active_listener=f.public.active_listener
        # Complete the ORIGINAL synthetic outgoing grant construction, before
        # this service selection. No production grant/validator is bypassed.
        recipients = {k:v['session'] for k,v in self.s.config['delivery']['recipients'].items()}
        f.conn.execute('UPDATE coordinator_delivery_grants_v1 SET recipients=?,kinds=?',
                       (encode(recipients),encode(['work','result','question','alert','effect-request'])))
        f.conn.execute("INSERT INTO sessions(session,campaign,role,profile,status,registered_at,last_seen_at) VALUES('synthetic-existing-root','synthetic','execution-manager',NULL,'active','synthetic-time','synthetic-time')")
        self.repo = f.directory/'candidate'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('remote', 'add', 'origin', 'https://example.invalid/synthetic')
        (self.repo/'module.txt').write_text('synthetic before\n')
        self.git('add', 'module.txt'); self.git('commit', '-qm', 'synthetic before')
        self.old = self.git('rev-parse', 'HEAD')
        (self.repo/'module.txt').write_text('synthetic candidate\n')
        self.git('add', 'module.txt'); self.git('commit', '-qm', 'synthetic candidate')
        self.head = self.git('rev-parse', 'HEAD')
        self.git('update-ref', 'refs/heads/source', self.head)
        self.git('update-ref', 'refs/heads/target', self.old)
        self.procedure = f.directory/'procedure.txt'; self.procedure.write_text('synthetic independent procedure\n')
        self.output = f.directory/'output'; self.output.mkdir()
        self.held = f.directory/'held-old'; self.held.mkdir()
        policy = f.processing_selection()
        policy.pop('expires'); policy.pop('max_starts')
        policy['service'] = {'max_inflight': 5, 'reviews': {}, 'report_tasks': ['ri'],
                             'admission': {'until':1600.,'pause_bytes':16*1024*1024,'max_new_inputs':2},
                             'legacy_resources': {r: {'original_hold': 'fictional unresolved original '+r,
                               'roots': [str(self.held)], 'unbounded': False,
                               'evidence': 'synthetic exact old resource account; original history remains owned'}
                                 for r in self.s.config['roles']}}
        # The original Work job has an unknown resource map and correctly fences
        # Work integration. Other roles retain their own independent accounts.
        self.cap = processing.select(self.s, self.boards, policy)['capability']
        self.s.processing = processing.Access(self.s, self.cap, self.boards)
        self.original_grants = [tuple(r) for r in f.conn.execute('SELECT * FROM coordinator_grants_v1')]

    def git(self, *args):
        return subprocess.check_output(['/usr/bin/git', '-C', str(self.repo), *args], stderr=subprocess.STDOUT).decode().strip()

    def authorize(self, tasks=('branch-integrator', 'qa-execution', 'ri', 'wp')):
        selection = {'configuration': digest(self.s.config), 'authority': 'synthetic Work selected service and scoped ordinary outcomes',
                     'expires': 2000., 'processing_capability': self.cap,
                     'grants': {self.s.config['tasks'][t]['role']: 'fictional-grant-'+self.s.config['tasks'][t]['role'] for t in tasks},
                     'tasks': {t: {'task_hash': digest(self.s.config['tasks'][t]), 'software_handoffs': {},
                                  'ordinary_effects': t in {'branch-integrator','qa-execution'}} for t in tasks}}
        self.epoch = prospective.select(self.s, 'fictional-Work', selection)['id']
        return selection

    def scope(self, kind):
        p = {'kind': kind, 'git': '/usr/bin/git', 'git_sha256': hashlib.sha256(Path('/usr/bin/git').read_bytes()).hexdigest(),
             'repository': str(self.repo), 'source_ref': 'refs/heads/source', 'source_head': self.head,
             'procedure_sha256': hashlib.sha256(self.procedure.read_bytes()).hexdigest(),
             'resources': [{'key': 'synthetic-'+kind, 'owner': ACCEPTOR, 'authority': 'synthetic resource entitlement', 'expires': 2000.}],
             'acceptor': ACCEPTOR, 'acceptance_authority': 'synthetic independent intent and acceptance delegation',
             'timeout': 1, 'max_output': 65536}
        if kind == 'local-ref':
            p.update(ref='refs/heads/target', before=self.old, target=self.head)
        else:
            for name, text in [('run', "from pathlib import Path\nPath(%r).write_text('candidate ran')\n" % str(self.output/'outcome')),
                               ('check', "from pathlib import Path\nassert Path(%r).read_text() == 'candidate ran'\nprint('known effect')\n" % str(self.output/'outcome'))]:
                path=self.repo/name; path.write_text('#!/usr/bin/python3\n'+text); path.chmod(0o755)
            self.git('add', 'run', 'check'); self.git('commit', '-qm', 'synthetic QA harness')
            self.head=self.git('rev-parse','HEAD'); self.git('update-ref','refs/heads/source',self.head)
            p['source_head']=self.head
            def command(name, stdout):
                return {'argv':[str(self.repo/name)], 'executable_sha256':hashlib.sha256((self.repo/name).read_bytes()).hexdigest(), 'stdout':stdout}
            p.update(command=command('run',''), readback=command('check','known effect\n'), known_exits=[0,1],
                     source_capture={'bwrap':'/usr/bin/bwrap','sha256':hashlib.sha256(Path('/usr/bin/bwrap').read_bytes()).hexdigest(),
                                     'max_bytes':65536,'max_files':20})
        return {'cwd':str(self.repo), 'read_roots':[str(self.repo),str(self.procedure)],
                'write_roots':[str(self.repo)] if kind=='local-ref' else [str(self.output)],
                'procedure':str(self.procedure),'resource_evidence':'synthetic exact current independent resource custody', 'ordinary_effects':p}

    def admit_ref(self, package):
        scope=self.scope('local-ref');scope['branch_binding']='synthetic-effect-branch'
        self.s.admit(package,'fictional-Branch',{'task_scopes':{'branch-integrator':scope}})
        coordinator='33333333-3333-4333-8333-333333333333'  # synthetic logical coordinator only
        self.f.conn.execute("INSERT INTO sessions(session,campaign,role,profile,status,registered_at,last_seen_at) VALUES(?,'synthetic','work-coordinator',NULL,'active','synthetic-time','synthetic-time')",(coordinator,))
        branches.register(self.s,'fictional-Work',{'id':'synthetic-effect-branch','repository':str(self.repo),
            'origin':'https://example.invalid/synthetic','ref':'refs/heads/target','incarnation':'synthetic-effect-incarnation',
            'scope':package,'root':coordinator,'authority':'synthetic exact scoped delegation'})
        branches.accept(self.s,'synthetic-effect-branch',coordinator,'synthetic actual scoped coordinator acceptance')
        basis=ref_scope.material(self.s,'branch-integrator',package)
        receipt={'basis':basis,'authority':'synthetic Branch custodian qualifies only exact prospective refs',
            'originals':[{'original':'synthetic original control reference','collector':'fictional-Branch',
                          'activity':'closed','actual_END':0,'evidence':'synthetic attributed original control activity return'}],
            'activity_scope':{'original_hold':basis['original_hold'],
                'operation':digest({'operation':basis['operation'],'repository':basis['common_repository'],'refs':basis['local_refs']}),
                'no_active_writers':True,'evidence':'synthetic actual current control of these exact common refs'},
            'remaining_holds':[basis['original_hold']],'past_effects':['synthetic old effects remain UNKNOWN and charged']}
        self.assertTrue(ref_scope.account(self.s,'fictional-Branch',receipt))
        return scope

    def queue(self, task, package=None, existing=None):
        role=self.s.config['tasks'][task]['role']
        event=existing or {'id':'synthetic-input-'+task,'role':role,'recipient':'fictional-'+role,'author':'synthetic-submitter',
                          'kind':'board','post':100,'body':'synthetic scoped request','package':package,'allowed_tasks':[task]}
        if not existing:self.s.ingest(event)
        self.s.db.execute("UPDATE events SET state='queued',ack='internal' WHERE id=?",(event['id'],))
        self.s.db.execute("INSERT INTO queue VALUES(?,?,?,?,?,?,'queued',NULL)",
                          (event['id'],event['id'],role,self.s.config['tasks'][task]['phase'],task,package))
        job=self.s.reserve(); self.assertIsNotNone(job)
        attempt=self.s.start_job(job['id'],job['token']);job=self.s.job(job['id'])
        admission=self.s.one('SELECT * FROM admissions WHERE package=?',(package,))
        self.boards[role].bind_software_attempt(self.s,job,attempt,admission)
        return job,attempt

    def collect(self, attempt, answer=None):
        answer=answer or {'semantic':'DONE','summary':'synthetic collected preparation','findings':[],'failures':[],'unknowns':[],
                         'artifacts':[],'category':'complete','handoffs':[],'no_handoff_reason':'synthetic internal result only'}
        self.s.begin(attempt,{'validation_seam':'synthetic logical worker; real local Python END, no native encounter'})
        child=subprocess.Popen([sys.executable,'-c','import sys;sys.stdout.write(sys.stdin.read())'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=child.communicate(encode(answer).encode());self.assertEqual(err,b'')
        self.s.collect(attempt,{'exit':child.returncode,'capture':'complete','cleanup':'owned local producer','error':None,
                               'result':json.loads(out),'detail':{'tool_completion':{'complete':True,'items':[]}}})
        actual=self.s.attempt(attempt)
        self.assertTrue(all(actual[k] is None for k in ('profile','session','turn')))

    def test_continuing_authority_real_ref_effect_and_independent_acceptance(self):
        self.authorize();scope=self.admit_ref('synthetic-ref')
        job,attempt=self.queue('branch-integrator','synthetic-ref');self.collect(attempt)
        self.assertEqual(prospective.for_job(self.s,self.s.job(job['id']))['id'],self.epoch)
        self.assertTrue(asyncio.run(ordinary.perform(self.s,self.boards['Branch'],self.s.job(job['id']))))
        self.assertEqual(self.git('rev-parse','refs/heads/target'),self.head)
        run=self.s.one('SELECT * FROM ordinary_runs WHERE attempt=?',(attempt,));receipt=json.loads(run['receipt'])
        self.assertEqual(run['state'],'reconciled');self.assertEqual(receipt['unknown_effects'],[])
        self.assertEqual(receipt['before']['ALLparents'],[self.old])
        self.assertEqual(receipt['before']['origin'],'https://example.invalid/synthetic')
        self.assertEqual(receipt['before']['fullref'],'refs/heads/source')
        self.assertEqual(receipt['before']['branch']['incarnation'],'synthetic-effect-incarnation')
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_acceptance'),[])
        evidence={'execution_hash':digest(receipt),'rationale':'synthetic independent target and result comparison','unknowns':[]}
        with self.assertRaises(Refusal):asyncio.run(ordinary.accept(self.s,self.s.controller,attempt,'accepted',evidence))
        accepted=asyncio.run(ordinary.accept(self.s,ACCEPTOR,attempt,'accepted',evidence))
        self.assertEqual(accepted['decision'],'accepted')
        self.assertEqual(self.original_grants,[tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')])
        self.assertEqual(self.s.job('fictional-old-job')['effects'],'unknown')
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM outboxes')['n'],67)
        self.assertTrue(all(json.loads(r['record'])['complete'] for r in self.s.rows("SELECT record FROM ordinary_tool_records WHERE json_extract(record,'$.ended') IS NOT NULL")))
        self.assertTrue(self.s.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'])

    def test_real_QA_candidate_runner_and_separate_acceptance(self):
        self.authorize();scope=self.scope('local-qa')
        self.s.admit('synthetic-qa','fictional-Branch',{'task_scopes':{'qa-execution':scope}})
        job,attempt=self.queue('qa-execution','synthetic-qa');self.collect(attempt)
        self.assertTrue(asyncio.run(ordinary.perform(self.s,self.boards['QA'],self.s.job(job['id']))))
        receipt=json.loads(self.s.one('SELECT receipt FROM ordinary_runs WHERE attempt=?',(attempt,))['receipt'])
        association=qa_source.verify(self.s,attempt,scope['ordinary_effects'],receipt)
        self.assertEqual(association['head'],self.head);self.assertEqual((self.output/'outcome').read_text(),'candidate ran')
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_acceptance'),[])
        evidence={'execution_hash':digest(receipt),'rationale':'synthetic semantic verification','unknowns':[]}
        self.git('remote','set-url','origin','https://example.invalid/synthetic-changed')
        with self.assertRaisesRegex(Refusal,'source identity changed'):asyncio.run(ordinary.accept(self.s,ACCEPTOR,attempt,'accepted',evidence))
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_acceptance'),[])
        self.git('remote','set-url','origin','https://example.invalid/synthetic')
        accepted=asyncio.run(ordinary.accept(self.s,ACCEPTOR,attempt,'accepted',evidence))
        self.assertEqual(accepted['decision'],'accepted')

    def test_original_collector_resumes_qualification_after_actual_independent_acceptance(self):
        self.authorize(tasks=('qa-execution','qc','wp'))
        scope=self.scope('local-qa')
        self.s.admit('synthetic-qa','fictional-Branch',{'task_scopes':{'qa-execution':scope}})
        job,attempt=self.queue('qa-execution','synthetic-qa')
        answer={'semantic':'DONE','summary':'synthetic QA preparation','findings':[],'failures':[],'unknowns':[],
                'artifacts':[],'category':'consolidated','handoffs':[],'no_handoff_reason':'separate one-package consolidation follows'}
        self.collect(attempt,answer)
        asyncio.run(ordinary.perform(self.s,self.boards['QA'],self.s.job(job['id'])))
        response=self.s.finish_job(job['id'],job['token'])
        cleanup,ca=self.queue('qc','synthetic-qa',existing=self.s.event(response))
        self.collect(ca,{**answer,'category':'qualification','summary':'synthetic consolidation retains independent acceptance boundary'})
        ordinary.wait_for_acceptance(self.s,self.s.job(cleanup['id']))
        dispatcher=service.Dispatcher(self.s,self.boards,models=object())
        count=self.s.one('SELECT COUNT(*) AS n FROM attempts')['n']
        async def resume():
            dispatcher.reconcile_collected(self.s.job(cleanup['id']))
            self.assertEqual(len(dispatcher.active),0)
            receipt=json.loads(self.s.one('SELECT receipt FROM ordinary_runs WHERE attempt=?',(attempt,))['receipt'])
            await ordinary.accept(self.s,ACCEPTOR,attempt,'accepted',{'execution_hash':digest(receipt),'rationale':'synthetic actual independent QA decision','unknowns':[]})
            dispatcher.reconcile_collected(self.s.job(cleanup['id']))
            dispatcher.reconcile_collected(self.s.job(cleanup['id']))
            self.assertEqual(len(dispatcher.active),1)
            await asyncio.gather(*dispatcher.active)
        asyncio.run(resume())
        closed=self.s.job(cleanup['id'])
        self.assertEqual(closed['controller'],self.s.controller);self.assertEqual(closed['active_attempt'],ca)
        self.assertEqual(closed['state'],'closed');self.assertIsNone(closed['hold_reason'])
        self.assertFalse(ordinary.awaiting_acceptance(self.s,closed))
        self.assertTrue(ordinary.qualification_current(self.s,closed))
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM attempts')['n'],count)
        self.assertEqual(self.s.event(closed['response'])['role'],'Branch')
        self.assertEqual(self.s.rows('SELECT * FROM recovery_requests'),[])

    def test_legacy_borrowed_mixed_stale_and_revoked_authority_refuse(self):
        self.authorize();scope=self.admit_ref('synthetic-ref')
        job,attempt=self.queue('branch-integrator','synthetic-ref');self.collect(attempt)
        old=self.s.job('fictional-old-job');self.assertIsNone(prospective.for_job(self.s,old))
        detail=self.s.attempt(attempt)['detail'];changed=json.loads(detail);changed['processing_capability']='synthetic-borrowed'
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(changed),attempt))
        with self.assertRaises(Refusal):asyncio.run(ordinary.perform(self.s,self.boards['Branch'],self.s.job(job['id'])))
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',(detail,attempt))
        members=json.loads(job['members']);members.append({'event':self.f.originals[0]['id'],'hash':digest(self.f.originals[0])})
        self.s.db.execute('UPDATE jobs SET members=? WHERE id=?',(encode(members),job['id']))
        self.assertIsNone(prospective.for_job(self.s,self.s.job(job['id'])))
        self.s.db.execute('UPDATE jobs SET members=? WHERE id=?',(job['members'],job['id']))
        self.git('update-ref','refs/heads/source',self.old)
        with self.assertRaisesRegex(Refusal,'legacy hold'):asyncio.run(ordinary.perform(self.s,self.boards['Branch'],self.s.job(job['id'])))
        self.assertEqual(self.git('rev-parse','refs/heads/target'),self.old)
        self.assertIsNone(self.s.one('SELECT state FROM ordinary_runs'))
        prospective.revoke(self.s,'fictional-Work',self.epoch)
        with self.assertRaises(Refusal):ordinary.selected(self.s,self.s.job(job['id']))
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_resources'),[])

    def test_interrupted_actual_CAS_retains_original_intent_without_replay(self):
        self.authorize();self.admit_ref('synthetic-ref')
        job,attempt=self.queue('branch-integrator','synthetic-ref');self.collect(attempt)
        adapter=ordinary.adapter
        async def interrupted(*args,**kwargs):
            await adapter(*args,**kwargs)
            raise Refusal('synthetic interruption after actual owned CAS/readback')
        with patch.object(ordinary,'adapter',side_effect=interrupted):
            with self.assertRaisesRegex(Refusal,'after actual'):asyncio.run(ordinary.perform(self.s,self.boards['Branch'],self.s.job(job['id'])))
        self.assertEqual(self.git('rev-parse','refs/heads/target'),self.head)
        self.assertEqual(self.s.one('SELECT state FROM ordinary_runs')['state'],'intent')
        self.assertTrue(self.s.rows('SELECT * FROM ordinary_resources'))
        with self.assertRaisesRegex(Refusal,'never replay'):asyncio.run(ordinary.perform(self.s,self.boards['Branch'],self.s.job(job['id'])))
        self.assertEqual(self.s.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.s.rows('SELECT * FROM ordinary_acceptance'),[])

    def test_Work_owned_report_whole_input_sole_integration_and_Work_response(self):
        self.authorize()
        report={'reference':'synthetic-owned-original-END-reference','collector':'fictional-Work','actual_END':0,
                'reports':[{'name':'PRIMARY.md','body':'synthetic whole report with dissent and PARTIAL coverage'},
                           {'name':'LIMITS.md','body':'synthetic external contracts remain unknown'}],
                'history':'synthetic full old and current review history; unchanged failed returns', 'method_pin':'synthetic exact selected method pin',
                'coverage':{'all9':'PARTIAL','unread':['synthetic unknown external contract']},'effects':'known-report-only'}
        with self.assertRaises(Refusal):service.ingest_report(self.s,'fictional-foreign','ri',report)
        borrowed={**report,'collector':'fictional-Reviews'}
        with self.assertRaises(Refusal):service.ingest_report(self.s,'fictional-Work','ri',borrowed)
        result=service.ingest_report(self.s,'fictional-Work','ri',report)
        self.assertEqual(result,service.ingest_report(self.s,'fictional-Work','ri',report))
        event=self.s.event(result['event']);job,attempt=self.queue('ri',existing=event)
        self.assertIn(report['reports'][0]['body'],job_prompt(self.s,job))
        answer={'semantic':'DONE','summary':'synthetic integration of whole attributed report; review remains partial',
                'findings':[event['body']], 'failures':[],'unknowns':[],'artifacts':[],'category':'consolidated',
                'handoffs':[],'no_handoff_reason':'sole internal Work response preserves whole input'}
        self.collect(attempt,answer)
        response=self.s.finish_job(job['id'],job['token']);self.assertIsNotNone(response)
        work=self.s.event(response)
        self.assertEqual(work['role'],'Work');self.assertEqual(work['allowed_tasks'],['wp'])
        self.assertEqual(work['body']['findings'][0]['original'],report)
        self.assertFalse(work['body']['findings'][0]['native_owner_execution'])
        self.assertEqual(self.s.rows('SELECT * FROM review_calls'),[])
        changed=copy.deepcopy(report);changed['reports'][0]['body']='synthetic forbidden replacement'
        with self.assertRaises(Refusal):service.ingest_report(self.s,'fictional-Work','ri',changed)
        self.assertEqual(self.s.event(result['event'])['body']['original'],report)
        prospective.revoke(self.s,'fictional-Work',self.epoch)
        processing.revoke(self.s,self.boards,self.cap)
        policy=self.f.processing_selection();policy.pop('expires');policy.pop('max_starts')
        policy['service']={'max_inflight':5,'reviews':{},'legacy_resources':{},'report_tasks':['ri']}
        self.cap=processing.select(self.s,self.boards,policy)['capability']
        self.s.processing=processing.Access(self.s,self.cap,self.boards)
        with self.assertRaises(Refusal):service.ingest_report(self.s,'fictional-Work','ri',report)
        self.assertEqual(self.s.event(result['event'])['body']['original'],report)

    def test_actual_scoped_coordinator_membership_route_and_stale_cross_scope_refusal(self):
        self.authorize()
        self.s.admit('synthetic-branch','fictional-Branch',{'task_scopes':{'branch-integrator':self.scope('local-ref')}})
        coordinator='22222222-2222-4222-8222-222222222222'  # synthetic logical Board actor, not a native encounter
        self.f.conn.execute("INSERT INTO sessions(session,campaign,role,profile,status,registered_at,last_seen_at) VALUES(?,'synthetic','work-coordinator',NULL,'active','synthetic-time','synthetic-time')",(coordinator,))
        receipt={'id':'synthetic-branch-association','repository':str(self.repo),'origin':'https://example.invalid/synthetic',
                 'ref':'refs/heads/target','incarnation':'synthetic-incarnation','scope':'synthetic-branch',
                 'root':coordinator,'authority':'synthetic scoped Work coordination; global Root unchanged'}
        branches.register(self.s,'fictional-Work',receipt)
        with self.assertRaises(Refusal):branches.accept(self.s,receipt['id'],'synthetic-existing-root','wrong acceptor')
        branches.accept(self.s,receipt['id'],coordinator,'synthetic actual scoped acceptance and delegation')
        with self.s.tx():
            key=self.s._outbox('Branch','Root','work',{'package':'synthetic-branch','ref':'refs/heads/target','text':'synthetic actual branch duty'})
        outbox=self.s.one('SELECT * FROM outboxes WHERE id=?',(key,))
        grant,target=self.boards['Branch']._delivery_grant(self.f.conn,self.s,outbox)
        self.assertEqual(target['session'],coordinator);self.assertEqual(target['board_role'],'work-coordinator')
        self.assertEqual(self.s.config['delivery']['recipients']['Root']['session'],'synthetic-existing-root')
        routed=self.boards['Branch'].post_delivery(self.s,outbox)
        saved=self.f.conn.execute('SELECT recipient FROM coordinator_deliveries_v1 WHERE id=?',(key,)).fetchone()
        self.assertEqual(saved['recipient'],coordinator)
        payload=json.loads(outbox['payload']);payload['package']='synthetic-other'
        with self.assertRaises(Refusal):self.boards['Branch']._delivery_grant(self.f.conn,self.s,{**outbox,'payload':encode(payload)})
        self.f.conn.execute("UPDATE sessions SET role='synthetic-stale-role' WHERE session=?",(coordinator,))
        with self.assertRaises(Refusal):self.boards['Branch']._delivery_grant(self.f.conn,self.s,outbox)
        self.f.conn.execute("UPDATE sessions SET role='work-coordinator' WHERE session=?",(coordinator,))
        self.s.db.execute("UPDATE branch_associations SET incarnation='synthetic-next-incarnation' WHERE id=?",(receipt['id'],))
        with self.assertRaises(Refusal):self.boards['Branch']._delivery_grant(self.f.conn,self.s,outbox)

    def test_pressure_amendment_preserves_old_debt_and_bounds_new_intake(self):
        # Exactly the supplied pressure shape, in explicitly synthetic rows.
        for n in range(64):
            self.s.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)',
                              ('synthetic-alert-'+str(n),'synthetic-subject','synthetic',900,encode({'old':n})))
        for n in range(130):
            self.s.db.execute('INSERT INTO alert_debt VALUES(?,?,?,?,?,0)',
                              ('synthetic-debt-'+str(n),'synthetic-subject','synthetic',900,encode({'old':n})))
        previous=self.s.rows('SELECT * FROM alert_debt ORDER BY id')
        selection=json.loads(self.s.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.cap,))['selection'])
        with self.assertRaises(Backpressure):service.admit_input(self.s)
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM jobs')['n'],1)
        processing.revoke(self.s,self.boards,self.cap)
        options={'capacity':{'authority':'synthetic Work explicit bounded prospective entitlement',
                            'evidence':'synthetic actual owned resource account; old charges still included',
                            'limits':{'max_alerts':256,'max_alert_debt':512}}}
        self.f.value=configuration.candidate(self.s,str(self.f.directory/'current.json'),['bi','qe'],scope_options=options)
        Path(self.f.value['operator_config']).write_text(encode(self.f.value))
        self.f.transition();self.s=self.f.runtime;self.boards=self.f.boards
        policy=self.f.processing_selection();policy.pop('expires');policy.pop('max_starts')
        policy['service']=selection['service']
        self.cap=processing.select(self.s,self.boards,policy)['capability']
        self.s.processing=processing.Access(self.s,self.cap,self.boards)
        self.assertEqual(self.s.rows('SELECT * FROM alert_debt ORDER BY id'),previous)
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM alerts')['n'],64)
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM outboxes')['n'],67)
        self.assertEqual(self.s.one("SELECT value FROM meta WHERE key='configuration'")['value'],digest(self.f.original))
        self.assertEqual(self.original_grants,[tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')])
        service.admit_input(self.s)
        for n in range(2):
            event={**self.f.originals[0],'id':'synthetic-window-'+str(n),'post':100+n,'allowed_tasks':['wp']}
            self.s.ingest(event)
        with self.assertRaises(Backpressure):service.admit_input(self.s)
        self.assertEqual(self.s.rows('SELECT * FROM alert_debt ORDER BY id'),previous)
        # Allocation history survives physical event retirement; no count refund.
        self.s.db.execute("DELETE FROM events WHERE id='synthetic-window-0'")
        with self.assertRaises(Backpressure):service.admit_input(self.s)
        # Original alerts have no linked full processing/holds clearance.
        with self.assertRaises(Refusal):capacity.retirement_basis(self.s,'synthetic-alert-0')

    def test_selected_cwd_capacity_limits_and_command_contracts(self):
        options={'cwd':{'ri':str(self.f.directory/'new-report-work'/'narrow')},
                 'capacity':{'authority':'synthetic explicit Work entitlement','evidence':'synthetic owned account',
                             'limits':{'max_alerts':256,'max_alert_debt':512}}}
        value=configuration.candidate(self.s,str(self.f.directory/'new-config.json'),[],scope_options=options)
        configuration.validate_changes(self.s,value,['ri'])
        self.assertEqual(value['tasks']['ri']['cwd'],options['cwd']['ri'])
        self.assertEqual(self.s.config['limits']['max_alert_debt'],128)
        with self.assertRaises(Refusal):configuration.validate_changes(self.s,value,['wp'])
        bad=copy.deepcopy(options);bad['capacity']['limits']['max_alerts']=65537
        with self.assertRaises(Refusal):configuration.candidate(self.s,'/fixtures/unused',[],scope_options=bad)
        bad=copy.deepcopy(options);bad['cwd']['ri']='/usr'
        with self.assertRaises(Refusal):configuration.candidate(self.s,'/fixtures/unused',[],scope_options=bad)
        for argv in [('authorize-prospective','--capability',self.cap,'--selection','synthetic.json'),
                     ('ordinary-acceptance','synthetic-attempt','--capability',self.cap,'--decision','accepted','--receipt','synthetic.json'),
                     ('processing-report',self.cap,'--task','ri','--receipt','synthetic.json')]:
            args=cli.parser().parse_args(argv);self.assertEqual(args.capability,self.cap)
        with self.assertRaises(OSError):Path('/src/tools/coordinator-runtime/coordinator_runtime/processing.py').open('ab')
        self.assertFalse(Path('/src/.git').exists())


class CandidateGate(Composition):
    def test_all_candidate_paths_checked_before_any_blob_copy_hash_or_root(self):
        p={'repository':str(self.repo),'source_head':self.head,'source_capture':{'max_bytes':65536,'max_files':20}}
        # Conditional supplied reproduction signal, no actual repository lookup.
        listing='100644 blob '+('a'*40)+' 1\tsafe.txt\0'+'100644 blob '+('b'*40)+' 2\tnested/WORK_LOG.md\0'
        async def listed(*args):return listing
        with patch.object(ordinary,'git',side_effect=listed), patch.object(ordinary,'tool') as blob:
            with self.assertRaisesRegex(Refusal,'whole-log'):asyncio.run(qa_source.export(self.s,'synthetic-unstarted-QA',p,{'head':self.head,'tree':'synthetic'}))
            blob.assert_not_called()
        self.assertFalse((self.s.home/'artifacts'/'synthetic-unstarted-QA').exists())
        # Known exact excluded origins are checked lexically before acquisition.
        self.s.config['artifact_exclusions']=[str(self.repo/'safe.txt')]
        with self.assertRaisesRegex(Refusal,'excluded'):qa_source.guard_candidate(self.s,str(self.repo),'safe.txt')


if __name__=='__main__':unittest.main()
