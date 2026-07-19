"""Workflow validators for the ACR-142 structural verifier."""

from __future__ import annotations

Finding = dict[str, str]
ParsedWorkflow = dict[str, object]

WORKFLOW_PATH = "workflows/prototype-validation-shipping.md"
REQUIRED_HEADINGS = [
    "Declared roles",
    "Lifecycle Procedure",
    "Contracts",
    "Structural Verification Anchors",
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
REQUIRED_CONTRACT_ANCHORS = [
    "branch_topology_contract",
    "validation_gate_contract",
    "rca_handback_contract",
    "screenshot_url_manifest_contract",
    "proof_bundle_contract",
    "artifact_cleanup_contract",
]


def check(parsed: ParsedWorkflow) -> list[Finding]:
    findings: list[Finding] = []
    path = str(parsed["path"])
    text = str(parsed.get("text", ""))
    frontmatter = parsed.get("frontmatter")
    heading_texts = {heading.text for heading in parsed.get("headings", [])}
    phase_labels = set(parsed.get("phase_labels", []))
    anchor_names = {
        anchor.name.lower() for anchor in parsed.get("anchors", [])
    } | {
        " ".join(anchor.columns).lower() for anchor in parsed.get("anchors", [])
    }

    if not parsed.get("exists"):
        findings.append(_finding(path, "missing_file", WORKFLOW_PATH, "required workflow file is absent"))

    if not isinstance(frontmatter, dict):
        findings.append(_finding(path, "missing_frontmatter", "workflow frontmatter", "missing YAML frontmatter"))
    else:
        workflow = frontmatter.get("workflow")
        dispatch = frontmatter.get("workflow_dispatch_contract")
        roles = frontmatter.get("declared_roles")
        if not isinstance(workflow, dict) or workflow.get("id") != "prototype-validation-shipping":
            findings.append(_finding(path, "missing_anchor", "workflow.id", "expected prototype-validation-shipping"))
        if not isinstance(dispatch, dict) or dispatch.get("orchestrator") != "prototype-validation-orchestrator":
            findings.append(_finding(path, "missing_anchor", "workflow_dispatch_contract.orchestrator", "expected prototype-validation-orchestrator"))
        if not isinstance(roles, list):
            findings.append(_finding(path, "missing_anchor", "declared_roles", "expected declared roles list"))
        else:
            for role in ("orchestration", "validator"):
                if role not in roles:
                    findings.append(_finding(path, "missing_anchor", role, "workflow declared role missing"))

    for heading in REQUIRED_HEADINGS:
        if heading not in heading_texts:
            findings.append(_finding(path, "missing_heading", f"## {heading}", "required workflow heading is absent"))

    for phase in REQUIRED_PHASES:
        if phase not in phase_labels:
            findings.append(_finding(path, "missing_phase", phase, "required workflow phase label is absent"))

    lowered = text.lower()
    for anchor in REQUIRED_CONTRACT_ANCHORS:
        in_table = any(anchor.lower() in name for name in anchor_names)
        if anchor.lower() not in lowered and not in_table:
            findings.append(_finding(path, "missing_anchor", anchor, "required workflow contract anchor is absent"))

    return findings


def _finding(path: str, code: str, anchor: str, message: str) -> Finding:
    return {
        "check": "workflow",
        "path": path,
        "code": code,
        "anchor": anchor,
        "message": message,
    }
