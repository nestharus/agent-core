"""Structural tests for the NES-276 incident-investigator operator."""

import re
from pathlib import Path


OPERATOR_RELATIVE_PATH = Path("agents/incident-investigator.md")
AGENTS_RELATIVE_PATH = Path("AGENTS.md")
RFQ_INCIDENT_SLUG = "2026-05-07-credential-manager"
REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_SECTION_GROUPS = (
    ("Role",),
    ("Use When",),
    ("Do Not Use When",),
    ("Required Inputs", "Inputs"),
    ("Procedure",),
    ("Output Contract",),
    ("Anti-Scope", "Anti-scope"),
    ("Stop Conditions", "Stop conditions"),
)
REQUIRED_INPUTS = (
    ("incident_brief_path", "required"),
    ("evidence_dir", "required"),
    ("repo_root", "required"),
    ("findings_path", "optional"),
)
PROCEDURE_TOKENS = (
    "evidence",
    "file:line",
    "git show",
    "git log",
    "git diff",
    "git blame",
    "unverifiable from code alone",
)
OUTPUT_CONTRACT_TOKENS = (
    "findings.md",
    "confirmed",
    "probable",
    "unverified",
    "causal",
    "contributing",
    "incidental",
    "confidence",
    "caveats",
    "stdout",
    "WROTE:",
)
ROUTING_INPUT_TOKENS = (
    "incident_brief_path",
    "evidence_dir",
    "repo_root",
    "findings_path?",
)


def _operator_path(repo_root):
    return repo_root / OPERATOR_RELATIVE_PATH


def _operator_text(repo_root):
    path = _operator_path(repo_root)
    assert path.exists(), f"missing {OPERATOR_RELATIVE_PATH}"
    return path.read_text(encoding="utf-8")


def _agents_text(repo_root):
    path = repo_root / AGENTS_RELATIVE_PATH
    assert path.exists(), f"missing {AGENTS_RELATIVE_PATH}"
    return path.read_text(encoding="utf-8")


def _frontmatter_match(text):
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    assert match, "operator file must start with YAML frontmatter"
    return match


def _parse_frontmatter(text):
    frontmatter = {}
    for line in _frontmatter_match(text).group("body").splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip().strip("'\"")
    return frontmatter


def _body_without_frontmatter(text):
    return text[_frontmatter_match(text).end() :]


def _heading_pattern(heading_options):
    return "|".join(re.escape(heading) for heading in heading_options)


def _find_h2(text, heading_options):
    pattern = rf"(?m)^##\s+(?:{_heading_pattern(heading_options)})\s*$"
    match = re.search(pattern, text)
    assert match, (
        "missing section heading: "
        + " or ".join(f"## {heading}" for heading in heading_options)
    )
    return match


def _section_after_h2(text, heading_options):
    match = _find_h2(text, heading_options)
    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    return following[: next_h1_or_h2.start()] if next_h1_or_h2 else following


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    heading_level = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{heading_level}}}\s+", following)
    return following[: next_heading.start()] if next_heading else following


def _h3_subsection(section, heading):
    match = re.search(rf"(?m)^###\s+{re.escape(heading)}\s*$", section)
    assert match, f"missing subsection heading: ### {heading}"
    following = section[match.end() :]
    next_h3 = re.search(r"(?m)^###\s+", following)
    return following[: next_h3.start()] if next_h3 else following


def _assert_contains_literal(text, token):
    assert re.search(re.escape(token), text), f"missing token: {token}"


def _assert_contains_literal_ci(text, token):
    assert re.search(re.escape(token), text, re.IGNORECASE), f"missing token: {token}"


def _assert_bullet_line_contains(section, token):
    assert re.search(rf"(?m)^\s*[-*]\s+.*{re.escape(token)}", section), (
        f"missing bullet containing {token}"
    )


def test_operator_file_exists_and_is_non_trivial(repo_root):
    """Schema 1: the incident-investigator operator file exists and is substantive."""
    path = _operator_path(repo_root)

    assert path.exists(), f"missing {OPERATOR_RELATIVE_PATH}"
    assert len(path.read_text(encoding="utf-8").encode("utf-8")) >= 500


