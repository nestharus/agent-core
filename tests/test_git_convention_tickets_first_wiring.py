"""Structural guard for tickets-first PR timing wiring."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_CONVENTION = REPO_ROOT / "conventions" / "git.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_tickets_first_pr_timing_is_wired_into_phase8_5():
    convention = _read(GIT_CONVENTION)
    orchestrator = _read(ORCHESTRATOR)

    assert "defer PR creation" not in convention
    assert (
        "Wired in `~/ai/agents/implementation-pipeline-orchestrator.md` "
        "§ Phase 8.5"
    ) in convention
    assert (
        "agents -m claude-opus -a ${ticket_operator} -p ${worktree_path} "
        "-f ${scratch_dir}/prompts/${wu_lower}-phase-8.5-ticket-comment.md "
        "2>&1 | tee ${scratch_dir}/logs/${wu_lower}-phase-8.5-ticket-comment.log"
    ) in orchestrator
    assert "${scratch_dir}/questions/<question_id>.question.json" in orchestrator
    assert "The Phase 9 draft PR does not open until A." in orchestrator
