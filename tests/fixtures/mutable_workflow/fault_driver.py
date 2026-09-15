"""Test-only process interruption at actual runtime/adapter call seams.

Never starts real agents. Test configuration supplies the fake executable.
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/mutable-workflow'))
import runtime
import surgery
import agent_adapter

boundary, command, directory, source = sys.argv[1:]
directory = Path(directory)
payload = json.loads(Path(source).read_text())
original_save = runtime.save
original_invoke = runtime.invoke
original_store_attempt = runtime.store_attempt
original_put = agent_adapter.store.put


def crash(name):
    if boundary == name:
        os._exit(90)


def save(db, state, kind, detail, attempt=None, updated=()):
    crash('before-' + kind)
    original_save(db, state, kind, detail, attempt, updated)
    crash('after-' + kind)


def invoke(*args):
    crash('before-dispatch')
    result = original_invoke(*args)
    crash('after-result-receipt')
    return result


def put(db, exchange, commit=True):
    if exchange['returncode'] is not None and exchange['state'] == 'pending':
        crash('before-capture-record')
    original_put(db, exchange, commit)
    if exchange['state'] == 'prepared':
        crash('after-prepared')
    if exchange['state'] == 'pending' and exchange['returncode'] is None:
        crash('before-agent-dispatch')


def store_attempt(db, attempt):
    if attempt is not None and attempt['output'] is not None:
        crash('during-attempt_returned')
    original_store_attempt(db, attempt)


runtime.store_attempt = store_attempt
runtime.save = surgery.save = save
runtime.invoke = invoke
agent_adapter.store.put = put
if command == 'ask':
    agent_adapter.execute(directory, 'ask', request=payload)
elif command == 'amend':
    with runtime.connect(directory) as db, runtime.exclusive(directory):
        surgery.amend(db, payload)
else:
    runtime.initialize(directory, payload)
    with runtime.connect(directory) as db:
        runtime.drive(db, directory, None)
