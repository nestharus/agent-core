"""Metadata-only selected retention in fresh owned public SDK fiction."""
import copy
import json
import os
import sqlite3
import time
import unittest
from contextlib import contextmanager
from unittest.mock import patch
from pathlib import Path
from test_qa629_repairs import Fixture, actor
from coordinator_runtime import processing, windows, configuration
from coordinator_runtime.contracts import Refusal, digest, encode


class SelectedBasis(Fixture):
    def setUp(self):
        self.bootstrap(self.configure)
        self.select(dict(max_inflight=8,reviews={},legacy_resources={}))
        self.oldcap=self.cap
        self.source=self.post('Work','work-integrator',None)
        self.mapping=self.store.resolve_input(self.source['id'],self.config['roles']['Work']['owner'],dict(
            **self.route_receipt()))
        self.classify(task='work-integrator')
        self.other=self.post('Branch','branch-proposer',None)
        self.store.set_hold(self.other['id'],'unrelated private capture/effect/consumer UNKNOWN')
        self.store.db.execute("UPDATE enrollments SET legacy_hold='unrelated UNKNOWN' WHERE role='Branch'")
        self.issuer=self.config['roles']['Work']['owner']
        with actor(self.boards['Work'].store,self.issuer):processing.revoke(self.store,self.boards,self.oldcap)
        self.expected=dict(event=self.source['id'],role='Work',source_hash=digest(self.source),
            source_birth=self.store.one('SELECT position FROM processing_source_positions WHERE event=?',(self.source['id'],))['position'],
            task='work-integrator',mapping_version=self.mapping['version'])
        self.original_allocation=windows.current(self.store)
        self.original_queue=self.store.one('SELECT * FROM queue WHERE event=?',(self.source['id'],))

    def configure(self):
        self.config['window_service']=dict(tasks=list(self.config['tasks']),max_new_inputs=40,batch_size=8,max_decisions=16)

    def route_receipt(self):
        return dict(source_hash=digest(self.source),mode='route',task='work-integrator',package=None,
            related_event=None,related_job=None,reason='Exact fictional same original',
            evidence=['original Work owns this mapping'],remaining_obligations=[])

    def basis(self,expected=None):
        with actor(self.boards['Work'].store,self.issuer):
            return processing.basis(self.store,self.boards,selected_retained=[expected or self.expected])

    def selection(self,basis=None):
        return dict(basis=basis or self.basis(),authority='Actual fictional Work explicit one-original plus future authority',
            retained_events=[self.source['id']],recover_controls={},future_intake=True,tasks=list(self.config['tasks']),
            max_shared_rows=1000,max_shared_payload_bytes=1000000,max_runtime_rows=1000,
            service=dict(max_inflight=8,reviews={},legacy_resources={}))

    def issue(self,selection):
        with actor(self.boards['Work'].store,self.issuer):return processing.select(self.store,self.boards,selection)['capability']

    @contextmanager
    def sentinel(self):
        # Authorizer prevents ANY body acquisition, including selected payloads.
        # A query gate separately prevents even an unselected hash/key/metadata
        # projection; SQLite authorizers cannot inspect bound row predicates.
        forbidden={'outboxes','attempts','results','artifact_blobs','artifact_custody','attempt_storage','source_custody','operational_errors'}
        denied=[];original=self.store.one;original_rows=self.store.rows
        original_opened=processing.ProcessingBoard.opened
        @contextmanager
        def opened(board,*args,**kwargs):
            with original_opened(board,*args,**kwargs) as conn:
                def board_authorize(action,table,column,db,caller):
                    if action==sqlite3.SQLITE_READ and column=='payload' and table in {'coordinator_deliveries_v1','coordinator_software_deliveries_v1'}:
                        denied.append((table,column));return sqlite3.SQLITE_DENY
                    if action==sqlite3.SQLITE_FUNCTION and column and column.lower()=='length':
                        denied.append(('function','length'));return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                conn.set_authorizer(board_authorize)
                try:yield conn
                finally:conn.set_authorizer(None)
        def authorize(action,table,column,db,caller):
            if action==sqlite3.SQLITE_READ and (table in forbidden or table=='events' and column in {'payload','error','ack_receipt'}):
                denied.append((table,column));return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        def gate(fn):
            def query(sql,args=()):
                lower=sql.lower()
                if ' from configuration_transitions' in lower and 'selection' in lower and 'json_extract(selection,' not in lower:
                    raise AssertionError('whole historical configuration selection acquired: '+sql)
                if ' from processing_capabilities' in lower and 'selection' in lower:
                    raise AssertionError('historical processing selection body/size acquired: '+sql)
                for table in ('input_resolutions','queue','processing_source_positions'):
                    if 'from '+table in lower and ('where event=?' not in lower or not args or args[0]!=self.source['id']):
                        raise AssertionError('unselected old source mapping metadata acquired: '+sql)
                if ' from events' in lower and 'max(rowid)' not in lower:
                    if 'where id=?' not in lower or not args or args[0]!=self.source['id']:
                        raise AssertionError('unselected old event metadata/hash acquired: '+sql)
                return fn(sql,args)
            return query
        self.store.db.set_authorizer(authorize)
        try:
            with patch.object(processing.ProcessingBoard,'opened',opened),patch.object(self.store,'one',side_effect=gate(original)),patch.object(self.store,'rows',side_effect=gate(original_rows)), \
                 patch.object(self.store,'event',side_effect=AssertionError('basis acquired source body')), \
                 patch.object(processing.ProcessingBoard,'_usage',side_effect=AssertionError('historical delivery LENGTH')), \
                 patch('coordinator_runtime.store.owned_bytes',side_effect=AssertionError('old capture filesystem byte accounting')):
                yield
        finally:self.store.db.set_authorizer(None)
        self.assertEqual(denied,[])

    def test_parent_missing_metadata_selected_api(self):
        with self.sentinel():
            b=self.basis();key=self.issue(self.selection(b))
        access=processing.Access(self.store,key,self.boards);self.store.processing=access
        self.assertTrue(access.event(self.source))
        self.assertFalse(access.event(self.other))
        self.assertFalse(b.get('future_only',False))
        self.assertNotIn(digest(self.other),encode(b))
        self.assertEqual(b['allocation']['allocation'],{k:self.original_allocation[k] for k in ('number','configuration','used','new_inputs','actor','created')})
        self.assertEqual(windows.current(self.store),self.original_allocation)
        self.assertEqual(self.store.rows('SELECT * FROM service_window_allocations'),[])
        self.assertEqual(self.store.one('SELECT * FROM queue WHERE event=?',(self.source['id'],)),self.original_queue)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(self.source['id'],))['processed_at'])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM events')['n'],2)
        self.assertEqual(self.store.rows('SELECT id FROM jobs'),[])
        self.assertEqual(self.store.input_resolution(self.source['id'])['version'],self.mapping['version'])
        self.assertEqual(self.store.enrollment('Branch')['legacy_hold'],'unrelated UNKNOWN')
        self.assertIsNotNone(self.store.one('SELECT hold FROM events WHERE id=?',(self.other['id'],))['hold'])
        # Future input is a separate genuine Board post, never a repost of original.
        fresh=self.post('Work','work-proposer',None)
        self.assertTrue(access.event(fresh))
        self.assertNotEqual(fresh['id'],self.source['id'])
        self.assertEqual(self.store.one('SELECT id FROM events WHERE id=?',(self.source['id'],))['id'],self.source['id'])

    def test_CLI_selected_basis_and_delegate_use_exact_public_pins(self):
        from coordinator_runtime import cli
        pins=self.area/'selected-public-pins.json';pins.write_text(encode([self.expected]))
        args=cli.parser().parse_args(['processing-basis','--selected-retained',str(pins)])
        with self.sentinel(),patch.dict(os.environ,{'CODEX_SESSION_ID':self.issuer}),actor(self.boards['Work'].store,self.issuer):
            basis=cli.operate(args,self.store)
            selection=self.selection(basis)
            path=self.area/'selected-public-authority.json';path.write_text(encode(selection))
            key=cli.operate(cli.parser().parse_args(['delegate-processing','--selection',str(path)]),self.store)['capability']
        self.assertTrue(processing.Access(self.store,key,self.boards).event(self.source))
        with self.assertRaises(Refusal):processing.basis(self.store,self.boards,future_only=True,selected_retained=[self.expected])

    def test_wrong_selected_operands_and_authority_refuse_before_bytes(self):
        for field,value in [('source_hash','0'*64),('role','Branch'),('source_birth',999),('task','work-proposer'),('mapping_version',999)]:
            expected={**self.expected,field:value}
            with self.subTest(field=field),self.sentinel(),self.assertRaises(Refusal):self.basis(expected)
        with actor(self.boards['Work'].store,self.config['roles']['Branch']['owner']),self.assertRaises(Exception):
            processing.basis(self.store,self.boards,selected_retained=[self.expected])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM processing_capabilities WHERE revoked IS NULL')['n'],0)

    def test_held_selected_unknown_mapping_and_exclusion_refuse_before_bytes(self):
        self.store.set_hold(self.source['id'],'explicit fictional source exclusion')
        with self.sentinel(),self.assertRaises(Refusal):self.basis()
        self.store.set_hold(self.source['id'],None)
        # Negative-only fiction: remove the selected derived mapping, never source.
        self.store.db.execute('DELETE FROM input_resolutions WHERE event=?',(self.source['id'],))
        with self.sentinel(),self.assertRaises(Refusal):self.basis()

    def test_selected_birth_is_not_renewed_after_delegation(self):
        key=self.issue(self.selection());access=processing.Access(self.store,key,self.boards)
        self.store.processing=access
        self.assertTrue(access.event(self.source))
        self.store.db.execute('UPDATE processing_source_positions SET position=position+100 WHERE event=?',(self.source['id'],))
        with self.assertRaisesRegex(Refusal,'birth changed'):access.event(self.source)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(self.source['id'],))['processed_at'])

    def test_drift_revision_task_and_selection_cannot_be_laundered(self):
        selection=self.selection()
        self.store.db.execute("UPDATE events SET hold='changed unrelated UNKNOWN' WHERE id=?",(self.other['id'],))
        with self.sentinel(),self.assertRaisesRegex(Refusal,'basis changed'):self.issue(selection)
        selection=self.selection();selection['basis']['journal_revision']['schema']='wrong'
        with self.sentinel(),self.assertRaisesRegex(Refusal,'basis changed'):self.issue(selection)
        selection=self.selection();selection['retained_events']=[self.other['id']]
        with self.sentinel(),self.assertRaises(Refusal):self.issue(selection)
        selection=self.selection();selection['recover_controls']={self.source['id']:'fake'}
        with self.sentinel(),self.assertRaises(Refusal):self.issue(selection)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM processing_capabilities WHERE revoked IS NULL')['n'],0)


