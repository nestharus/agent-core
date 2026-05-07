import subprocess
from pathlib import Path


PHASE_6_HEADING = "## Phase 6 - Implementation (required; test/code separation)"
PHASE_7_HEADING = "## Phase 7 - CodeRabbit Loop"
STEP_6A_HEADING = "### Step 6a - Define contract"
STEP_6B_HEADING = "### Step 6b - Encode tests first"
STEP_6C_HEADING = "### Step 6c - Write code"


def _repo_root():
    return Path(__file__).resolve().parents[1]


def _workflow_doc_text():
    return (_repo_root() / "workflows" / "implementation-pipeline.md").read_text(
        encoding="utf-8"
    )


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
