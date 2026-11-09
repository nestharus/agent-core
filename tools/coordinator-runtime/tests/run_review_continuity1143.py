"""Retained, network-isolated qualification; requires a NEW owned data root.

The sole checkout is mounted read-only. SDK4 plus a declared retention fixture
supplies SDK5; neither real account homes nor runtime journals are mounted.
"""
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

root = Path(os.environ['REVIEW_CONTINUITY1143_ROOT'])
repo, sdk, fixtures = root/'repo', root/'sdk', root/'fixtures'
before = os.environ.get('REVIEW_CONTINUITY1143_PRE_FIX') == '1'
label = 'before' if before else 'final'
label = os.environ.get('REVIEW_CONTINUITY1143_LABEL', label)
assert label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
tests = ['test_review_continuity1143',
         'test_oneoff1077.Recovery.test_selected_service_native_reviews_retains_full_calls_and_exact_close_hold',
         'test_oneoff1077.Recovery.test_interrupted_native_reviews_preserves_original_and_refuses_fresh_fallback',
         'test_reviews_ceiling766', 'test_contract482.MethodClosure',
         'test_execution_pool.ExecutionPool.test_allocation_across_classifier_task_diagnosis_and_successor_conserves_original',
         'test_execution_pool.ExecutionPool.test_real_fixture_launches_rotate_and_post_begin_exclusion_does_not_move_call',
         'test_continuing.Continuing.test_R03_actual_owner_corrects_rejected_route_once_without_replaying_review',
         'test_continuing.Continuing.test_L02_selected_owner_report_strings_have_custody_without_fabricated_model_attempt']
if before:
    tests = ['test_review_continuity1143.OpaqueBoundary.test_store_refuses_before_allocation_and_preserves_reserved_job',
             'test_review_continuity1143.OpaqueBoundary.test_executor_rechecks_task_before_material_or_fake_transport',
             'test_review_continuity1143.NativeContinuity.test_empty_future_pool_does_not_move_or_block_owned_continuation']
if os.environ.get('REVIEW_CONTINUITY1143_BASELINE') == '1':
    tests = ['test_reviews_ceiling766.ReviewsCeiling.test_actual_native_wrapper_invokes_only_owned_failure_producer',
             'test_continuing.Continuing.test_R03_actual_owner_corrects_rejected_route_once_without_replaying_review',
             'test_continuing.Continuing.test_L02_selected_owner_report_strings_have_custody_without_fabricated_model_attempt']
if os.environ.get('REVIEW_CONTINUITY1143_QUALIFIED') == '1':
    # These three inherited tests are retained in final-2 and separately run
    # under the pre-change boundary semantics. Keep their failures explicit.
    tests = [t for t in tests if not t.startswith('test_continuing.')]
    tests.remove('test_reviews_ceiling766')
    tests += ['test_reviews_ceiling766.ReviewsCeiling.'+name for name in (
        'test_exact_filename_cannot_expand_as_git_pathspec',
        'test_missing_package_admission_refuses_before_material',
        'test_native_identity_operand_is_distinct_from_file_permission',
        'test_scoped_B_refuses_before_material_metadata_or_body',
        'test_scoped_exact_A_reaches_real_material_and_read_facade',
        'test_unscoped_B_refuses_before_material_metadata_or_body',
        'test_unscoped_directory_refuses_before_recursive_listing',
        'test_unscoped_exact_A_reaches_real_material_and_read_facade',
        'test_unscoped_relationship_B_refuses_before_material')]

bootstrap = '''
import os, unittest
if os.environ.get('REVIEW_CONTINUITY1143_PRE_FIX') == '1':
    from pathlib import Path
    from coordinator_runtime import reviews
    # In-memory counterfactual of the two changed production boundaries only.
    # No source file, fixture pin, route value or provider result is changed.
    body = Path(reviews.__file__).read_text()
    body = body.replace("guard = runtime.execution_pool.admission(context['profile']) if opening and not close else _existing()",
                        "guard = _existing() if close else runtime.execution_pool.admission(context['profile'])")
    exec(compile(body, reviews.__file__, 'exec'), reviews.__dict__)
    reviews.route_binding = lambda task: dict(reviews.BINDING)
unittest.main(module=None, verbosity=2)
'''
cmd = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session',
       '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
       '--ro-bind', '/lib64', '/lib64', '--ro-bind', '/bin', '/bin',
       '--proc', '/proc', '--dev', '/dev', '--ro-bind', str(repo), '/src',
       '--ro-bind', str(sdk), '/src/tools/message-board',
       '--bind', str(fixtures), '/fixtures', '--tmpfs', '/tmp', '--dir', '/home',
       '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/fixtures',
       '--setenv', 'TMPDIR', '/fixtures/tmp', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
       '--setenv', 'ONEOFF1077_FIXTURES', '/fixtures', '--setenv', 'QA629_FIXTURES', '/fixtures',
       '--setenv', 'COORDINATOR_TEST_BOARD_LIBRARY', '/src/tools/message-board',
       '--setenv', 'PYTHONPATH', '/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests',
       '--setenv', 'REVIEW_CONTINUITY1143_PRE_FIX', '1' if before else '0',
       '--chdir', '/fixtures', '/usr/bin/python3', '-c', bootstrap, *tests]


def usage():
    size = entries = 0
    for home, dirs, files in os.walk(root, followlinks=False):
        entries += len(dirs) + len(files)
        for name in files:
            path = Path(home)/name
            # Negative tests deliberately create OWN synthetic alias sentinels.
            # Charge their entries without following or reading target values.
            try:
                size += path.lstat().st_size
            except FileNotFoundError:
                # An owned tempfile fixture can remove its own file during this
                # point observation. Do not retry, discover or follow it.
                continue
    return size, entries


space = os.statvfs(root)
assert space.f_bavail*space.f_frsize-268435456 >= 107374182400
assert space.f_favail-6000 >= 1000000
capture = root/('qualification-'+label+'.txt')
start = time.monotonic()
proc = None
reason = None
harness_error = None
with capture.open('xb') as output:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    try:
        while selector.get_map():
            size, entries = usage()
            if size >= 240*1024**2 or entries >= 5800:
                reason = 'conservative own allocation stop'
            if time.monotonic()-start > 120:
                reason = 'qualification timeout120s'
            if reason:
                proc.kill()
            for key, _ in selector.select(.2):
                data = os.read(key.fd, 65536)
                if not data:
                    selector.unregister(key.fileobj)
                elif output.tell()+len(data) <= 2*1024**2:
                    output.write(data)
                else:
                    reason = 'capture2MiB; partial evidence'
                    proc.kill()
        end = proc.wait(timeout=10)
    except Exception as exc:
        harness_error = type(exc).__name__
    finally:
        if proc.poll() is None:
            proc.kill()
        end = proc.wait()
        selector.close()
        proc.stdout.close()
size, entries = usage()
result = {'counterfactual': before, 'tests': tests, 'actual_END': end, 'stop_reason': reason,
          'harness_error': harness_error,
          'capture': str(capture), 'capture_bytes': capture.stat().st_size,
          'own_bytes_before_result': size, 'own_entries_before_result': entries,
          'source_readonly': True, 'network_isolated': True,
          'private_account_or_actual_journal_mounts': False,
          'meaning': 'owned qualification only; no opaque/provider/native/Source acceptance'}
(root/('qualification-'+label+'.json')).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
print(capture.read_text())
raise SystemExit(1 if harness_error else end)
