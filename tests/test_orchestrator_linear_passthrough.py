import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _orchestrator_text() -> str:
    return ORCHESTRATOR.read_text(encoding="utf-8")


def test_orchestrator_linear_inputs_pass_to_create_list_search_dispatches():
    """Risk: later-dispatch ambiguity; level: structural.

    Source: ACR-22 proposal Test-Intent T9 and assumption A8.
    """
    text = _orchestrator_text()

    assert "`linear_team_key` is passed through for team-scoped create, list, and search" in text
    assert "`linear_project_id`, when supplied, is passed through only to create" in text


def test_orchestrator_known_issue_read_comment_needs_no_separate_team_selection():
    """Risk: later-dispatch ambiguity; level: structural.

    Source: ACR-22 proposal Test-Intent T9 and assumption A8.
    """
    text = _orchestrator_text()

    assert "Known-issue-key read/comment dispatches" in text
    assert "do not require separate team selection" in text
