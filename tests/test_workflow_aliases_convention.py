import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONV_PATH = REPO_ROOT / "conventions" / "workflow-aliases.md"


REQUIRED_SECTION_PATTERNS = (
    ("Purpose", r"(?im)^#{1,6}\s+Purpose\b"),
    (
        "Use When / Do Not Use When",
        r"(?im)^#{1,6}\s+.*Use When.*Do Not Use When\b|^#{1,6}\s+Use When\b.*^#{1,6}\s+Do Not Use When\b",
    ),
    ("Workflow identity", r"(?im)^#{1,6}\s+Workflow identity\b"),
    (
        "Workflow alias declarations",
        r"(?im)^#{1,6}\s+Workflow alias declarations\b",
    ),
    (
        "Per-context disambiguation",
        r"(?im)^#{1,6}\s+Per-context disambiguation\b",
    ),
    (
        "Workflow dispatch contract",
        r"(?im)^#{1,6}\s+Workflow dispatch contract\b",
    ),
    (
        'Naming: "workflow dispatch contract" vs "contract"',
        r'(?im)^#{1,6}\s+Naming:\s+"workflow dispatch contract"\s+vs\s+"contract"(?:\s|$)',
    ),
    (
        "Composition with adjacent conventions",
        r"(?im)^#{1,6}\s+Composition with adjacent conventions\b",
    ),
    ("Anti-pattern / Non-goals", r"(?im)^#{1,6}\s+Anti-pattern / Non-goals\b"),
    ("Lifecycle / Maintenance", r"(?im)^#{1,6}\s+Lifecycle / Maintenance\b"),
)

SCHEMA_KEY_PATTERNS = {
    "workflow.id": r"workflow\.id|workflow:\s*\n(?:[^\n]*\n){0,4}\s+id:",
    "workflow_aliases": r"\bworkflow_aliases\b",
    "target.workflow_id": r"target\.workflow_id|target:\s*\n(?:[^\n]*\n){0,8}\s+workflow_id:",
    "target.path": r"target\.path|target:\s*\n(?:[^\n]*\n){0,8}\s+path:",
    "target.anchor": r"target\.anchor|target:\s*\n(?:[^\n]*\n){0,8}\s+anchor:",
    "target.phase": r"target\.phase|target:\s*\n(?:[^\n]*\n){0,8}\s+phase:",
    "disambiguation": r"\bdisambiguation\b",
    "workflow_dispatch_contract": r"\bworkflow_dispatch_contract\b",
    "workflow_dispatch_contract.orchestrator": r"workflow_dispatch_contract\.orchestrator|\borchestrator:",
    "workflow_dispatch_contract.inputs": r"workflow_dispatch_contract\.inputs|\binputs:",
    "workflow_dispatch_contract.expectations": r"workflow_dispatch_contract\.expectations|\bexpectations:",
    "workflow_dispatch_contract.outputs": r"workflow_dispatch_contract\.outputs|\boutputs:",
    "workflow_dispatch_contract.non_goals": r"workflow_dispatch_contract\.non_goals|\bnon_goals:",
}

DISPATCH_CONTRACT_KEYS = (
    "orchestrator",
    "inputs",
    "expectations",
    "outputs",
    "non_goals",
)

REQUIRED_RELATIVE_LINK_TARGETS = (
    "../conventions/workflow-routing.md",
    "../conventions/agent-questions-and-session-graph.md",
    "../agents/operator-file-format.md",
)

def _conv_text():
    return CONV_PATH.read_text(encoding="utf-8")


def _relative_markdown_targets(text):
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if not target:
            continue
        target = target.split(None, 1)[0].strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "/", "#")):
            continue
        target = target.split("#", 1)[0]
        if target:
            yield target


def test_workflow_aliases_convention_file_exists():
    """T1 risk: omitted/renamed convention; level: unit; source: proposal §7 T1."""
    assert CONV_PATH.exists(), f"missing convention file: {CONV_PATH}"


def test_required_sections_are_present():
    """T2 risk: missing/renamed topics; level: unit; source: proposal §7 T2."""
    text = _conv_text()
    for section, pattern in REQUIRED_SECTION_PATTERNS:
        assert re.search(pattern, text), f"missing required section: {section}"


def test_required_schema_keys_are_documented():
    """T3 risk: missing YAML keys; level: unit; source: proposal §7 T3."""
    text = _conv_text()
    for key, pattern in SCHEMA_KEY_PATTERNS.items():
        assert re.search(pattern, text), f"missing schema key documentation: {key}"


def test_dispatch_contract_has_fixed_key_set():
    """T4 risk: ad hoc dispatch keys; level: unit; source: proposal §7 T4."""
    text = _conv_text()
    for key in DISPATCH_CONTRACT_KEYS:
        assert re.search(rf"\b{re.escape(key)}\b", text), (
            f"missing workflow_dispatch_contract fixed key: {key}"
        )
    assert re.search(r"(?i)fixed key set|the only keys|no other keys", text), (
        "workflow_dispatch_contract must state that its five-key set is fixed"
    )


def test_relative_markdown_links_resolve():
    """T5 risk: broken adjacent references; level: unit; source: proposal §7 T5."""
    text = _conv_text()
    targets = list(_relative_markdown_targets(text))
    missing_required = [
        target for target in REQUIRED_RELATIVE_LINK_TARGETS if target not in targets
    ]
    assert missing_required == [], (
        f"missing required relative links: {missing_required}"
    )
    assert any(target.startswith("../workflows/") for target in targets), (
        "missing required relative link to an example workflow under ../workflows/"
    )

    missing = [
        target
        for target in targets
        if not (CONV_PATH.parent / target).resolve().exists()
    ]
    assert missing == [], f"relative Markdown links do not resolve: {missing}"
