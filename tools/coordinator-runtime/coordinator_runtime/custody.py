"""Exact declared artifact custody. Canonical files are witnessed, never retired."""

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

from .contracts import PROFILES, Refusal, digest, encode, artifact_leaves
from .cleanup import register_artifact

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifact_blobs(sha256 TEXT PRIMARY KEY,body BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS artifact_custody(
 attempt TEXT NOT NULL,path TEXT NOT NULL,kind TEXT NOT NULL,owner TEXT NOT NULL,
 witness TEXT NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(attempt,path));
"""


def safe_path(path, roots):
    p = Path(path)
    if (not p.is_absolute() or '..' in p.parts or not any(p.is_relative_to(Path(r)) for r in roots)
            or any(p.is_relative_to(Path.home()/name) for name in PROFILES)):
        raise Refusal('artifact path is outside exact selected source/effect roots')
    if any(x.is_symlink() for x in (p, *p.parents)):
        raise Refusal('artifact symlink/ancestor refused')
    return p


def read_file(path, maximum):
    refuse_log(path)
    parent = os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            next_fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            os.close(parent);parent=next_fd
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW,dir_fd=parent)
    except BaseException:
        os.close(parent);raise
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise Refusal('bounded single-link regular artifact required')
        data = bytearray()
        while True:
            block = os.read(fd, min(65536, maximum+1-len(data)))
            if not block:
                break
            data.extend(block)
            if len(data) > maximum:
                raise Refusal('artifact grew beyond custody budget')
        after = os.fstat(fd)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns,x.st_mode,x.st_uid,x.st_gid,x.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(os.stat(path.name,dir_fd=parent,follow_symlinks=False)):
            raise Refusal('artifact changed while capturing exact source')
        return bytes(data), {'dev': after.st_dev, 'ino': after.st_ino, 'size': after.st_size,
                             'mtime': after.st_mtime_ns, 'mode':stat.S_IMODE(after.st_mode),
                             'uid':after.st_uid,'gid':after.st_gid,'ctime':after.st_ctime_ns,
                             'sha256': hashlib.sha256(data).hexdigest()}
    finally:
        os.close(fd)
        os.close(parent)


def refuse_log(path, task=None):
    log = (task or {}).get('routine_completion', {}).get('bounded_log', {}).get('target')
    if Path(path).name == 'WORK_LOG.md' or log and str(path) == log:
        raise Refusal('whole-log acquisition unavailable; bounded entry/operation receipt only')


def origin_path(path):
    # Pure lexical checks only: never stat, resolve or search retained origins.
    if (not isinstance(path, str) or not path or '\x00' in path
            or not Path(path).is_absolute() or '..' in Path(path).parts):
        raise Refusal('invalid retained original path')
    return path


def blob_id(sha256):
    if not isinstance(sha256, str) or re.fullmatch('[0-9a-f]{64}', sha256) is None:
        raise Refusal('invalid retained blob identifier')
    return sha256


def metadata_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('duplicate metadata key')
            result[key] = item
        return result
    def constant(value):
        raise ValueError('non-JSON metadata constant: ' + value)
    try:
        result = json.loads(value, object_pairs_hook=pairs,
                            parse_constant=constant)
    except (ValueError, TypeError, RecursionError) as exc:
        raise Refusal('invalid retained custody metadata') from exc
    if not isinstance(result, dict):
        raise Refusal('retained custody metadata must be an object')
    return result


def custody_witness(row):
    witness = metadata_json(row['witness'])
    if (witness.get('sha256') != blob_id(row['sha256'])
            or type(witness.get('size')) is not int or witness['size'] < 0):
        raise Refusal('retained custody witness needs its exact hash and byte size')
    return witness


def _stage_origin(store, stage):
    target = origin_path(stage['target'])
    refuse_excluded(store, target)
    policy = metadata_json(stage['policy']) if stage['policy'] is not None else {}
    from .bounded_log import KIND, validate_policy
    if policy.get('kind') != KIND:
        return target
    try:
        validate_policy(policy)
    except (KeyError, TypeError, ValueError) as exc:
        raise Refusal('invalid retained bounded-entry policy') from exc
    # A lawful bounded entry is distinct from the whole target's body. Its
    # target's exclusion still applies; do not acquire/follow the whole log.
    return None if policy['bounded_log']['target'] == target else target


def _path_origins(store, path, tasks):
    refuse_excluded(store, path)
    for current in tasks:
        refuse_log(path, current)
    known = store.one('SELECT sha256 FROM artifacts WHERE path=?', (path,))
    hashes = [known['sha256']] if known else []
    hashes.extend(row['sha256'] for row in store.rows('SELECT sha256 FROM artifact_custody WHERE path=?', (path,)))
    stages = store.rows('SELECT s.target,r.policy FROM routine_stages s LEFT JOIN routine_runs r ON r.attempt=s.attempt WHERE s.path=?', (path,))
    targets = [_stage_origin(store, stage) for stage in stages]
    return hashes, [target for target in targets if target is not None]


def _hash_origins(store, sha256, sizes):
    paths = []
    for row in store.rows('SELECT * FROM artifact_custody WHERE sha256=?', (sha256,)):
        size = custody_witness(row)['size']
        if sha256 in sizes and sizes[sha256] != size:
            raise Refusal('conflicting retained custody byte sizes')
        sizes[sha256] = size
        paths.append(row['path'])
    # Older snapshots conserved blobs without artifact_custody. Consult their
    # existing preimage keys, never bodies or filesystem aliases.
    paths.extend(row['path'] for row in store.rows("SELECT j.key AS path FROM routine_runs r,json_each(r.before_files) j WHERE json_extract(j.value,'$.sha256')=?", (sha256,)))
    return paths


def _guard_sources(store, hashes, paths, task):
    """Follow recorded relationships before bodies, without filesystem searches.

    Distinct visited sets retain transitive stage restrictions and terminate
    cycles. Every current task's log policy governs every acquisition path.
    """
    tasks = [None, *store.config.get('tasks', {}).values()]
    if task is not None:
        tasks.append(task)
    seen_paths, seen_hashes, sizes = set(), set(), {}
    while paths or hashes:
        if paths:
            path = origin_path(paths.pop())
            if path in seen_paths:
                continue
            seen_paths.add(path)
            linked_hashes, targets = _path_origins(store, path, tasks)
            hashes.extend(linked_hashes)
            paths.extend(targets)
            continue
        sha256 = blob_id(hashes.pop())
        if sha256 in seen_hashes:
            continue
        seen_hashes.add(sha256)
        paths.extend(_hash_origins(store, sha256, sizes))
    return sizes


def guard_frozen(store, sha256, task=None, path=None):
    """Validate known custody and current policy BEFORE any retained body read."""
    try:
        return _guard_sources(store, [sha256], [path] if path is not None else [], task)
    except sqlite3.DatabaseError as exc:
        raise Refusal('retained origin metadata unavailable or corrupt') from exc


def refuse_excluded(store, path):
    if any(Path(path) == Path(p) or Path(path).is_relative_to(Path(p))
           for p in store.config.get('artifact_exclusions', [])):
        raise Refusal('opaque source excluded before acquisition')


def guard_path(store, path, task=None):
    try:
        _guard_sources(store, [], [str(path)], task)
    except sqlite3.DatabaseError as exc:
        raise Refusal('retained origin metadata unavailable or corrupt') from exc


def frozen_body(store, sha256, task=None, path=None):
    sizes = guard_frozen(store, sha256, task, path)
    length = store.one('SELECT length(body) AS size FROM artifact_blobs WHERE sha256=?', (sha256,))
    if not length:
        return None
    if length['size'] > store.config['limits'].get('max_artifact_bytes', 33554432):
        raise Refusal('source exceeds selected export bound; retained without truncation')
    if sha256 in sizes and sizes[sha256] != length['size']:
        raise Refusal('retained body size differs from its exact custody witness')
    return store.one('SELECT body FROM artifact_blobs WHERE sha256=?', (sha256,))


def capture(store, attempt, path, task, role_owned=False):
    guard_path(store, path, task)
    root = store.home/'artifacts'/attempt
    authority = task['effect_authority']
    candidate = Path(path)
    if any(candidate==Path(p) or candidate.is_relative_to(Path(p)) for p in store.config.get('artifact_exclusions',[])):
        raise Refusal('opaque artifact excluded before metadata or source acquisition')
    if candidate.is_relative_to(store.home) and not candidate.is_relative_to(store.home/'artifacts'):
        raise Refusal('journal/session/auxiliary stores are not task report artifacts')
    p = safe_path(path, [str(root), *authority['read_roots'], *authority['write_roots']])
    maximum = min(store.config['limits'].get('max_artifact_bytes', 33554432), store.config['limits']['max_bytes'])
    data, witness = read_file(p, maximum)
    prior = store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?', (attempt, str(p)))
    if prior:
        if prior['sha256'] != witness['sha256']:
            raise Refusal('previously frozen artifact changed; old source remains conserved')
        return prior
    canonical = str(p) in task.get('routine_completion',{}).get('targets',[])
    creator = store.one('SELECT attempt FROM artifacts WHERE path=?',(str(p),))
    if canonical:
        kind='role-owned'
    elif p.is_relative_to(root) and not role_owned:
        kind='runtime-owned'
    else:
        kind='linked-owned' if creator else 'role-owned'
    owner = store.config['roles'][task['role']]['owner']
    with store.tx():
        present=store.one('SELECT sha256 FROM artifact_blobs WHERE sha256=?',(witness['sha256'],))
        store.budget(None, (0 if present else len(data))+1024)
        store.db.execute('INSERT OR IGNORE INTO artifact_blobs VALUES(?,?)', (witness['sha256'], data))
        store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                         (attempt, str(p), kind, owner, encode(witness), witness['sha256']))
    if kind == 'runtime-owned':
        if not store.one('SELECT path FROM artifacts WHERE path=?', (str(p),)):
            register_artifact(store, attempt, p)
        with store.tx():
            store.db.execute('UPDATE artifacts SET conserved=? WHERE path=?',
                             (encode({'actor': store.config['actor'], 'owner': owner,
                                      'basis': 'exact durable artifact_blobs custody', **witness}), str(p)))
    return store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?', (attempt, str(p)))


def inventory(store, attempt, answer, task, role_owned=False):
    leaves=artifact_leaves(answer.get('artifacts'))
    seen,errors = set(),[]
    for item in leaves:
        path=item['path']
        try:
            if path not in seen:
                capture(store, attempt, path, task,role_owned)
                seen.add(path)
            witness=json.loads(store.one('SELECT witness FROM artifact_custody WHERE attempt=? AND path=?',(attempt,path))['witness'])
            if ('sha256' in item and item['sha256']!=witness['sha256'] or
                    'bytes' in item and (type(item['bytes']) is not int or item['bytes']!=witness['size'])):
                raise Refusal('declared artifact hash/bytes differ from captured source; original claim retained')
        except (Refusal,OSError) as exc:errors.append(type(exc).__name__+': '+str(exc)[:500])
    if errors:raise Refusal('artifact inventory incomplete: '+encode(errors))


def witnesses(store, attempt):
    return [{'path': r['path'], 'kind': r['kind'], 'owner': r['owner'], **json.loads(r['witness']),
             'custody': 'artifact_blobs', 'source_context': r['attempt'],
             'source_attempt': None if r['attempt'].startswith('owner:') else r['attempt']}
            for r in store.rows('SELECT * FROM artifact_custody WHERE attempt=?', (attempt,))]


def materialize(store, events, attempt, task=None):
    """Give the worker only its declared frozen input bytes, not journal access."""
    result = []
    for event in events:
        for w in event.get('artifact_witnesses', []):
            if w.get('custody') != 'artifact_blobs':
                continue
            # Refuse even if an input copy already exists or custody is inherited.
            # The witness origin must be present; opaque hashes are no authority.
            if not w.get('path'):
                raise Refusal('frozen artifact needs its retained original path')
            row = frozen_body(store, w['sha256'], task, w['path'])
            if not row or hashlib.sha256(row['body']).hexdigest() != w['sha256']:
                raise Refusal('required frozen artifact custody is unavailable')
            root = store.home/'artifacts'/attempt/'inputs'
            root.mkdir(mode=0o700, exist_ok=True)
            path = root/w['sha256']
            if not path.exists():
                store.budget(None,len(row['body']))
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as output:
                    output.write(row['body']); output.flush(); os.fsync(output.fileno())
                register_artifact(store, attempt, path)
                with store.tx():
                    store.db.execute('UPDATE artifacts SET conserved=? WHERE path=?',
                                     (encode({'basis': 'existing exact artifact_blobs', 'sha256': w['sha256']}), str(path)))
            result.append({**w, 'frozen_path': str(path)})
    return result
