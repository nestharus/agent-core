"""Compare actual scoped resources without disposing historical role debt."""
import json
import math
import re
import os
import subprocess
import copy
from pathlib import Path

from .contracts import PROFILES, Refusal, digest, encode, canonical_uuid, required_text, scoped_task, qa_branch_sequence


SCHEMA = """
CREATE TABLE IF NOT EXISTS qa_observation_amendments(
 capability TEXT NOT NULL,package TEXT NOT NULL,request TEXT NOT NULL,
 issuer TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(capability,package));
CREATE TRIGGER IF NOT EXISTS qa_observation_amendments_no_update BEFORE UPDATE ON qa_observation_amendments
 BEGIN SELECT RAISE(ABORT,'immutable Work observation amendment'); END;
CREATE TRIGGER IF NOT EXISTS qa_observation_amendments_no_delete BEFORE DELETE ON qa_observation_amendments
 BEGIN SELECT RAISE(ABORT,'immutable Work observation amendment'); END;
"""


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


def validate(runtime, policy, selection=None):
    for role, record in policy.items():
        if (role not in runtime.config['roles'] or not isinstance(record, dict)
                or set(record) - {'qa_operation', 'qa_operations', 'reviews_report'} != {'original_hold', 'roots', 'unbounded', 'evidence'}
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
        if 'reviews_report' in record:
            from .report_scope import validate as validate_report
            validate_report(runtime, role, record, selection)



def scope_excluded(runtime, name, admission):
    scope = json.loads(admission['receipt']).get('task_scopes', {}).get(name, {}) if admission else {}
    values = scope.get('read_roots', []) + scope.get('write_roots', []) + [scope.get('cwd', '')]
    return any(Path(value) == Path(p) or Path(value).is_relative_to(Path(p)) or Path(p).is_relative_to(Path(value))
               for value in values for p in runtime.config.get('artifact_exclusions', []))


def qa_accounts(record, runtime=None):
    if 'qa_operations' in record:
        values = record['qa_operations']
        # Five executing + one accepted cleanup + one waiting execution need
        # seven exact package accounts, without increasing either phase slot.
        if ('qa_operation' in record or not isinstance(values, list) or not 1 <= len(values) <= 7):
            raise Refusal('one to seven independent selected QA operation policies required')
    else:
        values = [record['qa_operation']] if 'qa_operation' in record else []
    return [selected_qa_account(runtime, record, a) for a in values] if runtime else values


def _qa_grants(runtime):
    # Supported enrollment metadata only; never source bodies or shared stores.
    return {r: runtime.one('SELECT owner,profile,grant_id,cutover,intake,legacy_hold FROM enrollments WHERE role=?', (r,))
            for r in ('Work', 'QA')}


def _qa_amendment(runtime, package):
    if not runtime.processing or not runtime.one("SELECT name FROM sqlite_master WHERE name='qa_observation_amendments'"):
        return None
    return runtime.one('SELECT * FROM qa_observation_amendments WHERE capability=? AND package=?',
                       (runtime.processing.key, package))


def _corrected_account(account, request):
    if (not isinstance(request, dict)
            or set(request) != {'basis', 'authority', 'evidence', 'statement', 'statement_sha256', 'relevant_roots'}
            or not isinstance(request['statement'], dict) or not request['statement']
            or request['statement_sha256'] != digest(request['statement'])):
        raise Refusal('exact whole new Work observation, statement hash and relevant roots required')
    required_text(request['authority'], 'current Work correction truth and rationale', 4000)
    if not isinstance(request['evidence'], list) or not 1 <= len(request['evidence']) <= 32:
        raise Refusal('finite explicit current owner observation evidence required')
    for item in request['evidence']:
        required_text(item, 'current Work observation evidence', 4000)
    value = copy.deepcopy(account)
    value['statement'] = request['statement']
    value['policy'].update(statement_sha256=request['statement_sha256'], relevant_roots=request['relevant_roots'])
    return value


def selected_qa_account(runtime, record, account):
    """Resolve one append-only Work attribution; never rewrite the old account.

    An amendment does not authenticate native QA authorship or prove a physical
    census. Original global unknown custody and every independent guard remain.
    """
    package = account.get('binding', {}).get('package') if isinstance(account, dict) else None
    row = _qa_amendment(runtime, package)
    if not row:
        return account
    cap, selection = runtime.processing.current()
    request = json.loads(row['request'])
    basis = request['basis']
    originals = [a for a in qa_accounts(record) if a['binding']['package'] == package]
    if (len(originals) != 1 or selection.get('service', {}).get('legacy_resources', {}).get('QA') != record
            or cap['issuer'] != runtime.config['roles']['Work']['owner'] or row['issuer'] != cap['issuer']
            or basis['capability'] != cap['id'] or basis['package'] != package
            or basis['issuer'] != cap['issuer'] or basis['configuration'] != digest(runtime.config)
            or basis['selection_sha256'] != digest(selection) or basis['original_record_sha256'] != digest(record)
            or basis['original_account_sha256'] != digest(originals[0]) or basis['grants'] != _qa_grants(runtime)):
        raise Refusal('observation amendment differs from its unchanged current cap/account/custody binding')
    if not runtime.processing.boards or 'Work' not in runtime.processing.boards:
        raise Refusal('current original Work authority checker required')
    runtime.processing.boards['Work'].verify_authority(runtime)
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (package,))
    if digest(admission) != basis['admission_sha256']:
        raise Refusal('observation amendment cannot rebind its original admission')
    corrected = _corrected_account(originals[0], request)
    if account != originals[0] and account != corrected:
        raise Refusal('unselected amended observation')
    _qa_observation(runtime, 'QA', record, corrected)
    return corrected


