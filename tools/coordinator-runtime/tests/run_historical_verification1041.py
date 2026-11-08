"""Owned offline qualification; pinned tracked input only, no installed caller."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

repo = Path(__file__).resolve().parents[3]
base = Path('/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/existing-historical-verification-correction1041/qualification')
base.mkdir(parents=True,exist_ok=True)
run = base/('attempt-'+str(time.time_ns()))
run.mkdir(mode=0o700)
src = run/'src'
src.mkdir()
pin = 'db1d4fca18f9dfacc65b5a6b2e64359be562327a'
listing = subprocess.run(['git','-C',str(repo),'ls-tree','-r','--name-only',pin,'--','tools/coordinator-runtime'],
                         stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout.decode().splitlines()
own = ['tools/coordinator-runtime/coordinator_runtime/historical_verification.py',
       'tools/coordinator-runtime/tests/run_historical_verification1041.py',
       'tools/coordinator-runtime/tests/test_historical_verification1041.py',
       'tools/coordinator-runtime/historical-verification1041.md']
dependencies = ['tools/direct-child/execution_pool.py','tools/operational_contracts.py','tools/branch_release.py',
                'tools/direct-child/dispatch.py','tools/direct-codex-child/launch.sh',
                *['tools/message-board/'+name for name in ('board_store.py','catalog.py','active_listener.py','queue_transport.py','managed_owner.py')]]
baseline = '--baseline' in sys.argv
manifest = {}
for rel in list(dict.fromkeys(listing+own+dependencies)):
    if any(p in {'AGENTS.md','WORK_LOG.md','runs','captures','__pycache__'} for p in Path(rel).parts):
        raise RuntimeError('unadmitted source member')
    if rel in dependencies or baseline and rel in listing:
        body = subprocess.run(['git','-C',str(repo),'show',pin+':'+rel],stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,check=True).stdout
    else:
        path = repo/rel
        if path.is_symlink():
            raise RuntimeError('source alias refused')
        body = path.read_bytes()
    if len(body)>2*1024*1024:
        raise RuntimeError('public source size ceiling')
    target=src/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(body)
    manifest[rel] = dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
(run/'source.json').write_text(json.dumps(manifest,indent=2)+'\n')
fixtures=run/'fixtures'
(fixtures/'tmp').mkdir(parents=True)
tests = [arg for arg in sys.argv[1:] if arg!='--baseline'] or ['test_historical_verification1041']
argv=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
for p in ('/usr','/bin','/lib','/lib64'):
    argv += ['--ro-bind',p,p]
argv += ['--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src','--bind',str(fixtures),'/fixtures',
         '--dir','/tmp','--dir','/home','--clearenv']
environment=dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',
                 PYTHONPATH='/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests',
                 COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board', QA629_FIXTURES='/fixtures',
                 COORDINATOR_ORDINARY_FIXTURES='/fixtures/ordinary-effects33')
for key,value in environment.items():
    argv += ['--setenv',key,value]
argv += ['--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v',*tests]
started=time.monotonic()
try:
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
    data=result.stdout
    record=dict(END=result.returncode,timeout=False)
except subprocess.TimeoutExpired as exc:
    data=exc.stdout or b''
    record=dict(END=None,timeout=True,meaning='owned subprocess killed and waited; qualification incomplete')
record.update(seconds=time.monotonic()-started,tests=tests,output_bytes=len(data),output_complete=len(data)<=262144,
              disposition='KEEP: actual processing+24h AND all holds',source=str(run/'source.json'),overlays=[],
              dependency_pin=pin,source_files=len(manifest),provider=False,
              mode='accepted-baseline' if baseline else 'candidate')
(run/'output.txt').write_bytes(data[:262144])
(run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(result=str(run/'result.json'),**record)))
print(data[-12000:].decode(errors='replace'))
raise SystemExit(0 if record['END']==0 else 1)
