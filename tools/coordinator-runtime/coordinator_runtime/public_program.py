"""Complete bounded public program identity, without retaining its body.

Callers supply actual current read authority and every exclusion before entering.
No execution, path search, alias following or underlying model inquiry occurs.
"""
import hashlib
import os
from pathlib import Path
import stat

from .contracts import Refusal
from .resource_scopes import root


def identity(path, size, maximum, exclusions=()):
    path = root(str(path), exclusions, metadata=False)
    if (set(path.parts) & {'.ssh', '.aws', '.config', '.local'}
            or any(part.startswith(('.codex', '.claude')) for part in path.parts)):
        raise Refusal('private namespace excluded before public program metadata')
    if (type(size) is not int or type(maximum) is not int
            or not 0 < size <= maximum <= 1024**3):
        raise Refusal('finite complete public program size/read ceiling required')
    descriptors = []
    def opened_parent():
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(parent)
        for part in path.parts[1:-1]:
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(parent)
        return parent
    stable = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
                        s.st_ctime_ns, s.st_mode, s.st_uid, s.st_gid, s.st_nlink)
    try:
        parent = opened_parent()
        ancestors = [(os.fstat(fd).st_dev, os.fstat(fd).st_ino) for fd in descriptors]
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        descriptors.append(fd)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode)
                or before.st_size != size or not before.st_mode & 0o111
                or before.st_mode & 0o6000):
            raise Refusal('exact regular executable required before body acquisition')
        total, hasher = 0, hashlib.sha256()
        while True:
            block = os.read(fd, min(1024*1024, maximum+1-total))
            if not block:
                break
            total += len(block)
            if total > maximum:
                raise Refusal('public program grew beyond complete read ceiling')
            hasher.update(block)
        first_hash = hasher.hexdigest()
        # Filesystems may report unchanged coarse timestamps for an in-place
        # write. A second complete bounded pass must agree with the first.
        os.lseek(fd, 0, os.SEEK_SET)
        checked, confirmation = 0, hashlib.sha256()
        while True:
            block = os.read(fd, min(1024*1024, maximum+1-checked))
            if not block:
                break
            checked += len(block)
            if checked > maximum:
                raise Refusal('public program grew beyond confirmation ceiling')
            confirmation.update(block)
        if checked != total or confirmation.hexdigest() != first_hash:
            raise Refusal('public program changed between complete identity passes')
        after = os.fstat(fd)
        if total != size or stable(before) != stable(after):
            raise Refusal('public program changed during complete identity acquisition')
        # Reopen every component from the anchor: a renamed/replaced ancestor
        # must not let a stable detached descriptor certify the current path.
        start = len(descriptors)
        current_parent = opened_parent()
        current = [(os.fstat(d).st_dev, os.fstat(d).st_ino) for d in descriptors[start:]]
        current_file = os.stat(path.name, dir_fd=current_parent, follow_symlinks=False)
        if current != ancestors or stable(current_file) != stable(after):
            raise Refusal('public program path identity changed')
        return dict(path=str(path), bytes=total, max_bytes=maximum, sha256=hasher.hexdigest(),
                    dev=after.st_dev, ino=after.st_ino, mode=stat.S_IMODE(after.st_mode),
                    uid=after.st_uid, gid=after.st_gid, mtime_ns=after.st_mtime_ns,
                    ctime_ns=after.st_ctime_ns, stable_before_after_path=True,
                    body_retained=False, executed=False, complete_passes=2,
                    read_bytes=total+checked, max_read_bytes=2*maximum)
    finally:
        for fd in reversed(descriptors):
            os.close(fd)
