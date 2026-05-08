import inspect
import json
import socket
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from clients.linear.client import LinearClient, LinearClientError
from clients.linear.tests.test_client_unit import create_mock_response


TEAM_ID = "11111111-1111-1111-1111-111111111111"
PROJECT_ID = "22222222-2222-2222-2222-222222222222"

SEARCH_ISSUES_QUERY = """query SearchIssues($filter: IssueFilter!, $first: Int!, $includeArchived: Boolean!) {
  issues(filter: $filter, first: $first, includeArchived: $includeArchived) {
    nodes {
      id
      identifier
      title
      url
      state {
        id
        name
        type
      }
      team {
        id
        key
        name
      }
      labels {
        nodes {
          id
          name
        }
      }
    }
  }
}
"""


def issue_node() -> dict[str, Any]:
    return {
        "id": "issue-uuid",
        "identifier": "NES-227",
        "title": "Add Linear issue search",
        "url": "https://linear.app/acme/issue/NES-227/add-linear-issue-search",
        "state": {"id": "state-uuid", "name": "In Progress", "type": "started"},
        "team": {"id": TEAM_ID, "key": "NES", "name": "NES"},
        "labels": {
            "nodes": [
                {"id": "label-1", "name": "agent-runner"},
                {"id": "label-2", "name": "prereq"},
            ]
        },
    }


def issues_response(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    return {"data": {"issues": {"nodes": nodes}}}


def malformed_response(raw: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = raw
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


def captured_graphql_body(mock_urlopen: MagicMock) -> dict[str, Any]:
    request = mock_urlopen.call_args.args[0]
    return json.loads(request.data.decode("utf-8"))


def run_search_and_capture_body(**kwargs: Any) -> dict[str, Any]:
    def resolve_label_ids(
        team: str,
        label_names: list[str],
        create_missing: bool = False,
    ) -> list[str]:
        assert create_missing is False
        assert team in {"NES", TEAM_ID}
        normalized = [name.strip() for name in label_names if name.strip()]
        return [f"label-id-{index}" for index, _ in enumerate(normalized, start=1)]

    client = LinearClient(api_key="test_key")
    with (
        patch.object(LinearClient, "_resolve_team_id", return_value=TEAM_ID),
        patch.object(LinearClient, "resolve_label_ids", side_effect=resolve_label_ids),
        patch.object(LinearClient, "resolve_project_id", return_value=PROJECT_ID, create=True),
        patch("urllib.request.urlopen") as mock_urlopen,
    ):
        mock_urlopen.return_value = create_mock_response(issues_response([]))
        client.search_issues(**kwargs)
        return captured_graphql_body(mock_urlopen)


def assert_error_code(exc_info: pytest.ExceptionInfo[LinearClientError], code: str) -> None:
    assert exc_info.value.code == code


def test_search_issues_signature_is_all_keyword_only() -> None:
    signature = inspect.signature(LinearClient.search_issues)

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        assert parameter.kind == inspect.Parameter.KEYWORD_ONLY


def test_search_issues_neither_team_arg_raises_invalid_input() -> None:
    client = LinearClient(api_key="test_key")

    with patch.object(LinearClient, "_run_graphql") as run_graphql:
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues()

    assert_error_code(exc_info, "INVALID_INPUT")
    run_graphql.assert_not_called()


def test_search_issues_both_team_args_raises_invalid_input() -> None:
    client = LinearClient(api_key="test_key")

    with patch.object(LinearClient, "_run_graphql") as run_graphql:
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_key="NES", team_id=TEAM_ID)

    assert_error_code(exc_info, "INVALID_INPUT")
    run_graphql.assert_not_called()


@pytest.mark.parametrize("first", [0, -1])
def test_search_issues_first_below_range_raises_invalid_input(first: int) -> None:
    client = LinearClient(api_key="test_key")

    with patch.object(LinearClient, "_run_graphql") as run_graphql:
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID, first=first)

    assert_error_code(exc_info, "INVALID_INPUT")
    run_graphql.assert_not_called()


