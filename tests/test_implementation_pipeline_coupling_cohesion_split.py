import re
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / "workflows" / "implementation-pipeline.md"
)
PHASE_6_HEADING = "## Phase 6 - Implementation (required; test/code separation)"
PHASE_7_HEADING = "## Phase 7 - CodeRabbit Loop"
STEP_6A_HEADING = "### Step 6a - Define contract"
STEP_6B_HEADING = "### Step 6b - Encode tests first"
STEP_6C_HEADING = "### Step 6c - Write code"


def _section(text, start_heading, end_heading=None):
    assert start_heading in text, f"missing token verbatim: {start_heading}"
    start = text.index(start_heading)
    if end_heading is None:
        return text[start:]

    after_start = text[start + len(start_heading) :]
    assert end_heading in after_start, f"missing token verbatim: {end_heading}"
    end = text.index(end_heading, start + len(start_heading))
    return text[start:end]


def _assert_token(text, token, *, where):
    assert token in text, f"{where} missing token verbatim: {token}"


def _assert_regex(text, pattern, missing_token, *, where):
    assert re.search(pattern, text), f"{where} missing token verbatim: {missing_token}"


def _phase6_sections():
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    phase6_text = _section(workflow_text, PHASE_6_HEADING, PHASE_7_HEADING)
    return {
        "phase6_text": phase6_text,
        "phase6_top_text": _section(phase6_text, PHASE_6_HEADING, STEP_6A_HEADING),
        "step6b_text": _section(phase6_text, STEP_6B_HEADING, STEP_6C_HEADING),
        "step6c_text": _section(phase6_text, STEP_6C_HEADING),
    }


def _phase6_top_text():
    return _phase6_sections()["phase6_top_text"]


def _step6b_text():
    return _phase6_sections()["step6b_text"]


def _step6c_text():
    return _phase6_sections()["step6c_text"]


def _couplingdecision_region(step6c_text):
    _assert_token(step6c_text, "CouplingDecision", where="Step 6c")
    match = re.search(r"(?is).{0,700}CouplingDecision.{0,1300}", step6c_text)
    assert match, "Step 6c missing token verbatim: CouplingDecision"
    return match.group(0)


def _process_tree_review_sentence(step6c_text):
    match = re.search(r"(?is)(?:^|\n)- Rule: Process-tree review:.*?(?:\n- Rule:|\Z)", step6c_text)
    assert match, "Step 6c missing token verbatim: Process-tree review"
    return match.group(0)


def test_phase6_top_names_coupling_role_split():
    """Risk T1: role-split deletion. Level: structural pytest. Source: NES-282 contract T1."""
    phase6_top_text = _phase6_top_text()

    assert "coupling-auditor" in phase6_top_text, (
        "Phase 6 top text missing token verbatim: coupling-auditor"
    )
    _assert_regex(
        phase6_top_text,
        r"(?is)\bintegrations between components\b|\bcomponent pairs?\b",
        "integrations between components",
        where="Phase 6 coupling role split",
    )


def test_phase6_top_names_cohesion_role_split():
    """Risk T2: cohesion role drift. Level: structural pytest. Source: NES-282 contract T2."""
    phase6_top_text = _phase6_top_text()

    assert "cohesion-auditor" in phase6_top_text, (
        "Phase 6 top text missing token verbatim: cohesion-auditor"
    )
    _assert_regex(
        phase6_top_text,
        r"(?is)\bindividual components\b|\bper-component organization\b",
        "individual components",
        where="Phase 6 cohesion role split",
    )


def test_step6c_bidirectional_coupling_rule():
    """Risk T3: one-directional coupling behavior. Level: structural pytest. Source: NES-282 contract T3."""
    step6c_text = _step6c_text()

    assert re.search(
        r"(?is)\bmerge\b.{0,160}\b(?:component elements|components|together)\b",
        step6c_text,
    ), (
        "Step 6c bidirectional coupling rule missing token verbatim: merge"
    )
    _assert_regex(
        step6c_text,
        r"(?is)\babstraction component\b.{0,180}\bdecoupl\w*\b|\bdecoupl\w*\b.{0,180}\babstraction component\b",
        "abstraction component",
        where="Step 6c bidirectional coupling rule",
    )


