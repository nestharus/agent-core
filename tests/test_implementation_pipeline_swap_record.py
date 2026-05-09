import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"

CANONICAL_SWAP_RECORD_PATH = "${planning_dir}/risk/${wu_lower}-prototype-swap-record.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _workflow_text():
    return _read(WORKFLOW)


def _assert_contains_all(text, phrases, *, where):
    missing = [phrase for phrase in phrases if phrase not in text]
    assert missing == [], f"{where} missing required text: {missing}"


def _assert_regex(text, pattern, description):
    assert re.search(pattern, text), f"missing {description}: {pattern}"


def _assert_not_regex(text, pattern, description):
    assert not re.search(pattern, text), f"unexpected {description}: {pattern}"


def _assert_ordered(text, phrases, *, where):
    cursor = 0
    for phrase in phrases:
        index = text.find(phrase, cursor)
        assert index != -1, f"{where} missing ordered text after offset {cursor}: {phrase}"
        cursor = index + len(phrase)


def _assert_ordered_regex(text, patterns, *, where):
    cursor = 0
    for pattern in patterns:
        match = re.search(pattern, text[cursor:])
        assert match, f"{where} missing ordered pattern after offset {cursor}: {pattern}"
        cursor += match.end()


def _step6c_process_tree_review_match(text):
    match = re.search(
        r"(?is)- Rule: Process-tree review: after Step 6c completes.*?`rerun or repaired`",
        text,
    )
    assert match, "missing Step 6c process-tree review anchor"
    return match


def _phase7_heading_match(text):
    match = re.search(r"(?m)^## Phase 7\s+[-\u2014]\s+CodeRabbit Loop\s*$", text)
    assert match, "missing Phase 7 CodeRabbit heading"
    return match


def _boundary_rule(text):
    review = _step6c_process_tree_review_match(text)
    phase7 = _phase7_heading_match(text)
    assert review.end() < phase7.start(), "Step 6c process-tree review must precede Phase 7"
    return text[review.end() : phase7.start()]


def test_swap_record_rule_sits_between_step6c_review_and_phase7():
    workflow = _workflow_text()
    boundary = _boundary_rule(workflow)

    _assert_regex(
        boundary,
        r"\bPrototypeSwapRecord\b",
        "PrototypeSwapRecord boundary rule between Step 6c review and Phase 7",
    )
    _assert_ordered_regex(
        workflow,
        (
            r"Process-tree review: after Step 6c completes",
            r"PrototypeSwapRecord",
            r"(?m)^## Phase 7\s+[-\u2014]\s+CodeRabbit Loop\s*$",
        ),
        where="swap-record boundary placement",
    )
    _assert_not_regex(boundary, r"(?m)^###\s+Step\s+6d\b", "Step 6d subsection")


def test_swap_record_requires_required_field_tokens():
    boundary = _boundary_rule(_workflow_text())

    _assert_contains_all(
        boundary,
        (
            "component_refs",
            "component_test_results",
            "procedural_test_results",
            "level_behavior_test_results",
            "removed_or_retired_refs",
            "audit_overlay_refs",
            "level_id",
            "prototype_ref",
        ),
        where="PrototypeSwapRecord required field set",
    )
    _assert_regex(
        boundary,
        r"(?is)(?:level_id|prototype_ref).{0,240}(?:additional|in addition to|on top of|not replacements? for).{0,240}(?:six|ticket)"
        r"|(?:additional|in addition to|on top of|not replacements? for).{0,240}(?:six|ticket).{0,240}(?:level_id|prototype_ref)",
        "identity fields as additive to the six ticket fields",
    )
    _assert_regex(boundary, r"(?is)\bartifact path\b", "audit overlay artifact path")
    _assert_regex(boundary, r"(?is)\bverdict\b|\bcurrentness\b", "audit overlay verdict/currentness evidence")
    _assert_regex(
        boundary,
        r"(?is)swapped component inventory|swapped components",
        "audit overlay applicability to swapped components",
    )


def test_same_layer_integration_evidence_stays_upstream_of_swap_record():
    """Risk: S7 swap-boundary conflation. Level: particular-integration. Source: proposal lines 45 and 70."""
    boundary = _boundary_rule(_workflow_text())

    _assert_contains_all(
        boundary,
        (
            "PrototypeSwapRecord",
            "component_test_results",
            "procedural_test_results",
            "level_behavior_test_results",
        ),
        where="PrototypeSwapRecord preserved fields with integration boundary pointer",
    )
    _assert_regex(
        boundary,
        r"(?is)(same[- ]layer|current[- ]layer).{0,180}"
        r"(component[- ]pair|pairwise).{0,180}integration[- ]test evidence|"
        r"integration[- ]test evidence.{0,180}(same[- ]layer|current[- ]layer).{0,180}"
        r"(component[- ]pair|pairwise)",
        "same-layer component-pair integration-test evidence",
    )
    _assert_regex(
        boundary,
        r"(?is)integration[- ]test evidence.{0,220}(upstream|before swap readiness|consumed before)|"
        r"(upstream|before swap readiness|consumed before).{0,220}integration[- ]test evidence",
        "integration-test evidence consumed upstream of swap readiness",
    )
    _assert_regex(
        boundary,
        r"(?is)(distinct from|not folded into|not a replacement for|not folded into)"
        r".{0,220}(component_test_results|procedural_test_results|level_behavior_test_results)",
        "integration-test evidence distinct from swap result fields",
    )
    assert "integration_test_results" not in boundary


