"""One producer contract for live clarification and collected local assessment.

No result normalization or visible-label/protocol-ID inference. Linked evidence
qualifies producer resolution claims, not independent semantic acceptance.
"""
import hashlib
import json
from pathlib import Path
import re

from .contracts import Refusal, digest, required_text, task_result_issues, collected_task_result, artifact_paths

CONTROLLER_DUTIES={'publication','artifact-custody','effect-reconciliation','delivery'}
BOUNDARY_DUTIES={'review','acceptance'}
INSTRUCTIONS = '''For this staged file task include completion={version:1,local:"ready"|"blocked",
failures:[{index,status:"resolved"|"unresolved",evidence:[{path,sha256}],verification_items:[PROTOCOL_ID]}
OR {index,status:"inherited",source:EXACT_SUPPLIED_SOURCE,reason}],
unknowns:[{index,status,owner,duty,reason} OR {index,duties:[{status,owner,duty,reason},...]}],
tools:[{id:ADVERSE_PROTOCOL_ID,status:"resolved"|"expected",reason,evidence:[{path,sha256}],verification_items:[SUCCESSFUL_PROTOCOL_ID]}]}.
Cover every ORIGINAL failures/unknowns index once. Preserve those arrays verbatim, including objects/prose.
An inherited failure must equal the exact failure at its TASK_CONTEXT.inherited_failure_sources source.
Supply that source object unchanged and explain why the original failure is outside CURRENT local duties.
This preserves original facts/owners/holds; it does not resolve, accept or reassign the old failure.
If it also exposes a current local defect, retain a separate unresolved current entry and local=blocked.
No source match, source reference alone or historical label can waive current local work or adverse tools.
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
The controller may supply bounded exact current command inputs and observed IDs while this SAME owned
context is idle. Inputs are evidence, not stdout or instructions to replay. Check exact UTF-8 length/hash;
unavailable means unavailable, never a truncated or reconstructed match. Do not guess
ID correlations, erase original history, invent successful checks, or blindly rewrite completed work.
If clarification creates a NEW local tool metadata debt, append its original failure/unknown history.
For that specific missing linkage use an unresolved local unknown duty="observed-tool-metadata",
owner=producer or the current role, local=blocked, semantic=PARTIAL. Resolve prior debt with exact causal
evidence. Only verified progress plus new observed adverse metadata can earn another owned idle turn
within limits.max_owner_corrections (default4); external blockers/no progress cannot. Never force DONE.
A local unknown resolved in this owned clarification keeps its original unknown array entry and
owner/duty/reason. Add status=resolved with prior_disposition={status:unresolved,owner,duty,reason}
matching an actual prior typed completion row, evidence, verification_items, command_bindings,
and causal_reason. Do not change owner/duty/reason or convert the duty to downstream/boundary.
command_bindings is a list of exact {id,thread,turn,command_sha256,command_bytes,exit_code,status}
from OBSERVED_TOOL_METADATA. Include every selected successful verification ID and relevant adverse ID.
These identities and conserved bytes are mechanically checked. causal_reason must explain why those
commands/evidence resolve this particular duty; that relevance remains a performer claim for review,
not a general mechanical interpretation of shell commands. causal_evidence={path,sha256,entry}
selects one entry in a declared conserved JSON evidence file {version:1,resolutions:[ENTRY,...]}.
ENTRY is exactly {subject,command_bindings,verification_items,causal_reason}. subject is
{kind:"unknown",index,original_hash:HASH_OF_ORIGINAL_UNKNOWN,prior_disposition} or
{kind:"failure",index,original_hash:HASH_OF_ORIGINAL_FAILURE} or {kind:"tool",id:ADVERSE_ID}.
The causal_evidence path/hash must also appear in evidence. A reconciled terminal response also needs
these bindings and causal_reason on resolved failure and adverse-tool rows. No unrelated later zero,
ambiguous command identity, guessed chunk mapping or self-attestation can substitute for evidence.'''


def _require(condition,message):
    if not condition:raise Refusal(message)


