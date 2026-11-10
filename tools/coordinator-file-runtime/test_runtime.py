"""Finite SQL-disabled local trials. All actor identities/evidence are synthetic.

Artifacts, including failures and interrupted temporaries, are retained. No
provider, legacy source/state, private store, or actual retained-data cleanup.
"""
import builtins
import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import uuid

_original_import = builtins.__import__
_sql_attempts = []


def no_sql(name, *args, **kwargs):
    if name.split('.')[0] in {'sqlite3', '_sqlite3'}:
        _sql_attempts.append(name)
        raise RuntimeError('SQL disabled by experiment')
    return _original_import(name, *args, **kwargs)


builtins.__import__ = no_sql
from runtime import Runtime, create, _pool
from storage import Held, Files, encode, LIMITS

ARTIFACTS = Path(os.environ['COORDINATOR_TEST_ARTIFACTS'])
CTX = mp.get_context('fork')
TOKENS = {'work': 'synthetic-work-token', 'branch': 'synthetic-branch-token',
          'reviews': 'synthetic-reviews-token', 'qa': 'synthetic-qa-token'}


def call(rt, op, actor='work', **kw):
    return rt.call(op, actor, TOKENS[actor], **kw)


def retry(rt, op, actor='work', **kw):
    # Finite retries of a refused metadata transaction, never an ambiguous
    # postcommit launch or provider retry. Not a native-agent polling loop.
    for _ in range(100):
        try:
            return call(rt, op, actor, **kw)
        except Held as exc:
            if str(exc) != 'metadata busy; retry same operation, no launch':
                raise
            time.sleep(.005)
    raise AssertionError('finite metadata contention retry bound exceeded')


def worker(path, args, actor, ready, release):
    rt = Runtime(path)
    try:
        reserved = retry(rt, 'reserve', actor, **args)
        c = reserved['collector']
        start = retry(rt, 'start', actor, attempt=args['attempt'], collector=c,
                      substrate='fixture', evidence='actual finite fixture process')
        ready.put({'ok': True, 'at': time.monotonic(), 'pid': os.getpid()})
        if not release.wait(8):
            raise AssertionError('fixture release deadline')
        retry(rt, 'collect', actor, attempt=args['attempt'], collector=c, launch_id=start['launch_id'],
              end=0, result={'finite': True}, evidence='current original fixture completing')
        retry(rt, 'reconcile', actor, attempt=args['attempt'], collector=c, evidence='no external effects')
    except BaseException as exc:
        ready.put({'ok': False, 'error': str(exc)})
        raise


