"""Work-scoped prospective software admission in the original journal.

The issuer freezes exact reusable scopes. A future addressed source may select
one by topic; its text supplies no paths, effects, acceptance or native consent.
Existing admissions, jobs, holds and old sources are never replaced or released.
"""
import json
from pathlib import Path

from .contracts import Refusal, digest, encode, required_text, scoped_task


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
        return {'package': package, 'receipt': receipt, 'acceptance_inferred': False,
                'native_owner_consent': False, 'existing_holds': 'unchanged'}


def permits(runtime, queue):
    """An admitted new package cannot unlock an older same-name responsibility."""
    record = runtime.one('SELECT * FROM processing_admissions WHERE package=?', (queue['package'],))
    if not record:
        return True  # Original owner admissions retain their existing path.
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (queue['package'],))
    receipt = json.loads(record['receipt'])
    if (not admission or admission['owner'] != runtime.config['actor']
            or admission['receipt'] != record['receipt'] or queue['task'] not in receipt['task_scopes']):
        return False
    # An exact descendant inherits the same package scope, never another source
    # with a coincidentally matching ref. Cycle detection is not a depth cap.
    current, visited = queue['event'], set()
    while current and current not in visited:
        visited.add(current)
        source = runtime.event(current)
        if current == record['event']:
            return digest(source) == receipt['software_admission']['source_hash']
        if source.get('package') != queue['package']:
            return False
        current = source.get('parent')
    return False


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
