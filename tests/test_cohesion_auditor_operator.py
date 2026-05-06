"""Structural tests for the NES-209 cohesion auditor operator."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "cohesion-auditor.md"
CODE_QUALITY_PATH = REPO_ROOT / "conventions" / "code-quality.md"

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    ("Required Inputs", "Inputs"),
    "Non-Negotiables",
    "Metric Binding",
    "Notes vs Alternative Metrics",
    "Phase 4 Integration Role",
    "Procedure",
    "Output Format",
    "Stop Conditions",
    "Escalation",
)
REQUIRED_CROSS_REFERENCES = (
    "code-quality.md",
    "proposer-critic-pattern.md",
    "risk-profile.md",
    "implementation-pipeline.md",
)
A1_METRIC_ROWS = ("Cohesion by classifications touched",)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/cohesion-auditor.md"
    return OPERATOR_PATH.read_text(encoding="utf-8")


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


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


def _has_band(section, verdict, value_pattern):
    same_line = [
        line
        for line in section.splitlines()
        if re.search(rf"\b{re.escape(verdict)}\b", line, re.IGNORECASE)
        and re.search(value_pattern, line)
    ]
    return bool(same_line)


def test_operator_file_exists():
    assert OPERATOR_PATH.exists(), "missing agents/cohesion-auditor.md"
    assert OPERATOR_PATH.stat().st_size > 1000


def test_frontmatter_has_required_keys():
    frontmatter = _parse_frontmatter(_operator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["description"]
    assert frontmatter["model"] == "gpt-high"
    assert frontmatter["output_format"] == ""


def test_required_sections_present():
    text = _operator_text()

    for heading in REQUIRED_H2_HEADINGS:
        if isinstance(heading, tuple):
            alternatives = "|".join(re.escape(alternative) for alternative in heading)
            assert re.search(rf"(?m)^##\s+(?:{alternatives})\s*$", text), (
                "missing section heading: ## Required Inputs or ## Inputs"
            )
            continue
        assert re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text), (
            f"missing section heading: ## {heading}"
        )


def test_cross_references_resolve():
    text = _operator_text()

    for basename in REQUIRED_CROSS_REFERENCES:
        assert basename in text, f"operator does not cite {basename}"
        candidates = (
            REPO_ROOT / "conventions" / basename,
            REPO_ROOT / "workflows" / basename,
        )
        assert any(candidate.exists() for candidate in candidates), (
            f"cited target does not resolve from repo root: {basename}"
        )


def test_a1_metric_row_quoted_verbatim():
    a1_text = CODE_QUALITY_PATH.read_text(encoding="utf-8")
    operator_text = _operator_text()

    for row_name in A1_METRIC_ROWS:
        assert row_name in a1_text, f"A1 is missing metric row: {row_name}"
        assert row_name in operator_text, f"operator is missing metric row: {row_name}"


def test_threshold_bands_named():
    metric_binding = _section_after_h2(_operator_text(), "Metric Binding")

    assert _has_band(metric_binding, "LOW", r"\b1\b"), (
        "cohesion LOW band must include 1"
    )
    assert _has_band(metric_binding, "HIGH", r"(?:>=\s*2|≥\s*2|2\+)"), (
        "cohesion HIGH band must include >=2, ≥2, or 2+"
    )


def test_output_path_pattern_present():
    output_format = _section_after_h2(_operator_text(), "Output Format")

    assert "cohesion.md" in output_format
    assert "cohesion-coupling.md" not in output_format


def test_evidence_rule_stated():
    text = _operator_text()

    assert re.search(r"\bevidence\b", text, re.IGNORECASE)
    assert re.search(r"\b(?:HIGH|non-LOW|non LOW)\b", text)


def test_stop_conditions_named():
    stop_conditions = _section_after_h2(_operator_text(), "Stop Conditions")

    assert "BLOCKED" in stop_conditions
    assert "NEEDS_INPUT" in stop_conditions
    assert re.search(r"\bsuccess\b", stop_conditions, re.IGNORECASE)


def test_critic_role_stated():
    text = _operator_text()

    assert re.search(r"\bcritic\b", text, re.IGNORECASE)
    assert "proposer-critic-pattern.md" in text


def test_metric_binding_excludes_opposite_row():
    metric_binding = _section_after_h2(_operator_text(), "Metric Binding")

    assert (
        "Coupling by distinct external symbols/modules referenced" not in metric_binding
    )
