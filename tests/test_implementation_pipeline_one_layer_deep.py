import re
from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / "workflows" / "implementation-pipeline.md"
)

PHASE_6_HEADING = "## Phase 6 - Implementation (required; test/code separation)"
PHASE_7_HEADING = "## Phase 7 - CodeRabbit Loop"
STEP_6A_HEADING = "### Step 6a - Define contract"
STEP_6B_HEADING = "### Step 6b - Encode tests first"
STEP_6C_HEADING = "### Step 6c - Write code"
DEPTH_PHRASE = "precisely one layer deep at the current recursion level"
MULTI_LAYER_VIOLATION = "multi_layer_derivation_violation"

HALT_BASIS_OPTIONS = {
    "clarify contracts",
    "reduce accidental coupling",
    "expose a design challenge",
    "improve evidence",
    "lower meaningful risk",
}

HALTRECORD_REQUIRED_FIELDS = {
    "halt_basis",
    "component_candidates_considered",
    "evidence_refs",
    "residual_risk_refs",
}

_WORKFLOW_TEXT = None


def _load_workflow_text():
    global _WORKFLOW_TEXT
    if _WORKFLOW_TEXT is None:
        assert WORKFLOW_PATH.exists(), f"workflow file not found: {WORKFLOW_PATH}"
        _WORKFLOW_TEXT = WORKFLOW_PATH.read_text(encoding="utf-8")
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


def _phase_6_section(text):
    return _section(text, PHASE_6_HEADING, PHASE_7_HEADING)


def _step_6c_section(text):
    return _section(_phase_6_section(text), STEP_6C_HEADING)


def _line_window_containing(text, token, *, before=8, after=20):
    lines = text.splitlines()
    token_line = next(
        (index for index, line in enumerate(lines) if token in line),
        None,
    )
    assert token_line is not None, f"missing depth-rule anchor: {token!r}"
    return "\n".join(
        lines[max(0, token_line - before) : min(len(lines), token_line + after + 1)]
    )


def _step_6c_depth_region(text):
    step_6c = _step_6c_section(text)
    start_token = "Post-prototype internal contract derivation"
    end_token = "Evidence-bearing halt rule"

    assert start_token in step_6c, f"Step 6c missing {start_token!r}"
    start = step_6c.index(start_token)
    end = step_6c.index(end_token, start) if end_token in step_6c[start:] else len(step_6c)
    derivation_region = step_6c[start:end]
    if DEPTH_PHRASE in derivation_region:
        return _line_window_containing(derivation_region, DEPTH_PHRASE)
    return derivation_region


def _step_6c_halt_block(text):
    step_6c = _step_6c_section(text)
    start_token = "Evidence-bearing halt rule"
    end_token = "Process-tree review"

    assert start_token in step_6c, f"Step 6c missing {start_token!r}"
    start = step_6c.index(start_token)
    assert end_token in step_6c[start:], (
        f"Step 6c missing {end_token!r} after {start_token!r}"
    )
    end = step_6c.index(end_token, start + len(start_token))
    return step_6c[start:end]


def _assert_contains_any(text, tokens, *, where):
    assert any(token in text for token in tokens), (
        f"{where} missing one of required tokens: {tokens}"
    )


def _assert_token_near_any(text, anchor, tokens, *, max_lines=20, where):
    lines = text.splitlines()
    anchor_lines = [index for index, line in enumerate(lines) if anchor in line]
    assert anchor_lines, f"{where} missing anchor token: {anchor!r}"

    for token in tokens:
        token_lines = [index for index, line in enumerate(lines) if token in line]
        if any(
            abs(anchor_line - token_line) <= max_lines
            for anchor_line in anchor_lines
            for token_line in token_lines
        ):
            return
    raise AssertionError(
        f"{where} missing {tokens!r} within {max_lines} lines of {anchor!r}"
    )


def _assert_regex_near(text, anchor, pattern, *, max_lines=20, where):
    window = _line_window_containing(text, anchor, before=max_lines, after=max_lines)
    assert re.search(pattern, window), f"{where} missing nearby pattern: {pattern}"


def _halt_basis_options(text):
    halt_block = _step_6c_halt_block(text)
    match = re.search(
        r"`halt_basis` options:\s*(?P<options>.*?)\.\s+The `halt_basis` field",
        halt_block,
        flags=re.S,
    )
    assert match, "could not parse halt_basis options from Step 6c halt block"
    return set(re.findall(r"`([^`]+)`", match.group("options")))


def _haltrecord_required_fields(text):
    halt_block = _step_6c_halt_block(text)
    match = re.search(
        r"`HaltRecord` required fields are\s*(?P<fields>.*?)\.",
        halt_block,
        flags=re.S,
    )
    assert match, "could not parse HaltRecord required fields from Step 6c halt block"
    return set(re.findall(r"`([^`]+)`", match.group("fields")))


