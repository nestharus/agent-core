"""Structural tests for the NES-141 function-classification auditor operator."""

import re


OPERATOR_RELATIVE_PATH = "agents/function-classification-auditor.md"
CODE_QUALITY_RELATIVE_PATH = "conventions/code-quality.md"

REQUIRED_FRONTMATTER = {
    "description": (
        "Audit changed functions against A1 function-classification rules and "
        "report multi-classifier functions with evidence and split direction."
    ),
    "model": "gpt-high",
    "output_format": "",
}
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
FUNCTION_CATEGORIES = [
    "orchestration",
    "filter",
    "validator",
    "predicate",
    "mapper",
    "accessor",
    "formatter",
    "parser",
]
FUNCTION_CLASSIFICATION_CROSS_REFERENCE = (
    "- `~/ai/agents/function-classification-auditor.md` - A5 / NES-141 "
    "enforcement surface for the `Function categories per function` threshold "
    "and `multi-classifier function` findings; this is a forward pointer only "
    "and does not change this convention's categories, rule, failure modes, "
    "thresholds, or policy-only status."
)


def _operator_path(repo_root):
    return repo_root / OPERATOR_RELATIVE_PATH


def _code_quality_path(repo_root):
    return repo_root / CODE_QUALITY_RELATIVE_PATH


def _operator_text(repo_root):
    path = _operator_path(repo_root)
    assert path.exists(), f"missing {OPERATOR_RELATIVE_PATH}"
    return path.read_text(encoding="utf-8")


def _code_quality_text(repo_root):
    path = _code_quality_path(repo_root)
    assert path.exists(), f"missing {CODE_QUALITY_RELATIVE_PATH}"
    return path.read_text(encoding="utf-8")


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


def _contains_in_order(text, patterns):
    """Assert patterns appear in text in order, using non-greedy dot-star matches."""
    cursor = 0
    for pattern in patterns:
        ordered_pattern = re.sub(r"\.\*(?!\?)", ".*?", pattern)
        match = re.search(ordered_pattern, text[cursor:], re.IGNORECASE | re.DOTALL)
        assert match, f"missing ordered pattern after offset {cursor}: {pattern}"
        cursor += match.end()


