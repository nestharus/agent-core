"""Owned, finite preparation qualification. No service/admission/acceptance."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import time
from common import encode, exclusive, load_json, record, require
from prepare import namespace, prepare


def collected(area, label, argv):
    start = time.monotonic()
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'})
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    require(len(stdout) + len(stderr) <= 65536, 'qualification capture overflow; preserve original')
    exclusive(area / (label + '.stdout'), stdout)
    exclusive(area / (label + '.stderr'), stderr)
    result = {'argv': argv, 'exit': process.returncode, 'timed_out': timed_out,
              'seconds': time.monotonic() - start, 'stdout': record(area / (label + '.stdout')),
              'stderr': record(area / (label + '.stderr')), 'complete': True}
    exclusive(area / (label + '.collection.json'), encode(result))
    return result, stdout


def qualify(candidate, root):
    root = Path(root)
    require(not root.exists(), 'fresh qualification root required')
    free = os.statvfs(root.parent)
    require(free.f_bavail * free.f_frsize > 100 * 1024**3 + 16 * 1024**2 and free.f_favail > 1000256, 'headroom')
    root.mkdir(mode=0o700)
    results = []
    variants = ('positive', 'candidate-tamper', 'script-tamper', 'manifest-tamper', 'wrong-cwd',
                'missing-observation', 'incomplete', 'wrong-run', 'dropped-case', 'extra-case', 'wrong-outcome', 'type-confusion')
    for variant in variants:
        area = root / variant
        m, commands = prepare(candidate, area)
        if variant == 'candidate-tamper':
            p = Path(m['export']) / 'tools/coordinator-runtime/coordinator_runtime/contracts.py'
            p.write_bytes(p.read_bytes() + b'\n# owned negative identity mutation\n')
        if variant == 'script-tamper':
            p = area / 'instance/behavior.py'; p.write_bytes(p.read_bytes() + b'\n# owned negative\n')
        if variant == 'manifest-tamper':
            p = area / 'instance/MANIFEST.json'; d = load_json(p); d['run_id'] = 'wrong'; p.write_bytes(encode(d))
        command_argv = namespace(m, commands, 'command')
        if variant == 'wrong-cwd':
            command_argv[command_argv.index('--chdir') + 1] = m['export']
        if variant != 'missing-observation':
            command, stdout = collected(area, 'command', command_argv)
            expected_exit = 1 if variant in {'candidate-tamper', 'script-tamper', 'manifest-tamper', 'wrong-cwd'} else 0
            require(command['exit'] == expected_exit and not command['timed_out'], 'unexpected original command result: ' + variant)
            if expected_exit == 0:
                require(stdout.decode() == commands['command']['stdout'], 'unexpected command stdout')
            else:
                require(stdout == b'', 'failed command emitted collection-success stdout')
        else:
            command = None
        if variant in {'incomplete', 'wrong-run', 'dropped-case', 'extra-case', 'wrong-outcome', 'type-confusion'}:
            path = Path(m['output']) / 'OBSERVATIONS.json'; d = load_json(path)
            if variant == 'incomplete': d['complete'] = False
            if variant == 'wrong-run': d['run_id'] = 'foreign-original'
            if variant == 'dropped-case': d['observations'].pop('sequence.exact')
            if variant == 'extra-case': d['observations']['invented'] = True
            if variant == 'wrong-outcome': d['observations']['sequence.qa-route'] = True
            if variant == 'type-confusion': d['observations']['sequence.exact'] = 1
            path.write_bytes(encode(d))
        readback, stdout = collected(area, 'readback', namespace(m, commands, 'readback'))
        require(readback['exit'] == (0 if variant == 'positive' else 1) and not readback['timed_out'],
                'unexpected original readback result: ' + variant)
        if variant == 'positive':
            require(stdout.decode() == commands['readback']['stdout'], 'unexpected readback stdout')
            receipt = load_json(Path(m['output']) / 'READBACK.json')
            require(len(receipt['cases']) == 31 and receipt['accepted'] is False, 'positive readback incomplete')
            replay, _ = collected(area, 'replayed-readback', namespace(m, commands, 'readback'))
            require(replay['exit'] == 1 and not replay['timed_out'], 'readback replay not refused')
        else:
            require(stdout == b'', 'failed readback emitted success stdout')
            require(not (Path(m['output']) / 'READBACK.json').exists(), 'negative produced success receipt')
        results.append({'variant': variant, 'command': command, 'readback': readback,
                        'manifest_sha256': commands['manifest_sha256'], 'passed': True})
        exclusive(root / 'PROGRESS-{}.json'.format(variant), encode(results[-1]))
    result = {'qualification': 'ordinary1141b-contract-package', 'complete': True, 'variants': results,
              'accepted': False, 'processing_complete': False,
              'meaning': 'twelve distinct original fixtures; no pooling of runs or service/QA acceptance'}
    exclusive(root / 'RESULT.json', encode(result))
    print(json.dumps({'complete': True, 'variants': len(results), 'case_count_positive': 31,
                      'readback_replay_refused': True, 'actual_acceptance': False}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', required=True); p.add_argument('--new-root', required=True)
    args = p.parse_args(); qualify(args.candidate, args.new_root)
