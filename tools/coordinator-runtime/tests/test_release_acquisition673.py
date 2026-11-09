"""Owned source copies only; no deployed module unloading or held-path probes.

Set RFQ673_FIXTURES to a new owned directory to retain every fixture. These
tests import each copy under a fresh package name; the interpreter and standard
library are trusted bootstrap inputs, as they are at release's call boundary.
"""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid


SOURCE = Path(__file__).absolute().parents[1]
ROOT = SOURCE.parent.parent
PROVIDERS = ('queue_transport.py', 'active_listener.py', 'catalog.py',
             'board_store.py', 'retention.py')
LOCAL_IMPORTS = ('retention_dependency.py', 'custody.py', 'cleanup.py')
AUDIT = []


def audit(event, args):
    if AUDIT and event in {'open', 'os.scandir', 'os.listdir'}:
        AUDIT[-1].record(event, args[0])


sys.addaudithook(audit)


class Trace:
    """Observe OS metadata functions and CPython loader audit events."""
    def __init__(self, excluded):
        self.excluded = Path(excluded)
        self.events = []

    def record(self, operation, path):
        if isinstance(path, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(path))
            if path == self.excluded or path.is_relative_to(self.excluded):
                self.events.append((operation, str(path)))

    def wrap(self, name):
        original = getattr(os, name)
        def call(path, *args, **kwargs):
            self.record(name, path)
            return original(path, *args, **kwargs)
        return call

    def __enter__(self):
        self.stat = patch.object(os, 'stat', self.wrap('stat'))
        self.lstat = patch.object(os, 'lstat', self.wrap('lstat'))
        self.stat.start()
        self.lstat.start()
        AUDIT.append(self)
        return self

    def __exit__(self, *args):
        AUDIT.pop()
        self.lstat.stop()
        self.stat.stop()