@pytest.mark.parametrize("first", [101, 200])
def test_search_issues_first_above_range_raises_invalid_input(first: int) -> None:
    client = LinearClient(api_key="test_key")

    with patch.object(LinearClient, "_run_graphql") as run_graphql:
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID, first=first)

    assert_error_code(exc_info, "INVALID_INPUT")
    run_graphql.assert_not_called()


def test_search_issues_unknown_team_key_raises_not_found() -> None:
    client = LinearClient(api_key="test_key")

    with (
        patch.object(LinearClient, "_resolve_team_id", return_value=None) as resolve_team_id,
        patch.object(LinearClient, "_run_graphql") as run_graphql,
    ):
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_key="DOES-NOT-EXIST")

    assert_error_code(exc_info, "NOT_FOUND")
    resolve_team_id.assert_called_once_with("DOES-NOT-EXIST")
    run_graphql.assert_not_called()


def test_search_issues_team_id_passthrough_skips_resolution() -> None:
    client = LinearClient(api_key="test_key")

    with (
        patch.object(LinearClient, "_resolve_team_id") as resolve_team_id,
        patch("urllib.request.urlopen") as mock_urlopen,
    ):
        mock_urlopen.return_value = create_mock_response(issues_response([]))
        client.search_issues(team_id=TEAM_ID)

    resolve_team_id.assert_not_called()


def test_search_issues_success_returns_normalized_list() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response(issues_response([issue_node()]))
        result = client.search_issues(team_id=TEAM_ID)

    assert result == [
        {
            "id": "issue-uuid",
            "identifier": "NES-227",
            "title": "Add Linear issue search",
            "url": "https://linear.app/acme/issue/NES-227/add-linear-issue-search",
            "state": {"id": "state-uuid", "name": "In Progress", "type": "started"},
            "team": {"id": TEAM_ID, "key": "NES", "name": "NES"},
            "labels": [
                {"id": "label-1", "name": "agent-runner"},
                {"id": "label-2", "name": "prereq"},
            ],
        }
    ]
    assert set(result[0]) == {"id", "identifier", "title", "url", "state", "team", "labels"}
    assert isinstance(result[0]["labels"], list)


def test_search_issues_empty_result_returns_empty_list() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response({"data": {"issues": {"nodes": []}}})
        result = client.search_issues(team_id=TEAM_ID)

    assert result == []


def test_search_issues_missing_data_issues_returns_empty_list() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response({"data": {}})
        result = client.search_issues(team_id=TEAM_ID)

    assert result == []


def test_search_issues_missing_data_returns_empty_list() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response({})
        result = client.search_issues(team_id=TEAM_ID)

    assert result == []


def test_search_issues_non_list_nodes_returns_empty_list() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response(
            {"data": {"issues": {"nodes": {"not": "a-list"}}}}
        )
        result = client.search_issues(team_id=TEAM_ID)

    assert result == []


def test_search_issues_state_and_team_remain_nested() -> None:
    node = issue_node()
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response(issues_response([node]))
        result = client.search_issues(team_id=TEAM_ID)

    assert result[0]["state"] == node["state"]
    assert result[0]["team"] == node["team"]
    assert isinstance(result[0]["state"], dict)
    assert isinstance(result[0]["team"], dict)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"team_key": "NES"},
        {"team_id": TEAM_ID},
        {"team_key": "NES", "title_contains": "search"},
        {"team_key": "NES", "title_starts_with": "NES"},
        {"team_key": "NES", "label_names": ["a", "b"]},
    ],
)
def test_search_issues_query_string_is_static(kwargs: dict[str, Any]) -> None:
    body = run_search_and_capture_body(**kwargs)

    assert body["query"] == SEARCH_ISSUES_QUERY


def test_search_issues_variables_have_three_keys() -> None:
    body = run_search_and_capture_body(
        team_id=TEAM_ID,
        title_contains="issue",
        label_names=["a"],
        include_archived=True,
        first=25,
    )

    assert set(body["variables"]) == {"filter", "first", "includeArchived"}


