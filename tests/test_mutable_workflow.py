"""CLI behavior checks against ACR-536's filed outcomes and root decisions.

Fake processes only. These assertions do not measure agent efficacy.
"""
import base64
import fcntl
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/mutable-workflow/cli.py'
FIXTURES = ROOT / 'tests/fixtures/mutable_workflow'


def call(run, command, *args, code=0):
    result = subprocess.run([sys.executable, str(CLI), command, str(run), *map(str, args)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == code, (result.stdout, result.stderr)
    return json.loads(result.stderr if code == 5 else result.stdout)


def plan_file(tmp_path, modes):
    plan = dict(purpose='Exercise local fake work',
                workers={'local': [sys.executable, str(FIXTURES / 'worker.py')]},
                steps=[dict(id=f'step-{i}', worker='local', input=mode)
                       for i, mode in enumerate(modes)])
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(plan))
    return path


def calls(run):
    return [json.loads(line) for line in (run / 'calls.jsonl').read_text().splitlines()]


def response(tmp_path, state, **overrides):
    edit = dict(run_id=state['run_id'], cursor=state['cursor'],
                blocked_step=state['steps'][state['position']]['id'], actor='fake',
                reason='caller-authorized local continuation',
                insert=[dict(id='inserted', worker='local', input='ordinary')])
    edit.update(overrides)
    path = tmp_path / 'response.json'
    path.write_text(json.dumps(edit))
    return path


def test_failure_judgment_insert_restart_and_inspect(tmp_path):
    run = tmp_path / 'run'
    plan = plan_file(tmp_path, ['ordinary', 'failure', 'finish'])
    failed = call(run, 'start', '--file', plan, code=1)
    assert failed['status'] == 'failure'
    prior = call(run, 'output', '--attempt', 1)
    failure = call(run, 'output', '--attempt', 2)
    view = call(run, 'inspect')
    judge = subprocess.run([sys.executable, str(FIXTURES / 'judge.py')],
                           input=json.dumps(dict(current=view['current'], output=failure)),
                           capture_output=True, text=True, check=True)
    edit = tmp_path / 'edit.json'
    edit.write_text(judge.stdout)
    amended = call(run, 'judge', '--file', edit, code=3)
    assert amended['steps'][2]['id'] == 'unplanned-recovery'
    assert 'unplanned-recovery' not in [s['id'] for s in json.loads(plan.read_text())['steps']]
    # New CLI process after durable edit, then another after durable worker completion.
    paused = call(run, 'resume', '--max-steps', 1, code=3)
    assert paused['position'] == 3
    done = call(run, 'resume')
    assert done['status'] == 'success'
    assert calls(run) == ['step-0', 'step-1', 'unplanned-recovery', 'step-2']
    assert call(run, 'output', '--attempt', 1) == prior
    assert call(run, 'output', '--attempt', 2) == failure
    assert done['attempts'][1]['outcome'] == 'failure'
    incremental = call(run, 'inspect', '--since', view['cursor'])
    assert incremental['events'][0]['kind'] == 'recovery_inserted'
    assert [e['cursor'] for e in incremental['events']] == list(range(view['cursor'] + 1, done['cursor'] + 1))
    assert call(run, 'inspect', '--since', done['cursor'])['events'] == []
    assert call(run, 'resume') == done
    assert calls(run).count('unplanned-recovery') == 1


def test_ordinary_needs_no_judgment_and_boundary_resume(tmp_path):
    run = tmp_path / 'run'
    ready = call(run, 'start', '--file', plan_file(tmp_path, ['ordinary', 'ordinary']),
                 '--max-steps', 1, code=3)
    assert ready['position'] == 1
    done = call(run, 'resume')
    assert done['edits'] == []
    assert calls(run) == ['step-0', 'step-1']


def test_explicit_unresolved_judgment(tmp_path):
    run = tmp_path / 'run'
    state = call(run, 'start', '--file', plan_file(tmp_path, ['judgment']), code=2)
    assert state['status'] == 'judgment'
    assert call(run, 'resume', code=2) == state
    call(run, 'judge', '--file', response(tmp_path, state), code=3)
    assert call(run, 'resume')['status'] == 'success'
    assert calls(run) == ['step-0', 'inserted']


@pytest.mark.parametrize('mode', ['empty', 'bad-json'])
def test_zero_exit_not_substantive_success(tmp_path, mode):
    run = tmp_path / 'run'
    state = call(run, 'start', '--file', plan_file(tmp_path, [mode]), code=4)
    assert state['status'] == 'ambiguous'
    output = call(run, 'output', '--attempt', 1)
    assert output['output']['returncode'] == 0
    call(run, 'judge', '--file', response(tmp_path, state), code=5)
    assert call(run, 'resume', code=4) == state
    assert calls(run) == ['step-0']


def test_nonzero_retains_raw_failure_evidence(tmp_path):
    run = tmp_path / 'run'
    call(run, 'start', '--file', plan_file(tmp_path, ['nonzero']), code=1)
    output = call(run, 'output', '--attempt', 1)['output']
    assert output['returncode'] == 7
    assert b'failure stderr' in base64.b64decode(output['stderr_b64'])
    assert b'success' in base64.b64decode(output['stdout_b64'])
    assert output['result']['outcome'] == 'failure'


@pytest.mark.parametrize('override', [dict(run_id='foreign'), dict(cursor=0),
    dict(blocked_step='other'), dict(insert=[dict(id='step-0', worker='local', input='ordinary')]),
    dict(insert=[dict(id='new', worker='unauthorized', input='ordinary')]), dict(insert=[])])
def test_invalid_edit_is_atomic(tmp_path, override):
    run = tmp_path / 'run'
    state = call(run, 'start', '--file', plan_file(tmp_path, ['failure']), code=1)
    before = call(run, 'inspect')
    call(run, 'judge', '--file', response(tmp_path, state, **override), code=5)
    assert call(run, 'inspect') == before


def test_replayed_edit_rejected(tmp_path):
    run = tmp_path / 'run'
    state = call(run, 'start', '--file', plan_file(tmp_path, ['failure']), code=1)
    path = response(tmp_path, state)
    call(run, 'judge', '--file', path, code=3)
    before = call(run, 'inspect')
    call(run, 'judge', '--file', path, code=5)
    assert call(run, 'inspect') == before


def test_killed_executor_is_ambiguous_not_replayed(tmp_path):
    run = tmp_path / 'run'
    plan = plan_file(tmp_path, ['ordinary', 'kill-executor'])
    result = subprocess.run([sys.executable, str(CLI), 'start', str(run), '--file', str(plan)],
                            capture_output=True, check=False)
    assert result.returncode == -9
    assert call(run, 'inspect')['current']['status'] == 'running'
    state = call(run, 'resume', code=4)
    assert state['status'] == 'ambiguous'
    assert call(run, 'output', '--attempt', 1)['outcome'] == 'success'
    uncertain = call(run, 'output', '--attempt', 2)
    assert uncertain['outcome'] == 'running' and uncertain['output'] is None
    assert call(run, 'resume', code=4) == state
    assert calls(run) == ['step-0', 'step-1']


def test_busy_writer_and_invalid_inspection(tmp_path):
    run = tmp_path / 'run'
    call(run, 'start', '--file', plan_file(tmp_path, ['ordinary']), '--max-steps', 0, code=3)
    with (run / 'writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert 'busy' in call(run, 'resume', code=5)['error']
        assert call(run, 'inspect')['current']['status'] == 'ready'
    call(run, 'inspect', '--since', -1, code=5)
    call(run, 'inspect', '--since', 1000, code=5)
    call(run, 'output', '--attempt', 10, code=5)
    assert call(run, 'resume')['status'] == 'success'


def test_missing_worker_is_failure_not_silent_success(tmp_path):
    run = tmp_path / 'run'
    plan = plan_file(tmp_path, ['ordinary'])
    data = json.loads(plan.read_text())
    data['workers']['local'] = ['/nonexistent/acr536-worker']
    plan.write_text(json.dumps(data))
    call(run, 'start', '--file', plan, code=1)
    assert 'launch failed' in call(run, 'output', '--attempt', 1)['output']['result']['detail']


@pytest.mark.parametrize('patch', [dict(purpose=''), dict(steps=[]),
    dict(workers={'local': ['relative-executable']}),
    dict(steps=[dict(id='x', worker='missing', input=None)])])
def test_invalid_plan_executes_nothing(tmp_path, patch):
    run = tmp_path / 'run'
    path = plan_file(tmp_path, ['ordinary'])
    plan = json.loads(path.read_text())
    plan.update(patch)
    path.write_text(json.dumps(plan))
    call(run, 'start', '--file', path, code=5)
    assert not run.exists()


def test_start_never_overwrites_and_resume_uses_persisted_plan(tmp_path):
    run = tmp_path / 'run'
    path = plan_file(tmp_path, ['ordinary'])
    call(run, 'start', '--file', path, '--max-steps', 0, code=3)
    before = call(run, 'inspect')
    call(run, 'start', '--file', path, code=5)
    assert call(run, 'inspect') == before
    path.unlink()
    assert call(run, 'resume')['status'] == 'success'
    assert calls(run) == ['step-0']


@pytest.mark.parametrize('name', ['run%20x', 'run?x', 'run#x'])
def test_literal_run_path_lifecycle(tmp_path, name):
    run = tmp_path / name
    failed = call(run, 'start', '--file', plan_file(tmp_path, ['failure']), code=1)
    before = call(run, 'inspect')
    assert before['current'] == failed
    output = call(run, 'output', '--attempt', 1)
    assert output['request']['run_id'] == failed['run_id']
    assert output['outcome'] == 'failure'
    call(run, 'judge', '--file', response(tmp_path, failed), code=3)
    ready = call(run, 'inspect')
    with (run / 'writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert 'busy' in call(run, 'resume', code=5)['error']
        assert call(run, 'inspect') == ready
    done = call(run, 'resume')
    assert done['run_id'] == failed['run_id']
    assert done['status'] == 'success'
    assert calls(run) == ['step-0', 'inserted']
    assert call(run, 'output', '--attempt', 1) == output
    since = call(run, 'inspect', '--since', before['cursor'])
    assert [event['kind'] for event in since['events']] == [
        'recovery_inserted', 'attempt_started', 'attempt_returned']
    assert since['current'] == done
    assert call(run, 'resume') == done
    assert calls(run) == ['step-0', 'inserted']


def test_literal_run_path_does_not_execute_percent_decoded_sibling(tmp_path):
    sibling = tmp_path / 'run x'
    plan = plan_file(tmp_path, ['ordinary'])
    call(sibling, 'start', '--file', plan, '--max-steps', 0, code=3)
    before = call(sibling, 'inspect')
    run = tmp_path / 'run%20x'
    own = call(run, 'start', '--file', plan)
    # The other run's durable history and work must remain untouched.
    assert call(sibling, 'inspect') == before
    assert not (sibling / 'calls.jsonl').exists()
    assert own['run_id'] != before['current']['run_id']
    assert own['status'] == 'success'
    assert call(run, 'inspect')['current'] == own
    assert call(run, 'output', '--attempt', 1)['request']['run_id'] == own['run_id']
    assert calls(run) == ['step-0']
    with (sibling / 'writer.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert call(run, 'resume') == own
    assert call(sibling, 'resume')['run_id'] == before['current']['run_id']
    assert calls(sibling) == ['step-0']
    assert call(run, 'inspect')['current'] == own


@pytest.mark.parametrize('name', ['run%20x', 'run?x', 'run#x'])
def test_literal_run_path_missing_database_is_not_created_or_aliased(tmp_path, name):
    sibling = tmp_path / 'run x'
    call(sibling, 'start', '--file', plan_file(tmp_path, ['ordinary']),
         '--max-steps', 0, code=3)
    before = call(sibling, 'inspect')
    run = tmp_path / name
    run.mkdir()
    assert call(run, 'inspect', code=5)['outcome'] == 'not_confirmed'
    assert call(run, 'resume', code=5)['outcome'] == 'not_confirmed'
    assert not (run / 'state.sqlite3').exists()
    assert not (run / 'calls.jsonl').exists()
    assert not (tmp_path / 'run').exists()
    assert call(sibling, 'inspect') == before
