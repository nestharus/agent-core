"""Runner CLI transport, not a provider enum shim.

Declared roles: orchestration, parser, validator, mapper, accessor, predicate.
The owning CLI/output contracts are linked in agent-adapter.md.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import capture_receipt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from secret_safe_capture import capture_stream, declared_secret_values, load_secret_names
from runtime import require, text, validate_worker


def validate_config(config):
    require(isinstance(config, dict) and set(config) ==
            {'runner', 'model', 'project', 'contract', 'authority'}, 'invalid runner configuration')
    validate_worker('runner', config['runner'])
    text(config['model'])
    for key in ('project', 'contract'):
        require(Path(config[key]).is_absolute(), f'{key} must be absolute')
    require(Path(config['project']).is_dir(), 'project must exist')
    authority = config['authority']
    require(isinstance(authority, dict) and set(authority) ==
            {'owner', 'access', 'effects', 'delegation', 'apply_edits'}, 'explicit authority required')
    for key in ('owner', 'access', 'effects', 'delegation'):
        text(authority[key])
    require(type(authority['apply_edits']) is bool, 'apply_edits must be boolean')
    values = declared_secret_values(load_secret_names(Path(config['contract'])), os.environ)
    require_secret_free(config, values)
    return values


def invoke(config, arguments, log, secrets):
    # Called only by the workflow controller. Tests substitute an executable here,
    # not a made-up acceptance result. Never use shell=True or discard a failed stream.
    with log.open('xb', buffering=0) as sink:
        code = capture_process(config, arguments, sink, secrets)
    capture_receipt.publish(log, code)
    return code


def capture_process(config, arguments, sink, secrets):
    process = spawn(config, arguments)
    try:
        capture_stream(process.stdout, [sink], secrets)
    finally:
        process.stdout.close()
    return process.wait()


def marker_records(data, marker):
    prefix = marker.encode() + b'='
    return [parse_object(line[len(prefix):]) for line in data.splitlines()
            if line.startswith(prefix)]


def parse_object(data):
    try:
        value = json.loads(data)
        return value if isinstance(value, dict) else {}
    except (ValueError, UnicodeError):
        return {}


def valid_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def invocation_id(data):
    # The runner emits its invocation before arbitrary provider payload. Later
    # marker-shaped model text does not replace that identity.
    records = marker_records(data, 'OULIPOLY_INVOCATION')
    if not records:
        return None
    first = records[0]
    return first.get('id') if valid_uuid(first.get('id')) else None


def terminal_record(data, identity, code):
    records = [record for record in marker_records(data, 'OULIPOLY_RESULT')
               if result_shape(record) and record['id'] == identity]
    if code != 0 or not records:
        return None
    last = records[-1]
    return last if last['success'] and last['exit_code'] == 0 else None


def result_shape(record):
    return (valid_uuid(record.get('id')) and type(record.get('success')) is bool
            and type(record.get('exit_code')) is int
            and record.get('status') in ('succeeded', 'failed')
            and isinstance(record.get('finished_at'), str)
            and 'terminal_reason' in record and 'error_category' in record)


def trace_root(data, identity, code):
    value = parse_object(data)
    root = value.get('root', {})
    require(isinstance(root, dict), 'trace root must be an object')
    invocation = root.get('invocation')
    require(isinstance(invocation, dict), 'trace invocation must be an object')
    require(code == 0 and value.get('requested_id') == identity
            and invocation.get('id') == identity
            and invocation.get('agent_runner_invocation_id') == identity,
            'trace absent, malformed or foreign; admission remains unresolved')
    require(isinstance(root.get('session'), dict), 'trace session missing')
    return root


def trace_completed(root):
    invocation = root['invocation']
    return (invocation.get('status') == 'succeeded' and invocation.get('success') is True
            and type(invocation.get('exit_code')) is int and invocation['exit_code'] == 0
            and isinstance(invocation.get('finished_at'), str) and bool(invocation['finished_at']) and not invocation.get('stale_running'))


def established_session(root, target):
    session = root['session']
    identity = session.get('provider_session_id')
    if not valid_uuid(identity) or session.get('id') != identity:
        return None
    if target is not None:
        return identity if identity == target and session.get('resume_acceptance') == 'accepted' else None
    return identity if session.get('capture_method') in (
        'forced_flag_verified', 'stdout_json_event', 'external_provider_launch') else None


def locate_result(data, code, target):
    value = parse_object(data)
    error = value.get('error')
    if code == 10 and isinstance(error, dict) and error.get('code') == 'session-not-found':
        return 'unavailable'
    require(code == 0 and value.get('session_id') == target
            and value.get('transcript_state') == 'available'
            and valid_uuid(value.get('chain_id')) and location_shape(value),
            'session lookup unresolved; no submission')
    return 'available'


def dispatch_arguments(config, prompt, target):
    arguments = ['-m', config['model'], '-p', config['project'], '-f', str(prompt)]
    if target is not None:
        arguments = ['resume', '--session-id', target] + arguments
    return arguments


def require_secret_free(value, secrets):
    require(not any(secret in os.fsencode(item) for item in strings(value) for secret in secrets),
            'declared secret in caller context; remove it before dispatch')


def strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for part in [*value.keys(), *value.values()] for item in strings(part)]
    if isinstance(value, list):
        return [item for part in value for item in strings(part)]
    return []


class LaunchNotSubmitted(OSError):
    """Popen itself failed before returning a child; not a capture/exit error."""


def spawn(config, arguments):
    try:
        return subprocess.Popen(config['runner'] + arguments, cwd=config['project'],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, bufsize=0)
    except OSError as exc:
        raise LaunchNotSubmitted(str(exc)) from exc


def location_shape(value):
    return (isinstance(value.get('provider_name'), str) and bool(value['provider_name'])
            and value.get('storage_type') in ('claude_code', 'codex_session', 'other')
            and absolute_text(value.get('jsonl_path')) and absolute_text(value.get('workspace_root'))
            and type(value.get('mutable')) is bool)


def absolute_text(value):
    return isinstance(value, str) and Path(value).is_absolute()
