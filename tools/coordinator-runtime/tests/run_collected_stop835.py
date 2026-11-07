import os, pathlib, subprocess, json, time, signal
repo=pathlib.Path(__file__).resolve().parents[3]
base=pathlib.Path(os.environ['COLLECTED_STOP835_FIXTURES']);base.mkdir(mode=0o700,exist_ok=True)
size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
if size>=128*1024**2:raise SystemExit('stop-new128MiB')
run=base/('attempt-'+str(time.time_ns()));run.mkdir(mode=0o700)
src=run/'src';src.mkdir();fixtures=run/'fixtures';fixtures.mkdir(mode=0o700);(fixtures/'tmp').mkdir(mode=0o700)
paths=subprocess.run(['git','-C',str(repo),'ls-files','tools/coordinator-runtime'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,check=True).stdout.splitlines()
paths += ['tools/coordinator-runtime/tests/test_collected_stop835.py','tools/coordinator-runtime/tests/test_source_amendment818.py','tools/coordinator-runtime/tests/test_source_amendment822.py','tools/coordinator-runtime/tests/test_source_composition827.py']
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
(src/'original822.json').write_text('{"__init__.py": "5d66d9f12796aefad7c957ac274a0c29a5145f2c2cfbda869447c7710006619b", "admitted.py": "49cb0e353fbf84d60123c569255271ea296dda82414ea43b724d494ae494b39b", "appserver.py": "c40db90e04a518c3a74d79f14161bb2bcf02cbd05666f7d8f1e5a709b1097f1b", "automatic_control.py": "3bf28ee9f03e96b63f786e298f1e767c8cd42e078989b326ee2e1fc6379dbe8b", "board.py": "a1c6d2f7cc8c3ac82d5bf24973d7bedd880b6315cf60ad39dc3dbe2d903f94e0", "board_delivery.py": "95480ba4c473f783009b744372f2128c67ce8505913f184534f73b33b296c100", "bounded_log.py": "348fddb9e583786c4e96ac3c94e6367b60f02a27e09f25b62c3c2dd4d8cf6029", "branches.py": "21ed8b7be4d8b3df076a50369cb03db9df749ca569591d0aaffe55360256f59d", "capacity.py": "ce37543dc8b93285151037677f86283c04afe4ec4302f0fe8030754573921c7d", "cleanup.py": "ff873a9b9c68ab4480b3b3c8e92417ef0f0436bdfa13e3b337d90c4a76442b5c", "cli.py": "6a6cb0b0e67dc9d94f2048b5f791faaf9f036616b414c39a90f71b4d204a7bdc", "coding.py": "ec2132c53b61c5e65a29bebc8a355c890f0932f16965c236586f5bf158a86050", "completion.py": "eb6bd1647e2dffad825911b35531dda9d243d7f45f9e32c95c8cae66e0d53454", "configuration.py": "0f180d0f1962b0b302b89523ad17af56c720d68603f09c432a0455a737c1e3e1", "contracts.py": "78f8765295520fc99c69c3ef4c9c6e187c1a4e8805ac5c8b6ec107f69a0ea8f6", "custodian_service.py": "c965b850ce03c813298bb80ba1f03adcc255a2e5577178e652dd2ca0c4863f32", "custody.py": "121300c6d98f3f3bdc8eae1f02759011e7852ed718f33671265f48e599003a90", "delivery.py": "a1379e7668a6bed95f285846e2c7bdc6b2f5d0f2a33159bba5354d602754aa4a", "dispatcher.py": "3a466177dec861095280fef663fc5849b1592f823e0a45a6aa743fd2757055ba", "execution_pool.py": "03eccea4713262bd53deff6f982090dee04dbfdd8a2d72082eb9b4f1ac3febac", "frontier.py": "35b82ff3d8aadc7bc26fbe8feaf9cb6cf4c28b6e8b5231dc0c53c17c6aeebdbb", "inputs.py": "a77daca813c5ac2d0983b7b4ee973d4c9be493f0c297e786274dddc80c1a6b03", "integration.py": "1bb925f6cdf6d1885d0ca7098d1336d348433acbc0254220af862a5544970eac", "integration_evidence.py": "905cb5f46c32a1c28eec92ea159e31486ce0ea079fd607102379fbc2b8386d44", "integration_management.py": "2ad8a12cf11a558f27c581bcd86f3ad692d9af069c45c9117fce6a486819b5b4", "local_integration.py": "fb9597b1fe5fd354d93d44b9e282d751527333c0614fb837c4824079349dbc01", "local_native.py": "37d95c92b556e69e46803c8d265646c03d4a500439711e68cf3739269123fb0f", "metadata_lookup.py": "5b161bea354b3f4be37746fbd9df094ca372847807bbdd6c689326cabf5aeee2", "method_closure.py": "360c13cc9de23d3474fdc14ceba8d63ba2724d486f07c4b14782062a46fc171f", "observations.py": "08900f2238d134f435c1b953023c0f27f42c3f214dbaeb670cc2726c9c49c8bc", "ordinary.py": "1f7daf62cfc74bcb0a696a9c6b10fa74a677719fcc74cf57df4cf26e21951efe", "owner_control.py": "3d59ec43199145f512671b7f01916821f6dc23b2da1386b28cc04144105fe2aa", "processing.py": "4e6906f1f0d3359c7615a343317ae7ac6e21a17a977126b798aef8a457c39c55", "processing_admission.py": "31b10eb6382e8ec4c2686c088222c418c7bc8a9e40b46a12b24392fc203c4e9f", "progress.py": "bc4a12c1e42e911586dee0267be43ea1586183aa263019ec6a127442ab26433a", "prospective.py": "0f9ea1024b6257eeb45c0072a966a12b36cf234412b84aae4791096d5d381aae", "public_tools.py": "13b1e250a10298591e1cbb81bb3f34f618ab792c076968ab303456bbfae3927c", "publication.py": "aeb6bee399e408593c6956f633103417ba899d9e1e4fc5b3635b57d67aed6837", "qa_source.py": "ef2ad2b357e1be26ede848729cc6eb4703f4deabe495241e58d5657fec7d0efc", "readiness.py": "6530a6993b1cadb0f2ce092f8e0c249614b279760a979ba1b4aa9200acef2d69", "recovery.py": "ff7680a65741edf043c72f5669e0dbf3ccb9c36261c0ef046997c6af7a53373c", "ref_scope.py": "5cd26adadd69a56c421e62a1c283f869807a6a52ea8ee1c7ac018d12b5b67c9b", "report_repair.py": "c8d438563e49690a499f4e9f516717f794351561cbf209af5ae9177a02acc7b0", "report_scope.py": "1705f538a882fc081f21361b7ef137fa2b173401c6ed074a8aa9c3b12ef66f6c", "reservation.py": "185b8a739c1d33d11395343998374bdad3e30149c531f6caee65778844a4e0a7", "resource_scopes.py": "88eabd00c8348d91a100e1368be6e803e15dd30ab7403c2d278a9e605caafc51", "retained.py": "37ec00cf8d2bd5d469f2d746003b0f62ac84504e818c4b92ad6a4c1edd5c8bca", "retention_dependency.py": "b5b274a151104e948334918a0688b2135e1afae5de5314a46297beb2fe7c77d8", "retirement.py": "d86138ae196c9c20772f7b349c23a81adb49a3ad0921bba488c2a8cae07af892", "review_reader.py": "d0ba7f0e661aaf39476842c2c5cfba4409d89f10e3035572b42188cb70218f86", "review_returns.py": "6d9d08da3230d2bac2536565eeb800f993e0a48b8da419a21725fae039347e1f", "reviews.py": "c773cad52008293c5cc390090576cf695500718d88733087a5ae62161f6e55b1", "routine.py": "b6e884e0c2d8264b6b291a900bf3003055a664fba4af58088970ac24939207d8", "selected_source.py": "ffbee1ce5950a4918915f8ab7fc2c16723c054a2ae0684c78ca13abfa9fe87fa", "service.py": "f1dbbef7d30998f07614ae40e4a2804e072c6449239ef5256e4ec93de9b0a39a", "service_recovery.py": "ab2819101d0adbdb1b220ce7a7433fe063a4a5f8301c3631eb7e00ddd66544b8", "service_wake.py": "789add4dbf66b44715e1318c66eb8f591a60ba5a12ceaf6c33e833c0bf22e8b5", "shared_custody.py": "871b79271ad00fd5582ee83de6a4f133f42132ebb11e6b21edc2f7b24f10e832", "software.py": "027fe8f78ff7210813d645b1372f87202cd61823ca12cbe80dc9e979baa7b693", "storage.py": "f628a1774490459dbbd8e4f5911a8916bf138bbf1e5dc94f0d55e94f44a9b8ce", "store.py": "9c155a9cc2d327dcab616361df4b7975623b9a046442cdcbdc8a136e51ea055c", "windows.py": "9b686ec4f0282e07cdd06079ae09de1c42de4e2b6bd24d58fc46b3b69ea2b24c"}')
# Declared inherited fixture adaptation, matching793 frozen-task basis repair.
p=src/'tools/coordinator-runtime/tests/test_source_continuity688.py'
s=p.read_text().replace('transition = dict(basis=dict(release=self.old_release,','transition = dict(basis=dict(release=self.old_release, tasks=self.config[\'tasks\'],')
p.write_text(s)
ids=[
 'test_collected_stop835.CollectedStop.test_public_release_oneoff_and_failed_service_cli_preserves_history',
 'test_collected_stop835.CollectedStop.test_bad_collection_foreign_uncollected_and_live_refuse_before_bodies',
 'test_collected_stop835.CollectedStop.test_release_contradiction_and_wrong_actor_refuse',
 'test_source_amendment822.OutsideReview.test_real_cli_basis_external_safe5_work_collection_and_selection',
 'test_source_amendment822.OutsideReview.test_collection_and_selection_mutation_fences_and_public_hashes',
 'test_source_amendment822.OutsideReview.test_external_running_unreleased_expired_exhausted_config_grant_refuse',
 'test_source_composition827.Composition.test_foreign_stopped_reservation_keeps_all_held_history',
 'test_lease_effect805.Isolation.test_actual_source_sdk5_and_snapshot_are_readonly',
 'test_processing206.KernelIsolationTests.test_real_source_and_dependency_writes_are_kernel_denied',
 'test_lease_effect805.EffectLease.test_expired_effect_refuses_before_body_with_framework_current',
 'test_lease_effect805.AdmittedLease.test_expired_effect_refuses_before_body_with_framework_current']
if os.environ.get('SOURCE_AMENDMENT818_PRE_FIX') == '1':
 p=src/'tools/coordinator-runtime/coordinator_runtime/report_repair.py'
 p.write_text(p.read_text().replace("lease_source(runtime, key, amendment)['implementation']", "amendment['basis']['implementation']").replace("lease_source(runtime, cap['id'], amendment)['release']", "amendment['basis']['release']"))
 ids=['test_source_amendment818.Amendment.test_authentic_original_plan_and_pending_history_preserved']
cmd=['bwrap','--die-with-parent','--unshare-all','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--ro-bind','/bin','/bin','--proc','/proc','--dev','/dev','--ro-bind',str(repo),'/actualsrc','--ro-bind',str(src),'/src','--bind',str(fixtures),'/fixtures','--tmpfs','/tmp','--dir','/home','--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/fixtures','--setenv','TMPDIR','/fixtures/tmp','--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','QA629_FIXTURES','/fixtures','--setenv','COORDINATOR_TEST_BOARD_LIBRARY','/src/tools/message-board','--setenv','PYTHONPATH','/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests','--chdir','/fixtures','/usr/bin/python3','-m','unittest','-v',*ids]
cap=run/'output.txt';proc=None;start=time.monotonic();output=b'';reason=None
try:
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 import selectors
 sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ)
 with cap.open('wb') as f:
  measured=time.monotonic()
  while sel.get_map():
   if time.monotonic()-measured>=1:
    measured=time.monotonic()
    owned_size=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
    if owned_size>=192*1024**2:reason='cumulative192MiB';os.killpg(proc.pid,signal.SIGKILL)
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
result=dict(pre_fix=os.environ.get('SOURCE_AMENDMENT818_PRE_FIX') == '1',run=str(run),END=end,pid=proc.pid if proc else None,timeout=reason,cumulative_bytes=size,tests=ids,readonly_src=True,network_isolated=True,private_TMPDIR_before_imports=True)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(cap.read_text()[-14000:])
if size>=192*1024**2:raise SystemExit('cumulative192MiB')

raise SystemExit(end if end is not None else 1)
