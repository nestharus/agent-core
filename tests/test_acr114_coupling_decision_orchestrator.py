import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _orchestrator_text():
    return _read(ORCHESTRATOR)


def _workflow_text():
    return _read(WORKFLOW)


def _section(text, heading_regex):
    match = re.search(rf"(?m)^(?P<level>##+) {heading_regex}\s*$", text)
    assert match, f"missing section heading matching: {heading_regex}"

    level = match.group("level")
    next_heading = re.search(rf"(?m)^{re.escape(level)} ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _phase6_section():
    return _section(_orchestrator_text(), r"Phase 6\s+[-\u2014]\s+.*")


def _step6c_section():
    return _section(_phase6_section(), r"Step 6c\s+[-\u2014]\s+Write code")


def _audit2_section():
    return _section(_phase6_section(), r"Process-tree audit #2")


def _workflow_phase6_section():
    return _section(_workflow_text(), r"Phase 6\b.*")


def _workflow_step6b_section():
    return _section(_workflow_phase6_section(), r"Step 6b\b.*")


def _workflow_step6c_section():
    return _section(_workflow_phase6_section(), r"Step 6c\b.*")


def _workflow_process_tree_rule():
    step6c = _workflow_step6c_section()
    match = re.search(r"(?is)(?:^|\n)- Rule: Process-tree review:.*?(?:\n- Rule:|\Z)", step6c)
    assert match, "workflow Step 6c missing Process-tree review rule"
    return match.group(0)


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


def test_phase6_workflow_role_split_present_in_workflow_and_operator():
    workflow = _workflow_phase6_section()
    step6c = _step6c_section()

    _assert_contains_all(
        workflow,
        (
            "coupling-auditor",
            "integrations between components",
            "component pairs",
            "cohesion-auditor",
            "individual components",
        ),
        where="workflow Phase 6 role split",
    )
    _assert_contains_all(
        step6c,
        (
            "coupling-auditor",
            "cohesion-auditor",
        ),
        where="operator Step 6c role split",
    )


def test_step6c_bidirectional_coupling_outcome_present_in_workflow_and_operator():
    workflow = _workflow_step6c_section()
    step6c = _step6c_section()
    tokens = (
        "merge",
        "merge_components",
        "introduce",
        "abstraction component",
        "introduce_abstraction_component",
    )

    _assert_contains_all(workflow, tokens, where="workflow bidirectional coupling outcome")
    _assert_contains_all(step6c, tokens, where="operator bidirectional coupling outcome")


def test_step6c_couplingdecision_schema_and_verdicts_present_in_workflow_and_operator():
    workflow = _workflow_step6c_section()
    step6c = _step6c_section()
    tokens = (
        "CouplingDecision",
        "merge_components",
        "introduce_abstraction_component",
        "no_change",
    )

    _assert_contains_all(workflow, tokens, where="workflow CouplingDecision verdicts")
    _assert_contains_all(step6c, tokens, where="operator CouplingDecision verdicts")


def test_step6b_output_index_carries_coupling_decision_ref_workflow_and_operator():
    workflow_step6b = _workflow_step6b_section()
    step6c = _step6c_section()

    _assert_contains_all(
        workflow_step6b,
        (
            "coupling_decision_ref",
            "level_id",
            "integration_test_refs",
        ),
        where="workflow Step 6b coupling decision output index",
    )
    _assert_contains_all(
        step6c,
        (
            "coupling_decision_ref",
            "CouplingDecision",
            "Process-tree audit #2",
        ),
        where="operator Step 6c coupling decision handoff",
    )
    _assert_ordered(
        _phase6_section(),
        (
            "coupling_decision_ref",
            "#### Process-tree audit #2",
        ),
        where="operator coupling decision handoff before audit #2",
    )


def test_process_tree_audit_2_requires_couplingdecision_evidence_workflow_and_operator():
    workflow_rule = _workflow_process_tree_rule()
    audit2 = _audit2_section()

    _assert_contains_all(
        workflow_rule,
        (
            "CouplingDecision",
            "auditor evidence refs",
            "current component inventory",
            "integration_test_refs",
        ),
        where="workflow Process-tree review",
    )
    _assert_contains_all(
        audit2,
        (
            "CouplingDecision",
            "coupling_audit_report_refs",
            "cohesion_audit_report_refs",
            "current",
            "level_id",
            "integration_test_refs",
        ),
        where="operator Process-tree audit #2",
    )


def test_step6c_detects_coupling_cohesion_applicability():
    step6c = _step6c_section()

    _assert_regex(step6c, r"(?m)^4\.", "Step 6c numbered detection sub-step")
    _assert_contains_all(
        step6c,
        (
            "passing level evidence",
            "candidate or accepted current-layer component inventory",
            "coupling",
            "cohesion",
        ),
        where="operator Step 6c ACR-114 applicability detection",
    )


def test_step6c_requires_couplingdecision_adjacent_to_levelcomponentset_or_candidate():
    step6c = _step6c_section()

    _assert_contains_all(
        step6c,
        (
            "CouplingDecision",
            "adjacent",
            "LevelComponentSet",
            "candidate component inventory",
        ),
        where="operator Step 6c CouplingDecision adjacency",
    )
    _assert_regex(
        step6c,
        r"(?is)\bCouplingDecision\b.{0,260}\bLevelComponentSet\b.{0,260}\bcandidate component inventory\b"
        r"|\bCouplingDecision\b.{0,260}\bcandidate component inventory\b.{0,260}\bLevelComponentSet\b",
        "CouplingDecision adjacency to LevelComponentSet or candidate inventory",
    )


def test_step6c_couplingdecision_required_field_tokens_present():
    step6c = _step6c_section()

    _assert_contains_all(
        step6c,
        (
            "level_id",
            "source_level_component_set_ref",
            "candidate_component_inventory_ref",
            "coupling_audit_report_refs",
            "cohesion_audit_report_refs",
            "verdict",
            "changed_component_refs",
            "removed_or_retired_refs",
            "new_abstraction_component_refs",
            "integration_test_refs",
            "rationale_evidence_refs",
            "defer_to_prototype_risk",
        ),
        where="operator Step 6c CouplingDecision required fields",
    )


def test_step6c_couplingdecision_verdict_enum_exact_values():
    step6c = _step6c_section()

    _assert_regex(
        step6c,
        r"(?is)\bverdict\b.{0,260}\bmerge_components\b.{0,160}\bintroduce_abstraction_component\b.{0,160}\bno_change\b",
        "CouplingDecision verdict enum exact values",
    )


def test_step6c_stay_at_current_level_constraint_explicit():
    step6c = _step6c_section()

    _assert_contains_all(
        step6c,
        (
            "current",
            "level_id",
            "nested sub-components",
            "grandchild components",
            "multi-layer hierarchy",
        ),
        where="operator Step 6c current-level constraint",
    )


def test_step6c_changed_inventory_requires_integration_test_refs_with_halt_pattern():
    step6c = _step6c_section()

    _assert_contains_all(
        step6c,
        (
            "rerun/current",
            "integration_test_refs",
            "current component inventory",
            "${planning_dir}/audit-history.md",
            "actor=implementation-pipeline-orchestrator",
            "Phase 6",
            "coupling_decision_missing_or_invalid",
            "Phase 6 advance to Process-tree audit #2 / Phase 7",
            "${scratch_dir}/questions/q-<uuidv4>.question.json",
            "NEEDS_INPUT:<absolute_question_artifact_path>",
        ),
        where="operator Step 6c changed-inventory halt pattern",
    )
    _assert_regex(
        step6c,
        r"(?is)\bblocking\b|\bevidence repair, not a self-resolvable procedural question\b",
        "blocking evidence repair halt wording",
    )


def test_process_tree_audit_2_manifest_extends_with_couplingdecision_and_halt_pattern():
    audit2 = _audit2_section()

    _assert_contains_all(
        audit2,
        (
            "CouplingDecision",
            "coupling_audit_report_refs",
            "cohesion_audit_report_refs",
            "current",
            "level_id",
            "integration_test_refs",
            "coupling_decision_missing_or_invalid",
            "NEEDS_INPUT:<absolute_question_artifact_path>",
        ),
        where="operator Process-tree audit #2 CouplingDecision manifest",
    )
    _assert_regex(
        audit2,
        r"(?is)\bhalt pattern\b|\bStep 6c\b.{0,160}\bsub-step 9\b",
        "Process-tree audit #2 halt-pattern reference",
    )


def test_step6c_explicit_non_applicable_requirement_for_inapplicable_wus():
    step6c = _step6c_section()

    _assert_contains_all(
        step6c,
        (
            "non-applicable",
            "canonical",
            "CouplingDecision",
            "adjacency locator",
        ),
        where="operator Step 6c explicit non-applicability path",
    )
    _assert_regex(
        step6c,
        r"missing artifact is NOT equivalent to non-applicability",
        "missing artifact is NOT equivalent to non-applicability",
    )


def test_acr114_step6c_window_forbids_scoped_deferral_framing():
    phase6 = _phase6_section()
    step6c = _step6c_section()
    audit2 = _audit2_section()
    window = step6c + "\n" + audit2

    _assert_ordered(
        phase6,
        (
            "#### Step 6c",
            "#### Process-tree audit #2",
        ),
        where="ACR-114 Step 6c window before audit #2",
    )
    for phrase in (
        "defer to ACR-114",
        "deferred to ACR-114",
        "pending ACR-114",
        "TODO ACR-114",
        "see ACR-114",
    ):
        assert phrase not in window, f"ACR-114 window contains forbidden phrase: {phrase}"


def test_acr114_subrules_precede_audit2_then_halt_gate_then_phase7_in_whole_file():
    orchestrator = _orchestrator_text()
    step6c = _step6c_section()
    marker_offsets = [
        step6c.find("coupling-auditor"),
        step6c.find("CouplingDecision"),
    ]
    marker_offsets = [offset for offset in marker_offsets if offset != -1]
    assert marker_offsets, "Step 6c missing ACR-114 sub-step marker"

    step6c_start = orchestrator.find(step6c)
    assert step6c_start != -1, "Step 6c section not found in operator text"
    marker_index = step6c_start + min(marker_offsets)
    audit_index = orchestrator.find("#### Process-tree audit #2")
    halt_index = orchestrator.find("#### Phase 6 halt-state transition gate")
    phase7_index = orchestrator.find("### Phase 7")

    assert marker_index < audit_index < halt_index < phase7_index, (
        "ACR-114 subrules must precede audit #2, halt gate, and Phase 7"
    )


def test_no_step_6d_introduced():
    phase6 = _phase6_section()

    assert re.search(r"(?m)^#### Step 6d\b", phase6) is None, (
        "operator Phase 6 must not introduce Step 6d"
    )


def test_acr114_test_scope_is_structural_only():
    source = Path(__file__).read_text(encoding="utf-8")
    import_lines = [
        line
        for line in source.splitlines()
        if re.match(r"^\s*(?:import|from)\s+", line)
    ]

    assert set(import_lines) == {"import re", "from pathlib import Path"}, (
        f"unexpected imports: {import_lines}"
    )
    assert len(import_lines) == 2, f"duplicate import lines: {import_lines}"
    assert ("sub" + "process") not in source
    assert not re.search(r"(?m)^\s*(?:import|from)\s+pytest\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+yaml\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+.*orchestrator\b", source)
    assert not re.search(r"\bagents\s+(?:-|trace\b|run\b|exec\b)", source)
    assert not re.search(r"(?is)\bopen\([^)]*\$\{planning_dir\}|Path\([^)]*\$\{planning_dir\}", source)
