"""Observe the actual candidate contract; no Store, SDK, network or ref effects."""
import copy
import json
from pathlib import Path


def observe(c, area):
    observations = {}

    def call(name, function, project=lambda value: value):
        try:
            observations[name] = project(function())
        except c.Refusal:
            observations[name] = 'REFUSED'

    config = {'qa_branch_sequence': 'accepted-qa-branch-cleanup-v1', 'tasks': {
        'qa-execution': {'role': 'QA', 'phase': 'execution', 'effects': 'owner-reconcile',
                         'require_package_scope': True, 'execution': 'native',
                         'responses': {'consolidated': ['branch-integrator']},
                         'effect_authority': {'operations': ['execute-admitted-qa']}},
        'branch-integrator': {'role': 'Branch', 'phase': 'integrator', 'effects': 'owner-reconcile',
                              'require_package_scope': True, 'execution': 'native',
                              'responses': {'complete': ['qa-cleanup']}},
        'qa-cleanup': {'role': 'QA', 'phase': 'cleanup', 'effects': 'owned-artifacts',
                      'require_package_scope': True, 'execution': 'native', 'package_narrowing': True,
                      'responses': {'qualification': ['work-proposer']}},
        'work-proposer': {'role': 'Work'}}}
    call('sequence.exact', lambda: c.qa_branch_sequence(config))
    call('sequence.unselected', lambda: c.qa_branch_sequence({'tasks': {}}))
    changed = copy.deepcopy(config); changed['qa_branch_sequence'] = 'invented'
    call('sequence.unknown-selector', lambda: c.qa_branch_sequence(changed))
    for name, key, value in (
            ('qa-route', 'responses', {'consolidated': ['qa-cleanup']}),
            ('qa-extra-operation', 'effect_authority', {'operations': ['execute-admitted-qa', 'read-source']}),
            ('qa-owner-execution', 'execution', 'owner'),
            ('qa-unscoped', 'require_package_scope', False)):
        value_config = copy.deepcopy(config); value_config['tasks']['qa-execution'][key] = value
        call('sequence.' + name, lambda v=value_config: c.qa_branch_sequence(v))
    changed = copy.deepcopy(config); changed['tasks']['branch-integrator']['responses']['complete'] = ['work-proposer']
    call('sequence.branch-skips-consolidation', lambda: c.qa_branch_sequence(changed))
    changed = copy.deepcopy(config); changed['tasks']['qa-cleanup']['package_narrowing'] = False
    call('sequence.cleanup-not-narrowed', lambda: c.qa_branch_sequence(changed))
    call('route.qa-to-branch', lambda: c.response_tasks(config['tasks']['qa-execution'], {'category': 'consolidated'}, config))
    call('route.branch-to-cleanup', lambda: c.response_tasks(config['tasks']['branch-integrator'], {'category': 'complete'}, config))
    call('route.cleanup-to-work', lambda: c.response_tasks(config['tasks']['qa-cleanup'], {'category': 'qualification'}, config))

    # These are new fictional lexical paths. No referenced files are acquired.
    read = str(area / 'inputs'); write = str(area / 'outputs')
    task = {'require_package_scope': True, 'package_narrowing': True, 'cwd': read,
            'scope_roots': [str(area)], 'scope_exclusions': [str(area / 'excluded')],
            'network': False, 'repository_reads': ['fictional-component'],
            'effect_authority': {'read_roots': [read], 'write_roots': [write],
                                 'operations': ['read-reports', 'consolidate-reports']}}
    scope = {'cwd': read, 'read_roots': [read + '/one'], 'write_roots': [write + '/one'],
             'procedure': read + '/procedure.txt', 'resource_evidence': 'fictional finite evidence',
             'network': False, 'repository_reads': ['fictional-component']}

    def scoped(value):
        return c.scoped_task('qa-cleanup', task, {'receipt': json.dumps({'task_scopes': {'qa-cleanup': value}})})

    call('scope.narrow', lambda: scoped(scope), lambda v: {
        'network': v['network'], 'operations': v['effect_authority']['operations'],
        'reads_narrow': v['effect_authority']['read_roots'] == [read + '/one'],
        'writes_narrow': v['effect_authority']['write_roots'] == [write + '/one'],
        'repository_reads': v['repository_reads']})
    for name, key, value in (
            ('network-expand', 'network', True), ('write-into-read', 'write_roots', [read]),
            ('read-outside', 'read_roots', [str(area.parent)]),
            ('missing-evidence', 'resource_evidence', ''), ('missing-procedure', 'procedure', ''),
            ('repository-expand', 'repository_reads', ['other-component']),
            ('ordinary-effect', 'ordinary_effects', {'kind': 'local-ref'}),
            ('excluded', 'read_roots', [str(area / 'excluded')]),
            ('relative', 'cwd', 'relative'), ('dotdot', 'read_roots', [read + '/../other'])):
        changed_scope = copy.deepcopy(scope); changed_scope[key] = value
        call('scope.' + name, lambda v=changed_scope: scoped(v))
    call('scope.absent-admission', lambda: c.scoped_task('qa-cleanup', task, None))

    original = {'semantic': 'PARTIAL', 'summary': 'fictional prior QA preparation',
                'findings': [{'whole': {'candidate': 'fictional', 'dissent': ['retain full meaning']}}],
                'failures': ['fictional unresolved dependency'], 'unknowns': ['fictional pending decision'],
                'artifacts': [], 'category': 'consolidated'}
    repaired = copy.deepcopy(original); repaired['summary'] = 'same fictional preparation, represented completely'
    call('report.whole-prior', lambda: c.task_result(repaired, original), lambda v: v == repaired)
    for name, key in (('erase-findings', 'findings'), ('erase-failures', 'failures'), ('erase-unknowns', 'unknowns')):
        changed_result = copy.deepcopy(repaired); changed_result[key] = []
        call('report.' + name, lambda v=changed_result: c.task_result(v, original))
    changed_result = copy.deepcopy(repaired); changed_result['findings'][0]['whole']['dissent'] = ['summary only']
    call('report.rewrite-dissent', lambda: c.task_result(changed_result, original))
    call('parse.duplicate-key', lambda: c.parse_json('{"package":"one","package":"two"}'))
    call('parse.non-json-number', lambda: c.parse_json('{"value":NaN}'))
    return observations
