"""Structural contract tests for the ACR-149 adversarial QA stage workflow."""

import pathlib
import re
import subprocess

import pytest


# ## Declared roles
# Declared roles: parser, validator, predicate

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


def _read(path: pathlib.Path) -> str:
    assert path.exists(), f"missing required file: {path}"
    return path.read_text(encoding="utf-8")


def _lower_text(path: pathlib.Path) -> str:
    return _read(path).lower()


def _assert_contains_all(text: str, required: list[str], label: str) -> None:
    missing = [item for item in required if item.lower() not in text.lower()]
    assert not missing, f"{label} missing required text: {missing}"


def _assert_heading(text: str, heading: str, label: str) -> None:
    pattern = rf"(?im)^##\s+{re.escape(heading)}\s*$"
    assert re.search(pattern, text), f"{label} missing heading: ## {heading}"


def _frontmatter_block(text: str, label: str) -> str:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", f"{label} must start with YAML frontmatter"
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index])
    pytest.fail(f"{label} missing closing YAML frontmatter delimiter")


def _markdown_section_body(text: str, heading_pattern: str, label: str) -> str:
    heading_match = re.search(
        rf"(?im)^(?P<marks>##+)\s+{heading_pattern}\s*$",
        text,
    )
    assert heading_match, f"{label} missing section matching: {heading_pattern}"
    heading_level = len(heading_match.group("marks"))
    body_start = heading_match.end()
    next_heading = re.search(
        rf"(?m)^#{{2,{heading_level}}}\s+",
        text[body_start:],
    )
    if next_heading:
        return text[body_start : body_start + next_heading.start()]
    return text[body_start:]


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


def _task_tokens(text: str) -> set[str]:
    code_tokens = re.findall(r"`([a-z][a-z-]*)`", text.lower())
    task_value_tokens = re.findall(r"\btask=([a-z][a-z-]*)\b", text.lower())
    bare_match = re.match(r"\s*([a-z][a-z-]*)\b", text.lower())
    tokens = set(code_tokens + task_value_tokens)
    if bare_match:
        tokens.add(bare_match.group(1))
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


