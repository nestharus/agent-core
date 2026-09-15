"""Deterministic executable double for the discovered runner CLI wire contract.

Never imports or launches agents. Mode changes are controlled by the test caller.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid

root = Path.cwd()
mode = json.loads((root / 'fake-mode.json').read_text())
args = sys.argv[1:]
with (root / 'runner-calls.jsonl').open('a') as calls:
    calls.write(json.dumps(args) + '\n')


def emit(marker, value):
    print(marker + '=' + json.dumps(value), flush=True)


def handshake(name):
    address = mode.get(name)
    if address:
        with socket.socket(socket.AF_UNIX) as sock:
            sock.connect(address)
            sock.sendall(b'ready')
            assert sock.recv(1) == b'!'


if args[0] == 'session':
    session = args[2]
    if mode.get('lookup', 'available') != 'available':
        code = mode['lookup']
        print(json.dumps({'error': {'code': code, 'message': 'fixture lookup refusal'}}), file=sys.stderr)
        sys.exit({'session-not-found': 10, 'operational-error': 1, 'unsupported-storage': 12}[code])
    print(json.dumps(dict(session_id=session, chain_id=str(uuid.UUID(int=10)), provider_name='fixture',
                          storage_type='other', jsonl_path=str(root/'session.jsonl'),
                          workspace_root=str(root), transcript_state='available', mutable=False)))
    sys.exit(0)

if args[0] == 'trace':
    path = root / (args[1] + '.json')
    if not path.exists():
        print('invocation absent', file=sys.stderr)
        sys.exit(1)
    trace = json.loads(path.read_text())
    if mode.get('trace_override'):
        trace['root']['invocation'].update(mode['trace_override'])
    if 'acceptance_override' in mode:
        trace['root']['session']['resume_acceptance'] = mode['acceptance_override']
    if mode.get('foreign_trace'):
        trace['requested_id'] = str(uuid.UUID(int=999))
    if mode.get('malformed_trace'):
        trace['root']['invocation'] = None
    print(json.dumps(trace))
    sys.exit(0)

prompt = json.loads(Path(args[args.index('-f') + 1]).read_text())
(root / 'last-prompt.json').write_text(json.dumps(prompt))
# Exercise the prompted existing evidence surface rather than reimplement it.
evidence = prompt['context']['evidence_access']['output_argv'] + ['--attempt', '1']
output = subprocess.run(evidence, check=True, capture_output=True, text=True)
(root / 'inspected-output.json').write_text(output.stdout)
identity = str(uuid.uuid4())
resuming = args[0] == 'resume'
session = args[args.index('--session-id') + 1] if resuming else str(uuid.UUID(int=20))
if mode.get('omit_identity'):
    print('partial output without control identity', flush=True)
    sys.exit(1)
emit('OULIPOLY_INVOCATION', dict(source='fixture', id=identity))
# Arbitrary provider marker-bearing bytes must not poison final-record selection.
emit('OULIPOLY_RESULT', dict(id=identity, status='failed', success=False, exit_code=9,
                            error_category='payload-only', terminal_reason=None, finished_at='earlier'))
print('arbitrary payload \x00 ' + os.environ.get('FAKE_DECLARED_SECRET', ''), flush=True)
current = prompt['context']['current']
response = dict(exchange_id=prompt['exchange_id'], run_id=current['run_id'],
                basis_cursor=prompt['context']['cursor'], kind=mode.get('kind', 'observation'),
                detail='bounded fixture result', edit=None)
if response['kind'] == 'edit':
    response['edit'] = dict(run_id=current['run_id'], cursor=current['cursor'], actor='fixture-agent',
                           reason='investigate with caller-granted local worker',
                           effects='local fake worker only; no new registry or credentials',
                           operations=mode.get('operations', [
                               dict(op='insert', before=None, steps=[dict(id='investigation', worker='local', input='ordinary')]),
                               dict(op='goto', step='investigation')]))
if mode.get('wrong_basis'):
    response['basis_cursor'] += 1
if not mode.get('omit_response'):
    emit('MUTABLE_WORKFLOW_RESPONSE', response)
code = mode.get('exit', 0)
complete = mode.get('complete', True)
invocation = dict(id=identity, agent_runner_invocation_id=identity, row_id=1, source='fixture',
                  model_name='fixture-model', parent_id=None,
                  status='succeeded' if complete and code == 0 else 'failed' if complete else 'running',
                  success=code == 0 if complete else None, exit_code=code if complete else None,
                  error_category=None, terminal_reason=None,
                  returned_artifacts=[dict(version_id='fixture-artifact-version', name='partial-evidence',
                  store_address=dict(workflow_run_id=current['run_id'], artifact_name='partial-evidence', version=1),
                  sha256='0' * 64, content_len=0, format_hint=None, verdict_line=None,
                  source=dict(kind='inline_bytes'), producer_invocation_uuid=identity,
                  returned_at='2026-09-15T00:00:01Z')],
                  started_at='2026-09-15T00:00:00Z', finished_at='2026-09-15T00:00:01Z' if complete else None)
trace = dict(requested_id=identity, generated_at='2026-09-15T00:00:02Z', root=dict(
    invocation=invocation, session=dict(id=session, provider_session_id=session,
    chain_id=str(uuid.UUID(int=10)), agent_runner_chain_id=str(uuid.UUID(int=10)),
    capture_method='resumed' if resuming else 'forced_flag_verified', transcript_path=None,
    transcript_state='no_locator', resume_acceptance=mode.get('acceptance', 'accepted') if resuming else None,
    resume_acceptance_evidence='fixture acceptance pattern' if resuming else None), warnings=[], children=[]))
if mode.get('no_session'):
    trace['root']['session'].update(id=None, provider_session_id=None, capture_method='none')
(root / (identity + '.json')).write_text(json.dumps(trace))
if mode.get('barrier'):
    print('padding' * 20000, flush=True)
handshake('barrier')
if mode.get('contrary_suffix'):
    emit('MUTABLE_WORKFLOW_RESPONSE', dict(response, kind='question', edit=None,
        detail='Do not apply the preceding edit; caller authority is unresolved'))
emit('OULIPOLY_RESULT', dict(id=identity, status='succeeded' if code == 0 else 'failed',
                            success=code == 0, exit_code=code, error_category=None,
                            terminal_reason=None, finished_at='2026-09-15T00:00:01Z'))
sys.exit(code)
