"""On-demand workflow-owned runner dispatch and consequence application.

Declared roles: orchestration, validator, mapper, formatter, accessor.
"""
from contextlib import closing
import json
from pathlib import Path
import uuid

import capture_receipt
import agent_store as store
import runner_transport as transport
from runtime import connect, exclusive, require
from surgery import amend


RESPONSE_CONTRACT = '''Return exactly one line MUTABLE_WORKFLOW_RESPONSE=<JSON object> on stdout.
Object fields: exchange_id, run_id, basis_cursor, kind, detail, edit.
kind is edit, question, or observation. detail is nonempty text. edit is null unless
kind=edit, when it is the existing cli.py amend JSON, with its original run/cursor.
Questions return to the named caller, not to a user or invented authority.
You may inspect current/since events and attempt evidence at the supplied paths.
Propose bounded investigation by inserting registered workers through an edit;
the caller's next ordinary drive executes them under the existing worker grant.
Do not launch additional agents or workers yourself. Do not mutate the graph directly.
Do not expand access/effects/delegation, credentials, registry or purpose. Tool access
is trusted-local, not sandbox enforcement. Keep secrets out of responses and files.
An edit is future intent, never retrospective completion credit or verified truth.
'''


def log_path(directory, exchange, name):
    return directory / 'agent-exchanges' / exchange['id'] / name


def persist_prompt(directory, exchange, secrets):
    payload = dict(instructions=RESPONSE_CONTRACT, exchange_id=exchange['id'],
                   request=exchange['request'], context=exchange['context'],
                   continuity=exchange['continuity'], target_session=exchange['target'])
    raw = json.dumps(payload, ensure_ascii=True).encode()
    # Inputs are caller-owned private context. Refuse a known declared value
    # rather than alter the question, authority or graph being handed off.
    require(not any(value in raw for value in secrets), 'declared secret in prompt; remove it before dispatch')
    path = log_path(directory, exchange, 'prompt.json')
    path.write_bytes(raw)
    return path


def prepare(directory, db, request, history, secrets):
    exchange = dict(key=request['key'], id=str(uuid.uuid4()), request=request,
                    context=store.context(directory, history), state='prepared',
                    target=None, continuity='fresh', observations=[], response=None,
                    application='not_applied', session=None, returncode=None,
                    invocation=None, capture_protocol='local-receipt-v1', collector=request['config']['authority']['owner'])
    transport.require_secret_free(exchange, secrets)
    log_path(directory, exchange, 'prompt.json').parent.mkdir(parents=True, mode=0o700)
    store.put(db, exchange)
    return exchange


def choose_target(directory, db, exchange, history, secrets):
    prior = store.continuation_basis(history)
    target = prior.get('session') if prior else None
    if target is None:
        record_without_target(exchange, prior)
        return
    config = exchange['request']['config']
    path = log_path(directory, exchange, 'locate.log')
    code = transport.invoke(config, ['session', 'locate', target, '--json'], path, secrets)
    exchange['lookup'] = dict(target=target, returncode=code, log=str(path))
    store.put(db, exchange)
    disposition = transport.locate_result(path.read_bytes(), code, target)
    exchange['continuity'] = 'fresh_fallback' if disposition == 'unavailable' else 'resume_attempt'
    exchange['target'] = target if disposition == 'available' else None
    exchange['fallback_basis'] = exchange['lookup'] if disposition == 'unavailable' else None


def submit(directory, db, exchange, secrets):
    prompt = persist_prompt(directory, exchange, secrets)
    exchange['state'] = 'pending'
    exchange['log'] = str(log_path(directory, exchange, 'runner.log'))
    # Commit before Popen. Loss anywhere after this point never licenses replay.
    store.put(db, exchange)
    config = exchange['request']['config']
    arguments = transport.dispatch_arguments(config, prompt, exchange['target'])
    exchange['returncode'] = transport.invoke(config, arguments, Path(exchange['log']), secrets)
    store.put(db, exchange)
    return collect_owned(directory, db, exchange, secrets)


def ask_owned(directory, db, request, secrets):
    previous = store.find(db, request['key'])
    if previous is not None:
        require(previous['request'] == request, 'key already bound to different request')
        return previous
    history = store.all_exchanges(db)
    store.admit_request(request, history)
    exchange = prepare(directory, db, request, history, secrets)
    try:
        choose_target(directory, db, exchange, history, secrets)
        return submit(directory, db, exchange, secrets)
    except (OSError, ValueError, TypeError) as exc:
        return retain_error(db, exchange, exc)


def retain_error(db, exchange, exc):
    exchange['error'] = str(exc)
    if exchange['state'] == 'prepared' or isinstance(exc, transport.LaunchNotSubmitted):
        exchange['state'] = 'not_submitted'
    store.put(db, exchange)
    return exchange


def read_trace(directory, exchange, secrets):
    index = len(exchange['observations']) + 1
    path = log_path(directory, exchange, f'trace-{index}.log')
    # A previous collector can die after writing the log but before storing its
    # reference. Never overwrite those bytes or accidentally turn a clash green.
    path = path.with_name(f'{path.stem}-{uuid.uuid4()}.log')
    config = exchange['request']['config']
    code = transport.invoke(config, ['trace', exchange['invocation'], '--json'], path, secrets)
    exchange['observations'].append(dict(log=str(path), returncode=code))
    return transport.trace_root(path.read_bytes(), exchange['invocation'], code)


