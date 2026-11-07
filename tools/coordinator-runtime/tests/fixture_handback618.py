"""Fictional protocol transport; no model, shell command, native or provider IO.

Only this process's supplied temporary plan/stage/report/record files are used.
Command events are authored fixtures, not executions of their command strings.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

plan = json.loads(Path(sys.argv[1]).read_text())
thread = str(uuid.uuid4())
turn = None
turns = 0
commands = ['sed -n 1,240p /fiction/runtime/templates/local-integration.md',
            'sed -n 1,260p /fiction/runtime/templates/bounded-catalog.md',
            'sed -n 1,680p /fiction/runtime/local-integration.md',
            'cat /fiction/runtime/bounded-catalog.md']


def send(value):
    print(json.dumps(value), flush=True)


def reply(request, result):
    send({'id': request['id'], 'result': result})


def final(text, identity, owner=None):
    item = {'type': 'agentMessage', 'phase': 'final_answer', 'id': identity, 'text': text}
    send({'method': 'item/completed', 'params': {'threadId': owner or thread, 'turnId': turn, 'item': item}})
    return item


def complete(items=(), status='completed'):
    send({'method': 'turn/completed', 'params': {'threadId': thread,
        'turn': {'id': turn, 'status': status, 'items': list(items), 'error': None}}})


def answer(ready=False):
    failures = [{'kind': 'documentation-read', 'command': commands[i], 'exit_code': 2} for i in range(2)]
    ref = {'path': plan['report'], 'sha256': hashlib.sha256(Path(plan['report']).read_bytes()).hexdigest()}
    partial = plan.get('partial', False)
    return {'semantic': 'PARTIAL' if partial else 'DONE', 'category': 'blocker' if partial else 'complete',
        'summary': 'Prepared stage and exact documentation outcomes retained.',
        'findings': [{'kind': 'fictional-source', 'scope': 'one owned stage; no canonical writes'}],
        'failures': failures, 'unknowns': ['Protocol identities unavailable in the original answer.'] if partial else [],
        'artifacts': [plan['report']], 'handoffs': [], 'no_handoff_reason': 'Controller consumes this internal fixture result.',
        'completion': {'version': 1, 'local': 'ready' if ready and not partial else 'blocked',
            'failures': [{'index': i, 'status': 'resolved' if ready else 'unresolved',
                'evidence': [ref], 'verification_items': ['tool-' + str(i + 2)] if ready else []} for i in range(2)],
            'unknowns': [{'index': 0, 'status': 'unresolved', 'owner': 'producer',
                'duty': 'protocol-identity', 'reason': 'Original unknown retained; no resolved-local-unknown grammar.'}] if partial else [],
            'tools': [{'id': 'tool-' + str(i), 'status': 'resolved',
                'reason': 'Exact failed read and exact successful replacement selected by command fingerprint.',
                'evidence': [ref], 'verification_items': ['tool-' + str(i + 2)]} for i in range(2)] if ready else []}}


for line in sys.stdin:
    request = json.loads(line)
    method, params = request.get('method'), request.get('params', {})
    if method == 'initialize':
        reply(request, {'codexHome': os.environ['CODEX_HOME']})
    elif method == 'config/read':
        reply(request, {'config': {'history': {'persistence': 'none'}, 'feedback': {'enabled': False},
            'features': {'shell_snapshot': False}}, 'origins': {}})
    elif method == 'thread/start':
        reply(request, {'thread': {'id': thread, 'sessionId': thread, 'ephemeral': True, 'path': None},
            'model': params['model'], 'modelProvider': params['modelProvider'],
            'reasoningEffort': params['config']['model_reasoning_effort'],
            'sandbox': {'type': 'workspaceWrite', 'networkAccess': False}})
    elif method == 'turn/start':
        turns += 1
        turn = str(uuid.uuid4())
        prompt = params['input'][0]['text']
        with Path(plan['record']).open('a') as record:
            record.write(json.dumps({'turn': turns, 'prompt': prompt}) + '\n')
        reply(request, {'turn': {'id': turn, 'status': 'inProgress'}})
        if turns == 1:
            context = json.JSONDecoder().raw_decode(prompt.split('TASK_CONTEXT=', 1)[1])[0]
            stage = context['staged_targets'][plan['target']]
            Path(stage).write_text('{"total":12}')
            Path(plan['writes']).write_text(stage + '\n')
            Path(plan['report']).write_text('Fictional exact failed/successful command selection; stage verified once.\n')
            for index, command in enumerate(commands):
                item = {'type': 'commandExecution', 'id': 'tool-' + str(index), 'status': 'completed',
                    'exitCode': 2 if index < 2 else 0, 'durationMs': 1, 'command': command,
                    'aggregatedOutput': 'THIS OUTPUT MUST NEVER BE CAPTURED'}
                if plan.get('incomplete_tool') and index == 3:
                    item['exitCode'] = None
                send({'method': 'item/completed', 'params': {'threadId': thread, 'turnId': turn, 'item': item}})
            if plan.get('hang_first'):
                continue
            text = json.dumps({'payload_json': json.dumps(answer())})
            if plan.get('conflict'):
                final('{invalid fictional JSON', 'invalid-first')
            item = {'type': 'agentMessage', 'phase': 'final_answer', 'id': 'first', 'text': text}
            if not plan.get('aggregate_only'):
                final(text, 'first', str(uuid.uuid4()) if plan.get('foreign_final') else None)
            complete([item] if plan.get('aggregate_only') else [])
        else:
            # Assert actual feedback, exact completed command fingerprints and
            # the one-turn contract. A setup failure cannot masquerade as PASS.
            assert turns == 2 and 'INNER TASK RESULT:' in prompt
            raw = prompt.split('OBSERVED_TOOL_METADATA=', 1)[1]
            rows = json.JSONDecoder().raw_decode(raw)[0]
            assert len(rows) == 4
            for index, row in enumerate(rows):
                assert row['id'] == 'tool-' + str(index)
                assert row['thread'] == thread and row['completed_notification']
                assert row['command_sha256'] == hashlib.sha256(commands[index].encode()).hexdigest()
                assert row['command_bytes'] == len(commands[index].encode())
                assert 'command' not in row and 'aggregatedOutput' not in row
            text = json.dumps({'payload_json': json.dumps(answer(True))})
            final(text, 'clarified')
            if plan.get('second_conflict'):
                final('{second fictional conflict', 'second-conflict')
            complete()
    elif method == 'thread/read':
        if plan.get('late_on_read'):
            final(json.dumps({'payload_json': json.dumps(answer(True))}), 'late-original')
        reply(request, {'thread': {'id': thread, 'status': {'type': plan.get('read_status', 'idle')}}})
    elif method == 'turn/interrupt':
        reply(request, {})
        complete(status='interrupted')
    elif method == 'thread/unsubscribe':
        reply(request, {'status': 'unsubscribed'})

sys.exit(0)
