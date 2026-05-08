import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _orchestrator_text() -> str:
    return ORCHESTRATOR.read_text(encoding="utf-8")


def test_acr113_orchestrator_linear_inputs_preserve_team_and_project_token() -> None:
    """T16: orchestrator inputs keep linear_project_id but allow UUID or slugId."""
    text = _orchestrator_text()

    assert "linear_team_key" in text
    assert "linear_project_id" in text
    assert re.search(r"(?is)linear_project_id.{0,180}(UUID|uuid).{0,120}slugId", text)


def test_acr113_orchestrator_phase0_readback_mentions_real_labels() -> None:
    """T16: Phase 0 Linear readback names labels as a frontmatter/readback field."""
    text = _orchestrator_text()

    assert re.search(r"(?is)Phase 0.{0,900}Linear.{0,900}labels", text)
    assert re.search(r"(?is)get-issue.{0,240}labels|labels.{0,240}get-issue", text)


def test_acr113_orchestrator_phase9_remains_key_only() -> None:
    """T16: Phase 9 cross-linking remains key-only and does not expand tuple routing."""
    text = _orchestrator_text()
    phase9_match = re.search(r"(?is)### Phase 9\b(?P<body>.*?)(?:### Phase 10\b|$)", text)
    assert phase9_match is not None
    phase9 = phase9_match.group("body")

    assert re.search(r"(?is)key-only|issue_key|ticket_id", phase9)
    assert not re.search(r"(?is)project.{0,80}label.{0,80}expand", phase9)
