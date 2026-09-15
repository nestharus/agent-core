"""Local sequential mutable execution. Public contracts live in README.md.

Declared roles: orchestration, validator, parser, mapper, accessor, formatter.
"""
import base64
import fcntl
import json
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
def exclusive(directory):
    with (directory / 'writer.lock').open('a') as lock:
        acquire_lock(lock)
        yield


def acquire_lock(lock):
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise ContractError('executor busy; no concurrent mutation admitted') from exc


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
                 cursor=0, attempts=[], edits=[])
    save(db, state, 'started', {'purpose': plan['purpose']})
    db.close()


def load(db):
    row = db.execute('SELECT body FROM state WHERE id=1').fetchone()
    require(row is not None, 'initialization incomplete; no execution admitted')
    return json.loads(row[0])


def save(db, state, kind, detail, attempt=None):
    state['cursor'] += 1
    event = dict(cursor=state['cursor'], kind=kind, detail=detail)
    with db:
        db.execute('INSERT OR REPLACE INTO state VALUES (1, ?)', (json.dumps(state),))
        db.execute('INSERT INTO events VALUES (?, ?)', (state['cursor'], json.dumps(event)))
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
                attempt_id=attempt_id, edits=state['edits'])


def begin_attempt(db, state):
    step = state['steps'][state['position']]
    attempt_id = len(state['attempts']) + 1
    attempt = dict(id=attempt_id, request=request_for(state, step, attempt_id),
                   outcome='running', output=None)
    state['status'] = 'running'
    state['attempts'].append(dict(id=attempt_id, step_id=step['id'], outcome='running'))
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


def invoke(argv, request, directory):
    try:
        result = subprocess.run(argv, input=json.dumps(request).encode(), capture_output=True,
                                cwd=directory, check=False)
        return dict(returncode=result.returncode, stdout_b64=base64.b64encode(result.stdout).decode(),
                    stderr_b64=base64.b64encode(result.stderr).decode(),
                    result=classify(result.returncode, result.stdout))
    except OSError as exc:
        return dict(returncode=None, stdout_b64='', stderr_b64='',
                    result=dict(outcome='failure', detail=f'worker launch failed: {exc}'))


def finish_attempt(db, state, attempt, output):
    outcome = output['result']['outcome']
    attempt.update(outcome=outcome, output=output)
    state['attempts'][-1]['outcome'] = outcome
    state['status'] = outcome
    if outcome == 'success':
        state['position'] += 1
        state['status'] = 'success' if state['position'] == len(state['steps']) else 'ready'
    save(db, state, 'attempt_returned', {'attempt_id': attempt['id'], 'outcome': outcome}, attempt)


def run_step(db, state, directory):
    attempt = begin_attempt(db, state)
    argv = state['workers'][attempt['request']['step']['worker']]
    output = invoke(argv, attempt['request'], directory)
    finish_attempt(db, state, attempt, output)


def recover_interruption(db, state):
    if state['status'] != 'running':
        return
    state['status'] = 'ambiguous'
    save(db, state, 'interrupted', {'attempt_id': state['attempts'][-1]['id'],
         'detail': 'execution may have occurred; automatic replay and edits prohibited'})


def drive(db, directory, max_steps):
    state = load(db)
    recover_interruption(db, state)
    count = 0
    while state['status'] == 'ready' and (max_steps is None or count < max_steps):
        run_step(db, state, directory)
        count += 1
    return state


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
    state['position'] = position
    state['status'] = 'ready'
    save(db, state, 'recovery_inserted', edit)
    return state
