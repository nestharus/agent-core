"""ACR-540 outcome tests: real CLI/fake processes, never a live provider.

Intent: ticket outcomes and root decisions; no inferred semantic policy oracle.
"""
import base64
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from test_mutable_workflow import call, plan_file
from test_mutable_workflow_runner import setup, agent, launches, mode
from test_mutable_workflow_surgery import ready, amend, step, held_worker, finish

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'tools/mutable-workflow/inspection_cli.py'
sys.path.insert(0, str(ENTRY.parent))
import inspection_view
import runtime


def inspect(command, run, *args, code=0):
    result = subprocess.run([sys.executable, str(ENTRY), command, str(run), *map(str, args)],
                            capture_output=True, text=True)
    assert result.returncode == code, (result.stdout, result.stderr)
    return json.loads(result.stderr if code == 5 else result.stdout)


def current(run):
    return inspect('summary', run)['sources'][0]['current']


def consume(run, token=None, limit=1):
    events = []
    while True:
        options = ['--cursor', token] if token else []
        page = inspect('summary', run, '--limit', limit, *options)
        events.extend(page['sources'][0]['events'])
        token = page['cursor']
        if not page['has_more']:
            return events, token


def test_live_replacement_paging_restart_and_original_evidence(tmp_path):
    with held_worker(tmp_path) as (run, process, connection):
        first = inspect('summary', run, '--limit', 1)
        assert first['has_more'] and first['sources'][0]['cursor']['position'] == 1
        assert first['sources'][0]['observed_head'] == 2
        assert current(run)['attempts'][0]['effects'] == 'unconfirmed'
        amend(tmp_path, run, [dict(op='replace', start='original', count=1, steps=[step('original')])])
        pending = current(run)
        assert pending['active_attempt'] is None and pending['target'] != '1'
        finish(process, connection)
        # Each call is a new process/connection, including continuation after completion.
        rest, token = consume(run, first['cursor'])
        events = first['sources'][0]['events'] + rest
        assert [e['sequence'] for e in events] == [1, 2, 3, 4]
        assert [e['summary']['kind'] for e in events] == ['started', 'attempt_started', 'amended', 'attempt_returned']
        assert inspect('summary', run, '--cursor', token)['sources'][0]['events'] == []
        old = inspect('node', run, '--node', '1')
        assert old['node']['disposition'] == 'removed'
        assert old['attempts'][0]['credited'] is False
        assert old['attempts'][0]['output']['result']['outcome'] == 'success'
        change = old['changes'][-1]
        assert change['removed_nodes'] == ['1'] and change['added_nodes'] == [pending['target']]
        detail = inspect('record', run, '--sequence', change['sequence'])['detail']['detail']
        assert detail['actor'] == 'local-test-editor' and detail['effects'] and detail['reason']


@pytest.mark.parametrize('bad,fragment', [('!', 'encoding'), ('0', 'encoding'),
    (inspection_view.encode(dict(version=2, sources=[])), 'unsupported'),
    (inspection_view.encode(dict(version=1, sources=[dict(path='x', run_id='x', epoch='x', position=-1)])), 'position')])
def test_malformed_cursor_explicit_error(tmp_path, bad, fragment):
    run, _ = ready(tmp_path)
    error = inspect('summary', run, '--cursor', bad, code=5)
    assert fragment in error['error'] and error['outcome'] == 'not_confirmed'


def test_foreign_ahead_expired_and_changed_source_set(tmp_path):
    a = tmp_path / 'a'; a.mkdir()
    b = tmp_path / 'b'; b.mkdir()
    run, _ = ready(a); foreign, _ = ready(b)
    token = inspect('summary', run)['cursor']
    assert 'foreign' in inspect('summary', foreign, '--cursor', token, code=5)['error']
    parsed = inspection_view.decode(token)
    parsed['sources'][0]['position'] += 1
    assert 'ahead' in inspect('summary', run, '--cursor', inspection_view.encode(parsed), code=5)['error']
    parsed = inspection_view.decode(token)
    parsed['sources'][0]['epoch'] = 'previous-generation'
    assert 'expired' in inspect('summary', run, '--cursor', inspection_view.encode(parsed), code=5)['error']
    assert 'source set' in inspect('summary', run, foreign, '--cursor', token, code=5)['error']


