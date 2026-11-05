"""Current selection under retained fiction; no model/provider/runtime mounts.

Intent: current work progresses without historical authority rebinding; source,
configuration, grant, payload and capability guards still decide actual work.
The no-change comparator restores only the former candidate enumeration.
"""
import asyncio
from contextlib import nullcontext
import copy
import json
import time
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing, processing_admission, service
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import Dispatcher
from test_configuration308 import CurrentConfiguration
from test_processing188 import EngineTests


class TypedModel:
    """Explicit deterministic typed-return seam, no native fields or AI call."""
    async def run(self, runtime, attempt, prompt, spec, schema):
        runtime.begin(attempt, {'fictional_typed_return': True})
        return {'exit': 0, 'capture': 'complete', 'cleanup': 'fictional-no-child',
                'result': {'event_id': runtime.attempt(attempt)['event'], 'task': 'wp',
                           'package': None, 'reason': 'fictional selected proposal'}}


class Classification(unittest.IsolatedAsyncioTestCase):
    def workload(self, size=64, continuing=False):
        fixture = CurrentConfiguration()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        runtime = fixture.runtime
        for n in range(size - 4):
            event = {**fixture.originals[0], 'id': 'fictional-retained-' + str(n)}
            with runtime.tx():
                runtime.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,900)',
                                   (event['id'], event['role'], encode(event), digest(event)))
                processing.note_source(runtime, event['id'])
        fixture.transition()
        if continuing:
            selection = fixture.processing_selection()
            del selection['expires'], selection['max_starts']
            selection['service'] = {'max_inflight': 3, 'reviews': {}, 'legacy_resources': {}}
            key = processing.select(fixture.runtime, fixture.boards, selection)['capability']
            fixture.runtime.processing = processing.Access(fixture.runtime, key, fixture.boards)
        else:
            fixture.issue()
        return fixture

    def original_rows(self, runtime):
        return {table: runtime.rows('SELECT * FROM ' + table +
                (" WHERE received=900" if table == 'events' else
                 " WHERE id='fictional-original-attempt'" if table == 'attempts' else ''))
                for table in ('events', 'attempts', 'jobs', 'outboxes', 'enrollments')}

    async def test_current_classification_and_supported_controls_under_retained_load(self):
        results = []
        for unchanged in (True, False):
            fixture = self.workload(64, continuing=True)
            runtime, boards = fixture.runtime, fixture.boards
            future = fixture.fresh()
            before = self.original_rows(runtime)
            ready, go, routed = asyncio.Event(), asyncio.Event(), asyncio.Event()
            original_release = configuration.assert_release
            checks = []
            def release(store):
                checks.append(store.controller)
                time.sleep(.002)  # Identical public-source validation cost seam.
                return original_release(store)
            async def activity(dispatcher, emit):
                ready.set()
                await go.wait()
                dispatcher.schedule_classifications()
                await asyncio.gather(*list(dispatcher.active))
                routed.set()
                await dispatcher.stopping.wait()
            comparator = (patch.object(configuration, 'event_candidate_scope', return_value=('1', ()))
                          if unchanged else nullcontext())
            with patch.object(service.Dispatcher, 'run', activity), comparator:
                original = asyncio.create_task(service.serve(runtime, boards, runtime.processing.key,
                                                            lambda value: None, models=TypedModel()))
                await asyncio.wait_for(ready.wait(), 5)
                try:
                    with patch.object(configuration, 'assert_release', release):
                        started = time.monotonic()
                        client = asyncio.create_task(service.control(runtime, runtime.processing.key, 'status'))
                        go.set()
                        answer = await asyncio.wait_for(client, 5)
                        elapsed = time.monotonic() - started
                        await asyncio.wait_for(routed.wait(), 5)
                    self.assertEqual(answer['runs'][0]['controller'], runtime.controller)
                    self.assertEqual(runtime.one('SELECT task FROM queue WHERE event=?', (future['id'],))['task'], 'wp')
                    self.assertEqual(before, self.original_rows(runtime))
                    results.append({'condition': 'former-enumeration' if unchanged else 'candidate',
                                    'retained': 64, 'release_checks': len(checks),
                                    'status_ms': int(elapsed * 1000), 'typed_route': 'wp'})
                finally:
                    stopped = await service.control(runtime, runtime.processing.key, 'stop')
                    self.assertIn('draining', stopped['state'])
                    await asyncio.wait_for(original, 5)
            self.assertEqual(before, self.original_rows(runtime))
        print('CLASSIFICATION381_CAUSAL=' + encode(results))
        self.assertGreater(results[0]['release_checks'], results[1]['release_checks'] + 60)
        self.assertLess(results[1]['status_ms'], results[0]['status_ms'] / 2)

    async def test_each_selection_and_launch_rechecks_current_authority(self):
        fixture = self.workload()
        runtime = fixture.runtime
        future = fixture.fresh()
        attempt, actual = runtime.claim_classification()
        self.assertEqual(actual['id'], future['id'])
        before = self.original_rows(runtime)
        saved_config = copy.deepcopy(runtime.config)
        saved_selection = runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (runtime.processing.key,))['selection']
        def restore():
            runtime.config.clear(); runtime.config.update(copy.deepcopy(saved_config))
            runtime.db.execute('UPDATE processing_capabilities SET revoked=NULL,selection=? WHERE id=?',
                               (saved_selection, runtime.processing.key))
        cases = {
            'revoked': lambda: runtime.db.execute('UPDATE processing_capabilities SET revoked=1001 WHERE id=?', (runtime.processing.key,)),
            'configuration': lambda: runtime.config.update(enabled=True),
            'source': lambda: runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',
                         (encode({**json.loads(saved_selection), 'basis': {**json.loads(saved_selection)['basis'], 'implementation': {}}}), runtime.processing.key)),
            'grant': lambda: fixture.conn.execute("UPDATE coordinator_grants_v1 SET actor='fictional-foreign' WHERE role='Work'"),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                mutate()
                dispatcher = Dispatcher(runtime, models=TypedModel(), boards=fixture.boards)
                outcome = await dispatcher.run_model(attempt, '', {}, {})
                self.assertTrue(outcome['detail']['known_not_started'], outcome)
                self.assertIsNone(runtime.attempt(attempt)['begin'])
                if label != 'grant':
                    with self.assertRaises(Refusal): runtime.claim_classification()
                fixture.conn.execute("UPDATE coordinator_grants_v1 SET actor=? WHERE role='Work'", (runtime.config['actor'],))
                restore()
        self.assertEqual(before, self.original_rows(runtime))
        runtime.authorize_launch(attempt)  # Restored current boundary remains usable.
        # A changed exact retained payload is still rejected by its original
        # authority; this negative is deliberately in the pre-transition mode.
        retained = EngineTests(); self.addCleanup(retained.tearDown); retained.setUp()
        source = retained.event('fictional-exact-retained', 'Work', 'wp', queued=False)
        retained.authority()
        retained.runtime.db.execute('UPDATE events SET payload=? WHERE id=?',
                                    (encode({**source, 'body': 'changed'}), source['id']))
        with self.assertRaises(Refusal): retained.runtime.claim_classification()

    async def test_recovery_and_admission_do_not_reacquire_excluded_bodies(self):
        fixture = self.workload()
        runtime = fixture.runtime
        future = fixture.fresh()
        # Historical states remain owed; neither selector can adopt them.
        runtime.db.execute("UPDATE events SET state='classification-held' WHERE received=900")
        before = self.original_rows(runtime)
        original_event = runtime.event
        def read(name):
            if name != future['id']:
                raise AssertionError('excluded historical body reacquired')
            return original_event(name)
        dispatcher = processing.ProcessingDispatcher(runtime, models=TypedModel(), boards=fixture.boards)
        with patch.object(runtime, 'event', read):
            dispatcher.schedule_classification_recovery()
            self.assertIsNone(runtime.claim_classification_recovery())
        self.assertEqual(before, self.original_rows(runtime))
        runtime.db.execute("UPDATE events SET state='received' WHERE received=900")
        before = self.original_rows(runtime)
        with patch.object(runtime, 'event', read):
            # Exercise the admission enumeration with an explicit fictional
            # policy seam, keeping the real current guard and actual admission.
            current = runtime.processing.current
            def policy():
                row, selection = current()
                return row, {**selection, 'software_admission': {'scopes': {'fictional-topic': {}}}}
            with patch.object(runtime.processing, 'current', policy):
                processing_admission.admit_pending(runtime)
        self.assertEqual(dispatcher.active, set())
        self.assertEqual(before, self.original_rows(runtime))

    async def test_logical_birth_boundary_legacy_fallback_and_retained_mode(self):
        fixture = self.workload(4)
        runtime = fixture.runtime
        future = fixture.fresh()
        # A legacy row without a logical position uses its original rowid.
        runtime.db.execute('DELETE FROM processing_source_positions WHERE event=?', (fixture.originals[1]['id'],))
        scope, parameters = configuration.event_candidate_scope(runtime)
        candidates = runtime.rows('SELECT e.id FROM events e WHERE (' + scope + ')', parameters)
        self.assertEqual(candidates, [{'id': future['id']}])
        # Logical birth survives a recycled lower physical rowid. The current
        # and historical event_allowed meanings must continue to agree.
        runtime.db.execute("INSERT INTO events(rowid,id,role,payload,hash,received) VALUES(-1,'fictional-recycled','Work','{}','fictional',1000)")
        processing.note_source(runtime, 'fictional-recycled')
        self.assertTrue(configuration.event_allowed(runtime, {'id': 'fictional-recycled'}))
        self.assertIn({'id': 'fictional-recycled'}, runtime.rows('SELECT e.id FROM events e WHERE (' + scope + ')', parameters))
        retained = EngineTests(); self.addCleanup(retained.tearDown); retained.setUp()
        source = retained.event('fictional-retained-allowed', 'Work', 'wp', queued=False)
        retained.authority()
        self.assertEqual(retained.runtime.claim_classification()[1]['id'], source['id'])
