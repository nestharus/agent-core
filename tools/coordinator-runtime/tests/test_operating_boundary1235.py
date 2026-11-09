"""Owned focused operating-boundary controls; provider/grants/epochs are fiction.

Real source hashing, retained holds, protected caller, Store collection, conflict
comparison and whole-envelope transport run. No actual provider or account runs.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime import public_program, review_composition, service_report_scope as service
from coordinator_runtime import report_scope, resource_scopes, prospective, processing, software
from coordinator_runtime.contracts import Refusal, digest, encode
from fixture_conservation import capacity
from test_current_caller1226 import CurrentCaller1226
import test_current_caller1226 as caller_fixture
from support import queued


class PublicProgram(unittest.TestCase):
    def setUp(self):
        capacity(Path('/fixtures'))
        self.area = Path(tempfile.mkdtemp(prefix='public-program-', dir='/fixtures'))

    def program(self, data=b'owned program fiction'):
        path = self.area/'program'
        capacity(self.area)
        path.write_bytes(data)
        path.chmod(0o700)
        return path

    def test_complete_stream_crosses_old_bound_without_body_retention(self):
        path = self.area/'large-program'
        size = 33*1024**2
        capacity(self.area)
        with path.open('xb') as stream:
            stream.truncate(size)
        path.chmod(0o700)
        value = public_program.identity(path, size, size)
        expected = hashlib.sha256()
        for _ in range(33): expected.update(bytes(1024**2))
        self.assertEqual(value['sha256'], expected.hexdigest())
        self.assertEqual(value['bytes'], size)
        self.assertTrue(value['stable_before_after_path'])
        self.assertFalse(value['body_retained'])
        self.assertFalse(value['executed'])

    def test_exclusions_private_and_invalid_bounds_precede_metadata(self):
        with patch.object(public_program.os, 'open', side_effect=AssertionError('must refuse lexically')):
            for path, size, ceiling, exclusions in [
                (self.area/'held/program',1,1,[str(self.area/'held')]),
                (Path.home()/'.codex2/program',1,1,[]),
                (self.area/'program',5,4,[]), (self.area/'program',True,4,[])]:
                with self.subTest(path=path):
                    with self.assertRaises(Refusal): public_program.identity(path,size,ceiling,exclusions)

    def test_size_regular_execute_and_alias_refusals_precede_body(self):
        path = self.program()
        with patch.object(public_program.os, 'read', side_effect=AssertionError('no refused body read')):
            with self.assertRaises(Refusal): public_program.identity(path,1,1)
            path.chmod(0o600)
            with self.assertRaises(Refusal): public_program.identity(path,20,20)
        opened=os.open
        def nofollow(name, flags, **options):
            self.assertTrue(flags & os.O_NOFOLLOW)
            if name == 'authored-alias': raise OSError('authored ELOOP refusal')
            return opened(name,flags,**options)
        with patch.object(public_program.os,'open',side_effect=nofollow):
            with self.assertRaises(OSError): public_program.identity(self.area/'authored-alias',20,20)

    def test_hardlinks_keep_exact_identity_without_alias_discovery(self):
        path = self.program()
        capacity(self.area)
        os.link(path,self.area/'authored-second-link')
        value = public_program.identity(path,path.stat().st_size,4096)
        self.assertEqual(value['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue(value['stable_before_after_path'])

    def test_content_mutation_during_hash_refuses(self):
        path = self.program(b'a'*(2*1024**2))
        read = os.read
        changed = []
        def mutate(fd, size):
            block = read(fd,size)
            if block and os.fstat(fd).st_ino == path.stat().st_ino and not changed:
                changed.append((os.fstat(fd).st_mtime_ns,os.fstat(fd).st_ctime_ns))
                capacity(self.area)
                with path.open('r+b') as stream: stream.write(b'b')
            return block
        with patch.object(public_program.os,'read',side_effect=mutate):
            with self.assertRaisesRegex(Refusal,'changed'): public_program.identity(path,2*1024**2,3*1024**2)
        self.assertEqual(path.read_bytes()[0:1],b'b')

    def test_replaced_parent_path_cannot_certify_detached_original(self):
        directory=self.area/'source'
        capacity(self.area);directory.mkdir()
        path=directory/'program'
        capacity(directory);path.write_bytes(b'owned program');path.chmod(0o700)
        inode=path.stat().st_ino
        read=os.read
        replaced=[]
        def replace(fd,size):
            block=read(fd,size)
            if block and os.fstat(fd).st_ino==inode and not replaced:
                replaced.append(True)
                capacity(self.area);directory.rename(self.area/'retained-original')
                capacity(self.area);directory.mkdir()
                capacity(directory);path.write_bytes(b'owned program');path.chmod(0o700)
            return block
        with patch.object(public_program.os,'read',side_effect=replace):
            with self.assertRaisesRegex(Refusal,'path identity changed'):
                public_program.identity(path,13,4096)
        self.assertTrue((self.area/'retained-original/program').exists())
        self.assertTrue(path.exists())

    def test_versioned_program_contract_preserves_old_policy_and_refuses_partial_identity(self):
        policy = dict(continuing=dict(version=review_composition.PROGRAM_VERSION,
            source_files={n+'.py':'a'*64 for n in review_composition.MODULES},
            pool_control=dict(routes='public-routes',static_sha256='a'*64), runtime_reads=['public-runtime'],
            executable_sha256='b'*64, executable_identity=dict(bytes=320575976,max_bytes=384*1024**2),
            capture_max=65536,allowance_bytes=64*1024**2,allowance_entries=2000))
        self.assertEqual(review_composition.declaration(policy)['executable_identity']['bytes'],320575976)
        for size,maximum in [(320575976,32*1024**2),(True,384*1024**2),(1,2*1024**3)]:
            bad=copy.deepcopy(policy);bad['continuing']['executable_identity']=dict(bytes=size,max_bytes=maximum)
            with self.assertRaises(Refusal):review_composition.declaration(bad)


class ProgramComposition(CurrentCaller1226):
    def test_v2_actual_dependency_checks_program_pin_and_typed_current_read_right(self):
        config_at=caller_fixture.config_at
        def source_rights(directory):
            value=config_at(directory)
            value['tasks']['reviews-proposer']['effect_authority']['operations'].append('read-source')
            return value
        with patch.object(caller_fixture,'config_at',side_effect=source_rights): self.fixture()
        value=self.policy['continuing']
        value['version']=review_composition.PROGRAM_VERSION
        value['executable_identity']=dict(bytes=self.executable.stat().st_size,max_bytes=384*1024**2)
        routes=review_composition.dependencies(self.store,self.attempt,self.policy,self.package)
        self.assertEqual(str(routes),self.store.config['execution_pool_routes'])
        pin=value['executable_sha256'];value['executable_sha256']='f'*64
        with self.assertRaisesRegex(Refusal,'changed'):
            review_composition.dependencies(self.store,self.attempt,self.policy,self.package)
        value['executable_sha256']=pin
        self.store.config['tasks']['reviews-proposer']['effect_authority']['operations'].remove('read-source')
        with self.assertRaisesRegex(Refusal,'typed'):
            review_composition.dependencies(self.store,self.attempt,self.policy,self.package)



    def test_release_source_selection_does_not_promote_execute_only_QA(self):
        from coordinator_runtime import configuration
        self.fixture()
        self.store.config.update(operator_cli=str(Path(configuration.__file__).parents[1]/'coordinator'),
            control_receive=dict(mode='cooperative',instructions=str(self.area/'procedure.md')))
        qa=self.store.config['tasks']['qa-execution']
        qa['effect_authority']['operations']=['execute-admitted-qa']
        with self.assertRaisesRegex(Refusal,'already source-authorized'):
            configuration.candidate(self.store,str(self.area/'unselected.json'),['qa-execution'])
        work=self.store.config['tasks']['work-proposer']
        work['effect_authority']['operations'].append('read-source')
        value=configuration.candidate(self.store,str(self.area/'unselected.json'),['work-proposer'])
        self.assertEqual(value['release_scope_tasks'],['work-proposer'])
        self.assertEqual(value['tasks']['qa-execution']['effect_authority']['operations'],['execute-admitted-qa'])
        self.assertEqual(value['tasks']['qa-execution'].get('scope_roots'),qa.get('scope_roots'))
        self.assertTrue(any(p.endswith('/tools/coordinator-runtime') for p in
            value['tasks']['work-proposer']['effect_authority']['read_roots']))


class ServiceReports(CurrentCaller1226):
    def prepare(self):
        original_config=caller_fixture.config_at
        def narrow(directory):
            value=original_config(directory)
            neutral=directory/'source-neutral'
            capacity(directory);neutral.mkdir()
            source=value['tasks']['reviews-proposer']
            source['cwd']=str(neutral)
            source['effect_authority']['read_roots']=[str(directory/n) for n in
                ('fiction.txt','procedure.md','fiction-cli','pool-routes.toml')]
            return value
        # Select the genuinely narrow source before Store reservation/freeze.
        # Broad cwd ceilings remain real conflicts, never rewritten afterward.
        with patch.object(caller_fixture,'config_at',side_effect=narrow):
            self.fixture()
        self.grants = True
        self.grant_calls = []
        def authority(*args):
            self.grant_calls.append(True)
            if not self.grants: raise Refusal('fictional current rights revoked')
            return {'owner':self.store.config['roles']['Reviews']['owner']}
        board=SimpleNamespace(verify_authority=authority,software_authority=authority,_software_job_grant=authority)
        self.access.boards={'Work':board,'Reviews':board}
        receiver=self.store.config['tasks']['reviews-integrator']
        neutral=self.area/'neutral'
        capacity(self.area);neutral.mkdir()
        receiver.update(cwd=str(neutral),sandbox='workspace-write',effects='owned-artifacts',capacity=1)
        receiver['effect_authority']['read_roots']=[str(self.area/'procedure.md')]
        receiver['effect_authority']['operations']=['read-reports','consolidate-reports','write-owned-artifacts']
        self.cap={'id':self.access.key,'issuer':self.store.config['roles']['Work']['owner']}
        self.access.current=lambda:(self.cap,self.selected)
        self.selected.update(future_intake=True,basis=dict(future_only=True,event_boundary=0,
            configuration=digest(self.store.config),implementation=processing.implementation()))
        self.record=dict(original_hold='original unbounded UNKNOWN retained',roots=[],unbounded=True,
                         evidence='Fictional new operation comparison; no legacy scope closure')
        p=dict(version=service.VERSION,authority='Fictional prospective Work selection before intake',expires=self.now+1000,
            configuration_sha256=digest(self.store.config),implementation_sha256=digest(self.selected['basis']['implementation']),
            source_task='reviews-proposer',source_task_sha256=digest(self.store.config['tasks']['reviews-proposer']),
            review_policy_sha256=digest(self.policy),task='reviews-integrator',task_sha256=digest(receiver),
            collector=self.store.controller,recipient=self.store.config['roles']['Reviews']['owner'])
        self.record['service_report']=p
        self.selected['service']['legacy_resources']['Reviews']=self.record
        self.store.db.execute('UPDATE enrollments SET legacy_hold=? WHERE role=?',(self.record['original_hold'],'Reviews'))
        self.epoch=dict(id='fictional-epoch',job_boundary=-1,policy=dict(ordinary_effects=False),
            selection=dict(processing_capability=self.cap['id']))
        for name in ('current','for_job'):
            context=patch.object(prospective,name,return_value=self.epoch);context.start();self.addCleanup(context.stop)
        context=patch.object(prospective,'job_position',return_value=1);context.start();self.addCleanup(context.stop)
        detail=json.loads(self.store.attempt(self.attempt)['detail']);detail['processing_capability']=self.cap['id']
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),self.attempt))
        outcome=self.execute()
        # The adverse command remains report evidence, not a capture failure.
        outcome['result']['failures'].append(dict(verdict='FAILED',meaning='fictional inherited adverse evidence'))
        outcome['result']['unknowns'].append(dict(original='unknown duty retained'))
        self.store.collect(self.attempt,outcome)
        response=self.store.finish_job(self.job['id'],self.job['token'])
        self.assertIsNotNone(response)
        self.response=self.store.event(response)
        queued(self.store,self.response)
        self.row=dict(role='Reviews',task='reviews-integrator',phase='integrator',package=None,event=response)
        service.authenticate(self.store,self.row,self.record)
        resource_scopes.original_modes(self.store,self.store.job(self.job['id']))
        return self.row

    def test_whole_protected_adverse_report_receives_under_retained_hold_with_new_analysis(self):
        row=self.prepare()
        resource_scopes.validate(self.store,{'Reviews':self.record},self.selected)
        self.assertFalse(resource_scopes.blocked(self.store,row))
        reports=report_scope.integration_inputs(self.store,row)
        self.assertEqual(reports[0]['original'],self.response)
        self.assertEqual(reports[0]['service_receipt']['grade'],'protected-nonnative')
        self.assertFalse(reports[0]['service_receipt']['native_owner_execution'])
        self.assertTrue(reports[0]['original']['body']['failures'])
        self.assertTrue(reports[0]['original']['body']['unknowns'])
        self.assertEqual(self.store.enrollment('Reviews')['legacy_hold'],self.record['original_hold'])
        self.assertTrue(self.record['unbounded'])
        self.assertEqual(report_scope.bounded_members(self.store,row,[row]),[row])
        analysis=dict(**report_scope.integration_protocol(self.store,row,reports),
            analysis='Independently compare current whole evidence; inherited failures remain failures.',
            decision='Return scoped consequences to Work; no acceptance or old closure.',
            method='Applied current declared method to these actual envelopes.',
            coverage=[dict(**pin,extent='whole',limits=['Nested references not acquired']) for pin in report_scope.source_pins(reports)])
        answer=dict(semantic='DONE',findings=[analysis])
        self.assertTrue(report_scope.analysis_result(self.store,row,answer,reports))
        self.assertGreater(len(self.grant_calls),2)

    def test_changed_capability_rights_source_binding_and_missing_protection_refuse(self):
        row=self.prepare()
        self.assertFalse(resource_scopes.blocked(self.store,row))
        for field in ('configuration_sha256','implementation_sha256','source_task_sha256','review_policy_sha256','task_sha256','collector','recipient'):
            original=self.record['service_report'][field];self.record['service_report'][field]='changed'
            with self.subTest(field=field):self.assertTrue(resource_scopes.blocked(self.store,row))
            self.record['service_report'][field]=original
        self.grants=False;self.assertTrue(resource_scopes.blocked(self.store,row));self.grants=True
        detail=json.loads(self.store.attempt(self.attempt)['detail'])
        detail['processing_capability']='old-capability'
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),self.attempt))
        self.assertTrue(resource_scopes.blocked(self.store,row))

    def test_whole_envelope_tamper_capture_and_real_lease_conflicts_refuse(self):
        row=self.prepare()
        self.assertFalse(resource_scopes.blocked(self.store,row))
        source=self.store.job(self.job['id'])
        self.store.db.execute("UPDATE attempts SET capture='incomplete' WHERE id=?",(self.attempt,))
        self.assertTrue(resource_scopes.blocked(self.store,row))
        self.store.db.execute("UPDATE attempts SET capture='complete' WHERE id=?",(self.attempt,))
        self.record['roots']=[str(self.area/'procedure.md')]
        self.assertTrue(resource_scopes.blocked(self.store,row));self.record['roots']=[]
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)',('orphan-lease','fictional-orphan'))
        self.assertTrue(resource_scopes.blocked(self.store,row))
        self.assertEqual(self.store.enrollment('Reviews')['legacy_hold'],self.record['original_hold'])

    def test_full_independent_allowance_and_native_boundary_stay_required(self):
        row=self.prepare()
        self.assertFalse(resource_scopes.blocked(self.store,row))
        old=self.store.config['limits']['max_result_bytes']
        # Keep configuration pin current only to isolate actual envelope budget.
        self.store.config['limits']['max_result_bytes']=self.store.config['limits']['max_bytes']
        self.record['service_report']['configuration_sha256']=digest(self.store.config)
        self.selected['basis']['configuration']=digest(self.store.config)
        with self.assertRaises(Refusal): service.authenticate(self.store,row,self.record)
        self.store.config['limits']['max_result_bytes']=old
        self.record['service_report']['configuration_sha256']=digest(self.store.config)
        self.selected['basis']['configuration']=digest(self.store.config)
        bad=copy.deepcopy(self.record);bad['native_review_return']={}
        with self.assertRaises(Refusal):service.validate(self.store,'Reviews',bad,self.selected)
        bad=copy.deepcopy(self.record);bad['reviews_report']={}
        with self.assertRaises(Refusal):service.validate(self.store,'Reviews',bad,self.selected)


    def test_received_delivery_rechecks_real_receiver_and_rejects_source_self_analysis(self):
        row=self.prepare()
        source=self.store.job(self.job['id'])
        outbox=dict(kind='result',payload=encode(self.response),recipient='Reviews',event=self.response['id'])
        self.assertEqual(software.report_delivery(self.store,source,outbox),['reviews-integrator'])
        self.grants=False
        with self.assertRaises(Refusal):software.report_delivery(self.store,source,outbox)
        self.grants=True
        receiver=self.store.reserve()
        self.assertIsNotNone(receiver)
        attempt=self.store.start_job(receiver['id'],receiver['token'])
        self.store.session(attempt,self.store.attempt(self.attempt)['session'])
        receiver=self.store.job(receiver['id'])
        self.assertTrue(resource_scopes.blocked(self.store,receiver))

    def test_original_envelope_and_protection_tampering_refuse(self):
        row=self.prepare()
        before=self.store.one('SELECT payload,hash FROM events WHERE id=?',(self.response['id'],))
        changed=copy.deepcopy(self.response);changed['body']['unknowns']=[]
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?',(encode(changed),self.response['id']))
        self.assertTrue(resource_scopes.blocked(self.store,row))
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?',(before['payload'],self.response['id']))
        call=self.store.one('SELECT receipt FROM review_calls WHERE attempt=?',(self.attempt,))
        turns=json.loads(call['receipt'])
        for turn in turns:
            if 'actual_END' in turn:turn['receipt']['protection']['persisted']=False
        self.store.db.execute('UPDATE review_calls SET receipt=? WHERE attempt=?',(encode(turns),self.attempt))
        self.assertTrue(resource_scopes.blocked(self.store,row))
