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


def original_answer(ready=False):
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


original = None
observed = []

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def answer(ready=False):
    global original
    if not ready:
        original=original_answer()
        return original
    import copy
    value=copy.deepcopy(original)
    if plan.get('unresolved'):return value
    value.update(semantic='DONE',category='complete')
    proof=value['completion'];proof['local']='ready'
    fields={'id','thread','turn','command_sha256','command_bytes','exit_code','status'}
    def bound(index):return {k:observed[index][k] for k in fields}
    manifest={'version':1,'resolutions':[]}
    def link(row,subject,ids):
        row.update(command_bindings=[bound(i) for i in ids],
            causal_reason='These exact corrected document reads verify the retained local documentation/protocol duty; stages were not replayed.')
        manifest['resolutions'].append({'subject':subject,'command_bindings':row['command_bindings'],
            'verification_items':row['verification_items'],'causal_reason':row['causal_reason']})
        row['causal_evidence']={'path':plan['report'],'entry':len(manifest['resolutions'])-1}
    proof['failures']=[];proof['tools']=[]
    for i in range(2):
        failure={'index':i,'status':'resolved','verification_items':['tool-'+str(i+2)]}
        link(failure,{'kind':'failure','index':i,'original_hash':digest(value['failures'][i])},[i,i+2])
        proof['failures'].append(failure)
        tool={'id':'tool-'+str(i),'status':'resolved','reason':'Exact failed read and its corrected read retained.',
            'verification_items':['tool-'+str(i+2)]}
        link(tool,{'kind':'tool','id':tool['id']},[i,i+2]);proof['tools'].append(tool)
    if value['unknowns']:
        prior={k:v for k,v in original['completion']['unknowns'][0].items() if k!='index'}
        duty={**prior,'index':0,'status':'resolved','prior_disposition':prior,
            'verification_items':['tool-2','tool-3']}
        link(duty,{'kind':'unknown','index':0,'original_hash':digest(value['unknowns'][0]),'prior_disposition':prior},[0,1,2,3])
        proof['unknowns']=[duty]
    Path(plan['report']).write_text(json.dumps(manifest))
    ref={'path':plan['report'],'sha256':hashlib.sha256(Path(plan['report']).read_bytes()).hexdigest()}
    for row in proof['failures']+proof['tools']+proof['unknowns']:
        row['evidence']=[ref];row['causal_evidence']['sha256']=ref['sha256']
    if plan.get('unrelated'):
        proof['tools'][0]['verification_items']=['tool-3']
        proof['tools'][0]['command_bindings']=[bound(0),bound(3)]
    if plan.get('erased_unknown'):value['unknowns']=[];proof['unknowns']=[]
    if plan.get('changed_owner'):proof['unknowns'][0]['owner']='controller'
    return value


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
            for stage_path in context['staged_targets'].values():
                Path(stage_path).write_text('{"total":12}')
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
            observed = rows
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
            if plan.get('late_current'):final(json.dumps({'payload_json':json.dumps(answer(True))}), 'late-current')
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
