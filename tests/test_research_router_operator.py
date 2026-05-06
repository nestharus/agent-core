"""Structural tests for the NES-214 research-router operator."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "research-router.md"

# Risk annotation for this structural test group:
# coverage-gap HIGH, selected structural-smoke level, source contract
# contracts/nes-214-research-router.md.
REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Inputs",
    "Procedure",
    ("Output Contract", "Outputs / Output Contract"),
    "Stop Conditions",
    "Escalation",
    "Notes",
)
REQUIRED_PROCEDURE_H3_HEADINGS = (
    "Classification",
    ("Recommendation", "Dispatch", "Output Contract"),
    "Fallback",
    "Ambiguity Handling",
)
REQUIRED_CROSS_REFERENCES = (
    "DECISIONS.md",
    "proposer-research-integration.md",
    "research.md",
    "agent-questions-and-session-graph.md",
    "workflow-routing.md",
)


def _heading_pattern(heading):
    if isinstance(heading, tuple):
        return "|".join(re.escape(alternative) for alternative in heading)
    return re.escape(heading)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/research-router.md"
    return OPERATOR_PATH.read_text(encoding="utf-8")


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
    heading_regex = _heading_pattern(heading)
    pattern = rf"(?m)^##\s+(?:{heading_regex})\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _subsection_after_h3(section, heading_pattern):
    pattern = rf"(?m)^###\s+(?:{heading_pattern})\s*$"
    match = re.search(pattern, section)
    assert match, f"missing Procedure subsection heading: ### {heading_pattern}"

    following = section[match.end() :]
    next_heading = re.search(r"(?m)^#{1,3}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def test_operator_file_exists():
    assert OPERATOR_PATH.exists(), "missing agents/research-router.md"
    assert OPERATOR_PATH.stat().st_size >= 1500


def test_frontmatter_has_required_keys():
    frontmatter = _parse_frontmatter(_operator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["description"]
    assert frontmatter["model"] == "gpt-high"
    assert frontmatter["output_format"] == ""


def test_frontmatter_description_is_single_quoted():
    frontmatter = _frontmatter_body(_operator_text())
    description_line = next(
        line for line in frontmatter.splitlines() if line.startswith("description:")
    )
    key, separator, value = description_line.partition(": ")

    assert key == "description"
    assert separator == ": "
    assert value.startswith("'")
    assert value.endswith("'")


def test_required_sections_present():
    text = _operator_text()
    section_offsets = []

    for heading in REQUIRED_H2_HEADINGS:
        heading_regex = _heading_pattern(heading)
        match = re.search(rf"(?m)^##\s+(?:{heading_regex})\s*$", text)
        assert match, (
            f"missing section heading: ## {heading}"
        )
        section_offsets.append(match.start())

    assert section_offsets == sorted(section_offsets)
    assert len(set(section_offsets)) == len(section_offsets)


def test_required_procedure_subsections_present():
    procedure = _section_after_h2(_operator_text(), "Procedure")

    for heading in REQUIRED_PROCEDURE_H3_HEADINGS:
        heading_regex = _heading_pattern(heading)
        assert re.search(rf"(?m)^###\s+(?:{heading_regex})\s*$", procedure), (
            f"missing Procedure subsection heading: ### {heading}"
        )


def test_three_routing_categories_named():
    text = _operator_text()

    assert re.search(r"\bliterature\b", text, re.IGNORECASE)
    assert re.search(r"\bdesign[- ]pattern\b", text, re.IGNORECASE)
    assert re.search(r"\bambiguous\b", text, re.IGNORECASE)


def test_recommend_only_contract():
    output_contract = _section_after_h2(
        _operator_text(),
        ("Output Contract", "Outputs / Output Contract"),
    )
    output_contract_lower = output_contract.lower()

    assert re.search(r"\brecommend", output_contract_lower)
    assert re.search(
        r"\bdoes\s+not\b.{0,120}\b(?:invoke|dispatch|call|run)\b"
        r"|"
        r"\b(?:invoke|dispatch|call|run)\b.{0,120}\bdoes\s+not\b"
        r"|"
        r"\bno\b.{0,80}\bagents\b.{0,80}\binvocation\b"
        r"|"
        r"\bdownstream invocation\b.{0,120}\b(?:does\s+not|not)\b",
        output_contract_lower,
        re.DOTALL,
    ), "Output Contract must explicitly disclaim downstream agents invocation"


def test_output_contract_fields():
    output_contract = _section_after_h2(
        _operator_text(),
        ("Output Contract", "Outputs / Output Contract"),
    )

    required_field_patterns = (
        r"\bclassification\b",
        r"\bconfidence\b",
        r"\brationale\b",
        r"\bcurrent[ _-]+target\b",
        r"\bfuture[ _-]+target\b",
        r"\bsuggested[ _-]+source[ _-]+constraints\b",
    )
    for field_pattern in required_field_patterns:
        assert re.search(field_pattern, output_contract, re.IGNORECASE), (
            f"Output Contract missing field token: {field_pattern}"
        )


def test_fallback_cites_research_workflow():
    procedure = _section_after_h2(_operator_text(), "Procedure")
    fallback = _subsection_after_h3(procedure, "Fallback")

    assert "research.md" in fallback
    assert re.search(r"\bliterature(?:[- ]shape)?\b", fallback, re.IGNORECASE)
    assert re.search(r"\bdesign[- ]pattern(?:[- ]shape)?\b", fallback, re.IGNORECASE)


def test_brenner_bot_disclaimer():
    notes = _section_after_h2(_operator_text(), "Notes")

    assert "brenner_bot" in notes
    assert re.search(r"\breference[- ]material\b", notes, re.IGNORECASE)
    assert re.search(
        r"\b(?:not invoked|does not invoke|do not invoke)\b",
        notes,
        re.IGNORECASE,
    )
    assert "D-2026-05-05d" in notes


def test_stop_conditions_vocabulary():
    stop_conditions = _section_after_h2(_operator_text(), "Stop Conditions")

    assert "BLOCKED" in stop_conditions
    assert "NEEDS_INPUT" in stop_conditions
    assert re.search(r"\bsuccess\b", stop_conditions, re.IGNORECASE)
    assert re.search(r"\bambiguous\b", stop_conditions, re.IGNORECASE)
    assert re.search(
        r"\b(?:not\s+a\s+research|non[- ]research)\b",
        stop_conditions,
        re.IGNORECASE,
    )


def test_anti_scope_named():
    text = _operator_text()

    assert "NES-151" in text
    assert "NES-206" in text
    assert "NES-208" in text
    assert re.search(r"\b(?:brenner_bot|upstream)\b", text, re.IGNORECASE)


def test_cross_references_resolve():
    text = _operator_text()

    for basename in REQUIRED_CROSS_REFERENCES:
        assert basename in text, f"operator does not cite {basename}"
        candidates = (
            REPO_ROOT / "conventions" / basename,
            REPO_ROOT / "workflows" / basename,
            REPO_ROOT / basename,
        )
        assert any(candidate.exists() for candidate in candidates), (
            f"cited target does not resolve from repo root: {basename}"
        )
