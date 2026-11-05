"""Fictional local invariants. NO native identities/accounts/acceptance fixtures.

Real local Git, pipes and sockets are tested as such. Native attempt fields stay
NULL. The parent separately owns native continuation and elapsed-retention proof.
"""
import asyncio
from contextlib import asynccontextmanager
import copy
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from test_processing188 import EngineTests, SelectionTests, engine_config
from coordinator_runtime import processing, service, reviews, retirement, capacity
from coordinator_runtime.cleanup import sweep, eligible_event
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import Dispatcher as BaseDispatcher
from coordinator_runtime.resource_scopes import blocked


class ContinuingSelection(SelectionTests):
    def setUp(self):
        super().setUp()
        self.runtime.config['limits']['max_attempts'] = 10
        self.board.conn.execute('UPDATE coordinator_software_grants_v1 SET configuration=?', (digest(self.runtime.config),))

    def selection(self, **changes):
        value = super().selection()
        value.pop('expires'); value.pop('max_starts')
        value['future_intake'] = True
        value['service'] = {'max_inflight': 3, 'reviews': {}, 'legacy_resources': {}}
        return {**value, **changes}

    # Inherit the fixture, not its finite-grant assertions.
    def test_continuing_selection_has_no_expiry_or_lifetime_start_reset(self):
        key = self.issue()
        self.runtime.now += 864000
        self.runtime.db.executescript('CREATE TABLE attempts(id,controller,collected);')
        self.runtime.controller = 'fictional-original-service'
        self.runtime.db.execute('UPDATE processing_capabilities SET starts=1000000')
        self.runtime.db.commit()
        self.assertEqual(self.runtime.processing.current()[0]['id'], key)
        with self.runtime.tx():
            self.runtime.processing.reserve(None, None, None)
        self.assertEqual(self.runtime.one('SELECT starts FROM processing_capabilities')['starts'], 1000001)
        processing.revoke(self.runtime, self.boards, key)
        with self.assertRaises(Refusal):
            self.runtime.processing.current()


