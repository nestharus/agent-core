"""Accountable recurring allocation windows, separate from processing and slots.

No finite response graph is assumed. Every actual allocation is charged in its
write transaction. Work may explicitly delegate a finite set of future window
boundaries to its continuing capability. ACK, END, age and settlement never
renew this account.
Historical rows remain physically retained and subject to byte/file admission.
"""
import json
import math
from contextlib import nullcontext

from .contracts import Backpressure, Refusal, digest, encode, required_text

KINDS = ('events', 'jobs', 'attempts', 'outboxes', 'decisions')
SCHEMA = """
CREATE TABLE IF NOT EXISTS service_windows(
 number INTEGER PRIMARY KEY,configuration TEXT NOT NULL,used TEXT NOT NULL,
 new_inputs INTEGER NOT NULL,actor TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS service_window_allocations(
 number INTEGER PRIMARY KEY REFERENCES service_windows(number),capability TEXT NOT NULL,
 authority_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS allocation_revision(name TEXT PRIMARY KEY,token TEXT NOT NULL);
"""


def revision_schema(store):
    return store.rows("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")


def revision_triggers(schema):
    for row in schema:
        if row['type'] != 'table' or row['name'].startswith('sqlite_') or row['name'] == 'allocation_revision':
            continue
        table = '"' + row['name'].replace('"', '""') + '"'
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            name = 'allocation_revision_' + digest([row['name'], operation])
            literal = "'" + row['name'].replace("'", "''") + "'"
            yield name, (f'CREATE TRIGGER "{name}" AFTER {operation} ON {table} '
                         f'BEGIN UPDATE allocation_revision SET token=hex(randomblob(32)) WHERE name={literal}; END')


def prepare_revision(store):
    """Install cooperative mutation witnesses without selecting any source row.

    Bootstrap covers subsequent mutations only. Installation changes the token,
    invalidating earlier witnesses. No historical body/key/size is inspected.
    """
    with store.tx():
        schema = revision_schema(store)
        existing = {r['name']: r['sql'] for r in schema if r['type'] == 'trigger'}
        for row in schema:
            if row['type'] == 'table' and not row['name'].startswith('sqlite_') and row['name'] != 'allocation_revision':
                store.db.execute('INSERT OR IGNORE INTO allocation_revision VALUES(?,hex(randomblob(32)))', (row['name'],))
        for name, sql in revision_triggers(schema):
            if name in existing:
                if existing[name] != sql:
                    raise Refusal('allocation revision trigger changed; explicit source recovery required')
            else:
                store.db.execute(sql)
                store.db.execute('UPDATE allocation_revision SET token=hex(randomblob(32))')


def revision(store):
    schema = revision_schema(store)
    existing = {r['name']: r['sql'] for r in schema if r['type'] == 'trigger'}
    if any(existing.get(name) != sql for name, sql in revision_triggers(schema)):
        raise Refusal('allocation revision coverage changed; reopen current source before taking a fresh basis')
    tokens = {r['name']: r['token'] for r in store.rows('SELECT name,token FROM allocation_revision ORDER BY name')}
    tables = {r['name'] for r in schema if r['type'] == 'table' and not r['name'].startswith('sqlite_') and r['name'] != 'allocation_revision'}
    if not tables <= tokens.keys():
        raise Refusal('allocation revision absent; no inferred currentness')
    return {'tokens': tokens, 'schema': digest(schema),
            'sequences': store.rows('SELECT name,seq FROM sqlite_sequence ORDER BY name'),
            'meaning': 'cooperative protocol mutation witness since bootstrap; no body read, size, integrity, whole-read or hostile-writer isolation attestation'}


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


def custodians(store):
    """Custody survives stopped intake; this does not reopen any enrollment."""
    owners = {r['role']: r['owner'] for r in store.rows('SELECT role,owner FROM enrollments')}
    if owners != {r: value['owner'] for r, value in store.config['roles'].items()}:
        raise Refusal('original allocation custodians differ from current role owners')
    return owners


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
    row = allocation(store, 'events' if new_input else kind, new_input=new_input)
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
    """Boundary currentness, without acquiring retained source bodies or keys.

    The revision detects protocol writes, including writes to opaque custody,
    across connections. It does not establish the truth/integrity of any body;
    applicable source guards and body validation remain independently required.
    """
    row = store.one('SELECT number,configuration,used,new_inputs,actor,created FROM service_windows ORDER BY number DESC LIMIT 1')
    if not row:
        raise Refusal('current allocation window missing')
    identity = store.path.stat()
    return {'configuration': digest(store.config), 'window': row['number'],
            'allocation': row, 'journal_revision': revision(store),
            'runtime': {'path': str(store.path), 'dev': identity.st_dev, 'ino': identity.st_ino,
                        'actor': store.config['actor']},
            'custodians': custodians(store)}


def validate_receipt(receipt, expected):
    if not isinstance(receipt, dict) or set(receipt) != {'basis', 'target', 'reason', 'evidence', 'custody'}:
        raise Refusal('current basis, target/why, evidence and continuing custody required')
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