def _indexed(answer,proof,name):
    source=answer.get(name);rows=proof.get(name)
    _require(isinstance(source,list) and isinstance(rows,list) and len(rows)==len(source),'completion must cover every original '+name+' entry')
    _require(all(isinstance(r,dict) and type(r.get('index')) is int for r in rows),'typed history index required')
    _require(sorted(r['index'] for r in rows)==list(range(len(source))),'history indices duplicated or missing')
    return rows


COMMAND_BINDING_FIELDS={'id','thread','turn','command_sha256','command_bytes','exit_code','status'}
CORRELATION_FIELDS={'command_bindings','causal_reason','causal_evidence'}


def _correlation(row,items,required=(),failure=None):
    bindings=row.get('command_bindings')
    _require(isinstance(bindings,list) and 1<=len(bindings)<=128,'exact command bindings required')
    required_text(row.get('causal_reason'),'causal verification relevance assertion',4000)
    _require(len({b.get('id') for b in bindings if isinstance(b,dict)})==len(bindings),'ambiguous command binding IDs')
    observed={}
    for item in items:observed.setdefault(item.get('id'),[]).append(item)
    for binding in bindings:
        _require(isinstance(binding,dict) and set(binding)==COMMAND_BINDING_FIELDS,'exact command identity fields required')
        matches=observed.get(binding['id'],[])
        _require(len(matches)==1,'ambiguous or unobserved command identity')
        item=matches[0]
        _require(item.get('type')=='commandExecution' and item.get('completed_notification') is True and
                 item.get('status') in {'completed','failed'} and type(item.get('exit_code')) is int and
                 isinstance(item.get('thread'),str) and isinstance(item.get('turn'),str) and
                 isinstance(item.get('command_sha256'),str) and re.fullmatch('[0-9a-f]{64}',item['command_sha256']) and
                 type(item.get('command_bytes')) is int and item['command_bytes']>0 and
                 digest(binding)==digest({k:item.get(k) for k in COMMAND_BINDING_FIELDS}),
                 'command fingerprint/thread/turn/outcome binding mismatch')
    ids={b['id'] for b in bindings}
    _require(set(row['verification_items'])<=ids and set(required)<=ids,'command bindings omit relevant verification/adverse IDs')
    if isinstance(failure,dict) and isinstance(failure.get('command'),str):
        import hashlib
        command=failure['command'].encode()
        matches=[i for i in items if i.get('type')=='commandExecution' and
            i.get('command_sha256')==hashlib.sha256(command).hexdigest() and i.get('command_bytes')==len(command) and
            i.get('exit_code')==failure.get('exit_code') and i.get('exit_code') not in {None,0}]
        _require(len(matches)==1 and matches[0]['id'] in ids,'original failure command identity is ambiguous or unmatched')


def _evidence(row,zero,check_ref,items=(),strict=False,required=(),failure=None,subject=None):
    refs=row.get('evidence');checks=row.get('verification_items')
    _require(isinstance(refs,list) and 1<=len(refs)<=16 and isinstance(checks,list) and 1<=len(checks)<=128,
             'resolution needs bounded report evidence and verification protocol IDs')
    _require(all(isinstance(c,str) and c in zero for c in checks),'verification must name observed successful command protocol IDs, never visible chunk labels')
    _require(len(checks)==len(set(checks)),'duplicate verification protocol IDs')
    correlate=bool(strict or CORRELATION_FIELDS & set(row))
    if correlate:_correlation(row,items,required,failure)
    bodies={}
    for ref in refs:
        _require(isinstance(ref,dict) and set(ref)=={'path','sha256'} and isinstance(ref['path'],str)
                 and isinstance(ref['sha256'],str) and re.fullmatch('[0-9a-f]{64}',ref['sha256']) is not None,
                 'exact resolution artifact path/hash required')
        if check_ref:bodies[(ref['path'],ref['sha256'])]=check_ref(ref)
    if correlate:
        witness=row.get('causal_evidence')
        _require(isinstance(witness,dict) and set(witness)=={'path','sha256','entry'} and isinstance(witness['path'],str) and
            isinstance(witness['sha256'],str) and type(witness['entry']) is int,
            'exact conserved causal witness and entry required')
        body=bodies.get((witness['path'],witness['sha256']))
        _require(isinstance(body,bytes),'causal witness bytes must be actually acquired/conserved')
        try:
            from .contracts import parse_json
            manifest=parse_json(body.decode('utf-8'))
        except (ValueError,UnicodeError,Refusal) as exc:raise Refusal('causal witness must be typed JSON evidence') from exc
        _require(isinstance(manifest,dict) and type(manifest.get('version')) is int and manifest['version']==1 and isinstance(manifest.get('resolutions'),list),
                 'causal witness resolutions version1 required')
        entries=manifest['resolutions'];index=witness['entry']
        _require(0<=index<len(entries) and digest(entries[index])==digest({
            'subject':subject,'command_bindings':row['command_bindings'],
            'verification_items':row['verification_items'],'causal_reason':row['causal_reason']}),
            'causal witness does not bind this duty and exact command selection; unrelated later success is insufficient')


