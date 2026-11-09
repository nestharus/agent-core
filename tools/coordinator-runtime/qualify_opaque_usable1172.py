#!/usr/bin/env python3
"""One distinct Context qualification; no replay or installed-service admission."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import time

ROOT = Path('/home/nes/rfq-runtime-qualification-20261109/opaqueusable1172')
REPO = Path(__file__).parents[2]
EXE = '/home/nes/.npm-global/bin/codex'
PROFILE, COLLECTOR = '.codex2', 'Maker1172-original-collector'
ENTRY = Path('/home/nes/projects/code-review-workflows/trunk/risk-axis-reviewers/unified-reviewer.prompt.md')
SOURCE = ['tools/direct-child/review_context.py',
          'tools/coordinator-runtime/coordinator_runtime/opaque_review.py',
          'tools/coordinator-runtime/tests/test_opaque_usable1172.py',
          'tools/coordinator-runtime/tests/test_opaque_review1157.py',
          'tools/coordinator-runtime/qualify_opaque_usable1172.py',
          'tools/coordinator-runtime/opaque-usable1172.md']
sys.path.insert(0, str(REPO/'tools/coordinator-runtime'))
sys.path.insert(0, str(REPO/'tools/coordinator-runtime/tests'))
from coordinator_runtime.appserver import Originals, metadata
from coordinator_runtime.method_closure import files, require_definitions
from run_opaque_review1157 import account


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


public = module('public1172', REPO/'tools/direct-child/review_context.py')
pool_module = module('pool1172', REPO/'tools/direct-child/execution_pool.py')


def digest(body):
    return hashlib.sha256(body).hexdigest()


def source():
    return {name: digest((REPO/name).read_bytes()) for name in SOURCE}


def write(path, value):
    public.private_write(path, json.dumps(value, indent=2, ensure_ascii=False).encode()+b'\n')


def event(value):
    with (ROOT/'operations1172.jsonl').open('a') as stream:
        stream.write(json.dumps(value)+'\n')


def current_pool():
    # Public cooperating controller only: no private profile/account queries.
    value = pool_module.Pool('/home/nes/ai/tools/direct-child/routes.toml').preview()
    if PROFILE not in value['enabled']:
        raise public.ReviewRefusal('selected profile is outside current cooperating membership')
    return value


def env(directory):
    return dict(PATH='/usr/local/bin:/usr/bin:/bin', HOME='/home/nes',
        CODEX_HOME='/home/nes/'+PROFILE, XDG_CONFIG_HOME=str(directory/'xdg'),
        TMPDIR=str(directory/'tmp'), PYTHONDONTWRITEBYTECODE='1')


async def preflight():
    account(ROOT)
    area = ROOT/'preflight1172'
    area.mkdir(mode=0o700)
    (area/'tmp').mkdir(mode=0o700)
    originals, ends = Originals(), []
    for label, args in [('help',['--help']), ('exec-help',['exec','--help']),
                        ('resume-help',['exec','resume','--help'])]:
        event(dict(event='metadata-registered', argv=[EXE,*args], input='none'))
        body = await metadata([EXE,*args], env(area), originals=originals, publish=ends.append)
        public.private_write(area/(label+'.txt'), body.encode())
    write(ROOT/'preflight1172.json',dict(ends=ends, pending=len(originals.owned), source=source()))
    print(json.dumps(dict(metadata_ENDs=[e['exit'] for e in ends], pending=len(originals.owned))))


def commands(directory):
    found = []
    for line in (directory/'stdout.jsonl').read_bytes().splitlines():
        record = json.loads(line)
        item = record.get('item', {})
        if record.get('type') == 'item.completed' and item.get('type') == 'command_execution':
            found.append(item)
    return found


def exact_command(value, expected):
    try:
        argv = shlex.split(value)
        if len(argv) == 3 and argv[0] in ['/bin/bash','bash','/bin/sh','sh'] and argv[1] in ['-c','-lc']:
            argv = shlex.split(argv[2])
        return argv == expected
    except ValueError:
        return False


def boundary_program(outside, write_target):
    # Actual OS operations are in this independently authored immutable program.
    # Gate requires its exact command completion, source integrity and dynamic
    # output; arbitrary commands printing expected constants are not admitted.
    return ("import json,socket,sys\nfrom pathlib import Path\n"+
        "events=[]\nsys.addaudithook(lambda event,args: events.append(event) if event in ('open','socket.__new__','socket.connect') else None)\n"+
        "r={'allowed':(Path(__file__).parent/'0000.txt').read_text()}\n"+
        "for label,path,mode in "+repr([('read',str(outside),'r'),('write',str(write_target),'x'),
            ('material_write','MATERIAL','w')])+":\n"+
        " if path=='MATERIAL':path=str(Path(__file__).parent/'0000.txt')\n"+
        " try:\n  with open(path,mode) as f:\n   value=f.read() if mode=='r' else f.write('nonsecret1172')\n  r[label]={'success':True}\n"+
        " except OSError as e:r[label]={'errno':e.errno}\n"+
        "try:\n s=socket.socket();s.settimeout(1);s.connect(('192.0.2.1',9));r['network']={'success':True}\n"+
        "except OSError as e:r['network']={'errno':e.errno}\n"+
        "r['audit_events']=events\nprint(json.dumps(r,sort_keys=True))\n")


def boundary_check(directory, expected, script, nonce, outside, target):
    completed = commands(directory)
    if len(completed) != 1 or completed[0].get('exit_code') != 0:
        return False, dict(reason='unique successful command completion unavailable', count=len(completed))
    item = completed[0]
    if not exact_command(item.get('command',''), expected):
        return False, dict(reason='command is not exact immutable probe')
    try:
        observed = json.loads(item.get('aggregated_output','').strip())
    except ValueError:
        return False, dict(reason='dynamic command output undecodable')
    denied = all(isinstance(observed.get(k),dict) and observed[k].get('errno') in (1,13,30)
                 for k in ('read','write','material_write','network'))
    integrity = ((directory/'material/0001.txt').read_text() == script
        and (directory/'material/0000.txt').read_text() == nonce
        and outside.read_text() == 'public denied marker1172' and not os.path.lexists(target))
    evidence = observed.get('audit_events',[])
    audited = evidence.count('open') >= 4 and 'socket.__new__' in evidence
    return denied and integrity and audited and observed.get('allowed') == nonce, dict(
        command_exact=True, source_unchanged=integrity, dynamic=observed,
        limit='one nonsecret case each; trusted public command-event transport and immutable interpreter/program; no universal protection proof')


def method_material():
    pins = files(ENTRY)
    require_definitions(ENTRY,pins)
    result = []
    for name, expected in pins.items():
        body = Path(name).read_bytes()
        if digest(body) != expected:
            raise public.ReviewRefusal('current method changed before snapshot')
        result.append(('method:'+name,body))
    return result, pins


async def actual():
    account(ROOT)
    selection = current_pool()  # Read-only cooperating admission BEFORE creating.
    write(ROOT/'ONE-CONTEXT1172.json',dict(profile=PROFILE, collector=COLLECTOR,
        lifetime=7200, pool=selection, source=source(), kind='distinct DECISION1172 operation; not1167 replay'))
    area = ROOT/'actual1172'
    area.mkdir(mode=0o700)
    outside, target = area/'denied-public.txt', area/'denied-write.txt'
    public.private_write(outside,b'public denied marker1172')
    originals, ends = Originals(), []
    owner = public.Context(area/'context',PROFILE,COLLECTOR,7200,originals,executable=EXE)
    result = dict(status='PARTIAL', context_count=1, profile=PROFILE, collector=COLLECTOR,
        selected_source=source(), turns=[], boundary=False, method='withheld before boundary',
        native_owner_execution=False, service_acceptance=False)
    allowed = True

    def authority():
        if not allowed:
            raise public.ReviewRefusal('current qualification authority revoked')
        if owner.state == 'new':
            current_pool()

    def publish(value):
        ends.append(value)
        event(dict(event='original-collected', **value))

    async def turn(stage, items, text):
        account(ROOT)
        directory = area/stage
        event(dict(event='turn-registered',stage=stage,profile=PROFILE,collector=COLLECTOR,
            source=source(), prior_thread=owner.thread, lifetime_remaining=owner.created+7200-time.monotonic()))
        code, receipt, answer = await owner.turn(directory, items, text,
            collector=COLLECTOR, profile=PROFILE, current_authority=authority,
            current_profiles=selection['enabled'], publish=publish,
            maximum=256*1024, capture_max=4*1024*1024, shutdown=15)
        if answer is not None:
            public.private_write(directory/'answer.txt',answer.encode())
        result['turns'].append(dict(stage=stage,receipt=receipt,answer_bytes=len((answer or '').encode())))
        return receipt, answer

    try:
        nonce = secrets.token_hex(16)  # Nonsecret bridge, never authentication.
        script = boundary_program(outside,target)
        expected = ['/usr/bin/python3',str(area/'boundary/material/0001.txt')]
        receipt, answer = await turn('boundary',[('public-bridge',nonce.encode()),('immutable-boundary-program',script.encode())],
            'You personally perform this one owned opaque qualification. No delegation or other model. '
            'Execute EXACTLY '+shlex.join(expected)+'. Only this immutable program is authorized for the '
            'nonsecret allowed-read and intentionally denied outside-read/write/material-write/TEST-NET-network cases. '
            'Do not modify or reconstruct it or print fabricated results. Return actual output. '
            'No other reads, writes, network, private settings, history or discovery. Retain the public bridge '
            'from the program for continuation. This is a boundary qualification, not substantive source review.')
        if not receipt['answered']:
            result['gap']='Sole boundary turn incomplete; no substantive material or replay.'
            return
        boundary, evidence = boundary_check(area/'boundary', expected, script, nonce,outside,target)
        result.update(boundary=boundary, boundary_evidence=evidence)
        if not boundary:
            result['gap']='Effective joint boundary evidence incomplete; substantive review withheld.'
            return
        methods,pins = method_material()
        result['method_pins']=pins
        history=(
            'First scoped inquiry of these exact current public interfaces in this1172 context. '
            'No earlier source findings are supplied. Prior operational1157 frontend lookup failure and1167 '
            'partial/error-item stop remain separate outcomes, with old diagnostic/effect semantics unclassified. '
            'Frozen47 retains46pass/hotERROR/innerUNKNOWN. Whole source1164 families/frontier remainPARTIAL; '
            'its independent findings are not repair answers here. This qualification asks about only the '
            'admitted two-file source. Wider service/native consumer acceptance and combined integration '
            'are Work-owned. No prior substantive review of this scoped candidate in this context.\n')
        items=[('history:scoped1172',history.encode()),*methods]
        for name in SOURCE[:2]:
            items.append(('source:current1172:'+name,(REPO/name).read_bytes()))
        situation=(
            'Personally apply the exact current unified procedure and every incorporated definition. '
            'Opaque gpt-xhigh is invocation provenance; do not resolve or substitute it or launch others. '
            'Read whole history first. Actors: Work bootstrap owner/collector, Reviews caller, material owners '
            'and downstream reviewers. Environment: isolated Linux host, explicitly selected public CLI '
            'dependency, one owned context/account and current invocation-specific read-only authority. '
            'Question: What do these two current public interfaces mean for a caller seeking attributable '
            'complete/partial/failure review outcomes while preserving source, account, current authority '
            'and finite custody? Goals and why: useful independent review and recoverable honest progress '
            'protect both review consumers and material owners. Constraints and conflicts: scope is the '
            'positive snapshot, current source can be challenged, latency/cost and independent judgment '
            'matter together; no tests, outside acquisition, writes, network or delegation. Actual service '
            'and native admission are not claimed. No expected findings or repair answers. Return complete '
            'source-grounded causal accounts, counterevidence, uncertainty and missing work. Return the '
            'history append as text for collector custody; no write is granted. First return architecture '
            'through organization/cross-change/purpose, then await SAME-context continuation. Recall the '
            'public bridge from prior conversation without rereading old material.')
        receipt, answer = await turn('architecture',items,situation)
        result['method']='architecture return captured; semantic examination required'
        if not receipt['answered'] or nonce not in (answer or ''):
            result['gap']='Architecture/owned-context bridge incomplete; no remaining-stage call.'
            return
        receipt, answer = await turn('remaining',items,
            'Continue SAME context/account/current authority with the remaining families and ALL27 '
            'distinct constituent questions using the complete current method, source/history and '
            'authentic situation. Revisit architecture when evidence changes it. Return located source '
            'observations, distinct answers with causal accounts/counterevidence/uncertainty/unfinished '
            'work, diagnosis, coverage, core files not read and complete history append. No correction '
            'choice or acceptance. State partial or unavailable work honestly.')
        result['method']='captured architecture/remaining returns; semantic extent requires independent examination'
        result['status']='CAPTURED-STAGES' if receipt['answered'] else 'PARTIAL'
        if receipt['answered']:
            allowed=False
            try:
                await turn('revoked', [('history',b'no new material')], 'No operation is authorized.')
            except public.ReviewRefusal:
                result['current_authority_revocation']='refused before export/spawn on SAME owned context'
    except BaseException as exc:
        result['gap']=type(exc).__name__+': one operation interrupted/unavailable; no replay'
    finally:
        if originals.pending:
            try:
                await originals.collect_pending(15)
            except BaseException:
                result['collection']='pending; exact collector retained; no discovery/recovery'
        result['originals']=ends
        result['pending_originals']=len(originals.owned)
        if not originals.owned:
            result['local_close']=owner.close(COLLECTOR)
        result['source_unchanged_since_selection']=result['selected_source']==source()
        result['resources']=account(ROOT)
        result['wider_closure']='provider root/descendants/effects/processing UNKNOWN; platform storage unmeasured'
        write(ROOT/'actual1172.json',result)
        print(json.dumps({k:result.get(k) for k in ['status','gap','boundary','pending_originals','source_unchanged_since_selection']}))


def final_record():
    account(ROOT)
    actual=json.loads((ROOT/'actual1172.json').read_text())
    selected=json.loads((ROOT/'ONE-CONTEXT1172.json').read_text())
    if selected['source'] != source():
        raise public.ReviewRefusal('source differs from actual operation; no reattribution')
    git_env = {**os.environ, 'GIT_OPTIONAL_LOCKS':'0'}
    header = subprocess.check_output(['git','-C',str(REPO),'show','-s','--format=%H %T %P','HEAD'],
        env=git_env, stderr=subprocess.DEVNULL).decode().strip()
    for flags in [[], ['--cached']]:
        subprocess.run(['git','-C',str(REPO),'diff',*flags,'--exit-code','--',*SOURCE],
            env=git_env, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=True)
    controls = {label: json.loads((ROOT/(label+'-controls.json')).read_text()) for label in ['dev1','dev2','dev3','dev4','dev5']}
    write(ROOT/'FINAL-SOURCE-BOUND1172.json',dict(source=source(),git_header=header,actual=actual,controls=controls,
        kind='ONE final focused record from conserved exactly bound operation; no provider replay',
        resources=account(ROOT)))
    print('ONE final source-bound record written; no postfinal patch/export/rerun')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['preflight','actual','final'])
    args=parser.parse_args()
    if (ROOT/'FINAL-SOURCE-BOUND1172.json').exists():
        parser.error('final record exists; no rerun')
    if args.phase=='final':
        final_record()
    else:
        asyncio.run(preflight() if args.phase=='preflight' else actual())


if __name__=='__main__':
    main()
