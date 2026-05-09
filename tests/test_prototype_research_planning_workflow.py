"""ACR-143 behavior-only structural guards; no procedural assertions; no implementation tests.

Read-only proposal context:
${planning_dir}/proposals/acr-143-acr-143.md.
This module does not assert specific entries inside workflows/index.json;
tests/test_workflow_metadata.py::test_workflow_index_is_current owns generated
index.json freshness.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.workflow_index.generator import parse_frontmatter


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / "workflows"
    / "prototype-research-planning.md"
)
OPERATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "agents"
    / "prototype-research-planner.md"
)

_WORKFLOW_TEXT: str | None = None
_OPERATOR_TEXT: str | None = None
_WORKFLOW_FRONTMATTER: dict | None = None
_OPERATOR_FRONTMATTER: dict | None = None


def _workflow_text() -> str:
    global _WORKFLOW_TEXT
    if _WORKFLOW_TEXT is None:
        assert WORKFLOW_PATH.is_file(), f"workflow file not found: {WORKFLOW_PATH}"
        _WORKFLOW_TEXT = WORKFLOW_PATH.read_text(encoding="utf-8")
    return _WORKFLOW_TEXT


def _operator_text() -> str:
    global _OPERATOR_TEXT
    if _OPERATOR_TEXT is None:
        assert OPERATOR_PATH.is_file(), f"operator file not found: {OPERATOR_PATH}"
        _OPERATOR_TEXT = OPERATOR_PATH.read_text(encoding="utf-8")
    return _OPERATOR_TEXT


def _workflow_frontmatter() -> dict:
    global _WORKFLOW_FRONTMATTER
    if _WORKFLOW_FRONTMATTER is None:
        _WORKFLOW_FRONTMATTER = parse_frontmatter(
            _workflow_text(),
            str(WORKFLOW_PATH),
        )
    return _WORKFLOW_FRONTMATTER


def _operator_frontmatter() -> dict:
    global _OPERATOR_FRONTMATTER
    if _OPERATOR_FRONTMATTER is None:
        _OPERATOR_FRONTMATTER = parse_frontmatter(
            _operator_text(),
            str(OPERATOR_PATH),
        )
    return _OPERATOR_FRONTMATTER


def _assert_contains(text: str, *tokens: str, case_sensitive: bool = False) -> None:
    haystack = text if case_sensitive else text.lower()
    for token in tokens:
        needle = token if case_sensitive else token.lower()
        assert needle in haystack, f"missing token: {token!r}"


def _assert_matches(text: str, pattern: str, description: str) -> None:
    assert re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL), (
        f"missing {description}: {pattern}"
    )


def _heading_pos(text: str, heading: str) -> int:
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    assert match, f"missing heading: {heading}"
    return match.start()


def _section_after_heading(text: str, heading: str) -> str:
    start = _heading_pos(text, heading)
    following = text[start + len(heading) :]
    next_heading = re.search(r"(?m)^##\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _phase_section(text: str, phase_number: int) -> str:
    pattern = rf"(?m)^### Phase {phase_number}\b[^\n]*$"
    match = re.search(pattern, text)
    assert match, f"missing Phase {phase_number} heading"
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^### (?:Phase \d+|Approval gate)\b[^\n]*$", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _procedure_section(text: str) -> str:
    return _section_after_heading(text, "## Procedure")


def _no_build_prototype_phase_zero_claim(text: str) -> None:
    assert re.search(
        r"build-prototype\.md[\s\S]{0,200}?Phase\s*0\b",
        text,
        flags=re.IGNORECASE,
    ) is None


def test_ti_001_workflow_doc_exists():
    assert WORKFLOW_PATH.is_file()


def test_ti_002_workflow_id_frontmatter():
    assert _workflow_frontmatter()["workflow"]["id"] == "prototype-research-planning"


def test_ti_003_dispatch_contract_keys():
    contract = _workflow_frontmatter()["workflow_dispatch_contract"]

    assert set(contract) == {
        "orchestrator",
        "inputs",
        "expectations",
        "outputs",
        "non_goals",
    }


def test_ti_004_seven_phases_in_order():
    text = _workflow_text()
    pattern = (
        r"^### Phase 1\b.*?"
        r"^### Phase 2\b.*?"
        r"^### Phase 3\b.*?"
        r"^### Phase 4\b.*?"
        r"^### Phase 5\b.*?"
        r"^### Phase 6\b.*?"
        r"^### Phase 7\b"
    )

    assert re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)


def test_ti_005_required_inputs_named():
    _assert_contains(
        _workflow_text(),
        "originating context",
        "user preferences",
        "planning_dir",
        "worktree_path",
        "scratch_dir",
        "defer dossier",
        "downstream consumer",
    )


def test_ti_006_outputs_named():
    _assert_contains(
        _workflow_text(),
        "behaviors.md",
        "ux.md",
        "contracts.md",
        "expectations.md",
        "avenues.md",
        "anti-scope.md",
        "prototype-proposal.md",
        "approval evidence",
        "behavior tests",
    )


def test_ti_007_approval_gate_position():
    text = _workflow_text()

    assert (
        _heading_pos(text, "### Phase 5 — Proposal")
        < _heading_pos(text, "### Approval gate")
        < _heading_pos(text, "### Phase 6 — Behavior tests (post-approval)")
    )


def test_ti_008_behavior_only_test_rule():
    text = _workflow_text()

    _assert_matches(text, r"behavior[- ]only", "behavior-only test rule")
    _assert_matches(text, r"observable\s+behavior|\bbehavior\b", "observable behavior")
    _assert_matches(text, r"never\s+(?:include\s+)?implementation", "never implementation boundary")
    _assert_contains(
        text,
        "specific functions called",
        "internal data structures",
        "library choices",
        "file layouts",
    )


def test_ti_009_no_procedural_tests():
    text = _workflow_text()

    _assert_matches(text, r"no\s+procedural\s+tests|forbid\w*\s+procedural", "procedural-test ban")
    _assert_contains(
        text,
        "races",
        "retry",
        "lifecycle",
        "internal invariants",
    )


def test_ti_010_avenues_fluid():
    text = _workflow_text()

    _assert_contains(text, "fluid", "candidate")
    _assert_matches(
        text,
        r"not\s+(?:commitments|specifications)|non-committal",
        "non-commitment wording",
    )


def test_ti_011_repo_true_handoff():
    text = _workflow_text()

    _assert_contains(
        text,
        "prototype-orchestrator.md",
        "Phase P0",
        "prototype input context",
        "build-prototype.md",
        "Phase P1",
        case_sensitive=True,
    )
    _no_build_prototype_phase_zero_claim(text)


def test_ti_012_workflow_anti_scope():
    text = _workflow_text()

    for pattern, description in (
        (r"no\s+market\s+research", "market research exclusion"),
        (r"no\s+comparable-product\s+analysis", "comparable-product exclusion"),
        (r"no\s+philosophy", "philosophy exclusion"),
        (r"no\s+4-layer\s+cascade", "4-layer cascade exclusion"),
        (r"no\s+ticket\s+regeneration", "ticket regeneration exclusion"),
        (r"no\s+risk-gate\s+cycles", "risk-gate cycle exclusion"),
        (r"no\s+implementation-detail\s+decisions", "implementation-detail exclusion"),
        (r"no\s+design\s+specification", "design specification exclusion"),
        (r"no\s+machine\s+enforcement", "machine enforcement exclusion"),
        (r"no\s+procedural\s+tests", "procedural tests exclusion"),
    ):
        _assert_matches(text, pattern, description)


def test_ti_013_operator_exists():
    assert OPERATOR_PATH.is_file()


def test_ti_014_operator_frontmatter():
    frontmatter = _operator_frontmatter()

    assert set(frontmatter) == {"description", "model", "output_format"}
    assert "prototype research planning workflow" in frontmatter["description"].lower()
    assert frontmatter["model"] == "gpt-high"


def test_ti_015_operator_inputs_outputs():
    _assert_contains(
        _operator_text(),
        "originating context",
        "repo_root",
        "worktree_path",
        "planning_dir",
        "scratch_dir",
        "user preferences",
        "approval evidence",
        "research-plan bundle",
        "proposal",
        "tests",
        "handoff summary",
    )


def test_ti_016_operator_seven_phase_substeps_with_body():
    procedure = _procedure_section(_operator_text())
    pattern = (
        r"^### Phase 1\b.*?"
        r"^### Phase 2\b.*?"
        r"^### Phase 3\b.*?"
        r"^### Phase 4\b.*?"
        r"^### Phase 5\b.*?"
        r"^### Phase 6\b.*?"
        r"^### Phase 7\b"
    )

    assert re.search(pattern, procedure, flags=re.MULTILINE | re.DOTALL)
    assert re.search(r"(?m)^\s*1\.\s+", procedure)
    for phase_number in range(1, 8):
        body = _phase_section(procedure, phase_number)
        assert len(re.sub(r"\s+", "", body)) >= 50, (
            f"Phase {phase_number} body is too thin"
        )


def test_ti_017_approval_stop_condition():
    text = _operator_text()

    _assert_matches(text, r"Phase\s+5.{0,220}Phase\s+6", "Phase 5/Phase 6 boundary")
    _assert_contains(text, "durable approval evidence", "BLOCKED:proposal-not-approved")


def test_ti_018_dispatch_boundaries():
    _assert_contains(
        _operator_text(),
        "smart planning agent",
        "audit pass",
        "test-writer",
        "post-approval",
    )


def test_ti_019_root_owned_questions():
    text = _operator_text()

    _assert_contains(text, "NEEDS_INPUT:<question_artifact>")
    _assert_matches(text, r"user-owned|root-owned", "user-owned/root-owned questions")
    _assert_matches(text, r"operator-owned", "operator-owned procedural choices")


def test_ti_020_no_index_content_assertion():
    source = Path(__file__).read_text(encoding="utf-8")

    assert "tests/test_workflow_metadata.py::test_workflow_index_is_current" in source
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("assert") and "index.json" in stripped:
            assert "prototype-research-planning" not in stripped


def test_ti_021_lighter_path_framing():
    text = _workflow_text()

    _assert_contains(text, "lighter", "prototype", "roadmap")
    _assert_matches(
        text,
        r"not\s+the\s+full\s+product-strategy\s+roadmap|"
        r"without\s+copying\s+the\s+full\s+roadmap\s+cascade",
        "negative product-strategy cascade framing",
    )


def test_ti_022_per_phase_contract_tokens():
    text = _workflow_text()

    phase_tokens = {
        1: ("behaviors", "UX", "user-facing"),
        2: ("contracts", "expectations", "observable"),
        3: ("fluid", "candidate", "avenues"),
        4: ("anti-scope",),
        5: ("proposal", "approval"),
        6: ("behavior", "post-approval", "appropriate level"),
        7: ("handoff", "prototype input context"),
    }
    for phase_number, tokens in phase_tokens.items():
        _assert_contains(_phase_section(text, phase_number), *tokens)


def test_ti_023_behavior_test_annotation_rule():
    text = _workflow_text()

    _assert_contains(text, "Covers:", "B-", "UX-", "C-", "E-", case_sensitive=True)
    _assert_matches(text, r"behavior.*UX.*contract.*expectation", "source ID linkage")


def test_ti_024_operator_per_phase_tokens():
    text = _operator_text()

    phase_expectations = {
        1: ("user-visible", "implementation commitments"),
        2: ("observable verification",),
        3: ("fluid candidates",),
        4: ("roadmap-style expansion",),
        5: ("proposal", "explicit anti-scope"),
    }
    for phase_number, tokens in phase_expectations.items():
        _assert_contains(_phase_section(text, phase_number), *tokens)


def test_ti_025_operator_phase_6_forbids():
    phase_6 = _phase_section(_operator_text(), 6)

    _assert_contains(phase_6, "behavior-only", "test-writer")
    _assert_matches(phase_6, r"implementation assertions?", "implementation assertion ban")
    _assert_matches(phase_6, r"procedural internals|procedural tests", "procedural ban")


def test_ti_026_operator_phase_7_handoff():
    phase_7 = _phase_section(_operator_text(), 7)

    _assert_contains(
        phase_7,
        "prototype input context",
        "prototype-orchestrator.md",
        "Phase P0",
        "build-prototype.md",
        "Phase P1",
        "research-plan",
        "proposal",
        "approval evidence",
        "behavior test paths",
        case_sensitive=True,
    )
    _no_build_prototype_phase_zero_claim(phase_7)


def test_ti_027_operator_no_risk_gate_framing():
    text = _operator_text()

    _assert_matches(
        text,
        r"not\s+a\s+roadmap-style\s+risk\s+gate|no\s+risk-gate\s+cycle",
        "non-risk-gate audit framing",
    )
    _assert_matches(
        text,
        r"no\s+machine-enforcement\s+framing|no\s+machine\s+enforcement",
        "no machine-enforcement framing",
    )
    assert not re.search(r"require\w*[^\n]{0,80}risk-gate cycle", text, re.IGNORECASE)


def test_ti_028_operator_approval_format():
    _assert_contains(
        _operator_text(),
        "${planning_dir}/proposals/prototype-proposal.approval.md",
        "## Approver",
        "## Decision",
        "approved",
        "revisions-requested",
        "rejected",
        "## Approved scope",
        "${planning_dir}/proposals/prototype-proposal.md",
        "## Rationale",
        case_sensitive=True,
    )
