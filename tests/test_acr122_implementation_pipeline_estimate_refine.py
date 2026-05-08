import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / "workflows" / "implementation-pipeline.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"(?m)^{re.escape(heading)}(?:\s|$).*", text)
    assert match, f"missing heading: {heading}"
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^## ", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _routing_row(text: str, name: str) -> str:
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"missing operator row: {name}"
    return match.group(0)


def test_workflow_phase1_documents_inherited_estimate_read_contract() -> None:
    text = _read(WORKFLOW)
    phase1 = _section(text, "## Phase 1 - Problem Research")

    for required in (
        "${scratch_dir}/ticket.md",
        "story_point_estimate",
        "estimate_source",
        "estimate_rationale",
        "estimate_field",
        "customfield_10016",
        "Linear",
        "backstop-spike",
        "missing",
        "NEEDS_INPUT",
        "problem map",
        "verbatim",
    ):
        assert required in phase1


def test_workflow_phase3_requires_refined_estimate_outputs_and_delta_flag() -> None:
    phase3 = _section(_read(WORKFLOW), "## Phase 3 - Proposal")

    for required in (
        "## Estimate refinement",
        "```yaml",
        "refined_story_point_estimate",
        "estimate_delta_rationale",
        "inherited_story_point_estimate",
        "estimate_source",
        "estimate_delta_flag",
        "over_2x",
        "task=update-estimate",
        "${scratch_dir}/prompts/${wu_lower}-phase-3-update-estimate.md",
        "${scratch_dir}/logs/${wu_lower}-phase-3-update-estimate.log",
    ):
        assert required in phase3
    assert ">2x" in phase3 or "> 2x" in phase3


def test_orchestrator_phase0_ticket_read_requires_estimate_metadata() -> None:
    phase0 = _section(_read(ORCHESTRATOR), "### Phase 0")

    for required in (
        "task=read",
        "${scratch_dir}/ticket.md",
        "frontmatter",
        "story_point_estimate",
        "estimate_source",
        "estimate_rationale",
        "estimate_field",
    ):
        assert required in phase0


def test_orchestrator_problem_map_prompt_carries_inherited_estimate() -> None:
    phase25 = _section(_read(ORCHESTRATOR), "### Phase 2.5")

    for required in (
        "${scratch_dir}/prompts/${wu_lower}-phase-2.5-problem-map.md",
        "inherited estimate",
        "story_point_estimate",
        "estimate_source",
        "estimate_rationale",
        "backstop-spike",
        "missing",
        "disposition",
    ):
        assert required in phase25
    assert re.search(r"(?is)before.{0,80}Phase 3", phase25)


def test_backstop_spike_routes_as_new_value_question_artifact() -> None:
    text = _read(WORKFLOW) + "\n" + _read(ORCHESTRATOR)

    for required in (
        "backstop-spike",
        "missing",
        "${scratch_dir}/questions/q-<uuidv4>.question.json",
        "NEEDS_INPUT:<absolute_artifact_path>",
        "single_choice",
        "Run a small prototype first",
        "Proceed without a baseline estimate",
        "Terminate WU",
    ):
        assert required in text
    assert re.search(r"(?is)new-value.{0,80}(value|scope|trade-off)", text)


def test_orchestrator_phase3_verifies_refined_estimate_outputs() -> None:
    phase3 = _section(_read(ORCHESTRATOR), "### Phase 3")

    for required in (
        "artifact verification",
        "## Estimate refinement",
        "```yaml",
        "refined_story_point_estimate",
        "estimate_delta_rationale",
        "estimate_delta_flag",
    ):
        assert required in phase3
    assert "fenced YAML block" in phase3 or "fenced `yaml` block" in phase3


def test_orchestrator_dispatches_update_estimate_before_phase4() -> None:
    phase3 = _section(_read(ORCHESTRATOR), "### Phase 3")

    for required in (
        "Pre-Phase-4 update-estimate dispatch",
        "${scratch_dir}/prompts/${wu_lower}-phase-3-update-estimate.md",
        "${scratch_dir}/logs/${wu_lower}-phase-3-update-estimate.log",
        "${ticket_operator}",
        "task=update-estimate",
        "issue_key",
        "estimate",
        "inherited_story_point_estimate",
        "estimate_source",
        "estimate_delta_rationale",
        "estimate_delta_flag",
        "2xx",
    ):
        assert required in phase3
    assert re.search(r"(?is)after.{0,80}Phase 3.{0,120}before.{0,80}Phase 4", phase3)


def test_orchestrator_phase4_scope_prompt_receives_estimate_delta_flag() -> None:
    text = _read(ORCHESTRATOR)
    phase4 = _section(text, "### Phase 4")

    for required in (
        "scope",
        "estimate_delta_flag",
        "inherited",
        "refined",
        "over_2x",
        "rationale",
        "unknown",
    ):
        assert required in phase4
    assert "no sidecar JSON" in text or "derived in-memory input" in text


def test_agents_row_mentions_estimate_read_refine_writeback() -> None:
    row = _routing_row(_read(AGENTS_MD), "implementation-pipeline-orchestrator")

    assert re.search(r"(?is)inherited.{0,40}estimate.{0,40}read", row)
    assert re.search(r"(?is)Phase 3.{0,60}(refine|refinement)", row)
    assert re.search(r"(?is)ticket.{0,60}(write-back|writeback)", row)
    assert "status" in row
