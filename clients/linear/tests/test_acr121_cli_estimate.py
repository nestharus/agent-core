import inspect
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from clients.linear import cli


REPO_ROOT = Path(__file__).resolve().parents[3]
USAGE = REPO_ROOT / "clients" / "linear" / "USAGE.yml"


def _stdout_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_usage_yml_create_example_has_estimate_flag() -> None:
    text = USAGE.read_text(encoding="utf-8")

    assert "create_issue:" in text
    assert "--estimate <int>" in text or "--estimate 5" in text


def test_cli_create_issue_passes_estimate_to_client(capsys) -> None:
    mock_issue = {"id": "issue-uuid", "identifier": "ACR-121", "title": "Estimate"}

    with patch("clients.linear.cli.LinearClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_issue
        mock_client_class.return_value = mock_client

        with patch.object(
            sys,
            "argv",
            [
                "linear",
                "create-issue",
                "--team",
                "ACR",
                "--title",
                "Estimate",
                "--estimate",
                "8",
            ],
        ):
            cli.main()

        mock_client.create_issue.assert_called_once_with(
            team="ACR",
            title="Estimate",
            description=None,
            project_id=None,
            label_ids=None,
            estimate=8,
        )
        assert _stdout_json(capsys)["ok"] is True


def test_cli_create_issue_omits_estimate_when_not_supplied(capsys) -> None:
    signature = inspect.signature(cli.create_issue)
    assert signature.parameters["estimate"].default is None

    mock_issue = {"id": "issue-uuid", "identifier": "ACR-122", "title": "No estimate"}

    with patch("clients.linear.cli.LinearClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_issue
        mock_client_class.return_value = mock_client

        with patch.object(
            sys,
            "argv",
            [
                "linear",
                "create-issue",
                "--team",
                "ACR",
                "--title",
                "No estimate",
            ],
        ):
            cli.main()

        kwargs = mock_client.create_issue.call_args.kwargs
        assert "estimate" not in kwargs
        assert _stdout_json(capsys)["ok"] is True
