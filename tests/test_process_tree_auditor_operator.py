import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESS_TREE_AUDITOR = REPO_ROOT / "agents" / "process-tree-auditor.md"
ORCHESTRATOR = REPO_ROOT / "agents" / "implementation-pipeline-orchestrator.md"


def _read(path):
    return path.read_text(encoding="utf-8")


def _process_tree_auditor_text():
    return _read(PROCESS_TREE_AUDITOR)


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


def _assert_regex(text, pattern, *, where):
    assert re.search(pattern, text, flags=re.MULTILINE | re.DOTALL), (
        f"{where} missing required pattern: {pattern}"
    )


def _pta_section(heading_regex):
    return _section(_process_tree_auditor_text(), heading_regex)


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


def test_pta_b14_canonical_output_path_field_documented():
    manifest = _pta_section(r"Expected Process Manifest")

    _assert_contains_all(
        manifest,
        (
            "canonical_output_path",
            "expected_verdict",
            "expected_sha256",
        ),
        where="Expected Process Manifest canonical-output row schema",
    )
    _assert_regex(
        manifest,
        r"expected_sha256.*optional|optional.*expected_sha256",
        where="Expected Process Manifest expected_sha256 optionality",
    )


def test_pta_b15_expected_verdict_tagged_union_shape():
    manifest = _pta_section(r"Expected Process Manifest")

    _assert_regex(
        manifest,
        r"expected_verdict:\s*\n\s*type:\s*exact\|regex\s*\n\s*value:",
        where="Expected Process Manifest tagged expected_verdict shape",
    )


def test_pta_b16_stat_and_read_procedure_documented():
    procedure = _pta_section(r"Procedure")

    _assert_regex(
        procedure,
        r"Step 4:.*canonical_output_path.*stat.*read.*parse verdict.*compare.*expected_verdict.*expected_sha256.*sha256",
        where="Procedure Step 4 canonical stat/read/verdict/hash sequence",
    )


def test_pta_b17_canonical_output_missing_block_class():
    procedure = _pta_section(r"Procedure")

    _assert_regex(
        procedure,
        r"canonical_output_missing.*blocking|blocking.*canonical_output_missing",
        where="Procedure canonical_output_missing block class",
    )


def test_pta_b18_canonical_output_modified_block_class():
    procedure = _pta_section(r"Procedure")

    _assert_regex(
        procedure,
        r"canonical_output_modified.*sha256.*blocking|sha256.*canonical_output_modified.*blocking|blocking.*canonical_output_modified.*sha256",
        where="Procedure canonical_output_modified block class",
    )


def test_pta_b19_canonical_output_missing_unexplained_block_class():
    procedure = _pta_section(r"Procedure")

    _assert_regex(
        procedure,
        r"canonical_output_missing_unexplained.*deletion.*blocking|deletion.*canonical_output_missing_unexplained.*blocking|blocking.*canonical_output_missing_unexplained.*deletion",
        where="Procedure canonical_output_missing_unexplained block class",
    )


def test_pta_b20_deletion_evidence_parsing_rule_documented():
    procedure = _pta_section(r"Procedure")

    _assert_contains_all(
        procedure,
        (
            "audit_history_path",
            "### Canonical Output Deletion",
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
        where="Procedure deletion-evidence parsing rule",
    )
    _assert_regex(
        procedure,
        r"replacement_path.*stat.*read.*verdict.*replacement_sha256",
        where="Procedure replacement verification rule",
    )


def test_pta_b21_distrust_of_derived_evidence_declared():
    non_negotiables = _pta_section(r"Non-Negotiables")

    _assert_contains_all(
        non_negotiables,
        (
            "WROTE:",
            "orchestrator stdout",
            "prior PASS verdicts",
            "agents-result JSON",
            "successful trace nodes",
            "cannot prove current canonical-output existence/content",
        ),
        where="Non-Negotiables derived-evidence distrust rule",
    )


def test_pta_b22_degraded_mode_documented():
    procedure = _pta_section(r"Procedure")

    _assert_regex(
        procedure,
        r"expected_sha256.*absent.*stat.*read.*parse.*verdict",
        where="Procedure degraded mode without expected_sha256",
    )
    _assert_contains_all(
        procedure,
        (
            "path + verdict-regex only",
            "degraded mode",
        ),
        where="Procedure degraded-mode limitation language",
    )


def test_pta_b23_join_manifest_composition_documented():
    manifest = _pta_section(r"Expected Process Manifest")

    _assert_regex(
        manifest,
        r"canonical_output_path.*projects directly|projects directly.*canonical_output_path",
        where="Expected Process Manifest canonical_output_path projection",
    )
    _assert_regex(
        manifest,
        r"sha256.*expected_sha256|expected_sha256.*sha256",
        where="Expected Process Manifest sha256 projection",
    )
    _assert_contains_all(
        manifest,
        (
            "verdict expectation comes from the gate contract",
            "not from `verdict_line`",
        ),
        where="Expected Process Manifest verdict expectation source",
    )


def test_pta_o1_orchestrator_phase4_canonical_projection_documented():
    phase4 = _phase4_section()

    _assert_contains_all(
        phase4,
        (
            "expected_process",
            "phase-4-join-manifest.json",
            "canonical_output_path",
            "expected_verdict",
            "expected_sha256",
            "sha256",
            "gate contract",
            "not from `verdict_line`",
        ),
        where="Phase 4 process-tree audit canonical-row projection",
    )


def test_pta_o2_orchestrator_phase8_canonical_projection_documented():
    phase8 = _phase8_section()

    _assert_contains_all(
        phase8,
        (
            "expected_process",
            "phase-8-join-manifest.json",
            "canonical_output_path",
            "expected_verdict",
            "expected_sha256",
            "sha256",
            "gate contract",
            "not from `verdict_line`",
        ),
        where="Phase 8 process-tree audit canonical-row projection",
    )
