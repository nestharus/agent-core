"""Actual ordinary caller and finite admission tests; all provider facts fictional.

New local children, Store/conflict/collection and typed configuration paths are
real. No model, protected engineering context or operating acceptance runs.
"""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from contextlib import contextmanager
import unittest
from unittest.mock import patch

from coordinator_runtime import appserver, report_scope, resource_scopes, configuration
from coordinator_runtime import public_runtime, review_composition
from coordinator_runtime.contracts import Refusal, digest, encode
from fixture_conservation import capacity
from test_operating_boundary1235 import ServiceReports
from test_current_caller1226 import CurrentCaller1226
import test_current_caller1226 as caller_fixture
from test_read_ceiling760 import ReadCeiling
from support import result
sys.path.insert(0, str(Path(__file__).parents[2]/'direct-child'))
import continuing_review as cr

HELPER = dict(path='/usr/bin/python3.12', bytes=8020928, max_bytes=16*1024**2,
    sha256='e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f',
    startup='python-isolated-no-site-no-bytecode',
    runtime_directories=sorted(public_runtime.RUNTIME_DIRECTORIES))


@contextmanager
def public_owner_fixture():
    """Explicit UID-map seam for the empty unprivileged test namespace only.

    Host root-owned public mounts report overflow uid here; the fresh namespace
    anchor is test-owned. This seam does not attest current host ownership.
    Complete program reads, modes, canonical paths and Python execution are real.
    """
    actual = Path.stat
    paths = {Path('/'), Path('/usr'), Path('/usr/bin'), Path('/usr/lib'),
             Path(HELPER['path']), *(Path(p) for p in HELPER['runtime_directories'])}
    def mapped(path, *args, **kwargs):
        info = actual(path,*args,**kwargs)
        if path in paths:
            fields=list(info);fields[4]=0
            return os.stat_result(fields)
        return info
    with patch.object(Path,'stat',new=mapped):yield


