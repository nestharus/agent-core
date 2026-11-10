#!/usr/bin/env python3
"""Bounded file coordinator CLI. JSON stdin; credentials only from environment."""
import argparse
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

from runtime import Runtime, create, _pool, _fast, ALLOWED_PROFILES
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
    refusal = None
    with runtime.files.transaction() as s:
        a = s['attempts'][request['attempt']]
        runtime.attempt(s, actor, **request)
        entered_creation = False
        try:
            runtime.authority(s, actor, credential)
            runtime.partial_capacity(s)
            with runtime.pool(s).admission(a['pool']['profile'], ALLOWED_PROFILES, blocking=False, expected_control=s['pool_binding']):
                runtime.fast(s)
                with _fast.admission(Path(s['pool_routes']).with_name('fast-tier'), before_write=runtime.pool_capacity):
                    entered_creation = True
                    child = subprocess.Popen([sys.executable, '-I', str(Path(__file__).with_name('fixture_worker.py'))],
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                             env={'PATH': os.defpath})
        except (Held, _pool.PoolError, ValueError, OSError) as exc:
            if entered_creation:
                raise  # Creation/effects may be uncertain; never infer no launch.
            a.update(state='not-started', creation_refusal={'actor': actor, 'at': runtime.clock(),
                     'evidence': 'fixture control refused before Popen: ' + str(exc)[:512]})
            refusal = exc
        if refusal is not None:
            runtime.partial_capacity(s)
    if refusal is not None:
        raise refusal
    output, _ = child.communicate(b'finish\n', timeout=5)
    if len(output) > 128:
        raise Held('fixture output invalid; preserve original custody')
    result = json.loads(output)
    return runtime.call('collect', actor, credential, **request, launch_id=start['launch_id'], end=child.returncode,
                        result=result, evidence='actual bundled Popen.communicate numeric END')


def watch(runtime, actor, credential, timeout):
    """One Linux abstract receiver per actor, bound before durable scan.

    Kernel lifetime follows the original socket, including crash; no stale file
    deletion or guessed process custody is involved. Hints never carry work.
    """
    if not 0 <= timeout <= 60:
        raise Held('watch timeout must be within 0..60 seconds')
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.bind(runtime.wake_address(actor))
        while True:
            # Only short refused metadata acquisitions retry, never an effect.
            try:
                current = runtime.call('inbox', actor, credential)
            except Held as exc:
                if str(exc) != 'metadata busy; retry same operation, no launch' or time.monotonic() >= deadline:
                    raise
                time.sleep(.005)
                continue
            remaining = max(0, deadline - time.monotonic())
            if current['packets'] or not remaining:
                return current
            if not select.select([sock], [], [], remaining)[0]:
                return runtime.call('inbox', actor, credential)
            sock.recv(64)


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
    sub.add_parser('run-provider')
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
                elif args.command == 'run-provider':
                    from provider import run_provider
                    result = run_provider(runtime, args.actor, credential, request)
                else:
                    result = runtime.call(args.operation, args.actor, credential, **request)
        print(json.dumps({'status': 'ok', 'result': result}, sort_keys=True))
        return 0
    except (Held, _pool.PoolError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'held', 'reason': str(exc)[:512], 'replay': 'not authorized'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
