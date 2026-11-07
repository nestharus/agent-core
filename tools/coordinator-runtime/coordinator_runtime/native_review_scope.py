"""Finite current native return consolidation, preserving the original unknown hold.

No native invocation, effect permission, acceptance or historical hold clearance.
Resource evidence is an attributed Work/owner account, never inferred from names.
"""
import json
import math
from .contracts import Refusal, digest, encode, required_text


def validate(runtime, role, record, selection=None):
    p = record['native_review_return']
    fields = {'version', 'authority', 'expires', 'package', 'component', 'packet_sha256',
              'source_task', 'source_task_sha256', 'task', 'task_sha256',
              'review_policy_sha256', 'grant', 'resource_evidence', 'relevant_roots'}
    if (role != 'Reviews' or record['unbounded'] is not True or 'reviews_report' in record
            or not isinstance(p, dict) or set(p) != fields
            or p['version'] != 'native-collected-review-v1'
            or type(p['expires']) not in (int, float) or not math.isfinite(p['expires'])
            or p['expires'] <= runtime.clock()):
        raise Refusal('finite native consolidation must preserve unbounded original hold')
    for k in ('authority', 'package', 'component', 'resource_evidence'):
        required_text(p[k], 'actual current native consolidation ' + k, 4000)
    import re
    for k in ('packet_sha256', 'source_task_sha256', 'task_sha256', 'review_policy_sha256'):
        if not isinstance(p[k], str) or not re.fullmatch('[0-9a-f]{64}', p[k]):
            raise Refusal('exact current source/task/method pins required')
    source = runtime.config['tasks'].get(p['source_task'], {})
    task = runtime.config['tasks'].get(p['task'], {})
    if (p['task'] != 'reviews-integrator' or source.get('role') != role
            or source.get('phase') != 'proposer' or source.get('execution') != 'owner'
            or p['source_task_sha256'] != digest(source) or p['task_sha256'] != digest(task)
            or task.get('role') != role or task.get('phase') != 'integrator'
            or task.get('effects') != 'owned-artifacts' or task.get('sandbox') != 'workspace-write'
            or task.get('network') or task.get('execution') == 'owner' or task.get('routine_completion')
            or task.get('effect_authority', {}).get('write_roots') != []
            or task['effect_authority']['owner'] != runtime.one('SELECT owner FROM enrollments WHERE role=?', (role,))['owner']
            or set(task['effect_authority']['operations']) -
               {'read-source', 'read-reports', 'prepare-intents', 'consolidate-reports', 'write-owned-artifacts'}
            or p['grant'] != runtime.one('SELECT grant_id FROM enrollments WHERE role=?', (role,))['grant_id']):
        raise Refusal('exact original grant and output-only current source/consumer rights required')
    from .resource_scopes import root
    if not isinstance(p['relevant_roots'], list) or len(p['relevant_roots']) > 32:
        raise Refusal('finite actual conflicting resource account required')
    for value in p['relevant_roots']:
        root(value, runtime.config.get('artifact_exclusions', []), metadata=False)
    if selection is not None:
        policy = selection.get('service', {}).get('reviews', {}).get(p['source_task'])
        if (not policy or digest(policy) != p['review_policy_sha256']
                or p['component'] not in policy['components']
                or not {p['task'], p['source_task']} <= set(selection['tasks'])):
            raise Refusal('exact current selected native method/component required')


