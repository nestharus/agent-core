"""Structural tests for the NES-234 alignment-cycle bootstrap prelude."""

import re


ORCHESTRATOR_RELATIVE_PATH = "agents/alignment-cycle-orchestrator.md"


def _orchestrator_path(repo_root):
    return repo_root / ORCHESTRATOR_RELATIVE_PATH


def _orchestrator_text(repo_root):
    path = _orchestrator_path(repo_root)
    assert path.exists(), f"missing {ORCHESTRATOR_RELATIVE_PATH}"
    return path.read_text(encoding="utf-8")


def test_alignment_cycle_orchestrator_file_exists(repo_root):
    assert _orchestrator_path(repo_root).exists()


def test_alignment_cycle_orchestrator_documents_empty_state_prelude(repo_root):
    text = _orchestrator_text(repo_root)

    assert "problem-bootstrap" in text
    assert "philosophy-bootstrap" in text
    assert re.search(
        r"empty-state|if\s+`?problem\.md`?\s+does\s+not\s+exist|before\s+Stage\s+1",
        text,
        re.I,
    )


def test_alignment_cycle_orchestrator_references_real_integrator_filenames(repo_root):
    text = _orchestrator_text(repo_root)

    assert text.count("problem-expansion-integrate.md") >= 2
    assert text.count("philosophy-expansion-integrate.md") >= 2


def test_alignment_cycle_orchestrator_omits_stale_integrator_filenames(repo_root):
    text = _orchestrator_text(repo_root)

    assert not re.search(r"(?<![\w-])problem-expansion\.md(?![\w-])", text)
    assert not re.search(r"(?<![\w-])philosophy-expansion\.md(?![\w-])", text)


def test_alignment_cycle_orchestrator_preserves_stage_dispatch_anchors(repo_root):
    text = _orchestrator_text(repo_root)

    for anchor in (
        "### Stage 1: Problem Alignment Review",
        "### Stage 1b: Problem Expansion (split: classify",
        "#### Stage 1b-classify",
        "#### Stage 1b-integrate",
        "### Stage 2: Philosophy Alignment Review",
        "### Stage 2b: Philosophy Expansion (split: classify",
        "#### Stage 2b-classify",
        "#### Stage 2b-integrate",
    ):
        assert anchor in text
