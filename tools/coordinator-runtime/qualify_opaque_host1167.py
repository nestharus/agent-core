#!/usr/bin/env python3
"""One owned public execute/command/export + Originals qualification composition.

This new caller deliberately uses the public low-level execute(argv, env, ...)
interface. It does not instantiate, replace, subclass or patch Context. It does
not qualify Context.turn(), opaque_review.call(), default service or native roots.
The public production modules stay at b551. All context lifecycle in this caller
is separately attributed to this harness, never retroactively to production.
"""
import argparse
import asyncio
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import secrets
import shlex
import stat
import subprocess
import sys
import time

BASE = 'b551d7d0d56d2468050c6ee7278fb1c3c05d74bf'
ROOT = Path('/home/nes/rfq-runtime-qualification-20261109/opaquehost1167')
REPO = ROOT / 'repo'
EXE = '/home/nes/.npm-global/bin/codex'
PROFILE = '.codex5'
COLLECTOR = 'Maker1167-original-collector'
CAP_BYTES, CAP_ENTRIES = 402653184, 10000
PRODUCTION = (
 'tools/coordinator-runtime/coordinator_runtime/configuration.py',
 'tools/coordinator-runtime/coordinator_runtime/native_review_scope.py',
 'tools/coordinator-runtime/coordinator_runtime/opaque_review.py',
 'tools/coordinator-runtime/coordinator_runtime/review_returns.py',
 'tools/coordinator-runtime/coordinator_runtime/reviews.py',
 'tools/coordinator-runtime/coordinator_runtime/store.py',
 'tools/coordinator-runtime/opaque-review1157.md',
 'tools/coordinator-runtime/tests/run_opaque_review1157.py',
 'tools/coordinator-runtime/tests/test_opaque_review1157.py',
 'tools/direct-child/README.md', 'tools/direct-child/review_context.py',
 'tools/coordinator-runtime/coordinator_runtime/appserver.py',
)
ENTRY = Path('/home/nes/projects/code-review-workflows/trunk/risk-axis-reviewers/unified-reviewer.prompt.md')

sys.path.insert(0, str(REPO / 'tools/coordinator-runtime'))
from coordinator_runtime.appserver import Originals, metadata
from coordinator_runtime.method_closure import files, require_definitions

spec = importlib.util.spec_from_file_location('public_review_context1167', REPO/'tools/direct-child/review_context.py')
public = importlib.util.module_from_spec(spec)
spec.loader.exec_module(public)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def write(path, value):
    body = json.dumps(value, indent=2, ensure_ascii=False).encode() + b'\n'
    public.private_write(path, body)


def event(value):
    with (ROOT/'operations.jsonl').open('a') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')


def account():
    """Only this newly owned root; links counted without target traversal."""
    count, logical, allocated, seen = 0, 0, 0, set()
    pending = [ROOT]
    while pending:
        path = pending.pop()
        info = path.lstat()
        count += 1
        logical += info.st_size
        identity = (info.st_dev, info.st_ino)
        if identity not in seen:
            allocated += info.st_blocks * 512
            seen.add(identity)
        if count > CAP_ENTRIES or max(logical, allocated) > CAP_BYTES:
            raise RuntimeError('owned cumulative allocation boundary exceeded')
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                pending.extend(Path(e.path) for e in entries)
    info = os.statvfs(ROOT)
    available = info.f_bavail * info.f_frsize
    assert available - CAP_BYTES - 2097152 >= 107374182400
    assert info.f_favail - CAP_ENTRIES - 12 >= 1000000
    return dict(logical_bytes=logical, allocated_bytes=allocated, entries=count,
        available_bytes=available, available_inodes=info.f_favail,
        whole_allowance_charge_bytes=CAP_BYTES+2097152,
        whole_allowance_charge_entries=CAP_ENTRIES+12,
        shared_prior_concurrent='UNKNOWN;notzero;notquota;notreservation;notcensus',
        provider_platform_storage='unmeasured')


def source_check():
    """Exact immutable public blobs only, no refs/config/untracked census."""
    found = {}
    for name in PRODUCTION:
        cmd = ['git', '-C', str(REPO), 'show', BASE+':'+name]
        event(dict(event='registered', purpose='exact-public-blob', argv=cmd))
        child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        body, _ = child.communicate(timeout=30)
        event(dict(event='collected', purpose='exact-public-blob', actual_END=child.returncode))
        assert child.returncode == 0
        actual = (REPO/name).read_bytes()
        assert actual == body, 'production source changed'
        found[name] = dict(bytes=len(body), sha256=digest(body))
    return found


