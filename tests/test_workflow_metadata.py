from pathlib import Path

from tools.workflow_index.generator import DISPATCH_CONTRACT_KEYS


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / "workflows"


def _workflow_docs():
    return sorted(WORKFLOWS_DIR.glob("*.md"))


# Proposal test-intent item 6 risk: tracked workflow docs skip required
# metadata or use incompatible contract shape; selected level: component
# shape-guard.
def test_all_workflow_docs_have_valid_dispatch_contract():
    from tools.workflow_index.generator import (
        parse_frontmatter,
        validate_dispatch_contract,
    )

    workflow_docs = _workflow_docs()
    assert workflow_docs, f"no workflow docs found under {WORKFLOWS_DIR}"

    for path in workflow_docs:
        parsed = parse_frontmatter(path.read_text(encoding="utf-8"), str(path))

        assert parsed.get("workflow", {}).get("id") == path.stem, (
            f"{path}: workflow.id must match filename stem"
        )
        assert "workflow_dispatch_contract" in parsed, (
            f"{path}: missing workflow_dispatch_contract"
        )
        contract = parsed["workflow_dispatch_contract"]
        assert set(contract) == DISPATCH_CONTRACT_KEYS, (
            f"{path}: workflow_dispatch_contract must have exactly "
            f"{sorted(DISPATCH_CONTRACT_KEYS)}"
        )
        assert isinstance(contract["orchestrator"], str), (
            f"{path}: orchestrator must be a string"
        )
        assert contract["orchestrator"].strip(), (
            f"{path}: orchestrator must be non-empty"
        )
        for key in ("inputs", "expectations", "outputs", "non_goals"):
            assert isinstance(contract[key], list), f"{path}: {key} must be a list"
            assert contract[key], f"{path}: {key} must be non-empty"
            assert all(isinstance(item, str) and item for item in contract[key]), (
                f"{path}: {key} must contain only non-empty strings"
            )
        validate_dispatch_contract(contract, str(path))


# Proposal test-intent item 6 and assumption-register entry 2 risk:
# unevidenced aliases or empty alias blocks get shipped; selected level:
# component shape-guard.
def test_workflow_docs_omit_aliases_until_evidenced():
    from tools.workflow_index.generator import parse_frontmatter

    for path in _workflow_docs():
        parsed = parse_frontmatter(path.read_text(encoding="utf-8"), str(path))

        assert "workflow_aliases" not in parsed, (
            f"{path}: omit workflow_aliases until there is concrete alias evidence"
        )


# Proposal test-intent item 5 risk: checked-in generated index is stale;
# selected level: component shape-guard.
def test_workflow_index_is_current():
    from tools.workflow_index.generator import check_index

    matches, diff_text = check_index(WORKFLOWS_DIR, WORKFLOWS_DIR / "index.json")

    assert matches is True, (
        "workflow index is stale; run "
        "`python3 -m tools.workflow_index generate`.\n"
        f"{diff_text}"
    )


# Proposal test-intent item 7 risk: the generator lands but is not
# discoverable from the tool catalog; selected level: unit.
def test_workflow_index_tool_is_discoverable():
    underscore_readme = REPO_ROOT / "tools" / "workflow_index" / "README.md"
    hyphen_readme = REPO_ROOT / "tools" / "workflow-index" / "README.md"
    tools_readme = REPO_ROOT / "tools" / "README.md"

    assert underscore_readme.exists() or hyphen_readme.exists(), (
        "missing workflow-index tool README"
    )
    assert tools_readme.exists(), f"missing tools catalog: {tools_readme}"

    catalog_text = tools_readme.read_text(encoding="utf-8")
    assert "workflow_index" in catalog_text or "workflow-index" in catalog_text
