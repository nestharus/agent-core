"""Structural tests for the NES-168 wu-session-resumer operator."""

import re
from pathlib import Path


OPERATOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "agents"
    / "wu-session-resumer.md"
)

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Inputs",
    "Procedure",
    "Outputs",
    "Stop Conditions",
    "Anti-scope",
)
REQUIRED_INPUTS = (
    "pr_url",
    "merge_sha",
    "head_sha",
    "pre_merge_main_sha",
    "branch_name",
    "ticket_id",
    "session_manifest_path",
)
OPTIONAL_COMMAND_INPUTS = ("test_command", "coverage_command")
FORBIDDEN_CODE_BLOCK_LANGUAGES = (
    "rust",
    "typescript",
    "ts",
    "javascript",
    "js",
    "powershell",
    "ps1",
)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/wu-session-resumer.md"
    return OPERATOR_PATH.read_text(encoding="utf-8")


def _frontmatter_and_body(text):
    assert text.startswith("---\n"), "operator file must start with YAML frontmatter"
    closing = text.find("\n---\n", len("---\n"))
    assert closing != -1, "operator file must close YAML frontmatter before body"
    frontmatter = text[len("---\n") : closing]
    body = text[closing + len("\n---\n") :]
    assert body.strip(), "operator body must follow YAML frontmatter"
    return frontmatter, body


def _parse_frontmatter(text):
    frontmatter_text, _body = _frontmatter_and_body(text)
    frontmatter = {}
    for line in frontmatter_text.splitlines():
        if not line.strip():
            continue
        assert not line.startswith((" ", "\t")), (
            f"frontmatter key must be top-level: {line}"
        )
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip()
    return frontmatter


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _operator_body():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    return body