def _duty(row,index,answer,task,config,zero,check_ref,items,prior_results):
    base={'status','owner','duty','reason'}
    resolved=base|{'prior_disposition','evidence','verification_items'}|CORRELATION_FIELDS
    _require(isinstance(row,dict) and (set(row)==resolved if row.get('status')=='resolved' else set(row)==base),
             'explicit individual unknown disposition required')
    _require(all(isinstance(row[k],str) for k in base),'typed unknown status/owner/duty/reason required')
    required_text(row['reason'],'unknown classification rationale',4000);required_text(row['duty'],'individual duty',4000)
    owner,duty,status=row['owner'],row['duty'],row['status'];actor=None
    if status=='unresolved':
        _require(answer['completion']['local']=='blocked','local ready contradicts an unresolved local unknown')
    elif status=='resolved':
        prior=row['prior_disposition']
        _require(isinstance(prior,dict) and set(prior)==base and prior.get('status')=='unresolved' and
            all(prior.get(k)==row[k] for k in ('owner','duty','reason')),
            'resolved local duty must conserve original owner/duty/reason')
        _require(owner not in {'controller','outside-workflow'} and (task is None or owner in {'producer',task['role']}),
            'resolved unknown must remain a current local producer duty')
        def witnessed(old):
            if not isinstance(old,dict) or digest(old.get('unknowns',[])[:index+1])!=digest(answer['unknowns'][:index+1]):return False
            completion=old.get('completion',{})
            if not isinstance(completion,dict):return False
            rows=completion.get('unknowns',[])
            if not isinstance(rows,list):return False
            for entry in rows:
                if not isinstance(entry,dict):continue
                if entry.get('index')!=index:continue
                group=entry.get('duties',[{k:v for k,v in entry.items() if k!='index'}])
                if any(digest(member)==digest(prior) for member in group):return True
            return False
        _require(any(witnessed(old) for old in prior_results),'resolved unknown lacks actual conserved prior local disposition')
        _evidence(row,zero,check_ref,items,True,subject={'kind':'unknown','index':index,
            'original_hash':digest(answer['unknowns'][index]),'prior_disposition':prior})
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


def failure_sources(store,attempt):
    """Only frozen inputs and explicitly linked prior results, never an owner census.

    Sources bind original JSON values, not inferred age, prose labels or semantic
    resolution. The producer must separately attest current duty scope.
    """
    row=store.attempt(attempt);job=store.job(row['job']);sources=[]
    def visit(value,origin,path):
        if isinstance(value,dict):
            failures=value.get('failures')
            if isinstance(failures,list):
                for index,failure in enumerate(failures):
                    sources.append({'source':{**origin,'path':[*path,'failures',index]},'failure':failure})
            for key,child in value.items():visit(child,origin,[*path,key])
        elif isinstance(value,list):
            for index,child in enumerate(value):visit(child,origin,[*path,index])
    for member in json.loads(job['members']):
        event=store.event(member['event'])
        _require(digest(event)==member['hash'],'frozen failure source changed')
        visit(event,{'kind':'event','id':member['event'],'sha256':member['hash']},[])
    detail=json.loads(row['detail'])
    if detail.get('prior_attempt'):
        old=store.attempt(detail['prior_attempt'])
        _require(old['job']==row['job'] and old['result']==detail.get('prior_result'),
                 'inherited prior result binding changed')
        if old['result'] is not None:
            prior=json.loads(old['result'])
            visit(prior,{'kind':'prior-result','id':old['id'],'sha256':digest(prior)},[])
    return sources


