import re
from pathlib import Path

from clients.linear.client import ROUTINE_MANAGER_OWNED_STATES


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _section_with_heading_matching(text: str, heading_pattern: str) -> str:
    match = re.search(rf"(?m)^(?P<marks>##+)\s+.*(?:{heading_pattern}).*$", text)
    assert match, f"missing section heading matching: {heading_pattern}"
    level = len(match.group("marks"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def test_implementation_pipeline_workflow_names_manager_owned_routine_status_path() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "manager-owned" in text
    for state in ROUTINE_MANAGER_OWNED_STATES:
        assert state in text
    assert "Todo to In Progress" in text or "Todo -> In Progress" in text
    assert "In Progress back to Todo" in text or "In Progress -> Todo" in text
    assert "GitHub close-keyword automation" in text
    assert "orchestrator itself does not transition status" in text


def test_implementation_pipeline_orchestrator_keeps_status_transition_out_of_phases() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")

    assert "ticket status transitions are manager-owned" in text
    assert "ticket status transitions are manager-owned. This orchestrator does not move ticket state" in text
    assert "orchestrator" in text
    assert "does not transition" in text
    assert "audit-history close" in text
    assert "comment" in text
    for phrase in (
        "status changes are user-owned",
        "The Linear path intentionally omits status transitions",
        "status transitions are user-owned",
        "not pipeline-owned",
    ):
        assert phrase not in text


def test_implementation_pipeline_orchestrator_does_not_dispatch_transition_tasks() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    transition_scan = "\n".join(
        (
            _section_with_heading_matching(text, r"Phase 0"),
            _section_with_heading_matching(text, r"Phase 3"),
            _section_with_heading_matching(text, r"Phase 4"),
            _section_with_heading_matching(text, r"Phase 5"),
            _section_with_heading_matching(text, r"Phase 6"),
            _section_with_heading_matching(text, r"Phase 7"),
            _section_with_heading_matching(text, r"Phase 8"),
        )
    )

    assert "Phase 0" in text
    assert "Final" in text
    assert "orchestrator itself does not transition status" in text or (
        "orchestrator" in text and "does not transition" in text
    )
    assert not re.search(
        r"(?is)(task\s*=\s*transition|transition-issue|target_status)",
        transition_scan,
    )
