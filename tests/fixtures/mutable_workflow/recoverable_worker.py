"""Fake effect owner: SQLite effect+result transaction, keyed by run/attempt.

This fixture guarantees exact-request concurrent deduplication only for its own
local SQL insertion. It makes no guarantee for an arbitrary external effect.
"""
import json
from pathlib import Path
import os
import signal
import socket
import sqlite3
import sys

value = json.load(sys.stdin)
if value.get('operation') == 'recovery_query':
    request = value['request']
    print(json.dumps(dict(protocol='deduplicated-attempt-v1', run_id=request['run_id'],
          attempt_id=request['attempt_id'], disposition='unknown' if request['step']['input'] == 'unknown'
          else 'retry_safe', detail='fixture owns atomic keyed effect and result; concurrent replay serialized')))
    sys.exit(0)

request = value
with Path('deliveries.jsonl').open('a') as stream:
    stream.write(json.dumps(request) + '\n')
with sqlite3.connect('effects.sqlite3') as db:
    db.execute('CREATE TABLE IF NOT EXISTS effects (run TEXT, attempt INTEGER, request TEXT, result TEXT, PRIMARY KEY(run,attempt))')
    db.execute('BEGIN IMMEDIATE')
    row = db.execute('SELECT request,result FROM effects WHERE run=? AND attempt=?',
                     (request['run_id'], request['attempt_id'])).fetchone()
    encoded = json.dumps(request, sort_keys=True)
    fresh = row is None
    if fresh:
        result = json.dumps(dict(outcome='success', detail='one atomic local fake effect'))
        db.execute('INSERT INTO effects VALUES (?,?,?,?)', (request['run_id'], request['attempt_id'], encoded, result))
    else:
        assert row[0] == encoded, 'same key cannot change request'
        result = row[1]
if fresh and isinstance(request['step']['input'], dict):
    with socket.create_connection(('127.0.0.1', request['step']['input']['port']), timeout=15) as connection:
        connection.sendall(b'effect-written\n')
        assert connection.recv(1) == b'R'
if fresh and request['step']['input'] == 'kill-after-effect':
    os.kill(os.getppid(), signal.SIGKILL)
    sys.exit(0)
print(result)
