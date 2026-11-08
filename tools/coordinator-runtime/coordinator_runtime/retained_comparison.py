"""Read-only historical comparison, separate from processing/input authority.

Witnesses must be recorded while the original mapper can still authenticate
its exact launch. No backfill from an expired grant or forbidden old body.
SQLite immutability is cooperative integrity, never native-principal proof.
"""
from contextlib import nullcontext
import json
import hashlib
import math
from pathlib import Path

from .contracts import Refusal, digest, encode, ident, required_text
from . import configuration, resource_scopes

SCHEMA = """
CREATE TABLE IF NOT EXISTS retained_comparison_witnesses(
 job TEXT PRIMARY KEY, witness TEXT NOT NULL, scope TEXT NOT NULL, record TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS retained_comparison_witness_no_update
 BEFORE UPDATE ON retained_comparison_witnesses BEGIN SELECT RAISE(ABORT,'immutable retained comparison witness'); END;
CREATE TRIGGER IF NOT EXISTS retained_comparison_witness_no_delete
 BEFORE DELETE ON retained_comparison_witnesses BEGIN SELECT RAISE(ABORT,'immutable retained comparison witness'); END;
CREATE TABLE IF NOT EXISTS retained_comparison_grants(
 id TEXT PRIMARY KEY, issuer TEXT NOT NULL, selection TEXT NOT NULL, created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS retained_comparison_grant_no_update
 BEFORE UPDATE ON retained_comparison_grants BEGIN SELECT RAISE(ABORT,'immutable metadata-only grant'); END;
CREATE TRIGGER IF NOT EXISTS retained_comparison_grant_no_delete
 BEFORE DELETE ON retained_comparison_grants BEGIN SELECT RAISE(ABORT,'immutable metadata-only grant'); END;
CREATE TABLE IF NOT EXISTS retained_comparison_revocations(id TEXT PRIMARY KEY);
"""
MODE = 'retained-comparison-metadata-v1'
PROOF_FIELDS = ('grant_id', 'issued_by', 'authority', 'role_owner', 'task_hash',
                'admission_hash', 'prospective_epoch', 'delegated_by',
                'delegation_authority', 'processing_capability')


def _transaction(runtime):
    return nullcontext() if runtime.db.in_transaction else runtime.tx()


def _principal(runtime, boards):
    owner = runtime.config['roles']['Work']['owner']
    if runtime.config.get('software_delegation', {}).get('grantor') != owner:
        raise Refusal('genuine current Work data-access issuer required')
    board = boards.get('Work') if boards else None
    if not board or board.store.acting_session(owner) != owner:
        raise Refusal('authenticated current Work session required; request authorship is insufficient')
    board.metadata_authority(runtime)
    configuration.assert_current(runtime)
    configuration.assert_release(runtime)
    return owner


def _source(runtime):
    # Exact public comparison/authentication dependencies; no untracked module
    # discovery. The selected release gate separately checks its full closure.
    directory = Path(__file__).parent
    paths = [directory / name for name in ('retained_comparison.py', 'contracts.py',
        'configuration.py', 'resource_scopes.py', 'processing.py', 'prospective.py',
        'retained.py', 'board.py', 'software.py', 'report_repair.py', 'selected_source.py')]
    for path in paths:
        resource_scopes.root(str(path), runtime.config.get('artifact_exclusions', []))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _scope(runtime, scope):
    if not isinstance(scope, dict) or set(scope) != {'reads', 'writes'}:
        raise Refusal('exact explicit public reads/writes required')
    values = scope['reads'] + scope['writes'] if all(isinstance(scope[k], list) for k in scope) else None
    if not values or len(values) > 256 or any(not isinstance(p, str) for p in values):
        raise Refusal('bounded nonempty public footprint required')
    for value in values:
        resource_scopes.root(value, runtime.config.get('artifact_exclusions', []), metadata=False)
    return scope


def record_current(runtime, identity):
    """Explicit original-authority recording; not callable with a comparison key.

    The existing mapper supplies ALL original grant/epoch/task/material checks.
    An expired/unavailable original refuses; no lazy reconstruction is attempted.
    Opaque executor resources stay unknown without persisting their derivatives.
    """
    with _transaction(runtime):
        return _record_current(runtime, identity)