def test_search_issues_variables_first_and_includearchived_passthrough() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, include_archived=True, first=25)

    assert body["variables"]["first"] == 25
    assert body["variables"]["includeArchived"] is True


@pytest.mark.parametrize("kwargs", [{"team_key": "NES"}, {"team_id": TEAM_ID}])
def test_search_issues_filter_team_id_eq(kwargs: dict[str, str]) -> None:
    body = run_search_and_capture_body(**kwargs)

    assert body["variables"]["filter"]["team"]["id"]["eq"] == TEAM_ID


def test_search_issues_filter_title_contains_uses_contains_ignore_case() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, title_contains="Issue Fragment")

    assert body["variables"]["filter"]["title"]["containsIgnoreCase"] == "Issue Fragment"


def test_search_issues_filter_title_starts_with_uses_starts_with() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, title_starts_with="NES-")

    assert body["variables"]["filter"]["title"]["startsWith"] == "NES-"


def test_search_issues_label_names_resolve_to_id_in_filter() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, label_names=["a", "b", "c"])

    assert body["variables"]["filter"]["labels"] == {
        "id": {"in": ["label-id-1", "label-id-2", "label-id-3"]}
    }
    assert "and" not in body["variables"]["filter"]


def test_search_issues_label_names_normalizes_whitespace_and_drops_empties() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, label_names=[" a", "", "b ", "  "])

    assert body["variables"]["filter"]["labels"] == {
        "id": {"in": ["label-id-1", "label-id-2"]}
    }


@pytest.mark.parametrize("label_names", [None, []])
def test_search_issues_no_label_names_no_and_key(label_names: list[str] | None) -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, label_names=label_names)

    assert "and" not in body["variables"]["filter"]


def test_search_issues_makes_exactly_one_search_request() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = create_mock_response(issues_response([]))
        client.search_issues(team_id=TEAM_ID)

    assert mock_urlopen.call_count == 1
    body = captured_graphql_body(mock_urlopen)
    assert "issues(filter: $filter, first: $first, includeArchived: $includeArchived)" in body[
        "query"
    ]


def test_search_issues_no_after_cursor_in_variables() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID)

    assert "after" not in body["variables"]


def test_search_issues_graphql_error_propagates() -> None:
    client = LinearClient(api_key="test_key")

    with patch.object(
        LinearClient,
        "_run_graphql",
        side_effect=LinearClientError("GRAPHQL_ERROR", "boom"),
    ):
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID)

    assert_error_code(exc_info, "GRAPHQL_ERROR")


def test_search_issues_api_error_propagates_on_httperror() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.linear.app/graphql", 500, "server error", {}, None
        )
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID)

    assert_error_code(exc_info, "API_ERROR")


def test_search_issues_api_error_propagates_on_urlerror() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID)

    assert_error_code(exc_info, "API_ERROR")


def test_search_issues_api_error_propagates_on_timeout() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = socket.timeout("timed out")
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID)

    assert_error_code(exc_info, "API_ERROR")


def test_search_issues_parse_error_propagates_on_malformed_json() -> None:
    client = LinearClient(api_key="test_key")

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = malformed_response(b"not json")
        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=TEAM_ID)

    assert_error_code(exc_info, "PARSE_ERROR")


def test_search_issues_docstring_lists_all_observable_codes() -> None:
    docstring = LinearClient.search_issues.__doc__ or ""

    for code in ["INVALID_INPUT", "NOT_FOUND", "API_ERROR", "PARSE_ERROR", "GRAPHQL_ERROR"]:
        assert code in docstring


