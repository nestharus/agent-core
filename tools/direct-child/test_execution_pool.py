"""Parent-worker pool controls with owned fake accounts/callers only."""

import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import dispatch as dispatcher
from execution_pool import Pool
import test_dispatch as dispatch_fixtures


class ParentPoolControl(unittest.TestCase):
    def setUp(self):
        self.fixture = dispatch_fixtures.DispatchTest('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        # Pool is also used in THIS process, whose HOME is not the fake CLI's.
        routes = Path(self.fixture.config)
        routes.write_text(routes.read_text().replace('state_dir = "~/.local/state/direct-child"',
                          'state_dir = '+json.dumps(str(self.fixture.state_dir))))
        self.pool = Pool(Path(self.fixture.config))
        self.assertTrue(self.pool.read()[2].is_relative_to(self.fixture.home))

    def control(self, *args):
        return subprocess.run([sys.executable, str(Path(__file__).with_name('execution_pool.py')),
                               '--routes', self.fixture.config, *args], env=self.fixture.env,
                              capture_output=True, text=True)

    def test_operator_change_and_profile_advice_control_actual_parent_worker_launches(self):
        self.assertEqual(self.control('set', '.codex3', '.codex5').returncode, 0)
        for seat in ('scout', 'observer'):
            answer = self.fixture.dispatch('--transport', 'direct', '--seat', seat, '--profile-advice', '.codex4')
            self.assertEqual(answer.returncode, 0, answer.stdout + answer.stderr)
        attempts = list(self.fixture.runs.iterdir())
        records = [json.loads((p/'route.json').read_text()) for p in attempts]
        self.assertEqual({r['profile'] for r in records}, {'.codex3', '.codex5'})
        self.assertTrue(all(r['profile_advice'] == '.codex4' for r in records))
        homes = {call['home'] for call in self.fixture.calls_readback() if call['args'][0] == 'exec'}
        self.assertEqual(homes, {str(self.fixture.home/p) for p in ('.codex3', '.codex5')})
        self.assertTrue(all(json.loads((p/'pool-admission.json').read_text())['state'] == 'admitted' for p in attempts))
        # Explicit standalone manual authorization retains its declared meaning.
        self.assertEqual(self.control('set').returncode, 0)
        before = self.pool.status()['turn']
        blocked = self.fixture.dispatch('--transport', 'direct')
        self.assertEqual(blocked.returncode, 2)
        manual = self.fixture.dispatch('--transport', 'direct', '--profile', '.codex', '--override-reason', 'authorized manual fixture')
        self.assertEqual(manual.returncode, 0, manual.stderr)
        self.assertEqual(self.pool.status()['turn'], before)

    def test_disable_after_reservation_in_preflight_prevents_real_exec_for_1_and_4(self):
        cli = self.fixture.bin/'codex'
        text = cli.read_text()
        text = text.replace('args = sys.argv[1:]', '''args = sys.argv[1:]
if args[-2:] == ["features", "list"]:
    import subprocess
    subprocess.run([sys.executable, os.environ["POOL_TOOL"], "--routes", os.environ["POOL_ROUTES"],
                    "set", ".codex5"], check=True, stdout=subprocess.DEVNULL)
''')
        cli.write_text(text)
        env = self.fixture.env | {'POOL_TOOL': str(Path(__file__).with_name('execution_pool.py')),
                                  'POOL_ROUTES': self.fixture.config}
        for profile in ('.codex', '.codex4'):
            self.pool.set([profile])
            answer = self.fixture.dispatch('--transport', 'direct', env=env)
            self.assertEqual(answer.returncode, 2, answer.stdout + answer.stderr)
            self.assertIn('disabled before launch', answer.stdout)
        self.assertFalse(any(call['args'][0] == 'exec' for call in self.fixture.calls_readback()))
        for attempt in self.fixture.runs.iterdir():
            receipt = json.loads((attempt/'pool-admission.json').read_text())
            self.assertEqual(receipt['state'], 'not-started')
            self.assertEqual((attempt/'final.md').read_text(), '')

    def test_invalid_counter_and_missing_control_refuse_without_provider_call_or_reset(self):
        counter = self.pool.read()[2]
        counter.parent.mkdir(parents=True)
        counter.write_text('broken\n')
        answer = self.fixture.dispatch('--transport', 'direct')
        self.assertEqual(answer.returncode, 2)
        self.assertEqual(counter.read_text(), 'broken\n')
        self.assertFalse(self.fixture.calls.exists())
        self.assertEqual(self.control('status').returncode, 2)
        counter.write_text('')
        self.assertEqual(self.control('status').returncode, 2)
        self.assertEqual(counter.read_text(), '')  # Unknown empty state is never reset to zero.
        Path(self.fixture.config).unlink()
        answer = self.fixture.dispatch('--transport', 'direct')
        self.assertEqual(answer.returncode, 2)
        self.assertFalse(self.fixture.calls.exists())

    def test_native_parent_boundary_rechecks_reserved_profile_without_fallback(self):
        reservation = self.pool.allocate()
        self.pool.set(['.codex5'])
        class Interrupts:
            received = None
        record = {'provider': 'codex', 'profile_source': 'rotation:0', 'config': self.fixture.config,
                  'profile': reservation['profile']}
        with patch.object(dispatcher.subprocess, 'Popen', side_effect=AssertionError('no native caller may start')):
            code, error = dispatcher.run_foreground(['never-execute'], self.fixture.cwd, Interrupts(), record)
        self.assertIsNone(code)
        self.assertEqual(error, 'PoolError')
        self.assertEqual(json.loads((self.fixture.cwd/'pool-admission.json').read_text())['state'], 'not-started')
        self.assertEqual(self.pool.status()['turn'], 1)


if __name__ == '__main__':
    unittest.main()
