import os, pathlib, subprocess, json, time, signal
repo=pathlib.Path(__file__).resolve().parents[3]
base=pathlib.Path(os.environ.get('OWNER_LEASE797_FIXTURES','/tmp/owner-lease797-fixtures'));base.mkdir(mode=0o700,exist_ok=True)
size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if size>=128*1024**2:raise SystemExit('stop-new128MiB')
run=base/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700)
src=run/'src';src.mkdir();fixtures=run/'fixtures';fixtures.mkdir(mode=0o700);(fixtures/'tmp').mkdir(mode=0o700)
paths=subprocess.run(['git','-C',str(repo),'ls-files','tools/coordinator-runtime'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/test_owner_lease797.py']
paths += ['tools/message-board/'+n+'.py' for n in ('board_store','catalog','retention','active_listener','queue_transport')]
paths += ['tools/direct-child/execution_pool.py']
for rel in dict.fromkeys(paths):
 if pathlib.Path(rel).name in ('AGENTS.md','WORK_LOG.md'):continue
 origin=repo/rel
 if not origin.is_file():continue
 target=src/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(origin.read_bytes())
# Declared inherited fixture adaptation, matching793 frozen-task basis repair.
p=src/'tools/coordinator-runtime/tests/test_source_continuity688.py'
s=p.read_text().replace('transition = dict(basis=dict(release=self.old_release,','transition = dict(basis=dict(release=self.old_release, tasks=self.config[\'tasks\'],')
p.write_text(s)
ids=['test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied']
ids += ['test_owner_lease797.OwnerLease.'+n for n in ('test_public_cutoff_continuation_whole_original_and_control_once','test_refusal_matrix_metadata_before_body_and_no_selection','test_stop_budget_and_original_policies_never_reset','test_owned_wake_future_timer_and_foreign_endpoint_refusal','test_changed_source_config_task_custody_and_peer_refuse','test_no_lease_and_total_input_window_and_native_effect_bounds')]
ids += ['test_report_control793.Boundaries.'+n for n in ('test_closed_exact_delta_and_v1_unchanged','test_original_deadlines_never_renewed','test_repair_selection_append_only')]
ids += ['test_control_marker789.MarkerTests.'+n for n in ('test_collected_marker_derives_only_task_preserves_raw_and_old_obligations','test_refuses_invalid_binding_source_collection_and_semantics','test_malformed_fields_other_modes_and_native_claims_are_not_normalized','test_wrong_queue_capability_and_source_bytes_refuse','test_native_owner_and_forged_derived_evidence_are_not_rewritten')]
ids += ['test_source_continuity688.Continuity.'+n for n in ('test_real_admitted_board_and_whole_attributed_report_keep_same_authority','test_basis_is_metadata_only_and_held_historical_reserved_refuse_before_body','test_mutated_body_rolls_back_receipt_and_reads_only_selected_bodies','test_wrong_owner_grant_stop_END_and_concurrent_collector','test_finite_windows_charges_and_revocation_survive_repair')]
cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/bin','/bin','--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src','--bind',str(fixtures),'/fixtures','--tmpfs','/tmp','--dir','/home','--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/fixtures','--setenv','TMPDIR','/fixtures/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','QA629_FIXTURES','/fixtures','--setenv','COORDINATOR_TEST_BOARD_LIBRARY','/src/tools/message-board','--setenv','PYTHONPATH','/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests','--chdir','/fixtures','/usr/bin/python3','-m','unittest','-v',*ids]
cap=run/'output.txt';proc=None;start=time.monotonic();output=b'';reason=None
try:
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 import selectors
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 with cap.open('wb') as f:
  while sel.get_map():
   if time.monotonic()-start>180:reason='timeout180s';os.killpg(proc.pid,signal.SIGKILL)
   for key,_ in sel.select(0.2):
    chunk=os.read(key.fd,65536)
    if not chunk:sel.unregister(key.fileobj);continue
    if f.tell()+len(chunk)>4*1024**2:reason='capture4MiB';os.killpg(proc.pid,signal.SIGKILL)
    else:f.write(chunk)
   if reason:break
finally:
 if proc:
  if proc.poll() is None:
   if reason:os.killpg(proc.pid,signal.SIGKILL)
  tail,_=proc.communicate(timeout=10)
  if tail and cap.stat().st_size+len(tail)<=4*1024**2:
   with cap.open('ab') as f:f.write(tail)
  end=proc.returncode
 else:end=None
size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
result=dict(run=str(run),END=end,pid=proc.pid if proc else None,timeout=reason,cumulative_bytes=size,tests=ids,readonly_src=True,network_isolated=True,private_TMPDIR_before_imports=True)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(cap.read_text()[-23000:])
if size>=192*1024**2:raise SystemExit('cumulative192MiB')
