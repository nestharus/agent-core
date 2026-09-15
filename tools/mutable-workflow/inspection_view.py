"""Compact private snapshots and append-only source-bound change pages.

Declared roles: orchestration, parser, mapper, accessor, validator, formatter.
"""
import base64
from contextlib import closing
import json
import sys
from pathlib import Path

import agent_store
import inspection_store as store
from runtime import connect, exclusive, load, require


NEXT = dict(ready='resume selects target after original executor releases ownership',
            running='original collector owns attempt; inspect evidence, not a liveness claim',
            success='traversal exhausted; caller still owns obligations and disposition',
            failure='inspect failed attempt; caller must decide new intent',
            judgment='caller judgment required before new intent',
            ambiguous='reconcile original effects with owner; no automatic replay',
            cancelled='caller must decide new intent; cancellation cause/effects remain unknown',
            aborted='scheduling stopped, not all effects or deliveries terminated')


def encode(value):
    return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).decode()


def decode(token):
    try:
        value = json.loads(base64.b64decode(token, altchars=b'-_', validate=True))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('invalid inspection cursor encoding') from exc
    require(isinstance(value, dict) and set(value) == {'version', 'sources'}, 'invalid inspection cursor fields')
    require(type(value['version']) is int and value['version'] == 1, 'unsupported inspection cursor version')
    require(isinstance(value['sources'], list), 'invalid cursor sources')
    for source in value['sources']:
        validate_source_cursor(source)
    return value


def validate_source_cursor(source):
    require(isinstance(source, dict) and set(source) == {'path', 'run_id', 'epoch', 'position'},
            'invalid source cursor fields')
    require(all(isinstance(source[key], str) and source[key] for key in ('path', 'run_id', 'epoch')),
            'invalid source cursor identity')
    require(type(source['position']) is int and source['position'] >= 0, 'invalid cursor position')


def sources(directories, token):
    paths = [str(Path(path).resolve()) for path in directories]
    require(paths and len(set(paths)) == len(paths), 'unique run directories required')
    previous = decode(token)['sources'] if token is not None else [None] * len(paths)
    require(len(paths) == len(previous), 'foreign cursor source set; restart without cursor')
    return list(zip(paths, previous))


def page(directories, token=None, limit=100):
    require(type(limit) is int and 1 <= limit <= 1000, 'limit must be 1..1000 per source')
    values = [read_source(Path(path), prior, limit) for path, prior in sources(directories, token)]
    return dict(version=1, sources=values, cursor=encode(dict(version=1, sources=[v['cursor'] for v in values])),
                has_more=any(v['has_more'] for v in values),
                consistency='each source is one SQLite snapshot; sources sampled in order, not a global atomic snapshot',
                privacy='whole-private-run readers only; payloads omitted, labels/identifiers are not redacted',
                coverage='graph and exchange commits in listed runs; external policy only if explicitly published; '
                         'filesystem/session/owner samples are not journaled changes')


def read_source(directory, prior, limit):
    with closing(connect(directory)) as db:
        return snapshot(db, directory, prior, limit)


def metadata(db):
    require(store.enabled(db), 'inspection index unavailable; use inspect for audited history or explicitly index this run')
    row = db.execute('SELECT epoch,head,graph_cursor,body FROM inspection_meta WHERE id=1').fetchone()
    require(row is not None, 'missing inspection metadata; restore intact storage')
    epoch, head, graph_cursor, body = row
    count, low, high = db.execute('SELECT count(*),min(sequence),max(sequence) FROM inspection_events').fetchone()
    require(count == head and low == 1 and high == head, 'missing inspection events; restore intact storage')
    require(db.execute('SELECT count(*) FROM state WHERE id=1').fetchone()[0] == 1, 'missing durable state')
    event_count, event_low, event_high = db.execute('SELECT count(*),min(cursor),max(cursor) FROM events').fetchone()
    require(event_low == 1 and event_count == event_high == graph_cursor, 'graph/index history mismatch; full audit required')
    current = json.loads(body)
    require(db.execute('SELECT count(*) FROM attempts').fetchone()[0] == len(current['attempts']),
            'attempt/index count mismatch; full audit required')
    require(db.execute('SELECT count(*) FROM inspection_attempts').fetchone()[0] == len(current['attempts']),
            'attempt projection count mismatch; restore intact storage')
    validate_exchange_count(db)
    return epoch, head, graph_cursor, current


