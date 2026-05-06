import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
WORKFLOW_PROCESS_AUDITOR = "workflow-process-auditor"
WORKFLOW_PROCESS_AUDITOR_LINK = (
    "[~/ai/agents/workflow-process-auditor.md](agents/workflow-process-auditor.md)"
)
WORKFLOW_PROCESS_AUDITOR_INPUTS = (
    "Inputs: `workflow_file`, `run_artifacts`, `repo_root`, "
    "`process_tree_report_path?`, `expected_process_path?`, "
    "`audit_history_path?`, `report_path?`, `mode?`"
)
WU_SESSION_RESUMER = "wu-session-resumer"
WU_SESSION_RESUMER_LINK = (
    "[~/ai/agents/wu-session-resumer.md](agents/wu-session-resumer.md)"
)
WU_SESSION_RESUMER_INPUTS = (
    "pr_url",
    "merge_sha",
    "head_sha",
    "pre_merge_main_sha",
    "branch_name",
    "ticket_id",
    "session_manifest_path",
)


def _agents_text():
    return AGENTS_MD.read_text(encoding="utf-8")


def _agents_text_from(repo_root):
    return (repo_root / "AGENTS.md").read_text(encoding="utf-8")


def _assert_heading_on_own_line(text, heading):
    assert re.search(rf"(?m)^{re.escape(heading)}$", text), (
        f"missing heading on its own line: {heading}"
    )


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^##\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _relative_markdown_links(text):
    links = []
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if not target:
            continue
        target = target.split(None, 1)[0].strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "/", "#")):
            continue
        target = target.split("#", 1)[0]
        if target:
            links.append((match.group(0), target))
    return links


def _relative_markdown_targets(text):
    for _label, target in _relative_markdown_links(text):
        yield target


def _file_markdown_targets(text):
    return [
        target
        for match in re.finditer(r"File:\s+(?P<link>(?<!!)\[[^\]]+\]\([^)]+\))", text)
        for _label, target in _relative_markdown_links(match.group("link"))
    ]


def _routing_row(text, name):
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"missing operator row: {name}"
    return match.group(0)


def test_new_section_headings_present():
    text = _agents_text()
    for heading in (
        "## Project Setup Pattern",
        "## Ecosystem Map",
        "### Per-Project Policy",
    ):
        _assert_heading_on_own_line(text, heading)


def test_existing_section_headings_preserved():
    text = _agents_text()
    for heading in (
        "## Operator Routing Table",
        "## How to Invoke",
        "## Workflow Topologies",
        "## Conventions",
        "## Model Roles",
        "## Operator File Format",
        "## How Projects Extend This",
    ):
        _assert_heading_on_own_line(text, heading)


def test_existing_routing_subsection_headings_preserved():
    text = _agents_text()
    for heading in (
        "### AGENTS maintenance",
        "### Coverage / behavior / test authoring",
        "### PR review / justification",
        "### Implementation pipeline orchestration",
        "### Strategic planning / proposal alignment cycle",
        "### Roadmap cascade",
        "### Worktree / branch execution",
        "### External integration",
    ):
        _assert_heading_on_own_line(text, heading)


def test_required_new_links_resolve():
    for target in (
        "conventions/project-layout.md",
        "agents/implementation-pipeline-orchestrator.md",
        "VALUES.md",
        "clients/",
        "tools/README.md",
        "DECISIONS.md",
        "agents/linear-operator.md",
        "agents/jira-operator.md",
        "conventions/rebase-verification.md",
        "conventions/wu-session-lifecycle.md",
    ):
        assert (REPO_ROOT / target).exists(), f"missing required link target: {target}"


def test_all_relative_links_in_agents_md_resolve():
    missing = [
        target
        for target in _relative_markdown_targets(_agents_text())
        if not (REPO_ROOT / target).exists()
    ]
    assert missing == []


