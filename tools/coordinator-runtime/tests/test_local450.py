"""Decision450 controls at original discovery and seven-consumer boundaries.

All actors, permissions and acceptance semantics are fictional declarations.
The launcher must isolate namespaces/network, public source and owned fixtures.
No native session, provider authentication or real Work execution is qualified.
"""
import copy
import json
import sqlite3
import subprocess
from contextlib import contextmanager, ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from support import result
from test_local436 import LocalTests
from test_local444 import MaterialTests, NativeEffects, NativeProtocol
from coordinator_runtime import local_integration as local, local_native, branches, ordinary, reviews
from coordinator_runtime.contracts import Refusal, digest, encode


class TypedPublication(unittest.TestCase):
    setUp = LocalTests.setUp
    versions = LocalTests.versions
    enqueue = LocalTests.enqueue
    prepare = LocalTests.prepare
    finish = LocalTests.finish
    reopen = MaterialTests.reopen
    lens = MaterialTests.lens

    def history(self, value):
        doc = json.loads(self.catalog.read_text())
        doc['relations'] = value
        self.catalog.write_text(encode(doc))
        self.lens(['relations'], ['$value'])

    def rejected(self, before, after):
        self.history(before)
        original = self.catalog.read_bytes()
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, 'array members|value type'):
            self.finish(*pair, mutate=lambda d:d.update(relations=after))
        self.assertEqual(self.catalog.read_bytes(), original)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])

    def test_bool_cannot_be_replaced_with_integer_then_appended(self):
        self.rejected([True, 'kept'], [1, 'kept', 'new'])

    def test_integer_cannot_be_replaced_with_bool_then_appended(self):
        self.rejected([1, 'kept'], [True, 'kept', 'new'])

    def test_nested_containers_retain_boolean_type(self):
        self.rejected([{'audit':[False, {'nested':True}]}],
                      [{'audit':[0, {'nested':1}]}, 'new'])

    def test_mixed_equal_values_cannot_spend_duplicate_boolean_twice(self):
        self.rejected([True, 1, True], [True, 1, 1, 'new'])

    def test_nested_duplicate_cannot_be_dropped(self):
        self.rejected([[True], [True], [1]], [[True], [1], 'new'])

    def test_legal_typed_duplicates_reorder_and_append_survive(self):
        self.history([True, 1, {'audit':[False]}, True])
        pair = self.prepare()
        self.assertTrue(self.finish(*pair, mutate=lambda d:d.update(
            relations=[1, True, True, {'audit':[False]}, {'proposed_owner':'candidate'}])))
        actual = json.loads(self.catalog.read_text())['relations']
        # Independent typed consumer assertions, no call to production comparator.
        self.assertIs(type(actual[0]), int)
        self.assertIs(actual[1], True); self.assertIs(actual[2], True)
        self.assertIs(actual[3]['audit'][0], False)
        self.assertEqual(len(actual), 5)
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')), 7)

    def ownership(self):
        # Controller declares custodian to mean ACCEPTED ownership. A separate
        # proposed_custodian field is proposal text, never inferred acceptance.
        for task in self.config['local_integration']['tasks'].values():
            task['ownership_fields'].append('custodian')
        point = self.config['local_integration']['points']['a']
        point['writable'] += ['children', 'extension']
        doc = json.loads(self.catalog.read_text())
        doc['items'][0].update(custodian='existing-accepted', children=[])
        self.catalog.write_text(encode(doc))
        self.reopen()

    def ownership_rejected(self, change):
        self.ownership()
        original = self.catalog.read_bytes()
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, 'manufacture acceptance|ownership/identity'):
            self.finish(*pair, mutate=lambda d:change(d['items'][0]))
        self.assertEqual(self.catalog.read_bytes(), original)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_custom_accepted_field_cannot_enter_new_list_member(self):
        self.ownership_rejected(lambda item:item['children'].append({'custodian':'invented'}))

    def test_custom_accepted_field_cannot_enter_new_allowed_object(self):
        self.ownership_rejected(lambda item:item.update(extension={'deep':{'custodian':'invented'}}))

    def test_custom_accepted_field_as_new_key_is_protected(self):
        self.ownership_rejected(lambda item:item.update(extension={'custodian':'invented'}))

    def test_neutral_and_proposed_additions_keep_existing_accepted_binding(self):
        self.ownership()
        pair = self.prepare()
        def change(d):
            item = d['items'][0]
            item['children'].extend([{'custodian':None}, {'custodian':'unassigned'},
                                     {'proposed_custodian':'candidate'}])
            item['extension'] = {'nested':{'custodian':False, 'proposed_custodian':'candidate'}}
        self.assertTrue(self.finish(*pair, mutate=change))
        item = json.loads(self.catalog.read_text())['items'][0]
        self.assertEqual(item['custodian'], 'existing-accepted')
        self.assertEqual(item['children'][2]['proposed_custodian'], 'candidate')
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')), 7)


