"""Offline tracked-public-source runner. Every output/fixture is retained."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

repo=Path(__file__).resolve().parents[3]
base=Path('/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/owner-intake-continuation-correction1008/verification')
if len(sys.argv)>1 and Path(sys.argv[1]) != base:
    raise SystemExit('exact assigned verification leaf only')
# All held namespaces are outside the only admitted roots. Reject before any
# metadata, and copy tracked PUBLIC tool sources only, never captures or logs.
def admitted(path):
    if not (path.is_relative_to(repo/'tools') or path.is_relative_to(base)):
        raise RuntimeError('outside exact public source or assigned verification roots')
    if any(p in {'runs','captures','WORK_LOG.md','AGENTS.md','__pycache__'} for p in path.parts):
        raise RuntimeError('excluded before metadata')
    return path

admitted(base).mkdir(parents=True,exist_ok=True,mode=0o700)
if os.statvfs(base).f_bavail*os.statvfs(base).f_frsize < 256*1024**2:
    raise SystemExit('insufficient output filesystem headroom')
run=admitted(base/('attempt-'+str(time.time_ns())));run.mkdir(mode=0o700)
src=run/'src';src.mkdir()
paths=subprocess.run(['git','-C',str(repo),'ls-files','--','tools/coordinator-runtime'],
    stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/'+n for n in ('test_future_software1008.py','run_future_software1008.py')]
paths += ['tools/message-board/'+n+'.py' for n in ('board_store','catalog','active_listener','queue_transport')]
paths += ['tools/direct-child/execution_pool.py','tools/operational_contracts.py','tools/branch_release.py']
manifest={};total=0
for rel in dict.fromkeys(paths):
    if Path(rel).name in {'WORK_LOG.md','AGENTS.md'}:continue
    origin=admitted(repo/rel)
    if origin.is_symlink() or not origin.is_file():raise RuntimeError('tracked public source unavailable')
    body=origin.read_bytes();total+=len(body)
    if len(body)>2*1024**2 or total>32*1024**2:raise RuntimeError('public fixture source budget')
    target=src/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
    manifest[rel]=hashlib.sha256(body).hexdigest()
sdk=src/'tools/coordinator-runtime/tests/fixture_snapshot'
for name in ('active_listener.py','queue_transport.py','catalog.py','board_store.py'):
    (sdk/name).write_bytes((src/'tools/message-board'/name).read_bytes())
(src/'tools/message-board/retention.py').write_bytes((sdk/'retention.py').read_bytes())
pins=dict(original={},candidate={})
for rel in paths:
    if Path(rel).parent != Path('tools/coordinator-runtime/coordinator_runtime') or not rel.endswith('.py'):continue
    body=subprocess.run(['git','-C',str(repo),'show','70425363481033cbcd9efb2caa190ca28140d444:'+rel],
                        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout
    pins['original'][Path(rel).name]=hashlib.sha256(body).hexdigest()
    pins['candidate'][Path(rel).name]=manifest[rel]
(run/'production-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(run/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
fixtures=run/'fixtures';(fixtures/'tmp').mkdir(parents=True)
argv=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
for p in ('/usr','/lib','/lib64','/bin'):argv+=['--ro-bind',p,p]
argv+=['--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src','--ro-bind',str(sdk),'/sdk',
       '--ro-bind',str(run/'production-pins.json'),'/public/production-pins.json',
       '--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',
    QA629_FIXTURES='/fixtures',COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',
    PYTHONPATH='/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():argv+=['--setenv',k,v]
ids=sys.argv[2:] or ['test_future_software1008']
argv+=['--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v',*ids]
start=time.monotonic()
try:
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
    data=result.stdout;record=dict(END=result.returncode,timeout=False)
except subprocess.TimeoutExpired as exc:
    data=exc.stdout or b'';record=dict(END=None,timeout=True,meaning='owned subprocess killed and waited by subprocess.run')
record.update(seconds=time.monotonic()-start,tests=ids,source_manifest=str(run/'source-manifest.json'),
    output_bytes=len(data),output_complete=len(data)<=524288,network_isolated=True,private_stores_mounted=False,
    fixture_deletion=False,public_source_bytes=total,argv=argv)
(run/'output.txt').write_bytes(data[:524288]);(run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(result=str(run/'result.json'),**{k:v for k,v in record.items() if k!='argv'})))
print(data[-22000:].decode(errors='replace'))
raise SystemExit(0 if record['END']==0 else 1)
