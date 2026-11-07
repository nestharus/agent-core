"""Fresh released-source fixtures; no actual runtime or provider operations.

Run in a new /fixtures under an empty network/PID namespace, /src read-only.
SDK principals and model returns are fiction. The transition row below is
synthetic protocol state for exercising the full release fence, not adoption
evidence; grants, wake, intake, classification and ACK use production APIs.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_managed_wake658 as wake
from support import config_at
from coordinator_runtime import configuration, observations, processing
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.store import Store


def released_config(directory):
    value = config_at(directory)
    root = Path(__file__).resolve().parents[3]
    value.update(operator_cli=str(root/'tools/coordinator-runtime/coordinator'),
                 operator_config=str(Path(directory)/'current-config.json'),
                 control_receive=dict(mode='cooperative', instructions=str(
                     root/'tools/coordinator-runtime/templates/coordinator-receive.md')),
                 classification_capacity=5,
                 artifact_exclusions=[str(Path(directory)/'held'/str(i)/'capture') for i in range(56)])
    return value


class RoleModels(wake.Models):
    async def run(self, store, attempt, prompt, spec, schema):
        row = store.attempt(attempt)
        assert row['kind'] == 'classifier'
        self.calls.append(attempt)
        store.begin(attempt, {'fictional_model': True})
        store.session(attempt, ident())
        event = store.event(row['event'])
        task = ('qa-execution' if event['role'] == 'QA' else event['role'].lower()+'-proposer')
        await asyncio.sleep(0)
        return dict(exit=0, capture='complete', cleanup='done', error=None,
                    result=dict(event_id=event['id'], task=task, package=event['package'],
                                reason='Fresh fictional finding selects its existing role'),
                    detail={'fixture': True, 'resume_disposition': 'unavailable-after-ephemeral-owner-exit'})


class ReleasedWake(unittest.IsolatedAsyncioTestCase):
    register = wake.ManagedWake.register
    post = wake.ManagedWake.post
    turn = wake.ManagedWake.turn
    save_selection = wake.ManagedWake.save_selection
    asyncTearDown = wake.ManagedWake.asyncTearDown
    test_actual_service_loop_with_release_fence = wake.ManagedWake.test_actual_service_loop_binds_scans_wakes_and_drains_original
    test_current_original_grant_after_validation = wake.ManagedWake.test_unauthorized_original_grant_cannot_acquire_from_hint

    async def asyncSetUp(self):
        with patch.object(wake, 'config_at', side_effect=released_config):
            await wake.ManagedWake.asyncSetUp(self)
        self.addCleanup(self.store.close)
        Path(self.config['operator_config']).write_text(encode(self.config))
        self.release = configuration.release(self.store, self.config)
        transition = dict(basis=dict(release=self.release, tasks=list(self.config['tasks']),
                                     processing=self.selection['basis']),
                          event_boundary=0, alert_boundary=0, jobs=[], outboxes=[], collectors={})
        current = digest(self.config)
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) '
                              'VALUES(?,?,?,?,?,?,?)',
                              (current,current,current,encode(self.config),encode(transition),self.owner,self.now))
        self.models = RoleModels()
        self.dispatcher.models = self.models

    def metrics(self, name, value):
        (self.directory/(name+'.json')).write_text(encode(value))

    def post_role(self, role):
        args = self.substrate.parser().parse_args(['open','--session',self.sender,
            '--to',self.config['roles'][role]['owner'],'--topic','fixture','--kind','finding',
            '--text','Owned role finding','--title','Four-role fixture','--no-push',
            '--ref','fixture-package'])
        with self.substrate.database(str(self.path)) as conn:
            with patch.dict(os.environ,{'CODEX_SESSION_ID':self.sender}):
                self.substrate.open_thread(conn,args)

    async def test_measure_redundant_current_and_four_role_wake_dispatch(self):
        samples = []
        with observations.owning('runtime') as record:
            for _ in range(12):
                started = time.perf_counter()
                self.store.processing.current()
                samples.append((time.perf_counter()-started)*1000)
        current = record.snapshot()
        with observations.owning('service') as record:
            self.bridge.start()
            started = time.perf_counter()
            for role in self.config['roles']:
                self.post_role(role)
            await asyncio.sleep(.01)
            self.assertTrue(self.dispatcher.wakeup.is_set())
            self.assertGreaterEqual(self.bridge.hints, 4)
            for _ in range(4):
                await self.turn()
            elapsed = (time.perf_counter()-started)*1000
        self.assertEqual(len(self.models.calls), 4)
        self.assertEqual({r['role'] for r in self.store.rows('SELECT role FROM queue')}, set(self.config['roles']))
        self.assertTrue(all(r['ack']=='done' for r in self.store.rows('SELECT ack FROM events')))
        self.assertTrue(all(r['collected'] is not None and r['exit']==0 for r in self.store.rows('SELECT collected,exit FROM attempts')))
        self.assertTrue(all(r['processed_at'] is None for r in self.store.rows('SELECT processed_at FROM events')))
        self.metrics('measurement',dict(current_ms=samples,current=current,
            four_role_wake_dispatch_ack_ms=elapsed,dispatch=record.snapshot(),release_files=len(self.release['files']),
            exclusions=len(self.config['artifact_exclusions']),
            seams=['synthetic configuration transition','fictional SDK principals','deterministic model answers',
                   'no provider/native/task execution or semantic response proof']))

    async def test_revocation_after_validation_refuses_wake_and_intake(self):
        self.store.processing.current()
        self.bridge.start()
        self.post()
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.now,self.key))
        with self.assertRaises(Refusal):
            self.dispatcher.intake()
        self.assertEqual(self.bridge.state,'authority-held')
        self.assertEqual(self.models.calls,[])
        self.assertEqual(self.store.rows('SELECT id FROM events'),[])

    async def test_template_drift_after_validation_prevents_wake_binding(self):
        self.store.processing.current()
        template = Path(self.config['tasks']['work-proposer']['templates'][0])
        original = template.read_bytes()
        template.write_bytes(b'X'+original[1:])
        with self.assertRaises(Refusal):
            self.bridge.start()
        self.assertEqual(self.bridge.receivers,[])
        self.assertEqual(self.models.calls,[])

    async def test_hot_pool_is_read_at_allocation_and_admission(self):
        from coordinator_runtime.execution_pool import ExecutionPool
        pool = ExecutionPool(self.config,self.store)
        for profiles in (['.codex'],['.codex4'],[],['.codex','.codex2','.codex3','.codex4','.codex5']):
            pool.pool.set(profiles)
            self.store.processing.current()
            self.assertEqual(configuration.release(self.store,self.config),self.release)
            if not profiles:
                with self.assertRaises(Refusal): pool.allocate()
            else:
                choice = pool.allocate()
                self.assertIn(choice['profile'],profiles)
                async with pool.admission(choice['profile']) as admitted:
                    self.assertEqual(admitted['profile'],choice['profile'])
        choice = pool.allocate()
        pool.pool.set([p for p in self.config['profiles'] if p != choice['profile']])
        with self.assertRaises(Refusal):
            async with pool.admission(choice['profile']):
                self.fail('removed profile admitted')


class SourceValidation(unittest.TestCase):
    """Owned synthetic source tree; production release/current fence, no exec."""
    def setUp(self):
        self.area = Path('/fixtures')/self._testMethodName
        self.area.mkdir()
        self.config = config_at(self.area)
        self.root = self.area/'release'
        directory = self.root/'tools/coordinator-runtime'
        self.module = directory/'coordinator_runtime/configuration.py'
        self.template = self.area/'templates/selected.md'
        self.provider = self.area/'provider'
        from coordinator_runtime.retention_dependency import FILES, source_pins
        names = ['tools/coordinator-runtime/coordinator_runtime/configuration.py',
                 'tools/coordinator-runtime/coordinator_runtime/program.py',
                 'tools/coordinator-runtime/coordinator',
                 'tools/coordinator-runtime/templates/coordinator-receive.md',
                 'tools/coordinator-runtime/final-release-risk.md',
                 'tools/branch_release.py','tools/operational_contracts.py',
                 'tools/direct-child/execution_pool.py','tools/direct-child/dispatch.py',
                 'tools/direct-codex-child/launch.sh',
                 *('tools/message-board/'+n for n in
                   ('catalog.py','board_store.py','active_listener.py','queue_transport.py','managed_owner.py'))]
        for path in [*(self.root/n for n in names),self.template,*(self.provider/n for n in FILES)]:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('# finite fictional source\n')
        self.config.update(board_library=str(self.root/'tools/message-board'),
            operator_cli=str(directory/'coordinator'),operator_config=str(self.area/'operator.json'),
            control_receive=dict(mode='cooperative',instructions=str(directory/'templates/coordinator-receive.md')),
            artifact_exclusions=[str(self.area/'held'/str(i)) for i in range(56)],
            canonical_publication=dict(method='retention-same-inode-v1',library=str(self.provider),
                                       source_pins=source_pins(self.provider,[])))
        for task in self.config['tasks'].values(): task['templates']=[str(self.template)]
        self.write_config(self.config)
        source = patch.object(configuration,'__file__',str(self.module))
        source.start();self.addCleanup(source.stop)
        self.expected = configuration.release(None,self.config)
        self.store = Store(self.config,clock=lambda:1000.)
        self.addCleanup(self.store.close)
        # Synthetic finite selection exercises current(), with no delegation or
        # task execution claim. No authority validator is patched or cached.
        current = digest(self.config)
        selection = dict(basis=dict(configuration=current,implementation=processing.implementation()),expires=1060.)
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)',
                              ('fixture-current',encode(selection),'fixture-issuer',1000.))
        transition = dict(basis=dict(release=self.expected))
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) '
                              'VALUES(?,?,?,?,?,?,?)',
                              (current,current,current,encode(self.config),encode(transition),'fixture-issuer',1000.))
        self.access = processing.Access(self.store,'fixture-current')
        self.access.current()

    def write_config(self, value):
        Path(value['operator_config']).write_text(encode(value))

    def test_unchanged_sources_are_all_rehashed_at_each_boundary(self):
        read = Path.read_bytes
        for _ in range(2):
            seen = set()
            def traced(path):
                seen.add(str(path))
                return read(path)
            with patch.object(Path,'read_bytes',traced): self.access.current()
            self.assertGreaterEqual(seen,set(self.expected['files']))

    def test_same_size_rewrite_with_restored_mtime_refuses(self):
        for path in (self.module,self.template,self.provider/'catalog.py'):
            with self.subTest(path=path):
                original = path.read_bytes();stat = path.stat()
                path.write_bytes(b'X'+original[1:])
                os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
                with self.assertRaises(Refusal): self.access.current()
                path.write_bytes(original)
                self.access.current()

    def test_identical_inode_replacement_is_revalidated(self):
        original = self.template.read_bytes();inode = self.template.stat().st_ino
        replacement = self.template.with_suffix('.replacement')
        replacement.write_bytes(original);replacement.replace(self.template)
        self.assertNotEqual(inode,self.template.stat().st_ino)
        read = Path.read_bytes;seen=[]
        def traced(path):
            seen.append(path)
            return read(path)
        with patch.object(Path,'read_bytes',traced): self.access.current()
        self.assertIn(self.template,seen)

    def test_config_and_static_pool_drift_refuse(self):
        self.write_config({**self.config,'recheck_seconds':.02})
        with self.assertRaises(Refusal): self.access.current()
        self.write_config(self.config);self.access.current()
        control = Path(self.config['execution_pool_routes'])
        control.write_text(control.read_text().replace('pool-state','other-state'))
        with self.assertRaises(Refusal): self.access.current()

    def test_parent_alias_change_refuses_before_child_read(self):
        parent = self.template.parent
        moved = parent.with_name('original-template-dir')
        parent.rename(moved);parent.symlink_to(moved,target_is_directory=True)
        read = Path.read_bytes
        def guarded(path):
            if path == self.template: raise AssertionError('aliased child bytes acquired')
            return read(path)
        with patch.object(Path,'read_bytes',guarded),self.assertRaises(Refusal): self.access.current()

    def test_new_exclusion_refuses_before_excluded_metadata_or_body(self):
        changed = copy.deepcopy(self.config)
        changed['artifact_exclusions'].append(str(self.template.parent))
        self.write_config(changed)
        lstat,stat,read = Path.lstat,Path.stat,Path.read_bytes
        def guard(fn):
            def call(path,*args,**kwargs):
                if path == self.template: raise AssertionError('excluded child touched')
                return fn(path,*args,**kwargs)
            return call
        with patch.object(Path,'lstat',guard(lstat)),patch.object(Path,'stat',guard(stat)), \
             patch.object(Path,'read_bytes',guard(read)),self.assertRaisesRegex(Refusal,'excluded before metadata'):
            configuration.release(self.store,changed)

    def test_excluded_module_directory_refuses_before_glob(self):
        changed = copy.deepcopy(self.config)
        changed['artifact_exclusions'].append(str(self.module.parent))
        self.write_config(changed)
        with patch.object(Path,'glob',side_effect=AssertionError('excluded directory enumerated')), \
             self.assertRaisesRegex(Refusal,'excluded before metadata'):
            configuration.release(self.store,changed)


class LexicalExclusions(unittest.TestCase):
    def test_path_component_equivalence_and_exclusion_before_metadata(self):
        from coordinator_runtime.contracts import PROFILES
        candidates = ['/a/b','/a/bc','/a/b/c','//a/b','/','/a//b/./c']
        for exclusions in (['/a/b'],['/'],['//'],['a/b'],['/a/./b/'],['/a/b/../c'],[]):
            for value in candidates:
                path = Path(value)
                expected = any(path == Path(p) or path.is_relative_to(Path(p)) for p in
                    [*exclusions,*(str(Path.home()/p) for p in PROFILES)])
                with self.subTest(exclusions=exclusions,value=value):
                    if expected:
                        with patch.object(Path,'is_symlink',side_effect=AssertionError('excluded metadata')), \
                             self.assertRaisesRegex(Refusal,'excluded before metadata'):
                            configuration._path(value,exclusions)
                    else:
                        with patch.object(Path,'is_symlink',return_value=False):
                            self.assertEqual(configuration._path(value,exclusions),path)
        exclusions=[]
        with patch.object(Path,'is_symlink',return_value=False): configuration._path('/a/b',exclusions)
        exclusions.append('/a')
        with patch.object(Path,'is_symlink',side_effect=AssertionError('new exclusion metadata')),self.assertRaises(Refusal):
            configuration._path('/a/b',exclusions)


if __name__ == '__main__':
    unittest.main()
