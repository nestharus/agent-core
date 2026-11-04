"""Synthetic fixture identities, grants and results. Never points at a live board."""

import copy
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coordinator_runtime.contracts import LUNA, SOL, digest, ident, validate_config
from coordinator_runtime.store import Store


def config_at(directory):
    home = Path(directory)
    pool_routes = home / 'pool-routes.toml'
    pool_routes.write_text('[rotation]\nstate_dir = '+json.dumps(str(home/'pool-state'))+
        '\n[providers.codex]\npool = [".codex2", ".codex3", ".codex5"]\n'+
        'manual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n')
    template = home / "fixture-template.md"
    template.write_text("Perform the bounded actual role task; retain failures/UNKNOWNs. No descendants.\n")
    roles = {r: {"owner": ident(), "profile": ".codex5" if r in {"Branch", "QA"} else ".codex",
                 "board_id": ident(), "board_role": r.lower(), "legacy_hold": "actual prior owner unresolved",
                 "routes": [], "package_admission_required": True} for r in ("Work", "Branch", "Reviews", "QA")}
    tasks = {}
    for role in roles:
        phases = ["execution", "cleanup"] if role == "QA" else ["proposer", "integrator"]
        for phase in phases:
            name = f"{role.lower()}-{phase}"
            roles[role]["routes"].append(name)
            tasks[name] = {"role": role, "phase": phase, "profile": roles[role]["profile"], "binding": copy.deepcopy(SOL),
                           "cwd": str(home), "sandbox": "read-only", "effects": "none", "templates": [str(template)],
                           "purpose": "Conserve actual bounded role responsibility and meaning.",
                           "authority": "Synthetic fixture only; read inputs, no external effects.", "responses": {}}
            tasks[name]["effect_authority"] = {"owner": roles[role]["owner"], "operations": ["read-reports"],
                                               "read_roots": [str(home)], "write_roots": []}
    tasks["work-proposer"]["responses"]["proposal"] = ["work-integrator"]
    tasks["branch-proposer"]["responses"]["proposal"] = ["branch-integrator"]
    tasks["reviews-proposer"]["responses"]["proposal"] = ["reviews-integrator"]
    tasks["reviews-integrator"]["responses"]["consolidated"] = ["work-proposer"]
    tasks["qa-execution"]["responses"]["consolidated"] = ["qa-cleanup"]
    tasks["qa-cleanup"]["responses"]["qualification"] = ["branch-proposer"]
    for task in tasks.values():
        task["responses"].update({"blocker": ["work-proposer"], "scope": ["work-proposer"]})
    value = {"version": 1, "enabled": False, "actor": ident(), "state_dir": str(home / "state"),
             "execution_pool_routes": str(pool_routes),
             "canonical_publication": {"method":"retention-same-inode-v1","library":str(Path(__file__).parent.resolve()/"fixture_snapshot")},
             "board_home": str(home / "boards"), "board_library": os.environ.get("COORDINATOR_TEST_BOARD_LIBRARY", str(Path(__file__).resolve().parents[2] / "message-board")),
             "profiles": [".codex", ".codex2", ".codex3", ".codex4", ".codex5"],
             "roles": roles, "tasks": tasks, "classifier": {"binding": copy.deepcopy(LUNA), "profile": ".codex2", "cwd": str(home)},
             "diagnosis": {"binding": copy.deepcopy(LUNA), "profile": ".codex4", "cwd": str(home)},
             "protocol_cli_version": "codex-cli 0.166.0", "limits": {"max_events": 10000, "max_jobs": 10000,
                 "max_attempts": 30000, "max_alerts": 10000, "max_bytes": 100000000, "max_result_bytes": 65536, "max_files": 50000},
             "deadlines": {"classify": 2, "task": 2, "ack": 30, "backlog": 60, "bind": 10,
                           "interrupt": 1, "shutdown": 1, "alert_interval": 1}, "recheck_seconds": 0.01}
    return validate_config(value)


def enrolled(config, clock=None, reconcile=True):
    store = Store(config, **({"clock": clock} if clock else {}))
    for role, selected in config["roles"].items():
        store.enroll(role, {"owner": selected["owner"], "actor": config["actor"], "id": ident(), "cutover": 0})
        if reconcile:
            store.reconcile_legacy(role, selected["owner"], {"collector": "fixture prior collector", "evidence": ["fixture closed"], "remaining_holds": []})
    return store


def event(config, name="one", role="Work", task=None, package=None):
    return {"id": digest({"name": name, "role": role}), "role": role, "recipient": config["roles"][role]["owner"],
            "author": ident(), "body": "Unchanged actionable finding", "kind": "response", "notice": None,
            "board_id": None, "grant": None, "package": package,
            "allowed_tasks": [task or f"{role.lower()}-integrator"]}


def result(semantic="DONE", category="complete", summary="Owned fixture result"):
    return {"semantic": semantic, "category": category, "summary": summary,
            "findings": [{"source": "fixture", "meaning": "Preserve this actionable finding"}],
            "failures": [] if semantic == "DONE" else [{"source": "fixture", "error": "explicit failure"}],
            "unknowns": [], "artifacts": []}


def collect(store, attempt, answer, code=0, error=None, capture="complete", **details):
    store.begin(attempt, {"fixture": True})
    store.session(attempt, ident())
    outcome = {"result": answer, "exit": code, "capture": capture, "cleanup": "done", "error": error,
               "detail": {"resume_disposition": "unavailable-after-ephemeral-owner-exit", **details}}
    store.collect(attempt, outcome)
    return outcome


def queued(store, message, answer=None):
    store.ingest(message)
    while True:
        attempt, actual = store.claim_classification()
        selected = answer if actual["id"] == message["id"] and answer else {
            "event_id": actual["id"], "task": actual["allowed_tasks"][0],
            "package": actual["package"], "reason": "fixture meaning selects this authorized role"}
        collect(store, attempt, selected)
        store.commit_classification(attempt)
        store.ack_state(actual["id"], "internal")
        if actual["id"] == message["id"]:
            return attempt


def ended_job(store, job, answer=None, code=0):
    attempt = store.start_job(job["id"], job["token"])
    collect(store, attempt, answer or result(), code)
    store.finish_job(job["id"], job["token"])
    return attempt
