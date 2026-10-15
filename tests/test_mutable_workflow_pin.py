"""Fresh-only pin transport at the fake-executable adapter boundary; no live runner."""
import copy
import json
import subprocess
import sys

import pytest

from test_mutable_workflow_runner import AGENT, agent, launches, mode, setup


def calls(run):
    return [json.loads(line) for line in (run.parent / 'runner-calls.jsonl').read_text().splitlines()]


def pinned(request):
    request['config']['model'] = 'gpt-xhigh'
    request['config']['fresh_provider_pin'] = 'codex5'


def assert_fresh(args, request):
    assert args == ['-m', 'gpt-xhigh', '-p', request['config']['project'],
                    '-f', args[5], '--pin-provider', 'codex5']


def test_pin_fresh_resume_and_present_diagnostics(setup):
    run, request = setup
    pinned(request)
    original = copy.deepcopy(request)
    first = agent(run, 'ask', request)
    assert first['request'] == original == request
    assert_fresh(launches(run.parent)[0], request)
    before = calls(run)
    assert agent(run, 'ask', request) == first
    assert agent(run, 'collect') == first
    assert calls(run) == before
    request['key'] = 'two'
    second = agent(run, 'ask', request)
    assert second['target'] == first['session'] == second['session']
    assert second['continuity'] == 'same_session'
    args = launches(run.parent)[1]
    assert args == ['resume', '--session-id', first['session'], '-m', 'gpt-xhigh',
                    '-p', request['config']['project'], '-f', args[-1]]
    result = subprocess.run([sys.executable, str(AGENT.with_name('inspection_cli.py')),
        'evidence', str(run), '--key', 'two', '--check-session'], capture_output=True, text=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert calls(run)[-1] == ['session', 'locate', first['session'], '--json']
    diagnostics = [args for args in calls(run) if args[0] in ('session', 'trace')]
    assert any(args[0] == 'trace' for args in diagnostics)
    assert all('--pin-provider' not in args for args in diagnostics)


@pytest.mark.parametrize('no_session', [False, True])
def test_admitted_fresh_fallback_retains_pin(setup, no_session):
    run, request = setup
    pinned(request)
    mode(run.parent, no_session=no_session)
    agent(run, 'ask', request)
    mode(run.parent, lookup='session-not-found')
    second = agent(run, 'ask', dict(request, key='two'))
    assert second['continuity'] == 'fresh_fallback' and second['target'] is None
    assert len(launches(run.parent)) == 2
    for args in launches(run.parent):
        assert_fresh(args, request)
    assert all('--pin-provider' not in args for args in calls(run) if args[0] in ('trace', 'session'))


@pytest.mark.parametrize('pin', [None, '', ' ', 'codex5 extra', '-codex5', 'codex5\x00',
                                'codex5\n', True, 5, [], {}])
def test_invalid_pin_fails_before_launch(setup, pin):
    run, request = setup
    request['config']['fresh_provider_pin'] = pin
    agent(run, 'ask', request, code=5)
    assert not (run.parent / 'runner-calls.jsonl').exists()
    assert not (run / 'agent-exchanges').exists()


@pytest.mark.parametrize('prefix', [['--pin-provider', 'codex5'], ['--pin-provider=codex5']])
def test_shared_prefix_pin_is_rejected(setup, prefix):
    run, request = setup
    request['config']['runner'] += prefix
    agent(run, 'ask', request, code=5)
    assert not (run.parent / 'runner-calls.jsonl').exists()


def test_unknown_config_key_fails_closed(setup):
    run, request = setup
    request['config']['pin_provider'] = 'codex5'
    agent(run, 'ask', request, code=5)
    assert not (run.parent / 'runner-calls.jsonl').exists()


@pytest.mark.parametrize('initial_pin', [False, True])
def test_pin_configuration_cannot_change_or_be_added_or_removed(setup, initial_pin):
    run, request = setup
    if initial_pin:
        pinned(request)
    first = agent(run, 'ask', request)
    before = calls(run)
    config = dict(request['config'], fresh_provider_pin='codex6')
    agent(run, 'ask', dict(request, config=config), code=5)
    agent(run, 'ask', dict(request, key='two', config=config), code=5)
    if initial_pin:
        del config['fresh_provider_pin']
        agent(run, 'ask', dict(request, key='two', config=config), code=5)
    assert calls(run) == before
    assert agent(run, 'show') == first


@pytest.mark.parametrize('values', [dict(omit_identity=True), dict(complete=False), dict(exit=9)])
def test_pinned_unknown_or_unresolved_work_blocks_replay(setup, values):
    run, request = setup
    pinned(request)
    mode(run.parent, **values)
    pending = agent(run, 'ask', request, code=4)
    assert pending['state'] == 'pending'
    agent(run, 'ask', request, code=4)
    agent(run, 'collect', code=4)
    agent(run, 'ask', dict(request, key='two'), code=5)
    assert len(launches(run.parent)) == 1
    assert_fresh(launches(run.parent)[0], request)


@pytest.mark.parametrize('acceptance', [None, 'unconfirmed', 'rejected'])
def test_pinned_unknown_resume_does_not_fall_back(setup, acceptance):
    run, request = setup
    pinned(request)
    agent(run, 'ask', request)
    request['key'] = 'two'
    mode(run.parent, acceptance=acceptance)
    pending = agent(run, 'ask', request, code=4)
    assert pending['state'] == 'pending' and pending['continuity'] == 'resume_attempt'
    agent(run, 'collect', key='two', code=4)
    agent(run, 'ask', request, code=4)
    agent(run, 'ask', dict(request, key='three'), code=5)
    assert len(launches(run.parent)) == 2
    assert '--pin-provider' not in launches(run.parent)[1]
