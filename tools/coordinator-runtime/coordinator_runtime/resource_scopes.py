"""Compare actual scoped resources without disposing historical role debt."""
import json
import math
import re
import os
import subprocess
import sqlite3
from contextlib import nullcontext
from pathlib import Path

from .contracts import OPERATIONS, PROFILES, Refusal, canonical_uuid, digest, encode, required_text, scoped_task, qa_branch_sequence


def _lexical_root(value):
    path = Path(required_text(str(value), 'resource root', 4000))
    if not path.is_absolute() or '..' in path.parts or path.anchor == '//':
        raise Refusal('absolute canonical single-root resource operand required')
    return path


def root(value, exclusions=(), *, metadata=True):
    # Validate BOTH operands before any symlink/stat operation. In particular,
    # Linux's equivalent // spelling must never bypass a lexical exclusion.
    path = _lexical_root(value)
    excluded = [_lexical_root(p) for p in
                [*exclusions, *[Path.home()/p for p in PROFILES]]]
    if any(path == p or path.is_relative_to(p) or p.is_relative_to(path) for p in excluded):
        raise Refusal('resource overlaps an excluded store before metadata')
    if metadata and any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal('resource aliases need their actual custodian; no symlink inference')
    return path


def overlaps(left, right):
    left, right = _lexical_root(left), _lexical_root(right)
    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
        return True
    def ancestors(path):
        return {(p.stat().st_dev, p.stat().st_ino) for p in (path, *path.parents) if p.exists()}
    def identity(path):
        return (path.stat().st_dev, path.stat().st_ino) if path.exists() else None
    return identity(left) in ancestors(right) or identity(right) in ancestors(left)


def access_modes(task, exclusions, *, metadata=True):
    """Configured access, including staged publication rights, not effect success.

    execution_spec relocates owned/staged writes to an attempt directory. Its
    configured cwd is therefore only a read dependency. A direct workspace-write
    task can write its cwd; canonical write roots survive staging and fencing.
    """
    exclusions = [*exclusions, *task.get('scope_exclusions', [])]
    authority = task['effect_authority']
    reads, writes = authority['read_roots'], authority['write_roots']
    operations = authority['operations']
    if (not isinstance(reads, list) or not isinstance(writes, list)
            or not isinstance(operations, list) or not operations or set(operations) - OPERATIONS
            or task.get('sandbox') not in {'read-only', 'workspace-write'}
            or task.get('effects') not in {'none', 'owned-artifacts', 'owner-reconcile'}
            or task.get('execution') == 'owner'
            or type(task.get('network', False)) is not bool or task.get('network')
            or 'organize-authorized-refs' in operations):
        raise Refusal('unknown or external original resource authority remains held')
    ordinary = task.get('admitted_scope', {}).get('ordinary_effects')
    if ordinary is not None and not isinstance(ordinary, dict):
        raise Refusal('opaque original ordinary authority')
    if 'execute-admitted-qa' in operations and (not ordinary or ordinary.get('kind') != 'local-qa'):
        raise Refusal('unmapped original QA operation remains held')
    if ordinary and (ordinary.get('kind') != 'local-qa' or 'execute-admitted-qa' not in operations):
        raise Refusal('unknown original external/ref operation remains held')
    if task['effects'] == 'none' and (writes or task['sandbox'] != 'read-only'):
        raise Refusal('inconsistent original read-only authority')
    if task['effects'] == 'owned-artifacts' and (writes or task['sandbox'] != 'workspace-write'):
        raise Refusal('unmapped original owned-artifact authority')
    reads = [*reads, task['cwd']]
    writes = list(writes)
    if task.get('routine_completion'):
        targets = task['routine_completion'].get('targets') if isinstance(task['routine_completion'], dict) else None
        if (not isinstance(targets, list) or not targets
                or any(not isinstance(p, str) or not any(Path(p).is_relative_to(Path(w)) for w in writes) for p in targets)):
            raise Refusal('unmapped original canonical publication targets')
    if (task['sandbox'] == 'workspace-write' and task['effects'] == 'owner-reconcile'
            and not task.get('routine_completion')):
        writes.append(task['cwd'])
    # Check the whole map lexically before touching any of its metadata.
    for value in reads + writes:
        root(value, exclusions, metadata=False)
    return ([root(p, exclusions, metadata=metadata) for p in reads],
            [root(p, exclusions, metadata=metadata) for p in writes])


# Exact inspected public caller output contract; no producer-label exemption.
RESOURCE_CALLER_SHA256 = '7d8be231fbdee40761128b07b969244b7c799220190858cfc57b0cb97f3616b5'


def original_resources(runtime, identity, task):
    return _native_resources(runtime, identity, task)[:2]


