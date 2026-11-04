"""Whole-command native read facade; stable across pinned correction cycles.

Only the service writes the manifest. The reviewer can execute this one command
repeatedly: it streams factual material in bounded chunks, then cycles for
rereading. No file path, shell operation or goal is accepted from reviewer text.
Source bodies stay in their original Git repository/definition/history homes.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CHUNK = 12000


def digest(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('exact selected regular path required')
    return path.read_bytes()


def items(manifest):
    for path, sha in manifest.get('prior_histories', {}).items():
        body = read(path)
        if digest(body) != sha:
            raise ValueError('whole original permitted history changed')
        yield 'prior-history:' + path, body
    history = Path(manifest['history'])
    body = read(history) if history.exists() else b''
    if digest(body) != manifest['history_sha256']:
        raise ValueError('whole permitted history changed')
    yield 'history', body
    for path, sha in manifest['method_files'].items():
        body = read(path)
        if digest(body) != sha:
            raise ValueError('current selected method changed')
        yield path, body
    yield 'actual-correction-diff', manifest['correction_diff'].encode()
    for source, witness in manifest['source'].items():
        process = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-C', manifest['repository'], 'show', source],
                                 check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if digest(process.stdout) != witness['sha256'] or len(process.stdout) != witness['bytes']:
            raise ValueError('original pinned source body differs')
        yield source, process.stdout


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
        saved = os.read(descriptor, 4096)
        state = json.loads(saved) if saved else {}
        item_index, offset = (state.get('item', 0), state.get('offset', 0)) if state.get('revision') == revision else (0, 0)
        found = False
        for index, (label, body) in enumerate(items(manifest)):
            if index < item_index:
                continue
            if offset > len(body):
                raise ValueError('cursor exceeds immutable selected material')
            chunk = body[offset:offset + CHUNK]
            # Base64 is explicit for non-UTF8/split UTF8 chunks. Never silently
            # replace bytes and call that a complete material read.
            try:
                text, encoding = chunk.decode(), 'utf8'
            except UnicodeDecodeError:
                text, encoding = base64.b64encode(chunk).decode(), 'base64'
            through = offset + len(chunk)
            answer = {'material_revision': revision, 'item': index, 'source': label, 'offset': offset,
                      'through': through, 'total_bytes': len(body), 'sha256': digest(body), 'encoding': encoding, 'text': text}
            state = {'revision': revision, 'item': index + (through == len(body)), 'offset': 0 if through == len(body) else through}
            found = True
            break
        if not found:
            answer = {'material_revision': revision, 'end_of_material': True,
                      'meaning': 'all supplied chunks emitted; reading/coverage/acceptance is not inferred; next call rereads from history'}
            state = {'revision': revision, 'item': 0, 'offset': 0}
        os.lseek(descriptor, 0, 0); os.ftruncate(descriptor, 0)
        os.write(descriptor, json.dumps(state).encode()); os.fsync(descriptor)
        return answer
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('one exact service-owned manifest required')
    print(json.dumps(next_chunk(sys.argv[1]), ensure_ascii=False))
