#!/usr/bin/env python3
"""Bounded software QA execution peer. Semantic acceptance belongs to its recipient.

Cooperative same-user contract, not a sandbox for hostile tests. Only the fixed
runtime/provider unittest procedure is admitted. No model, shell or Board entry.
"""
import argparse
import builtins
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time
import unittest

# Install before runtime/provider imports, also in every fixed child entry.
_import = builtins.__import__
def no_sql(name, *args, **kwargs):
    if name.split('.')[0] in {'sqlite3', '_sqlite3'}:
        raise RuntimeError('SQLite unavailable in software QA')
    return _import(name, *args, **kwargs)
builtins.__import__ = no_sql

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).absolute().parent))

from runtime import Runtime, ALLOWED_PROFILES, _fast, ident, require
from provider import Redactor
from storage import Held, check_capacity, digest, encode, read_regular

PREFIX = 'tools/coordinator-file-runtime/'
PUBLIC = tuple(PREFIX + p for p in ('coordinator.py', 'runtime.py', 'storage.py',
          'provider.py', 'fixture_worker.py', 'test_runtime.py', 'test_provider.py',
          'software_qa.py')) + ('tools/direct-child/execution_pool.py', 'tools/direct-child/fast_tier.py')
MODULES = ('test_runtime', 'test_provider')
MAX_JSON = 131072
MAX_SOURCE = 1048576


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def directory(path):
    path = Path(path)
    require(path.is_absolute(), 'absolute directory required')
    for p in reversed([path, *path.parents]):
        require(stat.S_ISDIR(os.lstat(p).st_mode), 'linked/non-directory ancestry refused')
    return path


def put(path, value, mode=0o400):
    """Exclusive durable publication. A partial/existing leaf is never replaced."""
    raw = value if isinstance(value, bytes) else encode(value)
    require(len(raw) <= MAX_SOURCE, 'finite publication exceeded')
    directory(path.parent)
    check_capacity(path.parent, len(raw), 1)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        fd = None
        sync = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW)
        try: os.fsync(sync)
        finally: os.close(sync)
    finally:
        if fd is not None:
            # fdopen owns the descriptor even when the write failed.
            pass


def get(path):
    directory(Path(path).parent)
    return json.loads(read_regular(path, MAX_JSON))


def validate(g):
    fields = {'schema', 'job', 'attempt', 'event', 'event_source_hash', 'package', 'scope',
              'source', 'policy', 'authority', 'config_actor', 'controller', 'workers',
              'acceptor', 'commit', 'inputs', 'program_sha256', 'retained_root', 'repository',
              'inventory', 'partitions', 'execute_attempt', 'consolidate_attempt', 'resources',
              'basis', 'limits', 'result_packet', 'receive_packet', 'procedure'}
    require(isinstance(g, dict) and set(g) == fields and g['schema'] == 1, 'exact software QA grant schema required')
    for key in ('job', 'attempt', 'event', 'package', 'config_actor', 'controller', 'acceptor',
                'execute_attempt', 'consolidate_attempt', 'result_packet', 'receive_packet'):
        ident(g[key])
    require(g['execute_attempt'] != g['consolidate_attempt'], 'separate consolidation attempt required')
    require(g['procedure'] == 'runtime-provider-unittest-v1', 'only fixed software test procedure supported')
    for key in ('scope', 'source', 'policy', 'authority'):
        require(isinstance(g[key], str) and 0 < len(encode(g[key])) <= 512, 'bounded current authority/source/scope required')
    require(isinstance(g['workers'], list) and len(g['workers']) == 5, 'five worker bindings required')
    for worker in g['workers']: ident(worker)
    require(g['acceptor'] not in [g['controller'], g['config_actor'], *g['workers']], 'acceptor must differ from workers/controller/configuration actor')
    require(re.fullmatch('[0-9a-f]{40}', g['commit']) is not None, 'immutable full commit required')
    require(set(g['inputs']) == set(PUBLIC), 'complete exact public input whitelist required')
    for h in [*g['inputs'].values(), g['program_sha256'], g['event_source_hash']]:
        require(isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h), 'full frozen SHA256 required')
    require(g['program_sha256'] == g['inputs'][PREFIX + 'software_qa.py'], 'actual program must be in frozen candidate')
    for key in ('repository', 'retained_root'):
        require(isinstance(g[key], str) and len(g[key]) <= 512 and Path(g[key]).is_absolute(), 'absolute bounded job paths required')
    inv, parts = g['inventory'], g['partitions']
    require(isinstance(inv, list) and 5 <= len(inv) <= 128 and len(set(inv)) == len(inv), 'unique complete selected case inventory required')
    for case in inv:
        require(isinstance(case, str) and len(case) <= 200 and re.fullmatch(r'test_(runtime|provider)\.[A-Za-z][A-Za-z0-9_]*\.test_[A-Za-z0-9_]+', case), 'fixed runtime/provider testcase IDs required')
    require(isinstance(parts, list) and len(parts) == 5 and all(isinstance(p, list) and p for p in parts), 'five nonempty partitions required')
    flat = sum(parts, [])
    require(len(flat) == len(inv) and len(set(flat)) == len(flat) and set(flat) == set(inv), 'partitions must cover inventory exactly without drops/duplicates')
    require(isinstance(g['resources'], dict) and 0 < len(g['resources']) <= 16 and set(g['basis']) == set(g['resources']), 'complete current resource basis required')
    for key, mode in g['resources'].items():
        ident(key)
        require(mode in {'read', 'write'} and type(g['basis'][key]) is int and g['basis'][key] >= 0, 'invalid resource basis')
    lim = g['limits']
    require(set(lim) == {'workers', 'seconds', 'capture_bytes', 'output_bytes', 'output_entries'}, 'exact finite limits required')
    require(lim['workers'] == 5 and type(lim['seconds']) is int and 1 <= lim['seconds'] <= 300, 'five workers and positive bounded deadline required')
    require(type(lim['capture_bytes']) is int and 4096 <= lim['capture_bytes'] <= 65536, 'bounded capture required')
    require(type(lim['output_bytes']) is int and 1048576 <= lim['output_bytes'] <= 12582912, 'bounded admitted outputs required')
    require(type(lim['output_entries']) is int and 32 <= lim['output_entries'] <= 4096, 'bounded output entries required')
    require(len(encode(g)) <= 32768, 'grant exceeds receive bound')
    return g


