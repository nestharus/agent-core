"""Producer recovery in the existing journal; no account/store effects.

Declared roles: orchestration, validator, mapper, accessor, predicate.
Launch context is written by the dispatcher before calling the adapter. Results,
original collection and effect/consumer state remain in their existing tables.
This is recovery context, never permission to replay an effect or claim that an
unknown residual was created, owned, headless, retired or physically removed.
"""

import json
from contextlib import nullcontext

from .contracts import Refusal, digest, encode

SCHEMA = """
CREATE TABLE IF NOT EXISTS oneoff_recovery(
 attempt TEXT PRIMARY KEY REFERENCES attempts(id),collector TEXT NOT NULL,
 created REAL NOT NULL,launch TEXT NOT NULL,launch_hash TEXT NOT NULL,
 collection_hash TEXT);
CREATE TABLE IF NOT EXISTS oneoff_terminal_recovery(
 attempt TEXT PRIMARY KEY REFERENCES oneoff_recovery(attempt),
 reserved_bytes INTEGER NOT NULL,body TEXT,sha256 TEXT,created REAL);
"""
COLLECTION = ('id', 'controller', 'kind', 'event', 'job', 'binding', 'profile',
              'session', 'turn', 'ended', 'exit', 'collected', 'capture',
              'cleanup', 'result', 'error', 'detail')


def launch_context(store, row, prompt, spec, schema):
    job = store.job(row['job']) if row['job'] else None
    return {'prompt': prompt, 'spec': spec, 'schema': schema,
            'attempt': row['id'], 'kind': row['kind'], 'collector': row['controller'],
            'binding': json.loads(row['binding']), 'profile': row['profile'],
            'event': row['event'], 'job': row['job'],
            'members': json.loads(job['members']) if job else [],
            'configuration': digest(store.config),
            'recovery_scope': 'durable launch/result/source context; no effect replay',
            'exact_session_after_exit': False}


def terminal_reserve(store):
    return 4 * store.config['limits']['max_result_bytes'] + 4096


def reserved_bytes(store):
    return store.one('SELECT COALESCE(SUM(r.reserved_bytes),0) AS bytes '
                     'FROM oneoff_terminal_recovery r JOIN attempts a ON a.id=r.attempt '
                     'WHERE r.body IS NULL AND a.collected IS NULL')['bytes']


def prepare(store, attempt, prompt, spec, schema):
    """Only the real unstarted reservation can receive a launch snapshot."""
    if spec.get('exact_session_after_exit'):
        raise Refusal('exact-session recovery after owner exit is unsupported by the ephemeral adapter; retain duty without launching')
    with store.tx():
        row = store.attempt(attempt)
        require_unstarted(store, row)
        launch = launch_context(store, row, prompt, spec, schema)
        body = encode(launch)
        reserve = terminal_reserve(store)
        store.budget(None, len(body.encode()) + reserve + 4096)
        store.db.execute('INSERT INTO oneoff_recovery VALUES(?,?,?,?,?,NULL)',
                         (attempt, store.controller, store.clock(), body, digest(launch)))
        store.db.execute('INSERT INTO oneoff_terminal_recovery(attempt,reserved_bytes) VALUES(?,?)',
                         (attempt, reserve))


def checkpoint(store, attempt, outcome, evidence=None):
    """Durable bounded return BEFORE ephemeral teardown; no completion inference.

    Original collection remains separate. A refused/partial checkpoint preserves
    the recovery duty; it does not certify adequate recovery or release a hold.
    """
    with (nullcontext() if store.db.in_transaction else store.tx(collection=attempt)):
        retained = store.one('SELECT * FROM oneoff_terminal_recovery WHERE attempt=?', (attempt,))
        if retained is None:
            return False  # Legacy/non-dispatch caller has no registered coverage.
        row = store.attempt(attempt)
        require_checkpoint(store, row, retained)
        if retained['body'] is not None:
            return  # First pre-teardown return is immutable; collection adds later facts.
        body = encode({'result': outcome.get('result'), 'error': outcome.get('error'),
                       'detail': outcome.get('detail', {}), 'evidence': evidence,
                       'meaning': 'pre-teardown context, not process END or processing completion'})
        if len(body.encode()) > retained['reserved_bytes']:
            raise Refusal('terminal recovery exceeds its finite launch reservation; recovery remains unqualified')
        store.db.execute('UPDATE oneoff_terminal_recovery SET body=?,sha256=?,created=? WHERE attempt=?',
                         (body, digest(json.loads(body)), store.clock(), attempt))
    return True


def require_checkpoint(store, row, retained):
    if (retained is None or row['controller'] != store.controller
            or row['collected'] is not None or row['begin'] is None or row['state'] != 'running'):
        raise Refusal('terminal recovery requires the original uncollected producer reservation')


def require_unstarted(store, row):
    if (row['controller'] != store.controller or row['state'] != 'reserved'
            or row['begin'] is not None or row['collected'] is not None):
        raise Refusal('launch recovery requires the original controller and unstarted reservation')
    if store.one('SELECT attempt FROM oneoff_recovery WHERE attempt=?', (row['id'],)):
        raise Refusal('original launch context already exists; no replacement or replay')


def collection_digest(row):
    return digest({key: row[key] for key in COLLECTION})


