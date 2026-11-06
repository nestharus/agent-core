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
    if job is not None:
        authorize_scope(store, job, binding)
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


def authorize_scope(store, row, binding):
    """Only trusted permission-index metadata before any native acquisition."""
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
        admission = store.one('SELECT receipt FROM admissions WHERE package=?', (binding['package'],))
        scope = json.loads(admission['receipt']).get('task_scopes', {}).get(binding['task'], {}) if admission else {}
        repository = scope.get('ordinary_effects', {}).get('repository')
        if not repository:
            raise Refusal('native execution needs its actual admitted procedure/resources; no fake Work task')
        paths = [repository, scope.get('procedure')]
        if not all(isinstance(p, str) and p for p in paths):
            raise Refusal('native execution needs actual admitted source/procedure paths')
        source_roots(store, row, paths)
    if kind == 'branch':
        branch_scope(store, row, binding['id'])
    if kind == 'review':
        review_scope(store, row, binding, role)


def review_scope(store, row, binding, role):
    coordinated = role == 'Work' or role == 'Reviews' and row.get('phase') == 'integrator'
    originals = original_review_jobs(store, row, set()) if coordinated else [row]
    relevant = []
    # Validate every original's current interface and source scope, including
    # originals for other components. Selecting a lens never drops evidence or
    # exempts another batch member from its provenance/hold/authority checks.
    for original in originals:
        components = review_material_scope(store, original)
        if binding['component'] in components:
            if not coordinated and components != {binding['component']}:
                raise Refusal('native review point differs from original component/material')
            relevant.append(original)
    if not relevant:
        raise Refusal('native review point differs from original component/material')
    context = store.one('SELECT collector,run FROM review_contexts WHERE component=?', (binding['component'],))
    if not context or context['collector'] != store.controller:
        raise Refusal('native review cannot borrow another original collector')
    # Attached material is checked against each relevant original's authority.
    for linked in store.rows('SELECT branch FROM branch_contexts WHERE address=?', (context['run'],)):
        for original in relevant:
            branch_scope(store, original, linked['branch'])


def review_material_scope(store, original):
    """Resolve logical components only after checking every original operand."""
    from .branches import review_component, job_branch_key
    members = json.loads(original['members']) if original.get('members') else [{'event': original['event']}]
    if not store.processing or not store.processing.review_task(original['task']):
        raise Refusal('native review requires its actual selected original review interface')
    policy = store.processing.current()[1]['service']['reviews'][original['task']]
    synthetic = {**original, 'members': json.dumps(members)}
    # job_branch also selects an owner-admission fallback. Authorize the exact
    # effective operand before review_key can resolve its physical identity.
    branch = job_branch_key(store, synthetic)
    if branch is not None:
        branch_scope(store, original, branch)
    components = set()
    for member in members:
        event = store.event(member['event'])
        body = event.get('body')
        packet = body.get('review', {}) if isinstance(body, dict) else {}
        component = policy['components'].get(packet.get('component'))
        if not component:
            raise Refusal('native review point differs from original component/material')
        source_roots(store, original, component['repository'], repository=True)
        components.add(review_component(branch, packet))
    return components


