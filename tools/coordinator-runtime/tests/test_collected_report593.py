"""Decision593 regressions: isolated real SDK/journal, deterministic collectors.

All principals, process ENDs, tools, source pins and review attestations are
fixture facts. No providers, installed sessions or native acceptance are used.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, collect, result, queued
from test_software_consumption import fixture_actor
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.store import Store
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime import local_integration as local, software, prospective, processing, configuration, report_repair


class Reports(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='report593-', dir=os.environ['TMPDIR']))
        self.config = config_at(self.area)
        self.config['tasks']['work-proposer']['publish_internal_results'] = True
        self.config['tasks']['reviews-integrator']['publish_internal_results'] = True
        self.catalog = self.area/'catalog.json'
        self.catalog.write_text(encode({'a':{'id':'a','state':'original','owner':'preserved'}}))
        point = {'kind':'item','line':'fixture','incarnation':'one',
                 'bindings':[{'target':str(self.catalog),'path':['a']}],
                 'resources':[], 'protected':['id','owner'], 'writable':['state']}
        self.config['local_integration'] = {'max_inflight':8,'points':{'a':point},'tasks':{
            t:{'capacity':5,'discovery_batch':4,'points':['a'],
               'authority':'Fictional current same report/consolidation responsibility',
               'method':v['templates'][0]} for t,v in self.config['tasks'].items()}}
        board_id = self.config['roles']['Work']['board_id']
        for role in self.config['roles'].values(): role['board_id'] = board_id
        self.actor = self.config['roles']['Work']['owner']
        self.config['software_delegation'] = {'grantor':self.actor,'authority':'Fictional independent Decision593',
                                               'boundary':'new-journal-only'}
        self.config['delivery'] = {'recipients':{r:{'session':v['owner'],'profile':v['profile'],'board_role':v['board_role']}
                                                 for r,v in self.config['roles'].items()}}
        self.substrate = module_at(self.config['board_library'], 'board_store')
        catalog = module_at(self.config['board_library'], 'catalog')
        home = Path(self.config['board_home'])
        with catalog.catalog(home) as conn:
            entry = catalog.create(conn, home, 'report-fixture', 'Owned report fixture',board_id=board_id,temporary_test=True)
        self.board_path = entry['db_path']
        with self.substrate.database(self.board_path) as conn:
            self.substrate.bind_board(conn,board_id,initialize=True)
            for role in self.config['roles'].values():
                args = self.substrate.parser().parse_args(['register','--session',role['owner'],'--role',role['board_role'],
                                                           '--route','managed','--profile',role['profile']])
                with fixture_actor(self.substrate,role['owner']):self.substrate.register(conn,args)
        self.store = Store(self.config,clock=lambda:1000.)
        self.addCleanup(self.store.close)
        self.boards = {r:Board(self.config,r) for r in self.config['roles']}
        for role, board in self.boards.items():
            with fixture_actor(board.store,self.actor):grant = board.grant_software(self.store,self.config['software_delegation']['authority'])
            self.store.enroll(role,grant)
            self.store.reconcile_legacy(role,self.config['roles'][role]['owner'],
                {'collector':'fixture','evidence':['No legacy fixture input'],'remaining_holds':[]})

    def source(self, role='Work', task='work-proposer', package=None):
        args = ['post','--session',self.actor,'--topic','fixture','--kind','finding','--text','Original report duty',
                '--to',self.config['roles'][role]['owner']]
        if package:args += ['--ref',package]
        with self.substrate.database(self.board_path) as conn, fixture_actor(self.substrate,self.actor):
            self.substrate.post(conn,self.substrate.parser().parse_args(args))
        source = self.boards[role].scan(self.store)[0]
        self.store.ingest(source,cursor=source['post'])
        self.store.resolve_input(source['id'],self.config['roles'][role]['owner'],{
            'source_hash':digest(source),'mode':'route','task':task,'package':package,'related_event':None,'related_job':None,
            'reason':'Independent fixture decision: report existing a only','evidence':['exact assigned a'],
            'remaining_obligations':['acceptance remains separate'], 'integration':{'state':'known','reads':['a'],'writes':[]}})
        queued(self.store,source,{'event_id':source['id'],'task':task,'package':package,'reason':'fixture selected duty'})
        return source

    def producer(self, role='Work', task='work-proposer', package=None, adverse=True, nonzero=True):
        source = self.source(role,task,package)
        job = self.store.reserve(); self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'],job['token'])
        job = self.store.job(job['id'])
        self.boards[role].bind_software_attempt(self.store,job,attempt,
            self.store.one('SELECT * FROM admissions WHERE package=?',(package,)))
        local.prepare_input_basis(self.store,job,attempt,self.config['tasks'][task])
        answer = result(category='consolidated' if role=='QA' or task=='reviews-integrator' else 'proposal')
        answer['completion'] = {'integration_steps':[{'step':s,'evidence':'Fixture scoped '+s} for s in local.STEPS]}
        if adverse:
            answer['failures'] = [{'kind':'preserved Source38/QA574/573 history','local_defect':False,
                                   'verdict':'FAILED','history':['initial wrong-actor assertion','TextEncoder ReferenceError then corrected']}]
            answer['unknowns'] = [{'effects':'unknown under original custodian','acceptance':None,'dissent':'preserve whole report'}]
        tools = {'complete':True,'items':[{'id':'failed-then-reported','status':'completed','exit_code':1}],
                 'nonzero_completions':['failed-then-reported']} if nonzero else {'complete':True,'items':[]}
        collect(self.store,attempt,answer,tool_completion=tools)
        response = self.store.finish_job(job['id'],job['token'])
        self.assertIsNotNone(response)
        returned = self.store.event(response)
        queued(self.store,returned)
        return source,self.store.job(job['id']),returned,answer

    def test_authentic_whole_adverse_report_reaches_assigned_integrator_without_cleanliness_or_acceptance(self):
        source,job,report,answer = self.producer()
        self.assertIsNone(software.clean_processing(self.store,job))
        self.assertTrue(software.collected_report(self.store,job,'work-integrator'))
        receiver = self.store.reserve(); self.assertIsNotNone(receiver)
        self.assertEqual(receiver['task'],'work-integrator')
        self.assertEqual(json.loads(receiver['members'])[0]['event'],report['id'])
        self.assertEqual(self.store.event(report['id'])['body'],answer)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(self.catalog.read_text(),encode({'a':{'id':'a','state':'original','owner':'preserved'}}))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_done_and_local_defect_false_do_not_replace_collection_or_capture(self):
        _,job,report,_ = self.producer()
        before = self.store.attempt(job['active_attempt'])
        for field,value in [('begin',None),('ended',None),('collected',None),('capture','incomplete'),('exit',1),('error','capture failure')]:
            with self.subTest(field=field):
                self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(value,before['id']))
                with self.assertRaises(Refusal):local.input_authority(self.store,report,'work-integrator',None)
                self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(before[field],before['id']))
        detail = json.loads(before['detail']); detail['tool_completion']['complete'] = False
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),before['id']))
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_real_unknown_effects_hold_source_and_cannot_become_qualification_or_execution(self):
        _,job,report,_ = self.producer()
        self.assertIsNone(software.collected_report(self.store,job,'qa-execution'))
        self.assertIsNone(software.collected_report(self.store,job,'branch-integrator'))
        self.store.db.execute("UPDATE jobs SET effects='unknown' WHERE id=?",(job['id'],))
        self.assertIsNone(self.store.reserve())
        self.store.db.execute("UPDATE jobs SET effects='none',hold_reason='actual held duty' WHERE id=?",(job['id'],))
        self.assertIsNone(self.store.reserve())
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(report['id'],))['processed_at'])

    def test_original_members_recipient_package_and_launch_rights_are_rechecked(self):
        source,job,report,_ = self.producer()
        self.store.set_hold(source['id'],'private/held fixture source')
        self.assertIsNone(self.store.reserve())
        self.store.set_hold(source['id'],None)
        changed = copy.deepcopy(report); changed['recipient'] = ident()
        with self.assertRaises(Refusal):local.input_authority(self.store,changed,'work-integrator',None)
        with self.assertRaises(Refusal):local.input_authority(self.store,report,'work-integrator','foreign-package')
        detail = json.loads(self.store.attempt(job['active_attempt'])['detail'])
        detail['software_authority']['task_hash'] = 'foreign method rights'
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),job['active_attempt']))
        with self.assertRaises(Refusal):local.input_authority(self.store,report,'work-integrator',None)
        self.assertIsNone(self.store.reserve())

    def test_current_prospective_authority_is_required_and_retains_exact_original_report(self):
        policies = {n:{'task_hash':digest(t),'software_handoffs':{},'ordinary_effects':False} for n,t in self.config['tasks'].items()}
        epoch = prospective.select(self.store,self.actor,{'configuration':digest(self.config),'authority':'Fictional prospective report duty',
            'expires':2000.,'grants':{r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},'tasks':policies})
        _,job,report,answer = self.producer()
        local.input_authority(self.store,report,'work-integrator',None)
        prospective.revoke(self.store,self.actor,epoch['id'])
        with self.assertRaises(Refusal):local.input_authority(self.store,report,'work-integrator',None)
        self.assertEqual(self.store.event(report['id'])['body'],answer)
        self.assertIsNone(software.clean_processing(self.store,job))

    def test_Reviews_and_QA_reports_keep_role_and_package_differences(self):
        # Each consumes a distinct real fixture package. Branch qualification is
        # deliberately NOT one of the relaxed report edges.
        for role,task,receiver in [('Reviews','reviews-proposer','reviews-integrator'),('QA','qa-execution','qa-cleanup')]:
            with self.subTest(role=role):
                package = 'fixture-'+role if role=='QA' else None
                if package:self.store.admit(package,self.config['roles']['Branch']['owner'],{'task_scopes':{}})
                _,job,report,answer = self.producer(role,task,package)
                consumer = self.store.reserve(); self.assertIsNotNone(consumer)
                self.assertEqual(consumer['task'],receiver);self.assertEqual(consumer['package'],package)
                self.assertEqual(report['body'],answer)
                self.assertIsNone(software.clean_processing(self.store,job))

    def test_adverse_published_response_uses_one_original_consumer_and_does_not_auto_settle(self):
        from coordinator_runtime.dispatcher import Dispatcher
        _,job,report,answer = self.producer()
        dispatcher = Dispatcher(self.store,models=object(),boards=self.boards)
        original_ids = self.store.rows('SELECT id FROM events ORDER BY id')
        dispatcher.pump_deliveries()
        dispatcher.pump_deliveries()  # Retry exact persisted intent, no duplicate.
        self.assertEqual(self.store.rows('SELECT id FROM events ORDER BY id'),original_ids)
        link = self.store.one('SELECT * FROM processing_delivery_links WHERE event=?',(report['id'],))
        # Non-processing mode still has one SDK receiving intent.
        outbox = self.store.one("SELECT * FROM outboxes WHERE job=? AND kind='result'",(job['id'],))
        self.assertIsNotNone(outbox)
        self.assertEqual(json.loads(outbox['payload']),report)
        with self.boards['Work'].opened() as conn:
            intent = conn.execute('SELECT event FROM coordinator_software_deliveries_v1 WHERE delivery=?',(outbox['id'],)).fetchone()
        self.assertIsNotNone(intent);self.assertEqual(intent['event'],report['id'])
        consumer = self.store.reserve();self.assertIsNotNone(consumer)
        self.assertEqual(json.loads(consumer['members'])[0]['event'],report['id'])
        self.assertEqual(self.store.event(report['id'])['body'],answer)
        self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(outbox['id'],))['processed_at'])

    def test_report_route_does_not_create_missing_cross_role_software_handoff_rights(self):
        from coordinator_runtime.dispatcher import Dispatcher
        _,job,report,_ = self.producer('Reviews','reviews-integrator',nonzero=False)
        outbox = self.store.one("SELECT * FROM outboxes WHERE job=? AND kind='result'",(job['id'],))
        dispatcher = Dispatcher(self.store,models=object(),boards=self.boards)
        dispatcher.pump_deliveries()
        with self.boards['Reviews'].opened() as conn:
            intent = conn.execute('SELECT event FROM coordinator_software_deliveries_v1 WHERE delivery=?',(outbox['id'],)).fetchone()
        self.assertIsNone(intent)
        self.assertEqual(self.store.event(report['id'])['source_job'],job['id'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM outboxes WHERE id=?',(outbox['id'],))['processed_at'])

    def test_publishing_routine_and_Branch_effect_paths_keep_original_guards(self):
        _,job,_,_ = self.producer()
        self.config['tasks']['work-proposer']['routine_completion'] = {'fixture':'must assess, never report exemption'}
        self.assertIsNone(software.collected_report(self.store,job,'work-integrator'))
        branch = {**job,'role':'Branch','phase':'proposer','task':'branch-proposer'}
        self.assertIsNone(software.collected_report(self.store,branch,'branch-integrator'))

    def processing_mode(self):
        for role,board in self.boards.items():
            with fixture_actor(board.store,self.actor):board.revoke_software(self.store,self.store.enrollment(role)['grant_id'])
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(role,))
        self.boards = {r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        selection = {'basis':processing.basis(self.store,self.boards),'authority':'Fictional continuing bounded report authority',
                     'retained_events':[],'recover_controls':{},'future_intake':True,'tasks':list(self.config['tasks']),
                     'max_shared_rows':1000,'max_shared_payload_bytes':1048576,'max_runtime_rows':1000,
                     'service':{'max_inflight':8,'reviews':{},'legacy_resources':{}}}
        with fixture_actor(self.boards['Work'].store,self.actor):
            self.key = processing.select(self.store,self.boards,selection)['capability']
        self.store.processing = processing.Access(self.store,self.key,self.boards)
        prospective.select(self.store,self.actor,{'configuration':digest(self.config),'authority':'Fictional original finite prospective grant',
            'expires':2000.,'grants':{r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            'tasks':{n:{'task_hash':digest(t),'software_handoffs':{},'ordinary_effects':False} for n,t in self.config['tasks'].items()},
            'processing_capability':self.key})

    def repair_fixture(self):
        self.processing_mode()
        source,job,report,answer = self.producer(nonzero=False)
        self.controller = self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.controller,self.key,'owned',1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.controller,self.key,'fictional-unused-endpoint','returned-awaiting-parent-END',1000.,1001.,'fixture stopped'))
        with fixture_actor(self.boards['Work'].store,self.actor):
            processing.release(self.store,self.boards,self.key,self.controller,{'actual_END':0,'evidence':['fictional SAME foreground collected END0']})
        # Controlled public source pin seam: exact SAME release path and config,
        # all other files frozen; this is not independent actual code review.
        root = '/fictional-release'
        file = root+'/tools/coordinator-runtime/coordinator_runtime/software.py'
        self.old_release = {'root':root,'files':{file:'old','/fictional-fixed-template':'unchanged'},'pool_control':'unchanged'}
        self.new_release = {**self.old_release,'files':{**self.old_release['files'],file:'reviewed repair'}}
        selection = json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.key,))['selection'])
        bindings = {r:{'original':{'binding':v['original']['binding']}} for r,v in selection['basis']['roles'].items()}
        transition = {'basis':{'release':self.old_release,'processing':{'roles':bindings},
                               'tasks':list(self.config['tasks'])},'event_boundary':0,
                      'jobs':[],'outboxes':[],'alert_boundary':0}
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
            ('fixture previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.actor,1000.))
        self.new_implementation = {**selection['basis']['implementation'],'software.py':'reviewed repair'}
        return source,job,report,answer

    def pins(self):
        stack = self.enterContext(patch.object(configuration,'release',return_value=self.new_release))
        self.enterContext(patch.object(processing,'implementation',return_value=self.new_implementation))
        return stack

    def request(self, report):
        with fixture_actor(self.boards['Work'].store,self.actor):
            basis = report_repair.basis(self.store,self.boards,self.key,report['id'],self.controller,self.actor)
        return {'basis':basis,'authority':'Fictional actual Work selects only reviewed report correction',
                'evidence':['Fictional continuing Source and independent QA, not producer test acceptance']}

    def apply_repair(self, request, actor=None):
        with fixture_actor(self.boards['Work'].store,actor or self.actor):
            return report_repair.apply(self.store,self.boards,actor or self.actor,request)

    def test_exact_already_queued_continuation_without_source_replay_or_new_epoch_or_charge_reset(self):
        source,job,report,answer = self.repair_fixture(); self.pins()
        before = {t:self.store.rows('SELECT * FROM '+t) for t in ('events','attempts','prospective_authorities','processing_capabilities','enrollments')}
        with self.assertRaises(Refusal):self.store.processing.current()
        request = self.request(report); receipt = self.apply_repair(request)
        self.assertEqual(receipt['event'],report['id'])
        for t,rows in before.items():self.assertEqual(self.store.rows('SELECT * FROM '+t),rows,t)
        self.store.controller = ident()  # New actual fixture collector, never impersonates old original.
        consumer = self.store.reserve();self.assertIsNotNone(consumer)
        self.assertEqual(consumer['task'],'work-integrator')
        self.assertEqual(json.loads(consumer['members'])[0]['event'],report['id'])
        second = self.apply_repair(request)
        self.assertEqual(second,receipt)
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.event(report['id'])['body'],answer)
        self.assertEqual(self.store.job(job['id']),job)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM collected_report_repairs')['n'],1)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_repair_requires_exact_current_actor_stop_END_release_scope_and_once_only_request(self):
        _,_,report,_ = self.repair_fixture();self.pins()
        request = self.request(report)
        with self.assertRaises(Refusal):self.apply_repair(request,ident())
        self.store.db.execute("UPDATE processing_runs SET state='owned' WHERE controller=?",(self.controller,))
        with self.assertRaises(Refusal):self.apply_repair(request)
        with fixture_actor(self.boards['Work'].store,self.actor):
            processing.release(self.store,self.boards,self.key,self.controller,{'actual_END':0,'evidence':['fictional SAME END']})
        request = self.request(report)
        changed = copy.deepcopy(self.new_release);changed['files']['/fictional-fixed-template']='unauthorized'
        with patch.object(configuration,'release',return_value=changed),self.assertRaises(Refusal):self.apply_repair(request)
        self.apply_repair(request)
        different = copy.deepcopy(request);different['authority'] += ' new decision'
        with self.assertRaises(Refusal):self.apply_repair(different)
        self.new_implementation['software.py']='changed after review'
        with self.assertRaises(Refusal):self.store.processing.current()

    def test_repair_held_or_changed_source_and_backpressure_are_not_bypassed(self):
        source,_,report,_ = self.repair_fixture();self.pins();request = self.request(report)
        self.store.set_hold(source['id'],'original privacy hold')
        with self.assertRaises(Refusal):self.apply_repair(request)
        self.assertEqual(self.store.rows('SELECT * FROM collected_report_repairs'),[])
        self.store.set_hold(source['id'],None)
        self.apply_repair(request)
        # Eight unrelated owned fixture responsibilities consume actual local
        # residency. The repair never clears them or raises max_inflight.
        for i in range(8):
            self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects) "
                "VALUES(?,'Work','proposer','work-proposer','[]','original other custodian',?,1000,'held','unknown')",
                ('unrelated-debt-'+str(i),ident()))
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM jobs WHERE effects='unknown'")['n'],8)
        self.assertEqual(self.apply_repair(request)['event'],report['id'])

    def test_supported_CLI_dispatch_selects_exact_repair_and_rejects_stale_reviewed_pins(self):
        from coordinator_runtime import cli
        _,_,report,_ = self.repair_fixture();self.pins()
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.actor}):
            args = cli.parser().parse_args(['collected-report-repair-basis',self.key,report['id'],'--controller',self.controller])
            basis = cli.operate(args,self.store)
            path = self.area/'reviewed-repair.json'
            path.write_text(encode({'basis':basis,'authority':'Fictional genuine current Work decision',
                                   'evidence':['Fictional independent qualifications, no native acceptance']}))
            args = cli.parser().parse_args(['select-collected-report-repair','--selection',str(path)])
            self.assertEqual(cli.operate(args,self.store)['event'],report['id'])
            self.new_release['files']['/fictional-fixed-template']='changed after selection'
            with self.assertRaises(Refusal):self.store.processing.current()

    def test_reservation_diagnostics_attribute_only_exact_source_and_never_global_error_bodies(self):
        _,_,report,_ = self.producer()
        self.store.db.execute("UPDATE attempts SET capture='incomplete' WHERE id=?",(report['source_attempt'],))
        self.assertIsNone(self.store.reserve())
        state = self.store.one('SELECT hash,role FROM events WHERE id=?',(report['id'],))
        queue = self.store.one('SELECT task,state,job FROM queue WHERE event=?',(report['id'],))
        # No processing capability is claimed by normal-mode fixture.
        observation = processing.reservation_observation(self.store,None,report['id'],state,queue,self.store.controller)
        self.assertTrue(observation['available']);self.assertTrue(observation['still_queued'])
        # Work50103 supersedes the old diagnostic-string contract. The
        # parent failure is retained separately; this asserts the reached
        # typed branch and that legacy strings cannot refresh its attribution.
        self.assertEqual(observation['outcome'], 'refusal')
        self.assertEqual(observation['predicate'], 'members')
        self.assertTrue(observation['current'])
        self.assertTrue(observation['same_controller'])
        with self.assertRaises(Refusal):local.input_authority(self.store,report,'work-integrator',None)
        self.store.db.execute('UPDATE operational_errors SET detail=? WHERE subject=?',
            (encode({'dependency':'RAW_UNRELATED_PRIVATE_CANARY'}),report['id']))
        self.assertEqual(processing.reservation_observation(self.store,None,report['id'],state,queue,self.store.controller), observation)
        self.store.db.execute('UPDATE reservation_outcomes SET controller=? WHERE event=?', (ident(), report['id']))
        stale = processing.reservation_observation(self.store,None,report['id'],state,queue,self.store.controller)
        self.assertFalse(stale['available']); self.assertEqual(stale['outcome'], 'stale')
        self.assertIsNone(stale['reason'])
        self.assertNotIn('CANARY', encode(stale))



if __name__ == '__main__':unittest.main()
