"""Structural tests for the NES-246 release-promote-operator."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_PATH = REPO_ROOT / "agents" / "release-promote-operator.md"

REQUIRED_FRONTMATTER_KEYS = {"description", "model", "output_format"}
REQUIRED_H2_HEADINGS = (
    "Role",
    "Use When",
    "Do Not Use When",
    "Non-Negotiables",
    "Required Inputs",
    "Procedure",
    "Outputs",
    "Stop Conditions",
    "Cross-references",
)
REQUIRED_INPUTS = (
    "repo_root",
    "worktree_path",
    "scratch_dir",
    "release_id",
    "release_branch_name",
    "main_branch_name",
    "tag_pattern",
    "manifest_path",
    "release_manifest_path",
    "qa_evidence_path",
    "promotion_approval",
)
CROSS_REFERENCES = (
    "~/ai/workflows/release-management.md",
    "~/ai/agents/release-orchestrator.md",
    "~/ai/agents/operator-file-format.md",
    "~/ai/conventions/agent-questions-and-session-graph.md",
)
DO_NOT_USE_TERMS = (
    "cut",
    "freeze",
    "hotfix",
    "reconcile",
    "final closure",
    "orchestrator authoring",
    "wrapper config",
    "settings mutation",
    "live release execution",
)


def _operator_text():
    assert OPERATOR_PATH.exists(), "missing agents/release-promote-operator.md"
    assert OPERATOR_PATH.stat().st_size > 0, "operator file must be non-empty"
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


def _operator_body():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    return body


def _section_after_h2(text, heading):
    pattern = rf"(?m)^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text)
    assert match, f"missing section heading: ## {heading}"

    following = text[match.end() :]
    next_h1_or_h2 = re.search(r"(?m)^#{1,2}\s+", following)
    if next_h1_or_h2:
        return following[: next_h1_or_h2.start()]
    return following


def _assert_contains(text, needle, message):
    assert needle in text, message


def _assert_regex(text, pattern, message):
    assert re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    ), message


def _near_pattern(first, second, distance=220):
    return (
        rf"{first}.{{0,{distance}}}{second}"
        rf"|{second}.{{0,{distance}}}{first}"
    )


def test_operator_file_exists():
    assert OPERATOR_PATH.exists(), "missing agents/release-promote-operator.md"
    assert OPERATOR_PATH.stat().st_size > 0, "operator file must be non-empty"


def test_frontmatter_contract():
    frontmatter = _parse_frontmatter(_operator_text())
    frontmatter_lines = _frontmatter_and_body(_operator_text())[0].splitlines()
    description = frontmatter["description"].strip("'\"")

    assert list(frontmatter) == ["description", "model", "output_format"]
    assert set(frontmatter) == REQUIRED_FRONTMATTER_KEYS
    assert frontmatter["description"].startswith("'")
    assert frontmatter["description"].endswith("'")
    assert description
    _assert_regex(
        description,
        r"promot(e|ion).{0,120}(frozen )?release.{0,120}(main|tag)",
        "description must name frozen release promotion to main plus tag mechanics",
    )
    assert "orchestrator" in description.lower()
    assert frontmatter["model"] == "gpt-high"
    assert frontmatter["output_format"] == "''"
    assert frontmatter_lines == [
        f"description: {frontmatter['description']}",
        "model: gpt-high",
        "output_format: ''",
    ]


def test_required_h2_sections_in_order():
    body = _operator_body()
    h1s = re.findall(r"(?m)^#\s+(.+?)\s*$", body)
    h2s = re.findall(r"(?m)^##\s+(.+?)\s*$", body)

    assert h1s, "operator body must contain an H1"
    assert tuple(h2s) == REQUIRED_H2_HEADINGS


def test_role_section_scope():
    role = _section_after_h2(_operator_body(), "Role")

    for token in (
        "release_branch_name",
        "main_branch_name",
        "tag_pattern",
        "release-orchestrator",
    ):
        _assert_contains(role, token, f"Role must mention {token}")
    _assert_regex(
        role,
        r"promot(e|ion).{0,160}release_branch_name.{0,160}main_branch_name"
        r"|release_branch_name.{0,160}main_branch_name.{0,160}promot(e|ion)",
        "Role must scope promotion from release_branch_name to main_branch_name",
    )
    _assert_regex(
        role,
        r"tag.{0,120}mechanics.{0,120}orchestrator|orchestrator.{0,120}"
        r"tag.{0,120}mechanics",
        "Role must keep tag mechanics under orchestrator control",
    )
    _assert_regex(
        role,
        r"final version identity.{0,120}tag_pattern|tag_pattern.{0,120}"
        r"final version identity",
        "Role must validate final version identity against tag_pattern",
    )


def test_use_when_section():
    use_when = _section_after_h2(_operator_body(), "Use When")
    lower_use_when = use_when.lower()

    for token in ("promote", "tag", "freeze evidence", "qa", "hotfix"):
        assert token in lower_use_when, f"Use When must mention {token}"
    _assert_regex(
        use_when,
        r"(customer-visible|Tier-3).{0,120}(approval|promotion_approval)"
        r"|(approval|promotion_approval).{0,120}(customer-visible|Tier-3)",
        "Use When must require customer-visible promotion approval readiness",
    )
    _assert_regex(
        use_when,
        r"release-orchestrator\.md.{0,80}(99-103|99.*103|Phase 4)"
        r"|99-103.{0,80}release-orchestrator\.md",
        "Use When must cite the release-orchestrator promote precondition",
    )


def test_do_not_use_when_section():
    do_not_use = _section_after_h2(_operator_body(), "Do Not Use When")
    lower_do_not_use = do_not_use.lower()

    for term in DO_NOT_USE_TERMS:
        assert term in lower_do_not_use, f"Do Not Use When must exclude {term}"


def test_non_negotiables_section():
    non_negotiables = _section_after_h2(_operator_body(), "Non-Negotiables")

    for token in ("qa_evidence_path", "promotion_approval"):
        _assert_contains(
            non_negotiables,
            token,
            f"Non-Negotiables must require readable {token}",
        )
    _assert_regex(
        non_negotiables,
        r"readable.{0,120}qa_evidence_path|qa_evidence_path.{0,120}readable",
        "Non-Negotiables must require readable qa_evidence_path",
    )
    _assert_regex(
        non_negotiables,
        r"readable.{0,120}promotion_approval|promotion_approval.{0,120}readable",
        "Non-Negotiables must require readable promotion_approval",
    )
    _assert_regex(
        non_negotiables,
        r"(must not|does not|never).{0,160}(remote )?tag push|"
        r"(must not|does not|never).{0,160}publication|"
        r"(no|without).{0,160}(publication|remote tag push)",
        "Non-Negotiables must forbid publication or remote tag push",
    )
    _assert_regex(
        non_negotiables,
        r"procedural gaps?.{0,80}block|block.{0,80}procedural gaps?",
        "Non-Negotiables must say procedural gaps block",
    )
    _assert_regex(
        non_negotiables,
        r"NEEDS_INPUT:<absolute_artifact_path>[\s\S]{0,280}"
        r"(value|scope|trade[- ]off|access|credential|Tier-3|approval)",
        "Non-Negotiables must reserve NEEDS_INPUT for human-owned questions",
    )
    _assert_contains(
        non_negotiables,
        "${scratch_dir}/questions/q-<uuidv4>.question.json",
        "Non-Negotiables must name the question artifact path",
    )


def test_required_inputs_section():
    inputs = _section_after_h2(_operator_body(), "Required Inputs")
    lower_inputs = inputs.lower()

    for input_name in REQUIRED_INPUTS:
        assert input_name in inputs, f"Required Inputs must name {input_name}"
    _assert_regex(
        inputs,
        r"version.{0,160}final version identity|final version identity.{0,160}version",
        "Required Inputs must describe version as final version identity",
    )
    _assert_regex(
        inputs,
        r"version.{0,220}(not|is not|isn't).{0,80}(top[- ]level|routing|required input)"
        r"|(not|is not|isn't).{0,80}(top[- ]level|routing|required input)"
        r".{0,220}version",
        "Required Inputs must not make version a top-level routing input",
    )
    assert "qa_approval_record_path" in lower_inputs
    _assert_regex(
        inputs,
        r"qa_approval_record_path.{0,180}(not|is not|isn't).{0,80}"
        r"(top[- ]level|required input|routing input)"
        r"|(not|is not|isn't).{0,80}(top[- ]level|required input|routing input)"
        r".{0,180}qa_approval_record_path",
        "Required Inputs must not require qa_approval_record_path",
    )


def test_manifest_alias():
    inputs = _section_after_h2(_operator_body(), "Required Inputs")

    _assert_regex(
        inputs,
        r"release_manifest_path.{0,220}(alias|workflow-name alias|same).{0,220}"
        r"manifest_path|manifest_path.{0,220}(alias|workflow-name alias|same)"
        r".{0,220}release_manifest_path",
        "Required Inputs must bind release_manifest_path to manifest_path",
    )
    _assert_regex(
        inputs,
        r"(not|is not|isn't).{0,80}(a )?second manifest|"
        r"(same|one).{0,80}(release )?(ledger|manifest)",
        "Required Inputs must say the alias is not a second manifest",
    )


def test_procedure_section():
    procedure = _section_after_h2(_operator_body(), "Procedure")

    for token in (
        "validate inputs",
        "clean",
        "safe",
        "qa_evidence_path",
        "promotion_approval",
        "git merge --ff-only",
        "BLOCKED:",
        "project-approved promotion evidence",
        "tag_pattern",
    ):
        assert token in procedure, f"Procedure must mention {token}"
    _assert_regex(
        procedure,
        r"before.{0,120}(side effects|promotion|tag|manifest)|"
        r"(side effects|promotion|tag|manifest).{0,120}before",
        "Procedure must validate before side effects",
    )
    _assert_regex(
        procedure,
        r"(never|do not|must not).{0,180}(squash|rebase|merge-commit)|"
        r"(squash|rebase|merge-commit).{0,180}(never|do not|must not|invent)",
        "Procedure must not invent squash, rebase, or merge-commit strategies",
    )
    _assert_regex(
        procedure,
        r"(create|record).{0,80}release tag evidence|"
        r"release tag evidence.{0,80}(create|record)",
        "Procedure must create or record release tag evidence",
    )
    _assert_regex(
        procedure,
        r"final version identity.{0,120}tag_pattern|tag_pattern.{0,120}"
        r"final version identity",
        "Procedure must validate final version identity against tag_pattern",
    )


def test_outputs_section():
    outputs = _section_after_h2(_operator_body(), "Outputs")

    for token in (
        "main_branch_name",
        "promotion evidence",
        "release tag evidence",
        "manifest_path",
        "release_manifest_path",
        "approval evidence",
        "stop-state evidence",
    ):
        assert token in outputs, f"Outputs must mention {token}"
    _assert_regex(
        outputs,
        r"manifest.{0,120}(promotion|tag).{0,120}entry|"
        r"(promotion|tag).{0,120}entry.{0,120}manifest",
        "Outputs must name manifest promotion/tag entry",
    )


def test_stop_conditions_section():
    stop_conditions = _section_after_h2(_operator_body(), "Stop Conditions")

    for token in (
        "Success",
        "BLOCKED:missing-required-input",
        "BLOCKED:promotion-approval-missing",
        "unsafe repo state",
        "non-fast-forward",
        "unsupported promotion path",
        "tag collision",
        "tag-pattern mismatch",
        "manifest-tag mismatch",
        "inconsistent tag evidence",
        "NEEDS_INPUT:<absolute_artifact_path>",
        "${scratch_dir}/questions/q-<uuidv4>.question.json",
    ):
        assert token in stop_conditions, f"Stop Conditions must mention {token}"
    _assert_regex(
        stop_conditions,
        r"human[- ]owned.{0,220}(value|scope|trade[- ]off|access|credential|Tier-3|approval)",
        "Stop Conditions must scope NEEDS_INPUT to human-owned questions",
    )
    _assert_regex(
        stop_conditions,
        r"procedural gaps?.{0,80}block|block.{0,80}procedural gaps?",
        "Stop Conditions must say procedural gaps block instead of asking",
    )


def test_cross_references_section():
    body = _operator_body()
    cross_references = _section_after_h2(body, "Cross-references")

    for path in CROSS_REFERENCES:
        assert path in body
        assert path in cross_references


def test_project_agnostic_paths():
    _frontmatter, body = _frontmatter_and_body(_operator_text())
    lower_body = body.lower()

    for forbidden in ("/home/nes/", "nestharus/ai"):
        assert forbidden not in lower_body
    for token in ("release_branch_name", "main_branch_name", "tag_pattern"):
        assert token in body


def test_dispatch_pattern():
    body = _operator_body()

    _assert_regex(
        body,
        r"release-orchestrator.{0,240}gpt-high|gpt-high.{0,240}release-orchestrator",
        "Body must say release-orchestrator invokes the gpt-high mechanics operator",
    )
    _assert_regex(
        body,
        r"agents -m gpt-high -p <worktree_path> -f <prompt-file>",
        "Body must name the agents CLI dispatch pattern",
    )
    _assert_regex(
        body,
        r"mechanics operator|operator.{0,80}mechanics",
        "Body must call this a mechanics operator",
    )
