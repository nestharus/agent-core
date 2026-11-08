"""Decision1036: real mapper and grant gates over a private fictional journal.

No provider/Board SDK/native caller is loaded. Session and Board-grant checkers
are explicit fictional external seams; they do not prove actual principal facts.
"""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import retained_comparison as comparison
from coordinator_runtime import configuration, processing, prospective, resource_scopes, reviews, ref_scope
from coordinator_runtime.contracts import Refusal, digest, encode, ident


class Principal:
    def __init__(self, owner):
        self.actor = owner

    def acting_session(self, expected):
        if self.actor != expected:
            raise Refusal('fictional authenticated session differs')
        return self.actor


class Board:
    def __init__(self, owner, grant):
        self.store = Principal(owner)
        self.grant = grant
        self.valid = True

    def verify_authority(self, runtime):
        if not self.valid:
            raise Refusal('fictional original Board binding revoked/changed')
        return True

    def metadata_authority(self, runtime):
        return self.verify_authority(runtime)

    def software_authority(self, runtime, name):
        self.verify_authority(runtime)
        return self.grant


class Journal:
    def __init__(self):
        self.home = Path('/fixtures/journal')
        self.home.mkdir(parents=True, exist_ok=True)
        self.now = 100.
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.processing = None
        self.controller = ident()

    def clock(self):
        return self.now

    def one(self, sql, args=()):
        row = self.db.execute(sql, args).fetchone()
        return dict(row) if row is not None else None

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    @contextmanager
    def tx(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def enrollment(self, role):
        return {'grant_id': self.grant['id']}


class RetainedComparison1036(unittest.TestCase):
    def setUp(self):
        self.s = s = Journal()
        self.addCleanup(s.db.close)
        s.db.executescript(comparison.SCHEMA + configuration.SCHEMA + processing.SCHEMA + prospective.SCHEMA + reviews.SCHEMA + ref_scope.SCHEMA + '''
CREATE TABLE jobs(id TEXT PRIMARY KEY,role,phase,task,package,active_attempt,state,hold_reason,members,effects);
CREATE TABLE attempts(id TEXT PRIMARY KEY,job,kind,controller,profile,binding,state,exit,begin,ended,collected,capture,error,session,detail);
CREATE TABLE events(id TEXT PRIMARY KEY,role,hold,hash,payload);
CREATE TABLE admissions(package,receipt);
CREATE TABLE ordinary_runs(attempt,job);
CREATE TABLE routine_runs(attempt);
''')
        owner, reviewer = ident(), ident()
        self.cap, self.epoch, self.attempt, self.job, self.event = [ident() for _ in range(5)]
        self.repo = Path('/fixtures/source'); self.repo.mkdir(exist_ok=True)
        self.method = Path('/fixtures/method.md'); self.method.write_text('fictional original public method')
        self.history = s.home/'review-history'/'public-history.json'
        self.history.parent.mkdir(exist_ok=True)
        task = dict(role='Reviews',phase='proposer',execution='owner',sandbox='read-only',effects='none',network=False,
                    cwd=str(self.repo),effect_authority=dict(owner=reviewer,operations=['read-source'],read_roots=[str(self.repo),str(self.method)],write_roots=[]))
        s.config = dict(roles={'Work':{'owner':owner},'Reviews':{'owner':reviewer}}, software_delegation={'grantor':owner},
                        tasks={'source':task}, artifact_exclusions=['/fictional/excluded'])
        self.packet = dict(component='fictional-source',origin='fictional-public-origin',base='a'*40,head='b'*40,previous=None,answered_ids=[])
        policy = dict(caller='/fictional/public-caller',caller_sha256=resource_scopes.RESOURCE_CALLER_SHA256,
                      method_files=[str(self.method)],routes={'.codex2':'fictional-route'},components={self.packet['component']:dict(
                          origin=self.packet['origin'],repository=str(self.repo),paths=['public.py'],history=str(self.history),authority='fictional public read authority')})
        s.grant = dict(id=ident(),issued_by=owner,authority='fictional original Work grant',owner=reviewer,prospective_epoch=self.epoch)
        self.boards = {'Work':Board(owner,s.grant),'Reviews':Board(owner,s.grant)}
        self.proof = dict(grant_id=s.grant['id'],issued_by=owner,authority=s.grant['authority'],role_owner=reviewer,
                          task_hash=digest(task),admission_hash=None,prospective_epoch=self.epoch,delegated_by=owner,
                          delegation_authority='fictional epoch authority',processing_capability=self.cap)
        self.selection = dict(tasks=['source'], future_intake=True,basis=dict(configuration=digest(s.config),implementation=processing.implementation(),
                                event_boundary=0,roles={'Reviews':{'future_after':0}}), service=dict(reviews={'source':policy},legacy_resources={'Reviews':dict(
                                    unbounded=True, original_hold='fictional unbounded old custody',roots=[],evidence='fictional custodian account',
                                    native_review_return=dict(version='native-collected-review-v1',source_task='source',package=None,grant=s.grant['id'],
                                      source_task_sha256=digest(task),review_policy_sha256=digest(policy),packet_sha256=digest(self.packet),expires=200,component=self.packet['component']))}))
        s.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)', (self.cap,encode(self.selection),owner,100))
        epoch_selection=dict(configuration=digest(s.config),authority='fictional epoch authority',expires=200,grants={'Reviews':s.grant['id']},
                             tasks={'source':dict(task_hash=digest(task),software_handoffs={},ordinary_effects=False)},grantor=owner,processing_capability=self.cap,job_birth='observed-v1')
        s.db.execute('INSERT INTO prospective_authorities VALUES(?,?,?,?,?,NULL)',(self.epoch,encode(epoch_selection),0,0,100))
        s.db.execute('INSERT INTO prospective_job_positions(position,job) VALUES(1,?)',(self.job,))
        s.db.execute('INSERT INTO processing_source_positions(position,event) VALUES(1,?)',(self.event,))
        source=dict(kind='board',post=1,branch_binding=None,body={'review':self.packet})
        self.source_hash=digest(source)
        s.db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(self.event,'Reviews',None,self.source_hash,encode(source)))
        s.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)',(self.job,'Reviews','proposer','source',None,self.attempt,'running',None,encode([dict(event=self.event,hash=self.source_hash)]),'unknown'))
        s.db.execute('INSERT INTO job_resource_policies VALUES(?,?,NULL)',(self.job,encode(task)))
        s.db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(self.attempt,self.job,'task',s.controller,'.codex2',encode(reviews.BINDING),'running',None,100,None,None,'unknown',None,None,encode(dict(processing_capability=self.cap,software_authority=self.proof))))
        context=dict(component=self.packet['component'],capability=self.cap,profile='.codex2',route='fictional-route',handle=str(s.home/'review-handles'/self.attempt),
                     run=None,collector=s.controller,state='opening',head=None,history_hash='c'*64,created=100,closed_at=None)
        s.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(context.values()))
        acquired=dict(selected_task='source',packet=self.packet,repository=str(self.repo),method_files=[str(self.method)],prior_histories={},
                      history=str(self.history),read_authority='fictional public read authority',relationship_paths=[],history_sha256='c'*64,
                      source={'a'*40+':public.py':dict(git_blob='d'*40,sha256='e'*64,bytes=12)})
        s.db.execute('INSERT INTO review_calls VALUES(?,?,?,?,?,NULL,NULL)',(self.attempt,self.packet['component'],s.controller,encode(acquired),'prepared'))
        s.db.execute('INSERT INTO review_call_contexts VALUES(?,?)',(self.attempt,encode(context)))
        s.processing=processing.Access(s,self.cap,self.boards)
        self.pin = comparison.record_current(s,dict(id=self.job,task='source'))

    def select(self):
        request=dict(mode=comparison.MODE,purpose='current genuine Work metadata comparison over exact public original witness',expires=900,pins=[self.pin])
        self.key=comparison.select(self.s,self.boards,request)['key']
        return self.key

    def expire_original(self):
        self.s.now=300
        self.s.db.execute('UPDATE processing_capabilities SET revoked=201 WHERE id=?',(self.cap,))
        self.s.db.execute('UPDATE prospective_authorities SET revoked=201 WHERE id=?',(self.epoch,))
        self.s.db.execute("UPDATE attempts SET state='collected',exit=6,ended=200,collected=201,capture='incomplete' WHERE id=?",(self.attempt,))
        self.s.db.execute("UPDATE jobs SET state='held',effects='none',hold_reason='fictional unresolved old hold' WHERE id=?",(self.job,))
        self.s.db.execute("UPDATE review_contexts SET state='interrupted' WHERE component=?",(self.packet['component'],))

    @contextmanager
    def no_old_bodies(self):
        # SQLite's authorizer is independent of helper naming: fail on any
        # forbidden column before SQLite even evaluates an expression over it.
        denied = {('events','payload'),('job_resource_policies','task'),('job_resource_policies','admission'),
                  ('review_calls','packet'),('review_calls','receipt'),('review_calls','answer'),
                  ('review_call_contexts','context'),('review_contexts','handle'),('review_contexts','run'),
                  ('attempts','session'),('attempts','error')}
        def authorizer(op, table, column, database, trigger):
            if op==sqlite3.SQLITE_READ and (table,column) in denied:
                raise AssertionError('forbidden old acquisition '+table+'.'+column)
            return sqlite3.SQLITE_OK
        self.s.db.set_authorizer(authorizer)
        try:
            yield
        finally:
            self.s.db.set_authorizer(None)

    def test_expired_revoked_original_distinct_metadata_authority_and_real_overlap(self):
        self.expire_original()
        self.select()
        before=list(self.s.db.iterdump())
        with self.no_old_bodies():
            record=comparison.project(self.s,self.boards,self.key,self.job)
            separated=comparison.compare(self.s,self.boards,self.key,self.job,dict(reads=['/fixtures/separate'],writes=[]))
            conflict=comparison.compare(self.s,self.boards,self.key,self.job,dict(reads=['/fixtures/separate'],writes=[str(self.repo/'public.py')]))
        self.assertEqual(record['original_proof'], self.proof)
        self.assertEqual(record['original_capability'],self.cap)
        self.assertTrue(separated['scoped_disjoint'])
        self.assertEqual(separated['status'],'UNKNOWN')  # unbounded old/native hold survives
        self.assertEqual(conflict['status'],'CONFLICT')
        self.assertFalse(conflict['eligible'])
        self.assertTrue(record['opaque_constraints'])
        self.assertFalse(any('review-handles' in p or 'review-history' in p or 'review-inputs' in p for p in record['scope']['reads'] + record['scope']['writes']))
        self.assertEqual(list(self.s.db.iterdump()),before)
        with self.assertRaises(Refusal):self.s.processing.current()
        with self.s.tx(),self.assertRaises(Refusal):
            resource_scopes._native_resources(self.s,dict(id=self.job,task='source'),self.s.config['tasks']['source'])

    def test_no_original_backfill_and_no_comparison_grant_execution_or_old_input(self):
        self.select(); self.expire_original()
        with self.assertRaises(Refusal):comparison.record_current(self.s,dict(id=self.job,task='source'))
        comparison_access=processing.Access(self.s,self.key,self.boards)
        with self.assertRaisesRegex(Refusal,'processing capability absent'):comparison_access.current()
        with self.assertRaisesRegex(Refusal,'processing capability absent'):comparison_access.event(dict(id=self.event,role='Reviews'))
        request=dict(mode='execution',purpose='replay',expires=900,pins=[self.pin])
        with self.assertRaises(Refusal):comparison.select(self.s,self.boards,request)
        absent=copy.deepcopy(self.pin);absent['job']=ident()
        key=comparison.select(self.s,self.boards,dict(mode=comparison.MODE,purpose='only unknown original',expires=900,pins=[absent]))['key']
        with self.no_old_bodies(),self.assertRaisesRegex(Refusal,'no backfill'):comparison.project(self.s,self.boards,key,absent['job'])

    def test_production_metadata_binding_does_not_borrow_processing_authority(self):
        self.expire_original()
        board=processing.ProcessingBoard.__new__(processing.ProcessingBoard)
        board.role='Work'
        @contextmanager
        def opened(**options):
            self.assertEqual(options,dict(settlement=True))
            yield 'fictional Board connection'
        board.opened=opened
        def original(conn,runtime):
            self.assertEqual(conn,'fictional Board connection')
            self.assertIs(runtime,self.s)
            return {'original':'fictional authenticated journal binding'}
        board._original=original
        with patch.object(self.s.processing,'current',side_effect=AssertionError('expired execution accessed')):
            self.assertEqual(board.metadata_authority(self.s),{'original':'fictional authenticated journal binding'})
        board.role='Reviews'
        with self.assertRaises(Refusal):board.metadata_authority(self.s)

    def test_original_expiry_alone_and_epoch_revocation_do_not_renew_execution(self):
        self.select()
        self.s.now=201
        with self.no_old_bodies():
            self.assertEqual(comparison.project(self.s,self.boards,self.key,self.job)['original_proof'],self.proof)
        with self.s.tx(),self.assertRaisesRegex(Refusal,'expired/revoked'):
            resource_scopes._native_resources(self.s,dict(id=self.job,task='source'),self.s.config['tasks']['source'])
        self.s.now=100
        self.s.db.execute('UPDATE prospective_authorities SET revoked=100 WHERE id=?',(self.epoch,))
        with self.no_old_bodies():
            self.assertEqual(comparison.project(self.s,self.boards,self.key,self.job)['physical'],'UNKNOWN')
        with self.s.tx(),self.assertRaisesRegex(Refusal,'expired/revoked'):
            resource_scopes._native_resources(self.s,dict(id=self.job,task='source'),self.s.config['tasks']['source'])

    def test_new_source_hold_precedes_witness_acquisition(self):
        self.select();self.expire_original()
        self.s.db.execute("UPDATE events SET hold='unbounded newly forbidden source' WHERE id=?",(self.event,))
        original=self.s.one
        def guarded(sql,args=()):
            if 'SELECT record FROM retained_comparison_witnesses' in sql:
                self.fail('witness acquired after source exclusion')
            return original(sql,args)
        with patch.object(self.s,'one',side_effect=guarded),self.no_old_bodies(),self.assertRaisesRegex(Refusal,'source held'):
            comparison.project(self.s,self.boards,self.key,self.job)

    def test_mutated_linkage_refuses_and_witnesses_are_immutable(self):
        self.select();self.expire_original()
        for sql,args in [
            ('UPDATE attempts SET controller=? WHERE id=?',(ident(),self.attempt)),
            ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.grant_id','wrong') WHERE id=?",(self.attempt,)),
            ('DELETE FROM review_calls WHERE attempt=?',(self.attempt,)),
            ('DELETE FROM review_call_contexts WHERE attempt=?',(self.attempt,)),
            ('DELETE FROM prospective_authorities WHERE id=?',(self.epoch,)),
            ("UPDATE events SET hash='mutated' WHERE id=?",(self.event,)),
            ('UPDATE processing_source_positions SET position=50 WHERE event=?',(self.event,)),
            ('UPDATE prospective_job_positions SET position=50 WHERE job=?',(self.job,)),
            ("UPDATE processing_capabilities SET issuer='different' WHERE id=?",(self.cap,)),
            ('UPDATE review_contexts SET collector=? WHERE component=?',(ident(),self.packet['component'])),
            ('UPDATE jobs SET active_attempt=? WHERE id=?',(ident(),self.job))]:
            self.s.db.execute('SAVEPOINT mutation')
            self.s.db.execute(sql,args)
            with self.no_old_bodies(),self.assertRaises(Refusal):comparison.project(self.s,self.boards,self.key,self.job)
            self.s.db.execute('ROLLBACK TO mutation');self.s.db.execute('RELEASE mutation')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable'):
            self.s.db.execute("UPDATE retained_comparison_witnesses SET record='{}'")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable'):
            self.s.db.execute('DELETE FROM retained_comparison_grants')

    def test_current_authority_source_configuration_issuer_expiry_and_revocation(self):
        self.select();self.expire_original()
        self.boards['Work'].store.actor=ident()
        with self.assertRaises(Refusal):comparison.project(self.s,self.boards,self.key,self.job)
        self.boards['Work'].store.actor=self.s.config['roles']['Work']['owner']
        self.boards['Work'].valid=False
        with self.assertRaises(Refusal):comparison.project(self.s,self.boards,self.key,self.job)
        self.boards['Work'].valid=True
        alternate=Path('/fixtures/changed-public-source');alternate.mkdir()
        current=json.loads(self.s.one('SELECT selection FROM retained_comparison_grants WHERE id=?',(self.key,))['selection'])['source']
        for name in current:
            (alternate/name).write_bytes((Path(comparison.__file__).parent/name).read_bytes())
        with (alternate/'contracts.py').open('ab') as stream:
            stream.write(b'\n# different actual current source bytes\n')
        with patch.object(comparison,'__file__',str(alternate/'retained_comparison.py')),self.assertRaisesRegex(Refusal,'source/configuration'):
            comparison.project(self.s,self.boards,self.key,self.job)
        self.s.config['tasks']['source']['cwd']='/fictional/different-current-task'
        with self.assertRaises(Refusal):comparison.project(self.s,self.boards,self.key,self.job)
        self.s.config['tasks']['source']['cwd']=str(self.repo)
        self.s.now=901
        with self.assertRaises(Refusal):comparison.project(self.s,self.boards,self.key,self.job)
        self.s.now=300
        comparison.revoke(self.s,self.boards,self.key)
        with self.assertRaisesRegex(Refusal,'revoked'):comparison.project(self.s,self.boards,self.key,self.job)

    def test_exclusion_before_witness_acquisition_and_metadata_unknown_aliases(self):
        bad=copy.deepcopy(self.pin);bad['scope']['writes'].append('/fictional/excluded/secret')
        with patch.object(Path,'stat',side_effect=AssertionError('metadata before lexical exclusion')),self.assertRaises(Refusal):
            comparison.select(self.s,self.boards,dict(mode=comparison.MODE,purpose='forbidden',expires=900,pins=[bad]))
        self.select();self.expire_original()
        with self.no_old_bodies(),patch.object(Path,'stat',side_effect=AssertionError('forbidden candidate stat')),self.assertRaises(Refusal):
            comparison.compare(self.s,self.boards,self.key,self.job,dict(reads=['/fictional/excluded/secret'],writes=[]))
        with self.no_old_bodies(),patch.object(resource_scopes,'overlaps',side_effect=OSError('unavailable identity')):
            result=comparison.compare(self.s,self.boards,self.key,self.job,dict(reads=['/fixtures/separate'],writes=['/fixtures/separate-output']))
        self.assertEqual(result['status'],'UNKNOWN');self.assertIsNone(result['scoped_overlap'])
        alias=Path('/fixtures/alias');alias.symlink_to(self.repo,target_is_directory=True)
        with self.no_old_bodies():
            result=comparison.compare(self.s,self.boards,self.key,self.job,dict(reads=[str(alias)],writes=[]))
        self.assertEqual(result['status'],'UNKNOWN')


if __name__=='__main__':
    unittest.main(verbosity=2)
