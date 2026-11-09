"""Work1074/1078/1085 current protections; expectations precede execution.

These are current fictional transitions, never substituted old704 counterparts.
"""
import copy
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'current_qa'))
from procedure import (SELECTORS, PROTECTIONS, HISTORICAL_UNSELECTED, VERSION, validate_outcomes, sandbox,
                       entry_text, command_bindings, verify_commands, sha, collect)
from coordinator_runtime import configuration, processing
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
from support import config_at, enrolled, event
from test_source_selection707 import SourceSelection


class CurrentGrowth1085(unittest.TestCase):
    def test_new_module_requires_changed_configuration_and_preserves_originals(self):
        f = SourceSelection()
        self.addCleanup(f.doCleanups)
        f.setUp()
        runtime = f.runtime
        original = configuration.journal(runtime)
        inode = runtime.path.stat().st_ino
        grants = list(f.f.conn.iterdump())
        added = f.copy.modules/'fictional_new_current1085.py'
        added.write_text('"""Owned inert fictional new module; no old counterpart."""\n')
        with self.assertRaisesRegex(Refusal, 'file extent'):
            f.selection()
        self.assertEqual(configuration.journal(runtime), original)
        value = configuration.candidate(runtime, str(f.f.directory/'growth.json'), ['bi', 'qe'])
        Path(value['operator_config']).write_text(encode(value))
        selected = f.selection(value)
        self.assertIn(str(added), selected['basis']['release']['files'])
        self.assertNotIn(str(added), f.before_release['files'])
        self.assertNotIn('source_only', selected['basis'])
        receipt = f.apply(selected, value)
        self.assertNotEqual(receipt['previous'], receipt['configuration'])
        self.assertFalse(receipt['historical_recovery'])
        self.assertEqual(runtime.path.stat().st_ino, inode)
        self.assertEqual(list(f.f.conn.iterdump()), grants)
        self.assertEqual(runtime.one('SELECT COUNT(*) n FROM events')['n'], 4)
        self.assertEqual(runtime.one('SELECT COUNT(*) n FROM outboxes')['n'], 67)
        self.assertEqual(runtime.job('fictional-old-job')['effects'], 'unknown')
        with self.assertRaises(Refusal):
            processing.Access(runtime, f.f.oldkey, f.f.boards).current()
        Path('/fixtures/growth-witness.json').write_text(json.dumps(dict(database=str(runtime.path),
            added=str(added), original_configuration=digest(f.original), current_configuration=digest(value))))


class RetainedCurrent1085(unittest.TestCase):
    def test_generated_commands_fit_the_actual_public_command_contract(self):
        from coordinator_runtime.ordinary import command_policy
        manifest = json.loads(Path('/procedure/manifest.json').read_text())
        commands = json.loads(Path('/procedure/COMMANDS.json').read_text())
        home = Path('/fixtures/current-command-policy')
        home.mkdir()
        runtime = enrolled(config_at(home))
        self.addCleanup(runtime.close)
        for role in ('command', 'readback'):
            command_policy(runtime, commands[role], [manifest['instance']], commands['public_executables'][role])

    def test_current_retained_file_and_real_input_backpressure(self):
        home = Path('/fixtures/current-oracle')
        home.mkdir(mode=0o700)
        original = home/'original.txt'
        original.write_bytes(b'current original retained\n')
        config = config_at(home)
        config['limits']['max_events'] = 1
        runtime = enrolled(config)
        self.addCleanup(runtime.close)
        self.assertTrue(runtime.ingest(event(config, name='current-original')))
        with self.assertRaises(Backpressure):
            runtime.ingest(event(config, name='current-refused-second'))
        self.assertEqual(runtime.rows('SELECT role,state,ack,processed_at FROM events'),
                         [dict(role='Work', state='received', ack='pending', processed_at=None)])
        self.assertEqual(runtime.rows('SELECT * FROM attempts'), [])
        self.assertEqual(original.read_bytes(), b'current original retained\n')


