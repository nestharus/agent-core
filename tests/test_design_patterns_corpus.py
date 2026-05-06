"""Structural tests for the NES-221 design-pattern corpus."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "conventions" / "design-patterns.md"

EXPECTED_DP_IDS = tuple(f"DP-{number:03d}" for number in range(1, 13))
FORBIDDEN_FRAMING_MARKERS = (
    "# Best Practices",
    "## Best Practices",
    "primary rule list",
    "primary rule-list deliverable",
    "comprehensive best-practices",
    "standalone best-practices",
)
REQUIRED_ENTRY_LABELS = (
    "- Short statement:",
    "- Canonical authority:",
    "- Exemplars:",
    "- Auditor use:",
)


def _corpus_text():
    return CORPUS_PATH.read_text(encoding="utf-8")


def _dp_entry_slices(text):
    matches = list(re.finditer(r"(?m)^###\s+(DP-\d{3})\s+-\s+.+$", text))
    entries = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entries[match.group(1)] = text[match.start() : end]
    return entries


def test_design_patterns_corpus_file_exists():
    """T1: Corpus exists and declares its thin-index identity."""
    assert CORPUS_PATH.exists()
    text = _corpus_text()

    first_nonblank_line = next(line for line in text.splitlines() if line.strip())
    assert first_nonblank_line == "# Design Patterns"

    first_dp_heading = re.search(r"(?m)^###\s+DP-\d{3}\s+-\s+", text)
    first_200_lines = "\n".join(text.splitlines()[:200])
    intro_span = text[: first_dp_heading.start()] if first_dp_heading else first_200_lines
    if len(first_200_lines) < len(intro_span):
        intro_span = first_200_lines
    assert "thin citation index" in intro_span.casefold()


def test_design_patterns_corpus_names_unindexed_pattern_signal():
    """Corpus names the unindexed-pattern maintenance signal."""
    assert "unindexed-pattern" in _corpus_text()


def test_design_patterns_corpus_has_exact_initial_dp_range():
    """T2: Corpus contains DP-001 through DP-012 and no DP-013+ entries."""
    text = _corpus_text()
    entries = _dp_entry_slices(text)

    assert tuple(entries) == EXPECTED_DP_IDS
    all_dp_tokens = set(re.findall(r"\bDP-\d{3}\b", text))
    assert all_dp_tokens == set(EXPECTED_DP_IDS)


def test_design_patterns_entries_have_required_field_labels():
    """T3: Every DP entry has statement, authority, exemplars, and auditor-use fields."""
    entries = _dp_entry_slices(_corpus_text())

    assert tuple(entries) == EXPECTED_DP_IDS
    for dp_id, entry in entries.items():
        for label in REQUIRED_ENTRY_LABELS:
            assert label in entry, f"{dp_id} missing required field label: {label}"
        assert re.search(
            r"- Canonical authority:\s+(?:`?(?:~/ai|/home/nes/ai|https?://)[^`\n]+`?)",
            entry,
        ), f"{dp_id} must cite a canonical path or URL"
        assert re.search(
            r"- Exemplars:\s+`?(?:~/ai|/home/nes/ai)[^`\n]+`?",
            entry,
        ), f"{dp_id} must cite at least one exemplar repo path"


def test_design_patterns_corpus_avoids_forbidden_primary_rule_framing():
    """T4: Corpus does not use forbidden thick best-practices framing markers."""
    text = _corpus_text().casefold()

    for marker in FORBIDDEN_FRAMING_MARKERS:
        assert marker.casefold() not in text
