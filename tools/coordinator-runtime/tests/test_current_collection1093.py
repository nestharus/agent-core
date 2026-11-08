"""Decision1093: original collection, recurring progress and honest witnesses.

Synthetic direct OS children only. Every injected failure retains its original
handle in this test's cleanup; baseline lost responsibility is never adopted.
"""
from contextlib import nullcontext
from functools import partial
import asyncio
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'current_qa'))
import procedure
import test_windows76 as windows_fixture


class WaitRecorder:
    def __init__(self, proc, calls):
        self.proc, self.calls, self.wait = proc, calls, proc.wait

    def __call__(self, *args, **kwargs):
        value = self.wait(*args, **kwargs)
        self.calls.append(dict(pid=self.proc.pid, END=value))
        return value


class BrokenClose:
    def __init__(self, selector):
        self.inner = selector()

    def __enter__(self):
        return self.inner

    def __exit__(self, *args):
        self.inner.close()
        raise OSError('owned selector close fault')


class FictionalBoard:
    def verify_authority(self, runtime):
        pass  # Fictional grant only; never genuine authority.


class SetupCollection1093(unittest.TestCase):
    def setUp(self):
        self.area = Path('/fixtures')/self.id()
        self.area.mkdir()
        self.originals = []
        self.calls = []
        self.real_popen = subprocess.Popen
        self.real_selector = procedure.selectors.DefaultSelector
        self.real_open = Path.open
        self.addCleanup(self.collect_originals)

    def launch(self, *args, **kwargs):
        proc = self.real_popen(*args, **kwargs)
        self.originals.append(proc)
        proc.wait = WaitRecorder(proc, self.calls)
        return proc

    def collect_originals(self):
        # A failing baseline assertion still collects the same directly owned
        # originals before this test returns. No PID lookup, polling or adoption.
        for proc in self.originals:
            self.collect_original(proc)
        (self.area/'original-ENDs.json').write_text(json.dumps(self.calls))

    def collect_original(self, proc):
        if proc.returncode is None:
            proc.kill()
            proc.wait(timeout=5)
        if proc.stdout is not None:
            proc.stdout.close()

    def invoke(self, code, context=nullcontext(), maximum=4096, seconds=.25):
        script = self.area/'child.py'
        script.write_text(code)
        out = self.area/'capture'
        out.mkdir()
        with patch.object(procedure.subprocess, 'Popen', side_effect=self.launch), context:
            record = procedure.collect([sys.executable, '-B', str(script)], out, seconds, maximum)
        (self.area/'collection.json').write_text(json.dumps(record))
        return record

    def failed_collection(self, context):
        record = self.invoke('import time\ntime.sleep(30)\n', context)
        self.assertEqual(len(self.originals), 1)
        self.assertIsNotNone(self.originals[0].returncode, 'collector returned before original wait')
        self.assertEqual(record['exit'], self.originals[0].returncode)
        self.assertFalse(record['complete'])
        self.assertTrue(record['reason'])
        self.assertTrue(any(row['stage'] == 'capture' for row in record.get('failures', [])))
        self.assertLess(record['seconds'], 9)
        self.assertTrue(self.calls, 'original numeric END never collected')

    def test_selector_constructor_failure_collects_original(self):
        self.failed_collection(patch.object(procedure.selectors, 'DefaultSelector', side_effect=OSError('owned selector fault')))

    def registration_fault(self):
        selector = self.real_selector()
        selector.register = lambda *a, **k: (_ for _ in ()).throw(OSError('owned register fault'))
        return selector

    def test_selector_registration_failure_collects_original(self):
        self.failed_collection(patch.object(procedure.selectors, 'DefaultSelector', side_effect=self.registration_fault))

    def open_fault(self, path, *args, **kwargs):
        if path.name == 'transcript.txt':
            raise OSError('owned transcript allocation fault')
        return self.real_open(path, *args, **kwargs)

    def test_transcript_creation_failure_collects_original(self):
        self.failed_collection(patch.object(Path, 'open', lambda path, *a, **k: self.open_fault(path, *a, **k)))

    def test_capture_drain_failure_collects_original(self):
        self.failed_collection(patch.object(procedure, 'next_body', side_effect=OSError('owned drain fault')))

    def test_resource_close_failure_collects_original(self):
        self.failed_collection(patch.object(procedure.selectors, 'DefaultSelector',
                                            partial(BrokenClose, self.real_selector)))

    def test_nonzero_END_keeps_complete_output_and_fails_execution(self):
        record = self.invoke('print("retained failure")\nraise SystemExit(7)\n')
        self.assertEqual(record['exit'], 7)
        self.assertTrue(record['complete'])
        self.assertEqual((self.area/'capture/transcript.txt').read_bytes(), b'retained failure\n')

    def test_output_EOF_does_not_replace_original_END(self):
        record = self.invoke('import os,time\nos.close(1)\nos.close(2)\ntime.sleep(30)\n')
        self.assertIsInstance(record['exit'], int)
        self.assertFalse(record['complete'])
        self.assertIn('deadline after EOF', record['reason'])
        self.assertLess(record['seconds'], 9)

    def test_overflow_collects_original_and_retains_failed_prefix(self):
        record = self.invoke('print("x"*8192)\n', maximum=32)
        self.assertIsInstance(record['exit'], int)
        self.assertFalse(record['complete'])
        self.assertIn('overflow', record['reason'])
        self.assertEqual(len((self.area/'capture/transcript.txt').read_bytes()), 32)

    def test_TERM_ignored_still_collects_original_KILL(self):
        code = 'import signal,time\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nprint("ready",flush=True)\ntime.sleep(30)\n'
        record = self.invoke(code, seconds=.5)
        self.assertEqual(record['exit'], -9)
        self.assertFalse(record['complete'])
        self.assertLess(record['seconds'], 9)

    def test_launch_failure_is_accounted_without_invented_original(self):
        out = self.area/'no-launch'
        out.mkdir()
        record = procedure.collect(['/nonexistent/owned1093-command'], out, .25, 4096)
        self.assertFalse(record['launched'])
        self.assertIsNone(record['pid'])
        self.assertIsNone(record['exit'])
        self.assertFalse(record['complete'])
        self.assertIn('launch failure', record['reason'])


