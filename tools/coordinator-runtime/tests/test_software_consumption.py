"""Offline prospective grant/consumer boundary, not four-role live qualification.

Every process is the owned fake app-server. It is NOT Luna/Sol, the opaque
selected-review launcher, Branch ref execution or QA CI. No deletion is run.
Require an explicitly owned absolute fixture root; retain all outputs.
"""
from contextlib import contextmanager
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from support import config_at, event, result
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode, ident, validate_config
from coordinator_runtime.dispatcher import Dispatcher, CLASSIFICATION_SCHEMA, classifier_prompt
from coordinator_runtime.store import Store


@contextmanager
def fixture_actor(substrate, actor):
    """Explicit synthetic authentication seam, never a session environment."""
    def acting(expected):
        if expected != actor:
            raise substrate.UserError('fictional actor differs from requested fixture authority')
        return actor
    with patch.object(substrate, 'acting_session', side_effect=acting):
        yield


class SoftwareConsumption(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        base = Path(os.environ['COORDINATOR_NORMAL_PATH_FIXTURES'])
        if (not base.is_absolute() or 'normal-path27-act' not in base.parts
                or base.is_symlink()
                or not Path(os.environ['TMPDIR']).is_relative_to(base)):
            raise AssertionError('owned absolute normal-path27-act fixture root/TMPDIR required')
        self.area = base / self._testMethodName / ident()
        self.area.mkdir(parents=True, mode=0o700)
        self.config = config_at(str(self.area))
        shared = self.config['roles']['Work']['board_id']
        for selected in self.config['roles'].values():
            selected['board_id'] = shared
        self.config['software_delegation'] = {'grantor': self.config['roles']['Work']['owner'],
            'authority': 'Synthetic user -> Work Decision27 fixture; no live authority', 'boundary': 'new-journal-only'}
        self.config['delivery'] = {'recipients': {r: {'session': v['owner'], 'profile': v['profile'], 'board_role': v['board_role']}
                                               for r, v in self.config['roles'].items()}}
        for task in self.config['tasks'].values():
            task.update(delivery_required=True, allowed_handoffs=list(self.config['roles']))
        # Explicit receiving intent, distinct from allowed native notification.
        for name, receiver in [('work-integrator', 'Branch'), ('branch-integrator', 'QA'),
                               ('reviews-integrator', 'Work'), ('qa-cleanup', 'Branch')]:
            self.config['tasks'][name]['software_handoffs'] = {receiver: [
                'qa-execution' if receiver == 'QA' else receiver.lower() + '-proposer']}
        self.config['tasks']['reviews-integrator']['publish_internal_results'] = True
        validate_config(self.config)
        self.substrate = module_at(self.config['board_library'], 'board_store')
        catalog = module_at(self.config['board_library'], 'catalog')
        home = Path(self.config['board_home'])
        with catalog.catalog(home) as cat:
            entry = catalog.create(cat, home, 'software-fixture', 'Owned offline consumption fixture',
                                   board_id=shared, temporary_test=True)
        self.path = Path(entry['db_path'])
        with self.substrate.database(str(self.path)) as conn:
            self.substrate.bind_board(conn, shared, initialize=True)
            for selected in self.config['roles'].values():
                args = self.substrate.parser().parse_args(['register', '--session', selected['owner'],
                    '--role', selected['board_role'], '--route', 'managed', '--profile', selected['profile']])
                with fixture_actor(self.substrate, selected['owner']):
                    self.substrate.register(conn, args)
        self.store = Store(self.config)
        self.addCleanup(self.store.close)  # Close only; all fixture evidence retained.
        self.boards = {role: Board(self.config, role) for role in self.config['roles']}
        for role, board in self.boards.items():
            with fixture_actor(board.store, self.config['software_delegation']['grantor']):
                grant = board.grant_software(self.store, self.config['software_delegation']['authority'])
            self.store.enroll(role, grant)
            self.store.reconcile_legacy(role, self.config['roles'][role]['owner'],
                {'collector': 'Synthetic fixture custodian', 'evidence': ['No legacy work in this fixture'], 'remaining_holds': []})
        self.runtime = Dispatcher(self.store, models=object(), boards=self.boards)
        self.ends = []

    def adapter(self, plan):
        path = self.area / (ident() + '-fake-process.json')
        path.write_text(encode(plan))
        return AppServer(self.config, [sys.executable, str(Path(__file__).with_name('fixture_appserver.py')), str(path)])

    async def classify(self):
        while claimed := self.store.claim_classification():
            attempt, message = claimed
            answer = {'event_id': message['id'], 'task': message['allowed_tasks'][0],
                      'package': message['package'], 'reason': 'Synthetic routing fixture, no model claim'}
            adapter = self.adapter({'result': answer})
            outcome = await adapter.run(self.store, attempt, classifier_prompt(message, self.config),
                {'cwd': str(self.area), 'sandbox': 'read-only'}, CLASSIFICATION_SCHEMA)
            self.assertEqual(outcome['exit'], 0)
            self.ends.append({'attempt': attempt, 'actual_owned_END': outcome['exit'], 'kind': 'fake-classifier'})
            self.store.collect(attempt, outcome)
            self.store.commit_classification(attempt)
        self.runtime.receipts()

    async def task(self, job, answer=None, extra=None):
        answer = answer or {**result(), 'handoffs': [], 'no_handoff_reason': 'Fixture collector owns this local result'}
        self.runtime.models = self.adapter({'result': answer, **(extra or {})})
        attempt = self.store.start_job(job['id'], job['token'])
        await self.runtime.execute(job['id'], attempt)
        row = self.store.attempt(attempt)
        self.assertEqual(row['exit'], 0)
        self.ends.append({'attempt': attempt, 'actual_owned_END': row['exit'], 'kind': 'fake-task'})
        return attempt

    async def sender(self, role, recipient, phase='integrator', package='fixture-package', category='complete', kind='work'):
        task = role.lower() + '-' + phase
        if role == 'QA' or recipient == 'QA':
            self.store.admit(package, self.config['roles']['Branch']['owner'],
                             {'fixture': 'Independent synthetic resource owner admission'}, accepted={'fixture': 'accepted'})
        source = event(self.config, ident(), role=role, task=task, package=package)
        self.store.ingest(source)
        await self.classify()
        job = self.store.reserve()
        self.assertEqual(job['task'], task)
        answer = {**result(category=category), 'handoffs': [{'recipient': recipient, 'kind': kind, 'ref': package,
                   'required': 'settled', 'text': 'Bounded synthetic next-stage work'}]}
        await self.task(job, answer)
        await self.classify()
        self.runtime.pump_deliveries()
        # The ordinary board scanner must not also turn this posted handoff
        # into a second job alongside its durable software receiver intent.
        before = self.store.rows('SELECT id,hash FROM events ORDER BY id')
        self.runtime.intake()
        self.assertEqual(self.store.rows('SELECT id,hash FROM events ORDER BY id'), before)
        return source, job, self.store.one('SELECT * FROM outboxes WHERE job=? AND recipient=?', (job['id'], recipient))

    async def consume(self):
        await self.classify()
        self.runtime.pump_deliveries()
        consumer = self.store.reserve()
        self.assertIsNotNone(consumer)
        await self.task(consumer)
        await self.classify()
        self.runtime.pump_deliveries()
        self.runtime.reconcile_completed()
        return consumer

    async def asyncTearDown(self):
        (self.area / 'process-ends.json').write_text(encode(self.ends) + '\n')

    async def test_four_role_consumer_seams_require_actual_processing_not_enqueue(self):
        # These exercise each role's software HANDOFF, not its business procedure.
        for role, recipient, phase in [('Work', 'Branch', 'integrator'), ('Branch', 'QA', 'integrator'),
                                       ('Reviews', 'Work', 'integrator'), ('QA', 'Branch', 'cleanup')]:
            with self.subTest(role=role):
                source, sender, outgoing = await self.sender(role, recipient, phase, package=ident())
                board = self.boards[role]
                posted = board.delivery_status(outgoing['id'])
                self.assertIsNone(posted['processed_at'])
                self.assertNotEqual(posted['state'], 'settled')
                self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (source['id'],))['processed_at'])
                consumer = await self.consume()
                final = board.delivery_status(outgoing['id'])
                self.assertEqual(final['state'], 'settled')
                self.assertEqual(final['settlement']['consumer_job'], consumer['id'])
                self.assertEqual(final['settlement']['processing']['actual_end'], 0)
                self.assertEqual(final['settlement']['issued_by'], self.config['roles']['Work']['owner'])
                self.assertFalse(final['control_receipt']['required'])
                self.assertFalse(final['settlement']['native_receipt'])
                self.assertEqual(self.store.job(sender['id'])['state'], 'closed')
                processed = self.store.one('SELECT processed_at FROM events WHERE id=?', (source['id'],))['processed_at']
                self.assertIsNotNone(processed)
                self.assertEqual(self.store.recover_source(source['id']), source)

    async def test_work_software_grant_preserves_seven_target_publication(self):
        # Recreate only the still-unused owned journal with a seven-file policy.
        self.store.close()
        self.config['state_dir'] = str(self.area / 'seven-target-state')
        self.config['actor'] = ident()  # New journal has a new actor; never steal old service membership.
        task = self.config['tasks']['work-integrator']
        targets = [self.area / ('canonical-' + str(n) + '.json') for n in range(7)]
        for target in targets:
            target.write_text('{"total":0}')
        inodes = [p.stat().st_ino for p in targets]
        task.update(effects='owner-reconcile', sandbox='workspace-write', network=False,
                    routine_completion={'kind': 'file-witness', 'targets': [str(p) for p in targets]})
        task['effect_authority'].update(write_roots=[str(p) for p in targets], operations=['read-reports', 'write-role-records'])
        self.store = Store(validate_config(self.config))
        self.addCleanup(self.store.close)
        for role, board in self.boards.items():
            with fixture_actor(board.store, self.config['roles']['Work']['owner']):
                grant = board.grant_software(self.store, self.config['software_delegation']['authority'])
            self.store.enroll(role, grant)
            self.store.reconcile_legacy(role, self.config['roles'][role]['owner'],
                {'collector': 'fixture', 'evidence': ['No old fixture work'], 'remaining_holds': []})
        self.runtime = Dispatcher(self.store, models=object(), boards=self.boards)
        self.store.ingest(event(self.config, ident()))
        await self.classify()
        job = self.store.reserve()
        await self.task(job, extra={'target': str(targets[0]), 'completion_mode': 'auto', 'tool_metadata': {'exitCode': 0}})
        self.assertEqual(self.store.job(job['id'])['effects'], 'reconciled')
        self.assertEqual([p.stat().st_ino for p in targets], inodes)
        self.assertEqual({r['target'] for r in self.store.rows('SELECT * FROM file_publications')}, {str(p) for p in targets})
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(receipt['delegated_by'], self.config['roles']['Work']['owner'])
        self.assertEqual(len(receipt['before']), 7)
        await self.classify()
        self.runtime.pump_deliveries()
        self.runtime.reconcile_completed()
        self.assertEqual(self.store.job(job['id'])['state'], 'closed')

    async def test_native_pending_duty_is_not_settled_by_software_processing(self):
        source, sender, outgoing = await self.sender('Reviews', 'Work')
        board = self.boards['Reviews']
        with board.opened() as conn:
            from coordinator_runtime.automatic_control import SCHEMA
            conn.executescript(SCHEMA)
            board.require_control(conn, outgoing['id'])
        with patch.object(board, 'automatic_control', side_effect=AssertionError('new routine native duty minted')):
            await self.consume()
        status = board.delivery_status(outgoing['id'])
        self.assertEqual(status['state'], 'settled')
        self.assertTrue(status['control_receipt']['pending'])
        self.assertIsNone(status['processed_at'])
        self.assertFalse(self.store.delivery_satisfied(self.store.one('SELECT * FROM outboxes WHERE id=?', (outgoing['id'],))))
        self.assertNotEqual(self.store.job(sender['id'])['state'], 'closed')
        self.assertTrue(self.store.dependency_hold(source['id']))

    async def test_unknown_and_inflight_native_sends_keep_original_custody(self):
        source, sender, outgoing = await self.sender('Reviews', 'Work')
        board = self.boards['Reviews']
        from coordinator_runtime.owner_control import SCHEMA
        with board.opened() as conn:
            conn.executescript(SCHEMA)
            board.require_control(conn, outgoing['id'])
            conn.execute('INSERT INTO coordinator_controls_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (ident(), outgoing['id'], self.config['actor'], self.config['roles']['Work']['owner'],
                 '.codex', 'queue-existing', digest('Synthetic pointer'), '{}', ident(), ident(),
                 'Synthetic retained pointer, never sent', 'unknown', encode({'status': 'unknown'}), self.store.clock()))
            original = dict(conn.execute('SELECT * FROM coordinator_controls_v1').fetchone())
        await self.consume()
        for state in ('unknown', 'inflight'):
            with board.opened() as conn:
                conn.execute('UPDATE coordinator_controls_v1 SET state=? WHERE id=?', (state, original['id']))
            self.runtime.pump_deliveries()
            status = board.delivery_status(outgoing['id'])
            self.assertTrue(status['control_receipt']['pending'])
            self.assertTrue(status['control_receipt']['unresolved_send'])
            self.assertIsNone(status['processed_at'])
            with board.opened() as conn:
                actual = dict(conn.execute('SELECT * FROM coordinator_controls_v1').fetchone())
            self.assertEqual(actual, {**original, 'state': state})
        self.assertEqual(self.store.recover_source(source['id']), source)
        self.assertNotEqual(self.store.job(sender['id'])['state'], 'closed')

    async def test_receiver_unknown_effects_and_changed_admission_prevent_settlement(self):
        _, _, outgoing = await self.sender('Branch', 'QA')
        await self.classify()
        consumer = self.store.reserve()
        await self.task(consumer)
        self.store.db.execute("UPDATE jobs SET effects='unknown' WHERE id=?", (consumer['id'],))
        self.runtime.pump_deliveries()
        self.assertIsNone(self.boards['Branch'].delivery_status(outgoing['id'])['processed_at'])
        self.store.db.execute("UPDATE jobs SET effects='none' WHERE id=?", (consumer['id'],))
        self.store.admit(consumer['package'], self.config['roles']['Branch']['owner'], {'fixture': 'Changed admission'})
        self.runtime.pump_deliveries()
        self.assertIsNone(self.boards['Branch'].delivery_status(outgoing['id'])['processed_at'])
        self.assertIn('admission', self.store.one('SELECT error FROM outboxes WHERE id=?', (outgoing['id'],))['error'])

    async def test_incomplete_tool_capture_never_falls_through_to_old_callback(self):
        self.store.ingest(event(self.config, ident(), role='Branch', task='branch-proposer'))
        await self.classify()
        job = self.store.reserve()
        await self.task(job, {**result(category='proposal'), 'handoffs': [], 'no_handoff_reason': 'Synthetic internal result'},
                        extra={'tool_metadata': {'exitCode': None}})
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertIn('tool capture', self.store.job(job['id'])['hold_reason'])
        self.assertFalse(self.store.one("SELECT id FROM events WHERE json_extract(payload,'$.source_job')=? AND json_extract(payload,'$.kind')='response'", (job['id'],)))
        await self.classify()
        self.runtime.pump_deliveries()
        for outbox in self.store.rows('SELECT * FROM outboxes WHERE job=?', (job['id'],)):
            self.assertFalse(self.store.delivery_satisfied(outbox))

    async def test_retries_reuse_one_receiver_and_original_source(self):
        _, _, outgoing = await self.sender('Work', 'Branch')
        intent = self.boards['Work']
        with intent.opened() as conn:
            saved = dict(conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (outgoing['id'],)).fetchone())
        for _ in range(3):
            self.runtime.pump_deliveries()
        self.assertEqual(self.store.event(saved['event']), json.loads(saved['payload']))
        consumer = await self.consume()
        for _ in range(3):
            self.runtime.pump_deliveries()
        self.assertEqual(len(self.store.rows('SELECT * FROM queue WHERE event=?', (saved['event'],))), 1)
        self.assertEqual(len(self.store.rows('SELECT * FROM attempts WHERE job=?', (consumer['id'],))), 1)

    async def test_published_response_and_result_handoff_share_one_real_consumer(self):
        # Update before any work/grants using a separate synthetic journal/actor.
        # The grants are intentionally pinned; changed selection must be refused.
        task = self.config['tasks']['reviews-integrator']
        old = task.get('publish_internal_results')
        task['publish_internal_results'] = False
        with self.assertRaisesRegex(Refusal, 'authority absent or changed'):
            self.boards['Reviews'].software_authority(self.store, 'reviews-integrator')
        if old is None:
            del task['publish_internal_results']
        else:
            task['publish_internal_results'] = old
        source, sender, _ = await self.sender('Reviews', 'Work', category='consolidated', kind='result')
        response = self.store.job(sender['id'])['response']
        with self.boards['Reviews'].opened() as conn:
            intents = [dict(r) for r in conn.execute('SELECT * FROM coordinator_software_deliveries_v1')]
        self.assertEqual(len(intents), 2)
        self.assertEqual({item['event'] for item in intents}, {response})
        consumer = await self.consume()
        self.assertEqual(len([j for j in self.store.rows('SELECT * FROM jobs')
                              if any(m['event'] == response for m in json.loads(j['members']))]), 1)
        self.assertEqual(self.store.job(sender['id'])['state'], 'closed')
        self.assertIsNotNone(consumer['active_attempt'] if consumer.get('active_attempt') else self.store.job(consumer['id'])['active_attempt'])
        self.assertEqual(self.store.recover_source(source['id']), source)

    async def test_questions_still_reach_the_persistent_exception_path(self):
        self.store.ingest(event(self.config, ident(), role='Reviews', task='reviews-integrator'))
        await self.classify()
        sender = self.store.reserve()
        await self.task(sender, {**result(), 'handoffs': [{'recipient': 'Work', 'kind': 'question',
            'ref': 'fixture exception', 'text': 'Actual consequential question, not routine work', 'required': 'settled'}]})
        await self.classify()
        original = self.boards['Reviews'].automatic_control
        with patch.object(self.boards['Reviews'], 'automatic_control', wraps=original) as control:
            self.runtime.pump_deliveries()
        question = self.store.one("SELECT * FROM outboxes WHERE kind='question'")
        self.assertTrue(any(call.args[1]['id'] == question['id'] for call in control.call_args_list))
        self.assertIsNone(self.boards['Reviews'].delivery_status(question['id'])['processed_at'])
        self.assertFalse(self.store.one("SELECT id FROM events WHERE json_extract(payload,'$.source_delivery.id')=?", (question['id'],)))

    async def test_revoked_receiver_grant_retains_sender_source_and_pending_delivery(self):
        source, sender, outgoing = await self.sender('Work', 'Branch')
        board = self.boards['Branch']
        with fixture_actor(board.store, self.config['roles']['Branch']['owner']):
            board.revoke(self.store.enrollment('Branch')['grant_id'])
        self.runtime.pump_deliveries()
        self.assertIn('revoked', self.store.one('SELECT error FROM outboxes WHERE id=?', (outgoing['id'],))['error'])
        self.assertNotEqual(self.store.job(sender['id'])['state'], 'closed')
        self.assertEqual(self.store.recover_source(source['id']), source)

    async def test_actual_work_can_revoke_its_software_capability_without_native_impersonation(self):
        board = self.boards['Branch']
        grant = self.store.enrollment('Branch')['grant_id']
        with fixture_actor(board.store, self.config['roles']['Work']['owner']):
            receipt = board.revoke_software(self.store, grant)
        self.assertEqual(receipt['issued_by'], self.config['roles']['Work']['owner'])
        with self.assertRaisesRegex(Refusal, 'revoked'):
            board.software_authority(self.store, 'branch-integrator')

    async def test_QA_five_execution_one_cleanup_and_single_integrator_batch(self):
        for n in range(6):
            package = 'qa-package-' + str(n)
            self.store.admit(package, self.config['roles']['Branch']['owner'], {'fixture': package})
            self.store.ingest(event(self.config, ident(), role='QA', task='qa-execution', package=package))
        await self.classify()
        reserved = [self.store.reserve() for _ in range(5)]
        self.assertTrue(all(job and job['phase'] == 'execution' for job in reserved))
        self.assertIsNone(self.store.reserve())
        for job in reserved[:2]:
            self.store.ingest(event(self.config, ident(), role='QA', task='qa-cleanup', package=job['package']))
        await self.classify()
        cleanup = self.store.reserve()
        self.assertEqual(cleanup['phase'], 'cleanup')
        self.assertEqual(len(json.loads(cleanup['members'])), 1)
        self.assertIsNone(self.store.reserve())
        for _ in range(2):
            self.store.ingest(event(self.config, ident(), role='Work', task='work-integrator'))
        await self.classify()
        batch = self.store.reserve()
        self.assertEqual(len(json.loads(batch['members'])), 2)
        self.store.ingest(event(self.config, ident(), role='Work', task='work-integrator'))
        await self.classify()
        self.assertIsNone(self.store.reserve())

    async def test_selected_review_remains_an_explicit_capability_gap(self):
        selected = copy.deepcopy(self.config)
        task = selected['tasks']['reviews-proposer']
        task.update(execution='instance', binding={'model': 'gpt-xhigh', 'provider': 'opaque', 'effort': 'opaque'})
        with self.assertRaisesRegex(Refusal, 'unsupported effort'):
            validate_config(selected)
        task['execution'] = 'owner'
        validate_config(selected)  # Compatibility only, still NOT an instanced route.
        self.assertEqual(task['binding']['model'], 'gpt-xhigh')

    async def test_prospective_grantor_is_actual_work_not_native_owner(self):
        board = self.boards['Branch']
        grant = board.verify_authority(self.store)
        self.assertEqual(grant['issued_by'], self.config['roles']['Work']['owner'])
        self.assertEqual(grant['owner'], self.config['roles']['Branch']['owner'])
        self.assertNotEqual(grant['owner'], grant['issued_by'])
        with fixture_actor(board.store, grant['owner']):
            with self.assertRaises(Exception):
                board.grant_software(self.store, self.config['software_delegation']['authority'])
        with fixture_actor(board.store, grant['issued_by']):
            with self.assertRaisesRegex(Refusal, 'unused journal'):
                board.grant_software(self.store, self.config['software_delegation']['authority'])

    async def test_old_native_grant_and_configuration_epoch_are_not_migrated(self):
        old_config = copy.deepcopy(self.config)
        old_config.pop('software_delegation')
        for task in old_config['tasks'].values():
            task.pop('software_handoffs', None)
        old_config['state_dir'] = str(self.area / 'old-native-journal')
        old_config['actor'] = ident()
        old = Store(validate_config(old_config))
        self.addCleanup(old.close)
        native = Board(old_config, 'Reviews')
        owner = old_config['roles']['Reviews']['owner']
        with fixture_actor(native.store, owner):
            grant = native.grant(old, 'Synthetic old native owner authority', delivery=True, completion=True)
        old.enroll('Reviews', grant)
        old.ingest(event(old_config, ident(), role='Reviews', task='reviews-proposer'))
        before = old.rows('SELECT * FROM events')
        with native.opened() as conn:
            native_grant = dict(conn.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?', (grant['id'],)).fetchone())
        with self.assertRaisesRegex(Refusal, 'configuration differs'):
            Store({**self.config, 'state_dir': old_config['state_dir']})
        self.assertEqual(old.rows('SELECT * FROM events'), before)
        with native.opened() as conn:
            self.assertEqual(dict(conn.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?', (grant['id'],)).fetchone()), native_grant)
        self.assertEqual(native_grant['issued_by'], owner)


if __name__ == '__main__':
    unittest.main()
