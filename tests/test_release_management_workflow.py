"""Shape guards for NES-242 release-management workflow surfaces.

Contract:
/home/nes/projects/ai/planning/nes-242-release-management-workflow/contracts/nes-242-release-management-workflow.md
"""

import json
import re
from pathlib import Path

import pytest

from tools.workflow_index.generator import DISPATCH_CONTRACT_KEYS, parse_frontmatter


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MD = REPO_ROOT / "workflows" / "release-management.md"
INDEX_JSON = REPO_ROOT / "workflows" / "index.json"

EXPECTED_H2_HEADINGS = [
    "## Purpose",
    "## Workflow Dispatch Surface",
    "## Use When",
    "## Do Not Use When",
    "## Required Inputs",
    "## Phase Map",
    "## Gate Ownership Table",
    "## Cross-references",
    "## Philosophy Mapping",
    "## Stop Conditions And Escalation",
    "## Anti-Scope",
]
TICKET_REQUIRED_HEADING_SUBSET = [
    "## Use When",
    "## Required Inputs",
    "## Phase Map",
    "## Gate Ownership Table",
    "## Cross-references",
    "## Philosophy Mapping",
]
REQUIRED_INPUT_SENTINELS = [
    "repo_root",
    "worktree_path",
    "scratch_dir",
    "planning_dir",
    "release_id",
    "develop_branch_name",
    "main_branch_name",
    "release_manifest_path",
    "freeze_window",
    "qa_evidence_path",
    "hotfix_policy",
    "reconcile_obligations",
]
PHASE_ORDER = [
    "cut",
    "freeze",
    "hotfix-cherry-pick",
    "promote",
    "tag",
    "reconcile",
]
BRANCH_TOPOLOGY_SENTINELS = ["develop", "release/*", "hotfix/*", "main", "tag"]
GATE_TABLE_HEADERS = [
    "Phase",
    "Gate",
    "Owner",
    "Who resolves failure / NEEDS_INPUT",
    "Evidence artifact",
    "Runbook-shaped human ticket?",
    "Philosophy principles",
]
GATE_PHASE_SENTINELS = [
    "cut",
    "freeze",
    "hotfix-cherry-pick",
    "promote",
    "tag",
    "reconcile",
    "final closure",
]
WIRED_OPERATOR_PATHS = [
    "~/ai/agents/release-orchestrator.md",
    "~/ai/agents/release-cut-operator.md",
    "~/ai/agents/release-hotfix-operator.md",
    "~/ai/agents/release-promote-operator.md",
    "~/ai/agents/release-reconcile-operator.md",
]
WIRED_OPERATOR_TICKETS = ["NES-243", "NES-244", "NES-245", "NES-246", "NES-247"]
PHILOSOPHY_SOURCE_PATH = (
    "/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md"
)
PHILOSOPHY_TABLE_HEADERS = [
    "Workflow surface",
    "Phase / gate / operator",
    "Source principle ids",
    "Source path",
    "How the workflow applies it",
]
REQUIRED_PHILOSOPHY_PRINCIPLES = [
    "P1",
    "P5",
    "P8",
    "P9",
    "P11",
    "P12",
    "P14",
    "P16",
    "T1",
]


def _read_required_file(path):
    assert path.is_file(), f"missing required file: {path}"
    return path.read_text(encoding="utf-8")


def _frontmatter_and_body(text):
    assert text.startswith("---\n") or text.startswith("---\r\n"), (
        "workflow file must start with YAML frontmatter"
    )
    lines = text.splitlines()
    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    assert closing_index is not None, "workflow frontmatter must close with ---"

    parsed = parse_frontmatter(text, str(WORKFLOW_MD))
    assert isinstance(parsed, dict), "workflow frontmatter must parse as a mapping"
    return parsed, "\n".join(lines[closing_index + 1 :])


@pytest.fixture(scope="module")
def workflow_document():
    if not WORKFLOW_MD.is_file():
        return {
            "error": f"missing required file: {WORKFLOW_MD}",
            "text": "",
            "frontmatter": {},
            "body": "",
        }
    text = WORKFLOW_MD.read_text(encoding="utf-8")
    if not text.strip():
        return {
            "error": "workflow file must be non-empty",
            "text": text,
            "frontmatter": {},
            "body": "",
        }
    parsed, body = _frontmatter_and_body(text)
    return {"error": None, "text": text, "frontmatter": parsed, "body": body}


