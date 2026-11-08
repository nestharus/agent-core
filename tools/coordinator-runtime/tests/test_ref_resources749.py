"""Exact ref leases through real owned Git CAS/readback and no-replay callers."""
import copy
import json
from unittest.mock import patch

from coordinator_runtime import branches, ordinary
from coordinator_runtime.contracts import Refusal, digest
from test_ordinary_effects import OrdinaryEffects


class RefResources(OrdinaryEffects):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.git('remote', 'set-url', 'origin', 'https://example.invalid/owned-composition749')

    def keys(self, source='refs/heads/source', destination='refs/heads/destination'):
        device, inode = branches.repository_identity(str(self.repo))
        return ['git-ref:'+str(device)+':'+str(inode)+':'+ref for ref in (source, destination)]

    def admitted_refs(self, same_ref=False):
        self.boundary()
        policy = self.admission()
        if same_ref:
            policy.update(ref=policy['source_ref'], before=self.head)
        keys = list(dict.fromkeys(self.keys(policy['source_ref'], policy['ref'])))
        policy['resources'] = [dict(key=key, owner=self.acceptor,
            authority='Owned fixture exact common Git ref lease', expires=self.now+90) for key in keys]
        admission = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        admission['task_scopes']['branch-integrator']['ordinary_effects'] = copy.deepcopy(policy)
        self.store.admit('package', self.config['roles']['Branch']['owner'], admission)
        return self.prepared()

    async def test_declared_source_destination_leases_reach_actual_CAS_and_readback(self):
        job, attempt = self.admitted_refs()
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
        self.assertTrue(await ordinary.perform(self.store, self.boards['Branch'], job))
        self.assertEqual(self.git('rev-parse', 'destination'), self.head)
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        commands = receipt['tools']
        cas = [r for r in commands if 'update-ref' in r['argv'] and r['exit'] is not None]
        self.assertEqual(len(cas), 1)
        self.assertEqual(cas[0]['exit'], 0)
        self.assertTrue(cas[0]['complete'])
        self.assertEqual(receipt['collector'], self.store.controller)
        self.assertEqual(receipt['unknown_effects'], [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [])
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', dict(
            execution_hash=digest(receipt), rationale='Independent fixture exact ref outcome', unknowns=[]))
        self.assertTrue(ordinary.accepted_package(self.store, 'package'))
        before = self.store.rows('SELECT * FROM ordinary_tool_records')
        self.assertTrue(await ordinary.perform(self.store, self.boards['Branch'], self.store.job(job['id'])))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'), before)

    async def test_identical_source_destination_policy_still_refuses_before_intent(self):
        job, _ = self.admitted_refs(same_ref=True)
        with self.assertRaisesRegex(Refusal, 'separate pinned source'):
            await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.git('rev-parse', 'source'), self.head)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [])

    async def test_foreign_unknown_declared_lease_refuses_before_effect_intent(self):
        job, _ = self.admitted_refs()
        key = self.keys()[0]
        # An uncollected/unknown original reservation is never inferred free.
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', (key, 'fictional-unknown-original'))
        with patch.object(ordinary, 'adapter', side_effect=AssertionError('foreign ref effect')):
            with self.assertRaisesRegex(Refusal, 'resource still belongs to another original'):
                await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.store.one('SELECT attempt FROM ordinary_resources WHERE resource=?', (key,))['attempt'],
                         'fictional-unknown-original')

    async def test_foreign_unknown_computed_ref_refuses_and_retains_current_intent(self):
        self.boundary()
        self.admission()  # A separate declared lease; computed ref still needs its own check.
        job, attempt = self.prepared()
        key = self.keys()[1]
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', (key, 'fictional-foreign-original'))
        with patch.object(ordinary, 'adapter', side_effect=AssertionError('foreign ref effect')):
            with self.assertRaisesRegex(Refusal, 'actual common Git ref remains owned'):
                await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
        run = self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt,))
        self.assertEqual(run['state'], 'intent')
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(self.store.one('SELECT attempt FROM ordinary_resources WHERE resource=?', (key,))['attempt'],
                         'fictional-foreign-original')
        before = self.store.rows('SELECT * FROM ordinary_tool_records')
        with self.assertRaisesRegex(Refusal, 'never replay'):
            await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'), before)
        self.assertEqual(self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt,)), run)

    async def test_current_attempt_leases_do_not_authorize_replaying_unknown_intent(self):
        job, attempt = self.admitted_refs()
        with patch.object(ordinary, 'adapter', side_effect=Refusal('Owned fixture interruption before CAS')):
            with self.assertRaisesRegex(Refusal, 'interruption'):
                await ordinary.perform(self.store, self.boards['Branch'], job)
        resources = self.store.rows('SELECT * FROM ordinary_resources ORDER BY resource')
        self.assertEqual({r['resource'] for r in resources}, set(self.keys()))
        self.assertEqual({r['attempt'] for r in resources}, {attempt})
        self.store.db.execute("UPDATE ordinary_runs SET state='unknown' WHERE attempt=?", (attempt,))
        before = self.store.rows('SELECT * FROM ordinary_tool_records')
        with patch.object(ordinary, 'source', side_effect=AssertionError('unknown intent read/replay')):
            with self.assertRaisesRegex(Refusal, 'never replay'):
                await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_tool_records'), before)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources ORDER BY resource'), resources)
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
