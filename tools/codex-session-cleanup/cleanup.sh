#!/bin/sh
set -eu
exec python3 "$(dirname "$(realpath -- "$0")")/cleanup.py" "$@"
