"""One owned offline qualification with source binding and real pipe EOF.

No provider executable or private backing is mounted. Complete captures and all
failed fixtures remain with the invoking owner. Source files must be frozen and
published before the final encounter; this driver never writes source.
"""
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).parent/'tests'))
from fixture_conservation import capacity, directory, write


def source_check(source, frozen):
    for relative, expected in frozen['files'].items():
        path = source / relative
        if not path.is_relative_to(source/'tools') or '..' in path.parts or path.is_symlink():
            raise ValueError('exact frozen public source only')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('frozen source changed: '+relative)


def capture(worker, output):
    selector = selectors.DefaultSelector()
    selector.register(worker.stdout, selectors.EVENT_READ, 'stdout')
    selector.register(worker.stderr, selectors.EVENT_READ, 'stderr')
    counts, eof, errors = {'stdout':0,'stderr':0}, {'stdout':False,'stderr':False}, []
    streams = {}
    limit, until, stopped = 32*1024**2, time.monotonic()+900, False
    for name in counts:
        capacity(output)
        streams[name] = (output/(name+'.txt')).open('xb')
    try:
        while selector.get_map():
            if time.monotonic() >= until:
                errors.append('qualification pipe deadline; incomplete capture')
                if stopped:
                    break
                worker.kill()
                stopped, until = True, time.monotonic()+10
            for key, _ in selector.select(1):
                part = os.read(key.fileobj.fileno(), 16384)
                name = key.data
                if not part:
                    eof[name] = True
                    selector.unregister(key.fileobj)
                    continue
                kept = part[:max(0, limit-counts[name])]
                counts[name] += len(part)
                capacity(output)
                streams[name].write(kept)
                if counts[name] > limit and not stopped:
                    errors.append(name+' exceeded complete capture allowance; prefix retained')
                    worker.kill()
                    stopped, until = True, time.monotonic()+10
        code = worker.wait()
    finally:
        selector.close()
        worker.stdout.close()
        worker.stderr.close()
        for stream in streams.values():
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
    return dict(actual_END=code, pipe_EOF=eof, capture_errors=errors,
                capture_complete=all(eof.values()) and not errors, stream_bytes=counts,
                meaning='same owned worker wait and pipe EOF, not whole processing or acceptance')


def main():
    output, selection, freeze = map(Path, sys.argv[1:])
    phase = capacity(output.parent)
    source = Path(__file__).resolve().parents[2]
    frozen = json.loads(freeze.read_text())
    source_check(source, frozen)
    directory(output)
    fixtures, record = output/'fixtures', output/'record'
    directory(fixtures)
    directory(record)
    argv = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
        '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin',
        '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
        '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--tmpfs', '/home',
        '--dir', '/empty-home', '--dir', '/etc',
        '--ro-bind', str(source/'tools'), '/src/tools',
        '--bind', str(fixtures), '/fixtures', '--bind', str(record), '/record',
        '--ro-bind', str(selection), '/selection.json',
        '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
        '--setenv', 'PYTHONPATH', '/src/tools/coordinator-runtime',
        '--setenv', 'RFQ673_FIXTURES', '/fixtures', '--setenv', 'HOME', '/empty-home',
        '--chdir', '/src/tools/coordinator-runtime', '/usr/bin/python3', '-B',
        '/src/tools/coordinator-runtime/focused_qualification1226.py']
    registration = dict(argv=argv, selection=json.loads(selection.read_text()), source=frozen,
        phase_capacity=phase, state='registered-before-launch',
        original='one foreground Popen object; no PID, polling, recovery or replacement')
    write(output/'registration.json', json.dumps(registration, indent=2).encode())
    worker = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    receipt = capture(worker, output)
    source_check(source, frozen)
    receipt['frozen_source_unchanged'] = True
    write(output/'collection.json', json.dumps(receipt, indent=2).encode())
    print(json.dumps(receipt), flush=True)
    return 0 if receipt['actual_END']==0 and receipt['capture_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