class CurrentUse(ServiceReports):
    def ordinary(self, change=None, after_start=False, continuation=False):
        self.prepare()
        receiver = self.store.reserve()
        self.assertIsNotNone(receiver)
        attempt = self.store.start_job(receiver['id'], receiver['token'])
        receiver = self.store.job(receiver['id'])
        # Real preparation authenticates the same original before awaited setup.
        reports = report_scope.integration_inputs(self.store, receiver)
        self.assertEqual(reports[0]['original'], self.response)
        plan = self.area/'ordinary-plan.json'
        capacity(plan.parent)
        plan.write_text(encode(dict(result=result('PARTIAL' if continuation else 'DONE'))))
        adapter = appserver.AppServer(self.store.config, [sys.executable,
            str(Path(__file__).with_name('fixture_appserver.py')),str(plan)])
        sent = []
        exchange, send, complete = appserver.Peer.exchange, appserver.Peer.send, appserver.Peer.completion
        async def scheduled(peer, number, method, params, future, progress, started):
            # This is an actual awaited RPC/setup path, including the task
            # scheduling gap introduced by Peer.rpc's wait_for(exchange).
            if method == ('thread/read' if continuation else 'turn/start') and not after_start:
                await asyncio.sleep(0)
                if change: change()
            return await exchange(peer,number,method,params,future,progress,started)
        async def observed(peer, value):
            await send(peer,value)
            if value.get('method') == 'turn/start':sent.append(value['method'])
        async def completed(peer,*args):
            answer = await complete(peer,*args)
            if after_start and change:change()
            return answer
        async def run():
            with patch.object(appserver.Peer,'exchange',scheduled), patch.object(appserver.Peer,'send',observed), patch.object(appserver.Peer,'completion',completed):
                return await adapter.run(self.store,attempt,'Whole original inline report fixture',
                    self.store.config['tasks']['reviews-integrator'])
        outcome = asyncio.run(run())
        self.assertIs(type(outcome['exit']),int)
        self.assertFalse(adapter.owned_collections)
        self.assertEqual(self.store.enrollment('Reviews')['legacy_hold'],self.record['original_hold'])
        self.assertTrue(self.record['unbounded'])
        self.assertEqual(self.store.event(self.response['id']),self.response)
        capacity(self.area)
        (self.area/'ordinary-use.json').write_text(encode(dict(attempt=attempt,sent=sent,outcome=outcome)))
        return attempt, receiver, outcome, sent

    def test_expiry_during_scheduled_turn_dispatch_prevents_any_model_turn(self):
        a,j,o,s = self.ordinary(lambda:setattr(self,'now',self.record['service_report']['expires']+1))
        self.assertEqual(s,[])
        self.assertIsNone(o['result'])
        self.assertIsNotNone(o['error'])
        self.assertEqual(o['detail']['thread_start'],'owned-root-observed')
        self.store.collect(a,o)
        self.assertIsNone(self.store.job(j['id'])['response'])

    def test_expiry_during_whole_authentication_is_reaffirmed_at_dispatch(self):
        original = report_scope.integration_inputs
        def checked(runtime, row):
            value = original(runtime, row)
            if getattr(self, 'expire_after_authentication', False):
                self.now = self.record['service_report']['expires']+1
            return value
        with patch.object(report_scope, 'integration_inputs', side_effect=checked):
            a,j,o,s = self.ordinary(lambda:setattr(self,'expire_after_authentication',True))
        self.assertEqual(s,[])
        self.assertIsNone(o['result'])
        self.assertIn('expired before actual analysis dispatch',o['error'])
        self.store.collect(a,o)
        self.assertIsNone(self.store.job(j['id'])['response'])

    def test_new_real_orphan_lease_during_setup_refuses_without_removing_conflict(self):
        def change():self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)',('new-retained-original','fictional-orphan'))
        a,j,o,s = self.ordinary(change)
        self.assertEqual(s,[])
        self.assertIsNone(o['result'])
        self.assertIsNotNone(self.store.one('SELECT * FROM ordinary_resources WHERE resource=?',('new-retained-original',)))
        self.store.collect(a,o)
        self.assertIsNone(self.store.job(j['id'])['response'])

    def test_authorized_start_then_expiry_keeps_result_and_honest_later_refusal(self):
        a,j,o,s = self.ordinary(lambda:setattr(self,'now',self.record['service_report']['expires']+1),after_start=True)
        self.assertEqual(s,['turn/start'])
        self.assertEqual(o['result']['semantic'],'DONE')
        self.store.collect(a,o)
        with self.assertRaises(Refusal):report_scope.validate_result(self.store,j,o['result'])
        self.assertIsNone(self.store.job(j['id'])['response'])
        self.assertEqual(self.store.attempt(a)['exit'],0)

    def test_continuation_rechecks_after_idle_read_and_preserves_first_partial(self):
        a,j,o,s = self.ordinary(lambda:setattr(self,'now',self.record['service_report']['expires']+1),continuation=True)
        self.assertEqual(s,['turn/start'])
        self.assertEqual(o['detail']['prior_turn_result']['semantic'],'PARTIAL')
        self.assertIsNotNone(o['error'])
        self.store.collect(a,o)
        self.assertIsNone(self.store.job(j['id'])['response'])


