import re
from pathlib import Path


def _implicit_flavor_drift_block(content: str) -> str:
    match = re.search(
        r"(?ms)^### 5b\. Implicit manager-flavor drift$(.*?)(^### |\Z)",
        content,
    )
    assert match, "implicit manager-flavor drift block is missing"
    return match.group(1)


def test_workflow_execution_violations_records_implicit_manager_flavor_drift():
    content = Path("conventions/workflow-execution-violations.md").read_text(
        encoding="utf-8"
    )
    block = _implicit_flavor_drift_block(content)

    assert "Manager-layer answer selection" in block


def test_workflow_execution_violations_resolution_cites_manager_max_default():
    content = Path("conventions/workflow-execution-violations.md").read_text(
        encoding="utf-8"
    )
    block = _implicit_flavor_drift_block(content)

    assert "manager-max" in block
    assert re.search(r"(?i)\bdefault\b", block)


def test_workflow_execution_violations_canonical_example_cites_manager_hackerman():
    content = Path("conventions/workflow-execution-violations.md").read_text(
        encoding="utf-8"
    )
    block = _implicit_flavor_drift_block(content)

    assert "manager-hackerman" in block
    assert "work-manager-operator-hackerman.md" in block
