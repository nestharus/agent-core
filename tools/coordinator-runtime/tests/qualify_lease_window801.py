"""Explicit final-tree qualification. Only newly owned fixtures are inventoried."""
import os,pathlib,subprocess,json,time,signal,hashlib,selectors,sys
repo=pathlib.Path(__file__).resolve().parents[3]
base=pathlib.Path('/tmp/lease-window801')
base.mkdir(mode=0o700,exist_ok=True)
def usage():
 total=0
 for p in base.rglob('*'):
  try:
   if p.is_file():total+=p.stat().st_size
  except FileNotFoundError:pass  # Owned SQLite transient WAL/checkpoint race.
 return total
def room():
 if usage()>=128*1024**2:raise RuntimeError('stop-new128MiB')
run=base/('final-'+str(time.time_ns()));room();run.mkdir(mode=0o700)
backing=pathlib.Path('/tmp/lease-window801/final-1794084542499436255')
src=backing/'src';oldsrc=backing/'oldsrc'
original_manifest=json.loads((backing/'manifest.json').read_text())
overlays={}
for rel,sha in original_manifest.items():
 current=repo/rel
 if hashlib.sha256(current.read_bytes()).hexdigest()!=sha:
  if '/coordinator_runtime/' in rel:raise RuntimeError('production backing changed')
  target=run/'overlay'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(current.read_bytes());overlays[rel]=target
 if hashlib.sha256((src/rel).read_bytes()).hexdigest()!=sha:raise RuntimeError('original backing changed')
manifest={rel:hashlib.sha256((repo/rel).read_bytes()).hexdigest() for rel in original_manifest}
(run/'manifest.json').write_text(json.dumps(manifest,indent=2))
records=[]
def execute(label,root,fixtures,env,args):
 room();fixtures.mkdir(mode=0o700,exist_ok=True);(fixtures/'tmp').mkdir(mode=0o700,exist_ok=True)
 cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
 for path in ['/usr','/lib','/lib64','/bin']:cmd+=['--ro-bind',path,path]
 cmd+=['--proc','/proc','--dev','/dev','--ro-bind',str(root),'/src','--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
 for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',QA629_FIXTURES='/fixtures',COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',PYTHONPATH='/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests',**env).items():cmd+=['--setenv',k,v]
 for rel,target in overlays.items():cmd+=['--ro-bind',str(target),'/src/'+rel]
 cmd+=['--chdir','/src/tools/coordinator-runtime/tests','/usr/bin/python3','-B',*args]
 child=None;data=bytearray();reason=None;started=time.monotonic()
 try:
  child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
  sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ)
  while sel.get_map():
   if time.monotonic()-started>180:reason='timeout180s';os.killpg(child.pid,signal.SIGKILL)
   for key,_ in sel.select(.1):
    chunk=os.read(key.fd,65536)
    if not chunk:sel.unregister(key.fd);continue
    if len(data)+len(chunk)>4*1024**2:reason='capture4MiB';os.killpg(child.pid,signal.SIGKILL)
    data.extend(chunk[:max(0,4*1024**2-len(data))])
   if usage()>=192*1024**2:reason='hard192MiB';os.killpg(child.pid,signal.SIGKILL)
  child.wait(timeout=10)
 finally:
  if child:
   if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
   child.wait()
  (run/(label+'.txt')).write_bytes(data)
  record=dict(label=label,pid=child.pid if child else None,END=child.returncode if child else None,reason=reason,bytes=len(data),owned_bytes=usage(),args=args)
  records.append(record);(run/'collection.json').write_text(json.dumps(records,indent=2));print(json.dumps(record),flush=True);print(data.decode(errors='replace')[-18000:],flush=True)
 return child.returncode
ids=['test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied']
ids += ['test_owner_lease797.OwnerLease.'+n for n in ('test_public_cutoff_continuation_whole_original_and_control_once','test_refusal_matrix_metadata_before_body_and_no_selection','test_stop_budget_and_original_policies_never_reset','test_owned_wake_future_timer_and_foreign_endpoint_refusal','test_changed_source_config_task_custody_and_peer_refuse','test_no_lease_and_total_input_window_and_native_effect_bounds')]
ids += ['test_report_control793.Boundaries.'+n for n in ('test_closed_exact_delta_and_v1_unchanged','test_original_deadlines_never_renewed','test_repair_selection_append_only')]
ids += ['test_control_marker789.MarkerTests.'+n for n in ('test_collected_marker_derives_only_task_preserves_raw_and_old_obligations','test_refuses_invalid_binding_source_collection_and_semantics','test_malformed_fields_other_modes_and_native_claims_are_not_normalized','test_wrong_queue_capability_and_source_bytes_refuse','test_native_owner_and_forged_derived_evidence_are_not_rewritten')]
ids += ['test_source_continuity688.Continuity.'+n for n in ('test_real_admitted_board_and_whole_attributed_report_keep_same_authority','test_basis_is_metadata_only_and_held_historical_reserved_refuse_before_body','test_mutated_body_rolls_back_receipt_and_reads_only_selected_bodies','test_wrong_owner_grant_stop_END_and_concurrent_collector','test_finite_windows_charges_and_revocation_survive_repair')]

lease_ids=ids
lease_end=execute('lease20',src,run/'lease-fixtures',{},['-m','unittest','-v',*lease_ids])
window_ids=['test_control_window798.Window798.'+n for n in ['test_continuing_policy_conservation_and_deadlines','test_near_admission_and_allocation_exhaustion','test_public_cli_basis_select_apply_two_anchors','test_fresh_basis_rejects_bad_upstream_before_body','test_midgroup_queue_and_hash_refuse_before_control_body','test_stale_between_groups_rolls_back_without_wrong_body']]+['test_authentic_control794.Kernel794.test_source_and_sdk_snapshots_readonly']
authentic_ids=['test_authentic_control794.Authentic794.'+n for n in ['test_positive_actual_pair_and_distinct_applier','test_negative_metadata_matrix_atomic_before_bodies','test_negative_full_bytes_and_expiry_atomic','test_negative_original_chain_and_request_pins','test_closed_actual_source_delta_and_v1_limits','test_stale_between_groups_rolls_back_without_wrong_body','test_return_failure_rolls_back_resolution_and_child']]
extra_ids=['test_lease_window801.LeaseWindow801.test_effective_lease_expires_between_body_groups','test_lease_window801.LeaseWindow801.test_plan_clock_and_issuer_guards_before_body']
new_ids=window_ids+extra_ids
fixtures=run/'authentic-fixtures'
producer_code='from test_control_window798 import Window798; from test_authentic_control794 import Authentic794; from test_lease_window801 import LeaseWindow801; cases='+repr([(i.split('.')[1],i.rsplit('.',1)[1]) for i in new_ids if '.Kernel794.' not in i])+ ';\nfor cls,name in cases:\n case=globals()[cls](name)\n try: case.setUp()\n finally: case.doCleanups()'
producer_end=execute('original23773',oldsrc,fixtures,dict(PHASE794='produce'),['-c',producer_code])
new_end=execute('lease-window-final',src,fixtures,dict(PHASE794='consume',QUALIFICATION801_OWNER_LEASE='1'),['-m','unittest','-v',*new_ids]) if producer_end==0 else 1
(run/'final.json').write_text(json.dumps(dict(lease_END=lease_end,producer_END=producer_end,combined_END=new_end,run=str(run),usage=usage(),exact_ids=lease_ids+new_ids),indent=2))
sys.exit(0 if lease_end==producer_end==new_end==0 else 1)