def kill(p):
    try: os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError: pass


def capture(originals, limit, seconds, secrets):
    """Original Popen objects must already be owned; bounded parallel collection.

    No PID lookup/reconstruction. On cancellation collect only these originals.
    Raw output remains in bounded memory, only sanitized bytes leave this method.
    """
    rows = [{'process': p, 'redactor': Redactor(secrets), 'log': bytearray(),
             'seen': 0, 'clean': 0, 'timeout': False, 'overflow': False, 'io_error': False}
            for p in originals]
    deadline = time.monotonic() + seconds
    interrupted = False
    with selectors.DefaultSelector() as selector:
        for row in rows:
            p = row['process']
            p.stdin.close()
            os.set_blocking(p.stdout.fileno(), False)
            selector.register(p.stdout, selectors.EVENT_READ, row)
        try:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    for key in list(selector.get_map().values()):
                        key.data['timeout'] = True
                        kill(key.data['process'])
                        selector.unregister(key.fileobj)
                    break
                for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                    row = key.data
                    try: chunk = os.read(key.fileobj.fileno(), 4096)
                    except OSError:
                        row['io_error'] = True
                        kill(row['process'])
                        chunk = b''
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    row['seen'] += len(chunk)
                    clean = row['redactor'].feed(chunk)
                    row['clean'] += len(clean)
                    row['log'].extend(clean[:max(0, limit - len(row['log']))])
                    if row['seen'] > 4 * limit:
                        row['overflow'] = True
                        kill(row['process'])
                        selector.unregister(key.fileobj)
        except BaseException:
            interrupted = True
            for p in originals: kill(p)
        finally:
            for row in rows:
                p = row.pop('process')
                p.stdout.close()
                clean = row.pop('redactor').feed(b'', final=True)
                row['clean'] += len(clean)
                row['log'].extend(clean[:max(0, limit - len(row['log']))])
                try: row['end'] = p.wait(timeout=max(.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    row['timeout'] = True
                    kill(p)
                    try: row['end'] = p.wait(timeout=5)
                    except subprocess.TimeoutExpired: row['end'] = None
                row['pid'] = p.pid
                row['interrupted'] = interrupted
                row['complete'] = (type(row['end']) is int and not any(row[k] for k in ('timeout', 'overflow', 'io_error', 'interrupted')) and row['clean'] <= limit)
                row['log'] = bytes(row['log'])
    return rows


class Processes:
    def __init__(self):
        self.originals = []
        self.stages = []

    def popen(self, command, cwd, payload, stage, guard=None):
        def create():
            p = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'},
                                 start_new_session=True)
            self.originals.append(p)  # BEFORE stdin/capture/filter/publication, even if any of them fails.
            self.stages.append(stage)
            return p
        p = guard(create) if guard else create()
        try:
            # Requests are at most 32KiB; avoid pipe-capacity blocking before collection.
            # The child reads this finite request first; no stdout is read here.
            if payload is not None:
                p.stdin.write(encode(payload))
                p.stdin.flush()
        except BaseException:
            kill(p)
            raise
        return p

    def git(self, repo, args, maximum=MAX_SOURCE):
        p = self.popen(['git', '--no-pager', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
                        '-C', str(repo), *args], repo, None, 'source-git')
        # Git takes no stdin. Fixed cat-file/ls-tree output is bounded and never diagnostics.
        rows = capture([p], maximum, 10, [])
        require(rows[0]['end'] == 0 and rows[0]['complete'], 'guarded Git acquisition failed; no diagnostic/backing recovery')
        return rows[0]['log']


def export(g, processes):
    """Only exact regular whitelisted tracked blobs from an immutable commit."""
    repo = directory(g['repository'])
    root = Path(g['retained_root'])
    directory(root.parent)
    require(not root.exists() and not root.is_symlink(), 'original retained root already exists; no relaunch/reuse')
    check_capacity(root.parent, g['limits']['output_bytes'] + MAX_SOURCE, g['limits']['output_entries'] + 32)
    root.mkdir(mode=0o700)
    (root / 'inputs').mkdir(mode=0o700)
    (root / 'outputs').mkdir(mode=0o700)
    commit = processes.git(repo, ['rev-parse', '--verify', g['commit'] + '^{commit}'], 256).decode().strip()
    require(commit == g['commit'], 'commit object mismatch')
    files = {}
    total = 0
    for name in PUBLIC:
        line = processes.git(repo, ['ls-tree', g['commit'], '--', name], 1024).decode().strip()
        fields = line.split()
        require(len(fields) == 4 and fields[0] in {'100644', '100755'} and fields[1] == 'blob' and fields[3] == name, 'regular exact tracked public blob required')
        raw = processes.git(repo, ['cat-file', 'blob', g['commit'] + ':' + name])
        total += len(raw)
        require(total <= MAX_SOURCE and sha(raw) == g['inputs'][name], 'frozen input hash/source limit mismatch')
        target = root / 'inputs' / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        put(target, raw)
        files[name] = {'sha256': sha(raw), 'bytes': len(raw), 'git_blob': fields[2], 'git_mode': fields[0]}
    manifest = {'schema': 1, 'grant': digest(g), 'commit': commit, 'source': g['source'],
                'policy': g['policy'], 'authority': g['authority'], 'attempt': g['attempt'],
                'retained_root': str(root), 'files': files}
    put(root / 'manifest.json', manifest)
    put(root / 'grant.json', g)
    # Read-only code and ancestry: separate output area remains writable.
    for p in sorted((root / 'inputs').rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if p.is_dir(): p.chmod(0o500)
    (root / 'inputs').chmod(0o500)
    return manifest


def inputs(g):
    root = directory(Path(g['retained_root']) / 'inputs')
    found = {}
    # This is our fresh controlled export, never a source/private-store census.
    for p in root.rglob('*'):
        s = p.lstat()
        require(stat.S_ISDIR(s.st_mode) or (stat.S_ISREG(s.st_mode) and s.st_nlink == 1), 'changed candidate type/link')
        require(s.st_mode & 0o222 == 0, 'candidate inputs must remain read-only')
        if stat.S_ISREG(s.st_mode):
            name = str(p.relative_to(root))
            require(name in PUBLIC, 'unexpected candidate member')
            found[name] = sha(read_regular(p, MAX_SOURCE))
    require(found == g['inputs'], 'complete candidate input binding changed')
    return found


def usage(g):
    root = directory(Path(g['retained_root']) / 'outputs')
    size = entries = special = 0
    pending = [root]
    while pending:
        parent = pending.pop()
        with os.scandir(parent) as names:
            for name in names:
                info = name.stat(follow_symlinks=False)
                entries += 1
                if stat.S_ISDIR(info.st_mode): pending.append(Path(name.path))
                else:
                    size += info.st_size
                    if not stat.S_ISREG(info.st_mode): special += 1
                # Negative test fixtures may deliberately retain links/special
                # entries. Count only lstat facts; never follow/open targets.
                require(size <= g['limits']['output_bytes'] and entries <= g['limits']['output_entries'], 'admitted output bound exceeded; retain partial')
    return {'bytes': size, 'entries': entries, 'special_entries_not_followed': special, 'physical_io': 'unobserved'}


def binding(g, manifest):
    return {'grant': digest(g), 'candidate': digest(manifest), 'job': g['job'], 'attempt': g['attempt'],
            'package': g['package'], 'source': g['source'], 'policy': g['policy'], 'authority': g['authority'],
            'retained_root': g['retained_root'], 'commit': g['commit']}


def parsed(row):
    lines = [x[len(b'SOFTWARE_QA_RESULT='):] for x in row['log'].splitlines() if x.startswith(b'SOFTWARE_QA_RESULT=')]
    if row['complete'] and len(lines) == 1:
        try: return json.loads(lines[0])
        except ValueError: pass
    return None


def public_row(row):
    return {k: v for k, v in row.items() if k != 'log'} | {'log_sha256': sha(row['log'])}


def stage_outcome(collection, result):
    """A flushed result never overrides the actual original process outcome."""
    if type(collection['end']) is int and collection['end'] != 0:
        return 'failure'
    if type(collection['end']) is not int or not collection['complete'] or result is None:
        return 'unknown'
    return result.get('outcome', 'unknown')


def guard(rt, actor, credential, attempt, collector, g):
    def admitted(create):
        with rt.files.transaction(readonly=True) as s:
            rt.authority(s, actor, credential)
            cfg, acc = s['actors'][g['config_actor']], s['actors'][g['acceptor']]
            require(cfg['role'] == 'Work' and cfg['active'] and cfg['adopted'] and acc['active'] and acc['adopted'], 'current grant authority/recipient unavailable')
            a = rt.attempt(s, actor, attempt, collector)
            require(a['state'] == 'launching' and a['substrate'] == 'owner-encounter', 'current original software attempt required; no replay')
            with rt.pool(s).admission(a['pool']['profile'], ALLOWED_PROFILES, blocking=False, expected_control=s['pool_binding']):
                with _fast.admission(Path(s['pool_routes']).with_name('fast-tier'), before_write=rt.pool_capacity):
                    return create()
    return admitted


class Peer:
    """The receiving software instance owns its original controller/consolidator.

    Keep this object after exceptions. No saved PID, root or launching attempt is
    an executable recovery command. settle() does metadata only and never Popen.
    """
    def __init__(self, runtime, actor, credential):
        self.rt, self.actor, self.credential = runtime, actor, credential
        self.processes = Processes()

    def adopt(self, basis):
        require(sha(read_regular(Path(__file__), MAX_SOURCE)), 'program unavailable')
        return self.rt.call('adopt', self.actor, self.credential,
                            basis='software-qa-v1 program=' + sha(read_regular(Path(__file__), MAX_SOURCE)) + '; ' + basis)

    def accept_grant(self, g):
        validate(g)
        require(g['controller'] == self.actor, 'job belongs to another execution peer')
        require(sha(read_regular(Path(__file__), MAX_SOURCE)) == g['program_sha256'], 'running executable differs from issued program')
        with self.rt.files.transaction(readonly=True) as s:
            self.rt.authority(s, self.actor, self.credential)
            require(s['actors'][self.actor]['role'] == 'QA', 'separate QA execution peer capability required')
            cfg = s['actors'][g['config_actor']]
            acc = s['actors'][g['acceptor']]
            require(cfg['role'] == 'Work' and cfg['active'] and cfg['adopted'], 'current Work configuration authority required')
            require(acc['role'] == 'QA' and acc['active'] and acc['adopted'], 'current addressed designated acceptor required')
            p = s['packets'][g['receive_packet']]
            require(p['sender'] == g['config_actor'] and p['recipient'] == self.actor and p['payload'] == {'software_qa_grant': digest(g)}, 'exact Work-issued addressed grant required')
            e = self.rt.event(s, self.actor, g['event'])
            pkg = s['packages'][g['package']]
            require(e['source_hash'] == g['event_source_hash'] and e['ack'] and not e['finished'], 'current original event/source required')
            require(pkg == {'event': g['event'], 'scope': g['scope'], 'basis': g['authority'], 'source_hash': e['source_hash']}, 'current Work package/scope/authority mismatch')
        require(Redactor([self.credential]).whole(encode(g)) == encode(g), 'credential in public grant refused')

    def run(self, g, declared_secrets=None):
        self.accept_grant(g)
        secrets = list(declared_secrets or []) + [self.credential]
        require(len(secrets) <= 31, 'at most 30 declared secrets')
        Redactor(secrets)
        self.rt.call('receipt', self.actor, self.credential, packet=g['receive_packet'], stage='picked-up', evidence='software grant ' + digest(g))
        m = export(g, self.processes)
        inputs(g)
        output = Path(g['retained_root']) / 'outputs'
        execute = self.stage(g, m, 'execute', secrets)
        require(type(execute['collection']['end']) is int and execute['collection']['complete'] and execute['result'] is not None,
                'execution collection incomplete; hold original, no consolidation/replay')
        require(execute['result']['binding'] == binding(g, m), 'execution binding mismatch')
        # A failure is still a genuinely collected execution, eligible for a
        # truthful separate consolidation. No test outcome becomes acceptance.
        consolidated = self.stage(g, m, 'consolidate', secrets)
        result = consolidated['result']
        require(result is not None and result['binding'] == binding(g, m), 'consolidation binding mismatch')
        require(result['inputs_before'] == g['inputs'] and result['inputs_after'] == g['inputs'], 'consolidation input binding incomplete')
        failures, unknowns = list(result['failures']), list(result['unknowns'])
        for name, stage in [('execution', execute), ('consolidation', consolidated)]:
            actual = stage_outcome(stage['collection'], stage['result'])
            if actual == 'failure':
                failures.append(name + ' numeric END/result failed: ' + str(stage['collection']['end']))
            elif actual not in ({'collected'} if name == 'execution' else {'success'}):
                unknowns.append(name + ' successful collection/result unavailable')
        outcome = 'failure' if failures else ('unknown' if unknowns else 'success')
        record = {'schema': 1, 'binding': binding(g, m), 'grant': g, 'manifest': m,
                  'receiver': {'actor': self.actor, 'pid': os.getpid(), 'program_sha256': g['program_sha256']},
                  'execution': execute, 'partitions': [get(output / ('partition-' + str(i) + '.json')) for i in range(5)],
                  'consolidation': consolidated, 'inputs_after': inputs(g),
                  'output_usage': usage(g), 'semantic_acceptance': 'reserved for designated actual actor',
                  'outcome': outcome, 'failures': failures, 'unknowns': unknowns}
        put(output / 'runner.json', record)
        self.settle(g, record)
        return {'runner': str(output / 'runner.json'), 'digest': digest(record), 'outcome': record['outcome'],
                'semantic_acceptance': False}

    def stage(self, g, m, mode, secrets):
        attempt = g[('execute' if mode == 'execute' else 'consolidate') + '_attempt']
        r = self.rt.call('reserve', self.actor, self.credential, attempt=attempt, event=g['event'], package=g['package'],
                         phase='qa-' + mode, resources=g['resources'], basis=g['basis'])
        collector = r['collector']
        start = self.rt.call('start', self.actor, self.credential, attempt=attempt, collector=collector,
                             substrate='owner-encounter', evidence='software-qa-v1 ' + digest(g))
        payload = {'grant': g, 'manifest': m, 'state': str(self.rt.files.path), 'actor': self.actor,
                   'credential': self.credential, 'attempt': attempt, 'collector': collector,
                   'launch_id': start['launch_id'], 'secrets': secrets}
        script = Path(g['retained_root']) / 'inputs' / PREFIX / 'software_qa.py'
        p = self.processes.popen([sys.executable, '-I', '-B', str(script), '--internal', mode], script.parent,
                                 payload, mode, guard(self.rt, self.actor, self.credential, attempt, collector, g))
        row = capture([p], g['limits']['capture_bytes'], g['limits']['seconds'] + 10, secrets + [collector])[0]
        result = parsed(row)
        public = {'binding': binding(g, m), 'attempt': attempt, 'launch_id': start['launch_id'],
                  'collection': public_row(row), 'result': result, 'outcome': stage_outcome(row, result)}
        out = Path(g['retained_root']) / 'outputs'
        put(out / (mode + '.log'), row['log'])
        put(out / (mode + '.json'), public)
        require(type(row['end']) is int, 'original process END uncollected; held')
        self.rt.call('collect', self.actor, self.credential, attempt=attempt, collector=collector,
                     launch_id=start['launch_id'], end=row['end'], result={'runner_stage': mode, 'digest': digest(public), 'complete': row['complete'],
                     'outcome': public['outcome']}, evidence='actual original Popen numeric END; retained ' + g['retained_root'])
        require(row['complete'] and result is not None, 'partial capture/collection remains unreconciled; no replay')
        self.rt.call('reconcile', self.actor, self.credential, attempt=attempt, collector=collector,
                     evidence='collected software process; admitted output only; ' + digest(public))
        return public

    def settle(self, g, record):
        """Idempotent metadata only after collection; no subprocesses or acceptance."""
        self.accept_grant(g)
        require(record['binding'] == binding(g, record['manifest']) and record['grant'] == g, 'runner/grant mismatch')
        path = Path(g['retained_root']) / 'outputs' / 'runner.json'
        require(get(path) == record and record['manifest'] == get(Path(g['retained_root']) / 'manifest.json'), 'exact complete retained runner required')
        require(record['inputs_after'] == g['inputs'] and inputs(g) == g['inputs'], 'current delivery input binding required')
        for mode in ('execute', 'consolidate'):
            a = self.rt.call('readback', self.actor, self.credential, kind='attempt', id=g[mode + '_attempt'])['value']
            stage = record['execution' if mode == 'execute' else 'consolidation']
            require(stage == get(path.parent / (mode + '.json')) and a['result']['digest'] == digest(stage), 'exact current collected stage digest required')
            require(a['state'] == 'collected' and a['reconciled'] and a['end'] == stage['collection']['end'], 'actual collected reconciled stage required')
        self.rt.call('send', self.actor, self.credential, packet=g['result_packet'], event=g['event'], recipient=g['acceptor'],
                     payload={'runner': str(path), 'digest': digest(record), 'binding': record['binding'],
                              'outcome': record['outcome'], 'semantic_acceptance': False})
        for stage in ('processed', 'settled'):
            self.rt.call('receipt', self.actor, self.credential, packet=g['receive_packet'], stage=stage,
                         evidence='software execution/delivery recorded ' + digest(record))
        return {'delivered': g['result_packet'], 'acceptor_receipts': 'owed by actual recipient', 'processing_retention': 'separate; all holds retained'}


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite): yield from flatten(test)
        else: yield test


@contextmanager
def test_module_context():
    """Each fixed module gets fresh test fixtures in the same bounded worker.

    Provider imports its own runtime fixtures. Keep the previous module's
    objects/results intact, but never reuse its mutable test globals or import
    wrapper for the next module. The outer SQL blocker stays installed; SQL
    attempts within a module still reach that module's unchanged test oracles.
    """
    original_import = builtins.__import__
    previous = {name: sys.modules.pop(name) for name in MODULES if name in sys.modules}
    try:
        yield
    finally:
        builtins.__import__ = original_import
        for name in MODULES:
            sys.modules.pop(name, None)
        sys.modules.update(previous)


def worker(g, m, index):
    before = inputs(g)
    selected = g['partitions'][index]
    root = Path(g['retained_root']) / 'outputs' / ('fixtures-' + str(index))
    root.mkdir(mode=0o700)
    sys.path.insert(0, str(Path(g['retained_root']) / 'inputs' / PREFIX))
    found, unknowns, outcomes = {}, [], []
    class Result(unittest.TestResult):
        def startTest(self, t):
            super().startTest(t)
            outcomes.append({'id': t.id(), 'status': 'unknown'})
        def mark(self, t, status):
            next(x for x in reversed(outcomes) if x['id'] == t.id())['status'] = status
        def addSuccess(self, t): super().addSuccess(t); self.mark(t, 'success')
        def addFailure(self, t, e): super().addFailure(t, e); self.mark(t, 'failure')
        def addError(self, t, e):
            super().addError(t, e)
            if any(x['id'] == t.id() for x in outcomes): self.mark(t, 'error')
            else: outcomes.append({'id': t.id(), 'status': 'setup-error'})
        def addSkip(self, t, reason): super().addSkip(t, reason); self.mark(t, 'skipped')
        def addExpectedFailure(self, t, e): super().addExpectedFailure(t, e); self.mark(t, 'expected-failure')
        def addUnexpectedSuccess(self, t): super().addUnexpectedSuccess(t); self.mark(t, 'unexpected-success')
        def addSubTest(self, t, sub, err):
            super().addSubTest(t, sub, err)
            if err: self.mark(t, 'subtest-failure')
    result = Result()
    # Preserve each module's standalone fixture/import semantics regardless of
    # Work's accepted partition pairing. No extra workers or rewritten oracles.
    for module in MODULES:
        try:
            module_root = root / module
            module_root.mkdir(mode=0o700)
            os.environ['COORDINATOR_TEST_ARTIFACTS'] = str(module_root)
            with test_module_context():
                suite = unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(module))
                current = list(flatten(suite))
                for case in current:
                    require(case.id() not in found, 'duplicate discovered testcase')
                    found[case.id()] = case
                unittest.TestSuite(c for c in current if c.id() in selected).run(result)
        except BaseException:
            unknowns.append(module + ': discovery/import/test procedure incomplete')
    missing = sorted(set(selected) - set(found))
    if missing: unknowns.append('selected cases missing from discovery')
    try: after = inputs(g)
    except (Held, OSError): after = None; unknowns.append('input binding changed/unavailable')
    return {'binding': binding(g, m), 'partition': index, 'actor': g['workers'][index],
            'pid': os.getpid(), 'controller_pid': os.getppid(), 'program_sha256': g['program_sha256'],
            'selected': selected, 'discovered': sorted(found), 'missing': missing, 'cases': outcomes,
            'tests_run': result.testsRun, 'inputs_before': before, 'inputs_after': after, 'unknowns': unknowns,
            'effects': 'fixed software tests; only separately admitted fixture outputs intended; external internals unobserved'}


