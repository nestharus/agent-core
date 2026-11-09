"""Exact-method offline qualification; used inside the caller's empty sandbox.

Only /fixtures (new originals) and /record (this encounter) are writable. No test
discovery, fixture deletion, provider, profile or old-state acquisition occurs.
Normal close callbacks run after pre-close byte conservation. Readback opens only
separate copies. This producer evidence is not independent review or acceptance.
"""
import collections
import json
import os
from pathlib import Path
import sqlite3
import sys
import traceback
import unittest

sys.path.insert(0, str(Path(__file__).parent / 'tests'))
from fixture_conservation import capacity, conserve, readback, verify, write, directory


class Recorder(unittest.TestResult):
    def __init__(self, output, fixture_root=Path('/fixtures')):
        super().__init__()
        self.output = output
        self.fixture_root = fixture_root
        self.snapshot_attempts = 0
        self.snapshotting = False
        self.conservation_pending = False
        capacity(output)
        self.stream = (output / 'events.jsonl').open('x')
        self.current = None
        self.all_records = []
        self.physical = []
        self.snapshotted = False
        self.connections = []
        self.original_connect = sqlite3.connect

    def event(self, kind, **fields):
        capacity(self.output)
        self.stream.write(json.dumps(dict(kind=kind, **fields), sort_keys=True) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def startTest(self, test):
        if self.conservation_pending:
            raise RuntimeError('previous required fixture conservation remains pending')
        super().startTest(test)
        self.current = dict(id=test.id(), outcome='UNFINISHED', assertions=[], lines={}, body_entered=False,
                            subtests=[], conservation=[])
        self.names_before = set(self.fixture_root.iterdir())
        self.snapshotted = False
        self.snapshot_attempts = 0
        self.snapshotting = False
        self.conservation_pending = False
        self.connections = []
        self.event('start', id=test.id())

    def trace(self, frame, event, arg):
        if self.current is None:
            return self.trace
        path = frame.f_code.co_filename
        tests = '/src/tools/coordinator-runtime/tests/'
        if event == 'line' and path.startswith(tests):
            self.current['lines'].setdefault(path[len(tests):], set()).add(frame.f_lineno)
        if event == 'call' and path.startswith(tests) and frame.f_code.co_name == self.current['id'].split('.')[-1]:
            self.current['body_entered'] = True
        if event == 'call' and frame.f_code.co_name.startswith('assert'):
            caller = frame.f_back
            if caller and caller.f_code.co_filename.startswith(tests):
                self.current['assertions'].append(dict(method=frame.f_code.co_name,
                    file=caller.f_code.co_filename[len(tests):], line=caller.f_lineno))
        return self.trace

    def snapshot(self, test):
        if self.snapshotting:
            return
        self.snapshotting = True
        try:
            self._snapshot(test)
        finally:
            self.snapshotting = False

    def _snapshot(self, test):
        if self.current is None or self.snapshotted:
            return
        self.conservation_pending = True
        self.snapshot_attempts += 1
        area = self.output / ('case-' + str(self.testsRun) + '-attempt-' + str(self.snapshot_attempts))
        directory(area)
        # Each name was created by this synchronous case in an empty owned root.
        created = sorted(set(self.fixture_root.iterdir()) - self.names_before)
        for index, root in enumerate(created):
            if root.is_file():
                # Fixed witnesses outside the per-fixture directories also stay.
                target = area / ('witness-' + str(index))
                write(target, root.read_bytes())
                self.current['conservation'].append(dict(original=str(root), witness=str(target)))
                continue
            record = conserve(root, area / ('snapshot-' + str(index)))
            self.physical.append(record)
            self.current['conservation'].append(record)
        # Preserve a logical image of the explicitly fictional in-memory Board.
        memory = []
        for value in self.connections:
            try:
                databases = value.execute('PRAGMA database_list').fetchall()
                if not any(row[2] == '' for row in databases):
                    continue
                image = value.serialize()
            except (sqlite3.OperationalError, sqlite3.ProgrammingError):
                continue  # Empty database or connection already closed by case.
            target = area / ('memory-' + str(len(memory)) + '.sqlite')
            write(target, image)
            memory.append(dict(path=str(target), bytes=len(image), meaning='logical image, not original physical file'))
        self.current['memory'] = memory
        self.event('conserved-before-close', id=self.current['id'], originals=[str(p) for p in created])
        self.snapshotted = True
        self.conservation_pending = False

    def connect(self, *args, **kwargs):
        self_recorder = self
        factory = kwargs.get('factory', sqlite3.Connection)
        class GuardedConnection(factory):
            def close(self):
                self_recorder.before_close()
                return super().close()

            def execute(self, *args, **kwargs):
                self_recorder.before_close()
                return super().execute(*args, **kwargs)

            def executemany(self, *args, **kwargs):
                self_recorder.before_close()
                return super().executemany(*args, **kwargs)

            def executescript(self, *args, **kwargs):
                self_recorder.before_close()
                return super().executescript(*args, **kwargs)

            def commit(self):
                self_recorder.before_close()
                return super().commit()

            def rollback(self):
                self_recorder.before_close()
                return super().rollback()

            def __exit__(self, *args):
                self_recorder.before_close()
                return super().__exit__(*args)
        kwargs['factory'] = GuardedConnection
        connection = self.original_connect(*args, **kwargs)
        if self.current is not None:
            self.connections.append(connection)
        return connection

    def before_close(self):
        # Ordinary close cannot consume an oracle whose copy failed. Keep the
        # same live connections and retry into a new retained attempt directory.
        if self.conservation_pending and not self.snapshotting:
            self.snapshot(None)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.current['outcome'] = 'PASS'

    def adverse(self, test, error, outcome):
        self.current['outcome'] = outcome
        trace = ''.join(traceback.format_exception(*error))
        self.current.setdefault('traces', []).append(trace)
        self.event(outcome.lower(), id=test.id(), trace=trace)
        self.snapshot(test)  # Before fallible close/teardown tails.

    def addError(self, test, error):
        super().addError(test, error)
        self.adverse(test, error, 'ERROR')

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.adverse(test, error, 'FAIL')

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        self.current['subtests'].append(dict(case=str(subtest), success=error is None))
        if error:
            self.adverse(test, error, 'FAIL' if issubclass(error[0], test.failureException) else 'ERROR')

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.current['outcome'] = 'SKIP'

    def stopTest(self, test):
        super().stopTest(test)
        self.snapshot(test)  # Never hand back a successful case with pending bytes.
        completed = {**self.current, 'lines': {k: sorted(v) for k, v in self.current['lines'].items()}}
        write(self.output / ('case-' + str(self.testsRun) + '.json'),
              json.dumps(completed, indent=2, sort_keys=True).encode())
        self.event('stop', id=test.id(), outcome=self.current['outcome'], body_entered=self.current['body_entered'])
        self.all_records.append(completed)
        self.current = None


def main():
    output = Path('/record')
    ids = json.loads(Path('/selection.json').read_text())
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('nonempty exact distinct selection required')
    capacity(output)
    recorder = Recorder(output)
    recorder.event('scope', ids=ids, meaning='focused producer qualification, not whole qualification/acceptance')
    old_cleanups = unittest.TestCase.doCleanups
    old_teardown = unittest.TestCase._callTearDown
    old_connect = sqlite3.connect
    def cleanups(test):
        recorder.snapshot(test)
        return old_cleanups(test)
    def teardown(test):
        recorder.snapshot(test)
        return old_teardown(test)
    unittest.TestCase.doCleanups = cleanups
    unittest.TestCase._callTearDown = teardown
    sqlite3.connect = recorder.connect
    sys.settrace(recorder.trace)
    try:
        for identity in ids:
            capacity(output)
            suite = unittest.defaultTestLoader.loadTestsFromName(identity)
            if suite.countTestCases() != 1:
                raise ValueError('exact single method required: ' + identity)
            suite.run(recorder)
    finally:
        sys.settrace(None)
        unittest.TestCase.doCleanups = old_cleanups
        unittest.TestCase._callTearDown = old_teardown
        sqlite3.connect = old_connect
    readbacks = []
    for index, record in enumerate(recorder.physical):
        # Physical states are never opened by SQLite, even mode=ro.
        result = readback(record, output / ('readback-' + str(index)))
        readbacks.append(result)
    conserved = sum(verify(record) for record in recorder.physical)
    outcomes = collections.Counter(case['outcome'] for case in recorder.all_records)
    finish = dict(selected=len(ids), started=recorder.testsRun, stopped=len(recorder.all_records),
                  outcomes=dict(outcomes), conserved_files=conserved, physical_snapshots=len(recorder.physical))
    write(output / 'result.json', json.dumps(dict(cases=recorder.all_records, finish=finish, readbacks=readbacks),
                                            indent=2, sort_keys=True).encode())
    recorder.event('finish', **finish)
    recorder.stream.close()
    return 0 if outcomes == {'PASS': len(ids)} else 1


if __name__ == '__main__':
    raise SystemExit(main())
