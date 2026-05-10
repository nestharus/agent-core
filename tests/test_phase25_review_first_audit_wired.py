from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def test_review_first_audit_dispatch_is_wired():
    text = ORCHESTRATOR.read_text(encoding="utf-8")

    assert "#### Phase 2.5 entry-mode audit dispatch" in text
    assert (
        "agents -m gpt-high -a audit -p ${worktree_path} -f "
        "${scratch_dir}/audit/${audit_slug}/prompts/${wu_lower}-review-first-audit.md "
        "2>&1 | tee ${scratch_dir}/audit/${audit_slug}/logs/"
        "${wu_lower}-review-first-audit.log"
    ) in text
    assert "${planning_dir}/audit/${audit_slug}/aggregate-audit.md" in text
    assert "${planning_dir}/audit/${audit_slug}/findings.json" in text
    assert "BLOCKED:audit-bundle-invalid" in text


def test_review_first_process_tree_dispatch_blocks_consumption():
    text = ORCHESTRATOR.read_text(encoding="utf-8")

    assert (
        "agents -m gpt-high -a process-tree-auditor -p ${worktree_path} -f "
        "${scratch_dir}/audit/${audit_slug}/prompts/"
        "${wu_lower}-review-first-process-tree.md 2>&1 | tee "
        "${scratch_dir}/audit/${audit_slug}/logs/"
        "${wu_lower}-review-first-process-tree.log"
    ) in text
    assert "${planning_dir}/audit/${audit_slug}/process-tree-expected.md" in text
    assert "Refuse to advance to Step 2.5.0, Phase 3, or value-zero termination" in text
    assert "`FAIL`, `NEEDS_INPUT`, `BLOCKED`" in text
