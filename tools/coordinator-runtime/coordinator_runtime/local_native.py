"""Read existing service identities; never create a parallel native catalog.

These observations confer no execution, acceptance, collector or file rights.
Native mutations still use branches/reviews/ordinary and their original gates.
"""
import json
from pathlib import Path

from .contracts import Refusal, required_text


def validate_binding(binding):
    shapes = {'branch': {'native', 'id'}, 'review': {'native', 'component'},
              'execution': {'native', 'package', 'task'}}
    if not isinstance(binding, dict) or set(binding) != shapes.get(binding.get('native'), set()):
        raise Refusal('exact existing branch, review context or execution admission identity required')
    for value in binding.values():
        required_text(value, 'native identity', 4000)


def source_role(config, binding):
    if binding['native'] == 'execution':
        task = config['tasks'].get(binding['task'])
        if not task or task['role'] not in {'Branch', 'QA'}:
            raise Refusal('native execution must name an existing Branch/QA task')
        return task['role']
    return {'branch': 'Branch', 'review': 'Reviews'}[binding['native']]


def validate_task(config, name, binding):
    role = config['tasks'][name]['role']
    permitted = {source_role(config, binding), 'Work'}
    if binding['native'] == 'branch':
        permitted.add('Reviews')
    if role not in permitted:
        raise Refusal('native binding cannot confer another role execution/read authority')


def ref_resource(branch):
    return 'git-ref:'+str(branch['device'])+':'+str(branch['inode'])+':'+branch['ref']


def branch_snapshot(store, key, own=None):
    from .branches import association
    from .reviews import git
    branch = association(store, key)
    if not branch['accepted']:
        raise Refusal('native branch requires actual responsible Root acceptance')
    turns = store.rows('SELECT * FROM branch_turns WHERE branch=? AND id!=? ORDER BY id', (key, own or ''))
    contexts = store.rows('SELECT * FROM branch_contexts WHERE branch=? ORDER BY kind,component,address', (key,))
    value = {'association': branch, 'contexts': contexts, 'turns': turns,
             'head': git(branch['repository'], 'rev-parse', '--verify', branch['ref']+'^{commit}').decode().strip()}
    resources = {ref_resource(branch)}
    resources.update('native-session:'+r['address'] for r in contexts)
    return value, resources


def snapshot(store, binding, job=None):
    """Original records and append history retain intervening service changes."""
    validate_binding(binding)
    own = job.get('active_attempt') if job else None
    kind = binding['native']
    if kind == 'branch':
        return branch_snapshot(store, binding['id'], own)
    if kind == 'review':
        context = store.one('SELECT * FROM review_contexts WHERE component=?', (binding['component'],))
        if not context or context['state'] != 'live' or context['collector'] != store.controller:
            raise Refusal('original native reviewer/context/collector unavailable; no replacement session')
        if store.processing and context['capability'] != store.processing.key:
            raise Refusal('original native review capability changed')
        resources = {'native-session:'+v for v in (context['handle'], context['run']) if v}
        branches = []
        for row in store.rows('SELECT branch FROM branch_contexts WHERE address=?', (context['run'],)):
            value, keys = branch_snapshot(store, row['branch'], own)
            branches.append(value); resources.update(keys)
        calls = store.rows('SELECT * FROM review_calls WHERE component=? AND attempt!=? ORDER BY attempt',
                           (binding['component'], own or ''))
        histories = store.rows('SELECT * FROM review_history_commits WHERE component=? AND attempt!=? ORDER BY attempt',
                               (binding['component'], own or ''))
        return {'context': context, 'calls': calls, 'history': histories, 'branches': branches}, resources
    admission = store.one('SELECT * FROM admissions WHERE package=?', (binding['package'],))
    scope = json.loads(admission['receipt']).get('task_scopes', {}).get(binding['task']) if admission else None
    if not scope or not scope.get('ordinary_effects'):
        raise Refusal('native execution needs its actual admitted procedure/resources; no fake Work task')
    from .ordinary import policy_for
    from .branches import repository_identity
    task = store.config['tasks'][binding['task']]
    if not task.get('require_package_scope'):
        raise Refusal('native execution requires its original scoped task interface')
    _, p = policy_for(store, {'task':binding['task'], 'package':binding['package'],
                              'role':task['role'], 'phase':task['phase']})
    # These paths are from the actual admission, never a packet-authored ref.
    from .resource_scopes import root
    repository = root(p['repository'], store.config.get('artifact_exclusions', []))
    device, inode = repository_identity(repository)
    resources = {r['key'] for r in p['resources']}
    resources.add('git-ref:'+str(device)+':'+str(inode)+':'+p['source_ref'])
    if p['kind'] == 'local-ref':
        resources.add('git-ref:'+str(device)+':'+str(inode)+':'+p['ref'])
    runs = store.rows('SELECT r.* FROM ordinary_runs r JOIN jobs j ON j.id=r.job '
                      'WHERE j.package=? AND j.task=? AND r.attempt!=? ORDER BY r.attempt',
                      (binding['package'], binding['task'], own or ''))
    acceptance = [store.one('SELECT * FROM ordinary_acceptance WHERE attempt=?', (r['attempt'],)) for r in runs]
    return {'admission': admission, 'scope': scope, 'runs': runs, 'acceptance': acceptance}, resources