def _normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def _a1_threshold_row(text, metric_name):
    for line in text.splitlines():
        cells = [cell.strip(" `") for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == metric_name:
            assert len(cells) == 4, f"malformed threshold row for {metric_name}: {line}"
            return cells[1], cells[2], cells[3]
    raise AssertionError(f"missing threshold row: {metric_name}")


def test_t1_operator_file_frontmatter_and_sections(repo_root):
    text = _operator_text(repo_root)
    frontmatter = _parse_frontmatter(text)
    headings, _ = _parse_markdown_sections(text)

    assert set(frontmatter) == set(REQUIRED_FRONTMATTER)
    assert frontmatter == REQUIRED_FRONTMATTER
    assert re.search(r"(?m)^# Function Classification Auditor\s*$", text)
    assert headings == REQUIRED_H2_HEADINGS


def test_t2_required_and_optional_inputs_declared(repo_root):
    inputs = _section_after_h2(_operator_text(repo_root), "Required Inputs")

    for required in ("repo_root=<path>", "diff_path=<path>", "output_path=<path>"):
        assert required in inputs
        assert re.search(
            rf"required.*{re.escape(required)}",
            inputs,
            re.IGNORECASE | re.DOTALL,
        )

    for optional in (
        "base_ref=<ref>",
        "head_ref=<ref>",
        "changed_functions_path=<path>",
        "proposal_path=<path>",
        "problem_map_path=<path>",
        "risk_profile_path=<path>",
        "code_quality_ref=<path>",
    ):
        assert optional in inputs
        assert re.search(
            rf"optional.*{re.escape(optional)}",
            inputs,
            re.IGNORECASE | re.DOTALL,
        )

    assert "`~/ai/conventions/code-quality.md`" in inputs
    assert re.search(r"(?i)default", inputs)


def test_t3_operator_binds_to_a1_source_of_truth(repo_root):
    text = _operator_text(repo_root)
    binding_text = "\n".join(
        (
            _section_after_h2(text, "Role"),
            _section_after_h2(text, "Non-Negotiables"),
            _section_after_h2(text, "Metric Binding"),
            _section_after_h2(text, "Cross-References"),
        )
    )

    assert "`~/ai/conventions/code-quality.md`" in binding_text
    assert "Function categories per function" in binding_text
    assert "single-classification rule" in binding_text
    assert "multi-classifier function" in binding_text
    assert re.search(r"(?i)(source[- ]of[- ]truth|authoritative)", binding_text)
    assert re.search(r"(?i)do not redefine A1|not redefine A1", binding_text)
    for category in FUNCTION_CATEGORIES:
        assert f"`{category}`" in binding_text


def test_t4_procedure_scans_every_changed_function(repo_root):
    procedure = _section_after_h2(_operator_text(repo_root), "Procedure")

    _contains_in_order(
        procedure,
        (
            r"\bload\b.*\binputs\b",
            r"\bread\b.*\bA1\b",
            r"\bverify\b.*\bA1\b.*\bpreservation\b",
            r"\bparse\b.*\bdiff(?:_path)?\b.*\bchanged functions?\b",
            r"\b(classify|scan)\b.*\b(each|every|all)\b.*\b(new|modified|changed)\b.*\bfunctions?\b",
        ),
    )


def test_t5_per_function_scoring_requires_exactly_one_category(repo_root):
    text = _operator_text(repo_root)
    metric_binding = _section_after_h2(text, "Metric Binding")
    procedure = _section_after_h2(text, "Procedure")
    scoring_text = f"{metric_binding}\n{procedure}"

    assert "Function categories per function" in scoring_text
    assert re.search(r"(?i)exactly one .*categor", scoring_text)
    assert re.search(r"(?i)one .*A1 categor.*per function", scoring_text)


def test_t6_operator_and_a1_pin_function_category_threshold(repo_root):
    metric_binding = _section_after_h2(_operator_text(repo_root), "Metric Binding")
    a1_text = _code_quality_text(repo_root)

    assert "Function categories per function" in metric_binding
    assert "LOW = 1 / MEDIUM = n/a / HIGH = >= 2" in _normalized(metric_binding)
    assert _a1_threshold_row(a1_text, "Function categories per function") == (
        "1",
        "n/a",
        ">= 2",
    )


def test_t7_mixed_classification_finding_shape(repo_root):
    output_contract = _section_after_h2(_operator_text(repo_root), "Output Contract")

    for token in (
        "Multi-Classifier Findings",
        "categories_mixed",
        "evidence",
        "failure_mode",
        "multi-classifier function",
        "path",
        "function",
    ):
        assert token in output_contract
    assert re.search(r"(?i)(exactly )?two or more", output_contract)


def test_t8_suggested_split_is_required_but_not_replacement_code(repo_root):
    text = _operator_text(repo_root)
    critic_text = "\n".join(
        (
            _section_after_h2(text, "Non-Negotiables"),
            _section_after_h2(text, "Output Contract"),
        )
    )

    assert "suggested_split" in critic_text
    assert re.search(r"(?i)suggested split|split direction", critic_text)
    assert re.search(r"(?i)not replacement code|never replacement code", critic_text)
    assert re.search(r"(?i)do not .*author.*replacement code|forbid.*replacement code", critic_text)


def test_t9_output_contract_report_schema_and_stdout_vocabulary(repo_root):
    output_contract = _section_after_h2(_operator_text(repo_root), "Output Contract")

    for heading in (
        "# Function Classification Audit",
        "## Inputs Read",
        "## References Read",
        "## Changed Functions",
        "## Multi-Classifier Findings",
        "## Residual Ambiguity / Stop-Condition Notes",
        "Verdict: LOW | HIGH",
    ):
        assert heading in output_contract

    for table_header in (
        "| Path | Function / symbol | Line span or diff hunk | Inferred category | Verdict | Evidence |",
        "| ID | Path | Function / symbol | Categories mixed | Evidence | Suggested split |",
    ):
        assert table_header in output_contract

    for stdout_token in (
        "LOW",
        "HIGH",
        "NEEDS_INPUT:<question_artifact>",
        "BLOCKED:<reason>",
    ):
        assert stdout_token in output_contract


def test_t10_stop_conditions_are_bounded(repo_root):
    stop_conditions = _section_after_h2(_operator_text(repo_root), "Stop Conditions")

    for token in (
        "success",
        "BLOCKED:missing-required-input",
        "BLOCKED:unreadable-input",
        "BLOCKED:malformed-diff",
        "BLOCKED:A1-metric-source",
        "NEEDS_INPUT:<question_artifact>",
    ):
        assert re.search(re.escape(token), stop_conditions, re.IGNORECASE)

    assert re.search(r"(?i)new-value|new value", stop_conditions)
    assert re.search(r"(?i)scope", stop_conditions)
    assert re.search(r"(?i)trade-off|trade off", stop_conditions)
    assert re.search(r"(?i)unresolved boundary ambiguity", stop_conditions)
    assert re.search(r"(?i)materially change the verdict", stop_conditions)


def test_t11_sibling_boundaries_exclude_adjacent_scopes(repo_root):
    text = _operator_text(repo_root)
    boundary_text = "\n".join(
        (
            _section_after_h2(text, "Do Not Use When"),
            _section_after_h2(text, "Sibling Boundaries"),
        )
    )
    lower_boundary = boundary_text.lower()

    for token in (
        "a4",
        "nes-140",
        "push-vs-pull",
        "a6",
        "nes-148",
        "nes-209",
        "cohesion",
        "coupling",
        "operator",
        "workflow design",
        "process-tree",
        "nesting-depth",
        "inline-function",
        "duplicate",
        "lint",
        "ci",
        "pre-commit",
        "runtime",
        "a1 redefinition",
        "replacement-code authoring",
    ):
        assert token in lower_boundary


def test_t12_operator_is_read_only_critic(repo_root):
    text = _operator_text(repo_root)
    read_only_text = "\n".join(
        (
            _section_after_h2(text, "Role"),
            _section_after_h2(text, "Non-Negotiables"),
        )
    )
    lower_text = read_only_text.lower()

    assert "read-only critic" in lower_text
    assert re.search(r"does not (?:edit|modify)|do not (?:edit|modify)", lower_text)
    for token in (
        "code",
        "proposals",
        "tests",
        "workflows",
        "branches",
        "planning artifacts",
        "worktree files",
        "output_path",
    ):
        assert token in lower_text


def test_t13_a1_cross_references_function_classification_auditor(repo_root):
    cross_references = _section_after_heading(
        _code_quality_text(repo_root),
        "## Cross-references",
    )

    assert FUNCTION_CLASSIFICATION_CROSS_REFERENCE in cross_references


def test_t14_a1_category_list_is_exact(repo_root):
    categories = _section_after_heading(_code_quality_text(repo_root), "### Categories")
    category_names = re.findall(r"(?m)^- `([^`]+)`:", categories)

    assert category_names == FUNCTION_CATEGORIES


def test_t15_a1_single_classification_rule_is_intact(repo_root):
    rule = _section_after_heading(
        _code_quality_text(repo_root),
        "### Single-classification rule",
    )

    assert "A function must classify cleanly as exactly one of the categories below." in rule
    assert (
        "it is messy and must be split until each resulting function has one "
        "primary classification"
    ) in rule
    assert "Max function categories per function = 1." in rule


def test_t16_a1_multi_classifier_failure_mode_is_intact(repo_root):
    a1_text = _code_quality_text(repo_root)
    single_classification_rule = _section_after_heading(
        a1_text,
        "### Single-classification rule",
    )
    failure_modes = _section_after_heading(a1_text, "## Failure modes")

    assert "multi-classifier function" in single_classification_rule
    assert re.search(r"(?m)^- `multi-classifier function`\s*$", failure_modes)


def test_t17_a1_function_category_threshold_row_is_exact(repo_root):
    assert _a1_threshold_row(
        _code_quality_text(repo_root),
        "Function categories per function",
    ) == ("1", "n/a", ">= 2")


def test_t18_a1_policy_only_non_enforcement_text_is_intact(repo_root):
    non_enforcement = _section_after_heading(
        _code_quality_text(repo_root),
        "## What this convention does not enforce",
    )

    assert (
        "This convention is policy, not enforcement. Auditors and future WUs "
        "enforce it. No linter, CI gate, pre-commit hook, workflow gate, "
        "language-specific style configuration, or runtime checker is "
        "established by this file."
    ) in non_enforcement
    for token in (
        "policy, not enforcement",
        "No linter",
        "CI gate",
        "pre-commit hook",
        "workflow gate",
        "language-specific style configuration",
        "runtime checker",
    ):
        assert token in non_enforcement
