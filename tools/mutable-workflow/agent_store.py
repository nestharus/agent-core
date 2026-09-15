"""Durable on-demand agent exchanges alongside, not inside, graph attempts.

Declared roles: orchestration, accessor, mapper, validator.
"""
import json
from pathlib import Path
import sys
from contextlib import closing

from runtime import connect, end_read, inspection, load, require


def setup(db):
    load(db)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'agent_exchanges' in tables or 'agent_history' in tables:
        require({'agent_exchanges', 'agent_history'} <= tables,
                'missing or unsupported agent history; use original runtime for pre-recovery records, never reset')
        all_exchanges(db)
        return
    with db:
        db.execute('CREATE TABLE agent_exchanges '
                   '(sequence INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, body TEXT NOT NULL)')
        db.execute('CREATE TABLE agent_history (id INTEGER PRIMARY KEY CHECK(id=1), '
                   'version INTEGER NOT NULL, count INTEGER NOT NULL)')
        db.execute('INSERT INTO agent_history VALUES (1,1,0)')


def all_exchanges(db):
    owned = not db.in_transaction
    if owned:
        db.execute('BEGIN')
    try:
        return exchange_snapshot(db)
    finally:
        end_read(db, owned)


def exchange_snapshot(db):
    state = load(db)
    rows = list(db.execute('SELECT sequence,key,body FROM agent_exchanges ORDER BY sequence'))
    validate_count(db, len(rows))
    require([row[0] for row in rows] == list(range(1, len(rows) + 1)),
            'missing agent exchange history; restore intact storage')
    return [validate_exchange(key, json.loads(body), state) for _, key, body in rows]


def validate_exchange(key, exchange, state):
    require(exchange.get('capture_protocol') == 'local-receipt-v1', 'unsupported exchange capture protocol')
    require(exchange['key'] == key == exchange['request']['key'], 'exchange key mismatch')
    require(exchange['context']['current']['run_id'] == state['run_id']
            and 0 <= exchange['context']['cursor'] <= state['cursor'], 'exchange context mismatch')
    require(exchange['state'] in ('prepared', 'pending', 'returned', 'not_submitted'), 'exchange state')
    require(exchange['state'] != 'returned' or exchange['response'] is not None, 'missing returned response')
    return exchange


def find(db, key):
    matches = [item for item in all_exchanges(db) if item['key'] == key]
    return matches[0] if matches else None


def put(db, exchange, commit=True):
    validate_count(db, db.execute('SELECT count(*) FROM agent_exchanges').fetchone()[0])
    db.execute('INSERT INTO agent_exchanges(key,body) VALUES (?,?) '
               'ON CONFLICT(key) DO UPDATE SET body=excluded.body',
               (exchange['key'], json.dumps(exchange, ensure_ascii=True)))
    db.execute('UPDATE agent_history SET count=(SELECT count(*) FROM agent_exchanges) WHERE id=1')
    if commit:
        db.commit()


def view(directory, since):
    with closing(connect(directory)) as db:
        return inspection(db, since)


def context(directory, history):
    prior = continuation_basis(history)
    since = prior['context']['cursor'] if prior else 0
    current = view(directory, since)
    current['prior_exchanges'] = [summary(item) for item in history]
    cli = [sys.executable, str(Path(__file__).with_name('cli.py'))]
    current['evidence_access'] = dict(run_dir=str(directory),
        inspect_argv=cli + ['inspect', str(directory)],
        output_argv=cli + ['output', str(directory)])
    return current


def admit_request(request, history):
    require(isinstance(request, dict) and set(request) == {'key', 'question', 'answer', 'config'},
            'request requires key, question, answer, config')
    require(isinstance(request['key'], str) and request['key'].strip(), 'nonempty key required')
    require(isinstance(request['question'], str) and request['question'].strip(), 'question required')
    require(request['answer'] is None or isinstance(request['answer'], str), 'answer must be text or null')
    if not history:
        return
    require(history[0]['request']['config'] == request['config'], 'authority/configuration cannot change in a conversation')
    require(history[-1]['state'] in ('returned', 'not_submitted'),
            'previous exchange unresolved; collect it, never blindly resubmit')
    prior = continuation_basis(history)
    previous = prior.get('response', {}) if prior else {}
    require(previous.get('kind') != 'question' or bool(request['answer']),
            'authority question belongs to caller; an answer is required')


def summary(exchange):
    value = {key: exchange.get(key) for key in
            ('key', 'id', 'state', 'invocation', 'target', 'session', 'continuity',
             'response', 'application', 'error', 'log', 'returned_artifacts', 'observations')}
    value['question'] = exchange['request']['question']
    value['answer'] = exchange['request']['answer']
    return value


def continuation_basis(history):
    completed = [item for item in history if item['state'] == 'returned']
    return completed[-1] if completed else None


def validate_count(db, count):
    row = db.execute('SELECT version,count FROM agent_history WHERE id=1').fetchone()
    require(row == (1, count), 'missing, unsupported or inconsistent agent history count; restore intact storage')
