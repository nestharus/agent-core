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
base = repo / '.qualification847'
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
p=src/'tools/coordinator-runtime/tests/test_source_continuity688.py'
s=p.read_text().replace('transition = dict(basis=dict(release=self.old_release,',"transition = dict(basis=dict(release=self.old_release, tasks=self.config['tasks'],")
p.write_text(s)
records=[]
(root/'snapshot.json').write_text(json.dumps(dict(source=source,sha256=manifest,sdk5=sdk_hashes),indent=2))

groups = {
 'reconcile': ['test_reconcile_admission847.Reconcile847.'+name for name in [
  'test_periodic_orphan_after_original_collection',
  'test_post_await_refusal_next_tick_stays_before_body',
  'test_direct_finish_and_awaiting_acceptance',
  'test_admitted_later_reads_join_transaction',
  'test_spawned_preparation_after_start_refuses_before_body',
  'test_async_preparation_after_start_refuses_before_body']],
 'controls': ['test_bootstrap_composition832.NativeToWork.test_native_whole_integrator_return_maps_real_work_point',
  'test_plain_control821.Completion821.test_same869_shape_existing_return_cli_terminal_once_preserves_every_original',
  'test_report_mapping825.Mapping825.test_delegated_known_completion_and_packet_work',
  'test_reconcile_admission847.Amendment847.test_actual_composite_cli_all_changed_modules',
  'test_authentic_control794.Kernel794.test_source_and_sdk_snapshots_readonly',
  'test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied']}
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
    overrides = {}
    if label == 'baseline836':
        rel = 'tools/coordinator-runtime/coordinator_runtime/native_review_scope.py'
        original = (src/rel).read_text()
        begin = original.index('def admit(runtime, row):')
        finish = original.index('@contextmanager',begin)
        changed = original[:begin] + 'def admit(runtime, row):\n    return  # causal reversal of only new boundary admission\n\n\n' + original[finish:]
        overlay = root/'baseline-native_review_scope.py'
        overlay.write_text(changed)
        overrides[rel] = hashlib.sha256(overlay.read_bytes()).hexdigest()
        command += ['--ro-bind',str(overlay),'/src/'+rel,'--ro-bind',str(overlay),'/actualsrc/'+rel]
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
                    reason=reason,argv=command,test_ids=ids,production_overrides=overrides,owned_bytes=usage())
        records.append(record)
        (root/'collection.json').write_text(json.dumps(records,indent=2))
        print(json.dumps(dict(root=str(root),source=source,**record)),flush=True)
        print(data.decode(errors='replace')[-10000:],flush=True)
print(json.dumps(dict(root=str(root),owned_bytes=usage(),all_children_collected=True)),flush=True)
raise SystemExit(0 if len(records)==len(sys.argv[1:] or groups) and all(r['END']==0 for r in records) else 1)
