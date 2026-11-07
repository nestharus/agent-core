import pathlib,subprocess,hashlib,json,os,sys,time,selectors
repo=pathlib.Path(os.environ.get('QUALIFICATION794_SOURCE','/home/nes/ai-worktrees/WORK-48847-control-report-qualify794'))
root=pathlib.Path('/tmp/control-report-authentic794');root.mkdir(mode=0o700,exist_ok=True)
usage=sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
if usage>=128*1024*1024:raise RuntimeError('stop-new-fixtures threshold')
run=root/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700);src=run/'src';src.mkdir();fixtures=run/'fixtures';fixtures.mkdir();(fixtures/'tmp').mkdir()
# Tracked, allowlisted sources only. No forbidden checkout documents or captures.
p=subprocess.run(['git','--git-dir=/home/nes/ai/.git','ls-tree','-r','--name-only','a5da5a0f1802b9a410f5aa0be1f050fb6b4acaa1','tools/coordinator-runtime','tools/message-board','tools/direct-child','tools/direct-codex-child','tools/branch_release.py','tools/operational_contracts.py'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
paths=[]
for name in p.stdout.splitlines():
 parts=pathlib.PurePosixPath(name).parts
 if any(s in {'AGENTS.md','WORK_LOG.md','runs','captures'} for s in parts):continue
 if name.endswith('.py') or name in ['tools/coordinator-runtime/coordinator','tools/coordinator-runtime/templates/coordinator-receive.md','tools/coordinator-runtime/final-release-risk.md','tools/direct-codex-child/launch.sh']:
  paths.append(name)
paths.append('tools/coordinator-runtime/tests/test_authentic_control794.py')
for name in paths:
 dest=src/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((repo/name).read_bytes())
if os.environ.get('QUALIFICATION794_BASE_RED')=='1':
 name='tools/coordinator-runtime/coordinator_runtime/processing.py'
 original=subprocess.run(['git','--git-dir=/home/nes/ai/.git','show','a5da5a0f1802b9a410f5aa0be1f050fb6b4acaa1:'+name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True)
 (src/name).write_bytes(original.stdout)
# SDK exact five-file dependency closure, separate immutable retention fixture.
for name in ['active_listener.py','board.py','board_store.py','catalog.py','queue_transport.py']:
 (src/'tools/coordinator-runtime/tests/fixture_snapshot'/name).write_bytes((repo/'tools/message-board'/name).read_bytes())
old={}
for file in (src/'tools/coordinator-runtime/coordinator_runtime').glob('*.py'):
 name='tools/coordinator-runtime/coordinator_runtime/'+file.name
 p=subprocess.run(['git','--git-dir=/home/nes/ai/.git','show','23773e6bfe46a2d71e8fc1dbfc38b1e60729331f:'+name],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 if p.returncode:raise RuntimeError('old module unavailable')
 old[file.name]=hashlib.sha256(p.stdout).hexdigest()
(src/'old-implementation794.json').write_text(json.dumps(old))
import shutil
oldsrc=run/'oldsrc';shutil.copytree(src,oldsrc)
for name in old:
 rel='tools/coordinator-runtime/coordinator_runtime/'+name
 result=subprocess.run(['git','--git-dir=/home/nes/ai/.git','show','23773e6bfe46a2d71e8fc1dbfc38b1e60729331f:'+rel],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 (oldsrc/rel).write_bytes(result.stdout)

ids=[n if '.' in n else 'test_authentic_control794.Authentic794.'+n for n in sys.argv[1:]]
if not ids:ids=['test_authentic_control794.Authentic794.test_positive_actual_pair_and_distinct_applier','test_authentic_control794.Authentic794.test_negative_metadata_matrix_atomic_before_bodies','test_authentic_control794.Authentic794.test_negative_full_bytes_and_expiry_atomic','test_authentic_control794.Authentic794.test_negative_original_chain_and_request_pins','test_authentic_control794.Authentic794.test_closed_actual_source_delta_and_v1_limits','test_authentic_control794.Authentic794.test_stale_between_groups_rolls_back_without_wrong_body','test_authentic_control794.Kernel794.test_source_and_sdk_snapshots_readonly','test_authentic_control794.Authentic794.test_return_failure_rolls_back_resolution_and_child']
cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/','--proc','/proc','--dev','/dev']
for path in ['/usr','/lib','/lib64','/bin']:
 if pathlib.Path(path).exists():cmd+=['--ro-bind',path,path]
cmd+=['--ro-bind',str(src),'/src','--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--setenv','HOME','/fixtures','--setenv','TMPDIR','/fixtures/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','PYTHONPATH','/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests','--setenv','QA629_FIXTURES','/fixtures','--setenv','COORDINATOR_TEST_BOARD_LIBRARY','/src/tools/message-board','--chdir','/src/tools/coordinator-runtime/tests','/usr/bin/python3','-B','-m','unittest','-v',*ids]
# Create each original with the actual immutable old source mounted at /src.
producer=cmd[:cmd.index('/usr/bin/python3')]
producer[producer.index(str(src))]=str(oldsrc)
producer+=['--setenv','PHASE794','produce','/usr/bin/python3','-B','-c',
 'import unittest; from test_authentic_control794 import Authentic794; names='+repr([i.rsplit('.',1)[1] for i in ids if '.Authentic794.' in i])+'; '+
 '\nfor name in names:\n case=Authentic794(name)\n try: case.setUp()\n finally: case.doCleanups()']
producer_child=subprocess.Popen(producer,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
producer_data=bytearray();producer_deadline=time.monotonic()+180
producer_selector=selectors.DefaultSelector();producer_selector.register(producer_child.stdout,selectors.EVENT_READ)
try:
 while producer_selector.get_map():
  if time.monotonic()>producer_deadline:producer_child.kill()
  for key,_ in producer_selector.select(.1):
   chunk=os.read(key.fd,65536)
   if not chunk:producer_selector.unregister(key.fd);continue
   if len(producer_data)+len(chunk)>4*1024*1024:producer_child.kill();chunk=chunk[:max(0,4*1024*1024-len(producer_data))]
   producer_data.extend(chunk)
finally:
 if producer_child.poll() is None:producer_child.kill()
 producer_child.wait();output=bytes(producer_data)
(run/'producer-output.txt').write_bytes(output[:4*1024*1024])
(run/'producer-collection.json').write_text(json.dumps(dict(END=producer_child.returncode,pid=producer_child.pid,output_bytes=len(output))))
if producer_child.returncode:
 print('PRODUCER END',producer_child.returncode);print(output.decode(errors='replace')[-14000:]);sys.exit(1)
cmd[cmd.index('/usr/bin/python3'):cmd.index('/usr/bin/python3')]=['--setenv','PHASE794','consume']
# Only newly owned root is counted. Refuse new fixtures at 128MiB.
usage=sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
if usage>=128*1024*1024:raise RuntimeError('stop-new-fixtures threshold')
child=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True);data=bytearray();deadline=time.monotonic()+180;reason=None
sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ)
try:
 while sel.get_map():
  if time.monotonic()>deadline:reason='180s timeout';child.kill()
  for key,_ in sel.select(.1):
   block=os.read(key.fd,65536)
   if not block:sel.unregister(key.fd);continue
   if len(data)+len(block)>4*1024*1024:reason='4MiB capture limit';child.kill();block=block[:max(0,4*1024*1024-len(data))]
   data.extend(block)
finally:
 if child.poll() is None:child.kill()
 end=child.wait();(run/'output.txt').write_bytes(data)
 usage=sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
 record=dict(child_pid=child.pid,END=end,reason=reason,exact_ids=ids,output_bytes=len(data),owned_total_bytes=usage,below128MiB=usage<128*1024*1024,below192MiB=usage<192*1024*1024,run=str(run))
 (run/'collection.json').write_text(json.dumps(record,indent=2));print(json.dumps(record));print(data.decode(errors='replace')[-18000:])