@contextmanager
def no_native_material(store):
    """Fail on acquisition, allow exact trusted permission-index queries."""
    acquired = []
    def forbidden(label):
        def call(*args, **kwargs):
            acquired.append(label)
            raise AssertionError('forbidden native acquisition: '+label)
        return call
    with ExitStack() as stack:
        for module, name in [(local_native,'branch_snapshot'), (branches,'association'),
                             (branches,'repository_identity'), (ordinary,'policy_for'),
                             (ordinary,'frozen_file'), (reviews,'git')]:
            stack.enter_context(patch.object(module, name, side_effect=forbidden(name)))
        original_rows, original_one = store.rows, store.one
        def checked(method, sql, args=()):
            if any(table in sql for table in ('branch_turns', 'review_calls', 'review_history_commits', 'ordinary_runs')):
                return forbidden('history query')(sql)
            if 'SELECT * FROM review_contexts' in sql or 'SELECT * FROM admissions' in sql:
                return forbidden('full native record')(sql)
            return method(sql, args)
        stack.enter_context(patch.object(store, 'rows', side_effect=lambda sql,args=():checked(original_rows,sql,args)))
        stack.enter_context(patch.object(store, 'one', side_effect=lambda sql,args=():checked(original_one,sql,args)))
        yield acquired
    if acquired:
        raise AssertionError(acquired)


class NativeNonfile(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = NativeEffects.asyncSetUp
    git = NativeEffects.git
    admission = NativeEffects.admission
    branch = NativeEffects.branch
    binding = NativeEffects.binding
    boundary = NativeEffects.boundary
    prepared_native = NativeEffects.prepared_native

    def discovery(self, binding, incarnation='branch-life'):
        self.binding('unused', {'kind':'item','line':'Main','incarnation':incarnation,
             'bindings':[binding], 'resources':[], 'protected':[], 'writable':[]}, ['branch-integrator'])
        policy = self.config['local_integration']
        policy['points'] = {}
        selected = policy['tasks']['branch-integrator']
        selected.update(points=[], new_point_prefix='native:', discovery_lines=[
            {'line':'Main','incarnation':incarnation,'authority':'fictional explicit current line'}])
        self.boundary()
        job, attempt = self.prepared_native('unused', discovery=True, category='scope')
        answer = result(category='scope')
        answer['completion'] = {'integration_steps':[{'step':s,'evidence':'fictional '+s} for s in local.STEPS],
            'discovered_points':{'native:found':{'kind':'item','line':'Main','incarnation':incarnation,
             'bindings':[binding], 'resources':[], 'protected':[], 'writable':[]}}}
        return job, self.store.attempt(attempt), answer

    async def test_foreign_package_branch_refuses_before_snapshot_even_wrong_incarnation(self):
        self.admission(); receipt = self.branch()
        # Different package has its own legitimate original admission.
        self.admission(package='other')
        job,attempt,answer = self.discovery({'native':'branch','id':receipt['id']}, 'guessed-life')
        self.store.db.execute("UPDATE branch_associations SET scope='other' WHERE id=?",(receipt['id'],))
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'admitted package'):
            local.finish_discovery(self.store, job, attempt, answer)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])

    async def test_execution_other_package_refuses_before_policy_source_or_history(self):
        self.admission(); self.admission(package='other')
        job,attempt,answer = self.discovery({'native':'execution','package':'other','task':'branch-integrator'}, 'guessed')
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'another package'):
            local.finish_discovery(self.store, job, attempt, answer)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])

    async def test_same_package_outside_role_roots_refuses_before_physical_Git(self):
        self.admission(); receipt = self.branch()
        job,attempt,answer = self.discovery({'native':'branch','id':receipt['id']})
        # Change only the trusted index to an independently out-of-scope source;
        # no existence, metadata or acquisition of that fictional path is needed.
        self.store.db.execute('UPDATE branch_associations SET repository=? WHERE id=?',
                              ('/forbidden-native-repository',receipt['id']))
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'read authority'):
            local.finish_discovery(self.store, job, attempt, answer)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])

    async def test_same_package_execution_outside_read_roots_refuses_before_procedure(self):
        self.admission()
        job,attempt,answer = self.discovery({'native':'execution','package':'package','task':'branch-integrator'}, 'guessed')
        admitted = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))['receipt'])
        admitted['task_scopes']['branch-integrator']['ordinary_effects']['repository'] = '/forbidden-native-repository'
        self.store.admit('package',self.config['roles']['Branch']['owner'],admitted)
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'read authority'):
            local.finish_discovery(self.store, job, attempt, answer)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])

    async def test_authorized_same_package_execution_can_be_discovered(self):
        self.admission()
        admission = self.store.one('SELECT receipt FROM admissions WHERE package=?',('package',))
        job,attempt,answer = self.discovery({'native':'execution','package':'package','task':'branch-integrator'}, digest(admission['receipt']))
        local.finish_discovery(self.store, job, attempt, answer)
        self.assertEqual(local.point_definitions(self.store)['native:found']['bindings'],
                         [{'native':'execution','package':'package','task':'branch-integrator'}])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    async def test_authorized_native_discovery_retains_original_reference(self):
        self.admission(); receipt = self.branch()
        job,attempt,answer = self.discovery({'native':'branch','id':receipt['id']})
        local.finish_discovery(self.store, job, attempt, answer)
        point = local.point_definitions(self.store)['native:found']
        self.assertEqual(point['bindings'], [{'native':'branch','id':receipt['id']}])
        receipt = json.loads(self.store.one('SELECT receipt FROM local_commits')['receipt'])
        self.assertEqual(list(receipt['continuations']), ['native:found'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])


