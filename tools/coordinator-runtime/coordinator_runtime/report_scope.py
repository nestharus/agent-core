"""Finite collected-report routes. Attribution is conserved, never new authority.

Work selects exact report bytes and configured input/output rights. The original
native method/context/collector and every legacy debt remain attributed input.
"""
import json
import math
from contextlib import nullcontext
from .contracts import Refusal, digest, encode, collected_task_result, required_text


def source_metadata(runtime, row, *, current_authority=True):
    """Admit ALL members before a new synchronous source read group.

    Call again after await. Metadata refusal never cancels original collection
    or acquires a held body to explain why current custody cannot proceed.
    The caller serializes this group with cooperative hold updates.
    """
    if row.get('id') and runtime.one('SELECT id FROM jobs WHERE id=?', (row['id'],)):
        members = json.loads(runtime.job(row['id'])['members'])
    elif row.get('event'):
        members = [dict(event=row['event'])]
    else:
        raise Refusal('exact collected report input required')
    sources = []
    for member in members:
        stored = runtime.one('SELECT id,role,hold,hash FROM events WHERE id=?', (member['event'],))
        if not stored or stored['hold'] is not None:
            raise Refusal('report input held, changed or outside current authority')
        if 'hash' in member and stored['hash'] != member['hash']:
            raise Refusal('original whole report member changed')
        sources.append(stored)
    if runtime.processing and current_authority:
        from .configuration import event_allowed, processing_tasks
        _, selection = runtime.processing.current()
        tasks = processing_tasks(runtime)
        if row['task'] not in selection['tasks'] or (tasks is not None and row['task'] not in tasks):
            raise Refusal('report task outside current source authority')
        for source in sources:
            if source['role'] != row['role'] or not event_allowed(runtime, source):
                raise Refusal('report input held, changed or outside current authority')
            if source['id'] in selection.get('retained_events', []):
                originals = {e['id']: e['hash'] for role in selection['basis']['roles'].values()
                             for e in role['original']['events']}
                if originals.get(source['id']) != source['hash']:
                    raise Refusal('retained report input outside current source authority')
            receipt = runtime.one('SELECT capability,source_hash,receipt_hash FROM processing_report_inputs WHERE event=?', (source['id'],))
            if receipt:
                if receipt['capability'] != runtime.processing.key:
                    raise Refusal('report input outside current collection authority')
                policy = selection.get('service', {}).get('legacy_resources', {}).get(row['role'], {}).get('reviews_report')
                if (receipt['source_hash'] != source['hash'] or policy is not None
                        and receipt['receipt_hash'] not in {pin['sha256'] for pin in policy['reports']}):
                    raise Refusal('report input outside current finite source selection')
    return sources


def source_events(runtime, row):
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        sources = source_metadata(runtime, row)
        events = []
        for source in sources:
            event = runtime.event(source['id'])
            if digest(event) != source['hash']:
                raise Refusal('original whole report member changed')
            if runtime.processing and not runtime.processing.event(event):
                raise Refusal('report input held, changed or outside current authority')
            events.append(event)
        return events


def execution_report(runtime, event, job, destination):
    """Accept only the original service-generated, fully collected return."""
    from .software import collected_report
    from .contracts import response_tasks
    source_metadata(runtime, job)
    attempt = runtime.attempt(job['active_attempt'])
    answer = collected_task_result(attempt)
    validate_transport(runtime, job, event, answer)
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
    if runtime.processing and row['task'] == 'reviews-integrator':
        record = runtime.processing.current()[1].get('service', {}).get('legacy_resources', {}).get('Reviews', {})
        if 'service_report' in record:
            from .service_report_scope import authenticate
            return authenticate(runtime, row, record)
    events = source_events(runtime, row)
    return [dict(event=e['id'], sha256=digest(e), original=e['body'],
                 **({'report_custody': e['report_custody']} if 'report_custody' in e else {})) for e in events]


