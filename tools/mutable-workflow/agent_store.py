"""Durable on-demand agent exchanges alongside, not inside, graph attempts.

Declared roles: orchestration, accessor, mapper, validator.
"""
import json
from pathlib import Path
import sys
from contextlib import closing

from runtime import connect, inspection, require


def setup(db):
    db.execute('CREATE TABLE IF NOT EXISTS agent_exchanges '
               '(sequence INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, body TEXT NOT NULL)')
    db.commit()


def all_exchanges(db):
    return [json.loads(row[0]) for row in db.execute(
        'SELECT body FROM agent_exchanges ORDER BY sequence')]


def find(db, key):
    row = db.execute('SELECT body FROM agent_exchanges WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else None


def put(db, exchange, commit=True):
    db.execute('INSERT INTO agent_exchanges(key,body) VALUES (?,?) '
               'ON CONFLICT(key) DO UPDATE SET body=excluded.body',
               (exchange['key'], json.dumps(exchange, ensure_ascii=True)))
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
