import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = (
    REPO_ROOT / ("age" + "nts") / "implementation-pipeline-orchestrator.md"
)


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


def _integration_tests_gate_section():
    return _section(_phase7_section(), r"Pre-dispatch integration-tests gate")


def test_integration_tests_gate_section_exists_and_ordered():
    phase7 = _phase7_section()

    _assert_contains_all(
        phase7,
        (
            "#### Pre-dispatch integration-tests gate",
            "#### Pre-dispatch swap-record gate",
        ),
        where="Phase 7 integration-tests gate and swap-record gate",
    )
    _assert_ordered(
        phase7,
        (
            "#### Pre-dispatch integration-tests gate",
            "#### Pre-dispatch swap-record gate",
        ),
        where="Phase 7 integration-tests gate before swap-record gate",
    )


def test_integration_tests_gate_canonical_path():
    gate = _integration_tests_gate_section()

    has_canonical_path = "${planning_dir}/contracts/${wu_lower}-${slug}.md" in gate
    has_contract_subsection_reference = re.search(
        r"(?is)\bLevelComponentSet\b.{0,200}\bpost-prototype\b.{0,200}\b(?:subsection|contract artifact)\b"
        r"|\bpost-prototype\b.{0,200}\bLevelComponentSet\b.{0,200}\b(?:subsection|contract artifact)\b",
        gate,
    )

    assert has_canonical_path or has_contract_subsection_reference, (
        "integration-tests gate must name the canonical contract path or an explicit "
        "post-prototype LevelComponentSet subsection in the contract artifact"
    )


def test_integration_tests_gate_required_field_tokens():
    gate = _integration_tests_gate_section()

    _assert_contains_all(
        gate,
        (
            "layer_level_id",
            "component_pair_refs[]",
            "integration_test_refs",
            "coverage_summary",
        ),
        where="Phase 7 integration-tests gate required field tokens",
    )


def test_integration_tests_gate_coverage_summary_semantics():
    gate = _integration_tests_gate_section()

    _assert_regex(
        gate,
        r"(?is)\bcoverage_summary\b.{0,260}\bno interacting pairs\b.{0,180}\b(?:allow|pass|proceed|continue)\b"
        r"|\bno interacting pairs\b.{0,180}\b(?:allow|pass|proceed|continue)\b.{0,260}\bcoverage_summary\b",
        "coverage_summary no interacting pairs allow path",
    )
    _assert_regex(
        gate,
        r"(?is)\bmissing\b.{0,120}\b(?:test refs|integration coverage)\b.{0,180}\b(?:halt|refuse|NEEDS_INPUT)\b"
        r"|\b(?:halt|refuse|NEEDS_INPUT)\b.{0,180}\bmissing\b.{0,120}\b(?:test refs|integration coverage)\b",
        "missing test refs or missing integration coverage halt path",
    )


def test_integration_tests_gate_per_pair_check():
    gate = _integration_tests_gate_section()

    _assert_regex(
        gate,
        r"(?is)\b(?:for each|each entry|iterate|iterating|iterates)\b.{0,160}\bcomponent_pair_refs\[\]\s+entry\b"
        r".{0,260}\b(?:corresponding|required|covers?|verify|verifies)\b.{0,180}\bintegration_test_refs\b",
        "component_pair_refs[] iteration with corresponding integration_test_refs",
    )
    _assert_regex(
        gate,
        r"(?is)\b(?:per pair|each pair|the pair|listed pair)\b",
        "per-pair coverage wording",
    )


def test_integration_tests_gate_violation_code():
    gate = _integration_tests_gate_section()

    _assert_contains_all(
        gate,
        ("integration_test_missing",),
        where="Phase 7 integration-tests gate violation code",
    )


def test_integration_tests_gate_refused_action():
    gate = _integration_tests_gate_section()

    exact_refusal = "Phase 7 CodeRabbit dispatch" in gate
    close_refusal = re.search(
        r"(?is)\b(?:refuse|refused|cannot|must not)\b.{0,160}\bPhase 7\b.{0,80}\bCodeRabbit\b.{0,80}\bdispatch\b"
        r"|\bPhase 7\b.{0,80}\bCodeRabbit\b.{0,80}\bdispatch\b.{0,160}\b(?:refuse|refused|cannot|must not)\b",
        gate,
    )

    assert exact_refusal or close_refusal, (
        "integration-tests gate must name refused Phase 7 CodeRabbit dispatch"
    )


def test_integration_tests_gate_needs_input_handling():
    gate = _integration_tests_gate_section()

    _assert_contains_all(
        gate,
        (
            "${scratch_dir}/questions/q-",
            "NEEDS_INPUT",
            "${planning_dir}/audit-history.md",
            "actor=implementation-pipeline-orchestrator",
        ),
        where="Phase 7 integration-tests gate NEEDS_INPUT handling",
    )


def test_integration_tests_gate_whole_file_ordering():
    orchestrator = _orchestrator_text()

    _assert_ordered(
        orchestrator,
        (
            "### Phase 7 \u2014 CodeRabbit Loop",
            "#### Pre-dispatch integration-tests gate",
            "integration_test_missing",
            "#### Pre-dispatch swap-record gate",
        ),
        where="whole-file Phase 7 integration-tests gate ordering",
    )


def test_integration_tests_gate_imports_only_re_and_pathlib():
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
    assert not re.search(r"(?m)^\s*(?:import|from)\s+.*(?:sub" + "process)\\b", source)
    assert ("ya" + "ml") not in source
    assert ("age" + "nts") not in source