class NativeFile(unittest.TestCase):
    def setUp(self):
        LocalTests.setUp(self)
        self.config['local_integration']['tasks']['work-integrator']['new_point_prefix'] = 'native:'
        local.policy(self.config)
    versions = LocalTests.versions
    enqueue = LocalTests.enqueue
    prepare = LocalTests.prepare
    finish = LocalTests.finish

    def native_fixture(self, kind='branch', scope='package'):
        # Explicit fictional authentication/Work coordination seam. Package
        # admission belongs to Branch; there is no invented Work execution scope.
        self.store.admit('package', self.config['roles']['Branch']['owner'], {'task_scopes':{}})
        conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE sessions(session,status,role,profile)')
        owner = self.config['roles']['Work']['owner']
        conn.execute("INSERT INTO sessions VALUES(?,'active','work',NULL)",(owner,))
        @contextmanager
        def opened(**kw): yield conn
        self.store.processing = SimpleNamespace(current=lambda:({'issuer':owner},{'work_coordination':{
            'tasks':['work-integrator'],'source_roles':['Branch','QA','Reviews']}}),
            boards={'Work':SimpleNamespace(opened=opened)}, task=lambda row:True)
        repo = self.area/'native-repo'; repo.mkdir()
        for args in [('init','--initial-branch=fixture'),('config','user.name','Fictional'),
                     ('config','user.email','fixture@example.invalid'),('config','commit.gpgsign','false'),
                     ('remote','add','origin','https://example.invalid/fixture')]:
            subprocess.run(['git','-C',str(repo),*args], check=True,capture_output=True)
        (repo/'source.txt').write_text('fictional original source')
        for args in [('add','source.txt'),('commit','-m','fixture source')]:
            subprocess.run(['git','-C',str(repo),*args], check=True,capture_output=True)
        receipt = {'id':'fixture-branch','repository':str(repo),'origin':'https://example.invalid/fixture',
                   'ref':'refs/heads/fixture','incarnation':'one','scope':'package','root':owner,
                   'authority':'fictional original selected authority'}
        branches.register(self.store,owner,receipt)
        branches.accept(self.store,receipt['id'],owner,'fictional existing acceptance')
        if scope != 'package':
            self.store.db.execute('UPDATE branch_associations SET scope=? WHERE id=?',(scope,receipt['id']))
        self.store.processing = None
        return {'native':'branch','id':receipt['id']}

    def file_discovery(self, binding, *, coordinated=True):
        pair = self.prepare(self.enqueue(discovery=True, package='package'))
        # The authentic model/collection seam is fixture-provided, like the
        # existing seven-duty publisher controls. Coordination is independent.
        if coordinated:
            self.store.processing = SimpleNamespace(current=lambda:({}, {'work_coordination':{
                'tasks':['work-integrator'], 'source_roles':['Branch','QA','Reviews']}}),
                task=lambda row:True, role=lambda role:True, authorize=lambda attempt:None)
        definition = {'kind':'item','line':'Main','incarnation':'one','bindings':[binding],
                      'resources':[], 'protected':['owner','acceptance_receipt'], 'writable':[]}
        return pair, {'discovered_points':{'native:found':definition}}

    def test_file_discovery_without_Work_coordination_acquires_no_native_material(self):
        binding = self.native_fixture()
        pair, extra = self.file_discovery(binding,coordinated=False)
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'independently issued'):
            self.finish(*pair, mutate=lambda d:None, completion_extra=extra)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_file_discovery_foreign_branch_cannot_be_retained(self):
        binding = self.native_fixture(scope='other')
        pair, extra = self.file_discovery(binding)
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'admitted package'):
            self.finish(*pair, mutate=lambda d:None, completion_extra=extra)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_foreign_file_reference_cannot_register_even_with_matching_incarnation(self):
        binding = self.native_fixture(scope='other')
        pair, extra = self.file_discovery(binding)
        with self.assertRaisesRegex(Refusal,'admitted package'):
            self.finish(*pair,mutate=lambda d:None,completion_extra=extra)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_file_discovery_execution_other_package_acquires_no_policy(self):
        self.native_fixture()
        pair,extra = self.file_discovery({'native':'execution','package':'other','task':'branch-integrator'})
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'another package'):
            self.finish(*pair, mutate=lambda d:None, completion_extra=extra)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_Work_review_coordination_cannot_borrow_an_unrelated_original_component(self):
        self.native_fixture()
        # Context exists, but this file job has no actual original Reviews
        # return. A task/source-role coordination grant alone cannot name it.
        self.store.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)',
            ('foreign-component','fixture-capability','.codex','fictional-route','handle','run',
             self.store.controller,'live','head','hash',1000.))
        pair,extra = self.file_discovery({'native':'review','component':'foreign-component'})
        with no_native_material(self.store), self.assertRaisesRegex(Refusal,'original component return'):
            self.finish(*pair,mutate=lambda d:None,completion_extra=extra)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_file_discovery_with_independent_coordination_keeps_seven_duties(self):
        binding = self.native_fixture()
        pair, extra = self.file_discovery(binding)
        self.assertTrue(self.finish(*pair,mutate=lambda d:None,completion_extra=extra))
        self.assertEqual(local.point_definitions(self.store)['native:found']['bindings'], [binding])
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')), 7)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])