def environment(area, directory):
    return dict(PATH='/usr/local/bin:/usr/bin:/bin', HOME='/home/nes',
        CODEX_HOME='/home/nes/'+PROFILE, XDG_CONFIG_HOME=str(area/'xdg'),
        TMPDIR=str(directory/'tmp'), PYTHONDONTWRITEBYTECODE='1')


def source_interface():
    return dict(Context=str(inspect.signature(public.Context)),
        Context_turn=str(inspect.signature(public.Context.turn)),
        execute=str(inspect.signature(public.execute)),
        selected='public command/export/execute with genuine runtime Originals',
        actual_frontend=EXE, physical_executable_resolution='not inspected or attested',
        argv_policy='public command() result; only argv[0] replaced by explicit admitted public frontend',
        environment_policy='fixed seven-key environment; original CODEX_HOME; system3 PATH; new owned XDG/TMP',
        Context_turn_qualified=False, service_adapter_qualified=False, native_root_qualified=False)


async def preflight():
    account()
    source = source_check()
    area = ROOT/'preflight'
    area.mkdir(mode=0o700)
    (area/'tmp').mkdir(mode=0o700)
    originals, ends, results = Originals(), [], []
    def publish(observation):
        ends.append(observation)
        event(dict(event='original-published', stage='public-help', **observation))
    for name, args in [('version', ['--version']), ('help', ['--help']),
                       ('exec-help', ['exec', '--help']), ('resume-help', ['exec', 'resume', '--help'])]:
        cmd = [EXE, *args]
        event(dict(event='registered', stage=name, argv=cmd, input='none; public metadata'))
        text = await metadata(cmd, environment(area, area), originals=originals, publish=publish)
        public.private_write(area/(name+'.txt'), text.encode())
        results.append(dict(name=name, bytes=len(text.encode()), sha256=digest(text.encode())))
    assert not originals.owned
    write(ROOT/'preflight.json', dict(source=source, interface=source_interface(),
        help=results, actual_numeric_ENDs=[e['exit'] for e in ends], resources=account()))
    print(json.dumps(dict(preflight='collected', numeric_ENDs=[e['exit'] for e in ends], interface=source_interface())), flush=True)


class Caller:
    """Harness-owned lifecycle. No claim to have exercised Context.turn()."""
    def __init__(self, area):
        self.area = area
        self.workspace = area/'workspace'
        self.workspace.mkdir(mode=0o700)
        self.originals, self.ends = Originals(), []
        self.created, self.lifetime = time.monotonic(), 7200
        self.thread, self.state, self.calls = None, 'new', 0
        self.source = source_check()

    def authorize(self):
        assert self.state in {'new', 'live'}
        assert time.monotonic() < self.created+self.lifetime
        # This exact Work authorization is phase-local; no external account or
        # authority-store query. Current pool membership admits only this open.
        if self.state == 'new':
            assert PROFILE in {'.codex2', '.codex3', '.codex4', '.codex5'}
        account()
        for name, expected in self.source.items():
            assert digest((REPO/name).read_bytes()) == expected['sha256']

    async def turn(self, name, items, text):
        self.authorize()
        directory = self.area/name
        directory.mkdir(mode=0o700)
        (directory/'tmp').mkdir(mode=0o700)
        manifest = public.export(directory/'material', items)
        prompt = (text + '\nOnly immutable material at ' + str(directory/'material/manifest.json') +
            ' is admitted. Read bounded sections and retain unread limits. No delegation, agents, messages, '
            'private stores, startup discovery, external tools or source mutation. The specifically '
            'authorized boundary commands are the sole exception to static read-only investigation.\n')
        public.private_write(directory/'prompt.txt', prompt.encode())
        requested = public.command(PROFILE, self.workspace, directory/'material', self.thread)
        actual = [EXE, *requested[1:]]
        env = environment(self.area, directory)
        write(directory/'launch.json', dict(requested_argv=requested, actual_argv=actual, environment=env,
            interface=source_interface(), expected_thread=self.thread, collector=COLLECTOR,
            lifetime_s=self.lifetime, remaining_s=self.created+self.lifetime-time.monotonic(),
            model_reference='opaque literal gpt-xhigh; unresolved/unattested'))
        def publish(observation):
            self.ends.append(observation)
            event(dict(event='original-published', stage=name, **observation))
        event(dict(event='registered', stage=name, collector=COLLECTOR, profile=PROFILE,
            actual_executable=EXE, input='registered before public execute; collector owns child before feeding input'))
        self.state = 'busy'
        try:
            code, receipt, answer = await public.execute(actual, env, prompt, directory,
                self.originals, publish, self.created+self.lifetime-time.monotonic(), 15,
                256*1024, 4*1024*1024, self.thread,
                lambda: event(dict(event='input-boundary', stage=name, owned_before_input=len(self.originals.owned))))
        except BaseException:
            self.state = 'interrupted'
            raise
        self.calls += 1
        receipt.update(input=self.calls-1, profile=PROFILE, collector=COLLECTOR,
            thread_same_as_original=self.thread in (None, receipt.get('thread')),
            material=manifest, execution_composition='new1167-public-caller',
            native_owner_execution=False, processing_completion=False)
        self.thread = receipt.get('thread') or self.thread
        self.state = 'live' if receipt['answered'] else 'interrupted'
        write(directory/'receipt.json', receipt)
        if answer is not None:
            public.private_write(directory/'answer.txt', answer.encode())
        return receipt, answer

    def close(self):
        assert not self.originals.owned
        self.state = 'closed'
        return dict(local_caller_fenced=True, actual_started_processes_collected=True,
            thread_retained=self.thread is not None, provider_root_close='not claimed',
            provider_storage='retained/unmeasured', kernel_descendant_closure='not claimed',
            effects_settled=False, processing_completion=False)


