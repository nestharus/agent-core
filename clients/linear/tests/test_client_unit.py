import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from clients.linear.client import LinearClient, LinearClientError


ACR113_TEAM_ID = "11111111-1111-1111-1111-111111111111"
ACR113_PROJECT_ID = "22222222-2222-2222-2222-222222222222"
ACR113_OTHER_PROJECT_ID = "33333333-3333-3333-3333-333333333333"


def create_mock_response(data: dict[str, Any]) -> MagicMock:
    """Create a mock HTTP response with the given data.

    Args:
        data: Dictionary to return as JSON response body.

    Returns:
        Mock object that behaves like an HTTP response.
    """
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(data).encode("utf-8")
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestLinearClientInit:
    def test_init_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Initialize client from LINEAR_API_KEY environment variable."""
        monkeypatch.setenv("LINEAR_API_KEY", "env_api_key")
        client = LinearClient()
        assert client._api_key == "env_api_key"

    def test_init_from_env_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Initialize client from env variable strips leading/trailing whitespace."""
        monkeypatch.setenv("LINEAR_API_KEY", "  env_api_key  ")
        client = LinearClient()
        assert client._api_key == "env_api_key"

    def test_init_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raise error when no API key is provided or in environment."""
        monkeypatch.delenv("LINEAR_API_KEY", raising=False)
        with pytest.raises(LinearClientError) as exc_info:
            LinearClient()
        assert exc_info.value.code == "MISSING_API_KEY"
        assert "LINEAR_API_KEY must be provided" in exc_info.value.message

    def test_init_raises_for_empty_env_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raise error when LINEAR_API_KEY env var is empty string."""
        monkeypatch.setenv("LINEAR_API_KEY", "")
        with pytest.raises(LinearClientError) as exc_info:
            LinearClient()
        assert exc_info.value.code == "MISSING_API_KEY"

    def test_init_raises_for_whitespace_only_env_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise error when LINEAR_API_KEY env var is whitespace-only."""
        monkeypatch.setenv("LINEAR_API_KEY", "   ")
        with pytest.raises(LinearClientError) as exc_info:
            LinearClient()
        assert exc_info.value.code == "EMPTY_API_KEY"


class TestLinearClientGetIssue:
    def test_get_issue_success(self, mocker: MockerFixture) -> None:
        """Successfully fetch issue details."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "title": "Test Issue",
                    "description": "Test description",
                    "url": "https://linear.app/issue/NES-24",
                    "branchName": "nes-24-test-issue",
                    "priority": 2,
                    "estimate": None,
                    "createdAt": "2025-01-01T00:00:00Z",
                    "updatedAt": "2025-01-02T00:00:00Z",
                    "completedAt": None,
                    "canceledAt": None,
                    "dueDate": None,
                    "team": None,
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

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.get_issue("NES-24")

        assert result["id"] == "issue-123"
        assert result["identifier"] == "NES-24"
        assert result["title"] == "Test Issue"

        # Verify urlopen was called
        mock_urlopen.assert_called_once()

    def test_get_issue_not_found(self, mocker: MockerFixture) -> None:
        """Raise error when issue is not found."""
        mock_response = {"data": {"issue": None}}

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("INVALID-999")

        assert exc_info.value.code == "NOT_FOUND"
        assert "INVALID-999" in exc_info.value.message

    def test_get_issue_parse_error(self, mocker: MockerFixture) -> None:
        """Raise error when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"Invalid JSON"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = mock_response

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "PARSE_ERROR"


class TestACR22KnownKeyReadContract:
    def test_get_issue_non_nes_identifier_does_not_resolve_team(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: known-key read team-coupling regression; level: unit.

        Source: ACR-22 proposal Test-Intent T1 and assumption A1.
        """
        mock_response = {
            "data": {
                "issue": {
                    "id": "age-issue-uuid",
                    "identifier": "AGE-1",
                    "title": "Known AGE issue",
                    "description": "Read by identifier",
                    "priority": 3,
                    "estimate": None,
                    "url": "https://linear.app/workspace/issue/AGE-1/known-age-issue",
                    "branchName": "age-1-known-age-issue",
                    "createdAt": "2026-05-01T00:00:00Z",
                    "updatedAt": "2026-05-02T00:00:00Z",
                    "completedAt": None,
                    "canceledAt": None,
                    "dueDate": None,
                    "team": {"id": "age-team-uuid", "name": "Agents", "key": "AGE"},
                    "assignee": None,
                    "state": {"id": "state-uuid", "name": "Todo", "type": "unstarted"},
                    "project": None,
                    "labels": {"nodes": []},
                    "parent": None,
                }
            }
        }
        run_graphql = mocker.patch.object(
            LinearClient,
            "_run_graphql",
            return_value=mock_response,
        )
        resolve_team_id = mocker.patch.object(LinearClient, "_resolve_team_id")

        client = LinearClient(api_key="test_key")
        result = client.get_issue("AGE-1")

        assert result["identifier"] == "AGE-1"
        assert result["team"] == {"id": "age-team-uuid", "name": "Agents", "key": "AGE"}
        run_graphql.assert_called_once()
        assert run_graphql.call_args.args[1] == {"issueId": "AGE-1"}
        resolve_team_id.assert_not_called()


