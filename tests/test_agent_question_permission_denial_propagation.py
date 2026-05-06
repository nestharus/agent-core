import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CONVENTION_PATH = "~/ai/conventions/agent-questions-and-session-graph.md"
CONVENTION_SECTION = "AskUserQuestion Permission-Denial"
CONTRACT_VIOLATION_SENTENCE_PATTERN = (
    r"[Ss]elf-applying defaults on a new-value, scope, or trade-off question after "
    r"`?AskUserQuestion`? is denied is a contract violation"
)
PERMISSION_DENIAL_PATTERN = r"permission[- ](?:denial|denied)"
VALUE_SCOPE_TRADEOFF_PATTERN = (
    r"value(?:/scope)?|\bscope\b|value/scope/trade-off|trade[- ]off"
)
QUESTION_ARTIFACT_MARKER_PATTERN = (
    r"NEEDS_INPUT:<absolute_artifact_path>|NEEDS_INPUT:<question_artifact"
)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _section_after_heading(
    text: str, heading: str, until_pattern: str = r"^#{1,6} "
) -> str:
    """Return the slice from a heading line through the next heading at depth <= heading depth."""
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"

    heading_depth = len(heading) - len(heading.lstrip("#"))
    following = text[match.end() :]
    for next_heading in re.finditer(rf"(?m){until_pattern}", following):
        line_end = following.find("\n", next_heading.start())
        if line_end == -1:
            line_end = len(following)
        next_line = following[next_heading.start() : line_end]
        next_depth = len(next_line) - len(next_line.lstrip("#"))
        if next_depth <= heading_depth:
            return text[match.start() : match.end() + next_heading.start()]
    return text[match.start() :]


def _assert_contains(text: str, needle: str, *, label: str) -> None:
    assert needle in text, f"{label} missing required text: {needle}"


def _assert_matches(
    text: str, pattern: str, *, label: str, flags: int = 0
) -> None:
    assert re.search(pattern, text, flags), (
        f"{label} missing required pattern: {pattern}"
    )


def _assert_not_contains(text: str, needle: str, *, label: str) -> None:
    assert needle not in text, f"{label} unexpectedly contained: {needle}"


def _assert_central_permission_denial_citation(
    text: str, *, label: str, needs_input_pattern: str = QUESTION_ARTIFACT_MARKER_PATTERN
) -> None:
    _assert_contains(text, "AskUserQuestion", label=f"{label}: AskUserQuestion")
    _assert_matches(
        text,
        PERMISSION_DENIAL_PATTERN,
        label=f"{label}: permission-denial term",
    )
    _assert_contains(text, CONVENTION_PATH, label=f"{label}: convention path")
    _assert_contains(text, CONVENTION_SECTION, label=f"{label}: convention section")
    _assert_matches(text, needs_input_pattern, label=f"{label}: NEEDS_INPUT marker")
    _assert_matches(text, r"\bprocedural\b", label=f"{label}: procedural split")
    _assert_matches(
        text,
        VALUE_SCOPE_TRADEOFF_PATTERN,
        label=f"{label}: value/scope/trade-off vocabulary",
    )


def _assert_contract_violation_sentence_count(
    text: str, expected_count: int, *, label: str
) -> None:
    matches = re.findall(CONTRACT_VIOLATION_SENTENCE_PATTERN, text)
    assert len(matches) == expected_count, (
        f"{label} expected {expected_count} contract-violation sentence matches; "
        f"found {len(matches)}"
    )


def test_convention_defines_askuserquestion_permission_denial_rule():
    text = _read("conventions/agent-questions-and-session-graph.md")
    section = _section_after_heading(text, "## AskUserQuestion Permission-Denial")

    _assert_contains(section, "AskUserQuestion", label="convention rule: tool name")
    _assert_matches(
        section,
        PERMISSION_DENIAL_PATTERN,
        label="convention rule: permission-denial term",
    )
    _assert_contains(section, "human-owned", label="convention rule: human-owned")
    _assert_matches(
        section,
        r"value(?:[/, -]scope)?",
        label="convention rule: value term",
    )
    _assert_matches(section, r"\bscope\b", label="convention rule: scope term")
    _assert_matches(
        section, r"trade[- ]off", label="convention rule: trade-off term"
    )
    _assert_contains(
        section,
        "${scratch_dir}/questions/",
        label="convention rule: scratch question directory",
    )
    _assert_contains(
        section,
        "q-<uuidv4>.question.json",
        label="convention rule: question artifact filename",
    )
    _assert_contains(
        section,
        "NEEDS_INPUT:<absolute_artifact_path>",
        label="convention rule: root artifact marker",
    )
    _assert_matches(section, r"\bhalts?\b", label="convention rule: halt behavior")
    _assert_contains(section, "procedural", label="convention rule: procedural split")
    _assert_contains(section, "inline", label="convention rule: inline handling")
    _assert_matches(
        section, r"new[- ]value", label="convention rule: new-value vocabulary"
    )
    _assert_contains(
        section,
        "contract violation",
        label="convention rule: contract violation framing",
    )
    _assert_matches(
        section,
        r"defaults?|decline",
        label="convention rule: no-defaulting forbidden language",
    )
    _assert_matches(
        section,
        r"question[- ]artifact envelope|Question Artifact Schema|question artifact schema|existing question-artifact envelope|sub-agent emission rule",
        label="convention rule: existing envelope reference",
    )
    _assert_contract_violation_sentence_count(
        text, 1, label="convention rule: exact contract-violation sentence"
    )


