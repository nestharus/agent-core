"""R1/R2/R3 boundary conditions; real journals, CLI and stock Git; transport MOCK."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
import test_stack_controller as t
import test_adapters as a
from adapter_runtime import check_once
from adapter_support import ProcessCapture,git_environment
from feed_adapter import DEFERRAL_V2
from git_probe_adapter import GitProbe
C=t.c
R=Path(os.environ['BOUNDARY_TEST_RUNTIME'])
ROOT=Path(__file__).resolve().parents[1]
class Owned(unittest.TestCase):
    def setUp(self):
        self.area=R/self._testMethodName;self.area.mkdir(mode=0o700)
        self.journal=self.area/'journal';self.lock=self.area/'lock'
    def check(self,s,tick='one',**kw):
        feed={'schema':'branch-adapter-result/v1','snapshot':s,
              'frontiers':['outside-explicit-pr-scope-UNKNOWN']}
        return check_once(C,feed,journal_path=self.journal,lock_path=self.lock,
                          owner=C.RECIPIENT,check_id=tick,**kw)
    def moved(self,s):
        n=copy.deepcopy(s);t.at(n,'A')['version']=t.v(80)
        return n
    def cli(self,s,tick):
        inp=self.area/('input-'+str(len(list(self.area.iterdir()))));inp.mkdir()
        snapshot=inp/'snapshot.json';snapshot.write_text(json.dumps(s))
        binding=inp/'binding.json';binding.write_text(json.dumps({
            'schema':'stack-startup/v1','source_sha256':hashlib.sha256(Path(C.__file__).read_bytes()).hexdigest(),
            'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            'feed_binding':s['feed']['binding'],'feed_schema':s['feed']['schema'],'owner':C.RECIPIENT}))
        state=self.area/'state';state.mkdir(exist_ok=True)
        cap=ProcessCapture(self.area/('capture-'+str(len(list(self.area.iterdir())))))
        argv=['/usr/bin/bwrap','--die-with-parent','--unshare-pid','--unshare-net',
              '--ro-bind','/','/','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
              '--bind',str(state),str(state),'--','/usr/bin/python3','-I','-S','-B',str(C.__file__),
              'once','--snapshot',str(snapshot),'--binding',str(binding),'--journal',str(state/'journal'),
              '--lock',str(state/'lock'),'--check-id',tick]
        result=cap.run(argv,env=git_environment(self.area),cwd=self.area)
        # Parse only successful controlled metadata; rejection requires only native end.
        return result,json.loads(result['stdout']) if result['exit_code'] in (0,3) else None

class AtomicAcceptance(Owned):
    def test_R1_adapter_rejection_preserves_all_bytes_original_replay(self):
        s=t.healthy(t.snapshot('linear'));first=self.check(s)
        before=self.journal.read_bytes();(self.area/'before.bin').write_bytes(before)
        with self.assertRaises(C.Invalid):self.check(self.moved(s))
        self.assertEqual(self.journal.read_bytes(),before)
        replay=self.check(s)
        self.assertEqual(replay['plan'],first['plan']);self.assertTrue(replay['replayed'])
        self.assertEqual(self.journal.read_bytes(),before)
    def test_R1_CLI_rejection_original_retry_and_historical_replay(self):
        s=t.healthy(t.snapshot('linear'));end,first=self.cli(s,'one');self.assertEqual(end['exit_code'],0)
        path=self.area/'state/journal';before=path.read_bytes();(self.area/'before.bin').write_bytes(before)
        end,_=self.cli(self.moved(s),'one');self.assertEqual(end['exit_code'],2)
        self.assertEqual(path.read_bytes(),before)
        end,replay=self.cli(s,'one');self.assertEqual(end['exit_code'],0)
        self.assertEqual(replay['plan'],first['plan']);self.assertEqual(path.read_bytes(),before)
        end,moved=self.cli(self.moved(s),'two');self.assertEqual(end['exit_code'],3)
        self.assertEqual(moved['plan']['stale'],['A','B'])
        later=path.read_bytes();end,replay=self.cli(s,'one')
        self.assertEqual(end['exit_code'],0);self.assertEqual(replay['plan'],first['plan'])
        self.assertEqual(path.read_bytes(),later)
    def test_R1_adapter_later_observation_replay_never_rolls_back_or_sends(self):
        s=t.healthy(t.snapshot('linear'));first=self.check(s)
        later=self.check(self.moved(s),'two');self.assertEqual(later['plan']['stale'],['A','B'])
        before=self.journal.read_bytes();calls=[]
        replay=self.check(s,sender=lambda alert:calls.append(alert))
        self.assertEqual(replay['plan'],first['plan']);self.assertEqual(calls,[])
        self.assertEqual(self.journal.read_bytes(),before)
    def test_R1_ambiguity_durable_before_sender_no_replay_distinct_repeat(self):
        s=t.snapshot('linear');s['groups']=[]
        s['probes']=[t.probe(s,['A','B'],kind='pair',status='CONFLICT')]
        calls=[]
        def mock(alert):
            persisted=json.loads(self.journal.read_bytes())
            row=persisted['checks'][alert['check_id']]
            self.assertEqual(row['state'],'AMBIGUOUS')
            self.assertIn('observation',persisted);self.assertIn('input_digest',row)
            calls.append(alert['check_id']);raise TimeoutError('MOCK')
        first=self.check(s,sender=mock);self.assertEqual(first['delivery']['state'],'AMBIGUOUS')
        before=self.journal.read_bytes()
        with self.assertRaises(C.Invalid):self.check(self.moved(s),sender=mock)
        self.assertEqual(self.journal.read_bytes(),before)
        self.assertEqual(self.check(s,sender=mock)['delivery']['state'],'AMBIGUOUS')
        self.assertEqual(self.journal.read_bytes(),before)
        self.assertEqual(self.check(s,'two',sender=mock)['delivery']['state'],'AMBIGUOUS')
        self.assertEqual(calls,['one','two'])
    def test_R1_planned_historical_replay_is_receipt_only(self):
        s=t.snapshot('linear');s['groups']=[]
        s['violations']=[{'unit':'A','kind':'repair','obligation':'current/repair','evidence_ref':'current'}]
        first=self.check(s);self.assertEqual(first['delivery']['state'],'PLANNED')
        self.check(self.moved(s),'two');before=self.journal.read_bytes();calls=[]
        replay=self.check(s,sender=lambda alert:calls.append(alert))
        self.assertEqual(replay['delivery'],first['delivery']);self.assertEqual(calls,[])
        self.assertEqual(self.journal.read_bytes(),before)
    def test_R1_save_failure_keeps_journal_pending_and_memory(self):
        s=t.healthy(t.snapshot('linear'));self.check(s)
        pending=self.journal.with_name('journal.pending');pending.write_bytes(b'held pending')
        before=self.journal.read_bytes()
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);memory=copy.deepcopy(j.data)
            with self.assertRaises(FileExistsError):j.accept(self.moved(s),'two')
            self.assertEqual(j.data,memory)
        self.assertEqual(self.journal.read_bytes(),before);self.assertEqual(pending.read_bytes(),b'held pending')
    def test_R1_legacy_receipt_unbound_input_not_adopted(self):
        s=t.healthy(t.snapshot('linear'))
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);p=C.plan(s)
            prior=j.prepare('one',[],p['plan_id']);before=self.journal.read_bytes()
            self.assertEqual(j.receipt('one'),prior)
            with self.assertRaises(C.Invalid):j.accept(s,'one')
            self.assertEqual(self.journal.read_bytes(),before)

class RuntimeFrontiers(Owned):
    def v1(self):
        s=t.healthy(t.snapshot('linear'))
        projection={'schema':'rfq.branch-deferral-eligibility-projection/1','mode':'ON_ENCOUNTER',
                    'complete_inventory_required':False,'canonical_source':'opaque/not-read',
                    'entries':[{'repository':s['repo'],'pull_request':20,
                                'classification':'DEFERRED_TO_NAMED_CAMPAIGN',
                                'remaining_real_failures_still_alert':True}]}
        return s,projection
    def test_R2_unknown_trigger_is_UNKNOWN(self):
        s,p=self.v1();r=self.check(s,deferral_projection=p)
        self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['alerts'],[])
        self.assertIn({'pr':20,'reason':'reactivation-trigger-UNKNOWN'},r['frontiers'])
        self.assertEqual(r['delivery']['state'],'SILENT')
    def test_R2_boolean_trigger_and_outside_scope_remain_bounded_healthy(self):
        s,p=self.v1();r=self.check(s,deferral_projection=p,triggers={20:True})
        self.assertEqual(r['status'],'HEALTHY_WITHIN_EXPLICIT_SCOPE')
        self.assertEqual(r['frontiers'],['outside-explicit-pr-scope-UNKNOWN'])
    def test_R2_unknown_preserves_known_violations_notices(self):
        s,p=self.v1();s['violations']=[{'unit':'A','kind':'repair','obligation':'repair/current','evidence_ref':'current'}]
        calls=[]
        def mock(alert):calls.append(alert['disposition']);raise TimeoutError('MOCK')
        r=self.check(s,deferral_projection=p,sender=mock)
        self.assertEqual(r['status'],'UNKNOWN');self.assertTrue(r['known_violations'])
        self.assertEqual([n['disposition'] for n in r['alerts']],['repair']);self.assertEqual(calls,['repair'])
    def test_R2_decoder_gap_with_snapshot_is_UNKNOWN(self):
        s=t.healthy(t.snapshot('linear'))
        feed={'schema':'branch-adapter-result/v1','snapshot':s,'frontiers':[{'pr':20,'reason':'decoder-UNKNOWN'}]}
        r=check_once(C,feed,journal_path=self.journal,lock_path=self.lock,owner=C.RECIPIENT,check_id='one')
        self.assertEqual(r['status'],'UNKNOWN')
    def test_R2_V2_false_decision_preserves_known_active_obligation(self):
        p=json.loads((ROOT/'fixtures/work-deferral-projection-v2.json').read_bytes())
        auth=json.loads((ROOT/'fixtures/work-trigger-decision.json').read_bytes())
        s=t.snapshot('linear');s['groups']=[];s['repo']='lama-ai-RFQ/RFQautomation'
        u=t.at(s,'B');u['pr']=1230;u['ref']='refs/heads/feat/integrated-auth-cloud-full'
        s['violations']=[{'unit':'B','kind':k,'obligation':'current/'+k,'evidence_ref':'current'}
                         for k in ('whole_landing','repair')]
        r=self.check(s,deferral_projection=p,deferral_capability=DEFERRAL_V2,**auth)
        self.assertEqual(r['status'],'VIOLATION');self.assertEqual([n['disposition'] for n in r['alerts']],['repair'])

class ObjectFormat(Owned):
    def test_R3_all_known_Git_OID_positions_rejected_before_native_or_getter(self):
        positions=['main','main_head','main_tree','main_parent','head','tree','parent','base']
        for pos in positions:
            with self.subTest(position=pos):
                s=a.snap(('A',));main=copy.deepcopy(a.V['Main']);u=s['units'][0]
                if pos=='main':s['main']='a'*64;main['head']='a'*64
                elif pos=='main_head':main['head']='a'*64
                elif pos=='main_tree':main['tree']='a'*64
                elif pos=='main_parent':main['parents']=['a'*64]
                elif pos=='base':u['physical_base']['head']='a'*64
                elif pos=='parent':u['version']['parents']=['a'*64]
                else:u['version'][pos]='a'*64
                p=GitProbe(C,self.area/pos);calls=[]
                r=p.probe(s,['A'],kind='ordered',main_version=main,scope=a.FIX['scope'],
                          source_getter=lambda:calls.append('forbidden'))
                self.assertEqual(calls,[]);self.assertEqual(r['native_ends'],[])
                self.assertFalse(p.repo.exists());self.assertEqual(r['status'],'UNKNOWN')
                self.assertIsNone(r['probe'])
                self.assertEqual(r['reason'],'unsupported-Git-object-format-before-init-or-getter')
    def test_R3_core_64_metadata_still_valid_no_digest_confusion_SHA1_clean(self):
        s=a.snap(('A',));s['units'][0]['version']['content']='f'*64
        s['units'][0]['version']['resolution']='e'*64
        C.Graph(s);p=GitProbe(C,self.area/'native')
        r=p.probe(s,['A'],kind='ordered',main_version=a.V['Main'],scope=a.FIX['scope'],
                  source_getter=lambda:a.FIX['records'])
        self.assertEqual(r['status'],'CLEAN');self.assertFalse(r['probe']['semantic'])
        future=copy.deepcopy(s);future['main']='a'*64;future['units'][0]['version']['head']='b'*64
        future['units'][0]['version']['tree']='c'*64;future['units'][0]['version']['parents']=['d'*64]
        C.Graph(future)

# R1 post-replacement controls. Real syscalls and files; only the fault boundary is injected.
import errno
import stat
from unittest.mock import patch
from contextlib import ExitStack

class JournalFault:
    def __init__(self, kind, after=1):
        self.kind=kind;self.after=after;self.replacements=0
    def __enter__(self):
        self.stack=ExitStack();replace,op,fs=C.os.replace,C.os.open,C.os.fsync
        def replace_fault(*a,**kw):
            if self.kind=='replace' and self.replacements+1==self.after:
                raise OSError(errno.EIO,'controlled replacement fault')
            r=replace(*a,**kw);self.replacements+=1;return r
        def open_fault(path,flags,*a,**kw):
            if flags & os.O_DIRECTORY and self.kind=='directory-open' and self.replacements==self.after:
                raise OSError(errno.EIO,'controlled directory open fault')
            return op(path,flags,*a,**kw)
        def fsync_fault(fd):
            directory=stat.S_ISDIR(os.fstat(fd).st_mode)
            if ((directory and self.kind=='directory-fsync' and self.replacements==self.after)
                or (not directory and self.kind=='file-fsync' and self.replacements+1==self.after)):
                raise OSError(errno.EIO,'controlled sync fault')
            return fs(fd)
        for name,fn in [('replace',replace_fault),('open',open_fault),('fsync',fsync_fault)]:
            self.stack.enter_context(patch.object(C.os,name,fn))
        return self
    def __exit__(self,*exc):return self.stack.__exit__(*exc)

class PostReplacementDurability(Owned):
    def seed(self):
        s=t.healthy(t.snapshot());self.check(s,'seed');return s
    def violating(self):return t.snapshot()
    def postreplace(self,kind):
        self.seed();before=self.journal.read_bytes();inode=self.journal.stat().st_ino
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd)
            with JournalFault(kind):r=j.accept(self.violating(),'new')
            self.assertEqual(r['acceptance'],'ACCEPTED_DURABILITY_UNCONFIRMED')
            self.assertEqual(r['persistence']['durability'],'UNCONFIRMED')
            self.assertEqual(r['persistence']['stage'],kind.upper().replace('-','_'))
            actual=json.loads(self.journal.read_bytes());self.assertEqual(actual,j.data)
            self.assertNotEqual(self.journal.read_bytes(),before);self.assertNotEqual(self.journal.stat().st_ino,inode)
            self.assertEqual(len(r['alerts']),3);self.assertEqual(r['delivery'],actual['checks']['new'])
            self.assertEqual(j.receipt_status('new')['persistence'],r['persistence'])
            self.assertEqual(r['persistence']['journal_sha256'],hashlib.sha256(self.journal.read_bytes()).hexdigest())
            self.assertEqual(r['persistence']['published_inode']['inode'],self.journal.stat().st_ino)
            # Neither same-memory nor reopened replay silently claims durable acceptance.
            replay=j.accept(self.violating(),'new');self.assertTrue(replay['replayed'])
            self.assertEqual(replay['persistence']['durability'],'UNCONFIRMED')
            j=C.DeliveryJournal(self.journal,lock_fd=fd);replay=j.accept(self.violating(),'new')
            self.assertEqual(replay['acceptance'],'HISTORICAL_RECEIPT_ONLY')
            self.assertEqual(replay['persistence']['durability'],'UNVERIFIED_AFTER_REOPEN')
    def test_directory_open_after_replace_is_explicit_accepted_indeterminate(self):self.postreplace('directory-open')
    def test_directory_fsync_after_replace_is_explicit_accepted_indeterminate(self):self.postreplace('directory-fsync')
    def precommit(self,kind):
        self.seed();before=self.journal.read_bytes();inode=self.journal.stat().st_ino
        if kind=='pending':self.journal.with_name('journal.pending').write_bytes(b'held pending')
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);memory=copy.deepcopy(j.data)
            with JournalFault(kind),self.assertRaises(OSError):j.accept(self.violating(),'new')
            self.assertEqual(j.data,memory);self.assertEqual(self.journal.read_bytes(),before)
            self.assertEqual(self.journal.stat().st_ino,inode)
            self.assertTrue(self.journal.with_name('journal.pending').exists())
            if kind=='pending':self.assertEqual(self.journal.with_name('journal.pending').read_bytes(),b'held pending')
    def test_file_fsync_before_replace_rejects_without_old_state_mutation(self):self.precommit('file-fsync')
    def test_replace_failure_rejects_without_old_state_mutation(self):self.precommit('replace')
    def test_staged_pending_collision_preserved(self):self.precommit('pending')
    def test_serialization_rejection_preserves_old_state(self):
        self.seed();before=self.journal.read_bytes();inode=self.journal.stat().st_ino
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);memory=copy.deepcopy(j.data)
            with self.assertRaises(TypeError):j.accept(self.violating(),'new',context={'unserializable':object()})
            self.assertEqual(j.data,memory);self.assertEqual(self.journal.read_bytes(),before)
            self.assertEqual(self.journal.stat().st_ino,inode)
            self.assertFalse(self.journal.with_name('journal.pending').exists())
    def runtime_fault(self,kind,after,expected_calls,state):
        calls=[]
        def sender(alert):
            # Verify the actual pre-send marker on disk, not a replacement journal mock.
            disk=json.loads(self.journal.read_bytes())
            self.assertEqual(disk['checks']['new']['state'],'AMBIGUOUS')
            calls.append(alert['alert_id'])
            return {'stage':'ENQUEUED','board':C.BOARD,'recipient':C.RECIPIENT,'notification_id':1}
        with JournalFault(kind,after):r=self.check(self.violating(),'new',sender=sender)
        self.assertEqual(r['status'],'INDETERMINATE');self.assertTrue(r['known_violations'])
        self.assertEqual(len(calls),expected_calls);self.assertEqual(r['delivery']['state'],state)
        self.assertEqual(len(r['alerts']),3)
        self.assertEqual(r['delivery'],json.loads(self.journal.read_bytes())['checks']['new'])
        before=self.journal.read_bytes();replay=self.check(self.violating(),'new',sender=sender)
        self.assertTrue(replay['replayed']);self.assertEqual(len(calls),expected_calls)
        self.assertEqual(replay['acceptance'],'HISTORICAL_RECEIPT_ONLY')
        self.assertEqual(self.journal.read_bytes(),before)
    def test_runtime_directory_open_acceptance_no_sender(self):self.runtime_fault('directory-open',1,0,'PLANNED')
    def test_runtime_directory_fsync_acceptance_no_sender(self):self.runtime_fault('directory-fsync',1,0,'PLANNED')
    def test_runtime_presend_directory_open_no_sender_ambiguous(self):self.runtime_fault('directory-open',2,0,'AMBIGUOUS')
    def test_runtime_presend_directory_fsync_no_sender_ambiguous(self):self.runtime_fault('directory-fsync',2,0,'AMBIGUOUS')
    def test_runtime_postsender_receipt_sync_stops_remaining_sends(self):self.runtime_fault('directory-fsync',3,1,'AMBIGUOUS')
    def test_recovery_exact_state_confirm_only_explicit_send_and_no_ambiguous_resend(self):
        self.seed();calls=[]
        def sender(a):calls.append(a['alert_id']);raise TimeoutError('controlled transport ambiguity')
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd)
            with JournalFault('directory-open'):r=j.accept(self.violating(),'new')
            before=self.journal.read_bytes();inode=self.journal.stat().st_ino
            with self.assertRaises(C.Invalid):j.deliver('new',r['alerts'],r['plan']['plan_id'],sender)
            with self.assertRaises(C.Invalid):j.confirm_durability('wrong-state')
            self.assertEqual(calls,[]);self.assertEqual(self.journal.read_bytes(),before)
            with JournalFault('directory-fsync',0),self.assertRaises(C.JournalDurabilityUnconfirmed):
                j.confirm_durability(C.digest(j.data))
            self.assertEqual(j.data,json.loads(before));self.assertEqual(calls,[])
            recovered=j.confirm_durability(C.digest(j.data))
            self.assertEqual(recovered['durability'],'CONFIRMED');self.assertEqual(calls,[])
            self.assertEqual(self.journal.read_bytes(),before);self.assertEqual(self.journal.stat().st_ino,inode)
            self.assertTrue(j.accept(self.violating(),'new')['replayed']);self.assertEqual(calls,[])
            row=j.deliver('new',r['alerts'],r['plan']['plan_id'],sender)
            self.assertEqual(row['state'],'AMBIGUOUS');self.assertEqual(len(calls),1)
            j.deliver('new',r['alerts'],r['plan']['plan_id'],sender);self.assertEqual(len(calls),1)
    def test_recovery_refuses_changed_disk_without_overwrite(self):
        self.seed()
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);other=copy.deepcopy(j.data)
            other['checks']['seed']['state']='EXTERNAL_SENTINEL'
            self.journal.write_text(json.dumps(other));before=self.journal.read_bytes();inode=self.journal.stat().st_ino
            with self.assertRaises(C.Invalid):j.confirm_durability(C.digest(j.data))
            self.assertEqual(self.journal.read_bytes(),before);self.assertEqual(self.journal.stat().st_ino,inode)
    def test_healthy_postreplace_is_indeterminate_and_remains_quiet(self):
        calls=[]
        with JournalFault('directory-fsync'):r=self.check(t.healthy(t.snapshot()),'healthy',sender=lambda a:calls.append(a))
        self.assertEqual(r['status'],'INDETERMINATE');self.assertFalse(r['known_violations'])
        self.assertEqual(r['delivery']['state'],'SILENT');self.assertEqual(calls,[])

_CLI_FAULT_DRIVER = r'''
import builtins,contextlib,json,sys
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import test_review_boundaries as b
kind,contract=sys.argv[3],Path(sys.argv[4])
original=builtins.print
def emit(*args,**kw):
    if kw.get('file') is None and len(args)==1:
        value=json.loads(args[0])
        if isinstance(value,dict):contract.write_text(json.dumps(value,sort_keys=True))
    original(*args,**kw)
with b.JournalFault(kind):
    builtins.print=emit
    try:code=b.C.main(sys.argv[5:])
    finally:builtins.print=original
sys.exit(code)
'''
class PostReplacementCLI(Owned):
    def invoke(self,kind,args,number):
        import subprocess,sys
        contract=self.area/('contract-'+str(number)+'.json')
        # Private native stdout/stderr are retained and never diagnostic inputs.
        stdout=self.area/('stdout-'+str(number)+'.private')
        stderr=self.area/('stderr-'+str(number)+'.private')
        env={k:v for k,v in os.environ.items() if k in ('ADAPTER_CORE_SOURCE','ADAPTER_TEST_RUNTIME',
             'ADAPTER_FIXTURE_HOME','BOUNDARY_TEST_RUNTIME','CORRECTION_TEST_RUNTIME','STACK_DAG_TEST_RUNTIME')}
        env.update(PATH='/usr/bin:/bin',HOME=str(self.area),LC_ALL='C')
        argv=['/usr/bin/python3','-I','-S','-B','-c',_CLI_FAULT_DRIVER,str(ROOT/'tests'),str(ROOT/'src'),kind,str(contract),*args]
        (self.area/('launch-'+str(number)+'.json')).write_text(json.dumps({'argv':argv,'env':env,'stdin':'/dev/null'}))
        with stdout.open('xb') as out,stderr.open('xb') as err:
            p=subprocess.run(argv,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=20)
        (self.area/('end-'+str(number)+'.json')).write_text(json.dumps({'exit_code':p.returncode}))
        return p.returncode,json.loads(contract.read_text()) if contract.exists() else None
    def cli_post(self,kind):
        s=t.snapshot();snapshot=self.area/'snapshot.json';snapshot.write_text(json.dumps(s))
        binding=self.area/'binding.json';binding.write_text(json.dumps({
          'schema':'stack-startup/v1','source_sha256':hashlib.sha256(Path(C.__file__).read_bytes()).hexdigest(),
          'snapshot_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),
          'feed_binding':s['feed']['binding'],'feed_schema':s['feed']['schema'],'owner':C.RECIPIENT}))
        args=['once','--snapshot',str(snapshot),'--binding',str(binding),'--journal',str(self.journal),
              '--lock',str(self.lock),'--check-id','new']
        end,r=self.invoke(kind,args,1);self.assertEqual(end,4)
        self.assertEqual(r['acceptance'],'ACCEPTED_DURABILITY_UNCONFIRMED')
        self.assertEqual(len(r['alerts']),3)
        self.assertEqual(r['delivery'],json.loads(self.journal.read_bytes())['checks']['new'])
        before=self.journal.read_bytes();inode=self.journal.stat().st_ino
        end,replay=self.invoke('none',args,2);self.assertEqual(end,3)
        self.assertEqual(replay['acceptance'],'HISTORICAL_RECEIPT_ONLY');self.assertTrue(replay['replayed'])
        self.assertEqual(self.journal.read_bytes(),before)
        args=['recover','--journal',str(self.journal),'--lock',str(self.lock),'--owner',C.RECIPIENT,
              '--check-id','new','--state-digest',r['persistence']['state_digest']]
        end,recovered=self.invoke('none',args,3);self.assertEqual(end,0)
        self.assertEqual(recovered['persistence']['durability'],'CONFIRMED')
        self.assertEqual(recovered['receipt'],r['delivery'])
        self.assertEqual(self.journal.read_bytes(),before);self.assertEqual(self.journal.stat().st_ino,inode)
    def test_actual_CLI_directory_open_exit4_replay_receipt_and_explicit_recovery(self):self.cli_post('directory-open')
    def test_actual_CLI_directory_fsync_exit4_replay_receipt_and_explicit_recovery(self):self.cli_post('directory-fsync')

class OtherJournalCallers(Owned):
    def test_observe_postreplace_exception_preserves_published_frontier(self):
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd)
            with JournalFault('directory-open'),self.assertRaises(C.JournalDurabilityUnconfirmed) as caught:
                j.observe(t.snapshot())
            self.assertEqual(j.data,json.loads(self.journal.read_bytes()))
            self.assertIn('observation',j.data)
            self.assertEqual(caught.exception.outcome['state_digest'],C.digest(j.data))
    def test_prepare_postreplace_exception_has_retrievable_current_receipt(self):
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd)
            with JournalFault('directory-fsync'),self.assertRaises(C.JournalDurabilityUnconfirmed):
                j.prepare('legacy',[],'prepared-plan')
            self.assertEqual(j.data,json.loads(self.journal.read_bytes()))
            self.assertEqual(j.receipt_status('legacy')['persistence']['durability'],'UNCONFIRMED')
            self.assertEqual(j.receipt('legacy')['state'],'SILENT')
    def test_reconcile_postreplace_exception_preserves_new_receipt_without_resend(self):
        calls=[];s=t.snapshot();p=C.plan(s);notices=C.alerts(s,p,'new')
        def sender(alert):
            calls.append(alert['alert_id'])
            return {'stage':'ENQUEUED','board':C.BOARD,'recipient':C.RECIPIENT,'notification_id':1}
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);j.deliver('new',notices,p['plan_id'],sender)
            before_calls=list(calls)
            receipt={'stage':'RECIPIENT_ACK','board':C.BOARD,'recipient':C.RECIPIENT,
                     'notification_id':1,'ack_ref':'controlled/ack'}
            with JournalFault('directory-fsync'),self.assertRaises(C.JournalDurabilityUnconfirmed):
                j.reconcile('new',notices[0]['alert_id'],receipt)
            self.assertEqual(j.data,json.loads(self.journal.read_bytes()))
            self.assertEqual(j.receipt('new')['attempts'][0]['receipt'],receipt)
            self.assertEqual(j.receipt_status('new')['persistence']['durability'],'UNCONFIRMED')
            self.assertEqual(calls,before_calls)
    def test_presend_file_fsync_failure_retains_planned_disk_and_memory_no_sender(self):
        calls=[];s=t.snapshot()
        with C.owner_lock(self.lock,C.RECIPIENT,journal_path=self.journal) as fd:
            j=C.DeliveryJournal(self.journal,lock_fd=fd);r=j.accept(s,'new')
            before=self.journal.read_bytes();inode=self.journal.stat().st_ino
            with JournalFault('file-fsync'),self.assertRaises(OSError):
                j.deliver('new',r['alerts'],r['plan']['plan_id'],lambda a:calls.append(a))
            self.assertEqual(calls,[]);self.assertEqual(j.data,json.loads(before))
            self.assertEqual(self.journal.read_bytes(),before);self.assertEqual(self.journal.stat().st_ino,inode)
            self.assertEqual(j.receipt('new')['state'],'PLANNED')