def _native_resources(runtime, identity, task):
    """Project an original standalone software Source, without reading its return.

    This is authority comparison, not collection or native sandbox certification.
    The original rights survive an interrupted/return-unavailable context.
    Only the current capability's originally selected standalone packet is mapped;
    branch contexts and opaque native owners retain the generic refusal. All SQL
    projections below are authority/material metadata, never source text, diff,
    answer, receipt, attempt result or the contents of a native handle.
    The caller holds the cooperative transaction and validates the whole map
    against exclusions before acquiring any filesystem metadata.
    """
    from . import configuration, prospective
    from .reviews import BINDING
    if not runtime.db.in_transaction or not runtime.processing or not runtime.processing.boards:
        raise Refusal('original Source mapping requires current cooperative software authority')
    operations = task['effect_authority']['operations']
    if (task.get('sandbox') != 'read-only' or task.get('effects') != 'none'
            or task.get('network') is not False or task['effect_authority']['write_roots'] != []
            or not isinstance(operations, list) or not operations
            or set(operations) - {'read-source', 'read-reports', 'prepare-intents', 'consolidate-reports'}
            or task.get('routine_completion') or task.get('admitted_scope', {}).get('ordinary_effects')):
        raise Refusal('unknown or external original resource authority remains held')
    job = runtime.one('SELECT id,role,phase,task,package,active_attempt,state,hold_reason,members FROM jobs WHERE id=?', (identity['id'],))
    if (not job or job['task'] != identity['task'] or job['role'] != 'Reviews'
            or job['phase'] != 'proposer' or job['package'] is not None
            or not job['active_attempt']):
        raise Refusal('original standalone software Source required')
    canonical_uuid(job['active_attempt'])
    attempt = runtime.one("SELECT job,kind,controller,profile,binding,state,exit,ended,collected,capture,"
        "json_extract(detail,'$.processing_capability') AS capability,"
        "json_type(detail,'$.software_authority') AS software_type,"
        "json_extract(detail,'$.software_authority') AS software FROM attempts WHERE id=?", (job['active_attempt'],))
    if (not attempt or attempt['kind'] != 'task' or attempt['job'] != job['id']
            or attempt['software_type'] != 'object' or not attempt['software']):
        raise Refusal('original software Source launch binding absent')
    if job['hold_reason'] is not None:
        # These are the existing service's exact incomplete-return custody
        # reasons. Their presence does not grant rights: every original binding
        # above still applies. Unknown/custom holds remain opaque. Numeric END
        # and collection here identify a returned attempt, never physical close.
        deferred = ('original Source incomplete; whole return retained in original attempt '
                    + job['active_attempt'] + ' and review call; sole report integration deferred')
        conserved = 'original Source incomplete; whole return conserved through sole report integration'
        if (job['hold_reason'] not in {deferred, conserved} or job['state'] != 'held'
                or attempt['state'] != 'collected'
                or attempt['ended'] is None or attempt['collected'] is None
                or attempt['capture'] != 'incomplete'):
            raise Refusal('unknown original Source hold remains opaque')
    proof = json.loads(attempt['software'])
    if not isinstance(proof, dict):
        raise Refusal('opaque original software Source launch proof')
    cap, selection = runtime.processing.current()
    if (attempt['capability'] != cap['id'] or cap['id'] != runtime.processing.key
            or cap['issuer'] != runtime.config['roles']['Work']['owner']
            or job['task'] not in selection['tasks'] or not proof.get('prospective_epoch')):
        raise Refusal('original Source processing capability changed')
    epoch = prospective.current(runtime, job['task'], proof['prospective_epoch'])
    position = prospective.job_position(runtime, job, epoch) if epoch else None
    if (not epoch or epoch['policy']['ordinary_effects'] is not False
            or position is None or position <= epoch['job_boundary']):
        raise Refusal('original Source epoch/birth absent or changed')
    configured = runtime.config['tasks'][job['task']]
    tasks = configuration.processing_tasks(runtime)
    same = runtime.one('SELECT json(task)=json(?) AS task, admission IS NULL AS admission '
        'FROM job_resource_policies WHERE job=?', (encode(configured), job['id']))
    if (configured.get('role') != 'Reviews' or configured.get('phase') != 'proposer'
            or configured.get('execution') != 'owner' or not same or not same['task'] or not same['admission']
            or json.loads(attempt['binding']) != BINDING
            or tasks is not None and job['task'] not in tasks):
        raise Refusal('original Source task/admission differs from current rights')
    # Standalone means genuinely absent original AND current admission. A later
    # config cannot turn a packaged/branch Source into this bounded case.
    if runtime.one('SELECT 1 AS present FROM admissions WHERE package=?', (job['package'],)):
        raise Refusal('standalone Source cannot inherit an admission')
    for role in ('Work', 'Reviews'):
        runtime.processing.boards[role].verify_authority(runtime)
    grant = runtime.processing.boards['Reviews'].software_authority(runtime, job['task'])
    expected = dict(grant_id=grant['id'], issued_by=grant['issued_by'], authority=grant['authority'],
        role_owner=grant['owner'], task_hash=digest(configured), admission_hash=None,
        prospective_epoch=epoch['id'], delegated_by=epoch['selection']['grantor'],
        delegation_authority=epoch['selection']['authority'], processing_capability=cap['id'])
    if (proof != expected or grant.get('prospective_epoch') != epoch['id']
            or task['effect_authority'].get('owner', configured['effect_authority']['owner']) != grant['owner']):
        raise Refusal('original Source software grant differs from its launch')
    members = json.loads(job['members'])
    if not isinstance(members, list) or len(members) != 1:
        raise Refusal('one original factual Source packet required')
    member = members[0]
    if not isinstance(member, dict) or not member.get('event') or not member.get('hash'):
        raise Refusal('original Source member identity/hash required')
    source = runtime.one("SELECT id,role,hold,hash,json_extract(payload,'$.kind') AS kind,"
        "json_extract(payload,'$.post') AS post,"
        "json_extract(payload,'$.branch_binding') AS branch FROM events WHERE id=?", (member['event'],))
    birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (member['event'],))
    if (not source or source['role'] != 'Reviews' or source['hold'] is not None
            or source['hash'] != member.get('hash') or not birth
            or birth['position'] <= max(epoch['event_boundary'], selection['basis']['event_boundary'])
            or not configuration.event_allowed(runtime, source) or source['branch'] is not None
            or not selection['future_intake'] or source['kind'] != 'board'
            or source['post'] <= selection['basis']['roles']['Reviews']['future_after']):
        raise Refusal('original Source member/birth/current input rights changed')
    policy = selection.get('service', {}).get('reviews', {}).get(job['task'])
    account = selection.get('service', {}).get('legacy_resources', {}).get('Reviews', {}).get('native_review_return', {})
    # The factual packet projection follows every member hold/hash/birth/right
    # check above. Even its metadata is unnecessary for a refused old input.
    original = runtime.one("SELECT json_extract(payload,'$.body.review') AS packet FROM events WHERE id=?", (member['event'],))
    packet = json.loads(original['packet']) if original and original['packet'] else None
    if (not policy or policy.get('caller_sha256') != RESOURCE_CALLER_SHA256
            or account.get('version') not in {'native-collected-review-v1','native-collected-partial-report-v1'}
            or account.get('source_task') != job['task'] or account.get('package', 'absent') is not None
            or account.get('grant') != grant['id'] or account.get('source_task_sha256') != digest(configured)
            or account.get('review_policy_sha256') != digest(policy) or account.get('packet_sha256') != digest(packet)
            or account.get('expires', 0) <= runtime.clock()):
        raise Refusal('original selected native Source policy/packet absent or changed')
    if (not isinstance(packet, dict) or set(packet) != {'component','origin','base','head','previous','answered_ids'}
            or packet['component'] != account.get('component')
            or any(not isinstance(packet[k], str) or not re.fullmatch('[a-f0-9]{40}', packet[k]) for k in ('base','head'))
            or packet['previous'] is not None and (not isinstance(packet['previous'], str)
                                                   or not re.fullmatch('[a-f0-9]{40}', packet['previous']))
            or not isinstance(packet['answered_ids'], list)
            or any(not isinstance(i, str) or not i.strip() for i in packet['answered_ids'])):
        raise Refusal('original immutable Source packet required')
    selected = policy['components'].get(packet['component'])
    if not selected or selected['origin'] != packet['origin']:
        raise Refusal('original selected Source component differs')
    roots = [Path(p) for p in task['effect_authority']['read_roots']] + [Path(task['cwd'])]
    paths = selected['paths'] + selected.get('relationship_paths', [])
    if (not paths or any(Path(p).is_absolute() or '..' in Path(p).parts for p in paths)
            or any(not any(p.is_relative_to(r) for r in roots) for p in
                [*[Path(selected['repository'])/p for p in paths],
                 *[Path(p) for p in policy['method_files']],
                 *[Path(p) for p in selected.get('prior_histories', {})]])):
        raise Refusal('original Source material exceeds frozen read authority')
    if runtime.one('SELECT 1 AS present FROM attempts a WHERE a.job=? AND '
            '(EXISTS (SELECT 1 FROM ordinary_runs r WHERE r.attempt=a.id) OR '
            'EXISTS (SELECT 1 FROM routine_runs r WHERE r.attempt=a.id)) LIMIT 1', (job['id'],)):
        raise Refusal('contradictory original ordinary/routine Source effects remain held')
    # Exclude all report/capture/body columns, including the embedded diff.
    fields = ('selected_task','packet','repository','method_files','prior_histories','history','read_authority','relationship_paths','history_sha256')
    call = runtime.one('SELECT component,collector,json_extract(packet,' + ','.join('?' for _ in fields) +
        ') AS material FROM review_calls WHERE attempt=?', (*['$.'+k for k in fields], job['active_attempt']))
    acquired = dict(zip(fields, json.loads(call['material']))) if call and call['material'] else {}
    context = runtime.one('SELECT component,capability,collector,profile,route,handle,state,created FROM review_contexts WHERE component=?', (packet['component'],))
    bound = runtime.one("SELECT json_extract(context,'$.head') AS head,json_extract(context,'$.history_hash') AS history_hash,"
        "json_extract(context,'$.component') AS component,json_extract(context,'$.capability') AS capability,"
        "json_extract(context,'$.collector') AS collector,json_extract(context,'$.profile') AS profile,"
        "json_extract(context,'$.route') AS route,json_extract(context,'$.handle') AS handle,"
        "json_extract(context,'$.created') AS created FROM review_call_contexts WHERE attempt=?", (job['active_attempt'],))
    if (not call or not context or not bound or call['component'] != context['component']
            or call['collector'] != attempt['controller'] or context['collector'] != attempt['controller']
            or context['capability'] != cap['id'] or context['profile'] != attempt['profile']
            or context['route'] != policy['routes'].get(attempt['profile']) or context['state'] not in {'opening','live','interrupted','closed'}
            or any(bound[k] != context[k] for k in ('component','capability','collector','profile','route','handle','created'))
            or bound['head'] != packet['previous']
            or acquired != dict(selected_task=job['task'], packet=packet, repository=selected['repository'],
                method_files=policy['method_files'], prior_histories=selected.get('prior_histories', {}),
                history=selected['history'], read_authority=selected['authority'],
                relationship_paths=selected.get('relationship_paths', []),history_sha256=bound['history_hash'])):
        raise Refusal('original Source material/context/collector differs')
    if job['hold_reason'] is not None and context['state'] not in {'interrupted','closed'}:
        raise Refusal('original incomplete-return hold lacks its interrupted context')
    sources = runtime.rows("SELECT s.key,json_extract(s.value,'$.git_blob') AS blob,"
        "json_extract(s.value,'$.sha256') AS sha256,json_extract(s.value,'$.bytes') AS bytes "
        "FROM review_calls c,json_each(c.packet,'$.source') s WHERE c.attempt=?", (job['active_attempt'],))
    if not sources:
        raise Refusal('missing original pinned Source material map')
    pins = {packet['base'],packet['head'],packet['previous']} - {None}
    for source in sources:
        pin, separator, name = source['key'].partition(':')
        path = Path(name)
        if (not separator or pin not in pins or not name or path.is_absolute() or '..' in path.parts
                or not any(path.is_relative_to(Path(p)) for p in paths)
                or not isinstance(source['blob'],str) or not re.fullmatch('[a-f0-9]{40}',source['blob'])
                or not isinstance(source['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',source['sha256'])
                or type(source['bytes']) is not int or source['bytes'] < 0):
            raise Refusal('original pinned Source material metadata differs')
    handle = Path(context['handle'])
    canonical_uuid(handle.name)
    if handle.parent != runtime.home/'review-handles' or not Path(selected['history']).is_relative_to(runtime.home/'review-history'):
        raise Refusal('unmapped original native handle/history namespace')
    facade = runtime.home/'review-inputs'/digest(packet['component'])/'material.json'
    reads = [*task['effect_authority']['read_roots'], task['cwd'], selected['repository'],
             policy['caller'], str(Path(__file__).with_name('review_reader.py')),
             *policy['method_files'], *selected.get('prior_histories', {}), selected['history']]
    lifetime = _native_lifetime(runtime, job, packet, context)
    histories = runtime.rows('SELECT h.path,h.state,h.after_hash,h.head FROM review_history_commits h '
        'JOIN attempts a ON a.id=h.attempt WHERE a.job=?', (job['id'],))
    # Applied alone is no blanket release: bind the exact original owned path,
    # head and append hash to the authenticated returned context. Unknown tails
    # remain writes, even after actual physical close.
    pending = [h['path'] for h in histories if not (
        lifetime in {'answered', 'closed'} and h['state'] == 'applied'
        and h['path'] == selected['history'] and h['head'] == packet['head']
        and h['after_hash'] == lifetime_context_hash(runtime, context['component']))]
    if lifetime == 'closed':
        return [], pending, True
    writes = [str(handle), str(facade),
              *[str(facade.with_suffix(s)) for s in ('.pending','.cursor','.item')], *pending]
    # An answered call has finished its executor append. The continuing native
    # reader may still own async work: answered is NOT whole-root settlement.
    if lifetime != 'answered':
        writes.append(selected['history'])
    return reads, writes, False


def lifetime_context_hash(runtime, component):
    return runtime.one('SELECT history_hash FROM review_contexts WHERE component=?', (component,))['history_hash']


def _native_lifetime(runtime, job, packet, context):
    """Original protocol evidence, never state/effects/age as a release rule.

    Project only fixed control fields. No full answer, handle body, receipt
    body, material body or caller output is acquired by this comparison.
    A tagged answer ends the executor turn, not native asynchronous custody.
    """
    from .reviews import answered, closed
    current = runtime.one('SELECT run,head,history_hash,closed_at FROM review_contexts WHERE component=?',
                          (context['component'],))
    original = runtime.one("SELECT json_extract(context,'$.run') AS run FROM review_call_contexts WHERE attempt=?", (job['active_attempt'],))
    attempts = runtime.rows("SELECT id,state,ended,collected FROM attempts WHERE job=? AND kind='task'", (job['id'],))
    status = runtime.one('SELECT state,begin,ended,collected,exit,capture,error,session FROM attempts WHERE id=?',
                         (job['active_attempt'],))
    if (not current or not current['run'] or not original or original['run'] != current['run']
            or not attempts or not status
            or any(a['state'] != 'collected' or a['ended'] is None or a['collected'] is None for a in attempts)):
        if context['state'] == 'closed':
            raise Refusal('closed label without original executor collection remains held')
        return 'active'
    # Fixed projections reproduce the existing public predicates, including
    # exact types, absence/false distinctions and whole close accounting.
    turn_fields = ('class','run','consumer_errors','turn.input','turn.admitted','turn.answer_present',
        'turn.linked_messages','turn.ack.message_id','turn.turn_end.event','turn.turn_end.input',
        'turn.turn_end.stop_reason','turn.turn_end.child','turn.root_ended','turn.refused','turn.rejected',
        'turn.ref','transport.errors','transport.attached.frontdoor','transport.attached.run',
        'transport.attached.backlog_dropped_total','transport.attached.interrupted_records_total',
        'collection.errors','collection.stdout_eof','collection.stderr_eof','collection.exit')
    close_fields = ('class','run','physical_close','root','consumer_errors','account_errors',
        'collection.eof','collection.errors','front_door_terminal.run','front_door_terminal.entry_status',
        'front_door_terminal.exit','front_door_terminal.collection_errors','front_door_terminal.killed',
        'front_door_terminal.retire.ok','front_door_terminal.retire.stop',
        'front_door_terminal.live.backlog_dropped_total','owner_terminal.status','async.errors',
        'async.unsettled','async.undelivered')
    fields = tuple(dict.fromkeys(turn_fields + close_fields))
    paths = ['$.receipt.' + k for k in fields]
    query = ("SELECT json_type(t.value) AS kind,json_type(t.value,'$.close_intent') AS intent,"
        "json_type(t.value,'$.actual_END') AS code_type,json_type(t.value,'$.close_actual_END') AS close_type,"
        "json_type(t.value,'$.receipt.turn.turn_end.child') AS child_type,"
        "json_extract(t.value,'$.actual_END') AS code,json_extract(t.value,'$.close_actual_END') AS close_code,"
        "json_type(t.value,'$.full_answer')='text' AND json_valid(json_extract(t.value,'$.full_answer')) AS answer,"
        'json_extract(t.value,' + ','.join('?' for _ in paths) + ') AS control '
        'FROM review_calls c,json_each(c.receipt) t WHERE c.attempt=? ORDER BY CAST(t.key AS INTEGER)')
    turns = runtime.rows(query, (*paths, job['active_attempt']))
    receipts = []
    for turn in turns:
        if turn['kind'] != 'object' or not turn['control']:
            raise Refusal('opaque original control evidence remains held')
        receipt = {}
        for path, value in zip(fields, json.loads(turn['control'])):
            target = receipt
            keys = path.split('.')
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            # Preserve missing optional child as absent, as answered requires.
            if value is not None:
                target[keys[-1]] = value
        if turn['child_type'] is not None:
            receipt.setdefault('turn', {}).setdefault('turn_end', {})['child'] = None
        receipts.append((turn, receipt))
    if context['state'] == 'closed':
        if (current['closed_at'] is None or len(receipts) < 2
                or receipts[-2][0]['intent'] != 'text' or receipts[-1][0]['close_type'] != 'integer'
                or not closed(receipts[-1][0]['close_code'], receipts[-1][1], current['run'])):
            raise Refusal('closed label lacks authenticated original physical close/whole accounting')
        return 'closed'
    if (context['state'] != 'live' or status['state'] != 'collected' or status['begin'] is None
            or status['exit'] != 0 or status['capture'] != 'complete' or status['error']
            or status['session'] != current['run'] or current['head'] != packet['head']
            or not receipts or any(t['code_type'] != 'integer' or t['intent'] or t['close_type'] is not None
                or not answered(t['code'], r, 'present' if t['answer'] else None, current['run'],
                                opening=r.get('turn', {}).get('input') == 0) for t,r in receipts)):
        return 'active'
    call = runtime.one('SELECT state FROM review_calls WHERE attempt=?', (job['active_attempt'],))
    history = runtime.one('SELECT path,state,after_hash,head FROM review_history_commits WHERE attempt=?',
                          (job['active_attempt'],))
    if (not call or call['state'] != 'collected' or not history or history['state'] != 'applied'
            or history['head'] != packet['head'] or history['after_hash'] != current['history_hash']):
        return 'active'
    return 'answered'




def original_modes(runtime, job):
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        return _original_modes(runtime, job)


def _original_modes(runtime, job):
    """Project only the immutable access map; never acquire old task/return bodies.

    Missing originals refuse. Neither a current configuration/admission nor a
    permanent execution fence can restamp retained publication/effect debt.
    """
    fields = ('cwd', 'sandbox', 'effects', 'network', 'execution', 'require_package_scope',
              'scope_roots', 'package_narrowing', 'scope_exclusions',
              'linked_repositories', 'repository_reads')
    paths = ['$.' + k for k in fields] + ['$.effect_authority.' + k for k in ('read_roots', 'write_roots', 'operations')]
    prefix = '$.task_scopes.' + json.dumps(job['task'])
    scope_fields = ('cwd', 'read_roots', 'write_roots', 'network', 'procedure', 'repository_reads')
    scope_paths = [prefix + '.' + k for k in scope_fields] + [prefix + '.ordinary_effects.kind']
    receipt = "json_extract(admission,'$.receipt')"
    frozen = runtime.one('SELECT json_extract(task,' + ','.join('?' for _ in paths) + ') AS access, '
        "json_type(task,'$.routine_completion') AS completion, json_extract(task,'$.routine_completion.targets') AS targets, "
        'json_extract(' + receipt + ',' + ','.join('?' for _ in scope_paths) + ') AS scope, '
        'json_type(' + receipt + ',?) AS ordinary, '
        'length(json_extract(' + receipt + ',?))>0 AS evidence '
        'FROM job_resource_policies WHERE job=?', (*paths, *scope_paths, prefix + '.ordinary_effects', prefix + '.resource_evidence', job['id']))
    if not frozen or not frozen['access']:
        raise Refusal('missing original frozen resource map')
    values = json.loads(frozen['access'])
    task = {k: v for k, v in zip(fields, values) if v is not None}
    task['effect_authority'] = dict(zip(('read_roots', 'write_roots', 'operations'), values[len(fields):]))
    if frozen['completion'] not in {None, 'null', 'object'}:
        raise Refusal('unknown original publication map')
    if frozen['completion'] == 'object':
        task['routine_completion'] = {'targets': json.loads(frozen['targets']) if frozen['targets'] else None}
    admission = None
    if task.get('require_package_scope'):
        if not frozen['scope'] or not frozen['evidence']:
            raise Refusal('missing original admitted resource map')
        values = json.loads(frozen['scope'])
        scope = {k: v for k, v in zip(scope_fields, values) if v is not None}
        # Only presence is needed by scoped_task; no old evidence body is read.
        scope['resource_evidence'] = True
        if frozen['ordinary'] not in {None, 'null', 'object'}:
            raise Refusal('opaque original ordinary operation')
        if frozen['ordinary'] == 'object':
            scope['ordinary_effects'] = {'kind': values[-1]}
        admission = {'receipt': json.dumps({'task_scopes': {job['task']: scope}})}
        if scope_excluded(runtime, job['task'], admission, task=task):
            raise Refusal('original admitted scope excluded before metadata')
        for value in scope.get('read_roots', []) + scope.get('write_roots', []) + [scope.get('cwd')]:
            root(value, runtime.config.get('artifact_exclusions', []), metadata=False)
    if scope_excluded(runtime, job['task'], admission, task=task):
        raise Refusal('original configured scope excluded before metadata')
    task = scoped_task(job['task'], task, admission)
    native = task.get('execution') == 'owner'
    if native:
        reads, writes, native_closed = _native_resources(runtime, job, task)
    else:
        reads, writes = access_modes(task, runtime.config.get('artifact_exclusions', []), metadata=False)
    # The runtime creates fresh per-attempt writable staging; these original
    # directories stay charged without acquiring their names, contents or sizes.
    staging = []
    if (native and not native_closed) or (not native and task['effects'] != 'none'):
        for attempt in runtime.rows("SELECT id FROM attempts WHERE job=? AND kind='task'", (job['id'],)):
            canonical_uuid(attempt['id'])
            staging.append(root(str(runtime.home/'artifacts'/attempt['id']), runtime.config.get('artifact_exclusions', []), metadata=False))
            if native:
                # Opening attempts own this possible handle too. It is never
                # part of the unique artifacts-child staging exemption.
                writes.append(str(runtime.home/'review-handles'/attempt['id']))
        writes.extend(staging)
    # A retained publication is a write dependency even after execution closure.
    for item in runtime.rows('SELECT p.target,p.temp FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=?', (job['id'],)):
        for value in (item['target'], item['temp']):
            if value is not None:
                writes.append(root(value, runtime.config.get('artifact_exclusions', []), metadata=False))
    # Native model read-only rights still have executor writes. Validate the
    # entire assembled map (including publication temporaries) before metadata.
    exclusions = runtime.config.get('artifact_exclusions', [])
    for value in reads + writes:
        root(str(value), exclusions, metadata=False)
    return ([root(str(p), exclusions) for p in reads],
            [root(str(p), exclusions) for p in writes], staging)


def validate(runtime, policy, selection=None):
    for role, record in policy.items():
        if (role not in runtime.config['roles'] or not isinstance(record, dict)
                or set(record) - {'qa_operation', 'qa_operations', 'reviews_report', 'native_review_return'} != {'original_hold', 'roots', 'unbounded', 'evidence'}
                or type(record['unbounded']) is not bool or not isinstance(record['roots'], list)):
            raise Refusal('legacy resource account needs exact hold, roots, unbounded and evidence')
        if runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))['legacy_hold'] != record['original_hold']:
            raise Refusal('resource account does not describe the actual retained hold')
        required_text(record['evidence'], 'supported original resource scope, not a renamed package')
        if not record['unbounded'] and not record['roots']:
            raise Refusal('unknown legacy scope cannot be declared independent')
        for value in record['roots']:
            root(value, runtime.config.get('artifact_exclusions', []), metadata=False)
        for value in record['roots']:
            root(value, runtime.config.get('artifact_exclusions', []))
        accounts = qa_accounts(record)
        if accounts:
            packages = []
            for account in accounts:
                qa_observation(runtime, role, record, account)
                binding = account['binding']
                packages.append(binding['package'])
                if selection is not None and 'topic' in binding:
                    scope = selection.get('software_admission', {}).get('scopes', {}).get(binding['topic'])
                    if (not scope or digest(scope) != binding['scope_sha256']
                            or not binding['package'].startswith(scope['package_prefix'])
                            or scope['task_scopes'].get('qa-execution') != account['policy']['scope']
                            or account.get('cleanup') and scope['task_scopes'].get('qa-cleanup') != account['cleanup']['scope']):
                        raise Refusal('QA policy must bind exact selected software topic/scopes')
            if len(packages) != len(set(packages)):
                raise Refusal('independent QA policies need distinct packages')
        if 'native_review_return' in record:
            from .native_review_scope import validate as validate_native
            validate_native(runtime, role, record, selection)
        if 'reviews_report' in record:
            from .report_scope import validate as validate_report
            validate_report(runtime, role, record, selection)



