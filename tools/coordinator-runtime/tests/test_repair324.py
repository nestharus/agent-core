"""Work's R320 outcomes on owned fiction; native/profile/session/turn stay NULL.

Public source is RO in bwrap. SQLite, disposable Git, file chunks and local
Python subprocesses are real. Caller identity and adapter-result construction
are explicit validation seams, never a successful native encounter.
"""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from coordinator_runtime import cli, custody, review_reader as reader, reviews
from coordinator_runtime.contracts import Refusal, digest, encode
from test_bounded311 import Base
from test_completion239 import Material


class Export(Base):
    def setUp(self):
        super().setUp()
        self.body = b'FICTION conditional retained artifact\x00\xff'
        self.sha = hashlib.sha256(self.body).hexdigest()
        self.path = str(self.area/'report.bin')
        self.store.db.execute('INSERT INTO artifact_blobs VALUES(?,?)', (self.sha, self.body))
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                              ('fiction-original', self.path, 'role-owned', 'fiction-owner',
                               encode({'sha256':self.sha, 'size':len(self.body)}), self.sha))
        self.args = SimpleNamespace(command='artifact-source', attempt='fiction-original', path=self.path, delivery='fiction-delivery')
        self.store.config['delivery']['recipients']['Work']['session'] = 'fiction-consumer'
        self.store._outbox('Work', 'Work', 'result', {'artifact_witnesses': [
            {'source_attempt':self.args.attempt, 'path':self.path, 'sha256':self.sha}]}, key=self.args.delivery)
        self.store.db.execute("UPDATE outboxes SET board_receipt='fiction-addressed-witness'")

    def export(self, caller):
        # Deliberately bypass native identity parsing; never set session env.
        with patch.object(cli, 'canonical_uuid', return_value=caller):
            return cli.operate(self.args, self.store)

    def denied_before_body(self):
        for caller in ('fiction-owner', 'fiction-consumer'):
            reads=[]
            def authorize(action, table, column, *unused):
                if action == sqlite3.SQLITE_READ and table == 'artifact_blobs' and column == 'body':
                    reads.append((table,column)); return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            self.store.db.set_authorizer(authorize)
            try:
                with self.assertRaises(Refusal): self.export(caller)
            finally:
                self.store.db.set_authorizer(None)
            self.assertEqual(reads, [], 'current guard must precede SQL body acquisition')
        self.assertEqual(self.store.one('SELECT body FROM artifact_blobs')['body'], self.body)

    def test_direct_exclusion_blocks_entitled_owner_and_consumer(self):
        self.store.config['artifact_exclusions'] = [self.path]
        self.denied_before_body()

    def test_known_origin_and_preimage_survive_renamed_export_path(self):
        origin=str(self.area/'opaque-held')
        self.store.config['artifact_exclusions']=[origin]
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                              ('fiction-prior',origin,'role-owned','fiction-owner',
                               encode({'sha256':self.sha, 'size':len(self.body)}),self.sha))
        self.denied_before_body()
        self.store.db.execute("DELETE FROM artifact_custody WHERE attempt='fiction-prior'")
        self.store.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
            ('fiction-old-run','wi','fiction-grant',encode({'kind':'file-witness'}),
             encode({origin:{'exists':True,'sha256':self.sha}}),'prepared'))
        self.denied_before_body()

    def test_standard_custom_and_historical_stage_logs_refuse_before_body(self):
        self.store.config['tasks']['wi']['routine_completion']={'bounded_log':{'target':self.path}}
        self.denied_before_body()
        del self.store.config['tasks']['wi']['routine_completion']
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                              ('fiction-log',str(self.area/'WORK_LOG.md'),'role-owned','fiction-owner','{}',self.sha))
        self.denied_before_body()
        self.store.db.execute("DELETE FROM artifact_custody WHERE attempt='fiction-log'")
        self.store.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',
                              ('fiction-legacy',str(self.area/'WORK_LOG.md'),self.path))
        self.denied_before_body()

    def test_nonexcluded_exact_export_ownership_hash_size_missing_and_custody(self):
        before=self.store.rows('SELECT * FROM artifact_custody')
        for caller in ('fiction-owner','fiction-consumer'):
            exported=self.export(caller)
            self.assertEqual(base64.b64decode(exported['body_base64']),self.body)
        with self.assertRaises(Refusal):self.export('fiction-unrelated')
        self.store.config['limits']['max_artifact_bytes']=1
        with self.assertRaisesRegex(Refusal,'export bound'):self.export('fiction-owner')
        self.store.config['limits']['max_artifact_bytes']=1000
        self.store.db.execute('UPDATE artifact_blobs SET body=?',(self.body[:-1]+b'Z',))
        with self.assertRaisesRegex(Refusal,'no longer match'):self.export('fiction-owner')
        self.store.db.execute('DELETE FROM artifact_blobs')
        with self.assertRaisesRegex(Refusal,'custody unavailable'):self.export('fiction-owner')
        self.assertEqual(self.store.rows('SELECT * FROM artifact_custody'),before)


