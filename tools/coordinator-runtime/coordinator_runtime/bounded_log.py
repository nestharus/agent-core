"""Bounded observation and opaque kernel conservation, never a whole-log witness.

Successful counted kernel copies conserve bytes without returning old bodies to
Python. Intents survive interruption; no replay/rollback of an uncertain write.
The selected cooperative lock does not exclude noncooperating writers.
"""
import json
import os
from pathlib import Path
import stat

from .contracts import Refusal, digest, encode
from .custody import safe_path, read_file
from .cleanup import open_parent

KIND = 'catalog-bounded-log-v1'


def selected(task):
    return task.get('routine_completion', {}).get('kind') == KIND


def inventory(policy):
    return [p for p in policy['targets'] if p != policy['bounded_log']['target']]


def validate(task, policy):
    spec = policy.get('bounded_log')
    if (set(policy) != {'kind', 'targets', 'bounded_log'} or task['role'] != 'Work'
            or task['phase'] != 'integrator' or len(policy['targets']) != 7
            or len(set(policy['targets'])) != 7 or not isinstance(spec, dict)
            or set(spec) != {'target', 'max_lines', 'max_bytes', 'max_entry_bytes'}
            or spec['target'] not in policy['targets'] or spec['max_lines'] != 12
            or type(spec['max_bytes']) is not int or not 1 <= spec['max_bytes'] <= 65536
            or type(spec['max_entry_bytes']) is not int or not 1 <= spec['max_entry_bytes'] <= 65536):
        raise Refusal('seven catalog duties and exact bounded log policy required')


