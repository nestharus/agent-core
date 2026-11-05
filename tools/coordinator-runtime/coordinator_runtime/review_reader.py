"""Whole-command native read facade; stable across pinned correction cycles.

Only the service writes the manifest. The reviewer can execute this one command
repeatedly: it streams factual material in bounded chunks, then cycles for
rereading. No file path, shell operation or goal is accepted from reviewer text.
One verified current item is cached beside the owned cursor, within a fixed
size bound. Emitted items are never reacquired merely to reach later items.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import stat

CHUNK = 12000
MAX_ITEM = 33554432
MAX_STATE = 1048576


def digest(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('exact selected regular path required')
    with path.open('rb') as stream:
        body = stream.read(MAX_ITEM + 1)
    if len(body) > MAX_ITEM:
        raise ValueError('selected material exceeds single-item read bound')
    return body


def items(manifest):
    """Enumerate metadata only; skipping an item must not acquire its body."""
    for path, sha in manifest.get('prior_histories', {}).items():
        yield 'prior-history:' + path, ('file', path, sha)
    yield 'history', ('history', manifest['history'], manifest['history_sha256'])
    for path, sha in manifest['method_files'].items():
        yield path, ('file', path, sha)
    yield 'actual-correction-diff', ('text', manifest['correction_diff'], None)
    for source, witness in manifest['source'].items():
        yield source, ('git', source, witness['sha256'])


def storage_bound(manifest):
    """Peak one-item cache plus cursor, checked by the service before launch."""
    sizes = [len(manifest['correction_diff'].encode())]
    sizes.extend(w['bytes'] for w in manifest['source'].values())
    for path in {*manifest.get('prior_histories', {}), manifest['history'], *manifest['method_files']}:
        observed = stamp(path)
        sizes.append(observed[2] if observed else 0)
    if any(type(size) is not int or not 0 <= size <= MAX_ITEM for size in sizes):
        raise ValueError('selected material exceeds single-item read bound')
    maximum = max(sizes)
    return maximum + 32 * ((maximum + CHUNK - 1) // CHUNK) + MAX_STATE


def stamp(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('exact selected regular path required')
    try:
        value = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(value.st_mode):
        raise ValueError('selected material must be regular')
    return [value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def acquire(manifest, item, files):
    kind, source, expected = item
    if kind in {'file', 'history'}:
        before = stamp(source)
        body = b'' if kind == 'history' and before is None else read(source)
        if stamp(source) != before:
            raise ValueError('selected material changed during acquisition')
        files[source] = before
    elif kind == 'text':
        body = source.encode()
    else:
        if not 0 <= manifest['source'][source]['bytes'] <= MAX_ITEM:
            raise ValueError('selected source exceeds single-item read bound')
        child = subprocess.Popen(['/usr/bin/git', '--no-replace-objects', '-C', manifest['repository'], 'show', source],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            body = child.stdout.read(MAX_ITEM + 1)
            if len(body) > MAX_ITEM:
                raise ValueError('selected source exceeds single-item read bound')
            if child.wait() != 0:
                raise ValueError('original pinned source unavailable')
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
            child.stdout.close()
        if len(body) != manifest['source'][source]['bytes']:
            raise ValueError('original pinned source length differs')
    if len(body) > MAX_ITEM or expected is not None and digest(body) != expected:
        raise ValueError('whole selected material differs/exceeds bound')
    return body


def cached_chunk(path, manifest, item, state, offset):
    """Seal one fully verified item; check identity and each returned chunk.

    Mutable originals already encountered are stat-checked on every call. A
    changed identity refuses, even if bytes were restored. This owned cursor and
    cache are cooperative local state, not an adversarial same-account boundary.
    """
    cache = path.with_suffix('.item')
    fd = os.open(cache, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        current = os.fstat(fd)
        if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1:
            raise ValueError('single-link owned item cache required')
        if offset == 0:
            body = acquire(manifest, item, state['files'])
            os.ftruncate(fd, 0)
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                for start in range(0, len(body), CHUNK):
                    part = body[start:start + CHUNK]
                    stream.write(hashlib.sha256(part).digest() + part)
                stream.flush()
                os.fsync(fd)
            state['cache'] = {'bytes': len(body), 'sha256': digest(body), 'stamp': stamp(cache)}
        saved = state['cache']
        if stamp(cache) != saved['stamp']:
            raise ValueError('verified current-item cache changed')
        total = saved['bytes']
        if offset > total or offset % CHUNK:
            raise ValueError('cursor exceeds immutable selected material')
        os.lseek(fd, offset // CHUNK * (CHUNK + 32), os.SEEK_SET)
        raw = os.read(fd, 32 + min(CHUNK, total - offset)) if total else b''
        chunk = raw[32:]
        if total and (len(chunk) != min(CHUNK, total - offset) or hashlib.sha256(chunk).digest() != raw[:32]):
            raise ValueError('verified current-item chunk differs')
        if stamp(cache) != saved['stamp']:
            raise ValueError('verified current-item cache changed during read')
        return chunk, total, saved['sha256']
    finally:
        os.close(fd)


def next_chunk(path):
    path = Path(path)
    raw = read(path)
    manifest = json.loads(raw)
    revision = digest(raw)
    # This is only an owned read cursor, never a second work/recovery journal.
    cursor = path.with_suffix('.cursor')
    descriptor = os.open(cursor, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        saved = os.read(descriptor, MAX_STATE + 1)
        if len(saved) > MAX_STATE:
            raise ValueError('owned cursor exceeds metadata bound')
        state = json.loads(saved) if saved else {}
        if state.get('revision') != revision or state.get('format') != 2:
            state = {'revision': revision, 'format': 2, 'item': 0, 'offset': 0, 'files': {}}
        for original, witnessed in state.get('files', {}).items():
            if stamp(original) != witnessed:
                raise ValueError('previously verified selected file changed')
        state.setdefault('files', {})
        item_index, offset = state.get('item', 0), state.get('offset', 0)
        found = False
        for index, (label, item) in enumerate(items(manifest)):
            if index < item_index:
                continue
            chunk, total, sha = cached_chunk(path, manifest, item, state, offset)
            # Base64 is explicit for non-UTF8/split UTF8 chunks. Never silently
            # replace bytes and call that a complete material read.
            try:
                text, encoding = chunk.decode(), 'utf8'
            except UnicodeDecodeError:
                text, encoding = base64.b64encode(chunk).decode(), 'base64'
            through = offset + len(chunk)
            answer = {'material_revision': revision, 'item': index, 'source': label, 'offset': offset,
                      'through': through, 'total_bytes': total, 'sha256': sha, 'encoding': encoding, 'text': text}
            state.update(item=index + (through == total), offset=0 if through == total else through)
            found = True
            break
        if not found:
            answer = {'material_revision': revision, 'end_of_material': True,
                      'meaning': 'all supplied chunks emitted; reading/coverage/acceptance is not inferred; next call rereads from history'}
            state = {'revision': revision, 'format': 2, 'item': 0, 'offset': 0, 'files': {}}
        encoded = json.dumps(state).encode()
        if len(encoded) > MAX_STATE:
            raise ValueError('owned cursor exceeds metadata bound')
        os.lseek(descriptor, 0, 0); os.ftruncate(descriptor, 0)
        with os.fdopen(descriptor, 'wb', closefd=False) as stream:
            stream.write(encoded); stream.flush(); os.fsync(descriptor)
        return answer
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('one exact service-owned manifest required')
    print(json.dumps(next_chunk(sys.argv[1]), ensure_ascii=False))
