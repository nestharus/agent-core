#!/usr/bin/env python3
"""Bounded file coordinator CLI. JSON stdin; credentials only from environment."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys

from runtime import Runtime, create, _pool
from storage import Held


def fixture(runtime, actor, credential, request):
    """Only bundled finite worker, no arbitrary shell/argv/provider execution."""
    required = {'attempt', 'collector'}
    if set(request) != required:
        raise Held('fixture needs exactly attempt and collector')
    start = runtime.call('start', actor, credential, **request, substrate='fixture', evidence='bundled finite fixture adapter')
    # Admission rechecked under the public pool lock through actual creation.
    # Persistent launching state precedes this boundary; a crash cannot authorize
    # another launch. No actual process handle can be recovered from a file.
    with runtime.files.transaction() as s:
        a = s['attempts'][request['attempt']]
        with runtime.pool(s).admission(a['pool']['profile'], blocking=False, expected_control=s['pool_binding']):
            child = subprocess.Popen([sys.executable, '-I', str(Path(__file__).with_name('fixture_worker.py'))],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     env={'PATH': os.defpath})
    output, _ = child.communicate(b'finish\n', timeout=5)
    if len(output) > 128:
        raise Held('fixture output invalid; preserve original custody')
    result = json.loads(output)
    return runtime.call('collect', actor, credential, **request, launch_id=start['launch_id'], end=child.returncode,
                        result=result, evidence='actual bundled Popen.communicate numeric END')


def watch(runtime, actor, credential, timeout):
    """Finite notification receiver, binds before initial durable scan."""
    if not 0 <= timeout <= 60:
        raise Held('watch timeout must be within 0..60 seconds')
    fd = os.open(runtime.files.path / 'watch.lock', os.O_RDWR | os.O_NOFOLLOW)
    bound = False
    directory = os.open(runtime.files.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            path = runtime.files.path / 'wake.sock'
            # Stale socket after crash is retained, not blindly unlinked.
            sock.bind('/proc/self/fd/' + str(directory) + '/wake.sock')
            bound = True
            initial = runtime.call('inbox', actor, credential)
            if initial['packets']:
                return initial
            select.select([sock], [], [], timeout)
            return runtime.call('inbox', actor, credential)
    finally:
        if bound:
            os.unlink(runtime.files.path / 'wake.sock')
        os.close(directory)
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument('--actor', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--routes', required=True)
    call = sub.add_parser('call')
    call.add_argument('operation')
    sub.add_parser('run-fixture')
    w = sub.add_parser('watch')
    w.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args()
    try:
        credential = os.environ.get('COORDINATOR_TOKEN', '')
        if args.command == 'init':
            result = create(args.state, args.actor, credential, args.routes)
        else:
            runtime = Runtime(args.state)
            if args.command == 'watch':
                result = watch(runtime, args.actor, credential, args.timeout)
            else:
                raw = sys.stdin.buffer.read(32769)
                if len(raw) > 32768:
                    raise Held('command exceeds 32KiB; not acquired further')
                request = json.loads(raw or '{}')
                if not isinstance(request, dict):
                    raise Held('JSON object required')
                if args.command == 'run-fixture':
                    result = fixture(runtime, args.actor, credential, request)
                else:
                    result = runtime.call(args.operation, args.actor, credential, **request)
        print(json.dumps({'status': 'ok', 'result': result}, sort_keys=True))
        return 0
    except (Held, _pool.PoolError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'held', 'reason': str(exc)[:512], 'replay': 'not authorized'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
