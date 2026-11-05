"""Bounded candidate-byte execution for local QA. No checkout mutation/adoption.

An independently selected harness may live outside the candidate. Candidate
tracked files are exported from Git objects, not from the current checkout;
outputs/generated inputs use separately admitted paths. This is not proof that
an arbitrary admitted harness tests the intended behavior.
"""
import hashlib
from pathlib import Path, PurePosixPath

from .contracts import Refusal, digest


def validate(store, p):
    from .ordinary import frozen_file
    policy = p['source_capture']
    if (not isinstance(policy, dict) or set(policy) != {'bwrap', 'sha256', 'max_bytes', 'max_files'}
            or policy['bwrap'] != '/usr/bin/bwrap'
            or type(policy['max_bytes']) is not int or not 1 <= policy['max_bytes'] <= 128 * 1024 * 1024
            or type(policy['max_files']) is not int or not 1 <= policy['max_files'] <= 5000):
        raise Refusal('explicit bounded local QA candidate export and namespace tool required')
    frozen_file(store, policy['bwrap'], [policy['bwrap']], policy['sha256'])


def guard_candidate(store, repository, name):
    # Lexical known origin first: no candidate body, copy, hash or export-root
    # creation is permitted until EVERY listed path has passed this boundary.
    from .custody import guard_path
    path = Path(repository) / name
    guard_path(store, path)
    for task in store.config['tasks'].values():
        guard_path(store, path, task)


async def export(store, attempt, p, source):
    from .ordinary import git, tool
    policy = p['source_capture']
    listing = await git(store, attempt, p, 'ls-tree', '-r', '-l', '-z', p['source_head'])
    files, total = [], 0
    for entry in listing.split('\0'):
        if not entry:
            continue
        metadata, name = entry.split('\t', 1)
        mode, kind, blob, size = metadata.split()
        path = PurePosixPath(name)
        if (kind != 'blob' or mode not in {'100644', '100755'} or path.is_absolute()
                or any(part in {'.', '..', '.git'} for part in path.parts) or str(path) != name):
            raise Refusal('QA export supports ordinary tracked files only; no symlink/submodule/path substitution')
        guard_candidate(store, p['repository'], name)
        if int(size) > 4 * 1024 * 1024:
            raise Refusal('candidate file exceeds exact retained-file verification budget')
        total += int(size)
        files.append({'path': name, 'mode': mode, 'blob': blob, 'size': int(size)})
        if total > policy['max_bytes'] or len(files) > policy['max_files']:
            raise Refusal('candidate export exceeds admitted source budget')
    if not files:
        raise Refusal('candidate has no tracked executable source inputs')
    root = store.home / 'artifacts' / attempt / 'qa-source'
    # Service-owned, retained, unique to this exact execution intent.
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    store.budget(None, total + len(files) * 1024)
    for item in files:
        guard_candidate(store, p['repository'], item['path'])
        target = root / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        argv = [p['git'], '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                '-c', 'core.hooksPath=/dev/null', '-C', p['repository'], 'cat-file', 'blob', item['blob']]
        record = await tool(store, attempt, 'qa-source-blob', argv, p['repository'], p,
                            output_file=target, maximum=policy['max_bytes'])
        if record['exit'] != 0 or record['stdout_bytes'] != item['size']:
            raise Refusal('candidate object export incomplete; retain original intent')
        body = target.read_bytes()
        algorithm = hashlib.sha1 if len(item['blob']) == 40 else hashlib.sha256
        if algorithm(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() != item['blob']:
            raise Refusal('exported bytes do not match the actual Git blob')
        item['sha256'] = record['stdout_sha256']
        target.chmod(0o755 if item['mode'] == '100755' else 0o644)
    return {'head': source['head'], 'tree': source['tree'], 'root': str(root), 'files': files,
            'manifest': digest(files), 'method': 'git-blobs-readonly-namespace-v1'}


def command(store, task, p, association, selected_command):
    from .ordinary import scoped_path, frozen_file
    argv = selected_command["argv"]
    root = association['root']
    executable = Path(argv[0])
    if executable.is_relative_to(Path(p['repository'])):
        exported_executable = Path(root) / executable.relative_to(Path(p['repository']))
        frozen_file(store, str(exported_executable), [root], selected_command['executable_sha256'])
    args = [p['source_capture']['bwrap'], '--unshare-net', '--die-with-parent', '--new-session',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
            '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
            '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--clearenv',
            '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1']
    authority = task['effect_authority']
    mounts = {path: False for path in authority['read_roots']}
    mounts.update({path: True for path in authority['write_roots']})
    for path, writable in sorted(mounts.items(), key=lambda item: len(Path(item[0]).parts)):
        scoped_path(store, path, authority['read_roots'] + authority['write_roots'])
        if writable and Path(root).is_relative_to(Path(path)):
            raise Refusal('QA output authority may not rename or mutate the retained candidate export')
        args += ['--bind' if writable else '--ro-bind', path, path]
    # Both names of the candidate are read-only, after any ancestor mounts.
    args += ['--ro-bind', root, root, '--ro-bind', root, p['repository'],
             '--chdir', p['repository'], '--', *argv]
    return args


def verify(store, attempt, p, receipt):
    from .ordinary import frozen_file
    association = receipt.get('outcome', {}).get('source_execution', {})
    expected = store.home / 'artifacts' / attempt / 'qa-source'
    if (association.get('method') != 'git-blobs-readonly-namespace-v1'
            or association.get('head') != p['source_head'] or association.get('tree') != receipt.get('before', {}).get('tree')
            or association.get('head') != receipt.get('before', {}).get('head') or association.get('root') != str(expected)
            or not association.get('files') or association.get('manifest') != digest(association['files'])):
        raise Refusal('actual candidate-byte execution association missing; ref labels alone cannot qualify QA')
    for item in association['files']:
        path = PurePosixPath(item['path'])
        if path.is_absolute() or '..' in path.parts:
            raise Refusal('candidate evidence path escaped retained export')
        frozen_file(store, str(expected / path), [str(expected)], item['sha256'])
    # Bind the association to this original actually collected runner record.
    records = [r for r in receipt['tools'] if r['label'] == 'qa-runner' and r.get('complete')]
    if len(records) != 1 or digest(records[0]) != association.get('runner_record'):
        raise Refusal('candidate evidence differs from the actual original runner collection')
    return association
