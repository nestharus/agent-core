import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _orchestrator_text():
    return ORCHESTRATOR.read_text(encoding="utf-8")


def _section_after_heading(text, heading, terminator_pattern=r"^##\s+"):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    following = text[match.end() :]
    next_heading = re.search(rf"(?m){terminator_pattern}", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _assert_contains(section, section_name, needle):
    assert needle in section, f"{section_name} missing required text: {needle}"


def _assert_matches(section, section_name, pattern, description):
    assert re.search(pattern, section), (
        f"{section_name} missing required pattern for {description}: {pattern}"
    )


def test_non_negotiables_define_askuserquestion_permission_denial_artifact_rule():
    section_name = "Non-Negotiables"
    section = _section_after_heading(_orchestrator_text(), "## Non-Negotiables")

    _assert_contains(section, section_name, "AskUserQuestion")
    _assert_matches(
        section,
        section_name,
        r"permission[- ](?:denial|denied)",
        "permission-denial term",
    )
    _assert_matches(
        section,
        section_name,
        r"q-<uuidv4>\.question\.json",
        "question id or artifact filename",
    )
    _assert_contains(section, section_name, "${scratch_dir}/questions/")
    _assert_contains(section, section_name, "NEEDS_INPUT:<")
    _assert_matches(section, section_name, r"\bhalts?\b", "halt behavior")
    _assert_contains(
        section,
        section_name,
        "~/ai/conventions/agent-questions-and-session-graph.md",
    )
    _assert_matches(section, section_name, r"\bprocedural\b", "procedural split")
    _assert_matches(section, section_name, r"\bnew[- ]value\b", "new-value split")
    _assert_matches(section, section_name, r"\binline\b", "inline procedural handling")
    _assert_matches(
        section,
        section_name,
        r"\bcontract violation\b",
        "contract violation framing",
    )


def test_phase_2_5_human_gate_defines_permission_denial_question_artifact_fallback():
    section_name = "Phase 2.5 human gate"
    section = _section_after_heading(
        _orchestrator_text(),
        "#### Phase 2.5 human gate",
        terminator_pattern=r"^(?:####|###)\s+",
    )

    _assert_contains(section, section_name, "AskUserQuestion")
    _assert_matches(
        section,
        section_name,
        r"permission[- ](?:denial|denied)",
        "permission-denial term",
    )
    _assert_matches(
        section,
        section_name,
        r"(?:q-<uuidv4>|\.question\.json)",
        "question id or JSON artifact filename",
    )
    _assert_contains(section, section_name, "NEEDS_INPUT")
    _assert_contains(section, section_name, "agent-questions-and-session-graph.md")


def test_needs_input_handling_covers_sub_agents_and_orchestrator_permission_denial():
    section_name = "NEEDS_INPUT Handling"
    section = _section_after_heading(_orchestrator_text(), "## NEEDS_INPUT Handling")

    _assert_contains(section, section_name, "sub-agent")
    _assert_contains(section, section_name, "AskUserQuestion")
    _assert_matches(section, section_name, r"\bprocedural\b", "procedural split")
    _assert_matches(section, section_name, r"\bvalue(?:/scope)?\b", "value/scope split")
    _assert_matches(section, section_name, r"\bscope\b", "scope split")
