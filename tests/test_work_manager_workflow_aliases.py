import re
from pathlib import Path


def test_workflow_aliases_contains_three_manager_aliases():
    content = Path("conventions/workflow-aliases.md").read_text(encoding="utf-8")

    assert "manager-max" in content
    assert "manager-pragmatic" in content
    assert "manager-hackerman" in content


def test_workflow_aliases_points_each_alias_to_flavor_file():
    content = Path("conventions/workflow-aliases.md").read_text(encoding="utf-8")

    expected_pairs = (
        ("manager-max", "work-manager-operator-max.md"),
        ("manager-pragmatic", "work-manager-operator-pragmatic.md"),
        ("manager-hackerman", "work-manager-operator-hackerman.md"),
    )
    for alias, flavor_file in expected_pairs:
        assert re.search(
            rf"{re.escape(alias)}[\s\S]{{0,180}}{re.escape(flavor_file)}",
            content,
        ), f"{alias} is not mapped to {flavor_file}"
