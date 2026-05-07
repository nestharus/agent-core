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

AUDITED_WORKFLOW_CONVENTION_DOCS: tuple[str, ...] = (
    "workflows/implementation-pipeline.md",
    "workflows/alignment-cycle.md",
    "workflows/tiered-approval.md",
    "conventions/risk-profile.md",
    "conventions/rebase-verification.md",
    "conventions/wu-session-lifecycle.md",
    "conventions/gate-ownership.md",
)

AUDITED_PATTERN_DOCS: tuple[str, ...] = ("patterns/infrastructure-reference.md",)

WORKFLOW_CONVENTION_ALLOWED_DECISIONS_TARGETS: dict[str, tuple[str, ...]] = {
    "workflows/implementation-pipeline.md": ("${worktree_path}/DECISIONS.md",),
    "workflows/alignment-cycle.md": ("${project_root}/DECISIONS.md",),
    "workflows/tiered-approval.md": ("${project_decisions_path}",),
    "conventions/risk-profile.md": ("${worktree_path}/DECISIONS.md",),
    "conventions/rebase-verification.md": ("${worktree_path}/DECISIONS.md",),
    "conventions/wu-session-lifecycle.md": ("${worktree_path}/DECISIONS.md",),
    "conventions/gate-ownership.md": ("${worktree_path}/DECISIONS.md",),
}

PATTERN_ALLOWED_DECISIONS_TARGETS: dict[str, tuple[str, ...]] = {
    "patterns/infrastructure-reference.md": (
        "${project_root}/DECISIONS.md",
        "caller-supplied project decisions path",
    ),
}

WORKFLOW_CONVENTION_READ_REFERENCE_ALLOWLIST: dict[
    tuple[str, int], tuple[str, ...]
] = {
    ("workflows/tiered-approval.md", 8): ("pre-authorization",),
    ("workflows/tiered-approval.md", 124): ("Pre-authorization",),
    ("conventions/gate-ownership.md", 125): (
        "DECISIONS.md",
        "project decisions path",
    ),
}

WORKFLOW_CONVENTION_CONTEXT_WRITE_REFERENCES: set[tuple[str, int]] = {
    ("workflows/tiered-approval.md", 79),
    ("workflows/tiered-approval.md", 127),
}

WORKFLOW_CONVENTION_CONTEXT_WRITE_EXPECTATIONS: dict[tuple[str, int], tuple[str, ...]] = {
    ("workflows/tiered-approval.md", 79): (
        "${project_decisions_path}",
        "project equivalent",
    ),
    ("workflows/tiered-approval.md", 127): (
        "${project_decisions_path}",
        "project equivalent",
    ),
}


def _decision_lines(path: Path) -> list[tuple[int, str]]:
    return [
        (lineno, line)
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if "DECISIONS.md" in line
    ]


