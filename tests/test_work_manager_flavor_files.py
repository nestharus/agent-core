from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

MAX_FLAVOR = REPO_ROOT / "agents/work-manager-operator-max.md"
PRAGMATIC_FLAVOR = REPO_ROOT / "agents/work-manager-operator-pragmatic.md"
HACKERMAN_FLAVOR = REPO_ROOT / "agents/work-manager-operator-hackerman.md"
OVERVIEW = REPO_ROOT / "agents/work-manager-operator.md"

FLAVOR_PATHS = (MAX_FLAVOR, PRAGMATIC_FLAVOR, HACKERMAN_FLAVOR)
MIN_CANONICAL_SHAPES = 15


def test_each_flavor_file_exists():
    assert MAX_FLAVOR.exists()
    assert PRAGMATIC_FLAVOR.exists()
    assert HACKERMAN_FLAVOR.exists()


def test_each_flavor_file_declares_its_identity():
    max_content = MAX_FLAVOR.read_text(encoding="utf-8")
    pragmatic_content = PRAGMATIC_FLAVOR.read_text(encoding="utf-8")
    hackerman_content = HACKERMAN_FLAVOR.read_text(encoding="utf-8")

    assert "manager-max" in max_content
    assert "manager-pragmatic" in pragmatic_content
    assert "manager-hackerman" in hackerman_content


def test_each_flavor_file_cross_references_other_flavors():
    for flavor_path in FLAVOR_PATHS:
        content = flavor_path.read_text(encoding="utf-8")

        assert "manager-max" in content
        assert "manager-pragmatic" in content
        assert "manager-hackerman" in content


def test_max_mode_rules_present_in_max_file():
    content = MAX_FLAVOR.read_text(encoding="utf-8")

    assert "Always choose the answer that carries the LEAST risk" in content
    assert "NEVER choose a shortcut" in content
    assert "NEVER prioritize speed over accuracy" in content
    assert "NEVER introduce additional risk" in content
    assert "When in doubt, default to the more conservative option" in content


def test_each_flavor_file_declares_acceptable_shortcuts():
    max_content = MAX_FLAVOR.read_text(encoding="utf-8")
    pragmatic_content = PRAGMATIC_FLAVOR.read_text(encoding="utf-8")
    hackerman_content = HACKERMAN_FLAVOR.read_text(encoding="utf-8")

    assert "Acceptable shortcuts: NONE" in max_content
    assert "Acceptable shortcuts" in pragmatic_content
    assert "Acceptable shortcuts" in hackerman_content


def test_each_flavor_file_declares_uncertainty_halt():
    for flavor_path in FLAVOR_PATHS:
        content = flavor_path.read_text(encoding="utf-8")

        assert "halt and ask the user" in content
        assert "not pre-enumerated" in content


def test_each_flavor_file_declares_first_read_last_authority():
    for flavor_path in FLAVOR_PATHS:
        content = flavor_path.read_text(encoding="utf-8")

        assert "first-read" in content or "loads this file at session start" in content
        assert "last-authority" in content or "this file wins" in content


def test_each_flavor_file_has_canonical_needs_input_table():
    canonical_shapes = (
        "Phase 4 code-quality HIGH",
        "Phase 4 code-quality MEDIUM with stable disposition",
        "Phase 4 scope-risk MEDIUM",
        "Phase 4 shortcut-risk MEDIUM",
        "Phase 4 supported-surface MEDIUM-with-Continue",
        "Phase 6 code-quality HIGH oscillation",
        "Phase 6 alignment NEEDS_REVISION",
        "Phase 6 prototype-risk HIGH",
        "Phase 6 derivation multi-layer violation",
        "Phase 7 CodeRabbit non-trivial advisory",
        "Phase 8 PR-review test-audit FAIL",
        "Phase 8 PR-review commit-hygiene split signal",
        "Auto-merge unavailable / merge conflict",
        "Schema-rebuild (Linear/Jira state required)",
        "Process-tree audit",
        "Phase 6 / process-tree-auditor blast-radius MEDIUM/HIGH",
        "cwd-resolution / current-working-directory drift",
    )

    for flavor_path in FLAVOR_PATHS:
        content = flavor_path.read_text(encoding="utf-8")
        matching_shapes = [shape for shape in canonical_shapes if shape in content]
        table_rows = [
            line
            for line in content.splitlines()
            if line.strip().startswith("|")
            and line.strip().endswith("|")
            and line.count("|") >= 3
        ]

        assert len(table_rows) >= MIN_CANONICAL_SHAPES
        assert len(matching_shapes) >= MIN_CANONICAL_SHAPES


def test_each_flavor_file_lists_specific_needs_input_shapes():
    for flavor_path in FLAVOR_PATHS:
        content = flavor_path.read_text(encoding="utf-8")

        assert "blast-radius" in content
        assert "cwd-resolution" in content
        assert "Process-tree audit" in content
        assert "blocking" in content
        assert "Phase 8 PR-review test-audit FAIL" in content
        assert "Auto-merge unavailable / merge conflict" in content


def test_overview_file_lists_three_flavors():
    content = OVERVIEW.read_text(encoding="utf-8")

    assert "work-manager-operator-max.md" in content
    assert "work-manager-operator-pragmatic.md" in content
    assert "work-manager-operator-hackerman.md" in content
