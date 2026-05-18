#!/usr/bin/env python3
import argparse
import difflib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


NOISE_TOKENS = {
    "aria",
    "button",
    "class",
    "const",
    "default",
    "div",
    "export",
    "function",
    "label",
    "return",
    "span",
    "svg",
}


def run(repo, args):
    return subprocess.check_output(args, cwd=repo, text=True, stderr=subprocess.DEVNULL)


def git_show(repo, rev, path):
    return run(repo, ["git", "show", f"{rev}:{path}"])


def git_log_subjects(repo, base, rev, path):
    output = run(repo, ["git", "log", "--format=%s", f"{base}..{rev}", "--", path])
    return [line.strip() for line in output.splitlines() if line.strip()]


def strip_comments_and_space(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"//.*$", "", line)
        line = re.sub(r"#.*$", "", line)
        collapsed = re.sub(r"\s+", "", line)
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines)


def is_substantive(base, side):
    return strip_comments_and_space(base) != strip_comments_and_space(side)


def line_stats(base, side):
    matcher = difflib.SequenceMatcher(a=base.splitlines(), b=side.splitlines())
    added = 0
    deleted = 0
    changed_blocks = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed_blocks += 1
        deleted += i2 - i1
        added += j2 - j1
    return {
        "added": added,
        "deleted": deleted,
        "total": added + deleted,
        "blocks": changed_blocks,
    }


def has_keyword(subjects, pattern):
    joined = "\n".join(subjects).lower()
    return re.search(pattern, joined) is not None


def tokens(text):
    split_tokens = []
    for raw in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        pieces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw).replace("_", " ").split()
        split_tokens.extend(piece.lower() for piece in pieces)
    return [token for token in split_tokens if len(token) > 3 and token not in NOISE_TOKENS]


def added_tokens(base, side):
    base_counts = Counter(tokens(base))
    side_counts = Counter(tokens(side))
    added = []
    for token, count in side_counts.items():
        extra = count - base_counts.get(token, 0)
        if extra > 0:
            added.extend([token] * extra)
    return added


def removed_tokens(base, side):
    base_counts = Counter(tokens(base))
    side_counts = Counter(tokens(side))
    removed = []
    for token, count in base_counts.items():
        missing = count - side_counts.get(token, 0)
        if missing > 0:
            removed.extend([token] * missing)
    return removed


def typo_fix_superseded(base, unpicked, resolved, subjects):
    if not has_keyword(subjects, r"\b(typo|spelling)\b"):
        return False
    resolved_tokens = Counter(tokens(resolved))
    added = added_tokens(base, unpicked)
    removed = removed_tokens(base, unpicked)
    added_present = all(resolved_tokens[token] > 0 for token in added) if added else True
    removed_absent = all(resolved_tokens[token] == 0 for token in removed) if removed else True
    return added_present and removed_absent


def classify_one(repo, bundle, path, mode):
    refs = json.loads((bundle / "refs.json").read_text())
    base = git_show(repo, refs["PRE_BASE"], path)
    target = git_show(repo, refs["NEW_TARGET"], path)
    branch = git_show(repo, refs["PRE_TIP"], path)
    resolved = git_show(repo, refs["POST_TIP"], path)

    sides = {
        "target": {
            "text": target,
            "subjects": git_log_subjects(repo, refs["PRE_BASE"], refs["NEW_TARGET"], path),
            "stats": line_stats(base, target),
            "substantive": is_substantive(base, target),
        },
        "branch": {
            "text": branch,
            "subjects": git_log_subjects(repo, refs["PRE_BASE"], refs["PRE_TIP"], path),
            "stats": line_stats(base, branch),
            "substantive": is_substantive(base, branch),
        },
    }
    for side in sides.values():
        side["hotfix"] = has_keyword(side["subjects"], r"\b(fix|hotfix|patch|bug)\b")
        side["restructure"] = has_keyword(
            side["subjects"], r"\b(refactor|restructure|extract|helper|move|rename)\b"
        )

    picked = None
    if resolved == target:
        picked = "target"
    elif resolved == branch:
        picked = "branch"

    if not picked:
        return {
            "path": path,
            "verdict": "QUIET",
            "reason": "resolution does not equal either side verbatim",
            "sides": sides,
        }

    unpicked = "branch" if picked == "target" else "target"
    picked_side = sides[picked]
    unpicked_side = sides[unpicked]

    if not unpicked_side["substantive"]:
        return {
            "path": path,
            "verdict": "QUIET",
            "reason": f"picked {picked}; unpicked {unpicked} is cosmetic/non-substantive",
            "sides": sides,
        }

    hotfix_restructure_pair = (
        picked_side["hotfix"] and unpicked_side["restructure"]
    ) or (
        picked_side["restructure"] and unpicked_side["hotfix"]
    )
    hunk_shape_risky = (
        picked_side["stats"]["total"] >= max(5, int(unpicked_side["stats"]["total"] * 1.5))
        and 0 < unpicked_side["stats"]["total"] <= 8
    )

    if mode == "hunk-shape":
        if hunk_shape_risky:
            verdict = "FIRE"
            reason = (
                f"picked {picked}; {picked} hunk total={picked_side['stats']['total']} "
                f"dominates small unpicked {unpicked} total={unpicked_side['stats']['total']}"
            )
        else:
            verdict = "QUIET"
            reason = "hunk-shape thresholds not met"
    elif mode == "commit-log":
        if hotfix_restructure_pair:
            verdict = "FIRE"
            reason = f"picked {picked}; commit subjects show hotfix/restructure pair"
        else:
            verdict = "QUIET"
            reason = "commit subjects do not show hotfix/restructure pair"
    elif mode == "combined":
        if typo_fix_superseded(base, unpicked_side["text"], resolved, unpicked_side["subjects"]):
            verdict = "QUIET"
            reason = f"picked {picked}; unpicked {unpicked} typo/spelling fix appears superseded"
        elif hotfix_restructure_pair:
            verdict = "FIRE"
            reason = (
                f"picked {picked} verbatim; commit subjects show hotfix/restructure pair "
                f"and unpicked intent is not superseded"
            )
        else:
            verdict = "QUIET"
            reason = "combined hotfix/restructure and hunk-shape signal not met"
    else:
        raise ValueError(mode)

    return {
        "path": path,
        "verdict": verdict,
        "reason": reason,
        "picked": picked,
        "unpicked": unpicked,
        "sides": sides,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["hunk-shape", "commit-log", "combined"], required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("bundle")
    args = parser.parse_args()

    repo = Path(args.repo)
    bundle = Path(args.bundle)
    paths = [
        line.strip()
        for line in (bundle / "conflict-artifacts" / "files.txt").read_text().splitlines()
        if line.strip()
    ]

    any_fire = False
    for path in paths:
        result = classify_one(repo, bundle, path, args.mode)
        any_fire = any_fire or result["verdict"] == "FIRE"
        print(f"{result['verdict']} {path}: {result['reason']}")
        for side_name in ("target", "branch"):
            side = result["sides"][side_name]
            subjects = "; ".join(side["subjects"]) or "(none)"
            print(
                f"  {side_name}: total={side['stats']['total']} blocks={side['stats']['blocks']} "
                f"substantive={side['substantive']} hotfix={side['hotfix']} "
                f"restructure={side['restructure']} subjects={subjects}"
            )
    if not paths:
        print("QUIET no conflict paths")
    print(f"SUMMARY mode={args.mode} verdict={'FIRE' if any_fire else 'QUIET'}")


if __name__ == "__main__":
    main()
