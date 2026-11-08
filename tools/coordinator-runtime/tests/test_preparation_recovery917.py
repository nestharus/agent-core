"""Retained synthetic boards/repos; actual old public report, no live state.

SDK principal, clock and model collection are explicit fixture seams. Public
admission, branch acceptance, recovery, tool execution and acceptance gates run.
"""
import copy
import json
import os
from pathlib import Path
import unittest

from support import collect, result, config_at, enrolled
import test_live_recovery as legacy
from test_software_routes643 import SoftwareRoutes643
from coordinator_runtime import branches, ordinary, preparation_recovery as recovery, prospective
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import job_prompt, recovery_prompt


class PreparationRecovery917(unittest.IsolatedAsyncioTestCase):
    package_count = 1
    asyncSetUp = SoftwareRoutes643.asyncSetUp
    package = SoftwareRoutes643.package
    select_software = SoftwareRoutes643.select_software
    source = SoftwareRoutes643.source
    prepared = SoftwareRoutes643.prepared
    bootstrap = SoftwareRoutes643.bootstrap
    hit = SoftwareRoutes643.hit
    record = SoftwareRoutes643.record
    git = SoftwareRoutes643.git
    classify = SoftwareRoutes643.classify

    def configure(self):
        SoftwareRoutes643.configure(self)
        self.branch = 'fixture-preparation-branch'
        scope = self.packages['future-qa-1']['scope']
        scope['task_scopes']['qa-execution']['branch_binding'] = self.branch
        self.operations[0]['binding']['scope_sha256'] = digest(scope)

    def original(self):
        public = Path(os.environ['QA_PREPARATION909_PUBLIC_INPUTS'])
        self.report_bytes = (public / 'ACTUAL-QA880-PREPARATION907.json').read_bytes()
        report = json.loads(self.report_bytes)
        detail = json.loads((public / 'ACTUAL-QA880-PREPARATION-DETAIL908.json').read_bytes())
        self.assertEqual(len(report['unknowns']), 6)
        self.source('future-qa-1')
        branches.register(self.store, self.issuer, dict(id=self.branch, repository=str(self.repo),
            origin='https://example.invalid/owned-fiction.git',ref='refs/heads/source',incarnation=ident(),
            scope='future-qa-1',root=self.issuer,authority='Synthetic accepted case Root'))
        branches.accept(self.store, self.branch, self.issuer, 'Synthetic Work genuinely accepts this branch only')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        job, attempt = self.prepared(job, report)
        # Synthetic collected SDK metadata, using all eight original shapes.
        # Never attribute real commands or native session identity to a fixture.
        old = self.store.attempt(attempt)
        tools = copy.deepcopy(detail['tool_completion'])
        for item in tools['items']:
            item['thread'] = old['session']
        synthetic = json.loads(old['detail'])
        synthetic.update(tool_completion=tools, ephemeral=True,ephemeral_readback=True,creation='owned',
                         teardown='actual-owned-process-exit-collected',root_identity_observed=True,
                         sandbox_readback=detail['sandbox_readback'])
        with self.store.tx():
            self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(synthetic),attempt))
        reason = 'Original fully collected preparation contains six retained unknowns'
        self.store.hold_job(job['id'], reason)
        self.store.record_operational_error(job['id'], {'error': reason}, 'QA', 'task-disposition-error')
        return self.store.job(job['id']), attempt

    def basis(self, job, attempt, actor=None):
        return recovery.basis(self.store,job['id'],job['token'],attempt,actor or self.issuer)

    def request(self, job, attempt, basis=None):
        receipt = dict(mode='remaining-work',reason='Explicit NEW preparation under the 909 clarified scope',
            evidence=['Whole original report and eight kernel read-only/no-network tool completions retained'],
            remaining='NEW read-only preparation encounter: preserve full prior report and all six unknowns as original history; '
                      'prepare only the currently admitted scope under 909; actual tools and independent acceptance remain owed.',
            software_preparation=dict(basis=basis or self.basis(job,attempt),
                                      fact='captured-read-only-preparation-no-ordinary-effect'))
        return self.store.request_recovery(job['id'],job['token'],attempt,self.issuer,receipt)

    async def test_exact_original_blockade_then_case_root_new_encounter_and_real_tools(self):
        job, attempt = self.original()
        old = self.store.attempt(attempt)
        before = self.store.job(job['id'])
        with self.assertRaisesRegex(Refusal,'known preparation required'):
            await ordinary.perform(self.store,self.boards['QA'],job)
        native_receipt = dict(mode='remaining-work',reason='Synthetic exact original',evidence=['whole report'],remaining='NEW preparation')
        with self.assertRaisesRegex(Refusal,'actual enrolled role owner'):
            self.store.request_recovery(job['id'],job['token'],attempt,self.issuer,native_receipt)
        with self.assertRaisesRegex(Refusal,'reconciled effects'):
            self.store.request_recovery(job['id'],job['token'],attempt,self.config['roles']['QA']['owner'],native_receipt)
        # Isolate the second, independent legacy_hold blockade without writing.
        with self.assertRaisesRegex(Refusal,'source/legacy holds'):
            self.store.remaining_work_conditions({**job,'effects':'reconciled'},old)
        request = self.request(job,attempt)
        self.assertEqual(self.store.attempt(attempt),old)
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'QA global UNKNOWN')
        self.assertFalse(json.loads(self.store.job(job['id'])['effect_receipt'])['native_owner_consent'])
        self.store.consume_recovery_request(request['id'])
        diagnosis = self.store.diagnosis_attempt(job['id'])
        self.assertIn('NEW read-only preparation',recovery_prompt(self.store,self.store.job(job['id'])))
        collect(self.store,diagnosis,dict(profile='.codex3',remaining='NEW preparation under exact current scope',rationale='Original unavailable; do not resume or replay'))
        successor = self.store.handoff(job['id'],diagnosis)
        current = self.store.job(job['id'])
        self.assertEqual(current['id'],job['id'])
        for field in ('created','token','members','package'):
            self.assertEqual(current[field],before[field])
        self.assertEqual(current['recovery_count'],before['recovery_count']+1)
        handoff = json.loads(self.store.attempt(successor)['detail'])
        self.assertEqual(handoff['prior_result'],old['result'])
        self.assertFalse(handoff['native_resume'])
        prompt=job_prompt(self.store,current)
        context=json.JSONDecoder().raw_decode(prompt.split('TASK_CONTEXT=',1)[1])[0]
        self.assertTrue(context['prior_owned_context']['prior_result']==old['result'])
        self.assertEqual(self.store.attempt(attempt),old)
        # New model seam, full old unknowns conserved as prospective findings.
        answer = result(category='consolidated',summary='New bounded preparation only')
        answer['findings'] += [dict(kind='ordinary-pending-stage',evidence=u) for u in json.loads(old['result'])['unknowns']]
        admission = self.store.one('SELECT * FROM admissions WHERE package=?',(job['package'],))
        self.boards['QA'].bind_software_attempt(self.store,current,successor,admission)
        collect(self.store,successor,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[],unknown_types=[]))
        self.assertTrue(await ordinary.perform(self.store,self.boards['QA'],self.store.job(job['id'])))
        self.assertTrue((self.area/'future-qa-1/out/actual.txt').is_file())
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'),[])
        self.assertFalse(ordinary.accepted_package(self.store,job['package']))
        self.assertEqual(self.store.attempt(attempt),old)
        public = Path(os.environ['QA_PREPARATION909_PUBLIC_INPUTS'])/'ACTUAL-QA880-PREPARATION907.json'
        self.assertEqual(public.read_bytes(),self.report_bytes)

    async def test_wrong_root_native_owner_and_other_package_refuse(self):
        job, attempt = self.original()
        for actor in (ident(),self.config['roles']['QA']['owner']):
            with self.subTest(actor=actor), self.assertRaises(Refusal):self.basis(job,attempt,actor)
        self.store.db.execute('UPDATE branch_associations SET scope=? WHERE id=?',('foreign-package',self.branch))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.assertEqual(self.store.rows('SELECT * FROM recovery_requests'),[])

    async def test_original_unknown_effect_intent_publication_uncollected_and_collector_refuse(self):
        job, attempt = self.original()
        original = self.store.attempt(attempt)
        for field,value in [('collected',None),('ended',None),('capture','incomplete'),('controller',ident()),('exit',1)]:
            with self.subTest(field=field):
                self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(value,attempt))
                with self.assertRaises(Refusal):self.basis(job,attempt)
                self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?',(original[field],attempt))
        self.store.db.execute("UPDATE jobs SET effect_receipt=? WHERE id=?",(encode(dict(evidence=['unknown original effect'],unknown_effects=['not resolved'])),job['id']))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.store.db.execute('UPDATE jobs SET effect_receipt=NULL WHERE id=?',(job['id'],))
        self.store.db.execute("INSERT INTO ordinary_runs VALUES(?,?,?,?,?,'intent',NULL)",(attempt,job['id'],self.epoch['id'],'original','{}'))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    async def test_typed_sandbox_full_known_tools_and_new_encounter_are_mandatory(self):
        job, attempt = self.original()
        old = self.store.attempt(attempt)
        original = json.loads(old['detail'])
        bad = [dict(sandbox_readback={'type':'workspaceWrite','networkAccess':False}),dict(ephemeral=False),
               dict(resume_disposition='available-while-owner-alive'),dict(root_identity_observed=False)]
        for field,value in [('complete',False),('unknown_types',['unknownTool']),('nonzero_completions',[1]),('items',[])]:
            bad.append(dict(tool_completion={**original['tool_completion'],field:value}))
        failed=copy.deepcopy(original['tool_completion']);failed['items'][0]['exit_code']=1
        bad.append(dict(tool_completion=failed))
        for delta in bad:
            with self.subTest(delta=delta):
                self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode({**original,**delta}),attempt))
                with self.assertRaises(Refusal):self.basis(job,attempt)
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(old['detail'],attempt))
        self.assertTrue(self.basis(job,attempt)['new_encounter'])

    async def test_source_lease_epoch_grant_frozen_policy_and_unrelated_hold_binding(self):
        job, attempt = self.original()
        basis=self.basis(job,attempt)
        self.store.hold_job(job['id'],'Unrelated hold')
        with self.assertRaises(Refusal):self.request(job,attempt,basis)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.store.hold_job(job['id'],job['hold_reason'])
        self.store.db.execute('UPDATE branch_associations SET root=? WHERE id=?',(ident(),self.branch))
        with self.assertRaises(Refusal):self.request(job,attempt,basis)
        self.store.db.execute('UPDATE branch_associations SET root=? WHERE id=?',(self.issuer,self.branch))
        self.store.db.execute('UPDATE prospective_authorities SET revoked=? WHERE id=?',(self.now,self.epoch['id']))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.store.db.execute('UPDATE prospective_authorities SET revoked=NULL WHERE id=?',(self.epoch['id'],))
        self.operations[0]['policy']['expires']=0  # Mutating the local Python copy supplies no journal authority.
        self.store.clock=lambda:self.now+601
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.assertEqual(self.store.rows('SELECT * FROM recovery_requests'),[])

    async def test_native_admission_and_revoked_capability_cannot_gain_authority(self):
        job, attempt = self.original()
        admission=self.store.one('SELECT * FROM admissions WHERE package=?',(job['package'],))
        receipt=json.loads(admission['receipt']);receipt.pop('software_admission')
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',(encode(receipt),job['package']))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',(admission['receipt'],job['package']))
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.now,self.cap))
        with self.assertRaises(Refusal):self.basis(job,attempt)

    async def test_publication_or_unknown_branch_writer_refuses_without_mutation(self):
        job, attempt = self.original()
        self.store.db.execute('INSERT INTO file_publications VALUES(?,?,?,?,?,?,?)',
            (attempt,str(self.area/'never-published'),'intent','unqualified',None,'{}',None))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.store.db.execute('DELETE FROM file_publications WHERE attempt=?',(attempt,))
        self.store.db.execute('INSERT INTO branch_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)',
            ('unknown-original',self.branch,'builder','','original-context',self.issuer,'.codex3',
             'unknown-writer','{}','unknown',self.now))
        with self.assertRaises(Refusal):self.basis(job,attempt)
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.rows('SELECT * FROM recovery_requests'),[])

    async def test_source_ref_frozen_admission_and_current_grant_are_independent_guards(self):
        job, attempt = self.original()
        basis=self.basis(job,attempt)
        self.git('update-ref','-d','refs/heads/source',self.packages[job['package']]['head'])
        with self.assertRaises(Refusal):self.request(job,attempt,basis)
        self.git('update-ref','refs/heads/source',self.packages[job['package']]['head'])
        admission=self.store.one('SELECT * FROM admissions WHERE package=?',(job['package'],))
        body=json.loads(admission['receipt']);body['resource_evidence']='changed scope'
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',(encode(body),job['package']))
        with self.assertRaises(Refusal):self.request(job,attempt,basis)
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?',(admission['receipt'],job['package']))
        grant=self.store.enrollment('QA')['grant_id']
        self.store.db.execute('UPDATE enrollments SET grant_id=? WHERE role=?',(ident(),'QA'))
        with self.assertRaises(Refusal):self.request(job,attempt,basis)
        self.store.db.execute('UPDATE enrollments SET grant_id=? WHERE role=?',(grant,'QA'))
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    async def test_expired_resource_lease_and_event_hold_refuse_even_with_live_epoch(self):
        job, attempt = self.original()
        current=json.loads(self.store.one('SELECT selection FROM prospective_authorities WHERE id=?',(self.epoch['id'],))['selection'])
        current['expires']=self.now+1200
        self.store.db.execute('UPDATE prospective_authorities SET selection=? WHERE id=?',(encode(current),self.epoch['id']))
        self.store.clock=lambda:self.now+601
        with self.assertRaisesRegex(Refusal,'lease required'):self.basis(job,attempt)
        self.store.clock=lambda:self.now
        event=json.loads(job['members'])[0]['event']
        self.store.set_hold(event,'actual unrelated source hold')
        with self.assertRaises(Refusal):self.basis(job,attempt)

    async def test_after_request_changed_rights_cannot_be_consumed_or_replayed(self):
        job, attempt = self.original()
        request=self.request(job,attempt)
        before=self.store.attempt(attempt)
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.now,self.cap))
        with self.assertRaises(Refusal):self.store.consume_recovery_request(request['id'])
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')
        self.assertEqual(self.store.attempt(attempt),before)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),1)

    def test_public_command_shape(self):
        from coordinator_runtime.cli import parser
        args=parser().parse_args(['software-preparation-recovery-basis','cap','job','--token','reservation','--attempt','original'])
        self.assertEqual((args.capability,args.job,args.attempt),('cap','job','original'))

    async def test_real_cli_routes_authenticate_Work_and_submit_the_exact_typed_receipt(self):
        from unittest.mock import patch
        from test_qa629_repairs import actor
        from coordinator_runtime.cli import parser, operate
        job,attempt=self.original()
        command=['software-preparation-recovery-basis',self.cap,job['id'],'--token',job['token'],'--attempt',attempt]
        # Genuine principals exist only on this synthetic Board. No live
        # environment identity or native owner is read or modified.
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.issuer}), actor(self.boards['Work'].store,self.issuer):
            basis=operate(parser().parse_args(command),self.store)
            path=self.area/'explicit-recovery-receipt.json'
            path.write_text(encode(dict(mode='remaining-work',reason='New preparation only under current admitted scope',
                evidence=['Full original capture and typed bounded basis reviewed'],remaining='NEW read-only preparation; preserve all old unknowns and actual duties',
                software_preparation=dict(basis=basis,fact='captured-read-only-preparation-no-ordinary-effect'))))
            command[0]='request-software-preparation-recovery'
            request=operate(parser().parse_args(command+['--receipt',str(path)]),self.store)
        self.assertEqual(request['actor'],self.issuer)
        self.assertEqual(request['state'],'pending')
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'),[])


