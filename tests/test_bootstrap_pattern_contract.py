import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONVENTION = REPO_ROOT / "conventions" / "bootstrap-pattern.md"


def _bootstrap_text() -> str:
    return CONVENTION.read_text(encoding="utf-8")


def test_acr113_bootstrap_ticketing_wrapper_facts_include_linear_tuple() -> None:
    """T18: ticketing wrappers carry team, optional project, and per-team labels."""
    text = _bootstrap_text()

    assert "Linear" in text
    assert re.search(r"(?is)team key.{0,120}(required|must)", text)
    assert re.search(r"(?is)optional.{0,120}project.{0,120}(UUID|uuid|slugId)", text)
    assert re.search(r"(?is)(per-team|team-scoped).{0,120}label", text)


def test_acr113_bootstrap_parent_routing_remains_explicit() -> None:
    """T18: parent routing stays an explicit wrapper fact, not inferred."""
    text = _bootstrap_text()

    assert re.search(r"(?is)parent.{0,80}(explicit|routing)", text)


def test_bootstrap_pattern_has_no_ambiguous_future_wiring_deferrals() -> None:
    """Project-bootstrap procedural wiring should be referenced, not punted."""
    text = _bootstrap_text()

    forbidden = (
        "future WU",
        "may add checks later",
        "deferred",
        "not yet wired",
        "not yet implemented",
        "not currently enforced",
    )
    for phrase in forbidden:
        assert phrase not in text, f"ambiguous deferral remains: {phrase}"

    assert (
        "`~/ai/workflows/project-bootstrap.md` § Emission steps 1-5"
        in text
    )
    assert "§ Closed Path Dispatch Contract" in text
    assert "§ Re-Bootstrap Trigger" in text
