"""Work-scoped prospective software admission in the original journal.

The issuer freezes exact reusable scopes. A future addressed source may select
one by topic; its text supplies no paths, effects, acceptance or native consent.
Existing admissions, jobs, holds and old sources are never replaced or released.
"""
import json
from pathlib import Path

from .contracts import Refusal, digest, encode, required_text, scoped_task, collected_capture


def validate(runtime, selection):
    policy = selection.get('software_admission')
    if policy is None:
        return
    if (not isinstance(policy, dict) or set(policy) != {'authority', 'max_packages', 'scopes'}
            or type(policy['max_packages']) is not int or not 1 <= policy['max_packages'] <= 4096
            or not isinstance(policy['scopes'], dict) or not 1 <= len(policy['scopes']) <= 32
            or selection['future_intake'] is not True):
        raise Refusal('bounded prospective software admission authority/scopes/capacity required')
    required_text(policy['authority'], 'actual Work prospective software admission authority', 4000)
    for name, scope in policy['scopes'].items():
        required_text(name, 'exact prospective source topic', 128)
        if (not isinstance(scope, dict) or set(scope) != {'submitters', 'package_prefix', 'task_scopes', 'evidence'}
                or not isinstance(scope['submitters'], list) or not 1 <= len(scope['submitters']) <= 32
                or not isinstance(scope['task_scopes'], dict) or not scope['task_scopes']):
            raise Refusal('scope needs exact submitters, package prefix, task scopes and authority evidence')
        required_text(scope['package_prefix'], 'bounded prospective package namespace', 128)
        required_text(scope['evidence'], 'genuine scoped admission and resource authority evidence', 16000)
        for submitter in scope['submitters']:
            required_text(submitter, 'authorized actual source submitter', 128)
        for task_name, task_scope in scope['task_scopes'].items():
            task = runtime.config['tasks'].get(task_name)
            if (task_name not in selection['tasks'] or not task or task['role'] not in {'Branch', 'QA'}
                    or not task.get('require_package_scope') or task.get('execution') == 'owner'):
                raise Refusal('software admission only narrows selected scoped Branch/QA tasks')
            if (not isinstance(task_scope, dict) or not isinstance(task_scope.get('read_roots'), list)
                    or not isinstance(task_scope.get('write_roots'), list)):
                raise Refusal('explicit reusable task read/write roots required')
            for value in task_scope['read_roots'] + task_scope['write_roots'] + [task_scope.get('cwd')]:
                required_text(value, 'scoped source path', 4000)
                path = Path(value)
                if any(path == Path(p) or path.is_relative_to(Path(p)) or Path(p).is_relative_to(path)
                       for p in runtime.config.get('artifact_exclusions', [])):
                    raise Refusal('software scope crosses an excluded input before metadata')
            scoped_task(task_name, task, {'receipt': encode({'task_scopes': {task_name: task_scope}})})


