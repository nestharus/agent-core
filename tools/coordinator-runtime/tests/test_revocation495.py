"""QA490-H1 correction controls. Run in an outer isolated /fixtures + /sdk.

Fresh fictional principals and semantic/native transports; actual Store/SDK
guards and custody. Fictional transport exits are never native process proof.
"""
import asyncio
import json
import sqlite3
from unittest.mock import patch

from _receiving485_fixtures import Native, actor
from coordinator_runtime import processing, reviews
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode


class Handback(Native):
    bound = False

    def configure_fixture(self):
        super().configure_fixture()
        self.config['tasks']['reviews-proposer']['require_package_scope'] = self.bound
        self.config['local_integration']['tasks']['work-proposer']['points'] = ['a', 'b']

    def source(self):
        self.init_native(bound=self.bound)
        self.history = self.store.home / 'review-history' / 'component.md'
        self.history.parent.mkdir(parents=True, exist_ok=True)
        self.history.write_text('Original fictional history: dissent and unread files remain.\n')
        self.original_history = self.history.read_bytes()
        if self.bound:
            event = self.source_event()
        else:
            packet = {'component': 'component', 'origin': 'https://example.invalid/fictional.git',
                      'base': self.head, 'head': self.head, 'previous': None, 'answered_ids': []}
            event = self.post(encode({'review': packet}), 'Reviews', None)
        self.initial[event['id']] = 'reviews-proposer'
        asyncio.run(self.phase('schedule_classifications'))
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        self.assertEqual(job['task'], 'reviews-proposer')
        self.source_before = self.store.event(event['id'])
        self.events_before = self.store.rows('SELECT id,payload,hash FROM events ORDER BY id')
        return event, job, attempt

    def revoke(self):
        issuer = self.config['roles']['Work']['owner']
        with actor(self.boards['Work'].store, issuer):
            processing.revoke(self.store, self.boards, self.key)

    def assert_held(self, event, job, attempt, deferred):
        row = self.store.job(job['id'])
        self.assertEqual(row['state'], 'held')
        self.assertIn('original Source incomplete', row['hold_reason'])
        self.assertEqual('integration deferred' in row['hold_reason'], deferred)
        self.assertEqual(row['active_attempt'], attempt)
        self.assertEqual(row['controller'], self.store.controller)
        self.assertEqual(row['effects'], 'none')
        self.assertIsNone(row['closed_at'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (event['id'],))['processed_at'])
        self.assertEqual(self.store.event(event['id']), self.source_before)
        self.assertTrue(self.history.read_bytes().startswith(self.original_history))
        # Independently read committed custody, including after full revocation.
        with sqlite3.connect(self.store.path.as_uri() + '?mode=ro', uri=True) as conn:
            self.assertEqual(conn.execute('SELECT state FROM jobs WHERE id=?', (job['id'],)).fetchone()[0], 'held')
            self.assertEqual(conn.execute('SELECT count(*) FROM results WHERE attempt=?', (attempt,)).fetchone()[0], 1)
        self.save('handback495-' + type(self).__name__ + '-' + self._testMethodName, {
            'job': row, 'attempt': self.store.attempt(attempt),
            'result': self.store.one('SELECT * FROM results WHERE attempt=?', (attempt,)),
            'call': self.store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,)),
            'capability': self.store.one('SELECT * FROM processing_capabilities WHERE id=?', (self.key,)),
            'fictional_native_calls': self.transport.calls, 'git_ENDs': self.gitends})

    def test_revoked_before_acquisition(self):
        event, job, attempt = self.source()
        board = self.boards['Reviews']
        original_bind = board.bind_software_attempt
        bindings = []

        def bind_then_revoke(*args):
            original_bind(*args)
            bindings.append(json.loads(self.store.attempt(attempt)['detail'])['software_authority'])
            self.revoke()

        with patch.object(board, 'bind_software_attempt', side_effect=bind_then_revoke), \
                patch.object(reviews, 'material', wraps=reviews.material) as material, \
                patch('asyncio.create_subprocess_exec', side_effect=AssertionError('no native launch')) as native:
            asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        self.assertEqual(len(bindings), 1)
        material.assert_not_called()
        native.assert_not_called()
        actual = self.store.attempt(attempt)
        self.assertEqual(actual['state'], 'not-started')
        for field in ('begin', 'ended', 'exit', 'session'):
            self.assertIsNone(actual[field])
        self.assertIsNotNone(actual['collected'])
        self.assertEqual(actual['cleanup'], 'no-session-created')
        detail = json.loads(actual['detail'])
        self.assertTrue(detail['known_not_started'])
        self.assertEqual(detail['processing_capability'], self.key)
        self.assertEqual(detail['software_authority'], bindings[0])
        self.assertIn('expired/revoked', actual['error'])
        self.assertEqual(self.store.rows('SELECT id,payload,hash FROM events ORDER BY id'), self.events_before)
        self.assertEqual(self.store.rows('SELECT * FROM outboxes'), [])
        self.assertEqual(self.transport.calls, [])
        self.assertEqual(self.history.read_bytes(), self.original_history)
        self.assert_held(event, job, attempt, deferred=True)
        with self.assertRaises(Refusal):
            self.store.processing.current()
        self.assertIsNotNone(self.store.one('SELECT revoked FROM processing_capabilities WHERE id=?', (self.key,))['revoked'])
        self.assertTrue(all(not row['intake'] for row in self.store.rows('SELECT intake FROM enrollments')))

    def test_revoked_after_first_return(self):
        event, job, attempt = self.source()
        transport = self.transport
        original_call = transport.call

        async def return_then_revoke(*args, **kwargs):
            # Match Native.call's durable launch-intent boundary. The shared
            # authored transport supplies semantic fiction, not this OS seam.
            self.store.authorize_launch(attempt)
            with self.store.tx():
                self.store.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?", (attempt,))
            response = await original_call(*args, **kwargs)
            if len(transport.calls) == 1:
                self.revoke()
            return response

        with patch.object(transport, 'call', side_effect=return_then_revoke):
            asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        self.assertEqual(len(transport.calls), 1)
        call = self.store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,))
        turns = json.loads(call['receipt'])
        self.assertEqual(len(turns), 1)
        self.assertIn('QA472-FULL-NATIVE-REPORT', turns[0]['full_answer'])
        actual = self.store.attempt(attempt)
        self.assertFalse(json.loads(actual['detail'])['known_not_started'])
        self.assertEqual(json.loads(actual['detail'])['original_review_calls'], turns)
        self.assertIn('expired/revoked', actual['error'])
        context = self.store.one('SELECT * FROM review_contexts WHERE component=?', (call['component'],))
        self.assertEqual(context['state'], 'interrupted')
        self.assertEqual(context['collector'], self.store.controller)
        self.assertEqual(context['capability'], self.key)
        self.assertEqual(context['run'], transport.run)
        self.assertEqual(self.store.rows('SELECT id,payload,hash FROM events ORDER BY id'), self.events_before)
        self.assertEqual(self.history.read_bytes(), self.original_history)
        self.assert_held(event, job, attempt, deferred=True)

    def test_partial_return(self):
        event, job, attempt = self.source()
        original_call = self.transport.call

        async def partial(*args, **kwargs):
            code, receipt, text = await original_call(*args, **kwargs)
            answer = json.loads(text)
            answer['semantic'] = 'PARTIAL'
            answer['summary'] = 'Unresolved fictional dissent remains'
            return code, receipt, encode(answer)

        with patch.object(self.transport, 'call', side_effect=partial):
            asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        key = digest({'incomplete_ordinary_review': attempt})
        returned = self.store.event(key)
        self.assertEqual(returned['source_attempt'], attempt)
        self.assertEqual(returned['parent'], event['id'])
        self.assertEqual(returned['allowed_tasks'], ['reviews-integrator'])
        body = returned['body']
        self.assertEqual(body['full_original_outcome']['result']['semantic'], 'PARTIAL')
        self.assertEqual(body['full_original_call'], self.store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,)))
        self.assertIn('fictional-unread', encode(body))
        self.assert_held(event, job, attempt, deferred=False)

    def test_failure_return_pressure(self):
        event, job, attempt = self.source()
        original_budget = self.store.budget

        def pressure(kind, *args, **kwargs):
            if kind == 'events':
                raise Backpressure('fictional integration event pressure; retain original')
            return original_budget(kind, *args, **kwargs)

        with patch.object(self.dispatch.reviews, 'execute', side_effect=Refusal('fictional incomplete Source')), \
                patch.object(self.store, 'budget', side_effect=pressure):
            asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        self.assertEqual(self.store.rows('SELECT id,payload,hash FROM events ORDER BY id'), self.events_before)
        self.assertIn('integration event pressure', self.store.job(job['id'])['hold_reason'])
        self.assertIn('fictional incomplete Source', self.store.attempt(attempt)['error'])
        self.assert_held(event, job, attempt, deferred=True)

    def test_valid_source(self):
        event, job, attempt = self.source()
        asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        self.assertEqual(job['package'], 'pkg' if self.bound else None)
        self.assertEqual(len(self.transport.calls), 2)
        self.assertEqual(self.store.attempt(attempt)['semantic'], 'DONE')
        self.assertIsNone(self.store.job(job['id'])['hold_reason'])
        self.assertTrue(self.history.read_bytes().startswith(self.original_history))
        self.save('valid-source495-' + type(self).__name__, {'attempt': self.store.attempt(attempt), 'git_ENDs': self.gitends})