class TestLinearClientCreateIssue:
    def test_create_issue_success(self, mocker: MockerFixture) -> None:
        """Successfully create a new issue."""
        # First call: list_teams for team resolution
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus", "key": "NES"},
                    ],
                }
            }
        }
        # Second call: issueCreate mutation
        create_response = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "new-issue-123",
                        "identifier": "NES-99",
                        "title": "New Feature",
                        "url": "https://linear.app/issue/NES-99",
                        "branchName": "nes-99-new-feature",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(teams_response),
            create_mock_response(create_response),
        ]

        client = LinearClient(api_key="test_key")
        result = client.create_issue(
            team="NES",
            title="New Feature",
            description="Feature description",
            priority=2,
        )

        assert result["identifier"] == "NES-99"
        assert result["title"] == "New Feature"

    def test_create_issue_empty_team(self, mocker: MockerFixture) -> None:
        """Raise error when team is an empty string."""
        # Empty team will cause _resolve_team_id to return None
        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.create_issue(team="", title="Test")

        assert exc_info.value.code == "NOT_FOUND"

    def test_create_issue_without_optional_params(self, mocker: MockerFixture) -> None:
        """Create issue with only required parameters."""
        # First call: list_teams for team resolution
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus", "key": "NES"},
                    ],
                }
            }
        }
        # Second call: issueCreate mutation
        create_response = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "new-issue-456",
                        "identifier": "NES-100",
                        "title": "Simple Issue",
                        "url": "https://linear.app/issue/NES-100",
                        "branchName": "nes-100-simple-issue",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(teams_response),
            create_mock_response(create_response),
        ]

        client = LinearClient(api_key="test_key")
        result = client.create_issue(team="NES", title="Simple Issue")

        assert result["identifier"] == "NES-100"

    def test_create_issue_with_all_optional_params(self, mocker: MockerFixture) -> None:
        """Create issue with all optional parameters."""
        # First call: list_teams for team resolution
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus", "key": "NES"},
                    ],
                }
            }
        }
        # Second call: issueCreate mutation
        create_response = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "new-issue-789",
                        "identifier": "NES-101",
                        "title": "Full Issue",
                        "url": "https://linear.app/issue/NES-101",
                        "branchName": "nes-101-full-issue",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(teams_response),
            create_mock_response(create_response),
        ]

        client = LinearClient(api_key="test_key")
        result = client.create_issue(
            team="NES",
            title="Full Issue",
            description="Full description",
            assignee_id="assignee-uuid",
            project_id="project-uuid",
            priority=1,
            state_id="state-uuid",
            parent_id="parent-uuid",
            label_ids=["label-1", "label-2"],
        )

        assert result["identifier"] == "NES-101"

    def test_create_issue_failure(self, mocker: MockerFixture) -> None:
        """Raise error when issueCreate returns success=False."""
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus", "key": "NES"},
                    ],
                }
            }
        }
        create_response = {
            "data": {
                "issueCreate": {
                    "success": False,
                    "issue": None,
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(teams_response),
            create_mock_response(create_response),
        ]

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.create_issue(team="NES", title="Failing Issue")

        assert exc_info.value.code == "API_ERROR"
        assert "Failed to create issue" in exc_info.value.message


class TestACR22CreateIssueTeamRoutingContract:
    def test_create_issue_ast_team_routes_mutation_to_resolved_team_id(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: implicit NES default in create; level: unit.

        Source: ACR-22 proposal Test-Intent T2 and assumptions A2/A3.
        """
        create_response = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "ast-issue-uuid",
                        "identifier": "AST-12",
                        "title": "AST routed issue",
                        "url": "https://linear.app/workspace/issue/AST-12/ast-routed-issue",
                        "branchName": "ast-12-ast-routed-issue",
                    },
                }
            }
        }
        list_teams = mocker.patch.object(
            LinearClient,
            "list_teams",
            return_value=[
                {"id": "ast-team-uuid", "name": "Agent Strategy", "key": "AST"},
                {"id": "nes-team-uuid", "name": "Nexus", "key": "NES"},
            ],
        )
        run_graphql = mocker.patch.object(
            LinearClient,
            "_run_graphql",
            return_value=create_response,
        )

        client = LinearClient(api_key="test_key")
        result = client.create_issue(
            team="AST",
            title="AST routed issue",
            description="Created in AST",
        )

        assert result["identifier"] == "AST-12"
        list_teams.assert_called_once_with(include_archived=True)
        run_graphql.assert_called_once()
        mutation_variables = run_graphql.call_args.args[1]
        assert mutation_variables["input"]["teamId"] == "ast-team-uuid"
        assert mutation_variables["input"]["title"] == "AST routed issue"
        assert mutation_variables["input"]["description"] == "Created in AST"

    def test_create_issue_unknown_team_stops_before_mutation(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: implicit NES default in create; level: unit.

        Source: ACR-22 proposal Test-Intent T2 and assumptions A2/A3.
        """
        mocker.patch.object(
            LinearClient,
            "list_teams",
            return_value=[
                {"id": "ast-team-uuid", "name": "Agent Strategy", "key": "AST"},
                {"id": "nes-team-uuid", "name": "Nexus", "key": "NES"},
            ],
        )
        run_graphql = mocker.patch.object(LinearClient, "_run_graphql")

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.create_issue(team="UNKNOWN", title="Should not create")

        assert exc_info.value.code == "NOT_FOUND"
        assert "UNKNOWN" in exc_info.value.message
        run_graphql.assert_not_called()


class TestLinearClientUpdateIssue:
    def test_update_issue_success(self, mocker: MockerFixture) -> None:
        """Successfully update an existing issue."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "NES-24",
                        "title": "Updated Title",
                        "url": "https://linear.app/issue/NES-24",
                        "updatedAt": "2025-01-03T00:00:00Z",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.update_issue(
            issue_id="NES-24",
            title="Updated Title",
            priority=1,
        )

        assert result["title"] == "Updated Title"
        assert result["updatedAt"] == "2025-01-03T00:00:00Z"

    def test_update_issue_partial_update(self, mocker: MockerFixture) -> None:
        """Update only some fields of an issue."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "NES-24",
                        "title": "Original Title",
                        "url": "https://linear.app/issue/NES-24",
                        "updatedAt": "2025-01-03T00:00:00Z",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.update_issue(issue_id="NES-24", priority=3)

        assert result["identifier"] == "NES-24"

    def test_update_issue_no_updates_error(self, mocker: MockerFixture) -> None:
        """Raise NO_UPDATES error when no updatable fields are provided."""
        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            # Only issue_id provided, no updatable fields
            client.update_issue(issue_id="NES-24")

        assert exc_info.value.code == "NO_UPDATES"
        assert "At least one field must be provided" in exc_info.value.message

    def test_update_issue_with_all_optional_params(self, mocker: MockerFixture) -> None:
        """Update issue with all optional parameters."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "NES-24",
                        "title": "Full Update Title",
                        "url": "https://linear.app/issue/NES-24",
                        "updatedAt": "2025-01-03T00:00:00Z",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.update_issue(
            issue_id="NES-24",
            title="Full Update Title",
            description="Updated description",
            assignee_id="assignee-uuid",
            project_id="project-uuid",
            priority=2,
            state_id="state-uuid",
            parent_id="parent-uuid",
            label_ids=["label-1", "label-2"],
        )

        assert result["title"] == "Full Update Title"

    def test_update_issue_with_status_alias(self, mocker: MockerFixture) -> None:
        """Update issue using status (backwards compat alias for state_id)."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "NES-24",
                        "title": "Issue",
                        "url": "https://linear.app/issue/NES-24",
                        "updatedAt": "2025-01-03T00:00:00Z",
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        # Using status parameter instead of state_id
        result = client.update_issue(issue_id="NES-24", status="some-state-uuid")

        assert result["identifier"] == "NES-24"

    def test_update_issue_failure(self, mocker: MockerFixture) -> None:
        """Raise error when issueUpdate returns success=False."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": False,
                    "issue": None,
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.update_issue(issue_id="NES-24", title="Failing Update")

        assert exc_info.value.code == "API_ERROR"
        assert "Failed to update issue" in exc_info.value.message


class TestLinearClientComments:
    def test_list_comments_success(self, mocker: MockerFixture) -> None:
        """Successfully list comments on an issue."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "First comment",
                                "createdAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-01T00:00:00Z",
                                "user": {
                                    "id": "user-1",
                                    "name": "Test User",
                                    "email": "test@example.com",
                                },
                            },
                            {
                                "id": "comment-2",
                                "body": "Second comment",
                                "createdAt": "2025-01-02T00:00:00Z",
                                "updatedAt": "2025-01-02T00:00:00Z",
                                "user": {
                                    "id": "user-2",
                                    "name": "Another User",
                                    "email": "another@example.com",
                                },
                            },
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.list_comments("NES-24")

        assert len(result["comments"]) == 2
        assert result["comments"][0]["body"] == "First comment"
        assert result["comments"][1]["body"] == "Second comment"
        assert result["comments"][0]["user"]["name"] == "Test User"

    def test_list_comments_empty(self, mocker: MockerFixture) -> None:
        """Return empty list when no comments exist."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.list_comments("NES-24")

        assert len(result["comments"]) == 0
        assert isinstance(result["comments"], list)

    def test_create_comment_success(self, mocker: MockerFixture) -> None:
        """Successfully create a comment on an issue."""
        mock_response = {
            "data": {
                "commentCreate": {
                    "success": True,
                    "comment": {
                        "id": "comment-new",
                        "body": "New comment",
                        "createdAt": "2025-01-03T00:00:00Z",
                        "issue": {"id": "issue-123"},
                        "user": {"id": "user-1", "name": "Test User", "email": "test@example.com"},
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.create_comment(issue_id="NES-24", body="New comment")

        assert result["id"] == "comment-new"
        assert result["body"] == "New comment"

    def test_list_comments_with_pagination(self, mocker: MockerFixture) -> None:
        """List comments handles pagination correctly."""
        page1_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "First comment",
                                "createdAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-01T00:00:00Z",
                                "user": None,
                            },
                        ],
                    },
                }
            }
        }
        page2_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-2",
                                "body": "Second comment",
                                "createdAt": "2025-01-02T00:00:00Z",
                                "updatedAt": "2025-01-02T00:00:00Z",
                                "user": {
                                    "id": "user-1",
                                    "name": "Test User",
                                    "email": "test@example.com",
                                },
                            },
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test_key")
        result = client.list_comments("NES-24")

        assert len(result["comments"]) == 2
        assert result["comments"][0]["id"] == "comment-1"
        assert result["comments"][1]["id"] == "comment-2"
        # Verify cursor was used - second call should include 'after' variable
        assert mock_urlopen.call_count == 2

    def test_list_comments_not_found(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND error when issue does not exist."""
        mock_response = {"data": {"issue": None}}

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_comments("INVALID-999")

        assert exc_info.value.code == "NOT_FOUND"
        assert "Issue not found" in exc_info.value.message

    def test_list_comments_pagination_error(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when pagination does not advance."""
        page1_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "First comment",
                                "createdAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-01T00:00:00Z",
                                "user": None,
                            },
                        ],
                    },
                }
            }
        }
        # Same cursor returned - pagination does not advance
        page2_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_comments("NES-24")

        assert exc_info.value.code == "PAGINATION_ERROR"
        assert "Pagination did not advance" in exc_info.value.message

    def test_list_comments_pagination_error_no_cursor(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when hasNextPage but no endCursor."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-123",
                    "identifier": "NES-24",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "First comment",
                                "createdAt": "2025-01-01T00:00:00Z",
                                "updatedAt": "2025-01-01T00:00:00Z",
                                "user": None,
                            },
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_comments("NES-24")

        assert exc_info.value.code == "PAGINATION_ERROR"

    def test_create_comment_failure(self, mocker: MockerFixture) -> None:
        """Raise error when commentCreate returns success=False."""
        mock_response = {
            "data": {
                "commentCreate": {
                    "success": False,
                    "comment": None,
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.create_comment(issue_id="NES-24", body="Failing comment")

        assert exc_info.value.code == "API_ERROR"
        assert "Failed to create comment" in exc_info.value.message

    def test_create_comment_not_dict_response(self, mocker: MockerFixture) -> None:
        """Raise error when commentCreate is not a dict."""
        mock_response = {
            "data": {
                "commentCreate": None  # Not a dict
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.create_comment(issue_id="NES-24", body="Test comment")

        assert exc_info.value.code == "API_ERROR"
        assert "Failed to create comment" in exc_info.value.message

    def test_create_comment_without_user(self, mocker: MockerFixture) -> None:
        """Create comment without user data (user_data is None)."""
        mock_response = {
            "data": {
                "commentCreate": {
                    "success": True,
                    "comment": {
                        "id": "comment-new",
                        "body": "System comment",
                        "createdAt": "2025-01-03T00:00:00Z",
                        "issue": {"id": "issue-123"},
                        "user": None,
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        result = client.create_comment(issue_id="NES-24", body="System comment")

        assert result["id"] == "comment-new"
        assert result["user"] is None


class TestLinearClientListProjects:
    def test_list_projects_success(self, mocker: MockerFixture) -> None:
        """Successfully list all projects."""
        mock_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "id": "project-1",
                            "name": "Project Alpha",
                            "description": "First project",
                            "url": "https://linear.app/project/alpha",
                            "slugId": "alpha",
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "archivedAt": None,
                            "state": "in_progress",
                        },
                        {
                            "id": "project-2",
                            "name": "Project Beta",
                            "description": None,
                            "url": "https://linear.app/project/beta",
                            "slugId": "beta",
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "archivedAt": None,
                            "state": "planned",
                        },
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        projects = client.list_projects()

        assert len(projects) == 2
        assert projects[0]["name"] == "Project Alpha"
        assert projects[1]["name"] == "Project Beta"

    def test_list_projects_empty(self, mocker: MockerFixture) -> None:
        """Return empty list when no projects exist."""
        mock_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        projects = client.list_projects()

        assert len(projects) == 0
        assert isinstance(projects, list)

    def test_list_projects_flattens_teams(self, mocker: MockerFixture) -> None:
        """Verify teams.nodes is flattened to teams list."""
        mock_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "id": "project-1",
                            "name": "Project Alpha",
                            "teams": {
                                "nodes": [
                                    {"id": "team-1", "name": "Engineering", "key": "ENG"},
                                    {"id": "team-2", "name": "Design", "key": "DES"},
                                ]
                            },
                        },
                        {
                            "id": "project-2",
                            "name": "Project Beta",
                            "teams": {
                                "nodes": [{"id": "team-1", "name": "Engineering", "key": "ENG"}]
                            },
                        },
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        projects = client.list_projects()

        # Verify teams is now a flat list, not nested under nodes
        assert len(projects) == 2
        assert isinstance(projects[0]["teams"], list)
        assert len(projects[0]["teams"]) == 2
        assert projects[0]["teams"][0]["key"] == "ENG"
        assert projects[0]["teams"][1]["key"] == "DES"
        assert isinstance(projects[1]["teams"], list)
        assert len(projects[1]["teams"]) == 1

    def test_list_projects_with_team_filter(self, mocker: MockerFixture) -> None:
        """List projects filtered by team ID."""
        # First call: list_teams for team resolution
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus", "key": "NES"},
                    ],
                }
            }
        }
        # Second call: list projects with team filter
        projects_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "id": "project-1",
                            "name": "Team Project",
                            "teams": {
                                "nodes": [{"id": "team-uuid-123", "name": "Nexus", "key": "NES"}]
                            },
                        },
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(teams_response),
            create_mock_response(projects_response),
        ]

        client = LinearClient(api_key="test_key")
        projects = client.list_projects(team_id="NES")

        assert len(projects) == 1
        assert projects[0]["name"] == "Team Project"

    def test_list_projects_team_not_found(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND when team does not exist."""
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus", "key": "NES"},
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(teams_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_projects(team_id="NONEXISTENT")

        assert exc_info.value.code == "NOT_FOUND"
        assert "Team not found" in exc_info.value.message

    def test_list_projects_with_pagination(self, mocker: MockerFixture) -> None:
        """List projects handles pagination correctly."""
        page1_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [
                        {"id": "project-1", "name": "Project 1"},
                    ],
                }
            }
        }
        page2_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "project-2", "name": "Project 2"},
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test_key")
        projects = client.list_projects()

        assert len(projects) == 2
        assert projects[0]["id"] == "project-1"
        assert projects[1]["id"] == "project-2"

    def test_list_projects_pagination_error(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when pagination does not advance."""
        page1_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [{"id": "project-1", "name": "Project 1"}],
                }
            }
        }
        # Same cursor returned - pagination does not advance
        page2_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_projects()

        assert exc_info.value.code == "PAGINATION_ERROR"
        assert "Pagination did not advance" in exc_info.value.message

    def test_list_projects_pagination_error_no_cursor(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when hasNextPage but no endCursor."""
        mock_response = {
            "data": {
                "projects": {
                    "pageInfo": {"hasNextPage": True, "endCursor": None},
                    "nodes": [{"id": "project-1", "name": "Project 1"}],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_projects()

        assert exc_info.value.code == "PAGINATION_ERROR"


class TestACR22LabelHelperContracts:
    def test_list_labels_resolves_ast_team_and_scopes_query(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        labels_response = {
            "data": {
                "issueLabels": {
                    "nodes": [
                        {
                            "id": "label-x",
                            "name": "hardening",
                            "color": "#abc",
                            "description": None,
                            "team": {"id": "ast-team-uuid", "key": "AST", "name": "AST"},
                        }
                    ]
                }
            }
        }
        resolve_team_id = mocker.patch.object(
            LinearClient,
            "_resolve_team_id",
            return_value="ast-team-uuid",
        )
        run_graphql = mocker.patch.object(
            LinearClient,
            "_run_graphql",
            return_value=labels_response,
        )

        client = LinearClient(api_key="test_key")
        labels = client.list_labels(team="AST")

        assert labels == labels_response["data"]["issueLabels"]["nodes"]
        resolve_team_id.assert_called_once_with("AST")
        run_graphql.assert_called_once()
        assert run_graphql.call_args.args[1] == {"teamId": "ast-team-uuid"}

    def test_create_label_resolves_ast_team_and_sends_team_id(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        create_response = {
            "data": {
                "issueLabelCreate": {
                    "success": True,
                    "issueLabel": {
                        "id": "label-x",
                        "name": "hardening",
                        "color": "#abc",
                        "description": "Coverage label",
                    },
                }
            }
        }
        mocker.patch.object(LinearClient, "_resolve_team_id", return_value="ast-team-uuid")
        run_graphql = mocker.patch.object(
            LinearClient,
            "_run_graphql",
            return_value=create_response,
        )

        client = LinearClient(api_key="test_key")
        label = client.create_label(
            team="AST",
            name="hardening",
            color="#abc",
            description="Coverage label",
        )

        assert label["id"] == "label-x"
        run_graphql.assert_called_once()
        assert run_graphql.call_args.args[1] == {
            "input": {
                "name": "hardening",
                "teamId": "ast-team-uuid",
                "color": "#abc",
                "description": "Coverage label",
            }
        }

    def test_resolve_label_ids_missing_label_raises_without_create(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        list_labels = mocker.patch.object(
            LinearClient,
            "list_labels",
            return_value=[{"id": "label-x", "name": "x"}],
        )
        create_label = mocker.patch.object(LinearClient, "create_label")

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.resolve_label_ids(team="AST", label_names=["x", "y"])

        assert exc_info.value.code == "NOT_FOUND"
        assert "y" in exc_info.value.message
        list_labels.assert_called_once_with("AST")
        create_label.assert_not_called()

    def test_resolve_label_ids_create_missing_creates_and_returns_ids(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        mocker.patch.object(
            LinearClient,
            "list_labels",
            return_value=[{"id": "label-x", "name": "x"}],
        )
        create_label = mocker.patch.object(
            LinearClient,
            "create_label",
            return_value={"id": "label-y", "name": "y"},
        )

        client = LinearClient(api_key="test_key")
        label_ids = client.resolve_label_ids(
            team="AST",
            label_names=["x", "y"],
            create_missing=True,
        )

        assert label_ids == ["label-x", "label-y"]
        create_label.assert_called_once_with("AST", "y")

    def test_apply_labels_merges_existing_labels_by_default(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        mocker.patch.object(
            LinearClient,
            "resolve_label_ids",
            return_value=["label-new", "label-existing"],
        )
        mocker.patch.object(LinearClient, "_resolve_team_id", return_value="team-ast")
        run_graphql = mocker.patch.object(
            LinearClient,
            "_run_graphql",
            return_value={
                "data": {
                    "issue": {
                        "team": {"id": "team-ast", "key": "AST"},
                        "labels": {
                            "nodes": [
                                {"id": "label-existing"},
                                {"id": "label-old"},
                            ]
                        }
                    }
                }
            },
        )
        update_issue = mocker.patch.object(
            LinearClient,
            "update_issue",
            return_value={"id": "issue-uuid", "labels": []},
        )

        client = LinearClient(api_key="test_key")
        result = client.apply_labels(
            issue_id="AST-12",
            team="AST",
            label_names=["x"],
            replace=False,
        )

        assert result["id"] == "issue-uuid"
        run_graphql.assert_called_once_with(
            run_graphql.call_args.args[0],
            {"id": "AST-12"},
        )
        update_issue.assert_called_once_with(
            "AST-12",
            label_ids=["label-existing", "label-old", "label-new"],
        )

    def test_apply_labels_replace_skips_existing_labels_query(
        self, mocker: MockerFixture
    ) -> None:
        """Risk: label helper coverage gap; level: unit.

        Source: ACR-22 proposal Test-Intent T6 and assumptions A2/A3/A7.
        """
        mocker.patch.object(
            LinearClient,
            "resolve_label_ids",
            return_value=["label-new", "label-new", "label-other"],
        )
        mocker.patch.object(LinearClient, "_resolve_team_id", return_value="team-ast")
        run_graphql = mocker.patch.object(
            LinearClient,
            "_run_graphql",
            return_value={
                "data": {
                    "issue": {
                        "team": {"id": "team-ast", "key": "AST"},
                        "labels": {"nodes": [{"id": "label-existing"}]},
                    }
                }
            },
        )
        update_issue = mocker.patch.object(
            LinearClient,
            "update_issue",
            return_value={"id": "issue-uuid", "labels": []},
        )

        client = LinearClient(api_key="test_key")
        client.apply_labels(
            issue_id="AST-12",
            team="AST",
            label_names=["x", "x", "y"],
            replace=True,
        )

        run_graphql.assert_called_once_with(
            run_graphql.call_args.args[0],
            {"id": "AST-12"},
        )
        update_issue.assert_called_once_with(
            "AST-12",
            label_ids=["label-new", "label-other"],
        )


class TestLinearClientListTeams:
    def test_list_teams_success(self, mocker: MockerFixture) -> None:
        """Successfully list all teams."""
        mock_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "id": "team-1",
                            "name": "Engineering",
                            "key": "ENG",
                            "description": "Engineering team",
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "archivedAt": None,
                            "private": False,
                            "timezone": "America/New_York",
                        },
                        {
                            "id": "team-2",
                            "name": "Nexus",
                            "key": "NES",
                            "description": None,
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "archivedAt": None,
                            "private": True,
                            "timezone": None,
                        },
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        teams = client.list_teams()

        assert len(teams) == 2
        assert teams[0]["key"] == "ENG"
        assert teams[1]["key"] == "NES"

    def test_list_teams_empty(self, mocker: MockerFixture) -> None:
        """Return empty list when no teams exist."""
        mock_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        teams = client.list_teams()

        assert len(teams) == 0
        assert isinstance(teams, list)

    def test_list_teams_caching(self, mocker: MockerFixture) -> None:
        """Verify list_teams caches results to avoid redundant API calls."""
        mock_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "id": "team-1",
                            "name": "Engineering",
                            "key": "ENG",
                            "description": "Engineering team",
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "archivedAt": None,
                            "private": False,
                            "timezone": "America/New_York",
                        },
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")

        # First call should hit the API
        teams1 = client.list_teams()
        assert mock_urlopen.call_count == 1
        assert len(teams1) == 1

        # Second call should use cache, no additional API call
        teams2 = client.list_teams()
        assert mock_urlopen.call_count == 1  # Still 1, not 2
        assert teams1 is teams2  # Same list object from cache

    def test_list_teams_caching_per_include_archived(self, mocker: MockerFixture) -> None:
        """Verify caching is separate for include_archived True/False."""
        mock_response_active = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{"id": "team-1", "name": "Active", "key": "ACT"}],
                }
            }
        }
        mock_response_all = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-1", "name": "Active", "key": "ACT"},
                        {"id": "team-2", "name": "Archived", "key": "ARC"},
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(mock_response_active),
            create_mock_response(mock_response_all),
        ]

        client = LinearClient(api_key="test_key")

        # Call without archived
        teams_active = client.list_teams(include_archived=False)
        assert mock_urlopen.call_count == 1
        assert len(teams_active) == 1

        # Call with archived - should hit API again (different cache key)
        teams_all = client.list_teams(include_archived=True)
        assert mock_urlopen.call_count == 2
        assert len(teams_all) == 2

        # Repeat calls should use cache
        client.list_teams(include_archived=False)
        client.list_teams(include_archived=True)
        assert mock_urlopen.call_count == 2  # No additional calls

    def test_list_teams_with_pagination(self, mocker: MockerFixture) -> None:
        """List teams handles pagination correctly."""
        page1_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [
                        {"id": "team-1", "name": "Team 1", "key": "T1"},
                    ],
                }
            }
        }
        page2_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-2", "name": "Team 2", "key": "T2"},
                    ],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test_key")
        teams = client.list_teams()

        assert len(teams) == 2
        assert teams[0]["id"] == "team-1"
        assert teams[1]["id"] == "team-2"
        assert mock_urlopen.call_count == 2

    def test_list_teams_pagination_error(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when pagination does not advance."""
        page1_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [{"id": "team-1", "name": "Team 1", "key": "T1"}],
                }
            }
        }
        # Same cursor returned - pagination does not advance
        page2_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_teams()

        assert exc_info.value.code == "PAGINATION_ERROR"
        assert "Pagination did not advance" in exc_info.value.message

    def test_list_teams_pagination_error_no_cursor(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when hasNextPage but no endCursor."""
        mock_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": True, "endCursor": None},
                    "nodes": [{"id": "team-1", "name": "Team 1", "key": "T1"}],
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_teams()

        assert exc_info.value.code == "PAGINATION_ERROR"


class TestLinearClientErrorHandling:
    def test_http_error_handling(self, mocker: MockerFixture) -> None:
        """Raise API_ERROR on HTTP errors from urlopen."""
        import urllib.error

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.linear.app/graphql",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None,
        )

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "API_ERROR"
        assert "401" in exc_info.value.message

    def test_url_error_handling(self, mocker: MockerFixture) -> None:
        """Raise API_ERROR on URLError from urlopen."""
        import urllib.error

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "API_ERROR"
        assert "Connection refused" in exc_info.value.message

    def test_invalid_json_handling(self, mocker: MockerFixture) -> None:
        """Handle malformed JSON responses."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true, invalid json'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = mock_response

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "PARSE_ERROR"

    def test_api_key_not_in_error_messages(self, mocker: MockerFixture) -> None:
        """Ensure API key is not leaked in error messages."""
        # GraphQL error response
        mock_response = {"errors": [{"message": "Invalid API key provided"}]}

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test-linear-api-key-12345")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        # Verify the API key is not in the error message
        error_message = str(exc_info.value)
        assert "test-linear-api-key-12345" not in error_message
        assert "GRAPHQL_ERROR" in error_message

    def test_graphql_error_handling(self, mocker: MockerFixture) -> None:
        """Handle GraphQL errors from the API."""
        mock_response = {
            "errors": [
                {"message": "Field 'issue' not found"},
                {"message": "Invalid query"},
            ]
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "GRAPHQL_ERROR"
        assert "Field 'issue' not found" in exc_info.value.message

    def test_graphql_multiple_errors_joined(self, mocker: MockerFixture) -> None:
        """Multiple GraphQL errors are joined with semicolons."""
        mock_response = {
            "errors": [
                {"message": "First error"},
                {"message": "Second error"},
                {"message": "Third error"},
            ]
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "GRAPHQL_ERROR"
        # Verify all errors are included and joined with semicolons
        assert "First error" in exc_info.value.message
        assert "Second error" in exc_info.value.message
        assert "Third error" in exc_info.value.message
        assert ";" in exc_info.value.message

    def test_non_utf8_response_raises_error(self, mocker: MockerFixture) -> None:
        """Handle non-UTF8 response from the API."""
        mock_response = MagicMock()
        # Invalid UTF-8 bytes
        mock_response.read.return_value = b"\x80\x81\x82"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = mock_response

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "PARSE_ERROR"
        assert "non-UTF-8" in exc_info.value.message

    def test_non_object_json_response_raises_error(self, mocker: MockerFixture) -> None:
        """Handle non-object JSON response (e.g., array or string)."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'["array", "response"]'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = mock_response

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        assert exc_info.value.code == "PARSE_ERROR"
        assert "non-object JSON" in exc_info.value.message

    def test_empty_response_data(self, mocker: MockerFixture) -> None:
        """Handle empty data in successful response."""
        mock_response = {"data": {"issue": None}}

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("NES-24")

        # Should raise NOT_FOUND when issue is None
        assert exc_info.value.code == "NOT_FOUND"


