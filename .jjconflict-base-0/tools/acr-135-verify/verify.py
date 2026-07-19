#!/usr/bin/env python3
"""Static verifier for ACR-135 prototype proof-test carry-forward docs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[2]


class CheckFailed(AssertionError):
    """Raised when a verifier check finds an uncovered product state."""


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    file: str
    name: str
    pattern_type: str
    pattern: str
    reason: str
    check: Callable[[str], None]

    def as_json(self) -> str:
        return json.dumps(
            {
                "anchor_id": self.anchor_id,
                "file": self.file,
                "anchor": self.name,
                "pattern_type": self.pattern_type,
                "pattern": self.pattern,
                "reason": self.reason,
            },
            sort_keys=True,
        )


def _read_rel(path: str) -> str:
    full_path = REPO_ROOT / path
    if not full_path.exists():
        raise CheckFailed(f"missing required file: {path}")
    return full_path.read_text(encoding="utf-8")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def _require_regex(text: str, pattern: str, context: str) -> None:
    _require(
        re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None,
        f"{context}: missing regex match {pattern!r}",
    )


def _require_contains(text: str, needle: str, context: str) -> None:
    _require(
        needle.lower() in text.lower(),
        f"{context}: missing substring {needle!r}",
    )


def _require_all(text: str, needles: list[str], context: str) -> None:
    missing = [needle for needle in needles if needle.lower() not in text.lower()]
    _require(not missing, f"{context}: missing required substrings: {missing}")


def _require_any(text: str, needles: list[str], context: str) -> None:
    _require(
        any(needle.lower() in text.lower() for needle in needles),
        f"{context}: missing any of required substrings: {needles}",
    )


def _require_window_all_any(
    text: str,
    required: list[str],
    alternatives: list[str],
    context: str,
    window_chars: int = 1800,
) -> None:
    lowered = text.lower()
    starts = [
        match.start()
        for needle in required + alternatives
        for match in re.finditer(re.escape(needle.lower()), lowered)
    ]
    for start in starts:
        window = lowered[max(0, start - window_chars) : start + window_chars]
        if all(needle.lower() in window for needle in required) and any(
            needle.lower() in window for needle in alternatives
        ):
            return
    raise CheckFailed(
        f"{context}: missing local context with {required} and one of {alternatives}"
    )


def _check_a1(text: str) -> None:
    _require_regex(text, r"^##\s+Carry-forward to implementation", "A1")


def _check_a2(text: str) -> None:
    _require_any(
        text,
        ["production solution's behavior test", "inherits that test verbatim"],
        "A2",
    )


def _check_a3(text: str) -> None:
    _require_contains(text, "strictly stronger equivalent", "A3")


def _check_a4(text: str) -> None:
    _require_all(
        text,
        ["prototype_test_pr_url", "test_paths_or_node_ids", "marker_reason"],
        "A4",
    )


def _check_a5(text: str) -> None:
    _require_any(text, ["silent drop", "silently drop", "workflow violation"], "A5")


def _check_a6(text: str) -> None:
    _require_any(text, ["implementation is wrong", "prototype's verdict was wrong"], "A6")


def _check_a7(text: str) -> None:
    _require_contains(text, "Carry-forward to implementation", "A7")


def _check_a8(text: str) -> None:
    _require_all(text, ["test_paths_or_node_ids", "prototype_test_pr_url"], "A8")


def _check_a9(text: str) -> None:
    _require_all(text, ["Step 6b output index", "inherited prototype"], "A9")


def _check_a10(text: str) -> None:
    _require_window_all_any(
        text,
        ["inherited prototype"],
        ["refuses to advance", "pre-dispatch readiness", "pre-CodeRabbit"],
        "A10",
    )


def _check_a11(text: str) -> None:
    _require_all(text, ["test_paths_or_node_ids"], "A11")
    _require_any(text, ["P4", "prototype-test PR"], "A11")


def _check_a12(text: str) -> None:
    _require_all(text, ["carry-forward"], "A12")
    _require_any(text, ["spawned implementation ticket", "spawned ticket"], "A12")


def _check_a13(text: str) -> None:
    _require_all(text, ["Step 6b output index"], "A13")
    _require_any(text, ["stronger-equivalent", "stronger equivalent"], "A13")


def _check_a14(text: str) -> None:
    _require_window_all_any(
        text,
        ["coderabbit", "inherited prototype"],
        ["refuse", "refusal", "pre-dispatch"],
        "A14",
    )


def _check_a15(text: str) -> None:
    _require_all(text, ["durable"], "A15")
    _require_any(text, ["implementation coverage", "not throwaway"], "A15")


def _check_a16(text: str) -> None:
    _require_any(text, ["stronger-equivalent", "strictly stronger"], "A16")


ANCHORS = [
    Anchor(
        "A1",
        "conventions/prototype-pending-tests.md",
        "Canonical carry-forward section",
        "case-insensitive regex",
        r"^##\s+Carry-forward to implementation",
        "Canonical convention must expose the carry-forward section anchor.",
        _check_a1,
    ),
    Anchor(
        "A2",
        "conventions/prototype-pending-tests.md",
        "Identity statement (C1)",
        "case-insensitive any-substring",
        "production solution's behavior test|inherits that test verbatim",
        "Prototype proof tests must be identified as inherited production behavior tests.",
        _check_a2,
    ),
    Anchor(
        "A3",
        "conventions/prototype-pending-tests.md",
        "No-rewrite rule (C2)",
        "case-insensitive substring",
        "strictly stronger equivalent",
        "The convention must define the no-rewrite stronger-equivalent rule.",
        _check_a3,
    ),
    Anchor(
        "A4",
        "conventions/prototype-pending-tests.md",
        "Payload schema (C3)",
        "case-insensitive all-substrings",
        "prototype_test_pr_url AND test_paths_or_node_ids AND marker_reason",
        "The spawned ticket payload must carry the canonical inherited-test fields.",
        _check_a4,
    ),
    Anchor(
        "A5",
        "conventions/prototype-pending-tests.md",
        "No silent drop (C4)",
        "case-insensitive any-substring",
        "silent drop|silently drop|workflow violation",
        "Dropping inherited proof tests must be named as a workflow violation.",
        _check_a5,
    ),
    Anchor(
        "A6",
        "conventions/prototype-pending-tests.md",
        "Drift = regression (C5)",
        "case-insensitive any-substring",
        "implementation is wrong|prototype's verdict was wrong",
        "Failure to pass inherited proof tests must be treated as implementation or prototype-verdict drift.",
        _check_a6,
    ),
    Anchor(
        "A7",
        "workflows/build-prototype.md",
        "Carry-forward cite",
        "case-insensitive substring",
        "Carry-forward to implementation",
        "Build-prototype must cite the canonical convention anchor.",
        _check_a7,
    ),
    Anchor(
        "A8",
        "workflows/build-prototype.md",
        "P4 payload requirement",
        "case-insensitive all-substrings",
        "test_paths_or_node_ids AND prototype_test_pr_url",
        "P4 ticket updates must include inherited test path/node ID and PR URL fields.",
        _check_a8,
    ),
    Anchor(
        "A9",
        "workflows/implementation-pipeline.md",
        "Phase 6 inherited-test mapping",
        "case-insensitive all-substrings",
        "Step 6b output index AND inherited prototype",
        "Phase 6 must map inherited prototype tests through the Step 6b output index.",
        _check_a9,
    ),
    Anchor(
        "A10",
        "workflows/implementation-pipeline.md",
        "Phase 7 readiness predicate",
        "case-insensitive local mixed all/any substrings",
        "inherited prototype AND (refuses to advance OR pre-dispatch readiness OR pre-CodeRabbit)",
        "Phase 7 readiness must refuse missing or invalid inherited prototype tests.",
        _check_a10,
    ),
    Anchor(
        "A11",
        "agents/prototype-orchestrator.md",
        "P3.10/P4 carry-forward payload",
        "case-insensitive mixed all/any substrings",
        "test_paths_or_node_ids AND (P4 OR prototype-test PR)",
        "Prototype orchestrator manifest/P4 flow must publish test path or node ID payloads.",
        _check_a11,
    ),
    Anchor(
        "A12",
        "agents/prototype-orchestrator.md",
        "Ticket update payload",
        "case-insensitive mixed all/any substrings",
        "carry-forward AND (spawned implementation ticket OR spawned ticket)",
        "Prototype orchestrator ticket update must carry the full carry-forward payload.",
        _check_a12,
    ),
    Anchor(
        "A13",
        "agents/implementation-pipeline-orchestrator.md",
        "Phase 6 output-index check",
        "case-insensitive mixed all/any substrings",
        "Step 6b output index AND (stronger-equivalent OR stronger equivalent)",
        "Implementation orchestrator must verify inherited-test mapping or supersession in Phase 6.",
        _check_a13,
    ),
    Anchor(
        "A14",
        "agents/implementation-pipeline-orchestrator.md",
        "Phase 7 refusal condition",
        "case-insensitive local mixed all/any substrings",
        "coderabbit AND inherited prototype AND (refuse OR refusal OR pre-dispatch)",
        "Implementation orchestrator must refuse CodeRabbit dispatch when inherited prototype tests are unresolved.",
        _check_a14,
    ),
    Anchor(
        "A15",
        "agents/prototype-test-pr-writer.md",
        "Durable-coverage framing",
        "case-insensitive mixed all/any substrings",
        "durable AND (implementation coverage OR not throwaway)",
        "Prototype-test PR body must frame tests as durable implementation coverage.",
        _check_a15,
    ),
    Anchor(
        "A16",
        "agents/prototype-test-pr-writer.md",
        "Stronger-equivalent supersession",
        "case-insensitive any-substring",
        "stronger-equivalent OR strictly stronger",
        "Prototype-test PR body must preserve assertions or record stronger-equivalent supersession.",
        _check_a16,
    ),
]


def _run_anchor(anchor: Anchor, text_by_file: dict[str, str]) -> tuple[str, bool, str | None]:
    try:
        anchor.check(text_by_file[anchor.file])
    except CheckFailed as exc:
        return anchor.anchor_id, False, str(exc)
    return anchor.anchor_id, True, None


def _load_touched_files() -> dict[str, str]:
    paths = sorted({anchor.file for anchor in ANCHORS})
    return {path: _read_rel(path) for path in paths}


def _print_anchor_list() -> None:
    for anchor in ANCHORS:
        print(anchor.as_json())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-anchors",
        action="store_true",
        help="print machine-readable JSONL anchor definitions and exit",
    )
    args = parser.parse_args(argv)

    if args.list_anchors:
        _print_anchor_list()
        return 0

    text_by_file = _load_touched_files()
    results = [_run_anchor(anchor, text_by_file) for anchor in ANCHORS]

    for anchor_id, passed, message in results:
        if passed:
            print(f"PASS {anchor_id}")
        else:
            print(f"FAIL {anchor_id}: {message}")

    failed = [(anchor_id, message) for anchor_id, passed, message in results if not passed]
    if failed:
        first_id, first_message = failed[0]
        print("FAILING ANCHORS SUMMARY:")
        for anchor_id, message in failed:
            print(f"- {anchor_id}: {message}")
        raise CheckFailed(f"{len(failed)} anchors failed; first failure {first_id}: {first_message}")

    print(f"ALL {len(ANCHORS)} ACR-135 ANCHORS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckFailed as exc:
        print(f"CHECK FAILED: {exc}")
        sys.exit(1)