class Completion(EngineTests):
    def continuing(self):
        row = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))
        selected = json.loads(row['selection'])
        selected.pop('expires', None); selected.pop('max_starts', None)
        selected['service'] = {'max_inflight': 5, 'reviews': {}, 'legacy_resources': {}}
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selected), self.key))
        return selected

    def test_O1_scoped_independent_integrator_and_real_overlap(self):
        task = self.runtime.config['tasks']['bi']
        fresh, held = self.directory / 'fresh', self.directory / 'held'
        fresh.mkdir(); held.mkdir()
        task.update(require_package_scope=True, scope_roots=[str(self.directory)], cwd=str(self.directory),
                    effect_authority={'read_roots': [], 'write_roots': [], 'operations': ['read-source']})
        self.runtime.db.execute("UPDATE enrollments SET legacy_hold='fictional old debt' WHERE role='Branch'")
        # Configuration is frozen for this test's independently constructed capability.
        row = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))
        refreshed = json.loads(row['selection'])
        refreshed['basis']['configuration'] = digest(self.runtime.config)
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(refreshed), self.key))
        selected = self.continuing()
        selected['service']['legacy_resources']['Branch'] = {'original_hold': 'fictional old debt', 'roots': [str(held)],
                                                             'unbounded': False, 'evidence': 'fictional explicit resource inventory'}
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selected), self.key))
        def admit(package, path):
            scope = {'cwd': str(path), 'read_roots': [str(path)], 'write_roots': [], 'network': False,
                     'procedure': 'fictional bounded procedure', 'resource_evidence': 'fictional admitted resource evidence'}
            self.runtime.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)', (package, 'fictional-scope-owner', encode({'task_scopes': {'bi': scope}})))
        admit('fictional-independent', fresh)
        admit('fictional-overlapping', held)
        self.event('fictional-new-branch', 'Branch', 'bi', 'fictional-independent')
        self.event('fictional-old-overlap', 'Branch', 'bi', 'fictional-overlapping')
        job = self.runtime.reserve()
        self.assertEqual(job['package'], 'fictional-independent')
        self.assertIsNone(self.runtime.reserve())
        self.assertEqual(self.runtime.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'], 'fictional old debt')
        queue = self.runtime.one("SELECT * FROM queue WHERE event='fictional-old-overlap'")
        self.assertTrue(blocked(self.runtime, queue))

    def test_O2_aged_delivery_cannot_retire_with_pending_child_or_later_child_clock(self):
        now = [1000.]
        self.runtime.clock = lambda: now[0]
        self.event('fictional-control-chain', 'Work', 'wp')
        child = {'id': 'fictional-work-child', 'role': 'Work', 'recipient': 'fictional-logical-Work',
                 'kind': 'response', 'parent': 'fictional-control-chain', 'body': 'whole fictional return',
                 'package': None, 'allowed_tasks': ['wp']}
        self.runtime.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',
                                (child['id'], 'Work', encode(child), digest(child), now[0], child['parent']))
        self.runtime.db.execute("INSERT INTO alerts VALUES('fictional-alert','fictional-subject','violation',1000,'{}',1000)")
        self.runtime.config['delivery']['recipients']['Work'] = {'session': 'fictional-logical-Work'}
        with self.runtime.tx():
            key = self.runtime._outbox('Work','Work','alert',{},alert='fictional-alert')
        self.runtime.db.execute('INSERT INTO processing_delivery_links VALUES(?,?)', (key, 'fictional-control-chain'))
        self.runtime.db.execute("UPDATE outboxes SET state='settled',processed_at=1000 WHERE id=?", (key,))
        now[0] += 86400
        from coordinator_runtime.frontier import require_aged
        with self.assertRaises(Refusal): require_aged(self.runtime, key, 86400)
        # Explicit fictional states distinguish downstream completion from delivery.
        self.runtime.db.execute("UPDATE events SET processed_at=?,state='processed'", (now[0],))
        with self.assertRaises(Refusal): require_aged(self.runtime, key, 86400)
        now[0] += 86400
        self.assertTrue(require_aged(self.runtime, key, 86400)['complete'])
        self.runtime.set_hold(child['id'], 'fictional late source hold')
        with self.assertRaises(Refusal): require_aged(self.runtime, key, 86400)

    def test_C1_sweep_preserves_aged_alert_without_explicit_all_hold_retirement(self):
        self.runtime.db.execute("INSERT INTO alerts VALUES('fictional-alert','fictional-subject','violation',1,'{}',2)")
        self.runtime.clock = lambda: 90000.
        sweep(self.runtime)
        self.assertIsNotNone(self.runtime.one('SELECT * FROM alerts'))

    def completed(self, name):
        self.event(name, 'Work', 'wp')
        self.runtime.db.execute("UPDATE events SET state='processed',processed_at=1000 WHERE id=?", (name,))
        self.runtime.db.execute("UPDATE queue SET state='done' WHERE event=?", (name,))
        self.runtime.clock = lambda: 90000.
        sweep(self.runtime)

    def receipt(self, basis):
        return {'basis': basis['basis'], 'qualified_at': self.runtime.clock(), 'holds': {h: [] for h in capacity.HOLDS},
                'evidence': 'fictional all-custodian control, not actual acceptance',
                **{name: {key: {'hash': value, 'custodian': 'fictional-custodian',
                               'evidence': 'fictional original-source conservation', 'disposition': 'producer-owned-disposable'}
                          for key, value in basis[name].items()} for name in ('sources','results')}}

    def test_repeated_same_journal_retirement_reuses_logical_event_capacity(self):
        self.continuing()
        self.runtime.config['limits']['max_events'] = 2
        # Reconstruct this fictional capability after its fixture-only config edit.
        selected = self.continuing()
        selected['basis']['configuration'] = digest(self.runtime.config)
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selected), self.key))
        for n in range(8):
            name = 'fictional-disposable-' + str(n)
            self.completed(name)
            observed = retirement.basis(self.runtime, name)
            retired = retirement.apply(self.runtime, name, 'fictional-issuer', self.receipt(observed))
            self.assertEqual(retired['retired']['members']['events'], [name])
            self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 0)
        self.assertEqual(self.runtime.path.name, 'runtime.sqlite3')

    def test_retirement_receipt_cannot_clear_new_hold_or_omit_full_child(self):
        self.continuing(); self.completed('fictional-disposable')
        observed = retirement.basis(self.runtime, 'fictional-disposable')
        receipt = self.receipt(observed)
        self.runtime.set_hold('fictional-disposable', 'fictional new recovery duty')
        with self.assertRaises(Refusal): retirement.apply(self.runtime, 'fictional-disposable', 'fictional-issuer', receipt)
        self.assertIsNotNone(self.runtime.one('SELECT id FROM events'))

    def test_relocated_body_recovers_source_and_retained_basis(self):
        event = self.event('fictional-original', 'Work', 'wp', queued=False)
        with self.runtime.tx():
            attempt = self.runtime._attempt('input-control', event['id'], None, processing.SOL, None)
        body = {'fictional': 'result body conserved once'}
        self.runtime.collect(attempt, {'exit': 0, 'capture':'complete', 'cleanup':'no-session-created', 'result': body})
        response = {'id':'fictional-response','kind':'response','role':'Work','source_attempt':attempt,
                    'body':body,'parent':event['id']}
        self.runtime.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',
                                (response['id'],'Work',encode(response),digest(response),1000,event['id']))
        with self.runtime.tx():
            row = self.runtime.one('SELECT * FROM events WHERE id=?',(response['id'],))
            replacement = self.runtime.source_for_retirement(row)
            self.runtime.db.execute('UPDATE events SET payload=? WHERE id=?',(replacement,response['id']))
        self.assertEqual(replacement,'{}')
        self.assertEqual(self.runtime.recover_source(response['id']),response)
        self.assertEqual(self.runtime.event(response['id']),response)

    def test_current_inflight_bound_preserves_old_unknowns_without_global_start_debt(self):
        selected = self.continuing()
        selected['service']['max_inflight'] = 1
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?',(encode(selected),self.key))
        self.event('fictional-message','Work','wp',queued=False)
        self.runtime.db.execute("INSERT INTO attempts(id,kind,controller,profile,binding,created,state) VALUES('fictional-old','classifier','fictional-old-collector',NULL,'{}',1,'unknown')")
        first = self.runtime.claim_classification()
        self.assertIsNotNone(first)
        self.event('fictional-later','Work','wp',queued=False)
        with self.assertRaises(Refusal): self.runtime.claim_classification()
        self.assertEqual(self.runtime.one("SELECT state FROM attempts WHERE id='fictional-old'")['state'],'unknown')
        self.assertIsNone(self.runtime.attempt(first[0])['session'])

    def test_original_service_control_reconnects_without_relaunch_or_fabricated_END(self):
        self.continuing()
        class Board:
            def verify_authority(self, runtime): return {'fictional': True}
        async def test():
            # This seam omits workflow/model ticks, not the real Unix endpoint,
            # original lifetime, protocol or journal writes being tested.
            ready = asyncio.Event()
            async def idle(dispatcher, emit):
                await dispatcher.stopping.wait()
            def emitted(value):
                if value.get('state') == 'serving': ready.set()
            with patch.object(service.Dispatcher, 'run', idle), patch.object(service.Dispatcher, 'recover_originals',
                    lambda d: {'collector': d.store.controller, 'uncollected': [], 'fictional_tick_seam': True}):
                original = asyncio.create_task(service.serve(self.runtime, {'Work':Board()}, self.key, emitted, models=object()))
                await asyncio.wait_for(ready.wait(),2)
                first = await service.control(self.runtime,self.key,'status')
                second = await service.control(self.runtime,self.key,'recover')
                self.assertEqual(first['runs'][0]['controller'],self.runtime.controller)
                self.assertEqual(second['collector'],self.runtime.controller)
                self.assertIsNone(first['runs'][0]['returned'])
                stop = await service.control(self.runtime,self.key,'stop')
                self.assertIn('parent',stop['state'])
                await asyncio.wait_for(original,2)
                with self.assertRaises(ConnectionRefusedError):
                    await asyncio.open_unix_connection(service.endpoint(self.runtime,self.key))
                self.assertEqual(self.runtime.one('SELECT state FROM processing_runs')['state'],'owned')
                self.assertNotIn('actual_END',self.runtime.one('SELECT receipt FROM service_runs')['receipt'])
        asyncio.run(test())

    def test_native_wrapper_collects_actual_local_failure_without_a_native_identity(self):
        self.event('fictional-local-call','Work','wp',queued=False)
        with self.runtime.tx(): attempt=self.runtime._attempt('input-control','fictional-local-call',None,processing.SOL,None)
        program=self.directory/'local-failure'
        program.write_text('#!/usr/bin/python3\nimport sys\nraise SystemExit(7)\n')
        program.chmod(0o700)
        self.runtime.authorize_launch=lambda a: None  # Explicit local transport seam, no provider authority.
        @asynccontextmanager
        async def admission(profile): yield {'fictional-local-only':True}
        self.runtime.execution_pool.admission=admission
        policy={'caller':str(program),'caller_sha256':reviews.sha(program.read_bytes()),'deadline':1,'routes':{None:'fictional-local-refusal-only'},'components':{'fictional-component':{'repository':'/fixtures'}}}
        context={'component':'fictional-component','route':'fictional-local-refusal-only','profile':None,
                 'handle':str(self.directory/'unused-handle'),'run':None}
        code,receipt,answer=asyncio.run(reviews.Native().call(self.runtime,attempt,policy,context,self.directory/'local-output','fictional local input',[],opening=True))
        self.assertEqual(code,7)
        self.assertEqual(receipt['class'],'incomplete')
        self.assertIsNone(answer)
        self.assertIsNone(self.runtime.attempt(attempt)['session'])
        self.assertFalse(Path(context['handle']).exists())


