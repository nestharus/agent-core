"""Compare actual scoped resources without disposing historical role debt."""
import json
from pathlib import Path

from .contracts import PROFILES, Refusal, digest, parse_json, required_text, scoped_task


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
                or set(record) not in ({'original_hold', 'roots', 'unbounded', 'evidence'},
                                       {'original_hold', 'roots', 'unbounded', 'evidence', 'operation_observation'})
                or type(record['unbounded']) is not bool or not isinstance(record['roots'], list)):
            raise Refusal('legacy resource account needs exact hold, roots, unbounded and evidence')
        if runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))['legacy_hold'] != record['original_hold']:
            raise Refusal('resource account does not describe the actual retained hold')
        required_text(record['evidence'], 'supported original resource scope, not a renamed package')
        if not record['unbounded'] and not record['roots']:
            raise Refusal('unknown legacy scope cannot be declared independent')
        if 'operation_observation' in record:
            validate_observation(runtime, role, record)
        for value in record['roots']:
            root(value, runtime.config.get('artifact_exclusions', []))


# Complete operands bind an accountable Work policy choice, not authentication
# of external QA facts. A message or hash alone never supplies an admission.
OBSERVATION_KIND = 'local-qa-operation-v1'
QA_TASKS = {'qa-execution': ('QA', 'execution'), 'qa-cleanup': ('QA', 'cleanup'),
            'branch-proposer': ('Branch', 'proposer')}
READ_OPERATIONS = {'read-source', 'read-reports', 'prepare-intents', 'consolidate-reports'}


def validate_observation(runtime, role, record):
    observation = record['operation_observation']
    if (role != 'QA' or record['unbounded'] is not True
            or not isinstance(observation, dict)
            or set(observation) != {'kind', 'account', 'package', 'source', 'tasks'}
            or observation['kind'] != OBSERVATION_KIND or not record['original_hold']):
        raise Refusal('operation observation retains the globally unknown QA account')
    account = observation['account']
    owner = runtime.one('SELECT owner FROM enrollments WHERE role=?', ('QA',))
    if (not isinstance(account, dict)
            or set(account) != {'author', 'reference', 'observed_at', 'disposition', 'additional_relevant_roots'}
            or not owner or account['author'] != owner['owner']
            or account['disposition'] != 'no-positive-current-own-conflict'
            or account['additional_relevant_roots'] != []):
        raise Refusal('attributed original operation-relative empty observation required')
    for key in ('reference', 'observed_at'):
        required_text(account[key], 'original QA account '+key, 4000)
    required_text(observation['package'], 'one exact original QA package', 128)
    source = observation['source']
    if not isinstance(source, dict) or set(source) != {'scope', 'submitter'}:
        raise Refusal('exact selected prospective source scope and submitter required')
    for value in source.values():
        required_text(value, 'original admitted source identity', 128)
    if not isinstance(observation['tasks'], dict) or set(observation['tasks']) != set(QA_TASKS):
        raise Refusal('execution, separate cleanup and read-only Branch receiver required')
    exclusions = runtime.config.get('artifact_exclusions', [])
    # Guard declared access paths before scoped_task can touch their metadata.
    for name, bound in observation['tasks'].items():
        if (not isinstance(bound, dict) or set(bound) != {'policy', 'scope'}
                or bound['policy'] != runtime.config['tasks'].get(name)
                or not isinstance(bound['scope'], dict)):
            raise Refusal('complete exact current task policy and admitted scope required')
        scope = bound['scope']
        for key in ('read_roots', 'write_roots'):
            if not isinstance(scope.get(key), list):
                raise Refusal('explicit observation access lists required')
        for value in scope['read_roots'] + scope['write_roots'] + [scope.get('cwd'), scope.get('procedure')]:
            root(value, exclusions)
    execution_scope = observation['tasks']['qa-execution']['scope']
    for name, bound in observation['tasks'].items():
        policy, scope = bound['policy'], bound['scope']
        expected_role, phase = QA_TASKS[name]
        operations = set(policy.get('effect_authority', {}).get('operations', []))
        if (policy.get('role') != expected_role or policy.get('phase') != phase
                or not policy.get('require_package_scope') or policy.get('network', False)
                or scope.get('network', False) or not operations
                or operations - (READ_OPERATIONS | ({'execute-admitted-qa'} if phase == 'execution' else set()))):
            raise Refusal('observation covers only local QA execution and read-only receivers')
        if phase != 'execution' and (scope['write_roots'] or scope.get('ordinary_effects')
                                     or not policy.get('package_narrowing') or policy.get('effects') != 'none'):
            raise Refusal('cleanup/receiver cannot expand access or acquire effects')
        if phase != 'execution':
            unavailable = execution_scope['write_roots'] + [execution_scope['procedure']]
            if any(overlaps(Path(p), Path(q)) for p in scope['read_roots'] for q in unavailable):
                raise Refusal('source-only cleanup/receiver cannot read execution output or procedure')
        scoped_task(name, policy, {'receipt': json.dumps({'task_scopes': {name: scope}})})
    operation = observation['tasks']['qa-execution']['scope'].get('ordinary_effects', {})
    if (not isinstance(operation, dict) or operation.get('kind') != 'local-qa'
            or not all(operation.get(k) for k in ('repository', 'source_ref', 'source_head', 'procedure_sha256',
                                                 'command', 'readback', 'source_capture', 'resources'))
            or operation.get('known_exits') != [0, 1]):
        raise Refusal('complete bound local QA source/procedure/commands/export/resources required')
    return observation