def authorize(store, row, binding):
    validate_binding(binding)
    validate_task(store.config, row['task'], binding)
    role = store.config['tasks'][row['task']]['role']
    if role == 'Work':
        from .processing_admission import permits
        coordination = store.processing.current()[1].get('work_coordination', {}) if store.processing else {}
        members = json.loads(row['members']) if row.get('members') else [{'event':row.get('event'), 'package':row.get('package')}]
        if (row['task'] not in coordination.get('tasks', [])
                or source_role(store.config, binding) not in coordination.get('source_roles', [])
                or not members or any(not m['event'] for m in members)
                or any(not permits(store, {'task':row['task'], 'event':m['event'], 'package':m['package']}) for m in members)):
            raise Refusal('native return observation requires independently issued current Work coordination')
    kind = binding['native']
    if kind == 'execution':
        if binding['package'] != row.get('package'):
            raise Refusal('native execution cannot borrow another package admission')
    if kind == 'branch':
        from .branches import association
        branch = association(store, binding['id'])
        if branch['scope'] != row.get('package'):
            raise Refusal('native branch point exceeds original admitted package')
        if role != 'Work':
            from .contracts import scoped_task
            task = store.config['tasks'][row['task']]
            if task.get('require_package_scope'):
                task = scoped_task(row['task'], task, store.one('SELECT * FROM admissions WHERE package=?', (row['package'],)))
            roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
            if not any(Path(branch['repository']).is_relative_to(Path(p)) for p in roots):
                raise Refusal('native branch source outside genuine role read authority')
            if role == 'Branch' and task['effects'] not in {'none', 'owned-artifacts'}:
                scope = task.get('admitted_scope', {})
                p = scope.get('ordinary_effects', {})
                if (scope.get('branch_binding') != branch['id'] or p.get('kind') != 'local-ref'
                        or p.get('repository') != branch['repository'] or p.get('ref') != branch['ref']):
                    raise Refusal('native branch effect needs its original exact association/ref admission')
    if kind == 'review' and role != 'Work':
        if not store.processing or not store.processing.review_task(row['task']):
            raise Refusal('native review requires its actual selected original review interface')
        context = store.one('SELECT * FROM review_contexts WHERE component=?', (binding['component'],))
        if not context or context['collector'] != store.controller:
            raise Refusal('native review cannot borrow another original collector')
        # Bind the actual review packet/component, including branch incarnation.
        from .branches import review_key
        members = json.loads(row['members']) if row.get('members') else [{'event': row['event']}]
        synthetic = {**row, 'members': json.dumps(members)}
        for member in members:
            body = store.event(member['event']).get('body')
            packet = body.get('review', {}) if isinstance(body, dict) else {}
            if review_key(store, synthetic, packet) != binding['component']:
                raise Refusal('native review point differs from original component/material')
    snapshot(store, binding, row)


def busy(store, resources, own=None):
    """Original external turns/unknown effects remain exclusive too."""
    for row in store.rows("SELECT t.id,t.address,b.device,b.inode,b.ref FROM branch_turns t "
                          "JOIN branch_associations b ON b.id=t.branch WHERE t.state IN ('active','unknown')"):
        if row['id'] != own and resources & {ref_resource(row), 'native-session:'+row['address']}:
            return True
    for row in store.rows("SELECT c.attempt,r.handle,r.run FROM review_calls c JOIN review_contexts r "
                          "ON r.component=c.component WHERE c.state!='collected'"):
        if row['attempt'] != own and resources & {'native-session:'+v for v in (row['handle'],row['run']) if v}:
            return True
    return False
