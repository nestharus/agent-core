"""Recycle qualified disposable episode rows in the SAME journal.

Required source/evidence is conserved by actual custodians before this operation.
This never deletes canonical files, shared Board/native stores, live contexts or
uncollected attempts. An all-holds receipt cannot override structural debt.
"""
import json
import math

from .contracts import Refusal, digest, encode, required_text
from .cleanup import eligible_event, RETENTION
from .capacity import HOLDS, NOTIFICATION, NOTIFICATION_LIMIT, NOTIFICATION_BYTES, SINGLE_NOTIFICATION_BYTES
from .frontier import require_aged


def cohort(store, root):
    store.event(root)
    events = {root}
    jobs = set()
    # Shared frozen batches and downstream returns form one retirement unit.
    # No finite depth/cycle shortcut is used to hide an outstanding frontier.
    while True:
        before = (set(events), set(jobs))
        for event in store.rows('SELECT id,parent FROM events'):
            if event['id'] in events or event['parent'] in events:
                events.add(event['id'])
                if event['parent']:
                    events.add(event['parent'])
        for job in store.rows('SELECT id,members,response FROM jobs'):
            members = {m['event'] for m in json.loads(job['members'])}
            if job['id'] in jobs or members & events or job['response'] in events:
                jobs.add(job['id']); events |= members
                if job['response']:
                    events.add(job['response'])
        for link in store.rows('SELECT delivery,event FROM processing_delivery_links'):
            outbox = store.one('SELECT event,job FROM outboxes WHERE id=?', (link['delivery'],))
            if outbox and (link['event'] in events or outbox['event'] in events or outbox['job'] in jobs):
                events.add(link['event'])
                if outbox['event']:
                    events.add(outbox['event'])
                if outbox['job']:
                    jobs.add(outbox['job'])
        if before == (events, jobs):
            return events, jobs


def basis(store, root):
    events, jobs = cohort(store, root)
    attempts = {a['id'] for a in store.rows('SELECT id,event,job FROM attempts') if a['event'] in events or a['job'] in jobs}
    deliveries = {o['id'] for o in store.rows('SELECT id,event,job FROM outboxes') if o['event'] in events or o['job'] in jobs}
    deliveries |= {l['delivery'] for l in store.rows('SELECT * FROM processing_delivery_links') if l['event'] in events}
    packages = {j['package'] for j in store.rows('SELECT package,id FROM jobs') if j['id'] in jobs and j['package']}
    occurrences = {m['occurrence'] for m in store.rows('SELECT * FROM alert_delivery_members') if m['delivery'] in deliveries}
    selected = {'events': sorted(events), 'jobs': sorted(jobs), 'attempts': sorted(attempts), 'deliveries': sorted(deliveries), 'packages': sorted(packages),
                'occurrences': sorted(occurrences)}
    # The exact data, not just row names, is bound to the qualified receipt.
    witnesses = {}
    for table, key, names in (('events','id',events), ('jobs','id',jobs), ('attempts','id',attempts), ('outboxes','id',deliveries)):
        witnesses[table] = [store.one(f'SELECT * FROM {table} WHERE {key}=?', (n,)) for n in sorted(names)]
    witnesses['occurrences'] = [store.one('SELECT * FROM alerts WHERE id=?', (n,)) for n in sorted(occurrences)]
    witnesses['alert_debt'] = [store.one('SELECT * FROM alert_debt WHERE id=?', (n,)) for n in sorted(occurrences)]
    witnesses['alert_members'] = [m for m in store.rows('SELECT * FROM alert_delivery_members ORDER BY occurrence') if m['delivery'] in deliveries]
    from .frontier import delivery
    witnesses['consumers'] = {n: delivery(store, n) for n in sorted(deliveries)}
    witnesses['job_births'] = [store.one('SELECT * FROM prospective_job_positions WHERE job=?', (n,)) for n in sorted(jobs)]
    return {'root': root, 'members': selected, 'basis': digest({'configuration': store.config, 'rows': witnesses}),
            'sources': {n: store.one('SELECT hash FROM events WHERE id=?', (n,))['hash'] for n in sorted(events)},
            'occurrences': {n: digest(store.one('SELECT * FROM alerts WHERE id=?', (n,))) for n in sorted(occurrences)},
            'results': {a: digest(store.one('SELECT * FROM results WHERE attempt=?', (a,))) for a in sorted(attempts)}}


