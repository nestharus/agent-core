import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "build-prototype.md"
IMPLEMENTATION_ORCHESTRATOR = (
    REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
)
ROADMAP_ORCHESTRATOR = REPO_ROOT / "agents" / "roadmap-orchestrator.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_has(text: str, needle: str) -> None:
    assert needle in text, f"missing required text: {needle}"


def _assert_regex(text: str, pattern: str) -> None:
    assert re.search(pattern, text), f"missing required pattern: {pattern}"


def test_implementation_defer_to_prototype_dispatch_is_wired():
    text = _read(IMPLEMENTATION_ORCHESTRATOR)

    _assert_has(
        text,
        "agents -m claude-opus -a prototype-orchestrator -p "
        "${prototype_worktree_path} -f "
        "${scratch_dir}/prompts/${wu_lower}-phase-2.5-prototype-dispatch.md "
        "2>&1 | tee "
        "${scratch_dir}/logs/${wu_lower}-phase-2.5-prototype-dispatch.log",
    )
    _assert_has(text, "${scratch_dir}/phase25/defer-disposition-execution.md")
    _assert_has(text, "prototype_dispatch_prompt_path")
    _assert_has(text, "prototype_dispatch_log_path")
    _assert_has(text, "${prototype_planning_dir}/dossier/spawned-tickets.md")
    _assert_regex(
        text,
        r"(?is)Refuse to advance to Phase 3.{0,240}phase-2\.5-prototype-dispatch\.log",
    )


def test_roadmap_layer_2_prototype_escape_hatch_is_wired():
    text = _read(ROADMAP_ORCHESTRATOR)

    _assert_has(text, "Prototype escape hatch for substrate feasibility")
    _assert_has(
        text,
        "agents -m claude-opus -a prototype-orchestrator -p "
        "${repo_root}/worktrees/prototype-${roadmap_layer_slug} -f "
        "${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-prototype.md "
        "2>&1 | tee ${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-prototype.log",
    )
    _assert_has(text, "${prototype_planning_dir}/dossier/answer.md")
    _assert_has(text, "${prototype_planning_dir}/dossier/spawned-tickets.md")
    _assert_has(
        text,
        "agents -m gpt-high -a engineering-roadmap-proposer -p ${worktree} -f "
        "${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-engineering-revision-from-prototype.md "
        "2>&1 | tee "
        "${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-engineering-revision-from-prototype.log",
    )


def test_roadmap_layer_3_prototype_escape_hatch_is_wired():
    text = _read(ROADMAP_ORCHESTRATOR)

    _assert_has(text, "Prototype escape hatch for WU decomposition")
    _assert_has(
        text,
        "roadmap_layer=Layer 3:${planning_dir}/ai-roadmap.md",
    )
    _assert_has(
        text,
        "agents -m gpt-high -a ai-roadmap-proposer -p ${worktree} -f "
        "${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-ai-revision-from-prototype.md "
        "2>&1 | tee "
        "${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-ai-revision-from-prototype.log",
    )


def test_build_prototype_source_references_wired_targets():
    text = _read(WORKFLOW)

    _assert_has(
        text,
        "Wired in `~/ai/agents/implementation-pipeline-orchestrator.md` "
        "§ Phase 2.5 human gate step 7",
    )
    _assert_has(
        text,
        "Wired in `~/ai/agents/roadmap-orchestrator.md` § Stage 2c",
    )
    _assert_has(
        text,
        "<!-- INTENTIONAL: \"deferred ticket\", \"deferred marker\", and \"re-defer\"",
    )
    assert "when wired to recognize prototype-needs" not in text
