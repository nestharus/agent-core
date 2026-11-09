"""Fictional provider integration through the actual selected caller and Store.

All emitted provider/tool results are authored fiction. Real local subprocess
waits, exports, publication and original finalizers are exercised. These tests
grant no actual account, service, receiving or native authority.
"""
import asyncio
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import patch

from coordinator_runtime import reviews, opaque_review, review_composition, processing, branches
from coordinator_runtime.contracts import Refusal, encode, digest
from support import config_at, enrolled, event, queued
from fixture_conservation import capacity

THREAD = '00000000-0000-4000-8000-000000001226'
ROOT = '00000000-0000-4000-8000-000000001227'
BUILDER = '00000000-0000-4000-8000-000000001228'

CLI = r"""#!/usr/bin/python3
import json,sys
from pathlib import Path
mode=MODE
denied={'allowed':{'read':'owned-allowed-canary'},'outside':{'error':13},
        'write':{'error':13},'network':{'error':13}}
if 'sandbox' in sys.argv:
 print(json.dumps(denied),flush=True)
 raise SystemExit(0)
prompt=sys.stdin.read()
print(json.dumps({'type':'thread.started','thread_id':THREAD_VALUE}),flush=True)
if 'sole owned nonsecret tool-protection qualification turn' in prompt:
 expected='/usr/bin/python3 -c '+prompt.split('\n/usr/bin/python3 -c ',1)[1].split('\nSelected immutable material is at ',1)[0]
 row=dict(denied)
 if mode=='adverse':row['write']='succeeded'
 item={'type':'command_execution','command':expected,'exit_code':0,'status':'completed','aggregated_output':json.dumps(row)}
 print(json.dumps({'type':'item.completed','item':item}),flush=True)
 if mode=='duplicate':
  print(json.dumps({'type':'item.completed','item':item}),flush=True)
 answer='Fictional qualification evidence; no actual provider protection claimed'
else:
 if mode=='malformed':
  print('not-json',flush=True)
  raise SystemExit(0)
 answer=json.dumps({'semantic':'DONE','summary':'fictional situated account',
  'report':'fictional full observation, dissent and limits','history_entry':'fictional source-bound history',
  'stage':'complete' if 'Continue the remaining' in prompt else 'architecture',
  'coverage':{'families':FAMILIES_VALUE,'core_files_not_read':['fictional method efficacy'],
   'observations':[],'answered_ids':[],'limits':['provider and all tool evidence are authored fiction']}})
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':answer}}),flush=True)
print(json.dumps({'type':'turn.completed'}),flush=True)
"""


