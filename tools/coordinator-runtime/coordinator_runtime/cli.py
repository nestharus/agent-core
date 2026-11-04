"""Operator entry points. No command adopts existing collectors or logs in."""

import argparse
import base64
import hashlib
import asyncio
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys

from .board import Board
from .cleanup import conserve, sweep
from .contracts import Refusal, canonical_uuid, encode, load_config, parse_json, regular_path
from .dispatcher import Dispatcher
from .store import Store, private_directory
from . import prospective, ordinary, windows


def print_json(value):
    print(encode(value), flush=True)


def read_record(path):
    return json.loads(regular_path(path).read_text())


def actual_actor(owner):
    actual = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
    if actual != owner:
        raise Refusal("current actor differs from actual enrolled owner; do not synthesize CODEX_SESSION_ID")
    return actual


def qualify_schema(codex, output):
    directory = private_directory(output)
    if list(directory.iterdir()):
        raise Refusal("schema output must be a fresh owned empty directory; retain earlier evidence")
    version = subprocess.run([codex, "--version"], check=True, capture_output=True, text=True).stdout.strip()
    subprocess.run([codex, "app-server", "generate-json-schema", "--experimental", "--out", str(directory)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    checks = {
        "v2/ThreadStartParams.json": {"ephemeral", "model", "modelProvider", "allowProviderModelFallback", "config"},
        "v2/ThreadStartResponse.json": {"model", "modelProvider", "reasoningEffort", "thread"},
        "v2/TurnStartParams.json": {"threadId", "input", "model", "effort", "outputSchema"},
        "v2/ThreadReadParams.json": {"threadId", "includeTurns"},
        "v2/ThreadUnsubscribeParams.json": {"threadId"},
        "v2/TurnInterruptParams.json": {"threadId", "turnId"},
    }
    for name, fields in checks.items():
        if not fields <= set(read_record(str(directory / name))["properties"]):
            raise Refusal(f"installed schema missing required API: {name}")
    receipt = {"cli_version": version, "schema_dir": str(directory),
               "checked": {name: sorted(fields) for name, fields in checks.items()},
               "qualification": "offline schema only; no app-server/model/cleanup behavior executed",
               "disposition": "retain for qualification and at least 24h plus consumer holds"}
    (directory / "qualification.json").write_text(encode(receipt)+"\n")
    return receipt


def parser():
    p = argparse.ArgumentParser(description="Opt-in coordinator dispatcher; default is no live activation")
    p.add_argument("--config")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser('processing-basis', help='Genuine Work: exact stopped software basis and future frontier')
    issue_processing = sub.add_parser('delegate-processing')
    issue_processing.add_argument('--selection', required=True)
    for name in ('processing-status', 'revoke-processing', 'processing-run', 'processing-source', 'processing-apply-control', 'processing-release'):
        item = sub.add_parser(name, help='Explicit software capability; no ordinary grant reactivation or native-owner claim')
        item.add_argument('capability')
        if name == 'processing-run':
            item.add_argument('--seconds', type=int, choices=range(1, 3601), required=True, metavar='1..3600')
            item.add_argument('--enable-models', action='store_true')
        if name in {'processing-source', 'processing-apply-control'}:
            item.add_argument('event')
        if name == 'processing-apply-control':
            item.add_argument('--attempt', required=True)
        if name == 'processing-release':
            item.add_argument('--controller', required=True)
            item.add_argument('--receipt', required=True)
    drain = sub.add_parser('retained-drain', help='Actual Work: one finite four-role retained software sweep, no intake or execution')
    drain.add_argument('--authority', required=True)
    drain.add_argument('--shared-rows', type=int, required=True)
    drain.add_argument('--shared-payload-bytes', type=int, required=True)
    drain.add_argument('--visits', type=int, choices=range(1, 4097), required=True, metavar='1..4096')
    drain.add_argument('--seconds', type=int, choices=range(1, 3601), required=True, metavar='1..3600')
    for name in ('retained-basis', 'delegate-retained', 'revoke-retained', 'retained-step'):
        item = sub.add_parser(name, help='Explicit bounded retained software custody; normal revocation stays intact')
        item.add_argument('role')
        if name == 'delegate-retained':
            item.add_argument('--policy', required=True)
        if name in {'revoke-retained', 'retained-step'}:
            item.add_argument('capability')
    sub.add_parser('window-basis', help='Current retained journal binding; no processing or hold waiver')
    advance = sub.add_parser('advance-window', help='Actual Work continues allocations and conserved duties')
    advance.add_argument('--receipt', required=True)
    boundary = sub.add_parser('authorize-prospective', help='Actual Work explicitly authorizes future work in unchanged original journal')
    boundary.add_argument('--selection', required=True)
    revoke_boundary = sub.add_parser('revoke-prospective')
    revoke_boundary.add_argument('epoch')
    semantic = sub.add_parser('ordinary-acceptance', help='Independent admitted actor decides exact current execution, distinct from reporting')
    semantic.add_argument('attempt')
    semantic.add_argument('--decision', choices=['accepted', 'rejected'], required=True)
    semantic.add_argument('--receipt', required=True)
    sub.add_parser('execution-pool', help='Inspect shared new-execution membership and next unreserved turn; no account probing')
    automatic=sub.add_parser('delegate-control',help='Actual source owner explicitly delegates prospective service control')
    automatic.add_argument('role')
    automatic.add_argument('--policy',required=True)
    automatic.add_argument('--authority',required=True)
    revoke_control=sub.add_parser('revoke-control')
    revoke_control.add_argument('role')
    revoke_control.add_argument('delegation')
    control_receipt=sub.add_parser('control-receipt',help='Actual recipient processes independent control duty, not business settlement')
    control_receipt.add_argument('role')
    control_receipt.add_argument('delivery')
    control_receipt.add_argument('--receipt',required=True)
    prepare=sub.add_parser('control-prepare',help='Prepare a bounded existing-owner delivery pointer; no native effect')
    prepare.add_argument('role')
    prepare.add_argument('delivery')
    prepare.add_argument('--selection',required=True)
    show_control=sub.add_parser('control-show',help='Read exact intent/correlation/uncertainty, never retry')
    show_control.add_argument('role')
    show_control.add_argument('intent')
    cancel_control=sub.add_parser('control-cancel',help='Withdraw prepared, never attempted/uncertain, control only')
    cancel_control.add_argument('role')
    cancel_control.add_argument('intent')
    send_control=sub.add_parser('control-send',help='Explicit one-shot selected channel; requires separate actual caller authority/applicability')
    send_control.add_argument('role')
    send_control.add_argument('intent')
    send_control.add_argument('--execute',action='store_true')
    schema = sub.add_parser("qualify-schema")
    schema.add_argument("--codex", default="codex")
    schema.add_argument("--output", required=True)
    enroll = sub.add_parser("enroll")
    enroll.add_argument("role")
    enroll.add_argument("--authority", required=True)
    enroll.add_argument("--delivery", action="store_true", help="Explicit role-lifetime outgoing delegation and real service actor")
    enroll.add_argument('--completion', action='store_true', help='Explicit bounded routine collector/file completion delegation')
    software = sub.add_parser('enroll-software', help='Actual Work/user grantor issues prospective delegation in a NEW journal; never native owner issuance')
    software.add_argument('role')
    software.add_argument('--authority', required=True)
    revoke_software = sub.add_parser('revoke-software', help='Actual Work grantor revokes only its own prospective software grant')
    revoke_software.add_argument('role')
    revoke_software.add_argument('--grant', required=True)
    extend = sub.add_parser("delegate-delivery")
    extend.add_argument("role")
    extend.add_argument("--authority", required=True)
    complete = sub.add_parser('delegate-completion')
    complete.add_argument('role')
    complete.add_argument('--authority', required=True)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("role")
    revoke.add_argument("--grant", required=True)
    legacy = sub.add_parser("reconcile-legacy")
    legacy.add_argument("role")
    legacy.add_argument("--receipt", required=True)
    admission = sub.add_parser("admit-package")
    admission.add_argument("package")
    admission.add_argument("--receipt", required=True)
    admission.add_argument("--accepted-receipt")
    effects = sub.add_parser("reconcile-effects")
    effects.add_argument("job")
    effects.add_argument("--token", required=True)
    effects.add_argument("--receipt", required=True)
    recovery=sub.add_parser('request-recovery',help='Actual owner queues exact redisposition or bounded remaining work; no direct model/effect')
    recovery.add_argument('job')
    recovery.add_argument('--token',required=True)
    recovery.add_argument('--attempt',required=True)
    recovery.add_argument('--receipt',required=True,help='use-diagnosis: exact diagnosis/selection with remaining:null; optional qualified publication_remainder basis and collector_continuity; remaining-work requests fresh diagnosis')
    for command in ('integration-closure-basis', 'retire-integration', 'integration-prestart-basis', 'withdraw-integration-prestart', 'integration-no-start-basis', 'withdraw-integration-no-start'):
        integration = sub.add_parser(command, help='Actual Work: closed execution only; all original duties retained')
        integration.add_argument('job')
        integration.add_argument('--token', required=True)
        if command in {'retire-integration', 'withdraw-integration-prestart', 'withdraw-integration-no-start'}:integration.add_argument('--receipt', required=True)
    window = sub.add_parser('integration-window-basis', help='Exact new inputs and conserved debt; no launch')
    window.add_argument('task')
    window.add_argument('--events', nargs='+', required=True)
    window = sub.add_parser('select-integration-window', help='Actual Work selects one bounded future batch with peer/custodian evidence')
    window.add_argument('--receipt', required=True)
    basis=sub.add_parser('publication-remainder-basis',help='Actual owner reads qualified publication operands; no request, new purpose, publication or launch')
    basis.add_argument('job')
    for name in ['token','attempt','diagnosis','selection']:basis.add_argument('--'+name,required=True)
    controls=sub.add_parser('owner-controls',help='Genuine coordinator reads its bounded pending inputs/recovery; no native wake inferred')
    controls.add_argument('role')
    controls.add_argument('--limit',type=int,choices=range(1,101),default=100,metavar='1..100')
    controls.add_argument('--after',help='Same-role input cursor from next_after')
    show=sub.add_parser('input-show',help='Actual owner reads immutable source and attributed derived decisions')
    show.add_argument('event')
    resolve=sub.add_parser('resolve-input',help='Actual owner supplies source_hash/mode/task/package/related_event/related_job/reason/evidence/remaining_obligations; see README')
    resolve.add_argument('event')
    resolve.add_argument('--receipt',required=True)
    hold = sub.add_parser("hold")
    hold.add_argument("event")
    hold.add_argument("--reason", required=True)
    release = sub.add_parser("release-hold")
    release.add_argument("event")
    release.add_argument("--receipt", required=True)
    conserved = sub.add_parser("conserve-artifact")
    conserved.add_argument("path")
    conserved.add_argument("--receipt", required=True)
    sub.add_parser("cleanup")
    catchup = sub.add_parser('owner-catchup')
    catchup.add_argument('role')
    catchup.add_argument('--after',type=int,required=True)
    catchup.add_argument('--through',type=int)
    sub.add_parser("service-unit")
    source = sub.add_parser("recover-source")
    source.add_argument("event")
    artifact = sub.add_parser('artifact-source')
    artifact.add_argument('attempt')
    artifact.add_argument('path')
    artifact.add_argument('--delivery',help='Exact already addressed consumer delivery, when caller is not the source owner')
    for command in ("delivery-show", "delivery-stage", "delivery-correct"):
        delivery = sub.add_parser(command)
        delivery.add_argument("role")
        delivery.add_argument("delivery")
        if command == "delivery-stage":
            delivery.add_argument("--stage", choices=["picked-up", "processed", "settled"], required=True)
            delivery.add_argument("--receipt", required=True)
        if command == "delivery-correct":
            delivery.add_argument("--receipt", required=True, help="Actual owner supersedes/reason/settlement correction")
    alert = sub.add_parser("ack-alert")
    alert.add_argument("occurrence")
    alert.add_argument("--receipt", required=True)
    basis = sub.add_parser('alert-retirement-basis', help='Exact source binding only; no eligibility or processing claim')
    basis.add_argument('occurrence')
    retirement = sub.add_parser('retire-alert', help='Genuine same source/consumer owner, processing+24h and every hold')
    retirement.add_argument('role')
    retirement.add_argument('occurrence')
    retirement.add_argument('--receipt', required=True)
    run = sub.add_parser("run")
    run.add_argument("--enable-models", action="store_true")
    return p


async def serve(store):
    runtime = Dispatcher(store)
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, runtime.stopping.set)
    loop.add_signal_handler(signal.SIGINT, runtime.stopping.set)
    await runtime.run(print_json)


def operate(args, store):
    if args.command in {'processing-basis', 'delegate-processing', 'processing-status', 'revoke-processing',
                        'processing-run', 'processing-source', 'processing-apply-control', 'processing-release'}:
        from . import processing
        boards = {r: processing.ProcessingBoard(store.config, r) for r in store.config['roles']}
        boards['Work'].store.acting_session(store.config['software_delegation']['grantor'])
        if args.command == 'processing-basis':
            return processing.basis(store, boards)
        if args.command == 'delegate-processing':
            return processing.select(store, boards, read_record(args.selection))
        if args.command == 'processing-status':
            return processing.status(store, args.capability)
        if args.command == 'revoke-processing':
            return processing.revoke(store, boards, args.capability)
        if args.command == 'processing-release':
            return processing.release(store, boards, args.capability, args.controller, read_record(args.receipt))
        store.processing = processing.Access(store, args.capability)
        store.processing.current()
        if args.command in {'processing-source', 'processing-apply-control'}:
            if not store.processing.event(store.event(args.event)):
                raise Refusal('source outside exact software processing selection')
            boards[store.event(args.event)['role']].verify_authority(store)
            if args.command == 'processing-apply-control':
                return processing.apply_control(store, args.event, args.attempt)
            return {'source': store.recover_source(args.event),
                    'resolution': store.input_resolution(args.event),
                    'responsibility': store.one('SELECT * FROM queue WHERE event=?', (args.event,))}
        if not args.enable_models or store.config.get('enabled') is not True:
            raise Refusal('processing-run needs unchanged enabled config and explicit --enable-models')
        qualified = read_record(store.config['protocol_qualification'])
        if qualified['cli_version'] != store.config['protocol_cli_version']:
            raise Refusal('offline protocol qualification differs from configured CLI')
        asyncio.run(processing.run(store, boards, args.capability, args.seconds, print_json))
        return {'controller': store.controller, 'meaning': 'parent must collect original END; inspect processing-status/errors/holds'}
    if args.command == 'retained-drain':
        from .retained import drain
        return drain(store, args.authority, args.shared_rows, args.shared_payload_bytes,
                     args.visits, args.seconds, print_json)
    if args.command in {'retained-basis', 'delegate-retained', 'revoke-retained', 'retained-step'}:
        from .retained import RetainedBoard
        board = RetainedBoard(store.config, args.role)
        if args.command == 'retained-basis':
            return board.retained_basis(store)
        if args.command == 'delegate-retained':
            return board.delegate_retained(store, read_record(args.policy))
        if args.command == 'revoke-retained':
            return board.revoke_retained(store, args.capability)
        return board.retained_step(store, args.capability)
    if args.command in {'integration-closure-basis', 'retire-integration', 'integration-window-basis', 'select-integration-window', 'integration-prestart-basis', 'withdraw-integration-prestart', 'integration-no-start-basis', 'withdraw-integration-no-start'}:
        actor = actual_actor(store.enrollment('Work')['owner'])
        Board(store.config, 'Work').verify_authority(store)
        if args.command == 'integration-no-start-basis':return store.integration_no_start_basis(args.job, args.token)
        if args.command == 'withdraw-integration-no-start':return store.withdraw_integration_no_start(args.job, args.token, actor, read_record(args.receipt))
        if args.command == 'integration-prestart-basis':return store.integration_prestart_basis(args.job, args.token)
        if args.command == 'withdraw-integration-prestart':return store.withdraw_integration_prestart(args.job, args.token, actor, read_record(args.receipt))
        if args.command == 'integration-closure-basis':return store.integration_closure_basis(args.job, args.token)
        if args.command == 'retire-integration':return store.retire_integration(args.job, args.token, actor, read_record(args.receipt))
        if args.command == 'integration-window-basis':return store.integration_window_basis(args.task, args.events)
        return store.select_integration_window(actor, read_record(args.receipt))
    if args.command in {'window-basis', 'advance-window'}:
        actor = actual_actor(store.enrollment('Work')['owner'])
        Board(store.config, 'Work').verify_authority(store)
        if args.command == 'advance-window':
            return windows.advance(store, actor, read_record(args.receipt))
        if not store.config.get('window_service'):
            raise Refusal('recurring allocation windows not selected')
        with store.tx():
            return windows.basis(store)
    if args.command in {'authorize-prospective', 'revoke-prospective'}:
        actor = actual_actor(store.config['roles']['Work']['owner'])
        if args.command == 'authorize-prospective':
            return prospective.select(store, actor, read_record(args.selection))
        return prospective.revoke(store, actor, args.epoch)
    if args.command == 'ordinary-acceptance':
        actor = canonical_uuid(os.environ.get('CODEX_SESSION_ID'))
        return asyncio.run(ordinary.accept(store, actor, args.attempt, args.decision, read_record(args.receipt)))
    if args.command == 'execution-pool':
        return store.execution_pool.status()
    if args.command in {"init", "status"}:
        return store.status()
    if args.command=='delegate-control':
        return Board(store.config,args.role).delegate_control(store,parse_json(regular_path(args.policy).read_text()),args.authority)
    if args.command=='revoke-control':
        return Board(store.config,args.role).revoke_control(store,args.delegation)
    if args.command=='control-receipt':
        return Board(store.config,args.role).control_receipt(args.delivery,read_record(args.receipt))
    if args.command=='control-prepare':
        return Board(store.config,args.role).control_prepare(store,args.delivery,parse_json(regular_path(args.selection).read_text()))
    if args.command=='control-show':
        return Board(store.config,args.role).control_show(args.intent)
    if args.command=='control-cancel':
        return Board(store.config,args.role).control_cancel(args.intent)
    if args.command=='control-send':
        if not args.execute:raise Refusal('explicit control-send --execute required; prepare/show has no native effect')
        return Board(store.config,args.role).control_send(store,args.intent)
    if args.command == "enroll":
        grant = Board(store.config, args.role).grant(store, args.authority, delivery=args.delivery, completion=args.completion)
        store.enroll(args.role, grant)
        return {"grant": grant, "legacy_hold": store.enrollment(args.role)["legacy_hold"]}
    if args.command == 'enroll-software':
        grant = Board(store.config, args.role).grant_software(store, args.authority)
        store.enroll(args.role, grant)
        return {'grant': grant, 'legacy_hold': store.enrollment(args.role)['legacy_hold'],
                'native_owner_issuance': False, 'historical_duties': 'retained in their original authority epochs'}
    if args.command == 'revoke-software':
        receipt = Board(store.config, args.role).revoke_software(store, args.grant)
        with store.tx():
            store.db.execute('UPDATE enrollments SET intake=0 WHERE role=? AND grant_id=?', (args.role, args.grant))
        return receipt
    if args.command == "delegate-delivery":
        return Board(store.config, args.role).extend_delivery(store, args.authority)
    if args.command == 'delegate-completion':
        return Board(store.config, args.role).extend_completion(store, args.authority)
    if args.command == "revoke":
        Board(store.config, args.role).revoke(args.grant)
        with store.tx():
            store.db.execute("UPDATE enrollments SET intake=0 WHERE role=? AND grant_id=?", (args.role, args.grant))
        return {"revoked": args.grant, "existing_responsibilities": "retained"}
    if args.command == "reconcile-legacy":
        actor = actual_actor(store.enrollment(args.role)["owner"])
        store.reconcile_legacy(args.role, actor, read_record(args.receipt))
        return {"role": args.role, "legacy_reconciled": True}
    if args.command == "admit-package":
        actor = actual_actor(store.enrollment("Branch")["owner"])
        store.admit(args.package, actor, read_record(args.receipt), read_record(args.accepted_receipt) if args.accepted_receipt else None)
        return {"package": args.package, "admitted_by": actor}
    if args.command == "reconcile-effects":
        job = store.job(args.job, args.token)
        actor = actual_actor(store.config["roles"][job["role"]]["owner"])
        store.reconcile_effects(args.job, args.token, actor, read_record(args.receipt))
        return {"job": args.job, "effects_reconciled": True}
    if args.command=='request-recovery':
        job=store.job(args.job,args.token)
        actor=actual_actor(store.enrollment(job['role'])['owner'])
        board=Board(store.config,job['role'])
        board.verify_authority(store)
        return store.request_recovery(args.job,args.token,args.attempt,actor,read_record(args.receipt),publication_board=board)
    if args.command=='publication-remainder-basis':
        job=store.job(args.job,args.token)
        actual_actor(store.enrollment(job['role'])['owner'])
        board=Board(store.config,job['role'])
        board.verify_authority(store)
        return store.publication_remainder_basis(args.job,args.token,args.attempt,args.diagnosis,args.selection,board)
    if args.command=='owner-controls':
        actual_actor(store.enrollment(args.role)['owner'])
        Board(store.config,args.role).verify_authority(store)
        return store.owner_controls(args.role,args.limit,args.after)
    if args.command in {'input-show','resolve-input'}:
        role=store.one('SELECT role FROM events WHERE id=?',(args.event,))
        if not role:raise Refusal('exact owned input required')
        actor=actual_actor(store.enrollment(role['role'])['owner'])
        Board(store.config,role['role']).verify_authority(store)
        if args.command=='resolve-input':return store.resolve_input(args.event,actor,read_record(args.receipt))
        return {'source':store.recover_source(args.event),
                'state':store.one('SELECT id,hash,state,classification,classifier,ack,processed_at,hold,error FROM events WHERE id=?',(args.event,)),
                'resolutions':store.rows('SELECT * FROM input_resolutions WHERE event=? ORDER BY version',(args.event,)),
                'responsibility':store.one('SELECT * FROM queue WHERE event=?',(args.event,))}
    if args.command == "hold":
        store.set_hold(args.event, args.reason)
        return {"held": args.event}
    if args.command == "release-hold":
        role = store.one("SELECT role FROM events WHERE id=?", (args.event,))["role"]
        actual_actor(store.config["roles"][role]["owner"])
        if not read_record(args.receipt):
            raise Refusal("hold release needs conservation/recovery evidence")
        store.set_hold(args.event, None)
        return {"released_hold": args.event}
    if args.command == "conserve-artifact":
        actor = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
        conserve(store, args.path, actor, read_record(args.receipt))
        return {"conserved": args.path}
    if args.command == "cleanup":
        return sweep(store)
    if args.command == 'owner-catchup':
        return Board(store.config,args.role).owner_catchup(store,args.after,args.through)
    if args.command == "recover-source":
        role = store.one("SELECT role FROM events WHERE id=?", (args.event,))["role"]
        actual_actor(store.config["roles"][role]["owner"])
        return store.recover_source(args.event)
    if args.command == 'artifact-source':
        row=store.one('SELECT * FROM artifact_custody WHERE attempt=? AND path=?',(args.attempt,args.path))
        if not row:raise Refusal('artifact custody not recorded for this exact source')
        caller=canonical_uuid(os.environ.get('CODEX_SESSION_ID'))
        if caller != row['owner']:
            delivery=store.one('SELECT * FROM outboxes WHERE id=?',(args.delivery,)) if args.delivery else None
            target=store.config.get('delivery',{}).get('recipients',{}).get(delivery['recipient'],{}) if delivery else {}
            listed=json.loads(delivery['payload']).get('artifact_witnesses',[]) if delivery else []
            if (not delivery or not delivery['board_receipt'] or target.get('session')!=caller or
                    not any((w.get('source_attempt')==args.attempt or w.get('source_context')==args.attempt) and w.get('path')==args.path and w.get('sha256')==row['sha256'] for w in listed)):
                raise Refusal('artifact source is private to its actual owner or exact addressed consumer')
        body=store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(row['sha256'],))['body']
        if hashlib.sha256(body).hexdigest()!=row['sha256']:raise Refusal('conserved artifact bytes no longer match the exact witness')
        if len(body)>store.config['limits'].get('max_artifact_bytes',33554432):raise Refusal('source exceeds selected export bound; retained without truncation')
        return {**row,'body_base64':base64.b64encode(body).decode()}
    if args.command == "service-unit":
        return service_unit(store.config, args.config)
    if args.command == "ack-alert":
        actor = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
        store.process_alert(args.occurrence, actor, read_record(args.receipt))
        return {"alert_processed": args.occurrence}
    if args.command == 'alert-retirement-basis':
        from .capacity import retirement_basis
        alert, outbox, basis = retirement_basis(store, args.occurrence)
        return {'alert': alert['id'], 'delivery': outbox['id'], 'basis': basis, 'eligibility': 'not established'}
    if args.command == 'retire-alert':
        return Board(store.config, args.role).retire_alert(store, args.occurrence, read_record(args.receipt))
    if args.command == "run":
        return run_selected(args, store)
    raise Refusal("unknown operator command")


