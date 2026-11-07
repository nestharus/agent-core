"""Maker regressions for lexical resource-root refusal; fictional operands only."""
from contextlib import ExitStack, contextmanager
import copy
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, contracts, resource_scopes as scopes
from coordinator_runtime.contracts import Refusal


class MetadataReached(AssertionError):
    pass


@contextmanager
def no_metadata():
    """A refusal must beat every Path metadata entry point, not just stat."""
    with ExitStack() as stack:
        calls = []
        def deny(*args, **kwargs):
            calls.append(args)
            raise MetadataReached('metadata reached')
        for name in ('is_symlink', 'stat', 'lstat', 'resolve', 'exists',
                     'is_file', 'is_dir', 'samefile', 'iterdir', 'glob', 'rglob'):
            stack.enter_context(patch.object(Path, name, side_effect=deny))
        yield calls


def task(reads, writes=(), *, effects='none', sandbox='read-only', **extra):
    return dict(cwd='/fictional699/work', effects=effects, sandbox=sandbox,
                effect_authority=dict(read_roots=list(reads), write_roots=list(writes),
                                      operations=['read-source']), **extra)


class ResourceRoot699(unittest.TestCase):
    def setUp(self):
        self.home = patch.object(Path, 'home', return_value=Path('/fictional-home699'))
        self.home.start()
        self.addCleanup(self.home.stop)

    def test_double_root_operand_before_metadata(self):
        for value in ('//fictional699/held/tree', '//fictional699/free', '//'):
            for metadata in (True, False):
                with self.subTest(value=value, metadata=metadata), no_metadata() as calls:
                    with self.assertRaises(Refusal):
                        scopes.root(value, ['/fictional699/held'], metadata=metadata)
                    self.assertEqual(calls, [])

    def test_double_root_exclusion_before_metadata(self):
        for exclusions in (['//fictional699/held'],
                           ['/fictional699/other', '//fictional699/held'],
                           ['//fictional699/held', '/fictional699/other']):
            for metadata in (True, False):
                with self.subTest(exclusions=exclusions, metadata=metadata), no_metadata() as calls:
                    with self.assertRaises(Refusal):
                        scopes.root('/fictional699/free', exclusions, metadata=metadata)
                    self.assertEqual(calls, [])

    def test_canonical_exclusion_equal_descendant_and_ancestor(self):
        for value in ('/fictional699/held', '/fictional699/held/tree', '/fictional699', '/'):
            with self.subTest(value=value), no_metadata() as calls:
                with self.assertRaisesRegex(Refusal, 'excluded store before metadata'):
                    scopes.root(value, ['/fictional699/held'])
                self.assertEqual(calls, [])

    def test_canonical_siblings_accepted_lexically(self):
        with no_metadata() as calls:
            for value in ('/fictional699/held-other', '/fictional699/free'):
                self.assertEqual(scopes.root(value, ['/fictional699/held'], metadata=False), Path(value))
            self.assertEqual(calls, [])

    def test_relative_parent_and_invalid_text_refuse_lexically(self):
        for value in ('relative', '../relative', '/fictional699/../free', '', None, 4):
            with self.subTest(value=value), no_metadata() as calls:
                with self.assertRaises(Refusal):
                    scopes.root(value)
                self.assertEqual(calls, [])

    def test_fictional_profiles_refuse_lexically(self):
        for profile in contracts.PROFILES:
            with self.subTest(profile=profile), no_metadata() as calls:
                with self.assertRaises(Refusal):
                    scopes.root('/fictional-home699/' + profile + '/child')
                self.assertEqual(calls, [])

    def test_metadata_sentinel_positive_control(self):
        with no_metadata() as calls:
            with self.assertRaises(MetadataReached):
                scopes.root('/fictional699/free', ['/fictional699/held'])
            self.assertEqual(len(calls), 1)

    def test_created_fixture_acceptance_and_symlink_refusal(self):
        # Preserve the exact created tree. Real metadata is confined to its
        # explicit members; ancestor checks are mocked, never probed.
        fixture = Path(tempfile.mkdtemp(prefix='root699-',
                                      dir=os.environ.get('RESOURCE_ROOT699_FIXTURES')))
        plain, link = fixture/'plain', fixture/'link'
        plain.mkdir()
        link.symlink_to(plain, target_is_directory=True)
        original = Path.is_symlink
        calls = []
        def owned_only(path):
            calls.append(path)
            return original(path) if path in {fixture, plain, link} else False
        with patch.object(Path, 'is_symlink', owned_only):
            self.assertEqual(scopes.root(str(plain)), plain)
            with self.assertRaisesRegex(Refusal, 'no symlink inference'):
                scopes.root(str(link))
        self.assertIn(plain, calls)
        self.assertIn(link, calls)

    def test_access_modes_whole_map_preflight(self):
        for bad in ('//fictional699/held/tree', '/fictional699/held/tree',
                    'relative', '/fictional699/../free'):
            for slot in ('read', 'write', 'cwd'):
                selected = task(['/fictional699/free'], ['/fictional699/write'],
                                effects='owner-reconcile', sandbox='workspace-write')
                if slot == 'cwd':
                    selected['cwd'] = bad
                else:
                    selected['effect_authority'][slot + '_roots'].append(bad)
                with self.subTest(bad=bad, slot=slot), no_metadata() as calls:
                    with self.assertRaises(Refusal):
                        scopes.access_modes(selected, ['/fictional699/held'])
                    self.assertEqual(calls, [])

    def test_access_modes_bad_exclusion_preflight(self):
        with no_metadata() as calls:
            with self.assertRaises(Refusal):
                scopes.access_modes(task(['/fictional699/free']), ['//fictional699/held'])
            self.assertEqual(calls, [])

    def test_access_modes_positive_and_existing_modes(self):
        for selected, expected in (
                (task(['/fictional699/read']), []),
                (task(['/fictional699/read'], effects='owned-artifacts', sandbox='workspace-write'), []),
                (task(['/fictional699/read'], ['/fictional699/write'], effects='owner-reconcile',
                      sandbox='workspace-write'), ['/fictional699/write', '/fictional699/work']),
                (task(['/fictional699/read'], ['/fictional699/write'], effects='owner-reconcile',
                      sandbox='workspace-write', routine_completion={'targets': ['/fictional699/write/out']}),
                 ['/fictional699/write'])):
            with self.subTest(effects=selected['effects'], expected=expected):
                with patch.object(Path, 'is_symlink', return_value=False) as metadata:
                    reads, writes = scopes.access_modes(selected, ['/fictional699/held'])
                self.assertEqual(reads, [Path('/fictional699/read'), Path('/fictional699/work')])
                self.assertEqual(writes, list(map(Path, expected)))
                self.assertTrue(metadata.called)

    def test_legacy_validation_keeps_canonical_and_refuses_double_root(self):
        runtime = types.SimpleNamespace(config={'roles': {'Work': {}},
                                                'artifact_exclusions': ['/fictional699/held']},
                                        one=lambda *args: {'legacy_hold': 'fictional-hold'})
        record = dict(original_hold='fictional-hold', roots=['/fictional699/free'],
                      unbounded=False, evidence='fictional attributed scope')
        with patch.object(Path, 'is_symlink', return_value=False) as metadata:
            scopes.validate(runtime, {'Work': record})
            self.assertTrue(metadata.called)
        for bad in ('//fictional699/held/tree', '/fictional699/held/tree', 'relative'):
            with self.subTest(bad=bad), no_metadata() as calls:
                with self.assertRaises(Refusal):
                    scopes.validate(runtime, {'Work': dict(record, roots=[bad])})
                self.assertEqual(calls, [])

    def test_release_guard_agrees_on_double_anchors(self):
        with no_metadata() as calls:
            with self.assertRaises(Refusal):
                configuration._path('//fictional699/free', ['/fictional699/held'])
            with self.assertRaises(Refusal):
                configuration._path('/fictional699/free', ['//fictional699/held'])
            self.assertEqual(calls, [])

    def test_caller_exclusion_entry_contract(self):
        # Exercise the real validate_config exclusion check. Unrelated policy
        # modules and role validation are stubs; this is not full config QA.
        config = dict(version=1, actor='00000000-0000-4000-8000-000000000699',
                      roles={'Work': {'routes': []}}, state_dir='/fictional699/state',
                      profiles=['.codex5'], tasks={},
                      limits=dict.fromkeys(('max_events', 'max_attempts', 'max_jobs',
                                            'max_bytes', 'max_alerts', 'max_result_bytes'), 1),
                      deadlines=dict.fromkeys(('classify', 'task', 'ack', 'backlog', 'bind',
                                               'interrupt', 'shutdown', 'alert_interval'), 1))
        for kind in ('classifier', 'diagnosis'):
            config[kind] = dict(binding=contracts.LUNA, profile='.codex5', cwd='/fictional699/work')
        modules = {}
        for name in ('admitted', 'windows', 'custodian_service', 'local_integration'):
            module = types.ModuleType('coordinator_runtime.' + name)
            module.policy = lambda config: None
            modules[module.__name__] = module
        with patch.dict('sys.modules', modules), patch.object(contracts, 'validate_role'), no_metadata() as calls:
            for entries in ([], ['/fictional699/held'], ['//fictional699/held']):
                selected = dict(copy.deepcopy(config), artifact_exclusions=entries)
                self.assertIs(contracts.validate_config(selected), selected)
            for entries in ('/fictional699/held', [None], [42], ['relative'],
                            [''], ['/fictional699/../held'], ['/fictional699/held'] * 65):
                with self.subTest(entries=entries), self.assertRaisesRegex(Refusal, 'opaque artifact exclusions'):
                    contracts.validate_config(dict(copy.deepcopy(config), artifact_exclusions=entries))
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