def _record_current(runtime, identity):
    if not runtime.processing or not runtime.processing.boards:
        raise Refusal('original processing authority and checkers required to record')
    _principal(runtime, runtime.processing.boards)
    task = runtime.config['tasks'][identity['task']]
    resource_scopes._native_resources(runtime, identity, task)
    cap, selection = runtime.processing.current()
    # Only original public task ceilings are releasable here. Native handles,
    # facade/cursor/history and capture namespaces remain opaque UNKNOWN
    # constraints: never export their paths/derivatives or stat them later.
    scope = _scope(runtime, dict(reads=sorted(set(task['effect_authority']['read_roots'] + [task['cwd']])), writes=[]))
    lineage = _lineage(runtime, identity['id'])
    if not lineage:
        raise Refusal('original linkage unavailable')
    policy = selection['service']['legacy_resources']['Reviews']
    record = dict(version=1, lineage=lineage, scope=scope,
        original_configuration=digest(runtime.config), original_capability=cap['id'],
        original_issuer=cap['issuer'],
        original_proof=dict(zip(PROOF_FIELDS, json.loads(lineage['proof']))),
        original_native_account={k: policy['native_review_return'].get(k) for k in
            ('version', 'source_task', 'package', 'grant', 'source_task_sha256',
             'review_policy_sha256', 'packet_sha256', 'expires')},
        unbounded=policy['unbounded'],
        # Evidence text is not exported. Never infer native ownership or close.
        opaque_constraints=['native-account', 'native-executor-state', 'history-and-capture-custody'],
        physical='UNKNOWN', rights='comparison only; original holds unchanged')
    witness = digest(record)
    runtime.db.execute('INSERT INTO retained_comparison_witnesses VALUES(?,?,?,?)',
                       (identity['id'], witness, digest(scope), encode(record)))
    return dict(job=identity['id'], witness=witness, scope=scope)


def _lineage(runtime, job):
    """Fixed journal projections only. No packet, native ID, return or task body."""
    proof = "json_extract(a.detail," + ','.join('?' for _ in PROOF_FIELDS) + ") AS proof,"
    return runtime.one("SELECT j.id,j.role,j.phase,j.task,j.package,j.active_attempt,"
        "json_extract(j.members,'$[0].event') AS event,json_extract(j.members,'$[0].hash') AS source_hash,"
        "a.job AS attempt_job,a.kind,a.controller,a.binding,"
        "json_extract(a.detail,'$.processing_capability') AS capability," + proof +
        "c.component,c.collector,x.capability AS context_capability,x.collector AS context_collector,x.created,"
        "e.role AS source_role,e.hash AS actual_source_hash,b.position AS source_birth,p.position AS job_birth,"
        "cap.issuer AS original_issuer,cap.created AS capability_created,ep.created AS epoch_created,"
        "ep.event_boundary AS epoch_event_boundary,ep.job_boundary AS epoch_job_boundary "
        'FROM jobs j JOIN attempts a ON a.id=j.active_attempt '
        'JOIN review_calls c ON c.attempt=a.id JOIN review_call_contexts snapshot ON snapshot.attempt=a.id '
        'JOIN review_contexts x ON x.component=c.component '
        "JOIN events e ON e.id=json_extract(j.members,'$[0].event') "
        'JOIN processing_source_positions b ON b.event=e.id JOIN prospective_job_positions p ON p.job=j.id '
        "JOIN processing_capabilities cap ON cap.id=json_extract(a.detail,'$.processing_capability') "
        "JOIN prospective_authorities ep ON ep.id=json_extract(a.detail,'$.software_authority.prospective_epoch') WHERE j.id=?",
        (*['$.software_authority.' + k for k in PROOF_FIELDS], job))


def select(runtime, boards, request):
    """Authenticate genuine Work and select exact metadata, never execution."""
    with _transaction(runtime):
        return _select(runtime, boards, request)


def _select(runtime, boards, request):
    issuer = _principal(runtime, boards)
    if not isinstance(request, dict) or set(request) != {'mode', 'purpose', 'expires', 'pins'} or request['mode'] != MODE:
        raise Refusal('exact metadata-only selection required; execution/input grants unsupported')
    required_text(request['purpose'], 'current scoped data-access purpose', 4000)
    expires = request['expires']
    if type(expires) not in {int, float} or not math.isfinite(expires) or expires <= runtime.clock():
        raise Refusal('finite current metadata-only expiry required')
    pins = request['pins']
    if not isinstance(pins, list) or not 1 <= len(pins) <= 32:
        raise Refusal('one to 32 exact original witness pins required')
    for pin in pins:
        _pin(runtime, pin)
    if len({p['job'] for p in pins}) != len(pins):
        raise Refusal('duplicate original witness pin')
    key = ident()
    selection = dict(request, configuration=digest(runtime.config), source=_source(runtime))
    runtime.db.execute('INSERT INTO retained_comparison_grants VALUES(?,?,?,?)',
                       (key, issuer, encode(selection), runtime.clock()))
    return dict(key=key, mode=MODE, issuer=issuer, execution=False, input=False)


