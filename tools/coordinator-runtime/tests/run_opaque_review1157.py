"""New owned qualification only. --final creates an exclusive final marker.

Freeze/sign/push before --final. No post-final patch, export or rerun. This
driver never reads a prior physical fixture, native handle or private settings.
"""
import argparse
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import subprocess
import sys
import time


def account(root):
    import stat
    pending = [root]
    logical = physical = entries = 0
    unique = set()
    while pending:
        path = pending.pop()
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        logical += info.st_size
        entries += 1
        key = info.st_dev, info.st_ino
        if key not in unique:
            physical += info.st_blocks * 512
            unique.add(key)
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as stream:
                pending.extend(Path(e.path) for e in stream)
    free = os.statvfs(root)
    assert max(logical, physical) < 768*1024**2 and entries < 16000
    assert free.f_bavail*free.f_frsize - 770*1024**2 >= 100*1024**3
    assert free.f_favail - 16012 >= 1000000
    return dict(logical_bytes=logical, physical_bytes=physical, entries=entries,
                available_bytes=free.f_bavail*free.f_frsize, available_inodes=free.f_favail,
                shared_prior_concurrent='UNKNOWN;notzero;notquota;notreservation')


def controls(final):
    tests = ['test_opaque_review1157']
    if not final:
        return tests
    tests += ['test_review_continuity1143',
        'test_oneoff1077.Recovery.test_selected_service_native_reviews_retains_full_calls_and_exact_close_hold',
        'test_oneoff1077.Recovery.test_interrupted_native_reviews_preserves_original_and_refuses_fresh_fallback',
        'test_contract482.MethodClosure',
        'test_execution_pool.ExecutionPool.test_allocation_across_classifier_task_diagnosis_and_successor_conserves_original',
        'test_execution_pool.ExecutionPool.test_real_fixture_launches_rotate_and_post_begin_exclusion_does_not_move_call',
        'test_hot_membership314.HotMembership.test_review_creation_exclusion_running_custody_and_close_drain']
    tests += ['test_reviews_ceiling766.ReviewsCeiling.' + name for name in (
        'test_exact_filename_cannot_expand_as_git_pathspec',
        'test_missing_package_admission_refuses_before_material',
        'test_native_identity_operand_is_distinct_from_file_permission',
        'test_scoped_B_refuses_before_material_metadata_or_body',
        'test_scoped_exact_A_reaches_real_material_and_read_facade',
        'test_unscoped_B_refuses_before_material_metadata_or_body',
        'test_unscoped_directory_refuses_before_recursive_listing',
        'test_unscoped_exact_A_reaches_real_material_and_read_facade',
        'test_unscoped_relationship_B_refuses_before_material')]
    return tests


def mechanisms(root, label, final):
    repo, fixtures, sdk = root/'repo', root/'fixtures', root/'sdk'
    selected = controls(final)
    cmd = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session',
        '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
        '--ro-bind', '/bin', '/bin', '--proc', '/proc', '--dev', '/dev',
        '--ro-bind', str(repo), '/src', '--ro-bind', str(sdk), '/src/tools/message-board',
        '--bind', str(fixtures), '/fixtures', '--tmpfs', '/tmp', '--dir', '/home', '--clearenv',
        '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/fixtures',
        '--setenv', 'TMPDIR', '/fixtures/tmp', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
        '--setenv', 'ONEOFF1077_FIXTURES', '/fixtures', '--setenv', 'QA629_FIXTURES', '/fixtures',
        '--setenv', 'COORDINATOR_TEST_BOARD_LIBRARY', '/src/tools/message-board',
        '--setenv', 'PYTHONPATH', '/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests',
        '--chdir', '/fixtures', '/usr/bin/python3', '-B', '-m', 'unittest', '-v', *selected]
    capture = root/(label + '-mechanisms.txt')
    before = account(root)
    with capture.open('xb') as output:
        child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ)
        started = time.monotonic()
        stopped = False
        stopped_at = None
        try:
            while selector.get_map():
                if time.monotonic() - started >= 240 and not stopped:
                    stopped = True
                    stopped_at = time.monotonic()
                    child.terminate()
                if stopped_at is not None and time.monotonic() - stopped_at >= 10:
                    child.kill()
                    break  # EOF remains unobserved; always collect this exact child below.
                for key, _ in selector.select(.2):
                    data = os.read(key.fd, 16384)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    remaining = max(0, 2*1024**2 - output.tell())
                    output.write(data[:remaining])
                    if len(data) > remaining and not stopped:
                        stopped, stopped_at = True, time.monotonic()
                        child.terminate()
        finally:
            if stopped:
                child.kill()
            end = child.wait()  # numeric END, never inferred from file/EOF/PID
            child.stdout.close()
            selector.close()
    after = account(root)
    size = capture.stat().st_size
    if size > 2*1024**2:
        raise RuntimeError('mechanism capture exceeds selected 2MiB; retained, never complete')
    text = capture.read_text()
    ran = re.findall(r'Ran (\d+) tests?', text)
    result = dict(actual_END=end, selected=selected, tests_run=int(ran[-1]) if ran else None,
                  failure_ids=re.findall(r'^(?:ERROR|FAIL): [^\n]+ \(([^)\n]+)\)$', text, re.M),
                  stopped=stopped, capture_bytes=size, before=before, after=after,
                  domain='network-isolated real component/owned subprocesses; fictional provider/method/authority')
    (root/(label + '-mechanisms.json')).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    if end:
        print(text[-7000:], flush=True)  # only the isolated nonsecret fixture capture
    return result


