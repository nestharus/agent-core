"""Selected installed-file entry, real public CLIs, fake processes only.

Independent intent: ACR-541 optional entry and root decisions (D1 evidence
fidelity, bounded recovery, original obligations survive graph departure).
No imports from the adapter or shared runtime and no real agent execution.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
ENTRY = REPO / 'workflows/mutable-review.py'
CRW = Path(os.environ.get('CRW_CHECKOUT', '/home/nes/projects/code-review-workflows/trunk'))
ADAPTER = CRW / 'risk-axis-reviewers/workflows/corrected-cohort/cli.py'
FAKE = ADAPTER.parent / 'tests/fake_runner.py'


def write(path, value):
    path.write_text(json.dumps(value))
    return path


def invoke(*args):
    return subprocess.run([sys.executable, str(ENTRY), *map(str, args)],
                          capture_output=True, text=True, timeout=180)


def call(run, command, *args, code=0):
    result = invoke('--adapter', ADAPTER, '--', command, run, *args)
    with (run.parent / 'entry-commands.jsonl').open('a') as log:
        log.write(json.dumps(dict(argv=result.args, returncode=result.returncode,
                                  stdout=result.stdout, stderr=result.stderr)) + '\n')
    assert result.returncode == code, (result.args, result.stdout, result.stderr)
    return json.loads(result.stderr if code == 5 else result.stdout)


def rows(root):
    return [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]


@pytest.fixture
def configured(tmp_path):
    assert ADAPTER.is_file() and FAKE.is_file(), 'compatible CRW checkout/fixtures required'
    # Public interface/source readback before starting the candidate consumer.
    provider = Path(os.environ.get('MUTABLE_WORKFLOW_PROVIDER', '/home/nes/ai/tools/mutable-workflow'))
    for path in (provider / 'README.md', provider / 'agent-adapter.md', provider / 'inspection.md',
                 ADAPTER.parent / 'README.md', ADAPTER.parent / 'submission.md',
                 ADAPTER.parent / 'inspection.md', ADAPTER.parent / 'provider.py'):
        assert path.read_text().strip(), str(path)
    for path in (provider / 'cli.py', provider / 'agent_cli.py', provider / 'inspection_cli.py'):
        result = subprocess.run([sys.executable, str(path), '--help'], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert invoke('--adapter', ADAPTER, '--', '--help').returncode == 0
    contract = tmp_path / 'capture.yaml'
    contract.write_text('schema: operator-contract-v1\nsecrets: []\n')  # fake declares no secrets
    effect = tmp_path / 'alternate-effect.txt'
    worker = tmp_path / 'alternate.py'
    worker.write_text('from pathlib import Path\nimport json\n'
                      f'Path({str(effect)!r}).write_text("actual alternate effect")\n'
                      'print(json.dumps(dict(outcome="success", detail="executed alternate")))\n')
    config = dict(selection='perspective-lives-v1', provider=str(provider),
                  runner=[sys.executable, str(FAKE), str(tmp_path)],
                  capture_contract=str(contract), project=str(tmp_path),
                  owner='fixture caller; collects in ' + str(tmp_path),
                  purpose='Preserve original evidence through optional execution',
                  why='Consumer decisions must see the actual source meaning',
                  question='Examine fake S0 then S1 without relabeling evidence',
                  actors='fixture caller and fake reviewers', environment='trusted local fake only',
                  material='S0', access=str(tmp_path), obligations='independent consumer acceptance remains',
                  decision_authority='fixture decisions only', allow_children=False,
                  allow_graph_edit=True, allow_activation=False,
                  workers={'alternative': [sys.executable, str(worker)]})
    write(tmp_path / 'mode.json', {})
    return config, tmp_path


@pytest.fixture
def started(configured):
    config, tmp_path = configured
    run = tmp_path / 'review'
    call(run, 'start', '--file', write(tmp_path / 'config.json', config))
    assert not (tmp_path / 'calls.jsonl').exists()  # no resident/root/semantic startup
    state = call(run, 'inspect')
    assert state['policy']['config'] == config
    assert state['graph']['attempts'] == []
    return run, tmp_path


def test_question_interruption_resume_evidence_and_executable_departure(started):
    run, root = started
    write(root / 'mode.json', dict(question_once='purpose'))
    question = call(run, 'drive', code=4)
    assert question['status'] == 'question'
    first = rows(root)[0]
    call(run, 'interrupt', '--file', write(root / 'interrupt.json', dict(
        id='actual-fixture-interruption', from_cycle=1, material='S1', owner='fixture caller',
        why='Source changed while the actual question was outstanding',
        verification='local fixture material change only', effects='no external effects',
        decision_context='Reconcile S0 question then inspect S1; do not credit S0')))
    assert call(run, 'drive', code=4)['status'] == 'question'
    assert len(rows(root)) == 1  # no obsolete re-launch
    write(root / 'mode.json', dict(evidence=['purpose/premise'], useful=True, next='no_act'))
    result = call(run, 'drive', '--answer', 'Read only the local fixture')
    assert result['status'] == 'qualified'
    calls = rows(root)
    recovery = calls[1]
    assert recovery['args'][0] == 'resume' and recovery['session'] == first['session']
    assert recovery['answer'] == 'Read only the local fixture'
    assert recovery['question']['decision_authority'] == 'none'
    assert recovery['assignment']['material'] == 'S0'
    assert recovery['question']['inputs']['recovery']['current_material'] == 'S1'
    state = call(run, 'inspect')
    old, current = state['policy']['cycles']
    assert not old['qualified'] and current['qualified']
    assert old['jobs']['purpose']['answers'][0]['question'] == question['question']
    # Literal content AND basis AND assignment, not just keyed accounting.
    accepted = current['jobs']['purpose']['accepted']
    original = json.loads(Path(accepted['source']).read_text())
    product = json.loads(original['response']['detail'])
    entry = product['entries']['premise']
    assert entry == dict(status='evidence', evidence='fixture source: supported outcome', basis='fixture:1')
    expected = dict(evidence='fixture source: supported outcome', basis='fixture:1', assignment=product['assignment'])
    downstream = [row for row in calls if row['assignment']['role'] in ('frame', 'decide')]
    assert [row['assignment']['role'] for row in downstream] == ['frame', 'decide']
    for row in downstream:
        assert row['question']['inputs']['evidence'] == {'purpose/premise': expected}
    assert result['decision']['decisions']['retain']['used'] == ['purpose/premise']
    summary = call(run, 'summary')
    assert summary['next'] == dict(kind='qualified', decision_next='no_act', consumer_completion=False)
    assert not state['stabilized']
    revision = summary['policy']['revision']
    record = call(run, 'record', '--revision', revision)
    original_bytes = Path(accepted['source']).read_bytes()
    # Explicit authorized graph surgery through the SAME selected entry.
    graph = state['graph']
    call(run, 'amend', '--file', write(root / 'edit.json', dict(
        run_id=graph['run_id'], cursor=graph['cursor'], actor='fixture caller',
        reason='Exercise alternate execution without certifying original policy', effects='one local marker',
        operations=[dict(op='replace', start=graph['steps'][0]['id'], count=len(graph['steps']),
                         steps=[dict(id='alternate', worker='alternative', input={})]),
                    dict(op='policy', value='alternate fixture only'), dict(op='goto', step='alternate')])) )
    departed = call(run, 'drive', code=4)
    assert departed['status'] == 'departed' and departed['graph']['status'] == 'success'
    assert departed['original_policy_complete'] is False
    assert (root / 'alternate-effect.txt').read_text() == 'actual alternate effect'
    assert Path(accepted['source']).read_bytes() == original_bytes
    assert call(run, 'record', '--revision', revision) == record
    final = call(run, 'inspect')
    assert not final['original_policy']
    assert final['consumer_completion'] == 'not established; root owns verification and disposition'
    assert final['policy']['config']['obligations'] == 'independent consumer acceptance remains'


def test_rejected_submission_resumes_and_role_can_propose_edit(started):
    run, root = started
    write(root / 'mode.json', dict(missing_once='purpose'))
    rejected = call(run, 'drive', code=4)
    assert rejected['status'] == 'rejected' and 'premise' in rejected['reason']
    first = rows(root)[0]
    write(root / 'mode.json', dict(surgery='purpose'))
    assert call(run, 'drive', code=4)['status'] == 'departed'
    second = rows(root)[1]
    assert second['args'][0] == 'resume' and second['session'] == first['session']
    assert 'missing perspectives: premise' in second['question']['feedback']
    result = call(run, 'drive', code=4)
    assert result['graph']['status'] == 'success' and not result['original_policy_complete']
    assert (root / 'alternate-effect.txt').read_text() == 'actual alternate effect'
    assert not call(run, 'inspect')['policy']['cycles'][0]['qualified']


def test_explicit_adapter_errors_are_not_success(tmp_path):
    assert invoke('start', tmp_path / 'run').returncode == 2
    assert invoke('--adapter', 'relative.py', '--', '--help').returncode == 2
    assert invoke('--adapter', tmp_path / 'missing.py', '--', '--help').returncode == 2
    result = call(tmp_path / 'missing-run', 'inspect', code=5)
    assert result['status'] == 'not_confirmed'
    assert not (tmp_path / 'missing-run').exists()
