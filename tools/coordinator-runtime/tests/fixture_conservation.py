"""Keep quiescent, explicitly owned fixtures before normal connection close.

Physical copies are never SQLite inputs. Readback uses a separate retained copy;
its SHM may change. Neither a digest nor a logical query replaces physical bytes.
The caller must select an owned root, stop its writers and retain all outputs.
This helper grants no access, deletion or cleanup authority.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat


def capacity(parent):
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        value = os.fstatvfs(fd)
    finally:
        os.close(fd)
    if value.f_bavail * value.f_frsize - 2 * 1024**3 < 100 * 1024**3 or value.f_favail - 32000 < 1000000:
        raise RuntimeError('full conservation phase would breach OS floor')
    return dict(parent=str(parent), available_bytes=value.f_bavail * value.f_frsize,
                available_inodes=value.f_favail, full_charge_bytes=2 * 1024**3,
                full_charge_entries=32000, leave_bytes=100 * 1024**3, leave_inodes=1000000)


def files(root):
    """Nofollow enumeration of this positively selected fixture only."""
    pending = [Path(root)]
    while pending:
        directory = pending.pop()
        if not stat.S_ISDIR(directory.lstat().st_mode):
            raise ValueError('owned directory required; aliases are not followed')
        with os.scandir(directory) as entries:
            for item in sorted(entries, key=lambda entry: entry.name):
                mode = item.stat(follow_symlinks=False).st_mode
                path = directory / item.name
                if stat.S_ISDIR(mode):
                    pending.append(path)
                elif stat.S_ISREG(mode):
                    yield path
                else:
                    raise ValueError('nonregular fixture member: ' + str(path))


def body(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('regular fixture file required')
        return stream.read()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write(path, value):
    capacity(path.parent)
    with path.open('xb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def directory(path):
    capacity(path.parent)
    path.mkdir(mode=0o700)


def conserve(root, destination):
    """Caller is synchronous/quiescent; verify copy against actual source bytes.

    This is not an atomic multi-file snapshot against concurrent writers. Detect
    changes at the copy boundary and fail with partial material still retained.
    """
    root, destination = Path(root), Path(destination)
    if destination == root or destination.is_relative_to(root):
        raise ValueError('conservation destination must be outside original')
    directory(destination)
    physical = destination / 'physical'
    directory(physical)
    records = []
    for source in files(root):
        relative = source.relative_to(root)
        target = physical / relative
        for parent in reversed(target.parents):
            if parent.is_relative_to(physical) and not parent.exists():
                directory(parent)
        before = source.stat()
        value = body(source)
        write(target, value)
        # Byte comparison is deliberately independent of the digest witness.
        after = source.stat()
        if (body(target) != value or body(source) != value
                or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)):
            raise RuntimeError('original changed during conservation')
        os.chmod(target, 0o400)
        records.append(dict(path=str(relative), bytes=len(value), sha256=sha(value),
                            source_device=before.st_dev, source_inode=before.st_ino,
                            byte_comparison=True))
    record = dict(original=str(root), physical=str(physical), files=records,
                  boundary='before normal close; quiescent caller, no concurrent-writer guarantee')
    write(destination / 'manifest.json', json.dumps(record, sort_keys=True, indent=2).encode())
    verify(record)
    return record


def verify(record):
    """Check that the bytes actually still exist, including every SHM member."""
    physical = Path(record['physical'])
    if {str(p.relative_to(physical)) for p in files(physical)} != {r['path'] for r in record['files']}:
        raise RuntimeError('conserved file extent changed')
    for member in record['files']:
        value = body(physical / member['path'])
        if len(value) != member['bytes'] or sha(value) != member['sha256']:
            raise RuntimeError('conserved bytes changed: ' + member['path'])
    return len(record['files'])


def readback(record, destination):
    """Open only a distinct retained copy, with WAL and SHM carried together."""
    destination = Path(destination)
    if destination == Path(record['physical']) or destination.is_relative_to(Path(record['physical'])):
        raise ValueError('readback must be separate from physical conservation')
    verify(record)
    directory(destination)
    for member in record['files']:
        target = destination / member['path']
        for parent in reversed(target.parents):
            if parent.is_relative_to(destination) and not parent.exists():
                directory(parent)
        write(target, body(Path(record['physical']) / member['path']))
    results = []
    for member in record['files']:
        path = destination / member['path']
        if not body(path).startswith(b'SQLite format 3\x00'):
            continue
        connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        try:
            tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            rows = {table: connection.execute('SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0]
                    for table in tables}
            results.append(dict(path=member['path'], integrity=connection.execute('PRAGMA integrity_check').fetchall(), rows=rows))
        finally:
            connection.close()
    changes = [member['path'] for member in record['files']
               if not (destination / member['path']).exists()
               or sha(body(destination / member['path'])) != member['sha256']]
    retained = verify(record)
    return dict(databases=results, readback_copy_changes=changes, conserved_files_verified=retained,
                meaning='logical readback of separate copy; not exact-byte preservation of that readback copy')


class CloseGate:
    """Keep an owned fixture live until verified conservation permits close.

    Failed attempts are never reused or erased. The live registry retains the
    callback (and its connection) on failure; the same owner can retry normally.
    This is ordinary failure ownership, not host-death or unlimited-resource proof.
    """
    pending = []

    def __init__(self, root, destination, close):
        self.root, self.destination, self.close_original = Path(root), Path(destination), close
        self.attempts, self.record, self.closed = 0, None, False
        self.pending.append(self)

    def preserve(self):
        if self.record is None:
            self.attempts += 1
            candidate = conserve(self.root, self.destination.with_name(
                self.destination.name + '-attempt-' + str(self.attempts)))
            self.record = candidate
        verify(self.record)
        return self.record

    def close(self):
        if self.closed:
            return
        self.preserve()  # On failure the callback is unreachable and stays owned.
        self.close_original()
        self.closed = True
        self.pending.remove(self)
