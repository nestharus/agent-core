"""Validate and normalize feature successor manifests before route dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


SCHEMA = "feature-route-manifest-v2"
SOURCE_SCHEMA = "feature-successor-envelope-v1"
INLINE_SOURCE_SCHEMA = "feature-inline-route-map-v2"
SUPPORTED_ROUTES = {"implementation-pipeline", "refactoring"}
MANAGER_FLAVORS = {"manager-max", "manager-pragmatic", "manager-hackerman"}
SOURCE_KIND_BACKENDS = {
    "age-255-estimate-clamp-successor-manifest": "linear",
}
SOURCE_BACKEND_INDICATORS = {
    "linear_readback": "linear",
}
ENVELOPE_KEYS = {
    "schema_version",
    "kind",
    "source_ticket",
    "source_proposal",
    "source_refined_estimate",
    "linear_readback",
    "original_disposition",
    "feature_branch",
    "manager_flavor",
    "successors",
    "coverage_summary",
    "handoff",
}
SUCCESSOR_KEYS = {
    "successor_id",
    "title",
    "brief_path",
    "route",
    "estimate",
    "estimate_source",
    "estimate_rationale",
    "depends_on",
    "surfaces",
    "characterization_ids",
    "new_behavior_ids",
    "runtime_proof_ids",
    "ticket_key",
    "ticket_url",
}
SUCCESSOR_REQUIRED_KEYS = {
    "successor_id",
    "title",
    "brief_path",
    "route",
    "depends_on",
    "surfaces",
    "ticket_key",
}
INLINE_RECORD_KEYS = {
    "ticket_id",
    "successor_id",
    "title",
    "brief_path",
    "surfaces",
    "owning_route",
    "depends_on",
    "branch_name",
    "ticket_source",
    "route_payload",
}
TICKET_SOURCE_KEYS = {"jira_issue_key", "linear_issue_key"}
REFACTORING_PAYLOAD_KEYS = {"target_list", "slice_bounds"}
NORMALIZED_MANIFEST_KEYS = {
    "schema",
    "source_schema",
    "feature_id",
    "feature_scope_path",
    "trunk_branch",
    "feature_branch",
    "ticket_system",
    "source_backend",
    "manager_flavor",
    "source_kind",
    "source_path",
    "source_sha256",
    "topological_order",
    "waves",
    "records",
}
HANDOFF_KEYS = {
    "coordinator",
    "feature_branch",
    "fresh_per_ticket_worktrees",
    "fresh_per_ticket_planning_dirs",
    "fresh_per_ticket_scratch_dirs",
    "fresh_owning_workflow_entry",
    "prior_age_255_artifacts_are_context_only",
    "owning_routes",
}
HANDOFF_TRUE_KEYS = {
    "fresh_per_ticket_worktrees",
    "fresh_per_ticket_planning_dirs",
    "fresh_per_ticket_scratch_dirs",
    "fresh_owning_workflow_entry",
    "prior_age_255_artifacts_are_context_only",
}


class RouteManifestError(ValueError):
    """Raised when route data is unsafe or cannot be normalized."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RouteManifestError(f"duplicate key: {key}")
        result[key] = value
    return result


