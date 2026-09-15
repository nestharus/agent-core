"""Atomic future-intent editing; public operation contracts live in README.md.

Declared roles: orchestration, validator, mapper, accessor.
"""
from runtime import (add_node, advance, fields, load, read_attempt, require,
                     save, text, validate_steps)


def index(state, step_id):
    matches = [i for i, step in enumerate(state['steps']) if step['id'] == step_id]
    require(bool(matches), f'unknown current step: {step_id!r}')
    return matches[0]


def target_key(state):
    if state['position'] == len(state['steps']):
        return None
    return state['node_ids'][state['position']]


def retarget(state, position, reopen=False):
    aborted = state["status"] == "aborted" and not reopen
    state['active_attempt'] = None
    state['position'] = position
    advance(state)
    if aborted:
        state["status"] = "aborted"


def validate_context(edit, state):
    fields(edit, ('run_id', 'cursor', 'actor', 'reason', 'effects', 'operations'))
    require(edit['run_id'] == state['run_id'] and type(edit['cursor']) is int
            and edit['cursor'] == state['cursor'],
            f'stale or foreign edit; inspect current cursor {state["cursor"]} and rebase intent')
    for key in ('actor', 'reason', 'effects'):
        text(edit[key])
    require(isinstance(edit['operations'], list) and bool(edit['operations']),
            'nonempty operations required')


def splice(state, start, count, steps):
    remaining = state['steps'][:start] + state['steps'][start + count:]
    if steps:
        validate_steps(steps, state['workers'], [step['id'] for step in remaining])
    require(isinstance(steps, list), 'steps must be a list')
    old_target = target_key(state)
    old_length = len(state['steps'])
    removed = state['node_ids'][start:start + count]
    for key in removed:
        state['nodes'][key]['disposition'] = 'removed'
    keys = [add_node(state, step) for step in steps]
    state['steps'][start:start + count] = steps
    state['node_ids'][start:start + count] = keys
    if old_target is not None and old_target not in removed:
        state['position'] = state['node_ids'].index(old_target)
        return
    if old_target is None and start != old_length:
        retarget(state, len(state['steps']))
        return
    retarget(state, start)


def insert(state, op):
    fields(op, ('op', 'before', 'steps'))
    validate_steps(op['steps'], state['workers'])
    start = len(state['steps']) if op['before'] is None else index(state, op['before'])
    splice(state, start, 0, op['steps'])


def replace(state, op):
    fields(op, ('op', 'start', 'count', 'steps'))
    start = index(state, op['start'])
    require(type(op['count']) is int and 0 < op['count'] <= len(state['steps']) - start,
            'count must select a nonempty existing contiguous range')
    splice(state, start, op['count'], op['steps'])


def remove(state, op):
    fields(op, ('op', 'steps'))
    require(isinstance(op['steps'], list) and bool(op['steps']), 'step IDs required')
    require(all(isinstance(item, str) for item in op['steps']), 'step IDs must be strings')
    require(len(op['steps']) == len(set(op['steps'])), 'duplicate step selection')
    positions = sorted([index(state, item) for item in op['steps']], reverse=True)
    for position in positions:
        splice(state, position, 1, [])


def skip(state, op):
    fields(op, ('op', 'steps'))
    require(isinstance(op['steps'], list) and bool(op['steps']), 'step IDs required')
    positions = [index(state, item) for item in op['steps']]
    for position in positions:
        state['nodes'][state['node_ids'][position]]['disposition'] = 'skipped'
    if state['position'] in positions:
        retarget(state, state['position'])


def jump(state, op):
    fields(op, ('op', 'step'))
    position = index(state, op['step'])
    key = state['node_ids'][position]
    require(state['nodes'][key]['disposition'] == 'scheduled',
            'target not scheduled; replace it to create new work')
    retarget(state, position, reopen=True)


def abort(state, op):
    fields(op, ('op',))
    state['active_attempt'] = None
    state['status'] = 'aborted'


def policy(state, op):
    fields(op, ('op', 'value'))
    state['policy'] = op['value']
    if state['active_attempt'] is not None:
        retarget(state, state['position'])


def cancel(db, updates, op):
    fields(op, ('op', 'attempt'))
    require(type(op['attempt']) is int and op['attempt'] > 0, 'positive attempt ID required')
    attempt = updates.get(op['attempt']) or read_attempt(db, op['attempt'])
    require(attempt['cancellation'] == 'not_requested', 'cancellation already recorded')
    available = attempt['outcome'] == 'running' and not attempt['orphaned']
    attempt['cancellation'] = 'requested' if available else 'unavailable'
    updates[attempt['id']] = attempt


OPERATIONS = dict(insert=insert, replace=replace, remove=remove, skip=skip,
                  goto=jump, **{'return': jump}, retry=jump, abort=abort, policy=policy)


def apply_operation(db, state, updates, op):
    require(isinstance(op, dict) and isinstance(op.get('op'), str), 'operation object required')
    if op['op'] == 'cancel':
        cancel(db, updates, op)
        return
    require(op['op'] in OPERATIONS, f'unknown operation: {op["op"]}')
    OPERATIONS[op['op']](state, op)


def amend(db, edit):
    state = load(db)
    validate_context(edit, state)
    updates = {}
    for op in edit['operations']:
        apply_operation(db, state, updates, op)
    state['edits'].append(edit)
    save(db, state, 'amended', edit, updated=updates.values())
    return state
