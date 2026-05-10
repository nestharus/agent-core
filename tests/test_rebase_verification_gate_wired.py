"""Shape guards for rebase-verification wiring in the implementation orchestrator."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
CONVENTION = REPO_ROOT / "conventions" / "rebase-verification.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_rebase_verification_dispatches_all_four_checks():
    text = _read(ORCHESTRATOR)

    assert "## Rebase Verification Gate" in text
    assert (
        "agents -m gpt-high -a test-audit-gate -p ${worktree_path} "
        "-f ${scratch_dir}/prompts/${wu_lower}-rebase-test-rerun.md "
        "2>&1 | tee ${scratch_dir}/logs/${wu_lower}-rebase-test-rerun.log"
    ) in text
    assert (
        "agents -m gpt-high -a coverage-analyzer -p ${worktree_path} "
        "-f ${scratch_dir}/prompts/${wu_lower}-rebase-coverage.md "
        "2>&1 | tee ${scratch_dir}/logs/${wu_lower}-rebase-coverage.log"
    ) in text
    assert (
        "agents -m gpt-high -a phase6-tests-contracts-alignment-reviewer "
        "-p ${worktree_path} "
        "-f ${scratch_dir}/prompts/${wu_lower}-rebase-contract-verify.md "
        "2>&1 | tee ${scratch_dir}/logs/${wu_lower}-rebase-contract-verify.log"
    ) in text
    assert (
        "agents -m gpt-high -a rebase-drift-checker -p ${worktree_path} "
        "-f ${scratch_dir}/prompts/${wu_lower}-rebase-drift.md "
        "2>&1 | tee ${scratch_dir}/logs/${wu_lower}-rebase-drift.log"
    ) in text


def test_rebase_verification_gate_names_canonical_artifacts():
    text = _read(ORCHESTRATOR)

    for artifact in (
        "${planning_dir}/risk/${wu_lower}-rebase-tests.md",
        "${planning_dir}/risk/${wu_lower}-rebase-coverage.md",
        "${planning_dir}/risk/${wu_lower}-rebase-contract-verify.md",
        "${planning_dir}/risk/${wu_lower}-rebase-drift.md",
        "${planning_dir}/risk/${wu_lower}-rebase-verification.md",
    ):
        assert artifact in text

    assert "BLOCKED:coverage-adapter-missing" in text
    assert "rebase-drift: no drift; report=${planning_dir}/risk/${wu_lower}-rebase-drift.md" in text


def test_rebase_verification_convention_has_no_open_deferral_language():
    text = _read(CONVENTION)

    for forbidden in (
        "## TODO",
        "tracked in a separate ticket",
        "operator review only",
        "not yet wired",
        "not yet implemented",
        "not currently enforced",
        "until that ticket lands",
    ):
        assert forbidden not in text

    assert "## Wiring Status" in text
    assert "Wired in `~/ai/agents/implementation-pipeline-orchestrator.md`" in text
