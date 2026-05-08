import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ClaimRecord:
    path: Path
    line_number: int
    operator: str
    claimed_model: str
    excerpt: str


@dataclass(frozen=True)
class Mismatch:
    claim: ClaimRecord
    frontmatter_model: str


def _frontmatter_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:index]
    return []


def _unquote_frontmatter_value(value: str) -> str:
    cleaned = value.strip().split(" #", 1)[0].strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1].strip()
    return cleaned


def _agent_frontmatter_models(repo_root: Path) -> dict[str, str]:
    """Return {operator_stem: model_value} for modeled agents/*.md files."""
    models: dict[str, str] = {}
    for path in sorted((repo_root / "agents").glob("*.md")):
        for line in _frontmatter_lines(path.read_text(encoding="utf-8")):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            match = re.match(r"^model:\s*(.*?)\s*$", stripped)
            if match is None:
                continue
            model = _unquote_frontmatter_value(match.group(1))
            if model and model.lower() != "n/a":
                models[path.stem] = model
            break
    return models


def _workflow_dispatch_orchestrator(text: str) -> str | None:
    """Return workflow_dispatch_contract.orchestrator from YAML frontmatter."""
    in_contract = False
    contract_indent = 0
    for raw_line in _frontmatter_lines(text):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if not in_contract:
            if stripped == "workflow_dispatch_contract:":
                in_contract = True
                contract_indent = indent
            continue
        if indent <= contract_indent:
            return None
        match = re.match(r"^orchestrator:\s*(.*?)\s*$", stripped)
        if match is None:
            continue
        orchestrator = _unquote_frontmatter_value(match.group(1))
        return orchestrator or None
    return None


def _model_pattern(known_models: set[str]) -> str:
    ordered = sorted(known_models, key=len, reverse=True)
    return "|".join(re.escape(model) for model in ordered)


def _operator_pattern(known_operators: set[str]) -> str:
    ordered = sorted(known_operators, key=len, reverse=True)
    return "|".join(re.escape(operator) for operator in ordered)