class NativeRecovery917(legacy.OwnerRecovery):
    """Existing native-owner regressions with conserved owned fixtures."""
    async def asyncSetUp(self):
        area=Path(os.environ['QA629_FIXTURES'])/self._testMethodName/ident()
        area.mkdir(parents=True,mode=0o700)
        self.config=config_at(area)
        self.store=enrolled(self.config)
        self.addCleanup(self.store.close)
        from coordinator_runtime.dispatcher import Dispatcher
        self.runtime=Dispatcher(self.store,models=object(),boards={})
        self.owner=self.config['roles']['Work']['owner']
        # Existing tests use self.temp.name as an owned path; no automatic
        # TemporaryDirectory cleanup, so failures and artifacts are conserved.
        from types import SimpleNamespace
        self.temp=SimpleNamespace(name=str(area))

    async def test_group_source_hash_change_and_privacy_exclusion_still_hold(self):
        # Same independent negative oracle as the inherited test. The pinned
        # base already changed its wording; assert pre-read refusal directly.
        from unittest.mock import patch
        from coordinator_runtime import custody
        source=Path(self.temp.name)/'report';source.write_text('peer changed this report')
        answer={**result(),'artifacts':[{'kind':'sources','files':[{'path':str(source),'sha256':'0'*64}]}]}
        job,attempt=self.held(answer)
        with self.assertRaises(Refusal):custody.inventory(self.store,attempt,answer,self.config['tasks']['work-integrator'])
        self.config['artifact_exclusions']=[str(source)]
        before=self.store.attempt(attempt)
        with patch('coordinator_runtime.custody.read_file',side_effect=AssertionError('must exclude before read')):
            with self.assertRaises(Refusal):custody.inventory(self.store,attempt,answer,self.config['tasks']['work-integrator'])
        self.assertEqual(self.store.attempt(attempt),before)

    async def test_unrelated_source_holds_and_request_budget_remain_binding(self):
        job,attempt=self.held()
        self.store.reconcile_effects(job['id'],job['token'],self.owner,{'evidence':['synthetic reconciled'],'unknown_effects':[]})
        source=json.loads(job['members'])[0]['event'];self.store.set_hold(source,'independent source hold')
        with self.assertRaises(Refusal):self.request(job,attempt,'remaining-work')
        self.assertEqual(self.store.rows('SELECT * FROM recovery_requests'),[])
        self.store.set_hold(source,None)
        self.store.hold_job(job['id'],'independent readiness hold')
        with self.assertRaises(Refusal):self.request(job,attempt,'remaining-work')
        self.store.hold_job(job['id'],'synthetic disposition error')
        self.config['limits']['max_owner_corrections']=1
        request=self.request(job,attempt);self.store.consume_recovery_request(request['id'])
        with self.assertRaisesRegex(Refusal,'exhausted'):self.request(job,attempt,reason='Another selected request with distinct evidence')


if __name__ == '__main__':unittest.main()
