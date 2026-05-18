#!/usr/bin/env bash
# prototype-pending: implementation pending in ACR-257; remove marker and make this test pass
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURE_ROOT="${FIXTURE_ROOT:-$SCRIPT_DIR/.tmp/v1-fixtures/proof}"
DETECTOR="$SCRIPT_DIR/detector.py"

printf '# fixture setup\n'
"$SCRIPT_DIR/fixture-setup.sh" "$FIXTURE_ROOT"

# shellcheck disable=SC1091
source "$FIXTURE_ROOT/trees.env"

printf '\n# predicted conflict file\n'
git -C "$REPO" show "$PREDICTED_TREE:f.txt"

run_case() {
  local label="$1"
  local tree="$2"
  local expected_status="$3"
  local expected_text="$4"
  local status=0
  local output

  printf '\n# %s\n' "$label"
  set +e
  output="$("$DETECTOR" --bundle "$BUNDLE" --repo "$REPO" --post-tree "$tree" 2>&1)"
  status=$?
  set -e
  printf '%s\n' "$output"
  printf 'exit=%s\n' "$status"

  if [[ "$status" != "$expected_status" ]]; then
    printf 'ASSERT_FAIL %s: expected exit %s, got %s\n' "$label" "$expected_status" "$status" >&2
    return 1
  fi
  if [[ "$output" != *"$expected_text"* ]]; then
    printf 'ASSERT_FAIL %s: expected output containing %q\n' "$label" "$expected_text" >&2
    return 1
  fi
  printf 'ASSERT_PASS %s\n' "$label"
}

run_case "correct hunk-only resolution" "$CORRECT_TREE" 0 "OK f.txt"
run_case "whole-file replace with main" "$REPLACE_MAIN_TREE" 2 "WHOLE_FILE_REPLACE_SUSPECT f.txt"
run_case "whole-file replace with dev" "$REPLACE_DEV_TREE" 2 "WHOLE_FILE_REPLACE_SUSPECT f.txt"

printf '\nSUMMARY V1 PASS: correct=OK replace-main=SUSPECT replace-dev=SUSPECT\n'