def inspect(answer,items,task=None,config=None,check_ref=None,inherited_sources=(),prior_results=(),strict_correlation=False,validate_partial=False):
    """Representation checks are identical while owned-live and after collection.

    Unsettled execution/capture is a separate hard fence, not a proof grammar
    repair or a label the producer can waive. Returns issues without mutating input.
    """
    issues=task_result_issues(answer);duties=[]
    def check(action):
        try:return action()
        except Refusal as exc:issues.append(str(exc))
    if not isinstance(answer,dict) or answer.get('semantic') not in ({'DONE','PARTIAL'} if validate_partial else {'DONE'}):return None,[],issues
    if len({r.get('id') for r in items})!=len(items):issues.append('ambiguous observed protocol IDs')
    proof=answer.get('completion')
    if not isinstance(proof,dict) or not {'version','local','failures','unknowns','tools'}<=set(proof) or set(proof)-{'version','local','failures','unknowns','tools','reported_commands','integration_steps','discovered_points'}:
        return None,[],issues+['explicit completion fields/version1 required; original return retained']
    if type(proof['version']) is not int or proof['version']!=1 or not isinstance(proof['local'],str) or proof['local'] not in {'ready','blocked'}:
        return proof,[],issues+['typed version1 local ready/blocked assessment required']
    zero={r['id'] for r in items if r.get('type')=='commandExecution' and r.get('exit_code')==0 and r.get('completed_notification') and r.get('status')=='completed'}
    adverse={r['id'] for r in items if r.get('exit_code') not in {None,0} or r.get('status')=='failed'}
    def failure(row):
        if row.get('status')=='inherited':
            _require(set(row)=={'index','status','source','reason'},'typed inherited failure source/rationale required')
            required_text(row['reason'],'inherited failure current-scope rationale',4000)
            sources=inherited_sources() if callable(inherited_sources) else inherited_sources
            _require(any(digest(row['source'])==digest(s['source']) and digest(answer['failures'][row['index']])==digest(s['failure'])
                         for s in sources),'inherited failure must match an exact controller-supplied frozen source')
            return
        _require(set(row)-CORRELATION_FIELDS=={'index','status','evidence','verification_items'},'typed local failure disposition required')
        if row['status']=='unresolved':_require(proof['local']=='blocked','local ready contradicts an unresolved local failure')
        else:
            _require(row['status']=='resolved','local failure status must be resolved or unresolved')
            _evidence(row,zero,check_ref,items,strict_correlation,failure=answer['failures'][row['index']],subject={'kind':'failure','index':row['index'],
                'original_hash':digest(answer['failures'][row['index']])})
    rows=check(lambda:_indexed(answer,proof,'failures'))
    for row in rows or []:check(lambda row=row:failure(row))
    rows=check(lambda:_indexed(answer,proof,'unknowns'))
    for row in rows or []:
        if set(row)=={'index','duties'}:
            group=row['duties']
            if not isinstance(group,list) or not 1<=len(group)<=16:
                issues.append('unknown duties group requires 1..16 explicit individual members');continue
        elif set(row)-{'prior_disposition','evidence','verification_items'}-CORRELATION_FIELDS=={'index','status','owner','duty','reason'}:group=[{k:v for k,v in row.items() if k!='index'}]
        else:issues.append('unknown entry must be one disposition or indexed duties group');continue
        seen=set()
        for member in group:
            duty=check(lambda member=member:_duty(member,row['index'],answer,task,config,zero,check_ref,items,prior_results))
            if duty:
                key=(duty['status'],duty['owner'],duty['duty'])
                if key in seen:issues.append('duplicate individual duty in group')
                seen.add(key);duties.append(duty)
    # A prior structured local duty cannot disappear by relabelling it as
    # downstream work or by dropping one member of an indexed duties group.
    for old in prior_results:
        if not isinstance(old,dict) or not isinstance(old.get('completion'),dict):continue
        old_rows=old['completion'].get('unknowns',[])
        if not isinstance(old_rows,list):continue
        for entry in old_rows:
            if not isinstance(entry,dict) or type(entry.get('index')) is not int:continue
            index=entry['index'];members=entry.get('duties',[{k:v for k,v in entry.items() if k!='index'}])
            if not isinstance(members,list):continue
            for member in members:
                if (not isinstance(member,dict) or member.get('status')!='unresolved' or
                        member.get('owner') not in {'producer',task['role'] if task else 'producer'}):continue
                candidates=[d for d in duties if d['index']==index and
                    all(d.get(k)==member.get(k) for k in ('owner','duty','reason')) and
                    (d['status']=='unresolved' or d['status']=='resolved' and
                     digest(d.get('prior_disposition'))==digest(member))]
                if not candidates:issues.append('original local unknown duty erased or reclassified; preserve or resolve it with evidence')
    rows=proof['tools']
    if not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows):
        issues.append('typed adverse protocol-item dispositions required')
    else:
        if len(rows)!=len(adverse) or {r['id'] for r in rows}!=adverse:
            issues.append('tools must cover ONLY the observed adverse protocol IDs exactly once; successful commands require no entry; never correlate visible labels')
        for row in rows:
            def tool(row=row):
                _require(set(row)-CORRELATION_FIELDS=={'id','status','reason','evidence','verification_items'} and isinstance(row['status'],str) and row['status'] in {'resolved','expected'},'typed adverse tool disposition required')
                required_text(row['reason'],'tool resolution rationale',4000);_evidence(row,zero,check_ref,items,strict_correlation,required=[row['id']],subject={'kind':'tool','id':row['id']})
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