def observed_operation(runtime, row, record, admission, cap, selection):
    observation = validate_observation(runtime, row['role'], record)
    work = runtime.config['roles']['Work']['owner']
    if (cap['issuer'] != work or row['package'] != observation['package']
            or row['task'] not in {'qa-execution', 'qa-cleanup'}
            or row['phase'] != QA_TASKS[row['task']][1] or not admission
            or admission['owner'] != runtime.config['actor']):
        raise Refusal('actual current Work selection and original QA admission required')
    original = runtime.one('SELECT * FROM processing_admissions WHERE package=?', (row['package'],))
    receipt = parse_json(admission['receipt'])
    if not isinstance(receipt, dict) or not isinstance(receipt.get('software_admission'), dict):
        raise Refusal('original structured software admission receipt required')
    provenance = receipt.get('software_admission', {})
    scopes = {n: b['scope'] for n, b in observation['tasks'].items()}
    source_selection = observation['source']
    policy = selection.get('software_admission', {})
    selected = policy.get('scopes', {}).get(source_selection['scope'])
    if (not original or original['receipt'] != admission['receipt'] or original['capability'] != cap['id']
            or provenance.get('capability') != original['capability'] or provenance.get('issuer') != work
            or provenance.get('source') != original['event']
            or original['scope'] != source_selection['scope'] or provenance.get('scope') != original['scope']
            or provenance.get('native_owner_consent') is not False
            or not selected or selected['task_scopes'] != scopes
            or source_selection['submitter'] not in selected['submitters']
            or not row['package'].startswith(selected['package_prefix'])
            or provenance.get('scope_hash') != digest(selected)
            or provenance.get('authority') != policy['authority']
            or receipt.get('resource_evidence') != selected['evidence']
            or receipt.get('task_scopes') != scopes or set(scopes) - set(selection['tasks'])):
        raise Refusal('original software admission/source and every separate scope must match')
    source = runtime.event(original['event'])
    if (digest(source) != provenance.get('source_hash') or source.get('package') != row['package']
            or source.get('author') != source_selection['submitter']
            or not isinstance(source.get('body'), dict) or source['body'].get('topic') != source_selection['scope']
            or source.get('role') != 'QA' or not runtime.processing.event(source)):
        raise Refusal('current authentic original admitted QA source required')
    if row.get('id'):
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (row['id'],))
        if (not frozen or parse_json(frozen['task']) != observation['tasks'][row['task']]['policy']
                or not frozen['admission'] or parse_json(frozen['admission']) != admission):
            raise Refusal('original frozen job policy/admission must stay unchanged')
    # Exact lease declarations are frozen too; expiry is independently current.
    from .ordinary import validate_resources
    operation = scopes['qa-execution']['ordinary_effects']
    validate_resources(runtime, operation)
    return operation


