"""Structural tests for the NES-244 release-cut-operator."""

import re
from pathlib import Path


OPERATOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "agents"
    / "release-cut-operator.md"
)

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Non-Negotiables",
    "Required Inputs",
    "Optional Inputs",
    "Procedure",
    "Outputs",
    "Stop Conditions",
    "Cross-references",
)
REQUIRED_INPUTS = (
    "repo_root",
    "worktree_path",
    "scratch_dir",
    "release_id",
    "develop_branch_name",
    "release_branch_name",
    "freeze_start_marker",
    "required_checks_policy",
    "settings_state_or_runbook_ticket",
)
DO_NOT_USE_TERMS = (
    "freeze",
    "hotfix",
    "reconcile",
)
CROSS_REFERENCES = (
    "~/ai/workflows/release-management.md",
    "~/ai/agents/release-orchestrator.md",
    "~/ai/conventions/agent-questions-and-session-graph.md",
)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/release-cut-operator.md"
    assert OPERATOR_PATH.stat().st_size > 0, "operator file must be non-empty"
    return OPERATOR_PATH.read_text(encoding="utf-8")


def _frontmatter_and_body(text):
    assert text.startswith("---\n"), "operator file must start with YAML frontmatter"
    closing = text.find("\n---\n", len("---\n"))
    assert closing != -1, "operator file must close YAML frontmatter before body"
    frontmatter = text[len("---\n") : closing]
    body = text[closing + len("\n---\n") :]
    assert body.strip(), "operator body must follow YAML frontmatter"
    return frontmatter, body


def _parse_frontmatter(text):
    frontmatter_text, _body = _frontmatter_and_body(text)
    frontmatter = {}
    for line in frontmatter_text.splitlines():
        if not line.strip():
            continue
        assert not line.startswith((" ", "\t")), (
            f"frontmatter key must be top-level: {line}"
        )
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip()
    return frontmatter


def _operator_body():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    return body


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _assert_regex(text, pattern, message):
    assert re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ), message


def _near_pattern(first, second, distance=220):
    return (
        rf"{first}.{{0,{distance}}}{second}"
        rf"|{second}.{{0,{distance}}}{first}"
    )


def test_operator_file_exists():
    assert OPERATOR_PATH.exists()
    assert OPERATOR_PATH.stat().st_size > 0


def test_frontmatter_contract():
    frontmatter = _parse_frontmatter(_operator_text())
    frontmatter_lines = _frontmatter_and_body(_operator_text())[0].splitlines()

    assert list(frontmatter) == ["description", "model", "output_format"]
    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["description"].startswith("'")
    assert frontmatter["description"].endswith("'")
    assert frontmatter["description"].strip("'\"")
    assert frontmatter["model"] == "gpt-high"
    assert frontmatter["output_format"] == "''"
    assert frontmatter_lines == [
        f"description: {frontmatter['description']}",
        "model: gpt-high",
        "output_format: ''",
    ]


def test_required_sections_present_in_order():
    body = _operator_body()
    h1s = re.findall(r"(?m)^#\s+(.+?)\s*$", body)
    h2s = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

    assert h1s, "operator body must contain an H1"
    assert tuple(h2s) == REQUIRED_H2_HEADINGS


def test_role_scopes_single_release_cut_concern():
    role = _section_after_h2(_operator_body(), "Role")

    _assert_regex(
        role,
        r"cut.*release.*develop|develop.*release.*cut",
        "Role must tie release cutting to develop_branch_name",
    )
    assert "release_branch_name" in role
    assert "develop_branch_name" in role


def test_use_when_scopes_to_cut_phase_only():
    use_when = _section_after_h2(_operator_body(), "Use When")

    assert "cut" in use_when.lower()
    assert "phase" in use_when.lower()
    _assert_regex(
        use_when,
        r"cut.{0,80}(only|phase)|phase.{0,80}cut",
        "Use When must scope the operator to the cut phase only",
    )


def test_do_not_use_when_excludes_sibling_and_orchestrator_scopes():
    do_not_use = _section_after_h2(_operator_body(), "Do Not Use When")
    lower_do_not_use = do_not_use.lower()

    for term in DO_NOT_USE_TERMS:
        assert term in lower_do_not_use, f"Do Not Use When must exclude {term}"
    assert "promote" in lower_do_not_use or "tag" in lower_do_not_use
    assert "orchestrator authoring" in lower_do_not_use


def test_non_negotiables_forbid_settings_mutation():
    non_negotiables = _section_after_h2(_operator_body(), "Non-Negotiables")

    _assert_regex(
        non_negotiables,
        _near_pattern(r"(must not|does not)", r"mutate.{0,80}settings", 120),
        "Non-Negotiables must forbid mutating repository settings",
    )
    _assert_regex(
        non_negotiables,
        r"(must not|does not).{0,160}mutate.{0,80}"
        r"(branch protection|required[- ]checks|required checks)",
        "Non-Negotiables must forbid branch protection or required-check mutation",
    )
    _assert_regex(
        non_negotiables,
        r"settings.{0,80}human[- ]owned|human[- ]owned.{0,80}settings",
        "Non-Negotiables must keep settings human-owned",
    )
    assert "linear-operator" in non_negotiables
    assert "jira-operator" in non_negotiables
    assert "runbook" in non_negotiables.lower()


