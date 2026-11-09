"""Current union mechanics; provider/grant/acceptance facts are authored fiction.

Owned switches only. Never toggles installed control or invokes real Codex.
"""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, AsyncMock
from coordinator_runtime import appserver, live_fast, review_composition, configuration, reviews
from coordinator_runtime.contracts import Refusal, digest
from test_current_caller1226 import CurrentCaller1226
import test_current_caller1226 as old
from test_coherent_runtime_use import HELPER, public_owner_fixture, CurrentUse
from test_read_ceiling760 import ReadCeiling


def control(path, tasks):
    helper = Path(review_composition.__file__).parents[2]/'direct-child/fast_tier.py'
    return dict(version=live_fast.VERSION,path=str(path),tasks=list(tasks),auxiliary={},
                helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest())


class CoalescedCaller(CurrentCaller1226):
    def fixture(self, *args, **kwargs):
        source = review_composition.source_bodies
        def current(runtime, attempt, policy):
            switch = self.area/'fast-tier'
            if not switch.exists():self.put(switch, 'true\n')
            runtime.config['fast_tier'] = control(switch,runtime.config['tasks'])
            directory = Path(review_composition.__file__).parents[2]/'direct-child'
            value = policy['continuing']
            value.update(version=review_composition.FAST_VERSION,
                source_files={n+'.py':reviews.sha((directory/(n+'.py')).read_bytes()) for n in review_composition.FAST_MODULES},
                executable_identity=dict(bytes=self.executable.stat().st_size,max_bytes=1024**2),
                probe_helper=copy.deepcopy(HELPER),fast_tier=copy.deepcopy(runtime.config['fast_tier']),
                runtime_reads=[str(self.executable),HELPER['path'],*HELPER['runtime_directories']])
            return source(runtime,attempt,policy)
        config_at=old.config_at
        def rights(directory):
            value=config_at(directory)
            value['fast_tier']=control(self.area/'fast-tier',value['tasks'])
            task=value['tasks']['reviews-proposer']
            task['effect_authority']['operations']=list(dict.fromkeys([*task['effect_authority']['operations'],'read-source']))
            task['effect_authority']['read_roots'] += [str(self.area/'fiction-cli'),HELPER['path'],*HELPER['runtime_directories']]
            return value
        fiction=old.CLI.replace('/usr/bin/python3 -c ', '/usr/bin/python3.12 -I -S -B -c ')
        with patch.object(old,'config_at',side_effect=rights),patch.object(old,'CLI',fiction),patch.object(review_composition,'source_bodies',side_effect=current):
            CurrentCaller1226.fixture(self,*args, **kwargs)

    def execute(self):
        with public_owner_fixture():return super().execute()

    def test_final_factory_freezes_fast_helper_and_preserves_qualified_original(self):
        self.fixture()
        self.assertIs(self.package.dispatch.fast_tier,self.package.fast_tier)
        self.assertEqual(self.package.fast_tier.__package__,self.package.__name__)
        frozen=self.package.fast_tier.flags
        outcome=self.execute();self.assertIsNone(outcome['error'])
        self.store.collect(self.attempt,outcome)
        owner=next(iter(self.transport.public_contexts.values()))
        self.assertTrue(owner.review.proof)
        self.assertEqual(len(owner.endpoint.protection.proofs),3)
        self.assertTrue(all(p['passed'] for p in owner.endpoint.protection.proofs))
        self.assertFalse(self.transport.originals.owned)
        self.assertEqual(self.package.fast_tier.flags,frozen)
        commands=[json.loads(p.read_text())['argv'] for p in self.area.rglob('launch.json')]
        self.assertEqual(len(commands),3)
        self.assertTrue(all('service_tier="fast"' in c and 'features.fast_mode=true' in c for c in commands))
        self.put(self.area/'fast-tier','false\n')
        # The live switch changes future selections; this exact endpoint keeps
        # its original snapshot even for a later resume command.
        argv=owner.endpoint.execution.prepare(['/fiction','--model','gpt-xhigh'],owner.context['profile'])
        self.assertIn('service_tier="fast"',argv)
        _,force=live_fast.snapshot(self.store,self.attempt,self.package)
        self.assertFalse(force)
        with patch.object(self.package.dispatch,'load_config',return_value=({},'fiction')),patch.object(self.package.dispatch,'resolve',return_value={'provider':'codex','model':'fiction','effort':'fixture'}):
            fresh=self.package.dispatch.open_opaque_execution(self.store.config['execution_pool_routes'],'gpt-xhigh',owner.context['profile'],force_fast=force)
        self.assertNotIn('service_tier="fast"',fresh.prepare(['/fiction','--model','gpt-xhigh'],owner.context['profile']))
        self.assertEqual([o['exit'] for o in self.observations()],[0]*9)
        with public_owner_fixture():asyncio.run(self.executor.close('fiction',self.policy))

    def test_six_module_contract_and_changed_helper_refuse_before_loading(self):
        self.fixture()
        legacy=copy.deepcopy(self.policy)
        value=legacy['continuing'];value['version']=review_composition.RUNTIME_VERSION
        value.pop('fast_tier');value['source_files'].pop('fast_tier.py')
        with self.assertRaisesRegex(Refusal,'v4 dependency'):review_composition.source_bodies(self.store,self.attempt,legacy)
        wrong=copy.deepcopy(self.policy);wrong['continuing']['source_files']['fast_tier.py']='0'*64
        with self.assertRaisesRegex(Refusal,'helper identity'):review_composition.source_bodies(self.store,self.attempt,wrong)
        self.store.config['fast_tier']['helper_sha256']='0'*64
        with self.assertRaisesRegex(Refusal,'helper changed'):live_fast.snapshot(self.store,self.attempt)

    def test_current_control_task_and_source_read_authority_are_independent(self):
        self.fixture()
        task=self.store.config['tasks']['reviews-proposer']
        task['effect_authority']['operations']=['read-reports']
        # Controller-only mutable read is not a source-reading grant.
        self.assertTrue(live_fast.snapshot(self.store,self.attempt)[1])
        with self.assertRaisesRegex(Refusal,'typed source-read'):review_composition.probe_helper(self.store,self.attempt,self.policy)
        self.store.config['fast_tier']['tasks'].remove('reviews-proposer')
        with self.assertRaisesRegex(Refusal,'control authority'):live_fast.snapshot(self.store,self.attempt)


