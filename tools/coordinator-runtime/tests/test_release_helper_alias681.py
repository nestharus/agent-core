"""Finite release qualification on fresh, explicitly inventoried Linux fixtures.

Run directly with --fixtures ABS_NEW_DIRECTORY --report ABS_JSON. The default
source is this checkout; --source-root accepts a separately staged public base.
No provider, native process, account store, actual runtime or network is used.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import copy
import hashlib
import importlib
from importlib.util import cache_from_source
import json
import os
from pathlib import Path
import posix
import sqlite3
import statistics
import sys
import time


MANIFEST = json.loads(Path(__file__).with_name('release681_sources.json').read_text())
RETENTION = ('queue_transport.py', 'active_listener.py', 'catalog.py',
             'board_store.py', 'retention.py')
PACKAGE = 'coordinator_runtime'
ACTIVE = None
BLOCKED_EFFECTS = []


def canonical(value):
    """Linux-only oracle, independent of production Path/index logic."""
    return '/' + os.fspath(value).lstrip('/')


def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'socket.__new__', 'socket.connect'}:
        BLOCKED_EFFECTS.append(event)
        raise AssertionError('finite fixture runner forbids external effects: ' + event)
    if ACTIVE is not None and event in {'open', 'os.listdir', 'os.scandir'}:
        value = ACTIVE.pending if event == 'open' and ACTIVE.pending is not None else args[0]
        ACTIVE.record('audit-' + event, value)


sys.addaudithook(audit)


class Trace:
    """Hook importlib's posix backend too; audit alone misses loader stats.

    Track owned directory descriptors directly. Never resolve /proc, seek an
    alias or guess a cwd-prefixed pathname for a dir_fd-relative open.
    """
    def __init__(self, targets):
        self.targets = [canonical(p) for p in targets]
        self.events = []
        self.observed = Counter()
        self.fds = {}
        self.pending = None
        self.saved = []

    def absolute(self, value, dir_fd=None):
        if isinstance(value, int):
            return self.fds.get(value)
        if not isinstance(value, (str, bytes, os.PathLike)):
            return None
        text = os.fsdecode(value)
        if not text.startswith('/'):
            if dir_fd not in self.fds:
                return None
            text = self.fds[dir_fd] + '/' + text
        return canonical(text)

    def record(self, operation, value, dir_fd=None):
        path = self.absolute(value, dir_fd)
        if path is None:
            return
        self.observed[operation] += 1
        if any(path == p or path.startswith(p.rstrip('/') + '/') for p in self.targets):
            self.events.append({'operation': operation, 'path': path})

    def __enter__(self):
        global ACTIVE
        assert ACTIVE is None
        for module in (os, posix):
            for name in ('stat', 'lstat'):
                original = getattr(module, name)
                def wrapped(value, *args, _original=original, _label=module.__name__+'.'+name, **kwargs):
                    self.record(_label, value, kwargs.get('dir_fd'))
                    return _original(value, *args, **kwargs)
                self.saved.append((module, name, original))
                setattr(module, name, wrapped)
        original_open = os.open
        def opened(value, flags, mode=0o777, *, dir_fd=None):
            path = self.absolute(value, dir_fd)
            prior, self.pending = self.pending, path
            try:
                fd = original_open(value, flags, mode, dir_fd=dir_fd)
                if path is not None:
                    self.fds[fd] = path
                return fd
            finally:
                self.pending = prior
        original_close = os.close
        def closed(fd):
            try:
                return original_close(fd)
            finally:
                self.fds.pop(fd, None)
        self.saved.extend([(os, 'open', original_open), (os, 'close', original_close)])
        os.open, os.close = opened, closed
        ACTIVE = self
        return self

    def __exit__(self, *args):
        global ACTIVE
        ACTIVE = None
        for module, name, original in reversed(self.saved):
            setattr(module, name, original)


def load(root):
    for name in list(sys.modules):
        if name == PACKAGE or name.startswith(PACKAGE + '.'):
            del sys.modules[name]
    path = str(root/'tools/coordinator-runtime')
    sys.path.insert(0, path)
    try:
        return importlib.import_module(PACKAGE+'.configuration')
    finally:
        sys.path.remove(path)


def deferred_cold():
    package = sys.modules[PACKAGE]
    for name in ('bounded_log', 'custody', 'cleanup', 'retention_dependency', 'execution_pool'):
        sys.modules.pop(PACKAGE+'.'+name, None)
        package.__dict__.pop(name, None)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Runtime:
    """Actual SQLite current-selection queries; never a production journal."""
    processing = None
    def __init__(self, module, config):
        self.module, self.config = module, config
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript(module.SCHEMA)

    def one(self, sql, params=()):
        return self.db.execute(sql, params).fetchone()

    def bind(self, release):
        binding = self.module.digest(self.config)
        self.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
                        ('original', binding, 'original', binding,
                         json.dumps({'basis': {'release': release}}), 'owned-fixture', 0.0))


class Fixture:
    def __init__(self, source, root):
        self.root = root
        root.mkdir(parents=True, exist_ok=False)
        self.manifest_bytes = {}
        for relative in MANIFEST:
            data = (source/relative).read_bytes()
            path = root/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.manifest_bytes[relative] = sha(data)
        self.modules = root/'tools/coordinator-runtime/coordinator_runtime'
        self.provider = root/'synthetic-retention'
        self.provider.mkdir()
        self.pins = {}
        for name in RETENTION:
            body = b'# inert owned retention source\n'
            if name == 'retention.py':
                body += b'def snapshot_lock():\n    return None\n'
            (self.provider/name).write_bytes(body)
            self.pins[name] = sha(body)
        self.template = root/'ordinary-method.md'
        self.template.write_text('Owned ordinary task template. No external startup.\n')
        self.control = root/'public-pool.toml'
        self.operator = root/'selected-operator.json'
        self.state = root/'never-created-pool-state'
        self.pool(['.codex2', '.codex5'])
        self.config = {
            'artifact_exclusions': [],
            'board_library': str(root/'tools/message-board'),
            'operator_cli': str(root/'tools/coordinator-runtime/coordinator'),
            'canonical_publication': {'method': 'retention-same-inode-v1',
                                      'library': str(self.provider), 'source_pins': self.pins},
            'control_receive': {'instructions': str(root/'tools/coordinator-runtime/templates/coordinator-receive.md')},
            'operator_config': str(self.operator),
            'execution_pool_routes': str(self.control),
            'tasks': {'ordinary': {'templates': [str(self.template)],
                                   'effect_authority': {'operations': ['read-source']}}},
        }
        self.sync()
        self.c = load(root)
        self.runtime = Runtime(self.c, self.config)

    def sync(self):
        self.operator.write_text(json.dumps(self.config, sort_keys=True))

    def pool(self, enabled, extra=''):
        self.control.write_text('[providers.codex]\npool = '+json.dumps(enabled)+
            '\nmanual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n'+
            extra+'\n[rotation]\nstate_dir = '+json.dumps(str(self.state))+'\n')

    def expected(self):
        # No production enumeration/return is used to define this expected map.
        selected = [self.root/p for p in MANIFEST]
        selected += [self.provider/p for p in RETENTION]
        selected += [self.operator, self.template]
        raw = self.control.read_bytes()
        marker = b'pool = '
        before, rest = raw.split(marker, 1)
        _, after = rest.split(b'\n', 1)
        static = before + marker + b'[]\n' + after
        return {'root': str(self.root),
                'files': {str(p): sha(p.read_bytes()) for p in selected},
                'pool_control': {'routes': str(self.control), 'static_sha256': sha(static)},
                'qualification': 'source bytes only; no installed provider/native or deployment claim'}

    def release(self):
        return self.c.release(self.runtime, self.config)


class Suite:
    def __init__(self):
        self.rows = []

    def check(self, name, action):
        try:
            detail = action()
            self.rows.append({'name': name, 'pass': True, 'detail': detail})
        except Exception as exc:
            self.rows.append({'name': name, 'pass': False,
                              'error': type(exc).__name__+': '+str(exc)[:1500],
                              'detail': getattr(exc, 'detail', None)})

    def guarded(self, f, name, targets, change, *, warm):
        before = copy.deepcopy(f.config)
        if warm:
            f.release()
        else:
            deferred_cold()
        change(f.config)
        f.sync()
        error = None
        try:
            with Trace(targets) as trace:
                try:
                    f.release()
                except f.c.Refusal as exc:
                    error = str(exc)
            detail = {'refusal': error, 'target_event_count': len(trace.events),
                      'target_operations': dict(Counter(e['operation'] for e in trace.events)),
                      'target_events_first64': trace.events[:64],
                      'observed_operations': dict(trace.observed)}
            if error is None or trace.events:
                failure = AssertionError('guard must refuse with zero target acquisitions')
                failure.detail = detail
                raise failure
            return detail
        finally:
            f.config.clear()
            f.config.update(before)
            f.sync()


def qualification(suite, f, mode):
    def whole():
        expected = f.expected()
        deferred_cold()
        with Trace([f.modules/'bounded_log.py']) as trace:
            cold = f.release()
        assert cold == expected
        assert any(e['operation'].startswith('posix.stat') for e in trace.events), trace.events
        assert any(e['operation'] == 'audit-open' for e in trace.events), trace.events
        warm = f.release()
        assert warm == expected == cold
        assert not f.state.exists()
        return {'complete_files': len(expected['files']), 'cold_helper_events': trace.events,
                'positive_tracer_operations': dict(trace.observed)}
    suite.check(mode+'/independent-whole-release-and-positive-tracer', whole)
    for warm in (False, True):
        state = 'warm' if warm else 'cold'
        # F2 exact deferred closure, plus retained F1/pool loader protection.
        sources = [f.modules/n for n in ('bounded_log.py', 'custody.py', 'cleanup.py',
                                         'retention_dependency.py', 'execution_pool.py')]
        sources += [f.root/'tools/direct-child/execution_pool.py']
        for source in sources:
            for target in (source, Path(cache_from_source(str(source)))):
                name = mode+'/'+state+'/exclude/'+str(target.relative_to(f.root))
                suite.check(name, lambda target=target, name=name: suite.guarded(
                    f, name, [target], lambda cfg: cfg.update(artifact_exclusions=[str(target)]), warm=warm))
        # Canonical single-root guards remain active for directories and inputs.
        for target in (f.modules, f.modules/'__pycache__', f.operator, f.control, f.template, f.provider/'catalog.py'):
            suite.check(mode+'/'+state+'/canonical/'+str(target.relative_to(f.root)),
                lambda target=target: suite.guarded(f, 'canonical', [target],
                    lambda cfg: cfg.update(artifact_exclusions=[str(target)]), warm=warm))
        # Both directions of Linux root spelling, with a same-operands control.
        # The target oracle maps // to / lexically; no actual private alias probe.
        for target, field in ((f.modules, None), (f.modules/'bounded_log.py', None),
                              (Path(cache_from_source(str(f.modules/'bounded_log.py'))), None),
                              (f.modules/'__pycache__', None),
                              (f.control, 'execution_pool_routes'), (f.operator, 'operator_config'),
                              (f.template, 'template'), (f.provider/'catalog.py', 'provider')):
            for exclusion_double, candidate_double in ((True, False), (False, True), (True, True)):
                # A module-directory candidate spelling is supplied by __file__.
                old_file = f.c.__file__
                def change(cfg, target=target, field=field, ed=exclusion_double, cd=candidate_double):
                    cfg['artifact_exclusions'] = [('//' + str(target).lstrip('/')) if ed else str(target)]
                    if cd:
                        if field in {'execution_pool_routes', 'operator_config'}:
                            cfg[field] = '//' + str(target).lstrip('/')
                        elif field == 'template':
                            cfg['tasks']['ordinary']['templates'] = ['//' + str(target).lstrip('/')]
                        elif field == 'provider':
                            cfg['canonical_publication']['library'] = '//' + str(f.provider).lstrip('/')
                        else:
                            f.c.__file__ = '//' + old_file.lstrip('/')
                try:
                    suite.check(mode+'/'+state+'/root-spelling/'+str(target.relative_to(f.root))+
                                '/'+str((exclusion_double, candidate_double)),
                        lambda target=target: suite.guarded(f, 'double-root', [target], change, warm=warm))
                finally:
                    f.c.__file__ = old_file
        # // selected inputs are refused even without an exclusion entry.
        for field, target in (('execution_pool_routes', f.control), ('operator_config', f.operator)):
            suite.check(mode+'/'+state+'/noncanonical-input/'+field,
                lambda field=field, target=target: suite.guarded(f, field, [target],
                    lambda cfg: cfg.update({field: '//'+str(target).lstrip('/')}), warm=warm))
        # Direct path-helper checks cover both spellings independently of any
        # earlier release preflight. All operands are freshly owned fixtures.
        for target in (f.modules, f.modules/'bounded_log.py',
                       Path(cache_from_source(str(f.modules/'bounded_log.py'))), f.control):
            for ed, cd in ((True, False), (False, True), (True, True)):
                def lexical(target=target, ed=ed, cd=cd):
                    excluded = '//'+str(target).lstrip('/') if ed else str(target)
                    value = '//'+str(target).lstrip('/') if cd else str(target)
                    with Trace([target]) as trace:
                        try:
                            f.c._path(value, [excluded])
                        except f.c.Refusal as exc:
                            assert not trace.events, trace.events
                            return {'refusal': str(exc), 'target_events': []}
                    raise AssertionError('noncanonical path/index operand accepted')
                suite.check(mode+'/'+state+'/path-helper-root/'+str(target.relative_to(f.root))+'/'+str((ed, cd)), lexical)
    f.runtime.bind(f.release())
    suite.check(mode+'/current-selected-release', lambda: f.c.assert_release(f.runtime))
    for relative in ('tools/coordinator-runtime/coordinator_runtime/configuration.py',
                     'tools/coordinator-runtime/coordinator_runtime/bounded_log.py',
                     'tools/coordinator-runtime/coordinator_runtime/retention_dependency.py',
                     'tools/coordinator-runtime/coordinator_runtime/execution_pool.py',
                     'tools/direct-child/execution_pool.py', 'tools/branch_release.py',
                     'tools/operational_contracts.py', 'tools/coordinator-runtime/final-release-risk.md'):
        def fresh(relative=relative):
            path = f.root/relative
            before = path.read_bytes()
            try:
                path.write_bytes(before+b'\n# owned fixture freshness mutation\n')
                result = f.release()
                assert result['files'][str(path)] == sha(path.read_bytes())
                try:
                    f.c.assert_release(f.runtime)
                except f.c.Refusal:
                    return {'fresh_hash': result['files'][str(path)], 'old_selection_refused': True}
                raise AssertionError('selected old source was accepted')
            finally:
                path.write_bytes(before)
        suite.check(mode+'/fresh-source/'+relative, fresh)
    def currentness():
        old = f.runtime.config
        f.runtime.config = {**old, 'owned-currentness-change': True}
        try:
            try:
                f.c.assert_release(f.runtime)
            except f.c.Refusal as exc:
                assert 'historical' in str(exc)
                return str(exc)
            raise AssertionError('historical config accepted')
        finally:
            f.runtime.config = old
    suite.check(mode+'/configuration-currentness', currentness)
    def operator_equality():
        f.operator.write_text('{}')
        try:
            try:
                f.release()
            except f.c.Refusal as exc:
                assert 'exact selected' in str(exc)
                return str(exc)
            raise AssertionError('different operator bytes accepted')
        finally:
            f.sync()
    suite.check(mode+'/operator-json-equality', operator_equality)
    def retained_pin():
        path = f.provider/'catalog.py'
        old = path.read_bytes()
        try:
            path.write_bytes(old+b'# changed\n')
            try:
                f.release()
            except f.c.Refusal as exc:
                assert 'source changed' in str(exc)
                return str(exc)
            raise AssertionError('retained source pin ignored')
        finally:
            path.write_bytes(old)
    suite.check(mode+'/retention-pins', retained_pin)
    for enabled in ([], ['.codex'], ['.codex3', '.codex4'], sorted(['.codex', '.codex2', '.codex3', '.codex4', '.codex5'])):
        def hot(enabled=enabled):
            f.pool(enabled)
            try:
                result = f.release()
                assert result == f.expected()
                f.c.assert_release(f.runtime)
                assert not f.state.exists()
                return {'enabled': enabled, 'static_binding_unchanged': True}
            finally:
                f.pool(['.codex2', '.codex5'])
        suite.check(mode+'/hot-pool/'+str(enabled), hot)
    def pool_static():
        f.pool(['.codex2'], 'public_extra = "changed"\n')
        try:
            result = f.release()
            assert result == f.expected()
            try:
                f.c.assert_release(f.runtime)
            except f.c.Refusal:
                return 'changed static bytes freshly bound and old selection refused'
            raise AssertionError('static control change accepted')
        finally:
            f.pool(['.codex2', '.codex5'])
    suite.check(mode+'/static-pool-currentness', pool_static)
    for bad in (['.codex2', '.codex2'], ['.fictional-account']):
        def invalid(bad=bad):
            f.pool(bad)
            try:
                try:
                    f.release()
                except f.c.Refusal:
                    return 'invalid public pool refused warm'
                raise AssertionError('invalid public pool accepted')
            finally:
                f.pool(['.codex2', '.codex5'])
        suite.check(mode+'/invalid-pool/'+str(bad), invalid)
    def final_preservation():
        assert all(sha((f.root/p).read_bytes()) == pin for p, pin in f.manifest_bytes.items())
        assert all(sha((f.provider/p).read_bytes()) == pin for p, pin in f.pins.items())
        assert f.release() == f.expected()
        f.c.assert_release(f.runtime)
        return {'restored_production_files': len(f.manifest_bytes), 'retention_files': len(f.pins)}
    suite.check(mode+'/final-source-preservation', final_preservation)


def latency(suite, f):
    rows = []
    for count in (0, 32, 64):
        f.config['artifact_exclusions'] = [str(f.root/'fictional-excluded'/str(n)) for n in range(count)]
        f.sync()
        expected = f.expected()
        deferred_cold()
        start = time.perf_counter()
        cold = f.release()
        cold_ms = (time.perf_counter()-start)*1000
        samples = []
        def timed():
            assert cold == expected
            for _ in range(21):
                start = time.perf_counter()
                actual = f.release()
                samples.append((time.perf_counter()-start)*1000)
                assert actual == expected
            return {'exclusions': count, 'whole_results_compared': 22}
        suite.check('latency/equality/'+str(count), timed)
        rows.append({'exclusions': count, 'cold_ms': cold_ms, 'warm_samples_ms': samples,
                     'median_ms': statistics.median(samples), 'complete_files': len(expected['files'])})
    f.config['artifact_exclusions'] = []
    f.sync()
    return rows


def symlinks(suite, source, root):
    """Separate immutable attempts; keep every alias fixture for review.

    Unexcluded aliases may be lstatted to refuse them. Their referents must
    never be opened or statted, and import-cache hits must not bypass refusal.
    """
    for writes in (False, True):
        sys.dont_write_bytecode = not writes
        for warm in (False, True):
            for kind in ('helper-source', 'helper-cache', 'control', 'module-directory'):
                label = 'aliases-'+str(writes)+'-'+str(warm)+'-'+kind
                f = Fixture(source, root/label)
                if warm:
                    f.release()
                else:
                    deferred_cold()
                if kind == 'helper-source':
                    path = f.modules/'bounded_log.py'
                elif kind == 'helper-cache':
                    path = Path(cache_from_source(str(f.modules/'bounded_log.py')))
                elif kind == 'control':
                    path = f.control
                else:
                    path = f.modules
                original = path.with_name(path.name+'.preserved681')
                if path.exists():
                    path.rename(original)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    original.write_bytes(b'owned cache alias target, never imported\n')
                path.symlink_to(original, target_is_directory=kind == 'module-directory')
                def refused():
                    error = None
                    with Trace([path, original]) as trace:
                        try:
                            f.release()
                        except f.c.Refusal as exc:
                            error = str(exc)
                    assert error is not None, 'symlink was accepted'
                    assert not any(e['path'] == canonical(original) or
                                   e['path'].startswith(canonical(original)+'/') or
                                   e['operation'] == 'audit-open' for e in trace.events), trace.events
                    assert 'alias' in error, error
                    return {'refusal': error, 'events': trace.events, 'referent_acquisitions': 0}
                suite.check(label, refused)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, default=Path(__file__).absolute().parents[3])
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('this fixture qualification requires Linux')
    assert args.fixtures.is_absolute() and args.report.is_absolute()
    args.fixtures.mkdir(parents=True, exist_ok=False)
    suite = Suite()
    timings = None
    fixtures = []
    for writes in (False, True):
        sys.dont_write_bytecode = not writes
        mode = 'cache-on' if writes else 'cache-off'
        fixture = Fixture(args.source_root, args.fixtures/mode)
        fixtures.append(fixture)
        qualification(suite, fixture, mode)
        if not writes:
            timings = latency(suite, fixture)
    symlinks(suite, args.source_root, args.fixtures)
    result = {'pass': sum(r['pass'] for r in suite.rows),
              'fail': sum(not r['pass'] for r in suite.rows), 'assertions': suite.rows,
              'latency': timings, 'blocked_effects': BLOCKED_EFFECTS,
              'source_manifest_files': len(MANIFEST),
              'limits': 'Fixture release boundary after trusted bootstrap; cooperative Python loader. No deployment/retirement/outer-END/adoption qualification.'}
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('pass', 'fail', 'blocked_effects', 'source_manifest_files')}))
    failed = [r['name'] for r in suite.rows if not r['pass']]
    print(json.dumps({'failure_count': len(failed), 'failures_first12': failed[:12]}))
    return bool(result['fail'])


if __name__ == '__main__':
    sys.exit(main())
