"""One argument-free unittest invocation with retained complete output or failure."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

from common import load_instance, require, sha, verify_inputs, write_json


def sandbox(m):
    d, c, out = m['instance'], m['candidate'], m['output']
    argv = [m['bwrap'], '--die-with-parent', '--unshare-all', '--new-session', '--tmpfs', '/']
    for p in ('/usr', '/lib', '/lib64', '/bin'):
        argv += ['--ro-bind', p, p]
    argv += ['--proc', '/proc', '--dev', '/dev', '--ro-bind', c, c,
             '--ro-bind', c, '/src', '--ro-bind', c, '/actualsrc',
             '--ro-bind', d, d, '--ro-bind', d, '/procedure', '--ro-bind', d+'/sdk', '/sdk',
             '--ro-bind', d+'/public', '/public', '--bind', out, '/fixtures',
             '--dir', '/tmp', '--dir', '/home', '--clearenv']
    env = dict(PATH='/usr/bin:/bin', HOME='/fixtures', TMPDIR='/fixtures/tmp',
               PYTHONDONTWRITEBYTECODE='1', QA629_FIXTURES='/fixtures/cases',
               COORDINATOR_ORDINARY_FIXTURES='/fixtures/ordinary-effects33',
               COORDINATOR_TEST_BOARD_LIBRARY='/sdk',
               PYTHONPATH='/procedure:/sdk:'+c+'/tools/coordinator-runtime:'+c+'/tools/coordinator-runtime/tests')
    for k, v in env.items():
        argv += ['--setenv', k, v]
    return argv+['--chdir', c, m['python'], '-B', '/procedure/worker.py']


def main(directory, expected):
    m = load_instance(directory, expected)
    verify_inputs(m)
    out = Path(m['output'])
    require(not out.exists(), 'fresh output required; no replay')
    os.mkdir(out, 0o700)
    write_json(out/'OWNER.json', {'instance': m['instance'], 'run_id': m['run_id']})
    for name in ('tmp', 'cases'):
        (out/name).mkdir()
    started = time.monotonic()
    argv = sandbox(m)
    record = {'manifest_sha256': expected, 'run_id': m['run_id'], 'argv': argv,
              'exit': None, 'complete': False, 'reason': None}
    # Drain the owned child through END, retaining all bytes up to the declared
    # limit. Overflow/timeout kills and waits this child and is always failure.
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    count = 0
    with (out/'transcript.txt').open('xb') as stream, selectors.DefaultSelector() as ready:
        ready.register(proc.stdout, selectors.EVENT_READ)
        eof = False
        while not eof:
            if time.monotonic()-started > m['limits']['timeout'] and record['reason'] is None:
                record['reason'] = 'timeout'
                proc.kill()
            for key, _ in ready.select(.1):
                body = os.read(key.fd, 65536)
                if not body:
                    eof = True
                    break
                count += len(body)
                if count > m['limits']['output_bytes']:
                    if record['reason'] is None:
                        record['reason'] = 'output overflow; retained prefix is incomplete'
                        proc.kill()
                else:
                    stream.write(body)
        record['exit'] = proc.wait()
    record.update(seconds=time.monotonic()-started, observed_output_bytes=count,
                  retained_output_bytes=(out/'transcript.txt').stat().st_size,
                  transcript_sha256=sha((out/'transcript.txt').read_bytes()))
    record['complete'] = record['reason'] is None and count == record['retained_output_bytes']
    verify_inputs(m)
    write_json(out/'execution.json', record)
    print(json.dumps({'exit': record['exit'], 'complete': record['complete'], 'output': str(out)}))
    raise SystemExit(0 if record['exit'] == 0 and record['complete'] else 1)
