import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONVENTION = REPO_ROOT / "conventions" / "connection-abstraction.md"


def _convention_text() -> str:
    return CONVENTION.read_text(encoding="utf-8")


def test_acr113_linear_project_conn_is_system_plus_team_with_optional_project_scope() -> None:
    """T17: Linear Project-conn identity is system + team key; project is scope."""
    text = _convention_text()

    assert "Linear" in text
    assert "System-conn" in text
    assert re.search(r"(?is)team key", text)
    assert re.search(r"(?is)optional.{0,120}project.{0,120}(UUID|uuid|slugId)", text)


def test_acr113_labels_are_filters_not_project_conn_identity() -> None:
    """T17: labels remain filters/conventions, not Project-conn identity."""
    text = _convention_text()

    assert re.search(r"(?is)labels?.{0,120}(filter|convention)", text)
    assert re.search(r"(?is)not.{0,80}(identity|Project-conn identity)", text)
    assert not re.search(r"(?is)labels?.{0,80}(are|as).{0,80}Project-conn identity", text)
