from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_contains_all(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{where} missing required token(s): {missing}"


def _section(text: str, start_heading: str, end_heading: str | None = None) -> str:
    start = text.find(start_heading)
    assert start != -1, f"missing section heading: {start_heading}"
    if end_heading is None:
        return text[start:]
    end = text.find(end_heading, start + len(start_heading))
    assert end != -1, f"missing end heading after {start_heading}: {end_heading}"
    return text[start:end]


def test_T4_workflow_documents_actual_capture_contract() -> None:
    text = _read(WORKFLOW)
    phase_8 = _section(
        text,
        "## Phase 8 - Post-CodeRabbit Review Gates",
        "## Phase 8.5 - Human Local Review Gate (tickets-first variant only)",
    )
    phase_85 = _section(
        text,
        "## Phase 8.5 - Human Local Review Gate (tickets-first variant only)",
        "## Phase 9 - Draft PR",
    )
    final_contract = text[text.find("## Phase 8 - Post-CodeRabbit Review Gates") :]

    _assert_contains_all(
        phase_8,
        (
            "Phase 8 capture documentation",
            "actual_story_points",
            "actual_capture_method",
            "claude-opus",
            "orchestrator-owned",
        ),
        where="T4 workflow Phase 8 capture documentation",
    )
    _assert_contains_all(
        phase_85,
        (
            "tickets-first Phase 8.5 deferral",
            "closure capture waits for local-review approval",
            "no calibration block, no comparison comment, no audit-history capture write",
        ),
        where="T4 workflow tickets-first deferral",
    )
    _assert_contains_all(
        final_contract,
        (
            "Final verification-only behavior",
            "Final halt-on-missing",
            "estimate_comparison_comment_ref",
            "must not post the close-comment",
        ),
        where="T4 workflow Final verification and halt contract",
    )


def test_T_worked_example_workflow_phase8_worked_example_present() -> None:
    text = _read(WORKFLOW)
    fence_marker = text.find("```worked example")
    assert fence_marker != -1, (
        "T-worked-example missing fenced block tagged 'worked example' for Phase 8"
    )

    window = text[fence_marker : fence_marker + 3000]
    _assert_contains_all(
        window,
        (
            "sample comment body",
            "inherited_story_point_estimate: 3",
            "refined_story_point_estimate: 5",
            "actual_story_points: 8",
            "actual_capture_method",
            "estimate_delta_narrative",
        ),
        where="T-worked-example concrete Phase 8 worked example",
    )
