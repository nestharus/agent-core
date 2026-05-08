import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINEAR_OPERATOR = REPO_ROOT / "agents" / "linear-operator.md"
JIRA_OPERATOR = REPO_ROOT / "agents" / "jira-operator.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _update_estimate_region(text: str) -> str:
    match = re.search(r"(?is)task=update-estimate.*", text)
    assert match, "missing task=update-estimate"
    following = text[match.start() :]
    next_task = re.search(r"(?im)^- .*`task=", following[1:])
    next_heading = re.search(r"(?m)^#{2,3} ", following[1:])
    cut_points = [
        point.start() + 1
        for point in (next_task, next_heading)
        if point is not None
    ]
    if cut_points:
        return following[: min(cut_points)]
    return following


def test_linear_read_frontmatter_renders_normalized_estimate_metadata() -> None:
    text = _read(LINEAR_OPERATOR)

    for required in (
        "task=read",
        "frontmatter",
        "story_point_estimate",
        "estimate_source",
        "estimate_rationale",
        'estimate_field: "estimate"',
        "get-issue",
        "description",
    ):
        assert required in text


def test_jira_read_fetches_customfield_10016_and_renders_normalized_estimate_metadata() -> None:
    text = _read(JIRA_OPERATOR)

    for required in (
        "task=read",
        "customfield_10016",
        "frontmatter",
        "story_point_estimate",
        "estimate_source",
        "estimate_rationale",
        'estimate_field: "customfield_10016"',
        "description",
    ):
        assert required in text


def test_ticket_operators_document_backend_neutral_update_estimate_task() -> None:
    for text in (_read(LINEAR_OPERATOR), _read(JIRA_OPERATOR)):
        region = _update_estimate_region(text)
        for required in (
            "task=update-estimate",
            "issue_key",
            "estimate",
            "inherited_story_point_estimate",
            "estimate_source",
            "estimate_delta_rationale",
            "estimate_delta_flag",
        ):
            assert required in region


def test_linear_update_estimate_task_uses_cli_estimate_and_rationale_note() -> None:
    region = _update_estimate_region(_read(LINEAR_OPERATOR))

    for required in (
        "clients.linear.cli update-issue",
        "--estimate <int>",
        "Markdown",
        "inherited estimate",
        "refined estimate",
        "source",
        "delta rationale",
    ):
        assert required in region


def test_jira_update_estimate_task_uses_customfield_put_and_adf_note() -> None:
    region = _update_estimate_region(_read(JIRA_OPERATOR))

    for required in (
        "PUT /rest/api/3/issue/{issueKey}",
        "fields.customfield_10016",
        "ADF",
        "inherited estimate",
        "refined estimate",
        "source",
        "delta rationale",
    ):
        assert required in region


def test_update_estimate_contract_does_not_transition_status() -> None:
    for text in (_read(LINEAR_OPERATOR), _read(JIRA_OPERATOR)):
        region = _update_estimate_region(text)
        assert re.search(r"(?is)(does not|must not|never).{0,80}(transition|status|state)", region)
        assert "POST /rest/api/3/issue/{issueKey}/transitions" not in region
        assert "transitionId" not in region
        assert "--status" not in region
        assert "state_id" not in region
