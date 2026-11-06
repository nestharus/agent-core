"""R27 first ingress through production Board/receiving APIs in owned bwrap fixtures.

Principals, model/tool collection and independent semantic acceptance are fiction.
No native caller, customer or real receiving/adoption proof is asserted.
"""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from support import collect, result, queued, event
import test_ordinary_effects as original
import test_local444 as native_tests
from coordinator_runtime import local_integration as local, prospective, ordinary, publication, routine
from coordinator_runtime.board import module_at
from coordinator_runtime.contracts import Refusal, digest, encode, scoped_task, validate_config
from coordinator_runtime.dispatcher import Dispatcher


class Ingress(unittest.IsolatedAsyncioTestCase):
    git = original.OrdinaryEffects.git
    admission = original.OrdinaryEffects.admission

    async def asyncSetUp(self):
        await original.OrdinaryEffects.asyncSetUp(self)
        self.catalog = self.area/'catalog.json'
        self.catalog.write_text(encode({'a':{'id':'a','owner':'original','state':'old'},
                                      'b':{'id':'b','owner':'other','state':'old'}}))
        self.config['canonical_publication']['library'] = '/sdk'
        points = {k:{'kind':'item','line':'Main','incarnation':'one',
            'bindings':[{'target':str(self.catalog),'path':[k]}], 'resources':[],
            'protected':['id','owner'],'writable':['state']} for k in ('a','b')}
        names = ['work-proposer','work-integrator','qa-execution','branch-proposer','branch-integrator','reviews-integrator']
        self.config['local_integration'] = {'max_inflight':8,'points':points,'tasks':{
            t:{'capacity':5,'discovery_batch':4,'points':['a','b'] if t.startswith('work-') else [],
               'authority':'fictional independent current receiver scope decision',
               'method':self.config['tasks'][t]['templates'][0]} for t in names}}
        self.config['software_delegation'] = {'grantor':self.config['roles']['Work']['owner'], 'authority':'fictional selected delegation', 'boundary':'new-journal-only'}
        self.config['tasks']['work-integrator']['software_handoffs'] = {'QA':['qa-execution'],'Branch':['branch-proposer']}
        self.config['tasks']['work-proposer']['software_handoffs'] = {}
        self.substrate = module_at(self.config['board_library'], 'board_store')
        self.dispatcher = Dispatcher(self.store, models=object(), boards=self.boards)
        validate_config(self.config)

    def post(self, role='Work', text='Original known work', package=None):
        args = ['post','--session',self.config['roles']['Work']['owner'], '--topic','fixture',
                '--kind','finding','--text',text,'--to',self.config['roles'][role]['owner']]
        if package: args += ['--ref',package]
        with self.substrate.database(self.board_path) as conn:
            with patch.object(self.substrate,'acting_session',side_effect=lambda expected:expected):
                self.substrate.post(conn,self.substrate.parser().parse_args(args))
        source = self.boards[role].scan(self.store)[0]
        self.store.ingest(source,cursor=source['post'])
        return source

    def classify(self, source, task):
        while claimed := self.store.claim_classification():
            attempt, message = claimed
            selected = task if message['id'] == source['id'] else message['allowed_tasks'][0]
            collect(self.store,attempt,{'event_id':message['id'],'task':selected,'package':message.get('package'),
                                      'reason':'fictional fresh LOW classification seam'})
            self.store.commit_classification(attempt)
            if message['id'] == source['id']:
                self.assertEqual(json.loads(self.store.attempt(attempt)['binding']),self.config['classifier']['binding'])
                return attempt
        self.fail('expected an original fresh classifier')

    def receipt(self, source, task, mapping=None):
        value = {'source_hash':digest(source),'mode':'route','task':task,'package':source.get('package'),
                 'related_event':None,'related_job':None,'reason':'independent fixture intent: this original concerns the selected receiver scope',
                 'evidence':['fictional independently accepted original identity and intended receiver outcome'],
                 'remaining_obligations':[]}
        if mapping is not None: value['integration'] = mapping
        return value

    def resolve(self, source, task='work-proposer', key='a', state='known'):
        mapping = {'state':state}
        if state == 'known': mapping.update(reads=[key],writes=[])
        return self.store.resolve_input(source['id'],self.config['roles'][source['role']]['owner'],self.receipt(source,task,mapping))

    def prepare(self, job):
        attempt = self.store.start_job(job['id'],job['token'])
        job = self.store.job(job['id'])
        admission = self.store.one('SELECT * FROM admissions WHERE package=?',(job['package'],))
        task = scoped_task(job['task'], self.config['tasks'][job['task']], admission)
        if prospective.for_job(self.store,job):
            self.boards[job['role']].bind_software_attempt(self.store,job,attempt,admission)
        local.prepare_input_basis(self.store,job,attempt,task)
        return job,attempt

    def finish(self, job, attempt, answer=None):
        answer = answer or result(category='proposal')
        answer.setdefault('handoffs',[])
        if not answer['handoffs']: answer['no_handoff_reason'] = 'fictional original collector retains all obligations'
        answer['completion'] = {'integration_steps':[{'step':s,'evidence':'fictional method account '+s} for s in local.STEPS]}
        collect(self.store,attempt,answer,tool_completion={'complete':True,'items':[],'nonzero_completions':[]})
        return self.store.finish_job(job['id'],job['token'])

    def qa_point(self):
        self.git('remote','add','origin','https://example.invalid/owned-QA')
        self.admission(kind='local-qa')
        row = self.store.one('SELECT * FROM admissions WHERE package=?',('package',))
        self.config['local_integration']['points']['execution'] = {
            'kind':'item','line':'Main','incarnation':digest(row['receipt']),
            'bindings':[{'native':'execution','package':'package','task':'qa-execution'}],
            'resources':[],'protected':[],'writable':[]}
        self.config['local_integration']['tasks']['qa-execution']['points'] = ['execution']
        validate_config(self.config)
        return row

    def boundary(self):
        tasks = ['work-proposer','work-integrator','qa-execution','branch-proposer','branch-integrator','reviews-integrator']
        return prospective.select(self.store,self.config['roles']['Work']['owner'],{
            'configuration':digest(self.config),'authority':'fictional independently selected exact receiving interfaces',
            'expires':self.now+100,'grants':{r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            'tasks':{t:{'task_hash':digest(self.config['tasks'][t]),
                        'software_handoffs':copy.deepcopy(self.config['tasks'][t].get('software_handoffs',{})),
                        'ordinary_effects':t=='qa-execution'} for t in tasks}})

    async def test_original_Board_text_is_unresolved_then_known_before_first_Work_reservation(self):
        self.boundary()
        source = self.post(text=encode({'integration':{'reads':['a'],'writes':[],'versions':{'a':'fabricated'}}}))
        original = copy.deepcopy(source)
        with self.assertRaises(Refusal): self.boards['Work'].receipt(self.store,source['id'])
        self.classify(source,'work-proposer')
        self.dispatcher.receipts()
        self.assertIsNotNone(self.store.one('SELECT * FROM queue WHERE event=?',(source['id'],)))
        self.assertIsNone(self.store.reserve())
        self.assertIn('not proof of new',self.store.one('SELECT detail FROM operational_errors')['detail'])
        resolution = self.resolve(source)
        observed = resolution['prior']['integration_observation']
        self.assertEqual(set(observed['packet']['versions']),{'a'})
        self.assertNotEqual(observed['packet']['versions']['a'],'fabricated')
        self.assertIsNone(self.store.reserve())  # reclassification is owed
        self.classify(source,'work-proposer')
        job,attempt = self.prepare(self.store.reserve())
        self.assertEqual(local.context(self.store,job)['basis']['scope']['mode'],'direct')
        self.assertEqual(self.store.event(source['id']),original)
        self.assertEqual(json.loads(job['members'])[0]['input_resolution'],resolution['version'])
        response = self.store.event(self.finish(job,attempt))
        self.assertEqual(response['integration']['versions'],observed['packet']['versions'])
        self.classify(response,'work-integrator')
        with self.assertRaisesRegex(Refusal,'cannot be retargeted'):
            self.resolve(response,'work-integrator',key='b')
        receiver = self.store.reserve()
        self.assertEqual(receiver['task'],'work-integrator')
        self.assertEqual(local.scope_for(self.store,receiver)['reads'],['a'])
        with self.assertRaisesRegex(Refusal,'reserved/executed'):
            self.resolve(source,key='b')

    async def test_explicit_new_unresolved_and_known_remain_distinct_and_parallel(self):
        unknown = self.post(); self.classify(unknown,'work-proposer')
        self.resolve(unknown,state='unresolved-existing'); self.classify(unknown,'work-proposer')
        new = self.post(text='Independently identified new candidate'); self.classify(new,'work-proposer')
        self.resolve(new,state='new'); self.classify(new,'work-proposer')
        known = self.post(text='Existing b'); self.classify(known,'work-proposer')
        self.resolve(known,key='b'); self.classify(known,'work-proposer')
        first,second = self.store.reserve(),self.store.reserve()
        self.assertEqual({local.scope_for(self.store,j)['lane'] for j in (first,second)},{'discovery','anchored'})
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?',(unknown['id'],))['state'],'queued')
        discovery = next(j for j in (first,second) if local.scope_for(self.store,j)['lane']=='discovery')
        self.assertEqual(local.scope_for(self.store,discovery)['sources'],[new['id']])
        self.assertEqual(set(local.point_definitions(self.store)),{'a','b'})

    async def test_service_revision_stays_at_observation_and_stale_arrival_reconciles(self):
        source = self.post(); self.classify(source,'work-proposer')
        selected = self.resolve(source)
        frozen = copy.deepcopy(selected['prior']['integration_observation'])
        data = json.loads(self.catalog.read_text()); data['a']['state']='later'; self.catalog.write_text(encode(data))
        self.classify(source,'work-proposer')
        job,attempt = self.prepare(self.store.reserve())
        basis = local.context(self.store,job)['basis']
        self.assertEqual(basis['scope']['mode'],'reconcile')
        self.assertNotEqual(basis['versions'],frozen['packet']['versions'])
        self.assertEqual(self.store.input_resolution(source['id'])['prior']['integration_observation'],frozen)

    async def test_held_or_out_of_scope_or_forged_revision_refuses_before_acquisition(self):
        source = self.post(); self.classify(source,'work-proposer')
        self.store.set_hold(source['id'],'fictional privacy/effect hold')
        with patch.object(local,'version',side_effect=AssertionError('material acquisition')), self.assertRaises(Refusal):
            self.resolve(source)
        self.store.set_hold(source['id'],None)
        with patch.object(local,'version',side_effect=AssertionError('material acquisition')), self.assertRaises(Refusal):
            self.resolve(source,key='not-permitted')
        receipt = self.receipt(source,'work-proposer',{'state':'known','reads':['a'],'writes':[], 'versions':{'a':'forged'}})
        with self.assertRaises(Refusal): self.store.resolve_input(source['id'],self.config['roles']['Work']['owner'],receipt)
        with self.assertRaises(Refusal):
            self.store.resolve_input(source['id'],self.config['roles']['QA']['owner'],self.receipt(source,'work-proposer',{'state':'new'}))
        self.assertEqual(self.store.rows('SELECT * FROM input_resolutions'),[])

    async def test_changed_admission_or_grant_never_restamps_mapping(self):
        source = self.post(); self.classify(source,'work-proposer'); self.resolve(source)
        original = copy.deepcopy(self.store.input_resolution(source['id']))
        self.store.db.execute("UPDATE enrollments SET grant_id='fictional-changed' WHERE role='Work'")
        with self.assertRaisesRegex(Refusal,'changed'):
            local.packet(self.store,{'event':source['id'],'task':'work-proposer','package':None})
        self.assertEqual(self.store.input_resolution(source['id']),original)

    async def test_first_QA_Board_input_uses_actual_receipt_before_reservation_and_original_adapter(self):
        admission = self.qa_point(); self.boundary()
        source = self.post('QA',package='package'); self.classify(source,'qa-execution')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        self.resolve(source,'qa-execution','execution'); self.classify(source,'qa-execution')
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        job,attempt = self.prepare(self.store.reserve())
        self.assertEqual(self.store.one('SELECT admission FROM qa_package_owners')['admission'],digest(admission['receipt']))
        self.finish(job,attempt,result(category='consolidated'))
        # Preparation DONE alone cannot settle ordinary effects; actual adapter
        # export/runner/readback executes inside this fixture's private namespace.
        self.assertTrue(await ordinary.perform(self.store,self.boards['QA'],job))
        self.assertTrue((self.area/'qa-output/actual-run.txt').is_file())
        self.assertFalse(ordinary.accepted_package(self.store,'package'))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])

    async def test_explicit_new_QA_never_reserves_unanchored_execution(self):
        self.qa_point(); self.boundary()
        source = self.post('QA',package='package'); self.classify(source,'qa-execution')
        self.resolve(source,'qa-execution',state='new'); self.classify(source,'qa-execution')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])

    async def handoff(self):
        self.qa_point(); self.boundary()
        # One genuine SDK Board source feeds Work; Work never borrows Branch
        # or Source rights. QA keeps its separately original Branch admission.
        source = self.post(package='package')
        # Work Board ref is intentionally not a package selector. Bind this
        # source through the already-supported owner package route first.
        owner = self.config['roles']['Work']['owner']
        routed = self.receipt(source,'work-integrator'); routed['package']='package'
        self.store.resolve_input(source['id'],owner,routed)
        self.classify(source,'work-integrator')
        # For mapping the conserved route carries this original owner selection.
        # It must not rewrite original bytes or use a fabricated source event.
        mapping = self.receipt(source,'work-integrator',{'state':'known','reads':['a'],'writes':[]})
        mapping['package']='package'
        self.store.resolve_input(source['id'],owner,mapping)
        self.classify(source,'work-integrator')
        job,attempt = self.prepare(self.store.reserve())
        answer = result(category='complete')
        answer['handoffs']=[{'recipient':'QA','kind':'work','ref':'package','required':'settled',
                            'text':'Actual addressed fixture QA duty; nested metadata is evidence only'}]
        self.finish(job,attempt,answer)
        while claimed := self.store.claim_classification():
            classifier,message = claimed
            collect(self.store,classifier,{'event_id':message['id'],'task':message['allowed_tasks'][0],
                'package':message.get('package'),'reason':'fictional fresh LOW outgoing route'})
            self.store.commit_classification(classifier)
        self.dispatcher.pump_deliveries()
        receiving = self.store.one("SELECT payload FROM events WHERE role='QA'")
        self.assertIsNotNone(receiving)
        return source,self.store.job(job['id']),json.loads(receiving['payload'])

    async def test_addressed_handoff_uses_receiver_map_not_nested_source_anchor(self):
        source,sender,received = await self.handoff()
        self.assertNotIn('integration',received)
        self.assertIn('source_result',received['body'])
        self.classify(received,'qa-execution')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])
        self.resolve(received,'qa-execution','execution'); self.classify(received,'qa-execution')
        receiver,attempt = self.prepare(self.store.reserve())
        basis = local.context(self.store,receiver)['basis']
        self.assertEqual(basis['scope']['reads'],['execution'])
        self.assertEqual(json.loads(sender['members'])[0]['hash'],digest(source))
        self.assertEqual(self.store.event(received['id']),received)
        self.assertEqual(self.store.job(sender['id'])['state'],'awaiting-delivery')
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])

    async def test_handoff_original_hold_blocks_mapping_before_native_read(self):
        source,_,received = await self.handoff()
        self.classify(received,'qa-execution')
        self.store.set_hold(source['id'],'fictional upstream source hold')
        with patch.object(local,'version',side_effect=AssertionError('native acquisition')), self.assertRaises(Refusal):
            self.resolve(received,'qa-execution','execution')
        self.assertEqual(self.store.rows('SELECT * FROM qa_package_owners'),[])

    async def test_accepted_branch_can_feed_Branch_and_Reviews_without_Source_identity(self):
        self.admission(); association = native_tests.NativeEffects.branch(self)
        point = {'kind':'item','line':'Main','incarnation':association['incarnation'],
                 'bindings':[{'native':'branch','id':association['id']}], 'resources':[], 'protected':[], 'writable':[]}
        self.config['local_integration']['points']['branch'] = point
        for task in ('branch-proposer','reviews-integrator'):
            self.config['local_integration']['tasks'][task]['points']=['branch']
        validate_config(self.config)
        self.boundary()
        source = self.post('Branch',package='package'); self.classify(source,'branch-proposer')
        self.resolve(source,'branch-proposer','branch'); self.classify(source,'branch-proposer')
        job,attempt = self.prepare(self.store.reserve())
        self.assertEqual(local.context(self.store,job)['basis']['scope']['reads'],['branch'])
        self.assertEqual(self.store.rows('SELECT * FROM review_contexts'),[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])


