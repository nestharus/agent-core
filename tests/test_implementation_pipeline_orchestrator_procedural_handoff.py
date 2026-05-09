import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _orchestrator_text() -> str:
    return ORCHESTRATOR.read_text(encoding="utf-8")


def _assert_contains_all(text: str, needles: list[str]) -> None:
    missing = [needle for needle in needles if needle not in text]
    assert missing == [], f"missing needles: {missing}"


def _assert_regex(text: str, pattern: str, description: str) -> None:
    assert re.search(pattern, text), f"{description}: pattern {pattern!r} not found"


def _step6c_block(text: str) -> str:
    """Return the Step 6c body up to the next H4 heading."""
    start = text.index("#### Step 6c — Write code")
    end = text.index("\n#### ", start + 1)
    return text[start:end]


def _audit2_block(text: str) -> str:
    start = text.index("#### Process-tree audit #2")
    end = text.index("\n#### ", start + 1)
    return text[start:end]


def test_step6c_orchestrator_detects_procedural_obligations_from_step6c_evidence():
    step6c = _step6c_block(_orchestrator_text())

    _assert_contains_all(
        step6c,
        [
            "implementation-discovered procedural obligation",
            "races",
            "ordering constraints",
            "retries",
            "resource lifecycle quirks",
            "behaviors-under-conditions",
            "implementation-specific quirks",
        ],
    )
    _assert_regex(
        step6c,
        r"(?is)\b4\.\s+\*\*Detect\b.{0,600}\b(?:inspect|review)\b.{0,240}\bStep 6c\b.{0,120}\b(?:output|log)\b.{0,500}\bimplementation-discovered procedural obligation\b.{0,700}\braces\b.{0,250}\bordering constraints\b.{0,250}\bretries\b.{0,250}\bresource lifecycle quirks\b.{0,250}\bbehaviors-under-conditions\b.{0,250}\bimplementation-specific quirks\b",
        "Step 6c Detect step names Step 6c evidence and all procedural classes",
    )


def test_step6c_orchestrator_records_obligation_in_output_index():
    step6c = _step6c_block(_orchestrator_text())

    _assert_contains_all(
        step6c,
        [
            "${scratch_dir}/phase6/step6b-output-index.md",
            "procedural obligation",
            "Step 6c evidence",
            "emitted procedural test file path",
            "procedural residual entry path",
            "residual class",
        ],
    )
    _assert_regex(
        step6c,
        r"(?is)\b5\.\s+\*\*Record\b.{0,700}\$\{scratch_dir\}/phase6/step6b-output-index\.md.{0,500}\bprocedural obligation\b.{0,250}\bStep 6c evidence\b.{0,250}\bemitted procedural test file path\b.{0,250}\b(?:test/test-group identifier|test-group identifier)\b.{0,350}\bprocedural residual entry path\b.{0,250}\bresidual class\b",
        "Step 6c Record step names the output-index procedural fields",
    )


def test_step6c_orchestrator_dispatches_separate_procedural_test_writer():
    step6c = _step6c_block(_orchestrator_text())

    _assert_contains_all(
        step6c,
        [
            "fresh",
            "separate",
            "Step 6b-style",
            "test-writer",
            "agents -m gpt-high",
            "different invocation UUID from Step 6c",
            "MUST NOT author the procedural test inline",
        ],
    )
    _assert_regex(
        step6c,
        r"(?is)\b6\.\s+\*\*Dispatch\b.{0,700}\bfresh\b.{0,200}\bseparate\b.{0,250}\bStep 6b-style\b.{0,250}\btest-writer\b.{0,250}`?agents -m gpt-high`?.{0,400}\bdifferent invocation UUID from Step 6c\b.{0,400}\bMUST NOT author the procedural test inline\b",
        "Step 6c Dispatch step requires a separate procedural test-writer",
    )


def test_step6c_orchestrator_refuses_close_without_test_or_residual():
    step6c = _step6c_block(_orchestrator_text())

    _assert_contains_all(
        step6c,
        [
            "component close",
            "Phase 7",
            "implementation-discovered procedural obligation",
            "authored procedural test linked from",
            "Step 6b output index",
            "procedural residual entry",
            "residual class",
        ],
    )
    _assert_regex(
        step6c,
        r"(?is)\b7\.\s+\*\*Refuse close\b.{0,500}\brefuse\b.{0,220}\bcomponent close\b.{0,350}\b(?:advance to Phase 7|Phase 7)\b.{0,500}\bimplementation-discovered procedural obligation\b.{0,500}\bauthored procedural test linked from\b.{0,250}\bStep 6b output index\b.{0,350}\bprocedural residual entry\b.{0,250}\bresidual class\b",
        "Step 6c Refuse close step blocks close without a procedural test or residual",
    )


def test_audit2_requires_procedural_handoff_evidence():
    audit2 = _audit2_block(_orchestrator_text())

    _assert_contains_all(
        audit2,
        [
            "procedural",
            "test-writer invocation UUID",
            "Step 6c invocation UUID",
            "${scratch_dir}/phase6/step6b-output-index.md",
            "Step 6c evidence",
            "emitted procedural test",
            "procedural residual",
            "residual class",
        ],
    )
    _assert_regex(
        audit2,
        r"(?is)\bprocedural\b.{0,500}\btest-writer invocation UUID\b.{0,400}\bStep 6c invocation UUID\b.{0,500}\$\{scratch_dir\}/phase6/step6b-output-index\.md.{0,500}\bStep 6c evidence\b.{0,500}\bemitted procedural test\b.{0,500}\bprocedural residual\b.{0,250}\bresidual class\b",
        "Process-tree audit #2 requires procedural handoff evidence",
    )
