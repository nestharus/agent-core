"""Finite cooperative Linux file transactions; no external state discovery."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import uuid

MAX_STATE = 262144
MAX_BUDGET = 524288
LIMITS = {'bytes': 134217728, 'reads': 268435456, 'entries': 1024}
# Normal work cannot consume the last quarter. Original-owner readback and
# settlement may use it; it is finite headroom, never a new grant or refund.
HEADROOM = {'bytes': 33554432, 'reads': 67108864, 'entries': 256}


class Held(Exception):
    """No effect authorized; caller retains the responsibility."""


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def check_capacity(path, bytes=0, entries=0):
    s = os.statvfs(path)
    on_os = os.stat(path).st_dev == os.stat('/').st_dev
    byte_floor, inode_floor = (16 * 1024**3, 100000) if on_os else (1024**3, 2000)
    # Round a bounded write up to filesystem blocks, including metadata slack.
    allocation = ((bytes + s.f_frsize - 1) // s.f_frsize + entries) * s.f_frsize
    if s.f_bavail * s.f_frsize - allocation < byte_floor or s.f_favail - entries < inode_floor:
        raise Held('capacity floor: retain work, no allocation')


def read_regular(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise Held('finite single-link regular file required')
        raw = f.read(maximum + 1)
        after = os.fstat(f.fileno())
        current = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) > maximum or identity(before) != identity(after) or identity(after) != identity(current):
            raise Held('file changed during bounded read')
        return raw


class Files:
    def __init__(self, path, *, clock=time.time, fault=lambda phase: None):
        self.path = Path(path)
        if not self.path.is_absolute():
            raise Held('absolute dedicated state path required')
        # Refuse links in every component. This is a cooperative namespace, not
        # hostile-writer protection or a file-system-wide identity attestation.
        for component in reversed([self.path, *self.path.parents]):
            s = os.lstat(component)
            if not stat.S_ISDIR(s.st_mode):
                raise Held('state ancestry must be real directories')
        s = self.path.stat()
        if s.st_uid != os.getuid() or s.st_mode & 0o077:
            raise Held('state directory must be own 0700')
        self.clock, self.fault = clock, fault
        self.continuation = False
        self.future = {}

    def sync(self):
        fd = os.open(self.path, os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def charge(self, *, bytes=0, reads=0, entries=0, future=None):
        """Write-ahead cumulative reservations, including refused/failed work.

        A torn charge record holds the runtime. It is never truncated or reset.
        Charged I/O is a conservative logical allocation, not physical usage.
        """
        raw = read_regular(self.path / 'budget.jsonl', MAX_BUDGET)
        previous = {'seq': 0, 'bytes': 0, 'reads': 0, 'entries': 0, 'hash': ''}
        for line in raw.splitlines(keepends=True):
            try:
                record = json.loads(line)
                body = {k: v for k, v in record.items() if k != 'hash'}
                if not line.endswith(b'\n') or record['hash'] != digest(body) or body['prior'] != previous['hash']:
                    raise ValueError()
                if record['seq'] != previous['seq'] + 1:
                    raise ValueError()
                for key in LIMITS:
                    if type(record[key]) is not int or record[key] < previous[key]:
                        raise ValueError()
            except (ValueError, KeyError, TypeError) as exc:
                raise Held('budget damaged; preserve and reconcile, no reset') from exc
            previous = record
        body = {'seq': previous['seq'] + 1, 'prior': previous['hash'],
                'bytes': previous['bytes'] + bytes + 1024,
                'reads': previous['reads'] + reads + len(raw),
                'entries': previous['entries'] + entries}
        if any(body[k] + (future or {}).get(k, 0) > LIMITS[k] for k in LIMITS):
            raise Held('cumulative budget exhausted; preserve ownership, no refund')
        if not self.continuation and any(body[k] + (future or {}).get(k, 0) > LIMITS[k] - HEADROOM[k] for k in LIMITS):
            raise Held('work pressure hold; reserved original-owner readback/settlement only')
        line = encode({**body, 'hash': digest(body)})
        if len(raw) + len(line) > MAX_BUDGET:
            raise Held('finite charge journal full; no reset')
        if not self.continuation and len(raw) + len(line) > MAX_BUDGET - 131072:
            raise Held('work pressure hold; charge journal continuation headroom')
        check_capacity(self.path, len(line) + 4096, 0)
        fd = os.open(self.path / 'budget.jsonl', os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        try:
            if os.write(fd, line) != len(line):
                raise Held('partial budget charge; retain damaged journal')
            os.fsync(fd)
        finally:
            os.close(fd)
        return body

    @contextmanager
    def lock(self):
        fd = os.open(self.path / 'lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink != 1:
                raise Held('invalid stable lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Held('metadata busy; retry same operation, no launch') from exc
            yield
        finally:
            os.close(fd)

    def save(self, state):
        raw = encode({'state': state, 'hash': digest(state)})
        if len(raw) > MAX_STATE:
            raise Held('finite state full; preserve current state')
        self.charge(bytes=len(raw), entries=1, future=self.future)
        check_capacity(self.path, len(raw), 1)
        name = self.path / ('.pending-' + uuid.uuid4().hex)
        fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        self.fault('before-replace')
        os.replace(name, self.path / 'state.json')
        self.sync()
        self.fault('after-replace')

    @contextmanager
    def transaction(self, *, readonly=False, continuation=False):
        with self.lock():
            self.continuation = continuation
            self.future = {}
            try:
                size = os.lstat(self.path / 'state.json').st_size
                if size > MAX_STATE:
                    raise Held('finite state exceeded')
                self.charge(reads=size + 1)
                try:
                    envelope = json.loads(read_regular(self.path / 'state.json', size))
                    state = envelope['state']
                    if envelope['hash'] != digest(state) or state['schema'] != 1:
                        raise ValueError()
                except (ValueError, KeyError, TypeError) as exc:
                    raise Held('invalid state; preserve, no fallback') from exc
                yield state
                if not readonly:
                    state['generation'] += 1
                    self.save(state)
            finally:
                self.continuation = False
                self.future = {}
