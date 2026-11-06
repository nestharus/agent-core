"""Owned component QA, never actual admission/selection or semantic acceptance.

Run in a fresh outer bwrap with QA544_EVIDENCE pointing at its sole writable
owned export. That directory supplies def41-source/, def41-manifest.json,
qa-runner.py and qa-resource-oracle.py (unchanged538), and candidate/ containing
exact copies of the two tracked procedure templates. Public runtime imports
must come from the immutable exported source, never the host checkout.
The runner/readback nested namespaces come from actual qa_source.command.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace

from coordinator_runtime import qa_source, ordinary, public_tools
from coordinator_runtime.contracts import Refusal, digest


FICTION = '00000000-0000-4000-8000-000000000544'
REL = 'tools/coordinator-runtime/tests/test_owned544.py'


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def oid(kind, data):
    return hashlib.sha1(kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def fixture_source(root, body):
    """Whole single-file Git-style fiction; not a real commit/authority claim."""
    path = root / REL
    path.parent.mkdir(parents=True)
    path.write_text(body)
    data = path.read_bytes()
    blob = oid('blob', data)
    tree = oid('tree', b'100644 test_owned544.py\0' + bytes.fromhex(blob))
    for name in ('tests', 'coordinator-runtime', 'tools'):
        tree = oid('tree', b'40000 ' + name.encode() + b'\0' + bytes.fromhex(tree))
    files = [{'path': REL, 'mode': '100644', 'blob': blob, 'size': len(data), 'sha256': sha(data)}]
    return {'head': 'b' * 40, 'tree': tree, 'files': files, 'manifest_sha256': sha(encode(files).encode())}


@unittest.skipUnless(os.environ.get('QA544_EVIDENCE'), 'requires explicit owned bwrap export fixture')
class ProcedureCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = Path(os.environ['QA544_EVIDENCE'])
        if not cls.evidence.is_absolute():
            raise ValueError('explicit absolute owned evidence directory required')
        cls.source = cls.evidence / 'def41-source'
        cls.manifest = json.loads((cls.evidence / 'def41-manifest.json').read_text())
        module = Path(qa_source.__file__)
        if not module.is_relative_to(cls.source):
            raise ValueError('runtime must be imported from immutable export inside outer bwrap')
        # A refusal-free inert custody response is an explicit fiction. No Store.
        cls.store = SimpleNamespace(config={'artifact_exclusions': [], 'tasks': {}},
                                    one=lambda *args: None, rows=lambda *args: [])
        cls.records = []

    @classmethod
    def tearDownClass(cls):
        (cls.evidence / 'collection-index.json').write_text(encode(cls.records) + '\n')

    def case(self, name, body=None, ids=None, baseline=False, limits=None):
        root = self.evidence / (os.environ.get('QA544_RUN', 'run') + '-' + name)
        root.mkdir(exist_ok=False)
        (root / 'scripts').mkdir()
        (root / 'output').mkdir()
        if body is None:
            source = copy.deepcopy(self.manifest)
            export = self.source
            tree = ast.parse((export / 'tools/coordinator-runtime/tests/test_coordination366.py').read_text())
            ids = ['test_coordination366.' + c.name + '.' + f.name
                   for c in tree.body if isinstance(c, ast.ClassDef)
                   for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and f.name.startswith('test_')]
            self.assertEqual(len(ids), 17)
            rel = 'tools/coordinator-runtime/tests/test_coordination366.py'
        else:
            export = root / 'source'
            source = fixture_source(export, body)
            ids = ids or ['test_owned544.Subject.test_body']
            rel = REL
        selection = {'schema': 'ordinary-qa-selection538-v1', 'selection_complete': True,
            'selected_by': FICTION, 'selection_authority': 'owned fictional component selector',
            'selection_rationale': 'Maker regression only; outside Work owns actual independent selection',
            'source': source, 'tests': [{'path': rel, 'sha256': next(f['sha256'] for f in source['files'] if f['path'] == rel), 'ids': ids}],
            'output_root': str(root / 'output'),
            'resource_boundary': 'selected-python-no-child-process-no-new-thread-v1',
            'limits': limits or {'capture_bytes': 1048576, 'result_bytes': 4194304}}
        raw = (encode(selection) + '\n').encode()
        (root / 'scripts/TEST-SELECTION.json').write_bytes(raw)
        oldrepo = '/home/nes/projects/ai/worktrees/WORK-48847-runtime-cutover-repair324'
        oldout = '/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/actual-four-role528/qa-execution'
        for name, oldname in [('qa_selected_tests.py', 'qa-runner.py'), ('qa_resource_readback.py', 'qa-resource-oracle.py')]:
            template = self.evidence / oldname if baseline else self.evidence / 'candidate' / name
            text = template.read_text()
            text = text.replace('$input.independently_selected_final_selection_file_sha256', sha(raw))
            text = text.replace('TEST-SELECTION-TEMPLATE.json', 'TEST-SELECTION.json')
            text = text.replace(oldrepo, str(root / 'repository')).replace(oldout, str(root / 'output'))
            text = text.replace('$input.final_repository', str(root / 'repository')).replace('$input.owned_output_root', str(root / 'output'))
            text = text.replace('01a18bac-b565-7742-86bc-0f9ba5ffc831', FICTION)
            (root / 'scripts' / name).write_text(text)
        return SimpleNamespace(root=root, export=export, source=source, ids=ids, selection=selection)

    def collect(self, case, role='runner', label=None):
        name = 'qa_selected_tests.py' if role == 'runner' else 'qa_resource_readback.py'
        script = case.root / 'scripts' / name
        binary = Path('/usr/bin/python3.12')
        pin = {'path': str(binary), 'bytes': binary.stat().st_size, 'sha256': sha(binary.read_bytes())}
        selected = {'argv': [str(binary), '-B', str(script)], 'executable_sha256': pin['sha256'],
                    'script_sha256': sha(script.read_bytes()), 'stdout': None}
        task = {'effect_authority': {'read_roots': [str(case.root / 'scripts')],
                                     'write_roots': [str(case.root / 'output')]}}
        p = {'repository': str(case.root / 'repository'), 'source_capture': {'bwrap': '/usr/bin/bwrap'}}
        public_tools.validate(self.store, {('command' if role == 'runner' else 'readback'): pin})
        ordinary.command_policy(self.store, selected, [str(case.root / 'scripts')], pin)
        command = qa_source.command(self.store, task, p, {'root': str(case.export)}, selected)
        self.assertNotIn('--unshare-pid', command)
        tag = label or role
        # Own original only; bounded files retained before interpreting outcomes.
        stdout = case.root / (tag + '.stdout')
        stderr = case.root / (tag + '.stderr')
        with stdout.open('xb') as out, stderr.open('xb') as err:
            proc = subprocess.Popen(command, stdout=out, stderr=err)
            try:
                end = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                end = proc.wait()
                raise AssertionError('owned original timed out; collection retained')
            finally:
                record = {'case': case.root.name, 'role': role, 'label': tag, 'pid': proc.pid,
                    'END': proc.returncode, 'argv': command, 'stdout': str(stdout), 'stderr': str(stderr),
                    'stdout_bytes': stdout.stat().st_size, 'stderr_bytes': stderr.stat().st_size,
                    'stdout_sha256': sha(stdout.read_bytes()), 'stderr_sha256': sha(stderr.read_bytes()),
                    'capture_complete': proc.returncode is not None}
                self.records.append(record)
                (case.root / (tag + '-collection.json')).write_text(encode(record) + '\n')
        self.assertLess(stdout.stat().st_size + stderr.stat().st_size, 1048576)
        return end

    def report(self, case):
        return json.loads((case.root / 'output/result.json').read_text())

    def complete(self, case, end, statuses, subtests=False):
        self.assertEqual(self.collect(case), end)
        self.assertEqual(self.collect(case, 'readback'), 0)
        report = self.report(case)
        self.assertEqual(report['selected_ids'], case.ids)
        self.assertEqual(report['started'], case.ids)
        self.assertEqual(report['stopped'], case.ids)
        events = report['events']
        if subtests:
            self.assertFalse(any(e['status'] == 'subtest-failed' for e in events))
            events = [e for e in events if not e['status'].startswith('subtest-')]
        self.assertEqual([e['status'] for e in events], statuses)
        self.assertEqual(report['exit'], end)
        self.assertEqual(report['strict_pass'], end == 0)
        self.assertEqual((case.root / 'runner.stdout').read_bytes(), (case.root / 'output/result.json').read_bytes())
        completion = json.loads((case.root / 'readback.stdout').read_text())
        self.assertEqual(completion['completed_tests'], len(case.ids))
        self.assertEqual(completion['outcome'], 'validated-in-actual-runner-report-and-exit')

    def test_01_original538_meaningful17_reproduces_incomplete(self):
        case = self.case('01-original538-meaningful17', baseline=True)
        self.assertEqual(self.collect(case), 2)
        self.assertEqual(self.collect(case, 'readback'), 2)
        self.assertEqual((case.root / 'output/result.json').read_bytes(), b'')

    def test_02_corrected_meaningful17_on_exact_def41(self):
        case = self.case('02-corrected-meaningful17')
        self.complete(case, 0, ['passed'] * 17, subtests=True)
        capture = self.report(case)['capture']
        self.assertIn('DRAIN_OBSERVATION=', capture)
        self.assertIn('PHASE_OBSERVATION=', capture)
        self.assertIn('SHARED_BUDGET_OBSERVATION=', capture)

    def test_03_async_setup_body_teardown_and_traceback_reporting(self):
        body = '''import asyncio, unittest
class Subject(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await asyncio.sleep(0)
        self.value = 6
    async def asyncTearDown(self):
        await asyncio.sleep(0)
        print('async teardown reached')
    async def test_pass(self):
        task = asyncio.create_task(asyncio.sleep(0, result=self.value * 7))
        self.assertEqual(await task, 42)
    async def test_failure(self):
        self.assertEqual(self.value, 9, 'actual intentional assertion544')
    async def test_error(self):
        raise ValueError('actual intentional error544')
    async def test_skip(self):
        self.skipTest('actual intentional skip544')
'''
        ids = ['test_owned544.Subject.test_' + n for n in ('pass', 'failure', 'error', 'skip')]
        case = self.case('03-async-outcomes', body, ids)
        self.complete(case, 1, ['passed', 'failed', 'error', 'skipped'])
        report = self.report(case)
        self.assertIn('actual intentional assertion544', report['events'][1]['detail'])
        self.assertIn('actual intentional error544', report['events'][2]['detail'])
        self.assertEqual(report['capture'].count('async teardown reached'), 4)

    def test_04_async_setup_error_is_conclusive(self):
        case = self.case('04-async-setup-error', '''import unittest
class Subject(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        raise LookupError('setup544')
    async def test_body(self):
        self.fail('unreached544')
''')
        self.complete(case, 1, ['error'])
        self.assertIn('setup544', self.report(case)['events'][0]['detail'])
        self.assertNotIn('unreached544', self.report(case)['events'][0]['detail'])

    def test_05_resource_denial_remains_and_errors_report(self):
        operations = {
            'read': "open('/etc/qa544-forbidden', 'r')",
            'own_script_read': "open(__import__('sys').argv[0], 'r')",
            'write': "open('qa544-forbidden', 'w')",
            'child': "__import__('subprocess').run(['/usr/bin/true'])",
            'thread': "__import__('threading').Thread(target=lambda: None).start()",
        }
        for kind, expression in operations.items():
            with self.subTest(kind=kind):
                case = self.case('05-resource-' + kind, 'import unittest\nclass Subject(unittest.TestCase):\n    def test_body(self):\n        ' + expression + '\n')
                self.complete(case, 1, ['error'])
                self.assertTrue(any(word in self.report(case)['events'][0]['detail'] for word in ('refused', 'forbids')))
        case = self.case('05-explicit-refusals', '''import unittest, threading
class Subject(unittest.TestCase):
    def test_body(self):
        with self.assertRaisesRegex(RuntimeError, 'outside selected source'):
            open('/etc/qa544-forbidden')
        with self.assertRaisesRegex(RuntimeError, 'file write refused'):
            open('qa544-forbidden', 'w')
        with self.assertRaisesRegex(RuntimeError, 'forbids child'):
            threading.Thread(target=lambda: None).start()
''')
        self.complete(case, 0, ['passed'])

    def test_06_load_capture_source_and_attempt_discrimination(self):
        body = 'import unittest\nclass Subject(unittest.TestCase):\n    def test_body(self):\n        self.assertEqual(6 * 7, 42)\n'
        missing = self.case('06-load-missing', body, ['test_owned544.Subject.test_missing'])
        self.assertEqual(self.collect(missing), 2)
        self.assertEqual(self.collect(missing, 'readback'), 2)
        overflow = self.case('06-capture-overflow', body.replace('self.assertEqual(6 * 7, 42)', "print('x' * 200)"), limits={'capture_bytes': 32, 'result_bytes': 65536})
        self.assertEqual(self.collect(overflow), 2)
        self.assertEqual(self.collect(overflow, 'readback'), 2)
        before = self.case('06-source-before', body)
        (before.export / REL).write_text(body + '# changed before\n')
        self.assertEqual(self.collect(before), 2)
        self.assertEqual(self.collect(before, 'readback'), 2)
        after = self.case('06-source-after', body)
        self.complete(after, 0, ['passed'])
        (after.export / REL).write_text(body + '# changed after\n')
        self.assertEqual(self.collect(after, 'readback', 'readback-changed'), 2)
        stale = self.case('06-existing-attempt', body)
        self.complete(stale, 0, ['passed'])
        prior = (stale.root / 'output/result.json').read_bytes()
        self.assertEqual(self.collect(stale, label='second-runner'), 2)
        self.assertEqual((stale.root / 'output/result.json').read_bytes(), prior)
        # Known retained limitation: readback alone still describes the first run.
        self.assertEqual(self.collect(stale, 'readback', 'readback-stale'), 0)
        changed = self.case('06-selection-changed', body)
        with (changed.root / 'scripts/TEST-SELECTION.json').open('a') as f:
            f.write(' ')
        self.assertEqual(self.collect(changed), 2)
        self.assertEqual(self.collect(changed, 'readback'), 2)

    def test_07_fd_capture_and_semantic_limits_remain_explicit(self):
        case = self.case('07-fd-and-python', '''import os, unittest
class Subject(unittest.TestCase):
    def test_body(self):
        os.write(1, b'FD544\\n')
        print('PY544')
        self.assertEqual(2 ** 5, 32)
''')
        self.assertEqual(self.collect(case), 0)
        self.assertEqual(self.collect(case, 'readback'), 0)
        self.assertEqual(self.report(case)['capture'], 'PY544\n')
        self.assertTrue((case.root / 'runner.stdout').read_bytes().startswith(b'FD544\n'))
        noop = self.case('07-noop-limit', 'import unittest\nclass Subject(unittest.TestCase):\n    def test_body(self):\n        pass\n')
        self.complete(noop, 0, ['passed'])

    def test_09_unselected_budget_and_class_skip_incomplete(self):
        body = 'import unittest\nclass Subject(unittest.TestCase):\n    def test_body(self):\n        self.assertEqual(6 * 7, 42)\n'
        case = self.case('09-unselected', body)
        # Removing the fictional seal must refuse before selection/result reads.
        for name in ('qa_selected_tests.py', 'qa_resource_readback.py'):
            path = case.root / 'scripts' / name
            text = path.read_text().replace(sha((case.root / 'scripts/TEST-SELECTION.json').read_bytes()),
                '$input.independently_selected_final_selection_file_sha256')
            path.write_text(text)
        self.assertEqual(self.collect(case), 2)
        self.assertEqual(self.collect(case, 'readback'), 2)
        self.assertFalse((case.root / 'output/result.json').exists())
        budget = self.case('09-result-budget', body, limits={'capture_bytes': 1024, 'result_bytes': 16})
        self.assertEqual(self.collect(budget), 2)
        self.assertEqual(self.collect(budget, 'readback'), 2)
        self.assertEqual((budget.root / 'output/result.json').read_bytes(), b'')
        skipped = self.case('09-class-skip-limit', body.replace('    def test_body(self):',
            "    @classmethod\n    def setUpClass(cls):\n        raise unittest.SkipTest('class skip544')\n    def test_body(self):"))
        # Conserved538 limitation: class setup skips do not start selected IDs.
        self.assertEqual(self.collect(skipped), 2)
        self.assertEqual(self.collect(skipped, 'readback'), 2)
        self.assertEqual((skipped.root / 'output/result.json').read_bytes(), b'')

    def test_08_actual_source_runner_association_refusals(self):
        case = self.case('08-association', 'import unittest\nclass Subject(unittest.TestCase):\n    def test_body(self):\n        self.assertTrue(4 > 1)\n')
        self.complete(case, 0, ['passed'])
        attempt = 'fictional-attempt544'
        # Exact owned retained fixture, using a single source export at expected path.
        home = case.root / 'service-fiction'
        expected = home / 'artifacts' / attempt / 'qa-source'
        expected.mkdir(parents=True)
        for item in case.source['files']:
            target = expected / item['path']; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((case.export / item['path']).read_bytes())
        record = json.loads((case.root / 'runner-collection.json').read_text())
        record.update(label='qa-runner', complete=True)
        association = dict(case.source, root=str(expected), manifest=digest(case.source['files']),
                           method='git-blobs-readonly-namespace-v1', runner_record=digest(record))
        receipt = {'before': {'head': case.source['head'], 'tree': case.source['tree']},
                   'tools': [record], 'outcome': {'source_execution': association}}
        store = SimpleNamespace(home=home, config=self.store.config, one=lambda *args: None, rows=lambda *args: [])
        policy = {'source_head': case.source['head']}
        self.assertEqual(qa_source.verify(store, attempt, policy, receipt), association)
        changed = copy.deepcopy(receipt); changed['tools'][0]['END'] = 2
        with self.assertRaises(Refusal):
            qa_source.verify(store, attempt, policy, changed)
        with self.assertRaises(Refusal):
            qa_source.verify(store, 'different-attempt544', policy, receipt)
        (expected / REL).write_text('changed source544\n')
        with self.assertRaises(Refusal):
            qa_source.verify(store, attempt, policy, receipt)


if __name__ == '__main__':
    unittest.main(verbosity=2)
