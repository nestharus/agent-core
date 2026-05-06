import re
from dataclasses import dataclass


"""
Risk annotation: verifies proposal §5 deterministic body-shape risk at unit
level. Fixture source is literal Markdown/title strings applied directly to the
local validator; no agents CLI, gh, Linear API, or LLM dispatch is used.
Assumptions covered: A1, A3, A5, A7.
"""


CLOSE_KEYWORD_RE = re.compile(r"\bCloses\s+[A-Z][A-Z0-9]+-\d+\b")
LINEAR_FIXTURE_KEY_RE = re.compile(r"^NES-\d+$")
FORBIDDEN_SECTION_RE = re.compile(
    r"(?im)^\s*#{1,6}\s+(Tickets?|Issues?|Linear|References)\b"
)
BASE_TITLE = "docs: update PR writer guidance"
TITLE_WITH_CLOSE = "docs: update PR writer guidance Closes NES-204"
KEY_NES_204 = "NES-204"
KEY_NES_205 = "NES-205"
KEY_JIRA_PROJ = "PROJ-123"
BODY_WITH_SINGLE_FOOTER = "## Verification\n\npytest tests\n\nCloses NES-204"
BODY_WITH_MULTIPLE_FOOTERS = (
    "## Verification\n\npytest tests\n\nCloses NES-204\nCloses NES-205"
)
BODY_HEADING_CLOSE = "## Verification\n\n# Closes NES-204"
BODY_FENCED_CODE_CLOSE = "## Verification\n\n```\nCloses NES-204\n```"
BODY_INDENTED_CODE_CLOSE = "## Verification\n\n    Closes NES-204"
BODY_BLOCKQUOTE_CLOSE = "## Verification\n\n> Closes NES-204"
BODY_LIST_CLOSE = "## Verification\n\n- Closes NES-204"
BODY_TABLE_CLOSE = "## Verification\n\n| Closes NES-204 |"
BODY_HTML_COMMENT_CLOSE = "## Verification\n\n<!-- Closes NES-204 -->"
BODY_TICKETS_SECTION_CLOSE = "## Tickets\n\nCloses NES-204"
BODY_WITHOUT_FOOTER = "## Verification\n\npytest tests"
BODY_TRAILING_PUNCTUATION_CLOSE = "## Verification\n\npytest tests\n\nCloses NES-204."
BODY_MARKDOWN_LINK_CLOSE = (
    "## Verification\n\npytest tests\n\n[Closes NES-204](https://linear.app)"
)


@dataclass(frozen=True)
class ContractResult:
    valid: bool
    expected_close_lines: tuple[str, ...]
    emitted_close_lines: tuple[str, ...]


def _normalized_linear_keys(linear_issue_keys):
    keys = []
    seen = set()
    for raw_key in linear_issue_keys:
        key = str(raw_key).strip().upper()
        if not LINEAR_FIXTURE_KEY_RE.fullmatch(key):
            continue
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return tuple(keys)


def _has_close_keyword_in_html_comment(body):
    return bool(re.search(r"<!--(?s:.*?)\bCloses\s+[A-Z][A-Z0-9]+-\d+\b(?s:.*?)-->", body))


def _has_forbidden_close_keyword_placement(body):
    in_fenced_code = False
    for line in body.splitlines():
        stripped = line.strip()
        contains_close_keyword = bool(CLOSE_KEYWORD_RE.search(line))
        if stripped.startswith("```"):
            in_fenced_code = not in_fenced_code
            continue
        if not contains_close_keyword:
            continue
        left_stripped = line.lstrip()
        if in_fenced_code:
            return True
        if line.startswith(("    ", "\t")):
            return True
        if left_stripped.startswith("#"):
            return True
        if left_stripped.startswith(">"):
            return True
        if re.match(r"^\s*(?:[-*+]|\d+\.)\s+", line):
            return True
        if "|" in line:
            return True
    return _has_close_keyword_in_html_comment(body)


