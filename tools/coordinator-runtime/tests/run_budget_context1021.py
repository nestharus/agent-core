"""Bounded offline runner; all generated files stay under one explicit owned leaf."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

repo = Path(__file__).resolve().parents[3]
base = Path(sys.argv[1])
expected = Path('/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/budget-context-correction1021/verification')
if base != expected:
    raise SystemExit('exact assigned verification leaf required')
# Live operational configuration is outside this Maker's acquisition scope.
# Source acquisition uses a closed positive root and output uses this exact leaf;
# that stronger boundary excludes ALL inherited 71 held namespaces before metadata.
# The native fixture's 71-entry policy is explicitly fictional, not live pins.
bounds = ['/fictional-held-boundary1021/'+str(i) for i in range(71)]

def admitted(path):
    if path == base or path.is_relative_to(base):
        return path
    if path.is_relative_to(repo/'tools/coordinator-runtime') or path in {
        *[repo/('tools/message-board/'+n+'.py') for n in ('board_store','catalog','active_listener','queue_transport')],
        repo/'tools/direct-child/execution_pool.py',repo/'tools/operational_contracts.py',repo/'tools/branch_release.py',
        Path('/opt/oulipoly-native/oulipoly-native-linux-x86_64-ba440a4c3368-de23d83ac522/bin/oulipoly-native-call')}:
        return path
    raise RuntimeError('outside exact public source/output scope before metadata')

admitted(base).mkdir(mode=0o700, parents=True, exist_ok=True)
if os.statvfs(base).f_bavail*os.statvfs(base).f_frsize < 256*1024**2 or os.statvfs(base).f_favail < 30000:
    raise SystemExit('insufficient owned output filesystem headroom')
run = admitted(base/('attempt-'+str(time.time_ns())))
run.mkdir(mode=0o700)
src = run/'src'
src.mkdir()
result = subprocess.run(['git','-C',str(repo),'ls-files','--','tools/coordinator-runtime'],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True)
paths = result.stdout.splitlines() + [
    'tools/coordinator-runtime/tests/test_native_footprint985.py',
    'tools/coordinator-runtime/tests/run_native_footprint985.py',
    'tools/coordinator-runtime/tests/test_retained_source995.py',
    'tools/coordinator-runtime/tests/run_retained_source995.py',
    'tools/coordinator-runtime/tests/test_source_duty1009.py',
    'tools/coordinator-runtime/tests/run_source_duty1009.py',
    'tools/coordinator-runtime/tests/test_integration1012.py',
    'tools/coordinator-runtime/tests/run_integration1012.py',
    'tools/coordinator-runtime/tests/test_future_boundaries1014.py',
    'tools/coordinator-runtime/tests/run_future_boundaries1014.py',
    *['tools/message-board/'+p for p in ('board_store.py','catalog.py','active_listener.py','queue_transport.py')],
    'tools/direct-child/execution_pool.py','tools/operational_contracts.py','tools/branch_release.py']
manifest = {}
total = 0
for rel in dict.fromkeys(paths):
    parts = Path(rel).parts
    if any(p in {'AGENTS.md','WORK_LOG.md','runs','captures','__pycache__'} for p in parts):
        continue
    source = admitted(repo/rel)
    if rel.startswith('tools/coordinator-runtime/'):
        if source.is_symlink() or not source.is_file():
            raise RuntimeError('selected tracked public source unavailable')
        body = source.read_bytes()
    else:
        body = subprocess.run(['git','-C',str(repo),'show','HEAD:'+rel],
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True).stdout
    if len(body) > 2*1024*1024:
        raise RuntimeError('individual public source bound exceeded')
    total += len(body)
    if total > 33554432: raise RuntimeError('bounded selected public source budget exceeded')
    target = src/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(body)
    manifest[rel] = hashlib.sha256(body).hexdigest()
# Same explicit SDK5 fixture composition used by the existing offline runners.
sdk = src/'tools/coordinator-runtime/tests/fixture_snapshot'
for name in ('active_listener.py','queue_transport.py','catalog.py','board_store.py'):
    (sdk/name).write_bytes((src/'tools/message-board'/name).read_bytes())
(src/'tools/message-board/retention.py').write_bytes((sdk/'retention.py').read_bytes())
public = Path('/opt/oulipoly-native/oulipoly-native-linux-x86_64-ba440a4c3368-de23d83ac522/bin/oulipoly-native-call')
body = admitted(public).read_bytes()
assert len(body) == 76690 and hashlib.sha256(body).hexdigest() == '7d8be231fbdee40761128b07b969244b7c799220190858cfc57b0cb97f3616b5'
(run/'caller.py').write_bytes(body)
(run/'exclusions.json').write_text(json.dumps(bounds)+'\n')
(run/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(run/'fixture-overlays.json').write_text(json.dumps({str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*[sdk/n for n in ('active_listener.py','queue_transport.py','catalog.py','board_store.py')],src/'tools/message-board/retention.py']},indent=2)+'\n')
# Exact original704 module bytes, scoped to tracked public production sources.
original_pins = {}
candidate_pins = {}
for rel in paths:
    if Path(rel).parent != Path('tools/coordinator-runtime/coordinator_runtime') or not rel.endswith('.py'):
        continue
    baseline = subprocess.run(['git','-C',str(repo),'show','70425363481033cbcd9efb2caa190ca28140d444:'+rel],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout
    original_pins[Path(rel).name] = hashlib.sha256(baseline).hexdigest()
    candidate_pins[Path(rel).name] = manifest[rel]
(run/'production-pins.json').write_text(json.dumps(dict(original=original_pins,candidate=candidate_pins),indent=2)+'\n')
label = sys.argv[2] if len(sys.argv)>2 else 'combined'
groups = {
    'combined': ['test_integration1012'],
    'fresh': ['test_future_boundaries1014'],
    'context': ['test_budget_context1021'],
    'publication': ['test_budget_context1021.Context1021.'+name for name in (
        'test_real_routine_staging_and_backup_reconcile_outside_transaction',
        'test_backup_real_byte_limit_keeps_stages_original_and_debt',
        'test_backup_original_epoch_keeps_collected_result_stages_and_preimages')],
    'final': ['test_budget_context1021','test_future_boundaries1014','test_integration1012',
        'test_future_software1008','test_source_duty1009',
        'test_source_continuity688.Continuity.test_exact_eight_module_ceiling_accepts_local_integration_and_store',
        'test_source_continuity688.Continuity.test_exact_delta_does_not_expand_modules_location_pool_or_dependencies'],
    'affected': ['test_future_software1008', 'test_source_duty1009',
        'test_source_continuity688.Continuity.test_exact_eight_module_ceiling_accepts_local_integration_and_store',
        'test_source_continuity688.Continuity.test_exact_delta_does_not_expand_modules_location_pool_or_dependencies'],
}
fixtures=run/'fixtures';(fixtures/'tmp').mkdir(parents=True)
argv=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
for p in ('/usr','/lib','/lib64','/bin'):
    argv += ['--ro-bind',p,p]
argv += ['--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src','--ro-bind',str(src),'/actualsrc',
         '--ro-bind',str(sdk),'/sdk','--ro-bind',str(run/'caller.py'),'/public/caller.py',
         '--ro-bind',str(run/'exclusions.json'),'/public/exclusions.json',
         '--ro-bind',str(run/'production-pins.json'),'/public/production-pins.json',
         '--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',
                QA629_FIXTURES='/fixtures',COORDINATOR_ORDINARY_FIXTURES='/fixtures/ordinary-effects33',COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',
                PYTHONPATH='/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():
    argv += ['--setenv',k,v]
argv += ['--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v',*groups[label]]
started=time.monotonic()
try:
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900)
    data=result.stdout
    record=dict(label=label,END=result.returncode,seconds=time.monotonic()-started,timeout=False)
except subprocess.TimeoutExpired as exc:
    data=exc.stdout or b''
    record=dict(label=label,END=None,seconds=time.monotonic()-started,timeout=True,
                meaning='subprocess.run killed and waited its owned child; test outcome incomplete')
record.update(output_bytes=len(data),output_complete=len(data)<=524288,argv=argv,
              source_manifest=str(run/'source-manifest.json'),exclusions=71)
(run/'output.txt').write_bytes(data[:524288])
(run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(report=str(run/'result.json'),output=str(run/'output.txt'),**{k:v for k,v in record.items() if k!='argv'})))
print(data.decode(errors='replace') if len(data)<=22000 else 'Display omitted; full bounded output retained at '+str(run/'output.txt'))
raise SystemExit(0 if record['END']==0 else 1)
