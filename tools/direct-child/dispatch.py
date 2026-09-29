#!/usr/bin/env python3
"""Contextual direct dispatcher: resolve a route from seat and class, then run
one native Codex or Claude child in the foreground. See README.md."""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "routes.toml"
CODEX_LAUNCHER = HERE.parent / "direct-codex-child" / "launch.sh"
CLAUDE_EMPTY_MCP = '{"mcpServers":{}}'
CLAUDE_SETTINGS = '{"autoMemoryEnabled":false}'
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
PROFILE = re.compile(r"\.?[A-Za-z0-9][A-Za-z0-9._-]*")
PROVIDERS = ("codex", "claude")
PASSES = ("generative", "corrective", "unspecified")


class Refusal(Exception):
    """Invalid input or config; nothing was launched or written."""


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest) is not None:
            parser.error(f"duplicate {option_string}")
        setattr(namespace, self.dest, values)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="dispatch.py", allow_abbrev=False,
        description="Resolve a contextual route and run one foreground native child.")
    for flag in ("--cwd", "--prompt", "--runs-dir", "--id"):
        parser.add_argument(flag, action=Once, required=True)
    for flag in ("--seat", "--class", "--basis", "--pass", "--route", "--model",
                 "--provider", "--effort", "--profile", "--override-reason", "--config"):
        parser.add_argument(flag, action=Once)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


# ---------------------------------------------------------------- config

def load_config(path):
    try:
        raw = path.read_bytes()
        config = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise Refusal(f"cannot read config {path}: {error}") from error
    validate_config(config)
    return config, hashlib.sha256(raw).hexdigest()


def _table(config, key):
    value = config.get(key)
    if not isinstance(value, dict) or not value:
        raise Refusal(f"config: [{key}] must be a nonempty table")
    return value


def _string(value, where):
    if not isinstance(value, str) or not value:
        raise Refusal(f"config: {where} must be a nonempty string")
    return value


def _strings(value, where):
    if (not isinstance(value, list) or not value
            or not all(isinstance(item, str) and PROFILE.fullmatch(item) for item in value)
            or len(set(value)) != len(value)):
        raise Refusal(f"config: {where} must be a nonempty list of distinct names")
    return value


def _binding(binding, where, providers):
    if not isinstance(binding, dict):
        raise Refusal(f"config: {where} must be a table")
    provider = _string(binding.get("provider"), f"{where}.provider")
    if provider not in providers:
        raise Refusal(f"config: {where}.provider {provider!r} is not a configured provider")
    if not NAME.fullmatch(_string(binding.get("model"), f"{where}.model")):
        raise Refusal(f"config: {where}.model must be a native model id")
    effort = _string(binding.get("effort"), f"{where}.effort")
    if effort not in providers[provider]["efforts"]:
        raise Refusal(f"config: {where}.effort {effort!r} is not a {provider} effort")


def validate_config(config):
    _string(_table(config, "rotation").get("state_dir"), "rotation.state_dir")
    providers = _table(config, "providers")
    for name, provider in providers.items():
        if name not in PROVIDERS or not isinstance(provider, dict):
            raise Refusal(f"config: unsupported provider {name!r}")
        pool = _strings(provider.get("pool"), f"providers.{name}.pool")
        manual = _strings(provider.get("manual_profiles"), f"providers.{name}.manual_profiles")
        if not set(pool) <= set(manual):
            raise Refusal(f"config: providers.{name}.pool must be within manual_profiles")
        if name == "codex" and not set(manual) <= {".codex", ".codex2", ".codex3",
                                                ".codex4", ".codex5"}:
            raise Refusal("config: codex profiles must be .codex through .codex5 (excluding .codex1)")
        _strings(provider.get("efforts"), f"providers.{name}.efforts")
    routes = _table(config, "routes")
    for name, route in routes.items():
        _binding(route, f"routes.{name}", providers)
    for name, alias in config.get("aliases", {}).items():
        _binding(alias, f"aliases.{name}", providers)
    classes = _table(config, "classes")
    if "unknown" not in classes:
        raise Refusal("config: classes.unknown is required")
    for name, entry in classes.items():
        if not isinstance(entry, dict) or type(entry.get("requires_basis")) is not bool:
            raise Refusal(f"config: classes.{name}.requires_basis must be true or false")
        if entry.get("route") not in routes:
            raise Refusal(f"config: classes.{name}.route is not a configured route")
    if classes["unknown"]["requires_basis"]:
        raise Refusal("config: classes.unknown cannot require a basis")
    for name, seat in _table(config, "seats").items():
        if not isinstance(seat, dict) or (("route" in seat) == ("by_class" in seat)):
            raise Refusal(f"config: seats.{name} needs exactly one of route or by_class")
        if "route" in seat and seat["route"] not in routes:
            raise Refusal(f"config: seats.{name}.route is not a configured route")
        if "by_class" in seat:
            by_class = seat["by_class"]
            if not isinstance(by_class, dict) or set(by_class) != set(classes):
                raise Refusal(f"config: seats.{name}.by_class must cover exactly the classes")
            if not all(route in routes for route in by_class.values()):
                raise Refusal(f"config: seats.{name}.by_class names an unconfigured route")
    if _table(config, "legacy").get("route") not in routes:
        raise Refusal("config: legacy.route is not a configured route")


