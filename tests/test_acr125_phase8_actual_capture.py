from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
AUDIT_HISTORY = REPO_ROOT / "conventions" / "audit-history.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, start_heading: str, end_heading: str | None = None) -> str:
    start = text.find(start_heading)
    assert start != -1, f"missing section heading: {start_heading}"
    if end_heading is None:
        return text[start:]
    end = text.find(end_heading, start + len(start_heading))
    assert end != -1, f"missing end heading after {start_heading}: {end_heading}"
    return text[start:end]


def _first_existing_section(text: str, headings: tuple[str, ...], end_heading: str) -> str:
    for heading in headings:
        if heading in text:
            return _section(text, heading, end_heading)
    assert False, f"missing any section heading: {headings}"


def _assert_contains_all(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{where} missing required token(s): {missing}"


def _assert_contains_any(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    assert any(token in text for token in tokens), (
        f"{where} missing one of required token(s): {tokens}"
    )


def _assert_ordered(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    cursor = 0
    for token in tokens:
        index = text.find(token, cursor)
        assert index != -1, (
            f"{where} missing ordered token after offset {cursor}: {token}"
        )
        cursor = index + len(token)


def _window_after(text: str, token: str, *, chars: int, where: str) -> str:
    start = text.find(token)
    assert start != -1, f"{where} missing anchor token: {token}"
    return text[start : start + chars]


def test_T1_phase8_default_capture_order() -> None:
    text = _read(ORCHESTRATOR)

    _assert_ordered(
        text,
        (
            "Process-tree audit #3",
            "`blocking` verdict halts draft PR",
            "### Phase 8.X",
            "actual_story_points",
            "### Phase 9",
            "Final close-comment",
            "inherited_story_point_estimate",
            "refined_story_point_estimate",
            "actual_story_points",
        ),
        where="T1 default Phase 8 actual-capture ordering",
    )


def test_T2_phase8_5_tickets_first_capture_after_approval() -> None:
    phase_85 = _section(
        _read(ORCHESTRATOR),
        "### Phase 8.5",
        "### Phase 9",
    )

    _assert_ordered(
        phase_85,
        (
            "A (review passed)",
            "approval recorded",
            "closure capture step occurs only after approval",
            "before Phase 9",
        ),
        where="T2 tickets-first answer A capture placement",
    )
    _assert_contains_all(
        phase_85,
        (
            "For answer B/C",
            "no calibration block, no comparison comment, no audit-history capture write",
        ),
        where="T2 tickets-first B/C no-write behavior",
    )


def test_T3_final_verifies_not_duplicates_comparison() -> None:
    final = _section(_read(ORCHESTRATOR), "### Final")

    _assert_contains_all(
        final,
        (
            "verifies calibration fields",
            "estimate_comparison_comment_ref",
            "references rather than repeats the full comparison",
        ),
        where="T3 Final calibration verification",
    )
    _assert_contains_any(
        final,
        ("halts", "blocks Final close", "must not post the close-comment"),
        where="T3 Final halt vocabulary",
    )


def test_T_judge_pin_closure_judge_model_dispatch_and_failure_mode() -> None:
    text = _read(ORCHESTRATOR)
    phase_8x = _first_existing_section(
        text,
        (
            "### Phase 8.X \u2014 Closure judge dispatch",
            "### Phase 8.X - Closure judge dispatch",
        ),
        "### Phase 9",
    )

    _assert_contains_all(
        phase_8x,
        (
            "claude-opus",
            "${planning_dir}/closure-judge.md",
            "```yaml",
            "Fibonacci",
            "null",
            "closer-best-effort | wall-time-derived | unmeasured",
            "orchestrator-supplied",
            "no retry",
            "no halt",
            "no NEEDS_INPUT",
            "missing-file",
            "missing-fence",
            "missing-key",
            "invalid-enum",
            "invalid-fibonacci",
            "value-mismatch",
            "value-mismatch:<key-name>:expected=<orch-value>:got=<judge-value>",
            "closer-best-effort:",
            "judge-output-invalid:",
            "unmeasured:",
            "estimate_comparison_comment_skip_rationale: jira-upsert-parity-deferred",
        ),
        where="T-judge-pin closure judge dispatch contract",
    )
    _assert_contains_any(
        phase_8x,
        ("first fenced YAML block", "first fenced `yaml` block", "fenced-YAML"),
        where="T-judge-pin fenced YAML parse anchor",
    )
    _assert_ordered(
        phase_8x,
        (
            "actual_story_points",
            "actual_capture_method",
            "actual_estimate_rationale",
            "inherited_story_point_estimate",
            "refined_story_point_estimate",
        ),
        where="T-judge-pin judge YAML field order",
    )


def test_T_upsert_calibration_comment_and_audit_history_are_idempotent() -> None:
    text = _read(ORCHESTRATOR)

    _assert_contains_all(
        text,
        (
            "Estimate calibration",
            "task=upsert-comment",
            "${planning_dir}/audit-history.md",
            "No append",
            "Phase 8.5 answer B/C",
            "no calibration block, no comparison comment, no audit-history capture write",
        ),
        where="T-upsert idempotent calibration writes",
    )
    _assert_contains_any(
        text,
        ("overwrite", "replace"),
        where="T-upsert audit-history overwrite/replace language",
    )


def test_T_final_halt_final_blocks_close_when_calibration_missing() -> None:
    orchestrator = _read(ORCHESTRATOR)
    workflow = _read(WORKFLOW)

    for label, text in (
        ("orchestrator", orchestrator),
        ("workflow", workflow),
    ):
        _assert_contains_any(
            text,
            ("halts", "blocks Final close", "must not post the close-comment"),
            where=f"T-final-halt {label} halt vocabulary",
        )
        _assert_contains_all(
            text,
            (
                "missing/invalid/inconsistent calibration block",
                "estimate_comparison_comment_ref",
                "must not post the close-comment",
                "<id | url | none>",
                "path",
                "none valid only when `ticket_system: jira`",
                "Final close-comment includes inherited/refined/actual values inline on both backends",
            ),
            where=f"T-final-halt {label} Final calibration contract",
        )


def test_T_delta_narrative_estimate_delta_narrative_orchestrator_template() -> None:
    text = _read(ORCHESTRATOR)

    _assert_contains_all(
        text,
        (
            "orchestrator is the deterministic producer",
            "closure judge does not author `estimate_delta_narrative`",
            "inherited=<v>; refined=<v>; actual=<v>; delta_refined_to_actual=<signed_int|null>; over_2x_inherited=<bool|unknown>",
            "actual_story_points - refined_story_point_estimate",
            "null otherwise",
            "actual_story_points > 2 * inherited_story_point_estimate",
            "unknown otherwise",
        ),
        where="T-delta-narrative deterministic producer and arithmetic rules",
    )


def test_T6_actual_capture_method_enum_and_point_validation() -> None:
    orchestrator = _read(ORCHESTRATOR)
    convention = _read(AUDIT_HISTORY)
    combined = orchestrator + "\n" + convention

    for label, text in (
        ("orchestrator", orchestrator),
        ("audit-history convention", convention),
    ):
        _assert_contains_all(
            text,
            (
                "closer-best-effort | wall-time-derived | unmeasured",
                "1, 2, 3, 5, 8, 13, 21, 40, 100",
            ),
            where=f"T6 {label} enum and Fibonacci tokens",
        )
    _assert_contains_all(
        combined,
        (
            "null only for unmeasured",
            "closer-best-effort:",
            "judge-output-invalid:missing-file",
            "judge-output-invalid:missing-fence",
            "judge-output-invalid:missing-key:",
            "judge-output-invalid:invalid-enum:",
            "judge-output-invalid:invalid-fibonacci:",
            "judge-output-invalid:value-mismatch:",
            "unmeasured:",
        ),
        where="T6 actual rationale validation vocabulary",
    )
    _assert_contains_any(
        combined,
        (
            "estimate_comparison_comment_skip_rationale: <none | jira-upsert-parity-deferred>",
            "estimate_comparison_comment_skip_rationale: <jira-upsert-parity-deferred | none>",
        ),
        where="T6 separate skip-rationale vocabulary",
    )
    forbidden_rationale_vocab = (
        "actual_estimate_rationale: <closer-best-effort:* | judge-output-invalid:* | "
        "unmeasured:* | jira-upsert-parity-deferred"
    )
    assert forbidden_rationale_vocab not in combined, (
        "T6 actual_estimate_rationale vocabulary must not include "
        "jira-upsert-parity-deferred"
    )


def test_T7_no_live_estimate_overwrite_for_actuals() -> None:
    combined = _read(ORCHESTRATOR) + "\n" + _read(WORKFLOW)

    _assert_contains_all(
        combined,
        (
            "must not dispatch `task=update-estimate` for actuals",
            "must not write actuals to Linear `estimate`",
            "must not write actuals to Jira `customfield_10016`",
        ),
        where="T7 no live estimate overwrite for actuals",
    )


def test_T8_ticket_comment_shape_backend_neutral() -> None:
    text = _read(ORCHESTRATOR)

    _assert_contains_all(
        text,
        (
            "Final close-comment includes inherited/refined/actual values inline on both backends",
            "task=upsert-comment",
            "Estimate calibration",
            "estimate_comparison_comment_skip_rationale: none",
            "estimate_comparison_comment_ref: <id|url>",
            "estimate_comparison_comment_ref: none",
            "estimate_comparison_comment_skip_rationale: jira-upsert-parity-deferred",
            "inherited_story_point_estimate",
            "refined_story_point_estimate",
            "actual_story_points",
            "actual_capture_method",
            "estimate_delta_narrative",
        ),
        where="T8 backend-neutral ticket comment shape",
    )
    _assert_contains_any(
        text,
        (
            "Jira skips the separate comparison comment",
            "Jira: skips separate comparison comment",
        ),
        where="T8 Jira comparison-comment skip",
    )
    assert "task=record-actual-estimate" not in text, (
        "T8 must not add a new task=record-actual-estimate operator task"
    )


def test_T9_no_wall_time_instrumentation() -> None:
    combined = "\n".join(
        (
            _read(ORCHESTRATOR),
            _read(WORKFLOW),
            _read(AUDIT_HISTORY),
        )
    )

    _assert_contains_any(
        combined,
        (
            "wall-time-derived reserved as enum-only",
            "wall-time-derived is reserved as enum-only",
            "wall-time-derived is a reserved enum value only",
        ),
        where="T9 wall-time-derived reserved-only wording",
    )
    wall_time_window = _window_after(
        combined,
        "wall-time-derived",
        chars=800,
        where="T9 wall-time-derived local contract",
    )
    _assert_contains_any(
        wall_time_window,
        (
            "no requirements for timers, durations, start/stop timestamps, or trace-derived time calculations",
            "does not require timers, durations, start/stop timestamps, or trace-derived time calculations",
            "must not add timers, duration tracking, start/stop timestamps, or trace-derived time calculations",
        ),
        where="T9 wall-time-derived anti-instrumentation wording",
    )
