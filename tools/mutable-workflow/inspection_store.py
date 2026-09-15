"""Transactional private inspection projections, not execution/policy authority.

Declared roles: orchestration, mapper, accessor, validator.
"""
import json
import uuid


def create(db):
    # Execute separately: executescript would commit a caller's transaction.
    db.execute('CREATE TABLE inspection_meta (id INTEGER PRIMARY KEY, epoch TEXT NOT NULL, '
               'head INTEGER NOT NULL, graph_cursor INTEGER NOT NULL, body TEXT NOT NULL)')
    db.execute('CREATE TABLE inspection_events (sequence INTEGER PRIMARY KEY, source TEXT NOT NULL, '
               'reference TEXT NOT NULL, summary TEXT NOT NULL, detail TEXT)')
    db.execute('CREATE TABLE inspection_attempts (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE INDEX inspection_event_sources ON inspection_events(source,sequence)')
    db.execute('CREATE TABLE inspection_exchanges (key TEXT PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('INSERT INTO inspection_meta VALUES (1,?,0,0,?)', (str(uuid.uuid4()), '{}'))


def enabled(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='inspection_meta'").fetchone() is not None


def append(db, source, reference, summary, detail=None):
    head = db.execute('SELECT head FROM inspection_meta WHERE id=1').fetchone()[0] + 1
    db.execute('INSERT INTO inspection_events VALUES (?,?,?,?,?)',
               (head, source, str(reference), json.dumps(summary),
                None if detail is None else json.dumps(detail)))
    db.execute('UPDATE inspection_meta SET head=? WHERE id=1', (head,))
    return head


def graph_summary(state):
    target = state['node_ids'][state['position']] if state['position'] < len(state['node_ids']) else None
    return dict(run_id=state['run_id'], status=state['status'], position=state['position'],
                target=target, active_attempt=state['active_attempt'],
                node_ids=state['node_ids'], nodes={key: node_summary(node) for key, node in state['nodes'].items()},
                attempts=state['attempts'], edit_count=len(state['edits']),
                policy_present=state['policy'] is not None,
                authority='caller worker registry; editor assertions are not authentication')


def node_summary(node):
    return dict(step_id=node['step']['id'], worker=node['step']['worker'], disposition=node['disposition'])


def graph(db, state, kind, detail):
    if not enabled(db):
        return  # Inspection indexing is explicitly selectable for existing runs.
    old = json.loads(db.execute('SELECT body FROM inspection_meta WHERE id=1').fetchone()[0])
    summary = graph_summary(state)
    change = dict(kind=kind, graph_cursor=state['cursor'], attempt_id=detail.get('attempt_id'),
                  actor=detail.get('actor'), authority_reference=state['cursor'],
                  removed_nodes=sorted(set(old.get('node_ids', [])) - set(state['node_ids'])),
                  relationship='same atomic change batch, not one-to-one replacement',
                  added_nodes=sorted(set(state['nodes']) - set(old.get('nodes', {}))))
    append(db, 'graph', state['cursor'], change)
    db.execute('UPDATE inspection_meta SET graph_cursor=?,body=? WHERE id=1',
               (state['cursor'], json.dumps(summary)))


def exchange_summary(value):
    response = value.get('response') or {}
    return dict(key=value['key'], id=value['id'], state=value['state'],
                application=value['application'], response_kind=response.get('kind'),
                owner=value['request']['config']['authority']['owner'],
                apply_edits=value['request']['config']['authority']['apply_edits'],
                invocation=value.get('invocation'), session=value.get('session'),
                continuity=value['continuity'], error_present=bool(value.get('error')),
                effects='unconfirmed' if value['state'] == 'pending' else 'not assessed',
                availability='unchecked; use evidence', basis_cursor=value['context']['cursor'])


def exchange(db, value):
    if not enabled(db):
        return
    summary = exchange_summary(value)
    revision = append(db, 'exchange', value['key'], summary, value)
    summary['revision'] = revision
    db.execute('INSERT INTO inspection_exchanges VALUES (?,?) ON CONFLICT(key) DO UPDATE SET body=excluded.body',
               (value['key'], json.dumps(summary)))


def attempt(db, value):
    if not enabled(db):
        return
    summary = {key: value.get(key) for key in ('id', 'outcome', 'orphaned', 'cancellation', 'credited')}
    summary.update(node_id=value['request']['node_id'], step_id=value['request']['step']['id'],
                   output_collected=value['output'] is not None,
                   effects='not assessed' if value['output'] is not None else 'unconfirmed')
    db.execute('INSERT INTO inspection_attempts VALUES (?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
               (value['id'], json.dumps(summary)))
