import re
from pathlib import Path


def _quick_activation_section(content: str) -> str:
    match = re.search(r"(?m)^## Quick Activation[^\n]*\n([\s\S]*?)(?=^## |\Z)", content)
    assert match, "missing Quick Activation section"
    return match.group(1)


def test_agents_md_routes_manager_flavors():
    content = Path("AGENTS.md").read_text(encoding="utf-8")
    section = _quick_activation_section(content)

    assert "manager-max" in section
    assert "manager-pragmatic" in section
    assert "manager-hackerman" in section


def test_agents_md_defaults_to_manager_max():
    content = Path("AGENTS.md").read_text(encoding="utf-8")
    section = _quick_activation_section(content)

    assert re.search(r"(?i)\bdefaults?\s+to\s+`?manager-max`?", section)


def test_agents_md_instructs_loading_flavor_file_at_session_start():
    content = Path("AGENTS.md").read_text(encoding="utf-8")
    section = _quick_activation_section(content)

    assert "load the file matching the declared flavor" in section


def test_agents_md_references_three_flavor_files():
    content = Path("AGENTS.md").read_text(encoding="utf-8")
    section = _quick_activation_section(content)

    expected_pairs = (
        ("manager-max", "work-manager-operator-max.md"),
        ("manager-pragmatic", "work-manager-operator-pragmatic.md"),
        ("manager-hackerman", "work-manager-operator-hackerman.md"),
    )
    for flavor, flavor_file in expected_pairs:
        assert re.search(
            rf"{re.escape(flavor)}[\s\S]{{0,220}}{re.escape(flavor_file)}",
            section,
        ), f"{flavor} is not linked to {flavor_file} in Quick Activation"
