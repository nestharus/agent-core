from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_ORCHESTRATOR = REPO_ROOT / "agents" / "prototype-orchestrator.md"
RELEASE_ORCHESTRATOR = REPO_ROOT / "agents" / "release-orchestrator.md"


def _without_acr126_p4_exception_lines(text: str) -> str:
    start_marker = "5. **If `defer_source` was set**:"
    end_marker = "6. **If the prototype's own ticket is set**:"
    if start_marker not in text or end_marker not in text:
        return text
    before, rest = text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)
    return f"{before}{end_marker}{after}"


def test_prototype_orchestrator_defers_wu_status_transitions_to_manager() -> None:
    text = PROTOTYPE_ORCHESTRATOR.read_text(encoding="utf-8")
    default_status_text = _without_acr126_p4_exception_lines(text)

    assert "Ticket status transitions are manager-owned" in text
    assert "Ticket status transitions are manager-owned; the prototype-orchestrator does not" in text
    assert "prototype-orchestrator does not" in text
    assert "Optionally transition to `Done`" not in default_status_text
    assert "Do not transition the deferring WU's status" not in default_status_text
    assert "that's user-owned" not in default_status_text


def test_release_orchestrator_distinguishes_release_lifecycle_from_wu_status() -> None:
    text = RELEASE_ORCHESTRATOR.read_text(encoding="utf-8")

    assert "release lifecycle" in text
    assert "routine WU ticket status" in text
    assert "manager-owned" in text
    assert "lifecycle state changes remain user-owned" not in text
    assert "does not introduce a ticket `task=transition` dispatch" in text
