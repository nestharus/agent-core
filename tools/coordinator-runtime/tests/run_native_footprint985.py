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
expected = Path('/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/native-source-footprint-correction985/verification/isolated985')
if base != expected:
    raise SystemExit('exact assigned verification leaf required')
bounds = json.loads(Path('/home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/ordinary-adoption781/ORDINARY-CONTROLLER704-CASE928-954-CONFIG.json').read_text())['artifact_exclusions']
assert len(bounds) == 71

def admitted(path):
    if any(path == Path(p) or path.is_relative_to(Path(p)) or Path(p).is_relative_to(path) for p in bounds):
        raise RuntimeError('excluded before source/fixture metadata')
    return path

admitted(base).mkdir(mode=0o700, parents=True, exist_ok=True)
run = admitted(base/('attempt-'+str(time.time_ns())))
run.mkdir(mode=0o700)
src = run/'src'
src.mkdir()
result = subprocess.run(['git','-C',str(repo),'ls-files','--','tools/coordinator-runtime'],
    capture_output=True, text=True, check=True)
paths = result.stdout.splitlines() + [
    'tools/coordinator-runtime/tests/test_native_footprint985.py',
    'tools/coordinator-runtime/tests/run_native_footprint985.py',
    *['tools/message-board/'+p for p in ('board_store.py','catalog.py','active_listener.py','queue_transport.py')],
    'tools/direct-child/execution_pool.py','tools/operational_contracts.py','tools/branch_release.py']
manifest = {}
for rel in dict.fromkeys(paths):
    parts = Path(rel).parts
    if any(p in {'AGENTS.md','WORK_LOG.md','runs','captures','__pycache__'} for p in parts):
        continue
    source = admitted(repo/rel)
    if source.is_symlink() or not source.is_file():
        raise RuntimeError('selected tracked public source unavailable')
    body = source.read_bytes()
    if len(body) > 2*1024*1024:
        raise RuntimeError('individual public source bound exceeded')
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
label = sys.argv[2] if len(sys.argv)>2 else 'focused'
groups = {
    'focused':['test_native_footprint985'],
    'regression':['test_native_preflight826.Preflight.test_orphan_lease_refuses_before_all_protected_reads',
                  'test_native_preflight826.Preflight.test_mapped_root_refuses_before_all_protected_reads',
                  'test_native_return820.NativeReturn.test_whole_native_return_and_real_integrator_transport',
                  'test_native_return820.NativeReturn.test_stale_held_uncollected_forged_method_and_orphan_refuse',
                  'test_native_reacquisition836.Reacquisition836.test_public_frozen_retry_after_pool_failure_refuses_before_body',
                  'test_native_reacquisition836.Reacquisition836.test_async_preparation_after_start_refuses_before_body',
                  'test_native_reacquisition836.Reacquisition836.test_spawned_preparation_after_start_refuses_before_body',
                  'test_unpackaged_native889.Unpackaged889.test_original_source_identity_and_epoch_refuse',
                  'test_ref_resources749','test_conserved_conflict756',
                  'test_retention_guards837.Retention837.test_direct_exclusion_and_new_hold_during_hash',
                  'test_retention_guards837.Retention837.test_original_identity_symlink_hardlink_hash_and_custody_fences',
                  'test_native331'],
}
groups['ordinary-retry']=['test_ref_resources749']
groups['ordinary-baseline']=[
 'test_ordinary_effects.OrdinaryEffects.'+n for n in [
 'test_QA_five_plus_one_and_recurring_alerts_remain',
 'test_dispatcher_uses_owned_tools_after_collected_preparation',
 'test_actual_git_CAS_capture_readback_and_independent_acceptance',
 'test_actual_delegated_callback_consumes_known_failed_reporting',
 'test_owned_CI_API_seam_matches_exact_run_event_jobs',
 'test_qualification_requires_real_acceptance_and_fresh_ref',
 'test_real_QA_failure_can_finish_reporting_but_cannot_be_accepted']
] + ['test_ref_resources749.RefResources.test_QA_five_plus_one_and_recurring_alerts_remain']
if label == 'ordinary-baseline':
    for name in ('resource_scopes.py','reviews.py'):
        rel='tools/coordinator-runtime/coordinator_runtime/'+name
        result=subprocess.run(['git','-C',str(repo),'show','70425363481033cbcd9efb2caa190ca28140d444:'+rel],
                              stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=True)
        (src/rel).write_bytes(result.stdout)
        manifest[rel]=hashlib.sha256(result.stdout).hexdigest()
    (run/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
fixtures=run/'fixtures';(fixtures/'tmp').mkdir(parents=True)
argv=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
for p in ('/usr','/lib','/lib64','/bin'):
    argv += ['--ro-bind',p,p]
argv += ['--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src','--ro-bind',str(src),'/actualsrc',
         '--ro-bind',str(sdk),'/sdk','--ro-bind',str(run/'caller.py'),'/public/caller.py',
         '--ro-bind',str(run/'exclusions.json'),'/public/exclusions.json',
         '--bind',str(fixtures),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',PYTHONDONTWRITEBYTECODE='1',
                QA629_FIXTURES='/fixtures',COORDINATOR_ORDINARY_FIXTURES='/fixtures/ordinary-effects33',COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',
                PYTHONPATH='/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():
    argv += ['--setenv',k,v]
argv += ['--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v',*groups[label]]
started=time.monotonic()
try:
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
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
print(data[-9000:].decode(errors='replace'))
raise SystemExit(0 if record['END']==0 else 1)
