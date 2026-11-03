"""One producer contract for live clarification and collected local assessment.

No result normalization or visible-label/protocol-ID inference. Linked evidence
qualifies producer resolution claims, not independent semantic acceptance.
"""
import json
from pathlib import Path
import re

from .contracts import Refusal, digest, required_text

CONTROLLER_DUTIES={'publication','artifact-custody','effect-reconciliation','delivery'}
BOUNDARY_DUTIES={'review','acceptance'}
INSTRUCTIONS = '''For this staged file task include completion={version:1,local:"ready"|"blocked",
failures:[{index,status:"resolved"|"unresolved",evidence:[{path,sha256}],verification_items:[PROTOCOL_ID]}],
unknowns:[{index,status,owner,duty,reason} OR {index,duties:[{status,owner,duty,reason},...]}],
tools:[{id:ADVERSE_PROTOCOL_ID,status:"resolved"|"expected",reason,evidence:[{path,sha256}],verification_items:[SUCCESSFUL_PROTOCOL_ID]}]}.
Cover every ORIGINAL failures/unknowns index once. Preserve those arrays verbatim, including objects/prose.
Use a duties group to split one combined original unknown into individual obligations, not a combined prose enum.
Controller deferred duties are EXACTLY publication, artifact-custody, effect-reconciliation, delivery;
owner=controller. A review/acceptance boundary is status=boundary, owner=outside-workflow,
duty EXACTLY review OR acceptance (use two group members for both). Required external duties use
status=deferred, their actual allowlisted role owner, a meaningful duty and necessary settled handoff.
Actual unresolved local work remains status=unresolved and local=blocked; DONE alone does not waive it.
ready means all current local construction/verification is satisfied, never downstream acceptance.
The tools list covers ONLY actually observed failed/nonzero PROTOCOL items, exactly once.
If the observed adverse set is EMPTY, tools MUST be []. Successful commands need NO adverse disposition.
Visible exec_command chunk labels and provider process labels are NOT protocol IDs or OS handles.
Optional reported_commands=[{namespace:"producer-visible",label,status,exit_code,reason}] preserves such
producer claims separately; it cannot discharge an adverse obligation or prove verification.
For resolved history/adverse items bind exact conserved OWN declared artifact hashes and explicitly
selected actual successful command PROTOCOL IDs. An unrelated later0 does not prove resolution.
The controller may supply bounded observed IDs while this SAME owned context is idle. Do not guess
ID correlations, erase original history, invent successful checks, or blindly rewrite completed work.'''


def _require(condition,message):
    if not condition:raise Refusal(message)


def _indexed(answer,proof,name):
    source=answer.get(name);rows=proof.get(name)
    _require(isinstance(source,list) and isinstance(rows,list) and len(rows)==len(source),'completion must cover every original '+name+' entry')
    _require(all(isinstance(r,dict) and type(r.get('index')) is int for r in rows),'typed history index required')
    _require(sorted(r['index'] for r in rows)==list(range(len(source))),'history indices duplicated or missing')
    return rows


def _evidence(row,zero,check_ref):
    refs=row.get('evidence');checks=row.get('verification_items')
    _require(isinstance(refs,list) and 1<=len(refs)<=16 and isinstance(checks,list) and 1<=len(checks)<=128,
             'resolution needs bounded report evidence and verification protocol IDs')
    _require(all(isinstance(c,str) and c in zero for c in checks),'verification must name observed successful command protocol IDs, never visible chunk labels')
    for ref in refs:
        _require(isinstance(ref,dict) and set(ref)=={'path','sha256'} and isinstance(ref['path'],str)
                 and isinstance(ref['sha256'],str) and re.fullmatch('[0-9a-f]{64}',ref['sha256']) is not None,
                 'exact resolution artifact path/hash required')
        if check_ref:check_ref(ref)


