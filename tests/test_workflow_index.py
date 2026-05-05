import json
from pathlib import Path

import pytest


VALID_CONTRACT = {
    "orchestrator": "implementation-pipeline-orchestrator",
    "inputs": ["ticket id"],
    "expectations": ["runs the workflow"],
    "outputs": ["planning artifacts"],
    "non_goals": ["does not skip phases"],
}


def _workflow_doc(workflow_id, contract=None, aliases=None):
    lines = [
        "---",
        "workflow:",
        f"  id: {workflow_id}",
        "workflow_dispatch_contract:",
        f"  orchestrator: \"{(contract or VALID_CONTRACT)['orchestrator']}\"",
        "  inputs:",
    ]
    for value in (contract or VALID_CONTRACT)["inputs"]:
        lines.append(f"    - \"{value}\"")
    lines.append("  expectations:")
    for value in (contract or VALID_CONTRACT)["expectations"]:
        lines.append(f"    - \"{value}\"")
    lines.append("  outputs:")
    for value in (contract or VALID_CONTRACT)["outputs"]:
        lines.append(f"    - \"{value}\"")
    lines.append("  non_goals:")
    for value in (contract or VALID_CONTRACT)["non_goals"]:
        lines.append(f"    - \"{value}\"")
    if aliases:
        lines.append("workflow_aliases:")
        for alias in aliases:
            lines.append(f"  - alias: \"{alias['alias']}\"")
            lines.append("    target:")
            target = alias["target"]
            lines.append(f"      workflow_id: {target['workflow_id']}")
            lines.append(f"      path: \"{target['path']}\"")
            if "anchor" in target:
                lines.append(f"      anchor: \"{target['anchor']}\"")
            if "phase" in target:
                lines.append(f"      phase: \"{target['phase']}\"")
    lines.extend(["---", f"# {workflow_id}", "", "Body."])
    return "\n".join(lines) + "\n"


def _valid_alias(**overrides):
    alias = {
        "alias": "RCA Workflow",
        "target": {
            "workflow_id": "implementation-pipeline",
            "path": "workflows/implementation-pipeline.md",
        },
    }
    alias.update(overrides)
    return alias


def _assert_sorted_mapping_keys(value):
    if isinstance(value, dict):
        assert list(value) == sorted(value), f"mapping keys are not sorted: {value}"
        for nested in value.values():
            _assert_sorted_mapping_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_sorted_mapping_keys(nested)


# Proposal test-intent item 1 risk: malformed frontmatter breaks generation;
# selected level: unit.
def test_frontmatter_parser_accepts_valid_blocks():
    from tools.workflow_index.generator import parse_frontmatter

    text = _workflow_doc("implementation-pipeline")

    parsed = parse_frontmatter(text, "workflows/implementation-pipeline.md")

    assert parsed == {
        "workflow": {"id": "implementation-pipeline"},
        "workflow_dispatch_contract": VALID_CONTRACT,
    }


# Proposal test-intent item 1 risk: malformed frontmatter reports are not
# file-specific enough to act on; selected level: unit.
@pytest.mark.parametrize(
    "text",
    [
        "---\nworkflow:\n  id: implementation-pipeline\n# no closing marker\n",
        "---\nworkflow: [\n---\n# Title\n",
        "# Title\n\nNo frontmatter.\n",
    ],
    ids=["missing-closing-delimiter", "invalid-yaml", "no-frontmatter"],
)
def test_frontmatter_parser_reports_invalid_blocks_with_path(text):
    from tools.workflow_index.generator import parse_frontmatter

    source_path = "workflows/broken.md"

    with pytest.raises(ValueError) as excinfo:
        parse_frontmatter(text, source_path)

    assert source_path in str(excinfo.value)


# Proposal test-intent item 2 risk: ad hoc or incomplete dispatch-contract
# keys create incompatible index data; selected level: unit.
@pytest.mark.parametrize(
    ("contract", "accepted"),
    [
        ({**VALID_CONTRACT, "extra": ["not allowed"]}, False),
        (
            {
                key: value
                for key, value in VALID_CONTRACT.items()
                if key != "outputs"
            },
            False,
        ),
        ({**VALID_CONTRACT, "inputs": "ticket id"}, False),
        (VALID_CONTRACT, True),
    ],
    ids=["extra-key", "missing-key", "non-list-value", "valid-contract"],
)
def test_dispatch_contract_fixed_key_set(contract, accepted):
    from tools.workflow_index.generator import validate_dispatch_contract

    if accepted:
        validate_dispatch_contract(contract, "workflows/example.md")
    else:
        with pytest.raises(ValueError):
            validate_dispatch_contract(contract, "workflows/example.md")


