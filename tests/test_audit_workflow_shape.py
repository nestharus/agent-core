"""Shape guards for NES-223 audit workflow.

Contract:
/home/nes/projects/ai/planning/nes-223-audit-sub-workflow/contracts/nes-223-audit-sub-workflow.md
"""

import re
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_MD = REPO_ROOT / "workflows" / "audit.md"

REQUIRED_DISPATCH_CONTRACT_KEYS = {
    "orchestrator",
    "inputs",
    "expectations",
    "outputs",
    "non_goals",
}
REQUIRED_HEADINGS = [
    "# Audit Workflow",
    "## Purpose",
    "## Target Typing",
    "## Required Inputs",
    "## Output Paths",
    "## Dispatch Manifest",
    "## Per-Target Auditor Routing",
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


def _workflow_text():
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


def _body():
    _parsed, body = _frontmatter_and_body(_workflow_text())
    return body


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


def _assert_section_mentions(section, substrings):
    _contains_all(section, substrings)


# Proposal Test-Intent risk: frontmatter or dispatch contract breaks index
# generation. Selected level: component shape-guard; source: Step 6a contract
# Step 6b Test Surface point 1.
def test_audit_workflow_frontmatter_id_and_dispatch_contract():
    parsed, _body = _frontmatter_and_body(_workflow_text())

    assert parsed.get("workflow", {}).get("id") == "audit"
    contract = parsed.get("workflow_dispatch_contract")
    assert isinstance(contract, dict), "missing workflow_dispatch_contract mapping"
    assert set(contract) == REQUIRED_DISPATCH_CONTRACT_KEYS
    assert isinstance(contract["orchestrator"], str)
    assert contract["orchestrator"].strip()

    for key in ("inputs", "expectations", "outputs", "non_goals"):
        value = contract[key]
        assert isinstance(value, list), f"{key} must be a list"
        assert value, f"{key} must be non-empty"
        assert all(isinstance(item, str) and item.strip() for item in value), (
            f"{key} must contain only non-empty strings"
        )


# Proposal Test-Intent risk: workflow omits load-bearing procedure sections.
# Selected level: component shape-guard; source: Step 6a contract body sections.
def test_audit_workflow_required_body_sections_present():
    body = _body()
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


# Proposal Test-Intent risk: target typing coverage regresses. Selected level:
# component shape-guard; source: Step 6a Target Typing clause.
def test_audit_workflow_target_typing_table_lists_five_types():
    target_typing = _section_after_heading(_body(), "## Target Typing")

    for target_type in ("workflow", "operator", "runtime", "rebase-drift", "mixed"):
        assert re.search(rf"(?m)^\|\s*`?{re.escape(target_type)}`?\s*\|", target_typing), (
            f"Target Typing table must contain row for {target_type}"
        )


# Proposal Test-Intent risk: per-target routing drifts from existing auditors.
# Selected level: component shape-guard; source: Step 6a Target Typing and
# Aggregate Verdict clauses.
def test_audit_workflow_target_typing_routes_to_named_auditors():
    body = _body()
    target_typing = _section_after_heading(body, "## Target Typing")

    _assert_section_mentions(
        target_typing,
        (
            "workflow-design-auditor",
            "agent-design-auditor",
            "workflow-process-auditor",
            "rebase-drift-checker",
        ),
    )
    assert "process-tree-auditor" in body


# Proposal Test-Intent risk: callers cannot provide a complete audit target.
# Selected level: component shape-guard; source: Step 6a Required Inputs clause.
def test_audit_workflow_required_inputs_complete():
    required_inputs = _section_after_heading(_body(), "## Required Inputs")

    _assert_section_mentions(
        required_inputs,
        (
            "target_type",
            "target_ref",
            "repo_root",
            "worktree_path",
            "scratch_dir",
            "planning_dir",
            "audit_work_dir",
            "design_patterns_ref",
            "operator_format_ref",
            "audit_history_path",
            "mode",
        ),
    )
    assert "target_paths" in required_inputs or "target_manifest" in required_inputs
    assert "~/ai/conventions/design-patterns.md" in required_inputs
    assert "~/ai/agents/operator-file-format.md" in required_inputs
    assert "default" in required_inputs.casefold()


# Proposal Test-Intent risk: pipeline and standalone artifacts are conflated.
# Selected level: component shape-guard; source: Step 6a Output Paths clause.
def test_audit_workflow_output_paths_split_scratch_planning():
    output_paths = _section_after_heading(_body(), "## Output Paths")

    _assert_section_mentions(
        output_paths,
        (
            "${scratch_dir}/audit/${audit_slug}/",
            "${planning_dir}/audit/${audit_slug}/",
            "${audit_work_dir}/",
        ),
    )
    _contains_all_casefold(output_paths, ("prompts", "logs", "durable", "standalone"))


# Proposal Test-Intent risk: durable handoff files are omitted. Selected level:
# component shape-guard; source: Step 6a Output Paths clause.
def test_audit_workflow_output_paths_list_durable_filenames():
    output_paths = _section_after_heading(_body(), "## Output Paths")

    _assert_section_mentions(
        output_paths,
        (
            "dispatch-manifest.md",
            "reports/workflow-design-audit.md",
            "reports/agent-design-audit.md",
            "reports/workflow-process-audit.md",
            "reports/rebase-drift.md",
            "findings.json",
            "findings.md",
            "aggregate-audit.md",
            "process-tree-expected.md",
            "prompts/<auditor>-<target_slug>.prompt.md",
            "logs/<auditor>-<target_slug>.log",
        ),
    )


# Proposal Test-Intent risk: dispatch requiredness becomes ambiguous. Selected
# level: component shape-guard; source: Step 6a Dispatch Manifest clause.
def test_audit_workflow_dispatch_manifest_required_column():
    manifest = _section_after_heading(_body(), "## Dispatch Manifest")

    _assert_ordered_substrings(
        manifest,
        (
            "Target item",
            "Target type",
            "Auditor/checker",
            "Model",
            "Prompt path",
            "Log path",
            "Report path",
            "Required",
        ),
    )
    assert re.search(r"\bdefault(?:s)?\s+(?:to|is)\s+`?true`?", manifest, re.IGNORECASE), (
        "Dispatch Manifest must document Required default true semantics"
    )
    assert "required: false" in manifest
    assert re.search(r"required:\s*false.*reason|reason.*required:\s*false", manifest, re.I | re.S), (
        "required: false must require a written reason"
    )


# Proposal Test-Intent risk: aggregate output vocabulary drifts. Selected level:
# component shape-guard; source: Step 6a Aggregate Verdict clause.
def test_audit_workflow_aggregate_verdict_five_outcomes():
    aggregate = _section_after_heading(_body(), "## Aggregate Verdict")

    _assert_section_mentions(
        aggregate,
        (
            "LOW",
            "MEDIUM",
            "HIGH",
            "NEEDS_INPUT:<absolute_artifact_path>",
            "BLOCKED:<reason>",
        ),
    )


# Proposal Test-Intent risk: rebase-drift checker signal is flattened
# incorrectly. Selected level: component shape-guard; source: Step 6a
# Aggregate Verdict clause.
def test_audit_workflow_aggregate_drift_high_label():
    aggregate = _section_after_heading(_body(), "## Aggregate Verdict")

    _assert_section_mentions(aggregate, ("rebase-drift-checker", "drift detected", "HIGH"))
    assert re.search(r"drift detected.*HIGH|HIGH.*drift detected", aggregate, re.I | re.S)
    assert re.search(
        r"preserv(?:e|es|ing).*drift detected|drift detected.*preserv",
        aggregate,
        re.I | re.S,
    )


# Proposal Test-Intent risk: process review and topology review are merged.
# Selected level: component shape-guard; source: Step 6a Aggregate Verdict and
# Process-Tree Relationship clauses.
def test_audit_workflow_process_tree_separate_track():
    body = _body()
    aggregate = _section_after_heading(body, "## Aggregate Verdict")
    process_tree = _section_after_heading(body, "## Process-Tree Relationship")
    combined = "\n".join((aggregate, process_tree))

    assert re.search(r"PASS\s*\|\s*FAIL\s*\|\s*NEEDS_INPUT\s*\|\s*BLOCKED", combined)
    assert "workflow-process-auditor" in combined
    assert "process-tree-auditor" in combined
    assert re.search(r"does\s+not\s+replace", combined, re.IGNORECASE)
    assert re.search(r"topology\s+authority", combined, re.IGNORECASE)


# Proposal Test-Intent risk: findings format ambiguity breaks downstream
# parsing. Selected level: component shape-guard; source: Step 6a Finding
# Normalization clause.
def test_audit_workflow_findings_both_formats_required():
    findings = _section_after_heading(_body(), "## Finding Normalization")

    _assert_section_mentions(findings, ("findings.json", "findings.md"))
    assert re.search(r"both|required|every dispatch", findings, re.IGNORECASE)
    assert re.search(r"human-readable|human rendering|human-readable rendering", findings, re.I)
    assert re.search(r"same (?:normalized )?(?:finding )?records", findings, re.I)
    assert re.search(r"must\s+not\s+contain.*absent from\s+`?findings\.json`?", findings, re.I | re.S)


# Proposal Test-Intent risk: normalized finding IDs are unstable. Selected
# level: component shape-guard; source: Step 6a Finding Normalization clause.
def test_audit_workflow_finding_id_conventions():
    findings = _section_after_heading(_body(), "## Finding Normalization")

    _assert_section_mentions(findings, ("AD-<round?>-F<NN>", "R<N>-F<NN>"))
    _assert_section_mentions(
        findings,
        (
            "id",
            "source_auditor",
            "source_id",
            "target item",
            "target type",
            "target identity",
            "required",
            "report path",
        ),
    )
    _contains_all_casefold(
        findings,
        ("severity", "drift signal", "citation", "location", "summary"),
    )
    assert re.search(r"closure expectation", findings, re.IGNORECASE)
    assert re.search(r"pipeline-blocking|blocks pipeline", findings, re.IGNORECASE)


# Proposal Test-Intent risk: audit workflow competes with canonical audit
# history ownership. Selected level: component shape-guard; source: Step 6a
# Audit-History Ownership clause.
def test_audit_workflow_audit_history_ownership():
    ownership = _section_after_heading(_body(), "## Audit-History Ownership")

    _assert_section_mentions(ownership, ("audit_history_path", "decision-encoder"))
    assert re.search(r"read(?:s)?\s+`?audit_history_path`?", ownership, re.I)
    assert re.search(r"read-only", ownership, re.I)
    assert re.search(
        r"does\s+not\s+write\s+canonical(?:\s+audit)?\s+history",
        ownership,
        re.I,
    )
    assert re.search(r"does\s+not\s+(?:keep|maintain).*per-critic", ownership, re.I | re.S)
    assert re.search(r"caller.*records|decision-encoder.*records", ownership, re.I | re.S)


# Proposal Test-Intent risk: stale reports are treated as current. Selected
# level: component shape-guard; source: Step 6a Rerun And Currentness clause.
def test_audit_workflow_rerun_equality_predicates():
    rerun = _section_after_heading(_body(), "## Rerun And Currentness Semantics")

    _assert_section_mentions(
        rerun,
        (
            "(target_paths, commit SHA)",
            "(target_paths, branch head SHA at audit time)",
            "(repo, base SHA, head SHA, file list)",
            "(workflow_file, runtime_artifacts_path, root invocation UUID when available, generated report timestamp)",
            "(path, content hash, mtime)",
            "content hash",
        ),
    )
    assert re.search(r"Branch name alone is insufficient", rerun, re.IGNORECASE)
    assert re.search(r"prior\s+LOW.*stale|no-drift.*stale|stale.*prior\s+LOW", rerun, re.I | re.S)


# Proposal Test-Intent risk: standalone and pipeline-callable contracts blur.
# Selected level: component shape-guard; source: Step 6a Standalone Mode and
# Pipeline-Callable Mode clauses.
def test_audit_workflow_modes_split():
    body = _body()
    standalone = _section_after_heading(body, "## Standalone Mode")
    pipeline = _section_after_heading(body, "## Pipeline-Callable Mode")

    _assert_section_mentions(standalone, ("audit_work_dir", "${audit_work_dir}/"))
    _contains_all_casefold(standalone, ("single", "no scratch/planning split"))
    assert re.search(r"no\s+automatic\s+implementation\s+phases", standalone, re.I)

    _assert_section_mentions(pipeline, ("planning_dir", "scratch_dir", "audit_history_path"))
    _contains_all_casefold(pipeline, ("WU identity", "prompts", "logs", "reports"))
    assert "${scratch_dir}/audit/${audit_slug}/" in pipeline
    assert "${planning_dir}/audit/${audit_slug}/" in pipeline
    assert "NES-224" in pipeline
    assert re.search(r"deferred", pipeline, re.IGNORECASE)


# Proposal Test-Intent risk: NES-223 silently wires NES-224 pipeline entry
# modes. Selected level: component shape-guard; source: Step 6a Anti-Scope
# clause.
def test_audit_workflow_anti_scope_excludes_pipeline_wiring():
    anti_scope = _section_after_heading(_body(), "## Anti-Scope")

    _assert_section_mentions(
        anti_scope,
        (
            "Phase 4 risk gates",
            "PR-review gates",
            "workflow-reviewer",
            "process-tree-auditor",
            "pipeline_entry_mode",
        ),
    )
    _contains_all_casefold(
        anti_scope,
        (
            "implementing fixes",
            "revising target artifacts",
            "historical audits",
        ),
    )
