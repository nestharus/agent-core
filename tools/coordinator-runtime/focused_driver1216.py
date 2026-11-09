"""One registered foreground offline worker, exact selected IDs, separate captures.

Caller supplies one new encounter directory in its admitted bulk area. Source
and bootstrap tools are read-only. Host home/config/site/network are unavailable.
This driver is a producer, not provider or independent acceptance machinery.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent / 'tests'))
from fixture_conservation import capacity, directory, write


def main():
    output, selection = map(Path, sys.argv[1:])
    phase_capacity = capacity(output.parent)
    directory(output)
    fixtures, record = output / 'fixtures', output / 'record'
    directory(fixtures)
    directory(record)
    source = Path(__file__).resolve().parents[2]
    argv = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
            '--ro-bind', '/usr', '/usr', '--ro-bind', '/bin', '/bin',
            '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
            '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
            '--tmpfs', '/home', '--dir', '/empty-home', '--dir', '/etc',
            '--ro-bind', str(source / 'tools'), '/src/tools',
            '--bind', str(fixtures), '/fixtures', '--bind', str(record), '/record',
            '--ro-bind', str(selection), '/selection.json',
            '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--setenv', 'PYTHONPATH', '/src/tools/coordinator-runtime',
            '--setenv', 'RFQ673_FIXTURES', '/fixtures', '--setenv', 'HOME', '/empty-home',
            '--chdir', '/src/tools/coordinator-runtime',
            '/usr/bin/python3', '-B', '/src/tools/coordinator-runtime/focused_qualification1216.py']
    registration = dict(argv=argv, selection=json.loads(selection.read_text()), phase_capacity=phase_capacity,
                        original='single owned Popen object; actual wait/EOF below', state='registered-before-launch')
    write(output / 'registration.json', json.dumps(registration, indent=2).encode())
    # Preserve the actual complete stdout/stderr separately from semantic reports.
    capacity(output)
    with (output / 'stdout.txt').open('xb') as stdout, (output / 'stderr.txt').open('xb') as stderr:
        worker = subprocess.Popen(argv, stdout=stdout, stderr=stderr)
        code = worker.wait()
        stdout.flush()
        stderr.flush()
        os.fsync(stdout.fileno())
        os.fsync(stderr.fileno())
    receipt = dict(actual_END=code, stdout_EOF=True, stderr_EOF=True, capture_closed=True,
                   final_capacity=capacity(output),
                   stdout_bytes=(output / 'stdout.txt').stat().st_size,
                   stderr_bytes=(output / 'stderr.txt').stat().st_size,
                   original='same Popen object registered in registration.json',
                   meaning='worker completion only; outer receiving original remains with Work')
    write(output / 'collection.json', json.dumps(receipt, indent=2).encode())
    print(json.dumps(receipt), flush=True)
    return 0 if code == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