def admit(runtime, event_id):
    """Apply the current issuer's exact scope, not a message-authored receipt."""
    with runtime.tx():
        cap, selection = runtime.processing.current()
        policy = selection.get('software_admission')
        event = runtime.event(event_id)
        boards = runtime.processing.boards or {}
        if event['role'] not in boards:
            raise Refusal('prospective admission needs the actual original role/grant checker')
        boards[event['role']].verify_authority(runtime)
        row = runtime.one('SELECT COALESCE(p.position,e.rowid) AS position,e.hold,e.hash FROM events e '
                          'LEFT JOIN processing_source_positions p ON p.event=e.id WHERE e.id=?', (event_id,))
        boundary = selection['basis'].get('event_boundary')
        role = selection['basis']['roles'].get(event['role'])
        body = event.get('body')
        scope_name = body.get('topic') if isinstance(body, dict) else None
        scope = policy['scopes'].get(scope_name) if policy and isinstance(scope_name, str) else None
        if (not scope or type(boundary) is not int or row['position'] <= boundary or row['hold'] or row['hash'] != digest(event)
                or not role or event['role'] not in {'Branch', 'QA'} or event.get('kind') != 'board'
                or event.get('post', 0) <= role['future_after'] or event_id in selection['retained_events']
                or event.get('author') not in scope['submitters'] or not runtime.processing.event(event)):
            raise Refusal('admission needs an unheld genuinely future scoped source from an authorized submitter')
        package = required_text(event.get('package'), 'actual original prospective package', 128)
        if not package.startswith(scope['package_prefix']):
            raise Refusal('prospective package outside the selected namespace')
        if not set(event['allowed_tasks']) & set(scope['task_scopes']):
            raise Refusal('source has no route within this exact admitted task scope')
        receipt = {'task_scopes': scope['task_scopes'], 'resource_evidence': scope['evidence'],
                   'software_admission': {'capability': cap['id'], 'issuer': cap['issuer'],
                       'authority': policy['authority'], 'source': event_id, 'source_hash': digest(event),
                       'scope': scope_name, 'scope_hash': digest(scope), 'native_owner_consent': False}}
        encoded = encode(receipt)
        previous = runtime.one('SELECT * FROM processing_admissions WHERE package=?', (package,))
        existing = runtime.one('SELECT * FROM admissions WHERE package=?', (package,))
        if previous:
            if (previous['event'] != event_id or previous['receipt'] != encoded or not existing
                    or existing['owner'] != runtime.config['actor'] or existing['receipt'] != encoded):
                raise Refusal('existing software admission/source changed; no replacement or replay')
            return {'package': package, 'receipt': receipt, 'already_recorded': True}
        if existing or runtime.one('SELECT id FROM jobs WHERE package=? LIMIT 1', (package,)):
            raise Refusal('existing admission or frozen package work stays with its original authority')
        count = runtime.one('SELECT COUNT(*) AS n FROM processing_admissions WHERE capability=?', (cap['id'],))['n']
        if count >= policy['max_packages']:
            raise Refusal('selected software admission capacity exhausted; source remains owned')
        # Recheck the selected paths at application; no mutable message operand
        # is used. Scoped task construction and launch revalidate again.
        validate(runtime, selection)
        runtime.budget(None, len(encoded.encode()) * 2 + 2048)
        runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)', (package, runtime.config['actor'], encoded))
        runtime.db.execute('INSERT INTO processing_admissions VALUES(?,?,?,?,?,?)',
                           (package, cap['id'], event_id, scope_name, encoded, runtime.clock()))
        # Freeze the runtime-applied whole admission after the random capability
        # exists. Selection binds topic/scope; neither immutable input is edited.
        applied = runtime.one('SELECT * FROM admissions WHERE package=?', (package,))
        runtime.db.execute('INSERT INTO processing_admission_resolutions VALUES(?,?,?,?,?,?,?)',
            (package, cap['id'], event_id, scope_name, digest(scope), digest(applied), digest(event)))
        return {'package': package, 'receipt': receipt, 'acceptance_inferred': False,
                'native_owner_consent': False, 'existing_holds': 'unchanged'}


def validate_coordination(runtime, selection):
    value = selection.get('work_coordination')
    if value is None:
        return
    if (not isinstance(value, dict) or set(value) != {'authority', 'tasks', 'source_roles'}
            or not isinstance(value['tasks'], list) or not value['tasks']
            or not isinstance(value['source_roles'], list) or not value['source_roles']
            or set(value['source_roles']) - {'Branch', 'QA', 'Reviews'}):
        raise Refusal('independent Work coordination authority, exact routes and upstream roles required')
    required_text(value['authority'], 'current independent Work coordination authority', 4000)
    for name in value['tasks']:
        task = runtime.config['tasks'].get(name)
        if (name not in selection['tasks'] or not task or task['role'] != 'Work'
                or task.get('require_package_scope') or task.get('execution') == 'owner'):
            raise Refusal('coordination selects existing independently authorized Work tasks, not execution admission')


