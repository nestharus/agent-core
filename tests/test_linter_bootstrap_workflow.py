"""Shape guards for NES-138 linter-bootstrap workflow surfaces.

Contract:
/home/nes/projects/ai/planning/nes-138-linter-bootstrap-workflow/.scratch/contracts/nes-138-linter-bootstrap-workflow.md
"""

import json
import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MD = REPO_ROOT / "workflows" / "linter-bootstrap.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
README_MD = REPO_ROOT / "README.md"
WORKFLOW_INDEX_JSON = REPO_ROOT / "workflows" / "index.json"
TBD_INVENTORY_AGENT = REPO_ROOT / "agents" / "linter-inventory-agent.md"

REQUIRED_DISPATCH_CONTRACT_KEYS = {
    "orchestrator",
    "inputs",
    "expectations",
    "outputs",
    "non_goals",
}
REQUIRED_HEADINGS = [
    "# Linter Bootstrap Workflow",
    "## Purpose",
    "## When To Use",
    "## Required Inputs",
    "## Outputs",
    "## Procedure",
    "### Stage 1 - Identify",
    "### Stage 2 - Research",
    "### Stage 3 - Setup-PR Proposal",
    "## Stop Conditions",
    "## Anti-Scope",
    "## Adjacent References",
]


def _workflow_text():
    assert WORKFLOW_MD.exists(), f"missing workflow file: {WORKFLOW_MD}"
    return WORKFLOW_MD.read_text(encoding="utf-8")


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

    raw_frontmatter = "\n".join(lines[1:closing_index])
    parsed = yaml.safe_load(raw_frontmatter)
    assert isinstance(parsed, dict), "workflow frontmatter must parse as a mapping"
    return parsed, "\n".join(lines[closing_index + 1 :])


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


def _markdown_link_targets(text):
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        yield match.group(1)


def _has_link_target_ending_with(text, expected_suffix):
    return any(
        target.rstrip("/").endswith(expected_suffix)
        for target in _markdown_link_targets(text)
    )


def _workflow_ids_from_index(index):
    if isinstance(index, dict):
        workflows = index.get("workflows")
    else:
        workflows = None

    if isinstance(workflows, dict):
        for entry in workflows.values():
            workflow = entry.get("workflow", {})
            if isinstance(workflow, dict):
                yield workflow.get("id")
        return

    if isinstance(workflows, list):
        entries = workflows
    elif isinstance(index, list):
        entries = index
    else:
        entries = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        workflow = entry.get("workflow", {})
        if isinstance(workflow, dict):
            yield workflow.get("id")
        elif isinstance(entry.get("id"), str):
            yield entry["id"]


# Proposal Test-Intent risk: requested workflow file is omitted or empty.
# Selected level: component; source: contract Schema 5 item 1 and proposal
# Test-Intent Track "Workflow file existence and title".
def test_workflow_file_exists_and_is_non_empty():
    assert WORKFLOW_MD.exists(), f"missing workflow file: {WORKFLOW_MD}"
    assert WORKFLOW_MD.stat().st_size > 0, "workflow file must be non-empty"


# Proposal Test-Intent risk: new workflow file has malformed frontmatter or an
# invalid dispatch contract. Selected level: component; source: contract Schema
# 5 item 2 and assumption-register entries A4/A5.
def test_workflow_frontmatter_has_dispatch_contract_shape():
    parsed, _body = _frontmatter_and_body(_workflow_text())

    assert parsed.get("workflow", {}).get("id") == "linter-bootstrap"
    contract = parsed.get("workflow_dispatch_contract")
    assert isinstance(contract, dict), "missing workflow_dispatch_contract mapping"
    assert set(contract) == REQUIRED_DISPATCH_CONTRACT_KEYS
    assert isinstance(contract["orchestrator"], str)
    assert contract["orchestrator"].strip()

    for key in ("inputs", "expectations", "outputs", "non_goals"):
        value = contract[key]
        assert isinstance(value, list), f"{key} must be a list"
        assert len(value) >= 2, f"{key} must contain at least two entries"
        assert all(isinstance(item, str) and item.strip() for item in value), (
            f"{key} must contain only non-empty strings"
        )