def metadata(info):
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()):
        raise Refusal('owned single-link regular bounded log required')
    return {'dev': info.st_dev, 'ino': info.st_ino, 'size': info.st_size,
            'mtime': info.st_mtime_ns, 'ctime': info.st_ctime_ns,
            'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid, 'gid': info.st_gid}


def prefix(fd, spec):
    result = bytearray()
    lines = 0
    # One-byte pread deliberately never crosses the twelfth physical line.
    while lines < spec['max_lines'] and len(result) < spec['max_bytes']:
        byte = os.pread(fd, 1, len(result))
        if not byte:
            break
        result.extend(byte)
        lines += byte == b'\n'
    return bytes(result)


def open_log(store, spec):
    name = spec['target']
    if any(Path(name) == Path(p) or Path(name).is_relative_to(Path(p))
           for p in store.config.get('artifact_exclusions', [])):
        raise Refusal('bounded log excluded before metadata')
    path = safe_path(name, [name])
    parent, leaf = open_parent(Path('/'), path)
    try:
        fd = os.open(leaf, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except BaseException:
        os.close(parent)
        raise
    return parent, leaf, fd


def observe(store, spec):
    parent, leaf, fd = open_log(store, spec)
    try:
        before = metadata(os.fstat(fd))
        bounded = prefix(fd, spec)
        if before != metadata(os.fstat(fd)) or before != metadata(os.stat(leaf, dir_fd=parent, follow_symlinks=False)):
            raise Refusal('bounded log changed during observation')
        return {'exists': True, **before, 'bounded_prefix_hex': bounded.hex(),
                'observation': {'max_lines': spec['max_lines'], 'max_bytes': spec['max_bytes']},
                'whole_log_hash': None}
    finally:
        os.close(fd)
        os.close(parent)


def copy_exact(source, destination, length, destination_offset=0):
    offset = 0
    while offset < length:
        count = os.copy_file_range(source, destination, min(length-offset, 1048576),
                                   offset_src=offset, offset_dst=destination_offset+offset)
        if count <= 0:
            raise Refusal('opaque kernel copy incomplete; retain original custody')
        offset += count
    return offset


def write_entry(fd, entry):
    offset = 0
    while offset < len(entry):
        count = os.pwrite(fd, entry[offset:], offset)
        if count <= 0:
            raise Refusal('bounded entry short write')
        offset += count


def publish(store, board, job, attempt, run, task, fence):
    spec = task['routine_completion']['bounded_log']
    target = spec['target']
    from .publication import stages
    entry_path = stages(store, attempt['id'])[target]
    entry, witness = read_file(safe_path(entry_path, [str(store.home/'artifacts'/attempt['id']/'staged')]), spec['max_entry_bytes'])
    held = store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?', (attempt['id'], entry_path))
    if not held or held['sha256'] != witness['sha256'] or not entry or not entry.endswith(b'\n'):
        raise Refusal('actual nonempty newline-terminated bounded entry and durable custody required')
    before = json.loads(run['before_files'])[target]
    prior = store.one('SELECT * FROM file_publications WHERE attempt=? AND target=?', (attempt['id'], target))
    if prior:
        if prior['state'] != 'published' or prior['proposed_sha'] != witness['sha256']:
            raise Refusal('interrupted bounded log intent remains owned; never replay')
        if observe(store, spec) != json.loads(prior['witness'])['after']:
            raise Refusal('published bounded log changed; original custody required')
        return dict(prior)
    if observe(store, spec) != before:
        raise Refusal('bounded log precondition changed; no peer overwrite')
    parent, leaf, fd = open_log(store, spec)
    backup_fd = None
    backup = store.home/'artifacts'/attempt['id']/'bounded-log.before.opaque'
    try:
        if metadata(os.fstat(fd)) != {k: before[k] for k in metadata(os.fstat(fd))}:
            raise Refusal('bounded log descriptor changed')
        fence()
        store.budget(None, before['size']+len(entry)+4096)
        # Exclusive opaque backup creation. A partial/unrecorded backup is held,
        # never replaced. No body/hash/custody.capture of this recovery source.
        backup_fd = os.open(backup, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        copied = copy_exact(fd, backup_fd, before['size'])
        os.fsync(backup_fd)
        directory = os.open(backup.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if observe(store, spec) != before:
            raise Refusal('bounded log changed while conserving opaque bytes')
        with store.tx():
            store.db.execute('INSERT INTO canonical_backups VALUES(?,?,?,?)', (attempt['id'], target, str(backup), encode(before)))
            store.db.execute("INSERT INTO file_publications VALUES(?,?,'intent',?,?,NULL,NULL)",
                             (attempt['id'], target, witness['sha256'], str(backup)))
        fence()
        if observe(store, spec) != before:
            raise Refusal('bounded log changed before mutation')
        restored = copy_exact(backup_fd, fd, before['size'], len(entry))
        write_entry(fd, entry)
        os.ftruncate(fd, before['size']+len(entry))
        os.fsync(fd)
        after = observe(store, spec)
        if (after['dev'], after['ino'], after['size'], after['mode'], after['uid'], after['gid']) != (
                before['dev'], before['ino'], before['size']+len(entry), before['mode'], before['uid'], before['gid']):
            raise Refusal('bounded log same-inode/size/ownership readback failed')
        if os.pread(fd, len(entry), 0) != entry:
            raise Refusal('actual new entry readback failed')
        receipt = {'method': 'counted-kernel-copy-prepend-v1', 'before': before, 'after': after,
                   'entry': {'path': entry_path, 'sha256': witness['sha256'], 'bytes': len(entry)},
                   'opaque_backup': str(backup), 'conserved_bytes': copied, 'shifted_bytes': restored,
                   'whole_old_content_semantic_read': False, 'whole_log_hash': None,
                   'unknown_effects': []}
        with store.tx():
            store.db.execute("UPDATE file_publications SET state='published',witness=? WHERE attempt=? AND target=?",
                             (encode(receipt), attempt['id'], target))
        return store.one('SELECT * FROM file_publications WHERE attempt=? AND target=?', (attempt['id'], target))
    except BaseException as exc:
        with store.tx():
            store.db.execute('UPDATE file_publications SET error=? WHERE attempt=? AND target=?',
                             (type(exc).__name__+': '+str(exc)[:500], attempt['id'], target))
        raise
    finally:
        if backup_fd is not None:
            os.close(backup_fd)
        os.close(fd)
        os.close(parent)
