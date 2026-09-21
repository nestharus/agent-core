"""Executable contract regressions for exact-output research readback."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / "workflows" / "research.md"
SECTION_HEADING = "Exact-output readback and process admission"
WIDENING_CLASSES = (
    "directory read",
    "wildcard",
    "marker lookup",
    "`grep`",
    "glob",
    "recursive traversal",
    "content search",
)


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^### {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^### |\Z)",
        text,
    )
    assert match is not None, f"missing workflow section: {heading}"
    return match.group("body")


def _read_named_path(
    path: Path,
    reader: Callable[[Path], str],
) -> str:
    """Model the workflow's one permitted default verification operation."""

    return reader(path)


def test_exact_output_contract_defaults_to_direct_named_path_only() -> None:
    section = _section(_workflow_text(), SECTION_HEADING)

    assert "verification read set\ndefaults to that path alone" in section
    assert "Read the named result path directly" in section
    assert "does not imply\nauthority to widen post-write verification" in section
    assert "expressly\nauthorizes it before dispatch" in section
    assert "allowed paths or patterns\nand the allowed operation classes" in section


@pytest.mark.parametrize("operation_class", WIDENING_CLASSES)
def test_every_unapproved_widening_class_has_a_blocking_disposition(
    operation_class: str,
) -> None:
    section = _section(_workflow_text(), SECTION_HEADING)
    violation_row = next(
        line
        for line in section.splitlines()
        if "outside the express assignment authority" in line
    )

    assert operation_class in violation_row
    assert "`BLOCKED:RESEARCH_READ_SET_VIOLATION`" in violation_row
    assert (
        "only when the assignment expressly\nauthorizes it before dispatch" in section
    )


def test_semantic_completion_does_not_override_process_compliance() -> None:
    section = _section(_workflow_text(), SECTION_HEADING)

    assert (
        "Record semantic completion and process/access compliance independently"
        in section
    )
    assert "`semantic_status: COMPLETE | INCONCLUSIVE`" in section
    assert "`process_status: COMPLIANT | BLOCKED`" in section
    assert "plausible\n   or independently corroborated semantic conclusion" in section
    assert "only when the\n   activity evidence is complete" in section
    assert "exclude all content returned by the\nunapproved widening" in section
    assert "retroactively validate a contaminated artifact" in section


def test_parent_requires_completed_bounded_activity_evidence() -> None:
    section = _section(_workflow_text(), SECTION_HEADING)

    assert "completed runner trace or an equivalent bounded activity record" in section
    assert "cover the completed activity through\n   the terminal" in section
    assert "identify the read targets and operation\n   classes" in section
    assert "`BLOCKED:RESEARCH_ACTIVITY_EVIDENCE_MISSING`" in section


def test_exact_read_ignores_siblings_and_nested_repository(tmp_path: Path) -> None:
    planning_dir = tmp_path / "planning"
    result_path = planning_dir / "research-result.md"
    sibling_path = planning_dir / "sibling-plan.md"
    nested_repo_path = planning_dir / "nested-product" / ".git" / "config"
    nested_repo_path.parent.mkdir(parents=True)
    result_path.write_text("public research result", encoding="utf-8")
    sibling_path.write_text("synthetic sibling canary", encoding="utf-8")
    nested_repo_path.write_text("synthetic nested-repository canary", encoding="utf-8")
    reads: list[Path] = []

    def record_exact_read(path: Path) -> str:
        reads.append(path)
        return path.read_text(encoding="utf-8")

    observed = _read_named_path(result_path, record_exact_read)

    assert observed == "public research result"
    assert reads == [result_path]


def test_public_result_read_does_not_touch_adjacent_private_fixture(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "public-output"
    output_dir.mkdir()
    result_path = output_dir / "result.md"
    private_path = output_dir / "synthetic-private-artifact"
    result_path.write_text("public-only result", encoding="utf-8")
    private_path.write_text("synthetic private value", encoding="utf-8")
    reads: list[Path] = []

    def record_exact_read(path: Path) -> str:
        reads.append(path)
        return path.read_text(encoding="utf-8")

    observed = _read_named_path(result_path, record_exact_read)

    assert observed == "public-only result"
    assert reads == [result_path]
    assert private_path not in reads


def test_violation_reporting_contract_excludes_sensitive_discovery_content() -> None:
    section = _section(_workflow_text(), SECTION_HEADING)

    for allowed_metadata in (
        "assignment identifier",
        "declared read-set reference",
        "bounded activity-record reference",
        "operation class",
        "process disposition",
        "counts",
    ):
        assert allowed_metadata in section

    assert "must not reproduce\ndiscovered paths or filenames" in section
    assert "matched content or snippets" in section
    assert "private values" in section
    assert "raw search output" in section
