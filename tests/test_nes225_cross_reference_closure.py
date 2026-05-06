"""Structural closure tests for NES-225 cross-reference reachability."""

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD = REPO_ROOT / "AGENTS.md"
WORKFLOW_INDEX_JSON = REPO_ROOT / "workflows" / "index.json"

NES219_ROUTABLE_OPERATORS = (
    "workflow-design-auditor",
    "agent-design-auditor",
    "workflow-process-auditor",
    "implementation-pipeline-orchestrator",
)

SPLIT_AUDITOR_REFERENCE_FILES = (
    REPO_ROOT / "agents" / "workflow-design-auditor.md",
    REPO_ROOT / "agents" / "agent-design-auditor.md",
    REPO_ROOT / "agents" / "function-classification-auditor.md",
    REPO_ROOT / "agents" / "push-pull-auditor.md",
    REPO_ROOT / "conventions" / "design-patterns.md",
)


def _section_after_heading(text, heading):
    match = re.search(rf"(?m)^{re.escape(heading)}$", text)
    assert match, f"missing section heading: {heading}"
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^##\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _routing_row(text, name):
    match = re.search(rf"(?ms)^- `{re.escape(name)}` - .*?(?=^- `|\Z)", text)
    assert match, f"missing operator row: {name}"
    return match.group(0)


def _bullet_markdown_links(text):
    for line in text.splitlines():
        if not line.startswith("- "):
            continue
        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
            yield match.group(1), match.group(2)


def _bullet_markdown_targets(text):
    return {target for _label, target in _bullet_markdown_links(text)}


def test_nes219_routable_operators_have_agents_routing_rows():
    agents_text = AGENTS_MD.read_text(encoding="utf-8")
    routing_table = _section_after_heading(agents_text, "## Operator Routing Table")

    for name in NES219_ROUTABLE_OPERATORS:
        row = _routing_row(routing_table, name)
        assert f"(agents/{name}.md)" in row
        assert "Model:" in row


def test_nes219_workflows_have_agents_topology_rows():
    agents_text = AGENTS_MD.read_text(encoding="utf-8")
    topologies = _section_after_heading(agents_text, "## Workflow Topologies")

    assert "workflows/audit.md" in _bullet_markdown_targets(topologies)
    assert "workflows/implementation-pipeline.md" in _bullet_markdown_targets(
        topologies
    )


def test_nes219_conventions_have_agents_first_hop_bullets():
    agents_text = AGENTS_MD.read_text(encoding="utf-8")
    conventions = _section_after_heading(agents_text, "## Conventions")

    assert "conventions/design-patterns.md" in _bullet_markdown_targets(conventions)
    assert "conventions/proposer-critic-pattern.md" in _bullet_markdown_targets(
        conventions
    )


@pytest.mark.parametrize(
    ("workflow_id", "path"),
    (
        ("audit", "workflows/audit.md"),
        ("implementation-pipeline", "workflows/implementation-pipeline.md"),
    ),
)
def test_workflow_index_contains_audit_and_implementation_pipeline_entries(
    workflow_id,
    path,
):
    index = json.loads(WORKFLOW_INDEX_JSON.read_text(encoding="utf-8"))
    entry = index["workflows"][workflow_id]

    assert entry["path"] == path
    assert entry["workflow"]["id"] == workflow_id


def test_nes209_split_auditor_references_are_consistent():
    for path in SPLIT_AUDITOR_REFERENCE_FILES:
        text = path.read_text(encoding="utf-8")

        assert "cohesion-coupling-auditor" not in text
        assert "cohesion-auditor" in text
        assert "coupling-auditor" in text