def validate_exchange_count(db):
    count = db.execute('SELECT count(*) FROM inspection_exchanges').fetchone()[0]
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'agent_exchanges' not in tables and 'agent_history' not in tables:
        require(count == 0, 'missing exchange storage; restore intact storage')
        return
    require({'agent_exchanges', 'agent_history'} <= tables, 'missing agent history')
    agent_store.validate_count(db, count)
    require(db.execute('SELECT count(*) FROM agent_exchanges').fetchone()[0] == count, 'exchange/index count mismatch')


def position_for(prior, directory, run_id, epoch, head):
    if prior is None:
        return 0
    require(prior['path'] == str(directory) and prior['run_id'] == run_id, 'foreign inspection cursor')
    require(prior['epoch'] == epoch, 'expired inspection cursor epoch; restart from retained baseline')
    require(prior['position'] <= head, 'inspection cursor ahead of retained history; restore correct source')
    return prior['position']


def snapshot(db, directory, prior, limit):
    db.execute('BEGIN')
    epoch, head, graph_cursor, current = metadata(db)
    position = position_for(prior, directory, current['run_id'], epoch, head)
    events = [dict(sequence=seq, source=source, reference=ref, summary=json.loads(body))
              for seq, source, ref, body in db.execute(
                  'SELECT sequence,source,reference,summary FROM inspection_events WHERE sequence>? '
                  'ORDER BY sequence LIMIT ?', (position, limit))]
    end = events[-1]['sequence'] if events else position
    exchanges = [json.loads(r[0]) for r in db.execute('SELECT body FROM inspection_exchanges ORDER BY rowid')]
    current['attempts'] = [json.loads(r[0]) for r in db.execute('SELECT body FROM inspection_attempts ORDER BY id')]
    current.update(graph_cursor=graph_cursor, next_action=NEXT[current['status']],
                   exchanges=exchanges, conversation_next=conversation_next(exchanges),
                   publications=policy_summaries(db), latest_graph_change=latest_graph_change(db),
                   policy_accounting='not interpreted by shared provider; consult published policy records/owner',
                   validation='transactional projection/count checks only; inspect/output retain full logical audit')
    return dict(path=str(directory), current=current, events=events, observed_head=head, has_more=end < head,
                evidence_access=evidence_access(directory),
                cursor=dict(path=str(directory), run_id=current['run_id'], epoch=epoch, position=end))


def conversation_next(exchanges):
    if not exchanges:
        return 'no conversation recorded; this is not permission to dispatch'
    latest = exchanges[-1]
    if latest['state'] in ('prepared', 'pending'):
        return 'collect exact retained key; unknown submission/effects block new keys'
    completed = [exchange for exchange in exchanges if exchange['state'] == 'returned']
    if completed and completed[-1]['application'] == 'question_to_caller':
        return 'named caller must answer retained question; no automatic authority expansion'
    return 'new request needs caller authority; prior return is not consumer completion'


def index(directory):
    with exclusive(directory, 'agent-collector.lock'):
        return index_writer(directory)


def index_writer(directory):
    with exclusive(directory):
        return index_connected(directory)


def index_connected(directory):
    with closing(connect(directory)) as db:
        return index_snapshot(db)


