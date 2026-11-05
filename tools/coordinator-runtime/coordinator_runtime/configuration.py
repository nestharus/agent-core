"""Work-selected prospective configuration on the original journal.

Append-only local selection, not historical recovery, enrollment or deployment.
Board grants and all original duties remain bound to their original bytes.
"""
from . import observations

from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path

from .contracts import Refusal, digest, encode, regular_path, required_text, validate_config, parse_json, PROFILES, scoped_startup

SCHEMA = """
CREATE TABLE IF NOT EXISTS configuration_transitions(
 position INTEGER PRIMARY KEY AUTOINCREMENT,previous TEXT NOT NULL,current TEXT NOT NULL UNIQUE,
 original TEXT NOT NULL,configuration TEXT NOT NULL,selection TEXT NOT NULL,
 issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS configuration_transitions_no_update
 BEFORE UPDATE ON configuration_transitions BEGIN SELECT RAISE(ABORT,'immutable configuration transition'); END;
CREATE TRIGGER IF NOT EXISTS configuration_transitions_no_delete
 BEFORE DELETE ON configuration_transitions BEGIN SELECT RAISE(ABORT,'immutable configuration transition'); END;
"""


def latest(runtime):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='configuration_transitions'"):
        return None  # Older read-only protocol fixtures; Store always installs the schema.
    return runtime.one('SELECT * FROM configuration_transitions ORDER BY position DESC LIMIT 1')


@observations.observe('configuration-current')
def assert_current(runtime):
    row = latest(runtime)
    if row and row['current'] != digest(runtime.config):
        raise Refusal('configuration is historical; reopen with the selected current configuration, never replay old authority')


def original_digest(runtime):
    row = latest(runtime)
    return row['original'] if row else digest(runtime.config)


def selected(runtime):
    assert_current(runtime)
    row = latest(runtime)
    return json.loads(row['selection']) if row else None


def original_binding(runtime, role, grant):
    """Only ProcessingBoard bridges current authority to a still-revoked grant."""
    selection = selected(runtime)
    if not selection:
        return digest(runtime.config)
    if selection['basis']['processing']['roles'][role]['original']['binding'] != grant:
        raise Refusal('current selection cannot replace the immutable original grant binding')
    return original_digest(runtime)


def _path(value, exclusions):
    path = Path(required_text(value, 'current selection path', 4000))
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('absolute canonical current selection path required')
    if any(path == Path(p) or path.is_relative_to(Path(p)) for p in [*exclusions, *(str(Path.home()/p) for p in PROFILES)]):
        raise Refusal('current selector is excluded before metadata')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal('current selection cannot follow aliases')
    return path


def branch_release_sources(root):
    """Exact public final-consumer dependencies outside the runtime module glob."""
    return [root/'tools/branch_release.py', root/'tools/operational_contracts.py',
            root/'tools/coordinator-runtime/final-release-risk.md']


