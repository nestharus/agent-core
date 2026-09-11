"""Mock transport/CLI evidence only; does not establish live API or agent efficacy."""
import copy
import http.client
import io
import json
from pathlib import Path

import pytest
import yaml

from clients.linear import cli
from clients.linear.client import LinearClient, LinearClientError
from clients.linear.project_operations import assign_issue_project, create_project

PROJECT = '11111111-1111-4111-8111-111111111111'
TEAM = '22222222-2222-4222-8222-222222222222'
ISSUE = '33333333-3333-4333-8333-333333333333'
OTHER = '44444444-4444-4444-8444-444444444444'
NAME = 'Notification Delivery Scaling — AGE-353'


def project(**changes):
    return dict(id=PROJECT, name=NAME, description=None, archivedAt=None,
                teams={'nodes': [{'id': TEAM, 'key': 'AGE'}],
                       'pageInfo': {'hasNextPage': False, 'endCursor': None}}, **changes)


def page(nodes=None, next_page=False, cursor=None):
    return {'data': {'projects': {'nodes': nodes or [], 'pageInfo': {
        'hasNextPage': next_page, 'endCursor': cursor}}}}


def transport(monkeypatch, responses):
    calls = []
    responses = iter(responses)

    def urlopen(request, timeout):
        calls.append(json.loads(request.data))
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, io.BytesIO):
            return response
        return io.BytesIO(json.dumps(response).encode())

    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    return LinearClient(api_key='mock-key'), calls


def created(echo=None, success=True):
    return {'data': {'projectCreate': {'success': success, 'project': echo if echo is not None else {'id': PROJECT}}}}


def read(p=None):
    return {'data': {'project': p if p is not None else project()}}


def test_create_transport_and_independent_read(monkeypatch):
    p = project()
    p['description'] = 'Caller text'
    client, calls = transport(monkeypatch, [page(), created(), read(p)])
    result = create_project(client, NAME, TEAM, PROJECT, 'Caller text')
    assert result['ok'] is True
    assert result['data']['mutation'] == 'acknowledged'
    assert result['data']['readback'] == 'matched'
    assert calls[0]['variables']['includeArchived'] is True
    assert calls[1]['variables'] == {'input': {'id': PROJECT, 'name': NAME, 'teamIds': [TEAM], 'description': 'Caller text'}}
    assert calls[2]['variables'] == {'id': PROJECT}
    assert 'project(id: $id)' in calls[2]['query']


@pytest.mark.parametrize('response', [{}, {'data': None}, {'data': {}},
    {'data': {'projects': {}}}, {'data': {'projects': {'nodes': [], 'pageInfo': {'hasNextPage': 0}}}},
    {'data': {'projects': {'nodes': None, 'pageInfo': {'hasNextPage': False}}}}])
def test_incomplete_inventory_never_creates(monkeypatch, response):
    client, calls = transport(monkeypatch, [response])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert not result['ok']
    assert result['data']['mutation'] == 'not_attempted'
    assert len(calls) == 1


@pytest.mark.parametrize('field,value', [('id', None), ('id', 'not-a-uuid'), ('name', ''), ('teams', None),
    ('teams', {'nodes': [{'id': 'bad'}], 'pageInfo': {'hasNextPage': False}}),
    ('teams', {'nodes': [{'id': TEAM}], 'pageInfo': {'hasNextPage': True}}),
    ('teams', {'nodes': [{}], 'pageInfo': {'hasNextPage': False}}),
    ('archivedAt', False), ('description', {})])
def test_malformed_inventory_nodes_block(monkeypatch, field, value):
    p = project()
    p[field] = value
    client, calls = transport(monkeypatch, [page([p])])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert not result['ok']
    assert len(calls) == 1


@pytest.mark.parametrize('cursors', [['a', 'a'], ['a', 'b', 'a'], [None], [''], [42]])
def test_inventory_cursor_anomalies(monkeypatch, cursors):
    client, calls = transport(monkeypatch, [page(next_page=True, cursor=c) for c in cursors])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert result['error']['code'] == 'PAGINATION_ERROR'
    assert result['data']['mutation'] == 'not_attempted'
    assert len(calls) == len(cursors)


