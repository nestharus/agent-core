"""Normal bounded receipt refresh, using new owned software-consumer fixtures.

Protocol answers/authentication are fictional. These are actual local writers,
collectors, SDK receipts and scheduler/frontier calls, not live role acceptance.
The processing-mode control selects only that guard via an explicit access seam;
it does not qualify a processing capability or service.
"""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime.contracts import ident
from coordinator_runtime.frontier import delivery
from test_software_consumption import SoftwareConsumption


class SettledReobservation(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = SoftwareConsumption.asyncSetUp
    asyncTearDown = SoftwareConsumption.asyncTearDown
    adapter = SoftwareConsumption.adapter
    classify = SoftwareConsumption.classify
    task = SoftwareConsumption.task
    sender = SoftwareConsumption.sender
    consume = SoftwareConsumption.consume

    def outgoing(self, key):
        return self.store.one('SELECT * FROM outboxes WHERE id=?', (key,))

    def processed(self, event):
        return self.store.one('SELECT processed_at FROM events WHERE id=?', (event,))['processed_at']

    def conserved(self):
        # Completion/scheduling state can advance; original identities cannot.
        return {
            'events': self.store.rows('SELECT id,hash,payload,parent FROM events ORDER BY id'),
            'attempts': self.store.rows('SELECT * FROM attempts ORDER BY id'),
            'results': self.store.rows('SELECT * FROM results ORDER BY attempt'),
            'grants': self.store.rows('SELECT * FROM enrollments ORDER BY role'),
            'jobs': self.store.rows('SELECT id,members,active_attempt,controller,effects,response FROM jobs ORDER BY id'),
            'outboxes': self.store.rows('SELECT id,job,event,producer,recipient,kind,required,payload,hold FROM outboxes ORDER BY id'),
        }

    async def test_normal_revisits_join_later_whole_frontier_without_replay(self):
        for asynchronous in (False, True):
            with self.subTest(asynchronous=asynchronous):
                source, sender, handoff = await self.sender('Work', 'Branch', package=ident())
                receiver = await self.consume()
                key = handoff['id']
                board = self.boards['Work']
                before = board.delivery_status(key)
                whole = delivery(self.store, key)
                self.assertTrue(whole['complete'])
                self.assertIsNotNone(self.processed(self.store.job(receiver['id'])['response']))
                self.assertEqual(before['state'], 'settled')
                self.assertIsNone(self.outgoing(key)['processed_at'])
                self.assertIsNone(self.processed(source['id']))
                self.assertGreater(whole['processed_at'], before['processed_at'])
                stable = self.conserved()
                # Normal passes must reobserve, without posting/transporting or
                # minting another native control or receiving business process.
                with patch.object(board, 'post_delivery', side_effect=AssertionError('repost')), \
                     patch.object(board, 'transport_delivery', side_effect=AssertionError('transport replay')), \
                     patch.object(board, 'automatic_control', side_effect=AssertionError('new native duty')):
                    for _ in range(8):
                        if asynchronous:
                            await self.runtime.pump_deliveries_async()
                        else:
                            self.runtime.pump_deliveries()
                        self.runtime.reconcile_completed()
                self.assertEqual(self.outgoing(key)['processed_at'], max(before['processed_at'], whole['processed_at']))
                self.assertEqual(board.delivery_status(key), before)
                self.assertEqual(self.conserved(), stable)
                self.assertIsNotNone(self.processed(source['id']))
                self.assertIsNotNone(self.processed(self.store.job(sender['id'])['response']))
                self.assertGreaterEqual(self.processed(source['id']), self.outgoing(key)['processed_at'])
                self.assertEqual(self.store.recover_source(source['id']), source)
                self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?', (self.store.job(sender['id'])['response'],))['state'], 'done')

    async def test_unstarted_and_held_receiver_duties_stay_unfinished(self):
        source, sender, handoff = await self.sender('Work', 'Branch', package=ident())
        await self.classify()
        key = handoff['id']
        receiving = delivery(self.store, key)['event']
        self.assertIsNotNone(receiving)
        for held in (False, True):
            with self.subTest(held=held):
                if held:
                    self.store.set_hold(receiving, 'Independent fictional receiver duty; retained')
                for _ in range(4):
                    self.runtime.pump_deliveries()
                    self.runtime.reconcile_completed()
                self.assertFalse(delivery(self.store, key)['complete'])
                self.assertIsNone(self.processed(source['id']))
                self.assertIsNone(self.processed(self.store.job(sender['id'])['response']))
                self.assertIsNone(self.outgoing(key)['processed_at'])
                self.assertIsNone(self.boards['Work'].delivery_status(key)['processed_at'])
                self.assertIsNone(self.store.one('SELECT job FROM queue WHERE event=?', (receiving,))['job'])
        self.assertTrue(self.store.one('SELECT hold FROM events WHERE id=?', (receiving,))['hold'])

    async def test_settled_receipt_does_not_waive_later_receiver_hold(self):
        source, sender, handoff = await self.sender('Work', 'Branch', package=ident())
        await self.consume()
        key = handoff['id']
        whole = delivery(self.store, key)
        self.assertTrue(whole['complete'])
        self.assertIsNone(self.outgoing(key)['processed_at'])
        board_before = self.boards['Work'].delivery_status(key)
        self.assertEqual(board_before['state'], 'settled')
        self.store.set_hold(whole['event'], 'Independent hold after local collection; retained')
        for _ in range(4):
            self.runtime.pump_deliveries()
            self.runtime.reconcile_completed()
        self.assertFalse(delivery(self.store, key)['complete'])
        self.assertIsNone(self.outgoing(key)['processed_at'])
        self.assertIsNone(self.processed(source['id']))
        self.assertIsNone(self.processed(self.store.job(sender['id'])['response']))
        self.assertEqual(self.boards['Work'].delivery_status(key), board_before)
        self.assertTrue(self.store.one('SELECT hold FROM events WHERE id=?', (whole['event'],))['hold'])

    async def test_processing_mode_requires_extra_whole_frontier_before_board_settlement(self):
        _, _, handoff = await self.sender('Work', 'Branch', package=ident())
        await self.classify()
        receiver = self.store.reserve()
        await self.task(receiver)
        await self.classify()
        key = handoff['id']
        board = self.boards['Work']
        self.assertIsNotNone(self.store.attempt(self.store.job(receiver['id'])['active_attempt'])['collected'])
        self.assertFalse(delivery(self.store, key)['complete'])
        # Only selection/access is fictional here. Production software_delivery
        # must still distinguish collected local work from its whole frontier.
        access = SimpleNamespace(event=lambda event: True, role=lambda role: True)
        with patch.object(self.store, 'processing', access):
            self.assertTrue(board.software_delivery(self.store, self.outgoing(key), self.boards))
        self.assertIsNone(board.delivery_status(key)['processed_at'])
        self.assertNotEqual(board.delivery_status(key)['state'], 'settled')
        # Complete only the receiver's own result through the existing handler,
        # leaving the source handoff for the processing-mode check below.
        for outbox in self.store.rows('SELECT * FROM outboxes WHERE job=?', (receiver['id'],)):
            self.runtime.pump_delivery(outbox)
        self.runtime.reconcile_completed()
        self.assertTrue(delivery(self.store, key)['complete'])
        with patch.object(self.store, 'processing', access):
            self.assertTrue(board.software_delivery(self.store, self.outgoing(key), self.boards))
        self.assertEqual(board.delivery_status(key)['state'], 'settled')
        self.assertIsNotNone(board.delivery_status(key)['processed_at'])
        for _ in range(4):
            self.runtime.pump_deliveries()
            self.runtime.reconcile_completed()
        self.assertIsNotNone(self.outgoing(key)['processed_at'])


if __name__ == '__main__':
    unittest.main()
