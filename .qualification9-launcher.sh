#!/usr/bin/env bash
set -euo pipefail
exec /home/nes/ai/tools/direct-codex-child/launch.sh "$@" --ephemeral --log-max-bytes 33554432