def test_couplingdecision_verdict_tokens_present():
    """Risk T4: verdict-token drift. Level: structural pytest. Source: NES-282 contract T4."""
    step6c_text = _step6c_text()

    for token in (
        "merge_components",
        "introduce_abstraction_component",
        "no_change",
    ):
        assert token in step6c_text, (
            f"Step 6c CouplingDecision verdict missing token verbatim: {token}"
        )


def test_couplingdecision_level_id_and_levelcomponentset_link():
    """Risk T5: decision record loses level scope. Level: structural pytest. Source: NES-282 contract T5."""
    step6c_text = _step6c_text()

    assert "CouplingDecision" in step6c_text, (
        "Step 6c missing token verbatim: CouplingDecision"
    )
    region = _couplingdecision_region(step6c_text)

    for token in (
        "CouplingDecision",
        "level_id",
        "source_level_component_set_ref",
        "candidate_component_inventory_ref",
        "LevelComponentSet",
        "defer_to_prototype_risk",
    ):
        _assert_token(region, token, where="Step 6c CouplingDecision record")


def test_couplingdecision_evidence_ref_fields():
    """Risk T6: auditor evidence omitted. Level: structural pytest. Source: NES-282 contract T6."""
    step6c_text = _step6c_text()

    for token in (
        "coupling_audit_report_refs",
        "cohesion_audit_report_refs",
        "rationale_evidence_refs",
    ):
        assert token in step6c_text, (
            f"Step 6c CouplingDecision evidence fields missing token verbatim: {token}"
        )


def test_couplingdecision_inventory_delta_fields():
    """Risk T7: inventory deltas implicit. Level: structural pytest. Source: NES-282 contract T7."""
    step6c_text = _step6c_text()

    for token in (
        "changed_component_refs",
        "removed_or_retired_refs",
        "new_abstraction_component_refs",
        "integration_test_refs",
    ):
        assert token in step6c_text, (
            f"Step 6c CouplingDecision inventory fields missing token verbatim: {token}"
        )


def test_step6c_process_tree_review_requires_couplingdecision():
    """Risk T8: process-tree review misses coupling decisions. Level: structural pytest. Source: NES-282 contract T8."""
    step6c_text = _step6c_text()
    review_sentence = _process_tree_review_sentence(step6c_text)

    assert "CouplingDecision" in review_sentence, (
        "Step 6c process-tree review missing token verbatim: CouplingDecision"
    )
    _assert_regex(
        review_sentence,
        r"(?is)\bbefore Phase 7\b",
        "before Phase 7",
        where="Step 6c process-tree review",
    )


def test_step6b_output_index_coupling_decision_handoff():
    """Risk T9: Step 6b output-index handoff loses decision evidence. Level: structural pytest. Source: NES-282 contract T9."""
    step6b_text = _step6b_text()

    assert "coupling_decision_ref" in step6b_text, (
        "Step 6b output index missing token verbatim: coupling_decision_ref"
    )
    _assert_token(step6b_text, "level_id", where="Step 6b output index")
    _assert_token(
        step6b_text,
        "${scratch_dir}/phase6/step6b-output-index.md",
        where="Step 6b output index",
    )


def test_no_step_6d_introduced():
    """Risk T10: Phase 6 shape drift. Level: structural pytest. Source: NES-282 contract T10."""
    phase6_sections = _phase6_sections()
    forbidden_heading = "### Step " + "6d"

    assert re.search(rf"(?m)^{re.escape(forbidden_heading)}\b", phase6_sections["phase6_text"]) is None, (
        f"Phase 6 contains forbidden heading: {forbidden_heading}"
    )