class TestLinearCLIOutputFormat:
    def test_list_projects_output_format(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify list_projects outputs data nested under 'projects' key."""
        from clients.linear import cli as linear_cli

        mock_projects = [
            {"id": "project-1", "name": "Project Alpha"},
            {"id": "project-2", "name": "Project Beta"},
        ]

        mocker.patch.object(linear_cli, "LinearClient")
        linear_cli.LinearClient.return_value.list_projects.return_value = mock_projects

        linear_cli.list_projects()
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is True
        assert "data" in output
        assert "projects" in output["data"]
        assert output["data"]["projects"] == mock_projects

    def test_list_teams_output_format(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify list_teams outputs data nested under 'teams' key."""
        from clients.linear import cli as linear_cli

        mock_teams = [
            {"id": "team-1", "name": "Engineering", "key": "ENG"},
            {"id": "team-2", "name": "Nexus", "key": "NES"},
        ]

        mocker.patch.object(linear_cli, "LinearClient")
        linear_cli.LinearClient.return_value.list_teams.return_value = mock_teams

        linear_cli.list_teams()
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is True
        assert "data" in output
        assert "teams" in output["data"]
        assert output["data"]["teams"] == mock_teams

    def test_list_comments_output_format(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify list_comments outputs data nested under 'comments' key."""
        from clients.linear import cli as linear_cli

        mock_comments = [
            {"id": "comment-1", "body": "First comment"},
            {"id": "comment-2", "body": "Second comment"},
        ]

        mocker.patch.object(linear_cli, "LinearClient")
        mock_client_result = {
            "issueId": "issue-123",
            "issueIdentifier": "NES-24",
            "comments": mock_comments,
            "totalCount": 2,
        }
        linear_cli.LinearClient.return_value.list_comments.return_value = mock_client_result

        linear_cli.list_comments("NES-24")
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is True
        assert "data" in output
        assert "comments" in output["data"]
        assert output["data"]["comments"] == mock_comments

    def test_get_issue_output_format(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify get_issue outputs data directly (not nested in a list key)."""
        from clients.linear import cli as linear_cli

        mock_issue = {
            "id": "issue-123",
            "identifier": "NES-24",
            "title": "Test Issue",
        }

        mocker.patch.object(linear_cli, "LinearClient")
        linear_cli.LinearClient.return_value.get_issue.return_value = mock_issue

        linear_cli.get_issue("NES-24")
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is True
        assert "data" in output
        # For scalar returns, data is the object directly (not nested)
        assert output["data"] == mock_issue

    def test_create_issue_output_format(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify create_issue outputs data directly (not nested in a list key)."""
        from clients.linear import cli as linear_cli

        mock_issue = {
            "id": "new-issue-123",
            "identifier": "NES-99",
            "title": "New Feature",
        }

        mocker.patch.object(linear_cli, "LinearClient")
        linear_cli.LinearClient.return_value.create_issue.return_value = mock_issue

        linear_cli.create_issue(team="NES", title="New Feature")
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is True
        assert "data" in output
        assert output["data"] == mock_issue

    def test_create_comment_output_format(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify create_comment outputs data directly (not nested in a list key)."""
        from clients.linear import cli as linear_cli

        mock_comment = {
            "id": "comment-new",
            "body": "New comment",
        }

        mocker.patch.object(linear_cli, "LinearClient")
        linear_cli.LinearClient.return_value.create_comment.return_value = mock_comment

        linear_cli.create_comment(issue_id="NES-24", body="New comment")
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is True
        assert "data" in output
        assert output["data"] == mock_comment

    def test_missing_command_outputs_json_error(
        self, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
    ) -> None:
        """Verify that missing command outputs JSON error, not usage text."""
        from clients.linear import cli as linear_cli

        # Simulate running with no command
        mocker.patch("sys.argv", ["linear"])

        with pytest.raises(SystemExit) as exc_info:
            linear_cli.main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is False
        assert "error" in output
        assert output["error"]["code"] == "INVALID_INPUT"
        assert "command is required" in output["error"]["message"]

    def test_invalid_argument_outputs_json_error(
        self, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
    ) -> None:
        """Verify that invalid arguments output JSON error, not usage text."""
        from clients.linear import cli as linear_cli

        # Simulate passing an invalid command
        mocker.patch("sys.argv", ["linear", "create-issue", "--invalid-option", "value"])

        with pytest.raises(SystemExit) as exc_info:
            linear_cli.main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is False
        assert "error" in output
        assert output["error"]["code"] == "INVALID_INPUT"

    def test_missing_required_argument_outputs_json_error(
        self, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
    ) -> None:
        """Verify that missing required argument outputs JSON error."""
        from clients.linear import cli as linear_cli

        # create-issue requires --team and --title
        mocker.patch("sys.argv", ["linear", "create-issue"])

        with pytest.raises(SystemExit) as exc_info:
            linear_cli.main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["ok"] is False
        assert "error" in output
        assert output["error"]["code"] == "INVALID_INPUT"
        assert "--team" in output["error"]["message"]


class TestLinearClientNetworkErrors:
    def test_timeout_error_raises_api_error(self, mocker: MockerFixture) -> None:
        """Verify TimeoutError is caught and wrapped as LinearClientError."""

        # Mock urlopen to raise TimeoutError
        mocker.patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        )

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client._run_graphql("query { viewer { id } }", timeout=30)

        assert exc_info.value.code == "API_ERROR"
        assert "timed out" in exc_info.value.message
        assert "30 seconds" in exc_info.value.message

    def test_timeout_error_includes_custom_timeout_value(self, mocker: MockerFixture) -> None:
        """Verify TimeoutError message includes the configured timeout value."""

        mocker.patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        )

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client._run_graphql("query { viewer { id } }", timeout=60)

        assert "60 seconds" in exc_info.value.message

    def test_socket_timeout_raises_api_error(self, mocker: MockerFixture) -> None:
        """Verify socket.timeout is caught and wrapped as LinearClientError."""

        # Mock urlopen to raise socket.timeout
        mocker.patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        )

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client._run_graphql("query { viewer { id } }", timeout=30)

        assert exc_info.value.code == "API_ERROR"
        assert "timed out" in exc_info.value.message
        assert "30 seconds" in exc_info.value.message

    def test_socket_timeout_includes_custom_timeout_value(self, mocker: MockerFixture) -> None:
        """Verify socket.timeout error message includes the configured timeout value."""

        mocker.patch(
            "urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        )

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client._run_graphql("query { viewer { id } }", timeout=60)

        assert "60 seconds" in exc_info.value.message

    def test_json_serialization_error_raises_parse_error(self, mocker: MockerFixture) -> None:
        """Verify TypeError from json.dumps is wrapped as LinearClientError."""

        # Create a non-serializable object
        class NonSerializable:
            pass

        client = LinearClient(api_key="test_key")
        with pytest.raises(LinearClientError) as exc_info:
            client._run_graphql(
                "query { viewer { id } }",
                variables={"bad": NonSerializable()},
            )

        assert exc_info.value.code == "PARSE_ERROR"
        assert "Failed to serialize request payload to JSON" in exc_info.value.message


class TestLinearClientListUnresolvedComments:
    def test_list_unresolved_comments_success(self, mocker: MockerFixture) -> None:
        """Successfully list unresolved comments."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-uuid-1",
                                "body": "Test comment body",
                                "createdAt": "2025-01-15T10:00:00Z",
                                "updatedAt": "2025-01-15T11:00:00Z",
                                "resolvedAt": None,
                                "user": {
                                    "id": "user-uuid-1",
                                    "name": "Test User",
                                    "email": "test@example.com",
                                },
                            }
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test-key")
        result = client.list_unresolved_comments("NES-456")

        assert result["issueId"] == "issue-uuid-123"
        assert result["issueIdentifier"] == "NES-456"
        assert result["totalCount"] == 1
        assert len(result["comments"]) == 1
        assert result["comments"][0]["body"] == "Test comment body"

    def test_list_unresolved_comments_filters_resolved(self, mocker: MockerFixture) -> None:
        """Resolved comments are filtered out."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "Unresolved comment",
                                "createdAt": "2025-01-15T10:00:00Z",
                                "updatedAt": "2025-01-15T11:00:00Z",
                                "resolvedAt": None,
                                "user": {"id": "u1", "name": "User1", "email": "u1@example.com"},
                            },
                            {
                                "id": "comment-2",
                                "body": "Resolved comment",
                                "createdAt": "2025-01-15T10:00:00Z",
                                "updatedAt": "2025-01-15T11:00:00Z",
                                "resolvedAt": "2025-01-15T12:00:00Z",
                                "user": {"id": "u2", "name": "User2", "email": "u2@example.com"},
                            },
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test-key")
        result = client.list_unresolved_comments("NES-456")

        assert result["totalCount"] == 1
        assert len(result["comments"]) == 1
        assert result["comments"][0]["id"] == "comment-1"
        assert result["comments"][0]["body"] == "Unresolved comment"

    def test_list_unresolved_comments_pagination(self, mocker: MockerFixture) -> None:
        """Pagination handles multiple pages correctly."""
        page1_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "First comment",
                                "createdAt": "2025-01-15T10:00:00Z",
                                "updatedAt": "2025-01-15T11:00:00Z",
                                "resolvedAt": None,
                                "user": {"id": "u1", "name": "User1", "email": "u1@example.com"},
                            }
                        ],
                    },
                }
            }
        }
        page2_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-2",
                                "body": "Second comment",
                                "createdAt": "2025-01-15T12:00:00Z",
                                "updatedAt": "2025-01-15T13:00:00Z",
                                "resolvedAt": None,
                                "user": {"id": "u2", "name": "User2", "email": "u2@example.com"},
                            }
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test-key")
        result = client.list_unresolved_comments("NES-456")

        assert result["totalCount"] == 2
        assert len(result["comments"]) == 2
        assert result["comments"][0]["id"] == "comment-1"
        assert result["comments"][1]["id"] == "comment-2"

    def test_list_unresolved_comments_issue_not_found(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND error when issue doesn't exist."""
        mock_response = {"data": {"issue": None}}

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_unresolved_comments("INVALID-999")

        assert exc_info.value.code == "NOT_FOUND"
        assert "Issue not found: INVALID-999" in exc_info.value.message

    def test_list_unresolved_comments_handles_null_user(self, mocker: MockerFixture) -> None:
        """Handle comments with null user (system comments)."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "System comment",
                                "createdAt": "2025-01-15T10:00:00Z",
                                "updatedAt": "2025-01-15T11:00:00Z",
                                "resolvedAt": None,
                                "user": None,
                            }
                        ],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.return_value = create_mock_response(mock_response)

        client = LinearClient(api_key="test-key")
        result = client.list_unresolved_comments("NES-456")

        assert result["totalCount"] == 1
        assert len(result["comments"]) == 1
        assert result["comments"][0]["user"] is None

    def test_list_unresolved_comments_return_structure(self, mocker: MockerFixture) -> None:
        """Verify the full key set and nesting of the returned value.

        This test ensures the return structure matches what
        list_unresolved_comments_command in commands.py expects to output
        via json.dumps().
        """
        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "id": "issue-uuid-123",
                        "identifier": "NES-456",
                        "comments": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "id": "comment-uuid-1",
                                    "body": "Test comment body",
                                    "createdAt": "2025-01-15T10:00:00Z",
                                    "updatedAt": "2025-01-15T11:00:00Z",
                                    "resolvedAt": None,
                                    "user": {
                                        "id": "user-uuid-1",
                                        "name": "Test User",
                                        "email": "test@example.com",
                                    },
                                }
                            ],
                        },
                    }
                }
            }
        )
        mock_urlopen.return_value = mock_response

        client = LinearClient(api_key="test-key")
        result = client.list_unresolved_comments("NES-456")

        # Assert top-level keys exist and have correct types
        assert "issueId" in result
        assert "issueIdentifier" in result
        assert "comments" in result
        assert "totalCount" in result

        assert isinstance(result["issueId"], str)
        assert isinstance(result["issueIdentifier"], str)
        assert isinstance(result["comments"], list)
        assert isinstance(result["totalCount"], int)

        # Assert top-level values
        assert result["issueId"] == "issue-uuid-123"
        assert result["issueIdentifier"] == "NES-456"
        assert result["totalCount"] == 1

        # Assert comment structure
        assert len(result["comments"]) == 1
        comment = result["comments"][0]

        # Assert per-comment keys exist
        assert "id" in comment
        assert "body" in comment
        assert "createdAt" in comment
        assert "updatedAt" in comment
        assert "user" in comment

        # Assert per-comment values
        assert comment["id"] == "comment-uuid-1"
        assert comment["body"] == "Test comment body"
        assert comment["createdAt"] == "2025-01-15T10:00:00Z"
        assert comment["updatedAt"] == "2025-01-15T11:00:00Z"

        # Assert user structure within comment
        user = comment["user"]
        assert user is not None
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert user["id"] == "user-uuid-1"
        assert user["name"] == "Test User"
        assert user["email"] == "test@example.com"

    def test_list_unresolved_comments_pagination_error(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when pagination doesn't advance."""
        page1_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [
                            {
                                "id": "comment-1",
                                "body": "First comment",
                                "createdAt": "2025-01-15T10:00:00Z",
                                "updatedAt": "2025-01-15T11:00:00Z",
                                "resolvedAt": None,
                                "user": None,
                            }
                        ],
                    },
                }
            }
        }
        # Second response has same cursor, which should trigger pagination error
        page2_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "comments": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        "nodes": [],
                    },
                }
            }
        }

        mock_urlopen = mocker.patch("urllib.request.urlopen")
        mock_urlopen.side_effect = [
            create_mock_response(page1_response),
            create_mock_response(page2_response),
        ]

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.list_unresolved_comments("NES-456")

        assert exc_info.value.code == "PAGINATION_ERROR"
        assert "Pagination did not advance" in exc_info.value.message


