"""Decision444 controls using fictional owned values and original service APIs.

The launcher must provide bwrap isolation. Authentication/model/owner evidence
is fixture-supplied; these controls authenticate no real actor or rollout.
"""
import copy
import json
from pathlib import Path
import unittest
import subprocess
from unittest.mock import patch
from types import SimpleNamespace

from support import enrolled, queued, event, collect, result
from test_local436 import LocalTests
from coordinator_runtime import local_integration as local, publication, routine
from coordinator_runtime.contracts import Refusal, encode, validate_config
from coordinator_runtime.contracts import digest, scoped_task
from coordinator_runtime import branches, ordinary, local_native
from test_ordinary_effects import OrdinaryEffects
from test_local436 import CoordinationTests
from coordinator_runtime import processing, processing_admission, reviews


class MaterialTests(unittest.TestCase):
    setUp = LocalTests.setUp
    versions = LocalTests.versions
    enqueue = LocalTests.enqueue
    prepare = LocalTests.prepare
    finish = LocalTests.finish

    def reopen(self):
        self.store.close()
        self.config['state_dir'] = str(self.area/'changed-state')
        validate_config(self.config)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)

    def alias(self):
        data = json.loads(self.catalog.read_text())
        data['items'][0]['ticket'] = 'ticket-a'
        self.catalog.write_text(encode(data))
        point = copy.deepcopy(self.config['local_integration']['points']['a'])
        point['bindings'][0]['path'] = ['items', {'field':'ticket', 'value':'ticket-a'}]
        self.config['local_integration']['points']['alias'] = point
        self.config['tasks']['work-integrator']['responses']['complete'] = []
        for p in self.config['local_integration']['tasks'].values():
            p['points'].append('alias')
        self.reopen()

    def lens(self, path, writable, protected=()):
        p = self.config['local_integration']['points']['a']
        p['bindings'][0]['path'] = path
        p['writable'] = list(writable)
        p['protected'] = list(protected)
        self.reopen()

    def test_alternate_selectors_exclude_same_actual_material_across_roles(self):
        self.alias()
        self.prepare()
        waiting = self.enqueue('alias', role='Branch')
        self.assertIsNone(self.store.reserve())
        self.enqueue('b', role='Branch')
        job = self.store.reserve()
        self.assertEqual(local.scope_for(self.store, job)['writes'], ['b'])
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?', (waiting['id'],))['state'], 'queued')

    def test_alternate_selectors_pair_and_change_restore_invalidates_old_decision(self):
        self.alias()
        original = self.versions('alias')['alias']
        first = self.prepare()
        self.assertTrue(self.finish(*first, state='intervening'))
        self.store.finish_job(first[0]['id'], first[0]['token'])
        second = self.prepare(self.enqueue('alias'))
        self.assertTrue(self.finish(*second, state='old'))
        self.store.finish_job(second[0]['id'], second[0]['token'])
        self.assertEqual(json.loads(self.catalog.read_text())['items'][0]['state'], 'old')
        self.assertNotEqual(original, self.versions('alias')['alias'])
        source = event(self.config, 'old-decision', 'Work', 'work-integrator')
        source['integration'] = {'reads':[], 'writes':['alias'], 'versions':{'alias':original}}
        queued(self.store, source)
        job, attempt = self.prepare(source)
        self.assertEqual(local.context(self.store, self.store.job(job['id']))['basis']['scope']['mode'], 'reconcile')
        with self.assertRaisesRegex(Refusal, 'all four'):
            self.finish(job, attempt, steps=False)

    def test_hardlink_alias_is_an_explicit_unsupported_artifact_before_effect(self):
        alias = self.area/'same-file.json'
        alias.hardlink_to(self.catalog)
        point = copy.deepcopy(self.config['local_integration']['points']['a'])
        point['bindings'] = [{'target':str(alias), 'path':['items', {'field':'id','value':'a'}, 'state']}]
        self.config['local_integration']['points']['alias'] = point
        # No new publisher member is invented: only the Branch reader gets this
        # separately authorized alias; Work keeps its exact seven consumers.
        self.config['local_integration']['tasks']['branch-proposer']['points'].append('alias')
        self.reopen()
        with self.assertRaisesRegex(Refusal, 'single-link'):
            self.prepare()
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_parent_and_nested_lenses_exclude_actual_overlap(self):
        point = copy.deepcopy(self.config['local_integration']['points']['a'])
        point['bindings'][0]['path'].append('state')
        self.config['local_integration']['points']['nested'] = point
        self.config['local_integration']['tasks']['branch-proposer']['points'].append('nested')
        self.reopen()
        self.prepare()
        self.enqueue('nested', role='Branch', task='branch-proposer')
        self.assertIsNone(self.store.reserve())

    def test_nonobject_write_without_explicit_value_right_refuses_before_effect(self):
        self.lens(['items', {'field':'id','value':'a'}, 'state'], [])
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, '\\$value'):
            self.finish(*pair)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_explicit_scalar_value_right_preserves_all_seven_duties(self):
        self.lens(['items', {'field':'id','value':'a'}, 'state'], ['$value'])
        pair = self.prepare()
        self.assertTrue(self.finish(*pair))
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications WHERE attempt=?', (pair[1],))), 7)

    def test_scalar_owner_lens_cannot_bypass_accepted_ownership(self):
        self.lens(['items', {'field':'id','value':'a'}, 'owner'], ['$value'])
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, 'ownership'):
            self.finish(*pair, mutate=lambda d:d['items'][0].update(owner='fabricated'))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_nested_alias_cannot_bypass_another_admitted_custom_owner_protection(self):
        data = json.loads(self.catalog.read_text()); data['items'][0]['custodian'] = 'original-accepted'
        self.catalog.write_text(encode(data))
        original = self.config['local_integration']['points']['a']
        original['protected'].append('custodian')
        nested = copy.deepcopy(original)
        nested['bindings'][0]['path'].append('custodian')
        nested.update(protected=[],writable=['$value'])
        self.config['local_integration']['points']['nested'] = nested
        for p in self.config['local_integration']['tasks'].values():p['points'].append('nested')
        self.reopen()
        pair = self.prepare(self.enqueue('nested'))
        with self.assertRaisesRegex(Refusal,'ownership/identity'):
            self.finish(*pair,mutate=lambda d:d['items'][0].update(custodian='invented'))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_nonobject_type_transition_requires_an_explicit_schema_decision(self):
        self.lens(['items', {'field':'id','value':'a'}, 'state'], ['$value'])
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal,'value type'):
            self.finish(*pair,mutate=lambda d:d['items'][0].update(state=['changed-shape']))

    def test_list_value_permission_conserves_prior_members_and_multiplicity(self):
        data = json.loads(self.catalog.read_text()); data['relations'] = ['prior', 'prior', 7]
        self.catalog.write_text(encode(data))
        self.lens(['relations'], ['$value'])
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, 'array members'):
            self.finish(*pair, mutate=lambda d:d.update(relations=['prior', 7, 'new']))

    def test_list_value_permission_can_append_without_changing_prior_members(self):
        data = json.loads(self.catalog.read_text()); data['relations'] = ['prior', 7]
        self.catalog.write_text(encode(data))
        self.lens(['relations'], ['$value'])
        pair = self.prepare()
        self.assertTrue(self.finish(*pair, mutate=lambda d:d['relations'].append({'id':'new', 'owner':None})))
        self.assertEqual(json.loads(self.catalog.read_text())['relations'][:2], ['prior', 7])

    def test_invariant_list_with_no_value_right_cannot_be_replaced(self):
        self.lens(['relations'], [])
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, '\\$value'):
            self.finish(*pair, mutate=lambda d:d['relations'].append('unadmitted'))

    def test_explicit_value_right_does_not_manufacture_nested_acceptance(self):
        self.lens(['relations'], ['$value'])
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, 'manufacture acceptance'):
            self.finish(*pair, mutate=lambda d:d['relations'].append({'owner':'invented'}))

    def test_empty_catalog_bootstraps_discovery_from_controller_line_without_seed(self):
        self.config['local_integration']['points'] = {}
        for p in self.config['local_integration']['tasks'].values():
            p['points'] = []
            p['discovery_lines'] = [{'line':'Main', 'incarnation':'one', 'authority':'fictional controller-issued namespace'}]
        self.reopen()
        pair = self.prepare(self.enqueue(discovery=True))
        definition = {'kind':'item', 'line':'Main', 'incarnation':'one',
                      'bindings':[{'target':str(self.catalog), 'path':['items', {'field':'id','value':'d'}]}],
                      'resources':[], 'protected':['id','owner','acceptance_receipt'], 'writable':['state']}
        self.assertTrue(self.finish(*pair, mutate=lambda d:d['items'].append({'id':'d','owner':None,'state':'new'}),
                                   completion_extra={'discovered_points':{'new:d':definition}}))
        receipt = json.loads(self.store.one('SELECT receipt FROM local_commits')['receipt'])
        self.assertEqual(list(receipt['continuations']), ['new:d'])
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')), 7)
        self.assertNotIn('a', local.point_definitions(self.store))

    def test_known_existing_without_selector_is_owned_dependency_not_duplicate(self):
        source = event(self.config, 'unresolved-existing', 'Work', 'work-integrator')
        source['integration'] = {'unresolved_existing':'original owner must resolve existing row'}
        queued(self.store, source)
        self.enqueue('b')
        job = self.store.reserve()
        self.assertEqual(local.scope_for(self.store, job)['writes'], ['b'])
        self.assertIn('not new-work duplication', self.store.one('SELECT detail FROM operational_errors WHERE subject=?', (source['id'],))['detail'])
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])

    def test_nonfile_discovery_cannot_register_file_points_without_consumers(self):
        self.enqueue(role='Branch',task='branch-proposer',discovery=True)
        job = self.store.reserve(); self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'],job['token']); job = self.store.job(job['id'])
        local.prepare_input_basis(self.store,job,attempt,self.config['tasks'][job['task']])
        answer = result()
        answer['completion'] = {'integration_steps':[{'step':s,'evidence':'fictional '+s} for s in local.STEPS],
                                'discovered_points':{'new:file':copy.deepcopy(self.config['local_integration']['points']['a'])}}
        collect(self.store,attempt,answer)
        with self.assertRaisesRegex(Refusal,'complete consumer publication'):
            self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'),[])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_permanent_old_execution_fence_keeps_duties_without_global_readiness(self):
        old,attempt = self.prepare()
        source = json.loads(old['members'])[0]['event']
        # Existing fenced/unknown native state is fictional fixture input, not
        # an assertion that this test authenticated an actual retirement.
        self.store.db.execute('INSERT INTO integration_retirements VALUES(?,?,?,?,?,?)',
            (old['id'],attempt,self.config['roles']['Work']['owner'],'{}',encode({'evidence':'fictional existing permanent fence'}),self.store.clock()))
        original = self.store.job(old['id'])
        self.enqueue('b')
        self.assertIsNotNone(self.store.reserve())
        with self.assertRaisesRegex(Refusal,'execution retired'):
            self.store.require_execution_open(old['id'])
        self.assertEqual(self.store.job(old['id']),original)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source,))['processed_at'])

    def test_all_five_pool_membership_is_hot_user_controlled(self):
        from coordinator_runtime.execution_pool import _module
        pool = _module.Pool(Path(self.config['execution_pool_routes']))
        known = ['.codex','.codex2','.codex3','.codex4','.codex5']
        pool.set(known)
        self.assertEqual({self.store.execution_pool.allocate()['profile'] for _ in range(5)},set(known))
        pool.set(['.codex4'])
        self.assertEqual(self.store.execution_pool.allocate()['profile'],'.codex4')
        pool.set([])
        with self.assertRaisesRegex(Refusal,'empty'):
            self.store.execution_pool.allocate()

    def test_repeated_unchanged_violation_notifies_and_healthy_has_no_alert(self):
        self.assertEqual(self.store.emit_alerts(),[])
        source = self.enqueue()
        received = self.store.one('SELECT received FROM events WHERE id=?',(source['id'],))['received']
        self.store.clock = lambda:received+1000
        first = self.store.emit_alerts()
        self.store.clock = lambda:received+1002
        second = self.store.emit_alerts()
        self.assertTrue(first); self.assertTrue(second)
        self.assertTrue({a['id'] for a in first}.isdisjoint({a['id'] for a in second}))


