import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clients.linear import cli
from clients.linear.client import LinearClientError


ISSUE_FIXTURE = [
    {
        "id": "issue-uuid",
        "identifier": "NES-227",
        "title": "Add Linear issue search",
        "url": "https://linear.app/acme/issue/NES-227/add-linear-issue-search",
        "state": {"id": "state-uuid", "name": "In Progress", "type": "started"},
        "team": {"id": "team-uuid", "key": "NES", "name": "NES"},
        "labels": [{"id": "label-uuid", "name": "agent-runner"}],
    }
]


def patched_client(search_result: list[dict[str, object]] | None = None) -> MagicMock:
    mock_client = MagicMock()
    mock_client.search_issues.return_value = search_result if search_result is not None else []
    return mock_client


def stdout_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    return json.loads(captured.out)


def run_main_with_mock_client(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    search_result: list[dict[str, object]] | None = None,
) -> tuple[MagicMock, dict[str, object]]:
    mock_client = patched_client(search_result)
    with patch("clients.linear.cli.LinearClient", return_value=mock_client):
        with patch.object(sys, "argv", argv):
            cli.main()

    return mock_client, stdout_json(capsys)


def test_wrapper_success_writes_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    mock_client = patched_client(ISSUE_FIXTURE)

    with patch("clients.linear.cli.LinearClient", return_value=mock_client):
        cli.search_issues(team_key="NES")

    result = stdout_json(capsys)
    assert result == {"ok": True, "data": ISSUE_FIXTURE}


def test_wrapper_passes_kwargs_through(capsys: pytest.CaptureFixture[str]) -> None:
    mock_client = patched_client(ISSUE_FIXTURE)

    with patch("clients.linear.cli.LinearClient", return_value=mock_client):
        cli.search_issues(
            team_key="NES",
            team_id=None,
            title_contains="search",
            title_starts_with="NES-",
            labels=["agent-runner", "prereq"],
            include_archived=True,
            first=25,
        )

    mock_client.search_issues.assert_called_once_with(
        team_key="NES",
        team_id=None,
        title_contains="search",
        title_starts_with="NES-",
        label_names=["agent-runner", "prereq"],
        include_archived=True,
        first=25,
    )
    assert stdout_json(capsys)["ok"] is True


def test_wrapper_does_not_swallow_linear_client_error() -> None:
    mock_client = patched_client()
    mock_client.search_issues.side_effect = LinearClientError("API_ERROR", "boom")

    with patch("clients.linear.cli.LinearClient", return_value=mock_client):
        with pytest.raises(LinearClientError) as exc_info:
            cli.search_issues(team_key="NES")

    assert exc_info.value.code == "API_ERROR"


def test_main_search_issues_success(capsys: pytest.CaptureFixture[str]) -> None:
    mock_client, result = run_main_with_mock_client(
        ["linear", "search-issues", "--team-key", "NES"], capsys, ISSUE_FIXTURE
    )

    mock_client.search_issues.assert_called_once_with(
        team_key="NES",
        team_id=None,
        title_contains=None,
        title_starts_with=None,
        label_names=None,
        include_archived=False,
        first=50,
    )
    assert result == {"ok": True, "data": ISSUE_FIXTURE}


def test_main_search_issues_linear_client_error(capsys: pytest.CaptureFixture[str]) -> None:
    mock_client = patched_client()
    mock_client.search_issues.side_effect = LinearClientError("API_ERROR", "msg")

    with patch("clients.linear.cli.LinearClient", return_value=mock_client):
        with (
            patch.object(sys, "argv", ["linear", "search-issues", "--team-key", "NES"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            cli.main()

    assert exc_info.value.code == 1
    result = stdout_json(capsys)
    assert result["ok"] is False
    assert result["error"]["code"] == "API_ERROR"
    assert result["error"]["message"] == "msg"


def test_main_search_issues_missing_team_flags_exits_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch.object(sys, "argv", ["linear", "search-issues"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.main()

    assert exc_info.value.code == 2
    result = stdout_json(capsys)
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_INPUT"


def test_main_search_issues_conflicting_team_flags_exits_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        patch.object(
            sys,
            "argv",
            ["linear", "search-issues", "--team-key", "NES", "--team-id", "uuid"],
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.main()

    assert exc_info.value.code == 2
    result = stdout_json(capsys)
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.parametrize(
    ("labels_arg", "expected_label_names"),
    [
        ("a,b,c", ["a", "b", "c"]),
        (" a, b ,, c ", ["a", "b", "c"]),
        ("x", ["x"]),
        (None, None),
    ],
)
def test_main_search_issues_labels_normalization(
    labels_arg: str | None,
    expected_label_names: list[str] | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["linear", "search-issues", "--team-key", "NES"]
    if labels_arg is not None:
        argv.extend(["--labels", labels_arg])

    mock_client, _ = run_main_with_mock_client(argv, capsys)

    assert mock_client.search_issues.call_args.kwargs["label_names"] == expected_label_names


@pytest.mark.parametrize(
    ("argv", "expected_include_archived"),
    [
        (["linear", "search-issues", "--team-key", "NES", "--include-archived"], True),
        (["linear", "search-issues", "--team-key", "NES"], False),
    ],
)
def test_main_search_issues_include_archived_toggle(
    argv: list[str],
    expected_include_archived: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_client, _ = run_main_with_mock_client(argv, capsys)

    assert mock_client.search_issues.call_args.kwargs["include_archived"] is expected_include_archived


@pytest.mark.parametrize("first", [25, 0, 200])
def test_main_search_issues_first_passthrough(
    first: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_client, _ = run_main_with_mock_client(
        ["linear", "search-issues", "--team-key", "NES", "--first", str(first)],
        capsys,
    )

    assert mock_client.search_issues.call_args.kwargs["first"] == first


def test_main_search_issues_help_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["linear", "search-issues", "--help"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.main()

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    for flag in [
        "--team-key",
        "--team-id",
        "--title-contains",
        "--title-starts-with",
        "--labels",
        "--include-archived",
        "--first",
    ]:
        assert flag in help_text


def test_search_files_do_not_patch_scripts_clients_linear_cli() -> None:
    forbidden = "scripts.clients." + "linear_cli"
    repo_root = Path(__file__).resolve().parents[3]
    test_files = [
        repo_root / "clients/linear/tests/test_search_issues_unit.py",
        repo_root / "clients/linear/tests/test_cli_search_issues_unit.py",
    ]

    for test_file in test_files:
        assert forbidden not in test_file.read_text(encoding="utf-8")
