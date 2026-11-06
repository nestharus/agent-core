"""Local whole-consumer joins shared by delivery clocks and retirement."""
import json
from .contracts import Refusal, digest


def published_incoming(store, event):
    """Identify only the exact outbox publishing this same receiving source."""
    payload = store.event(event)
    key = digest({'response_delivery': event})
    row = store.one('SELECT * FROM outboxes WHERE id=?', (key,))
    link = store.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (key,))
    if (not row or not link or link['event'] != event or row['hold']
            or row['kind'] != 'result' or row['event'] != event
            or row['job'] != payload.get('source_job') or row['recipient'] != payload.get('role')
            or row['role'] != payload.get('source_role') or row['producer'] != payload.get('author')
            or json.loads(row['payload']) != payload or payload.get('kind') != 'response'
            or json.loads(row['board_receipt'] or '{}').get('control_receipt', {}).get('pending')):
        return None
    producer = store.job(row['job'])
    if (producer['active_attempt'] != payload.get('source_attempt')
            or producer['response'] != digest({'response': payload.get('source_attempt')})
            or payload.get('source_members') != json.loads(producer['members'])):
        return None
    return key


def delivery(store, key):
    link = store.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (key,))
    if not link:
        # Before the structural-link table existed, a receiving source can
        # already be present. Relocation must not make that consumer disappear.
        candidates = [e['id'] for e in store.rows(
            "SELECT e.id FROM events e LEFT JOIN source_custody c ON c.event=e.id "
            "WHERE json_extract(e.payload,'$.source_delivery.id')=? "
            "OR json_extract(c.binding,'$.header.source_delivery.id')=?", (key,key))]
        if len(candidates) > 1:
            raise Refusal('delivery has ambiguous local original consumers')
        link = {'event': candidates[0]} if candidates else None
    if not link:
        return {'event': None, 'complete': True, 'processed_at': None, 'basis': None}
    rows = store.dependents(link['event'])
    complete = bool(rows) and not store.dependency_hold(link['event']) and all(
        r['processed_at'] is not None and not r['hold'] for r in rows)
    if not complete:
        incoming = published_incoming(store, link['event']) if rows else None
        # The receiving event cannot acquire its global processing timestamp
        # before this incoming edge settles. Prove its same whole obligations
        # without that one edge; leave the event and every other edge untouched.
        if incoming and store.completion_candidates(link['event'], incoming):
            ids = {r['id'] for r in rows}
            jobs = {j['id'] for j in store.rows('SELECT id,members FROM jobs')
                    if any(m['event'] in ids for m in json.loads(j['members']))}
            complete = all(not r['hold'] and (r['id'] == link['event'] or r['processed_at'] is not None) for r in rows)
            complete = complete and all(store.delivery_satisfied(o) for o in store.rows('SELECT * FROM outboxes')
                                         if o['id'] != incoming and (o['event'] in ids or o['job'] in jobs))
            if complete:
                rows = [{**r, 'processed_at': r['processed_at'] if r['processed_at'] is not None else store.clock()}
                        for r in rows]
    return {'event': link['event'], 'complete': complete,
            'processed_at': max((r['processed_at'] for r in rows), default=None) if complete else None,
            'basis': digest([{'id': r['id'], 'hash': r['hash'], 'processed_at': r['processed_at'], 'hold': r['hold']}
                             for r in sorted(rows, key=lambda r: r['id'])])}


def require_aged(store, key, retention):
    result = delivery(store, key)
    if not result['complete'] or (result['event'] and store.clock() < result['processed_at'] + retention):
        raise Refusal('whole child/downstream consumer processing plus retention is still held')
    return result
