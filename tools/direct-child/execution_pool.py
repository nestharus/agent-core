#!/usr/bin/env python3
"""Public Codex allocation control. No account stores or provider calls.

Reservations consume a durable round-robin turn, even if never launched. Pool
updates and launch admissions cooperate on the same counter lock. Existing calls
are never moved. Direct edits/noncooperating writers are outside this protocol.
"""

from contextlib import contextmanager
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib

PROFILES = {'.codex', '.codex2', '.codex3', '.codex4', '.codex5'}
DEFAULT_ROUTES = Path.home() / 'ai/tools/direct-child/routes.toml'
MAX_ROUTES = 1024 * 1024
MAX_COUNTER = 4096

MEMBERSHIP = rb'(?ms)(^\[providers\.codex\][^\[]*?^pool\s*=\s*)\[[^\]]*\]'


class PoolError(Exception):
    pass


class PoolBusy(PoolError):
    pass


def replace_membership(raw, enabled):
    """Change only the supported public setting, retaining every other byte."""
    changed, n = re.subn(MEMBERSHIP, lambda m: m[1] + json.dumps(enabled).encode(), raw)
    if n != 1:
        raise PoolError('unsupported public pool syntax; no update')
    original = tomllib.loads(raw.decode())
    original['providers']['codex']['pool'] = enabled
    if tomllib.loads(changed.decode()) != original:
        raise PoolError('public pool syntax does not isolate membership; no update')
    return changed


def counter_value(value):
    if not value or not value.isascii() or not value.isdigit():
        raise PoolError('empty/malformed existing rotation counter; no reset/fallback')
    try:
        return int(value)
    except ValueError as exc:
        raise PoolError('rotation counter exceeds supported integer conversion; no reset/fallback') from exc


