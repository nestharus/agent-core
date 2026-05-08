import re
from pathlib import Path


JIRA_OPERATOR = (
    Path(__file__).resolve().parent.parent / "agents" / "jira-operator.md"
)
ALLOWED_ESTIMATE_VALUES = "1, 2, 3, 5, 8, 13, 21, 40, 100"


def _read_jira_operator() -> str:
    return JIRA_OPERATOR.read_text(encoding="utf-8")


def _h2_section(text: str, heading: str) -> str:
    match = re.search(r"(?m)^## " + re.escape(heading) + r"\s*$", text)
    assert match, f"missing H2 section: {heading}"
    following = text[match.end() :]
    next_h2 = re.search(r"(?m)^## ", following)
    if next_h2:
        return following[: next_h2.start()]
    return following


def _markdown_section_containing(text: str, needle: str) -> str:
    position = text.find(needle)
    assert position != -1, f"missing required text: {needle}"

    heading_matches = list(re.finditer(r"(?m)^#{2,3} .*$", text))
    section_start = 0
    section_end = len(text)

    for index, heading_match in enumerate(heading_matches):
        if heading_match.start() <= position:
            section_start = heading_match.start()
            if index + 1 < len(heading_matches):
                section_end = heading_matches[index + 1].start()
        else:
            break

    return text[section_start:section_end]


def _markdown_sections_containing(text: str, needle: str) -> list[str]:
    sections = []
    start = 0
    while True:
        position = text.find(needle, start)
        if position == -1:
            break
        sections.append(_markdown_section_containing(text, needle))
        start = position + len(needle)
    assert sections, f"missing required text: {needle}"
    return sections


def _has_reject_before_payload_rule(section: str, payload_terms: tuple[str, ...]) -> bool:
    payload_pattern = "|".join(re.escape(term) for term in payload_terms)
    pattern = (
        r"(?is)\breject(?:s|ed|ing)?\b.{0,200}"
        r"\b(?:before|prior to)\b.{0,200}\b(?:"
        + payload_pattern
        + r")\b"
    )
    return bool(
        re.search(pattern, section)
    )


def test_allowed_estimate_values_listed_in_jira_operator() -> None:
    assert ALLOWED_ESTIMATE_VALUES in _read_jira_operator()


def test_jira_operator_cross_references_linear_validation_source() -> None:
    allowed_values_sections = _markdown_sections_containing(
        _read_jira_operator(), ALLOWED_ESTIMATE_VALUES
    )

    assert any(
        "clients/linear/client.py" in section
        and ("ALLOWED_ESTIMATES" in section or "_validate_estimate" in section)
        and re.search(
            r"(?is)cross-backend|source of truth|Linear validation source",
            section,
        )
        for section in allowed_values_sections
    )


def test_create_rejects_invalid_estimates_before_payload() -> None:
    create_section = _h2_section(_read_jira_operator(), "Procedure: Create")

    assert "customfield_10016" in create_section
    assert _has_reject_before_payload_rule(
        create_section,
        ("REST payload", "POST", "payload"),
    )


def test_update_estimate_rejects_invalid_estimates_before_payload() -> None:
    update_section = _h2_section(_read_jira_operator(), "Procedure: Update Estimate")

    assert "customfield_10016" in update_section
    assert _has_reject_before_payload_rule(
        update_section,
        ("PUT", "REST payload", "payload"),
    )
    assert not re.search(
        r"(?is)validation remains outside (?:this|the) operator(?:'s)? task",
        update_section,
    )
    assert not re.search(
        r"(?is)Layer 4 decides.{0,120}this operator does not validate",
        update_section,
    )