def test_step_6c_declares_one_layer_current_level_derivation():
    """Risk: T1. Level: structural pytest. Source: NES-280 proposal T1 and A2/A4."""
    step_6c = _step_6c_section(_load_workflow_text())

    assert DEPTH_PHRASE in step_6c
    _assert_token_near_any(
        step_6c,
        DEPTH_PHRASE,
        ("immediate internal components", "immediate components"),
        max_lines=20,
        where="Step 6c one-layer derivation rule",
    )


def test_step_6c_forbids_nested_subcomponents_in_single_derivation_pass():
    """Risk: T2. Level: structural pytest. Source: NES-280 proposal T2 and A2/A4."""
    depth_region = _step_6c_depth_region(_load_workflow_text())

    _assert_contains_any(
        depth_region,
        ("nested sub-components", "grandchild components", "multi-layer"),
        where="Step 6c depth-rule region",
    )
    _assert_contains_any(
        depth_region,
        ("single derivation pass", "same derivation pass", "one derivation pass"),
        where="Step 6c depth-rule region",
    )


def test_deeper_decomposition_routes_through_recursive_child_level():
    """Risk: T3. Level: structural pytest. Source: NES-280 proposal T3 and A1/A2."""
    workflow = _load_workflow_text()
    depth_region = _step_6c_depth_region(workflow)
    phase_6 = _phase_6_section(workflow)

    _assert_contains_any(
        depth_region,
        ("recursive child entry", "recursive Phase 6 reuse"),
        where="Step 6c depth-rule region",
    )
    assert "level_id" in depth_region
    assert re.search(r"(?m)^### Step 6d\b", phase_6) is None
    assert phase_6.index(STEP_6A_HEADING) < phase_6.index(STEP_6B_HEADING)
    assert phase_6.index(STEP_6B_HEADING) < phase_6.index(STEP_6C_HEADING)


def test_multi_layer_derivation_violation_declared_with_existing_halt_shape():
    """Risk: T4. Level: structural pytest. Source: NES-280 proposal T4 and A1/A4."""
    workflow = _load_workflow_text()
    step_6c = _step_6c_section(workflow)

    assert MULTI_LAYER_VIOLATION in step_6c
    _assert_regex_near(
        step_6c,
        MULTI_LAYER_VIOLATION,
        r"(?is)more than one (?:component depth )?layer.{0,160}single derivation pass"
        r"|single derivation pass.{0,160}more than one (?:component depth )?layer",
        max_lines=20,
        where="multi-layer derivation violation condition",
    )
    _assert_regex_near(
        step_6c,
        MULTI_LAYER_VIOLATION,
        r"(?is)(orchestrator-runtime|runtime detection|runtime enforcement|runtime refusal).{0,240}"
        r"(separate enforcement WU|separate ticket|tracked in a separate ticket)"
        r"|(separate enforcement WU|separate ticket|tracked in a separate ticket).{0,240}"
        r"(orchestrator-runtime|runtime detection|runtime enforcement|runtime refusal)",
        max_lines=20,
        where="workflow declaration versus runtime enforcement split",
    )
    assert _haltrecord_required_fields(workflow) == HALTRECORD_REQUIRED_FIELDS
    assert _halt_basis_options(workflow) == HALT_BASIS_OPTIONS


def test_anti_scope_remains_doc_structural_only():
    """Risk: T5. Level: structural pytest. Source: NES-280 proposal T5 and A1/A2/A4."""
    source = Path(__file__).read_text(encoding="utf-8")
    workflow = _load_workflow_text()
    phase_6 = _phase_6_section(workflow)
    step_6c = _step_6c_section(workflow)
    import_lines = [
        line for line in source.splitlines() if re.match(r"^\s*(?:import|from)\s+", line)
    ]

    for line in import_lines:
        assert re.match(r"^(?:import re|from pathlib import Path|import pytest)$", line), (
            f"unexpected import line: {line}"
        )
        assert not re.search(
            r"\b(?:agents\.|clients\.|runtime|orchestrator)\b",
            line,
        )

    assert re.search(r"(?m)^### Step 6d\b", phase_6) is None
    assert _halt_basis_options(workflow) == HALT_BASIS_OPTIONS
    assert len(_halt_basis_options(workflow)) == 5
    assert not re.search(
        r"(?i)(?:^|[`'\s(])(?:/?home/nes/ai/|~/ai/)?(?:agents|workflows)/"
        r"[^`'\s),;]*(?:nes-280|one-layer|multi-layer|component-deriv|contract-deriv)"
        r"[^`'\s),;]*\.md",
        step_6c,
    )
