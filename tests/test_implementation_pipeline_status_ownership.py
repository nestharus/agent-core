import re
from pathlib import Path

from clients.linear.client import ROUTINE_MANAGER_OWNED_STATES


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


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

    assert "Phase 0" in text
    assert "Final" in text
    assert "orchestrator itself does not transition status" in text or (
        "orchestrator" in text and "does not transition" in text
    )
    assert not re.search(
        r"(?is)(?:Phase 0|Phase 9|Final)[\s\S]{0,1600}"
        r"(task\s*=\s*transition|transition-issue|target_status)",
        text,
    )
