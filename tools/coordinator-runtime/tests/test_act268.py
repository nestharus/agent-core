"""Explicitly fictional engineering controls; no native/provider identities.

NULL native/account fields and named fixture projections do not qualify any
actual session, custodian consent, elapsed retention or rollout.
"""
import asyncio
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import subprocess
import unittest
from unittest.mock import patch

from test_processing188 import EngineTests
from test_completion239 import Completion,Material
from coordinator_runtime import branches,reviews,service,service_recovery,processing,retirement,shared_custody,capacity
from coordinator_runtime.contracts import Refusal,digest,encode
from coordinator_runtime.frontier import delivery,require_aged


class Engineering(EngineTests):
    _scope_setup=Completion.test_O1_scoped_independent_integrator_and_real_overlap
    _complete=Completion.completed
    _retirement_receipt=Completion.receipt
    def continuing(self):
        selected=json.loads(self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.key,))['selection'])
        selected.pop('expires',None); selected.pop('max_starts',None)
        selected['service']={'max_inflight':20,'reviews':{},'legacy_resources':{}}
        selected['basis']['configuration']=digest(self.runtime.config)
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',(encode(selected),self.key))
        return selected

    def test_shared_response_links_survive_reopen_and_later_descendant_hold(self):
        self.continuing(); self.event('fictional-consumer','Work','wp')
        for key in ('fictional-outbox-a','fictional-outbox-b'):
            self.runtime.db.execute('INSERT INTO processing_delivery_links VALUES(?,?)',(key,'fictional-consumer'))
        self.runtime.db.execute("UPDATE events SET processed_at=1000,state='processed'")
        self.runtime.db.execute("UPDATE queue SET state='done'")
        self.runtime.clock=lambda:90000.
        self.assertTrue(require_aged(self.runtime,'fictional-outbox-b',86400)['complete'])
        child={'id':'fictional-late-child','role':'Work','recipient':'fictional-logical-Work','kind':'response','body':'fictional pending','parent':'fictional-consumer','package':None,'allowed_tasks':['wp']}
        self.runtime.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',(child['id'],'Work',encode(child),digest(child),90000.,child['parent']))
        for key in ('fictional-outbox-a','fictional-outbox-b'):
            self.assertFalse(delivery(self.runtime,key)['complete'])
        self.runtime.db.execute('UPDATE events SET processed_at=90000,state=\'processed\' WHERE id=?',(child['id'],))
        for key in ('fictional-outbox-a','fictional-outbox-b'):
            with self.assertRaises(Refusal): require_aged(self.runtime,key,86400)
        self.runtime.clock=lambda:180000.
        self.assertTrue(require_aged(self.runtime,'fictional-outbox-b',86400)['complete'])
        self.runtime.set_hold(child['id'],'fictional later recovery hold')
        self.assertFalse(delivery(self.runtime,'fictional-outbox-a')['complete'])

    def test_old_unique_consumer_schema_migrates_without_losing_links(self):
        self.event('fictional-consumer','Work','wp')
        self.runtime.db.execute('DROP TABLE processing_delivery_links')
        self.runtime.db.execute('CREATE TABLE processing_delivery_links(delivery TEXT PRIMARY KEY,event TEXT NOT NULL UNIQUE REFERENCES events(id))')
        self.runtime.db.execute("INSERT INTO processing_delivery_links VALUES('fictional-a','fictional-consumer')")
        processing.migrate_links(self.runtime)
        self.runtime.db.execute("INSERT INTO processing_delivery_links VALUES('fictional-b','fictional-consumer')")
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM processing_delivery_links')['n'],2)

    def test_current_effectful_job_does_not_become_its_own_legacy_debt(self):
        # Reuse actual admitted-root setup, then cross the previously missing
        # reservation -> current effectful reconciliation boundary.
        self._scope_setup()
        from coordinator_runtime.resource_scopes import blocked
        job=self.runtime.one("SELECT * FROM jobs WHERE package='fictional-independent'")
        self.assertFalse(blocked(self.runtime,job))
        self.runtime.db.execute("UPDATE jobs SET effects='reconciled' WHERE id=?",(job['id'],))
        self.assertFalse(blocked(self.runtime,self.runtime.job(job['id'])))
        self.assertEqual(self.runtime.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'],'fictional old debt')

    def test_foreign_classifiers_do_not_consume_current_service_admission(self):
        self.continuing(); self.event('fictional-fresh','Work','wp',queued=False)
        for n in range(5):
            self.runtime.db.execute('INSERT INTO attempts(id,kind,event,controller,binding,state,created) VALUES(?,?,?,?,?,?,?)',('fictional-old-'+str(n),'classifier','fictional-fresh','fictional-old-original',encode(processing.SOL),'unknown',1000))
        spawned=[]
        dispatcher=service.Dispatcher(self.runtime,{})
        dispatcher.spawn=lambda task: (spawned.append(True),task.close())
        dispatcher.schedule_classifications()
        self.assertEqual(len(spawned),1)
        self.assertEqual(self.runtime.one("SELECT COUNT(*) AS n FROM attempts WHERE controller='fictional-old-original' AND collected IS NULL")['n'],5)

    def test_busy_review_reservation_does_not_hide_independent_work(self):
        selected=self.continuing()
        self.runtime.config['tasks']['source']={**self.runtime.config['tasks']['wp'],'role':'Reviews'}
        selected=self.continuing(); selected['tasks'].append('source'); selected['service']['reviews']={'source':{}}
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',(encode(selected),self.key))
        self.event('fictional-source','Reviews','source')
        event=self.runtime.event('fictional-source'); event['body']={'review':{'component':'fictional-component'}}
        self.runtime.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',(encode(event),digest(event),'fictional-source'))
        reserved=self.runtime.reserve(); self.assertEqual(reserved['task'],'source')
        self.event('fictional-independent','Work','wp')
        class Board:
            def verify_authority(self,store): return None
        dispatcher=service.Dispatcher(self.runtime,{'Reviews':Board(),'Work':Board()})
        dispatcher.reviews.busy.add('fictional-component')
        spawned=[]
        dispatcher.spawn=lambda task:(spawned.append(True),task.close())
        dispatcher.schedule_job()
        self.assertEqual(len(spawned),1)
        self.assertIsNone(self.runtime.job(reserved['id'])['active_attempt'])
        self.assertIsNotNone(self.runtime.one("SELECT active_attempt FROM jobs WHERE task='wp'")['active_attempt'])

    def test_material_and_authority_refusal_records_affirmative_no_start(self):
        self.continuing(); self.event('fictional-source','Work','wp')
        job=self.runtime.reserve(); attempt=self.runtime.start_job(job['id'],job['token'])
        class Board:
            def bind_software_attempt(self,*args): raise Refusal('fictional affirmative authority refusal before caller creation')
        dispatcher=service.Dispatcher(self.runtime,{'Work':Board()})
        asyncio.run(dispatcher.execute_review(job,attempt,{}))
        actual=self.runtime.attempt(attempt)
        self.assertEqual(actual['state'],'not-started'); self.assertIsNone(actual['exit'])
        self.assertIsNotNone(actual['collected']); self.assertIsNone(actual['session'])
        self.assertIsNone(actual['profile'])
        self.assertIn('affirmative',json.loads(self.runtime.one('SELECT payload FROM events WHERE source_job IS NULL') or '{}') if False else actual['error'])
        returned=[self.runtime.event(e['id']) for e in self.runtime.rows("SELECT id FROM events WHERE id!='fictional-source'")]
        self.assertEqual(returned[0]['body']['status'],'PARTIAL')

    def test_lost_original_informed_recovery_retains_unknowns_and_allows_new_original(self):
        self.continuing(); self.event('fictional-old','Work','wp',queued=False)
        with self.runtime.tx(): attempt=self.runtime._attempt('input-control','fictional-old',None,processing.SOL,None)
        self.runtime.db.execute("INSERT INTO processing_runs VALUES(?,?,'owned',1000)",(self.runtime.controller,self.key))
        # A source upgrade selects new current authority; the revoked original
        # capability remains intact and must not become an unrepairable global
        # process barrier. This is a local software-capability projection only.
        prior=self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.key,))
        self.runtime.db.execute('UPDATE processing_capabilities SET revoked=1001 WHERE id=?',(self.key,))
        self.runtime.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)',('fictional-upgrade-cap',prior['selection'],'fictional-issuer',1002.))
        self.runtime.processing=processing.Access(self.runtime,'fictional-upgrade-cap')
        observed=service_recovery.basis(self.runtime,self.runtime.controller)
        receipt={'basis':observed['basis'],'activity':'unavailable','actual_END':None,'evidence':'fictional original lost; no END asserted','remaining_holds':['fictional possible original activity/effects'],'custodians':{attempt:'fictional-original-custodian'}}
        result=service_recovery.apply(self.runtime,'fictional-issuer',self.runtime.controller,receipt)
        self.assertFalse(result['same_session_continuity'])
        self.assertIsNone(self.runtime.attempt(attempt)['collected'])
        self.assertIsNone(self.runtime.attempt(attempt)['exit'])
        self.assertIsNone(self.runtime.one("SELECT controller FROM processing_runs WHERE state='owned'"))
        self.runtime.controller='fictional-successor-collector'
        self.event('fictional-independent-new','Work','wp',queued=False)
        fresh=self.runtime.claim_classification()
        self.assertIsNotNone(fresh)
        self.assertEqual(self.runtime.attempt(fresh[0])['controller'],'fictional-successor-collector')
        self.assertIsNone(self.runtime.attempt(attempt)['collected'])

    def test_unknown_activity_cannot_be_relabelled_a_review_successor(self):
        self.continuing()
        self.runtime.db.execute('DROP TABLE review_contexts')
        self.runtime.db.executescript(reviews.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT'))
        self.runtime.db.execute('INSERT INTO review_contexts VALUES(?,?,NULL,?,?,NULL,?,?,?,?,?,NULL)',('fictional-component',self.key,'fictional-unused-route','/fixtures/unopened-handle','fictional-lost-original','interrupted',None,reviews.sha(b''),1000))
        current=service_recovery.review_basis(self.runtime,'fictional-component')
        receipt={'basis':current['basis'],'activity':'unknown','evidence':'fictional uncertain inactivity','custodian':'fictional-original-owner','remaining_holds':['fictional unavailable original'],'history_hash':reviews.sha(b'')}
        result=service_recovery.recover_review(self.runtime,'fictional-issuer','fictional-component',receipt)
        self.assertFalse(result['successor_admissible'])
        self.assertIsNotNone(self.runtime.one('SELECT component FROM review_contexts'))
        current=service_recovery.review_basis(self.runtime,'fictional-component')
        receipt.update(basis=current['basis'],activity='inactive',evidence='fictional owner-supported inactivity; not a native encounter')
        result=service_recovery.recover_review(self.runtime,'fictional-issuer','fictional-component',receipt)
        self.assertTrue(result['successor_admissible']); self.assertFalse(result['same_session_continuity'])
        self.assertIsNone(self.runtime.one('SELECT component FROM review_contexts'))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM review_predecessors')['n'],2)

    def test_interrupted_history_append_reconciles_exact_bytes_without_caller_replay(self):
        self.continuing()
        history=self.runtime.home/'review-history'/'fictional'; history.parent.mkdir(); history.write_bytes(b'original\n')
        entry='{"fictional":"full partial return"}\n'
        with patch.object(reviews,'apply_history',side_effect=OSError('fictional interruption after durable intent')):
            with self.assertRaises(OSError): reviews.commit_history(self.runtime,'fictional-attempt','fictional-component',history,b'original\n',entry,'a'*40)
        first=reviews.apply_history(self.runtime,'fictional-attempt'); second=reviews.apply_history(self.runtime,'fictional-attempt')
        self.assertEqual(first,second); self.assertEqual(history.read_bytes(),b'original\n'+entry.encode())
        history.write_bytes(b'unknown mixed history')
        with self.assertRaises(Refusal): reviews.apply_history(self.runtime,'fictional-attempt')
        self.assertIsNone(self.runtime.one('SELECT * FROM attempts'))

    def test_git_handback_capture_limit_conserves_actual_local_exit(self):
        from coordinator_runtime.coding import Git
        repository=self.directory/'local-git'; repository.mkdir()
        subprocess.run(['/usr/bin/git','-C',str(repository),'init','-q'],check=True)
        git=Git(str(repository),self.directory/'bounded-git')
        code,body=git.run('-c','alias.flood=!python3 -c "print(chr(120)*200000)"','flood')
        self.assertEqual(len(body),131072)
        self.assertEqual(git.records[0]['capture'],'incomplete')
        self.assertEqual(git.records[0]['actual_END'],code)
        # This exact owned local OS process is not a native/provider encounter.
        self.assertIsInstance(code,int)

    def test_review_coverage_requires_architecture_core_limits_and_actual_answered_ids(self):
        account={'families':{f:'partial' for f in reviews.FAMILIES},'core_files_not_read':['fictional-core.py'],'observations':[{'id':'fictional-O1','location':'fictional-core.py:1'}],'answered_ids':['fictional-prior-O1'],'limits':['fictional bounded source']}
        returned={'coverage':account}; packet={'answered_ids':['fictional-prior-O1']}
        reviews.coverage(returned,packet,False)
        account['families']['organization-and-communication']='full'
        with self.assertRaises(Refusal): reviews.coverage(returned,packet,False)
        account['families']['organization-and-communication']='partial'; account['answered_ids']=[]
        with self.assertRaises(Refusal): reviews.coverage(returned,packet,False)


class Branches(Material):
    def test_branch_root_remains_responsible_and_components_histories_are_separate(self):
        policy,packet=self.setup_repository(); self.runtime.processing=None
        self.runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)',('fictional-scope','fictional-owner','{}'))
        class Capability:
            def current(inner): return {'issuer':'fictional-Work'},{}
        self.runtime.processing=Capability()
        repository=policy['components']['fictional-component']['repository']
        reviews.git(repository,'remote','add','origin',packet['origin'])
        for name in ('fictional-a','fictional-b','fictional-renamed'): reviews.git(repository,'branch',name)
        def register(key,ref):
            return branches.register(self.runtime,'fictional-Work',{'id':key,'repository':repository,'origin':packet['origin'],'ref':ref,'incarnation':key,'scope':'fictional-scope','root':'fictional-responsible-Root','authority':'fictional Work branch authority'})
        # Explicit logical-actor projection; no actual native UUID is fabricated.
        with patch.object(branches,'canonical_uuid',side_effect=lambda value:value):
            register('fictional-branch-A','refs/heads/fictional-a'); register('fictional-branch-B','refs/heads/fictional-b')
            for key in ('fictional-branch-A','fictional-branch-B'):
                branches.accept(self.runtime,key,'fictional-responsible-Root','fictional actual-owner acceptance seam')
        def job(key):
            body={'id':key,'branch_binding':key,'package':'fictional-scope'}
            self.runtime.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',(key,'Work',encode(body),digest(body),1000))
            return {'members':encode([{'event':key}])}
        a,b=job('fictional-branch-A'),job('fictional-branch-B')
        self.assertNotEqual(branches.review_key(self.runtime,a,packet),branches.review_key(self.runtime,b,packet))
        self.assertNotEqual(branches.review_policy(self.runtime,a,policy,packet)['components']['fictional-component']['history'],branches.review_policy(self.runtime,b,policy,packet)['components']['fictional-component']['history'])
        self.assertEqual(branches.route(self.runtime,'fictional-branch-A')['branch']['root'],'fictional-responsible-Root')
        self.assertEqual(set(packet),{'component','origin','base','head','previous','answered_ids'})
        with patch.object(branches,'canonical_uuid',side_effect=lambda value:value):
            branches.lifecycle(self.runtime,'fictional-branch-A','fictional-responsible-Root',{'state':'active','ref':'refs/heads/fictional-renamed','root':'fictional-responsible-Root','evidence':'fictional explicit rename keeping reviewed pins'})
        history=json.loads(branches.route(self.runtime,'fictional-branch-A')['branch']['history'])
        self.assertEqual(history[-1]['prior_ref'],'refs/heads/fictional-a')
        self.runtime.db.execute("INSERT INTO branch_turns VALUES('fictional-turn','fictional-branch-A','builder','','fictional-local-context','fictional-responsible-Root',NULL,'fictional-writer','{}','unknown',1000,NULL,NULL)")
        with self.assertRaises(Refusal): branches.lifecycle(self.runtime,'fictional-branch-A','fictional-responsible-Root',{'state':'closed','ref':'refs/heads/fictional-renamed','root':'fictional-responsible-Root','evidence':'fictional attempted close with unknown writer'})
        # Explicit local context/NULL-account projection. This exercises the
        # real branch writer fence, not a fabricated native session.
        self.runtime.db.execute("UPDATE branch_turns SET state='returned' WHERE id='fictional-turn'")
        self.runtime.db.execute('INSERT INTO branch_contexts VALUES(?,?,?,?,?,NULL,?,?,?,NULL)',('fictional-branch-A','builder','','fictional-local-owned-context','fixture-local-only','fictional-responsible-Root','available','fictional observed local context seam'))
        self.runtime.execution_pool.status=lambda:{'enabled':[None]}
        reviews.git(repository,'checkout','fictional-renamed')
        material=reviews.git(repository,'show','-s','--format=%H%n%T%n%P','HEAD').decode().splitlines()
        turn={'id':'fictional-owned-turn','kind':'builder','component':'','address':'fictional-local-owned-context','profile':None,'material':{'head':material[0],'tree':material[1],'parents':material[2].split()},'writer':repository}
        branches.begin(self.runtime,'fictional-branch-A','fictional-responsible-Root',turn)
        with self.assertRaises(Refusal): branches.begin(self.runtime,'fictional-branch-A','fictional-responsible-Root',{**turn,'id':'fictional-overlap'})
        self.runtime.execution_pool.status=lambda:{'enabled':[]}
        local_end=subprocess.run(['/usr/bin/python3','-c','pass'],check=True).returncode
        with self.assertRaises(Refusal): branches.end(self.runtime,'fictional-branch-A','fictional-responsible-Root','fictional-owned-turn',{'activity':'returned','actual_END':local_end,'effects':'reconciled','evidence':'actual isolated local OS END with fictional branch context projection; no signed handback'})
        # Explicit fixture-only state transition isolates future-pool refusal;
        # the production API above correctly retained the unpublished writer.
        self.runtime.db.execute("UPDATE branch_turns SET state='returned' WHERE id='fictional-owned-turn'")
        with self.assertRaises(Refusal): branches.begin(self.runtime,'fictional-branch-A','fictional-responsible-Root',{**turn,'id':'fictional-excluded-next'})
        wire={'review':packet,'branch_binding':'fictional-branch-A'}
        factual=branches.board_review(self.runtime,{'author':'fictional-responsible-Root','text':encode(wire)})
        self.assertEqual(factual['packet'],packet)
        with self.assertRaises(Refusal): branches.board_review(self.runtime,{'author':'fictional-other','text':encode(wire)})
        with self.assertRaises(Refusal): branches.board_review(self.runtime,{'author':'fictional-responsible-Root','text':encode({**wire,'goal':'not admitted into Source'})})
        self.runtime.processing=None

    def test_future_review_turn_refuses_disabled_account_without_moving_context(self):
        policy,packet=self.setup_repository()
        # Admission refusal occurs before any native process. The real protocol
        # transport is retained, but no account or native address is invented.
        class Pool:
            from contextlib import asynccontextmanager
            @asynccontextmanager
            async def admission(inner,profile):
                raise Refusal('fictional current user pool excludes context account')
                yield
        self.runtime.execution_pool=Pool(); self.runtime.authorize_launch=lambda attempt:None
        self.runtime.db.execute('DROP TABLE review_contexts'); self.runtime.db.executescript(reviews.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT'))
        self.runtime.processing=None
        policy.update(caller='/fixtures/never-created-local-program',deadline=1)
        context={'component':'fictional-component','profile':None,'route':None,'handle':'/fixtures/unused-handle'}
        with self.assertRaises(Refusal): asyncio.run(reviews.Native().call(self.runtime,'fictional-no-start',policy,context,self.directory/'refused-call','factual input',[],opening=False))
        self.assertIsNone(context['profile']); self.assertEqual(context['handle'],'/fixtures/unused-handle')
        self.assertIsNone(self.runtime.one('SELECT * FROM review_contexts'))


# Avoid inherited tests obscuring the actual selected engineering controls.
for cls,parent in ((Engineering,EngineTests),(Branches,Material)):
    for name in dir(parent):
        if name.startswith('test_') and name not in cls.__dict__: setattr(cls,name,None)
del cls,parent,name,EngineTests,Material

if __name__=='__main__': unittest.main(verbosity=2)

class Shared(Engineering):
    def board(self):
        library=Path('/src/tools/message-board/board_store.py')
        spec=importlib.util.spec_from_file_location('fictional_public_board_store',library)
        public=importlib.util.module_from_spec(spec); spec.loader.exec_module(public)
        class Shell:
            @contextmanager
            def write(inner,conn):
                conn.execute('BEGIN IMMEDIATE')
                try: yield; conn.commit()
                except BaseException: conn.rollback(); raise
            def acting_session(inner,expected):
                if expected not in {'fictional-issuer','fictional-recipient'}: raise Refusal('fictional actor ownership refusal')
                return expected
            def retire_coordinator_pointer(inner,conn,key,actor,proof):
                with patch.object(public,'acting_session',inner.acting_session):
                    return public.retire_coordinator_pointer(conn,key,actor,proof)
        class Board(shared_custody.SharedCustody):
            def __init__(inner):
                inner.selected={'owner':'fictional-logical-Work'}; inner.store=Shell()
                inner.conn=sqlite3.connect(self.directory/'fictional-shared.sqlite3',isolation_level=None)
                inner.conn.row_factory=sqlite3.Row
                inner.conn.executescript('''
                  PRAGMA foreign_keys=ON;
                  CREATE TABLE coordinator_grants_v1(id PRIMARY KEY,runtime,runtime_dev,runtime_ino,actor,owner,issued_by);
                  CREATE TABLE coordinator_deliveries_v1(id PRIMARY KEY,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,processed_at);
                  CREATE TABLE posts(seq INTEGER PRIMARY KEY AUTOINCREMENT,author,recipient,topic,kind,text,ref,reply_to REFERENCES posts(seq),created_at);
                  CREATE TRIGGER posts_no_delete BEFORE DELETE ON posts BEGIN SELECT RAISE(ABORT,'board posts are immutable'); END;
                  CREATE TABLE threads(thread_id PRIMARY KEY REFERENCES posts(seq),title);
                  CREATE TABLE thread_posts(post_seq PRIMARY KEY REFERENCES posts(seq),thread_id REFERENCES threads(thread_id));
                  CREATE TABLE subscriptions(thread_id REFERENCES threads(thread_id),session);
                  CREATE TABLE attachments(post_seq REFERENCES posts(seq),path);
                  CREATE TABLE notification_outbox(notification_id INTEGER PRIMARY KEY AUTOINCREMENT,post_seq REFERENCES posts(seq),thread_id REFERENCES threads(thread_id),delivery_state);
                  CREATE TABLE notification_attempts(notification_id REFERENCES notification_outbox(notification_id),attempt_number);
                  CREATE TABLE coordinator_software_deliveries_v1(delivery PRIMARY KEY,payload);
                  CREATE TABLE coordinator_owner_return_checks_v1(delivery,receipt);
                  CREATE TABLE coordinator_owner_corrections_v1(delivery,receipt);
                '''+shared_custody.SCHEMA)
                info=self.runtime.path.stat()
                inner.conn.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?)',('fictional-original-grant',str(self.runtime.path),info.st_dev,info.st_ino,self.runtime.config['actor'],'fictional-logical-Work','fictional-issuer'))
            @contextmanager
            def opened(inner,**kwargs): yield inner.conn
            def _delivery_record(inner,conn,row):
                return {'control_receipt':{'pending':False},'meaning':'explicit local control-proof projection, not native consent'}
        return Board()

    def create(self,board,n):
        root='fictional-episode-'+str(n)
        self.runtime.clock=lambda:90000.+n*200000.
        self._complete(root)
        self.runtime.clock=lambda:90000.+n*200000.
        with self.runtime.tx():
            key=self.runtime._outbox('Work','Work','alert',{'fictional':'whole result '+str(n)},event=root)
        self.runtime.db.execute("UPDATE outboxes SET state='settled',processed_at=1000 WHERE id=?",(key,))
        outbox=self.runtime.one('SELECT * FROM outboxes WHERE id=?',(key,)); conn=board.conn
        post=conn.execute('INSERT INTO posts(author,recipient,topic,kind,text,ref,created_at) VALUES(?,?,?,?,?,?,?)',(self.runtime.config['actor'],'fictional-recipient','coordinator-runtime','handoff','fictional owned pointer','delivery:'+key,'fictional time')).lastrowid
        conn.execute('INSERT INTO threads VALUES(?,?)',(post,'fictional'))
        conn.execute('INSERT INTO thread_posts VALUES(?,?)',(post,post))
        notice=conn.execute("INSERT INTO notification_outbox(post_seq,thread_id,delivery_state) VALUES(?,?,'acknowledged')",(post,post)).lastrowid
        conn.execute('INSERT INTO coordinator_deliveries_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,'fictional-original-grant','fictional-logical-Work',self.runtime.config['actor'],outbox['producer'],'fictional-recipient','alert','settled',outbox['payload'],post,notice,'settled',1000))
        conn.execute('INSERT INTO coordinator_software_deliveries_v1 VALUES(?,?)',(key,'fictional whole receiving intent'))
        return root,key,post

    def custody_receipt(self,board,key):
        current=board.shared_custody_basis(self.runtime,key)
        consent={'basis':current['basis'],'qualified_at':self.runtime.clock(),'holds':{h:[] for h in capacity.HOLDS},'evidence':'fictional actual-recipient closed consumption projection','reply_route_closed':True,'conservation':'fictional all required sources/results retained in original homes'}
        board.shared_custody_consent(self.runtime,key,consent)
        return {'basis':current['basis'],'qualified_at':self.runtime.clock(),'holds':{h:[] for h in capacity.HOLDS},'evidence':'fictional issuer all-custodian projection; not real consent/24h','custodian':'fictional-archive-custodian','archive':str(self.runtime.home/'shared-custody'/key),'archive_budget_bytes':1048576,'archive_existing_bytes':0,'conservation':'fictional original full returns/source/history conserved'}

    def test_repeated_local_and_shared_retirement_conserves_payloads_frontier_and_budget(self):
        self.runtime.config['software_delegation']={'grantor':'fictional-issuer'}
        self.runtime.config['delivery']['recipients']['Work']={'session':'fictional-recipient'}
        self.continuing(); board=self.board()
        previous=0
        for n in range(4):
            root,key,post=self.create(board,n)
            # Local rows must not disappear first, even with all-hold assertions.
            self.runtime.db.execute('UPDATE outboxes SET board_receipt=? WHERE id=?',(encode({'fictional':'shared custody exists'}),key))
            observed=retirement.basis(self.runtime,root)
            with self.assertRaises(Refusal): retirement.apply(self.runtime,root,'fictional-issuer',self._retirement_receipt(observed))
            receipt=self.custody_receipt(board,key)
            result=board.retire_shared_custody(self.runtime,key,receipt)
            self.assertGreater(post,previous); previous=post
            witness=json.loads(Path(result['canonical_archive']).read_text())
            self.assertEqual(witness['original']['material']['delivery']['payload'],encode({'fictional':'whole result '+str(n)}))
            self.assertIsNone(board.conn.execute('SELECT id FROM coordinator_deliveries_v1').fetchone())
            self.assertIsNone(board.conn.execute('SELECT delivery FROM coordinator_software_deliveries_v1').fetchone())
            self.assertEqual(board.conn.execute('SELECT COUNT(*) FROM coordinator_scan_frontiers_v1').fetchone()[0],1)
            self.runtime.clock=lambda:180000.+n*200000.
            release={'hash':digest(witness),'qualified_at':self.runtime.clock(),'holds':{h:[] for h in capacity.HOLDS},'evidence':'fictional actual custody release after original conservation','originals':{name:{'hash':digest(value),'custodian':'fictional-original-custodian','evidence':'fictional full original preserved at its actual source'} for name,value in witness['original']['material'].items()},'custodian':'fictional-archive-custodian'}
            full=board.release_shared_archive(self.runtime,key,release)
            self.assertEqual(full['original_witness'],witness)
            observed=retirement.basis(self.runtime,root)
            retirement.apply(self.runtime,root,'fictional-issuer',self._retirement_receipt(observed))
            self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'],0)
            self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM outboxes')['n'],0)
        self.assertEqual(board.conn.execute('SELECT count FROM coordinator_scan_frontiers_v1').fetchone()[0],4)
        self.assertEqual(list((self.runtime.home/'shared-custody').iterdir()),[])
        # Ordinary posts remain protected after the narrow public interface.
        foreign=board.conn.execute("INSERT INTO posts(author,recipient,topic,text,ref) VALUES('fictional-foreign','fictional-recipient','other','keep me','unrelated')").lastrowid
        with self.assertRaises(sqlite3.IntegrityError): board.conn.execute('DELETE FROM posts WHERE seq=?',(foreign,))
        board.conn.close()

    def test_shared_retirement_refuses_foreign_reply_and_current_changed_hold(self):
        self.runtime.config['software_delegation']={'grantor':'fictional-issuer'}
        self.runtime.config['delivery']['recipients']['Work']={'session':'fictional-recipient'}
        self.continuing(); board=self.board(); root,key,post=self.create(board,0)
        receipt=self.custody_receipt(board,key)
        reply=board.conn.execute('INSERT INTO posts(author,recipient,topic,text,reply_to) VALUES(?,?,?,?,?)',('fictional-foreign','fictional-recipient','coordinator-runtime','foreign required body',post)).lastrowid
        with self.assertRaises(Refusal): board.retire_shared_custody(self.runtime,key,receipt)
        self.assertIsNotNone(board.conn.execute('SELECT id FROM coordinator_deliveries_v1 WHERE id=?',(key,)).fetchone())
        self.assertEqual(board.conn.execute('SELECT text FROM posts WHERE seq=?',(reply,)).fetchone()[0],'foreign required body')
        board.conn.close()

for name in dir(Engineering):
    if name.startswith('test_') and name not in Shared.__dict__: setattr(Shared,name,None)
del name,Completion