class Fairness1093(windows_fixture.Controls):
    """Independent oracle is traversal, never a fixed two-visit stride.

    Frozen finite backlog; eligible Work worker returns promptly; each awaited
    visit frees the lane. No arrival-rate or permanent-busy service SLO claimed.
    """
    def test_continuously_eligible_finite_backlog_progresses_past_page(self):
        self.worker()
        store = self.store()
        self.alerts(store, 20)
        original = store.rows('SELECT * FROM alerts ORDER BY rowid')
        asyncio.run(self.visits(store))
        actual = store.rows('SELECT * FROM custodian_visits ORDER BY rowid')
        Path('/fixtures/fairness1093-ENDs.json').write_text(json.dumps(actual))
        self.assertEqual(len(actual), 20)
        self.assertEqual({row['occurrence'] for row in actual}, {row['id'] for row in original})
        self.assertEqual(len({row['occurrence'] for row in actual}), 20)
        self.assertTrue(all(row['pid'] and row['numeric_end'] == 0 and row['state'] == 'held' for row in actual))
        self.assertEqual(store.rows('SELECT * FROM alerts ORDER BY rowid'), original)

    async def visits(self, store):
        dispatcher = windows_fixture.Dispatcher(store, models=object(), boards={'Work': FictionalBoard()})
        for _ in range(20):
            dispatcher.custodian_progress()
            await dispatcher.custodian_service.close()


class Witness1098(unittest.TestCase):
    def setUp(self):
        self.area = Path('/fixtures')/self.id()
        home = self.area/'current-oracle'
        (home/'state').mkdir(parents=True)
        (home/'original.txt').write_bytes(b'current original retained\n')
        self.database = home/'state/runtime.sqlite3'
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE events(role,state,ack,processed_at)')
            db.execute("INSERT INTO events VALUES('Work','received','pending',NULL)")

    def test_dedicated_complete_witness_keeps_processing_unaccepted(self):
        result = procedure.observe_witness(self.area)
        self.assertTrue(result['verified'])
        self.assertFalse(result['actual_acceptance'])
        self.assertFalse(result['processing_completion'])

    def test_changed_retained_row_remains_unresolved(self):
        with sqlite3.connect(self.database) as db:
            db.execute("UPDATE events SET ack='changed'")
        self.assertFalse(procedure.observe_witness(self.area)['verified'])

    def test_nonempty_sidecar_refuses_before_immutable_query(self):
        sidecar = Path(str(self.database)+'-wal')
        sidecar.write_bytes(b'owned unresolved fixture WAL')
        with patch.object(procedure.sqlite3, 'connect', side_effect=AssertionError('unsafe immutable read')):
            result = procedure.observe_witness(self.area)
        self.assertFalse(result['verified'])
        self.assertEqual(sidecar.read_bytes(), b'owned unresolved fixture WAL')


def load_tests(loader, tests, pattern):
    classes = (SetupCollection1093, Fairness1093, Witness1098)
    return unittest.TestSuite(cls(name) for cls in classes for name in cls.__dict__ if name.startswith('test_'))
