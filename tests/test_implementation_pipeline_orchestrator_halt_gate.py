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


def _phase6_section():
    return _section(_orchestrator_text(), r"Phase 6 — .*")


def _phase6_halt_gate_section():
    return _section(_phase6_section(), r"Phase 6 halt-state transition gate")


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


def test_phase6_halt_state_gate_exists_and_precedes_phase7():
    orchestrator = _orchestrator_text()
    phase6 = _phase6_section()

    _assert_contains_all(
        phase6,
        (
            "#### Phase 6 halt-state transition gate",
            "Phase 6 evidence-bearing halt rule",
            "#### Process-tree audit #2",
        ),
        where="Phase 6 halt-state transition gate",
    )
    _assert_ordered(
        orchestrator,
        (
            "#### Process-tree audit #2",
            "#### Phase 6 halt-state transition gate",
            "### Phase 7",
        ),
        where="Phase 6 halt-state transition gate before Phase 7",
    )


def test_phase6_halt_gate_names_canonical_path_and_required_field_tokens():
    gate = _phase6_halt_gate_section()

    _assert_contains_all(
        gate,
        (
            "${planning_dir}/risk/${wu_lower}-halt-record.md",
            "halt_basis",
            "component_candidates_considered",
            "evidence_refs",
            "residual_risk_refs",
        ),
        where="Phase 6 halt gate canonical path and required fields",
    )


def test_phase6_halt_gate_names_halt_basis_enum_values():
    gate = _phase6_halt_gate_section()

    _assert_contains_all(
        gate,
        (
            "clarify contracts",
            "reduce accidental coupling",
            "expose a design challenge",
            "improve evidence",
            "lower meaningful risk",
        ),
        where="Phase 6 halt_basis enum values",
    )


def test_phase6_halt_gate_enforces_verdict_resolution_rule():
    gate = _phase6_halt_gate_section()

    _assert_contains_all(
        gate,
        (
            "evidence_refs",
            "Decision Recording entry named",
            "auditor_verdict_conflict_residual",
        ),
        where="Phase 6 halt gate verdict-resolution rule",
    )
    _assert_regex(
        gate,
        r"(?is)\bsplit-or-revise\b.{0,240}\boverlay\b|\boverlay\b.{0,240}\bsplit-or-revise\b",
        "split-or-revise overlay verdict wording",
    )
    _assert_regex(
        gate,
        r"(?is)\bexplicit override evidence\b.{0,160}\bevidence_refs\b"
        r"|\bevidence_refs\b.{0,160}\bexplicit override evidence\b",
        "explicit override evidence in evidence_refs",
    )


def test_phase6_halt_gate_blocks_missing_or_invalid_with_violation_code_and_needs_input():
    gate = _phase6_halt_gate_section()

    _assert_contains_all(
        gate,
        (
            "halt_record_missing_or_invalid",
            "halt_overrules_split_or_revise_by_omission",
            "for step 2-4 failures",
            "for the step 5 verdict-conflict case",
            "NEEDS_INPUT",
            "${scratch_dir}/questions/q-",
            "${planning_dir}/audit-history.md",
            "superseded by a later Phase 6 rerun or process-tree audit",
            "fail to prove currentness for the active WU and level",
            "allow the Phase 6 halt-state transition",
        ),
        where="Phase 6 halt gate violation and NEEDS_INPUT handling",
    )
    _assert_regex(
        gate,
        r"(?is)\b(?:refuse|cannot advance|must not advance)\b.{0,180}\bPhase 6 halt-state transition\b"
        r"|\bPhase 6 halt-state transition\b.{0,180}\b(?:refuse|cannot advance|must not advance)\b"
        r"|\b(?:refuse|cannot advance|must not advance)\b.{0,180}\badvance to Phase 7\b"
        r"|\badvance to Phase 7\b.{0,180}\b(?:refuse|cannot advance|must not advance)\b",
        "refused Phase 6 halt-state transition or advance to Phase 7 wording",
    )


def test_phase6_halt_gate_distinguishes_missing_from_non_applicable():
    gate = _phase6_halt_gate_section()

    _assert_regex(
        gate,
        r"(?is)\bmissing\b.{0,80}\b(?:artifact|file)\b.{0,120}\bnot equivalent\b.{0,120}\bnon-applicability\b"
        r"|\bnot equivalent\b.{0,120}\bnon-applicability\b.{0,120}\bmissing\b.{0,80}\b(?:artifact|file)\b",
        "missing artifact is not equivalent to non-applicability",
    )


def test_phase6_halt_gate_sits_between_audit2_and_phase7_in_whole_file():
    orchestrator = _orchestrator_text()

    _assert_ordered(
        orchestrator,
        (
            "#### Process-tree audit #2",
            "#### Phase 6 halt-state transition gate",
            "halt_record_missing_or_invalid",
            "### Phase 7",
        ),
        where="Phase 6 audit #2 to halt gate to Phase 7 ordering",
    )


def test_halt_gate_test_scope_is_structural_only():
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
    # Split to avoid the source-level assertion matching itself.
    assert ("sub" + "process") not in source
    assert not re.search(r"(?m)^\s*(?:import|from)\s+pytest\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+yaml\b", source)
    assert not re.search(r"(?m)^\s*(?:import|from)\s+.*orchestrator\b", source)
    assert not re.search(r"\bagents\s+(?:-|trace\b|run\b|exec\b)", source)
    assert not re.search(r"(?is)\bopen\([^)]*\$\{planning_dir\}|Path\([^)]*\$\{planning_dir\}", source)