@pytest.mark.parametrize('variant', ['one', 'duplicate', 'archived', 'wrong-team', 'description'])
def test_candidates_require_selection_never_create(monkeypatch, variant):
    p = project()
    if variant == 'archived':
        p['archivedAt'] = '2026-01-01'
    if variant == 'wrong-team':
        p['teams']['nodes'][0]['id'] = OTHER
    if variant == 'description':
        p['description'] = 'Different intent'
    candidates = [p]
    if variant == 'duplicate':
        other = copy.deepcopy(p)
        other['id'] = OTHER
        candidates.append(other)
    client, calls = transport(monkeypatch, [page(next_page=True, cursor='next'), page(candidates)])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert result['error']['code'] == 'PROJECT_CANDIDATES'
    assert len(result['data']['candidates']) == len(candidates)
    assert len(calls) == 2


@pytest.mark.parametrize('response', [TimeoutError(), {}, {'data': {}},
    {'data': {'projectCreate': None}}, created(success=False), created(success='true')])
def test_unknown_or_unacknowledged_create_retains_uuid_no_retry(monkeypatch, response):
    client, calls = transport(monkeypatch, [page(), response])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert not result['ok']
    assert result['data']['projectId'] == PROJECT
    assert result['data']['mutation'] == 'unknown'
    assert result['data']['readback'] == 'not_attempted'
    assert len(calls) == 2


@pytest.mark.parametrize('echo', [{}, {'id': OTHER}])
def test_acknowledged_identity_error_preserves_both_identities(monkeypatch, echo):
    client, calls = transport(monkeypatch, [page(), created(echo)])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert not result['ok']
    assert result['data']['mutation'] == 'acknowledged'
    assert result['data']['returnedProjectId'] == echo.get('id')
    assert result['data']['projectId'] == PROJECT
    assert len(calls) == 2


@pytest.mark.parametrize('variant', ['timeout', 'missing', 'identity', 'name', 'team', 'description', 'archived'])
def test_create_readback_failures_preserve_ack(monkeypatch, variant):
    p = project()
    if variant in ('identity', 'name', 'description', 'archived'):
        p[{'identity': 'id', 'name': 'name', 'description': 'description', 'archived': 'archivedAt'}[variant]] = OTHER
    if variant == 'team':
        p['teams']['nodes'][0]['id'] = OTHER
    response = TimeoutError() if variant == 'timeout' else {'data': {}} if variant == 'missing' else read(p)
    client, calls = transport(monkeypatch, [page(), created(), response])
    result = create_project(client, NAME, TEAM, PROJECT, '' if variant == 'description' else None)
    assert not result['ok']
    assert result['data']['mutation'] == 'acknowledged'
    assert result['data']['readback'] == 'unverified'
    assert result['data']['projectId'] == PROJECT
    assert len(calls) == 3


def issue(project_id=OTHER):
    return {'id': ISSUE, 'identifier': 'AGE-353', 'title': 'Original', 'description': 'Unchanged',
            'team': {'id': TEAM}, 'project': {'id': project_id}, 'estimate': 8,
            'state': {'id': OTHER}, 'labels': [{'id': OTHER}], 'parent': {'id': OTHER}}


def assignment_client(monkeypatch, after=None, mutation=None, initial=None):
    client, calls = transport(monkeypatch, [read(), mutation or {'data': {'issueUpdate': {'success': True}}}])
    initial = initial or issue()
    reads = []
    def get_issue(token):
        reads.append(token)
        if len(reads) == 1:
            return initial
        if isinstance(after, Exception):
            raise after
        return after if after is not None else issue(PROJECT)
    monkeypatch.setattr(client, 'get_issue', get_issue)
    return client, calls, reads


def test_assignment_only_project_patch_and_exact_independent_read(monkeypatch):
    client, calls, reads = assignment_client(monkeypatch)
    result = assign_issue_project(client, 'AGE-353', PROJECT)
    assert result['ok']
    assert calls[1]['variables'] == {'id': ISSUE, 'input': {'projectId': PROJECT}}
    assert reads == ['AGE-353', ISSUE]
    assert result['data']['mutation'] == 'acknowledged'
    assert result['data']['readback'] == 'matched'


@pytest.mark.parametrize('after', [issue(), {**issue(PROJECT), 'id': OTHER}, {'id': ISSUE},
    LinearClientError('API_ERROR', 'read failed')])
def test_assignment_read_failure_never_restores_or_retries(monkeypatch, after):
    client, calls, reads = assignment_client(monkeypatch, after=after)
    result = assign_issue_project(client, 'AGE-353', PROJECT)
    assert not result['ok']
    assert result['data']['mutation'] == 'acknowledged'
    assert result['data']['issueId'] == ISSUE
    assert result['data']['projectId'] == PROJECT
    assert result['data']['readback'] == 'unverified'
    assert len(calls) == 2
    assert len(reads) == 2