def run_selected(args, store):
    if not args.enable_models or store.config.get("enabled") is not True:
        raise Refusal("run requires explicit enabled configuration and --enable-models; no implicit cutover")
    qualified = read_record(store.config["protocol_qualification"])
    if qualified["cli_version"] != store.config["protocol_cli_version"]:
        raise Refusal("offline schema qualification differs from configured CLI")
    asyncio.run(serve(store))
    return {"stopped": "owned tasks collected; inspect status for unresolved holds"}


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "qualify-schema":
            print_json(qualify_schema(args.codex, args.output))
            return 0
        if not args.config:
            raise Refusal("--config is required")
        config = load_config(args.config)
        if args.command in {"delivery-show", "delivery-stage", "delivery-correct"}:
            board = Board(config, args.role)
            if args.command == "delivery-show":
                value = board.show_delivery(args.delivery)
            elif args.command == "delivery-correct":
                value = board.correct_owner_return(args.delivery, read_record(args.receipt))
            else:
                value = board.delivery_stage(args.delivery, args.stage, read_record(args.receipt))
            print_json(value)
            return 0
        store = Store(config)
        try:
            value = operate(args, store)
            print_json(value)
            if args.command == 'execution-pool' and value.get('state') == 'held':
                return 2
        finally:
            store.close()
        return 0
    except (Refusal, ValueError, KeyError, OSError, sqlite3.Error) as exc:
        print_json({"state": "held", "error": f"{type(exc).__name__}: {str(exc)[:1000]}"})
        return 2


def stop_budget(config):
    d = config["deadlines"]
    # Two bounded turns, interruption, six bounded metadata subprocesses,
    # initialization/start/read/unsubscribe RPCs and exact owned teardown.
    return int(2*max(d["task"], d["classify"])+d["interrupt"]+6*46+180+3*d["shutdown"]+60)


def service_unit(config, path):
    cli = str(Path(__file__).resolve().parents[1]/"coordinator")
    return {"stop_budget_seconds": stop_budget(config), "unit":
        "[Service]\nType=simple\nUMask=0077\n"
        f"ExecStart=/usr/bin/python3 {cli} --config {path} run --enable-models\n"
        f"Restart=no\nKillMode=mixed\nTimeoutStopSec={stop_budget(config)}\nStandardOutput=null\nStandardError=null\n"}


if __name__ == "__main__":
    sys.exit(main())
