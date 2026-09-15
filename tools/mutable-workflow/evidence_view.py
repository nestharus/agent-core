"""Present evidence samples, distinct from historical settlement and permission.

Declared roles: orchestration, accessor, mapper, validator.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import stat as file_stat

from agent_adapter import show
import runner_transport as transport


RECEIPT_MAX_BYTES = 4096


def evidence(directory, key, verify=False, check_session=False):
    exchange = show(directory, key)  # Original full validation, never reclassify it.
    logs = list(dict.fromkeys([p for p in [exchange.get('log'), exchange.get('lookup', {}).get('log')]
                              + [o['log'] for o in exchange['observations']] if p]))
    return dict(key=key, historical_state=exchange['state'], historical_application=exchange['application'],
                historical_capture=exchange.get('capture_receipt'),
                log_references='recorded' if logs else 'not_recorded',
                logs=[log_status(directory, Path(path), verify, exchange.get('capture_receipt')
                      if path == exchange.get('log') else None) for path in logs],
                session=session_status(exchange, check_session),
                returned_artifacts=[dict(reference=ref, availability='unchecked_external_store',
                    reason='reference is not access permission; no artifact-store reader selected')
                    for ref in exchange.get('returned_artifacts', [])],
                meaning='present samples may race changes; never overwrite historical settlement; no transcript read')


def allowed(root, path):
    return path.resolve().is_relative_to(root.resolve())


def log_status(root, path, verify, retained=None):
    receipt_state, receipt = receipt_status(root, path)
    if retained and receipt and retained != receipt:
        receipt_state = 'mismatch_with_historical_receipt'
    value = log_sample(root, path, verify, retained or receipt)
    return dict(value, receipt=receipt_state)


def log_sample(root, path, verify, expected):
    try:
        return bounded_log_sample(root, path, verify, expected)
    except FileNotFoundError:
        return dict(path=str(path), availability='missing')
    except PermissionError:
        return dict(path=str(path), availability='inaccessible')
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        return dict(path=str(path), availability='unresolved', reason='unreadable or malformed evidence')


def bounded_log_sample(root, path, verify, expected):
    if not allowed(root, path):
        return dict(path=str(path), availability='restricted', reason='outside private run boundary')
    return inspect_log(path, verify, expected)


def receipt_status(root, path):
    receipt = path.with_suffix(path.suffix + '.capture.json')
    try:
        return bounded_receipt(root, receipt)
    except FileNotFoundError:
        return 'missing', None
    except PermissionError:
        return 'inaccessible', None
    except (ValueError, OSError, RuntimeError):
        return 'malformed_or_unreadable', None


def bounded_receipt(root, path):
    if not allowed(root, path):
        return 'restricted', None
    if not file_stat.S_ISREG(path.stat().st_mode):
        return 'unsupported_file_type', None
    # Nonblocking open also covers replacement by a FIFO after the stat sample.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        return read_receipt(descriptor)
    finally:
        os.close(descriptor)


def read_receipt(descriptor):
    sample = os.fstat(descriptor)
    if not file_stat.S_ISREG(sample.st_mode):
        return 'unsupported_file_type', None
    if sample.st_size > RECEIPT_MAX_BYTES:
        return 'oversized', None
    raw = os.read(descriptor, RECEIPT_MAX_BYTES + 1)
    if len(raw) > RECEIPT_MAX_BYTES:
        return 'oversized', None
    return parse_receipt(raw)


def parse_receipt(raw):
    value = json.loads(raw.decode('utf-8'))
    if not isinstance(value, dict) or set(value) != {'version', 'bytes', 'sha256', 'returncode'}:
        return 'malformed', None
    if (type(value['version']) is not int or value['version'] != 1 or type(value['bytes']) is not int
            or value['bytes'] < 0 or type(value['returncode']) is not int or not isinstance(value['sha256'], str)
            or len(value['sha256']) != 64 or any(c not in '0123456789abcdef' for c in value['sha256'])):
        return 'malformed', None
    return 'available', value


def inspect_log(path, verify, expected):
    stat = path.stat()
    if not file_stat.S_ISREG(stat.st_mode):
        return dict(path=str(path), availability='unsupported_file_type')
    probe_read_access(path)
    value = dict(path=str(path), bytes=stat.st_size, availability='available_unverified')
    if expected and stat.st_size != expected['bytes']:
        value['availability'] = 'truncated' if stat.st_size < expected['bytes'] else 'size_mismatch'
        return value
    if verify and expected:
        value['availability'] = verify_log(path, expected, stat)
    return value


def verify_log(path, expected, before):
    with path.open('rb') as stream:
        digest = hash_stream(stream)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        return 'changed_during_check'
    return 'matches_capture' if digest == expected['sha256'] else 'digest_mismatch'


def hash_stream(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(65536), b''):
        digest.update(chunk)
    return digest.hexdigest()


def session_status(exchange, check):
    target = exchange.get('session')
    if not target:
        return dict(availability='identity_unestablished', target=exchange.get('target'))
    if not check:
        return dict(availability='unchecked', session=target)
    try:
        return query_session(exchange, target)
    except (OSError, ValueError, TypeError, KeyError):
        return dict(availability='unresolved', session=target, reason='public lookup failed or ambiguous; no fallback or dispatch')


def query_session(exchange, target):
    config = exchange['request']['config']
    transport.validate_config(config)
    result = subprocess.run(config['runner'] + ['session', 'locate', target, '--json'],
                            cwd=config['project'], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    disposition = transport.locate_result(result.stdout, result.returncode, target)
    return dict(availability=disposition, session=target, returncode=result.returncode,
                basis='present public session locate response; no transcript or semantic-memory claim')


def probe_read_access(path):
    # Opening tests this reader's current access without decoding/copying log bytes.
    with path.open('rb') as stream:
        return stream.readable()