def needs_clarification(answer,items,task=None,config=None,check_ref=None,inherited_sources=()):
    return bool(inspect(answer,items,task,config,check_ref,inherited_sources)[2])


def live_issues(store,attempt,answer,items,task,prior_results=(),strict_correlation=False,validate_partial=False):
    if not task.get('routine_completion') or not isinstance(answer,dict) or answer.get('semantic') not in ({'DONE','PARTIAL'} if validate_partial else {'DONE'}):
        return task_result_issues(answer)
    from .custody import read_file,safe_path
    from .publication import stages
    root=store.home/'artifacts'/attempt
    try:declared=set(artifact_paths(answer.get('artifacts')))
    except Refusal:return task_result_issues(answer)
    declared.update(stages(store,attempt).values())
    def reference(ref):
        path=Path(ref['path'])
        _require(path.is_relative_to(root) and '..' not in path.parts,'resolution evidence must belong to this producer attempt')
        _require(not any(path==Path(p) or path.is_relative_to(Path(p)) for p in store.config.get('artifact_exclusions',[])),'opaque resolution reference excluded before metadata')
        _require(str(path) in declared,'resolution reference must be a declared own output or known staged file')
        try:body,witness=read_file(safe_path(str(path),[str(root)]),min(store.config['limits'].get('max_artifact_bytes',33554432),store.config['limits']['max_bytes']))
        except (OSError,Refusal) as exc:raise Refusal('own resolution artifact unavailable/unsafe: '+type(exc).__name__) from exc
        _require(witness['sha256']==ref['sha256'],'resolution artifact hash is not current exact own bytes')
        return body
    return inspect(answer,items,task,store.config,reference,lambda:failure_sources(store,attempt),prior_results,strict_correlation,validate_partial)[2]


