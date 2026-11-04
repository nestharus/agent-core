"""Prospective terminal-work credits; never retrofit old responsibility.

Count credits reserve the full failure/owner-correction tail before intake.
Byte/file admission remains subject to the existing measured resource fences:
logical credits are not a reservation of physical SQLite/WAL or disk space.
"""
import json

from .contracts import Backpressure, Refusal, digest, encode

KINDS = ('events', 'jobs', 'attempts', 'outboxes')
SCHEMA = """
CREATE TABLE IF NOT EXISTS duty_accounts(
 event TEXT PRIMARY KEY,owner TEXT NOT NULL,configuration TEXT NOT NULL,
 plan TEXT NOT NULL,remaining TEXT NOT NULL,created REAL NOT NULL);
"""


def policy(config):
    selected = config.get('finite_service')
    if selected is None:
        return None
    if (not isinstance(selected, dict) or set(selected) != {'tasks', 'max_admitted'}
            or type(selected['max_admitted']) is not int or not 1 <= selected['max_admitted'] <= 1000
            or not isinstance(selected['tasks'], list) or not selected['tasks']
            or len(selected['tasks']) != len(set(selected['tasks']))):
        raise Refusal('finite service needs explicit terminal tasks and bounded admission count')
    for name in selected['tasks']:
        task = config['tasks'].get(name)
        if (not task or task['role'] not in {'Work', 'Branch', 'Reviews', 'QA'}
                or task['phase'] == 'integrator' or task.get('execution') == 'owner'
                or task.get('effects') != 'none' or task.get('responses')
                or task.get('software_handoffs') or task.get('routine_completion')
                or task.get('ordinary_effects') or task.get('require_package_scope')):
            raise Refusal('finite service supports terminal no-effect non-batched tasks only')
    return selected


def plan(config):
    # Initial task plus one automatic recovery and at most C owner corrections.
    # Each correction can require a diagnosis and one remaining task attempt.
    corrections = config['limits'].get('max_owner_corrections', 4)
    tasks = 2 + corrections
    diagnoses = 1 + corrections
    # Each task can owe 16 explicit handoffs, an owner report and a question.
    # No effects/publications/response recursion is admitted by policy().
    outboxes = 18 * tasks
    # An interrupted partial plan can grow monotonically one delivery at a time;
    # every distinct outgoing-plan event can require classification + diagnosis.
    events = 1 + outboxes
    # Each event also has up to C genuine owner input decisions, each of
    # which can require a fresh classifier. These are not free retries.
    return {'events': events, 'jobs': 1, 'attempts': (2 + corrections) * events + tasks + diagnoses,
            'outboxes': outboxes}


def root(store, event=None, job=None):
    if job:
        members = json.loads(store.job(job)['members'])
        if len(members) != 1:
            return None  # Batched/legacy jobs do not borrow terminal credits.
        event = members[0]['event']
    seen = set()
    while event and event not in seen:
        seen.add(event)
        row = store.one('SELECT * FROM duty_accounts WHERE event=?', (event,))
        if row:
            return row
        row = store.one('SELECT parent FROM events WHERE id=?', (event,))
        event = row['parent'] if row else None
    return None


def reserved(store):
    totals = dict.fromkeys(KINDS, 0)
    for row in store.rows('SELECT remaining FROM duty_accounts'):
        for key, count in json.loads(row['remaining']).items():
            totals[key] += count
    return totals


def admit(store, event):
    selected = policy(store.config)
    if not selected:
        return
    # Internal outgoing-plan events are created by the original source, not new
    # external admissions. No caller-supplied ancestry can inherit credits.
    if event.get('parent') or event.get('source_delivery'):
        raise Refusal('finite service does not admit recursive/foreign-store input')
    legacy = store.one('SELECT e.id FROM events e WHERE e.processed_at IS NULL '
                       'AND (e.parent IS NULL OR NOT EXISTS (SELECT 1 FROM events p WHERE p.id=e.parent)) '
                       'AND NOT EXISTS (SELECT 1 FROM duty_accounts d WHERE d.event=e.id) LIMIT 1')
    if legacy or any(root(store, job=j['id']) is None for j in store.rows("SELECT id FROM jobs WHERE state!='closed'")):
        raise Backpressure('unaccounted existing outgoing duties; preserve them before prospective expansion')
    routes = event.get('allowed_tasks', store.config['roles'][event['role']].get('routes', []))
    if (not routes or set(routes) - set(selected['tasks'])
            or any(store.config['tasks'][n]['role'] != event['role'] for n in routes)):
        raise Refusal('incoming complete task choices exceed the terminal service envelope')
    if store.db.execute('SELECT COUNT(*) FROM duty_accounts').fetchone()[0] >= selected['max_admitted']:
        raise Backpressure('finite admitted lifetime population reached; existing duties retained')
    footprint, held, usage = plan(store.config), reserved(store), store.usage()
    for kind in KINDS:
        cap = store.config['limits'].get('max_' + kind, store.config['limits']['max_events'])
        if usage[kind] + held[kind] + footprint[kind] > cap:
            raise Backpressure('complete downstream ' + kind + ' credits cannot fit before intake')
    owner = store.enrollment(event['role'])['owner']
    store.db.execute('INSERT INTO duty_accounts VALUES(?,?,?,?,?,?)',
                     (event['id'], owner, digest(store.config), encode(footprint), encode(footprint), store.clock()))


def charge(store, kind, *, event=None, job=None):
    """Inside the allocating transaction; failed effects roll credits back too."""
    account = root(store, event, job)
    if not account or kind not in KINDS:
        return
    remaining = json.loads(account['remaining'])
    if remaining[kind] <= 0:
        raise Backpressure('admitted downstream allowance exhausted; exact source stays held')
    remaining[kind] -= 1
    store.db.execute('UPDATE duty_accounts SET remaining=? WHERE event=?', (encode(remaining), account['event']))


def check(store, usage, kind):
    if kind not in KINDS:
        return
    cap = store.config['limits'].get('max_' + kind, store.config['limits']['max_events'])
    if usage[kind] + reserved(store)[kind] >= cap:
        raise Backpressure('count capacity reserved for already-admitted outgoing duties')
