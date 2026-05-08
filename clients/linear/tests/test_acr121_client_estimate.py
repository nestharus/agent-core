import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from clients.linear.client import ALLOWED_ESTIMATES, LinearClient, LinearClientError


TEAM_ID = "11111111-1111-1111-1111-111111111111"
def _mock_response(data: dict[str, Any]) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(data).encode("utf-8")
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    return response


def _teams_response() -> dict[str, Any]:
    return {
        "data": {
            "teams": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"id": TEAM_ID, "name": "ACR", "key": "ACR"}],
            }
        }
    }


def _create_response() -> dict[str, Any]:
    return {
        "data": {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue-uuid",
                    "identifier": "ACR-121",
                    "title": "Estimated issue",
                    "url": "https://linear.app/acme/issue/ACR-121",
                    "branchName": "acr-121-estimated-issue",
                },
            }
        }
    }


def _request_payload(request: object) -> dict[str, Any]:
    data = getattr(request, "data")
    assert isinstance(data, bytes)
    return json.loads(data.decode("utf-8"))


def _issue_create_input(mock_urlopen: MagicMock) -> dict[str, Any]:
    request = mock_urlopen.call_args_list[-1].args[0]
    payload = _request_payload(request)
    return payload["variables"]["input"]


def _mock_create_urlopen(mocker: MockerFixture) -> MagicMock:
    mock_urlopen = mocker.patch("urllib.request.urlopen")
    mock_urlopen.side_effect = [
        _mock_response(_teams_response()),
        _mock_response(_create_response()),
    ]
    return mock_urlopen


def test_create_issue_includes_estimate_in_input_when_supplied(
    mocker: MockerFixture,
) -> None:
    mock_urlopen = _mock_create_urlopen(mocker)

    LinearClient(api_key="test_key").create_issue(
        team="ACR",
        title="Estimated issue",
        estimate=5,
    )

    assert _issue_create_input(mock_urlopen)["estimate"] == 5


def test_create_issue_omits_estimate_when_not_supplied(
    mocker: MockerFixture,
) -> None:
    mock_urlopen = _mock_create_urlopen(mocker)

    LinearClient(api_key="test_key").create_issue(
        team="ACR",
        title="Unestimated issue",
        estimate=None,
    )

    assert "estimate" not in _issue_create_input(mock_urlopen)


def test_create_issue_rejects_non_fibonacci_estimate() -> None:
    with pytest.raises(LinearClientError) as exc_info:
        LinearClient(api_key="test_key").create_issue(
            team="ACR",
            title="Invalid estimate",
            estimate=4,
        )

    assert exc_info.value.code == "INVALID_INPUT"
    assert "fibonacci" in exc_info.value.message.lower()


@pytest.mark.parametrize("estimate", sorted(ALLOWED_ESTIMATES))
def test_create_issue_accepts_each_fibonacci_value(
    mocker: MockerFixture,
    estimate: int,
) -> None:
    mock_urlopen = _mock_create_urlopen(mocker)

    LinearClient(api_key="test_key").create_issue(
        team="ACR",
        title=f"Estimate {estimate}",
        estimate=estimate,
    )

    assert _issue_create_input(mock_urlopen)["estimate"] == estimate
