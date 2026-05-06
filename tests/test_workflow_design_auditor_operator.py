"""Structural tests for the NES-221 workflow-design-auditor operator."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "workflow-design-auditor.md"

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_INPUT_KEYS = ("workflow_file", "repo_root", "design_patterns_ref")
EXPECTED_STDOUT_PREFIX = "workflow-design-audit:"
EXPECTED_BOUNDARY_OPERATORS = (
    "agent-design-auditor",
    "process-tree-auditor",
    "workflow-reviewer",
)
REQUIRED_SECTION_GROUPS = (
    ("Role",),
    ("Use When",),
    ("Do Not Use When",),
    ("Required Inputs", "Inputs"),
    ("Procedure",),
    ("Output Contract", "Output"),
    ("Stop Conditions",),
    ("Anti-Scope", "Anti-scope"),
)


def _operator_text():
    return OPERATOR_PATH.read_text(encoding="utf-8")


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


def _has_heading(text, heading):
    return bool(re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text))


def _section_after_h2(text, heading_options):
    for heading in heading_options:
        match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
        if match:
            following = text[match.end() :]
            next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
            return following[: next_h1_or_h2.start()] if next_h1_or_h2 else following
    expected = " or ".join(f"## {heading}" for heading in heading_options)
    raise AssertionError(f"missing section heading: {expected}")


def test_workflow_design_auditor_file_exists():
    """T5: workflow-design-auditor.md exists under agents/."""
    assert OPERATOR_PATH.exists()


def test_workflow_design_auditor_frontmatter_contract():
    """T6: Frontmatter has exactly description, model, and output_format."""
    frontmatter = _parse_frontmatter(_operator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["description"]
    assert frontmatter["model"] == "gpt-high"
    assert frontmatter["output_format"] == ""


def test_workflow_design_auditor_required_inputs_section_names_contract_keys():
    """T7: Required inputs include workflow_file, repo_root, and design_patterns_ref."""
    inputs = _section_after_h2(_operator_text(), ("Required Inputs", "Inputs"))

    for key in REQUIRED_INPUT_KEYS:
        assert key in inputs
    assert re.search(
        r"design_patterns_ref=.*(?:~/ai|/home/nes/ai)/conventions/design-patterns\.md",
        inputs,
    )


def test_workflow_design_auditor_output_contract_names_stdout_vocabulary():
    """T8: Output Contract names stdout vocabulary, citations, and closure."""
    output_contract = _section_after_h2(_operator_text(), ("Output Contract", "Output"))

    assert EXPECTED_STDOUT_PREFIX in output_contract
    assert "Verdict:" in output_contract
    for token in ("LOW", "MEDIUM", "HIGH"):
        assert token in output_contract
    assert "pattern ID" in output_contract
    assert "Closure expectation" in output_contract


def test_workflow_design_auditor_required_body_sections_are_present():
    """T9: Operator body contains the required design-auditor skeleton sections."""
    text = _operator_text()

    for heading_options in REQUIRED_SECTION_GROUPS:
        assert any(_has_heading(text, heading) for heading in heading_options), (
            "missing section heading: "
            + " or ".join(f"## {heading}" for heading in heading_options)
        )


def test_workflow_design_auditor_boundary_names_adjacent_operators():
    """T10: Do Not Use When routes operator, topology, and step-log work elsewhere."""
    do_not_use = _section_after_h2(_operator_text(), ("Do Not Use When",))

    for operator_name in EXPECTED_BOUNDARY_OPERATORS:
        assert operator_name in do_not_use
    assert "runtime execution bundle" in do_not_use
    assert "single step log" in do_not_use
    assert "gate" in do_not_use