def test_routing_and_workflow_topology_links_are_operational_artifacts():
    """Risk: dispatch-surface static-link pollution; level: unit/structural.

    Source: NES-208 proposal Test-intent track and assumption A7.
    """
    text = _agents_text()
    operator_routing = _section_after_heading(text, "## Operator Routing Table")
    workflow_topologies = _section_after_heading(text, "## Workflow Topologies")
    conventions = _section_after_heading(text, "## Conventions")

    operator_file_targets = _file_markdown_targets(operator_routing)
    assert operator_file_targets, "expected operator routing File: links"
    for target in operator_file_targets:
        assert target.startswith("agents/"), (
            f"operator routing File target must stay under agents/: {target}"
        )
        assert (REPO_ROOT / target).exists(), (
            f"operator routing File target must resolve: {target}"
        )
        assert not target.startswith(
            ("workflows/", "conventions/", "models/", "tools/", "clients/")
        ), f"operator routing File target uses non-agent surface: {target}"
        assert target not in {"DECISIONS.md", "VALUES.md"}, (
            f"operator routing File target uses static doc: {target}"
        )

    convention_targets = list(_relative_markdown_targets(conventions))
    assert convention_targets, "expected convention section links"
    for target in convention_targets:
        assert target.startswith("conventions/"), (
            f"conventions target must stay under conventions/: {target}"
        )
        assert (REPO_ROOT / target).exists(), f"conventions target must resolve: {target}"

    workflow_targets = list(_relative_markdown_targets(workflow_topologies))
    convention_dispatch_targets = [
        target
        for target in operator_file_targets + workflow_targets
        if target.startswith("conventions/")
    ]
    assert convention_dispatch_targets == []

    assert workflow_targets, "expected workflow topology links"
    for target in workflow_targets:
        assert target.startswith("workflows/"), (
            f"workflow topology target must stay under workflows/: {target}"
        )
        assert (REPO_ROOT / target).exists(), (
            f"workflow topology target must resolve: {target}"
        )
        assert target not in {"DECISIONS.md", "VALUES.md", "models/roles.md"}, (
            f"workflow topology target uses static doc: {target}"
        )
        assert not target.startswith("conventions/"), (
            f"workflow topology target uses convention surface: {target}"
        )


def test_routing_table_rows_preserved():
    text = _agents_text()
    # Inputs markers copied from the current AGENTS.md representative rows:
    # agentsmd-curator: Inputs: `mode`, `repo_root`, `agents_md?`, `agents_dir?`, `findings_to_fix?`, `operator_file?`, `routing_entry?`
    # coverage-analyzer: Inputs: `task`, `worktree_path`, `scope?`
    # pr-writer: Inputs: `branch`, `base`, `repo_root`, `output_path`, `context_files?`, `stack_parent_pr?`, `merged_refs?`, `linear_issue_keys?`
    # coderabbit-operator: Inputs: `branch`, `base`, `worktree_path`, `test_command?`, `max_passes?`, `audit_history_path?`
    # implementation-pipeline-orchestrator: Inputs: `jira_issue_key?`, `linear_issue_key?`, `wu_brief_path?`, `ticket_system?`, `jira_url?`, `jira_project?`, `jira_account_email?`, `linear_team_key?`, `linear_project_id?`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, `audit_history_path?`, `pipeline_entry_mode?`, `audit_target_*?`, `existing_review_bundle_path?`, `review_staleness_policy?`, `tickets_first_variant?`
    # worktree-operator: Inputs: `task`, `name?`, `base_branch?`, `repo_root`, `worktrees_root?`, `e2e_settings_zip?`
    # jira-operator: Inputs: `task`, `issue_key?`, `body?`, `target_status?`, `jql?`, `fields?`, `jira_url`, `jira_project`, `jira_account_email`
    entries = {
        "agentsmd-curator": (
            "agents/agentsmd-curator.md",
            "Inputs: `mode`, `repo_root`, `agents_md?`, `agents_dir?`, `findings_to_fix?`, `operator_file?`, `routing_entry?`",
            "gpt-high",
        ),
        "coverage-analyzer": (
            "agents/coverage-analyzer.md",
            "Inputs: `task`, `worktree_path`, `scope?`",
            "gpt-high",
        ),
        "pr-writer": (
            "agents/pr-writer.md",
            "Inputs: `branch`, `base`, `repo_root`, `output_path`, `context_files?`, `stack_parent_pr?`, `merged_refs?`, `linear_issue_keys?`",
            "gpt-high",
        ),
        "coderabbit-operator": (
            "agents/coderabbit-operator.md",
            "Inputs: `branch`, `base`, `worktree_path`, `test_command?`, `max_passes?`, `audit_history_path?`",
            "gpt-high",
        ),
        "implementation-pipeline-orchestrator": (
            "agents/implementation-pipeline-orchestrator.md",
            "Inputs: `jira_issue_key?`, `linear_issue_key?`, `wu_brief_path?`, `ticket_system?`, `jira_url?`, `jira_project?`, `jira_account_email?`, `linear_team_key?`, `linear_project_id?`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, `audit_history_path?`, `pipeline_entry_mode?`, `audit_target_*?`, `existing_review_bundle_path?`, `review_staleness_policy?`, `tickets_first_variant?`",
            "claude-opus",
        ),
        "worktree-operator": (
            "agents/worktree-operator.md",
            "Inputs: `task`, `name?`, `base_branch?`, `repo_root`, `worktrees_root?`, `e2e_settings_zip?`",
            "gpt-high",
        ),
        "jira-operator": (
            "agents/jira-operator.md",
            "Inputs: `task`, `issue_key?`, `body?`, `target_status?`, `jql?`, `fields?`, `jira_url`, `jira_project`, `jira_account_email`",
            "claude-haiku",
        ),
    }
    for name, (path, inputs_marker, model) in entries.items():
        assert re.search(rf"(?m)^- `{re.escape(name)}` - ", text), (
            f"missing operator row: {name}"
        )
        file_link = f"File: [~/ai/{path}]({path})"
        assert file_link in text, f"missing file path for {name}: {path}"
        entry_pattern = (
            rf"(?ms)^- `{re.escape(name)}` - .*?\n"
            rf"  .*?{re.escape(file_link)}.*?"
            rf"{re.escape(inputs_marker)}.*? \| Model: `{re.escape(model)}`$"
        )
        assert re.search(entry_pattern, text), (
            f"missing expected inputs or model marker for {name}: {inputs_marker}; {model}"
        )


