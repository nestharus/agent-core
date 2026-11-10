"""One temporary fast-tier policy for new Codex launches; no account inspection.

The adjacent fast-tier file contains exactly true or false. Missing, linked or
invalid policy refuses before launch. Disabled means no tier override, allowing
the original provider/profile semantics. Requests never attest served tier.
"""
from contextlib import contextmanager
import argparse
import fcntl
import os
from pathlib import Path
import stat
import sys
import tempfile

POLICY = Path(__file__).with_name('fast-tier')


@contextmanager
def policy_lock(path=None, *, exclusive=False, before_write=lambda p: None):
    """Stable cooperative guard shared by setters and actual creation adapters.

    A direct edit bypasses the contract. No provider or private account access.
    """
    path = POLICY if path is None else Path(path)
    before_write(path.parent)
    fd = os.open(path.with_name('fast-tier.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('invalid fast-tier stable lock')
        try:
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('fast-tier control busy; no launch/update') from exc
        yield path
    finally:
        os.close(fd)


@contextmanager
def admission(path=None, *, before_write=lambda p: None):
    """Hold enabled fast policy through the adapter's actual Popen boundary."""
    with policy_lock(path, before_write=before_write) as selected:
        if not enabled(selected):
            raise ValueError('selected all-fast policy disabled; no launch')
        yield


def enabled(path=None):
    path = POLICY if path is None else Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb', buffering=0) as stream:
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


def set_policy(value, path=None, *, before_write=lambda p: None):
    with policy_lock(path, exclusive=True, before_write=before_write) as selected:
        _set_policy(value, selected)


def _set_policy(value, selected):
    if value not in {'true', 'false'}:
        raise ValueError('fast-tier value must be true or false')
    enabled(selected)  # Preserve a missing/invalid current file for its owner.
    before = selected.stat(follow_symlinks=False)
    with tempfile.NamedTemporaryFile(dir=selected.parent, prefix='.fast-tier-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write((value+'\n').encode())
        stream.flush()
        os.fchmod(stream.fileno(), stat.S_IMODE(before.st_mode))
        os.fsync(stream.fileno())
    current = selected.stat(follow_symlinks=False)
    if (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) != (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size):
        raise ValueError('fast-tier policy changed concurrently; temporary retained')
    os.replace(temporary, selected)
    fd = os.open(selected.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--routes', type=Path, help='select the routes-adjacent policy and guard')
        sub = parser.add_subparsers(dest='command', required=True)
        sub.add_parser('get')
        sub.add_parser('set').add_argument('value', choices=['on', 'off'])
        args = parser.parse_args()
        if args.routes is not None and not args.routes.is_absolute():
            raise ValueError('absolute public routes path required')
        selected = args.routes.with_name('fast-tier') if args.routes is not None else POLICY
        if args.command == 'set':
            set_policy('true' if args.value == 'on' else 'false', selected)
        print(str(enabled(selected)).lower())
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
