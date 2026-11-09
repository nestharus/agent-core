"""Real launcher/dispatcher process tests against owned fake CLIs and profiles.

All provider calls are fiction. FAST_TEST_TOOLS may select a prepared copy of
public installed sources, preserving their unrelated version differences.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_dispatch as fixture


class FastTier(unittest.TestCase):
    def setUp(self):
        self.f = fixture.DispatchTest('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        source = Path(os.environ.get('FAST_TEST_TOOLS', str(Path(__file__).resolve().parents[1])))
        tools = self.f.root / 'public-tools'
        for directory, names in {
            'direct-child': ['dispatch.py', 'profile_lease.py', 'fast_tier.py', 'fast-tier', 'execution_pool.py'],
            'direct-codex-child': ['launch.sh', 'capture_output.py'],
        }.items():
            target = tools / directory
            target.mkdir(parents=True)
            for name in names:
                origin = source / directory / name
                if origin.is_file():
                    shutil.copy2(origin, target / name)
        self.policy = tools / 'direct-child/fast-tier'
        self.dispatcher = tools / 'direct-child/dispatch.py'
        self.launcher = tools / 'direct-codex-child/launch.sh'
        self.helper = self.policy.with_name('fast_tier.py')
        active = patch.object(fixture, 'DISPATCH', self.dispatcher)
        active.start(); self.addCleanup(active.stop)

    def calls(self):
        return self.f.calls_readback() if self.f.calls.exists() else []

    def launch(self, *extra, profile='.codex2'):
        return subprocess.run([str(self.launcher), '--profile', profile,
            '--cwd', str(self.f.cwd), '--prompt', str(self.f.prompt),
            '--runs-dir', str(self.f.runs), '--id', 'fast', *extra],
            env=self.f.env, text=True, capture_output=True)

    def route(self, stdout):
        return json.loads(next(line.split('=',1)[1] for line in stdout.splitlines()
            if line.startswith('DIRECT_CHILD_ROUTE=')))

    def assert_fast(self, call):
        args = call['args']
        self.assertIn('service_tier="fast"', args)
        self.assertIn('features.fast_mode=true', args)
        self.assertIn('--dangerously-bypass-approvals-and-sandbox', args)
        self.assertIn('mcp_servers.firecrawl.enabled=false', args)
        self.assertIn('mcp_servers.openaiDeveloperDocs.enabled=false', args)
        self.assertIn('features.multi_agent=false', args)

    def test_enabled_default_selects_direct_before_native_and_records_request(self):
        result = self.f.dispatch()
        self.assertEqual(result.returncode, 0, result.stderr)
        route = self.route(result.stdout)
        self.assertEqual(route['transport_rule'], 'user-fast-tier-policy-direct')
        self.assertEqual(route['requested_service_tier'], 'fast')
        self.assertEqual(route['served_service_tier'], 'unobserved')
        self.assertFalse(any(c['tool']=='native-call' for c in self.calls()))
        execs = [c for c in self.calls() if c['args'][0]=='exec']
        self.assertEqual(len(execs),1); self.assert_fast(execs[0])
        attempt = next(self.f.runs.iterdir())
        self.assertEqual(json.loads((attempt/'route.json').read_text()), route)
        self.assertIn('force_fast=true', (attempt/'state.txt').read_text())
        self.assertIn('served_service_tier=unobserved', (attempt/'state.txt').read_text())

    def test_explicit_native_and_deadline_refuse_before_allocation_or_calls(self):
        for extra in [('--transport','native'), ('--native-deadline','30')]:
            result = self.f.dispatch(*extra)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.f.assert_no_effects()

    def test_dry_run_describes_actual_policy_and_does_not_allocate(self):
        result = self.f.dispatch('--dry-run')
        self.assertEqual(result.returncode,0,result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith('DRY RUN: {'))
        route = json.loads(line.removeprefix('DRY RUN: '))
        self.assertEqual(route['transport'],'direct')
        self.assertEqual(route['requested_service_tier'],'fast')
        self.assertIn('--expected-fast-policy true', result.stdout)
        result = self.launch('--dry-run')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('requested_service_tier=fast',result.stdout)
        self.f.assert_no_effects()

    def test_all_current_profiles_and_literal_models_keep_model_effort_and_protection(self):
        models = [('gpt-6.1-sol','high'),('gpt-6.1-terra','xhigh'),
                  ('gpt-6-astra','max'),('gpt-6-sol','medium'),('gpt-6-luna','low')]
        for index,(model, effort) in enumerate(models):
            profile = ('.codex2','.codex3','.codex4','.codex5')[index%4]
            result = self.launch('--model',model,'--effort',effort,profile=profile)
            self.assertEqual(result.returncode,0,result.stderr)
            call = [c for c in self.calls() if c['args'][0]=='exec'][-1]
            self.assert_fast(call)
            self.assertEqual(call['args'][call['args'].index('-m')+1], model)
            self.assertIn('model_reasoning_effort='+json.dumps(effort),call['args'])
            self.assertEqual(Path(call['home']).name,profile)

    def test_off_restores_native_selection_and_direct_profile_tier(self):
        result = subprocess.run([sys.executable,str(self.helper),'set','off'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        result = self.f.dispatch('--dry-run')
        self.assertEqual(result.returncode,0,result.stderr)
        route = json.loads(next(l.removeprefix('DRY RUN: ') for l in result.stdout.splitlines() if l.startswith('DRY RUN: {')))
        self.assertEqual(route['transport'],'native')
        self.assertFalse(route['force_fast'])
        result = self.launch()
        self.assertEqual(result.returncode,0,result.stderr)
        call = [c for c in self.calls() if c['args'][0]=='exec'][-1]
        self.assertFalse(any(a.startswith('service_tier=') or a.startswith('features.fast_mode=') for a in call['args']))
        result = subprocess.run([sys.executable,str(self.helper),'set','on'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.policy.read_text(),'true\n')

    def test_invalid_missing_linked_policy_and_dispatch_snapshot_refuse(self):
        for content in ('maybe\n','TRUE\n','false\ntrailing'):
            self.policy.write_text(content)
            self.assertEqual(self.f.dispatch().returncode,2)
            self.assertEqual(self.launch().returncode,2)
            self.f.assert_no_effects()
        self.policy.unlink()
        self.assertEqual(self.launch().returncode,2)
        self.policy.symlink_to(self.f.prompt)
        self.assertEqual(self.f.dispatch().returncode,2)
        self.policy.unlink();self.policy.write_text('false\n')
        self.assertEqual(self.launch('--expected-fast-policy','true').returncode,2)
        self.f.assert_no_effects()

    def test_creative_provider_keeps_route_and_reports_support_limit(self):
        result = self.f.dispatch('--dry-run','--kind','creative')
        self.assertEqual(result.returncode,0,result.stderr)
        route = json.loads(next(l.removeprefix('DRY RUN: ') for l in result.stdout.splitlines() if l.startswith('DRY RUN: {')))
        self.assertEqual((route['provider'],route['model'],route['effort']),('claude','claude-opus-5-5','high'))
        self.assertEqual(route['fast_tier_support'],'not-established-for-provider')
        self.assertEqual(route['requested_service_tier'],'profile-default')
        self.assertNotIn('service_tier=',result.stdout)
        self.f.assert_no_effects()

    def test_provider_failure_is_not_replayed(self):
        # Fake CLI exits after recording the single actual exec invocation.
        fake = self.f.bin/'codex'
        fake.write_text(fake.read_text()+"\nsys.exit(23)\n")
        result = self.f.dispatch()
        self.assertEqual(result.returncode,23,result.stderr)
        self.assertEqual(len([c for c in self.calls() if c['args'][0]=='exec']),1)
        self.assertFalse(any(c['tool']=='native-call' for c in self.calls()))

    def test_dispatcher_literal_model_profile_overrides_preserve_binding(self):
        for index, model in enumerate(('gpt-6.1-sol','gpt-6.1-terra','gpt-6-astra','gpt-6-sol','gpt-6-luna')):
            profile=('.codex2','.codex3','.codex4','.codex5')[index%4]
            result=self.f.dispatch('--model',model,'--provider','codex','--effort','xhigh',
                '--profile',profile,'--override-reason','owned policy test')
            self.assertEqual(result.returncode,0,result.stderr)
            route=self.route(result.stdout)
            self.assertEqual((route['model'],route['effort'],route['profile']),(model,'xhigh',profile))
            self.assertEqual(route['requested_service_tier'],'fast')
            self.assert_fast([c for c in self.calls() if c['args'][0]=='exec'][-1])
