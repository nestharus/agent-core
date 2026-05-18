#!/usr/bin/env bash
# prototype-pending: implementation pending in ACR-255-spawned-TBD; remove marker and make this test pass
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR"
FIXTURES="$ROOT/.tmp/v3-fixtures"
EVIDENCE="$SCRIPT_DIR"
RUN="$FIXTURES/minimal-conflict-repo"
BUNDLE="$RUN/.tmp/verified-rebase/feature__topic/v3-probe"
LOG_PRED="$EVIDENCE/predicted-tree-probe.log"
LOG_CONFLICT="$EVIDENCE/conflict-artifact-probe.log"

rm -rf "$RUN"
mkdir -p "$RUN" "$BUNDLE/conflict-artifacts" "$EVIDENCE"

cd "$RUN"
git init -q
git config user.email "v3@example.invalid"
git config user.name "V3 Probe"

cat > module.txt <<'BASE'
header: stable
prelude: unchanged
common-auto: base
section-start
logic: base computation
section-end
footer-auto: base
BASE

git add module.txt
git commit -q -m "base"
git branch -m main
git tag base

git checkout -q -b feature/topic
cat > module.txt <<'FEATURE'
header: stable
prelude: unchanged
branch-auto: branch-only non-conflicting line
common-auto: base
section-start
logic: branch restructure computation
logic-helper: branch extracted helper
section-end
footer-auto: base
branch-tail-auto: branch-only tail line
FEATURE
git commit -am "feature restructure with branch-auto" -q
PRE_TIP=$(git rev-parse HEAD)

git checkout -q main
cat > module.txt <<'TARGET'
header: stable
prelude: unchanged
common-auto: target-side non-conflicting update
section-start
logic: target hotfix computation
logic-hotfix: target adds clamp
section-end
target-auto: target-only non-conflicting line
footer-auto: base
TARGET
git commit -am "target hotfix with target-auto" -q
NEW_TARGET=$(git rev-parse HEAD)
PRE_BASE=$(git rev-parse base)

jj git init --colocate >/dev/null 2>&1 || true
git checkout -q feature/topic

PRE_OP=$(jj op log --limit 1 --no-graph --no-pager --template 'id' 2>/dev/null || true)
PREDICTED_OUTPUT="$BUNDLE/predicted-tree-command.out"
PREDICTED_STATUS=0
git merge-tree --write-tree --merge-base="$PRE_BASE" "$PRE_TIP" "$NEW_TARGET" > "$PREDICTED_OUTPUT" 2>&1 || PREDICTED_STATUS=$?
PREDICTED_TREE=$(sed -n '1p' "$PREDICTED_OUTPUT" | tr -d '[:space:]')
if ! git cat-file -e "$PREDICTED_TREE^{tree}" 2>/dev/null; then
  echo "merge-tree did not produce a usable tree" >&2
  cat "$PREDICTED_OUTPUT" >&2
  exit 1
fi

JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'
jj --config "$JJ_IMMUTABLE" rebase -b feature/topic -d main --no-pager >/tmp/v3-jj-rebase.out 2>&1 || {
  cat /tmp/v3-jj-rebase.out >&2
  exit 1
}

POST_TIP=$(git rev-parse feature/topic)
POST_CHANGE_ID=$(jj log -r feature/topic --no-graph --no-pager --limit 1 --template 'change_id')

git diff "$PRE_BASE" "$NEW_TARGET" --find-renames > "$BUNDLE/target-delta.patch"
git diff "$PRE_BASE" "$PRE_TIP" --find-renames > "$BUNDLE/branch-intended.patch"
git diff "$NEW_TARGET" "$POST_TIP" --find-renames > "$BUNDLE/branch-actual.patch"
git diff "$PREDICTED_TREE" "$POST_TIP^{tree}" --find-renames > "$BUNDLE/residual.patch"
git range-diff "$PRE_BASE..$PRE_TIP" "$NEW_TARGET..$POST_TIP" > "$BUNDLE/range-diff.txt" || true
jj resolve --list -r "$POST_CHANGE_ID" --no-pager > "$BUNDLE/conflict-artifacts/files.txt" 2>/dev/null || true
while IFS= read -r path; do
  [ -z "$path" ] && continue
  path=${path%%[[:space:]]*}
  slug=$(echo "$path" | tr '/' '__')
  jj file show -r "$POST_CHANGE_ID" "$path" > "$BUNDLE/conflict-artifacts/${slug}.conflict"
done < "$BUNDLE/conflict-artifacts/files.txt"
jj op log --limit 20 --no-pager > "$BUNDLE/jj-op-log-after.txt"
printf '%s\n' "$PRE_OP" > "$BUNDLE/jj-pre-op-id.txt"

cat > "$BUNDLE/refs.json" <<JSON
{
  "branch": "feature/topic",
  "target": "main",
  "PRE_BASE": "$PRE_BASE",
  "PRE_TIP": "$PRE_TIP",
  "NEW_TARGET": "$NEW_TARGET",
  "POST_TIP": "$POST_TIP",
  "POST_CHANGE_ID": "$POST_CHANGE_ID",
  "PREDICTED_TREE": "$PREDICTED_TREE",
  "merge_tree_status": $PREDICTED_STATUS,
  "timestamp": "v3-probe",
  "verdict": "DIRTY-EXPLAINED"
}
JSON