class BoundHandback(Handback):
    bound = True

    def test_withdrawal_independent_progress(self):
        event, job, attempt = self.source()
        board = self.boards['Reviews']
        original_bind = board.bind_software_attempt

        def withdraw(*args):
            result = original_bind(*args)
            receipt = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('pkg',))['receipt'])
            receipt['task_scopes']['reviews-proposer']['read_roots'] = []
            receipt['task_scopes']['reviews-proposer']['write_roots'] = []
            self.store.admit('pkg', self.config['roles']['Branch']['owner'], receipt)
            return result

        with patch.object(board, 'bind_software_attempt', side_effect=withdraw), \
                patch.object(reviews, 'material', wraps=reviews.material) as material:
            asyncio.run(self.dispatch.execute_review(job, attempt, event['body']['review']))
        material.assert_not_called()
        self.assert_held(event, job, attempt, deferred=False)
        # A refused Source reservation does not become a global service hold.
        other = self.post('Independent fictional Work item a; read-only reconciliation', 'Work')
        self.initial[other['id']] = 'work-proposer'
        self.members[other['id']] = ['a']
        def progressed():
            return self.store.one("SELECT a.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt WHERE j.task='work-proposer' AND a.collected IS NOT NULL AND a.semantic='DONE'")
        asyncio.run(self.until(progressed, n=18))
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertEqual(self.store.job(job['id'])['active_attempt'], attempt)
        self.assertEqual(len(self.transport.calls), 0)
        self.save('independent-progress495', {'original_job': self.store.job(job['id']), 'unrelated_event': other['id']})
