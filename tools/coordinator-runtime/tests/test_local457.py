"""Decision457: fictional original Source -> integrator -> Work, real schemas.

Run only inside the positive-mount bwrap sandbox. Principals, authentication,
account allocation and collected tool/model receipts are declared fixture seams;
production selection, schemas, frozen members, routing and guards execute.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from support import result
import test_local436 as prior436
import test_local444 as prior444
from test_local450 import no_native_material
from test_processing188 import engine_config
from coordinator_runtime.store import Store
from coordinator_runtime import processing, reviews, local_native, branches
from coordinator_runtime import local_integration as local
from coordinator_runtime.contracts import Refusal, digest, encode


class FieldPresence(unittest.TestCase):
    setUp = prior436.LocalTests.setUp
    versions = prior436.LocalTests.versions
    enqueue = prior436.LocalTests.enqueue
    prepare = prior436.LocalTests.prepare
    finish = prior436.LocalTests.finish
    reopen = prior444.MaterialTests.reopen

    def refused(self, change, pattern='unselected/unknown|ownership/identity|protected'):
        original = self.catalog.read_bytes()
        pair = self.prepare()
        with self.assertRaisesRegex(Refusal, pattern):
            self.finish(*pair, mutate=lambda d:change(d['items'][0]))
        self.assertEqual(self.catalog.read_bytes(), original)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])

    def test_unselected_absent_field_cannot_be_created_as_null(self):
        self.refused(lambda item:item.update(unknown_flag=None))

    def test_protected_absent_identity_cannot_be_created_as_null_even_if_writable(self):
        self.config['local_integration']['points']['a']['writable'].append('acceptance_receipt')
        self.reopen()
        self.refused(lambda item:item.update(acceptance_receipt=None))

    def test_nested_protected_absence_is_conserved_under_selected_parent(self):
        self.config['local_integration']['points']['a']['writable'].append('unknown')
        self.reopen()
        self.refused(lambda item:item['unknown'].update(owner=None))

    def test_another_protected_value_view_retains_absence(self):
        point = copy.deepcopy(self.config['local_integration']['points']['a'])
        point['bindings'][0]['path'].append('optional')
        point.update(protected=['$value'], writable=[])
        self.config['local_integration']['points']['optional-view'] = point
        self.config['local_integration']['points']['a']['writable'].append('optional')
        self.reopen()
        self.refused(lambda item:item.update(optional=None), 'overlapping admitted view')

    def test_permitted_null_and_proposal_keep_seven_consumers(self):
        self.config['local_integration']['points']['a']['writable'] += ['optional', 'extension']
        self.reopen()
        pair = self.prepare()
        self.assertTrue(self.finish(*pair, mutate=lambda d:d['items'][0].update(
            optional=None, extension={'owner':None, 'proposed_owner':'candidate'})))
        item = json.loads(self.catalog.read_text())['items'][0]
        self.assertIn('optional', item); self.assertIsNone(item['optional'])
        self.assertEqual(item['owner'], 'accepted-owner')
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')), 7)

    def test_existing_unselected_null_remains_legal(self):
        data = json.loads(self.catalog.read_text()); data['items'][0]['optional'] = None
        self.catalog.write_text(encode(data))
        pair = self.prepare(); self.assertTrue(self.finish(*pair))
        self.assertIn('optional', json.loads(self.catalog.read_text())['items'][0])

    def test_protected_null_cannot_be_removed(self):
        data = json.loads(self.catalog.read_text()); data['items'][0]['acceptance_receipt'] = None
        self.catalog.write_text(encode(data))
        self.refused(lambda item:item.pop('acceptance_receipt'), 'drops unknown/history/source')

    def test_absence_and_null_produce_different_point_revisions(self):
        point = self.config['local_integration']['points']['a']
        point['bindings'][0]['path'].append('optional')
        self.reopen()
        before = self.versions('a')['a']
        data = json.loads(self.catalog.read_text()); data['items'][0]['optional'] = None
        self.catalog.write_text(encode(data))
        self.assertNotEqual(before, self.versions('a')['a'])


class OriginalFlow(unittest.TestCase):
    authority = prior436.CoordinationTests.authority
    boards = prior436.CoordinationTests.boards
    fixture_configuration = prior436.CoordinationTests.fixture_configuration
    configure = prior436.CoordinationTests.configure
    repository = prior444.NativeProtocol.repository

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix='flow457-', dir='/fixtures'))
        config = engine_config(self.directory)
        # Use unchanged production NOT NULL constraints, including enrollments
        # and review_contexts. These are fictional public profile labels only.
        config['profiles'] = ['.codex']
        config['classifier']['profile'] = '.codex'
        for task in config['tasks'].values(): task['profile'] = '.codex'
        for role in config['roles'].values(): role['profile'] = '.codex'
        self.runtime = Store(config, controller='fictional-controller', clock=lambda:1000.)
        self.addCleanup(self.runtime.close)
        self.runtime.execution_pool = SimpleNamespace(allocate=lambda:{'profile':'.codex','fictional':True})
        self.events = []
        for role in config['roles']:
            self.runtime.db.execute('INSERT INTO enrollments VALUES(?,?,?,?,?,0,NULL,NULL)',
                (role,'fictional-logical-'+role,'.codex','fictional-grant-'+role,0))
        self.key = self.authority()
        repo = self.repository()
        method = self.directory/'source-method.md'; method.write_text('Fictional original read-only observation method.\n')
        reduction = self.directory/'reduce-method.md'; reduction.write_text('Fictional four-step reduction.\n')
        source = copy.deepcopy(config['tasks']['ri'])
        source.update(phase='proposer',responses={'proposal':['ri']},templates=[str(method)],cwd=str(repo),
            effect_authority={'read_roots':[str(repo)],'write_roots':[],'operations':['read-source']})
        config['tasks']['rp'] = source
        config['tasks']['ri'].update(responses={'consolidated':['wp']},templates=[str(reduction)])
        config['tasks']['ri'].pop('execution')  # Genuine model integrator interface.
        config['tasks']['wp'].update(responses={'complete':['wp']},templates=[str(reduction)])
        for task in ('ri','wp'):
            config['tasks'][task]['effect_authority'] = {
                'read_roots':[str(self.directory)],'write_roots':[],'operations':['read-source']}
        point = {'kind':'item','line':'Main','incarnation':'fictional-original-run',
            'bindings':[{'native':'review','component':'component'}], 'resources':[], 'protected':[], 'writable':[]}
        config['local_integration'] = {'max_inflight':8,'points':{'review':point},'tasks':{
            task:{'capacity':5,'discovery_batch':4,'points':['review'],
                  'authority':'fictional independently selected reduction', 'method':str(reduction)} for task in ('ri','wp')}}
        for selected in config['local_integration']['tasks'].values():
            selected.update(new_point_prefix='native:', discovery_lines=[
                {'line':'Main','incarnation':'fictional-original-run','authority':'fictional selected native context lineage'}])
        self.configure()
        policy = {'caller':'/usr/bin/true','caller_sha256':reviews.sha(Path('/usr/bin/true').read_bytes()),
            'routes':{'.codex':'fictional-route'},'deadline':20,'method':str(method),'method_files':reviews.method_files(str(method)),
            'components':{'component':{'repository':str(repo),'origin':'https://example.invalid/fixture','paths':['source.txt'],
                'history':str(self.runtime.home/'review-history'/'component.md'),'authority':'fictional original read scope'}}}
        old = self.runtime.processing.current()[1]
        processing.revoke(self.runtime,self.selected_boards,self.key)
        old['basis'] = processing.basis(self.runtime,self.selected_boards)
        old.pop('expires'); old.pop('max_starts')
        old['service'] = {'max_inflight':8,'reviews':{'rp':policy},'legacy_resources':{}}
        self.key = processing.select(self.runtime,self.selected_boards,old)['capability']
        self.runtime.processing = processing.Access(self.runtime,self.key,self.selected_boards)
        self.runtime.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)',
            ('component',self.key,'.codex','fictional-route','fictional-handle','fictional-original-run',
             self.runtime.controller,'live','fictional-head','fictional-history',1000.))
        self.repo = repo

    def classify(self, event, task):
        attempt, view = self.runtime.claim_classification()
        self.assertEqual(view['id'], event['id'])
        self.runtime.collect(attempt,{'exit':0,'capture':'complete','cleanup':'fictional-no-session',
            'result':{'event_id':event['id'],'task':task,'package':view.get('package'),'reason':'fictional route meaning'}})
        self.runtime.commit_classification(attempt)

    def source(self, name='original', package='package'):
        event = {'id':name,'role':'Reviews','recipient':'fictional-logical-Reviews','kind':'board','post':11,
            'author':'fictional-author','body':{'review':{'component':'component'}},'package':package,'allowed_tasks':['rp']}
        self.runtime.ingest(event); self.classify(event,'rp')
        return event

    def start(self, event, task):
        self.classify(event,task)
        job = self.runtime.reserve(); self.assertIsNotNone(job)
        attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
        self.selected_boards[job['role']].bind_software_attempt(self.runtime,job,attempt,
            self.runtime.one('SELECT * FROM admissions WHERE package=?',(job['package'],)))
        local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks'][task])
        return job,attempt

    def finish(self, job, attempt, answer):
        if job['task'] == 'rp':
            # Explicit fixture admission of a new relationship, separate from
            # the read-only Source report. Absence no longer selects discovery.
            answer['integration'] = {'new_work':'fictional independently admitted new native relationship'}
        if job['task'] in ('ri','wp'):
            answer['completion'] = {'integration_steps':[{'step':s,'evidence':'fictional attributed '+s} for s in local.STEPS]}
        if job['task'] == 'ri' and self.native_discovery:
            # Ordinary Source reports first reach sole semantic consolidation.
            # Its explicitly selected discovery emits the original native point,
            # and Work receives the service-created anchored continuation.
            answer['completion']['discovered_points'] = {'native:original':copy.deepcopy(
                self.runtime.config['local_integration']['points']['review'])}
        elif job['task'] == 'ri':
            # A factual consolidated report can also carry normalized metadata
            # for a separately selected Work reader, without native discovery.
            answer['integration'] = {'reads':['review'],'writes':[],
                'versions':{'review':local.version(self.runtime,'review',{})}}
        self.runtime.begin(attempt,{'fictional':True})
        self.runtime.collect(attempt,{'exit':0,'capture':'complete','cleanup':'fictional-no-session','result':answer,
            'detail':{'tool_completion':{'complete':True,'items':[],'nonzero_completions':[]}}})
        return self.runtime.event(self.runtime.finish_job(job['id'],job['token']))

    def graph(self, multiple=False, discovery=True):
        self.native_discovery = discovery
        # Owner admission is original, not a synthetic Work execution scope.
        self.runtime.admit('package','fictional-logical-Branch',{'task_scopes':{}})
        self.source()
        if multiple: self.source('second-original')
        proposals = []
        for _ in range(2 if multiple else 1):
            job = self.runtime.reserve(); self.assertIsNotNone(job)
            attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
            self.selected_boards['Reviews'].bind_software_attempt(self.runtime,job,attempt,
                self.runtime.one('SELECT * FROM admissions WHERE package=?',(job['package'],)))
            answer = reviews.proposal_result({'semantic':'DONE','summary':'fictional full Source report'},
                'component',{'original':'fictional pinned material'},self.runtime.controller,attempt,[{'fictional':'turn'}])
            proposals.append(self.finish(job,attempt,answer))
        for proposal in sorted(proposals,key=lambda p:p['id']): self.classify(proposal,'ri')
        job = self.runtime.reserve(); self.assertIsNotNone(job)
        attempt = self.runtime.start_job(job['id'],job['token']); job = self.runtime.job(job['id'])
        self.selected_boards['Reviews'].bind_software_attempt(self.runtime,job,attempt,
            self.runtime.one('SELECT * FROM admissions WHERE package=?',(job['package'],)))
        local.prepare_input_basis(self.runtime,job,attempt,self.runtime.config['tasks']['ri'])
        returned = self.finish(job,attempt,result(category='consolidated'))
        return returned,proposals,job

    def test_real_proposal_integrator_Work_and_later_Work_context(self):
        returned,proposals,integrator = self.graph(multiple=True)
        self.assertEqual(len(json.loads(integrator['members'])),2)
        self.assertEqual(returned['source_job'],integrator['id'])
        self.assertFalse(self.runtime.processing.review_task('ri'))
        for _ in range(2):
            job,attempt = self.start(returned,'wp')
            self.assertEqual(local.context(self.runtime,job)['basis']['scope']['writes'],['native:original'])
            snapshot,resources = local_native.snapshot(self.runtime,{'native':'review','component':'component'},job)
            self.assertEqual(snapshot['context']['run'],'fictional-original-run')
            self.assertEqual(snapshot['context']['profile'],'.codex')
            self.assertIn('native-session:fictional-original-run',resources)
            self.assertEqual(len(local_native.original_review_jobs(self.runtime,job,set())),2)
            returned = self.finish(job,attempt,result())
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'),[])
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?',('original',))['processed_at'])

    def test_report_only_integrator_still_reaches_selected_Work_native_reader(self):
        returned,proposals,integrator = self.graph(discovery=False)
        self.assertEqual(proposals[0]['body']['category'],'proposal')
        self.assertNotIn('completion',proposals[0]['body'])
        self.assertEqual(returned['body']['category'],'consolidated')
        for _ in range(2):
            job,attempt = self.start(returned,'wp')
            basis = local.context(self.runtime,job)['basis']
            self.assertEqual(basis['scope']['reads'],['review'])
            self.assertEqual(basis['scope']['writes'],[])
            self.assertEqual(len(local_native.original_review_jobs(self.runtime,job,set())),1)
            returned = self.finish(job,attempt,result())

    def refused_graph(self, corrupt, pattern='original|coordination|revoked|currentness|collector|component'):
        returned,proposals,integrator = self.graph(multiple=True)
        job,attempt = self.start(returned,'wp')
        corrupt(job,proposals,integrator)
        with no_native_material(self.runtime), self.assertRaisesRegex(Refusal,pattern):
            local_native.snapshot(self.runtime,{'native':'review','component':'component'},job)
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'),[])

    def test_held_second_original_refuses_before_native_acquisition(self):
        self.refused_graph(lambda *args:self.runtime.db.execute("UPDATE events SET hold='fictional hold' WHERE id='second-original'"))

    def test_uncollected_original_refuses_before_native_acquisition(self):
        def corrupt(job,proposals,integrator):
            self.runtime.db.execute('UPDATE attempts SET collected=NULL WHERE id=?',(proposals[1]['source_attempt'],))
        self.refused_graph(corrupt)

    def test_changed_original_hash_refuses_before_native_acquisition(self):
        def corrupt(*args):
            row = self.runtime.event('second-original'); row['body']['review']['component']='foreign'
            self.runtime.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',(encode(row),digest(row),row['id']))
        self.refused_graph(corrupt)

    def test_missing_original_source_job_refuses_before_native_acquisition(self):
        def corrupt(job,proposals,integrator):
            self.runtime.db.execute('DELETE FROM jobs WHERE id=?',(proposals[1]['source_job'],))
        self.refused_graph(corrupt, 'job reservation fence differs')

    def test_mixed_package_original_refuses_before_native_acquisition(self):
        self.refused_graph(lambda job,p,i:self.runtime.db.execute('UPDATE jobs SET package=? WHERE id=?',('unrelated',p[1]['source_job'])))

    def test_revoked_current_coordination_refuses_before_native_acquisition(self):
        self.refused_graph(lambda *args:processing.revoke(self.runtime,self.selected_boards,self.key))

    def test_unrelated_component_refuses_before_native_acquisition(self):
        returned,_,_ = self.graph(); job,_ = self.start(returned,'wp')
        with no_native_material(self.runtime), self.assertRaisesRegex(Refusal,'component/material'):
            local_native.snapshot(self.runtime,{'native':'review','component':'unrelated'},job)

    def test_changed_original_collector_refuses_before_native_acquisition(self):
        self.refused_graph(lambda *args:self.runtime.db.execute("UPDATE review_contexts SET collector='foreign'"))

    def test_original_selected_method_interface_cannot_be_replaced_by_integrator(self):
        def corrupt(*args):
            row = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.key,))
            selection = json.loads(row['selection'])
            selection['service']['reviews'] = {}
            self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',(encode(selection),self.key))
        self.refused_graph(corrupt, 'selected original review interface')

    def branch_operand(self, fallback=True, forbidden=False):
        # Genuine original admission fallback for a locally selected Reviews
        # proposer; trusted index can refer to an inaccessible fictional path.
        config = self.runtime.config
        selected = copy.deepcopy(config['local_integration']['tasks']['ri'])
        config['local_integration']['tasks']['rp'] = selected
        config['tasks']['rp']['templates'] = [selected['method']]
        self.fixture_configuration()
        key = 'fictional-branch'
        device,inode = branches.repository_identity(self.repo)
        self.runtime.db.execute('INSERT INTO branch_associations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (key,'/forbidden-native-repo' if forbidden else str(self.repo),device,inode,
             'https://example.invalid/fixture','refs/heads/fixture','life','package','fictional-root',
             'fictional actual authority','active','fictional acceptance',1000.,None,'[]'))
        self.runtime.admit('package','fictional-logical-Branch',{'task_scopes':{'rp':{'branch_binding':key}}})
        event = {'id':'branch-input','role':'Reviews','recipient':'fictional-logical-Reviews','kind':'board','post':11,
            'body':{'review':{'component':'component'}},'package':'package','allowed_tasks':['rp']}
        if not fallback: event['branch_binding'] = key
        self.runtime.ingest(event)
        row = {'task':'rp','role':'Reviews','phase':'proposer','package':'package',
            'members':json.dumps([{'event':event['id'],'hash':digest(event),'package':'package'}])}
        return row,key

    def test_admission_fallback_wrong_component_refuses_before_physical_Git(self):
        row,_ = self.branch_operand(forbidden=True)
        with no_native_material(self.runtime), self.assertRaisesRegex(Refusal,'read authority'):
            local_native.authorize_scope(self.runtime,row,{'native':'review','component':'wrong-key'})

    def test_direct_branch_wrong_component_still_refuses_before_physical_Git(self):
        row,_ = self.branch_operand(fallback=False,forbidden=True)
        with no_native_material(self.runtime), self.assertRaisesRegex(Refusal,'read authority'):
            local_native.authorize_scope(self.runtime,row,{'native':'review','component':'wrong-key'})

    def permitted_branch(self, fallback):
        row,key = self.branch_operand(fallback=fallback)
        component = branches.review_key(self.runtime,row,{'component':'component'})
        self.runtime.db.execute('UPDATE review_contexts SET component=?',(component,))
        local_native.authorize_scope(self.runtime,row,{'native':'review','component':component})
        self.assertEqual(branches.job_branch(self.runtime,row)['id'],key)
        self.assertTrue(component.startswith('branch:'))

    def test_authorized_fallback_retains_actual_branch_key(self):
        self.permitted_branch(True)

    def test_authorized_direct_retains_actual_branch_key(self):
        self.permitted_branch(False)


if __name__ == '__main__':
    unittest.main()
