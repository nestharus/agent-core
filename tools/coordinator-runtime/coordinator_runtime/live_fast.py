"""Explicit controller-only live fast control, separate from immutable source.

The selected configuration delegates only a bounded policy read to the runtime.
It does not expose control/helper bytes to an execute-only QA task or grant it
source reading. Actual processing admission still authenticates current rights.
"""
import hashlib
from pathlib import Path
import re
from types import ModuleType
from .contracts import Refusal, digest, required_text
from .resource_scopes import root
from .custody import read_file

VERSION = 'shared-live-fast-tier-v1'
FIELDS = {'version', 'path', 'helper_sha256', 'tasks', 'auxiliary'}
AUXILIARY = {'classifier', 'diagnosis', 'input-mapping', 'input-locator'}
ROLES = {'Work', 'Branch', 'Reviews', 'QA'}


def declaration(value, tasks, exclusions=()):
    if (not isinstance(value, dict) or set(value) != FIELDS
            or value['version'] != VERSION or not isinstance(value['tasks'], list)
            or not value['tasks'] or not all(isinstance(t,str) for t in value['tasks'])
            or not isinstance(value['path'],str) or len(set(value['tasks'])) != len(value['tasks'])
            or set(value['tasks']) - set(tasks)
            or not isinstance(value['helper_sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', value['helper_sha256'])):
        raise Refusal('explicit shared live fast control and immutable helper binding required')
    auxiliary = value['auxiliary']
    if (not isinstance(auxiliary, dict) or set(auxiliary) - AUXILIARY
            or any(not isinstance(roles,list) or not roles or not all(isinstance(r,str) for r in roles)
                   or len(set(roles)) != len(roles) or set(roles) - ROLES for roles in auxiliary.values())):
        raise Refusal('explicit auxiliary context kinds and source roles required')
    if isinstance(tasks,dict):
        granted = {tasks[t]['role'] for t in value['tasks']}
        if any(set(roles) - granted for roles in auxiliary.values()):
            raise Refusal('auxiliary control requires selected original role grant')
    from .public_runtime import public_path
    path = public_path(value['path'], exclusions)
    if str(path) != value['path'] or path.name != 'fast-tier':
        raise Refusal('exact public fast-tier control file required')
    return value


def helper(config, package=None):
    value = declaration(config.get('fast_tier'), config['tasks'], config.get('artifact_exclusions', []))
    path = Path(__file__).parents[2] / 'direct-child' / 'fast_tier.py'
    # Implementation dependency, not task source material. Exclusions precede
    # metadata/body acquisition and the exact source pin precedes execution.
    root(str(path), config.get('artifact_exclusions', []), metadata=False)
    body = read_file(root(str(path), config.get('artifact_exclusions', [])), 65536)[0]
    if hashlib.sha256(body).hexdigest() != value['helper_sha256']:
        raise Refusal('selected immutable fast helper changed')
    if package is not None:
        if getattr(package, 'failed', True) or not hasattr(package, 'fast_tier'):
            raise Refusal('frozen fast dependency required')
        return package.fast_tier
    module = ModuleType('_selected_fast_' + value['helper_sha256'])
    module.__file__ = str(path)
    exec(compile(body, str(path), 'exec'), module.__dict__)
    return module


def snapshot(runtime, attempt, package=None):
    runtime.authorize_launch(attempt)
    value = declaration(runtime.config.get('fast_tier'), runtime.config['tasks'],
                        runtime.config.get('artifact_exclusions', []))
    row = runtime.attempt(attempt)
    if row['job'] is not None:
        task = runtime.job(row['job'])['task']
        if task not in value['tasks']:
            raise Refusal('current task lacks explicit live fast control authority')
    else:
        role = runtime.event(row['event'])['role']
        if role not in value['auxiliary'].get(row['kind'], []):
            raise Refusal('current auxiliary context lacks explicit live fast control authority')
    module = helper(runtime.config, package)
    # This is an explicitly delegated controller read, not read-source implied
    # by a safe-file label or a copy of the switch in a selected checkout.
    path = root(value['path'], runtime.config.get('artifact_exclusions', []))
    try:
        force = module.enabled(path)
    except ValueError as error:
        raise Refusal(str(error)) from error
    runtime.authorize_launch(attempt)
    return module, force


def extend(runtime, original, candidate, option):
    if option is None:
        return
    from .configuration import assert_current
    if runtime is None or digest(runtime.config) != digest(original):
        raise Refusal('live control requires current enrolled runtime')
    assert_current(runtime)
    if not isinstance(option, dict) or set(option) != {'control', 'bindings'}:
        raise Refusal('explicit live control choice and original grant bindings required')
    control = declaration(option['control'], original['tasks'], candidate.get('artifact_exclusions', []))
    bindings = option['bindings']
    if not isinstance(bindings, dict) or set(bindings) != set(control['tasks']):
        raise Refusal('every selected live control task needs its original grant binding')
    for name, proof in bindings.items():
        prior = original['tasks'][name]
        owner = prior['effect_authority']['owner']
        enrolled = runtime.one('SELECT owner,grant_id,intake FROM enrollments WHERE role=?', (prior['role'],))
        if (not isinstance(proof, dict) or set(proof) != {'configuration', 'role_owner', 'original_grant', 'authority'}
                or proof['configuration'] != digest(original) or proof['role_owner'] != owner
                or owner != original['roles'][prior['role']]['owner'] or not enrolled
                or enrolled['owner'] != owner or enrolled['grant_id'] != proof['original_grant']
                or enrolled['intake'] != 0):
            raise Refusal('live control requires exact configuration, owner and stopped original grant')
        required_text(proof['authority'], 'attributed controller-only mutable control choice', 4000)
    # Validation of all lexical/authority operands precedes acquisition.
    import copy
    candidate['fast_tier'] = copy.deepcopy(control)
    module = helper(candidate)
    path = root(control['path'], candidate.get('artifact_exclusions', []))
    try:
        module.enabled(path)
    except ValueError as error:
        raise Refusal(str(error)) from error