def release(runtime, candidate):
    """Actual public source bytes; no account probing, pool allocation or install."""
    directory = Path(__file__).resolve().parents[1]
    root = directory.parent.parent
    exclusions = candidate.get('artifact_exclusions', [])
    expected = {'board_library': str(root/'tools/message-board'),
                'operator_cli': str(directory/'coordinator')}
    if any(candidate.get(k) != v for k, v in expected.items()):
        raise Refusal('current operator and Board SDK must select this same release checkout')
    if candidate.get('canonical_publication', {}).get('method') != 'retention-same-inode-v1':
        raise Refusal('current retention must preserve the same-inode snapshot lock contract')
    receive = candidate.get('control_receive', {})
    if receive.get('instructions') != str(directory/'templates/coordinator-receive.md'):
        raise Refusal('current receive instructions must select this release')
    operator = regular_path(str(_path(candidate.get('operator_config'), exclusions)))
    if parse_json(operator.read_text()) != candidate:
        raise Refusal('operator config file must contain this exact selected current configuration')
    paths = [*sorted((directory/'coordinator_runtime').glob('*.py')), directory/'coordinator',
             *(root/'tools/message-board'/p for p in ('catalog.py', 'board_store.py', 'active_listener.py', 'queue_transport.py', 'managed_owner.py')),
             root/'tools/direct-child/execution_pool.py', root/'tools/direct-child/dispatch.py',
             root/'tools/direct-codex-child/launch.sh', directory/'templates/coordinator-receive.md',
             Path(candidate['canonical_publication']['library'])/'retention.py', operator,
             *branch_release_sources(root)]
    for task in candidate['tasks'].values():
        paths.extend(Path(p) for p in task['templates']
                     if not (scoped_startup(task) and Path(p).name in {'AGENTS.md', 'WORK_LOG.md'}))
    from .custody import refuse_log
    files = {}
    for p in sorted(set(paths)):
        refuse_log(p)
        files[str(p)] = hashlib.sha256(regular_path(str(_path(str(p), exclusions))).read_bytes()).hexdigest()
    # Membership is user-owned hot control, including an empty paused pool.
    # Pin all other bytes and the exact public location, without touching state.
    control = regular_path(str(_path(candidate['execution_pool_routes'], exclusions)))
    from .execution_pool import _module
    try:
        pool = _module.Pool(control)
        raw, _, _ = pool.read()
        pool_control = pool.control_binding(raw)
    except _module.PoolError as exc:
        raise Refusal('current public pool unavailable: '+str(exc)) from exc
    return {'root': str(root), 'files': files, 'pool_control': pool_control,
            'qualification': 'source bytes only; no installed provider/native or deployment claim'}


def candidate(runtime, operator_config, scope_tasks, retention_library=None, bounded_work_log=False, scope_options=None):
    """Produce a draft for Work inspection; does not select or write a config."""
    value = copy.deepcopy(runtime.config)
    directory = Path(__file__).resolve().parents[1]
    root = directory.parent.parent
    old_directory = Path(value['operator_cli']).parent
    value.update(board_library=str(root/'tools/message-board'), operator_cli=str(directory/'coordinator'),
                 operator_config=operator_config, profiles=sorted(PROFILES))
    value['release_scope_tasks'] = list(scope_tasks)
    # Retention is a separately supplied dependency; this repository does not
    # contain retention.py. Preserve its explicit selector unless Work selects
    # another actual compatible provider, and pin that public dependency.
    if retention_library is not None:
        value['canonical_publication']['library'] = retention_library
    value['control_receive']['instructions'] = str(directory/'templates/coordinator-receive.md')
    for kind in ('classifier', 'diagnosis'):
        value[kind]['cwd'] = str(root)
    for name, task in value['tasks'].items():
        task['templates'] = [str(directory/Path(p).relative_to(old_directory))
                             if Path(p).is_relative_to(old_directory) else p for p in task['templates']]
        if name in scope_tasks:
            authority = task['effect_authority']
            if 'read-source' not in authority['operations']:
                raise Refusal('source scope requires an already source-authorized task')
            for name in ('coordinator-runtime', 'message-board', 'direct-child', 'direct-codex-child'):
                path = str(root/'tools'/name)
                if path not in authority['read_roots']:
                    authority['read_roots'].append(path)
            if task['role'] == 'Branch':
                # Existing Branch source authority, exact files only. No tools/
                # ancestor grant, additional task, write, network or capacity.
                for source in branch_release_sources(root):
                    if str(source) not in authority['read_roots']:
                        authority['read_roots'].append(str(source))
            if task.get('require_package_scope'):
                if task['role'] not in {'Branch', 'QA'}:
                    raise Refusal('only scoped Branch/QA tasks may acquire the release repository scope')
                if str(root) not in task['scope_roots']:
                    task['scope_roots'].append(str(root))
    if bounded_work_log:
        from .bounded_log import KIND
        matches = [t for t in value['tasks'].values() if t['role']=='Work' and t['phase']=='integrator' and t.get('routine_completion')]
        if len(matches) != 1:
            raise Refusal('one existing seven-duty Work integrator required')
        matches[0]['templates'] = [p for p in matches[0]['templates'] if Path(p).name not in {'AGENTS.md','WORK_LOG.md'}]
        policy = matches[0]['routine_completion']
        logs = [p for p in policy['targets'] if Path(p).name == 'WORK_LOG.md']
        if len(logs) != 1 or len(policy['targets']) != 7:
            raise Refusal('existing seven real targets and exact log target required')
        matches[0]['routine_completion'] = {'kind': KIND, 'targets': policy['targets'],
            'bounded_log': {'target': logs[0], 'max_lines': 12, 'max_bytes': 8192, 'max_entry_bytes': 16384}}
    if set(scope_tasks) - set(value['tasks']):
        raise Refusal('unknown task in current configuration draft')
    if scope_options is not None:
        apply_scope_options(runtime.config, value, scope_options)
    for task in value['tasks'].values():
        if task.get('require_package_scope'):
            task['scope_exclusions'] = list(value.get('artifact_exclusions', []))
    return value


