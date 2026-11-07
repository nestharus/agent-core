"""Owned positive-mount qualification; failures and numeric ENDs retained."""
import os, pathlib, subprocess, json, time, signal, selectors, tempfile, hashlib
repo=pathlib.Path(__file__).resolve().parents[3]
root=pathlib.Path(tempfile.mkdtemp(prefix='report-leaf816-',dir='/tmp'))
os.chmod(root,0o700)
def usage():
    total=0
    for p in root.rglob('*'):
        try:
            if p.is_file(): total+=p.stat().st_size
        except FileNotFoundError: pass
    return total
src=root/'src';src.mkdir()
paths=subprocess.run(['git','--git-dir=/home/nes/ai/.git','ls-tree','-r','--name-only','822bea11b10f95bb6489d4dade9367dfe00d6ccf','tools/coordinator-runtime','tools/message-board','tools/direct-child','tools/direct-codex-child','tools/branch_release.py','tools/operational_contracts.py'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/test_report_leaf816.py']
manifest={}
for rel in dict.fromkeys(paths):
    if any(p in {'AGENTS.md','WORK_LOG.md','runs','captures'} for p in pathlib.PurePosixPath(rel).parts):continue
    if not (rel.endswith('.py') or rel.endswith('/coordinator') or rel.endswith('/coordinator-receive.md') or rel.endswith('/launch.sh')):continue
    data=(repo/rel).read_bytes(); target=src/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    manifest[rel]=hashlib.sha256(data).hexdigest()
for name in ['active_listener.py','queue_transport.py','catalog.py','board_store.py']:
    (src/'tools/coordinator-runtime/tests/fixture_snapshot'/name).write_bytes((src/'tools/message-board'/name).read_bytes())
(src/'tools/message-board/retention.py').write_bytes((src/'tools/coordinator-runtime/tests/fixture_snapshot/retention.py').read_bytes())
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
oldsrc=root/'oldsrc';oldsrc.mkdir()
for rel in manifest:
    data=(src/rel).read_bytes()
    if '/coordinator_runtime/' in rel:
        old=subprocess.run(['git','--git-dir=/home/nes/ai/.git','show','23773e6bfe46a2d71e8fc1dbfc38b1e60729331f:'+rel],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        if old.returncode:continue
        data=old.stdout
    dest=oldsrc/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
for name in ['active_listener.py','queue_transport.py','catalog.py','board_store.py']:
    (oldsrc/'tools/coordinator-runtime/tests/fixture_snapshot'/name).write_bytes((oldsrc/'tools/message-board'/name).read_bytes())
(oldsrc/'tools/message-board/retention.py').write_bytes((oldsrc/'tools/coordinator-runtime/tests/fixture_snapshot/retention.py').read_bytes())
handoff=root/'handoff';handoff.mkdir()
records=[]
def run(label,ids,source=None,code=None):
    if usage()>=128*1024**2:raise RuntimeError('stop-new128MiB')
    fixtures=root/label;fixtures.mkdir();(fixtures/'tmp').mkdir()
    cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
    for path in ['/usr','/lib','/lib64','/bin']:cmd+=['--ro-bind',path,path]
    cmd+=['--proc','/proc','--dev','/dev','--ro-bind',str(source or src),'/src','--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
    for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',QA629_FIXTURES='/fixtures',COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',PYTHONPATH='/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():cmd+=['--setenv',k,v]
    cmd += ['--bind' if code else '--ro-bind',str(handoff),'/handoff']
    cmd+=['--chdir','/fixtures','/usr/bin/python3','-B']+(['-c',code] if code else ['-m','unittest','-v',*ids])
    child=None;data=bytearray();reason=None;start=time.monotonic()
    try:
        child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ)
        while sel.get_map():
            if time.monotonic()-start>180 or usage()+len(data)>=192*1024**2:
                reason='time180-or-total192MiB';os.killpg(child.pid,signal.SIGKILL)
            for key,_ in sel.select(.1):
                chunk=os.read(key.fd,65536)
                if not chunk:sel.unregister(key.fd);continue
                if len(data)+len(chunk)>4*1024**2:
                    reason='capture4MiB';os.killpg(child.pid,signal.SIGKILL)
                data.extend(chunk[:max(0,4*1024**2-len(data))])
        child.wait(timeout=10)
    finally:
        if child:
            if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
            child.wait()
        (root/(label+'.txt')).write_bytes(data)
        record=dict(label=label,pid=child.pid if child else None,END=child.returncode if child else None,reason=reason,bytes=len(data),owned_bytes=usage(),test_ids=ids)
        records.append(record);(root/'collection.json').write_text(json.dumps(records,indent=2));print(json.dumps(record),flush=True);print(data.decode(errors='replace')[-18000:],flush=True)
    return child.returncode
new=['test_report_leaf816.ReportLeaf816.'+n for n in ['test_collected_reviews_return_maps_known_work_point_preserving_originals','test_metadata_wrong_cap_hold_birth_changed_hash_and_uncollected_before_body','test_expired_and_changed_task_grant_refuse_before_body','test_changed_frozen_receipt_and_orphan_marker_refuse','test_new_point_and_native_impersonation_remain_refused','test_mutation_after_target_read_is_refused','test_original23773_producer_admitted_collected_and_mapped','test_forged_response_identity_refuses_before_leaf_body']]
ids=['test_authentic_control794.Kernel794.test_source_and_sdk_snapshots_readonly','test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied',*new,'test_report_local700.ReportLocal.test_dispatcher_conserves_whole_reports_without_native_context','test_report_local700.ReportLocal.test_source_and_frozen_permission_failures_remain_queued','test_collected_report593.Reports.test_authentic_whole_adverse_report_reaches_assigned_integrator_without_cleanliness_or_acceptance']
producer_code='''import json
from pathlib import Path
from test_report_transport739 import ReportTransport
from coordinator_runtime import processing
case=ReportTransport('test_prompt_supplies_each_original_once_and_explicit_protocol')
try:
 case.setUp()
 job,attempt,members=case.start([case.reports[0]])
 response=case.finish(job,attempt,case.answer(job))
 Path('/handoff/original23773.json').write_text(json.dumps(dict(source='23773e6bfe46a2d71e8fc1dbfc38b1e60729331f',implementation=processing.implementation(),response=response,attempt=case.store.attempt(attempt)),sort_keys=True))
finally:case.doCleanups()
'''
producer_end=run('original23773',[],oldsrc,producer_code)
end=run('candidate',ids) if producer_end==0 else producer_end
if end==0:
    target=src/'tools/coordinator-runtime/coordinator_runtime/local_integration.py';candidate=target.read_bytes()
    baseline=subprocess.run(['git','--git-dir=/home/nes/ai/.git','show','822bea11b10f95bb6489d4dade9367dfe00d6ccf:tools/coordinator-runtime/coordinator_runtime/local_integration.py'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout
    target.write_bytes(baseline)
    try:run('baseline-red',[new[0]])
    finally:target.write_bytes(candidate)
print(json.dumps(dict(root=str(root),END=end,owned_bytes=usage())),flush=True)
raise SystemExit(end)