@pytest.mark.parametrize(
    ("kwargs", "expected_filter", "expected_first", "expected_include_archived"),
    [
        (
            {"team_id": TEAM_ID},
            {"team": {"id": {"eq": TEAM_ID}}},
            50,
            False,
        ),
        (
            {"team_id": TEAM_ID, "title_contains": "fragment", "first": 1},
            {
                "team": {"id": {"eq": TEAM_ID}},
                "title": {"containsIgnoreCase": "fragment"},
            },
            1,
            False,
        ),
        (
            {
                "team_id": TEAM_ID,
                "title_starts_with": "NES-",
                "include_archived": True,
                "first": 100,
            },
            {
                "team": {"id": {"eq": TEAM_ID}},
                "title": {"startsWith": "NES-"},
            },
            100,
            True,
        ),
        (
            {
                "team_id": TEAM_ID,
                "title_contains": "fragment",
                "title_starts_with": "NES-",
                "label_names": [" a ", "b"],
                "include_archived": True,
                "first": 25,
            },
            {
                "team": {"id": {"eq": TEAM_ID}},
                "title": {"containsIgnoreCase": "fragment", "startsWith": "NES-"},
                "labels": {"id": {"in": ["label-id-1", "label-id-2"]}},
            },
            25,
            True,
        ),
    ],
)
def test_parameterized_filter_matrix(
    kwargs: dict[str, Any],
    expected_filter: dict[str, Any],
    expected_first: int,
    expected_include_archived: bool,
) -> None:
    body = run_search_and_capture_body(**kwargs)
    assert body["variables"] == {
        "filter": expected_filter,
        "first": expected_first,
        "includeArchived": expected_include_archived,
    }


@pytest.mark.parametrize(
    ("kwargs", "markers"),
    [
        ({"team_id": TEAM_ID, "title_contains": "abc-xyz-fragment"}, ["abc-xyz-fragment"]),
        ({"team_id": TEAM_ID, "title_starts_with": "NES-marker"}, ["NES-marker"]),
        (
            {
                "team_id": TEAM_ID,
                "title_contains": "contains-marker",
                "title_starts_with": "starts-marker",
            },
            ["contains-marker", "starts-marker"],
        ),
    ],
)
def test_graphql_query_uses_variables_not_string_interpolation(
    kwargs: dict[str, Any], markers: list[str]
) -> None:
    body = run_search_and_capture_body(**kwargs)

    assert body["query"] == SEARCH_ISSUES_QUERY
    variables_json = json.dumps(body["variables"])
    for marker in markers:
        assert marker in variables_json
        assert marker not in body["query"]


def test_labels_filter_uses_any_resolved_id_semantics() -> None:
    body = run_search_and_capture_body(team_id=TEAM_ID, label_names=["a", "b"])

    assert body["variables"]["filter"]["labels"] == {
        "id": {"in": ["label-id-1", "label-id-2"]}
    }


def test_acr113_search_issues_resolves_project_and_labels_before_filtering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T8: search emits resolved project/label ID filters, not raw slug or names."""
    client = LinearClient(api_key="test_key")
    run_graphql = MagicMock(return_value=issues_response([]))
    monkeypatch.setattr(client, "_resolve_team_id", MagicMock(return_value=TEAM_ID))
    monkeypatch.setattr(
        client, "resolve_project_id", MagicMock(return_value=PROJECT_ID), raising=False
    )
    monkeypatch.setattr(
        client, "resolve_label_ids", MagicMock(return_value=["lbl_uuid_abc123"])
    )
    monkeypatch.setattr(client, "_run_graphql", run_graphql)

    client.search_issues(
        team_key="ACR",
        project="acr-strategy",
        label_names=["hardening"],
        first=25,
    )

    client.resolve_project_id.assert_called_once_with("ACR", "acr-strategy")
    client.resolve_label_ids.assert_called_once_with(
        "ACR", ["hardening"], create_missing=False
    )
    query, variables = run_graphql.call_args.args
    assert query == SEARCH_ISSUES_QUERY
    assert variables["filter"] == {
        "team": {"id": {"eq": TEAM_ID}},
        "project": {"id": {"eq": PROJECT_ID}},
        "labels": {"id": {"in": ["lbl_uuid_abc123"]}},
    }
    variables_json = json.dumps(variables)
    assert '"acr-strategy"' not in variables_json
    assert '"hardening"' not in variables_json
