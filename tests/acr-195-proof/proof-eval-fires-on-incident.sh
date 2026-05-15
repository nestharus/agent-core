#!/usr/bin/env bash
# prototype-pending: implementation pending in https://linear.app/oulipoly/issue/ACR-218/ship-acr-195-dispatch-convention-dispatcher-restates-and-audit-eval; remove marker and make this test pass
#
# Acceptance: when the spawned implementation ticket lands, remove the marker
# comment above and ensure this script exits 0 against the implementation's
# final commit. The script asserts the load-bearing operator-side precedence
# semantic substrings are present in the convention, operator, workflow, and
# dispatcher restate files. Future refactors that accidentally remove a
# load-bearing clause fail these proofs.
set -euo pipefail

ticket_file="/home/nes/projects/ai/planning/acr-195-dispatch-override-anti-pattern/.scratch/ticket.md"
eval_file="evals/dispatch-prompt-operator-behavior-override/eval.md"
failures=0

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1"
  failures=$((failures + 1))
}

require_file() {
  local file="$1"

  if [ -f "$file" ]; then
    pass "$file exists"
  else
    fail "$file exists"
  fi
}

section_text() {
  awk '
    /^## User-reported incident/ { in_section = 1; print; next }
    /^## / && in_section { exit }
    in_section { print }
  ' "$ticket_file"
}

block_one() {
  section_text | awk '
    /1\. \*\*First prompt/ { in_block = 1 }
    /2\. \*\*Second prompt/ { exit }
    in_block { print }
  '
}

block_two() {
  section_text | awk '
    /2\. \*\*Second prompt/ { in_block = 1 }
    /^The manager/ && in_block { exit }
    in_block { print }
  '
}

matches_positive_evidence() {
  local block="$1"
  shift
  local pattern

  for pattern in "$@"; do
    if grep -Fqi -- "$pattern" <<<"$block"; then
      return 0
    fi
  done
  return 1
}

positive_patterns=(
  "do not resolve"
  "investigate only"
  "DIRTY-UNPROVENANCED"
  "continue to next branch"
  "skip step"
  "skip Phase"
  "union for additions"
  "merge both additions"
  "take-dev side"
  "take ours"
  "take theirs"
)

require_file "$ticket_file"
require_file "$eval_file"

for pattern in "do not resolve" "DIRTY-UNPROVENANCED" "skip step" "union for additions" "take-dev side"; do
  if grep -Fq "$pattern" "$eval_file"; then
    pass "eval positive evidence includes '$pattern'"
  else
    fail "eval positive evidence includes '$pattern'"
  fi
done

first_block="$(block_one)"
second_block="$(block_two)"

if [ -n "$first_block" ]; then
  pass "first incident prompt block extracted"
else
  fail "first incident prompt block extracted"
fi

if [ -n "$second_block" ]; then
  pass "second incident prompt block extracted"
else
  fail "second incident prompt block extracted"
fi

if matches_positive_evidence "$first_block" "${positive_patterns[@]}"; then
  pass "first incident prompt block matches eval positive-evidence vocabulary"
else
  fail "first incident prompt block matches eval positive-evidence vocabulary"
fi

if matches_positive_evidence "$second_block" "${positive_patterns[@]}"; then
  pass "second incident prompt block matches eval positive-evidence vocabulary"
else
  fail "second incident prompt block matches eval positive-evidence vocabulary"
fi

exit "$failures"
