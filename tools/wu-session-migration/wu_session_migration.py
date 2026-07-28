from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence, cast
from urllib.parse import urlparse


PLAN_SCHEMA = "wu-session-migration-plan-v1"
INVENTORY_SCHEMA = "age-260-session-migration-inventory-v1"
PR_EVIDENCE_SCHEMA = "wu-session-pr-evidence-v2"
PR_PROVIDER_JSON_SELECTOR = "url,state,headRefName,headRefOid,baseRefName,baseRefOid,mergeCommit,mergedAt"
DISPOSITION_SCHEMA = "wu-session-cutover-dispositions-v1"
CONFLICT_RESOLUTION_SCHEMA = "wu-session-conflict-resolutions-v1"
ACTIVE_INDEX_SCHEMA = "wu-sessions-active-wake-v1"
JOURNAL_SCHEMA = "wu-session-migration-journal-v1"
RUNTIME_REQUEST_SCHEMA = "wu-session-runtime-write-v1"
RUNTIME_OPERATIONS = {
    "phase0-init",
    "phase7-upsert",
    "phase9-update",
    "resumer-update",
    "resumer-close",
}
SUPPORTED_TICKET_SYSTEMS = {"jira", "linear"}
EXPECTED_COUNTS = {
    "manifest_files": 306,
    "index_files": 7,
    "index_rows": 152,
    "migration_cohort": 42,
    "migration_cohort_base_branch_persisted_or_derived": 25,
    "migration_cohort_distinct_manifests_already_indexed": 30,
    "migration_cohort_explicit_refusal": 3,
    "migration_cohort_fully_persisted": 2,
    "migration_cohort_index_rows": 32,
    "migration_cohort_trusted_pr_query_required": 37,
}
RETIRED_KEYS = {
    "base",
    "branch_base",
    "branch_out_base",
    "base_ref",
    "draft_pr_base",
    "pr_base_branch",
    "pre_merge_main_sha",
    "manifest_path",
    "manifest",
    "head_sha",
    "pr_head_sha",
    "pr_url",
}
INDEX_RESERVED_KEYS = {"schema", "schema_version", "sessions", "rows"}
FULL_OID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
LIST_LOCATOR_RE = re.compile(r"^(sessions|rows)\[(\d+)]$")
MERGE_METHOD_CAPTURE_KEYS = {
    "source",
    "command",
    "captured_at",
    "payload",
    "payload_sha256",
}
MERGE_METHOD_PAYLOAD_KEYS = {"sha", "merged", "message"}
RUNTIME_REQUEST_KEYS = {
    "schema",
    "operation",
    "planning_root",
    "manifest_path",
    "index_path",
    "row_identity",
    "sources",
    "replacement_manifest",
    "replacement_index",
    "input_set_sha256",
    "payload_sha256",
}
SOURCE_IDENTITY_KEYS = {"exists", "sha256", "device", "inode", "mode"}
ROW_IDENTITY_KEYS = {"ticket_id", "branch", "draft_pr_url", "session_manifest_path"}
ACTIVE_ROW_KEYS = {
    "ticket_id",
    "ticket_system",
    "branch",
    "base_branch",
    "branch_out_sha",
    "draft_pr_url",
    "draft_pr_number",
    "draft_pr_head_sha",
    "pr_open_base_sha",
    "pre_merge_base_sha",
    "merge_sha",
    "merged_at",
    "session_manifest_path",
    "worktree_path",
    "planning_dir",
}
RUNTIME_ALLOWED_MANIFEST_CHANGES = {
    "phase7-upsert": {
        "draft_pr_url",
        "draft_pr_number",
        "draft_pr_head_sha",
        "pr_open_base_sha",
        "phase_history",
    },
    "phase9-update": {
        "phase_8_reviewed_is_draft",
        "phase_8_reviewed_base_sha",
        "phase_8_reviewed_head_sha",
        "phase_8_reviewed_artifact_path",
        "phase_8_reviewed_artifact_sha256",
        "phase_9_currentness_result",
        "phase_9_currentness_path",
        "phase_9_currentness_sha256",
        "pre_merge_base_sha",
        "merge_sha",
        "post_merge_base_sha",
        "merged_at",
        "phase_history",
    },
    "resumer-update": {
        "pre_merge_base_sha",
        "merge_sha",
        "post_merge_base_sha",
        "merged_at",
        "post_merge",
        "phase_history",
    },
    "resumer-close": {
        "pre_merge_base_sha",
        "merge_sha",
        "post_merge_base_sha",
        "merged_at",
        "post_merge",
        "successor_session_brief",
        "closed_at",
        "phase_history",
    },
}

# Tests replace this hook to inject deterministic failures without weakening production checks.
FAULT_HOOK: Callable[[str, int], None] | None = None


class MigrationError(ValueError):
    pass


class InputError(MigrationError):
    pass