def qualify_notification(store, outbox, capability, events):
    """Whole current-origin notification; underlying violation subjects stay owned.

    The episode receipt conserves each full occurrence separately. Its linked
    consumer and all downstream work must belong to this same disposable cohort.
    No notification ACK, model END or caller hold assertion replaces those checks.
    """
    links = store.rows('SELECT * FROM alert_delivery_members WHERE delivery=? ORDER BY occurrence', (outbox['id'],))
    payload = json.loads(outbox['payload'])
    if not links:
        if isinstance(payload, dict) and payload.get('schema') == NOTIFICATION:
            raise Refusal('notification membership is missing; preserve the original group')
        return
    if not isinstance(payload, dict) or not isinstance(payload.get('occurrences'), list):
        raise Refusal('original notification envelope required')
    full = payload.get('occurrences', [])
    if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in full):
        raise Refusal('every exact original occurrence identity required')
    from .frontier import delivery
    consumer = delivery(store, outbox['id'])
    if (outbox['kind'] != 'alert' or outbox['event'] or outbox['job']
            or outbox['producer'] != store.config['actor'] or payload.get('schema') != NOTIFICATION
            or not 1 <= len(full) <= NOTIFICATION_LIMIT
            or len(encode(payload).encode()) > (SINGLE_NOTIFICATION_BYTES if len(full) == 1 else NOTIFICATION_BYTES)
            or len({r['id'] for r in full}) != len(full)
            or outbox['alert'] != full[0]['id'] or consumer['event'] not in events):
        raise Refusal('whole bounded notification and original linked consumer required')
    expected = sorted([{'occurrence': r['id'], 'delivery': outbox['id'], 'source_hash': digest(r)} for r in full], key=lambda r: r['occurrence'])
    if links != expected:
        raise Refusal('partial/shared/changed notification membership remains held')
    for occurrence in full:
        alert = store.one('SELECT * FROM alerts WHERE id=?', (occurrence['id'],))
        debt = store.one('SELECT * FROM alert_debt WHERE id=?', (occurrence['id'],))
        shared = store.one('SELECT id FROM outboxes WHERE alert=? AND id!=?', (occurrence['id'], outbox['id']))
        if (not alert or json.loads(alert['payload']) != occurrence
                or occurrence.get('processing_capability') != capability
                or shared
                or (debt and (debt['represented'] != 1 or debt['payload'] != alert['payload']))):
            raise Refusal('exact current-origin occurrence/debt custody required; no historical reattribution')
        if (type(alert['processed_at']) not in {int, float} or not math.isfinite(alert['processed_at'])
                or not max(alert['created'], outbox['created']) <= alert['processed_at'] <= store.clock() - RETENTION):
            raise Refusal('every full occurrence needs actual processing plus 24h')
    saved = json.loads(outbox['board_receipt']) if outbox['board_receipt'] else {}
    transport = saved.get('transport', {})
    if (saved.get('id') != outbox['id'] or saved.get('state') != 'settled'
            or saved.get('recipient') != store.enrollment(outbox['role'])['owner']
            or saved.get('control_receipt', {}).get('pending') is not False
            or not saved.get('processing') or not saved.get('settlement')
            or type(outbox['processed_at']) not in {int, float}
            or not math.isfinite(outbox['processed_at'])
            or transport.get('delivery_state') != 'acknowledged'
            or type(saved.get('processed_at')) not in {int, float}
            or not math.isfinite(saved['processed_at'])
            or not outbox['created'] <= saved['processed_at'] <= store.clock() - RETENTION):
        raise Refusal('whole addressed processing/control/settlement proof remains held')
    if transport.get('route') == 'queue':
        proof = saved['processing'].get('transport', {})
        if (not transport.get('queue_message_id') or proof.get('state') != 'processed'
                or proof.get('queue_message_id') != transport['queue_message_id'] or not proof.get('evidence')):
            raise Refusal('exact queue processing correlation required')