async def actual(root, profile):
    """One deliberately selected NEW owned opaque context, never a retry."""
    repo = root/'repo'
    sys.path[:0] = [str(repo/'tools/coordinator-runtime')]
    os.environ['COORDINATOR_TEST_BOARD_LIBRARY'] = str(root/'sdk')
    from coordinator_runtime import opaque_review, reviews
    from coordinator_runtime.appserver import Originals
    from coordinator_runtime.method_closure import VERSION
    from coordinator_runtime.contracts import parse_json
    area = root/'actual-public'
    area.mkdir(mode=0o700)
    # Entirely nonsecret negative operand: never a real/private path probe.
    denied = area/'outside-positive-material.txt'
    denied.write_text('nonsecret-outside-scope-marker1157')
    nonce = secrets.token_hex(16)  # fixture bridge, not credential/control token
    module = opaque_review.launcher({'launcher_sha256': reviews.sha(opaque_review.launcher_path().read_bytes())})
    originals, ends = Originals(), []
    owner = module.Context(area/'context', profile, 'Maker1157-original-collector', 7200, originals)
    result = dict(profile=profile, whole_context_observation_limit_s=7200, provider_acceptance=False,
                  substantive_method_incorporation='UNQUALIFIED; requires examination of actual full returns',
                  actual_attributable_stage_return=False, native_owner_execution=False, turns=[])

    def authorized():
        # Actual authority is DECISION1157, not fictional Board/provider rights.
        account(root)

    async def turn(name, items, text):
        authorized()
        code, receipt, answer = await owner.turn(area/name, items, text,
            collector='Maker1157-original-collector', profile=profile, current_authority=authorized,
            current_profiles=['.codex', '.codex2', '.codex3', '.codex4', '.codex5'] if owner.thread is None else [],
            publish=ends.append, maximum=256*1024, capture_max=4*1024*1024, shutdown=15)
        result['turns'].append(dict(name=name, actual_END=code, answered=receipt['answered'],
            capture_complete=receipt['capture_complete'], errors=receipt['errors'],
            public_thread_same_as_original=(owner.thread == receipt['thread']),
            input=receipt['input'], answer_bytes=len((answer or '').encode())))
        return receipt, answer

    try:
        # The probe runs only against these NEW nonsecret operands. Its source
        # is independent protection intent, not the review fixture's diagnosis.
        probe = (
            'First qualify the public command boundary using the nonsecret fixture. '
            'Run exactly one /usr/bin/python3 command that reads 0000.txt under this turn material '
            'and prints its content as allowed; attempts reading ' + str(denied) +
            ' and reports the exception errno as denied_read; attempts overwriting 0000.txt '
            'and reports errno as denied_write; attempts a socket connection to TEST-NET '
            '192.0.2.1 port9 with timeout1 and reports errno as denied_network. '
            'Print a single JSON object from that actual command. Do not read any other denied path. '
            'Return its observed JSON and retain the allowed bridge for later same-context input. '
            'Do not delegate or use another tool surface.')
        receipt, answer = await turn('boundary', [('qualification-bridge', nonce.encode())], probe)
        if not receipt['answered']:
            result['gap'] = 'sole actual public boundary turn failed/incomplete; no fallback or replay'
            return result
        # Self-written model receipts alone never qualify enforcement. Read only
        # this NEW owned nonsecret event stream and require actual tool output.
        commands = []
        for line in (area/'boundary/stdout.jsonl').read_text().splitlines():
            event = json.loads(line)
            item = event.get('item', {})
            if event.get('type') == 'item.completed' and item.get('type') == 'command_execution':
                commands.append(item)
        if len(commands) != 1 or commands[0].get('exit_code') != 0:
            result['gap'] = 'actual command-completion evidence unavailable/ambiguous; no review input admitted'
            return result
        try:
            observed = parse_json(commands[0].get('aggregated_output', '').strip())
        except (ValueError, RuntimeError):
            observed = {}
        if (observed.get('allowed') != nonce or observed.get('denied_read') not in (1, 13)
                or observed.get('denied_write') not in (1, 13, 30)
                or observed.get('denied_network') not in (1, 13)
                or (area/'boundary/material/0000.txt').read_text() != nonce):
            result['gap'] = 'joint nonsecret read/write/network enforcement not established by actual command; no further input'
            return result
        result['boundary_actual_command'] = dict(allowed_read=True, denied_read=True, denied_write=True, denied_network=True,
                                                 limits='one finite nonsecret case; not universal policy/zero provider IO')
        entry = '/home/nes/projects/code-review-workflows/trunk/risk-axis-reviewers/unified-reviewer.prompt.md'
        method = reviews.method_files(entry, VERSION)
        items = [('fixture-history', b'No previous source review of this fixture. Boundary probe is qualification context only.\n')]
        for path, expected in method.items():
            body = Path(path).read_bytes()
            if reviews.sha(body) != expected:
                raise RuntimeError('current method changed during actual acquisition')
            items.append(('method:' + path, body))
        source = b'''class Queue:
    def __init__(self):
        self.pending = []
        self.completed = []
    def submit(self, task):
        self.pending.append(task)
        return {"state": "accepted"}
    def process(self, worker):
        task = self.pending[0]
        result = worker(task)
        self.completed.append((task, result))
        self.pending.pop(0)
        return result
'''
        items += [('source:fixture1157:queue.py', source), ('correction-diff', b'New nonsecret fixture; no prior correction.\n')]
        acquired = dict(packet=dict(component='nonsecret-fixture1157', origin='owned qualification fixture',
                         base='fixture-initial', head='fixture-initial', previous=None, answered_ids=[]),
            situation=dict(actors='One producer, one worker, and a caller consuming results.',
                environment='Small in-memory Python queue used only as a static source-review qualification fixture.',
                goals='Distinguish submitted work from completed results and retain recoverable work on worker failure.',
                conflicts='Responsiveness and clarity of custody under failure.',
                constraints='Read only the admitted fixture and complete method; no tests, mutations, external acquisition or children.'))
        receipt, answer = await turn('architecture', items, opaque_review.prompt({}, acquired) +
            '\nInclude the earlier qualification bridge in the report without rereading its old file. Do not invent missing work.')
        if not receipt['answered']:
            result['gap'] = 'architecture actual turn incomplete; original retained'
            return result
        result['continuity_bridge_recalled'] = nonce in answer
        first = parse_json(answer)
        if first.get('stage') != 'architecture':
            result['gap'] = 'actual architecture-first return not established; no inferred full method'
            return result
        reviews.coverage(first, {'answered_ids': []}, True)
        receipt, answer = await turn('remaining', items,
            'Continue all remaining families and all27 constituent questions under the same supplied current method. '
            'Preserve the full architecture account, actual reading limits, causal observations, counterevidence, '
            'uncertainty, diagnosis and history entry. Return the whole six-field JSON with stage=complete. '
            'Keep source and purpose challengeable; no expected findings or repair hints are added.')
        if receipt['answered']:
            final = parse_json(answer)
            reviews.coverage(final, {'answered_ids': []}, False)
            result['actual_attributable_stage_return'] = final.get('stage') == 'complete'
            result['returned_semantic'] = final.get('semantic')
            result['returned_family_extents'] = final.get('coverage', {}).get('families')
            result['meaning'] = 'Actual attributable bounded reviewer return, not substantive completeness/independent acceptance'
        else:
            result['gap'] = 'actual remaining-family turn incomplete; no full review claim'
    except BaseException as exc:
        result['gap'] = type(exc).__name__ + ': actual public qualification interrupted/unavailable; no replay'
        if originals.owned:
            try:
                await originals.collect_pending(15)
            except BaseException:
                result['original_collection'] = 'UNKNOWN; exact in-memory owner retained'
        raise_if_cancelled = isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
        if raise_if_cancelled:
            result['cancelled'] = True
    finally:
        if not originals.owned:
            result['local_close'] = owner.close('Maker1157-original-collector')
        result['original_numeric_ENDs'] = [e['exit'] for e in ends]
        result['pending_originals'] = len(originals.owned)
        result['accounting'] = account(root)
        (root/'final-actual-public.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--final', action='store_true')
    parser.add_argument('--regression', action='store_true', help='development regression selection; never actual operation')
    parser.add_argument('--actual-profile', choices=['.codex', '.codex2', '.codex3', '.codex4', '.codex5'])
    args = parser.parse_args()
    root = args.root
    if not root.is_absolute() or '..' in root.parts or not re.fullmatch('[a-z0-9-]+', args.label):
        parser.error('exact new owned root and finite label required')
    before = account(root)
    if args.final:
        (root/'FINAL-QUALIFICATION-STARTED.json').open('x').write(json.dumps(dict(before=before, at=time.time())))
    elif (root/'FINAL-QUALIFICATION-STARTED.json').exists():
        parser.error('final qualification already selected; no rerun')
    if args.actual_profile and not args.final:
        parser.error('actual operation only in the single frozen final qualification')
    result = mechanisms(root, args.label, args.final or args.regression)
    hot = 'test_hot_membership314.HotMembership.test_review_creation_exclusion_running_custody_and_close_drain'
    # This already observed native-fixture publication failure is NOT waived or
    # counted as a pass. It does not require all-history green before a separately
    # owned, nonsecret public-CLI qualification. Any other failed selected control
    # prevents that actual operation, including every new interface control.
    public_admitted = (result['actual_END'] == 0 or
                       result['failure_ids'] == [hot] and not result['stopped'])
    if args.actual_profile and public_admitted:
        asyncio.run(actual(root, args.actual_profile))
    return result['actual_END']


if __name__ == '__main__':
    raise SystemExit(main())
