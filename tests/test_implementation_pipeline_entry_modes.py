import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _workflow_text():
    return _read(WORKFLOW)


def _orchestrator_text():
    return _read(ORCHESTRATOR)


def _frontmatter(text):
    parts = text.split("---", 2)
    assert len(parts) == 3, "workflow doc must have YAML frontmatter"
    return parts[1]


def _assert_contains_all(text, needles):
    missing = [needle for needle in needles if needle not in text]
    assert missing == []


def _assert_regex(text, pattern, description):
    assert re.search(pattern, text), f"missing {description}: {pattern}"


def _assert_ordered(text, *needles):
    cursor = 0
    for needle in needles:
        index = text.find(needle, cursor)
        assert index != -1, f"missing ordered text after offset {cursor}: {needle}"
        cursor = index + len(needle)


# NES-224 AC1/AC16, assumptions A5/A10, component shape guard.
def test_workflow_declares_entry_modes_and_default_normal():
    workflow = _workflow_text()
    frontmatter = _frontmatter(workflow)

    _assert_contains_all(workflow, ("normal", "review_first", "plug_existing_review"))
    _assert_regex(workflow, r"(?is)normal.{0,80}default|default.{0,80}normal", "default-normal text")
    assert "### `research_shape`" not in workflow
    assert "pipeline_entry_mode=research_shape" not in workflow
    assert not re.search(r"(?m)^\s*entry_modes\s*:", frontmatter)


# NES-224 AC2/AC3, assumptions A2/A4, component shape guard.
def test_review_first_insertion_and_audit_outputs():
    combined = _workflow_text() + "\n" + _orchestrator_text()

    _assert_ordered(combined, "Phase 0", "review_first", "Phase 2.5")
    _assert_contains_all(
        combined,
        (
            "${planning_dir}/audit/",
            "dispatch-manifest.md",
            "aggregate-audit.md",
            "findings.json",
            "findings.md",
        ),
    )


# NES-224 AC7, assumption A4, component shape guard.
def test_review_first_preserves_phase25_required_artifacts_and_evidence_role():
    combined = _workflow_text() + "\n" + _orchestrator_text()

    _assert_contains_all(
        combined,
        (
            "problem-map",
            "coverage",
            "lifecycle",
            "entrypoints",
            "duplicates",
            "cross-language",
            "risk-profile",
        ),
    )
    _assert_regex(
        combined,
        r"(?is)review_first.{0,500}evidence.{0,500}not a substitute",
        "review_first evidence-not-substitute framing",
    )


# NES-224 AC13, assumptions A2/A4, component shape guard.
def test_process_tree_audit_timing_for_review_first():
    orchestrator = _orchestrator_text()

    _assert_regex(
        orchestrator,
        r"(?is)audit fanout.{0,120}(?:return|join).{0,500}process-tree-auditor.{0,500}(?:Phase 2\.5|Phase 3).{0,200}consum",
        "audit fanout process-tree audit before consumption",
    )
    _assert_regex(
        orchestrator,
        r"(?is)Entry modes add an additional process-tree audit.{0,160}before Phase 2\.5 or Phase 3 consumes",
        "entry-mode additional process-tree audit count",
    )
    _assert_regex(
        orchestrator,
        r"(?is)Phase 4.{0,800}expected-process.{0,400}entry-mode subtree",
        "Phase 4 expected-process manifest names entry-mode subtree",
    )


# NES-224 AC14, assumption A4, component shape guard.
def test_value_zero_termination_after_review_first_low_aggregate():
    orchestrator = _orchestrator_text()

    _assert_contains_all(
        orchestrator,
        (
            "aggregate LOW",
            "no remaining value",
            "DECISIONS.md",
            "WU id",
            "phase",
            "evidence path",
            "${ticket_operator}",
            "task=comment",
            "halt-before-Phase-3",
            "every current ticket acceptance/scope item",
            "no remaining non-audit implementation or verification ask",
            "previously unevaluated value, scope, or trade-off question",
        ),
    )


# NES-224 AC4, assumptions A1/A2/A3/A6, component shape guard.
def test_plug_existing_review_schema_and_currentness():
    orchestrator = _orchestrator_text()

    _assert_contains_all(
        orchestrator,
        (
            "existing_review_bundle_schema",
            "nes-design-audit-v1",
            "target identity",
            "currentness",
            "pre-Phase-3 validation",
        ),
    )


