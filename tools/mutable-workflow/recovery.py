"""Worker-owned retry admission. See README.md; never infer safety from editor prose.

Declared roles: orchestration, validator, mapper, accessor.
"""
import json
import subprocess

from runtime import (captured, exclusive, fields, finish_attempt, invoke, load, read_attempt,
                     recover_interruption, require, save, text)


def recover(db, directory, attempt_id, redeliver=False):
    with exclusive(directory, 'executor.lock'):
        return recover_owned(db, directory, attempt_id, redeliver)


def recover_owned(db, directory, attempt_id, redeliver):
    with exclusive(directory, blocking=True):
        recover_interruption(db)
    state = load(db)
    attempt = read_attempt(db, attempt_id)
    if attempt['output'] is not None:
        return dict(current=state, attempt=attempt, next_action='settled; no redelivery')
    worker = attempt['request']['step']['worker']
    require(state.get('recovery', {}).get(worker) == 'deduplicated-attempt-v1',
            'worker has no retry contract; effects remain unknown; reconcile with effect owner before new intent')
    argv = state['workers'][worker]
    observation = query(argv, attempt, directory)
    with exclusive(directory, blocking=True):
        record_query(db, attempt_id, observation)
    require(not redeliver or observation['disposition'] == 'retry_safe',
            'worker cannot establish safe redelivery; retain uncertainty and reconcile with effect owner')
    if redeliver:
        redeliver_attempt(db, directory, attempt_id, argv)
    return dict(current=load(db), attempt=read_attempt(db, attempt_id),
                next_action='explicit redeliver permitted by worker contract' if not redeliver
                and observation['disposition'] == 'retry_safe' else 'inspect retained evidence')


def query(argv, attempt, directory):
    request = dict(protocol='deduplicated-attempt-v1', operation='recovery_query',
                   request=attempt['request'])
    process = subprocess.run(argv, input=json.dumps(request).encode(), capture_output=True,
                             cwd=directory, check=False)
    output = captured(process.returncode, process.stdout, process.stderr)
    try:
        value = validate_reply(json.loads(process.stdout), attempt['request'], process.returncode)
    except (ValueError, TypeError, UnicodeError) as exc:
        return dict(disposition='unknown', detail=str(exc), output=output)
    return dict(disposition=value['disposition'], detail=value['detail'], output=output)


def validate_reply(value, request, code):
    fields(value, ('protocol', 'run_id', 'attempt_id', 'disposition', 'detail'))
    require(code == 0 and value['protocol'] == 'deduplicated-attempt-v1'
            and value['run_id'] == request['run_id']
            and type(value['attempt_id']) is int and value['attempt_id'] == request['attempt_id'],
            'unbound or failed recovery query')
    require(value['disposition'] in ('retry_safe', 'unknown'), 'invalid recovery disposition')
    text(value['detail'])
    return value


def record_query(db, attempt_id, observation):
    attempt = read_attempt(db, attempt_id)
    attempt.setdefault('recovery_observations', []).append(observation)
    save(db, load(db), 'worker_recovery_observed', dict(attempt_id=attempt_id,
         observation=observation), attempt)


def redeliver_attempt(db, directory, attempt_id, argv):
    with exclusive(directory, blocking=True):
        attempt = admit_redelivery(db, attempt_id)
    output, submitted = invoke(db, argv, attempt, directory)
    with exclusive(directory, blocking=True):
        finish_attempt(db, load(db), read_attempt(db, attempt_id), output, submitted)


def admit_redelivery(db, attempt_id):
    attempt = read_attempt(db, attempt_id)
    require(attempt['output'] is None, 'attempt already settled')
    save(db, load(db), 'attempt_redelivered', dict(attempt_id=attempt_id,
         detail='same exact request; worker owns concurrent deduplication and replay guarantee'))
    return attempt
