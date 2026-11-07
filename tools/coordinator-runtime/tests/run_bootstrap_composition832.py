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
base = repo / '.qualification832'
base.mkdir(mode=0o700, exist_ok=True)
def usage():
    return sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if usage() >= 128*1024**2:
    raise SystemExit('stop-new128MiB')
root = base / ('attempt-' + str(time.time_ns()))
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
# Authentic old822 implementation inventory, supplied by the closed827 runner.
tree = ast.parse((src/'tools/coordinator-runtime/tests/run_source_composition827.py').read_text())
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='write_text':
        if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
            value=node.args[0].value
            if value.startswith('{"__init__.py":'):
                (src/'original822.json').write_text(value)
                break
else:
    raise RuntimeError('missing exact closed old822 inventory')
records=[]
(root/'snapshot.json').write_text(json.dumps(dict(source=source,sha256=manifest,sdk5=sdk_hashes),indent=2))

groups = {
 'interaction': ['test_bootstrap_composition832.NativeToWork.test_native_whole_integrator_return_maps_real_work_point',
                 'test_bootstrap_composition832.CompositeAmendment.test_actual_composite_cli_all_changed_modules'],
 'native': ['test_native_preflight826.Preflight.'+n for n in
            ['test_orphan_lease_refuses_before_all_protected_reads','test_mapped_root_refuses_before_all_protected_reads',
             'test_native_singleton_transport_boundary']] +
           ['test_native_return820.NativeReturn.'+n for n in
            ['test_whole_native_return_and_real_integrator_transport','test_stale_held_uncollected_forged_method_and_orphan_refuse',
             'test_external_marker_and_incomplete_family_cannot_be_native']],
 'report': ['test_report_mapping825.Mapping825.'+n for n in
            ['test_delegated_new_completion_refuses_before_resolution','test_delegated_known_completion_and_packet_work',
             'test_genuine_outer_new_work_refuses_packet','test_genuine_outer_known_packet_works']] +
           ['test_report_leaf816.ReportLeaf816.'+n for n in
            ['test_collected_reviews_return_maps_known_work_point_preserving_originals',
             'test_metadata_wrong_cap_hold_birth_changed_hash_and_uncollected_before_body',
             'test_new_point_and_native_impersonation_remain_refused']],
 'control': ['test_plain_control821.Completion821.'+n for n in
            ['test_same869_shape_existing_return_cli_terminal_once_preserves_every_original',
             'test_automatic_delegated_collected_structured_scope_nonempty',
             'test_pending_descendant_reserved_and_effect_consumers_refuse_before_source',
             'test_tool_metadata_and_binding_refuse_before_protected_body']] +
            ['test_plain_control821.LeaseCompletion821.test_genuine_lease_control_terminal_raw_native_expiry_and_old_producer_conserved'],
 'source': ['test_source_composition827.GitComposition.test_exact_added_blobs_closure_dependencies_config_sdk_and_legacy',
            'test_source_amendment822.OutsideReview.test_self_forged_wrong_partial_uncollected_unreleased_and_changed_public_refuse',
            'test_source_amendment822.OutsideReview.test_collection_and_selection_mutation_fences_and_public_hashes',
            'test_authentic_control794.Kernel794.test_source_and_sdk_snapshots_readonly',
            'test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied']}
groups['composite'] = [test for tests in list(groups.values()) for test in tests]
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
                    COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',
                    PYTHONPATH='/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests').items():
        command += ['--setenv',k,v]
    command += ['--chdir','/fixtures','/usr/bin/python3','-B','-m','unittest','-v',*ids]
    child=None
    data=bytearray()
    reason=None
    started=time.monotonic()
    measured=started
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
    finally:
        if child:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
            child.wait()
        (root/(label+'.txt')).write_bytes(data)
        record=dict(label=label,pid=child.pid if child else None,END=child.returncode if child else None,
                    reason=reason,argv=command,test_ids=ids,owned_bytes=usage())
        records.append(record)
        (root/'collection.json').write_text(json.dumps(records,indent=2))
        print(json.dumps(dict(root=str(root),source=source,**record)),flush=True)
        print(data.decode(errors='replace')[-10000:],flush=True)
print(json.dumps(dict(root=str(root),owned_bytes=usage(),all_children_collected=True)),flush=True)
raise SystemExit(0 if len(records)==len(sys.argv[1:] or groups) and all(r['END']==0 for r in records) else 1)
