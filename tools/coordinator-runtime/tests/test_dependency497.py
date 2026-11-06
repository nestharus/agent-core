"""Maker497 fictional dependencies only; run inside the supplied bwrap boundary.

No Store, SQL connection, Board construction, native CLI, account, pool or network
operation is used. Runtime loader/send/lock functions receive owned test doubles.
"""
import ast
import copy
from contextlib import contextmanager, nullcontext
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coordinator_runtime import configuration, publication, retention_dependency as dep
from coordinator_runtime.contracts import Refusal, digest
from coordinator_runtime.owner_control import load_helper, OwnerControl

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / 'tools/message-board'
RECIPIENT = '11111111-1111-4111-8111-111111111111'
INTENT = '22222222-2222-4222-8222-222222222222'
QUEUE = '33333333-3333-4333-8333-333333333333'
ATTEMPT = '44444444-4444-4444-8444-444444444444'
MESSAGE = '55555555-5555-4555-8555-555555555555'


class Dependency497(unittest.TestCase):
    def setUp(self):
        # Deliberately retained in this invocation's isolated /tmp until exit.
        self.area = Path(tempfile.mkdtemp(prefix='maker497-'))
        self.library = self.area / 'provider'
        self.library.mkdir()
        bodies = {
            'queue_transport.py': 'VALUE = "owned queue"\n',
            'active_listener.py': 'VALUE = "owned listener"\n',
            'catalog.py': 'VALUE = "owned catalog"\n',
            'board_store.py': 'import queue_transport\nimport active_listener\n'
                              'def deferred():\n    import retention\n    return retention\n',
            'retention.py': 'import board_store\nimport catalog\n'
                'from contextlib import contextmanager\nimport fcntl\nimport os\n'
                'from pathlib import Path\n'
                f'CONTROL_DIR = Path({str(self.area / "control")!r})\n'
                '@contextmanager\ndef snapshot_lock():\n'
                '    CONTROL_DIR.mkdir(exist_ok=True)\n'
                '    fd = os.open(CONTROL_DIR / "work-rollback.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)\n'
                '    try:\n'
                '        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
                '        yield\n'
                '    finally:\n        os.close(fd)\n',
        }
        for name, body in bodies.items():
            (self.library/name).write_text(body)
        self.pins = dep.source_pins(str(self.library), [])
        self.store = SimpleNamespace(config={'canonical_publication': {
            'method': 'retention-same-inode-v1', 'library': str(self.library),
            'source_pins': self.pins}, 'artifact_exclusions': []})

    def selection(self, mode='queue-resume-existing'):
        return {'intent': INTENT, 'mode': mode, 'recipient': RECIPIENT, 'profile': '.codex4',
                'helper_sources': {'queue_transport.py': hashlib.sha256(
                    (LIBRARY/'queue_transport.py').read_bytes()).hexdigest()}}

    def helper(self, selection=None):
        return load_helper(SimpleNamespace(library=str(LIBRARY)), selection or self.selection())

    def test_public_loader_resume_exact_original_uuid_profile_pointer_and_warning(self):
        for warning in ('', '\nWarning: resume unavailable'):
            helper = self.helper()
            pointer = f'CONTROL intent={INTENT} attempt={ATTEMPT} message={MESSAGE}. Read full durable meaning.'
            calls = []
            def runner(argv, env, timeout, cap):
                calls.append((argv, env['CODEX_HOME']))
                return helper.CommandOutcome(0, 'Queued message '+QUEUE+warning)
            with patch.object(helper, '_profile_home', return_value=self.area / '.codex4') as profile:
                result = helper.queue_notice(RECIPIENT, '.codex4', pointer, resume=True, runner=runner)
            profile.assert_called_once_with('.codex4')
            self.assertEqual(calls, [(['codex', 'queue', '--thread', RECIPIENT, '--message', pointer, '--resume'],
                                      str(self.area / '.codex4'))])
            self.assertEqual((result.status, result.queue_message_id), ('queued', QUEUE))
            self.assertEqual(result.reason, 'queue_accepted_resume_warning' if warning
                             else 'queue_accepted_resume_requested_unknown')
            self.assertFalse(hasattr(result, 'processed'))

    def test_existing_mode_argv_unchanged_and_invalid_resume_never_calls_runner(self):
        helper = self.helper(self.selection('queue-existing'))
        calls = []
        def runner(argv, *args):
            calls.append(argv)
            return helper.CommandOutcome(0, 'Queued message '+QUEUE)
        with patch.object(helper, '_profile_home', return_value=self.area):
            result = helper.queue_notice(RECIPIENT, '.codex4', 'pointer', runner=runner)
            for invalid in (1, None, 'true'):
                with self.assertRaises(ValueError):
                    helper.queue_notice(RECIPIENT, '.codex4', 'pointer', resume=invalid, runner=runner)
        self.assertEqual(calls, [['codex','queue','--thread',RECIPIENT,'--message','pointer']])
        self.assertEqual(result.reason, 'queue_accepted')

    def test_helper_mode_hash_signature_and_compiled_identity_refuse_before_send(self):
        for mode in ('unsupported', None):
            with self.assertRaisesRegex(Refusal, 'unsupported'):
                self.helper(self.selection(mode))
        selection = self.selection()
        selection['helper_sources']['queue_transport.py'] = '0'*64
        with self.assertRaisesRegex(Refusal, 'source pin changed'):
            self.helper(selection)
        pin = self.selection()['helper_sources']['queue_transport.py']
        for helper, reason in (
                (SimpleNamespace(__coordinator_source_sha256__='0'*64), 'compiled'),
                (SimpleNamespace(__coordinator_source_sha256__=pin, queue_notice=lambda a,b,c: None), 'interface')):
            with patch('coordinator_runtime.board.module_at', return_value=helper):
                with self.assertRaisesRegex(Refusal, reason):
                    self.helper()

    def test_queue_uncertainty_remains_single_attempt_without_fallback(self):
        helper = self.helper()
        for outcome, expected in ((helper.CommandOutcome(0, 'unrecognized'), 'ambiguous'),
                                  (helper.CommandOutcome(None, '', timed_out=True), 'timeout'),
                                  (helper.CommandOutcome(0, 'Queued message '+QUEUE, output_truncated=True), 'ambiguous')):
            calls = []
            def runner(*args):
                calls.append(args)
                return outcome
            with patch.object(helper, '_profile_home', return_value=self.area):
                result = helper.queue_notice(RECIPIENT, '.codex4', 'pointer', resume=True, runner=runner)
            self.assertEqual(result.status, expected)
            self.assertEqual(len(calls), 1)

    def test_runtime_send_correlates_original_control_and_never_replays_enqueue(self):
        # A protocol double, not SQLite or a constructed Board. It tests the
        # real send state machine; real enrollment/grant/receipt QA stays owed.
        selection = self.selection()
        selection.update(scope='delivery-control-only', evidence=['fictional authority'],
            binding={'context': RECIPIENT, 'profile': '.codex4', 'state': 'unknown',
                     'turn': None, 'valid_until': time.time()+300, 'evidence': ['fictional binding']})
        payload = {'reason': 'owned fictional durable meaning'}
        pointer = f'CONTROL intent={INTENT} attempt={ATTEMPT} message={MESSAGE}. Read full durable meaning.'
        row = {'id': INTENT, 'delivery': 'fictional-delivery', 'caller': MESSAGE,
               'recipient': RECIPIENT, 'profile': '.codex4', 'mode': selection['mode'],
               'payload_hash': digest(payload), 'selection': json.dumps(selection),
               'attempt': ATTEMPT, 'client_message': MESSAGE, 'pointer': pointer,
               'state': 'prepared', 'result': None}
        class Connection:
            def execute(inner, sql, values=()):
                if sql.startswith("UPDATE coordinator_controls_v1 SET state='inflight'"):
                    self.assertEqual(row['state'], 'prepared')
                    row['state'] = 'inflight'
                    return SimpleNamespace(rowcount=1)
                if sql.startswith('UPDATE coordinator_controls_v1 SET state=?,result=?'):
                    row.update(state=values[0], result=values[1])
                    return SimpleNamespace(rowcount=1)
                if sql.startswith('SELECT * FROM coordinator_control_steps_v1'):
                    return []
                if sql.startswith('SELECT * FROM coordinator_controls_v1 WHERE id='):
                    return SimpleNamespace(fetchone=lambda: row)
                raise AssertionError('unadmitted protocol operation: '+sql)
        @contextmanager
        def opened(**kwargs):
            yield Connection()
        calls, bindings = [], []
        def binding(conn, runtime, delivery, chosen, **kwargs):
            self.assertEqual(delivery, row['delivery'])
            self.assertEqual(chosen, selection)
            bindings.append((delivery, chosen['recipient'], chosen['profile']))
            return {'id': delivery, 'payload': json.dumps(payload)}, {'owner': MESSAGE}
        board = SimpleNamespace(library=str(LIBRARY), opened=opened,
            config={'actor': ATTEMPT}, store=SimpleNamespace(write=lambda conn: nullcontext()),
            _control_lookup=lambda conn, intent: row if intent == INTENT else None,
            _control_selection=OwnerControl._control_selection,
            _control_binding=binding, control_receipt_status=lambda *args: {'pending': True},
            _control_record=lambda conn, record: copy.deepcopy(record))
        def selected_loader(actual_board, chosen):
            helper = load_helper(actual_board, chosen)
            self.assertEqual(helper.__coordinator_source_sha256__, chosen['helper_sources']['queue_transport.py'])
            helper._profile_home = lambda profile: self.area/profile
            queue_notice = helper.queue_notice
            def runner(argv, env, timeout, cap):
                self.assertEqual(row['state'], 'inflight')
                self.assertEqual(argv, ['codex','queue','--thread',RECIPIENT,'--message',pointer,'--resume'])
                self.assertEqual(env['CODEX_HOME'], str(self.area/'.codex4'))
                calls.append(argv)
                return helper.CommandOutcome(0, 'Queued message '+QUEUE+'\nWarning: wake unknown')
            helper.queue_notice = lambda *args, **kw: queue_notice(*args, runner=runner, **kw)
            return helper
        with patch.dict(os.environ, {'CODEX_SESSION_ID': MESSAGE}):
            with patch('coordinator_runtime.owner_control.load_helper', side_effect=selected_loader) as loader:
                accepted = OwnerControl.control_send(board, object(), INTENT)
                repeated = OwnerControl.control_send(board, object(), INTENT)
        self.assertEqual(accepted, repeated)
        self.assertEqual(loader.call_count, 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(bindings), 2)
        self.assertEqual(accepted['state'], 'accepted')
        self.assertEqual(json.loads(accepted['result'])['queue_message_id'], QUEUE)
        self.assertNotIn('processed_at', accepted)
        self.assertEqual((accepted['id'], accepted['attempt'], accepted['client_message']), (INTENT, ATTEMPT, MESSAGE))

    def test_retirement_api_preserved_without_importing_or_calling_board(self):
        tree = ast.parse((LIBRARY/'board_store.py').read_bytes())
        func = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'retire_coordinator_pointer')
        self.assertEqual([a.arg for a in func.args.args], ['conn','delivery','issuer','proof'])

    def test_retention_complete_compiled_resolution_overrides_ambient_modules(self):
        ambient = {name: SimpleNamespace(VALUE='unselected ambient')
                   for name in ('queue_transport','active_listener','catalog','board_store','retention')}
        with patch.dict(sys.modules, ambient):
            module = dep.load(str(self.library), self.pins, [])
            self.assertEqual(module.board_store.queue_transport.VALUE, 'owned queue')
            self.assertEqual(module.board_store.active_listener.VALUE, 'owned listener')
            self.assertEqual(module.catalog.VALUE, 'owned catalog')
            self.assertIs(module.board_store.deferred(), module)
            modules = {'retention': module, 'board_store': module.board_store,
                       'catalog': module.catalog, 'queue_transport': module.board_store.queue_transport,
                       'active_listener': module.board_store.active_listener}
            for name, loaded in modules.items():
                self.assertEqual(loaded.__file__, str(self.library/(name+'.py')))
                self.assertEqual(loaded.__coordinator_source_sha256__, self.pins[name+'.py'])
                self.assertIs(sys.modules[name], ambient[name])

    def test_each_dependency_tamper_refuses_before_any_provider_execution(self):
        for name in dep.FILES:
            path = self.library/name
            original = path.read_bytes()
            path.write_bytes(original+b'\n# changed\n')
            with patch('builtins.compile', side_effect=AssertionError('no compile before closure pins match')):
                with self.assertRaisesRegex(Refusal, 'source changed'):
                    dep.load(str(self.library), self.pins, [])
            path.write_bytes(original)

    def test_missing_pin_extra_pin_missing_file_symlink_and_exclusion_refuse(self):
        for pins in (None, {'retention.py': self.pins['retention.py']}, {**self.pins, 'extra.py': '0'*64}):
            with self.assertRaisesRegex(Refusal, 'five-file'):
                dep.load(str(self.library), pins, [])
        path = self.library/'catalog.py'
        path.rename(self.area/'saved.py')
        with self.assertRaisesRegex(Refusal, 'unavailable'):
            dep.load(str(self.library), self.pins, [])
        path.symlink_to(self.area/'saved.py')
        with self.assertRaisesRegex(Refusal, 'aliases'):
            dep.load(str(self.library), self.pins, [])
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('excluded before metadata')):
            with self.assertRaisesRegex(Refusal, 'excluded'):
                dep.load(str(self.library), self.pins, [str(self.library)])

    def test_unlisted_provider_import_refuses_without_ambient_fallback(self):
        path = self.library/'retention.py'
        path.write_text('import undeclared_dependency497\n')
        (self.library/'undeclared_dependency497.py').write_text('raise AssertionError("must never execute")\n')
        pins = dep.source_pins(str(self.library), [])
        with patch.dict(sys.modules, {'undeclared_dependency497': SimpleNamespace()}):
            with self.assertRaisesRegex(Refusal, 'outside exact dependency closure'):
                dep.load(str(self.library), pins, [])

    def test_unsupported_retention_lock_signature_refuses_before_entry(self):
        path = self.library/'retention.py'
        path.write_text('def snapshot_lock(unprovided):\n    raise AssertionError("never enter")\n')
        pins = dep.source_pins(str(self.library), [])
        with self.assertRaisesRegex(Refusal, 'zero-argument snapshot_lock interface'):
            dep.load(str(self.library), pins, [])

    def test_publication_wrapper_uses_cooperative_same_inode_and_rechecks_tamper(self):
        lock = self.area/'control/work-rollback.lock'
        with publication.snapshot_lock(self.store):
            inode = lock.stat().st_ino
            with self.assertRaises(BlockingIOError):
                with publication.snapshot_lock(self.store):
                    self.fail('second independent fd acquired a held cooperative lock')
        with publication.snapshot_lock(self.store):
            self.assertEqual(lock.stat().st_ino, inode)
        (self.library/'board_store.py').write_text('raise AssertionError("tampered")\n')
        with self.assertRaisesRegex(Refusal, 'source changed'):
            with publication.snapshot_lock(self.store):
                self.fail('publication entered with a changed dependency')
        self.assertEqual(lock.stat().st_ino, inode)

    def test_compiled_identity_mismatch_refuses_before_lock(self):
        path = self.library/'retention.py'
        path.write_text('__file__ = "/fictional/unselected.py"\n')
        pins = dep.source_pins(str(self.library), [])
        with self.assertRaisesRegex(Refusal, 'compiled retention dependency identity'):
            dep.load(str(self.library), pins, [])

    def draft(self, options=None):
        directory = ROOT/'tools/coordinator-runtime'
        value = {'operator_cli': str(directory/'coordinator'),
                 'canonical_publication': {'method': 'retention-same-inode-v1', 'library': str(self.library)},
                 'tasks': {'source': {'templates': [], 'role': 'Work',
                    'effect_authority': {'operations': ['read-source'], 'read_roots': [str(self.area/'original')], 'write_roots': []}}},
                 'control_receive': {}, 'classifier': {}, 'diagnosis': {}, 'artifact_exclusions': [], 'limits': {}}
        return configuration.candidate(SimpleNamespace(config=value), str(self.area/'operator.json'), [], scope_options=options)

    def test_draft_pins_complete_closure_without_automatic_scope_or_effect_grant(self):
        draft = self.draft()
        self.assertEqual(draft['canonical_publication']['source_pins'], self.pins)
        self.assertEqual(draft['tasks']['source']['effect_authority']['read_roots'], [str(self.area/'original')])
        self.assertEqual(draft['tasks']['source']['effect_authority']['write_roots'], [])
        self.assertEqual(draft['board_library'], str(LIBRARY))

    def test_draft_excludes_before_metadata_and_scope_only_admits_exact_closure(self):
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('no excluded metadata')):
            with self.assertRaisesRegex(Refusal, 'excluded'):
                self.draft({'exclusions': [str(self.library)]})
        reads = [str(self.library/f) for f in dep.FILES]
        self.assertEqual(self.draft({'read_roots': {'source': reads}})['tasks']['source']['effect_authority']['read_roots'], reads)
        for path in (str(self.library), str(self.library/'extra.py'), str(ROOT)):
            with self.assertRaises(Refusal):
                self.draft({'read_roots': {'source': [path]}})

    def test_new_exact_file_scope_does_not_expand_cleanup_or_nonsource_authority(self):
        for change in ('cleanup', 'reports'):
            draft = self.draft()
            task = draft['tasks']['source']
            if change == 'cleanup':
                task['phase'] = 'cleanup'
            else:
                task['effect_authority']['operations'] = ['read-reports']
            with self.assertRaises(Refusal):
                configuration.apply_scope_options(copy.deepcopy(draft), draft,
                    {'read_roots': {'source': [str(self.library/'board_store.py')]}})
        with self.assertRaises(Refusal):
            self.draft([])

    def test_release_manifest_contains_all_closure_files_and_rejects_stale_pin(self):
        candidate = self.draft()
        directory = ROOT/'tools/coordinator-runtime'
        candidate.update(control_receive={'instructions': str(directory/'templates/coordinator-receive.md')},
                         execution_pool_routes=str(self.area/'routes.toml'))
        Path(candidate['execution_pool_routes']).write_text('fictional public pool control')
        Path(candidate['operator_config']).write_text(json.dumps(candidate))
        # Only fictional pool read/control data. No real allocation/settings IO.
        pool = SimpleNamespace(read=lambda: (b'fictional', [], self.area/'unused'),
                               control_binding=lambda raw: {'fictional': True})
        with patch('coordinator_runtime.execution_pool._module.Pool', return_value=pool):
            manifest = configuration.release(None, candidate)
        for name in dep.FILES:
            self.assertEqual(manifest['files'][str(self.library/name)], self.pins[name])
        (self.library/'active_listener.py').write_text('VALUE = "changed"\n')
        with self.assertRaisesRegex(Refusal, 'source changed'):
            configuration.release(None, candidate)


if __name__ == '__main__':
    unittest.main(verbosity=2)