# NES-224 AC4, assumptions A1/A2, component shape guard.
def test_plug_existing_review_rejects_missing_required_bundle_file():
    orchestrator = _orchestrator_text()

    _assert_regex(
        orchestrator,
        r"(?is)findings\.json.{0,300}required[- ]file.{0,400}missing[- ]file.{0,400}BEFORE Phase 3 prompt composition",
        "missing required bundle file rejection before Phase 3",
    )


# NES-224 AC8, assumption A6, component shape guard.
def test_imported_finding_id_mapping_preserved():
    orchestrator = _orchestrator_text()

    _assert_contains_all(
        orchestrator,
        (
            "source_id",
            "origin_bundle_path",
            "SEED-FNN",
            "R<N>-F<NN>",
            "decision-encoder",
        ),
    )


# NES-224 AC5, assumptions A3/A6, component shape guard.
def test_stale_low_reports_do_not_close_changed_targets():
    combined = _workflow_text() + "\n" + _orchestrator_text()

    _assert_contains_all(
        combined,
        (
            "stale LOW",
            "no-drift",
            "changed targets",
            "context only",
            "current re-audit before closure",
        ),
    )


# NES-224 AC5, assumptions A3/A6, component shape guard.
def test_stale_bundle_import_requires_fallback_policy():
    orchestrator = _orchestrator_text()

    _assert_contains_all(orchestrator, ("stale bundle", "fallback policy"))
    _assert_regex(
        orchestrator,
        r"(?is)(NEEDS_INPUT:<absolute_artifact_path>|rerun `?review_first`?)",
        "stale bundle fallback action",
    )
    assert "cannot certify changed targets" in orchestrator


# NES-224 AC5, assumptions A3/A6, component shape guard.
def test_reaudit_after_substantive_revision_defined():
    combined = _workflow_text() + "\n" + _orchestrator_text()

    _assert_regex(combined, r"(?is)substantive revision", "substantive revision definition")
    _assert_regex(
        combined,
        r"(?is)rerun(?:ning)? `?audit\.md`?.{0,300}before findings close|before findings close.{0,300}rerun(?:ning)? `?audit\.md`?",
        "audit rerun before findings close",
    )
    _assert_regex(
        combined,
        r"(?is)re-enter Phase 3.{0,120}proposal redesign.{0,120}Phase 4.{0,120}re-gating",
        "substantive-revision re-entry logic",
    )


# NES-224 AC6, assumption A8, component shape guard.
def test_phase3_prompt_includes_audit_bundle_and_design_research_handoff():
    orchestrator = _orchestrator_text()

    _assert_regex(orchestrator, r"(?is)Phase 3.{0,1200}aggregate-audit\.md", "Phase 3 aggregate audit handoff")
    _assert_contains_all(
        orchestrator,
        (
            "findings.json",
            "findings.md",
            "dispatch-manifest.md",
            "per-auditor reports",
            "target identity/staleness",
            "design-fix research handoff",
        ),
    )


# NES-224 AC6, assumption A8, component shape guard.
def test_targeted_research_is_orchestrator_visible():
    orchestrator = _orchestrator_text()

    _assert_contains_all(
        orchestrator,
        (
            "DESIGN_RESEARCH_REQUIRED",
            "workflows/research.md",
            "${planning_dir}/research/design-fixes/",
        ),
    )


# NES-224 AC10, assumption A5, component shape guard.
def test_normal_mode_rejects_audit_field_pollution():
    orchestrator = _orchestrator_text()

    _assert_regex(orchestrator, r"(?is)(absent|normal mode).{0,300}audit-only fields", "normal-mode audit-only field rejection")
    _assert_contains_all(
        orchestrator,
        (
            "audit_workflow_path",
            "audit_target_type",
            "existing_review_bundle_path",
            "review_staleness_policy",
            "proposer_fix_scope",
            "BLOCKED:entry-mode-input-conflict",
        ),
    )


# NES-224 AC10, selector fail-closed shape guard.
def test_rejects_unknown_pipeline_entry_mode():
    orchestrator = _orchestrator_text()

    assert "BLOCKED:unknown-pipeline-entry-mode" in orchestrator
    _assert_regex(
        orchestrator,
        r"(?is)fail[- ]closed",
        "unknown entry-mode fail-closed prohibition",
    )


# NES-224 AC15, assumption A6, component shape guard.
def test_audit_history_insertion_trigger():
    orchestrator = _orchestrator_text()

    _assert_contains_all(
        orchestrator,
        (
            "second round",
            "decision-encoder",
            "bundle path",
            "target identity",
            "aggregate verdict",
            "source IDs",
            "WU-local IDs",
            "currentness flag",
        ),
    )