def apply(store, root, actor, receipt):
    """Issuer supplies actual all-custodian receipts; structural checks stay local."""
    with store.tx():
        current = basis(store, root)
        cap, selection = store.processing.current()
        if 'service' not in selection or actor != cap['issuer']:
            raise Refusal('genuine continuing issuer required; no legacy cleanup capability extension')
        custody = ('sources', 'results', 'occurrences') if current['occurrences'] else ('sources', 'results')
        if (not isinstance(receipt, dict) or set(receipt) != {'basis', 'qualified_at', 'holds', 'evidence', *custody}
                or receipt['basis'] != current['basis'] or receipt['holds'] != {h: [] for h in HOLDS}
                or type(receipt['qualified_at']) not in {int, float} or not 0 <= store.clock() - receipt['qualified_at'] <= 60):
            raise Refusal('current exact cohort basis/time/all-hold qualification required')
        required_text(receipt['evidence'], 'actual all-source/consumer/recovery/effect/privacy custodians')
        if any(set(receipt[name]) != set(current[name]) for name in custody):
            raise Refusal('every original source and result needs exact conservation/disposability proof')
        for name in custody:
            expected = current[name]
            for key, value in receipt[name].items():
                if not isinstance(value, dict) or set(value) != {'hash', 'custodian', 'evidence', 'disposition'} or value['hash'] != expected[key]:
                    raise Refusal('exact original custody proof required')
                required_text(value['custodian'], 'actual source/result custodian')
                required_text(value['evidence'], 'full original conservation/effect evidence')
                if value['disposition'] not in {'conserved-at-original-source', 'producer-owned-disposable'}:
                    raise Refusal('canonical/protected/foreign stores are never disposable')
        members = current['members']
        subjects = members['events'] + members['jobs'] + members['attempts'] + members['deliveries'] + members['occurrences']
        for subject in subjects:
            if store.one('SELECT subject FROM operational_errors WHERE subject=? AND active=1', (subject,)):
                raise Refusal('an actual scoped operational/recovery question remains unresolved')
        for event in members['events']:
            row = store.one('SELECT * FROM events WHERE id=?', (event,))
            if not store.processing.retirement_event(store.event(event)) or not eligible_event(store, row):
                raise Refusal('source/descendant processing+24h or a structural hold remains')
            if row['state'] != 'retired':
                raise Refusal('retire owned artifact/queue material first; do not delete required body custody')
        for attempt in members['attempts']:
            row = store.attempt(attempt)
            # All old attempts, control recognition and foreign collectors stay
            # outside this prospective disposable-output operation.
            if json.loads(row['detail']).get('processing_capability') != cap['id']:
                raise Refusal('old/foreign original attempt is conserved, never swept into a new episode')
            if row['collected'] is None or row['ended'] is None or row['cleanup'] not in {'done','no-session-created','owned-ephemeral-lifecycle-observed'}:
                raise Refusal('original process/context/recovery custody is not closed')
            if store.one("SELECT path FROM artifact_custody WHERE attempt=? AND kind='role-owned'", (attempt,)):
                raise Refusal('canonical role-owned source is not disposable output')
            if store.one('SELECT path FROM artifacts WHERE attempt=? AND removed IS NULL', (attempt,)):
                raise Refusal('exact owned artifact retirement remains outstanding')
            if store.one("SELECT target FROM file_publications WHERE attempt=? AND state!='published'", (attempt,)):
                raise Refusal('publication intent/temporary stays with actual source/effect custodian')
            if store.one('SELECT resource FROM ordinary_resources WHERE attempt=?', (attempt,)):
                raise Refusal('original resource/effect holder remains')
            if store.one('SELECT attempt FROM canonical_backups WHERE attempt=?', (attempt,)):
                raise Refusal('protected canonical backup custody is outside disposable episode retirement')
        for job in members['jobs']:
            row = store.job(job)
            if row['state'] != 'closed' or row['effects'] not in {'none', 'reconciled'} or row['hold_reason']:
                raise Refusal('whole frozen job/downstream/effects remain held')
            for table in ('integration_retirements', 'integration_prestart_dispositions'):
                if store.one(f'SELECT job FROM {table} WHERE job=?', (job,)):
                    raise Refusal('enduring integration debt is not disposable output')
            if store.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'", (job,)):
                raise Refusal('selected owner recovery still outstanding')
        for key in members['deliveries']:
            row = store.one('SELECT * FROM outboxes WHERE id=?', (key,))
            if not row:
                raise Refusal('original linked delivery is missing; preserve uncertain custody')
            qualify_notification(store, row, cap['id'], members['events'])
            require_aged(store, key, RETENTION)
            if (not row or row['state'] != 'settled' or row['hold'] or row['error']
                    or row['processed_at'] is None or store.clock() < row['processed_at'] + RETENTION):
                raise Refusal('delivery processing+24h and all holds remain')
            if row.get('board_receipt'):
                conserved=store.one("SELECT * FROM shared_custody_intents WHERE delivery=? AND state='retired'",(key,))
                if not conserved:
                    raise Refusal('actual shared canonical custody must retire/conserve before deleting local scan attribution')
        # No canonical or shared Board row is deleted here. All SQL targets are
        # this journal's exact qualified episode. SQLite reuses its free pages;
        # this makes no physical platform-reclamation claim.
        def delete(table, column, values):
            for value in values:
                store.db.execute(f'DELETE FROM {table} WHERE {column}=?', (value,))
        for table, column in [('delivery_wakeups','delivery'), ('processing_delivery_links','delivery')]:
            delete(table, column, members['deliveries'])
        # Keep row/frontier chronology monotonic even when every newer alert is
        # reclaimed. This preserves existing configuration alert boundaries.
        from .capacity import preserve_alert_frontier
        preserve_alert_frontier(store)
        delete('alert_delivery_members', 'delivery', members['deliveries'])
        for key in members['deliveries']:
            row = store.one('SELECT alert FROM outboxes WHERE id=?', (key,))
            if row and row['alert']:
                alert = store.one('SELECT * FROM alerts WHERE id=?', (row['alert'],))
                if alert['processed_at'] is None or store.clock() < alert['processed_at'] + RETENTION:
                    raise Refusal('alert whole processing retention remains')
                delete('alert_debt', 'id', [row['alert']]); delete('alerts','id',[row['alert']])
        delete('alert_debt', 'id', members['occurrences'])
        delete('alerts', 'id', members['occurrences'])
        delete('outboxes','id',members['deliveries'])
        # The conserved archive has its own consumer/retention frontier. Keep
        # its exact binding and observed conservation receipt after the original
        # episode retires, so later reconciliation/release needs no lost outbox
        # or reconstructed authority. This small custody record remains charged.
        blob_candidates = {r['sha256'] for a in members['attempts'] for r in store.rows('SELECT sha256 FROM artifact_custody WHERE attempt=?', (a,))}
        for table, column in [('results','attempt'),('artifact_custody','attempt'),('artifacts','attempt'),('attempt_storage','attempt'),
                              ('routine_runs','attempt'),('routine_stages','attempt'),('file_publications','attempt'),('ordinary_runs','attempt'),('ordinary_tool_records','attempt'),
                              ('ordinary_acceptance','attempt')]:
            delete(table,column,members['attempts'])
        # Continuing review calls/history remain branch evidence through actual
        # branch/context closure, with their original snapshots and raw returns.
        for table, column in [('recovery_requests','job'),('recovery_dispositions','job'),('owner_results','job'),('qa_package_owners','job')]:
            delete(table,column,members['jobs'])
        delete('attempts','id',members['attempts'])
        # Per-job birth retires only with the same fully qualified cohort.
        # Never reset sqlite_sequence: future epochs/jobs keep this frontier.
        delete('prospective_job_positions','job',members['jobs'])
        delete('jobs','id',members['jobs'])
        for table, column in [('queue','event'),('input_resolutions','event'),('source_custody','event'),('duty_accounts','event'),
                              ('processing_controls','event'),('processing_control_returns','source'),('processing_source_positions','event'),
                              ('input_lookups','event'),('input_locators','event')]:
            delete(table,column,members['events'])
        # Remove child links inside this already-joined disposable cohort before
        # deleting rows under SQLite's immediate foreign-key checks.
        for event in members['events']:
            store.db.execute('UPDATE events SET parent=NULL WHERE id=?', (event,))
        delete('events','id',members['events'])
        for event in members['events']:
            delete('processing_delivery_links','event',[event])
        for package in members['packages']:
            if not store.one('SELECT id FROM jobs WHERE package=?', (package,)):
                delete('processing_admissions','package',[package]); delete('admissions','package',[package])
        # A conserved peer/prior source may still cite a body after this cohort
        # retires. Search reference fields in this journal, never native stores.
        for sha in blob_candidates:
            referenced = False
            for table in store.rows("SELECT name FROM sqlite_master WHERE type='table' AND name!='artifact_blobs'"):
                name = table['name']
                if not name.replace('_','').isalnum():
                    raise Refusal('unexpected journal table; preserve body custody')
                for column in store.rows(f'PRAGMA table_info({name})'):
                    if column['type'].upper() == 'TEXT' and store.one(f'SELECT 1 AS found FROM {name} WHERE instr({column["name"]},?)>0 LIMIT 1', (sha,)):
                        referenced = True; break
                if referenced: break
            if not referenced:
                delete('artifact_blobs','sha256',[sha])
    return {'retired': current, 'actor': actor, 'receipt': receipt,
            'meaning': 'retain this whole original retirement receipt; same-journal logical capacity only'}
