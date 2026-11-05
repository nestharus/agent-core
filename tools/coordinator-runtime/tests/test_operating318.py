"""Owned fiction only: NULL native/provider/session/turn; no live owner receipt.

315's supplied counterexamples and Work's actual outcomes are the oracles.
Public source is RO; real SQLite, kernel publication and disposable Git execute.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, custody, publication, processing, resource_scopes, ref_scope
from coordinator_runtime.cleanup import register_artifact
from coordinator_runtime.contracts import Refusal, digest, encode, scoped_startup, scoped_task
from coordinator_runtime.dispatcher import job_prompt, execution_spec
from coordinator_runtime.appserver import thread_request
import test_bounded311 as bounded
import test_configuration308 as current


class LogRoutes(unittest.TestCase):
    def setUp(self):
        self.f = bounded.Catalog(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.f.prepare()
        self.s, self.task = self.f.store, self.f.task
        # Conditional fixture, not a claim about actual witness existence.
        self.body = b'FICTION conserved whole old log\n'
        self.sha = hashlib.sha256(self.body).hexdigest()
        self.s.db.execute('INSERT INTO artifact_blobs VALUES(?,?)', (self.sha, self.body))
        self.s.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                          ('fiction-old', str(self.f.log), 'role-owned', 'fiction-owner', '{}', self.sha))
        self.w = {'path':str(self.f.log), 'custody':'artifact_blobs', 'sha256':self.sha}

    def without_body(self, operation):
        original = self.s.one
        def guard(sql, *args):
            self.assertNotIn('SELECT body', sql, 'refuse before cached body acquisition')
            return original(sql, *args)
        with patch.object(self.s, 'one', side_effect=guard):
            with self.assertRaises(Refusal): operation()
        self.assertEqual(self.s.one('SELECT body FROM artifact_blobs WHERE sha256=?', (self.sha,))['body'], self.body)

    def test_member_prior_cached_and_disguised_witness_refuse_before_body(self):
        for witness in [self.w, {**self.w, 'path':str(self.s.home/'artifacts'/'fiction-cache'/self.sha)}]:
            self.without_body(lambda: custody.materialize(self.s,[{'artifact_witnesses':[witness]}],self.f.attempt,self.task))
        event = {**self.s.event(json.loads(self.f.current['members'])[0]['event']), 'artifact_witnesses':[self.w]}
        job = {**self.f.current, 'members':encode([{'event':event['id'],'hash':digest(event)}])}
        with patch.object(self.s, 'event', return_value=event):
            self.without_body(lambda: job_prompt(self.s,job,self.task))
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode({'prior_artifact_witnesses':[self.w]}),self.f.attempt))
        self.without_body(lambda: job_prompt(self.s,self.f.current,self.task))

    def test_fresh_capture_registration_and_legacy_stage_refuse(self):
        with patch.object(custody, 'read_file', side_effect=AssertionError('no body read')):
            with self.assertRaises(Refusal): custody.capture(self.s,self.f.attempt,str(self.f.log),self.task)
        with self.assertRaises(Refusal): register_artifact(self.s,self.f.attempt,self.f.log)
        stage = self.s.home/'artifacts'/self.f.attempt/'historical-stage'
        stage.write_bytes(self.body)
        self.s.db.execute('INSERT INTO routine_stages VALUES(?,?,?)', ('fiction-legacy',str(self.f.log),str(stage)))
        with patch.object(custody, 'read_file', side_effect=AssertionError('no legacy stage read')):
            with self.assertRaises(Refusal): custody.capture(self.s,self.f.attempt,str(stage),self.task)
        before={str(self.f.log):{'exists':True,'sha256':self.sha}}
        (self.s.home/'artifacts'/'fiction-legacy-new').mkdir()
        self.without_body(lambda: publication.prepare(self.s,'fiction-legacy-new',before))

    def test_legacy_preimage_origin_survives_without_artifact_custody_row(self):
        self.s.db.execute("DELETE FROM artifact_custody WHERE attempt='fiction-old'")
        self.s.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                          ('fiction-snapshot','wi','fiction-grant',encode({'kind':'file-witness'}),
                           encode({str(self.f.log):{'exists':True,'sha256':self.sha}}),'prepared'))
        disguised={**self.w,'path':str(self.s.home/'artifacts'/'fiction-cache'/self.sha)}
        self.without_body(lambda: custody.materialize(self.s,[{'artifact_witnesses':[disguised]}],self.f.attempt,self.task))

    def test_configuration_binding_never_acquires_or_rehashes_old_blobs(self):
        statements=[]
        self.s.db.set_trace_callback(statements.append)
        try: binding=configuration.journal(self.s)
        finally: self.s.db.set_trace_callback(None)
        self.assertIn('body integrity unobserved',binding['artifact_blobs']['body_observation'])
        self.assertTrue(any('SELECT sha256,length(body)' in s for s in statements))
        self.assertFalse(any('SELECT * FROM "artifact_blobs"' in s for s in statements))


class FutureScopes(unittest.TestCase):
    def setUp(self):
        self.f=current.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def test_narrow_work_retention_exclusions_neutral_startup_together(self):
        f=self.f
        f.runtime.config['tasks']['wp']['effect_authority']['operations']=['read-source','read-reports','prepare-intents']
        f.runtime.config['tasks']['wp']['templates'].append('/unmounted/AGENTS.md')
        safe=f.directory/'exact-report.md';safe.write_text('fiction useful report')
        excluded=str(f.directory/'held-never-touch')
        options={'read_roots':{'wp':[str(safe),'/src/tools/coordinator-runtime/tests/fixture_snapshot/retention.py']},
                 'neutral_startup':['wp'], 'exclusions':[excluded]}
        value=configuration.candidate(f.runtime,str(f.directory/'new.json'),['wp','bi'],scope_options=options)
        Path(value['operator_config']).write_text(encode(value))
        configuration.validate_changes(f.runtime,value,['wp','bi'])
        self.assertEqual(value['tasks']['wp']['effect_authority']['read_roots'],options['read_roots']['wp'])
        self.assertIn(excluded,value['artifact_exclusions'])
        self.assertTrue(scoped_startup(value['tasks']['wp']))
        manifest=configuration.release(f.runtime,value)
        self.assertNotIn('/unmounted/AGENTS.md',manifest['files'])
        request=thread_request(value['tasks']['wp'],value['tasks']['wp']['binding'])
        self.assertEqual(request['config']['project_doc_max_bytes'],0)
        self.assertNotIn('startup',f.original['tasks']['wp'])
        escaped=copy.deepcopy(value);escaped['artifact_exclusions']=[]
        with self.assertRaises(Refusal):configuration.validate_changes(f.runtime,escaped,['wp','bi'])
        broad=copy.deepcopy(options);broad['read_roots']['wp']=['/fixtures']
        with patch('pathlib.Path.is_symlink',side_effect=AssertionError('no broad excluded-root metadata')):
            with self.assertRaises(Refusal):configuration.candidate(f.runtime,str(f.directory/'broad.json'),[],scope_options=broad)
        unsafe=copy.deepcopy(options);unsafe['read_roots']['wp']=['/home']
        with self.assertRaises(Refusal):configuration.candidate(f.runtime,str(f.directory/'wide.json'),[],scope_options=unsafe)


class LinkedScope(unittest.TestCase):
    def setUp(self):
        self.f=bounded.RefOperations(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def test_actual_linked_topology_ceiling_is_paired_and_rechecked(self):
        f=self.f
        linked=f.area/'fiction-linked';f.command('worktree','add','--quiet','--detach',str(linked),f.old)
        common=f.repo/'.git'
        task=copy.deepcopy(f.task);task['scope_roots']=[str(linked)]
        value=copy.deepcopy(f.config);value['tasks']['bi']=task
        options={'linked_repositories':{'bi':[{'repository':str(linked),'common_git':str(common)}]}}
        configuration.apply_scope_options(f.config,value,options)
        task=value['tasks']['bi']
        scope={**f.scope,'cwd':str(linked),'read_roots':[str(linked)],'write_roots':[str(common)]}
        admission={'receipt':encode({'task_scopes':{'bi':scope}})}
        self.assertEqual(scoped_task('bi',task,admission)['effect_authority']['write_roots'],[str(common)])
        for roots in ([str(common.parent)], [str(f.area/'unassociated'/'.git')]):
            bad={'receipt':encode({'task_scopes':{'bi':{**scope,'write_roots':roots}}})}
            with self.assertRaises(Refusal):scoped_task('bi',task,bad)
        wrong=copy.deepcopy(task);wrong['linked_repositories'][0]['common_git']=str(f.area/'wrong'/'.git')
        bad={'receipt':encode({'task_scopes':{'bi':{**scope,'write_roots':[wrong['linked_repositories'][0]['common_git']]}}})}
        with self.assertRaises(Refusal):scoped_task('bi',wrong,bad)
        task['scope_exclusions']=[str(common)]
        with patch('pathlib.Path.is_symlink',side_effect=AssertionError('no excluded metadata')):
            with self.assertRaises(Refusal):scoped_task('bi',task,admission)


class OwnerPreconditions(unittest.TestCase):
    def setUp(self):
        self.f=bounded.Catalog(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.s=self.f.store

    def test_all_local_event_attempts_and_publication_intents_are_distinct_from_external_debt(self):
        self.assertFalse(any(processing.local_disposition(self.s,'Work').values()))
        # External retained scope is not a local effect or synthetic historical map.
        self.s.db.execute("UPDATE enrollments SET legacy_hold='fiction external44/17 retained' WHERE role='Work'")
        self.assertFalse(any(processing.local_disposition(self.s,'Work').values()))
        event={'id':'fiction-control','role':'Work','recipient':'fictional-logical-Work','kind':'board','post':2,
               'body':'fiction','allowed_tasks':['wi'],'package':None}
        self.s.ingest(event)
        self.s.db.execute("INSERT INTO attempts(id,kind,event,controller,profile,binding,created) VALUES('fiction-ack','ack',?,'original',NULL,'{}',900)",(event['id'],))
        self.assertEqual(processing.local_disposition(self.s,'Work')['uncollected_originals'][0]['id'],'fiction-ack')
        self.s.db.execute("UPDATE attempts SET ended=901,collected=902,exit=0 WHERE id='fiction-ack'")
        self.assertFalse(any(processing.local_disposition(self.s,'Work').values()))
        self.s.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,effects) VALUES('fiction-held-job','Work','integrator','wi','[]','original','token',900,'unknown')")
        self.s.db.execute("INSERT INTO attempts(id,kind,job,controller,profile,binding,created) VALUES('fiction-held-attempt','task','fiction-held-job','original',NULL,'{}',900)")
        self.s.db.execute("INSERT INTO file_publications VALUES('fiction-held-attempt',?,'intent',NULL,NULL,NULL,NULL)",(str(self.f.log),))
        local=processing.local_disposition(self.s,'Work')
        self.assertTrue(local['effect_jobs']);self.assertTrue(local['uncollected_originals']);self.assertTrue(local['publication_intents'])
        self.assertEqual(self.s.enrollment('Work')['legacy_hold'],'fiction external44/17 retained')


class OwnerApplication(unittest.TestCase):
    def test_existing_owner_procedure_keeps_nonempty_holds_and_refuses_ineligible_empty_clearance(self):
        f=current.CurrentConfiguration(methodName='runTest')
        self.addCleanup(f.doCleanups);f.setUp()
        s=f.runtime;role='Work';hold=s.one('SELECT legacy_hold FROM enrollments WHERE role=?',(role,))['legacy_hold']
        request={'kind':'legacy-disposition','role':role,'target':role,'prior':hold,
                 'receipt':{'collector':'fiction original collector','evidence':['fiction exact future resources; external44/17 separately conserved'],
                            'remaining_holds':['fiction undisposed prospective resource conflict']}}
        def select(req):
            value=f.processing_selection();value['owner_operations']=[req]
            return processing.select(s,f.boards,value)['capability']
        key=select(request)
        source=processing.owner_source(s,f.boards,key,role,'legacy-disposition',role)
        self.assertTrue(source['local_resource_disposition']['effect_jobs'])
        self.assertTrue(source['local_resource_disposition']['uncollected_originals'])
        result=processing.apply_owner(s,f.boards,key,request,'fictional-Work')
        self.assertFalse(result['hold_cleared']);self.assertEqual(s.one('SELECT legacy_hold FROM enrollments WHERE role=?',(role,))['legacy_hold'],hold)
        processing.revoke(s,f.boards,key)
        empty=copy.deepcopy(request);empty['receipt']['remaining_holds']=[]
        key=select(empty)
        with self.assertRaises(Refusal):processing.apply_owner(s,f.boards,key,empty,'fictional-Work')
        with self.assertRaises(Refusal):processing.apply_owner(s,f.boards,key,empty,'fiction-stranger')
        self.assertEqual(s.job('fictional-old-job')['effects'],'unknown')
        self.assertEqual(s.one('SELECT COUNT(*) AS n FROM events')['n'],4)
        self.assertEqual(s.one('SELECT COUNT(*) AS n FROM outboxes')['n'],67)
        self.assertTrue(all(r['profile'] is None and r['session'] is None and r['turn'] is None for r in s.rows('SELECT profile,session,turn FROM attempts')))
