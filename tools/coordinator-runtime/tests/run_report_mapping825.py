"""Owned positive-mount qualification; failures and numeric ENDs retained."""
import os, pathlib, subprocess, json, time, signal, selectors, tempfile, hashlib, sys
repo=pathlib.Path(__file__).resolve().parents[3]
root=pathlib.Path(tempfile.mkdtemp(prefix='report-mapping825-',dir='/tmp'))
os.chmod(root,0o700)
prior=[pathlib.Path(p) for p in sys.argv[1:]]
def usage():
    total=0
    for p in (p for base in [root,*prior] for p in base.rglob('*')):
        try:
            if p.is_file(): total+=p.stat().st_size
        except FileNotFoundError: pass
    return total
src=root/'src';src.mkdir()
paths=subprocess.run(['git','-C',str(repo),'ls-files','tools/coordinator-runtime','tools/message-board','tools/direct-child','tools/direct-codex-child','tools/branch_release.py','tools/operational_contracts.py'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/test_report_mapping825.py','tools/coordinator-runtime/tests/run_report_mapping825.py']
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
ids=['test_report_mapping825.Mapping825.'+n for n in ['test_delegated_new_completion_refuses_before_resolution','test_delegated_known_completion_and_packet_work','test_genuine_outer_new_work_refuses_packet','test_genuine_outer_known_packet_works']]
ids += ['test_authentic_control794.Kernel794.test_source_and_sdk_snapshots_readonly','test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied']
ids += ['test_report_leaf816.ReportLeaf816.'+n for n in ['test_collected_reviews_return_maps_known_work_point_preserving_originals','test_metadata_wrong_cap_hold_birth_changed_hash_and_uncollected_before_body','test_expired_and_changed_task_grant_refuse_before_body','test_changed_frozen_receipt_and_orphan_marker_refuse','test_new_point_and_native_impersonation_remain_refused','test_mutation_after_target_read_is_refused','test_forged_response_identity_refuses_before_leaf_body']]
ids += ['test_metadata471.Automatic.test_unknown_is_owned_and_only_positive_new_enters_discovery','test_metadata471.Automatic.test_snapshot_is_before_model_and_never_restamped_after_result','test_metadata471.Automatic.test_holds_permissions_and_original_source_refuse_before_acquisition']
end=run('candidate',ids)
# Same tests and immutable baseline production bodies: both bypasses must be red.
originals={}
for name in ['local_integration.py','metadata_lookup.py']:
    rel='tools/coordinator-runtime/coordinator_runtime/'+name
    target=src/rel; originals[rel]=target.read_bytes()
    target.write_bytes(subprocess.run(['git','-C',str(repo),'show','acd5b20781fba2cfe7b16df6d731342d111420bc:'+rel],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout)
try: baseline=run('baseline-red',[ids[0],ids[2]])
finally:
    for rel,data in originals.items():(src/rel).write_bytes(data)
print(json.dumps(dict(root=str(root),END=end,baseline_END=baseline,owned_bytes=usage())),flush=True)
raise SystemExit(end)