def _qa_owner(runtime):
    # No supplied actor argument. The real process identity is mandatory even
    # for an API caller; SDK authority is independently checked below.
    actor = canonical_uuid(os.environ.get('CODEX_SESSION_ID'))
    owner = runtime.config['roles']['Work']['owner']
    if actor != owner or runtime.config.get('software_delegation', {}).get('grantor') != owner:
        raise Refusal('actual authenticated current Work alone corrects its observation')
    boards = runtime.processing.boards if runtime.processing else None
    if not boards or not all(r in boards for r in ('Work', 'QA')):
        raise Refusal('original Work and QA authority checkers required')
    if boards['Work'].store.acting_session(owner) != actor:
        raise Refusal('actual Work identity differs')
    for role in ('Work', 'QA'):
        boards[role].verify_authority(runtime)
    return actor


def _qa_observation_basis(runtime, controller, event):
    from . import configuration, prospective, windows, local_integration
    from .report_repair import stopped_original
    actor = _qa_owner(runtime)
    cap, selection = runtime.processing.current()
    if cap['issuer'] != actor or 'service' not in selection:
        raise Refusal('same current genuine continuing Work capability required')
    stopped_original(runtime, cap['id'], controller)
    if (runtime.one("SELECT 1 FROM processing_runs WHERE capability=? AND state='owned' LIMIT 1", (cap['id'],))
            or runtime.one('SELECT 1 FROM attempts WHERE controller=? AND (collected IS NULL OR ended IS NULL OR exit IS NULL) LIMIT 1', (controller,))):
        raise Refusal('every original owned attempt and SAME service parent END must be collected')
    queue = runtime.one('SELECT * FROM queue WHERE event=?', (event,))
    state = runtime.one('SELECT hash,hold,state FROM events WHERE id=?', (event,))
    if (not queue or not state or state['hold'] or queue['state'] != 'queued' or queue['job'] is not None
            or queue['role'] != 'QA' or queue['phase'] != 'execution' or queue['task'] != 'qa-execution'):
        raise Refusal('one exact current unheld queued unstarted QA execution required')
    package = queue['package']
    record = selection.get('service', {}).get('legacy_resources', {}).get('QA', {})
    accounts = [a for a in qa_accounts(record) if a['binding']['package'] == package]
    if len(accounts) != 1 or _qa_amendment(runtime, package):
        raise Refusal('one original selected package observation without another amendment required')
    original = accounts[0]
    if (runtime.one('SELECT 1 FROM jobs WHERE package=? LIMIT 1', (package,))
            or runtime.one('SELECT 1 FROM qa_package_owners WHERE package=?', (package,))):
        raise Refusal('reserved or previously started package cannot rebind an observation')
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (package,))
    if not admission or runtime.one('SELECT 1 FROM ordinary_runs WHERE admission=? LIMIT 1', (digest(admission['receipt']),)):
        raise Refusal('package ordinary run/effect intent cannot rebind an observation')
    source = runtime.event(event)
    routed = runtime.routing_event(event)
    if (state['hash'] != digest(source) or routed.get('package') != package
            or routed['role'] != queue['role'] or not runtime.processing.task(queue)):
        raise Refusal('current unchanged queued source/hash/mapping/admission required')
    local_integration.input_authority(runtime, source, queue['task'], package)
    # This validates the ORIGINAL source/admission/tools/expiry but does not
    # require its positive held roots to be disjoint: that is the mistaken
    # Work attribution being corrected, not a guard to disable.
    qa_operation(runtime, queue, record, original)
    scope = original['policy']['scope']
    operation = scope['ordinary_effects']
    for resource in operation['resources']:
        if runtime.one('SELECT 1 FROM ordinary_resources WHERE resource=?', (resource['key'],)):
            raise Refusal('original operation resource lease stays held')
    branch = None
    if scope.get('branch_binding'):
        from .local_native import branch_scope
        from .branches import association
        branch_scope(runtime, queue, scope['branch_binding'])
        branch = association(runtime, scope['branch_binding'])
        if (not branch['accepted'] or branch['root'] != operation['acceptor']
                or branch['repository'] != operation['repository'] or branch['scope'] != package):
            raise Refusal('unchanged current exact Root-accepted branch association required')
    return {'capability': cap['id'], 'issuer': actor, 'configuration': digest(runtime.config),
            'selection_sha256': digest(selection), 'starts': cap['starts'], 'controller': controller,
            'package': package, 'event': event, 'source_sha256': state['hash'], 'queue': queue,
            'mapping': runtime.input_resolution(event), 'admission_sha256': digest(admission),
            'original_record_sha256': digest(record), 'original_account_sha256': digest(original),
            'original_hold': record['original_hold'], 'custodian': original['policy']['custodian'],
            'binding': original['binding'], 'grants': _qa_grants(runtime),
            'prospective': prospective.current(runtime, queue['task']), 'branch': branch,
            'original_release': runtime.one('SELECT state FROM processing_runs WHERE controller=? AND capability=?', (controller, cap['id'])),
            'revision': windows.revision(runtime)}


