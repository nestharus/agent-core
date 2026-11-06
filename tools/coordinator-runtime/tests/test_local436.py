"""Fictional local integration controls; no provider or live data is available.

Authority/collection is supplied by fixture actors. Real config validation,
classification, reservations, read-set checks, custody and file publication run.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event, queued, collect, result
from coordinator_runtime import local_integration as local, routine, publication, bounded_log
from coordinator_runtime.contracts import Refusal, encode, validate_config


class Board:
    def completion_authority(self, store, task):
        return {'id': 'fictional-completion', 'owner': store.config['roles']['Work']['owner'],
                'issued_by': store.config['roles']['Work']['owner'], 'authority': 'fictional seven-duty policy'}


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='local436-', dir='/fixtures'))
        self.config = config_at(self.area)
        self.catalog = self.area/'catalog.json'
        self.catalog.write_text(encode({'items': [{'id': 'a', 'epoch': 'one', 'state': 'old', 'owner': 'accepted-owner', 'unknown': {'retain': 1}},
                                                  {'id': 'b', 'epoch': 'one', 'state': 'old', 'owner': 'another-owner'}],
                                     'relations': [], 'unknown-peer': ['keep']}))
        self.peers = [self.catalog, self.area/'assignments.md', self.area/'register.json', self.area/'now.json', self.area/'now.md', self.area/'root.md']
        for p in self.peers[1:]:
            p.write_text('{}\n' if p.suffix == '.json' else 'Peer historical text\n')
        self.log = self.area/'WORK_LOG.md'; self.log.write_text('old log\n'*20)
        task = self.config['tasks']['work-integrator']
        task.update(effects='owner-reconcile', sandbox='workspace-write', routine_completion={'kind': bounded_log.KIND,
            'targets': [str(p) for p in self.peers]+[str(self.log)],
            'bounded_log': {'target': str(self.log), 'max_lines': 12, 'max_bytes': 8192, 'max_entry_bytes': 16384}})
        task['effect_authority'].update(operations=['read-reports','write-role-records'], write_roots=[str(p) for p in self.peers]+[str(self.log)])
        task['responses']['complete']=['work-proposer']
        points = {k: {'kind':'item', 'line':'Main', 'incarnation':'one',
                      'bindings':[{'target':str(self.catalog), 'path':['items', {'field':'id','value':k}]}],
                      'resources':[], 'protected':['id','epoch','owner','acceptance_receipt'], 'writable':['state']} for k in ('a','b')}
        points['relations'] = {'kind':'relation', 'line':'Main', 'incarnation':'one',
                     'bindings':[{'target':str(self.catalog), 'path':['relations']}], 'resources':[], 'protected':[], 'writable':[]}
        tasks = {name: {'capacity':5,'discovery_batch':4,'points':list(points),
                        'authority':'fictional current issuer delegates routine choices for these exact points',
                        'method':value['templates'][0], 'new_point_prefix':'new:', 'ownership_fields':['owner','acceptance_receipt']} for name,value in self.config['tasks'].items()}
        self.config['local_integration'] = {'tasks':tasks,'points':points,'max_inflight':20}
        validate_config(self.config)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.board = Board()
        self.n = 0

    def versions(self, *keys):
        return {k:local.version(self.store,k,{str(self.catalog):self.catalog.read_bytes()}) for k in keys}

    def enqueue(self, key='a', *, reads=(), role='Work', task=None, package=None, discovery=False):
        self.n += 1
        task = task or (role.lower()+'-integrator' if role != 'QA' else 'qa-cleanup')
        source = event(self.config, str(self.n), role, task, package)
        if not discovery:
            keys = set(reads)|{key}
            source['integration'] = {'reads':list(reads),'writes':[key], 'versions':self.versions(*keys)}
        queued(self.store, source)
        return source

    def prepare(self, source=None):
        source = source or self.enqueue()
        job = self.store.reserve(); self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'], job['token'])
        (self.store.home/'artifacts'/attempt).mkdir(mode=0o700, parents=True)
        job = self.store.job(job['id'])
        routine.prepare(self.store,self.board,job,attempt,self.config['tasks'][job['task']])
        return job, attempt

    def finish(self, job, attempt, key='a', state='updated', *, steps=True, mutate=None, completion_extra=None):
        mapping = publication.stages(self.store,attempt)
        path = Path(mapping[str(self.catalog)])
        data = json.loads(path.read_text())
        if mutate: mutate(data)
        else: next(v for v in data['items'] if v['id']==key)['state']=state
        path.write_text(encode(data)+'\n')
        Path(mapping[str(self.peers[1])]).write_bytes(('Supplement '+key+'\n').encode()+self.peers[1].read_bytes())
        Path(mapping[str(self.log)]).write_text('New entry '+key+'\n')
        publication.conserve_stages(self.store,attempt,self.config['tasks'][job['task']])
        answer = result(); answer.update(handoffs=[], no_handoff_reason='fictional no other effects')
        answer['completion']={'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[]}
        if steps: answer['completion']['integration_steps']=[{'step':s,'evidence':'fictional selected method account '+s} for s in local.STEPS]
        answer['completion'].update(completion_extra or {})
        collect(self.store,attempt,answer,tool_completion={'complete':True, 'items':[{'id':'fictional-command','exit_code':0,'status':'completed'}]})
        return routine.reconcile(self.store,self.board,self.store.job(job['id']))

    def test_disjoint_same_file_seven_duties_keep_peers_and_unknowns(self):
        first = self.prepare()
        second = self.prepare(self.enqueue('b'))
        self.assertTrue(self.finish(*first))
        self.assertTrue(self.finish(*second,key='b'))
        body=json.loads(self.catalog.read_text())
        self.assertEqual([v['state'] for v in body['items']],['updated','updated'])
        self.assertEqual(body['items'][0]['unknown'],{'retain':1})
        self.assertEqual(body['unknown-peer'],['keep'])
        self.assertIn('Supplement a',self.peers[1].read_text());self.assertIn('Supplement b',self.peers[1].read_text())
        self.assertTrue(self.log.read_text().startswith('New entry b\nNew entry a\n'))
        for job,attempt in (first,second):
            rows=self.store.rows('SELECT * FROM file_publications WHERE attempt=?',(attempt,))
            self.assertEqual(len(rows),7);self.assertTrue(all(r['state']=='published' for r in rows))
            self.assertEqual(self.store.one('SELECT state FROM local_commits WHERE attempt=?',(attempt,))['state'],'published')
        self.assertFalse(routine.reconcile(self.store,self.board,self.store.job(second[0]['id'])))

    def test_same_point_stays_queued_but_independent_point_runs(self):
        first=self.prepare()
        waiting=self.enqueue('a');self.enqueue('b')
        other=self.store.reserve();self.assertIsNotNone(other)
        self.assertEqual(local.scope_for(self.store,other)['writes'],['b'])
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?',(waiting['id'],))['state'],'queued')
        self.assertIsNone(self.store.reserve())

    def test_meaningful_overlap_is_a_pair_not_whole_role_batch(self):
        one=self.enqueue();two=self.enqueue();third=self.enqueue();self.enqueue('b')
        job=self.store.reserve()
        self.assertEqual(len(json.loads(job['members'])),2)
        self.assertEqual(local.scope_for(self.store,job)['mode'],'reconcile')
        other=self.store.reserve();self.assertEqual(local.scope_for(self.store,other)['writes'],['b'])
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?',(third['id'],))['state'],'queued')

    def test_relation_absence_becomes_stale_without_global_invalidation(self):
        job,attempt=self.prepare(self.enqueue(reads=['relations']))
        data=json.loads(self.catalog.read_text());data['relations'].append({'id':'new-blocker'});self.catalog.write_text(encode(data))
        with self.assertRaisesRegex(Refusal,'read-set is stale'):self.finish(job,attempt)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        self.assertIsNotNone(self.store.one('SELECT basis FROM local_bases'))

    def test_unrelated_point_change_rebases_but_target_recreation_refuses(self):
        job,attempt=self.prepare()
        data=json.loads(self.catalog.read_text());data['items'][0]['epoch']='recreated';self.catalog.write_text(encode(data))
        with self.assertRaisesRegex(Refusal,'read-set is stale'):self.finish(job,attempt)

    def test_stale_arrival_requires_selected_four_step_return(self):
        source=self.enqueue()
        data=json.loads(self.catalog.read_text());data['items'][0]['state']='peer update';self.catalog.write_text(encode(data))
        job,attempt=self.prepare(source)
        context=local.context(self.store,job)
        self.assertEqual(context['basis']['scope']['mode'],'reconcile')
        with self.assertRaisesRegex(Refusal,'all four'):self.finish(job,attempt,steps=False)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_unknown_work_uses_separate_discovery_lane_without_blocking_anchored(self):
        self.enqueue(discovery=True);self.enqueue(discovery=True);self.enqueue()
        discovery=self.store.reserve();anchored=self.store.reserve()
        self.assertEqual(local.scope_for(self.store,discovery)['lane'],'discovery')
        self.assertEqual(len(json.loads(discovery['members'])),2)
        self.assertEqual(local.scope_for(self.store,anchored)['lane'],'anchored')
        context=local.context(self.store,discovery)
        self.assertIn('a',context['discovery_points'])

    def test_resource_and_cross_role_point_exclusion(self):
        self.prepare()
        self.enqueue(role='Reviews')
        self.assertIsNone(self.store.reserve())
        self.enqueue('b',role='Branch')
        self.assertEqual(self.store.reserve()['role'],'Branch')

    def test_owned_fields_and_out_of_scope_changes_refuse(self):
        job,attempt=self.prepare()
        with self.assertRaisesRegex(Refusal,'ownership/identity'):
            self.finish(job,attempt,mutate=lambda d:d['items'][0].update(owner='invented-transfer'))
        self.assertEqual(json.loads(self.catalog.read_text())['items'][0]['owner'],'accepted-owner')

    def test_partial_publication_keeps_intent_no_replay_and_no_clock(self):
        job,attempt=self.prepare()
        write=publication.write_same_inode
        count=0
        def interrupted(fd,body):
            nonlocal count
            count+=1
            write(fd,body)
            if count==2:raise OSError('fictional interruption after possible effect')
        with patch.object(publication,'write_same_inode',side_effect=interrupted):
            with self.assertRaisesRegex(OSError,'interruption'):self.finish(job,attempt)
        self.assertEqual(self.store.one('SELECT state FROM local_commits')['state'],'intent')
        self.assertTrue(self.store.rows("SELECT * FROM file_publications WHERE state='intent'"))
        with self.assertRaisesRegex(Refusal,'never replay'):
            routine.reconcile(self.store,self.board,self.store.job(job['id']))
        self.assertTrue(all(r['processed_at'] is None for r in self.store.rows('SELECT processed_at FROM events WHERE parent IS NULL')))

    def test_no_row_indices_or_other_line_authority(self):
        bad=copy.deepcopy(self.config);bad['local_integration']['points']['a']['bindings'][0]['path']=['items',0]
        with self.assertRaisesRegex(Refusal,'indices'):validate_config(bad)
        bad=copy.deepcopy(self.config);bad['local_integration']['points']['a']['bindings'][0]['target']='/unselected/cloud.json'
        with self.assertRaisesRegex(Refusal,'access policy'):validate_config(bad)


    def test_qa_execution_ceiling_and_independent_cleanup_without_role_barrier(self):
        # Explicit per-package scopes and separate points. The ceiling is five
        # actual QA executions; unrelated cleanup can progress simultaneously.
        for i in range(7):
            key='q'+str(i)
            self.config['local_integration']['points'][key]=copy.deepcopy(self.config['local_integration']['points']['a'])
            self.config['local_integration']['points'][key]['bindings'][0]['path']=['qa'+str(i)]
            for value in self.config['local_integration']['tasks'].values():value['points'].append(key)
        data=json.loads(self.catalog.read_text())
        for i in range(7):data['qa'+str(i)]={'id':'q'+str(i),'state':'ready'}
        self.catalog.write_text(encode(data))
        # The test controls were configured before any source/job allocation.
        # Rebind an empty owned fixture, never an operating/historical journal.
        self.store.close()
        self.config['state_dir']=str(self.area/'qa-state')
        self.store=enrolled(self.config);self.addCleanup(self.store.close)
        for i in range(6):
            package='fictional-package-'+str(i)
            self.store.admit(package,self.config['roles']['Branch']['owner'],{'task_scopes':{},'evidence':'fictional isolated package'})
            self.enqueue('q'+str(i),role='QA',task='qa-execution',package=package)
        jobs=[self.store.reserve() for _ in range(5)]
        self.assertTrue(all(j and j['phase']=='execution' for j in jobs))
        self.assertIsNone(self.store.reserve())
        self.store.admit('fictional-cleanup',self.config['roles']['Branch']['owner'],{'task_scopes':{},'evidence':'fictional separate cleanup'})
        self.enqueue('q6',role='QA',task='qa-cleanup',package='fictional-cleanup')
        cleanup=self.store.reserve();self.assertEqual(cleanup['phase'],'cleanup')
        self.enqueue('b',role='QA',task='qa-cleanup',package='fictional-package-0')
        self.assertIsNone(self.store.reserve())

    def test_actual_resource_lease_and_running_source_revision_are_retained(self):
        point=self.config['local_integration']['points']['a']
        point['resources']=['fictional-owner-session']
        self.store.close(); self.config['state_dir']=str(self.area/'resource-state')
        self.store=enrolled(self.config); self.addCleanup(self.store.close)
        self.enqueue()
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)',('fictional-owner-session','fictional-other-original'))
        self.assertIsNone(self.store.reserve())
        self.store.db.execute('DELETE FROM ordinary_resources WHERE resource=?',('fictional-owner-session',))
        job=self.store.reserve();self.assertIsNotNone(job)
        original=job['members']
        self.enqueue()
        self.assertEqual(self.store.job(job['id'])['members'],original)
        self.assertIsNone(self.store.reserve())


    def test_central_discovery_emits_stable_anchored_continuation_with_custody(self):
        source=self.enqueue(discovery=True)
        job,attempt=self.prepare(source)
        definition=copy.deepcopy(self.config['local_integration']['points']['a'])
        definition['bindings'][0]['path']=['items',{'field':'id','value':'d'}]
        self.assertTrue(self.finish(job,attempt,mutate=lambda d:d['items'].append({'id':'d','epoch':'one','state':'new','owner':None,'proposed_owner':'fictional-proposal'}),
                                   completion_extra={'discovered_points':{'new:d':definition}}))
        answer=json.loads(self.store.attempt(attempt)['result'])
        with self.store.tx():
            returned=self.store._response(self.store.job(job['id']),self.store.attempt(attempt),self.config['tasks'][job['task']],answer)
        output=self.store.event(returned)
        self.assertEqual(output['package'],source['package'])
        self.assertEqual(output['source_members'],json.loads(job['members']))
        self.assertEqual(output['integration']['writes'],['new:d'])
        self.assertEqual(output['integration']['versions'],self.versions('new:d'))
        queued(self.store,output)
        next_job=self.store.reserve()
        self.assertEqual(local.scope_for(self.store,next_job)['lane'],'anchored')
        from coordinator_runtime.cleanup import eligible_event
        self.assertFalse(eligible_event(self.store,self.store.one('SELECT * FROM events WHERE id=?',(source['id'],))))

    def test_discovery_cannot_invent_accepted_ownership(self):
        job,attempt=self.prepare(self.enqueue(discovery=True))
        with self.assertRaisesRegex(Refusal,'manufacture acceptance'):
            self.finish(job,attempt,mutate=lambda d:d['items'].append({'id':'d','owner':'invented-owner'}))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_published_receipts_rejoin_after_lost_return_without_replay(self):
        job,attempt=self.prepare()
        with patch.object(routine, 'reconcile', wraps=routine.reconcile):
            self.assertTrue(self.finish(job,attempt))
        # Controlled loss of the consumer receipt, not of publication knowledge.
        self.store.db.execute("UPDATE jobs SET effects='unknown',effect_receipt=NULL WHERE id=?",(job['id'],))
        data=json.loads(self.catalog.read_text());data['items'][1]['state']='later-peer';self.catalog.write_text(encode(data))
        with patch.object(publication,'write_same_inode',side_effect=AssertionError('must not replay')):
            self.assertTrue(routine.reconcile(self.store,self.board,self.store.job(job['id'])))
        self.assertEqual(json.loads(self.catalog.read_text())['items'][1]['state'],'later-peer')


    def test_unique_oversize_result_is_refused_with_exact_recovery_custody(self):
        job,attempt=self.prepare()
        answer=result(summary='fictional unique material '+('z'*70000))
        collect(self.store,attempt,answer)
        row=self.store.attempt(attempt)
        self.assertIsNone(row['result']);self.assertEqual(row['capture'],'incomplete')
        recovery=json.loads(row['detail'])['oversize_result']
        self.assertEqual(json.loads(Path(recovery['path']).read_text()),answer)
        self.assertEqual(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(recovery['sha256'],))['body'],encode(answer).encode())
        self.assertEqual(recovery['collector'],self.store.controller)
        self.assertFalse(routine.reconcile(self.store,self.board,self.store.job(job['id'])))

    def test_local_path_does_not_acquire_all_historical_debt(self):
        with patch.object(self.store,'integration_debt',side_effect=AssertionError('unrelated historical acquisition')):
            job,attempt=self.prepare()
            from coordinator_runtime.dispatcher import job_prompt
            prompt=job_prompt(self.store,job)
            self.assertIn('local_integration',prompt)
            self.assertIn('"conserved_integration_debt":[]',prompt)

    def test_malformed_point_packet_retains_error_and_unrelated_work_progresses(self):
        source=event(self.config,'malformed')
        source['integration']={'reads':[],'writes':['unknown-unresolved'],'versions':{'unknown-unresolved':'unknown'}}
        queued(self.store,source)
        self.enqueue('b')
        job=self.store.reserve();self.assertEqual(local.scope_for(self.store,job)['writes'],['b'])
        self.assertIsNotNone(self.store.one('SELECT subject FROM operational_errors WHERE subject=?',(source['id'],)))

    def test_retirement_clock_starts_only_at_whole_processing_and_all_holds(self):
        from coordinator_runtime.cleanup import eligible_event, RETENTION
        source=self.enqueue(task='work-proposer')
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token'])
        collect(self.store,attempt,result())
        old=self.store.one('SELECT * FROM events WHERE id=?',(source['id'],))
        self.assertIsNone(old['processed_at']);self.assertFalse(eligible_event(self.store,old))
        self.store.finish_job(job['id'],job['token'])
        row=self.store.one('SELECT * FROM events WHERE id=?',(source['id'],))
        self.assertIsNotNone(row['processed_at']);self.assertFalse(eligible_event(self.store,row))
        self.store.clock=lambda:row['processed_at']+RETENTION+1
        self.assertTrue(eligible_event(self.store,row))
        self.store.db.execute("UPDATE events SET hold='fictional consumer/effect hold' WHERE id=?",(source['id'],))
        self.assertFalse(eligible_event(self.store,self.store.one('SELECT * FROM events WHERE id=?',(source['id'],))))


    def test_report_revision_and_later_update_become_a_reviewed_continuation(self):
        source=self.enqueue(role='Reviews')
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token'])
        local.prepare_input_basis(self.store,job,attempt,self.config['tasks'][job['task']])
        frozen=json.loads(self.store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))['basis'])
        data=json.loads(self.catalog.read_text());data['items'][0]['state']='later correction';self.catalog.write_text(encode(data))
        answer=result(category='consolidated',summary='fictional review of the recorded original revision only')
        collect(self.store,attempt,answer)
        response=self.store.finish_job(job['id'],job['token'])
        returned=self.store.event(response)
        self.assertEqual(returned['integration']['versions'],frozen['versions'])
        self.assertEqual(returned['source_attempt'],attempt)
        self.assertEqual(returned['body'],answer)
        queued(self.store,returned)
        next_job=self.store.reserve();next_attempt=self.store.start_job(next_job['id'],next_job['token'])
        local.prepare_input_basis(self.store,next_job,next_attempt,self.config['tasks'][next_job['task']])
        self.assertEqual(local.context(self.store,self.store.job(next_job['id']))['basis']['scope']['mode'],'reconcile')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])

    def test_unknown_field_modification_cannot_hide_in_a_point_delta(self):
        job,attempt=self.prepare()
        with self.assertRaisesRegex(Refusal,'unselected/unknown'):
            self.finish(job,attempt,mutate=lambda d:d['items'][0]['unknown'].update(retain=999))
        self.assertEqual(json.loads(self.catalog.read_text())['items'][0]['unknown']['retain'],1)


    def test_discovery_cannot_hide_custom_owner_acceptance_in_new_fields(self):
        job,attempt=self.prepare(self.enqueue(discovery=True))
        with self.assertRaisesRegex(Refusal,'manufacture acceptance'):
            self.finish(job,attempt,mutate=lambda d:d['items'].append({'id':'d','owner':None,'acceptance_receipt':'invented receipt'}))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_prospective_scope_option_preserves_task_effects_and_canonical_membership(self):
        from coordinator_runtime.configuration import apply_scope_options
        original=copy.deepcopy(self.config); del original['local_integration']
        candidate=copy.deepcopy(original)
        apply_scope_options(original,candidate,{'local_integration':self.config['local_integration']})
        validate_config(candidate)
        self.assertEqual(candidate['tasks'],original['tasks'])
        self.assertEqual(candidate['roles'],original['roles'])
        self.assertEqual(candidate['profiles'],original['profiles'])


    def test_central_lane_compares_cross_package_candidates_without_reparenting(self):
        first=self.enqueue(package='fictional-main-package',discovery=True)
        second=self.enqueue(package='fictional-cloud-package',discovery=True)
        self.enqueue(role='Branch',package='fictional-branch-package',discovery=True)
        self.enqueue('a')
        discovery=self.store.reserve()
        scope=local.scope_for(self.store,discovery)
        self.assertEqual(discovery['package'],first['package'])
        self.assertEqual(scope['sources'],[first['id']])
        self.assertEqual([m['event'] for m in scope['neighbors']],[second['id']])
        context=local.context(self.store,discovery)
        self.assertEqual(context['discovery_neighbors'][0]['package'],second['package'])
        # A global central discovery slot never blocks an anchored integration.
        anchored=self.store.reserve();self.assertEqual(local.scope_for(self.store,anchored)['lane'],'anchored')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?',(second['id'],))['state'],'queued')


# The existing NULL-native protocol fixture owns a real disposable Board SQLite
# substrate. Its actor authentication is an explicit seam; selection, automatic
# admission, source construction, classification and reservation are production.
import test_processing206 as protocol
from coordinator_runtime import processing, processing_admission
from coordinator_runtime.contracts import digest


class CoordinationTests(unittest.TestCase):
    setUp=protocol.ProtocolTests.setUp
    tearDown=protocol.ProtocolTests.tearDown
    authority=protocol.ProtocolTests.authority
    event=protocol.ProtocolTests.event
    receipt=protocol.ProtocolTests.receipt
    classify=protocol.ProtocolTests.classify
    fixture_configuration=protocol.ProtocolTests.fixture_configuration
    boards=protocol.ProtocolTests.boards
    fresh=protocol.ProtocolTests.fresh

    def configure(self, coordination=True):
        self.runtime.config['delivery']['recipients']={'Work':{'session':'fictional-logical-Work'}}
        for name in ('bi','qe'):
            self.runtime.config['tasks'][name].update(require_package_scope=True,scope_roots=['/fixtures'],
                effect_authority={'read_roots':['/fixtures'],'write_roots':[],'operations':['read-source']},
                responses={'scope':['wp']}, allowed_handoffs=['Work'], software_handoffs={'Work':['wp']})
        boards,conn=self.boards()
        self.conn=conn; self.selected_boards=boards
        conn.execute('ALTER TABLE coordinator_deliveries_v1 ADD COLUMN kind TEXT')
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1000 WHERE revoked IS NULL')
        scope={'cwd':str(self.directory),'read_roots':[str(self.directory)],'write_roots':[],
               'procedure':str(self.directory/'fictional-procedure.md'),'resource_evidence':'fictional exact resource authority'}
        self.policy={'authority':'fictional Work prospective admission','max_packages':5,
                     'scopes':{'fictional-new-work':{'submitters':['fictional-author'],'package_prefix':'fictional-new-',
                        'task_scopes':{'bi':scope,'qe':scope},'evidence':'fictional Branch/QA execution only'}}}
        selection={'basis':processing.basis(self.runtime,boards),'authority':'fictional current independent Work software authority',
                   'expires':1060.,'retained_events':[],'recover_controls':{},'future_intake':True,
                   'tasks':list(self.runtime.config['tasks']),'max_starts':100,'max_shared_rows':1000,
                   'max_shared_payload_bytes':1048576,'max_runtime_rows':100,'software_admission':self.policy}
        if coordination:
            selection['work_coordination']={'authority':'fictional separately issued Work allocation authority',
                                           'tasks':['wp'],'source_roles':['Branch','QA','Reviews']}
        self.key=processing.select(self.runtime,boards,selection)['capability']
        self.runtime.processing=processing.Access(self.runtime,self.key,boards)
        return boards

    def returned(self, role='QA', handoff=False):
        source=self.fresh('return-'+role,role)
        processing_admission.admit(self.runtime,source['id'])
        task='qe' if role=='QA' else 'bi'
        self.classify(source,task)
        job=self.runtime.reserve();self.assertIsNotNone(job)
        attempt=self.runtime.start_job(job['id'],job['token'])
        self.runtime.begin(attempt,{'fictional_collected_preparation':True})
        answer=result(category='scope',summary='fictional broader allocation concern')
        if handoff:
            answer['handoffs']=[{'kind':'work','recipient':'Work','text':'fictional bounded allocation concern','ref':'fictional-point','required':'settled'}]
        self.runtime.collect(attempt,{'exit':0,'capture':'complete','cleanup':'no-session-created','result':answer})
        # Real response constructor conserves the original execution package and
        # ALL members. No impossible Work scope is inserted into the admission.
        if handoff:
            with self.runtime.tx():
                self.runtime._task_handoff(self.runtime.job(job['id']),self.runtime.attempt(attempt),self.runtime.config['tasks'][task],answer,answer['handoffs'][0],0)
            return source,job,self.runtime.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        with self.runtime.tx():
            response=self.runtime._response(self.runtime.job(job['id']),self.runtime.attempt(attempt),self.runtime.config['tasks'][task],answer)
        return source,job,self.runtime.event(response)

    def test_valid_automatic_qa_and_branch_returns_keep_package_and_reach_work(self):
        self.configure()
        for role in ('QA','Branch'):
            source,job,returned=self.returned(role)
            self.assertEqual(returned['package'],source['package'])
            admission=json.loads(self.runtime.one('SELECT receipt FROM admissions WHERE package=?',(source['package'],))['receipt'])
            self.assertNotIn('wp',admission['task_scopes'])
            self.classify(returned,'wp')
            receiving=self.runtime.reserve();self.assertIsNotNone(receiving)
            self.assertEqual(receiving['role'],'Work');self.assertEqual(receiving['package'],source['package'])
            self.assertEqual(returned['source_members'],json.loads(job['members']))
            self.assertFalse(admission['software_admission']['native_owner_consent'])

    def test_execution_admission_alone_grants_no_work_coordination(self):
        self.configure(False)
        source,job,returned=self.returned()
        self.classify(returned,'wp')
        self.assertIsNone(self.runtime.reserve())
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])

    def test_bad_later_member_and_package_switch_cannot_borrow_coordination(self):
        self.configure()
        source,job,returned=self.returned()
        original=json.loads(job['members'])
        # A corrupt later member is not hidden by the genuine first ancestor.
        unrelated=self.event('fictional-wrong-later','QA','qe',package=source['package'],queued=False)
        members=original+[{'queue':'fictional-wrong','event':unrelated['id'],'hash':digest(unrelated),'package':source['package']}]
        self.runtime.db.execute('UPDATE jobs SET members=? WHERE id=?',(encode(members),job['id']))
        changed={**returned,'source_members':members}
        self.runtime.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',(encode(changed),digest(changed),returned['id']))
        self.assertFalse(processing_admission.permits(self.runtime,{'task':'wp','event':returned['id'],'package':source['package']}))
        self.assertFalse(processing_admission.permits(self.runtime,{'task':'wp','event':returned['id'],'package':'fictional-other-line'}))


    def test_cross_role_receiving_intent_checks_original_grants_payload_and_transport(self):
        self.configure()
        source,job,outbox=self.returned(handoff=True)
        payload=json.loads(outbox['payload'])
        delivery={'id':outbox['id'],'source_grant':'fictional-grant-QA','receiver_grant':'fictional-grant-Work',
                  'source_hash':digest(payload),'notice':1,'post':12}
        received={'id':'fictional-receiving-source','role':'Work','recipient':'fictional-logical-Work',
                  'author':None,'body':payload,'kind':'response','package':source['package'],'allowed_tasks':['wp'],
                  'source_delivery':delivery,'processing_capability':self.key,'parent':outbox['event']}
        # Actual native delivery/identity is absent. These are explicitly owned
        # fictional persisted receipts exercising production receiving checks.
        self.conn.execute('INSERT INTO coordinator_deliveries_v1 VALUES(?,?,?,?,?,?,?,?,0,?)',
                          (outbox['id'],'fictional-grant-QA',self.runtime.config['actor'],outbox['producer'],
                           'fictional-logical-Work',outbox['payload'],1,12,'work'))
        self.conn.execute("INSERT INTO notification_outbox VALUES(1,'managed','managed_pending')")
        self.conn.execute('INSERT INTO coordinator_software_deliveries_v1 VALUES(?,?,?,?,?)',
                          (outbox['id'],'fictional-grant-QA','fictional-grant-Work',received['id'],encode(received)))
        self.assertTrue(self.selected_boards['Work'].receiving_intent(self.runtime,received))
        self.runtime.ingest(received)
        self.runtime.db.execute('INSERT INTO processing_delivery_links VALUES(?,?)',(outbox['id'],received['id']))
        self.classify(received,'wp')
        consumer=self.runtime.reserve();self.assertIsNotNone(consumer)
        self.assertEqual(consumer['role'],'Work');self.assertEqual(consumer['package'],source['package'])
        self.assertEqual(payload['source_members'],json.loads(job['members']))
        self.conn.execute("UPDATE notification_outbox SET delivery_state='ambiguous'")
        with self.assertRaises(Refusal):self.selected_boards['Work'].receiving_intent(self.runtime,received)
        self.conn.execute("UPDATE notification_outbox SET delivery_state='managed_pending'")
        self.conn.execute("UPDATE coordinator_software_deliveries_v1 SET receiver_grant='fictional-wrong-grant'")
        with self.assertRaises(Refusal):self.selected_boards['Work'].receiving_intent(self.runtime,received)


if __name__=='__main__':unittest.main()
