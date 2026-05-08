from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_ORCHESTRATOR = REPO_ROOT / "agents" / "prototype-orchestrator.md"
RELEASE_ORCHESTRATOR = REPO_ROOT / "agents" / "release-orchestrator.md"


def test_prototype_orchestrator_defers_wu_status_transitions_to_manager() -> None:
    text = PROTOTYPE_ORCHESTRATOR.read_text(encoding="utf-8")

    assert "Ticket status transitions are manager-owned" in text
    assert "prototype-orchestrator does not" in text
    assert "Optionally transition to `Done`" not in text
    assert "Do not transition the deferring WU's status" not in text
    assert "that's user-owned" not in text


def test_release_orchestrator_distinguishes_release_lifecycle_from_wu_status() -> None:
    text = RELEASE_ORCHESTRATOR.read_text(encoding="utf-8")

    assert "release lifecycle" in text
    assert "routine WU ticket status" in text
    assert "manager-owned" in text
    assert "lifecycle state changes remain user-owned" not in text
    assert "does not introduce a ticket `task=transition` dispatch" in text
