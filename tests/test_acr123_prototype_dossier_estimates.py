import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_PROTOTYPE_WORKFLOW = REPO_ROOT / "workflows" / "build-prototype.md"
PROTOTYPE_ORCHESTRATOR = REPO_ROOT / "agents" / "prototype-orchestrator.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section_with_heading_matching(text: str, heading_pattern: str) -> str:
    match = re.search(rf"(?m)^(?P<marks>##+)\s+.*(?:{heading_pattern}).*$", text)
    assert match, f"missing section heading matching: {heading_pattern}"
    level = len(match.group("marks"))
    following = text[match.end() :]
    next_heading = re.search(rf"(?m)^#{{2,{level}}}\s+", following)
    if next_heading:
        return following[: next_heading.start()]
    return following


def _subsection_within(section: str, heading_pattern: str) -> str:
    return _section_with_heading_matching(section, heading_pattern)


def _build_p33_section() -> str:
    return _section_with_heading_matching(_read(BUILD_PROTOTYPE_WORKFLOW), r"P3\.3")


def _build_p4_section() -> str:
    return _section_with_heading_matching(_read(BUILD_PROTOTYPE_WORKFLOW), r"Phase P4|P4")


def _build_roadmap_relationship_section() -> str:
    relationship = _section_with_heading_matching(
        _read(BUILD_PROTOTYPE_WORKFLOW),
        r"Relationship to other workflows",
    )
    return _subsection_within(relationship, r"Roadmap workflow")


def _orchestrator_p33_section() -> str:
    return _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"P3\.3")


def _orchestrator_p4_section() -> str:
    return _section_with_heading_matching(_read(PROTOTYPE_ORCHESTRATOR), r"Phase P4|P4")


def test_build_prototype_p33_documents_story_point_estimate_field() -> None:
    section = _build_p33_section()

    assert "story_point_estimate" in section
    assert "1, 2, 3, 5, 8, 13, 21, 40, 100" in section


def test_build_prototype_p33_documents_estimate_rationale_field() -> None:
    section = _build_p33_section()

    assert "estimate_rationale" in section
    assert re.search(r"(?i)\bone sentence\b|\bsingle sentence\b", section)


def test_build_prototype_p33_documents_confidence_field() -> None:
    section = _build_p33_section()

    assert "confidence" in section
    assert re.search(r"\bhigh\b\s*(?:\||,|/)\s*\bmedium\b\s*(?:\||,|/)\s*\blow\b", section)


def test_build_prototype_p4_maps_estimate_to_jira_customfield_10016() -> None:
    section = _build_p4_section()

    assert "customfield_10016" in section
    assert re.search(r"(?is)\binteger\b.{0,80}\bestimate\b|\bestimate\b.{0,80}\binteger\b", section)


def test_build_prototype_p4_maps_estimate_to_linear_estimate_field() -> None:
    section = _build_p4_section()

    assert re.search(r"(?is)\bLinear\b.{0,120}\binteger\b.{0,80}`?estimate`?\b", section)


def test_build_prototype_p4_preserves_estimate_in_filed_ticket_description() -> None:
    section = _build_p4_section()

    assert "Story Point Estimate" in section
    assert "Estimate Rationale" in section
    assert "Confidence" in section


def test_build_prototype_relationship_section_has_big_prototype_addendum() -> None:
    section = _build_roadmap_relationship_section()

    assert "Layer 2" in section
    assert "Layer 3" in section
    assert "lower confidence" in section
    assert "raises confidence per ticket" in section


def test_prototype_orchestrator_p33_dispatch_requests_three_estimate_fields() -> None:
    section = _orchestrator_p33_section()

    assert "story_point_estimate" in section
    assert "estimate_rationale" in section
    assert "confidence" in section


def test_prototype_orchestrator_p33_rationale_must_cite_evidence() -> None:
    section = _orchestrator_p33_section()

    assert "estimate_rationale" in section
    assert (
        "dossier/evidence/" in section
        or "dossier/risk-profile.md" in section
        or "dossier/challenges.md" in section
    )


def test_prototype_orchestrator_p4_dispatch_passes_estimate_to_jira_default() -> None:
    section = _orchestrator_p4_section()

    assert "story_point_estimate" in section
    assert "customfield_10016" in section


def test_prototype_orchestrator_p4_dispatch_passes_estimate_to_linear_branch() -> None:
    section = _orchestrator_p4_section()

    assert "story_point_estimate" in section
    assert "linear-operator" in section
    assert "--estimate <int>" in section or "estimate=<int>" in section