class ApplyError(MigrationError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wu-session-migration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_run = subparsers.add_parser("dry-run")
    dry_run.add_argument("--inventory", type=Path, required=True)
    dry_run.add_argument("--reviewed-inventory-sha256", required=True)
    dry_run.add_argument("--pr-evidence", type=Path, required=True)
    dry_run.add_argument("--dispositions", type=Path, required=True)
    dry_run.add_argument("--conflict-resolutions", type=Path)
    dry_run.add_argument("--plan", type=Path, required=True)

    capture = subparsers.add_parser("capture-evidence")
    capture.add_argument("--inventory", type=Path, required=True)
    capture.add_argument("--reviewed-inventory-sha256", required=True)
    capture.add_argument("--output", type=Path, required=True)

    apply = subparsers.add_parser("apply")
    apply.add_argument("--plan", type=Path, required=True)
    for operation in sorted(RUNTIME_OPERATIONS):
        runtime = subparsers.add_parser(operation)
        runtime.add_argument("--request", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        with _cutover_lock():
            recover_incomplete_transaction()
            if args.command == "dry-run":
                plan = build_plan(
                    args.inventory,
                    args.pr_evidence,
                    args.dispositions,
                    args.reviewed_inventory_sha256,
                    args.conflict_resolutions,
                    args.plan,
                )
                try:
                    _atomic_write_bytes(args.plan, _json_bytes(plan))
                except OSError as exc:
                    raise InputError(f"cannot write plan {args.plan}: {exc}") from exc
                print(
                    "WU-SESSION-MIGRATION-DRY-RUN: "
                    f"{'PASS' if plan['eligible'] else 'REFUSED'}; plan={args.plan}"
                )
                return 0 if plan["eligible"] else 1
            if args.command == "capture-evidence":
                capture_evidence(
                    args.inventory, args.reviewed_inventory_sha256, args.output
                )
                print(f"WU-SESSION-PR-EVIDENCE: PASS; evidence={args.output}")
                return 0
            if args.command == "apply":
                apply_plan(args.plan, lock_already_held=True)
                print(f"WU-SESSION-MIGRATION-APPLY: PASS; plan={args.plan}")
                return 0
            apply_runtime_request(args.request, args.command, lock_already_held=True)
            print(f"WU-SESSION-RUNTIME-WRITE: PASS; operation={args.command}; request={args.request}")
            return 0
    except InputError as exc:
        print(f"wu-session-migration: {exc}", file=sys.stderr)
        return 2
    except ApplyError as exc:
        print(f"wu-session-migration: {exc}", file=sys.stderr)
        return 3
    except MigrationError as exc:
        print(f"wu-session-migration: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"wu-session-migration: {exc}", file=sys.stderr)
        return 3


def build_plan(
    inventory_path: Path,
    evidence_path: Path,
    dispositions_path: Path,
    reviewed_inventory_sha256: str | None = None,
    conflict_resolutions_path: Path | None = None,
    plan_path: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(reviewed_inventory_sha256, str) or not FULL_OID_RE.fullmatch(
        reviewed_inventory_sha256.lower()
    ):
        raise InputError("an explicit full reviewed inventory SHA-256 is required")

    inventory_raw = _safe_read_bytes(inventory_path)
    actual_inventory_sha256 = _sha256(inventory_raw)
    if actual_inventory_sha256 != reviewed_inventory_sha256.lower():
        raise InputError("reviewed inventory SHA-256 mismatch")
    inventory = _decode_json(inventory_raw, inventory_path)
    evidence_raw = _safe_read_bytes(evidence_path)
    evidence = _decode_json(evidence_raw, evidence_path)
    dispositions_raw = _safe_read_bytes(dispositions_path)
    dispositions_doc = _decode_json(dispositions_raw, dispositions_path)
    resolutions_raw: bytes | None = None
    resolutions_doc: dict[str, Any] = {
        "schema": CONFLICT_RESOLUTION_SCHEMA,
        "resolutions": [],
    }
    if conflict_resolutions_path is not None:
        resolutions_raw = _safe_read_bytes(conflict_resolutions_path)
        resolutions_doc = _decode_json(resolutions_raw, conflict_resolutions_path)

    context = _validate_inventory(inventory, inventory_path)
    managed_paths = context["manifest_paths"] + context["index_paths"]
    auxiliary_paths = [inventory_path, evidence_path, dispositions_path]
    if conflict_resolutions_path is not None:
        auxiliary_paths.append(conflict_resolutions_path)
    _reject_path_aliases(managed_paths + auxiliary_paths)
    if plan_path is not None:
        _validate_plan_destination(
            plan_path,
            context["planning_roots"],
            managed_paths + auxiliary_paths,
        )

    if evidence.get("schema") != PR_EVIDENCE_SCHEMA or not isinstance(
        evidence.get("prs"), dict
    ):
        raise InputError(f"PR evidence must use schema {PR_EVIDENCE_SCHEMA}")
    if evidence.get("reviewed_inventory_sha256") != actual_inventory_sha256:
        raise InputError("PR evidence is not bound to the reviewed inventory digest")
    cohort = inventory["migration_cohort"]
    dispositions = _validate_dispositions(dispositions_doc, cohort)
    resolutions = _validate_conflict_resolutions(resolutions_doc, cohort)
    documents = context["documents"]
    source_metadata = context["source_metadata"]
    inventory_rows = context["inventory_rows"]
    index_paths = context["index_paths"]

    rows: list[dict[str, Any]] = []
    active_rows: dict[Path, list[dict[str, Any]]] = {path: [] for path in index_paths}
    manifest_replacements: dict[Path, dict[str, Any]] = {}
    for candidate in sorted(cohort, key=lambda item: item["manifest_path"]):
        verdict = _plan_candidate(
            candidate,
            evidence["prs"],
            dispositions,
            resolutions,
            index_paths,
            documents,
            inventory_rows,
        )
        rows.append(verdict)
        if verdict["verdict"] in {"migrated-open", "migrated-merged"}:
            manifest_path = Path(verdict["manifest_path"])
            manifest_replacements[manifest_path] = verdict.pop("_manifest")
            active_rows[Path(verdict["index_path"])].append(verdict.pop("_active_row"))

    replacements: dict[Path, Any] = dict(manifest_replacements)
    active_index_paths: list[Path] = []
    for source_index_path in index_paths:
        active_path = source_index_path.with_name("sessions.active-wake.json")
        _assert_safe_output(active_path)
        active_index_paths.append(active_path)
        replacements[active_path] = {
            "schema": ACTIVE_INDEX_SCHEMA,
            "reviewed_inventory_sha256": actual_inventory_sha256,
            "source_index_path": str(source_index_path),
            "sessions": sorted(
                active_rows[source_index_path],
                key=lambda row: (
                    row["draft_pr_url"],
                    row["branch"],
                    row["ticket_id"],
                    row["session_manifest_path"],
                ),
            ),
        }
    _reject_path_aliases(active_index_paths, allow_missing=True)
    _reject_cross_aliases(active_index_paths, managed_paths + auxiliary_paths)

    writes: list[dict[str, Any]] = []
    for path in sorted(replacements, key=str):
        replacement_bytes = _json_bytes(replacements[path])
        if path.exists():
            raw, identity = _safe_read_with_identity(path)
            source_exists = True
            source_sha256 = _sha256(raw)
            source_device = identity[0]
            source_inode = identity[1]
            source_mode = os.stat(path, follow_symlinks=False).st_mode & 0o777
            if raw == replacement_bytes:
                continue
        else:
            source_exists = False
            source_sha256 = None
            source_device = None
            source_inode = None
            source_mode = None
        writes.append(
            {
                "path": str(path),
                "source_exists": source_exists,
                "source_sha256": source_sha256,
                "source_device": source_device,
                "source_inode": source_inode,
                "source_mode": source_mode,
                "replacement_sha256": _sha256(replacement_bytes),
                "replacement": replacements[path],
            }
        )

    inputs = {
        "inventory": {
            "path": str(inventory_path.absolute()),
            "sha256": actual_inventory_sha256,
        },
        "pr_evidence": {
            "path": str(evidence_path.absolute()),
            "sha256": _sha256(evidence_raw),
        },
        "dispositions": {
            "path": str(dispositions_path.absolute()),
            "sha256": _sha256(dispositions_raw),
        },
        "conflict_resolutions": (
            {
                "path": str(conflict_resolutions_path.absolute()),
                "sha256": _sha256(resolutions_raw or b""),
            }
            if conflict_resolutions_path is not None
            else None
        ),
    }
    eligible = all(row["verdict"] != "refused" for row in rows)
    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "mode": "dry-run",
        "eligible": eligible,
        "reviewed_inventory_sha256": actual_inventory_sha256,
        "validated_counts": EXPECTED_COUNTS,
        "planning_roots": [str(path) for path in context["planning_roots"]],
        "source_index_paths": [str(path) for path in index_paths],
        "active_index_paths": [str(path) for path in active_index_paths],
        "inputs": inputs,
        "input_set_sha256": _sha256(_canonical_json_bytes(inputs)),
        "rows": rows,
        "writes": writes,
    }
    plan["payload_sha256"] = _sha256(_canonical_json_bytes(plan))
    return plan


def apply_plan(plan_path: Path, *, lock_already_held: bool = False) -> None:
    if not lock_already_held:
        with _cutover_lock():
            recover_incomplete_transaction()
            _apply_plan_locked(plan_path)
        return
    _apply_plan_locked(plan_path)


def _apply_plan_locked(plan_path: Path) -> None:
    plan_raw = _safe_read_bytes(plan_path)
    plan = _decode_json(plan_raw, plan_path)
    _validate_plan_schema(plan)
    if plan.get("eligible") is not True:
        raise ApplyError("apply refuses an ineligible migration plan")
    inputs = plan["inputs"]
    conflict_input = inputs.get("conflict_resolutions")
    try:
        rebuilt = build_plan(
            Path(inputs["inventory"]["path"]),
            Path(inputs["pr_evidence"]["path"]),
            Path(inputs["dispositions"]["path"]),
            plan["reviewed_inventory_sha256"],
            Path(conflict_input["path"]) if conflict_input is not None else None,
            plan_path,
        )
    except MigrationError as exc:
        raise ApplyError(f"stale or invalid reviewed plan inputs: {exc}") from exc
    if rebuilt != plan:
        raise ApplyError("stale or semantically altered migration plan")
    planning_roots = [Path(value) for value in plan["planning_roots"]]
    source_paths = [Path(value) for value in plan["source_index_paths"]]
    managed_targets = [Path(write["path"]) for write in plan["writes"]]
    _validate_plan_destination(plan_path, planning_roots, source_paths + managed_targets)
    _verify_plan_inputs(plan)
    _validate_writes(plan["writes"], planning_roots)
    _execute_transaction(
        plan_path=plan_path,
        plan_raw=plan_raw,
        operation="migration-apply",
        plan_payload_sha256=plan["payload_sha256"],
        input_set_sha256=plan["input_set_sha256"],
        planning_roots=planning_roots,
        writes=plan["writes"],
    )


def apply_runtime_request(
    request_path: Path,
    operation: str,
    *,
    lock_already_held: bool = False,
) -> None:
    if operation not in RUNTIME_OPERATIONS:
        raise InputError(f"unsupported runtime operation: {operation}")
    if not lock_already_held:
        with _cutover_lock():
            recover_incomplete_transaction()
            _apply_runtime_request_locked(request_path, operation)
        return
    _apply_runtime_request_locked(request_path, operation)


def _apply_runtime_request_locked(request_path: Path, operation: str) -> None:
    request_raw = _safe_read_bytes(request_path)
    request = _decode_json(request_raw, request_path)
    writes, planning_roots = _validate_runtime_request(request, operation, check_sources=True)
    _reject_cross_aliases([request_path], [Path(write["path"]) for write in writes])
    _execute_transaction(
        plan_path=request_path,
        plan_raw=request_raw,
        operation=operation,
        plan_payload_sha256=request["payload_sha256"],
        input_set_sha256=request["input_set_sha256"],
        planning_roots=planning_roots,
        writes=writes,
    )


def _execute_transaction(
    *,
    plan_path: Path,
    plan_raw: bytes,
    operation: str,
    plan_payload_sha256: str,
    input_set_sha256: str,
    planning_roots: list[Path],
    writes: Sequence[Mapping[str, Any]],
) -> None:
    transaction_id = str(uuid.uuid4())
    targets: list[dict[str, Any]] = []
    held_parents: dict[Path, dict[str, Any]] = {}
    try:
        for write in writes:
            path = Path(write["path"])
            if path.parent not in held_parents:
                held_parents[path.parent] = _open_held_parent(path.parent)
        for write in writes:
            path = Path(write["path"])
            parent = held_parents[path.parent]
            _verify_source_identity_at(parent, path.name, write, path)
            replacement_mode = write["source_mode"] if write["source_exists"] else 0o600
            replacement_name = f".{path.name}.{transaction_id}.replacement"
            backup_name = f".{path.name}.{transaction_id}.backup"
            targets.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "parent_path": str(path.parent),
                    "parent_device": parent["device"],
                    "parent_inode": parent["inode"],
                    "original_exists": write["source_exists"],
                    "original_sha256": write["source_sha256"],
                    "original_device": write["source_device"],
                    "original_inode": write["source_inode"],
                    "original_mode": write["source_mode"],
                    "backup_name": backup_name if write["source_exists"] else None,
                    "backup_path": (
                        str(path.parent / backup_name) if write["source_exists"] else None
                    ),
                    "backup_sha256": write["source_sha256"],
                    "backup_mode": write["source_mode"],
                    "backup_device": None,
                    "backup_inode": None,
                    "replacement_name": replacement_name,
                    "replacement_path": str(path.parent / replacement_name),
                    "replacement_sha256": write["replacement_sha256"],
                    "replacement_mode": replacement_mode,
                    "replacement_device": None,
                    "replacement_inode": None,
                }
            )

        journal = {
            "schema": JOURNAL_SCHEMA,
            "transaction_id": transaction_id,
            "operation": operation,
            "phase": "staging",
            "plan_path": str(plan_path.absolute()),
            "plan_sha256": _sha256(plan_raw),
            "plan_payload_sha256": plan_payload_sha256,
            "input_set_sha256": input_set_sha256,
            "planning_roots": [str(path) for path in planning_roots],
            "ordered_targets": targets,
            "completed_replacements": [],
        }
        _inject_fault("journal", 0)
        _inject_fault("journal-create", 0)
        _write_journal(journal)

        for index, (write, target) in enumerate(zip(writes, targets)):
            _inject_fault("stage", index)
            path = Path(write["path"])
            parent = held_parents[path.parent]
            _verify_source_identity_at(parent, path.name, write, path)
            if write["source_exists"]:
                original_bytes, _ = _read_at(parent, path.name, path)
                _write_new_file_at(
                    parent,
                    target["backup_name"],
                    original_bytes,
                    write["source_mode"],
                    "backup",
                    index,
                )
                target["backup_device"], target["backup_inode"] = _identity_at(
                    parent, target["backup_name"]
                )
                _write_journal(journal)
            replacement_bytes = _json_bytes(write["replacement"])
            _write_new_file_at(
                parent,
                target["replacement_name"],
                replacement_bytes,
                target["replacement_mode"],
                "replacement",
                index,
            )
            target["replacement_device"], target["replacement_inode"] = _identity_at(
                parent, target["replacement_name"]
            )
            _write_journal(journal)
        for write in writes:
            path = Path(write["path"])
            _verify_source_identity_at(held_parents[path.parent], path.name, write, path)
        _inject_fault("after-final-source-check", 0)
        for parent in held_parents.values():
            _verify_held_parent(parent)
        for write in writes:
            path = Path(write["path"])
            _verify_source_identity_at(held_parents[path.parent], path.name, write, path)
        journal["phase"] = "prepared"
        _write_journal(journal)
        _inject_fault("journal-transition", 0)
        journal["phase"] = "committing"
        _write_journal(journal)

        for write in writes:
            path = Path(write["path"])
            parent = held_parents[path.parent]
            _verify_held_parent(parent)
            _verify_source_identity_at(parent, path.name, write, path)
        for index, (write, target) in enumerate(zip(writes, targets)):
            parent = held_parents[Path(target["parent_path"])]
            _verify_held_parent(parent)
            _inject_fault("replace", index)
            _inject_fault("replacement", index)
            _verify_source_identity_at(parent, target["name"], write, Path(target["path"]))
            os.replace(
                target["replacement_name"],
                target["name"],
                src_dir_fd=parent["fd"],
                dst_dir_fd=parent["fd"],
            )
            _inject_fault("directory-fsync", index)
            _inject_fault("commit-parent-fsync", index)
            os.fsync(parent["fd"])
            journal["completed_replacements"].append(index)
            _inject_fault("journal", index + 1)
            _inject_fault("journal-transition", index + 1)
            _write_journal(journal)
        journal["phase"] = "committed"
        _inject_fault("journal-transition", len(targets) + 1)
        _write_journal(journal)
        _cleanup_transaction(journal, held_parents=held_parents)
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if _journal_path().exists():
            try:
                recover_incomplete_transaction()
            except ApplyError as recovery_exc:
                raise ApplyError(
                    f"transaction failed; recovery remains pending: {exc}; {recovery_exc}"
                ) from exc
        if isinstance(exc, InputError):
            raise
        raise ApplyError(f"transaction failed and was rolled back: {exc}") from exc
    finally:
        for parent in held_parents.values():
            os.close(parent["fd"])


def recover_incomplete_transaction() -> None:
    journal_path = _journal_path()
    if not journal_path.exists():
        return
    try:
        journal = _decode_json(_safe_read_bytes(journal_path), journal_path)
    except MigrationError as exc:
        raise ApplyError(f"cannot read recovery journal: {exc}") from exc
    journal = _validate_recovery_journal(journal)
    held_parents: dict[Path, dict[str, Any]] = {}
    try:
        failures: list[str] = []
        unavailable_parents: set[Path] = set()
        for target in journal["ordered_targets"]:
            parent_path = Path(target["parent_path"])
            if parent_path in held_parents or parent_path in unavailable_parents:
                continue
            try:
                parent = _open_held_parent(parent_path)
                expected_identities = {
                    (candidate["parent_device"], candidate["parent_inode"])
                    for candidate in journal["ordered_targets"]
                    if candidate["parent_path"] == target["parent_path"]
                }
                if expected_identities != {(parent["device"], parent["inode"])}:
                    os.close(parent["fd"])
                    raise ApplyError("recorded parent identity does not match")
                held_parents[parent_path] = parent
            except (MigrationError, OSError) as exc:
                unavailable_parents.add(parent_path)
                targets = [
                    candidate["path"]
                    for candidate in journal["ordered_targets"]
                    if candidate["parent_path"] == str(parent_path)
                ]
                failures.append(
                    f"{parent_path} (targets: {', '.join(targets)}): {exc}"
                )

        unsafe_targets = _validate_recovery_targets(
            journal, held_parents, unavailable_parents
        )
        failures.extend(
            f"{journal['ordered_targets'][index]['path']}: {message}"
            for index, message in sorted(unsafe_targets.items())
        )
        parents_to_fsync: set[Path] = set()
        ordered = list(enumerate(journal["ordered_targets"]))
        if journal["phase"] not in {"staging", "committed"}:
            ordered.reverse()
        for index, target in ordered:
            parent_path = Path(target["parent_path"])
            if parent_path in unavailable_parents or index in unsafe_targets:
                continue
            parent = held_parents[parent_path]
            try:
                _inject_fault("recovery", index)
                _verify_held_parent(parent)
                if journal["phase"] == "committed":
                    if _existing_hash_at(parent, target["name"], Path(target["path"])) != target[
                        "replacement_sha256"
                    ]:
                        raise OSError("committed target does not contain the replacement")
                elif journal["phase"] != "staging":
                    _rollback_recovery_target(parent, target, index)
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                failures.append(f"{target['path']}: {exc}")
                continue
            parents_to_fsync.add(parent_path)
            failures.extend(
                _cleanup_target_artifacts(parent, target, index)
            )

        for parent_path in sorted(parents_to_fsync, key=str):
            parent = held_parents[parent_path]
            try:
                _verify_held_parent(parent)
                _inject_fault("rollback-parent-fsync", 0)
                _inject_fault("cleanup-parent-fsync", 0)
                os.fsync(parent["fd"])
            except (MigrationError, OSError) as exc:
                failures.append(f"{parent_path}: {exc}")
        if failures:
            raise ApplyError("recovery failures: " + "; ".join(failures))
        _remove_transaction_journal()
    finally:
        for parent in held_parents.values():
            os.close(parent["fd"])


def _rollback_recovery_target(
    parent: Mapping[str, Any], target: Mapping[str, Any], index: int
) -> None:
    current_hash = _existing_hash_at(parent, target["name"], Path(target["path"]))
    if target["original_exists"]:
        if current_hash == target["original_sha256"]:
            return
        if current_hash != target["replacement_sha256"]:
            raise OSError("target has content from neither side of the transaction")
        backup_hash = _existing_hash_at(
            parent, target["backup_name"], Path(target["backup_path"])
        )
        if backup_hash != target["backup_sha256"]:
            raise OSError("original backup is missing or corrupt")
        _inject_fault("rollback-replace", index)
        os.replace(
            target["backup_name"],
            target["name"],
            src_dir_fd=parent["fd"],
            dst_dir_fd=parent["fd"],
        )
    elif current_hash is not None:
        if current_hash != target["replacement_sha256"]:
            raise OSError("new target has unexpected content")
        _inject_fault("rollback-unlink", index)
        os.unlink(target["name"], dir_fd=parent["fd"])
    else:
        return
    _inject_fault("rollback", index)


def _validate_recovery_targets(
    journal: Mapping[str, Any],
    held_parents: Mapping[Path, Mapping[str, Any]],
    unavailable_parents: set[Path],
) -> dict[int, str]:
    errors: dict[int, list[str]] = {}
    inode_owners: dict[tuple[int, int], list[tuple[int, Path]]] = {
        _inode(Path(journal["plan_path"])): [(-1, Path(journal["plan_path"]))]
    }
    for index, target in enumerate(journal["ordered_targets"]):
        parent_path = Path(target["parent_path"])
        if parent_path in unavailable_parents:
            continue
        parent = held_parents[parent_path]
        try:
            _verify_held_parent(parent)
        except (MigrationError, OSError) as exc:
            errors.setdefault(index, []).append(str(exc))
            continue
        artifacts = [
            (Path(target["path"]), target["name"], None),
            (
                Path(target["replacement_path"]),
                target["replacement_name"],
                "replacement",
            ),
        ]
        if target["backup_path"] is not None:
            artifacts.append(
                (Path(target["backup_path"]), target["backup_name"], "backup")
            )
        for path, name, prefix in artifacts:
            try:
                _assert_safe_output(path)
                metadata = os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode):
                    raise OSError("path is not a regular file")
                inode_owners.setdefault((metadata.st_dev, metadata.st_ino), []).append(
                    (index, path)
                )
                if prefix is not None:
                    expected_identity = (
                        target[f"{prefix}_device"],
                        target[f"{prefix}_inode"],
                    )
                    if expected_identity != (None, None) and (
                        metadata.st_dev,
                        metadata.st_ino,
                    ) != expected_identity:
                        raise OSError(f"{prefix} artifact identity changed")
            except FileNotFoundError:
                continue
            except (MigrationError, OSError) as exc:
                errors.setdefault(index, []).append(f"{path}: {exc}")
    for owners in inode_owners.values():
        if len(owners) < 2:
            continue
        paths = ", ".join(str(path) for _, path in owners)
        for index, _ in owners:
            if index >= 0:
                errors.setdefault(index, []).append(
                    f"recovery inode aliases another bound path: {paths}"
                )
    return {index: ", ".join(messages) for index, messages in errors.items()}


