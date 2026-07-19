"""Generate a deterministic workflow metadata index from Markdown frontmatter."""

from __future__ import annotations

import difflib
import json
import re
import string
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = 1
GENERATED_FROM = "workflows/*.md"
DISPATCH_CONTRACT_KEYS = {
    "orchestrator",
    "inputs",
    "expectations",
    "outputs",
    "non_goals",
}
LIST_CONTRACT_KEYS = ("inputs", "expectations", "outputs", "non_goals")
TARGET_REQUIRED_KEYS = ("workflow_id", "path")
TARGET_OPTIONAL_KEYS = ("anchor", "phase")
DISAMBIGUATION_KEYS = {
    "context",
    "preferred_target",
    "competing_targets",
    "fallback_question",
}


def parse_frontmatter(text: str, source_path: str) -> dict:
    """Parse YAML frontmatter from a Markdown file's text."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        raise ValueError(f"{source_path}: missing opening frontmatter delimiter")

    lines = text.splitlines()
    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        raise ValueError(f"{source_path}: missing closing frontmatter delimiter")

    raw_yaml = "\n".join(lines[1:closing_index])
    try:
        parsed = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        if mark is None:
            raise ValueError(f"{source_path}: invalid YAML frontmatter: {error}") from error
        line = mark.line + 2
        raise ValueError(
            f"{source_path}: invalid YAML frontmatter near line {line}: {error}"
        ) from error

    if not isinstance(parsed, dict):
        raise ValueError(f"{source_path}: frontmatter must be a mapping")
    return parsed


def validate_dispatch_contract(contract: dict, source_path: str) -> None:
    """Validate the fixed workflow dispatch contract key set."""
    if not isinstance(contract, dict):
        raise ValueError(f"{source_path}: workflow_dispatch_contract must be a mapping")

    actual_keys = set(contract)
    if actual_keys != DISPATCH_CONTRACT_KEYS:
        missing = sorted(DISPATCH_CONTRACT_KEYS - actual_keys)
        extra = sorted(actual_keys - DISPATCH_CONTRACT_KEYS)
        parts = []
        if missing:
            parts.append(f"missing keys {missing}")
        if extra:
            parts.append(f"unexpected keys {extra}")
        raise ValueError(
            f"{source_path}: workflow_dispatch_contract has invalid keys: "
            + ", ".join(parts)
        )

    orchestrator = contract["orchestrator"]
    if not isinstance(orchestrator, str) or not orchestrator.strip():
        raise ValueError(
            f"{source_path}: workflow_dispatch_contract.orchestrator "
            "must be a non-empty string"
        )

    for key in LIST_CONTRACT_KEYS:
        value = contract[key]
        if not isinstance(value, list):
            raise ValueError(f"{source_path}: workflow_dispatch_contract.{key} must be a list")
        if not value:
            raise ValueError(
                f"{source_path}: workflow_dispatch_contract.{key} must be non-empty"
            )
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(
                f"{source_path}: workflow_dispatch_contract.{key} must contain "
                "only non-empty strings"
            )


def validate_aliases(aliases: list | None, source_path: str) -> None:
    """Validate optional workflow aliases using the B1 shape."""
    if aliases is None:
        return
    if not isinstance(aliases, list):
        raise ValueError(f"{source_path}: workflow_aliases must be a list")

    seen: dict[str, set[tuple[str | None, str | None]]] = {}
    for index, alias in enumerate(aliases):
        prefix = f"{source_path}: workflow_aliases[{index}]"
        if not isinstance(alias, dict):
            raise ValueError(f"{prefix} must be a mapping")

        alias_text = alias.get("alias")
        if not isinstance(alias_text, str) or not alias_text.strip():
            raise ValueError(f"{prefix}.alias must be a non-empty string")

        target = _validate_target(alias.get("target"), f"{prefix}.target")
        disambiguation = alias.get("disambiguation")
        if disambiguation is not None:
            _validate_disambiguation(disambiguation, f"{prefix}.disambiguation")

        normalized = normalize_alias(alias_text)
        target_key = (target.get("phase"), target.get("anchor"))
        prior_targets = seen.setdefault(normalized, set())
        if target_key in prior_targets:
            raise ValueError(
                f"{prefix}: duplicate normalized alias {normalized!r} without "
                "a distinct target.phase or target.anchor"
            )
        prior_targets.add(target_key)


def normalize_alias(alias: str) -> str:
    """Normalize an alias without stemming, synonym expansion, or fuzzy matching."""
    separators = string.punctuation.translate(str.maketrans("", "", "-_"))
    translation = str.maketrans({character: " " for character in separators})
    value = alias.strip().lower().translate(translation)
    value = value.replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", value).strip()


def build_index(workflows_dir: Path | str) -> dict:
    """Walk workflow Markdown files and project them to the index schema."""
    workflows_dir = Path(workflows_dir)
    workflows: dict[str, dict] = {}
    aliases: list[dict] = []
    global_aliases: dict[str, list[dict]] = {}

    for path in sorted(workflows_dir.glob("*.md"), key=lambda item: item.name):
        source_path = _source_path_for(workflows_dir, path)
        parsed = parse_frontmatter(path.read_text(encoding="utf-8"), source_path)
        workflow = parsed.get("workflow")
        if not isinstance(workflow, dict):
            raise ValueError(f"{source_path}: workflow must be a mapping")

        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ValueError(f"{source_path}: workflow.id must be a non-empty string")
        if workflow_id != path.stem:
            raise ValueError(f"{source_path}: workflow.id must match filename stem")
        if workflow_id in workflows:
            raise ValueError(f"{source_path}: duplicate workflow.id {workflow_id!r}")

        contract = parsed.get("workflow_dispatch_contract")
        validate_dispatch_contract(contract, source_path)
        workflow_aliases = parsed.get("workflow_aliases")
        validate_aliases(workflow_aliases, source_path)

        workflows[workflow_id] = {
            "path": source_path,
            "workflow": {"id": workflow_id},
            "workflow_dispatch_contract": contract,
        }

        for alias in workflow_aliases or []:
            entry = _project_alias(workflow_id, alias)
            aliases.append(entry)
            global_aliases.setdefault(entry["normalized_alias"], []).append(entry)

    for normalized, entries in global_aliases.items():
        workflow_ids = {entry["workflow_id"] for entry in entries}
        if len(workflow_ids) > 1:
            missing = [
                entry["workflow_id"]
                for entry in entries
                if "disambiguation" not in entry
            ]
            if missing:
                raise ValueError(
                    f"{workflows_dir}: normalized alias {normalized!r} is ambiguous "
                    f"across workflows {sorted(workflow_ids)} but "
                    f"{sorted(missing)} lack disambiguation"
                )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_from": GENERATED_FROM,
        "workflows": {
            workflow_id: workflows[workflow_id] for workflow_id in sorted(workflows)
        },
        "aliases": sorted(
            aliases,
            key=lambda item: (item["workflow_id"], item["normalized_alias"]),
        ),
    }


def serialize_index(index: dict) -> str:
    """Serialize the workflow index deterministically."""
    return json.dumps(index, indent=2, sort_keys=True) + "\n"


def write_index(workflows_dir: Path, output: Path) -> None:
    """Build and write the workflow index."""
    rendered = serialize_index(build_index(workflows_dir))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def check_index(workflows_dir: Path, output: Path) -> tuple[bool, str]:
    """Return whether regenerated output matches the checked-in index.

    The message is a unified diff when the index exists and a plain error when
    the checked-in index is missing.
    """
    expected = serialize_index(build_index(workflows_dir))
    output = Path(output)
    try:
        actual = output.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, f"{output}: missing index file"

    actual = actual.rstrip("\n") + "\n"
    if actual == expected:
        return True, ""

    diff = difflib.unified_diff(
        actual.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile=str(output),
        tofile="regenerated workflow index",
    )
    return False, "".join(diff)


def _validate_target(target: Any, source_path: str) -> dict:
    if not isinstance(target, dict):
        raise ValueError(f"{source_path} must be a mapping")
    for key in TARGET_REQUIRED_KEYS:
        value = target.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{source_path}.{key} must be a non-empty string")
    allowed_keys = set(TARGET_REQUIRED_KEYS) | set(TARGET_OPTIONAL_KEYS)
    extra_keys = set(target) - allowed_keys
    if extra_keys:
        raise ValueError(f"{source_path} has unexpected keys {sorted(extra_keys)}")
    for key in TARGET_OPTIONAL_KEYS:
        if key in target and (
            not isinstance(target[key], str) or not target[key].strip()
        ):
            raise ValueError(f"{source_path}.{key} must be a non-empty string")
    return target


def _validate_disambiguation(disambiguation: Any, source_path: str) -> None:
    if not isinstance(disambiguation, list) or not disambiguation:
        raise ValueError(f"{source_path} must be a non-empty list")
    for index, record in enumerate(disambiguation):
        prefix = f"{source_path}[{index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{prefix} must be a mapping")
        actual_keys = set(record)
        if actual_keys != DISAMBIGUATION_KEYS:
            raise ValueError(
                f"{prefix} must have exactly {sorted(DISAMBIGUATION_KEYS)}"
            )
        for key in ("context", "fallback_question"):
            value = record[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{prefix}.{key} must be a non-empty string")
        _validate_target(record["preferred_target"], f"{prefix}.preferred_target")
        competing_targets = record["competing_targets"]
        if not isinstance(competing_targets, list) or not competing_targets:
            raise ValueError(f"{prefix}.competing_targets must be a non-empty list")
        for target_index, target in enumerate(competing_targets):
            _validate_target(target, f"{prefix}.competing_targets[{target_index}]")


def _project_alias(workflow_id: str, alias: dict) -> dict:
    entry = {
        "workflow_id": workflow_id,
        "alias": alias["alias"],
        "normalized_alias": normalize_alias(alias["alias"]),
        "target": dict(alias["target"]),
    }
    if "disambiguation" in alias:
        entry["disambiguation"] = alias["disambiguation"]
    return entry


def _source_path_for(workflows_dir: Path, path: Path) -> str:
    return f"{workflows_dir.name}/{path.name}"