class ReviewsRoute(Base):
    def configure(self):
        self.config['tasks']['rp']=copy.deepcopy(self.config['tasks']['ri'])
        self.config['tasks']['rp'].update(phase='proposer',execution='model',delivery_required=True,
                                       responses={'proposal':['ri']})
        self.config['tasks']['ri'].update(execution='model',delivery_required=True,responses={'consolidated':['wp']})
        self.config['delivery']['recipients'].update({'Reviews':{'session':'fictional-logical-Reviews'}})

    def queue(self, event_id, task, role='Reviews', existing=False):
        s=self.store
        if existing:
            e=s.event(event_id)
        else:
            e={'id':event_id,'role':role,'recipient':'fictional-logical-'+role,'kind':'board','post':1,
               'body':'fictional explicit local routing control','allowed_tasks':[task],'package':None}
            s.ingest(e)
        s.db.execute("UPDATE events SET state='queued',ack='internal' WHERE id=?",(event_id,))
        s.db.execute("INSERT INTO queue VALUES(?,?,?,?,?,NULL,'queued',NULL)",
                     (event_id,event_id,role,s.config['tasks'][task]['phase'],task))
        job=s.reserve(); self.assertEqual(job['task'],task)
        attempt=s.start_job(job['id'],job['token'])
        return s.job(job['id']),attempt

    def run_local(self, attempt, result):
        # Genuine owned Python END/full capture. No native calls/identities.
        child=subprocess.Popen([sys.executable,'-c','import sys;sys.stdout.write(sys.stdin.read())'],
                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.store.begin(attempt,{'validation_seam':'owned local JSON echo, no native report producer'})
        stdout,stderr=child.communicate(encode(result).encode())
        self.assertEqual(stderr,b'')
        self.store.collect(attempt,{'result':json.loads(stdout),'exit':child.returncode,'capture':'complete',
                                    'cleanup':'owned-local-control','error':None,
                                    'detail':{'validation_seam':'proposal adapter output; no native proof'}})
        actual=self.store.attempt(attempt)
        self.assertTrue(all(actual[k] is None for k in ('profile','session','turn')))

    def proposal(self, attempt, semantic='DONE'):
        coverage={'families':{name:'partial' for name in reviews.FAMILIES},'core_files_not_read':['fiction-core'],
                  'observations':[{'id':'fiction-O1','meaning':'keep original dissent'}],
                  'answered_ids':[],'limits':['fictional coverage only']}
        returned={'semantic':semantic,'summary':'fictional local report adapter input','coverage':coverage}
        turns=[{'native_profile':None,'native_session':None,'native_turn':None,'provider_encounter':None,
                'full_answer':{'report':'whole original partial architecture and final report','coverage':coverage}}]
        return reviews.proposal_result(returned,'fiction-component',{'history_sha256':'fiction-retained-pin'},
                                       self.store.controller,attempt,turns)

    def test_delivery_required_proposal_reaches_sole_integrator_and_Work_once(self):
        s=self.store; job,attempt=self.queue('fiction-review','rp')
        answer=self.proposal(attempt); self.run_local(attempt,answer)
        response=s.finish_job(job['id'],job['token'])
        self.assertEqual(s.event(response)['allowed_tasks'],['ri'])
        self.assertEqual(s.event(response)['body'],answer)
        self.assertNotEqual(s.job(job['id'])['state'],'held')
        self.assertFalse(s.rows("SELECT id FROM outboxes WHERE kind='question'"))
        s.finish_job(job['id'],job['token'])
        self.assertEqual(len(s.rows("SELECT id FROM events WHERE parent='fiction-review'")),1)
        integrated,ia=self.queue(response,'ri',existing=True)
        consolidated={**answer,'category':'consolidated','summary':'fiction sole integration conserving whole report',
                      'no_handoff_reason':'Work receives the sole internal consolidated response'}
        self.run_local(ia,consolidated)
        work=s.finish_job(integrated['id'],integrated['token'])
        self.assertEqual(s.event(work)['role'],'Work')
        self.assertEqual(s.event(work)['allowed_tasks'],['wp'])
        self.assertEqual(s.event(work)['body']['findings'],answer['findings'])
        self.assertEqual(s.one("SELECT COUNT(*) AS n FROM jobs WHERE task='rp'")['n'],1)
        self.assertEqual(s.one("SELECT COUNT(*) AS n FROM jobs WHERE task='ri'")['n'],1)
        self.assertEqual(s.event(response)['body'],answer)

    def test_partial_adapter_preserves_unknowns_and_cannot_finish_as_DONE(self):
        job,attempt=self.queue('fiction-partial','rp')
        answer=self.proposal(attempt,'PARTIAL');self.run_local(attempt,answer)
        self.assertTrue(answer['unknowns']);self.assertEqual(answer['findings'][0]['turns'][0]['native_session'],None)
        self.assertIsNone(self.store.finish_job(job['id'],job['token']))
        self.assertEqual(self.store.job(job['id'])['state'],'held')
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']),answer)


class Reader(Material):
    def fixture(self):
        self.directory=Path(tempfile.mkdtemp(dir=self.directory))
        policy,packet=self.setup_repository()
        repository=Path(policy['components']['fictional-component']['repository'])
        # Multiple chunks including split UTF8 and non-UTF8, in real owned Git.
        body=b'\x00'+('x'*11998+'é').encode()*3+b'\xfftail'
        (repository/'module.py').write_bytes(body)
        subprocess.run(['git','-C',str(repository),'add','module.py'],check=True)
        subprocess.run(['git','-C',str(repository),'-c','commit.gpgsign=false','commit','-qm','fiction binary'],check=True)
        packet['head']=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD']).decode().strip()
        history=self.directory/'history.txt';history.write_text('fiction prior history')
        method=self.directory/'method.md';method.write_text('fiction current method')
        policy['method_files']={str(method):reviews.sha(method.read_bytes())}
        prior=self.directory/'prior.txt';prior.write_text('fiction older history')
        policy['components']['fictional-component']['prior_histories']={str(prior):reviews.sha(prior.read_bytes())}
        acquired=reviews.material(policy,packet,None)
        manifest=self.directory/'material.json';manifest.write_text(encode(acquired))
        return manifest,acquired,body,history,method,prior

    def test_each_item_acquired_once_exact_chunks_end_reset_and_no_prior_git_show(self):
        manifest,acquired,body,*unused=self.fixture(); chunks={}; calls=[]
        original=reader.acquire
        def acquired_once(m,selection,maximum):
            calls.append(selection[0]);return original(m,selection,maximum)
        with patch.object(reader,'acquire',side_effect=acquired_once):
            while True:
                part=reader.next_chunk(manifest)
                if part.get('end_of_material'):break
                value=part['text'].encode() if part['encoding']=='utf8' else base64.b64decode(part['text'])
                self.assertLessEqual(len(value),reader.CHUNK)
                prior=chunks.setdefault(part['source'],bytearray())
                self.assertEqual(part['offset'],len(prior));prior.extend(value)
                self.assertEqual(part['through'],len(prior))
                self.assertLessEqual(manifest.with_suffix('.item').stat().st_size,reader.CACHE_MAX)
            self.assertEqual(len(calls),len(reader.selections(acquired)))
            self.assertEqual(len(calls),len(set(calls)))
            for source,witness in acquired['source'].items():
                self.assertEqual(reader.digest(chunks[source]),witness['sha256'])
                self.assertEqual(len(chunks[source]),witness['bytes'])
            self.assertIn(body,[bytes(v) for v in chunks.values()])
            self.assertEqual(manifest.with_suffix('.item').stat().st_size,0)
            self.assertEqual(reader.next_chunk(manifest)['offset'],0)
            self.assertEqual(len(calls),len(reader.selections(acquired))+1)

    def test_changed_emitted_history_method_prior_refuses_without_reacquisition(self):
        for index in range(3):
            manifest,acquired,body,history,method,prior=self.fixture()
            for unused in range(3):reader.next_chunk(manifest)
            target=[history,method,prior][index];target.write_text('fiction changed input')
            with patch.object(reader,'acquire',side_effect=AssertionError('no acquisition after invalidation')):
                with self.assertRaises(ValueError):reader.next_chunk(manifest)

    def test_cache_tamper_revision_reset_bound_and_wrong_source_digest(self):
        manifest,acquired,*unused=self.fixture()
        while True:
            part=reader.next_chunk(manifest)
            if part.get('total_bytes',0)>reader.CHUNK:break
        manifest.with_suffix('.item').write_bytes(b'fiction tampered cache')
        with self.assertRaisesRegex(ValueError,'cache changed'):reader.next_chunk(manifest)
        revised={**acquired,'cache_max_bytes':10};manifest.write_text(encode(revised))
        with self.assertRaisesRegex(ValueError,'bound'):reader.next_chunk(manifest)
        revised=copy.deepcopy(acquired);first=next(iter(revised['source']));revised['source'][first]['sha256']='0'*64
        manifest.write_text(encode(revised))
        with self.assertRaisesRegex(ValueError,'source changed'):
            while True:reader.next_chunk(manifest)

    def test_legacy_cursor_keeps_partial_offset_and_absent_history_is_fenced(self):
        manifest,acquired,body,history,*unused=self.fixture()
        source=next(k for k,v in acquired['source'].items() if v['bytes']==len(body))
        index=next(i for i,s in enumerate(reader.selections(json.loads(manifest.read_bytes()))) if s[0]==source)
        manifest.with_suffix('.cursor').write_text(encode({'revision':reader.digest(manifest.read_bytes()),
                                                          'item':index,'offset':reader.CHUNK}))
        part=reader.next_chunk(manifest)
        actual=part['text'].encode() if part['encoding']=='utf8' else base64.b64decode(part['text'])
        self.assertEqual(part['offset'],reader.CHUNK)
        self.assertEqual(actual,body[reader.CHUNK:2*reader.CHUNK])
        # A genuinely absent permitted history is also an exact input, not an
        # invitation to accept a later-created history under the old revision.
        absent=self.directory/'absent-history.txt'
        acquired.update(history=str(absent),history_sha256=reader.digest(b''))
        manifest.write_text(encode(acquired))
        reader.next_chunk(manifest);reader.next_chunk(manifest)
        absent.write_text('fiction late history')
        with self.assertRaisesRegex(ValueError,'history/method changed'):reader.next_chunk(manifest)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(cls(name) for cls in (Export,ReviewsRoute,Reader)
                              for name in cls.__dict__ if name.startswith('test_'))
