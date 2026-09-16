"""Root's new-run adoption decisions: actual default CLI, fake processes only.

No --adapter, selection, reactivation_policy or activation grant in the caller's
new-run configuration. CRW_CHECKOUT selects the candidate installation, not policy.
These tests do not qualify the installed real runner or semantic efficacy.
"""
import json
from pathlib import Path

import pytest

from test_mutable_review_entry import configured, CRW, invoke, write, rows, call


@pytest.fixture(autouse=True)
def candidate_installation(monkeypatch):
    monkeypatch.setenv('CRW_CHECKOUT', str(CRW))


def default_call(run, command, *args, code=0):
    result = invoke('--', command, run, *args)
    with (run.parent / 'default-commands.jsonl').open('a') as log:
        log.write(json.dumps(dict(argv=result.args, returncode=result.returncode,
                                  stdout=result.stdout, stderr=result.stderr)) + '\n')
    assert result.returncode == code, (result.args, result.stdout, result.stderr)
    return json.loads(result.stderr if code == 5 else result.stdout)


def new_config(config):
    return {key: value for key, value in config.items()
            if key not in ('selection', 'reactivation_policy', 'allow_activation', 'workers')} | {
                'allow_graph_edit': False, 'allow_children': False}


@pytest.fixture
def default_started(configured):
    config, root = configured
    config = new_config(config)
    run = root / 'default'
    result = default_call(run, 'start', '--file', write(root / 'default.json', config))
    assert not (root / 'calls.jsonl').exists()
    stored = result['policy']['config']
    assert stored == dict(config, selection='perspective-lives-v1',
                         reactivation_policy='after-act-domain-v1', allow_activation=True)
    assert len(result['policy']['cycles'][0]['enabled']) == 9
    assert sum(map(len, result['policy']['cycles'][0]['enabled'].values())) == 27
    assert result['reactivation_judge']['selection'] == 'after-act-domain-v1'
    return run, root


def link_act(run, root):
    cycle = default_call(run, 'inspect')['policy']['cycles'][-1]
    return default_call(run, 'act', '--file', write(root / 'act.json', dict(
        id='fixture-act-' + str(cycle['number']), from_cycle=cycle['number'],
        decision_assignment=cycle['decision']['assignment'], material='S' + str(cycle['number']),
        owner='fixture caller', why='Authorized fixture change', verification='fake only', effects='fixture only')))


def test_new_default_activation_question_resume_and_original_returns(default_started):
    run, root = default_started
    survivor = 'organization-and-communication/utilitarian-intent'
    mode = dict(evidence=[survivor], useful=True)
    write(root / 'mode.json', mode)
    default_call(run, 'drive')
    initial = rows(root)
    assert len({row['session'] for row in initial}) == 11
    assert sum(len(row['assignment']['enabled']) for row in initial) == 27
    link_act(run, root)
    default_call(run, 'drive')
    assert not any(row['assignment']['role'] == 'reactivation' for row in rows(root))
    link_act(run, root)
    write(root / 'mode.json', dict(mode, question_once='reactivation'))
    question = default_call(run, 'drive', code=4)
    assert question['status'] == 'question'
    owner = default_call(run, 'inspect')['owner']
    # First return exposes its original source; retained questions expose owner.
    assert Path(question['return']).is_file()
    judge = rows(root)[-1]
    assert judge['assignment']['role'] == 'reactivation'
    q = judge['question']
    assert q['decision_authority'] == 'none' and not q['allow_graph_edit']
    assert q['question_destination'] == q['return_destination'] == q['root'] == owner
    assert 'Judge activation only' in q['reactivation_authority']
    assert 'organization-and-communication' not in judge['assignment']['candidates']
    retained_question = default_call(run, 'drive', code=4)
    assert retained_question['status'] == 'question' and retained_question['owner'] == owner
    assert rows(root)[-1] == judge
    write(root / 'mode.json', dict(mode, judgments={'purpose': 'activate'}, next='no_act'))
    result = default_call(run, 'drive', '--answer', 'Actual fixture root answer within existing access')
    assert result['status'] == 'qualified' and result['decision']['next'] == 'no_act'
    judges = [row for row in rows(root) if row['assignment']['role'] == 'reactivation']
    assert len(judges) == 2 and judges[1]['session'] == judge['session']
    assert judges[1]['args'][0] == 'resume' and judges[1]['answer'].startswith('Actual fixture root')
    state = default_call(run, 'inspect')
    cycle = state['policy']['cycles'][-1]
    assert cycle['enabled']['purpose'] == ['premise']
    assert cycle['enabled']['organization-and-communication'] == ['utilitarian-intent']
    assert len(state['policy']['activations']) == 1
    assert state['policy']['lives']['purpose']['allowance'] == 1
    accepted = cycle['jobs']['reactivation']['accepted']
    original = json.loads(Path(accepted['source']).read_text())
    assert json.loads(original['response']['detail'])['domains']['purpose']['judgment'] == 'activate'
    assert cycle['jobs']['reactivation']['answers'][0]['question'] == question['question']
    assert set(cycle['credit_sources']) == set(cycle['jobs'])
    assert state['consumer_completion'] == 'not established; root owns verification and disposition'
    for row in rows(root):
        q = row['question']
        assert q['access'] == str(root) and not q['allow_children'] and not q['allow_graph_edit']
        assert q['decision_authority'] == ('fixture decisions only' if row['assignment']['role'] == 'decide' else 'none')
    assert default_call(run, 'summary')['next']['consumer_completion'] is False
    before = len(rows(root))
    default_call(run, 'drive')
    assert len(rows(root)) == before


