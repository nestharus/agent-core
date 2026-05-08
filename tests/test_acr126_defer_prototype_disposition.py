import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

IMPLEMENTATION_WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
BUILD_PROTOTYPE_WORKFLOW = REPO_ROOT / "workflows" / "build-prototype.md"
IMPLEMENTATION_ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
PROTOTYPE_ORCHESTRATOR = REPO_ROOT / "agents" / "prototype-orchestrator.md"
LINEAR_OPERATOR = REPO_ROOT / "agents" / "linear-operator.md"
JIRA_OPERATOR = REPO_ROOT / "agents" / "jira-operator.md"
TICKET_GENERATION_AGENT = REPO_ROOT / "agents" / "ticket-generation-agent.md"
LINEAR_CLIENT = REPO_ROOT / "clients" / "linear" / "client.py"
LINEAR_CLI = REPO_ROOT / "clients" / "linear" / "cli.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section_with_heading_matching(text: str, heading_pattern: str) -> str:
    match = re.search(rf"(?m)^(?P<marks>##+)\s+.*(?:{heading_pattern}).*$", text)
    assert match, f"missing section heading matching: {heading_pattern}"
    level = len(match.group("marks"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _window_after(text: str, anchor: str, chars: int = 5000) -> str:
    start = text.find(anchor)
    assert start >= 0, f"missing anchor: {anchor}"
    return text[start : start + chars]


def _assert_contains_all(text: str, tokens: tuple[str, ...]) -> None:
    missing = [token for token in tokens if token not in text]
    assert missing == []


def _assert_ordered(text: str, tokens: tuple[str, ...]) -> None:
    cursor = -1
    for token in tokens:
        index = text.find(token, cursor + 1)
        assert index >= 0, f"missing ordered token after {cursor}: {token}"
        cursor = index


def _assert_not_regex(text: str, pattern: str) -> None:
    assert not re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)


def test_phase25_defer_branch_documents_immediate_disposition_before_halt() -> None:
    # risk: Phase 2.5 immediate disposition side effects can be omitted or reordered; selected level structural; source proposal test-intent row 1 / assumption register status-ownership choice.
    window = _window_after(_read(IMPLEMENTATION_ORCHESTRATOR), "defer to prototype")

    _assert_contains_all(
        window,
        (
            "prototype_id",
            "defer_source=${ticket_id}",
            "deferred_marker_operation",
            "sprint_cycle_removal",
            "${scratch_dir}/phase25/defer-disposition-execution.md",
            "comment_prompt_path",
            "comment_log_path",
            "actor=implementation-pipeline-orchestrator",
        ),
    )
    _assert_ordered(
        window,
        (
            "prototype_id",
            "prototype-orchestrator",
            "deferred_marker_operation",
            "task=comment",
            "sprint_cycle_removal",
            "defer-disposition-execution.md",
            "Halt",
        ),
    )


def test_phase25_defer_branch_linear_uses_deferred_label_not_backlog() -> None:
    # risk: Linear immediate deferral can expand the routine transition set to Backlog; selected level structural; source proposal test-intent row 2 / assumption register Linear Backlog is not added.
    window = _window_after(_read(IMPLEMENTATION_ORCHESTRATOR), "defer to prototype")

    _assert_contains_all(
        window,
        (
            "linear-operator",
            "task=apply-labels",
            "labels=deferred-to-prototype",
            "create_missing=true",
            "replace=false",
        ),
    )
    _assert_not_regex(
        window,
        r"linear-operator.{0,240}task\s*=\s*transition.{0,240}target_status\s*=\s*Backlog",
    )


def test_phase25_defer_branch_jira_prefers_blocked_with_comment_fallback() -> None:
    # risk: Jira immediate deferral can rely on an unsupported label-update path; selected level structural; source proposal test-intent row 3 / assumption register Jira Blocked fallback.
    window = _window_after(_read(IMPLEMENTATION_ORCHESTRATOR), "defer to prototype")

    _assert_contains_all(
        window,
        (
            "jira-operator",
            "task=transition",
            "target_status=Blocked",
            "Blocked",
            "comment-only",
            "task=comment",
            "unavailable",
        ),
    )
    _assert_not_regex(window, r"jira-operator.{0,240}task\s*=\s*apply-labels")


def test_phase25_defer_branch_records_sprint_cycle_removal_unsupported() -> None:
    # risk: unsupported sprint/cycle removal can be documented as actually applied; selected level structural; source proposal test-intent row 4 / assumption register sprint-cycle removal unsupported.
    window = _window_after(_read(IMPLEMENTATION_ORCHESTRATOR), "defer to prototype")

    _assert_contains_all(
        window,
        (
            "sprint_cycle_removal",
            "fallback:operationally-manual",
            "no current Linear/Jira sprint/cycle/iteration removal task",
        ),
    )
    _assert_not_regex(window, r"(cycleId|cycle_id|remove-?cycle|remove-?sprint)")


def test_phase25_defer_branch_crosslink_comment_names_tracker_or_prototype_identity() -> None:
    # risk: deferring ticket can lose the durable prototype identity link; selected level structural; source proposal test-intent row 5 / assumption register immediate cross-link comment.
    window = _window_after(_read(IMPLEMENTATION_ORCHESTRATOR), "defer to prototype")

    _assert_contains_all(
        window,
        (
            "prototype_tracker",
            "prototype_identity",
            "dossier_path",
            "prototype_tracker=none",
            "prototype-${prototype_id}",
        ),
    )
    assert "proto-<short>" in window or "proto-${" in window


def test_implementation_pipeline_workflow_documents_worked_defer_example() -> None:
    # risk: workflow docs can describe only the prototype dispatch and omit terminal disposition; selected level structural; source proposal test-intent row 6.
    section = _section_with_heading_matching(_read(IMPLEMENTATION_WORKFLOW), r"Defer to prototype")

    _assert_contains_all(
        section,
        (
            "worked example",
            "deferred-to-prototype",
            "prototype dossier",
            "close-as-superseded",
            "backend fallback",
            "sprint/cycle removal",
            "unsupported",
        ),
    )
    _assert_ordered(section, ("deferred-to-prototype", "prototype dossier", "close-as-superseded"))


def test_build_prototype_branch_disposition_keeps_branch_enum_and_adds_original_ticket_section() -> None:
    # risk: original-ticket disposition can overload the existing prototype branch enum; selected level structural; source proposal test-intent row 7 / assumption register separate branch-disposition section.
    text = _read(BUILD_PROTOTYPE_WORKFLOW)

    assert re.search(r"merge\s*(?:/|\|).*cherry-pick\s*(?:/|\|).*keep\s*(?:/|\|).*discard", text)
    _assert_contains_all(
        text,
        (
            "## Original ticket disposition",
            "Disposition:",
            "Rationale:",
            "Spawned ticket references:",
            "Backend caveats:",
        ),
    )


def test_branch_disposition_original_ticket_enum_accepts_three_values() -> None:
    # risk: P3/P4 can diverge on disposition enum values; selected level structural; source proposal test-intent row 8 / assumption register exact three values.
    section = _section_with_heading_matching(_read(BUILD_PROTOTYPE_WORKFLOW), r"Original ticket disposition")

    _assert_contains_all(section, ("close-as-superseded", "keep-as-meta-tracker", "re-defer"))
    assert re.search(
        r"Disposition:\s*<close-as-superseded\s*\|\s*keep-as-meta-tracker\s*\|\s*re-defer>",
        section,
    )
    assert "merge | cherry-pick | keep | discard" not in section


def test_prototype_p33_requests_original_ticket_disposition_evidence() -> None:
    # risk: P3.3 can file spawned tickets without evidence for original-ticket disposition; selected level structural; source proposal test-intent row 9 / assumption register P4 uses approved dossier evidence.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"P3\.3")

    _assert_contains_all(
        section,
        (
            "original deferred ticket",
            "close-as-superseded",
            "keep-as-meta-tracker",
            "re-defer",
            "spawned-ticket entries by index",
            "story_point_estimate",
            "estimate_rationale",
            "confidence",
        ),
    )


def test_prototype_p39_writes_parseable_original_ticket_disposition() -> None:
    # risk: P3.9 can leave original-ticket disposition unparseable for P4; selected level structural; source proposal test-intent row 10 / assumption register parseable section.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"P3\.9")

    _assert_contains_all(
        section,
        (
            "P3.3",
            "## Original ticket disposition",
            "Disposition:",
            "Rationale:",
            "Spawned ticket references:",
            "Backend caveats:",
        ),
    )


def test_prototype_p3_gate_reviews_original_ticket_disposition() -> None:
    # risk: P4 can execute a value decision the P3 human gate did not approve; selected level structural; source proposal test-intent row 11 / assumption register P4 does not re-gate the disposition value.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"P3 verify|human gate")

    _assert_contains_all(
        section,
        (
            "original-ticket disposition",
            "approve",
            "authorizes P4",
            "mechanical execution",
        ),
    )


def test_prototype_p4_executes_close_as_superseded_disposition() -> None:
    # risk: close-as-superseded can run before spawned ticket keys exist or without backend links/comments; selected level structural; source proposal test-intent row 12 / cross-language trace item 2.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"Phase P4|P4")

    _assert_contains_all(
        section,
        (
            "close-as-superseded",
            "parsed disposition",
            "spawned ticket keys",
            "task=transition",
            "task=comment",
            "Cloners",
            "parent/sub-issue",
            "comment-only",
        ),
    )
    _assert_ordered(section, ("File spawned tickets", "spawned ticket keys", "close-as-superseded"))


def test_prototype_p4_executes_keep_as_meta_tracker_disposition() -> None:
    # risk: keep-as-meta-tracker can leave the original ticket stranded in a deferred marker; selected level structural; source proposal test-intent row 13 / assumption register Linear parent/comment fallback.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"Phase P4|P4")

    _assert_contains_all(
        section,
        (
            "keep-as-meta-tracker",
            "Todo",
            "In Progress",
            "deferred-to-prototype",
            "replace=true",
            "parents/relates spawned tickets",
            "meta-tracker rationale",
        ),
    )


def test_prototype_p4_executes_re_defer_disposition() -> None:
    # risk: re-defer can be treated as terminal instead of preserving uncertainty and queuing the follow-up prototype; selected level structural; source proposal test-intent row 14 / assumption register recursive defer anti-scope.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"Phase P4|P4")

    _assert_contains_all(
        section,
        (
            "re-defer",
            "keep the deferred marker",
            "remaining unknowns",
            "next prototype",
            "existing prototype dispatch conventions",
        ),
    )


def test_prototype_p4_malformed_disposition_uses_needs_input_contract() -> None:
    # risk: P4 can guess from malformed approved dossier data or re-ask an approved value question; selected level structural; source proposal test-intent row 15 / question convention assumption.
    section = _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"Phase P4|P4")

    _assert_contains_all(
        section,
        (
            "NEEDS_INPUT:<absolute_question_artifact_path>",
            "missing or malformed",
            "enum value",
            "spawned keys absent",
            "MUST NOT guess",
            "MUST NOT re-ask",
        ),
    )


