"""Focused prospective protocol tests; only owned fake executable and RPC peer.

No database, provider, native route, account configuration or session is opened.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from coordinator_runtime import appserver
from coordinator_runtime.contracts import Refusal


class FastTierProtocol(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='fast-protocol-'))
        self.policy = self.root/'fast-tier'
        self.policy.write_text('true\n')
        path = Path(__file__).resolve().parents[2]/'direct-child/fast_tier.py'
        spec = importlib.util.spec_from_file_location('test_shared_fast',path)
        self.shared = importlib.util.module_from_spec(spec);spec.loader.exec_module(self.shared)
        self.shared.POLICY = self.policy
        self.config = {'codex':str(self.root/'fake-codex'), 'protocol_cli_version':'fictional-version'}
        self.argv_capture = self.root/'argv.json'
        Path(self.config['codex']).write_text('#!'+sys.executable+'\nimport sys,json\nfrom pathlib import Path\nPath('+repr(str(self.argv_capture))+').write_text(json.dumps(sys.argv[1:]))\n')
        Path(self.config['codex']).chmod(0o700)
        self.adapter = appserver.AppServer(self.config)
        active = patch.object(appserver,'fast_policy',side_effect=lambda:(self.shared,self.shared.enabled()))
        active.start();self.addCleanup(active.stop)

    async def test_actual_startup_argv_and_thread_protocol_request_preserve_controls(self):
        # Preflight metadata itself has independent tests; this keeps its actual
        # returned protection arguments while exercising the startup builder.
        controls = ['-c','mcp_servers.example.enabled=false','-c','features.multi_agent=false']
        with patch.object(appserver,'preflight',new=AsyncMock(return_value=(controls,{'mcp':'fixture-only'}))):
            argv,facts = await self.adapter.command('.codex3')
        child = await __import__('asyncio').create_subprocess_exec(*argv)
        self.assertEqual(await child.wait(),0)
        actual = json.loads(self.argv_capture.read_text())
        self.assertEqual(actual[:len(controls)],controls)
        self.assertIn('service_tier="fast"',actual)
        self.assertIn('features.fast_mode=true',actual)
        self.assertEqual(actual[-4:],['app-server','--strict-config','--listen','stdio://'])
        self.assertEqual(facts['requested_service_tier'],'fast')
        self.assertEqual(facts['served_service_tier'],'unobserved')
        calls=[]
        class Peer:
            owned_storage=None
            force_fast=facts['force_fast']
            async def send(self,value):calls.append(value)
            async def rpc(self,method,params):
                calls.append({'method':method,'params':params})
                if method=='initialize':return {'codexHome':str(Path.home()/'.codex3')}
                raise Refusal('fixture stops at actual thread/start boundary')
        class Store:
            def authorize_launch(self,attempt):pass
        spec={'cwd':str(self.root),'sandbox':'read-only','effect_authority':{'write_roots':[]}}
        binding={'model':'gpt-6.1-terra','provider':'openai','effort':'xhigh'}
        with self.assertRaisesRegex(Refusal,'fixture stops'):
            await self.adapter.session(Peer(),Store(),'owned','prompt',spec,binding,'.codex3',None,{'detail':{}})
        request=next(c['params'] for c in calls if c['method']=='thread/start')
        self.assertEqual(request['config']['service_tier'],'fast')
        self.assertTrue(request['config']['features.fast_mode'])
        self.assertEqual(request['config']['model_reasoning_effort'],'xhigh')
        self.assertEqual(request['model'],'gpt-6.1-terra')
        self.assertTrue(request['ephemeral'])
        self.assertFalse(request['allowProviderModelFallback'])
        self.assertEqual(request['approvalPolicy'],'never')
        self.assertEqual(request['sandbox'],'read-only')

    async def test_disabled_has_no_tier_overrides_and_invalid_refuses_before_preflight(self):
        self.policy.write_text('false\n')
        probe=AsyncMock(return_value=([],{}))
        with patch.object(appserver,'preflight',new=probe):
            argv,facts=await self.adapter.command('.codex4')
        self.assertFalse(any(a.startswith('service_tier=') or a.startswith('features.fast_mode=') for a in argv))
        self.assertEqual(facts['requested_service_tier'],'profile-default')
        self.policy.write_text('invalid\n')
        probe=AsyncMock()
        with patch.object(appserver,'preflight',new=probe):
            with self.assertRaises(ValueError):await self.adapter.command('.codex4')
        probe.assert_not_called()

    def test_original_request_keeps_snapshot_when_policy_changes(self):
        force=self.shared.enabled()
        self.policy.write_text('false\n')
        spec={'cwd':str(self.root),'sandbox':'read-only'}
        binding={'model':'literal-model','provider':'openai','effort':'high'}
        original=appserver.thread_request(spec,binding,force)
        new=appserver.thread_request(spec,binding,self.shared.enabled())
        self.assertEqual(original['config']['service_tier'],'fast')
        self.assertNotIn('service_tier',new['config'])
