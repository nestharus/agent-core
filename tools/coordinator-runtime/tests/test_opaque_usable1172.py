"""DECISION1172 owned subprocess controls; all provider output is fiction."""
import json
import unittest
from test_opaque_review1157 import SharedOwnership, Material
from coordinator_runtime import opaque_review, reviews
from coordinator_runtime.contracts import Refusal


class Dependency(unittest.TestCase):
    setUp = Material.setUp

    def test_dependency_is_explicit_absolute_and_never_shell_or_search(self):
        for invalid in ['codex', '', '../codex', '/tmp/../codex', '/bad\x00path']:
            with self.subTest(value=repr(invalid)), self.assertRaises(self.module.ReviewRefusal):
                self.module.executable_path(invalid)
        self.assertEqual(self.module.executable_path('/public/frontend'), '/public/frontend')
        with self.assertRaises(TypeError):
            self.module.Context(self.home/'missing', '.codex2', 'collector', 30, object())
        self.assertFalse((self.home/'missing').exists())

    def test_service_policy_requires_the_same_explicit_dependency(self):
        policy = dict(transport='opaque-cli-v1', executable='/public/frontend',
            launcher_sha256=reviews.sha(opaque_review.launcher_path().read_bytes()),
            deadline=30, method='fixture', method_files={}, method_closure='unified-definitions-v1', components={})
        opaque_review.validate(policy)
        policy['executable'] = 'codex'
        with self.assertRaises(Refusal):
            opaque_review.validate(policy)
        del policy['executable']
        with self.assertRaises(Refusal):
            opaque_review.validate(policy)


class Diagnostics(unittest.IsolatedAsyncioTestCase):
    setUp = SharedOwnership.setUp
    standin = SharedOwnership.standin
    turn = SharedOwnership.turn

    async def test_diagnostic_item_is_attributed_and_does_not_fabricate_tool_effect(self):
        event = {'type':'item.completed', 'item':{'type':'error', 'message':'fictional diagnostic'}}
        self.child_body = 'import json,sys\nsys.stdin.read()\nprint(' + repr(json.dumps(event)) + ',flush=True)\n' + self.child_body.replace('sys.stdin.read()', 'pass')
        code, receipt, answer = await self.turn('diagnostic')
        self.assertEqual(code, 0)
        self.assertTrue(receipt['answered'])
        self.assertTrue(receipt['capture_complete'])
        self.assertEqual(receipt['errors'], [])
        self.assertEqual(len(receipt['diagnostics']), 1)
        self.assertEqual(receipt['diagnostics'][0]['message_bytes'], len('fictional diagnostic'))
        self.assertNotIn('fictional diagnostic', str(receipt['diagnostics']))
        self.assertEqual(self.context.state, 'live')
        self.assertFalse(self.originals.owned)

    async def test_terminal_failure_retains_complete_capture_numeric_end_and_no_answer(self):
        events = [dict(type='item.completed', item=dict(type='error', message='fictional failure')),
                  dict(type='turn.failed', error={'message':'fictional turn failure'})]
        self.child_body = 'import sys\nsys.stdin.read()\n' + '\n'.join('print('+repr(json.dumps(e))+',flush=True)' for e in events) + '\nraise SystemExit(1)\n'
        code, receipt, answer = await self.turn('failed')
        self.assertEqual(code, 1)
        self.assertTrue(receipt['capture_complete'])
        self.assertTrue(receipt['turn_failed'])
        self.assertFalse(receipt['answered'])
        self.assertEqual(len(receipt['diagnostics']), 2)
        self.assertFalse(receipt['errors'])
        self.assertEqual(self.context.state, 'interrupted')
        with self.assertRaises(self.module.ReviewRefusal):
            await self.turn('no-replay')
        self.assertEqual(len(self.argv), 1)
        self.assertFalse(self.originals.owned)

    async def test_explicit_dependency_and_fixed_account_environment_reach_high_level_turn(self):
        await self.turn('dependency')
        argv, env = self.argv[0]
        self.assertEqual(argv[0], '/usr/bin/false')
        self.assertEqual(env['PATH'], '/usr/local/bin:/usr/bin:/bin')
        self.assertEqual(env['CODEX_HOME'], '/home/nes/.codex4')
        self.assertEqual(set(env), {'PATH','HOME','CODEX_HOME','XDG_CONFIG_HOME','TMPDIR','PYTHONDONTWRITEBYTECODE'})

    async def test_diagnostic_flood_is_bounded_partial_and_still_collected(self):
        event = json.dumps({'type':'item.completed','item':{'type':'error','message':'fictional'}})
        self.child_body = 'import sys\nsys.stdin.read()\n' + 'print('+repr((event+'\n')*80)+',flush=True)\n'
        code, receipt, answer = await self.turn('flood')
        self.assertIsInstance(code, int)
        self.assertEqual(len(receipt['diagnostics']), 64)
        self.assertFalse(receipt['capture_complete'])
        self.assertFalse(receipt['answered'])
        self.assertFalse(self.originals.owned)


class BoundaryDiscrimination(unittest.TestCase):
    setUp = Material.setUp

    def test_constants_from_a_different_command_cannot_admit_substantive_material(self):
        import importlib.util
        from pathlib import Path
        path = Path(__file__).parents[1]/'qualify_opaque_usable1172.py'
        spec = importlib.util.spec_from_file_location('qualification1172',path)
        caller = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(caller)
        expected = ['/usr/bin/python3', '/owned/material/0001.txt']
        self.assertTrue(caller.exact_command('/usr/bin/python3 /owned/material/0001.txt', expected))
        self.assertFalse(caller.exact_command("/usr/bin/python3 -c 'print(13)'", expected))
        self.assertFalse(caller.exact_command('/usr/bin/python3 /owned/material/0001.txt; echo 13', expected))
        directory=self.home/'omitted-operations'
        directory.mkdir()
        omitted = dict(type='item.completed',item=dict(type='command_execution',exit_code=0,
            command="/usr/bin/python3 -c 'print(13)'", aggregated_output='{"read":{"errno":13}}'))
        (directory/'stdout.jsonl').write_text(json.dumps(omitted)+'\n')
        admitted,evidence=caller.boundary_check(directory,expected,'unavailable', 'bridge',
                                               self.home/'unavailable-read',self.home/'unavailable-write')
        self.assertFalse(admitted)
        self.assertEqual(evidence['reason'],'command is not exact immutable probe')