def index_snapshot(db):
    require(not store.enabled(db), 'inspection already indexed; never reset cursor history')
    db.execute('BEGIN IMMEDIATE')
    state = load(db)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    exchanges = agent_store.all_exchanges(db) if 'agent_exchanges' in tables or 'agent_history' in tables else []
    store.create(db)
    store.graph(db, state, 'baseline', {})
    for row in db.execute('SELECT body FROM attempts'):
        store.attempt(db, json.loads(row[0]))
    for exchange in exchanges:
        store.exchange(db, exchange)
    db.commit()
    return dict(outcome='indexed', historical_exchange_revisions='unavailable before baseline',
                graph_history='retained in inspect/output; baseline is not reconstructed transitions')


def record(directory, sequence):
    with closing(connect(directory)) as db:
        return read_record(db, sequence)


def read_record(db, sequence):
    db.execute('BEGIN')
    metadata(db)
    row = db.execute('SELECT source,reference,summary,detail FROM inspection_events WHERE sequence=?', (sequence,)).fetchone()
    require(row is not None, 'unknown inspection sequence')
    source, ref, summary, detail = row
    if source == 'graph':
        detail = db.execute('SELECT body FROM events WHERE cursor=?', (int(ref),)).fetchone()[0]
    return dict(sequence=sequence, source=source, reference=ref, summary=json.loads(summary), detail=json.loads(detail))


def node(directory, identity):
    with closing(connect(directory)) as db:
        return read_node(db, identity)


def read_node(db, identity):
    db.execute('BEGIN')
    state = load(db)  # Deep evidence retains existing full audit, including raw output checks.
    require(identity in state['nodes'], 'unknown node incarnation')
    attempts = [json.loads(r[0]) for r in db.execute('SELECT body FROM attempts')]
    attempts = [a for a in attempts if a['request']['node_id'] == identity]
    events = node_events(db, identity)
    return dict(node_id=identity, node=state['nodes'][identity], current_membership=identity in state['node_ids'],
                attempts=attempts, changes=events, policy=state['policy'],
                policy_records=publication_records(db),
                policy_meaning='declared engine value, not consumer qualification; original bases retained per attempt')


def node_events(db, identity):
    if not store.enabled(db):
        return dict(availability='unindexed; consult full inspect edit history')
    rows = [(seq, json.loads(body)) for seq, body in db.execute(
        "SELECT sequence,summary FROM inspection_events WHERE source='graph'")]
    return [dict(sequence=seq, **value) for seq, value in rows
            if identity in value['added_nodes'] or identity in value['removed_nodes']]


def policy_summaries(db):
    rows = db.execute("SELECT sequence,summary FROM inspection_events WHERE sequence IN "
                      "(SELECT max(sequence) FROM inspection_events WHERE source LIKE 'policy:%' GROUP BY source)")
    return [dict(sequence=row[0], **json.loads(row[1])) for row in rows]


def latest_graph_change(db):
    row = db.execute("SELECT sequence,summary FROM inspection_events WHERE source='graph' ORDER BY sequence DESC LIMIT 1").fetchone()
    return dict(sequence=row[0], **json.loads(row[1]))


def publication_records(db):
    if not store.enabled(db):
        return dict(availability='unindexed; consumer policy history not inferred')
    rows = db.execute("SELECT sequence,summary FROM inspection_events WHERE source LIKE 'policy:%' ORDER BY sequence")
    return [dict(sequence=row[0], **json.loads(row[1])) for row in rows]


def evidence_access(directory):
    inspect = [sys.executable, str(Path(__file__).with_name('inspection_cli.py'))]
    graph = [sys.executable, str(Path(__file__).with_name('cli.py'))]
    agent = [sys.executable, str(Path(__file__).with_name('agent_cli.py'))]
    return dict(record_argv=inspect + ['record', str(directory)], node_argv=inspect + ['node', str(directory)],
                evidence_argv=inspect + ['evidence', str(directory)],
                audit_argv=graph + ['inspect', str(directory)], output_argv=graph + ['output', str(directory)],
                exchange_argv=agent + ['show', str(directory)], owner_argv=agent + ['owner', str(directory)])
