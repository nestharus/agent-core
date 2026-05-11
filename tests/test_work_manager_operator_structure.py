import re
from pathlib import Path

from clients.linear.client import ROUTINE_MANAGER_OWNED_STATES


REPO_ROOT = Path(__file__).resolve().parents[1]
WORK_MANAGER = REPO_ROOT / "agents" / "work-manager-operator.md"


def _operator_text():
    return WORK_MANAGER.read_text(encoding="utf-8")


def _extract_section(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    level = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _assert_contains(section, section_name, needle):
    assert needle in section, f"{section_name} missing required text: {needle}"


def _assert_matches(section, section_name, pattern, description):
    assert re.search(pattern, section), (
        f"{section_name} missing required pattern for {description}: {pattern}"
    )


def test_no_nes_source_of_truth_sentence():
    text = _operator_text()

    assert "Linear team NES is the source of truth" not in text


def test_no_list_nes_issues_phrase():
    text = _operator_text()

    assert "list NES issues" not in text


def test_no_standard_label_set_on_team_nes_phrase():
    text = _operator_text()

    assert "Standard label set on team NES" not in text


def test_reference_set_does_not_name_nes_as_backlog_source_of_truth():
    reference_set = _extract_section(_operator_text(), "## Reference Set")

    assert not re.search(
        r"(?i)linear\s+team\s+nes\b[^\n]*backlog\s+source\s+of\s+truth",
        reference_set,
    )


def test_default_sections_do_not_name_team_nes():
    text = _operator_text()

    for heading in ("## Required Inputs", "### Refresh cadence", "### Labels"):
        section = _extract_section(text, heading).replace("`", "")
        assert "team NES" not in section, f"{heading} must not default to team NES"


def test_ticket_routing_heading_present():
    text = _operator_text()

    assert re.search(r"(?m)^### Ticket routing$", text)


def test_ticket_routing_names_agent_family_team_keys():
    section = _extract_section(_operator_text(), "### Ticket routing")

    for team_key in (
        "ACR",
        "AGE",
        "AST",
        "ASC",
        "AMS",
        "ACO",
        "ALD",
        "ACX",
        "AMM",
        "ALG",
        "AEV",
        "ASS",
        "ATS",
        "AHR",
        "NES",
    ):
        _assert_matches(section, "Ticket routing", rf"\b{team_key}\b", team_key)


def test_ticket_routing_defaults_workflow_agent_convention_to_agent_core():
    section = _extract_section(_operator_text(), "### Ticket routing")
    section_lower = section.lower()

    for word in ("workflow", "agent", "convention"):
        _assert_contains(section_lower, "Ticket routing", word)
    assert "agent-core" in section_lower or re.search(r"\bACR\b", section)


def test_ticket_routing_includes_app_to_team_example():
    section = _extract_section(_operator_text(), "### Ticket routing")

    _assert_contains(section, "Ticket routing", "agent-runner")
    _assert_matches(section, "Ticket routing", r"\bAGE\b", "agent-runner AGE route")


def test_ticket_routing_names_legacy_nes_exception():
    section = _extract_section(_operator_text(), "### Ticket routing")

    assert "legacy NES" in section or "Existing NES tickets remain" in section


def test_ticket_routing_forbids_silent_ambiguous_defaults():
    section = _extract_section(_operator_text(), "### Ticket routing").lower()

    assert "silent" in section or "ambiguous" in section
    assert "ask" in section or "surface" in section


def test_required_inputs_names_ticket_system_backend_choices():
    section = _extract_section(_operator_text(), "## Required Inputs")

    assert re.search(
        r"ticket_system\s*:?\s*(?:`)?jira\s*\|\s*linear(?:`)?",
        section,
    ) or re.search(
        r"ticket_system[\s\S]{0,160}jira\s*\|\s*linear",
        section,
    )


def test_required_inputs_names_jira_and_linear_issue_key_alternatives():
    section = _extract_section(_operator_text(), "## Required Inputs")

    _assert_contains(section, "Required Inputs", "jira_issue_key")
    _assert_contains(section, "Required Inputs", "linear_issue_key")


def test_required_inputs_names_jira_input_bundle():
    section = _extract_section(_operator_text(), "## Required Inputs")

    for token in ("jira_url", "jira_project", "jira_account_email"):
        _assert_contains(section, "Required Inputs", token)


def test_required_inputs_names_linear_input_bundle():
    section = _extract_section(_operator_text(), "## Required Inputs")

    for token in ("linear_team_key", "linear_project_id"):
        _assert_contains(section, "Required Inputs", token)


def test_ticket_backend_selection_names_both_ticket_operators():
    text = _operator_text()

    _assert_contains(text, "Work Manager operator", "jira-operator.md")
    _assert_contains(text, "Work Manager operator", "linear-operator.md")


def test_ticket_backend_shorthand_variables_present():
    text = _operator_text()

    for token in ("${ticket_operator}", "${ticket_id}", "${ticket_system_inputs}"):
        _assert_contains(text, "Work Manager operator", token)


def test_ticket_format_substitution_names_adf_and_markdown():
    text = _operator_text()

    for token in ("ADF", "Markdown"):
        _assert_contains(text, "Work Manager operator", token)
    _assert_matches(
        text,
        "Work Manager operator",
        r"(?is)\bformat\b[\s\S]{0,600}\b(?:ADF|Markdown)\b|"
        r"\b(?:ADF|Markdown)\b[\s\S]{0,600}\bformat\b",
        "format substitution",
    )


def test_linear_status_transitions_are_manager_owned_for_dispatch_and_failure():
    text = _operator_text()
    text_lower = text.lower()

    assert "linear path intentionally omits status transitions" not in text_lower
    assert "status changes are user-owned" not in text_lower
    _assert_contains(text, "Work Manager operator", "manager owns")
    _assert_contains(text, "Work Manager operator", "task=transition")
    _assert_contains(text, "Work Manager operator", "target_status")
    for state in ROUTINE_MANAGER_OWNED_STATES:
        _assert_contains(text, "Work Manager operator", state)
    _assert_matches(
        text,
        "Work Manager operator",
        r"Todo\s*(?:->|\u2192|to)\s*In Progress",
        "dispatch Todo to In Progress transition",
    )
    _assert_matches(
        text,
        "Work Manager operator",
        r"In Progress\s*(?:->|\u2192|back to)\s*Todo",
        "permanent dispatch failure rollback transition",
    )
    _assert_matches(
        text,
        "Work Manager operator",
        r"(?is)In Progress\s*(?:->|\u2192|to)\s*Done[\s\S]{0,240}(GitHub|automation|manual)",
        "manual Done override for GitHub automation gap",
    )


def test_ticket_backend_selection_is_exactly_one_per_wu_or_session():
    text = _operator_text()

    _assert_matches(
        text,
        "Work Manager operator",
        r"(?is)\b(one ticket system|one backend)\b[\s\S]{0,160}\bper\s+(WU|session)\b|"
        r"\bper\s+(WU|session)\b[\s\S]{0,160}\b(one ticket system|one backend)\b",
        "exactly one ticket backend per WU or session",
    )


def test_refresh_cadence_mentions_linear_and_jira_refresh_paths():
    section = _extract_section(_operator_text(), "### Refresh cadence")

    assert "linear_team_key" in section or "linear_project_id" in section
    _assert_contains(section, "Refresh cadence", "jira_project")


def test_labels_section_uses_active_team_or_backend_aware_wording():
    section = _extract_section(_operator_text(), "### Labels")

    assert "active team" in section or (
        "Linear" in section and "JIRA" in section
    ) or "active project" in section


def test_state_transitions_reference_both_operators_and_manager_owned_linear_rule():
    section = _extract_section(_operator_text(), "### State transitions")

    _assert_contains(section, "State transitions", "jira-operator.md")
    _assert_contains(section, "State transitions", "linear-operator.md")
    _assert_contains(section, "State transitions", "task=transition")
    _assert_contains(section, "State transitions", "target_status")
    _assert_contains(section, "State transitions", "issueUpdate(stateId)")
    for state in ROUTINE_MANAGER_OWNED_STATES:
        _assert_contains(section, "State transitions", state)
    assert "user-owned" not in section.lower()


def test_github_auto_transition_is_linear_specific_without_generic_nes_example():
    section = _extract_section(_operator_text(), "### GitHub auto-transition")

    _assert_contains(section, "GitHub auto-transition", "Linear")
    assert (
        "linear_issue_keys" in section
        or "ticket_system=linear" in section
        or "Linear-only" in section
    )
    if "NES-NNN" in section:
        assert "legacy" in section


def test_reference_set_includes_both_ticket_operators():
    section = _extract_section(_operator_text(), "## Reference Set")

    _assert_contains(section, "Reference Set", "jira-operator.md")
    _assert_contains(section, "Reference Set", "linear-operator.md")


def test_anti_scope_preserves_no_inline_code_and_pipeline_orchestration_rules():
    text = _operator_text().lower()

    assert "no code edits" in text
    assert "no inline orchestration" in text


def test_overview_points_at_three_flavor_files():
    text = _operator_text()

    _assert_contains(text, "Work Manager operator", "work-manager-operator-max.md")
    _assert_contains(
        text,
        "Work Manager operator",
        "work-manager-operator-pragmatic.md",
    )
    _assert_contains(
        text,
        "Work Manager operator",
        "work-manager-operator-hackerman.md",
    )


def test_dispatch_discipline_requires_active_flavor_citation():
    text = _operator_text()

    assert "cite the active flavor" in text


def test_acr157_overview_declares_flavor_system_authority_and_gates():
    text = _operator_text()
    text_lower = text.lower()

    assert "Flavor System" in text
    assert "first-read" in text
    assert "last-authority" in text
    assert "Phase 8" in text
    assert "user-review" in text or "acceptance" in text
    assert "auto-merge" in text
    assert "bypass" in text_lower or "gate" in text_lower
