import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPERATOR = REPO_ROOT / "agents" / "linear-operator.md"


def _operator_text() -> str:
    return OPERATOR.read_text(encoding="utf-8")


def test_acr113_operator_search_uses_live_cli_tuple_filters() -> None:
    """T15: operator search/list procedures use the real CLI, not direct Python."""
    text = _operator_text()

    assert "CLI does not directly expose a search subcommand" not in text
    assert "search-issues" in text
    assert "list-issues" in text
    assert "--team" in text
    assert "--project" in text
    assert "--label" in text


def test_acr113_operator_documents_label_project_error_contracts() -> None:
    """T15: label/project resolution and mismatch failures are operator-visible."""
    text = _operator_text()

    for token in ["AMBIGUOUS_LABEL", "AMBIGUOUS_PROJECT", "INVALID_INPUT"]:
        assert token in text
    assert re.search(r"(?is)team.{0,80}label.{0,80}(wins|precedence)", text)
    assert re.search(r"(?is)same-tier.{0,120}duplicate|duplicate.{0,120}same-tier", text)
    assert re.search(r"(?is)project.{0,120}(UUID|uuid).{0,120}slugId", text)
    assert re.search(r"(?is)issue.{0,120}team.{0,120}mismatch", text)


def test_acr113_operator_readback_uses_real_get_issue_labels() -> None:
    """T15: Phase 0 readback frontmatter must use labels returned by get-issue."""
    text = _operator_text()

    assert "get-issue" in text
    assert re.search(r"(?is)labels:.{0,160}get-issue|get-issue.{0,160}labels", text)
    assert "slugId" in text