def scope_excluded(runtime, name, admission, *, task=None):
    task = runtime.config['tasks'][name] if task is None else task
    scope = json.loads(admission['receipt']).get('task_scopes', {}).get(name, {}) if admission else {}
    exclusions = [*runtime.config.get('artifact_exclusions', []), *task.get('scope_exclusions', [])]
    # Ceilings/topology are lexical operands too, before scoped_task can follow
    # ancestry, associated Git topology or any admitted operand's symlinks.
    for value in [*exclusions, *task.get('scope_roots', []),
                  *(p[k] for p in task.get('linked_repositories', []) for k in ('repository','common_git'))]:
        _lexical_root(value)
    authority = task.get('effect_authority', {})
    configured = [*authority.get('read_roots', []), *authority.get('write_roots', []), task['cwd']]
    for value in configured:
        _lexical_root(value)
    # A ceiling may contain excluded descendants while the actual admitted
    # scope is disjoint. Validate its spelling, then compare the effective
    # requested operands; do not turn a ceiling into an actual broad read.
    if task.get('require_package_scope') and scope:
        values = scope.get('read_roots', []) + scope.get('write_roots', [])
        values += [scope[k] for k in ('cwd', 'procedure') if k in scope]
    else:
        values = configured
    try:
        for value in values:
            root(value, exclusions, metadata=False)
    except Refusal:
        return True
    return False


