"""Effect expiry correction: real local job/adapter, synthetic actor/END/release seams.
No provider or native operation is invoked. Historical implementation pins are
immutable23773; the fixture release root and stopped collector remain fictional.
"""
import asyncio
import copy
import json
import hashlib
import os
import errno
from pathlib import Path
import unittest
from unittest.mock import patch
from test_owner_lease797 import OwnerLease
from test_qa629_repairs import CrossRole
from support import collect, result
from coordinator_runtime import prospective, ordinary, local_integration, service
from coordinator_runtime.contracts import Refusal, encode, digest

HISTORICAL_IMPLEMENTATION = {'__init__.py': '5d66d9f12796aefad7c957ac274a0c29a5145f2c2cfbda869447c7710006619b', 'admitted.py': '49cb0e353fbf84d60123c569255271ea296dda82414ea43b724d494ae494b39b', 'appserver.py': 'c40db90e04a518c3a74d79f14161bb2bcf02cbd05666f7d8f1e5a709b1097f1b', 'automatic_control.py': '3bf28ee9f03e96b63f786e298f1e767c8cd42e078989b326ee2e1fc6379dbe8b', 'board.py': 'a1c6d2f7cc8c3ac82d5bf24973d7bedd880b6315cf60ad39dc3dbe2d903f94e0', 'board_delivery.py': '95480ba4c473f783009b744372f2128c67ce8505913f184534f73b33b296c100', 'bounded_log.py': '348fddb9e583786c4e96ac3c94e6367b60f02a27e09f25b62c3c2dd4d8cf6029', 'branches.py': '21ed8b7be4d8b3df076a50369cb03db9df749ca569591d0aaffe55360256f59d', 'capacity.py': 'ce37543dc8b93285151037677f86283c04afe4ec4302f0fe8030754573921c7d', 'cleanup.py': 'ff873a9b9c68ab4480b3b3c8e92417ef0f0436bdfa13e3b337d90c4a76442b5c', 'cli.py': 'b30214373b65944afb9214a630baf444e742bef0c1d4363a0d8d9eea7905a905', 'coding.py': 'ec2132c53b61c5e65a29bebc8a355c890f0932f16965c236586f5bf158a86050', 'completion.py': 'eb6bd1647e2dffad825911b35531dda9d243d7f45f9e32c95c8cae66e0d53454', 'configuration.py': '0f180d0f1962b0b302b89523ad17af56c720d68603f09c432a0455a737c1e3e1', 'contracts.py': '78f8765295520fc99c69c3ef4c9c6e187c1a4e8805ac5c8b6ec107f69a0ea8f6', 'custodian_service.py': 'c965b850ce03c813298bb80ba1f03adcc255a2e5577178e652dd2ca0c4863f32', 'custody.py': '121300c6d98f3f3bdc8eae1f02759011e7852ed718f33671265f48e599003a90', 'delivery.py': '6119ccd9090ccbb4a31ee161732903778acb1a3ad2349190f797c1d3fdb5c7b6', 'dispatcher.py': '3a466177dec861095280fef663fc5849b1592f823e0a45a6aa743fd2757055ba', 'execution_pool.py': '03eccea4713262bd53deff6f982090dee04dbfdd8a2d72082eb9b4f1ac3febac', 'frontier.py': '35b82ff3d8aadc7bc26fbe8feaf9cb6cf4c28b6e8b5231dc0c53c17c6aeebdbb', 'inputs.py': 'a77daca813c5ac2d0983b7b4ee973d4c9be493f0c297e786274dddc80c1a6b03', 'integration.py': '1bb925f6cdf6d1885d0ca7098d1336d348433acbc0254220af862a5544970eac', 'integration_evidence.py': '905cb5f46c32a1c28eec92ea159e31486ce0ea079fd607102379fbc2b8386d44', 'integration_management.py': '2ad8a12cf11a558f27c581bcd86f3ad692d9af069c45c9117fce6a486819b5b4', 'local_integration.py': 'fb9597b1fe5fd354d93d44b9e282d751527333c0614fb837c4824079349dbc01', 'local_native.py': '37d95c92b556e69e46803c8d265646c03d4a500439711e68cf3739269123fb0f', 'metadata_lookup.py': '5b161bea354b3f4be37746fbd9df094ca372847807bbdd6c689326cabf5aeee2', 'method_closure.py': '360c13cc9de23d3474fdc14ceba8d63ba2724d486f07c4b14782062a46fc171f', 'observations.py': '08900f2238d134f435c1b953023c0f27f42c3f214dbaeb670cc2726c9c49c8bc', 'ordinary.py': 'd66d3fced5dbdec5a87e6e7a08b6e691d48771038bb13fd213eae819e55dc335', 'owner_control.py': '3d59ec43199145f512671b7f01916821f6dc23b2da1386b28cc04144105fe2aa', 'processing.py': '7cab9122a5153489ab0f639043249e52f205dd45c589953fbe8b9d6defc6f999', 'processing_admission.py': '31b10eb6382e8ec4c2686c088222c418c7bc8a9e40b46a12b24392fc203c4e9f', 'progress.py': 'bc4a12c1e42e911586dee0267be43ea1586183aa263019ec6a127442ab26433a', 'prospective.py': '9546a9842114b8252dbb3f957bb1d903071b4227734b8e7f72b3a7bd1a909833', 'public_tools.py': '13b1e250a10298591e1cbb81bb3f34f618ab792c076968ab303456bbfae3927c', 'publication.py': 'aeb6bee399e408593c6956f633103417ba899d9e1e4fc5b3635b57d67aed6837', 'qa_source.py': 'ef2ad2b357e1be26ede848729cc6eb4703f4deabe495241e58d5657fec7d0efc', 'readiness.py': '6530a6993b1cadb0f2ce092f8e0c249614b279760a979ba1b4aa9200acef2d69', 'recovery.py': 'ff7680a65741edf043c72f5669e0dbf3ccb9c36261c0ef046997c6af7a53373c', 'ref_scope.py': '4239564a4d3ebb335a8df47661b6515d5fbe980962779530abe8ae3a669de76d', 'report_repair.py': '0ee14365c7804a31f78dba0a620c15ce50de6340ca1469a50194c1e1b84581c9', 'report_scope.py': '35b7730e58b0e511c816023fdaf9be98d229fd83e6f70f10b0ea8f014dea4df7', 'reservation.py': '185b8a739c1d33d11395343998374bdad3e30149c531f6caee65778844a4e0a7', 'resource_scopes.py': '88eabd00c8348d91a100e1368be6e803e15dd30ab7403c2d278a9e605caafc51', 'retained.py': '37ec00cf8d2bd5d469f2d746003b0f62ac84504e818c4b92ad6a4c1edd5c8bca', 'retention_dependency.py': 'b5b274a151104e948334918a0688b2135e1afae5de5314a46297beb2fe7c77d8', 'retirement.py': 'd86138ae196c9c20772f7b349c23a81adb49a3ad0921bba488c2a8cae07af892', 'review_reader.py': 'd0ba7f0e661aaf39476842c2c5cfba4409d89f10e3035572b42188cb70218f86', 'review_returns.py': '6d9d08da3230d2bac2536565eeb800f993e0a48b8da419a21725fae039347e1f', 'reviews.py': 'c773cad52008293c5cc390090576cf695500718d88733087a5ae62161f6e55b1', 'routine.py': 'b6e884e0c2d8264b6b291a900bf3003055a664fba4af58088970ac24939207d8', 'selected_source.py': 'ffbee1ce5950a4918915f8ab7fc2c16723c054a2ae0684c78ca13abfa9fe87fa', 'service.py': '37cf95c86ce6df3ad985e1a53f58fb456c660067272d06a87e2e3d4bae348fe7', 'service_recovery.py': 'ab2819101d0adbdb1b220ce7a7433fe063a4a5f8301c3631eb7e00ddd66544b8', 'service_wake.py': 'ccda602f4802fdceead1a299be11e3e78f54966a44cf5ab579ee4ee6f124a009', 'shared_custody.py': '871b79271ad00fd5582ee83de6a4f133f42132ebb11e6b21edc2f7b24f10e832', 'software.py': '027fe8f78ff7210813d645b1372f87202cd61823ca12cbe80dc9e979baa7b693', 'storage.py': 'f628a1774490459dbbd8e4f5911a8916bf138bbf1e5dc94f0d55e94f44a9b8ce', 'store.py': 'f782fde646b89863d8b643e020f0b18ad64a2af116e49b07c3b6917626abc54d', 'windows.py': '341ad4784d78f3c9b84107b24fd3c5e8dfe5d8589c90e2ec21bd69b2d3151e71'}

