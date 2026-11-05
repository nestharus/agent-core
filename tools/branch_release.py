#!/usr/bin/env python3
"""Final Branch risk consumer. Read-only inputs; no release or dispatch effects.

Owners acquire and authenticate the supplied evidence under existing procedures.
This check binds their assessment and decision to that evidence; it cannot attest
that prose is true, that a person has read it, or that customer risk is calibrated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from operational_contracts import validate_pr_currentness


MAX_BYTES = 65536
METHOD = 'final-release-risk-v1'
AXES = ('complexity_coupling', 'lifecycle_recovery', 'representation_migration',
        'interfaces_consumers', 'integrated_interactions', 'evidence_strength')
CONSEQUENCES = ('worst_plausible_impact', 'users', 'customers', 'tenants', 'cross_tenant',
                'update', 'sign_in', 'data_correctness', 'confidentiality', 'sensitivity',
                'duration', 'recovery', 'rollback')
DESTINATIONS = {'scope': 'Work', 'reduction': 'Root', 'confidence': 'Reviews'}


class Invalid(ValueError):
    pass


def check(condition, why):
    if not condition:
        raise Invalid(why)


def text(value, label):
    check(isinstance(value, str) and bool(value.strip()), label + ': nonempty text required')


def fields(value, required, label):
    check(isinstance(value, dict) and set(value) == set(required), label + ': exact fields required')


def texts(value, label, nonempty=False):
    check(isinstance(value, list) and len(value) <= 128 and (not nonempty or bool(value)),
          label + ': bounded explicit list required')
    for item in value:
        text(item, label)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def oid(value, label):
    check(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', value),
          label + ': full Git object required')


def sha(value, label):
    check(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value), label + ': sha256 required')


def material(value):
    fields(value, ('repository', 'pr_url', 'pr_number', 'ref', 'incarnation', 'base', 'head',
                   'tree', 'parents', 'constituents', 'combined_tip', 'contracts'), 'material')
    for key in ('repository', 'pr_url', 'ref', 'incarnation'):
        text(value[key], 'material.' + key)
    check(type(value['pr_number']) is int and value['pr_number'] > 0, 'actual PR number required')
    for key in ('base', 'head', 'tree', 'combined_tip'):
        oid(value[key], key)
    texts(value['parents'], 'ALLparents')
    for parent in value['parents']:
        oid(parent, 'parent')
    check(len(value['parents']) == len(set(value['parents'])), 'duplicate parent')
    members = value['constituents']
    check(isinstance(members, list) and 1 <= len(members) <= 128, 'ordered integrated constituents required')
    seen = set()
    for member in members:
        fields(member, ('pr_url', 'base', 'head', 'tree', 'depends_on'), 'constituent')
        text(member['pr_url'], 'constituent PR')
        check(member['pr_url'] not in seen, 'duplicate constituent')
        texts(member['depends_on'], 'ordered dependencies')
        check(set(member['depends_on']) <= seen, 'dependencies must precede their consumers')
        seen.add(member['pr_url'])
        for key in ('base', 'head', 'tree'):
            oid(member[key], 'constituent ' + key)
    check(members[-1]['head'] == value['head'] == value['combined_tip']
          and members[-1]['tree'] == value['tree'] and members[-1]['pr_url'] == value['pr_url'],
          'actual last constituent must remain the combined verification tip')
    check(isinstance(value['contracts'], dict), 'explicit relevant contract/config/schema/dependency hashes required')
    for name, digest in value['contracts'].items():
        text(name, 'contract path')
        sha(digest, 'contract digest')


def owner(value, label):
    fields(value, ('actor', 'authority'), label)
    text(value['actor'], label + ' actor')
    text(value['authority'], label + ' authority')


def changes(old, new, path=''):
    if isinstance(old, dict) and isinstance(new, dict):
        return sorted(p for key in old.keys() | new.keys()
                      for p in (changes(old[key], new[key], path + '.' + key) if key in old and key in new
                                else [(path + '.' + key).lstrip('.')]))
    return [] if old == new else [path.lstrip('.')]


def correspondence(receipt, before, after, authority, label):
    fields(receipt, ('from', 'to', 'changes', 'rationale', 'evidence', 'actor', 'authority', 'record'), label)
    check(receipt['from'] == fingerprint(before) and receipt['to'] == fingerprint(after),
          label + ': exact before/after correspondence required')
    check(receipt['changes'] == changes(before, after), label + ': account for every changed relationship')
    check({k: receipt[k] for k in ('actor', 'authority')} == authority,
          label + ': actual authorized owner required')
    for key in ('rationale', 'record'):
        text(receipt[key], label + ' ' + key)
    texts(receipt['evidence'], label + ' unaffected evidence', True)


def evidence(value, kind, current_material):
    fields(value, ('kind', 'original', 'sha256', 'method', 'status', 'material', 'owner',
                   'acceptance', 'limits', 'correspondence'), kind + ' evidence')
    check(value['kind'] == kind, 'wrong evidence kind: ' + kind)
    check(value['status'] == ('accepted' if kind == 'qa' else 'satisfied'), 'missing actual ' + kind + ' outcome')
    for key in ('original', 'method', 'acceptance'):
        text(value[key], kind + ' ' + key)
    sha(value['sha256'], kind + ' original hash')
    owner(value['owner'], kind + ' owner')
    texts(value['limits'], kind + ' limits')
    material(value['material'])
    if value['material'] != current_material:
        correspondence(value['correspondence'], value['material'], current_material, value['owner'], kind)
    else:
        check(value['correspondence'] is None, 'unnecessary/ambiguous ' + kind + ' correspondence')


def followup(value):
    fields(value, ('owner', 'scope', 'due', 'completion'), 'bounded followup')
    for key, item in value.items():
        text(item, 'followup ' + key)


def validate(current, assessment, disposition, unaffected=None):
    """Return eligibility for the existing final gate, never approval/acceptance.

    Validate source-bound facts structurally. Qualitative likelihood, confidence,
    consequences and acceptance rationale remain actual accountable judgments.
    """
    result = {'schema': 'branch-final-release-check-v1', 'status': 'BLOCKED',
              'errors': [], 'routes': [], 'blockers': [], 'accepted': [], 'followups': [],
              'release_performed': False, 'approval_granted': False}
    try:
        for item in (current, assessment, disposition, unaffected):
            check(len(json.dumps(item, ensure_ascii=False, allow_nan=False).encode()) <= MAX_BYTES,
                  'input exceeds existing 64KiB result bound; retain partial originals')
        fields(current, ('schema', 'material', 'evidence', 'gates', 'release_owner', 'recipients',
                         'hard_holds', 'pr_currentness'), 'current')
        check(current['schema'] == 'branch-release-current-v1', 'current schema')
        material(current['material'])
        owner(current['release_owner'], 'release owner')
        fields(current['recipients'], ('Work', 'Root', 'Reviews'), 'existing recipients')
        for role, recipient in current['recipients'].items():
            fields(recipient, ('actor', 'binding', 'evidence'), role + ' recipient')
            for key, value in recipient.items():
                text(value, role + ' ' + key)
        fields(current['hard_holds'], ('privacy', 'unknown_effects', 'custody'), 'hard holds')
        for name, held in current['hard_holds'].items():
            texts(held, name)
            check(not held, name + ': risk acceptance cannot waive hard holds')
        fields(current['evidence'], ('reviews', 'qa'), 'ordinary prerequisites')
        fields(current['gates'], ('ci', 'stack', 'approval'), 'separate final gates')
        for kind, value in {**current['evidence'], **current['gates']}.items():
            evidence(value, kind, current['material'])
        pin = current['material']
        p = current['pr_currentness']
        fields(p, ('reviewed', 'immediate', 'fetched_base_sha', 'fetched_head_sha', 'expected_draft'), 'PR currentness')
        check(type(p['expected_draft']) is bool, 'explicit expected draft state required')
        checked = validate_pr_currentness(**p, context='branch-final-release')
        check(checked['status'] == 'READY', 'fresh PR currentness: ' + '; '.join(checked['errors']))
        check(all(p['immediate'].get(k) == pin[v] for k, v in
                  (('pr_url', 'pr_url'), ('pr_number', 'pr_number'), ('base_ref_oid', 'base'),
                   ('head_ref_oid', 'head'))), 'PR capture differs from actual integrated material')
        check('refs/heads/' + p['immediate']['head_ref_name'] == pin['ref'], 'PR ref differs from material')
        basis = {'method': METHOD, 'material': pin, 'evidence': current['evidence']}
        fields(assessment, ('schema', 'basis', 'original', 'status', 'coverage', 'understanding',
                            'confidence', 'limits', 'unassessed', 'factors', 'requests'), 'assessment')
        check(assessment['schema'] == METHOD and assessment['status'] == 'complete',
              'missing or incomplete final assessment; DONE/CI are insufficient')
        fields(assessment['original'], ('attempt', 'collector', 'reference'), 'actual assessment original')
        for key, value in assessment['original'].items():
            text(value, 'original ' + key)
        fields(assessment['basis'], ('method', 'material', 'evidence'), 'assessment basis')
        check(assessment['basis']['method'] == METHOD, 'changed assessment method requires reassessment')
        material(assessment['basis']['material'])
        fields(assessment['basis']['evidence'], ('reviews', 'qa'), 'assessment evidence')
        for kind, value in assessment['basis']['evidence'].items():
            evidence(value, kind, assessment['basis']['material'])
        if assessment['basis'] != basis:
            for key in ('repository', 'pr_url', 'pr_number', 'ref', 'incarnation'):
                check(assessment['basis']['material'][key] == pin[key], 'different assessment target: ' + key)
            correspondence(unaffected, assessment['basis'], basis, current['release_owner'], 'risk currentness')
        else:
            check(unaffected is None, 'ambiguous unused risk correspondence')
        fields(assessment['coverage'], AXES, 'risk coverage (not an ordinary CRW episode)')
        for axis, account in assessment['coverage'].items():
            text(account, axis)
        for key in ('understanding', 'confidence'):
            text(assessment[key], key)
        texts(assessment['limits'], 'assessment limits')
        texts(assessment['unassessed'], 'unassessed areas')
        check(not assessment['unassessed'], 'unassessed consequences require return, not inferred clearance')
        fields(disposition, ('schema', 'assessment_sha256', 'basis_sha256', 'actor', 'authority',
                             'record', 'decision', 'factors', 'requests', 'limits_rationale'), 'actual disposition')
        check(disposition['schema'] == 'final-release-disposition-v1', 'disposition schema')
        check(disposition['assessment_sha256'] == fingerprint(assessment)
              and disposition['basis_sha256'] == fingerprint(basis), 'missing/stale actual disposition')
        check({k: disposition[k] for k in ('actor', 'authority')} == current['release_owner'],
              'assessor recommendation is not authorized risk acceptance')
        text(disposition['record'], 'actual decision record')
        check(disposition['decision'] in ('release', 'hold'), 'explicit release/hold decision required')
        text(disposition['limits_rationale'], 'explicit disposition of understanding/confidence/limits')
        factors = indexed(assessment['factors'], 'assessment factors')
        decisions = indexed(disposition['factors'], 'factor dispositions')
        check(factors.keys() == decisions.keys(), 'every factor needs an actual disposition; no dropped/new factors')
        for key, factor in factors.items():
            fields(factor, ('id', 'surface', 'mechanism', 'likelihood', 'confidence', 'understood',
                            'uncertainties', 'support', 'counterevidence', 'consequence',
                            'recommendation', 'hard_boundary'), 'risk factor')
            for name in ('surface', 'mechanism', 'likelihood', 'confidence', 'understood', 'recommendation'):
                text(factor[name], 'factor ' + name)
            for name in ('uncertainties', 'support', 'counterevidence'):
                texts(factor[name], 'factor ' + name, name == 'support')
            fields(factor['consequence'], CONSEQUENCES, 'customer consequence')
            for name, value in factor['consequence'].items():
                text(value, 'consequence ' + name)
            check(factor['hard_boundary'] in ('none', 'privacy', 'unknown-effects-custody'), 'hard boundary classification')
            d = decisions[key]
            fields(d, ('id', 'outcome', 'rationale', 'owner', 'evidence', 'acceptance', 'followup'), 'factor decision')
            for name in ('rationale', 'owner'):
                text(d[name], 'decision ' + name)
            texts(d['evidence'], 'decision evidence', True)
            outcome = d['outcome']
            check(outcome in ('blocker', 'accepted', 'followup', 'reduced'), 'explicit factor outcome required')
            if outcome == 'accepted':
                fields(d['acceptance'], ('actor', 'authority', 'record'), 'actual acceptance')
                check({k: d['acceptance'][k] for k in ('actor', 'authority')} == current['release_owner'],
                      'factor acceptance requires actual release authority')
                text(d['acceptance']['record'], 'acceptance record')
                result['accepted'].append(key)
            else:
                check(d['acceptance'] is None, 'acceptance cannot be inferred from recommendation/reduction/followup')
            if outcome == 'followup' or d['followup'] is not None:
                followup(d['followup'])
                result['followups'].append(key)
            if outcome == 'blocker' or factor['hard_boundary'] != 'none':
                result['blockers'].append(key)
        requests = indexed(assessment['requests'], 'risk questions')
        returns = indexed(disposition['requests'], 'question returns')
        check(requests.keys() == returns.keys(), 'missing required question dispositions')
        for key, request in requests.items():
            fields(request, ('id', 'kind', 'question', 'why', 'factor_ids', 'blocking'), 'risk question')
            check(request['kind'] in DESTINATIONS and type(request['blocking']) is bool, 'typed question kind/urgency')
            for name in ('question', 'why'):
                text(request[name], 'question ' + name)
            texts(request['factor_ids'], 'question factors', True)
            check(set(request['factor_ids']) <= factors.keys(), 'question must name assessed factors')
            role = DESTINATIONS[request['kind']]
            result['routes'].append({'id': key, 'role': role, 'recipient': current['recipients'][role],
                                     'required': 'settled', 'question': request['question'], 'why': request['why']})
            returned = returns[key]
            fields(returned, ('id', 'state', 'original', 'answer', 'followup'), 'question disposition')
            check(returned['state'] in ('returned', 'pending', 'followup'), 'question state')
            if returned['state'] == 'returned':
                text(returned['original'], 'actual question original return')
                if request['kind'] == 'confidence':
                    fields(returned['answer'], ('findings', 'clarity', 'fragility', 'confidence', 'limits'), 'Reviews confidence return')
                    check(isinstance(returned['answer']['findings'], list), 'explicit findings including zero')
                    texts(returned['answer']['limits'], 'confidence limits')
                    for name in ('clarity', 'fragility', 'confidence'):
                        text(returned['answer'][name], name)
                else:
                    text(returned['answer'], 'actual answer')
                check(returned['followup'] is None, 'ambiguous completed return')
            elif returned['state'] == 'followup' and not request['blocking']:
                followup(returned['followup'])
            else:
                result['blockers'].append('question:' + key)
        if disposition['decision'] == 'hold':
            result['blockers'].append('authorized-release-hold')
        check(not result['blockers'], 'release blockers require reduction/decision/actual returns')
        result['status'] = 'ELIGIBLE_FOR_EXISTING_FINAL_GATE'
        result['basis_sha256'] = fingerprint(basis)
        result['assessment_sha256'] = fingerprint(assessment)
        result['disposition_sha256'] = fingerprint(disposition)
    except (Invalid, TypeError, ValueError, KeyError, AttributeError, RecursionError) as exc:
        result['errors'].append(str(exc))
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode()) > MAX_BYTES:
        # Do not silently truncate routes/factors into an apparently complete
        # result. The supplied packet originals remain the authoritative frontier.
        return {'schema': 'branch-final-release-check-v1', 'status': 'BLOCKED',
                'errors': ['Derived check exceeds 64KiB; return scoped partial with original inputs retained; routes unavailable.'],
                'release_performed': False, 'approval_granted': False}
    return result


def indexed(value, label):
    check(isinstance(value, list) and len(value) <= 128, label + ': bounded list required')
    result = {}
    for item in value:
        check(isinstance(item, dict), label + ': object required')
        text(item.get('id'), label + ' id')
        check(item['id'] not in result, label + ': duplicate id')
        result[item['id']] = item
    return result


def load(path):
    # Inputs are explicitly acquired public/owned artifacts, never recursively
    # discovered. The caller applies exclusions before handing paths to this CLI.
    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    with Path(path).open('rb') as source:
        body = source.read(MAX_BYTES + 1)
    check(len(body) <= MAX_BYTES, 'input exceeds result bound')
    return json.loads(body, object_pairs_hook=pairs,
                      parse_constant=lambda _: check(False, 'non-JSON number'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'assessment', 'disposition'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--unaffected', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate(load(args.current), load(args.assessment), load(args.disposition),
                          load(args.unaffected) if args.unaffected else None)
    except (OSError, ValueError, Invalid, RecursionError) as exc:
        result = {'schema': 'branch-final-release-check-v1', 'status': 'BLOCKED',
                  'errors': [str(exc)], 'release_performed': False, 'approval_granted': False}
    # Fresh owned output preserves previous decisions/checks, including refusals.
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write('\n')
    print(result['status'])
    return 0 if result['status'] == 'ELIGIBLE_FOR_EXISTING_FINAL_GATE' else 2


if __name__ == '__main__':
    sys.exit(main())