class TestFetchGitHubAttachments:
    def test_fetch_attachments_success(self, mocker: MockerFixture) -> None:
        """Successfully fetch GitHub attachments."""
        mock_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "attachments": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {"url": "https://github.com/org/repo/pull/1", "title": "PR #1"},
                                {"url": "https://github.com/org/repo/pull/2", "title": "PR #2"},
                            ],
                        }
                    }
                }
            }
        )
        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        client = LinearClient(api_key="test-key")
        attachments = client.fetch_github_attachments("NES-123")

        assert len(attachments) == 2
        assert attachments[0]["url"] == "https://github.com/org/repo/pull/1"
        assert attachments[1]["url"] == "https://github.com/org/repo/pull/2"

    def test_fetch_attachments_ticket_not_found_raises(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND error when ticket does not exist."""
        mock_response = create_mock_response({"data": {"issue": None}})
        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.fetch_github_attachments("INVALID-999")

        assert exc_info.value.code == "NOT_FOUND"
        assert "Ticket not found: INVALID-999" in exc_info.value.message

    def test_fetch_attachments_with_pagination(self, mocker: MockerFixture) -> None:
        """Fetch attachments across multiple pages."""
        page1_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "attachments": {
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                            "nodes": [
                                {"url": "https://github.com/org/repo/pull/1", "title": "PR #1"}
                            ],
                        }
                    }
                }
            }
        )
        page2_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "attachments": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {"url": "https://github.com/org/repo/pull/2", "title": "PR #2"}
                            ],
                        }
                    }
                }
            }
        )
        mocker.patch("urllib.request.urlopen", side_effect=[page1_response, page2_response])

        client = LinearClient(api_key="test-key")
        attachments = client.fetch_github_attachments("NES-123")

        assert len(attachments) == 2
        assert attachments[0]["url"] == "https://github.com/org/repo/pull/1"
        assert attachments[1]["url"] == "https://github.com/org/repo/pull/2"

    def test_fetch_attachments_pagination_error(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when pagination does not advance."""
        page1_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "attachments": {
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                            "nodes": [
                                {"url": "https://github.com/org/repo/pull/1", "title": "PR #1"}
                            ],
                        }
                    }
                }
            }
        )
        # Same cursor returned - pagination does not advance
        page2_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "attachments": {
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                            "nodes": [],
                        }
                    }
                }
            }
        )
        mocker.patch("urllib.request.urlopen", side_effect=[page1_response, page2_response])

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.fetch_github_attachments("NES-123")

        assert exc_info.value.code == "PAGINATION_ERROR"
        assert "Pagination did not advance" in exc_info.value.message

    def test_fetch_attachments_pagination_error_no_cursor(self, mocker: MockerFixture) -> None:
        """Raise PAGINATION_ERROR when hasNextPage but no endCursor."""
        mock_response = create_mock_response(
            {
                "data": {
                    "issue": {
                        "attachments": {
                            "pageInfo": {"hasNextPage": True, "endCursor": None},
                            "nodes": [
                                {"url": "https://github.com/org/repo/pull/1", "title": "PR #1"}
                            ],
                        }
                    }
                }
            }
        )
        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.fetch_github_attachments("NES-123")

        assert exc_info.value.code == "PAGINATION_ERROR"


