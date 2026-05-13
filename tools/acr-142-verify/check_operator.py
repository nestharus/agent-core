"""Top-level operator validators for the ACR-142 structural verifier."""

from __future__ import annotations

Finding = dict[str, str]
ParsedOperator = dict[str, object]

OPERATOR_PATH = "agents/prototype-validation-orchestrator.md"
REQUIRED_SECTIONS = [
    "Role",
    "Use When",
    "Do Not Use When",
    "Inputs",
    "Outputs",
    "Procedure",
    "Stop Conditions",
]
REQUIRED_PHASES = [
    "Phase 0",
    "Phase 1",
    "Phase 2",
    "Phase 2b",
    "Phase 3",
    "Phase 4",
    "Phase 4b",
    "Phase 5",
    "Phase 6",
    "Phase 7",
    "Phase 8",
    "Phase 8b",
]
CHILD_OPERATORS = [
    "prototype-validation-contract-validator.md",
    "prototype-validation-screenshot-uploader.md",
    "prototype-validation-packager.md",
    "prototype-validation-proof-bundle-adapter.md",
]
HANDOFF_ANCHORS = [
    "rca_handback_path",
    "screenshot_url_manifest_path",
    "proof_bundle_path",
    "pr_writer_input_bundle_path",
    "package_manifest_path",
    "cleanup_report_path",
]
ORDERING_ANCHOR = "uploader_before_packager"


def check(parsed: ParsedOperator) -> list[Finding]:
    findings: list[Finding] = []
    path = str(parsed["path"])
    text = str(parsed.get("text", ""))
    normalized = str(parsed.get("normalized_text", ""))
    frontmatter = parsed.get("frontmatter")
    headings = {heading.text for heading in parsed.get("headings", [])}
    numbered_phase_labels = set(parsed.get("numbered_phase_labels", []))

    if not parsed.get("exists"):
        findings.append(_finding(path, "missing_file", OPERATOR_PATH, "required top-level operator file is absent"))
        findings.append(_finding(path, "missing_ordering_anchor", ORDERING_ANCHOR, "uploader dispatch ordering cannot be verified without the operator file"))

    if not isinstance(frontmatter, dict):
        findings.append(_finding(path, "missing_frontmatter", "operator frontmatter", "missing YAML frontmatter"))
    else:
        keys = set(frontmatter)
        expected = {"description", "model", "output_format"}
        if keys != expected:
            findings.append(_finding(path, "invalid_frontmatter", "description/model/output_format", f"expected exactly {sorted(expected)}, found {sorted(keys)}"))
        if frontmatter.get("model") != "claude-opus":
            findings.append(_finding(path, "missing_anchor", "model: claude-opus", "orchestrator model must be claude-opus"))

    for role in ("orchestration", "parser"):
        if role not in normalized:
            findings.append(_finding(path, "missing_role", role, "top-level operator declared/default role missing"))

    for section in REQUIRED_SECTIONS:
        if section not in headings:
            findings.append(_finding(path, "missing_heading", f"## {section}", "required operator section is absent"))
    if "Escalation" not in headings and "NEEDS_INPUT Handling" not in headings:
        findings.append(_finding(path, "missing_heading", "## Escalation or ## NEEDS_INPUT Handling", "required operator escalation section is absent"))

    for phase in REQUIRED_PHASES:
        if phase not in numbered_phase_labels:
            findings.append(_finding(path, "missing_numbered_phase", phase, "required numbered procedure sub-step is absent"))

    for child in CHILD_OPERATORS:
        if child not in text:
            findings.append(_finding(path, "missing_child_dispatch", child, "child-dispatch registry must name this operator"))

    for anchor in HANDOFF_ANCHORS:
        if anchor not in text:
            findings.append(_finding(path, "missing_handoff_anchor", anchor, "bounded handoff envelope reference is absent"))

    if "agents -m" not in text or "-f" not in text:
        findings.append(_finding(path, "missing_dispatch_shape", "agents -m <model> -f <prompt-file>", "child dispatch shape is absent"))

    _check_uploader_before_packager(parsed, findings)

    return findings


def _check_uploader_before_packager(parsed: ParsedOperator, findings: list[Finding]) -> None:
    if not parsed.get("exists"):
        return

    path = str(parsed["path"])
    procedure = str(parsed.get("procedure", ""))
    if not procedure:
        findings.append(_finding(path, "missing_ordering_anchor", ORDERING_ANCHOR, "procedure body is absent, so uploader-to-packager ordering cannot be verified"))
        return

    phase_blocks = parsed.get("procedure_phase_blocks", {})
    phase_3 = phase_blocks.get("Phase 3")
    phase_4b = phase_blocks.get("Phase 4b")
    packager_anchor = parsed.get("procedure_packager_proof_bundle_anchor")
    uploader_positions = list(parsed.get("procedure_uploader_dispatch_positions", []))
    walkthrough_positions = list(parsed.get("procedure_walkthrough_positions", []))

    invalid_reasons: list[str] = []
    if phase_3 is None:
        invalid_reasons.append("Phase 3 numbered procedure block is absent")
    if phase_4b is None:
        invalid_reasons.append("Phase 4b numbered procedure block is absent")
    if packager_anchor is None:
        invalid_reasons.append("packager proof-bundle assembly anchor is absent")
    if not uploader_positions:
        invalid_reasons.append("uploader dispatch anchor is absent from the procedure body")

    if phase_3 and not _block_has_ordered_uploader_after_walkthrough(phase_3, uploader_positions, walkthrough_positions):
        invalid_reasons.append("Phase 3 must place uploader dispatch after QA walkthrough prose")
    if phase_4b and not _block_has_ordered_uploader_after_walkthrough(phase_4b, uploader_positions, walkthrough_positions):
        invalid_reasons.append("Phase 4b must place uploader dispatch after QA walkthrough prose")

    allowed_blocks = [block for block in (phase_3, phase_4b) if block]
    for uploader_pos in uploader_positions:
        if not any(start <= uploader_pos < end for start, end in allowed_blocks):
            invalid_reasons.append("uploader dispatch appears outside Phase 3 / Phase 4b QA walkthrough blocks")
            break
        if packager_anchor is not None and uploader_pos > packager_anchor:
            invalid_reasons.append("uploader dispatch appears after packager proof-bundle assembly")
            break

    if packager_anchor is not None and phase_3 and phase_4b:
        if phase_3[1] > packager_anchor or phase_4b[1] > packager_anchor:
            invalid_reasons.append("Phase 3 and Phase 4b walkthrough blocks must both precede packager proof-bundle assembly")

    if invalid_reasons:
        findings.append(_finding(path, "missing_ordering_anchor", ORDERING_ANCHOR, "; ".join(dict.fromkeys(invalid_reasons))))


def _block_has_ordered_uploader_after_walkthrough(
    block: tuple[int, int],
    uploader_positions: list[int],
    walkthrough_positions: list[int],
) -> bool:
    block_uploaders = [position for position in uploader_positions if block[0] <= position < block[1]]
    if not block_uploaders:
        return False
    first_uploader = min(block_uploaders)
    return any(block[0] <= position < first_uploader for position in walkthrough_positions)


def _finding(path: str, code: str, anchor: str, message: str) -> Finding:
    return {
        "check": "operator",
        "path": path,
        "code": code,
        "anchor": anchor,
        "message": message,
    }