class NativeEffects(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = OrdinaryEffects.asyncSetUp
    git = OrdinaryEffects.git
    boundary = OrdinaryEffects.boundary
    admission = OrdinaryEffects.admission

    def binding(self, key, definition, tasks):
        self.config['local_integration'] = {'max_inflight':8, 'points':{key:definition},
            'tasks':{t:{'capacity':5,'discovery_batch':4,'points':[key],
                       'authority':'fictional current issuer-selected bounded native decisions',
                       'method':self.config['tasks'][t]['templates'][0]} for t in tasks}}
        validate_config(self.config)

    def branch(self, accept=True):
        self.git('remote','add','origin','https://example.invalid/owned-fixture')
        # The ordinary fixture's actual Board membership and owner API are
        # used. Only acting_session is a fictional authentication seam.
        board = self.boards['Work']
        root = self.config['roles']['Work']['owner']
        self.store.processing = SimpleNamespace(current=lambda:({'issuer':root},{}), boards=self.boards)
        receipt = {'id':'branch-native', 'repository':str(self.repo), 'origin':'https://example.invalid/owned-fixture',
                   'ref':'refs/heads/destination','incarnation':'branch-life','scope':'package',
                   'root':root,'authority':'fictional explicitly selected responsible Root distinct from builder'}
        branches.register(self.store, root, receipt)
        if accept:
            with self.assertRaises(Refusal):
                branches.accept(self.store, receipt['id'], self.acceptor, 'wrong actor')
            branches.accept(self.store, receipt['id'], root, 'fictional actual member acceptance; no native actor claim')
        self.store.processing = None
        admitted = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))['receipt'])
        admitted['task_scopes']['branch-integrator']['branch_binding'] = receipt['id']
        self.store.admit('package',self.config['roles']['Branch']['owner'],admitted)
        return receipt

    def prepared_native(self, key, role='Branch', discovery=False, category='complete'):
        task = 'branch-integrator' if role=='Branch' else 'qa-execution'
        source = event(self.config,'native-preparation',role,task,'package')
        if not discovery:
            source['integration'] = {'reads':[], 'writes':[key], 'versions':{key:local.version(self.store,key,{})}}
        queued(self.store,source)
        job = self.store.reserve(); self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'],job['token']); job = self.store.job(job['id'])
        admission = self.store.one('SELECT * FROM admissions WHERE package=?',('package',))
        self.boards[role].bind_software_attempt(self.store,job,attempt,admission)
        task_value = scoped_task(task,self.config['tasks'][task],admission)
        local.prepare_input_basis(self.store,job,attempt,task_value)
        answer = result(category=category)
        answer['completion'] = {'integration_steps':[{'step':s,'evidence':'fictional independent method return '+s} for s in local.STEPS]}
        collect(self.store,attempt,answer,tool_completion={'complete':True,'items':[],'nonzero_completions':[]})
        return job,attempt

    async def test_branch_native_ref_original_effect_and_separate_acceptance(self):
        self.admission(); receipt = self.branch()
        point = {'kind':'item','line':'Main','incarnation':receipt['incarnation'],
                 'bindings':[{'native':'branch','id':receipt['id']}], 'resources':[], 'protected':[], 'writable':[]}
        self.binding('branch',point,['branch-integrator']); self.boundary()
        job,attempt = self.prepared_native('branch')
        self.assertEqual(branches.job_branch(self.store,job)['id'],receipt['id'])
        self.assertIsNotNone(self.store.one('SELECT id FROM branch_turns WHERE id=?',(attempt,)))
        self.assertIsNone(self.store.one('SELECT attempt FROM routine_runs'))
        self.assertTrue(await ordinary.perform(self.store,self.boards['Branch'],job))
        self.assertEqual(self.git('rev-parse','destination'),self.head)
        actual = json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(actual['collector'],self.store.controller)
        self.assertFalse(ordinary.accepted_package(self.store,'package'))
        await ordinary.accept(self.store,self.acceptor,attempt,'accepted',
            {'execution_hash':digest(actual),'rationale':'independent intended destination/source correspondence','unknowns':[]})
        self.assertTrue(ordinary.accepted_package(self.store,'package'))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        self.assertIsNotNone(self.store.one('SELECT * FROM local_material_commits WHERE attempt=?',(attempt,)))

    async def test_branch_native_requires_original_root_acceptance(self):
        self.admission(); receipt = self.branch(accept=False)
        with self.assertRaisesRegex(Refusal,'unavailable'):
            local_native.snapshot(self.store,{'native':'branch','id':receipt['id']})
        self.assertEqual(self.git('rev-parse','destination'),self.old)

    async def test_execution_native_QA_preserves_runner_resource_and_independent_acceptance(self):
        self.git('remote','add','origin','https://example.invalid/owned-QA')
        self.admission(kind='local-qa')
        row = self.store.one('SELECT * FROM admissions WHERE package=?',('package',))
        point = {'kind':'item','line':'Main','incarnation':digest(row['receipt']),
                 'bindings':[{'native':'execution','package':'package','task':'qa-execution'}],
                 'resources':[], 'protected':[], 'writable':[]}
        self.binding('execution',point,['qa-execution']); self.boundary()
        job,attempt = self.prepared_native('execution',role='QA',category='consolidated')
        try:
            self.assertTrue(await ordinary.perform(self.store,self.boards['QA'],job))
        except Refusal:
            print('Retained original QA tool failures:', [{k:r.get(k) for k in ('label','exit','complete','stderr')}
                  for v in self.store.rows('SELECT record FROM ordinary_tool_records WHERE attempt=?',(attempt,))
                  if (r:=json.loads(v['record'])).get('complete') and r.get('exit') != 0])
            raise
        self.assertTrue((self.area/'qa-output/actual-run.txt').is_file())
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(receipt['outcome']['source_execution']['method'],'git-blobs-readonly-namespace-v1')
        self.assertFalse(ordinary.accepted_package(self.store,'package'))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])
        self.assertIsNone(self.store.one('SELECT attempt FROM routine_runs'))
        self.store.finish_job(job['id'],job['token'])
        output = self.store.event(self.store.job(job['id'])['response'])
        self.assertEqual(output['source_attempt'],attempt)
        self.assertEqual(output['effect_observation']['collector'],self.store.controller)
        self.assertEqual(output['package'],'package')

    async def test_stale_native_decision_refuses_before_original_effect_intent(self):
        self.admission(); receipt = self.branch()
        point = {'kind':'item','line':'Main','incarnation':receipt['incarnation'],
                 'bindings':[{'native':'branch','id':receipt['id']}], 'resources':[], 'protected':[], 'writable':[]}
        self.binding('branch',point,['branch-integrator']); self.boundary()
        job,attempt = self.prepared_native('branch')
        # Actual branch history API records an intervening decision even when
        # the visible ref is unchanged. No fixture version is manufactured.
        with self.store.tx():
            branches.record(self.store,receipt['id'],receipt['root'],{'observation':'intervening current decision'})
        with self.assertRaisesRegex(Refusal,'read-set is stale'):
            await ordinary.perform(self.store,self.boards['Branch'],job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])
        self.assertEqual(self.git('rev-parse','destination'),self.old)

    async def test_execution_native_cannot_borrow_package_or_fake_Work_scope(self):
        self.admission()
        binding = {'native':'execution','package':'package','task':'branch-integrator'}
        with self.assertRaisesRegex(Refusal,'another package'):
            local_native.authorize(self.store,{'task':'branch-integrator','package':'other'},binding)
        with self.assertRaisesRegex(Refusal,'independently issued'):
            local_native.authorize(self.store,{'task':'work-proposer','package':'package'},binding)
        with self.assertRaisesRegex(Refusal,'Branch/QA task'):
            local_native.source_role(self.config,{'native':'execution','package':'package','task':'work-proposer'})

    async def test_native_ref_and_original_unknown_turn_exclude_parallel_reservation(self):
        self.admission(); receipt = self.branch()
        point = {'kind':'item','line':'Main','incarnation':receipt['incarnation'],
                 'bindings':[{'native':'branch','id':receipt['id']}], 'resources':[], 'protected':[], 'writable':[]}
        self.binding('branch',point,['branch-integrator']); self.boundary()
        self.store.db.execute('INSERT INTO branch_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)',
            ('original-unknown',receipt['id'],'builder','','original-owned-address','original-collector',
             '.codex','original-writer','{}','unknown',self.store.clock()))
        source = event(self.config,'native-overlap','Branch','branch-integrator','package')
        source['integration'] = {'reads':[],'writes':['branch'],'versions':{'branch':local.version(self.store,'branch',{})}}
        queued(self.store,source)
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.one('SELECT state FROM branch_turns WHERE id=?',('original-unknown',))['state'],'unknown')
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])