class TestResolveTeamId:
    def test_uuid_returns_as_is(self, mocker: MockerFixture) -> None:
        """Valid UUID string returns as-is without API call."""
        mock_urlopen = mocker.patch("urllib.request.urlopen")

        client = LinearClient(api_key="test-key")
        result = client._resolve_team_id("550e8400-e29b-41d4-a716-446655440000")

        assert result == "550e8400-e29b-41d4-a716-446655440000"
        # No API call should be made for UUID
        mock_urlopen.assert_not_called()

    def test_team_key_lookup_case_insensitive(self, mocker: MockerFixture) -> None:
        """Team key lookup is case-insensitive."""
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus Team", "key": "NES"},
                    ],
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(teams_response))

        client = LinearClient(api_key="test-key")
        # Lowercase "nes" should match team with key "NES"
        result = client._resolve_team_id("nes")

        assert result == "team-uuid-123"

    def test_team_name_lookup_case_insensitive(self, mocker: MockerFixture) -> None:
        """Team name lookup is case-insensitive."""
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-456", "name": "Engineering", "key": "ENG"},
                    ],
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(teams_response))

        client = LinearClient(api_key="test-key")
        # Lowercase "engineering" should match team with name "Engineering"
        result = client._resolve_team_id("engineering")

        assert result == "team-uuid-456"

    def test_key_takes_precedence_over_name(self, mocker: MockerFixture) -> None:
        """Team key lookup takes precedence over name lookup."""
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-by-key", "name": "Different Name", "key": "NES"},
                        {"id": "team-by-name", "name": "nes", "key": "OTHER"},
                    ],
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(teams_response))

        client = LinearClient(api_key="test-key")
        # "nes" should match by key first, not by name
        result = client._resolve_team_id("nes")

        assert result == "team-by-key"

    def test_not_found_returns_none(self, mocker: MockerFixture) -> None:
        """Returns None when team is not found."""
        teams_response = {
            "data": {
                "teams": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {"id": "team-uuid-123", "name": "Nexus Team", "key": "NES"},
                    ],
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(teams_response))

        client = LinearClient(api_key="test-key")
        result = client._resolve_team_id("nonexistent")

        assert result is None

    def test_empty_string_returns_none_without_api_call(self, mocker: MockerFixture) -> None:
        """Empty string returns None without calling list_teams."""
        mock_urlopen = mocker.patch("urllib.request.urlopen")

        client = LinearClient(api_key="test-key")
        result = client._resolve_team_id("")

        assert result is None
        mock_urlopen.assert_not_called()

    def test_whitespace_only_returns_none_without_api_call(self, mocker: MockerFixture) -> None:
        """Whitespace-only string returns None without calling list_teams."""
        mock_urlopen = mocker.patch("urllib.request.urlopen")

        client = LinearClient(api_key="test-key")
        result = client._resolve_team_id("   ")

        assert result is None
        mock_urlopen.assert_not_called()

    def test_excessively_long_string_returns_none_without_api_call(
        self, mocker: MockerFixture
    ) -> None:
        """String over 100 characters returns None without calling list_teams."""
        mock_urlopen = mocker.patch("urllib.request.urlopen")

        client = LinearClient(api_key="test-key")
        long_string = "a" * 101
        result = client._resolve_team_id(long_string)

        assert result is None
        mock_urlopen.assert_not_called()