def permits(runtime, queue):
    """Conserve package/source ancestry while checking each real upstream member.

    Current Work coordination authority can consume a genuine role return. It
    never adds a Work task to the Branch/QA execution admission or grants effects.
    Actual processing and software launch grants remain independently required.
    """
    if runtime.routing_event(queue['event']).get('package') != queue['package']:
        return False
    record = runtime.one('SELECT * FROM processing_admissions WHERE package=?', (queue['package'],))
    if not record:
        return True  # Original owner admissions retain their existing path.
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (queue['package'],))
    receipt = json.loads(record['receipt'])
    if (not admission or admission['owner'] != runtime.config['actor']
            or admission['receipt'] != record['receipt']):
        return False
    task = runtime.config['tasks'][queue['task']]
    receiver = task.get('package_narrowing') and task['role'] == 'Branch' and task['phase'] == 'proposer'
    if receiver:
        scope = receipt['task_scopes'].get(queue['task'], {})
        key = scope.get('branch_binding')
        if not isinstance(key, str) or not key:
            return False
        # Original package/role read authority is checked before physical Git
        # identity. Association acceptance remains a separate genuine operand.
        from .local_native import branch_scope
        from .branches import association
        branch_scope(runtime, queue, key)
        branch = association(runtime, key)
        if not branch['accepted']:
            return False
    coordination = None
    if queue['task'] not in receipt['task_scopes']:
        if not runtime.processing:
            return False
        selection = runtime.processing.current()[1]
        coordination = selection.get('work_coordination')
        if not coordination or queue['task'] not in coordination['tasks']:
            return False
        validate_coordination(runtime, selection)
    visiting = set()
    def ancestry(event_id, coordination_edge=False):
        if event_id in visiting:
            return False
        visiting.add(event_id)
        try:
            source = runtime.event(event_id)
            if source.get('package') != queue['package']:
                return False
            if event_id == record['event']:
                return digest(source) == receipt['software_admission']['source_hash']
            # Software-generated returns bind every member to its actual frozen
            # source job/attempt. Parent-only traversal loses later members.
            if source.get('source_job'):
                job = runtime.job(source['source_job'])
                members = json.loads(job['members'])
                if (source.get('source_members') != members or not members
                        or source.get('source_attempt') != job['active_attempt']
                        or source.get('source_role') != job['role']
                        or job['package'] != queue['package']):
                    return False
                if coordination_edge:
                    upstream = (job['role'] == 'QA' and job['phase'] == 'cleanup' and job['task'] in receipt['task_scopes']
                                if receiver else job['role'] in coordination['source_roles'] and job['task'] in receipt['task_scopes'])
                    continuation = not receiver and job['role'] == 'Work' and job['task'] in coordination['tasks']
                    if not (upstream or continuation):
                        return False
                    # The exact configured return route cannot be forged by a
                    # body claiming to be a result from an unrelated role.
                    from .contracts import response_tasks, collected_task_result
                    attempt = runtime.attempt(job['active_attempt'])
                    if (attempt['collected'] is None or attempt['ended'] is None or attempt['exit'] != 0
                            or attempt['error'] or not collected_capture(attempt)
                            or receiver and (attempt['job'] != job['id'] or attempt['controller'] != job['controller'])
                            or source.get('body') != collected_task_result(attempt)
                            or receiver and (source['body'].get('semantic') != 'DONE' or source['body'].get('category') != 'qualification')
                            or queue['task'] not in response_tasks(runtime.config['tasks'][job['task']], source['body'], runtime.config)):
                        return False
                return all(digest(runtime.event(m['event'])) == m['hash'] and
                           not runtime.one('SELECT hold FROM events WHERE id=?', (m['event'],))['hold'] and
                           (not runtime.processing or runtime.processing.event(runtime.event(m['event']))) and
                           ancestry(m['event']) for m in members)
            if source.get('source_delivery'):
                delivery = source['source_delivery']
                outbox = runtime.one('SELECT * FROM outboxes WHERE id=?', (delivery.get('id'),))
                link = runtime.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (delivery.get('id'),))
                if not outbox or not outbox['job'] or not link or link['event'] != event_id:
                    return False
                payload = json.loads(outbox['payload'])
                job = runtime.job(outbox['job'])
                members = json.loads(job['members'])
                attempt = runtime.attempt(job['active_attempt'])
                from .contracts import collected_task_result
                answer = collected_task_result(attempt)
                if (source.get('body') != payload or delivery.get('source_hash') != digest(payload)
                        or payload.get('source_members') != members or not members
                        or payload.get('package') != queue['package'] or job['package'] != queue['package']
                        or payload.get('attempt') != attempt['id'] or payload.get('source_result') != answer
                        or payload.get('original_handoff') not in answer.get('handoffs', [])
                        or attempt['collected'] is None or attempt['ended'] is None or attempt['exit'] != 0
                        or attempt['error'] or not collected_capture(attempt)):
                    return False
                if receiver and (attempt['job'] != job['id'] or attempt['controller'] != job['controller']):
                    return False
                if coordination_edge:
                    from . import prospective
                    epoch = prospective.for_job(runtime, job)
                    task = epoch['policy'] if epoch else runtime.config['tasks'][job['task']]
                    source_roles = ['QA'] if receiver else coordination['source_roles']
                    destination = 'Branch' if receiver else 'Work'
                    if (job['role'] not in source_roles or job['task'] not in receipt['task_scopes']
                            or receiver and (job['phase'] != 'cleanup' or answer.get('semantic') != 'DONE' or answer.get('category') != 'qualification')
                            or queue['task'] not in task.get('software_handoffs', {}).get(destination, [])):
                        return False
                return all(digest(runtime.event(m['event'])) == m['hash'] and
                           not runtime.one('SELECT hold FROM events WHERE id=?', (m['event'],))['hold'] and
                           (not runtime.processing or runtime.processing.event(runtime.event(m['event']))) and
                           ancestry(m['event']) for m in members)
            if coordination_edge:
                return False  # Message-authored lineage is no automatic return.
            return bool(source.get('parent')) and ancestry(source['parent'])
        finally:
            visiting.remove(event_id)
    return ancestry(queue['event'], coordination is not None or bool(receiver))


