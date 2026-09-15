"""Controller/owner death controls through real finite-owner and fake runner seams."""
import json
import os
import signal
import socket
import subprocess
import sys
import uuid

import pytest
from test_mutable_workflow import call
from test_mutable_workflow_runner import agent, setup, mode, launches, start_held, finish_held, FAKE

DRIVER = FAKE.with_name('owner_driver.py')


def owner(run):
    return agent(run, 'owner')


def wait_unlocked(run):
    # Bounded test observation, not a production recovery retry/scheduler.
    subprocess.run([sys.executable, '-c',
        "import fcntl,sys; f=open(sys.argv[1],'a'); fcntl.flock(f,fcntl.LOCK_EX)",
        str(run / 'agent-collector.lock')], check=True, timeout=15)


def held(run, request, boundary):
    path = run.parent / 'owner-request.json'
    path.write_text(json.dumps(request))
    listener = socket.socket(socket.AF_UNIX)
    address = '\0owner-' + str(uuid.uuid4())
    listener.bind(address)
    listener.listen(1)
    listener.settimeout(15)
    process = subprocess.Popen([sys.executable, str(DRIVER), boundary, str(run), str(path), address[1:]],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    connection, _ = listener.accept()
    connection.settimeout(15)
    identity = json.loads(connection.recv(4096))
    return process, listener, connection, identity['pid']


@pytest.mark.parametrize('boundary', ['before-capture', 'after-eof-before-receipt',
    'after-receipt', 'before-collection', 'after-trace', 'after-collection'])
def test_controller_death_keeps_real_owner_and_settles_once(setup, boundary):
    run, request = setup
    mode(run.parent, kind='edit')
    process, listener, connection, pid = held(run, request, boundary)
    try:
        assert pid != process.pid and os.getsid(pid) == pid
        process.kill()
        process.communicate(timeout=15)  # Owner must not retain controller pipes.
        assert owner(run)['lock_held'] is True
        agent(run, 'collect', code=5)
        agent(run, 'ask', dict(request, key='duplicate'), code=5)
        connection.sendall(b'!')
        assert connection.recv(1) == b''
        wait_unlocked(run)
        result = agent(run, 'show')
        assert result['application'] == 'applied' and result['capture_receipt']['returncode'] == 0
        assert result['terminal_result']['success'] is True
        assert owner(run)['latest']['result_recorded'] is True
        before = call(run, 'inspect')
        assert agent(run, 'collect') == agent(run, 'ask', request) == result
        assert call(run, 'inspect') == before
        assert len(before['current']['edits']) == 1 and len(launches(run.parent)) == 1
    finally:
        connection.close()
        listener.close()
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=15)


@pytest.mark.parametrize('contrary', [False, True])
def test_controller_death_during_stream_preserves_complete_response_universe(setup, contrary):
    run, request = setup
    process, listener, connection = start_held(run, request, contrary_suffix=contrary)
    process.kill()
    process.communicate(timeout=15)
    assert owner(run)['lock_held'] is True
    finish_held(process, listener, connection)
    wait_unlocked(run)
    result = agent(run, 'show', code=4 if contrary else 0)
    data = open(result['log'], 'rb').read()
    assert data.count(b'MUTABLE_WORKFLOW_RESPONSE=') == (2 if contrary else 1)
    assert result['capture_receipt']['bytes'] == len(data)
    assert result['application'] == ('not_applied' if contrary else 'applied')
    if contrary:
        assert 'multiple bound' in result['error']
        assert not call(run, 'inspect')['current']['edits']
    assert len(launches(run.parent)) == 1


@pytest.mark.parametrize('boundary,recoverable', [('before-capture', False),
    ('after-eof-before-receipt', False), ('after-receipt', True), ('before-collection', True),
    ('after-collection', True)])
