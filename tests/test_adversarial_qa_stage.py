"""Structural contract tests for the ACR-149 adversarial QA stage workflow."""

import pathlib
import re
import subprocess

import pytest


# ## Declared roles
# Declared roles: orchestration, filter, validator, predicate, mapper, accessor, parser

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / "workflows" / "adversarial-qa-stage.md"
OPERATOR_PATH = REPO_ROOT / "agents" / "adversarial-qa-driver.md"
EVAL_RUNTIME_PATH = REPO_ROOT / "workflows" / "eval-runtime.md"
TEST_PATH = REPO_ROOT / "tests" / "test_adversarial_qa_stage.py"

A1_VOCABULARY = {
    "orchestration",
    "filter",
    "validator",
    "predicate",
    "mapper",
    "accessor",
    "formatter",
    "parser",
}


def _path_must_exist(path: pathlib.Path) -> pathlib.Path:
    assert path.exists(), f"missing required file: {path}"
    return path


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _lower_text(text: str) -> str:
    return text.lower()


def _missing_items(text: str, required: list[str]) -> list[str]:
    lowered = text.lower()
    return [item for item in required if item.lower() not in lowered]


def _assert_no_missing(missing: list[str], label: str) -> None:
    assert not missing, f"{label} missing required text: {missing}"


def _assert_contains_all(text: str, required: list[str], label: str) -> None:
    _assert_no_missing(_missing_items(text, required), label)


def _has_heading(text: str, heading: str) -> bool:
    pattern = rf"(?im)^##\s+{re.escape(heading)}\s*$"
    return bool(re.search(pattern, text))


def _assert_heading(text: str, heading: str, label: str) -> None:
    assert _has_heading(text, heading), f"{label} missing heading: ## {heading}"


def _split_frontmatter(text: str) -> tuple[list[str], int | None, str]:
    lines = text.splitlines()
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    frontmatter = "\n".join(lines[1:closing_index]) if closing_index is not None else ""
    return lines, closing_index, frontmatter


def _assert_frontmatter_delimiters(
    lines: list[str],
    closing_index: int | None,
    label: str,
) -> None:
    assert lines and lines[0].strip() == "---", f"{label} must start with YAML frontmatter"
    if closing_index is None:
        pytest.fail(f"{label} missing closing YAML frontmatter delimiter")


def _frontmatter_block(text: str, label: str) -> str:
    lines, closing_index, frontmatter = _split_frontmatter(text)
    _assert_frontmatter_delimiters(lines, closing_index, label)
    return frontmatter


def _extract_section_body(text: str, heading_pattern: str) -> str | None:
    heading_match = re.search(
        rf"(?im)^(?P<marks>##+)\s+{heading_pattern}\s*$",
        text,
    )
    if not heading_match:
        return None
    heading_level = len(heading_match.group("marks"))
    body_start = heading_match.end()
    next_heading = re.search(
        rf"(?m)^#{{2,{heading_level}}}\s+",
        text[body_start:],
    )
    if next_heading:
        return text[body_start : body_start + next_heading.start()]
    return text[body_start:]


def _assert_heading_present(body: str | None, heading_pattern: str, label: str) -> None:
    assert body is not None, f"{label} missing section matching: {heading_pattern}"


def _markdown_section_body(text: str, heading_pattern: str, label: str) -> str:
    body = _extract_section_body(text, heading_pattern)
    _assert_heading_present(body, heading_pattern, label)
    return body or ""


def _external_surface_body(text: str) -> str:
    external_heading = re.search(
        r"(?im)^(?P<marks>##+)\s+.*(?:external surfaces?|ticket[- ]operator surface|"
        r"ticket task surface).*$",
        text,
    )
    if external_heading:
        heading_level = len(external_heading.group("marks"))
        body_start = external_heading.end()
        next_heading = re.search(
            rf"(?m)^#{{2,{heading_level}}}\s+",
            text[body_start:],
        )
        if next_heading:
            return text[body_start : body_start + next_heading.start()]
        return text[body_start:]
    return _markdown_section_body(text, "Procedure", "adversarial QA driver")


