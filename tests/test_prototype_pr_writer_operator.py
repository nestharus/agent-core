import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR = REPO_ROOT / "agents" / "prototype-pr-writer.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"

REQUIRED_FRONTMATTER_KEYS = ("description", "model", "output_format")
REQUIRED_H2_SECTIONS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Output Body Structure",
    "Procedure",
    "Stop Conditions",
)
REQUIRED_INPUTS = (
    "truth_branch_ref",
    "proposal_path",
    "behavior_tests_paths",
    "test_results",
    "qa_walkthrough_report_path",
    "qa_screenshots_dir",
    "deliverable_paths",
)
OUTPUT_BODY_SECTIONS = (
    "Use-cases / expectations being shipped",
    "Per-use-case proof bundle",
    "Test summary",
    "Deliverable + PR attachments",
    "Anti-scope reminder",
    "What this PR is NOT",
)
PROOF_BUNDLE_TOKENS = (
    "Behavior",
    "Test proof",
    "Visual proof",
    "inline in the PR description body",
    "GitHub",
    "user-attachments",
    "NOT committed to the truth branch",
    "caption",
    "action triggered",
    "expected vs observed",
    "Observed vs expected",
)
DELIVERABLE_TOKENS = (
    "docker-compose.yml",
    "README.md",
    "docker compose up -d",
    "docker compose down",
    "registry image tag",
    "zip",
    "download link",
    "asset-attachment fallback",
    "fenced code block",
)
FORBIDDEN_MACHINE_ENFORCEMENT_PHRASES = (
    "machine-enforced",
    "machine enforcement",
    "automated enforcement of",
)

_OPERATOR_TEXT = None
_AGENTS_TEXT = None


def _operator_text():
    global _OPERATOR_TEXT
    assert OPERATOR.exists(), "missing operator file token: agents/prototype-pr-writer.md"
    if _OPERATOR_TEXT is None:
        _OPERATOR_TEXT = OPERATOR.read_text(encoding="utf-8")
    return _OPERATOR_TEXT


def _agents_text():
    global _AGENTS_TEXT
    assert AGENTS_MD.exists(), "missing AGENTS.md token"
    if _AGENTS_TEXT is None:
        _AGENTS_TEXT = AGENTS_MD.read_text(encoding="utf-8")
    return _AGENTS_TEXT


