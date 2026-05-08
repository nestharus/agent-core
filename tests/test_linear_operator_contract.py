import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LINEAR_OPERATOR = REPO_ROOT / "agents" / "linear-operator.md"


def _operator_text() -> str:
    return LINEAR_OPERATOR.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"(?m)^## {re.escape(heading)}\s*$", text)
    assert match, f"missing section: {heading}"
    next_heading = re.search(r"(?m)^## ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def test_linear_operator_required_inputs_distinguish_team_scoped_from_known_key_tasks():
    """Risk: stale operator prose, agent-runner routing examples; level: structural.

    Source: ACR-22 proposal Test-Intent T8 and assumptions A1/A2/A7.
    """
    required_inputs = _section(_operator_text(), "Required Inputs")

    assert "`linear_team_key` is required" in required_inputs
    for team_scoped_task in (
        "create",
        "list-issues",
        "list-projects",
        "search",
        "list-labels",
        "create-label",
        "apply-labels",
    ):
        assert f"`{team_scoped_task}`" in required_inputs
    assert "`query`" not in required_inputs
    assert re.search(
        r"(?is)issue_key.{0,200}required.{0,200}apply-labels",
        required_inputs,
    )
    assert "`linear_team_key` is not required" in required_inputs
    for known_key_term in ("known-issue-key", "`read`", "`comment`"):
        assert known_key_term in required_inputs


def test_linear_operator_search_section_names_actual_issue_commands():
    """Risk: stale operator prose, agent-runner routing examples; level: structural.

    Source: ACR-22 proposal Test-Intent T8 and assumptions A1/A2/A7.
    """
    search_section = _section(_operator_text(), "Procedure: Search")

    assert "list-issues --team" in search_section
    assert "search-issues --team-key" in search_section
    assert "search-issues --team-id" not in search_section
    assert "The CLI does not directly expose a search subcommand" not in search_section


def test_linear_operator_uses_non_nes_known_issue_examples():
    """Risk: stale operator prose, agent-runner routing examples; level: structural.

    Source: ACR-22 proposal Test-Intent T8 and assumptions A1/A2/A7.
    """
    text = _operator_text()

    assert re.search(r"\b(?:AGE|AST)-\d+\b", text)


def test_linear_operator_does_not_use_agent_runner_as_active_label_guidance():
    """Risk: stale operator prose, agent-runner routing examples; level: structural.

    Source: ACR-22 proposal Test-Intent T8 and assumptions A1/A2/A7.
    """
    lines = _operator_text().splitlines()
    active_agent_runner_lines = [
        line
        for line in lines
        if "agent-runner" in line
        and not re.search(r"\b(deprecated|historical|history|legacy)\b", line, re.I)
    ]

    assert active_agent_runner_lines == []


def test_linear_operator_does_not_assert_four_heading_brief_contract():
    """Risk: stale operator prose, four-heading ticket-contract drift; level: structural.

    Source: ACR-110 proposal Test-Intent T1; assumption-register A1/A2/A3.
    """
    text = _operator_text()

    stale_contract_pattern = re.compile(
        r"(?is)(?:MUST\s+contain|validates?\s+that|validation\s+requires|"
        r"requires\b).{0,240}`Code Boundary`.{0,80}`Test Boundary`.{0,80}"
        r"`Acceptance Criteria`.{0,80}`Anti-scope`"
    )
    stale_contract_matches = [
        re.sub(r"\s+", " ", match.group(0)).strip()
        for match in stale_contract_pattern.finditer(text)
    ]

    assert stale_contract_matches == []
