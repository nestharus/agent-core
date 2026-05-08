import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _orchestrator_text():
    return _read(ORCHESTRATOR)


def _extract_section(text, heading_regex):
    match = re.search(rf"(?m)^(?P<level>##+) {heading_regex}\s*$", text)
    assert match, f"missing section heading matching: {heading_regex}"

    level = match.group("level")
    next_heading = re.search(rf"(?m)^{re.escape(level)} ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _phase6_section():
    return _extract_section(_orchestrator_text(), r"Phase 6 — .*")


def _step6c_section():
    return _extract_section(_phase6_section(), r"Step 6c — Write code")


def _token_window(text, token, *, chars_after):
    assert token in text, f"missing token: {token}"
    start = text.index(token)
    return text[start : start + chars_after]


def test_step6c_prompt_requires_first_log_line_consumed_index():
    """Risk: Coverage gap HIGH. Level: particular-unit. Source: contract §3 behavior 1."""
    section = _step6c_section()

    for token in (
        "FIRST LOG LINE REQUIREMENT",
        "consumed: ${scratch_dir}/phase6/step6b-output-index.md",
        "first non-empty stdout line",
        "before changing product code",
    ):
        assert token in section, f"missing token: {token}"
    block = _token_window(section, "FIRST LOG LINE REQUIREMENT", chars_after=500)
    assert "consumed: ${scratch_dir}/phase6/step6b-output-index.md" in block, (
        "missing token: consumed: ${scratch_dir}/phase6/step6b-output-index.md"
    )


def test_step6c_prompt_requires_consumed_echo_for_each_step6b_test_file():
    """Risk: Behavioral ambiguity MEDIUM. Level: particular-unit. Source: contract §3 behavior 2."""
    section = _step6c_section()

    for token in (
        "each <step6b-test-file>",
        "consumed: <step6b-test-file>",
        "Step 6b test file path",
        "before any product-code change",
    ):
        assert token in section, f"missing token: {token}"


def test_step6c_consumption_echo_is_in_phase6c_prompt_composition():
    """Risk: Blast radius MEDIUM. Level: particular-unit. Source: contract §3 behavior 3."""
    section = _step6c_section()
    composition = _token_window(
        section,
        "Compose `${scratch_dir}/prompts/${wu_lower}-phase-6c.md`",
        chars_after=1200,
    )

    for token in (
        "FIRST LOG LINE REQUIREMENT",
        "Step 6b output index path",
        "test file paths",
        "contract path",
        "proposal path",
        "problem map path",
    ):
        assert token in composition, f"missing token: {token}"


def test_step6c_prompt_preserves_required_pre_change_inputs():
    """Risk: Blast radius MEDIUM. Level: particular-unit. Source: contract §3 behavior 4."""
    section = _step6c_section()

    for token in (
        "Step 6b output index path",
        "test file paths",
        "contract path",
        "proposal path",
        "problem map path",
        "inputs the agent must read before changing product code",
    ):
        assert token in section, f"missing token: {token}"


def test_step6c_prompt_mentions_level_scope_for_recursive_consumption_echo():
    """Risk: Behavioral ambiguity MEDIUM. Level: particular-unit. Source: contract §3 behavior 5."""
    section = _step6c_section()

    for token in (
        "level_id",
        "scoped artifact identifiers",
        "<level_id>:<local_artifact_id>",
    ):
        assert token in section, f"missing token: {token}"


def test_step6c_canonical_token_excludes_legacy_variants():
    """Risk: Duplicate-system count MEDIUM. Level: particular-unit. Source: contract §3 behavior 6."""
    section = _step6c_section()

    for token in (
        "consumed:",
        "consumed: ${scratch_dir}/phase6/step6b-output-index.md",
    ):
        assert token in section, f"missing token: {token}"
    for token in (
        "READ:",
        "CONSUMED_FROM_STEP6B",
        "READ_STEP6B_INDEX",
        "READ_TEST_FILE",
        "consumption-evidence",
    ):
        assert token not in section


def test_step6c_first_log_line_requirement_block_is_co_located_with_consumed():
    """Risk: Brittleness markers MEDIUM. Level: particular-unit. Source: contract §3 behavior 7."""
    section = _step6c_section()

    assert section.count("FIRST LOG LINE REQUIREMENT") == 1
    block = _token_window(section, "FIRST LOG LINE REQUIREMENT", chars_after=500)
    for token in (
        "consumed:",
        "first non-empty stdout line",
    ):
        assert token in block, f"missing token: {token}"
    assert "consumed:" in section, "missing token: consumed:"
    assert "Before any product-code change" in section, (
        "missing token: Before any product-code change"
    )
    assert section.index("consumed:") < section.index("Before any product-code change")


def test_step6c_first_log_line_requirement_appears_in_exactly_one_orchestrator_section():
    """Risk: Change-path entropy MEDIUM. Level: particular-unit. Source: contract §3 behavior 8."""
    orchestrator = _orchestrator_text()
    section = _step6c_section()

    assert orchestrator.count("FIRST LOG LINE REQUIREMENT") == 1
    assert section.count("FIRST LOG LINE REQUIREMENT") == 1
    occurrence = orchestrator.index("FIRST LOG LINE REQUIREMENT")
    step6c_start = orchestrator.index("#### Step 6c — Write code")
    step6c_end = orchestrator.index("#### Process-tree audit #2", step6c_start)
    assert step6c_start <= occurrence < step6c_end
