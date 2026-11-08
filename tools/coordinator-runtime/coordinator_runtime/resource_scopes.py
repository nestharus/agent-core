"""Compare actual scoped resources without disposing historical role debt."""
import json
import math
import re
import os
import subprocess
import sqlite3
from contextlib import nullcontext
from pathlib import Path

from .contracts import OPERATIONS, PROFILES, Refusal, canonical_uuid, digest, encode, required_text, scoped_task, qa_branch_sequence


def root(value, exclusions=(), *, metadata=True):
    path = Path(required_text(value, 'resource root', 4000))
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('absolute resource root required')
    if any(path == Path(p) or path.is_relative_to(Path(p)) or Path(p).is_relative_to(path)
           for p in [*exclusions, *[Path.home()/p for p in PROFILES]]):
        raise Refusal('resource overlaps an excluded store before metadata')
    if metadata and any(p.is_symlink() for p in (path, *path.parents)):
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


def access_modes(task, exclusions):
    """Configured access, including staged publication rights, not effect success.

    execution_spec relocates owned/staged writes to an attempt directory. Its
    configured cwd is therefore only a read dependency. A direct workspace-write
    task can write its cwd; canonical write roots survive staging and fencing.
    """
    authority = task['effect_authority']
    reads, writes = authority['read_roots'], authority['write_roots']
    operations = authority['operations']
    if (not isinstance(reads, list) or not isinstance(writes, list)
            or not isinstance(operations, list) or not operations or set(operations) - OPERATIONS
            or task.get('sandbox') not in {'read-only', 'workspace-write'}
            or task.get('effects') not in {'none', 'owned-artifacts', 'owner-reconcile'}
            or task.get('execution') == 'owner'
            or type(task.get('network', False)) is not bool or task.get('network')
            or 'organize-authorized-refs' in operations):
        raise Refusal('unknown or external original resource authority remains held')
    ordinary = task.get('admitted_scope', {}).get('ordinary_effects')
    if ordinary is not None and not isinstance(ordinary, dict):
        raise Refusal('opaque original ordinary authority')
    if 'execute-admitted-qa' in operations and (not ordinary or ordinary.get('kind') != 'local-qa'):
        raise Refusal('unmapped original QA operation remains held')
    if ordinary and (ordinary.get('kind') != 'local-qa' or 'execute-admitted-qa' not in operations):
        raise Refusal('unknown original external/ref operation remains held')
    if task['effects'] == 'none' and (writes or task['sandbox'] != 'read-only'):
        raise Refusal('inconsistent original read-only authority')
    if task['effects'] == 'owned-artifacts' and (writes or task['sandbox'] != 'workspace-write'):
        raise Refusal('unmapped original owned-artifact authority')
    reads = [*reads, task['cwd']]
    writes = list(writes)
    if task.get('routine_completion'):
        targets = task['routine_completion'].get('targets') if isinstance(task['routine_completion'], dict) else None
        if (not isinstance(targets, list) or not targets
                or any(not isinstance(p, str) or not any(Path(p).is_relative_to(Path(w)) for w in writes) for p in targets)):
            raise Refusal('unmapped original canonical publication targets')
    if (task['sandbox'] == 'workspace-write' and task['effects'] == 'owner-reconcile'
            and not task.get('routine_completion')):
        writes.append(task['cwd'])
    # Check the whole map lexically before touching any of its metadata.
    for value in reads + writes:
        root(value, exclusions, metadata=False)
    return ([root(p, exclusions) for p in reads], [root(p, exclusions) for p in writes])


def original_modes(runtime, job):
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        return _original_modes(runtime, job)