class CollectionContract1085(unittest.TestCase):
    def setUp(self):
        self.m = dict(run_id='fictional-new-run', candidate='/fictional-current', instance='/fictional-procedure',
                      output='/fictional-effects', runtime_modules=['fixture.py'])
        self.r = dict(run_id='fictional-new-run', manifest='fictional-manifest', argv=sandbox(self.m),
                      exit=0, complete=True, reason=None)
        self.events = [dict(kind='scope', ids=['independent_fixture.Control.test_behavior'], selectors=SELECTORS,
                                 historical_unselected=copy.deepcopy(HISTORICAL_UNSELECTED)),
                       dict(kind='start', id='independent_fixture.Control.test_behavior'),
                       dict(kind='success', id='independent_fixture.Control.test_behavior'),
                       dict(kind='finish', tests=1, runtime_modules=['fixture.py'])]

    def check(self):
        return validate_outcomes(self.m, self.r, self.events, 'fictional-manifest')

    def test_complete_concrete_collection_is_distinct_from_acceptance(self):
        self.assertEqual(self.check(), ['independent_fixture.Control.test_behavior'])
        self.assertNotIn('acceptance', self.r)

    def test_failed_incomplete_unknown_END_and_stale_bindings_refuse(self):
        for changes in (dict(exit=1), dict(exit=None), dict(complete=False), dict(reason='overflow'),
                        dict(run_id='old-run'), dict(manifest='old-manifest'), dict(argv=['wrong-tool'])):
            with self.subTest(changes=changes):
                self.setUp()
                self.check()  # Each negative starts from a valid positive.
                self.r.update(changes)
                guard = 'stale execution binding' if set(changes) & {'run_id', 'manifest', 'argv'} else 'failed/incomplete actual execution'
                with self.assertRaisesRegex(ValueError, guard):
                    self.check()

    def test_skip_error_failure_missing_and_duplicate_outcomes_refuse(self):
        for kind in ('skip', 'error', 'failure', 'unexpected-success', 'expected-failure'):
            with self.subTest(kind=kind):
                self.setUp()
                self.check()
                self.events[2]['kind'] = kind
                with self.assertRaisesRegex(ValueError, 'failures/errors/skips/unexecuted controls'):
                    self.check()
        self.setUp()
        self.check()
        self.events.pop(2)
        with self.assertRaisesRegex(ValueError, 'failures/errors/skips/unexecuted controls'):
            self.check()
        self.setUp()
        self.check()
        self.events.insert(2, copy.deepcopy(self.events[1]))
        with self.assertRaisesRegex(ValueError, 'missing/duplicate actual starts'):
            self.check()
        self.setUp()
        self.check()
        self.events.insert(3, copy.deepcopy(self.events[2]))
        with self.assertRaisesRegex(ValueError, 'failures/errors/skips/unexecuted controls'):
            self.check()

    def test_omitted_current_module_and_reduced_protection_selection_refuse(self):
        self.check()
        self.events[-1]['runtime_modules'] = []
        with self.assertRaisesRegex(ValueError, 'incomplete current runtime import closure'):
            self.check()
        self.setUp()
        self.check()
        self.events[0]['selectors'] = SELECTORS[:-1]
        with self.assertRaisesRegex(ValueError, 'incomplete current protection selection'):
            self.check()

    def test_scope_start_outcome_shape_and_history_guards_discriminate(self):
        mutations = [
            (lambda e: e.pop(), 'incomplete events'),
            (lambda e: e[0].update(ids=[]), 'missing/duplicate selected IDs'),
            (lambda e: e[0].update(historical_unselected={}), 'unbound historical applicability disposition'),
            (lambda e: e.pop(1), 'missing/duplicate actual starts'),
            (lambda e: e[-1].update(tests=2), 'incomplete or extra outcomes'),
            (lambda e: e.insert(3, dict(kind='unselected-extra')), 'incomplete or extra outcomes')]
        for mutate, guard in mutations:
            with self.subTest(guard=guard):
                self.setUp()
                self.check()
                mutate(self.events)
                with self.assertRaisesRegex(ValueError, guard):
                    self.check()

    def test_all_decision_dimensions_have_fixed_current_selection(self):
        # Independently named obligations1093/1107/1114, never observed length.
        self.assertEqual(set(PROTECTIONS), {
            'source-package-tools', 'genuine-history-and-lineage', 'independent-current-authority',
            'retained-resources-and-capacity', 'collection-and-currentness',
            'independent-same-package-receivers', 'whole-owned-lifecycle',
            'ordinary-journal-failure-and-finite-progress'})
        self.assertIn('test_collection1114', PROTECTIONS['whole-owned-lifecycle'])
        self.assertIn('test_correction1092', PROTECTIONS['whole-owned-lifecycle'])
        self.assertIn('test_final_composition1107', PROTECTIONS['ordinary-journal-failure-and-finite-progress'])
        self.assertEqual(VERSION, 'current-contract1085-v1')
        self.assertEqual(set(SELECTORS), {s for group in PROTECTIONS.values() for s in group})