def apply_scope_options(original, value, options):
    """Explicit future narrowing and associated resource ceilings, never old policy edits."""
    if not isinstance(options, dict) or set(options) - {'read_roots', 'neutral_startup', 'exclusions', 'linked_repositories', 'capacity', 'cwd'}:
        raise Refusal('unsupported prospective scope option')
    select_capacity(original, value, options.get('capacity'))
    exclusions = options.get('exclusions', [])
    if not isinstance(exclusions, list):
        raise Refusal('explicit additional exclusions required')
    # Lexical exclusion union only. Never stat an exclusion or seek its aliases.
    for p in exclusions:
        path = Path(required_text(p, 'known exclusion', 4000))
        if not path.is_absolute() or '..' in path.parts:
            raise Refusal('absolute known exclusion required')
        if p not in value.setdefault('artifact_exclusions', []):
            value['artifact_exclusions'].append(p)
    def safe(p):
        from .resource_scopes import root
        return root(p, value.get('artifact_exclusions', []))
    reads = options.get('read_roots', {})
    linked = options.get('linked_repositories', {})
    neutral = options.get('neutral_startup', [])
    if not isinstance(reads, dict) or not isinstance(linked, dict) or not isinstance(neutral, list):
        raise Refusal('exact task read scopes, linked repositories and startup selections required')
    if (set(reads) | set(linked) | set(neutral)) - set(value['tasks']):
        raise Refusal('unknown prospective scoped task')
    for name, roots in reads.items():
        if not isinstance(roots, list) or not roots:
            raise Refusal('nonempty explicit future read roots required')
        allowed = value['tasks'][name]['effect_authority']['read_roots']
        retention = str(Path(value['canonical_publication']['library'])/'retention.py')
        for p in roots:
            path = safe(p)
            if not (p == retention or any(path.is_relative_to(Path(r)) for r in allowed)):
                raise Refusal('read roots may only narrow existing/release authority or select exact retention.py')
            # No broad ancestor containing a known exclusion is a safe read scope.
            if any(Path(e).is_relative_to(path) for e in value.get('artifact_exclusions', [])):
                raise Refusal('read root contains a known exclusion; select exact safe inputs')
        value['tasks'][name]['effect_authority']['read_roots'] = list(dict.fromkeys(roots))
    for name in neutral:
        task = value['tasks'][name]
        task['startup'] = 'explicit-packet'
        task['templates'] = [p for p in task['templates'] if Path(p).name not in {'AGENTS.md','WORK_LOG.md'}]
    for name, records in linked.items():
        task = value['tasks'][name]
        if task['role'] not in {'Branch','QA'} or not task.get('require_package_scope') or not isinstance(records, list) or not records:
            raise Refusal('associated common Git ceiling needs an existing scoped Branch/QA task')
        for record in records:
            if not isinstance(record, dict) or set(record) != {'repository','common_git'}:
                raise Refusal('exact repository/common Git pair required')
            repo, common = safe(record['repository']), safe(record['common_git'])
            if (not any(repo.is_relative_to(Path(p)) for p in task['scope_roots'])
                    or common.name != '.git' or common == repo or repo.is_relative_to(common)):
                raise Refusal('narrow associated common Git path and already admitted repository required')
            # No general home/AI grant. This separate ceiling is usable only with
            # its paired cwd and freshly verified actual topology in scoped_task.
        task['linked_repositories'] = copy.deepcopy(records)
    directories = options.get('cwd', {})
    if not isinstance(directories, dict) or set(directories) - set(value['tasks']):
        raise Refusal('exact future task working-directory map required')
    for name, directory in directories.items():
        path = safe(directory)
        allowed = original['tasks'][name]['effect_authority']['read_roots'] + [original['tasks'][name]['cwd']]
        if (not any(path.is_relative_to(Path(p)) for p in allowed)
                or any(Path(e).is_relative_to(path) for e in value.get('artifact_exclusions', []))):
            raise Refusal('future cwd must narrow existing nonexcluded authority; no new resource grant')
        value['tasks'][name]['cwd'] = str(path)
    value['prospective_scope_selection'] = copy.deepcopy(options)


