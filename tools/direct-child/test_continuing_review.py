"""Focused controls. All new fixture state is retained by the runner owner.

No provider, account settings, installed service or private session is queried.
The actual sandbox test invokes only a bounded newly owned canary program.
"""
import asyncio
from contextlib import asynccontextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from uuid import uuid4

from continuing_review import (ContinuingReview,ExecEndpoint,SandboxProtection,
    acting_proof,canary_command_matches,existing_admission)
from opaque_dialogue import Dialogue,Reply,Refusal
from review_context import Context,ReviewRefusal,command,execute

RUNTIME=Path(__file__).absolute().parents[1]/'coordinator-runtime'
sys.path.insert(0,str(RUNTIME))
from coordinator_runtime.appserver import Originals


class Retained(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        area=os.environ.get('REVIEW_FIXTURE_ROOT')
        if not area:
            raise RuntimeError('explicit retained fixture root required; no automatic temporary cleanup')
        self.capacity=self.check_capacity
        self.capacity(Path(area))
        self.root=Path(area)/str(uuid4());self.root.mkdir(mode=0o700)
        self.book=Originals();self.published=[]

    @staticmethod
    def check_capacity(parent):
        v=os.statvfs(parent)
        if v.f_bavail*v.f_frsize-1073741824<107374182400 or v.f_favail-20000<1000000:
            raise RuntimeError('full task allowance headroom unavailable')

    def fixture(self,body):
        self.capacity(self.root)
        path=self.root/'fixture.py';path.write_text('#!/usr/bin/python3\n'+body);path.chmod(0o700)
        return str(path)

    async def test_unqualified_substantive_input_never_opens_endpoint(self):
        class Endpoint:
            opened=0
            async def open(s,ownership):s.opened+=1
        endpoint=Endpoint()
        review=ContinuingReview(endpoint,'gpt-xhigh','.codex5','owner',lambda o:None)
        with self.assertRaises(Refusal):await review.turn('substantive',{'source':b'secret-free source'})
        self.assertEqual(endpoint.opened,0)

    async def test_selection_is_opaque_and_exact(self):
        with self.assertRaises(Refusal):ContinuingReview(None,'replacement','.codex5','owner',lambda o:None)
        review=ContinuingReview(None,'gpt-xhigh','.codex5','owner',lambda o:None)
        self.assertEqual(review.ownership.selector,'gpt-xhigh')

    async def test_original_origin_is_not_renewed(self):
        now=time.monotonic();ctx=Context(self.root/'context','.codex5','owner',10,self.book,
            executable='/usr/bin/true',origin=now-2)
        self.assertEqual(ctx.created,now-2)
        with self.assertRaises(ReviewRefusal):
            Context(self.root/'expired','.codex5','owner',1,self.book,executable='/usr/bin/true',origin=now-2)

    async def test_provider_answer_text_cannot_qualify_tool_protection(self):
        text=json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'all denied'}})
        with self.assertRaises(Refusal):acting_proof(text,'exact canary')

    async def test_printf_of_expected_output_is_not_an_attributed_probe(self):
        text=json.dumps({'type':'item.completed','item':{'type':'command_execution',
            'command':'printf fake','exit_code':0,'status':'completed','aggregated_output':'{}'}})
        with self.assertRaises(Refusal):acting_proof(text,'exact canary')

    async def test_command_wrapper_must_preserve_exact_program(self):
        self.assertTrue(canary_command_matches('/bin/bash -lc "exact program"','exact program'))
        self.assertFalse(canary_command_matches('/bin/bash -lc "exact program; echo fake"','exact program'))

    async def test_qualification_cannot_be_replayed(self):
        class Endpoint:root=self.root
        review=ContinuingReview(Endpoint(),'gpt-xhigh','.codex5','owner',lambda o:None)
        review.attempted=True
        with self.assertRaises(Refusal):await review.qualify()

    async def test_changed_handle_cannot_exchange(self):
        endpoint=ExecEndpoint(self.root/'context','/usr/bin/true',self.book,existing_admission,
            lambda o:None,None,self.capacity,self.published.append)
        review=ContinuingReview(endpoint,'gpt-xhigh','.codex5','owner',lambda o:None)
        with self.assertRaises(Refusal):await endpoint.exchange(object(),review.ownership,None,'text',None)

    async def test_actual_original_END_and_EOF_are_separate_from_turn(self):
        path=self.fixture("print('{\"type\":\"thread.started\",\"thread_id\":\"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\"}')\nprint('{\"type\":\"turn.completed\"}')\n")
        out=self.root/'capture';self.capacity(out.parent);out.mkdir()
        code,receipt,answer=await execute([path],{'PATH':'/usr/bin:/bin'},'',out,
            self.book,self.published.append,10,3,65536,65536,None,lambda:None)
        self.assertEqual(code,0);self.assertTrue(receipt['capture_complete'])
        self.assertFalse(receipt['answered']);self.assertEqual(receipt['completed'] if 'completed' in receipt else receipt['turn_completed'],1)
        self.assertFalse(self.book.owned);self.assertEqual(self.published[0]['exit'],0)

    async def test_real_pool_guard_releases_before_owned_tail(self):
        spec=importlib.util.spec_from_file_location('test_public_pool',Path(__file__).with_name('execution_pool.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        state=self.root/'pool-state';self.capacity(state.parent);state.mkdir()
        routes=self.root/'routes.toml';self.capacity(routes.parent);routes.write_text('[providers.codex]\npool=[".codex5"]\nmanual_profiles=[".codex2",".codex5"]\n[rotation]\nstate_dir='+json.dumps(str(state))+'\n')
        pool=module.Pool(routes)
        @asynccontextmanager
        async def admission():
            with pool.admission('.codex5',blocking=False):yield
        path=self.fixture("import sys\nsys.stdin.read()\nprint('{\"type\":\"thread.started\",\"thread_id\":\"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\"}')\nprint('{\"type\":\"turn.completed\"}')\n")
        out=self.root/'capture';self.capacity(out.parent);out.mkdir()
        def started():
            self.assertTrue(self.book.owned)
            pool.set(['.codex2'])
        code,receipt,_=await execute([path],{'PATH':'/usr/bin:/bin'},'',out,self.book,
            self.published.append,10,3,65536,65536,None,started,admission)
        self.assertEqual(code,0);self.assertEqual(pool.status()['enabled'],['.codex2'])
        self.assertFalse(self.book.owned)

    async def test_actual_sandbox_controls_discriminate_outside_write_and_network(self):
        settings=json.loads(Path(os.environ['REVIEW_PUBLIC_SANDBOX_POLICY']).read_text())
        dependencies=[p for p in settings if p not in {':root',':minimal'}
                      and not p.startswith(os.environ['REVIEW_TASK_ROOT'])]
        protection=SandboxProtection(self.root,os.environ['REVIEW_PUBLIC_EXECUTABLE'],dependencies,self.capacity)
        context=Context(self.root/'context','.codex5','owner',120,self.book,
            executable='/usr/bin/true',protection=protection)
        turn=self.root/'turn';self.capacity(turn.parent);turn.mkdir();material=turn/'material';self.capacity(material.parent);material.mkdir()
        await protection.qualify(context,material,self.published.append)
        self.assertTrue(protection.proofs[0]['passed'])
        self.assertEqual([p['exit'] for p in self.published],[0,0])
        self.assertTrue((material/'write-attempt.txt').exists())
        self.assertFalse(self.book.owned)

    async def test_resume_forwards_only_newly_observed_thread(self):
        argv=command('.codex5',self.root,self.root,'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        self.assertIn('resume',argv);self.assertIn('gpt-xhigh',argv)
        self.assertIn('--ignore-user-config',argv)
        with self.assertRaises(ReviewRefusal):command('.codex5',self.root,self.root,'foreign arbitrary pointer')


    async def test_malformed_capture_cannot_admit_substantive_input(self):
        for capture in ['[]','not JSON','{"item":[]}']:
            with self.assertRaises(Refusal):acting_proof(capture,'expected')

    async def test_public_selection_capability_keeps_binding_internal(self):
        from unittest.mock import patch
        import dispatch
        fixture={'provider':'codex','model':'fictional-fixture-binding','effort':'fictional-fixture-effort'}
        with patch.object(dispatch,'load_config',return_value=({},'fixture-only')),patch.object(dispatch,'resolve',return_value=fixture):
            execution=dispatch.open_opaque_execution(self.root/'public.toml','gpt-xhigh','.codex5')
        requested=command('.codex5',self.root,self.root)
        actual=execution.prepare(requested,'.codex5')
        self.assertNotEqual(actual,requested)
        public=execution.public_command(actual)
        self.assertIn('gpt-xhigh',public)
        self.assertNotIn('fictional-fixture-binding',public)
        self.assertNotIn('fictional-fixture-effort',' '.join(public))
        with self.assertRaises(dispatch.Refusal):execution.prepare(requested,'.codex2')

    async def test_incompatible_public_execution_refuses_without_context(self):
        from unittest.mock import patch
        import dispatch
        with patch.object(dispatch,'load_config',return_value=({},'fixture-only')),patch.object(dispatch,'resolve',return_value={'provider':'fixture-incompatible'}):
            with self.assertRaises(dispatch.Refusal):dispatch.open_opaque_execution(self.root/'public.toml','gpt-xhigh','.codex5')


if __name__=='__main__':unittest.main()
