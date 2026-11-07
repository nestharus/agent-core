"""Finite collected-report routes. Attribution is conserved, never new authority.

Work selects exact report bytes and configured input/output rights. The original
native method/context/collector and every legacy debt remain attributed input.
"""
import json
import math
from .contracts import Refusal, digest, encode, collected_task_result, required_text


def source_events(runtime, row):
    if row.get('id') and runtime.one('SELECT id FROM jobs WHERE id=?', (row['id'],)):
        members = json.loads(runtime.job(row['id'])['members'])
        events = []
        for member in members:
            event = runtime.event(member['event'])
            if digest(event) != member['hash']:
                raise Refusal('original whole report member changed')
            events.append(event)
    elif row.get('event'):
        events = [runtime.event(row['event'])]
    else:
        raise Refusal('exact collected report input required')
    for event in events:
        stored = runtime.one('SELECT hold,hash FROM events WHERE id=?', (event['id'],))
        if stored['hold'] or stored['hash'] != digest(event) or not runtime.processing.event(event):
            raise Refusal('report input held, changed or outside current authority')
    return events


def execution_report(runtime, event, job, destination):
    """Accept only the original service-generated, fully collected return."""
    from .software import collected_report
    from .contracts import response_tasks
    attempt = runtime.attempt(job['active_attempt'])
    answer = collected_task_result(attempt)
    if (job['response'] != event['id'] or event.get('source_job') != job['id'] or event.get('source_attempt') != attempt['id']
            or event.get('source_members') != json.loads(job['members']) or event.get('source_role') != job['role']
            or event.get('package') != job['package'] or event.get('body') != answer
            or event['id'] != digest({'response': attempt['id']})
            or event.get('allowed_tasks') != response_tasks(runtime.config['tasks'][job['task']], answer, runtime.config)
            or destination not in event['allowed_tasks'] or not collected_report(runtime, job, destination)):
        raise Refusal('authentic whole original execution report required')
    return answer


def validate(runtime, role, record, selection=None):
    policy = record['reviews_report']
    fields = {'version', 'authority', 'expires', 'task', 'task_sha256', 'reports'}
    if (role != 'Reviews' or record['unbounded'] is not True or not isinstance(policy, dict)
            or set(policy) != fields or policy['version'] != 'reviews-report-v1'
            or type(policy['expires']) not in {int, float} or not math.isfinite(policy['expires'])
            or policy['expires'] <= runtime.clock() or policy['task'] != 'reviews-integrator'):
        raise Refusal('finite Reviews report policy must preserve unbounded original hold')
    required_text(policy['authority'], 'actual Work finite report authority', 4000)
    task = runtime.config['tasks'][policy['task']]
    if (policy['task_sha256'] != digest(task) or task['role'] != role or task['phase'] != 'integrator'
            or task['effects'] != 'owned-artifacts' or task.get('network') or task.get('execution') == 'owner'
            or task.get('require_package_scope')
            or set(task['effect_authority']['operations']) - {'read-source', 'read-reports', 'prepare-intents', 'consolidate-reports', 'write-owned-artifacts'}):
        raise Refusal('exact current report-only sole integrator rights required')
    reports = policy['reports']
    if not isinstance(reports, list) or not 1 <= len(reports) <= 32:
        raise Refusal('finite exact fresh collected report set required')
    seen = set()
    for report in reports:
        if not isinstance(report, dict) or set(report) != {'reference', 'sha256'}:
            raise Refusal('report selection needs whole original receipt digest')
        required_text(report['reference'], 'exact collected report reference', 4000)
        import re
        if not isinstance(report['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', report['sha256']) or report['reference'] in seen:
            raise Refusal('distinct exact whole report pins required')
        seen.add(report['reference'])
    if selection is not None and policy['task'] not in selection.get('service', {}).get('report_tasks', []):
        raise Refusal('report resource policy requires actual selected public collection route')


def eligible(runtime, row, record):
    cap, selected = runtime.processing.current()
    validate(runtime, row['role'], record, selected)
    policy = record['reviews_report']
    if (cap['issuer'] != runtime.config['roles']['Work']['owner'] or row['task'] != policy['task']
            or row['phase'] != 'integrator' or row['package'] is not None
            or selected['service']['legacy_resources'].get('Reviews') != record):
        raise Refusal('exact Work-selected report operation required')
    from . import prospective
    epoch = prospective.current(runtime, row['task'])
    if not epoch or epoch['policy']['ordinary_effects'] is not False:
        raise Refusal('current no-effect software report integration authority required')
    for role in ('Work', 'Reviews'):
        runtime.processing.boards[role].verify_authority(runtime)
    pins = {p['reference']: p['sha256'] for p in policy['reports']}
    for event in source_events(runtime, row):
        body = event.get('body', {})
        receipt = body.get('original', {})
        frozen = runtime.one('SELECT * FROM processing_report_inputs WHERE event=?', (event['id'],))
        position = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event['id'],))
        if (not frozen or frozen['capability'] != cap['id'] or frozen['source_hash'] != digest(event)
                or frozen['receipt_hash'] != digest(receipt) or pins.get(receipt.get('reference')) != digest(receipt)
                or not position or position['position'] <= selected['basis']['event_boundary']
                or event.get('processing_report') != cap['id'] or event.get('author') != cap['issuer']
                or receipt.get('collector') != cap['issuer'] or body.get('kind') != 'attributed-report'
                or body.get('native_owner_execution') is not False or receipt.get('effects') != 'known-report-only'):
            raise Refusal('exact fresh genuinely collected public report input required; no message authority')


