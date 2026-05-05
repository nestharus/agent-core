"""Tests for NES-137 code-quality convention discoverability + structural shape. Contract: planning/nes-137-code-quality-convention/contracts/nes-137-code-quality.md."""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_QUALITY_MD = REPO_ROOT / "conventions" / "code-quality.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
README_MD = REPO_ROOT / "README.md"

REQUIRED_CODE_QUALITY_HEADINGS = [
    "## Purpose",
    "## Scope",
    "## Function classification",
    "## Nesting depth",
    "## Inline functions",
    "## Duplicate handling",
    "## Push-vs-pull system coupling",
    "## Numerical thresholds",
    "## Failure modes",
    "## What this convention does not enforce",
    "## Cross-references",
]


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    if not match:
        pytest.fail(f"missing section heading: {heading}")

    heading_level = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{1,{heading_level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _bullet_markdown_links(text):
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
            yield match.group(1), match.group(2)


def test_code_quality_convention_file_exists():
    """Risk: convention file referenced from indexes but absent or empty; level=unit; source=contract Test contract."""
    assert CODE_QUALITY_MD.exists(), "missing conventions/code-quality.md"
    assert CODE_QUALITY_MD.stat().st_size >= 500


def test_code_quality_required_headings_present_in_order():
    """Risk: convention omits required auditor anchor sections; level=unit; source=contract Test contract."""
    text = CODE_QUALITY_MD.read_text(encoding="utf-8")
    headings = [match.group(0) for match in re.finditer(r"(?m)^##\s+.+$", text)]

    assert headings == REQUIRED_CODE_QUALITY_HEADINGS


def test_agents_md_indexes_code_quality_convention():
    """Risk: AGENTS.md discoverability misses the convention; level=unit; source=contract Test contract."""
    conventions = _section_after_heading(
        AGENTS_MD.read_text(encoding="utf-8"),
        "## Conventions",
    )

    assert (
        "`~/ai/conventions/code-quality.md`",
        "conventions/code-quality.md",
    ) in set(_bullet_markdown_links(conventions))


def test_readme_indexes_code_quality_convention():
    """Risk: README.md discoverability misses the convention; level=unit; source=contract Test contract."""
    conventions = _section_after_heading(
        README_MD.read_text(encoding="utf-8"),
        "### Conventions",
    )

    assert (
        "`conventions/code-quality.md`",
        "conventions/code-quality.md",
    ) in set(_bullet_markdown_links(conventions))
