import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clients.linear.cli import (
    get_issue_description,
    main,
    split_plans,
    transition_issue,
    update_issue,
)
from clients.linear.client import LinearClientError


def stdout_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


class TestGetIssueDescription:
    def test_prints_description_when_present(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should print issue description when it exists."""
        mock_issue = {"description": "This is the ticket description."}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            get_issue_description("NES-123")

            captured = capsys.readouterr()
            assert captured.out.strip() == "This is the ticket description."

    def test_prints_empty_when_description_is_none(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should print empty string when description is None."""
        mock_issue = {"description": None}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            get_issue_description("NES-456")

            captured = capsys.readouterr()
            assert captured.out.strip() == ""

    def test_prints_empty_when_description_missing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should print empty string when description key is missing."""
        mock_issue = {}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            get_issue_description("NES-789")

            captured = capsys.readouterr()
            assert captured.out.strip() == ""


class TestSplitPlans:
    def test_splits_multiple_plans(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should split description into separate plan files."""
        description = """Some intro text

---
### Plan 1: First plan
This is the first plan content.

### Plan 2: Second plan
This is the second plan content.
"""
        mock_issue = {"description": description}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            output_dir = tmp_path / "plans"
            split_plans("NES-123", str(output_dir))

            # Check output JSON
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True
            assert result["data"]["count"] == 2

            # Check plan files were created
            plan1 = output_dir / "plan1.md"
            plan2 = output_dir / "plan2.md"
            assert plan1.exists()
            assert plan2.exists()
            assert "First plan" in plan1.read_text()
            assert "Second plan" in plan2.read_text()

    def test_exits_when_no_separator(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should exit with error when no --- separator found."""
        description = "Just some text without separator"
        mock_issue = {"description": description}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            with pytest.raises(SystemExit) as exc_info:
                split_plans("NES-123", str(tmp_path / "plans"))

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is False
            assert result["error"]["code"] == "NO_PLAN"

    def test_exits_when_no_plan_headers(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should exit with error when no Plan headers found after separator."""
        description = """Some intro text

---
This is content but no Plan N: headers
"""
        mock_issue = {"description": description}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            with pytest.raises(SystemExit) as exc_info:
                split_plans("NES-123", str(tmp_path / "plans"))

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is False
            assert result["error"]["code"] == "NO_PLANS"

    def test_handles_single_plan(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Should handle description with a single plan."""
        description = """Intro

---
### Plan 1: Only plan
This is the only plan.
"""
        mock_issue = {"description": description}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            output_dir = tmp_path / "plans"
            split_plans("NES-123", str(output_dir))

            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True
            assert result["data"]["count"] == 1

            plan1 = output_dir / "plan1.md"
            assert plan1.exists()
            assert "Only plan" in plan1.read_text()


class TestUpdateIssue:
    def test_updates_with_inline_description(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should update issue with inline description."""
        mock_issue = {
            "id": "issue-uuid",
            "identifier": "NES-123",
            "title": "Test Issue",
            "url": "https://linear.app/test/issue/NES-123",
            "updatedAt": "2024-01-01T00:00:00Z",
        }

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.update_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            update_issue("NES-123", description="New description")

            mock_client.update_issue.assert_called_once_with(
                issue_id="NES-123", description="New description"
            )
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True
            assert result["data"]["identifier"] == "NES-123"

    def test_updates_from_description_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Should update issue with description from file."""
        # Create description file
        desc_file = tmp_path / "description.md"
        desc_file.write_text("Description from file", encoding="utf-8")

        mock_issue = {
            "id": "issue-uuid",
            "identifier": "NES-123",
            "title": "Test Issue",
            "url": "https://linear.app/test/issue/NES-123",
            "updatedAt": "2024-01-01T00:00:00Z",
        }

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.update_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            update_issue("NES-123", description_file=str(desc_file))

            mock_client.update_issue.assert_called_once_with(
                issue_id="NES-123", description="Description from file"
            )


class TestTransitionIssue:
    def test_transition_issue_calls_client_primitive(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        transition_result = {
            "issue_id": "issue-uuid",
            "identifier": "ACR-130",
            "beforeStatus": "Todo",
            "afterStatus": "In Progress",
            "stateId": "progress-state",
        }

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.transition_issue.return_value = transition_result
            mock_client_class.return_value = mock_client

            exit_code = transition_issue(
                issue_id="ACR-130",
                target_status="In Progress",
            )

            assert exit_code is None
            mock_client.transition_issue.assert_called_once_with(
                issue_id="ACR-130",
                target_status="In Progress",
            )
            result = stdout_json(capsys)
            assert result == {"ok": True, "data": transition_result}

    def test_main_transition_issue_command_dispatches_to_wrapper(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        transition_result = {
            "issue_id": "issue-uuid",
            "identifier": "ACR-130",
            "beforeStatus": "Todo",
            "afterStatus": "In Progress",
            "stateId": "progress-state",
        }

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.transition_issue.return_value = transition_result
            mock_client_class.return_value = mock_client

            main(
                [
                    "linear",
                    "transition-issue",
                    "ACR-130",
                    "--target-status",
                    "In Progress",
                ]
            )

            mock_client.transition_issue.assert_called_once_with(
                issue_id="ACR-130",
                target_status="In Progress",
            )
            assert stdout_json(capsys)["ok"] is True

    def test_transition_issue_success_prints_json_envelope(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        transition_result = {
            "issue_id": "issue-uuid",
            "identifier": "ACR-130",
            "beforeStatus": "Todo",
            "afterStatus": "Done",
            "stateId": "done-state",
        }

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.transition_issue.return_value = transition_result
            mock_client_class.return_value = mock_client

            exit_code = transition_issue(issue_id="ACR-130", target_status="Done")

            assert exit_code is None
            assert stdout_json(capsys) == {"ok": True, "data": transition_result}

    def test_transition_issue_client_error_propagates_without_catching(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.transition_issue.side_effect = LinearClientError(
                "INVALID_INPUT",
                "target_status must be one of the routine manager-owned states",
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(LinearClientError) as exc_info:
                transition_issue(
                    issue_id="ACR-130",
                    target_status="Backlog",
                )

            assert exc_info.value.code == "INVALID_INPUT"
            assert "target_status" in exc_info.value.message
            assert capsys.readouterr().out == ""

    def test_main_transition_issue_client_error_exits_one(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.transition_issue.side_effect = LinearClientError(
                "INVALID_INPUT",
                "target_status must be one of the routine manager-owned states",
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(SystemExit) as exc_info:
                main(
                    [
                        "linear",
                        "transition-issue",
                        "ACR-130",
                        "--target-status",
                        "Backlog",
                    ]
                )

            assert exc_info.value.code == 1
            result = stdout_json(capsys)
            assert result["ok"] is False
            assert result["error"]["code"] == "INVALID_INPUT"
            assert "target_status" in result["error"]["message"]

    def test_transition_issue_missing_target_status_is_argparse_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["linear", "transition-issue", "ACR-130"])

        assert exc_info.value.code == 2
        result = stdout_json(capsys)
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_INPUT"
        assert "--target-status" in result["error"]["message"]


class TestMain:
    def test_get_issue_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call get_issue with issue_id argument."""
        mock_issue = {"id": "uuid", "identifier": "NES-123", "title": "Test"}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "get-issue", "NES-123"]):
                main()

            mock_client.get_issue.assert_called_once_with("NES-123")
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True

    def test_get_issue_description_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call get_issue_description with issue_id argument."""
        mock_issue = {"description": "Test description"}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "get-issue-description", "NES-123"]):
                main()

            captured = capsys.readouterr()
            assert captured.out.strip() == "Test description"

    def test_split_plans_command(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call split_plans with issue_id and output_dir arguments."""
        description = """Intro

---
### Plan 1: Test
Content
"""
        mock_issue = {"description": description}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            output_dir = tmp_path / "plans"
            with patch.object(
                sys,
                "argv",
                ["linear", "split-plans", "NES-123", "--output-dir", str(output_dir)],
            ):
                main()

            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True

    def test_list_projects_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call list_projects."""
        mock_projects = [{"id": "proj-1", "name": "Project 1"}]

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_projects.return_value = mock_projects
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-projects"]):
                main()

            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True
            assert result["data"]["projects"] == mock_projects

    def test_list_projects_without_team_keeps_workspace_scope(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: hidden client capability at CLI boundary; level: unit.

        Source: ACR-22 proposal Test-Intent T3 and assumptions A2/A3.
        """
        mock_projects = [{"id": "proj-1", "name": "Workspace Project"}]

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_projects.return_value = mock_projects
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-projects"]):
                main()

            mock_client.list_projects.assert_called_once_with(team_id=None)
            result = json.loads(capsys.readouterr().out)
            assert result["ok"] is True
            assert result["data"]["projects"] == mock_projects

    def test_list_projects_with_team_forwards_team_key(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: hidden client capability at CLI boundary; level: unit.

        Source: ACR-22 proposal Test-Intent T3 and assumptions A2/A3.
        """
        mock_projects = [{"id": "proj-ast", "name": "AST Project"}]

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_projects.return_value = mock_projects
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-projects", "--team", "AST"]):
                main()

            mock_client.list_projects.assert_called_once_with(team_id="AST")
            result = json.loads(capsys.readouterr().out)
            assert result == {"ok": True, "data": {"projects": mock_projects}}

    def test_list_teams_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call list_teams."""
        mock_teams = [{"id": "team-1", "name": "Team 1"}]

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_teams.return_value = mock_teams
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-teams"]):
                main()

            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True
            assert result["data"]["teams"] == mock_teams

    def test_list_labels_forwards_ast_team(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        mock_labels = [{"id": "label-x", "name": "hardening"}]

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_labels.return_value = mock_labels
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-labels", "--team", "AST"]):
                main()

            mock_client.list_labels.assert_called_once_with(team="AST")
            assert json.loads(capsys.readouterr().out) == {
                "ok": True,
                "data": mock_labels,
            }

    def test_create_label_forwards_ast_team_and_label_fields(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        mock_label = {"id": "label-x", "name": "hardening"}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.create_label.return_value = mock_label
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "create-label",
                    "--team",
                    "AST",
                    "--name",
                    "hardening",
                    "--color",
                    "#abc",
                    "--description",
                    "Coverage label",
                ],
            ):
                main()

            mock_client.create_label.assert_called_once_with(
                team="AST",
                name="hardening",
                color="#abc",
                description="Coverage label",
            )
            assert json.loads(capsys.readouterr().out)["data"] == mock_label

    def test_apply_labels_forwards_ast_team_and_merge_flags(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        mock_result = {"id": "issue-uuid", "labels": [{"id": "label-x"}]}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.apply_labels.return_value = mock_result
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "apply-labels",
                    "AST-12",
                    "--team",
                    "AST",
                    "--labels",
                    "hardening,prereq",
                    "--create-missing",
                    "--replace",
                ],
            ):
                main()

            mock_client.apply_labels.assert_called_once_with(
                issue_id="AST-12",
                team="AST",
                label_names=["hardening", "prereq"],
                create_missing=True,
                replace=True,
            )
            assert json.loads(capsys.readouterr().out)["data"] == mock_result

    def test_list_comments_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call list_comments with issue_id argument."""
        mock_comments = {"comments": [{"id": "comment-1", "body": "Hello"}]}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_comments.return_value = mock_comments
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-comments", "NES-123"]):
                main()

            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True
            assert result["data"]["comments"] == mock_comments["comments"]

    def test_create_issue_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call create_issue with required arguments."""
        mock_issue = {"id": "uuid", "identifier": "NES-124", "title": "New Issue"}

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
                    "NES",
                    "--title",
                    "New Issue",
                    "--description",
                    "Issue description",
                ],
            ):
                main()

            mock_client.create_issue.assert_called_once_with(
                team="NES",
                title="New Issue",
                description="Issue description",
                project_id=None,
                label_ids=None,
            )
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True

    def test_create_issue_ast_without_labels_does_not_resolve_or_default_labels(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: NES default + agent-runner routing in CLI; level: unit.

        Source: ACR-22 proposal Test-Intent T7 and assumptions A2/A6/A7.
        """
        mock_issue = {"id": "uuid", "identifier": "AST-124", "title": "T"}

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
                    "AST",
                    "--title",
                    "T",
                    "--description",
                    "D",
                ],
            ):
                main()

            mock_client.resolve_label_ids.assert_not_called()
            mock_client.create_issue.assert_called_once_with(
                team="AST",
                title="T",
                description="D",
                project_id=None,
                label_ids=None,
            )
            assert json.loads(capsys.readouterr().out)["ok"] is True

    def test_create_issue_ast_labels_resolve_before_create(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: NES default + agent-runner routing in CLI; level: unit.

        Source: ACR-22 proposal Test-Intent T7 and assumptions A2/A6/A7.
        """
        mock_issue = {"id": "uuid", "identifier": "AST-125", "title": "T"}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.resolve_label_ids.return_value = ["label-x", "label-y"]
            mock_client.create_issue.return_value = mock_issue
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "create-issue",
                    "--team",
                    "AST",
                    "--title",
                    "T",
                    "--description",
                    "D",
                    "--label",
                    "x, y",
                    "--create-missing-labels",
                ],
            ):
                main()

            mock_client.resolve_label_ids.assert_called_once_with(
                "AST",
                ["x", "y"],
                create_missing=True,
            )
            mock_client.create_issue.assert_called_once_with(
                team="AST",
                title="T",
                description="D",
                project_id=None,
                label_ids=["label-x", "label-y"],
            )
            assert json.loads(capsys.readouterr().out)["ok"] is True

    def test_no_command_error_lists_issue_and_project_list_commands(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: parser/help drift across command set; level: unit.

        Source: ACR-22 proposal Test-Intent T10 and assumptions A2/A5.
        """
        with (
            patch.object(sys, "argv", ["linear"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code != 0
        result = json.loads(capsys.readouterr().out)
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_INPUT"
        assert "list-issues" in result["error"]["message"]
        assert "list-projects" in result["error"]["message"]

    def test_list_issues_without_team_exits_with_team_required_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Risk: parser/help drift across command set; level: unit.

        Source: ACR-22 proposal Test-Intent T10 and assumptions A2/A5.
        """
        with (
            patch.object(sys, "argv", ["linear", "list-issues"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 2
        result = json.loads(capsys.readouterr().out)
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_INPUT"
        assert "--team" in result["error"]["message"]

    def test_update_issue_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call update_issue with issue_id and description."""
        mock_issue = {
            "id": "uuid",
            "identifier": "NES-123",
            "title": "Updated",
            "url": "https://linear.app/NES-123",
            "updatedAt": "2024-01-01T00:00:00Z",
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
                    "NES-123",
                    "--description",
                    "Updated description",
                ],
            ):
                main()

            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True

    def test_create_comment_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should call create_comment with issue_id and body."""
        mock_comment = {"id": "comment-uuid", "body": "Comment text"}

        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.create_comment.return_value = mock_comment
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "create-comment",
                    "NES-123",
                    "--body",
                    "Comment text",
                ],
            ):
                main()

            mock_client.create_comment.assert_called_once_with(
                issue_id="NES-123", body="Comment text"
            )
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is True

    def test_handles_linear_client_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Should catch LinearClientError and output JSON error."""
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issue.side_effect = LinearClientError("NOT_FOUND", "Issue not found")
            mock_client_class.return_value = mock_client

            with (
                patch.object(sys, "argv", ["linear", "get-issue", "NES-999"]),
                pytest.raises(SystemExit) as exc_info,
            ):
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["ok"] is False
            assert result["error"]["code"] == "NOT_FOUND"
            assert result["error"]["message"] == "Issue not found"

    def test_acr113_create_issue_resolves_project_and_labels_before_create(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T12: create-issue resolves the full (team, project, labels) tuple first."""
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.resolve_project_id.return_value = "project-uuid"
            mock_client.resolve_label_ids.return_value = ["label-hardening", "label-bug"]
            mock_client.create_issue.return_value = {
                "id": "issue-uuid",
                "identifier": "AST-1",
                "title": "Tuple create",
            }
            mock_client.get_issue.return_value = {
                "id": "issue-uuid",
                "identifier": "AST-1",
                "labels": [{"id": "label-hardening", "name": "hardening"}],
            }
            mock_client.apply_labels.return_value = {"id": "issue-uuid"}
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "create-issue",
                    "--team",
                    "AST",
                    "--project",
                    "acr-strategy",
                    "--label",
                    "hardening,Bug",
                    "--title",
                    "Tuple create",
                ],
            ):
                main()

            method_names = [call[0] for call in mock_client.method_calls]
            assert method_names.index("resolve_project_id") < method_names.index(
                "resolve_label_ids"
            )
            assert method_names.index("resolve_label_ids") < method_names.index("create_issue")
            mock_client.resolve_project_id.assert_called_once_with("AST", "acr-strategy")
            mock_client.resolve_label_ids.assert_called_once_with(
                "AST", ["hardening", "Bug"], create_missing=False
            )
            mock_client.create_issue.assert_called_once_with(
                team="AST",
                title="Tuple create",
                description=None,
                project_id="project-uuid",
                label_ids=["label-hardening", "label-bug"],
            )
            mock_client.get_issue.assert_called_once_with("issue-uuid")
            mock_client.apply_labels.assert_called_once_with(
                issue_id="issue-uuid",
                team="AST",
                label_names=["hardening", "Bug"],
                create_missing=False,
                replace=False,
            )
            assert stdout_json(capsys)["ok"] is True

    def test_acr113_create_issue_label_resolution_failure_aborts_create(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T12: label resolution failure stops before issueCreate."""
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.resolve_project_id.return_value = "project-uuid"
            mock_client.resolve_label_ids.side_effect = LinearClientError(
                "NOT_FOUND", "Label not found on team AST: missing"
            )
            mock_client_class.return_value = mock_client

            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "linear",
                        "create-issue",
                        "--team",
                        "AST",
                        "--project",
                        "acr-strategy",
                        "--label",
                        "missing",
                        "--title",
                        "Tuple create",
                    ],
                ),
                pytest.raises(SystemExit) as exc_info,
            ):
                main()

            assert exc_info.value.code == 1
            mock_client.create_issue.assert_not_called()
            result = stdout_json(capsys)
            assert result["ok"] is False
            assert result["error"]["code"] == "NOT_FOUND"

    def test_acr113_list_labels_command_returns_json_envelope(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T13: list-labels forwards team and returns the standard envelope."""
        labels = [{"id": "label-hardening", "name": "hardening"}]
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_labels.return_value = labels
            mock_client_class.return_value = mock_client

            with patch.object(sys, "argv", ["linear", "list-labels", "--team", "ACR"]):
                main()

            mock_client.list_labels.assert_called_once_with(team="ACR")
            assert stdout_json(capsys) == {"ok": True, "data": labels}

    def test_acr113_create_label_command_returns_json_envelope(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T13: create-label forwards team/name/options and returns the standard envelope."""
        label = {"id": "label-new", "name": "new-label"}
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.create_label.return_value = label
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "create-label",
                    "--team",
                    "ACR",
                    "--name",
                    "new-label",
                    "--color",
                    "#5e6ad2",
                    "--description",
                    "desc",
                ],
            ):
                main()

            mock_client.create_label.assert_called_once_with(
                team="ACR", name="new-label", color="#5e6ad2", description="desc"
            )
            assert stdout_json(capsys) == {"ok": True, "data": label}

    def test_acr113_apply_labels_command_preserves_plural_labels_flag(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T13: apply-labels keeps --labels plural and forwards merge options."""
        result = {"id": "issue-uuid", "labels": [{"id": "label-hardening"}]}
        with patch("clients.linear.cli.LinearClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.apply_labels.return_value = result
            mock_client_class.return_value = mock_client

            with patch.object(
                sys,
                "argv",
                [
                    "linear",
                    "apply-labels",
                    "ACR-1",
                    "--team",
                    "ACR",
                    "--labels",
                    "hardening,Bug",
                    "--create-missing",
                    "--replace",
                ],
            ):
                main()

            mock_client.apply_labels.assert_called_once_with(
                issue_id="ACR-1",
                team="ACR",
                label_names=["hardening", "Bug"],
                create_missing=True,
                replace=True,
            )
            assert stdout_json(capsys) == {"ok": True, "data": result}

    def test_acr113_no_command_error_lists_registered_command_inventory(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """T19: no-command error names every supported parser subcommand."""
        with (
            patch.object(sys, "argv", ["linear"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 2
        result = stdout_json(capsys)
        message = result["error"]["message"]
        for command in [
            "get-issue",
            "get-issue-description",
            "split-plans",
            "create-issue",
            "update-issue",
            "comment",
            "create-comment",
            "get-comment",
            "upsert-comment",
            "list-issues",
            "list-projects",
            "list-labels",
            "create-label",
            "transition-issue",
            "apply-labels",
            "search-issues",
        ]:
            assert command in message