# Proposal Test-Intent risk: document omits load-bearing procedure sections.
# Selected level: component; source: contract Schema 5 item 3.
def test_workflow_required_headings_appear_in_order():
    _parsed, body = _frontmatter_and_body(_workflow_text())
    headings = [
        line.strip()
        for line in body.splitlines()
        if re.match(r"^#{1,6}\s+", line.strip())
    ]

    position = -1
    for required_heading in REQUIRED_HEADINGS:
        try:
            next_position = headings.index(required_heading, position + 1)
        except ValueError:
            pytest.fail(f"missing or misordered heading: {required_heading}")
        position = next_position


# Proposal Test-Intent risk: workflow restates or drifts from A1 instead of
# linking to source policy. Selected level: component; source: contract Schema
# 5 item 4 and assumption-register entries A1/A2.
def test_workflow_body_contains_a1_cross_link():
    _parsed, body = _frontmatter_and_body(_workflow_text())

    assert "~/ai/conventions/code-quality.md" in body


# Proposal Test-Intent risk: workflow overclaims by creating or defining the
# TBD linter-inventory-agent operator. Selected level: component; source:
# contract Schema 5 item 5 and assumption-register entry A3.
def test_tbd_linter_inventory_operator_is_only_referenced_not_defined():
    _parsed, body = _frontmatter_and_body(_workflow_text())

    assert "linter-inventory-agent" in body
    assert not TBD_INVENTORY_AGENT.exists(), (
        "NES-138 must not create agents/linter-inventory-agent.md"
    )


# Proposal Test-Intent risk: workflow omits stable artifact outputs needed by
# downstream setup-PR handoff. Selected level: component; source: contract
# Schema 5 item 6.
def test_workflow_body_contains_output_path_anchors():
    _parsed, body = _frontmatter_and_body(_workflow_text())

    for anchor in (
        "linter-bootstrap-inventory.md",
        "linter-bootstrap-research.md",
        "linter-bootstrap-setup-pr.md",
    ):
        assert anchor in body


# Proposal Test-Intent risk: workflow omits machine-readable stop vocabulary.
# Selected level: component; source: contract Schema 5 item 7.
def test_workflow_body_contains_stop_condition_vocabulary():
    _parsed, body = _frontmatter_and_body(_workflow_text())

    for vocabulary in ("BLOCKED", "NEEDS_INPUT", "SUCCESS_SETUP_PR_PROPOSED"):
        assert vocabulary in body


# Proposal Test-Intent risk: shared routing discovers the workflow as an
# operator or omits it from workflow topology. Selected level: component;
# source: contract Schema 5 item 8 and assumption-register entry A3.
def test_agents_indexes_linter_bootstrap_as_workflow_not_operator():
    agents_text = AGENTS_MD.read_text(encoding="utf-8")
    topology_section = _section_after_heading(agents_text, "## Workflow Topologies")
    operator_section = _section_after_heading(
        agents_text,
        "## Operator Routing Table",
    )

    assert _has_link_target_ending_with(
        topology_section,
        "workflows/linter-bootstrap.md",
    )
    assert "linter-bootstrap" not in operator_section


# Proposal Test-Intent risk: human workflow index omits the new workflow.
# Selected level: component; source: contract Schema 5 item 9 and
# assumption-register entry A6.
def test_readme_indexes_linter_bootstrap_workflow():
    workflows_section = _section_after_heading(
        README_MD.read_text(encoding="utf-8"),
        "### Workflows",
    )

    assert _has_link_target_ending_with(
        workflows_section,
        "workflows/linter-bootstrap.md",
    )


# Proposal Test-Intent risk: generated workflow metadata index is stale.
# Selected level: component; source: contract Schema 5 item 10 and
# assumption-register entries A4/A5.
def test_workflow_index_contains_linter_bootstrap_key():
    index = json.loads(WORKFLOW_INDEX_JSON.read_text(encoding="utf-8"))

    assert "linter-bootstrap" in set(_workflow_ids_from_index(index))
