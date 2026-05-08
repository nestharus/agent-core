"""Structural tests for the ACR-21 risk-assessor operator contract."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "risk-assessor.md"


def _operator_text():
    assert OPERATOR_PATH.exists(), f"risk-assessor operator not found: {OPERATOR_PATH}"
    return OPERATOR_PATH.read_text(encoding="utf-8")


def _section_after_h2(text, heading):
    match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
    if not match:
        return ""

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    return following[: next_h1_or_h2.start()] if next_h1_or_h2 else following


def _persisted_state_section(text):
    return _section_after_h2(text, "Persisted-State Invariant Risk")


def _detailed_assessments_section(text):
    return _section_after_h2(text, "Detailed Assessments")


def _assert_contains_all(text, tokens, *, where):
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{where} missing required tokens/phrases: {missing}"


def _assert_contains_any(text, tokens, *, where):
    assert any(token in text for token in tokens), (
        f"{where} missing one of required tokens/phrases: {tokens}"
    )


def test_01_existing_contract_preservation_tokens_remain_present():
    text = _operator_text()

    _assert_contains_all(
        text,
        (
            "## Priority Summary",
            "P0",
            "P1",
            "P2",
            "P3",
            "P4",
            "R1",
            "R2",
            "R3",
            "R4",
            "V1",
            "V2",
            "V3",
            "## Coverage Enforcement Recommendations",
            "uncovered_areas",
            "worktree_path",
            "coverage_data",
        ),
        where="existing risk-assessor contract",
    )


def test_02_persisted_state_section_and_output_subsection_are_present():
    text = _operator_text()

    _assert_contains_all(
        text,
        (
            "## Persisted-State Invariant Risk",
            "### 1.5. Challenge Persisted-State Invariants",
            "Persisted-state invariant risk:",
        ),
        where="ACR-21 persisted-state section presence",
    )


def test_03_persisted_state_classes_are_named_in_new_section():
    section = _persisted_state_section(_operator_text())
    lower_section = section.lower()

    _assert_contains_all(
        lower_section,
        ("configuration files", "environment variables", "databases"),
        where="persisted-state classes in ## Persisted-State Invariant Risk",
    )
    _assert_contains_any(
        lower_section,
        ("lock files", "cache stores", "state files", "other persisted artifacts"),
        where="other persisted artifact class in ## Persisted-State Invariant Risk",
    )


def test_04_detection_heuristic_categories_are_named_with_examples():
    section = _persisted_state_section(_operator_text())
    lower_section = section.lower()

    _assert_contains_any(
        section,
        ("NOT NULL", "UNIQUE", "CHECK"),
        where="schema-constraint examples in ## Persisted-State Invariant Risk",
    )
    _assert_contains_any(
        section,
        ("Optional", "nullable", "enum", "Literal"),
        where="type-narrowing examples in ## Persisted-State Invariant Risk",
    )
    _assert_contains_any(
        lower_section,
        ("regex", "length", "range"),
        where="validation-rule examples in ## Persisted-State Invariant Risk",
    )
    _assert_contains_any(
        lower_section,
        ("required keys", "required config keys", "required configuration keys"),
        where="config-file shape example in ## Persisted-State Invariant Risk",
    )
    assert "format" in lower_section, (
        "env-var requirement examples in ## Persisted-State Invariant Risk "
        "missing required token/phrase: 'format'"
    )
    _assert_contains_any(
        lower_section,
        ("partial-migration", "non-null backfill", "unique"),
        where="database-constraint examples in ## Persisted-State Invariant Risk",
    )


def test_05_decision_rule_names_old_valid_new_invalid_failure_verbs():
    text = _operator_text()
    verbs = ("reject", "reinterpret", "startup", "corrupt", "drop", "migration")
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    matching_sentences = [
        sentence
        for sentence in sentences
        if sum(verb in sentence.lower() for verb in verbs) >= 4
    ]

    assert matching_sentences, (
        "decision rule missing a sentence with at least four persisted-state "
        f"failure verbs from {verbs}"
    )


def test_06_no_new_invariant_conclusion_requires_negative_justification():
    section = _persisted_state_section(_operator_text())
    lower_section = section.lower()

    has_required_justification = "categories were checked" in lower_section or (
        "no new invariant" in lower_section and "why each is absent" in lower_section
    )
    assert has_required_justification, (
        "no-new-invariant rule missing required wording: "
        "'categories were checked' or 'no new invariant' with 'why each is absent'"
    )


def test_07_empty_context_rule_requires_scan_before_no_context_outcome():
    section = _persisted_state_section(_operator_text())
    lower_section = section.lower()

    assert "scan" in lower_section or "scans" in lower_section, (
        "empty-context rule missing required scan/scans wording"
    )
    assert "no new-invariant context was supplied" in lower_section, (
        "empty-context rule missing required phrase: "
        "'no new-invariant context was supplied'"
    )
    assert "sufficient" in lower_section, (
        "empty-context rule missing required insufficiency wording for bare "
        "'no new-invariant context was supplied'"
    )


def test_08_per_invariant_output_fields_are_documented():
    text = _operator_text()

    _assert_contains_all(
        text,
        (
            "invariant_description",
            "persisted_state_classes_examined",
            "existing_state_violations",
            "broken_invariant_test_refs",
            "migration_path",
            "breakage_acceptance_decision",
        ),
        where="ACR-21 per-invariant output fields",
    )


def test_09_sentinel_values_require_parallel_evidence_records():
    section = _persisted_state_section(_operator_text())

    _assert_contains_all(
        section,
        ("surfaces searched", "signals checked"),
        where="sentinel-with-evidence requirement",
    )


def test_10_breakage_acceptance_decision_requires_citation():
    section = _persisted_state_section(_operator_text()).lower()

    _assert_contains_all(
        section,
        ("must cite", "unattributed"),
        where="breakage_acceptance_decision citation rule",
    )


def test_11_sub_investigation_contract_is_read_only_and_names_file_globs():
    section = _persisted_state_section(_operator_text()).lower()
    read_only_tokens = (
        "no writes",
        "no migrations",
        "no schema mutations",
        "no env-var changes",
        "no fixture rewrites",
        "no generated-artifact regeneration",
    )
    present_read_only_tokens = [
        token for token in read_only_tokens if token in section
    ]

    assert len(present_read_only_tokens) >= 3, (
        "read-only sub-investigation contract missing at least three explicit "
        f"tokens from {read_only_tokens}; found {present_read_only_tokens}"
    )
    _assert_contains_any(
        section,
        ("*.toml", "*.yaml", "*.yml", "*.json"),
        where="sub-investigation config-file globs",
    )


def test_12_persisted_state_findings_integrate_with_existing_rv_scoring():
    section = _persisted_state_section(_operator_text())
    lower_section = section.lower()
    mentions_rv_tokens = all(token in section for token in ("R1", "R2", "R3", "R4"))
    mentions_v_tokens = all(token in section for token in ("V1", "V2", "V3"))
    mentions_existing_scoring = (
        "existing risk dimensions" in lower_section
        or "existing r/v scoring" in lower_section
    )

    assert mentions_rv_tokens or mentions_v_tokens or mentions_existing_scoring, (
        "R/V integration rule missing required reference to R1-R4, V1-V3, "
        "'existing risk dimensions', or 'existing R/V scoring'"
    )