def _cleanup_target_artifacts(
    parent: Mapping[str, Any], target: Mapping[str, Any], index: int
) -> list[str]:
    failures: list[str] = []
    for prefix in ("backup", "replacement"):
        name = target[f"{prefix}_name"]
        if not name:
            continue
        display_path = Path(target[f"{prefix}_path"])
        try:
            _verify_held_parent(parent)
            _inject_fault("cleanup-unlink", index)
            try:
                metadata = os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError("transaction artifact is not a regular file")
            expected_identity = (
                target[f"{prefix}_device"],
                target[f"{prefix}_inode"],
            )
            if expected_identity == (None, None):
                raw, identity = _read_at(parent, name, display_path)
                if (
                    _sha256(raw) != target[f"{prefix}_sha256"]
                    or identity[2] != target[f"{prefix}_mode"]
                ):
                    raise OSError(
                        "identity-unbound transaction artifact does not match "
                        "planned bytes and regular-file metadata"
                    )
            elif (metadata.st_dev, metadata.st_ino) != expected_identity:
                raise OSError("transaction artifact identity changed")
            os.unlink(name, dir_fd=parent["fd"])
        except (MigrationError, OSError) as exc:
            failures.append(f"{display_path}: {exc}")
    return failures


def _remove_transaction_journal() -> None:
    journal_path = _journal_path()
    _inject_fault("journal-cleanup", 0)
    journal_path.unlink(missing_ok=True)
    _fsync_directory(journal_path.parent)


def _validate_recovery_journal(document: Mapping[str, Any]) -> dict[str, Any]:
    try:
        journal_keys = {
            "schema",
            "transaction_id",
            "operation",
            "phase",
            "plan_path",
            "plan_sha256",
            "plan_payload_sha256",
            "input_set_sha256",
            "planning_roots",
            "ordered_targets",
            "completed_replacements",
        }
        target_keys = {
            "path",
            "name",
            "parent_path",
            "parent_device",
            "parent_inode",
            "original_exists",
            "original_sha256",
            "original_device",
            "original_inode",
            "original_mode",
            "backup_name",
            "backup_path",
            "backup_sha256",
            "backup_mode",
            "backup_device",
            "backup_inode",
            "replacement_name",
            "replacement_path",
            "replacement_sha256",
            "replacement_mode",
            "replacement_device",
            "replacement_inode",
        }
        if set(document) != journal_keys or document.get("schema") != JOURNAL_SCHEMA:
            raise InputError("recovery journal has unknown or missing top-level fields")
        transaction_id = document.get("transaction_id")
        try:
            uuid.UUID(cast(str, transaction_id))
        except (TypeError, ValueError) as exc:
            raise InputError("recovery journal transaction id is malformed") from exc
        operation = document.get("operation")
        if operation != "migration-apply" and operation not in RUNTIME_OPERATIONS:
            raise InputError("recovery journal operation is unsupported")
        phase = document.get("phase")
        if phase not in {"staging", "prepared", "committing", "committed"}:
            raise InputError("recovery journal phase is malformed")
        roots_raw = document.get("planning_roots")
        targets = document.get("ordered_targets")
        completed = document.get("completed_replacements")
        if (
            not isinstance(roots_raw, list)
            or not roots_raw
            or not all(isinstance(value, str) for value in roots_raw)
            or not isinstance(targets, list)
            or not targets
            or not isinstance(completed, list)
            or not all(isinstance(value, int) for value in completed)
        ):
            raise InputError("recovery journal roots, targets, or progress are malformed")
        if completed != list(range(len(completed))) or any(value >= len(targets) for value in completed):
            raise InputError("recovery journal progress is not an ordered prefix")
        if phase in {"staging", "prepared"} and completed:
            raise InputError(f"{phase} recovery journal cannot have completed replacements")
        if phase == "committed" and completed != list(range(len(targets))):
            raise InputError("committed recovery journal progress is incomplete")

        plan_path = _absolute_path_field(document, "plan_path")
        plan_raw = _safe_read_bytes(plan_path)
        if _sha256(plan_raw) != document.get("plan_sha256"):
            raise InputError("recovery journal plan digest mismatch")
        plan = _decode_json(plan_raw, plan_path)
        if operation == "migration-apply":
            _validate_plan_schema(plan)
            planning_roots = [Path(value) for value in plan["planning_roots"]]
            writes = plan["writes"]
            if document.get("plan_payload_sha256") != plan["payload_sha256"]:
                raise InputError("recovery journal plan payload digest mismatch")
            if document.get("input_set_sha256") != plan["input_set_sha256"]:
                raise InputError("recovery journal input-set digest mismatch")
            _validate_writes(writes, planning_roots, check_paths=False)
        else:
            writes, planning_roots = _validate_runtime_request(
                plan, cast(str, operation), check_sources=False, check_paths=False
            )
            if document.get("plan_payload_sha256") != plan["payload_sha256"]:
                raise InputError("recovery journal request payload digest mismatch")
            if document.get("input_set_sha256") != plan["input_set_sha256"]:
                raise InputError("recovery journal request input-set digest mismatch")
        if roots_raw != [str(path) for path in planning_roots]:
            raise InputError("recovery journal planning-root projection mismatch")
        if len(targets) != len(writes):
            raise InputError("recovery journal target count does not match the bound plan")

        normalized: set[str] = {_normalized(plan_path)}
        for index, (raw_target, write) in enumerate(zip(targets, writes)):
            if not isinstance(raw_target, dict) or set(raw_target) != target_keys:
                raise InputError(f"recovery journal target {index} has unknown or missing fields")
            target = cast(dict[str, Any], raw_target)
            path = Path(write["path"])
            parent_path = path.parent
            expected_replacement_name = f".{path.name}.{transaction_id}.replacement"
            expected_backup_name = f".{path.name}.{transaction_id}.backup"
            expected = {
                "path": str(path),
                "name": path.name,
                "parent_path": str(parent_path),
                "original_exists": write["source_exists"],
                "original_sha256": write["source_sha256"],
                "original_device": write["source_device"],
                "original_inode": write["source_inode"],
                "original_mode": write["source_mode"],
                "backup_name": expected_backup_name if write["source_exists"] else None,
                "backup_path": str(parent_path / expected_backup_name) if write["source_exists"] else None,
                "backup_sha256": write["source_sha256"],
                "backup_mode": write["source_mode"],
                "replacement_name": expected_replacement_name,
                "replacement_path": str(parent_path / expected_replacement_name),
                "replacement_sha256": write["replacement_sha256"],
                "replacement_mode": write["source_mode"] if write["source_exists"] else 0o600,
            }
            for key, value in expected.items():
                if target.get(key) != value:
                    raise InputError(f"recovery journal target projection mismatch: {path}: {key}")
            if not all(isinstance(target.get(key), int) and target[key] >= 0 for key in ("parent_device", "parent_inode")):
                raise InputError(f"recovery journal parent identity is malformed: {path}")
            for prefix, required in (("backup", write["source_exists"]), ("replacement", True)):
                artifact_identity = (target.get(f"{prefix}_device"), target.get(f"{prefix}_inode"))
                identity_is_bound = all(
                    isinstance(value, int) and value >= 0 for value in artifact_identity
                )
                identity_is_unbound = artifact_identity == (None, None)
                if required and phase != "staging" and not identity_is_bound:
                    raise InputError(f"recovery journal {prefix} identity is malformed: {path}")
                if required and phase == "staging" and not (
                    identity_is_bound or identity_is_unbound
                ):
                    raise InputError(f"recovery journal {prefix} identity is malformed: {path}")
                if not required and artifact_identity != (None, None):
                    raise InputError(f"recovery journal absent {prefix} has identity values: {path}")
            if path.name not in {"session.json", "sessions.index.json", "sessions.active-wake.json"}:
                raise InputError(f"recovery journal target basename is unsupported: {path}")
            if not any(_is_below(path, root) for root in planning_roots):
                raise InputError(f"recovery journal target escapes planning roots: {path}")
            for artifact in (
                path,
                Path(target["replacement_path"]),
                Path(target["backup_path"]) if target["backup_path"] is not None else None,
            ):
                if artifact is None:
                    continue
                norm = _normalized(artifact)
                if norm in normalized:
                    raise InputError(f"duplicate recovery journal path: {artifact}")
                normalized.add(norm)
        return dict(document)
    except ApplyError:
        raise
    except (MigrationError, OSError, KeyError, TypeError, ValueError) as exc:
        raise ApplyError(f"malformed or substituted recovery journal: {exc}") from exc


def capture_evidence(
    inventory_path: Path, reviewed_inventory_sha256: str, output_path: Path
) -> None:
    raw = _safe_read_bytes(inventory_path)
    if _sha256(raw) != reviewed_inventory_sha256.lower():
        raise InputError("reviewed inventory SHA-256 mismatch")
    inventory = _decode_json(raw, inventory_path)
    context = _validate_inventory(inventory, inventory_path)
    _validate_plan_destination(
        output_path,
        context["planning_roots"],
        context["manifest_paths"] + context["index_paths"] + [inventory_path],
        allow_inside_planning=True,
    )
    prs: dict[str, Any] = {}
    for candidate in sorted(inventory["migration_cohort"], key=lambda row: row["pr_url"]):
        pr_url = candidate.get("pr_url")
        if not isinstance(pr_url, str) or not pr_url or pr_url in prs:
            continue
        command = [
            "gh",
            "pr",
            "view",
            "--json",
            PR_PROVIDER_JSON_SELECTOR,
            "--",
            pr_url,
        ]
        payload = _run_json_command(command)
        capture: dict[str, Any] = {
            "provider": _capture_record(command, payload),
            "merge_commit": None,
            "merge_method": None,
            "branch_out": None,
        }
        manifest = context["documents"].get(Path(candidate["manifest_path"]))
        persisted_repo_root = manifest.get("repo_root") if isinstance(manifest, dict) else None
        repo_root = (
            Path(persisted_repo_root)
            if isinstance(persisted_repo_root, str) and Path(persisted_repo_root).is_absolute()
            else _manifest_repo_root(Path(candidate["manifest_path"]))
        )
        merge_sha = _nested(payload, "mergeCommit", "oid")
        if isinstance(merge_sha, str) and merge_sha:
            git_command = ["git", "-C", str(repo_root), "show", "-s", "--format=%H %P", merge_sha]
            git_payload = _run_text_command(git_command).strip()
            capture["merge_commit"] = _capture_record(git_command, git_payload)
        branch_out = candidate.get("branch_out_sha")
        if isinstance(branch_out, str) and branch_out:
            git_command = [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                "--verify",
                f"{branch_out}^{{commit}}",
            ]
            git_payload = _run_text_command(git_command).strip()
            capture["branch_out"] = _capture_record(
                git_command,
                {
                    "repository": str(repo_root),
                    "requested_oid": branch_out,
                    "resolved_oid": git_payload,
                },
            )
        prs[pr_url] = capture
    document = {
        "schema": PR_EVIDENCE_SCHEMA,
        "reviewed_inventory_sha256": reviewed_inventory_sha256.lower(),
        "prs": prs,
    }
    try:
        _atomic_write_bytes(output_path, _json_bytes(document))
    except OSError as exc:
        raise InputError(f"cannot write evidence {output_path}: {exc}") from exc


