"""Structural tests for NES-277 post-mortem-author contract.

Source of truth: contracts/nes-277-post-mortem-author.md.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "post-mortem-author.md"
AGENTS_MD_PATH = REPO_ROOT / "AGENTS.md"

FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_BODY_SECTIONS = (
    "# Post-Mortem Author",
    "## Role",
    "## Use When",
    "## Do Not Use When",
    "## Required Inputs",
    "## Procedure",
    "## Output Contract",
    "## Anti-Scope",
    "## Stop Conditions",
)
REQUIRED_INPUT_TOKENS = ("findings_path", "incident_brief_path", "output_path")
OUTPUT_CONTRACT_SECTION_NAMES = (
    "TL;DR",
    "Background",
    "Reframe",
    "Root cause(s)",
    "Per-customer / per-environment divergence",
    "Per-suspect-commit verdict",
    "What went well",
    "What went poorly",
    "Action items",
    "Lessons learned",
    "Open items",
    "References",
)
FINDINGS_COMPATIBILITY_TOKENS = (
    "confirmed",
    "probable",
    "unverified",
    "causal",
    "contributing",
    "incidental",
    "unverifiable from code alone",
)
STOP_CONDITION_TOKENS = ("WROTE:", "BLOCKED:", "NEEDS_INPUT:")
ANTI_SCOPE_PATTERNS = {
    "no own investigation": r"\bno\b.{0,40}\b(?:own|independent|new)\b.{0,40}\binvestigat",
    "no ticket filing/transitioning/commenting": (
        r"\bno\b.{0,60}\bticket\b.{0,80}\b(?:filing|transitioning|commenting)"
        r"|\bticket\b.{0,80}\b(?:filing|transitioning|commenting)\b.{0,60}\bno\b"
        r"|\bdo not\b.{0,60}\bticket\b.{0,80}\b(?:file|transition|comment)"
    ),
    "no external posting": (
        r"\bno\b.{0,80}\b(?:Confluence|Slack|GitHub|Jira|Linear)\b.{0,80}\bpost"
        r"|\bno\b.{0,80}\bpost.{0,80}\b(?:Confluence|Slack|GitHub|Jira|Linear)\b"
    ),
    "no application runs": r"\bno\b.{0,40}\bapplication runs?\b",
    "no test-suite runs": r"\bno\b.{0,40}\btest[- ]suite runs?\b",
    "no source edits except output_path": (
        r"\bno\b.{0,80}\bsource edits?\b.{0,120}\boutput_path\b"
    ),
    "no git mutation": r"\bno\b.{0,40}\bgit mutation\b",
}


@pytest.fixture(scope="module")
def operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/post-mortem-author.md"
    return OPERATOR_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def agents_md_text():
    assert AGENTS_MD_PATH.exists(), "missing AGENTS.md"
    return AGENTS_MD_PATH.read_text(encoding="utf-8")


def _frontmatter_text(text):
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---(?:\n|\Z)", text, re.DOTALL)
    assert match, "operator file must start with YAML frontmatter"
    return match.group("frontmatter")


def _parse_frontmatter(text):
    frontmatter = {}
    for line in _frontmatter_text(text).splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip().strip("'\"")
    return frontmatter


def _operator_body(text):
    match = re.match(r"\A---\n.*?\n---\n(?P<body>.*)\Z", text, re.DOTALL)
    assert match, "operator file must contain a body after frontmatter"
    return match.group("body")


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _routing_row(text):
    pattern = r"(?ms)^- `post-mortem-author`\s+(?:-|—)\s+.*?(?=^\s*-\s+`|^###\s+|\Z)"
    match = re.search(pattern, text)
    assert match, "missing post-mortem-author routing row"
    return match.group(0)


def _allowed_example_fence_spans(text):
    spans = []
    for match in re.finditer(r"(?ms)^```(?P<label>[^\n]*)\n.*?^```", text):
        block = match.group(0).lower()
        label = match.group("label").lower()
        if "example" in label or "historical example" in block:
            spans.append(match.span())
    return spans


def _inside_allowed_example_fence(index, spans):
    return any(start <= index < end for start, end in spans)


def test_frontmatter_keys_exact(operator_text):
    """Risk: A.1 frontmatter shape (HIGH coverage gap; per Step 6a §A.1)"""
    frontmatter = _parse_frontmatter(operator_text)

    assert set(frontmatter) == FRONTMATTER_KEYS, (
        "frontmatter must have exactly description, model, output_format; "
        f"found {sorted(frontmatter)}"
    )


def test_frontmatter_model_claude_opus(operator_text):
    """Risk: A.1 model pin (HIGH coverage gap; per Step 6a §A.1)"""
    frontmatter = _parse_frontmatter(operator_text)

    assert frontmatter.get("model") == "claude-opus", (
        "post-mortem-author must default to model: claude-opus"
    )


def test_frontmatter_output_format_empty(operator_text):
    """Risk: A.1 output format shape (HIGH coverage gap; per Step 6a §A.1)"""
    frontmatter = _parse_frontmatter(operator_text)

    assert frontmatter.get("output_format") == "", (
        "output_format must be the empty string for Markdown output"
    )


def test_frontmatter_description_role_phrasing(operator_text):
    """Risk: A.1 synthesis-only description (HIGH coverage gap; per Step 6a §A.1)"""
    frontmatter = _parse_frontmatter(operator_text)
    description = frontmatter.get("description", "")
    description_lower = description.lower()

    for token in ("findings", "brief", "post-mortem"):
        assert token in description_lower, (
            f"description must mention synthesis input/output token: {token}"
        )
    assert re.search(r"\bsynthesi[sz]e", description_lower), (
        "description must frame the operator as synthesis"
    )
    forbidden_tokens = ("investigation", "ticket", "confluence", "slack", "jira", "linear", "github")
    forbidden_found = [token for token in forbidden_tokens if token in description_lower]
    assert not forbidden_found, (
        "description must not imply investigation, ticketing, or external posting; "
        f"found: {', '.join(forbidden_found)}"
    )


def test_required_body_sections_present_in_order(operator_text):
    """Risk: A.2 operator skeleton drift (HIGH coverage gap; per Step 6a §A.2)"""
    offsets = []
    for heading in REQUIRED_BODY_SECTIONS:
        match = re.search(rf"(?m)^{re.escape(heading)}\s*$", operator_text)
        assert match, f"missing required section heading: {heading}"
        offsets.append(match.start())

    assert offsets == sorted(offsets), (
        "required body sections must appear in contract order"
    )


def test_required_input_tokens_present(operator_text):
    """Risk: A.3 required input compatibility (HIGH coverage gap; per Step 6a §A.3)"""
    required_inputs = _section_after_h2(operator_text, "Required Inputs")

    for token in REQUIRED_INPUT_TOKENS:
        assert re.search(rf"`?{re.escape(token)}`?", required_inputs), (
            f"Required Inputs section must name {token}"
        )


def test_output_contract_section_names_present_in_order(operator_text):
    """Risk: A.4 post-mortem shape drift (HIGH coverage gap; per Step 6a §A.4)"""
    output_contract = _section_after_h2(operator_text, "Output Contract")
    offsets = []

    for section_name in OUTPUT_CONTRACT_SECTION_NAMES:
        offset = output_contract.find(section_name)
        assert offset != -1, (
            f"Output Contract must name post-mortem section: {section_name}"
        )
        offsets.append(offset)

    assert offsets == sorted(offsets), (
        "Output Contract post-mortem sections must appear in contract order"
    )


def test_findings_compatibility_tokens_present(operator_text):
    """Risk: A.5 findings-format compatibility (MEDIUM ambiguity; per Step 6a §A.5)"""
    body = _operator_body(operator_text)
    missing = [token for token in FINDINGS_COMPATIBILITY_TOKENS if token not in body]

    assert not missing, (
        "operator body must preserve incident-investigator findings tokens; "
        f"missing: {', '.join(missing)}"
    )


def test_stop_condition_tokens_present(operator_text):
    """Risk: A.6 stop-condition visibility (MEDIUM ambiguity; per Step 6a §A.6)"""
    stop_conditions = _section_after_h2(operator_text, "Stop Conditions")

    for token in STOP_CONDITION_TOKENS:
        assert token in stop_conditions, (
            f"Stop Conditions section must enumerate {token}"
        )


def test_anti_scope_phrases_present(operator_text):
    """Risk: A.7 synthesis-only side-effect guard (HIGH coverage gap; per Step 6a §A.7)"""
    anti_scope = _section_after_h2(operator_text, "Anti-Scope")
    missing = [
        name
        for name, pattern in ANTI_SCOPE_PATTERNS.items()
        if not re.search(pattern, anti_scope, re.IGNORECASE | re.DOTALL)
    ]

    assert not missing, (
        "Anti-Scope section must unambiguously prohibit required actions; "
        f"missing: {', '.join(missing)}"
    )


def test_no_rfq_hardcode(operator_text):
    """Risk: A.8 reuse-portability hardcode guard (HIGH coverage gap; per Step 6a §A.8)"""
    allowed_spans = _allowed_example_fence_spans(operator_text)
    forbidden_patterns = {
        "RFQ": r"\bRFQ\b",
        "credential-manager": r"credential-manager",
        "2026-05-07": r"2026-05-07",
        "40-character commit SHA": r"\b[0-9a-f]{40}\b",
    }
    violations = []
    for name, pattern in forbidden_patterns.items():
        for match in re.finditer(pattern, operator_text, re.IGNORECASE):
            if not _inside_allowed_example_fence(match.start(), allowed_spans):
                violations.append(name)

    assert not violations, (
        "operator must not hardcode RFQ or incident-specific tokens outside "
        f"explicit example fences; found: {', '.join(sorted(set(violations)))}"
    )


def test_agents_md_routing_subsection_ordering(agents_md_text):
    """Risk: B.1 AGENTS subsection placement (MEDIUM routing ambiguity; per Step 6a §B.1)"""
    coverage_heading = "### Coverage / behavior / test authoring"
    incident_heading = "### Incident / RCA"
    pr_heading = "### PR review / justification"

    coverage_offset = agents_md_text.find(coverage_heading)
    incident_offset = agents_md_text.find(incident_heading)
    pr_offset = agents_md_text.find(pr_heading)

    assert coverage_offset != -1, f"missing AGENTS heading: {coverage_heading}"
    assert incident_offset != -1, f"missing AGENTS heading: {incident_heading}"
    assert pr_offset != -1, f"missing AGENTS heading: {pr_heading}"
    assert coverage_offset < incident_offset < pr_offset, (
        "### Incident / RCA must appear after coverage/test authoring and before PR review"
    )


def test_agents_md_routing_row_present(agents_md_text):
    """Risk: B.2 routing discoverability (HIGH coverage gap; per Step 6a §B.2)"""
    row = _routing_row(agents_md_text)

    assert re.search(r"(?m)^- `post-mortem-author`\s+(?:-|—)\s+", row), (
        "AGENTS.md must contain a post-mortem-author routing row"
    )


def test_agents_md_routing_row_file_link(agents_md_text):
    """Risk: B.2 routing file-link grammar (HIGH coverage gap; per Step 6a §B.2)"""
    row = _routing_row(agents_md_text)

    assert re.search(
        r"(?m)^\s*File:\s+\[~/ai/agents/post-mortem-author\.md\]"
        r"\(agents/post-mortem-author\.md\)\s*$",
        row,
    ), "post-mortem-author row must link to agents/post-mortem-author.md"


def test_agents_md_routing_row_input_tokens(agents_md_text):
    """Risk: B.2 routing input-token drift (HIGH coverage gap; per Step 6a §B.2)"""
    row = _routing_row(agents_md_text)
    match = re.search(r"(?m)^\s*Inputs:\s*(?P<inputs>.+?)\s*$", row)
    assert match, "post-mortem-author row must include an Inputs: line"

    input_tokens = [
        token.strip().strip("`")
        for token in match.group("inputs").split(",")
        if token.strip()
    ]
    assert input_tokens == list(REQUIRED_INPUT_TOKENS), (
        "post-mortem-author row must list exactly findings_path, "
        f"incident_brief_path, output_path; found: {input_tokens}"
    )


def test_agents_md_routing_row_model(agents_md_text):
    """Risk: B.2 routing model-token drift (HIGH coverage gap; per Step 6a §B.2)"""
    row = _routing_row(agents_md_text)

    assert re.search(r"(?m)^\s*Model:\s+claude-opus\s*$", row), (
        "post-mortem-author row must declare Model: claude-opus"
    )
