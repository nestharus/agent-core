"""Bounded future alert service; no historical replay or foreign retirement.

An observed due occurrence survives a full outbox. A saturated alert journal
instead records an explicit, owner-custodied service gap. Neither means delivery
or processing. Only the actual same source/consumer owner can retire an aged
standalone alert, with current Board authority and all-hold evidence.
"""
import json
import math

from .contracts import Backpressure, Refusal, digest, encode, ident, required_text

RETENTION = 86400
NOTIFICATION = "alert-occurrences-v1"
NOTIFICATION_LIMIT = 32
NOTIFICATION_BYTES = 32768
SINGLE_NOTIFICATION_BYTES = 196608
# Withheld from ordinary admission, not additional capacity. This small fixed
# record cannot guarantee writes after disk exhaustion or noncooperating writes.
PRESSURE_RESERVE = 4096
HOLDS = {"source", "consumer", "control", "transport", "publication", "resource",
         "recovery", "effect", "privacy"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS alert_delivery_members(
 occurrence TEXT PRIMARY KEY REFERENCES alerts(id),delivery TEXT NOT NULL REFERENCES outboxes(id),
 source_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alert_service(
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),last_observed REAL NOT NULL,
 gap_since REAL,gap_through REAL,custodian TEXT NOT NULL,reason TEXT,
 scope TEXT,unrepresented INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS alert_debt(
 id TEXT PRIMARY KEY,subject TEXT NOT NULL,kind TEXT NOT NULL,created REAL NOT NULL,
 payload TEXT NOT NULL,represented INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS alert_cadence(
 subject TEXT NOT NULL,kind TEXT NOT NULL,last_created REAL NOT NULL,PRIMARY KEY(subject,kind));
"""


def service(store):
    row = store.one("SELECT * FROM alert_service WHERE singleton=1")
    latest = store.one("SELECT value FROM meta WHERE key='alert-observation'")
    return {**row, 'latest': json.loads(latest['value']) if latest else None} if row else None


def preserve_alert_frontier(store):
    """One constant-size high-water mark; no old occurrence gains new origin."""
    physical = store.one('SELECT COALESCE(MAX(rowid),0) AS n FROM alerts')['n']
    saved = store.one("SELECT value FROM meta WHERE key='alert-row-frontier'")
    frontier = max(physical, int(saved['value']) if saved else 0)
    store.db.execute("INSERT INTO meta VALUES('alert-row-frontier',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (str(frontier),))
    return frontier


def insert_alert(store, occurrence):
    # The original occurrence ID/time/full body survive debt materialization.
    # Explicit placement prevents qualified deletion reusing an old boundary.
    position = preserve_alert_frontier(store) + 1
    store.db.execute('INSERT INTO alerts(rowid,id,subject,kind,created,payload,processed_at) VALUES(?,?,?,?,?,?,NULL)',
                     (position, occurrence['id'], occurrence['subject'], occurrence['kind'],
                      occurrence['created'], encode(occurrence)))
    preserve_alert_frontier(store)


def capture(store):
    """Observe only now; missed intervals remain an explicit gap, never backfill.

    A full alert cohort is atomic. Existing causes and old occurrences survive
    refusal. The gap remains open even after later successful observations;
    success cannot retroactively fulfill an unavailable cadence obligation.
    """
    now = store.clock()
    interval = store.config['deadlines']['alert_interval']
    refusal = None
    with store.tx():
        previous = service(store)
        if previous and now < previous['last_observed'] + interval:
            return []
        role = store.config.get('delivery', {}).get('alert_role', 'Work')
        owner = store.enrollment(role)['owner']
        if not previous:
            store.db.execute("INSERT INTO alert_service(singleton,last_observed,custodian) VALUES(1,?,?)",
                             (now, owner))
        elif now >= previous['last_observed'] + 2 * interval:
            gap(store, previous['last_observed'] + interval, now,
                'unobserved cadence interval; historical population unknown', None, 0)
        violations = []
        for violation in store.violations():
            cadence = store.config.get('alert_cadences', {}).get(violation['kind'], interval)
            prior = store.one('SELECT last_created FROM alert_cadence WHERE subject=? AND kind=?',
                              (violation['subject'], violation['kind']))
            if not prior or now >= prior['last_created'] + cadence:
                violations.append(violation)
        # Origin is recorded only at this actual observation, never backfilled
        # onto historical alerts/debt. It selects custody, not receiving authority.
        origin = ({'processing_capability': store.processing.current()[0]['id']}
                  if store.processing else {})
        occurrences = [{'id': ident(), 'created': now, **v, **origin} for v in violations]
        try:
            store.db.execute('SAVEPOINT alert_cohort')
            emitted = []
            for occurrence in occurrences:
                store.budget('alerts', len(encode(occurrence).encode()) + 1024)
                insert_alert(store, occurrence)
                emitted.append(occurrence)
            store.db.execute('RELEASE alert_cohort')
        except Refusal:
            store.db.execute('ROLLBACK TO alert_cohort')
            store.db.execute('RELEASE alert_cohort')
            gap(store, now, now, 'due cohort not represented: alert count/byte pressure',
                digest({'observed_at': now, 'violations': violations}), len(violations))
            # Keep exact original occurrences, not just an interval/digest. A
            # later representation keeps its original ID/time and does not
            # claim that the missed delivery/cadence was fulfilled on time.
            try:
                store.db.execute('SAVEPOINT exact_debt')
                pending = store.one('SELECT COUNT(*) AS n FROM alert_debt WHERE represented=0')['n']
                maximum = store.config['limits'].get('max_alert_debt', store.config['limits']['max_alerts'])
                if pending + len(occurrences) > maximum:
                    raise Backpressure('exact alert debt capacity exhausted')
                for occurrence in occurrences:
                    store.budget(None, len(encode(occurrence).encode()) + 1024)
                    store.db.execute('INSERT INTO alert_debt VALUES(?,?,?,?,?,0)',
                        (occurrence['id'], occurrence['subject'], occurrence['kind'], now, encode(occurrence)))
                store.db.execute('RELEASE exact_debt')
                disposition = 'exact-debt'
            except Refusal as exc:
                store.db.execute('ROLLBACK TO exact_debt')
                store.db.execute('RELEASE exact_debt')
                refusal = Backpressure(str(exc) + '; newest due payloads unavailable; originals remain held')
                disposition = 'unavailable'
                store.db.execute('UPDATE alert_service SET reason=? WHERE singleton=1', (str(refusal),))
            emitted = []
        else:
            disposition = 'exact-alerts'
        # One reserved, bounded newest-observation record is independent of the
        # all-or-nothing occurrence/debt savepoints. It is not an exact payload
        # archive, a missed-population census or a delivery/processing receipt.
        observation = {'at': now, 'custodian': owner, 'due_count': len(occurrences),
                       'scope': digest({'observed_at': now, 'violations': violations}),
                       'representation': disposition,
                       'coverage': 'newest due payloads unavailable' if refusal else 'exact observed due cohort retained'}
        store.db.execute("INSERT INTO meta VALUES('alert-observation',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (encode(observation),))
        if refusal is None:
            for occurrence in occurrences:
                store.db.execute('INSERT INTO alert_cadence VALUES(?,?,?) ON CONFLICT(subject,kind) '
                                 'DO UPDATE SET last_created=excluded.last_created',
                                 (occurrence['subject'], occurrence['kind'], now))
        store.db.execute('UPDATE alert_service SET last_observed=? WHERE singleton=1', (now,))
    if refusal is not None:
        # Raise only after COMMIT. A refusal cannot roll back the very evidence
        # that tells supported callers/status that current coverage was lost.
        refusal.observation = observation
        raise refusal
    return emitted


def gap(store, since, through, reason, scope, count):
    store.db.execute('UPDATE alert_service SET gap_since=COALESCE(gap_since,?),gap_through=?,reason=?, '
                     'scope=COALESCE(scope,?),unrepresented=unrepresented+? WHERE singleton=1',
                     (since, through, reason, scope, count))


def deliver_pending(store, limit=32):
    """Allocate each original occurrence once; pressure does not erase its ID."""
    if not store.config.get('delivery'):
        return 0
    continuing = store.processing and 'service' in store.processing.current()[1]
    origin = store.processing.key if continuing else None
    first = store.one('SELECT * FROM alert_debt WHERE represented=0 AND '
                      "(? IS NULL OR json_extract(payload,'$.processing_capability')=?) "
                      'ORDER BY created,id LIMIT 1', (origin, origin))
    if first:
        # Exact debt from one observed time/origin is an atomic cohort. Reading
        # a delivery-sized prefix must not turn a refused cohort into partial
        # admission. Same-time ambiguous legacy debt is conservatively joined,
        # never assigned invented observation history. Debt count stays bounded
        # by its already selected finite capacity; notification pages remain 32.
        cohort = store.rows('SELECT * FROM alert_debt WHERE represented=0 AND created=? '
                            "AND json_extract(payload,'$.processing_capability') IS ? ORDER BY id",
                            (first['created'], json.loads(first['payload']).get('processing_capability')))
        try:
            with store.tx():
                for row in cohort:
                    store.budget('alerts', len(row['payload'].encode()) + 1024)
                    insert_alert(store, json.loads(row['payload']))
                    store.db.execute('UPDATE alert_debt SET represented=1 WHERE id=?', (row['id'],))
        except Backpressure:
            pass  # All original debt remains; existing owed deliveries proceed.
    role = store.config['delivery'].get('alert_role', 'Work')
    recipient = store.config['delivery'].get('alert_recipient', 'Work')
    from .configuration import selected
    transition = selected(store) if continuing else None
    boundary = transition['alert_boundary'] if transition else 0
    rows = store.rows('SELECT a.* FROM alerts a WHERE a.rowid>? AND '
                      "(? IS NULL OR json_extract(a.payload,'$.processing_capability')=?) AND NOT EXISTS "
                      '(SELECT 1 FROM outboxes o WHERE o.alert=a.id) AND NOT EXISTS '
                      '(SELECT 1 FROM alert_delivery_members m WHERE m.occurrence=a.id) '
                      'ORDER BY a.created,a.id LIMIT ?', (boundary, origin, origin, limit,))
    if continuing:
        return deliver_notifications(store, role, recipient, rows)
    count = 0
    for row in rows:
        try:
            with store.tx():
                store._outbox(role, recipient, 'alert', json.loads(row['payload']), alert=row['id'],
                              key=digest({'alert': row['id']}))
            count += 1
        except Backpressure:
            break
    return count


def deliver_notifications(store, role, recipient, rows):
    """Bounded full batches, not deduplication: every occurrence keeps its ID.

    Undelivered rows/debt remain pending on pressure. A large occurrence
    uses one full singleton envelope, within the receiving message bound. No
    oversized payload is clipped or converted into business-work authority.
    """
    count = 0
    while rows:
        batch = []
        for row in rows[:NOTIFICATION_LIMIT]:
            candidate = batch + [row]
            payload = notification_payload(store, candidate)
            if len(encode(payload).encode()) > NOTIFICATION_BYTES:
                break
            batch = candidate
        if not batch:
            batch = rows[:1]
            payload = notification_payload(store, batch)
            if len(encode(payload).encode()) > SINGLE_NOTIFICATION_BYTES:
                gap(store, store.clock(), store.clock(),
                    'full occurrence exceeds notification envelope; exact source retained pending delivery',
                    digest(payload), 0)
                break
        else:
            payload = notification_payload(store, batch)
        try:
            with store.tx():
                key = store._outbox(role, recipient, 'alert', payload, alert=batch[0]['id'],
                                    key=digest({'alert_occurrences': [r['id'] for r in batch]}))
                for row in batch:
                    store.budget(None, 256)
                    store.db.execute('INSERT INTO alert_delivery_members VALUES(?,?,?)',
                                     (row['id'], key, digest(json.loads(row['payload']))))
        except Backpressure:
            break
        count += 1
        rows = rows[len(batch):]
    return count


def notification_payload(store, rows):
    return {'schema': NOTIFICATION,
            'source_custodians': {r: value['owner'] for r, value in store.config['roles'].items()}, 'occurrences': [json.loads(r['payload']) for r in rows],
            'scope': 'Full due occurrences; notification processing alone settles no underlying cause, '
                     'old source, native ownership, effect, acceptance or hold.'}


def notification(store, event):
    """Authenticate the whole typed notification, never a caller marker alone."""
    if not store.processing or not event.get('source_delivery'):
        return None
    key = event['source_delivery']['id']
    outbox = store.one('SELECT * FROM outboxes WHERE id=?', (key,))
    if not outbox or outbox['kind'] != 'alert' or outbox['job'] or outbox['event'] or not outbox['alert']:
        return None
    payload = json.loads(outbox['payload'])
    if payload.get('schema') != NOTIFICATION:
        return None
    if not store.processing.owed_control(event) or event['body'] != payload:
        raise Refusal('notification differs from its exact addressed source')
    members = store.rows('SELECT occurrence,source_hash FROM alert_delivery_members WHERE delivery=? ORDER BY occurrence', (key,))
    occurrences = payload.get('occurrences', [])
    expected = [{'occurrence': r['id'], 'source_hash': digest(r)} for r in occurrences]
    if (not 1 <= len(occurrences) <= NOTIFICATION_LIMIT or len(encode(payload).encode()) > (SINGLE_NOTIFICATION_BYTES if len(occurrences)==1 else NOTIFICATION_BYTES)
            or any(r.get('processing_capability') != store.processing.key for r in occurrences)
            or len({r['id'] for r in occurrences}) != len(occurrences)
            or sorted(expected, key=lambda r: r['occurrence']) != members
            or outbox['alert'] != occurrences[0]['id'] or outbox['producer'] != store.config['actor']):
        raise Refusal('whole original notification membership/attribution is required')
    return {'delivery': key, 'occurrences': occurrences,
            'coverage_evidence': 'alert-occurrences:' + digest(occurrences),
            'source_custodians': payload['source_custodians'], 'scope': payload['scope']}


def retirement_basis(store, occurrence):
    if store.one('SELECT delivery FROM alert_delivery_members WHERE occurrence=?', (occurrence,)):
        raise Refusal('grouped notification custody requires whole-cohort qualification; standalone retirement is unavailable')
    alert = store.one('SELECT * FROM alerts WHERE id=?', (occurrence,))
    outboxes = store.rows('SELECT * FROM outboxes WHERE alert=? ORDER BY id', (occurrence,))
    if not alert or len(outboxes) != 1:
        raise Refusal('retirement requires one exact standalone alert and linked delivery')
    outbox = outboxes[0]
    if outbox['kind'] != 'alert' or outbox['event'] is not None or outbox['job'] is not None:
        raise Refusal('job/event/other-kind lifecycle is outside standalone alert retirement')
    debt = store.one('SELECT * FROM alert_debt WHERE id=?', (occurrence,))
    if debt and (debt['represented'] != 1 or debt['payload'] != outbox['payload']):
        raise Refusal('exact original represented debt must remain with its source delivery')
    from .frontier import delivery
    return alert, outbox, digest({'configuration': digest(store.config), 'alert': alert, 'outbox': outbox,
                                  'exact_debt': debt,
                                  'whole_consumer': delivery(store, outbox['id'])})


def retire(store, occurrence, actor, receipt, current_delivery):
    """Called inside the genuine Board owner/grant lock, never automatic sweep.

    Evidence is the actual custodian's qualified assertion, not an inferred
    global hold census. Board/native retained records are never removed here.
    """
    with store.tx():
        alert, outbox, basis = retirement_basis(store, occurrence)
        from .frontier import require_aged
        require_aged(store, outbox['id'], RETENTION)
        role = outbox['role']
        owner = store.enrollment(role)['owner']
        recipient = store.config['delivery']['recipients'][outbox['recipient']]['session']
        if actor != owner or actor != recipient or outbox['producer'] != store.config['actor']:
            raise Refusal('only the genuine same source/consumer owner can retire this alert')
        if receipt.get('basis') != basis or receipt.get('holds') != {name: [] for name in HOLDS}:
            raise Refusal('exact current source basis and every explicitly empty hold category required')
        required_text(receipt.get('evidence'), 'actual all-custodian qualification evidence', 2000)
        if type(receipt.get('qualified_at')) not in {int, float} or not math.isfinite(receipt['qualified_at']):
            raise Refusal('finite current qualification time required')
        if not 0 <= store.clock() - receipt['qualified_at'] <= 60:
            raise Refusal('hold qualification is stale or future-dated')
        saved = json.loads(outbox['board_receipt']) if outbox['board_receipt'] else None
        if (saved != current_delivery or current_delivery.get('recipient') != actor
                or current_delivery.get('id') != outbox['id']):
            raise Refusal('current exact recipient/transport/control receipt differs; reconcile first')
        control = current_delivery.get('control_receipt', {})
        transport = current_delivery.get('transport', {})
        if (outbox['state'] != 'settled' or outbox['hold'] or outbox['error']
                or current_delivery.get('state') != 'settled' or control.get('pending') is not False
                or not current_delivery.get('processing') or not current_delivery.get('settlement')
                or transport.get('delivery_state') != 'acknowledged'):
            raise Refusal('source/consumer/control/transport duty is still held')
        if transport.get('route') == 'queue':
            proof = current_delivery['processing'].get('transport', {})
            if (not transport.get('queue_message_id') or proof.get('state') != 'processed'
                    or proof.get('queue_message_id') != transport['queue_message_id'] or not proof.get('evidence')):
                raise Refusal('exact actual queue-processing correlation required')
        times = [alert['processed_at'], outbox['processed_at'], current_delivery.get('processed_at')]
        if any(type(t) not in {int, float} or not math.isfinite(t)
               or not max(alert['created'], outbox['created']) <= t <= store.clock()-RETENTION for t in times):
            raise Refusal('actual processing completion plus 24 hours is required at every frontier')
        if store.one('SELECT subject FROM operational_errors WHERE subject IN (?,?) AND active=1',
                     (occurrence, outbox['id'])):
            raise Refusal('active scoped error remains held')
        # Keep the evidence with the caller's retained exact receipt/output; no
        # unbounded local tombstone journal and no generic delivery deletion.
        preserve_alert_frontier(store)
        store.db.execute('DELETE FROM delivery_wakeups WHERE delivery=?', (outbox['id'],))
        store.db.execute('DELETE FROM outboxes WHERE id=?', (outbox['id'],))
        store.db.execute('DELETE FROM alert_debt WHERE id=?', (occurrence,))
        store.db.execute('DELETE FROM alerts WHERE id=?', (occurrence,))
    return {'retired_alert': occurrence, 'retired_delivery': outbox['id'], 'basis': basis,
            'actor': actor, 'receipt': receipt, 'scope': 'runtime rows only; retain this original receipt; no platform reclamation'}
