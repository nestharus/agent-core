#!/usr/bin/env bash
#
# Purpose: prove the current agents runner preserves a provider-authored WROTE:
# line at byte 0 of its own line in a merged `2>&1 | tee` log.
# Expected verdict: RESULT: LINE_START_PRESERVED
# Command: tests/prototype-acr-203-clarify/test-A-wrote-line-start.sh
# Originating evidence: /home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-A-runner-envelope.md
#
# Optional environment:
#   AGENTS_BIN=/home/nes/.local/bin/agents
#   WORKTREE_PATH=/home/nes/projects/ai/worktrees/prototype-acr-203-clarify

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
worktree_path="${WORKTREE_PATH:-$(cd "$script_dir/../.." && pwd)}"
agents_bin="${AGENTS_BIN:-/home/nes/.local/bin/agents}"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/acr-203-A.XXXXXX")"
prompt="$scratch/prompt.md"
log="$scratch/merged.log"

cleanup() {
  rm -rf "$scratch"
}
trap cleanup EXIT

cat >"$prompt" <<'PROMPT'
You are a runner-envelope probe.

Do not run commands. Do not write files. Do not explain anything.

Your entire final stdout response must be exactly one line:
WROTE: /tmp/acr-203-clarify-probe.txt
PROMPT

set +e
"$agents_bin" -m gpt-high -p "$worktree_path" -f "$prompt" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
agents_status="${statuses[0]}"
tee_status="${statuses[1]}"
pipeline_status=0
if [ "$agents_status" -ne 0 ] || [ "$tee_status" -ne 0 ]; then
  pipeline_status=1
fi

if [ "$pipeline_status" -ne 0 ] || [ "$agents_status" -ne 0 ]; then
  echo "FAIL: agents invocation failed pipeline_status=$pipeline_status agents_status=$agents_status tee_status=$tee_status"
  exit 1
fi

matches="$(LC_ALL=C grep -ab '^WROTE:' "$log" || true)"
match_count="$(printf '%s\n' "$matches" | sed '/^$/d' | wc -l | tr -d ' ')"
if [ "$match_count" -ne 1 ]; then
  echo "FAIL: expected exactly one line-start WROTE match, found $match_count"
  printf '%s\n' "$matches"
  exit 1
fi

offset="${matches%%:*}"
if [ "$offset" -gt 0 ]; then
  previous_byte="$(dd if="$log" bs=1 skip=$((offset - 1)) count=1 2>/dev/null | od -An -tx1 | tr -d ' \n')"
  if [ "$previous_byte" != "0a" ]; then
    echo "FAIL: byte before WROTE was 0x$previous_byte, expected newline 0x0a"
    exit 1
  fi
fi

echo "grep_match: $matches"
echo "RESULT: LINE_START_PRESERVED"