INTEGRATION_KIND = 'report-integration-v1'


def uses_transport(row):
    """QA retains its exact legacy template and whole-copy serialization."""
    return row['task'] == 'reviews-integrator'


def source_pins(reports):
    return [{'event': r['event'], 'sha256': r['sha256']} for r in reports]


def integration_protocol(runtime, row, reports):
    """Producer declaration, supplied before execution; never reviewer testimony."""
    return dict(kind=INTEGRATION_KIND, sources=source_pins(reports),
                task_sha256=digest(runtime.config['tasks'][row['task']]))


INSTRUCTIONS = (
    'REPORT TRANSPORT: software retains TASK_CONTEXT.collected_reports exactly once as '
    'immutable attributed source custody on the response; do not retransmit these bodies '
    'or adopt a file as your result. Return your NEW analysis in one findings entry with '
    'kind="report-integration-v1", sources and task_sha256 copied from '
    'TASK_CONTEXT.report_integration, analysis (nonempty text), decision (nonempty text), '
    'method (nonempty text explaining application of the supplied current method), '
    'coverage (one {event,sha256,extent,limits} per supplied source in order). '
    'extent is whole/partial/unread for that supplied envelope, NOT a claim to have read '
    'its referenced artifacts or underlying historical evidence; limits is a text list '
    'and must explain partial/unread. DONE requires whole current envelope coverage and '
    'genuinely finished new analysis. Original adverse/unknown facts and duties remain '
    'original; contradictory new assertions are separately attributed, never corrections '
    'of original bytes. Include new handoff intents only; inherited intents stay inert '
    'in source custody with their actual owners. No transport field supplies acceptance, '
    'native review, execution or receiving processing. Clarifications still conserve '
    'your own prior model return under the ordinary exact-prefix rules.\n')


def analysis_result(runtime, row, result, reports):
    """Recognize only explicit new semantics; legacy whole-copy returns still work.

    Coverage is the model's attributed declaration, not software proof of thought
    or of reading any nested source. Bind it to every actual current input.
    """
    entries = [f for f in result['findings'] if isinstance(f, dict) and f.get('kind') == INTEGRATION_KIND]
    if not entries:
        return False
    # Clarifications may preserve earlier assertions verbatim and append a new
    # current analysis. Never discard those earlier assertions to select one.
    current = entries[-1]
    protocol = integration_protocol(runtime, row, reports)
    if (set(current) != set(protocol) | {'analysis', 'decision', 'coverage', 'method'}
            or any(encode(current[k]) != encode(v) for k, v in protocol.items())):
        raise Refusal('report analysis needs exact current sources and method binding')
    required_text(current['analysis'], 'current report integration analysis', runtime.config['limits']['max_result_bytes'])
    required_text(current['decision'], 'current report integration decision', 16000)
    required_text(current['method'], 'current report integration method', 16000)
    coverage = current['coverage']
    if not isinstance(coverage, list) or len(coverage) != len(reports):
        raise Refusal('report analysis needs every current input coverage declaration')
    for item, pin in zip(coverage, source_pins(reports)):
        if (not isinstance(item, dict) or set(item) != {'event', 'sha256', 'extent', 'limits'}
                or any(encode(item[k]) != encode(v) for k, v in pin.items())
                or item['extent'] not in ('whole', 'partial', 'unread')
                or not isinstance(item['limits'], list)):
            raise Refusal('report coverage must bind exact current input and extent')
        for limit in item['limits']:
            required_text(limit, 'report coverage limit', 16000)
        if item['extent'] != 'whole' and (not item['limits'] or result['semantic'] == 'DONE'):
            raise Refusal('incomplete current report coverage cannot become DONE')
    if any(isinstance(f, dict) and 'collected_reports' in f for f in result['findings']):
        raise Refusal('new report protocol conserves originals in software custody once')
    return True


