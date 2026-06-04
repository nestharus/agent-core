#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
OUT="${1:-$ROOT/.tmp/v1-fixtures/proof}"
REPO="$OUT/repo"
BUNDLE="$OUT/bundle"

rm -rf "$OUT"
mkdir -p "$REPO" "$BUNDLE/conflict-artifacts"

git -C "$REPO" init -q -b main
git -C "$REPO" config user.email "prototype@example.com"
git -C "$REPO" config user.name "Prototype Fixture"

cat > "$REPO/f.txt" <<'EOF'
base header
common top
common before conflict
base conflict line
common after conflict
common before dev
common bottom
EOF

git -C "$REPO" add f.txt
git -C "$REPO" commit -q -m "base"
git -C "$REPO" branch dev

perl -0pi -e 's/common top/main auto top/' "$REPO/f.txt"
perl -0pi -e 's/base conflict line/main conflict line/' "$REPO/f.txt"
git -C "$REPO" commit -am "main changes" -q

git -C "$REPO" checkout -q dev
perl -0pi -e 's/base conflict line/dev conflict line/' "$REPO/f.txt"
perl -0pi -e 's/common before dev/dev auto lower/' "$REPO/f.txt"
git -C "$REPO" commit -am "dev changes" -q

PRE_BASE="$(git -C "$REPO" merge-base dev main)"
PRE_TIP="$(git -C "$REPO" rev-parse dev)"
NEW_TARGET="$(git -C "$REPO" rev-parse main)"

set +e
MERGE_TREE_OUTPUT="$(git -C "$REPO" merge-tree --write-tree --merge-base="$PRE_BASE" "$PRE_TIP" "$NEW_TARGET" 2>"$OUT/merge-tree.stderr")"
MERGE_TREE_RC=$?
set -e
printf "%s\n" "$MERGE_TREE_OUTPUT" > "$OUT/merge-tree.stdout"
PREDICTED_TREE="$(printf "%s\n" "$MERGE_TREE_OUTPUT" | sed -n '1p')"

git -C "$REPO" diff "$PRE_BASE" "$NEW_TARGET" --find-renames > "$BUNDLE/target-delta.patch"
git -C "$REPO" diff "$PRE_BASE" "$PRE_TIP" --find-renames > "$BUNDLE/branch-intended.patch"
printf "f.txt\n" > "$BUNDLE/conflict-artifacts/files.txt"
git -C "$REPO" show "$PREDICTED_TREE:f.txt" > "$BUNDLE/conflict-artifacts/f.txt.conflict"

git -C "$REPO" checkout -q -b outcome-correct main
cat > "$REPO/f.txt" <<'EOF'
base header
main auto top
common before conflict
stitched conflict resolution keeps intent from both sides
common after conflict
dev auto lower
common bottom
EOF
git -C "$REPO" commit -am "correct hunk-only resolution" -q
CORRECT_TREE="$(git -C "$REPO" rev-parse HEAD^{tree})"

git -C "$REPO" checkout -q -b outcome-replace-main main
git -C "$REPO" show main:f.txt > "$REPO/f.txt"
git -C "$REPO" commit --allow-empty -am "whole file replace with main" -q
REPLACE_MAIN_TREE="$(git -C "$REPO" rev-parse HEAD^{tree})"

git -C "$REPO" checkout -q -b outcome-replace-dev main
git -C "$REPO" show dev:f.txt > "$REPO/f.txt"
git -C "$REPO" commit -am "whole file replace with dev" -q
REPLACE_DEV_TREE="$(git -C "$REPO" rev-parse HEAD^{tree})"

cat > "$BUNDLE/refs.json" <<EOF
{
  "branch": "dev",
  "target": "main",
  "PRE_BASE": "$PRE_BASE",
  "PRE_TIP": "$PRE_TIP",
  "NEW_TARGET": "$NEW_TARGET",
  "POST_TIP": null,
  "POST_CHANGE_ID": null,
  "PREDICTED_TREE": "$PREDICTED_TREE",
  "timestamp": "synthetic-v1",
  "verdict": "synthetic",
  "merge_tree_rc": $MERGE_TREE_RC
}
EOF

git -C "$REPO" diff "$NEW_TARGET" "$CORRECT_TREE" --find-renames > "$BUNDLE/branch-actual.patch"
git -C "$REPO" diff "$PREDICTED_TREE" "$CORRECT_TREE" --find-renames > "$BUNDLE/residual.patch"

cat > "$OUT/trees.env" <<EOF
REPO=$REPO
BUNDLE=$BUNDLE
PRE_BASE=$PRE_BASE
PRE_TIP=$PRE_TIP
NEW_TARGET=$NEW_TARGET
PREDICTED_TREE=$PREDICTED_TREE
CORRECT_TREE=$CORRECT_TREE
REPLACE_MAIN_TREE=$REPLACE_MAIN_TREE
REPLACE_DEV_TREE=$REPLACE_DEV_TREE
MERGE_TREE_RC=$MERGE_TREE_RC
EOF

printf "fixture=%s\n" "$OUT"
printf "repo=%s\n" "$REPO"
printf "bundle=%s\n" "$BUNDLE"
printf "merge_tree_rc=%s\n" "$MERGE_TREE_RC"
printf "predicted_tree=%s\n" "$PREDICTED_TREE"
printf "correct_tree=%s\n" "$CORRECT_TREE"
printf "replace_main_tree=%s\n" "$REPLACE_MAIN_TREE"
printf "replace_dev_tree=%s\n" "$REPLACE_DEV_TREE"
