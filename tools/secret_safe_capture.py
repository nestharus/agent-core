#!/usr/bin/env python3
"""Capture a complete child stream without retaining declared secret values."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import BinaryIO

import yaml


REDACTION = b"[REDACTED]"
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CONTRACT_SECTION = re.compile(
    r"(?ms)^## Contract\s*$\n(?P<section>.*?)(?=^##\s|\Z)"
)
_YAML_FENCE = re.compile(r"(?ms)^```ya?ml\s*$\n(?P<yaml>.*?)^```\s*$")


class SecretCaptureError(ValueError):
    """Raised when a contract cannot safely drive child-log capture."""


def load_secret_names(contract_path: Path) -> tuple[str, ...]:
    """Return the validated environment names declared by one operator contract."""

    try:
        text = contract_path.read_text(encoding="utf-8")
        if contract_path.suffix.lower() == ".md":
            section = _CONTRACT_SECTION.search(text)
            fences = _YAML_FENCE.findall(section.group("section")) if section else []
            if len(fences) != 1:
                raise SecretCaptureError(
                    "operator must contain exactly one Contract YAML block"
                )
            text = fences[0]
        contract = yaml.safe_load(text)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SecretCaptureError("contract is unreadable or malformed") from exc
    if not isinstance(contract, dict):
        raise SecretCaptureError("contract root must be a mapping")
    if contract.get("schema") != "operator-contract-v1":
        raise SecretCaptureError("contract schema must be operator-contract-v1")

    secrets = contract.get("secrets")
    if not isinstance(secrets, list):
        raise SecretCaptureError("contract secrets must be a list")

    names: list[str] = []
    for name in secrets:
        if not isinstance(name, str) or not _ENV_NAME.fullmatch(name):
            raise SecretCaptureError("contract contains an invalid secret name")
        if name in names:
            raise SecretCaptureError("contract contains a duplicate secret name")
        names.append(name)
    return tuple(names)


def declared_secret_values(
    names: Sequence[str], environ: Mapping[str, str]
) -> tuple[bytes, ...]:
    """Read non-empty declared values without exposing them in diagnostics."""

    values: list[bytes] = []
    for name in names:
        value = environ.get(name)
        if not value:
            continue
        encoded = os.fsencode(value)
        if encoded in REDACTION:
            raise SecretCaptureError("declared value conflicts with redaction marker")
        if encoded not in values:
            values.append(encoded)
    values.sort(key=len, reverse=True)
    return tuple(values)


def _next_secret(
    data: bytes, values: Sequence[bytes], start: int
) -> tuple[int, bytes] | None:
    match_start: int | None = None
    match_value = b""
    for value in values:
        candidate = data.find(value, start)
        if candidate < 0:
            continue
        if match_start is None or candidate < match_start:
            match_start = candidate
            match_value = value
        elif candidate == match_start and len(value) > len(match_value):
            match_value = value
    if match_start is None:
        return None
    return match_start, match_value


def _overlapping_secret_end(
    data: bytes, values: Sequence[bytes], match_start: int, match_value: bytes
) -> int:
    match_end = match_start + len(match_value)
    search_start = match_start + 1
    while search_start < match_end:
        for value in values:
            if data.startswith(value, search_start):
                match_end = max(match_end, search_start + len(value))
        search_start += 1
    return match_end


def _redact_ready(
    data: bytes, values: Sequence[bytes], *, final: bool
) -> tuple[bytes, bytes]:
    retain = 0 if final else max(len(value) for value in values) - 1
    safe_limit = max(0, len(data) - retain)
    cursor = 0
    redacted: list[bytes] = []

    while cursor < safe_limit:
        match = _next_secret(data, values, cursor)
        if match is None or match[0] >= safe_limit:
            redacted.append(data[cursor:safe_limit])
            cursor = safe_limit
            break
        match_start, match_value = match
        match_end = _overlapping_secret_end(data, values, match_start, match_value)
        if not final and match_end > safe_limit:
            redacted.append(data[cursor:match_start])
            cursor = match_start
            break
        redacted.extend((data[cursor:match_start], REDACTION))
        cursor = match_end

    return b"".join(redacted), data[cursor:]


def capture_stream(
    source: BinaryIO,
    outputs: Sequence[BinaryIO],
    secret_values: Sequence[bytes],
    *,
    chunk_size: int = 64 * 1024,
) -> None:
    """Copy a stream completely, replacing declared values before any output write."""

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")

    pending = b""
    while True:
        chunk = source.read(chunk_size)
        if not chunk:
            break
        if secret_values:
            ready, pending = _redact_ready(pending + chunk, secret_values, final=False)
        else:
            ready = chunk
        for output in outputs:
            output.write(ready)
            output.flush()

    if secret_values:
        ready, pending = _redact_ready(pending, secret_values, final=True)
        if pending:
            raise SecretCaptureError("redaction did not consume the complete stream")
        for output in outputs:
            output.write(ready)
            output.flush()


def render_presence(names: Sequence[str], environ: Mapping[str, str]) -> str:
    """Render presence-only diagnostics for declared environment names."""

    return "".join(
        f"{name}={'present' if name in environ else 'absent'}\n" for name in names
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture")
    capture.add_argument("--contract", type=Path, required=True)
    capture.add_argument("--log", type=Path, required=True)

    presence = subparsers.add_parser("presence")
    presence.add_argument("--contract", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        names = load_secret_names(args.contract.expanduser())
        if args.command == "presence":
            sys.stdout.write(render_presence(names, os.environ))
            return 0

        values = declared_secret_values(names, os.environ)
        with args.log.expanduser().open("wb") as log:
            capture_stream(sys.stdin.buffer, (sys.stdout.buffer, log), values)
        return 0
    except (OSError, SecretCaptureError) as exc:
        print(f"BLOCKED:secret-safe-capture:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
