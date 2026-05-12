#!/usr/bin/env python3
"""Static verifier for ACR-137 Phase 6 product-document edits."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_INDEX_BASELINE_SHA256 = (
    "4dbd8ff9a238519ac90b087f47569400e8e6c1b66aaa88c380320bdf2897886f"
)

MARKER_REASON = (
    "prototype-pending: implementation pending in <ticket-key-or-url>; "
    "remove marker and make this test pass"
)


class CheckFailed(AssertionError):
    """Raised when a verifier check finds an uncovered product state."""


def _read_rel(path: str) -> str:
    full_path = REPO_ROOT / path
    if not full_path.exists():
        raise CheckFailed(f"missing required file: {path}")
    return full_path.read_text(encoding="utf-8")


def _body_without_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise CheckFailed("missing YAML frontmatter")
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise CheckFailed("unterminated YAML frontmatter")

    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def _require_contains(text: str, needle: str, label: str | None = None) -> None:
    _require(
        needle.lower() in text.lower(),
        f"missing substring: {label or needle}",
    )


def _require_all(text: str, needles: list[str], context: str) -> None:
    missing = [needle for needle in needles if needle.lower() not in text.lower()]
    _require(not missing, f"{context} missing: {', '.join(missing)}")


def _require_ordered(text: str, markers: list[str], context: str) -> None:
    lowered = text.lower()
    cursor = -1
    for marker in markers:
        index = lowered.find(marker.lower(), cursor + 1)
        _require(index >= 0, f"{context} missing ordered marker: {marker}")
        cursor = index


def _find_near(text: str, first: str, second: str, distance: int = 5000) -> int:
    lowered = text.lower()
    first_l = first.lower()
    second_l = second.lower()
    first_positions = [m.start() for m in re.finditer(re.escape(first_l), lowered)]
    second_positions = [m.start() for m in re.finditer(re.escape(second_l), lowered)]
    for first_pos in first_positions:
        for second_pos in second_positions:
            if abs(first_pos - second_pos) <= distance:
                return min(first_pos, second_pos)
    raise CheckFailed(
        f"could not locate {first!r} within {distance} chars of {second!r}"
    )


def _section_slice(
    text: str,
    start_marker: str,
    end_marker: str | None,
    max_len: int = 20000,
) -> str:
    """Return bounded text from start_marker to end_marker or max_len."""

    lowered = text.lower()
    start = lowered.find(start_marker.lower())
    if start < 0:
        raise CheckFailed(f"missing section start marker: {start_marker}")

    hard_end = min(len(text), start + max_len)
    if end_marker is None:
        return text[start:hard_end]

    end = lowered.find(end_marker.lower(), start + len(start_marker))
    if end < 0:
        end = hard_end
    return text[start : min(end, hard_end)]


def _section_slice_from_near(
    text: str,
    first: str,
    second: str,
    end_marker: str | None,
    distance: int = 5000,
    max_len: int = 20000,
) -> str:
    start = _find_near(text, first, second, distance)
    bounded = text[start : min(len(text), start + max_len)]
    if end_marker is None:
        return bounded
    end = bounded.lower().find(end_marker.lower(), len(first))
    if end < 0:
        return bounded
    return bounded[:end]


def check_operator_format() -> None:
    text = _read_rel("agents/prototype-test-pr-writer.md")
    fields = _frontmatter(text)
    body = _body_without_frontmatter(text)

    for key in ("description", "model", "output_format"):
        _require(key in fields, f"frontmatter missing {key}")
    _require(fields["model"] == "claude-opus", "frontmatter model must be claude-opus")

    required_sections = [
        "# Prototype-Test PR Writer",
        "## Use When",
        "## Do Not Use When",
        "## Required Inputs",
        "## Inputs",
        "## Procedure",
        "## Output Contract",
        "## Stop Conditions",
    ]
    _require_ordered(body, required_sections, "operator body")

    required_inputs = [
        "prototype_test_branch_ref",
        "base",
        "repo_root",
        "dossier_answer_path",
        "proof_test_audit_path",
        "spawned_tickets_path",
        "test_manifest_path",
        "pending_marker_convention_path",
        "implementation_ticket_urls",
        "output_path",
    ]
    required_inputs_slice = _section_slice(body, "## Required Inputs", "## Inputs")
    _require_all(required_inputs_slice, required_inputs, "Required Inputs section")

    _require_contains(body, "default", "base default language")
    _require("hard-coded to `main`" in body or "hard-coded to main" in body, "base must not be hard-coded to main")

    procedure = _section_slice(body, "## Procedure", "## Output Contract")
    title_pos = procedure.lower().find("title")
    _require(title_pos >= 0, "Procedure must mention title file")
    title_window = procedure[max(0, title_pos - 300) : title_pos + 600].lower()
    _require("single line" in title_window, "title file must be single line")
    _require(
        "< 70" in title_window or "under 70" in title_window,
        "title file must be under 70 chars",
    )
    _require_all(procedure, ["${output_path}.title", "${output_path}"], "Procedure")

    output_contract = _section_slice(body, "## Output Contract", "## Stop Conditions")
    reviewer_sections = [
        "Verdict",
        "Reviewer focus",
        "Test manifest",
        "Pending markers",
        "Dossier link",
        "Spawned implementation tickets",
        "Anti-scope",
    ]
    _require_ordered(output_contract, reviewer_sections, "Output Contract")
    _require_all(
        output_contract,
        [
            "~/ai/conventions/prototype-review.md",
            "~/ai/conventions/prototype-pending-tests.md",
            "Remove the prototype-pending markers in the listed test files and make these tests pass.",
            "CodeRabbit",
        ],
        "Output Contract",
    )

    stop_conditions = _section_slice(body, "## Stop Conditions", None)
    _require_contains(stop_conditions, "BLOCKED", "BLOCKED stop conditions")
    _require_all(
        stop_conditions,
        [
            "test_manifest_path",
            "spawned_tickets_path",
            "pending_marker_convention_path",
            "implementation_ticket_urls",
            "answer.md",
            "proof-test audit",
        ],
        "Stop Conditions",
    )


def check_pending_marker_convention() -> None:
    text = _read_rel("conventions/prototype-pending-tests.md")
    required_sections = [
        "# Prototype-Pending Tests",
        "## Purpose",
        "## Marker Reason Format",
        "## Preferred Runner Mapping",
        "## Boundary vs. Other Marker Conventions",
        "## Reviewer Guidance",
        "## Implementation-Ticket Carry-Forward",
    ]
    _require_ordered(text, required_sections, "prototype-pending convention")
    _require(MARKER_REASON in text.splitlines(), "missing exact marker reason line")
    _require_all(
        text,
        [
            "@pytest.mark.xfail",
            "strict=True",
            "test.fixme",
            "skip",
            "fixme",
            "~/ai/conventions/test-reports.md",
            "~/ai/agents/red-phase-gate.md",
            "~/ai/agents/green-phase-gate.md",
            "does NOT make generic untraceable skip/xfail acceptable",
            "~/ai/conventions/prototype-review.md",
            "Remove the `prototype-pending:` markers in the listed test files and make these tests pass.",
        ],
        "prototype-pending convention",
    )


def check_build_prototype_edits() -> None:
    text = _body_without_frontmatter(_read_rel("workflows/build-prototype.md"))
    _require_contains(text, "P4 prototype-test PR publication")
    p4_publication = _section_slice(
        text,
        "P4 prototype-test PR publication",
        "###",
        max_len=12000,
    )
    _require_all(
        p4_publication,
        [
            "file spawned tickets",
            "finalize marker reasons",
            "real ticket keys",
            "push",
            "dispatch",
            "prototype-test-pr-writer",
            "gh pr create --draft",
            "capture URL",
            "answer.md",
            "spawned-tickets.md",
            "URL",
            "branch",
            "test paths",
            "marker reason",
            "ticket mapping",
        ],
        "P4 prototype-test PR publication step",
    )
    _require_all(
        text,
        [
            "answer.md",
            "evidence/",
            "risk-profile.md",
            "challenges.md",
            "spawned-tickets.md",
            "branch-disposition.md",
        ],
        "build-prototype dossier output list",
    )


def check_prototype_orchestrator_edits() -> None:
    text = _read_rel("agents/prototype-orchestrator.md")
    _require_contains(text, "dossier/test-publication-manifest.md")
    p4 = _section_slice(text, "### Phase P4", "### Final", max_len=30000)
    _require_all(
        p4,
        [
            "dossier/test-publication-manifest.md",
            "update prototype-test branch markers",
            "prototype-pending-tests.md",
            "prototype-test-pr-writer",
            "agents -m claude-opus",
            "gh pr create --draft",
            "capture PR URL",
            "dossier/answer.md",
            "dossier/spawned-tickets.md",
            "comment on each spawned implementation ticket",
        ],
        "prototype-orchestrator P4",
    )


def check_prototype_review_edits() -> None:
    text = _read_rel("conventions/prototype-review.md")
    _require_all(
        text,
        [
            "prototype-test PR",
            "test design",
            "outcome alignment",
            "pending-marker traceability",
            "dossier verdict",
            "prototype-pending-tests.md",
        ],
        "prototype-review convention",
    )
    lowered = text.lower()
    _require(
        "coderabbit" in lowered and ("not" in lowered or "no default" in lowered),
        "prototype-review must say CodeRabbit is not default",
    )
    _require(
        "production pr-review" in lowered
        and ("not" in lowered or "do not" in lowered or "no default" in lowered),
        "prototype-review must exclude default production PR-review gates",
    )


def check_pipeline_carry_forward() -> None:
    workflow = _read_rel("workflows/implementation-pipeline.md")
    workflow_defer = _section_slice_from_near(
        workflow,
        "Phase 2.5",
        "defer",
        "## Phase 3",
        distance=5000,
        max_len=20000,
    )
    _require_all(
        workflow_defer,
        [
            "prototype-test PR URL",
            "branch",
            "test paths",
            "marker reason",
            "Remove the `prototype-pending:` markers and make these tests pass.",
        ],
        "implementation-pipeline Phase 2.5 defer-to-prototype section",
    )

    orchestrator = _read_rel("agents/implementation-pipeline-orchestrator.md")
    phase25_defer = _section_slice_from_near(
        orchestrator,
        "Phase 2.5",
        "defer",
        "### Phase 3",
        distance=5000,
        max_len=30000,
    )
    _require_contains(
        phase25_defer,
        "predecessor-prototype-evidence.md",
        "Phase 2.5 defer branch predecessor-prototype evidence",
    )

    phase3 = _section_slice(
        orchestrator,
        "### Phase 3",
        "### Phase 4",
        max_len=30000,
    )
    _require_all(
        phase3,
        [
            "prototype-pending",
            "test paths",
            "Remove the `prototype-pending:` markers and make these tests pass.",
        ],
        "implementation-pipeline-orchestrator Phase 3 prompt composition",
    )


def check_agentsmd_rows() -> None:
    text = _read_rel("AGENTS.md")
    lowered = text.lower()
    writer_pos = lowered.find("prototype-test-pr-writer")
    _require(writer_pos >= 0, "AGENTS.md missing prototype-test-pr-writer row")

    neighboring_writer_positions = [
        pos
        for marker in ("- `pr-writer`", "- `prototype-pr-writer`")
        if (pos := lowered.find(marker)) >= 0
    ]
    _require(neighboring_writer_positions, "AGENTS.md missing nearby PR writer anchors")
    _require(
        any(abs(writer_pos - pos) <= 3000 for pos in neighboring_writer_positions),
        "prototype-test-pr-writer row is not within 3000 chars of pr-writer/prototype-pr-writer",
    )
    writer_window = text[max(0, writer_pos - 600) : writer_pos + 1200].lower()
    _require_all(
        writer_window,
        ["fail-expected", "pending", "prototype-test pr"],
        "prototype-test-pr-writer row",
    )

    convention_pos = lowered.find("prototype-pending-tests.md")
    _require(convention_pos >= 0, "AGENTS.md missing prototype-pending-tests.md row")
    review_pos = lowered.find("prototype-review.md")
    _require(review_pos >= 0, "AGENTS.md missing prototype-review.md anchor")
    _require(
        abs(convention_pos - review_pos) <= 3000,
        "prototype-pending-tests.md row is not within 3000 chars of prototype-review.md",
    )


def check_workflows_index_noop() -> None:
    path = REPO_ROOT / "workflows/index.json"
    if not path.exists():
        raise CheckFailed("missing workflows/index.json")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    _require(
        digest == WORKFLOWS_INDEX_BASELINE_SHA256,
        f"workflows/index.json sha256 changed: {digest}",
    )


CHECKS = {
    "operator_format": check_operator_format,
    "pending_marker_convention": check_pending_marker_convention,
    "build_prototype_edits": check_build_prototype_edits,
    "prototype_orchestrator_edits": check_prototype_orchestrator_edits,
    "prototype_review_edits": check_prototype_review_edits,
    "pipeline_carry_forward": check_pipeline_carry_forward,
    "agentsmd_rows": check_agentsmd_rows,
    "workflows_index_noop": check_workflows_index_noop,
}


def _run_check(name: str) -> tuple[str, bool, str | None]:
    try:
        CHECKS[name]()
    except CheckFailed as exc:
        return name, False, str(exc)
    return name, True, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="run every check")
    group.add_argument("--check", choices=sorted(CHECKS), help="run one check")
    args = parser.parse_args(argv)

    selected = list(CHECKS) if args.all else [args.check]
    results = [_run_check(name) for name in selected]

    for name, passed, message in results:
        if passed:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}: {message}")

    failed = [(name, message) for name, passed, message in results if not passed]
    if failed:
        print("FAILING CHECKS SUMMARY:")
        for name, message in failed:
            print(f"- {name}: {message}")
        return 1

    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
