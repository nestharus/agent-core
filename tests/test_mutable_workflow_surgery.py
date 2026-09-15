"""ACR-537 outcome controls: real local fake subprocesses, no semantic agents.

Socket handshakes hold real work after its local effect and before its return;
no timing sleep is used to infer admission or settlement.
"""
import base64
from contextlib import contextmanager
import json
import socket
import subprocess
import sys

import pytest

from test_mutable_workflow import CLI, FIXTURES, call, calls, plan_file


def step(name, value='ordinary'):
    return dict(id=name, worker='local', input=value)


def edit_file(tmp_path, state, operations, name='amend', **overrides):
    edit = dict(run_id=state['run_id'], cursor=state['cursor'], actor='local-test-editor',
                reason='exercise authorized revised local work',
                effects='fake append-only local effects retained; repeated execution is safe here',
                operations=operations)
    edit.update(overrides)
    path = tmp_path / f'{name}.json'
    path.write_text(json.dumps(edit))
    return path


def amend(tmp_path, run, operations, code=3, state=None):
    state = state or call(run, 'inspect')['current']
    return call(run, 'amend', '--file', edit_file(tmp_path, state, operations), code=code)


def ready(tmp_path, modes=('ordinary', 'ordinary', 'ordinary')):
    run = tmp_path / 'run'
    state = call(run, 'start', '--file', plan_file(tmp_path, modes), '--max-steps', 0, code=3)
    return run, state


def test_composed_arbitrary_surgery_executes_new_trajectory(tmp_path):
    run, _ = ready(tmp_path, ['ordinary'] * 5)
    state = amend(tmp_path, run, [
        dict(op='replace', start='step-0', count=2, steps=[step('new-a'), step('new-b'), step('new-c')]),
        dict(op='insert', before='step-2', steps=[step('inserted')]),
        dict(op='remove', steps=['step-3']), dict(op='skip', steps=['step-4']),
        dict(op='policy', value={'basis': 'different-policy', 'obligations': ['new-a']}),
        dict(op='goto', step='new-b')])
    assert [s['id'] for s in state['steps']] == ['new-a', 'new-b', 'new-c', 'inserted', 'step-2', 'step-4']
    done = call(run, 'resume')
    assert calls(run) == ['new-b', 'new-c', 'inserted', 'step-2']
    assert done['policy'] == {'basis': 'different-policy', 'obligations': ['new-a']}
    assert done['nodes']['1']['disposition'] == 'removed'
    assert done['nodes']['5']['disposition'] == 'skipped'
    assert all(a['outcome'] == 'success' for a in done['attempts'])
    assert call(run, 'output', '--attempt', 1)['request']['policy'] == done['policy']


@pytest.mark.parametrize('operation', ['goto', 'return', 'retry'])
def test_reentry_is_new_attempt_and_does_not_rewrite_old_result(tmp_path, operation):
    run, _ = ready(tmp_path, ['ordinary'])
    done = call(run, 'resume')
    first = call(run, 'output', '--attempt', 1)
    amend(tmp_path, run, [dict(op=operation, step='step-0')])
    again = call(run, 'resume')
    second = call(run, 'output', '--attempt', 2)
    assert first == call(run, 'output', '--attempt', 1)
    assert first['request']['node_id'] == second['request']['node_id']
    assert second['request']['attempt_id'] != first['request']['attempt_id']
    assert second['request']['basis_cursor'] > done['cursor']
    assert len(again['attempts']) == 2 and calls(run) == ['step-0', 'step-0']


def test_remove_completed_abort_and_skip_are_not_execution_or_compensation(tmp_path):
    run, _ = ready(tmp_path)
    call(run, 'resume', '--max-steps', 1, code=3)
    original = call(run, 'output', '--attempt', 1)
    amend(tmp_path, run, [dict(op='remove', steps=['step-0']), dict(op='skip', steps=['step-1'])])
    aborted = amend(tmp_path, run, [dict(op='abort')], code=6)
    assert call(run, 'resume', code=6) == aborted
    assert original == call(run, 'output', '--attempt', 1)
    assert calls(run) == ['step-0']
    assert aborted['nodes']['1']['disposition'] == 'removed'
    assert aborted['nodes']['2']['disposition'] == 'skipped'
    assert len(aborted['attempts']) == 1
    # Structural edits alone do not restart an aborted workflow.
    amend(tmp_path, run, [dict(op='replace', start='step-2', count=1, steps=[step('restart')])], code=6)
    amend(tmp_path, run, [dict(op='goto', step='restart')])
    call(run, 'resume')
    assert calls(run) == ['step-0', 'restart']


