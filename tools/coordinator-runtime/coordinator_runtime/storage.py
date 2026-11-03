"""Exact per-attempt auxiliary storage, separate from shared account credentials.

No profile/history inventory. Physical retirement proves only these owned paths;
ephemeral/read/unsubscribe and global shared-profile absence remain distinct.
"""
import json
import asyncio
from contextlib import suppress
import os
from pathlib import Path
import stat

from .contracts import Refusal, encode

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempt_storage(
 attempt TEXT PRIMARY KEY,path TEXT NOT NULL,dev INTEGER NOT NULL,ino INTEGER NOT NULL,
 settings TEXT NOT NULL,state TEXT NOT NULL,removed REAL,error TEXT);
"""


async def guard(store, child, outcome):
    """Backpressure new allocation and stop only this owned writer on overflow.

    This is a sampled byte/count bound, not a filesystem quota or data discard.
    """
    while child.returncode is None:
        try:
            usage=store.usage()
            if usage['bytes'] >= store.config['limits']['max_bytes']:
                raise Refusal('cumulative owned storage byte capacity reached')
        except (Refusal,OSError) as exc:
            outcome['error']=str(exc)
            outcome['detail']['storage_capacity_hold']=str(exc)
            with suppress(ProcessLookupError):child.terminate()
            return
        await asyncio.sleep(0.25)


def prepare(store, attempt):
    if store.config.get('session_storage', {}).get('mode') != 'owned-attempt':
        return None
    path = store.home/'sessions'/attempt
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal('owned storage symlink boundary refused')
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    for child in ['sqlite','logs']:(path/child).mkdir(mode=0o700)
    settings = {'sqlite_home': str(path/'sqlite'), 'log_dir': str(path/'logs'),
                'history': {'persistence':'none'}, 'feedback': {'enabled':False}, 'features': {'shell_snapshot':False}}
    info = path.stat()
    with store.tx():
        store.db.execute('INSERT INTO attempt_storage VALUES(?,?,?,?,?,?,NULL,NULL)',
                         (attempt, str(path), info.st_dev, info.st_ino, encode(settings), 'prepared'))
    return settings


def flags(settings):
    if not settings:return []
    result = ['--strict-config']
    for key, value in settings.items():
        if isinstance(value, dict):
            for name, leaf in value.items():result += ['-c', key+'.'+name+'='+encode(leaf)]
        else:result += ['-c', key+'='+encode(value)]
    return result


def verify(store, attempt, settings, returned):
    effective = returned.get('config', {})
    for name, expected in settings.items():
        observed = effective.get(name)
        if isinstance(expected, dict):
            if not isinstance(observed, dict) or any(observed.get(k) != v for k,v in expected.items()):
                raise Refusal('effective owned storage setting missing/overridden: '+name)
        elif observed != expected:
            raise Refusal('effective owned storage path missing/overridden: '+name)
    with store.tx():store.db.execute("UPDATE attempt_storage SET state='effective-paths-verified' WHERE attempt=?", (attempt,))


def eligible(store, row):
    attempt = store.attempt(row['attempt'])
    ended = attempt['ended'] is not None or (attempt['state']=='not-started' and attempt['begin'] is None)
    if not ended or attempt['collected'] is None or row['state'] not in {'effective-paths-verified','prepared'}:
        return False
    from .cleanup import eligible_event
    keys = [attempt['event']] if attempt['event'] else [m['event'] for m in json.loads(store.job(attempt['job'])['members'])]
    events = [store.one('SELECT * FROM events WHERE id=?',(key,)) for key in keys]
    return bool(events) and all(eligible_event(store,e) for e in events)


def remove_tree(fd, remaining):
    """Descriptor-relative exact owned tree; no symlinks, aliases or broad glob."""
    for name in os.listdir(fd):
        remaining[0] -= 1
        if remaining[0] < 0:raise Refusal('owned storage entry bound; retain remainder')
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=fd)
            try:remove_tree(child, remaining)
            finally:os.close(child)
            os.rmdir(name, dir_fd=fd)
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            os.unlink(name, dir_fd=fd)
        else:raise Refusal('unowned/link/special storage entry retained')
    os.fsync(fd)


def sweep(store):
    receipts = []
    for row in store.rows('SELECT * FROM attempt_storage WHERE removed IS NULL'):
        with store.tx():
            if not eligible(store,row):continue
            path = Path(row['path'])
            expected = store.home/'sessions'/row['attempt']
            try:
                if path != expected or any(p.is_symlink() for p in (path,*path.parents)):
                    raise Refusal('exact owned storage path changed')
                info = path.lstat()
                if (info.st_dev,info.st_ino) != (row['dev'],row['ino']):raise Refusal('owned storage inode changed')
                # Keep the parent identity across the final removal, too.
                fd = os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:remove_tree(fd,[store.config['limits'].get('max_files',50000)])
                finally:os.close(fd)
                if (path.lstat().st_dev,path.lstat().st_ino) != (row['dev'],row['ino']):raise Refusal('owned storage root changed before removal')
                path.rmdir()
                if path.exists() or path.is_symlink():raise Refusal('owned namespace changed after removal; replacement retained')
                store.db.execute("UPDATE attempt_storage SET state='owned-paths-physically-retired',removed=?,error=NULL WHERE attempt=?", (store.clock(),row['attempt']))
                receipts.append({'attempt':row['attempt'],'owned_paths':'physically-retired','shared_profile_absence':'not-inventoried'})
            except (Refusal,OSError) as exc:
                store.db.execute('UPDATE attempt_storage SET error=? WHERE attempt=?', (str(exc)[:500],row['attempt']))
                receipts.append({'attempt':row['attempt'],'state':'partial-held','error':type(exc).__name__})
    return receipts