class NativeProtocol(unittest.TestCase):
    def setUp(self):
        # Same explicit NULL-account protocol projection as the inherited
        # fixture. No profile/session/turn authentication is manufactured.
        with patch.object(reviews,'SCHEMA',reviews.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT')):
            CoordinationTests.setUp(self)
    tearDown = CoordinationTests.tearDown
    authority = CoordinationTests.authority
    event = CoordinationTests.event
    receipt = CoordinationTests.receipt
    classify = CoordinationTests.classify
    fixture_configuration = CoordinationTests.fixture_configuration
    boards = CoordinationTests.boards
    fresh = CoordinationTests.fresh
    configure = CoordinationTests.configure

    def repository(self):
        repo = self.directory/'native-repository'; repo.mkdir()
        commands = [['init','--initial-branch=fixture'], ['config','user.name','Fictional'],
                    ['config','user.email','fixture@example.invalid'], ['config','commit.gpgsign','false'],
                    ['remote','add','origin','https://example.invalid/fixture']]
        for args in commands:
            subprocess.run(['/usr/bin/git','-C',str(repo),*args], check=True, capture_output=True)
        (repo/'source.txt').write_text('independent fictional intent\n')
        for args in [['add','source.txt'],['commit','-m','owned fictional source']]:
            subprocess.run(['/usr/bin/git','-C',str(repo),*args], check=True, capture_output=True)
        return repo

    def native_selection(self, coordination=True):
        method = self.directory/'method.md'; method.write_text('Fictional admitted four-step method, no live meaning.\n')
        for task in ('bi','wp'):
            self.runtime.config['tasks'][task]['templates'] = [str(method)]
            self.runtime.config['tasks'][task]['effect_authority'] = {'read_roots':[str(self.directory)],'write_roots':[],'operations':['read-source']}
        self.runtime.config['local_integration'] = {'max_inflight':8,'points':{},'tasks':{
            task:{'capacity':5,'discovery_batch':4,'points':[],'authority':'fictional genuine bounded role decision selection',
                  'method':str(method),'new_point_prefix':'native:',
                  'discovery_lines':[{'line':'Main','incarnation':'life','authority':'fictional selected native line'}]}
            for task in ('bi','wp')}}
        self.configure(coordination)

    def branch_return(self):
        repo = self.repository()
        source = self.fresh('native-return','Branch')
        processing_admission.admit(self.runtime,source['id'])
        root = '22222222-2222-4222-8222-222222222222'
        self.conn.execute('CREATE TABLE sessions(session,status,role,profile)')
        self.conn.execute("INSERT INTO sessions VALUES(?,'active','work-coordinator',NULL)",(root,))
        association = {'id':'native-existing-branch','repository':str(repo),'origin':'https://example.invalid/fixture',
                       'ref':'refs/heads/fixture','incarnation':'life','scope':source['package'],'root':root,
                       'authority':'fictional issued branch authority'}
        branches.register(self.runtime,'fictional-issuer',association)
        branches.accept(self.runtime,association['id'],root,'fictional existing original coordinator acceptance')
        self.classify(source,'bi')
        job = self.runtime.reserve(); self.assertIsNotNone(job)
        attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
        self.selected_boards['Branch'].bind_software_attempt(self.runtime,job,attempt,
            self.runtime.one('SELECT * FROM admissions WHERE package=?',(source['package'],)))
        local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks']['bi'])
        definition = {'kind':'item','line':'Main','incarnation':'life',
                      'bindings':[{'native':'branch','id':association['id']}], 'resources':[],'protected':[],'writable':[]}
        answer = result(category='scope',summary='fictional existing branch broader Work concern')
        answer.update(handoffs=[],no_handoff_reason='fictional report preserves existing native authority, no new effects')
        answer['completion'] = {'integration_steps':[{'step':s,'evidence':'fictional attributed '+s} for s in local.STEPS],
                                'discovered_points':{'native:branch':definition}}
        self.runtime.begin(attempt,{'fictional':True})
        self.runtime.collect(attempt,{'exit':0,'capture':'complete','cleanup':'no-session-created','result':answer,
            'detail':{'tool_completion':{'complete':True,'items':[],'nonzero_completions':[]}}})
        response = self.runtime.finish_job(job['id'],job['token'])
        self.assertIsNotNone(response)
        return source,job,self.runtime.event(response)

    def test_existing_native_branch_discovery_and_separate_Work_coordination(self):
        self.native_selection()
        source,upstream,returned = self.branch_return()
        self.assertEqual(returned['integration']['writes'],['native:branch'])
        self.assertEqual(returned['source_members'],json.loads(upstream['members']))
        self.assertEqual(returned['package'],source['package'])
        admission = json.loads(self.runtime.one('SELECT receipt FROM admissions WHERE package=?',(source['package'],))['receipt'])
        self.assertNotIn('wp',admission['task_scopes'])
        self.classify(returned,'wp')
        job = self.runtime.reserve(); self.assertIsNotNone(job)
        attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
        local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks']['wp'])
        self.assertEqual(local.context(self.runtime,job)['basis']['scope']['lane'],'anchored')
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'),[])
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.runtime.db.execute("UPDATE events SET hold='fictional source custody hold' WHERE id=?",(source['id'],))
        with self.assertRaisesRegex(Refusal,'coordination|currentness'):
            local.current_job(self.runtime,job)

    def test_native_branch_return_without_Work_coordination_is_not_execution_permission(self):
        self.native_selection(False)
        source,upstream,returned = self.branch_return()
        self.classify(returned,'wp')
        self.assertIsNone(self.runtime.reserve())
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])

    def review_selection(self):
        repo = self.repository()
        method = self.directory/'review-method.md'; method.write_text('Fictional original method, preserve collector and history.\n')
        task = copy.deepcopy(self.runtime.config['tasks']['ri'])
        task.update(phase='proposer',responses={'proposal':['ri']},templates=[str(method)],cwd=str(repo),
                    effect_authority={'read_roots':[str(repo)],'write_roots':[],'operations':['read-source']})
        self.runtime.config['tasks']['rp'] = task
        point = {'kind':'item','line':'Main','incarnation':'fictional-original-run',
                 'bindings':[{'native':'review','component':'component'}], 'resources':[], 'protected':[],'writable':[]}
        self.runtime.config['local_integration'] = {'max_inflight':8,'points':{'review':point},'tasks':{
            'rp':{'capacity':5,'discovery_batch':4,'points':['review'],'authority':'fictional original review decision scope','method':str(method)}}}
        self.configure()
        policy = {'caller':'/usr/bin/true','caller_sha256':reviews.sha(Path('/usr/bin/true').read_bytes()),
                  'routes':{},'deadline':20,'method':str(method),'method_files':reviews.method_files(str(method)),
                  'components':{'component':{'repository':str(repo),'origin':'https://example.invalid/fixture',
                      'paths':['source.txt'],'history':str(self.runtime.home/'review-history'/'component.md'),
                      'authority':'fictional original component source authority'}}}
        old = json.loads(self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.key,))['selection'])
        processing.revoke(self.runtime,self.selected_boards,self.key)
        old['basis'] = processing.basis(self.runtime,self.selected_boards)
        old.pop('expires'); old.pop('max_starts')
        old['service'] = {'max_inflight':8,'reviews':{'rp':policy},'legacy_resources':{}}
        self.key = processing.select(self.runtime,self.selected_boards,old)['capability']
        self.runtime.processing = processing.Access(self.runtime,self.key,self.selected_boards)
        self.runtime.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)',
            ('component',self.key,None,'fictional-route','fictional-original-handle','fictional-original-run',
             self.runtime.controller,'live','fictional-original-head','fictional-history-hash',1000.,))

    def test_review_native_original_context_revision_collector_and_component_boundaries(self):
        self.review_selection()
        source = {'id':'review-native-input','role':'Reviews','recipient':'fictional-logical-Reviews','kind':'board','post':11,
                  'body':{'review':{'component':'component'}},'package':None,'allowed_tasks':['rp'],
                  'integration':{'reads':['review'],'writes':[],'versions':{'review':local.version(self.runtime,'review',{})}}}
        self.runtime.ingest(source); self.classify(source,'rp')
        job = self.runtime.reserve(); self.assertIsNotNone(job)
        attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
        local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks']['rp'])
        before = local.context(self.runtime,job)['basis']['versions']['review']
        self.runtime.db.execute("UPDATE review_contexts SET history_hash='later-history' WHERE component='component'")
        self.assertNotEqual(before,local.version(self.runtime,'review',{},job))
        self.assertEqual(local.context(self.runtime,job)['basis']['versions']['review'],before)
        self.runtime.db.execute("UPDATE review_contexts SET collector='another-original' WHERE component='component'")
        with self.assertRaisesRegex(Refusal,'collector'):
            local.current_job(self.runtime,job)
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'),[])


if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main()
