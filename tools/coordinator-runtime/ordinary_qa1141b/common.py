"""Positive-file package integrity. This module imports no candidate code."""
import hashlib
import json
import os
from pathlib import Path
import stat

BASE = '2a242eb6c126bf8605613c784bf9660927074388'
TREE = 'f1ce8066e17bd79381d00b84f8150a0bce69bf1d'
PARENT = 'b1b4d0740efb2a1956e3b9e9ceb50857863b5652'
PREFIX = 'tools/coordinator-runtime/coordinator_runtime/'
CANDIDATE = {
    PREFIX + '__init__.py': {'bytes': 107, 'sha256': '5d66d9f12796aefad7c957ac274a0c29a5145f2c2cfbda869447c7710006619b'},
    PREFIX + 'contracts.py': {'bytes': 44985, 'sha256': '78f8765295520fc99c69c3ef4c9c6e187c1a4e8805ac5c8b6ec107f69a0ea8f6'}}
SCRIPTS = ('common.py', 'behavior.py', 'runner.py', 'readback.py', 'ORACLE.json', 'PROCEDURE.md')
TOOLS = {
    '/usr/bin/python3.12': {'bytes': 8020928, 'sha256': 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'},
    '/usr/bin/bwrap': {'bytes': 72160, 'sha256': 'e318903862396f96de3df57264e0158682b952fd3fb53ac23d876413e7b30f71'}}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def plain(path, directory=False):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and str(path) == os.fspath(path), 'absolute canonical path required')
    for parent in reversed((path, *path.parents)):
        s = parent.lstat()
        require(not stat.S_ISLNK(s.st_mode), 'symlink refused')
    s = path.lstat()
    require(stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode), 'ordinary file/directory required')
    return path


def record(path, maximum=4 * 1024 * 1024):
    path = plain(path)
    require(path.stat().st_size <= maximum, 'positive file exceeds finite bound')
    body = path.read_bytes()
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def load_json(path):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'duplicate metadata key')
            result[k] = v
        return result
    path = plain(path)
    require(path.stat().st_size <= 1024 * 1024, 'bounded metadata required')
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(RuntimeError('non-JSON number')))


def exclusive(path, body):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(body); f.flush(); os.fsync(f.fileno())


def load(instance, pin):
    instance = plain(instance, True)
    require(record(instance / 'MANIFEST.json')['sha256'] == pin, 'manifest identity changed')
    m = load_json(instance / 'MANIFEST.json')
    require(m['version'] == 1 and m['base'] == BASE and m['tree'] == TREE and m['parent'] == PARENT, 'candidate release identity changed')
    require(Path.cwd() == Path(m['candidate']), 'candidate CWD differs from manifest')
    require(m['candidate_files'] == CANDIDATE, 'candidate positive closure changed')
    for name, expected in CANDIDATE.items():
        require(record(Path(m['candidate']) / name) == expected, 'candidate bytes changed')
    require(set(m['scripts']) == set(SCRIPTS), 'package positive closure changed')
    for name, expected in m['scripts'].items():
        require(record(instance / name) == expected, 'package bytes changed')
    require(m['tools'] == TOOLS, 'tool release changed')
    for name, expected in TOOLS.items():
        require(record(name, 32 * 1024 * 1024) == expected, 'public tool bytes changed')
    return m