def test_new_convention_bullets_present():
    conventions = _section_after_heading(_agents_text(), "## Conventions")
    for link in (
        "[`~/ai/conventions/rebase-verification.md`](conventions/rebase-verification.md)",
        "[`~/ai/conventions/wu-session-lifecycle.md`](conventions/wu-session-lifecycle.md)",
    ):
        assert link in conventions


def test_github_url_present_in_ecosystem_map():
    text = _agents_text()
    ecosystem_match = re.search(r"(?m)^## Ecosystem Map$", text)
    assert ecosystem_match, "missing Ecosystem Map section"
    following_lines = text[ecosystem_match.end() :].splitlines()[:30]
    assert "https://github.com/nestharus/ai" in "\n".join(following_lines)


# S2 / coverage-gap MEDIUM / lean-plus / proposal Test-Intent T12.
def test_workflow_process_auditor_routing_row_present(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WORKFLOW_PROCESS_AUDITOR)

    assert row.startswith(f"- `{WORKFLOW_PROCESS_AUDITOR}` - ")


# S2 / coverage-gap MEDIUM / lean-plus / proposal Test-Intent T12.
def test_workflow_process_auditor_routing_row_links_operator_file(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WORKFLOW_PROCESS_AUDITOR)

    assert f"File: {WORKFLOW_PROCESS_AUDITOR_LINK}" in row


# S2 / coverage-gap MEDIUM and blast-radius MEDIUM / lean-plus /
# proposal Test-Intent T12.
def test_workflow_process_auditor_routing_row_inputs_and_model(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WORKFLOW_PROCESS_AUDITOR)

    assert WORKFLOW_PROCESS_AUDITOR_INPUTS in row
    assert re.search(r"\|\s+Model:\s+`?gpt-high`?", row)


# S2 / blast-radius MEDIUM and duplicate-system-count HIGH boundary / lean-plus /
# proposal Test-Intent T12.
def test_workflow_process_auditor_routing_row_boundary_phrases(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WORKFLOW_PROCESS_AUDITOR)

    assert "consumes process-tree reports as evidence" in row
    assert "does not replace" in row


# NES-168 / coverage-gap MEDIUM / proposal Test-Intent T12.
def test_wu_session_resumer_routing_row_present(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WU_SESSION_RESUMER)

    assert row.startswith(f"- `{WU_SESSION_RESUMER}` - ")


# NES-168 / coverage-gap MEDIUM / proposal Test-Intent T12.
def test_wu_session_resumer_routing_row_links_operator_file(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WU_SESSION_RESUMER)

    assert f"File: {WU_SESSION_RESUMER_LINK}" in row


# NES-168 / behavioral-ambiguity MEDIUM / proposal Test-Intent T13.
def test_wu_session_resumer_routing_row_inputs_and_model(repo_root):
    row = _routing_row(_agents_text_from(repo_root), WU_SESSION_RESUMER)

    assert re.search(r"\|\s+Model:\s+`?gpt-high`?", row)
    for input_name in WU_SESSION_RESUMER_INPUTS:
        assert f"`{input_name}`" in row