def test_initial_match_does_not_mutate_but_reads_again(monkeypatch):
    client, calls, reads = assignment_client(monkeypatch, initial=issue(PROJECT))
    result = assign_issue_project(client, 'AGE-353', PROJECT)
    assert result['ok']
    assert result['data']['mutation'] == 'already_matching'
    assert len(calls) == 1
    assert reads == ['AGE-353', ISSUE]


@pytest.mark.parametrize('mutation', [{'data': {'issueUpdate': {}}}, {'data': {'issueUpdate': {'success': False}}}])
def test_assignment_missing_ack_stops(monkeypatch, mutation):
    client, calls, reads = assignment_client(monkeypatch, mutation=mutation)
    result = assign_issue_project(client, 'AGE-353', PROJECT)
    assert not result['ok']
    assert result['data']['mutation'] == 'unknown'
    assert len(reads) == 1
    assert len(calls) == 2


def test_wrong_team_blocks_assignment(monkeypatch):
    initial = issue()
    initial['team']['id'] = OTHER
    client, calls, reads = assignment_client(monkeypatch, initial=initial)
    result = assign_issue_project(client, 'AGE-353', PROJECT)
    assert not result['ok']
    assert result['data']['mutation'] == 'not_attempted'
    assert len(calls) == 1


def test_cli_failure_has_progress_and_nonzero_exit(monkeypatch, capsys):
    monkeypatch.setenv('LINEAR_API_KEY', 'mock-key')
    _, calls = transport(monkeypatch, [page(), created(), TimeoutError()])
    with pytest.raises(SystemExit) as exit:
        cli.main(['create-project', '--name', NAME, '--team-id', TEAM, '--project-id', PROJECT])
    assert exit.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert not result['ok']
    assert result['data']['mutation'] == 'acknowledged'
    assert result['data']['projectId'] == PROJECT
    assert len(calls) == 3


def test_cli_assignment_dispatch(monkeypatch, capsys):
    client, calls, reads = assignment_client(monkeypatch)
    monkeypatch.setattr(cli, 'LinearClient', lambda: client)
    cli.main(['assign-issue-project', 'AGE-353', '--project-id', PROJECT])
    assert json.loads(capsys.readouterr().out)['data']['readback'] == 'matched'
    assert calls[1]['variables']['input'] == {'projectId': PROJECT}


def test_cli_get_project(monkeypatch, capsys):
    monkeypatch.setenv('LINEAR_API_KEY', 'mock-key')
    _, calls = transport(monkeypatch, [read()])
    cli.main(['get-project', PROJECT])
    assert json.loads(capsys.readouterr().out)['data']['id'] == PROJECT
    assert len(calls) == 1


@pytest.mark.parametrize('args', [['get-project', NAME], ['create-project', '--name', NAME],
    ['assign-issue-project', 'AGE-353']])
def test_cli_invalid_inputs_no_transport(monkeypatch, capsys, args):
    monkeypatch.setenv('LINEAR_API_KEY', 'mock-key')
    _, calls = transport(monkeypatch, [])
    with pytest.raises(SystemExit):
        cli.main(args)
    assert not json.loads(capsys.readouterr().out)['ok']
    assert not calls


def test_operator_sidecar_and_usage_parity():
    root = Path(__file__).resolve().parents[1]
    text = (root / 'agents/linear-operator.md').read_text()
    embedded = yaml.safe_load(text.split('```yaml\n', 1)[1].split('```', 1)[0])
    sidecar = yaml.safe_load((root / 'contracts/operators/linear-operator.yaml').read_text())
    assert embedded == {k: v for k, v in sidecar.items() if k not in ('source', 'model', 'description')}
    usage = yaml.safe_load((root / 'clients/linear/USAGE.yml').read_text())['linear_client_usage']['project_operations']
    for command in ['get-project', 'create-project', 'assign-issue-project']:
        assert command in text
        assert command in {row['task'] for row in sidecar['outputs']}
        assert any(command in value for value in usage.values())


def test_cli_assignment_full_transport(monkeypatch, capsys):
    def remote_issue(project_id):
        value = issue(project_id)
        value['project']['teams'] = {'nodes': [{'id': TEAM}]}
        value['labels'] = {'nodes': value['labels']}
        return {'data': {'issue': value}}

    monkeypatch.setenv('LINEAR_API_KEY', 'mock-key')
    _, calls = transport(monkeypatch, [read(), remote_issue(OTHER),
        {'data': {'issueUpdate': {'success': True, 'issue': None}}}, remote_issue(PROJECT)])
    cli.main(['assign-issue-project', 'AGE-353', '--project-id', PROJECT])
    result = json.loads(capsys.readouterr().out)
    assert result['ok']
    assert calls[1]['variables'] == {'issueId': 'AGE-353'}
    assert calls[2]['variables'] == {'id': ISSUE, 'input': {'projectId': PROJECT}}
    assert calls[3]['variables'] == {'issueId': ISSUE}
    assert result['data']['observedIssue']['description'] == 'Unchanged'