# ------------------------------------------------------------ resolution

def resolve(config, args):
    """Explicit route/model, else seat, else class, else legacy default."""
    classes, seats, routes = config["classes"], config["seats"], config["routes"]
    klass = getattr(args, "class")
    if klass is None and args.basis is not None:
        raise Refusal("--basis needs --class")
    class_source = "supplied" if klass is not None else "not supplied"
    klass = klass or "unknown"
    if klass not in classes:
        raise Refusal(f"unknown class {klass!r}; configured: {', '.join(classes)}")
    if classes[klass]["requires_basis"] and not (args.basis or "").strip():
        raise Refusal(f"class {klass!r} requires --basis with its evidence reference")
    if args.seat is not None and args.seat not in seats:
        raise Refusal(f"unknown seat {args.seat!r}; configured: {', '.join(seats)}")
    if args.pass_ is not None and args.pass_ not in PASSES[:2]:
        raise Refusal("--pass must be generative or corrective")

    overrides = [flag for flag, value in (("--route", args.route), ("--model", args.model),
                                          ("--provider", args.provider), ("--effort", args.effort),
                                          ("--profile", args.profile)) if value is not None]
    if overrides and not (args.override_reason or "").strip():
        raise Refusal(f"{', '.join(overrides)} requires --override-reason")
    if args.override_reason is not None and not overrides:
        raise Refusal("--override-reason given without an override")
    if args.route is not None and args.model is not None:
        raise Refusal("choose --route or --model, not both")
    if args.provider is not None and args.model is None:
        raise Refusal("--provider is only valid with a native --model")

    route_name = model_alias = None
    if args.route is not None:
        if args.route not in routes:
            raise Refusal(f"unknown route {args.route!r}; configured: {', '.join(routes)}")
        route_name, rule = args.route, "explicit-route"
    elif args.model is not None:
        rule = "explicit-model"
    elif args.seat is not None and "route" in seats[args.seat]:
        route_name, rule = seats[args.seat]["route"], f"seat:{args.seat}"
    elif args.seat is not None:
        route_name, rule = seats[args.seat]["by_class"][klass], f"seat-class:{args.seat}/{klass}"
    elif class_source == "supplied":
        route_name, rule = classes[klass]["route"], f"class:{klass}"
    else:
        route_name, rule = config["legacy"]["route"], "legacy-unspecified"

    if args.model is not None and args.model in config.get("aliases", {}):
        if args.provider is not None:
            raise Refusal(f"--model {args.model} is an alias; do not add --provider")
        model_alias = args.model
        binding = config["aliases"][args.model]
    elif args.model is not None:
        if not NAME.fullmatch(args.model):
            raise Refusal("--model must be a configured alias or a native model id")
        if args.provider is None or args.effort is None:
            raise Refusal("a native --model needs --provider and --effort")
        binding = {"provider": args.provider, "model": args.model, "effort": args.effort}
    else:
        binding = routes[route_name]
    provider = binding["provider"]
    if provider not in config["providers"]:
        raise Refusal(f"provider {provider!r} is not configured")
    effort = args.effort if args.effort is not None else binding["effort"]
    if effort not in config["providers"][provider]["efforts"]:
        raise Refusal(f"effort {effort!r} is not a configured {provider} effort")
    if args.profile is not None and args.profile not in config["providers"][provider]["manual_profiles"]:
        raise Refusal(f"profile {args.profile!r} is not a {provider} profile")

    return {
        "schema": "direct-child-route/1",
        "seat": args.seat, "class": klass, "class_source": class_source,
        "basis": args.basis, "pass": args.pass_ or "unspecified",
        "rule": rule, "route": route_name, "model_alias": model_alias,
        "provider": provider, "model": binding["model"], "effort": effort,
        "overrides": overrides, "override_reason": args.override_reason,
    }


