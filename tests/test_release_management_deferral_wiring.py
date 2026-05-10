"""Structural guards for release-management deferral wiring."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "release-management.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "release-orchestrator.md"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing required file: {path}"
    return path.read_text(encoding="utf-8")


def test_release_management_deferral_language_removed():
    text = _read(WORKFLOW)
    forbidden = [
        "release operator routing and topology updates are deferred",
        "future release operators",
        "future `release-orchestrator`",
        "A future release orchestrator",
        "Forward-referenced release operators",
        "future operators execute approved changes",
    ]

    missing = [phrase for phrase in forbidden if phrase in text]
    assert missing == []


def test_release_orchestrator_dispatches_wired_suboperators_with_artifacts():
    text = _read(ORCHESTRATOR)
    expected = [
        (
            "agents -m gpt-high -a release-cut-operator -p ${worktree_path} "
            "-f ${scratch_dir}/prompts/${release_id}-cut.md 2>&1 | tee "
            "${scratch_dir}/logs/${release_id}-cut.log"
        ),
        "${planning_dir}/release/${release_id}/cut-evidence.md",
        (
            "agents -m gpt-high -a release-hotfix-operator -p ${worktree_path} "
            "-f ${scratch_dir}/prompts/${release_id}-hotfix.md 2>&1 | tee "
            "${scratch_dir}/logs/${release_id}-hotfix.log"
        ),
        "${planning_dir}/release/${release_id}/hotfix-evidence.md",
        (
            "agents -m gpt-high -a release-promote-operator -p ${worktree_path} "
            "-f ${scratch_dir}/prompts/${release_id}-promote.md 2>&1 | tee "
            "${scratch_dir}/logs/${release_id}-promote.log"
        ),
        "${planning_dir}/release/${release_id}/promote-tag-evidence.md",
        (
            "agents -m gpt-high -a release-reconcile-operator -p ${worktree_path} "
            "-f ${scratch_dir}/prompts/${release_id}-reconcile.md 2>&1 | tee "
            "${scratch_dir}/logs/${release_id}-reconcile.log"
        ),
        "${planning_dir}/release/${release_id}/reconcile-evidence.md",
    ]

    missing = [phrase for phrase in expected if phrase not in text]
    assert missing == []
