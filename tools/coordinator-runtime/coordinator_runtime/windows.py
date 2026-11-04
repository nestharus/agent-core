"""Accountable recurring allocation windows, separate from processing and slots.

No finite response graph is assumed. Every actual allocation is charged in its
write transaction. Exhaustion preserves the exact pending source for Work's
next boundary decision; ACK, END, age and settlement never renew this account.
Historical rows remain physically retained and subject to byte/file admission.
"""
import hashlib
import json

from .contracts import Backpressure, Refusal, digest, encode, required_text

KINDS = ('events', 'jobs', 'attempts', 'outboxes', 'decisions')
SCHEMA = """
CREATE TABLE IF NOT EXISTS service_windows(
 number INTEGER PRIMARY KEY,configuration TEXT NOT NULL,used TEXT NOT NULL,
 new_inputs INTEGER NOT NULL,actor TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
"""


def policy(config):
    value = config.get('window_service')
    if value is None:
        return None
    if config.get('finite_service') is not None:
        raise Refusal('terminal lifetime and recurring windows are separate modes')
    if (not isinstance(value, dict) or 'Work' not in config['roles'] or set(value) != {'tasks', 'max_new_inputs', 'batch_size', 'max_decisions'}
            or not isinstance(value['tasks'], list) or not value['tasks']
            or len(set(value['tasks'])) != len(value['tasks'])
            or set(value['tasks']) != set(config['tasks'])):
        raise Refusal('window service must retain every configured task and its routes')
    for key, maximum in [('max_new_inputs', 10000), ('batch_size', 64), ('max_decisions', 10000)]:
        if type(value[key]) is not int or not 1 <= value[key] <= maximum:
            raise Refusal('positive bounded window ' + key + ' required')
    for role in config['roles'].values():
        if set(role['routes']) - set(value['tasks']):
            raise Refusal('window service cannot drop a mixed-role choice')
    return value


def current(store):
    return store.one('SELECT * FROM service_windows ORDER BY number DESC LIMIT 1')


def initialize(store):
    if not policy(store.config) or current(store):
        return
    if any(store.one('SELECT 1 FROM ' + table + ' LIMIT 1') for table in ('events', 'jobs', 'attempts', 'outboxes')):
        raise Refusal('recurring accounts require a new journal; no retrospective duty adoption')
    store.db.execute('INSERT INTO service_windows VALUES(1,?,?,0,?,?,?)',
                     (digest(store.config), encode(dict.fromkeys(KINDS, 0)), store.config['roles']['Work']['owner'],
                      encode({'basis': 'new empty journal; explicit window_service configuration'}), store.clock()))


def charge(store, kind, *, new_input=False):
    if not store.config.get('window_service'):
        return
    if not store.db.in_transaction:
        raise Refusal('window allocations require the source write transaction')
    row = current(store)
    if not row or row['configuration'] != digest(store.config):
        raise Refusal('current allocation window/configuration missing')
    used = json.loads(row['used'])
    if new_input:
        if row['new_inputs'] >= store.config['window_service']['max_new_inputs']:
            raise Backpressure('Work-owned window boundary due; new input remains upstream unACKed')
        store.db.execute('UPDATE service_windows SET new_inputs=new_inputs+1 WHERE number=?', (row['number'],))
    if kind not in KINDS:
        return
    cap = (store.config['window_service']['max_decisions'] if kind == 'decisions' else
           store.config['limits'].get('max_' + kind, store.config['limits']['max_events']))
    if used[kind] >= cap:
        raise Backpressure('Work-owned window boundary due for ' + kind + '; all existing duties retained')
    used[kind] += 1
    store.db.execute('UPDATE service_windows SET used=? WHERE number=?', (encode(used), row['number']))


def basis(store):
    """Streaming full journal binding, including holds/results/consent history.

    This is a currentness witness, not a claim every duty is resolved. No debt
    body is truncated to fit a response envelope. Ordinary SQLite cooperating
    transaction semantics apply; this does not fence external writers/effects.
    """
    h = hashlib.sha256()
    for table in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = table[0]
        # Names originate in the inspected schema, not a message/receipt.
        h.update(encode(name).encode() + b'\n')
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid'):
            for value in row:
                body = value if isinstance(value, bytes) else encode(value).encode()
                h.update((b'B' if isinstance(value, bytes) else b'J') + str(len(body)).encode() + b':' + body)
            h.update(b'\n')
    return {'configuration': digest(store.config), 'window': current(store)['number'],
            'journal_sha256': h.hexdigest(),
            'custodians': {r: store.enrollment(r)['owner'] for r in store.config['roles']}}


def advance(store, actor, receipt):
    """Actual Work continues bounded allocations, never recycles duties or slots."""
    if not policy(store.config):
        raise Refusal('recurring allocation windows not selected')
    with store.tx():
        if actor != store.enrollment('Work')['owner']:
            raise Refusal('window boundary belongs to current enrolled Work owner')
        if not isinstance(receipt, dict) or set(receipt) != {'basis', 'target', 'reason', 'evidence', 'custody'}:
            raise Refusal('current basis, target/why, evidence and continuing custody required')
        expected = basis(store)
        if receipt['basis'] != expected:
            raise Refusal('window basis changed; retain old boundary decision without replay')
        for key in ('target', 'reason', 'evidence'):
            required_text(receipt[key], 'actual Work ' + key, 16000)
        if (not isinstance(receipt['custody'], dict) or set(receipt['custody']) != set(expected['custodians'])
                or any(not isinstance(v, dict) or set(v) != {'owner', 'evidence'}
                       or v['owner'] != expected['custodians'][r] for r, v in receipt['custody'].items())):
            raise Refusal('every continuing role duty needs its unchanged actual custodian attribution')
        for value in receipt['custody'].values():
            required_text(value['evidence'], 'continuing custody evidence', 4000)
        encoded = encode(receipt)
        if len(encoded.encode()) > store.config['limits']['max_result_bytes']:
            raise Refusal('window decision exceeds admitted result bytes')
        store.budget(None, len(encoded.encode()) + 2048)
        number = current(store)['number'] + 1
        store.db.execute('INSERT INTO service_windows VALUES(?,?,?,0,?,?,?)',
                         (number, digest(store.config), encode(dict.fromkeys(KINDS, 0)), actor, encoded, store.clock()))
    return {'window': number, 'basis': expected, 'actor': actor,
            'meaning': 'allocations continue; no processing, release, custody transfer or hold waiver'}
