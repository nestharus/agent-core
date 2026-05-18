#!/usr/bin/env bash
# prototype-pending: implementation pending in ACR-255-spawned-TBD; remove marker and make this test pass
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VECTOR_WORKTREE="${VECTOR_WORKTREE:-$SCRIPT_DIR}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$SCRIPT_DIR}"
FIXTURE_ROOT="${FIXTURE_ROOT:-$VECTOR_WORKTREE/.tmp/v2-fixtures}"

"$EVIDENCE_DIR/fixture-setup.sh"

run_detector() {
  local mode="$1"
  local scenario="$2"
  local repo="$3"
  local bundle="$4"

  printf '\n## mode=%s scenario=%s\n' "$mode" "$scenario"
  "$EVIDENCE_DIR/detector.py" --mode "$mode" --repo "$repo" "$bundle"
}

run_detector hunk-shape hotfix-on-restructured \
  "$FIXTURE_ROOT/hotfix-on-restructured" \
  "$FIXTURE_ROOT/hotfix-on-restructured/bundle-bad-pick"
run_detector hunk-shape orthogonal-comment-pick \
  "$FIXTURE_ROOT/orthogonal-comment-pick" \
  "$FIXTURE_ROOT/orthogonal-comment-pick/bundle-legit-pick"
run_detector hunk-shape superseded-typo-pick \
  "$FIXTURE_ROOT/superseded-typo-pick" \
  "$FIXTURE_ROOT/superseded-typo-pick/bundle-legit-superseded"

run_detector commit-log hotfix-on-restructured \
  "$FIXTURE_ROOT/hotfix-on-restructured" \
  "$FIXTURE_ROOT/hotfix-on-restructured/bundle-bad-pick"
run_detector commit-log orthogonal-comment-pick \
  "$FIXTURE_ROOT/orthogonal-comment-pick" \
  "$FIXTURE_ROOT/orthogonal-comment-pick/bundle-legit-pick"
run_detector commit-log superseded-typo-pick \
  "$FIXTURE_ROOT/superseded-typo-pick" \
  "$FIXTURE_ROOT/superseded-typo-pick/bundle-legit-superseded"

run_detector combined hotfix-on-restructured \
  "$FIXTURE_ROOT/hotfix-on-restructured" \
  "$FIXTURE_ROOT/hotfix-on-restructured/bundle-bad-pick"
run_detector combined orthogonal-comment-pick \
  "$FIXTURE_ROOT/orthogonal-comment-pick" \
  "$FIXTURE_ROOT/orthogonal-comment-pick/bundle-legit-pick"
run_detector combined superseded-typo-pick \
  "$FIXTURE_ROOT/superseded-typo-pick" \
  "$FIXTURE_ROOT/superseded-typo-pick/bundle-legit-superseded"

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if [[ "$haystack" != *"$needle"* ]]; then
    printf 'ASSERT_FAIL missing expected output: %s\n' "$needle" >&2
    return 1
  fi
  printf 'ASSERT_PASS %s\n' "$needle"
}

combined_output="$("$EVIDENCE_DIR/detector.py" --mode combined --repo "$FIXTURE_ROOT/hotfix-on-restructured" "$FIXTURE_ROOT/hotfix-on-restructured/bundle-bad-pick")"
assert_contains "$combined_output" "SUMMARY mode=combined verdict=FIRE"
combined_output="$("$EVIDENCE_DIR/detector.py" --mode combined --repo "$FIXTURE_ROOT/orthogonal-comment-pick" "$FIXTURE_ROOT/orthogonal-comment-pick/bundle-legit-pick")"
assert_contains "$combined_output" "SUMMARY mode=combined verdict=QUIET"
combined_output="$("$EVIDENCE_DIR/detector.py" --mode combined --repo "$FIXTURE_ROOT/superseded-typo-pick" "$FIXTURE_ROOT/superseded-typo-pick/bundle-legit-superseded")"
assert_contains "$combined_output" "SUMMARY mode=combined verdict=QUIET"

printf '\nSUMMARY V2 PASS: hotfix-on-restructured=FIRE orthogonal-comment-pick=QUIET superseded-typo-pick=QUIET\n'
