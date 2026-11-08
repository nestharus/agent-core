"""Execute fixed independently selected current controls in a positive sandbox."""
import errno
from functools import partial
import importlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from procedure import require, sha, SELECTORS


def emit(stream, kind, **values):
    stream.write(json.dumps(dict(kind=kind, **values), sort_keys=True)+'\n')
    stream.flush()


class Result(unittest.TextTestResult):
    def __init__(self, *args, events, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = events

    def startTest(self, test):
        emit(self.events, 'start', id=test.id())
        super().startTest(test)

    def addSuccess(self, test):
        emit(self.events, 'success', id=test.id())
        super().addSuccess(test)

    def addFailure(self, test, err):
        emit(self.events, 'failure', id=test.id())
        super().addFailure(test, err)

    def addError(self, test, err):
        emit(self.events, 'error', id=test.id())
        super().addError(test, err)

    def addSkip(self, test, reason):
        emit(self.events, 'skip', id=test.id(), reason=reason)
        super().addSkip(test, reason)


def fixture_publication():
    from coordinator_runtime.retention_dependency import source_pins
    return dict(method='retention-same-inode-v1', library='/sdk', source_pins=source_pins('/sdk', []))


def flatten(suite):
    for item in suite:
        yield from flatten(item) if isinstance(item, unittest.TestSuite) else [item]


def readonly(candidate, files):
    require(Path.cwd() == candidate and not (candidate/'.git').exists(), 'wrong candidate CWD/noGit')
    try:
        fd = os.open(candidate/next(iter(files)), os.O_WRONLY)
    except OSError as exc:
        require(exc.errno == errno.EROFS, 'candidate must be actually read-only')
        return
    os.close(fd)
    raise ValueError('writable candidate')


def origins(m):
    c = Path(m['candidate'])
    modules = {}
    for name, module in list(sys.modules.items()):
        p = getattr(module, '__file__', None)
        if p and Path(p).is_relative_to(c):
            rel = str(Path(p).relative_to(c))
            require(rel in m['files'] and sha(Path(p).read_bytes()) == m['files'][rel]['sha256'], 'unlisted/changed import')
            modules[name] = rel
    return modules


def main():
    m = json.loads(Path('/procedure/manifest.json').read_text())
    readonly(Path(m['candidate']), m['files'])
    import support
    with patch.object(support, 'fixture_publication', fixture_publication):
        run(m)


def run(m):
    suite = unittest.defaultTestLoader.loadTestsFromNames(SELECTORS)
    require(not unittest.defaultTestLoader.errors, 'selected current tests failed to load')
    tests = {test.id(): test for test in flatten(suite)}
    for rel in m['runtime_modules']:
        importlib.import_module('coordinator_runtime.'+Path(rel).stem)
    events = Path('/fixtures/events.jsonl').open('x')
    emit(events, 'scope', ids=sorted(tests), selectors=SELECTORS, seams=m['seams'])
    result = unittest.TextTestRunner(verbosity=2, resultclass=partial(Result, events=events)).run(
        unittest.TestSuite(tests[k] for k in sorted(tests)))
    loaded = origins(m)
    emit(events, 'finish', tests=result.testsRun, modules=loaded,
         runtime_modules=sorted({p for p in loaded.values() if p in m['runtime_modules']}))
    events.close()
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped and not result.expectedFailures
                     and not result.unexpectedSuccesses else 1)


if __name__ == '__main__':
    main()
