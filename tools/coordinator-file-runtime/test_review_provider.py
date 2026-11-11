"""Decision16 fixed public processes: no provider, profiles or operating roles.

Separate from the accepted software-QA client and its fixed test oracles.
All synthetic state, failures and process evidence are retained by the caller.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import provider
import test_provider as fixtures
from test_runtime import ARTIFACTS, TOKENS, call, check_capacity, _sql_attempts
from provider import Codex, run_provider
from storage import Held, digest


CONTRACT = 'fresh-current-component-v1'
FIXED_REVIEW = r'''
import json, sys
args = sys.argv[1:]
if 'mcp' in args:
    disabled = any('enabled=false' in x for x in args)
    rows = [{'name':'alpha','enabled':not disabled}]
    if disabled: rows.append({'name':'openaiDeveloperDocs','enabled':False})
    if '--bad-mcp' in args: rows[0]['enabled'] = True
    print(json.dumps(rows)); sys.exit(0)
envelope = json.load(sys.stdin)
binding = envelope['review_execution']
task = json.loads(envelope['task'])
# This is a declared fictional binding, never a real model identity check.
assert args[args.index('--model') + 1] == 'fixture-opaque-binding'
assert 'service_tier="fast"' in args
assert 'resume' not in args and '--ephemeral' in args
if task.get('mode') == 'multiple':
    print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'{}'}}))
result = {'association': binding, 'task': task}
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps(result)}}))
sys.exit(17 if task.get('mode') == 'failure' else 0)
'''


class ReviewProviderTrial(unittest.TestCase):
    setUp = fixtures.ProviderTrial.setUp
    raw = fixtures.ProviderTrial.raw
    ingest = fixtures.ProviderTrial.ingest
    classify = fixtures.ProviderTrial.classify
    reserve = fixtures.ProviderTrial.reserve
    collect = fixtures.ProviderTrial.collect
    prepare = fixtures.ProviderTrial.prepare
    run_entry = fixtures.ProviderTrial.run_entry

    def branch(self, branch='b', incarnation='current-1'):
        call(self.rt, 'branch', 'branch', branch=branch, repository='public-fixture',
             ref='WORK-fixture', incarnation=incarnation, root='fixture-holder', basis='current public source')

    def review(self, review='r', **extra):
        fields = dict(component='runtime-provider', branch='b', opaque_contract='gpt-xhigh',
                      context='current-context-' + review, history='authored-history-' + review,
                      execution_contract=CONTRACT)
        fields.update(extra)
        return call(self.rt, 'review', 'reviews', review=review, **fields)

    def configure_opaque(self, selection='present'):
        # Add a complete fictional public dispatch schema before constructing a
        # fresh fixture runtime. Never read the real routes/alias/account stores.
        # Rebinding only this freshly created synthetic state is fixture input.
        alias = ('\n[aliases.gpt-xhigh]\nprovider="codex"\nmodel="fixture-opaque-binding"\neffort="xhigh"\n')
        if selection == 'missing': alias = ''
        if selection == 'incompatible':
            alias = ('\n[providers.claude]\npool=["claude5"]\nmanual_profiles=["claude5"]\nefforts=["xhigh"]\n'
                     '[aliases.gpt-xhigh]\nprovider="claude"\nmodel="fixture-incompatible"\neffort="xhigh"\n')
        self.routes.write_text(self.routes.read_text().replace('efforts = ["low", "xhigh"]',
            'efforts = ["low", "high", "max", "xhigh"]') + alias +
            '[classes.unknown]\nroute="refine"\nrequires_basis=false\n'
            '[seats.observer]\nroute="refine"\n[legacy]\nroute="refine"\n')
        with self.rt.files.transaction() as state:
            state['pool_binding'] = self.rt.pool(state).control_binding(self.routes.read_bytes())

    def prepare_review(self, review='r', attempt='review-call', event='review-event', **task):
        self.classify(event, owner='reviews')
        state = self.raw()
        branch = state['reviews'][review]['branch']
        resources = {'review:' + review: 'write', 'branch:' + branch: 'read'}
        basis = {key: state['versions'].get(key, 0) for key in resources}
        r = call(self.rt, 'reserve', 'reviews', attempt=attempt, event=event, phase='review',
                 resources=resources, basis=basis, review=review)
        self.script = self.root / ('fixed-' + attempt + '.py')
        self.script.write_text(FIXED_REVIEW)
        self.adapter = Codex([sys.executable, '-I', str(self.script)])
        return dict(attempt=attempt, collector=r['collector'], prompt=json.dumps(task),
                    cwd=str(self.root), output_limit=16384, timeout=2, declared_secrets=[])

    def setup_review(self, **task):
        self.configure_opaque()
        self.branch()
        self.review()
        return self.prepare_review(**task)

    def test_selected_review_uses_opaque_boundary_and_current_associations(self):
        request = self.setup_review(question='independently examine current public material')
        turn = (self.root / 'rotation/codex.counter').read_bytes()
        self.assertEqual(self.run_entry(request, 'reviews')['end'], 0)
        a = self.raw()['attempts']['review-call']
        binding = a['result']['association']
        self.assertEqual(binding['component'], 'runtime-provider')
        self.assertEqual(binding['opaque_contract'], 'gpt-xhigh')
        self.assertEqual(binding['context'], 'current-context-r')
        self.assertEqual(binding['history'], 'authored-history-r')
        self.assertEqual(binding['branch']['incarnation'], 'current-1')
        self.assertEqual(binding['resources'], a['resources'])
        self.assertEqual(binding['basis'], a['basis'])
        self.assertEqual(a['provider_report']['review_execution']['association_sha256'], digest(binding))
        self.assertEqual(a['provider_report']['review_execution']['selector'], 'gpt-xhigh')
        self.assertNotIn('fixture-opaque-binding', json.dumps(a['provider_report']))
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0, 0])
        self.assertEqual((self.root / 'rotation/codex.counter').read_bytes(), turn)
        self.assertEqual(_sql_attempts, [])

    def test_successor_and_same_record_calls_are_fresh_with_explicit_history(self):
        request = self.setup_review()
        self.run_entry(request, 'reviews')
        call(self.rt, 'reconcile', 'reviews', attempt=request['attempt'], collector=request['collector'],
             evidence='fixed process complete; no external effects or semantic acceptance')
        self.review('next', predecessor='r')
        request = self.prepare_review('next', 'next-call', 'next-event')
        self.run_entry(request, 'reviews')
        binding = self.raw()['attempts']['next-call']['result']['association']
        self.assertEqual(binding['predecessor']['review'], 'r')
        self.assertEqual(binding['predecessor']['context'], 'current-context-r')
        self.assertEqual(binding['predecessor']['history'], 'authored-history-r')
        call(self.rt, 'reconcile', 'reviews', attempt=request['attempt'], collector=request['collector'], evidence='fixed no effects')
        request = self.prepare_review('next', 'follow-on', 'follow-event')
        self.run_entry(request, 'reviews')
        binding = self.raw()['attempts']['follow-on']['result']['association']
        self.assertEqual(binding['prior_calls'], ['next-call'])
        self.assertEqual(self.raw()['reviews']['next']['calls'], ['next-call', 'follow-on'])
        self.assertTrue(self.raw()['attempts']['follow-on']['provider_report']['review_execution']['fresh'])

    def test_legacy_unknown_and_unselected_contracts_remain_unstarted(self):
        self.branch()
        for review, fields in [('legacy', {'execution_contract': None}),
                               ('unknown', {'execution_contract': None, 'opaque_contract': 'unknown-owner-selector'})]:
            self.review(review, **fields)
            request = self.prepare_review(review, 'call-' + review, 'event-' + review)
            with self.assertRaises(Held): self.run_entry(request, 'reviews')
            self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')
            self.assertFalse(self.adapter.originals)

    def test_unknown_execution_or_wrong_selector_cannot_select_new_contract(self):
        self.branch()
        for fields in [dict(execution_contract='unknown-execution'), dict(opaque_contract='technical-sol-xhigh')]:
            with self.assertRaises(Held): self.review('invalid', **fields)
            self.assertNotIn('invalid', self.raw()['reviews'])

    def test_missing_or_incompatible_public_binding_has_no_fallback_or_original(self):
        request = self.setup_review()
        # The exact public opaque boundary must be entered; its refusal cannot
        # be replaced with technical refine, a second turn or a task process.
        with patch('provider.opaque_task_flags', side_effect=Held('synthetic unavailable opaque capability')):
            with self.assertRaises(Held): self.run_entry(request, 'reviews')
        a = self.raw()['attempts'][request['attempt']]
        self.assertEqual(a['state'], 'not-started')
        self.assertIsNone(a['end'])
        self.assertFalse(self.adapter.originals)
        with self.assertRaises(Held): self.run_entry(request, 'reviews')

    def test_actual_public_boundary_refuses_missing_alias(self):
        self.configure_opaque('missing')
        self.branch(); self.review()
        request = self.prepare_review()
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')
        self.assertFalse(self.adapter.originals)

    def test_actual_public_boundary_refuses_incompatible_capability(self):
        self.configure_opaque('incompatible')
        self.branch(); self.review()
        request = self.prepare_review()
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')
        self.assertFalse(self.adapter.originals)

    def test_current_creation_guards_and_effective_mcp_still_apply(self):
        request = self.setup_review()
        create = self.adapter.create
        def revoked(*args, **kw):
            if self.adapter.stage == 'task':
                call(self.rt, 'revoke', target='reviews', reason='fixture authority ended')
            return create(*args, **kw)
        self.adapter.create = revoked
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        a = self.raw()['attempts'][request['attempt']]
        self.assertEqual(a['state'], 'not-started')
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0])

    def test_review_pool_fast_and_static_changes_refuse_before_task(self):
        for change in ['pool', 'fast', 'static']:
            with self.subTest(change=change):
                self.setUp()
                request = self.setup_review()
                create = self.adapter.create
                def changed(*args, **kw):
                    if self.adapter.stage == 'task':
                        if change == 'pool': fixtures._pool.Pool(self.routes).set([])
                        if change == 'fast': fixtures._fast.set_policy('false', self.root / 'fast-tier')
                        if change == 'static': self.routes.write_text(self.routes.read_text() + '\n# fixture change\n')
                    return create(*args, **kw)
                self.adapter.create = changed
                with self.assertRaises(Held): self.run_entry(request, 'reviews')
                self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0])
                self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')

    def test_mcp_refusal_withholds_review_task(self):
        request = self.setup_review()
        self.adapter.command.append('--bad-mcp')
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0])
        self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')

    def test_failure_keeps_original_truth(self):
        request = self.setup_review(mode='failure')
        self.assertEqual(self.run_entry(request, 'reviews')['end'], 17)
        a = self.raw()['attempts'][request['attempt']]
        self.assertTrue(a['provider_report']['final_complete'])
        self.assertFalse(a['reconciled'])
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0, 17])

    def test_incomplete_final_is_not_review_success(self):
        request = self.setup_review(mode='multiple')
        self.run_entry(request, 'reviews')
        a = self.raw()['attempts'][request['attempt']]
        self.assertEqual(a['end'], 0)
        self.assertFalse(a['provider_report']['final_complete'])
        self.assertEqual(a['result'], {'provider_incomplete': True})

    def test_envelope_is_bounded_and_association_secrets_are_refused(self):
        request = self.setup_review()
        request['prompt'] = 'x' * 16384
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        self.assertFalse(self.adapter.originals)
        self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')

    def test_association_secrets_refuse_without_rewriting_references(self):
        request = self.setup_review()
        request['declared_secrets'] = ['current-context-r']
        with self.assertRaises(Held): self.run_entry(request, 'reviews')
        self.assertFalse(self.adapter.originals)
        self.assertEqual(self.raw()['reviews']['r']['context'], 'current-context-r')
        self.assertEqual(self.raw()['attempts'][request['attempt']]['state'], 'not-started')

    def test_lost_report_reply_keeps_actual_end_without_relaunch(self):
        request = self.setup_review()
        original = self.rt.call
        def lost(op, *args, **kw):
            result = original(op, *args, **kw)
            if op == 'provider_report': raise Held('fixture lost committed reply')
            return result
        with patch.object(self.rt, 'call', lost):
            with self.assertRaises(Held): self.run_entry(request, 'reviews')
        a = self.raw()['attempts'][request['attempt']]
        self.assertEqual(a['state'], 'launching')
        self.assertIsNone(a['end'])
        self.assertEqual(a['provider_report']['processes'][-1]['end'], 0)
        self.assertEqual([p.returncode for p in self.adapter.originals], [0, 0, 0])
        with self.assertRaises(Held): self.run_entry(request, 'reviews')

    def test_declared_secrets_stay_out_of_review_task_and_publication(self):
        request = self.setup_review(note='public-declared-secret')
        request['declared_secrets'] = ['public-declared-secret']
        self.run_entry(request, 'reviews')
        result = self.raw()['attempts'][request['attempt']]['result']
        self.assertEqual(result['task']['note'], '[REDACTED]')
        self.assertNotIn('public-declared-secret', json.dumps(self.raw()))

    def test_branch_review_overlap_responsive_intake_and_addressed_return(self):
        review_request = self.setup_review()
        review_adapter = self.adapter
        self.branch('other', 'current-2')
        self.classify('build', owner='branch')
        reserved = call(self.rt, 'reserve', 'branch', attempt='builder', event='build', phase='known',
                        point='build', branch='other', resources={'point:build': 'write', 'branch:other': 'write'},
                        basis={'point:build': 0, 'branch:other': 0})
        script = self.root / 'fixed-builder.py'
        script.write_text(fixtures.FIXED)
        builder = Codex([sys.executable, '-I', str(script)])
        build_request = dict(attempt='builder', collector=reserved['collector'], prompt='{}',
                             cwd=str(self.root), output_limit=8192, timeout=2, declared_secrets=[])
        real_drain = provider.drain
        overlap = []
        def while_review_waits(process, *args):
            if process in review_adapter.originals and review_adapter.stage == 'task':
                self.assertIsNone(process.poll())
                self.ingest('responsive-intake')
                states = self.raw()['attempts']
                overlap.append(states['review-call']['state'])
                run_provider(self.rt, 'branch', TOKENS['branch'], build_request, adapter=builder)
            return real_drain(process, *args)
        with patch('provider.drain', while_review_waits): self.run_entry(review_request, 'reviews')
        self.assertEqual(overlap, ['launching'])
        self.assertEqual([p.returncode for p in builder.originals], [0, 0, 0])
        self.assertEqual([p.returncode for p in review_adapter.originals], [0, 0, 0])
        call(self.rt, 'send', 'reviews', packet='review-result', event='review-event', recipient='work',
             payload={'attempt':'review-call', 'scope':'fixed public fixture only'})
        self.assertEqual(call(self.rt, 'inbox')['packets'][0]['id'], 'review-result')
        for stage in ['picked-up', 'processed', 'settled']:
            call(self.rt, 'receipt', packet='review-result', stage=stage, evidence='fixture recipient ' + stage)
        self.assertFalse(self.raw()['events']['responsive-intake']['ack'])

    def test_cli_fresh_reviews_with_sql_blocked_and_fixed_public_process(self):
        request = self.setup_review(question='fixture CLI review')
        directory = Path(__file__).resolve().parent
        wrapper = '''
import builtins, pathlib, runpy, sys
directory, script, state = sys.argv[1:]
original_import = builtins.__import__
def no_sql(name, *args, **kwargs):
    if name.split('.')[0] in {'sqlite3','_sqlite3'}: raise RuntimeError('SQL forbidden')
    return original_import(name,*args,**kwargs)
builtins.__import__ = no_sql
sys.path.insert(0,directory)
import provider
factory = provider.Codex
provider.Codex = lambda: factory([sys.executable,'-I',script])
sys.argv = [str(pathlib.Path(directory)/'coordinator.py'),'--state',state,'--actor','reviews','run-provider']
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', wrapper,
                                    str(directory), str(self.script), str(self.path)],
                                   env={'PATH':os.defpath, 'COORDINATOR_TOKEN':TOKENS['reviews'],
                                        'PYTHONDONTWRITEBYTECODE':'1'},
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print('ORIGINAL_FIXED_REVIEW_CLI', process.pid, flush=True)
        out, err = process.communicate(json.dumps(request).encode(), timeout=10)
        print('FIXED_REVIEW_CLI_END', process.pid, process.returncode, flush=True)
        self.assertEqual(process.returncode, 0, err)
        self.assertEqual(json.loads(out)['result']['end'], 0)
        a = self.raw()['attempts'][request['attempt']]
        self.assertEqual([p['end'] for p in a['provider_report']['processes']], [0, 0, 0])
        self.assertEqual(a['result']['association']['opaque_contract'], 'gpt-xhigh')


if __name__ == '__main__':
    check_capacity(ARTIFACTS.parent, 8 * 1024**2, 2048)
    ARTIFACTS.mkdir(mode=0o700, parents=True, exist_ok=False)
    unittest.main(verbosity=2)
