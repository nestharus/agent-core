"""Structural tests for the NES-234 problem-bootstrap operator."""

import re


OPERATOR_RELATIVE_PATH = "agents/problem-bootstrap.md"
REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Required Inputs",
    "Procedure",
    "Output Contract",
    "Anti-scope",
    "Stop Conditions",
)
REQUIRED_INPUTS = (
    "brief_path",
    "project_root",
    "problem_path",
    "axis_table_path",
    "scratch_dir",
)


def _operator_path(repo_root):
    return repo_root / OPERATOR_RELATIVE_PATH


def _operator_text(repo_root):
    path = _operator_path(repo_root)
    assert path.exists(), f"missing {OPERATOR_RELATIVE_PATH}"
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


def _section_after_h2(text, heading):
    match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    return following[: next_h1_or_h2.start()] if next_h1_or_h2 else following


def test_problem_bootstrap_file_exists(repo_root):
    assert _operator_path(repo_root).exists()


def test_problem_bootstrap_frontmatter_exact_keys(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS


def test_problem_bootstrap_frontmatter_model_is_gpt_high(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert frontmatter["model"] == "gpt-high"


def test_problem_bootstrap_frontmatter_output_format_is_empty(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert frontmatter["output_format"] == ""


def test_problem_bootstrap_description_non_empty_and_period_terminated(repo_root):
    frontmatter = _parse_frontmatter(_operator_text(repo_root))

    assert frontmatter["description"]
    assert frontmatter["description"].endswith(".")


def test_problem_bootstrap_required_body_sections_in_order(repo_root):
    text = _operator_text(repo_root)
    section_offsets = []

    for heading in REQUIRED_H2_HEADINGS:
        match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
        assert match, f"missing section heading: ## {heading}"
        section_offsets.append(match.start())

    assert section_offsets == sorted(section_offsets)
    assert len(set(section_offsets)) == len(REQUIRED_H2_HEADINGS)


def test_problem_bootstrap_required_inputs_mentions_all_named_inputs(repo_root):
    inputs = _section_after_h2(_operator_text(repo_root), "Required Inputs")

    for input_name in REQUIRED_INPUTS:
        assert input_name in inputs


def test_problem_bootstrap_stop_conditions_mentions_required_tokens(repo_root):
    stop_conditions = _section_after_h2(_operator_text(repo_root), "Stop Conditions")

    assert "BLOCKED:" in stop_conditions
    assert "NEEDS_INPUT:" in stop_conditions


def test_problem_bootstrap_anti_scope_names_contract_boundaries(repo_root):
    anti_scope = _section_after_h2(_operator_text(repo_root), "Anti-scope")

    assert re.search(r"does\s+NOT\s+change\s+`?philosophy\.md`?", anti_scope, re.I)
    assert re.search(r"does\s+NOT\s+dispatch\s+`?proposer`?", anti_scope, re.I)
    assert re.search(
        r"does\s+NOT\s+execute\s+Stage\s+1/1b\s+sub-agents",
        anti_scope,
        re.I,
    )
