"""PR-writer link validators for the ACR-142 structural verifier."""

from __future__ import annotations

Finding = dict[str, str]
ParsedWriterLinks = dict[str, dict[str, object]]

PROTOTYPE_WRITER = "agents/prototype-pr-writer.md"
PRODUCTION_WRITER = "agents/pr-writer.md"
REQUIRED_PROTOTYPE_INPUTS = [
    "truth_branch_ref",
    "proposal_path",
    "behavior_tests_paths",
    "test_results",
    "qa_walkthrough_report_path",
    "qa_screenshots_dir",
    "deliverable_paths",
]
ADAPTER_HANDOFF_ANCHORS = [
    "prototype-validation-proof-bundle-adapter.md",
    "screenshot_url_manifest_path",
    "proof_bundle_path",
]


def check(parsed: ParsedWriterLinks) -> list[Finding]:
    findings: list[Finding] = []
    prototype_doc = parsed[PROTOTYPE_WRITER]
    production_doc = parsed[PRODUCTION_WRITER]

    prototype_text = str(prototype_doc.get("text", ""))
    production_text = str(production_doc.get("text", ""))

    if not prototype_doc.get("exists"):
        findings.append(_finding(PROTOTYPE_WRITER, "missing_file", PROTOTYPE_WRITER, "prototype PR writer file is absent"))
    for required_input in REQUIRED_PROTOTYPE_INPUTS:
        if required_input not in prototype_text:
            findings.append(_finding(PROTOTYPE_WRITER, "missing_required_input", required_input, "prototype writer required input is absent"))
    for anchor in ADAPTER_HANDOFF_ANCHORS:
        if anchor not in prototype_text:
            findings.append(_finding(PROTOTYPE_WRITER, "missing_adapter_handoff", anchor, "prototype writer lacks validation-shipping adapter handoff reference"))

    if not production_doc.get("exists"):
        findings.append(_finding(PRODUCTION_WRITER, "missing_file", PRODUCTION_WRITER, "production PR writer file is absent"))
    production_lower = production_text.lower()
    if "production" not in production_lower or "implementation" not in production_lower:
        findings.append(_finding(PRODUCTION_WRITER, "missing_production_identity", "production implementation PR writer", "production PR writer identity is not explicit"))
    if "prototype-validation-proof-bundle-adapter.md" in production_text:
        findings.append(_finding(PRODUCTION_WRITER, "mixed_writer_scope", "prototype-validation-proof-bundle-adapter.md", "production writer must remain distinct from prototype proof-bundle adapter"))

    return findings


def _finding(path: str, code: str, anchor: str, message: str) -> Finding:
    return {
        "check": "writer_links",
        "path": path,
        "code": code,
        "anchor": anchor,
        "message": message,
    }
