"""ACR-539 decision-grounded fault/recovery controls: fake effects, no models."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from test_mutable_workflow import call, plan_file, FIXTURES
from test_mutable_workflow_surgery import amend, edit_file
from test_mutable_workflow_runner import agent, setup, mode, launches

DRIVER = FIXTURES / 'fault_driver.py'


def recoverable_plan(tmp_path, mode='ordinary', contract=True):
    value = dict(purpose='recover bounded atomic fake effects',
                 workers={'local': [sys.executable, str(FIXTURES / 'recoverable_worker.py')]},
                 steps=[dict(id='one', worker='local', input=mode)])
    if contract:
        value['recovery'] = {'local': 'deduplicated-attempt-v1'}
    path = tmp_path / 'recoverable.json'
    path.write_text(json.dumps(value))
    return path


def fault(boundary, command, run, source):
    result = subprocess.run([sys.executable, str(DRIVER), boundary, command, str(run), str(source)],
                            capture_output=True, text=True)
    assert result.returncode == 90, (result.stdout, result.stderr)


def effect_count(run):
    with sqlite3.connect(run / 'effects.sqlite3') as db:
        return db.execute('SELECT count(*) FROM effects').fetchone()[0]


def test_effect_before_ack_safe_redelivery_is_same_request_not_new_execution(tmp_path):
    run = tmp_path / 'run'
    result = subprocess.run([sys.executable, str(FIXTURES.parents[2] / 'tools/mutable-workflow/cli.py'),
                             'start', str(run), '--file', str(recoverable_plan(tmp_path, 'kill-after-effect'))],
                            capture_output=True)
    assert result.returncode == -9
    assert effect_count(run) == 1
    call(run, 'resume', code=4)
    original = call(run, 'output', '--attempt', 1)
    observed = call(run, 'recover', '--attempt', 1, code=4)
    assert observed['attempt']['recovery_observations'][-1]['disposition'] == 'retry_safe'
    assert observed['attempt']['output'] is None and effect_count(run) == 1
    recovered = call(run, 'recover', '--attempt', 1, '--redeliver')
    assert recovered['current']['status'] == 'success'
    assert recovered['attempt']['request'] == original['request']
    assert recovered['attempt']['orphaned'] is True
    assert effect_count(run) == 1
    deliveries = [json.loads(line) for line in (run / 'deliveries.jsonl').read_text().splitlines()]
    assert deliveries == [original['request'], original['request']]
    before = call(run, 'inspect')
    call(run, 'recover', '--attempt', 1, '--redeliver')
    assert call(run, 'inspect') == before and effect_count(run) == 1
    amend(tmp_path, run, [dict(op='return', step='one')])
    # The explicit new execution intentionally has a new effect identity.
    result = subprocess.run([sys.executable, str(FIXTURES.parents[2] / 'tools/mutable-workflow/cli.py'),
                             'resume', str(run)], capture_output=True)
    assert result.returncode == -9
    call(run, 'recover', '--attempt', 2, '--redeliver')
    assert effect_count(run) == 2
    assert call(run, 'output', '--attempt', 1) == recovered['attempt']


@pytest.mark.parametrize('contract,mode_value', [(False, 'ordinary'), (True, 'unknown')])
def test_unknown_effect_requires_reconciliation_not_caller_text(tmp_path, contract, mode_value):
    run = tmp_path / 'run'
    path = recoverable_plan(tmp_path, mode_value, contract)
    fault('after-result-receipt', 'start', run, path)
    assert effect_count(run) == 1
    error = call(run, 'recover', '--attempt', 1, '--redeliver', code=5)
    assert 'reconcile with effect owner' in error['error']
    assert call(run, 'output', '--attempt', 1)['output'] is None
    call(run, 'resume', code=4)
    assert effect_count(run) == 1


@pytest.mark.parametrize('boundary', ['before-attempt_started', 'after-attempt_started',
    'before-dispatch', 'after-result-receipt', 'before-attempt_returned', 'during-attempt_returned', 'after-attempt_returned'])
def test_worker_fault_boundaries_have_recoverable_action(tmp_path, boundary):
    run = tmp_path / 'run'
    fault(boundary, 'start', run, recoverable_plan(tmp_path))
    state = call(run, 'inspect')['current']
    if not state['attempts']:
        assert call(run, 'resume')['status'] == 'success'
    else:
        assert call(run, 'recover', '--attempt', 1, '--redeliver')['current']['status'] == 'success'
    assert effect_count(run) == 1
    assert len(call(run, 'inspect')['current']['attempts']) == 1
    assert len([event for event in call(run, 'inspect')['events'] if event['kind'] == 'attempt_returned']) == 1


@pytest.mark.parametrize('boundary', ['before-amended', 'after-amended'])
def test_edit_commit_interruption_and_duplicate_command(tmp_path, boundary):
    run = tmp_path / 'run'
    state = call(run, 'start', '--file', plan_file(tmp_path, ['ordinary']), '--max-steps', 0, code=3)
    path = edit_file(tmp_path, state, [dict(op='policy', value='new')])
    fault(boundary, 'amend', run, path)
    if boundary == 'before-amended':
        assert call(run, 'inspect')['current'] == state
        call(run, 'amend', '--file', path, code=3)
    before = call(run, 'inspect')
    call(run, 'amend', '--file', path, code=5)
    assert call(run, 'inspect') == before
    assert call(run, 'resume')['policy'] == 'new'


@pytest.mark.parametrize('sql', ['DELETE FROM events WHERE cursor=2', 'DELETE FROM attempts',
    "UPDATE attempts SET body=json_set(body,'$.outcome','failure')",
    "UPDATE state SET body=json_set(body,'$.position',0)",
    "UPDATE events SET body=json_set(body,'$.cursor',99) WHERE cursor=2"])
def test_missing_or_inconsistent_history_is_not_success(tmp_path, sql):
    run = tmp_path / 'run'
    call(run, 'start', '--file', plan_file(tmp_path, ['ordinary']))
    with sqlite3.connect(run / 'state.sqlite3') as db:
        db.execute(sql)
    for command, args in [('resume', []), ('inspect', []), ('output', ['--attempt', 1])]:
        error = call(run, command, *args, code=5)
        assert 'inconsistent durable history' in error['error']


def agent_fault(setup, boundary, **values):
    run, request = setup
    mode(run.parent, **values)
    source = run.parent / 'fault-request.json'
    source.write_text(json.dumps(request))
    fault(boundary, 'ask', run, source)
    return run, request


def test_capture_receipt_recovers_before_exchange_record_and_keeps_session(setup):
    run, request = agent_fault(setup, 'before-capture-record', kind='edit')
    pending = agent(run, 'show', code=4)
    assert pending['returncode'] is None
    assert Path(pending['log'] + '.capture.json').exists()
    recovered = agent(run, 'collect')
    assert recovered['application'] == 'applied' and recovered['capture_receipt']['returncode'] == 0
    before = call(run, 'inspect')
    assert agent(run, 'collect') == recovered
    assert call(run, 'inspect') == before
    mode(run.parent, lookup='session-not-found')
    next_exchange = agent(run, 'ask', dict(request, key='new-question'))
    assert next_exchange['continuity'] == 'fresh_fallback'
    assert len(launches(run.parent)) == 2


@pytest.mark.parametrize('damage', ['truncate', 'missing', 'corrupt'])
def test_capture_receipt_does_not_certify_damaged_prefix(setup, damage):
    run, _ = agent_fault(setup, 'before-capture-record', kind='edit')
    pending = agent(run, 'show', code=4)
    log = Path(pending['log'])
    receipt = Path(pending['log'] + '.capture.json')
    if damage == 'truncate':
        log.write_bytes(log.read_bytes()[:-1])
    elif damage == 'missing':
        receipt.unlink()
    else:
        receipt.write_text('{}')
    before = call(run, 'inspect')
    retained = agent(run, 'collect', code=4)
    assert retained['application'] == 'not_applied' and retained['response'] is None
    assert call(run, 'inspect') == before
    assert len(launches(run.parent)) == 1


def test_joint_application_commit_survives_loss_and_duplicate_collection(setup):
    run, request = agent_fault(setup, 'after-amended', kind='edit')
    before = call(run, 'inspect')
    returned = agent(run, 'collect')
    assert returned['application'] == 'applied'
    assert agent(run, 'ask', request) == returned
    assert call(run, 'inspect') == before and len(launches(run.parent)) == 1


@pytest.mark.parametrize('boundary,state', [('after-prepared', 'not_submitted'),
                                           ('before-agent-dispatch', 'pending')])
def test_preparation_and_uncertain_submission_are_different(setup, boundary, state):
    run, request = agent_fault(setup, boundary)
    returned = agent(run, 'collect', code=4)
    assert returned['state'] == state
    assert not (run.parent / 'runner-calls.jsonl').exists()
    if state == 'pending':
        agent(run, 'ask', dict(request, key='next'), code=5)
    else:
        assert agent(run, 'ask', dict(request, key='next'))['state'] == 'returned'


@pytest.mark.parametrize('boundary', ['before-started', 'after-started'])
def test_initialization_interruption_never_resets(tmp_path, boundary):
    run = tmp_path / 'run'
    path = recoverable_plan(tmp_path)
    fault(boundary, 'start', run, path)
    if boundary == 'before-started':
        assert 'initialization incomplete' in call(run, 'resume', code=5)['error']
        call(run, 'start', '--file', path, code=5)
        assert not (run / 'effects.sqlite3').exists()
    else:
        assert call(run, 'resume')['status'] == 'success'
        assert effect_count(run) == 1


def test_duplicate_result_receipt_is_idempotent_but_conflict_is_rejected(tmp_path):
    sys.path.insert(0, str(FIXTURES.parents[2] / 'tools/mutable-workflow'))
    import runtime
    run = tmp_path / 'run'
    call(run, 'start', '--file', plan_file(tmp_path, ['failure']), code=1)
    original = call(run, 'output', '--attempt', 1)
    before = call(run, 'inspect')
    with runtime.connect(run) as db, runtime.exclusive(run):
        runtime.finish_attempt(db, runtime.load(db), runtime.read_attempt(db, 1), original['output'], False)
        with pytest.raises(runtime.ContractError, match='conflicting duplicate'):
            runtime.finish_attempt(db, runtime.load(db), runtime.read_attempt(db, 1),
                                   runtime.captured(0, b'{"outcome":"success","detail":"contrary"}', b''), False)
    assert call(run, 'inspect') == before
    assert call(run, 'output', '--attempt', 1) == original


def test_contended_edit_rejection_then_explicit_retry_keeps_worker_credit(tmp_path):
    import fcntl
    from test_mutable_workflow_surgery import held_worker, finish, step
    with held_worker(tmp_path) as (run, process, connection):
        current = call(run, 'inspect')['current']
        path = edit_file(tmp_path, current, [dict(op='insert', before='tail', steps=[step('new')])])
        with (run / 'writer.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            assert 'busy' in call(run, 'amend', '--file', path, code=5)['error']
            assert call(run, 'inspect')['current'] == current
        # No other cancellation writer is eligible; worker remains at its socket barrier.
        call(run, 'amend', '--file', path, code=3)
        state = finish(process, connection)
        assert state['steps'][state['position']]['id'] == 'new'
        assert call(run, 'output', '--attempt', 1)['credited'] is True
        assert call(run, 'resume')['status'] == 'success'


@pytest.mark.parametrize('sql', ['DELETE FROM agent_exchanges', 'DROP TABLE agent_exchanges',
                                'DELETE FROM agent_history', 'DROP TABLE agent_history'])
def test_missing_agent_history_does_not_reset_conversation(setup, sql):
    run, request = setup
    agent(run, 'ask', request)
    with sqlite3.connect(run / 'state.sqlite3') as db:
        db.execute(sql)
    agent(run, 'show', code=5)
    agent(run, 'ask', dict(request, key='next'), code=5)
    assert len(launches(run.parent)) == 1



def test_redelivery_while_original_worker_remains_in_flight(tmp_path):
    import socket
    from test_mutable_workflow import CLI
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        server.listen()
        server.settimeout(15)
        run = tmp_path / 'run'
        path = recoverable_plan(tmp_path, {'port': server.getsockname()[1]})
        process = subprocess.Popen([sys.executable, str(CLI), 'start', str(run), '--file', str(path)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        connection, _ = server.accept()
        connection.settimeout(15)
        try:
            assert connection.recv(1024) == b'effect-written\n'
            process.kill()
            process.wait(timeout=15)
            # Original fake is still held, with its own effect/result committed.
            result = call(run, 'recover', '--attempt', 1, '--redeliver')
            assert result['attempt']['orphaned'] is True
            assert result['attempt']['cancellation'] == 'not_requested'
            assert result['current']['status'] == 'success'
            assert effect_count(run) == 1
        finally:
            connection.sendall(b'R')
            connection.close()
            process.communicate(timeout=15)
