#!/usr/bin/env bash
#
# Purpose: prove the negative case: a sentinel-only watcher can advance too
# early when a gate touches its sentinel before writing its report.
# Expected verdict: RESULT: SENTINEL_FIRST_RACE_OBSERVED
# Command: tests/prototype-acr-203-clarify/test-B-sentinel-first-races.sh
# Originating evidence: /home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-B-sentinel-fanout.md
#
# This test passes when the race is observed. That is intentional: it confirms
# sentinel-last discipline is load-bearing for sub-workflows that internally
# fan out and use sentinel files as a completion backstop.

set -euo pipefail

scratch="$(mktemp -d "${TMPDIR:-/tmp}/acr-203-B-race.XXXXXX")"
reports="$scratch/reports"
sentinels="$scratch/sentinels"
mkdir -p "$reports" "$sentinels"

cleanup() {
  jobs -pr | xargs -r kill 2>/dev/null || true
  rm -rf "$scratch"
}
trap cleanup EXIT

report="$reports/gate-race.md"
sentinel="$sentinels/gate-race.done"

(
  touch "$sentinel"
  sleep 2
  {
    echo "# Gate race"
    echo
    echo "Verdict: LOW"
  } >"$report"
) &
gate_pid=$!

while [ ! -e "$sentinel" ]; do
  [ "$SECONDS" -gt 5 ] && break
  sleep 0.05
done

if [ -e "$sentinel" ] && [ ! -s "$report" ]; then
  race_observed=1
else
  race_observed=0
fi

wait "$gate_pid"

if [ "$race_observed" -ne 1 ]; then
  echo "FAIL: watcher did not observe sentinel-before-report race"
  echo "sentinel_present=$([ -e "$sentinel" ] && echo yes || echo no)"
  echo "report_present_at_check=$([ -s "$report" ] && echo yes || echo no)"
  exit 1
fi

echo "sentinel_present_at_watcher_exit: yes"
echo "report_missing_at_watcher_exit: yes"
echo "report_eventually_present: $([ -s "$report" ] && echo yes || echo no)"
echo "RESULT: SENTINEL_FIRST_RACE_OBSERVED"