class Trial(unittest.TestCase):
    def setUp(self):
        self.root = ARTIFACTS / (self._testMethodName + '-' + uuid.uuid4().hex[:8])
        self.root.mkdir(mode=0o700)
        self.routes = self.root / 'routes.toml'
        self.routes.write_text('[providers.codex]\npool = [".codex2", ".codex4", ".codex5"]\n'
                               'manual_profiles = [".codex2", ".codex3", ".codex4", ".codex5"]\n'
                               '[rotation]\nstate_dir = ' + json.dumps(str(self.root / 'rotation')) + '\n')
        (self.root / 'fast-tier').write_text('true\n')
        self.path = self.root / 'state'
        create(self.path, 'work', TOKENS['work'], self.routes)
        self.rt = Runtime(self.path)
        for actor, role in [('branch', 'Branch'), ('reviews', 'Reviews'), ('qa', 'QA')]:
            call(self.rt, 'invite', target=actor, role=role, invitation_token=TOKENS[actor], basis='synthetic fixture invitation')
            call(self.rt, 'adopt', actor, basis='synthetic self-adoption; no real owner represented')

    def ingest(self, event):
        return call(self.rt, 'ingest', event=event, payload={'point': event}, producer='fixture', source_basis='independent test intent')

    def classify(self, event, owner='work', kind='known'):
        self.ingest(event)
        status = self.raw()['events'][event]
        a = call(self.rt, 'reserve', attempt='class-' + event, event=event, phase='classifier', resources={}, basis={})
        c = a['collector']
        start = call(self.rt, 'start', attempt='class-' + event, collector=c, substrate='fixture', evidence='synthetic LOW provenance')
        call(self.rt, 'collect', attempt='class-' + event, collector=c, launch_id=start['launch_id'], end=0,
             result={'event_hash': status['source_hash'], 'classification': kind}, evidence='synthetic collected LOW')
        call(self.rt, 'classify', event=event, attempt='class-' + event, collector=c, classification=kind, owner=owner, needs=['outcome'])
        call(self.rt, 'reconcile', attempt='class-' + event, collector=c, evidence='classifier no effects')
        call(self.rt, 'ack', event=event)
        return c

    def raw(self):
        # Only owned synthetic state; no directory discovery.
        return json.loads((self.path / 'state.json').read_text())['state']

    def reserve(self, event, attempt='a', actor='work', phase='known', **kw):
        return call(self.rt, 'reserve', actor, attempt=attempt, event=event, phase=phase,
                    resources={'point:' + event: 'write'}, basis={'point:' + event: 0}, point=event, **kw)

    def collect(self, attempt, collector, actor='work', end=0):
        start = call(self.rt, 'start', actor, attempt=attempt, collector=collector, substrate='fixture', evidence='synthetic start')
        call(self.rt, 'collect', actor, attempt=attempt, collector=collector, launch_id=start['launch_id'], end=end,
             result={'proposal': True}, evidence='finite actual numeric fixture outcome')

    def test_sql_attempts_fail_and_runtime_imports_do_not_use_sql(self):
        before = len(_sql_attempts)
        with self.assertRaisesRegex(RuntimeError, 'SQL disabled'):
            __import__('sqlite3')
        self.assertEqual(len(_sql_attempts), before + 1)
        call(self.rt, 'status')
        self.assertEqual(len(_sql_attempts), before + 1)

    def test_self_adoption_revocation_and_no_borrowed_collector(self):
        with self.assertRaises(Held):
            self.rt.call('status', 'qa', TOKENS['branch'])
        self.classify('one')
        a = self.reserve('one')
        with self.assertRaisesRegex(Held, 'original collector'):
            call(self.rt, 'start', attempt='a', collector='borrowed', substrate='fixture', evidence='bad')
        call(self.rt, 'revoke', target='qa', reason='fixture revocation')
        with self.assertRaisesRegex(Held, 'revoked'):
            call(self.rt, 'inbox', 'qa')
        self.assertEqual(self.raw()['attempts']['a']['collector'], a['collector'])

    def test_duplicate_changed_content_and_ack_before_responsibility(self):
        self.ingest('one')
        self.assertTrue(self.ingest('one')['duplicate'])
        with self.assertRaisesRegex(Held, 'changed content'):
            call(self.rt, 'ingest', event='one', payload={'changed': True}, producer='fixture', source_basis='independent test intent')
        with self.assertRaisesRegex(Held, 'no ACK'):
            call(self.rt, 'ack', event='one')
        self.assertFalse(self.raw()['events']['one']['ack'])

    def test_classifier_typed_capture_and_unresolved_responsibilities(self):
        self.classify('uncertain', kind='unresolved')
        with self.assertRaisesRegex(Held, 'unresolved/control'):
            self.reserve('uncertain')
        with self.assertRaisesRegex(Held, 'incomplete'):
            call(self.rt, 'finish', event='uncertain')
        self.assertEqual(self.raw()['events']['uncertain']['classification']['provenance'], 'synthetic LOW provenance')
        call(self.rt, 'resolve', event='uncertain', need='outcome', evidence='owned unresolved need explicitly dispositioned in fixture')
        call(self.rt, 'finish', event='uncertain')

    def test_failed_or_mismatched_low_cannot_ack(self):
        self.ingest('one')
        a = call(self.rt, 'reserve', attempt='class', event='one', phase='classifier', resources={}, basis={})
        self.collect('class', a['collector'], end=4)
        with self.assertRaisesRegex(Held, 'fresh collected LOW'):
            call(self.rt, 'classify', event='one', attempt='class', collector=a['collector'], classification='known', owner='work', needs=['outcome'])
        with self.assertRaisesRegex(Held, 'no ACK'):
            call(self.rt, 'ack', event='one')

    def test_independent_process_overlap_discovery_and_responsive_control(self):
        self.classify('new', kind='new')
        self.classify('known')
        ready, release = CTX.Queue(), CTX.Event()
        processes = []
        for args in [dict(attempt='discovery', event='new', phase='discovery', resources={}, basis={}),
                     dict(attempt='known', event='known', phase='known', point='known', resources={'point:known': 'write'}, basis={'point:known': 0})]:
            p = CTX.Process(target=worker, args=(self.path, args, 'work', ready, release))
            p.start(); processes.append(p)
            self.assertTrue(ready.get(timeout=5)['ok'])
        start = time.monotonic()
        self.ingest('during-block')
        call(self.rt, 'status')
        self.assertLess(time.monotonic() - start, 2)
        self.assertTrue(all(p.is_alive() for p in processes))
        release.set()
        for p in processes:
            p.join(5)
            self.assertEqual(p.exitcode, 0)

    def test_resources_conflict_and_stale_proposal_preserve_unrelated(self):
        self.classify('one'); self.classify('two')
        a = self.reserve('one')
        with self.assertRaisesRegex(Held, 'resource conflict'):
            call(self.rt, 'reserve', attempt='b', event='two', phase='known', point='one', resources={'point:one': 'write'}, basis={'point:one': 0})
        self.collect('a', a['collector'])
        call(self.rt, 'reconcile', attempt='a', collector=a['collector'], evidence='no effect; proposal not applied')
        b = call(self.rt, 'reserve', attempt='b', event='two', phase='known', point='one', resources={'point:one': 'write'}, basis={'point:one': 0})
        self.collect('b', b['collector'])
        call(self.rt, 'integrate', attempt='b', collector=b['collector'], writes={'point:one': {'value': 2}})
        with self.assertRaisesRegex(Held, 'stale proposal'):
            call(self.rt, 'integrate', attempt='a', collector=a['collector'], writes={'point:one': {'stale': 1}})
        self.assertEqual(self.raw()['versions'], {'point:one': 1})
        self.assertFalse(self.raw()['events']['two']['finished'])

    def test_qa_five_actual_processes_same_package_and_separate_consolidation(self):
        for i in range(7):
            self.classify('q' + str(i), 'qa')
            call(self.rt, 'package', package='pkg' + str(i), event='q' + str(i), scope='finite fixture package', basis='synthetic admission')
        ready, release = CTX.Queue(), CTX.Event()
        processes = []
        for i in range(5):
            args = dict(attempt='qa' + str(i), event='q' + str(i), phase='qa-execute', package='pkg' + str(i), resources={}, basis={})
            p = CTX.Process(target=worker, args=(self.path, args, 'qa', ready, release))
            p.start(); processes.append(p)
            self.assertTrue(ready.get(timeout=5)['ok'])
        with self.assertRaisesRegex(Held, 'capacity'):
            call(self.rt, 'reserve', 'qa', attempt='six', event='q5', phase='qa-execute', package='pkg5', resources={}, basis={})
        with self.assertRaisesRegex(Held, 'already owned'):
            call(self.rt, 'reserve', 'qa', attempt='same', event='q0', phase='qa-execute', package='pkg0', resources={}, basis={})
        # A separate completed package can consolidate while all five execution
        # slots remain occupied; execution capacity is not a global QA mutex.
        self.assertTrue(all(p.is_alive() for p in processes))
        release.set()
        for p in processes:
            p.join(5); self.assertEqual(p.exitcode, 0)
        con = call(self.rt, 'reserve', 'qa', attempt='con', event='q0', phase='qa-consolidate', package='pkg0', resources={}, basis={})
        with self.assertRaisesRegex(Held, 'capacity'):
            call(self.rt, 'reserve', 'qa', attempt='con2', event='q1', phase='qa-consolidate', package='pkg1', resources={}, basis={})
        # Five independent executions can resume while consolidation is reserved.
        more = call(self.rt, 'reserve', 'qa', attempt='six-now', event='q5', phase='qa-execute', package='pkg5', resources={}, basis={})
        self.assertTrue(con['collector'] and more['collector'])

    def test_packet_four_roles_corrections_and_whole_processing(self):
        self.classify('one')
        for actor in ('branch', 'reviews', 'qa'):
            call(self.rt, 'send', packet='to-' + actor, event='one', recipient=actor, payload={'request': 'finite addressed package'})
            inbox = call(self.rt, 'inbox', actor)['packets']
            self.assertEqual(inbox[0]['recipient'], actor)
            with self.assertRaisesRegex(Held, 'exactly one'):
                call(self.rt, 'receipt', actor, packet='to-' + actor, stage='settled', evidence='skipped pickup')
            call(self.rt, 'receipt', actor, packet='to-' + actor, stage='picked-up', evidence='synthetic pickup')
            call(self.rt, 'receipt', actor, packet='to-' + actor, stage='processed', evidence='synthetic processing')
        call(self.rt, 'resolve', event='one', need='outcome', evidence='fixture outcome')
        with self.assertRaisesRegex(Held, 'downstream unsettled'):
            call(self.rt, 'finish', event='one')
        for actor in ('branch', 'reviews', 'qa'):
            call(self.rt, 'receipt', actor, packet='to-' + actor, stage='settled', evidence='synthetic downstream acceptance')
        call(self.rt, 'send', packet='correction', event='one', recipient='qa', payload={'corrected': True}, correction_of='to-qa')
        with self.assertRaisesRegex(Held, 'downstream unsettled'):
            call(self.rt, 'finish', event='one')
        for stage in ('picked-up', 'processed', 'settled'):
            call(self.rt, 'receipt', 'qa', packet='correction', stage=stage, evidence='fixture correction handled')
        call(self.rt, 'finish', event='one')
        self.assertIsNotNone(self.raw()['events']['one']['processed_at'])

    def test_branch_and_opaque_reviews_preserve_prospective_history(self):
        call(self.rt, 'branch', 'branch', branch='b1', repository='fixture-repo', ref='fixture-ref', incarnation='new-1', root='fixture-engineering-root', basis='fixture accepted association')
        call(self.rt, 'review', 'reviews', review='r1', component='component-a', branch='b1', opaque_contract='owner-opaque-selector', context='new-context', history='owner-supplied-history-hash')
        call(self.rt, 'review', 'reviews', review='r2', component='component-a', branch='b1', opaque_contract='owner-opaque-selector', context='new-successor-context', history='new-history-hash', predecessor='r1')
        self.assertEqual(self.raw()['reviews']['r2']['predecessor'], 'r1')
        self.classify('build', 'branch')
        a = call(self.rt, 'reserve', 'branch', attempt='builder', event='build', phase='known', point='build', branch='b1', resources={'point:build': 'write', 'branch:b1': 'write'}, basis={'point:build': 0, 'branch:b1': 0})
        self.collect('builder', a['collector'], 'branch')
        with self.assertRaisesRegex(Held, 'builder handback'):
            call(self.rt, 'reconcile', 'branch', attempt='builder', collector=a['collector'], evidence='mere END is insufficient')
        call(self.rt, 'reconcile', 'branch', attempt='builder', collector=a['collector'], evidence='synthetic only',
             builder={'commit': 'a'*40, 'remote_readback': 'a'*40, 'pushed': True, 'signed': True, 'effects_reconciled': True})

    def test_crash_before_and_after_commit_and_lost_ack(self):
        self.ingest('one')
        for phase, expected in [('before-replace', False), ('after-replace', True)]:
            def die():
                def fault(p):
                    if p == phase:
                        os._exit(73)
                rt = Runtime(self.path, fault=fault)
                call(rt, 'ingest', event='crash-' + phase, payload={}, producer='fixture', source_basis='crash fixture')
            p = CTX.Process(target=die); p.start(); p.join(5)
            self.assertEqual(p.exitcode, 73)
            self.assertEqual('crash-' + phase in self.raw()['events'], expected)
        # After committed intake before reply, duplicate delivery finds the same
        # responsibility state, without creating a second event/effect.
        result = call(self.rt, 'ingest', event='crash-after-replace', payload={}, producer='fixture', source_basis='crash fixture')
        self.assertTrue(result['duplicate'])
        self.assertFalse(result['ack'])

    def test_launch_and_effect_interruption_are_held_without_replay(self):
        self.classify('one')
        a = self.reserve('one')
        start = call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='fixture', evidence='original collector fixture')
        call(self.rt, 'effect', effect='push1', attempt='a', collector=a['collector'], kind='push', intent='synthetic owned effect')
        marker = self.root / 'synthetic-effect.txt'
        def effect_then_die():
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(fd, b'effect happened\n'); os.fsync(fd); os.close(fd)
            os._exit(74)
        p = CTX.Process(target=effect_then_die); p.start(); p.join(5)
        self.assertEqual(p.exitcode, 74)
        self.assertEqual(call(self.rt, 'recover')['effects'][0]['state'], 'intent')
        with self.assertRaisesRegex(Held, 'no replay'):
            call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='fixture', evidence='blind replay')
        call(self.rt, 'collect', attempt='a', collector=a['collector'], launch_id=start['launch_id'], end=p.exitcode, result={'interrupted': True}, evidence='original parent joined actual fixture exit')
        with self.assertRaisesRegex(Held, 'uncertain effect'):
            call(self.rt, 'reconcile', attempt='a', collector=a['collector'], evidence='cannot waive effect')
        self.assertEqual(marker.read_bytes(), b'effect happened\n')
        call(self.rt, 'observe_effect', effect='push1', outcome='applied', evidence='original parent observed owned marker')
        call(self.rt, 'reconcile', attempt='a', collector=a['collector'], evidence='numeric failure retained and owned effect observed')

    def test_live_pool_change_empty_corrupt_and_no_counter_refund(self):
        self.classify('one')
        a = self.reserve('one')
        pool = _pool.Pool(self.routes)
        before = pool.status()['turn']
        pool.set([])
        self.assertEqual(pool.status()['turn'], before)
        with self.assertRaises(_pool.PoolError):
            call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='fixture', evidence='disabled pool')
        self.assertEqual(self.raw()['attempts']['a']['state'], 'reserved')
        pool.set(['.codex4'])
        self.assertEqual(pool.status()['turn'], before)
        self.routes.write_text('broken public control')
        with self.assertRaises(_pool.PoolError):
            call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='fixture', evidence='corrupt pool')
        self.assertTrue(self.raw()['attempts']['a']['fast_requested'])
        self.assertEqual(self.raw()['attempts']['a']['served_tier'], 'unobserved')

    def test_retention_uses_whole_processing_plus_day_and_all_holds(self):
        self.classify('one')
        now = [1000.0]
        rt = Runtime(self.path, clock=lambda: now[0])
        call(rt, 'resolve', event='one', need='outcome', evidence='fixture outcome')
        call(rt, 'finish', event='one')
        now[0] += 86400
        self.assertFalse(call(rt, 'eligibility', event='one')['eligible_metadata_only'])
        for hold in list(self.raw()['events']['one']['holds']):
            call(rt, 'hold', event='one', name=hold, enabled=False, evidence='synthetic holder release; no actual data deletion')
        self.assertTrue(call(rt, 'eligibility', event='one')['eligible_metadata_only'])
        call(rt, 'hold', event='one', name='late-source', enabled=True, evidence='late actual obligation simulated')
        self.assertFalse(call(rt, 'eligibility', event='one')['eligible_metadata_only'])

    def test_torn_journal_pressure_and_symlink_refuse_without_reset(self):
        with (self.path / 'budget.jsonl').open('ab') as f:
            f.write(b'{partial'); f.flush(); os.fsync(f.fileno())
        before = (self.path / 'budget.jsonl').read_bytes()
        with self.assertRaisesRegex(Held, 'budget damaged'):
            call(self.rt, 'status')
        self.assertEqual((self.path / 'budget.jsonl').read_bytes(), before)
        linked = self.root / 'linked'
        linked.symlink_to(self.path)
        with self.assertRaisesRegex(Held, 'real directories'):
            Runtime(linked)

    def test_budget_pressure_is_not_refunded(self):
        with self.rt.files.lock():
            with self.assertRaisesRegex(Held, 'budget exhausted'):
                self.rt.files.charge(bytes=LIMITS['bytes'])
        before = (self.path / 'budget.jsonl').read_bytes()
        with self.assertRaisesRegex(Held, 'no ACK'):
            self.ingest('new'); call(self.rt, 'ack', event='new')
        self.assertGreater(len((self.path / 'budget.jsonl').read_bytes()), len(before))

    def test_cli_actual_fixture_entrypoint_with_sql_disabled(self):
        self.classify('one')
        a = self.reserve('one')
        cli = Path(__file__).with_name('coordinator.py')
        bootstrap = "import builtins,runpy,sys; original=builtins.__import__; builtins.__import__=lambda n,*a,**k: (_ for _ in ()).throw(RuntimeError('SQL disabled')) if n.split('.')[0] in ('sqlite3','_sqlite3') else original(n,*a,**k); sys.path.insert(0,sys.argv[1]); sys.argv=sys.argv[2:]; runpy.run_path(sys.argv[0],run_name='__main__')"
        command = [sys.executable, '-B', '-c', bootstrap, str(cli.parent), str(cli), '--state', str(self.path), '--actor', 'work', 'run-fixture']
        r = subprocess.run(command, input=json.dumps({'attempt': 'a', 'collector': a['collector']}), text=True,
                           env={**os.environ, 'COORDINATOR_TOKEN': TOKENS['work']}, capture_output=True, timeout=10)
        (self.root / 'cli-result.json').write_text(json.dumps({'returncode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)['result']['end'], 0)
        self.assertEqual(self.raw()['attempts']['a']['result']['provider_acceptance'], False)

    def test_final_fast_wake_and_idempotent_receipt_edges(self):
        from coordinator import watch
        self.classify('one')
        a = self.reserve('one')
        (self.root / 'fast-tier').write_text('false\n')
        with self.assertRaisesRegex(Held, 'all-fast policy'):
            call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='fixture', evidence='disabled fast')
        self.assertEqual(self.raw()['attempts']['a']['state'], 'reserved')
        (self.root / 'fast-tier').write_text('true\n')
        self.collect('a', a['collector'])
        call(self.rt, 'integrate', attempt='a', collector=a['collector'], writes={'point:one': 1})
        ready = CTX.Queue()
        def receiver():
            rt = Runtime(self.path)
            original = rt.call
            def observed(*args, **kwargs):
                result = original(*args, **kwargs)
                if args[0] == 'inbox':
                    ready.put('bound-and-scanned')
                return result
            rt.call = observed
            result = watch(rt, 'qa', TOKENS['qa'], 3)
            ready.put(result)
        p = CTX.Process(target=receiver); p.start()
        self.assertEqual(ready.get(timeout=4), 'bound-and-scanned')
        retry(self.rt, 'send', packet='wake', event='one', recipient='qa', payload={'fixture': True})
        self.assertEqual(ready.get(timeout=4), 'bound-and-scanned')
        result = ready.get(timeout=4)
        p.join(4); self.assertEqual(p.exitcode, 0)
        self.assertEqual(result['packets'][0]['id'], 'wake')
        for stage in ('picked-up', 'processed', 'settled'):
            call(self.rt, 'receipt', 'qa', packet='wake', stage=stage, evidence='same receipt')
            self.assertTrue(call(self.rt, 'receipt', 'qa', packet='wake', stage=stage, evidence='same receipt')['duplicate'])
        # Missing wake listener loses hints; durable data still survives restart.
        call(self.rt, 'send', packet='dropped-hint', event='one', recipient='qa', payload={})
        self.assertEqual(call(Runtime(self.path), 'inbox', 'qa')['packets'][0]['id'], 'dropped-hint')

    def test_unqualified_provider_resume_and_release_explicitly_refused(self):
        self.classify('one')
        a = self.reserve('one')
        with self.assertRaisesRegex(Held, 'unqualified provider'):
            call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='codex', evidence='unqualified')
        for op in ('resume', 'release', 'migrate', 'delete'):
            with self.assertRaisesRegex(Held, 'unsupported operation'):
                call(self.rt, op)


if __name__ == '__main__':
    ARTIFACTS.mkdir(mode=0o700, parents=True, exist_ok=False)
    unittest.main(verbosity=2)
