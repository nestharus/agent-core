import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TICKET_GENERATION_AGENT = REPO_ROOT / "agents" / "ticket-generation-agent.md"
JIRA_OPERATOR = REPO_ROOT / "agents" / "jira-operator.md"
LINEAR_OPERATOR = REPO_ROOT / "agents" / "linear-operator.md"
ROADMAP_WORKFLOW = REPO_ROOT / "workflows" / "roadmap.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _h2_section(text: str, heading: str) -> str:
    match = re.search(rf"(?m)^## {re.escape(heading)}\s*$", text)
    assert match, f"missing H2 section: {heading}"
    following = text[match.end() :]
    next_h2 = re.search(r"(?m)^## ", following)
    if next_h2:
        return following[: next_h2.start()]
    return following


def _h2_section_starting_with(text: str, heading_prefix: str) -> str:
    match = re.search(rf"(?m)^## {re.escape(heading_prefix)}.*$", text)
    assert match, f"missing H2 section starting with: {heading_prefix}"
    following = text[match.end() :]
    next_h2 = re.search(r"(?m)^## ", following)
    if next_h2:
        return following[: next_h2.start()]
    return following


def _template_region(text: str, template_name: str) -> str:
    heading = f"## Output format: `tickets/{template_name}`"
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    assert match, f"missing template region: {template_name}"
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^## Output format: `tickets/", following)
    if next_heading:
        return following[: next_heading.start()]
    next_quality = re.search(r"(?m)^## Quality checklist\s*$", following)
    if next_quality:
        return following[: next_quality.start()]
    return following


def _routing_row(text: str, name: str) -> str:
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"missing operator row: {name}"
    return match.group(0)


def test_outputs_h2_present_in_ticket_generation_agent() -> None:
    _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")


def test_outputs_h2_lists_all_three_estimate_fields() -> None:
    outputs = _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")

    for field_name in (
        "story_point_estimate",
        "estimate_source",
        "estimate_rationale",
    ):
        assert field_name in outputs


def test_outputs_h2_lists_full_fibonacci_allowed_set() -> None:
    outputs = _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")

    assert "1, 2, 3, 5, 8, 13, 21, 40, 100" in outputs


def test_outputs_h2_lists_full_estimate_source_enum() -> None:
    outputs = _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")

    for source in (
        "prototype-dossier",
        "layer-2-magnitude",
        "layer-3-slice",
        "backstop-spike",
    ):
        assert source in outputs


def test_outputs_h2_states_priority_order_verbatim() -> None:
    outputs = _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")

    assert (
        "prototype-dossier > layer-2-magnitude > layer-3-slice > backstop-spike"
        in outputs
    )


def test_outputs_h2_states_init_remains_unsized() -> None:
    outputs = _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")

    assert re.search(r"(?is)\bINIT\b.{0,80}\bremain[s]?\b.{0,40}\bunsized\b", outputs)


def test_outputs_h2_states_layer_4_markdown_only() -> None:
    outputs = _h2_section(_read(TICKET_GENERATION_AGENT), "Outputs")

    assert re.search(r"(?is)Layer 4.{0,80}markdown-only", outputs)
    assert "customfield_10016" in outputs
    assert re.search(r"(?is)\bLinear\b.{0,80}\bestimate\b", outputs)
    assert re.search(r"(?is)downstream.{0,80}(filer|operator)", outputs)


def test_slice_template_has_story_point_estimate_field() -> None:
    slice_template = _template_region(_read(TICKET_GENERATION_AGENT), "SLICE-NNN.md")

    assert "**Story Point Estimate:**" in slice_template


def test_slice_template_has_estimate_source_field() -> None:
    slice_template = _template_region(_read(TICKET_GENERATION_AGENT), "SLICE-NNN.md")

    assert "**Estimate Source:**" in slice_template


def test_slice_template_has_estimate_rationale_field() -> None:
    slice_template = _template_region(_read(TICKET_GENERATION_AGENT), "SLICE-NNN.md")

    assert "**Estimate Rationale:**" in slice_template


def test_init_template_does_not_have_story_point_estimate() -> None:
    text = _read(TICKET_GENERATION_AGENT)
    init_template = _template_region(text, "INIT-NNN.md")
    outputs = _h2_section(text, "Outputs")

    assert "**Story Point Estimate:**" not in init_template
    assert re.search(r"(?is)\bINIT\b.{0,80}\bremain[s]?\b.{0,40}\bunsized\b", outputs)


def test_index_template_has_story_points_column() -> None:
    index_template = _template_region(_read(TICKET_GENERATION_AGENT), "INDEX.md")

    assert re.search(r"(?m)^\|.*Story Points.*\|$", index_template)


def test_guardrail_no_independent_estimation_rephrased() -> None:
    guardrails = _h2_section_starting_with(
        _read(TICKET_GENERATION_AGENT),
        "Guardrails",
    )

    assert not re.search(
        r"Does not estimate effort independently.{0,5}effort comes from the engineering roadmap",
        guardrails,
    )
    assert re.search(r"(?is)does not invent independent estimates", guardrails)
    assert re.search(r"(?is)source.{0,40}priority", guardrails)


def test_effort_field_retained_with_inherited_qualifier() -> None:
    text = _read(TICKET_GENERATION_AGENT)
    init_template = _template_region(text, "INIT-NNN.md")
    slice_template = _template_region(text, "SLICE-NNN.md")

    for template in (init_template, slice_template):
        assert re.search(r"\*\*Effort(?:\s*\([^)]*inherited from engineering roadmap[^)]*\))?:\*\*", template)
        assert re.search(r"(?is)Effort.{0,80}inherited from engineering roadmap", template)


def test_jira_operator_has_customfield_10016_example() -> None:
    create_section = _h2_section(_read(JIRA_OPERATOR), "Procedure: Create")

    assert "customfield_10016" in create_section
    assert re.search(r"customfield_10016['\"]?\s*:\s*5\b", create_section)


def test_linear_operator_documents_estimate_input() -> None:
    required_inputs = _h2_section(_read(LINEAR_OPERATOR), "Required Inputs")

    assert re.search(r"`?estimate`?\s*=\s*<int>", required_inputs)
    assert re.search(r"(?is)estimate.{0,120}fibonacci", required_inputs)
    assert re.search(r"(?is)task.{0,80}create|create.{0,80}estimate", required_inputs)


def test_linear_operator_create_example_has_estimate_flag() -> None:
    create_section = _h2_section(_read(LINEAR_OPERATOR), "Procedure: Create")

    assert "--estimate <int>" in create_section or re.search(r"--estimate\s+5\b", create_section)
    assert re.search(r"(?is)optional.{0,80}story-point estimate|story-point estimate.{0,80}optional", create_section)


def test_roadmap_layer_4_mentions_story_point_estimate() -> None:
    layer_4 = re.search(
        r"(?ms)^### Layer 4 - Ticket generation\s*(.*?)(?=^## |^### |\Z)",
        _read(ROADMAP_WORKFLOW),
    )
    assert layer_4, "missing roadmap Layer 4 section"
    section = layer_4.group(1)

    assert "story-point estimate" in section
    assert "estimate source" in section
    assert "estimate rationale" in section
    assert re.search(r"(?is)\bINIT\b.{0,80}\bunsized\b", section)


def test_agents_md_ticket_generation_row_mentions_estimate() -> None:
    row = _routing_row(_read(AGENTS_MD), "ticket-generation-agent")

    assert re.search(r"(?is)story-point|estimate", row)
    assert re.search(r"(?is)provenance|source|rationale", row)
