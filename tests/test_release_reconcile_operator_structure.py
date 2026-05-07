"""Structural tests for the NES-247 release-reconcile-operator."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR = REPO_ROOT / "agents" / "release-reconcile-operator.md"

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_SECTIONS = (
    "## Role",
    "## Use When",
    "## Do Not Use When",
    "## Non-Negotiables",
    "## Required Inputs",
    "## Optional Inputs",
    "## Procedure",
    "## Outputs",
    "## Stop Conditions",
    "## Cross-references",
)
REQUIRED_INPUT_NAMES = (
    "repo_root",
    "worktree_path",
    "scratch_dir",
    "release_id",
    "develop_branch_name",
    "main_branch_name",
    "release_branch_name",
    "concurrent_release_branches",
    "named_invariants",
    "reconciliation_strategy",
    "manifest_path",
    "release_manifest_path",
    "reconcile_obligations",
)
REQUIRED_BLOCKED_TOKENS = (
    "BLOCKED:missing-required-input",
    "BLOCKED:invariant-violation",
    "BLOCKED:reconcile-open",
    "BLOCKED:manifest-update-missing",
    "BLOCKED:unsafe-reconcile-target",
    "BLOCKED:unsupported-reconciliation-strategy",
    "NEEDS_INPUT:",
)
REQUIRED_CROSS_REFERENCES = (
    "~/ai/workflows/release-management.md",
    "~/ai/agents/release-orchestrator.md",
    "~/ai/agents/operator-file-format.md",
    "~/ai/workflows/agents-cli.md",
    "~/ai/conventions/agent-questions-and-session-graph.md",
    "/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md",
    "/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/problem.md",
    "/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy-decisions-resolved.md",
)
RFQ_CROSS_REFERENCES = REQUIRED_CROSS_REFERENCES[-3:]


def _operator_text():
    assert OPERATOR.exists(), "missing agents/release-reconcile-operator.md"
    assert OPERATOR.stat().st_size > 0, "operator file must be non-empty"
    return OPERATOR.read_text(encoding="utf-8")


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
    try:
        import yaml
    except ImportError:
        yaml = None

    if yaml is not None:
        frontmatter = yaml.safe_load(frontmatter_text)
        assert isinstance(frontmatter, dict), "frontmatter must parse as a mapping"
        return frontmatter

    frontmatter = {}
    for line in frontmatter_text.splitlines():
        if not line.strip():
            continue
        assert not line.startswith((" ", "\t")), (
            f"frontmatter key must be top-level: {line}"
        )
        key, separator, value = line.partition(":")
        assert separator, f"invalid frontmatter line: {line}"
        frontmatter[key.strip()] = value.strip().strip("'\"")
    return frontmatter


def _operator_body():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    return body


def _section_after_h2(text, heading):
    heading_text = heading.removeprefix("##").strip()
    pattern = rf"(?m)^##\s+{re.escape(heading_text)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading_text}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _assert_regex(text, pattern, message):
    assert re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ), message


def test_operator_file_exists():
    assert OPERATOR.exists()
    assert OPERATOR.stat().st_size > 0


def test_frontmatter_keys():
    text = _operator_text()
    frontmatter = _parse_frontmatter(text)
    frontmatter_lines = _frontmatter_and_body(text)[0].splitlines()
    description = frontmatter["description"].lower()

    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert list(frontmatter) == ["description", "model", "output_format"]
    assert frontmatter_lines == [
        f"description: '{frontmatter['description']}'",
        "model: gpt-high",
        "output_format: ''",
    ]
    assert "reconcile" in description
    assert any(token in description for token in ("hotfix", "carry-back", "develop"))


def test_frontmatter_model_is_gpt_high():
    frontmatter = _parse_frontmatter(_operator_text())

    assert frontmatter["model"] == "gpt-high"


def test_frontmatter_output_format_empty_string():
    frontmatter = _parse_frontmatter(_operator_text())

    assert frontmatter["output_format"] == ""


def test_required_h2_sections_present_in_order():
    body = _operator_body()
    h1s = re.findall(r"(?m)^#\s+(.+?)\s*$", body)
    h2s = tuple(re.findall(r"(?m)^##\s+(.+?)\s*$", body))
    required_h2_names = tuple(
        heading.removeprefix("##").strip() for heading in REQUIRED_H2_SECTIONS
    )

    assert h1s, "operator body must contain an H1"
    assert "release-reconcile-operator" in h1s[0] or "release-reconcile-operator" in body
    assert h2s == required_h2_names


def test_required_input_names_present():
    inputs = _section_after_h2(_operator_body(), "## Required Inputs")

    for input_name in REQUIRED_INPUT_NAMES:
        assert f"`{input_name}`" in inputs, (
            f"Required Inputs must declare `{input_name}`"
        )


def test_named_invariants_gate_declared():
    inputs = _section_after_h2(_operator_body(), "## Required Inputs")

    _assert_regex(
        inputs,
        r"`?named_invariants`?[\s\S]{0,320}"
        r"(?:\bevaluat(?:e|ed|ion)\b[\s\S]{0,180}"
        r"(?:fail[- ]closed|gate|BLOCKED:invariant-violation)"
        r"|(?:fail[- ]closed|gate|BLOCKED:invariant-violation)"
        r"[\s\S]{0,180}\bevaluat(?:e|ed|ion)\b)"
        r"|(?:\bevaluat(?:e|ed|ion)\b[\s\S]{0,180}"
        r"(?:fail[- ]closed|gate|BLOCKED:invariant-violation)"
        r"|(?:fail[- ]closed|gate|BLOCKED:invariant-violation)"
        r"[\s\S]{0,180}\bevaluat(?:e|ed|ion)\b)"
        r"[\s\S]{0,320}`?named_invariants`?",
        "Required Inputs must make named_invariants evaluation a fail-closed gate",
    )


def test_concurrent_release_branches_bounded_multi_path():
    text = "\n".join(
        (
            _section_after_h2(_operator_body(), "## Required Inputs"),
            _section_after_h2(_operator_body(), "## Procedure"),
        )
    )
    contexts = [
        text[max(0, match.start() - 320) : match.end() + 320]
        for match in re.finditer(r"`?concurrent_release_branches`?", text)
    ]

    assert any(
        re.search(
            r"(?i)bounded[- ]multi[- ]path|N\s*>\s*1|multiple\s+release\s+lines?",
            context,
        )
        and re.search(r"`?named_invariants`?", context)
        for context in contexts
    ), (
        "concurrent_release_branches must be tied to bounded-multi-path/N>1 "
        "release-line handling gated by named_invariants"
    )


def test_manifest_paths_are_aliases():
    inputs = _section_after_h2(_operator_body(), "## Required Inputs")

    _assert_regex(
        inputs,
        r"`manifest_path`[\s\S]{0,220}`release_manifest_path`"
        r"|`release_manifest_path`[\s\S]{0,220}`manifest_path`",
        "Required Inputs must discuss manifest_path and release_manifest_path together",
    )
    _assert_regex(
        inputs,
        r"\balias(?:es)?\b",
        "Required Inputs must state manifest paths are aliases",
    )


def test_optional_input_reconcile_branch_name():
    optional_inputs = _section_after_h2(_operator_body(), "## Optional Inputs")

    assert "`reconcile_branch_name`" in optional_inputs
    assert re.search(r"(?i)\boptional\b", optional_inputs)


def test_non_negotiables_cite_rfq_and_do_not_redefine_taxonomy():
    non_negotiables = _section_after_h2(_operator_body(), "## Non-Negotiables")

    _assert_regex(
        non_negotiables,
        r"\bcit(?:e|ed|ation)\b",
        "Non-Negotiables must require RFQ citation",
    )
    assert "rfq" in non_negotiables.lower()
    assert "invariant" in non_negotiables.lower()
    for token in ("philosophy", "problem", "resolved"):
        assert token in non_negotiables.lower()
    _assert_regex(
        non_negotiables,
        r"(do not define|do not redefine|must not define a new taxonomy)",
        "Non-Negotiables must forbid redefining the inherited invariant taxonomy",
    )
    assert "taxonomy" in non_negotiables.lower()
    assert any(token in non_negotiables for token in REQUIRED_BLOCKED_TOKENS[:-1])


def test_procedure_names_invariants_and_reconcile_paths():
    procedure = _section_after_h2(_operator_body(), "## Procedure")

    for token in (
        "named_invariants",
        "concurrent_release_branches",
        "reconciliation_strategy",
        "develop_branch_name",
        "release_branch_name",
        "manifest",
    ):
        assert token in procedure, f"Procedure must mention {token}"
    assert re.search(r"(?i)carry[- ]back", procedure)
    assert re.search(r"(?i)forward[- ]propagat", procedure)


def test_outputs_recommendation_and_states():
    outputs = _section_after_h2(_operator_body(), "## Outputs")

    for token in (
        "manifest",
        "invariant",
        "reconcile",
    ):
        assert token in outputs.lower(), f"Outputs must mention {token}"
    assert re.search(r"(?i)\b(recommendation|state|closure|residual|handoff|success)\b", outputs)


def test_stop_conditions_enumerated():
    stop_conditions = _section_after_h2(_operator_body(), "## Stop Conditions")

    for token in REQUIRED_BLOCKED_TOKENS:
        assert token in stop_conditions, f"Stop Conditions must enumerate {token}"


def test_cross_references_present():
    cross_references = _section_after_h2(_operator_body(), "## Cross-references")

    for reference in REQUIRED_CROSS_REFERENCES:
        assert reference in cross_references, (
            f"Cross-references must include {reference}"
        )


def test_role_scoped_to_post_release_reconciliation():
    role = _section_after_h2(_operator_body(), "## Role")
    role_lower = role.lower()

    assert re.search(r"(?i)post[- ]release", role)
    assert "reconcile" in role_lower or "reconciliation" in role_lower
    assert "`develop_branch_name`" in role or "develop_branch_name" in role
    assert "`release_branch_name`" in role or "release_branch_name" in role

    offenders = [
        line.strip()
        for line in role.splitlines()
        if re.search(r"(?i)\b(own(?:s|ership)?|responsible for|handles)\b", line)
        and re.search(r"(?i)\b(promote|tag|hotfix|cut)\b", line)
        and not re.search(r"(?i)\b(do not|does not|must not|never|not)\b", line)
    ]
    assert offenders == [], (
        "Role must not claim ownership of cut/hotfix/promote/tag mechanics: "
        f"{offenders}"
    )


def test_do_not_use_when_excludes_sibling_concerns():
    do_not_use = _section_after_h2(_operator_body(), "## Do Not Use When")

    for category, pattern in (
        ("cut mechanics", r"\b(?:branch\s+)?cut\b"),
        ("hotfix mechanics", r"\bhotfix\b"),
        ("promote mechanics", r"\bpromote\b"),
        ("tag mechanics", r"\btag\b"),
        ("sibling-operator/orchestrator authoring", r"\b(sibling|orchestrator authoring)\b"),
        ("settings mutation / branch protection", r"\b(settings|branch protection)\b"),
        ("live release execution", r"\blive release\b"),
        ("project wrapper configuration", r"\bwrapper\b"),
    ):
        assert re.search(pattern, do_not_use, flags=re.IGNORECASE), (
            f"Do Not Use When must exclude {category}"
        )


def test_path_hygiene_no_unrelated_local_paths():
    body = _operator_body()
    h2_names = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

    assert not re.search(r"\bNES-\d+\b", body)
    assert not re.search(r"/home/nes/projects/", body)

    for h2_name in h2_names:
        section = _section_after_h2(body, f"## {h2_name}")
        if h2_name in {"Cross-references", "Non-Negotiables"}:
            for path in re.findall(r"/home/nes/work/\S+", section):
                assert path.rstrip("`.,)") in RFQ_CROSS_REFERENCES
            continue
        assert "/home/nes/work/" not in section
