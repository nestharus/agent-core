"""625 owned protocol fiction: fresh current unknown, one staged write.

No provider or shell is run. Command notifications are fictional evidence.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

plan = json.loads(Path(sys.argv[1]).read_text())
thread = str(uuid.uuid4())
turn = None
count = 0
original = None

def emit(value):
    print(json.dumps(value), flush=True)

def response(request, value):
    emit({'id': request['id'], 'result': value})

def notification(method, **fields):
    emit({'method': method, 'params': {'threadId': thread, 'turnId': turn, **fields}})

def terminal(value, name):
    text = value if isinstance(value, str) else json.dumps({'payload_json': json.dumps(value)})
    notification('item/completed', item={'id': name, 'type': 'agentMessage',
        'phase': 'final_answer', 'text': text})

def end():
    notification('turn/completed', turn={'id': turn, 'status': 'completed', 'items': [], 'error': None})

def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

for line in sys.stdin:
    request = json.loads(line)
    method = request.get('method')
    params = request.get('params', {})
    if method == 'initialize':
        response(request, {'codexHome': os.environ['CODEX_HOME']})
    elif method == 'config/read':
        response(request, {'config': {'history': {'persistence': 'none'}, 'feedback': {'enabled': False},
            'features': {'shell_snapshot': False}}, 'origins': {}})
    elif method == 'thread/start':
        response(request, {'thread': {'id': thread, 'sessionId': thread, 'ephemeral': True, 'path': None},
            'model': params['model'], 'modelProvider': params['modelProvider'],
            'reasoningEffort': params['config']['model_reasoning_effort'],
            'sandbox': {'type': 'readOnly' if plan.get('consumer') else 'workspaceWrite', 'networkAccess': False}})
    elif method == 'turn/start':
        count += 1
        turn = str(uuid.uuid4())
        response(request, {'turn': {'id': turn, 'status': 'inProgress'}})
        prompt = params['input'][0]['text']
        with Path(plan['trace']).open('a') as trace:
            trace.write(json.dumps({'thread': thread, 'turn': turn, 'ordinal': count}) + '\n')
        if plan.get('consumer'):
            assert count == 1
            terminal({'semantic': 'DONE', 'category': 'complete', 'summary': 'Consumed exact owned upstream fixture.',
                'findings': [{'consumed': 625}], 'failures': [], 'unknowns': [], 'artifacts': [],
                'handoffs': [], 'no_handoff_reason': 'Delegated owner callback consumes this final report.'}, 'consumer-625')
            end()
            continue
        if count == 1:
            context = json.JSONDecoder().raw_decode(prompt.split('TASK_CONTEXT=', 1)[1])[0]
            for target, stage in context['staged_targets'].items():
                Path(stage).write_text(json.dumps({'consumer': Path(target).stem, 'verified': 625}))
            Path(plan['writes']).write_text('one preparation, seven distinct stages\n')
            Path(plan['evidence']).write_text('Original identity uncertainty remains attributed.\n')
            original = {'semantic': 'PARTIAL', 'category': 'blocker', 'summary': 'Stages prepared; command correlation still owed.',
                'findings': [{'fixture': 625, 'prepared': 7}], 'failures': [],
                'unknowns': [{'scope': 'own-stage-verification', 'question': 'Which exact observed command verified the prepared stages?'}],
                'artifacts': [plan['evidence']], 'handoffs': plan.get('handoffs', []),
                'completion': {'version': 1, 'local': 'blocked', 'failures': [], 'tools': [],
                    'unknowns': [{'index': 0, 'status': 'unresolved', 'owner': 'producer',
                        'duty': 'stage-command-correlation', 'reason': 'Exact command identity must be linked to the stage check.'}]}}
            if not original['handoffs']:
                original['no_handoff_reason'] = 'The delegated collector owns this internal fixture result.'
            notification('item/completed', item={'id': 'stage-check-625', 'type': 'commandExecution',
                'command': 'fictional-stage-verifier --all-seven --run 625', 'status': 'completed',
                'exitCode': None if plan.get('missing_close') else 0, 'durationMs': 1})
            if not plan.get('legacy'):
                terminal('{invalid original 625', 'invalid-origin-625')
            terminal(original, 'blocked-origin-625')
            end()
        else:
            assert count == 2, 'Only one owned clarification is permitted'
            rows = json.JSONDecoder().raw_decode(prompt.split('OBSERVED_TOOL_METADATA=', 1)[1])[0]
            assert len(rows) == 1 and rows[0]['id'] == 'stage-check-625'
            answer = copy.deepcopy(original)
            if not plan.get('unresolved'):
                answer.update(semantic='DONE', category='complete', summary='Own verification correlated; original unknown conserved.')
                prior = {k: v for k, v in original['completion']['unknowns'][0].items() if k != 'index'}
                binding = {k: rows[0][k] for k in ['id', 'thread', 'turn', 'command_sha256', 'command_bytes', 'exit_code', 'status']}
                reason = 'The exact stage verifier notification checks all seven stages from this single preparation.'
                entry = {'subject': {'kind': 'unknown', 'index': 0, 'original_hash': sha(answer['unknowns'][0]),
                            'prior_disposition': prior}, 'command_bindings': [binding],
                         'verification_items': [binding['id']], 'causal_reason': reason}
                body = json.dumps({'version': 1, 'resolutions': [entry]}).encode()
                Path(plan['evidence']).write_bytes(body)
                ref = {'path': plan['evidence'], 'sha256': hashlib.sha256(body).hexdigest()}
                answer['completion'].update(local='ready', unknowns=[{'index': 0, **prior, 'status': 'resolved',
                    'prior_disposition': prior, 'command_bindings': [binding], 'verification_items': [binding['id']],
                    'causal_reason': reason, 'evidence': [ref], 'causal_evidence': {**ref, 'entry': 0}}])
            terminal(answer, 'qualified-current-625')
            if plan.get('competing'):
                terminal({**answer, 'summary': 'Materially competing current answer.'}, 'competing-current-625')
            end()
            if plan.get('late'):
                terminal(answer, 'late-current-625')
    elif method == 'thread/read':
        response(request, {'thread': {'id': thread, 'status': {'type': 'idle'}}})
    elif method == 'thread/unsubscribe':
        response(request, {'status': 'unsubscribed'})
    elif method == 'turn/interrupt':
        response(request, {})
        notification('turn/completed', turn={'id': turn, 'status': 'interrupted', 'items': [], 'error': None})
