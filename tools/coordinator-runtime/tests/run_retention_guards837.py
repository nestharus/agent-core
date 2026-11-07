"""Bounded retained fictional QA; positive mounts only, no network or native tools."""
import hashlib,json,os,selectors,signal,subprocess,time,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
base=repo/'.qualification837';base.mkdir(mode=0o700,exist_ok=True)
def usage():return sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if usage()>=128*1024**2:raise SystemExit('stop-new128MiB')
run=base/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700)
fixture=run/'fixtures';(fixture/'tmp').mkdir(parents=True,mode=0o700)
sdk=run/'sdk';sdk.mkdir()
for name in ['board_store.py','catalog.py','queue_transport.py','active_listener.py','retention.py']:
 origin=repo/'tools/message-board'/name if name!='retention.py' else repo/'tools/coordinator-runtime/tests/fixture_snapshot'/name
 (sdk/name).write_bytes(origin.read_bytes())
ids=['test_retention_guards837.Retention837.'+n for n in [
 'test_immutable_clock_hold_clear_restart_and_unknown','test_new_dependent_and_reopened_work_keep_source',
 'test_late_exclusion_origin_and_hold_before_all_path_io','test_direct_exclusion_and_new_hold_during_hash',
 'test_every_existing_lifecycle_refusal_and_once_only','test_original_identity_symlink_hardlink_hash_and_custody_fences',
 'test_kernel_source_and_sdk5_readonly']]
cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
for p in ['/usr','/lib','/lib64','/bin']:cmd+=['--ro-bind',p,p]
cmd+=['--proc','/proc','--dev','/dev','--ro-bind',str(repo),'/src','--ro-bind',str(repo),'/actualsrc','--ro-bind',str(sdk),'/sdk','--bind',str(fixture),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',COORDINATOR_TEST_BOARD_LIBRARY='/sdk',PYTHONPATH='/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():cmd+=['--setenv',k,v]
baseline='--baseline' in sys.argv
if baseline:
 ids=[ids[0],ids[2]]
 for name in ['store.py','cleanup.py']:
  rel='tools/coordinator-runtime/coordinator_runtime/'+name
  body=subprocess.run(['git','-C',str(repo),'show','71009f42eaaaed58db03ba178ba2e9f958da8573:'+rel],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout
  path=run/('baseline-'+name);path.write_bytes(body)
  cmd+=['--ro-bind',str(path),'/src/'+rel]
source_files=[repo/'tools/coordinator-runtime/coordinator_runtime'/n for n in ['cleanup.py','store.py','report_repair.py']]
start_hashes={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
cmd+=['--chdir','/fixtures' ,'/usr/bin/python3','-B','-m','unittest','-v',*ids]
proc=None;data=bytearray();reason=None;start=time.monotonic()
try:
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 while sel.get_map():
  if time.monotonic()-start>180:reason='timeout180s'
  if usage()+len(data)>=192*1024**2:reason='total192MiB'
  if reason and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL)
  for key,_ in sel.select(.1):
   chunk=os.read(key.fd,65536)
   if not chunk:sel.unregister(key.fd);continue
   if len(data)+len(chunk)>4*1024**2:reason='capture4MiB'
   data.extend(chunk[:max(0,4*1024**2-len(data))])
finally:
 if proc:
  if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL)
  proc.wait()
 (run/'output.txt').write_bytes(data)
 result=dict(baseline=baseline,start_source_sha256=start_hashes,END=proc.returncode if proc else None,pid=proc.pid if proc else None,reason=reason,test_ids=ids,run=str(run),bytes=usage(),source_sha256={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [repo/'tools/coordinator-runtime/coordinator_runtime'/n for n in ['cleanup.py','store.py','report_repair.py']]},sdk5={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sdk.iterdir()},private_TMPDIR_before_imports=True,network_isolated=True,kernel_readonly_actual_source_and_sdk5=True)
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result));print(data.decode(errors='replace'))
raise SystemExit(result['END'] if result['END'] is not None else 1)
