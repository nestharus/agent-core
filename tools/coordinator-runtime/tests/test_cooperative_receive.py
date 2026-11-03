"""Cooperative existing-owner controls, synthetic boards only; no wake claims."""
import json
import os
import unittest
from unittest.mock import patch

import test_continuing as fixtures
from support import queued,event


class CooperativeReceive(unittest.TestCase):
    setUp=fixtures.Continuing.setUp

    def test_managed_control_owner_read_stage_never_competes_for_normal_ack_cursor(self):
        owner=self.config['roles']['Work']['owner'];sender=self.boards['Reviews']
        with self.store.tx():
            key=self.store._outbox('Reviews','Work','question',{'text':'Actual owner must resolve this bounded control question.'})
        row=self.store.one('SELECT * FROM outboxes WHERE id=?',(key,))
        receipt=sender.post_delivery(self.store,row);self.store.delivery_observed(key,receipt)
        with patch.object(sender.store,'dispatch_notices',side_effect=AssertionError('managed control dispatched as queue')):
            self.assertEqual(sender.transport_delivery(self.store,row)['state'],'posted')
        self.assertEqual(self.boards['Work'].scan(self.store),[])
        with self.substrate.database(str(self.path)) as conn:
            before=conn.execute('SELECT ack_seq FROM sessions WHERE session=?',(owner,)).fetchone()[0]
        cursor=self.store.one("SELECT seq FROM cursors WHERE role='Work'")['seq']
        with patch.dict(os.environ,{'CODEX_SESSION_ID':owner}):
            body=sender.show_delivery(key)
            self.assertIn('bounded control',body['payload']['text'])
            sender.delivery_stage(key,'picked-up',{'evidence':['genuine synthetic owner read full control']})
            sender.delivery_stage(key,'processed',{'evidence':['owner decided affected source stays held']})
            sender.delivery_stage(key,'settled',{'evidence':['owner returned explicit control disposition'],'resolution':'Retain genuine source holds; no task acceptance inferred.'})
        with self.substrate.database(str(self.path)) as conn:
            self.assertEqual(conn.execute('SELECT ack_seq FROM sessions WHERE session=?',(owner,)).fetchone()[0],before)
        self.assertEqual(self.store.one("SELECT seq FROM cursors WHERE role='Work'")['seq'],cursor)
        self.assertEqual(self.boards['Work'].scan(self.store),[])

    def test_selected_reviews_owner_work_is_received_without_generic_model_or_replay(self):
        queued(self.store,event(self.config,'selected-review',role='Reviews',task='reviews-proposer'))
        job=self.store.reserve();self.store.delegate_owner_job(job['id']);self.runtime.pump_deliveries()
        outbox=self.store.one("SELECT * FROM outboxes WHERE kind='work'")
        board=self.boards['Reviews'];owner=self.config['roles']['Reviews']['owner']
        self.assertEqual(board.scan(self.store),[])  # Same-owner selected procedure is a control duty.
        with patch.dict(os.environ,{'CODEX_SESSION_ID':owner}):
            received=board.show_delivery(outbox['id'])
            self.assertEqual(received['payload']['selected_binding']['model'],'gpt-xhigh')
            board.delivery_stage(outbox['id'],'picked-up',{'evidence':['exact existing synthetic owner acquired original procedure responsibility']})
        self.assertEqual(self.store.job(job['id'])['state'],'awaiting-owner')
        self.assertEqual(self.store.rows('SELECT * FROM attempts WHERE job=?',(job['id'],)),[])  # The incoming fake classifier remains; no generic review worker exists.
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        self.assertIsNone(board.delivery_status(outbox['id'])['processed_at'])