@pytest.mark.parametrize('initial', [{**issue(), 'id': OTHER},
    {**issue(), 'project': {}}, {**issue(), 'project': False}])
def test_bad_initial_identity_or_project_prevents_patch(monkeypatch, initial):
    if initial['id'] == OTHER:
        initial['identifier'] = 'AGE-999'
    client, calls, _ = assignment_client(monkeypatch, initial=initial)
    result = assign_issue_project(client, 'AGE-353', PROJECT)
    assert not result['ok']
    assert result['data']['mutation'] == 'not_attempted'
    assert len(calls) == 1


def test_project_id_collision_blocks_even_with_different_name(monkeypatch):
    p = project()
    p['name'] = 'Unrelated name'
    client, calls = transport(monkeypatch, [page([p])])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert result['error']['code'] == 'PROJECT_CANDIDATES'
    assert len(calls) == 1


def test_missing_nullable_fields_are_not_inferred(monkeypatch):
    p = project()
    del p['archivedAt']
    client, calls = transport(monkeypatch, [page([p])])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert not result['ok']
    assert len(calls) == 1


@pytest.mark.parametrize('project_id', [NAME, '11111111-1111-1111-8111-111111111111'])
def test_creation_requires_uuid_v4_before_any_transport(monkeypatch, project_id):
    client, calls = transport(monkeypatch, [])
    result = create_project(client, NAME, TEAM, project_id)
    assert not result['ok']
    assert not calls


class InterruptedBody(io.BytesIO):
    """Fail on response.read(), not on opening the request."""

    def __init__(self, error):
        super().__init__()
        self.error = error

    def read(self, *args, **kwargs):
        raise self.error


def remote_issue_response(project_id):
    value = issue(project_id)
    value['project']['teams'] = {'nodes': [{'id': TEAM}]}
    value['labels'] = {'nodes': value['labels']}
    return {'data': {'issue': value}}


@pytest.mark.parametrize('operation', ['create', 'assignment'])
@pytest.mark.parametrize('stage', ['mutation', 'readback'])
@pytest.mark.parametrize('error', [http.client.IncompleteRead(b'{"data":', 100),
    http.client.RemoteDisconnected('connection closed'), ConnectionResetError('reset')])
def test_cli_interrupted_body_retains_progress(monkeypatch, capsys, operation, stage, error):
    monkeypatch.setenv('LINEAR_API_KEY', 'mock-key')
    broken = InterruptedBody(error)
    if operation == 'create':
        responses = [page(), broken] if stage == 'mutation' else [page(), created(), broken]
        args = ['create-project', '--name', NAME, '--team-id', TEAM, '--project-id', PROJECT]
        mutation_index = 1
    else:
        responses = [read(), remote_issue_response(OTHER), broken]
        if stage == 'readback':
            responses = [read(), remote_issue_response(OTHER),
                {'data': {'issueUpdate': {'success': True, 'issue': None}}}, broken]
        args = ['assign-issue-project', 'AGE-353', '--project-id', PROJECT]
        mutation_index = 2
    _, calls = transport(monkeypatch, responses)
    with pytest.raises(SystemExit) as exit:
        cli.main(args)
    assert exit.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result['ok'] is False
    assert result['error']['code'] == 'API_ERROR'
    progress = result['data']
    assert progress['projectId'] == PROJECT
    assert progress['mutation'] == ('unknown' if stage == 'mutation' else 'acknowledged')
    assert progress['readback'] == ('not_attempted' if stage == 'mutation' else 'unverified')
    assert len(calls) == len(responses)  # No retry, follow-on read after unknown, or rollback.
    if operation == 'create':
        assert progress['teamId'] == TEAM
        assert progress['name'] == NAME
        assert calls[mutation_index]['variables'] == {
            'input': {'id': PROJECT, 'name': NAME, 'teamIds': [TEAM]}}
        if stage == 'readback':
            assert calls[-1]['variables'] == {'id': PROJECT}
    else:
        assert progress['requestedIssue'] == 'AGE-353'
        assert progress['issueId'] == ISSUE
        assert progress['initialProjectId'] == OTHER
        assert calls[1]['variables'] == {'issueId': 'AGE-353'}
        assert calls[mutation_index]['variables'] == {'id': ISSUE, 'input': {'projectId': PROJECT}}
        if stage == 'readback':
            assert calls[-1]['variables'] == {'issueId': ISSUE}


