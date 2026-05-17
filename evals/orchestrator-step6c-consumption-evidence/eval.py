#!/usr/bin/env python3
"""Runnable ACR-247 side-channel consumption-evidence eval.

This script is intentionally self-contained. It models the Audit #2 predicate
for the ACR-247 side-channel fixtures without becoming the topology authority.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID


EVAL_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = EVAL_DIR / "fixtures"
PROJECTION_IDENTITY = "~/ai/workflows/step6c-consumption-side-file.md"
PROJECTION_EXECUTABLE = "step6c-consumption-side-file"

REQUIRED_BUNDLE_FIELDS = {
    "schema_version": int,
    "level_id": str,
    "side_file_path": str,
    "source_step6b_output_index_path": str,
    "projection_helper_identity": str,
    "projection_schema_version": int,
    "canonical_row_count": int,
    "side_file_sha256": str,
    "source_index_sha256": str,
    "projected_at": str,
    "step6c_invocation_uuid": str,
    "step6c_prompt_path": str,
    "step6c_log_path": str,
}

ATTESTATION_TOKENS = (
    "consumed:",
    "CONSUMED_EVIDENCE_EMITTED",
    "read-confirmed",
    "read confirmed",
    "READ-CONFIRMED",
)

PROMPT_FORBIDDEN_TOKENS = re.compile(
    r"consumed\s*:|CONSUMED_EVIDENCE_EMITTED|read[- ]confirmation rows?|"
    r"read[- ]confirmed|load-bearing (?:model-authored )?(?:attestation|proof|evidence)",
    re.IGNORECASE,
)
PROMPT_REQUIREMENT_WORDS = re.compile(
    r"\b(must|shall|required?|requires?|needs?|prove|proof|load-bearing|"
    r"authoritative|attest(?:ation|ed)?|emit|include|write|produce|provide|record)\b",
    re.IGNORECASE,
)
PROMPT_NEGATED_REQUIREMENT = re.compile(
    r"\b(do not|does not|must not|should not|never|without|not)\b.{0,50}"
    r"\b(require|request|ask|use|treat|accept|rely|depend)\b",
    re.IGNORECASE,
)
CANONICAL_DISPATCH = re.compile(
    r"^agents\s+-m\s+\S+\s+-p\s+\S+\s+-f\s+\S+\s+2>&1\s+\|\s+tee\s+\S+\s*$"
)
SHELL_HYGIENE_BLOCKERS = re.compile(
    r"\b(agents-with-evidence|python\s+-c|python\s+<<|bash\s+-c|sh\s+-c|"
    r"head\b|tail\b|awk\b|sed\b|grep\b|xargs\b|tee\s+.*\|)\b|<<\s*\w+|&&|;|`|\$\(",
    re.IGNORECASE,
)


@dataclass
class ProjectionResult:
    status: str
    detail: str
    output_path: Path | None = None


@dataclass
class FixtureResult:
    name: str
    expected: str
    actual: str
    status: str
    detail: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def load_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the tiny YAML subset used by these fixtures.

    Supported shape: mappings with scalar values and one indentation level.
    This keeps the eval stdlib-only while remaining explicit about fixture
    format expectations.
    """

    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent]:
            raise ValueError(f"{path}:{lineno}: tabs are not supported")
        line = raw.strip()
        if ":" not in line:
            raise ValueError(f"{path}:{lineno}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parse_scalar(value)
    return result


def fixture_path(fixture_dir: Path, value: Any) -> Path:
    path = Path(str(value))
    if not path.is_absolute():
        path = fixture_dir / path
    return path


def strip_example_context(text: str) -> str:
    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    kept_lines: list[str] = []
    for raw in without_fences.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith(">") or stripped.startswith("    "):
            continue
        kept_lines.append(raw)
    return "\n".join(kept_lines)


def prompt_requests_load_bearing_attestation(text: str) -> bool:
    candidate = strip_example_context(text)
    for raw_line in candidate.splitlines():
        line = raw_line.strip()
        if not line or not PROMPT_FORBIDDEN_TOKENS.search(line):
            continue
        if PROMPT_NEGATED_REQUIREMENT.search(line):
            continue
        token_match = PROMPT_FORBIDDEN_TOKENS.search(line)
        assert token_match is not None
        start = max(0, token_match.start() - 120)
        end = min(len(line), token_match.end() + 120)
        window = line[start:end]
        if PROMPT_REQUIREMENT_WORDS.search(window):
            return True
    return False


def check_prompt_contract(fixture_dir: Path, meta: dict[str, Any]) -> tuple[str, str]:
    prompt_keys = [
        "step6c_prompt_path",
        "step6c_prompt_clean_path",
        "step6c_prompt_dirty_path",
    ]
    prompt_paths = [
        fixture_path(fixture_dir, meta[key])
        for key in prompt_keys
        if isinstance(meta.get(key), str)
    ]
    if not prompt_paths:
        prompt_paths = sorted(fixture_dir.glob("step6c-prompt-*.md"))
    if not prompt_paths:
        return "block-prompt-contract-invalid", "fixture references no Step 6c prompt"

    verdicts: list[str] = []
    details: list[str] = []
    for prompt_path in prompt_paths:
        if not prompt_path.exists():
            return "block-prompt-contract-invalid", f"prompt missing: {prompt_path}"
        text = prompt_path.read_text(encoding="utf-8", errors="replace")
        if prompt_requests_load_bearing_attestation(text):
            verdicts.append("block-if-prompt-requests-load-bearing-attestation")
            details.append(f"{prompt_path.name}: prompt requires load-bearing attestation")
        else:
            verdicts.append("pass-if-prompt-clean")
            details.append(f"{prompt_path.name}: prompt is clean")

    ordered = [
        "pass-if-prompt-clean",
        "block-if-prompt-requests-load-bearing-attestation",
    ]
    actual = " | ".join(value for value in ordered if value in set(verdicts))
    return actual, "; ".join(details)


def dispatch_shape_verdict(text: str) -> tuple[str, str]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(lines) != 1:
        return (
            "block-if-wrapper-or-shell-fanout-or-truncating-filter",
            "dispatch capture must contain exactly one command line",
        )
    line = lines[0]
    if SHELL_HYGIENE_BLOCKERS.search(line):
        return (
            "block-if-wrapper-or-shell-fanout-or-truncating-filter",
            "dispatch command contains wrapper, heredoc, fanout, or truncating filter",
        )
    if not CANONICAL_DISPATCH.fullmatch(line):
        return (
            "block-if-wrapper-or-shell-fanout-or-truncating-filter",
            "dispatch command does not match canonical agents -m ... -p ... -f ... 2>&1 | tee ... shape",
        )
    return "pass-if-dispatch-shape-clean", "dispatch command shape is canonical"


def check_dispatch_hygiene(fixture_dir: Path, meta: dict[str, Any]) -> tuple[str, str]:
    command_keys = [
        "dispatch_cmd_path",
        "dispatch_cmd_clean_path",
        "dispatch_cmd_dirty_path",
    ]
    command_paths = [
        fixture_path(fixture_dir, meta[key])
        for key in command_keys
        if isinstance(meta.get(key), str)
    ]
    if not command_paths:
        command_paths = sorted(fixture_dir.glob("step6c-dispatch-cmd-*.txt"))
    if not command_paths:
        return "block-dispatch-hygiene-invalid", "fixture references no dispatch command"

    verdicts: list[str] = []
    details: list[str] = []
    for command_path in command_paths:
        if not command_path.exists():
            return "block-dispatch-hygiene-invalid", f"dispatch command missing: {command_path}"
        verdict, detail = dispatch_shape_verdict(
            command_path.read_text(encoding="utf-8", errors="replace")
        )
        verdicts.append(verdict)
        details.append(f"{command_path.name}: {detail}")

    ordered = [
        "pass-if-dispatch-shape-clean",
        "block-if-wrapper-or-shell-fanout-or-truncating-filter",
    ]
    actual = " | ".join(value for value in ordered if value in set(verdicts))
    return actual, "; ".join(details)


def normalize_anchor(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def check_convention_rule_present(
    fixture_dir: Path,
    meta: dict[str, Any],
    strict: bool = False,
) -> tuple[str, str]:
    snippet_path = fixture_path(
        fixture_dir,
        meta.get("convention_rule_snippet_path", "convention-rule-snippet.md"),
    )
    target_meta_path = fixture_path(
        fixture_dir,
        meta.get("expected_convention_target_path", "expected-convention-target.yaml"),
    )
    if not snippet_path.exists():
        return "block-if-convention-rule-absent", f"snippet missing: {snippet_path}"
    if not target_meta_path.exists():
        return "block-if-convention-rule-absent", f"target metadata missing: {target_meta_path}"

    target_meta = load_simple_yaml(target_meta_path)
    target_values = [
        value
        for key, value in target_meta.items()
        if key == "target_path" or key.startswith("target_path_option")
    ]
    if not target_values:
        return "block-if-convention-rule-absent", "target metadata declares no target_path"

    worktree_root = EVAL_DIR.parent.parent
    anchor = normalize_anchor(snippet_path.read_text(encoding="utf-8"))
    for raw_target in target_values:
        target_path = worktree_root / str(raw_target)
        if not target_path.exists():
            continue
        target_text = strip_example_context(
            target_path.read_text(encoding="utf-8", errors="replace")
        )
        if anchor in normalize_anchor(target_text):
            return "pass-if-convention-rule-present", f"anchor present in {raw_target}"

    if bool(meta.get("pre_step6c_skip")) and not strict:
        return "skip", "awaiting-step6c-ac5"

    return (
        "block-if-convention-rule-absent",
        "no declared convention target contains the load-bearing evidence anchor",
    )


def parse_rfc3339(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def consumed_rows(side_file: Path) -> list[str]:
    rows: list[str] = []
    for raw in side_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(line)
    return rows


def validate_bundle_schema(bundle: Any) -> tuple[bool, str]:
    if not isinstance(bundle, dict):
        return False, "side_channel_evidence_bundle is missing or not a mapping"
    for key, expected_type in REQUIRED_BUNDLE_FIELDS.items():
        if key not in bundle:
            return False, f"missing required key: {key}"
        if not isinstance(bundle[key], expected_type):
            return False, f"malformed key {key}: expected {expected_type.__name__}"

    if bundle["schema_version"] != 1:
        return False, "schema_version must be 1"
    if bundle["projection_schema_version"] != 1:
        return False, "projection_schema_version must be 1"
    if bundle["projection_helper_identity"] != PROJECTION_IDENTITY:
        return False, "projection_helper_identity does not match the contract"
    if not re.fullmatch(r"[0-9a-f]{64}", bundle["side_file_sha256"]):
        return False, "side_file_sha256 must be a 64-char lowercase hex digest"
    if not re.fullmatch(r"[0-9a-f]{64}", bundle["source_index_sha256"]):
        return False, "source_index_sha256 must be a 64-char lowercase hex digest"
    for path_key in (
        "side_file_path",
        "source_step6b_output_index_path",
        "step6c_prompt_path",
        "step6c_log_path",
    ):
        if not Path(bundle[path_key]).is_absolute():
            return False, f"{path_key} must be absolute"
    try:
        parse_rfc3339(bundle["projected_at"])
    except ValueError as exc:
        return False, f"projected_at is not RFC3339-compatible: {exc}"
    try:
        UUID(bundle["step6c_invocation_uuid"])
    except ValueError as exc:
        return False, f"step6c_invocation_uuid is malformed: {exc}"
    return True, "schema complete"


def projection_command() -> tuple[list[str] | None, str]:
    if shutil.which(PROJECTION_EXECUTABLE):
        return [
            PROJECTION_EXECUTABLE,
            "project",
            "--index",
            "{index}",
            "--out",
            "{out}",
            "--level-id",
            "{level_id}",
        ], "canonical"

    raw = os.environ.get("STEP6C_PROJECTION_CMD")
    if raw:
        return shlex.split(raw), "env"

    return None, "unavailable"


def projection_unavailable_detail() -> str:
    return (
        f"projection helper unavailable: {PROJECTION_EXECUTABLE} not found on PATH "
        "and STEP6C_PROJECTION_CMD is not set"
    )


def render_projection_command(template: list[str], index: Path, level_id: str, out: Path) -> list[str]:
    cmd = [
        part.format(index=str(index), out=str(out), level_id=level_id)
        for part in template
    ]
    joined = " ".join(template)
    if "{index}" not in joined:
        cmd.extend(["--index", str(index)])
    if "{out}" not in joined:
        cmd.extend(["--out", str(out)])
    if "{level_id}" not in joined:
        cmd.extend(["--level-id", level_id])
    return cmd


def run_projection(index: Path, level_id: str, out: Path) -> ProjectionResult:
    template, source = projection_command()
    if template is None:
        return ProjectionResult("skip", projection_unavailable_detail())

    cmd = render_projection_command(template, index, level_id, out)

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(EVAL_DIR),
            check=False,
        )
    except FileNotFoundError as exc:
        if source == "canonical":
            return ProjectionResult("skip", f"projection helper unavailable: {exc}")
        return ProjectionResult("block", f"projection helper failed to start: {exc}")

    combined = f"{proc.stdout}\n{proc.stderr}".strip()
    if proc.returncode != 0:
        return ProjectionResult(
            "block",
            f"projection helper failed with exit {proc.returncode}: {combined}",
        )
    if not out.exists():
        return ProjectionResult("block", "projection helper exited 0 but wrote no output")
    return ProjectionResult("ok", "projection helper wrote output", out)


def first_blocking_verdict(fixture_dir: Path, strict: bool = False) -> tuple[str, str]:
    fixture_meta_path = fixture_dir / "fixture.yaml"
    manifest_path = fixture_dir / "expected-process-manifest.yaml"
    source_index_path = fixture_dir / "step6b-output-index.md"

    # Required by the eval contract: load fixture metadata, manifest, and index.
    fixture_meta = load_simple_yaml(fixture_meta_path)
    applies_check = str(fixture_meta.get("applies_check", "")).strip()
    if applies_check == "prompt-contract":
        return check_prompt_contract(fixture_dir, fixture_meta)
    if applies_check == "dispatch-hygiene":
        return check_dispatch_hygiene(fixture_dir, fixture_meta)
    if applies_check == "convention-rule":
        return check_convention_rule_present(fixture_dir, fixture_meta, strict=strict)

    if not source_index_path.exists():
        return "block-source-index-missing", "fixture step6b-output-index.md is missing"
    _ = source_index_path.read_bytes()

    if not manifest_path.exists():
        return "block-manifest-missing", "expected-process-manifest.yaml is missing"
    manifest = load_simple_yaml(manifest_path)
    bundle = manifest.get("side_channel_evidence_bundle")

    # 1. Manifest entry presence.
    if bundle is None:
        return "block-manifest-missing", "side_channel_evidence_bundle block missing"

    # 2. Schema completeness.
    ok, detail = validate_bundle_schema(bundle)
    if not ok:
        return "block-manifest-schema-incomplete", detail

    side_file = Path(bundle["side_file_path"])
    source_index = Path(bundle["source_step6b_output_index_path"])

    # 3. Side-file presence.
    if not side_file.exists():
        return "block-side-file-missing", f"side file missing: {side_file}"

    # 4. Source-index presence.
    if not source_index.exists():
        return "block-source-index-missing", f"source index missing: {source_index}"

    # 5. Source-index sha currentness.
    current_source_sha = sha256_file(source_index)
    if current_source_sha != bundle["source_index_sha256"]:
        return (
            "block-source-index-sha-mismatch",
            f"source sha mismatch: manifest={bundle['source_index_sha256']} current={current_source_sha}",
        )

    # 6. Side-file sha currentness.
    current_side_sha = sha256_file(side_file)
    if current_side_sha != bundle["side_file_sha256"]:
        return (
            "block-side-file-sha-mismatch",
            f"side-file sha mismatch: manifest={bundle['side_file_sha256']} current={current_side_sha}",
        )

    # 7. Re-projection equivalence.
    with tempfile.TemporaryDirectory(prefix="acr247-reproject-") as tmp:
        reprojected = Path(tmp) / "step6c-consumed-evidence.txt"
        projection = run_projection(source_index, bundle["level_id"], reprojected)
        if projection.status == "skip":
            return "skip", projection.detail
        if projection.status == "block":
            return "block-reprojection-mismatch", projection.detail
        if reprojected.read_bytes() != side_file.read_bytes():
            return "block-reprojection-mismatch", "re-projected bytes differ from side-file bytes"

    # 8. Row count check. The manifest count excludes the required prefix index row.
    rows = consumed_rows(side_file)
    if not rows:
        return "block-row-count-mismatch", "side-file contains no canonical rows"
    expected_prefix = f"consumed: {source_index}"
    if rows[0] != expected_prefix:
        return "block-reprojection-mismatch", "side-file first row is not the source-index prefix"
    output_rows = rows[1:]
    if len(output_rows) != bundle["canonical_row_count"]:
        return (
            "block-row-count-mismatch",
            f"row count mismatch: manifest={bundle['canonical_row_count']} current={len(output_rows)}",
        )
    if len(set(rows)) != len(rows):
        return "block-reprojection-mismatch", "duplicate canonical consumed rows"

    # 9. Dispatch-time ordering.
    projected_at = parse_rfc3339(bundle["projected_at"])
    start_raw = fixture_meta.get("step6c_invocation_start_at")
    if not isinstance(start_raw, str):
        return "block-dispatch-time-ordering", "fixture missing step6c_invocation_start_at"
    step6c_start = parse_rfc3339(start_raw)
    if projected_at >= step6c_start:
        return (
            "block-dispatch-time-ordering",
            f"projected_at {projected_at.isoformat()} is not before Step 6c start {step6c_start.isoformat()}",
        )

    # 10. Level-scope correctness.
    level_id = bundle["level_id"]
    for row in output_rows:
        value = row.removeprefix("consumed: ").strip()
        if level_id == "none":
            if re.match(r"^level-[A-Za-z0-9_.-]+:", value):
                return "block-level-scope-mismatch", f"child-scoped row in parent manifest: {value}"
        else:
            if not value.startswith(f"{level_id}:"):
                return (
                    "block-level-scope-mismatch",
                    f"row is not scoped to {level_id}: {value}",
                )

    # 11. Model-attestation rejection. Informational only; never turns a block
    # into a pass and never blocks an otherwise valid manifest/side-file bundle.
    log_path = Path(bundle["step6c_log_path"])
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        _attestations = [token for token in ATTESTATION_TOKENS if token in log_text]

    return "pass", "all Audit #2 side-channel predicate checks passed"


def verdict_matches(expected: str, actual: str) -> bool:
    expected_options = [part.strip() for part in expected.split("|") if part.strip()]
    if len(expected_options) > 1:
        if actual in expected_options:
            return True
        actual_parts = {part.strip() for part in actual.split("|") if part.strip()}
        if actual_parts and actual_parts.issubset(set(expected_options)):
            return True
    if actual == "skip":
        return True
    if expected == actual:
        return True
    expected_blocks = expected.startswith("block-")
    actual_blocks = actual.startswith("block-")
    if expected_blocks and actual_blocks:
        return True
    return False


def strict_projection_helper_failure(actual: str, detail: str) -> bool:
    return actual == "block-reprojection-mismatch" and detail.startswith(
        "projection helper "
    )


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")


def run_fixture(fixture_dir: Path, strict: bool = False) -> FixtureResult:
    meta = load_simple_yaml(fixture_dir / "fixture.yaml")
    expected = str(meta.get("expected_audit_verdict", "")).strip()
    if not expected:
        return FixtureResult(fixture_dir.name, "<missing>", "block-fixture-invalid", "FAIL", "expected_audit_verdict missing")
    actual, detail = first_blocking_verdict(fixture_dir, strict=strict)
    if actual == "skip":
        if strict:
            status = "FAIL"
            detail = f"strict mode treats SKIP as failure: {detail}"
        else:
            status = "SKIP"
    elif strict and strict_projection_helper_failure(actual, detail):
        status = "FAIL"
        detail = f"strict mode requires successful projection-helper invocation: {detail}"
    elif verdict_matches(expected, actual):
        status = "PASS"
    else:
        status = "FAIL"
    return FixtureResult(fixture_dir.name, expected, actual, status, detail)


def selected_fixtures(arg: str | None) -> list[Path]:
    if arg:
        path = Path(arg)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.exists():
            raise SystemExit(f"fixture not found: {path}")
        return [path]
    return sorted(path for path in FIXTURES_DIR.iterdir() if path.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ACR-247 side-channel eval fixtures")
    parser.add_argument("--fixture", help="Run one fixture directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any SKIP or projection-helper invocation failure",
    )
    args = parser.parse_args(argv)

    results = [run_fixture(path, strict=args.strict) for path in selected_fixtures(args.fixture)]

    for result in results:
        print(f"{result.status}: {result.name}: expected={result.expected} actual={result.actual}")
        print(f"  {result.detail}")

    print()
    print("| fixture | expected | actual | status |")
    print("|---|---|---|---|")
    for result in results:
        print(
            f"| {markdown_cell(result.name)} | {markdown_cell(result.expected)} | "
            f"{markdown_cell(result.actual)} | {result.status} |"
        )

    failures = [result for result in results if result.status == "FAIL"]
    skipped = [result for result in results if result.status == "SKIP"]
    passed = [result for result in results if result.status == "PASS"]
    print()
    print(
        f"summary: total={len(results)} pass={len(passed)} "
        f"skip={len(skipped)} fail={len(failures)} strict={args.strict}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