def test_empty_replacement_then_append_new_work(tmp_path):
    run, _ = ready(tmp_path, ['ordinary'])
    emptied = amend(tmp_path, run, [dict(op='replace', start='step-0', count=1, steps=[])], code=0)
    assert emptied['attempts'] == [] and emptied['steps'] == []
    amend(tmp_path, run, [dict(op='insert', before=None, steps=[step('brand-new')])])
    call(run, 'resume')
    assert calls(run) == ['brand-new']


@pytest.mark.parametrize('bad', [
    dict(op='replace', start='step-0', count=99, steps=[]),
    dict(op='replace', start='step-0', count=True, steps=[]),
    dict(op='replace', start='step-0', count=1, steps='bad'),
    dict(op='insert', before='missing', steps=[step('x')]),
    dict(op='insert', before=None, steps=[step('step-1')]),
    dict(op='insert', before=None, steps=[dict(id='x', worker='ungranted', input=None)]),
    dict(op='goto', step='missing'), dict(op='cancel', attempt=999),
    dict(op='registry', value={}), dict(op='abort', unexpected=True),
])
def test_invalid_composition_rolls_back_every_operation(tmp_path, bad):
    run, state = ready(tmp_path)
    before = call(run, 'inspect')
    amend(tmp_path, run, [dict(op='policy', value='would-change'),
                         dict(op='remove', steps=['step-2']), bad], code=5)
    assert call(run, 'inspect') == before
    assert state['workers'] == before['current']['workers']
    assert not (run / 'calls.jsonl').exists()


