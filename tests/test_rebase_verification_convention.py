"""Structural tests for the NES-167 rebase verification convention update."""

import re
from pathlib import Path


CONVENTION_PATH = (
    Path(__file__).resolve().parent.parent
    / "conventions"
    / "rebase-verification.md"
)


def _convention_text():
    assert CONVENTION_PATH.exists(), "missing conventions/rebase-verification.md"
    return CONVENTION_PATH.read_text(encoding="utf-8")


def _section_after_h3(text, heading):
    pattern = rf"(?m)^###\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ### {heading}"

    following = text[match.end() :]
    next_h1_to_h3 = re.search(r"(?m)^#{1,3}\s+", following)
    if next_h1_to_h3:
        return following[: next_h1_to_h3.start()]
    return following


def test_check_four_points_to_operator():
    check_four = _section_after_h3(_convention_text(), "4. Drift check")

    assert (
        "~/ai/agents/rebase-drift-checker.md" in check_four
        or "agents/rebase-drift-checker.md" in check_four
    ), "Drift check must point to the rebase-drift-checker operator"
    assert (
        "merged_base_diff_path" in check_four
        or "caller-supplied merged-base diff" in check_four
    ), "Drift check must name the merged-base diff input"
    assert "touched-surface enumeration" in check_four, (
        "Drift check must reference the Phase 2.5 touched-surface enumeration"
    )
    assert (
        "${planning_dir}/risk/<wu>-rebase-drift.md" in check_four
        or "report_path" in check_four
    ), "Drift check must document the report path"
    assert "rebase-drift: drift detected" in check_four, (
        "Drift check must document the drift-detected stdout verdict"
    )
    assert "rebase-drift: no drift" in check_four, (
        "Drift check must document the no-drift stdout verdict"
    )
