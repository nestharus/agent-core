"""Structural tests for the NES-222 workflow-process-auditor operator."""

import re


OPERATOR_RELATIVE_PATH = "agents/workflow-process-auditor.md"
DECISIONS_RELATIVE_PATH = "DECISIONS.md"

REQUIRED_FRONTMATTER_KEYS = ("description", "model", "output_format")
EXPECTED_DESCRIPTION_LINE = (
    "description: 'Audit workflow run artifacts for procedure adherence without "
    "replacing process-tree topology review. Reports LOW/MEDIUM/HIGH findings. "
    "Read-only.'"
)
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Inputs",
    "Evidence Hierarchy",
    "Non-Negotiables",
    "Procedure",
    "Stop Conditions",
    "Output Format",
)
ROUTABLE_INPUT_MARKERS = (
    "workflow_file=<path>",
    "run_artifacts=<path or paths>",
    "repo_root=<path>",
    "process_tree_report_path=<path>",
    "expected_process_path=<path>",
    "audit_history_path=<path>",
    "report_path=<path>",
    "mode=<blocking|advisory>",
)
RUNTIME_CONTEXT_MARKERS = (
    "target_ref=<branch|commit|invocation uuid|artifact id>",
    "process_tree_path=<path>",
    "step_log=<path>",
)
REQUIRED_REPORT_FIELDS = (
    "procedure-adherence verdict",
    "topology evidence consumed",
    "violation class",
    "severity",
    "evidence source",
    "workflow location",
    "required next action",
)


def _operator_path(repo_root):
    return repo_root / OPERATOR_RELATIVE_PATH


def _operator_text(repo_root):
    path = _operator_path(repo_root)
    assert path.exists(), f"missing {OPERATOR_RELATIVE_PATH}"
    return path.read_text(encoding="utf-8")


def _frontmatter_body(text):
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    assert match, "operator file must start with YAML frontmatter"
    return match.group("body")


def _parse_frontmatter(text):
    frontmatter = {}
    for line in _frontmatter_body(text).splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip().strip("'\"")
    return frontmatter


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _assert_near(text, patterns, max_chars=260):
    joined = r".{0," + str(max_chars) + r"}"
    forward = joined.join(patterns)
    reverse = joined.join(reversed(patterns))
    assert re.search(forward, text, re.IGNORECASE | re.DOTALL) or re.search(
        reverse,
        text,
        re.IGNORECASE | re.DOTALL,
    )


# S1.1 / coverage-gap HIGH / exhaustive / proposal Test-Intent T1.
def test_operator_file_exists_and_non_empty(repo_root):
    path = _operator_path(repo_root)

    assert path.exists(), f"missing {OPERATOR_RELATIVE_PATH}"
    assert path.stat().st_size > 1000


