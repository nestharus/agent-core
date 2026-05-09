import re
from pathlib import Path


"""
Risk annotation: verifies proposal §5 structural operator-spec risk at unit
level. Fixture source is the repo-local agents/pr-writer.md operator Markdown
file, resolved from this test file and inspected with regex assertions.
Assumptions covered: A4, A6, A7.
"""


REPO_ROOT = Path(__file__).resolve().parents[1]
PR_WRITER_MD = REPO_ROOT / "agents/pr-writer.md"


def _operator_text():
    return PR_WRITER_MD.read_text(encoding="utf-8")


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    heading_level = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{heading_level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _assert_regex(text, pattern, message):
    assert re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL), message


def test_pr_writer_frontmatter_model_is_claude_opus():
    """NES-264 contract §1.1 / proposal T1: pr-writer defaults to claude-opus."""
    text = _operator_text()
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---", text, flags=re.DOTALL)
    assert match, "operator spec must start with YAML frontmatter"

    frontmatter = match.group("frontmatter")
    assert re.search(r"(?m)^model:\s*claude-opus\s*$", frontmatter)
    assert not re.search(r"(?m)^model:\s*gpt-high\s*$", frontmatter)


def test_pr_writer_uses_three_dot_branch_contribution_diff():
    text = _operator_text()
    inputs = _section_after_heading(text, "## Inputs")
    procedure = _section_after_heading(text, "## Procedure")
    stop_conditions = _section_after_heading(text, "## Stop Conditions")

    _assert_regex(
        inputs,
        re.escape("git diff base...branch"),
        "Inputs section must describe the repo checkout as the source for the three-dot branch contribution diff",
    )
    _assert_regex(
        procedure,
        re.escape("git -C ${repo_root} diff ${base}...${branch} --stat"),
        "Procedure must read the executable three-dot branch contribution diff",
    )
    _assert_regex(
        stop_conditions,
        re.escape("BLOCKED:diff-empty"),
        "Stop Conditions section must retain the diff-empty blocked state",
    )
    _assert_regex(
        stop_conditions,
        re.escape("git diff base...branch"),
        "Stop Conditions section must define diff-empty using the three-dot branch contribution diff",
    )

    assert "git -C ${repo_root} diff ${base}..${branch} --stat" not in text
    assert "git diff base..branch" not in text


def test_inputs_declares_linear_issue_keys_optional():
    inputs = _section_after_heading(_operator_text(), "## Inputs")

    _assert_regex(
        inputs,
        r"linear_issue_keys.*optional|optional.*linear_issue_keys",
        "Inputs section must declare linear_issue_keys as optional",
    )


def test_close_keyword_footer_rule_present():
    text = _operator_text()

    _assert_regex(text, r"Closes\s+<KEY>", "must name canonical Closes <KEY> footer")
    _assert_regex(
        text,
        r"standalone.*(?:paragraph|normal Markdown)|(?:paragraph|normal Markdown).*standalone",
        "footer rule must require a standalone normal paragraph",
    )
    _assert_regex(
        text,
        r"after.*(?:prose|reviewer-facing|body).*sections|after.*Verification.*Out of scope",
        "footer rule must place the footer after prose sections",
    )
    _assert_regex(
        text,
        r"blank[- ]line|blank line",
        "footer rule must require a blank-line separator",
    )


def test_audience_rule_exception_carved_out():
    audience_rules = _section_after_heading(_operator_text(), "## Required Audience Rules — ABSOLUTE")

    _assert_regex(
        audience_rules,
        r"(exception|carve[- ]out).*close[- ]keyword|close[- ]keyword.*(exception|carve[- ]out)",
        "audience rule must document a close-keyword exception",
    )
    _assert_regex(
        audience_rules,
        r"linear_issue_keys|Linear issue key",
        "audience exception must be scoped to explicit Linear issue keys",
    )


def test_self_audit_close_keyword_rules_present():
    procedure = _section_after_heading(_operator_text(), "## Procedure")

    _assert_regex(
        procedure,
        r"self[- ]audit.*close|close.*self[- ]audit",
        "Self-Audit procedure must mention close-keyword checks",
    )
    required_patterns = {
        "title": r"title",
        "heading": r"heading|#-prefixed",
        "fenced code": r"fenced\s+code|```",
        "indented code": r"indented\s+code|4[- ]space",
        "blockquote": r"blockquote|block\s+quote|>",
        "list": r"list\s+item|(?:bulleted|numbered)\s+list",
        "table cell": r"table\s+cell|table",
        "HTML comment": r"HTML\s+comment|<!--",
        "forbidden sections": r"Tickets?.*Issues?.*Linear.*References|References.*Linear.*Issues?.*Tickets?",
    }
    for name, pattern in required_patterns.items():
        _assert_regex(
            procedure,
            pattern,
            f"Self-Audit must forbid close-keyword placement in {name}",
        )


def test_existing_pr_title_body_edit_uses_rest_patch():
    procedure = _section_after_heading(_operator_text(), "## Procedure")

    required_patterns = {
        "REST PATCH endpoint uses explicit PR number variable": (
            r"\bPATCH\s+/repos/\{owner\}/\{repo\}/pulls/\$\{existing_pr_number\}(?=\s|\\|$)"
        ),
        "existing PR number resolution documented": r"already-known\s+PR\s+number|REPLACE_WITH_PR_NUMBER",
        "`title` field PATCHed": r"-f\s+title\s*=",
        "`body` field PATCHed": r"-f\s+body\s*=",
        "`gh pr edit` excluded from title/body refresh path": (
            r"gh\s+pr\s+edit.{0,160}(?:NOT|not).{0,160}title/body|"
            r"(?:NOT|not).{0,160}title/body.{0,160}gh\s+pr\s+edit"
        ),
        "Projects-classic GraphQL/deprecation rationale": (
            r"Projects[- ]classic|deprecat(?:ed|ion)"
        ),
    }
    missing = [
        name
        for name, pattern in required_patterns.items()
        if not re.search(pattern, procedure, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    ]

    assert not missing, (
        "Procedure must document existing-PR title/body REST edit guidance; "
        f"missing: {', '.join(missing)}"
    )


def test_jira_exclusion_documented():
    text = _operator_text()

    _assert_regex(
        text,
        r"\bJira[- ]?shaped keys?\b|\bJira keys?\b|\bJIRA[- ]?shaped keys?\b|\bJIRA keys?\b",
        "spec must name Jira-shaped keys or Jira keys",
    )
    _assert_regex(
        text,
        r"(?:Jira[- ]?shaped keys?|Jira keys?|JIRA[- ]?shaped keys?|JIRA keys?).{0,160}"
        r"(?:not|do not|does not|must not|silently drop|dropped).{0,160}"
        r"(?:emit|footer|close[- ]keyword|close lines?)",
        "spec must say Jira-shaped keys are not emitted by default",
    )


def test_no_invention_rule_documented():
    text = _operator_text()

    _assert_regex(
        text,
        r"must not\s+(?:guess|infer|invent)|do not\s+(?:guess|infer|invent)|not\s+(?:guessed|inferred|invented)",
        "spec must forbid guessing issue keys",
    )
    for source in ("branch", "slug", "prose"):
        _assert_regex(
            text,
            source,
            f"no-invention rule must name {source} as an invalid key source",
        )
