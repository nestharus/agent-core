"""Compare actual scoped resources without disposing historical role debt."""
import json
import math
import re
import os
import subprocess
from pathlib import Path

from .contracts import PROFILES, Refusal, digest, required_text, scoped_task


def root(value, exclusions=()):
    path = Path(required_text(value, 'resource root', 4000))
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('absolute resource root required')
    if any(path == Path(p) or path.is_relative_to(Path(p)) or Path(p).is_relative_to(path)
           for p in [*exclusions, *[Path.home()/p for p in PROFILES]]):
        raise Refusal('resource overlaps an excluded store before metadata')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal('resource aliases need their actual custodian; no symlink inference')
    # Existing ancestry is compared by identity too (including bind aliases).
    return path


def overlaps(left, right):
    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
        return True
    def ancestors(path):
        return {(p.stat().st_dev, p.stat().st_ino) for p in (path, *path.parents) if p.exists()}
    def identity(path):
        return (path.stat().st_dev, path.stat().st_ino) if path.exists() else None
    return identity(left) in ancestors(right) or identity(right) in ancestors(left)


def validate(runtime, policy):
    for role, record in policy.items():
        if (role not in runtime.config['roles'] or not isinstance(record, dict)
                or set(record) - {'qa_operation'} != {'original_hold', 'roots', 'unbounded', 'evidence'}
                or type(record['unbounded']) is not bool or not isinstance(record['roots'], list)):
            raise Refusal('legacy resource account needs exact hold, roots, unbounded and evidence')
        if runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))['legacy_hold'] != record['original_hold']:
            raise Refusal('resource account does not describe the actual retained hold')
        required_text(record['evidence'], 'supported original resource scope, not a renamed package')
        if not record['unbounded'] and not record['roots']:
            raise Refusal('unknown legacy scope cannot be declared independent')
        for value in record['roots']:
            root(value, runtime.config.get('artifact_exclusions', []))
        if 'qa_operation' in record:
            qa_observation(runtime, role, record)


def scope_excluded(runtime, name, admission):
    scope = json.loads(admission['receipt']).get('task_scopes', {}).get(name, {}) if admission else {}
    values = scope.get('read_roots', []) + scope.get('write_roots', []) + [scope.get('cwd', '')]
    return any(Path(value) == Path(p) or Path(value).is_relative_to(Path(p)) or Path(p).is_relative_to(Path(value))
               for value in values for p in runtime.config.get('artifact_exclusions', []))


