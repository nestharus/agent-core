import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"


def _workflow_text():
    return WORKFLOW.read_text(encoding="utf-8")


def _section(text, heading_regex):
    match = re.search(rf"(?m)^(?P<level>#+) {heading_regex}\s*$", text)
    assert match, f"missing section heading matching: {heading_regex}"

    level = match.group("level")
    next_heading = re.search(rf"(?m)^#{{1,{len(level)}}} ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _phase_6_section():
    return _section(_workflow_text(), r"Phase 6 - Implementation \(required; test/code separation\)")


def _step_6b_section():
    return _section(_workflow_text(), r"Step 6b - Encode tests first")


def _step_6c_section():
    return _section(_workflow_text(), r"Step 6c - Write code")


def _assert_contains_all(text, phrases, *, where):
    missing = [phrase for phrase in phrases if phrase not in text]
    assert missing == [], f"{where} missing required text: {missing}"


def _assert_matches(text, pattern, description):
    assert re.search(pattern, text), f"missing {description}: {pattern}"


def _assert_ordered(text, phrases, *, where):
    cursor = 0
    for phrase in phrases:
        index = text.find(phrase, cursor)
        assert index != -1, f"{where} missing ordered text after offset {cursor}: {phrase}"
        cursor = index + len(phrase)


def test_phase_6_has_three_sub_steps_in_order():
    # Phase 2.5 characterization: invariant 1 (per nes-268-coverage-inventory.md "Uncovered behaviors").
    # Risk: scope-risk MEDIUM. Source: ~/ai/conventions/risk-profile.md per-surface verdict for the workflow doc.
    phase_6 = _phase_6_section()

    step_headings = re.findall(r"(?m)^### (Step 6[^-\n]*) - ", phase_6)

    assert step_headings == ["Step 6a", "Step 6b", "Step 6c"]


def test_phase_6_preserves_step_6b_6c_independence_rule():
    # Phase 2.5 characterization: invariant 2 (Step 6b/Step 6c independence rule, "load-bearing" per workflow doc).
    # Risk: scope-risk MEDIUM (preserves separation invariant NES-268 must not regress).
    phase_6 = _phase_6_section()
    step_6b = _step_6b_section()
    step_6c = _step_6c_section()

    _assert_matches(
        phase_6,
        r"(?is)test writer.{0,120}code writer.{0,120}different agent invocations",
        "Phase 6 different-invocation rule",
    )
    _assert_contains_all(
        step_6b,
        (
            "the test writer is a separate agent invocation from Step 6c",
            "the test writer does **not** see the implementation",
        ),
        where="Step 6b independence rules",
    )
    _assert_contains_all(
        step_6c,
        ("the code writer is a separate agent invocation from Step 6b",),
        where="Step 6c independence rules",
    )


def test_step_6c_requires_phase_6_process_tree_review_before_coderabbit():
    # Phase 2.5 characterization: invariant 3 (Phase 6 process-tree audit #2 boundary before Phase 7).
    # Risk: scope-risk MEDIUM (NES-268 must preserve audit-#2 evidence model except via the proposal §2 carve-out).
    step_6c = _step_6c_section()

    _assert_contains_all(
        step_6c,
        (
            "Process-tree review",
            "after Step 6c completes and before Phase 7",
            "process-tree-auditor",
            "Phase 6 subtree",
            "prevents CodeRabbit",
        ),
        where="Step 6c to Phase 7 audit boundary",
    )


def test_phase_6_invalidated_assumption_or_problem_map_drift_returns_to_phase_2_5():
    # Phase 2.5 characterization: invariant 4 (problem-map fallback rule preserved across NES-268's Phase 6 edit).
    # Risk: scope-risk MEDIUM.
    phase_6 = _phase_6_section()

    _assert_contains_all(
        phase_6,
        (
            "if Step 6a, 6b, or 6c uncovers evidence",
            "invalidates an approved assumption",
            "the touched surface differs materially from the approved `problem map`",
            "stop implementation and return to research",
            "resume at Phase 2.5 before more code or tests are written",
        ),
        where="Phase 6 Phase 2.5 fallback rule",
    )


def test_phase_5_phase_6_phase_7_ordering_is_preserved():
    # Phase 2.5 characterization: invariant 5 (phase ordering preserved; NES-268 must not reorder phases).
    # Risk: scope-risk MEDIUM.
    workflow = _workflow_text()

    _assert_ordered(
        workflow,
        (
            "## Phase 5 - Hookpoint Research",
            "## Phase 6 - Implementation (required; test/code separation)",
            "## Phase 7 - CodeRabbit Loop",
        ),
        where="Phase 5 to Phase 7 ordering",
    )
