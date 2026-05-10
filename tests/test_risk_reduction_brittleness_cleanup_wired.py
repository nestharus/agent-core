from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / "workflows" / "risk-reduction.md"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_todo_brittleness_cleanup_has_jira_dispatch_and_artifact():
    text = _workflow_text()

    assert (
        "agents -m claude-opus -a jira-operator -p <worktree> "
        "-f ${scratch_dir}/prompts/risk-reduction-brittleness-todo.md "
        "2>&1 | tee ${scratch_dir}/logs/risk-reduction-brittleness-todo.log"
    ) in text
    assert (
        "${planning_dir}/risk-reduction/"
        "${surface_slug}-brittleness-followups.md"
    ) in text
    assert "refuses to advance if the artifact is missing" in text


def test_xfail_brittleness_cleanup_has_test_writer_and_green_gate_dispatches():
    text = _workflow_text()

    assert (
        "agents -m gpt-high -a test-writer -p <worktree> "
        "-f ${scratch_dir}/prompts/risk-reduction-xfail-tests.md "
        "2>&1 | tee ${scratch_dir}/logs/risk-reduction-xfail-test-writer.log"
    ) in text
    assert (
        "agents -m gpt-high -a green-phase-gate -p <worktree> "
        "-f ${scratch_dir}/prompts/risk-reduction-xfail-green-gate.md "
        "2>&1 | tee ${scratch_dir}/logs/risk-reduction-xfail-green-gate.log"
    ) in text
    assert (
        "${planning_dir}/risk-reduction/"
        "${surface_slug}-xfail-green-gate.md"
    ) in text
