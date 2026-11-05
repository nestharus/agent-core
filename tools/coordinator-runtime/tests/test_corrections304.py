"""Explicit local fiction only; native session/profile/turn fields remain NULL.

Complete public Board schema is real source; actor/custodian/clock/control facts
are isolated projections, never genuine consent, native operation or elapsed24h.
"""
import asyncio
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from test_act268 import Shared, Engineering
from coordinator_runtime import capacity,reviews,service_recovery
from coordinator_runtime.appserver import thread_request
from coordinator_runtime.contracts import Refusal,digest,encode,report_only
from coordinator_runtime.dispatcher import execution_spec,job_prompt


class PublicCustody(Shared):
    def setUp(self):
        super().setUp()
        self.runtime.config['software_delegation']={'grantor':'fictional-issuer'}
        self.runtime.config['delivery']['recipients']['Work']={'session':'fictional-recipient'}
        self.continuing()
        self.board_instance=self.board()
        self.addCleanup(self.board_instance.database.__exit__,None,None,None)

    def setup_delivery(self):
        board=self.board_instance
        root,key,post=self.create(board,0)
        return board,key,post,self.custody_receipt(board,key)

    def release(self,result,completed):
        witness=json.loads(Path(result['canonical_archive']).read_text())
        return {'hash':digest(witness),'qualified_at':self.runtime.clock(),
                'holds':{h:[] for h in capacity.HOLDS},'evidence':'fictional all-custodian release',
                'originals':{name:{'hash':digest(value),'custodian':'fictional-original-custodian',
                                  'evidence':'fictional preserved whole original'}
                             for name,value in witness['original']['material'].items()},
                'custodian':'fictional-archive-custodian',
                'processing':{'completed_at':completed,'evidence':'fictional archive consumer completed, not just publication'}}

    def test_full_schema_and_ordinary_foreign_immutability_after_allowed_retirement(self):
        board,key,post,receipt=self.setup_delivery()
        conn=board.conn
        guards={r['name']:r['sql'] for r in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")}
        self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0],4)
        self.assertTrue({'posts_no_delete','threads_no_delete','thread_posts_no_delete'}<=set(guards))
        foreign=conn.execute("INSERT INTO posts(author,topic,kind,text,created_at) VALUES('fictional-foreign','ordinary','status','conserve foreign','fictional time')").lastrowid
        conn.execute("INSERT INTO threads VALUES(?,'ordinary','ordinary','fictional-foreign','fictional time')",(foreign,))
        conn.execute('INSERT INTO thread_posts VALUES(?,?)',(foreign,foreign))
        result=board.retire_shared_custody(self.runtime,key,receipt)
        self.assertIsNone(conn.execute('SELECT seq FROM posts WHERE seq=?',(post,)).fetchone())
        self.assertEqual(guards,{r['name']:r['sql'] for r in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")})
        for table,column in [('posts','seq'),('threads','thread_id'),('thread_posts','post_seq')]:
            with self.subTest(table=table):
                with self.assertRaises(sqlite3.IntegrityError): conn.execute(f'DELETE FROM {table} WHERE {column}=?',(foreign,))
                with self.assertRaises(sqlite3.IntegrityError): conn.execute(f'UPDATE {table} SET {column}={column} WHERE {column}=?',(foreign,))
        self.assertEqual(conn.execute('SELECT text FROM posts WHERE seq=?',(foreign,)).fetchone()[0],'conserve foreign')
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM coordinator_pointer_retirement_guard').fetchone()[0],0)
        self.assertEqual(result['conserved_at'],90000.)

    def test_refused_authority_recipient_marker_transport_attachment_and_foreign_link(self):
        board=self.board_instance
        cases={
            'issuer':("UPDATE coordinator_grants_v1 SET issued_by='fictional-foreign'",()),
            'recipient':("UPDATE coordinator_deliveries_v1 SET recipient='fictional-foreign'",()),
            'marker':("UPDATE posts SET ref='ordinary' WHERE seq=?",None),
            'transport':("UPDATE notification_outbox SET delivery_state='ambiguous' WHERE post_seq=?",None),
            'attachment':("INSERT INTO attachments VALUES(?,1,'fictional-required-attachment')",None),
            'foreign-link':("INSERT INTO thread_posts VALUES(?,?)",None),
        }
        # Each refused case has a fresh isolated database; no cleanup of evidence.
        for n,(name,(sql,args)) in enumerate(cases.items()):
            if n:
                board=self.board_instance=self.board()
                self.addCleanup(board.database.__exit__,None,None,None)
            _,key,post=self.create(board,n)
            if name=='marker':
                # Ordinary SQL cannot rewrite it; test the helper's attribution
                # refusal via a newly inserted non-generated pointer instead.
                with self.assertRaises(sqlite3.IntegrityError): board.conn.execute(sql,(post,))
                wrong=board.conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,ref,created_at) VALUES(?,'fictional-recipient','ordinary','status','keep','ordinary','fictional time')",(self.runtime.config['actor'],)).lastrowid
                board.conn.execute('UPDATE coordinator_deliveries_v1 SET post=? WHERE id=?',(wrong,key))
            elif name=='foreign-link':
                foreign=board.conn.execute("INSERT INTO posts(author,topic,kind,text,created_at) VALUES('fictional-foreign','ordinary','status','foreign reply','fictional time')").lastrowid
                board.conn.execute(sql,(foreign,post))
            else: board.conn.execute(sql,(post,) if args is None else args)
            proof={'basis':'fictional exact qualification','archive_hash':'fictional archive hash',
                   'recipient':'fictional-recipient','evidence':'fictional conservation receipt'}
            with self.subTest(case=name):
                with self.assertRaisesRegex(board.store.UserError,'owned coordinator|producer-owned|notification uncertainty|foreign reply/attachment'):
                    with board.store.write(board.conn):
                        board.store.retire_coordinator_pointer(board.conn,key,'fictional-issuer',proof)
                self.assertIsNotNone(board.conn.execute('SELECT id FROM coordinator_deliveries_v1 WHERE id=?',(key,)).fetchone())
                self.assertIsNotNone(board.conn.execute('SELECT seq FROM posts WHERE seq=?',(post,)).fetchone())
            # Select a distinct exact database file for the next case.
            self.directory=self.directory/('fictional-next-'+str(n)); self.directory.mkdir()

    def test_rollback_after_pointer_delete_preserves_archive_intent_and_all_rows(self):
        board,key,post,receipt=self.setup_delivery()
        before=[tuple(r) for r in board.conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")]
        original=board.store.retire_coordinator_pointer
        def interrupted(*args):
            original(*args)
            raise OSError('fictional interruption before shared transaction commit')
        with patch.object(board.store,'retire_coordinator_pointer',side_effect=interrupted):
            with self.assertRaises(OSError): board.retire_shared_custody(self.runtime,key,receipt)
        self.assertIsNotNone(board.conn.execute('SELECT seq FROM posts WHERE seq=?',(post,)).fetchone())
        self.assertIsNotNone(board.conn.execute('SELECT post_seq FROM thread_posts WHERE post_seq=?',(post,)).fetchone())
        self.assertEqual(before,[tuple(r) for r in board.conn.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")])
        self.assertTrue(Path(receipt['archive']).is_file())
        intent=self.runtime.one('SELECT * FROM shared_custody_intents WHERE delivery=?',(key,))
        self.assertEqual(intent['state'],'prepared'); self.assertIsNone(intent['receipt'])
        with self.assertRaises(Refusal): board.reconcile_shared_custody(self.runtime,key)

    def test_delayed_publication_processing_boundary_and_each_hold(self):
        board,key,post,receipt=self.setup_delivery()
        receipt['qualified_at']=89941.
        original=board.store.retire_coordinator_pointer
        def delayed(*args):
            result=original(*args)
            self.runtime.clock=lambda:90030.
            return result
        with patch.object(board.store,'retire_coordinator_pointer',side_effect=delayed):
            result=board.retire_shared_custody(self.runtime,key,receipt)
        self.assertEqual(result['conserved_at'],90030.)
        completed=90120.  # Explicit later custodian processing, not fsync/publication.
        for now,claim in [(89941.+86400,completed),(90030.+86400,completed),
                          (completed+86400-0.001,completed),(completed+86400,90029.)]:
            self.runtime.clock=lambda:now
            with self.assertRaises(Refusal): board.release_shared_archive(self.runtime,key,self.release(result,claim))
            self.assertTrue(Path(receipt['archive']).exists())
        self.runtime.clock=lambda:completed+86400
        release=self.release(result,completed)
        for hold in capacity.HOLDS:
            bad={**release,'holds':{**release['holds'],hold:['fictional unresolved obligation']}}
            with self.subTest(hold=hold):
                with self.assertRaises(Refusal): board.release_shared_archive(self.runtime,key,bad)
        released=board.release_shared_archive(self.runtime,key,release)
        self.assertTrue(released['removed_owned_copy'])
        self.assertEqual(released['receipt']['processing']['completed_at'],completed)

    def test_lost_return_reconciles_without_inventing_original_completion_or_resetting_clock(self):
        board,key,post,receipt=self.setup_delivery()
        original=self.runtime.tx
        calls=0
        @contextmanager
        def lose_return():
            nonlocal calls
            calls+=1
            if calls==2: raise OSError('fictional loss after shared commit before local result')
            with original(): yield
        with patch.object(self.runtime,'tx',lose_return):
            with self.assertRaises(OSError): board.retire_shared_custody(self.runtime,key,receipt)
        self.assertIsNone(board.conn.execute('SELECT seq FROM posts WHERE seq=?',(post,)).fetchone())
        self.assertEqual(self.runtime.one('SELECT state FROM shared_custody_intents')['state'],'prepared')
        self.runtime.clock=lambda:91000.
        result=board.reconcile_shared_custody(self.runtime,key)
        self.assertEqual(result['conserved_at'],91000.)
        self.runtime.clock=lambda:92000.
        self.assertEqual(board.reconcile_shared_custody(self.runtime,key),result)
        self.runtime.clock=lambda:90000.+86400
        with self.assertRaises(Refusal): board.release_shared_archive(self.runtime,key,self.release(result,91000.))
        self.assertTrue(Path(receipt['archive']).exists())


class Recovery(Engineering):
    def context(self):
        self.continuing()
        self.runtime.db.execute('DROP TABLE review_contexts')
        self.runtime.db.executescript(reviews.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT'))
        self.runtime.db.execute('INSERT INTO review_contexts VALUES(?,?,NULL,?,?,NULL,?,?,?,?,?,NULL)',
            ('fictional-component',self.key,'fictional-unused-route','/fixtures/unopened-handle',
             'fictional-lost-original','interrupted',None,reviews.sha(b''),1000))
        self.event('fictional-old','Work','wp',queued=False)
        with self.runtime.tx():
            attempt=self.runtime._attempt('input-control','fictional-old',None,{'model':'gpt-6.1-sol','effort':'high','provider':'openai'},None)
        return attempt

    def disposition(self,activity='inactive',holds=None):
        current=service_recovery.review_basis(self.runtime,'fictional-component')
        return {'basis':current['basis'],'activity':activity,'evidence':'fictional owner-supported disposition',
                'custodian':'fictional-original-custodian','remaining_holds':holds or [],'history_hash':reviews.sha(b'')}

    def test_all_produced_unfinished_states_require_custody_for_inactive_and_unknown(self):
        attempt=self.context()
        for state in ['launch-intent','prepared','owned','admitted-unknown','collected','future-unrecognized']:
            self.runtime.db.execute('DELETE FROM review_calls')
            self.runtime.db.execute('INSERT INTO review_calls VALUES(?,?,?,?,?,NULL,NULL)',
                (attempt,'fictional-component','fictional-lost-original','{}',state))
            for activity in ['inactive','unknown']:
                with self.subTest(state=state,activity=activity):
                    with self.assertRaises(Refusal): service_recovery.recover_review(self.runtime,'fictional-issuer','fictional-component',self.disposition(activity))
            self.assertIsNotNone(self.runtime.one('SELECT component FROM review_contexts'))
        self.runtime.db.execute("UPDATE review_calls SET state='launch-intent'")
        original=self.runtime.attempt(attempt)
        saved=service_recovery.recover_review(self.runtime,'fictional-issuer','fictional-component',
            self.disposition('unknown',['fictional original caller/native/effect custody']))
        self.assertFalse(saved['successor_admissible'])
        saved=service_recovery.recover_review(self.runtime,'fictional-issuer','fictional-component',
            self.disposition('inactive',['fictional original caller/native/effect custody']))
        self.assertTrue(saved['successor_admissible']); self.assertFalse(saved['same_session_continuity'])
        self.assertEqual(self.runtime.attempt(attempt),original)
        self.assertEqual(saved['originals_and_obligations']['calls'][0]['state'],'launch-intent')
        self.assertEqual(self.runtime.one('SELECT state FROM review_calls')['state'],'launch-intent')
        self.runtime.controller='fictional-successor-collector'
        self.event('fictional-independent','Work','wp',queued=False)
        fresh=self.runtime.claim_classification()
        self.assertIsNotNone(fresh)
        self.assertIsNone(self.runtime.attempt(attempt)['exit'])
        self.assertIsNone(self.runtime.attempt(attempt)['collected'])
        self.assertIsNone(self.runtime.attempt(attempt)['session'])
        self.assertIsNone(self.runtime.attempt(attempt)['profile'])

    def test_affirmative_collected_no_start_allows_successor_without_invented_end(self):
        attempt=self.context()
        self.runtime.db.execute('INSERT INTO review_calls VALUES(?,?,?,?,?,NULL,NULL)',
            (attempt,'fictional-component','fictional-lost-original','{}','prepared'))
        context={'component':'fictional-component','route':'fictional-unused-route',
                 'handle':'/fixtures/unopened-handle','profile':None,'run':None}
        policy={'caller':'/fictional/not-installed-caller','deadline':1}
        launch=[]
        async def refused(*args,**kwargs):
            launch.append(args)
            raise FileNotFoundError('fictional affirmative local executable absence; no native caller created')
        # Local pool seam only; no native account enrollment/admission fact.
        with patch.object(self.runtime.execution_pool,'admission',return_value=reviews._existing(),create=True), patch.object(asyncio,'create_subprocess_exec',side_effect=refused):
            with self.assertRaises(FileNotFoundError):
                asyncio.run(reviews.Native().call(self.runtime,attempt,policy,context,
                    self.directory/'affirmative-local-refusal','fictional factual input',[],opening=True))
        self.assertEqual(launch[0][launch[0].index('--cwd')+1],'/tmp')
        self.assertEqual(self.runtime.one('SELECT state FROM review_calls')['state'],'prepared')
        self.assertIsNone(self.runtime.attempt(attempt)['begin'])
        self.runtime.collect(attempt,{'exit':None,'capture':'not-started','cleanup':'no-session-created',
            'result':None,'error':'fictional affirmative process-creation refusal',
            'detail':{'known_not_started':True}})
        result=service_recovery.recover_review(self.runtime,'fictional-issuer','fictional-component',self.disposition())
        self.assertTrue(result['successor_admissible'])
        self.assertEqual(result['remaining_holds'],[])
        self.assertIsNone(self.runtime.attempt(attempt)['exit'])
        self.assertIsNone(self.runtime.attempt(attempt)['session'])


class Startup(Engineering):
    def test_report_only_prompt_and_execution_cwd_preserve_source_work_context(self):
        self.event('fictional-report','Work','wp')
        job=self.runtime.reserve(); attempt=self.runtime.start_job(job['id'],job['token'])
        job=self.runtime.job(job['id'])
        template=self.directory/'explicit-report-method'; template.write_text('Read only this explicit fictional report.')
        task={**self.runtime.config['tasks']['wp'],'templates':[str(template)],'purpose':'fictional report interpretation',
              'authority':'fictional explicit reports only','effects':'none','cwd':'/fictional/project',
              'effect_authority':{'operations':['read-reports','consolidate-reports'],'read_roots':[str(template)],'write_roots':[]}}
        directory=self.runtime.home/'artifacts'/attempt
        directory.mkdir(parents=True)
        spec=execution_spec(task,directory)
        self.assertEqual(spec['cwd'],'/tmp'); self.assertEqual(spec['effect_authority']['write_roots'],[])
        prompt=job_prompt(self.runtime,job,task)
        self.assertIn('REPORT-ONLY:',prompt); self.assertNotIn('Read applicable AGENTS',prompt)
        self.assertIn('Do not read project AGENTS, WORK_LOG',prompt)
        owned={**task,'effects':'owned-artifacts'}
        self.assertEqual(execution_spec(owned,directory)['effect_authority']['write_roots'],[str(directory)])
        source={**task,'effect_authority':{**task['effect_authority'],'operations':['read-source']}}
        self.assertFalse(report_only(source)); self.assertEqual(execution_spec(source,directory)['cwd'],'/fictional/project')
        self.assertIn('Read applicable AGENTS',job_prompt(self.runtime,job,source))

    def test_report_only_thread_request_uses_neutral_cwd_and_disables_project_docs(self):
        task={'effects':'none','cwd':'/fictional/project','sandbox':'read-only',
              'effect_authority':{'operations':['read-reports'],'read_roots':['/fictional/explicit-report'],'write_roots':[]}}
        spec=execution_spec(task,Path('/fixtures/fictional-output'))
        request=thread_request(spec,{'model':'gpt-6.1-sol','effort':'high','provider':'openai'})
        self.assertEqual(request['cwd'],'/tmp')
        self.assertEqual(request['config']['project_doc_max_bytes'],0)
        self.assertIn('Do not read project AGENTS, WORK_LOG',request['developerInstructions'])
        source={**spec,'effect_authority':{'operations':['read-source']}}
        self.assertNotIn('project_doc_max_bytes',thread_request(source,{'model':'gpt-6.1-sol','effort':'high','provider':'openai'})['config'])
        # Pure request construction; no native profile/session/turn response.



class Isolation(unittest.TestCase):
    def test_kernel_read_only_source_and_positive_isolated_write(self):
        source=Path('/src/tools/coordinator-runtime/coordinator_runtime/shared_custody.py')
        self.assertTrue(os.statvfs(source).f_flag & os.ST_RDONLY)
        with self.assertRaises(OSError) as failed: source.open('ab')
        self.assertEqual(failed.exception.errno,errno.EROFS)
        target=Path('/fixtures/positive-isolated-write')
        target.write_text('fictional isolated output'); self.assertEqual(target.read_text(),'fictional isolated output')


for cls,parent in [(PublicCustody,Shared),(Recovery,Engineering),(Startup,Engineering)]:
    for name in dir(parent):
        if name.startswith('test_') and name not in cls.__dict__: setattr(cls,name,None)
del cls,parent,name,Shared,Engineering
