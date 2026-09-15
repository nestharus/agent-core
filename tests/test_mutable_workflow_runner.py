"""ACR-538 acceptance through the real adapter subprocess/parsing boundary.

Only the explicitly injected Python fixture executable runs, never agents.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from test_mutable_workflow import call, plan_file

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / 'tools/mutable-workflow/agent_cli.py'
FAKE = ROOT / 'tests/fixtures/mutable_workflow_runner/runner.py'


def agent(run, command, request=None, key='one', code=0):
    argv = [sys.executable, str(AGENT), command, str(run)]
    if request is not None:
        path = run.parent / 'request.json'
        path.write_text(json.dumps(request))
        argv += ['--file', str(path)]
    else:
        argv += ['--key', key]
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert result.returncode == code, (result.stdout, result.stderr)
    return json.loads(result.stderr if code == 5 else result.stdout)


@pytest.fixture
def setup(tmp_path):
    run = tmp_path / 'run'
    call(run, 'start', '--file', plan_file(tmp_path, ['judgment']), code=2)
    contract = tmp_path / 'contract.yaml'
    contract.write_text('schema: operator-contract-v1\nsecrets: [FAKE_DECLARED_SECRET]\n')
    config = dict(runner=[sys.executable, str(FAKE)], model='fixture-model', project=str(tmp_path),
                  contract=str(contract), authority=dict(owner='test-root', access='local fake run and evidence',
                  effects='registered local fake workers only', delegation='propose registered investigation workers',
                  apply_edits=True))
    request = dict(key='one', question='Investigate the judgment boundary', answer=None, config=config)
    mode(tmp_path)
    return run, request


def mode(root, **values):
    (root / 'fake-mode.json').write_text(json.dumps(values))


def launches(root):
    rows = [json.loads(row) for row in (root / 'runner-calls.jsonl').read_text().splitlines()]
    return [row for row in rows if row[0] not in ('trace', 'session')]


def test_fresh_then_accepted_same_session_with_current_changes(setup):
    run, request = setup
    first = agent(run, 'ask', request)
    assert first['continuity'] == 'fresh'
    assert first['terminal_result']['success'] is True
    assert first['session'] and first['application'] == 'no_edit'
    assert agent(run, 'ask', request) == first
    assert len(launches(run.parent)) == 1
    current = call(run, 'inspect')['current']
    edit = dict(run_id=current['run_id'], cursor=current['cursor'], actor='caller', reason='new policy basis',
                effects='local only', operations=[dict(op='policy', value='changed')])
    path = run.parent / 'edit.json'
    path.write_text(json.dumps(edit))
    call(run, 'amend', '--file', path, code=2)
    request['key'] = 'two'
    second = agent(run, 'ask', request)
    assert second['target'] == first['session'] == second['session']
    assert second['acceptance'] == 'accepted' and second['continuity'] == 'same_session'
    prompt = json.loads((run.parent / 'last-prompt.json').read_text())
    assert prompt['context']['current']['policy'] == 'changed'
    assert prompt['context']['events'][0]['kind'] == 'amended'
    assert json.loads((run.parent / 'inspected-output.json').read_text())['outcome'] == 'judgment'
    assert prompt['context']['prior_exchanges'][0]['log'] == first['log']
    assert launches(run.parent)[1][:2] == ['resume', '--session-id']
    assert '-a' not in launches(run.parent)[1]


def test_unavailable_preflight_fresh_fallback_carries_question_and_history(setup):
    run, request = setup
    mode(run.parent, kind='question')
    first = agent(run, 'ask', request)
    assert first['application'] == 'question_to_caller'
    request['key'] = 'two'
    agent(run, 'ask', request, code=5)
    request['answer'] = 'Caller authorizes bounded investigation only'
    mode(run.parent, lookup='session-not-found')
    second = agent(run, 'ask', request)
    assert second['continuity'] == 'fresh_fallback'
    assert second['fallback_basis']['returncode'] == 10
    assert second['target'] is None
    prompt = json.loads((run.parent / 'last-prompt.json').read_text())
    assert prompt['request']['answer'] == request['answer']
    assert prompt['context']['prior_exchanges'][0]['response']['kind'] == 'question'
    assert prompt['context']['current']['purpose'] == 'Exercise local fake work'
    assert json.loads((run.parent / 'inspected-output.json').read_text())['output']['result']['outcome'] == 'judgment'
    assert all(args[0] != 'resume' for args in launches(run.parent))


@pytest.mark.parametrize('lookup', ['operational-error', 'unsupported-storage'])
def test_lookup_errors_are_not_unavailability(setup, lookup):
    run, request = setup
    agent(run, 'ask', request)
    request['key'] = 'two'
    mode(run.parent, lookup=lookup)
    value = agent(run, 'ask', request, code=4)
    assert value['state'] == 'not_submitted'
    assert len(launches(run.parent)) == 1


@pytest.mark.parametrize('acceptance', [None, 'unconfirmed', 'rejected'])
def test_unknown_or_rejected_resume_does_not_create_fresh_duplicate(setup, acceptance):
    run, request = setup
    agent(run, 'ask', request)
    request['key'] = 'two'
    mode(run.parent, acceptance=acceptance)
    value = agent(run, 'ask', request, code=4)
    assert value['state'] == 'pending' and value['continuity'] == 'resume_attempt'
    assert value['session'] is None
    agent(run, 'collect', key='two', code=4)
    agent(run, 'ask', request, code=4)
    request['key'] = 'three'
    agent(run, 'ask', request, code=5)
    assert len(launches(run.parent)) == 2


def test_delayed_trace_is_collected_without_resubmission(setup):
    run, request = setup
    mode(run.parent, complete=False)
    pending = agent(run, 'ask', request, code=4)
    assert pending['state'] == 'pending'
    request2 = dict(request, key='two')
    agent(run, 'ask', request2, code=5)
    mode(run.parent, trace_override=dict(status='succeeded', success=True, exit_code=0, finished_at='later'))
    done = agent(run, 'collect')
    assert done['state'] == 'returned'
    assert done['completion_basis'] == 'runner_trace'
    assert len(done['observations']) == 2
    assert len(launches(run.parent)) == 1


@pytest.mark.parametrize('values', [dict(exit=9), dict(omit_identity=True), dict(omit_response=True), dict(wrong_basis=True)])
def test_failure_and_partial_evidence_are_retained_no_blind_retry(setup, values):
    run, request = setup
    mode(run.parent, **values)
    partial = agent(run, 'ask', request, code=4)
    assert partial['state'] == 'pending'
    assert Path(partial['log']).read_bytes()
    assert agent(run, 'show', code=4) == partial
    agent(run, 'ask', request, code=4)
    assert len(launches(run.parent)) == 1
    if values.get('exit'):
        assert partial['returncode'] == 9
        trace = json.loads((run.parent / (partial['invocation'] + '.json')).read_text())
        assert partial['returned_artifacts'] == trace['root']['invocation']['returned_artifacts']
        assert b'MUTABLE_WORKFLOW_RESPONSE' in Path(partial['log']).read_bytes()


def test_agent_real_graph_edit_investigation_then_resume(setup):
    run, request = setup
    before = call(run, 'output', '--attempt', 1)
    mode(run.parent, kind='edit')
    result = agent(run, 'ask', request)
    assert result['application'] == 'applied'
    graph = call(run, 'inspect')['current']
    assert graph['steps'][-1]['id'] == 'investigation'
    assert graph['workers'] == result['context']['current']['workers']
    assert call(run, 'resume')['status'] == 'success'
    assert call(run, 'output', '--attempt', 1) == before
    assert call(run, 'output', '--attempt', 2)['request']['step']['id'] == 'investigation'
    assert agent(run, 'collect')['application'] == 'applied'
    assert len(call(run, 'inspect')['current']['edits']) == 1
    mode(run.parent)
    request['key'] = 'two'
    assert agent(run, 'ask', request)['continuity'] == 'same_session'
    assert len(launches(run.parent)) == 2


@pytest.mark.parametrize('allowed,operations', [(False, None), (True, [dict(op='insert', before=None,
    steps=[dict(id='escape', worker='unregistered', input='anything')])])])
def test_model_text_cannot_expand_effect_or_registry_grant(setup, allowed, operations):
    run, request = setup
    request['config']['authority']['apply_edits'] = allowed
    mode(run.parent, kind='edit', **({'operations': operations} if operations else {}))
    original = call(run, 'inspect')
    value = agent(run, 'ask', request)
    assert value['application'] == 'rejected'
    assert value['response']['kind'] == 'edit'
    assert call(run, 'inspect') == original


def test_declared_secret_redacted_before_log_and_result_publication(setup, monkeypatch):
    run, request = setup
    monkeypatch.setenv('FAKE_DECLARED_SECRET', 'DO_NOT_PUBLISH_123')
    value = agent(run, 'ask', request)
    assert b'DO_NOT_PUBLISH_123' not in Path(value['log']).read_bytes()
    assert b'[REDACTED]' in Path(value['log']).read_bytes()
    assert 'DO_NOT_PUBLISH_123' not in json.dumps(value)


def test_invalid_contract_stops_before_provider(setup):
    run, request = setup
    Path(request['config']['contract']).write_text('secrets: []')
    agent(run, 'ask', request, code=5)
    assert not (run.parent / 'runner-calls.jsonl').exists()


def start_held(run, request, **values):
    # Keep Unix socket path short without placing artifacts outside planning.
    path = run.parent / 'request-held.json'
    path.write_text(json.dumps(request))
    listener = socket.socket(socket.AF_UNIX)
    address = '\0acr538-' + str(os.getpid()) + '-' + run.parent.name
    listener.bind(address)
    listener.listen(1)
    listener.settimeout(10)
    mode(run.parent, kind='edit', barrier=address, **values)
    process = subprocess.Popen([sys.executable, str(AGENT), 'ask', str(run), '--file', str(path)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    conn, _ = listener.accept()
    assert conn.recv(5) == b'ready'
    return process, listener, conn


def finish_held(process, listener, conn):
    conn.sendall(b'!')
    conn.close()
    listener.close()
    stdout, stderr = process.communicate(timeout=10)
    return stdout, stderr


def test_late_graph_edit_is_rejected_without_rebasing_and_new_question_can_resume(setup):
    run, request = setup
    process, listener, conn = start_held(run, request)
    # The live provider is held after its original response. A second controller
    # cannot dispatch; an ordinary graph editor is deliberately not blocked.
    agent(run, 'ask', dict(request, key='parallel'), code=5)
    current = call(run, 'inspect')['current']
    edit = dict(run_id=current['run_id'], cursor=current['cursor'], actor='caller', reason='new evidence',
                effects='local only', operations=[dict(op='policy', value='new-basis')])
    path = run.parent / 'live-edit.json'
    path.write_text(json.dumps(edit))
    call(run, 'amend', '--file', path, code=2)
    stdout, stderr = finish_held(process, listener, conn)
    assert process.returncode == 0, (stdout, stderr)
    returned = json.loads(stdout)
    assert returned['application'] == 'rejected'
    assert 'stale' in returned['error']
    assert returned['response']['edit']['cursor'] == current['cursor']
    assert len(call(run, 'inspect')['current']['steps']) == 1
    mode(run.parent)
    assert agent(run, 'ask', dict(request, key='rebase'))['continuity'] == 'same_session'


@pytest.mark.parametrize('contrary_suffix', [False, True])
def test_collector_loss_cannot_apply_unique_prefix_on_trace_success(setup, contrary_suffix):
    run, request = setup
    original = call(run, 'inspect')
    process, listener, conn = start_held(run, request, contrary_suffix=contrary_suffix)
    process.kill()
    stdout, stderr = finish_held(process, listener, conn)
    assert process.returncode < 0
    pending = agent(run, 'show', code=4)
    assert pending['state'] == 'pending' and pending['returncode'] is None
    retained = Path(pending['log']).read_bytes()
    assert retained.count(b'MUTABLE_WORKFLOW_RESPONSE=') == 1
    assert b'OULIPOLY_INVOCATION=' in retained
    assert b'Do not apply' not in retained
    # Synthetic upstream success is deliberately insufficient: this fixture is
    # not a reproduction of the real runner's spooled delivery state machine.
    mode(run.parent)
    for _ in range(2):
        partial = agent(run, 'collect', code=4)
        assert partial['application'] == 'not_applied' and partial['response'] is None
        assert partial['returncode'] is None and partial['terminal_result'] is None
        assert partial['completion_basis'] == 'runner_trace'
        assert partial['trace']['invocation']['success'] is True
        assert partial['returned_artifacts']
        assert 'complete local capture unconfirmed' in partial['error']
        assert Path(partial['log']).read_bytes() == retained
    assert agent(run, 'ask', request, code=4) == partial
    agent(run, 'ask', dict(request, key='no-replay'), code=5)
    assert call(run, 'inspect') == original
    assert len(launches(run.parent)) == 1


def test_complete_capture_with_contrary_suffix_rejects_both_responses(setup):
    run, request = setup
    original = call(run, 'inspect')
    mode(run.parent, kind='edit', contrary_suffix=True)
    partial = agent(run, 'ask', request, code=4)
    assert partial['returncode'] == 0 and partial['terminal_result']['success'] is True
    assert Path(partial['log']).read_bytes().count(b'MUTABLE_WORKFLOW_RESPONSE=') == 2
    assert 'missing or multiple bound agent responses' in partial['error']
    assert partial['application'] == 'not_applied'
    assert call(run, 'inspect') == original
    agent(run, 'collect', code=4)
    assert len(launches(run.parent)) == 1


def test_trace_timeout_projection_is_not_completion(setup):
    run, request = setup
    mode(run.parent, trace_override=dict(status='failed', terminal_reason='tracing_timeout',
                                         stale_running=dict(age_seconds=1900, threshold_seconds=1800)))
    pending = agent(run, 'ask', request, code=4)
    assert pending['state'] == 'pending' and pending['application'] == 'not_applied'
    assert len(launches(run.parent)) == 1


def test_generic_exit_rejection_preserves_report_without_fresh_fallback(setup):
    run, request = setup
    agent(run, 'ask', request)
    request['key'] = 'two'
    mode(run.parent, exit=9, acceptance='rejected')
    failed = agent(run, 'ask', request, code=4)
    assert failed['acceptance'] == 'rejected'
    assert failed['returncode'] == 9 and failed['returned_artifacts']
    assert failed['continuity'] == 'resume_attempt'
    agent(run, 'collect', key='two', code=4)
    assert len(launches(run.parent)) == 2


def test_nonadmitted_lookup_retry_retains_session_and_since_basis(setup):
    run, request = setup
    first = agent(run, 'ask', request)
    current = call(run, 'inspect')['current']
    path = run.parent / 'edit-before-failed-lookup.json'
    path.write_text(json.dumps(dict(run_id=current['run_id'], cursor=current['cursor'], actor='root',
        reason='new evidence', effects='local only', operations=[dict(op='policy', value='new')])) )
    call(run, 'amend', '--file', path, code=2)
    mode(run.parent, lookup='operational-error')
    agent(run, 'ask', dict(request, key='lookup-failed'), code=4)
    mode(run.parent)
    result = agent(run, 'ask', dict(request, key='retry-lookup'))
    assert result['session'] == first['session'] and result['continuity'] == 'same_session'
    assert result['context']['events'][0]['kind'] == 'amended'
    assert result['context']['prior_exchanges'][1]['state'] == 'not_submitted'
    assert len(launches(run.parent)) == 2


def test_show_during_live_dispatch_is_read_only_and_does_not_wait_for_collector(setup):
    run, request = setup
    process, listener, conn = start_held(run, request)
    try:
        pending = agent(run, 'show', code=4)
        assert pending['state'] == 'pending'
        assert len(launches(run.parent)) == 1
    finally:
        finish_held(process, listener, conn)


def test_model_configuration_and_request_identity_do_not_drift(setup):
    run, request = setup
    first = agent(run, 'ask', request)
    agent(run, 'ask', dict(request, question='silently changed'), code=5)
    changed = dict(request, key='two', config=dict(request['config'], model='different'))
    agent(run, 'ask', changed, code=5)
    assert len(launches(run.parent)) == 1
    assert agent(run, 'show') == first


def test_secret_bearing_question_rejected_without_new_persisted_exchange(setup, monkeypatch):
    run, request = setup
    monkeypatch.setenv('FAKE_DECLARED_SECRET', 'DONT_PUBLISH_ME')
    request['question'] = 'DONT_PUBLISH_ME'
    result = agent(run, 'ask', request, code=5)
    assert 'DONT_PUBLISH_ME' not in json.dumps(result)
    assert not (run.parent / 'runner-calls.jsonl').exists()
    assert not (run / 'agent-exchanges').exists()


def test_launch_failure_is_distinct_from_submitted_failure(setup):
    run, request = setup
    request['config']['runner'] = [str(run.parent / 'nonexistent-executable')]
    failed = agent(run, 'ask', request, code=4)
    assert failed['state'] == 'not_submitted'
    assert failed['returncode'] is None
    assert Path(failed['log']).read_bytes() == b''
    assert agent(run, 'collect', code=4) == failed
    assert not (run.parent / 'runner-calls.jsonl').exists()


@pytest.mark.parametrize('values', [dict(foreign_trace=True), dict(malformed_trace=True),
                                     dict(trace_override=dict(exit_code=False))])
def test_foreign_malformed_or_bool_exit_trace_cannot_settle(setup, values):
    run, request = setup
    mode(run.parent, **values)
    pending = agent(run, 'ask', request, code=4)
    assert pending['state'] == 'pending'
    assert pending['application'] == 'not_applied'
    assert len(launches(run.parent)) == 1


def test_missing_reported_identity_is_explicit_fresh_not_recovery(setup):
    run, request = setup
    mode(run.parent, no_session=True)
    first = agent(run, 'ask', request)
    assert first['session'] is None
    mode(run.parent)
    second = agent(run, 'ask', dict(request, key='two'))
    assert second['continuity'] == 'fresh_fallback'
    assert second['fallback_basis']['prior_exchange'] == 'one'
    assert second['target'] is None
    assert len(launches(run.parent)) == 2
