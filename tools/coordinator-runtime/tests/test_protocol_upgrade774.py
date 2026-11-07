"""Owned public protocol fiction; run /src RO, /fixtures RW, no network.

Only 308's explicit NULL-native actor/config/membership/allocation seams apply.
The fake executable accepts --version only; no live binary or provider is used.
All fixtures and failures are retained, with a private caller-supplied TMPDIR.
"""
import copy
import fcntl
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing
from coordinator_runtime.contracts import Refusal, digest, encode
import test_configuration308 as fixture


class ProtocolUpgrade(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        original_engine = fixture.engine_config
        def engine(directory):
            value = original_engine(directory)
            for name, role in (('bp', 'Branch'), ('rp', 'Reviews')):
                value['tasks'][name] = {**copy.deepcopy(value['tasks']['wp']), 'role': role}
            value.update(codex='/fictional/original-codex', protocol_cli_version='codex-cli 0.166.0',
                         protocol_qualification='/fictional/original-qualification.json')
            return value
        with patch.object(fixture, 'engine_config', side_effect=engine):
            self.f.setUp()
        self.f.transition()
        self.s = self.f.runtime
        self.before = copy.deepcopy(self.s.config)
        self.area = self.f.directory/'candidate-public'; self.area.mkdir()
        self.binary = self.area/'codex'
        self.binary.write_text('#!/bin/sh\n[ "$#" = 1 ] && [ "$1" = --version ] || exit 73\nprintf "codex-cli 0.167.0\\n"\n')
        self.binary.chmod(0o700)
        self.schemas = {}
        for name, fields in configuration.PROTOCOL_SCHEMA_FIELDS.items():
            p = self.area/name; p.parent.mkdir(exist_ok=True)
            p.write_text(encode({'properties': {f:{} for f in fields}}))
            self.schemas[name] = self.sha(p)
        self.settings = self.area/'strict-metadata.json'
        self.settings.write_text(encode({'fixture': 'own empty-config strict metadata only'}))
        self.receipt = self.area/'qualification.json'
        self.receipt.write_text(encode({'cli_version':'codex-cli 0.167.0',
            'settings_check':str(self.settings), 'checked':{n:sorted(f) for n,f in configuration.PROTOCOL_SCHEMA_FIELDS.items()},
            'scope':'FICTION: generated schema/empty-config strict metadata only; no native behavior'}))
        self.choice = {'configuration':digest(self.s.config), 'owner':'fictional-Work',
            'authority':'FICTION: genuine Work selected these exact public package and extracted binary pins',
            'public_package':{'name':'@openai/codex', 'version':'0.167.0', 'registry':'https://registry.npmjs.org',
                'integrity':'sha512-'+'A'*86+'==', 'tarball':'https://registry.npmjs.org/@openai/codex/-/codex-0.167.0.tgz'},
            'codex':str(self.binary), 'executable_sha256':self.sha(self.binary), 'cli_version':'codex-cli 0.167.0',
            'qualification':str(self.receipt), 'qualification_sha256':self.sha(self.receipt),
            'schema_files':self.schemas, 'settings_check':str(self.settings), 'settings_sha256':self.sha(self.settings)}

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def draft(self, choice=None):
        value = configuration.candidate(self.s, str(self.f.directory/'upgrade.json'), [],
            scope_options={'protocol_upgrade':self.choice if choice is None else choice})
        Path(value['operator_config']).write_text(encode(value))
        return value

    def selection(self, value):
        return {'basis':configuration.basis(self.s, self.f.boards, value, list(value['tasks'])),
                'authority':'FICTION: Work reviews exact whole source and qualified protocol'}

    def test_positive_exact_binary_receipt_new_selection_preserves_all_eight_tasks_and_originals(self):
        value = self.draft()
        self.assertEqual(len(value['tasks']), 8)
        self.assertEqual(value['tasks'], self.before['tasks'])
        self.assertEqual(value['roles'], self.before['roles'])
        tables = ('attempts','jobs','events','enrollments','processing_capabilities','processing_runs')
        originals = {t:self.s.rows('SELECT * FROM '+t) for t in tables}
        grants = list(self.f.conn.iterdump())
        result = configuration.apply(self.s, self.f.boards, value, self.selection(value))
        self.assertFalse(result['historical_recovery'])
        self.assertEqual(originals, {t:self.s.rows('SELECT * FROM '+t) for t in tables})
        self.assertEqual(grants, list(self.f.conn.iterdump()))
        self.assertEqual(self.s.config, self.before)
        self.assertEqual(configuration.current_binding(self.s)['current'], digest(value))
        self.assertEqual(value['protocol_cli_version'], 'codex-cli 0.167.0')
        self.assertEqual(self.before['protocol_cli_version'], 'codex-cli 0.166.0')

    def test_stale_wrong_owner_version_package_and_receipt_refuse(self):
        cases = [('configuration','0'*64), ('owner','fictional-QA'),
                 ('cli_version','codex-cli 0.166.0'), ('qualification_sha256','0'*64)]
        for field, entry in cases:
            with self.subTest(field=field):
                choice = copy.deepcopy(self.choice); choice[field] = entry
                with self.assertRaises(Refusal): self.draft(choice)
        choice = copy.deepcopy(self.choice); choice['public_package']['registry'] = 'https://untrusted.invalid'
        with self.assertRaises(Refusal): self.draft(choice)

    def test_private_protocol_path_refuses_before_metadata(self):
        choice = copy.deepcopy(self.choice); choice['codex'] = '/fixtures/.ssh/not-opened'
        with patch.object(configuration, '_path', side_effect=AssertionError('metadata boundary crossed')):
            with self.assertRaisesRegex(Refusal, 'canonical public protocol evidence'):
                configuration.select_protocol(self.s, self.before, copy.deepcopy(self.before), choice)

    def test_rehashed_wrong_receipt_version_refuses(self):
        import json
        record = json.loads(self.receipt.read_text()); record['cli_version'] = 'codex-cli 0.166.0'
        self.receipt.write_text(encode(record)); self.choice['qualification_sha256'] = self.sha(self.receipt)
        with self.assertRaisesRegex(Refusal, 'receipt/version/settings differ'): self.draft()

    def test_later_explicit_basic_draft_retains_selected_protocol_without_replay(self):
        self.f.value = self.draft(); self.f.transition(); self.s = self.f.runtime
        value = configuration.candidate(self.s, str(self.f.directory/'later.json'), [], scope_options={})
        Path(value['operator_config']).write_text(encode(value))
        configuration.apply(self.s, self.f.boards, value, self.selection(value))
        for key in ('codex','protocol_cli_version','protocol_qualification'):
            self.assertEqual(value[key], self.f.value[key])

    def test_actual_wrong_binary_version_and_edited_binary_refuse(self):
        self.binary.write_text('#!/bin/sh\nprintf "codex-cli 0.166.0\\n"\n')
        with self.assertRaisesRegex(Refusal, 'bytes changed'): self.draft()
        self.choice['executable_sha256'] = self.sha(self.binary)
        with self.assertRaisesRegex(Refusal, 'actual selected executable version differs'): self.draft()

    def test_rehashed_receipt_claim_without_actual_schema_fields_refuses(self):
        schema = self.area/'v2/ThreadDeleteParams.json'
        schema.write_text(encode({'properties':{}}))
        self.choice['schema_files']['v2/ThreadDeleteParams.json'] = self.sha(schema)
        with self.assertRaisesRegex(Refusal, 'actual pinned generated schema'): self.draft()

    def changed_evidence_refuses(self, p):
        value = self.draft(); selected = self.selection(value)
        p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(Refusal, 'bytes changed'):
            configuration.apply(self.s, self.f.boards, value, selected)

    def test_receipt_changed_after_basis_refuses(self):
        self.changed_evidence_refuses(self.receipt)

    def test_settings_changed_after_basis_refuses(self):
        self.changed_evidence_refuses(self.settings)

    def test_cross_rights_and_edited_candidate_refuse(self):
        value = self.draft(); selected = self.selection(value)
        value['tasks']['wp']['network'] = True
        Path(value['operator_config']).write_text(encode(value))
        with self.assertRaises(Refusal): configuration.apply(self.s, self.f.boards, value, selected)
        value = self.draft(); selected = self.selection(value)
        value['codex'] = '/fictional/other'
        Path(value['operator_config']).write_text(encode(value))
        with self.assertRaises(Refusal): configuration.apply(self.s, self.f.boards, value, selected)
        value = self.draft()
        with self.assertRaisesRegex(Refusal, 'every conserved task'):
            configuration.basis(self.s, self.f.boards, value, ['wp'])

    def test_active_controller_without_parent_END_and_release_refuses(self):
        key = processing.select(self.s, self.f.boards, self.f.processing_selection())['capability']
        self.s.db.execute("INSERT INTO processing_runs VALUES('fictional-active',?,'owned',1000)", (key,))
        processing.revoke(self.s, self.f.boards, key)
        value = self.draft()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            configuration.apply(self.s, self.f.boards, value, self.selection(value))
        processing.release(self.s, self.f.boards, key, 'fictional-active',
            {'actual_END':0, 'evidence':['FICTION: parent collected original END']})
        configuration.apply(self.s, self.f.boards, value, self.selection(value))

    def test_existing_active_capability_and_collector_lock_fences_remain(self):
        key = processing.select(self.s, self.f.boards, self.f.processing_selection())['capability']
        value = self.draft()
        with self.assertRaisesRegex(Refusal, 'explicitly revoke'):
            configuration.apply(self.s, self.f.boards, value, self.selection(value))
        processing.revoke(self.s, self.f.boards, key)
        with (self.s.home/'service.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(Refusal, 'owns its lock'):
                configuration.apply(self.s, self.f.boards, value, self.selection(value))

    def test_unchanged_legacy_basic_selection_keeps_actual_selectors(self):
        value = configuration.candidate(self.s, str(self.f.directory/'legacy-next.json'), [])
        Path(value['operator_config']).write_text(encode(value))
        configuration.apply(self.s, self.f.boards, value, self.selection(value))
        for key in ('codex','protocol_cli_version','protocol_qualification'):
            self.assertEqual(value[key], self.before[key])


if __name__ == '__main__': unittest.main()