def select_capacity(original, value, policy):
    """Explicit bounded prospective ceilings; original rows/grants stay charged.

    This declaration is not physical entitlement, allocation or headroom proof.
    Work selects it through the existing exact configuration basis/decision.
    """
    if policy is None:
        return
    bounds = {'max_bytes': 1024 * 1024 * 1024, 'max_files': 50000,
              'max_events': 65536, 'max_jobs': 65536, 'max_attempts': 65536,
              'max_outboxes': 65536, 'max_alerts': 65536, 'max_alert_debt': 65536,
              'max_board_deliveries': 65536}
    if (not isinstance(policy, dict) or set(policy) != {'authority', 'evidence', 'limits'}
            or not isinstance(policy['limits'], dict) or not policy['limits'] or set(policy['limits']) - set(bounds)):
        raise Refusal('exact bounded Work prospective capacity authority/evidence/limits required')
    for key in ('authority', 'evidence'):
        required_text(policy[key], 'genuine prospective capacity ' + key, 16000)
    for key, limit in policy['limits'].items():
        if type(limit) is not int or not 1 <= limit <= bounds[key]:
            raise Refusal('prospective capacity exceeds supported finite ceiling: ' + key)
        value['limits'][key] = limit


def validate_changes(runtime, value, tasks):
    validate_config(value)
    if (not isinstance(tasks, list) or not tasks or len(set(tasks)) != len(tasks)
            or set(tasks) - set(value['tasks'])):
        raise Refusal('exact prospective task allowlist required')
    # Reconstruct the permitted change. All other identities, grants, task
    # effects/bindings/concurrency, recipients, policies and fences freeze.
    # Only the explicit bounded capacity option may amend residency ceilings.
    root = str(Path(__file__).resolve().parents[3])
    additions = value.get('release_scope_tasks', [])
    if not isinstance(additions, list) or len(set(additions)) != len(additions) or set(additions) - set(value['tasks']):
        raise Refusal('exact release source-task list required')
    bounded = any(t.get('routine_completion') != runtime.config['tasks'][name].get('routine_completion') for name,t in value['tasks'].items())
    options = value.get('prospective_scope_selection')
    expected = candidate(runtime, value['operator_config'], additions, value.get('canonical_publication', {}).get('library'), bounded, options)
    if bounded and any(name not in tasks for name,t in value['tasks'].items() if t.get('routine_completion') != runtime.config['tasks'][name].get('routine_completion')):
        raise Refusal('changed bounded completion policy needs selected prospective Work task')
    if value != expected:
        raise Refusal('unsupported current configuration delta; only coherent selectors and exact release scopes may change')
    if any(name not in tasks for name in additions):
        raise Refusal('every added scope needs an explicitly selected prospective task')
    if options and (set(options.get('read_roots', {})) | set(options.get('neutral_startup', [])) | set(options.get('linked_repositories', {})) | set(options.get('cwd', {}))) - set(tasks):
        raise Refusal('every changed future scope/startup needs an explicitly selected task')
    # Scoped_task still narrows each actual package; this grants no writes or
    # Root acceptance. Broad ancestors and peer checkout roots cannot enter.
    if any(root not in value['tasks'][name]['scope_roots'] for name in additions
           if value['tasks'][name].get('require_package_scope')):
        raise Refusal('exact release scope required')


