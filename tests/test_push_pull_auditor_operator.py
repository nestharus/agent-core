"""Structural tests for the NES-140 push/pull coupling auditor operator."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "push-pull-auditor.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
CODE_QUALITY_PATH = REPO_ROOT / "conventions" / "code-quality.md"

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = [
    "Role",
    "Use When",
    "Do Not Use When",
    "Required Inputs",
    "Non-Negotiables",
    "Metric Binding",
    "Procedure",
    "Output Contract",
    "Stop Conditions",
    "Sibling Boundaries",
    "Cross-References",
]
OPTIONAL_INPUTS = (
    "base_ref",
    "head_ref",
    "changed_files_path",
    "proposal_path",
    "problem_map_path",
    "risk_profile_path",
    "code_quality_ref",
)
STOP_CONDITIONS = (
    "success",
    "BLOCKED:missing-required-input",
    "BLOCKED:unreadable-input",
    "BLOCKED:malformed-diff",
    "BLOCKED:A1-metric-source",
    "BLOCKED:unwritable-output",
    "NEEDS_INPUT:<question_artifact>",
)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/push-pull-auditor.md"
    return OPERATOR_PATH.read_text(encoding="utf-8")


def _agents_text():
    return AGENTS_PATH.read_text(encoding="utf-8")


def _code_quality_text():
    return CODE_QUALITY_PATH.read_text(encoding="utf-8")


def _parse_frontmatter(text):
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    assert match, "operator file must start with YAML frontmatter"

    frontmatter = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip().strip("'\"")
    return frontmatter


def _parse_markdown_sections(text):
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    matches = list(re.finditer(r"(?m)^##\s+(?P<heading>.+?)\s*$", body))
    headings = [match.group("heading") for match in matches]
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group("heading")] = body[match.end() : end]
    return headings, sections


def _section_after_h2(text, heading):
    _, sections = _parse_markdown_sections(text)
    assert heading in sections, f"missing section heading: ## {heading}"
    return sections[heading]


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    assert match, f"missing section heading: {heading}"

    heading_level = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{heading_level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _routing_row(text, name):
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"missing operator row: {name}"
    return match.group(0)


def _contains_in_order(text, patterns):
    cursor = 0
    for pattern in patterns:
        match = re.search(pattern, text[cursor:], re.IGNORECASE | re.DOTALL)
        assert match, f"missing ordered pattern after offset {cursor}: {pattern}"
        cursor += match.end()


def test_b01_operator_path_exists():
    assert OPERATOR_PATH.exists(), "missing agents/push-pull-auditor.md"
    assert OPERATOR_PATH.stat().st_size > 1000


def test_b02_frontmatter_keys():
    frontmatter = _parse_frontmatter(_operator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS


def test_b03_frontmatter_model():
    frontmatter = _parse_frontmatter(_operator_text())

    assert frontmatter["model"] == "gpt-high"


def test_b04_description_mentions_metric_and_failure_mode():
    frontmatter = _parse_frontmatter(_operator_text())
    description = frontmatter["description"].lower()

    assert "push-vs-pull" in description
    assert "coupling" in description
    assert "uncontrolled-source coupler" in description


def test_b05_h1_names_push_pull_auditor():
    assert re.search(r"(?m)^#\s+Push/Pull Coupling Auditor\s*$", _operator_text())


def test_b06_headings_and_use_when_boundaries():
    text = _operator_text()
    headings, _ = _parse_markdown_sections(text)
    use_when = _section_after_h2(text, "Use When")

    assert headings == REQUIRED_H2_HEADINGS
    assert re.search(r"(?i)ad[- ]hoc.*reviewer|reviewer.*ad[- ]hoc", use_when)
    assert "Phase 4" in use_when
    assert "Phase 8" in use_when
    assert re.search(r"(?i)future", use_when)
    assert re.search(r"(?i)separate .*workflow[- ]wiring WU", use_when)
    assert not re.search(r"(?i)\b(now|currently)\s+integrated\b", use_when)


def test_b07_read_only_critic_and_output_path_only():
    text = _operator_text()
    role_and_non_negotiables = "\n".join(
        (
            _section_after_h2(text, "Role"),
            _section_after_h2(text, "Non-Negotiables"),
        )
    ).lower()

    assert "read-only critic" in role_and_non_negotiables
    assert "output_path" in role_and_non_negotiables
    assert re.search(r"(write|writes|writing).*only.*`?output_path`?", role_and_non_negotiables)


def test_b08_a1_source_binding_in_required_sections():
    text = _operator_text()

    for heading in ("Role", "Metric Binding", "Cross-References"):
        section = _section_after_h2(text, heading)
        assert "`~/ai/conventions/code-quality.md`" in section
        assert "Push-vs-pull system coupling" in section


def test_b09_no_local_a1_redefinition():
    text = _operator_text()

    for heading in ("Non-Negotiables", "Metric Binding"):
        section = _section_after_h2(text, heading)
        assert re.search(r"(?i)(do not|must not|never).*redefine A1", section)


def test_b10_session_graph_pull_vs_push_disambiguated():
    text = _operator_text()
    role_or_cross_refs = "\n".join(
        (
            _section_after_h2(text, "Role"),
            _section_after_h2(text, "Cross-References"),
        )
    )

    assert "Pull-vs-Push Policy" in role_or_cross_refs
    assert "agent-questions-and-session-graph.md" in role_or_cross_refs
    assert re.search(r"(?i)distinct|different|disambiguation", role_or_cross_refs)


def test_b11_required_inputs_declared():
    inputs = _section_after_h2(_operator_text(), "Required Inputs")

    for required in ("repo_root=<path>", "diff_path=<path>", "output_path=<path>"):
        assert f"`{required}`" in inputs
        assert re.search(rf"(?i)required.*{re.escape(required)}", inputs, re.DOTALL)


def test_b12_optional_inputs_declared():
    inputs = _section_after_h2(_operator_text(), "Required Inputs")

    for optional in OPTIONAL_INPUTS:
        assert re.search(rf"`{re.escape(optional)}=(?:<path>|<ref>)`", inputs)
        assert re.search(rf"(?i)optional.*{re.escape(optional)}", inputs, re.DOTALL)


def test_b13_code_quality_ref_default():
    inputs = _section_after_h2(_operator_text(), "Required Inputs")

    assert "`code_quality_ref=<path>`" in inputs
    assert "`~/ai/conventions/code-quality.md`" in inputs
    assert re.search(r"(?i)default", inputs)


def test_b14_procedure_loads_inputs_and_reads_a1_before_scoring():
    procedure = _section_after_h2(_operator_text(), "Procedure")

    _contains_in_order(
        procedure,
        (
            r"\bload\b.*\binputs\b",
            r"\bread\b.*\bA1\b",
            r"\bscore\b|\bscoring\b",
        ),
    )


def test_b15_procedure_verifies_a1_preservation_before_scoring():
    procedure = _section_after_h2(_operator_text(), "Procedure")

    _contains_in_order(
        procedure,
        (
            r"\bverify\b.*\bPush-vs-pull system coupling\b",
            r"\bsession-graph\b.*\bPull-vs-Push Policy\b",
            r"\buncontrolled-source coupler\b",
            r"\bscore\b|\bscoring\b",
        ),
    )


def test_b16_procedure_scans_every_code_level_pull_site():
    procedure = _section_after_h2(_operator_text(), "Procedure")

    assert re.search(r"(?i)(every|all).*new.*modified.*code-level", procedure)
    assert re.search(r"(?i)pull/read site|pull site|read site", procedure)
    assert re.search(r"(?i)visible.*change evidence|change evidence.*visible", procedure)


def test_b17_procedure_scans_deployment_level_pull_sites():
    procedure = _section_after_h2(_operator_text(), "Procedure")

    assert re.search(r"(?i)deployment-level", procedure)
    for token in ("database", "cache", "filesystem", "private endpoint"):
        assert token in procedure.lower()


def test_b18_low_source_control_recipe():
    text = _operator_text()
    scoring_text = "\n".join(
        (
            _section_after_h2(text, "Metric Binding"),
            _section_after_h2(text, "Procedure"),
        )
    )

    assert re.search(r"(?i)\bLOW\b.*source-control", scoring_text, re.DOTALL)
    assert re.search(r"(?i)consumer controls the source", scoring_text)
    assert re.search(r"(?i)declared owner.*controlled boundary", scoring_text, re.DOTALL)


def test_b19_low_common_interface_recipe():
    text = _operator_text()
    scoring_text = "\n".join(
        (
            _section_after_h2(text, "Metric Binding"),
            _section_after_h2(text, "Procedure"),
        )
    )

    assert re.search(r"(?i)\bLOW\b.*common-interface", scoring_text, re.DOTALL)
    assert re.search(r"(?i)producer pushes.*common interface", scoring_text, re.DOTALL)
    assert re.search(r"(?i)consumer pulls.*interface", scoring_text, re.DOTALL)
    assert re.search(r"(?i)stable|declared owner|explicit agreement", scoring_text)


def test_b20_high_recipe_private_source_vocabulary():
    text = _operator_text()
    high_text = "\n".join(
        (
            _section_after_h2(text, "Metric Binding"),
            _section_after_h2(text, "Output Contract"),
        )
    )

    assert re.search(r"(?i)\bHIGH\b", high_text)
    for token in (
        "private storage shape",
        "private file layout",
        "unstable generated output",
        "incidental naming",
        "private endpoint",
        "uncontrolled source",
        "uncontrolled-source coupler",
    ):
        assert token in high_text.lower()


def test_b21_overall_verdict_rule():
    text = _operator_text()
    verdict_text = "\n".join(
        (
            _section_after_h2(text, "Metric Binding"),
            _section_after_h2(text, "Output Contract"),
        )
    )

    assert re.search(r"(?i)overall verdict.*HIGH.*any pull site.*HIGH", verdict_text, re.DOTALL)
    assert re.search(r"(?i)otherwise.*LOW", verdict_text)
    assert re.search(r"(?i)no MEDIUM", verdict_text)


def test_b22_output_contract_report_skeleton_headings():
    output_contract = _section_after_h2(_operator_text(), "Output Contract")

    for heading in (
        "# Push/Pull Coupling Audit",
        "## Inputs Read",
        "## References Read",
        "## Pull Sites Inspected",
        "## Uncontrolled-Source Coupler Findings",
        "## Residual Ambiguity / Stop-Condition Notes",
    ):
        assert heading in output_contract


def test_b23_pull_site_table_fields():
    output_contract = _section_after_h2(_operator_text(), "Output Contract")

    assert (
        "| ID | Puller | Source | Pull mechanism | Ownership/interface evidence | "
        "Verdict | Evidence |"
    ) in output_contract
    for header in (
        "Puller",
        "Source",
        "Pull mechanism",
        "Ownership/interface evidence",
        "Verdict",
        "Evidence",
    ):
        assert header in output_contract


def test_b24_finding_schema_snake_case_keys():
    output_contract = _section_after_h2(_operator_text(), "Output Contract")

    for key in (
        "id",
        "puller",
        "source",
        "implicit_contract_evidence",
        "missing_proof",
        "decoupling_direction",
    ):
        assert re.search(rf"(?m)^`?{re.escape(key)}`?:", output_contract) or key in output_contract
    assert "failure_mode: uncontrolled-source coupler" in output_contract


def test_b25_decoupling_direction_required_and_non_remedial():
    text = _operator_text()
    critic_text = "\n".join(
        (
            _section_after_h2(text, "Non-Negotiables"),
            _section_after_h2(text, "Output Contract"),
        )
    )

    assert "decoupling_direction" in critic_text
    assert re.search(r"(?i)decoupling direction", critic_text)
    assert re.search(r"(?i)required|must", critic_text)
    assert re.search(r"(?i)not replacement code|never replacement code", critic_text)


def test_b26_final_stdout_vocabulary_bounded():
    output_contract = _section_after_h2(_operator_text(), "Output Contract")

    for token in (
        "LOW",
        "HIGH",
        "NEEDS_INPUT:<question_artifact>",
        "BLOCKED:<reason>",
    ):
        assert token in output_contract
    assert re.search(
        r"(?i)final stdout.*LOW\s*\|\s*HIGH\s*\|\s*NEEDS_INPUT:<question_artifact>\s*\|\s*BLOCKED:<reason>",
        output_contract,
        re.DOTALL,
    )


def test_b27_stop_conditions_vocabulary():
    stop_conditions = _section_after_h2(_operator_text(), "Stop Conditions")

    for token in STOP_CONDITIONS:
        assert re.search(re.escape(token), stop_conditions, re.IGNORECASE)


def test_b28_a5_scope_excluded():
    text = _operator_text()
    boundary_text = "\n".join(
        (
            _section_after_h2(text, "Do Not Use When"),
            _section_after_h2(text, "Sibling Boundaries"),
        )
    ).lower()

    for token in (
        "a5",
        "function-classification",
        "nesting depth",
        "inline-function",
        "duplicate-responsibility",
    ):
        assert token in boundary_text


def test_b29_a6_scope_excluded():
    text = _operator_text()
    boundary_text = "\n".join(
        (
            _section_after_h2(text, "Do Not Use When"),
            _section_after_h2(text, "Sibling Boundaries"),
        )
    ).lower()

    for token in ("a6", "cohesion-coupling", "cohesion", "coupling scoring"):
        assert token in boundary_text


def test_b30_workflow_runtime_routing_and_remediation_scope_excluded():
    text = _operator_text()
    boundary_text = "\n".join(
        (
            _section_after_h2(text, "Do Not Use When"),
            _section_after_h2(text, "Sibling Boundaries"),
        )
    ).lower()

    for token in (
        "workflow",
        "process-tree",
        "design audit",
        "routing maintenance",
        "ci",
        "linter",
        "pre-commit",
        "runtime",
        "remediation-code authoring",
    ):
        assert token in boundary_text


def test_b31_cross_references_targets():
    cross_references = _section_after_h2(_operator_text(), "Cross-References")

    for token in (
        "~/ai/conventions/code-quality.md",
        "Push-vs-pull system coupling",
        "agent-questions-and-session-graph.md",
        "Pull-vs-Push Policy",
        "~/ai/agents/function-classification-auditor.md",
        "~/ai/agents/cohesion-coupling-auditor.md",
        "~/ai/agents/process-tree-auditor.md",
    ):
        assert token in cross_references


def test_b32_agents_routing_row_exists():
    row = _routing_row(_agents_text(), "push-pull-auditor")

    assert row.startswith("- `push-pull-auditor` - ")


def test_b33_agents_row_links_operator_file():
    row = _routing_row(_agents_text(), "push-pull-auditor")

    assert "File: [~/ai/agents/push-pull-auditor.md](agents/push-pull-auditor.md)" in row
    assert (REPO_ROOT / "agents" / "push-pull-auditor.md").exists()


def test_b34_agents_row_inputs():
    row = _routing_row(_agents_text(), "push-pull-auditor")

    for required in ("repo_root", "diff_path", "output_path"):
        assert f"`{required}`" in row
    for optional in OPTIONAL_INPUTS:
        assert f"`{optional}?`" in row


def test_b35_agents_row_model():
    row = _routing_row(_agents_text(), "push-pull-auditor")

    assert re.search(r"\|\s+Model:\s+`gpt-high`", row)


def test_b36_agents_row_summary_phrase():
    row = _routing_row(_agents_text(), "push-pull-auditor")
    lower_row = row.lower()

    assert "push-vs-pull system coupling" in lower_row
    assert "uncontrolled-source coupler" in lower_row


def test_b37_code_quality_cross_reference_forward_pointer():
    cross_references = _section_after_heading(_code_quality_text(), "## Cross-references")

    assert "`~/ai/agents/push-pull-auditor.md`" in cross_references
    assert "A4 / NES-140 enforcement surface" in cross_references
    assert "`Push-vs-pull system coupling`" in cross_references
    assert "`uncontrolled-source coupler`" in cross_references


def test_b38_a1_preservation_phrases():
    a1_text = _code_quality_text()

    for phrase in (
        "Pulling from a source you do not control is high-coupling.",
        "uncontrolled-source coupler",
        "push into a common interface",
        "## Numerical thresholds",
        "## What this convention does not enforce",
    ):
        assert phrase in a1_text

    for metric in (
        "Nesting depth",
        "Function categories per function",
        "Cohesion by classifications touched",
        "Coupling by distinct external symbols/modules referenced",
    ):
        assert re.search(rf"(?m)^\| `{re.escape(metric)}` \|", a1_text)

    failure_modes = _section_after_heading(a1_text, "## Failure modes")
    push_pull_section = _section_after_heading(a1_text, "## Push-vs-pull system coupling")
    assert re.search(r"(?m)^- `uncontrolled-source coupler`\s*$", failure_modes)
    assert "uncontrolled-source coupler" in push_pull_section
