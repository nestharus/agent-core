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
from unittest.mock import patch

_original_import = builtins.__import__
_sql_attempts = []


def no_sql(name, *args, **kwargs):
    if name.split('.')[0] in {'sqlite3', '_sqlite3'}:
        _sql_attempts.append(name)
        raise RuntimeError('SQL disabled by experiment')
    return _original_import(name, *args, **kwargs)


builtins.__import__ = no_sql
from runtime import Runtime, create, _pool, _fast
from storage import Held, Files, encode, LIMITS, HEADROOM, check_capacity

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
        # Fresh coordination-only test purpose. This is an observed floor,
        # never a reservation or a renewed allocation for previous attempts.
        check_capacity(ARTIFACTS, 8 * 1024**2, 2048)
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

    def public_control(self, helper, *args):
        # Standalone calls have their own positive 128KiB/16-entry allowance
        # inside this fixture's allocation; no Runtime callback is assumed.
        check_capacity(self.root, 131072, 16)
        command = [sys.executable, '-B', str(Path(__file__).parents[1] / 'direct-child' / helper),
                   '--routes', str(self.routes), *args]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        print('ORIGINAL_CONTROL_PROCESS', p.pid, flush=True)
        out, err = p.communicate(timeout=5)
        print('CONTROL_END', p.pid, p.returncode, flush=True)
        return p.returncode, out, err

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

    def test_c04_encoded_unicode_history_and_accountable_partial(self):
        self.ingest('unicode')
        source = self.raw()['events']['unicode']['source_hash']
        a = call(self.rt, 'reserve', attempt='low', event='unicode', phase='classifier', resources={}, basis={})
        start = call(self.rt, 'start', attempt='low', collector=a['collector'], substrate='fixture', evidence='synthetic LOW')
        call(self.rt, 'collect', attempt='low', collector=a['collector'], launch_id=start['launch_id'], end=0,
             result={'event_hash': source, 'classification': 'known'}, evidence='synthetic original collected')
        needs = ['n' + str(i) for i in range(16)]
        call(self.rt, 'classify', event='unicode', attempt='low', collector=a['collector'], classification='known', owner='work', needs=needs)
        call(self.rt, 'reconcile', attempt='low', collector=a['collector'], evidence='no effects')
        call(self.rt, 'ack', event='unicode')
        from runtime import MAX_TEXT, MAX_HISTORY
        evidence = '\U0001f600' * 42
        self.assertLessEqual(len(encode(evidence)), MAX_TEXT)
        with self.assertRaisesRegex(Held, 'encoded JSON bytes'):
            call(self.rt, 'resolve', event='unicode', need='n0', evidence='\U0001f600' * 43)
        self.assertEqual(self.raw()['events']['unicode']['resolutions'], {})
        for need in needs:
            call(self.rt, 'resolve', event='unicode', need=need, evidence=evidence)
        e = self.raw()['events']['unicode']
        self.assertEqual(list(e['resolutions'].values()), [evidence] * 16)
        self.assertEqual([h['evidence'] for h in e['resolution_history']], [evidence] * 16)
        # No replacement or silent history drop, including same-value repeats.
        for i in range(MAX_HISTORY):
            call(self.rt, 'hold', event='unicode', name='resource', enabled=True, evidence='observed-' + str(i))
        before = self.raw()['events']['unicode']['hold_evidence']
        with self.assertRaisesRegex(Held, 'hold history'):
            call(self.rt, 'hold', event='unicode', name='resource', enabled=False, evidence='additional assertion stays outside')
        result = call(self.rt, 'partial', kind='event', id='unicode', evidence='hold history full; actual pending release retained outside, resource hold remains')
        self.assertFalse(result['completed'])
        self.assertEqual(self.raw()['events']['unicode']['hold_evidence'], before)
        self.assertIn('resource', self.raw()['events']['unicode']['holds'])
        self.assertIsNone(self.raw()['events']['unicode']['processed_at'])
        with self.assertRaisesRegex(Held, 'outside actual'):
            call(self.rt, 'partial', 'qa', kind='event', id='unicode', evidence='foreign substitution')
        with self.assertRaisesRegex(Held, 'conflict'):
            call(self.rt, 'partial', kind='event', id='unicode', evidence='pretend complete')

    def test_c04_pressure_discovery_integration_return_and_partial_tail(self):
        self.classify('pressure')
        a = self.reserve('pressure')
        self.collect('a', a['collector'])
        call(self.rt, 'send', packet='pending', event='pressure', recipient='qa', payload={'actual': 'unreceived'})
        with self.rt.files.lock():
            self.rt.files.continuation = True
            latest = self.rt.files.charge()
            self.rt.files.charge(bytes=LIMITS['bytes'] - HEADROOM['bytes'] - latest['bytes'],
                                 reads=LIMITS['reads'] - HEADROOM['reads'] - latest['reads'])
            self.rt.files.continuation = False
        with self.assertRaisesRegex(Held, 'pressure'):
            self.ingest('unsupported-new-intake')
        recovered = call(self.rt, 'recover', 'qa')
        self.assertEqual(recovered['addressed'], ['pending'])
        self.assertEqual(call(self.rt, 'inbox', 'qa')['packets'][0]['id'], 'pending')
        call(self.rt, 'integrate', attempt='a', collector=a['collector'], writes={'point:pressure': {'value': '\U0001f600'}})
        call(self.rt, 'send', packet='necessary-return', event='pressure', recipient='branch', payload={'result': 'integrated'})
        for actor, packet in [('qa', 'pending'), ('branch', 'necessary-return')]:
            self.assertEqual(call(self.rt, 'inbox', actor)['packets'][0]['id'], packet)
            for stage in ('picked-up', 'processed', 'settled'):
                call(self.rt, 'receipt', actor, packet=packet, stage=stage, evidence='actual fixture ' + stage)
        call(self.rt, 'reconcile', attempt='a', collector=a['collector'], evidence='no effects')
        call(self.rt, 'resolve', event='pressure', need='outcome', evidence='necessary return accepted by synthetic recipient')
        call(self.rt, 'finish', event='pressure')
        self.assertTrue(self.raw()['events']['pressure']['finished'])
        self.assertNotIn('unsupported-new-intake', self.raw()['events'])
        # A failed/unknown original is reportable, never reconciled by partial.
        # Use a separate unclassified admitted event to distinguish an honest
        # partial from fabricated classification/ACK/whole processing.
        call(self.rt, 'partial', kind='event', id='pressure', evidence='external acceptance remains synthetic only')
        self.assertGreater(json.loads((self.path / 'budget.jsonl').read_text().splitlines()[-1])['bytes'],
                           LIMITS['bytes'] - HEADROOM['bytes'])

    def test_c04_partial_reservation_survives_encoded_material_pressure(self):
        self.ingest('one')
        self.ingest('two')
        from runtime import MAX_STATE
        current = self.raw()
        # Actual published cap is exercised by a candidate whose encoded body
        # fits the command cap but would consume reserved dispositions.
        # Many bounded records, no filler or direct state fabrication.
        admitted = ['one', 'two']
        for i in range(64):
            name = 'bounded-' + str(i)
            try:
                call(self.rt, 'ingest', event=name, payload='x' * 4092, producer='fixture', source_basis='finite encoded material')
            except Held as exc:
                self.assertIn('pressure', str(exc))
                break
            admitted.append(name)
        else:
            self.fail('finite admission must refuse before reserved dispositions are lost')
        self.assertNotIn(name, self.raw()['events'])
        # Partial all admitted records using recovered IDs, preserving sources,
        # ACK false, holds and all unfinished facts under the real cap.
        ids = [p['id'] for p in call(self.rt, 'recover')['partial_candidates'] if p['kind'] == 'event']
        self.assertCountEqual(ids, admitted)
        for event in ids:
            call(self.rt, 'readback', kind='event', id=event)
            call(self.rt, 'partial', kind='event', id=event, evidence='capacity pressure; original retained, classification and all downstream work unfinished')
        state = self.raw()
        self.assertLess(len(encode(state)), MAX_STATE)
        self.assertTrue(all(e.get('partial') and not e['ack'] and not e['finished'] and e['holds'] for e in state['events'].values()))

    def test_c04_cancelled_qa_allows_later_success_without_erasing_failure(self):
        self.classify('qa-cancel', 'qa')
        call(self.rt, 'package', package='same', event='qa-cancel', scope='same genuine package', basis='synthetic')
        def reserve(attempt, phase='qa-execute'):
            return call(self.rt, 'reserve', 'qa', attempt=attempt, event='qa-cancel', phase=phase, package='same', resources={}, basis={})
        cancelled = reserve('cancelled')
        before = _pool.Pool(self.routes).status()['turn']
        call(self.rt, 'cancel', 'qa', attempt='cancelled', collector=cancelled['collector'], evidence='definitely never created')
        self.assertEqual(_pool.Pool(self.routes).status()['turn'], before)
        with self.assertRaisesRegex(Held, 'collected and reconciled'):
            reserve('too-early', 'qa-consolidate')
        success = reserve('later')
        self.collect('later', success['collector'], 'qa')
        call(self.rt, 'reconcile', 'qa', attempt='later', collector=success['collector'], evidence='actual synthetic success, no effects')
        consolidation = reserve('consolidation', 'qa-consolidate')
        call(self.rt, 'cancel', 'qa', attempt='consolidation', collector=consolidation['collector'], evidence='test leaves consolidation definitely unstarted')
        failed = reserve('real-failure')
        self.collect('real-failure', failed['collector'], 'qa', end=7)
        call(self.rt, 'reconcile', 'qa', attempt='real-failure', collector=failed['collector'], evidence='actual failure retained')
        later = reserve('another-success')
        self.collect('another-success', later['collector'], 'qa')
        call(self.rt, 'reconcile', 'qa', attempt='another-success', collector=later['collector'], evidence='later success does not erase failure')
        result = reserve('failure-still-matters', 'qa-consolidate')
        self.assertTrue(result['collector'])
        self.assertIsNone(self.raw()['attempts']['cancelled']['end'])
        self.assertEqual(self.raw()['attempts']['real-failure']['end'], 7)

    def test_qa_failure_only_and_unknown_effect_consolidation(self):
        self.classify('qa-failure', 'qa')
        call(self.rt, 'package', package='failure-package', event='qa-failure', scope='failure report', basis='synthetic')
        def reserve(attempt, phase='qa-execute'):
            return call(self.rt, 'reserve', 'qa', attempt=attempt, event='qa-failure', phase=phase,
                        package='failure-package', resources={}, basis={})
        failed = reserve('failed-only')
        started = call(self.rt, 'start', 'qa', attempt='failed-only', collector=failed['collector'],
                       substrate='fixture', evidence='actual synthetic execution')
        call(self.rt, 'effect', 'qa', effect='unknown-effect', attempt='failed-only', collector=failed['collector'],
             kind='delivery', intent='synthetic effect')
        with self.assertRaisesRegex(Held, 'unknowns'):
            reserve('unknown-consolidation', 'qa-consolidate')
        call(self.rt, 'collect', 'qa', attempt='failed-only', collector=failed['collector'],
             launch_id=started['launch_id'], end=7, result={'failure': True}, evidence='numeric failure')
        with self.assertRaisesRegex(Held, 'uncertain effect'):
            call(self.rt, 'reconcile', 'qa', attempt='failed-only', collector=failed['collector'], evidence='not yet')
        with self.assertRaisesRegex(Held, 'unknowns'):
            reserve('unreconciled-consolidation', 'qa-consolidate')
        call(self.rt, 'observe_effect', 'qa', effect='unknown-effect', outcome='not-applied', evidence='actual observation')
        call(self.rt, 'reconcile', 'qa', attempt='failed-only', collector=failed['collector'], evidence='failure reconciled')
        result = reserve('failure-report', 'qa-consolidate')
        self.assertTrue(result['collector'])
        state = self.raw()
        self.assertEqual(state['attempts']['failed-only']['end'], 7)
        self.assertEqual(state['attempts']['failed-only']['reconciliation'], 'failure reconciled')
        self.assertEqual(state['effects']['unknown-effect']['outcome'], 'not-applied')

    def test_c04_revocation_at_creation_and_ambiguous_popen_remain_distinct(self):
        from coordinator import fixture
        self.classify('authority', 'qa')
        call(self.rt, 'package', package='authority', event='authority', scope='fixture', basis='synthetic')
        a = call(self.rt, 'reserve', 'qa', attempt='revoked', event='authority', phase='qa-execute', package='authority', resources={}, basis={})
        original = self.rt.call
        def intervene(op, *args, **kwargs):
            result = original(op, *args, **kwargs)
            if op == 'start':
                call(Runtime(self.path), 'revoke', target='qa', reason='revoked after start before creation')
            return result
        with patch.object(self.rt, 'call', side_effect=intervene), patch('coordinator.subprocess.Popen') as popen:
            with self.assertRaisesRegex(Held, 'revoked'):
                fixture(self.rt, 'qa', TOKENS['qa'], {'attempt': 'revoked', 'collector': a['collector']})
            popen.assert_not_called()
        state = self.raw()['attempts']['revoked']
        self.assertEqual(state['state'], 'not-started')
        self.assertIsNone(state['end'])
        self.assertFalse(state['reconciled'])
        with self.assertRaisesRegex(Held, 'revoked'):
            call(self.rt, 'cancel', 'qa', attempt='revoked', collector=a['collector'], evidence='no successor authority')
        with self.assertRaisesRegex(Held, 'original collector'):
            call(self.rt, 'cancel', attempt='revoked', collector=a['collector'], evidence='Work cannot borrow custody')
        self.classify('ambiguous')
        b = self.reserve('ambiguous', 'unknown')
        with patch('coordinator.subprocess.Popen', side_effect=OSError('unknown original creation outcome')):
            with self.assertRaisesRegex(_pool.PoolError, 'unknown original creation outcome'):
                fixture(self.rt, 'work', TOKENS['work'], {'attempt': 'unknown', 'collector': b['collector']})
        self.assertEqual(self.raw()['attempts']['unknown']['state'], 'launching')
        with self.assertRaisesRegex(Held, 'uncertain custody'):
            call(self.rt, 'cancel', attempt='unknown', collector=b['collector'], evidence='cannot infer never started')

    def test_c04_real_public_cli_paths_guard_actual_fixture_creation(self):
        from coordinator import fixture
        self.assertEqual(self.public_control('execution_pool.py', 'set', '.codex4')[0], 0)
        self.assertEqual(self.public_control('fast_tier.py', 'get')[:2], (0, 'true\n'))
        self.classify('public')
        a = self.reserve('public')
        original = subprocess.Popen
        control_ends = []
        def create_child(*args, **kwargs):
            # Use the real CLI with its --routes selector, no POLICY patch.
            with patch('subprocess.Popen', original):
                control_ends.append(self.public_control('fast_tier.py', 'set', 'off')[0])
            self.assertEqual((self.root / 'fast-tier').read_text(), 'true\n')
            child = original(*args, **kwargs)
            print('ORIGINAL_FIXED_WORKER', child.pid, flush=True)
            return child
        with patch('coordinator.subprocess.Popen', side_effect=create_child):
            result = fixture(self.rt, 'work', TOKENS['work'], {'attempt': 'a', 'collector': a['collector']})
        self.assertEqual(control_ends, [2])
        self.assertEqual(result['end'], 0)
        self.assertEqual(self.public_control('fast_tier.py', 'set', 'off')[:2], (0, 'false\n'))
        self.assertEqual(self.public_control('fast_tier.py', 'set', 'on')[:2], (0, 'true\n'))
        self.assertEqual(self.raw()['attempts']['a']['pool']['profile'], '.codex4')

    def test_c03_lost_reserve_start_and_collection_replies_recover_original_operands(self):
        self.classify('lost')
        def lose_reply(op, **fields):
            def child():
                rt = Runtime(self.path, fault=lambda phase: os._exit(73) if phase == 'after-commit' else None)
                call(rt, op, **fields)
            original = CTX.Process(target=child)
            original.start(); original.join(5)
            self.assertEqual(original.exitcode, 73)
        lose_reply('reserve', attempt='lost', event='lost', phase='known', point='lost',
                   resources={'point:lost': 'write'}, basis={'point:lost': 0})
        recovered = call(self.rt, 'recover')['attempts'][0]
        self.assertEqual(recovered['id'], 'lost')
        collector = recovered['collector']
        with self.assertRaisesRegex(Held, 'original owner'):
            call(self.rt, 'readback', 'qa', kind='attempt', id='lost')
        lose_reply('start', attempt='lost', collector=collector, substrate='fixture', evidence='original fixture')
        saved = call(self.rt, 'readback', kind='attempt', id='lost')['value']
        self.assertEqual(saved['state'], 'launching')
        with self.assertRaisesRegex(Held, 'no replay'):
            call(self.rt, 'start', attempt='lost', collector=collector, substrate='fixture', evidence='original fixture')
        with self.assertRaisesRegex(Held, 'definitely unstarted'):
            call(self.rt, 'cancel', attempt='lost', collector=collector, evidence='cannot assume absent process')
        # This child records an independently supplied synthetic numeric END;
        # fault exit 73 is metadata-process custody, not a provider's END.
        fields = dict(attempt='lost', collector=collector, launch_id=saved['launch_id'], end=7,
                      result={'synthetic_original_outcome': 'failed'}, evidence='synthetic original collector END')
        lose_reply('collect', **fields)
        current = call(self.rt, 'readback', kind='attempt', id='lost')['value']
        self.assertEqual((current['end'], current['collection_evidence']), (7, fields['evidence']))
        self.assertTrue(call(self.rt, 'collect', **fields)['duplicate'])
        with self.assertRaisesRegex(Held, 'conflict'):
            call(self.rt, 'collect', **{**fields, 'end': 0})

    def test_c03_unstarted_empty_pool_disposition_releases_discovery_without_refund(self):
        self.classify('first', kind='new'); self.classify('second', kind='new')
        a = call(self.rt, 'reserve', attempt='first', event='first', phase='discovery', resources={}, basis={})
        pool = _pool.Pool(self.routes)
        before = pool.status()['turn']
        pool.set([])
        with self.assertRaises(_pool.PoolError):
            call(self.rt, 'start', attempt='first', collector=a['collector'], substrate='fixture', evidence='removed')
        with self.assertRaisesRegex(Held, 'original collector'):
            call(self.rt, 'cancel', 'qa', attempt='first', collector=a['collector'], evidence='foreign')
        fields = dict(attempt='first', collector=a['collector'], evidence='original owner: definitely never started')
        self.assertFalse(call(self.rt, 'cancel', **fields)['turn_refunded'])
        self.assertTrue(call(self.rt, 'cancel', **fields)['duplicate'])
        self.assertEqual(pool.status()['turn'], before)
        pool.set(['.codex4'])  # Explicit fixture control action, no automatic re-enable.
        b = call(self.rt, 'reserve', attempt='second', event='second', phase='discovery', resources={}, basis={})
        self.assertTrue(b['collector'])
        self.assertEqual(pool.status()['turn'], before + 1)
        self.assertIsNone(call(self.rt, 'readback', kind='attempt', id='first')['value']['end'])

    def test_c03_fast_and_pool_changes_between_start_and_actual_creation_refuse(self):
        from coordinator import fixture
        self.classify('one')
        a = self.reserve('one')
        original = self.rt.call
        def change_fast(*args, **kw):
            result = original(*args, **kw)
            if args[0] == 'start':
                with patch.object(_fast, 'POLICY', self.root / 'fast-tier'):
                    _fast.set_policy('false')
            return result
        with patch.object(self.rt, 'call', side_effect=change_fast), patch('coordinator.subprocess.Popen') as popen:
            with self.assertRaisesRegex(Held, 'all-fast policy'):
                fixture(self.rt, 'work', TOKENS['work'], {'attempt': 'a', 'collector': a['collector']})
            popen.assert_not_called()
        self.assertEqual(call(self.rt, 'readback', kind='attempt', id='a')['value']['state'], 'not-started')
        call(self.rt, 'cancel', attempt='a', collector=a['collector'], evidence='original observed control refusal before creation')
        # A separate original reservation proves the equivalent pool interval.
        (self.root / 'fast-tier').write_text('true\n')
        self.classify('two')
        b = self.reserve('two', attempt='b')
        def change_pool(*args, **kw):
            result = original(*args, **kw)
            if args[0] == 'start':
                _pool.Pool(self.routes).set([])
            return result
        with patch.object(self.rt, 'call', side_effect=change_pool), patch('coordinator.subprocess.Popen') as popen:
            with self.assertRaises(_pool.PoolError):
                fixture(self.rt, 'work', TOKENS['work'], {'attempt': 'b', 'collector': b['collector']})
            popen.assert_not_called()

    def test_c03_supported_fast_setter_serializes_with_actual_fixture_creation(self):
        from coordinator import fixture
        self.classify('one'); a = self.reserve('one')
        real_popen = subprocess.Popen
        result = CTX.Queue()
        def setter():
            with patch.object(_fast, 'POLICY', self.root / 'fast-tier'):
                try:
                    _fast.set_policy('false')
                except ValueError as exc:
                    result.put(str(exc))
                else:
                    result.put('unexpectedly changed')
        def at_creation(*args, **kwargs):
            p = CTX.Process(target=setter); p.start(); p.join(4)
            self.assertEqual(p.exitcode, 0)
            self.assertIn('control busy', result.get(timeout=2))
            self.assertEqual((self.root / 'fast-tier').read_text(), 'true\n')
            return real_popen(*args, **kwargs)
        with patch('coordinator.subprocess.Popen', side_effect=at_creation):
            self.assertEqual(fixture(self.rt, 'work', TOKENS['work'], {'attempt': 'a', 'collector': a['collector']})['end'], 0)
        with patch.object(_fast, 'POLICY', self.root / 'fast-tier'):
            _fast.set_policy('false')  # Guard released after actual creation.
        self.assertEqual((self.root / 'fast-tier').read_text(), 'false\n')

    def test_c03_four_simultaneous_receivers_get_only_addressed_work(self):
        from coordinator import watch
        self.classify('routing')
        ready = CTX.Queue()
        children = []
        for actor in TOKENS:
            output = CTX.Queue()
            def receive(actor=actor, output=output):
                rt = Runtime(self.path)
                original = rt.call
                scanned = False
                def announced(*args, **kw):
                    nonlocal scanned
                    value = original(*args, **kw)
                    if not scanned:
                        ready.put(actor); scanned = True
                    return value
                rt.call = announced
                output.put(watch(rt, actor, TOKENS[actor], 5))
            p = CTX.Process(target=receive); p.start()
            children.append((actor, p, output))
        self.assertEqual({ready.get(timeout=4) for _ in TOKENS}, set(TOKENS))
        for actor, _, _ in children:
            retry(self.rt, 'send', packet='to-' + actor, event='routing', recipient=actor, payload={'for': actor})
        for actor, p, output in children:
            value = output.get(timeout=6)
            p.join(5); self.assertEqual(p.exitcode, 0)
            self.assertEqual([x['id'] for x in value['packets']], ['to-' + actor])

    def test_c03_interrupted_receiver_rebinds_without_stale_cleanup(self):
        from coordinator import watch
        def die():
            rt = Runtime(self.path)
            original = rt.call
            def scanned(*args, **kwargs):
                original(*args, **kwargs)
                os._exit(75)
            rt.call = scanned
            watch(rt, 'qa', TOKENS['qa'], 2)
        p = CTX.Process(target=die); p.start(); p.join(4)
        self.assertEqual(p.exitcode, 75)
        self.assertEqual(watch(self.rt, 'qa', TOKENS['qa'], 0)['packets'], [])

    def test_c03_cross_event_and_transitive_corrections_restart_whole_processing_clock(self):
        self.classify('old'); self.classify('new'); self.classify('later')
        now = [1000.0]
        rt = Runtime(self.path, clock=lambda: now[0])
        def settle(packet):
            for stage in ('picked-up', 'processed', 'settled'):
                call(rt, 'receipt', 'qa', packet=packet, stage=stage, evidence='synthetic actual recipient ' + stage)
        call(rt, 'send', packet='p1', event='old', recipient='qa', payload={'v': 1})
        settle('p1')
        call(rt, 'resolve', event='old', need='outcome', evidence='first completed outcome')
        call(rt, 'finish', event='old')
        for name in self.raw()['events']['old']['holds']:
            call(rt, 'hold', event='old', name=name, enabled=False, evidence='synthetic holder only')
        now[0] += 86400
        self.assertTrue(call(rt, 'eligibility', event='old')['eligible_metadata_only'])
        call(rt, 'send', packet='p2', event='new', recipient='qa', payload={'v': 2}, correction_of='p1')
        self.assertFalse(call(rt, 'eligibility', event='old')['eligible_metadata_only'])
        with self.assertRaisesRegex(Held, 'downstream unsettled'):
            call(rt, 'finish', event='old')
        settle('p2')
        call(rt, 'finish', event='old')
        self.assertEqual(call(rt, 'readback', kind='event', id='old')['value']['processed_at'], now[0])
        now[0] += 86400
        self.assertTrue(call(rt, 'eligibility', event='old')['eligible_metadata_only'])
        call(rt, 'send', packet='p3', event='later', recipient='qa', payload={'v': 3}, correction_of='p2')
        self.assertFalse(call(rt, 'eligibility', event='old')['eligible_metadata_only'])
        self.assertFalse(call(rt, 'eligibility', event='old')['deletion_authorized'])
        settle('p3')
        call(rt, 'finish', event='old')
        self.assertFalse(call(rt, 'eligibility', event='old')['eligible_metadata_only'])

    def test_c03_review_phase_owner_and_branch_associations_are_required(self):
        call(self.rt, 'branch', 'branch', branch='b', repository='repo', ref='ref', incarnation='one', root='root', basis='synthetic')
        with self.assertRaisesRegex(Held, 'already bound'):
            call(self.rt, 'branch', 'branch', branch='alias', repository='repo', ref='ref', incarnation='one', root='root', basis='synthetic')
        call(self.rt, 'review', 'reviews', review='r', component='one', branch='b', opaque_contract='opaque', context='fresh', history='supplied')
        with self.assertRaisesRegex(Held, 'association conflict'):
            call(self.rt, 'review', 'reviews', review='wrong', component='two', branch='b', opaque_contract='opaque', context='new', history='supplied', predecessor='r')
        self.classify('work'); self.classify('review', 'reviews'); self.classify('build', 'branch')
        with self.assertRaisesRegex(Held, 'review history'):
            self.reserve('work', review='r')
        self.assertEqual(call(self.rt, 'readback', 'reviews', kind='review', id='r')['value']['calls'], [])
        builder = call(self.rt, 'reserve', 'branch', attempt='builder', event='build', phase='known', point='build', branch='b',
                       resources={'point:build': 'write', 'branch:b': 'write'}, basis={'point:build': 0, 'branch:b': 0})
        fields = dict(attempt='review', event='review', phase='review', review='r', resources={'review:r': 'write', 'branch:b': 'read'},
                      basis={'review:r': 0, 'branch:b': 0})
        with self.assertRaisesRegex(Held, 'resource conflict'):
            call(self.rt, 'reserve', 'reviews', **fields)
        call(self.rt, 'cancel', 'branch', attempt='builder', collector=builder['collector'], evidence='synthetic never started')
        review = call(self.rt, 'reserve', 'reviews', **fields)
        self.assertTrue(review['collector'])
        self.assertEqual(call(self.rt, 'readback', 'reviews', kind='review', id='r')['value']['calls'], ['review'])
        self.assertNotIn('collector', call(self.rt, 'recover')['attempts'][0])

    def test_c03_pressure_keeps_owner_readback_and_unstarted_disposition(self):
        self.classify('one'); a = self.reserve('one')
        self.ingest('pending')
        low = call(self.rt, 'reserve', attempt='pending-low', event='pending', phase='classifier', resources={}, basis={})
        started = call(self.rt, 'start', attempt='pending-low', collector=low['collector'], substrate='fixture', evidence='synthetic LOW')
        call(self.rt, 'collect', attempt='pending-low', collector=low['collector'], launch_id=started['launch_id'], end=0,
             result={'event_hash': self.raw()['events']['pending']['source_hash'], 'classification': 'unresolved'}, evidence='synthetic collected LOW')
        generation = self.raw()['generation']
        call(self.rt, 'status'); call(self.rt, 'inbox')
        self.assertEqual(self.raw()['generation'], generation)
        raw = (self.path / 'budget.jsonl').read_bytes()
        previous = json.loads(raw.splitlines()[-1])
        with self.rt.files.lock():
            self.rt.files.charge(bytes=LIMITS['bytes'] - HEADROOM['bytes'] - previous['bytes'] - 1024,
                                 reads=LIMITS['reads'] - HEADROOM['reads'] - previous['reads'] - len(raw))
        with self.assertRaisesRegex(Held, 'work pressure hold'):
            call(self.rt, 'status')
        recovered = call(self.rt, 'recover')['attempts'][0]
        self.assertEqual(recovered['collector'], a['collector'])
        self.assertEqual(call(self.rt, 'readback', kind='attempt', id='a')['value']['state'], 'reserved')
        call(self.rt, 'cancel', attempt='a', collector=a['collector'], evidence='pressure: definitely unstarted')
        current = call(self.rt, 'readback', kind='attempt', id='a')['value']
        self.assertEqual(current['state'], 'cancelled')
        call(self.rt, 'classify', event='pending', attempt='pending-low', collector=low['collector'],
             classification='unresolved', owner='work', needs=['outcome'])
        call(self.rt, 'reconcile', attempt='pending-low', collector=low['collector'], evidence='synthetic no effects')
        call(self.rt, 'ack', event='pending')
        call(self.rt, 'resolve', event='pending', need='outcome', evidence='explicit held unresolved outcome disposition')
        call(self.rt, 'finish', event='pending')
        last = json.loads((self.path / 'budget.jsonl').read_bytes().splitlines()[-1])
        self.assertTrue(all(last[k] >= previous[k] for k in LIMITS))
        with self.assertRaisesRegex(Held, 'work pressure hold'):
            self.ingest('no-new-grant')

    def test_c03_evidence_is_attributable_immutable_and_readable_after_lost_replies(self):
        self.classify('one'); a = self.reserve('one')
        started = call(self.rt, 'start', attempt='a', collector=a['collector'], substrate='fixture', evidence='original')
        call(self.rt, 'effect', effect='e', attempt='a', collector=a['collector'], kind='delivery', intent='synthetic intent')
        observation = dict(effect='e', outcome='not-applied', evidence='original holder inspected actual fixture')
        call(self.rt, 'observe_effect', **observation)
        self.assertTrue(call(self.rt, 'observe_effect', **observation)['duplicate'])
        with self.assertRaisesRegex(Held, 'conflict'):
            call(self.rt, 'observe_effect', **{**observation, 'outcome': 'applied'})
        call(self.rt, 'collect', attempt='a', collector=a['collector'], launch_id=started['launch_id'], end=3,
             result={'failed': True}, evidence='original synthetic END')
        fields = dict(attempt='a', collector=a['collector'], evidence='original failure disposition, no acceptance')
        call(self.rt, 'reconcile', **fields)
        self.assertTrue(call(self.rt, 'reconcile', **fields)['duplicate'])
        with self.assertRaisesRegex(Held, 'conflict'):
            call(self.rt, 'reconcile', **{**fields, 'evidence': 'replacement success'})
        resolution = dict(event='one', need='outcome', evidence='first original outcome')
        call(self.rt, 'resolve', **resolution)
        self.assertTrue(call(self.rt, 'resolve', **resolution)['duplicate'])
        with self.assertRaisesRegex(Held, 'conflict'):
            call(self.rt, 'resolve', **{**resolution, 'evidence': 'overwrite'})
        event = call(self.rt, 'readback', kind='event', id='one')['value']
        self.assertEqual(event['resolution_history'][0]['actor'], 'work')
        self.assertEqual(event['resolutions']['outcome'], resolution['evidence'])
        attempt = call(self.rt, 'readback', kind='attempt', id='a')['value']
        self.assertEqual(attempt['end'], 3)
        self.assertEqual(attempt['reconciliation'], fields['evidence'])
        self.assertEqual(call(self.rt, 'readback', kind='effect', id='e')['value']['observation'], observation['evidence'])

    def test_c03_imminent_allocation_is_subtracted_from_capacity_before_growth(self):
        from types import SimpleNamespace
        on_os = self.path.stat().st_dev == Path('/').stat().st_dev
        floor, inodes = (16 * 1024**3, 100000) if on_os else (1024**3, 2000)
        def capacity(extra_bytes, extra_inodes):
            return SimpleNamespace(f_bavail=(floor + extra_bytes) // 4096, f_frsize=4096, f_favail=inodes + extra_inodes)
        with patch('storage.os.statvfs', return_value=capacity(65536, 2)):
            check_capacity(self.path, 4096, 1)
        for extra_bytes, extra_inodes in [(0, 2), (65536, 0)]:
            with patch('storage.os.statvfs', return_value=capacity(extra_bytes, extra_inodes)):
                with self.assertRaisesRegex(Held, 'capacity floor'):
                    check_capacity(self.path, 4096, 1)
        before = (self.path / 'state.json').read_bytes()
        with patch('storage.os.statvfs', return_value=capacity(4096, 2)):
            with self.assertRaisesRegex(Held, 'capacity floor'):
                self.ingest('cannot-fit')
        self.assertEqual((self.path / 'state.json').read_bytes(), before)


if __name__ == '__main__':
    check_capacity(ARTIFACTS.parent, 8 * 1024**2, 2048)
    ARTIFACTS.mkdir(mode=0o700, parents=True, exist_ok=False)
    unittest.main(verbosity=2)
