"""Actual adapter boundary qualification on an explicitly supplied owned fixture.

PORTABLE1047_SPEC names the qualification spec, never a live runtime config.
PORTABLE1047_RESULTS is a fresh KEEP directory. No fixture or result is deleted.
Run after a successful baseline command/readback; this suite does not claim
final1041 adequacy. Tool ENDs and complete outputs are retained per test.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'portable_qa'))
from common import file_pin, sha
from prepare import prepare


class Procedure1047(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(Path(os.environ['PORTABLE1047_SPEC']).read_text())
        cls.base = Path(os.environ['PORTABLE1047_RESULTS'])
        cls.base.mkdir(mode=0o700)

    def setUp(self):
        self.area = self.base/self._testMethodName
        self.area.mkdir(mode=0o700)
        self.spec = copy.deepcopy(type(self).spec)
        self.spec.update(instance=str(self.area/'instance'), output=str(self.area/'output'))

    def invoke(self, argv, cwd, label):
        r = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=950)
        (self.area/(label+'.json')).write_text(json.dumps(dict(argv=argv,cwd=str(cwd),END=r.returncode,
            stdout=r.stdout.decode(),stderr=r.stderr.decode()),indent=2)+'\n')
        return r

    def command(self, commands, role='command', args=()):
        return self.invoke(commands[role]['argv']+list(args), self.spec['candidate'], role)

    def readonly_readback(self, changes, reason):
        # Remap an owned derivative at the original output name. The original
        # retained result and manifest remain byte-for-byte untouched.
        m = json.loads((Path(type(self).spec['instance'])/'manifest.json').read_text())
        derived = self.area/'retained-derivative'
        derived.mkdir(mode=0o700)
        original = Path(m['output'])
        for name in ('OWNER.json', 'execution.json', 'transcript.txt', 'events.jsonl'):
            (derived/name).write_bytes((original/name).read_bytes())
        changes(derived, m)
        argv = [m['bwrap'], '--die-with-parent', '--unshare-all', '--new-session', '--tmpfs', '/']
        for p in ('/usr', '/lib', '/lib64', '/bin'):
            argv += ['--ro-bind', p, p]
        argv += ['--proc', '/proc', '--dev', '/dev', '--ro-bind', m['candidate'], m['candidate'],
                 '--ro-bind', m['instance'], m['instance'], '--ro-bind', str(derived), m['output'],
                 '--clearenv', '--setenv', 'HOME', '/fictional', '--chdir', m['candidate'],
                 m['python'], '-B', m['instance']+'/readback_entry.py']
        r = self.invoke(argv, self.spec['candidate'], 'readback-negative')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(reason, r.stderr.decode())

    def test_wrong_source_refuses_before_output(self):
        self.spec['candidate_files'][next(iter(self.spec['candidate_files']))]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            prepare(self.spec)
        self.assertFalse(Path(self.spec['output']).exists())

    def test_input_mismatch_refuses_execution(self):
        commands = prepare(self.spec)
        (Path(self.spec['instance'])/'sdk/retention.py').write_text('changed fixture input\n')
        r = self.command(commands)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('identity mismatch', r.stderr.decode())
        self.assertFalse(Path(self.spec['output']).exists())
        r = self.command(commands, 'readback')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('identity mismatch', r.stderr.decode())

    def test_no_git_candidate_required(self):
        candidate = self.area/'candidate'
        candidate.mkdir()
        (candidate/'.git').mkdir()
        self.spec['candidate'] = str(candidate)
        with self.assertRaisesRegex(ValueError, 'no-Git candidate export'):
            prepare(self.spec)

    def test_missing_positive_dependency_refuses(self):
        del self.spec['candidate_files']['tools/message-board/board_store.py']
        with self.assertRaisesRegex(ValueError, 'complete board input missing'):
            prepare(self.spec)

    def test_script_mismatch_refuses_execution(self):
        commands = prepare(self.spec)
        with (Path(self.spec['instance'])/'worker.py').open('a') as p:
            p.write('\n# altered script\n')
        r = self.command(commands)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('identity mismatch', r.stderr.decode())

    def test_derived_command_input_mismatch_refuses(self):
        commands = prepare(self.spec)
        (Path(self.spec['instance'])/'COMMANDS.json').write_text('{}\n')
        r = self.command(commands)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('derived command input identity mismatch', r.stderr.decode())

    def test_wrong_test_set_refuses(self):
        self.spec['expected_ids'] = self.spec['expected_ids'][:-1]
        commands = prepare(self.spec)
        r = self.command(commands)
        self.assertNotEqual(r.returncode, 0)
        text = (Path(self.spec['output'])/'transcript.txt').read_text()
        self.assertIn('missing/extra/wrong declared tests', text)

    def injected(self, body):
        candidate = self.area/'candidate'
        shutil.copytree(self.spec['candidate'], candidate, symlinks=True)
        rel = 'tools/coordinator-runtime/tests/test_aaa_adversary1047.py'
        (candidate/rel).write_text('import unittest\nfrom pathlib import Path\nclass Adversary(unittest.TestCase):\n'
                                   ' def test_boundary(self):\n'+body)
        self.spec['candidate'] = str(candidate)
        self.spec['candidate_files'][rel] = file_pin(candidate/rel)
        selector = 'test_aaa_adversary1047.Adversary.test_boundary'
        self.spec['selected_selectors'].append(selector)
        self.spec['expected_ids'].append(selector)
        return prepare(self.spec)

    def test_failed_test_is_not_pass(self):
        commands = self.injected('  self.fail("actual failing fixture assertion")\n')
        r = self.command(commands)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('actual failing fixture assertion', (Path(self.spec['output'])/'transcript.txt').read_text())
        self.assertNotEqual(self.command(commands, 'readback').returncode, 0)

    def test_skipped_test_is_not_pass(self):
        commands = self.injected('  self.skipTest("actual skipped fixture")\n')
        self.assertNotEqual(self.command(commands).returncode, 0)
        self.assertIn('"kind": "skip"', (Path(self.spec['output'])/'events.jsonl').read_text())
        self.assertNotEqual(self.command(commands, 'readback').returncode, 0)

    def test_actual_source_write_is_blocked(self):
        commands = self.injected('  Path("/src/invalid-write1047").write_text("forbidden")\n')
        self.assertNotEqual(self.command(commands).returncode, 0)
        self.assertIn('Read-only file system', (Path(self.spec['output'])/'transcript.txt').read_text())
        self.assertFalse((Path(self.spec['candidate'])/'invalid-write1047').exists())

    def test_complete_output_required(self):
        self.spec['limits']['output_bytes'] = 1
        commands = prepare(self.spec)
        self.assertNotEqual(self.command(commands).returncode, 0)
        record = json.loads((Path(self.spec['output'])/'execution.json').read_text())
        self.assertFalse(record['complete'])
        self.assertIn('overflow', record['reason'])
        self.assertNotEqual(self.command(commands, 'readback').returncode, 0)

    def test_overlap_and_unsupported_scope_refuse(self):
        self.spec['output'] = str(Path(self.spec['candidate'])/'forbidden-output')
        with self.assertRaisesRegex(ValueError, 'overlapping roots'):
            prepare(self.spec)
        self.spec['output'] = str(self.area/'output')
        self.spec['convenient_smaller_scope'] = True
        with self.assertRaisesRegex(ValueError, 'exact constructor fields'):
            prepare(self.spec)

    def test_unsupported_arguments_refuse(self):
        commands = prepare(self.spec)
        r = self.command(commands, args=['unsupported'])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no runner arguments', r.stderr.decode())

    def test_stale_result_refuses(self):
        def change(d, m):
            r = json.loads((d/'execution.json').read_text())
            r['run_id'] = 'stale-execution'
            (d/'execution.json').write_text(json.dumps(r))
        self.readonly_readback(change, 'stale/wrong execution binding')

    def test_altered_output_refuses(self):
        def change(d, m):
            with (d/'transcript.txt').open('ab') as p:
                p.write(b'altered retained output\n')
        self.readonly_readback(change, 'incomplete/altered retained output')

    def test_missing_or_skipped_outcome_refuses(self):
        def change(d, m):
            rows = (d/'events.jsonl').read_text().splitlines()
            (d/'events.jsonl').write_text('\n'.join(rows[:-2])+'\n')
        self.readonly_readback(change, 'failed/skipped/missing test success')

    def test_readback_wrong_source_refuses(self):
        def change(d, m):
            rows = [json.loads(x) for x in (d/'events.jsonl').read_text().splitlines()]
            rows[-1]['modules']['coordinator_runtime.store'] = 'wrong/source.py'
            (d/'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
        self.readonly_readback(change, 'actual candidate runtime was not exercised')

    def test_wrong_ownership_refuses(self):
        def change(d, m):
            (d/'OWNER.json').write_text('{}\n')
        self.readonly_readback(change, 'wrong output ownership')

    def test_resource_effect_mismatch_refuses(self):
        def change(d, m):
            (d/'oracle').mkdir()
            (d/'oracle/original.txt').write_text('lost original\n')
        self.readonly_readback(change, 'wrong retained file effect')

    def test_retained_journal_effect_mismatch_refuses(self):
        def change(d, m):
            (d/'oracle/state').mkdir(parents=True)
            (d/'oracle/original.txt').write_text('retained original; second input refused\n')
            with sqlite3.connect(d/'oracle/state/runtime.sqlite3') as db:
                db.execute('CREATE TABLE events(role,state,ack,processed_at)')
                db.execute("INSERT INTO events VALUES('Work','processed','pending',123)")
        self.readonly_readback(change, 'wrong retained journal effect')

    def test_existing_output_refuses_replay(self):
        commands = prepare(self.spec)
        Path(self.spec['output']).mkdir()
        r = self.command(commands)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('fresh output required', r.stderr.decode())


if __name__ == '__main__':
    unittest.main()