def commands(directory):
    found = []
    for line in (directory/'stdout.jsonl').read_text().splitlines():
        value = json.loads(line)
        item = value.get('item', {})
        if value.get('type') == 'item.completed' and item.get('type') == 'command_execution':
            found.append(item)
    return found


def method_material():
    closure = files(ENTRY)
    require_definitions(ENTRY, closure)
    items = []
    for name, expected in closure.items():
        body = Path(name).read_bytes()
        assert digest(body) == expected
        items.append(('method:'+name, body))
    return items, closure


async def actual():
    account()
    assert (ROOT/'preflight.json').is_file()
    public.private_write(ROOT/'ONE-ACTUAL-CONTEXT-SELECTED.json', json.dumps(dict(
        profile=PROFILE, collector=COLLECTOR, interface=source_interface(), whole_lifetime_s=7200,
        harness_sha256=digest(Path(__file__).read_bytes()))).encode())
    area = ROOT/'actual'
    area.mkdir(mode=0o700)
    outside = area/'outside-nonsecret.txt'
    outside.write_text('nonsecret denied read marker1167')
    outside_write = area/'outside-write-nonsecret.txt'
    nonce = secrets.token_hex(16)  # public fixture, not authentication
    owner = Caller(area)
    result = dict(status='PARTIAL', profile=PROFILE, collector=COLLECTOR,
        interface=source_interface(), native_owner_execution=False, turns=[],
        boundary_command_evidence=False, substantive_method='not yet performed',
        provider_acceptance=False, actual_service_acceptance=False)
    try:
        script_path = area/'boundary/material/0001.txt'
        script = ("import json,socket\nfrom pathlib import Path\n" +
            "p=Path(__file__).parent/'0000.txt'\nr={'allowed':p.read_text()}\n" +
            "for k,path,mode in " + repr([
                ('denied_read',str(outside),'r'),
                ('denied_outside_write',str(outside_write),'x'),
                ('denied_material_write',str(area/'boundary/material/0000.txt'),'w')]) + ":\n" +
            " try:\n  with open(path,mode) as f:\n   if mode=='r': f.read()\n   else: f.write('nonsecret boundary test1167')\n  r[k]='SUCCESS'\n" +
            " except OSError as e: r[k]=e.errno\n" +
            "try:\n s=socket.socket();s.settimeout(1);s.connect(('192.0.2.1',9));r['denied_network']='SUCCESS'\n" +
            "except OSError as e: r['denied_network']=e.errno\n" +
            "finally: s.close()\nprint(json.dumps(r,sort_keys=True))\n")
        requested_command = ['/usr/bin/python3', str(script_path)]
        probe = ('You personally perform one owned opaque interface qualification. No children or other models. '
            'Execute exactly one command: '+shlex.join(requested_command)+'. The supplied immutable program '
            'performs the admitted nonsecret allowed-read and denied outside-read/outside-write/material-write/'
            'TEST-NET-network cases. Do not modify, replace, quote as output, or reconstruct the program. '
            'Use only this command surface; return the actual observed JSON. Retain its public bridge for '
            'same-context continuation. Do not perform unrelated reads, writes, network or discovery. '
            'A model-written receipt without exact command completion is insufficient.')
        receipt, answer = await owner.turn('boundary', [('public-bridge', nonce.encode()),
            ('exact-nonsecret-boundary-program', script.encode())], probe)
        result['turns'].append(dict(stage='boundary', receipt=receipt, answer_bytes=len((answer or '').encode())))
        if not receipt['answered']:
            result['gap'] = 'Sole actual boundary turn incomplete; no replay or new context.'
            return
        completed = commands(area/'boundary')
        if len(completed) != 1 or completed[0].get('exit_code') != 0:
            result['gap'] = 'Unique successful actual command completion unavailable; no substantive input admitted.'
            return
        actual_command = shlex.split(completed[0].get('command', ''))
        if len(actual_command) == 3 and actual_command[0] in ('/bin/bash','bash','/bin/sh','sh') and actual_command[1] in ('-lc','-c'):
            actual_command = shlex.split(actual_command[2])
        if actual_command != requested_command:
            result['gap'] = 'Completed command differs from independent exact boundary program; no substantive input.'
            return
        try:
            observed = json.loads(completed[0].get('aggregated_output', '').strip())
        except ValueError:
            observed = {}
        boundary = (observed.get('allowed') == nonce and observed.get('denied_read') in (1,13)
            and observed.get('denied_outside_write') in (1,13,30)
            and observed.get('denied_material_write') in (1,13,30)
            and observed.get('denied_network') in (1,13)
            and (area/'boundary/material/0000.txt').read_text() == nonce
            and outside.read_text() == 'nonsecret denied read marker1167'
            and not os.path.lexists(outside_write)
            and script_path.read_bytes() == script.encode())
        result['boundary_command_evidence'] = boundary
        result['boundary_command'] = dict(actual_exit=completed[0].get('exit_code'),
            command_sha256=digest(completed[0].get('command', '').encode()),
            observed=observed, limit='one nonsecret case per boundary; no universal/zero-internal-IO claim')
        if not boundary:
            result['gap'] = 'Actual command did not establish all admitted material/tool/effect boundaries; fenced before review.'
            return
        methods, closure = method_material()
        result['method_closure'] = closure
        history = ('This is the first static review of these exact published implementation interfaces in this '
            'isolated qualification. Work retains the independent full Source1164 review; it is not input. '
            'Known prior1157 host attempt failed before provider start;17+29 mechanism controls passed, changed '
            'hot-control ERROR and inner UNKNOWN remain separate, without reconstruction. No code correction '
            'is selected here. The qualification probe is operational context, not source findings.\n').encode()
        items = [('history:qualification1167', history), *methods]
        for name in ('tools/direct-child/review_context.py',
                     'tools/coordinator-runtime/coordinator_runtime/opaque_review.py',
                     'tools/coordinator-runtime/coordinator_runtime/appserver.py',
                     'tools/coordinator-runtime/opaque-review1157.md'):
            items.append(('source:'+BASE+':'+name, (REPO/name).read_bytes()))
        items.append(('source:new1167-qualification-caller', Path(__file__).read_bytes()))
        items.append(('change-context', b'Published production b551 is unchanged. The new1167 harness composes its public functions for isolated qualification only.\n'))
        situation = ('You personally perform the unified static reviewer seat for collecting Work. gpt-xhigh is '
            'opaque invocation provenance; do not resolve or attest it or launch another model. Use the exact '
            'current unified procedure and every linked incorporated family/constituent/procedure/contract. '
            'Read whole supplied history first. Actors are the Work controller, Reviews consumer, material owners '
            'and original collector. Environment is a Linux host with an explicit admitted public CLI frontend '
            'and one owned profile/context; production interfaces are pinned b551, and the new caller is isolated. '
            'Goals are meaningful history-informed architecture-first/all9/27 review, independent judgment, '
            'effective material/tool/effect protections, owned continuation and honest finite custody. '
            'Responsiveness, independence, current authority and preservation must be considered together. '
            'Constraints: static read-only admitted snapshots, no tests, source writes, outside acquisition, '
            'delegation, private store inspection or underlying binding attestation. Challenge premises and '
            'constraints freely from evidence; no expected findings or repair choices are supplied. '
            'Return full attributable source-grounded observations, causal explanation, counterevidence, '
            'uncertainties, diagnosis, coverage and history entry as the method requires. History write authority '
            'is report-only: return the complete append entry for collector custody. First return architecture '
            'through organization, cross-change and purpose ONLY, then await continuation. State core files not '
            'read and partial source boundary; this is not full runtime/source or service acceptance. '
            'Include the earlier public qualification bridge from retained conversation without rereading its old file.')
        receipt, answer = await owner.turn('architecture', items, situation)
        result['turns'].append(dict(stage='architecture', receipt=receipt, answer_bytes=len((answer or '').encode())))
        if not receipt['answered']:
            result['gap'] = 'Architecture original incomplete; no continuation/fallback.'
            return
        result['bridge_recalled_in_architecture'] = nonce in answer
        if nonce not in answer:
            result['gap'] = 'Expected same-context public bridge recall absent; remaining-family input withheld.'
            return
        receipt, answer = await owner.turn('remaining', items,
            'Continue the remaining families and all27 constituent questions in this same context under the same '
            'exact current method, source, situation and independence. Preserve/revise architecture from evidence. '
            'Return full observations, diagnosis, counterevidence, uncertainties, coverage, core files not read '
            'and complete history append. Explicitly identify missing or partial work. No acceptance or correction '
            'choice. No new expected findings or repair hints are supplied.')
        result['turns'].append(dict(stage='remaining', receipt=receipt, answer_bytes=len((answer or '').encode())))
        result['substantive_method'] = 'Attributable captured returns require independent examination; no completeness/acceptance inferred.'
        result['status'] = 'CAPTURED-STAGES;SEMANTIC-EXTENT-REQUIRES-EXAMINATION' if receipt['answered'] else 'PARTIAL'
    except BaseException as exc:
        result['gap'] = type(exc).__name__+': sole operation interrupted/unavailable; no replay.'
        if owner.originals.pending:
            try:
                await owner.originals.collect_pending(15)
            except BaseException:
                result['collection'] = 'pending; exact owner retained, no process discovery'
        if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError)):
            result['cancelled'] = True
    finally:
        result['numeric_original_ENDs'] = [e['exit'] for e in owner.ends]
        result['pending_originals'] = len(owner.originals.owned)
        if not owner.originals.owned:
            result['local_close'] = owner.close()
        result['possible_effects'] = 'Normal provider storage unmeasured; local preparation retained; command attempts may have effects before fencing.'
        result['resources'] = account()
        write(ROOT/'actual-result.json', result)
        print(json.dumps(dict(status=result['status'], gap=result.get('gap'),
            boundary_command_evidence=result['boundary_command_evidence'],
            numeric_original_ENDs=result['numeric_original_ENDs'], pending_originals=result['pending_originals'])), flush=True)


