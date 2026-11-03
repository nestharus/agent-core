"""Validated configuration and model output boundaries (roles: parser, validator)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import uuid

ROLES = {"Work", "Branch", "Reviews", "QA"}
PROFILES = {".codex", ".codex2", ".codex3", ".codex4", ".codex5"}
PHASES = {"proposer", "integrator", "execution", "cleanup"}
OPERATIONS = {"read-source", "read-reports", "write-role-records", "write-owned-artifacts",
              "prepare-intents", "organize-authorized-refs", "execute-admitted-qa", "consolidate-reports"}
LUNA = {"model": "gpt-6-luna", "effort": "low", "provider": "openai"}
SOL = {"model": "gpt-6.1-sol", "effort": "xhigh", "provider": "openai"}


class Refusal(RuntimeError):
    """Preserve responsibility and return a concrete unavailable boundary."""


class Backpressure(Refusal):
    """No held work may be discarded to make room."""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal("conflicting duplicate JSON key")
        result[key] = value
    return result


def invalid_constant(value):
    raise Refusal("non-JSON numeric constant refused")


def parse_json(value):
    return json.loads(value, object_pairs_hook=unique_object, parse_constant=invalid_constant)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def ident():
    return str(uuid.uuid4())


def canonical_uuid(value):
    if not isinstance(value, str):
        raise Refusal("identity must be a canonical UUID")
    try:
        parsed = str(uuid.UUID(value))
    except ValueError as exc:
        raise Refusal("identity must be a canonical UUID") from exc
    if parsed != value:
        raise Refusal("identity must be a canonical UUID")
    return value


def required_text(value, label, maximum=16000):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > maximum:
        raise Refusal(f"{label}: nonempty bounded text required")
    return value


def regular_path(value):
    path = Path(value)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise Refusal("absolute regular source file required")
    if any(parent.is_symlink() for parent in path.parents):
        raise Refusal("symlink ancestor refused")
    return path


def model_binding(value):
    if not isinstance(value, dict) or set(value) != {"model", "effort", "provider"}:
        raise Refusal("explicit model/effort/provider binding required")
    required_text(value["model"], "model", 128)
    if value["effort"] not in {"low", "medium", "high", "xhigh"}:
        raise Refusal("unsupported effort")
    required_text(value["provider"], "provider", 128)
    return value


def load_config(path):
    return validate_config(parse_json(regular_path(path).read_text()))


def validate_config(config):
    if config.get("version") != 1:
        raise Refusal("configuration version 1 required")
    canonical_uuid(config["actor"])
    if not config.get("roles") or set(config["roles"]) - ROLES:
        raise Refusal("only explicitly selected Work/Branch/Reviews/QA roles are supported")
    if not Path(config["state_dir"]).is_absolute():
        raise Refusal("absolute state_dir required")
    if config["classifier"]["binding"] != LUNA or config["diagnosis"]["binding"] != LUNA:
        raise Refusal("classification and diagnosis require fresh gpt-6-luna low")
    profiles = config["profiles"]
    if not profiles or set(profiles) - PROFILES or len(profiles) != len(set(profiles)):
        raise Refusal("select existing authorized profile names explicitly")
    for kind in ("classifier", "diagnosis"):
        if config[kind]["profile"] not in profiles or not Path(config[kind]["cwd"]).is_absolute():
            raise Refusal("classification/diagnosis require an authorized account and absolute cwd")
    if type(config.get("classification_capacity", 5)) is not int or not 1 <= config.get("classification_capacity", 5) <= 32:
        raise Refusal("classification capacity must be a bounded positive integer")
    excluded = [Path.home()/p for p in PROFILES]
    if any(Path(config["state_dir"]).is_relative_to(p) or p.is_relative_to(Path(config["state_dir"])) for p in excluded):
        raise Refusal("runtime state cannot be inside or encompass profile/session stores")
    for role, selected in config["roles"].items():
        validate_role(role, selected, profiles)
    for name, task in config["tasks"].items():
        validate_task(name, task, config)
        if task.get('routine_completion'):
            from .routine import policy_for
            policy_for(task)
    if config.get('session_storage',{}).get('mode') not in {None,'owned-attempt'}:
        raise Refusal('only exact owned-attempt auxiliary storage is supported')
    for selected in config["roles"].values():
        if set(selected["routes"]) - set(config["tasks"]):
            raise Refusal("role route references an unknown configured task")
    recipients = config.get("delivery", {}).get("recipients", {})
    for name, recipient in recipients.items():
        if name not in ROLES | {"Root"}:
            raise Refusal("delivery selects only the four roles and external Root")
        canonical_uuid(recipient["session"])
        required_text(recipient["board_role"], "recipient board role", 128)
        if recipient.get("profile") not in PROFILES:
            raise Refusal("recipient retains its actual selected account")
        if name in config["roles"] and recipient["session"] != config["roles"][name]["owner"]:
            raise Refusal("delivery cannot substitute a selected role owner")
    for task in config["tasks"].values():
        if set(task.get("allowed_handoffs", [])) - set(recipients):
            raise Refusal("task handoffs exceed selected recipients")
        if task.get("require_package_scope") and not task.get("scope_roots"):
            raise Refusal("package effects need explicit admitted scope roots")
    for key in ("max_events", "max_attempts", "max_jobs", "max_bytes", "max_alerts", "max_result_bytes"):
        if type(config["limits"].get(key)) is not int or config["limits"][key] <= 0:
            raise Refusal(f"positive cumulative limit required: {key}")
    if type(config["limits"].get("max_owner_corrections", 4)) is not int or not 1 <= config["limits"].get("max_owner_corrections", 4) <= 8:
        raise Refusal("owner corrections require a bounded per-delivery budget from 1 through 8")
    for key in ("classify", "task", "ack", "backlog", "bind", "interrupt", "shutdown", "alert_interval"):
        if not isinstance(config["deadlines"].get(key), (int, float)) or config["deadlines"][key] <= 0:
            raise Refusal(f"positive deadline required: {key}")
    return config


def validate_role(role, selected, profiles):
    canonical_uuid(selected["owner"])
    if selected["profile"] not in profiles:
        raise Refusal("role owner profile is outside selected accounts")
    canonical_uuid(selected["board_id"])
    required_text(selected["board_role"], "actual board role", 128)
    if not selected.get("legacy_hold"):
        raise Refusal("initial configuration must retain an explicit legacy hold")
    if not isinstance(selected.get("routes"), list) or not selected["routes"]:
        raise Refusal("role must explicitly allow typed task IDs")
    if role == "QA" and not selected.get("package_admission_required", False):
        raise Refusal("QA retains per-package admission from its actual resource owner")


def validate_task(name, task, config):
    required_text(name, "task ID", 80)
    role, phase = task["role"], task["phase"]
    if role not in config["roles"] or phase not in PHASES:
        raise Refusal("task role/phase outside enrollment")
    if (role == "QA") != (phase in {"execution", "cleanup"}):
        raise Refusal("QA uses execution/cleanup; other roles use proposer/integrator")
    owner_execution = task.get("execution") == "owner"
    if owner_execution and (role != "Reviews" or phase != "proposer" or task["binding"] != {"model": "gpt-xhigh", "provider": "opaque", "effort": "opaque"}):
        raise Refusal("owner execution retains the current selected opaque Reviews binding; no substitute model")
    binding = task["binding"] if owner_execution else model_binding(task["binding"])
    if (phase in {"integrator", "cleanup"} or role == "Work") and binding != SOL:
        raise Refusal("Work and integrators require explicit gpt-6.1-sol xhigh")
    if task["profile"] not in config["profiles"]:
        raise Refusal("task profile outside authorized accounts")
    if name not in config["roles"][role]["routes"]:
        raise Refusal("task not allowlisted for role")
    if task.get("effects") not in {"none", "owned-artifacts", "owner-reconcile"}:
        raise Refusal("effect authority must be none, owned-artifacts or explicit owner-reconcile")
    if task.get("sandbox") not in {"read-only", "workspace-write"}:
        raise Refusal("bounded sandbox required")
    if task["effects"] == "none" and task["sandbox"] != "read-only":
        raise Refusal("automatic no-effect closure requires read-only sandbox")
    if not Path(task["cwd"]).is_absolute():
        raise Refusal("absolute task workspace required")
    if not task.get("templates") or not all(Path(p).is_absolute() for p in task["templates"]):
        raise Refusal("explicit absolute method/task templates required")
    required_text(task.get("authority"), "task effect/access authority")
    authority = task.get("effect_authority", {})
    if authority.get("owner") != config["roles"][role]["owner"]:
        raise Refusal("typed effect authority must retain the actual role owner")
    operations = authority.get("operations", [])
    if not operations or set(operations) - OPERATIONS:
        raise Refusal("effect operations must be explicitly selected from the typed allowlist")
    if not all(Path(p).is_absolute() for p in authority.get("write_roots", []) + authority.get("read_roots", [])):
        raise Refusal("explicit absolute effect/access roots required")
    if task["effects"] == "none" and set(operations) - {"read-source", "read-reports", "prepare-intents", "consolidate-reports"}:
        raise Refusal("read-only tasks cannot acquire mutation authority")
    if task["effects"] == "owned-artifacts" and (authority.get("write_roots") or task["sandbox"] != "workspace-write"):
        raise Refusal("owned-artifacts uses only the runtime's exact fresh attempt directory")
    if task["effects"] == "owned-artifacts" and set(operations) - {"read-source", "read-reports", "prepare-intents", "consolidate-reports", "write-owned-artifacts"}:
        raise Refusal("owned-artifacts cannot acquire canonical/external effects")
    if "execute-admitted-qa" in operations and role != "QA":
        raise Refusal("QA execution stays with its selected actual owner")
    if "organize-authorized-refs" in operations and role != "Branch":
        raise Refusal("Branch organization authority cannot be selected for another role")
    if type(task.get("network", False)) is not bool:
        raise Refusal("network access must be explicitly boolean")
    if task.get("network", False) and task["effects"] in {"none", "owned-artifacts"}:
        raise Refusal("automatic no-effect tasks cannot acquire external network effects")
    if type(task.get("capacity", 1)) is not int or not 1 <= task.get("capacity", 1) <= 5:
        raise Refusal("bounded proposer capacity required")


def scoped_task(name, task, admission):
    """Branch's actual per-package admission narrows configured effect roots.

    Nothing in message text becomes launcher argv or authority. The existing
    resource owner records the exact execution scope using admit-package.
    """
    if not task.get("require_package_scope"):
        return task
    receipt = parse_json(admission["receipt"]) if admission else {}
    scope = receipt.get("task_scopes", {}).get(name)
    if not isinstance(scope, dict) or not scope.get("procedure") or not scope.get("resource_evidence"):
        raise Refusal("actual package procedure, resource-owner evidence and task scope are missing")
    roots = scope.get("write_roots", []) + scope.get("read_roots", []) + [scope.get("cwd", "")]
    allowed = [Path(p) for p in task["scope_roots"]]
    private = [Path.home()/p for p in PROFILES]
    for value in roots:
        path = Path(value)
        if (not path.is_absolute() or not any(path.is_relative_to(root) for root in allowed)
                or any(path.is_relative_to(p) or p.is_relative_to(path) for p in private)
                or any(p.is_symlink() for p in (path, *path.parents)) or ".." in path.parts):
            raise Refusal("package scope escapes selected roots or crosses a symlink/private boundary")
    network = scope.get("network", False)
    if type(network) is not bool or (network and not task.get("network", False)):
        raise Refusal("admission cannot expand selected network authority")
    authority = {**task["effect_authority"], "read_roots": scope.get("read_roots", []), "write_roots": scope.get("write_roots", [])}
    return {**task, "cwd": scope["cwd"], "network": network, "effect_authority": authority, "admitted_scope": scope}


def classification(answer, event, config):
    if not isinstance(answer, dict) or set(answer) != {"event_id", "task", "package", "reason"}:
        raise Refusal("complete classification object required")
    if answer["event_id"] != event["id"]:
        raise Refusal("classification is for a different event")
    if event["kind"] == "outgoing-response" and answer["task"] == "@delivery":
        if answer["package"] != event.get("package") or not event.get("delivery_plan"):
            raise Refusal("outgoing response must retain its bound package and admitted delivery plan")
        required_text(answer["reason"], "response classification reason", 4000)
        return answer
    task = config["tasks"].get(answer["task"])
    if task is None:
        raise Refusal("message-selected task is not allowlisted")
    allowed = event.get("allowed_tasks")
    if not isinstance(allowed, list) or answer["task"] not in allowed:
        raise Refusal("classification exceeds event's typed routing authority")
    required_text(answer["reason"], "classification rationale", 4000)
    if task["role"] == "QA" or task.get("require_package_scope"):
        required_text(answer["package"], "QA package", 128)
    if answer["package"] != event.get("package"):
        raise Refusal("classifier cannot invent or change a package identity")
    return answer


def task_result(answer):
    keys = {"semantic", "summary", "findings", "failures", "unknowns", "artifacts", "category"}
    if not isinstance(answer, dict) or not keys <= set(answer) or set(answer)-keys-{"handoffs", "no_handoff_reason"}:
        raise Refusal("task result must conserve summary/findings/failures/unknowns/artifacts/category")
    if answer["semantic"] not in {"DONE", "PARTIAL", "FAILED", "UNKNOWN"}:
        raise Refusal("unknown semantic completion")
    required_text(answer["summary"], "summary")
    for key in ("findings", "failures", "unknowns", "artifacts"):
        if not isinstance(answer[key], list):
            raise Refusal(f"{key} must be an explicit list, including honest empties")
    if answer["category"] not in {"proposal", "consolidated", "qualification", "scope", "blocker", "complete"}:
        raise Refusal("typed response category required")
    if answer["semantic"] != "DONE" and not (answer["failures"] or answer["unknowns"]):
        raise Refusal("partial/failed/unknown work must retain its unresolved meaning")
    if "handoffs" in answer and not isinstance(answer["handoffs"], list):
        raise Refusal("handoffs must be an explicit bounded list")
    if len(answer.get("handoffs", [])) > 16:
        raise Refusal("handoff count exceeds admitted per-task bound")
    return answer


def response_tasks(task, result, config):
    """Destination authority is static configuration, never a command from a message."""
    key = result["category"]
    choices = task.get("responses", {}).get(key, [])
    if key in {"scope", "blocker"}:
        choices = [n for n in choices if config["tasks"][n]["role"] == "Work"]
    if task["role"] == "Reviews" and task["phase"] == "integrator":
        choices = [n for n in choices if config["tasks"][n]["role"] == "Work"]
    if task["role"] == "QA" and task["phase"] == "cleanup" and key == "qualification":
        choices = [n for n in choices if config["tasks"][n]["role"] == "Branch"]
    if set(choices) - set(config["tasks"]):
        raise Refusal("response route references an unknown typed task")
    return choices
