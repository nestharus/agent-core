import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _workflow_text():
    return _read(WORKFLOW)


def _section(text, heading_regex):
    match = re.search(rf"(?m)^(?P<level>##+) {heading_regex}\s*$", text)
    assert match, f"missing section heading matching: {heading_regex}"

    level = match.group("level")
    level_len = len(level)
    next_heading = re.search(rf"(?m)^#{{1,{level_len}}} ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _assert_contains_all(text, phrases, *, where):
    missing = [phrase for phrase in phrases if phrase not in text]
    assert missing == [], f"{where} missing required text: {missing}"


def _assert_contains_any(text, phrases, *, where):
    assert any(phrase in text for phrase in phrases), (
        f"{where} missing one of required alternatives: {phrases}"
    )


def _assert_ordered(text, phrases, *, where):
    cursor = 0
    for phrase in phrases:
        index = text.find(phrase, cursor)
        assert index != -1, f"{where} missing ordered text after offset {cursor}: {phrase}"
        cursor = index + len(phrase)


def _phase6_top_level(text):
    phase6 = _section(text, r"Phase 6 - Implementation.*")
    step6a = re.search(r"(?m)^### Step 6a - Define contract\s*$", phase6)
    assert step6a, "Phase 6 section missing Step 6a heading"
    return phase6[: step6a.start()]


def test_phase_map_names_recursion_edge():
    workflow = _workflow_text()
    phase_map = _section(workflow, r"Phase Map")

    _assert_contains_all(
        phase_map,
        (
            "Phase 6",
            "child recursion level",
            "level-open",
            "child-levels-open",
        ),
        where="Phase Map recursion edge",
    )
    _assert_ordered(
        phase_map,
        (
            "Phase 2.5",
            "Phase 3",
            "Phase 4",
            "Phase 5",
            "Phase 6",
            "Phase 7",
            "Phase 8",
            "Phase 9",
            "Phase 10",
        ),
        where="Phase Map core path",
    )


def test_phase6_top_level_names_child_entry_and_parent_exit_rules():
    workflow = _workflow_text()
    top_level = _phase6_top_level(workflow)

    _assert_contains_all(
        top_level,
        (
            "child recursion level",
            "audited",
            "ChildLevelFramingRecord",
            "level-open",
            "child-levels-open",
            "candidate child",
            "considered for framing",
            "audit_overlay_refs",
            "level_id",
        ),
        where="Phase 6 recursion entry and parent exit rules",
    )
    prohibited_halt_fields = (
        "halt_basis",
        "halt_record",
        "terminate_recursion",
        "termination_criteria_ref",
    )
    present = [token for token in prohibited_halt_fields if token in top_level]
    assert present == [], f"Phase 6 top-level defines NES-271 halt field tokens: {present}"


def test_step6a_defines_child_level_framing_record_fields():
    workflow = _workflow_text()
    step6a = _section(workflow, r"Step 6a - Define contract")

    _assert_contains_all(
        step6a,
        (
            "ChildLevelFramingRecord",
            "parent_level_id",
            "source_component_implementation_ref",
            "derived_child_outer_contract_ref",
            "transferred_level_behavior_test_refs",
            "persisted_neighbor_claim_refs",
            "framing_rationale_evidence_refs",
            "audit_overlay_refs",
            "parent_artifact_currency_refs",
        ),
        where="Step 6a ChildLevelFramingRecord field set",
    )
    _assert_ordered(
        step6a,
        (
            "parent_level_id",
            "source_component_implementation_ref",
            "derived_child_outer_contract_ref",
            "transferred_level_behavior_test_refs",
            "persisted_neighbor_claim_refs",
            "framing_rationale_evidence_refs",
            "audit_overlay_refs",
            "parent_artifact_currency_refs",
        ),
        where="Step 6a ChildLevelFramingRecord field order",
    )


def test_parent_artifact_currency_refs_is_load_bearing():
    workflow = _workflow_text()
    step6a = _section(workflow, r"Step 6a - Define contract")

    _assert_contains_all(
        step6a,
        (
            "ChildLevelFramingRecord",
            "parent_artifact_currency_refs",
            "are current for child entry",
            "stale",
            "source_component_implementation_ref",
            "derived_child_outer_contract_ref",
            "transferred_level_behavior_test_refs",
            "persisted_neighbor_claim_refs",
            "framing_rationale_evidence_refs",
        ),
        where="Step 6a parent artifact currency contract",
    )


def test_where_artifacts_live_defines_level_id_scoped_artifact_rule():
    workflow = _workflow_text()
    artifacts = _section(workflow, r"Where artifacts live")

    _assert_contains_all(
        artifacts,
        (
            "level_id",
            "<level_id>:<local_artifact_id>",
            "recursive Phase 6",
            "output-index row",
            "emitted test group",
            "residual reference",
            "overlay reference",
            "swap reference",
            "halt reference",
            "child-framing reference",
            "identifier",
            "sibling record",
        ),
        where="Where artifacts live level_id scoped artifact rule",
    )


def test_step6b_and_step6c_carry_level_scope():
    workflow = _workflow_text()
    step6b = _section(workflow, r"Step 6b - Encode tests first")
    step6c = _section(workflow, r"Step 6c - Write code")

    _assert_contains_all(
        step6b,
        (
            "level_id",
            "transferred_level_behavior_test_refs",
            "Step 6b output index",
            "${scratch_dir}/phase6/step6b-output-index.md",
            "<level_id>:<local_artifact_id>",
        ),
        where="Step 6b recursive carry-through",
    )
    _assert_contains_any(
        step6b,
        ("fixture source", "fixture application point"),
        where="Step 6b fixture mapping",
    )
    _assert_contains_any(
        step6b,
        ("emitted test group", "test group identifier"),
        where="Step 6b level-scoped test identifiers",
    )
    _assert_contains_any(
        step6b,
        ("residual entry", "residual reference"),
        where="Step 6b level-scoped residual identifiers",
    )

    _assert_contains_all(
        step6c,
        (
            "level_id",
            "${scratch_dir}/phase6/step6b-output-index.md",
            "Step 6b output index",
        ),
        where="Step 6c recursive scoped consumption",
    )
    _assert_contains_any(
        step6c,
        ("consume", "consumes", "consumption"),
        where="Step 6c consumption wording",
    )
    _assert_contains_any(
        step6c,
        ("emitted tests", "test paths", "test outputs"),
        where="Step 6c test artifact consumption",
    )
    _assert_contains_all(
        step6c,
        ("log evidence",),
        where="Step 6c log evidence wording",
    )


def test_recursion_control_text_cross_references_overlay_review_without_scheduler():
    workflow = _workflow_text()
    top_level = _phase6_top_level(workflow)
    step6a = _section(workflow, r"Step 6a - Define contract")
    recursion_text = top_level + "\n" + step6a

    _assert_contains_all(
        recursion_text,
        (
            "audit_overlay_refs",
            "ChildLevelFramingRecord",
            "audited",
            "scheduler",
            "workflow",
            "operator",
        ),
        where="recursion control overlay review cross-reference",
    )
    _assert_contains_any(
        recursion_text,
        ("reviewed", "review evidence", "review"),
        where="recursion control reviewed framing wording",
    )
    _assert_contains_any(
        recursion_text,
        ("does not add a new scheduler", "does not add a new scheduler, workflow, or operator"),
        where="recursion control scheduler anti-scope wording",
    )
