import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


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


def _subsection(text, heading_regex):
    return _section(text, heading_regex)


def _child_recursion_section():
    return _subsection(
        _orchestrator_text(),
        r"Child-recursion fire detection and child-level entry",
    )


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


def _assert_regex(text, pattern, description):
    assert re.search(pattern, text), f"missing {description}: {pattern}"


def _agents_command_token():
    return "age" + "nts -m gpt-high"


def test_child_recursion_fire_detection_section_exists_and_is_ordered():
    orchestrator = _orchestrator_text()

    _assert_contains_all(
        orchestrator,
        (
            "#### Step 6c — Write code",
            "#### Child-recursion fire detection and child-level entry",
            "#### Process-tree audit #2",
            "### Phase 7 — CodeRabbit Loop",
        ),
        where="child-recursion section anchors",
    )
    _assert_ordered(
        orchestrator,
        (
            "#### Step 6c — Write code",
            "#### Child-recursion fire detection and child-level entry",
            "#### Process-tree audit #2",
            "### Phase 7 — CodeRabbit Loop",
        ),
        where="child-recursion section ordering",
    )


def test_child_recursion_fire_detection_names_trigger_sources():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "LevelComponentSet",
            "CouplingDecision",
            "Phase 3",
            "accepted internal components",
            "candidate child",
            "current level_id",
            "multi-layer",
        ),
        where="child-recursion trigger detection",
    )
    _assert_regex(
        section,
        r"(?is)\bACR-7\b.{0,240}\bmulti-layer\b.{0,240}\bmust not\b"
        r"|\bmulti-layer\b.{0,240}\bACR-7\b.{0,240}\bmust not\b"
        r"|\bmulti-layer\b.{0,240}\bmust not\b.{0,240}\bACR-7\b",
        "ACR-7 multi-layer evidence must not feed child recursion",
    )


def test_child_level_framing_record_composition_names_all_fields_in_order():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "ChildLevelFramingRecord",
            "${planning_dir}/risk/${wu_lower}-child-framing-${child_level_id}.md",
        ),
        where="ChildLevelFramingRecord composition",
    )
    _assert_ordered(
        section,
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
        where="ChildLevelFramingRecord field order",
    )


def test_child_framing_verify_gate_requires_currency_and_audit_refs():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "Child-framing verify gate",
            "audit_overlay_refs",
            "parent_artifact_currency_refs",
            "current",
            "stale",
            "superseded",
            "residual risk",
            "child level-open transition",
        ),
        where="Child-framing verify gate currency and audit refs",
    )


def test_child_framing_verify_gate_refuses_missing_or_stale_record():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "Verify",
            "ChildLevelFramingRecord",
            "missing or stale parent_artifact_currency_refs",
            "refuse",
            "${planning_dir}/audit-history.md",
            "actor=implementation-pipeline-orchestrator",
            "${scratch_dir}/questions/q-",
            "NEEDS_INPUT",
            "NEEDS_INPUT:<absolute_question_artifact_path>",
            "child_level_framing_record_missing_or_invalid",
            "child level-open transition",
        ),
        where="Child-framing verify gate refusal",
    )
    _assert_contains_any(
        section,
        (
            "blocking NEEDS_INPUT for evidence repair",
            "blocking `NEEDS_INPUT` for evidence repair",
        ),
        where="Child-framing verify gate evidence repair",
    )


def test_recursive_child_phase6_dispatch_reuses_step6abc_with_child_level_id():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "Recursive child Phase 6 dispatch",
            "Step 6a",
            "Step 6b",
            "Step 6c",
            "fresh",
            "separate",
            _agents_command_token(),
            "different invocation UUID",
            "level_id",
            "${scratch_dir}/phase6/step6b-output-index.md",
            "<level_id>:<local_artifact_id>",
        ),
        where="Recursive child Phase 6 dispatch",
    )