def admit_pending(runtime):
    policy = runtime.processing.current()[1].get('software_admission')
    if not policy:
        return
    from .configuration import event_candidate_scope
    scope, parameters = event_candidate_scope(runtime)
    candidates = runtime.rows("SELECT e.id,e.role FROM events e WHERE e.state='received' "
                              "AND e.hold IS NULL AND (" + scope + ") ORDER BY e.received,e.id", parameters)
    for row in candidates:
        event = runtime.event(row['id'])
        body = event.get('body')
        if not isinstance(body, dict) or not isinstance(body.get('topic'), str) or body['topic'] not in policy['scopes']:
            continue
        try:
            admit(runtime, row['id'])
        except (Refusal, OSError, TypeError, ValueError) as exc:
            runtime.record_operational_error(row['id'], {'dependency': str(exc)}, row['role'], 'processing-admission-dependency')


def resolved(runtime, package, topic, scope_hash):
    """Exact current Work-issued selection -> immutable applied admission."""
    cap, selected = runtime.processing.current()
    runtime.processing.boards['Work'].verify_authority(runtime)
    row = runtime.one('SELECT * FROM processing_admission_resolutions WHERE package=?', (package,))
    applied = runtime.one('SELECT * FROM admissions WHERE package=?', (package,))
    original = runtime.one('SELECT * FROM processing_admissions WHERE package=?', (package,))
    scope = selected.get('software_admission', {}).get('scopes', {}).get(topic)
    if (cap['issuer'] != runtime.config['roles']['Work']['owner'] or not row or not applied or not original
            or not scope or row['capability'] != cap['id'] or original['capability'] != cap['id']
            or row['topic'] != topic or original['scope'] != topic or row['scope_hash'] != scope_hash
            or digest(scope) != scope_hash or digest(applied) != row['admission_hash']
            or applied['receipt'] != original['receipt'] or applied['owner'] != runtime.config['actor']
            or row['event'] != original['event']):
        raise Refusal('unchanged runtime-resolved current software admission required')
    event = runtime.event(row['event'])
    state = runtime.one('SELECT hold,hash FROM events WHERE id=?', (row['event'],))
    receipt = json.loads(applied['receipt'])
    if (state['hold'] or state['hash'] != row['source_hash'] or digest(event) != row['source_hash']
            or not runtime.processing.event(event) or event.get('author') not in scope['submitters']
            or event.get('body', {}).get('topic') != topic or event.get('package') != package
            or receipt['software_admission']['scope_hash'] != scope_hash
            or receipt['software_admission']['capability'] != cap['id']):
        raise Refusal('original topic/source/submitter identity changed or held')
    return applied