def execute(payload):
    g, m = payload['grant'], payload['manifest']
    inputs(g)
    rt = Runtime(payload['state'])
    processes, results = Processes(), []
    out = Path(g['retained_root']) / 'outputs'
    script = Path(g['retained_root']) / 'inputs' / PREFIX / 'software_qa.py'
    create_guard = guard(rt, payload['actor'], payload['credential'], payload['attempt'], payload['collector'], g)
    try:
        for i in range(5):
            processes.popen([sys.executable, '-I', '-B', str(script), '--internal', 'worker'], script.parent,
                            {'grant': g, 'manifest': m, 'partition': i}, 'partition-' + str(i), create_guard)
    except BaseException:
        # Preserve all created originals; creation boundary ambiguity is not a
        # definitely-unstarted fact and never authorizes a replacement launch.
        rows = capture(processes.originals, g['limits']['capture_bytes'], g['limits']['seconds'], payload['secrets'] + [payload['collector']])
        for i, row in enumerate(rows):
            put(out / ('partial-' + str(i) + '.log'), row['log'])
            put(out / ('partial-' + str(i) + '.json'), public_row(row))
        raise Held('worker creation interrupted/ambiguous; partial originals retained; no replay')
    rows = capture(processes.originals, g['limits']['capture_bytes'], g['limits']['seconds'], payload['secrets'] + [payload['collector']])
    for i, row in enumerate(rows):
        record = {'binding': binding(g, m), 'partition': i, 'controller_pid': os.getpid(),
                  'collection': public_row(row), 'result': parsed(row)}
        put(out / ('partition-' + str(i) + '.log'), row['log'])
        put(out / ('partition-' + str(i) + '.json'), record)
        results.append(digest(record))
    return {'binding': binding(g, m), 'controller_pid': os.getpid(), 'program_sha256': g['program_sha256'],
            'records': results, 'outcome': 'collected' if all(type(r['end']) is int for r in rows) else 'unknown',
            'inputs_after': inputs(g), 'output_usage': usage(g)}