class SnapshotTiming(unittest.TestCase):
    def test_routine_basis_is_frozen_before_staging_can_publish_an_intervening_generation(self):
        from test_local436 import LocalTests
        helper = LocalTests('test_disjoint_same_file_seven_duties_keep_peers_and_unknowns')
        helper.setUp(); self.addCleanup(helper.doCleanups)
        helper.config['canonical_publication']['library']='/sdk'
        original = publication.prepare
        captured = {}
        def staging(store,attempt,before,policy):
            row = store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))
            self.assertIsNotNone(row, 'actual read basis must exist BEFORE staging can release an intervening commit')
            captured.update(json.loads(row['basis']))
            store.db.execute('INSERT INTO local_point_versions VALUES(?,?)',('a',19))
            return original(store,attempt,before,policy)
        with patch.object(publication,'prepare',side_effect=staging):
            job,attempt = helper.prepare()
        basis = json.loads(helper.store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))['basis'])
        self.assertEqual(basis,captured)
        with self.assertRaisesRegex(Refusal,'read-set is stale'):
            local.current_basis(helper.store,job)


class StoppedMapping(unittest.IsolatedAsyncioTestCase):
    """Actual SDK, stopped software grants and future-only production selection.

    Only principal authentication and collected model returns are fixture seams.
    No epoch is rotated between independent known receiver inputs.
    """
    post = Ingress.post
    classify = Ingress.classify
    receipt = Ingress.receipt

    async def asyncSetUp(self):
        import test_software_consumption as software_tests
        from support import config_at
        from coordinator_runtime import processing
        def configured(path):
            cfg = config_at(path)
            self.catalog = Path(path)/'catalog.json'
            self.catalog.write_text(encode({'a':{'state':'old'},'b':{'state':'other'}}))
            cfg['canonical_publication']['library']='/sdk'
            cfg['local_integration'] = {'max_inflight':8,'points':{
                key:{'kind':'item','line':'Main','incarnation':'one','bindings':[{'target':str(self.catalog),'path':[key]}],
                     'resources':[],'protected':[],'writable':['state']} for key in ('a','b')},
                'tasks':{t:{'capacity':5,'discovery_batch':4,'points':['a','b'],
                            'method':cfg['tasks'][t]['templates'][0],'authority':'fictional receiver mapping authority'}
                         for t in ('work-proposer','work-integrator')}}
            return cfg
        with patch.object(software_tests,'config_at',side_effect=configured):
            await software_tests.SoftwareConsumption.asyncSetUp(self)
        self.board_path = str(self.path)
        with self.store.tx():
            self.store.db.execute('UPDATE enrollments SET intake=0')
        for role,board in self.boards.items():
            with software_tests.fixture_actor(board.store,self.config['roles'][role]['owner']):
                board.revoke(self.store.one('SELECT grant_id FROM enrollments WHERE role=?',(role,))['grant_id'])
        self.processing_boards = {r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        selection = {'basis':processing.basis(self.store,self.processing_boards,future_only=True),
            'authority':'fictional explicit future receiver mapping selection','retained_events':[],
            'recover_controls':{},'future_intake':True,'tasks':list(self.config['tasks']),
            'input_mappings':['work-proposer','work-integrator'],
            'max_shared_rows':1000,'max_shared_payload_bytes':1048576,'max_runtime_rows':100,
            'service':{'max_inflight':8,'reviews':{},'legacy_resources':{}}}
        with software_tests.fixture_actor(self.processing_boards['Work'].store,self.config['roles']['Work']['owner']):
            self.key = processing.select(self.store,self.processing_boards,selection)['capability']
        self.store.processing = processing.Access(self.store,self.key,self.processing_boards)
        self.boards = self.processing_boards

    async def test_future_selected_mapping_preserves_parallel_known_scopes_without_epoch_rotation(self):
        from coordinator_runtime import processing
        first = self.post(); self.classify(first,'work-proposer')
        receipt = self.receipt(first,'work-proposer',{'state':'known','reads':['a'],'writes':[]})
        with self.assertRaises(Refusal):
            processing.map_input(self.store,self.boards,self.key,first['id'],self.config['actor'],receipt)
        resolution = processing.map_input(self.store,self.boards,self.key,first['id'],self.config['roles']['Work']['owner'],receipt)
        self.classify(first,'work-proposer')
        first_job = self.store.reserve(); self.assertIsNotNone(first_job)
        second = self.post(text='Other existing scope'); self.classify(second,'work-proposer')
        processing.map_input(self.store,self.boards,self.key,second['id'],self.config['roles']['Work']['owner'],
            self.receipt(second,'work-proposer',{'state':'known','reads':['b'],'writes':[]}))
        self.classify(second,'work-proposer')
        second_job = self.store.reserve(); self.assertIsNotNone(second_job)
        self.assertEqual([local.scope_for(self.store,j)['reads'] for j in (first_job,second_job)],[['a'],['b']])
        self.assertEqual(self.store.input_resolution(first['id']),resolution)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM processing_capabilities')['n'],1)
        self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'),[])
        self.assertTrue(all(r['intake']==0 for r in self.store.rows('SELECT intake FROM enrollments')))

    async def test_unselected_task_and_original_hold_refuse_before_mapping_read(self):
        from coordinator_runtime import processing
        source = self.post(); self.classify(source,'work-proposer')
        with self.assertRaises(Refusal):
            processing.map_input(self.store,self.boards,self.key,source['id'],self.config['roles']['Work']['owner'],
                self.receipt(source,'branch-proposer',{'state':'new'}))
        self.store.set_hold(source['id'],'fictional privacy hold')
        with patch.object(self.store,'event',side_effect=AssertionError('held source acquisition')), self.assertRaises(Refusal):
            processing.map_input(self.store,self.boards,self.key,source['id'],self.config['roles']['Work']['owner'],
                self.receipt(source,'work-proposer',{'state':'new'}))
        self.assertEqual(self.store.rows('SELECT * FROM input_resolutions'),[])


class BoardPublication(unittest.TestCase):
    def test_original_sdk_Board_mapping_reaches_all_seven_existing_consumers(self):
        from test_local436 import LocalTests
        from coordinator_runtime.board import Board
        from coordinator_runtime.store import Store
        helper = LocalTests('test_disjoint_same_file_seven_duties_keep_peers_and_unknowns')
        helper.setUp(); self.addCleanup(helper.doCleanups)
        helper.store.close()
        helper.config['delivery']={'recipients':{'Work':{'session':helper.config['roles']['Work']['owner'],
            'profile':helper.config['roles']['Work']['profile'],'board_role':helper.config['roles']['Work']['board_role']}}}
        helper.config['state_dir']=str(helper.area/'board-state')
        helper.config['canonical_publication']['library']='/sdk'
        helper.store = Store(helper.config); self.addCleanup(helper.store.close)
        sdk = module_at('/sdk','board_store'); catalog = module_at('/sdk','catalog')
        cfg=helper.config; owner=cfg['roles']['Work']['owner']
        with catalog.catalog(Path(cfg['board_home'])) as conn:
            entry=catalog.create(conn,Path(cfg['board_home']),'publication','Owned seven-consumer Board fixture',
                                 board_id=cfg['roles']['Work']['board_id'],temporary_test=True)
        with sdk.database(entry['db_path']) as conn:
            sdk.bind_board(conn,entry['board_id'],initialize=True)
            with patch.object(sdk,'acting_session',side_effect=lambda expected:expected):
                sdk.register(conn,sdk.parser().parse_args(['register','--session',owner,'--role',cfg['roles']['Work']['board_role'],
                                                         '--profile',cfg['roles']['Work']['profile'],'--route','managed']))
        board=Board(cfg,'Work')
        with patch.object(board.store,'acting_session',side_effect=lambda expected:expected):
            grant=board.grant(helper.store,'fictional independently delegated joined seven-file duty',completion=True,delivery=True)
        helper.store.enroll('Work',grant)
        helper.store.reconcile_legacy('Work',owner,{'collector':'fictional original custodian','evidence':['fixture has no prior effects'], 'remaining_holds':[]})
        with sdk.database(entry['db_path']) as conn:
            with patch.object(sdk,'acting_session',side_effect=lambda expected:expected):
                sdk.post(conn,sdk.parser().parse_args(['post','--session',owner,'--topic','fixture','--kind','finding',
                                                       '--text','Independent original a state update','--to',owner]))
        source=board.scan(helper.store)[0]; helper.store.ingest(source,cursor=source['post'])
        receipt=Ingress.receipt(self,source,'work-integrator',{'state':'known','reads':[],'writes':['a']})
        helper.store.resolve_input(source['id'],owner,receipt)
        attempt,message=helper.store.claim_classification()
        collect(helper.store,attempt,{'event_id':message['id'],'task':'work-integrator','package':None,'reason':'fictional fresh LOW route'})
        helper.store.commit_classification(attempt)
        ack=board.receipt(helper.store,source['id']); helper.store.ack_state(source['id'],'plain',ack)
        helper.board=board
        job,attempt=helper.prepare(source)
        self.assertTrue(helper.finish(job,attempt))
        self.assertEqual(len(helper.store.rows('SELECT * FROM file_publications')),7)
        self.assertEqual(json.loads(helper.catalog.read_text())['items'][0]['state'],'updated')
        self.assertEqual(helper.store.event(source['id']),source)