def _duty(row,index,answer,task,config):
    _require(isinstance(row,dict) and set(row)=={'status','owner','duty','reason'},'explicit individual unknown disposition required')
    _require(all(isinstance(row[k],str) for k in row),'typed unknown status/owner/duty/reason required')
    required_text(row['reason'],'unknown classification rationale',4000);required_text(row['duty'],'individual duty',4000)
    owner,duty,status=row['owner'],row['duty'],row['status'];actor=None
    if status=='unresolved':
        _require(answer['completion']['local']=='blocked','local ready contradicts an unresolved local unknown')
    elif status=='boundary':
        _require(owner=='outside-workflow' and duty in BOUNDARY_DUTIES,'boundary duty must be exactly review or acceptance; split combined duties')
    elif status=='deferred' and owner=='controller':
        _require(duty in CONTROLLER_DUTIES,'controller duty must be one exact publication/artifact-custody/effect-reconciliation/delivery value; split combined duties')
        actor=config['actor'] if config else None
    elif status=='deferred':
        if task is not None:_require(owner in task.get('allowed_handoffs',[]),'external duty owner is outside the selected role allowlist')
        handoffs=answer.get('handoffs',[])
        _require(isinstance(handoffs,list) and any(isinstance(h,dict) and h.get('recipient')==owner and h.get('required')=='settled' for h in handoffs),
                 'necessary external duty lacks a durable admitted handoff')
        actor=config['delivery']['recipients'][owner]['session'] if config else None
    else:raise Refusal('unresolved/unsupported local unknown remains held')
    return {'index':index,**row,'actual_owner':actor}


def inspect(answer,items,task=None,config=None,check_ref=None):
    """Representation checks are identical while owned-live and after collection.

    Unsettled execution/capture is a separate hard fence, not a proof grammar
    repair or a label the producer can waive. Returns issues without mutating input.
    """
    issues=[];duties=[]
    def check(action):
        try:return action()
        except Refusal as exc:issues.append(str(exc))
    proof=answer.get('completion') if isinstance(answer,dict) else None
    if not isinstance(proof,dict) or not {'version','local','failures','unknowns','tools'}<=set(proof) or set(proof)-{'version','local','failures','unknowns','tools','reported_commands'}:
        return None,[],['explicit completion fields/version1 required; original return retained']
    if type(proof['version']) is not int or proof['version']!=1 or not isinstance(proof['local'],str) or proof['local'] not in {'ready','blocked'}:
        return proof,[],['typed version1 local ready/blocked assessment required']
    zero={r['id'] for r in items if r.get('type')=='commandExecution' and r.get('exit_code')==0 and r.get('completed_notification') and r.get('status')=='completed'}
    adverse={r['id'] for r in items if r.get('exit_code') not in {None,0} or r.get('status')=='failed'}
    def failure(row):
        _require(set(row)=={'index','status','evidence','verification_items'},'typed local failure disposition required')
        if row['status']=='unresolved':_require(proof['local']=='blocked','local ready contradicts an unresolved local failure')
        else:
            _require(row['status']=='resolved','local failure status must be resolved or unresolved')
            _evidence(row,zero,check_ref)
    rows=check(lambda:_indexed(answer,proof,'failures'))
    for row in rows or []:check(lambda row=row:failure(row))
    rows=check(lambda:_indexed(answer,proof,'unknowns'))
    for row in rows or []:
        if set(row)=={'index','duties'}:
            group=row['duties']
            if not isinstance(group,list) or not 1<=len(group)<=16:
                issues.append('unknown duties group requires 1..16 explicit individual members');continue
        elif set(row)=={'index','status','owner','duty','reason'}:group=[{k:v for k,v in row.items() if k!='index'}]
        else:issues.append('unknown entry must be one disposition or indexed duties group');continue
        seen=set()
        for member in group:
            duty=check(lambda member=member:_duty(member,row['index'],answer,task,config))
            if duty:
                key=(duty['status'],duty['owner'],duty['duty'])
                if key in seen:issues.append('duplicate individual duty in group')
                seen.add(key);duties.append(duty)
    rows=proof['tools']
    if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows):
        issues.append('typed adverse protocol-item dispositions required')
    else:
        if len(rows)!=len(adverse) or {r['id'] for r in rows}!=adverse:
            issues.append('tools must cover ONLY the observed adverse protocol IDs exactly once; successful commands require no entry; never correlate visible labels')
        for row in rows:
            def tool(row=row):
                _require(set(row)=={'id','status','reason','evidence','verification_items'} and isinstance(row['status'],str) and row['status'] in {'resolved','expected'},'typed adverse tool disposition required')
                required_text(row['reason'],'tool resolution rationale',4000);_evidence(row,zero,check_ref)
            check(tool)
    claims=proof.get('reported_commands',[])
    if not isinstance(claims,list) or len(claims)>128:issues.append('reported_commands must be a bounded list of uncorrelated producer claims')
    else:
        for row in claims:
            def claim(row=row):
                _require(isinstance(row,dict) and set(row)=={'namespace','label','status','exit_code','reason'} and row['namespace']=='producer-visible','reported command namespace must be producer-visible, never protocol/OS identity')
                for key in ['label','status','reason']:required_text(row[key],key,4000)
                _require(row['exit_code'] is None or type(row['exit_code']) is int,'reported exit remains numeric or unknown')
            check(claim)
    return proof,duties,issues


