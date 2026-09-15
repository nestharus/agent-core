"""Finite POSIX collection owner for the purpose-built workflow runtime.

Declared roles: orchestration, accessor, mapper, validator.
No scheduler, restart, provider-output fetch or cached-PID signaling.
"""
import json
import os
import sqlite3
import uuid

from runtime import exclusive, require


def publish(path, value):
    temporary = path.with_name(path.name + '.' + str(uuid.uuid4()) + '.tmp')
    with temporary.open('x') as stream:
        json.dump(value, stream, ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run(directory, command, operation):
    # exclusive closes, never LOCK_UNs: the child inherits this same open file
    # description. Parent death cannot release the child's ownership. No DB
    # connection or provider process exists at fork in the supported CLI entry.
    with exclusive(directory, 'agent-collector.lock'):
        record = prepare(directory, command)
        status = launch(record, operation)
        return result(record, status)


def launch(record, operation):
    pid = os.fork()
    if pid == 0:
        own(record, operation)
    return os.waitpid(pid, 0)[1]


def result(record, status):
    require(os.waitstatus_to_exitcode(status) == 0,
            f'collection owner lost (exit {os.waitstatus_to_exitcode(status)}); inspect owner and exchange, collect retained evidence; '
            'submission/effects may be unknown, never resubmit')
    value = json.loads((record / 'result.json').read_text())
    require(isinstance(value, dict) and set(value) in ({'result'}, {'error'}),
            'malformed owner result; reconcile retained exchange')
    require('error' not in value, value.get('error', 'owner error'))
    return value['result']


def prepare(directory, command):
    identity = str(uuid.uuid4())
    record = directory / 'agent-owners' / identity
    record.mkdir(parents=True, mode=0o700)
    publish(record / 'intent.json', dict(version=1, id=identity, command=command))
    publish(directory / 'agent-owner.json', dict(version=1, id=identity))
    return record


def detach():
    os.setsid()
    # Do not keep a dead controller's stdout/stderr pipe open or write raw errors
    # to a second sink. Provider bytes still use the declared-secret transport.
    with open(os.devnull, 'r+b', buffering=0) as sink:
        redirect(sink.fileno())


def redirect(sink):
    for fd in (0, 1, 2):
        os.dup2(sink, fd)


def own(record, operation):
    try:
        detach()
        publish(record / 'started.json', dict(pid=os.getpid(), session=os.getsid(0)))
        value = perform(operation)
        publish(record / 'result.json', value)
    except BaseException:
        # Missing result is uncertainty, not a fabricated not-submitted outcome.
        os._exit(1)
    os._exit(0)


def perform(operation):
    try:
        return {'result': operation()}
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        return {'error': str(exc)}


def inspect(directory):
    try:
        return unlocked_observation(directory)
    except ValueError as exc:
        require('busy' in str(exc), str(exc))
        return observation(directory, True)


def unlocked_observation(directory):
    with exclusive(directory, 'agent-collector.lock'):
        return observation(directory, False)


def observation(directory, held):
    path = directory / 'agent-owner.json'
    value = dict(outcome='ownership_observation', lock_held=held, latest=None)
    if not path.exists():
        return value
    reference = json.loads(path.read_text())
    require(isinstance(reference, dict) and reference.get('version') == 1,
            'malformed collection owner reference')
    identity = reference.get('id')
    require(isinstance(identity, str) and str(uuid.UUID(identity)) == identity,
            'malformed collection owner identity')
    record = directory / 'agent-owners' / identity
    value['latest'] = dict(id=identity, path=str(record),
        intent=read_intent(record, identity),
        started=(record / 'started.json').exists(), result_recorded=(record / 'result.json').exists())
    value['guidance'] = ('owner/controller holds collection lock; wait for its return, do not duplicate'
        if held else 'no collection lock holder observed; collect existing key for reconciliation, '
        'not evidence that provider stopped or submission never happened')
    return value


def read_intent(record, identity):
    value = json.loads((record / 'intent.json').read_text())
    require(isinstance(value, dict) and set(value) == {'version', 'id', 'command'},
            'malformed collection owner intent; inspect retained exchange')
    require(value['version'] == 1 and value['id'] == identity
            and value['command'] in ('ask', 'collect'), 'foreign/unsupported collection owner intent')
    return value
