"""Pure stock-helper controls from Root's pin-first decision; all owner facts TEST ONLY.

The scalar pin/Main distinction reflects supplied evidence, but the complete
synthetic diamond and owner assertions are NOT current operational OwnerBindings.
No provider, native invocation, journal, sender or Git operation runs here.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import test_collector_dag as stock
from collector_dag_adapter import translate, freeze_bundle, ACCOUNT, PRODUCER
from feed_adapter import FeedAdapter

CORE = stock.CORE
PIN = '449e2a3d89ce4f51e69558d56b278594a129fbac'
MAIN = '22b5c4724117cd237996611f215c0494cde5a44a'
BASE_CAS = 'owner-PR-ref-head-base-membership-CAS-UNKNOWN'

def refreeze(b):
    # Rebuild the actual stock projection, not merely a digest after fixture edits.
    return freeze_bundle(CORE, **{k:deepcopy(b[k]) for k in
        ('account','producer','repo','binding','acquisition','native_packet',
         'native_observed_at','acquired_at')})

class PhysicalBaseBinding(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(dir=stock.RUN))
        self.n = 0
        self.s = stock.baseline()
        self.s['main'] = MAIN
        for unit in self.s['units']:
            unit['physical_base']['head'] = MAIN
        for p in self.s['probes']:
            p['base'] = MAIN
        self.b = stock.bundle_for(self.s)

    def fixture(self, *, pin=True, ref='main'):
        b, owner = stock.FinalBindingBoundary.complete(self)
        packet = b['native_packet']
        pr = packet['data']['node']['entries']['nodes'][0]['pullRequest']
        pr['baseRefName'] = ref
        if pin:
            pr['baseRefOid'] = PIN
        b = refreeze(b)
        owner = replace(owner, bundle_id=b['snapshot_id'])
        owner.envelope['snapshot']['feed']['snapshot_id'] = b['snapshot_id']
        owner.envelope['snapshot']['units'][0]['physical_base'] = {
            'ref': ref, 'head': PIN if pin else MAIN}
        return b, owner

    def run_translate(self, b, owner, **kw):
        self.n += 1
        folder = self.area / str(self.n)
        folder.mkdir()
        args = dict(account=ACCOUNT, repo=stock.REPO, binding=stock.BINDING,
                    expected_snapshot_id=b['snapshot_id'], now=stock.NOW,
                    capture_dir=folder, expected_code_version='controlled-code-v1',
                    owner_bindings=owner)
        args.update(kw)
        return translate(CORE, b, **args)

    def accepted(self, b, owner):
        result = self.run_translate(b, owner)
        self.assertIsNotNone(result['snapshot'], result['frontiers'])
        self.assertIsNotNone(result['qualified_scope'])
        self.assertEqual(result['snapshot'], owner.envelope['snapshot'])
        return result

    def rejected(self, b, owner, frontier):
        result = self.run_translate(b, owner)
        self.assertIsNone(result['snapshot'])
        self.assertIsNone(result['qualified_scope'])
        self.assertIn(frontier, result['frontiers'])
        return result

    def test_differing_pin_admitted_and_current_Main_metadata_preserved(self):
        b, owner = self.fixture()
        frozen = deepcopy(b)
        r = self.accepted(b, owner)
        self.assertEqual(r['snapshot']['units'][0]['physical_base']['head'], PIN)
        self.assertEqual(r['snapshot']['main'], MAIN)
        self.assertNotEqual(PIN, MAIN)
        self.assertEqual(r['main_structure'], b['native_packet']['data']['repository']['defaultBranchRef'])
        self.assertEqual(r['main_structure']['target']['tree']['oid'], owner.main_version['tree'])
        self.assertEqual([x['oid'] for x in r['main_structure']['target']['parents']['nodes']],
                         owner.main_version['parents'])
        self.assertEqual(b, frozen)
        self.assertEqual(r['field_provenance']['native_packet/data/node/entries/nodes/0/pullRequest/baseRefOid']['snapshot_id'], b['snapshot_id'])

    def test_present_pin_rejects_current_Main_and_other_wrong_owner_operands(self):
        for wrong in (MAIN, 'f'*40):
            with self.subTest(wrong=wrong):
                b, owner = self.fixture()
                owner.envelope['snapshot']['units'][0]['physical_base']['head'] = wrong
                self.rejected(b, owner, BASE_CAS)

    def test_absent_pin_keeps_Main_fallback_and_rejects_stored_operand(self):
        b, owner = self.fixture(pin=False)
        self.accepted(b, owner)
        owner.envelope['snapshot']['units'][0]['physical_base']['head'] = PIN
        self.rejected(b, owner, BASE_CAS)

    def test_absent_pin_keeps_member_ref_fallback(self):
        b, owner = self.fixture(pin=False, ref='B')
        owner.envelope['snapshot']['units'][0]['physical_base']['head'] = self.s['units'][1]['version']['head']
        self.accepted(b, owner)

    def test_absent_unresolved_ref_stays_unknown_but_present_pin_is_sufficient(self):
        b, owner = self.fixture(pin=False, ref='outside-unacquired')
        self.rejected(b, owner, BASE_CAS)
        b, owner = self.fixture(ref='outside-unacquired')
        self.accepted(b, owner)

    def test_null_or_malformed_present_pin_does_not_fall_back(self):
        for value in (None, '', 'invalid', 7):
            with self.subTest(value=value):
                b, owner = self.fixture()
                b['native_packet']['data']['node']['entries']['nodes'][0]['pullRequest']['baseRefOid'] = value
                with self.assertRaises(ValueError):
                    refreeze(b)

    def test_no_owner_stays_partial_and_unknown_source_field_rejected(self):
        b, owner = self.fixture()
        r = self.run_translate(b, None)
        self.assertIsNone(r['snapshot']); self.assertIsNone(r['qualified_scope'])
        b['native_packet']['data']['node']['entries']['nodes'][0]['pullRequest']['unknown'] = True
        with self.assertRaises(ValueError):
            refreeze(b)

    def test_native_projection_and_collector_agree_for_present_pin(self):
        b, owner = self.fixture()
        s = owner.envelope['snapshot']
        associations = {u['pr']: {k:deepcopy(u[k]) for k in
            ('id','ticket','campaign','requires','provenance','evidence','eligibility','admitted')}
            | {'content':u['version']['content'], 'resolution':u['version']['resolution']}
            for u in s['units']}
        folder = self.area/'native'; folder.mkdir()
        feed = FeedAdapter(CORE, account=ACCOUNT['session'], binding=stock.BINDING,
                           repo=stock.REPO, capture_dir=folder)
        native = feed.native(json.dumps(b['native_packet']).encode(),
            snapshot_id=b['snapshot_id'], associations=associations, groups=s['groups'])
        self.assertIsNotNone(native['snapshot'])
        result = self.accepted(b, owner)
        # Feed schema and owner-provided probes differ by contract; physical and
        # canonical unit facts, logical groups and current Main must agree.
        for key in ('main','repo','units','segments','groups'):
            self.assertEqual(native['snapshot'][key], result['snapshot'][key])
        for key in ('binding','snapshot_id'):
            self.assertEqual(native['snapshot']['feed'][key], result['snapshot']['feed'][key])

    def test_differing_pin_does_not_bypass_Main_or_PR_immutable_metadata(self):
        for field, frontier in (('main-head','owner-Main-structural-CAS-UNKNOWN'),
                ('main-tree','owner-Main-tree-orderedparents-CAS-UNKNOWN'),
                ('main-parents','owner-Main-tree-orderedparents-CAS-UNKNOWN'),
                ('pr-tree','owner-PR-tree-orderedparents-CAS-UNKNOWN'),
                ('pr-parents','owner-PR-tree-orderedparents-CAS-UNKNOWN'),
                ('pr-ref',BASE_CAS), ('base-ref',BASE_CAS), ('membership',BASE_CAS)):
            with self.subTest(field=field):
                b, owner = self.fixture(); s = owner.envelope['snapshot']; u = s['units'][0]
                if field == 'main-head': s['main'] = PIN
                elif field == 'main-tree': owner.main_version['tree'] = 'e'*40
                elif field == 'main-parents': owner.main_version['parents'].reverse()
                elif field == 'pr-tree': u['version']['tree'] = 'e'*40
                elif field == 'pr-parents': u['version']['parents'] = ['e'*40]
                elif field == 'pr-ref': u['ref'] = 'refs/heads/wrong'
                elif field == 'base-ref': u['physical_base']['ref'] = 'wrong'
                else: u['native_stack'] = 'other'
                self.rejected(b, owner, frontier)

    def test_differing_pin_keeps_coverage_freshness_and_generation_checks(self):
        for field, frontier in (('facet','canonical-owner-coverage-or-freshness-UNKNOWN'),
                ('owner-time','canonical-owner-coverage-or-freshness-UNKNOWN'),
                ('native-time','native-prior-read-current-freshness-UNKNOWN'),
                ('collector-code','collector-code-version-unbound-UNKNOWN')):
            with self.subTest(field=field):
                b, owner = self.fixture()
                if field == 'facet': owner.field_coverage['10'].remove('evidence')
                elif field == 'owner-time': owner = replace(owner, observed_at='2026-11-01T00:00:00+00:00')
                elif field == 'native-time':
                    b['native_observed_at'] = '2026-11-01T00:00:00+00:00'
                    b = refreeze(b); owner = replace(owner,bundle_id=b['snapshot_id'])
                    owner.envelope['snapshot']['feed']['snapshot_id'] = b['snapshot_id']
                else:
                    b['acquisition']['latest']['code_version'] = 'wrong'
                    b = refreeze(b); owner = replace(owner,bundle_id=b['snapshot_id'])
                    owner.envelope['snapshot']['feed']['snapshot_id'] = b['snapshot_id']
                self.rejected(b, owner, frontier)

    def test_differing_pin_keeps_foreign_account_and_bundle_CAS(self):
        for field in ('account','bundle','mutated-bundle','repo'):
            with self.subTest(field=field):
                b, owner = self.fixture(); kw = {}
                if field == 'account': kw['account'] = dict(ACCOUNT, profile='.codex3')
                elif field == 'bundle': owner = replace(owner,bundle_id='foreign')
                elif field == 'repo': kw['repo'] = 'foreign/repository'
                else: b['native_known'][0]['headRefOid'] = 'e'*40
                with self.assertRaises(ValueError): self.run_translate(b,owner,**kw)

    def test_plan_and_simulation_keep_independent_base_and_Main_CAS(self):
        b, owner = self.fixture(); s = self.accepted(b,owner)['snapshot']
        prepared = CORE.plan(s)
        a = next(op for op in prepared['operations'] if op['unit']=='A')
        self.assertEqual(a['expected_physical_base'], {'ref':'main','head':PIN})
        self.assertEqual(a['new_bases'], [{'unit':None,'tip':MAIN}])
        actual = {'main':MAIN, 'units':{u['id']:{k:deepcopy(u[k]) for k in
            ('version','physical_base','native_stack')} for u in s['units']}}
        for field in ('base','Main'):
            changed = deepcopy(actual)
            if field == 'base': changed['units']['A']['physical_base']['head'] = MAIN
            else: changed['main'] = PIN
            trace = CORE.simulate(s,prepared,changed,{})
            self.assertEqual(trace['trace'][0]['effect'],'CAS_MISMATCH')
        trace = CORE.simulate(s,prepared,actual,{})
        self.assertEqual(trace['trace'][0]['effect'],'UNKNOWN')  # no invented composition outcome
        self.assertEqual(prepared['logical_dependencies']['C'], ['A'])
        self.assertNotIn('B',prepared['logical_dependencies']['C'])
