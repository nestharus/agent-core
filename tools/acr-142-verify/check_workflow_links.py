"""Workflow cross-link validators for the ACR-142 structural verifier."""

from __future__ import annotations

Finding = dict[str, str]
ParsedWorkflowLinks = dict[str, dict[str, object]]

WORKFLOW_LINK_PATHS = [
    "workflows/build-prototype.md",
    "workflows/prototype-research-planning.md",
    "workflows/rca-prototype.md",
    "workflows/implementation-pipeline.md",
]
BOUNDED_LANGUAGE = [
    "handoff",
    "cross-reference",
    "pointer",
    "passive",
    "later consumer",
    "caller",
    "handback",
    "alternative",
    "prototype-as-deliverable",
    "shippable prototype",
]


def check(parsed: ParsedWorkflowLinks) -> list[Finding]:
    findings: list[Finding] = []
    for path in WORKFLOW_LINK_PATHS:
        document = parsed[path]
        text = str(document.get("text", ""))
        lowered = text.lower()
        if not document.get("exists"):
            findings.append(_finding(path, "missing_file", path, "workflow sibling file is absent"))
            continue
        if "prototype-validation-shipping.md" not in lowered:
            findings.append(_finding(path, "missing_cross_link", "prototype-validation-shipping.md", "sibling workflow lacks validation-shipping cross-reference"))
        if "prototype-validation-shipping.md" in lowered and not any(term in lowered for term in BOUNDED_LANGUAGE):
            findings.append(_finding(path, "missing_bounded_language", "bounded cross-reference / handoff language", "cross-link must be bounded handoff language"))
    return findings


def _finding(path: str, code: str, anchor: str, message: str) -> Finding:
    return {
        "check": "workflow_links",
        "path": path,
        "code": code,
        "anchor": anchor,
        "message": message,
    }
