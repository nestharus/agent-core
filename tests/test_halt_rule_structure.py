import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
_WORKFLOW_TEXT = None

PHASE_2_5_HEADING = "## Phase 2.5 - Existing-State Risk Profile"
PHASE_3_HEADING = "## Phase 3 - Proposal"
PHASE_4_HEADING = "## Phase 4 - Risk Gates (required; parallel)"
PHASE_6_HEADING = "## Phase 6 - Implementation (required; test/code separation)"
PHASE_7_HEADING = "## Phase 7 - CodeRabbit Loop"
STEP_6C_HEADING = "### Step 6c - Write code"
DECISION_RECORDING_HEADING = "## Decision Recording"
ORCHESTRATOR_HEADING = "## Orchestrator"

HALT_BASIS_OPTIONS = (
    "clarify contracts",
    "reduce accidental coupling",
    "expose a design challenge",
    "improve evidence",
    "lower meaningful risk",
)

HALTRECORD_REQUIRED_FIELDS = (
    "halt_basis",
    "component_candidates_considered",
    "evidence_refs",
    "residual_risk_refs",
)


def _workflow_text():
    global _WORKFLOW_TEXT
    if _WORKFLOW_TEXT is None:
        assert WORKFLOW.exists(), f"workflow file not found: {WORKFLOW}"
        _WORKFLOW_TEXT = WORKFLOW.read_text(encoding="utf-8")
    return _WORKFLOW_TEXT


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


def _phase_2_5_section():
    return _section(_workflow_text(), PHASE_2_5_HEADING, PHASE_3_HEADING)


def _phase_3_section():
    return _section(_workflow_text(), PHASE_3_HEADING, PHASE_4_HEADING)


def _phase_6_section():
    return _section(_workflow_text(), PHASE_6_HEADING, PHASE_7_HEADING)


def _step_6c_section():
    return _section(_phase_6_section(), STEP_6C_HEADING)


def _step_6c_halt_block():
    step_6c = _step_6c_section()
    start_token = "Evidence-bearing halt rule"
    end_token = "Process-tree review"

    assert start_token in step_6c, f"Step 6c missing {start_token!r}"

    start = step_6c.index(start_token)
    assert end_token in step_6c[start:], (
        f"Step 6c missing {end_token!r} after {start_token!r}"
    )
    end = step_6c.index(end_token, start + len(start_token))
    return step_6c[start:end]


def _phase_6_process_tree_review_paragraph():
    step_6c = _step_6c_section()
    lines = step_6c.splitlines()
    for index, line in enumerate(lines):
        if "Process-tree review" in line:
            collected = []
            for following in lines[index:]:
                if collected and re.match(
                    r"^#{1,6}\s|^-\s+Rule:(?!.*Process-tree review)",
                    following,
                ):
                    break
                collected.append(following)
            return "\n".join(collected)
    raise AssertionError("Step 6c is missing its process-tree review paragraph")


def _decision_recording_section():
    return _section(_workflow_text(), DECISION_RECORDING_HEADING, ORCHESTRATOR_HEADING)


def _assert_matches(text, pattern, description):
    assert re.search(pattern, text), f"missing {description}: {pattern}"


def _assert_section_consumes_halt_evidence(section, *, section_name):
    assert re.search(r"(?i)\bHaltRecord\b|\bhalt records?\b", section), (
        f"{section_name} must name HaltRecord or halt records"
    )
    assert re.search(r"(?i)\bresidual\b", section), (
        f"{section_name} must name residual halt evidence"
    )
    _assert_matches(
        section,
        r"(?is)\b(input|inputs|evidence)\b.{0,220}\bhalt\b|"
        r"\bhalt\b.{0,220}\b(input|inputs|evidence)\b",
        f"{section_name} halt evidence as inputs/evidence",
    )
    assert "auditor_verdict_conflict_residual" in section, (
        f"{section_name} must reference auditor_verdict_conflict_residual"
    )


