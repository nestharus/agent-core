#!/usr/bin/env bash
#
# Purpose: prove sentinel-last fanout completion works when each gate writes a
# report, verifies it is non-empty, and only then touches its sentinel.
# Expected verdict: RESULT: SENTINEL_LAST_WORKS
# Command: tests/prototype-acr-203-clarify/test-B-sentinel-last-works.sh
# Originating evidence: /home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-B-sentinel-fanout.md

set -euo pipefail

scratch="$(mktemp -d "${TMPDIR:-/tmp}/acr-203-B-last.XXXXXX")"
reports="$scratch/reports"
sentinels="$scratch/sentinels"
mkdir -p "$reports" "$sentinels"

cleanup() {
  jobs -pr | xargs -r kill 2>/dev/null || true
  rm -rf "$scratch"
}
trap cleanup EXIT

gate() {
  name="$1"
  delay="$2"
  report="$reports/gate-$name.md"
  sentinel="$sentinels/gate-$name.done"

  sleep "$delay"
  {
    echo "# Gate $name"
    echo
    echo "Verdict: LOW"
  } >"$report"
  test -s "$report"
  touch "$sentinel"
}

gate A 1 &
gate B 2 &
gate C 3 &
gate D 4 &

while :; do
  if [ -e "$sentinels/gate-A.done" ] &&
     [ -e "$sentinels/gate-B.done" ] &&
     [ -e "$sentinels/gate-C.done" ] &&
     [ -e "$sentinels/gate-D.done" ]; then
    break
  fi
  [ "$SECONDS" -gt 12 ] && break
  sleep 0.2
done

wait

missing=0
for gate_name in A B C D; do
  if [ ! -e "$sentinels/gate-$gate_name.done" ]; then
    echo "FAIL: missing sentinel for gate $gate_name"
    missing=1
  fi
  if [ ! -s "$reports/gate-$gate_name.md" ]; then
    echo "FAIL: missing or empty report for gate $gate_name"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  exit 1
fi

echo "all_sentinels_present: yes"
echo "all_reports_present: yes"
echo "elapsed_seconds: $SECONDS"
echo "RESULT: SENTINEL_LAST_WORKS"
