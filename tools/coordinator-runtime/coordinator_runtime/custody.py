"""Exact declared artifact custody. Canonical files are witnessed, never retired."""

import hashlib
import json
import os
from pathlib import Path
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


def capture(store, attempt, path, task, role_owned=False):
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


def materialize(store, events, attempt):
    """Give the worker only its declared frozen input bytes, not journal access."""
    result = []
    for event in events:
        for w in event.get('artifact_witnesses', []):
            if w.get('custody') != 'artifact_blobs':
                continue
            row = store.one('SELECT body FROM artifact_blobs WHERE sha256=?', (w['sha256'],))
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