def test_operator_frontmatter_contract(repo_root):
    """Schema 1: frontmatter has the exact keys, model, output format, and description tokens."""
    text = _operator_text(repo_root)
    frontmatter = _parse_frontmatter(text)
    description = frontmatter["description"]

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["model"] == "gpt-high"
    assert frontmatter["output_format"] == ""
    assert description
    assert re.search(r"\bincident\b", description, re.IGNORECASE)
    assert re.search(r"\binvestigat(?:e|ion)\b", description, re.IGNORECASE)
    assert re.search(r"\bevidence\b", description, re.IGNORECASE)
    assert re.search(
        r"\bread[- ]only\b|\bno[- ]mutation\b|\bwithout\s+mutating\b",
        description,
        re.IGNORECASE,
    )
    assert RFQ_INCIDENT_SLUG not in description
    assert "credential-manager" not in description.lower()
    assert "rfq" not in description.lower()


def test_operator_required_body_sections(repo_root):
    """Schema 1: the body title, sections, role content, bullets, and ordered procedure exist."""
    text = _operator_text(repo_root)
    body = _body_without_frontmatter(text)
    first_body_line = next(line for line in body.splitlines() if line.strip())

    assert first_body_line == "# Incident Investigator"

    offsets = {}
    for heading_options in REQUIRED_SECTION_GROUPS:
        match = _find_h2(text, heading_options)
        offsets[heading_options[0]] = match.start()

    assert offsets["Role"] < offsets["Procedure"]
    assert offsets["Role"] < offsets["Output Contract"]

    role = _section_after_h2(text, ("Role",))
    role_paragraphs = [block.strip() for block in re.split(r"\n\s*\n", role) if block.strip()]
    assert 1 <= len(role_paragraphs) <= 2
    assert re.search(r"\bincident\b", role, re.IGNORECASE)
    assert re.search(r"\binvestigat(?:e|ion)\b", role, re.IGNORECASE)
    assert re.search(r"\bread[- ]only\b|\bwithout\s+mutat", role, re.IGNORECASE)

    for heading_options in (
        ("Use When",),
        ("Do Not Use When",),
        ("Required Inputs", "Inputs"),
        ("Anti-Scope", "Anti-scope"),
    ):
        section = _section_after_h2(text, heading_options)
        assert re.search(r"(?m)^\s*[-*]\s+", section), (
            "expected a bulleted list in "
            + " or ".join(f"## {heading}" for heading in heading_options)
        )

    procedure = _section_after_h2(text, ("Procedure",))
    assert re.search(r"(?m)^\s*\d+\.\s+", procedure), (
        "Procedure must use numbered or ordered steps"
    )


def test_operator_required_inputs_tokens(repo_root):
    """Schema 1: Required Inputs names required/optional input tokens and the findings default."""
    inputs = _section_after_h2(_operator_text(repo_root), ("Required Inputs", "Inputs"))

    for token, requirement in REQUIRED_INPUTS:
        _assert_bullet_line_contains(inputs, token)
        assert re.search(
            rf"(?im)^\s*[-*]\s+[^\n]*{re.escape(token)}[^\n]*"
            rf"\b{re.escape(requirement)}\b",
            inputs,
        ), f"{token} bullet must mark {requirement}"

    _assert_contains_literal(inputs, "${evidence_dir}/findings.md")


