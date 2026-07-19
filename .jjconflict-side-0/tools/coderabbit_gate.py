#!/usr/bin/env python3
"""Legacy helper for checking the repository-level CodeRabbit marker label."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote


def run_gh(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def resolve_repo(repo: str | None, worktree_path: str | None) -> tuple[str | None, str | None]:
    if repo:
        return repo, None

    result = run_gh(
        ["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=worktree_path,
    )
    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip()

    resolved = result.stdout.strip()
    if not resolved or "/" not in resolved:
        return None, f"could not resolve repo from gh output: {resolved!r}"
    return resolved, None


def write_output(path: str | None, payload: dict[str, object]) -> None:
    if not path:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="GitHub repo in owner/name form.")
    parser.add_argument("--worktree-path", help="Worktree used to resolve the GitHub repo when --repo is omitted.")
    parser.add_argument("--label", default="coderabbit", help="Repository marker label name. Default: coderabbit.")
    parser.add_argument("--output", help="Optional JSON verdict output path.")
    args = parser.parse_args()

    checked_at = datetime.now(UTC).isoformat()
    repo, repo_error = resolve_repo(args.repo, args.worktree_path)
    if repo_error or not repo:
        payload = {
            "checked_at": checked_at,
            "label": args.label,
            "reason": repo_error or "repo not supplied and could not be resolved",
            "source": "github-repo-label",
            "verdict": "BLOCKED:gh-repo-unresolved",
        }
        write_output(args.output, payload)
        print(payload["verdict"])
        return 2

    repo_check = run_gh(["api", f"/repos/{repo}"])
    if repo_check.returncode != 0:
        payload = {
            "checked_at": checked_at,
            "label": args.label,
            "reason": (repo_check.stderr or repo_check.stdout).strip(),
            "repo": repo,
            "source": "github-repo-label",
            "verdict": "BLOCKED:gh-auth-unavailable",
        }
        write_output(args.output, payload)
        print(payload["verdict"])
        return 2

    encoded_label = quote(args.label, safe="")
    label_check = run_gh(["api", f"/repos/{repo}/labels/{encoded_label}"])
    if label_check.returncode == 0:
        payload = {
            "checked_at": checked_at,
            "label": args.label,
            "reason": "CodeRabbit marker label exists on repository",
            "repo": repo,
            "source": "github-repo-label",
            "verdict": "ENABLED:github-label-present",
        }
        write_output(args.output, payload)
        print(payload["verdict"])
        return 0

    label_error = (label_check.stderr or label_check.stdout).strip()
    if "HTTP 404" in label_error or '"message": "Not Found"' in label_error or "Not Found" in label_error:
        payload = {
            "checked_at": checked_at,
            "label": args.label,
            "reason": "CodeRabbit marker label is absent from repository",
            "repo": repo,
            "source": "github-repo-label",
            "verdict": "SKIP:github-label-missing",
        }
        write_output(args.output, payload)
        print(payload["verdict"])
        return 0

    payload = {
        "checked_at": checked_at,
        "label": args.label,
        "reason": label_error,
        "repo": repo,
        "source": "github-repo-label",
        "verdict": "BLOCKED:gh-label-read-failed",
    }
    write_output(args.output, payload)
    print(payload["verdict"])
    return 2


if __name__ == "__main__":
    sys.exit(main())