class TypedPublicRead(ReadCeiling):
    def typed(self):
        program = self.f.directory/'finite-public-program'
        capacity(program.parent)
        with program.open('xb') as out:
            for _ in range(34):out.write(b'finite program identity fixture\n'.ljust(1024**2,b'x'))
        program.chmod(0o700)
        return dict(version=public_runtime.VERSION,binding=copy.deepcopy(self.entry),
            capability='future-only-new',programs=[dict(path=str(program),bytes=34*1024**2,
                max_bytes=40*1024**2,sha256=self.sha(program))],runtime_directories=[])

    def test_large_program_uses_separate_finite_type_and_real_source_grant_binding(self):
        entry = self.typed()
        evidence=copy.deepcopy(self.entry)
        evidence['safe_files'][entry['programs'][0]['path']]=entry['programs'][0]['sha256']
        evidence['read_roots'].append(entry['programs'][0]['path'])
        with self.assertRaisesRegex(Refusal,'bounded acquisition'):self.draft(evidence)
        options={'public_runtime_reads':{'bp':entry}}
        value=configuration.candidate(self.s,str(self.f.directory/'typed.json'),[],scope_options=options)
        capacity(self.f.directory);Path(value['operator_config']).write_text(encode(value))
        configuration.validate_changes(self.s,value,['bp'])
        self.assertIn(entry['programs'][0]['path'],value['tasks']['bp']['effect_authority']['read_roots'])
        self.assertEqual(value['tasks']['bp']['effect_authority']['operations'],['read-source'])
        grants=[tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')]
        basis=configuration.basis(self.s,self.f.boards,value,['bp'])
        configuration.apply(self.s,self.f.boards,value,dict(basis=basis,authority='fictional actual Work choice'))
        self.assertEqual(grants,[tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')])
        self.assertEqual(self.s.config,self.f.original)
        self.assertFalse(self.s.one('SELECT id FROM processing_capabilities WHERE revoked IS NULL'))

    def test_changed_source_owner_grant_program_and_unselected_task_refuse(self):
        entry=self.typed()
        for field,invalid in [('configuration','0'*64),('role_owner','foreign'),('original_grant','foreign')]:
            bad=copy.deepcopy(entry);bad['binding'][field]=invalid
            with self.subTest(field=field),self.assertRaises(Refusal):
                configuration.candidate(self.s,str(self.f.directory/'invalid.json'),[],scope_options={'public_runtime_reads':{'bp':bad}})
        bad=copy.deepcopy(entry);bad['programs'][0]['sha256']='0'*64
        with self.assertRaisesRegex(Refusal,'changed'):
            configuration.candidate(self.s,str(self.f.directory/'invalid.json'),[],scope_options={'public_runtime_reads':{'bp':bad}})
        value=configuration.candidate(self.s,str(self.f.directory/'unselected.json'),[],scope_options={'public_runtime_reads':{'bp':entry}})
        capacity(self.f.directory);Path(value['operator_config']).write_text(encode(value))
        with self.assertRaises(Refusal):configuration.validate_changes(self.s,value,['wp'])

    def test_execute_only_does_not_become_source_read_by_label(self):
        entry=self.typed()
        self.s.config['tasks']['bp']['effect_authority']['operations']=['execute-admitted-qa']
        with patch.object(public_runtime,'identity',side_effect=AssertionError('no body read')):
            with self.assertRaisesRegex(Refusal,'source-read'):
                public_runtime.extend(self.s,self.s.config,copy.deepcopy(self.s.config),{'bp':entry})

    def test_directory_trust_is_explicit_finite_and_exclusions_precede_acquisition(self):
        for path in ['/', '/usr', '/usr/lib']:
            with self.subTest(path=path),self.assertRaises(Refusal):public_runtime.trusted_directory(path)
        with patch.object(public_runtime,'identity',side_effect=AssertionError('held body acquired')):
            with self.assertRaises(Refusal):public_runtime.check_helper(HELPER,['/usr/bin/python3.12'])
        with patch.object(Path,'iterdir',side_effect=AssertionError('runtime census')),patch.object(Path,'glob',side_effect=AssertionError('runtime tree hash')):
            with public_owner_fixture():
                for path in HELPER['runtime_directories']:public_runtime.trusted_directory(path)


class HelperInvocation(unittest.IsolatedAsyncioTestCase):
    async def test_actual_isolated_startup_and_control_all_four_operations(self):
        import tempfile
        area=Path(tempfile.mkdtemp(prefix='isolated-helper-',dir='/fixtures'))
        capacity(area);(area/'json.py').write_text('raise RuntimeError("authored cwd startup trap")')
        allowed,outside,write=area/'allowed',area/'outside',area/'write'
        for p in [allowed,outside]:capacity(area);p.write_text('owned-allowed-canary' if p==allowed else 'owned-outside-canary')
        calls=[]
        def helper():
            with public_owner_fixture():calls.append(public_runtime.check_helper(HELPER,[]))
            return HELPER['path']
        server=await asyncio.start_server(lambda r,w:w.close(),'127.0.0.1',0)
        try:
            argv=cr.probe_command(allowed,outside,write,server.sockets[0].getsockname()[1],helper)
            self.assertEqual(argv[:5],[HELPER['path'],'-I','-S','-B','-c'])
            child=await asyncio.create_subprocess_exec(*argv,cwd=area,
                env={'PYTHONPATH':str(area),'PYTHONHOME':str(area),'HOME':str(area)},
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            out,err=await child.communicate()
            self.assertEqual(child.returncode,0,err)
            row=json.loads(out)
            self.assertEqual(row,dict(allowed=dict(read='owned-allowed-canary'),outside=dict(read='owned-outside-canary'),write='succeeded',network='succeeded'))
            self.assertEqual(len(calls),1)
            self.assertFalse((area/'__pycache__').exists())
            capacity(area);(area/'actual-child.json').write_text(encode(dict(argv=argv,END=child.returncode,stdout_EOF=True,stderr_EOF=True,result=row)))
        finally:
            server.close();await server.wait_closed()

    async def test_helper_changed_pin_and_missing_typed_read_right_prevent_command(self):
        bad=copy.deepcopy(HELPER);bad['sha256']='0'*64
        with public_owner_fixture(),self.assertRaisesRegex(Refusal,'changed'):public_runtime.check_helper(bad,[])
        config=dict(tasks={'rp':dict(effect_authority=dict(operations=['read-reports'],read_roots=[]))},artifact_exclusions=[])
        runtime=SimpleNamespace(config=config,attempt=lambda a:dict(job='j'),job=lambda j:dict(task='rp'))
        policy=dict(continuing=dict(version=review_composition.RUNTIME_VERSION,
            source_files={n+'.py':'a'*64 for n in review_composition.MODULES},
            pool_control=dict(routes='fictional',static_sha256='b'*64),runtime_reads=[HELPER['path'],*HELPER['runtime_directories']],
            executable_sha256='c'*64,executable_identity=dict(bytes=1,max_bytes=1),probe_helper=HELPER,
            capture_max=65536,allowance_bytes=64*1024**2,allowance_entries=2000))
        with patch.object(public_runtime,'identity',side_effect=AssertionError('no unauthorized read')):
            with self.assertRaisesRegex(Refusal,'typed source-read'):review_composition.probe_helper(runtime,'a',policy)


class JointFactory(CurrentCaller1226):
    def test_v3_common_helper_drives_real_local_control_and_exact_provider_evidence(self):
        config_at=caller_fixture.config_at
        def rights(directory):
            value=config_at(directory)
            task=value['tasks']['reviews-proposer']
            task['effect_authority']['operations'].append('read-source')
            task['effect_authority']['read_roots'] += [HELPER['path'], *HELPER['runtime_directories']]
            return value
        fiction=caller_fixture.CLI.replace('/usr/bin/python3 -c ', '/usr/bin/python3.12 -I -S -B -c ')
        with patch.object(caller_fixture,'config_at',side_effect=rights),patch.object(caller_fixture,'CLI',fiction):self.fixture()
        value=self.policy['continuing']
        value.update(version=review_composition.RUNTIME_VERSION,
            executable_identity=dict(bytes=self.executable.stat().st_size,max_bytes=1024**2),
            probe_helper=copy.deepcopy(HELPER),runtime_reads=[str(self.executable),HELPER['path'],*HELPER['runtime_directories']])
        with public_owner_fixture():outcome=self.execute()
        self.assertIsNone(outcome['error'])
        self.store.collect(self.attempt,outcome)
        owner=next(iter(self.transport.public_contexts.values()))
        self.assertTrue(owner.review.proof)
        self.assertEqual(len(owner.endpoint.protection.proofs),3)
        for proof in owner.endpoint.protection.proofs:
            self.assertTrue(proof['passed'])
            self.assertEqual(proof['control']['outside']['read'],'owned-outside-canary')
            self.assertEqual(proof['protected']['outside']['error'],13)
        self.assertEqual([o['kind'] for o in self.observations()].count('owned-sandbox-control'),6)
        self.assertFalse(self.transport.originals.owned)
        with public_owner_fixture():asyncio.run(self.executor.close('fiction',self.policy))