def test_recursive_child_phase6_dispatch_preserves_test_code_separation():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "test-writer",
            "code-writer",
            "child-scoped Step 6b output-index rows",
            "before product-code changes",
        ),
        where="Recursive child Phase 6 dispatch test/code separation",
    )
    _assert_regex(
        section,
        r"(?is)\bStep 6b\b.{0,280}\btest-writer\b.{0,280}\bStep 6c\b.{0,280}\bcode-writer\b"
        r"|\btest-writer\b.{0,280}\bStep 6b\b.{0,280}\bcode-writer\b.{0,280}\bStep 6c\b"
        r"|\bStep 6b\b.{0,280}\bStep 6c\b.{0,280}\btest-writer\b.{0,280}\bcode-writer\b",
        "child Step 6b test-writer and Step 6c code-writer separation",
    )


def test_recursive_parent_exit_gate_requires_all_candidates_considered():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "Recursive parent exit gate",
            "child-levels-open",
            "each candidate child",
            "considered for framing",
            "missing consideration is not non-applicability",
            "child_candidate_framing_consideration_missing",
        ),
        where="Recursive parent exit gate",
    )


def test_termination_reuses_existing_halt_gate_without_redefining_halt():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "#### Phase 6 halt-state transition gate",
            "HaltRecord",
            "halt_record_missing_or_invalid",
            "halt_overrules_split_or_revise_by_omission",
        ),
        where="recursive termination halt-gate citation",
    )
    _assert_contains_any(
        section,
        (
            "ACR-11 does not redefine halt criteria",
            "ACR-11 does NOT redefine halt criteria",
            "does not redefine halt criteria",
        ),
        where="recursive termination no halt redefinition",
    )
    _assert_regex(
        section,
        r"(?is)\bdoes not redefine\b.{0,220}\bhalt criteria\b"
        r"|\bdoes NOT redefine\b.{0,220}\bhalt criteria\b",
        "ACR-11 does not redefine halt criteria",
    )


def test_recursive_phase6_reuse_semantics_included_in_process_tree_audit2():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        (
            "Recursive Phase 6 reuse semantics",
            "Process-tree audit #2",
            "child-level Step 6b",
            "child-level Step 6c",
            "test-writer invocation UUID",
            "Step 6c invocation UUID",
            "level_id",
            "recursive_phase6_reuse_evidence_missing",
        ),
        where="Recursive Phase 6 reuse semantics",
    )


def test_recursion_control_preserves_no_new_operator_or_workflow_scope():
    section = _child_recursion_section()

    _assert_contains_all(
        section,
        ("does not add a new scheduler, workflow, or operator",),
        where="child-recursion anti-scope footer",
    )

    operator_tokens = set(re.findall(r"\b[A-Za-z0-9_-]+-operator\b", section))
    workflow_paths = set(re.findall(r"~/ai/workflows/[A-Za-z0-9_.\-/]+", section))

    allowed_operator_tokens = {
        "agentsmd-curator",
        "agentsmd-maintenance-orchestrator",
        "alignment-cycle-orchestrator",
        "coderabbit-operator",
        "commit-hygiene-operator",
        "fastapi-review-operator",
        "implementation-pipeline-orchestrator",
        "jira-operator",
        "jj-operator",
        "linear-operator",
        "pipeline-artifacts-operator",
        "pr-review-operator",
        "process-tree-auditor",
        "release-cut-operator",
        "release-hotfix-operator",
        "release-orchestrator",
        "release-promote-operator",
        "release-reconcile-operator",
        "roadmap-orchestrator",
        "worktree-operator",
        "wu-session-resumer",
    }
    allowed_workflow_paths = {"~/ai/workflows/implementation-pipeline.md"}

    assert operator_tokens <= allowed_operator_tokens, (
        f"unexpected child-recursion operator references: {operator_tokens}"
    )
    assert workflow_paths <= allowed_workflow_paths, (
        f"unexpected child-recursion workflow references: {workflow_paths}"
    )


def test_recursion_control_test_scope_is_structural_only():
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
    assert not re.search(r"(?m)^\s*(?:import|from)\s+ya" + r"ml\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+.*orchestrator\b", source)
    assert not re.search(r"\bage" + r"nts\s+(?:-|trace\b|run\b|exec\b)", source)
    assert not re.search(r"(?is)\bopen\([^)]*\$\{planning_dir\}|Path\([^)]*\$\{planning_dir\}", source)
