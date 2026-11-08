"""Owned immutable Git snapshots, SDK5, isolated children and retained numeric ENDs."""
import ast
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

repo = Path(__file__).resolve().parents[3]
base = repo / '.qualification862-qualified'
base.mkdir(mode=0o700, exist_ok=False)
def usage():
    return sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if usage() >= 128*1024**2:
    raise SystemExit('stop-new128MiB')
root = base / 'candidate'
root.mkdir(mode=0o700)
src = root/'src'
src.mkdir()
def git(*args):
    return subprocess.run(['git','-C',str(repo),*args],check=True,
                          stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout
head = git('show','--no-patch','--format=%H','HEAD').decode().strip()
source = git('show','--no-patch','--format=%H %T %P','HEAD').decode().strip()
paths = git('ls-tree','-r','--name-only',head,'--','tools/coordinator-runtime',
            'tools/message-board','tools/direct-child','tools/direct-codex-child',
            'tools/branch_release.py','tools/operational_contracts.py').decode().splitlines()
manifest = {}
for rel in paths:
    if any(p in {'AGENTS.md','WORK_LOG.md','runs','captures'} for p in Path(rel).parts):
        continue
    if not (rel.endswith('.py') or rel.endswith('/coordinator') or rel.endswith('/launch.sh')
            or rel in ['tools/coordinator-runtime/final-release-risk.md',
                       *['tools/coordinator-runtime/templates/'+name+'.md' for name in
                         ('work-catalog','branch-repository','reviews-selected','qa-package')]]
            or rel.endswith('/coordinator-receive.md')):
        continue
    data = git('show',head+':'+rel)
    target = src/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
    manifest[rel] = hashlib.sha256(data).hexdigest()
sdk = src/'tools/coordinator-runtime/tests/fixture_snapshot'
for name in ['active_listener.py','queue_transport.py','catalog.py','board_store.py']:
    (sdk/name).write_bytes((src/'tools/message-board'/name).read_bytes())
(src/'tools/message-board/retention.py').write_bytes((sdk/'retention.py').read_bytes())
sdk_hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
              [sdk/n for n in ['active_listener.py','queue_transport.py','catalog.py','board_store.py','retention.py']]}
records=[]
(root/'snapshot.json').write_text(json.dumps(dict(source=source,sha256=manifest,sdk5=sdk_hashes),indent=2))

groups = {
 'scope': ['test_control_scope862.Scope862.'+name for name in [
  'test_unresolved_cli_consumption_preserves_original_classifier_lineages',
  'test_unresolved_negatives_before_any_body',
  'test_basis_and_disposition_exclude_old_unselected_birth_before_body',
  'test_whole_return_mutation_refuses_without_rewriting_original_result',
  'test_current_scope_completion_leaves_unrelated_held_source_whole']],
 'controls': ['test_plain_control821.Completion821.'+name for name in [
  'test_same869_shape_existing_return_cli_terminal_once_preserves_every_original',
  'test_pending_descendant_reserved_and_effect_consumers_refuse_before_source',
  'test_unknown_message_owned_and_stale_source_pins_block',
  'test_tool_metadata_and_binding_refuse_before_protected_body',
  'test_existing_return_mutation_fence_rolls_back']]
  + ['test_control_marker831.Marker831.test_marker_api_fresh_classifier_completion_replay',
     'test_plain_control817.Terminal817.test_kernel_closure'],
 'notifications': ['test_alert_phase340.Notifications.'+name for name in [
  'test_load_recurrence_full_occurrences_and_finite_consumer_work',
  'test_notification_consumption_does_not_create_business_return',
  'test_forgery_partial_control_and_missing_coverage_cannot_finish_notice',
  'test_unresolved_notification_interpretation_keeps_work_return']]
  + ['test_alert_phase340.Silence.test_zero_violations_produce_no_occurrence_or_notification'],
 'admission': ['test_reconcile_admission847.Reconcile847.'+name for name in [
  'test_periodic_orphan_after_original_collection',
  'test_admitted_later_reads_join_transaction']]}
(root/'fixture-plan.json').write_text(json.dumps(dict(groups=groups, source=source,
  purpose='Fresh synthetic current-control qualification only',
  limits=dict(child_seconds=180,capture_bytes=4*1024**2,stop_new=128*1024**2,hard=192*1024**2),
  cleanup='retain all fixtures, failures and collection records for genuine Work; no cleanup authorized'),indent=2))
for label in (sys.argv[1:] or list(groups)):
    if usage() >= 128*1024**2:
        print('stop-new128MiB',flush=True)
        break
    ids = groups[label]
    fixture = root/label
    (fixture/'tmp').mkdir(parents=True,mode=0o700)
    command=['bwrap','--die-with-parent','--unshare-all','--new-session','--tmpfs','/']
    for p in ['/usr','/lib','/lib64','/bin']:
        command += ['--ro-bind',p,p]
    command += ['--proc','/proc','--dev','/dev','--ro-bind',str(src),'/src',
                '--ro-bind',str(src),'/actualsrc','--ro-bind',str(sdk),'/sdk',
                '--bind',str(fixture),'/fixtures','--dir','/tmp','--dir','/home','--clearenv']
    for k,v in dict(PATH='/usr/bin:/bin',HOME='/fixtures',TMPDIR='/fixtures/tmp',
                    PYTHONDONTWRITEBYTECODE='1',QA629_FIXTURES='/fixtures',
                    CAPACITY48_FIXTURES='/fixtures/capacity48',
                    COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',
                    PYTHONPATH='/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():
        command += ['--setenv',k,v]
    overrides = {}
    command += ['--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v',*ids]
    child=None
    data=bytearray()
    reason=None
    started=time.monotonic()
    measured=started
    collector_exception=None
    try:
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        sel=selectors.DefaultSelector()
        sel.register(child.stdout,selectors.EVENT_READ)
        while sel.get_map():
            now=time.monotonic()
            if now-measured>1:
                measured=now
                if usage()+len(data)>=192*1024**2:
                    reason='aggregate192MiB'
            if now-started>180:
                reason='timeout180s'
            if reason and child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
            for key,_ in sel.select(.1):
                chunk=os.read(key.fd,65536)
                if not chunk:
                    sel.unregister(key.fd)
                    continue
                if len(data)+len(chunk)>4*1024**2:
                    reason='capture4MiB'
                data.extend(chunk[:max(0,4*1024**2-len(data))])
    except BaseException as exc:
        collector_exception=type(exc).__name__+': '+str(exc)
    finally:
        if child:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
            child.wait()
        (root/(label+'.txt')).write_bytes(data)
        record=dict(label=label,pid=child.pid if child else None,END=child.returncode if child else None,
                    reason=reason,collector_exception=collector_exception,argv=command,test_ids=ids,production_overrides=overrides,owned_bytes=usage())
        records.append(record)
        (root/'collection.json').write_text(json.dumps(records,indent=2))
        print(json.dumps(dict(root=str(root),source=source,**record)),flush=True)
        print(data.decode(errors='replace'),flush=True)
    if collector_exception or reason:
        break  # never retry an unknown admission/collection
print(json.dumps(dict(root=str(root),owned_bytes=usage(),all_children_collected=True)),flush=True)
raise SystemExit(0 if len(records)==len(sys.argv[1:] or groups) and all(r['END']==0 and not r['reason'] and not r['collector_exception'] for r in records) else 1)
