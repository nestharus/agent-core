import re
import subprocess
from pathlib import Path


PHASE_6_HEADING = "## Phase 6 - Implementation (required; test/code separation)"
PHASE_7_HEADING = "## Phase 7 - CodeRabbit Loop"
STEP_6A_HEADING = "### Step 6a - Define contract"
STEP_6B_HEADING = "### Step 6b - Encode tests first"
STEP_6C_HEADING = "### Step 6c - Write code"
OPERATOR_PHASE_6_HEADING = (
    "### Phase 6 \u2014 Implementation (test/code separation) + Process-tree Audit #2"
)
OPERATOR_STEP_6C_HEADING = "#### Step 6c \u2014 Write code"
OPERATOR_PROCESS_TREE_AUDIT_2_HEADING = "#### Process-tree audit #2"
OPERATOR_PHASE_6_HALT_GATE_HEADING = "#### Phase 6 halt-state transition gate"
OPERATOR_PHASE_7_HEADING = "### Phase 7 \u2014 CodeRabbit Loop"


def _repo_root():
    return Path(__file__).resolve().parents[1]


def _workflow_doc_text():
    return (_repo_root() / "workflows" / "implementation-pipeline.md").read_text(
        encoding="utf-8"
    )


def _operator_doc_text():
    return (
        _repo_root() / "agents" / "implementation-pipeline-orchestrator.md"
    ).read_text(encoding="utf-8")


def _section(text, start_heading, end_heading=None):
    assert start_heading in text, f"heading not found: {start_heading!r}"
    start = text.index(start_heading)
    if end_heading is None:
        end = len(text)
    else:
        text_after_start = text[start + len(start_heading) :]
        assert end_heading in text_after_start, (
            f"end heading not found after start: {end_heading!r}"
        )
        end = text.index(end_heading, start + len(start_heading))
    return text[start:end]


def _phase_6_section():
    return _section(_workflow_doc_text(), PHASE_6_HEADING, PHASE_7_HEADING)


def _step_6a_section():
    return _section(_phase_6_section(), STEP_6A_HEADING, STEP_6B_HEADING)


def _step_6b_section():
    return _section(_phase_6_section(), STEP_6B_HEADING, STEP_6C_HEADING)


def _step_6c_section():
    return _section(_phase_6_section(), STEP_6C_HEADING)


def _operator_phase_6_section():
    return _section(_operator_doc_text(), OPERATOR_PHASE_6_HEADING, OPERATOR_PHASE_7_HEADING)


def _operator_step_6c_section():
    return _section(
        _operator_phase_6_section(),
        OPERATOR_STEP_6C_HEADING,
        OPERATOR_PROCESS_TREE_AUDIT_2_HEADING,
    )


def _operator_process_tree_audit_2_section():
    return _section(
        _operator_phase_6_section(),
        OPERATOR_PROCESS_TREE_AUDIT_2_HEADING,
        OPERATOR_PHASE_6_HALT_GATE_HEADING,
    )


def _operator_step_6c_numbered_item(number):
    step_6c = _operator_step_6c_section()
    pattern = rf"(?ms)^{number}\.\s.*?(?=^\d+\.|\n#### |\Z)"
    match = re.search(pattern, step_6c)
    assert match is not None, f"Step 6c is missing numbered step {number}"
    return match.group(0)


def _frontmatter(text):
    parts = text.split("---", 2)
    assert len(parts) == 3, "workflow doc must have YAML frontmatter"
    return parts[1]


