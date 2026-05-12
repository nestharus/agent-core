"""Child-operator validators for the ACR-142 structural verifier."""

from __future__ import annotations

Finding = dict[str, str]
ParsedChildren = dict[str, dict[str, object]]

CHILD_SPECS = {
    "agents/prototype-validation-contract-validator.md": {
        "roles": ["validator"],
        "anchors": [
            ("root inputs", "root inputs"),
            ("branch separation", "branch separation"),
            ("phase output", "phase output"),
            ("stop condition", "stop condition"),
            ("rca envelope", "rca envelope"),
            ("proof bundle", "proof bundle"),
            ("cleanup scope", "cleanup scope"),
        ],
    },
    "agents/prototype-validation-screenshot-uploader.md": {
        "roles": ["accessor", "formatter"],
        "anchors": [
            ("upload_channel: gh_api_user_attachments", "upload channel: gh api user attachments"),
            ("gh api", "gh api"),
            ("user attachments", "user attachments"),
            ("screenshot_url_manifest_path", "screenshot url manifest path"),
        ],
    },
    "agents/prototype-validation-packager.md": {
        "roles": ["orchestration", "formatter"],
        "anchors": [
            ("image tag", "image tag"),
            ("zip path", "zip path"),
            ("package manifest", "package manifest"),
            ("proof bundle", "proof bundle"),
            ("cleanup report", "cleanup report"),
            ("validator approved", "validator approved"),
        ],
    },
    "agents/prototype-validation-proof-bundle-adapter.md": {
        "roles": ["parser", "orchestration"],
        "anchors": [
            ("truth_branch_ref", "truth branch ref"),
            ("proposal_path", "proposal path"),
            ("behavior_tests_paths", "behavior tests paths"),
            ("test_results", "test results"),
            ("qa_walkthrough_report_path", "qa walkthrough report path"),
            ("qa_screenshots_dir", "qa screenshots dir"),
            ("deliverable_paths", "deliverable paths"),
            ("prototype-pr-writer.md", "prototype pr writer.md"),
        ],
    },
}
REQUIRED_SECTIONS = [
    "Role",
    "Use When",
    "Do Not Use When",
    "Inputs",
    "Outputs",
    "Procedure",
    "Stop Conditions",
]
PACKAGER_PATH = "agents/prototype-validation-packager.md"
UPLOADER_PRODUCER = "prototype-validation-screenshot-uploader.md"
UPLOADER_MANIFEST_ANCHOR = "screenshot_url_manifest_path"


def check(parsed: ParsedChildren) -> list[Finding]:
    findings: list[Finding] = []
    for path, spec in CHILD_SPECS.items():
        document = parsed[path]
        normalized = str(document.get("normalized_text", ""))
        headings = {heading.text for heading in document.get("headings", [])}

        if not document.get("exists"):
            findings.append(_finding(path, "missing_file", path, "required child operator file is absent"))

        frontmatter = document.get("frontmatter")
        if not isinstance(frontmatter, dict):
            findings.append(_finding(path, "missing_frontmatter", "operator frontmatter", "missing YAML frontmatter"))
        else:
            keys = set(frontmatter)
            expected = {"description", "model", "output_format"}
            if keys != expected:
                findings.append(_finding(path, "invalid_frontmatter", "description/model/output_format", f"expected exactly {sorted(expected)}, found {sorted(keys)}"))

        for section in REQUIRED_SECTIONS:
            if section not in headings:
                findings.append(_finding(path, "missing_heading", f"## {section}", "required child-operator section is absent"))
        if "Escalation" not in headings and "NEEDS_INPUT Handling" not in headings:
            findings.append(_finding(path, "missing_heading", "## Escalation or ## NEEDS_INPUT Handling", "required child-operator escalation section is absent"))

        for role in spec["roles"]:
            if role not in normalized:
                findings.append(_finding(path, "missing_role", role, "child operator declared role missing"))

        for anchor, normalized_anchor in spec["anchors"]:
            if normalized_anchor not in normalized:
                findings.append(_finding(path, "missing_anchor", anchor, "required child-operator responsibility anchor is absent"))

        if path == PACKAGER_PATH:
            _check_packager_consumes_uploader_manifest(document, findings)

    return findings


def _check_packager_consumes_uploader_manifest(document: dict[str, object], findings: list[Finding]) -> None:
    path = PACKAGER_PATH
    if not document.get("exists"):
        findings.append(_finding(path, "missing_packager_uploader_manifest_consumption", f"{UPLOADER_MANIFEST_ANCHOR} from {UPLOADER_PRODUCER}", "packager file is absent, so uploader-manifest consumption cannot be verified"))
        return

    prose = str(document.get("responsibility_prose", ""))
    normalized = str(document.get("normalized_responsibility_prose", ""))
    has_manifest = "screenshot url manifest path" in normalized
    has_uploader_producer = UPLOADER_PRODUCER in prose
    has_consumption = any(token in normalized for token in ("consume", "consumes", "consuming", "consumed"))
    has_proof_bundle = "proof bundle" in normalized or "proof_bundle_path" in prose

    if not (has_manifest and has_uploader_producer and has_consumption and has_proof_bundle):
        findings.append(_finding(path, "missing_packager_uploader_manifest_consumption", f"{UPLOADER_MANIFEST_ANCHOR} from {UPLOADER_PRODUCER}", "packager must state that proof-bundle assembly consumes the uploader-produced screenshot URL manifest"))


def _finding(path: str, code: str, anchor: str, message: str) -> Finding:
    return {
        "check": "child_operators",
        "path": path,
        "code": code,
        "anchor": anchor,
        "message": message,
    }