class LocalSelectedBasis(Fixture):
    setUp=SelectedBasis.setUp
    basis=SelectedBasis.basis
    issue=SelectedBasis.issue
    sentinel=SelectedBasis.sentinel
    def configure(self):
        SelectedBasis.configure(self)
        self.catalog=self.area/'catalog.json';self.catalog.write_text(encode(dict(a=dict(id='a',owner='fixture',state='original'))))
        self.config['local_integration']=dict(max_inflight=8,points={'a':dict(kind='item',line='fixture',incarnation='one',
            bindings=[dict(target=str(self.catalog),path=['a'])],resources=[],protected=['id','owner'],writable=['state'])},
            tasks={t:dict(capacity=5,discovery_batch=4,points=['a'],authority='Fictional current known point',method=v['templates'][0])
                for t,v in self.config['tasks'].items()})

    def route_receipt(self):
        request=(dict(state='unresolved-existing') if 'unknown_selected_mapping' in self._testMethodName
                 else dict(state='known',reads=['a'],writes=[]))
        return {**SelectedBasis.route_receipt(self),'integration':request}

    def selection(self,basis=None):
        return {**SelectedBasis.selection(self,basis),'input_mappings':['work-integrator']}

    def test_same_original_remaps_current_observed_versions_then_reserves(self):
        with self.sentinel():key=self.issue(self.selection())
        self.store.processing=processing.Access(self.store,key,self.boards)
        self.runtime.boards=self.boards
        # Current capability differs from the original observed mapping.
        # It cannot silently restamp, retry or claim processing completion.
        with self.assertRaisesRegex(Refusal,'mapping policy/admission/grant/capability changed'):
            self.store.reserve()
        with actor(self.boards['Work'].store,self.issuer):
            mapped=processing.map_input(self.store,self.boards,key,self.source['id'],self.issuer,self.route_receipt())
        self.assertEqual(mapped['version'],self.mapping['version']+1)
        self.assertEqual(mapped['prior']['integration_observation']['binding']['capability'],key)
        self.classify(task='work-integrator')
        job=self.store.reserve();self.assertIsNotNone(job)
        self.assertEqual(json.loads(job['members'])[0]['event'],self.source['id'])
        self.assertEqual(json.loads(job['members'])[0]['hash'],self.expected['source_hash'])
        self.assertEqual(json.loads(job['members'])[0]['input_resolution'],mapped['version'])
        self.assertEqual(self.store.event(self.source['id']),self.source)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(self.source['id'],))['processed_at'])
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM events')['n'],2)
        self.assertEqual(self.catalog.read_text(),encode(dict(a=dict(id='a',owner='fixture',state='original'))))

    def test_unknown_selected_mapping_refuses_before_source_bytes(self):
        # A genuine public owner resolution explicitly says identity unresolved.
        with self.sentinel(),self.assertRaisesRegex(Refusal,'known mapping'):self.basis()


