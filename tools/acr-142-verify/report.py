"""Report formatting for the ACR-142 structural verifier."""

from __future__ import annotations

from collections import defaultdict

Finding = dict[str, str]


def render(findings: list[Finding]) -> str:
    if not findings:
        return "PASS: all ACR-142 structural checks passed."
    return render_grouped(findings)


def render_grouped(findings: list[Finding]) -> str:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.get("check", "unknown")].append(finding)

    lines = [
        f"FAIL: ACR-142 structural verifier found {len(findings)} issue(s).",
    ]
    for check_name, group_findings in grouped.items():
        lines.append("")
        lines.append(f"[{check_name}]")
        for finding in group_findings:
            path = finding.get("path", "<unknown>")
            code = finding.get("code", "missing_anchor")
            anchor = finding.get("anchor", "")
            message = finding.get("message", "")
            anchor_text = f" {anchor}" if anchor else ""
            lines.append(f"- {path} :: {code}{anchor_text} :: {message}")
    return "\n".join(lines)
