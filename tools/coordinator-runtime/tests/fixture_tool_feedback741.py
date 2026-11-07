"""Owned synthetic provider transport. Command strings are data, never executed."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

plan = json.loads(Path(sys.argv[1]).read_text())
thread = str(uuid.uuid4())
round_number = 0
turn = None
commands = {}
failure_indexes, external_failure_indexes = {}, []
failures, unknowns, resolutions, artifacts = [], [], [], []
prior = None


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def send(value):
    print(encode(value), flush=True)


def reply(request, value):
    send({'id': request['id'], 'result': value})


def emit_debt():
    index = len(commands)
    # These full completion wrappers deliberately differ from native labels and
    # preserve newlines, quoting and non-ASCII UTF-8 bytes.
    pair = ["/bin/bash -lc 'read_or_verify_" + str(index) + " typo λ\n'",
            "/bin/bash -lc 'read_or_verify_" + str(index) + " corrected λ\n'"]
    if index == 0:
        pair = ["/bin/bash -lc 'python3 verify_stages.py λ\n'"] * 2
    commands[index] = pair
    failure_indexes[index] = None
    if index == 0:
        failure_indexes[index] = len(failures)
        failures.append({'kind': 'verifier', 'meaning': 'Retained original nonzero ' + str(index)})
    # A new linkage-only debt is an explicit local metadata unknown. Its actual
    # adverse protocol item remains captured; no unresolved failure is renamed.
    unknowns.append({'kind': 'current-tool-linkage', 'meaning': 'Exact completion linkage missing ' + str(index)})
    for command, code in zip(pair, [2, 0]):
        send({'method': 'item/completed', 'params': {'threadId': thread, 'turnId': turn,
            'item': {'type': 'commandExecution', 'id': str(uuid.uuid4()), 'status': 'failed' if code else 'completed',
                     'exitCode': code, 'durationMs': 1, 'command': command,
                     'aggregatedOutput': 'FORBIDDEN_STDOUT_741'}}})


def unresolved(index):
    return {'index': index, 'status': 'unresolved', 'owner': 'producer',
            'duty': 'observed-tool-metadata', 'reason': 'Exact current command linkage ' + str(index) + ' is unavailable.'}


def parse_feedback(prompt):
    metadata = json.JSONDecoder().raw_decode(prompt.split('OBSERVED_TOOL_METADATA=', 1)[1])[0]
    inputs = json.JSONDecoder().raw_decode(prompt.split('OBSERVED_COMMAND_INPUTS=', 1)[1])[0]
    assert 'FORBIDDEN_STDOUT_741' not in prompt
    assert {r['id'] for r in metadata} == {r['id'] for r in inputs}
    by_command = {}
    for row in inputs:
        assert row['availability'] == 'exact'
        assert row['thread'] == thread
        assert hashlib.sha256(row['command'].encode()).hexdigest() == row['command_sha256']
        assert len(row['command'].encode()) == row['command_bytes']
        observed = next(r for r in metadata if r['id'] == row['id'])
        assert all(row[k] == observed[k] for k in ('id','thread','turn','command_sha256','command_bytes','exit_code','status'))
        by_command[(row['command'],row['exit_code'])] = row
    return by_command


def answer(prompt):
    global prior
    if round_number == 1:
        context = json.JSONDecoder().raw_decode(prompt.split('TASK_CONTEXT=', 1)[1])[0]
        stage = context['staged_targets'][plan['target']]
        Path(stage).write_text('{"total":12}')
        Path(plan['writes']).write_text(stage + '\n')
        emit_debt()
    else:
        inputs = parse_feedback(prompt)
        if plan.get('no_progress'):
            return prior
        index = len(resolutions)
        pair = [inputs[(c,code)] for c,code in zip(commands[index],[2,0])]
        fields = ('id','thread','turn','command_sha256','command_bytes','exit_code','status')
        bindings = [{k: r[k] for k in fields} for r in pair]
        if plan.get('altered'):
            bindings[1]['command_sha256'] = '0' * 64
        if plan.get('guessed'):
            bindings[1]['id'] = 'visible-label-is-not-a-protocol-id'
        checks = [pair[1]['id']]
        reason = 'Corrected the exact verifier/read typo; selected own verification proves that concrete correction.'
        failure_index = failure_indexes[index]
        subjects = ([{'kind':'failure','index':failure_index,'original_hash':digest(failures[failure_index])}]
                    if failure_index is not None else []) + [
                    {'kind':'unknown','index':index,'original_hash':digest(unknowns[index]),
                     'prior_disposition':{k:v for k,v in unresolved(index).items() if k != 'index'}},
                    {'kind':'tool','id':pair[0]['id']}]
        path = Path(plan['report']).with_name('causal-' + str(round_number) + '.json')
        path.write_text(encode({'version':1,'resolutions':[{'subject':subject,'command_bindings':bindings,
            'verification_items':checks,'causal_reason':reason} for subject in subjects]}))
        ref = {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        artifacts.append(str(path))
        common = {'evidence':[ref],'verification_items':checks,'command_bindings':bindings,'causal_reason':reason}
        rows = [None, None, None]
        for entry, subject in enumerate(subjects):
            row = {**common,'causal_evidence':{**ref,'entry':entry},'status':'resolved'}
            if subject['kind'] != 'tool':row['index'] = subject['index']
            if subject['kind'] == 'unknown':
                row.update({k:v for k,v in unresolved(index).items() if k not in {'index','status'}})
                row['prior_disposition'] = subject['prior_disposition']
            if subject['kind'] == 'tool':row.update(id=pair[0]['id'],reason=reason)
            rows[{'failure':0,'unknown':1,'tool':2}[subject['kind']]] = row
        resolutions.append(rows)
        if round_number == 2 or plan.get('endless'):
            emit_debt()
    pending = len(commands) > len(resolutions)
    external = plan.get('external') and round_number == 2
    if external:
        unknowns.append('Actual external dependency still absent.')
    if plan.get('failure_only_external') and round_number == 2:
        external_failure_indexes.append(len(failures))
        failures.append({'kind':'external-resource', 'meaning':'Actual external scope remains unavailable.'})
    partial = pending or external or bool(external_failure_indexes)
    proof = {'version':1,'local':'blocked' if partial else 'ready',
             'failures':[r[0] for r in resolutions if r[0] is not None], 'unknowns':[r[1] for r in resolutions],
             'tools':[r[2] for r in resolutions]}
    if pending:
        index = len(commands)-1
        if failure_indexes[index] is not None:
            proof['failures'].append({'index':failure_indexes[index],'status':'unresolved','evidence':[],'verification_items':[]})
        proof['unknowns'].append(unresolved(index))
    for index in external_failure_indexes:
        proof['failures'].append({'index':index,'status':'unresolved','evidence':[],'verification_items':[]})
    if external:
        proof['unknowns'].append({'index':len(unknowns)-1,'status':'unresolved','owner':'producer',
                                 'duty':'obtain-external-scope','reason':'External authority missing.'})
    value = {'semantic':'PARTIAL' if partial else 'DONE','category':'blocker' if partial else 'complete',
             'summary':'Original adverse facts and prepared stage preserved.', 'findings':[],
             'failures':list(failures),'unknowns':list(unknowns),'artifacts':list(artifacts),
             'handoffs':[],'no_handoff_reason':'Owned internal fixture.', 'completion':proof}
    if plan.get('terminal') and round_number >= 2:
        value['semantic'] = plan['terminal']
        value['category'] = 'blocker'
    prior = value
    return value


for line in sys.stdin:
    request = json.loads(line)
    method, params = request.get('method'), request.get('params',{})
    if method == 'initialize':reply(request,{'codexHome':os.environ['CODEX_HOME']})
    elif method == 'config/read':reply(request,{'config':{'history':{'persistence':'none'},'feedback':{'enabled':False},'features':{'shell_snapshot':False}},'origins':{}})
    elif method == 'thread/start':
        reply(request,{'thread':{'id':thread,'sessionId':thread,'ephemeral':True,'path':None},
                       'model':params['model'],'modelProvider':params['modelProvider'],
                       'reasoningEffort':params['config']['model_reasoning_effort'],
                       'sandbox':{'type':'workspaceWrite','networkAccess':False}})
    elif method == 'turn/start':
        round_number += 1
        turn = str(uuid.uuid4())
        prompt = params['input'][0]['text']
        # Only synthetic prompt evidence in a private fixture directory.
        with Path(plan['record']).open('a') as out:out.write(encode({'turn':round_number,'prompt':prompt})+'\n')
        reply(request,{'turn':{'id':turn,'status':'inProgress'}})
        value = answer(prompt)
        send({'method':'item/completed','params':{'threadId':thread,'turnId':turn,
            'item':{'type':'agentMessage','phase':'final_answer','id':str(uuid.uuid4()),
                    'text':encode({'payload_json':encode(value)})}}})
        send({'method':'turn/completed','params':{'threadId':thread,'turn':{'id':turn,'status':'completed','items':[]}}})
    elif method == 'thread/read':reply(request,{'thread':{'id':thread,'status':{'type':plan.get('read_status','idle')}}})
    elif method == 'thread/unsubscribe':reply(request,{'status':'unsubscribed'})
