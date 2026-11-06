"""Authenticated informative Source receipts, separate from clean processing.

Only the original collector records these receipts. They permit the selected
sole report integrator to map an actually collected PARTIAL return, without
completing Source, taking over its context or accepting any business effects.
"""
import json

from .contracts import Refusal, collected_task_result, digest, encode, response_tasks

SCHEMA = """
CREATE TABLE IF NOT EXISTS review_report_returns(
 event TEXT PRIMARY KEY,attempt TEXT NOT NULL UNIQUE,payload_hash TEXT NOT NULL,
 binding TEXT NOT NULL);
"""


def identity(store, job, attempt, outcome):
    """Recheck actual collection and current original rights, not envelope claims."""
    from . import reviews, local_integration as local
    if (not store.processing or job['role'] != 'Reviews' or job['phase'] != 'proposer'
            or not store.processing.review_task(job['task'])
            or job['active_attempt'] != attempt['id'] or attempt['job'] != job['id']
            or job['controller'] != store.controller or attempt['controller'] != store.controller
            or attempt['kind'] != 'task' or attempt['state'] != 'collected'
            or attempt['begin'] is None or attempt['ended'] is None or attempt['collected'] is None
            or attempt['exit'] != 0 or attempt['capture'] != 'complete' or attempt['error']):
        raise Refusal('informative report requires its actual current original Source collection')
    store.processing.authorize(attempt)
    boards = store.processing.boards or {}
    board = boards.get('Reviews')
    if not board:
        raise Refusal('informative report requires its current original role authority checker')
    board._software_job_grant(store, job)
    answer = collected_task_result(attempt)
    if answer['semantic'] != 'PARTIAL':
        raise Refusal('informative mapping is only for an actually collected PARTIAL Source report')
    routes = response_tasks(store.config['tasks'][job['task']], answer, store.config)
    integrators = [n for n, t in store.config['tasks'].items()
                   if t['role'] == 'Reviews' and t['phase'] == 'integrator']
    selection = store.processing.current()[1]
    if (len(integrators) != 1 or routes != integrators
            or selection.get('service', {}).get('report_tasks') != routes
            or routes[0] not in selection['tasks']
            or store.config['tasks'][routes[0]].get('execution') == 'owner'):
        raise Refusal('informative mapping requires the explicitly selected sole Reviews report integrator')
    board.software_authority(store, routes[0])
    proof = reviews.collected_proof(store, job, attempt)
    call = store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt['id'],))
    record = store.one('SELECT * FROM results WHERE attempt=?', (attempt['id'],))
    if not proof or not call or not record or not isinstance(outcome, dict):
        raise Refusal('informative report needs original call, outcome and collected Source proof')
    turns = json.loads(call['receipt'])
    acquired = json.loads(call['packet'])
    returned = json.loads(call['answer'])
    expected = reviews.proposal_result(returned, call['component'], acquired,
                                       call['collector'], attempt['id'], turns)
    fields = ('exit', 'capture', 'cleanup', 'error')
    if (call['collector'] != store.controller or acquired.get('selected_task') != job['task']
            or not turns or call['answer'] != turns[-1].get('full_answer')
            or expected != answer or outcome.get('result') != answer
            or any(outcome.get(k) != attempt[k] for k in fields)
            or outcome.get('detail', {}).get('native_original_calls') != turns
            or json.loads(attempt['detail']).get('native_original_calls') != turns
            or any(record[k] != attempt[k] for k in ('result', 'error', 'exit', 'capture', 'job'))):
        raise Refusal('informative report differs from its whole original call/outcome/collection')
    context = store.one('SELECT * FROM review_contexts WHERE component=?', (call['component'],))
    context_call = store.one('SELECT * FROM review_call_contexts WHERE attempt=?', (attempt['id'],))
    history = store.one('SELECT * FROM review_history_commits WHERE attempt=?', (attempt['id'],))
    if (not context or not context_call or not history or context['state'] != 'live'
            or context['collector'] != attempt['controller'] or context['run'] != attempt['session']
            or context['capability'] != store.processing.key or history['state'] != 'applied'
            or history['component'] != call['component'] or history['head'] != acquired['packet']['head']
            or history['before_hash'] != acquired['history_sha256']
            or history['after_hash'] != context['history_hash']):
        raise Refusal('informative report needs its original live context and applied history custody')
    members = json.loads(job['members'])
    if not members:
        raise Refusal('informative report cannot discard original frozen members')
    for member in members:
        original = store.event(member['event'])
        state = store.one('SELECT hash,hold FROM events WHERE id=?', (member['event'],))
        if (not state or state['hold'] or state['hash'] != member['hash']
                or digest(original) != member['hash'] or member['package'] != job['package']
                or not store.processing.event(original)
                or original.get('body', {}).get('review') != acquired['packet']):
            raise Refusal('informative report original member/hash/package/permission changed')
    from .branches import job_branch_key
    return {'job': job['id'], 'attempt': attempt['id'], 'collector': attempt['controller'],
            'run': attempt['session'], 'package': job['package'], 'members': members,
            'branch': job_branch_key(store, job), 'routes': routes,
            'source_rights': local.mapping_binding(store, job['task'], job['package']),
            'receiver_rights': local.mapping_binding(store, routes[0], job['package']),
            'review_policy': digest(selection['service']['reviews'][job['task']]),
            'call': digest(call), 'outcome': digest(outcome), 'collection': digest(record),
            'context': digest(context_call), 'history': digest(history),
            'attempt_truth': {k: attempt[k] for k in ('binding', 'begin', 'ended', 'collected',
                                                    'exit', 'capture', 'cleanup', 'result', 'error')}}


