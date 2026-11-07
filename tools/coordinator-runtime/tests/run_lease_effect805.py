import os, pathlib, subprocess, json, time, signal
repo=pathlib.Path(__file__).resolve().parents[3]
base=pathlib.Path(os.environ.get('LEASE_EFFECT805_FIXTURES','/tmp/lease-effect805-fixtures'));base.mkdir(mode=0o700,exist_ok=True)
size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if size>=128*1024**2:raise SystemExit('stop-new128MiB')
run=base/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700)
src=run/'src';src.mkdir();fixtures=run/'fixtures';fixtures.mkdir(mode=0o700);(fixtures/'tmp').mkdir(mode=0o700)
paths=subprocess.run(['git','-C',str(repo),'ls-files','tools/coordinator-runtime'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/test_lease_effect805.py']
paths += ['tools/message-board/'+n+'.py' for n in ('board_store','catalog','retention','active_listener','queue_transport')]
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
if os.environ.get('LEASE_EFFECT805_REPRODUCE') == '1':
 p=src/'tools/coordinator-runtime/coordinator_runtime/prospective.py'
 p.write_text(p.read_text().replace(
  "expires = selection['expires'] if ordinary_effects and policy['ordinary_effects'] else (lease_expiry(store, row) or selection['expires'])",
  "expires = lease_expiry(store, row) or selection['expires']"))
# Declared inherited fixture adaptation, matching793 frozen-task basis repair.
p=src/'tools/coordinator-runtime/tests/test_source_continuity688.py'
s=p.read_text().replace('transition = dict(basis=dict(release=self.old_release,','transition = dict(basis=dict(release=self.old_release, tasks=self.config[\'tasks\'],')
p.write_text(s)
ids=['test_lease_effect805.Isolation.test_actual_source_sdk5_and_snapshot_are_readonly',
 'test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied',
 'test_lease_effect805.EffectLease.test_expired_effect_refuses_before_body_with_framework_current',
 'test_lease_effect805.AdmittedLease.test_expired_effect_refuses_before_body_with_framework_current',
 'test_owner_lease797.OwnerLease.test_public_cutoff_continuation_whole_original_and_control_once',
 'test_owner_lease797.OwnerLease.test_stop_budget_and_original_policies_never_reset']
if os.environ.get('LEASE_EFFECT805_REPRODUCE') == '1':
 ids=[i for i in ids if '.EffectLease.' in i or '.AdmittedLease.' in i]
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
result=dict(reproduction=os.environ.get('LEASE_EFFECT805_REPRODUCE') == '1',run=str(run),END=end,pid=proc.pid if proc else None,timeout=reason,cumulative_bytes=size,tests=ids,readonly_src=True,network_isolated=True,private_TMPDIR_before_imports=True)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(cap.read_text()[-23000:])
if size>=192*1024**2:raise SystemExit('cumulative192MiB')

raise SystemExit(end if end is not None else 1)