def test_build_prototype_p4_documents_original_ticket_disposition_execution() -> None:
    # risk: build-prototype P4 can remain branch-only and omit original-ticket hand-off execution; selected level structural; source proposal test-intent row 16.
    section = _section_with_heading_matching(_read(BUILD_PROTOTYPE_WORKFLOW), r"Phase P4|P4")

    _assert_contains_all(
        section,
        (
            "original-ticket disposition",
            "after P3 approval",
            "mechanically",
            "close-as-superseded",
            "keep-as-meta-tracker",
            "re-defer",
        ),
    )


def test_prototype_orchestrator_defer_source_is_backend_polymorphic() -> None:
    # risk: implementation pipeline passes a backend-polymorphic ticket id while prototype P0 reads only Jira; selected level structural; source proposal test-intent row 17 / cross-language trace item 1.
    text = _read(PROTOTYPE_ORCHESTRATOR)
    input_window = _window_after(text, "`defer_source`", chars=1500)
    p0_section = _section_with_heading_matching(text, r"Phase P0|P0")

    _assert_contains_all(input_window + p0_section, ("defer_source", "selected ticket operator", "Linear", "JIRA"))
    assert "originating WU's `jira_issue_key`" not in input_window
    _assert_not_regex(p0_section, r"defer_source.{0,240}via `jira-operator`")