def _validate_inventory(inventory: Mapping[str, Any], inventory_path: Path) -> dict[str, Any]:
    if inventory.get("schema") != INVENTORY_SCHEMA:
        raise InputError(f"inventory must use schema {INVENTORY_SCHEMA}")
    counts = inventory.get("counts")
    manifests = inventory.get("manifests")
    index_files = inventory.get("index_files")
    index_rows = inventory.get("index_rows")
    cohort = inventory.get("migration_cohort")
    if not isinstance(counts, dict):
        raise InputError("inventory counts must be an object")
    for name, expected in EXPECTED_COUNTS.items():
        if counts.get(name) != expected:
            raise InputError(f"inventory count mismatch for {name}: expected {expected}")
    if not isinstance(manifests, list) or len(manifests) != EXPECTED_COUNTS["manifest_files"]:
        raise InputError("inventory manifests are incomplete")
    if not isinstance(index_files, list) or len(index_files) != EXPECTED_COUNTS["index_files"]:
        raise InputError("inventory index_files are incomplete")
    if not isinstance(index_rows, list) or len(index_rows) != EXPECTED_COUNTS["index_rows"]:
        raise InputError("inventory index_rows are incomplete")
    if not isinstance(cohort, list) or len(cohort) != EXPECTED_COUNTS["migration_cohort"]:
        raise InputError("inventory migration_cohort is incomplete")
    _validate_classification_counts(counts, manifests, index_rows)

    documents: dict[Path, Any] = {}
    source_metadata: dict[Path, tuple[str, int, int]] = {}
    manifest_paths: list[Path] = []
    manifest_by_path: dict[str, Mapping[str, Any]] = {}
    source_inodes: set[tuple[int, int]] = set()
    for position, record in enumerate(manifests):
        if not isinstance(record, dict):
            raise InputError(f"malformed manifest inventory row {position}")
        path = _inventory_path(record, "path", "manifest")
        if path.name != "session.json":
            raise InputError(f"unexpected manifest basename: {path}")
        if str(path) in manifest_by_path:
            raise InputError(f"duplicate manifest path: {path}")
        raw, identity = _safe_read_with_identity(path)
        if identity in source_inodes:
            raise InputError(f"duplicate device/inode alias: {path}")
        source_inodes.add(identity)
        source_metadata[path] = (_sha256(raw), identity[0], identity[1])
        manifest_paths.append(path)
        manifest_by_path[str(path)] = record
        if record.get("readable") is True:
            document = _decode_json(raw, path)
            _compare_inventory_fields(document, record.get("fields"), f"manifest {path}")
            documents[path] = document
        elif record.get("readable") is False:
            try:
                json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                documents[path] = None
            else:
                raise InputError(f"inventory says readable manifest is malformed: {path}")
        else:
            raise InputError(f"manifest readable flag is malformed: {path}")

    index_paths: list[Path] = []
    index_by_path: dict[str, Mapping[str, Any]] = {}
    actual_locator_rows: dict[tuple[str, str], Mapping[str, Any]] = {}
    planning_roots: set[Path] = set()
    for position, record in enumerate(index_files):
        if not isinstance(record, dict):
            raise InputError(f"malformed index inventory row {position}")
        path = _inventory_path(record, "path", "index")
        if path.name != "sessions.index.json":
            raise InputError(f"unexpected source index basename: {path}")
        if str(path) in index_by_path:
            raise InputError(f"duplicate source index path: {path}")
        raw, identity = _safe_read_with_identity(path)
        if identity in source_inodes:
            raise InputError(f"duplicate device/inode alias: {path}")
        source_inodes.add(identity)
        document = _decode_json(raw, path)
        rows = _enumerate_index_rows(document)
        if record.get("row_count") != len(rows):
            raise InputError(f"source index row count mismatch: {path}")
        source_metadata[path] = (_sha256(raw), identity[0], identity[1])
        documents[path] = document
        index_paths.append(path)
        index_by_path[str(path)] = record
        planning_roots.add(_planning_root(path))
        for locator, row in rows:
            actual_locator_rows[(str(path), locator)] = row

    if len(actual_locator_rows) != EXPECTED_COUNTS["index_rows"]:
        raise InputError("source indexes do not contain exactly 152 unique rows")
    inventory_row_map: dict[tuple[str, str], Mapping[str, Any]] = {}
    for position, record in enumerate(index_rows):
        if not isinstance(record, dict):
            raise InputError(f"malformed index_rows row {position}")
        index_path = record.get("index_path")
        locator = record.get("row_locator")
        if not isinstance(index_path, str) or index_path not in index_by_path:
            raise InputError(f"index row references undeclared index: {index_path}")
        if not isinstance(locator, str) or not locator:
            raise InputError(f"index row has malformed locator at position {position}")
        key = (index_path, locator)
        if key in inventory_row_map:
            raise InputError(f"duplicate index row locator: {index_path} {locator}")
        actual = actual_locator_rows.get(key)
        if actual is None:
            raise InputError(f"index row locator does not resolve: {index_path} {locator}")
        _compare_inventory_fields(actual, record.get("fields"), f"index row {key}")
        linked = record.get("linked_manifest_path")
        if linked is not None and linked not in manifest_by_path:
            raise InputError(f"index row links an unenumerated manifest: {linked}")
        inventory_row_map[key] = record
    if set(inventory_row_map) != set(actual_locator_rows):
        raise InputError("inventory index_rows do not reconcile all source rows")

    planning_roots.update(_planning_root(path) for path in manifest_paths)
    roots = sorted(planning_roots, key=str)
    for path in manifest_paths:
        if not any(_is_below(path, root) for root in roots):
            raise InputError(f"manifest is outside every declared planning root: {path}")
    _reject_path_aliases(manifest_paths + index_paths)

    seen_cohort_paths: set[str] = set()
    seen_joins: set[tuple[str, str]] = set()
    seen_locators: set[tuple[str, str]] = set()
    for position, candidate in enumerate(cohort):
        if not isinstance(candidate, dict):
            raise InputError(f"malformed cohort row {position}")
        required_strings = ("manifest_path", "derived_session_manifest_path", "classification", "branch", "pr_url")
        for key in required_strings:
            if not isinstance(candidate.get(key), str) or not candidate[key]:
                raise InputError(f"cohort row {position} lacks {key}")
        path = candidate["manifest_path"]
        if path != candidate["derived_session_manifest_path"] or path not in manifest_by_path:
            raise InputError(f"cohort manifest does not reconcile: {path}")
        if path in seen_cohort_paths:
            raise InputError(f"duplicate cohort manifest: {path}")
        seen_cohort_paths.add(path)
        join = (candidate["pr_url"], candidate["branch"])
        if join in seen_joins:
            raise InputError(f"duplicate cohort PR/branch join: {join}")
        seen_joins.add(join)
        existing = candidate.get("existing_index_rows")
        if not isinstance(existing, list):
            raise InputError(f"cohort existing_index_rows is malformed: {path}")
        for locator in existing:
            if not isinstance(locator, dict):
                raise InputError(f"malformed cohort locator: {path}")
            raw_key = (locator.get("index_path"), locator.get("row_locator"))
            if not all(isinstance(value, str) and value for value in raw_key):
                raise InputError(f"cohort locator is incomplete: {path}")
            key = cast(tuple[str, str], raw_key)
            if key in seen_locators:
                raise InputError(f"cohort locator is reused: {key}")
            seen_locators.add(key)
            inventory_row = inventory_row_map.get(key)
            if inventory_row is None or inventory_row.get("linked_manifest_path") != path:
                raise InputError(f"cohort locator does not reconcile to manifest: {key}")
    if len(seen_cohort_paths) != EXPECTED_COUNTS["migration_cohort"]:
        raise InputError("cohort unique-manifest reconciliation failed")
    if len(seen_locators) != counts.get("migration_cohort_index_rows"):
        raise InputError("cohort index locator count mismatch")
    derived_cohort_counts = {
        "migration_cohort_base_branch_persisted_or_derived": sum(
            row.get("persisted_or_derived_base_branch") is not None for row in cohort
        ),
        "migration_cohort_distinct_manifests_already_indexed": sum(
            bool(row.get("existing_index_rows")) for row in cohort
        ),
        "migration_cohort_explicit_refusal": sum(
            bool(row.get("explicit_refusal_reasons")) for row in cohort
        ),
        "migration_cohort_fully_persisted": sum(
            row.get("fully_derivable_from_persisted_evidence") is True for row in cohort
        ),
        "migration_cohort_index_rows": len(seen_locators),
        "migration_cohort_trusted_pr_query_required": sum(
            bool(row.get("later_trusted_pr_query_requirements"))
            and not bool(row.get("explicit_refusal_reasons"))
            for row in cohort
        ),
    }
    for name, actual in derived_cohort_counts.items():
        if counts.get(name) != actual:
            raise InputError(f"cohort aggregate does not reconcile: {name}")

    return {
        "documents": documents,
        "source_metadata": source_metadata,
        "manifest_paths": manifest_paths,
        "index_paths": sorted(index_paths, key=str),
        "planning_roots": roots,
        "inventory_rows": inventory_row_map,
    }


