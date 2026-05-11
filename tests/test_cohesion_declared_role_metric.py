"""Structural tests for the ACR-171 declared-role cohesion metric contract."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_QUALITY_MD = REPO_ROOT / "conventions" / "code-quality.md"
WORKFLOW_MD = REPO_ROOT / "workflows" / "code-quality.md"
COHESION_AUDITOR_MD = REPO_ROOT / "agents" / "cohesion-auditor.md"
DECISIONS_MD = REPO_ROOT / "DECISIONS.md"
ORCHESTRATOR_MD = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"
THIS_TEST_FILE = Path(__file__).resolve()

A1_CATEGORY_TOKENS = [
    "orchestration",
    "filter",
    "validator",
    "predicate",
    "mapper",
    "accessor",
    "formatter",
    "parser",
]


def _read_markdown(path):
    assert path.is_file(), f"missing markdown file: {path}"
    return path.read_text(encoding="utf-8")


def _assert_contains_all(text, substrings, label):
    missing = [substring for substring in substrings if substring not in text]
    assert missing == [], f"{label} is missing expected substrings: {missing}"


def test_convention_has_declared_roles_section():
    """Risk: canonical convention omits the ACR-171 declaration mechanism."""
    text = _read_markdown(CODE_QUALITY_MD)

    assert "## Declared roles" in text, (
        "conventions/code-quality.md must define ## Declared roles"
    )


def test_convention_vocabulary_tokens_present():
    """Risk: declared role sets drift from the A1 category vocabulary."""
    text = _read_markdown(CODE_QUALITY_MD)

    _assert_contains_all(
        text,
        [
            "Declared role set tokens must come from the A1 category vocabulary",
            *A1_CATEGORY_TOKENS,
        ],
        "conventions/code-quality.md",
    )


def test_convention_default_path_rule_present():
    """Risk: anti-scoped orchestrators lack the documented path default."""
    text = _read_markdown(CODE_QUALITY_MD)

    _assert_contains_all(
        text,
        [
            "`agents/*-orchestrator.md`",
            (
                "The default declared role set for `agents/*-orchestrator.md` "
                "is `orchestration`, `parser`."
            ),
            (
                "A documented path default supplies declared roles only when "
                "the file has no"
            ),
            "## Declared roles",
        ],
        "conventions/code-quality.md",
    )


def test_convention_count_only_fallback_rule_present():
    """Risk: declared-role refinement loses the explicit ordering rule (declared-role compare before count-only fallback)."""
    text = _read_markdown(CODE_QUALITY_MD)
    expected = "For cohesion scoring, compare the actual classification set to the declared role set before applying count-only fallback."
    assert expected in text, (
        "conventions/code-quality.md must contain the ordering rule:\n"
        f"  {expected!r}"
    )


def test_convention_refined_a1_row_present():
    """Risk: canonical A1 cohesion still uses count-only LOW/HIGH wording."""
    text = _read_markdown(CODE_QUALITY_MD)

    _assert_contains_all(
        text,
        [
            "Cohesion by classifications touched",
            "actual classifications are a subset of the declared role set",
            (
                "actual classifications exceed the declared role set or include "
                "classifications outside the declared role set"
            ),
        ],
        "conventions/code-quality.md",
    )


def test_convention_refined_a1_row_fallback_present():
    """Risk: unattributed files stop failing closed under the refined metric."""
    text = _read_markdown(CODE_QUALITY_MD)

    _assert_contains_all(
        text,
        [
            (
                "for files without declared roles or a documented path default, "
                "exactly 1 classification"
            ),
            (
                "for files without declared roles or a documented path default, "
                "2 or more classifications"
            ),
        ],
        "conventions/code-quality.md",
    )


def test_convention_legacy_a1_row_absent():
    """Risk: the legacy count-only row remains beside the refined row."""
    text = _read_markdown(CODE_QUALITY_MD)

    assert (
        "| `Cohesion by classifications touched` | 1 classification | n/a | "
        ">= 2 classifications |"
    ) not in text, "legacy count-only A1 cohesion row must be removed"


def test_convention_orchestrator_example_low():
    """Risk: orchestrator subset-match behavior lacks a concrete LOW example."""
    text = _read_markdown(CODE_QUALITY_MD)
    example_start = text.find("agents/implementation-pipeline-orchestrator.md")
    assert example_start != -1, (
        "orchestrator LOW example must reference "
        "agents/implementation-pipeline-orchestrator.md"
    )
    example = text[max(0, example_start - 300) : example_start + 700]

    _assert_contains_all(
        example,
        [
            "agents/implementation-pipeline-orchestrator.md",
            "orchestration",
            "parser",
            "LOW",
        ],
        "conventions/code-quality.md orchestrator example",
    )


def test_convention_orchestrator_example_high_phrase():
    """Risk: examples omit the HIGH case for undeclared classifications."""
    text = _read_markdown(CODE_QUALITY_MD)

    assert "classifications outside the declared role set" in text, (
        "orchestrator HIGH example must name classifications outside the declared role set"
    )


def test_workflow_mirror_phrases_present():
    """Risk: workflow mirror drifts from the canonical declared-role metric."""
    text = _read_markdown(WORKFLOW_MD)

    _assert_contains_all(
        text,
        [
            "LOW when actual classifications are a subset of the declared role set",
            (
                "HIGH when actual classifications exceed the declared role set "
                "or include classifications outside the declared role set"
            ),
            "~/ai/conventions/code-quality.md",
        ],
        "workflows/code-quality.md",
    )


def test_workflow_canonical_source_phrase_present():
    """Risk: workflow mirror becomes a competing canonical rule source."""
    text = _read_markdown(WORKFLOW_MD)

    assert "remains the canonical rule source" in text, (
        "workflow mirror must state that the convention remains canonical"
    )


def test_cohesion_auditor_binding_phrases_present():
    """Risk: cohesion auditor applies the old count-only local binding."""
    text = _read_markdown(COHESION_AUDITOR_MD)

    _assert_contains_all(
        text,
        [
            "Cohesion by classifications touched",
            "LOW = actual classifications are a subset of the declared role set",
            (
                "HIGH = actual classifications exceed the declared role set or "
                "include classifications outside the declared role set"
            ),
        ],
        "agents/cohesion-auditor.md",
    )


def test_cohesion_auditor_legacy_binding_absent():
    """Risk: auditor binding still advertises the legacy threshold bands."""
    text = _read_markdown(COHESION_AUDITOR_MD)

    assert (
        "LOW = 1 classification; MEDIUM = n/a; HIGH = >= 2 classifications"
    ) not in text, "legacy cohesion auditor binding must be removed"


def test_decisions_entry_present():
    """Risk: durable decision log omits the ACR-171 residual and rationale."""
    text = _read_markdown(DECISIONS_MD)
    heading_match = re.search(
        r"^## D-2026-05-11[^\n]*ACR-171[^\n]*$",
        text,
        flags=re.MULTILINE,
    )
    assert heading_match is not None, (
        "DECISIONS.md ACR-171 entry must use a D-2026-05-11* decision heading"
    )
    entry_start = heading_match.start()
    next_heading = text.find("\n## D-", entry_start + 1)
    entry = text[entry_start : next_heading if next_heading != -1 else len(text)]

    _assert_contains_all(
        entry,
        [
            "ACR-171",
            "declared-role-match",
            "agents/*-orchestrator.md",
            "test_code_quality_required_headings_present_in_order",
            "out of ACR-171 scope",
            "Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>",
        ],
        "DECISIONS.md ACR-171 entry",
    )


def test_orchestrator_file_unmodified_by_pytest():
    """Risk: tests-first guard mutates the anti-scoped orchestrator file."""
    assert ORCHESTRATOR_MD.is_file(), (
        "expected anti-scoped orchestrator file to exist for read-only guard"
    )
    _read_markdown(ORCHESTRATOR_MD)
    source = THIS_TEST_FILE.read_text(encoding="utf-8")

    target_markers = ("implementation-pipeline-orchestrator.md", "ORCHESTRATOR_MD")
    forbidden_patterns = (
        ".write_text(",
        ".write_bytes(",
        ".open(",
        "open(",
        "os.system(",
    )
    offending_lines = [
        line.strip()
        for line in source.splitlines()
        if any(marker in line for marker in target_markers)
        and any(pattern in line for pattern in forbidden_patterns)
    ]
    assert offending_lines == [], (
        "test module must not contain write-capable calls targeting "
        f"agents/implementation-pipeline-orchestrator.md: {offending_lines}"
    )
