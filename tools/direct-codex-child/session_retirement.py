"""Prospective, cooperative owner-only retirement. No inventory or scheduling.

Trust boundary: the original owner controls this attempt directory and all actors
named in its immutable owner receipt. Actor strings are not authentication against
hostile writers. All participating resume/fork/hold writers MUST use edit() and
its same lock; absent exclusive cooperation, custody must remain unqualified.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import uuid

HOLDS = ('source', 'consumer', 'control', 'outbox', 'publication', 'resource',
         'recovery', 'effect', 'privacy', 'custody')
QUALIFIED_BINARY_SHA256 = 'cdcb45aaa01d0f14e298985e09465aebccd47f64ecd298aea44814af7b62bbda'
DAY = 86400
LIMIT = 1024 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def require(ok, why):
    if not ok:
        raise ValueError(why)


def uid(value):
    require(isinstance(value, str) and str(uuid.UUID(value)) == value, 'noncanonical UUID')
    return value


def load(path):
    with open(path, 'rb') as f:
        data = f.read(LIMIT + 1)
    require(len(data) <= LIMIT, 'oversized receipt')
    return json.loads(data)


def durable(path, value):
    with open(path, 'x', encoding='utf8') as f:
        json.dump(value, f, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def bootstrap(attempt, receipt, binding, lifetime):
    """Only a future launcher calls this before starting its sole invocation."""
    require(lifetime in ('oneoff', 'reusable'), 'lifetime')
    require(set(receipt) == {'owner', 'custodian', 'collector', 'caller_session_id',
                            'account_binding', 'context_ref', 'required_closures', 'hold_owners'}, 'owner receipt fields')
    for k in ('owner', 'custodian', 'collector', 'account_binding'):
        require(isinstance(receipt[k], str) and bool(receipt[k]), k)
    uid(receipt['caller_session_id'])
    require(receipt['required_closures'].get('processing') == receipt['owner'], 'processing owner')
    require(receipt['required_closures'].get('context') == receipt['owner'], 'actual context close required')
    require(set(receipt['hold_owners']) == set(HOLDS) and
            all(isinstance(v, str) and v for v in receipt['hold_owners'].values()), 'hold owners')
    require(all(isinstance(k, str) and isinstance(v, str) and k and v
                for k, v in receipt['required_closures'].items()), 'closure owners')
    require(lifetime != 'reusable' or bool(receipt['context_ref']), 'reusable context ref')
    require(binding['account_binding'] == receipt['account_binding'], 'account binding')
    require(Path(binding['binary']).is_absolute() and Path(binding['codex_home']).is_absolute(), 'absolute binding')
    manifest = dict(schema=1, invocation_id=str(uuid.uuid4()), lifetime=lifetime,
                    receipt=receipt, binding=binding, started_at=time.time())
    durable(Path(attempt)/'session-retirement.json', manifest)
    return manifest


@contextlib.contextmanager
def locked(attempt):
    with open(Path(attempt)/'session-retirement.lock', 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def read(attempt):
    m = load(Path(attempt)/'session-retirement.json')
    state = dict(generation=0, metadata=None, end=None, collection=None, closures={},
                 holds={k: ['unqualified'] for k in HOLDS}, custody=None, operation=None)
    path = Path(attempt)/'session-retirement.jsonl'
    prev = digest(m)
    if path.exists():
        with open(path, 'rb') as f:
            while True:
                line = f.readline(LIMIT + 1)
                if not line:
                    break
                require(len(line) <= LIMIT and line.endswith(b'\n'), 'torn journal; hold, never repair/replay')
                row = json.loads(line)
                require(row['previous'] == prev and row['hash'] == digest({k:v for k,v in row.items() if k != 'hash'}), 'journal chain')
                state = row['state']
                prev = row['hash']
    return m, state, prev


def append(attempt, state, previous, event, now):
    row = dict(previous=previous, event=event, at=now, state=state)
    row['hash'] = digest(row)
    path = Path(attempt)/'session-retirement.jsonl'
    with open(path, 'a', encoding='utf8') as f:
        f.write(json.dumps(row, sort_keys=True)+'\n')
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(Path(attempt), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return row['hash']


def edit(attempt, actor, generation, kind, value, now=None):
    """Original actors submit actual receipts; END never implies processing.

    Cooperative callers must reopen BEFORE resuming/forking/adding obligations.
    A frozen operation blocks every mutation, including resume and hold release.
    """
    now = time.time() if now is None else now
    with locked(attempt):
        m, s, prev = read(attempt)
        r = m['receipt']
        require(generation == s['generation'], 'stale generation')
        if kind == 'release-unsent':
            require(actor == r['owner'] and s['operation'] and s['operation']['state'] == 'unsent' and value, 'only proven unsent')
            s['operation'] = None
            append(attempt, s, prev, dict(kind=kind, actor=actor, receipt=value), now)
            return
        require(s['operation'] is None, 'retirement fence; reconcile with actual effect owner')
        if kind == 'metadata':
            require(actor == r['owner'] and s['metadata'] is None, 'metadata immutable')
            s['metadata'] = value
        elif kind == 'end':
            require(actor == r['owner'] and s['end'] is None and type(value) is int, 'END')
            s['end'] = value
        elif kind == 'collect':
            require(actor == r['collector'] and s['end'] is not None and s['collection'] is None, 'original collector')
            require(set(value) == {'handle', 'receipt'} and all(value.values()), 'collection receipt')
            s['collection'] = value
        elif kind == 'close':
            name = value['name']
            require(r['required_closures'].get(name) == actor, 'closure owner')
            require(name not in s['closures'], 'immutable completion; reopen generation')
            require(type(value['at']) in (int, float) and math.isfinite(value['at']) and 0 <= value['at'] <= now and value['receipt'], 'actual completion')
            s['closures'][name] = value
        elif kind == 'hold':
            name = value['name']
            require(r['hold_owners'].get(name) == actor, 'hold owner')
            require(type(value['refs']) is list and all(isinstance(x, str) and x for x in value['refs']) and value['receipt'], 'hold references')
            s['holds'][name] = value['refs']
        elif kind == 'custody':
            require(actor == r['custodian'], 'cascade custodian')
            require(value.get('receipt'), 'custody evidence')
            s['custody'] = value
        elif kind == 'reopen':
            require(actor == r['owner'] and value, 'owner reopen receipt')
            s.update(generation=s['generation']+1, closures={}, custody=None,
                     holds={k:['reopened-unqualified'] for k in HOLDS})
        else:
            raise ValueError('unsupported lifecycle event')
        append(attempt, s, prev, dict(kind=kind, actor=actor, receipt=value), now)


def eligible(m, s, binding, current_session, now):
    r = m['receipt']
    uid(current_session)
    require(binding == m['binding'], 'original profile/route/binary/account binding required')
    require(not binding.get('ephemeral'), 'ephemeral teardown is separate')
    md = s['metadata']
    require(md and md.get('qualified') is True and md.get('count') == 1, 'missing/duplicate typed root')
    root = uid(md['thread_id'])
    require(root != current_session and r['caller_session_id'] != current_session, 'current caller')
    require(s['end'] is not None and s['collection'], 'original END and collection required')
    require(set(s['closures']) == set(r['required_closures']), 'real processing/consumer/context closure')
    require(set(s['holds']) == set(HOLDS) and all(v == [] for v in s['holds'].values()), 'outstanding hold')
    c = s['custody']
    require(c and c.get('exclusive') is True and c.get('coverage') == 'complete' and
            c.get('generation') == s['generation'] and c.get('invocation_id') == m['invocation_id'] and
            c.get('binding_digest') == digest(binding) and c.get('active_callers') == [] and c.get('unknown_descendants') == [], 'exclusive cascade fence')
    members = c['members']
    require(root in members and current_session not in members and r['caller_session_id'] not in members, 'cascade reaches caller')
    times = [v['at'] for v in s['closures'].values()]
    for thread, member in members.items():
        uid(thread)
        require(member.get('custodian') == r['custodian'] and member.get('active') is False and
                type(member.get('end')) is int and member.get('collection_receipt') and member.get('closure_receipt'), 'descendant custody/END')
        for k in ('processed_at', 'context_closed_at'):
            t = member.get(k)
            require(type(t) in (int, float) and math.isfinite(t) and 0 <= t <= now, 'descendant real closure')
            times.append(t)
    edges = c.get('edges')
    require(isinstance(edges, list), 'actual descendant edges')
    reached = {root}
    for _ in members:
        for edge in edges:
            require(set(edge) == {'parent', 'child', 'receipt'} and edge['receipt'] and edge['parent'] in members and edge['child'] in members, 'edge coverage')
            if edge['parent'] in reached:
                reached.add(edge['child'])
    require(reached == set(members) and len(edges) == len(members)-1 and
            len({e['child'] for e in edges}) == len(edges) and all(e['child'] != root for e in edges), 'exclusive complete tree')
    due = max(times) + DAY
    require(now >= due, 'retention')
    return root, due


class Stdio:
    """Finite newly controlled server, bounded body-free RPC, no client attach."""
    def __init__(self, binding):
        with open(binding['binary'], 'rb') as f:
            actual = hashlib.file_digest(f, 'sha256').hexdigest()
        require(actual == binding['binary_sha256'] == QUALIFIED_BINARY_SHA256, 'binary changed/unqualified protocol')
        env = os.environ.copy()
        env['CODEX_HOME'] = binding['codex_home']
        self.p = subprocess.Popen([binding['binary'], 'app-server', '--listen', 'stdio://'],
                                  env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, start_new_session=True)
        self.buffer = b''
        self.seen = 0
        self.deadline = time.monotonic()+30

    def send(self, value):
        self.p.stdin.write(json.dumps(value).encode()+b'\n')
        self.p.stdin.flush()

    def call(self, method, params, request_id):
        self.send(dict(id=request_id, method=method, params=params))
        with selectors.DefaultSelector() as sel:
            sel.register(self.p.stdout, selectors.EVENT_READ)
            while True:
                while b'\n' in self.buffer:
                    line, self.buffer = self.buffer.split(b'\n', 1)
                    response = json.loads(line)
                    if response.get('id') == request_id:
                        require('error' not in response and isinstance(response.get('result'), dict), 'RPC error/unknown result')
                        return response['result']
                left = self.deadline-time.monotonic()
                require(left > 0 and sel.select(left), 'RPC timeout')
                chunk = os.read(self.p.stdout.fileno(), 65536)
                self.seen += len(chunk)
                require(chunk and self.seen <= LIMIT, 'RPC EOF/cap')
                self.buffer += chunk

    def close(self):
        self.p.stdin.close()
        try:
            return self.p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            try:
                return self.p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.p.kill()
                return self.p.wait(timeout=2)


def retire(attempt, actor, binding, current_session, now=None, factory=Stdio, checkpoint=lambda _: None):
    """One bounded original-owner visit; no pool lookup, no possible-send replay."""
    now = time.time() if now is None else now
    with locked(attempt):
        m, s, prev = read(attempt)
        require(actor == m['receipt']['owner'], 'original owner')
        op = s['operation']
        if op and op['state'] != 'unsent':
            return op  # ACK/possible-send/unknown are terminal for dispatch
        root, due = eligible(m, s, binding, current_session, now)
        checkpoint('before_intent')
        op = dict(id=str(uuid.uuid4()), state='unsent', generation=s['generation'], due_at=due,
                  basis=digest(s), binding_digest=digest(binding), logical_outcome=None)
        s['operation'] = op
        prev = append(attempt, s, prev, 'intent-and-cooperative-fence', now)
        checkpoint('before_possible_send')
        server = None
        try:
            server = factory(binding)
            result = server.call('initialize', {'clientInfo': {'name':'owner-session-retirement', 'version':'1'}}, 'initialize')
            require(result.get('codexHome') == binding['codex_home'], 'initialize profile mismatch')
            server.send({'method':'initialized'})
            # Before any delete bytes can be sent. A crash here remains unknown.
            op['state'] = 'possible-send'
            prev = append(attempt, s, prev, 'possible-send', now)
            checkpoint('after_possible_send')
            result = server.call('thread/delete', {'threadId':root}, op['id'])
            require(result == {}, 'unexpected delete ACK schema')
            op.update(state='ack', logical_outcome='supported logical deletion acknowledged')
            prev = append(attempt, s, prev, 'terminal-ack', now)
            checkpoint('after_ack')
        except Exception as error:
            op['failure'] = type(error).__name__
            prev = append(attempt, s, prev, 'unsent-or-unknown; no blind replay', now)
        finally:
            if server is not None:
                try:
                    op['adapter_end'] = server.close()
                except Exception as error:
                    op['adapter_end'] = None
                    op['end_failure'] = type(error).__name__
                append(attempt, s, prev, 'adapter-END', now)
        return op


def intercept(attempt):
    """Future exec --json stdout only, upstream of opaque capture caps.

    Forward every byte unchanged. Inspect only bounded prospective typed events;
    never save event bodies. Oversized/malformed JSON permanently disqualifies.
    """
    m, _, _ = read(attempt)
    count, root, bad = 0, None, False
    pending = b''
    oversized = False
    while True:
        chunk = os.read(0, 65536)
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
        for part in chunk.splitlines(keepends=True):
            if not oversized:
                pending += part
                if len(pending) > 65536:
                    oversized, bad, pending = True, True, b''
            if part.endswith(b'\n'):
                if not oversized:
                    try:
                        event = json.loads(pending)
                        if event.get('type') == 'thread.started':
                            count += 1
                            root = uid(event['thread_id'])
                    except (ValueError, KeyError, AttributeError, TypeError):
                        bad = True
                pending, oversized = b'', False
    if pending or oversized:
        bad = True
    edit(attempt, m['receipt']['owner'], 0, 'metadata',
         dict(qualified=not bad and count == 1, count=count, thread_id=root))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['bootstrap', 'intercept', 'end', 'record', 'retire'])
    p.add_argument('--attempt', required=True)
    p.add_argument('--receipt')
    p.add_argument('--binding')
    p.add_argument('--lifetime')
    p.add_argument('--code', type=int)
    p.add_argument('--actor')
    p.add_argument('--generation', type=int)
    p.add_argument('--event', help='body-free actual-owner event JSON: kind and value')
    a = p.parse_args()
    if a.command == 'bootstrap':
        bootstrap(a.attempt, load(a.receipt), json.loads(a.binding), a.lifetime)
    elif a.command == 'intercept':
        intercept(a.attempt)
    elif a.command == 'record':
        event = json.loads(a.event)
        edit(a.attempt, a.actor, a.generation, event['kind'], event['value'])
    elif a.command == 'retire':
        require(bool(os.environ.get('CODEX_SESSION_ID')), 'current caller identity required')
        print(json.dumps(retire(a.attempt, a.actor, json.loads(a.binding), os.environ['CODEX_SESSION_ID']), sort_keys=True))
    else:
        m, s, _ = read(a.attempt)
        edit(a.attempt, m['receipt']['owner'], s['generation'], 'end', a.code)


if __name__ == '__main__':
    main()
