"""Local sequential mutable execution. Public contracts live in README.md.

Declared roles: orchestration, validator, parser, mapper, accessor, formatter, predicate.
"""
import base64
import fcntl
import json
import signal
import sqlite3
import subprocess
import uuid
from contextlib import contextmanager


class ContractError(ValueError):
    """Rejected input; no work is authorized by rejection."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def fields(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected),
            f"expected fields: {', '.join(expected)}")


def text(value):
    require(isinstance(value, str) and bool(value.strip()), 'nonempty text required')


def validate_steps(steps, workers, existing=()):
    require(isinstance(steps, list) and bool(steps), 'nonempty steps required')
    ids = list(existing)
    for step in steps:
        validate_step(step, workers)
        ids.append(step['id'])
    require(len(ids) == len(set(ids)), 'step IDs must be unique')


def validate_step(step, workers):
    fields(step, ('id', 'worker', 'input'))
    text(step['id'])
    require(isinstance(step['worker'], str) and step['worker'] in workers,
            'worker not authorized by caller')


def validate_worker(name, argv):
    text(name)
    require(isinstance(argv, list) and bool(argv), 'worker argv required')
    for arg in argv:
        text(arg)
    require(argv[0].startswith('/'), 'worker executable must be absolute')


def validate_plan(plan):
    fields(plan, ('purpose', 'workers', 'steps'))
    text(plan['purpose'])
    require(isinstance(plan['workers'], dict) and bool(plan['workers']), 'workers required')
    for name, argv in plan['workers'].items():
        validate_worker(name, argv)
    validate_steps(plan['steps'], plan['workers'])
    return plan


@contextmanager
def exclusive(directory, name="writer.lock", blocking=False):
    with (directory / name).open("a") as lock:
        acquire_lock(lock, blocking)
        yield


def acquire_lock(lock, blocking=False):
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
    except BlockingIOError as exc:
        raise ContractError('writer or executor busy; inspect and retry/rebase intent') from exc


def connect(directory):
    # Encode the literal filename before adding SQLite options; never create on reconnect.
    uri = (directory / 'state.sqlite3').absolute().as_uri()
    db = sqlite3.connect(f"{uri}?mode=rw", uri=True)
    db.execute('PRAGMA synchronous=FULL')
    return db


def initialize(directory, plan):
    validate_plan(plan)
    directory.mkdir(mode=0o700)
    db = sqlite3.connect(directory / 'state.sqlite3')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
        CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
        CREATE TABLE events (cursor INTEGER PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE attempts (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
    ''')
    state = dict(plan, run_id=str(uuid.uuid4()), status='ready', position=0,
                 cursor=0, attempts=[], edits=[], version=2, policy=None, active_attempt=None,
                 node_ids=[], nodes={})
    state['node_ids'] = [add_node(state, step) for step in state['steps']]
    save(db, state, 'started', {'purpose': plan['purpose']})
    db.close()


def add_node(state, step):
    key = str(len(state["nodes"]) + 1)
    state["nodes"][key] = dict(step=step, disposition="scheduled")
    return key


def load(db):
    row = db.execute('SELECT body FROM state WHERE id=1').fetchone()
    require(row is not None, 'initialization incomplete; no execution admitted')
    state = json.loads(row[0])
    require(state.get("version") == 2, "unsupported run version; use original runtime for v1 runs")
    return state


def save(db, state, kind, detail, attempt=None, updated=()):
    state['cursor'] += 1
    event = dict(cursor=state['cursor'], kind=kind, detail=detail)
    with db:
        db.execute('INSERT OR REPLACE INTO state VALUES (1, ?)', (json.dumps(state),))
        db.execute('INSERT INTO events VALUES (?, ?)', (state['cursor'], json.dumps(event)))
        store_attempt(db, attempt)
        store_updates(db, updated)


def store_updates(db, updated):
    for attempt in updated:
        store_attempt(db, attempt)


def store_attempt(db, attempt):
    if attempt is not None:
        db.execute('INSERT OR REPLACE INTO attempts VALUES (?, ?)',
                   (attempt['id'], json.dumps(attempt)))


def read_attempt(db, attempt_id):
    row = db.execute('SELECT body FROM attempts WHERE id=?', (attempt_id,)).fetchone()
    require(row is not None, 'attempt output missing')
    return json.loads(row[0])


def inspection(db, since):
    # One read transaction binds the current view and event interval.
    db.execute('BEGIN')
    state = load(db)
    require(0 <= since <= state['cursor'], 'cursor outside this run history')
    events = db.execute('SELECT body FROM events WHERE cursor>? ORDER BY cursor', (since,))
    return dict(current=state, events=[json.loads(row[0]) for row in events],
                cursor=state['cursor'])


def request_for(state, step, attempt_id):
    return dict(run_id=state['run_id'], purpose=state['purpose'], step=step,
                attempt_id=attempt_id, edits=state['edits'], policy=state['policy'],
                node_id=state['node_ids'][state['position']], basis_cursor=state['cursor'])


def begin_attempt(db, state):
    step = state['steps'][state['position']]
    attempt_id = len(state['attempts']) + 1
    attempt = dict(id=attempt_id, request=request_for(state, step, attempt_id),
                   outcome='running', output=None, cancellation='not_requested',
                   orphaned=False)
    state['status'] = 'running'
    state['active_attempt'] = attempt_id
    state['attempts'].append(dict(id=attempt_id, step_id=step['id'],
                                  node_id=attempt['request']['node_id'], outcome='running'))
    save(db, state, 'attempt_started', {'attempt_id': attempt_id}, attempt)
    return attempt


def parse_result(stdout):
    result = json.loads(stdout)
    fields(result, ('outcome', 'detail'))
    require(result['outcome'] in ('success', 'failure', 'judgment'), 'unknown worker outcome')
    text(result['detail'])
    return result


def classify(returncode, stdout):
    if returncode != 0:
        return dict(outcome='failure', detail=f'worker process exit {returncode}; inspect raw output')
    try:
        return parse_result(stdout)
    except (ValueError, TypeError, UnicodeError) as exc:
        return dict(outcome='ambiguous', detail=f'no admissible substantive result: {exc}')


def captured(returncode, stdout, stderr):
    return dict(returncode=returncode, stdout_b64=base64.b64encode(stdout).decode(),
                stderr_b64=base64.b64encode(stderr).decode(), result=classify(returncode, stdout))


def signal_cancellation(db, directory, attempt_id, process, sent):
    if sent:
        return True
    with exclusive(directory, blocking=True):
        return cancel_if_requested(db, attempt_id, process)


def cancel_if_requested(db, attempt_id, process):
    attempt = read_attempt(db, attempt_id)
    if attempt['cancellation'] != 'requested':
        return False
    return send_cancel(db, attempt, process)


def send_cancel(db, attempt, process):
    state = load(db)
    try:
        process.terminate()
    except ProcessLookupError:
        attempt['cancellation'] = 'unavailable'
        save(db, state, 'cancellation_unavailable', {'attempt_id': attempt['id']}, attempt)
        return False
    save(db, state, 'cancellation_signal_sent', {'attempt_id': attempt['id']}, attempt)
    return True


def communicate_tick(process, payload=None):
    try:
        stdout, stderr = process.communicate(input=payload, timeout=0.05)
        return captured(process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        return None


def collect_process(db, directory, attempt, process):
    output = communicate_tick(process, json.dumps(attempt['request']).encode())
    sent = False
    while output is None:
        sent = signal_cancellation(db, directory, attempt['id'], process, sent)
        output = communicate_tick(process)
    return output, sent


def invoke(db, argv, attempt, directory):
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=directory)
    except OSError as exc:
        return dict(returncode=None, stdout_b64='', stderr_b64='',
                    result=dict(outcome='failure', detail=f'worker launch failed: {exc}')), False
    with process:
        return collect_process(db, directory, attempt, process)


def skipped_target(state):
    return (state['position'] < len(state['steps']) and
            state['nodes'][state['node_ids'][state['position']]]['disposition'] != 'scheduled')


def advance(state):
    while skipped_target(state):
        state['position'] += 1
    state['status'] = 'success' if state['position'] == len(state['steps']) else 'ready'


def settle_cancellation(attempt, output, sent):
    if attempt['cancellation'] != 'requested':
        return
    confirmed = sent and output['returncode'] == -signal.SIGTERM
    attempt['cancellation'] = 'confirmed' if confirmed else 'unavailable'
    if confirmed:
        output['result'] = dict(outcome='cancelled',
                                detail='direct worker exited by requested SIGTERM; effects not undone')


def finish_attempt(db, state, attempt, output, sent):
    require(attempt['output'] is None, 'attempt already settled')
    settle_cancellation(attempt, output, sent)
    outcome = output['result']['outcome']
    credited = state['active_attempt'] == attempt['id']
    attempt.update(outcome=outcome, output=output, credited=credited)
    state['attempts'][attempt['id'] - 1]['outcome'] = outcome
    if credited:
        settle_current(state, outcome)
    save(db, state, 'attempt_returned', dict(attempt_id=attempt['id'], outcome=outcome,
         credited=credited, cancellation=attempt['cancellation']), attempt)


def settle_current(state, outcome):
    state['active_attempt'] = None
    state['status'] = outcome
    if outcome == 'success':
        state['position'] += 1
        advance(state)


def admit_ready(db):
    state = load(db)
    if state['status'] != 'ready':
        return None
    attempt = begin_attempt(db, state)
    return attempt, state['workers'][attempt['request']['step']['worker']]


def run_step(db, directory):
    with exclusive(directory, blocking=True):
        admission = admit_ready(db)
    if admission is None:
        return False
    attempt, argv = admission
    output, sent = invoke(db, argv, attempt, directory)
    with exclusive(directory, blocking=True):
        finish_attempt(db, load(db), read_attempt(db, attempt['id']), output, sent)
    return True


def recover_attempt(db, state, summary):
    attempt = read_attempt(db, summary['id'])
    if attempt['outcome'] != 'running' or attempt['orphaned']:
        return
    attempt['orphaned'] = True
    if attempt['cancellation'] == 'requested':
        attempt['cancellation'] = 'unavailable'
    if state['status'] in ('ready', 'running'):
        state['status'] = 'ambiguous'
    save(db, state, 'interrupted', dict(attempt_id=attempt['id'],
         detail='collector lost; execution/effects unknown; no automatic replay'), attempt)


def drive(db, directory, max_steps):
    # Executor ownership is distinct from short edit/settlement exclusion.
    with exclusive(directory, 'executor.lock'):
        return drive_owned(db, directory, max_steps)


def recover_interruption(db):
    state = load(db)
    for summary in state['attempts']:
        recover_attempt(db, state, summary)


def drive_owned(db, directory, max_steps):
    with exclusive(directory):
        recover_interruption(db)
    count = 0
    while (max_steps is None or count < max_steps) and run_step(db, directory):
        count += 1
    return load(db)


def validate_edit(edit, state):
    fields(edit, ('run_id', 'cursor', 'blocked_step', 'actor', 'reason', 'insert'))
    require(state['status'] in ('failure', 'judgment'), 'not an editable judgment boundary')
    require(edit['run_id'] == state['run_id'] and type(edit['cursor']) is int
            and edit['cursor'] == state['cursor'], 'stale or foreign judgment context')
    require(edit['blocked_step'] == state['steps'][state['position']]['id'], 'wrong blocked step')
    text(edit['actor'])
    text(edit['reason'])
    validate_steps(edit['insert'], state['workers'], [step['id'] for step in state['steps']])


def apply_edit(db, edit):
    state = load(db)
    validate_edit(edit, state)
    state['edits'].append(edit)
    position = state['position'] + 1
    state['steps'][position:position] = edit['insert']
    keys = [add_node(state, step) for step in edit['insert']]
    state['node_ids'][position:position] = keys
    state['position'] = position
    state['status'] = 'ready'
    save(db, state, 'recovery_inserted', edit)
    return state