def _original_modes(runtime, job):
    """Project only the immutable access map; never acquire old task/return bodies.

    Missing originals refuse. Neither a current configuration/admission nor a
    permanent execution fence can restamp retained publication/effect debt.
    """
    fields = ('cwd', 'sandbox', 'effects', 'network', 'execution', 'require_package_scope',
              'scope_roots', 'package_narrowing', 'scope_exclusions',
              'linked_repositories', 'repository_reads')
    paths = ['$.' + k for k in fields] + ['$.effect_authority.' + k for k in ('read_roots', 'write_roots', 'operations')]
    prefix = '$.task_scopes.' + json.dumps(job['task'])
    scope_fields = ('cwd', 'read_roots', 'write_roots', 'network', 'procedure', 'repository_reads')
    scope_paths = [prefix + '.' + k for k in scope_fields] + [prefix + '.ordinary_effects.kind']
    receipt = "json_extract(admission,'$.receipt')"
    frozen = runtime.one('SELECT json_extract(task,' + ','.join('?' for _ in paths) + ') AS access, '
        "json_type(task,'$.routine_completion') AS completion, json_extract(task,'$.routine_completion.targets') AS targets, "
        'json_extract(' + receipt + ',' + ','.join('?' for _ in scope_paths) + ') AS scope, '
        'json_type(' + receipt + ',?) AS ordinary, '
        'length(json_extract(' + receipt + ',?))>0 AS evidence '
        'FROM job_resource_policies WHERE job=?', (*paths, *scope_paths, prefix + '.ordinary_effects', prefix + '.resource_evidence', job['id']))
    if not frozen or not frozen['access']:
        raise Refusal('missing original frozen resource map')
    values = json.loads(frozen['access'])
    task = {k: v for k, v in zip(fields, values) if v is not None}
    task['effect_authority'] = dict(zip(('read_roots', 'write_roots', 'operations'), values[len(fields):]))
    if frozen['completion'] not in {None, 'null', 'object'}:
        raise Refusal('unknown original publication map')
    if frozen['completion'] == 'object':
        task['routine_completion'] = {'targets': json.loads(frozen['targets']) if frozen['targets'] else None}
    admission = None
    if task.get('require_package_scope'):
        if not frozen['scope'] or not frozen['evidence']:
            raise Refusal('missing original admitted resource map')
        values = json.loads(frozen['scope'])
        scope = {k: v for k, v in zip(scope_fields, values) if v is not None}
        # Only presence is needed by scoped_task; no old evidence body is read.
        scope['resource_evidence'] = True
        if frozen['ordinary'] not in {None, 'null', 'object'}:
            raise Refusal('opaque original ordinary operation')
        if frozen['ordinary'] == 'object':
            scope['ordinary_effects'] = {'kind': values[-1]}
        admission = {'receipt': json.dumps({'task_scopes': {job['task']: scope}})}
        if scope_excluded(runtime, job['task'], admission):
            raise Refusal('original admitted scope excluded before metadata')
        for value in scope.get('read_roots', []) + scope.get('write_roots', []) + [scope.get('cwd')]:
            root(value, runtime.config.get('artifact_exclusions', []), metadata=False)
    task = scoped_task(job['task'], task, admission)
    native = task.get('execution') == 'owner'
    if native:
        from .reviews import original_resources
        reads, writes = original_resources(runtime, job, task)
    else:
        reads, writes = access_modes(task, runtime.config.get('artifact_exclusions', []))
    # The runtime creates fresh per-attempt writable staging; these original
    # directories stay charged without acquiring their names, contents or sizes.
    staging = []
    if native or task['effects'] != 'none':
        for attempt in runtime.rows("SELECT id FROM attempts WHERE job=? AND kind='task'", (job['id'],)):
            canonical_uuid(attempt['id'])
            staging.append(root(str(runtime.home/'artifacts'/attempt['id']), runtime.config.get('artifact_exclusions', []), metadata=False))
            if native:
                # Opening attempts own this possible handle too. It is never
                # part of the unique artifacts-child staging exemption.
                writes.append(str(runtime.home/'review-handles'/attempt['id']))
        writes.extend(staging)
    # A retained publication is a write dependency even after execution closure.
    for item in runtime.rows('SELECT p.target,p.temp FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=?', (job['id'],)):
        for value in (item['target'], item['temp']):
            if value is not None:
                writes.append(root(value, runtime.config.get('artifact_exclusions', []), metadata=False))
    # Native model read-only rights still have executor writes. Validate the
    # entire assembled map (including publication temporaries) before metadata.
    exclusions = runtime.config.get('artifact_exclusions', [])
    for value in reads + writes:
        root(str(value), exclusions, metadata=False)
    return ([root(str(p), exclusions) for p in reads],
            [root(str(p), exclusions) for p in writes], staging)