def journal(runtime):
    """Protocol mutation witnesses; no retained body/key/size acquisition.

    Applicable guarded body validation stays at source use. These tokens bind
    writes since bootstrap, not historical truth, integrity or whole reads.
    """
    from . import windows
    witness = windows.revision(runtime)
    result = {}
    for table in runtime.rows("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = table['name']
        token = (digest(witness['sequences']) if name == 'sqlite_sequence' else
                 'revision infrastructure; no source rows' if name == 'allocation_revision' else witness['tokens'][name])
        result[name] = {'revision': token, 'schema': digest(table['sql'])}
        if table['name'] == 'artifact_blobs':
            result[name]['body_observation'] = 'no body/key/size acquisition; body integrity unobserved'
    return result


def basis(runtime, boards, value, tasks):
    from . import processing
    assert_current(runtime)
    validate_changes(runtime, value, tasks)
    identity = runtime.path.stat()
    return {'configuration': digest(runtime.config), 'candidate': digest(value),
            'runtime': {'path': str(runtime.path), 'dev': identity.st_dev, 'ino': identity.st_ino,
                        'actor': runtime.config['actor']},
            'processing': processing.basis(runtime, boards, future_only=True), 'journal': journal(runtime),
            'release': release(runtime, value), 'tasks': tasks}


@contextmanager
def stopped(runtime):
    fd = os.open(runtime.home/'service.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('original cooperative service owns its lock; collect/control it, never displace it') from exc
        yield
    finally:
        os.close(fd)


def apply(runtime, boards, value, selection):
    if not isinstance(selection, dict) or set(selection) != {'basis', 'authority'}:
        raise Refusal('exact current transition basis and genuine Work authority required')
    required_text(selection['authority'], 'Work current configuration decision and rationale', 4000)
    issuer = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    tasks = selection['basis']['tasks']
    with stopped(runtime), runtime.tx():
        current = basis(runtime, boards, value, tasks)
        if current != selection['basis']:
            raise Refusal('current transition source/basis changed; no automatic retry')
        if current['candidate'] == current['configuration']:
            raise Refusal('current transition needs an actual prospective configuration change')
        if (current['processing']['current'] or runtime.one('SELECT id FROM prospective_authorities WHERE revoked IS NULL')
                or any(r['original']['continuation'] for r in current['processing']['roles'].values())):
            raise Refusal('explicitly revoke existing processing/prospective/retained capabilities; no implicit supersession')
        if any(r['original']['binding']['issued_by'] != issuer for r in current['processing']['roles'].values()):
            raise Refusal('same genuine original Work issuer required')
        record = {**selection, 'previous_configuration': runtime.config,
                  'event_boundary': current['processing']['event_boundary'],
                  'jobs': [r['id'] for r in runtime.rows('SELECT id FROM jobs')],
                  'outboxes': [r['id'] for r in runtime.rows('SELECT id FROM outboxes')],
                  'collectors': {r['id']: r['controller'] for r in runtime.rows('SELECT id,controller FROM attempts')},
                  'alert_boundary': runtime.one('SELECT COALESCE(MAX(rowid),0) AS n FROM alerts')['n']}
        encoded = encode(record)
        runtime.budget(None, len(encoded.encode()) + len(encode(value).encode()) + 4096)
        runtime.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
                           (current['configuration'], current['candidate'], original_digest(runtime), encode(value), encoded, issuer, runtime.clock()))
    return {'configuration': current['candidate'], 'previous': current['configuration'],
            'runtime': current['runtime'], 'normal_grants': 'unchanged and still revoked',
            'next': 'reopen this same journal with selected current config; take fresh processing-basis and delegate prospective authority',
            'historical_recovery': False}


def validate_processing(runtime, selection):
    transition = selected(runtime)
    if not transition:
        return
    if (selection['retained_events'] or selection['recover_controls'] or not selection['future_intake']
            or set(selection['tasks']) - set(transition['basis']['tasks'])
            or any(r['kind'] != 'admit-package' for r in selection.get('owner_operations', []))):
        raise Refusal('current configuration authority is prospective only; historical recovery/holds remain original')


def event_allowed(runtime, event):
    transition = selected(runtime)
    if not transition:
        return True
    row = runtime.one('SELECT COALESCE(p.position,e.rowid) AS position FROM events e LEFT JOIN processing_source_positions p ON p.event=e.id WHERE e.id=?', (event['id'],))
    return not row or row['position'] > transition['event_boundary']


def task_for_job(runtime, job):
    """Retained resource debt uses its historical policy, never new selectors."""
    for row in runtime.rows('SELECT selection FROM configuration_transitions ORDER BY position'):
        transition = json.loads(row['selection'])
        if job['id'] in transition['jobs']:
            return transition['previous_configuration']['tasks'][job['task']]
    return runtime.config['tasks'][job['task']]


def owned_service_conflict(runtime):
    """A new version never adopts or disposes an old collector.

    The cooperative lock still excludes a live owner. Other-version originals
    remain owned with their attempts/resources/contexts; scoped gates decide
    whether any particular new work can proceed. Same-version recovery is strict.
    """
    transition = selected(runtime)
    known = {row['previous'] for row in runtime.rows('SELECT previous FROM configuration_transitions')} if transition else set()
    for run in runtime.rows("SELECT * FROM processing_runs WHERE state='owned'"):
        cap = runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (run['capability'],))
        if (not transition or not cap or json.loads(cap['selection'])['basis']['configuration'] not in known
                or json.loads(cap['selection'])['basis']['configuration'] == digest(runtime.config)):
            return True
    return False