def _abstract_ticket_tasks_from_external_surface(text: str) -> set[str]:
    section = _external_surface_body(text)
    tasks: set[str] = set()
    lines = section.splitlines()

    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        lowered_cells = [cell.lower() for cell in cells]
        if set(lowered_cells) <= {"", "---", ":---", "---:", ":---:"}:
            continue
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
            lowered_row = [cell.lower() for cell in row_cells]
            if set(lowered_row) <= {"", "---", ":---", "---:", ":---:"}:
                continue
            tasks.update(_task_tokens(row_cells[abstract_column]))

    for line in lines:
        bullet = re.match(r"\s*(?:[-*]|\d+\.)\s+(?P<body>.+)", line)
        if not bullet:
            continue
        body = bullet.group("body")
        lowered_body = body.lower()
        if "must not" in lowered_body or "no third" in lowered_body:
            continue
        if (
            "${ticket_operator}" not in lowered_body
            and "abstract" not in lowered_body
            and "task" not in lowered_body
        ):
            continue
        abstract_side = re.split(
            r"\s+(?:->|maps?\s+to|resolves?\s+to|backend|linear-operator|jira-operator)\b",
            body,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        tasks.update(_task_tokens(abstract_side))

    return tasks


def _declared_role_tokens(text: str, label: str) -> set[str]:
    section_match = re.search(
        r"(?ims)^##\s+Declared roles\s*$"
        r"(?P<body>.*?)(?=^##\s+|\Z)",
        text,
    )
    if section_match:
        section = section_match.group("body")
    else:
        marker_match = re.search(r"(?im)^#\s*Declared roles:\s*(?P<roles>.+)$", text)
        assert marker_match, f"{label} missing declared roles section or marker"
        section = marker_match.group("roles")

    discovered = {
        token
        for token in re.findall(r"\b[a-z][a-z-]*\b", section.lower())
        if token in A1_VOCABULARY
    }
    listed_tokens = {
        token.lower()
        for token in re.findall(r"`([a-z][a-z-]*)`", section.lower())
    }
    out_of_vocabulary = listed_tokens - A1_VOCABULARY
    assert discovered, f"{label} declared roles section did not name A1 role tokens"
    assert not out_of_vocabulary, (
        f"{label} declared roles section contains non-A1 tokens: "
        f"{sorted(out_of_vocabulary)}"
    )
    return discovered


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
    text = _read(WORKFLOW_PATH)
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
    text = _read(WORKFLOW_PATH)
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
    missing_exclusions = [
        branch_scope
        for branch_scope, pattern in exclusion_patterns.items()
        if not re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    ]
    assert not missing_exclusions, (
        "workflow must explicitly exclude production and prototype scopes; "
        f"missing {missing_exclusions}"
    )


def test_workflow_bug_report_contents():
    text = _lower_text(WORKFLOW_PATH)
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
    text = _lower_text(WORKFLOW_PATH)
    forbidden_phrases = [
        "machine enforcement",
        "tracked in a separate ticket",
    ]
    present = [phrase for phrase in forbidden_phrases if phrase in text]
    assert not present, f"workflow contains forbidden framing: {present}"


def test_operator_file_exists_and_frontmatter_conforms():
    assert OPERATOR_PATH.exists(), f"{OPERATOR_PATH} must exist"
    assert OPERATOR_PATH.stat().st_size > 0, "operator file must be non-empty"
    text = _read(OPERATOR_PATH)
    frontmatter = _frontmatter_block(text, "adversarial QA driver")
    lines = [
        line.strip()
        for line in frontmatter.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    keys = [line.split(":", 1)[0].strip() for line in lines if ":" in line]
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
    text = _read(OPERATOR_PATH)
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
    text = _read(OPERATOR_PATH)
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
    forbidden_abstract_tasks = abstract_tasks & {"comment", "apply-labels"}
    assert not forbidden_abstract_tasks, (
        "operator must not introduce standalone comment or apply-labels as "
        f"abstract ticket tasks: {sorted(forbidden_abstract_tasks)}"
    )


def test_operator_consolidates_evidence_policy():
    text = _lower_text(OPERATOR_PATH)
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
    text = _lower_text(OPERATOR_PATH)
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
    text = _read(EVAL_RUNTIME_PATH)
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "eval-runtime must start with frontmatter"
    closing_indices = [index for index, line in enumerate(lines[1:60], start=1) if line.strip() == "---"]
    assert closing_indices, "eval-runtime closing frontmatter delimiter must appear within first 60 lines"
    frontmatter = "\n".join(lines[1 : closing_indices[0]])
    assert re.search(r"(?m)^\s*workflow:\s*$", frontmatter), (
        "eval-runtime frontmatter must contain workflow mapping"
    )
    assert re.search(r"(?m)^\s+id:\s*\S+", frontmatter), (
        "eval-runtime frontmatter must contain workflow.id"
    )

    completed = subprocess.run(
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
    assert completed.returncode == 0, (
        "workflow index check failed\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


def test_new_files_declare_a1_roles():
    workflow_roles = _declared_role_tokens(_read(WORKFLOW_PATH), "workflow")
    operator_roles = _declared_role_tokens(_read(OPERATOR_PATH), "operator")
    test_roles = _declared_role_tokens(_read(TEST_PATH), "structural pytest")

    assert {"orchestration", "validator", "formatter"} <= workflow_roles
    assert workflow_roles == {"orchestration", "validator", "formatter"}

    assert {"orchestration", "validator", "accessor", "formatter"} <= operator_roles
    assert operator_roles == {"orchestration", "validator", "accessor", "formatter"}

    assert {"parser", "validator", "predicate"} <= test_roles
    assert test_roles == {"parser", "validator", "predicate"}
