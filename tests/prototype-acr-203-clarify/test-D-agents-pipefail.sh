#!/usr/bin/env bash
#
# Purpose: prove `set -o pipefail` preserves a nonzero `agents` exit through
# `2>&1 | tee` when the runner fails before provider execution.
# Expected verdict: RESULT: PIPEFAIL_PROPAGATES
# Command: tests/prototype-acr-203-clarify/test-D-agents-pipefail.sh
# Originating evidence: /home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-D-agents-native-completion.md
#
# Optional environment:
#   AGENTS_BIN=/home/nes/.local/bin/agents
#   WORKTREE_PATH=/home/nes/projects/ai/worktrees/prototype-acr-203-clarify

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
worktree_path="${WORKTREE_PATH:-$(cd "$script_dir/../.." && pwd)}"
agents_bin="${AGENTS_BIN:-/home/nes/.local/bin/agents}"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/acr-203-D.XXXXXX")"
prompt="$scratch/prompt.md"
log="$scratch/invalid-model.log"

cleanup() {
  rm -rf "$scratch"
}
trap cleanup EXIT

cat >"$prompt" <<'PROMPT'
This prompt should never reach a provider because the model name is invalid.
PROMPT

set +e
"$agents_bin" -m __acr_203_missing_model__ -p "$worktree_path" -f "$prompt" 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
set -e
agents_status="${statuses[0]}"
tee_status="${statuses[1]}"
pipeline_status=0
if [ "$tee_status" -ne 0 ]; then
  pipeline_status="$tee_status"
elif [ "$agents_status" -ne 0 ]; then
  pipeline_status="$agents_status"
fi

if [ "$pipeline_status" -eq 0 ]; then
  echo "FAIL: pipeline unexpectedly exited 0"
  exit 1
fi

if [ "$agents_status" -eq 0 ]; then
  echo "FAIL: agents command unexpectedly exited 0"
  exit 1
fi

if [ "$tee_status" -ne 0 ]; then
  echo "FAIL: tee command failed with status $tee_status"
  exit 1
fi

if ! grep -q 'Unknown model' "$log"; then
  echo "FAIL: expected invalid-model error was not present in log"
  exit 1
fi

echo "pipeline_status: $pipeline_status"
echo "agents_status: $agents_status"
echo "tee_status: $tee_status"
echo "RESULT: PIPEFAIL_PROPAGATES"
