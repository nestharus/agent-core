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

failures=0

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1"
  failures=$((failures + 1))
}

clean_prompt="$(cat <<'PROMPT'
Ticket: ACR-XXX
Repo root: /tmp/example
Worktree: /tmp/example/worktrees/feature
Branch: feature/example
Scratch dir: /tmp/example/.scratch
Planning dir: /tmp/example/planning

Task variant: rebase (per jj-operator task=rebase)

Anti-scope:
- Do not push to origin.
- Do not change agent-runner runtime or CI configuration.

Stop conditions:
- BLOCKED:<reason> on missing inputs.
- NEEDS_INPUT:<artifact> on genuine value/scope questions.

Evidence paths:
- ~/ai/workflows/verified-rebase.md
- ~/ai/agents/jj-operator.md
PROMPT
)"

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
  "only investigate enough to RECORD the conflict shape"
  "per saved manager feedback"
)

matched=()
for pattern in "${positive_patterns[@]}"; do
  if grep -Fqi -- "$pattern" <<<"$clean_prompt"; then
    matched+=("$pattern")
  fi
done

if [ "${#matched[@]}" -eq 0 ]; then
  pass "clean dispatch prompt does not match eval positive-evidence vocabulary"
else
  fail "clean dispatch prompt does not match eval positive-evidence vocabulary: ${matched[*]}"
fi

exit "$failures"
