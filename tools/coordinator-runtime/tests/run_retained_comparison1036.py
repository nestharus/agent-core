"""Exact owned offline qualification. No actual config, caller, SDK or journal."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

repo=Path(__file__).resolve().parents[3]
base=Path('/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/retained-comparison-correction1036/qualification')
base.mkdir(parents=True,exist_ok=True)
run=base/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700)
src=run/'src';src.mkdir()
result=subprocess.run(['git','-C',str(repo),'ls-files','--','tools/coordinator-runtime'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True)
paths=result.stdout.splitlines()+['tools/coordinator-runtime/coordinator_runtime/retained_comparison.py','tools/coordinator-runtime/tests/test_retained_comparison1036.py','tools/coordinator-runtime/tests/run_retained_comparison1036.py']
manifest={}
for name in dict.fromkeys(paths):
    p=Path(name)
    if any(k in {'AGENTS.md','WORK_LOG.md','runs','captures','__pycache__'} for k in p.parts):
        raise SystemExit('unexpected excluded tracked source')
    source=repo/p
    if source.is_symlink() or not source.is_file():
        raise SystemExit('selected source unavailable; no fallback')
    body=source.read_bytes()
    target=src/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
    manifest[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
(run/'source.json').write_text(json.dumps(manifest,indent=2)+'\n')
fixtures=run/'fixtures';(fixtures/'tmp').mkdir(parents=True)
argv=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
for p in ('/usr','/lib','/lib64','/bin'):
    argv+=['--ro-bind',p,p]
argv+=['--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src','--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--clearenv',
       '--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/fixtures','--setenv','TMPDIR','/fixtures/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1',
       '--setenv','PYTHONPATH','/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests',
       '--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v','test_retained_comparison1036']
try:
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    output=result.stdout;code=result.returncode
except subprocess.TimeoutExpired as e:
    output=e.stdout or b'';code=None
(run/'output.txt').write_bytes(output)
record=dict(test_returncode=code,output_bytes=len(output),argv=argv,source=str(run/'source.json'),
            overlays=[],actual_journal=False,providers=False,cleanup='KEEP actual processing completion +24h AND all holds; no deletion')
(run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(result=str(run/'result.json'),test_returncode=code,output_bytes=len(output))))
print(output.decode(errors='replace')[-12000:])
raise SystemExit(0 if code==0 else 1)