def _line_is_fence(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _iter_operator_model_claims(
    path: Path,
    text: str,
    workflow_orchestrator: str | None,
    known_operators: set[str],
    known_models: set[str],
) -> Iterable[ClaimRecord]:
    """Yield explicit operator-model claims outside fenced code blocks."""
    if not known_operators or not known_models:
        return

    operator_names = _operator_pattern(known_operators)
    model_names = _model_pattern(known_models)
    inline_claim = re.compile(
        rf"(?<![A-Za-z0-9_-])`?(?P<operator>{operator_names})`?"
        rf"(?:\]\([^)]+\))?\s*\(\s*`?(?P<model>{model_names})`?\s*\)"
        rf"(?![A-Za-z0-9_-])"
    )
    path_claim = re.compile(
        rf"agents/(?P<operator>[A-Za-z0-9_-]+)\.md\b.*?"
        rf"\bModel:\s*`?(?P<model>{model_names})`?"
    )
    table_claim = re.compile(
        rf"\|\s*`?(?P<operator>{operator_names})`?\s*\|"
        rf"\s*`?(?P<model>{model_names})`?\s*\|"
    )
    orchestrator_claim = re.compile(
        rf"\*\*Orchestrator\*\*\s*\(\s*`?(?P<model>{model_names})`?\s*\)"
    )

    in_fence = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _line_is_fence(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        emitted: set[tuple[str, str]] = set()
        excerpt = line.strip()

        for pattern in (path_claim, inline_claim, table_claim):
            for match in pattern.finditer(line):
                operator = match.group("operator")
                model = match.group("model")
                if operator not in known_operators:
                    continue
                key = (operator, model)
                if key in emitted:
                    continue
                emitted.add(key)
                yield ClaimRecord(path, line_number, operator, model, excerpt)

        if workflow_orchestrator not in known_operators:
            continue
        for match in orchestrator_claim.finditer(line):
            model = match.group("model")
            key = (workflow_orchestrator, model)
            if key in emitted:
                continue
            emitted.add(key)
            yield ClaimRecord(path, line_number, workflow_orchestrator, model, excerpt)


def _relative_path(path: Path) -> str:
    if path.is_absolute():
        try:
            return path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def _claim_mismatches(
    claims: Iterable[ClaimRecord],
    frontmatter_models: dict[str, str],
) -> list[Mismatch]:
    mismatches: list[Mismatch] = []
    for claim in claims:
        expected = frontmatter_models.get(claim.operator)
        if expected is not None and claim.claimed_model != expected:
            mismatches.append(Mismatch(claim, expected))
    return mismatches


def _format_mismatches(mismatches: list[Mismatch]) -> str:
    """Render all operator-model claim drifts as one failure block."""
    lines = ["operator model claim drift:"]
    for mismatch in mismatches:
        claim = mismatch.claim
        lines.append(
            f"- {_relative_path(claim.path)}:{claim.line_number}: "
            f"{claim.operator} claims {claim.claimed_model}, but "
            f"agents/{claim.operator}.md frontmatter is {mismatch.frontmatter_model}"
        )
        lines.append(f"  line: {claim.excerpt}")
    return "\n".join(lines)


def test_workflow_and_convention_operator_model_claims_match_frontmatter():
    frontmatter_models = _agent_frontmatter_models(REPO_ROOT)
    known_operators = set(frontmatter_models)
    known_models = set(frontmatter_models.values()) | {
        "gpt-high",
        "claude-opus",
        "claude-sonnet",
        "claude-haiku",
    }

    all_claims: list[ClaimRecord] = []
    for directory_name in ("workflows", "conventions"):
        for path in sorted((REPO_ROOT / directory_name).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            workflow_orchestrator = (
                _workflow_dispatch_orchestrator(text)
                if directory_name == "workflows"
                else None
            )
            all_claims.extend(
                _iter_operator_model_claims(
                    path,
                    text,
                    workflow_orchestrator,
                    known_operators,
                    known_models,
                )
            )

    mismatches = _claim_mismatches(all_claims, frontmatter_models)
    assert not mismatches, "\n" + _format_mismatches(mismatches)


def test_extractor_flags_workflow_orchestrator_drift_against_frontmatter_fixture():
    fixture = """---
workflow:
  id: roadmap
workflow_dispatch_contract:
  orchestrator: "roadmap-orchestrator"
  inputs:
    - "fixture input"
  expectations:
    - "fixture expectation"
  outputs:
    - "fixture output"
  non_goals:
    - "fixture non-goal"
---
# Fixture Roadmap Workflow

- **Orchestrator** (`gpt-high`): identifies which research questions need answering.
- **Proposer** (`gpt-high`): generic role label, not an operator claim.

```markdown
- **Orchestrator** (`gpt-high`): fenced example must not be enforced.
```
"""
    frontmatter_models = {"roadmap-orchestrator": "claude-opus"}
    known_operators = set(frontmatter_models)
    known_models = set(frontmatter_models.values()) | {"gpt-high", "claude-opus"}
    workflow_orchestrator = _workflow_dispatch_orchestrator(fixture)
    claims = list(
        _iter_operator_model_claims(
            Path("workflows/roadmap.md"),
            fixture,
            workflow_orchestrator,
            known_operators,
            known_models,
        )
    )

    mismatches = _claim_mismatches(claims, frontmatter_models)

    assert len(mismatches) == 1
    assert _format_mismatches(mismatches) == (
        "operator model claim drift:\n"
        "- workflows/roadmap.md:17: roadmap-orchestrator claims gpt-high, "
        "but agents/roadmap-orchestrator.md frontmatter is claude-opus\n"
        "  line: - **Orchestrator** (`gpt-high`): identifies which research "
        "questions need answering."
    )
