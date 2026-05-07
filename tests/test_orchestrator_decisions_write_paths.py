import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

AUDITED_ORCHESTRATORS: tuple[str, ...] = (
    "agents/implementation-pipeline-orchestrator.md",
    "agents/prototype-orchestrator.md",
    "agents/roadmap-orchestrator.md",
    "agents/alignment-cycle-orchestrator.md",
    "agents/agentsmd-maintenance-orchestrator.md",
)


def _decision_lines(path: Path) -> list[tuple[int, str]]:
    return [
        (lineno, line)
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if "DECISIONS.md" in line
    ]


def _is_write_reference(line: str) -> bool:
    return "DECISIONS.md" in line and re.search(
        r"\b(record|append|note|write)\b", line, re.IGNORECASE
    ) is not None


def _has_worktree_decisions_target(line: str) -> bool:
    return re.search(r"\$\{worktree_path\}/DECISIONS\.md", line) is not None


def _has_unqualified_decisions_target(line: str) -> bool:
    return re.search(r"(?<!\$\{worktree_path\}/)DECISIONS\.md", line) is not None


def _forbidden_write_target_reason(line: str) -> str | None:
    if "${repo_root}/DECISIONS.md" in line:
        return "forbidden target ${repo_root}/DECISIONS.md"
    if "~/ai/DECISIONS.md" in line:
        return "forbidden target ~/ai/DECISIONS.md"
    if "/home/nes/ai/DECISIONS.md" in line:
        return "forbidden target /home/nes/ai/DECISIONS.md"
    if _has_unqualified_decisions_target(line):
        return "unqualified DECISIONS.md (no ${worktree_path} prefix)"
    return None


def test_unqualified_decisions_detection_rejects_mixed_targets() -> None:
    line = "append ${worktree_path}/DECISIONS.md and DECISIONS.md"

    assert _forbidden_write_target_reason(line) == (
        "unqualified DECISIONS.md (no ${worktree_path} prefix)"
    )


def test_decisions_write_references_target_worktree_decisions_file() -> None:
    failures: list[str] = []

    for relpath in AUDITED_ORCHESTRATORS:
        path = REPO_ROOT / relpath
        for lineno, line in _decision_lines(path):
            if not _is_write_reference(line):
                continue

            reason = _forbidden_write_target_reason(line)
            if reason is not None:
                failures.append(f"{relpath}:{lineno}: {reason}: {line.strip()!r}")

    assert not failures, "\n".join(
        [
            "DECISIONS.md write references must target ${worktree_path}/DECISIONS.md:",
            *failures,
        ]
    )


def test_audited_orchestrator_decisions_read_references_stay_allowed() -> None:
    implementation_path = (
        REPO_ROOT / "agents/implementation-pipeline-orchestrator.md"
    )
    implementation_lines = [
        line
        for _, line in _decision_lines(implementation_path)
        if line.strip()
        == "### Final — Audit-history close + DECISIONS.md sync + ticket close-comment"
    ]
    assert implementation_lines == [
        "### Final — Audit-history close + DECISIONS.md sync + ticket close-comment"
    ]
    assert _is_write_reference(implementation_lines[0]) is False

    roadmap_path = REPO_ROOT / "agents/roadmap-orchestrator.md"
    roadmap_lines = _decision_lines(roadmap_path)
    assert roadmap_lines
    for _, line in roadmap_lines:
        assert line.strip() == "- `DECISIONS.md`"
        assert re.search(r"\b(record|append|note|write)\b", line, re.IGNORECASE) is None
        assert _is_write_reference(line) is False

    assert (
        _decision_lines(REPO_ROOT / "agents/alignment-cycle-orchestrator.md") == []
    )
    assert (
        _decision_lines(REPO_ROOT / "agents/agentsmd-maintenance-orchestrator.md")
        == []
    )