def qa_observation_basis(runtime, controller, event):
    """Fresh bounded correction operands; no observation truth is inferred."""
    from . import configuration
    with configuration.stopped(runtime), runtime.tx():
        return _qa_observation_basis(runtime, controller, event)


def amend_qa_observation(runtime, request):
    """Append Work's new testimony, only before any package job/effect exists."""
    from . import configuration
    from .selected_source import custody_budget
    _qa_owner(runtime)
    if not isinstance(request, dict) or not isinstance(request.get('basis'), dict):
        raise Refusal('exact current observation correction basis required')
    basis = request['basis']
    with configuration.stopped(runtime), runtime.tx():
        cap, selection = runtime.processing.current()
        if basis.get('capability') != cap['id']:
            raise Refusal('amendment cannot select another capability')
        previous = _qa_amendment(runtime, basis.get('package'))
        record = selection.get('service', {}).get('legacy_resources', {}).get('QA', {})
        if previous:
            if json.loads(previous['request']) != request:
                raise Refusal('different observation amendment already retained; no replacement')
            original = next(a for a in qa_accounts(record) if a['binding']['package'] == basis['package'])
            selected_qa_account(runtime, record, original)  # Read-only; no new charge or write.
            return _qa_amendment_receipt(request)
        if _qa_observation_basis(runtime, basis['controller'], basis['event']) != basis:
            raise Refusal('correction basis changed; obtain a fresh bounded owner observation')
        original = next(a for a in qa_accounts(record) if a['binding']['package'] == basis['package'])
        corrected = _corrected_account(original, request)
        _qa_observation(runtime, 'QA', record, corrected)  # Lexical exclusions before metadata.
        if corrected['statement'] == original['statement']:
            raise Refusal('a new explicit owner observation is required, not an old binding restamp')
        encoded = encode(request)
        if len(encoded.encode()) > runtime.config['limits']['max_result_bytes']:
            raise Refusal('whole observation correction exceeds finite metadata envelope')
        custody_budget(runtime, len(encoded.encode()) + 2048)
        runtime.db.execute('INSERT INTO qa_observation_amendments VALUES(?,?,?,?,?)',
                           (cap['id'], basis['package'], encoded, cap['issuer'], runtime.clock()))
        qa_operation(runtime, basis['queue'], record)  # Same transaction exact anchor recheck.
    return _qa_amendment_receipt(request)


