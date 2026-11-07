"""Finite actual reservation outcomes. No raw error, scope or source-body reads."""
from .contracts import Refusal

PREDICATES = (
    'enrollment', 'role-enabled', 'processing-task', 'owner-review', 'legacy-hold',
    'task-active', 'package-admission', 'outstanding-jobs', 'local-selection',
    'execution-capacity', 'same-package-outstanding', 'qa-admission', 'qa-phase',
    'qa-package-outstanding', 'qa-prior-admission', 'qa-prior-dependency',
    'integration-window', 'members', 'local-availability', 'member-processing',
    'job-budget', 'reservation', 'local-packet', 'local-qa-anchor', 'local-native-access',
    'local-active-jobs', 'local-capacity', 'local-resources', 'local-native-busy',
    'local-ordinary-busy', 'local-unknown-material', 'local-discovery',
    'local-scope-conflict', 'local-branch-conflict',
)
OUTCOMES = ('false', 'refusal', 'reserved')


def write(store, record):
    store.db.execute('INSERT OR REPLACE INTO reservation_outcomes VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', record)


class Evaluation:
    def __init__(self, store, row):
        self.store, self.row, self.predicate = store, row, 'enrollment'
        # Existing immutable intake hash and mapping metadata only. No event()
        # reconstruction, protected body read, scope lookup or diagnostic hash.
        source = store.one('SELECT hash FROM events WHERE id=?', (row['event'],))
        mapping = store.one('SELECT version FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (row['event'],))
        self.context = (row['event'], source['hash'], row['id'], row['task'], row['phase'],
                        store.processing.key if store.processing else None, store.controller,
                        mapping['version'] if mapping else 0)

    def __enter__(self):
        return self

    def at(self, predicate):
        assert predicate in PREDICATES
        self.predicate = predicate

    def finish(self, outcome):
        assert outcome in OUTCOMES
        record = (*self.context, self.store.clock(), 1, outcome, self.predicate)
        write(self.store, record)
        observations = getattr(self.store, '_reservation_observations', None)
        if observations is not None:
            observations.append(record)

    def failed(self, predicate):
        self.at(predicate)
        self.finish('false')

    def __exit__(self, kind, error, trace):
        if kind is not None and issubclass(kind, Refusal):
            self.finish('refusal')  # Fixed reached stage, never str(error).
        return False  # Preserve the original Refusal and traceback.


def view(runtime, key, event, state, responsibility, controller):
    unknown = {'available': False, 'current': False, 'outcome': 'not-evaluated',
               'predicate': None, 'reason': None, 'meaning': 'no exact current observation; skipped guards remain not-evaluated'}
    if not runtime.one("SELECT 1 AS present FROM sqlite_master WHERE type='table' AND name='reservation_outcomes'"):
        return unknown  # Read-only old journals are never migrated by this view.
    if not responsibility:
        return unknown
    queue = runtime.one('SELECT id,task,phase FROM queue WHERE event=?', (event,))
    if not queue:
        return unknown
    source = runtime.one('SELECT hash FROM events WHERE id=?', (event,))
    if (not source or source['hash'] != state['hash'] or queue['task'] != responsibility['task']
            or queue['phase'] != responsibility.get('phase', queue['phase'])):
        return {**unknown, 'outcome': 'stale', 'meaning': 'changed source or queue context; old reason withheld'}
    mapping = runtime.one('SELECT version FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (event,))
    version = mapping['version'] if mapping else 0
    # Compare all identities inside SQL. Never export an old foreign identity.
    placeholders = ','.join('?' for _ in PREDICATES)
    row = runtime.one(
        'SELECT current,valid,CASE WHEN current=1 AND valid=1 THEN predicate END AS predicate, '
        'CASE WHEN current=1 AND valid=1 THEN outcome END AS outcome, '
        'CASE WHEN current=1 AND valid=1 THEN observed END AS observed FROM ('
        'SELECT *,CASE WHEN source_hash=? AND queue=? AND task=? AND phase=? '
        'AND capability IS ? AND controller=? AND mapping_version=? THEN 1 ELSE 0 END AS current, '
        f'CASE WHEN schema_version=1 AND predicate IN ({placeholders}) AND outcome IN (?,?,?) '
        "AND typeof(observed) IN ('real','integer') AND observed>=0 AND observed<1e15 "
        "AND (outcome!='reserved' OR predicate='reservation') THEN 1 ELSE 0 END AS valid "
        'FROM reservation_outcomes WHERE event=?)',
        (state['hash'], queue['id'], queue['task'], queue['phase'], key, controller, version,
         *PREDICATES, *OUTCOMES, event))

    if not row:
        return unknown
    if not row['current']:
        return {**unknown, 'outcome': 'stale', 'meaning': 'changed attribution; old identity and reason withheld'}
    if not row['valid']:
        return {**unknown, 'outcome': 'unknown', 'meaning': 'malformed or unrecognized stored observation'}
    return {'available': True, 'current': True, 'schema_version': 1,
            'source': event, 'source_hash': state['hash'], 'task': responsibility['task'],
            'phase': queue['phase'], 'capability': key, 'controller': controller,
            'mapping_version': version, 'observed': row['observed'],
            'outcome': row['outcome'], 'predicate': row['predicate'], 'reason': row['predicate'],
            'same_controller': True, 'still_queued': responsibility['state']=='queued' and responsibility['job'] is None,
            'meaning': 'last actual exact-context evaluation; later guards not-evaluated; no fresh attempt, liveness, acceptance or clearance proof'}
