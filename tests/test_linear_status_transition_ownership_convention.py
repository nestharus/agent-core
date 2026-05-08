import re
from pathlib import Path

from clients.linear.client import ROUTINE_MANAGER_OWNED_STATES


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_WINDOW_LINES = 3

SCAN_FILES = (
    REPO_ROOT / "agents" / "linear-operator.md",
    REPO_ROOT / "agents" / "work-manager-operator.md",
    REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md",
    REPO_ROOT / "workflows" / "implementation-pipeline.md",
    REPO_ROOT / "agents" / "prototype-orchestrator.md",
    REPO_ROOT / "agents" / "release-orchestrator.md",
)

ALLOWED_USER_OWNED_LINE_RANGES = {
    REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md": (
        range(74, 75),
        range(133, 134),
        range(135, 136),
    ),
}

STATUS_CONTEXT_TOKENS = (
    "status",
    "transition",
    "state",
    "lifecycle",
    "Linear",
    "Linear/",
    *tuple(ROUTINE_MANAGER_OWNED_STATES),
)

STALE_PHRASE_INVENTORY = {
    REPO_ROOT / "agents" / "linear-operator.md": (
        "Status transitions are user-owned",
        "Not exposed (user-owned)",
    ),
    REPO_ROOT / "workflows" / "implementation-pipeline.md": (
        "Status transitions remain user-owned regardless of ticket system",
        "Status transitions remain user-owned",
    ),
    REPO_ROOT / "agents" / "work-manager-operator.md": (
        "status changes are user-owned",
        "The Linear path intentionally omits status transitions",
        "status transitions are user-owned",
        "do not present Linear state changes as pipeline-owned",
        "rely on user-owned status changes",
        "do not force status from the manager seat",
        "Any Linear status placement remains user-owned",
        "Linear status transitions are user-owned",
    ),
    REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md": (
        "status changes are user-owned",
        "The Linear path intentionally omits status transitions",
        "status transitions are user-owned",
        "Do NOT transition the ticket status from this orchestrator",
    ),
    REPO_ROOT / "agents" / "prototype-orchestrator.md": (
        "Do not transition the deferring WU's status",
        "Do not transition the deferring WU's status - that's user-owned",
        "Do not transition the deferring WU's status \u2014 that's user-owned",
    ),
    REPO_ROOT / "agents" / "release-orchestrator.md": (
        "lifecycle state changes remain user-owned",
        "lifecycle state changes remain user-owned unless a future release workflow changes that contract",
    ),
}


def _allowed_user_owned_hit(path: Path, line_number: int) -> bool:
    return any(
        line_number in allowed_range
        for allowed_range in ALLOWED_USER_OWNED_LINE_RANGES.get(path, ())
    )


def _user_owned_status_context_violations(
    path: Path,
    text: str,
) -> list[str]:
    lines = text.splitlines()
    violations = []
    for index, line in enumerate(lines):
        line_number = index + 1
        if "user-owned" not in line.lower():
            continue
        if _allowed_user_owned_hit(path, line_number):
            continue

        start = max(0, index - CONTEXT_WINDOW_LINES)
        end = min(len(lines), index + CONTEXT_WINDOW_LINES + 1)
        snippet = "\n".join(lines[start:end])
        for token in STATUS_CONTEXT_TOKENS:
            escaped = re.escape(token)
            # Alphabetic tokens need word boundaries to avoid substring matches.
            # Tokens with punctuation, such as "Linear/", are matched exactly.
            pattern = (
                rf"\b{escaped}\b" if token.replace(" ", "").isalpha() else escaped
            )
            if re.search(pattern, snippet, flags=re.IGNORECASE):
                violations.append(
                    f"{path}:{line_number} matched {token!r} in context:\n{snippet}"
                )
                break
    return violations


def test_user_owned_status_transition_context_is_not_allowed() -> None:
    violations = []
    for path in SCAN_FILES:
        violations.extend(
            _user_owned_status_context_violations(
                path,
                path.read_text(encoding="utf-8"),
            )
        )

    assert violations == []


def test_stale_status_transition_phrases_are_absent() -> None:
    violations = []
    for path, phrases in STALE_PHRASE_INVENTORY.items():
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase in text:
                line_number = text[: text.index(phrase)].count("\n") + 1
                violations.append(f"{path}:{line_number} still contains {phrase!r}")

    assert violations == []


def test_user_owned_context_regression_cases() -> None:
    virtual_path = REPO_ROOT / "agents" / "virtual.md"

    assert _user_owned_status_context_violations(
        virtual_path,
        "Linear lifecycle changes are user-owned",
    )
    assert _user_owned_status_context_violations(
        virtual_path,
        "issue state mutation is user-owned for Linear",
    )
    assert (
        _user_owned_status_context_violations(
            virtual_path,
            "the user is responsible for scope decisions",
        )
        == []
    )