def _raw_task_tokens(text: str) -> set[str]:
    code_tokens = re.findall(r"`([a-z][a-z-]*)`", text.lower())
    task_value_tokens = re.findall(r"\btask=([a-z][a-z-]*)\b", text.lower())
    bare_match = re.match(r"\s*([a-z][a-z-]*)\b", text.lower())
    tokens = set(code_tokens + task_value_tokens)
    if bare_match:
        tokens.add(bare_match.group(1))
    return tokens


def _drop_generic_task_tokens(tokens: set[str]) -> set[str]:
    return tokens - {
        "abstract",
        "backend",
        "driver",
        "jira-operator",
        "labels",
        "linear-operator",
        "task",
        "ticket",
        "ticket_operator",
    }


def _task_tokens(text: str) -> set[str]:
    return _drop_generic_task_tokens(_raw_task_tokens(text))


def _parse_external_surface_rows(text: str) -> list[tuple[str, str]]:
    section = _external_surface_body(text)
    rows: list[tuple[str, str]] = []
    lines = section.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        lowered_cells = [cell.lower() for cell in cells]
        abstract_columns = [
            column_index
            for column_index, cell in enumerate(lowered_cells)
            if "abstract" in cell and "task" in cell
        ]
        if not abstract_columns:
            continue
        abstract_column = abstract_columns[0]
        for row in lines[index + 1 :]:
            if not row.lstrip().startswith("|"):
                break
            row_cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if len(row_cells) <= abstract_column:
                continue
            rows.append(("table", row_cells[abstract_column]))

    for line in lines:
        bullet = re.match(r"\s*(?:[-*]|\d+\.)\s+(?P<body>.+)", line)
        if not bullet:
            continue
        body = bullet.group("body")
        abstract_side = re.split(
            r"\s+(?:->|maps?\s+to|resolves?\s+to|backend|linear-operator|jira-operator)\b",
            body,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        rows.append(("bullet", abstract_side))

    return rows


def _filter_to_task_rows(rows: list[tuple[str, str]]) -> list[tuple[str, str]]:
    task_rows: list[tuple[str, str]] = []
    for kind, value in rows:
        lowered_value = value.lower()
        if set([cell.strip() for cell in lowered_value.split("|")]) <= {
            "",
            "---",
            ":---",
            "---:",
            ":---:",
        }:
            continue
        if kind == "bullet" and ("must not" in lowered_value or "no third" in lowered_value):
            continue
        if kind == "bullet" and (
            "${ticket_operator}" not in lowered_value
            and "abstract" not in lowered_value
            and "task" not in lowered_value
        ):
            continue
        task_rows.append((kind, value))
    return task_rows


def _task_rows_to_tokens(rows: list[tuple[str, str]]) -> set[str]:
    tasks: set[str] = set()
    for _, value in rows:
        tasks.update(_task_tokens(value))
    return tasks


def _abstract_ticket_tasks_from_external_surface(text: str) -> set[str]:
    return _task_rows_to_tokens(_filter_to_task_rows(_parse_external_surface_rows(text)))


def _parse_declared_roles_section(text: str) -> str | None:
    section_match = re.search(
        r"(?ims)^##\s+Declared roles\s*$"
        r"(?P<body>.*?)(?=^##\s+|\Z)",
        text,
    )
    if section_match:
        return section_match.group("body")
    marker_match = re.search(r"(?im)^#\s*Declared roles:\s*(?P<roles>.+)$", text)
    if marker_match:
        return marker_match.group("roles")
    return None


def _parse_declared_role_words(section: str | None) -> set[str]:
    return set(re.findall(r"\b[a-z][a-z-]*\b", (section or "").lower()))


def _parse_listed_role_tokens(section: str | None) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"`([a-z][a-z-]*)`", (section or "").lower())
    }


def _drop_non_a1_tokens(tokens: set[str]) -> set[str]:
    return {token for token in tokens if token in A1_VOCABULARY}


def _out_of_a1_vocabulary(tokens: set[str]) -> set[str]:
    return tokens - A1_VOCABULARY


