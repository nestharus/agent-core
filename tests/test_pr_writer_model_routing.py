import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# Mirror of `tests/test_agentsmd_structure.py::FORBIDDEN_TOKEN_SELF_TEST`: this
# file contains `gpt-high.*pr-writer` regex literals as test fixtures, so any
# self-scan must exclude its own path. Currently `paths` lists only specific
# roots that don't include this file; this constant documents the exclusion
# explicitly for future readers who may broaden `paths`.
FORBIDDEN_TOKEN_SELF_TEST = Path("tests/test_pr_writer_model_routing.py")


def _read_repo_text(relative_path):
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _line_containing(text, fragment):
    lines = [line for line in text.splitlines() if fragment in line]
    assert len(lines) == 1, f"expected exactly one line containing {fragment!r}"
    return lines[0]


def test_phase9_pr_writer_dispatch_uses_claude_opus():
    text = _read_repo_text("agents/implementation-pipeline-orchestrator.md")
    dispatch_lines = [
        line
        for line in text.splitlines()
        if "${wu_lower}-phase-9-pr-writer.md" in line and "agents -m" in line
    ]
    assert len(dispatch_lines) == 1
    line = dispatch_lines[0]

    match = re.search(
        r"agents\s+-m\s+(?P<model>\S+)\s+"
        r"-p\s+\$\{worktree_path\}\s+"
        r"-f\s+\$\{scratch_dir\}/prompts/\$\{wu_lower\}-phase-9-pr-writer\.md",
        line,
    )
    assert match, "Phase 9 PR-writer dispatch line must keep the expected shape"
    assert match.group("model") == "claude-opus"
    stale_dispatch = (
        "agents -m gpt-high -p ${worktree_path} "
        "-f ${scratch_dir}/prompts/${wu_lower}-phase-9-pr-writer.md"
    )
    assert stale_dispatch not in line


def test_worktree_operator_open_pr_dispatch_uses_claude_opus():
    text = _read_repo_text("agents/worktree-operator.md")
    line = _line_containing(text, "-a ~/ai/agents/pr-writer.md")

    match = re.search(
        r"agents\s+-m\s+(?P<model>\S+)\s+-a\s+~/ai/agents/pr-writer\.md",
        line,
    )
    assert match, "Open-PR pr-writer dispatch line must keep the expected shape"
    assert match.group("model") == "claude-opus"
    assert "agents -m gpt-high -a ~/ai/agents/pr-writer.md" not in line


def test_no_in_scope_pr_writer_gpt_high_routing_literals_remain():
    """NES-264 proposal T5: guard in-scope PR-writer routing against stale gpt-high."""
    pattern = re.compile(r"gpt-high.*pr-writer|pr-writer.*gpt-high")
    paths = [
        *sorted((REPO_ROOT / "agents").rglob("*.md")),
        *sorted((REPO_ROOT / "workflows").rglob("*.md")),
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "tests/test_agentsmd_structure.py",
    ]

    hits = []
    for path in paths:
        if path.relative_to(REPO_ROOT) == FORBIDDEN_TOKEN_SELF_TEST:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if pattern.search(line):
                location = f"{path.relative_to(REPO_ROOT)}:{line_number}"
                hits.append(f"{location}: {line.strip()}")

    assert hits == []