def record(store, event, job, attempt, outcome):
    """Persist once in the emission transaction; never restamp old input rights."""
    binding = identity(store, job, attempt, outcome)
    old = store.one('SELECT * FROM review_report_returns WHERE attempt=?', (attempt['id'],))
    expected = {'event': event['id'], 'attempt': attempt['id'],
                'payload_hash': digest(event), 'binding': encode(binding)}
    state = store.one('SELECT hash FROM events WHERE id=?', (event['id'],))
    if old:
        if (old != expected or not state or state['hash'] != expected['payload_hash']
                or store.event(event['id']) != event):
            raise Refusal('original informative report receipt changed; no replay or restamping')
        return
    if state:
        raise Refusal('existing unreceipted report cannot acquire new mapping rights')
    store.budget(None, len(encode(expected).encode()), job=job['id'])
    store.db.execute('INSERT INTO review_report_returns VALUES(?,?,?,?)', tuple(expected.values()))


def proof(store, event, task):
    """Authenticate only collector-recorded envelopes; no status/kind exemption."""
    row = store.one('SELECT * FROM review_report_returns WHERE event=?', (event['id'],))
    if not row:
        return None
    attempt = store.attempt(row['attempt'])
    job = store.job(attempt['job'])
    body = event.get('body', {})
    if not isinstance(body, dict):
        raise Refusal('informative report requires its original structured envelope')
    binding = identity(store, job, attempt, body.get('full_original_outcome'))
    expected = {'id': digest({'incomplete_ordinary_review': attempt['id']}),
                'role': 'Reviews', 'recipient': store.enrollment('Reviews')['owner'],
                'author': attempt['session'], 'kind': 'response',
                'parent': binding['members'][0]['event'], 'package': job['package'],
                'allowed_tasks': binding['routes'], 'notice': None, 'board_id': None, 'grant': None,
                'source_job': job['id'], 'source_attempt': attempt['id'],
                'source_role': job['role'], 'source_members': binding['members'],
                'body': {'status': 'PARTIAL',
                         'full_original_call': store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt['id'],)),
                         'full_original_outcome': body.get('full_original_outcome'),
                         'meaning': 'Source incomplete; sole integrator must preserve all reports, dissent and gaps'}}
    if binding['branch']:
        expected['branch_binding'] = binding['branch']
    state = store.one('SELECT hash,hold FROM events WHERE id=?', (event['id'],))
    if (task not in binding['routes'] or event != expected or not state or state['hold']
            or state['hash'] != row['payload_hash'] or digest(event) != row['payload_hash']
            or encode(binding) != row['binding']):
        raise Refusal('informative report original lineage/route/rights/payload changed')
    return binding


def observes_source(store, row, members, scope, source):
    """A report read may coexist with its held, collected Source responsibility.

    This is not execution capacity release. All global/resource/native-busy
    checks still apply, and writes or unrelated/mixed unproved inputs retain
    the ordinary unknown-scope fence.
    """
    task = store.config['tasks'][row['task']]
    if (scope['lane'] != 'anchored' or scope['writes'] or not scope['reads']
            or task['role'] != 'Reviews' or task['phase'] != 'integrator'
            or task['effects'] not in {'none', 'owned-artifacts'}
            or task.get('routine_completion') or source['state'] != 'held'):
        return False
    receipts = [proof(store, store.event(m['event']), row['task']) for m in members]
    return bool(receipts and all(r and r['job'] == source['id'] for r in receipts))
