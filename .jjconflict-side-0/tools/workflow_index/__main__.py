"""CLI entrypoint for workflow index generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generator import check_index, write_index


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.workflow_index",
        description="Generate or check workflows/index.json from workflow frontmatter.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Defaults to nearest cwd ancestor containing workflows/.",
    )
    common.add_argument(
        "--workflows-dir",
        default="workflows",
        help="Workflow docs directory, resolved relative to --repo-root.",
    )
    common.add_argument(
        "--output",
        default="workflows/index.json",
        help="Index output path, resolved relative to --repo-root.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "generate", parents=[common], help="Write the generated workflow index."
    )
    subparsers.add_parser(
        "check", parents=[common], help="Compare checked-in index to regenerated output."
    )

    args = parser.parse_args()
    repo_root = _resolve_repo_root(args.repo_root)
    workflows_dir = _resolve_path(repo_root, args.workflows_dir)
    output = _resolve_path(repo_root, args.output)

    try:
        if args.command == "generate":
            write_index(workflows_dir, output)
        elif args.command == "check":
            matches, diff_text = check_index(workflows_dir, output)
            if not matches:
                print(diff_text, file=sys.stderr, end="" if diff_text.endswith("\n") else "\n")
                sys.exit(2)
    except Exception as error:
        print(f"workflow-index: {error}", file=sys.stderr)
        sys.exit(1)


def _resolve_repo_root(repo_root: str | None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()

    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "workflows").is_dir():
            return candidate
    raise FileNotFoundError(
        f"No workflows/ directory found in {current} or any parent. "
        "Use --repo-root to specify the repository root explicitly."
    )


def _resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path


if __name__ == "__main__":
    main()
