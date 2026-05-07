import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
# Generous upper bound for the current single-sentence overlay evidence rule.
_OVERLAY_EVIDENCE_WINDOW = 400


def _read(path):
    return path.read_text(encoding="utf-8")


def _orchestrator_text():
    return _read(ORCHESTRATOR)


def _section(text, heading_regex):
    match = re.search(rf"(?m)^(?P<level>##+) {heading_regex}\s*$", text)
    assert match, f"missing section heading matching: {heading_regex}"

    level = match.group("level")
    next_heading = re.search(rf"(?m)^{re.escape(level)} ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _assert_contains_all(text, phrases, *, where):
    missing = [phrase for phrase in phrases if phrase not in text]
    assert missing == [], f"{where} missing required text: {missing}"


def _assert_ordered(text, phrases, *, where):
    cursor = 0
    for phrase in phrases:
        index = text.find(phrase, cursor)
        assert index != -1, f"{where} missing ordered text after offset {cursor}: {phrase}"
        cursor = index + len(phrase)


def _assert_regex(text, pattern, description):
    assert re.search(pattern, text), f"missing {description}: {pattern}"


def _phase7_section():
    return _section(_orchestrator_text(), r"Phase 7\s+[-\u2014]\s+CodeRabbit Loop")


def test_phase7_pre_dispatch_swap_record_gate_exists_and_precedes_coderabbit_dispatch():
    phase7 = _phase7_section()

    _assert_contains_all(
        phase7,
        (
            "Pre-dispatch swap-record gate",
            "allow the following Phase 7 CodeRabbit dispatch to proceed",
            "Dispatch `coderabbit-operator` per `~/ai/workflows/coderabbit-loop.md`",
            "branch `${branch_name}`",
            "base `main`",
            "worktree path",
        ),
        where="Phase 7 swap-record gate and CodeRabbit dispatch",
    )
    _assert_ordered(
        phase7,
        (
            "Pre-dispatch swap-record gate",
            "allow the following Phase 7 CodeRabbit dispatch to proceed",
            "Dispatch `coderabbit-operator` per `~/ai/workflows/coderabbit-loop.md`",
        ),
        where="Phase 7 swap-record gate before CodeRabbit dispatch",
    )


def test_phase7_swap_gate_names_canonical_path_and_required_field_tokens():
    phase7 = _phase7_section()

    _assert_contains_all(
        phase7,
        (
            "${planning_dir}/risk/${wu_lower}-prototype-swap-record.md",
            "~/ai/workflows/implementation-pipeline.md",
            "level_id",
            "prototype_ref",
            "component_refs",
            "component_test_results",
            "procedural_test_results",
            "level_behavior_test_results",
            "removed_or_retired_refs",
            "audit_overlay_refs",
        ),
        where="Phase 7 swap-record canonical path and required fields",
    )


def test_phase7_swap_gate_names_terminal_state_vocabulary():
    phase7 = _phase7_section()

    _assert_contains_all(
        phase7,
        (
            "consumed",
            "non-applicable",
            "superseded",
        ),
        where="Phase 7 swap-record terminal-state vocabulary",
    )


def test_phase7_swap_gate_requires_overlay_verdict_currentness_evidence():
    phase7 = _phase7_section()

    _assert_regex(
        phase7,
        rf"(?is)\baudit_overlay_refs\b.{{0,{_OVERLAY_EVIDENCE_WINDOW}}}\bartifact path\b",
        "audit_overlay_refs artifact path evidence",
    )
    _assert_regex(
        phase7,
        rf"(?is)\baudit_overlay_refs\b.{{0,{_OVERLAY_EVIDENCE_WINDOW}}}\b(?:verdict|currentness)\b",
        "audit_overlay_refs verdict or currentness evidence",
    )
    _assert_regex(
        phase7,
        rf"(?is)\baudit_overlay_refs\b.{{0,{_OVERLAY_EVIDENCE_WINDOW}}}\b(?:swapped component inventory|swapped components)\b",
        "audit_overlay_refs applicability to swapped components",
    )


def test_phase7_swap_gate_blocks_missing_or_invalid_with_violation_code_and_needs_input():
    phase7 = _phase7_section()

    _assert_contains_all(
        phase7,
        (
            "prototype_swap_record_missing_or_invalid",
            "NEEDS_INPUT",
            "${scratch_dir}/questions/q-",
            "${planning_dir}/audit-history.md",
        ),
        where="Phase 7 swap-record violation and NEEDS_INPUT handling",
    )
    _assert_regex(
        phase7,
        r"(?is)\bPhase 7\b.{0,180}\bdispatch\b.{0,180}\b(?:refuse|cannot consume|cannot advance)\b"
        r"|\b(?:refuse|cannot consume|cannot advance)\b.{0,180}\bPhase 7\b.{0,180}\bdispatch\b",
        "refused Phase 7 dispatch wording",
    )


def test_phase7_swap_gate_distinguishes_missing_from_non_applicable():
    phase7 = _phase7_section()

    _assert_regex(
        phase7,
        r"(?is)\bmissing\b.{0,80}\b(?:artifact|file)\b.{0,120}\bnot equivalent\b.{0,120}\bnon-applicability\b"
        r"|\bnot equivalent\b.{0,120}\bnon-applicability\b.{0,120}\bmissing\b.{0,80}\b(?:artifact|file)\b",
        "missing artifact is not equivalent to non-applicability",
    )


def test_phase7_swap_gate_preserves_single_operator_scope():
    phase7 = _phase7_section()

    _assert_contains_all(
        phase7,
        (
            "coderabbit-operator",
            "~/ai/workflows/coderabbit-loop.md",
        ),
        where="Phase 7 CodeRabbit operator scope",
    )
    operator_tokens = set(re.findall(r"\b[A-Za-z0-9_-]+-operator\b", phase7))
    workflow_paths = set(re.findall(r"~/ai/workflows/[A-Za-z0-9_.\-/]+", phase7))

    assert operator_tokens <= {"coderabbit-operator"}, f"unexpected Phase 7 operators: {operator_tokens}"
    assert workflow_paths <= {
        "~/ai/workflows/coderabbit-loop.md",
        "~/ai/workflows/implementation-pipeline.md",
    }, f"unexpected Phase 7 workflow paths: {workflow_paths}"


def test_phase7_swap_gate_sits_after_phase6_process_tree_audit_in_whole_file():
    orchestrator = _orchestrator_text()

    _assert_ordered(
        orchestrator,
        (
            "#### Process-tree audit #2",
            "A `blocking` verdict prevents Phase 7.",
            "### Phase 7",
            "Pre-dispatch swap-record gate",
            "prototype_swap_record_missing_or_invalid",
            "Dispatch `coderabbit-operator` per `~/ai/workflows/coderabbit-loop.md`",
        ),
        where="Phase 6 audit to Phase 7 swap-record gate ordering",
    )


def test_swap_gate_test_scope_is_structural_only():
    source = Path(__file__).read_text(encoding="utf-8")
    import_lines = [
        line
        for line in source.splitlines()
        if re.match(r"^\s*(?:import|from)\s+", line)
    ]

    assert import_lines == ["import re", "from pathlib import Path"]
    # Split to avoid the source-level assertion matching itself.
    assert ("sub" + "process") not in source
    assert not re.search(r"(?m)^\s*(?:import|from)\s+pytest\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+yaml\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+.*orchestrator\b", source)
    assert not re.search(r"\bagents\s+(?:-|trace\b|run\b|exec\b)", source)
    assert not re.search(r"(?is)\bopen\([^)]*\$\{planning_dir\}|Path\([^)]*\$\{planning_dir\}", source)