def _validate_pr_body(title, body, linear_issue_keys):
    expected_close_lines = tuple(
        f"Closes {key}" for key in _normalized_linear_keys(linear_issue_keys)
    )
    emitted_close_lines = tuple(
        line for line in body.splitlines() if line in expected_close_lines
    )

    if CLOSE_KEYWORD_RE.search(title):
        return ContractResult(False, expected_close_lines, emitted_close_lines)
    if FORBIDDEN_SECTION_RE.search(body):
        return ContractResult(False, expected_close_lines, emitted_close_lines)
    if _has_forbidden_close_keyword_placement(body):
        return ContractResult(False, expected_close_lines, emitted_close_lines)

    lines = body.rstrip("\n").splitlines()
    if not expected_close_lines:
        valid = not CLOSE_KEYWORD_RE.search(body)
        return ContractResult(valid, expected_close_lines, emitted_close_lines)

    if len(lines) < len(expected_close_lines):
        return ContractResult(False, expected_close_lines, emitted_close_lines)

    footer_start = len(lines) - len(expected_close_lines)
    footer = tuple(lines[footer_start:])
    if footer != expected_close_lines:
        return ContractResult(False, expected_close_lines, emitted_close_lines)
    if len(emitted_close_lines) != len(expected_close_lines):
        return ContractResult(False, expected_close_lines, emitted_close_lines)
    if footer_start > 0 and lines[footer_start - 1] != "":
        return ContractResult(False, expected_close_lines, emitted_close_lines)

    return ContractResult(True, expected_close_lines, emitted_close_lines)


def test_standalone_close_line_accepted():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITH_SINGLE_FOOTER,
        [KEY_NES_204],
    )

    assert result.valid
    assert result.emitted_close_lines == ("Closes NES-204",)


def test_multiple_keys_each_on_own_line():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITH_MULTIPLE_FOOTERS,
        [KEY_NES_204, KEY_NES_205],
    )

    assert result.valid
    assert result.emitted_close_lines == ("Closes NES-204", "Closes NES-205")


def test_close_keyword_in_title_rejected():
    result = _validate_pr_body(
        TITLE_WITH_CLOSE,
        BODY_WITH_SINGLE_FOOTER,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_heading_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_HEADING_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_fenced_code_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_FENCED_CODE_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_indented_code_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_INDENTED_CODE_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_blockquote_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_BLOCKQUOTE_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_list_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_LIST_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_table_cell_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_TABLE_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_close_keyword_in_html_comment_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_HTML_COMMENT_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_tickets_section_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_TICKETS_SECTION_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_empty_keys_no_footer():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITHOUT_FOOTER,
        [],
    )

    assert result.valid
    assert result.expected_close_lines == ()


def test_jira_key_dropped():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITHOUT_FOOTER,
        [KEY_JIRA_PROJ],
    )

    assert result.valid
    assert result.expected_close_lines == ()
    assert result.emitted_close_lines == ()


def test_mixed_valid_and_jira_keys():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITH_SINGLE_FOOTER,
        [KEY_NES_204, KEY_JIRA_PROJ],
    )

    assert result.valid
    assert result.expected_close_lines == ("Closes NES-204",)
    assert result.emitted_close_lines == ("Closes NES-204",)


def test_duplicate_key_emitted_once():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITH_SINGLE_FOOTER,
        [KEY_NES_204, KEY_NES_204],
    )

    assert result.valid
    assert result.emitted_close_lines == ("Closes NES-204",)


def test_lowercase_key_normalized():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_WITH_SINGLE_FOOTER,
        ["nes-204"],
    )

    assert result.valid
    assert result.expected_close_lines == ("Closes NES-204",)


def test_trailing_punctuation_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_TRAILING_PUNCTUATION_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid


def test_markdown_link_around_close_rejected():
    result = _validate_pr_body(
        BASE_TITLE,
        BODY_MARKDOWN_LINK_CLOSE,
        [KEY_NES_204],
    )

    assert not result.valid
