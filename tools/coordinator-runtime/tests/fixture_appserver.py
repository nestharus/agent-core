"""Real owned fixture process, fake model. Implements only the tested protocol."""

import json
import os
from pathlib import Path
import sys
import time
import uuid

plan = json.loads(Path(sys.argv[1]).read_text())
thread, turn, turns = str(uuid.uuid4()), None, 0


def send(value):
    print(json.dumps(value), flush=True)


def respond(request, value):
    send({"id": request["id"], "result": value})


def completed(status="completed"):
    send({"method": "turn/completed", "params": {"threadId": thread,
        "turn": {"id": turn, "status": status, "items": [], "error": None}}})


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
        turn, turns = str(uuid.uuid4()), turns+1
        respond(request, {"turn": {"id": turn, "status": "inProgress"}})
        if plan.get("hang_first") and turns == 1:
            continue
        answer = plan.get("result")
        if plan.get("write_file"):
            path = Path.cwd() / plan["write_file"]
            path.write_text("conserved actionable fixture report\n")
            answer = {**answer, "artifacts": [{"path": str(path), "meaning": "exact owned report"}]}
        text = plan.get("raw_final") or json.dumps(answer)
        send({"method": "item/completed", "params": {"threadId": thread, "turnId": turn,
            "item": {"type": "agentMessage", "id": str(uuid.uuid4()), "phase": "final_answer", "text": text}}})
        completed()
    elif method == "turn/interrupt":
        respond(request, {})
        completed("interrupted")
    elif method == "thread/read":
        respond(request, {"thread": {"id": thread, "status": {"type": "idle"}}})
    elif method == "thread/unsubscribe":
        respond(request, {"status": "unsubscribed"})

time.sleep(plan.get("exit_delay", 0))
sys.exit(plan.get("exit", 0))
