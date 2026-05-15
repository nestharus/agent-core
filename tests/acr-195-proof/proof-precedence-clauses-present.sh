#!/usr/bin/env bash
# prototype-pending: implementation pending in https://linear.app/oulipoly/issue/ACR-217/ship-operator-side-caller-prompt-precedence-for-rebase-mechanics; remove marker and make this test pass
#
# Acceptance: when the spawned implementation ticket lands, remove the marker
# comment above and ensure this script exits 0 against the implementation's
# final commit. The script asserts the load-bearing operator-side precedence
# semantic substrings are present in the convention, operator, workflow, and
# dispatcher restate files. Future refactors that accidentally remove a
# load-bearing clause fail these proofs.
set -euo pipefail

failures=0

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1"
  failures=$((failures + 1))
}

contains() {
  local file="$1"
  local needle="$2"
  local label="$3"

  if grep -Fq "$needle" "$file"; then
    pass "$label"
  else
    fail "$label"
  fi
}

contains "agents/operator-file-format.md" "## Caller Prompt Precedence" \
  "operator-file-format has Caller Prompt Precedence heading"
contains "agents/operator-file-format.md" "The operator file's documented procedure is authoritative." \
  "operator-file-format asserts operator procedure authority"

jj_anchor_count=0
for needle in "conflict resolution" "verdict handling" "push/no-push handling" "phase shape"; do
  if grep -Fq "$needle" "agents/jj-operator.md"; then
    jj_anchor_count=$((jj_anchor_count + 1))
  fi
done
if [ "$jj_anchor_count" -ge 3 ]; then
  pass "jj-operator Non-Negotiables name at least three incident override classes"
else
  fail "jj-operator Non-Negotiables name at least three incident override classes"
fi

contains "agents/jj-operator.md" "treat it as a \`NEEDS_INPUT\` signal" \
  "jj-operator surfaces caller mechanics overrides as NEEDS_INPUT"
contains "workflows/verified-rebase.md" "Caller prompts do not override this workflow." \
  "verified-rebase carries mirrored caller-prompt override reminder"

if [ -f "conventions/no-operator-behavior-override-in-dispatch.md" ]; then
  pass "no-operator-behavior-override convention exists"
else
  fail "no-operator-behavior-override convention exists"
fi
contains "conventions/no-operator-behavior-override-in-dispatch.md" "Allowed dispatch content" \
  "convention contains allowed dispatch content table heading"
contains "conventions/no-operator-behavior-override-in-dispatch.md" "Forbidden dispatch override" \
  "convention contains forbidden dispatch override table heading"

for dispatcher in \
  "agents/work-manager-operator.md" \
  "agents/implementation-pipeline-orchestrator.md" \
  "agents/roadmap-orchestrator.md"; do
  contains "$dispatcher" "no-operator-behavior-override-in-dispatch" \
    "$dispatcher cites no-operator-behavior-override-in-dispatch"
done

exit "$failures"
