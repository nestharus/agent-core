"""Local whole-consumer joins shared by delivery clocks and retirement."""
from .contracts import Refusal, digest


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
    return {'event': link['event'], 'complete': complete,
            'processed_at': max((r['processed_at'] for r in rows), default=None) if complete else None,
            'basis': digest([{'id': r['id'], 'hash': r['hash'], 'processed_at': r['processed_at'], 'hold': r['hold']}
                             for r in sorted(rows, key=lambda r: r['id'])])}


def require_aged(store, key, retention):
    result = delivery(store, key)
    if not result['complete'] or (result['event'] and store.clock() < result['processed_at'] + retention):
        raise Refusal('whole child/downstream consumer processing plus retention is still held')
    return result
