"""Finite isolated ALL-tracked export qualification; never a service operation."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import subprocess
import tarfile
import time
from common import encode, exclusive, load_json, record, require
from prepare import namespace, prepare


def headroom(parent, size=16 * 1024**2, entries=256):
    free = os.statvfs(parent)
    require(free.f_bavail * free.f_frsize >= 100 * 1024**3 + size
            and free.f_favail >= 1000000 + entries, 'leave100GiB/1M including next phase')


def collected(area, label, argv, maximum=65536, git=False):
    """Drain bounded streams to numeric wait. Truncation is retained, never success."""
    headroom(area, maximum + 16384, 4)
    paths = {name: area / (label + '.' + name) for name in ('stdout', 'stderr')}
    streams = {name: open(path, 'xb', buffering=0) for name, path in paths.items()}
    hashes = {name: hashlib.sha256() for name in streams}
    counts = dict.fromkeys(streams, 0)
    kept = dict.fromkeys(streams, 0)
    start = time.monotonic()
    result = {'argv': argv, 'collector_cwd': str(Path.cwd()), 'exit': None, 'timed_out': False, 'complete': False,
              'stderr_suppressed': git, 'outside_owned_debt': None}
    process = None
    selector = selectors.DefaultSelector()
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL if git else subprocess.PIPE,
                                   start_new_session=True,
                                   env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1',
                                        'GIT_OPTIONAL_LOCKS': '0'})
        for name in streams:
            pipe = getattr(process, name)
            if pipe is not None:
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
        stage = 0
        deadline = start + 60
        while selector.get_map():
            now = time.monotonic()
            if now >= deadline:
                result['timed_out'] = True
                if stage == 2:
                    break
                try:
                    os.killpg(process.pid, signal.SIGTERM if stage == 0 else signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stage += 1
                deadline = now + 2
            for key, _ in selector.select(min(0.25, max(0, deadline - now))):
                body = os.read(key.fd, 8192)
                if not body:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                name = key.data
                counts[name] += len(body)
                hashes[name].update(body)
                prefix = body[:max(0, maximum - sum(kept.values()))]
                streams[name].write(prefix)
                kept[name] += len(prefix)
        pipe_complete = not selector.get_map()
        try:
            result['exit'] = process.wait(timeout=max(0.1, start + 65 - time.monotonic()))
        except subprocess.TimeoutExpired:
            result['timed_out'] = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                result['exit'] = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                result['outside_owned_debt'] = 'No numeric END; outside Work must retain original custody. Never replay.'
        result['complete'] = pipe_complete and result['exit'] is not None and counts == kept
    except Exception as exc:
        result['collection_error'] = type(exc).__name__
        if process is not None and process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                result['exit'] = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                result['outside_owned_debt'] = 'Collection exception; actual original END remains outside Work debt.'
    finally:
        for key in list(selector.get_map().values()):
            key.fileobj.close()
        selector.close()
        for stream in streams.values():
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
    result['seconds'] = time.monotonic() - start
    for name in streams:
        result[name] = {**record(paths[name], maximum), 'observed_bytes': counts[name],
                        'observed_sha256': hashes[name].hexdigest(), 'truncated': counts[name] != kept[name]}
    exclusive(area / (label + '.collection.json'), encode(result))
    return result, paths['stdout']


def require_collection(result):
    require(result['exit'] is not None and result['complete'] and not result['timed_out'],
            'incomplete collection; retain failure and any outside-owned debt')


def export_all(candidate, head, root):
    """Normal immutable Git only. Every tracked member is validated before export."""
    headroom(root, 96 * 1024**2, 5000)
    header, header_path = collected(root, 'git-header', ['git', '-C', str(candidate), 'cat-file', 'commit', head], git=True)
    require_collection(header)
    require(header['exit'] == 0, 'immutable source header failed')
    lines = header_path.read_text().split('\n\n', 1)[0].splitlines()
    tree = next(line[5:] for line in lines if line.startswith('tree '))
    parents = [line[7:] for line in lines if line.startswith('parent ')]
    listing, path = collected(root, 'git-listing', ['git', '-C', str(candidate), 'ls-tree', '-r', '-l', '-z', head],
                              maximum=2 * 1024**2, git=True)
    require_collection(listing)
    require(listing['exit'] == 0, 'immutable listing failed')
    files = []
    for entry in path.read_bytes().split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.decode().split('\t', 1)
        mode, kind, blob, size = metadata.split()
        relative = PurePosixPath(name)
        require(kind == 'blob' and mode in {'100644', '100755'} and not relative.is_absolute()
                and all(part not in {'.', '..', '.git'} for part in relative.parts)
                and str(relative) == name, 'ordinary tracked public files only')
        require(int(size) <= 4 * 1024**2, 'bounded file')
        files.append({'path': name, 'mode': mode, 'blob': blob, 'bytes': int(size)})
    require(0 < len(files) <= 5000 and sum(item['bytes'] for item in files) <= 32 * 1024**2,
            'finite ALL-tracked export budget')
    archive, archive_path = collected(root, 'git-archive', ['git', '-C', str(candidate), 'archive', '--format=tar', head],
                                      maximum=40 * 1024**2, git=True)
    require_collection(archive)
    require(archive['exit'] == 0, 'immutable archive failed')
    export = root / 'qa-source'
    export.mkdir(mode=0o700)
    expected = {item['path']: item for item in files}
    seen = set()
    with tarfile.open(archive_path, 'r:') as tar:
        for member in tar:
            if member.isdir():
                continue
            require(member.isfile() and member.name in expected and member.name not in seen,
                    'archive member outside positive immutable listing')
            item = expected[member.name]
            require(member.size == item['bytes'], 'archive size differs')
            body = tar.extractfile(member).read()
            algorithm = hashlib.sha1 if len(item['blob']) == 40 else hashlib.sha256
            require(algorithm(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() == item['blob'],
                    'archive content differs from immutable blob')
            target = export / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            exclusive(target, body)
            target.chmod(0o755 if item['mode'] == '100755' else 0o644)
            item['sha256'] = hashlib.sha256(body).hexdigest()
            seen.add(member.name)
    require(seen == set(expected), 'ALL-tracked coverage incomplete')
    association = {'head': head, 'tree': tree, 'parents': parents, 'root': str(export), 'files': files, 'count': len(files),
                   'bytes': sum(item['bytes'] for item in files),
                   'meaning': 'isolated immutable ALL export; not service-owned association or admission'}
    exclusive(root / 'EXPORT.json', encode(association))
    return export, association


def qualify(candidate, head, root):
    candidate = Path(candidate)
    root = Path(root)
    require(not root.exists(), 'fresh qualification root required')
    headroom(root.parent, 128 * 1024**2, 6500)
    root.mkdir(mode=0o700)
    export, association = export_all(candidate, head, root)
    results = []
    variants = ('positive', 'candidate-tamper', 'script-tamper', 'manifest-tamper', 'wrong-cwd',
                'missing-observation', 'incomplete', 'wrong-run', 'dropped-case', 'extra-case',
                'wrong-outcome', 'type-confusion', 'foreign-cwd-export')
    for variant in variants:
        headroom(root)
        area = root / variant
        m, commands = prepare(candidate, area)
        require('export' not in m, 'prepared alias must not stand in for service export')
        if variant == 'script-tamper':
            p = area / 'instance/behavior.py'
            p.write_bytes(p.read_bytes() + b'\n# owned negative\n')
        if variant == 'manifest-tamper':
            p = area / 'instance/MANIFEST.json'
            d = load_json(p); d['run_id'] = 'wrong'; p.write_bytes(encode(d))
        command_argv = namespace(m, commands, 'command', export)
        if variant == 'candidate-tamper':
            target = 'tools/coordinator-runtime/coordinator_runtime/contracts.py'
            altered = area / 'altered-contracts.py'
            exclusive(altered, (export / target).read_bytes() + b'\n# owned negative identity mutation\n')
            i = command_argv.index('--chdir')
            command_argv[i:i] = ['--ro-bind', str(altered), str(candidate / target)]
        if variant == 'foreign-cwd-export':
            foreign = area / 'foreign'; foreign.mkdir()
            i = command_argv.index('--chdir')
            command_argv[i:i] = ['--ro-bind', str(foreign), str(candidate)]
        if variant == 'wrong-cwd':
            command_argv[command_argv.index('--chdir') + 1] = str(export)
        if variant != 'missing-observation':
            command, path = collected(area, 'command', command_argv)
            require_collection(command)
            expected_exit = 1 if variant in {'candidate-tamper', 'script-tamper', 'manifest-tamper',
                                            'wrong-cwd', 'foreign-cwd-export'} else 0
            require(command['exit'] == expected_exit, 'unexpected original command result: ' + variant)
            require(path.read_bytes() == (commands['command']['stdout'].encode() if expected_exit == 0 else b''),
                    'unexpected command stdout')
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
        readback, path = collected(area, 'readback', namespace(m, commands, 'readback', export))
        require_collection(readback)
        require(readback['exit'] == (0 if variant == 'positive' else 1), 'unexpected readback: ' + variant)
        if variant == 'positive':
            require(path.read_bytes() == commands['readback']['stdout'].encode(), 'readback stdout')
            receipt = load_json(Path(m['output']) / 'READBACK.json')
            require(len(receipt['cases']) == 31 and receipt['accepted'] is False, 'positive readback incomplete')
            replay, _ = collected(area, 'replayed-readback', namespace(m, commands, 'readback', export))
            require_collection(replay)
            require(replay['exit'] == 1, 'readback replay not refused')
        else:
            require(path.read_bytes() == b'', 'failed readback emitted success stdout')
            require(not (Path(m['output']) / 'READBACK.json').exists(), 'negative produced receipt')
        results.append({'variant': variant, 'command': command, 'readback': readback,
                        'manifest_sha256': commands['manifest_sha256'], 'passed': True})
        exclusive(root / ('PROGRESS-' + variant + '.json'), encode(results[-1]))
    result = {'qualification': 'ordinary1152-contract-package', 'complete': True, 'variants': results,
              'export': association, 'accepted': False, 'processing_complete': False,
              'meaning': '13 distinct isolated variants at ALL-tracked final export; service association/QA acceptance owed'}
    exclusive(root / 'RESULT.json', encode(result))
    print(json.dumps({'complete': True, 'variants': len(results), 'case_count_positive': 31,
                      'export_files': association['count'], 'actual_acceptance': False}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', required=True); p.add_argument('--source-head', required=True)
    p.add_argument('--new-root', required=True)
    args = p.parse_args(); qualify(args.candidate, args.source_head, args.new_root)
