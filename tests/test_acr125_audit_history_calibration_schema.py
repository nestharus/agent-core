from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_HISTORY = REPO_ROOT / "conventions" / "audit-history.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


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


def _assert_contains_all(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    missing = [token for token in tokens if token not in text]
    assert missing == [], f"{where} missing required token(s): {missing}"


def _assert_contains_any(text: str, tokens: tuple[str, ...], *, where: str) -> None:
    assert any(token in text for token in tokens), (
        f"{where} missing one of required token(s): {tokens}"
    )


def test_T5_audit_history_final_state_schema_tokens() -> None:
    final_state = _section(_read(AUDIT_HISTORY), "## Final state")

    _assert_contains_all(
        final_state,
        (
            "ticket_id",
            "ticket_system",
            "inherited_story_point_estimate",
            "refined_story_point_estimate",
            "actual_story_points",
            "actual_capture_method",
            "actual_estimate_rationale",
            "estimate_comparison_comment_ref",
            "estimate_comparison_comment_skip_rationale",
            "estimate_delta_narrative",
            "estimate_comparison_comment_ref: <id | url | none>",
            "estimate_comparison_comment_skip_rationale: <jira-upsert-parity-deferred | none>",
        ),
        where="T5 audit-history Final state calibration schema",
    )


def test_T_parser_contract_audit_history_parser_contract_is_queryable() -> None:
    convention = _read(AUDIT_HISTORY)
    orchestrator = _read(ORCHESTRATOR)

    _assert_contains_all(
        convention,
        (
            "ACR-118/ACR-121 calibration consumers MUST locate the unique `## Final state` section and parse the YAML-style block; consumers MUST treat `actual_estimate_rationale` as the estimate-choice rationale and `estimate_comparison_comment_skip_rationale` as the separate comparison-comment skip rationale; consumers MUST parse `estimate_comparison_comment_ref` as `<id|url|none>`; consumers MAY rely on exactly one `actual_story_points:` key per file.",
            "actual_estimate_rationale",
            "estimate_comparison_comment_skip_rationale",
            "estimate_comparison_comment_ref: <id | url | none>",
        ),
        where="T-parser-contract audit-history parser contract",
    )
    _assert_contains_any(
        orchestrator,
        ("overwrite", "replace"),
        where="T-parser-contract orchestrator overwrite/replace language",
    )
    _assert_contains_all(
        orchestrator,
        (
            "exactly one `actual_story_points:` key per file",
            "No append",
        ),
        where="T-parser-contract orchestrator unique actual_story_points invariant",
    )
