"""Recurring bounded owner progress. No built-in all-hold or processing fiction.

The actual owner supplies its existing custodian qualification and durable
evidence sink. The Board owner entry still checks actual identity and grants.
Absent that capability the service reports an owned gap and conserves rows.
"""
import json
import math

from . import capacity
from .contracts import Refusal, encode, required_text

PAGE = 16


class OwnerAlertCustodian:
    def __init__(self, board, qualify, retain):
        self.board, self.qualify, self.retain = board, qualify, retain

    def progress_alert(self, store, occurrence):
        alert, outbox, basis = capacity.retirement_basis(store, occurrence)
        times = (alert['processed_at'], outbox['processed_at'])
        if any(type(t) not in {int, float} or not math.isfinite(t)
               or not max(alert['created'], outbox['created']) <= t <= store.clock()-capacity.RETENTION for t in times):
            raise Refusal('unknown processing or processing+24h not reached; original source retained')
        # No processing stamp is generated. This asks the actual qualified
        # source/consumer/control/transport/hold custodians on every visit.
        receipt = self.qualify(store, alert, outbox, basis)
        if receipt is None:
            raise Refusal('actual custodian qualification unavailable; source retained')
        if receipt.get('holds') != {name: [] for name in capacity.HOLDS}:
            raise Refusal('actual custodian holds remain; original source retained')
        # Preserve the complete beforeimage and original assertion BEFORE a
        # possible retirement effect. A failed result publication retains this
        # intent with its genuine custodian, never triggers blind replay.
        intent = {'alert': alert, 'outbox': outbox, 'basis': basis, 'receipt': receipt}
        reference = self.retain({'retirement_intent': intent})
        required_text(reference, 'actual retained retirement-intent reference', 2000)
        result = self.board.retire_alert(store, occurrence, receipt)
        self.retain({'retirement_result': result, 'intent_reference': reference})
        return result


def step(store, custodians):
    """Fair fixed-frontier pages, called by the recurring dispatcher, not CLI drain.

    A failing or held occurrence consumes one visit, not the whole frontier.
    Successful later visits never clear prior gap evidence. Meta is a bounded
    scheduling hint/status, not a processing/retirement receipt or hold census.
    """
    if not store.config.get('finite_service'):
        return
    row = store.one("SELECT value FROM meta WHERE key='custodian-progress'")
    state = json.loads(row['value']) if row else {'cursor': 0, 'end': 0, 'passes': 0, 'first_gap': None}
    now = store.clock()
    if now < state.get('next_at', 0):
        return
    if state['cursor'] >= state['end']:
        state['cursor'] = 0
        state['end'] = store.one('SELECT COALESCE(MAX(rowid),0) AS n FROM alerts')['n']
    rows = store.rows('SELECT a.id,a.rowid AS seq,o.role FROM alerts a LEFT JOIN outboxes o ON o.alert=a.id '
                      'WHERE a.rowid>? AND a.rowid<=? ORDER BY a.rowid LIMIT ?',
                      (state['cursor'], state['end'], PAGE))
    failures, retired = [], 0
    for alert in rows:
        state['cursor'] = alert['seq']
        custodian = custodians.get(alert['role'])
        try:
            if custodian is None:
                raise Refusal('no actual owner qualification/evidence capability registered')
            custodian.progress_alert(store, alert['id'])
            retired += 1
        except Exception as exc:
            failures.append({'occurrence': alert['id'], 'role': alert['role'],
                             'owner': store.config['roles'].get(alert['role'], {}).get('owner'),
                             'observed_at': now, 'reason': str(exc)[:300]})
    if len(rows) < PAGE:
        state['cursor'] = state['end']
    state.update(next_at=now + store.config.get('recheck_seconds', 1), passes=state['passes'] + 1,
                 visited=len(rows), retired=retired, failures=failures)
    if failures and state['first_gap'] is None:
        state['first_gap'] = {'at': now, 'occurrence': failures[0]['occurrence'],
                              'role': failures[0]['role'], 'owner': failures[0]['owner'],
                              'reason': failures[0]['reason'], 'custody': 'original source rows and actual owner'}
    with store.tx():
        store.db.execute("INSERT INTO meta VALUES('custodian-progress',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (encode(state),))
    return state