def feedback_progress(store,attempt,prior,answer,previous_items,items,task,prior_results):
    """Eligibility for feedback, never readiness or semantic acceptance.

    Check prior adverse resolution against actual current successes, with the
    same strict byte/causal checks. Only newly observed adverse metadata may be
    absent from this return; all real external/unresolved prior duties stop here.
    """
    if not isinstance(prior,dict) or not isinstance(answer,dict) or answer.get('semantic')!='PARTIAL':return False
    proof=answer.get('completion');old=prior.get('completion')
    if not isinstance(proof,dict) or not isinstance(old,dict) or proof.get('local')!='blocked':return False
    if any(not isinstance(proof.get(k),list) for k in ('tools','failures','unknowns')) or not isinstance(old.get('tools'),list):return False
    adverse=lambda rows:{r['id'] for r in rows if r.get('exit_code') not in {None,0} or r.get('status')=='failed'}
    before=adverse(previous_items);new=adverse(items)-before
    if not new:return False
    # A claim alone is insufficient: live_issues below validates exact successful
    # selections, original duty subjects, current own bytes and conserved priors.
    resolved=lambda p:{r.get('id') for r in p.get('tools',[]) if isinstance(r,dict) and r.get('status') in {'resolved','expected'}}
    if not (resolved(proof)-resolved(old)) & before:return False
    unresolved=[]
    for row in proof.get('unknowns',[]):
        if not isinstance(row,dict) or type(row.get('index')) is not int:return False
        group=row.get('duties',[row])
        if not isinstance(group,list):return False
        for duty in group:
            if not isinstance(duty,dict):return False
            if row['index']>=len(prior.get('unknowns',[])) and duty.get('status')=='deferred':return False
            if duty.get('status')=='unresolved':
                if (row.get('index',-1)<len(prior.get('unknowns',[])) or
                        duty.get('owner') not in {'producer',task['role']} or duty.get('duty')!='observed-tool-metadata'):
                    return False
                unresolved.append(duty)
    if not unresolved:return False
    if any(r.get('status')=='unresolved'
           for r in proof.get('failures',[]) if isinstance(r,dict)):return False
    known=[r for r in items if r['id'] not in new]
    return not live_issues(store,attempt,answer,known,task,prior_results,True,True)


def assess(store,attempt):
    from .custody import frozen_body
    answer=collected_task_result(attempt)
    detail=json.loads(attempt['detail'])
    tools=detail.get('tool_completion',{})
    _require(tools.get('complete'),'unsettled tool metadata blocks local readiness')
    root=store.home/'artifacts'/attempt['id']
    def reference(ref):
        path=Path(ref['path'])
        _require(path.is_relative_to(root) and '..' not in path.parts,'resolution evidence must belong to this producer attempt')
        held=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],str(path)))
        _require(held and held['sha256']==ref['sha256'],'resolution evidence is not the exact conserved artifact')
        # Conservation/own-attempt identity does not grant current acquisition
        # rights. Close recorded origins before even reading retained length.
        blob=frozen_body(store,ref['sha256'],task,str(path))
        _require(blob is not None,'exact causal evidence bytes are not conserved')
        _require(hashlib.sha256(blob['body']).hexdigest()==ref['sha256'],'conserved resolution evidence hash changed')
        return blob['body']
    job=store.job(attempt['job']);task=store.config['tasks'][job['task']]
    prior_results=prior_handbacks(detail)
    proof,duties,issues=inspect(answer,tools['items'],task,store.config,reference,lambda:failure_sources(store,attempt['id']),prior_results,bool(detail.get('handback_receipt')))
    _require(not issues,'; '.join(issues))
    _require(answer.get('semantic')=='DONE' and proof['local']=='ready','current local work is not ready')
    return {'version':1,'local':'ready','producer':attempt['session'],'result_hash':digest(answer),
        'original_failures':answer['failures'],'original_unknowns':answer['unknowns'],
        'resolved_history':[r for r in proof['failures'] if r['status']=='resolved'],
        'inherited_history':[r for r in proof['failures'] if r['status']=='inherited'],
        'tool_dispositions':proof['tools'],'subsequent_duties':[d for d in duties if d['status']!='resolved'],
        'resolved_local_unknowns':[d for d in duties if d['status']=='resolved'],
        'handback_receipt':detail.get('handback_receipt'),
        'reported_commands':proof.get('reported_commands',[]),
        'clarification_origin':{'result_hash':digest(detail['prior_turn_result']),'completion':detail['prior_turn_result'].get('completion') if isinstance(detail['prior_turn_result'],dict) else None,'issues':detail.get('readiness_issues',[])} if detail.get('readiness_clarification') else None,
        'qualification':'producer-attested local readiness/resolution with actual protocol IDs and conserved-byte links; producer-visible labels are uncorrelated claims, not OS handles; not independent semantic verification or downstream acceptance'}


def prior_handbacks(detail):
    values=[r['typed_return'] for r in detail.get('prior_terminal_returns',[]) if r.get('valid_json')]
    if 'prior_turn_result' in detail:values.append(detail['prior_turn_result'])
    values.extend(detail.get('prior_turn_results',[]))
    return values
