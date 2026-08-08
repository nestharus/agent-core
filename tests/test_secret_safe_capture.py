from __future__ import annotations

import io
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools/secret_safe_capture.py"
SENTINEL = "acr373-synthetic-sentinel"
INVOCATION_ID = "9e69e8cc-616d-4640-bf1d-96f5391b1a2e"

_CAPTURE_SPEC = importlib.util.spec_from_file_location("secret_safe_capture", TOOL)
assert _CAPTURE_SPEC and _CAPTURE_SPEC.loader
_CAPTURE_MODULE = importlib.util.module_from_spec(_CAPTURE_SPEC)
_CAPTURE_SPEC.loader.exec_module(_CAPTURE_MODULE)
REDACTION = _CAPTURE_MODULE.REDACTION
SecretCaptureError = _CAPTURE_MODULE.SecretCaptureError
capture_stream = _CAPTURE_MODULE.capture_stream
declared_secret_values = _CAPTURE_MODULE.declared_secret_values
load_secret_names = _CAPTURE_MODULE.load_secret_names

_CONTRACT_SPEC = importlib.util.spec_from_file_location(
    "operational_contracts", REPO_ROOT / "tools/operational_contracts.py"
)
assert _CONTRACT_SPEC and _CONTRACT_SPEC.loader
_CONTRACT_MODULE = importlib.util.module_from_spec(_CONTRACT_SPEC)
_CONTRACT_SPEC.loader.exec_module(_CONTRACT_MODULE)
extract_provider_payload = _CONTRACT_MODULE.extract_provider_payload


def _contract(path: Path, secrets: str) -> Path:
    path.write_text(
        "schema: operator-contract-v1\n"
        "inputs: []\n"
        "defaults: []\n"
        f"secrets: {secrets}\n"
        "outputs: []\n"
        "errors: []\n"
        "side_effects: []\n"
        "must_delegate: []\n"
        "may_direct: []\n"
        "forbidden_direct: []\n",
        encoding="utf-8",
    )
    return path


def _runner_stream(payload: bytes) -> bytes:
    return (
        b'OULIPOLY_INVOCATION={"source":"fixture","id":"'
        + INVOCATION_ID.encode()
        + b'"}\n'
        + payload
        + b'OULIPOLY_RESULT={"id":"'
        + INVOCATION_ID.encode()
        + b'","status":"succeeded","success":true,"exit_code":0}\n'
    )


def test_capture_redacts_declared_secret_before_complete_durable_output(
    tmp_path: Path,
) -> None:
    contract = _contract(tmp_path / "operator.yaml", "[SYNTHETIC_SECRET]")
    log = tmp_path / "child.log"
    ordinary = b"ordinary output remains complete\n"
    stream = _runner_stream(ordinary + SENTINEL.encode() + b"\nfinal ordinary line\n")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "capture",
            "--contract",
            str(contract),
            "--log",
            str(log),
        ],
        input=stream,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"SYNTHETIC_SECRET": SENTINEL},
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == b""
    assert SENTINEL.encode() not in result.stdout
    assert SENTINEL.encode() not in log.read_bytes()
    assert result.stdout == log.read_bytes()
    assert ordinary in log.read_bytes()
    assert b"final ordinary line\n" in log.read_bytes()
    assert REDACTION in log.read_bytes()

    extracted = tmp_path / "provider-output.txt"
    extract_provider_payload(log, extracted)
    assert extracted.read_bytes() == ordinary + REDACTION + b"\nfinal ordinary line\n"


def test_capture_redacts_values_split_across_read_boundaries() -> None:
    source = io.BytesIO(b"before-" + SENTINEL.encode() + b"-after")
    stdout = io.BytesIO()
    durable = io.BytesIO()
    values = declared_secret_values(
        ("SYNTHETIC_SECRET",), {"SYNTHETIC_SECRET": SENTINEL}
    )

    capture_stream(source, (stdout, durable), values, chunk_size=3)

    assert stdout.getvalue() == b"before-" + REDACTION + b"-after"
    assert durable.getvalue() == stdout.getvalue()


def test_presence_diagnostics_reveal_only_declared_state(tmp_path: Path) -> None:
    contract = _contract(
        tmp_path / "operator.yaml", "[SYNTHETIC_PRESENT, SYNTHETIC_ABSENT]"
    )

    result = subprocess.run(
        [sys.executable, str(TOOL), "presence", "--contract", str(contract)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"SYNTHETIC_PRESENT": SENTINEL},
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == (
        b"SYNTHETIC_PRESENT=present\nSYNTHETIC_ABSENT=absent\n"
    )
    assert SENTINEL.encode() not in result.stdout
    assert result.stderr == b""


@pytest.mark.parametrize(
    "contents",
    [
        "",
        "[not valid",
        "schema: wrong\nsecrets: []\n",
        "schema: operator-contract-v1\n",
        "schema: operator-contract-v1\nsecrets: SYNTHETIC_SECRET\n",
        "schema: operator-contract-v1\nsecrets: ['']\n",
        "schema: operator-contract-v1\nsecrets: [SYNTHETIC_SECRET, SYNTHETIC_SECRET]\n",
    ],
)
def test_malformed_contract_fails_before_log_creation(
    tmp_path: Path, contents: str
) -> None:
    contract = tmp_path / "operator.yaml"
    contract.write_text(contents, encoding="utf-8")
    log = tmp_path / "child.log"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "capture",
            "--contract",
            str(contract),
            "--log",
            str(log),
        ],
        input=b"ordinary output\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={},
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.startswith(b"BLOCKED:secret-safe-capture:")
    assert not log.exists()


@pytest.mark.parametrize("secrets", ["[]", "[SYNTHETIC_ABSENT]"])
def test_empty_or_absent_declared_secrets_preserve_every_byte(
    tmp_path: Path, secrets: str
) -> None:
    contract = _contract(tmp_path / "operator.yaml", secrets)
    names = load_secret_names(contract)
    values = declared_secret_values(names, {})
    stream = b"complete ordinary output\x00with binary bytes\n"
    stdout = io.BytesIO()
    durable = io.BytesIO()

    capture_stream(io.BytesIO(stream), (stdout, durable), values, chunk_size=2)

    assert stdout.getvalue() == stream
    assert durable.getvalue() == stream


def test_load_secret_names_rejects_unreadable_contract(tmp_path: Path) -> None:
    with pytest.raises(SecretCaptureError):
        load_secret_names(tmp_path / "missing.yaml")


def test_load_secret_names_supports_embedded_contract_fallback(tmp_path: Path) -> None:
    operator = tmp_path / "operator.md"
    operator.write_text(
        "---\nmodel: test\n---\n\n"
        "## Contract\n\n"
        "```yaml\n"
        "schema: operator-contract-v1\n"
        "secrets:\n"
        "  - SYNTHETIC_SECRET\n"
        "```\n\n"
        "## Procedure\n",
        encoding="utf-8",
    )

    assert load_secret_names(operator) == ("SYNTHETIC_SECRET",)


def test_redaction_marker_conflict_fails_before_log_creation(tmp_path: Path) -> None:
    contract = _contract(tmp_path / "operator.yaml", "[SYNTHETIC_SECRET]")
    log = tmp_path / "child.log"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "capture",
            "--contract",
            str(contract),
            "--log",
            str(log),
        ],
        input=b"ordinary output\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"SYNTHETIC_SECRET": REDACTION.decode()},
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == b""
    assert REDACTION not in result.stderr
    assert not log.exists()
