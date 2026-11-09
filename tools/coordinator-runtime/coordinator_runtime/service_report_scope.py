"""Prospective protected NONNATIVE service reports under retained old holds.

Selection authenticates a source/receiver contract, never fictional future
receipts. Each real whole report is authenticated again at receiving. Resource
comparison remains in resource_scopes; this module cannot clear any old hold.
"""
import json
import math

from .contracts import Refusal, digest, required_text, encode

VERSION = 'protected-service-report-v1'
FIELDS = {'version', 'authority', 'expires', 'configuration_sha256',
          'implementation_sha256', 'source_task', 'source_task_sha256',
          'review_policy_sha256', 'task', 'task_sha256', 'collector', 'recipient'}


def validate(runtime, role, record, selection=None):
    from . import opaque_review
    policy = record['service_report']
    if (role != 'Reviews' or record['unbounded'] is not True
            or any(k in record for k in ('reviews_report', 'native_review_return'))
            or not isinstance(policy, dict) or set(policy) != FIELDS
            or policy['version'] != VERSION
            or type(policy['expires']) not in {int, float} or not math.isfinite(policy['expires'])
            or policy['expires'] <= runtime.clock() or policy['task'] != 'reviews-integrator'
            or policy['source_task'] != 'reviews-proposer'):
        raise Refusal('exact prospective nonnative report contract with retained unbounded hold required')
    required_text(policy['authority'], 'genuine prospective Work report choice', 4000)
    source, receiver = (runtime.config['tasks'][policy[k]] for k in ('source_task', 'task'))
    if (policy['configuration_sha256'] != digest(runtime.config)
            or policy['source_task_sha256'] != digest(source) or policy['task_sha256'] != digest(receiver)
            or source['role'] != role or source['phase'] != 'proposer' or source.get('execution') != 'owner'
            or receiver['role'] != role or receiver['phase'] != 'integrator' or receiver['capacity'] != 1
            or receiver['effects'] != 'owned-artifacts' or receiver.get('network')
            or receiver.get('execution') == 'owner' or receiver.get('require_package_scope')
            or set(receiver['effect_authority']['operations']) - {'read-source', 'read-reports',
                'prepare-intents', 'consolidate-reports', 'write-owned-artifacts'}
            or policy['collector'] != runtime.controller
            or policy['recipient'] != runtime.config['roles'][role]['owner']):
        raise Refusal('current exact source/sole independent report receiver rights required')
    opaque_review.binding(source)
    if selection is not None:
        review = selection.get('service', {}).get('reviews', {}).get(policy['source_task'])
        if (not review or review.get('transport') != opaque_review.VERSION or not review.get('continuing')
                or policy['review_policy_sha256'] != digest(review)
                or policy['implementation_sha256'] != digest(selection['basis']['implementation'])
                or selection['basis']['configuration'] != policy['configuration_sha256']
                or selection['basis'].get('future_only') is not True or selection.get('future_intake') is not True
                or {policy['task'], policy['source_task']} - set(selection['tasks'])
                or policy['task'] not in selection['service'].get('report_tasks', [])):
            raise Refusal('same final source and future protected service selection required')
        from .review_composition import declaration
        declaration(review)
    return policy


def preflight(runtime, row, record):
    from . import prospective
    from .report_scope import source_metadata
    cap, selected = runtime.processing.current()
    policy = validate(runtime, row['role'], record, selected)
    if (cap['issuer'] != runtime.config['roles']['Work']['owner']
            or cap['id'] != runtime.processing.key or row['task'] != policy['task']
            or row['phase'] != 'integrator' or row['package'] is not None
            or selected['service']['legacy_resources'].get('Reviews') != record):
        raise Refusal('genuine Work current service report receiver required')
    held = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', ('Reviews',))
    if not held or not held['legacy_hold'] or held['legacy_hold'] != record['original_hold']:
        raise Refusal('exact retained original hold changed; no report waiver')
    epoch = prospective.current(runtime, row['task'])
    if (not epoch or epoch['policy']['ordinary_effects'] is not False
            or epoch['selection']['processing_capability'] != cap['id']):
        raise Refusal('current separate no-effect report analysis authority required')
    for role in ('Work', 'Reviews'):
        runtime.processing.boards[role].verify_authority(runtime)
    runtime.processing.boards['Reviews'].software_authority(runtime, row['task'])
    if row.get('active_attempt'):
        runtime.processing.boards['Reviews']._software_job_grant(runtime, row)
    source_metadata(runtime, row)
    return policy