def original_review_jobs(store, row, visiting):
    """Follow only the original return/member provenance already permissioned."""
    result = []
    members = (json.loads(row['members']) if row.get('members') else
               [{'event':row['event'], 'hash':store.one('SELECT hash FROM events WHERE id=?', (row['event'],))['hash']}])
    for member in members:
        key = member['event']
        if key in visiting:
            raise Refusal('native review original return ancestry is cyclic')
        event = store.event(key)
        job = event.get('source_job')
        if not job and event.get('source_delivery'):
            outbox = store.one('SELECT job FROM outboxes WHERE id=?', (event['source_delivery'].get('id'),))
            job = outbox['job'] if outbox else None
        source = store.job(job) if job else None
        if not source or source.get('package') != row.get('package'):
            raise Refusal('native review needs its actual original component return')
        task = store.config['tasks'].get(source['task'], {})
        if task.get('role') != source['role'] or task.get('phase') != source['phase']:
            raise Refusal('native review original role interface changed')
        if source['role'] == 'Work':
            coordination = store.processing.current()[1].get('work_coordination', {}) if store.processing else {}
            if source['task'] not in coordination.get('tasks', []) or 'Reviews' not in coordination.get('source_roles', []):
                raise Refusal('native review continuation requires current independent Work coordination')
        source_members = json.loads(source['members'])
        attempt = store.attempt(source['active_attempt']) if source.get('active_attempt') else None
        from .contracts import collected_task_result, response_tasks, digest
        if (digest(event) != member.get('hash')
                or event.get('package') != row.get('package')
                or member.get('package', row.get('package')) != row.get('package')
                or store.one('SELECT hold FROM events WHERE id=?', (key,))['hold']
                or not attempt or attempt['collected'] is None or attempt['ended'] is None
                or attempt['exit'] != 0 or attempt['error'] or attempt['capture'] != 'complete'
                or not source_members
                or store.processing and not store.processing.event(event)):
            raise Refusal('native review original return provenance/collection changed')
        answer = collected_task_result(attempt)
        from .review_returns import proof as report_proof
        report = report_proof(store, event, row['task'])
        if report:
            valid = True  # Exact original PARTIAL report receipt, never Source completion.
        elif event.get('source_job'):
            valid = (event.get('source_members') == source_members
                     and event.get('source_attempt') == attempt['id']
                     and event.get('source_role') == source['role'] and event.get('body') == answer
                     and row['task'] in response_tasks(store.config['tasks'][source['task']], answer, store.config))
        else:
            from . import prospective
            epoch = prospective.for_job(store, source)
            proof = json.loads(attempt['detail']).get('software_authority', {})
            if (epoch and proof.get('prospective_epoch') != epoch['id']
                    or not epoch and (proof.get('prospective_epoch') or prospective.requires_authority(store, source))):
                raise Refusal('native review original handoff needs its current bound prospective authority')
            policy = epoch['policy'] if epoch else store.config['tasks'][source['task']]
            delivery = event['source_delivery']
            outbox = store.one('SELECT * FROM outboxes WHERE id=?', (delivery.get('id'),))
            link = store.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (delivery.get('id'),))
            payload = json.loads(outbox['payload']) if outbox else {}
            valid = (link and link['event'] == key and event.get('body') == payload
                     and delivery.get('source_hash') == digest(payload)
                     and payload.get('source_members') == source_members
                     and payload.get('package') == row.get('package')
                     and payload.get('attempt') == attempt['id'] and payload.get('source_result') == answer
                     and payload.get('original_handoff') in answer.get('handoffs', [])
                     and row['task'] in policy.get('software_handoffs', {}).get(row['role'], []))
        if not valid:
            raise Refusal('native review original return provenance/collection changed')
        for original in source_members:
            if (digest(store.event(original['event'])) != original['hash']
                    or store.event(original['event']).get('package') != row.get('package')
                    or store.one('SELECT hold FROM events WHERE id=?', (original['event'],))['hold']
                    or store.processing and not store.processing.event(store.event(original['event']))):
                raise Refusal('native review original member authority/hash/hold changed')
        if source['role'] == 'Work' or source['role'] == 'Reviews' and source['phase'] == 'integrator':
            result.extend(original_review_jobs(store, source, visiting | {key}))
        elif source['role'] == 'Reviews' and source['phase'] == 'proposer':
            result.append(source)
        else:
            raise Refusal('native review needs its actual original component return')
    if not result:
        raise Refusal('native review needs its actual original component return')
    return result


def source_roots(store, row, paths, *, repository=False):
    paths = [paths] if isinstance(paths, str) else paths
    if store.config['tasks'][row['task']]['role'] == 'Work':
        return  # Independently issued coordination above, never borrowed execution.
    task = store.config['tasks'][row['task']]
    if task.get('require_package_scope'):
        admission = store.one('SELECT receipt FROM admissions WHERE package=?', (row.get('package'),))
        scope = json.loads(admission['receipt']).get('task_scopes', {}).get(row['task'], {}) if admission else {}
        roots = scope.get('read_roots', []) + scope.get('write_roots', [])
        repositories = [p for p in scope.get('repository_reads', []) if p in task.get('repository_reads', [])]
    else:
        roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
        repositories = task.get('repository_reads', [])
    def covered(value, roots, repositories):
        return (repository and value in repositories
                or any(Path(value).is_relative_to(Path(p)) for p in roots))
    if any(not covered(value, roots, repositories) for value in paths):
        raise Refusal('native source outside genuine role read authority')
    # Only now may scoped_task validate physical topology of the allowed scope.
    from .contracts import scoped_task
    actual = scoped_task(row['task'], task, store.one('SELECT receipt FROM admissions WHERE package=?', (row.get('package'),)))
    roots = actual['effect_authority']['read_roots'] + actual['effect_authority']['write_roots']
    if any(not covered(value, roots, actual.get('repository_reads', [])) for value in paths):
        raise Refusal('native source outside genuine role read authority')


def branch_scope(store, row, key):
    # Do not call association here: it resolves physical Git identity.
    branch = store.one('SELECT id,scope,repository,ref FROM branch_associations WHERE id=?', (key,))
    if not branch or branch['scope'] != row.get('package'):
        raise Refusal('native branch point exceeds original admitted package')
    source_roots(store, row, branch['repository'], repository=True)
    task = store.config['tasks'][row['task']]
    if task.get('package_narrowing') and task['role'] == 'Branch':
        admission = store.one('SELECT receipt FROM admissions WHERE package=?', (row.get('package'),))
        scope = json.loads(admission['receipt']).get('task_scopes', {}).get(row['task'], {}) if admission else {}
        if scope.get('branch_binding') != branch['id']:
            raise Refusal('Branch proposal needs its exact original admitted association')
    if task['role'] == 'Branch' and task['effects'] not in {'none', 'owned-artifacts'}:
        admission = store.one('SELECT receipt FROM admissions WHERE package=?', (row.get('package'),))
        scope = json.loads(admission['receipt']).get('task_scopes', {}).get(row['task'], {}) if admission else {}
        p = scope.get('ordinary_effects', {})
        if (scope.get('branch_binding') != branch['id'] or p.get('kind') != 'local-ref'
                or p.get('repository') != branch['repository'] or p.get('ref') != branch['ref']):
            raise Refusal('native branch effect needs its original exact association/ref admission')


def authorize(store, row, binding):
    # snapshot performs scope authorization before material acquisition.
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
