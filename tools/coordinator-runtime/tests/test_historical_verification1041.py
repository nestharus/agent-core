"""Original db1 journal protocol; fictional principals/transport, no provider.

The original has only preexisting db1 records, not a new historical witness.
Real Store intake/reservation, immutable policy/birth and software launch binding
are exercised. Native call/context rows are explicitly transport fiction.
"""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import historical_verification as h
from coordinator_runtime import processing, prospective, reviews, resource_scopes, configuration
from coordinator_runtime.board import Board, EXTENSION
from coordinator_runtime.software import BOARD_SCHEMA
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from support import config_at, enrolled, event, queued


class Principal:
    def __init__(self, actor): self.actor=actor
    def acting_session(self, expected):
        if self.actor != expected: raise Refusal('fictional current principal mismatch')
        return self.actor


class Historical1041(unittest.TestCase):
    def setUp(self):
        self.area=Path(tempfile.mkdtemp(prefix='historical1041-',dir='/fixtures'))
        self.config=config_at(self.area)
        if self._testMethodName=='test_current_metadata_residency_is_bounded_without_old_body_accounting':
            self.config['limits']['max_jobs']=1
        self.transitioned=self._testMethodName=='test_original_transition_and_frozen_task_not_current_substitute'
        if self.transitioned:
            self.config.update(operator_cli='/src/tools/coordinator-runtime/coordinator',operator_config=str(self.area/'current.json'),
                control_receive={'mode':'cooperative','instructions':'/src/tools/coordinator-runtime/templates/coordinator-receive.md'})
        self.config['software_delegation']=dict(grantor=self.config['roles']['Work']['owner'],authority='original Work software grant')
        self.repo=self.area/'public-source'; self.repo.mkdir()
        self.other=self.area/'public-independent'; self.other.mkdir()
        task=self.config['tasks']['reviews-proposer']
        task.update(execution='owner',network=False,cwd=str(self.repo),binding=reviews.BINDING)
        task['effect_authority']['read_roots']=[str(self.repo)]
        if self.transitioned:Path(self.config['operator_config']).write_text(encode(self.config))
        self.now=100.
        self.s=enrolled(self.config,clock=lambda:self.now)
        self.addCleanup(self.s.close)
        self.owner=self.config['roles']['Reviews']['owner']; self.work=self.config['roles']['Work']['owner']
        self.connection=sqlite3.connect(':memory:',isolation_level=None)
        self.connection.row_factory=sqlite3.Row
        self.addCleanup(self.connection.close)
        self.connection.executescript(EXTENSION+BOARD_SCHEMA+'''
CREATE TABLE sessions(session TEXT PRIMARY KEY,status TEXT);
CREATE TABLE posts(seq INTEGER PRIMARY KEY,recipient TEXT);
CREATE TABLE thread_posts(post_seq INTEGER,thread_id INTEGER);
CREATE TABLE threads(thread_id INTEGER,opener TEXT);
''')
        for actor in (self.owner,self.work):
            self.connection.execute("INSERT INTO sessions VALUES(?,'active')",(actor,))
        self.connection.execute('INSERT INTO posts VALUES(1,?)',(self.owner,))
        self.connection.execute('INSERT INTO thread_posts VALUES(1,1)')
        self.connection.execute('INSERT INTO threads VALUES(1,?)',(self.work,))
        self.principal=Principal(self.work)
        self.boards={r:self.board(r) for r in ('Work','Reviews')}
        if self.transitioned: self.original_transition()
        self.cap=ident()
        original=processing.implementation()
        self.current_implementation=original
        selection=dict(tasks=['reviews-proposer'],future_intake=True,retained_events=[],recover_controls={},
            service={'max_inflight':100,'reviews':{'reviews-proposer':{}}},
            expires=200,max_starts=100,max_runtime_rows=10000,max_shared_rows=10000,max_shared_payload_bytes=1000000,
            basis=dict(configuration=digest(self.config),implementation=original,event_boundary=0,
                roles={r:dict(future_after=0,original=dict(binding=dict(id=self.grants[r],issued_by=self.work),events=[]))
                       for r in ('Work','Reviews')}))
        # Existing db1 capability journal representation; no new witness rows.
        self.s.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)',(self.cap,encode(selection),self.work,100))
        self.s.processing=processing.Access(self.s,self.cap,self.boards)
        # Real original epoch selection/birth protocol, before Source intake.
        for b in self.boards.values(): b.verify_authority=lambda runtime:True  # Original Board launch seam only.
        epoch=prospective.select(self.s,self.work,dict(configuration=digest(self.config),authority='original epoch',expires=200,
            processing_capability=self.cap,grants={'Reviews':self.grants['Reviews']},
            tasks={'reviews-proposer':dict(task_hash=digest(task),software_handoffs={},ordinary_effects=False)}))
        self.epoch=epoch['id']
        source=event(self.config,'original standalone','Reviews','reviews-proposer')
        source.update(kind='board',post=1,grant=self.grants['Reviews'],board_id=self.config['roles']['Reviews']['board_id'])
        source['body']={'review':{'component':'fictional-public-component','origin':'fictional-public-origin',
                                 'base':'a'*40,'head':'b'*40,'previous':None,'answered_ids':[]}}
        self.source=source
        queued(self.s,source)
        job=self.s.reserve()
        if job is None: raise AssertionError('original real reservation unavailable')
        self.job=job['id']
        self.attempt=self.s.start_job(self.job,job['token'])
        job=self.s.job(self.job)
        grant=dict(id=self.grants['Reviews'],issued_by=self.work,authority='original Work software grant',owner=self.owner,
                   prospective_epoch=self.epoch,delegated_by=self.work,delegation_authority='original epoch')
        with patch.object(self.boards['Reviews'],'software_authority',return_value=grant):
            Board.bind_software_attempt(self.boards['Reviews'],self.s,job,self.attempt,None)
        self.s.begin(self.attempt,{'fictional_native_transport':True})
        self.component='fictional-public-component'
        context=dict(component=self.component,capability=self.cap,profile='.codex2',route='OPAQUE-NOT-READ',
            handle='OPAQUE-NOT-READ',run='OPAQUE-NOT-READ',collector=self.s.controller,state='opening',head=None,
            history_hash='f'*64,created=100,closed_at=None)
        self.s.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(context.values()))
        self.s.db.execute('INSERT INTO review_calls VALUES(?,?,?,?,?,NULL,NULL)',
            (self.attempt,self.component,self.s.controller,encode(dict(selected_task='reviews-proposer',source={},correction_diff='FORBIDDEN-BODY')),'prepared'))
        self.s.db.execute('INSERT INTO review_call_contexts VALUES(?,?)',(self.attempt,encode(context)))
        self.identity=dict(job=self.job,attempt=self.attempt,event=source['id'],source_hash=digest(source),
            task='reviews-proposer',capability=self.cap,epoch=self.epoch,component=self.component,collector=self.s.controller,post=1)
        # New metadata API has not been called, and stores NO original witness.
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM historical_metadata_access')['n'],0)
        self.old_proof=self.s.one("SELECT json_extract(detail,'$.software_authority') AS p FROM attempts WHERE id=?",(self.attempt,))
        self.now=300.
        self.s.db.execute('UPDATE processing_capabilities SET revoked=201 WHERE id=?',(self.cap,))
        self.s.db.execute('UPDATE prospective_authorities SET revoked=201 WHERE id=?',(self.epoch,))
        self.s.db.execute("UPDATE attempts SET state='collected',exit=6,ended=200,collected=201,capture='incomplete' WHERE id=?",(self.attempt,))
        self.s.db.execute("UPDATE jobs SET state='held',effects='none',hold_reason='original Source incomplete; whole return conserved through sole report integration' WHERE id=?",(self.job,))
        self.s.db.execute("UPDATE review_contexts SET state='interrupted' WHERE component=?",(self.component,))
        self.s.db.execute('UPDATE enrollments SET intake=0')
        if not self.transitioned: self.connection.execute("UPDATE coordinator_grants_v1 SET revoked='201'")

    def original_transition(self):
        # Preexisting db1 immutable transition, recorded BEFORE epoch/intake.
        # Represents a new source task admitted after the initial software grant.
        old=copy.deepcopy(self.config); del old['tasks']['reviews-proposer']
        self.original_configuration=digest(old)
        self.connection.execute("UPDATE coordinator_grants_v1 SET revoked='90'")
        self.connection.execute('UPDATE coordinator_software_grants_v1 SET configuration=?,policies=\'{}\'',(self.original_configuration,))
        bindings={}
        for role in ('Work','Reviews'):
            grant=dict(self.connection.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?',(self.grants[role],)).fetchone())
            bindings[role]={'original':{'binding':processing.ProcessingBoard._binding(grant)}}
        release=configuration.release(self.s,self.config)
        selection={'basis':{'tasks':['reviews-proposer'],'processing':{'roles':bindings},'release':release},
                   'event_boundary':0,'job_boundary':0,'attempt_boundary':0}
        self.s.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) '
            'VALUES(?,?,?,?,?,?,90)',(self.original_configuration,digest(self.config),self.original_configuration,
            encode(self.config),encode(selection),self.work))
        self.s.db.execute('UPDATE meta SET value=? WHERE key=\'configuration\'',(self.original_configuration,))
        self.s.db.execute('UPDATE enrollments SET intake=0')

    def board(self,role):
        if not hasattr(self,'grants'): self.grants={}
        b=processing.ProcessingBoard.__new__(processing.ProcessingBoard)
        b.role=role; b.config=self.config; b.selected=self.config['roles'][role]; b.store=self.principal
        grant=ident(); self.grants[role]=grant
        info=self.s.path.stat()
        self.connection.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)',
            (grant,b.selected['board_id'],role,b.selected['owner'],b.selected['profile'],self.config['actor'],str(self.s.path),
             info.st_dev,info.st_ino,0,self.work,'original Work software grant','100'))
        self.connection.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?,?)',
            (grant,encode({n:digest(t) for n,t in self.config['tasks'].items() if t['role']==role}),digest(self.config)))
        self.s.db.execute('UPDATE enrollments SET grant_id=? WHERE role=?',(grant,role))
        @contextmanager
        def opened(**options): yield self.connection  # Actual SDK lifecycle/account identity is explicit fiction.
        b.opened=opened
        return b

    def selection(self):
        return dict(identity=self.identity,purpose='current historical journal verification',authority='current Reviews metadata only',
            expires=900,public_roots=[str(self.repo)],fields=list(h.FIELDS),principal=self.work,
            configuration=digest(self.config),implementation=self.current_implementation)

    def authorize(self):
        self.principal.actor=self.owner
        key=h.authorize(self.s,self.boards,self.selection())['metadata_access']
        self.principal.actor=self.work
        return key

    @contextmanager
    def safe_queries(self):
        denied={('jobs','token'),('attempts','session'),('attempts','result'),('attempts','error'),
            ('review_contexts','handle'),('review_contexts','run'),('review_contexts','route'),
            ('review_calls','receipt'),('review_calls','answer'),('results','result')}
        def authorizer(op,table,column,db,trigger):
            if op==sqlite3.SQLITE_READ and (table,column) in denied:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        original=self.s.one
        def bounded(sql,args=()):
            if 'SELECT *' in sql and any(t in sql for t in ('events','attempts','jobs','review_','job_resource')):
                raise AssertionError('whole original body requested')
            if any(term in sql for term in ('$.body','$.handle','$.route','$.run','$.session')):
                raise AssertionError('forbidden JSON projection')
            return original(sql,args)
        self.s.db.set_authorizer(authorizer)
        try:
            with patch.object(self.s,'one',side_effect=bounded): yield
        finally: self.s.db.set_authorizer(None)

    def test_existing_unrecorded_revoked_source_supported_without_renewal(self):
        with self.safe_queries():
            key=self.authorize()
        before=list(self.s.db.iterdump())
        with self.safe_queries():
            facts=h.project(self.s,self.boards,key)
            disjoint=h.compare(self.s,self.boards,key,dict(reads=[],writes=[str(self.other)]))
            conflict=h.compare(self.s,self.boards,key,dict(reads=[],writes=[str(self.repo/'a.py')]))
        self.assertEqual(list(self.s.db.iterdump()),before)
        self.assertEqual(facts['verification'],'verified-scoped-journal-relationships')
        self.assertEqual(facts['public_reads'],[str(self.repo)])
        self.assertEqual(facts['outcome']['END'],6)
        self.assertTrue(facts['original_authority']['epoch_expired'])
        self.assertEqual(disjoint['public_subset'],'disjoint'); self.assertEqual(disjoint['comparison'],'UNKNOWN')
        self.assertEqual(conflict['comparison'],'CONFLICT'); self.assertFalse(conflict['eligible'])
        self.assertEqual(facts['physical'],'UNKNOWN'); self.assertFalse(facts['native_identity_verified'])
        self.assertNotIn('OPAQUE-NOT-READ',encode(facts))
        self.assertEqual(self.old_proof,self.s.one("SELECT json_extract(detail,'$.software_authority') AS p FROM attempts WHERE id=?",(self.attempt,)))
        with self.assertRaises(Refusal):self.s.processing.current()
        for operation in ('current','event'):
            with self.assertRaises(Refusal):
                access=processing.Access(self.s,key,self.boards)
                getattr(access,operation)(*([self.source] if operation=='event' else []))

    def test_current_owner_principal_and_visibility_precede_data(self):
        with self.assertRaises(Refusal):h.authorize(self.s,self.boards,self.selection())
        key=self.authorize()
        self.principal.actor=ident()
        with patch.object(self.s,'one',side_effect=AssertionError('acquired before principal')):
            with self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        self.principal.actor=self.work
        self.connection.execute('DELETE FROM thread_posts')
        with self.safe_queries(),self.assertRaisesRegex(Refusal,'visibility'):h.project(self.s,self.boards,key)

    def test_expiry_revocation_and_source_config_issuer_changes(self):
        key=self.authorize()
        self.now=901
        with self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        self.now=300
        changed=copy.deepcopy(self.config);changed['tasks']['reviews-proposer']['purpose']='different current task'
        with patch.object(self.s,'config',changed),self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        with patch.object(processing,'implementation',return_value={'foreign.py':'f'*64}),self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        self.connection.execute("UPDATE coordinator_grants_v1 SET issued_by=? WHERE id=?",(ident(),self.grants['Reviews']))
        with self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        self.connection.execute('UPDATE coordinator_grants_v1 SET issued_by=? WHERE id=?',(self.work,self.grants['Reviews']))
        self.principal.actor=self.owner;h.revoke(self.s,self.boards,key);self.principal.actor=self.work
        with self.assertRaises(Refusal):h.project(self.s,self.boards,key)

    def test_mutated_or_missing_original_relationships_refuse(self):
        key=self.authorize()
        faults=[
            ("UPDATE jobs SET members=json_set(members,'$[0].hash','wrong') WHERE id=?",self.job),
            ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.grant_id','wrong') WHERE id=?",self.attempt),
            ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.task_hash','wrong') WHERE id=?",self.attempt),
            ("UPDATE attempts SET detail=json_remove(detail,'$.software_authority.admission_hash') WHERE id=?",self.attempt),
            ("UPDATE attempts SET detail=json_set(detail,'$.configuration_sha256','wrong') WHERE id=?",self.attempt),
            ("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','wrong') WHERE id=?",self.attempt),
            ('DELETE FROM prospective_job_positions WHERE job=?',self.job),
            ('UPDATE processing_source_positions SET position=0 WHERE event=?',self.source['id']),
            ("UPDATE prospective_authorities SET selection=json_set(selection,'$.grants.Reviews','wrong') WHERE id=?",self.epoch),
            ("UPDATE processing_capabilities SET issuer='wrong' WHERE id=?",self.cap),
            ("UPDATE review_contexts SET collector='wrong' WHERE component=?",self.component),
            ("UPDATE review_call_contexts SET context=json_set(context,'$.capability','wrong') WHERE attempt=?",self.attempt),
            ('DELETE FROM review_calls WHERE attempt=?',self.attempt),
            ("UPDATE jobs SET hold_reason='opaque duty' WHERE id=?",self.job)]
        for sql,arg in faults:
            with self.subTest(sql=sql):
                self.s.db.execute('SAVEPOINT fault')
                try:
                    self.s.db.execute(sql,(arg,))
                    with self.safe_queries(),self.assertRaises(Refusal):h.project(self.s,self.boards,key)
                finally:
                    self.s.db.execute('ROLLBACK TO fault'); self.s.db.execute('RELEASE fault')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable original'):
            self.s.db.execute("UPDATE job_resource_policies SET task='{}' WHERE job=?",(self.job,))

    def test_held_excluded_opaque_and_forbidden_scope(self):
        key=self.authorize()
        self.s.db.execute("UPDATE events SET hold='privacy' WHERE id=?",(self.source['id'],))
        original=self.s.one
        def no_projection(sql,args=()):
            if 'json_extract(payload' in sql or 'FROM attempts' in sql: raise AssertionError('held data projected')
            return original(sql,args)
        with patch.object(self.s,'one',side_effect=no_projection),self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        self.s.db.execute('UPDATE events SET hold=NULL WHERE id=?',(self.source['id'],))
        with patch.object(resource_scopes,'overlaps',side_effect=AssertionError('excluded metadata')):
            with self.assertRaises(Refusal):h.compare(self.s,self.boards,key,dict(reads=[],writes=['/fixtures/.codex4/private']))
        request=self.selection(); request['fields'].append('native-handle')
        self.principal.actor=self.owner
        with self.assertRaises(Refusal):h.authorize(self.s,self.boards,request)
        self.principal.actor=self.work
        self.s.db.execute("UPDATE review_contexts SET handle='changed opaque',run='changed opaque' WHERE component=?",(self.component,))
        facts=h.project(self.s,self.boards,key)
        self.assertFalse(facts['native_identity_verified']);self.assertFalse(facts['closure']);self.assertFalse(facts['eligible'])

    def test_current_metadata_is_not_an_original_witness_or_effect_selection(self):
        request=self.selection();request['identity']={**self.identity,'attempt':ident()}
        self.principal.actor=self.owner
        key=h.authorize(self.s,self.boards,request)['metadata_access'];self.principal.actor=self.work
        with self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        self.assertEqual(self.s.one('SELECT active_attempt FROM jobs WHERE id=?',(self.job,))['active_attempt'],self.attempt)
        request=self.selection();request['execution']=True;self.principal.actor=self.owner
        with self.assertRaises(Refusal):h.authorize(self.s,self.boards,request)

    def test_original_expiry_only_and_public_membership_are_not_execution(self):
        self.s.db.execute('UPDATE processing_capabilities SET revoked=NULL WHERE id=?',(self.cap,))
        self.s.db.execute('UPDATE prospective_authorities SET revoked=NULL WHERE id=?',(self.epoch,))
        key=self.authorize()
        facts=h.project(self.s,self.boards,key)
        self.assertTrue(facts['original_authority']['epoch_expired'])
        self.assertFalse(facts['original_authority']['epoch_revoked'])
        with self.assertRaises(Refusal):prospective.current(self.s,'reviews-proposer',self.epoch)
        request=self.selection();request['public_roots']=[str(self.other)]
        self.principal.actor=self.owner
        key=h.authorize(self.s,self.boards,request)['metadata_access'];self.principal.actor=self.work
        self.assertEqual(h.project(self.s,self.boards,key)['public_reads'],[])

    def test_cli_entry_routes_and_no_expired_execution_check(self):
        from coordinator_runtime import cli
        key=self.authorize()
        args=cli.parser().parse_args(['historical-metadata-project',key])
        with patch.object(processing,'ProcessingBoard',side_effect=lambda config,role:self.boards[role]):
            with patch.object(self.s.processing,'current',side_effect=AssertionError('expired execution called')):
                self.assertEqual(cli.operate(args,self.s)['verification'],'verified-scoped-journal-relationships')
        with self.s.tx(),self.assertRaises(Refusal):
            resource_scopes._native_resources(self.s,dict(id=self.job,task='reviews-proposer'),self.config['tasks']['reviews-proposer'])

    def test_original_transition_and_frozen_task_not_current_substitute(self):
        key=self.authorize()
        with self.safe_queries(): facts=h.project(self.s,self.boards,key)
        self.assertEqual(facts['verification'],'verified-scoped-journal-relationships')
        self.assertEqual(facts['public_reads'],[str(self.repo)])
        self.assertNotEqual(self.original_configuration,digest(self.config))
        self.assertEqual(self.connection.execute('SELECT policies FROM coordinator_software_grants_v1 WHERE grant_id=?',
            (self.grants['Reviews'],)).fetchone()[0],'{}')
        # A fabricated/missing preexisting transition cannot be replaced by the
        # metadata selection or by a current task. Schema itself refuses edits.
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable configuration'):
            self.s.db.execute("UPDATE configuration_transitions SET issuer='wrong'")
        self.s.db.execute('SAVEPOINT missing_original_epoch')
        try:
            self.s.db.execute('DELETE FROM prospective_authorities WHERE id=?',(self.epoch,))
            with self.assertRaises(Refusal):h.project(self.s,self.boards,key)
        finally:
            self.s.db.execute('ROLLBACK TO missing_original_epoch');self.s.db.execute('RELEASE missing_original_epoch')

    def test_current_metadata_residency_is_bounded_without_old_body_accounting(self):
        key=self.authorize()
        self.principal.actor=self.owner
        with self.safe_queries(),self.assertRaisesRegex(Refusal,'residency ceiling'):
            h.authorize(self.s,self.boards,self.selection())
        self.principal.actor=self.work
        self.assertEqual(h.project(self.s,self.boards,key)['outcome']['END'],6)
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM historical_metadata_access')['n'],1)