class EffectLease(OwnerLease):
    effect_mode = True

    def configure(self):
        OwnerLease.configure(self)
        CrossRole.configure(self)
        if self.effect_mode is True:
            p = self.scope['ordinary_effects']
            p.pop('public_executables')
            self.script.write_text('#!/usr/bin/python3\nprint("owned check")\n')
            self.script.chmod(0o700)
            for key in ('command','readback'):
                p[key] = dict(argv=[str(self.script)],
                    executable_sha256=hashlib.sha256(self.script.read_bytes()).hexdigest(),stdout='owned check\n')

    def select(self, service=None):
        # Update the same object used by797's release seam before selection.
        self.old_impl.clear()
        self.old_impl.update(HISTORICAL_IMPLEMENTATION)
        return super().select(service)

    def setUp(self):
        select = prospective.select
        def original_epoch(store, actor, selection):
            selection['tasks']['qa-execution']['ordinary_effects'] = self.effect_mode
            selection['expires'] = 1700.
            return select(store, actor, selection)
        with patch.object(prospective, 'select', side_effect=original_epoch):
            super().setUp()

    def test_expired_effect_refuses_before_body_with_framework_current(self):
        self.apply()
        self.store.admit('own-package', self.config['roles']['Branch']['owner'],
                         dict(task_scopes={'qa-execution':self.scope}))
        self.post('QA','qa-execution','own-package')
        # Old Work debt remains selected; reserve it without consuming or erasing it.
        job = self.store.reserve()
        if job['task'] != 'qa-execution':
            self.assertEqual(job['task'],'work-proposer')
            job = self.store.reserve()
        self.assertEqual(job['task'],'qa-execution')
        attempt = self.store.start_job(job['id'],job['token'])
        job = self.store.job(job['id'])
        admission = self.store.one('SELECT * FROM admissions WHERE package=?',('own-package',))
        self.boards['QA'].bind_software_attempt(self.store,job,attempt,admission)
        collect(self.store,attempt,result(category='consolidated'),
                tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        # Valid unexpired policy reaches the authentic ordinary admitted selector.
        self.assertEqual(ordinary.selected(self.store,job)['policy']['ordinary_effects'],self.effect_mode)
        ordinary.policy_for(self.store,job)
        tables = ('prospective_authorities','ordinary_runs','ordinary_resources',
                  'ordinary_tool_records','ordinary_acceptance','processing_capabilities','service_windows')
        before = {t:copy.deepcopy(self.store.rows('SELECT * FROM '+t)) for t in tables}
        self.now = 1700.  # Exact original cutoff, inside first framework lease.
        self.assertIsNotNone(prospective.current(self.store,'qa-execution'))
        ordinary.validate_resources(self.store,self.scope['ordinary_effects'])
        with patch.object(local_integration,'current_sources',side_effect=AssertionError('source body before expiry guard')):
            with self.assertRaisesRegex(Refusal,'prospective authority expired'):
                asyncio.run(ordinary.perform(self.store,self.boards['QA'],job))
        with self.assertRaisesRegex(Refusal,'prospective authority expired'):
            ordinary.selected(self.store,job)
        for table, rows in before.items():
            self.assertEqual(self.store.rows('SELECT * FROM '+table),rows,table)
        # A synthetic preexisting intent tests the real tool entry separately;
        # no subprocess may be created after this boundary either.
        self.store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',
            (attempt,job['id'],self.epoch['id'],digest(admission['receipt']),encode(self.scope['ordinary_effects']),'intent','{}'))
        records = self.store.rows('SELECT * FROM ordinary_tool_records')
        with patch.object(local_integration,'current_sources',side_effect=AssertionError('body before tool guard')):
            with self.assertRaisesRegex(Refusal,'prospective authority expired'):
                asyncio.run(ordinary.tool(self.store,attempt,'forbidden',
                    self.scope['ordinary_effects']['command']['argv'],str(self.repo),self.scope['ordinary_effects']))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'),records)
        # Report/control/intake continue beyond the effect cutoff.
        self.now=1900.
        service.admit_input(self.store)
        self.post('Reviews','@control',None)
        self.assertEqual(self.store.rows('SELECT * FROM prospective_authorities'),before['prospective_authorities'])
        self.now=2200.
        with self.assertRaises(Refusal):service.admit_input(self.store)

class AdmittedLease(EffectLease):
    effect_mode = 'admitted-v1'

class Isolation(unittest.TestCase):
    def test_actual_source_sdk5_and_snapshot_are_readonly(self):
        sources = [Path('/actualsrc/tools/coordinator-runtime/coordinator_runtime/ordinary.py')]
        sources += [Path('/src/tools/message-board')/(n+'.py') for n in
                    ('board_store','catalog','retention','active_listener','queue_transport')]
        sources += list(Path('/src/tools/coordinator-runtime/tests/fixture_snapshot').glob('*.py'))
        self.assertGreaterEqual(len(sources), 7)
        for source in sources:
            self.assertTrue(source.is_file(),str(source))
            self.assertTrue(os.statvfs(source).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as denied:
                os.open(source, os.O_WRONLY)
            self.assertEqual(denied.exception.errno,errno.EROFS)