def _is_write_reference(line: str) -> bool:
    if "DECISIONS.md" not in line:
        return False

    if re.search(
        r"\b(record|recorded|recording|append|note|write|written|document|"
        r"disposition)\b",
        line,
        re.IGNORECASE,
    ):
        return True

    if re.search(r"\bskip with justification\b", line, re.IGNORECASE):
        return True

    return re.search(
        r"\b(pre-authorized|preauthorized|runbook)\b",
        line,
        re.IGNORECASE,
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


def _has_unallowed_decisions_target(line: str, allowed_targets: tuple[str, ...]) -> bool:
    unchecked_line = line
    for target in allowed_targets:
        unchecked_line = unchecked_line.replace(target, "")
    return "DECISIONS.md" in unchecked_line


def _workflow_convention_forbidden_write_target_reason(
    relpath: str, lineno: int, line: str
) -> str | None:
    if (relpath, lineno) in WORKFLOW_CONVENTION_READ_REFERENCE_ALLOWLIST:
        return None
    if "${repo_root}/DECISIONS.md" in line:
        return "forbidden target ${repo_root}/DECISIONS.md"
    if "~/ai/DECISIONS.md" in line:
        return "forbidden target ~/ai/DECISIONS.md"
    if "/home/nes/ai/DECISIONS.md" in line:
        return "forbidden target /home/nes/ai/DECISIONS.md"

    allowed_targets = WORKFLOW_CONVENTION_ALLOWED_DECISIONS_TARGETS.get(relpath)
    if allowed_targets is None:
        return f"no allowed DECISIONS.md target configured for {relpath!r}"
    if _has_unallowed_decisions_target(line, allowed_targets):
        expected = " or ".join(allowed_targets)
        return f"unqualified DECISIONS.md (expected {expected})"
    return None


def _pattern_forbidden_write_target_reason(relpath: str, line: str) -> str | None:
    allowed_fragments = PATTERN_ALLOWED_DECISIONS_TARGETS.get(relpath)
    if allowed_fragments is None:
        return f"no allowed DECISIONS.md target configured for {relpath!r}"

    if "${worktree_path}/DECISIONS.md" in line:
        return "forbidden target ${worktree_path}/DECISIONS.md"
    if "${repo_root}/DECISIONS.md" in line:
        return "forbidden target ${repo_root}/DECISIONS.md"
    if "~/ai/DECISIONS.md" in line:
        return "forbidden target ~/ai/DECISIONS.md"
    if "/home/nes/ai/DECISIONS.md" in line:
        return "forbidden target /home/nes/ai/DECISIONS.md"
    if _has_unallowed_decisions_target(line, allowed_fragments):
        expected = " and ".join(allowed_fragments)
        return f"unqualified DECISIONS.md (expected {expected})"

    missing_fragments = [
        fragment for fragment in allowed_fragments if fragment not in line
    ]
    if missing_fragments:
        missing = " and ".join(missing_fragments)
        return f"missing required fragment(s): {missing}"
    return None


def _is_workflow_convention_write_reference(
    relpath: str, lineno: int, line: str
) -> bool:
    return (relpath, lineno) in WORKFLOW_CONVENTION_CONTEXT_WRITE_REFERENCES or (
        _is_write_reference(line)
    )


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


def test_workflow_convention_decisions_write_references_use_per_file_target() -> None:
    assert set(WORKFLOW_CONVENTION_ALLOWED_DECISIONS_TARGETS) == set(
        AUDITED_WORKFLOW_CONVENTION_DOCS
    )
    failures: list[str] = []

    for relpath in AUDITED_WORKFLOW_CONVENTION_DOCS:
        path = REPO_ROOT / relpath
        for lineno, line in _decision_lines(path):
            if (relpath, lineno) in WORKFLOW_CONVENTION_READ_REFERENCE_ALLOWLIST:
                continue
            if not _is_workflow_convention_write_reference(relpath, lineno, line):
                continue

            reason = _workflow_convention_forbidden_write_target_reason(
                relpath, lineno, line
            )
            if reason is not None:
                failures.append(f"{relpath}:{lineno}: {reason}: {line.strip()!r}")

    assert not failures, "\n".join(
        [
            "Workflow/convention DECISIONS.md write references must use their per-file target:",
            *failures,
        ]
    )


def test_pattern_decisions_write_references_use_project_decisions_target() -> None:
    assert set(PATTERN_ALLOWED_DECISIONS_TARGETS) == set(AUDITED_PATTERN_DOCS)
    failures: list[str] = []

    for relpath in AUDITED_PATTERN_DOCS:
        path = REPO_ROOT / relpath
        for lineno, line in _decision_lines(path):
            if not _is_write_reference(line):
                continue

            reason = _pattern_forbidden_write_target_reason(relpath, line)
            if reason is not None:
                failures.append(f"{relpath}:{lineno}: {reason}: {line.strip()!r}")

    assert not failures, "\n".join(
        [
            "Pattern DECISIONS.md write references must use the project decisions target:",
            *failures,
        ]
    )


def test_workflow_convention_decisions_read_references_stay_allowed() -> None:
    for (relpath, lineno), expected_fragments in (
        WORKFLOW_CONVENTION_READ_REFERENCE_ALLOWLIST.items()
    ):
        line = (REPO_ROOT / relpath).read_text(encoding="utf-8").splitlines()[
            lineno - 1
        ]
        assert any(fragment in line for fragment in expected_fragments), (
            f"{relpath}:{lineno} no longer matches the read-reference allow-list: "
            f"{line!r}"
        )
        if "DECISIONS.md" in line:
            assert _workflow_convention_forbidden_write_target_reason(
                relpath, lineno, line
            ) is None


def test_workflow_convention_decisions_read_references_use_qualified_target() -> None:
    expected_references = {
        ("workflows/tiered-approval.md", 8): "project_decisions_path",
        ("workflows/tiered-approval.md", 124): "project decisions path",
        ("conventions/gate-ownership.md", 125): "project decisions path",
    }

    for (relpath, lineno), expected_reference in expected_references.items():
        line = (REPO_ROOT / relpath).read_text(encoding="utf-8").splitlines()[
            lineno - 1
        ]
        assert expected_reference in line, (
            f"{relpath}:{lineno} must reference the project decisions target: "
            f"{line!r}"
        )
        assert "DECISIONS.md" not in line, (
            f"{relpath}:{lineno} must not revert to bare DECISIONS.md wording: "
            f"{line!r}"
        )


def test_workflow_convention_context_write_references_stay_allowed() -> None:
    assert set(WORKFLOW_CONVENTION_CONTEXT_WRITE_EXPECTATIONS) == (
        WORKFLOW_CONVENTION_CONTEXT_WRITE_REFERENCES
    )

    for (relpath, lineno), expected_fragments in (
        WORKFLOW_CONVENTION_CONTEXT_WRITE_EXPECTATIONS.items()
    ):
        line = (REPO_ROOT / relpath).read_text(encoding="utf-8").splitlines()[
            lineno - 1
        ]
        assert all(fragment in line for fragment in expected_fragments), (
            f"{relpath}:{lineno} no longer matches the context-write allow-list: "
            f"{line!r}"
        )
        assert _is_workflow_convention_write_reference(relpath, lineno, line)
        assert _workflow_convention_forbidden_write_target_reason(
            relpath, lineno, line
        ) is None


def test_write_classifier_recognizes_workflow_convention_shapes() -> None:
    write_examples = [
        "Skip only by explicit written decision in `DECISIONS.md`.",
        "Removing axes requires a project-level decision recorded in `DECISIONS.md`.",
        "Platform decisions will be recorded in `${project_root}/DECISIONS.md` "
        "(or the caller-supplied project decisions path) as they are made.",
        "Recording a runbook in `DECISIONS.md` pre-authorizes the action.",
        "Document it in `DECISIONS.md`.",
        "Any drop is a regression that needs disposition in DECISIONS.md.",
        "This is a `DECISIONS.md` skip with justification.",
        "Record in `DECISIONS.md` before closing the ticket.",
        "append ${worktree_path}/DECISIONS.md and note the reason",
    ]
    non_write_examples = [
        "- `DECISIONS.md`",
        "### Final - Audit-history close + DECISIONS.md sync + ticket close-comment",
        "Read `DECISIONS.md` before asking the user.",
    ]

    for line in write_examples:
        assert _is_write_reference(line), line
    for line in non_write_examples:
        assert not _is_write_reference(line), line