# -------------------------------------------------------------- rotation

def counter_path(config, provider):
    return Path(os.path.expanduser(config["rotation"]["state_dir"])) / f"{provider}.counter"


def _read_counter(text, path):
    text = text.strip()
    if not text:
        return 0
    if not text.isdigit():
        raise Refusal(f"malformed rotation counter {path}")
    return int(text)


def preview_profile(config, provider):
    """Next pool profile without locking, creating, or advancing anything."""
    pool = config["providers"][provider]["pool"]
    if len(pool) == 1:
        return pool[0], "fixed"
    path = counter_path(config, provider)
    try:
        count = _read_counter(path.read_text(encoding="utf-8"), path)
    except FileNotFoundError:
        count = 0
    return pool[count % len(pool)], f"rotation-preview:{count} (not reserved)"


def allocate_profile(config, provider):
    """Atomically take the next pool profile under an exclusive flock."""
    pool = config["providers"][provider]["pool"]
    if len(pool) == 1:
        return pool[0], "fixed"
    path = counter_path(config, provider)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        raise Refusal(f"cannot open rotation counter {path}: {error}") from error
    with os.fdopen(fd, "r+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        count = _read_counter(handle.read(), path)
        handle.seek(0)
        handle.truncate()
        handle.write(f"{count + 1}\n")
        handle.flush()
        os.fsync(handle.fileno())
    return pool[count % len(pool)], f"rotation:{count}"


# ----------------------------------------------------------------- launch

def codex_command(args, record, profile, route_json=None):
    command = [str(CODEX_LAUNCHER), "--profile", profile, "--cwd", args.cwd,
               "--prompt", args.prompt, "--runs-dir", args.runs_dir, "--id", args.id,
               "--model", record["model"], "--effort", record["effort"]]
    return command + (["--route-json", route_json] if route_json is not None else [])


def claude_command(record, wrapper):
    return [wrapper, "-p", "--model", record["model"], "--effort", record["effort"],
            "--strict-mcp-config", "--mcp-config", CLAUDE_EMPTY_MCP,
            "--settings", CLAUDE_SETTINGS, "--no-session-persistence",
            "--output-format", "stream-json", "--verbose"]


def run_claude(args, record, command):
    """Foreground Claude attempt; exit is native unless the result is absent or an error."""
    runs_dir = Path(args.runs_dir)
    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix=f"{args.id}.", dir=runs_dir.resolve()))
    except OSError as error:
        raise Refusal(f"cannot reserve attempt directory: {error}") from error
    paths = {name: attempt / name for name in
             ("prompt.md", "log.txt", "stderr.txt", "final.md", "state.txt", "route.json")}
    shutil.copyfile(args.prompt, paths["prompt.md"])
    paths["prompt.md"].chmod(0o400)
    for name in ("log.txt", "stderr.txt", "final.md"):
        paths[name].touch()
    paths["route.json"].write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    def git(*git_args):
        result = subprocess.run(["git", "-C", args.cwd, *git_args], capture_output=True,
                                text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"

    state = paths["state.txt"]
    with state.open("w", encoding="utf-8") as out:
        out.write(f"child_id={args.id}\nprovider=claude\nprofile={record['profile']}\n"
                  f"model={record['model']}\neffort={record['effort']}\n"
                  f"seat={record['seat']}\nclass={record['class']}\nrule={record['rule']}\n"
                  f"route_record={paths['route.json']}\ncwd={args.cwd}\n"
                  f"git_branch={git('branch', '--show-current')}\n"
                  f"git_head_at_start={git('rev-parse', 'HEAD')}\n"
                  f"native_command={shlex.join(command)}\n"
                  f"prompt={paths['prompt.md']}\nlog={paths['log.txt']}\n"
                  f"stderr={paths['stderr.txt']}\nfinal={paths['final.md']}\n"
                  f"start_utc={utc_now()}\n"
                  "expected_status=native terminal exit plus claude_exit entry\n")
    print(f"DIRECT_CHILD_ATTEMPT={attempt}\nDIRECT_CHILD_STATE={state}", flush=True)

    events, log_error, native_rc, launch_error = [], None, None, None
    process = None
    try:
        with paths["prompt.md"].open("rb") as stdin, paths["stderr.txt"].open("wb") as err, \
                paths["log.txt"].open("ab") as log:
            process = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE,
                                       stderr=err, cwd=args.cwd)
            for line in process.stdout:
                if log_error is None:
                    log_error = capture_line(log, line)
                capture_line(sys.stdout.buffer, line)
                event = parse_result(line)
                if event is not None:
                    events.append(event)
            native_rc = process.wait()
    except OSError as error:
        if native_rc is None:
            launch_error = str(error)
        else:
            log_error = str(error)
    finally:
        # Even a capture failure must not leave an already launched child unreaped.
        if process is not None:
            if native_rc is None:
                native_rc = process.wait()
            process.stdout.close()

    # Preserve the observed wait status before touching final custody. If state
    # storage also fails, terminal metadata remains available; it is not durable.
    state_error = append_state(state, f"claude_exit={'none' if native_rc is None else native_rc}\n")
    result_valid, semantic_error, result_error = result_semantics(events)
    text = "\n".join(event["result"] for event in events
                     if isinstance(event.get("result"), str) and event["result"].strip())
    final_status, final_error = capture_final(paths["final.md"], text, result_valid and native_rc == 0)
    custody_error = log_error or state_error or final_error or launch_error
    exit_code = claude_exit_code(native_rc, semantic_error, result_valid,
                                 final_status, custody_error)
    completion = (f"log_capture_exit={0 if log_error is None else 1}\n"
                  + (f"log_capture_error={log_error}\n" if log_error else "")
                  + (f"launch_error={launch_error}\n" if launch_error else "")
                  + (f"state_capture_error={state_error}\n" if state_error else "")
                  + f"result_event={'present' if events else 'missing'}\n"
                  f"result_event_count={len(events)}\n"
                  f"semantic_is_error={'unknown' if semantic_error is None else str(semantic_error).lower()}\n"
                  + (f"result_error={result_error}\n" if result_error else "")
                  + f"final_status={final_status}\n"
                  + (f"final_capture_error={final_error}\n" if final_error else "")
                  + f"custody_status={'incomplete' if custody_error else 'complete'}\n"
                  f"dispatcher_exit={exit_code}\nend_utc={utc_now()}\n")
    completion_error = append_state(state, completion)
    state_error = state_error or completion_error
    if completion_error:
        exit_code = claude_exit_code(native_rc, semantic_error, result_valid,
                                     final_status, completion_error)
    for name, error in (("launch_error", launch_error), ("log_capture_error", log_error),
                        ("final_capture_error", final_error), ("state_capture_error", state_error)):
        if error:
            report_claude(f"direct-child: incomplete custody: {name}={error}", sys.stderr)
    report_claude(f"DIRECT_CHILD_EXIT={exit_code} CLAUDE_EXIT={native_rc} "
                  f"SEMANTIC_IS_ERROR={'unknown' if semantic_error is None else str(semantic_error).lower()} "
                  f"FINAL_STATUS={final_status} "
                  f"CUSTODY_STATUS={'incomplete' if custody_error or state_error else 'complete'}")
    if final_status == "missing":
        report_claude(f"DIRECT_CHILD_FINAL_MISSING_OR_EMPTY={paths['final.md']}")
    return exit_code


