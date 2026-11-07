"""Real frozen service retry and AppServer async preparation; synthetic actors only."""
import asyncio
from contextlib import ExitStack
from unittest.mock import patch
from test_native_return820 import NativeReturn
from coordinator_runtime import appserver, service, prospective
from coordinator_runtime.contracts import Refusal

class Reacquisition836(NativeReturn):
    def frozen(self):
        self.source()
        asyncio.run(self.phase('schedule_classifications'))
        job = self.store.reserve()
        self.assertEqual(job['task'], 'reviews-integrator')
        with patch.object(self.store.execution_pool, 'allocate', side_effect=Refusal('fictional pool allocation unavailable')):
            with self.assertRaises(Refusal):
                self.dispatch.schedule_job()
        self.assertIsNone(self.store.job(job['id'])['active_attempt'])
        self.assertEqual(self.store.job(job['id'])['state'], 'reserved')
        return self.store.job(job['id'])

    def conflict(self):
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped836','orphan836')")

    def traps(self):
        stack = ExitStack()
        original_event, original_attempt, original_one = self.store.event, self.store.attempt, self.store.one
        def event(key):
            if self.store.one("SELECT resource FROM ordinary_resources WHERE resource='unmapped836'") and key in (self.e['id'],self.returned['id']):
                raise AssertionError('protected Source/return body before fresh physical refusal')
            return original_event(key)
        def attempt(key,*args,**kwargs):
            if self.store.one("SELECT resource FROM ordinary_resources WHERE resource='unmapped836'") and key == self.a['id']:
                raise AssertionError('protected native attempt/result before fresh physical refusal')
            return original_attempt(key,*args,**kwargs)
        def one(sql,args=()):
            if 'review_calls' in sql.lower() and original_one("SELECT resource FROM ordinary_resources WHERE resource='unmapped836'"):
                raise AssertionError('protected native packet/receipt/answer before fresh physical refusal')
            return original_one(sql,args)
        stack.enter_context(patch.object(self.store,'event',side_effect=event))
        stack.enter_context(patch.object(self.store,'attempt',side_effect=attempt))
        stack.enter_context(patch.object(self.store,'one',side_effect=one))
        return stack

    def test_public_frozen_retry_after_pool_failure_refuses_before_body(self):
        job = self.frozen()
        self.conflict()
        with self.traps(), self.assertRaises(Refusal):
            self.dispatch.schedule_job()
        self.assertIsNone(self.store.job(job['id'])['active_attempt'])
        self.assertEqual(len(self.transport.calls),2)
        self.assertIsNotNone(self.store.one("SELECT resource FROM ordinary_resources WHERE resource='unmapped836'"))

    def test_async_preparation_after_start_refuses_before_body(self):
        job = self.frozen()
        attempt = self.store.start_job(job['id'],job['token'])
        server = appserver.AppServer(self.config)
        yielded = []
        async def command(*args):
            await asyncio.sleep(0)
            yielded.append(True)
            self.conflict()
            return ['/fictional-never-start836'], {'fictional_preflight':True}
        async def prepare():
            current = self.store.job(job['id'])
            admission = self.store.one('SELECT * FROM admissions WHERE package=?',(current['package'],))
            self.boards['Reviews'].bind_software_attempt(self.store,current,attempt,admission)
            return await server.run(self.store,attempt,'fictional prebuilt native packet',self.config['tasks']['reviews-integrator'])
        with self.traps(), patch.object(server,'command',side_effect=command), \
             patch.object(appserver.storage,'prepare',return_value=None), \
             patch.object(appserver.asyncio,'create_subprocess_exec',side_effect=AssertionError('process launched after conflict')):
            outcome = asyncio.run(prepare())
        self.assertEqual(yielded,[True])
        self.assertIn('physical admission',outcome['error'])
        self.assertTrue(outcome['detail']['known_not_started'])
        self.store.collect(attempt,outcome)
        self.assertIsNotNone(self.store.attempt(attempt)['collected'])
        self.assertEqual(len(self.transport.calls),2)

    def test_frozen_resume_without_conflict_preserves_source(self):
        job = self.frozen()
        originals = self.store.rows('SELECT * FROM review_calls')
        async def resume():
            self.dispatch.schedule_job()
            await self.drain()
        asyncio.run(resume())
        current = self.store.job(job['id'])
        self.assertIsNotNone(current['active_attempt'])
        self.assertIsNotNone(self.store.attempt(current['active_attempt'])['collected'])
        self.assertEqual(originals,self.store.rows('SELECT * FROM review_calls'))
        self.assertEqual(len(self.transport.calls),2)