# S1.2 / coverage-gap HIGH / exhaustive / proposal Test-Intent T2.
def test_operator_frontmatter_exact_keys(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert tuple(frontmatter) == REQUIRED_FRONTMATTER_KEYS


# S1.2 / coverage-gap HIGH / exhaustive / proposal Test-Intent T2.
def test_operator_frontmatter_model_is_gpt_high(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert frontmatter["model"] == "gpt-high"


# S1.2 / coverage-gap HIGH / exhaustive / proposal Test-Intent T2.
def test_operator_frontmatter_output_format_empty(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert frontmatter["output_format"] == ""


# S1.2 / coverage-gap HIGH / exhaustive / proposal Test-Intent T2.
def test_operator_frontmatter_description_single_quoted(repo_root):
    frontmatter = _frontmatter_body(_operator_text(repo_root))

    assert EXPECTED_DESCRIPTION_LINE in frontmatter.splitlines()


# S1.3 / coverage-gap HIGH / exhaustive / proposal Test-Intent T5.
def test_operator_required_body_sections_in_order(repo_root):
    text = _operator_text(repo_root)
    section_offsets = []

    for heading in REQUIRED_H2_HEADINGS:
        match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
        assert match, f"missing section heading: ## {heading}"
        section_offsets.append(match.start())

    assert section_offsets == sorted(section_offsets)
    assert len(set(section_offsets)) == len(REQUIRED_H2_HEADINGS)


# S1.4 / coverage-gap HIGH / exhaustive / proposal Test-Intent T3.
def test_operator_inputs_block_lists_routable_fields_in_order(repo_root):
    inputs = _section_after_h2(_operator_text(repo_root), "Inputs")
    offsets = []

    for marker in ROUTABLE_INPUT_MARKERS:
        match = re.search(rf"(?m)^-\s+`{re.escape(marker)}`\s", inputs)
        assert match, f"missing Inputs bullet: {marker}"
        offsets.append(match.start())

    assert offsets == sorted(offsets)


# S1.4 / behavioral-ambiguity MEDIUM / exhaustive / proposal Test-Intent T4 and A1.
def test_operator_runtime_context_fields_documented_outside_routable_inputs(repo_root):
    inputs = _section_after_h2(_operator_text(repo_root), "Inputs")

    for marker in RUNTIME_CONTEXT_MARKERS:
        assert marker in inputs


# S1.5 / blast-radius HIGH and duplicate-system-count HIGH / exhaustive /
# proposal Test-Intent T6 and A4.
def test_operator_process_tree_auditor_boundary_text(repo_root):
    text = _operator_text(repo_root)

    _assert_near(text, (r"process-tree-auditor", r"does not replace", r"topology"))
    assert re.search(
        r"(?:must\s+not|does\s+not)\s+emit\s+a\s+substitute\s+`?PASS\s*\|\s*FAIL`?\s+topology\s+verdict",
        text,
        re.IGNORECASE,
    )
    for phrase in (
        "child invocation",
        "model/role mapping",
        "expected-process manifest",
        "trace integrity",
    ):
        assert phrase in text


# S1.5 / blast-radius HIGH and duplicate-system-count HIGH / exhaustive /
# proposal Test-Intent T7 and A5.
def test_operator_workflow_reviewer_boundary_text(repo_root):
    text = _operator_text(repo_root)

    _assert_near(text, (r"workflow-reviewer", r"step log"))
    assert re.search(
        r"step logs?.{0,160}supporting evidence.{0,120}broader runtime bundle",
        text,
        re.IGNORECASE | re.DOTALL,
    )


# S1.6 / coverage-gap HIGH / exhaustive / proposal Test-Intent T8 and A2.
def test_operator_output_format_names_required_report_fields(repo_root):
    output_format = _section_after_h2(_operator_text(repo_root), "Output Format")

    for field in REQUIRED_REPORT_FIELDS:
        assert field in output_format
    assert "Verdict: LOW | MEDIUM | HIGH" in output_format


# S1.7 / coverage-gap HIGH / exhaustive / proposal Test-Intent T9.
def test_operator_stop_conditions_vocabulary(repo_root):
    stop_conditions = _section_after_h2(_operator_text(repo_root), "Stop Conditions")

    assert "BLOCKED:<input>" in stop_conditions
    assert "NEEDS_INPUT:<artifact>" in stop_conditions
    assert re.search(
        r"routine procedure violations?.{0,160}Violations table",
        stop_conditions,
        re.IGNORECASE | re.DOTALL,
    )


# S1.8 / duplicate-system-count HIGH / exhaustive / proposal Test-Intent T11 and A6.
def test_operator_audit_history_read_only_assertion(repo_root):
    text = _operator_text(repo_root)

    assert re.search(
        r"audit[- ]history.{0,120}read-only|read-only.{0,120}audit[- ]history",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        r"does\s+not\s+write.{0,120}audit[- ]history|decision-encoder",
        text,
        re.IGNORECASE | re.DOTALL,
    )


# S1.9 / language-fragmentation HIGH / exhaustive / proposal Test-Intent T10 and A3.
def test_operator_taxonomy_citation_present(repo_root):
    text = _operator_text(repo_root)

    assert re.search(
        r"(?:~\/ai\/conventions|\.\.\/conventions)\/workflow-execution-violations\.md",
        text,
    )


def _decisions_text(repo_root):
    return (repo_root / DECISIONS_RELATIVE_PATH).read_text(encoding="utf-8")


# S3 / coverage-gap MEDIUM and duplicate-system-count MEDIUM / lean-plus /
# proposal Test-Intent T13.
def test_decisions_md_records_workflow_reviewer_boundary(repo_root):
    text = _decisions_text(repo_root)

    assert re.search(r"\b(?:NES-222|NES-219B)\b", text)
    assert re.search(
        r"workflow-reviewer.{0,160}remains.{0,160}(?:narrow|single).{0,160}step[- ]log",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        r"workflow-process-auditor.{0,200}multi-artifact workflow runs.{0,200}step logs?.{0,160}supporting evidence",
        text,
        re.IGNORECASE | re.DOTALL,
    )


# S3 / coverage-gap MEDIUM and duplicate-system-count MEDIUM / lean-plus /
# proposal Test-Intent T14.
def test_decisions_md_records_process_tree_auditor_boundary(repo_root):
    text = _decisions_text(repo_root)

    assert re.search(r"\b(?:NES-222|NES-219B)\b", text)
    assert re.search(
        r"process-tree-auditor.{0,200}remains.{0,200}(?:topology|expected-process).{0,240}authority",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        r"workflow-process-auditor.{0,200}consumes process-tree reports as evidence",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        r"(?:does\s+not|must\s+not).{0,120}substitute\s+`?PASS\s*\|\s*FAIL`?.{0,120}topology verdict",
        text,
        re.IGNORECASE | re.DOTALL,
    )


# S3 / coverage-gap MEDIUM and duplicate-system-count MEDIUM / lean-plus /
# closes Phase 8 finding P8-F01 (S3 single-append requirement).
def test_decisions_md_workflow_process_auditor_entry_is_single_append(repo_root):
    text = _decisions_text(repo_root)
    decision_blocks = re.findall(r"(?ms)^##\s+D-[^\n]+.*?(?=^##\s+D-|\Z)", text)
    matching_blocks = [
        block
        for block in decision_blocks
        if re.search(
            r"^##\s+D-[^\n]*\b(?:NES-222|NES-219B)\b[^\n]*\bworkflow-process-auditor\b",
            block,
        )
    ]

    assert len(matching_blocks) == 1

    block = matching_blocks[0]
    assert text.count(block) == 1
    boundary_patterns = (
        r"workflow-reviewer.{0,160}remains.{0,160}(?:narrow|single).{0,160}step[- ]log",
        r"workflow-process-auditor.{0,200}multi-artifact workflow runs.{0,200}step logs?.{0,160}supporting evidence",
        r"process-tree-auditor.{0,200}remains.{0,200}(?:topology|expected-process).{0,240}authority",
        r"workflow-process-auditor.{0,200}consumes process-tree reports as evidence",
        r"(?:does\s+not|must\s+not).{0,120}substitute\s+`?PASS\s*\|\s*FAIL`?.{0,120}topology verdict",
    )
    boundary_blocks = [
        candidate
        for candidate in decision_blocks
        if all(
            re.search(pattern, candidate, re.IGNORECASE | re.DOTALL)
            for pattern in boundary_patterns
        )
    ]

    assert boundary_blocks == [block]

    assert re.search(
        boundary_patterns[0],
        block,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        boundary_patterns[1],
        block,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        boundary_patterns[2],
        block,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        boundary_patterns[3],
        block,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(
        boundary_patterns[4],
        block,
        re.IGNORECASE | re.DOTALL,
    )
