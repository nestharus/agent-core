import os, pathlib, subprocess, json, time, signal
repo=pathlib.Path(__file__).resolve().parents[3]
base=pathlib.Path(os.environ.get('CONTROL_MARKER831_FIXTURES','/tmp/control-marker831-owned'));base.mkdir(mode=0o700,exist_ok=True)
size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if size>=128*1024**2:raise SystemExit('stop-new128MiB')
run=base/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700)
src=run/'src';src.mkdir();fixtures=run/'fixtures';fixtures.mkdir(mode=0o700);(fixtures/'tmp').mkdir(mode=0o700)
paths=subprocess.run(['git','-C',str(repo),'ls-files','tools/coordinator-runtime'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/test_plain_control817.py','tools/coordinator-runtime/tests/test_plain_control821.py','tools/coordinator-runtime/coordinator_runtime/plain_control.py','tools/coordinator-runtime/tests/test_control_marker831.py']
paths += ['tools/message-board/'+n+'.py' for n in ('board','board_store','catalog','retention','active_listener','queue_transport')]
paths += ['tools/direct-child/execution_pool.py']
for rel in dict.fromkeys(paths):
 if pathlib.Path(rel).name in ('AGENTS.md','WORK_LOG.md'):continue
 origin=repo/rel
 if not origin.is_file():continue
 target=src/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(origin.read_bytes())
# The public Board tree has four SDK files. Complete the isolated SDK5
# projection with the explicit synthetic retention fixture, never a provider.
(src/'tools/message-board/retention.py').write_bytes(
    (src/'tools/coordinator-runtime/tests/fixture_snapshot/retention.py').read_bytes())
ids=['test_plain_control817.Terminal817.'+n for n in (
 'test_kernel_closure','test_public_board_collected_control_terminal_once',
 'test_existing_pending_consumer_refuses_completed_consumer_preserved',
 'test_unknown_scope_obligations_and_bad_metadata_refuse_before_body',
 'test_obligations_remain_blocking_and_unmodified','test_mutation_at_transaction_refuses',
 'test_conserved_duty_pins_lossless_and_exact_completion',
 'test_uncertain_outbox_and_stale_capability_refuse_before_body','test_refused_or_forged_result_before_source_body')]
ids += ['test_processing206.ProtocolTests.test_control_transaction_creates_one_work_return_and_consumer_blocks_completion',
 'test_control_marker789.MarkerTests.test_malformed_fields_other_modes_and_native_claims_are_not_normalized']
ids += ['test_plain_control821.Completion821.'+n for n in ('test_same869_shape_existing_return_cli_terminal_once_preserves_every_original','test_automatic_delegated_collected_structured_scope_nonempty','test_pending_descendant_reserved_and_effect_consumers_refuse_before_source','test_unknown_message_owned_and_stale_source_pins_block','test_current_work_external_conservation_attestation','test_tool_metadata_and_binding_refuse_before_protected_body','test_existing_return_mutation_fence_rolls_back','test_software_cannot_invent_scope_or_impersonate_work')]
ids += ['test_plain_control821.LeaseCompletion821.test_genuine_lease_control_terminal_raw_native_expiry_and_old_producer_conserved']
ids += ['test_control_marker831.Marker831.'+n for n in ('test_marker_api_fresh_classifier_completion_replay','test_marker_existing_return_cli_terminal_once','test_marker_metadata_before_body','test_marker_descendant_reservation_effect_guards','test_marker_unknown_owned_and_stale_guards','test_marker_external_attestation','test_marker_automatic_scope','test_marker_source_reservation_and_external_guards')]
ids += ['test_control_marker789.MarkerTests.'+n for n in ('test_collected_marker_derives_only_task_preserves_raw_and_old_obligations','test_refuses_invalid_binding_source_collection_and_semantics','test_wrong_queue_capability_and_source_bytes_refuse','test_native_owner_and_forged_derived_evidence_are_not_rewritten')]
if os.environ.get('CONTROL_MARKER831_BASELINE') == '1':
 for name in ('plain_control.py','processing.py'):
  data=subprocess.run(['git','-C',str(repo),'show','ff9a0b97d612de1086148661c2e81bf9cc854c92:tools/coordinator-runtime/coordinator_runtime/'+name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout
  (src/'tools/coordinator-runtime/coordinator_runtime'/name).write_bytes(data)
 ids=['test_control_marker831.Marker831.test_marker_api_fresh_classifier_completion_replay','test_control_marker831.Marker831.test_marker_metadata_before_body']
if os.environ.get('CONTROL_MARKER831_GUARDS') == '1':
 ids=['test_control_marker831.Marker831.test_marker_source_reservation_and_external_guards']
cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/bin','/bin','--proc','/proc','--dev','/dev','--ro-bind',str(repo),'/actualsrc','--ro-bind',str(src),'/src','--bind',str(fixtures),'/fixtures','--tmpfs','/tmp','--dir','/home','--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/fixtures','--setenv','TMPDIR','/fixtures/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','QA629_FIXTURES','/fixtures','--setenv','COORDINATOR_TEST_BOARD_LIBRARY','/src/tools/message-board','--setenv','PYTHONPATH','/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests','--chdir','/fixtures','/usr/bin/python3','-m','unittest','-v',*ids]
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
   os.killpg(proc.pid,signal.SIGKILL)
  tail,_=proc.communicate(timeout=10)
  if tail and cap.stat().st_size+len(tail)<=4*1024**2:
   with cap.open('ab') as f:f.write(tail)
  end=proc.returncode
 else:end=None
size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
result=dict(reproduction=os.environ.get('CONTROL_MARKER831_BASELINE') == '1',run=str(run),END=end,pid=proc.pid if proc else None,timeout=reason,cumulative_bytes=size,tests=ids,readonly_src=True,network_isolated=True,private_TMPDIR_before_imports=True)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(cap.read_text()[-23000:])
if size>=192*1024**2:raise SystemExit('cumulative192MiB')

raise SystemExit(end if end is not None else 1)