class Fixture:
    def __init__(self):
        parent = os.environ.get('RFQ673_FIXTURES')
        self.area = Path(tempfile.mkdtemp(prefix='release673-', dir=parent))
        self.root = self.area/'release'
        self.directory = self.root/'tools/coordinator-runtime'
        self.modules = self.directory/'coordinator_runtime'
        self.home = self.area/'home'
        self.home.mkdir()
        # This is the public, tracked module directory, not recursive discovery.
        sources = sorted((SOURCE/'coordinator_runtime').glob('*.py'))
        self.modules.mkdir(parents=True)
        for source in sources:
            (self.modules/source.name).write_bytes(source.read_bytes())
        names = ['tools/coordinator-runtime/coordinator',
                 'tools/coordinator-runtime/templates/coordinator-receive.md',
                 'tools/coordinator-runtime/final-release-risk.md',
                 'tools/branch_release.py', 'tools/operational_contracts.py',
                 'tools/direct-child/execution_pool.py', 'tools/direct-child/dispatch.py',
                 'tools/direct-child/review_context.py',
                 *('tools/direct-child/'+p for p in ('continuing_review.py', 'opaque_dialogue.py', 'profile_lease.py')),
                 'tools/direct-codex-child/launch.sh',
                 *('tools/message-board/'+n for n in
                   ('catalog.py', 'board_store.py', 'active_listener.py',
                    'queue_transport.py', 'managed_owner.py'))]
        for name in names:
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT/name).read_bytes())
        self.provider = self.area/'provider'
        self.provider.mkdir()
        self.pins = {}
        for name in PROVIDERS:
            body = b'# inert owned dependency, never executed\n'
            (self.provider/name).write_bytes(body)
            self.pins[name] = hashlib.sha256(body).hexdigest()
        self.templates = []
        for n in range(4):
            path = self.area/f'template-{n}.md'
            path.write_text('Owned template '+str(n)+'\n')
            self.templates.append(path)
        self.operator = self.area/'operator.json'
        self.routes = self.area/'routes.toml'
        self.routes.write_text('[rotation]\nstate_dir = '+json.dumps(str(self.area/'pool-state'))+
            '\n[providers.codex]\npool = [".codex2", ".codex3", ".codex5"]\n'+
            'manual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n')
        self.config = dict(board_library=str(self.root/'tools/message-board'),
            operator_cli=str(self.directory/'coordinator'), operator_config=str(self.operator),
            canonical_publication=dict(method='retention-same-inode-v1',
                library=str(self.provider), source_pins=self.pins),
            control_receive=dict(instructions=str(self.directory/'templates/coordinator-receive.md')),
            execution_pool_routes=str(self.routes),
            artifact_exclusions=[str(self.area/'excluded'/str(n)) for n in range(64)],
            tasks={str(n): dict(templates=[str(p)]) for n, p in enumerate(self.templates)})
        self.save()
        self.identity = 'owned_release673_'+uuid.uuid4().hex
        spec = importlib.util.spec_from_file_location(self.identity, self.modules/'__init__.py',
            submodule_search_locations=[str(self.modules)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[self.identity] = package
        spec.loader.exec_module(package)
        self.configuration = importlib.import_module(self.identity+'.configuration')
        self.Refusal = importlib.import_module(self.identity+'.contracts').Refusal

    def save(self):
        self.operator.write_text(json.dumps(self.config, sort_keys=True))

    def release(self):
        with patch.object(Path, 'home', return_value=self.home):
            return self.configuration.release(None, self.config)


class ReleaseAcquisition(unittest.TestCase):
    def test_cold_and_warm_exclusions_precede_os_and_loader_access(self):
        for warm in (False, True):
            for target in ('modules', 'configuration.py', *LOCAL_IMPORTS,
                           'runtime-cache', 'retention-cache', 'pool-cache'):
                with self.subTest(warm=warm, target=target):
                    f = Fixture()
                    if warm:
                        f.release()
                    excluded = {
                        'modules': f.modules,
                        'runtime-cache': f.modules/'__pycache__',
                        'retention-cache': Path(importlib.util.cache_from_source(
                            str(f.modules/'retention_dependency.py'))),
                        'pool-cache': Path(importlib.util.cache_from_source(
                            str(f.root/'tools/direct-child/execution_pool.py'))),
                    }.get(target, f.modules/target)
                    f.config['artifact_exclusions'] = [str(excluded)]
                    f.save()
                    with Trace(excluded) as trace:
                        with self.assertRaisesRegex(f.Refusal, 'excluded before metadata'):
                            f.release()
                    self.assertEqual(trace.events, [], 'acquired excluded operand before refusal')
                    if not warm and target in {'modules', 'configuration.py', *LOCAL_IMPORTS,
                                               'runtime-cache', 'retention-cache'}:
                        self.assertNotIn(f.identity+'.retention_dependency', sys.modules)

    def test_entire_release_hashes_every_file_on_every_call(self):
        f = Fixture()
        expected_paths = {*(f.modules/p.name for p in (SOURCE/'coordinator_runtime').glob('*.py')),
            f.directory/'coordinator', f.directory/'templates/coordinator-receive.md',
            f.directory/'final-release-risk.md', f.root/'tools/branch_release.py',
            f.root/'tools/operational_contracts.py', f.root/'tools/direct-child/execution_pool.py',
            f.root/'tools/direct-child/dispatch.py', f.root/'tools/direct-child/review_context.py',
            f.root/'tools/direct-codex-child/launch.sh',
            *(f.root/'tools/message-board'/p for p in
              ('catalog.py', 'board_store.py', 'active_listener.py', 'queue_transport.py', 'managed_owner.py')),
            *(f.provider/p for p in PROVIDERS), f.operator, *f.templates}
        # Release contract is the independently declared complete member set,
        # including the current module inventory; it has no fixed cardinality.
        expected = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in expected_paths}
        original = Path.read_bytes
        for _ in range(2):
            seen = {}
            def read(path):
                body = original(path)
                seen[str(path)] = body
                return body
            with patch.object(Path, 'read_bytes', read):
                actual = f.release()
            self.assertEqual(actual['files'], expected)
            self.assertEqual(set(seen), set(expected) | {str(f.routes)})
            self.assertEqual(seen[str(f.routes)], f.routes.read_bytes())
            self.assertTrue(all(hashlib.sha256(body).hexdigest() == expected[p]
                                for p, body in seen.items() if p in expected))

    def test_fresh_bytes_exclusions_and_pool_control(self):
        f = Fixture()
        expected = f.release()
        for path in (f.modules/'configuration.py', f.templates[0], f.provider/'catalog.py', f.operator):
            with self.subTest(path=path.name):
                body = path.read_bytes()
                stamp = path.stat()
                path.write_bytes(b'X'+body[1:])
                os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
                if path in {f.provider/'catalog.py', f.operator}:
                    with self.assertRaises((f.Refusal, ValueError)):
                        f.release()
                else:
                    self.assertNotEqual(f.release(), expected)
                path.write_bytes(body)
                self.assertEqual(f.release(), expected)
        routes = f.routes.read_text()
        for enabled in ('[]', '[".codex"]', '[".codex4"]',
                        '[".codex", ".codex2", ".codex3", ".codex4", ".codex5"]'):
            f.routes.write_text(routes.replace('[".codex2", ".codex3", ".codex5"]', enabled))
            self.assertEqual(f.release(), expected)
        f.routes.write_text(routes.replace('pool-state', 'other-state'))
        self.assertNotEqual(f.release(), expected)
        f.routes.write_text(routes)
        f.config['artifact_exclusions'].append(str(f.templates[0]))
        f.save()
        with self.assertRaisesRegex(f.Refusal, 'excluded before metadata'):
            f.release()

    def test_bootstrap_and_dependency_aliases_refuse(self):
        for target in ('bootstrap', 'dependency', 'cache'):
            with self.subTest(target=target):
                f = Fixture()
                if target == 'bootstrap':
                    alias = f.area/'alias'
                    alias.symlink_to(f.root, target_is_directory=True)
                    f.configuration.__file__ = str(alias/'tools/coordinator-runtime/coordinator_runtime/configuration.py')
                elif target == 'dependency':
                    path = f.modules/'retention_dependency.py'
                    original = f.area/'dependency.py'
                    path.rename(original)
                    path.symlink_to(original)
                else:
                    original = f.area/'cache'
                    original.mkdir()
                    (f.modules/'__pycache__').symlink_to(original, target_is_directory=True)
                with self.assertRaisesRegex(f.Refusal, 'aliases'):
                    f.release()
                self.assertNotIn(f.identity+'.retention_dependency', sys.modules)

    def test_lexical_semantics_profiles_and_current_index(self):
        f = Fixture()
        mod = f.configuration
        profiles = importlib.import_module(f.identity+'.contracts').PROFILES
        with patch.object(Path, 'home', return_value=f.home):
            with self.assertRaisesRegex(f.Refusal, 'canonical single-root'):
                mod._PathExclusions(['//'])
            for exclusions in (['/a/b'], ['/'], ['a/b'], ['/a/./b/'], [],
                               [Path('/a/b')], ['/α/β'], ['/adjacent']):
                index = mod._PathExclusions(exclusions)
                for value in ('/a/b', '/a/bc', '/a/b/c', '//a/b', '/', '/a//b/./c',
                              '/α/β/γ', '/adjacent-sibling',
                              *(str(f.home/p/'fictional') for p in profiles)):
                    path = Path(value)
                    if value.startswith('//'):
                        with patch.object(Path, 'is_symlink', side_effect=AssertionError('noncanonical metadata')):
                            with self.assertRaisesRegex(f.Refusal, 'absolute canonical'):
                                mod._path(value, index)
                        continue
                    expected = any(path == Path(p) or path.is_relative_to(Path(p))
                        for p in [*exclusions, *(f.home/p for p in profiles)])
                    self.assertEqual(index.contains(path), expected)
            f.configuration.__file__ = str(f.home/'.codex4'/'configuration.py')
            with Trace(f.home/'.codex4') as trace:
                with self.assertRaisesRegex(f.Refusal, 'excluded before metadata'):
                    f.release()
            self.assertEqual(trace.events, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
