"""Structural tests for NES-221 AGENTS.md routing rows."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
AGENTS_STRUCTURE_TEST = REPO_ROOT / "tests" / "test_agentsmd_structure.py"


def _agents_text():
    return AGENTS_MD.read_text(encoding="utf-8")


def _assert_operator_row(name, description, inputs):
    text = _agents_text()
    path = f"agents/{name}.md"
    file_link = f"File: [~/ai/{path}]({path})"
    pattern = (
        rf"(?ms)^- `{re.escape(name)}` - {re.escape(description)}\.\s*\n"
        rf"\s+{re.escape(file_link)} \| Inputs: {re.escape(inputs)} "
        rf"\| Model: `gpt-high`$"
    )
    assert re.search(pattern, text), f"missing or malformed AGENTS.md row: {name}"


def test_agentsmd_contains_workflow_design_auditor_routing_row():
    """T17: AGENTS.md contains the workflow-design-auditor routing row."""
    _assert_operator_row(
        "workflow-design-auditor",
        "Audit workflow document design against the shared design-pattern corpus; does not audit runtime execution",
        "`workflow_file`, `repo_root`, `design_patterns_ref?`, `context_files?`, `audit_history_path?`, `report_path?`, `mode?`",
    )


def test_agentsmd_contains_agent_design_auditor_routing_row():
    """T18: AGENTS.md contains the agent-design-auditor routing row."""
    _assert_operator_row(
        "agent-design-auditor",
        "Audit operator prompt design, operator-file-format conformance, and single-concern shape; does not maintain AGENTS routing",
        "`operator_file`, `repo_root`, `operator_format_ref?`, `design_patterns_ref?`, `context_files?`, `audit_history_path?`, `report_path?`, `mode?`",
    )


def test_existing_agentsmd_structure_suite_remains_present():
    """T19: Existing AGENTS.md structure tests remain collected alongside NES-221 row tests."""
    assert AGENTS_STRUCTURE_TEST.exists()
    structure_text = AGENTS_STRUCTURE_TEST.read_text(encoding="utf-8")
    for test_name in (
        "test_all_relative_links_in_agents_md_resolve",
        "test_routing_table_rows_preserved",
        "test_existing_section_headings_preserved",
    ):
        assert f"def {test_name}(" in structure_text


def test_agentsmd_omits_future_audit_workflow_entries():
    """T20: AGENTS.md does not add NES-224 pipeline wiring before it lands.

    The original guard also excluded `workflow-process-auditor`. That row is now in
    scope because NES-222 ships it; the row's structural assertions live in
    `tests/test_agentsmd_structure.py`. NES-223 now lands the Audit sub-workflow
    row, so this guard only protects against premature NES-224 / NES-219D
    `pipeline_entry_mode` wiring.
    """
    text = _agents_text()

    assert "pipeline_entry_mode" not in text
