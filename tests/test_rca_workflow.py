"""Shape guards for NES-278 RCA workflow surfaces.

Contract:
/home/nes/projects/ai/planning/nes-278-rca-workflow/contracts/nes-278-rca-workflow.md

Run with PYTHONPATH=. when invoking pytest directly so the workflow index
generator import resolves from a clean checkout.
"""

import json
import re
from pathlib import Path

import pytest

from tools.workflow_index.generator import (
    DISPATCH_CONTRACT_KEYS,
    parse_frontmatter,
    validate_dispatch_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MD = REPO_ROOT / "workflows" / "rca.md"
INDEX_JSON = REPO_ROOT / "workflows" / "index.json"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
README_MD = REPO_ROOT / "README.md"

EXPECTED_H2_HEADINGS = [
    "## Purpose",
    "## Workflow Dispatch Surface",
    "## Use When",
    "## Do Not Use When",
    "## Required Inputs",
    "## Output Paths",
    "## Phase Map",
    "## Phase 1 - Incident Framing",
    "## Phase 2 - Evidence Pack Assembly",
    "## Phase 3 - File Incident Tracker",
    "## Phase 4 - Dispatch Incident Investigator",
    "## Phase 5 - Dispatch Post-Mortem Author",
    "## Phase 6 - File Action-Item Tickets",
    "## Phase 7 - Author Runbooks For Unverifiable Factors",
    "## Phase 8 - Comment Findings And Post-Mortem Links",
    "## Phase 9 - Close Or Stay Open",
    "## Wrap Relationship To Implementation Pipeline",
    "## Resume And Currentness",
    "## Stop Conditions",
    "## Anti-Scope",
    "## Distinction From Post-Mortem-Only Workflow",
    "## Cross-References",
]
PHASE_HEADINGS = [
    heading for heading in EXPECTED_H2_HEADINGS if re.match(r"^## Phase \d+ - ", heading)
]
PHASE_SUBSECTIONS = [
    "### Entry Conditions",
    "### Actions",
    "### Outputs",
    "### Stop Or Transition",
]
REQUIRED_INPUT_NAMES = [
    "incident_handle",
    "incident_brief_path",
    "incident_context",
    "evidence_dir",
    "repo_root",
    "scratch_dir",
    "planning_dir",
    "ticket_system",
    "incident_issue_key",
    "linear_team_key",
    "linear_project_id",
    "jira_url",
    "jira_project",
    "jira_account_email",
    "action_item_policy",
    "action_item_worktrees_root",
    "action_item_planning_root",
    "runbook_output_dir",
    "close_policy",
]
REQUIRED_OUTPUT_PATHS = [
    "${planning_dir}/incident-brief.md",
    "${planning_dir}/evidence/",
    "${planning_dir}/findings.md",
    "${planning_dir}/post-mortem.md",
    "${planning_dir}/action-items.md",
    "${planning_dir}/runbooks/",
    "${planning_dir}/tracker-comments/phase-8.md",
    "${planning_dir}/rca-close.md",
    "${planning_dir}/rca-run-manifest.md",
    "${scratch_dir}/prompts/",
    "${scratch_dir}/logs/",
    "${scratch_dir}/questions/",
]
TICKET_OPERATOR_PATHS = [
    "~/ai/agents/linear-operator.md",
    "~/ai/agents/jira-operator.md",
]
CROSS_REFERENCE_PATHS = [
    "~/ai/agents/incident-investigator.md",
    "~/ai/agents/post-mortem-author.md",
    "~/ai/agents/linear-operator.md",
    "~/ai/agents/jira-operator.md",
    "~/ai/agents/implementation-pipeline-orchestrator.md",
    "~/ai/workflows/implementation-pipeline.md",
    "~/ai/workflows/post-mortem.md",
    "~/ai/conventions/workflow-routing.md",
]
REFERENCED_OPERATOR_FILES = [
    "incident-investigator.md",
    "post-mortem-author.md",
    "linear-operator.md",
    "jira-operator.md",
    "implementation-pipeline-orchestrator.md",
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
            "error": f"missing workflow file: {WORKFLOW_MD}",
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


def _subsection_after_heading(text, heading):
    return _section_after_heading(text, heading)


def _contains_all(text, substrings):
    missing = [item for item in substrings if item not in text]
    assert missing == [], f"missing expected substrings: {missing}"


def _heading_lines(body, level):
    prefix = "#" * level
    pattern = re.compile(rf"^{re.escape(prefix)}\s+")
    return [line.strip() for line in body.splitlines() if pattern.match(line.strip())]


def _markdown_link_targets(text):
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        yield match.group(1)


def _has_link_target_ending_with(text, expected_suffix):
    return any(
        target.rstrip("/").endswith(expected_suffix)
        for target in _markdown_link_targets(text)
    )


def test_workflow_md_exists_and_nonempty():
    assert WORKFLOW_MD.exists(), f"missing workflow file: {WORKFLOW_MD}"
    assert WORKFLOW_MD.stat().st_size > 0, "workflow file must be non-empty"


def test_workflow_id_matches_filename_stem(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    assert parsed.get("workflow", {}).get("id") == "rca"
    assert parsed.get("workflow", {}).get("id") == WORKFLOW_MD.stem


def test_workflow_dispatch_contract_keys(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    contract = parsed.get("workflow_dispatch_contract")

    assert isinstance(contract, dict), "missing workflow_dispatch_contract mapping"
    assert set(contract) == DISPATCH_CONTRACT_KEYS, (
        "workflow_dispatch_contract must have exactly "
        f"{sorted(DISPATCH_CONTRACT_KEYS)}"
    )
    validate_dispatch_contract(contract, str(WORKFLOW_MD))


def test_workflow_aliases_absent(workflow_document):
    parsed = _require_workflow_document(workflow_document)["frontmatter"]
    assert "workflow_aliases" not in parsed


def test_top_level_title_is_rca_workflow(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    assert _heading_lines(body, 1)[:1] == ["# RCA Workflow"]


def test_required_h2_order(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    headings = re.findall(r"^## .+", body, re.MULTILINE)
    assert headings == EXPECTED_H2_HEADINGS


def test_each_phase_has_required_subsections(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]

    for heading in PHASE_HEADINGS:
        phase = _section_after_heading(body, heading)
        subsections = re.findall(r"^### .+", phase, re.MULTILINE)
        assert subsections[:4] == PHASE_SUBSECTIONS, (
            f"{heading} must start with the required phase subsections"
        )


def test_phase_4_cites_incident_investigator(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    phase = _section_after_heading(body, "## Phase 4 - Dispatch Incident Investigator")
    actions = _subsection_after_heading(phase, "### Actions")

    _contains_all(
        actions,
        (
            "~/ai/agents/incident-investigator.md",
            "incident_brief_path",
            "evidence_dir",
            "repo_root",
            "findings_path",
        ),
    )


def test_phase_5_cites_post_mortem_author(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    phase = _section_after_heading(body, "## Phase 5 - Dispatch Post-Mortem Author")
    actions = _subsection_after_heading(phase, "### Actions")

    _contains_all(
        actions,
        (
            "~/ai/agents/post-mortem-author.md",
            "findings_path",
            "incident_brief_path",
            "output_path",
        ),
    )


def test_phase_3_cites_ticket_operators(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    phase = _section_after_heading(body, "## Phase 3 - File Incident Tracker")
    actions = _subsection_after_heading(phase, "### Actions")

    _contains_all(actions, TICKET_OPERATOR_PATHS)


def test_phase_6_cites_ticket_operators_and_orchestrator(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    phase = _section_after_heading(body, "## Phase 6 - File Action-Item Tickets")
    actions = _subsection_after_heading(phase, "### Actions")

    _contains_all(
        actions,
        (
            "~/ai/agents/linear-operator.md",
            "~/ai/agents/jira-operator.md",
            "~/ai/agents/implementation-pipeline-orchestrator.md",
        ),
    )


def test_phase_8_cites_ticket_operators(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    phase = _section_after_heading(
        body,
        "## Phase 8 - Comment Findings And Post-Mortem Links",
    )
    actions = _subsection_after_heading(phase, "### Actions")

    _contains_all(actions, TICKET_OPERATOR_PATHS)


def test_wrap_section_contains_wrap_statement(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    wrap = _section_after_heading(body, "## Wrap Relationship To Implementation Pipeline")

    assert "RCA wraps the implementation workflow at Phase 6" in wrap


def test_wrap_section_contains_handoff_inputs_linear(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    wrap = _section_after_heading(body, "## Wrap Relationship To Implementation Pipeline")

    assert "linear_issue_key=" in wrap


def test_wrap_section_contains_handoff_inputs_jira(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    wrap = _section_after_heading(body, "## Wrap Relationship To Implementation Pipeline")

    assert "jira_issue_key=" in wrap


def test_wrap_section_contains_review_boundary(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    wrap = _section_after_heading(body, "## Wrap Relationship To Implementation Pipeline")

    assert "Implementation review and PR review remain distinct concern surfaces" in wrap


def test_required_input_names_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    required_inputs = _section_after_heading(body, "## Required Inputs")

    _contains_all(required_inputs, REQUIRED_INPUT_NAMES)


def test_output_paths_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    output_paths = _section_after_heading(body, "## Output Paths")

    _contains_all(output_paths, REQUIRED_OUTPUT_PATHS)


def test_stop_conditions_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    stop_conditions = _section_after_heading(body, "## Stop Conditions")

    assert "incident closes" in stop_conditions or "Success / incident closes" in stop_conditions
    assert (
        "incident stays open" in stop_conditions
        or "stays open" in stop_conditions
        or "pending" in stop_conditions
    )
    assert "Abort at Phase 1" in stop_conditions or "no incident to investigate" in stop_conditions
    assert (
        "Already-produced-findings" in stop_conditions
        or "later-phase entry" in stop_conditions
    )
    assert "BLOCKED:" in stop_conditions
    assert "NEEDS_INPUT:" in stop_conditions
    assert (
        "implementation handoff pending" in stop_conditions
        or "action-item WUs" in stop_conditions
    )


def test_cross_references_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    cross_references = _section_after_heading(body, "## Cross-References")

    _contains_all(cross_references, CROSS_REFERENCE_PATHS)
    assert "NES-283" in cross_references or "queued" in cross_references


def test_anti_scope_explicit(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    anti_scope = _section_after_heading(body, "## Anti-Scope")
    anti_scope_lower = anti_scope.casefold()

    assert (
        "does not modify" in anti_scope_lower
        or "does not edit" in anti_scope_lower
    )
    _contains_all(
        anti_scope,
        (
            "incident-investigator",
            "post-mortem-author",
            "ticket operators",
            "implementation-pipeline-orchestrator",
        ),
    )
    assert "does not redesign" in anti_scope_lower
    assert "incident-tracker filing protocol" in anti_scope
    assert "existing operator" in anti_scope_lower
    assert "does not replace" in anti_scope_lower
    _contains_all(anti_scope, ("Phase 4", "Phase 7", "Phase 8", "CodeRabbit", "PR-review"))
    assert "workflow specifies HOW runbooks are produced" in anti_scope
    assert "does not author runbook documents" in anti_scope


def test_distinction_section_present(workflow_document):
    body = _require_workflow_document(workflow_document)["body"]
    distinction = _section_after_heading(
        body,
        "## Distinction From Post-Mortem-Only Workflow",
    )

    assert "workflows/post-mortem.md" in distinction
    assert "NES-283" in distinction


def test_referenced_operator_files_exist():
    for filename in REFERENCED_OPERATOR_FILES:
        path = REPO_ROOT / "agents" / filename
        assert path.is_file(), f"referenced operator file missing: {path}"


def test_agents_md_workflow_topologies_lists_rca():
    agents_text = _read_required_file(AGENTS_MD)
    topology_section = _section_after_heading(agents_text, "## Workflow Topologies")

    assert (
        "`~/ai/workflows/rca.md`](workflows/rca.md)" in topology_section
        or _has_link_target_ending_with(topology_section, "workflows/rca.md")
    ), "AGENTS.md Workflow Topologies must link to workflows/rca.md"


def test_readme_lists_rca_workflow():
    readme_text = _read_required_file(README_MD)
    workflows_section = _section_after_heading(readme_text, "### Workflows")

    assert (
        "`workflows/rca.md`](workflows/rca.md)" in workflows_section
        or _has_link_target_ending_with(workflows_section, "workflows/rca.md")
    ), "README.md Workflows section must link to workflows/rca.md"


def test_index_json_includes_rca():
    index = json.loads(_read_required_file(INDEX_JSON))
    workflows = index.get("workflows")
    assert isinstance(workflows, dict), "workflow index must contain workflows mapping"

    entry = workflows.get("rca")
    path_matches = [
        item
        for item in workflows.values()
        if isinstance(item, dict) and item.get("path", "").endswith("workflows/rca.md")
    ]
    assert isinstance(entry, dict) or path_matches, "workflow index missing rca entry"

    if isinstance(entry, dict):
        assert entry.get("workflow", {}).get("id") == "rca"
        assert entry.get("path") == "workflows/rca.md"