def test_multisource_exchange_deltas_do_not_depend_on_graph_cursor(setup, tmp_path):
    run, request = setup
    other_parent = tmp_path / 'other'; other_parent.mkdir()
    other, _ = ready(other_parent)
    start = inspect('summary', run, other)
    before = start['sources'][0]['current']['graph_cursor']
    mode(run.parent, kind='question')
    returned = agent(run, 'ask', request)
    amend(other_parent, other, [dict(op='skip', steps=['step-0'])])
    after = inspect('summary', run, other, '--cursor', start['cursor'])
    left, right = after['sources']
    assert left['current']['graph_cursor'] == before
    assert left['events'] and all(e['source'] == 'exchange' for e in left['events'])
    assert right['events'][0]['summary']['kind'] == 'amended'
    assert 'answer' in left['current']['conversation_next']
    assert left['current']['exchanges'][0]['owner'] == 'test-root'
    assert left['current']['exchanges'][0]['availability'].startswith('unchecked')
    revision = left['current']['exchanges'][0]['revision']
    assert inspect('record', run, '--sequence', revision)['detail'] == returned
    assert len(launches(run.parent)) == 1


@pytest.mark.parametrize('damage,expected', [('missing', 'missing'), ('truncated', 'truncated'),
    ('altered', 'digest_mismatch'), ('trace_missing', 'missing'), ('receipt_missing', 'matches_capture')])
def test_post_settlement_damage_visible_without_rewriting_history(setup, damage, expected):
    run, request = setup
    original = agent(run, 'ask', request)
    log = Path(original['log'])
    target = log
    if damage == 'missing':
        log.unlink()
    elif damage == 'truncated':
        log.write_bytes(log.read_bytes()[:-1])
    elif damage == 'altered':
        raw = log.read_bytes(); log.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    elif damage == 'trace_missing':
        target = Path(original['observations'][0]['log']); target.unlink()
    else:
        log.with_suffix('.log.capture.json').unlink()
    report = inspect('evidence', run, '--key', 'one', '--verify')
    selected = next(item for item in report['logs'] if item['path'] == str(target))
    assert selected['availability'] == expected
    if damage == 'receipt_missing':
        assert selected['receipt'] == 'missing'
    assert report['historical_state'] == 'returned'
    assert agent(run, 'show') == original == agent(run, 'collect')
    assert len(launches(run.parent)) == 1


@pytest.mark.parametrize('lookup,expected', [('available', 'available'), ('session-not-found', 'unavailable'),
    ('operational-error', 'unresolved'), ('unsupported-storage', 'unresolved')])
def test_present_session_query_is_explicit_and_never_dispatches(setup, lookup, expected):
    run, request = setup
    original = agent(run, 'ask', request)
    before = (run.parent / 'runner-calls.jsonl').read_text()
    assert inspect('evidence', run, '--key', 'one')['session']['availability'] == 'unchecked'
    assert (run.parent / 'runner-calls.jsonl').read_text() == before
    mode(run.parent, lookup=lookup)
    result = inspect('evidence', run, '--key', 'one', '--check-session')
    assert result['session']['availability'] == expected
    assert 'jsonl_path' not in json.dumps(result)
    assert agent(run, 'show') == original and len(launches(run.parent)) == 1


def test_summary_omits_payload_and_evidence_never_follows_external_log(setup):
    run, request = setup
    secret = 'PRIVATE-QUESTION-NOT-FOR-SUMMARY'
    request['question'] = secret
    returned = agent(run, 'ask', request)
    assert secret not in json.dumps(inspect('summary', run))
    assert secret in json.dumps(inspect('record', run, '--sequence', current(run)['exchanges'][0]['revision']))
    external = run.parent / 'not-authorized.txt'; external.write_text('PRIVATE EXTERNAL CONTENT')
    Path(returned['log']).unlink(); Path(returned['log']).symlink_to(external)
    report = inspect('evidence', run, '--key', 'one', '--verify')
    assert report['logs'][0]['availability'] == 'restricted'
    assert 'PRIVATE EXTERNAL CONTENT' not in json.dumps(report)
    assert report['returned_artifacts'][0]['availability'] == 'unchecked_external_store'


def test_summary_work_count_independent_of_retained_payload(tmp_path, monkeypatch):
    run, _ = ready(tmp_path, ['ordinary'])
    db = runtime.connect(run)
    attempt = runtime.begin_attempt(db, runtime.load(db))
    runtime.finish_attempt(db, runtime.load(db), attempt,
        runtime.captured(0, b'{"outcome":"success","detail":"ok"}', b'private-worker-payload' * 100000), False)
    db.close()
    original = json.loads
    sizes = []
    def counted(value, *args, **kwargs):
        sizes.append(len(value))
        return original(value, *args, **kwargs)
    monkeypatch.setattr(json, 'loads', counted)
    def no_payload(*args, **kwargs):
        raise AssertionError('summary decoded retained worker payload')
    monkeypatch.setattr(base64, 'b64decode', no_payload)
    result = inspection_view.page([run])
    assert 'private-worker-payload' not in json.dumps(result)
    assert max(sizes) < 3000 and sum(sizes) < 10000