def collected(store, attempt):
    """Called inside original collection's existing transaction, never by a model."""
    capsule = store.one('SELECT collector,collection_hash FROM oneoff_recovery WHERE attempt=?', (attempt,))
    if capsule is None:
        return  # Historical/unregistered attempts gain no retrospective coverage.
    row = store.attempt(attempt)
    if not store.db.in_transaction or capsule['collector'] != store.controller or row['controller'] != store.controller:
        raise Refusal('launch snapshot collection belongs to its original collector')
    if capsule['collection_hash'] is not None:
        raise Refusal('original recovery collection cannot be replaced')
    store.db.execute('UPDATE oneoff_recovery SET collection_hash=? WHERE attempt=?',
                     (collection_digest(row), attempt))


def snapshot(store, attempt):
    """Recover exact context after owner exit/restart without resuming a session.

    The caller must already have lawful journal/source access. Recheck current
    execution/privacy admission BEFORE acquiring a launch or result body.
    """
    store.require_attempt_execution_open(attempt)
    store.authorize_preparation(attempt)
    row = store.attempt(attempt)
    capsule = store.one('SELECT * FROM oneoff_recovery WHERE attempt=?', (attempt,))
    if capsule is None:
        raise Refusal('no producer launch snapshot; original custodian retains the coverage gap')
    launch = json.loads(capsule['launch'])
    if capsule['launch_hash'] != digest(launch) or capsule['collector'] != row['controller']:
        raise Refusal('original launch source/collector changed')
    if capsule['collection_hash'] != collection_digest(row):
        raise Refusal('original collection missing or changed; recovery/effect duty remains held')
    terminal = store.one('SELECT body,sha256 FROM oneoff_terminal_recovery WHERE attempt=?', (attempt,))
    if terminal and terminal['body'] is not None and terminal['sha256'] != digest(json.loads(terminal['body'])):
        raise Refusal('original terminal recovery context changed')
    return {'launch': launch, 'launch_hash': capsule['launch_hash'],
            'collection': {key: row[key] for key in COLLECTION},
            'collection_hash': capsule['collection_hash'],
            'pre_teardown': json.loads(terminal['body']) if terminal and terminal['body'] else None,
            'source_custody': 'existing events/results/artifact_blobs; retain their existing holds',
            'permission_to_replay': False}


def source_events(store, row):
    if row['job']:
        job = store.job(row['job'])
        return [event_metadata(store, member['event']) for member in json.loads(job['members'])]
    return [event_metadata(store, row['event'])] if row['event'] else []


def event_metadata(store, event):
    row = store.one('SELECT id,processed_at,hold FROM events WHERE id=?', (event,))
    if row is None:
        raise Refusal('original processing source unavailable; retain custody')
    return row


def retirement_state(store, attempt):
    """Exact existing processing+24h/all-hold gate; no session deletion grant."""
    from .cleanup import eligible_event
    store.require_attempt_execution_open(attempt)
    row = store.attempt(attempt)
    capsule = store.one('SELECT collection_hash FROM oneoff_recovery WHERE attempt=?', (attempt,))
    if not capsule or capsule['collection_hash'] != collection_digest(row):
        return 'held-original-recovery-gap'
    if (row['collected'] is None or row['ended'] is None or row['capture'] != 'complete'
            or row['error'] or row['cleanup'] not in {'done', 'owned-ephemeral-lifecycle-observed'}):
        return 'held-original-collection-or-capture'
    events = source_events(store, row)
    if not events or not all(eligible_event(store, event) for event in events):
        return 'held-processing-24h-or-dependencies'
    return 'processing-window-qualified-custodian-still-required'


def recovery_hold(store, row):
    capsule = store.one('SELECT * FROM oneoff_recovery WHERE attempt=?', (row['id'],))
    if capsule is None:
        return False  # No retroactive ownership/coverage or freeze of old work.
    terminal = store.one('SELECT body,sha256 FROM oneoff_terminal_recovery WHERE attempt=?', (row['id'],))
    if terminal is None or terminal_changed(terminal):
        return True
    if row['cleanup'] == 'owned-ephemeral-lifecycle-observed' and terminal['body'] is None:
        return True
    return (capsule['collector'] != row['controller']
            or capsule['launch_hash'] != digest(json.loads(capsule['launch']))
            or capsule['collection_hash'] != collection_digest(row))


def terminal_changed(terminal):
    return terminal['body'] is not None and terminal['sha256'] != digest(json.loads(terminal['body']))


def residual_handoff(store, attempt):
    """Known producer observation only; no arbitrary-ID registration/inventory."""
    store.require_attempt_execution_open(attempt)
    row = store.attempt(attempt)
    detail = json.loads(row['detail'])
    residual = detail.get('session_residuals', {})
    known = row['session']
    observed = (detail.get('thread_start') == 'owned-root-observed'
                and residual.get('known_thread') == known and known is not None)
    return {'attempt': attempt, 'original_collector': row['controller'],
            'record': known if observed else None,
            'producer_observed_root': observed,
            'processing': retirement_state(store, attempt),
            'residual_state': 'held-current-custodian-required',
            'answer_collector': store.config['actor'],
            'missing': ['actual lawful current session/store custodian and current effect authority',
                        'current version/endpoint and exact cascade/auxiliary applicability',
                        'independent headless and human/current-use facts for every cascade member',
                        'all recovery/privacy/custody/consumer/effect holds and actual receipts'],
            'compatibility': 'pinned cleaner requires 0.166.0/exclusive maintenance; 0.167.0 schema alone is insufficient',
            'automatic_delete': False, 'physical_reclamation': 'unknown'}