@contextmanager
def held_worker(tmp_path, ignore_cancel=False, outcome='success'):
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen()
    server.settimeout(15)
    run = tmp_path / 'run'
    plan = dict(purpose='controlled local effects',
                workers={'local': [sys.executable, str(FIXTURES / 'controlled_worker.py')]},
                steps=[step('original', {'port': server.getsockname()[1], 'ignore_cancel': ignore_cancel, 'outcome': outcome}), step('tail')])
    path = tmp_path / 'controlled.json'
    path.write_text(json.dumps(plan))
    process = subprocess.Popen([sys.executable, str(CLI), 'start', str(run), '--file', str(path),
                                '--max-steps', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    connection = None
    try:
        connection, _ = server.accept()
        connection.settimeout(15)
        assert connection.recv(1024) == b'effect-written\n'
        yield run, process, connection
    finally:
        close_worker(process, connection, server)


def close_worker(process, connection, server):
    if connection is not None:
        connection.close()
    server.close()
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=15)


def finish(process, connection, codes=(3,)):
    connection.sendall(b'R')
    stdout, stderr = process.communicate(timeout=15)
    assert process.returncode in codes, (stdout, stderr)
    return json.loads(stdout)


def effects(run):
    return [json.loads(line) for line in (run / 'effects.jsonl').read_text().splitlines()]


@pytest.mark.parametrize('operation', ['replace', 'remove', 'skip', 'abort', 'goto', 'policy', 'retry', 'return'])
def test_inflight_amendment_retains_late_original_without_replacement_credit(tmp_path, operation):
    with held_worker(tmp_path) as (run, process, connection):
        check_inflight_amendment(tmp_path, operation, run, process, connection)


def check_inflight_amendment(tmp_path, operation, run, process, connection):
    admitted = call(run, 'output', '--attempt', 1)
    assert admitted['output'] is None
    ops = dict(
        replace=[dict(op='replace', start='original', count=1, steps=[step('original', 'replacement')])],
        remove=[dict(op='remove', steps=['original'])],
        skip=[dict(op='skip', steps=['original'])],
        abort=[dict(op='abort')], goto=[dict(op='goto', step='tail')],
        policy=[dict(op='policy', value={'basis': 'new'})],
        retry=[dict(op='retry', step='original')], **{'return': [dict(op='return', step='original')]})
    amended = amend(tmp_path, run, ops[operation], code=6 if operation == 'abort' else 3)
    assert len(effects(run)) == 1
    done = finish(process, connection, codes=(6,) if operation == 'abort' else (3,))
    original = call(run, 'output', '--attempt', 1)
    assert original['request'] == admitted['request']
    assert original['outcome'] == 'success' and original['credited'] is False
    assert original['cancellation'] == 'not_requested'
    assert done['position'] == amended['position'] and done['edits'] == amended['edits']
    assert base64.b64decode(original['output']['stdout_b64']) == (
        b'{"outcome": "success", "detail": "controlled local effect returned"}\n')
    assert base64.b64decode(original['output']['stderr_b64']) == b''
    if operation == 'replace':
        call(run, 'resume')
        replacement = call(run, 'output', '--attempt', 2)
        assert replacement['request']['step']['input'] == 'replacement'
        assert replacement['request']['node_id'] != original['request']['node_id']
        assert replacement['credited'] is True
        assert original == call(run, 'output', '--attempt', 1)
    if operation in ('retry', 'return', 'policy'):
        call(run, 'resume')
        repeated = call(run, 'output', '--attempt', 2)
        assert repeated['request']['node_id'] == original['request']['node_id']
        assert repeated['request']['attempt_id'] == 2 and repeated['credited'] is True
        assert repeated['request']['policy'] == amended['policy']
    assert effects(run)[0] == admitted['request']  # abort/remove did not undo effect


def test_future_insertion_keeps_running_credit_and_executes_future_work(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        amend(tmp_path, run, [dict(op='insert', before='tail', steps=[step('new')])])
        state = finish(process, connection)
        assert state['steps'][state['position']]['id'] == 'new'
        assert call(run, 'output', '--attempt', 1)['credited'] is True
        call(run, 'resume')
        assert [r['step']['id'] for r in effects(run)] == ['original', 'new', 'tail']


def test_cancel_request_confirmation_and_no_automatic_retry(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        # Amendment return is the committed request, not termination evidence.
        state = amend(tmp_path, run, [dict(op='cancel', attempt=1)])
        assert state['status'] == 'running'
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 7, (stdout, stderr)
        attempt = call(run, 'output', '--attempt', 1)
        assert attempt['cancellation'] == 'confirmed'
        assert attempt['outcome'] == 'cancelled' and attempt['output']['returncode'] == -15
        assert len(effects(run)) == 1
        call(run, 'resume', code=7)
        assert len(effects(run)) == 1
        kinds = [event['kind'] for event in call(run, 'inspect')['events']]
        assert 'amended' in kinds and 'cancellation_signal_sent' in kinds


def test_cancel_unavailable_after_return_and_atomic_invalid_cancel_composition(tmp_path):
    run, _ = ready(tmp_path, ['ordinary'])
    call(run, 'resume')
    before = call(run, 'output', '--attempt', 1)
    snapshot = call(run, 'inspect')
    amend(tmp_path, run, [dict(op='cancel', attempt=1), dict(op='goto', step='missing')], code=5)
    assert call(run, 'inspect') == snapshot
    assert call(run, 'output', '--attempt', 1) == before
    amend(tmp_path, run, [dict(op='cancel', attempt=1)], code=0)
    after = call(run, 'output', '--attempt', 1)
    assert after['cancellation'] == 'unavailable'
    assert after['output'] == before['output'] and after['request'] == before['request']


def test_cancel_superseded_worker_is_not_workflow_abort(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        amend(tmp_path, run, [dict(op='replace', start='original', count=1, steps=[step('replacement')]),
                             dict(op='cancel', attempt=1)])
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == 3, (stdout, stderr)
        assert call(run, 'output', '--attempt', 1)['credited'] is False
        assert call(run, 'output', '--attempt', 1)['cancellation'] == 'confirmed'
        call(run, 'resume')
        assert [r['step']['id'] for r in effects(run)] == ['original', 'replacement', 'tail']


def test_completion_first_rejects_stale_edit_then_accepts_rebased_intent(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        old = call(run, 'inspect')['current']
        finished = finish(process, connection)
        before = call(run, 'output', '--attempt', 1)
        ops = [dict(op='replace', start='tail', count=1, steps=[step('replacement')])]
        error = amend(tmp_path, run, ops, code=5, state=old)
        assert 'stale' in error['error'] and call(run, 'inspect')['current'] == finished
        amend(tmp_path, run, ops)
        call(run, 'resume')
        assert call(run, 'output', '--attempt', 1) == before
        assert [r['step']['id'] for r in effects(run)] == ['original', 'replacement']


def test_real_completion_edit_race_has_one_serialized_outcome(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        check_completion_edit_race(tmp_path, run, process, connection)


def check_completion_edit_race(tmp_path, run, process, connection):
    state = call(run, 'inspect')['current']
    path = edit_file(tmp_path, state, [dict(op='replace', start='original', count=1,
                                         steps=[step('replacement')])])
    editor = subprocess.Popen([sys.executable, str(CLI), 'amend', str(run), '--file', str(path)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finish(process, connection)
    stdout, stderr = editor.communicate(timeout=15)
    assert editor.returncode in (3, 5), (stdout, stderr)
    current = call(run, 'inspect')['current']
    attempt = call(run, 'output', '--attempt', 1)
    if editor.returncode == 3:
        assert len(current['edits']) == 1 and attempt['credited'] is False
        assert current['steps'][current['position']]['id'] == 'replacement'
    else:
        assert current['edits'] == [] and attempt['credited'] is True
        assert any(word in json.loads(stderr)['error'] for word in ('stale', 'busy'))
    assert len(effects(run)) == 1 and attempt['outcome'] == 'success'
    events = call(run, 'inspect')['events']
    assert sum(event['kind'] == 'attempt_returned' for event in events) == 1


def test_competing_editors_rebase_loser_without_lost_edits(tmp_path):
    run, state = ready(tmp_path, ['ordinary'])
    edits = [edit_file(tmp_path, state, [dict(op='insert', before=None, steps=[step(name)])], name)
             for name in ('a', 'b')]
    editors = [subprocess.Popen([sys.executable, str(CLI), 'amend', str(run), '--file', str(path)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE) for path in edits]
    results = [editor.communicate(timeout=15) for editor in editors]
    assert sorted(editor.returncode for editor in editors) == [3, 5], results
    loser = next(i for i, editor in enumerate(editors) if editor.returncode == 5)
    current = call(run, 'inspect')['current']
    assert len(current['edits']) == 1
    losing = json.loads(edits[loser].read_text())
    amend(tmp_path, run, losing['operations'])
    done = call(run, 'resume')
    assert len(done['edits']) == 2 and sorted(calls(run)) == ['a', 'b', 'step-0']


def test_lossless_binary_output_full_bytes(tmp_path):
    run = tmp_path / 'run'
    plan = dict(purpose='full byte fidelity', workers={'local': [sys.executable,
                str(FIXTURES / 'controlled_worker.py')]}, steps=[step('binary', 'binary')])
    path = tmp_path / 'binary.json'
    path.write_text(json.dumps(plan))
    call(run, 'start', '--file', path, code=4)
    before = call(run, 'output', '--attempt', 1)
    assert base64.b64decode(before['output']['stdout_b64']) == bytes(range(256)) * 8
    assert base64.b64decode(before['output']['stderr_b64']) == bytes(reversed(range(256))) * 9
    amend(tmp_path, run, [dict(op='remove', steps=['binary'])], code=0)
    assert call(run, 'output', '--attempt', 1) == before


def test_collector_loss_makes_cancellation_unavailable_without_fabricating_output(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        admitted = call(run, 'output', '--attempt', 1)
        process.kill()
        connection.sendall(b'R')
        process.communicate(timeout=15)
        state = call(run, 'resume', code=4)
        assert state['status'] == 'ambiguous'
        orphan = call(run, 'output', '--attempt', 1)
        assert orphan['orphaned'] is True and orphan['output'] is None
        amend(tmp_path, run, [dict(op='cancel', attempt=1)], code=4)
        orphan = call(run, 'output', '--attempt', 1)
        assert orphan['cancellation'] == 'unavailable' and orphan['outcome'] == 'running'
        assert orphan['request'] == admitted['request']
        assert len(effects(run)) == 1
        # Explicit effect-reconciled new intent, not automatic rerun.
        amend(tmp_path, run, [dict(op='retry', step='original')])
        call(run, 'resume')
        assert call(run, 'output', '--attempt', 1) == orphan
        assert [r['attempt_id'] for r in effects(run)] == [1, 2, 3]


def test_v1_storage_fails_explicitly_without_relabeling_history(tmp_path):
    import sqlite3
    run, _ = ready(tmp_path)
    with sqlite3.connect(run / 'state.sqlite3') as db:
        state = json.loads(db.execute('SELECT body FROM state').fetchone()[0])
        del state['version']
        db.execute('UPDATE state SET body=?', (json.dumps(state),))
    assert 'unsupported run version' in call(run, 'resume', code=5)['error']
    assert not (run / 'calls.jsonl').exists()


def test_removing_or_replacing_past_work_does_not_restart_exhausted_traversal(tmp_path):
    run, _ = ready(tmp_path)
    call(run, 'resume')
    original = [call(run, 'output', '--attempt', i) for i in (1, 2, 3)]
    amended = amend(tmp_path, run, [dict(op='remove', steps=['step-0']),
                                  dict(op='replace', start='step-1', count=1,
                                       steps=[step('new-past')])], code=0)
    assert amended['position'] == len(amended['steps'])
    call(run, 'resume')
    assert calls(run) == ['step-0', 'step-1', 'step-2']
    assert original == [call(run, 'output', '--attempt', i) for i in (1, 2, 3)]
    amend(tmp_path, run, [dict(op='goto', step='new-past')])
    call(run, 'resume')
    assert calls(run) == ['step-0', 'step-1', 'step-2', 'new-past', 'step-2']


def test_requested_cancellation_can_return_naturally_without_confirmation(tmp_path):
    with held_worker(tmp_path, ignore_cancel=True) as (run, process, connection):
        amend(tmp_path, run, [dict(op='cancel', attempt=1)])
        assert connection.recv(1024) == b'cancel-observed\n'
        requested = call(run, 'output', '--attempt', 1)
        assert requested['cancellation'] == 'requested' and requested['output'] is None
        finish(process, connection)
        returned = call(run, 'output', '--attempt', 1)
        assert returned['cancellation'] == 'unavailable'
        assert returned['outcome'] == 'success' and returned['credited'] is True
        assert returned['request'] == requested['request']
        assert len(effects(run)) == 1


def test_signal_without_collector_return_is_not_confirmation(tmp_path):
    with held_worker(tmp_path, ignore_cancel=True) as (run, process, connection):
        amend(tmp_path, run, [dict(op='cancel', attempt=1)])
        assert connection.recv(1024) == b'cancel-observed\n'
        process.kill()
        connection.sendall(b'R')
        process.communicate(timeout=15)
        call(run, 'resume', code=4)
        missing = call(run, 'output', '--attempt', 1)
        assert missing['cancellation'] == 'unavailable'
        assert missing['output'] is None and missing['orphaned'] is True
        assert len(effects(run)) == 1


def test_policy_text_does_not_change_granted_programs(tmp_path):
    run, initial = ready(tmp_path, ['ordinary'])
    state = amend(tmp_path, run, [dict(op='policy', value={'workers': {'local': ['/ungranted']},
                                                       'credentials': 'not-a-grant'})])
    assert state['workers'] == initial['workers']
    call(run, 'resume')
    assert calls(run) == ['step-0']
    output = call(run, 'output', '--attempt', 1)
    assert output['request']['policy'] == state['policy']
    assert output['outcome'] == 'success'


@pytest.mark.parametrize('outcome, classified', [('failure', 'failure'), ('invalid', 'ambiguous')])
def test_unfavorable_late_return_is_evidence_not_replacement_settlement(tmp_path, outcome, classified):
    with held_worker(tmp_path, outcome=outcome) as (run, process, connection):
        amended = amend(tmp_path, run, [dict(op='replace', start='original', count=1,
                                            steps=[step('replacement')])])
        finished = finish(process, connection)
        late = call(run, 'output', '--attempt', 1)
        assert late['outcome'] == classified and late['credited'] is False
        assert finished['position'] == amended['position'] and finished['status'] == 'ready'
        expected = json.dumps({'outcome': outcome, 'detail': 'controlled local effect returned'}) + '\n'
        assert base64.b64decode(late['output']['stdout_b64']) == expected.encode()
        call(run, 'resume')
        assert call(run, 'output', '--attempt', 1) == late
        assert [r['step']['id'] for r in effects(run)] == ['original', 'replacement', 'tail']
