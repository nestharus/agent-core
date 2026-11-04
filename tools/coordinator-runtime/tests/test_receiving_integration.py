"""Combined22/23 construction witnesses, using owned journals and fixture boards.

CLI identity verification, service END assertions, models and queue helper are
explicit seams. No native/provider/live service or real receiving is exercised.
"""
import asyncio
import json
import os
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import test_collector_continuity as collector
import test_continuing as continuing
import test_control_recovery as controls
import test_driver_progress as progress
import test_live_recovery as recovery
from support import collect, event, queued, result
from test_board_dispatch import FakeModels
from coordinator_runtime.contracts import LUNA, Refusal, encode
from coordinator_runtime.dispatcher import DELIVERY_PAGE, Dispatcher, job_prompt
from coordinator_runtime.store import Store


class ReceivingIntegration(unittest.IsolatedAsyncioTestCase):
    held = recovery.OwnerRecovery.held
    request = recovery.OwnerRecovery.request
    receipt = collector.CollectorContinuity.receipt
    reaffirm = collector.CollectorContinuity.reaffirm
    continuity = collector.CollectorContinuity.continuity
    owner_cli = collector.CollectorContinuity.owner_cli
    policy = controls.AutomaticControls.policy
    delegate = controls.AutomaticControls.delegate
    helper = controls.AutomaticControls.helper
    delivery = controls.AutomaticControls.delivery

    async def asyncSetUp(self):
        original_config = continuing.config_at

        def config_at(path):
            config = original_config(path)
            config['limits']['max_outboxes'] = 40000
            config['roles']['Work']['routes'] = ['work-integrator', 'work-proposer']
            return config

        with patch.object(continuing, 'config_at', side_effect=config_at):
            controls.AutomaticControls.setUp(self)
        self.owner = self.config['roles']['Work']['owner']
        self.job, self.original = self.held({**result(), 'handoffs': [],
            'no_handoff_reason': 'Synthetic original held for explicit owner disposition'})
        self.store.reconcile_effects(self.job['id'], self.job['token'], self.owner,
            {'evidence': ['Owned fixture effects accounted; publication duties independent'], 'unknown_effects': []})
        self.store.claim_recovery(self.job['id'])
        failed = self.store.diagnosis_attempt(self.job['id'])
        collect(self.store, failed, None, error='Historical synthetic turn error')
        self.runtime.advance_recovery(self.job['id'], failed)
        self.original_collector = self.store.controller
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.store.adopt_collected(self.job['id'])
        self.runtime = Dispatcher(self.store, models=object(), boards=self.boards)
        self.selection = self.request(self.job, self.original, 'remaining-work',
            remaining='Same job peer-compatible remainder; conserve original reports, duties and current peers')
        self.store.consume_recovery_request(self.selection['id'])
        self.diagnosis = self.store.diagnosis_attempt(self.job['id'])
        self.choice = {'profile': '.codex3', 'remaining': 'Same target with fresh peer preimages; no old-stage replay',
            'rationale': 'Preserve owner-selected continuity while independent publication and consumer duties remain'}
        collect(self.store, self.diagnosis, self.choice, binding_readback=LUNA, root_identity_observed=True)
        self.store.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?", (self.job['id'],))

    async def restart_with_history(self):
        # Real older control duty plus a large ineligible tail. Neither hints nor
        # traversal may erase holds or promote any of it to processed work.
        self.delegate(self.policy('Work'))
        old_control = self.store.one("SELECT id FROM outboxes WHERE kind='question'")['id']
        old = progress.retained(self.store, 25712, state='classification-pending')
        await collector.CollectorContinuity.restart(self)
        self.runtime.boards = self.boards
        self.runtime.models = FakeModels()
        self.assertEqual(self.store.db.execute('PRAGMA user_version').fetchone()[0], 1)
        return old_control, old

    def queue_owner_cli(self):
        view, cli_controller = self.owner_cli(['owner-controls', 'Work', '--limit', '100'])
        self.assertEqual(view['recovery'][0]['controller'], self.previous)
        self.assertNotIn(cli_controller, {self.previous, self.store.controller})
        path = Path(self.temp.name) / 'combined-continuity.json'
        path.write_text(encode(self.receipt(collector_continuity=self.continuity())))
        argv = ['request-recovery', self.job['id'], '--token', self.job['token'],
                '--attempt', self.original, '--receipt', str(path)]
        request, _ = self.owner_cli(argv)
        self.assertEqual(self.owner_cli(argv)[0], request)
        self.assertEqual(self.store.job(self.job['id']), self.before)
        return request

    async def tick(self):
        await self.runtime.tick()
        if self.runtime.active:
            await asyncio.gather(*self.runtime.active)

    def request_state(self, request):
        return self.store.one('SELECT * FROM recovery_requests WHERE id=?', (request['id'],))

    def assert_originals(self):
        self.assertEqual(self.store.attempt(self.original), self.original_raw)
        self.assertEqual(self.store.attempt(self.diagnosis), self.diagnosis_raw)
        self.assertEqual(self.request_state(self.selection), self.selection_raw)
        current = self.store.job(self.job['id'])
        self.assertEqual(current['token'], self.before['token'])
        self.assertEqual(current['members'], self.before['members'])
        self.assertEqual(current['recovery_owner'], self.previous)

    async def test_owner_cli_continuity_fresh_ACK_and_both_control_lanes_share_a_tick(self):
        old_control, old = await self.restart_with_history()
        request = self.queue_owner_cli()
        fresh_control = self.delivery(recipient='Work')
        sender = self.config['roles']['Branch']['owner']
        args = self.substrate.parser().parse_args(['open', '--session', sender,
            '--topic', 'combined', '--kind', 'finding', '--title', 'Fresh intake',
            '--text', 'Fresh same-role responsibility remains queued behind held integrator',
            '--to', self.owner, '--no-push'])
        with self.substrate.database(str(self.path)) as conn, patch.dict(os.environ, {'CODEX_SESSION_ID': sender}):
            self.substrate.open_thread(conn, args)
        self.assertTrue(self.boards['Work'].scan(self.store))
        pages, allocation_seen_before_pump = [], []
        rows = self.store.rows

        def observe(sql, values=()):
            found = rows(sql, values)
            if 'AS delivery_seq' in sql:
                pages.append(len(found))
                allocation_seen_before_pump.append(self.request_state(request)['state'])
            return found

        calls = []
        with patch.object(self.store, 'rows', side_effect=observe), patch(
                'coordinator_runtime.owner_control.load_helper', return_value=self.helper(calls, status='ambiguous', qid=False)):
            for _ in range(4):
                await self.tick()
        self.assertTrue(pages)
        self.assertLessEqual(max(pages), DELIVERY_PAGE)
        self.assertEqual(set(allocation_seen_before_pump), {'consumed'})
        self.assertLess(self.runtime.delivery_revisit, len(old))
        self.runtime.execute.assert_awaited_once()
        self.runtime.recover.assert_not_called()
        current = self.store.job(self.job['id'])
        self.assertEqual(self.runtime.execute.await_args.args, (current['id'], current['active_attempt']))
        self.assert_originals()
        self.assertIn(self.choice['remaining'], job_prompt(self.store, current))
        self.assertIn(self.choice['rationale'], job_prompt(self.store, current))
        audit = json.loads(self.request_state(request)['result'])['collector_continuity']
        self.assertNotEqual(audit['before_witness']['closure_hash'], audit['after_witness']['closure_hash'])
        self.assertEqual({k: v for k, v in audit['before_witness'].items() if k != 'closure_hash'},
                         {k: v for k, v in audit['after_witness'].items() if k != 'closure_hash'})
        fresh = self.store.one("SELECT * FROM events WHERE json_extract(payload,'$.kind')='board'")
        self.assertEqual(fresh['ack'], 'done')
        self.assertTrue(fresh['classification'])
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?', (fresh['id'],))['state'], 'queued')
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')), 1)
        with self.substrate.database(str(self.path)) as conn:
            attempted = [dict(row) for row in conn.execute("SELECT * FROM coordinator_controls_v1 WHERE state='unknown'")]
        self.assertEqual({row['delivery'] for row in attempted}, {old_control, fresh_control})
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(self.boards['Work'].delivery_status(key)['control_receipt']['pending']
                            for key in (old_control, fresh_control)))
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM outboxes WHERE hold='independent source/effect hold' AND processed_at IS NULL")['n'], len(old))

    async def test_currentness_source_and_unrelated_holds_refuse_without_old_result_fallthrough(self):
        await self.restart_with_history()
        request = self.queue_owner_cli()
        source = json.loads(self.before['members'])[0]['event']
        raw = self.diagnosis_raw['result']
        changes = [('attempts', 'result', encode({**self.choice, 'rationale': 'New meaning after owner read'}), self.diagnosis, raw),
                   ('jobs', 'hold_reason', 'Independent custodian hold', self.job['id'], self.before['hold_reason']),
                   ('events', 'hold', 'Actual source hold', source, None)]
        with patch.object(self.boards['Work'], 'verify_authority', side_effect=Refusal('Owned current grant revoked')):
            await self.tick()
        self.assertEqual(self.store.job(self.job['id']), self.before)
        self.assertEqual(self.request_state(request)['state'], 'pending')
        self.runtime.execute.assert_not_called()
        with patch('coordinator_runtime.owner_control.load_helper', return_value=self.helper([], status='ambiguous', qid=False)):
            for table, field, value, key, previous in changes:
                with self.subTest(field=field):
                    self.store.db.execute(f'UPDATE {table} SET {field}=? WHERE id=?', (value, key))
                    expected = self.store.job(self.job['id'])
                    await self.tick()
                    self.assertEqual(self.store.job(self.job['id']), expected)
                    self.assertEqual(self.request_state(request)['state'], 'pending')
                    self.runtime.execute.assert_not_called()
                    self.store.db.execute(f'UPDATE {table} SET {field}=? WHERE id=?', (previous, key))
            await self.tick()
        self.runtime.execute.assert_awaited_once()
        self.assert_originals()

    async def test_allocation_rollback_keeps_custody_while_fresh_control_gets_an_opportunity(self):
        await self.restart_with_history()
        request = self.queue_owner_cli()
        fresh = self.delivery(recipient='Work')
        calls = []
        allocate = self.store._attempt

        def refuse_successor(kind, event_id, job_id, *args, **kwargs):
            if kind == 'task' and job_id == self.job['id']:
                raise Refusal('Owned allocation capacity refusal')
            return allocate(kind, event_id, job_id, *args, **kwargs)

        with patch.object(self.store, '_attempt', side_effect=refuse_successor), patch(
                'coordinator_runtime.owner_control.load_helper', return_value=self.helper(calls, status='ambiguous', qid=False)):
            await self.tick()
        self.assertEqual(self.store.job(self.job['id']), self.before)
        self.assertEqual(self.request_state(request)['state'], 'pending')
        self.assertEqual(json.loads(self.request_state(request)['result'])['retained_diagnosis']['closure_hash'],
                         self.store.retained_diagnosis_witness(self.before, self.receipt(), request=request['id'])['closure_hash'])
        self.runtime.execute.assert_not_called()
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT state FROM coordinator_controls_v1 WHERE delivery=?', (fresh,)).fetchone()[0], 'unknown')
        with patch('coordinator_runtime.owner_control.load_helper', return_value=self.helper(calls, status='ambiguous', qid=False)):
            await self.tick()
        self.runtime.execute.assert_awaited_once()
        self.assert_originals()

    async def test_postallocation_prespawn_unknown_stays_with_actual_custodian_across_later_ticks(self):
        await self.restart_with_history()
        request = self.queue_owner_cli()
        queued(self.store, event(self.config, 'next-batch'))

        def interrupted(coroutine):
            coroutine.close()
            raise OSError('Owned injection after committed allocation before spawn')

        with patch.object(self.runtime, 'spawn', side_effect=interrupted), patch(
                'coordinator_runtime.owner_control.load_helper', return_value=self.helper([], status='ambiguous', qid=False)):
            await self.tick()
        current = self.store.job(self.job['id'])
        reserved = self.store.attempt(current['active_attempt'])
        self.assertEqual(self.request_state(request)['state'], 'consumed')
        for field in ('begin', 'ended', 'exit', 'collected'):
            self.assertIsNone(reserved[field])
        self.assertEqual(reserved['controller'], self.store.controller)
        other = Store(self.config)
        self.addCleanup(other.close)
        later = Dispatcher(other, models=object(), boards=self.boards)
        later.execute = AsyncMock()
        later.recover = AsyncMock()
        with patch('coordinator_runtime.owner_control.load_helper', return_value=self.helper([], status='ambiguous', qid=False)):
            for _ in range(3):
                await later.tick()
        later.execute.assert_not_called()
        later.recover.assert_not_called()
        self.assertEqual(other.attempt(reserved['id']), reserved)
        self.assertFalse(other.execution_complete(other.job(current['id'])))
        self.assertIsNone(other.reserve())
        self.assertEqual(len(other.rows('SELECT * FROM jobs')), 1)
        self.assert_originals()

    async def test_supplied_receipt_survives_bounded_passes_while_continuity_is_held(self):
        await self.restart_with_history()
        request = self.queue_owner_cli()
        self.store.set_hold(json.loads(self.before['members'])[0]['event'], 'Independent source remains held')
        fresh = self.delivery(recipient='Work')
        calls = []
        with patch('coordinator_runtime.owner_control.load_helper', return_value=self.helper(calls)):
            await self.tick()
        with self.substrate.database(str(self.path)) as conn:
            record = dict(conn.execute('SELECT * FROM coordinator_controls_v1 WHERE delivery=?', (fresh,)).fetchone())
        qid = json.loads(record['result'])['queue_message_id']
        supplied = {'evidence': [{'source': 'Owned synthetic full read', 'full_read': record['payload_hash']}],
            'disposition': {'action': 'Control only', 'remaining': ['Independent source/effect duties']},
            'transport': {'queue_message_id': qid, 'state': 'processed', 'evidence': ['Exact synthetic consumer receipt']}}
        board = self.boards['Work']
        with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
            got = board.control_receipt(fresh, supplied)
            with self.assertRaisesRegex(Refusal, 'immutable'):
                board.control_receipt(fresh, {**supplied, 'evidence': ['Changed supplied source meaning']})
        with patch('coordinator_runtime.owner_control.load_helper', return_value=self.helper(calls)):
            for _ in range(3):
                await self.tick()
        kept = board.delivery_status(fresh)
        self.assertEqual(kept['control_receipt']['receipt']['supplied_receipt'], supplied)
        self.assertEqual(kept['control_receipt'], got['control_receipt'])
        self.assertEqual(self.store.job(self.job['id']), self.before)
        self.assertEqual(self.request_state(request)['state'], 'pending')
        self.runtime.execute.assert_not_called()
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',
            (json.loads(self.before['members'])[0]['event'],))['processed_at'])


if __name__ == '__main__':
    unittest.main()
