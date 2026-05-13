#!/usr/bin/env python3
"""Orchestrate ACR-142 structural verification checks."""

from __future__ import annotations

import sys

import check_child_operators
import check_operator
import check_workflow
import check_workflow_links
import check_writer_links
import parse as parse_module
import report
from read import read_files


PATHS_BY_CHECK = {
    "workflow": ["workflows/prototype-validation-shipping.md"],
    "operator": ["agents/prototype-validation-orchestrator.md"],
    "child_operators": [
        "agents/prototype-validation-contract-validator.md",
        "agents/prototype-validation-screenshot-uploader.md",
        "agents/prototype-validation-packager.md",
        "agents/prototype-validation-proof-bundle-adapter.md",
    ],
    "workflow_links": [
        "workflows/build-prototype.md",
        "workflows/prototype-research-planning.md",
        "workflows/rca-prototype.md",
        "workflows/implementation-pipeline.md",
    ],
    "writer_links": [
        "agents/prototype-pr-writer.md",
        "agents/pr-writer.md",
    ],
}


def main(argv: list[str] | None = None) -> int:
    parsed_args = parse_module.parse_cli_flags(sys.argv[1:] if argv is None else argv)
    findings: list[dict[str, str]] = []

    for check_name in parsed_args.checks:
        paths = PATHS_BY_CHECK[check_name]
        loaded = read_files(paths)
        documents = {path: parse_module.parse_document(path, loaded) for path in paths}

        if check_name == "workflow":
            findings.extend(check_workflow.check(documents[paths[0]]))
        elif check_name == "operator":
            findings.extend(check_operator.check(documents[paths[0]]))
        elif check_name == "child_operators":
            findings.extend(check_child_operators.check(documents))
        elif check_name == "workflow_links":
            findings.extend(check_workflow_links.check(documents))
        elif check_name == "writer_links":
            findings.extend(check_writer_links.check(documents))

    print(report.render(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