def test_missing_history_is_not_false_empty(tmp_path):
    run, _ = ready(tmp_path)
    token = inspect('summary', run)['cursor']
    with sqlite3.connect(run / 'state.sqlite3') as db:
        db.execute('DELETE FROM inspection_events WHERE sequence=1')
    assert 'missing inspection' in inspect('summary', run, '--cursor', token, code=5)['error']


def test_existing_run_explicit_index_has_baseline_not_invented_history(tmp_path):
    run, _ = ready(tmp_path)
    with sqlite3.connect(run / 'state.sqlite3') as db:
        for table in ('inspection_meta', 'inspection_events', 'inspection_exchanges', 'inspection_attempts'):
            db.execute('DROP TABLE ' + table)
    assert 'unavailable' in inspect('summary', run, code=5)['error']
    call(run, 'resume')
    assert inspect('index', run)['historical_exchange_revisions'].startswith('unavailable')
    events, _ = consume(run)
    assert len(events) == 1 and events[0]['summary']['kind'] == 'baseline'
    assert len(current(run)['attempts']) == 3
    assert 'already indexed' in inspect('index', run, code=5)['error']


def test_policy_publication_retains_owner_basis_and_order_without_semantic_credit(tmp_path):
    run, state = ready(tmp_path)
    token = inspect('summary', run)['cursor']
    publication = dict(source='fake-policy-owner', revision=1, run_id=state['run_id'], status='blocked',
        owner='root', basis={'selection': 'fixture-only', 'graph_cursor': state['cursor']},
        detail={'next': 'root must reconcile retained unknown request', 'uncertainty': 'submission unknown',
                'policy_claims': {'not_provider_semantics': True}, 'source': 'owned fixture notes'})
    path = tmp_path / 'publication.json'; path.write_text(json.dumps(publication))
    result = inspect('publish', run, '--file', path)
    assert inspect('publish', run, '--file', path)['sequence'] == result['sequence']
    page = inspect('summary', run, '--cursor', token)
    assert len(page['sources'][0]['events']) == 1
    assert page['sources'][0]['current']['publications'][0]['status'] == 'blocked'
    assert page['sources'][0]['current']['graph_cursor'] == state['cursor']
    assert inspect('record', run, '--sequence', result['sequence'])['detail'] == publication
    publication['revision'] = 3; path.write_text(json.dumps(publication))
    assert 'gap' in inspect('publish', run, '--file', path, code=5)['error']
    publication['revision'] = 1; publication['status'] = 'complete'; path.write_text(json.dumps(publication))
    assert 'already bound' in inspect('publish', run, '--file', path, code=5)['error']


def test_payload_omission_includes_graph_inputs_and_amendment_prose(tmp_path):
    run, _ = ready(tmp_path)
    amend(tmp_path, run, [dict(op='replace', start='step-0', count=1,
        steps=[step('replacement', {'private_input': 'INPUT-CANARY'})]),
        dict(op='policy', value={'private_policy': 'POLICY-CANARY'})])
    summary = inspect('summary', run)
    assert 'INPUT-CANARY' not in json.dumps(summary) and 'POLICY-CANARY' not in json.dumps(summary)
    graph_change = summary['sources'][0]['current']['latest_graph_change']
    original = inspect('record', run, '--sequence', graph_change['sequence'])
    assert 'INPUT-CANARY' in json.dumps(original) and 'POLICY-CANARY' in json.dumps(original)


@pytest.mark.parametrize('boundary,returned', [('during-attempt_returned', False), ('after-attempt_returned', True)])
def test_abrupt_process_restart_keeps_journal_and_graph_joint(boundary, returned, tmp_path):
    from test_mutable_workflow_recovery import fault, recoverable_plan
    run = tmp_path / 'run'
    fault(boundary, 'start', run, recoverable_plan(tmp_path))
    events, token = consume(run)
    assert [e['summary']['kind'] for e in events] == (
        ['started', 'attempt_started', 'attempt_returned'] if returned else ['started', 'attempt_started'])
    assert current(run)['attempts'][0]['output_collected'] is returned
    call(run, 'recover', '--attempt', 1, '--redeliver')
    rest, _ = consume(run, token)
    complete = events + rest
    assert sum(e['summary']['kind'] == 'attempt_returned' for e in complete) == 1
    assert current(run)['attempts'][0]['output_collected'] is True
    assert [e['sequence'] for e in complete] == list(range(1, len(complete) + 1))


def test_failed_atomic_application_does_not_publish_applied_revision(setup):
    run, request = setup
    mode(run.parent, kind='edit', operations=[dict(op='abort'), dict(op='unknown-operation')])
    before = inspect('summary', run)
    returned = agent(run, 'ask', request)
    assert returned['application'] == 'rejected'
    page = inspect('summary', run, '--cursor', before['cursor'])
    events = page['sources'][0]['events']
    assert all(e['source'] == 'exchange' for e in events)
    assert not any(e['summary']['application'] == 'applied' for e in events)
    assert page['sources'][0]['current']['status'] == 'judgment'