def transport_custody(runtime, row, result):
    """Software composition only. The collected model result is never rewritten."""
    if not uses_transport(row):
        return None
    reports = integration_inputs(runtime, row)
    if reports is None or not analysis_result(runtime, row, result, reports):
        return None
    return source_custody(runtime, row, result, reports)


def source_custody(runtime, row, result, reports):
    """Carry originals even on an informative incomplete return; never qualify it."""
    original = runtime.one('SELECT id,job,controller FROM attempts WHERE id=?', (row['active_attempt'],))
    if not original or original['job'] != row['id']:
        raise Refusal('custody requires the actual original job attempt collector')
    custody = dict(version=INTEGRATION_KIND, collector=original['controller'],
                   attempt=original['id'], model_result_sha256=digest(result),
                   collected_reports=reports)
    if len(encode(result).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('new model analysis exceed selected result budget')
    validate_envelope(runtime, dict(body=result, report_custody=custody))
    return custody


def transport_limit(runtime):
    return min(runtime.config['limits'].get('max_artifact_bytes', 33554432),
               runtime.config['limits']['max_bytes'])


def validate_envelope(runtime, value):
    """Measure the actual encoded software envelope, including every wrapper.

    Each journal/outbox write also retains its existing cumulative budget check;
    this per-envelope ceiling grants no storage reservation or source rights.
    """
    if len(encode(value).encode()) > transport_limit(runtime):
        raise Refusal('whole report transport exceeds existing artifact/global ceiling')


def selected_intake(runtime, event):
    """Only exact Work-selected originals can use the larger intake envelope."""
    if not runtime.processing:
        return False
    cap, selection = runtime.processing.current()
    receipt = event.get('body', {}).get('original', {}) if isinstance(event.get('body'), dict) else {}
    if not isinstance(receipt, dict):
        return False
    policy = selection.get('service', {}).get('legacy_resources', {}).get('Reviews', {}).get('reviews_report')
    if not policy:
        return False
    validate(runtime, 'Reviews', selection['service']['legacy_resources']['Reviews'], selection)
    return (event.get('processing_report') == cap['id'] and event.get('author') == cap['issuer']
            and event.get('role') == 'Reviews' and event.get('kind') == 'response'
            and event.get('recipient') == runtime.config['roles']['Reviews']['owner']
            and event.get('allowed_tasks') == [policy['task']]
            and event.get('id') == digest({'attributed_report': {'collector': cap['issuer'], 'reference': receipt.get('reference')}})
            and receipt.get('collector') == cap['issuer'] and receipt.get('effects') == 'known-report-only'
            and event['body'].get('kind') == 'attributed-report' and event['body'].get('native_owner_execution') is False
            and any(p['reference'] == receipt.get('reference') and p['sha256'] == digest(receipt) for p in policy['reports']))


def validate_large_event(runtime, event):
    """Authenticate the narrow selected exception to ordinary message sizing."""
    if not selected_intake(runtime, event):
        if event.get('kind') != 'response' or 'report_custody' not in event or not event.get('source_job'):
            return False
        job = runtime.job(event['source_job'])
        if not uses_transport(job) or len(event.get('allowed_tasks', [])) != 1:
            raise Refusal('large event requires exact selected report consumer')
        execution_report(runtime, event, job, event['allowed_tasks'][0])
    validate_envelope(runtime, event)
    return True


def incomplete_custody(runtime, row, result):
    if not uses_transport(row):
        return None
    reports = integration_inputs(runtime, row)
    if reports is None:
        return None
    # Legacy failures may already contain the exact whole source membership.
    # Do not attach another recursive copy or make their old valid budget fail.
    expected = encode({'collected_reports': reports})
    findings = result.get('findings', []) if isinstance(result, dict) else []
    if isinstance(findings, list) and any(encode(f) == expected for f in findings):
        return None
    return source_custody(runtime, row, result, reports)


def validate_transport(runtime, row, event, result):
    expected = transport_custody(runtime, row, result)
    if encode(event.get('report_custody')) != encode(expected):
        raise Refusal('original software report custody changed or omitted')
    if expected is not None:
        validate_envelope(runtime, event)


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
    applies = (row['task'] == 'reviews-integrator' and ('reviews_report' in record or 'native_review_return' in record or 'service_report' in record)
               or row['task'] == 'qa-cleanup' and any(a.get('cleanup') and a['binding']['package'] == row['package']
                   for a in qa_accounts(record)))
    if not applies:
        return None
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        source_metadata(runtime, row)
        if blocked(runtime, row):
            raise Refusal('current report operation authority/resources changed')
        return conserved_inputs(runtime, row)


def validate_result(runtime, row, result):
    reports = integration_inputs(runtime, row)
    if reports is not None:
        if uses_transport(row) and analysis_result(runtime, row, result, reports):
            transport_custody(runtime, row, result)
            return
        # Use the source pins' canonical JSON identity: Python equality conflates
        # booleans/numbers and numeric representations that encode distinctly.
        expected = encode({'collected_reports': reports})
        if not any(encode(finding) == expected for finding in result['findings']):
            raise Refusal('consolidation must conserve exact whole original report envelopes and qualifications')


def complete_return(reports):
    """Legacy complete whole-copy return shape, not reviewer reasoning.

    Kept for legacy serialization accounting. New selected transport admission
    reserves independent analysis headroom; all collection checks still apply.
    """
    return dict(semantic='DONE', category='consolidated',
                summary='Whole attributed reports conserved; original qualifications remain.',
                findings=[dict(collected_reports=reports)], failures=[], unknowns=[], artifacts=[])


def fits_return(runtime, reports, *, transport=False):
    if not transport:
        return len(encode(complete_return(reports)).encode()) <= runtime.config['limits']['max_result_bytes']
    # Reserve the FULL selected model allowance for useful new analysis. Source
    # bytes do not consume that allowance. The real response/outbox wrappers are
    # measured again at their actual write and receive boundaries.
    custody = dict(version=INTEGRATION_KIND, collector=runtime.controller,
                   attempt='0'*36, model_result_sha256='0'*64, collected_reports=reports)
    size = len(encode(dict(body=None, report_custody=custody)).encode()) - len('null')
    return size + runtime.config['limits']['max_result_bytes'] <= transport_limit(runtime)


def bounded_members(runtime, row, rows):
    """Qualify every member before freezing, then pack whole envelopes in order.

    A nonfitting neighbor remains queued; it is never partially represented.
    All singleton receipts admitted by this source have a conforming return.
    Older nonfitting singletons remain conserved/refused under current limits.
    """
    if not runtime.processing or row['task'] != 'reviews-integrator':
        return rows
    record = runtime.processing.current()[1].get('service', {}).get('legacy_resources', {}).get('Reviews', {})
    if 'native_review_return' in record:
        from .native_review_scope import eligible as native_eligible
        with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
            native_eligible(runtime, row, record)
            incoming = conserved_inputs(runtime, row)
            if not fits_return(runtime, incoming, transport=True):
                raise Refusal('whole native report has no complete transport with selected new analysis headroom')
            return [row]  # Exact whole return; other current reports remain queued.
    if 'service_report' in record:
        from .resource_scopes import blocked
        if blocked(runtime, row):
            raise Refusal('current service report authority/resources changed')
        incoming = conserved_inputs(runtime, row)
        if not fits_return(runtime, incoming, transport=True):
            raise Refusal('whole service report lacks full independent analysis headroom')
        return [row]  # One whole authenticated report job; neighbors remain queued.
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
        if not fits_return(runtime, incoming, transport=True):
            if candidate['id'] == row['id']:
                raise Refusal('whole report has no complete transport with selected new analysis headroom')
            continue
        if fits_return(runtime, reports + incoming, transport=True):
            chosen.append(candidate)
            reports += incoming
    if not chosen:
        raise Refusal('no qualified complete report batch within existing transport ceiling')
    return chosen