def test_required_inputs_section_names_contract_fields_and_manifest_alias():
    inputs = _section_after_h2(_operator_body(), "Required Inputs")

    for input_name in REQUIRED_INPUTS:
        assert input_name in inputs, f"Required Inputs must name {input_name}"
    assert "manifest_path" in inputs or "release_manifest_path" in inputs
    assert "manifest_path" in inputs and "release_manifest_path" in inputs
    _assert_regex(
        inputs,
        r"manifest_path.{0,220}(alias|corresponds|workflow).{0,220}"
        r"release_manifest_path|release_manifest_path.{0,220}"
        r"(alias|corresponds|workflow).{0,220}manifest_path",
        "Required Inputs must bind manifest_path to release_manifest_path alias",
    )


def test_optional_inputs_section_names_cut_commit_sha():
    optional_inputs = _section_after_h2(_operator_body(), "Optional Inputs")

    assert "cut_commit_sha" in optional_inputs


def test_procedure_covers_cut_point_branch_manifest_and_settings_steps():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    for token in (
        "develop_branch_name",
        "release_branch_name",
        "release/*",
        "cut_commit_sha",
        "manifest",
        "scope",
        "version",
        "counter",
        "freeze_start_marker",
        "runbook",
    ):
        assert token in procedure, f"Procedure must mention {token}"
    assert "linear-operator" in procedure or "jira-operator" in procedure
    _assert_regex(
        procedure,
        r"release_branch_name.{0,180}(does not|not).{0,80}exist"
        r"|does not.{0,80}exist.{0,180}release_branch_name",
        "Procedure must validate release_branch_name does not yet exist",
    )
    _assert_regex(
        procedure,
        r"cut_commit_sha.{0,220}(develop[-_ ]tip|develop tip)"
        r"|develop[-_ ]tip.{0,220}cut_commit_sha",
        "Procedure must resolve supplied cut_commit_sha or explicit develop tip",
    )
    _assert_regex(
        procedure,
        r"required_checks_policy.{0,240}settings_state_or_runbook_ticket"
        r"|settings_state_or_runbook_ticket.{0,240}required_checks_policy",
        "Procedure must evaluate settings evidence using both settings inputs",
    )


def test_outputs_name_durable_cut_manifest_runbook_and_stop_state_evidence():
    outputs = _section_after_h2(_operator_body(), "Outputs")

    assert "release_branch_name" in outputs
    _assert_regex(outputs, r"cut.{0,40}sha|sha.{0,40}cut", "Outputs must name cut SHA")
    _assert_regex(
        outputs,
        r"manifest.{0,80}cut record|cut record.{0,80}manifest",
        "Outputs must name manifest cut record",
    )
    for token in ("scope", "version", "counter", "runbook"):
        assert token in outputs.lower(), f"Outputs must mention {token}"
    assert (
        "stop" in outputs.lower()
        or "BLOCKED" in outputs
        or "NEEDS_INPUT" in outputs
    )


def test_stop_conditions_include_blocked_codes_and_question_artifact_contract():
    stop_conditions = _section_after_h2(_operator_body(), "Stop Conditions")

    assert "BLOCKED:missing-required-input" in stop_conditions
    assert "BLOCKED:settings-runbook-required" in stop_conditions
    assert "BLOCKED:release-branch-already-exists" in stop_conditions or re.search(
        r"(?is)BLOCKED:.{0,120}release_branch_name.{0,120}already exists",
        stop_conditions,
    )
    assert "~/ai/conventions/agent-questions-and-session-graph.md" in stop_conditions
    assert "${scratch_dir}/questions/q-" in stop_conditions
    assert "NEEDS_INPUT:<absolute_artifact_path>" in stop_conditions
    _assert_regex(
        stop_conditions,
        r"human[- ]owned.{0,220}(value|scope|trade[- ]off|access|credential|Tier-3|settings)",
        "Stop Conditions must scope NEEDS_INPUT to human-owned questions",
    )
    _assert_regex(
        stop_conditions,
        r"procedural gaps?.{0,80}block|block.{0,80}procedural gaps?",
        "Stop Conditions must say procedural gaps block instead of asking",
    )


def test_cross_references_include_required_targets_and_dispatcher():
    body = _operator_body()
    cross_references = _section_after_h2(body, "Cross-references")

    for path in CROSS_REFERENCES:
        assert path in body
        assert path in cross_references or path.endswith(
            "agent-questions-and-session-graph.md"
        )
    assert "release-orchestrator" in cross_references
    assert "dispatcher" in cross_references or "dispatch" in cross_references


def test_lifecycle_transitions_only_to_freeze():
    body = _operator_body()
    procedure_and_outputs = (
        _section_after_h2(body, "Procedure")
        + "\n"
        + _section_after_h2(body, "Outputs")
        + "\n"
        + _section_after_h2(body, "Stop Conditions")
    )

    _assert_regex(
        body,
        r"freeze.{0,80}(transition|next phase)|"
        r"(transition|next phase).{0,80}freeze",
        "Operator must state the only lifecycle transition is to freeze",
    )
    for pattern in (
        r"\b(promote|promotes|promotion)\b",
        r"\b(tag|tags|tagging)\b",
        r"\bhotfix(?:es)?\b",
        r"\b(reconcile|reconciles|reconciliation)\b",
    ):
        assert not re.search(
            pattern,
            procedure_and_outputs,
            flags=re.IGNORECASE,
        ), "Procedure/Outputs/Stop Conditions must not own later release phases"


def test_project_agnostic_configuration_has_no_local_paths_or_project_names():
    _frontmatter, body = _frontmatter_and_body(_operator_text())

    for forbidden in ("/home/nes/", "nestharus/ai", "nes-244"):
        assert forbidden not in body.lower()
    assert "develop_branch_name" in body
    assert "release_branch_name" in body
    assert "required_checks_policy" in body
