import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pytest_mock import MockerFixture

from clients.linear import cli
from clients.linear.client import LinearClient, LinearClientError


REPO_ROOT = Path(__file__).resolve().parents[3]
USAGE = REPO_ROOT / "clients" / "linear" / "USAGE.yml"


def _issue_response(estimate: int | None) -> dict:
    return {
        "data": {
            "issue": {
                "id": "issue-uuid",
                "identifier": "ACR-122",
                "title": "Estimate refinement",
                "description": "Ticket body",
                "url": "https://linear.app/acme/issue/ACR-122",
                "branchName": "acr-122-estimate-refinement",
                "priority": 2,
                "estimate": estimate,
                "createdAt": "2026-05-08T00:00:00Z",
                "updatedAt": "2026-05-08T01:00:00Z",
                "completedAt": None,
                "canceledAt": None,
                "dueDate": None,
                "team": {"id": "team-uuid", "name": "ACR", "key": "ACR"},
                "assignee": None,
                "state": None,
                "project": None,
                "labels": {"nodes": []},
                "parent": None,
                "comments": {"totalCount": 0},
                "children": {"totalCount": 0},
            }
        }
    }


def _issue_update_response() -> dict:
    return {
        "data": {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "ACR-122",
                    "title": "Estimate refinement",
                    "url": "https://linear.app/acme/issue/ACR-122",
                    "updatedAt": "2026-05-08T02:00:00Z",
                },
            }
        }
    }


def test_get_issue_returns_non_null_estimate(mocker: MockerFixture) -> None:
    client = LinearClient(api_key="test_key")
    mocker.patch.object(client, "_run_graphql", return_value=_issue_response(13))

    result = client.get_issue("ACR-122")

    assert result["estimate"] == 13


def test_update_issue_accepts_estimate_and_sends_issue_update_input(
    mocker: MockerFixture,
) -> None:
    client = LinearClient(api_key="test_key")
    run_graphql = mocker.patch.object(
        client,
        "_run_graphql",
        return_value=_issue_update_response(),
    )

    client.update_issue(issue_id="ACR-122", estimate=8)

    assert run_graphql.call_args.args[1] == {
        "id": "ACR-122",
        "input": {"estimate": 8},
    }


def test_update_issue_omits_estimate_when_not_supplied(
    mocker: MockerFixture,
) -> None:
    client = LinearClient(api_key="test_key")
    run_graphql = mocker.patch.object(
        client,
        "_run_graphql",
        return_value=_issue_update_response(),
    )

    client.update_issue(issue_id="ACR-122", description="Updated body")

    issue_input = run_graphql.call_args.args[1]["input"]
    assert issue_input == {"description": "Updated body"}
    assert "estimate" not in issue_input


def test_update_issue_rejects_non_fibonacci_estimate() -> None:
    client = LinearClient(api_key="test_key")

    with pytest.raises(LinearClientError) as exc_info:
        client.update_issue(issue_id="ACR-122", estimate=4)

    assert exc_info.value.code == "INVALID_INPUT"
    message = exc_info.value.message.lower()
    assert "fibonacci" in message or "allowed" in message


def test_update_issue_allows_estimate_only_update(mocker: MockerFixture) -> None:
    client = LinearClient(api_key="test_key")
    run_graphql = mocker.patch.object(
        client,
        "_run_graphql",
        return_value=_issue_update_response(),
    )

    result = client.update_issue(issue_id="ACR-122", estimate=13)

    assert result["identifier"] == "ACR-122"
    assert run_graphql.call_args.args[1]["input"] == {"estimate": 13}


def test_cli_update_issue_passes_estimate_to_client(capsys: pytest.CaptureFixture[str]) -> None:
    mock_issue = {
        "id": "issue-uuid",
        "identifier": "ACR-122",
        "title": "Estimate refinement",
        "url": "https://linear.app/acme/issue/ACR-122",
        "updatedAt": "2026-05-08T02:00:00Z",
    }

    with patch("clients.linear.cli.LinearClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.update_issue.return_value = mock_issue
        mock_client_class.return_value = mock_client

        with patch.object(
            sys,
            "argv",
            ["linear", "update-issue", "ACR-122", "--estimate", "13"],
        ):
            cli.main()

        mock_client.update_issue.assert_called_once_with(
            issue_id="ACR-122",
            estimate=13,
        )
        assert json.loads(capsys.readouterr().out)["ok"] is True


def test_cli_update_issue_omits_estimate_when_not_supplied(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_issue = {
        "id": "issue-uuid",
        "identifier": "ACR-122",
        "title": "Estimate refinement",
        "url": "https://linear.app/acme/issue/ACR-122",
        "updatedAt": "2026-05-08T02:00:00Z",
    }

    with patch("clients.linear.cli.LinearClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.update_issue.return_value = mock_issue
        mock_client_class.return_value = mock_client

        with patch.object(
            sys,
            "argv",
            [
                "linear",
                "update-issue",
                "ACR-122",
                "--description",
                "Updated description",
            ],
        ):
            cli.main()

        kwargs = mock_client.update_issue.call_args.kwargs
        assert kwargs == {
            "issue_id": "ACR-122",
            "description": "Updated description",
        }
        assert "estimate" not in kwargs
        assert json.loads(capsys.readouterr().out)["ok"] is True


def test_usage_yml_update_issue_example_has_estimate_flag() -> None:
    usage = yaml.safe_load(USAGE.read_text(encoding="utf-8"))
    examples = usage["linear_client_usage"]["examples"]

    assert "update_issue" in examples
    example = examples["update_issue"]
    assert "update-issue" in example
    assert "--estimate" in example
    assert "13" in example or "<int>" in example
