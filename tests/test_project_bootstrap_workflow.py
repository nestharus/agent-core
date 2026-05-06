import re
from pathlib import Path

from tools.workflow_index.generator import (
    parse_frontmatter,
    validate_dispatch_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / "workflows" / "project-bootstrap.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
README_MD = REPO_ROOT / "README.md"

PROCEDURE_SUBSECTIONS = (
    "Open Path",
    "Emission",
    "Closed Path Dispatch Contract",
    "Re-Bootstrap Trigger",
)
STOP_CONDITIONS = (
    "WRAPPER_EMITTED",
    "WRAPPER_REFRESHED",
    "NO_WRAPPER_NEEDED",
    "REBOOTSTRAP_NOT_NEEDED",
    "NEEDS_INPUT",
    "BLOCKED",
)
PROCEDURE_DECISIONS = STOP_CONDITIONS + (
    "REBOOTSTRAP_OPENED",
    "OPEN_PATH_READY_FOR_EMISSION",
)


def _workflow_text():
    assert WORKFLOW_PATH.exists(), f"missing workflow file: {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _agents_text():
    assert AGENTS_MD.exists(), f"missing agents file: {AGENTS_MD}"
    return AGENTS_MD.read_text(encoding="utf-8")


def _readme_text():
    assert README_MD.exists(), f"missing readme file: {README_MD}"
    return README_MD.read_text(encoding="utf-8")


def _markdown_body(text):
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :])
    return text


