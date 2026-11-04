"""Pool/receiving composition and actual inspection, with owned offline fixtures."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import config_at
from coordinator_runtime import cli
from coordinator_runtime.contracts import encode
from coordinator_runtime.execution_pool import _module as public_pool
import test_receiving_integration as receiving

PARENT = Path(__file__).resolve().parents[2] / 'direct-child'
spec = importlib.util.spec_from_file_location('pool_receiving_parent', PARENT / 'dispatch.py')
parent = importlib.util.module_from_spec(spec)
search_path = sys.path[:]
try:
    spec.loader.exec_module(parent)
finally:
    sys.path[:] = search_path


class Inspection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pool-inspection-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.routes = self.home / 'routes.toml'
        self.state = self.home / 'rotation'
        raw = (PARENT / 'routes.toml').read_text().replace(
            'state_dir = "~/.local/state/direct-child"',
            'state_dir = ' + json.dumps(str(self.state)))
        self.routes.write_text(raw)
        self.pool = public_pool.Pool(self.routes)
        self.assertTrue(self.pool.read()[2].is_relative_to(self.home))
        self.prompt = self.home / 'prompt.txt'
        self.prompt.write_text('Owned dry preview only; no model launch.')

    def preview(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = parent.main(['--config', str(self.routes), '--cwd', str(self.home),
                '--prompt', str(self.prompt), '--runs-dir', str(self.home / 'runs'),
                '--id', 'preview', '--transport', 'direct', '--dry-run'])
        return code, out.getvalue(), err.getvalue()

    def test_parent_singleton_preview_validates_counter_and_never_writes(self):
        self.pool.set(['.codex5'])
        counter = self.pool.read()[2]
        for invalid in ('broken\n', '', '１２\n'):
            counter.write_text(invalid)
            before = {p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
            code, output, error = self.preview()
            self.assertEqual(code, 2, (output, error))
            self.assertNotIn('DRY RUN:', output)
            self.assertEqual({p: p.read_bytes() for p in self.home.rglob('*') if p.is_file()}, before)
        counter.write_text('19\n')
        code, output, _ = self.preview()
        self.assertEqual(code, 0, output)
        self.assertIn('rotation-preview:19 (not reserved)', output)
        self.assertEqual(counter.read_text(), '19\n')
        self.assertFalse((self.home / 'runs').exists())
        counter.write_bytes(b'\xff\n')
        self.assertEqual(self.preview()[0], 2)
        self.assertEqual(counter.read_bytes(), b'\xff\n')

    def test_actual_exec_admission_and_parent_boundary_refuse_without_reallocation(self):
        self.pool.set(['.codex5'])
        marker, receipt = self.home / 'executed', self.home / 'admission.json'
        command = [sys.executable, str(public_pool.__file__), '--routes', str(self.routes),
            'exec', '--profile', '.codex4', '--receipt', str(receipt), '--',
            sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("owned")', str(marker)]
        blocked = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(blocked.returncode, 2, blocked.stdout)
        self.assertEqual(json.loads(receipt.read_text())['state'], 'not-started')
        self.assertFalse(marker.exists())
        record = {'provider': 'codex', 'profile_source': 'rotation:0',
                  'profile': '.codex4', 'config': str(self.routes)}
        class Interrupts:
            received = None
        with patch.object(parent.subprocess, 'Popen', side_effect=AssertionError('disabled caller must not start')):
            code, error = parent.run_foreground(['never-execute'], self.home, Interrupts(), record)
        self.assertIsNone(code)
        self.assertEqual(error, 'PoolError')
        command[command.index('.codex4')] = '.codex5'
        admitted = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(admitted.returncode, 0, admitted.stderr)
        self.assertEqual(json.loads(receipt.read_text())['state'], 'admitted')
        self.assertEqual(marker.read_text(), 'owned')
        self.assertEqual(self.pool.status()['turn'], 0)

    def test_absent_state_preview_creates_nothing_and_defaults_match(self):
        self.assertFalse(self.state.exists())
        self.assertEqual(self.preview()[0], 0)
        self.assertFalse(self.state.exists())
        self.assertEqual(parent.DEFAULT_CONFIG, public_pool.DEFAULT_ROUTES)

    def test_runtime_and_public_CLI_distinguish_held_inspection_from_successful_disable(self):
        config = config_at(self.home)
        config['execution_pool_routes'] = str(self.routes)
        config_path = self.home / 'runtime.json'
        config_path.write_text(encode(config))
        command = [sys.executable, str(public_pool.__file__), '--routes', str(self.routes)]
        disabled = subprocess.run(command + ['set'], capture_output=True, text=True)
        self.assertEqual(disabled.returncode, 0, disabled.stdout)
        status = subprocess.run(command + ['status'], capture_output=True, text=True)
        self.assertEqual(status.returncode, 2, status.stdout)
        self.assertEqual(json.loads(status.stdout)['state'], 'empty')
        for corrupt in (None, 'broken\n', ''):
            if corrupt is not None:
                self.pool.read()[2].write_text(corrupt)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(['--config', str(config_path), 'execution-pool'])
            self.assertEqual(code, 2, out.getvalue())
            self.assertEqual(json.loads(out.getvalue())['state'], 'held')
        self.pool.read()[2].write_text('7\n')
        self.pool.set(['.codex3', '.codex5'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(['--config', str(config_path), 'execution-pool'])
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['turn'], 7)


class PoolReceiving(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_owner_continuity_uses_current_shared_parent_pool_and_preserves_advice(self):
        fixture = receiving.ReceivingIntegration('runTest')
        self.addCleanup(fixture.doCleanups)
        await fixture.asyncSetUp()
        await fixture.restart_with_history()
        request = fixture.queue_owner_cli()
        pool = public_pool.Pool(fixture.config['execution_pool_routes'])
        pool.set(['.codex5'])
        turn = pool.status()['turn']
        chosen, source = parent.allocate_profile({}, 'codex', fixture.config['execution_pool_routes'])
        self.assertEqual((chosen, source), ('.codex5', f'rotation:{turn}'))
        await fixture.tick()
        current = fixture.store.job(fixture.job['id'])
        successor = fixture.store.attempt(current['active_attempt'])
        self.assertEqual(successor['profile'], '.codex5')
        self.assertEqual(json.loads(successor['detail'])['choice'], fixture.choice)
        self.assertEqual(json.loads(successor['detail'])['choice']['profile'], '.codex3')
        self.assertEqual(fixture.request_state(request)['state'], 'consumed')
        self.assertEqual(json.loads(successor['detail'])['execution_pool_allocation']['turn'], turn + 1)
        # This full tick may also classify the retained recovery question. That
        # fresh work takes its own turn rather than being mistaken for replay.
        self.assertGreaterEqual(pool.status()['turn'], turn + 2)
        fixture.assert_originals()
        fixture.runtime.execute.assert_awaited_once()
        fixture.runtime.recover.assert_not_called()


if __name__ == '__main__':
    unittest.main()
