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
    software = config.get('software_delegation')
    if software is not None:
        if (not isinstance(software, dict) or set(software) != {'grantor', 'authority', 'boundary'}
                or software['boundary'] != 'new-journal-only'):
            raise Refusal('software delegation requires explicit grantor/authority and a new journal boundary')
        canonical_uuid(software['grantor'])
        if 'Work' not in config['roles'] or software['grantor'] != config['roles']['Work']['owner']:
            raise Refusal('prospective rollout delegation retains actual Work grantor provenance')
        required_text(software['authority'], 'user/Work software delegation authority', 4000)
    for name, task in config["tasks"].items():
        validate_task(name, task, config)
        if task.get('routine_completion'):
            from .routine import policy_for
            policy_for(task)
    if config.get('session_storage',{}).get('mode') not in {None,'producer-owned'}:
        raise Refusal('select producer-owned storage; allocated Codex namespaces do not prove logical ownership')
    if any(t.get('routine_completion') for t in config['tasks'].values()):
        method=config.get('canonical_publication',{})
        if method.get('method')!='retention-same-inode-v1' or not isinstance(method.get('library'),str) or not Path(method['library']).is_absolute():
            raise Refusal('explicit selected retention.snapshot_lock library and same-inode method required')
    excluded_paths=config.get('artifact_exclusions',[])
    if not isinstance(excluded_paths,list) or len(excluded_paths)>64 or any(not isinstance(p,str) or not Path(p).is_absolute() or '..' in Path(p).parts for p in excluded_paths):
        raise Refusal('bounded absolute opaque artifact exclusions required')
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
        handoffs = task.get('software_handoffs', {})
        if not isinstance(handoffs, dict) or (handoffs and not software):
            raise Refusal('software handoffs need explicit prospective delegation')
        for role, routes in handoffs.items():
            if (role not in config['roles'] or role not in task.get('allowed_handoffs', [])
                    or not isinstance(routes, list) or not routes or len(routes) != len(set(routes))
                    or any(route not in config['roles'][role]['routes']
                           or config['tasks'][route]['role'] != role for route in routes)):
                raise Refusal('software handoff routes must name exact enrolled recipient tasks')
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
    from .inputs import input_routes, CONTROL_ROUTES
    if not isinstance(answer, dict) or set(answer) != {"event_id", "task", "package", "reason"}:
        raise Refusal("complete classification object required")
    if answer["event_id"] != event["id"]:
        raise Refusal("classification is for a different event")
    if not isinstance(answer['task'],str) or answer['task'] not in input_routes(event):
        raise Refusal("classification exceeds event's typed routing authority")
    if answer['package']!=event.get('package'):
        raise Refusal('classifier cannot invent or change a package identity')
    required_text(answer['reason'],'classification rationale',4000)
    if answer['task'] in CONTROL_ROUTES:
        if answer['task']=='@coalesce' and event.get('owner_resolution',{}).get('receipt',{}).get('mode')!='coalesce':
            raise Refusal('coalescence requires actual owner selection of an existing responsibility')
        return answer
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


TASK_REQUIRED = {'semantic','summary','findings','failures','unknowns','artifacts','category'}
TASK_OPTIONAL = {'handoffs','no_handoff_reason','completion'}
TASK_ARRAYS = ('findings','failures','unknowns','artifacts','handoffs')
TASK_SEMANTICS = {'DONE','PARTIAL','FAILED','UNKNOWN'}
TASK_CATEGORIES = {'proposal','consolidated','qualification','scope','blocker','complete'}
ORIGINAL_FIELDS_KIND = 'outer-contract-original'
_NO_PRIOR = object()
HANDOFF_KINDS = {'work','result','question'}


def artifact_leaves(artifacts):
    """Validate declared references without acquiring metadata or inventing paths.

    Groups retain their full meaning in the result; only explicit leaf paths
    select bytes for custody. Metadata such as common/canonical_target is data.
    """
    leaves=[]
    def visit(items,depth):
        if not isinstance(items,list) or len(items)>64 or depth>4:
            raise Refusal('artifacts require bounded lists/groups (64 items/leaves, depth4)')
        for item in items:
            if isinstance(item,dict) and 'files' in item:
                if 'path' in item or not item['files']:
                    raise Refusal('artifact group needs nonempty files and no ambiguous group path')
                visit(item['files'],depth+1)
                continue
            path=item if isinstance(item,str) else item.get('path') if isinstance(item,dict) else None
            if not isinstance(path,str) or not path or not Path(path).is_absolute() or '..' in Path(path).parts:
                raise Refusal('artifact leaf needs an explicit absolute path; no invented or relative paths')
            leaves.append({'path':path} if isinstance(item,str) else item)
            if len(leaves)>64:raise Refusal('bounded declared artifact leaf count64 exceeded')
    visit(artifacts,0)
    return leaves