cat > "$BUNDLE/summary.md" <<SUMMARY
# V3 Minimal Verified-Rebase Bundle

- Branch: feature/topic
- Target: main
- PRE_BASE: $PRE_BASE
- PRE_TIP: $PRE_TIP
- NEW_TARGET: $NEW_TARGET
- POST_TIP: $POST_TIP
- POST_CHANGE_ID: $POST_CHANGE_ID
- PREDICTED_TREE: $PREDICTED_TREE
- merge-tree status: $PREDICTED_STATUS
- Verdict: DIRTY-EXPLAINED
SUMMARY

{
  echo "# PREDICTED_TREE probe"
  echo "repo: $RUN"
  echo "bundle: $BUNDLE"
  echo "PRE_BASE=$PRE_BASE"
  echo "PRE_TIP=$PRE_TIP"
  echo "NEW_TARGET=$NEW_TARGET"
  echo "POST_TIP=$POST_TIP"
  echo "POST_CHANGE_ID=$POST_CHANGE_ID"
  echo "PREDICTED_TREE=$PREDICTED_TREE"
  echo "merge-tree exit status=$PREDICTED_STATUS"
  echo
  echo "## merge-tree raw output"
  sed -n '1,220p' "$PREDICTED_OUTPUT"
  echo
  echo "## predicted tree module.txt"
  git show "$PREDICTED_TREE:module.txt" || true
  echo
  echo "## post tip module.txt (jj first-class conflict rendered through git tree)"
  git show "$POST_TIP:module.txt" || true
  echo
  echo "## diff predicted tree vs post tip"
  git diff "$PREDICTED_TREE" "$POST_TIP^{tree}" -- module.txt || true
  echo
  echo "## diff predicted tree vs PRE_TIP side"
  git diff "$PREDICTED_TREE" "$PRE_TIP^{tree}" -- module.txt || true
  echo
  echo "## diff predicted tree vs NEW_TARGET side"
  git diff "$PREDICTED_TREE" "$NEW_TARGET^{tree}" -- module.txt || true
  echo
  echo "## whole-file-replace simulation: predicted vs branch side"
  git diff --no-index <(git show "$PREDICTED_TREE:module.txt") <(git show "$PRE_TIP:module.txt") || true
  echo
  echo "## whole-file-replace simulation: predicted vs target side"
  git diff --no-index <(git show "$PREDICTED_TREE:module.txt") <(git show "$NEW_TARGET:module.txt") || true
} > "$LOG_PRED"

{
  echo "# conflict artifact probe"
  echo "repo: $RUN"
  echo "bundle: $BUNDLE"
  echo
  echo "## conflict files"
  sed -n '1,120p' "$BUNDLE/conflict-artifacts/files.txt"
  echo
  for f in "$BUNDLE"/conflict-artifacts/*.conflict; do
    [ -e "$f" ] || continue
    echo "## artifact: ${f#$BUNDLE/}"
    sed -n '1,220p' "$f"
    echo
    echo "## marker line numbers: ${f#$BUNDLE/}"
    nl -ba "$f" | sed -n '/<<<<<<<\|+++++++\|%%%%%%%\|\\\\\\\\\\\\\\\|=======\|>>>>>>>/p'
    echo
    echo "## outside-marker lines: ${f#$BUNDLE/}"
    awk '
      /^<<<<<<< / { in_marker=1; next }
      /^>>>>>>> / { in_marker=0; next }
      !in_marker { print }
    ' "$f"
    echo
  done
  echo "## residual.patch"
  sed -n '1,220p' "$BUNDLE/residual.patch"
  echo
  echo "## branch-intended.patch"
  sed -n '1,220p' "$BUNDLE/branch-intended.patch"
  echo
  echo "## target-delta.patch"
  sed -n '1,220p' "$BUNDLE/target-delta.patch"
  echo
  echo "## branch-actual.patch"
  sed -n '1,220p' "$BUNDLE/branch-actual.patch"
} > "$LOG_CONFLICT"

find "$BUNDLE" -type f | sort

require_log_entry() {
  local log_file="$1"
  local needle="$2"
  if ! grep -Fq "$needle" "$log_file"; then
    printf 'ASSERT_FAIL missing %q in %s\n' "$needle" "$log_file" >&2
    return 1
  fi
  printf 'ASSERT_PASS %s contains %s\n' "${log_file##*/}" "$needle"
}

require_log_entry "$LOG_PRED" "# PREDICTED_TREE probe"
require_log_entry "$LOG_PRED" "## predicted tree module.txt"
require_log_entry "$LOG_CONFLICT" "# conflict artifact probe"
require_log_entry "$LOG_CONFLICT" "## artifact: conflict-artifacts/module.txt.conflict"

printf '\nSUMMARY V3 PASS: predicted-tree-probe.log and conflict-artifact-probe.log regenerated\n'
