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
        r"\bvalue(?:/scope)?\b|\bscope\b",
        "value/scope split",
    )
    _assert_contains(section, section_name, "NEEDS_INPUT:<")
    _assert_contains(
        section,
        section_name,
        "~/ai/conventions/agent-questions-and-session-graph.md",
    )
    _assert_contains(section, section_name, "AskUserQuestion Permission-Denial")
    _assert_matches(section, section_name, r"\bprocedural\b", "procedural split")
    _assert_matches(section, section_name, r"\binline\b", "inline procedural handling")


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
    _assert_contains(section, section_name, "NEEDS_INPUT")
    _assert_contains(section, section_name, "agent-questions-and-session-graph.md")
    _assert_contains(section, section_name, "AskUserQuestion Permission-Denial")


def test_needs_input_handling_covers_sub_agents_and_orchestrator_permission_denial():
    section_name = "NEEDS_INPUT Handling"
    section = _section_after_heading(_orchestrator_text(), "## NEEDS_INPUT Handling")

    _assert_contains(section, section_name, "sub-agent")
    _assert_contains(section, section_name, "AskUserQuestion")
    _assert_matches(section, section_name, r"\bprocedural\b", "procedural split")
    _assert_matches(section, section_name, r"\bvalue(?:/scope)?\b", "value/scope split")
    _assert_matches(section, section_name, r"\bscope\b", "scope split")
    _assert_contains(
        section,
        section_name,
        "~/ai/conventions/agent-questions-and-session-graph.md",
    )
    _assert_contains(section, section_name, "AskUserQuestion Permission-Denial")
    _assert_matches(
        section,
        section_name,
        r"permission[- ](?:denial|denied)",
        "permission-denial term",
    )
    _assert_matches(
        section,
        section_name,
        r"NEEDS_INPUT:<absolute_artifact_path>|NEEDS_INPUT:<question_artifact",
        "question artifact marker",
    )


def test_entry_mode_preflight_missing_target_identity_uses_question_artifact():
    section_name = "entry-mode preflight missing target identity"
    text = _orchestrator_text()

    _assert_matches(
        text,
        section_name,
        r"(?is)(?:entry-mode|pipeline_entry_mode|review_first).{0,800}missing target identity.{0,800}NEEDS_INPUT:<absolute_artifact_path>",
        "missing target identity NEEDS_INPUT",
    )
    _assert_contains(text, section_name, "${scratch_dir}/questions/")
    _assert_matches(
        text,
        section_name,
        r"q-<uuidv4>\.question\.json",
        "question artifact filename",
    )


def test_entry_mode_preflight_stale_bundle_needs_input_fallback_uses_question_artifact():
    section_name = "entry-mode preflight stale bundle needs_input fallback"
    text = _orchestrator_text()

    _assert_matches(
        text,
        section_name,
        r"(?is)stale bundle.{0,800}review_staleness_fallback=needs_input.{0,800}NEEDS_INPUT:<absolute_artifact_path>",
        "stale bundle needs_input fallback NEEDS_INPUT",
    )
    _assert_contains(text, section_name, "${scratch_dir}/questions/")
    _assert_matches(
        text,
        section_name,
        r"q-<uuidv4>\.question\.json",
        "question artifact filename",
    )


def test_required_review_staleness_policy_reruns_review_first_without_question():
    section_name = "required staleness policy"
    text = _orchestrator_text()

    _assert_matches(
        text,
        section_name,
        r"(?is)review_staleness_policy=required.{0,160}(?:always reruns|dispatch a fresh) `?review_first`?",
        "required policy reruns review_first",
    )
    _assert_matches(
        text,
        section_name,
        r"(?is)review_staleness_policy=required.{0,260}prior bundle as context",
        "required policy treats prior bundle as context",
    )


def test_entry_mode_preflight_user_owned_staleness_choice_uses_question_artifact():
    section_name = "entry-mode preflight user-owned staleness choice"
    text = _orchestrator_text()

    _assert_matches(
        text,
        section_name,
        r"(?is)user-owned.{0,300}staleness.{0,300}choice.{0,800}NEEDS_INPUT:<absolute_artifact_path>",
        "user-owned staleness choice NEEDS_INPUT",
    )
    _assert_contains(text, section_name, "${scratch_dir}/questions/")
    _assert_matches(
        text,
        section_name,
        r"q-<uuidv4>\.question\.json",
        "question artifact filename",
    )