def artifact_paths(artifacts):
    return [item['path'] for item in artifact_leaves(artifacts)]


def handoff_issue(handoff):
    if not isinstance(handoff,dict) or set(handoff)!={'recipient','kind','text','ref','required'}:
        return 'handoff needs exact recipient/kind/text/ref/required fields'
    if not isinstance(handoff['recipient'],str) or handoff['recipient'] not in ROLES|{'Root'}:
        return 'handoff recipient must name a selected role or external Root'
    if handoff['required']!='settled':
        return 'necessary task handoffs retain actual recipient processing and settlement'
    try:
        required_text(handoff['kind'],'handoff intent label',128)
        required_text(handoff['text'],'handoff meaning',65536)
        if handoff['ref'] is not None:required_text(handoff['ref'],'handoff reference',16000)
    except Refusal as exc:return str(exc)
    return None


def handoff_delivery_kind(handoff):
    issue=handoff_issue(handoff)
    if issue:raise Refusal(issue)
    # Unfamiliar intent labels are faithful questions for the actual recipient,
    # never executable message kinds or an automatic grant of work authority.
    return handoff['kind'] if handoff['kind'] in HANDOFF_KINDS else 'question'


def task_result_instructions():
    """The prompt and both live/collected validators use this same contract."""
    return ('INNER TASK RESULT: required keys='+encode(sorted(TASK_REQUIRED))+
        '; only optional keys='+encode(sorted(TASK_OPTIONAL))+'. No other outer keys. '
        'semantic is one of '+encode(sorted(TASK_SEMANTICS))+'; category is one of '+encode(sorted(TASK_CATEGORIES))+'. '
        'Use blocker for blocked work (legacy blocked alias is accepted only for non-DONE). '
        'summary is nonempty text (at most16000 UTF-8 bytes); findings/failures/unknowns/artifacts are explicit lists, '
        'including honest empties, never invented empties to obtain DONE. PARTIAL/FAILED/UNKNOWN must retain '
        'failures or unknowns. Optional handoffs is a list of at most16; no_handoff_reason is text (or null when '
        'handoffs is nonempty); completion is an object. '
        'Artifacts: at most64 explicit absolute path strings or {path:ABSOLUTE_PATH,...metadata}; '
        'groups use {files:[LEAVES_OR_GROUPS],...metadata}, nonempty files, no group path, depth at most4 '
        'and at most64 total leaves. Keep common/kind/hash/byte/anchor/read-extent metadata intact; '
        'Supplied leaf sha256/bytes must match the declared source bytes actually captured. '
        'common metadata is never an implicit path or authority. No relative or invented paths. '
        'Handoffs use exact {recipient,kind,text,ref,required}; recipient is an allowed role or Root, '
        'required="settled", text is full nonempty meaning, ref is a nonempty string or null. '
        'kind is a nonempty intent label up to128 UTF-8 bytes. Prefer work/result/question. '
        'Other labels are conserved verbatim and delivered only as addressed questions for actual recipient '
        'disposition, never automatic execution, acceptance or expanded effects. '
        'Preserve dissent as attributed entries in findings with its full original evidence/meaning, not an outer dissent key. '
        'If dissent exposes unresolved local work, also retain that work in failures/unknowns and return truthful blocked/partial readiness. '
        'If clarifying an outer mismatch, preserve original valid findings/failures/unknowns/artifacts/handoffs as verbatim '
        'array prefixes. If artifact/handoff items themselves are malformed, conserve that entire original array '
        'in outer-contract-original.fields and keep its valid items as verbatim prefixes of the repaired list. '
        'Clarify missing paths only from genuine owned evidence, never guess them. '
        'Original non-list findings/failures/unknowns must be retained as the first item of the repaired '
        'list, not silently replaced by []. Conserve original unsupported or malformed array fields exactly in a findings '
        'entry {kind:"'+ORIGINAL_FIELDS_KIND+'",fields:{ORIGINAL_KEY:ORIGINAL_VALUE,...}}. For a non-object original, '
        'fields={"$result":ORIGINAL_JSON_VALUE}. This is data preservation, not authority or a resolution/acceptance claim. '
        'Correct only the representation or genuinely remaining authorized work in this SAME context; do not hide a local '
        'blocker, change PARTIAL to DONE merely to repair JSON, drop adverse evidence or replay completed effects.\n')


