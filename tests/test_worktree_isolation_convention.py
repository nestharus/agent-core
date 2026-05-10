"""Structural tests for the ACR-147 worktree isolation convention update."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONVENTION = REPO_ROOT / "conventions" / "worktree-isolation.md"


def _read():
    assert CONVENTION.exists(), "missing conventions/worktree-isolation.md"
    return CONVENTION.read_text(encoding="utf-8")


def test_convention_file_exists():
    assert CONVENTION.exists(), "missing conventions/worktree-isolation.md"
    assert CONVENTION.is_file(), "conventions/worktree-isolation.md is not a file"
    text = _read()
    assert text
    assert CONVENTION.stat().st_size >= 200


def test_unconditional_rule_named():
    text = _read()

    assert "unconditional" in text
    assert "every branch's work" in text or "all branch work" in text


def test_central_checkout_definition_present():
    text = _read()

    assert "central checkout" in text.lower()


def test_allowed_read_state_operations_listed():
    text = _read()
    required = ["git status", "git log", "git fetch", "gh pr view", "gh pr list"]
    missing = [literal for literal in required if literal not in text]

    assert not missing
    assert "git diff" in text or "git show" in text


def test_disallowed_state_mutating_operations_listed():
    text = _read()
    required = [
        "git checkout",
        "git switch",
        "git reset",
        "git commit",
        "git merge",
        "git rebase",
        "git push",
    ]
    missing = [literal for literal in required if literal not in text]

    assert not missing
    assert "tracked file" in text or "tracked files" in text


def test_jj_substrate_carveout_named():
    text = _read()
    marker = "jj-operator" if "jj-operator" in text else "agents/jj-operator.md"
    marker_index = text.find(marker)
    proximity = text[max(0, marker_index - 120) : marker_index + 180]

    assert marker_index != -1
    assert "substrate" in proximity or "jj" in proximity


def test_worktree_administration_carveout_named():
    text = _read()
    marker = (
        "worktree-operator"
        if "worktree-operator" in text
        else "agents/worktree-operator.md"
    )
    marker_index = text.find(marker)
    proximity = text[max(0, marker_index - 160) : marker_index + 220]

    assert marker_index != -1
    assert "administration" in proximity
    assert "creation" in proximity or "sync" in proximity


def test_outside_repo_scratch_carveout_named():
    text = _read()
    marker = (
        "pipeline-artifacts-operator"
        if "pipeline-artifacts-operator" in text
        else "agents/pipeline-artifacts-operator.md"
    )

    assert marker in text
    assert "Tasks Without a Worktree" in text