def final_record():
    """One selected immutable proof assembly; no operation rerun."""
    account()
    source = source_check()
    selected = json.loads((ROOT/'ONE-ACTUAL-CONTEXT-SELECTED.json').read_text())
    assert selected['harness_sha256'] == digest(Path(__file__).read_bytes()), 'caller changed after actual selection'
    actual = json.loads((ROOT/'actual-result.json').read_text())
    proof = dict(source=source, interface=source_interface(), actual=actual,
        harness_sha256=digest(Path(__file__).read_bytes()), resources=account(),
        final_kind='ONE selected source-bound proof assembly of conserved original evidence; no provider replay',
        history='Prior1157 frozen failure and hot-control UNKNOWN unchanged; no full418/test correction.')
    write(ROOT/'FINAL-SELECTED-PROOF.json', proof)
    print(json.dumps(dict(final='written-once', status=actual['status'], actual_context_count=1)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['preflight','actual','final'])
    args = parser.parse_args()
    if (ROOT/'FINAL-SELECTED-PROOF.json').exists():
        parser.error('final proof already exists; no patch/export/rerun')
    event(dict(event='phase-registered', phase=args.phase, harness_sha256=digest(Path(__file__).read_bytes())))
    if args.phase == 'preflight':
        asyncio.run(preflight())
    elif args.phase == 'actual':
        asyncio.run(actual())
    else:
        final_record()


if __name__ == '__main__':
    main()