def _qa_amendment_receipt(request):
    return {'capability': request['basis']['capability'], 'package': request['basis']['package'],
            'amendment_sha256': digest(request), 'statement_sha256': request['statement_sha256'],
            'native_qa_authorship': False, 'admission_or_effect_authority_changed': False,
            'meaning': 'new explicit Work attribution; original account, unknown hold, budgets and expiry retained'}


def qa_observation(runtime, role, record, account=None):
    """Validate Work's attributed evidence and exact proposed policy, not authorship.

    This structural check also runs before issuance. Only qa_operation, through
    the current trusted Work capability, can apply it. Digests bind bytes; they
    cannot prove native authorship or the truth/completeness of external facts.
    """
    account = record['qa_operation'] if account is None else account
    account = selected_qa_account(runtime, record, account)
    return _qa_observation(runtime, role, record, account)


def _qa_observation(runtime, role, record, account):
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
    if account not in accounts and not any(
            a['binding'] == account.get('binding') and selected_qa_account(runtime, record, a) == account
            for a in accounts):
        raise Refusal('unselected QA operation')
    account = selected_qa_account(runtime, record, account)
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
    selected = [root(p, exclusions) for p in task['effect_authority']['read_roots'] + task['effect_authority']['write_roots'] + [task['cwd']]]
    held = [root(p, exclusions) for p in record['roots'] + operation_held]
    # Actual unresolved local jobs retain their original roots across roles,
    # including reservations with no attempt/ordinary lease. This is local
    # responsibility, not a census or clearance of external legacy inventory.
    for job in runtime.rows("SELECT * FROM jobs WHERE effects NOT IN ('none','reconciled')"):
        if row.get('id') == job['id']:
            continue  # Reconcile this operation against OTHER unresolved owners.
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (job['id'],))
        try:
            if frozen:
                prior = json.loads(frozen['task'])
                prior_admission = json.loads(frozen['admission']) if frozen['admission'] else None
            else:
                from .configuration import task_for_job
                prior = task_for_job(runtime, job)
                if prior.get('require_package_scope'):
                    return True  # Never launder missing original scope through current admission.
                prior_admission = None
            if scope_excluded(runtime, job['task'], prior_admission):
                return True
            prior = scoped_task(job['task'], prior, prior_admission)
            authority = prior['effect_authority']
            if prior.get('network') or 'organize-authorized-refs' in authority.get('operations', []):
                return True  # Path separation cannot map unresolved external/shared-ref effects.
            held.extend(root(p, exclusions) for p in authority['read_roots'] + authority['write_roots'] + [prior['cwd']])
        except (Refusal, OSError, KeyError, TypeError, ValueError):
            return True
    return not selected or any(overlaps(a, b) for a in selected for b in held)


def qa_cleanup(runtime, row, record, account):
    """Consolidation consumes this accepted execution, never a model DONE."""
    from . import ordinary, prospective, qa_source
    from .report_scope import source_events, execution_report
    account = selected_qa_account(runtime, record, account)
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
        if {'collected_reports': conserved_inputs(runtime, branch_job)} not in events[0]['body']['findings']:
            raise Refusal('final cleanup cannot omit the whole original QA report')
    else:
        for event in events:
            execution_report(runtime, event, original, row['task'])
    return held
