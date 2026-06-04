#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


START = "<<<<<<< "
MID = "======="
END = ">>>>>>> "


def run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{proc.stderr}")
    return proc.stdout


def show_file(repo: Path, treeish: str, path: str) -> list[str]:
    try:
        data = run_git(repo, "show", f"{treeish}:{path}")
    except SystemExit as exc:
        raise SystemExit(f"missing {path} in {treeish}: {exc}")
    return data.splitlines(keepends=True)


def split_conflict_template(lines: list[str]) -> tuple[list[list[str]], int]:
    segments: list[list[str]] = [[]]
    conflict_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(START):
            conflict_count += 1
            i += 1
            while i < len(lines) and not lines[i].startswith(END):
                i += 1
            if i == len(lines):
                raise SystemExit("unterminated conflict marker block in predicted file")
            i += 1
            segments.append([])
            continue
        if line.startswith(MID) or line.startswith(END):
            raise SystemExit("malformed conflict marker block in predicted file")
        segments[-1].append(line)
        i += 1
    return segments, conflict_count


def find_segment(haystack: list[str], needle: list[str], start: int) -> int:
    if not needle:
        return start
    limit = len(haystack) - len(needle)
    for idx in range(start, limit + 1):
        if haystack[idx : idx + len(needle)] == needle:
            return idx
    return -1


def template_matches(predicted: list[str], resolved: list[str]) -> tuple[bool, str]:
    segments, conflict_count = split_conflict_template(predicted)
    if conflict_count == 0:
        if predicted == resolved:
            return True, "no conflicts and exact file match"
        return False, "no conflict markers in predicted file; resolved content differs"

    pos = 0
    for index, segment in enumerate(segments):
        found = find_segment(resolved, segment, pos)
        if found < 0:
            preview = "".join(segment[:3]).rstrip("\n")
            return False, f"missing outside-marker segment {index}: {preview!r}"
        if index == 0 and found != 0:
            return False, "resolved file added/changed content before first outside-marker segment"
        pos = found + len(segment)

    last_segment = segments[-1]
    if last_segment and pos != len(resolved):
        return False, "resolved file added/changed content after last outside-marker segment"
    return True, f"{conflict_count} conflict block(s) treated as wildcard; outside-marker content preserved"


def detect(bundle: Path, repo: Path, post_tree: str) -> int:
    refs = json.loads((bundle / "refs.json").read_text())
    predicted_tree = refs["PREDICTED_TREE"]
    files_path = bundle / "conflict-artifacts" / "files.txt"
    paths = [line.strip() for line in files_path.read_text().splitlines() if line.strip()]

    failures = []
    clean = []
    for path in paths:
        predicted = show_file(repo, predicted_tree, path)
        resolved = show_file(repo, post_tree, path)
        ok, reason = template_matches(predicted, resolved)
        if ok:
            clean.append((path, reason))
        else:
            failures.append((path, reason))

    for path, reason in clean:
        print(f"OK {path}: {reason}")
    for path, reason in failures:
        print(f"WHOLE_FILE_REPLACE_SUSPECT {path}: {reason}")

    if failures:
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--post-tree", required=True)
    args = parser.parse_args()
    return detect(args.bundle, args.repo, args.post_tree)


if __name__ == "__main__":
    sys.exit(main())
