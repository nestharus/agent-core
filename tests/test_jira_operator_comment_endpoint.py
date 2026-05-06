import re

import pytest


CANONICAL_ENDPOINT = "POST /rest/api/3/issue/{issueIdOrKey}/comment"
RUNNABLE_V3_URL = "${jira_url}/rest/api/3/issue/$ISSUE_KEY/comment"
V2_SINGULAR_FALLBACK = "POST /rest/api/2/issue/{issueIdOrKey}/comment"
V2_PLURAL_BAD_PATH = "/rest/api/2/issue/{issueIdOrKey}/comments"
V3_PLURAL_BAD_ENDPOINT = "POST /rest/api/3/issue/{issueIdOrKey}/comments"
RUNNABLE_PLURAL_BAD_URL = "${jira_url}/rest/api/3/issue/$ISSUE_KEY/comments"


def _markdown_units(block):
    units = []
    current = []

    def flush():
        if current:
            units.append(" ".join(current))
            current.clear()

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            flush()
            continue
        if re.match(r"^[-*]\s+", stripped):
            flush()
        current.append(stripped)

    flush()
    return units


def _unit_with(block, *needles):
    lowered_needles = [needle.lower() for needle in needles]
    for unit in _markdown_units(block):
        lowered_unit = unit.lower()
        if all(needle in lowered_unit for needle in lowered_needles):
            return unit
    raise AssertionError(f"missing markdown unit containing: {', '.join(needles)}")


def _complete_endpoint_pattern(endpoint):
    method, path = endpoint.split(" ", 1)
    return re.compile(rf"{re.escape(method)}\s+{re.escape(path)}(?!\w)", re.IGNORECASE)


def _unit_with_complete_endpoint(block, endpoint):
    pattern = _complete_endpoint_pattern(endpoint)
    for unit in _markdown_units(block):
        if pattern.search(unit):
            return unit
    raise AssertionError(f"missing complete-token endpoint: {endpoint}")


def _non_support_marker_pattern():
    return re.compile(
        r"non[- ]supported|unsupported|forbidden|never|not\s+used|must\s+not|do\s+not",
        re.IGNORECASE,
    )


def _assert_canonical_endpoint_pinned(block):
    unit = _unit_with_complete_endpoint(block, CANONICAL_ENDPOINT)
    assert re.search(r"\bcanonical\b", unit, re.IGNORECASE), (
        "canonical v3 endpoint must be labeled canonical in the same paragraph or list item"
    )


def _assert_runnable_curl_uses_v3_singular_default(block):
    assert RUNNABLE_V3_URL in block
    assert RUNNABLE_PLURAL_BAD_URL not in block


def _assert_v2_singular_fallback_named(block):
    unit = _unit_with_complete_endpoint(block, V2_SINGULAR_FALLBACK)
    assert re.search(r"\bsingular\b|\(v2\s*\+\s*singular\)", unit, re.IGNORECASE), (
        "v2 fallback must be labeled as singular adjacent to the endpoint"
    )
    assert V2_PLURAL_BAD_PATH not in unit or _non_support_marker_pattern().search(unit), (
        "v2 plural path must not be presented as the fallback"
    )


def _assert_fallback_precondition_defined(block):
    for unit in _markdown_units(block):
        if not re.search(r"\bfallback\b", unit, re.IGNORECASE):
            continue
        if "404" not in unit or not re.search(r"\bbody\b", unit, re.IGNORECASE):
            continue
        if re.search(
            r"No endpoint POST|missing endpoint|unavailable|endpoint is missing",
            unit,
            re.IGNORECASE,
        ):
            return
    raise AssertionError(
        "fallback rule must require 404, response-body confirmation, "
        "and a missing-endpoint indicator"
    )


def _assert_silent_404_rejected(block):
    for unit in _markdown_units(block):
        if not re.search(r"\bfallback\b", unit, re.IGNORECASE):
            continue
        if not re.search(r"\bsilent\b|\bgeneric\b", unit, re.IGNORECASE):
            continue
        if re.search(r"\bnot\b|must\s+not|do\s+not|does\s+not", unit, re.IGNORECASE):
            return
    raise AssertionError("fallback paragraph must reject silent or generic 404 fallback")


def _assert_plural_path_non_supported(block):
    unit = _unit_with(block, V2_PLURAL_BAD_PATH)
    assert "/comments" in unit
    assert _non_support_marker_pattern().search(unit), (
        "observed plural comment path must be marked non-supported"
    )


def _assert_failure_surface_requires_verbatim_evidence(block):
    unit = _unit_with(block, "BLOCKED")
    for required in ("verbatim", "HTTP status", "body"):
        assert re.search(re.escape(required), unit, re.IGNORECASE), (
            f"BLOCKED failure surface must include {required}"
        )


def _assert_no_known_bad_endpoint_selection(block):
    assert RUNNABLE_PLURAL_BAD_URL not in block

    marker = _non_support_marker_pattern()
    for unit in _markdown_units(block):
        lowered = unit.lower()
        if V3_PLURAL_BAD_ENDPOINT.lower() in lowered:
            assert marker.search(unit), "v3 plural /comments must not be supported"
        if "/comments" in lowered and "canonical" in lowered:
            assert marker.search(unit), "plural /comments must not be canonical"
        if V2_PLURAL_BAD_PATH.lower() in lowered and "fallback" in lowered:
            assert marker.search(unit), "v2 plural /comments must not be fallback"


def _canonical_path_becomes_plural(block):
    return block.replace(CANONICAL_ENDPOINT, V3_PLURAL_BAD_ENDPOINT)


def _drop_canonical_label(block):
    return re.sub(r"\bcanonical\b", "primary", block, flags=re.IGNORECASE)


