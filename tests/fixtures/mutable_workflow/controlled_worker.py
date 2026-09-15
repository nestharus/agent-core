"""Deterministic local effect/return barrier; loopback test controller only."""
from functools import partial
import json
from pathlib import Path
import signal
import socket
import sys

def report_ignored_cancel(controller, signum, frame):
    controller.sendall(b'cancel-observed\n')


def configure_cancel(controller, mode):
    if mode.get('ignore_cancel'):
        signal.signal(signal.SIGTERM, partial(report_ignored_cancel, controller))


request = json.load(sys.stdin)
with Path('effects.jsonl').open('a') as stream:
    stream.write(json.dumps(request) + '\n')
mode = request['step']['input']
if isinstance(mode, dict) and request['attempt_id'] == mode.get('hold_attempt', 1):
    with socket.create_connection(('127.0.0.1', mode['port']), timeout=15) as controller:
        configure_cancel(controller, mode)
        controller.sendall(b'effect-written\n')
        assert controller.recv(1) == b'R'
if mode == 'binary':
    sys.stdout.buffer.write(bytes(range(256)) * 8)
    sys.stderr.buffer.write(bytes(reversed(range(256))) * 9)
else:
    outcome = mode.get('outcome', 'success') if isinstance(mode, dict) else 'success'
    print(json.dumps({'outcome': outcome, 'detail': 'controlled local effect returned'}))
