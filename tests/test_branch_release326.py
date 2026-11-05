"""Synthetic public fixtures; no live runtime or native/provider identities."""
from copy import deepcopy
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import branch_release as gate
sys.path.insert(0, str(TOOLS / 'coordinator-runtime'))
from coordinator_runtime import configuration
from coordinator_runtime.contracts import Refusal

FICTION = {key: None for key in ('native', 'profile', 'session', 'turn', 'provider', 'encounter')}


@contextmanager
def retained_fixture():
    # Preserve owned packet originals, refusals and successful checks. Retirement
    # belongs to their custodian under the actual processing+24h/all-hold rules.
    yield tempfile.mkdtemp(prefix='branch-release326-')


def packet():
    """Intent: a bounded UI oddity can ship with accountable acceptance/followup."""
    logical_owner = {'actor': 'fixture-release-role', 'authority': 'fixture delegated release decision'}
    m = {'repository': 'fixture/repository', 'pr_url': 'https://example.invalid/fixture/pull/3',
         'pr_number': 3, 'ref': 'refs/heads/fixture-feature', 'incarnation': 'fixture-incarnation',
         'base': 'a' * 40, 'head': 'b' * 40, 'tree': 'c' * 40, 'parents': ['a' * 40],
         'constituents': [{'pr_url': 'https://example.invalid/fixture/pull/3', 'base': 'a' * 40,
                           'head': 'b' * 40, 'tree': 'c' * 40, 'depends_on': []}],
         'combined_tip': 'b' * 40, 'contracts': {'fixture/schema.json': 'd' * 64}}

    def proof(kind):
        return {'kind': kind, 'original': 'fixture-owned-original-' + kind, 'sha256': 'e' * 64,
                'method': 'fixture independent ' + kind + ' procedure',
                'status': 'accepted' if kind == 'qa' else 'satisfied', 'material': deepcopy(m),
                'owner': {'actor': 'fixture-' + kind + '-role', 'authority': 'fixture ' + kind + ' authority'},
                'acceptance': 'fixture actual decision/result ' + kind, 'limits': [], 'correspondence': None}
    pr = {'pr_url': m['pr_url'], 'pr_number': m['pr_number'], 'state': 'OPEN', 'is_draft': True,
          'base_ref_name': 'fixture-base', 'base_ref_oid': m['base'],
          'head_ref_name': 'fixture-feature', 'head_ref_oid': m['head']}
    current = {'schema': 'branch-release-current-v1', 'material': m,
               'evidence': {k: proof(k) for k in ('reviews', 'qa')},
               'gates': {k: proof(k) for k in ('ci', 'stack', 'approval')},
               'release_owner': logical_owner,
               'recipients': {r: {'actor': 'fixture-' + r + '-role',
                                  'binding': 'fixture accepted ' + r + ' responsibility',
                                  'evidence': 'fixture independent role association'}
                              for r in ('Work', 'Root', 'Reviews')},
               'hard_holds': {'privacy': [], 'unknown_effects': [], 'custody': []},
               'pr_currentness': {'reviewed': deepcopy(pr), 'immediate': deepcopy(pr),
                                 'fetched_base_sha': m['base'], 'fetched_head_sha': m['head'],
                                 'expected_draft': True}}
    consequence = {'worst_plausible_impact': 'A badge may show an old label until refresh.',
                   'users': 'Only users viewing the optional badge.', 'customers': 'Opted-in customers.',
                   'tenants': 'One configured tenant at a time.', 'cross_tenant': 'No shared read/write; fixture architectural evidence.',
                   'update': 'Independent updater remains available; fixture separation check.',
                   'sign_in': 'Independent sign-in path; fixture boundary evidence.',
                   'data_correctness': 'No persisted mutation, only an optional label.',
                   'confidentiality': 'No sensitive input or access boundary involved.',
                   'sensitivity': 'Public static label.', 'duration': 'Until next page refresh.',
                   'recovery': 'Refresh restores the label; fixture recovery oracle.',
                   'rollback': 'Can disable optional badge without deployment; fixture readback.'}
    assessment = {'schema': gate.METHOD,
                  'basis': {'method': gate.METHOD, 'material': deepcopy(m), 'evidence': deepcopy(current['evidence'])},
                  'original': {'attempt': 'fixture-assessment-attempt', 'collector': 'fixture-logical-collector',
                               'reference': 'fixture-retained-original'},
                  'status': 'complete', 'coverage': {k: 'Fixture source account: badge state is isolated; ' + k for k in gate.AXES},
                  'understanding': 'Badge cache lifecycle is understood; replay while tab suspended is uncertain.',
                  'confidence': 'Reasoned confidence in bounded display-only consequence, limited to fixture.',
                  'limits': ['Suspended-tab timing not exhaustively explored.'], 'unassessed': [],
                  'factors': [{'id': 'badge-cache', 'surface': 'fixture/badge.py: cache lifecycle at exact head',
                               'mechanism': 'Unusual lifetime may retain an old badge label.',
                               'likelihood': 'Plausible after long suspension; no numerical estimate.',
                               'confidence': 'Consequence bounded by independent display-only boundary.',
                               'understood': 'No mutation/network and refresh resets cache.',
                               'uncertainties': ['Suspended-tab resumption ordering.'],
                               'support': ['fixture independent UI boundary and refresh observations'],
                               'counterevidence': ['Ordinary QA observed no wrong badge.'],
                               'consequence': consequence, 'recommendation': 'Accept optional display exposure with followup.',
                               'hard_boundary': 'none'}], 'requests': []}
    decision = {'schema': 'final-release-disposition-v1', 'assessment_sha256': gate.fingerprint(assessment),
                'basis_sha256': gate.fingerprint(assessment['basis']), **logical_owner,
                'record': 'fixture actual delegated decision original', 'decision': 'release',
                'factors': [{'id': 'badge-cache', 'outcome': 'accepted',
                             'rationale': 'Bounded optional label; refresh works and no data access/update/sign-in effect.',
                             'owner': 'fixture-product-owner', 'evidence': ['fixture isolation and refresh evidence'],
                             'acceptance': {**logical_owner, 'record': 'fixture explicit factor acceptance'}, 'followup': None}],
                'requests': [], 'limits_rationale': 'Accept the stated timing uncertainty because observed recovery and isolation bound consequence.'}
    return current, assessment, decision