class TestGetTicketInfo:
    def test_get_ticket_info_success(self, mocker: MockerFixture) -> None:
        """Successfully get ticket info with all fields."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "title": "Test Ticket",
                    "branchName": "nes-456-test-ticket",
                    "state": {"id": "state-id", "name": "In Progress", "type": "started"},
                    "team": {"id": "team-uuid-789"},
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        result = client.get_ticket_info("NES-456")

        assert result["id"] == "issue-uuid-123"
        assert result["identifier"] == "NES-456"
        assert result["title"] == "Test Ticket"
        assert result["branch_name"] == "nes-456-test-ticket"
        assert result["state"] == "In Progress"
        assert result["state_type"] == "started"
        assert result["team_id"] == "team-uuid-789"

    def test_get_ticket_info_not_found(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND error when ticket not found."""
        mock_response = {"data": {"issue": None}}
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_ticket_info("INVALID-999")

        assert exc_info.value.code == "NOT_FOUND"
        assert "Ticket not found: INVALID-999" in exc_info.value.message

    def test_get_ticket_info_null_nested_objects(self, mocker: MockerFixture) -> None:
        """Handle null state and team gracefully."""
        mock_response = {
            "data": {
                "issue": {
                    "id": "issue-uuid-123",
                    "identifier": "NES-456",
                    "title": "Test Ticket",
                    "branchName": "nes-456-test-ticket",
                    "state": None,
                    "team": None,
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        result = client.get_ticket_info("NES-456")

        assert result["id"] == "issue-uuid-123"
        assert result["state"] is None
        assert result["state_type"] is None
        assert result["team_id"] is None


class TestGetDoneStateId:
    def test_get_done_state_id_success(self, mocker: MockerFixture) -> None:
        """Successfully get done state ID."""
        mock_response = {
            "data": {
                "team": {
                    "states": {
                        "nodes": [{"id": "done-state-id", "name": "Done", "type": "completed"}]
                    }
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        result = client.get_done_state_id("team-uuid-123")

        assert result == "done-state-id"

    def test_get_done_state_id_team_not_found(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND error when team not found."""
        mock_response = {"data": {"team": None}}
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_done_state_id("invalid-team-uuid")

        assert exc_info.value.code == "NOT_FOUND"
        assert "Team not found" in exc_info.value.message

    def test_get_done_state_id_not_found(self, mocker: MockerFixture) -> None:
        """Raise NOT_FOUND error when no done state found."""
        mock_response = {"data": {"team": {"states": {"nodes": []}}}}
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_done_state_id("team-uuid-123")

        assert exc_info.value.code == "NOT_FOUND"
        assert "No 'Done' state found" in exc_info.value.message

    def test_get_done_state_id_missing_id_field(self, mocker: MockerFixture) -> None:
        """Raise error when state exists but id field is missing."""
        mock_response = {
            "data": {
                "team": {
                    "states": {
                        "nodes": [
                            {"name": "Done", "type": "completed"}  # No 'id' field
                        ]
                    }
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.get_done_state_id("team-uuid-123")

        assert exc_info.value.code == "NOT_FOUND"
        assert "No 'Done' state ID found" in exc_info.value.message


class TestSetTicketState:
    def test_set_ticket_state_success(self, mocker: MockerFixture) -> None:
        """Successfully set ticket state returns dict with stateName."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {"state": {"name": "Done"}},
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        result = client.set_ticket_state("issue-uuid", "state-uuid")

        assert result == {"stateName": "Done"}

    def test_set_ticket_state_failure(self, mocker: MockerFixture) -> None:
        """Raise error when state update fails."""
        mock_response = {
            "data": {
                "issueUpdate": {
                    "success": False,
                    "issue": None,
                }
            }
        }
        mocker.patch("urllib.request.urlopen", return_value=create_mock_response(mock_response))

        client = LinearClient(api_key="test-key")
        with pytest.raises(LinearClientError) as exc_info:
            client.set_ticket_state("issue-uuid", "invalid-state-uuid")

        assert exc_info.value.code == "API_ERROR"
        assert "Failed to update state" in exc_info.value.message


class TestACR113LabelInventoryAndResolution:
    def test_list_labels_queries_team_and_workspace_labels(self, mocker: MockerFixture) -> None:
        """T1: list_labels resolves the team and retains team/workspace label shape."""
        labels = [
            {
                "id": "label-team-hardening",
                "name": "hardening",
                "color": "#5e6ad2",
                "description": "Team label",
                "team": {"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"},
            },
            {
                "id": "label-workspace-bug",
                "name": "Bug",
                "color": "#e5484d",
                "description": "Workspace label",
                "team": None,
            },
        ]
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "_resolve_team_id", return_value=ACR113_TEAM_ID)
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={"data": {"issueLabels": {"nodes": labels}}},
        )

        result = client.list_labels("ACR")

        query, variables = run_graphql.call_args.args
        assert "issueLabels" in query
        assert "team: {id: {eq: $teamId}}" in query
        assert "team: {null: true}" in query
        assert "team { id key name }" in query
        assert variables == {"teamId": ACR113_TEAM_ID}
        assert result == labels
        assert result[0]["team"]["id"] == ACR113_TEAM_ID
        assert result[1]["team"] is None

    def test_resolve_label_ids_prefers_team_label_over_workspace_label(
        self, mocker: MockerFixture
    ) -> None:
        """T2: a team-owned label wins over a same-name workspace label."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(
            client,
            "list_labels",
            return_value=[
                {
                    "id": "label-team-hardening",
                    "name": "hardening",
                    "team": {"id": ACR113_TEAM_ID, "key": "ACR"},
                },
                {"id": "label-workspace-hardening", "name": "hardening", "team": None},
            ],
        )

        assert client.resolve_label_ids("ACR", ["hardening"]) == ["label-team-hardening"]

    def test_resolve_label_ids_same_tier_duplicate_raises_ambiguous_label(
        self, mocker: MockerFixture
    ) -> None:
        """T2: duplicate exact names in the same precedence tier are forbidden."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(
            client,
            "list_labels",
            return_value=[
                {
                    "id": "label-team-hardening-a",
                    "name": "hardening",
                    "team": {"id": ACR113_TEAM_ID, "key": "ACR"},
                },
                {
                    "id": "label-team-hardening-b",
                    "name": "hardening",
                    "team": {"id": ACR113_TEAM_ID, "key": "ACR"},
                },
            ],
        )

        with pytest.raises(LinearClientError) as exc_info:
            client.resolve_label_ids("ACR", ["hardening"])

        assert exc_info.value.code == "AMBIGUOUS_LABEL"

    def test_resolve_label_ids_missing_label_without_create_fails_before_create(
        self, mocker: MockerFixture
    ) -> None:
        """T3: missing labels fail without invoking create_label."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "list_labels", return_value=[])
        create_label = mocker.patch.object(client, "create_label")

        with pytest.raises(LinearClientError) as exc_info:
            client.resolve_label_ids("ACR", ["new-label"], create_missing=False)

        assert exc_info.value.code == "NOT_FOUND"
        create_label.assert_not_called()

    def test_resolve_label_ids_create_missing_calls_create_label(
        self, mocker: MockerFixture
    ) -> None:
        """T3: create_missing creates the label and returns the created ID."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "list_labels", return_value=[])
        create_label = mocker.patch.object(
            client,
            "create_label",
            return_value={"id": "label-new", "name": "new-label"},
        )

        assert client.resolve_label_ids("ACR", ["new-label"], create_missing=True) == [
            "label-new"
        ]
        create_label.assert_called_once_with("ACR", "new-label")


class TestACR113ApplyLabelsContract:
    def test_apply_labels_rejects_issue_team_mismatch_before_update(
        self, mocker: MockerFixture
    ) -> None:
        """T4: applying labels must verify the issue belongs to the supplied team."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "_resolve_team_id", return_value=ACR113_TEAM_ID)
        mocker.patch.object(client, "resolve_label_ids", return_value=["label-hardening"])
        mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "issue": {
                        "team": {"id": "other-team-id", "key": "OTHER"},
                        "labels": {"nodes": [{"id": "label-existing"}]},
                    }
                }
            },
        )
        update_issue = mocker.patch.object(client, "update_issue")

        with pytest.raises(LinearClientError) as exc_info:
            client.apply_labels("ACR-1", "ACR", ["hardening"])

        assert exc_info.value.code == "INVALID_INPUT"
        update_issue.assert_not_called()

    def test_apply_labels_merge_and_replace_send_full_replacement_ids(
        self, mocker: MockerFixture
    ) -> None:
        """T4/T10: merge de-duplicates current+resolved IDs, replace sends resolved IDs."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "_resolve_team_id", return_value=ACR113_TEAM_ID)
        mocker.patch.object(client, "resolve_label_ids", return_value=["label-new", "label-old"])
        mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "issue": {
                        "team": {"id": ACR113_TEAM_ID, "key": "ACR"},
                        "labels": {"nodes": [{"id": "label-old"}, {"id": "label-existing"}]},
                    }
                }
            },
        )
        update_issue = mocker.patch.object(client, "update_issue", return_value={"id": "issue"})

        client.apply_labels("ACR-1", "ACR", ["hardening"], replace=False)
        client.apply_labels("ACR-1", "ACR", ["hardening"], replace=True)

        assert update_issue.call_args_list[0].kwargs["label_ids"] == [
            "label-old",
            "label-existing",
            "label-new",
        ]
        assert update_issue.call_args_list[1].kwargs["label_ids"] == [
            "label-new",
            "label-old",
        ]


class TestACR113ReadbackAndProjectContracts:
    def test_get_issue_returns_real_labels_and_expanded_project(
        self, mocker: MockerFixture
    ) -> None:
        """T5: get_issue must query labels and project slug/team readback fields."""
        issue = {
            "id": "issue-uuid",
            "identifier": "ACR-1",
            "title": "Readback",
            "description": "body",
            "priority": 2,
            "estimate": None,
            "url": "https://linear.app/acme/issue/ACR-1",
            "branchName": "acr-1-readback",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
            "completedAt": None,
            "canceledAt": None,
            "dueDate": None,
            "team": {"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"},
            "assignee": None,
            "state": None,
            "project": {
                "id": ACR113_PROJECT_ID,
                "slugId": "acr-strategy",
                "name": "ACR Strategy",
                "teams": {"nodes": [{"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"}]},
            },
            "labels": {
                "nodes": [
                    {
                        "id": "label-hardening",
                        "name": "hardening",
                        "color": "#5e6ad2",
                        "team": {"id": ACR113_TEAM_ID, "key": "ACR"},
                    }
                ]
            },
            "parent": None,
        }
        client = LinearClient(api_key="test_key")
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={"data": {"issue": issue}},
        )

        result = client.get_issue("ACR-1")

        query = run_graphql.call_args.args[0]
        assert "labels" in query
        assert "color" in query
        assert "team {" in query
        assert "slugId" in query
        assert "teams {" in query
        assert result["labels"] == issue["labels"]["nodes"]
        assert result["project"]["slugId"] == "acr-strategy"
        assert result["project"]["teams"] == issue["project"]["teams"]["nodes"]

    @pytest.mark.parametrize(
        ("include_labels", "labels"),
        [(False, None), (True, None)],
        ids=["omitted", "null"],
    )
    def test_get_issue_rejects_missing_labels_field(
        self,
        mocker: MockerFixture,
        include_labels: bool,
        labels: dict[str, Any] | None,
    ) -> None:
        """T5: missing labels field is invalid; empty labels.nodes is the empty case."""
        issue = {
            "id": "issue-uuid",
            "identifier": "ACR-1",
            "title": "Readback",
            "description": "body",
            "priority": 2,
            "estimate": None,
            "url": "https://linear.app/acme/issue/ACR-1",
            "branchName": "acr-1-readback",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
            "completedAt": None,
            "canceledAt": None,
            "dueDate": None,
            "team": {"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"},
            "assignee": None,
            "state": None,
            "project": None,
            "parent": None,
        }
        if include_labels:
            issue["labels"] = labels
        client = LinearClient(api_key="test_key")
        mocker.patch.object(
            client,
            "_run_graphql",
            return_value={"data": {"issue": issue}},
        )

        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("ACR-1")

        assert exc_info.value.code == "INVALID_RESPONSE"
        assert "labels" in exc_info.value.message

    def test_get_issue_rejects_missing_project_field(self, mocker: MockerFixture) -> None:
        """T5: missing project field is invalid; project null is the no-project case."""
        issue = {
            "id": "issue-uuid",
            "identifier": "ACR-1",
            "title": "Readback",
            "description": "body",
            "priority": 2,
            "estimate": None,
            "url": "https://linear.app/acme/issue/ACR-1",
            "branchName": "acr-1-readback",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
            "completedAt": None,
            "canceledAt": None,
            "dueDate": None,
            "team": {"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"},
            "assignee": None,
            "state": None,
            "labels": {"nodes": []},
            "parent": None,
        }
        client = LinearClient(api_key="test_key")
        mocker.patch.object(
            client,
            "_run_graphql",
            return_value={"data": {"issue": issue}},
        )

        with pytest.raises(LinearClientError) as exc_info:
            client.get_issue("ACR-1")

        assert exc_info.value.code == "INVALID_RESPONSE"
        assert "project" in exc_info.value.message

    @pytest.mark.parametrize(
        ("include_labels", "labels"),
        [(False, None), (True, None)],
        ids=["omitted", "null"],
    )
    def test_search_issues_rejects_missing_labels_field(
        self,
        mocker: MockerFixture,
        include_labels: bool,
        labels: dict[str, Any] | None,
    ) -> None:
        """T5: second readback path must not synthesize labels from missing fields."""
        issue = {
            "id": "issue-uuid",
            "identifier": "ACR-1",
            "title": "Readback",
            "url": "https://linear.app/acme/issue/ACR-1",
            "state": None,
            "team": {"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"},
        }
        if include_labels:
            issue["labels"] = labels
        client = LinearClient(api_key="test_key")
        mocker.patch.object(
            client,
            "_run_graphql",
            return_value={"data": {"issues": {"nodes": [issue]}}},
        )

        with pytest.raises(LinearClientError) as exc_info:
            client.search_issues(team_id=ACR113_TEAM_ID)

        assert exc_info.value.code == "INVALID_RESPONSE"
        assert "labels" in exc_info.value.message

    def test_list_projects_team_filter_uses_variables_and_returns_slug_and_teams(
        self, mocker: MockerFixture
    ) -> None:
        """T6: list_projects pins team filter, includeArchived, first, slugId, and teams."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "_resolve_team_id", return_value=ACR113_TEAM_ID)
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "projects": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": ACR113_PROJECT_ID,
                                "name": "ACR Strategy",
                                "slugId": "acr-strategy",
                                "url": "https://linear.app/project/acr-strategy",
                                "archivedAt": None,
                                "teams": {
                                    "nodes": [
                                        {"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"}
                                    ]
                                },
                            }
                        ],
                    }
                }
            },
        )

        projects = client.list_projects(team_id="ACR", include_archived=True)

        query, variables = run_graphql.call_args.args
        assert "accessibleTeams: {id: {eq: $teamId}}" in query
        assert "includeArchived" in query
        assert "slugId" in query
        assert "archivedAt" in query
        assert "teams" in query
        assert variables == {"teamId": ACR113_TEAM_ID, "includeArchived": True, "first": 100}
        assert projects[0]["slugId"] == "acr-strategy"
        assert projects[0]["teams"] == [{"id": ACR113_TEAM_ID, "key": "ACR", "name": "ACR"}]

    def test_list_projects_without_team_omits_team_filter_and_team_variable(
        self, mocker: MockerFixture
    ) -> None:
        """T6: workspace project listing must not send teamId: null."""
        client = LinearClient(api_key="test_key")
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "projects": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [],
                    }
                }
            },
        )

        client.list_projects(team_id=None)

        query, variables = run_graphql.call_args.args
        assert "accessibleTeams" not in query
        assert "teamId" not in variables

    def test_resolve_project_id_matches_uuid_and_slug_with_team_scope(
        self, mocker: MockerFixture
    ) -> None:
        """T7: project UUIDs and slugIds resolve only from team-accessible projects."""
        client = LinearClient(api_key="test_key")
        list_projects = mocker.patch.object(
            client,
            "list_projects",
            return_value=[
                {
                    "id": ACR113_PROJECT_ID,
                    "slugId": "acr-strategy",
                    "name": "Do not match by name",
                    "teams": [{"id": ACR113_TEAM_ID, "key": "ACR"}],
                }
            ],
        )

        assert client.resolve_project_id("ACR", ACR113_PROJECT_ID) == ACR113_PROJECT_ID
        assert client.resolve_project_id("ACR", "acr-strategy") == ACR113_PROJECT_ID
        list_projects.assert_called_with(team_id="ACR", include_archived=False)

    def test_resolve_project_id_rejects_missing_names_urls_and_duplicate_slugs(
        self, mocker: MockerFixture
    ) -> None:
        """T7: no name/URL fallback; duplicate distinct projects are ambiguous."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(
            client,
            "list_projects",
            return_value=[
                {
                    "id": ACR113_PROJECT_ID,
                    "name": "ACR Strategy",
                    "slugId": "acr-strategy",
                    "url": "https://linear.app/project/acr-strategy",
                    "teams": [{"id": ACR113_TEAM_ID, "key": "ACR"}],
                },
                {
                    "id": ACR113_OTHER_PROJECT_ID,
                    "name": "Other",
                    "slugId": "acr-strategy",
                    "url": "https://linear.app/project/other",
                    "teams": [{"id": ACR113_TEAM_ID, "key": "ACR"}],
                },
            ],
        )

        with pytest.raises(LinearClientError) as exc_info:
            client.resolve_project_id("ACR", "ACR Strategy")
        assert exc_info.value.code == "NOT_FOUND"

        with pytest.raises(LinearClientError) as exc_info:
            client.resolve_project_id("ACR", "https://linear.app/project/acr-strategy")
        assert exc_info.value.code == "NOT_FOUND"

        with pytest.raises(LinearClientError) as exc_info:
            client.resolve_project_id("ACR", "acr-strategy")
        assert exc_info.value.code == "AMBIGUOUS_PROJECT"


