import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
JIRA_OPERATOR = REPO_ROOT / "agents" / "jira-operator.md"


def _operator_text():
    return JIRA_OPERATOR.read_text(encoding="utf-8")


def _h2_headings(text):
    return re.findall(r"(?m)^##\s+(.+?)\s*$", text)


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^##\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _error_handling_section():
    return _section_after_heading(_operator_text(), "## Error Handling")


def _non_example_lines(section):
    lines = []
    in_fence = False
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith((">", "~~")):
            continue
        lines.append(stripped)
    return lines


def test_error_handling_section_exists_exactly_once():
    assert _h2_headings(_operator_text()).count("Error Handling") == 1


def test_error_handling_envelope_tokens_present():
    section = _error_handling_section()
    assert "BLOCKED: JIRA" in section
    assert "returned HTTP" in section


def test_error_handling_response_body_label_present():
    assert "Response body:" in _error_handling_section()


def test_error_handling_verbatim_word_present():
    section = _error_handling_section()
    assert re.search(r"(?is)Response body:.{0,300}\bverbatim\b", section) or re.search(
        r"(?is)\bverbatim\b.{0,300}Response body:", section
    )


def test_error_handling_wrong_shape_example_present():
    section = _error_handling_section()
    assert re.search(
        r"(?is)\bwrong(?:\s+shape)?\b.*?^BLOCKED:.*?\blacks permission\b",
        section,
        re.MULTILINE,
    )


def test_error_handling_right_shape_envelope_example_present():
    section = _error_handling_section()
    assert re.search(
        r"(?is)\bright(?:\s+shape)?\b.*?"
        r"^BLOCKED: JIRA [A-Z]+ /[^\n]+ returned HTTP \d{3}\s*"
        r".*?Response body:",
        section,
        re.MULTILINE,
    )


def test_error_handling_prohibition_statement_present():
    section = _error_handling_section()
    sentences = re.findall(
        r"(?is)(?:^|[.!?]\s+)([^.!?]*(?:MUST\s+NOT|must\s+not)[^.!?]*)",
        section,
    )
    assert any(
        "probe" in sentence.lower()
        and (
            "higher-level" in sentence.lower()
            or "diagnos" in sentence.lower()
            or "classification" in sentence.lower()
            or "cause" in sentence.lower()
        )
        for sentence in sentences
    )


def test_error_handling_canonical_probe_named():
    assert "GET /rest/api/3/myself" in _error_handling_section()


def test_error_handling_probe_example_present():
    section = _error_handling_section()
    assert re.search(
        r"(?is)\bwith probe\b.*?"
        r"^BLOCKED: JIRA [A-Z]+ /[^\n]+ returned HTTP \d{3}\s*"
        r".*?Response body:.*?"
        r"GET /rest/api/3/myself.*?HTTP \d{3}",
        section,
        re.MULTILINE,
    )


def test_create_procedure_no_bare_400_403_404_instruction():
    section = _section_after_heading(_operator_text(), "## Procedure: Create")
    stale_instruction_lines = [
        line
        for line in _non_example_lines(section)
        if re.match(r"^Surface BLOCKED on 400/403/404\b", line)
    ]
    assert stale_instruction_lines == []


def test_create_procedure_references_error_handling():
    section = _section_after_heading(_operator_text(), "## Procedure: Create")
    assert re.search(r"Error Handling|## Error Handling|envelope rule", section)


def test_output_contract_global_failure_clause_references_envelope():
    section = _section_after_heading(_operator_text(), "## Output Contract")
    assert re.search(r"(?is)(any Jira REST 4xx|4xx|failure).*?(Error Handling|envelope)", section)


def test_stop_conditions_references_error_handling_for_http():
    section = _section_after_heading(_operator_text(), "## Stop Conditions")
    assert re.search(r"(?is)(HTTP|401|4xx|404|issue key).*?(Error Handling|envelope)", section)


def test_frontmatter_keys_exact():
    text = _operator_text()
    match = re.match(r"(?s)^---\n(.*?)\n---\n", text)
    assert match, "missing YAML frontmatter block"
    keys = []
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", line)
        assert key_match, f"frontmatter line does not declare a simple key: {line}"
        keys.append(key_match.group(1))
    assert keys == ["description", "model", "output_format"]


def test_required_h2s_present():
    headings = set(_h2_headings(_operator_text()))
    for heading in (
        "Use When",
        "Do Not Use When",
        "Required Inputs",
        "Output Contract",
        "Stop Conditions",
    ):
        assert heading in headings, f"missing required H2: {heading}"


def test_no_duplicate_h2_names():
    headings = _h2_headings(_operator_text())
    duplicates = sorted({heading for heading in headings if headings.count(heading) > 1})
    assert duplicates == []


def test_no_lacks_permission_in_callers():
    matches = []
    for root_name in ("agents", "workflows", "conventions"):
        root = REPO_ROOT / root_name
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative_path = path.relative_to(REPO_ROOT)
            if relative_path == Path("agents/jira-operator.md"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if "lacks permission" in line:
                    matches.append(f"{relative_path}:{line_number}: {line.strip()}")
    assert matches == []