def validate(runtime, policy, selection=None):
    for role, record in policy.items():
        if (role not in runtime.config['roles'] or not isinstance(record, dict)
                or set(record) - {'qa_operation', 'qa_operations', 'reviews_report', 'native_review_return'} != {'original_hold', 'roots', 'unbounded', 'evidence'}
                or type(record['unbounded']) is not bool or not isinstance(record['roots'], list)):
            raise Refusal('legacy resource account needs exact hold, roots, unbounded and evidence')
        if runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))['legacy_hold'] != record['original_hold']:
            raise Refusal('resource account does not describe the actual retained hold')
        required_text(record['evidence'], 'supported original resource scope, not a renamed package')
        if not record['unbounded'] and not record['roots']:
            raise Refusal('unknown legacy scope cannot be declared independent')
        for value in record['roots']:
            root(value, runtime.config.get('artifact_exclusions', []))
        accounts = qa_accounts(record)
        if accounts:
            packages = []
            for account in accounts:
                qa_observation(runtime, role, record, account)
                binding = account['binding']
                packages.append(binding['package'])
                if selection is not None and 'topic' in binding:
                    scope = selection.get('software_admission', {}).get('scopes', {}).get(binding['topic'])
                    if (not scope or digest(scope) != binding['scope_sha256']
                            or not binding['package'].startswith(scope['package_prefix'])
                            or scope['task_scopes'].get('qa-execution') != account['policy']['scope']
                            or account.get('cleanup') and scope['task_scopes'].get('qa-cleanup') != account['cleanup']['scope']):
                        raise Refusal('QA policy must bind exact selected software topic/scopes')
            if len(packages) != len(set(packages)):
                raise Refusal('independent QA policies need distinct packages')
        if 'native_review_return' in record:
            from .native_review_scope import validate as validate_native
            validate_native(runtime, role, record, selection)
        if 'reviews_report' in record:
            from .report_scope import validate as validate_report
            validate_report(runtime, role, record, selection)



def scope_excluded(runtime, name, admission):
    scope = json.loads(admission['receipt']).get('task_scopes', {}).get(name, {}) if admission else {}
    values = scope.get('read_roots', []) + scope.get('write_roots', []) + [scope.get('cwd', '')]
    return any(Path(value) == Path(p) or Path(value).is_relative_to(Path(p)) or Path(p).is_relative_to(Path(value))
               for value in values for p in runtime.config.get('artifact_exclusions', []))


def qa_accounts(record):
    if 'qa_operations' in record:
        values = record['qa_operations']
        # Five executing + one accepted cleanup + one waiting execution need
        # seven exact package accounts, without increasing either phase slot.
        if ('qa_operation' in record or not isinstance(values, list) or not 1 <= len(values) <= 7):
            raise Refusal('one to seven independent selected QA operation policies required')
        return values
    return [record['qa_operation']] if 'qa_operation' in record else []