def test_swap_record_blocks_phase7_without_record_or_non_applicability():
    boundary = _boundary_rule(_workflow_text())

    _assert_regex(
        boundary,
        r"(?is)(Phase 7|CodeRabbit).{0,240}(diff|consume|consumption|advance)",
        "Phase 7 or CodeRabbit diff-consumption boundary",
    )
    _assert_regex(
        boundary,
        r"(?is)(PrototypeSwapRecord|swap record).{0,240}(explicit non-applicability|non-applicability statement)"
        r"|(?:explicit non-applicability|non-applicability statement).{0,240}(PrototypeSwapRecord|swap record)",
        "swap record or explicit non-applicability requirement",
    )
    _assert_regex(
        boundary,
        r"(?is)implementation-pipeline orchestrator|Phase 7 dispatch",
        "enforcement actor",
    )
    _assert_regex(
        boundary,
        r"(?is)\brefuse\b|cannot consume|cannot advance",
        "refused Phase 7 action",
    )
    _assert_contains_all(
        boundary,
        (
            "consumed",
            "non-applicable",
            "superseded",
            CANONICAL_SWAP_RECORD_PATH,
        ),
        where="swap-record no-bypass required tokens",
    )
    _assert_regex(
        boundary,
        r"(?is)supported[- ]surface.{0,160}(retained prototype paths?|escape clause|exception)"
        r"|retained prototype paths?.{0,160}supported[- ]surface",
        "supported-surface escape clause for retained prototype paths",
    )


def test_swap_record_test_scope_is_workflow_boundary_only():
    source = Path(__file__).read_text(encoding="utf-8")
    boundary = _boundary_rule(_workflow_text())
    import_lines = [
        line
        for line in source.splitlines()
        if re.match(r"^\s*(?:import|from)\s+", line)
    ]

    assert import_lines == ["import re", "from pathlib import Path"]
    _assert_not_regex(source, r"(?m)^\s*import\s+pytest\b|^\s*from\s+pytest\b", "pytest import")
    _assert_not_regex(source, r"(?m)^\s*import\s+yaml\b|^\s*from\s+yaml\b", "yaml import")
    _assert_not_regex(
        source,
        r"(?m)^\s*import\s+.*orchestrator|^\s*from\s+.*orchestrator",
        "orchestrator import",
    )
    _assert_regex(boundary, r"(?is)(no|forbid|forbids|must not|do not).{0,120}new operators?", "no new operators")
    _assert_regex(
        boundary,
        r"(?is)(no|forbid|forbids|must not|do not).{0,120}new workflow file",
        "no new workflow file",
    )
    _assert_regex(
        boundary,
        r"(?is)(overlay scheduling.{0,120}NES-270|NES-270.{0,120}overlay scheduling)",
        "overlay scheduling deferred to sibling NES-270",
    )
    _assert_not_regex(
        boundary,
        r"(?is)(orchestrator-runtime|runtime enforcement|runtime refusal).{0,220}NES-273",
        "stale orchestrator-runtime NES-273 deferral framing",
    )
    _assert_not_regex(
        boundary,
        r"(?is)structural pytest plus operator review only",
        "stale 'structural pytest plus operator review only' deferral phrase",
    )
    _assert_not_regex(
        boundary,
        r"(?is)until\s+NES-273\s+lands",
        "stale 'until NES-273 lands' deferral phrase",
    )
    _assert_regex(
        boundary,
        r"(?is)Pre[- ]dispatch\s+swap[- ]record\s+gate",
        "operator-file pre-dispatch swap-record gate cited from workflow rule",
    )
    _assert_regex(
        boundary,
        r"(?is)implementation-pipeline-orchestrator\.md",
        "operator-file path cited from workflow rule",
    )


def test_retained_prototype_paths_require_supported_surface_escape_clause():
    workflow = _workflow_text()
    boundary = _boundary_rule(workflow)

    _assert_regex(
        boundary,
        r"(?is)(retained prototype paths?|parallel prototype code).{0,180}(cannot|must not|forbid|forbids).{0,180}shadow implementation"
        r"|shadow implementation.{0,180}(cannot|must not|forbid|forbids)",
        "retained prototypes cannot remain as shadow implementation",
    )
    _assert_regex(
        boundary,
        r"(?is)supported[- ]surface.{0,180}(only|escape clause|exception)"
        r"|(only|escape clause|exception).{0,180}supported[- ]surface",
        "supported-surface naming as only retained-prototype escape clause",
    )
    _assert_contains_all(boundary, ("removed_or_retired_refs",), where="retained prototype policy")
    _assert_ordered_regex(
        workflow,
        (
            r"Process-tree review: after Step 6c completes",
            r"PrototypeSwapRecord",
            r"(?m)^## Phase 7\s+[-\u2014]\s+CodeRabbit Loop\s*$",
        ),
        where="retained-prototype policy placement",
    )
