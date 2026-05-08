from pathlib import Path

from clients.linear.client import ROUTINE_MANAGER_OWNED_STATES


REPO_ROOT = Path(__file__).resolve().parents[3]
USAGE = REPO_ROOT / "clients" / "linear" / "USAGE.yml"


def _usage_text() -> str:
    return USAGE.read_text(encoding="utf-8")


def test_acr113_usage_documents_live_python_cli_commands() -> None:
    """T14: USAGE.yml must describe the live clients.linear.cli command surface."""
    text = _usage_text()

    assert "PYTHONPATH=$HOME/ai python3 -m clients.linear.cli" in text
    for command in [
        "create-issue",
        "search-issues",
        "list-issues",
        "list-projects",
        "list-labels",
        "apply-labels",
        "get-issue",
    ]:
        assert command in text


def test_acr113_usage_pins_project_and_per_team_label_route() -> None:
    """T14: examples mention team, project UUID-or-slugId, and singular --label."""
    text = _usage_text()

    assert "--team" in text
    assert "--project" in text
    assert "--label" in text
    assert "slugId" in text or "slug-or-id" in text or "UUID or slug" in text
    assert "per-team" in text or "selected team" in text or "team-scoped" in text


def test_acr113_usage_rejects_stale_linear_wrapper_references() -> None:
    """T14: stale scripts/TypeScript guidance must not remain live contract text."""
    text = _usage_text()

    forbidden = [
        "scripts/clients/linear",
        "scripts/clients/linear_client.py",
        "@linear/sdk",
        "uv run linear",
        "first page only",
    ]
    for token in forbidden:
        assert token not in text


def test_acr130_usage_documents_transition_issue_command_and_flag() -> None:
    """ACR-130: USAGE.yml mirrors the manager-owned Linear transition command."""
    text = _usage_text()

    assert "transition-issue" in text
    assert "--target-status" in text
    assert "Manager-owned routine status transition" in text
    assert "ACR-130" in text


def test_acr130_usage_transition_routine_states_match_client_constant() -> None:
    """ACR-130: documented routine states stay locked to the client constant."""
    text = _usage_text()
    transition_index = text.find("transition_issue:")
    assert transition_index != -1, "usage must include transition_issue"
    routine_states_index = text.find("routine_states:", transition_index)
    assert routine_states_index != -1, "transition usage must include routine_states"

    following = text[routine_states_index:].splitlines()[1:]
    documented_states = []
    for line in following:
        if not line.startswith(" ") or (
            documented_states and line.strip() and not line.lstrip().startswith("- ")
        ):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            documented_states.append(stripped[2:].strip().strip('"'))

    assert set(documented_states) == set(ROUTINE_MANAGER_OWNED_STATES)
    assert len(documented_states) == len(ROUTINE_MANAGER_OWNED_STATES)
