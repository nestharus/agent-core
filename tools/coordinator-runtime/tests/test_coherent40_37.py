"""Future authority and retained publication share the original accounting domain."""
import unittest

from test_publication_remainder import PublicationRemainder
from coordinator_runtime import prospective
from coordinator_runtime.contracts import digest
from support import event, queued


class CoherentAssembly(PublicationRemainder):
    async def test_future_boundary_conserves_original_remainder_and_singleton(self):
        before = self.retained()
        original = self.store.attempt(self.original)
        selection = {
            'configuration': digest(self.config),
            'authority': 'Fictional future authority, preserving original remainder',
            'expires': self.store.clock() + 100,
            'grants': {'Work': self.store.enrollment('Work')['grant_id']},
            'tasks': {'work-integrator': {
                'task_hash': digest(self.task), 'software_handoffs': {},
                'ordinary_effects': False}},
        }
        prospective.select(self.store, self.owner, selection)
        self.assertEqual(self.retained(), before)
        self.assertIsNone(prospective.for_job(self.store, self.store.job(self.job['id'])))
        queued(self.store, event(self.config, 'future work while original held'))
        self.assertIsNone(self.store.reserve())
        request = self.request()
        successor = self.consume(request)['successor']
        current = self.store.job(self.job['id'])
        self.assertEqual(current['active_attempt'], successor)
        self.assertEqual(current['token'], self.job['token'])
        self.assertEqual(current['members'], self.job['members'])
        self.assertEqual(self.store.attempt(self.original), original)
        self.assertEqual(self.store.rows('SELECT * FROM outboxes'), before['outboxes'])
        self.assertIsNone(prospective.for_job(self.store, current))
        self.assertIsNone(self.consume(request))
        self.assertIsNone(self.store.reserve())
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')), 1)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(CoherentAssembly(name) for name in CoherentAssembly.__dict__
                              if name.startswith('test_'))