def _runnable_default_becomes_plural(block):
    return block.replace(RUNNABLE_V3_URL, RUNNABLE_PLURAL_BAD_URL)


def _fallback_path_becomes_v2_plural(block):
    return block.replace(V2_SINGULAR_FALLBACK, f"POST {V2_PLURAL_BAD_PATH}")


def _drop_body_confirmation(block):
    return re.sub(r"\bbody\b", "response", block, flags=re.IGNORECASE)


def _drop_non_support_label(block):
    mutated = block
    replacements = (
        r"non[- ]supported",
        r"unsupported",
        r"forbidden",
        r"never",
        r"not\s+used",
        r"must\s+not",
        r"do\s+not",
    )
    for pattern in replacements:
        mutated = re.sub(pattern, "supported", mutated, flags=re.IGNORECASE)
    return mutated


def _drop_verbatim_failure_evidence(block):
    return re.sub(r"\bverbatim\b", "summarized", block, flags=re.IGNORECASE)


def test_comment_procedure_pins_canonical_v3_comment_endpoint(comment_procedure_block):
    """Risk annotation: Canonical endpoint pin; Coverage gap HIGH; T1 -> A2 from proposal."""
    _assert_canonical_endpoint_pinned(comment_procedure_block)


def test_comment_procedure_preserves_v3_singular_runnable_curl(comment_procedure_block):
    """Risk annotation: Singular default path; Coverage gap HIGH; T2 -> A2/A5 from proposal."""
    _assert_runnable_curl_uses_v3_singular_default(comment_procedure_block)


def test_comment_procedure_names_v2_singular_fallback(comment_procedure_block):
    """Risk annotation: Narrow v2 singular fallback; Behavioral ambiguity MEDIUM; T3 -> A3 from proposal."""
    _assert_v2_singular_fallback_named(comment_procedure_block)


def test_comment_procedure_requires_body_confirmed_404_for_fallback(comment_procedure_block):
    """Risk annotation: Fallback precondition; Behavioral ambiguity MEDIUM; T4 -> A3/A4 from proposal."""
    _assert_fallback_precondition_defined(comment_procedure_block)


def test_comment_procedure_rejects_silent_or_generic_404_fallback(comment_procedure_block):
    """Risk annotation: Silent 404 rejection; Behavioral ambiguity MEDIUM; T5 -> A4 from proposal."""
    _assert_silent_404_rejected(comment_procedure_block)


def test_comment_procedure_marks_plural_comments_path_non_supported(comment_procedure_block):
    """Risk annotation: Plural path non-support; Coverage gap HIGH; T6 -> A5 from proposal."""
    _assert_plural_path_non_supported(comment_procedure_block)


def test_comment_procedure_blocks_with_verbatim_evidence_when_attempts_fail(
    comment_procedure_block,
):
    """Risk annotation: Failure surface; Coverage gap HIGH; T7 -> A3/A4 from proposal."""
    _assert_failure_surface_requires_verbatim_evidence(comment_procedure_block)


def test_comment_procedure_links_endpoint_rationale_evidence(comment_procedure_block):
    """Risk annotation: Evidence cross-link; Coverage gap HIGH; T8 -> A1 from proposal."""
    for required in (
        "~/work/rfqautomation-linux/DECISIONS.md",
        "`jira-operator` hardening note (no ticket)",
        "INFA-141",
        "17120",
        "17623",
        "2026-05-05",
    ):
        assert required in comment_procedure_block


def test_endpoint_selection_contract_stays_out_of_unrelated_procedures(
    jira_operator_section,
):
    """Risk annotation: Scope containment; Blast radius MEDIUM; T9 -> A1 from proposal."""
    for heading in (
        "## Procedure: Read",
        "## Procedure: Transition",
        "## Procedure: Create",
        "## Procedure: Search (JQL)",
    ):
        block = jira_operator_section(heading)
        assert not re.search(
            r"\bcanonical\b|\bfallback\b|non[- ]supported|/comments",
            block,
            re.IGNORECASE,
        )


@pytest.mark.parametrize(
    ("case_name", "mutator", "assertion"),
    (
        (
            "v3_plural_canonical",
            _canonical_path_becomes_plural,
            _assert_canonical_endpoint_pinned,
        ),
        ("missing_canonical_label", _drop_canonical_label, _assert_canonical_endpoint_pinned),
        (
            "plural_runnable_default",
            _runnable_default_becomes_plural,
            _assert_runnable_curl_uses_v3_singular_default,
        ),
        (
            "v2_plural_fallback",
            _fallback_path_becomes_v2_plural,
            _assert_v2_singular_fallback_named,
        ),
        (
            "missing_body_confirmation",
            _drop_body_confirmation,
            _assert_fallback_precondition_defined,
        ),
        (
            "plural_no_longer_non_supported",
            _drop_non_support_label,
            _assert_plural_path_non_supported,
        ),
        (
            "missing_verbatim_failure_evidence",
            _drop_verbatim_failure_evidence,
            _assert_failure_surface_requires_verbatim_evidence,
        ),
    ),
)
def test_endpoint_contract_assertions_reject_common_mutations(
    comment_procedure_block,
    case_name,
    mutator,
    assertion,
):
    """Risk annotation: Exhaustive negative/mutation guard; Coverage gap HIGH; T10 -> A6 from proposal."""
    _assert_no_known_bad_endpoint_selection(comment_procedure_block)
    assertion(comment_procedure_block)

    mutated = mutator(comment_procedure_block)
    assert mutated != comment_procedure_block, f"mutation did not change block: {case_name}"
    with pytest.raises(AssertionError):
        assertion(mutated)