def qa_observation(runtime, role, record):
    """Validate Work's attributed evidence and exact proposed policy, not authorship.

    This structural check also runs before issuance. Only qa_operation, through
    the current trusted Work capability, can apply it. Digests bind bytes; they
    cannot prove native authorship or the truth/completeness of external facts.
    """
    account = record['qa_operation']
    if (role != 'QA' or record['unbounded'] is not True
            or not isinstance(account, dict) or set(account) != {'statement', 'binding', 'policy'}):
        raise Refusal('operation-relative QA policy must preserve global unknown scope')
    statement, binding, policy = (account[k] for k in ('statement', 'binding', 'policy'))
    fields = {'version', 'custodian', 'reference', 'statement_sha256', 'authority',
              'expires', 'scope', 'source', 'inputs', 'relevant_roots'}
    if (not isinstance(policy, dict) or set(policy) != fields or policy['version'] != 'qa-operation-v1'
            or not isinstance(statement, dict) or not statement
            or policy['statement_sha256'] != digest(statement)):
        raise Refusal('whole attributed observation and exact selected policy required')
    enrollment = runtime.one('SELECT owner,legacy_hold FROM enrollments WHERE role=?', (role,))
    if (not enrollment or policy['custodian'] != enrollment['owner']
            or record['original_hold'] != enrollment['legacy_hold']):
        raise Refusal('observation policy differs from actual retained QA custodian/hold')
    for key in ('reference', 'authority'):
        required_text(policy[key], 'accountable Work observation ' + key, 4000)
    if (type(policy['expires']) not in {int, float} or not math.isfinite(policy['expires'])
            or policy['expires'] <= runtime.clock()):
        raise Refusal('operation-relative selection expired')
    if (not isinstance(binding, dict) or set(binding) != {'task', 'package', 'admission_sha256'}
            or binding['task'] != 'qa-execution'):
        raise Refusal('one exact admitted QA execution binding required')
    required_text(binding['package'], 'actual independently admitted package')
    if not isinstance(binding['admission_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', binding['admission_sha256']):
        raise Refusal('exact whole admission digest required')
    source = policy['source']
    if (not isinstance(source, dict) or set(source) != {'common_git', 'tree', 'parents'}
            or not isinstance(source['tree'], str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', source['tree'])
            or not isinstance(source['parents'], list) or len(source['parents']) > 32
            or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', v) for v in source['parents'])
            or not isinstance(policy['scope'], dict)
            or not isinstance(policy['inputs'], list) or len(policy['inputs']) > 32
            or not isinstance(policy['relevant_roots'], list) or len(policy['relevant_roots']) > 32):
        raise Refusal('exact finite QA source topology, scope and inputs required')
    exclusions = runtime.config.get('artifact_exclusions', [])
    root(source['common_git'], exclusions)
    for value in policy['relevant_roots']:
        root(value, exclusions)
    seen = set()
    for item in policy['inputs']:
        if (not isinstance(item, dict) or set(item) != {'path', 'sha256'}
                or not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise Refusal('exact selected supporting input byte pins required')
        path = str(root(item['path'], exclusions))
        if path in seen:
            raise Refusal('duplicate selected QA input')
        seen.add(path)
    return statement


def qa_operation(runtime, row, record):
    """Compare a recorded bounded fact; return no grant, lease or acceptance.

    All paths are exclusion-checked before policy/tool/source metadata. Actual
    adapter source/export/collection/acceptance checks remain independently owed.
    """
    if not runtime.processing:
        raise Refusal('current Work selection required')
    cap, selected = runtime.processing.current()
    if (cap['issuer'] != runtime.config['roles']['Work']['owner']
            or row['task'] not in selected['tasks']
            or selected.get('service', {}).get('legacy_resources', {}).get('QA') != record
            or not runtime.processing.boards or 'Work' not in runtime.processing.boards):
        raise Refusal('exact current genuine Work-selected QA policy required')
    runtime.processing.boards['Work'].verify_authority(runtime)
    qa_observation(runtime, row['role'], record)
    policy = record['qa_operation']['policy']
    binding = record['qa_operation']['binding']
    if (row['role'] != 'QA' or row['phase'] != 'execution'
            or row['task'] != binding['task'] or row['package'] != binding['package']):
        raise Refusal('QA observation does not describe this operation')
    task = runtime.config['tasks'][row['task']]
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    if (not admission or digest(admission) != binding['admission_sha256']
            or task['role'] != 'QA' or task['phase'] != 'execution'
            or not task.get('require_package_scope') or scope_excluded(runtime, row['task'], admission)):
        raise Refusal('unchanged genuine narrowed QA admission required before metadata')
    task = scoped_task(row['task'], task, admission)
    scope = task['admitted_scope']
    if (scope != policy['scope'] or task['network'] is not False
            or task['effect_authority']['owner'] != runtime.enrollment('QA')['owner']
            or task['effect_authority']['operations'] != ['execute-admitted-qa']):
        raise Refusal('selected observation cannot admit changed operation/scope/network/role')
    exclusions = runtime.config.get('artifact_exclusions', [])
    for path in scope['read_roots'] + scope['write_roots'] + [scope['cwd'], scope['procedure']]:
        root(path, exclusions)
    from . import prospective, ordinary
    epoch = prospective.current(runtime, row['task'])
    if not epoch or not epoch['policy']['ordinary_effects']:
        raise Refusal('current finite prospective QA authority required')
    p = scope.get('ordinary_effects', {})
    if (not isinstance(p, dict) or p.get('kind') != 'local-qa'
            or p.get('git') != '/usr/bin/git'
            or set(p.get('public_executables', {})) != {'command', 'readback'}
            or any(r.get('owner') != runtime.enrollment('QA')['owner'] for r in p.get('resources', []))):
        raise Refusal('only actual QA-owned local QA resources permitted')
    # Topology and supplementary inputs must be in the actual read ceiling;
    # their presence in evidence is not a path grant or a padding-root license.
    reads = [Path(v) for v in scope['read_roots']]
    for path in [policy['source']['common_git'], *[i['path'] for i in policy['inputs']]]:
        if not any(Path(path).is_relative_to(r) for r in reads):
            raise Refusal('selected QA evidence input is outside admitted read authority')
    # A queue ID is not a job ID. Public policy validation supports a genuine
    # pre-reservation projection; never fabricate an attempt/birth/launch proof.
    current = runtime.one('SELECT * FROM jobs WHERE id=?', (row.get('id'),))
    if current:
        if any(current[k] != row[k] for k in ('role', 'phase', 'task', 'package')):
            raise Refusal('original QA job identity differs')
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (current['id'],))
        if (not frozen or json.loads(frozen['task']) != runtime.config['tasks'][row['task']]
                or not frozen['admission'] or json.loads(frozen['admission']) != admission):
            raise Refusal('original QA job resources cannot be rebound')
    policy_job = current if current and current['active_attempt'] else {
        k:row[k] for k in ('role', 'phase', 'task', 'package')}
    _, p = ordinary.policy_for(runtime, policy_job)
    for item in policy['inputs']:
        ordinary.frozen_file(runtime, item['path'], scope['read_roots'], item['sha256'])
    # Read-only current source/ref/topology checks. No checkout substitution,
    # source body export, native/provider invocation or effect replay.
    def git(*args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
        result = subprocess.run([p['git'], '--no-replace-objects', '--no-optional-locks',
                                 '-c', 'core.hooksPath=/dev/null', '-C', p['repository'], *args],
                                capture_output=True, check=True, timeout=p['timeout'], env=env)
        return result.stdout.decode('utf-8').strip()
    if git('rev-parse', '--show-toplevel') != p['repository']:
        raise Refusal('actual QA repository cwd changed')
    common = root(git('rev-parse', '--path-format=absolute', '--git-common-dir'), exclusions)
    if str(common) != policy['source']['common_git']:
        raise Refusal('actual common Git differs from observed QA operation')
    if (git('rev-parse', '--verify', p['source_ref'] + '^{commit}') != p['source_head']
            or git('rev-parse', '--verify', p['source_head'] + '^{tree}') != policy['source']['tree']
            or git('show', '-s', '--format=%P', p['source_head']).split() != policy['source']['parents']):
        raise Refusal('current exact QA source/ref/tree/ordered parent differs')
    # No unfamiliar lease can be treated as an empty relevant set. The
    # original immutable policy maps a foreign lease, not its resource label.
    own = current['active_attempt'] if current and all(current[k] == row[k] for k in ('role', 'task', 'package')) else None
    held = list(policy['relevant_roots'])
    for lease in runtime.rows('SELECT * FROM ordinary_resources'):
        if own and lease['attempt'] == own:
            continue
        run = runtime.one('SELECT * FROM ordinary_runs WHERE attempt=?', (lease['attempt'],))
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (run['job'],)) if run else None
        job = runtime.one('SELECT * FROM jobs WHERE id=?', (run['job'],)) if run else None
        if not frozen or not frozen['admission'] or not job:
            raise Refusal('unmapped original resource lease remains unknown')
        prior_admission = json.loads(frozen['admission'])
        if scope_excluded(runtime, job['task'], prior_admission):
            raise Refusal('original lease scope excluded before metadata')
        prior = scoped_task(job['task'], json.loads(frozen['task']), prior_admission)
        policy = prior['admitted_scope'].get('ordinary_effects', {})
        if (json.loads(run['policy']) != policy
                or lease['resource'] not in {r['key'] for r in policy.get('resources', [])}):
            raise Refusal('lease lacks its original frozen operation map')
        held += prior['effect_authority']['read_roots'] + prior['effect_authority']['write_roots'] + [prior['cwd']]
    return held


def blocked(runtime, row, task=None):
    enrollment = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (row['role'],))
    if not enrollment or not enrollment['legacy_hold']:
        return False
    task = task or runtime.config['tasks'][row['task']]
    if runtime.processing and row['phase'] == 'proposer' and task['effects'] == 'none':
        return False
    if not runtime.processing:
        return True
    selection = runtime.processing.current()[1]
    if row['role'] == 'Branch' and row['phase'] == 'integrator':
        admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
        try:
            if scope_excluded(runtime, row['task'], admission):
                return True
            exact = scoped_task(row['task'], task, admission)
            from .ref_scope import eligible
            if eligible(runtime, row, exact):
                return False
        except (Refusal, KeyError):
            pass  # Ordinary local/ref/network path rules below still refuse.
    record = selection.get('service', {}).get('legacy_resources', {}).get(row['role'])
    if not record or record['original_hold'] != enrollment['legacy_hold']:
        return True
    operation_held = []
    if 'qa_operation' in record:
        try:
            operation_held = qa_operation(runtime, row, record)
        except (Refusal, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            return True
    elif record['unbounded']:
        return True
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    # Independence needs a genuine narrowed admission, not a package label.
    if task.get('require_package_scope'):
        if not admission:
            return True
        task = scoped_task(row['task'], task, admission)
    elif not task.get('effect_authority'):
        return True  # No actual configured resource boundary to compare.
    if task.get('network') or 'organize-authorized-refs' in task['effect_authority'].get('operations', []):
        return True  # Path separation alone cannot prove external/shared-ref independence.
    exclusions = runtime.config.get('artifact_exclusions', [])
    selected = [root(p, exclusions) for p in task['effect_authority']['read_roots'] + task['effect_authority']['write_roots'] + [task['cwd']]]
    held = [root(p, exclusions) for p in record['roots'] + operation_held]
    # Actual unresolved local jobs remain owners of their configured/admitted
    # roots even when an external legacy inventory was narrower.
    for job in runtime.rows("SELECT * FROM jobs WHERE role=? AND effects NOT IN ('none','reconciled')", (row['role'],)):
        if row.get('id') == job['id']:
            continue  # Reconcile this operation against OTHER unresolved owners.
        from .configuration import task_for_job
        prior = task_for_job(runtime, job)
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (job['id'],))
        if frozen:
            prior = json.loads(frozen['task'])
            prior_admission = json.loads(frozen['admission']) if frozen['admission'] else None
        elif prior.get('require_package_scope'):
            return True  # Missing original scope remains unknown, never current admission laundering.
        else:
            prior_admission = None
        try:
            if scope_excluded(runtime, job['task'], prior_admission):
                return True
            prior = scoped_task(job['task'], prior, prior_admission)
            authority = prior['effect_authority']
        except (Refusal, KeyError):
            return True
        held.extend(root(p, exclusions) for p in authority['read_roots'] + authority['write_roots'] + [prior['cwd']])
    return not selected or any(overlaps(a, b) for a in selected for b in held)