# Proposal test-intent item 3 risk: future alias declarations drift from B1;
# selected level: unit.
@pytest.mark.parametrize(
    ("aliases", "accepted"),
    [
        ([_valid_alias()], True),
        ([_valid_alias(target={"path": "workflows/implementation-pipeline.md"})], False),
        (
            [
                _valid_alias(alias="RCA Workflow"),
                _valid_alias(alias="rca workflow!"),
            ],
            False,
        ),
        (
            [
                _valid_alias(
                    alias="RCA Workflow",
                    target={
                        "workflow_id": "implementation-pipeline",
                        "path": "workflows/implementation-pipeline.md",
                        "phase": "Phase 0",
                    },
                ),
                _valid_alias(
                    alias="rca workflow!",
                    target={
                        "workflow_id": "implementation-pipeline",
                        "path": "workflows/implementation-pipeline.md",
                        "phase": "Phase 2.5",
                    },
                ),
            ],
            True,
        ),
        (
            [
                _valid_alias(
                    disambiguation=[
                        {
                            "context": (
                                "The user is asking about a defect or regression."
                            ),
                            "preferred_target": {
                                "workflow_id": "implementation-pipeline",
                                "path": "workflows/implementation-pipeline.md",
                                "phase": "Phase 0",
                            },
                            "competing_targets": [
                                {
                                    "workflow_id": "risk-reduction",
                                    "path": "workflows/risk-reduction.md",
                                }
                            ],
                            "fallback_question": (
                                "Do you mean RCA inside the implementation "
                                "pipeline or risk reduction?"
                            ),
                        }
                    ]
                )
            ],
            True,
        ),
    ],
    ids=[
        "valid-alias",
        "missing-target-workflow-id",
        "duplicate-normalized-alias",
        "duplicate-distinguished-by-phase",
        "valid-disambiguation-record",
    ],
)
def test_alias_schema_fixture_validates_b1_shape(aliases, accepted):
    from tools.workflow_index.generator import validate_aliases

    if accepted:
        validate_aliases(aliases, "workflows/example.md")
    else:
        with pytest.raises(ValueError):
            validate_aliases(aliases, "workflows/example.md")


# Derived from contract § E and proposal test-intent item 3 risk: alias lookup
# semantics drift into stemming, synonyms, or punctuation-sensitive matching;
# selected level: unit.
@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("RCA Workflow", "rca workflow"),
        ("  RCA Workflow!  ", "rca workflow"),
        ("workflow,routing", "workflow routing"),
        ("foo  bar", "foo bar"),
    ],
)
def test_alias_normalization(raw, normalized):
    from tools.workflow_index.generator import normalize_alias

    assert normalize_alias(raw) == normalized
    assert normalize_alias("workflows") != normalize_alias("workflow")


# Proposal test-intent item 4 risk: nondeterministic output causes noisy diffs
# and stale-index ambiguity; selected level: unit.
def test_index_generation_is_deterministic(tmp_path):
    from tools.workflow_index.generator import build_index, serialize_index

    workflows_dir = tmp_path / "plain" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "bravo.md").write_text(_workflow_doc("bravo"), encoding="utf-8")
    (workflows_dir / "alpha.md").write_text(_workflow_doc("alpha"), encoding="utf-8")

    first = serialize_index(build_index(workflows_dir))
    second = serialize_index(build_index(workflows_dir))

    assert first == second
    plain_index = json.loads(first)
    _assert_sorted_mapping_keys(plain_index)
    assert plain_index["aliases"] == []

    aliased_dir = tmp_path / "aliased" / "workflows"
    aliased_dir.mkdir(parents=True)
    (aliased_dir / "zulu.md").write_text(
        _workflow_doc(
            "zulu",
            aliases=[
                {
                    "alias": "Zulu Flow",
                    "target": {
                        "workflow_id": "zulu",
                        "path": "workflows/zulu.md",
                    },
                }
            ],
        ),
        encoding="utf-8",
    )
    (aliased_dir / "alpha.md").write_text(
        _workflow_doc(
            "alpha",
            aliases=[
                {
                    "alias": "Alpha Flow",
                    "target": {
                        "workflow_id": "alpha",
                        "path": "workflows/alpha.md",
                    },
                }
            ],
        ),
        encoding="utf-8",
    )

    aliased_index = json.loads(serialize_index(build_index(aliased_dir)))

    assert aliased_index["aliases"] == sorted(
        aliased_index["aliases"],
        key=lambda item: (item["workflow_id"], item["normalized_alias"]),
    )


# Proposal test-intent item 5 risk: authors forget to regenerate
# workflows/index.json; selected level: component.
def test_check_mode_passes_for_current_output_and_fails_for_stale_output(tmp_path):
    from tools.workflow_index.generator import check_index, write_index

    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    output = workflows_dir / "index.json"
    (workflows_dir / "alpha.md").write_text(_workflow_doc("alpha"), encoding="utf-8")
    (workflows_dir / "bravo.md").write_text(_workflow_doc("bravo"), encoding="utf-8")

    write_index(workflows_dir, output)

    matches, diff_text = check_index(workflows_dir, output)
    assert matches is True
    assert diff_text == ""

    stale_index = json.loads(output.read_text(encoding="utf-8"))
    stale_index["workflows"]["alpha"]["path"] = "workflows/stale.md"
    output.write_text(json.dumps(stale_index, indent=2, sort_keys=True) + "\n")

    matches, diff_text = check_index(workflows_dir, output)
    assert matches is False
    assert diff_text