def require_current_job(runtime, job):
    transition = selected(runtime)
    if not transition:
        return
    attempt = runtime.attempt(job['active_attempt']) if job['active_attempt'] else None
    proof = json.loads(attempt['detail']).get('processing_capability') if attempt else None
    if not runtime.processing or proof != runtime.processing.key or any(
            not event_allowed(runtime, runtime.event(m['event'])) for m in json.loads(job['members'])):
        raise Refusal('historical job/effect cannot inherit current configuration authority')
    runtime.processing.authorize(attempt)


def outbox_allowed(runtime, outbox):
    transition = selected(runtime)
    if not transition:
        return True
    if outbox['id'] in transition['outboxes']:
        return False
    if outbox.get('event') and not event_allowed(runtime, runtime.event(outbox['event'])):
        return False
    if outbox.get('job'):
        try:
            require_current_job(runtime, runtime.job(outbox['job']))
        except Refusal:
            return False
    if outbox.get('alert'):
        row = runtime.one('SELECT rowid AS n FROM alerts WHERE id=?', (outbox['alert'],))
        if not row or row['n'] <= transition['alert_boundary']:
            return False
    return True


@observations.observe('source-release')
def assert_release(runtime):
    transition = selected(runtime)
    if transition and release(runtime, runtime.config) != transition['basis']['release']:
        raise Refusal('selected public release/dependencies changed; duties held pending an explicit current transition')


def authorize_collection(runtime, attempt):
    """Original collectors may record actual returns, never acquire new effects."""
    row = latest(runtime)
    if not row or row['current'] == digest(runtime.config):
        return
    for version in runtime.rows('SELECT previous,selection FROM configuration_transitions ORDER BY position'):
        record = json.loads(version['selection'])
        if (version['previous'] == digest(runtime.config)
                and record['collectors'].get(attempt) == runtime.controller
                and runtime.attempt(attempt)['controller'] == runtime.controller):
            return
    raise Refusal('historical collection belongs only to the actual original attempt/controller; no takeover')
