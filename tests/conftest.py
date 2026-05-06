from pathlib import Path

import pytest


@pytest.fixture
def repo_root():
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").exists():
            return candidate
    raise AssertionError("could not locate repo root containing AGENTS.md")


@pytest.fixture
def jira_operator_section(repo_root):
    operator_path = repo_root / "agents" / "jira-operator.md"

    def section(heading):
        text = operator_path.read_text(encoding="utf-8")
        heading_line = f"{heading}\n"
        start = text.find(heading_line)
        assert start != -1, f"missing heading: {heading}"
        block_start = start + len(heading_line)
        next_heading = text.find("\n## ", block_start)
        if next_heading == -1:
            return text[block_start:]
        return text[block_start:next_heading]

    return section


@pytest.fixture
def comment_procedure_block(jira_operator_section):
    return jira_operator_section("## Procedure: Comment")
