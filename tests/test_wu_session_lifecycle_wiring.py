"""Shape guards for WU session lifecycle deferral wiring."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = REPO_ROOT / "conventions" / "wu-session-lifecycle.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
WAKE_WORKFLOW = REPO_ROOT / "workflows" / "wu-session-wake.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lifecycle_deferral_language_is_replaced_with_wiring_refs():
    text = _read(LIFECYCLE)

    forbidden = (
        "This convention is **skeletal**",
        "Several pieces are not yet implemented",
        "No implementation",
        "Does not yet exist",
        "(TBD)",
        "needs to learn this",
        "Refactor the two",
    )
    for phrase in forbidden:
        assert phrase not in text

    assert "Wired in `~/ai/agents/implementation-pipeline-orchestrator.md`" in text
    assert "Wired in `~/ai/agents/wu-session-resumer.md`" in text
    assert "Wired in `~/ai/workflows/wu-session-wake.md`" in text
    assert "<!-- INTENTIONAL:" in text


def test_implementation_orchestrator_writes_session_manifest_and_index():
    text = _read(ORCHESTRATOR)

    assert "**Initialize the WU session manifest.**" in text
    assert "${planning_dir}/session.json" in text
    assert "${planning_dir}/../sessions.index.json" in text
    assert "branch_out_sha" in text
    assert "BLOCKED:session-manifest-init-failed" in text
    assert "**Update the session manifest for draft PR dormancy.**" in text
    assert "draft_pr_head_sha" in text
    assert "BLOCKED:session-manifest-pr-update-failed" in text


def test_predecessor_successor_handoff_is_wired_into_phase0():
    text = _read(ORCHESTRATOR)

    assert "`predecessor_session_manifest_path`" in text
    assert "${scratch_dir}/predecessor-session.md" in text
    assert "successor_session_brief" in text
    assert "BLOCKED:invalid-predecessor-session" in text


def test_wake_workflow_dispatches_wu_session_resumer():
    text = _read(WAKE_WORKFLOW)

    assert "agents -m gpt-high -a wu-session-resumer -p ${worktree_path} " in text
    assert (
        "-f ${planning_dir}/prompts/${ticket_id}-wu-session-resume.md "
        "2>&1 | tee ${planning_dir}/logs/${ticket_id}-wu-session-resume.log"
    ) in text
    assert "session_manifest_path" in text
    assert "pre_merge_main_sha" in text