class CurrentCaller1226(unittest.TestCase):
    def setUp(self):
        capacity(Path('/fixtures'))
        self.area = Path(tempfile.mkdtemp(prefix='caller1226-', dir='/fixtures'))
        self.store = None
        self.member = None
        self.active = True
        self.now = time.time()
        self.auth_calls = 0

    def tearDown(self):
        # The qualification recorder conserves this entire fixture before here.
        if self.store is not None:
            self.store.processing = None
            self.store.close()
        if self.member is not None:
            self.member.close()

    def put(self, path, body):
        capacity(path.parent)
        path.write_text(body)
        return path

    def git(self, *args):
        capacity(self.area)
        return subprocess.check_output(['git', '-C', str(self.area), *args], stderr=subprocess.DEVNULL).decode().strip()

    def fixture(self, mode='normal', branch=False, shared_actor=False):
        config = config_at(self.area)
        self.git('init', '-q', '-b', 'fixture')
        self.put(self.area/'fiction.txt', 'nonsecret independent source fixture\n')
        self.git('add', '--', 'fiction.txt')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '--no-gpg-sign', '-qm', 'nonsecret fictional specimen')
        self.git('remote', 'add', 'origin', 'https://example.invalid/fiction')
        head = self.git('rev-parse', 'HEAD')
        directory = Path(review_composition.__file__).parents[2]/'direct-child'
        config['tasks']['reviews-proposer'].update(execution='owner', capacity=5, binding=dict(opaque_review.BINDING))
        config['tasks']['reviews-proposer']['effect_authority']['read_roots'].append(str(directory))
        config['tasks']['reviews-proposer']['responses']['consolidated'] = ['reviews-integrator']
        config['limits']['max_bytes'] = 400*1024**2
        capacity(self.area)
        self.store = enrolled(config, clock=lambda:self.now)
        self.packet = dict(component='fiction', origin='https://example.invalid/fiction',
                           base=head, head=head, previous=None, answered_ids=[])
        method = self.put(self.area/'procedure.md', 'Fictional method input, never actual efficacy.\n')
        body = CLI.replace('MODE', repr(mode)).replace('THREAD_VALUE', repr(THREAD))
        body = body.replace('FAMILIES_VALUE', repr({f:'partial' for f in reviews.FAMILIES}))
        self.executable = self.put(self.area/'fiction-cli', body)
        self.executable.chmod(0o700)
        source_files = {name+'.py':reviews.sha((directory/(name+'.py')).read_bytes())
                        for name in review_composition.MODULES}
        raw = Path(config['execution_pool_routes']).read_bytes()
        control = self.store.execution_pool.pool.control_binding(raw)
        self.policy = dict(transport=opaque_review.VERSION, launcher_sha256=source_files['review_context.py'],
            executable=str(self.executable), deadline=120, method=str(method),
            method_files={str(method):reviews.sha(method.read_bytes())}, method_closure='unified-definitions-v1',
            components={'fiction':dict(repository=str(self.area), origin=self.packet['origin'], paths=['fiction.txt'],
                history=str(self.store.home/'review-history/fiction'), authority='owned fictional source only',
                situation=dict(actors='fictional independent actors', environment='offline owned test',
                    goals='preserve source meaning and original custody', conflicts='latency and coverage',
                    constraints='no actual provider or operating effects'))},
            continuing=dict(version=review_composition.VERSION, source_files=source_files,
                pool_control=control, runtime_reads=[str(self.executable)],
                executable_sha256=reviews.sha(self.executable.read_bytes()), capture_max=4*1024**2,
                allowance_bytes=64*1024**2, allowance_entries=2000))
        self.selected = dict(tasks=list(config['tasks']), service=dict(
            reviews={'reviews-proposer':self.policy}, legacy_resources={}, report_tasks=['reviews-integrator']))
        self.access = SimpleNamespace(key='fictional-current-capability', current=lambda:(
            {'issuer':config['roles']['Work']['owner']}, self.selected),
            reserve=lambda *a:'fictional-current-capability', authorize=self.authorize,
            role=lambda *a:True, event=lambda *a:True, task=lambda *a:True, owed_control=lambda *a:False)
        self.access.review_task = MethodType(processing.Access.review_task, self.access)
        binding = None
        if branch:
            self.store.admit('fictional-package', config['roles']['Branch']['owner'], {'evidence':'owned fiction'})
            self.store.processing = self.access
            self.member = sqlite3.connect(self.area/'membership.sqlite')
            self.member.execute('CREATE TABLE sessions(session,status,role,profile)')
            self.member.execute('INSERT INTO sessions VALUES(?,?,?,?)',
                                (THREAD if shared_actor else ROOT, 'active', 'root', '.codex2'))
            self.member.row_factory = sqlite3.Row
            @contextmanager
            def opened(**options):
                yield self.member
            self.access.boards = {'Work':SimpleNamespace(opened=opened)}
            receipt = dict(id='fictional-branch', repository=str(self.area), origin=self.packet['origin'],
                ref='refs/heads/fixture', incarnation='fictional-incarnation', scope='fictional-package',
                root=THREAD if shared_actor else ROOT, authority='fictional Work-selected branch duty')
            branches.register(self.store, config['roles']['Work']['owner'], receipt)
            branches.accept(self.store, receipt['id'], receipt['root'], 'fictional active membership and delegation')
            branches.link(self.store, receipt['id'], receipt['root'], dict(address=BUILDER,
                identity_kind='fictional-builder', profile='.codex2', collector=receipt['root'], evidence='owned fiction'))
            binding = receipt['id']
            self.store.processing = None
        message = event(config, 'review', role='Reviews', task='reviews-proposer',
                        package='fictional-package' if branch else None)
        message['body'] = {'review':self.packet}
        if binding:
            message['branch_binding'] = binding
        queued(self.store, message)
        self.job = self.store.reserve()
        self.store.processing = self.access
        self.transport = reviews.Native()
        self.executor = reviews.Executor(self.store, self.transport)
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])
        paths, bodies = review_composition.source_bodies(self.store, self.attempt, self.policy)
        self.package = review_composition.modules(paths, bodies)

    def authorize(self, *args):
        self.auth_calls += 1
        if not self.active:
            raise Refusal('fictional current authority revoked')

    def execute(self):
        # Only ordinary provider resolution and the defining-method fixture are
        # fictional seams. Native.call, protected factory, Context, Originals,
        # actual pool admission, source snapshot and Store publisher are real.
        with (patch.object(self.package.dispatch, 'load_config', return_value=({}, 'fiction')),
             patch.object(self.package.dispatch, 'resolve', return_value={
                 'provider':'codex','model':'fictional-binding','effort':'fictional-effort'}),
             patch.object(reviews, 'method_files', return_value=self.policy['method_files'])):
            return asyncio.run(self.executor.execute(self.store.job(self.job['id']), self.attempt,
                                                      self.policy, self.packet))

    def observations(self):
        return json.loads(self.store.attempt(self.attempt)['detail']).get('original_end_observations', [])

    def test_factory_qualifies_before_material_and_uses_same_original_for_both_stages(self):
        self.fixture()
        outcome = self.execute()
        self.store.collect(self.attempt, outcome)
        proof = reviews.collected_proof(self.store, self.store.job(self.job['id']), self.store.attempt(self.attempt))
        self.assertEqual(proof['kind'], 'selected-opaque-cli-review')
        self.assertFalse(proof['native_owner_execution'])
        self.assertEqual([t['receipt']['input'] for t in proof['calls']], [1,2])
        self.assertEqual({t['receipt']['thread'] for t in proof['calls']}, {THREAD})
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertEqual(owner.review.ownership.created, owner.context['created'])
        qualification = owner.endpoint.receipts[0]
        self.assertEqual([m['label'] for m in qualification['material']], ['nonsecret qualification'])
        for turn in proof['calls']:
            self.assertTrue(opaque_review.qualified(turn['receipt']))
            self.assertTrue(any(m['label'].startswith('source:') for m in turn['receipt']['material']))
        self.assertEqual([o['kind'] for o in self.observations()].count('owned-sandbox-control'), 6)
        self.assertEqual([o['kind'] for o in self.observations()].count('opaque-cli-process'), 3)
        self.assertTrue(all(type(o['exit']) is int and o['evidence_complete'] for o in self.observations()))
        self.assertFalse(self.transport.originals.owned)
        self.assertGreater(self.auth_calls, 10)
        asyncio.run(self.executor.close('fiction', self.policy))
        self.assertEqual(self.store.one('SELECT state FROM review_contexts')['state'], 'closed')
        self.assertIsNone(json.loads(self.store.one('SELECT receipt FROM review_calls')['receipt'])[-1]['close_actual_END'])

    def correction(self):
        message = event(self.store.config, 'correction', role='Reviews', task='reviews-proposer')
        self.packet = {**self.packet, 'previous':self.packet['head']}
        message['body'] = {'review':self.packet}
        queued(self.store, message)
        self.job = self.store.reserve()
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])

    def test_pool_removal_preserves_original_account_creation_collector_and_continuation(self):
        self.fixture()
        first = self.execute()
        self.store.collect(self.attempt, first)
        owner = next(iter(self.transport.public_contexts.values()))
        ownership = owner.review.ownership
        self.store.execution_pool.pool.set(['.codex5'])
        self.correction()
        outcome = self.execute()
        self.assertEqual(outcome['exit'], 0)
        self.assertIs(next(iter(self.transport.public_contexts.values())), owner)
        self.assertIs(owner.review.ownership, ownership)
        self.assertEqual(self.store.attempt(self.attempt)['profile'], ownership.profile)
        self.assertEqual([r['input'] for r in owner.endpoint.receipts], [0,1,2,3,4])
        self.assertEqual({r['thread'] for r in owner.endpoint.receipts}, {THREAD})
        self.assertEqual(self.store.execution_pool.pool.status()['enabled'], ['.codex5'])
        self.assertFalse(self.transport.originals.owned)

    def test_removed_new_profile_refuses_at_actual_process_creation_admission(self):
        self.fixture()
        self.store.execution_pool.pool.set(['.codex5'])
        with self.assertRaisesRegex(Refusal, 'profile disabled before launch'):
            self.execute()
        self.assertFalse(any(o['kind']=='opaque-cli-process' for o in self.observations()))
        self.assertFalse(self.transport.originals.owned)
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertIsNone(owner.review.proof)

    def test_original_lifetime_expires_without_renewal_or_new_context(self):
        self.fixture()
        outcome = self.execute()
        self.store.collect(self.attempt, outcome)
        owner = next(iter(self.transport.public_contexts.values()))
        ownership = owner.review.ownership
        self.correction()
        self.now = ownership.expires
        with self.assertRaisesRegex(ValueError, 'lifetime'):
            self.execute()
        self.assertIs(next(iter(self.transport.public_contexts.values())), owner)
        self.assertIs(owner.review.ownership, ownership)
        self.assertEqual(len(owner.endpoint.receipts), 3)
        self.assertFalse(self.transport.originals.owned)

    def test_persisted_proof_failure_withholds_actual_factory_substantive_turn(self):
        self.fixture()
        actual = self.package.continuing_review.private_write
        def fail(path, body, check):
            actual(path, body, check)
            if path.name == 'acting-proof.json':
                raise OSError('fictional post-persistence failure')
        with patch.object(self.package.continuing_review, 'private_write', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'post-persistence'):
                self.execute()
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertIsNone(owner.review.proof)
        self.assertEqual(len(owner.endpoint.receipts), 1)
        self.assertTrue((owner.root/'turn-0/acting-proof.json').exists())
        self.assertFalse(self.transport.originals.owned)
        closed = asyncio.run(self.executor.close('fiction', self.policy))
        self.assertIsNone(closed['actual_END'])
        self.assertTrue(closed['receipt']['local_owner_closed'])
        self.assertEqual(closed['receipt']['observed_thread'], THREAD)

    def test_listener_finalization_failure_withholds_actual_factory_substantive_turn(self):
        self.fixture()
        actual = asyncio.start_server
        calls = []
        class Listener:
            def __init__(self, server):
                self.server, self.sockets = server, server.sockets
            def close(self):
                self.server.close()
            async def wait_closed(self):
                await self.server.wait_closed()
                raise OSError('fictional listener finalization failure')
        async def listener(*args, **options):
            server = await actual(*args, **options)
            calls.append(server)
            return Listener(server) if len(calls)==1 else server
        with patch.object(asyncio, 'start_server', side_effect=listener):
            with self.assertRaisesRegex(OSError, 'listener finalization'):
                self.execute()
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertIsNone(owner.review.proof)
        self.assertEqual(len(owner.endpoint.receipts), 1)
        self.assertFalse(self.transport.originals.owned)

    def test_local_close_keeps_unrelated_original_with_its_collector(self):
        self.fixture()
        self.execute()
        async def close_with_other_original():
            child = await asyncio.create_subprocess_exec('/usr/bin/python3', '-c', 'pass',
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            async def finish(entry):
                entry['evidence'] = {'scope':'separate owned fictional metadata process; no pipe capture'}
            key = self.transport.originals.own(child, 'preflight-metadata', finish,
                lambda observed:self.store.record_original_end(self.attempt, observed))
            await self.executor.close('fiction', self.policy)
            self.assertIn(key, self.transport.originals.owned)
            self.assertEqual(await self.transport.originals.finish(key, 3), 0)
        asyncio.run(close_with_other_original())
        self.assertFalse(self.transport.originals.owned)
        self.assertEqual(self.store.one('SELECT state FROM review_contexts')['state'], 'closed')

    def test_actual_branch_root_builder_and_reviewer_remain_separate(self):
        self.fixture(branch=True)
        outcome = self.execute()
        self.assertEqual(outcome['exit'], 0)
        contexts = self.store.rows("SELECT kind,address FROM branch_contexts WHERE branch='fictional-branch'")
        self.assertIn(dict(kind='builder', address=BUILDER), contexts)
        self.assertIn(dict(kind='review', address=THREAD), contexts)
        self.assertNotEqual(THREAD, ROOT)
        self.assertNotEqual(THREAD, BUILDER)

    def test_observed_root_identity_is_refused_before_source_export_to_reviewer(self):
        self.fixture(branch=True, shared_actor=True)
        with self.assertRaisesRegex(Refusal, 'separate'):
            self.execute()
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertEqual(len(owner.endpoint.receipts), 1)
        self.assertEqual([m['label'] for m in owner.endpoint.receipts[0]['material']], ['nonsecret qualification'])
        self.assertFalse(self.transport.originals.owned)

    def test_all_exact_adverse_control_events_prevent_substantive_material(self):
        self.fixture(mode='duplicate')
        with self.assertRaisesRegex(ValueError, 'uniquely attributed'):
            self.execute()
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertIsNone(owner.review.proof)
        self.assertEqual(len(owner.endpoint.receipts), 1)
        self.assertFalse(self.transport.originals.owned)

    def test_successful_write_report_is_an_adverse_control(self):
        self.fixture(mode='adverse')
        with self.assertRaisesRegex(ValueError, 'adverse'):
            self.execute()
        owner = next(iter(self.transport.public_contexts.values()))
        self.assertIsNone(owner.review.proof)
        self.assertEqual(len(owner.endpoint.receipts), 1)

    def test_current_revocation_refuses_without_context_or_export(self):
        self.fixture()
        self.active = False
        with self.assertRaisesRegex(Refusal, 'revoked'):
            self.execute()
        self.assertFalse(self.transport.public_contexts)
        self.assertFalse(self.observations())

    def test_excluded_dependency_refuses_before_read_even_when_source_is_cached(self):
        self.fixture()
        source = str(Path(review_composition.__file__).parents[2]/'direct-child/opaque_dialogue.py')
        self.store.config['artifact_exclusions'] = [source]
        with patch.object(review_composition, 'read_file', side_effect=AssertionError('read before exclusion')):
            with self.assertRaisesRegex(Refusal, 'excluded'):
                self.execute()
        self.assertFalse(self.transport.public_contexts)

    def test_changed_dependency_pin_and_missing_composition_fail_closed(self):
        self.fixture()
        self.policy['continuing']['source_files']['opaque_dialogue.py'] = '0'*64
        with self.assertRaisesRegex(Refusal, 'dependency changed'):
            self.execute()
        self.assertFalse(self.transport.public_contexts)

    def test_missing_composition_refuses_before_new_owner(self):
        self.fixture()
        del self.policy['continuing']
        with self.assertRaisesRegex(Refusal, 'composition required'):
            self.execute()
        self.assertFalse(self.transport.public_contexts)

    def test_capacity_failure_precedes_new_owner_or_provider_launch(self):
        self.fixture()
        with patch.object(self.store, 'admit_artifact_write', side_effect=Refusal('fictional capacity exhausted')):
            with self.assertRaisesRegex(Refusal, 'capacity exhausted'):
                self.execute()
        self.assertFalse(self.transport.public_contexts)
        self.assertFalse(self.transport.originals.owned)

    def test_publication_failure_keeps_same_original_and_retries_real_store_delivery(self):
        self.fixture()
        actual = self.store.record_original_end
        refused = []
        def publish(attempt, observation):
            if not refused:
                refused.append(observation['original'])
                raise OSError('fictional publication unavailable')
            return actual(attempt, observation)
        with patch.object(self.store, 'record_original_end', side_effect=publish):
            with self.assertRaises(Exception):
                self.execute()
        self.assertEqual(len(self.transport.originals.owned), 1)
        original = refused[0]
        asyncio.run(self.transport.collect_pending(self.store))
        self.assertFalse(self.transport.originals.owned)
        self.assertTrue(any(o['original']==original for o in self.observations()))
        self.assertTrue(any(o['failures'] for o in self.observations()))

    def test_control_kind_does_not_accept_nonnumeric_or_foreign_collection(self):
        self.fixture()
        bad = dict(original='fiction', kind='owned-sandbox-control', exit=True)
        with self.assertRaises(Refusal):
            self.store.record_original_end(self.attempt, bad)
        bad['exit'] = 0
        controller = self.store.controller
        self.store.controller = 'fictional-foreign'
        with self.assertRaises(Refusal):
            self.store.record_original_end(self.attempt, bad)
        self.store.controller = controller
        self.assertFalse(self.observations())

    def test_release_binds_actual_selected_continuing_imports_and_excludes_before_acquisition(self):
        from test_release_acquisition673 import Fixture, Trace
        f = Fixture()
        f.config['tasks']['protected-review'] = dict(role='Reviews', phase='proposer',
            execution='owner', binding=dict(opaque_review.BINDING), templates=[])
        f.save()
        measured = f.release()
        for name in ('continuing_review.py','opaque_dialogue.py','profile_lease.py'):
            path = f.root/'tools/direct-child'/name
            self.assertEqual(measured['files'][str(path)], reviews.sha(path.read_bytes()))
        excluded = f.root/'tools/direct-child/opaque_dialogue.py'
        f.config['artifact_exclusions'] = [str(excluded)]
        f.save()
        with Trace(excluded) as trace:
            with self.assertRaisesRegex(f.Refusal, 'excluded before metadata'):
                f.release()
        self.assertEqual(trace.events, [])

    def test_unqualified_or_generic_proof_never_satisfies_protected_admission(self):
        self.fixture()
        receipt = dict(input=1, thread=THREAD, profile='.codex2', collector=self.store.controller)
        self.assertFalse(opaque_review.qualified(receipt))
        with self.assertRaisesRegex(ValueError, 'effective acting-boundary'):
            paths, bodies = review_composition.source_bodies(self.store, self.attempt, self.policy)
            package = review_composition.modules(paths, bodies)
            endpoint = SimpleNamespace(maximum=65536)
            owner = package.continuing_review.ContinuingReview(
                endpoint, 'gpt-xhigh', '.codex2', self.store.controller, lambda _:None)
            asyncio.run(owner.turn('substantive', {'source':b'fiction'}))