def validate_delegation(store, selection):
    authority = selection['service'].get('allocations')
    if authority is None:
        return  # Historical/noncontinuing procedures retain manual boundaries.
    if (not policy(store.config) or not isinstance(authority, dict)
            or set(authority) != {'basis', 'target', 'reason', 'evidence', 'custody', 'expires', 'max_windows'}
            or type(authority['expires']) not in {int, float} or not math.isfinite(authority['expires'])
            or authority['expires'] <= store.clock()
            or type(authority['max_windows']) is not int or not 1 <= authority['max_windows'] <= 10000):
        raise Refusal('explicit finite continuing allocation authority, expiry and window ceiling required')
    validate_receipt({k: v for k, v in authority.items() if k not in {'expires', 'max_windows'}}, basis(store))
    if store.config['software_delegation']['grantor'] != authority['basis']['custodians']['Work']:
        raise Refusal('continuing allocations require genuine original Work issuer and custodian')


def append(store, actor, receipt, capability=None, authority_hash=None):
    encoded = encode(receipt)
    if len(encoded.encode()) > store.config['limits']['max_result_bytes']:
        raise Refusal('window decision exceeds admitted result bytes')
    store.budget(None, len(encoded.encode()) + 2048)
    number = current(store)['number'] + 1
    store.db.execute('INSERT INTO service_windows VALUES(?,?,?,0,?,?,?)',
                     (number, digest(store.config), encode(dict.fromkeys(KINDS, 0)), actor, encoded, store.clock()))
    if capability is not None:
        store.db.execute('INSERT INTO service_window_allocations VALUES(?,?,?)', (number, capability, authority_hash))
    return number


def allocation(store, kind, *, new_input=False):
    """Choose a window within the source transaction; never reattribute old use."""
    row = current(store)
    if not row:
        raise Refusal('current allocation window/configuration missing')
    cap = selection = authority = None
    if store.processing:
        cap, selection = store.processing.current()
        authority = selection.get('service', {}).get('allocations')
    if authority is not None:
        owners = custodians(store)
        if (cap['issuer'] != owners['Work'] or cap['issuer'] != store.config['software_delegation']['grantor']
                or authority['basis']['configuration'] != digest(store.config)
                or {r: v['owner'] for r, v in authority['custody'].items()} != owners
                or store.clock() >= (__import__(__package__+'.report_repair', fromlist=['lease_deadline']).lease_deadline(store) or authority['expires'])):
            raise Refusal('continuing allocation authority expired/borrowed or custody/configuration changed')
        anchor = authority['basis']['window']
        link = store.one('SELECT capability,authority_hash FROM service_window_allocations WHERE number=?', (row['number'],))
        if (row['number'] != anchor and link != {'capability': cap['id'], 'authority_hash': digest(authority)}
                or row['number'] == anchor and row['configuration'] != authority['basis']['allocation']['configuration']):
            raise Refusal('window outside original continuing allocation authority; no mixed-original adoption')
    used = json.loads(row['used'])
    limit = (store.config['window_service']['max_decisions'] if kind == 'decisions' else
             store.config['limits'].get('max_' + str(kind), store.config['limits']['max_events']))
    due = (row['configuration'] != digest(store.config)
           or new_input and row['new_inputs'] >= store.config['window_service']['max_new_inputs']
           or kind in KINDS and used[kind] >= limit)
    if not due:
        return row
    if authority is None:
        if row['configuration'] != digest(store.config):
            raise Refusal('current allocation window/configuration missing')
        raise Backpressure('Work-owned window boundary due; existing duties and upstream input retained')
    count = store.one('SELECT COUNT(*) AS n FROM service_window_allocations WHERE capability=?', (cap['id'],))['n']
    from .report_repair import lease_record
    amendment = lease_record(store, cap['id'])
    maximum = amendment['plan']['max_windows'] if amendment else authority['max_windows']
    if count >= maximum:
        raise Backpressure('continuing allocation authority exhausted; no renewal, refund or duty release')
    expected = basis(store)
    receipt = {'basis': expected, 'capability': cap['id'], 'authority_hash': digest(authority),
               'ordinal': count + 1, 'target': authority['target'], 'reason': authority['reason'],
               'evidence': authority['evidence'], 'custody': authority['custody']}
    append(store, cap['issuer'], receipt, cap['id'], digest(authority))
    return current(store)


def preflight_input(store):
    """Before upstream acquisition, select at most the remaining bounded batch."""
    if not policy(store.config):
        return None
    with (store.tx() if not store.db.in_transaction else nullcontext()):
        row = allocation(store, 'events', new_input=True)
        return min(store.config['window_service']['max_new_inputs'] - row['new_inputs'],
                   store.config['limits']['max_events'] - json.loads(row['used'])['events'])


def advance(store, actor, receipt):
    """Actual Work continues bounded allocations, never recycles duties or slots."""
    if not policy(store.config):
        raise Refusal('recurring allocation windows not selected')
    with store.tx():
        if actor != store.enrollment('Work')['owner']:
            raise Refusal('window boundary belongs to current enrolled Work owner')
        expected = basis(store)
        validate_receipt(receipt, expected)
        number = append(store, actor, receipt)
    return {'window': number, 'basis': expected, 'actor': actor,
            'meaning': 'allocations continue; no processing, release, custody transfer or hold waiver'}
