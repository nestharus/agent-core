import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONV_PATH = REPO_ROOT / "conventions" / "proposer-research-integration.md"

REQUIRED_H2_HEADINGS = (
    "Purpose",
    "Scope",
    "When Proposer Dispatches Research",
    "Current and Future Research Target",
    "Research Workflow Composition",
    "What Research Returns",
    "Proposer Revision",
    "Cycle Re-Entry",
    "Anti-Pattern: Research as Justification Generator",
    "Cross-References and Delegated Concerns",
    "Non-Goals",
)

REQUIRED_REFERENCES = (
    "proposer-critic-pattern.md",
    "../workflows/research.md",
    "../DECISIONS.md",
    "audit-history.md",
    "review-convergence.md",
    "gate-ownership.md",
    "../models/roles.md",
)

REMOTE_OR_ABSOLUTE_PREFIXES = ("http://", "https://", "mailto:", "~/")


def _conv_text():
    return CONV_PATH.read_text(encoding="utf-8")


def _markdown_link_targets(text):
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if target:
            yield target


def _target_path(target):
    target = target.split(None, 1)[0].strip("<>")
    target = target.split("#", 1)[0]
    return (CONV_PATH.parent / target).resolve()


def _anti_pattern_body(text):
    heading = "## Anti-Pattern: Research as Justification Generator"
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    assert match, f"missing required section: {heading}"

    following = text[match.end() :]
    next_h2 = re.search(r"(?m)^##\s+", following)
    if next_h2:
        return following[: next_h2.start()]
    return following


def test_proposer_research_integration_convention_exists_and_is_nontrivial():
    """T1 risk: omitted, renamed, or empty convention; level: unit; source: contract T1."""
    byte_count = CONV_PATH.stat().st_size if CONV_PATH.exists() else 0

    assert CONV_PATH.exists(), (
        f"missing convention file: {CONV_PATH} (byte count: {byte_count})"
    )
    assert byte_count >= 500, (
        f"convention file too small: {CONV_PATH} (byte count: {byte_count})"
    )


def test_proposer_research_integration_required_h2_headings_present():
    """T2 risk: missing load-bearing section; level: unit; source: contract T2."""
    text = _conv_text()

    for heading in REQUIRED_H2_HEADINGS:
        pattern = rf"^##\s+{re.escape(heading)}\s*$"
        assert re.search(pattern, text, flags=re.MULTILINE), (
            f"missing required H2 heading: ## {heading}"
        )


def test_proposer_research_integration_required_references_present():
    """T3 risk: missing ownership or workflow reference; level: unit; source: contract T3."""
    text = _conv_text()

    for reference in REQUIRED_REFERENCES:
        assert reference in text, f"missing required reference: {reference}"


def test_proposer_research_integration_relative_markdown_links_resolve():
    """T4 risk: broken local documentation links; level: unit; source: contract T4."""
    text = _conv_text()
    unresolved = []

    for target in _markdown_link_targets(text):
        if target.startswith(REMOTE_OR_ABSOLUTE_PREFIXES):
            continue
        if not _target_path(target).exists():
            unresolved.append(target)

    assert unresolved == [], f"relative Markdown links do not resolve: {unresolved}"


def test_proposer_research_integration_anti_pattern_guard_wording_present():
    """T5 risk: research used as justification after approval; level: unit; source: contract T5."""
    body = _anti_pattern_body(_conv_text())
    missing = []

    if "justification" not in body:
        missing.append("justification")
    if not any(token in body for token in ("approved", "LOW")):
        missing.append("approved or LOW")
    if not any(
        phrase in body
        for phrase in ("does not override", "does not silence", "not acceptance")
    ):
        missing.append(
            "does not override / does not silence / not acceptance"
        )

    assert missing == [], f"anti-pattern section missing required wording: {missing}"
