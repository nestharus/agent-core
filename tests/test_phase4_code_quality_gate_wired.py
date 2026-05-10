import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
WORKFLOW = REPO_ROOT / "workflows" / "code-quality.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_phase4_code_quality_gate_has_dispatch_and_artifacts():
    text = _read(ORCHESTRATOR)
    match = re.search(
        r"(?ms)^#### Phase 4 code-quality gate\n(?P<section>.*?)(?=^### |\Z)",
        text,
    )
    assert match, "missing Phase 4 code-quality gate sub-step"
    section = match.group("section")

    required = (
        "agents -m gpt-high -p ${worktree_path} -f ${scratch_dir}/prompts/${wu_lower}-phase-4-code-quality.md 2>&1 | tee ${scratch_dir}/logs/${wu_lower}-phase-4-code-quality.log",
        "${planning_dir}/code-quality/${wu_lower}-phase-4/dispatch-manifest.md",
        "${planning_dir}/code-quality/${wu_lower}-phase-4/findings.json",
        "${planning_dir}/code-quality/${wu_lower}-phase-4/findings.md",
        "${planning_dir}/code-quality/${wu_lower}-phase-4/aggregate-code-quality.md",
        "phase_4_code_quality_missing_or_blocking",
        "NEEDS_INPUT:<absolute_question_artifact_path>",
    )
    missing = [token for token in required if token not in section]
    assert missing == []


def test_code_quality_workflow_back_references_phase4_wiring():
    text = _read(WORKFLOW)

    assert "does not wire implementation-pipeline Phase 4" not in text
    assert "future tickets file them" not in text
    assert (
        "`~/ai/agents/implementation-pipeline-orchestrator.md` § `#### Phase 4 code-quality gate`"
        in text
    )
