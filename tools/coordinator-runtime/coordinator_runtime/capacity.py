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
# Withheld from ordinary admission, not additional capacity. This small fixed
# record cannot guarantee writes after disk exhaustion or noncooperating writes.
PRESSURE_RESERVE = 4096
HOLDS = {"source", "consumer", "control", "transport", "publication", "resource",
         "recovery", "effect", "privacy"}
SCHEMA = """
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
    return store.one("SELECT * FROM alert_service WHERE singleton=1")


def capture(store):
    """Observe only now; missed intervals remain an explicit gap, never backfill.

    A full alert cohort is atomic. Existing causes and old occurrences survive
    refusal. The gap remains open even after later successful observations;
    success cannot retroactively fulfill an unavailable cadence obligation.
    """
    now = store.clock()
    interval = store.config['deadlines']['alert_interval']
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
        occurrences = [{'id': ident(), 'created': now, **v} for v in violations]
        try:
            store.db.execute('SAVEPOINT alert_cohort')
            emitted = []
            for occurrence in occurrences:
                store.budget('alerts', len(encode(occurrence).encode()) + 1024)
                store.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)',
                                 (occurrence['id'], occurrence['subject'], occurrence['kind'], now, encode(occurrence)))
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
            pending = store.one('SELECT COUNT(*) AS n FROM alert_debt WHERE represented=0')['n']
            maximum = store.config['limits'].get('max_alert_debt', store.config['limits']['max_alerts'])
            if pending + len(occurrences) > maximum:
                raise Backpressure('exact alert debt capacity exhausted; observation unavailable, causes remain held')
            for occurrence in occurrences:
                store.budget(None, len(encode(occurrence).encode()) + 1024)
                store.db.execute('INSERT INTO alert_debt VALUES(?,?,?,?,?,0)',
                    (occurrence['id'], occurrence['subject'], occurrence['kind'], now, encode(occurrence)))
            emitted = []
        for occurrence in occurrences:
            store.db.execute('INSERT INTO alert_cadence VALUES(?,?,?) ON CONFLICT(subject,kind) '
                             'DO UPDATE SET last_created=excluded.last_created',
                             (occurrence['subject'], occurrence['kind'], now))
        store.db.execute('UPDATE alert_service SET last_observed=? WHERE singleton=1', (now,))
    return emitted


def gap(store, since, through, reason, scope, count):
    store.db.execute('UPDATE alert_service SET gap_since=COALESCE(gap_since,?),gap_through=?,reason=?, '
                     'scope=COALESCE(scope,?),unrepresented=unrepresented+? WHERE singleton=1',
                     (since, through, reason, scope, count))


def deliver_pending(store, limit=32):
    """Allocate each original occurrence once; pressure does not erase its ID."""
    if not store.config.get('delivery'):
        return 0
    for row in store.rows('SELECT * FROM alert_debt WHERE represented=0 ORDER BY created,id LIMIT ?', (limit,)):
        try:
            with store.tx():
                store.budget('alerts', len(row['payload'].encode()) + 1024)
                store.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)',
                                 (row['id'], row['subject'], row['kind'], row['created'], row['payload']))
                store.db.execute('UPDATE alert_debt SET represented=1 WHERE id=?', (row['id'],))
        except Backpressure:
            break
    role = store.config['delivery'].get('alert_role', 'Work')
    recipient = store.config['delivery'].get('alert_recipient', 'Work')
    rows = store.rows('SELECT a.* FROM alerts a WHERE NOT EXISTS '
                      '(SELECT 1 FROM outboxes o WHERE o.alert=a.id) ORDER BY a.created,a.id LIMIT ?', (limit,))
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


def retirement_basis(store, occurrence):
    alert = store.one('SELECT * FROM alerts WHERE id=?', (occurrence,))
    outboxes = store.rows('SELECT * FROM outboxes WHERE alert=? ORDER BY id', (occurrence,))
    if not alert or len(outboxes) != 1:
        raise Refusal('retirement requires one exact standalone alert and linked delivery')
    outbox = outboxes[0]
    if outbox['kind'] != 'alert' or outbox['event'] is not None or outbox['job'] is not None:
        raise Refusal('job/event/other-kind lifecycle is outside standalone alert retirement')
    return alert, outbox, digest({'configuration': digest(store.config), 'alert': alert, 'outbox': outbox})


def retire(store, occurrence, actor, receipt, current_delivery):
    """Called inside the genuine Board owner/grant lock, never automatic sweep.

    Evidence is the actual custodian's qualified assertion, not an inferred
    global hold census. Board/native retained records are never removed here.
    """
    with store.tx():
        alert, outbox, basis = retirement_basis(store, occurrence)
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
        store.db.execute('DELETE FROM delivery_wakeups WHERE delivery=?', (outbox['id'],))
        store.db.execute('DELETE FROM outboxes WHERE id=?', (outbox['id'],))
        store.db.execute('DELETE FROM alerts WHERE id=?', (occurrence,))
    return {'retired_alert': occurrence, 'retired_delivery': outbox['id'], 'basis': basis,
            'actor': actor, 'receipt': receipt, 'scope': 'runtime rows only; retain this original receipt; no platform reclamation'}