def capture_line(handle, line):
    try:
        handle.write(line)
        handle.flush()
    except OSError as error:
        return str(error)
    return None


def parse_result(line):
    try:
        event = json.loads(line)
    except ValueError:
        return None
    return event if isinstance(event, dict) and event.get("type") == "result" else None


def result_semantics(events):
    """Only one affirmative native result can establish successful semantics."""
    if len(events) != 1:
        return False, None, "missing result" if not events else "multiple result events"
    event = events[0]
    if type(event.get("is_error")) is not bool:
        return False, None, "is_error must be a boolean"
    if event["is_error"]:
        return False, True, "result reports an error"
    if event.get("subtype") != "success":
        return False, None, "result subtype is not success"
    if not isinstance(event.get("result"), str) or not event["result"].strip():
        return False, None, "result text is missing or empty"
    return True, False, None


def append_state(state, text):
    try:
        with state.open("a", encoding="utf-8") as out:
            out.write(text)
    except (OSError, UnicodeError) as error:
        return str(error)
    return None


def report_claude(text, stream=None):
    try:
        print(text, file=stream or sys.stdout, flush=True)
    except (OSError, UnicodeError) as error:
        return str(error)
    return None


def capture_final(path, text, result_valid):
    if not text:
        return "missing", None
    try:
        path.write_text(text, encoding="utf-8")
        captured = path.read_text(encoding="utf-8")
        if captured != text:
            return "capture-error", "final readback differs from result text"
    except (OSError, UnicodeError) as error:
        return "capture-error", str(error)
    status = "present" if result_valid else "invalid-result"
    label = "FINAL" if result_valid else "RESULT_TEXT"
    error = (report_claude(f"DIRECT_CHILD_{label}_BEGIN={path}")
             or report_claude(captured) or report_claude(f"DIRECT_CHILD_{label}_END"))
    return ("capture-error", error) if error else (status, None)


