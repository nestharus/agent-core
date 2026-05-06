"""Shape guards for NES-207 code-quality workflow surfaces.

Contract:
/home/nes/projects/ai/planning/nes-207-code-quality-workflow/contracts/nes-207-code-quality-workflow.md
"""

import json
import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MD = REPO_ROOT / "workflows" / "code-quality.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
README_MD = REPO_ROOT / "README.md"
CONVENTION_MD = REPO_ROOT / "conventions" / "code-quality.md"
WORKFLOW_INDEX_JSON = REPO_ROOT / "workflows" / "index.json"

REQUIRED_DISPATCH_CONTRACT_KEYS = {
    "orchestrator",
    "inputs",
    "expectations",
    "outputs",
    "non_goals",
}
REQUIRED_HEADINGS = [
    "# Code-Quality Workflow",
    "## Purpose",
    "## Use When",
    "## Do Not Use When",
    "## Required Inputs",
    "## Output Paths",
    "## Dispatch Manifest",
    "## Per-Concern Auditor Routing",
    "## Aggregate Verdict",
    "## Finding Normalization",
    "## Audit-History Ownership",
    "## Rerun And Currentness Semantics",
    "## Process-Tree Relationship",
    "## Standalone Mode",
    "## Pipeline-Callable Mode",
    "## Stop Conditions And Escalation",
    "## Anti-Scope",
]
REQUIRED_AUDITOR_ROUTES = [
    (
        "A4",
        "Push-vs-pull system coupling",
        "~/ai/agents/push-pull-auditor.md",
        REPO_ROOT / "agents" / "push-pull-auditor.md",
    ),
    (
        "A5",
        "Function classification",
        "~/ai/agents/function-classification-auditor.md",
        REPO_ROOT / "agents" / "function-classification-auditor.md",
    ),
    (
        "A6",
        "Cohesion",
        "~/ai/agents/cohesion-auditor.md",
        REPO_ROOT / "agents" / "cohesion-auditor.md",
    ),
    (
        "A6",
        "Coupling",
        "~/ai/agents/coupling-auditor.md",
        REPO_ROOT / "agents" / "coupling-auditor.md",
    ),
]
RETIRED_AUDITOR_PATH = "~/ai/agents/cohesion-coupling-auditor.md"
CONVENTION_RULE_SENTINELS = [
    "Push-vs-pull system coupling",
    "Function classification",
    "Cohesion by classifications touched",
    "Coupling by distinct external symbols/modules referenced",
]
REQUIRED_INPUT_FIELDS = [
    "repo_root",
    "diff_path",
    "touched_surfaces_path",
    "scratch_dir",
    "planning_dir",
    "proposal_path",
    "problem_map_path",
    "risk_profile_path",
    "wu_id",
    "base_ref",
    "head_ref",
    "changed_files_path",
    "changed_functions_path",
    "code_trace_paths",
    "code_quality_ref",
]
REQUIRED_OUTPUT_PATHS = [
    "${scratch_dir}/code-quality/${slug}/prompts",
    "${scratch_dir}/code-quality/${slug}/logs",
    "${planning_dir}/code-quality/${slug}/reports",
    "${planning_dir}/code-quality/${slug}/findings.json",
    "${planning_dir}/code-quality/${slug}/findings.md",
    "${planning_dir}/code-quality/${slug}/dispatch-manifest.md",
    "${planning_dir}/code-quality/${slug}/aggregate-code-quality.md",
    "process-tree-expected.md",
    "${code_quality_work_dir}/",
]
REQUIRED_MANIFEST_HEADERS = [
    "Concern",
    "Auditor",
    "Model",
    "Prompt path",
    "Log path",
    "Report path",
    "Required",
]
NORMALIZED_FINDING_FIELDS = [
    "id",
    "source_auditor",
    "source_id",
    "severity",
    "metric",
    "failure_mode",
    "path",
    "function",
    "component",
    "source_component",
    "target_component",
    "line_span_or_diff_hunk",
    "evidence",
    "closure_expectation",
    "report_path",
    "blocks_pipeline",
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

    raw_frontmatter = "\n".join(lines[1:closing_index])
    parsed = yaml.safe_load(raw_frontmatter)
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


def _contains_all_casefold(text, substrings):
    lowered = text.casefold()
    missing = [item for item in substrings if item.casefold() not in lowered]
    assert missing == [], f"missing expected substrings: {missing}"


def _assert_ordered_substrings(text, substrings):
    position = -1
    for substring in substrings:
        next_position = text.find(substring, position + 1)
        assert next_position != -1, f"missing or misordered substring: {substring}"
        position = next_position


def _markdown_link_targets(text):
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        yield match.group(1)


def _has_link_target_ending_with(text, expected_suffix):
    return any(
        target.rstrip("/").endswith(expected_suffix)
        for target in _markdown_link_targets(text)
    )


def _paragraphs_with_definition_language(text, sentinel):
    definition_terms = re.compile(
        r"\b(must|cannot|violates?|failure mode|threshold|rule is|the rule|"
        r"defines?|max|prefer)\b",
        re.IGNORECASE,
    )
    return [
        paragraph
        for paragraph in re.split(r"\n\s*\n", text)
        if sentinel in paragraph and definition_terms.search(paragraph)
    ]


def test_cq_t_01_workflow_file_exists_and_is_non_empty():
    """CQ-T-01: workflows/code-quality.md exists and is non-empty."""
    assert WORKFLOW_MD.is_file(), f"missing workflow file: {WORKFLOW_MD}"
    assert WORKFLOW_MD.stat().st_size > 0, "workflow file must be non-empty"


def test_cq_t_02_frontmatter_parses_and_id_matches_stem(workflow_document):
    """CQ-T-02: YAML frontmatter parses and workflow.id is code-quality."""
    parsed = _require_workflow_document(workflow_document)["frontmatter"]

    assert parsed.get("workflow", {}).get("id") == "code-quality"
    assert parsed.get("workflow", {}).get("id") == WORKFLOW_MD.stem


def test_cq_t_03_dispatch_contract_uses_fixed_shape(workflow_document):
    """CQ-T-03: workflow_dispatch_contract has the fixed contract key set."""
    document = _require_workflow_document(workflow_document)
    contract = document["frontmatter"].get("workflow_dispatch_contract")

    assert isinstance(contract, dict), "missing workflow_dispatch_contract mapping"
    assert set(contract) == REQUIRED_DISPATCH_CONTRACT_KEYS, (
        "workflow_dispatch_contract must have exactly "
        f"{sorted(REQUIRED_DISPATCH_CONTRACT_KEYS)}"
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


def test_cq_t_04_frontmatter_omits_aliases(workflow_document):
    """CQ-T-04: workflow_aliases block is absent."""
    document = _require_workflow_document(workflow_document)
    assert "workflow_aliases" not in document["frontmatter"], (
        "omit workflow_aliases until concrete alias evidence exists"
    )


def test_cq_t_05_required_body_headings_appear_in_order(workflow_document):
    """CQ-T-05: required body headings appear in contract order."""
    document = _require_workflow_document(workflow_document)
    headings = [
        line.strip()
        for line in document["body"].splitlines()
        if re.match(r"^#{1,6}\s+", line.strip())
    ]

    position = -1
    for required_heading in REQUIRED_HEADINGS:
        try:
            next_position = headings.index(required_heading, position + 1)
        except ValueError:
            pytest.fail(f"missing or misordered heading: {required_heading}")
        position = next_position


def test_cq_t_06_workflow_names_four_child_auditors(workflow_document):
    """CQ-T-06: four child auditors are named with labels and operator paths."""
    document = _require_workflow_document(workflow_document)
    routing = _section_after_heading(
        document["body"],
        "## Per-Concern Auditor Routing",
    )

    for concern, label, operator_path, _disk_path in REQUIRED_AUDITOR_ROUTES:
        _contains_all(routing, (concern, label, operator_path))
        assert "gpt-high" in routing, "routing must name gpt-high for child auditors"


def test_cq_t_07_retired_cohesion_coupling_path_absent(workflow_document):
    """CQ-T-07: retired cohesion-coupling-auditor path is absent."""
    document = _require_workflow_document(workflow_document)
    assert RETIRED_AUDITOR_PATH not in document["text"], (
        f"workflow must not cite retired path {RETIRED_AUDITOR_PATH}"
    )


def test_cq_t_08_convention_is_rule_source_without_inlined_rules(workflow_document):
    """CQ-T-08: convention is referenced; rule descriptions are not inlined."""
    body = _require_workflow_document(workflow_document)["body"]
    convention_text = _read_required_file(CONVENTION_MD)

    assert "~/ai/conventions/code-quality.md" in body, (
        "workflow must reference the code-quality convention as rule source"
    )
    _contains_all(convention_text, CONVENTION_RULE_SENTINELS)

    for sentinel in CONVENTION_RULE_SENTINELS:
        defining_paragraphs = _paragraphs_with_definition_language(body, sentinel)
        assert defining_paragraphs == [], (
            f"{sentinel!r} appears in definition-like workflow text: "
            f"{defining_paragraphs}"
        )


def test_cq_t_09_required_inputs_enumerate_invocation_fields(workflow_document):
    """CQ-T-09: Required Inputs covers Phase-4, PR-review, and ad-hoc fields."""
    document = _require_workflow_document(workflow_document)
    required_inputs = _section_after_heading(
        document["body"],
        "## Required Inputs",
    )

    _contains_all(required_inputs, REQUIRED_INPUT_FIELDS)
    _contains_all_casefold(required_inputs, ("Phase 4", "PR-review", "ad-hoc"))


def test_cq_t_10_output_paths_document_pipeline_and_standalone_roots(
    workflow_document,
):
    """CQ-T-10: Output Paths documents scratch, planning, and standalone paths."""
    document = _require_workflow_document(workflow_document)
    output_paths = _section_after_heading(document["body"], "## Output Paths")

    _contains_all(output_paths, REQUIRED_OUTPUT_PATHS)


def test_cq_t_11_dispatch_manifest_table_has_required_headers(workflow_document):
    """CQ-T-11: Dispatch Manifest table has the seven required headers."""
    document = _require_workflow_document(workflow_document)
    manifest = _section_after_heading(document["body"], "## Dispatch Manifest")

    _assert_ordered_substrings(manifest, REQUIRED_MANIFEST_HEADERS)


def test_cq_t_12_aggregate_verdict_documents_outcomes_and_rollup(
    workflow_document,
):
    """CQ-T-12: Aggregate Verdict documents outcomes and worst-case rules."""
    document = _require_workflow_document(workflow_document)
    aggregate = _section_after_heading(document["body"], "## Aggregate Verdict")

    _contains_all(
        aggregate,
        ("NEEDS_INPUT:<absolute_artifact_path>", "BLOCKED:<reason>", "HIGH", "MEDIUM", "LOW"),
    )
    assert re.search(r"any required child returns `?HIGH`?", aggregate, re.I), (
        "HIGH must be produced when any required child returns HIGH"
    )
    assert re.search(r"coupling returns `?MEDIUM`?", aggregate, re.I), (
        "MEDIUM must be tied to coupling returning MEDIUM"
    )
    assert re.search(r"every required child returns `?LOW`?", aggregate, re.I), (
        "LOW must require every required child to return LOW"
    )
    assert re.search(r"coupling.*only child.*MEDIUM|only child.*MEDIUM.*coupling", aggregate, re.I | re.S), (
        "Aggregate Verdict must state coupling is the only child with native MEDIUM"
    )
    assert re.search(r"PASS\s*\|\s*FAIL\s*\|\s*NEEDS_INPUT\s*\|\s*BLOCKED", aggregate), (
        "process-tree fanout review vocabulary must stay separate"
    )


def test_cq_t_13_finding_normalization_lists_formats_and_fields(
    workflow_document,
):
    """CQ-T-13: Finding Normalization lists both formats and required fields."""
    document = _require_workflow_document(workflow_document)
    findings = _section_after_heading(
        document["body"],
        "## Finding Normalization",
    )

    _contains_all(findings, ("findings.json", "findings.md"))
    _contains_all(findings, NORMALIZED_FINDING_FIELDS)
    assert re.search(r"severity.*stop-state|stop-state.*severity", findings, re.I | re.S), (
        "normalized records must allow severity or stop-state"
    )


def test_cq_t_14_anti_scope_lists_required_exclusions(workflow_document):
    """CQ-T-14: Anti-Scope lists the six contract exclusions."""
    document = _require_workflow_document(workflow_document)
    anti_scope = _section_after_heading(document["body"], "## Anti-Scope")

    exclusion_patterns = [
        r"does\s+not\s+implement.*auditor|auditor.*does\s+not\s+implement",
        r"does\s+not\s+redefine\s+A1|duplicate.*convention.*rule descriptions",
        r"does\s+not\s+edit.*child auditor",
        r"nesting.*inline.*duplicate|duplicate.*inline.*nesting",
        r"does\s+not\s+wire.*implementation-pipeline.*Phase 4",
        r"does\s+not\s+replace.*audit\.md.*PR-review.*process-tree-auditor",
    ]
    for pattern in exclusion_patterns:
        assert re.search(pattern, anti_scope, re.I | re.S), (
            f"Anti-Scope missing required exclusion pattern: {pattern}"
        )


def test_cq_t_15_agents_indexes_code_quality_as_workflow_topology():
    """CQ-T-15: AGENTS Workflow Topologies references code-quality workflow."""
    agents_text = _read_required_file(AGENTS_MD)
    topology_section = _section_after_heading(agents_text, "## Workflow Topologies")

    assert _has_link_target_ending_with(topology_section, "workflows/code-quality.md"), (
        "AGENTS.md Workflow Topologies must link to workflows/code-quality.md"
    )


def test_cq_t_16_agents_operator_table_omits_code_quality_handle():
    """CQ-T-16: AGENTS operator-routing table has no code-quality handle row."""
    agents_text = _read_required_file(AGENTS_MD)
    operator_section = _section_after_heading(agents_text, "## Operator Routing Table")

    assert not re.search(r"(?m)^\|\s*`?code-quality`?\s*\|", operator_section), (
        "code-quality belongs to Workflow Topologies, not the operator table"
    )
    assert not re.search(r"(?m)^-\s+`?code-quality`?\s+-", operator_section), (
        "code-quality must not be listed as an operator handle"
    )


def test_cq_t_17_readme_indexes_code_quality_workflow():
    """CQ-T-17: README workflow-library section references code-quality workflow."""
    readme_text = _read_required_file(README_MD)
    workflows_section = _section_after_heading(readme_text, "### Workflows")

    assert _has_link_target_ending_with(workflows_section, "workflows/code-quality.md"), (
        "README.md Workflows section must link to workflows/code-quality.md"
    )


def test_cq_t_18_convention_cross_references_code_quality_workflow():
    """CQ-T-18: convention Cross-references points at code-quality workflow."""
    convention_text = _read_required_file(CONVENTION_MD)
    cross_references = _section_after_heading(convention_text, "## Cross-references")

    assert (
        "~/ai/workflows/code-quality.md" in cross_references
        or _has_link_target_ending_with(cross_references, "workflows/code-quality.md")
    ), "code-quality convention must cross-reference workflows/code-quality.md"


def test_cq_t_19_workflow_index_contains_matching_code_quality_entry():
    """CQ-T-19: workflows/index.json contains matching code-quality metadata."""
    from tools.workflow_index.generator import parse_frontmatter

    workflow_text = _read_required_file(WORKFLOW_MD)
    parsed = parse_frontmatter(workflow_text, str(WORKFLOW_MD))
    index = json.loads(_read_required_file(WORKFLOW_INDEX_JSON))

    workflows = index.get("workflows")
    assert isinstance(workflows, dict), "workflow index must contain workflows mapping"
    entry = workflows.get("code-quality")
    assert isinstance(entry, dict), "workflow index missing code-quality entry"
    assert entry.get("workflow", {}).get("id") == "code-quality"
    assert entry.get("path") == "workflows/code-quality.md"
    assert entry.get("workflow_dispatch_contract") == parsed.get(
        "workflow_dispatch_contract"
    ), "index dispatch contract must match workflow frontmatter"


@pytest.mark.parametrize(
    ("operator_label", "operator_path"),
    [(label, disk_path) for _concern, label, _route_path, disk_path in REQUIRED_AUDITOR_ROUTES],
)
def test_cq_t_20_operator_paths_exist_on_disk(operator_label, operator_path):
    """CQ-T-20: the four referenced child operator files exist on disk."""
    assert operator_path.is_file(), f"{operator_label} operator path missing: {operator_path}"