class Material(EngineTests):
    def test_kernel_source_and_dependency_are_read_only_with_positive_fixture_write(self):
        import errno
        for path in ('/src/tools/coordinator-runtime/coordinator_runtime/service.py', '/src/tools/direct-child/execution_pool.py'):
            self.assertTrue(os.statvfs(path).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as raised:
                os.open(path,os.O_WRONLY)
            self.assertEqual(raised.exception.errno,errno.EROFS)
        (self.directory/'positive-write').write_text('actual isolated fixture write')
        self.assertTrue((self.directory/'positive-write').exists())

    def setup_repository(self):
        repository = self.directory / 'source'
        repository.mkdir()
        def run(*args): return subprocess.check_output(['git','-C',str(repository),*args]).decode().strip()
        run('init','-q'); run('config','user.name','Fictional local fixture'); run('config','user.email','fixture@invalid')
        (repository/'module.py').write_text('value = 1\n')
        run('add','module.py'); run('-c','commit.gpgsign=false','commit','-qm','fictional base fixture')
        base=run('rev-parse','HEAD')
        (repository/'module.py').write_text('value = 2\n')
        run('add','module.py'); run('-c','commit.gpgsign=false','commit','-qm','fictional correction fixture')
        head=run('rev-parse','HEAD')
        policy={'components':{'fictional-component':{'repository':str(repository),'origin':'fictional-fixture-only',
                'paths':['module.py'],'history':str(self.directory/'history.txt'),'authority':'fictional source read'}},'method_files':{}}
        packet={'component':'fictional-component','origin':'fictional-fixture-only','base':base,'head':head,'previous':None,'answered_ids':[]}
        return policy,packet

    def test_exact_source_pins_correction_diff_and_no_goal_fields(self):
        policy,packet=self.setup_repository()
        acquired=reviews.material(policy,packet,None)
        self.assertIn('-value = 1',acquired['correction_diff'])
        self.assertIn('+value = 2',acquired['correction_diff'])
        with self.assertRaises(Refusal): reviews.material(policy,{**packet,'goal':'leading repair'},None)
        with self.assertRaises(Refusal): reviews.material(policy,{**packet,'head':'HEAD'},None)
        with self.assertRaises(Refusal): reviews.material(policy,{**packet,'answered_ids':['fabricated-prior']},None)
        with self.assertRaises(Refusal): reviews.material(policy,{**packet,'previous':packet['base']},None)

    def test_whole_history_and_same_previous_head_are_bound(self):
        policy,packet=self.setup_repository()
        history=Path(policy['components']['fictional-component']['history'])
        history.write_text('fictional prior attributed partial coverage\n')
        prior={'head':packet['base'],'history_hash':reviews.sha(history.read_bytes())}
        packet.update(previous=packet['base'],answered_ids=['fictional-observation'])
        acquired=reviews.material(policy,packet,prior)
        self.assertEqual(acquired['history_sha256'],prior['history_hash'])
        history.write_text('changed history')
        with self.assertRaises(Refusal): reviews.material(policy,packet,prior)

    def test_selected_method_follows_actual_constituent_homes_not_just_family_names(self):
        home=self.directory/'method'; (home/'families').mkdir(parents=True); (home/'organization').mkdir()
        entry=home/'unified-reviewer.prompt.md'; family=home/'families'/'organization.md'; definition=home/'organization'/'entity.md'
        entry.write_text('[selected family](families/organization.md)\n')
        family.write_text('[constituent](../organization/entity.md)\n')
        definition.write_text('Fictional definition for dependency-wiring test only.\n')
        pins=reviews.method_files(str(entry))
        self.assertEqual(set(pins),{str(entry),str(family),str(definition)})
        definition.write_text('Changed fictional definition.\n')
        self.assertNotEqual(reviews.method_files(str(entry)),pins)

    def test_stable_read_facade_streams_exact_material_and_revalidates_history(self):
        from coordinator_runtime.review_reader import next_chunk
        policy, packet = self.setup_repository()
        history = Path(policy['components']['fictional-component']['history'])
        history.write_text('fictional permitted prior history\n')
        acquired = reviews.material(policy, packet, None)
        manifest = self.directory/'material.json'
        manifest.write_text(encode(acquired))
        received = {}
        while True:
            item = next_chunk(str(manifest))
            if item.get('end_of_material'): break
            self.assertEqual(item['encoding'],'utf8')
            received.setdefault(item['source'],'')
            received[item['source']] += item['text']
        self.assertEqual(received['history'],'fictional permitted prior history\n')
        self.assertEqual(received[packet['head']+':module.py'],'value = 2\n')
        self.assertEqual(received[packet['base']+':module.py'],'value = 1\n')
        self.assertIn('+value = 2',received['actual-correction-diff'])
        history.write_text('unqualified changed history')
        with self.assertRaises(ValueError): next_chunk(str(manifest))

    def test_executor_conserves_actual_local_original_failure_without_native_identity(self):
        from contextlib import asynccontextmanager
        policy, packet = self.setup_repository()
        method = self.directory/'fictional-method.md'; method.write_text('Fictional local failure path only.\n')
        caller = self.directory/'local-original'; caller.write_text('#!/usr/bin/python3\nraise SystemExit(7)\n'); caller.chmod(0o700)
        policy.update(method=str(method),method_files=reviews.method_files(str(method)),caller=str(caller),caller_sha256=reviews.sha(caller.read_bytes()),deadline=1,
                      routes={None:'fictional-local-refusal-only'})
        # Explicit NULL projection avoids inventing an account for this local
        # SQL/pipe failure test. Production context profiles stay NOT NULL.
        self.runtime.db.execute('DROP TABLE review_contexts')
        self.runtime.db.executescript(reviews.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT'))
        self.event('fictional-original-call','Work','wp',queued=False)
        with self.runtime.tx():
            attempt=self.runtime._attempt('input-control','fictional-original-call',None,processing.SOL,None)
        @asynccontextmanager
        async def admission(profile): yield {'fictional-local-only':True}
        self.runtime.execution_pool.admission=admission
        self.runtime.authorize_launch=lambda a: None
        with self.assertRaises(Refusal):
            asyncio.run(reviews.Executor(self.runtime).execute({},attempt,policy,packet))
        context=self.runtime.one('SELECT * FROM review_contexts')
        self.assertEqual(context['state'],'interrupted')
        self.assertIsNone(context['run']); self.assertIsNone(context['profile'])
        calls=json.loads(self.runtime.one('SELECT receipt FROM review_calls')['receipt'])
        self.assertEqual(calls[0]['actual_END'],7)
        self.assertIsNone(self.runtime.attempt(attempt)['session'])

    def test_partial_coding_commit_failure_still_attempts_normal_push_and_exact_readback(self):
        from coordinator_runtime import coding
        calls=[]
        class FictionalGit:
            def __init__(self, repository, output):
                self.records=[]; self.output=Path(output); self.output.mkdir()
            def run(self,*args):
                calls.append(args); self.records.append({'fictional_argv':args})
                if args[0]=='symbolic-ref': return 0,b'fictional-existing-branch\n'
                if args[0]=='rev-parse': return 0,b'a'*40+b'\n'
                if args[0]=='diff': return 0,b'module.py\0'
                if args[0]=='ls-files': return 0,b''
                if args[0]=='commit': return 7,b''
                if args[0]=='show': return 0,b'a'*40+b'\n'+b'b'*40+b'\n'+b'c'*40+b'\n'
                if args[0]=='ls-remote': return 0,b'a'*40+b'\trefs/heads/fictional-existing-branch\n'
                return 0,b''
        with patch.object(coding,'Git',FictionalGit):
            outcome=coding.publish('/fictional-nonexistent-source','fictional-existing-branch',['module.py'],
                                   'fictional handback',str(self.directory/'handback'),partial=True)
        self.assertTrue(outcome['partial'])
        self.assertTrue(any('signed commit failed' in error for error in outcome['errors']))
        self.assertIn(('commit','-S','-m','fictional handback'),calls)
        self.assertIn(('push','origin','HEAD:refs/heads/fictional-existing-branch'),calls)
        self.assertIn(('ls-remote','--exit-code','origin','refs/heads/fictional-existing-branch'),calls)
        self.assertFalse(any('--force' in command or 'reset' in command or 'rebase' in command for command in calls))


# unittest inheritance above supplies useful fixture methods, but running those
# inherited tests here would obscure the precise Act239 selection.
for cls, parent in ((ContinuingSelection, SelectionTests),(Completion,EngineTests),(Material,EngineTests)):
    for name in dir(parent):
        if name.startswith('test_') and name not in cls.__dict__:
            setattr(cls,name,None)
del cls, parent, name, EngineTests, SelectionTests


if __name__ == '__main__': unittest.main(verbosity=2)