def _main_workflow_doc_text():
    for ref in ("master", "origin/master"):
        result = subprocess.run(
            [
                "git",
                "-C",
                str(_repo_root()),
                "show",
                f"{ref}:workflows/implementation-pipeline.md",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            return result.stdout
    raise RuntimeError(
        "Could not read base workflow from 'master' or 'origin/master'. "
        "Ensure the base branch is available."
    )


def _sentence_containing(text, token):
    assert token in text
    index = text.index(token)
    start_candidates = [text.rfind(".", 0, index), text.rfind("\n\n", 0, index)]
    start = max(start_candidates) + 1
    end_candidates = [
        candidate
        for candidate in (text.find(".", index), text.find("\n\n", index))
        if candidate != -1
    ]
    end = min(end_candidates) if end_candidates else len(text)
    return text[start:end]


def _markdown_rule_paragraphs_containing(text, token):
    paragraphs = []
    current = []

    def flush_current():
        if not current:
            return
        paragraph = "\n".join(current)
        if token in paragraph:
            paragraphs.append(paragraph)
        current.clear()

    for line in text.splitlines():
        starts_item = bool(re.match(r"^\s*(?:- |\d+\.\s)", line))
        starts_heading = line.startswith("#")
        blank = not line.strip()
        if starts_item or starts_heading or blank:
            flush_current()
        if blank or starts_heading:
            continue
        current.append(line)
    flush_current()
    return paragraphs


def _assert_token(section, token, section_name):
    assert token in section, f"missing {token!r} in {section_name}"


def _assert_any_token(section, tokens, section_name):
    assert any(token in section for token in tokens), (
        f"missing one of {tokens!r} in {section_name}"
    )


def _assert_regex(section, pattern, section_name, missing):
    assert re.search(pattern, section, flags=re.IGNORECASE | re.DOTALL), (
        f"missing {missing!r} in {section_name}"
    )


def test_step_6a_is_scoped_to_level_outer_contract():
    # Contract row: Step 6a is scoped to level outer contract; reduces behavioral-ambiguity HIGH.
    step_6a = _step_6a_section()

    assert "level outer contract" in step_6a
    assert "internal component contracts" in step_6a
    assert "does not author internal component contracts" in step_6a


def test_step_6b_inputs_reference_the_level_outer_contract():
    # Contract row: Step 6b inputs reference the level outer contract; reduces behavioral-ambiguity HIGH and change-path-entropy MEDIUM.
    step_6b = _step_6b_section()
    inputs_line = next(
        (line for line in step_6b.splitlines() if line.startswith("- Inputs:")),
        None,
    )

    assert inputs_line is not None, "Step 6b is missing an '- Inputs:' line"
    assert "level outer contract" in inputs_line


def test_post_prototype_derivation_rule_is_named():
    # Contract row: Post-prototype derivation rule is named; reduces behavioral-ambiguity HIGH.
    step_6c = _step_6c_section()

    assert "Post-prototype internal contract derivation" in step_6c


def test_internal_contracts_wait_for_passing_prototype():
    # Contract row: Internal contracts wait for passing prototype; reduces behavioral-ambiguity HIGH.
    step_6c = _step_6c_section()

    assert "derive internal component contracts" in step_6c
    evidence_phrase = next(
        (
            phrase
            for phrase in ("passing level prototype", "passes level behavior tests")
            if phrase in step_6c
        ),
        None,
    )
    assert evidence_phrase is not None, "Step 6c is missing passing prototype evidence"
    assert step_6c.index(evidence_phrase) < step_6c.index("derive internal component contracts")


def test_required_derivation_record_fields_present():
    # Contract row: Required derivation-record fields present; reduces coverage-gap HIGH.
    step_6c = _step_6c_section()

    for field in (
        "prototype_evidence_links",
        "accidental_coupling_exclusions",
        "neighbor_claims",
        "rejected_component_candidates",
        "generalization_notes",
        "generalization_probe_refs",
    ):
        assert field in step_6c


def test_process_tree_review_covers_derivation_evidence_when_triggered():
    # Contract row: Derivation evidence is visible to Phase 6 process-tree review; reduces coverage-gap HIGH.
    step_6c = _step_6c_section()
    review_line = next(
        (line for line in step_6c.splitlines() if "Process-tree review" in line),
        None,
    )

    assert review_line is not None, "Step 6c is missing its process-tree review rule"
    assert "derivation trigger fires" in review_line
    assert "derivation record" in review_line
    assert "no-split / rejection subsection" in review_line


def test_conditional_gating_two_trigger_arms():
    # Contract row: Conditional gating two trigger arms; reduces blast-radius HIGH.
    step_6c_lower = _step_6c_section().lower()

    assert "recursive" in step_6c_lower or "component-decomposition" in step_6c_lower
    assert "candidate internal components" in step_6c_lower


def test_conditional_gating_non_triggered_wus_unaffected():
    # Contract row: Conditional gating non-triggered WUs unaffected; reduces blast-radius HIGH.
    step_6c = _step_6c_section()

    assert "no derivation record is required" in step_6c
    assert "Phase 7 proceeds unchanged" in step_6c


def test_symmetric_no_split_termination():
    # Contract row: Symmetric no-split termination; reduces blast-radius HIGH.
    step_6c_lower = _step_6c_section().lower()

    assert "no-split" in step_6c_lower or "no split" in step_6c_lower
    assert "rejection" in step_6c_lower
    assert "subsection" in step_6c_lower


def test_docs_workflow_structural_pytest_carve_out():
    # Contract row: Docs/workflow structural-pytest carve-out; reduces lifecycle-visibility MEDIUM.
    step_6c_lower = _step_6c_section().lower()

    assert "structural pytest" in step_6c_lower or "structural test" in step_6c_lower
    assert "honest test level" in step_6c_lower


def test_derived_contracts_share_existing_artifact_path():
    # Contract row: Derived contracts share existing artifact path; reduces lifecycle-visibility MEDIUM.
    step_6c = _step_6c_section()
    path = "${planning_dir}/contracts/${wu_lower}-${slug}.md"

    assert path in step_6c
    path_index = step_6c.index(path)
    nearby = step_6c[max(0, path_index - 200) : path_index + len(path) + 200].lower()
    assert "subsection" in nearby


def test_probe_content_remains_out_of_scope():
    # Contract row: Probe content remains out of scope; reduces lifecycle-visibility MEDIUM.
    step_6c = _step_6c_section()
    probe_sentence = _sentence_containing(step_6c, "generalization_probe_refs").lower()

    assert "generalization_probe_refs" in probe_sentence
    assert "divergence" in probe_sentence
    for probe_list_marker in (
        "probe steps:",
        "probe step list:",
        "probe cases:",
        "probe scenarios:",
        "probe success criteria:",
    ):
        assert probe_list_marker not in probe_sentence


def test_derivation_occurs_before_phase_7():
    # Contract row: Derivation occurs before Phase 7; reduces change-path-entropy MEDIUM.
    workflow = _workflow_doc_text()

    assert "Post-prototype internal contract derivation" in workflow
    assert workflow.index("Post-prototype internal contract derivation") < workflow.index(
        PHASE_7_HEADING
    )


def test_phase_6_introduction_distinguishes_outer_vs_internal():
    # Contract row: Phase 6 introduction distinguishes outer vs internal; reduces change-path-entropy MEDIUM.
    introduction = _section(_workflow_doc_text(), PHASE_6_HEADING, STEP_6A_HEADING)

    assert "level outer contract" in introduction
    assert (
        "internal component contract" in introduction
        or "internal component contracts" in introduction
    )


def test_current_layer_component_pair_integration_tests_are_derivation_evidence():
    """Risk: AC1/S2/S5 workflow-contract gap. Level: particular-integration. Source: proposal lines 40 and 65."""
    introduction = _section(_workflow_doc_text(), PHASE_6_HEADING, STEP_6A_HEADING)
    step_6c = _step_6c_section()
    phase_6 = _phase_6_section()

    assert re.search(
        r"(?is)\bcurrent[- ]layer\b.{0,180}\bintegration tests?\b.{0,180}"
        r"\b(interactions?|component[- ]pair|interacting component)\b|"
        r"\bintegration tests?\b.{0,180}\b(interactions?|component[- ]pair|interacting component)\b"
        r".{0,180}\bcurrent[- ]layer\b",
        introduction,
    )
    assert "Post-prototype internal contract derivation" in step_6c
    assert "LevelComponentSet" in step_6c
    assert re.search(
        r"(?is)\bLevelComponentSet\b.{0,260}\bintegration_test_refs\b|"
        r"\bintegration_test_refs\b.{0,260}\bLevelComponentSet\b",
        step_6c,
    )
    assert "### Step 6d" not in phase_6


def test_levelcomponentset_integration_test_fields():
    """Risk: AC2/AC3/S5 derivation-record drift. Level: particular-integration. Source: proposal lines 43 and 66."""
    step_6c = _step_6c_section()

    assert "LevelComponentSet" in step_6c
    for field in (
        "layer_level_id",
        "integration_test_refs",
        "coverage_summary",
        "prototype_evidence_links",
        "accidental_coupling_exclusions",
        "neighbor_claims",
        "rejected_component_candidates",
        "generalization_notes",
        "generalization_probe_refs",
    ):
        assert field in step_6c
    assert "component_pair_refs[]" in step_6c or "component_pair_refs" in step_6c
    assert re.search(
        r"(?is)\bcoverage_summary\b.{0,260}\bno interacting pairs\b.{0,260}"
        r"\b(interacting pair|missing test refs?|missing integration)\b|"
        r"\b(interacting pair|missing test refs?|missing integration)\b.{0,260}"
        r"\bno interacting pairs\b.{0,260}\bcoverage_summary\b",
        step_6c,
    )
    assert re.search(
        r"(?is)\bcomponent_pair_refs\[\]\b.{0,260}\baccepted component(?:s| inventory)?\b.{0,260}"
        r"\bneighbor_claims\b|\bneighbor_claims\b.{0,260}\baccepted component(?:s| inventory)?\b.{0,260}"
        r"\bcomponent_pair_refs\[\]\b",
        step_6c,
    )


def test_step_6b_output_index_layer_integration_intent():
    """Risk: AC1/AC3/S4 output-index handoff drift. Level: particular-integration. Source: proposal lines 42 and 67."""
    step_6b = _step_6b_section()
    start_token = "- Output-index fields:"
    end_token = "- Output: `risk/NN-test-residuals.md`"

    assert start_token in step_6b, "Step 6b is missing its output-index field list"
    assert end_token in step_6b, "Step 6b is missing the residuals output after field list"
    field_list = step_6b[
        step_6b.index(start_token) : step_6b.index(end_token, step_6b.index(start_token))
    ]

    assert re.search(
        r"(?is)\bintegration[- ]test(?:\s+intent)?\b.{0,360}"
        r"\bparticular-integration\b.{0,360}\b(layer_level_id|level_id)\b.{0,360}"
        r"\bintegration_test_refs\b|"
        r"\bparticular-integration\b.{0,360}\bintegration[- ]test(?:\s+intent)?\b"
        r".{0,360}\b(layer_level_id|level_id)\b.{0,360}\bintegration_test_refs\b",
        field_list,
    )
    assert re.search(
        r"(?is)\bLevelComponentSet\b.{0,360}\bintegration_test_refs\b|"
        r"\bintegration_test_refs\b.{0,360}\bLevelComponentSet\b",
        field_list,
    )
    for procedural_field in (
        "procedural obligation",
        "Step 6c evidence",
        "emitted procedural test file path",
        "procedural residual entry path",
        "residual class",
    ):
        assert procedural_field in field_list


def test_no_new_workflow_file_path():
    # Contract row: No new workflow file path; reduces scope-risk MEDIUM.
    phase_6 = _phase_6_section()

    for path in (
        "workflows/recursive-systems-design.md",
        "workflows/contract-derivation.md",
        "workflows/prototype-derives-contracts.md",
        "workflows/internal-contract-deriver.md",
    ):
        assert path not in phase_6


def test_no_new_operator():
    # Contract row: No new operator; reduces scope-risk MEDIUM.
    phase_6 = _phase_6_section()

    for path in (
        "agents/contract-deriver.md",
        "agents/prototype-contract-author.md",
        "agents/internal-contract-deriver.md",
    ):
        assert path not in phase_6


def test_phase_6_still_names_three_sub_steps():
    # Contract row: Phase 6 still names three sub-steps; reduces scope-risk MEDIUM.
    phase_6 = _phase_6_section()

    assert phase_6.index(STEP_6A_HEADING) < phase_6.index(STEP_6B_HEADING)
    assert phase_6.index(STEP_6B_HEADING) < phase_6.index(STEP_6C_HEADING)


def test_frontmatter_unchanged():
    # Contract row: Frontmatter unchanged; reduces scope-risk MEDIUM.
    assert _frontmatter(_workflow_doc_text()) == _frontmatter(_main_workflow_doc_text())


def test_operator_step_6c_step_4_detects_both_derivation_triggers():
    # Contract group 1: Step 6c step 8 trigger detection covers both trigger arms.
    step_4 = _operator_step_6c_numbered_item(8)
    section_name = "operator Step 6c numbered step 8"

    _assert_regex(
        step_4,
        r"\bapproved proposal\b.{0,200}\b(recursive|component[- ]decomposition)\b|"
        r"\b(recursive|component[- ]decomposition)\b.{0,200}\bapproved proposal\b",
        section_name,
        "approved proposal recursive/component-decomposition trigger arm",
    )
    _assert_token(step_4, "dedicated recursion-scope section", section_name)
    assert "per-surface mode list" not in step_4
    _assert_regex(
        step_4,
        r"\bcandidate internal components\b.{0,200}\bpassing prototype\b|"
        r"\bpassing prototype\b.{0,200}\bcandidate internal components\b",
        section_name,
        "candidate internal components from passing prototype trigger arm",
    )
    _assert_token(step_4, "no derivation record is required", section_name)
    _assert_token(step_4, "Phase 7 proceeds unchanged", section_name)
    _assert_token(
        step_4,
        "${scratch_dir}/phase6/post-prototype-derivation-status.md",
        section_name,
    )
    _assert_regex(
        step_4,
        r"\brecord(?:ed)?\b.{0,120}\b(no[- ]trigger|neither trigger)\b|"
        r"\b(no[- ]trigger|neither trigger)\b.{0,120}\brecord(?:ed)?\b",
        section_name,
        "recorded no-trigger outcome",
    )


def test_operator_step_6c_step_5_derivation_prompt_is_one_layer_deep():
    # Contract group 2: Step 6c step 9 composes the derivation prompt with one-layer scope.
    step_5 = _operator_step_6c_numbered_item(9)
    section_name = "operator Step 6c numbered step 9"

    _assert_token(
        step_5,
        "${scratch_dir}/prompts/${wu_lower}-phase-6c-derivation.md",
        section_name,
    )
    _assert_token(step_5, "immediate internal components", section_name)
    _assert_token(step_5, "level_id", section_name)
    _assert_regex(step_5, r"\bone[- ]layer[- ]deep\b", section_name, "one layer deep")
    assert "multi-layer" not in step_5.lower(), (
        "operator Step 6c numbered step 9 must not include multi-layer wording"
    )
    for token in (
        "passing prototype evidence",
        "proposal",
        "problem map",
        "hookpoint research",
        "Step 6b output index",
        "existing contract path",
        "${planning_dir}/contracts/${wu_lower}-${slug}.md",
        "writing or replacing the post-prototype subsection",
        "${planning_dir}/risk/${wu_lower}-halt-record.md",
        "${scratch_dir}/phase6/post-prototype-derivation-status.md",
        "superseded",
    ):
        _assert_token(step_5, token, section_name)


def test_operator_step_6c_step_6_dispatches_fresh_derivation_successor():
    # Contract group 3: Step 6c step 10 dispatches a fresh derivation successor.
    step_6 = _operator_step_6c_numbered_item(10)
    section_name = "operator Step 6c numbered step 10"

    for token in (
        "agents -m gpt-high",
        "-p ${worktree_path}",
        "-f ${prompt}",
        "2>&1 | tee ${log}",
        "${scratch_dir}/logs/${wu_lower}-phase-6c-derivation.log",
        "Step 6c successor",
        "not a Step 6b",
        "not Phase 7",
    ):
        _assert_token(step_6, token, section_name)


def test_operator_step_6c_step_7_verifies_derivation_record_fields():
    # Contract group 4: Step 6c step 11 verifies all derivation-record fields.
    step_7 = _operator_step_6c_numbered_item(11)
    section_name = "operator Step 6c numbered step 11"

    _assert_token(
        step_7,
        "${planning_dir}/contracts/${wu_lower}-${slug}.md",
        section_name,
    )
    for field in (
        "prototype_evidence_links",
        "accidental_coupling_exclusions",
        "neighbor_claims",
        "rejected_component_candidates",
        "generalization_notes",
        "generalization_probe_refs",
    ):
        _assert_token(step_7, field, section_name)


def test_operator_step_6c_step_7_verifies_levelcomponentset_fields():
    # Contract group 5: Step 6c step 11 verifies the LevelComponentSet shape.
    step_7 = _operator_step_6c_numbered_item(11)
    section_name = "operator Step 6c numbered step 11"

    _assert_token(step_7, "LevelComponentSet", section_name)
    for field in (
        "layer_level_id",
        "component_pair_refs[]",
        "integration_test_refs",
        "coverage_summary",
    ):
        _assert_token(step_7, field, section_name)


def test_operator_step_6c_step_7_blocks_nested_multilayer_derivation():
    # Contract group 5 supplement: derived contracts stay one current-level layer deep.
    step_7 = _operator_step_6c_numbered_item(11)
    section_name = "operator Step 6c numbered step 11"

    for token in (
        "nested sub-components",
        "grandchild components",
        "multi-layer hierarchy",
        "one layer deep",
    ):
        _assert_token(step_7, token, section_name)


def test_operator_step_6c_step_8_requires_no_split_rejection_evidence():
    # Contract group 6: Step 6c step 12 covers trigger-fired no-split/rejection evidence.
    step_8 = _operator_step_6c_numbered_item(12)
    section_name = "operator Step 6c numbered step 12"

    for token in (
        "trigger fires",
        "no split",
        "rejection",
        "HaltRecord",
        "${planning_dir}/risk/${wu_lower}-halt-record.md",
        "halt_basis",
        "evidence_refs",
        "component_candidates_considered",
        "option-level evidence",
    ):
        _assert_token(step_8, token, section_name)


def test_operator_step_6c_step_9_refuses_phase_7_on_missing_derivation_evidence():
    # Contract group 7: Step 6c step 13 refuses to advance on missing/invalid evidence.
    step_9 = _operator_step_6c_numbered_item(13)
    section_name = "operator Step 6c numbered step 13"

    _assert_regex(
        step_9,
        r"\brefus(?:e|es|al)\b.{0,160}\b(Process-tree audit #2|Phase 7)\b|"
        r"\b(Process-tree audit #2|Phase 7)\b.{0,160}\brefus(?:e|es|al)\b",
        section_name,
        "refusal to advance to Process-tree audit #2 / Phase 7",
    )
    for token in (
        "post-prototype subsection",
        "required derivation-record field token",
        "LevelComponentSet",
        "no-split / rejection branch",
        "multi-layer",
        "component-depth count",
        "multi_layer_derivation_violation",
        "${planning_dir}/audit-history.md",
        "actor=implementation-pipeline-orchestrator",
        "Phase 6",
        "post_prototype_derivation_missing_or_invalid",
        "canonical paths",
        "refused action",
        "failed checks",
        "${scratch_dir}/questions/q-<uuidv4>.question.json",
        "NEEDS_INPUT:<absolute_question_artifact_path>",
        "evidence repair",
        "MUST NOT generate or supply the missing artifact",
    ):
        _assert_token(step_9, token, section_name)


def test_operator_process_tree_audit_2_includes_derivation_manifest_entries():
    # Contract group 8: Process-tree audit #2 can verify produce-side derivation work.
    audit_2 = _operator_process_tree_audit_2_section()
    section_name = "operator Process-tree audit #2"

    _assert_token(audit_2, "derivation successor invocation", section_name)
    _assert_token(
        audit_2,
        "${scratch_dir}/prompts/${wu_lower}-phase-6c-derivation.md",
        section_name,
    )
    _assert_token(
        audit_2,
        "${scratch_dir}/logs/${wu_lower}-phase-6c-derivation.log",
        section_name,
    )
    for token in (
        "${planning_dir}/contracts/${wu_lower}-${slug}.md",
        "LevelComponentSet",
        "no-split / rejection evidence",
        "${scratch_dir}/phase6/post-prototype-derivation-status.md",
        "coexisting live no-trigger status",
        "superseded",
    ):
        _assert_token(audit_2, token, section_name)


def test_workflow_post_prototype_rule_has_no_acr13_deferral_cleanup_phrase():
    # Contract group 9: ACR-13 post-prototype derivation rule has no scoped deferral phrase.
    forbidden = (
        "until that ticket lands, this workflow prohibition is enforced by structural "
        "pytest plus operator review only"
    )
    paragraphs = _markdown_rule_paragraphs_containing(
        _step_6c_section(), "Post-prototype internal contract derivation"
    )

    assert paragraphs, "missing workflow paragraph for post-prototype derivation rule"
    for paragraph in paragraphs:
        assert forbidden not in paragraph, (
            "ACR-13 post-prototype derivation paragraph contains scoped deferral phrase"
        )
