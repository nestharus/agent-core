import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _assert_contains_all(text: str, needles: list[str]) -> None:
    missing = [needle for needle in needles if needle not in text]
    assert missing == [], f"missing needles: {missing}"


def _assert_regex(text: str, pattern: str, description: str) -> None:
    assert re.search(pattern, text), f"{description}: pattern {pattern!r} not found"


def _assert_ordered(text: str, *needles: str) -> None:
    cursor = 0
    for needle in needles:
        index = text.find(needle, cursor)
        assert index != -1, f"missing ordered text after offset {cursor}: {needle}"
        cursor = index + len(needle)


def test_phase6_overview_preserves_separation_rule_for_procedural_handoff():
    """Concept: Phase 6 overview preserves separation for procedural handoff; source proposal T1 / risk Phase 6 overview HIGH."""
    workflow = _workflow_text()

    _assert_ordered(
        workflow,
        "That rule is load-bearing: if the same agent writes both, the tests mirror the implementation instead of validating the contract.",
        "Step 6c may discover procedural obligations",
        "does not relax the different-invocation rule",
        "separate Step 6b-style test-writer invocation",
    )


def test_step6b_output_index_carries_procedural_fields():
    """Concept: Step 6b output index carries procedural fields; source proposal T2 / risk Step 6b output-index HIGH."""
    workflow = _workflow_text()

    _assert_contains_all(
        workflow,
        [
            "procedural obligation",
            "Step 6c evidence that discovered the obligation",
            "emitted procedural test file path and test or test-group identifier when a procedural test was authored, or procedural residual entry path when no procedural test is emitted",
            "residual class when no procedural test is emitted",
        ],
    )
    _assert_regex(
        workflow,
        r"(?is)Output-index fields:.{0,700}procedural obligation.{0,200}Step 6c evidence that discovered the obligation.{0,200}emitted procedural test file path and test or test-group identifier when a procedural test was authored, or procedural residual entry path when no procedural test is emitted.{0,200}residual class when no procedural test is emitted",
        "Step 6b output-index procedural field list",
    )


def test_step6c_trigger_lists_six_procedural_classes():
    """Concept: Step 6c trigger lists the six procedural classes; source proposal T3 / risk Step 6c handoff HIGH."""
    workflow = _workflow_text()

    _assert_regex(
        workflow,
        r"(?is)Step 6c - Write code.{0,1600}implementation reveals.{0,300}procedural obligation.{0,500}races.{0,250}ordering constraints.{0,250}retries.{0,250}resource lifecycle quirks.{0,250}behaviors-under-conditions.{0,250}implementation-specific quirks.{0,500}procedural-test handoff",
        "Step 6c procedural handoff trigger names six classes",
    )


def test_step6c_records_obligation_and_dispatches_separate_test_writer():
    """Concept: Step 6c records evidence and dispatches a separate test writer; source proposal T4 / risk Step 6c close-gate HIGH."""
    workflow = _workflow_text()

    _assert_contains_all(
        workflow,
        [
            "${scratch_dir}/phase6/step6b-output-index.md",
            "procedural obligation",
            "Step 6c evidence",
            "Step 6b-style test-writer invocation",
        ],
    )
    _assert_regex(
        workflow,
        r"(?is)Recording requires.{0,300}procedural obligation.{0,300}Step 6c evidence.{0,300}\$\{scratch_dir\}/phase6/step6b-output-index\.md.{0,500}(?:fresh.{0,80}separate|separate.{0,80}fresh).{0,200}Step 6b-style test-writer invocation.{0,500}MUST NOT author the procedural test inline",
        "Step 6c records obligation evidence and dispatches a separate test writer",
    )


def test_step6c_close_gate_requires_test_or_residual_per_obligation():
    """Concept: Step 6c close gate requires a test or residual per obligation; source proposal T5 / risk Step 6c close-gate HIGH."""
    workflow = _workflow_text()

    _assert_regex(
        workflow,
        r"(?is)component cannot close.{0,250}each implementation-discovered procedural obligation.{0,350}authored procedural test linked from the Step 6b output index.{0,250}recorded residual entry with residual class",
        "Step 6c close gate requires test or residual for each procedural obligation",
    )