def qa_observation(runtime, role, record, account=None):
    """Validate Work's attributed evidence and exact proposed policy, not authorship.

    This structural check also runs before issuance. Only qa_operation, through
    the current trusted Work capability, can apply it. Digests bind bytes; they
    cannot prove native authorship or the truth/completeness of external facts.
    """
    account = record['qa_operation'] if account is None else account
    if (role != 'QA' or record['unbounded'] is not True
            or not isinstance(account, dict) or set(account) - {'cleanup'} != {'statement', 'binding', 'policy'}):
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
    if (not isinstance(binding, dict) or set(binding) not in ({'task', 'package', 'admission_sha256'}, {'task', 'package', 'topic', 'scope_sha256'})
            or binding['task'] != 'qa-execution'):
        raise Refusal('one exact admitted QA execution binding required')
    required_text(binding['package'], 'actual independently admitted package')
    pin = binding.get('admission_sha256', binding.get('scope_sha256'))
    if 'topic' in binding:
        required_text(binding['topic'], 'selected software admission topic', 128)
    if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
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
    # Proposed policy validation is lexical. Task-specific exclusions must run
    # in scoped_task before any selected input's filesystem metadata.
    root(source['common_git'], exclusions, metadata=False)
    for value in policy['relevant_roots']:
        root(value, exclusions, metadata=False)
    seen = set()
    for item in policy['inputs']:
        if (not isinstance(item, dict) or set(item) != {'path', 'sha256'}
                or not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise Refusal('exact selected supporting input byte pins required')
        path = str(root(item['path'], exclusions, metadata=False))
        if path in seen:
            raise Refusal('duplicate selected QA input')
        seen.add(path)
    if 'cleanup' in account:
        cleanup = account['cleanup']
        if (not isinstance(cleanup, dict) or set(cleanup) != {'task', 'scope', 'procedure_sha256'}
                or cleanup['task'] != 'qa-cleanup' or not isinstance(cleanup['scope'], dict)
                or cleanup['scope'].get('ordinary_effects') or cleanup['scope'].get('network') is not False
                or not re.fullmatch('[0-9a-f]{64}', cleanup['procedure_sha256'])):
            raise Refusal('separate exact no-effect same-package cleanup scope required')
        for value in cleanup['scope'].get('read_roots', []) + cleanup['scope'].get('write_roots', []) + [cleanup['scope'].get('cwd'), cleanup['scope'].get('procedure')]:
            root(value, exclusions, metadata=False)
        task = runtime.config['tasks']['qa-cleanup']
        if not task.get('package_narrowing') or task['effects'] != 'owned-artifacts':
            raise Refusal('cleanup must narrow the existing report-only task')
        scoped_task('qa-cleanup', task, {'receipt': json.dumps({'task_scopes': {'qa-cleanup': cleanup['scope']}})})
    return statement


def qa_operation(runtime, row, record, account=None):
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
    accounts = qa_accounts(record)
    if account is None:
        matches = [a for a in accounts if a['binding']['package'] == row['package']]
        if len(matches) != 1:
            raise Refusal('one exact selected package operation required')
        account = matches[0]
    if account not in accounts:
        raise Refusal('unselected QA operation')
    qa_observation(runtime, row['role'], record, account)
    if row['task'] == 'qa-cleanup':
        return qa_cleanup(runtime, row, record, account)
    policy = account['policy']
    binding = account['binding']
    if (row['role'] != 'QA' or row['phase'] != 'execution'
            or row['task'] != binding['task'] or row['package'] != binding['package']):
        raise Refusal('QA observation does not describe this operation')
    task = runtime.config['tasks'][row['task']]
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    if 'topic' in binding:
        from .processing_admission import resolved
        admission = resolved(runtime, row['package'], binding['topic'], binding['scope_sha256'])
    if (not admission or 'admission_sha256' in binding and digest(admission) != binding['admission_sha256']
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
        root(path, exclusions)
    # A queue ID is not a job ID. Public policy validation supports a genuine
    # pre-reservation projection; never fabricate an attempt/birth/launch proof.
    current = runtime.one('SELECT id,role,phase,task,package,active_attempt,members FROM jobs WHERE id=?', (row.get('id'),))
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
    # Foreign leases are mapped in blocked for every route, including Reviews.
    # Unmoded attributed relevant roots remain exclusive dependencies.
    return list(policy['relevant_roots'])


def blocked(runtime, row, task=None):
    # Serialize metadata, physical admission and protected authentication with
    # cooperative policy/hold/resource changes, including direct callers.
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        return _blocked(runtime, row, task)


def _blocked(runtime, row, task=None):
    if qa_branch_sequence(runtime.config) and row['task'] == 'branch-integrator':
        try:
            from .ordinary import branch_dependency
            branch_dependency(runtime, row)
        except (Refusal, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            return True
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
    if qa_accounts(record):
        try:
            operation_held = qa_operation(runtime, row, record)
        except (Refusal, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            return True
    elif 'native_review_return' in record:
        try:
            from .native_review_scope import preflight
            operation_held = preflight(runtime, row, record)
        except (Refusal, OSError, KeyError, TypeError, ValueError):
            return True
    elif 'reviews_report' in record:
        try:
            from .report_scope import eligible
            eligible(runtime, row, record)
        except (Refusal, OSError, KeyError, TypeError, ValueError):
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
    try:
        reads, writes = access_modes(task, exclusions)
        future_staging = None
        if task['sandbox'] == 'workspace-write' and task['effects'] != 'none':
            directory = root(str(runtime.home/'artifacts'), exclusions)
            if row.get('active_attempt'):
                canonical_uuid(row['active_attempt'])
                directory /= row['active_attempt']
                writes.append(root(str(directory), exclusions))
            else:
                future_staging = directory
        held_reads = []
        held_writes = [root(p, exclusions) for p in record['roots'] + operation_held]
        original_staging = []
        mapped = {}

        def retain(job):
            if job['id'] not in mapped:
                mapped[job['id']] = original_modes(runtime, job)
                r, w, staging = mapped[job['id']]
                held_reads.extend(r)
                held_writes.extend(w)
                original_staging.extend(staging)

        # These scalar identities select immutable maps, never old return,
        # capture, error, receipt or full job/task bodies. UNKNOWN is unchanged.
        for job in runtime.rows("SELECT id,task FROM jobs WHERE effects NOT IN ('none','reconciled')"):
            if row.get('id') != job['id']:
                retain(job)
        # Effect reconciliation alone cannot clear an interrupted or incomplete
        # publication. These scalar state predicates acquire no receipt bodies.
        for job in runtime.rows('SELECT j.id,j.task FROM jobs j WHERE '
                "EXISTS (SELECT 1 FROM attempts a JOIN routine_runs r ON r.attempt=a.id WHERE a.job=j.id AND r.state IS NOT 'reconciled') OR "
                "EXISTS (SELECT 1 FROM attempts a JOIN file_publications p ON p.attempt=a.id WHERE a.job=j.id AND (p.state IS NOT 'published' OR p.error IS NOT NULL))"):
            if row.get('id') != job['id']:
                retain(job)
        # An orphan/opaque lease is globally unknown, even on a report route.
        for lease in runtime.rows('SELECT resource,attempt FROM ordinary_resources'):
            job = runtime.one('SELECT j.id,j.task FROM ordinary_runs r JOIN jobs j ON j.id=r.job WHERE r.attempt=?', (lease['attempt'],))
            if not job:
                return True
            if job['id'] == row.get('id'):
                continue
            path = '$.task_scopes.' + json.dumps(job['task']) + '.ordinary_effects'
            original = runtime.one('SELECT json(r.policy)=json(json_extract(json_extract(f.admission,\'$.receipt\'),?)) AS matches '
                'FROM ordinary_runs r JOIN job_resource_policies f ON f.job=r.job WHERE r.attempt=? '
                "AND EXISTS (SELECT 1 FROM json_each(r.policy,'$.resources') k WHERE json_extract(k.value,'$.key')=?)",
                (path, lease['attempt'], lease['resource']))
            if not original or not original['matches']:
                return True
            retain(job)
        if future_staging:
            # A fresh attempt has a new PRIMARY KEY UUID and mkdir(exist_ok=False).
            # Its direct child cannot be an original attempt's directory. Broad
            # parent access and unmapped descendants still conflict; this is no
            # grant to write the artifacts parent or a release of old staging.
            for directory in original_staging:
                if directory.exists() and any(parent.exists() and directory.samefile(parent)
                        for parent in (future_staging, *future_staging.parents)):
                    return True  # An ancestor bind alias is not a distinct child.
            for held in held_reads + held_writes:
                if (not any(held.is_relative_to(p) for p in original_staging)
                        and overlaps(future_staging, held)):
                    return True
        conflict = not (reads or writes) or (any(overlaps(a, b) for a in writes for b in held_reads + held_writes)
                                        or any(overlaps(a, b) for a in reads for b in held_writes))
        if conflict:
            return True
        if 'native_review_return' in record:
            from .native_review_scope import _authenticate
            _authenticate(runtime, row, record)
        return False
    except (Refusal, OSError, KeyError, TypeError, ValueError, sqlite3.Error):
        return True


def qa_cleanup(runtime, row, record, account):
    """Consolidation consumes this accepted execution, never a model DONE."""
    from . import ordinary, prospective, qa_source
    from .report_scope import source_events, execution_report
    cleanup = account.get('cleanup')
    if not cleanup or row['phase'] != 'cleanup' or row['role'] != 'QA':
        raise Refusal('separately selected same-package cleanup required')
    epoch = prospective.current(runtime, row['task'])
    if not epoch or epoch['policy']['ordinary_effects'] is not False:
        raise Refusal('current no-effect consolidation authority required')
    rows = ordinary.accepted_runs(runtime, row['package'])
    qa = [r for r in rows if r['task'] == 'qa-execution']
    if len(qa) != 1:
        raise Refusal('all admitted ordinary results and one exact accepted same-package QA execution required')
    sequence = qa_branch_sequence(runtime.config)
    if sequence:
        ordinary.sequence_policies(runtime, row['package'])
    run = qa[0]
    original = runtime.job(run['job'])
    held = qa_operation(runtime, original, record, account)
    qa_source.verify(runtime, run['attempt'], json.loads(run['policy']), json.loads(run['receipt']))
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    if scope_excluded(runtime, row['task'], admission):
        raise Refusal('cleanup excluded before metadata')
    task = scoped_task(row['task'], runtime.config['tasks'][row['task']], admission)
    if (task['admitted_scope'] != cleanup['scope'] or task.get('network')
            or task['effect_authority']['owner'] != runtime.enrollment('QA')['owner']
            or set(task['effect_authority']['operations']) - {'read-source', 'read-reports', 'prepare-intents', 'consolidate-reports', 'write-owned-artifacts'}):
        raise Refusal('cleanup scope cannot acquire execution/native/effect authority')
    ordinary.frozen_file(runtime, cleanup['scope']['procedure'], cleanup['scope']['read_roots'], cleanup['procedure_sha256'])
    events = source_events(runtime, row)
    if not events:
        raise Refusal('actual complete execution reports required')
    if sequence:
        branch = [r for r in rows if r['task'] == 'branch-integrator']
        if len(branch) != 1 or len(events) != 1:
            raise Refusal('one accepted Branch result and its whole report required for final cleanup')
        branch = branch[0]
        branch_job = runtime.job(branch['job'])
        if branch_job['effects'] != 'reconciled' or branch_job['hold_reason'] or not ordinary.selected(runtime, branch_job):
            raise Refusal('accepted Branch result unresolved, held or no longer authorized')
        prospective.board(runtime, 'Branch')._software_job_grant(runtime, branch_job)
        _, policy = ordinary.policy_for(runtime, branch_job)
        if policy != json.loads(branch['policy']):
            raise Refusal('accepted Branch policy changed')
        ordinary.accepted_source_current(runtime, branch, policy)
        ordinary.accepted_report(runtime, events[0], branch, row['task'])
        # The Branch return must retain the complete QA envelope too.
        from .report_scope import conserved_inputs
        expected = encode({'collected_reports': conserved_inputs(runtime, branch_job)})
        if not any(encode(finding) == expected for finding in events[0]['body']['findings']):
            raise Refusal('final cleanup cannot omit the whole original QA report')
    else:
        for event in events:
            execution_report(runtime, event, original, row['task'])
    return held