def _near(text, first, second, distance=300):
    escaped_first = re.escape(first)
    escaped_second = re.escape(second)
    return bool(
        re.search(
            rf"{escaped_first}.{{0,{distance}}}{escaped_second}"
            rf"|{escaped_second}.{{0,{distance}}}{escaped_first}",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )


def test_operator_file_exists():
    assert OPERATOR_PATH.exists()


def test_frontmatter_keys_exact_match():
    frontmatter = _parse_frontmatter(_operator_text())

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS


def test_frontmatter_description_non_empty():
    frontmatter = _parse_frontmatter(_operator_text())

    assert frontmatter["description"].strip("'\"")


def test_frontmatter_model_is_gpt_high():
    frontmatter = _parse_frontmatter(_operator_text())

    assert frontmatter["model"] == "gpt-high"


def test_frontmatter_output_format_empty_quotes():
    frontmatter = _parse_frontmatter(_operator_text())

    assert frontmatter["output_format"] == "''"


def test_required_h2_sections_present_in_order():
    body = _operator_body()
    h2s = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

    assert tuple(h2s) == REQUIRED_H2_HEADINGS


def test_inputs_section_lists_required_fields():
    inputs = _section_after_h2(_operator_body(), "Inputs")

    for input_name in REQUIRED_INPUTS:
        assert input_name in inputs, f"Inputs section must list {input_name}"


def test_inputs_section_marks_optional_command_fields():
    inputs = _section_after_h2(_operator_body(), "Inputs")

    for input_name in OPTIONAL_COMMAND_INPUTS:
        assert input_name in inputs, f"Inputs section must list {input_name}"
        assert _near(inputs, input_name, "optional", distance=120), (
            f"Inputs section must mark {input_name} optional"
        )


def test_inputs_section_rejects_ambiguous_base_sha():
    inputs = _section_after_h2(_operator_body(), "Inputs")
    backticked_flags = set(re.findall(r"`([A-Za-z0-9_]+)`", inputs))

    assert "base_sha" not in backticked_flags


def test_inputs_section_mentions_branch_out_sha_from_manifest():
    inputs = _section_after_h2(_operator_body(), "Inputs")
    lower_inputs = inputs.lower()

    assert "branch_out_sha" in inputs
    assert _near(inputs, "branch_out_sha", "manifest", distance=160)
    if _near(inputs, "branch_out_sha", "merge event", distance=160):
        assert re.search(
            r"(?is)(branch_out_sha.{0,180}not.{0,40}merge event"
            r"|not.{0,40}merge event.{0,180}branch_out_sha)",
            lower_inputs,
        )


def test_procedure_step_test_rerun():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    lower_procedure = procedure.lower()

    assert "test rerun" in lower_procedure or "test re-run" in lower_procedure
    assert "post_merge.test_rerun_status" in procedure


def test_procedure_step_coverage():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    lower_procedure = procedure.lower()

    assert "coverage" in lower_procedure
    assert "post_merge.coverage_delta" in procedure


def test_procedure_step_contract_verify():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    lower_procedure = procedure.lower()

    assert "contract verif" in lower_procedure
    assert "post_merge.contract_verify" in procedure
    assert "step6b-output-index.md" in procedure


def test_procedure_step_drift_delegate():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    assert "~/ai/agents/rebase-drift-checker.md" in procedure


def test_procedure_step_prep_next_wu():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    assert "successor_session_brief" in procedure


def test_procedure_step_ticket_cross_link():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    assert "linear-operator" in procedure
    assert "jira-operator" in procedure


def test_procedure_step_disposition_before_close_gate():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    lower_procedure = procedure.lower()

    assert "disposition-before-close" in lower_procedure
    assert "closed_at" in procedure
    assert _near(procedure, "disposition-before-close", "closed_at", distance=300)
    assert re.search(
        r"(?is)(before|protect|gate|until).{0,180}closed_at"
        r"|closed_at.{0,180}(after|protect|gate|until)",
        procedure,
    )


def test_stop_conditions_vocabulary():
    stop_conditions = _section_after_h2(_operator_body(), "Stop Conditions")

    for token in ("BLOCKED:", "NEEDS_INPUT:", "record-and-continue"):
        assert token in stop_conditions


def test_stop_conditions_bind_failed_test_rerun_to_disposition_gate():
    stop_conditions = _section_after_h2(_operator_body(), "Stop Conditions")

    assert "post_merge.test_rerun_status" in stop_conditions
    assert "failed" in stop_conditions.lower()
    assert "disposition-before-close" in stop_conditions.lower()
    assert _near(
        stop_conditions,
        "post_merge.test_rerun_status",
        "disposition-before-close",
        distance=300,
    )


def test_stop_conditions_bind_drift_to_disposition_gate():
    stop_conditions = _section_after_h2(_operator_body(), "Stop Conditions")

    assert "post_merge.contract_verify" in stop_conditions
    assert "drift" in stop_conditions.lower()
    assert "disposition-before-close" in stop_conditions.lower()
    assert _near(
        stop_conditions,
        "post_merge.contract_verify",
        "disposition-before-close",
        distance=300,
    )


def test_anti_scope_section_excludes_scheduling():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert "not schedule" in anti_scope or "does not schedule" in anti_scope


def test_anti_scope_section_excludes_polling():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert "not poll" in anti_scope or "does not poll" in anti_scope


def test_anti_scope_section_excludes_batch():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert (
        "not batch" in anti_scope
        or "no batch logic" in anti_scope
        or "no pr batching" in anti_scope
    )


def test_anti_scope_section_excludes_multi_session_dispatch():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert "multi-session" in anti_scope


def test_anti_scope_section_excludes_modifying_lifecycle_convention():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert "wu-session-lifecycle.md" in anti_scope
    assert (
        "not modify" in anti_scope
        or "does not modify" in anti_scope
        or "read-only" in anti_scope
    )


def test_anti_scope_section_excludes_spawning_successor():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert "not spawn" in anti_scope or "does not spawn" in anti_scope
    assert "successor" in anti_scope


def test_anti_scope_section_excludes_transition_ticket_status():
    anti_scope = _section_after_h2(_operator_body(), "Anti-scope").lower()

    assert "transition ticket status" in anti_scope


def test_question_artifact_filename_pattern_correct():
    body = _operator_body()

    assert "q-<uuidv4>.question.json" in body


def test_question_artifact_disposition_filename_pattern_forbidden():
    body = _operator_body()

    assert "q-disposition-" not in body


def test_question_convention_referenced():
    body = _operator_body()

    assert "agent-questions-and-session-graph.md" in body


def test_needs_input_return_string_format():
    body = _operator_body()

    assert "NEEDS_INPUT:<absolute_artifact_path>" in body


def test_use_when_names_one_merge_event_per_session():
    use_when = _section_after_h2(_operator_body(), "Use When").lower()

    assert "one merge event" in use_when
    assert "one session" in use_when


def test_do_not_use_when_rejects_scheduler_poller_webhook():
    do_not_use = _section_after_h2(_operator_body(), "Do Not Use When").lower()

    assert "scheduler" in do_not_use
    assert "poller" in do_not_use
    assert "webhook" in do_not_use


def test_outputs_section_names_required_artifacts():
    outputs = _section_after_h2(_operator_body(), "Outputs").lower()

    for token_group in (
        ("manifest update", "update manifest", "manifest"),
        ("audit-history", "audit history"),
        ("ticket comment",),
        ("drift report",),
        ("successor brief", "successor_session_brief"),
    ):
        assert any(token in outputs for token in token_group), (
            f"Outputs section must mention one of {token_group}"
        )


def test_outputs_section_names_drift_report_manifest_field():
    outputs = _section_after_h2(_operator_body(), "Outputs")
    procedure = _section_after_h2(_operator_body(), "Procedure")
    drift_steps = [
        step for step in re.split(r"(?m)^\d+\.\s+", procedure)
        if "drift" in step.lower()
    ]

    assert "post_merge.drift_report_path" in outputs or any(
        "post_merge.drift_report_path" in step for step in drift_steps
    )


def test_no_rust_typescript_javascript_powershell_artifacts():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    language_pattern = "|".join(
        re.escape(language) for language in FORBIDDEN_CODE_BLOCK_LANGUAGES
    )

    assert not re.search(
        rf"(?im)^```\s*(?:{language_pattern})\b",
        body,
    )


def test_role_section_non_empty():
    role = _section_after_h2(_operator_body(), "Role")

    assert role.strip()


def test_procedure_step_validate_inputs():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    assert "validate inputs" in procedure.lower()


def test_procedure_step_manifest_read():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    lower_procedure = procedure.lower()

    assert "session_manifest_path" in procedure
    assert "Read" in procedure or "read " in lower_procedure or "parse" in lower_procedure


def test_procedure_step_manifest_identity_validation():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    steps = re.split(r"(?m)^\d+\.\s+", procedure)
    matching_steps = [
        step for step in steps if "validate manifest identity" in step.lower()
    ]

    assert matching_steps
    identity_step = matching_steps[0]
    for token in ("ticket_id", "branch", "head_sha"):
        assert token in identity_step


def test_procedure_step_sync_main_to_merge_sha():
    procedure = _section_after_h2(_operator_body(), "Procedure")
    steps = re.split(r"(?m)^\d+\.\s+", procedure)
    sync_phrases = (
        "Sync local main",
        "Sync main",
        "update main to",
        "sync local main",
    )

    for step in steps:
        normalized_step = step.replace("`", "")
        if "merge_sha" in step and any(
            phrase in normalized_step for phrase in sync_phrases
        ):
            return
    assert False, "Procedure must sync local main to merge_sha in one step"


def test_procedure_does_not_defer_internal_checks():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    for forbidden in (
        "test-rerun-runner.md",
        "coverage-regression-operator.md",
        "contract-verifier.md",
        "deferred to follow-up",
        "defer to follow-up",
        "not yet implemented",
        "TODO",
        "TBD",
    ):
        assert forbidden not in procedure


def test_outputs_section_names_check_report_artifacts():
    outputs = _section_after_h2(_operator_body(), "Outputs")
    lines = outputs.splitlines()

    for keyword in ("test-rerun", "coverage", "contract"):
        matching_lines = [line for line in lines if keyword in line.lower()]
        assert matching_lines, f"Outputs section must mention {keyword}"
        assert any(
            ".md" in line or "${planning_dir}/reports/" in line
            for line in matching_lines
        ), f"Outputs section must name a path-like artifact for {keyword}"
