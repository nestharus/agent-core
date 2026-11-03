"""Operator entry points. No command adopts existing collectors or logs in."""

import argparse
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
from .contracts import Refusal, canonical_uuid, encode, load_config, regular_path
from .dispatcher import Dispatcher
from .store import Store, private_directory


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
    schema = sub.add_parser("qualify-schema")
    schema.add_argument("--codex", default="codex")
    schema.add_argument("--output", required=True)
    enroll = sub.add_parser("enroll")
    enroll.add_argument("role")
    enroll.add_argument("--authority", required=True)
    enroll.add_argument("--delivery", action="store_true", help="Explicit role-lifetime outgoing delegation and real service actor")
    extend = sub.add_parser("delegate-delivery")
    extend.add_argument("role")
    extend.add_argument("--authority", required=True)
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
    sub.add_parser("service-unit")
    source = sub.add_parser("recover-source")
    source.add_argument("event")
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
    if args.command in {"init", "status"}:
        return store.status()
    if args.command == "enroll":
        grant = Board(store.config, args.role).grant(store, args.authority, delivery=args.delivery)
        store.enroll(args.role, grant)
        return {"grant": grant, "legacy_hold": store.enrollment(args.role)["legacy_hold"]}
    if args.command == "delegate-delivery":
        return Board(store.config, args.role).extend_delivery(store, args.authority)
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
    if args.command == "recover-source":
        role = store.one("SELECT role FROM events WHERE id=?", (args.event,))["role"]
        actual_actor(store.config["roles"][role]["owner"])
        return store.recover_source(args.event)
    if args.command == "service-unit":
        return service_unit(store.config, args.config)
    if args.command == "ack-alert":
        actor = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
        store.process_alert(args.occurrence, actor, read_record(args.receipt))
        return {"alert_processed": args.occurrence}
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
            print_json(operate(args, store))
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