def authenticate(runtime, row, record):
    """After real conflict guards, authenticate actual whole service originals."""
    from . import prospective, reviews
    from .report_scope import source_events, execution_report, fits_return
    policy = preflight(runtime, row, record)
    cap, selected = runtime.processing.current()
    reports = []
    for event in source_events(runtime, row):
        if (event.get('kind') != 'response' or event.get('role') != 'Reviews'
                or event.get('recipient') != policy['recipient'] or event.get('package') is not None
                or event.get('allowed_tasks') != [row['task']] or not event.get('source_job')):
            raise Refusal('whole assigned service report required; no attributed-message substitution')
        source = runtime.job(event['source_job'])
        if (source['task'] != policy['source_task'] or source['role'] != 'Reviews'
                or source['phase'] != 'proposer' or source['package'] is not None
                or source['id'] == row.get('id') or source['controller'] != policy['collector']):
            raise Refusal('exact separate original service source required')
        attempt = runtime.attempt(source['active_attempt'])
        detail = json.loads(attempt['detail'])
        epoch = prospective.for_job(runtime, source)
        position = prospective.job_position(runtime, source, epoch) if epoch else None
        frozen = runtime.one('SELECT task,admission FROM job_resource_policies WHERE job=?', (source['id'],))
        birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event['id'],))
        if (not epoch or epoch['selection']['processing_capability'] != cap['id']
                or epoch['policy']['ordinary_effects'] is not False
                or position is None or position <= epoch['job_boundary']
                or not birth or birth['position'] <= selected['basis']['event_boundary']
                or detail.get('processing_capability') != cap['id']
                or not frozen or frozen['admission'] is not None
                or encode(json.loads(frozen['task'])) != encode(runtime.config['tasks'][source['task']])):
            raise Refusal('fresh actual source capability/epoch/task rights required')
        runtime.processing.boards['Reviews']._software_job_grant(runtime, source)
        answer = execution_report(runtime, event, source, row['task'])
        proof = reviews.collected_proof(runtime, source, attempt)
        if (not proof or proof.get('kind') != 'selected-opaque-cli-review'
                or proof.get('native_owner_execution') is not False
                or proof.get('collector') != policy['collector']
                or proof.get('attempt') != attempt['id']):
            raise Refusal('actual protected nonnative source grade required; native has its own contract')
        if row.get('active_attempt'):
            receiver = runtime.attempt(row['active_attempt'])
            if receiver['session'] and receiver['session'] == attempt['session']:
                raise Refusal('report analysis must remain independent of source context')
        # Every original byte, protection grade, failure and nested duty travels
        # in conserved custody. No new answer can restamp or accept that source.
        receiver_epoch = prospective.current(runtime, row['task'])
        receipt = dict(version=VERSION, capability=cap['id'], source_epoch=epoch['id'],
            receiver_epoch=receiver_epoch['id'], collector=attempt['controller'],
            recipient=event['recipient'], attempt=attempt['id'], actual_END=attempt['exit'],
            capture=attempt['capture'], grade='protected-nonnative', native_owner_execution=False,
            source_task=source['task'], source_task_sha256=policy['source_task_sha256'],
            task=row['task'], task_sha256=policy['task_sha256'],
            configuration_sha256=policy['configuration_sha256'],
            implementation_sha256=policy['implementation_sha256'],
            meaning='authenticated whole original; new analysis and independent acceptance remain owed')
        reports.append(dict(event=event['id'], sha256=digest(event), original=event,
                            service_receipt=receipt))
    if not reports or not fits_return(runtime, reports, transport=True):
        raise Refusal('whole service report plus FULL independent analysis allowance must fit')
    return reports


def eligible(runtime, row, record):
    preflight(runtime, row, record)
    authenticate(runtime, row, record)


def resources(runtime, identity, task, record):
    """Frozen future ordinary source ceilings, before any return/body acquisition.

    This maps only the selected NEW capability's protected public task. Old
    owner/native jobs retain their own refusal/proof. No closed-state inference
    releases context, history, staging or publication dependencies.
    """
    from . import prospective
    from .resource_scopes import access_modes, root
    cap, selected = runtime.processing.current()
    policy = validate(runtime, 'Reviews', record, selected)
    job = runtime.one('SELECT id,task,role,phase,package,active_attempt,controller FROM jobs WHERE id=?', (identity['id'],))
    if (not job or job['task'] != policy['source_task'] or job['role'] != 'Reviews'
            or job['phase'] != 'proposer' or job['package'] is not None or not job['active_attempt']
            or job['controller'] != policy['collector']):
        raise Refusal('retained original is outside new protected service resource contract')
    epoch = prospective.for_job(runtime, job)
    position = prospective.job_position(runtime, job, epoch) if epoch else None
    frozen = runtime.one('SELECT task,admission FROM job_resource_policies WHERE job=?', (job['id'],))
    attempt = runtime.one("SELECT controller,json_extract(detail,'$.processing_capability') AS capability FROM attempts WHERE id=?", (job['active_attempt'],))
    if (not epoch or epoch['selection']['processing_capability'] != cap['id']
            or epoch['policy']['ordinary_effects'] is not False
            or position is None or position <= epoch['job_boundary']
            or not frozen or frozen['admission'] is not None
            or encode(json.loads(frozen['task'])) != encode(runtime.config['tasks'][job['task']])
            or not attempt or attempt['capability'] != cap['id'] or attempt['controller'] != policy['collector']):
        raise Refusal('original protected resource map lacks fresh exact launch rights')
    runtime.processing.boards['Reviews']._software_job_grant(runtime, job)
    call = runtime.one('SELECT component,collector FROM review_calls WHERE attempt=?', (job['active_attempt'],))
    if not call or call['collector'] != policy['collector']:
        raise Refusal('original protected context metadata unavailable')
    review = selected['service']['reviews'][job['task']]
    component = review['components'].get(call['component'])
    if not component:
        raise Refusal('original protected source component changed')
    # Removing the owner transport marker here is a resource projection only,
    # after exact frozen task/binding/grant checks. It grants no executor right.
    reads, writes = access_modes({**task, 'execution':'protected-resource-projection'},
                                runtime.config.get('artifact_exclusions', []), metadata=False)
    writes.append(root(component['history'], runtime.config.get('artifact_exclusions', []), metadata=False))
    return reads, writes, False