class CurrentAnalysis(CurrentUse):
    def ordinary(self,*args,**kwargs):
        actual=appserver.thread_request
        def observed(spec,binding,force_fast=False):
            request=actual(spec,binding,force_fast)
            self.assertEqual(request['config']['service_tier'],'fast')
            self.assertEqual(request['model'],binding['model'])
            self.assertEqual(request['config']['model_reasoning_effort'],binding['effort'])
            return request
        with patch.object(appserver,'thread_request',side_effect=observed):
            return super().ordinary(*args,**kwargs)

    def prepare(self,*args,**kwargs):
        # Existing real whole-report/current-use fixtures now select the shared
        # controller binding; provider/source grants remain explicit fiction.
        with public_owner_fixture():super().prepare(*args,**kwargs)
        self.store.config['fast_tier']=control(self.area/'fast-tier',self.store.config['tasks'])
        self.put(self.area/'fast-tier','true\n')

    def fixture(self,*args,**kwargs):
        return CoalescedCaller.fixture(self,*args,**kwargs)

    def execute(self):
        with public_owner_fixture():return CurrentCaller1226.execute(self)


class GenericAcrossCheckouts(unittest.IsolatedAsyncioTestCase):
    async def test_same_owned_switch_controls_two_real_selected_helpers_and_old_peer_snapshot(self):
        root=Path(tempfile.mkdtemp(prefix='global-control-',dir='/fixtures'))
        switch=root/'fast-tier';switch.write_text('true\n')
        original=Path(appserver.__file__).parents[2]/'direct-child/fast_tier.py'
        from coordinator_runtime import live_fast as actual
        fake=root/'fake-cli'
        fake.write_text('#!'+sys.executable+'\nimport sys,json\nprint(json.dumps(sys.argv[1:]))\n');fake.chmod(0o700)
        adapters=[]
        for number in range(2):
            checkout=root/str(number);directory=checkout/'tools/direct-child';directory.mkdir(parents=True)
            (directory/'fast_tier.py').write_bytes(original.read_bytes())
            # Deliberately opposite checkout-local policies expose accidental
            # adjacent-file default use. The explicit selected shared path wins.
            (directory/'fast-tier').write_text('false\n')
            modulepath=checkout/'tools/coordinator-runtime/coordinator_runtime/live_fast.py';modulepath.parent.mkdir(parents=True)
            name='coordinator_runtime._fixture_live_'+str(number)
            spec=importlib.util.spec_from_file_location(name,actual.__file__)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.__file__=str(modulepath)
            config={'fast_tier':control(switch,['owned']), 'tasks':{'owned':{'role':'Work'}},'artifact_exclusions':[], 'codex':str(fake),'protocol_cli_version':'fiction'}
            runtime=SimpleNamespace(config=config,authorize_launch=lambda a:None,attempt=lambda a:{'job':'j'},job=lambda j:{'task':'owned'})
            adapters.append((appserver.AppServer(config),runtime,module))
        async def command(item):
            adapter,runtime,module=item
            with patch.object(appserver,'fast_policy',side_effect=module.snapshot),patch.object(appserver,'preflight',new=AsyncMock(return_value=(['-c','features.multi_agent=false'],{}))):
                return await adapter.command('.codex3',runtime=runtime,attempt='a')
        before=[await command(a) for a in adapters]
        switch.write_text('false\n')
        after=[await command(a) for a in adapters]
        for argv,facts in before+after:
            child=await asyncio.create_subprocess_exec(*argv,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            out,err=await child.communicate()
            self.assertEqual(child.returncode,0,err)
            self.assertEqual(json.loads(out),argv[1:])
        for argv,facts in before:
            self.assertIn('service_tier="fast"',argv);self.assertIn('features.multi_agent=false',argv)
            self.assertEqual(facts['served_service_tier'],'unobserved')
        for argv,facts in after:self.assertNotIn('service_tier="fast"',argv)
        spec={'cwd':str(root),'sandbox':'read-only'};binding={'model':'literal','effort':'high','provider':'openai'}
        self.assertEqual(appserver.thread_request(spec,binding,before[0][1]['force_fast'])['config']['service_tier'],'fast')
        self.assertNotIn('service_tier',appserver.thread_request(spec,binding,after[0][1]['force_fast'])['config'])
        switch.write_text('invalid\n')
        with self.assertRaises(Refusal):await command(adapters[0])
        switch.unlink();switch.symlink_to(root/'never-read')
        with self.assertRaises(Refusal):await command(adapters[0])


class ControlDraft(ReadCeiling):
    def option(self):
        switch=self.f.directory/'fast-tier';switch.write_text('true\n')
        return dict(control=control(switch,['bp','qc']),bindings={name:dict(configuration=digest(self.s.config),
            role_owner=self.s.config['tasks'][name]['effect_authority']['owner'],
            original_grant='fictional-grant-'+self.s.config['tasks'][name]['role'],
            authority='fictional explicit controller-only live read') for name in ['bp','qc']})

    def test_real_draft_current_grants_and_selected_tasks_without_QA_source_elevation(self):
        option=self.option();before=copy.deepcopy(self.s.config)
        value=configuration.candidate(self.s,str(self.f.directory/'live.json'),[],scope_options={'live_fast_control':option})
        self.assertEqual(value['fast_tier'],option['control'])
        self.assertEqual(value['tasks']['qc']['effect_authority'],before['tasks']['qc']['effect_authority'])
        self.assertNotIn('read-source',value['tasks']['qc']['effect_authority']['operations'])
        Path(value['operator_config']).write_text(json.dumps(value))
        configuration.validate_changes(self.s,value,['bp','qc'])
        with self.assertRaises(Refusal):configuration.validate_changes(self.s,value,['bp'])
        for field,bad in [('configuration','0'*64),('role_owner','foreign'),('original_grant','foreign')]:
            broken=copy.deepcopy(option);broken['bindings']['qc'][field]=bad
            with self.assertRaises(Refusal):configuration.candidate(self.s,str(self.f.directory/'bad.json'),[],scope_options={'live_fast_control':broken})
        with self.assertRaises(Refusal):configuration.candidate(self.s,str(self.f.directory/'bad.json'),[],scope_options={'live_fast_control':{**option,'bindings':{'bp':option['bindings']['bp']}}})
        self.assertEqual(self.s.config,before)


class AllEightLiveContexts(unittest.IsolatedAsyncioTestCase):
    async def test_actual_all8_attempts_and_auxiliary_classifier_use_one_shared_control(self):
        from support import config_at,enrolled,event,queued,collect,result
        from fixture_conservation import capacity
        root=Path(tempfile.mkdtemp(prefix='all8-control-',dir='/fixtures'))
        switch=root/'fast-tier';switch.write_text('true\n')
        config=config_at(root)
        config['fast_tier']=control(switch,config['tasks'])
        config['fast_tier']['auxiliary']={'classifier':['Work','Branch','Reviews','QA'],
            'diagnosis':['Work','Branch','Reviews','QA'], 'input-mapping':['Work','Branch','Reviews','QA'],
            'input-locator':['Work','Branch','Reviews','QA']}
        store=enrolled(config);self.addCleanup(store.close)
        store.admit('owned-all8-package',config['roles']['Branch']['owner'],{'evidence':'owned fictional package only'})
        adapter=appserver.AppServer(config)
        for index,(name,task) in enumerate(config['tasks'].items()):
            queued(store,event(config,'all8-'+str(index),role=task['role'],task=name,package='owned-all8-package'))
            job=store.reserve();self.assertEqual(job['task'],name)
            attempt=store.start_job(job['id'],job['token'])
            with patch.object(appserver,'preflight',new=AsyncMock(return_value=([],{}))):
                argv,facts=await adapter.command('.codex3',runtime=store,attempt=attempt)
            self.assertIn('service_tier="fast"',argv)
            collect(store,attempt,result());store.finish_job(job['id'],job['token'])
        for index,role in enumerate(['Work','Branch','Reviews','QA']):
            message=event(config,'aux-'+str(index),role=role,task=config['roles'][role]['routes'][0],package='owned-all8-package')
            store.ingest(message);attempt,actual=store.claim_classification()
            self.assertIsNone(store.attempt(attempt)['job'])
            self.assertTrue(live_fast.snapshot(store,attempt)[1])
            config['fast_tier']['auxiliary']['classifier'].remove(role)
            with self.assertRaisesRegex(Refusal,'auxiliary'):live_fast.snapshot(store,attempt)
            config['fast_tier']['auxiliary']['classifier'].append(role)
            collect(store,attempt,dict(event_id=actual['id'],task=actual['allowed_tasks'][0],package=actual['package'],reason='authored classification'))
            store.commit_classification(attempt);store.ack_state(actual['id'],'internal')
        self.assertEqual(set(config['fast_tier']['tasks']),set(config['tasks']))
