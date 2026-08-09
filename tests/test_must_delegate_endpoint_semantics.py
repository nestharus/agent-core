from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANAGED_ENDPOINTS = {
    "jira-operator": "jira-writes",
    "linear-operator": "linear-writes",
    "worktree-operator": "worktree-mutation",
}
SHELL_BLOCK = re.compile(r"```(?:bash|sh)\n(.*?)```", re.DOTALL)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _execution_boundary(operator_name: str) -> str:
    text = _read(f"agents/{operator_name}.md")
    start = text.index("## Execution Boundary")
    end = text.find("\n## ", start + 1)
    return text[start:] if end == -1 else text[start:end]


def _has_executable_self_dispatch(operator_name: str, source: str) -> bool:
    normalized_blocks = (
        " ".join(block.replace("\\\n", " ").split())
        for block in SHELL_BLOCK.findall(source)
    )
    pattern = re.compile(
        rf"\bagents\b.*?\s-a\s+[^ ]*{re.escape(operator_name)}\.md(?:\s|$)"
    )
    return any(pattern.search(block) for block in normalized_blocks)


def test_authoritative_contracts_define_selected_endpoint_semantics() -> None:
    operator_format = _read("agents/operator-file-format.md")
    routing = _read("workflows/agents-cli.md")

    for value in (
        "`must_delegate:` is a caller-routing boundary",
        "not an instruction that the selected endpoint applies to itself",
        "MUST NOT dispatch another copy of itself for the same operation",
        "different owned concern",
        "visible in process-tree evidence",
    ):
        assert value in operator_format

    for value in (
        "selecting the operator as the execution endpoint",
        "never dispatches the same operator for the same operation",
        "different concern explicitly owned by the endpoint procedure",
        "remain visible in process-tree evidence",
    ):
        assert value in routing


@pytest.mark.parametrize(
    "operator_name, delegated_operation", MANAGED_ENDPOINTS.items()
)
def test_managed_endpoint_executes_without_self_dispatch(
    operator_name: str, delegated_operation: str
) -> None:
    contract = yaml.safe_load(_read(f"contracts/operators/{operator_name}.yaml"))
    boundary = _execution_boundary(operator_name)
    operator = _read(f"agents/{operator_name}.md")

    assert delegated_operation in contract["must_delegate"]
    assert f"`must_delegate: {delegated_operation}` is a caller boundary" in boundary
    assert "Once selected" in boundary
    assert f"must never dispatch `{operator_name}.md`" in boundary
    assert not _has_executable_self_dispatch(operator_name, operator)


def test_self_dispatch_detector_rejects_same_agent_operation_fixture() -> None:
    recursive_fixture = """```bash
agents -a ~/ai/agents/jira-operator.md \\
  --input task=comment \\
  --input issue_key=ACR-316
```"""
    valid_child_fixture = """```bash
agents -a ~/ai/agents/pr-writer.md \\
  --input linear_issue_keys=ACR-316
```"""

    assert _has_executable_self_dispatch("jira-operator", recursive_fixture)
    assert not _has_executable_self_dispatch("jira-operator", valid_child_fixture)
