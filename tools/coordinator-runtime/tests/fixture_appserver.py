"""Real owned fixture process, fake model. Implements only the tested protocol."""

import json
import os
from pathlib import Path
import sys
import time
import uuid
import hashlib

plan = json.loads(Path(sys.argv[1]).read_text())
thread, turn, turns = str(uuid.uuid4()), None, 0
task_context = {}
tool_records=[]


def send(value):
    print(json.dumps(value), flush=True)


def respond(request, value):
    send({"id": request["id"], "result": value})


def completed(status="completed", error=None):
    send({"method": "turn/completed", "params": {"threadId": thread,
        "turn": {"id": turn, "status": status, "items": [], "error": error}}})


for line in sys.stdin:
    request = json.loads(line)
    method, params = request.get("method"), request.get("params", {})
    if method == "initialize":
        respond(request, {"codexHome": os.environ["CODEX_HOME"]})
    elif method == "thread/start":
        if plan.get("capacity"):
            send({"id": request["id"], "error": {"code": -32000, "message": "model capacity exhausted"}})
            continue
        respond(request, {"thread": {"id": thread, "sessionId": thread, "ephemeral": plan.get("ephemeral", True), "path": None},
            "model": plan.get("model", params["model"]), "modelProvider": params["modelProvider"],
            "reasoningEffort": params["config"]["model_reasoning_effort"],
            "sandbox": {"type": "readOnly" if params["sandbox"] == "read-only" else "workspaceWrite", "networkAccess": False}})
    elif method == "turn/start":
        prompt=params['input'][0]['text']
        if 'TASK_CONTEXT=' in prompt:
            task_context=json.JSONDecoder().raw_decode(prompt.split('TASK_CONTEXT=',1)[1])[0]
        turn, turns = str(uuid.uuid4()), turns+1
        respond(request, {"turn": {"id": turn, "status": "inProgress"}})
        if plan.get("turn_error"):
            send({"method": "error", "params": {"error": plan["turn_error"]}})
            completed("failed", plan["turn_error"])
            continue
        if plan.get("hang_first") and turns == 1:
            continue
        answer = plan.get("result")
        write_stage=turns==1 or not str(plan.get('completion_mode','')).startswith('legacy')
        if plan.get('target') and write_stage:
            target=task_context.get('staged_targets',{}).get(plan['target'],plan['target'])
            Path(target).write_text(json.dumps(plan.get('target_contents',{'total':12})))
            if plan.get('probe_record'):
                Path(plan['probe_record']).write_text(json.dumps({'actual_write_path':target,'canonical_before_publication':json.loads(Path(plan['target']).read_text())}))
        if plan.get('additional_target') and write_stage:
            extra=task_context['staged_targets'][plan['additional_target']]
            Path(extra).write_text(json.dumps(plan['additional_contents']))
        if plan.get('tool_metadata'):
            meta = {'type':'commandExecution','id':str(uuid.uuid4()),'status':'completed',
                    'command':'private command body NOT to retain','aggregatedOutput':'private output NOT to retain',
                    'processId':'provider-label-only','durationMs':2,**plan['tool_metadata']}
            if plan.get('completion_mode')=='legacy-resolved' and turns>1:meta.update(exitCode=0,status='completed')
            send({'method':'item/completed','params':{'threadId':thread,'turnId':turn,'item':meta}})
            tool_records.append(meta)
        if plan.get("write_file"):
            path = Path.cwd() / plan["write_file"]
            path.write_text("conserved actionable fixture report\n")
            answer = {**answer, "artifacts": [str(path)] if plan.get('artifact_strings') else [{"path": str(path), "meaning": "exact owned report"}]}
        mode=plan.get('completion_mode')
        if isinstance(answer,dict) and answer.get('semantic')=='DONE' and mode:
            if mode=='auto' and not answer.get('failures') and not answer.get('unknowns'):
                answer={**answer,'completion':{'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[]}}
            elif mode.startswith('legacy') and turns>1:
                proof={'version':1,'local':'ready','failures':[],'unknowns':[], 'tools':[]}
                if mode=='legacy-deferred':
                    proof['unknowns']=[{'index':i,'status':'deferred','owner':'controller','duty':'publication','reason':'Expected subsequent controller publication; local staged construction is verified.'} for i in range(len(answer['unknowns']))]
                if mode=='legacy-resolved':
                    report=Path.cwd()/'resolution.json';report.write_text('{"report_repaired":true,"local_validation":"passed"}')
                    ref={'path':str(report),'sha256':hashlib.sha256(report.read_bytes()).hexdigest()}
                    if plan.get('bad_resolution_hash'):ref['sha256']='0'*64
                    check=next(r['id'] for r in reversed(tool_records) if r.get('exitCode')==0)
                    if plan.get('bad_verification_item'):check='not-an-observed-verification'
                    proof['failures']=[{'index':i,'status':'resolved','evidence':[ref],'verification_items':[check]} for i in range(len(answer['failures']))]
                    proof['tools']=[{'id':r['id'],'status':'resolved','reason':'Report mismatch repaired; exact own report and selected verification item bind the producer claim.', 'evidence':[ref],'verification_items':[check]} for r in tool_records if r.get('exitCode') not in {None,0} or r['status']=='failed']
                    answer={**answer,'artifacts':[*answer.get('artifacts',[]),str(report)]}
                if plan.get('erase_history'):answer={**answer,'failures':[],'unknowns':[]};proof.update(failures=[],unknowns=[])
                answer={**answer,'completion':proof}
        if set(params.get("outputSchema", {}).get("properties", {})) == {"payload_json"}:
            answer = {"payload_json": json.dumps(answer)}
        text = plan.get("raw_final") or json.dumps(answer)
        send({"method": "item/completed", "params": {"threadId": thread, "turnId": turn,
            "item": {"type": "agentMessage", "id": str(uuid.uuid4()), "phase": "final_answer", "text": text}}})
        completed()
    elif method == "turn/interrupt":
        respond(request, {})
        completed("interrupted")
    elif method == "thread/read":
        respond(request, {"thread": {"id": thread, "status": {"type": plan.get("read_status", "idle")}}})
    elif method == 'config/read':
        config=plan.get('storage_config',{})
        respond(request,{'config':config,'origins':{}})
    elif method == "thread/unsubscribe":
        if plan.get("unsubscribe_error"):
            send({"id": request["id"], "error": {"code": -32000, "message": "synthetic unsubscribe failure"}})
            continue
        if plan.get("late_result"):
            send({"method": "item/completed", "params": {"threadId": thread, "turnId": turn,
                "item": {"type": "agentMessage", "id": str(uuid.uuid4()), "phase": "final_answer", "text": json.dumps(plan["late_result"])}}})
        respond(request, {"status": "unsubscribed"})

time.sleep(plan.get("exit_delay", 0))
sys.exit(plan.get("exit", 0))
