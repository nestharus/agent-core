"""Exact prospective local-ref authority; historical effects remain owned.

The actual retained role custodian supplies attributed original activity evidence.
This is neither legacy reconciliation nor historical recovery. External evidence
is an accountable assertion, not runtime discovery or inferred inactivity.
"""
import json
import subprocess
from pathlib import Path

from .contracts import Refusal, digest, encode, required_text, scoped_task
from .resource_scopes import root, scope_excluded

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_resource_policies(job TEXT PRIMARY KEY,task TEXT NOT NULL,admission TEXT);
CREATE TRIGGER IF NOT EXISTS job_resource_policies_no_update BEFORE UPDATE ON job_resource_policies
 BEGIN SELECT RAISE(ABORT,'immutable original job resources'); END;
CREATE TRIGGER IF NOT EXISTS job_resource_policies_no_delete BEFORE DELETE ON job_resource_policies
 BEGIN SELECT RAISE(ABORT,'immutable original job resources'); END;
CREATE TABLE IF NOT EXISTS ref_scope_accounts(
 id TEXT PRIMARY KEY,actor TEXT NOT NULL,basis TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS ref_scope_accounts_no_update BEFORE UPDATE ON ref_scope_accounts
 BEGIN SELECT RAISE(ABORT,'immutable prospective ref account'); END;
CREATE TRIGGER IF NOT EXISTS ref_scope_accounts_no_delete BEFORE DELETE ON ref_scope_accounts
 BEGIN SELECT RAISE(ABORT,'immutable prospective ref account'); END;
"""


def material(store, task_name, package):
    try:
        return _material(store, task_name, package)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refusal('exact current repository/ref evidence unavailable; operation held') from exc


def _material(store, task_name, package):
    if not store.processing:
        raise Refusal('current prospective processing authority required')
    cap, selection = store.processing.current()
    if task_name not in selection['tasks']:
        raise Refusal('ref operation outside current selected tasks')
    task = store.config['tasks'][task_name]
    admission = store.one('SELECT * FROM admissions WHERE package=?', (package,))
    if scope_excluded(store, task_name, admission):
        raise Refusal('ref scope excluded before metadata')
    task = scoped_task(task_name, task, admission)
    scope = task.get('admitted_scope', {})
    p = scope.get('ordinary_effects', {})
    if (task['role'] != 'Branch' or task['phase'] != 'integrator' or not task.get('require_package_scope')
            or p.get('kind') != 'local-ref' or task.get('network')
            or 'organize-authorized-refs' not in task['effect_authority']['operations']):
        raise Refusal('exact admitted local-ref adapter required; no generic network/ref waiver')
    # Use the adapter's complete policy/procedure/tool/lease validation too.
    from .ordinary import policy_for
    policy_for(store, {'task': task_name, 'package': package, 'role': 'Branch', 'phase': 'integrator'})
    from .branches import association, repository_identity
    branch = association(store, scope.get('branch_binding'))
    if (branch['scope'] != package or branch['repository'] != p['repository'] or branch['ref'] != p['ref']
            or task['cwd'] != p['repository']):
        raise Refusal('exact accepted branch scope/repository/ref/incarnation required')
    from .reviews import git
    repository = root(p['repository'], store.config.get('artifact_exclusions', []))
    common = root(git(str(repository), 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip(), store.config.get('artifact_exclusions', []))
    # Write authority is required for the actual common repository, not a cwd alias.
    if not any(common.is_relative_to(Path(r)) for r in task['effect_authority']['write_roots']):
        raise Refusal('actual common repository write authority absent')
    device, inode = repository_identity(repository)
    if git(str(repository), 'remote', 'get-url', 'origin').decode().strip() != branch['origin']:
        raise Refusal('actual origin differs from accepted branch')
    source = git(str(repository), 'rev-parse', '--verify', p['source_ref']+'^{commit}').decode().strip()
    before = git(str(repository), 'rev-parse', '--verify', p['ref']+'^{commit}').decode().strip()
    if source != p['source_head'] or before != p['before']:
        raise Refusal('fresh actual ref before-state differs; new operation qualification required')
    enrollment = store.one('SELECT * FROM enrollments WHERE role=?', ('Branch',))
    if not enrollment or not enrollment['legacy_hold']:
        raise Refusal('exact retained legacy custody required')
    # Preserve both historical policy and actual activity. New scopes never
    # rewrite a prior job's resource authority. No inference from ACK/free lock.
    from .configuration import task_for_job
    old = []
    for job in store.rows("SELECT * FROM jobs WHERE role='Branch' AND effects NOT IN ('none','reconciled') ORDER BY id"):
        old.append({'id': job['id'], 'controller': job['controller'], 'effects': job['effects'],
                    'policy': task_for_job(store, job),
                    'original_resource_policy': store.one('SELECT * FROM job_resource_policies WHERE job=?', (job['id'],)),
                    'attempts': store.rows('SELECT id,controller,begin,ended,exit,collected,capture,error FROM attempts WHERE job=? ORDER BY id', (job['id'],))})
    turns = store.rows("SELECT t.* FROM branch_turns t JOIN branch_associations b ON b.id=t.branch WHERE b.device=? AND b.inode=? AND t.writer IS NOT NULL AND t.state IN ('active','unknown') ORDER BY t.id", (device, inode))
    if turns:
        raise Refusal('actual common-repository writer activity/unknown remains fenced')
    current_job = store.one("SELECT active_attempt FROM jobs WHERE package=? AND task=? AND state!='closed'", (package, task_name))
    own = current_job['active_attempt'] if current_job else None
    prefix_key = 'git-ref:' + str(device) + ':' + str(inode) + ':'
    for lease in store.rows('SELECT * FROM ordinary_resources'):
        if lease['attempt'] == own:
            continue
        key = lease['resource']
        held_run = store.one('SELECT policy,receipt FROM ordinary_runs WHERE attempt=?',(lease['attempt'],))
        held_receipt = json.loads(held_run['receipt']) if held_run and held_run['receipt'] else {}
        held_policy = json.loads(held_run['policy']) if held_run else {}
        identity = held_receipt.get('before',{}).get('common_repository')
        # A caller's resource key, even a plausible path/ref name, is not an
        # actual map. Only original executed source evidence qualifies it.
        if (not identity or held_policy.get('kind') != 'local-ref'
                or not all(type(identity.get(k)) is int for k in ('dev','ino'))):
            raise Refusal('unmapped original resource lease remains unknown')
        held_prefix = 'git-ref:'+str(identity['dev'])+':'+str(identity['ino'])+':'
        if key not in {held_prefix+held_policy['source_ref'],held_prefix+held_policy['ref']}:
            raise Refusal('unmapped original resource lease remains unknown')
        if key in {prefix_key+p['ref'], prefix_key+p['source_ref']}:
            raise Refusal('exact common-repository local ref overlaps original lease')
    return {'capability': cap['id'], 'configuration': digest(store.config), 'task': task_name,
            'package': package, 'admission': digest(admission), 'operation': p,
            'branch': {k: branch[k] for k in ('id','repository','device','inode','origin','ref','incarnation','scope','root','accepted')},
            'common_repository': {'path': str(common), 'dev': device, 'ino': inode},
            'local_refs': [{'ref': p['source_ref'], 'mode': 'read', 'head': source},
                           {'ref': p['ref'], 'mode': 'write', 'head': before}],
            'remote_refs': [], 'network': False,
            'custodian': enrollment['owner'], 'original_hold': enrollment['legacy_hold'], 'unresolved_jobs': old}


def account(store, actor, receipt):
    if not isinstance(receipt, dict) or set(receipt) != {'basis','authority','originals','activity_scope','remaining_holds','past_effects'}:
        raise Refusal('prospective account requires actual activity originals and conserved past obligations')
    basis = receipt['basis']
    actual = material(store, basis['task'], basis['package'])
    if actual != basis or actor != actual['custodian']:
        raise Refusal('actual retained custodian and fresh exact prospective basis required')
    if not historical_resources_clear(store, actual):
        raise Refusal('original historical resource scope/overlap remains unknown or conflicting; activity closure is separate')
    required_text(receipt['authority'], 'actual custodian current-operation authority and rationale')
    if (not isinstance(receipt['remaining_holds'], list) or actual['original_hold'] not in receipt['remaining_holds']
            or not isinstance(receipt['past_effects'], list) or not receipt['past_effects']):
        raise Refusal('past effects/source custody remain explicit; no empty clearance')
    activity = receipt['activity_scope']
    if (not isinstance(activity, dict) or set(activity) != {'original_hold','operation','no_active_writers','evidence'}
            or activity['original_hold'] != actual['original_hold'] or activity['operation'] != digest({'operation':actual['operation'],'repository':actual['common_repository'],'refs':actual['local_refs']})
            or activity['no_active_writers'] is not True):
        raise Refusal('actual custodian must qualify current exact resources/activity, not just old ENDs')
    required_text(activity['evidence'], 'current exact operation activity/control evidence')
    originals = receipt['originals']
    if not isinstance(originals, list) or not originals:
        raise Refusal('genuine original control/activity/END evidence required')
    for original in originals:
        if (not isinstance(original, dict) or set(original) != {'original','collector','activity','actual_END','evidence'}
                or original['activity'] != 'closed'
                or type(original['actual_END']) is not int):
            raise Refusal('unknown actual activity remains held; no inferred END/collector transfer')
        required_text(original['collector'], 'actual original collector, never reassigned')
        required_text(original['original'], 'actual original receipt reference')
        required_text(original['evidence'], 'actual collected original/control/activity evidence')
    # Current candidate job does not need a retrospective END. All OTHER prior
    # unresolved jobs require genuine already collected originals; old unknown
    # effects remain charged. External originals are attributed above.
    for job in actual['unresolved_jobs']:
        if not job['attempts']:
            raise Refusal('prior job activity unavailable; hold affected operation')
        for attempt in job['attempts']:
            if attempt['ended'] is None or attempt['collected'] is None or type(attempt['exit']) is not int:
                raise Refusal('actual unfinished prior original activity remains held')
    key = digest({'actor': actor, 'receipt': receipt})
    with store.tx():
        store.budget(None, len(encode(receipt).encode())+2048)
        store.db.execute('INSERT OR IGNORE INTO ref_scope_accounts VALUES(?,?,?,?,?)',
                         (key, actor, encode(actual), encode(receipt), store.clock()))
    return {'id': key, 'basis': actual, 'meaning': 'prospective exact local-ref operation only; all historical holds/effects unchanged'}


def eligible(store, row, task):
    # Match an immutable custodian account to exact current operation material.
    try:
        actual = material(store, row['task'], row['package'])
    except (Refusal, OSError, KeyError):
        return False
    if not historical_resources_clear(store, actual, row.get('id')):
        return False
    # Current job/attempt progression is not a change to historical activity.
    records = store.rows('SELECT * FROM ref_scope_accounts WHERE actor=?', (actual['custodian'],))
    for record in records:
        saved = json.loads(record['basis'])
        current = {**actual, 'unresolved_jobs': [j for j in actual['unresolved_jobs'] if j['id'] != row.get('id')]}
        previous = {**saved, 'unresolved_jobs': [j for j in saved['unresolved_jobs'] if j['id'] != row.get('id')]}
        if current == previous:
            return True
    return False


def historical_resources_clear(store, actual, current_job=None):
    """Only original frozen/executed maps can establish ref independence.

    Collected END and no-active-writer evidence cannot replace missing scope.
    Conservative refusal retains the original hold and all past-effect custody.
    """
    for job in actual['unresolved_jobs']:
        if job['id'] == current_job:
            continue
        frozen = job['original_resource_policy']
        if not frozen or not frozen['admission']:
            return False
        try:
            # The exact task key is retained on the original job, not the new admission.
            old = store.job(job['id'])
            if scope_excluded(store, old['task'], json.loads(frozen['admission'])):
                return False
            task = scoped_task(old['task'], json.loads(frozen['task']), json.loads(frozen['admission']))
            policy = task.get('admitted_scope', {}).get('ordinary_effects', {})
            if policy.get('kind') != 'local-ref' or task.get('network'):
                return False
            runs = store.rows('SELECT policy,receipt FROM ordinary_runs WHERE attempt IN (SELECT id FROM attempts WHERE job=?)', (job['id'],))
            if not runs:
                return False
            for run in runs:
                if json.loads(run['policy']) != policy or not run['receipt']:
                    return False
                source = json.loads(run['receipt']).get('before', {})
                identity = source.get('common_repository', {})
                if not all(type(identity.get(k)) is int for k in ('dev','ino')):
                    return False
                same = all(identity[k] == actual['common_repository'][k] for k in ('dev','ino'))
                if same and {policy['source_ref'], policy['ref']} & {r['ref'] for r in actual['local_refs']}:
                    return False
        except (Refusal, KeyError, TypeError, ValueError):
            return False
    return True