def _heading_body(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    following = text[match.end() :]
    level = len(heading) - len(heading.lstrip("#"))
    next_heading = re.search(rf"(?m)^#{{1,{level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _procedure_subsection_body(text, name):
    procedure = _heading_body(_markdown_body(text), "## Procedure")
    return _heading_body(procedure, f"### {name}")


def _contains_all(text, substrings):
    lowered = text.lower()
    missing = [item for item in substrings if item.lower() not in lowered]
    assert missing == [], f"missing expected substrings: {missing}"


def _operator_names():
    names = {path.stem for path in (REPO_ROOT / "agents").glob("*.md")}
    # Include shared operators documented in AGENTS.md even when no local wrapper exists.
    names.update(
        {
            "agentsmd-curator",
            "agentsmd-maintenance-orchestrator",
            "linear-operator",
            "jira-operator",
        }
    )
    return names


def _has_operational_marker(body):
    if any(name in body for name in _operator_names()):
        return True
    if any(decision in body for decision in PROCEDURE_DECISIONS):
        return True
    if "python3 -m" in body:
        return True
    return re.search(
        r"\b(?:Read|read|Run|run)\s+`?(?:~?/|/|\.?/|[A-Za-z0-9_.-]+/|python3 -m)",
        body,
    ) is not None


def test_project_bootstrap_workflow_cites_bootstrap_pattern_convention():
    text = _workflow_text()

    assert "bootstrap-pattern.md" in text, (
        "project bootstrap workflow must cite bootstrap-pattern.md"
    )


def test_project_bootstrap_workflow_has_required_procedure_subsections():
    body = _markdown_body(_workflow_text())

    assert re.search(r"(?m)^## Procedure$", body), (
        "missing Procedure section"
    )
    for subsection in PROCEDURE_SUBSECTIONS:
        section_body = _procedure_subsection_body(body, subsection)
        assert section_body.strip(), (
            f"Procedure subsection '{subsection}' must have a non-empty body"
        )


def test_project_bootstrap_workflow_stop_conditions_are_named():
    stop_conditions = _heading_body(_markdown_body(_workflow_text()), "## Stop Conditions")

    assert stop_conditions.strip(), "Stop Conditions section must be non-empty"
    for condition in STOP_CONDITIONS:
        assert condition in stop_conditions, (
            f"Stop Conditions must name {condition}"
        )


def test_project_bootstrap_workflow_is_listed_in_agents_workflow_topologies():
    topologies = _heading_body(_agents_text(), "## Workflow Topologies")

    assert "workflows/project-bootstrap.md" in topologies, (
        "AGENTS.md Workflow Topologies must link to workflows/project-bootstrap.md"
    )


def test_project_bootstrap_workflow_is_listed_in_readme_workflow_library():
    text = _readme_text()

    assert "workflows/project-bootstrap.md" in text, (
        "README.md workflow library must link to workflows/project-bootstrap.md"
    )


def test_project_bootstrap_workflow_names_layout_destination_contract():
    text = _workflow_text()
    emission = _procedure_subsection_body(text, "Emission")

    assert "project-layout.md" in emission, (
        "Emission must cite project-layout.md"
    )
    _contains_all(
        emission,
        (
            "<project>/trunk/agents/",
            "<project>/agents/",
        ),
    )


def test_project_bootstrap_workflow_procedure_subsections_orchestrate():
    text = _workflow_text()

    for subsection in PROCEDURE_SUBSECTIONS:
        body = _procedure_subsection_body(text, subsection)
        assert _has_operational_marker(body), (
            f"Procedure subsection '{subsection}' is rule-list-shaped "
            "— must orchestrate, not describe."
        )


def test_project_bootstrap_workflow_frontmatter_dispatch_contract_content():
    text = _workflow_text()
    parsed = parse_frontmatter(text, str(WORKFLOW_PATH))
    validate_dispatch_contract(
        parsed.get("workflow_dispatch_contract"),
        str(WORKFLOW_PATH),
    )

    assert parsed.get("workflow", {}).get("id") == "project-bootstrap", (
        "workflow.id must be project-bootstrap"
    )
    contract = parsed["workflow_dispatch_contract"]
    assert contract["orchestrator"] == "Work Manager or root coordinator", (
        "project-bootstrap dispatch owner must stay literal"
    )
    for key in ("inputs", "expectations", "outputs", "non_goals"):
        assert isinstance(contract[key], list), f"{key} must be a list"
        assert contract[key], f"{key} must be non-empty"

    non_goals = "\n".join(contract["non_goals"])
    for required in (
        "does not redefine bootstrap-pattern",
        "does not implement category-specific",
        "does not migrate",
    ):
        assert required in non_goals, (
            f"workflow non_goals must contain {required!r}"
        )


def test_project_bootstrap_workflow_emission_names_wrapper_shape_contract():
    emission = _procedure_subsection_body(_workflow_text(), "Emission")

    _contains_all(
        emission,
        (
            "frontmatter",
            "H1",
            "Base procedure: ~/ai/agents/<name>.md",
            "local defaults",
        ),
    )
    assert re.search(r"\bre-?inline", emission, re.IGNORECASE), (
        "Emission must prohibit re-inlining the shared base procedure"
    )


def test_project_bootstrap_workflow_emission_names_agents_wrapper_precedence():
    emission = _procedure_subsection_body(_workflow_text(), "Emission")

    _contains_all(
        emission,
        (
            "project AGENTS.md",
            "policy knobs",
            "wrapper",
            "category-specific defaults",
            "precedence",
        ),
    )
    assert re.search(r"\bduplicate|\boverride", emission, re.IGNORECASE), (
        "Emission must name duplicate or override control for global policy facts"
    )


def test_project_bootstrap_workflow_emission_names_wrapper_validation_step():
    emission = _procedure_subsection_body(_workflow_text(), "Emission")

    _contains_all(
        emission,
        (
            "validate",
            "operator-file-format.md",
            "frontmatter",
            "H1",
            "Base procedure:",
            "destination",
            "agentsmd-curator",
        ),
    )


def test_project_bootstrap_workflow_names_skipped_emission_reporting():
    text = _workflow_text()
    emission = _procedure_subsection_body(text, "Emission")
    rebootstrap = _procedure_subsection_body(text, "Re-Bootstrap Trigger")
    stop_conditions = _heading_body(_markdown_body(text), "## Stop Conditions")
    combined = "\n".join((emission, rebootstrap, stop_conditions))

    _contains_all(
        combined,
        (
            "NO_WRAPPER_NEEDED",
            "REBOOTSTRAP_NOT_NEEDED",
            "NEEDS_INPUT",
            "BLOCKED",
        ),
    )
    assert re.search(r"\brun[- ]report\b|\breport", combined, re.IGNORECASE), (
        "Skipped emission outcomes must be reported with run-report rationale"
    )