def test_operator_procedure_tokens(repo_root):
    """Schema 1: Procedure encodes read order, hypothesis testing, evidence, git, and caveats."""
    procedure = _section_after_h2(_operator_text(repo_root), ("Procedure",))

    assert re.search(
        r"read.{0,80}brief.{0,80}first|read\s+the\s+(?:incident\s+)?brief",
        procedure,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(r"\bhypothes(?:is|es)\b", procedure, re.IGNORECASE)
    assert re.search(r"\bevery\s+(?:open\s+)?question\b", procedure, re.IGNORECASE)
    for token in PROCEDURE_TOKENS:
        _assert_contains_literal_ci(procedure, token)


def test_operator_output_contract_tokens(repo_root):
    """Schema 1: Output Contract names the required findings schema and vocabularies."""
    output_contract = _section_after_h2(_operator_text(repo_root), ("Output Contract",))

    assert re.search(r"\bexecutive\s+summary\b", output_contract, re.IGNORECASE)
    assert re.search(r"\brecommended\s+actions\b", output_contract, re.IGNORECASE)
    for token in OUTPUT_CONTRACT_TOKENS:
        _assert_contains_literal_ci(output_contract, token)


def test_operator_anti_scope_tokens(repo_root):
    """Schema 1: Anti-Scope forbids mutation, execution, ticketing, posting, and logins."""
    anti_scope = _section_after_h2(_operator_text(repo_root), ("Anti-Scope", "Anti-scope"))

    assert re.search(r"\b(?:code|source)\s+edits?\b", anti_scope, re.IGNORECASE)
    assert re.search(r"\bcommits?\b", anti_scope, re.IGNORECASE)
    for git_operation in ("checkout", "reset", "rebase", "push"):
        _assert_contains_literal_ci(anti_scope, git_operation)
    assert re.search(r"\b(?:application|app)\s+runs?\b", anti_scope, re.IGNORECASE)
    assert re.search(r"\btest[- ]suite\s+runs?\b", anti_scope, re.IGNORECASE)
    assert re.search(r"\bticket\s+transitions?\b", anti_scope, re.IGNORECASE)
    assert re.search(
        r"\bexternal\s+posting\b|"
        r"(?=.*\bConfluence\b)(?=.*\bSlack\b)(?=.*\bJira\b)"
        r"(?=.*\bLinear\b)(?=.*\bGitHub\b)",
        anti_scope,
        re.IGNORECASE | re.DOTALL,
    )
    assert re.search(r"\bexternal[- ]system\s+logins?\b", anti_scope, re.IGNORECASE)


def test_operator_stop_conditions_tokens(repo_root):
    """Schema 1: Stop Conditions contains BLOCKED, NEEDS_INPUT, and WROTE sentinels."""
    stop_conditions = _section_after_h2(
        _operator_text(repo_root),
        ("Stop Conditions", "Stop conditions"),
    )

    assert re.search(r"BLOCKED:\s*(?:<[^>]+>|\{[^}]+\}|[A-Za-z_]+)", stop_conditions)
    assert re.search(r"NEEDS_INPUT:\s*(?:<[^>]+>|\{[^}]+\}|[A-Za-z_]+)", stop_conditions)
    assert re.search(r"WROTE:\s*(?:<[^>]+>|\{[^}]+\}|[A-Za-z_]+)", stop_conditions)


def test_agents_md_incident_rca_subsection_present(repo_root):
    """Schema 2: AGENTS.md registers incident-investigator in the Incident / RCA subsection."""
    agents_text = _agents_text(repo_root)
    operator_routing = _section_after_heading(agents_text, "## Operator Routing Table")
    coverage_match = re.search(
        rf"(?m)^###\s+{re.escape('Coverage / behavior / test authoring')}\s*$",
        operator_routing,
    )
    incident_match = re.search(
        rf"(?m)^###\s+{re.escape('Incident / RCA')}\s*$",
        operator_routing,
    )
    pr_match = re.search(
        rf"(?m)^###\s+{re.escape('PR review / justification')}\s*$",
        operator_routing,
    )

    assert coverage_match, "missing Coverage / behavior / test authoring subsection"
    assert incident_match, "missing Incident / RCA subsection"
    assert pr_match, "missing PR review / justification subsection"
    assert coverage_match.start() < incident_match.start() < pr_match.start()

    incident_section = _h3_subsection(operator_routing, "Incident / RCA")
    row_match = re.search(
        r"(?ms)^- `incident-investigator`\s+(?:-|\u2014)\s+.+?"
        r"^\s+File:\s+.*?(?=^- `|\Z)",
        incident_section,
    )
    assert row_match, "missing parser-compatible incident-investigator routing row"
    row = row_match.group(0)

    _assert_contains_literal(row, "incident-investigator")
    _assert_contains_literal(row, "agents/incident-investigator.md")
    for token in ROUTING_INPUT_TOKENS:
        _assert_contains_literal(row, token)
    assert re.search(r"Model:\s*`gpt-high`", row), "routing row must name Model: `gpt-high`"


def test_consolidation_discipline_no_rfq_hardcode(repo_root):
    """Schema 1: RFQ is source-shape context only, and suspect commits can be not applicable."""
    text = _operator_text(repo_root)
    text_lower = text.lower()

    assert RFQ_INCIDENT_SLUG not in text
    assert re.search(r"\bRFQ\b", text)
    assert re.search(
        r"\b(?:historical|source[- ]of[- ]shape|inspiration|example)\b",
        text,
        re.IGNORECASE,
    )
    assert "not applicable" in text_lower
    assert re.search(r"suspect[- ]commit|suspect commits?", text, re.IGNORECASE)


def test_test_module_stays_structural_and_local(repo_root):
    """Schema 3: this pytest module stays read-only, local, and free of dispatch machinery."""
    source = (repo_root / "tests" / "test_incident_investigator_operator.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = (
        "sub" + "process",
        "requests",
        "urllib",
        "socket",
        "httpx",
    )

    assert "read_text(encoding=\"utf-8\")" in source
    for module_name in forbidden_imports:
        assert not re.search(rf"(?m)^\s*(?:import|from)\s+{re.escape(module_name)}\b", source)
    assert not re.search(r"(?m)^\s*pytest\.main\(", source)
    assert not re.search(r"(?m)^\s*agents\s+-", source)
