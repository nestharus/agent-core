"""Owned path fixtures exercise the real validator without acquiring exclusions."""
import copy
from contextlib import ExitStack
import errno
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime.configuration import apply_scope_options
from coordinator_runtime.contracts import Refusal, validate_config
from coordinator_runtime.custody import refuse_excluded
from support import config_at


class ExclusionCapacity(unittest.TestCase):
    def setUp(self):
        # Deliberately retain owned fixtures, including failed attempts.
        self.home = Path(tempfile.mkdtemp(prefix='capacity783-'))
        self.config = config_at(self.home)
        self.paths = []
        for i in range(66):
            path = self.home / f'held-{i:04d}.capture'
            path.write_text('owned synthetic hold\n')
            self.paths.append(str(path))

    def test_64_plus_two_retains_exact_history_and_refuses_acquisition(self):
        original = copy.deepcopy(self.config)
        original['artifact_exclusions'] = self.paths[:64]
        value = copy.deepcopy(original)
        with ExitStack() as stack:
            for name in ('stat', 'lstat', 'open', 'read_text', 'read_bytes', 'resolve'):
                previous = getattr(Path, name)
                def guarded(path, *args, _previous=previous, **kwargs):
                    if str(path) in self.paths:
                        raise AssertionError('opaque exclusion acquisition attempted')
                    return _previous(path, *args, **kwargs)
                stack.enter_context(patch.object(Path, name, guarded))
            apply_scope_options(original, value, {'exclusions': self.paths[64:]})
            self.assertIs(validate_config(value), value)
            self.assertEqual(value['artifact_exclusions'], self.paths)
            for path in self.paths:
                with self.assertRaisesRegex(Refusal, 'excluded before acquisition'):
                    refuse_excluded(SimpleNamespace(config=value), path)
        self.assertEqual(original['artifact_exclusions'], self.paths[:64])
        unchanged = copy.deepcopy(value)
        self.assertEqual(unchanged.pop('prospective_scope_selection'),
                         {'exclusions': self.paths[64:]})
        unchanged['artifact_exclusions'] = self.paths[:64]
        self.assertEqual(unchanged, original)

    def test_4096_passes_and_4097_refuses(self):
        self.config['artifact_exclusions'] = [str(self.home / f'opaque-{i}') for i in range(4096)]
        self.assertIs(validate_config(self.config), self.config)
        self.config['artifact_exclusions'].append(str(self.home / 'one-too-many'))
        with self.assertRaisesRegex(Refusal, 'bounded absolute opaque artifact exclusions'):
            validate_config(self.config)

    def test_bad_path_and_type_still_refuse(self):
        for bad in ('relative', str(self.home) + '/../escape', 7, None, {}):
            with self.subTest(bad=bad):
                self.config['artifact_exclusions'] = self.paths + [bad]
                with self.assertRaisesRegex(Refusal, 'bounded absolute opaque artifact exclusions'):
                    validate_config(self.config)
        for bad in (None, {}, tuple(self.paths), 'absolute-list-required'):
            with self.subTest(container=type(bad).__name__):
                self.config['artifact_exclusions'] = bad
                with self.assertRaises(Refusal):
                    validate_config(self.config)

    def test_scope_option_bad_path_and_type_still_refuse(self):
        for bad in ({'exclusions': 'bad'}, {'exclusions': [7]},
                    {'exclusions': ['relative']}, {'exclusions': [str(self.home) + '/../escape']}):
            with self.subTest(options=bad), self.assertRaises(Refusal):
                apply_scope_options(self.config, copy.deepcopy(self.config), bad)

    def test_fixture_writable_source_readonly_and_network_isolated(self):
        own = self.home / 'writable-witness'
        own.write_text('owned')
        self.assertEqual(own.read_text(), 'owned')
        with self.assertRaises(OSError) as denied:
            Path(__file__).open('ab')
        self.assertEqual(denied.exception.errno, errno.EROFS)
        with socket.socket() as connection:
            with self.assertRaises(OSError) as denied:
                connection.connect(('192.0.2.1', 9))
            self.assertEqual(denied.exception.errno, errno.ENETUNREACH)


if __name__ == '__main__':
    unittest.main(verbosity=2)