def consolidate(g, m):
    out = Path(g['retained_root']) / 'outputs'
    execution = get(out / 'execute.json')
    require(execution['binding'] == binding(g, m) and execution['result']['binding'] == binding(g, m), 'current execution binding required')
    require(execution['collection']['complete'] and type(execution['collection']['end']) is int, 'complete original execution collection required')
    require(execution['result']['controller_pid'] == execution['collection']['pid'] and execution['result']['program_sha256'] == g['program_sha256'], 'actual controller program/process binding required')
    expected = execution['result']['records']
    require(len(expected) == 5, 'exact five current run digests required')
    unknowns, failures, records, cases = [], [], [], []
    if execution['collection']['end'] != 0:
        failures.append('controller numeric END ' + str(execution['collection']['end']))
    if execution['result']['outcome'] != 'collected':
        unknowns.append('controller collection result incomplete')
    if execution['result']['inputs_after'] != g['inputs']:
        unknowns.append('controller input binding incomplete')
    before = inputs(g)
    for i in range(5):
        r = get(out / ('partition-' + str(i) + '.json'))
        require(digest(r) == expected[i] and r['binding'] == binding(g, m) and r['partition'] == i and r['controller_pid'] == execution['collection']['pid'], 'current run/candidate/attempt/grant digest mismatch')
        records.append(r)
        c, result = r['collection'], r['result']
        if not c['complete'] or type(c['end']) is not int or result is None:
            unknowns.append('partition ' + str(i) + ' incomplete collection/capture'); continue
        require(result['binding'] == binding(g, m) and result['selected'] == g['partitions'][i]
                and result['pid'] == c['pid'] and result['controller_pid'] == r['controller_pid']
                and result['actor'] == g['workers'][i] and result['program_sha256'] == g['program_sha256'], 'actual worker/process/partition binding mismatch')
        unknowns.extend(result['unknowns'])
        if result['discovered'] != sorted(g['inventory']): unknowns.append('discovery differs from Work complete inventory')
        if result['inputs_before'] != g['inputs'] or result['inputs_after'] != g['inputs']: unknowns.append('partition input binding incomplete')
        if c['end'] != 0: failures.append('partition ' + str(i) + ' numeric END ' + str(c['end']))
        cases.extend(result['cases'])
    actual = [c['id'] for c in cases]
    if sorted(actual) != sorted(g['inventory']) or len(set(actual)) != len(actual): unknowns.append('missing/duplicate/setup cases in actual execution')
    failures.extend(c['id'] + ':' + c['status'] for c in cases if c['status'] in {'failure', 'error', 'setup-error', 'subtest-failure', 'unexpected-success'})
    unknowns.extend(c['id'] + ':' + c['status'] for c in cases if c['status'] not in {'success', 'failure', 'error', 'setup-error', 'subtest-failure', 'unexpected-success'})
    after = inputs(g)
    return {'binding': binding(g, m), 'record_digests': expected, 'cases': cases,
            'inputs_before': before, 'inputs_after': after, 'failures': failures, 'unknowns': unknowns,
            'outcome': 'failure' if failures else ('unknown' if unknowns else 'success'),
            'semantic_acceptance': False, 'effects': 'fixture outputs retained; no semantic disposition or retirement',
            'collection': 'separate consolidation; its numeric END does not imply successful tests'}