def test_implementation_pipeline_cites_central_permission_denial_rule():
    text = _read("agents/implementation-pipeline-orchestrator.md")
    sections = {
        "implementation pipeline Non-Negotiables": _section_after_heading(
            text, "## Non-Negotiables"
        ),
        "implementation pipeline Phase 2.5 human gate": _section_after_heading(
            text, "#### Phase 2.5 human gate"
        ),
        "implementation pipeline NEEDS_INPUT Handling": _section_after_heading(
            text, "## NEEDS_INPUT Handling"
        ),
    }

    _assert_central_permission_denial_citation(
        sections["implementation pipeline Non-Negotiables"],
        label="implementation pipeline Non-Negotiables",
        needs_input_pattern=r"NEEDS_INPUT:<absolute_artifact_path>",
    )
    _assert_central_permission_denial_citation(
        sections["implementation pipeline Phase 2.5 human gate"],
        label="implementation pipeline Phase 2.5 human gate",
        needs_input_pattern=r"NEEDS_INPUT",
    )
    _assert_central_permission_denial_citation(
        sections["implementation pipeline NEEDS_INPUT Handling"],
        label="implementation pipeline NEEDS_INPUT Handling",
        needs_input_pattern=r"NEEDS_INPUT:<absolute_artifact_path>",
    )

    combined_sections = "\n".join(sections.values())
    _assert_contract_violation_sentence_count(
        combined_sections,
        0,
        label="implementation pipeline citation sections: no local body sentence",
    )
    _assert_contract_violation_sentence_count(
        text, 0, label="implementation pipeline file: no local body sentence"
    )


def test_prototype_orchestrator_cites_central_permission_denial_rule():
    text = _read("agents/prototype-orchestrator.md")
    section = _section_after_heading(text, "## NEEDS_INPUT Handling")

    _assert_central_permission_denial_citation(
        section, label="prototype orchestrator NEEDS_INPUT Handling"
    )


def test_roadmap_orchestrator_cites_central_permission_denial_rule():
    text = _read("agents/roadmap-orchestrator.md")

    _assert_contains(
        text,
        "## NEEDS_INPUT Handling",
        label="roadmap orchestrator: new NEEDS_INPUT Handling heading",
    )
    risk_position = text.index("## Risk Resolution Protocol")
    needs_input_position = text.index("## NEEDS_INPUT Handling")
    run_report_position = text.index("## Run Report")
    assert risk_position < needs_input_position < run_report_position, (
        "roadmap orchestrator NEEDS_INPUT Handling must be between "
        "Risk Resolution Protocol and Run Report"
    )

    section = _section_after_heading(text, "## NEEDS_INPUT Handling")
    _assert_central_permission_denial_citation(
        section, label="roadmap orchestrator NEEDS_INPUT Handling"
    )


def test_alignment_cycle_orchestrator_cites_central_permission_denial_rule():
    text = _read("agents/alignment-cycle-orchestrator.md")
    section = _section_after_heading(text, "#### Stage 2b-classify")

    _assert_contains(
        section,
        "philosophy-decisions.md",
        label="alignment cycle Stage 2b-classify: preserve domain gate",
    )
    _assert_central_permission_denial_citation(
        section, label="alignment cycle Stage 2b-classify"
    )
    _assert_not_contains(
        text,
        "## NEEDS_INPUT Handling",
        label="alignment cycle: no alternate NEEDS_INPUT Handling section",
    )


def test_agentsmd_maintenance_orchestrator_cites_central_permission_denial_rule():
    text = _read("agents/agentsmd-maintenance-orchestrator.md")
    stop_conditions = _section_after_heading(text, "## Stop Conditions")
    output_contract = _section_after_heading(text, "## Output Contract")

    _assert_central_permission_denial_citation(
        stop_conditions,
        label="AGENTS maintenance Stop Conditions",
        needs_input_pattern=r"NEEDS_INPUT:<absolute_artifact_path>",
    )
    _assert_matches(
        stop_conditions,
        rf"(?:{PERMISSION_DENIAL_PATTERN}[^.\n]*?NEEDS_INPUT:<absolute_artifact_path>|NEEDS_INPUT:<absolute_artifact_path>[^.\n]*?{PERMISSION_DENIAL_PATTERN})",
        label="AGENTS maintenance Stop Conditions: single-sentence permission-denial artifact binding",
    )
    _assert_contains(
        output_contract,
        "NEEDS_INPUT:<reason>",
        label="AGENTS maintenance Output Contract: legacy reason marker",
    )
    _assert_contains(
        output_contract,
        "NEEDS_INPUT:<absolute_artifact_path>",
        label="AGENTS maintenance Output Contract: permission-denial artifact marker",
    )
    _assert_matches(
        output_contract,
        PERMISSION_DENIAL_PATTERN,
        label="AGENTS maintenance Output Contract: permission-denial clarification",
    )
    _assert_matches(
        output_contract,
        VALUE_SCOPE_TRADEOFF_PATTERN,
        label="AGENTS maintenance Output Contract: value/scope/trade-off clarification",
    )


@pytest.mark.parametrize(
    "rel",
    [
        "agents/implementation-pipeline-orchestrator.md",
        "agents/prototype-orchestrator.md",
        "agents/roadmap-orchestrator.md",
        "agents/alignment-cycle-orchestrator.md",
        "agents/agentsmd-maintenance-orchestrator.md",
    ],
)
def test_all_orchestrator_citations_match_convention_section_name(rel):
    text = _read(rel)

    _assert_contains(
        text,
        CONVENTION_SECTION,
        label=f"{rel}: exact convention section citation",
    )
    _assert_contains(text, CONVENTION_PATH, label=f"{rel}: convention path citation")
