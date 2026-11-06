"""Exact public QA executable identities, separate from source/evidence roots."""
import hashlib
import os
from pathlib import Path
import re
import stat

from .contracts import Refusal
from .custody import guard_path

# Only installed, canonical, public binaries for these two QA argv[0] roles.
# Neither an ancestor grant nor a credential-capable CLI alias is admitted.
PATHS = {'command': {'/usr/bin/python3.12', '/usr/bin/git'},
         'readback': {'/usr/bin/python3.12', '/usr/bin/git'}}
MAX_BYTES = 32 * 1024 * 1024


def validate(store, pins):
    if not isinstance(pins, dict) or not pins or set(pins) - set(PATHS):
        raise Refusal('public executable pins require exact command/readback roles')
    total = 0
    for role, pin in pins.items():
        if (not isinstance(pin, dict) or set(pin) != {'path', 'bytes', 'sha256'}
                or pin['path'] not in PATHS[role] or type(pin['bytes']) is not int
                or not 1 <= pin['bytes'] <= MAX_BYTES
                or not isinstance(pin['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', pin['sha256'])):
            raise Refusal('bounded canonical public executable identity required')
        total += pin['bytes']
    if total > 64 * 1024 * 1024:
        raise Refusal('public executable acquisition exceeds declared aggregate bound')
    for pin in pins.values():
        identity(store, pin)


def identity(store, pin):
    """Stream complete bytes without retaining executable bodies as evidence."""
    path = pin['path']
    guard_path(store, path)  # Includes opaque exclusions before any metadata.
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    try:
        for part in Path(path).parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = next_fd
        fd = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_mode & 0o022
                or not before.st_mode & 0o111 or before.st_size != pin['bytes']):
            raise Refusal('public executable must be exact installed regular executable bytes')
        h, count, header = hashlib.sha256(), 0, b''
        while True:
            block = os.read(fd, min(65536, pin['bytes'] + 1 - count))
            if not block:
                break
            if not header:
                header = block[:4]
            count += len(block)
            if count > pin['bytes']:
                raise Refusal('public executable grew beyond its exact declared size')
            h.update(block)
        witness = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_uid, s.st_gid)
        if (header != b'\x7fELF' or count != pin['bytes'] or h.hexdigest() != pin['sha256']
                or witness(before) != witness(os.fstat(fd))
                or witness(before) != witness(os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False))):
            raise Refusal('public executable changed or differs from its installed identity')
    except OSError as exc:
        raise Refusal('canonical public executable unavailable') from exc
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)
