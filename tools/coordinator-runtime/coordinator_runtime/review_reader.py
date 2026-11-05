"""Bounded whole-command material reader with one disposable active-item cache.

The manifest and cursor retain factual selection/progress only. A body is fully
verified once per visit, then emitted by offset from a single private cache.
Original files stay in their homes; immutable Git pins never become HEAD reads.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

CHUNK = 12000
CACHE_MAX = 32 * 1024 * 1024


def digest(body):
    return hashlib.sha256(body).hexdigest()


def selected_path(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('exact selected regular path required')
    return path


def read(path):
    return selected_path(path).read_bytes()


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid, info.st_gid, info.st_nlink]


def file_identity(path):
    path = selected_path(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('selected material must be a regular file')
    return identity(info)


def selections(manifest):
    """Describe items without acquiring bodies that the cursor already passed."""
    result = [('prior-history:' + p, 'file', p, sha) for p, sha in manifest.get('prior_histories', {}).items()]
    result.append(('history', 'history', manifest['history'], manifest['history_sha256']))
    result.extend((p, 'file', p, sha) for p, sha in manifest['method_files'].items())
    result.append(('actual-correction-diff', 'diff', None, None))
    result.extend((p, 'git', p, witness['sha256']) for p, witness in manifest['source'].items())
    return result


def acquire(manifest, selection, maximum):
    label, kind, source, expected = selection
    witness = None
    if kind in {'file', 'history'}:
        witness = file_identity(source)
        if witness is None and kind == 'history':
            body = b''
        else:
            with selected_path(source).open('rb') as stream:
                before = identity(os.fstat(stream.fileno()))
                if before != witness or before[2] > maximum:
                    raise ValueError('selected file changed or exceeds active-item bound')
                body = stream.read(maximum + 1)
                if identity(os.fstat(stream.fileno())) != before or file_identity(source) != before:
                    raise ValueError('selected material changed during acquisition')
    elif kind == 'diff':
        body = manifest['correction_diff'].encode()
    else:
        process = subprocess.Popen(['/usr/bin/git', '--no-replace-objects', '-C', manifest['repository'], 'show', source],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            body = process.stdout.read(maximum + 1)
            if len(body) > maximum:
                process.kill()
                raise ValueError('pinned source exceeds active-item bound; original retained')
            if process.wait() != 0:
                raise ValueError('original pinned source unavailable')
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
            process.wait()
    if len(body) > maximum:
        raise ValueError('selected material exceeds active-item bound; original retained')
    actual = digest(body)
    if expected is not None and actual != expected:
        raise ValueError('whole selected history/method/pinned source changed')
    if kind == 'git' and len(body) != manifest['source'][source]['bytes']:
        raise ValueError('original pinned source length differs')
    return body, actual, witness


def next_chunk(path):
    path = selected_path(path)
    raw = read(path)
    manifest = json.loads(raw)
    revision = digest(raw)
    maximum = min(CACHE_MAX, manifest.get('cache_max_bytes', CACHE_MAX))
    if type(maximum) is not int or maximum <= 0:
        raise ValueError('positive bounded active-item capacity required')
    cursor = path.with_suffix('.cursor')
    descriptor = os.open(cursor, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    cache = None
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        with os.fdopen(os.dup(descriptor), 'rb') as stream:
            saved = stream.read(1024 * 1024 + 1)
        if len(saved) > 1024 * 1024:
            raise ValueError('material cursor exceeds bounded metadata capacity')
        state = json.loads(saved) if saved else {}
        if state.get('revision') != revision:
            state = {'revision': revision, 'item': 0, 'offset': 0, 'files': {}}
        selected = selections(manifest)
        legacy = 'files' not in state
        if legacy:
            # An existing emission-only cursor keeps its exact position. Check
            # prior mutable inputs once when establishing their new witnesses.
            state['files'] = {}
            for selection in selected[:state['item']]:
                if selection[1] in {'file', 'history'}:
                    _, _, witness = acquire(manifest, selection, maximum)
                    state['files'][selection[2]] = witness
        # Revalidate already-observed mutable inputs without reacquiring their
        # bodies. Changed, replaced or newly created histories refuse even when
        # emission has moved on to a later source item.
        for source, witness in state['files'].items():
            if file_identity(source) != witness:
                raise ValueError('previously emitted history/method changed')
        index, offset = state['item'], state['offset']
        cache = os.open(path.with_suffix('.item'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        info = os.fstat(cache)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ValueError('single private owned active-item file required')
        if index == len(selected):
            answer = {'material_revision': revision, 'end_of_material': True,
                      'meaning': 'all supplied chunks emitted; reading/coverage/acceptance is not inferred; next call rereads from history'}
            state.update(item=0, offset=0)
        else:
            if not 0 <= index < len(selected) or offset < 0:
                raise ValueError('cursor exceeds immutable selected material')
            active = state.get('active')
            if active is None:
                if offset and not legacy:
                    raise ValueError('active-item witness missing')
                body, sha, witness = acquire(manifest, selected[index], maximum)
                os.ftruncate(cache, 0)
                with os.fdopen(os.dup(cache), 'wb') as stream:
                    stream.write(body); stream.flush(); os.fsync(stream.fileno())
                active = {'identity': identity(os.fstat(cache)), 'sha256': sha, 'bytes': len(body)}
                if selected[index][1] in {'file', 'history'}:
                    state['files'][selected[index][2]] = witness
            if offset > active['bytes']:
                raise ValueError('cursor exceeds immutable selected material')
            if identity(os.fstat(cache)) != active['identity']:
                raise ValueError('verified active material cache changed')
            chunk = os.pread(cache, CHUNK, offset)
            if identity(os.fstat(cache)) != active['identity']:
                raise ValueError('verified active material cache changed while emitting')
            try:
                text, encoding = chunk.decode(), 'utf8'
            except UnicodeDecodeError:
                text, encoding = base64.b64encode(chunk).decode(), 'base64'
            through = offset + len(chunk)
            answer = {'material_revision': revision, 'item': index, 'source': selected[index][0], 'offset': offset,
                      'through': through, 'total_bytes': active['bytes'], 'sha256': active['sha256'], 'encoding': encoding, 'text': text}
            complete = through == active['bytes']
            state.update(item=index + complete, offset=0 if complete else through, active=None if complete else active)
        if state.get('active') is None:
            os.ftruncate(cache, 0)  # Only this disposable verified cache; never original material.
        encoded = json.dumps(state).encode()
        if len(encoded) > 1024 * 1024:
            raise ValueError('material cursor exceeds bounded metadata capacity')
        os.lseek(descriptor, 0, 0); os.ftruncate(descriptor, 0)
        os.write(descriptor, encoded); os.fsync(descriptor)
        return answer
    finally:
        if cache is not None:
            os.close(cache)
        os.close(descriptor)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('one exact service-owned manifest required')
    print(json.dumps(next_chunk(sys.argv[1]), ensure_ascii=False))
