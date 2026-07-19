#!/usr/bin/env python3
"""Project Phase 6 Step 6b output-index rows into Step 6c side-file evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECTION_HELPER_IDENTITY = "~/ai/workflows/step6c-consumption-side-file.md"
PROJECTION_SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise ValueError(f"not a markdown table row: {line!r}")
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def normalize_artifact_id(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


def scoped_artifact_id(value: str, level_id: str) -> str:
    if level_id == "none":
        return value
    if Path(value).is_absolute():
        return value
    if value.startswith(f"{level_id}:"):
        return value
    return f"{level_id}:{value}"


def parse_step6b_outputs(index_path: Path) -> list[str]:
    output_col: int | None = None
    outputs: list[str] = []

    for lineno, raw in enumerate(index_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = split_markdown_row(line)
        if output_col is None:
            lowered = [cell.casefold() for cell in cells]
            if "step 6b output" in lowered:
                output_col = lowered.index("step 6b output")
            continue
        if is_separator_row(cells):
            continue
        if output_col >= len(cells):
            raise ValueError(f"{index_path}:{lineno}: missing Step 6b output cell")
        artifact_id = normalize_artifact_id(cells[output_col])
        if not artifact_id:
            raise ValueError(f"{index_path}:{lineno}: blank Step 6b output cell")
        outputs.append(artifact_id)

    if output_col is None:
        raise ValueError(f"{index_path}: no markdown table header named 'Step 6b output'")
    if not outputs:
        raise ValueError(f"{index_path}: no Step 6b output rows")
    return outputs


def canonical_rows(index_path: Path, level_id: str) -> list[str]:
    resolved_index = index_path.resolve()
    rows = [f"consumed: {resolved_index}"]
    for output in parse_step6b_outputs(index_path):
        rows.append(f"consumed: {scoped_artifact_id(output, level_id)}")
    if len(set(rows)) != len(rows):
        raise ValueError("duplicate canonical consumed rows are forbidden")
    return rows


def write_side_file(index_path: Path, out_path: Path, level_id: str) -> list[str]:
    rows = canonical_rows(index_path, level_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return rows


def manifest_value_from_env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


def write_manifest(
    manifest_path: Path,
    index_path: Path,
    side_file_path: Path,
    rows: list[str],
    level_id: str,
    projected_at: str,
) -> None:
    prompt_path = manifest_value_from_env(
        "STEP6C_PROMPT_PATH",
        str(Path("/abs/pending/step6c-prompt.md")),
    )
    log_path = manifest_value_from_env(
        "STEP6C_LOG_PATH",
        str(Path("/abs/pending/step6c.log")),
    )
    invocation_uuid = manifest_value_from_env(
        "STEP6C_INVOCATION_UUID",
        "00000000-0000-4000-8000-000000000000",
    )
    content = "\n".join(
        [
            "side_channel_evidence_bundle:",
            "  schema_version: 1",
            f"  level_id: {level_id}",
            f"  side_file_path: {side_file_path.resolve()}",
            f"  source_step6b_output_index_path: {index_path.resolve()}",
            f"  projection_helper_identity: {PROJECTION_HELPER_IDENTITY}",
            f"  projection_schema_version: {PROJECTION_SCHEMA_VERSION}",
            f"  canonical_row_count: {len(rows) - 1}",
            f"  side_file_sha256: {sha256_file(side_file_path)}",
            f"  source_index_sha256: {sha256_file(index_path)}",
            f"  projected_at: {projected_at}",
            f"  step6c_invocation_uuid: {invocation_uuid}",
            f"  step6c_prompt_path: {Path(prompt_path).resolve()}",
            f"  step6c_log_path: {Path(log_path).resolve()}",
            "",
        ]
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(content, encoding="utf-8")


def project(args: argparse.Namespace) -> int:
    index_path = Path(args.index)
    out_path = Path(args.out)
    if not index_path.is_file():
        print(f"ERROR:index-not-found:{index_path}", file=sys.stderr)
        return 2
    if args.level_id == "":
        print("ERROR:level-id-required", file=sys.stderr)
        return 2

    try:
        rows = write_side_file(index_path, out_path, args.level_id)
        projected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if args.expected_process:
            write_manifest(
                Path(args.expected_process),
                index_path,
                out_path,
                rows,
                args.level_id,
                projected_at,
            )
    except ValueError as exc:
        print(f"ERROR:{exc}", file=sys.stderr)
        return 2

    print(f"WROTE:{out_path.resolve()}")
    if args.expected_process:
        print(f"WROTE:{Path(args.expected_process).resolve()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="step6c-consumption-side-file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    project_parser = subparsers.add_parser("project")
    project_parser.add_argument("--index", required=True, help="Step 6b output index")
    project_parser.add_argument("--out", required=True, help="side-file output path")
    project_parser.add_argument("--level-id", required=True, help='recursive level id or "none"')
    project_parser.add_argument(
        "--expected-process",
        help="optional path for the side_channel_evidence_bundle manifest entry",
    )
    project_parser.set_defaults(func=project)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