def bounded_read(path, maximum):
    """Finite regular public control, refusing links and growth before parse."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb', buffering=0) as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise PoolError('public control exceeds finite regular-file bound')
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
        current = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mode, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) > maximum or identity(before) != identity(after) or identity(after) != identity(current):
            raise PoolError('public control changed or exceeded acquisition bound')
        return raw


class Pool:
    def __init__(self, routes=DEFAULT_ROUTES, *, reader=bounded_read, charge=lambda amount: None, before_write=lambda parent: None, before_access=lambda path, operation: None):
        self.reader, self.charge, self.before_write = reader, charge, before_write
        self.before_access = before_access
        self.routes = Path(routes)
        if not self.routes.is_absolute():
            raise PoolError('absolute public pool routes path required')

    def read(self):
        try:
            raw = self.reader(self.routes, MAX_ROUTES)
            config = tomllib.loads(raw.decode())
            entry = config['providers']['codex']
            pool, manual = entry['pool'], entry['manual_profiles']
            for values in (pool, manual):
                if (not isinstance(values, list) or any(not isinstance(p, str) or p not in PROFILES for p in values)
                        or len(values) != len(set(values))):
                    raise PoolError('invalid Codex pool/authorization names or duplicates')
            if not set(pool) <= set(manual):
                raise PoolError('enabled pool is outside public manual authorization')
            state = Path(os.path.expanduser(config['rotation']['state_dir']))
            if not state.is_absolute():
                raise PoolError('absolute rotation state directory required')
            return raw, pool, state / 'codex.counter'
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise PoolError('public execution pool unavailable/invalid: ' + str(exc)) from exc

    @contextmanager
    def locked(self, blocking=True, expected_control=None):
        raw, _, path = self.read()
        self.assert_control(raw, expected_control)
        self.before_write(path.parent)
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Stable control lock serializes first creation too. Retain the old
            # counter flock for compatibility with existing automatic allocators.
            self.before_access(path.with_suffix('.pool.lock'), 'create')
            guard_fd = os.open(path.with_suffix('.pool.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            with os.fdopen(guard_fd, 'r+') as control:
                self.lock(control, blocking)
                try:
                    self.before_access(path, 'create')
                    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                    created = True
                except FileExistsError:
                    self.before_access(path, 'access')
                    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
                    created = False
                with os.fdopen(fd, 'r+') as handle:
                    handle._pool_path = path
                    self.lock(handle, blocking)
                    raw, pool, current_path = self.read()
                    self.assert_control(raw, expected_control)
                    if current_path != path:
                        raise PoolError('rotation state path changed; explicit cutover required')
                    value = self.read_counter(handle)
                    if not value:
                        if not created:
                            raise PoolError('empty existing rotation counter; unknown state, no reset/fallback')
                        self.before_access(path, 'write')
                        handle.write('0\n')
                        handle.flush()
                        os.fsync(handle.fileno())
                    yield handle, raw, pool, counter_value(value or '0')
        except (OSError, UnicodeError) as exc:
            raise PoolError('public execution pool lock/state unavailable: ' + str(exc)) from exc

    def read_counter(self, handle):
        # Current exact-target authority after any intervening control reread.
        path = getattr(handle, '_pool_path', None)
        if path is not None:
            self.before_access(path, 'read')
        # Precharge before body acquisition, including malformed/failed reads.
        self.charge(MAX_COUNTER + 1)
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_COUNTER:
            raise PoolError('rotation counter exceeds finite regular-file bound')
        value = os.read(handle.fileno(), MAX_COUNTER + 1).decode('ascii')
        if len(value) > MAX_COUNTER:
            raise PoolError('rotation counter grew beyond finite bound')
        return value.strip()

    @staticmethod
    def lock(handle, blocking):
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise PoolBusy('execution pool control busy; retry before any launch') from exc

    def witness(self, raw, pool, count):
        return {'routes': str(self.routes), 'routes_sha256': hashlib.sha256(raw).hexdigest(),
                'enabled': pool, 'turn': count, 'profile': pool[count % len(pool)] if pool else None,
                'availability': 'not-probed', 'fairness': 'durable reservation turns; no refund on failure'}

    def control_binding(self, raw):
        """Static public bytes, with only the supported membership value masked."""
        return {'routes': str(self.routes),
                'static_sha256': hashlib.sha256(replace_membership(raw, [])).hexdigest()}

    def assert_control(self, raw, expected):
        if expected is not None and self.control_binding(raw) != expected:
            raise PoolError('selected static execution pool control changed; no allocation/admission')

    def status(self, *, blocking=True, expected_control=None):
        with self.locked(blocking, expected_control) as (_, raw, pool, count):
            return {**self.witness(raw, pool, count), 'state': 'enabled' if pool else 'empty',
                    'next_is_reserved': False}

    def preview(self):
        """Inspect an unreserved turn without creating or changing control state.

        An absent counter means the first turn. An existing empty/corrupt or busy
        counter cannot advertise eligibility, including for a singleton pool.
        This snapshot is never a reservation or a substitute for admission.
        """
        raw, pool, path = self.read()
        self.eligible(pool)
        try:
            self.before_access(path, 'read')
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            count = 0
        except OSError as exc:
            raise PoolError('public execution pool preview unavailable: ' + str(exc)) from exc
        else:
            try:
                with os.fdopen(fd, 'r', encoding='ascii', errors='replace') as handle:
                    handle._pool_path = path
                    self.lock(handle, False)
                    raw, pool, current_path = self.read()
                    if current_path != path:
                        raise PoolError('rotation state path changed; explicit cutover required')
                    self.eligible(pool)
                    value = self.read_counter(handle)
                    count = counter_value(value)
            except OSError as exc:
                raise PoolError('public execution pool preview unavailable: ' + str(exc)) from exc
        return {**self.witness(raw, pool, count), 'state': 'enabled',
                'next_is_reserved': False}

    def allocate(self, authorized=None, *, blocking=True, expected_control=None):
        with self.locked(blocking, expected_control) as (handle, raw, pool, count):
            self.eligible(pool, authorized)
            chosen = self.witness(raw, pool, count)
            try:
                next_value = str(count + 1) + '\n'
            except ValueError as exc:
                raise PoolError('next rotation counter exceeds supported integer conversion; no reset/fallback') from exc
            self.before_access(handle._pool_path, 'write')
            handle.seek(0)
            handle.write(next_value)
            handle.flush()
            os.fsync(handle.fileno())
            handle.truncate()
            return chosen

    @staticmethod
    def eligible(pool, authorized=None):
        if not pool:
            raise PoolError('execution pool empty; no allocation/launch/fallback')
        if authorized is not None and not set(pool) <= set(authorized):
            raise PoolError('execution pool exceeds runtime account authorization; explicit compatibility decision required')

    @contextmanager
    def admission(self, profile, authorized=None, *, blocking=True, expected_control=None):
        with self.locked(blocking, expected_control) as (_, raw, pool, count):
            self.eligible(pool, authorized)
            if profile not in pool:
                raise PoolError('reserved execution profile disabled before launch: ' + profile)
            witness = self.witness(raw, pool, count)
            witness['next_reservation_turn'] = witness.pop('turn')
            yield {**witness, 'profile': profile,
                   'boundary': 'cooperative admission held through local process creation; no reassignment'}

    def set(self, enabled):
        if (not isinstance(enabled, list) or any(not isinstance(p, str) or p not in PROFILES for p in enabled)
                or len(set(enabled)) != len(enabled)):
            raise PoolError('enabled must contain distinct authorized Codex names (empty is allowed)')
        with self.locked() as (_, raw, _, count):
            config = tomllib.loads(raw.decode())
            if not set(enabled) <= set(config['providers']['codex']['manual_profiles']):
                raise PoolError('pool update cannot expand account authorization')
            for binding in config.get('native', {}).get('bindings', []):
                if binding.get('provider') == 'codex' and not set(enabled) <= set(binding.get('site_routes', {})):
                    raise PoolError('enabled pool lacks a declared native account route; explicit compatibility decision required')
            changed = replace_membership(raw, enabled)
            temp = None
            try:
                fd, temp = tempfile.mkstemp(prefix='.pool-update-', dir=self.routes.parent)
                with os.fdopen(fd, 'wb') as out:
                    os.fchmod(out.fileno(), self.routes.stat().st_mode & 0o777)
                    out.write(changed)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temp, self.routes)
                temp = None
                directory = os.open(self.routes.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if temp is not None:
                    os.unlink(temp)
            return {**self.witness(changed, enabled, count), 'state': 'enabled' if enabled else 'empty',
                    'effective': 'subsequent cooperating allocations/admissions; existing calls unchanged'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--routes', default=str(DEFAULT_ROUTES))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    update = sub.add_parser('set')
    update.add_argument('enabled', nargs='*', help='ordered enabled names; no names disables new execution')
    execute = sub.add_parser('exec', help='Admit a previously reserved profile immediately before exec; never allocate/retry')
    execute.add_argument('--profile', required=True)
    execute.add_argument('--receipt', required=True)
    execute.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        pool = Pool(args.routes)
        if args.command == 'exec':
            command = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
            if not command:
                raise PoolError('exec requires an actual command')
            try:
                with pool.admission(args.profile) as admission:
                    Path(args.receipt).write_text(json.dumps({'state': 'admitted', **admission}) + '\n')
                    os.execvp(command[0], command)
            except PoolError as exc:
                Path(args.receipt).write_text(json.dumps({'state': 'not-started', 'error': str(exc)}) + '\n')
                raise
        result = pool.status() if args.command == 'status' else pool.set(args.enabled)
        print(json.dumps(result, sort_keys=True))
        return 2 if args.command == 'status' and result['state'] != 'enabled' else 0
    except (PoolError, OSError) as exc:
        print(json.dumps({'state': 'held', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
