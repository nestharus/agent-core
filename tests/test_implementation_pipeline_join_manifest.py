import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _orchestrator_text():
    return _read(ORCHESTRATOR)


def _section(text, heading_regex):
    match = re.search(rf"(?m)^(?P<level>##+) {heading_regex}\s*$", text)
    assert match, f"missing section heading matching: {heading_regex}"

    level = match.group("level")
    next_heading = re.search(rf"(?m)^{re.escape(level)} ", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def _assert_contains_all(text, phrases, *, where):
    missing = [phrase for phrase in phrases if phrase not in text]
    assert missing == [], f"{where} missing required text: {missing}"


def _assert_ordered(text, phrases, *, where):
    cursor = 0
    for phrase in phrases:
        index = text.find(phrase, cursor)
        assert index != -1, f"{where} missing ordered text after offset {cursor}: {phrase}"
        cursor = index + len(phrase)


def _phase4_section():
    return _section(
        _orchestrator_text(),
        r"Phase 4 \u2014 Risk Gates \(parallel\) \+ Process-tree Audit #1",
    )


def _phase8_section():
    return _section(
        _orchestrator_text(),
        r"Phase 8 \u2014 Post-CodeRabbit Gates \+ Process-tree Audit #3",
    )


def _reverification_section():
    return _section(_orchestrator_text(), r"Canonical Join Manifest Re-Verification")


def _violation_detection_section():
    return _section(_orchestrator_text(), r"Violation Detection and Escalation")


def test_phase4_writes_join_manifest_after_low_gate_before_supported_surface():
    phase4 = _phase4_section()

    _assert_ordered(
        phase4,
        (
            "All four must return LOW",
            "phase-4-join-manifest.json",
            "supported-surface termination",
            "Process-tree audit #1",
        ),
        where="Phase 4 join-manifest ordering",
    )


def test_phase4_join_manifest_has_canonical_output_identity_fields():
    phase4 = _phase4_section()

    _assert_contains_all(
        phase4,
        (
            "${planning_dir}/risk/phase-4-join-manifest.json",
            "one object per gate (`audit`, `scope`, `shortcut`, `supported-surface`)",
            "gate_name",
            "producing_invocation_uuid",
            "agents trace --json",
            "most recent completed child invocation",
            "missing phase artifact",
            "canonical_output_path",
            "size",
            "mtime",
            "sha256",
            "verdict_line",
            "verified_at",
        ),
        where="Phase 4 join-manifest identity fields",
    )


def test_phase4_verdict_line_is_read_from_canonical_path():
    phase4 = _phase4_section()

    _assert_contains_all(
        phase4,
        (
            "from the canonical path on disk",
            "not trusted from stdout",
        ),
        where="Phase 4 verdict-line disposition rule",
    )


def test_phase8_writes_join_manifest_after_pr_review_gates_before_split_audit():
    phase8 = _phase8_section()

    _assert_ordered(
        phase8,
        (
            "test-audit",
            "multi-concern",
            "justification",
            "commit-hygiene",
            "phase-4-join-manifest.json",
            "phase-8-join-manifest.json",
            "split",
            "Process-tree audit #3",
        ),
        where="Phase 8 join-manifest ordering",
    )


def test_phase8_join_manifest_has_canonical_output_identity_fields():
    phase8 = _phase8_section()

    _assert_contains_all(
        phase8,
        (
            "${planning_dir}/risk/phase-8-join-manifest.json",
            "${planning_dir}/risk/${wu_lower}-<gate>.md",
            "test-audit",
            "multi-concern",
            "justification",
            "commit-hygiene",
            "gate_name",
            "producing_invocation_uuid",
            "agents trace --json",
            "most recent completed child invocation",
            "missing phase artifact",
            "canonical_output_path",
            "size",
            "mtime",
            "sha256",
            "verdict_line",
            "verified_at",
        ),
        where="Phase 8 join-manifest identity fields",
    )


def test_phase8_verdict_line_is_read_from_canonical_path():
    phase8 = _phase8_section()

    _assert_contains_all(
        phase8,
        (
            "from the canonical path on disk",
            "not trusted from stdout",
        ),
        where="Phase 8 verdict-line disposition rule",
    )


def test_join_manifest_reverification_blocks_stale_or_changed_outputs():
    reverification = _reverification_section()

    _assert_contains_all(
        reverification,
        (
            "every resume start",
            "every phase join",
            "prior PASS state",
            "previously recorded LOW, non-blocking, or PASS gate/audit result",
            "size",
            "mtime",
            "sha256",
            "verdict_line",
            "BLOCKED:join-manifest-mismatch",
        ),
        where="Canonical Join Manifest Re-Verification",
    )
    assert (
        "final PASS" in reverification or "final close" in reverification
    ), "Canonical Join Manifest Re-Verification missing final PASS or final close call site"


def test_violation_detection_names_join_manifest_mismatch():
    violation_detection = _violation_detection_section()

    assert (
        "join-manifest" in violation_detection
        or "join manifest mismatch" in violation_detection
    ), "Violation Detection missing join-manifest mismatch phrase"
    _assert_contains_all(
        violation_detection,
        (
            "missing canonical path",
            "stat",
            "sha256",
        ),
        where="Violation Detection join-manifest mismatch conditions",
    )
    assert (
        "verdict_line" in violation_detection or "verdict line" in violation_detection
    ), "Violation Detection missing changed verdict_line condition"


def test_intentional_canonical_report_removal_requires_audit_history_entry():
    reverification = _reverification_section()

    _assert_contains_all(
        reverification,
        (
            "actor",
            "timestamp",
            "manifest_path",
            "gate_name",
            "canonical_output_path",
            "old_sha256",
            "reason",
            "replacement_path",
            "replacement_sha256",
        ),
        where="intentional canonical-report removal audit-history entry",
    )