@pytest.mark.parametrize('error', [TypeError('programming error'), ValueError('programming error')])
def test_transport_does_not_hide_programming_errors(monkeypatch, error):
    client, calls = transport(monkeypatch, [page(), InterruptedBody(error)])
    with pytest.raises(type(error), match='programming error'):
        create_project(client, NAME, TEAM, PROJECT)
    assert len(calls) == 2


@pytest.mark.parametrize('team_id', [None, TEAM])
@pytest.mark.parametrize('include_archived', [False, True])
def test_inventory_small_pages_preserve_variants_archive_and_later_candidates(
    monkeypatch, team_id, include_archived,
):
    first = project()
    first.update(id=OTHER, name='Different project')
    later = project()
    if include_archived:
        later['archivedAt'] = '2026-01-01'
    client, calls = transport(monkeypatch, [
        page([first], next_page=True, cursor='page-2'),
        page([later], next_page=True, cursor='page-3'),
        page(),
    ])
    inventory = client.list_projects(team_id=team_id, include_archived=include_archived)
    assert [p['id'] for p in inventory] == [OTHER, PROJECT]
    assert inventory[1]['name'] == NAME
    assert inventory[1]['archivedAt'] == later['archivedAt']
    assert inventory[1]['teams'] == later['teams']['nodes']
    expected = {'first': 1, 'includeArchived': include_archived}
    if team_id is not None:
        expected['teamId'] = TEAM
    assert [call['variables'] for call in calls] == [
        expected, {**expected, 'after': 'page-2'}, {**expected, 'after': 'page-3'}]
    for call in calls:
        query = call['query']
        assert ('accessibleTeams:' in query) == (team_id is not None)
        assert 'teams(first: 100)' in query
        assert 'pageInfo { hasNextPage endCursor }' in query
        assert 'first: $first' in query
        assert 'includeArchived: $includeArchived' in query
        assert 'after: $after' in query
        assert 'mutation' not in query


@pytest.mark.parametrize('team_id', [None, TEAM])
@pytest.mark.parametrize('cursors', [[None], [''], [42], ['a', 'a'], ['a', 'b', 'a']])
def test_small_page_cursor_errors_both_inventory_variants(monkeypatch, team_id, cursors):
    client, calls = transport(monkeypatch, [page(next_page=True, cursor=c) for c in cursors])
    with pytest.raises(LinearClientError) as error:
        client.list_projects(team_id=team_id, include_archived=True)
    assert error.value.code == 'PAGINATION_ERROR'
    assert len(calls) == len(cursors)
    assert all(call['variables']['first'] == 1 for call in calls)


@pytest.mark.parametrize('team_id', [None, TEAM])
def test_small_pages_reject_later_incomplete_team_membership(monkeypatch, team_id):
    later = project()
    later['teams']['pageInfo']['hasNextPage'] = True
    client, calls = transport(monkeypatch, [
        page(next_page=True, cursor='later'), page([later])])
    with pytest.raises(LinearClientError) as error:
        client.list_projects(team_id=team_id, include_archived=True)
    assert error.value.code == 'INVALID_RESPONSE'
    assert len(calls) == 2


@pytest.mark.parametrize('match', ['name', 'id'])
@pytest.mark.parametrize('archived', [False, True])
def test_one_project_pages_later_candidate_blocks_creation(monkeypatch, match, archived):
    first = project()
    first.update(id=OTHER, name='Different project')
    later = project()
    if match == 'name':
        later['id'] = ISSUE
    else:
        later['name'] = 'Different name with retained ID'
    if archived:
        later['archivedAt'] = '2026-01-01'
    client, calls = transport(monkeypatch, [
        page([first], next_page=True, cursor='later'), page([later])])
    result = create_project(client, NAME, TEAM, PROJECT)
    assert result['error']['code'] == 'PROJECT_CANDIDATES'
    assert result['data']['mutation'] == 'not_attempted'
    assert result['data']['readback'] == 'not_attempted'
    assert [p['id'] for p in result['data']['candidates']] == [later['id']]
    assert [call['variables'] for call in calls] == [
        {'first': 1, 'includeArchived': True},
        {'first': 1, 'includeArchived': True, 'after': 'later'}]
    assert all('mutation' not in call['query'] for call in calls)
