# Guard roadmap model-role and risk-gate prose against authority drift.
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _section_after_heading(
    text: str,
    heading_regex: str,
    next_heading_pattern: str = r"(?m)^##\s+",
    label: str = "document",
) -> str:
    """Return the slice of `text` from the first match of `heading_regex` (anchored as ^...$ in MULTILINE) up to but not including the next match of `next_heading_pattern`."""
    match = re.search(rf"(?m)^{heading_regex}$", text)
    if match is None:
        pytest.fail(f"{label}: missing section heading matching: {heading_regex}")
    following = text[match.end() :]
    next_heading = re.search(next_heading_pattern, following)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _assert_no_forbidden_patterns(
    section: str, patterns: list[str], label: str
) -> None:
    for pattern in patterns:
        match = re.search(pattern, section, re.S)
        if match is None:
            continue
        line_start = section.rfind("\n", 0, match.start()) + 1
        line_end = section.find("\n", match.start())
        if line_end == -1:
            line_end = len(section)
        line_number = section.count("\n", 0, match.start()) + 1
        line_context = f"line {line_number}: {section[line_start:line_end].strip()}"
        pytest.fail(
            f"{label}: contains forbidden pattern {pattern!r} at "
            f"{line_context}\n\n{section[:900]}"
        )


ROADMAP_RISK_MODEL_ROWS = [
    pytest.param(
        {
            "rel_path": "agents/roadmap-orchestrator.md",
            "section_anchor": r"#### Stage 1b: Executive Risk Assessment.*",
            "next_heading_pattern": r"(?m)^####\s+",
            "required_patterns": [
                r"Completeness.*gpt-high",
                r"Market misread.*claude-opus",
                r"Dependency trap.*claude-opus",
            ],
            "forbidden_patterns": [r"3x claude-opus", r"Completeness.*claude-opus"],
        },
        id="roadmap-orch-stage-1b",
    ),
    pytest.param(
        {
            "rel_path": "agents/roadmap-orchestrator.md",
            "section_anchor": r"#### Stage 1b: Executive Risk Assessment.*",
            "next_heading_pattern": r"(?m)^####\s+",
            "required_patterns": [
                r"agents\s+-m\s+gpt-high[^\n]*executive-risk-completeness\.md"
            ],
            "forbidden_patterns": [
                r"agents\s+-m\s+claude-opus[^\n]*executive-risk-completeness\.md"
            ],
        },
        id="roadmap-orch-stage-1b-dispatch",
    ),
    pytest.param(
        {
            "rel_path": "agents/roadmap-orchestrator.md",
            "section_anchor": r"#### Stage 2c: Engineering Risk Assessment.*",
            "next_heading_pattern": r"(?m)^####\s+",
            "required_patterns": [
                r"Feasibility.*gpt-high",
                r"Integration.*claude-opus",
                r"Drift.*claude-opus",
            ],
            "forbidden_patterns": [r"3x claude-opus", r"Feasibility.*claude-opus"],
        },
        id="roadmap-orch-stage-2c",
    ),
    pytest.param(
        {
            "rel_path": "agents/roadmap-orchestrator.md",
            "section_anchor": r"#### Stage 3b: AI Risk Assessment.*",
            "next_heading_pattern": r"(?m)^####\s+",
            "required_patterns": [
                r"Coverage.*gpt-high",
                r"Decomposition.*claude-opus",
                r"Dependency.*claude-opus",
            ],
            "forbidden_patterns": [r"3x claude-opus", r"Coverage.*claude-opus"],
        },
        id="roadmap-orch-stage-3b",
    ),
    pytest.param(
        {
            "rel_path": "agents/roadmap-orchestrator.md",
            "section_anchor": r"## Model Selection",
            "next_heading_pattern": r"(?m)^(?:\*\*Anti-patterns:\*\*|##\s+)",
            "required_patterns": [r"models/roles\.md"],
            "forbidden_patterns": [
                r"Risk assessment\s*\|\s*`?claude-opus`?\s*\|\s*Alignment checking, coherence judgment",
                r"(?i)all\s+risk\s+assessments\s+use\s+`claude-opus`?",
            ],
        },
        id="roadmap-orch-model-selection-table",
    ),
    pytest.param(
        {
            "rel_path": "agents/roadmap-orchestrator.md",
            "section_anchor": r"### Stage 3c: Validate AI Roadmap",
            "next_heading_pattern": r"(?m)^###\s+",
            "required_patterns": [r"models/roles\.md"],
            "forbidden_patterns": [r"model roles table in AGENTS\.md"],
        },
        id="roadmap-orch-stage-3c-validate",
    ),
    pytest.param(
        {
            "rel_path": "AGENTS.md",
            "section_anchor": r"### Roadmap cascade",
            "next_heading_pattern": r"(?m)^###\s+",
            "required_patterns": [r"3x risk gates", r"all-LOW"],
            "forbidden_patterns": [
                r"3x risk gates \(claude-opus, all-LOW required\)"
            ],
        },
        id="agents-md-roadmap-cascade",
    ),
    pytest.param(
        {
            "rel_path": "agents/ai-roadmap-proposer.md",
            "section_anchor": r"### Step 1: Understand the implementation pipeline",
            "next_heading_pattern": r"(?m)^###\s+",
            "required_patterns": [],
            "forbidden_patterns": [r"3x risk"],
        },
        id="proposer-step-1-pipeline-summary",
    ),
    pytest.param(
        {
            "rel_path": "agents/ai-roadmap-proposer.md",
            "section_anchor": r"### Step 1: Understand the implementation pipeline",
            "next_heading_pattern": r"(?m)^###\s+",
            "required_patterns": [r"models/roles\.md"],
            "forbidden_patterns": [r"model roles table"],
        },
        id="proposer-step-1-authority",
    ),
    pytest.param(
        {
            "rel_path": "agents/ai-roadmap-proposer.md",
            "section_anchor": r"## Quality checklist",
            "next_heading_pattern": r"(?m)^##\s+",
            "required_patterns": [r"models/roles\.md"],
            "forbidden_patterns": [r"model roles table in AGENTS\.md"],
        },
        id="proposer-checklist-authority",
    ),
    pytest.param(
        {
            "rel_path": "agents/roadmap-risk-types.md",
            "section_anchor": r"# .+",
            "next_heading_pattern": r"(?m)^##\s+",
            "required_patterns": [
                r"(?i)three risk agents run in parallel",
                r"(?i)all must return LOW",
                r"workflows/roadmap\.md",
            ],
            "forbidden_patterns": [r"(?i)Risk assessments use\s+`?claude-opus`?"],
        },
        id="risk-types-overview",
    ),
    pytest.param(
        {
            "rel_path": "workflows/roadmap.md",
            "section_anchor": r"## Risk-Type Reference",
            "next_heading_pattern": r"(?m)^##\s+",
            "required_patterns": [
                r"Presence and checklist-style risks go to `gpt-high`",
                r"Intent and direction-style risks go to `claude-opus`",
                r"Executive\s*\|\s*Market misread\s*\|\s*`claude-opus`",
                r"Executive\s*\|\s*Dependency trap\s*\|\s*`claude-opus`",
                r"Executive\s*\|\s*Completeness\s*\|\s*`gpt-high`",
                r"Engineering\s*\|\s*Feasibility\s*\|\s*`gpt-high`",
                r"Engineering\s*\|\s*Integration\s*\|\s*`claude-opus`",
                r"Engineering\s*\|\s*Drift\s*\|\s*`claude-opus`",
                r"AI\s*\|\s*Decomposition\s*\|\s*`claude-opus`",
                r"AI\s*\|\s*Coverage\s*\|\s*`gpt-high`",
                r"AI\s*\|\s*Dependency\s*\|\s*`claude-opus`",
            ],
            "forbidden_patterns": [r"(?i)Risk assessments use\s+`?claude-opus`?"],
        },
        id="roadmap-workflow-risk-type-reference",
    ),
]