def _pin(runtime, pin):
    if not isinstance(pin, dict) or set(pin) != {'job', 'witness', 'scope'}:
        raise Refusal('exact job/witness/public scope pin required')
    required_text(pin['job'], 'original job', 128)
    if not isinstance(pin['witness'], str) or len(pin['witness']) != 64 or any(c not in '0123456789abcdef' for c in pin['witness']):
        raise Refusal('exact original witness digest required')
    _scope(runtime, pin['scope'])


def revoke(runtime, boards, key):
    with _transaction(runtime):
        issuer = _principal(runtime, boards)
        row = runtime.one('SELECT issuer FROM retained_comparison_grants WHERE id=?', (key,))
        if not row or row['issuer'] != issuer:
            raise Refusal('only genuine metadata issuer can revoke its grant')
        runtime.db.execute('INSERT OR IGNORE INTO retained_comparison_revocations VALUES(?)', (key,))


def project(runtime, boards, key, job):
    with _transaction(runtime):
        return _project(runtime, boards, key, job)


def _project(runtime, boards, key, job):
    issuer = _principal(runtime, boards)
    row = runtime.one('SELECT issuer,selection FROM retained_comparison_grants WHERE id=?', (key,))
    if not row or row['issuer'] != issuer or runtime.one('SELECT id FROM retained_comparison_revocations WHERE id=?', (key,)):
        raise Refusal('current metadata-only grant absent/revoked/wrong issuer')
    selection = json.loads(row['selection'])
    if (selection['mode'] != MODE or selection['expires'] <= runtime.clock()
            or selection['configuration'] != digest(runtime.config) or selection['source'] != _source(runtime)):
        raise Refusal('metadata authority expired or current source/configuration changed')
    pin = next((p for p in selection['pins'] if p['job'] == job), None)
    if not pin:
        raise Refusal('original outside exact current metadata selection')
    _pin(runtime, pin)  # Entire declared map excluded BEFORE journal acquisition.
    source = runtime.one("SELECT e.hold IS NOT NULL AS held FROM jobs j JOIN events e ON e.id=json_extract(j.members,'$[0].event') WHERE j.id=?", (job,))
    if source and source['held']:
        raise Refusal('original source held before witness acquisition')
    row = runtime.one('SELECT record FROM retained_comparison_witnesses WHERE job=? AND witness=? AND scope=?',
                      (job, pin['witness'], digest(pin['scope'])))
    if not row:
        raise Refusal('authentic original witness unavailable; no backfill from old bodies')
    record = json.loads(row['record'])
    if digest(record) != pin['witness'] or record['scope'] != pin['scope'] or record['lineage'] != _lineage(runtime, job):
        raise Refusal('original immutable witness/linkage changed or unavailable')
    # State/hold labels grant no closure or access to their arbitrary bodies.
    state = runtime.one('SELECT hold_reason IS NOT NULL AS held,state,effects FROM jobs WHERE id=?', (job,))
    return dict(record, current_state=state, qualification='recorded possible footprint; no native-principal or physical-state proof')


def compare(runtime, boards, key, job, candidate):
    """Assess exact declared possible access. This never calls admission/start."""
    with _transaction(runtime):
        return _compare(runtime, boards, key, job, candidate)


def _compare(runtime, boards, key, job, candidate):
    _scope(runtime, candidate)  # Whole candidate exclusion before any metadata.
    record = _project(runtime, boards, key, job)
    original = record['scope']
    values = original['reads'] + original['writes'] + candidate['reads'] + candidate['writes']
    # All lexical checks complete before the first stat, including a late
    # excluded candidate. Alias/metadata failure is UNKNOWN, never disjoint.
    for value in values:
        resource_scopes.root(value, runtime.config.get('artifact_exclusions', []), metadata=False)
    return _assessment(runtime, record, candidate)


def _assessment(runtime, record, candidate):
    try:
        original = record['scope']
        exclusions = runtime.config.get('artifact_exclusions', [])
        for value in original['reads'] + original['writes'] + candidate['reads'] + candidate['writes']:
            resource_scopes.root(value, exclusions)
        conflict = any(resource_scopes.overlaps(a, b) for a in candidate['writes'] for b in original['reads'] + original['writes'])
        conflict = conflict or any(resource_scopes.overlaps(a, b) for a in candidate['reads'] for b in original['writes'])
        status = 'CONFLICT' if conflict else 'UNKNOWN'
        # A Source retains an unverified physical account, and original unbounded
        # holds cannot become finite just because the named paths are disjoint.
        return dict(status=status, scoped_overlap=conflict, scoped_disjoint=not conflict, unbounded=record['unbounded'],
                    physical=record['physical'], opaque_constraints=record['opaque_constraints'],
                    eligible=False, rights=MODE)
    except (Refusal, OSError):
        return dict(status='UNKNOWN', scoped_overlap=None, unbounded=record['unbounded'],
                    physical='UNKNOWN', opaque_constraints=record['opaque_constraints'],
                    eligible=False, rights=MODE)
