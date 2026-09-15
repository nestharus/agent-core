"""Bounded durable graph diagnostics, not repair or tamper authentication.

Declared roles: validator, orchestration.
"""
import base64
import json


def check(condition, message):
    if not condition:
        raise ValueError('inconsistent durable history: ' + message)


def validate(db, state):
    try:
        validate_history(db, state)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError(f'inconsistent durable history: missing/malformed field {exc}') from exc


def validate_history(db, state):
    events = [(cursor, json.loads(body)) for cursor, body in db.execute(
        'SELECT cursor,body FROM events ORDER BY cursor')]
    check(type(state['cursor']) is int and state['cursor'] > 0, 'invalid cursor')
    check([cursor for cursor, _ in events] == list(range(1, state['cursor'] + 1)),
          'missing or extra events; restore intact storage, never reset')
    for cursor, event in events:
        check(event['cursor'] == cursor and isinstance(event['detail'], dict), 'event identity/body')
    check(events[0][1]['kind'] == 'started', 'missing initialization event')
    validate_graph(state)
    rows = [(identity, json.loads(body)) for identity, body in db.execute(
        'SELECT id,body FROM attempts ORDER BY id')]
    check([identity for identity, _ in rows] == list(range(1, len(state['attempts']) + 1)),
          'missing or extra attempt rows')
    index = attempt_events(events)
    for identity, attempt in rows:
        validate_attempt(state, identity, attempt, index)
    active = state['active_attempt']
    check(active is None or (type(active) is int and 1 <= active <= len(rows)), 'active attempt missing')
    if active is not None:
        validate_active(state, rows[active - 1][1])


def validate_graph(state):
    check(type(state['position']) is int and 0 <= state['position'] <= len(state['steps']), 'position')
    check(len(state['steps']) == len(state['node_ids']), 'graph membership length')
    check(len(set(state['node_ids'])) == len(state['node_ids']), 'duplicate node membership')
    check(len({step['id'] for step in state['steps']}) == len(state['steps']), 'duplicate step IDs')
    for key, step in zip(state['node_ids'], state['steps']):
        check(state['nodes'][key]['step'] == step and state['nodes'][key]['disposition'] != 'removed',
              'graph/archive mismatch')
    check(state['status'] in ('ready', 'running', 'success', 'failure', 'judgment', 'ambiguous',
                              'aborted', 'cancelled'), 'status')
    check(state['status'] != 'success' or state['position'] == len(state['steps']), 'false exhaustion')
    check(state['status'] in ('success', 'aborted') or state['position'] < len(state['steps']), 'missing current target')
    check(state['status'] != 'running' or state['active_attempt'] is not None, 'running without active attempt')


def attempt_events(events):
    index = {}
    for _, event in events:
        index_attempt_event(index, event)
    return index


def index_attempt_event(index, event):
    if event['kind'] not in ('attempt_started', 'attempt_returned'):
        return
    identity = event['detail'].get('attempt_id')
    check(type(identity) is int, 'attempt event identity')
    index.setdefault((event['kind'], identity), []).append(event)


def validate_attempt(state, identity, attempt, events):
    summary = state['attempts'][identity - 1]
    request = attempt['request']
    check(attempt['id'] == summary['id'] == request['attempt_id'] == identity, 'attempt identity')
    check(request['run_id'] == state['run_id'], 'foreign attempt')
    check(request['step'] == state['nodes'][request['node_id']]['step'], 'attempt/archive mismatch')
    check(summary['node_id'] == request['node_id'] and summary['step_id'] == request['step']['id'],
          'attempt summary identity')
    check(summary['outcome'] == attempt['outcome'], 'attempt summary outcome')
    check(type(request['basis_cursor']) is int and 0 < request['basis_cursor'] < state['cursor'], 'attempt basis')
    admissions = events.get(('attempt_started', identity), [])
    check(len(admissions) == 1 and admissions[0]['cursor'] == request['basis_cursor'] + 1, 'attempt admission')
    returns = events.get(('attempt_returned', identity), [])
    check(len(returns) == (0 if attempt['output'] is None else 1), 'attempt return evidence')
    validate_output(attempt)
    if returns:
        check(returns[0]['detail']['outcome'] == attempt['outcome']
              and returns[0]['detail']['credited'] == attempt['credited'], 'return projection')


def validate_active(state, attempt):
    check(attempt['output'] is None, 'settled active attempt')
    check(state['position'] < len(state['node_ids'])
          and state['node_ids'][state['position']] == attempt['request']['node_id'], 'active target')


def validate_output(attempt):
    output = attempt['output']
    check(type(attempt['orphaned']) is bool and attempt['cancellation'] in
          ('not_requested', 'requested', 'confirmed', 'unavailable'), 'cancellation/orphan projection')
    if output is None:
        check(attempt['outcome'] == 'running', 'uncollected outcome')
        return
    check(type(attempt['credited']) is bool, 'missing credit evidence')
    check(isinstance(output, dict) and set(output) ==
          {'returncode', 'stdout_b64', 'stderr_b64', 'result'}, 'missing output fields')
    check(output['returncode'] is None or type(output['returncode']) is int, 'return code')
    for key in ('stdout_b64', 'stderr_b64'):
        base64.b64decode(output[key], validate=True)
    result = output['result']
    check(set(result) == {'outcome', 'detail'} and result['outcome'] in
          ('success', 'failure', 'judgment', 'ambiguous') and isinstance(result['detail'], str)
          and bool(result['detail'].strip()), 'worker result')
    expected = 'cancelled' if attempt['cancellation'] == 'confirmed' else result['outcome']
    check(attempt['outcome'] == expected, 'scheduling/worker outcome mismatch')
