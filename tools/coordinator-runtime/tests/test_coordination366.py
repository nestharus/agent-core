"""Bounded fictional timing discriminators; no provider or authority efficacy."""
import asyncio
import copy
import json
from contextlib import contextmanager
from types import MethodType, SimpleNamespace
import time
import unittest
from unittest.mock import patch

from coordinator_runtime.appserver import Peer
from coordinator_runtime.contracts import Refusal, SOL, digest, encode, ident
from coordinator_runtime import metadata_lookup as lookup
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.inputs import InputJournal


class Pipe:
    def __init__(self, delay=0, blocked=False):
        self.stdout = asyncio.StreamReader()
        self.stdin = self
        self.delay = delay
        self.release = asyncio.Event()
        self.entered = asyncio.Event()
        self.blocked = blocked
        self.frames = []

    def write(self, data):
        self.frames.append(json.loads(data))

    async def drain(self):
        self.entered.set()
        if self.blocked:
            await self.release.wait()
        await asyncio.sleep(self.delay)

    def respond(self, result=None):
        self.stdout.feed_data((json.dumps({'id': self.frames[-1]['id'], 'result': result or {'ok': True}})+'\n').encode())


class Coordination(unittest.IsolatedAsyncioTestCase):
    async def close_peer(self, peer):
        peer.reader.cancel()
        await asyncio.gather(peer.reader, return_exceptions=True)

    async def test_blocked_drain_uses_existing_RPC_budget_and_late_response_cannot_settle(self):
        child = Pipe(blocked=True)
        peer = Peer(child, 4096)
        call = asyncio.create_task(peer.rpc('thread/start', {}, timeout=.04))
        try:
            await child.entered.wait()
            await asyncio.sleep(.10)
            observed = call.done()
            print('DRAIN_OBSERVATION='+json.dumps({'done_before_release': observed, 'progress': peer.progress}))
            self.assertTrue(observed, 'RPC budget must cover blocked drain')
            with self.assertRaises(asyncio.TimeoutError):
                await call
            self.assertEqual(peer.pending, {})
            self.assertEqual(peer.progress[-1]['state'], 'timeout')
            child.respond({'thread': {'id': 'fictional-late-root'}})
            await asyncio.sleep(0)
            self.assertIsNone(peer.thread)
            self.assertEqual(peer.progress[-1]['state'], 'timeout')
        finally:
            child.release.set()
            child.respond()
            await asyncio.gather(call, return_exceptions=True)
            await self.close_peer(peer)

    async def test_send_and_response_share_one_budget(self):
        child = Pipe(delay=.06)
        peer = Peer(child, 4096)
        async def response():
            await child.entered.wait()
            await asyncio.sleep(.12)
            child.respond()
        responder = asyncio.create_task(response())
        try:
            with self.assertRaises(asyncio.TimeoutError):
                await peer.rpc('config/read', {}, timeout=.09)
            self.assertEqual(peer.pending, {})
            self.assertEqual(peer.progress[-1]['state'], 'timeout')
            print('SHARED_BUDGET_OBSERVATION='+json.dumps(peer.progress))
        finally:
            await responder
            await self.close_peer(peer)

    async def test_real_tick_yields_to_matching_reader_and_control_between_phases(self):
        child = Pipe()
        peer = Peer(child, 4096)
        dispatcher = Dispatcher.__new__(Dispatcher)
        dispatcher.phase_errors = {}
        phases, cleared, errors, control_seen, reader_seen = [], [], [], [], []
        dispatcher.store = SimpleNamespace(clear_operational_error=cleared.append,
            record_operational_error=lambda subject, detail: errors.append(subject))
        names = ('receipts', 'reconcile_completed', 'intake', 'schedule_classifications',
                 'schedule_classification_recovery', 'schedule_input_mappings', 'schedule_job', 'schedule_recovery',
                 'custodian_progress', 'automatic_cleanup')
        def phase(name):
            def operation():
                phases.append(name)
                if peer.progress[-1]['state'] == 'succeeded':
                    reader_seen.append(name)
                time.sleep(.01)  # Finite synchronous phase; never interrupt/skip its checks.
                if name == 'intake':
                    raise Refusal('fictional held intake')
            operation.__name__ = name
            return operation
        for name in names:
            setattr(dispatcher, name, phase(name))
        async def pump():
            phases.append('pump')
        dispatcher.pump_deliveries_async = pump
        call = asyncio.create_task(peer.rpc('thread/start', {}, timeout=1))
        try:
            await child.entered.wait()
            child.respond({'thread': {'id': 'fictional-owned-root'}})
            asyncio.get_running_loop().call_soon(lambda: control_seen.append(len(phases)))
            with patch('coordinator_runtime.dispatcher.capacity.deliver_pending', lambda store: phases.append('capacity')):
                await dispatcher.tick()
            response = await call
            print('PHASE_OBSERVATION='+json.dumps({'control_seen_after_phases': control_seen,
                'reader_seen': reader_seen, 'phases': phases, 'cleared': cleared, 'errors': errors, 'RPC': peer.progress}))
            self.assertEqual(response['thread']['id'], 'fictional-owned-root')
            self.assertLess(control_seen[0], len(names), 'control callback must run before all synchronous phases')
            self.assertTrue(reader_seen, 'matching response must be collected between phases')
            self.assertEqual(phases, list(names)+['capacity', 'pump'])
            self.assertEqual(errors, ['dispatcher-phase:intake'])
            self.assertEqual(cleared, ['dispatcher-phase:' + name for name in names if name != 'intake'])
            self.assertEqual(peer.progress[-1]['state'], 'succeeded')
        finally:
            await asyncio.gather(call, return_exceptions=True)
            await self.close_peer(peer)

    async def test_rpc_cancellation_clears_pending_without_claiming_response(self):
        child = Pipe(blocked=True)
        peer = Peer(child, 4096)
        call = asyncio.create_task(peer.rpc('thread/start', {}, timeout=1))
        try:
            await child.entered.wait()
            call.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await call
            self.assertEqual(peer.pending, {})
            self.assertEqual(peer.progress[-1]['failure'], 'CancelledError')
            self.assertEqual(peer.progress[-1]['state'], 'failed')
        finally:
            await self.close_peer(peer)