def eligible(runtime, row, record):
    from . import prospective, reviews, local_integration
    from .report_scope import source_metadata, source_events, execution_report
    cap, selected = runtime.processing.current()
    validate(runtime, row['role'], record, selected)
    p = record['native_review_return']
    if (cap['issuer'] != runtime.config['roles']['Work']['owner']
            or selected['service']['legacy_resources'].get('Reviews') != record
            or row['task'] != p['task'] or row['phase'] != 'integrator'
            or row['package'] != p['package']):
        raise Refusal('actual Work-selected same-case native consolidation required')
    for role in ('Work', 'Reviews'):
        runtime.processing.boards[role].verify_authority(runtime)
    epoch = prospective.current(runtime, row['task'])
    if not epoch or epoch['policy']['ordinary_effects'] is not False:
        raise Refusal('current finite no-effect consumer epoch required')
    # Check all current envelope/member metadata before any protected body read.
    sources = source_metadata(runtime, row)
    if len(sources) != 1:
        raise Refusal('one whole current native return per operation required')
    source = sources[0]
    pos = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (source['id'],))
    if not pos or pos['position'] <= selected['basis']['event_boundary']:
        raise Refusal('fresh current native return birth required')
    # Source job identity is selected from scalar envelope fields only.
    link = runtime.one("SELECT json_extract(payload,'$.source_job') AS job FROM events WHERE id=?", (source['id'],))
    if not link or not link['job']:
        raise Refusal('external or orphan report is not a native Source return')
    job = runtime.one('SELECT id,role,phase,task,package,hold_reason,effects,active_attempt FROM jobs WHERE id=?', (link['job'],))
    if (not job or job['role'] != 'Reviews' or job['phase'] != 'proposer' or job['task'] != p['source_task']
            or job['package'] != p['package'] or job['hold_reason']
            or job['effects'] not in ('none', 'reconciled') or not job['active_attempt']):
        raise Refusal('current unheld genuine native source job required')
    job = runtime.job(job['id'])
    originals = source_metadata(runtime, job)
    for original in originals:
        birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (original['id'],))
        if not birth or birth['position'] <= selected['basis']['event_boundary']:
            raise Refusal('fresh current source birth required before bodies')
    attempt = runtime.attempt(job['active_attempt'])
    runtime.processing.authorize(attempt)
    if not prospective.for_job(runtime, job):
        raise Refusal('original current source epoch/birth required')
    runtime.processing.boards['Reviews']._software_job_grant(runtime, job)
    if row.get('active_attempt'):
        consumer = runtime.job(row['id'])
        if consumer['hold_reason'] or not prospective.for_job(runtime, consumer):
            raise Refusal('current unheld consumer birth/task rights required')
        runtime.processing.authorize(runtime.attempt(row['active_attempt']))
    proof = reviews.collected_proof(runtime, job, attempt)
    if not proof or proof['material'].get('selected_task') != p['source_task']:
        raise Refusal('original collected native context required')
    context = runtime.one('SELECT capability,collector,run,state FROM review_contexts WHERE component=?', (proof['component'],))
    if (not context or context['capability'] != cap['id'] or context['collector'] != proof['collector']
            or context['run'] != proof['run'] or context['state'] != 'live'):
        raise Refusal('actual current original native context required')
    acquired = proof['material']
    current_policy = selected['service']['reviews'][p['source_task']]
    if acquired.get('method_files') != current_policy['method_files']:
        raise Refusal('original native method pins differ from current method')
    packet = acquired['packet']
    if packet['component'] != p['component'] or digest(packet) != p['packet_sha256']:
        raise Refusal('exact current component/source pins required')
    turns = proof['calls']
    if len(turns) < 2:
        raise Refusal('whole architecture and complete method stages required')
    for i, turn in enumerate(turns):
        returned = json.loads(turn['full_answer'])
        reviews.coverage(returned, packet, i == 0)
        if returned.get('semantic') != 'DONE' or returned.get('stage') != ('architecture' if i == 0 else 'complete'):
            raise Refusal('incomplete native procedure cannot acquire consolidation scope')
    expected = reviews.proposal_result(returned, proof['component'], acquired,
                                       proof['collector'], attempt['id'],
                                       json.loads(runtime.one('SELECT receipt FROM review_calls WHERE attempt=?', (attempt['id'],))['receipt']))
    events = source_events(runtime, row)
    event = events[0]
    local_integration.input_authority(runtime, event, row['task'], row['package'])
    answer = execution_report(runtime, event, job, row['task'])
    if encode(answer) != encode(expected):
        raise Refusal('whole original native return conservation required')
    return p['relevant_roots']
