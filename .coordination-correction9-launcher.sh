#!/usr/bin/env bash
set -euo pipefail
exec /home/nes/ai/tools/direct-codex-child/launch.sh "$@" --log-max-bytes 33554432