def frozen_roots(runtime, job, exclusions):
    frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (job['id'],))
    if not frozen or not frozen['admission']:
        raise Refusal('unmapped current local owner retains its original resource hold')
    admission = parse_json(frozen['admission'])
    if scope_excluded(runtime, job['task'], admission):
        raise Refusal('original owner scope excluded before metadata')
    prior = scoped_task(job['task'], parse_json(frozen['task']), admission)
    authority = prior['effect_authority']
    return [root(p, exclusions) for p in authority['read_roots'] + authority['write_roots'] + [prior['cwd']]]


def observed_local_holds(runtime, row, operation, exclusions):
    held = []
    for job in runtime.rows("SELECT * FROM jobs WHERE effects NOT IN ('none','reconciled')"):
        if row.get('id') != job['id']:
            held.extend(frozen_roots(runtime, job, exclusions))
    keys = {r['key'] for r in operation['resources']}
    for lease in runtime.rows('SELECT * FROM ordinary_resources'):
        run = runtime.one('SELECT * FROM ordinary_runs WHERE attempt=?', (lease['attempt'],))
        if run and row.get('id') == run['job'] and row.get('active_attempt') == lease['attempt']:
            continue  # This original's own lease, never a foreign lease adoption.
        if not run or lease['resource'] in keys:
            raise Refusal('conflicting or unmapped current local lease remains held')
        job = runtime.one('SELECT * FROM jobs WHERE id=?', (run['job'],))
        policy = parse_json(run['policy'])
        if (not job or policy.get('kind') != 'local-qa'
                or lease['resource'] not in {r['key'] for r in policy.get('resources', [])}):
            raise Refusal('unmapped current local lease remains held')
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (job['id'],))
        receipt = parse_json(parse_json(frozen['admission'])['receipt']) if frozen and frozen['admission'] else {}
        if receipt.get('task_scopes', {}).get(job['task'], {}).get('ordinary_effects') != policy:
            raise Refusal('lease differs from the original frozen operation')
        held.extend(frozen_roots(runtime, job, exclusions))
    return held


def scope_excluded(runtime, name, admission):
    scope = json.loads(admission['receipt']).get('task_scopes', {}).get(name, {}) if admission else {}
    values = scope.get('read_roots', []) + scope.get('write_roots', []) + [scope.get('cwd', '')]
    return any(Path(value) == Path(p) or Path(value).is_relative_to(Path(p)) or Path(p).is_relative_to(Path(value))
               for value in values for p in runtime.config.get('artifact_exclusions', []))


def blocked(runtime, row, task=None):
    enrollment = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (row['role'],))
    if not enrollment or not enrollment['legacy_hold']:
        return False
    task = task or runtime.config['tasks'][row['task']]
    if runtime.processing and row['phase'] == 'proposer' and task['effects'] == 'none':
        return False
    if not runtime.processing:
        return True
    cap, selection = runtime.processing.current()
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
    observation = record.get('operation_observation')
    if record['unbounded'] and observation is None:
        return True
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    operation = None
    if observation is not None:
        try:
            if task != runtime.config['tasks'][row['task']]:
                return True
            operation = observed_operation(runtime, row, record, admission, cap, selection)
        except (Refusal, KeyError, TypeError, ValueError, OSError):
            return True
    # Independence needs a genuine narrowed admission, not a package label.
    if scope_excluded(runtime, row['task'], admission):
        return True
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
    held = [root(p, exclusions) for p in record['roots']]
    if operation is not None:
        try:
            held.extend(observed_local_holds(runtime, row, operation, exclusions))
            return not selected or any(overlaps(a, b) for a in selected for b in held)
        except (Refusal, KeyError, TypeError, ValueError, OSError):
            return True
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
            prior = scoped_task(job['task'], prior, prior_admission)
            authority = prior['effect_authority']
        except (Refusal, KeyError):
            return True
        held.extend(root(p, exclusions) for p in authority['read_roots'] + authority['write_roots'] + [prior['cwd']])
    return not selected or any(overlaps(a, b) for a in selected for b in held)