def _plan_candidate(
    candidate: Mapping[str, Any],
    evidence_by_url: Mapping[str, Any],
    dispositions: Mapping[str, Mapping[str, Any]],
    resolutions: Mapping[tuple[str, str], Mapping[str, Any]],
    index_paths: list[Path],
    documents: Mapping[Path, Any],
    inventory_rows: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    manifest_path = Path(candidate["manifest_path"])
    identity = {
        "manifest_path": str(manifest_path),
        "ticket_id": candidate.get("ticket_id"),
        "branch": candidate.get("branch"),
        "pr_url": candidate.get("pr_url"),
    }
    try:
        manifest = documents.get(manifest_path)
        if not isinstance(manifest, dict):
            raise MigrationError("malformed-manifest")
        locator_rows = _resolve_candidate_locators(candidate, documents, inventory_rows)
        conflicts = _identity_conflicts(candidate, manifest, locator_rows, None)
        unresolved = _unresolved_conflicts(conflicts, candidate, locator_rows, resolutions)
        if unresolved:
            raise MigrationError("source-identity-conflict:" + ",".join(sorted(unresolved)))
        if manifest.get("closed_at"):
            return {**identity, "verdict": "excluded-history", "reason": "closed_at is authoritative"}

        refusal_reasons = candidate.get("explicit_refusal_reasons") or []
        disposition = dispositions.get(str(manifest_path))
        if refusal_reasons:
            if disposition is None:
                raise MigrationError("accepted-breakage-disposition-required")
            return {
                **identity,
                "verdict": "excluded-accepted-breakage",
                "reason": disposition["reason"],
            }
        if disposition is not None:
            raise MigrationError("disposition-not-allowed-for-provable-row")

        pr_url = _required_string(candidate, "pr_url")
        evidence_record = evidence_by_url.get(pr_url)
        if not isinstance(evidence_record, dict):
            raise MigrationError("missing-trusted-pr-evidence")
        evidence = _derive_and_validate_evidence(evidence_record)
        conflicts = _identity_conflicts(candidate, manifest, locator_rows, evidence)
        unresolved = _unresolved_conflicts(conflicts, candidate, locator_rows, resolutions)
        if unresolved:
            raise MigrationError("source-identity-conflict:" + ",".join(sorted(unresolved)))
        _validate_pr_identity(candidate, manifest, evidence)
        state = evidence["state"]
        if state == "CLOSED":
            return {
                **identity,
                "verdict": "excluded-closed-unmerged",
                "reason": "trusted PR state is CLOSED without merge",
            }
        canonical = _canonical_manifest(candidate, manifest, evidence, state, manifest_path)
        index_path = _select_index_path(manifest_path, candidate, index_paths)
        active_row = _canonical_index_row(canonical, manifest_path)
        return {
            **identity,
            "verdict": "migrated-open" if state == "OPEN" else "migrated-merged",
            "reason": "trusted provider/git capture accepted",
            "index_path": str(index_path),
            "pre_merge_base_sha": canonical["pre_merge_base_sha"],
            "_manifest": canonical,
            "_active_row": active_row,
        }
    except (MigrationError, OSError, json.JSONDecodeError) as exc:
        return {**identity, "verdict": "refused", "reason": str(exc)}


def _derive_and_validate_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    provider = record.get("provider")
    if not isinstance(provider, dict):
        raise MigrationError("missing-provider-capture")
    payload = _validate_capture_record(provider, "provider")
    if not isinstance(payload, dict):
        raise MigrationError("malformed-provider-payload")
    pr_url = payload.get("url")
    provider_command = provider["command"]
    if (
        provider_command[:3] != ["gh", "pr", "view"]
        or len(provider_command) != 7
        or provider_command[3] != "--json"
        or provider_command[4] != PR_PROVIDER_JSON_SELECTOR
        or provider_command[5] != "--"
        or provider_command[6] != pr_url
    ):
        raise MigrationError("provider-capture-command-mismatch")
    raw_state = payload.get("state")
    merged_at = payload.get("mergedAt")
    merge_sha = _nested(payload, "mergeCommit", "oid")
    if raw_state == "OPEN":
        if merge_sha is not None or merged_at is not None:
            raise MigrationError("contradictory-pr-state-evidence")
        state = "OPEN"
    elif raw_state == "CLOSED":
        if merge_sha is not None or merged_at is not None:
            raise MigrationError("contradictory-pr-state-evidence")
        state = "CLOSED"
    elif raw_state == "MERGED":
        if merge_sha is None or merged_at is None:
            raise MigrationError("contradictory-pr-state-evidence")
        state = "MERGED"
    else:
        raise MigrationError("unsupported-pr-state")
    if state not in {"OPEN", "CLOSED", "MERGED"}:
        raise MigrationError("unsupported-pr-state")
    evidence = {
        "pr_url": pr_url,
        "state": state,
        "head_sha": payload.get("headRefOid"),
        "head_ref_name": payload.get("headRefName"),
        "base_ref_name": payload.get("baseRefName"),
        "base_ref_oid": payload.get("baseRefOid"),
        "merge_sha": merge_sha,
        "merged_at": merged_at,
        "merge_parents": [],
        "merge_shape": None,
        "merge_repository": None,
        "canonical_branch_out_sha": None,
        "branch_out_requested_oid": None,
        "branch_out_repository": None,
    }
    _require_full_oid(evidence["head_sha"], "pr-head-oid")
    _require_full_oid(evidence["base_ref_oid"], "current-base-oid")
    if not all(isinstance(evidence[key], str) and evidence[key] for key in ("pr_url", "head_ref_name", "base_ref_name")):
        raise MigrationError("provider-identity-field-missing")
    merge_capture = record.get("merge_commit")
    merge_method_capture = record.get("merge_method")
    if state in {"OPEN", "CLOSED"}:
        if (
            merge_sha is not None
            or merged_at is not None
            or merge_capture is not None
            or merge_method_capture is not None
        ):
            raise MigrationError("contradictory-pr-state-evidence")
    else:
        _require_full_oid(merge_sha, "merge-oid")
        if not isinstance(merged_at, str) or not merged_at:
            raise MigrationError("missing-merged-at")
        if not isinstance(merge_capture, dict):
            raise MigrationError("missing-merge-commit-capture")
        merge_text = _validate_capture_record(merge_capture, "merge-commit")
        if not isinstance(merge_text, str):
            raise MigrationError("malformed-merge-commit-capture")
        parts = merge_text.strip().split()
        merge_command = merge_capture["command"]
        if (
            merge_command[:1] != ["git"]
            or "-C" not in merge_command
            or "show" not in merge_command
            or merge_command[-1] != merge_sha
        ):
            raise MigrationError("merge-commit-capture-command-mismatch")
        if not parts or parts[0] != merge_sha:
            raise MigrationError("merge-commit-capture-oid-mismatch")
        parents = parts[1:]
        for parent in parents:
            _require_full_oid(parent, "merge-parent")
        if len(parents) == 2 and parents[1] == evidence["head_sha"]:
            shape = "MERGE"
        elif len(parents) == 1:
            method = _validate_merge_method_capture(
                merge_method_capture,
                cast(str, pr_url),
                cast(str, merge_sha),
                cast(str, evidence["head_sha"]),
            )
            if method != "SQUASH" or merge_sha == evidence["head_sha"]:
                raise MigrationError("ambiguous-pre-merge-base")
            shape = "SQUASH"
        else:
            raise MigrationError("ambiguous-pre-merge-base")
        evidence["merge_parents"] = parents
        evidence["merge_shape"] = shape
        evidence["merge_repository"] = merge_command[merge_command.index("-C") + 1]
    branch_capture = record.get("branch_out")
    if branch_capture is not None:
        branch_payload = _validate_capture_record(branch_capture, "branch-out")
        if not isinstance(branch_payload, dict):
            raise MigrationError("malformed-branch-out-capture")
        resolved = branch_payload.get("resolved_oid")
        requested = branch_payload.get("requested_oid")
        repository = branch_payload.get("repository")
        _require_full_oid(resolved, "branch-out-oid")
        if not isinstance(resolved, str):
            raise MigrationError("branch-out-evidence-mismatch")
        if not isinstance(requested, str) or not resolved.startswith(requested.lower()):
            raise MigrationError("branch-out-evidence-mismatch")
        if not isinstance(repository, str) or not Path(repository).is_absolute():
            raise MigrationError("branch-out-repository-missing")
        branch_command = branch_capture["command"]
        if (
            branch_command[:3] != ["git", "-C", repository]
            or "rev-parse" not in branch_command
            or branch_command[-1] != f"{requested}^{{commit}}"
        ):
            raise MigrationError("branch-out-capture-command-mismatch")
        evidence["canonical_branch_out_sha"] = resolved.lower()
        evidence["branch_out_requested_oid"] = requested.lower()
        evidence["branch_out_repository"] = repository
    return evidence


def _validate_capture_record(record: Mapping[str, Any], label: str) -> Any:
    command = record.get("command")
    captured_at = record.get("captured_at")
    payload = record.get("payload")
    digest = record.get("payload_sha256")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise MigrationError(f"{label}-capture-command-missing")
    if not isinstance(captured_at, str) or not captured_at:
        raise MigrationError(f"{label}-capture-time-missing")
    if digest != _sha256(_canonical_json_bytes(payload)):
        raise MigrationError(f"{label}-capture-digest-mismatch")
    return payload


def _validate_merge_method_capture(
    record: Any, pr_url: str, merge_sha: str, head_sha: str
) -> str:
    if not isinstance(record, dict) or set(record) != MERGE_METHOD_CAPTURE_KEYS:
        raise MigrationError("missing-or-malformed-merge-method-capture")
    if record.get("source") != "github-merge-operation-response":
        raise MigrationError("unsupported-merge-method-capture-source")
    payload = _validate_capture_record(record, "merge-method")
    if not isinstance(payload, dict) or set(payload) != MERGE_METHOD_PAYLOAD_KEYS:
        raise MigrationError("malformed-merge-method-payload")
    command = record["command"]
    parsed = urlparse(pr_url)
    path_parts = parsed.path.strip("/").split("/")
    if parsed.netloc != "github.com" or len(path_parts) != 4 or path_parts[2] != "pull":
        raise MigrationError("merge-method-capture-pr-url-mismatch")
    endpoint = f"repos/{path_parts[0]}/{path_parts[1]}/pulls/{path_parts[3]}/merge"
    if len(command) != 9 or command[:5] != ["gh", "api", "--method", "PUT", endpoint]:
        raise MigrationError("merge-method-capture-command-mismatch")
    fields = {command[6], command[8]} if command[5] == command[7] == "-f" else set()
    method_fields = [value for value in fields if value.startswith("merge_method=")]
    if fields - set(method_fields) != {f"sha={head_sha}"} or len(method_fields) != 1:
        raise MigrationError("merge-method-capture-command-mismatch")
    if payload.get("merged") is not True or payload.get("sha") != merge_sha:
        raise MigrationError("merge-method-capture-identity-mismatch")
    if not isinstance(payload.get("message"), str) or not payload["message"]:
        raise MigrationError("malformed-merge-method-payload")
    method = method_fields[0].partition("=")[2].upper()
    if method not in {"MERGE", "SQUASH", "REBASE"}:
        raise MigrationError("unsupported-merge-method-evidence")
    return cast(str, method)


def _validate_pr_identity(
    candidate: Mapping[str, Any], manifest: Mapping[str, Any], evidence: Mapping[str, Any]
) -> None:
    pr_url = _required_string(candidate, "pr_url")
    if evidence.get("pr_url") != pr_url:
        raise MigrationError("pr-url-mismatch")
    branch = _required_string(candidate, "branch")
    if evidence.get("head_ref_name") != branch:
        raise MigrationError("pr-head-ref-mismatch")
    persisted_head = candidate.get("persisted_head_sha") or manifest.get("draft_pr_head_sha")
    if not _oid_values_compatible(persisted_head, evidence.get("head_sha")):
        raise MigrationError("pr-head-oid-mismatch")
    persisted_base = candidate.get("persisted_or_derived_base_branch") or manifest.get("base_branch")
    if persisted_base is not None and evidence.get("base_ref_name") != persisted_base:
        raise MigrationError("pr-base-ref-mismatch")
    expected_repository = manifest.get("repo_root")
    if not isinstance(expected_repository, str) or not Path(expected_repository).is_absolute():
        expected_repository = str(_manifest_repo_root(Path(candidate["manifest_path"])))
    if evidence.get("state") == "MERGED" and evidence.get("merge_repository") != expected_repository:
        raise MigrationError("merge-commit-repository-mismatch")


def _canonical_manifest(
    candidate: Mapping[str, Any],
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    state: str,
    manifest_path: Path,
) -> dict[str, Any]:
    ticket_id = candidate.get("ticket_id")
    ticket_system = candidate.get("ticket_system")
    if not isinstance(ticket_id, str) or not ticket_id:
        raise MigrationError("missing-ticket-id")
    if ticket_system not in SUPPORTED_TICKET_SYSTEMS:
        raise MigrationError("unsupported-ticket-system")
    branch_out_sha = _canonical_branch_out(candidate, manifest, evidence)
    result = copy.deepcopy(dict(manifest))
    for key in RETIRED_KEYS:
        result.pop(key, None)
    result.update(
        {
            "ticket_id": ticket_id,
            "ticket_system": ticket_system,
            "branch": evidence["head_ref_name"],
            "base_branch": evidence["base_ref_name"],
            "branch_out_sha": branch_out_sha,
            "draft_pr_url": evidence["pr_url"],
            "draft_pr_head_sha": evidence["head_sha"],
            "session_manifest_path": str(manifest_path),
        }
    )
    result.setdefault("pr_open_base_sha", None)
    persisted_pre_merge = candidate.get("persisted_or_derived_pre_merge_base_sha")
    manifest_pre_merge = manifest.get("pre_merge_base_sha")
    if state == "OPEN":
        if persisted_pre_merge not in {None, ""} or manifest_pre_merge not in {None, ""}:
            raise MigrationError("open-row-has-frozen-pre-merge-base")
        result.update({"pre_merge_base_sha": None, "merge_sha": None, "merged_at": None})
    else:
        merge_sha = evidence["merge_sha"]
        persisted_merge = candidate.get("merge_sha") or manifest.get("merge_sha")
        if persisted_merge is not None and persisted_merge != merge_sha:
            raise MigrationError("pr-merge-oid-mismatch")
        pre_merge = evidence["merge_parents"][0]
        for value in (persisted_pre_merge, manifest_pre_merge):
            if value not in {None, ""} and value != pre_merge:
                raise MigrationError("persisted-pre-merge-base-conflict")
        result.update(
            {
                "pre_merge_base_sha": pre_merge,
                "merge_sha": merge_sha,
                "merged_at": evidence["merged_at"],
            }
        )
    return result


def _canonical_branch_out(
    candidate: Mapping[str, Any], manifest: Mapping[str, Any], evidence: Mapping[str, Any]
) -> str:
    candidate_value = candidate.get("branch_out_sha")
    manifest_value = manifest.get("branch_out_sha")
    if candidate_value != manifest_value:
        raise MigrationError("branch-out-candidate-manifest-mismatch")
    if not isinstance(candidate_value, str) or not candidate_value:
        raise MigrationError("missing-branch-out-identity")
    supplied = evidence.get("canonical_branch_out_sha")
    if (
        evidence.get("branch_out_requested_oid") != candidate_value.lower()
        or not isinstance(supplied, str)
        or not supplied.startswith(candidate_value.lower())
    ):
        raise MigrationError("branch-out-requires-trusted-repository-resolution")
    expected_repository = manifest.get("repo_root")
    if not isinstance(expected_repository, str) or not Path(expected_repository).is_absolute():
        expected_repository = str(_manifest_repo_root(Path(candidate["manifest_path"])))
    if evidence.get("branch_out_repository") != expected_repository:
        raise MigrationError("branch-out-repository-mismatch")
    return supplied


def _canonical_index_row(manifest: Mapping[str, Any], manifest_path: Path) -> dict[str, Any]:
    for key in ("worktree_path", "planning_dir"):
        value = manifest.get(key)
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise MigrationError(f"missing-or-nonabsolute-{key}")
    row = {
        "ticket_id": manifest["ticket_id"],
        "ticket_system": manifest["ticket_system"],
        "branch": manifest["branch"],
        "base_branch": manifest["base_branch"],
        "branch_out_sha": manifest["branch_out_sha"],
        "draft_pr_url": manifest["draft_pr_url"],
        "draft_pr_number": manifest.get("draft_pr_number"),
        "draft_pr_head_sha": manifest["draft_pr_head_sha"],
        "pr_open_base_sha": manifest.get("pr_open_base_sha"),
        "pre_merge_base_sha": manifest.get("pre_merge_base_sha"),
        "merge_sha": manifest.get("merge_sha"),
        "merged_at": manifest.get("merged_at"),
        "session_manifest_path": str(manifest_path),
        "worktree_path": manifest["worktree_path"],
        "planning_dir": manifest["planning_dir"],
    }
    if set(row) != ACTIVE_ROW_KEYS:
        raise MigrationError("internal-active-row-schema-mismatch")
    return row


def _resolve_candidate_locators(
    candidate: Mapping[str, Any],
    documents: Mapping[Path, Any],
    inventory_rows: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[tuple[tuple[str, str], Mapping[str, Any]]]:
    result = []
    for locator in candidate.get("existing_index_rows", []):
        key = (locator["index_path"], locator["row_locator"])
        if key not in inventory_rows:
            raise MigrationError("candidate-index-locator-not-in-reviewed-inventory")
        row = _resolve_locator(documents[Path(key[0])], key[1])
        result.append((key, row))
    return result


def _identity_conflicts(
    candidate: Mapping[str, Any],
    manifest: Mapping[str, Any],
    locator_rows: list[tuple[tuple[str, str], Mapping[str, Any]]],
    evidence: Mapping[str, Any] | None,
) -> list[tuple[tuple[str, str] | None, str]]:
    sources: list[tuple[tuple[str, str] | None, Mapping[str, Any]]] = [
        (None, manifest),
        *locator_rows,
    ]
    expected = {
        "manifest_path": candidate.get("manifest_path"),
        "ticket_id": candidate.get("ticket_id"),
        "ticket_system": candidate.get("ticket_system"),
        "branch": candidate.get("branch"),
        "pr_url": candidate.get("pr_url"),
        "head_sha": candidate.get("persisted_head_sha"),
        "base_branch": candidate.get("persisted_or_derived_base_branch"),
    }
    if evidence is not None:
        expected.update(
            {
                "branch": evidence.get("head_ref_name"),
                "pr_url": evidence.get("pr_url"),
                "head_sha": evidence.get("head_sha"),
                "base_branch": evidence.get("base_ref_name"),
            }
        )
    conflicts: list[tuple[tuple[str, str] | None, str]] = []
    for locator, source in sources:
        actual = {
            "manifest_path": _row_manifest_path(source) if locator is not None else candidate.get("manifest_path"),
            "ticket_id": source.get("ticket_id"),
            "ticket_system": source.get("ticket_system"),
            "branch": source.get("branch"),
            "pr_url": source.get("draft_pr_url") or source.get("pr_url"),
            "head_sha": source.get("draft_pr_head_sha") or source.get("head_sha") or source.get("pr_head_sha"),
            "base_branch": source.get("base_branch") or _clean_base(source.get("base")),
        }
        for field, expected_value in expected.items():
            actual_value = actual[field]
            if expected_value is None:
                continue
            if actual_value is None:
                if locator is None and field in {
                    "ticket_id",
                    "ticket_system",
                    "branch",
                    "pr_url",
                    "head_sha",
                }:
                    conflicts.append((locator, field))
                continue
            compatible = (
                _oid_values_compatible(actual_value, expected_value)
                if field == "head_sha"
                else actual_value == expected_value
            )
            if not compatible:
                conflicts.append((locator, field))
    return conflicts


def _unresolved_conflicts(
    conflicts: list[tuple[tuple[str, str] | None, str]],
    candidate: Mapping[str, Any],
    locator_rows: list[tuple[tuple[str, str], Mapping[str, Any]]],
    resolutions: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[str]:
    unresolved = []
    rows = dict(locator_rows)
    for locator, field in conflicts:
        if locator is None:
            unresolved.append(f"manifest:{field}")
            continue
        resolution = resolutions.get(locator)
        if resolution is None or not _resolution_matches(resolution, candidate, rows[locator]):
            unresolved.append(f"{locator[1]}:{field}")
    return unresolved


def _resolution_matches(
    resolution: Mapping[str, Any], candidate: Mapping[str, Any], source_row: Mapping[str, Any]
) -> bool:
    retained = resolution.get("retained_identity")
    if not isinstance(retained, dict):
        return False
    expected = {
        "manifest_path": candidate.get("manifest_path"),
        "ticket_id": candidate.get("ticket_id"),
        "ticket_system": candidate.get("ticket_system"),
        "branch": candidate.get("branch"),
        "pr_url": candidate.get("pr_url"),
        "head_sha": candidate.get("persisted_head_sha"),
        "base_branch": candidate.get("persisted_or_derived_base_branch"),
    }
    return retained == expected and resolution.get("discarded_row_sha256") == _sha256(
        _canonical_json_bytes(source_row)
    )


def _validate_dispositions(
    document: Mapping[str, Any], cohort: list[Mapping[str, Any]]
) -> dict[str, Mapping[str, Any]]:
    if document.get("schema") != DISPOSITION_SCHEMA or not isinstance(document.get("dispositions"), list):
        raise InputError(f"dispositions must use schema {DISPOSITION_SCHEMA}")
    refusal_paths = {
        item.get("manifest_path") for item in cohort if item.get("explicit_refusal_reasons")
    }
    result: dict[str, Mapping[str, Any]] = {}
    for item in document["dispositions"]:
        if not isinstance(item, dict):
            raise InputError("malformed cutover disposition")
        path = item.get("manifest_path")
        if not isinstance(path, str) or path not in refusal_paths or path in result:
            raise InputError(f"disposition path is not one unique exact refusal path: {path}")
        if item.get("accepted_breakage") is not True or item.get("owner") != "manager":
            raise InputError(f"disposition lacks manager-owned accepted-breakage marker: {path}")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise InputError(f"disposition lacks reason: {path}")
        result[path] = item
    return result


def _validate_conflict_resolutions(
    document: Mapping[str, Any], cohort: list[Mapping[str, Any]]
) -> dict[tuple[str, str], Mapping[str, Any]]:
    if document.get("schema") != CONFLICT_RESOLUTION_SCHEMA or not isinstance(document.get("resolutions"), list):
        raise InputError(f"conflict resolutions must use schema {CONFLICT_RESOLUTION_SCHEMA}")
    valid_locators = {
        (row["index_path"], row["row_locator"])
        for candidate in cohort
        for row in candidate.get("existing_index_rows", [])
    }
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in document["resolutions"]:
        if not isinstance(item, dict):
            raise InputError("malformed conflict resolution")
        raw_key = (item.get("index_path"), item.get("row_locator"))
        if not all(isinstance(value, str) and value for value in raw_key):
            raise InputError(f"conflict resolution locator is malformed: {raw_key}")
        key = cast(tuple[str, str], raw_key)
        if key not in valid_locators or key in result:
            raise InputError(f"conflict resolution locator is not unique and reviewed: {key}")
        if item.get("conflict_resolution") is not True or item.get("owner") != "manager":
            raise InputError(f"conflict resolution lacks manager ownership: {key}")
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise InputError(f"conflict resolution lacks reason: {key}")
        if not isinstance(item.get("discarded_row_sha256"), str):
            raise InputError(f"conflict resolution lacks discarded row digest: {key}")
        result[key] = item
    return result


def runtime_source_identity(path: Path) -> dict[str, Any]:
    if not path.exists() and not path.is_symlink():
        _assert_safe_output(path)
        return {"exists": False, "sha256": None, "device": None, "inode": None, "mode": None}
    raw, identity = _safe_read_with_identity(path)
    return {
        "exists": True,
        "sha256": _sha256(raw),
        "device": identity[0],
        "inode": identity[1],
        "mode": os.stat(path, follow_symlinks=False).st_mode & 0o777,
    }


def runtime_request_digests(request: Mapping[str, Any]) -> tuple[str, str]:
    input_binding = {
        key: request.get(key)
        for key in (
            "operation",
            "planning_root",
            "manifest_path",
            "index_path",
            "row_identity",
            "sources",
        )
    }
    input_set_sha256 = _sha256(_canonical_json_bytes(input_binding))
    unsigned = dict(request)
    unsigned["input_set_sha256"] = input_set_sha256
    unsigned.pop("payload_sha256", None)
    return input_set_sha256, _sha256(_canonical_json_bytes(unsigned))


def _validate_runtime_request(
    request: Mapping[str, Any],
    expected_operation: str | None,
    *,
    check_sources: bool,
    check_paths: bool = True,
) -> tuple[list[dict[str, Any]], list[Path]]:
    if set(request) != RUNTIME_REQUEST_KEYS or request.get("schema") != RUNTIME_REQUEST_SCHEMA:
        raise InputError(f"runtime request must use closed schema {RUNTIME_REQUEST_SCHEMA}")
    operation = request.get("operation")
    if operation not in RUNTIME_OPERATIONS or (
        expected_operation is not None and operation != expected_operation
    ):
        raise InputError("runtime request operation mismatch")
    expected_input_digest, expected_payload_digest = runtime_request_digests(request)
    if request.get("input_set_sha256") != expected_input_digest:
        raise InputError("runtime request input-set digest mismatch")
    if request.get("payload_sha256") != expected_payload_digest:
        raise InputError("runtime request payload digest mismatch")

    planning_root = _absolute_path_field(request, "planning_root")
    manifest_path = _absolute_path_field(request, "manifest_path")
    index_path = _absolute_path_field(request, "index_path")
    if (
        planning_root.name != "planning"
        or manifest_path.name != "session.json"
        or manifest_path.parent.parent != planning_root
        or index_path != planning_root / "sessions.active-wake.json"
    ):
        raise InputError("runtime manifest, planning root, and active index are not canonical")
    if check_paths:
        _validate_runtime_directory(planning_root, "planning root")
        _validate_runtime_directory(manifest_path.parent, "session planning directory")
        _assert_safe_output(manifest_path)
        _assert_safe_output(index_path)
        _reject_path_aliases([manifest_path, index_path], allow_missing=True)

    sources = request.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"manifest", "index"}:
        raise InputError("runtime request sources must contain exact manifest and index identities")
    source_records: dict[str, Mapping[str, Any]] = {}
    for name, path in (("manifest", manifest_path), ("index", index_path)):
        record = sources.get(name)
        if not isinstance(record, dict) or set(record) != SOURCE_IDENTITY_KEYS:
            raise InputError(f"runtime {name} source identity has unknown or missing fields")
        _validate_source_record(record, name)
        if check_sources and runtime_source_identity(path) != record:
            raise ApplyError(f"stale runtime {name} source identity: {path}")
        source_records[name] = record

    replacement_manifest = request.get("replacement_manifest")
    replacement_index = request.get("replacement_index")
    if not isinstance(replacement_manifest, dict) or not isinstance(replacement_index, dict):
        raise InputError("runtime replacements must be JSON objects")
    row_identity = request.get("row_identity")
    if operation == "phase0-init":
        if row_identity is not None:
            raise InputError("phase0-init row_identity must be null")
    else:
        _validate_row_identity(row_identity, manifest_path)

    source_manifest: dict[str, Any] | None = None
    source_index: dict[str, Any] = {"sessions": []}
    if check_sources and source_records["manifest"]["exists"]:
        source_manifest = _decode_json(_safe_read_bytes(manifest_path), manifest_path)
    if check_sources and source_records["index"]["exists"]:
        source_index = _decode_json(_safe_read_bytes(index_path), index_path)
    if check_sources:
        _validate_runtime_projection(
            cast(str, operation),
            planning_root,
            manifest_path,
            source_manifest,
            source_index,
            replacement_manifest,
            replacement_index,
            cast(Mapping[str, Any] | None, row_identity),
        )

    writes = [
        _runtime_write(manifest_path, source_records["manifest"], replacement_manifest),
        _runtime_write(index_path, source_records["index"], replacement_index),
    ]
    _validate_writes(writes, [planning_root], check_paths=check_paths)
    return writes, [planning_root]


def _validate_runtime_projection(
    operation: str,
    planning_root: Path,
    manifest_path: Path,
    source_manifest: Mapping[str, Any] | None,
    source_index: Mapping[str, Any],
    replacement_manifest: Mapping[str, Any],
    replacement_index: Mapping[str, Any],
    row_identity: Mapping[str, Any] | None,
) -> None:
    _validate_runtime_manifest(replacement_manifest, manifest_path, planning_root)
    _validate_active_index_document(
        source_index,
        planning_root=planning_root,
        allow_uninitialized=True,
    )
    if operation == "phase0-init":
        if source_manifest is not None:
            raise InputError("phase0-init requires an absent manifest source")
        if any(replacement_manifest.get(key) is not None for key in ("draft_pr_url", "draft_pr_head_sha", "pre_merge_base_sha", "closed_at")):
            raise InputError("phase0-init manifest is not a pre-PR open session")
        expected_index = copy.deepcopy(dict(source_index))
        if expected_index == {"sessions": []}:
            expected_index["schema"] = ACTIVE_INDEX_SCHEMA
    else:
        if source_manifest is None:
            raise InputError(f"{operation} requires an existing manifest")
        _validate_active_index_document(
            source_index,
            planning_root=planning_root,
            allow_uninitialized=operation == "phase7-upsert",
        )
        changed = {
            key
            for key in set(source_manifest) | set(replacement_manifest)
            if source_manifest.get(key) != replacement_manifest.get(key)
        }
        if not changed <= RUNTIME_ALLOWED_MANIFEST_CHANGES[operation]:
            raise InputError(f"{operation} changes forbidden manifest fields: {sorted(changed)}")
        if not changed:
            raise InputError(f"{operation} must change the manifest")
        canonical_row = _canonical_index_row(replacement_manifest, manifest_path)
        if row_identity != _active_row_identity(canonical_row):
            raise InputError("runtime row identity does not match the replacement manifest")
        if operation == "phase7-upsert":
            if source_manifest.get("draft_pr_url") not in {None, ""}:
                raise InputError("phase7-upsert requires a pre-PR manifest")
            expected_index = _index_upsert_projection(
                source_index, canonical_row, cast(Mapping[str, Any], row_identity), require_existing=False
            )
        elif operation in {"phase9-update", "resumer-update"}:
            expected_index = _index_upsert_projection(
                source_index, canonical_row, cast(Mapping[str, Any], row_identity), require_existing=True
            )
        else:
            if not replacement_manifest.get("closed_at"):
                raise InputError("resumer-close requires final manifest closure")
            expected_index = _index_remove_projection(
                source_index, cast(Mapping[str, Any], row_identity)
            )
    if replacement_index != expected_index:
        raise InputError(f"{operation} replacement index is not the exact allowed projection")
    _validate_active_index_document(
        replacement_index,
        planning_root=planning_root,
        allow_uninitialized=False,
    )


def _validate_runtime_manifest(
    manifest: Mapping[str, Any], manifest_path: Path, planning_root: Path
) -> None:
    for key in (
        "ticket_id",
        "ticket_system",
        "branch",
        "base_branch",
        "branch_out_sha",
        "worktree_path",
        "planning_dir",
    ):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise InputError(f"runtime manifest lacks {key}")
    if manifest["ticket_system"] not in SUPPORTED_TICKET_SYSTEMS:
        raise InputError("runtime manifest has unsupported ticket_system")
    _require_full_oid(manifest["branch_out_sha"], "branch-out-oid")
    if manifest.get("session_manifest_path", str(manifest_path)) != str(manifest_path):
        raise InputError("runtime manifest path identity mismatch")
    if not Path(manifest["planning_dir"]).is_absolute() or not Path(manifest["worktree_path"]).is_absolute():
        raise InputError("runtime manifest planning/worktree paths must be absolute")
    if Path(manifest["planning_dir"]) != manifest_path.parent:
        raise InputError("runtime manifest planning_dir does not match its canonical parent")
    if manifest_path.parent.parent != planning_root:
        raise InputError("runtime manifest does not belong to the declared project planning root")


def _validate_active_index_document(
    document: Mapping[str, Any], *, planning_root: Path, allow_uninitialized: bool
) -> None:
    if allow_uninitialized and document == {"sessions": []}:
        return
    if set(document) - {"schema", "sessions", "reviewed_inventory_sha256", "source_index_path"}:
        raise InputError("runtime active index has unknown top-level fields")
    if document.get("schema") != ACTIVE_INDEX_SCHEMA:
        raise InputError("runtime active index schema mismatch")
    source_index_path = document.get("source_index_path")
    if source_index_path is not None:
        expected_source_index = planning_root / "sessions.index.json"
        if source_index_path != str(expected_source_index):
            raise InputError("runtime active index source path is cross-root or noncanonical")
        try:
            _assert_safe_existing(expected_source_index)
        except InputError as exc:
            raise InputError(
                f"runtime active index source path is not descriptor-safe: {exc}"
            ) from exc
    sessions = document.get("sessions")
    if not isinstance(sessions, list):
        raise InputError("runtime active index sessions must be an array")
    wake_joins: set[tuple[str, str]] = set()
    manifest_paths: set[str] = set()
    ticket_branches: set[tuple[str, str]] = set()
    for position, row in enumerate(sessions):
        if not isinstance(row, dict) or set(row) != ACTIVE_ROW_KEYS:
            raise InputError(f"runtime active row {position} has unknown or missing fields")
        for key in (
            "ticket_id",
            "ticket_system",
            "branch",
            "base_branch",
            "draft_pr_url",
            "session_manifest_path",
            "worktree_path",
            "planning_dir",
        ):
            if not isinstance(row.get(key), str) or not row[key]:
                raise InputError(f"runtime active row {position} lacks {key}")
        if row["ticket_system"] not in SUPPORTED_TICKET_SYSTEMS:
            raise InputError(f"runtime active row {position} has unsupported ticket_system")
        _require_full_oid(row.get("branch_out_sha"), "branch-out-oid")
        _require_full_oid(row.get("draft_pr_head_sha"), "pr-head-oid")
        for key in ("pr_open_base_sha", "pre_merge_base_sha", "merge_sha"):
            if row.get(key) is not None:
                _require_full_oid(row[key], key.replace("_", "-"))
        if (row.get("merge_sha") is None) != (row.get("merged_at") is None):
            raise InputError(f"runtime active row {position} has contradictory merge fields")
        row_manifest = _canonical_runtime_row_manifest(row, position, planning_root)
        wake_join = (row["draft_pr_url"], row["branch"])
        ticket_branch = (row["ticket_id"], row["branch"])
        if wake_join in wake_joins:
            raise InputError(f"runtime active row {position} duplicates a PR/branch wake join")
        if str(row_manifest) in manifest_paths:
            raise InputError(f"runtime active row {position} duplicates a manifest join")
        if ticket_branch in ticket_branches:
            raise InputError(f"runtime active row {position} duplicates a ticket/branch join")
        wake_joins.add(wake_join)
        manifest_paths.add(str(row_manifest))
        ticket_branches.add(ticket_branch)


def _index_upsert_projection(
    source_index: Mapping[str, Any],
    replacement_row: Mapping[str, Any],
    identity: Mapping[str, Any] | None,
    *,
    require_existing: bool,
) -> dict[str, Any]:
    result = copy.deepcopy(dict(source_index))
    sessions = result.setdefault("sessions", [])
    if not isinstance(sessions, list) or not all(isinstance(row, dict) for row in sessions):
        raise InputError("runtime index sessions must be an array of objects")
    matches = [index for index, row in enumerate(sessions) if identity is not None and _active_row_identity(row) == identity]
    if len(matches) > 1 or (require_existing and len(matches) != 1) or (not require_existing and matches):
        raise InputError("runtime active-row identity is missing or duplicated")
    if matches:
        sessions[matches[0]] = copy.deepcopy(dict(replacement_row))
    else:
        wake_join = (replacement_row.get("draft_pr_url"), replacement_row.get("branch"))
        manifest_path = replacement_row.get("session_manifest_path")
        ticket_branch = (replacement_row.get("ticket_id"), replacement_row.get("branch"))
        if any(
            (row.get("draft_pr_url"), row.get("branch")) == wake_join
            or row.get("session_manifest_path") == manifest_path
            or (row.get("ticket_id"), row.get("branch")) == ticket_branch
            for row in sessions
        ):
            raise InputError("runtime upsert collides with an existing active-row join")
        sessions.append(copy.deepcopy(dict(replacement_row)))
    if identity is not None:
        result["schema"] = ACTIVE_INDEX_SCHEMA
        sessions.sort(key=lambda row: (row["draft_pr_url"], row["branch"], row["ticket_id"], row["session_manifest_path"]))
    return result


def _index_remove_projection(
    source_index: Mapping[str, Any], identity: Mapping[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(dict(source_index))
    sessions = result.get("sessions")
    if not isinstance(sessions, list) or not all(isinstance(row, dict) for row in sessions):
        raise InputError("runtime active index sessions must be an array of objects")
    matches = [index for index, row in enumerate(sessions) if _active_row_identity(row) == identity]
    if len(matches) != 1:
        raise InputError("resumer-close requires one exact active row")
    sessions.pop(matches[0])
    return result


def _active_row_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in sorted(ROW_IDENTITY_KEYS)}


def _validate_row_identity(value: Any, manifest_path: Path) -> None:
    if not isinstance(value, dict) or set(value) != ROW_IDENTITY_KEYS:
        raise InputError("runtime row_identity has unknown or missing fields")
    if not all(isinstance(item, str) and item for item in value.values()):
        raise InputError("runtime row_identity fields must be non-empty strings")
    if value["session_manifest_path"] != str(manifest_path):
        raise InputError("runtime row_identity manifest path mismatch")


def _validate_source_record(record: Mapping[str, Any], name: str) -> None:
    exists = record.get("exists")
    if not isinstance(exists, bool):
        raise InputError(f"runtime {name} source exists flag is malformed")
    identity = (record.get("sha256"), record.get("device"), record.get("inode"), record.get("mode"))
    if exists:
        if (
            not isinstance(identity[0], str)
            or not FULL_OID_RE.fullmatch(identity[0])
            or not all(isinstance(value, int) and value >= 0 for value in identity[1:])
        ):
            raise InputError(f"runtime {name} source identity is malformed")
    elif any(value is not None for value in identity):
        raise InputError(f"runtime absent {name} source has identity values")


def _runtime_write(
    path: Path, source: Mapping[str, Any], replacement: Mapping[str, Any]
) -> dict[str, Any]:
    replacement_bytes = _json_bytes(replacement)
    return {
        "path": str(path),
        "source_exists": source["exists"],
        "source_sha256": source["sha256"],
        "source_device": source["device"],
        "source_inode": source["inode"],
        "source_mode": source["mode"],
        "replacement_sha256": _sha256(replacement_bytes),
        "replacement": copy.deepcopy(dict(replacement)),
    }


def _absolute_path_field(mapping: Mapping[str, Any], key: str) -> Path:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise InputError(f"runtime request lacks {key}")
    path = Path(value)
    if not path.is_absolute() or str(path) != os.path.normpath(str(path)):
        raise InputError(f"runtime request {key} must be normalized and absolute")
    return path


def _validate_runtime_directory(path: Path, label: str) -> None:
    try:
        parent = _open_held_parent(path)
        try:
            _verify_held_parent(parent)
        finally:
            os.close(parent["fd"])
    except ApplyError as exc:
        raise InputError(f"runtime {label} is not descriptor-safe: {path}: {exc}") from exc


def _canonical_runtime_row_manifest(
    row: Mapping[str, Any], position: int, planning_root: Path
) -> Path:
    manifest_value = row["session_manifest_path"]
    planning_value = row["planning_dir"]
    manifest_path = Path(manifest_value)
    planning_dir = Path(planning_value)
    if (
        not manifest_path.is_absolute()
        or str(manifest_path) != os.path.normpath(str(manifest_path))
        or not planning_dir.is_absolute()
        or str(planning_dir) != os.path.normpath(str(planning_dir))
        or manifest_path.name != "session.json"
        or manifest_path.parent != planning_dir
        or planning_dir.parent != planning_root
    ):
        raise InputError(f"runtime active row {position} has noncanonical planning paths")
    _validate_runtime_directory(planning_dir, f"active row {position} planning directory")
    try:
        _assert_safe_existing(manifest_path)
    except InputError as exc:
        raise InputError(
            f"runtime active row {position} manifest is not descriptor-safe: {manifest_path}: {exc}"
        ) from exc
    return manifest_path


def _validate_plan_schema(plan: Mapping[str, Any]) -> None:
    if plan.get("schema") != PLAN_SCHEMA or plan.get("mode") != "dry-run":
        raise InputError("apply requires a dry-run migration plan")
    supplied = plan.get("payload_sha256")
    unsigned = dict(plan)
    unsigned.pop("payload_sha256", None)
    if supplied != _sha256(_canonical_json_bytes(unsigned)):
        raise InputError("plan payload digest mismatch")
    for key in ("inputs", "writes", "planning_roots", "source_index_paths", "active_index_paths"):
        if not isinstance(plan.get(key), list if key != "inputs" else dict):
            raise InputError(f"plan {key} has the wrong schema")
    if not isinstance(plan.get("eligible"), bool):
        raise InputError("plan eligible flag is malformed")
    if not isinstance(plan.get("rows"), list):
        raise InputError("plan rows have the wrong schema")
    if not isinstance(plan.get("reviewed_inventory_sha256"), str) or not FULL_OID_RE.fullmatch(
        plan["reviewed_inventory_sha256"]
    ):
        raise InputError("plan reviewed inventory digest is malformed")
    inputs = plan["inputs"]
    if set(inputs) != {
        "inventory",
        "pr_evidence",
        "dispositions",
        "conflict_resolutions",
    }:
        raise InputError("plan input set is malformed")
    for name in ("inventory", "pr_evidence", "dispositions"):
        record = inputs[name]
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("path"), str)
            or not isinstance(record.get("sha256"), str)
        ):
            raise InputError(f"plan input is malformed: {name}")
    conflict_record = inputs["conflict_resolutions"]
    if conflict_record is not None and (
        not isinstance(conflict_record, dict)
        or not isinstance(conflict_record.get("path"), str)
        or not isinstance(conflict_record.get("sha256"), str)
    ):
        raise InputError("plan conflict-resolution input is malformed")
    if plan.get("validated_counts") != EXPECTED_COUNTS:
        raise InputError("plan aggregate counts are not the reviewed cutover counts")


def _verify_plan_inputs(plan: Mapping[str, Any]) -> None:
    inputs = plan["inputs"]
    if plan.get("input_set_sha256") != _sha256(_canonical_json_bytes(inputs)):
        raise InputError("plan input-set digest mismatch")
    for name, record in inputs.items():
        if record is None:
            continue
        if not isinstance(record, dict) or not isinstance(record.get("path"), str) or not isinstance(record.get("sha256"), str):
            raise InputError(f"malformed plan input: {name}")
        try:
            current = _sha256(_safe_read_bytes(Path(record["path"])))
        except MigrationError as exc:
            raise ApplyError(f"stale plan input {name}: {exc}") from exc
        if current != record["sha256"]:
            raise ApplyError(f"stale plan input digest: {name}")


def _validate_writes(
    writes: Any, planning_roots: list[Path], *, check_paths: bool = True
) -> None:
    if not isinstance(writes, list):
        raise InputError("plan writes must be an array")
    for root in planning_roots:
        if not root.is_absolute() or str(root) != os.path.normpath(str(root)) or root.name != "planning":
            raise InputError(f"planned planning root is not canonical: {root}")
    paths: list[Path] = []
    write_keys = {
        "path",
        "source_exists",
        "source_sha256",
        "source_device",
        "source_inode",
        "source_mode",
        "replacement_sha256",
        "replacement",
    }
    for index, write in enumerate(writes):
        if not isinstance(write, dict) or set(write) != write_keys:
            raise InputError(f"plan contains malformed write {index}")
        path_value = write.get("path")
        if not isinstance(path_value, str):
            raise InputError(f"plan write {index} lacks a path")
        path = Path(path_value)
        if path.name not in {"session.json", "sessions.index.json", "sessions.active-wake.json"}:
            raise InputError(f"planned target has an unsupported basename: {path}")
        if not any(_is_below(path, root) for root in planning_roots):
            raise InputError(f"planned target escapes reviewed planning roots: {path}")
        if check_paths:
            _assert_safe_output(path)
        replacement = write.get("replacement")
        if _sha256(_json_bytes(replacement)) != write.get("replacement_sha256"):
            raise InputError(f"replacement hash mismatch: {path}")
        if not isinstance(write.get("source_exists"), bool):
            raise InputError(f"source existence flag is malformed: {path}")
        source_values = (
            write.get("source_sha256"),
            write.get("source_device"),
            write.get("source_inode"),
            write.get("source_mode"),
        )
        if write["source_exists"]:
            if (
                not isinstance(source_values[0], str)
                or not FULL_OID_RE.fullmatch(source_values[0])
                or not all(isinstance(value, int) and value >= 0 for value in source_values[1:])
            ):
                raise InputError(f"source identity is malformed: {path}")
        elif any(value is not None for value in source_values):
            raise InputError(f"absent source has identity values: {path}")
        paths.append(path)
    if check_paths:
        _reject_path_aliases(paths, allow_missing=True)
    elif len({_normalized(path) for path in paths}) != len(paths):
        raise InputError("plan contains duplicate normalized target paths")


def _verify_source_identity(path: Path, write: Mapping[str, Any]) -> None:
    if write["source_exists"]:
        try:
            raw, identity = _safe_read_with_identity(path)
        except MigrationError as exc:
            raise ApplyError(f"stale source identity: {path}: {exc}") from exc
        if (
            _sha256(raw) != write["source_sha256"]
            or identity[0] != write["source_device"]
            or identity[1] != write["source_inode"]
        ):
            raise ApplyError(f"stale source identity: {path}")
    elif path.exists() or path.is_symlink():
        raise ApplyError(f"planned new target now exists: {path}")


def _select_index_path(manifest_path: Path, candidate: Mapping[str, Any], index_paths: list[Path]) -> Path:
    existing = {Path(item["index_path"]) for item in candidate.get("existing_index_rows", [])}
    if existing:
        if len(existing) != 1 or next(iter(existing)) not in index_paths:
            raise MigrationError("ambiguous-index-path")
        return next(iter(existing))
    candidates = [path for path in index_paths if _is_below(manifest_path, path.parent)]
    if not candidates:
        raise MigrationError("no-index-for-unindexed-live-manifest")
    return max(candidates, key=lambda path: len(path.parent.parts))


def _enumerate_index_rows(document: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    rows: list[tuple[str, Mapping[str, Any]]] = []
    for key in ("sessions", "rows"):
        value = document.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            raise InputError(f"index {key} must be an array")
        for index, row in enumerate(value):
            if not isinstance(row, dict):
                raise InputError(f"index locator {key}[{index}] is not an object")
            rows.append((f"{key}[{index}]", row))
    for key, value in document.items():
        if key not in INDEX_RESERVED_KEYS and isinstance(value, dict):
            rows.append((key, value))
    return rows


def _resolve_locator(document: Mapping[str, Any], locator: str) -> Mapping[str, Any]:
    match = LIST_LOCATOR_RE.fullmatch(locator)
    if match:
        values = document.get(match.group(1))
        index = int(match.group(2))
        if not isinstance(values, list) or index >= len(values) or not isinstance(values[index], dict):
            raise MigrationError("exact-index-row-locator-does-not-resolve")
        return values[index]
    value = document.get(locator)
    if locator in INDEX_RESERVED_KEYS or not isinstance(value, dict):
        raise MigrationError("exact-index-row-locator-does-not-resolve")
    return value


def _validate_classification_counts(
    counts: Mapping[str, Any], manifests: list[Any], index_rows: list[Any]
) -> None:
    manifest_counts = Counter(row.get("classification") for row in manifests if isinstance(row, dict))
    index_counts = Counter(row.get("classification") for row in index_rows if isinstance(row, dict))
    if dict(manifest_counts) != counts.get("manifest_classifications"):
        raise InputError("manifest classification aggregates do not reconcile")
    if dict(index_counts) != counts.get("index_row_classifications"):
        raise InputError("index-row classification aggregates do not reconcile")


def _compare_inventory_fields(actual: Mapping[str, Any], expected: Any, label: str) -> None:
    if not isinstance(expected, dict):
        raise InputError(f"{label} inventory fields are malformed")
    for key, value in expected.items():
        if actual.get(key) != value:
            raise InputError(f"{label} field changed: {key}")


def _inventory_path(record: Mapping[str, Any], key: str, label: str) -> Path:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise InputError(f"{label} path is malformed")
    path = Path(value)
    _assert_safe_existing(path)
    return path


def _planning_root(path: Path) -> Path:
    positions = [index for index, part in enumerate(path.parts) if part == "planning"]
    if not positions:
        raise InputError(f"path is outside a planning tree: {path}")
    return Path(*path.parts[: positions[0] + 1])


def _manifest_repo_root(manifest_path: Path) -> Path:
    planning_root = _planning_root(manifest_path)
    project_root = planning_root.parent
    for name in ("trunk", "repo"):
        candidate = project_root / name
        if candidate.is_dir():
            return candidate
    return project_root


def _validate_plan_destination(
    plan_path: Path,
    planning_roots: list[Path],
    protected_paths: list[Path],
    *,
    allow_inside_planning: bool = False,
) -> None:
    _assert_safe_output(plan_path)
    if not allow_inside_planning and any(_is_below(plan_path, root) for root in planning_roots):
        raise InputError(f"plan path is inside a managed planning tree: {plan_path}")
    _reject_cross_aliases([plan_path], protected_paths)


def _reject_cross_aliases(paths: list[Path], protected: list[Path]) -> None:
    protected_norm = {_normalized(path) for path in protected}
    protected_inodes = {_inode(path) for path in protected if path.exists()}
    for path in paths:
        if _normalized(path) in protected_norm:
            raise InputError(f"path aliases protected input or source: {path}")
        if path.exists() and _inode(path) in protected_inodes:
            raise InputError(f"path inode aliases protected input or source: {path}")


def _reject_path_aliases(paths: list[Path], *, allow_missing: bool = False) -> None:
    normalized: set[str] = set()
    inodes: set[tuple[int, int]] = set()
    for path in paths:
        if allow_missing:
            _assert_safe_output(path)
        else:
            _assert_safe_existing(path)
        norm = _normalized(path)
        if norm in normalized:
            raise InputError(f"duplicate normalized path: {path}")
        normalized.add(norm)
        if path.exists():
            inode = _inode(path)
            if inode in inodes:
                raise InputError(f"duplicate device/inode alias: {path}")
            inodes.add(inode)


def _assert_safe_existing(path: Path) -> None:
    if not path.is_absolute() or str(path) != os.path.normpath(str(path)):
        raise InputError(f"path must be normalized and absolute: {path}")
    _reject_symlink_components(path)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise InputError(f"path is missing: {path}: {exc}") from exc
    if resolved != path:
        raise InputError(f"path does not resolve to itself: {path}")
    if not path.is_file():
        raise InputError(f"path is not a regular file: {path}")


def _assert_safe_output(path: Path) -> None:
    if not path.is_absolute() or str(path) != os.path.normpath(str(path)):
        raise InputError(f"output path must be normalized and absolute: {path}")
    _reject_symlink_components(path.parent)
    if not path.parent.is_dir():
        raise InputError(f"output parent does not exist: {path.parent}")
    if path.exists() or path.is_symlink():
        _assert_safe_existing(path)


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return
        if os.path.islink(current):
            raise InputError(f"symlink path component is forbidden: {current}")
        if not current.exists() and metadata:
            raise InputError(f"unsafe path component: {current}")


def _safe_read_bytes(path: Path) -> bytes:
    raw, _ = _safe_read_with_identity(path)
    return raw


def _safe_read_with_identity(path: Path) -> tuple[bytes, tuple[int, int]]:
    _assert_safe_existing(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        current = os.lstat(path)
        if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
            raise InputError(f"path identity changed while opening: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read()
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise InputError(f"path changed while reading: {path}")
        return raw, (before.st_dev, before.st_ino)
    finally:
        os.close(descriptor)


def _open_held_parent(path: Path) -> dict[str, Any]:
    _reject_symlink_components(path)
    if not path.is_absolute() or str(path) != os.path.normpath(str(path)):
        raise InputError(f"parent path must be normalized and absolute: {path}")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ApplyError(f"cannot hold target parent {path}: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        current = os.lstat(path)
        if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            current.st_dev,
            current.st_ino,
        ):
            raise ApplyError(f"target parent identity changed while opening: {path}")
        return {
            "path": path,
            "fd": descriptor,
            "device": opened.st_dev,
            "inode": opened.st_ino,
        }
    except BaseException:
        os.close(descriptor)
        raise


def _verify_held_parent(parent: Mapping[str, Any]) -> None:
    path = cast(Path, parent["path"])
    try:
        opened = os.fstat(parent["fd"])
        current = os.lstat(path)
    except OSError as exc:
        raise ApplyError(f"held parent is no longer reachable at {path}: {exc}") from exc
    if (
        not stat.S_ISDIR(opened.st_mode)
        or stat.S_ISLNK(current.st_mode)
        or (opened.st_dev, opened.st_ino) != (parent["device"], parent["inode"])
        or (current.st_dev, current.st_ino) != (parent["device"], parent["inode"])
    ):
        raise ApplyError(f"held parent identity changed: {path}")


def _read_at(
    parent: Mapping[str, Any], name: str, display_path: Path
) -> tuple[bytes, tuple[int, int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent["fd"])
    except OSError as exc:
        raise InputError(f"cannot open regular file {display_path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        current_before = os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(current_before.st_mode)
            or (before.st_dev, before.st_ino)
            != (current_before.st_dev, current_before.st_ino)
        ):
            raise InputError(f"path is not a regular file: {display_path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read()
        after = os.fstat(descriptor)
        current_after = os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ) or (after.st_dev, after.st_ino) != (
            current_after.st_dev,
            current_after.st_ino,
        ):
            raise InputError(f"path changed while reading: {display_path}")
        return raw, (before.st_dev, before.st_ino, before.st_mode & 0o777)
    except OSError as exc:
        raise InputError(f"cannot verify regular file {display_path}: {exc}") from exc
    finally:
        os.close(descriptor)


def _verify_source_identity_at(
    parent: Mapping[str, Any],
    name: str,
    write: Mapping[str, Any],
    display_path: Path,
) -> None:
    if write["source_exists"]:
        try:
            raw, identity = _read_at(parent, name, display_path)
        except MigrationError as exc:
            raise ApplyError(f"stale source identity: {display_path}: {exc}") from exc
        if (
            _sha256(raw) != write["source_sha256"]
            or identity
            != (write["source_device"], write["source_inode"], write["source_mode"])
        ):
            raise ApplyError(f"stale source identity: {display_path}")
        return
    try:
        os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
    except FileNotFoundError:
        return
    raise ApplyError(f"planned new target now exists: {display_path}")


def _write_new_file_at(
    parent: Mapping[str, Any],
    name: str,
    payload: bytes,
    mode: int,
    kind: str,
    index: int,
) -> None:
    _verify_held_parent(parent)
    _inject_fault(f"{kind}-create", index)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, mode, dir_fd=parent["fd"])
    try:
        os.fchmod(descriptor, mode)
        _inject_fault(f"{kind}-write", index)
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
        _inject_fault(f"{kind}-file-fsync", index)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _inject_fault(f"{kind}-parent-fsync", index)
    os.fsync(parent["fd"])


def _existing_hash_at(parent: Mapping[str, Any], name: str, display_path: Path) -> str | None:
    try:
        raw, _ = _read_at(parent, name, display_path)
    except InputError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return None
        raise
    return _sha256(raw)


def _identity_at(parent: Mapping[str, Any], name: str) -> tuple[int, int]:
    metadata = os.stat(name, dir_fd=parent["fd"], follow_symlinks=False)
    return metadata.st_dev, metadata.st_ino


def _decode_json(raw: bytes, path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise InputError(f"JSON root must be an object: {path}")
    return parsed


def _write_new_file(path: Path, payload: bytes, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(descriptor)
        _fsync_directory(path.parent)
    finally:
        os.close(descriptor)


def _atomic_write_bytes(path: Path, payload: bytes, fault_prefix: str | None = None) -> None:
    _assert_safe_output(path)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            if fault_prefix is not None:
                _inject_fault(f"{fault_prefix}-write", 0)
            handle.write(payload)
            handle.flush()
            if fault_prefix is not None:
                _inject_fault(f"{fault_prefix}-file-fsync", 0)
            os.fsync(handle.fileno())
        if fault_prefix is not None:
            _inject_fault(f"{fault_prefix}-replace", 0)
        os.replace(temp_path, path)
        if fault_prefix is not None:
            _inject_fault(f"{fault_prefix}-parent-fsync", 0)
        _fsync_directory(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def _state_root() -> Path:
    override = os.environ.get("WU_SESSION_MIGRATION_STATE_DIR")
    return Path(override) if override else Path.home() / ".local/state/ai/wu-session-migration"


def _journal_path() -> Path:
    return _state_root() / "transaction.json"


@contextmanager
def _cutover_lock() -> Iterator[None]:
    root = _state_root()
    root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(root / "cutover.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _write_journal(journal: Mapping[str, Any]) -> None:
    root = _state_root()
    root.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(_journal_path(), _json_bytes(journal), "journal")


def _cleanup_transaction(
    journal: Mapping[str, Any],
    *,
    held_parents: Mapping[Path, Mapping[str, Any]],
) -> None:
    failures: list[str] = []
    parents_to_fsync: set[Path] = set()
    for index, target in enumerate(journal["ordered_targets"]):
        parent = held_parents[Path(target["parent_path"])]
        parents_to_fsync.add(Path(target["parent_path"]))
        failures.extend(_cleanup_target_artifacts(parent, target, index))
    for index, parent_path in enumerate(sorted(parents_to_fsync, key=str)):
        parent = held_parents[parent_path]
        try:
            _inject_fault("cleanup-parent-fsync", index)
            os.fsync(parent["fd"])
        except OSError as exc:
            failures.append(f"{parent_path}: {exc}")
    if failures:
        raise ApplyError("transaction cleanup failures: " + "; ".join(failures))
    _remove_transaction_journal()


def _capture_record(command: list[str], payload: Any) -> dict[str, Any]:
    return {
        "command": command,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "payload_sha256": _sha256(_canonical_json_bytes(payload)),
    }


def _run_json_command(command: list[str]) -> dict[str, Any]:
    text = _run_text_command(command)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApplyError(f"trusted command returned malformed JSON: {command[0]}") from exc
    if not isinstance(value, dict):
        raise ApplyError(f"trusted command returned a non-object: {command[0]}")
    return value


def _run_text_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ApplyError(f"trusted evidence capture failed: {' '.join(command)}: {exc}") from exc
    return result.stdout


def _inject_fault(point: str, index: int) -> None:
    if FAULT_HOOK is not None:
        FAULT_HOOK(point, index)
    requested = os.environ.get("WU_SESSION_MIGRATION_INTERRUPT")
    if requested == f"{point}:{index}":
        os._exit(97)


def _existing_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return _sha256(_safe_read_bytes(path))


def _row_manifest_path(row: Mapping[str, Any]) -> str | None:
    for key in ("session_manifest_path", "manifest_path", "manifest"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _oid_values_compatible(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str) or not left or not right:
        return False
    left = left.lower()
    right = right.lower()
    return left.startswith(right) or right.startswith(left)


def _clean_base(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("origin/"):
        return value.removeprefix("origin/")
    return value


def _required_string(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise MigrationError(f"missing-{key.replace('_', '-')}")
    return value


def _require_full_oid(value: Any, label: str) -> None:
    if not isinstance(value, str) or not FULL_OID_RE.fullmatch(value.lower()):
        raise MigrationError(f"invalid-or-abbreviated-{label}")


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _normalized(path: Path) -> str:
    return os.path.normpath(str(path.absolute()))


def _inode(path: Path) -> tuple[int, int]:
    metadata = os.stat(path, follow_symlinks=False)
    return metadata.st_dev, metadata.st_ino


def _is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return path != root


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
