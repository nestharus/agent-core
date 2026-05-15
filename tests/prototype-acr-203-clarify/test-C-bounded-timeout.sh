#!/usr/bin/env bash
#
# Purpose: prove a sentinel watcher with `[ $SECONDS -gt 10 ] && break` exits
# cleanly when the sentinel never appears and does not leave a child process.
# Expected verdict: RESULT: BOUNDED_TIMEOUT_CLEAN
# Command: tests/prototype-acr-203-clarify/test-C-bounded-timeout.sh
# Originating evidence: /home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-C-trap-cleanup.md

set -euo pipefail

sentinel="${TMPDIR:-/tmp}/acr-203-C-never-appears.$$"
rm -f "$sentinel"

cleanup() {
  jobs -pr | xargs -r kill 2>/dev/null || true
  rm -f "$sentinel"
}
trap cleanup EXIT INT TERM

start_epoch="$(date +%s)"
ticks=0

while [ ! -e "$sentinel" ]; do
  sleep 1 &
  child=$!
  wait "$child"
  ticks=$((ticks + 1))
  [ "$SECONDS" -gt 10 ] && break
done

end_epoch="$(date +%s)"
elapsed=$((end_epoch - start_epoch))

ps -p $$ -o pid=,ppid=,stat=,cmd=

children="$(jobs -pr)"
if [ -n "$children" ]; then
  echo "FAIL: child processes still attached to watcher: $children"
  exit 1
fi

if [ "$elapsed" -lt 10 ] || [ "$elapsed" -gt 13 ]; then
  echo "FAIL: elapsed seconds $elapsed outside expected bounded range"
  exit 1
fi

echo "ticks: $ticks"
echo "elapsed_seconds: $elapsed"
echo "child_processes_after_loop: none"
echo "RESULT: BOUNDED_TIMEOUT_CLEAN"