def test_roadmap_orchestrator_model_authority_cites_roles_md():
    path = REPO_ROOT / "agents/roadmap-orchestrator.md"
    section = _section_after_heading(
        path.read_text(encoding="utf-8"),
        r"## Model Selection",
        r"(?m)^(?:\*\*Anti-patterns:\*\*|##\s+)",
        str(path),
    )

    assert re.search(r"models/roles\.md", section), (
        f"{path}: ## Model Selection is missing required pattern "
        f"models/roles\\.md\n\n{section[:900]}"
    )
    assert not re.search(r"src/models\.md", section), (
        f"{path}: ## Model Selection contains forbidden pattern "
        f"src/models\\.md\n\n{section[:900]}"
    )


@pytest.mark.parametrize("row", ROADMAP_RISK_MODEL_ROWS)
def test_roadmap_risk_model_split_cascades_to_all_restatements(row):
    rel_path = row["rel_path"]
    section_anchor = row["section_anchor"]
    section = _section_after_heading(
        (REPO_ROOT / rel_path).read_text(encoding="utf-8"),
        section_anchor,
        row.get("next_heading_pattern", r"(?m)^##\s+"),
        rel_path,
    )

    for pattern in row["required_patterns"]:
        assert re.search(pattern, section, re.S), (
            f"{rel_path}: section anchor {section_anchor!r} is missing required "
            f"pattern {pattern!r}\n\n{section[:900]}"
        )

    _assert_no_forbidden_patterns(
        section, row["forbidden_patterns"], f"{rel_path}: {section_anchor!r}"
    )


def test_ai_roadmap_proposer_phase4_fanout_matches_implementation_orchestrator():
    rel_path = "agents/ai-roadmap-proposer.md"
    section_anchor = r"### Step 7: Assign pipeline phases per work unit"
    section = _section_after_heading(
        (REPO_ROOT / rel_path).read_text(encoding="utf-8"),
        section_anchor,
        r"(?m)^###\s+",
        rel_path,
    )
    required_patterns = [
        r"[Aa]udit\s*risk.*gpt-high",
        r"[Ss]cope\s*risk.*claude-opus",
        r"[Ss]hortcut\s*risk.*claude-opus",
        r"[Ss]upported.surface\s*risk.*claude-opus",
    ]
    forbidden_patterns = [
        r"Risk:\s*claude-opus\s*\(3x\s*parallel\)",
        r"(?i)Phase 4 \(3x risk\)",
    ]

    for pattern in required_patterns:
        assert re.search(pattern, section, re.S), (
            f"{rel_path}: section anchor {section_anchor!r} is missing required "
            f"pattern {pattern!r}\n\n{section[:900]}"
        )

    _assert_no_forbidden_patterns(
        section, forbidden_patterns, f"{rel_path}: {section_anchor!r}"
    )
