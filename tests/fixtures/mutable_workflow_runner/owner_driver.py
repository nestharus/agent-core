"""Fake-only barriers at actual ownership/capture/collection seams."""
import json
import os
from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/mutable-workflow'))
import agent_adapter
import collection_owner
import capture_receipt
import runner_transport

boundary, directory, source, address = sys.argv[1:]
address = '\0' + address
directory = Path(directory)
request = json.loads(Path(source).read_text())
connection = None
fired = False


def stop(name):
    global connection, fired
    if boundary != name or fired:
        return
    fired = True
    connection = socket.socket(socket.AF_UNIX)
    connection.connect(address)
    connection.sendall(json.dumps(dict(pid=os.getpid())).encode() + b'\n')
    assert connection.recv(1) == b'!'
    # Kept until owner exit: EOF witnesses end of this actual owner, not receipt.


original_spawn = runner_transport.spawn
original_publish = capture_receipt.publish
original_trace = agent_adapter.read_trace
original_prepare = collection_owner.prepare
original_owner_publish = collection_owner.publish


def spawn(*args):
    stop('before-capture')
    return original_spawn(*args)


def publish(log, code):
    if log.name == 'runner.log':
        stop('after-eof-before-receipt')
    original_publish(log, code)
    if log.name == 'runner.log':
        stop('after-receipt')


def trace(*args):
    stop('before-collection')
    result = original_trace(*args)
    stop('after-trace')
    return result


def prepare(*args):
    result = original_prepare(*args)
    stop('before-owner-fork')
    return result


def owner_publish(path, value):
    original_owner_publish(path, value)
    if path.name == 'result.json':
        stop('after-collection')


runner_transport.spawn = spawn
capture_receipt.publish = publish
agent_adapter.read_trace = trace
collection_owner.prepare = prepare
collection_owner.publish = owner_publish
print(json.dumps(agent_adapter.execute(directory, 'ask', request=request)))