def internal(mode):
    # -I does not prepend the script directory. Add only its explicit public
    # sibling source path, before imports in the bootstrap below.
    payload = json.loads(sys.stdin.buffer.read(65537))
    g = validate(payload['grant'])
    m = payload['manifest']
    require(m == get(Path(g['retained_root']) / 'manifest.json') and m['grant'] == digest(g), 'frozen complete manifest mismatch')
    if mode == 'worker':
        # A lost controller never grants a worker an unlimited lifetime. This
        # timer bounds this fixed worker, not opaque descendants or host activity.
        signal.setitimer(signal.ITIMER_REAL, g['limits']['seconds'] + 5)
        result = worker(g, m, payload['partition'])
    elif mode == 'execute': result = execute(payload)
    else: result = consolidate(g, m)
    print('SOFTWARE_QA_RESULT=' + json.dumps(result, separators=(',', ':'), sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state')
    parser.add_argument('--actor')
    parser.add_argument('--internal', choices=('worker', 'execute', 'consolidate'), help=argparse.SUPPRESS)
    parser.add_argument('command', nargs='?', choices=('adopt', 'run', 'settle'))
    args = parser.parse_args()
    try:
        if args.internal:
            internal(args.internal)
        else:
            require(args.state and args.actor and args.command, 'explicit state, execution peer and operation required')
            request = json.loads(sys.stdin.buffer.read(32769))
            require(len(encode(request)) <= 32768, 'finite receive request exceeded')
            peer = Peer(Runtime(args.state), args.actor, os.environ.get('COORDINATOR_TOKEN', ''))
            if args.command == 'adopt':
                require(set(request) == {'basis'}, 'adopt accepts only encounter basis')
                result = peer.adopt(request['basis'])
            else:
                require(set(request) == ({'grant', 'declared_secrets'} if args.command == 'run' else {'grant'}), 'exact command fields required')
                g = validate(request['grant'])
                result = peer.run(g, request['declared_secrets']) if args.command == 'run' else peer.settle(g, get(Path(g['retained_root']) / 'outputs' / 'runner.json'))
            print(json.dumps({'status': 'ok', 'result': result}))
        return 0
    except (Held, OSError, ValueError, KeyError, TypeError) as exc:
        # Never print exception bodies, paths, requests, credentials or Git diagnostics.
        print(json.dumps({'status': 'held', 'reason': type(exc).__name__, 'replay': 'not authorized; original custody retained'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