def test_linear_operator_contract_names_deferred_label_fallback() -> None:
    # risk: Linear operator docs can fail to name the approved fallback and accidentally admit Backlog; selected level structural; source proposal test-intent row 18 / cross-language trace item 4.
    text = _read(LINEAR_OPERATOR)
    transition_section = _section_with_heading_matching(text, r"Procedure: Transition")

    _assert_contains_all(
        text,
        (
            "deferred-to-prototype",
            "task=apply-labels",
            "create_missing=true",
            "replace=false",
            "ROUTINE_MANAGER_OWNED_STATES",
        ),
    )
    assert "Backlog" not in transition_section


def test_jira_operator_contract_names_blocked_transition_and_no_label_update_fallback() -> None:
    # risk: Jira fallback can depend on a nonexistent update-label task; selected level structural; source proposal test-intent row 19 / assumption register Jira label fallback not declared.
    text = _read(JIRA_OPERATOR)

    _assert_contains_all(
        text,
        (
            "target_status=Blocked",
            "task=transition",
            "comment-only",
            "Blocked",
            "unavailable",
            "no declared",
            "apply-labels",
            "label-update",
        ),
    )
    assert not re.search(r"`task`:\s+one of[^\n]*apply-labels", text)


def test_ticket_generation_agent_preserves_estimate_fields_around_disposition_signal() -> None:
    # risk: original-ticket disposition can leak into Layer 4 spawned-ticket estimate schema; selected level structural; source proposal test-intent row 20 / estimate anti-scope assumption.
    text = _read(TICKET_GENERATION_AGENT)

    _assert_contains_all(
        text,
        (
            "original-ticket disposition",
            "prototype dossier",
            "story_point_estimate",
            "estimate_source",
            "estimate_rationale",
            "must not",
        ),
    )
    _assert_not_regex(
        text,
        r"(story_point_estimate|estimate_source|estimate_rationale)\s*:\s*original-ticket disposition",
    )


def test_linear_client_and_cli_have_no_backlog_or_cycle_removal_change() -> None:
    # risk: no-change Linear Python surfaces can grow Backlog or cycle/sprint removal primitives outside the approved fallback; selected level structural; source proposal test-intent row 21 / cross-language trace items 4-5.
    from clients.linear.client import ROUTINE_MANAGER_OWNED_STATES

    client_text = _read(LINEAR_CLIENT)
    cli_text = _read(LINEAR_CLI)
    combined = f"{client_text}\n{cli_text}"

    assert ROUTINE_MANAGER_OWNED_STATES == frozenset({"Todo", "In Progress", "Done"})
    assert "Backlog" not in combined
    for forbidden in ("cycleId", "cycle_id", "remove-cycle", "remove-sprint", "sprint_id", "iteration_id"):
        assert forbidden not in combined