def test_owner_loss_is_not_controller_loss_or_permission_to_repeat(setup, boundary, recoverable):
    run, request = setup
    mode(run.parent, kind='edit')
    process, listener, connection, pid = held(run, request, boundary)
    try:
        os.kill(pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 1 and b'collection owner lost (exit -9)' in stderr
        assert owner(run)['lock_held'] is False
        result = agent(run, 'collect', code=0 if recoverable else 4)
        if recoverable:
            assert result['application'] == 'applied'
            assert len(call(run, 'inspect')['current']['edits']) == 1
        else:
            assert result['state'] == 'pending' and result['application'] == 'not_applied'
            assert 'unknown submission' in result['error'] or 'complete local capture unconfirmed' in result['error']
            agent(run, 'ask', dict(request, key='no-replay'), code=5)
            assert not call(run, 'inspect')['current']['edits']
        assert agent(run, 'ask', request, code=0 if recoverable else 4) == result
        expected = 0 if boundary == 'before-capture' else 1
        assert (len(launches(run.parent)) if (run.parent / 'runner-calls.jsonl').exists() else 0) == expected
    finally:
        connection.close()
        listener.close()


def test_controller_death_before_owner_fork_never_submits(setup):
    run, request = setup
    process, listener, connection, pid = held(run, request, 'before-owner-fork')
    assert pid == process.pid
    process.kill()
    process.communicate(timeout=15)
    connection.close()
    listener.close()
    assert not (run.parent / 'runner-calls.jsonl').exists()
    status = owner(run)
    assert not status['lock_held'] and not status['latest']['started']
    agent(run, 'collect', code=5)  # no exchange; no automatic resubmission
    assert agent(run, 'ask', request)['state'] == 'returned'
    assert len(launches(run.parent)) == 1


def test_owner_records_never_publish_unvalidated_declared_secret(setup, monkeypatch):
    run, request = setup
    secret = 'OWNER_PRIVATE_SECRET_123'
    monkeypatch.setenv('FAKE_DECLARED_SECRET', secret)
    request['key'] = secret
    agent(run, 'ask', request, code=5)
    assert not (run.parent / 'runner-calls.jsonl').exists()
    assert all(secret.encode() not in path.read_bytes() for path in (run / 'agent-owners').rglob('*.json'))
    request['key'] = 'one'
    result = agent(run, 'ask', request)
    assert '[REDACTED]' in open(result['log']).read()
    assert all(secret.encode() not in path.read_bytes() for path in (run / 'agent-owners').rglob('*.json'))


@pytest.mark.parametrize('target', ['agent-owner.json', 'intent.json'])
def test_malformed_owner_metadata_has_useful_diagnostic_without_replay(setup, target):
    run, request = setup
    agent(run, 'ask', request)
    record = owner(run)['latest']
    path = run / target if target == 'agent-owner.json' else run / 'agent-owners' / record['id'] / target
    path.write_text('[]')
    error = agent(run, 'owner', code=5)
    assert 'malformed collection owner' in error['error']
    assert agent(run, 'show')['state'] == 'returned'
    assert len(launches(run.parent)) == 1


def test_owner_loss_while_original_runner_is_live_retains_submission_uncertainty(setup):
    run, request = setup
    process, listener, connection = start_held(run, request)
    status = owner(run)
    record = run / 'agent-owners' / status['latest']['id']
    pid = json.loads((record / 'started.json').read_text())['pid']
    os.kill(pid, signal.SIGKILL)
    stdout, stderr = process.communicate(timeout=15)
    assert process.returncode == 5
    assert json.loads(stderr)['outcome'] == 'not_confirmed'
    assert 'collection owner lost (exit -9)' in json.loads(stderr)['error']
    assert owner(run)['lock_held'] is False
    try:
        # Original fake is still held at its socket barrier. Acquiring the lock
        # cannot authorize a second submission or certify its successful prefix.
        pending = agent(run, 'collect', code=4)
        assert pending['returncode'] is None and pending['response'] is None
        assert pending['trace']['invocation']['success'] is True
        assert 'complete local capture unconfirmed' in pending['error']
        agent(run, 'ask', dict(request, key='no-duplicate'), code=5)
        assert not call(run, 'inspect')['current']['edits']
        assert len(launches(run.parent)) == 1
    finally:
        finish_held(process, listener, connection)
    assert agent(run, 'collect', code=4)['response'] is None
