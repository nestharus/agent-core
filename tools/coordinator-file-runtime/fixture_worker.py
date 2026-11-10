"""Finite scheduler fixture, never a role or a provider stand-in."""
import json
import sys

if sys.stdin.buffer.readline(16) != b'finish\n':
    raise SystemExit(3)
print(json.dumps({'fixture': 'completed', 'provider_acceptance': False}))