def claude_exit_code(native_rc, semantic_error, result_valid, final_status, custody_error):
    if native_rc is None:
        return 1
    if native_rc != 0:
        return 128 - native_rc if native_rc < 0 else native_rc
    if semantic_error is True:
        return 3
    if not result_valid or final_status != "present":
        return 4
    return 1 if custody_error else 0


def check_paths(args):
    if not NAME.fullmatch(args.id):
        raise Refusal("id must use letters, digits, dot, underscore, or hyphen")
    for value in (args.cwd, args.prompt, args.runs_dir):
        if not value.startswith("/") or "\n" in value:
            raise Refusal("cwd, prompt, and runs-dir must be absolute paths without newlines")
    if not os.path.isdir(args.cwd):
        raise Refusal(f"cwd is not a directory: {args.cwd}")
    if not (os.path.isfile(args.prompt) and os.access(args.prompt, os.R_OK)
            and os.path.getsize(args.prompt) > 0):
        raise Refusal(f"prompt must be a readable nonempty file: {args.prompt}")
    args.cwd = os.path.realpath(args.cwd)


def main(argv):
    args = parse_args(argv)
    args.pass_ = getattr(args, "pass")
    try:
        config_path = Path(args.config) if args.config else DEFAULT_CONFIG
        config, digest = load_config(config_path)
        record = resolve(config, args)
        record.update(config=str(config_path.resolve()), config_sha256=digest)
        check_paths(args)
        provider = record["provider"]
        if provider == "claude":
            wrapper = args.profile or config["providers"]["claude"]["pool"][0]
            if not args.dry_run and shutil.which(wrapper) is None:
                raise Refusal(f"Claude wrapper {wrapper!r} is not on PATH")
        if args.dry_run:
            if args.profile is not None:
                profile, source = args.profile, "explicit"
            else:
                profile, source = preview_profile(config, provider)
            record.update(profile=profile, profile_source=source)
            command = (claude_command(record, profile) if provider == "claude"
                       else codex_command(args, record, profile))
            print("DRY RUN: " + json.dumps(record, sort_keys=True))
            print("DRY RUN: would run: " + shlex.join(command))
            print("DRY RUN: no files written, rotation not advanced, no model launched")
            return 0
        if args.profile is not None:
            profile, source = args.profile, "explicit"
        else:
            profile, source = allocate_profile(config, provider)
        record.update(profile=profile, profile_source=source)
    except Refusal as error:
        print(f"direct-child: {error}", file=sys.stderr)
        return 2
    route_json = json.dumps(record, sort_keys=True)
    print(f"DIRECT_CHILD_ROUTE={route_json}", flush=True)
    if provider == "codex":
        command = codex_command(args, record, profile, route_json)
        os.execv(command[0], command)
    try:
        return run_claude(args, record, claude_command(record, profile))
    except Refusal as error:
        print(f"direct-child: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