class OriginalReviewReturns(NativeProtocol):
    def configure(self, coordination=True):
        if 'rp' in self.runtime.config['tasks']:
            selected = self.runtime.config['local_integration']['tasks']['rp']
            self.runtime.config['local_integration']['tasks']['wp'] = copy.deepcopy(selected)
            self.runtime.config['tasks']['wp']['templates'] = [selected['method']]
            self.runtime.config['tasks']['wp']['effect_authority'] = {
                'read_roots':[str(self.directory)], 'write_roots':[], 'operations':['read-source']}
            self.runtime.config['tasks']['wp'].setdefault('responses', {})['complete'] = ['wp']
            self.runtime.config['tasks']['rp']['responses']['scope'] = ['wp']
        return NativeProtocol.configure(self,coordination)

    def review_job(self):
        source = {'id':'review450-source','role':'Reviews','recipient':'fictional-logical-Reviews',
                  'kind':'board','post':11,'body':{'review':{'component':'component'}},
                  'package':None,'allowed_tasks':['rp'],
                  'integration':{'reads':['review'],'writes':[],
                     'versions':{'review':local.version(self.runtime,'review',{})}}}
        self.runtime.ingest(source); self.classify(source,'rp')
        job = self.runtime.reserve(); self.assertIsNotNone(job)
        attempt = self.runtime.start_job(job['id'],job['token'])
        job = self.runtime.job(job['id'])
        self.selected_boards['Reviews'].bind_software_attempt(self.runtime,job,attempt,None)
        local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks']['rp'])
        return job,attempt

    def finish_report(self, job, attempt):
        answer = result(category='complete' if job['role']=='Work' else 'scope')
        answer.update(handoffs=[],no_handoff_reason='fictional original read-only review return')
        self.runtime.begin(attempt,{'fictional':True})
        self.runtime.collect(attempt,{'exit':0,'capture':'complete','cleanup':'no-session-created','result':answer,
            'detail':{'tool_completion':{'complete':True,'items':[],'nonzero_completions':[]}}})
        return self.runtime.finish_job(job['id'],job['token'])

    def test_original_Reviews_to_Work_and_Work_continuation_remain_readable(self):
        self.review_selection()
        job,attempt = self.review_job()
        returned = self.runtime.event(self.finish_report(job,attempt))
        for _ in range(2):
            self.classify(returned,'wp')
            job = self.runtime.reserve(); self.assertIsNotNone(job)
            attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
            self.selected_boards['Work'].bind_software_attempt(self.runtime,job,attempt,None)
            local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks']['wp'])
            basis = local.context(self.runtime,job)['basis']
            self.assertEqual(basis['scope']['reads'], ['review'])
            returned = self.runtime.event(self.finish_report(job,attempt))
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'), [])

    def test_unselected_review_component_refuses_before_context_and_history(self):
        self.review_selection()
        job,attempt = self.review_job()
        with no_native_material(self.runtime), self.assertRaisesRegex(Refusal,'component/material'):
            local_native.snapshot(self.runtime,{'native':'review','component':'unselected'},job)


if __name__ == '__main__':
    unittest.main()