def test_session_identity_not_established_is_not_missing_session(setup):
    run, request = setup
    mode(run.parent, no_session=True)
    agent(run, 'ask', request)
    report = inspect('evidence', run, '--key', 'one', '--check-session')
    assert report['session']['availability'] == 'identity_unestablished'
    rows = [json.loads(line) for line in (run.parent / 'runner-calls.jsonl').read_text().splitlines()]
    assert not any(row[0] == 'session' for row in rows)


@pytest.mark.parametrize('damage', ['receipt_corrupt', 'nonregular'])
def test_unusable_local_artifact_is_visible_without_reading_arbitrary_bytes(setup, damage):
    run, request = setup
    result = agent(run, 'ask', request)
    log = Path(result['log'])
    if damage == 'receipt_corrupt':
        log.with_suffix('.log.capture.json').write_text('{malformed')
    else:
        log.unlink(); log.mkdir()
    report = inspect('evidence', run, '--key', 'one', '--verify')
    value = report['logs'][0]
    if damage == 'receipt_corrupt':
        assert value['receipt'] == 'malformed_or_unreadable' and value['availability'] == 'matches_capture'
    else:
        assert value['availability'] == 'unsupported_file_type'


def test_compact_snapshot_does_not_mix_concurrent_commit(tmp_path):
    import threading
    run, _ = ready(tmp_path)
    db = runtime.connect(run)
    snapshot = inspection_view.snapshot(db, run, None, 1)
    commit_entered = threading.Event()
    errors = []
    def writer():
        connection = runtime.connect(run)
        connection.set_trace_callback(lambda sql: commit_entered.set() if sql == 'COMMIT' else None)
        try:
            state = runtime.load(connection)
            runtime.begin_attempt(connection, state)
        except Exception as exc:
            errors.append(exc)
        finally:
            connection.close()
    thread = threading.Thread(target=writer)
    thread.start()
    try:
        assert commit_entered.wait(10)
        # Writer has reached COMMIT but this existing read transaction still sees its original snapshot.
        assert inspection_view.metadata(db)[1] == snapshot['observed_head'] == 1
    finally:
        db.close()
        thread.join(10)
    assert not thread.is_alive() and not errors
    token = inspection_view.encode(dict(version=1, sources=[snapshot['cursor']]))
    next_page = inspect('summary', run, '--cursor', token)
    assert next_page['sources'][0]['events'][0]['summary']['kind'] == 'attempt_started'
    assert next_page['sources'][0]['current']['status'] == 'running'


def test_unsubmitted_continuation_does_not_erase_original_question(setup):
    run, request = setup
    mode(run.parent, kind='question')
    agent(run, 'ask', request)
    mode(run.parent, lookup='operational-error')
    agent(run, 'ask', dict(request, key='second', answer='bounded actual answer'), code=4)
    assert 'answer retained question' in current(run)['conversation_next']
    assert current(run)['exchanges'][-1]['state'] == 'not_submitted'


def test_payload_work_counts_compare_zero_and_large_history(tmp_path, monkeypatch):
    counts = []
    original = json.loads
    for size in (0, 1048576):
        directory = tmp_path / str(size); directory.mkdir()
        run, _ = ready(directory, ['ordinary'])
        db = runtime.connect(run)
        attempt = runtime.begin_attempt(db, runtime.load(db))
        runtime.finish_attempt(db, runtime.load(db), attempt,
            runtime.captured(0, b'{"outcome":"success","detail":"ok"}', b'x' * size), False)
        db.close()
        parsed_bytes = []
        def counted(value, *args, **kwargs):
            parsed_bytes.append(len(value))
            return original(value, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(json, 'loads', counted)
            inspection_view.page([run])
        counts.append(sum(parsed_bytes))
    assert counts[0] == counts[1]


def test_unreadable_log_reports_access_gap_even_without_hashing(setup, monkeypatch):
    import evidence_view
    run, request = setup
    returned = agent(run, 'ask', request)
    log = Path(returned['log'])
    original = Path.open
    def restricted(path, *args, **kwargs):
        if path == log:
            raise PermissionError('fixture reader denied')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', restricted)
    result = evidence_view.evidence(run, 'one')
    assert result['logs'][0]['availability'] == 'inaccessible'
    assert result['historical_state'] == 'returned'


@pytest.mark.parametrize('options,message', [(['--cursor', ''], 'encoding'),
    (['--limit', '0'], 'limit'), (['--limit', '1001'], 'limit'),
    (['--cursor', inspection_view.encode(dict(version=True, sources=[]))], 'unsupported')])
def test_invalid_cursor_and_page_boundary_never_restart_silently(tmp_path, options, message):
    run, _ = ready(tmp_path)
    assert message in inspect('summary', run, *options, code=5)['error']