class CurrentConfigurationSelected(LocalSelectedBasis):
    def configure(self):
        LocalSelectedBasis.configure(self)
        root=Path(__file__).resolve().parents[1]
        self.config.update(operator_cli=str(root/'coordinator'),operator_config=str(self.area/'original-config.json'),
            control_receive=dict(mode='cooperative',instructions=str(root/'templates/coordinator-receive.md')))

    def setUp(self):
        SelectedBasis.setUp(self)
        value=configuration.candidate(self.store,str(self.area/'current-config.json'),[])
        Path(value['operator_config']).write_text(encode(value))
        decision=dict(basis=configuration.basis(self.store,self.boards,value,list(value['tasks'])),
            authority='Genuine fictional Work selects this same-journal current configuration')
        with actor(self.boards['Work'].store,self.issuer):configuration.apply(self.store,self.boards,value,decision)
        from coordinator_runtime.store import Store
        from coordinator_runtime.dispatcher import Dispatcher
        self.store.close()
        self.config=value;self.store=Store(value);self.addCleanup(self.store.close)
        self.boards={r:processing.ProcessingBoard(value,r) for r in value['roles']}
        for b in self.boards.values():b.runtime=self.store
        self.runtime=Dispatcher(self.store,models=object(),boards=self.boards)

    def selection(self,basis=None):
        choice=LocalSelectedBasis.selection(self,basis)
        choice['service']['allocations']=dict(basis=choice['basis']['allocation'],target='fictional next Work allocation',
            reason='Retain same original through current config without renewing old use',evidence='Fictional explicit Work decision',
            custody={r:dict(owner=v['owner'],evidence='Every old duty retained') for r,v in self.config['roles'].items()},
            expires=self.store.clock()+600,max_windows=1)
        return choice

    def test_actual_fixture_configuration_then_selected_original_remap(self):
        # Real prospective config API on an owned journal; no old business job
        # or source grant is rewritten. Selected basis/delegation remain under
        # the body/hash/size sentinel after this configuration decision.
        transition=configuration.latest(self.store)
        self.assertGreaterEqual(transition['position'],1)
        with self.sentinel():
            basis=self.basis();key=self.issue(self.selection(basis))
        self.assertEqual(basis['configuration_transition']['position'],transition['position'])
        self.store.processing=processing.Access(self.store,key,self.boards)
        self.assertTrue(self.store.processing.event(self.source))
        scope,parameters=configuration.event_candidate_scope(self.store)
        ids=[r['id'] for r in self.store.rows('SELECT e.id FROM events e WHERE '+scope,parameters)]
        self.assertEqual(ids,[self.source['id']])
        self.assertFalse(self.store.processing.event(self.other))
        with actor(self.boards['Work'].store,self.issuer):
            mapped=processing.map_input(self.store,self.boards,key,self.source['id'],self.issuer,self.route_receipt())
        self.classify(task='work-integrator')
        job=self.store.reserve();self.assertIsNotNone(job)
        self.assertEqual(json.loads(job['members'])[0]['event'],self.source['id'])
        self.assertEqual(self.store.event(self.source['id']),self.source)
        self.assertEqual(mapped['version'],self.mapping['version']+1)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM events')['n'],2)


from test_bounded311 import Catalog as _Catalog

class SevenDuties(_Catalog):
    """Original seven-duty assertions with the current required fixture pins.

    This is only a schema/bootstrap repair for the isolated legacy fixture;
    production retention/source/readiness/publication checks stay active.
    """
    def configure(self):
        _Catalog.configure(self)
        from coordinator_runtime.retention_dependency import source_pins
        policy=self.config['canonical_publication']
        policy['source_pins']=source_pins(policy['library'],[])