def test_phase_6_halt_rule_named_with_five_halt_basis_options():
    # Risk: Phase 6 halt rule exists. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    halt_block = _step_6c_halt_block()

    _assert_matches(
        halt_block,
        r"(?is)\bhalt(?:s|ed|ing)?\b.{0,140}\blevel\b.{0,220}\bevidence\b|"
        r"\blevel\b.{0,140}\bhalt(?:s|ed|ing)?\b.{0,220}\bevidence\b|"
        r"\bevidence\b.{0,140}\bhalt(?:s|ed|ing)?\b.{0,220}\blevel\b",
        "halt rule tying halt, level, and evidence",
    )
    for basis in HALT_BASIS_OPTIONS:
        assert halt_block.count(basis) == 1, (
            f"halt block must contain {basis!r} exactly once"
        )
    _assert_matches(
        halt_block,
        r"(?is)\bhalts?\b.{0,160}\bnone\b.{0,160}\bhalt_basis\b",
        "halt rule requiring no halt_basis option to earn granularity",
    )
    assert "one or more `halt_basis` options" not in halt_block


def test_haltrecord_required_fields_present():
    # Risk: HaltRecord required fields appear literally. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    halt_block = _step_6c_halt_block()

    assert "HaltRecord" in halt_block
    for field in HALTRECORD_REQUIRED_FIELDS:
        assert field in halt_block


def test_integration_test_missing_violation():
    """Risk: AC4/S6 missing pair coverage silent-skip. Level: particular-integration. Source: proposal lines 44 and 68."""
    halt_block = _step_6c_halt_block()

    assert HALTRECORD_REQUIRED_FIELDS == (
        "halt_basis",
        "component_candidates_considered",
        "evidence_refs",
        "residual_risk_refs",
    )
    assert HALT_BASIS_OPTIONS == (
        "clarify contracts",
        "reduce accidental coupling",
        "expose a design challenge",
        "improve evidence",
        "lower meaningful risk",
    )
    assert "integration_test_missing" in halt_block
    _assert_matches(
        halt_block,
        r"(?is)\b(interacting component pair|component_pair_refs\[\]|component pair)\b"
        r".{0,220}\bintegration_test_refs\b.{0,220}\bintegration_test_missing\b|"
        r"\bintegration_test_missing\b.{0,220}\b(interacting component pair|component_pair_refs\[\]|component pair)\b"
        r".{0,220}\bintegration_test_refs\b",
        "integration_test_missing tied to missing interacting-pair integration refs",
    )
    _assert_matches(
        halt_block,
        r"(?is)\b(not|is not|cannot|must not)\b.{0,140}\b(non-applicability|non applicable|silently skipped|silent skip)\b|"
        r"\b(no-silent-skip|no silent skip)\b",
        "missing integration-test refs are not non-applicability or silent skip",
    )
    _assert_matches(
        halt_block,
        r"(?is)\breplayable\b.{0,180}\b(pair|which pair|component pair)\b.{0,180}"
        r"\b(expected coverage|expected integration coverage|coverage expected)\b|"
        r"\b(pair|which pair|component pair)\b.{0,180}\b(expected coverage|expected integration coverage|coverage expected)\b"
        r".{0,180}\breplayable\b",
        "replayable missing-pair evidence",
    )


def test_component_candidates_considered_required():
    # Risk: component_candidates_considered is required. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    halt_block = _step_6c_halt_block()
    lines = halt_block.splitlines()
    token_lines = [
        index
        for index, line in enumerate(lines)
        if "component_candidates_considered" in line
    ]

    assert token_lines, "halt block must name component_candidates_considered"
    nearby = "\n".join(
        line
        for token_line in token_lines
        for line in lines[max(0, token_line - 5) : min(len(lines), token_line + 6)]
    )
    assert re.search(r"\b(required|must|MUST)\b", nearby), (
        "component_candidates_considered must appear near required language"
    )
    assert re.search(r"\b(rejected|considered|candidate|candidates)\b", nearby), (
        "component_candidates_considered must appear near split-candidate language"
    )