class MappingCompletionContract(unittest.TestCase):
    """523: real prompt/decision/proof/guard, in-memory fictional dependencies.

    No SDK, provider, file consumer, scheduler or live authority is exercised.
    The fixture's current delegation and Board checks are explicit fictions.
    """

    def setUp(self):
        from coordinator_runtime import local_integration as local
        self.local = local
        self.source = {'id':'fictional-source', 'kind':'board', 'role':'Work',
                       'recipient':ident(), 'package':None, 'allowed_tasks':['work-proposer'],
                       'body':'Existing rollout; related missing member needs Work.'}
        self.definition = {'kind':'item', 'line':'fictional', 'incarnation':'one',
            'bindings':[{'target':'/fixtures/catalog.json','path':['rollout']}],
            'resources':[], 'protected':['owner'], 'writable':[]}
        config = {'actor':ident(), 'limits':{'max_result_bytes':65536},
            'tasks':{'work-proposer':{'role':'Work', 'effects':'none'}},
            'local_integration':{'points':{'known':self.definition},
                                 'tasks':{'work-proposer':{'points':['known']}}}}
        self.enrollment = {'owner':self.source['recipient']}
        self.state = {'state':'queued', 'hold':None, 'processed_at':None,
                      'classification':'fictional-classification', 'classifier':'classifier',
                      'hash':digest(self.source)}
        self.queue = {'job':None}
        self.current = True
        self.rights = True
        self.source_current = True
        self.board_checks = []
        def authority(store):
            self.board_checks.append('authority')
            if not self.rights:
                raise Refusal('fictional current rights withdrawn')
        def original(store, source):
            self.board_checks.append('source')
            if not self.source_current:
                raise Refusal('fictional original source changed')
        self.selection = {'tasks':['work-proposer'], 'basis':{'event_boundary':0},
                          'metadata_lookup':{'tasks':['work-proposer']}}
        def current():
            if not self.current:
                raise Refusal('fictional current delegation revoked')
            return None, self.selection
        access = SimpleNamespace(key='fictional-capability', current=current,
            event=lambda source:True, task=lambda row:True,
            boards={'Work':SimpleNamespace(verify_authority=authority, verify_input_source=original)})
        self.store = SimpleNamespace(config=config, controller='fictional-controller', processing=access,
            event=lambda event:copy.deepcopy(self.source), input_resolution=lambda event:None,
            enrollment=lambda role:self.enrollment, one=self.one, rows=self.rows,
            attempt=lambda attempt:self.row if attempt=='mapping' else {'collected':1})
        self.unresolved = [{'scope':'fictional-scope', 'member':'missing', 'status':'absent'}]
        self.snapshot = {'points':{'known':{'definition':copy.deepcopy(self.definition), 'version':digest('fictional-v1'),
                                          'value':{'exists':True, 'owner':None}}},
            'unresolved':self.unresolved, 'binding':local.mapping_binding(self.store,'work-proposer',None),
            'observed':1}
        self.record = {'event':self.source['id'], 'attempt':'mapping', 'capability':access.key,
                       'source_hash':digest(self.source), 'snapshot':encode({'work-proposer':self.snapshot})}
        self.receipt = {'task':'work-proposer', 'integration':{'state':'known','reads':['known'],'writes':[]},
            'reason':'Independently authorized read-only proposal for the uniquely observed rollout.',
            'evidence':['Observed existing rollout; owner value is absent, not consent.',
                        'Related missing member remains unresolved-existing, not new work.'],
            'remaining_obligations':['Work must resolve the absent owner and missing relationship.']}
        self.answer = {'semantic':'DONE', 'summary':'Completed known/unresolved split interpretation.',
                       'decision_json':encode(self.receipt)}
        self.row = {'kind':'input-mapping', 'event':self.source['id'], 'controller':self.store.controller,
            'begin':1, 'ended':2, 'collected':3, 'exit':0, 'error':None, 'capture':'complete',
            'binding':encode(SOL), 'session':ident(), 'result':encode(self.answer),
            'detail':encode({'processing_capability':access.key,
                            'tool_completion':{'complete':True,'items':[],'nonzero_completions':[],'unknown_types':[]}})}

    def one(self, sql, args=()):
        if 'FROM input_lookups' in sql:
            return self.record
        if 'FROM processing_source_positions' in sql:
            return {'position':1}
        if 'FROM events' in sql:
            return self.state
        if 'FROM queue' in sql:
            return self.queue
        if 'FROM admissions' in sql:
            return None
        self.fail('Unexpected fixture query: '+sql)

    def rows(self, sql, args=()):
        if 'FROM local_discovered_points' in sql or 'FROM local_lookup_points' in sql:
            return []
        self.fail('Unexpected fixture query: '+sql)

    def proof(self):
        receipt = lookup.decision(self.store,self.source['id'],'mapping')
        return lookup.proof(self.store,self.source['id'],self.store.config['actor'],'mapping',receipt)

    def test_prompt_defines_completion_without_erasing_questions_or_rights(self):
        prompt = lookup.mapping_prompt(self.store,self.source['id'],'mapping')
        for clause in ['DONE means this bounded metadata interpretation is complete',
                       'retaining all unanswered owner/relationship questions explicitly',
                       'An absent owner value neither grants nor revokes those rights',
                       'If missing authority or meaning prevents a valid bounded interpretation',
                       'return PARTIAL or UNKNOWN', 'use FAILED', 'Never relabel a prior result to DONE',
                       'Unresolved members have no selectable point or novelty authority']:
            with self.subTest(clause=clause):
                self.assertTrue(clause in prompt,'Missing bounded completion instruction: '+clause)
        self.assertIn(encode(self.source),prompt)
        self.assertIn(encode(self.snapshot),prompt)

    def test_completed_split_passes_real_boundary_with_questions_and_frozen_version(self):
        before = copy.deepcopy((self.row,self.record,self.source,self.state,self.queue))
        receipt = lookup.decision(self.store,self.source['id'],'mapping')
        provenance, observation = self.proof()
        self.assertEqual(receipt['evidence'],self.receipt['evidence'])
        self.assertEqual(receipt['remaining_obligations'],self.receipt['remaining_obligations'])
        self.assertEqual(observation['unresolved'],self.unresolved)
        self.assertEqual(observation['packet'],{'reads':['known'],'writes':[],
                                             'versions':{'known':self.snapshot['points']['known']['version']}})
        self.assertFalse(provenance['native_owner_receipt'])
        self.assertEqual(self.board_checks,['authority','source'])
        self.assertEqual((self.row,self.record,self.source,self.state,self.queue),before)

    def test_genuine_incomplete_results_refuse_before_authority_or_point_work(self):
        for semantic in ['UNKNOWN','PARTIAL','FAILED']:
            with self.subTest(semantic=semantic):
                self.row['result'] = encode({**self.answer,'semantic':semantic})
                before = copy.deepcopy((self.row,self.record,self.state,self.queue))
                with self.assertRaisesRegex(Refusal,'incomplete metadata interpretation'):
                    self.proof()
                self.assertEqual((self.row,self.record,self.state,self.queue),before)
                self.assertEqual(self.board_checks,[])

    def test_malformed_decisions_and_unobserved_points_still_refuse(self):
        variants = [{**self.answer,'extra':True}, {**self.answer,'summary':''},
            {**self.answer,'decision_json':encode({**self.receipt,'extra':True})},
            {**self.answer,'decision_json':encode({**self.receipt,'integration':{
                'state':'known','reads':['missing'],'writes':[]}})},
            {**self.answer,'decision_json':'{"task":1,"task":2}'}]
        for answer in variants:
            with self.subTest(answer=answer):
                self.row['result'] = encode(answer)
                with self.assertRaises(Refusal):
                    self.proof()

    def test_current_rights_source_and_config_refusals_remain(self):
        def revoked(): self.current = False
        def rights(): self.rights = False
        def original(): self.source_current = False
        def source_hash(): self.record['source_hash'] = 'changed'
        def task(): self.store.config['tasks']['work-proposer']['effects'] = 'changed'
        def enrollment(): self.enrollment['owner'] = ident()
        def policy(): self.store.config['local_integration']['points']['known']['incarnation'] = 'changed'
        for fault in [revoked,rights,original,source_hash,task,enrollment,policy]:
            with self.subTest(fault=fault.__name__):
                self.setUp()
                fault()
                with self.assertRaises(Refusal):
                    self.proof()

    def test_unknown_relationships_still_cannot_authorize_novelty(self):
        self.row['result'] = encode({**self.answer,'decision_json':encode({
            **self.receipt,'integration':{'state':'new'}})})
        with self.assertRaisesRegex(Refusal,'cannot authorize new business'):
            self.proof()

    def test_incomplete_collection_and_changed_frozen_definition_still_refuse(self):
        for field, value in [('capture','partial'),('exit',1),('collected',None),('binding',encode({})),
                             ('controller','other'),('error','interpretation failure')]:
            with self.subTest(field=field):
                self.setUp()
                self.row[field] = value
                with self.assertRaises(Refusal):
                    self.proof()
        self.setUp()
        self.store.config['local_integration']['points']['known']['incarnation'] = 'changed'
        # Even a forged fresh policy binding cannot restamp a frozen definition.
        self.snapshot['binding'] = self.local.mapping_binding(self.store,'work-proposer',None)
        self.record['snapshot'] = encode({'work-proposer':self.snapshot})
        with self.assertRaisesRegex(Refusal,'original point definition changed'):
            self.proof()

    def wire_journal(self):
        """531: real journal methods over explicit fictional row/write adapters.

        No database/SQL engine, filesystem consumer, Board or scheduler runs.
        Unexpected queries/writes fail, and the adapter rolls back failed calls.
        """
        store = self.store
        self.resolutions, self.job_scopes, self.writes = [], {}, []
        self.state.update(role='Work', error=None, ack=None, ack_receipt=None)
        self.store.config['limits'] = {'max_result_bytes':65536}
        self.store.config['local_integration']['tasks']['work-proposer']['authority'] = 'Fictional read-only proposal.'
        # This fixture config changed before observation, never restamp a result.
        self.snapshot['binding'] = self.local.mapping_binding(store,'work-proposer',None)
        self.record['snapshot'] = encode({'work-proposer':self.snapshot})
        original_one = store.one

        def one(sql, args=()):
            if 'FROM input_resolutions' in sql:
                matches = [r for r in self.resolutions if r['event'] == args[0]
                           and (len(args) == 1 or r['version'] == args[1])]
                return copy.deepcopy(matches[-1]) if matches else None
            if 'FROM local_jobs' in sql:
                return copy.deepcopy(self.job_scopes.get(args[0]))
            if sql == 'SELECT point FROM local_lookup_points WHERE point=?':
                return None
            if 'FROM local_point_commits' in sql:
                return None
            return original_one(sql,args)

        def execute(sql, args):
            self.writes.append(sql)
            if sql == 'INSERT INTO input_resolutions VALUES(?,?,?,?,?,?,?)':
                self.resolutions.append(dict(zip(
                    ['event','version','source_hash','actor','receipt','prior','created'],args)))
            elif sql == "UPDATE events SET state='received' WHERE id=?":
                self.assertEqual(args,(self.source['id'],))
                self.state['state'] = 'received'
            elif sql == "UPDATE queue SET state='owner-resolution-pending' WHERE event=?":
                self.assertEqual(args,(self.source['id'],))
                self.queue['state'] = 'owner-resolution-pending'
            elif sql == 'INSERT INTO local_jobs VALUES(?,?,?)':
                self.job_scopes[args[0]] = dict(zip(['job','policy','scope'],args))
            else:
                self.fail('Unexpected fictional journal write: '+sql)

        @contextmanager
        def tx():
            before = copy.deepcopy((self.state,self.queue,self.resolutions,self.job_scopes,self.writes))
            store.db.in_transaction = True
            try:
                yield
            except Exception:
                self.state,self.queue,self.resolutions,self.job_scopes,self.writes = before
                raise
            finally:
                store.db.in_transaction = False

        store.one, store.tx = one, tx
        store.db = SimpleNamespace(in_transaction=False, execute=execute)
        store.clock = lambda:4
        store.budget = lambda *args, **kwargs:None
        for name in ['input_resolution','routing_event','resolve_input','validate_input_selection']:
            setattr(store,name,MethodType(getattr(InputJournal,name),store))
        return store

    def resolve_wire(self):
        receipt = lookup.decision(self.store,self.source['id'],'mapping')
        return self.store.resolve_input(self.source['id'],self.store.config['actor'],receipt,
                                        mapping_attempt='mapping')

    def test_wire_prompt_names_actual_consumer_types_and_service_owned_versions(self):
        prompt = lookup.mapping_prompt(self.store,self.source['id'],'mapping')
        for clause in ['task must be an exact delegated task string',
                       'summary and reason must be nonblank text of at most 16000 UTF-8 bytes each',
                       'evidence must be a nonempty list of at most 32 nonblank strings',
                       'remaining_obligations must be a list of at most 32 nonblank strings',
                       'each at most 4000 UTF-8 bytes', 'do not drop questions to fit the bounds',
                       'service binds source/package', 'frozen string versions and mapping basis',
                       'do not supply or restamp versions', 'at most 64 unique observed point-key strings']:
            with self.subTest(clause=clause):
                self.assertTrue(clause in prompt,'Missing wire-contract instruction: '+clause)
        payload = json.loads(prompt.split('\n',1)[1])
        with self.subTest(clause='max_result_bytes payload'):
            self.assertEqual(payload.get('max_result_bytes'),self.store.config['limits']['max_result_bytes'])

    def test_wire_split_reaches_resolution_packet_and_read_only_job_scope(self):
        store = self.wire_journal()
        originals = copy.deepcopy((self.source,self.row,self.record))
        resolution = self.resolve_wire()
        frozen = resolution['prior']['integration_observation']
        self.assertEqual(resolution['receipt']['evidence'],self.receipt['evidence'])
        self.assertEqual(resolution['receipt']['remaining_obligations'],self.receipt['remaining_obligations'])
        self.assertEqual(frozen['unresolved'],self.unresolved)
        self.assertEqual(frozen['binding'],self.snapshot['binding'])
        self.assertEqual(frozen['observed'],self.snapshot['observed'])
        self.assertFalse(resolution['prior']['software_processing']['native_owner_receipt'])
        self.assertEqual(self.state['state'],'received')  # Fresh classification still required.
        self.assertEqual(self.queue,{'job':None,'state':'owner-resolution-pending'})
        routed = store.routing_event(self.source['id'])
        self.assertEqual(routed['owner_resolution'],resolution)
        row = {'event':self.source['id'],'task':'work-proposer','package':None}
        packet = self.local.packet(store,row)
        self.assertEqual(packet,{'lane':'anchored','reads':['known'],'writes':[],
            'versions':{'known':self.snapshot['points']['known']['version']},'sources':[self.source['id']]})
        job = {'id':'fictional-job','task':'work-proposer','active_attempt':None,
               'members':encode([{'event':self.source['id'],'input_resolution':1}])}
        self.local.record_job(store,job)
        context = self.local.context(store,job)
        self.assertEqual(context['basis']['inputs'],[packet])
        self.assertEqual(context['basis']['writes'],[])
        self.assertEqual(store.input_resolution(self.source['id'],1),resolution)
        self.assertEqual((self.source,self.row,self.record),originals)
        self.assertEqual(len(self.writes),4)  # Resolution, two routing states, job scope only.

    def test_wire_list_bounds_accept_exact_limits_and_refuse_invalid_items(self):
        self.wire_journal()
        bounded = {**self.receipt,'evidence':['é'*2000]+['observed']*31,
                   'remaining_obligations':['q'*4000]+['question']*31}
        self.row['result'] = encode({**self.answer,'decision_json':encode(bounded)})
        self.assertEqual(self.resolve_wire()['receipt']['evidence'],bounded['evidence'])
        for key in ['evidence','remaining_obligations']:
            for value in [{'observed':'object'},'text',None,[''],['   '],[None],[7],[False],[{}],[['nested']],
                          ['x'*4001],['é'*2001],['x']*33] + ([[]] if key == 'evidence' else []):
                with self.subTest(key=key,shape=type(value).__name__):
                    self.setUp()
                    self.wire_journal()
                    self.row['result'] = encode({**self.answer,'decision_json':encode({**self.receipt,key:value})})
                    before = copy.deepcopy((self.source,self.row,self.record,self.state,self.queue))
                    with self.assertRaises(Refusal):
                        self.resolve_wire()
                    self.assertEqual(self.resolutions,[])
                    self.assertEqual(self.writes,[])
                    self.assertEqual((self.source,self.row,self.record,self.state,self.queue),before)
        self.setUp()
        self.wire_journal()
        self.row['result'] = encode({**self.answer,'decision_json':encode({**self.receipt,'remaining_obligations':[]})})
        self.assertEqual(self.resolve_wire()['receipt']['remaining_obligations'],[])

    def test_wire_incomplete_malformed_and_result_budget_refuse_without_writes(self):
        variants = [{**self.answer,'semantic':s} for s in ['UNKNOWN','PARTIAL','FAILED']]
        variants += [{**self.answer,'decision_json':'{"task":1,"task":2}'},
                     {**self.answer,'decision_json':'{'},
                     {**self.answer,'decision_json':encode({**self.receipt,'versions':{}})}]
        for answer in variants:
            with self.subTest(semantic=answer['semantic']):
                self.setUp()
                self.wire_journal()
                self.row['result'] = encode(answer)
                with self.assertRaises((Refusal,ValueError)):
                    self.resolve_wire()
                self.assertEqual(self.resolutions,[])
                self.assertEqual(self.writes,[])
                self.assertEqual(self.state['state'],'queued')
        self.setUp()
        self.wire_journal()
        self.store.config['limits']['max_result_bytes'] = 100
        with self.assertRaisesRegex(Refusal,'admitted result bound'):
            self.resolve_wire()
        self.assertEqual(self.writes,[])

    def test_wire_source_capture_config_and_rights_refusals_survive_full_resolution(self):
        for fault in ['capture','source','config','rights','delegation']:
            with self.subTest(fault=fault):
                self.setUp()
                self.wire_journal()
                if fault == 'capture': self.row['capture'] = 'partial'
                elif fault == 'source': self.record['source_hash'] = 'changed'
                elif fault == 'config': self.store.config['tasks']['work-proposer']['effects'] = 'changed'
                elif fault == 'rights': self.rights = False
                else: self.current = False
                with self.assertRaises(Refusal):
                    self.resolve_wire()
                self.assertEqual(self.resolutions,[])
                self.assertEqual(self.writes,[])

    def test_wire_version_type_and_post_resolution_binding_or_rights_still_refuse_packet(self):
        for fault in ['version','binding','rights']:
            with self.subTest(fault=fault):
                self.setUp()
                store = self.wire_journal()
                if fault == 'version':
                    # Adverse fictional service observation, not a model-supplied stamp.
                    self.snapshot['points']['known']['version'] = {'wrong':'object'}
                    self.record['snapshot'] = encode({'work-proposer':self.snapshot})
                resolution = self.resolve_wire()
                if fault == 'binding': store.config['tasks']['work-proposer']['effects'] = 'changed'
                elif fault == 'rights': self.rights = False
                before = copy.deepcopy((self.resolutions,self.writes))
                message = {'version':'incomplete version basis','binding':'mapping policy/admission',
                           'rights':'rights withdrawn'}[fault]
                with self.assertRaisesRegex(Refusal,message):
                    self.local.packet(store,{'event':self.source['id'],'task':'work-proposer','package':None})
                self.assertEqual((self.resolutions,self.writes),before)
                self.assertEqual(store.input_resolution(self.source['id']),resolution)
