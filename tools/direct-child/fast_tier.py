"""One temporary fast-tier policy for new Codex launches; no account inspection.

The adjacent fast-tier file contains exactly true or false. Missing, linked or
invalid policy refuses before launch. Disabled means no tier override, allowing
the original provider/profile semantics. Requests never attest served tier.
"""
import os
from pathlib import Path
import stat
import sys
import tempfile

POLICY = Path(__file__).with_name('fast-tier')


def enabled(path=None):
    path = POLICY if path is None else Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('fast-tier policy must be a regular file')
            raw = stream.read(17)
    except OSError as error:
        raise ValueError('fast-tier policy unavailable; launch refused') from error
    if raw not in (b'true', b'true\n', b'false', b'false\n'):
        raise ValueError('fast-tier policy must contain exactly true or false')
    return raw.rstrip(b'\n') == b'true'


def selection(provider='codex', force=None):
    force = enabled() if force is None else force
    supported = provider == 'codex'
    return {'force_fast': force,
            'requested_service_tier': 'fast' if force and supported else 'profile-default',
            'fast_tier_support': 'codex-request-supported-availability-unverified' if supported else 'not-established-for-provider',
            'served_service_tier': 'unobserved'}


def flags(force):
    return ['-c', 'features.fast_mode=true', '-c', 'service_tier="fast"'] if force else []


def set_policy(value):
    enabled()  # Preserve a missing/invalid current file for its owner.
    before = POLICY.stat(follow_symlinks=False)
    with tempfile.NamedTemporaryFile(dir=POLICY.parent, prefix='.fast-tier-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write((value+'\n').encode())
        stream.flush()
        os.fchmod(stream.fileno(), stat.S_IMODE(before.st_mode))
        os.fsync(stream.fileno())
    current = POLICY.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) != (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size):
        raise ValueError('fast-tier policy changed concurrently; temporary retained')
    os.replace(temporary, POLICY)
    fd = os.open(POLICY.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['get']:
            print(str(enabled()).lower())
        elif sys.argv[1:] in (['set', 'on'], ['set', 'off']):
            set_policy('true' if sys.argv[2] == 'on' else 'false')
            print(str(enabled()).lower())
        else:
            raise ValueError('usage: fast_tier.py get | set on | set off')
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