def conserved_inputs(runtime, row):
    """Whole envelopes for integration; no summary can erase original dissent."""
    events = source_events(runtime, row)
    return [{'event': e['id'], 'sha256': digest(e), 'original': e['body']} for e in events]


def integration_inputs(runtime, row):
    """Guard the selected route before prompt acquisition and supply exact bytes.

    A worker receives these inline envelopes, never access to the runtime journal
    or an instruction to reconstruct source hashes or investigate old captures.
    """
    if not runtime.processing:
        return None
    selected = runtime.processing.current()[1]
    record = selected.get('service', {}).get('legacy_resources', {}).get(row['role'], {})
    from .resource_scopes import qa_accounts, blocked
    applies = (row['task'] == 'reviews-integrator' and 'reviews_report' in record
               or row['task'] == 'qa-cleanup' and any(a.get('cleanup') and a['binding']['package'] == row['package']
                   for a in qa_accounts(record)))
    if not applies:
        return None
    if blocked(runtime, row):
        raise Refusal('current report operation authority/resources changed')
    return conserved_inputs(runtime, row)


def validate_result(runtime, row, result):
    reports = integration_inputs(runtime, row)
    if reports is not None:
        # Use the source pins' canonical JSON identity: Python equality conflates
        # booleans/numbers and numeric representations that encode distinctly.
        expected = encode({'collected_reports': reports})
        if not any(encode(finding) == expected for finding in result['findings']):
            raise Refusal('consolidation must conserve exact whole original report envelopes and qualifications')


def complete_return(reports):
    """A complete legal return shape, not manufactured reviewer reasoning.

    Used for exact admission/composition accounting. Workers may add analysis
    within the same actual result budget; all collection checks still apply.
    """
    return dict(semantic='DONE', category='consolidated',
                summary='Whole attributed reports conserved; original qualifications remain.',
                findings=[dict(collected_reports=reports)], failures=[], unknowns=[], artifacts=[])


def fits_return(runtime, reports):
    return len(encode(complete_return(reports)).encode()) <= runtime.config['limits']['max_result_bytes']


def bounded_members(runtime, row, rows):
    """Qualify every member before freezing, then pack whole envelopes in order.

    A nonfitting neighbor remains queued; it is never partially represented.
    All singleton receipts admitted by this source have a conforming return.
    Older nonfitting singletons remain conserved/refused under current limits.
    """
    if not runtime.processing or row['task'] != 'reviews-integrator':
        return rows
    record = runtime.processing.current()[1].get('service', {}).get('legacy_resources', {}).get('Reviews', {})
    if 'reviews_report' not in record:
        return rows
    chosen, reports = [], []
    for candidate in rows:
        try:
            eligible(runtime, candidate, record)
        except Refusal:
            if candidate['id'] == row['id']:
                raise
            continue
        incoming = conserved_inputs(runtime, candidate)
        if not fits_return(runtime, incoming):
            if candidate['id'] == row['id']:
                raise Refusal('whole report has no complete return within current selected result budget')
            continue
        if fits_return(runtime, reports + incoming):
            chosen.append(candidate)
            reports += incoming
    if not chosen:
        raise Refusal('no qualified complete report batch within current result budget')
    return chosen