def test_verdict_resolution_rule_named_with_residual_token():
    # Risk: Verdict-resolution rule is named. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    step_6c = _step_6c_section()

    _assert_matches(
        step_6c,
        r"(?i)verdict[- ]resolution|resolution rule",
        "named verdict-resolution rule",
    )
    assert "auditor_verdict_conflict_residual" in step_6c
    _assert_matches(
        step_6c,
        r"(?i)\b(split|revise)\b.{0,80}\bverdict\b|"
        r"\bverdict\b.{0,80}\b(split|revise)\b",
        "split/revise verdict terms in verdict-resolution context",
    )
    _assert_matches(
        step_6c,
        r"(?is)\b(not|cannot|can't|must not)\b.{0,160}"
        r"\b(overrule|override|overrulable|overridable|overrideable)\b.{0,160}"
        r"\b(omission|halt-by-omission|halt by omission)\b|"
        r"\b(omission|halt-by-omission|halt by omission)\b.{0,160}"
        r"\b(not|cannot|can't|must not)\b.{0,160}"
        r"\b(overrule|override|overrulable|overridable|overrideable)\b",
        "split/revise verdict not overrideable by halt-by-omission",
    )
    _assert_matches(
        step_6c,
        r"(?is)\b(cite|cites|citing)\b.{0,160}"
        r"\b(conflicting|conflict)\b.{0,120}\b(overlay )?verdict\b.{0,160}"
        r"\bevidence\b",
        "citation of conflicting overlay verdict and evidence",
    )


def test_phase_2_5_consumes_halt_evidence():
    # Risk: Phase 2.5 consumes halt evidence. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    _assert_section_consumes_halt_evidence(
        _phase_2_5_section(),
        section_name="Phase 2.5",
    )


def test_phase_3_consumes_halt_evidence():
    # Risk: Phase 3 consumes halt evidence. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    _assert_section_consumes_halt_evidence(
        _phase_3_section(),
        section_name="Phase 3",
    )


def test_anti_scope_no_numerical_thresholds_in_halt_paragraph():
    # Risk: Anti-scope guard for numerical thresholds. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    halt_block = _step_6c_halt_block()
    numerical_pattern = re.compile(
        r"(?:[<>]=?\s*\d+(?:\.\d+)?\s*%?)|(?:\d+\s*%)|"
        r"(?:at least\s+\d+)|(?:minimum of\s+\d+)|(?:score of\s+\d+)",
        flags=re.IGNORECASE,
    )

    for basis in HALT_BASIS_OPTIONS:
        assert basis in halt_block
        for match in re.finditer(re.escape(basis), halt_block):
            basis_index = match.start()
            nearby = halt_block[max(0, basis_index - 240) : basis_index + 240]
            assert not numerical_pattern.search(nearby), (
                f"halt basis {basis!r} must not define a numerical threshold"
            )


def test_phase_6_process_tree_review_covers_halt_evidence():
    # Risk: Phase 6 process-tree review covers halt evidence. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    review_paragraph = _phase_6_process_tree_review_paragraph()

    assert re.search(r"(?i)\bHaltRecord\b|\bhalt evidence\b|\bhalt rule\b", review_paragraph)


def test_decision_recording_covers_halt_residuals():
    # Risk: Decision Recording rule covers accepted halt residuals. Level: unit / structural. Source: NES-271 proposal Test-Intent Track.
    section = _decision_recording_section()

    assert re.search(r"(?i)\bhalt\b.{0,80}\bresiduals?\b", section), (
        "Decision Recording must reference halt residuals"
    )
    assert "auditor_verdict_conflict_residual" in section, (
        "Decision Recording must reference auditor_verdict_conflict_residual"
    )
    _assert_matches(
        section,
        r"(?i)\bDECISIONS\.md\b",
        "Decision Recording section must reference DECISIONS.md",
    )