def qa_accounts(record):
    if 'qa_operations' in record:
        values = record['qa_operations']
        # Five executing + one accepted cleanup + one waiting execution need
        # seven exact package accounts, without increasing either phase slot.
        if ('qa_operation' in record or not isinstance(values, list) or not 1 <= len(values) <= 7):
            raise Refusal('one to seven independent selected QA operation policies required')
        return values
    return [record['qa_operation']] if 'qa_operation' in record else []


def qa_observation(runtime, role, record, account=None):
    """Validate Work's attributed evidence and exact proposed policy, not authorship.

    This structural check also runs before issuance. Only qa_operation, through
    the current trusted Work capability, can apply it. Digests bind bytes; they
    cannot prove native authorship or the truth/completeness of external facts.
    """
    account = record['qa_operation'] if account is None else account
    if (role != 'QA' or record['unbounded'] is not True
            or not isinstance(account, dict) or set(account) - {'cleanup'} != {'statement', 'binding', 'policy'}):
        raise Refusal('operation-relative QA policy must preserve global unknown scope')
    statement, binding, policy = (account[k] for k in ('statement', 'binding', 'policy'))
    fields = {'version', 'custodian', 'reference', 'statement_sha256', 'authority',
              'expires', 'scope', 'source', 'inputs', 'relevant_roots'}
    if (not isinstance(policy, dict) or set(policy) != fields or policy['version'] != 'qa-operation-v1'
            or not isinstance(statement, dict) or not statement
            or policy['statement_sha256'] != digest(statement)):
        raise Refusal('whole attributed observation and exact selected policy required')
    enrollment = runtime.one('SELECT owner,legacy_hold FROM enrollments WHERE role=?', (role,))
    if (not enrollment or policy['custodian'] != enrollment['owner']
            or record['original_hold'] != enrollment['legacy_hold']):
        raise Refusal('observation policy differs from actual retained QA custodian/hold')
    for key in ('reference', 'authority'):
        required_text(policy[key], 'accountable Work observation ' + key, 4000)
    if (type(policy['expires']) not in {int, float} or not math.isfinite(policy['expires'])
            or policy['expires'] <= runtime.clock()):
        raise Refusal('operation-relative selection expired')
    if (not isinstance(binding, dict) or set(binding) not in ({'task', 'package', 'admission_sha256'}, {'task', 'package', 'topic', 'scope_sha256'})
            or binding['task'] != 'qa-execution'):
        raise Refusal('one exact admitted QA execution binding required')
    required_text(binding['package'], 'actual independently admitted package')
    pin = binding.get('admission_sha256', binding.get('scope_sha256'))
    if 'topic' in binding:
        required_text(binding['topic'], 'selected software admission topic', 128)
    if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
        raise Refusal('exact whole admission digest required')
    source = policy['source']
    if (not isinstance(source, dict) or set(source) != {'common_git', 'tree', 'parents'}
            or not isinstance(source['tree'], str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', source['tree'])
            or not isinstance(source['parents'], list) or len(source['parents']) > 32
            or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', v) for v in source['parents'])
            or not isinstance(policy['scope'], dict)
            or not isinstance(policy['inputs'], list) or len(policy['inputs']) > 32
            or not isinstance(policy['relevant_roots'], list) or len(policy['relevant_roots']) > 32):
        raise Refusal('exact finite QA source topology, scope and inputs required')
    exclusions = runtime.config.get('artifact_exclusions', [])
    # Proposed policy validation is lexical. Task-specific exclusions must run
    # in scoped_task before any selected input's filesystem metadata.
    root(source['common_git'], exclusions, metadata=False)
    for value in policy['relevant_roots']:
        root(value, exclusions, metadata=False)
    seen = set()
    for item in policy['inputs']:
        if (not isinstance(item, dict) or set(item) != {'path', 'sha256'}
                or not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
            raise Refusal('exact selected supporting input byte pins required')
        path = str(root(item['path'], exclusions, metadata=False))
        if path in seen:
            raise Refusal('duplicate selected QA input')
        seen.add(path)
    if 'cleanup' in account:
        cleanup = account['cleanup']
        if (not isinstance(cleanup, dict) or set(cleanup) != {'task', 'scope', 'procedure_sha256'}
                or cleanup['task'] != 'qa-cleanup' or not isinstance(cleanup['scope'], dict)
                or cleanup['scope'].get('ordinary_effects') or cleanup['scope'].get('network') is not False
                or not re.fullmatch('[0-9a-f]{64}', cleanup['procedure_sha256'])):
            raise Refusal('separate exact no-effect same-package cleanup scope required')
        for value in cleanup['scope'].get('read_roots', []) + cleanup['scope'].get('write_roots', []) + [cleanup['scope'].get('cwd'), cleanup['scope'].get('procedure')]:
            root(value, exclusions, metadata=False)
        task = runtime.config['tasks']['qa-cleanup']
        if not task.get('package_narrowing') or task['effects'] != 'owned-artifacts':
            raise Refusal('cleanup must narrow the existing report-only task')
        scoped_task('qa-cleanup', task, {'receipt': json.dumps({'task_scopes': {'qa-cleanup': cleanup['scope']}})})
    return statement


def qa_operation(runtime, row, record, account=None):
    """Compare a recorded bounded fact; return no grant, lease or acceptance.

    All paths are exclusion-checked before policy/tool/source metadata. Actual
    adapter source/export/collection/acceptance checks remain independently owed.
    """
    if not runtime.processing:
        raise Refusal('current Work selection required')
    cap, selected = runtime.processing.current()
    if (cap['issuer'] != runtime.config['roles']['Work']['owner']
            or row['task'] not in selected['tasks']
            or selected.get('service', {}).get('legacy_resources', {}).get('QA') != record
            or not runtime.processing.boards or 'Work' not in runtime.processing.boards):
        raise Refusal('exact current genuine Work-selected QA policy required')
    runtime.processing.boards['Work'].verify_authority(runtime)
    accounts = qa_accounts(record)
    if account is None:
        matches = [a for a in accounts if a['binding']['package'] == row['package']]
        if len(matches) != 1:
            raise Refusal('one exact selected package operation required')
        account = matches[0]
    if account not in accounts:
        raise Refusal('unselected QA operation')
    qa_observation(runtime, row['role'], record, account)
    if row['task'] == 'qa-cleanup':
        return qa_cleanup(runtime, row, record, account)
    policy = account['policy']
    binding = account['binding']
    if (row['role'] != 'QA' or row['phase'] != 'execution'
            or row['task'] != binding['task'] or row['package'] != binding['package']):
        raise Refusal('QA observation does not describe this operation')
    task = runtime.config['tasks'][row['task']]
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    if 'topic' in binding:
        from .processing_admission import resolved
        admission = resolved(runtime, row['package'], binding['topic'], binding['scope_sha256'])
    if (not admission or 'admission_sha256' in binding and digest(admission) != binding['admission_sha256']
            or task['role'] != 'QA' or task['phase'] != 'execution'
            or not task.get('require_package_scope') or scope_excluded(runtime, row['task'], admission)):
        raise Refusal('unchanged genuine narrowed QA admission required before metadata')
    task = scoped_task(row['task'], task, admission)
    scope = task['admitted_scope']
    if (scope != policy['scope'] or task['network'] is not False
            or task['effect_authority']['owner'] != runtime.enrollment('QA')['owner']
            or task['effect_authority']['operations'] != ['execute-admitted-qa']):
        raise Refusal('selected observation cannot admit changed operation/scope/network/role')
    exclusions = runtime.config.get('artifact_exclusions', [])
    for path in scope['read_roots'] + scope['write_roots'] + [scope['cwd'], scope['procedure']]:
        root(path, exclusions)
    from . import prospective, ordinary
    epoch = prospective.current(runtime, row['task'])
    if not epoch or not epoch['policy']['ordinary_effects']:
        raise Refusal('current finite prospective QA authority required')
    p = scope.get('ordinary_effects', {})
    if (not isinstance(p, dict) or p.get('kind') != 'local-qa'
            or p.get('git') != '/usr/bin/git'
            or set(p.get('public_executables', {})) != {'command', 'readback'}
            or any(r.get('owner') != runtime.enrollment('QA')['owner'] for r in p.get('resources', []))):
        raise Refusal('only actual QA-owned local QA resources permitted')
    # Topology and supplementary inputs must be in the actual read ceiling;
    # their presence in evidence is not a path grant or a padding-root license.
    reads = [Path(v) for v in scope['read_roots']]
    for path in [policy['source']['common_git'], *[i['path'] for i in policy['inputs']]]:
        if not any(Path(path).is_relative_to(r) for r in reads):
            raise Refusal('selected QA evidence input is outside admitted read authority')
        root(path, exclusions)
    # A queue ID is not a job ID. Public policy validation supports a genuine
    # pre-reservation projection; never fabricate an attempt/birth/launch proof.
    current = runtime.one('SELECT id,role,phase,task,package,active_attempt,members FROM jobs WHERE id=?', (row.get('id'),))
    if current:
        if any(current[k] != row[k] for k in ('role', 'phase', 'task', 'package')):
            raise Refusal('original QA job identity differs')
        frozen = runtime.one('SELECT * FROM job_resource_policies WHERE job=?', (current['id'],))
        if (not frozen or json.loads(frozen['task']) != runtime.config['tasks'][row['task']]
                or not frozen['admission'] or json.loads(frozen['admission']) != admission):
            raise Refusal('original QA job resources cannot be rebound')
    policy_job = current if current and current['active_attempt'] else {
        k:row[k] for k in ('role', 'phase', 'task', 'package')}
    _, p = ordinary.policy_for(runtime, policy_job)
    for item in policy['inputs']:
        ordinary.frozen_file(runtime, item['path'], scope['read_roots'], item['sha256'])
    # Read-only current source/ref/topology checks. No checkout substitution,
    # source body export, native/provider invocation or effect replay.
    def git(*args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
        result = subprocess.run([p['git'], '--no-replace-objects', '--no-optional-locks',
                                 '-c', 'core.hooksPath=/dev/null', '-C', p['repository'], *args],
                                capture_output=True, check=True, timeout=p['timeout'], env=env)
        return result.stdout.decode('utf-8').strip()
    if git('rev-parse', '--show-toplevel') != p['repository']:
        raise Refusal('actual QA repository cwd changed')
    common = root(git('rev-parse', '--path-format=absolute', '--git-common-dir'), exclusions)
    if str(common) != policy['source']['common_git']:
        raise Refusal('actual common Git differs from observed QA operation')
    if (git('rev-parse', '--verify', p['source_ref'] + '^{commit}') != p['source_head']
            or git('rev-parse', '--verify', p['source_head'] + '^{tree}') != policy['source']['tree']
            or git('show', '-s', '--format=%P', p['source_head']).split() != policy['source']['parents']):
        raise Refusal('current exact QA source/ref/tree/ordered parent differs')
    # Foreign leases are mapped in blocked for every route, including Reviews.
    # Unmoded attributed relevant roots remain exclusive dependencies.
    return list(policy['relevant_roots'])


def blocked(runtime, row, task=None):
    # Serialize metadata, physical admission and protected authentication with
    # cooperative policy/hold/resource changes, including direct callers.
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        return _blocked(runtime, row, task)


def _blocked(runtime, row, task=None):
    if qa_branch_sequence(runtime.config) and row['task'] == 'branch-integrator':
        try:
            from .ordinary import branch_dependency
            branch_dependency(runtime, row)
        except (Refusal, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            return True
    enrollment = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (row['role'],))
    if not enrollment or not enrollment['legacy_hold']:
        return False
    task = task or runtime.config['tasks'][row['task']]
    if runtime.processing and row['phase'] == 'proposer' and task['effects'] == 'none':
        return False
    if not runtime.processing:
        return True
    selection = runtime.processing.current()[1]
    if row['role'] == 'Branch' and row['phase'] == 'integrator':
        admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
        try:
            if scope_excluded(runtime, row['task'], admission):
                return True
            exact = scoped_task(row['task'], task, admission)
            from .ref_scope import eligible
            if eligible(runtime, row, exact):
                return False
        except (Refusal, KeyError):
            pass  # Ordinary local/ref/network path rules below still refuse.
    record = selection.get('service', {}).get('legacy_resources', {}).get(row['role'])
    if not record or record['original_hold'] != enrollment['legacy_hold']:
        return True
    operation_held = []
    if qa_accounts(record):
        try:
            operation_held = qa_operation(runtime, row, record)
        except (Refusal, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
            return True
    elif 'native_review_return' in record:
        try:
            from .native_review_scope import preflight
            operation_held = preflight(runtime, row, record)
        except (Refusal, OSError, KeyError, TypeError, ValueError):
            return True
    elif 'reviews_report' in record:
        try:
            from .report_scope import eligible
            eligible(runtime, row, record)
        except (Refusal, OSError, KeyError, TypeError, ValueError):
            return True
    elif record['unbounded']:
        return True
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    # Independence needs a genuine narrowed admission, not a package label.
    if task.get('require_package_scope'):
        if not admission:
            return True
        if scope_excluded(runtime, row['task'], admission, task=task):
            return True
        task = scoped_task(row['task'], task, admission)
    elif not task.get('effect_authority'):
        return True  # No actual configured resource boundary to compare.
    if task.get('network') or 'organize-authorized-refs' in task['effect_authority'].get('operations', []):
        return True  # Path separation alone cannot prove external/shared-ref independence.
    exclusions = runtime.config.get('artifact_exclusions', [])
    try:
        reads, writes = access_modes(task, exclusions, metadata=False)
        for value in [*reads, *writes, *record['roots'], *operation_held, str(runtime.home/'artifacts')]:
            root(str(value), exclusions, metadata=False)
        reads, writes = ([root(str(p), exclusions) for p in reads],
                         [root(str(p), exclusions) for p in writes])
        future_staging = None
        if task['sandbox'] == 'workspace-write' and task['effects'] != 'none':
            directory = root(str(runtime.home/'artifacts'), exclusions)
            if row.get('active_attempt'):
                canonical_uuid(row['active_attempt'])
                directory /= row['active_attempt']
                writes.append(root(str(directory), exclusions))
            else:
                future_staging = directory
        held_reads = []
        held_writes = [root(p, exclusions) for p in record['roots'] + operation_held]
        original_staging = []
        mapped = {}

        def retain(job):
            if job['id'] not in mapped:
                mapped[job['id']] = original_modes(runtime, job)
                r, w, staging = mapped[job['id']]
                held_reads.extend(r)
                held_writes.extend(w)
                original_staging.extend(staging)

        # An orphan/opaque lease is globally unknown, even on a report route.
        for lease in runtime.rows('SELECT resource,attempt FROM ordinary_resources'):
            job = runtime.one('SELECT j.id,j.task FROM ordinary_runs r JOIN jobs j ON j.id=r.job WHERE r.attempt=?', (lease['attempt'],))
            if not job:
                return True
            if job['id'] == row.get('id'):
                continue
            path = '$.task_scopes.' + json.dumps(job['task']) + '.ordinary_effects'
            original = runtime.one('SELECT json(r.policy)=json(json_extract(json_extract(f.admission,\'$.receipt\'),?)) AS matches '
                'FROM ordinary_runs r JOIN job_resource_policies f ON f.job=r.job WHERE r.attempt=? '
                "AND EXISTS (SELECT 1 FROM json_each(r.policy,'$.resources') k WHERE json_extract(k.value,'$.key')=?)",
                (path, lease['attempt'], lease['resource']))
            if not original or not original['matches']:
                return True
            retain(job)
        if any(overlaps(a, b) for a in reads + writes for b in held_writes):
            return True
        # These scalar identities select immutable maps, never old return,
        # capture, error, receipt or full job/task bodies. UNKNOWN is unchanged.
        for job in runtime.rows("SELECT id,task FROM jobs WHERE effects NOT IN ('none','reconciled')"):
            if row.get('id') != job['id']:
                retain(job)
        # A returned/interrupted Source still owns its original call/context,
        # reader, history and output resources even if the executor's effect
        # column is none/reconciled. A preparation may fail before its call row:
        # an original owner attempt without an authentic map remains unknown.
        for job in runtime.rows('SELECT j.id,j.task FROM jobs j WHERE EXISTS ('
                'SELECT 1 FROM attempts a JOIN review_calls c ON c.attempt=a.id WHERE a.job=j.id) OR '
                'EXISTS (SELECT 1 FROM job_resource_policies f JOIN attempts a ON a.job=f.job '
                "WHERE f.job=j.id AND a.kind='task' AND json_extract(f.task,'$.execution')='owner')"):
            if row.get('id') != job['id']:
                retain(job)
        # Effect reconciliation alone cannot clear an interrupted or incomplete
        # publication. These scalar state predicates acquire no receipt bodies.
        for job in runtime.rows('SELECT j.id,j.task FROM jobs j WHERE '
                "EXISTS (SELECT 1 FROM attempts a JOIN routine_runs r ON r.attempt=a.id WHERE a.job=j.id AND r.state IS NOT 'reconciled') OR "
                "EXISTS (SELECT 1 FROM attempts a JOIN file_publications p ON p.attempt=a.id WHERE a.job=j.id AND (p.state IS NOT 'published' OR p.error IS NOT NULL))"):
            if row.get('id') != job['id']:
                retain(job)
        if future_staging:
            # A fresh attempt has a new PRIMARY KEY UUID and mkdir(exist_ok=False).
            # Its direct child cannot be an original attempt's directory. Broad
            # parent access and unmapped descendants still conflict; this is no
            # grant to write the artifacts parent or a release of old staging.
            for directory in original_staging:
                if directory.exists() and any(parent.exists() and directory.samefile(parent)
                        for parent in (future_staging, *future_staging.parents)):
                    return True  # An ancestor bind alias is not a distinct child.
            for held in held_reads + held_writes:
                if (not any(held.is_relative_to(p) for p in original_staging)
                        and overlaps(future_staging, held)):
                    return True
        conflict = not (reads or writes) or (any(overlaps(a, b) for a in writes for b in held_reads + held_writes)
                                        or any(overlaps(a, b) for a in reads for b in held_writes))
        if conflict:
            return True
        if 'native_review_return' in record:
            from .native_review_scope import _authenticate
            _authenticate(runtime, row, record)
        return False
    except (Refusal, OSError, KeyError, TypeError, ValueError, sqlite3.Error):
        return True


def qa_cleanup(runtime, row, record, account):
    """Consolidation consumes this accepted execution, never a model DONE."""
    from . import ordinary, prospective, qa_source
    from .report_scope import source_events, execution_report
    cleanup = account.get('cleanup')
    if not cleanup or row['phase'] != 'cleanup' or row['role'] != 'QA':
        raise Refusal('separately selected same-package cleanup required')
    epoch = prospective.current(runtime, row['task'])
    if not epoch or epoch['policy']['ordinary_effects'] is not False:
        raise Refusal('current no-effect consolidation authority required')
    rows = ordinary.accepted_runs(runtime, row['package'])
    qa = [r for r in rows if r['task'] == 'qa-execution']
    if len(qa) != 1:
        raise Refusal('all admitted ordinary results and one exact accepted same-package QA execution required')
    sequence = qa_branch_sequence(runtime.config)
    if sequence:
        ordinary.sequence_policies(runtime, row['package'])
    run = qa[0]
    original = runtime.job(run['job'])
    held = qa_operation(runtime, original, record, account)
    qa_source.verify(runtime, run['attempt'], json.loads(run['policy']), json.loads(run['receipt']))
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    if scope_excluded(runtime, row['task'], admission):
        raise Refusal('cleanup excluded before metadata')
    task = scoped_task(row['task'], runtime.config['tasks'][row['task']], admission)
    if (task['admitted_scope'] != cleanup['scope'] or task.get('network')
            or task['effect_authority']['owner'] != runtime.enrollment('QA')['owner']
            or set(task['effect_authority']['operations']) - {'read-source', 'read-reports', 'prepare-intents', 'consolidate-reports', 'write-owned-artifacts'}):
        raise Refusal('cleanup scope cannot acquire execution/native/effect authority')
    ordinary.frozen_file(runtime, cleanup['scope']['procedure'], cleanup['scope']['read_roots'], cleanup['procedure_sha256'])
    events = source_events(runtime, row)
    if not events:
        raise Refusal('actual complete execution reports required')
    if sequence:
        branch = [r for r in rows if r['task'] == 'branch-integrator']
        if len(branch) != 1 or len(events) != 1:
            raise Refusal('one accepted Branch result and its whole report required for final cleanup')
        branch = branch[0]
        branch_job = runtime.job(branch['job'])
        if branch_job['effects'] != 'reconciled' or branch_job['hold_reason'] or not ordinary.selected(runtime, branch_job):
            raise Refusal('accepted Branch result unresolved, held or no longer authorized')
        prospective.board(runtime, 'Branch')._software_job_grant(runtime, branch_job)
        _, policy = ordinary.policy_for(runtime, branch_job)
        if policy != json.loads(branch['policy']):
            raise Refusal('accepted Branch policy changed')
        ordinary.accepted_source_current(runtime, branch, policy)
        ordinary.accepted_report(runtime, events[0], branch, row['task'])
        # The Branch return must retain the complete QA envelope too.
        from .report_scope import conserved_inputs
        expected = encode({'collected_reports': conserved_inputs(runtime, branch_job)})
        if not any(encode(finding) == expected for finding in events[0]['body']['findings']):
            raise Refusal('final cleanup cannot omit the whole original QA report')
    else:
        for event in events:
            execution_report(runtime, event, original, row['task'])
    return held
