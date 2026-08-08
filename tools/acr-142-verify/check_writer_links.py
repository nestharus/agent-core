"""PR-writer link validators for the ACR-142 structural verifier."""

from __future__ import annotations

import re

Finding = dict[str, str]
ParsedWriterLinks = dict[str, dict[str, object]]

PROTOTYPE_WRITER = "agents/prototype-pr-writer.md"
PRODUCTION_WRITER = "agents/pr-writer.md"
ADAPTER_PATH = "prototype-validation-evidence-bundle-adapter.md"
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
    ADAPTER_PATH,
    "screenshot_url_manifest_path",
    "experiment_evidence_bundle_path",
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
    if _has_active_adapter_reference(production_doc):
        findings.append(_finding(PRODUCTION_WRITER, "mixed_writer_scope", ADAPTER_PATH, "production writer must remain distinct from the prototype evidence-bundle adapter"))

    return findings


def _has_active_adapter_reference(document: dict[str, object]) -> bool:
    sections = document.get("sections", {})
    if isinstance(sections, dict) and sections:
        anti_scope_headings = ("do not use", "anti-scope", "out of scope")
        active_text = "\n\n".join(
            str(text)
            for heading, text in sections.items()
            if not any(marker in str(heading).lower() for marker in anti_scope_headings)
        )
    else:
        active_text = str(document.get("text", ""))

    negative_paragraph = re.compile(r"\b(?:do not use|must not|forbid(?:den)?|anti-scope)\b", re.IGNORECASE)
    return any(
        ADAPTER_PATH in paragraph and not negative_paragraph.search(paragraph)
        for paragraph in re.split(r"\n\s*\n", active_text)
    )


def _finding(path: str, code: str, anchor: str, message: str) -> Finding:
    return {
        "check": "writer_links",
        "path": path,
        "code": code,
        "anchor": anchor,
        "message": message,
    }