def _assert_a1_vocabulary(
    section: str | None,
    discovered: set[str],
    out_of_vocabulary: set[str],
    label: str,
) -> None:
    assert section is not None, f"{label} missing declared roles section or marker"
    assert discovered, f"{label} declared roles section did not name A1 role tokens"
    assert not out_of_vocabulary, (
        f"{label} declared roles section contains non-A1 tokens: "
        f"{sorted(out_of_vocabulary)}"
    )


def _declared_role_tokens(text: str, label: str) -> set[str]:
    section = _parse_declared_roles_section(text)
    discovered = _drop_non_a1_tokens(_parse_declared_role_words(section))
    out_of_vocabulary = _out_of_a1_vocabulary(_parse_listed_role_tokens(section))
    _assert_a1_vocabulary(section, discovered, out_of_vocabulary, label)
    return discovered


def _missing_exclusion_patterns(text: str, patterns: dict[str, str]) -> list[str]:
    return [
        branch_scope
        for branch_scope, pattern in patterns.items()
        if not re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    ]


def _present_forbidden_phrases(text: str, forbidden_phrases: list[str]) -> list[str]:
    return [phrase for phrase in forbidden_phrases if phrase in text]


def _parse_operator_frontmatter_keys(frontmatter: str) -> list[str]:
    lines = [
        line.strip()
        for line in frontmatter.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return [line.split(":", 1)[0].strip() for line in lines if ":" in line]


def _forbidden_abstract_tasks_present(abstract_tasks: set[str]) -> set[str]:
    return abstract_tasks & {"comment", "apply-labels"}


def _parse_eval_runtime_frontmatter(text: str) -> dict[str, object]:
    lines = text.splitlines()
    closing_indices = [
        index
        for index, line in enumerate(lines[1:60], start=1)
        if line.strip() == "---"
    ]
    frontmatter = "\n".join(lines[1 : closing_indices[0]]) if closing_indices else ""
    return {
        "lines": lines,
        "closing_indices": closing_indices,
        "frontmatter": frontmatter,
    }


def _run_workflow_index_check() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            "-m",
            "tools.workflow_index",
            "check",
            "--repo-root",
            str(REPO_ROOT),
            "--workflows-dir",
            "workflows",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_workflow_file_exists():
    assert WORKFLOW_PATH.exists(), f"{WORKFLOW_PATH} must exist"
    assert WORKFLOW_PATH.stat().st_size > 0, "workflow file must be non-empty"
    text = _read(WORKFLOW_PATH)
    _frontmatter_block(text, "adversarial QA workflow")
    _assert_contains_all(
        text,
        [
            "workflow:",
            "id: adversarial-qa-stage",
            "workflow_dispatch_contract:",
            "orchestrator:",
            "inputs:",
            "expectations:",
            "outputs:",
            "non_goals:",
            "agents/adversarial-qa-driver",
        ],
        "adversarial QA workflow frontmatter and dispatch contract",
    )


def test_workflow_declares_five_phases():
    text = _read(_path_must_exist(WORKFLOW_PATH))
    for heading in (
        "Purpose",
        "Workflow Dispatch Surface",
        "Required Inputs",
        "Output Paths",
        "Phase Map",
        "Stop Conditions",
        "Anti-Scope",
        "Handoff Boundary",
        "Cross-References",
    ):
        _assert_heading(text, heading, "adversarial QA workflow")

    for phase_heading in (
        "setup",
        "normal-usage regression sweep",
        "adversarial probing",
        "bug report filing",
        "summary report",
    ):
        _assert_heading(text, phase_heading, "adversarial QA workflow phase map")


def test_workflow_names_stage_scope_and_split():
    text = _read(_path_must_exist(WORKFLOW_PATH))
    _assert_contains_all(
        text,
        [
            "stage-only",
            "production",
            "prototype",
            "normal-usage regression sweep",
            "adversarial probing",
        ],
        "workflow stage/prod/prototype scope split",
    )
    assert text.lower().find("normal-usage regression sweep") != text.lower().find(
        "adversarial probing"
    )
    exclusion_patterns = {
        "production": (
            r"((exclude|excludes|not|outside).{0,40}\bproduction\b|"
            r"\bproduction\b.{0,40}(excluded|outside.{0,20}scope))"
        ),
        "prototype": (
            r"((exclude|excludes|not|outside).{0,40}\bprototype\b|"
            r"\bprototype\b.{0,40}(excluded|outside.{0,20}scope))"
        ),
    }
    missing_exclusions = _missing_exclusion_patterns(text, exclusion_patterns)
    assert not missing_exclusions, (
        "workflow must explicitly exclude production and prototype scopes; "
        f"missing {missing_exclusions}"
    )


def test_workflow_bug_report_contents():
    text = _lower_text(_read(_path_must_exist(WORKFLOW_PATH)))
    _assert_contains_all(
        text,
        [
            "expected behavior",
            "actual behavior",
            "deterministic steps to reproduce",
            "utc timestamp",
            "local logs when available",
            "environment",
            "labels",
            "severity/priority",
            "rca handoff",
        ],
        "workflow canonical bug-report contents",
    )
    assert "screenshot" in text or "video" in text, (
        "workflow bug-report contents must name screenshot or video evidence"
    )
    _assert_contains_all(
        text,
        [
            "~/ai/conventions/test-reports.md",
            "~/ai/conventions/risk-profile.md",
        ],
        "workflow cross-reference conventions",
    )


def test_workflow_forbidden_framing_absent():
    text = _lower_text(_read(_path_must_exist(WORKFLOW_PATH)))
    forbidden_phrases = [
        "machine enforcement",
        "tracked in a separate ticket",
    ]
    present = _present_forbidden_phrases(text, forbidden_phrases)
    assert not present, f"workflow contains forbidden framing: {present}"


def test_operator_file_exists_and_frontmatter_conforms():
    assert OPERATOR_PATH.exists(), f"{OPERATOR_PATH} must exist"
    assert OPERATOR_PATH.stat().st_size > 0, "operator file must be non-empty"
    text = _read(OPERATOR_PATH)
    frontmatter = _frontmatter_block(text, "adversarial QA driver")
    keys = _parse_operator_frontmatter_keys(frontmatter)
    assert keys == ["description", "model", "output_format"], (
        "operator frontmatter must contain exactly description, model, output_format"
    )
    _assert_contains_all(
        frontmatter,
        [
            "description:",
            "model: gpt-high",
            "output_format: ''",
        ],
        "operator frontmatter",
    )
    for heading in (
        "Role",
        "Use When",
        "Do Not Use When",
        "Inputs",
        "Procedure",
        "Evidence And Bug Report Contract",
        "Stop Conditions",
        "Escalation",
        "Outputs",
    ):
        _assert_heading(text, heading, "adversarial QA driver")


def test_operator_names_input_contract():
    text = _read(_path_must_exist(OPERATOR_PATH))
    lowered = text.lower()
    inputs_body = _markdown_section_body(text, "Inputs", "adversarial QA driver")
    lowered_inputs = inputs_body.lower()
    _assert_contains_all(
        text,
        [
            "stage_url",
            "health_check_url",
            "use_case_dossier_path",
            "run_id",
            "ticket_system",
            "${ticket_operator}",
            "feature_flags",
        ],
        "operator required input identifiers",
    )
    assert "planning_dir" in text or "evidence_dir_root" in text, (
        "operator must name planning_dir or evidence_dir_root"
    )
    assert "linear_team_key" in text or "linear_project_id" in text or "jira_" in text, (
        "operator must name ticket backend routing inputs"
    )
    assert "browser" in lowered or "browser_identity" in lowered, (
        "operator must name browser identity"
    )
    credential_or_role_tokens = (
        "credentials_path",
        "credentials",
        "role",
        "roles",
        "role_bindings",
    )
    assert any(
        re.search(rf"\b{re.escape(token)}\b", lowered_inputs)
        for token in credential_or_role_tokens
    ), "operator inputs must name credentials or roles"
    assert "local_log_paths" in text or "log_capture_path" in text, (
        "operator must name local log input paths"
    )


def test_operator_names_core_subprocedures():
    text = _read(_path_must_exist(OPERATOR_PATH))
    lowered = text.lower()
    _assert_contains_all(
        text,
        [
            "evidence-capture sub-procedure",
            "bug filing sub-procedure",
            "summary-write sub-procedure",
            "ticket_system",
            "${ticket_operator}",
            "create",
            "comment-write",
            "linear-operator.md task=create",
            "linear-operator.md task=upsert-comment",
            "jira-operator.md task=create",
            "jira-operator.md task=comment",
        ],
        "operator core procedure and backend-resolution table",
    )
    assert "exactly two" in lowered and "abstract" in lowered, (
        "operator must state that the driver invokes exactly two abstract ticket tasks"
    )
    abstract_tasks = _abstract_ticket_tasks_from_external_surface(text)
    assert abstract_tasks == {"create", "comment-write"}, (
        "operator external surface must expose exactly create and comment-write "
        f"abstract ticket tasks, found {sorted(abstract_tasks)}"
    )
    forbidden_abstract_tasks = _forbidden_abstract_tasks_present(abstract_tasks)
    assert not forbidden_abstract_tasks, (
        "operator must not introduce standalone comment or apply-labels as "
        f"abstract ticket tasks: {sorted(forbidden_abstract_tasks)}"
    )


def test_operator_consolidates_evidence_policy():
    text = _lower_text(_read(_path_must_exist(OPERATOR_PATH)))
    _assert_contains_all(
        text,
        [
            "~/ai/conventions/test-reports.md",
            "per-finding pdf",
            "raw screenshots",
            "videos",
            "logs",
            "run bundle",
            "utc timestamp",
            "stage environment",
            "browser/agent identity",
            "feature flags",
            "deterministic repro steps",
            "component labels",
            "severity/priority",
            "local logs when available",
            "run-bundle links",
            "~/ai/conventions/risk-profile.md",
            "insufficient for stage qa",
        ],
        "operator consolidated evidence and bug-report policy",
    )


def test_operator_declares_readiness_contract():
    text = _lower_text(_read(_path_must_exist(OPERATOR_PATH)))
    _assert_contains_all(
        text,
        [
            "health_check_url",
            "http",
            "status",
            "2xx",
            "4xx",
            "5xx",
            "no body parsing",
            "connection-refused",
            "timeout",
        ],
        "operator readiness contract",
    )
    assert "body" in text and "parsing" in text, (
        "readiness contract must reject private response-body coupling"
    )


def test_eval_runtime_workflow_frontmatter_parses():
    parsed = _parse_eval_runtime_frontmatter(_read(_path_must_exist(EVAL_RUNTIME_PATH)))
    lines = parsed["lines"]
    assert lines and lines[0].strip() == "---", "eval-runtime must start with frontmatter"
    closing_indices = parsed["closing_indices"]
    assert closing_indices, "eval-runtime closing frontmatter delimiter must appear within first 60 lines"
    frontmatter = parsed["frontmatter"]
    assert re.search(r"(?m)^\s*workflow:\s*$", frontmatter), (
        "eval-runtime frontmatter must contain workflow mapping"
    )
    assert re.search(r"(?m)^\s+id:\s*\S+", frontmatter), (
        "eval-runtime frontmatter must contain workflow.id"
    )

    completed = _run_workflow_index_check()
    assert completed.returncode == 0, (
        "workflow index check failed\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


def test_new_files_declare_a1_roles():
    workflow_roles = _declared_role_tokens(_read(_path_must_exist(WORKFLOW_PATH)), "workflow")
    operator_roles = _declared_role_tokens(_read(_path_must_exist(OPERATOR_PATH)), "operator")
    test_roles = _declared_role_tokens(_read(_path_must_exist(TEST_PATH)), "structural pytest")

    assert {"orchestration", "validator", "formatter"} <= workflow_roles
    assert workflow_roles == {"orchestration", "validator", "formatter"}

    assert {"orchestration", "validator", "accessor", "formatter"} <= operator_roles
    assert operator_roles == {"orchestration", "validator", "accessor", "formatter"}

    assert {
        "orchestration",
        "filter",
        "validator",
        "predicate",
        "mapper",
        "accessor",
        "parser",
    } <= test_roles
    assert test_roles == {
        "orchestration",
        "filter",
        "validator",
        "predicate",
        "mapper",
        "accessor",
        "parser",
    }