class ActualCollection1085(unittest.TestCase):
    def setUp(self):
        self.area = Path('/fixtures')/self.id()
        self.area.mkdir()

    def invoke(self, name, code, maximum=4096, seconds=3):
        script = self.area/(name+'.py')
        script.write_text(code)
        out = self.area/name
        out.mkdir()
        record = collect(['/usr/bin/python3.12', '-B', str(script)], out, seconds, maximum)
        (out/'actual-collection.json').write_text(json.dumps(record))
        return record, (out/'transcript.txt').read_bytes()

    def test_actual_nonzero_END_is_collected_with_complete_failure_output(self):
        record, body = self.invoke('failure', 'print("owned failure")\nraise SystemExit(7)\n')
        self.assertEqual(record['exit'], 7)
        self.assertTrue(record['complete'])
        self.assertEqual(body, b'owned failure\n')

    def test_actual_overflow_and_timeout_keep_failure_and_finite_collection(self):
        record, body = self.invoke('overflow', 'print("x"*8192)\n', maximum=32)
        self.assertFalse(record['complete'])
        self.assertIn('overflow', record['reason'])
        self.assertEqual(len(body), 32)
        record, body = self.invoke('timeout', 'import time\ntime.sleep(30)\n', seconds=1)
        self.assertFalse(record['complete'])
        self.assertIn('deadline', record['reason'])
        self.assertIsInstance(record['exit'], int)
        self.assertLess(record['seconds'], 10)

    def test_entry_and_command_cannot_be_rebound_together(self):
        m = dict(instance=str(self.area), tools={'/usr/bin/python3.12': {'sha256': 'fictional-tool-pin'}})
        expected = 'fictional-exact-manifest'
        commands = command_bindings(m, expected)
        for role in ('command', 'readback'):
            (self.area/(role+'_entry.py')).write_text(entry_text(role, self.area, expected))
        path = self.area/'COMMANDS.json'
        path.write_text(json.dumps(commands))
        verify_commands(m, expected)
        changed = b'raise SystemExit(0)\n'
        (self.area/'readback_entry.py').write_bytes(changed)
        commands['readback']['script_sha256'] = sha(changed)
        path.write_text(json.dumps(commands))
        with self.assertRaisesRegex(ValueError, 'derived command binding changed'):
            verify_commands(m, expected)


class AllocationSites1127(unittest.TestCase):
    def test_whole_visible_account_and_actual_allocation_floors_remain_joint(self):
        from procedure import resources
        area=Path('/fixtures/allocation-sites1127');area.mkdir()
        (area/'owned.txt').write_text('visible retained input')
        m=dict(area=str(area), instance=str(area/'instance'), output=str(area/'output'),
               limits=dict(entries=100,bytes=1024**2))
        positive=resources(m)
        self.assertGreaterEqual(positive['entries'],2)
        self.assertEqual({x['purpose'] for x in positive['allocation_sites']},{'instance','output'})
        low={**m,'instance':'/tmp/nonexistent-instance1127'}
        with self.assertRaisesRegex(ValueError,'OS capacity floor lost'):resources(low)
        self.assertFalse(Path(low['instance']).exists())
        small={**m,'limits':dict(entries=1,bytes=1024**2)}
        with self.assertRaisesRegex(ValueError,'retained cumulative attempt exceeds admission'):resources(small)
        self.assertEqual((area/'owned.txt').read_text(),'visible retained input')