def needs_clarification(answer,items,task=None,config=None,check_ref=None):
    return isinstance(answer,dict) and answer.get('semantic')=='DONE' and bool(inspect(answer,items,task,config,check_ref)[2])


def live_issues(store,attempt,answer,items,task):
    if not isinstance(answer,dict) or answer.get('semantic')!='DONE':return []
    from .custody import read_file,safe_path
    from .publication import stages
    root=store.home/'artifacts'/attempt
    declared={r if isinstance(r,str) else r.get('path') for r in answer.get('artifacts',[]) if isinstance(r,str) or isinstance(r,dict) and isinstance(r.get('path'),str)} if isinstance(answer.get('artifacts'),list) else set()
    declared.update(stages(store,attempt).values())
    def reference(ref):
        path=Path(ref['path'])
        _require(path.is_relative_to(root) and '..' not in path.parts,'resolution evidence must belong to this producer attempt')
        _require(not any(path==Path(p) or path.is_relative_to(Path(p)) for p in store.config.get('artifact_exclusions',[])),'opaque resolution reference excluded before metadata')
        _require(str(path) in declared,'resolution reference must be a declared own output or known staged file')
        try:_,witness=read_file(safe_path(str(path),[str(root)]),min(store.config['limits'].get('max_artifact_bytes',33554432),store.config['limits']['max_bytes']))
        except (OSError,Refusal) as exc:raise Refusal('own resolution artifact unavailable/unsafe: '+type(exc).__name__) from exc
        _require(witness['sha256']==ref['sha256'],'resolution artifact hash is not current exact own bytes')
    return inspect(answer,items,task,store.config,reference)[2]


def assess(store,attempt):
    answer=json.loads(attempt['result']) if attempt['result'] else {}
    detail=json.loads(attempt['detail'])
    if detail.get('readiness_clarification'):
        prior=detail['prior_turn_result']
        for key in ['failures','unknowns']:
            old=prior.get(key,[])
            _require(isinstance(answer.get(key),list) and answer[key][:len(old)]==old,'clarification erased or rewrote original '+key)
    tools=detail.get('tool_completion',{})
    _require(tools.get('complete'),'unsettled tool metadata blocks local readiness')
    root=store.home/'artifacts'/attempt['id']
    def reference(ref):
        path=Path(ref['path'])
        _require(path.is_relative_to(root) and '..' not in path.parts,'resolution evidence must belong to this producer attempt')
        held=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],str(path)))
        _require(held and held['sha256']==ref['sha256'],'resolution evidence is not the exact conserved artifact')
    job=store.job(attempt['job']);task=store.config['tasks'][job['task']]
    proof,duties,issues=inspect(answer,tools['items'],task,store.config,reference)
    _require(not issues,'; '.join(issues))
    _require(answer.get('semantic')=='DONE' and proof['local']=='ready','current local work is not ready')
    return {'version':1,'local':'ready','producer':attempt['session'],'result_hash':digest(answer),
        'original_failures':answer['failures'],'original_unknowns':answer['unknowns'],
        'resolved_history':proof['failures'],'tool_dispositions':proof['tools'],'subsequent_duties':duties,
        'reported_commands':proof.get('reported_commands',[]),
        'clarification_origin':{'result_hash':digest(detail['prior_turn_result']),'completion':detail['prior_turn_result'].get('completion'),'issues':detail.get('readiness_issues',[])} if detail.get('readiness_clarification') else None,
        'qualification':'producer-attested local readiness/resolution with actual protocol IDs and conserved-byte links; producer-visible labels are uncorrelated claims, not OS handles; not independent semantic verification or downstream acceptance'}