def _nonblank(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RouteManifestError(f"{field} must be a non-blank trimmed string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise RouteManifestError(f"{field} contains a control character")
    return value


def _string_list(value: Any, field: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise RouteManifestError(f"{field} must be a list")
    items = [_nonblank(item, f"{field}[]") for item in value]
    if len(items) != len(set(items)):
        raise RouteManifestError(f"{field} contains duplicate values")
    return items


def _canonical_absolute(value: str | Path, field: str) -> Path:
    raw = str(value)
    path = Path(raw)
    if not path.is_absolute():
        raise RouteManifestError(f"{field} must be absolute")
    if any(part in {".", ".."} for part in raw.split("/")):
        raise RouteManifestError(f"{field} must not contain . or .. components")
    if raw != str(path):
        raise RouteManifestError(f"{field} must use its exact normalized lexical spelling")
    try:
        resolved = path.resolve(strict=False)
    except OSError as exc:
        raise RouteManifestError(f"{field} cannot be resolved: {exc}") from exc
    if str(path) != str(resolved):
        raise RouteManifestError(
            f"{field} lexical path must equal resolve(strict=False); aliases and symlinks are forbidden"
        )
    return resolved


def _absolute_dir(value: str | Path, field: str) -> Path:
    return _canonical_absolute(value, field)


def _brief_path(value: Any, field: str) -> Path:
    path = _canonical_absolute(_nonblank(value, field), field)
    if not path.is_file() or path.stat().st_size == 0:
        raise RouteManifestError(f"{field} must name a readable non-empty absolute file")
    return path


def _slug(ticket_key: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", ticket_key.lower()).strip("-")
    if not slug or slug in {".", ".."} or ".." in slug:
        raise RouteManifestError(f"unsafe derived route slug for {ticket_key!r}")
    return slug


def _branch_is_valid(branch: str) -> bool:
    result = subprocess.run(
        ["git", "check-ref-format", "--branch", branch],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.returncode == 0 and result.stdout.rstrip("\n") == branch


def _short_branch(value: Any, field: str) -> str:
    branch = _nonblank(value, field)
    remote_result = subprocess.run(
        ["git", "remote"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    remote_prefixes = tuple(
        f"{remote}/"
        for remote in remote_result.stdout.splitlines()
        if remote and remote == remote.strip()
    )
    if branch.startswith(
        ("refs/", "remotes/", "origin/", "upstream/") + remote_prefixes
    ):
        raise RouteManifestError(f"{field} must be a short GitHub branch name")
    if not _branch_is_valid(branch):
        raise RouteManifestError(
            f"{field} must pass git check-ref-format --branch without normalization"
        )
    return branch


def _path_under(root: Path, slug: str, field: str) -> str:
    root = _canonical_absolute(root, f"{field} root")
    candidate = root / slug
    resolved = _canonical_absolute(candidate, field)
    if resolved.parent != root or resolved.name != slug:
        raise RouteManifestError(f"unsafe derived {field}")
    return str(resolved)


def _ticket_url_backend(value: Any, field: str) -> str:
    url = _nonblank(value, field)
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise RouteManifestError(f"{field} must be an exact backend https URL")
    hostname = parsed.hostname.lower()
    if hostname == "linear.app":
        return "linear"
    if hostname == "atlassian.net" or hostname.endswith(".atlassian.net"):
        return "jira"
    raise RouteManifestError(f"{field} has an unsupported ticket backend host")


def _validate_source_backend(envelope: dict[str, Any], ticket_system: str) -> None:
    indicators: list[tuple[str, str]] = []
    source_kind = envelope.get("kind")
    source_backend = (
        SOURCE_KIND_BACKENDS.get(source_kind) if isinstance(source_kind, str) else None
    )
    if source_backend is not None:
        indicators.append((f"kind={source_kind}", source_backend))
    for key, backend in SOURCE_BACKEND_INDICATORS.items():
        if key in envelope:
            indicators.append((key, backend))

    successors = envelope.get("successors")
    if isinstance(successors, list):
        for index, row in enumerate(successors):
            if isinstance(row, dict) and "ticket_url" in row:
                field = f"successors[{index}].ticket_url"
                indicators.append((field, _ticket_url_backend(row["ticket_url"], field)))

    mismatches = [
        f"{indicator} requires ticket_system={backend}"
        for indicator, backend in indicators
        if backend != ticket_system
    ]
    if mismatches:
        raise RouteManifestError("source backend mismatch: " + "; ".join(mismatches))


def _ticket_source(
    value: Any, field: str, *, ticket_id: str, ticket_system: str
) -> tuple[dict[str, str], tuple[str, str]]:
    expected_key = "jira_issue_key" if ticket_system == "jira" else "linear_issue_key"
    if not isinstance(value, dict) or set(value) != {expected_key}:
        raise RouteManifestError(
            f"{field} must contain exactly one {expected_key}; feature routes require "
            "an existing backend issue key and do not accept wu_brief_path"
        )
    identity = _nonblank(value[expected_key], f"{field}.{expected_key}")
    if identity != ticket_id:
        raise RouteManifestError(f"{field}.{expected_key} must equal ticket_id")
    return {expected_key: identity}, (expected_key, identity)


def _canonical_payload_json(value: Any, field: str) -> str:
    encoded = _nonblank(value, field)
    try:
        decoded = json.loads(encoded, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as error:
        raise RouteManifestError(f"{field} must be strict JSON: {error}") from error
    if not isinstance(decoded, dict) or not decoded:
        raise RouteManifestError(f"{field} must encode a non-empty JSON mapping")
    canonical = json.dumps(decoded, separators=(",", ":"), sort_keys=True)
    if encoded != canonical:
        raise RouteManifestError(f"{field} must use canonical compact sorted JSON")
    return encoded


def _route_payload(value: Any, field: str, owning_route: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise RouteManifestError(f"{field} must be a mapping")
    if owning_route == "implementation-pipeline":
        if value:
            raise RouteManifestError(f"{field} must be empty for implementation-pipeline")
        return {}
    if set(value) != REFACTORING_PAYLOAD_KEYS:
        raise RouteManifestError(
            f"{field} keys must exactly equal {sorted(REFACTORING_PAYLOAD_KEYS)}"
        )
    return {
        key: _canonical_payload_json(value[key], f"{field}.{key}")
        for key in sorted(REFACTORING_PAYLOAD_KEYS)
    }


def _topological_waves(
    ordered_ticket_keys: list[str], dependencies: dict[str, list[str]]
) -> tuple[list[str], list[dict[str, Any]]]:
    remaining = set(ordered_ticket_keys)
    completed: set[str] = set()
    order: list[str] = []
    waves: list[dict[str, Any]] = []
    while remaining:
        ready = [
            key
            for key in ordered_ticket_keys
            if key in remaining and set(dependencies[key]) <= completed
        ]
        if not ready:
            raise RouteManifestError("successor dependencies contain a cycle")
        waves.append({"index": len(waves), "tickets": ready})
        order.extend(ready)
        completed.update(ready)
        remaining.difference_update(ready)
    return order, waves


def _validate_normalized_output(manifest: dict[str, Any]) -> None:
    if set(manifest) != NORMALIZED_MANIFEST_KEYS:
        raise RouteManifestError("normalized manifest has an invalid closed key set")
    if manifest.get("schema") != SCHEMA:
        raise RouteManifestError("normalized manifest has an invalid schema")
    for field in (
        "source_schema",
        "feature_id",
        "feature_scope_path",
        "trunk_branch",
        "feature_branch",
        "ticket_system",
        "source_backend",
        "manager_flavor",
        "source_kind",
    ):
        _nonblank(manifest.get(field), f"normalized.{field}")
    source_path = manifest.get("source_path")
    if source_path is not None:
        _canonical_absolute(source_path, "normalized.source_path")
    source_sha256 = manifest.get("source_sha256")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise RouteManifestError("normalized.source_sha256 must be a lowercase SHA-256")
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        raise RouteManifestError("normalized manifest records must be non-empty")
    if any(not isinstance(row, dict) or set(row) != INLINE_RECORD_KEYS | {
        "route_worktree_path",
        "route_planning_dir",
        "route_scratch_dir",
    } for row in records):
        raise RouteManifestError("normalized record has an invalid closed key set")
    ordered = manifest.get("topological_order")
    waves = manifest.get("waves")
    if not isinstance(ordered, list) or not isinstance(waves, list):
        raise RouteManifestError("normalized dependency output is invalid")
    flattened: list[str] = []
    for index, wave in enumerate(waves):
        if not isinstance(wave, dict) or set(wave) != {"index", "tickets"}:
            raise RouteManifestError("normalized wave has an invalid closed key set")
        if wave["index"] != index or not isinstance(wave["tickets"], list):
            raise RouteManifestError("normalized wave identity is invalid")
        flattened.extend(wave["tickets"])
    if flattened != ordered or set(ordered) != {row["ticket_id"] for row in records}:
        raise RouteManifestError("normalized dependency output does not cover records exactly")


def _normalize_route_records(
    raw_records: Any,
    *,
    feature_id: str,
    feature_scope_path: str | Path,
    feature_branch: str,
    trunk_branch: str,
    manager_flavor: str,
    ticket_system: str,
    scoped_ticket_list: Iterable[str],
    child_worktrees_root: str | Path,
    planning_dir: str | Path,
    scratch_dir: str | Path,
    source_schema: str,
    source_kind: str,
    source_path: str | None,
    source_sha256: str,
    source_backend: str,
) -> dict[str, Any]:
    """Validate the one canonical route-record contract shared by every source."""
    if ticket_system not in {"jira", "linear"}:
        raise RouteManifestError("ticket_system must be jira or linear")
    if source_backend != ticket_system:
        raise RouteManifestError("source backend does not match ticket_system")
    feature_id = _nonblank(feature_id, "feature_id")
    feature_branch = _short_branch(feature_branch, "feature_branch")
    trunk_branch = _short_branch(trunk_branch, "trunk_branch")
    if feature_branch == trunk_branch:
        raise RouteManifestError("feature and trunk branches must differ")
    if manager_flavor not in MANAGER_FLAVORS:
        raise RouteManifestError("manager_flavor is unsupported")
    scope_path = _brief_path(str(feature_scope_path), "feature_scope_path")
    worktrees_root = _absolute_dir(child_worktrees_root, "child_worktrees_root")
    planning_root = _absolute_dir(planning_dir, "planning_dir")
    scratch_root = _absolute_dir(scratch_dir, "scratch_dir")
    if len({worktrees_root, planning_root, scratch_root}) != 3:
        raise RouteManifestError(
            "child_worktrees_root, planning_dir, and scratch_dir must be canonically distinct"
        )
    scoped = [_nonblank(item, "scoped_ticket_list[]") for item in scoped_ticket_list]
    if not scoped or len(scoped) != len(set(scoped)):
        raise RouteManifestError("scoped_ticket_list must contain unique tickets")
    if not isinstance(raw_records, list) or not raw_records:
        raise RouteManifestError("route records must be a non-empty list")

    parsed_rows: list[dict[str, Any]] = []
    ticket_keys: set[str] = set()
    successor_ids: set[str] = set()
    source_identities: set[tuple[str, str]] = set()
    slugs: set[str] = set()
    branches: set[str] = set()
    derived_paths: set[Path] = set()
    for index, raw_row in enumerate(raw_records):
        field = f"records[{index}]"
        if not isinstance(raw_row, dict) or set(raw_row) != INLINE_RECORD_KEYS:
            unknown = sorted(set(raw_row) - INLINE_RECORD_KEYS) if isinstance(raw_row, dict) else []
            missing = sorted(INLINE_RECORD_KEYS - set(raw_row)) if isinstance(raw_row, dict) else []
            raise RouteManifestError(
                f"{field} must be a closed mapping; unknown={unknown}; missing={missing}"
            )
        ticket_id = _nonblank(raw_row["ticket_id"], f"{field}.ticket_id")
        successor_id = _nonblank(raw_row["successor_id"], f"{field}.successor_id")
        title = _nonblank(raw_row["title"], f"{field}.title")
        brief_path = _brief_path(raw_row["brief_path"], f"{field}.brief_path")
        surfaces = _string_list(raw_row["surfaces"], f"{field}.surfaces", allow_empty=False)
        owning_route = _nonblank(raw_row["owning_route"], f"{field}.owning_route")
        if owning_route not in SUPPORTED_ROUTES:
            raise RouteManifestError(f"{field}.owning_route is unsupported")
        depends_on = _string_list(
            raw_row["depends_on"], f"{field}.depends_on", allow_empty=True
        )
        branch = _short_branch(raw_row["branch_name"], f"{field}.branch_name")
        ticket_source, source_identity = _ticket_source(
            raw_row["ticket_source"],
            f"{field}.ticket_source",
            ticket_id=ticket_id,
            ticket_system=ticket_system,
        )
        payload = _route_payload(
            raw_row["route_payload"], f"{field}.route_payload", owning_route
        )
        if ticket_id in ticket_keys or successor_id in successor_ids:
            raise RouteManifestError("ticket_id and successor_id values must be unique")
        if source_identity in source_identities:
            raise RouteManifestError("ticket_source identities must be unique")

        slug = _slug(ticket_id)
        expected_branch = f"route/{slug}"
        if branch != expected_branch:
            raise RouteManifestError(f"{field}.branch_name must equal {expected_branch}")
        if slug in slugs:
            raise RouteManifestError("derived route slugs collide")
        if branch in branches or branch in {feature_branch, trunk_branch}:
            raise RouteManifestError(f"unsafe or protected route branch {branch!r}")
        route_worktree_path = _path_under(worktrees_root, slug, "worktree path")
        route_planning_dir = _path_under(planning_root / "routes", slug, "planning path")
        route_scratch_dir = _path_under(scratch_root / "routes", slug, "scratch path")
        for path in (route_worktree_path, route_planning_dir, route_scratch_dir):
            canonical_path = Path(path).resolve(strict=False)
            if canonical_path in derived_paths:
                raise RouteManifestError("derived route paths collide")
            derived_paths.add(canonical_path)

        ticket_keys.add(ticket_id)
        successor_ids.add(successor_id)
        source_identities.add(source_identity)
        slugs.add(slug)
        branches.add(branch)
        parsed_rows.append(
            {
                "ticket_id": ticket_id,
                "successor_id": successor_id,
                "title": title,
                "brief_path": str(brief_path),
                "surfaces": surfaces,
                "owning_route": owning_route,
                "depends_on": depends_on,
                "branch_name": branch,
                "ticket_source": ticket_source,
                "route_payload": payload,
                "route_worktree_path": route_worktree_path,
                "route_planning_dir": route_planning_dir,
                "route_scratch_dir": route_scratch_dir,
            }
        )

    if set(scoped) != ticket_keys:
        raise RouteManifestError("scoped_ticket_list must exactly equal route ticket keys")
    dependencies: dict[str, list[str]] = {}
    for row in parsed_rows:
        for dependency in row["depends_on"]:
            if dependency not in ticket_keys or dependency == row["ticket_id"]:
                raise RouteManifestError("unknown or self ticket dependency")
        dependencies[row["ticket_id"]] = row["depends_on"]
    ordered_keys = [row["ticket_id"] for row in parsed_rows]
    topological_order, waves = _topological_waves(ordered_keys, dependencies)
    manifest = {
        "schema": SCHEMA,
        "source_schema": source_schema,
        "feature_id": feature_id,
        "feature_scope_path": str(scope_path),
        "trunk_branch": trunk_branch,
        "feature_branch": feature_branch,
        "ticket_system": ticket_system,
        "source_backend": source_backend,
        "manager_flavor": manager_flavor,
        "source_kind": source_kind,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "topological_order": topological_order,
        "waves": waves,
        "records": parsed_rows,
    }
    _validate_normalized_output(manifest)
    return manifest


def load_successor_manifest(path: str | Path) -> tuple[dict[str, Any], str]:
    """Load JSON with duplicate-key rejection and return its source hash."""
    manifest_path = _canonical_absolute(path, "successor_manifest_path")
    if not manifest_path.is_file():
        raise RouteManifestError("successor_manifest_path must be a readable absolute file")
    raw = manifest_path.read_bytes()
    try:
        parsed = json.loads(raw, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RouteManifestError(f"invalid successor manifest JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise RouteManifestError("successor manifest must be a mapping")
    return parsed, hashlib.sha256(raw).hexdigest()


def load_ticket_route_map(raw: str) -> tuple[list[dict[str, Any]], str]:
    """Load inline JSON with duplicate-key rejection and return its source hash."""
    if not isinstance(raw, str) or not raw:
        raise RouteManifestError("ticket_route_map must be a non-empty JSON string")
    try:
        parsed = json.loads(raw, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as error:
        raise RouteManifestError(f"invalid ticket_route_map JSON: {error}") from error
    if not isinstance(parsed, list):
        raise RouteManifestError("ticket_route_map must be a list")
    return parsed, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_successor_manifest(
    manifest_path: str | Path,
    *,
    feature_id: str,
    feature_scope_path: str | Path,
    feature_branch: str,
    trunk_branch: str,
    manager_flavor: str,
    ticket_system: str,
    scoped_ticket_list: Iterable[str],
    child_worktrees_root: str | Path,
    planning_dir: str | Path,
    scratch_dir: str | Path,
) -> dict[str, Any]:
    """Normalize a strict successor envelope without performing writes."""
    envelope, source_sha256 = load_successor_manifest(manifest_path)
    unknown_envelope = set(envelope) - ENVELOPE_KEYS
    if unknown_envelope:
        raise RouteManifestError(f"unknown envelope keys: {sorted(unknown_envelope)}")
    if envelope.get("schema_version") != 1:
        raise RouteManifestError("schema_version must equal 1")
    if envelope.get("kind") != "age-255-estimate-clamp-successor-manifest":
        raise RouteManifestError("unsupported successor manifest kind")

    _validate_source_backend(envelope, ticket_system)
    if envelope.get("feature_branch") != feature_branch:
        raise RouteManifestError("envelope feature_branch does not match the caller")
    if envelope.get("manager_flavor") != manager_flavor:
        raise RouteManifestError("envelope manager_flavor does not match the caller")

    successors = envelope.get("successors")
    if not isinstance(successors, list) or not successors:
        raise RouteManifestError("successors must be a non-empty list")

    source_rows: list[dict[str, Any]] = []
    successor_ids: dict[str, str] = {}
    ticket_keys: set[str] = set()
    for index, raw_row in enumerate(successors):
        field = f"successors[{index}]"
        if not isinstance(raw_row, dict):
            raise RouteManifestError(f"{field} must be a mapping")
        unknown = set(raw_row) - SUCCESSOR_KEYS
        missing = SUCCESSOR_REQUIRED_KEYS - set(raw_row)
        if unknown or missing:
            raise RouteManifestError(
                f"{field} has unknown keys {sorted(unknown)} or missing keys {sorted(missing)}"
            )
        successor_id = _nonblank(raw_row["successor_id"], f"{field}.successor_id")
        ticket_key = _nonblank(raw_row["ticket_key"], f"{field}.ticket_key")
        title = _nonblank(raw_row["title"], f"{field}.title")
        route = _nonblank(raw_row["route"], f"{field}.route")
        if route not in SUPPORTED_ROUTES:
            raise RouteManifestError(f"{field}.route is unsupported")
        brief_path = _brief_path(raw_row["brief_path"], f"{field}.brief_path")
        depends_on = _string_list(raw_row["depends_on"], f"{field}.depends_on", allow_empty=True)
        surfaces = _string_list(raw_row["surfaces"], f"{field}.surfaces", allow_empty=False)
        for optional_list in ("characterization_ids", "new_behavior_ids", "runtime_proof_ids"):
            if optional_list in raw_row:
                _string_list(raw_row[optional_list], f"{field}.{optional_list}", allow_empty=True)
        if successor_id in successor_ids or ticket_key in ticket_keys:
            raise RouteManifestError("successor_id and ticket_key values must be unique")
        successor_ids[successor_id] = ticket_key
        ticket_keys.add(ticket_key)
        source_rows.append(
            {
                "ticket_id": ticket_key,
                "successor_id": successor_id,
                "title": title,
                "brief_path": str(brief_path),
                "surfaces": surfaces,
                "owning_route": route,
                "source_depends_on": depends_on,
            }
        )

    normalized_rows: list[dict[str, Any]] = []
    for row in source_rows:
        mapped: list[str] = []
        for successor_id in row.pop("source_depends_on"):
            dependency = successor_ids.get(successor_id)
            if dependency is None or dependency == row["ticket_id"]:
                raise RouteManifestError("unknown or self successor dependency")
            mapped.append(dependency)
        target_contract = {
            "brief_path": row["brief_path"],
            "surfaces": row["surfaces"],
        }
        slice_contract = {
            "successor_id": row["successor_id"],
            "title": row["title"],
            "surfaces": row["surfaces"],
        }
        normalized_rows.append(
            {
                **row,
                "depends_on": mapped,
                "branch_name": f"route/{_slug(row['ticket_id'])}",
                "ticket_source": {
                    "linear_issue_key" if ticket_system == "linear" else "jira_issue_key": row[
                        "ticket_id"
                    ]
                },
                "route_payload": (
                    {
                        "target_list": json.dumps(
                            target_contract, separators=(",", ":"), sort_keys=True
                        ),
                        "slice_bounds": json.dumps(
                            slice_contract, separators=(",", ":"), sort_keys=True
                        ),
                    }
                    if row["owning_route"] == "refactoring"
                    else {}
                ),
            }
        )

    handoff = envelope.get("handoff")
    if handoff is not None:
        if not isinstance(handoff, dict) or set(handoff) != HANDOFF_KEYS:
            raise RouteManifestError("handoff must be a strict mapping")
        if handoff.get("coordinator") != "feature-development":
            raise RouteManifestError("handoff coordinator must be feature-development")
        if handoff.get("feature_branch") != feature_branch:
            raise RouteManifestError("handoff feature_branch does not match the caller")
        if any(handoff.get(key) is not True for key in HANDOFF_TRUE_KEYS):
            raise RouteManifestError("handoff freshness and context flags must be true")
        owning_routes = handoff.get("owning_routes")
        if not isinstance(owning_routes, dict) or owning_routes != {
            row["successor_id"]: row["owning_route"] for row in normalized_rows
        }:
            raise RouteManifestError("handoff owning_routes does not match successors")

    return _normalize_route_records(
        normalized_rows,
        feature_id=feature_id,
        feature_scope_path=feature_scope_path,
        feature_branch=feature_branch,
        trunk_branch=trunk_branch,
        manager_flavor=manager_flavor,
        ticket_system=ticket_system,
        scoped_ticket_list=scoped_ticket_list,
        child_worktrees_root=child_worktrees_root,
        planning_dir=planning_dir,
        scratch_dir=scratch_dir,
        source_schema=SOURCE_SCHEMA,
        source_kind="successor_manifest_path",
        source_path=str(_canonical_absolute(manifest_path, "successor_manifest_path")),
        source_sha256=source_sha256,
        source_backend=SOURCE_KIND_BACKENDS["age-255-estimate-clamp-successor-manifest"],
    )


def normalize_ticket_route_map(
    ticket_route_map_json: str,
    *,
    feature_id: str,
    feature_scope_path: str | Path,
    feature_branch: str,
    trunk_branch: str,
    manager_flavor: str,
    ticket_system: str,
    scoped_ticket_list: Iterable[str],
    child_worktrees_root: str | Path,
    planning_dir: str | Path,
    scratch_dir: str | Path,
) -> dict[str, Any]:
    """Normalize strict inline records through the shared canonical validator."""
    records, source_sha256 = load_ticket_route_map(ticket_route_map_json)
    return _normalize_route_records(
        records,
        feature_id=feature_id,
        feature_scope_path=feature_scope_path,
        feature_branch=feature_branch,
        trunk_branch=trunk_branch,
        manager_flavor=manager_flavor,
        ticket_system=ticket_system,
        scoped_ticket_list=scoped_ticket_list,
        child_worktrees_root=child_worktrees_root,
        planning_dir=planning_dir,
        scratch_dir=scratch_dir,
        source_schema=INLINE_SOURCE_SCHEMA,
        source_kind="ticket_route_map",
        source_path=None,
        source_sha256=source_sha256,
        source_backend=ticket_system,
    )


def normalize_route_source(
    *,
    successor_manifest_path: str | Path | None = None,
    ticket_route_map_json: str | None = None,
    **common: Any,
) -> dict[str, Any]:
    """Enforce source xor before parsing and normalize the selected source."""
    selected = (successor_manifest_path is not None, ticket_route_map_json is not None)
    if sum(selected) != 1:
        raise RouteManifestError(
            "exactly one of successor_manifest_path or ticket_route_map_json is required"
        )
    if successor_manifest_path is not None:
        return normalize_successor_manifest(successor_manifest_path, **common)
    assert ticket_route_map_json is not None
    return normalize_ticket_route_map(ticket_route_map_json, **common)


def write_manifest(output_path: str | Path, manifest: dict[str, Any]) -> None:
    """Atomically write a fully validated normalized manifest."""
    output = _canonical_absolute(output_path, "output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, delete=False
    ) as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--successor-manifest")
    source.add_argument("--ticket-route-map-json")
    parser.add_argument("--feature-id", required=True)
    parser.add_argument("--feature-scope-path", required=True)
    parser.add_argument("--feature-branch", required=True)
    parser.add_argument("--trunk-branch", required=True)
    parser.add_argument("--manager-flavor", required=True)
    parser.add_argument("--ticket-system", choices=("jira", "linear"), required=True)
    parser.add_argument("--scoped-ticket", action="append", required=True)
    parser.add_argument("--child-worktrees-root", required=True)
    parser.add_argument("--planning-dir", required=True)
    parser.add_argument("--scratch-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        manifest = normalize_route_source(
            successor_manifest_path=args.successor_manifest,
            ticket_route_map_json=args.ticket_route_map_json,
            feature_id=args.feature_id,
            feature_scope_path=args.feature_scope_path,
            feature_branch=args.feature_branch,
            trunk_branch=args.trunk_branch,
            manager_flavor=args.manager_flavor,
            ticket_system=args.ticket_system,
            scoped_ticket_list=args.scoped_ticket,
            child_worktrees_root=args.child_worktrees_root,
            planning_dir=args.planning_dir,
            scratch_dir=args.scratch_dir,
        )
        write_manifest(args.output, manifest)
    except RouteManifestError as error:
        print(f"BLOCKED:invalid-ticket-route-manifest: {error}")
        return 2
    print(f"feature-route-manifest: normalized; output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