def bind(current, assessment, decision):
    decision['assessment_sha256'] = gate.fingerprint(assessment)
    decision['basis_sha256'] = gate.fingerprint({'method': gate.METHOD, 'material': current['material'],
                                                'evidence': current['evidence']})


def correspondence(before, after, owner):
    return {'from': gate.fingerprint(before), 'to': gate.fingerprint(after),
            'changes': gate.changes(before, after), **owner,
            'rationale': 'Fixture unchanged badge relationships; changed base documentation has no consumers in this package.',
            'evidence': ['fixture exact diff and relationship account'], 'record': 'fixture actual currentness judgment'}


def bounded_followup():
    return {'owner': 'fixture-product-owner', 'scope': 'Clarify suspended badge cache lifecycle only.',
            'due': 'Before next badge change', 'completion': 'Independent suspension/refresh evidence returned to Branch.'}


class BranchRelease(unittest.TestCase):
    def assertBlocked(self, result, contains=None):
        self.assertEqual(result['status'], 'BLOCKED', result)
        self.assertFalse(result['release_performed'])
        self.assertFalse(result['approval_granted'])
        if contains:
            self.assertIn(contains, ' '.join(result['errors']))

    def eligible(self, *args):
        answer = gate.validate(*args)
        self.assertEqual(answer['status'], 'ELIGIBLE_FOR_EXISTING_FINAL_GATE', answer)
        self.assertFalse(answer['approval_granted'])
        self.assertFalse(answer['release_performed'])
        return answer

    def test_bounded_accepted_ui_risk_and_nonblocking_followup(self):
        c, a, d = packet()
        self.assertEqual(self.eligible(c, a, d)['accepted'], ['badge-cache'])
        d['factors'][0].update(outcome='followup', acceptance=None, followup=bounded_followup())
        answer = self.eligible(c, a, d)
        self.assertEqual(answer['accepted'], [])
        self.assertEqual(answer['followups'], ['badge-cache'])

    def test_zero_bugs_high_uncertainty_blocks_without_defect(self):
        c, a, d = packet()
        f = a['factors'][0]
        f.update(mechanism='Opaque shared token cache ownership may expose another tenant; no defect demonstrated.',
                 likelihood='Unknown; ordinary Reviews found zero bugs.', confidence='Low: cannot trace cache ownership.')
        f['consequence'].update(worst_plausible_impact='Sensitive cross-tenant data read.',
                                confidentiality='Unknown shared token scope.', cross_tenant='Potentially many tenants.',
                                recovery='Disclosure cannot be recalled.', rollback='Stops further access but cannot recover disclosed data.')
        d['factors'][0].update(outcome='blocker', acceptance=None, rationale='Reasoning cannot bound confidentiality consequence.')
        bind(c, a, d)
        result = gate.validate(c, a, d)
        self.assertBlocked(result)
        self.assertIn('badge-cache', result['blockers'])
        self.assertEqual(a['factors'][0]['counterevidence'], ['Ordinary QA observed no wrong badge.'])

    def test_recovery_and_blast_radius_inform_actual_different_decisions(self):
        c, a, d = packet()
        self.eligible(c, a, d)
        a['factors'][0]['consequence'].update(users='All signed-in users.', customers='Every customer.', tenants='All tenants.',
            cross_tenant='Shared session authority.', sign_in='Users may be unable to sign in.',
            update='Updater uses the same session and cannot repair remotely.', duration='Until manual recovery.',
            recovery='Requires per-tenant operator repair.', rollback='Rollback cannot restore corrupted credentials.')
        d['decision'] = 'hold'
        d['limits_rationale'] = 'Shared authentication reach and unavailable remote recovery exceed current release acceptance.'
        d['factors'][0].update(outcome='blocker', acceptance=None)
        bind(c, a, d)
        self.assertBlocked(gate.validate(c, a, d))

    def test_mere_assessor_recommendation_generic_done_or_ci_not_decision(self):
        c, a, d = packet()
        for change in ('missing-factor', 'wrong-actor', 'missing-acceptance', 'stale-assessment', 'generic-done'):
            altered = deepcopy(d)
            if change == 'missing-factor': altered['factors'] = []
            if change == 'wrong-actor': altered['actor'] = 'fixture-assessor-role'
            if change == 'missing-acceptance': altered['factors'][0]['acceptance'] = None
            if change == 'stale-assessment': altered['assessment_sha256'] = '0' * 64
            if change == 'generic-done': altered = {'semantic': 'DONE', 'ci': 'green'}
            with self.subTest(change=change): self.assertBlocked(gate.validate(c, a, altered))

    def test_prerequisites_wrong_missing_partial_stale(self):
        for where in ('reviews', 'qa', 'ci', 'stack', 'approval'):
            for problem in ('missing', 'wrong', 'failed', 'stale', 'unaccepted'):
                c, a, d = packet()
                group = c['evidence'] if where in c['evidence'] else c['gates']
                if problem == 'missing': del group[where]
                if problem == 'wrong': group[where]['kind'] = 'other'
                if problem == 'failed': group[where]['status'] = 'partial'
                if problem == 'stale': group[where]['material']['base'] = 'f' * 40
                if problem == 'unaccepted': group[where]['acceptance'] = ''
                with self.subTest(where=where, problem=problem): self.assertBlocked(gate.validate(c, a, d))

    def test_risk_limits_do_not_imply_missing_coverage_can_ship(self):
        for problem in ('partial', 'unassessed', 'coverage-gap'):
            c, a, d = packet()
            if problem == 'partial': a['status'] = 'partial'
            if problem == 'unassessed': a['unassessed'] = ['Unknown updater dependency not investigated.']
            if problem == 'coverage-gap': del a['coverage']['lifecycle_recovery']
            bind(c, a, d)
            self.assertBlocked(gate.validate(c, a, d))

    def test_material_and_evidence_changes_require_reassessment_or_correspondence(self):
        for delta in ('base', 'head', 'contract', 'review', 'qa', 'dependency'):
            c, a, d = packet()
            if delta == 'base': c['material']['base'] = 'f' * 40
            if delta == 'head': c['material']['head'] = 'f' * 40
            if delta == 'contract': c['material']['contracts']['fixture/schema.json'] = 'f' * 64
            if delta in ('review', 'qa'): c['evidence']['reviews' if delta == 'review' else 'qa']['sha256'] = 'f' * 64
            if delta == 'dependency': c['material']['constituents'][0]['depends_on'] = ['unknown PR']
            bind(c, a, d)
            with self.subTest(delta=delta): self.assertBlocked(gate.validate(c, a, d))

    def test_same_head_new_base_explicit_unaffected_is_proportionate(self):
        c, a, d = packet()
        c['material']['base'] = 'f' * 40
        # Ordinary gates retain their own originals only with their own owners'
        # explicit supported correspondence; risk needs a separate judgment.
        for proof in [*c['evidence'].values(), *c['gates'].values()]:
            proof['correspondence'] = correspondence(proof['material'], c['material'], proof['owner'])
        p = c['pr_currentness']
        p['reviewed']['base_ref_oid'] = p['immediate']['base_ref_oid'] = p['fetched_base_sha'] = 'f' * 40
        bind(c, a, d)
        self.assertBlocked(gate.validate(c, a, d), 'risk currentness')
        basis = {'method': gate.METHOD, 'material': c['material'], 'evidence': c['evidence']}
        receipt = correspondence(a['basis'], basis, c['release_owner'])
        self.eligible(c, a, d, receipt)
        receipt['changes'] = ['material.head']
        self.assertBlocked(gate.validate(c, a, d, receipt), 'every changed relationship')

    def test_correspondence_cannot_cross_target_or_method(self):
        for name in ('incarnation', 'ref', 'repository', 'method'):
            c, a, d = packet()
            if name == 'method': a['basis']['method'] = 'unselected-risk-method'
            else: a['basis']['material'][name] = 'different-target'
            bind(c, a, d)
            basis = {'method': gate.METHOD, 'material': c['material'], 'evidence': c['evidence']}
            r = correspondence(a['basis'], basis, c['release_owner'])
            self.assertBlocked(gate.validate(c, a, d, r))

    def test_new_current_assessment_keeps_ordinary_evidence_without_rerun(self):
        c, a, d = packet()
        a['understanding'] += ' Additional relationship analysis confirms the same bounded consequence.'
        self.assertBlocked(gate.validate(c, a, d), 'stale actual disposition')
        bind(c, a, d)
        self.eligible(c, a, d)

    def test_fresh_provider_capture_not_just_same_head(self):
        for where, value in (('fetched_base_sha', 'f' * 40), ('fetched_head_sha', 'f' * 40), ('expected_draft', False)):
            c, a, d = packet()
            c['pr_currentness'][where] = value
            self.assertBlocked(gate.validate(c, a, d), 'fresh PR currentness')
        c, a, d = packet()
        c['pr_currentness']['reviewed']['head_ref_name'] = 'other'
        c['pr_currentness']['immediate']['head_ref_name'] = 'other'
        self.assertBlocked(gate.validate(c, a, d), 'PR ref')

    def test_reassessment_of_changed_tip_uses_current_material_and_actual_new_decision(self):
        c, a, d = packet()
        c['material'].update(head='f' * 40, tree='1' * 40, parents=['b' * 40], combined_tip='f' * 40)
        c['material']['constituents'][-1].update(head='f' * 40, tree='1' * 40)
        for proof in [*c['evidence'].values(), *c['gates'].values()]:
            proof['material'] = deepcopy(c['material'])
            proof['original'] += '-current-after-change'
            proof['sha256'] = '2' * 64
        p = c['pr_currentness']
        p['reviewed']['head_ref_oid'] = p['immediate']['head_ref_oid'] = p['fetched_head_sha'] = 'f' * 40
        self.assertBlocked(gate.validate(c, a, d))
        a['basis'] = {'method': gate.METHOD, 'material': deepcopy(c['material']), 'evidence': deepcopy(c['evidence'])}
        a['original']['attempt'] = 'fixture-new-actual-assessment-attempt'
        a['understanding'] += ' Reassessed changed cache initialization against current integrated tip.'
        bind(c, a, d)
        self.eligible(c, a, d)

    def test_ordered_stack_dependencies_and_last_constituent_are_material(self):
        c, a, d = packet()
        first = {'pr_url': 'https://example.invalid/fixture/pull/2', 'base': 'a' * 40,
                 'head': '3' * 40, 'tree': '4' * 40, 'depends_on': []}
        c['material']['constituents'][0]['depends_on'] = [first['pr_url']]
        c['material']['constituents'].insert(0, first)
        for proof in [*c['evidence'].values(), *c['gates'].values()]:
            proof['material'] = deepcopy(c['material'])
        a['basis'] = {'method': gate.METHOD, 'material': deepcopy(c['material']), 'evidence': deepcopy(c['evidence'])}
        bind(c, a, d)
        self.eligible(c, a, d)
        c['material']['constituents'].reverse()
        self.assertBlocked(gate.validate(c, a, d), 'dependencies must precede')

    def test_reduction_requires_actual_evidence_and_acceptance_is_not_reduction(self):
        c, a, d = packet()
        d['factors'][0].update(outcome='reduced', acceptance=None,
                               evidence=['fixture changed cache ownership and independent refresh verification'],
                               rationale='State lifetime simplified; remaining bounded behavior checked.')
        self.eligible(c, a, d)
        d['factors'][0]['evidence'] = []
        self.assertBlocked(gate.validate(c, a, d), 'decision evidence')
        c, a, d = packet()
        d['factors'][0]['acceptance']['actor'] = 'fixture-assessor-role'
        self.assertBlocked(gate.validate(c, a, d), 'actual release authority')

    def test_hard_custody_and_privacy_cannot_be_accepted(self):
        for hold in ('privacy', 'unknown_effects', 'custody'):
            c, a, d = packet()
            c['hard_holds'][hold] = ['fixture original remains with its custodian']
            self.assertBlocked(gate.validate(c, a, d), 'cannot waive')
        for boundary in ('privacy', 'unknown-effects-custody'):
            c, a, d = packet()
            a['factors'][0]['hard_boundary'] = boundary
            bind(c, a, d)
            self.assertBlocked(gate.validate(c, a, d))

    def test_scope_reduction_confidence_routes_and_actual_zero_finding_return(self):
        c, a, d = packet()
        for kind in ('scope', 'reduction', 'confidence'):
            a['requests'].append({'id': kind, 'kind': kind, 'question': 'Fixture bounded ' + kind + ' question',
                                  'why': 'Trace the cache lifecycle and justify confidence.',
                                  'factor_ids': ['badge-cache'], 'blocking': True})
            d['requests'].append({'id': kind, 'state': 'pending', 'original': None, 'answer': None, 'followup': None})
        bind(c, a, d)
        result = gate.validate(c, a, d)
        self.assertBlocked(result)
        self.assertEqual([r['role'] for r in result['routes']], ['Work', 'Root', 'Reviews'])
        self.assertEqual(result['routes'][1]['recipient'], c['recipients']['Root'])
        self.assertTrue(all(r['required'] == 'settled' for r in result['routes']))
        for returned in d['requests']:
            returned.update(state='returned', original='fixture actual original return', answer='fixture source-bound answer')
        d['requests'][-1]['answer'] = {'findings': [], 'clarity': 'Ownership was traced.',
            'fragility': 'Long lifetime remains unusual but bounded.', 'confidence': 'Reasoned confidence in display-only scope.',
            'limits': ['No live product calibration.']}
        self.eligible(c, a, d)
        d['requests'][-1]['answer'] = {'findings': []}
        self.assertBlocked(gate.validate(c, a, d), 'confidence return')

    def test_nonblocking_confidence_inquiry_can_be_bounded_followup(self):
        c, a, d = packet()
        a['requests'] = [{'id': 'confidence', 'kind': 'confidence', 'question': 'Explain a future cache simplification.',
                          'why': 'Improve maintainability of understood bounded code.', 'factor_ids': ['badge-cache'], 'blocking': False}]
        d['requests'] = [{'id': 'confidence', 'state': 'followup', 'original': None, 'answer': None,
                          'followup': bounded_followup()}]
        bind(c, a, d)
        self.eligible(c, a, d)
        d['requests'][0]['followup']['scope'] = ''
        self.assertBlocked(gate.validate(c, a, d), 'followup scope')

    def test_duplicates_and_dropped_factors_never_silently_normalized(self):
        c, a, d = packet()
        a['factors'].append(deepcopy(a['factors'][0]))
        bind(c, a, d)
        self.assertBlocked(gate.validate(c, a, d), 'duplicate id')
        self.assertEqual(len(a['factors']), 2)

    def test_derived_route_overflow_is_explicit_partial_without_truncating_originals(self):
        c, a, d = packet()
        c['recipients']['Reviews']['evidence'] = 'fixture independent responsibility evidence ' * 200
        for number in range(12):
            key = 'confidence-' + str(number)
            a['requests'].append({'id': key, 'kind': 'confidence', 'question': 'Trace cache ownership.',
                                  'why': 'Explain confidence.', 'factor_ids': ['badge-cache'], 'blocking': False})
            d['requests'].append({'id': key, 'state': 'followup', 'original': None, 'answer': None,
                                  'followup': bounded_followup()})
        bind(c, a, d)
        original = deepcopy((c, a, d))
        result = gate.validate(c, a, d)
        self.assertBlocked(result, 'Derived check exceeds')
        self.assertLess(len(json.dumps(result).encode()), gate.MAX_BYTES)
        self.assertEqual((c, a, d), original)

    def prospective_fixture(self):
        tasks = {}
        for role in ('Branch', 'QA', 'Work'):
            tasks[role] = {'role': role, 'capacity': 1, 'profile': None, 'network': False,
                           'effects': 'none', 'templates': ['/fixture-old/templates/role.md'],
                           'effect_authority': {'operations': ['read-source'], 'read_roots': ['/fixtures'],
                                                'write_roots': []}}
        return SimpleNamespace(config={'operator_cli': '/fixture-old/coordinator', 'control_receive': {},
            'classifier': {'cwd': '/fixtures'}, 'diagnosis': {'cwd': '/fixtures'}, 'tasks': tasks,
            'profiles': [None], 'canonical_publication': {'library': '/fixtures/fixture-retention'}})

    def test_prospective_source_selection_adds_exact_branch_consumer_files_only(self):
        runtime = self.prospective_fixture()
        original = deepcopy(runtime.config)
        value = configuration.candidate(runtime, '/fixtures/fixture-current.json', ['Branch', 'QA'])
        expected = {str(p) for p in configuration.branch_release_sources(TOOLS.parent)}
        self.assertTrue(expected <= set(value['tasks']['Branch']['effect_authority']['read_roots']))
        self.assertFalse(expected & set(value['tasks']['QA']['effect_authority']['read_roots']))
        self.assertNotIn(str(TOOLS), value['tasks']['Branch']['effect_authority']['read_roots'])
        self.assertEqual(value['tasks']['Work']['effect_authority'], original['tasks']['Work']['effect_authority'])
        for role in value['tasks']:
            for key in ('capacity', 'profile', 'network', 'effects'):
                self.assertEqual(value['tasks'][role][key], original['tasks'][role][key])
            self.assertEqual(value['tasks'][role]['effect_authority']['write_roots'], [])
        self.assertEqual(runtime.config, original)
        self.assertEqual(set(value['tasks']), set(original['tasks']))

    def test_report_only_task_cannot_acquire_source_for_final_risk(self):
        runtime = self.prospective_fixture()
        runtime.config['tasks']['Branch']['effect_authority']['operations'] = ['read-reports']
        with self.assertRaisesRegex(Refusal, 'already source-authorized'):
            configuration.candidate(runtime, '/fixtures/fixture-current.json', ['Branch'])

    def test_actual_branch_consumer_cli_success_block_and_preserves_inputs(self):
        with retained_fixture() as root:
            home = Path(root)
            c, a, d = packet()
            files = {'current': c, 'assessment': a, 'disposition': d}
            for name, body in files.items(): (home / (name + '.json')).write_text(json.dumps(body))
            originals = {p.name: p.read_bytes() for p in home.iterdir()}
            command = [sys.executable, str(TOOLS / 'branch_release.py')]
            for name in files: command += ['--' + name, str(home / (name + '.json'))]
            run = subprocess.run([*command, '--output', str(home / 'eligible.json')], capture_output=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads((home / 'eligible.json').read_text())['accepted'], ['badge-cache'])
            for name, body in originals.items(): self.assertEqual((home / name).read_bytes(), body)
            # Same actual consumer path refuses a completed assessment with an
            # explicitly blocking uncertainty, irrespective of zero bug findings.
            d['factors'][0].update(outcome='blocker', acceptance=None)
            (home / 'disposition.json').write_text(json.dumps(d))
            run = subprocess.run([*command, '--output', str(home / 'blocked.json')], capture_output=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(json.loads((home / 'blocked.json').read_text())['blockers'], ['badge-cache'])
            self.assertTrue((home / 'eligible.json').exists())

    def test_cli_malformed_and_oversized_evidence_refuse_with_original_intact(self):
        for malformed in ('{"schema":1,"schema":2}', '{"likelihood":NaN}', '{', ' ' * (gate.MAX_BYTES + 1)):
            with retained_fixture() as root:
                home = Path(root)
                c, a, d = packet()
                (home / 'current').write_text(malformed)
                (home / 'assessment').write_text(json.dumps(a))
                (home / 'decision').write_text(json.dumps(d))
                run = subprocess.run([sys.executable, str(TOOLS / 'branch_release.py'),
                    '--current', str(home / 'current'), '--assessment', str(home / 'assessment'),
                    '--disposition', str(home / 'decision'), '--output', str(home / 'refusal')], capture_output=True)
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertEqual((home / 'current').read_text(), malformed)
                self.assertEqual(json.loads((home / 'refusal').read_text())['status'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