class TestACR113IssueMutationInputs:
    def test_create_issue_sends_resolved_project_and_label_ids(
        self, mocker: MockerFixture
    ) -> None:
        """T9: IssueCreateInput carries teamId, projectId, labelIds, and scalars."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "_resolve_team_id", return_value=ACR113_TEAM_ID)
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "issueCreate": {
                        "success": True,
                        "issue": {
                            "id": "issue-uuid",
                            "identifier": "ACR-1",
                            "title": "Tuple create",
                            "url": "https://linear.app/acme/issue/ACR-1",
                            "branchName": "acr-1-tuple-create",
                        },
                    }
                }
            },
        )

        client.create_issue(
            team="ACR",
            title="Tuple create",
            description="body",
            project_id=ACR113_PROJECT_ID,
            label_ids=["label-hardening", "label-bug"],
            priority=2,
        )

        variables = run_graphql.call_args.args[1]
        assert variables == {
            "input": {
                "title": "Tuple create",
                "teamId": ACR113_TEAM_ID,
                "description": "body",
                "projectId": ACR113_PROJECT_ID,
                "priority": 2,
                "labelIds": ["label-hardening", "label-bug"],
            }
        }

    def test_create_issue_omits_absent_and_empty_optional_tuple_fields(
        self, mocker: MockerFixture
    ) -> None:
        """T9: absent project and absent or empty labels are omitted, never nulled."""
        client = LinearClient(api_key="test_key")
        mocker.patch.object(client, "_resolve_team_id", return_value=ACR113_TEAM_ID)
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "issueCreate": {
                        "success": True,
                        "issue": {
                            "id": "issue-uuid",
                            "identifier": "ACR-1",
                            "title": "No tuple",
                            "url": "https://linear.app/acme/issue/ACR-1",
                            "branchName": "acr-1-no-tuple",
                        },
                    }
                }
            },
        )

        client.create_issue(team="ACR", title="No tuple", project_id=None, label_ids=[])

        issue_input = run_graphql.call_args.args[1]["input"]
        assert issue_input == {"title": "No tuple", "teamId": ACR113_TEAM_ID}
        assert "projectId" not in issue_input
        assert "labelIds" not in issue_input

    def test_update_issue_sends_combined_issue_update_input(
        self, mocker: MockerFixture
    ) -> None:
        """T10: IssueUpdateInput carries projectId and labelIds with the issue id."""
        client = LinearClient(api_key="test_key")
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "issueUpdate": {
                        "success": True,
                        "issue": {
                            "id": "issue-uuid",
                            "identifier": "ACR-1",
                            "title": "Updated",
                            "url": "https://linear.app/acme/issue/ACR-1",
                            "updatedAt": "2026-01-01T00:00:00Z",
                        },
                    }
                }
            },
        )

        client.update_issue(
            issue_id="ACR-1",
            project_id=ACR113_PROJECT_ID,
            label_ids=["label-hardening", "label-bug"],
        )

        assert run_graphql.call_args.args[1] == {
            "id": "ACR-1",
            "input": {
                "projectId": ACR113_PROJECT_ID,
                "labelIds": ["label-hardening", "label-bug"],
            },
        }

    def test_update_issue_omits_unchanged_tuple_fields(self, mocker: MockerFixture) -> None:
        """T10: projectId and labelIds are independent optional update fields."""
        client = LinearClient(api_key="test_key")
        run_graphql = mocker.patch.object(
            client,
            "_run_graphql",
            return_value={
                "data": {
                    "issueUpdate": {
                        "success": True,
                        "issue": {
                            "id": "issue-uuid",
                            "identifier": "ACR-1",
                            "title": "Updated",
                            "url": "https://linear.app/acme/issue/ACR-1",
                            "updatedAt": "2026-01-01T00:00:00Z",
                        },
                    }
                }
            },
        )

        client.update_issue(issue_id="ACR-1", label_ids=["label-hardening"])
        label_only_input = run_graphql.call_args.args[1]["input"]
        assert label_only_input == {"labelIds": ["label-hardening"]}

        client.update_issue(issue_id="ACR-1", project_id=ACR113_PROJECT_ID)
        project_only_input = run_graphql.call_args.args[1]["input"]
        assert project_only_input == {"projectId": ACR113_PROJECT_ID}


def test_acr113_package_exports_remain_stable() -> None:
    """T20: ACR-113 does not silently expand clients.linear.__all__."""
    import clients.linear as linear_package

    assert linear_package.__all__ == ["LinearClient", "LinearClientError"]
    assert linear_package.LinearClient is LinearClient
    assert linear_package.LinearClientError is LinearClientError
