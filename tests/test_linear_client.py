from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from clients.linear.cli import verify_issue_description
from clients.linear.client import (
    LinearClient,
    LinearClientError,
    descriptions_match_after_linear_canonicalization,
)


def _client(monkeypatch: pytest.MonkeyPatch) -> LinearClient:
    client = LinearClient(api_key="test-key")
    monkeypatch.setattr(client, "_resolve_team_id", lambda _team: "team-1")
    return client


def _label(name: str, label_id: str, team: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "id": label_id,
        "name": name,
        "color": "#000000",
        "description": None,
        "team": team,
    }


def _page(
    nodes: list[dict[str, Any]], *, has_next: bool, cursor: str | None
) -> dict[str, Any]:
    return {
        "data": {
            "issueLabels": {
                "nodes": nodes,
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            }
        }
    }


def test_list_labels_reads_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    calls: list[dict[str, Any]] = []
    responses = iter(
        [
            _page([_label("first", "label-1")], has_next=True, cursor="cursor-1"),
            _page([_label("hardening", "label-2")], has_next=False, cursor=None),
        ]
    )

    def run(_query: str, variables: dict[str, Any]) -> dict[str, Any]:
        calls.append(variables)
        return next(responses)

    monkeypatch.setattr(client, "_run_graphql", run)

    assert [label["name"] for label in client.list_labels("ACR")] == [
        "first",
        "hardening",
    ]
    assert [call["after"] for call in calls] == [None, "cursor-1"]
    assert all(call["first"] == 50 for call in calls)


@pytest.mark.parametrize(
    "page_info",
    [
        None,
        {"hasNextPage": "yes", "endCursor": "cursor-1"},
        {"hasNextPage": True, "endCursor": None},
    ],
)
def test_list_labels_rejects_malformed_pagination(
    monkeypatch: pytest.MonkeyPatch, page_info: Any
) -> None:
    client = _client(monkeypatch)
    monkeypatch.setattr(
        client,
        "_run_graphql",
        lambda _query, _variables: {
            "data": {"issueLabels": {"nodes": [], "pageInfo": page_info}}
        },
    )

    with pytest.raises(LinearClientError) as error:
        client.list_labels("ACR")

    assert error.value.code == "PAGINATION_ERROR"


def test_list_labels_rejects_repeated_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    responses = iter(
        [
            _page([], has_next=True, cursor="cursor-1"),
            _page([], has_next=True, cursor="cursor-1"),
        ]
    )
    monkeypatch.setattr(client, "_run_graphql", lambda _query, _variables: next(responses))

    with pytest.raises(LinearClientError) as error:
        client.list_labels("ACR")

    assert error.value.code == "PAGINATION_ERROR"


def test_resolve_label_ids_uses_later_page_without_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    responses = iter(
        [
            _page([], has_next=True, cursor="cursor-1"),
            _page(
                [_label("hardening", "label-later", {"id": "team-1"})],
                has_next=False,
                cursor=None,
            ),
        ]
    )
    monkeypatch.setattr(client, "_run_graphql", lambda _query, _variables: next(responses))
    monkeypatch.setattr(
        client,
        "create_label",
        lambda *_args, **_kwargs: pytest.fail("existing label must not be recreated"),
    )

    assert client.resolve_label_ids("ACR", ["hardening"], create_missing=True) == [
        "label-later"
    ]


def test_resolve_label_ids_preserves_team_precedence_and_ambiguity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    team = {"id": "team-1"}
    monkeypatch.setattr(
        client,
        "list_labels",
        lambda _team: [
            _label("shared", "workspace-label"),
            _label("shared", "team-label", team),
        ],
    )
    assert client.resolve_label_ids("ACR", ["shared"]) == ["team-label"]

    monkeypatch.setattr(
        client,
        "list_labels",
        lambda _team: [
            _label("duplicate", "team-a", team),
            _label("duplicate", "team-b", team),
        ],
    )
    with pytest.raises(LinearClientError) as error:
        client.resolve_label_ids("ACR", ["duplicate"])
    assert error.value.code == "AMBIGUOUS_LABEL"


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ("# Heading\n\n- first\n  - nested\n", "# Heading\n\n* first\n  * nested"),
        ("- first\n", "* first\n"),
        ("text\n", "text"),
        ("- first\r\n", "* first"),
    ],
)
def test_description_readback_accepts_observed_linear_canonicalization(
    expected: str, actual: str
) -> None:
    assert descriptions_match_after_linear_canonicalization(expected, actual)


def test_description_readback_tracks_exact_fence_boundary() -> None:
    expected = "````text\n```\n- literal\n````\n- list\n"
    actual = "````text\n```\n- literal\n````\n* list"

    assert descriptions_match_after_linear_canonicalization(expected, actual)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ("# Original\n", "# Changed"),
        ("- first\n", "* second"),
        ("[label](https://example.test/a)\n", "[label](https://example.test/b)"),
        ("text\n\n", "text"),
        ("```text\n- literal\n```\n", "```text\n* literal\n```"),
        ("* first", "- first"),
        ("text", "text\n"),
    ],
)
def test_description_readback_rejects_material_drift(
    expected: str, actual: str
) -> None:
    assert not descriptions_match_after_linear_canonicalization(expected, actual)


def test_description_readback_reports_unreadable_source_as_client_error(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.md"

    with pytest.raises(LinearClientError) as error:
        verify_issue_description("ACR-1", str(missing))

    assert error.value.code == "INVALID_INPUT"