def interpret_trace(exchange, root, data):
    exchange['trace'] = root
    exchange['session'] = transport.established_session(root, exchange['target'])
    exchange['acceptance'] = root['session'].get('resume_acceptance')
    exchange['returned_artifacts'] = root['invocation'].get('returned_artifacts', [])
    exchange['terminal_result'] = transport.terminal_record(data, exchange['invocation'], exchange['returncode'])
    require(exchange['returncode'] in (None, 0), 'recorded runner failure; partial result is not deliverable')
    require(transport.trace_completed(root), 'provider not confirmed completed; retain partials and collect later')
    require(exchange['target'] is None or exchange['session'] == exchange['target'],
            'attempted resume not accepted into target; no fresh replay')
    # Trace establishes upstream completion, not complete local response capture.
    # Neither is workflow completion.
    exchange['completion_basis'] = 'runner_trace'
    exchange['continuity'] = 'same_session' if exchange['target'] else exchange['continuity']


def read_response(exchange, data):
    values = [value for value in transport.marker_records(data, 'MUTABLE_WORKFLOW_RESPONSE')
              if value.get('exchange_id') == exchange['id']]
    require(len(values) == 1, 'missing or multiple bound agent responses; partial evidence retained')
    value = values[0]
    require(set(value) == {'exchange_id', 'run_id', 'basis_cursor', 'kind', 'detail', 'edit'},
            'invalid agent response fields')
    require(value['run_id'] == exchange['context']['current']['run_id']
            and type(value['basis_cursor']) is int
            and value['basis_cursor'] == exchange['context']['cursor'], 'response has foreign basis')
    require(value['kind'] in ('edit', 'question', 'observation') and
            isinstance(value['detail'], str) and bool(value['detail'].strip()), 'invalid response kind/detail')
    require((value['kind'] == 'edit' and isinstance(value['edit'], dict)) or
            (value['kind'] != 'edit' and value['edit'] is None), 'invalid response edit')
    return value


def apply_response(directory, db, exchange):
    response = exchange['response']
    if response['kind'] != 'edit':
        exchange['application'] = 'question_to_caller' if response['kind'] == 'question' else 'no_edit'
        return
    require(exchange['request']['config']['authority']['apply_edits'], 'edit authority not granted')
    edit = response['edit']
    require(edit.get('run_id') == response['run_id'] and edit.get('cursor') == response['basis_cursor'],
            'edit must retain response basis; inspect and request new judgment after stale return')
    apply_atomic(directory, db, exchange, edit)


def apply_atomic(directory, db, exchange, edit):
    with exclusive(directory):
        # amend/save owns the transaction commit: record application in that same
        # transaction, so a lost collector cannot apply a jump/cancel twice.
        exchange['application'] = 'applied'
        exchange['state'] = 'returned'
        store.put(db, exchange, commit=False)
        amend(db, edit)


def collect_owned(directory, db, exchange, secrets):
    if exchange['state'] in ('returned', 'not_submitted'):
        return exchange
    if exchange['state'] == 'prepared':
        return retain_error(db, exchange, ValueError('interrupted before submission intent; new key permitted'))
    path = Path(exchange.get('log', log_path(directory, exchange, 'runner.log')))
    data = path.read_bytes() if path.exists() else b''
    exchange['invocation'] = transport.invocation_id(data)
    try:
        recover_capture(exchange, path, data)
        require(exchange['invocation'] is not None, 'no invocation identity; unknown submission, caller must reconcile')
        root = read_trace(directory, exchange, secrets)
        interpret_trace(exchange, root, data)
        # A validated local receipt is distinct from upstream trace success.
        require(exchange['returncode'] == 0 and exchange.get('capture_receipt') is not None,
                'complete local capture unconfirmed; retained prefix is evidence only, caller must reconcile')
        exchange['response'] = read_response(exchange, data)
        settle_response(directory, db, exchange)
        exchange['state'] = 'returned'
        store.put(db, exchange)
        return exchange
    except (OSError, ValueError, TypeError) as exc:
        db.rollback()
        exchange['state'] = 'pending'
        exchange['application'] = 'not_applied'
        return retain_error(db, exchange, ValueError(str(exc)))


def execute(directory, command, request=None, key=None):
    if command == 'show':
        return show(directory, key)
    with exclusive(directory, 'agent-collector.lock'):
        return execute_owned(directory, command, request, key)


def execute_owned(directory, command, request, key):
    with closing(connect(directory)) as db:
        store.setup(db)
        return operate(directory, db, command, request, key)


def operate(directory, db, command, request, key):
    if command == 'ask':
        store.admit_request(request, [])
        secrets = transport.validate_config(request['config'])
        return ask_owned(directory, db, request, secrets)
    exchange = store.find(db, key)
    require(exchange is not None, 'unknown exchange key')
    secrets = transport.validate_config(exchange['request']['config'])
    return collect_owned(directory, db, exchange, secrets)


def settle_response(directory, db, exchange):
    try:
        apply_response(directory, db, exchange)
        exchange.pop('error', None)
    except (ValueError, TypeError) as exc:
        db.rollback()
        exchange['application'] = 'rejected'
        exchange['error'] = str(exc)


def record_without_target(exchange, prior):
    if prior is None:
        return
    require(prior.get('trace', {}).get('session', {}).get('provider_session_id') is None,
            'previous identity not established; caller must reconcile before fresh dispatch')
    exchange['continuity'] = 'fresh_fallback'
    exchange['fallback_basis'] = dict(prior_exchange=prior['key'],
        detail='completed prior exchange reported no session identity; this request not submitted')


def show(directory, key):
    with closing(connect(directory)) as db:
        exchange = store.find(db, key)
    require(exchange is not None, 'unknown exchange key')
    return exchange


def recover_capture(exchange, path, data):
    receipt = capture_receipt.read(path, data)
    if receipt is not None:
        require(exchange['returncode'] in (None, receipt['returncode']), 'capture exit disagreement')
        exchange['returncode'] = receipt['returncode']
        exchange['capture_receipt'] = receipt
    if receipt is None:
        exchange.pop('capture_receipt', None)
