"""Explicit native membership controls; all owner/occurrence facts are TEST ONLY.

Uses the real frozen bundle, collector and foreground runtime on private fixtures.
No provider, live owner, native Git, transport or installed caller is exercised.
"""
from copy import deepcopy
from dataclasses import replace
import json
import unittest

import test_collector_dag as stock
from test_physical_base_binding import PhysicalBaseBinding, MAIN, refreeze
from collector_dag_adapter import foreground_check, NATIVE_NODE, ACCOUNT


class NativeMembership(unittest.TestCase):
    setUp = PhysicalBaseBinding.setUp
    fixture = PhysicalBaseBinding.fixture
    run_translate = PhysicalBaseBinding.run_translate
    accepted = PhysicalBaseBinding.accepted

    def membership_fixture(self, pin, membership='omitted'):
        b, owner = self.fixture()
        pr = b['native_packet']['data']['node']['entries']['nodes'][0]['pullRequest']
        pr['baseRefOid'] = pin
        if membership != 'omitted':
            pr['stack'] = deepcopy(membership)
        b = refreeze(b)
        owner = replace(owner, bundle_id=b['snapshot_id'])
        owner.envelope['snapshot']['feed']['snapshot_id'] = b['snapshot_id']
        owner.envelope['snapshot']['units'][0]['physical_base']['head'] = pin
        return b, owner

    def test_absent_and_right_membership_support_equal_and_differing_pins(self):
        for pin in (MAIN, '449e2a3d89ce4f51e69558d56b278594a129fbac'):
            for membership in ('omitted', {'id': NATIVE_NODE, 'number': 1649}):
                with self.subTest(pin=pin, membership=membership):
                    b, owner = self.membership_fixture(pin, membership)
                    before = deepcopy((b, owner))
                    self.accepted(b, owner)
                    self.assertEqual((b, owner), before)

    def test_explicit_null_cannot_be_qualified_by_valid_owner_overlay(self):
        for pin in (MAIN, '449e2a3d89ce4f51e69558d56b278594a129fbac'):
            with self.subTest(pin=pin):
                b, owner = self.membership_fixture(pin, None)
                violation = {'unit': 'A', 'kind': 'repair', 'obligation': 'repair-required',
                             'evidence_ref': 'controlled/repair'}
                owner.envelope['snapshot']['violations'] = [violation]
                before = deepcopy((b, owner))
                r = self.run_translate(b, owner)
                self.assertIsNone(r['snapshot'])
                self.assertIsNone(r['qualified_scope'])
                self.assertIn({'pr': 10, 'reason':
                    'explicit-stack-removal-inconsistent-with-entry-UNKNOWN'}, r['frontiers'])
                self.assertEqual(r['retained_known_active_violations'], [violation])
                record = r['field_provenance']['owner_snapshot/units/0/native_stack']
                self.assertEqual(record['coverage'], 'UNQUALIFIED_OWNER_SCOPE')
                self.assertEqual(record['state'], 'UNKNOWN')
                path = 'native_packet/data/node/entries/nodes/0/pullRequest/stack'
                self.assertEqual(r['field_provenance'][path]['snapshot_id'], b['snapshot_id'])
                capture = json.loads((self.area/str(self.n)/'feed-0001.json').read_text())
                self.assertIsNone(capture['payload']['data']['node']['entries']['nodes'][0]['pullRequest']['stack'])
                self.assertEqual((b, owner), before)

    def test_null_without_owner_stays_partial_and_retains_native_negative(self):
        b, owner = self.membership_fixture(MAIN, None)
        r = self.run_translate(b, None)
        self.assertIsNone(r['snapshot'])
        self.assertIsNone(r['qualified_scope'])
        self.assertIn('native_packet/data/node/entries/nodes/0/pullRequest/stack',
                      r['field_provenance'])
        self.assertIsNone(b['native_packet']['data']['node']['entries']['nodes'][0]['pullRequest']['stack'])

    def test_wrong_nonnull_native_membership_rejects_equal_and_differing_pins(self):
        for pin in (MAIN, '449e2a3d89ce4f51e69558d56b278594a129fbac'):
            for wrong in ({'id': NATIVE_NODE, 'number': 999},
                          {'id': 'wrong-node', 'number': 1649}):
                with self.subTest(pin=pin, membership=wrong):
                    with self.assertRaisesRegex(ValueError, 'native-stack-membership-CAS'):
                        self.membership_fixture(pin, wrong)

    def test_null_foreground_refuses_sender_and_journal_and_retains_violation(self):
        b, owner = self.membership_fixture(MAIN, None)
        violation = {'unit': 'A', 'kind': 'repair', 'obligation': 'repair-required',
                     'evidence_ref': 'controlled/repair'}
        owner.envelope['snapshot']['violations'] = [violation]
        folder = self.area/'foreground'
        folder.mkdir()
        def refusing_sender(alert):
            self.fail('unqualified explicit negative reached sender')
        r = foreground_check(stock.CORE, b, account=ACCOUNT, repo=stock.REPO,
            binding=stock.BINDING, expected_snapshot_id=b['snapshot_id'], now=stock.NOW,
            capture_dir=folder, expected_code_version='controlled-code-v1',
            owner_bindings=owner, journal_path=folder/'journal.json',
            lock_path=folder/'owner.lock', owner='controlled-owner', check_id='controlled-null',
            sender=refusing_sender)
        self.assertEqual(r['status'], 'UNKNOWN')
        self.assertIsNone(r['qualified_scope'])
        self.assertEqual(r['retained_known_active_violations'], [violation])
        self.assertFalse((folder/'journal.json').exists())
        self.assertFalse((folder/'owner.lock').exists())
