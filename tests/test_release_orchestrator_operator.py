import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "release-orchestrator.md"
WORKFLOW = REPO_ROOT / "workflows" / "release-management.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
SUB_OPERATORS = [
    "release-cut-operator.md",
    "release-hotfix-operator.md",
    "release-promote-operator.md",
    "release-reconcile-operator.md",
]
REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_SECTIONS = (
    "## Role",
    "## Use When",
    "## Do Not Use When",
    "## Ticket System Pluggability",
    "## Required Inputs",
    "## Procedure",
    "## Output Contract",
    "## Stop Conditions",
)


def _orchestrator_text():
    return ORCHESTRATOR.read_text(encoding="utf-8")


def _workflow_text():
    return WORKFLOW.read_text(encoding="utf-8")


def _agents_text():
    return AGENTS_MD.read_text(encoding="utf-8")


def _section_after_heading(text, heading, terminator_pattern=r"^##\s+"):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    following = text[match.end() :]
    next_heading = re.search(rf"(?m){terminator_pattern}", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _frontmatter_text(text):
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "operator file must start with YAML frontmatter"
    return match.group(1)


def _parse_frontmatter(text):
    raw = _frontmatter_text(text)
    try:
        import yaml
    except ImportError:
        yaml = None

    if yaml is not None:
        parsed = yaml.safe_load(raw)
        assert isinstance(parsed, dict), "frontmatter must parse as a mapping"
        return parsed

    frontmatter = {}
    for line in raw.splitlines():
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip().strip("'\"")
    return frontmatter


def _assert_contains(section, section_name, needle):
    assert needle in section, f"{section_name} missing required text: {needle}"


def _assert_matches(section, section_name, pattern, description):
    assert re.search(pattern, section), (
        f"{section_name} missing required pattern for {description}: {pattern}"
    )


def _routing_row(text, name):
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"missing operator row: {name}"
    return match.group(0)


def _is_negated(line):
    return re.search(
        r"(?i)\b(?:do\s+not|don't|does\s+not|must\s+not|never|no|not|forbid|forbidden|without)\b",
        line,
    )


def _assert_no_unnegated_line(text, pattern, description):
    offenders = [
        line.strip()
        for line in text.splitlines()
        if re.search(pattern, line) and not _is_negated(line)
    ]
    assert offenders == [], f"unexpected {description}: {offenders}"


def test_frontmatter_required_keys():
    """Frontmatter has exactly the required keys and values."""
    frontmatter = _parse_frontmatter(_orchestrator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["description"]
    assert frontmatter["model"] == "claude-opus"
    assert frontmatter["output_format"] == ""


def test_required_h2_sections_present():
    """Operator body contains every required H2 section."""
    text = _orchestrator_text()

    for heading in REQUIRED_H2_SECTIONS:
        assert re.search(rf"(?m)^{re.escape(heading)}$", text), (
            f"missing required H2 section: {heading}"
        )


def test_required_inputs_section_names_all_tokens():
    """Required Inputs names release topology, lifecycle, ticket, and issue tokens."""
    section = _section_after_heading(_orchestrator_text(), "## Required Inputs")
    required_tokens = (
        "repo_root",
        "worktree_path",
        "scratch_dir",
        "planning_dir",
        "release_id",
        "develop_branch_name",
        "main_branch_name",
        "release_branch_name",
        "tag_pattern",
        "qa_lane_id",
        "freeze_window",
        "qa_evidence_path",
        "required_checks_policy",
        "settings_state_or_runbook_ticket",
        "hotfix_policy",
        "promotion_approval",
        "reconcile_obligations",
        "ticket_system",
        "jira_url",
        "jira_project",
        "jira_account_email",
        "linear_team_key",
        "linear_project_id",
    )

    for token in required_tokens:
        _assert_contains(section, "Required Inputs", token)
    assert "manifest_path" in section or "release_manifest_path" in section
    _assert_matches(
        section,
        "Required Inputs",
        r"\b(?:jira_(?:issue_key|release_key)|release_ticket_key)\b",
        "Jira issue identity",
    )
    _assert_matches(
        section,
        "Required Inputs",
        r"\b(?:linear_(?:issue_key|release_key)|release_ticket_key)\b",
        "Linear issue identity",
    )


def test_release_branch_name_pattern_present():
    """release_branch_name is associated with the release/* pattern."""
    section = _section_after_heading(_orchestrator_text(), "## Required Inputs")

    _assert_matches(
        section,
        "Required Inputs",
        r"release_branch_name[\s\S]{0,120}release/\*|release/\*[\s\S]{0,120}release_branch_name",
        "release_branch_name release/* association",
    )


def test_linear_project_id_optional():
    """linear_project_id is visibly marked optional."""
    section = _section_after_heading(_orchestrator_text(), "## Required Inputs")

    _assert_matches(
        section,
        "Required Inputs",
        r"linear_project_id\?|linear_project_id[\s\S]{0,80}\boptional\b|\boptional\b[\s\S]{0,80}linear_project_id",
        "optional linear_project_id marker",
    )


def test_ticket_system_pluggability_section_content():
    """Ticket System Pluggability names both ticket backends and operators."""
    section = _section_after_heading(
        _orchestrator_text(), "## Ticket System Pluggability"
    )

    for needle in (
        "ticket_system",
        "jira",
        "linear",
        "jira-operator.md",
        "linear-operator.md",
    ):
        _assert_contains(section, "Ticket System Pluggability", needle)


def test_procedure_names_all_release_phases_in_order():
    """Procedure names all release phases in canonical order."""
    section = _section_after_heading(_orchestrator_text(), "## Procedure")

    _assert_matches(
        section,
        "Procedure",
        r"\bcut\b[\s\S]*\bfreeze\b[\s\S]*\bhotfix-cherry-pick\b[\s\S]*\bpromote\b[\s\S]*\btag\b[\s\S]*\breconcile\b",
        "canonical release phase order",
    )


def test_procedure_names_sub_operators_per_phase():
    """Procedure names the sub-operator dispatched for each delegated phase."""
    section = _section_after_heading(_orchestrator_text(), "## Procedure")
    expected = {
        "cut": "release-cut-operator.md",
        "hotfix-cherry-pick": "release-hotfix-operator.md",
        "promote": "release-promote-operator.md",
        "reconcile": "release-reconcile-operator.md",
    }

    for phase, operator in expected.items():
        _assert_matches(
            section,
            "Procedure",
            rf"{re.escape(phase)}[\s\S]{{0,240}}{re.escape(operator)}|{re.escape(operator)}[\s\S]{{0,240}}{re.escape(phase)}",
            f"{phase} dispatches {operator}",
        )


def test_forward_references_to_sub_operators_present():
    """The orchestrator intentionally forward-references all four sub-operators."""
    text = _orchestrator_text()

    for operator in SUB_OPERATORS:
        _assert_contains(text, "release orchestrator", operator)


def test_forward_referenced_files_do_not_exist():
    """Forward-referenced sub-operator files are intentionally absent for NES-243."""
    for operator in SUB_OPERATORS:
        path = REPO_ROOT / "agents" / operator
        assert not path.exists(), f"unexpected sub-operator exists: {path}"


def test_required_citations_present():
    """Operator cites workflow, question-envelope convention, and operator format."""
    text = _orchestrator_text()

    for citation in (
        "~/ai/workflows/release-management.md",
        "~/ai/conventions/agent-questions-and-session-graph.md",
        "~/ai/agents/operator-file-format.md",
    ):
        _assert_contains(text, "release orchestrator", citation)


def test_agents_cli_dispatch_pattern_present():
    """Operator dispatch text is anchored on the agents CLI convention."""
    text = _orchestrator_text()

    assert any(pattern in text for pattern in ("agents -m", "agents -a", "agents -p"))
    _assert_contains(text, "release orchestrator", "~/ai/workflows/agents-cli.md")


def test_no_claude_code_agent_mcp_dispatch_instructions():
    """Operator does not instruct dispatch through Claude Code Agent MCP."""
    text = _orchestrator_text()

    assert not re.search(r"mcp__[A-Za-z_]+__agent", text), (
        "must not name an MCP agent-dispatch tool"
    )
    _assert_no_unnegated_line(
        text,
        r"(?i)(?:Claude Code Agent MCP|Agent tool.{0,80}dispatch|dispatch.{0,80}Agent tool)",
        "Claude Code Agent MCP dispatch instruction",
    )


def test_needs_input_envelope_present():
    """Operator names the literal NEEDS_INPUT artifact-path envelope."""
    text = _orchestrator_text()

    _assert_matches(
        text,
        "release orchestrator",
        r"NEEDS_INPUT:<(?:absolute_artifact_path|question_artifact_path|[^>]*artifact[^>]*path)>",
        "NEEDS_INPUT artifact envelope",
    )


def test_anti_scope_three_clauses_present():
    """Operator states all three explicit anti-scope clauses."""
    text = _orchestrator_text()

    _assert_matches(
        text,
        "release orchestrator",
        r"(?i)Do NOT author sub-operators NES-244\.\.247|four sub-operators \(NES-244\.\.247\)",
        "NES-244..247 sub-operator anti-scope",
    )
    _assert_matches(
        text,
        "release orchestrator",
        r"(?i)Do NOT retrofit implementation-pipeline-orchestrator\.md|no shared infrastructure with implementation-pipeline-orchestrator\.md",
        "implementation-pipeline-orchestrator anti-scope",
    )
    _assert_matches(
        text,
        "release orchestrator",
        r"(?i)Do NOT execute releases|does not execute releases",
        "live release execution anti-scope",
    )


def test_no_imperative_status_transition_instructions():
    """Operator does not issue ticket status-transition instructions."""
    text = _orchestrator_text()

    _assert_no_unnegated_line(
        text, r"\btask=transition\b", "imperative task=transition line"
    )
    _assert_no_unnegated_line(
        text, r"\btarget_status=", "imperative target_status line"
    )
    _assert_no_unnegated_line(
        text,
        r"(?i)(?:jira-operator|linear-operator).{0,160}\btransition\b.{0,80}\bstatus\b|(?:jira-operator|linear-operator).{0,160}\bstatus\b.{0,80}\btransition\b",
        "ticket-operator status transition instruction",
    )


def test_agentsmd_release_management_subheading_present():
    """AGENTS.md has a Release management subsection under Operator Routing Table."""
    routing_table = _section_after_heading(_agents_text(), "## Operator Routing Table")

    assert re.search(r"(?m)^### Release management$", routing_table), (
        "missing Release management routing subsection"
    )


def test_agentsmd_release_management_routing_rows_complete():
    """AGENTS.md release routing rows name paths and model markers."""
    routing_table = _section_after_heading(_agents_text(), "## Operator Routing Table")
    expected = {
        "release-orchestrator": ("agents/release-orchestrator.md", "claude-opus"),
        "release-cut-operator": ("agents/release-cut-operator.md", "gpt-high"),
        "release-hotfix-operator": ("agents/release-hotfix-operator.md", "gpt-high"),
        "release-promote-operator": ("agents/release-promote-operator.md", "gpt-high"),
        "release-reconcile-operator": (
            "agents/release-reconcile-operator.md",
            "gpt-high",
        ),
    }

    for name, (path, model) in expected.items():
        row = _routing_row(routing_table, name)
        _assert_contains(row, name, path)
        _assert_contains(row, name, model)


def test_agentsmd_workflow_topologies_release_entry():
    """AGENTS.md Workflow Topologies links the release-management workflow."""
    topologies = _section_after_heading(_agents_text(), "## Workflow Topologies")

    _assert_matches(
        topologies,
        "Workflow Topologies",
        r"(?m)^- .*~/ai/workflows/release-management\.md.*\(workflows/release-management\.md\)",
        "release-management topology bullet",
    )


def test_workflow_to_orchestrator_cross_reference():
    """Workflow document cross-references the release orchestrator."""
    text = _workflow_text()

    assert "release-orchestrator" in text or "~/ai/agents/release-orchestrator.md" in text


def test_orchestrator_to_workflow_cross_reference():
    """Operator cross-references the release-management workflow."""
    _assert_contains(
        _orchestrator_text(), "release orchestrator", "release-management.md"
    )