def _parse_frontmatter(text):
    match = re.match(r"\A---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    assert match, "missing frontmatter fence token: ---"

    values = {}
    for line in match.group("body").splitlines():
        if not line.strip():
            continue
        assert ":" in line, f"malformed frontmatter line token: {line}"
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _h2_headings(text):
    return [match.group(1).strip() for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", text)]


def _h2_section(text, *headings):
    heading_set = set(headings)
    for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", text):
        if match.group(1).strip() not in heading_set:
            continue
        following = text[match.end() :]
        next_h2 = re.search(r"(?m)^##\s+", following)
        if next_h2:
            return following[: next_h2.start()]
        return following
    wanted = " or ".join(f"## {heading}" for heading in headings)
    raise AssertionError(f"missing H2 section token: {wanted}")


def _h2_offset(text, heading):
    match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
    assert match, f"missing H2 section token: ## {heading}"
    return match.start()


def _assert_contains(text, token, *, label):
    assert token.lower() in text.lower(), f"missing {label} token: {token}"


def _output_body_section():
    return _h2_section(_operator_text(), "Output Body Structure")


def _output_body_subsection(token):
    section = _output_body_section()
    section_lower = section.lower()
    start = section_lower.find(token.lower())
    assert start != -1, f"missing output-body subsection token: {token}"

    following_offsets = [
        section_lower.find(next_token.lower())
        for next_token in OUTPUT_BODY_SECTIONS
        if section_lower.find(next_token.lower()) > start
    ]
    end = min(following_offsets) if following_offsets else len(section)
    return section[start:end]


def test_operator_file_exists():
    assert OPERATOR.exists(), "missing operator file token: agents/prototype-pr-writer.md"


def test_frontmatter_keys():
    frontmatter = _parse_frontmatter(_operator_text())

    for key in REQUIRED_FRONTMATTER_KEYS:
        assert key in frontmatter, f"missing frontmatter key token: {key}"
    assert frontmatter.get("model") == "claude-opus", (
        "missing frontmatter model token: claude-opus"
    )


def test_required_h2_sections_present():
    headings = _h2_headings(_operator_text())

    for heading in REQUIRED_H2_SECTIONS:
        assert heading in headings, f"missing H2 section token: ## {heading}"
    assert "Required Inputs" in headings or "Inputs" in headings, (
        "missing H2 section token: ## Required Inputs or ## Inputs"
    )


def test_h2_section_order():
    text = _operator_text()

    output_body = _h2_offset(text, "Output Body Structure")
    procedure = _h2_offset(text, "Procedure")
    stop_conditions = _h2_offset(text, "Stop Conditions")
    assert output_body < procedure, "out-of-order H2 token: Output Body Structure"
    assert procedure < stop_conditions, "out-of-order H2 token: Procedure"


def test_required_inputs_enumerated():
    inputs_section = _h2_section(_operator_text(), "Required Inputs", "Inputs")

    for token in REQUIRED_INPUTS:
        _assert_contains(inputs_section, token, label="required-input")


def test_output_body_six_sections_in_order():
    section = _output_body_section()
    section_lower = section.lower()
    previous_offset = -1

    for token in OUTPUT_BODY_SECTIONS:
        offset = section_lower.find(token.lower())
        assert offset != -1, f"missing output-body token: {token}"
        assert offset > previous_offset, f"out-of-order output-body token: {token}"
        previous_offset = offset


def test_proof_bundle_tokens():
    proof_bundle = _output_body_subsection("Per-use-case proof bundle")

    for token in PROOF_BUNDLE_TOKENS:
        _assert_contains(proof_bundle, token, label="proof-bundle")


def test_deliverable_tokens():
    deliverables = _output_body_subsection("Deliverable + PR attachments")

    for token in DELIVERABLE_TOKENS:
        _assert_contains(deliverables, token, label="deliverable")


def test_anti_scope_tokens():
    anti_scope = _h2_section(_operator_text(), "Do Not Use When")

    no_code_walkthrough = re.search(
        r"(?is)\b(no|not|never|forbid|forbids|forbidden|without|avoid)\b.{0,80}"
        r"\bcode[- ]walkthrough\b|"
        r"\bcode[- ]walkthrough\b.{0,80}"
        r"\b(no|not|never|forbid|forbids|forbidden|without|avoid)\b",
        anti_scope,
    )
    assert no_code_walkthrough, "missing anti-scope token: no code-walkthrough"
    _assert_contains(anti_scope, "CodeRabbit", label="anti-scope")
    _assert_contains(anti_scope, "NOT committed to the truth branch", label="anti-scope")
    _assert_contains(anti_scope, "pr-writer.md", label="anti-scope")


def test_stop_conditions_tokens():
    stop_conditions = _h2_section(_operator_text(), "Stop Conditions")

    _assert_contains(stop_conditions, "BLOCKED:", label="stop-conditions")
    _assert_contains(stop_conditions, "PR URL", label="stop-conditions")


def test_no_machine_enforcement_framing():
    text = _operator_text().lower()

    for token in FORBIDDEN_MACHINE_ENFORCEMENT_PHRASES:
        assert token not in text, f"forbidden machine-enforcement token present: {token}"


def test_agents_md_routing_row_present():
    match = re.search(r"(?ms)^- `prototype-pr-writer` - .*?(?=^- `|\Z)", _agents_text())
    assert match, "missing AGENTS.md routing row token: prototype-pr-writer"
    row = match.group(0)

    _assert_contains(row, "prototype-pr-writer.md", label="AGENTS.md routing-row")
    assert re.search(r"(?i)shippable[- ]prototype", row), (
        "missing AGENTS.md routing-row token: shippable-prototype"
    )
    _assert_contains(row, "proof", label="AGENTS.md routing-row")
    _assert_contains(row, "PR writer", label="AGENTS.md routing-row")
