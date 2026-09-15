"""Deterministic, local-only test worker; no providers or external services."""
import json
import os
from pathlib import Path
import signal
import sys

request = json.load(sys.stdin)
step = request['step']
with Path('calls.jsonl').open('a') as stream:
    stream.write(json.dumps(step['id']) + '\n')
mode = step['input']
if mode == 'kill-executor':
    os.kill(os.getppid(), signal.SIGKILL)
    sys.exit(0)
if mode == 'empty':
    sys.exit(0)
if mode == 'bad-json':
    print('not a result')
    sys.exit(0)
if mode == 'nonzero':
    print(json.dumps({'outcome': 'success', 'detail': 'untrustworthy process claim'}))
    print('failure stderr', file=sys.stderr)
    sys.exit(7)
if mode == 'failure':
    print(json.dumps({'outcome': 'failure', 'detail': 'missing local prerequisite: seed'}))
elif mode == 'judgment':
    print(json.dumps({'outcome': 'judgment', 'detail': 'choose local prerequisite'}))
elif mode == 'recover':
    assert 'missing local prerequisite: seed' in request['edits'][-1]['reason']
    Path('seed').write_text('available')
    print(json.dumps({'outcome': 'success', 'detail': 'local prerequisite created'}))
elif mode == 'finish':
    assert Path('seed').read_text() == 'available'
    print(json.dumps({'outcome': 'success', 'detail': 'prerequisite consumed'}))
else:
    print(json.dumps({'outcome': 'success', 'detail': 'ordinary fake work completed'}))