def _require_workflow_document(workflow_document):
    assert workflow_document["error"] is None, workflow_document["error"]
    return workflow_document


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    if not match:
        pytest.fail(f"missing section heading: {heading}")

    heading_level = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{heading_level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _contains_all(text, substrings):
    missing = [item for item in substrings if item not in text]
    assert missing == [], f"missing expected substrings: {missing}"


def _assert_ordered_substrings(text, substrings):
    position = -1
    for substring in substrings:
        next_position = text.find(substring, position + 1)
        assert next_position != -1, f"missing or misordered substring: {substring}"
        position = next_position


def _heading_lines(body, level):
    prefix = "#" * level
    pattern = re.compile(rf"^{re.escape(prefix)}\s+")
    return [line.strip() for line in body.splitlines() if pattern.match(line.strip())]


def _assert_table_header(section, expected_headers):
    expected = [item.strip() for item in expected_headers]
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells == expected:
            return
    pytest.fail(f"missing Markdown table header: {expected}")


def _index_workflows_mapping():
    index = json.loads(_read_required_file(INDEX_JSON))
    workflows = index.get("workflows")
    assert isinstance(workflows, dict), "workflow index must contain workflows mapping"
    return workflows


def test_release_management_workflow_file_exists_and_nonempty():
    assert WORKFLOW_MD.is_file(), f"missing workflow file: {WORKFLOW_MD}"
    assert WORKFLOW_MD.stat().st_size > 0, "workflow file must be non-empty"


def test_frontmatter_parses(workflow_document):
    document = _require_workflow_document(workflow_document)
    assert isinstance(document["frontmatter"], dict)
    assert document["body"].strip(), "workflow body must be non-empty"


def test_workflow_id_is_release_management(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    assert parsed.get("workflow", {}).get("id") == "release-management"


def test_workflow_id_matches_filename_stem(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    assert parsed.get("workflow", {}).get("id") == WORKFLOW_MD.stem


def test_dispatch_contract_has_exact_five_keys(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    contract = parsed.get("workflow_dispatch_contract")

    assert isinstance(contract, dict), "missing workflow_dispatch_contract mapping"
    assert set(contract) == DISPATCH_CONTRACT_KEYS, (
        "workflow_dispatch_contract must have exactly "
        f"{sorted(DISPATCH_CONTRACT_KEYS)}"
    )
    assert isinstance(contract["orchestrator"], str)
    assert contract["orchestrator"].strip(), "orchestrator must be non-empty"

    for key in ("inputs", "expectations", "outputs", "non_goals"):
        value = contract[key]
        assert isinstance(value, list), f"{key} must be a list"
        assert value, f"{key} must be non-empty"
        assert all(isinstance(item, str) and item.strip() for item in value), (
            f"{key} must contain only non-empty strings"
        )


def test_dispatch_contract_orchestrator_is_release_orchestrator(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    contract = parsed.get("workflow_dispatch_contract", {})

    assert contract.get("orchestrator") == "release-orchestrator"


def test_workflow_aliases_block_is_absent(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    assert "workflow_aliases" not in parsed


def test_top_level_heading_is_release_management_workflow(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    h1_headings = _heading_lines(body, 1)

    assert h1_headings[:1] == ["# Release Management Workflow"]


def test_full_ordered_h2_heading_list(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    assert _heading_lines(body, 2) == EXPECTED_H2_HEADINGS


def test_ticket_required_heading_subset_in_order(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    _assert_ordered_substrings("\n".join(_heading_lines(body, 2)), TICKET_REQUIRED_HEADING_SUBSET)


def test_required_inputs_lists_release_shaped_names(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    required_inputs = _section_after_heading(body, "## Required Inputs")

    _contains_all(required_inputs, REQUIRED_INPUT_SENTINELS)


def test_phase_map_orders_phases_correctly(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    phase_map = _section_after_heading(body, "## Phase Map")

    _assert_ordered_substrings(phase_map, PHASE_ORDER)


def test_branch_topology_present_in_body(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    _contains_all(body, BRANCH_TOPOLOGY_SENTINELS)


def test_gate_ownership_table_columns_in_order(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    gate_section = _section_after_heading(body, "## Gate Ownership Table")

    _assert_table_header(gate_section, GATE_TABLE_HEADERS)


def test_gate_ownership_table_required_phase_rows(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    gate_section = _section_after_heading(body, "## Gate Ownership Table")

    _contains_all(gate_section, GATE_PHASE_SENTINELS)


def test_human_settings_boundary_vocabulary_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    gate_section = _section_after_heading(body, "## Gate Ownership Table")

    _contains_all(gate_section, ("runbook", "settings"))
    assert "human" in gate_section
    assert "~/ai/workflows/tiered-approval.md" in body or "Tier-3" in body


def test_hotfix_override_gate_vocabulary_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    gate_section = _section_after_heading(body, "## Gate Ownership Table")

    _contains_all(gate_section, ("blast-radius", "rehearsal", "override", "cherry-pick"))


def test_reconcile_gate_blocks_closure(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    gate_section = _section_after_heading(body, "## Gate Ownership Table")
    stop_section = _section_after_heading(body, "## Stop Conditions And Escalation")
    combined = "\n".join((gate_section, stop_section))

    assert re.search(r"reconcile.*blocks closure|blocks closure.*reconcile", combined, re.I | re.S)


def test_philosophy_source_path_cited(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    philosophy = _section_after_heading(body, "## Philosophy Mapping")

    assert PHILOSOPHY_SOURCE_PATH in philosophy


def test_philosophy_mapping_table_columns(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    philosophy = _section_after_heading(body, "## Philosophy Mapping")

    _assert_table_header(philosophy, PHILOSOPHY_TABLE_HEADERS)


def test_required_philosophy_principles_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    philosophy = _section_after_heading(body, "## Philosophy Mapping")

    _contains_all(philosophy, REQUIRED_PHILOSOPHY_PRINCIPLES)


def test_wired_operator_paths_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    cross_references = _section_after_heading(body, "## Cross-references")

    _contains_all(cross_references, WIRED_OPERATOR_PATHS)


def test_wired_operator_marker_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    cross_references = _section_after_heading(body, "## Cross-references")

    assert "wired" in cross_references
    assert "forward reference" not in cross_references


def test_wired_operator_nes_ticket_numbers_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    cross_references = _section_after_heading(body, "## Cross-references")

    _contains_all(cross_references, WIRED_OPERATOR_TICKETS)


def test_anti_scope_section_encodes_required_boundaries(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    anti_scope = _section_after_heading(body, "## Anti-Scope")

    assert "orchestrator" in anti_scope
    assert "sub-operator" in anti_scope or "release-cut-operator" in anti_scope
    assert "AGENTS" in anti_scope
    assert "wrapper" in anti_scope or "project-specific" in anti_scope
    assert "convention" in anti_scope
    assert "settings" in anti_scope or "live release" in anti_scope


def test_workflow_index_contains_release_management_entry():
    workflows = _index_workflows_mapping()
    entry = workflows.get("release-management")

    assert isinstance(entry, dict), "workflow index missing release-management entry"
    assert entry.get("workflow", {}).get("id") == "release-management"


def test_workflow_index_release_management_entry_path():
    workflows = _index_workflows_mapping()
    entry = workflows.get("release-management")

    assert isinstance(entry, dict), "workflow index missing release-management entry"
    assert entry.get("path") == "workflows/release-management.md"


def test_workflow_index_release_management_entry_dispatch_contract_matches_frontmatter():
    workflow_text = _read_required_file(WORKFLOW_MD)
    parsed = parse_frontmatter(workflow_text, str(WORKFLOW_MD))
    workflows = _index_workflows_mapping()
    entry = workflows.get("release-management")

    assert isinstance(entry, dict), "workflow index missing release-management entry"
    assert entry.get("workflow_dispatch_contract") == parsed.get(
        "workflow_dispatch_contract"
    )