def task_result_issues(answer):
    """Pure complete outer diagnostics; never mutate/drop/project a producer return."""
    if not isinstance(answer,dict):return ['task result must be a JSON object']
    issues=[]
    missing=TASK_REQUIRED-set(answer);extra=set(answer)-TASK_REQUIRED-TASK_OPTIONAL
    if missing:issues.append('missing required task-result fields: '+', '.join(sorted(missing)))
    if extra:issues.append('unsupported task-result fields: '+', '.join(sorted(extra)))
    if 'semantic' in answer and (not isinstance(answer['semantic'],str) or answer['semantic'] not in TASK_SEMANTICS):
        issues.append('semantic must be one of '+', '.join(sorted(TASK_SEMANTICS)))
    if 'summary' in answer:
        try:required_text(answer['summary'],'summary')
        except Refusal as exc:issues.append(str(exc))
    for key in TASK_ARRAYS:
        if key in answer and not isinstance(answer[key],list):issues.append(key+' must be an explicit list, including honest empties')
    category=answer.get('category')
    alias=category=='blocked' and isinstance(answer.get('semantic'),str) and answer['semantic'] in TASK_SEMANTICS-{'DONE'}
    if 'category' in answer and (not isinstance(category,str) or category not in TASK_CATEGORIES) and not alias:
        issues.append('category must be one of '+', '.join(sorted(TASK_CATEGORIES))+'; blocked alias only for non-DONE')
    if isinstance(answer.get('semantic'),str) and answer['semantic'] in TASK_SEMANTICS-{'DONE'} and not (answer.get('failures') or answer.get('unknowns')):
        issues.append('partial/failed/unknown work must retain its unresolved meaning in failures or unknowns')
    if isinstance(answer.get('handoffs'),list) and len(answer['handoffs'])>16:issues.append('handoff count exceeds admitted per-task bound16')
    if isinstance(answer.get('artifacts'),list):
        try:artifact_paths(answer['artifacts'])
        except Refusal as exc:issues.append('artifacts: '+str(exc))
    if isinstance(answer.get('handoffs'),list):
        for index,handoff in enumerate(answer['handoffs']):
            issue=handoff_issue(handoff)
            if issue:issues.append('handoff '+str(index)+': '+issue)
    if ('no_handoff_reason' in answer and not isinstance(answer['no_handoff_reason'],str)
            and not (answer['no_handoff_reason'] is None and isinstance(answer.get('handoffs'),list) and answer['handoffs'])):
        issues.append('no_handoff_reason must be text; null is allowed only with nonempty handoffs')
    if 'completion' in answer and not isinstance(answer['completion'],dict):issues.append('completion must be an object')
    return issues


def clarification_fields(prior):
    if not isinstance(prior,dict):return {'$result':prior}
    return {k:v for k,v in prior.items() if k not in TASK_REQUIRED|TASK_OPTIONAL or
            k in TASK_ARRAYS and (not isinstance(v,list) or valid_items(k,v)!=v)}


def valid_items(key,items):
    """Conserve invalid nested representations separately, never erase them."""
    if key=='handoffs':return [item for item in items if not handoff_issue(item)]
    if key!='artifacts':return items
    valid=[]
    for item in items:
        try:artifact_paths([item])
        except Refusal:continue
        valid.append(item)
    return valid


def clarification_issues(answer,prior):
    """Exact conservation, not semantic normalization of an old rejected response."""
    if not isinstance(answer,dict):return ['clarification must return a task-result object']
    issues=[]
    if isinstance(prior,dict):
        for key in TASK_ARRAYS:
            if key not in prior:continue
            old=prior[key]
            if not isinstance(old,list):
                if key not in {'findings','failures','unknowns'}:continue
                old=[old]
            else:old=valid_items(key,old)
            if not isinstance(answer.get(key),list) or answer[key][:len(old)]!=old:
                issues.append('clarification erased or rewrote original '+key)
    fields=clarification_fields(prior)
    if fields and (not isinstance(answer.get('findings'),list) or
            {'kind':ORIGINAL_FIELDS_KIND,'fields':fields} not in answer['findings']):
        issues.append('clarification must conserve original extra/malformed fields in findings kind='+ORIGINAL_FIELDS_KIND+': '+', '.join(sorted(fields)))
    return issues


def task_result(answer,prior=_NO_PRIOR):
    issues=task_result_issues(answer)
    if prior is not _NO_PRIOR:issues+=clarification_issues(answer,prior)
    if issues:raise Refusal('; '.join(issues))
    if answer.get('category')=='blocked':
        return {**answer,'category':'blocker'}  # Existing non-DONE alias; raw remains conserved, no other projection.
    return answer


def collected_task_result(attempt):
    answer=json.loads(attempt['result']) if attempt['result'] else None
    detail=json.loads(attempt['detail'])
    return task_result(answer,detail['prior_turn_result']) if 'prior_turn_result' in detail else task_result(answer)


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
