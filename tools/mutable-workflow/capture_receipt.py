"""Local full-capture receipt, not upstream delivery evidence.

Declared roles: orchestration, mapper, validator, accessor.
"""
import hashlib
import json
import os


def descriptor(data, code):
    return dict(version=1, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), returncode=code)


def publish(log, code):
    # invoke has consumed EOF, redaction tail and wait before calling this.
    with log.open('rb') as stream:
        os.fsync(stream.fileno())
    data = log.read_bytes()
    path = log.with_suffix(log.suffix + '.capture.json')
    temporary = path.with_suffix('.tmp')
    with temporary.open('x') as stream:
        json.dump(descriptor(data, code), stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read(log, data):
    path = log.with_suffix(log.suffix + '.capture.json')
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or any(type(value.get(key)) is not int
            for key in ('version', 'bytes', 'returncode')):
        raise ValueError('invalid complete-capture receipt; reconcile storage')
    if value != descriptor(data, value['returncode']):
        raise ValueError('complete-capture receipt mismatch; missing/corrupt bytes, no prefix settlement')
    return value
