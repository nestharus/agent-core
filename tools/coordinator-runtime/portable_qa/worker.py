"""Standard unittest worker; only the declared exported candidate is importable."""
import errno
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from common import require, sha


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    m = json.loads(Path('/procedure/manifest.json').read_text())
    c = Path(m['candidate'])
    require(Path.cwd() == c and not (c/'.git').exists(), 'wrong source CWD/noGit condition')
    probe = c/next(iter(m['candidate_files']))
    try:
        fd = os.open(probe, os.O_WRONLY)
    except OSError as exc:
        require(exc.errno == errno.EROFS, 'candidate must be mounted read-only')
    else:
        os.close(fd)
        raise ValueError('candidate is writable')
    events = Path('/fixtures/events.jsonl').open('x')
    def emit(kind, **values):
        events.write(json.dumps({'kind': kind, **values}, sort_keys=True)+'\n')
        events.flush()
    import support
    from coordinator_runtime.retention_dependency import source_pins
    def fixture_publication():
        return {'method': 'retention-same-inode-v1', 'library': '/sdk', 'source_pins': source_pins('/sdk', [])}
    with patch.object(support, 'fixture_publication', fixture_publication):
        tests = list(flatten(unittest.defaultTestLoader.loadTestsFromNames(m['selectors'])))
        unique = {t.id(): t for t in tests}
        require(set(unique) == set(m['expected_ids']), 'missing/extra/wrong declared tests')
        require(not unittest.defaultTestLoader.errors, 'test loading failed')
        emit('scope', ids=sorted(unique), read_only=True, seams=m['seams'])
        class Result(unittest.TextTestResult):
            def startTest(self, test):
                emit('start', id=test.id())
                super().startTest(test)
            def addSuccess(self, test):
                emit('success', id=test.id())
                super().addSuccess(test)
            def addSkip(self, test, reason):
                emit('skip', id=test.id(), reason=reason)
                super().addSkip(test, reason)
                self.stop()
        result = unittest.TextTestRunner(verbosity=2, resultclass=Result, failfast=True).run(
            unittest.TestSuite(unique[k] for k in sorted(unique)))
        modules = {}
        for name, module in list(sys.modules.items()):
            loc = getattr(module, '__file__', None)
            if not loc:
                continue
            p = Path(loc)
            if p.is_relative_to(c):
                rel = str(p.relative_to(c))
                require(rel in m['candidate_files'], 'unlisted candidate module loaded')
                require(sha(p.read_bytes()) == m['candidate_files'][rel]['sha256'], 'loaded source changed')
                modules[name] = rel
            elif name.startswith('coordinator_runtime') or name.startswith('test_') or name == 'support':
                raise ValueError('wrong candidate module origin')
        emit('finish', tests=result.testsRun, modules=modules)
        events.close()
        raise SystemExit(0 if result.wasSuccessful() and not result.skipped and not result.expectedFailures
                         and not result.unexpectedSuccesses else 1)


if __name__ == '__main__':
    main()