def test_default_rejection_and_denied_graph_edit_return_without_credit(default_started):
    run, root = default_started
    write(root / 'mode.json', dict(missing_once='purpose'))
    result = default_call(run, 'drive', code=4)
    assert result['status'] == 'rejected' and 'premise' in result['reason']
    first = rows(root)[0]
    write(root / 'mode.json', dict(surgery='purpose'))
    error = default_call(run, 'drive', code=5)
    assert error['status'] == 'not_confirmed' and 'graph-edit authority absent' in error['error']
    second = rows(root)[1]
    assert second['session'] == first['session'] and second['args'][0] == 'resume'
    assert 'missing perspectives: premise' in second['question']['feedback']
    state = default_call(run, 'inspect')
    assert state['owner'].startswith('fixture caller')
    assert not state['policy']['cycles'][0]['qualified']
    assert state['policy']['reactivation']['completed'] == 0
    assert all(p['current'] == 2 for d in state['policy']['lives'].values() for p in d['perspectives'].values())
    assert not (root / 'alternate-effect.txt').exists()


@pytest.mark.parametrize('field,value', [('allow_activation', False), ('allow_activation', 1),
    ('reactivation_policy', None), ('selection', 'manual')])
def test_default_conflict_is_not_overwritten(configured, field, value):
    config, root = configured
    config = dict(new_config(config), **{field: value})
    run = root / 'denied'
    result = default_call(run, 'start', '--file', write(root / 'denied.json', config), code=5)
    assert 'default conflicts with ' + field in result['error']
    assert not run.exists() and not (root / 'calls.jsonl').exists()


@pytest.mark.parametrize('field', ['owner', 'access', 'decision_authority', 'capture_contract', 'runner',
                                   'allow_children', 'allow_graph_edit'])
def test_default_does_not_invent_required_caller_inputs(configured, field):
    config, root = configured
    config = new_config(config)
    del config[field]
    run = root / 'missing'
    assert default_call(run, 'start', '--file', write(root / 'missing.json', config), code=5)['status'] == 'not_confirmed'
    assert not run.exists() and not (root / 'calls.jsonl').exists()


def test_default_continuation_preserves_explicit_historical_selection(configured):
    config, root = configured
    # Explicit old entry remains usable, including no automatic selection and denial.
    run = root / 'explicit'
    call(run, 'start', '--file', write(root / 'explicit.json', config))
    before = default_call(run, 'inspect')
    assert before['policy']['config'] == config and 'reactivation' not in before['policy']
    source = Path(before['policy']['cycles'][0]['jobs']['purpose']['assignment']['receipt'])
    assert not source.exists()
    write(root / 'mode.json', dict(next='no_act'))
    default_call(run, 'drive')
    after = default_call(run, 'inspect')
    assert after['policy']['config'] == config and 'reactivation' not in after['policy']
    assert not any(row['assignment']['role'] == 'reactivation' for row in rows(root))
    saved = (run / 'review.json').read_bytes()
    default_call(run, 'start', '--file', write(root / 'new.json', new_config(config)), code=5)
    assert (run / 'review.json').read_bytes() == saved
    assert default_call(run, 'inspect')['policy']['config'] == config


def test_missing_default_installation_fails_without_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv('CRW_CHECKOUT', str(tmp_path / 'unavailable'))
    result = invoke('--', 'start', tmp_path / 'run', '--file', tmp_path / 'config.json')
    assert result.returncode == 2 and not (tmp_path / 'run').exists()


def test_installed_location_and_start_only_routing(monkeypatch):
    import runpy
    import sys
    from test_mutable_review_entry import ENTRY, ADAPTER
    arguments = runpy.run_path(str(ENTRY))['arguments']
    monkeypatch.delenv('CRW_CHECKOUT', raising=False)
    monkeypatch.setattr(sys, 'argv', [str(ENTRY), '--', 'start', '/private/new', '--file', '/private/actual.json'])
    adapter, command = arguments()
    assert adapter == Path('/home/nes/projects/code-review-workflows/trunk/risk-axis-reviewers/workflows/corrected-cohort/cli.py')
    assert command == ['start-default', '/private/new', '--file', '/private/actual.json']
    monkeypatch.setattr(sys, 'argv', [str(ENTRY), '--', 'drive', '/private/saved', '--answer', 'actual answer'])
    assert arguments()[1] == ['drive', '/private/saved', '--answer', 'actual answer']
    monkeypatch.setattr(sys, 'argv', [str(ENTRY), '--adapter', str(ADAPTER), '--', 'start', '/private/explicit'])
    assert arguments() == (ADAPTER, ['start', '/private/explicit'])


def test_source_selection_links_the_executable_owner_not_manual_membership():
    from test_mutable_review_entry import REPO, ADAPTER
    instructions = (REPO / 'AGENTS.md').read_text()
    workflow = (REPO / 'workflows/mutable-review.md').read_text()
    owner = (ADAPTER.parent / 'README.md').read_text()
    method = (CRW / 'methods/evidence-to-change.md').read_text()
    assert 'select **the corrected cohort loop**' not in instructions
    assert '**`perspective-lives-v1`** with **`after-act-domain-v1`**' in instructions
    assert 'enabled perspectives' in instructions
    assert 'executable-observe-frame-decide-act-recurrence' in instructions
    assert '## Executable Observe Frame Decide Act recurrence' in method
    assert '## New-run consumer default' in owner and '`start-default`' in workflow
    assert 'already conditions its graph-edit' in owner
    assert 'must independently correct its unconditional' not in owner
    assert 'runtime-compatibility' in instructions
    # These are source-coherence checks, not assertions that deployment occurred.
    assert 'does **not** assert the candidate is deployed' in method
