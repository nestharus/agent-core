#!/usr/bin/env python3
"""Contextual direct dispatcher: resolve a route from seat, class and kind, then run
one Codex or Claude child in the foreground, through the Linux native ACP v2
caller for exactly mapped bindings by default, otherwise directly. See README.md."""

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
import time
import tomllib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import codex_auth  # noqa: E402  (sibling module; also when run through runpy)

DEFAULT_CONFIG = HERE / "routes.toml"
CODEX_LAUNCHER = HERE.parent / "direct-codex-child" / "launch.sh"
CLAUDE_EMPTY_MCP = '{"mcpServers":{}}'
CLAUDE_SETTINGS = '{"autoMemoryEnabled":false}'
# Known names to request denial of. Help, init metadata and emitted calls are
# separate evidence; none certifies that the session executed without mediation.
CLAUDE_WITHHELD_TOOLS = ("Agent", "Task", "Workflow")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
PROFILE = re.compile(r"\.?[A-Za-z0-9][A-Za-z0-9._-]*")
PROVIDERS = ("codex", "claude")
PASSES = ("generative", "corrective", "unspecified")
TRANSPORTS = ("direct", "native")
# Dispatcher refusals after the attempt record exists and before any task:
EXIT_NATIVE_CREDENTIAL = 70  # no fresh access token; renewal not needed, failed or unknown
EXIT_LEASE_TIMEOUT = 75      # profile lease busy for the whole bound
NATIVE_INTEGERS = ("deadline_s", "site_grace_s", "site_collection_s", "site_margin_s",
                   "slack_s", "renew_timeout_s")
# The pinned caller's own ceilings: it refuses a deadline above 7200 s and a
# child allowance outside 1..4. A site may admit less; the front door decides.
CALLER_MAX_DEADLINE_S = 7200
CALLER_CHILD_LIMIT = 4
CHILD_LIMITS = ("max_starts", "max_concurrent")


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
    for flag in ("--seat", "--class", "--basis", "--kind", "--pass", "--route", "--model",
                 "--provider", "--effort", "--profile", "--override-reason", "--config",
                 "--transport"):
        parser.add_argument(flag, action=Once)
    parser.add_argument("--native-deadline", action=Once, type=int, metavar="SECONDS",
                        help="native front-door deadline; refused when the launch resolves direct")
    parser.add_argument("--native-child-route", action="append", metavar="NAME",
                        help="explicit opt-in to a declared site child route (repeatable); "
                             "refused when the launch resolves direct")
    parser.add_argument("--native-child-max-starts", action=Once, type=int, metavar="N")
    parser.add_argument("--native-child-max-concurrent", action=Once, type=int, metavar="N")
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
    kinds = config.get("kinds", {})
    if not isinstance(kinds, dict):
        raise Refusal("config: [kinds] must be a table")
    for name, entry in kinds.items():
        if not isinstance(entry, dict) or not NAME.fullmatch(name):
            raise Refusal(f"config: kinds.{name} must be a named table")
        if set(entry) - {"route", "seats"} or ("route" in entry) != ("seats" in entry):
            raise Refusal(f"config: kinds.{name} takes route and seats together, or neither")
        if "route" in entry:
            if entry["route"] not in routes:
                raise Refusal(f"config: kinds.{name}.route is not a configured route")
            if (not isinstance(entry["seats"], list)
                    or not all(seat in config["seats"] for seat in entry["seats"])
                    or len(set(entry["seats"])) != len(entry["seats"])):
                raise Refusal(f"config: kinds.{name}.seats must list distinct configured seats")
    if _table(config, "legacy").get("route") not in routes:
        raise Refusal("config: legacy.route is not a configured route")
    validate_transport(config)


def validate_transport(config):
    """[lease], [transport] and [native] are optional: without them the lease
    waits 120 s, transport is direct and nothing can run natively."""
    wait = config.get("lease", {}).get("wait_s", 120)
    if type(wait) not in (int, float) or not 0 < wait <= 3600:
        raise Refusal("config: lease.wait_s must be a number of seconds in (0, 3600]")
    default = config.get("transport", {}).get("default", "direct")
    if default not in TRANSPORTS:
        raise Refusal("config: transport.default must be direct or native")
    native = config.get("native")
    if native is None:
        if default == "native":
            raise Refusal("config: transport.default native needs a [native] table")
        return
    if not isinstance(native, dict):
        raise Refusal("config: [native] must be a table")
    caller = _string(native.get("caller"), "native.caller")
    if not caller.startswith("/") or "\n" in caller:
        raise Refusal("config: native.caller must be an absolute path")
    for key in NATIVE_INTEGERS:
        if type(native.get(key)) is not int or native[key] < (1 if key in ("deadline_s", "renew_timeout_s") else 0):
            raise Refusal(f"config: native.{key} must be a nonnegative integer (positive for deadlines)")
    ceiling = native.setdefault("max_deadline_s", CALLER_MAX_DEADLINE_S)
    if type(ceiling) is not int or not 1 <= ceiling <= CALLER_MAX_DEADLINE_S:
        raise Refusal(f"config: native.max_deadline_s must be 1..{CALLER_MAX_DEADLINE_S} "
                      "(the pinned caller's ceiling)")
    if native["deadline_s"] > ceiling:
        raise Refusal("config: native.deadline_s exceeds native.max_deadline_s")
    children = native.setdefault("children", {"routes": []})
    if (not isinstance(children, dict) or set(children) - {"routes", *CHILD_LIMITS}
            or not isinstance(children.get("routes"), list)
            or not all(isinstance(name, str) and NAME.fullmatch(name) for name in children["routes"])
            or len(set(children["routes"])) != len(children["routes"])):
        raise Refusal("config: [native.children] takes routes (distinct site child route names) "
                      "and optional max_starts, max_concurrent")
    for key in CHILD_LIMITS:
        value = children.setdefault(key, CALLER_CHILD_LIMIT)
        if type(value) is not int or not 1 <= value <= CALLER_CHILD_LIMIT:
            raise Refusal(f"config: native.children.{key} must be 1..{CALLER_CHILD_LIMIT}")
    bindings = native.get("bindings", [])
    seen = set()
    for index, binding in enumerate(bindings if isinstance(bindings, list) else [None]):
        where = f"native.bindings[{index}]"
        # A Claude site route fixes its store, so the store is part of the
        # binding; Codex credentials come from rotation, so it names none.
        claude = isinstance(binding, dict) and binding.get("provider") == "claude"
        fields = {"provider", "model", "effort", "site_route"} | ({"profile"} if claude else set())
        if not isinstance(binding, dict) or set(binding) - {"children"} != fields:
            raise Refusal(f"config: {where} needs exactly provider, model, effort and site_route, "
                          "plus profile for a Claude binding, and optional children")
        offers = binding.setdefault("children", [])
        if (not isinstance(offers, list) or len(set(map(str, offers))) != len(offers)
                or not all(isinstance(name, str) and name in children["routes"] for name in offers)):
            raise Refusal(f"config: {where}.children must list distinct [native.children] routes")
        _binding(binding, where, config["providers"])
        if not NAME.fullmatch(_string(binding["site_route"], f"{where}.site_route")):
            raise Refusal(f"config: {where}.site_route must be a site route name")
        if claude:
            store = config["providers"]["claude"]
            if binding["profile"] not in store["manual_profiles"]:
                raise Refusal(f"config: {where}.profile is not a configured Claude profile")
            if len(store["pool"]) != 1:
                raise Refusal(f"config: {where}: a native Claude binding needs a one-store Claude "
                              "pool, so the store is known before transport is chosen")
        key = (binding["provider"], binding["model"], binding["effort"], binding.get("profile"))
        if key in seen:
            raise Refusal(f"config: {where} repeats a binding")
        seen.add(key)


# ------------------------------------------------------------ resolution

def resolve(config, args):
    """Explicit route/model, else routed kind, else seat, else class, else legacy
    default. A routed kind refuses any result other than its own route's binding."""
    classes, seats, routes = config["classes"], config["seats"], config["routes"]
    kinds = config.get("kinds", {})
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
    if args.kind is not None and args.kind not in kinds:
        raise Refusal(f"unknown kind {args.kind!r}; configured: {', '.join(kinds) or 'none'}")
    kind_route = kinds.get(args.kind, {}).get("route")
    if kind_route is not None and args.seat is not None and args.seat not in kinds[args.kind]["seats"]:
        raise Refusal(f"--kind {args.kind} does not route seat {args.seat!r}; it routes "
                      f"{', '.join(kinds[args.kind]['seats'])} and launches with no seat")

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
    elif kind_route is not None:
        route_name = kind_route
        rule = f"seat-kind:{args.seat}/{args.kind}" if args.seat else f"kind:{args.kind}"
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
    if kind_route is not None:
        want = routes[kind_route]
        if (provider, binding["model"], effort) != (want["provider"], want["model"], want["effort"]):
            raise Refusal(f"--kind {args.kind} requires {want['provider']} / {want['model']} / "
                          f"{want['effort']} (route {kind_route}); {', '.join(overrides)} resolves to "
                          f"{provider} / {binding['model']} / {effort}. Change routes.toml, "
                          "not the launch")

    return {
        "schema": "direct-child-route/1",
        "seat": args.seat, "class": klass, "class_source": class_source,
        "basis": args.basis, "pass": args.pass_ or "unspecified",
        "kind": args.kind or "unstated",
        "kind_source": "supplied" if args.kind is not None else "not supplied",
        "rule": rule, "route": route_name, "model_alias": model_alias,
        "provider": provider, "model": binding["model"], "effort": effort,
        "overrides": overrides, "override_reason": args.override_reason,
    }


def child_request(args):
    """The explicit child opt-in as given, checked for form only; or None."""
    routes = args.native_child_route or []
    limits = {key: getattr(args, f"native_child_{key}") for key in CHILD_LIMITS}
    if not routes:
        if any(value is not None for value in limits.values()):
            raise Refusal("--native-child-max-starts/--native-child-max-concurrent need "
                          "--native-child-route")
        return None
    if len(set(routes)) != len(routes) or not all(NAME.fullmatch(name) for name in routes):
        raise Refusal("--native-child-route must name distinct site child routes")
    return routes, limits


def resolve_transport(config, args, record):
    """Pick direct or native before anything starts. The route's provider,
    model, effort and (for Claude) store are never changed; with default
    native an unmapped binding runs direct by rule, and an explicit native
    request for one is refused. Never a post-launch fallback. Native-only
    requests (a deadline, a child opt-in) are checked here, before profile
    allocation, lease, credential preparation or any write: an invalid value
    is refused on every transport, and a valid one on a launch that resolves
    direct is refused, not dropped."""
    if args.transport is not None and args.transport not in TRANSPORTS:
        raise Refusal("--transport must be direct or native")
    native = config.get("native", {})
    ceiling = native.get("max_deadline_s", CALLER_MAX_DEADLINE_S)
    if args.native_deadline is not None and not 1 <= args.native_deadline <= ceiling:
        raise Refusal(f"--native-deadline must be a positive number of seconds, at most {ceiling} "
                      "(declared bound; the site may admit less and refuses)")
    asked = child_request(args)
    source = "explicit" if args.transport is not None else "default"
    wanted = args.transport or config.get("transport", {}).get("default", "direct")
    # The Claude store is the explicit profile or the one-store pool (a native
    # Claude binding requires one store); Codex bindings name no store.
    store = (args.profile or config["providers"]["claude"]["pool"][0]
             if record["provider"] == "claude" else None)
    key = (record["provider"], record["model"], record["effort"], store)
    declared = next((b for b in native.get("bindings", [])
                     if (b["provider"], b["model"], b["effort"], b.get("profile")) == key), None)
    site_route = declared["site_route"] if declared else None
    binding = " / ".join(part for part in key if part is not None)
    fields = {"transport_source": source, "site_route": None, "native_caller": None,
              "native_deadline_s": None, "native_children": None}
    if wanted == "direct" or site_route is None:
        if site_route is None and source == "explicit" and wanted == "native":
            raise Refusal(f"--transport native: no native site route is declared for "
                          f"{binding}; launch it direct")
        rule = f"{source}-direct" if wanted == "direct" else "default-native-unmapped-direct"
        for flag, given in (("--native-deadline", args.native_deadline is not None),
                            ("--native-child-route", asked is not None)):
            if given:
                raise Refusal(f"{flag} applies only to a native launch; {binding} runs "
                              f"direct here ({rule}), and direct launches have no deadline or "
                              "native children. Omit it, or launch a natively mapped binding")
        return dict(fields, transport="direct", transport_rule=rule)
    deadline = args.native_deadline if args.native_deadline is not None else native["deadline_s"]
    children = None
    if asked is not None:
        routes, limits = asked
        unoffered = [name for name in routes if name not in declared["children"]]
        if unoffered:
            raise Refusal(f"--native-child-route {', '.join(unoffered)}: not declared as offered "
                          f"by site route {site_route} ({', '.join(declared['children']) or 'none'} "
                          "declared); nothing was started")
        for name, value in limits.items():
            bound = native["children"][name]
            if value is not None and not 1 <= value <= bound:
                raise Refusal(f"--native-child-{name.replace('_', '-')} must be 1..{bound} "
                              "(declared site limit; the site may admit less and refuses)")
        children = {"routes": routes, **limits,
                    "declared_limits": {name: native["children"][name] for name in CHILD_LIMITS},
                    "grant": ("reuses the parent's one access-only Codex snapshot"
                              if store is None else
                              "one separate access-only Codex child grant from the rotated pool; "
                              "never the Claude store's login"),
                    "offer_source": "routes.toml declaration; the site's child_routes, offers "
                                    "and child_limits decide and are not read here"}
    return dict(fields, transport="native", transport_rule=f"{source}-native",
                site_route=site_route, native_caller=native["caller"],
                native_deadline_s=deadline, native_children=children,
                native_credential="codex-access-snapshot" if store is None else "none",
                site_binding_source="routes.toml declaration; the root-owned site config "
                                    "fixes the actual model, effort and any Claude store and "
                                    "is not read here")


def credential_need(config, deadline):
    """(seconds the token must cover at our check, the caller's margin)."""
    native = config["native"]
    site = 2 * native["site_grace_s"] + native["site_collection_s"] + native["site_margin_s"]
    return deadline + site + native["slack_s"], site + native["slack_s"] // 2


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

def lease_wait(config):
    return config.get("lease", {}).get("wait_s", 120)


def codex_command(args, record, profile, config, route_json=None):
    command = [str(CODEX_LAUNCHER), "--profile", profile, "--cwd", args.cwd,
               "--prompt", args.prompt, "--runs-dir", args.runs_dir, "--id", args.id,
               "--model", record["model"], "--effort", record["effort"],
               "--lease-wait", str(lease_wait(config))]
    return command + (["--route-json", route_json] if route_json is not None else [])


def native_command(record, cwd, prompt, out, credential_dir=None, margin=None):
    """The pinned caller's documented interface; the request carries site
    route names only. The one access-only snapshot is the Codex parent's own
    (its children reuse it), or an opted-in Claude parent's separate child
    grant; a Claude parent's own route takes no credential. The caller's
    freshness margin keeps half our slack, so seconds between our check and
    its own do not refuse the launch."""
    command = [record["native_caller"], "--route", record["site_route"],
               "--prompt-file", prompt, "--cwd", cwd, "--out", out, "--trusted-task",
               "--deadline", str(record["native_deadline_s"])]
    children = record.get("native_children")
    for name in (children or {}).get("routes", ()):
        command += ["--child-route", name]
    for name in CHILD_LIMITS:
        if (children or {}).get(name) is not None:
            command += [f"--child-{name.replace('_', '-')}", str(children[name])]
    if credential_dir is None:
        return command
    flag = ("--credential-codex-profile" if record["provider"] == "codex"
            else "--child-credential-codex-profile")
    return command + [flag, credential_dir, "--credential-margin", str(margin)]


def claude_command(record, wrapper):
    return [wrapper, "-p", "--model", record["model"], "--effort", record["effort"],
            "--strict-mcp-config", "--mcp-config", CLAUDE_EMPTY_MCP,
            "--settings", CLAUDE_SETTINGS, "--no-session-persistence",
            "--disallowedTools", ",".join(CLAUDE_WITHHELD_TOOLS),
            "--output-format", "stream-json", "--verbose"]


def select_claude_restriction(command, attempt, cwd):
    """Metadata only, before the sole task. Unknown support omits the restriction."""
    metadata = attempt / "restriction-metadata"
    env = os.environ.copy()
    help_command = [command[0], "--disallowedTools", ",".join(CLAUDE_WITHHELD_TOOLS), "--help"]
    supported, rc = False, "unavailable"
    try:
        metadata.mkdir(mode=0o700)
        for variable, directory in (("HOME", "home"), ("XDG_CONFIG_HOME", "config"),
                                    ("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache"),
                                    ("XDG_STATE_HOME", "state"), ("CODEX_HOME", "codex"),
                                    ("CLAUDE_CONFIG_DIR", "claude"), ("TMPDIR", "tmp")):
            path = metadata / directory
            path.mkdir(mode=0o700)
            env[variable] = str(path)
        result = subprocess.run(help_command, stdin=subprocess.DEVNULL, capture_output=True,
                                cwd=cwd, env=env, timeout=10, check=False)
        rc = str(result.returncode)
        (metadata / "stdout.txt").write_bytes(result.stdout)
        (metadata / "stderr.txt").write_bytes(result.stderr)
        supported = result.returncode == 0 and re.search(
            rb"(?m)^\s*--disallowedTools(?:\s|,)", result.stdout) is not None
        note = ("denial arguments accepted by help and flag documented; task support unproven"
                if supported else "denial help rejected or flag undocumented; restriction omitted")
    except (OSError, subprocess.TimeoutExpired) as error:
        note = f"denial help unavailable ({type(error).__name__}); restriction omitted"
    if not supported:
        command = command.copy()
        index = command.index("--disallowedTools")
        del command[index:index + 2]
    evidence = (f"restriction_help_command={shlex.join(help_command)}\n"
                f"restriction_help_exit={rc}\nrestriction_metadata={metadata}\n"
                f"restriction_selection={'requested' if supported else 'omitted'}\n"
                f"restriction_selection_note={note}\n")
    return command, evidence


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
    command, restriction_evidence = select_claude_restriction(command, attempt, args.cwd)

    def git(*git_args):
        result = subprocess.run(["git", "-C", args.cwd, *git_args], capture_output=True,
                                text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"

    state = paths["state.txt"]
    with state.open("w", encoding="utf-8") as out:
        out.write(f"child_id={args.id}\nprovider=claude\nprofile={record['profile']}\n"
                  f"model={record['model']}\neffort={record['effort']}\n"
                  f"seat={record['seat']}\nclass={record['class']}\nkind={record['kind']}\n"
                  f"rule={record['rule']}\n"
                  f"route_record={paths['route.json']}\ncwd={args.cwd}\n"
                  f"git_branch={git('branch', '--show-current')}\n"
                  f"git_head_at_start={git('rev-parse', 'HEAD')}\n"
                  f"native_command={shlex.join(command)}\n"
                  f"prompt={paths['prompt.md']}\nlog={paths['log.txt']}\n"
                  f"stderr={paths['stderr.txt']}\nfinal={paths['final.md']}\n"
                  f"requested_disallowed_tools={','.join(CLAUDE_WITHHELD_TOOLS) if '--disallowedTools' in command else ''}\n"
                  f"{restriction_evidence}"
                  f"start_utc={utc_now()}\n"
                  "expected_status=native terminal exit plus claude_exit entry\n")
    print(f"DIRECT_CHILD_ATTEMPT={attempt}\nDIRECT_CHILD_STATE={state}", flush=True)

    events, log_error, native_rc, launch_error = [], None, None, None
    delegation = {"init_tools": [], "uses": 0}
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
                event = parse_event(line)
                if event is not None:
                    note_delegation(event, delegation)
                    if event.get("type") == "result":
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
                  + delegation_state(delegation)
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
            report(f"direct-child: incomplete custody: {name}={error}", sys.stderr)
    report(f"DIRECT_CHILD_EXIT={exit_code} CLAUDE_EXIT={native_rc} "
                  f"SEMANTIC_IS_ERROR={'unknown' if semantic_error is None else str(semantic_error).lower()} "
                  f"FINAL_STATUS={final_status} "
                  f"CUSTODY_STATUS={'incomplete' if custody_error or state_error else 'complete'}")
    if final_status == "missing":
        report(f"DIRECT_CHILD_FINAL_MISSING_OR_EMPTY={paths['final.md']}")
    return exit_code


def capture_line(handle, line):
    try:
        handle.write(line)
        handle.flush()
    except OSError as error:
        return str(error)
    return None


def parse_event(line):
    try:
        event = json.loads(line)
    except ValueError:
        return None
    return event if isinstance(event, dict) else None


def note_delegation(event, delegation):
    """Retain init metadata and emitted known-name tool-use blocks, not child counts."""
    if event.get("type") == "system" and event.get("subtype") == "init":
        delegation["init_tools"].append(event.get("tools"))
    message = event.get("message") if event.get("type") == "assistant" else None
    content = message.get("content") if isinstance(message, dict) else None
    for block in content if isinstance(content, list) else ():
        if (isinstance(block, dict) and block.get("type") == "tool_use"
                and block.get("name") in CLAUDE_WITHHELD_TOOLS):
            delegation["uses"] += 1


def delegation_state(delegation):
    """Describe metadata narrowly; never certify capability absence or gate a task."""
    lists = delegation["init_tools"]
    valid = bool(lists) and all(isinstance(tools, list) and tools
                               and all(isinstance(name, str) and name for name in tools)
                               for tools in lists)
    offered = sorted({name for tools in lists if isinstance(tools, list)
                      for name in tools if isinstance(name, str)} & set(CLAUDE_WITHHELD_TOOLS))
    if offered:
        init_status, note = "offered", "init offered " + ",".join(offered)
    elif not valid:
        init_status, note = "unknown", "init tool metadata missing, empty or malformed"
    elif any(set(tools) != set(lists[0]) for tools in lists[1:]):
        init_status, note = "unknown", "conflicting init tool lists"
    elif delegation["uses"]:
        init_status, note = "contradicted", "known-name tool uses emitted despite init omission"
    else:
        init_status, note = "not-listed", "known names absent from recorded init lists; capability absence unproven"
    return ("delegation_capability=not-established\n"
            f"delegation_capability_note={note}\n"
            f"delegation_init_status={init_status}\n"
            f"delegation_init_tools={json.dumps(lists, separators=(',', ':'))}\n"
            f"delegation_tool_uses={delegation['uses']}\n"
            "delegation_scope=known Agent,Task,Workflow names; other coordination tools, shell-launched "
            "processes, hooks, plugins and skills not covered\n")


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


def report(text, stream=None):
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
    error = (report(f"DIRECT_CHILD_{label}_BEGIN={path}")
             or report(captured) or report(f"DIRECT_CHILD_{label}_END"))
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


# ---------------------------------------------------------------- native

NATIVE_RECORD_NOTE = {
    "codex": "qualified native record: answer text, turn and owner events and Bash argv; "
             "no Bash output bodies or reasoning; not a complete log",
    "claude": "qualified native record: answer text, turn and owner events and Bash argv; "
              "no Bash output bodies, Read/Write/Edit bodies or reasoning; not a complete log",
}
NATIVE_TOOLS_NOTE = {
    "codex": "native constructs a Bash-only tool configuration; "
             "a trusted shell can still start processes, CLIs and this dispatcher",
    "claude": "native trusted-task offers Bash plus built-in Read, Write and Edit, whose effects "
              "are not Bash records; a trusted shell can still start processes, CLIs and this "
              "dispatcher; Claude Code managed settings still apply",
}
NATIVE_CHILDREN_NOTE = ("counts are the caller's tally of owner exports in native/children.json: "
                        "export can lag the parent's local result while Bash drains, zero exports "
                        "is not zero local results, and none is parent consumption, answer "
                        "correctness, the model, the account or the issuer; Bash counts combine "
                        "parent and child")
# The front door returns the native entry's status when observed, else its own
# (Runner native_root.rs and the package README). Statuses describe transport
# and retirement, not processing or task correctness; the caller's class is
# separate.
FRONT_DOOR_EXITS = {
    0: "entry ended: every harness end observed, nothing owed",
    64: "entry refused the request before any effect",
    66: "owner refused the request or its store",
    69: "owner could not be started",
    70: "owner started; its end is unknown to the entry",
    73: "entry setup construction failed",
    74: "entry lost output: lines not all delivered",
    82: "owner cancelled", 83: "owner ended with work owed",
    84: "owner incomplete or owned-unattached", 85: "owner authority lost or store failed",
    86: "owner root absent",
    87: "owner closed: the caller's close after the linked turn end was followed through and "
        "the host ended by a kill; not evidence that anything was processed",
    90: "front door refused admission", 91: "front door setup failure",
    92: "front door requested a namespace kill and observed collection",
    93: "front door stop or collection unknown", 94: "front door cleanup or residue failure",
}


def front_door_meaning(code):
    if not isinstance(code, int) or isinstance(code, bool):
        return "not observed"
    return FRONT_DOOR_EXITS.get(code, "undocumented status")


def run_native(args, config, record, profile):
    """Own catchable cancellation and snapshot cleanup for the whole attempt."""
    cleanup = {}
    with codex_auth.CatchSignals() as interrupts:
        try:
            code = _run_native(args, config, record, profile, interrupts, cleanup)
        finally:
            if "credential_dir" in cleanup and not cleanup.get("snapshot_cleanup_done"):
                error = codex_auth.remove_access_snapshot(cleanup["credential_dir"])
                cleanup["error"] = error
                if "state" in cleanup:
                    append_state(cleanup["state"],
                                 f"credential_snapshot_removed={'yes' if error is None else 'no:' + error}\n")
        if interrupts.received is not None:
            code = 128 + interrupts.received
            if "state" in cleanup:
                append_state(cleanup["state"], f"native_signal={interrupts.received}\n"
                             f"dispatcher_exit={code}\n")
            report(f"DIRECT_CHILD_EXIT={code} SIGNAL={interrupts.received}")
        elif cleanup.get("error") and code == 0:
            code = 6
        return code


def _run_native(args, config, record, profile, interrupts, cleanup):
    """One native attempt, then the installed caller in the foreground. Codex:
    profile lease; freshness, with at most one official renewal; an
    access-only snapshot; lease released. Claude: none of these; the site
    route fixes the store and Claude Code uses its own login there. The
    caller's exit is the attempt's. Nothing is replayed or sent direct."""
    os.umask(0o077)
    # One access-only Codex grant at most: the Sol parent's own, which its
    # children reuse, or an opted-in Claude parent's separate child grant.
    # A Claude parent without children prepares nothing.
    child_grant = record["provider"] == "claude" and record.get("native_children") is not None
    codex = record["provider"] == "codex" or child_grant
    grant_profile = record.get("child_profile") if child_grant else profile
    profile_home = Path(os.path.expanduser("~")) / grant_profile if codex else None
    runs_dir = Path(args.runs_dir)
    try:
        if codex and not profile_home.is_dir():
            raise Refusal(f"missing profile: {profile_home}")
        runs_dir.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix=f"{args.id}.", dir=runs_dir.resolve()))
        paths = {name: attempt / name for name in
                 ("prompt.md", "final.md", "state.txt", "route.json", "renewal.json")}
        shutil.copyfile(args.prompt, paths["prompt.md"])
        paths["prompt.md"].chmod(0o400)
        paths["final.md"].touch()
        paths["route.json"].write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, Refusal) as error:
        print(f"direct-child: {error}", file=sys.stderr)
        return 2
    out = attempt / "native"
    children = record.get("native_children")
    preparation = ""
    if record["provider"] == "claude":
        preparation = ("credential=none\nprofile_lease=none\n"
                       "credential_note=the site route fixes the store; Claude Code uses its own "
                       "login there; this dispatcher reads, renews and stages nothing for it\n")
    if children is not None:
        preparation += (f"native_child_routes={','.join(children['routes'])}\n"
                        + "".join(f"native_child_{name}={children[name]}\n" for name in CHILD_LIMITS
                                  if children[name] is not None)
                        + f"native_child_grant={children['grant']}\n")
    if codex:
        credential_dir = attempt / ("native-child-credential" if child_grant else "native-credential")
        cleanup["credential_dir"] = credential_dir
        need, margin = credential_need(config, record["native_deadline_s"])
        command = native_command(record, args.cwd, str(paths["prompt.md"]), str(out),
                                 str(credential_dir), margin)
        preparation += ((f"child_grant_profile={grant_profile}\n"
                         f"child_grant_profile_source={record['child_profile_source']}\n"
                         "lease_scope=child grant profile\n" if child_grant else "")
                        + f"renewal_record={paths['renewal.json']}\n"
                        f"lease={profile_home / codex_auth.LEASE_NAME}\nlease_wait_s={lease_wait(config)}\n"
                        f"credential_need_s={need}\n")
    else:
        command = native_command(record, args.cwd, str(paths["prompt.md"]), str(out))
    state = paths["state.txt"]
    cleanup["state"] = state

    def git(*git_args):
        result = subprocess.run(["git", "-C", args.cwd, *git_args], capture_output=True,
                                text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"

    state.write_text(
        f"child_id={args.id}\ntransport=native\nprovider={record['provider']}\nprofile={profile}\n"
        f"model={record['model']}\neffort={record['effort']}\nsite_route={record['site_route']}\n"
        f"seat={record['seat']}\nclass={record['class']}\nkind={record['kind']}\n"
        f"rule={record['rule']}\ntransport_rule={record['transport_rule']}\n"
        f"route_record={paths['route.json']}\ncwd={args.cwd}\n"
        f"git_branch={git('branch', '--show-current')}\n"
        f"git_head_at_start={git('rev-parse', 'HEAD')}\n"
        f"prompt={paths['prompt.md']}\nfinal={paths['final.md']}\nnative_out={out}\n"
        f"{preparation}start_utc={utc_now()}\n"
        "expected_status=native terminal exit plus native_caller_exit entry\n", encoding="utf-8")
    print(f"DIRECT_CHILD_ATTEMPT={attempt}\nDIRECT_CHILD_STATE={state}", flush=True)

    summary = ""
    if codex:
        renewal, snapshot = None, None
        try:
            with codex_auth.ProfileLease(profile_home, lease_wait(config), interrupts=interrupts) as lease:
                append_state(state, f"lease_status=acquired\nlease_waited_s={lease.waited_s}\n")
                renewal, snapshot = codex_auth.ensure_fresh(
                    profile_home, need, config["native"]["renew_timeout_s"], cwd=attempt,
                    interrupts=interrupts)
                paths["renewal.json"].write_text(json.dumps(renewal, sort_keys=True) + "\n",
                                                 encoding="utf-8")
                if snapshot is not None and interrupts.received is None:
                    codex_auth.write_access_snapshot(credential_dir, snapshot)
        except codex_auth._Interrupted:
            return native_refused(state, 128 + interrupts.received, "native_task=not-started\n")
        except codex_auth.LeaseTimeout as error:
            return native_refused(state, EXIT_LEASE_TIMEOUT, f"lease_status=timeout\nlease_note={error}\n")
        except OSError as error:
            code = EXIT_LEASE_TIMEOUT if renewal is None else EXIT_NATIVE_CREDENTIAL
            snapshot_error = codex_auth.remove_access_snapshot(credential_dir)
            cleanup["snapshot_cleanup_done"] = True
            return native_refused(state, code, f"native_prelaunch_error={type(error).__name__}\n"
                                  f"credential_snapshot_removed={snapshot_error or 'yes'}\n")
        summary = (f"lease_released_utc={utc_now()}\nrenewal={renewal['renewal']}\n"
                   f"issuer_contact={renewal['issuer_contact']}\n"
                   f"profile_written={renewal['profile_written']}\n"
                   + "".join(f"credential_{key}={renewal[key]}\n"
                             for key in ("remaining_s_before", "remaining_s_after") if key in renewal))
        if snapshot is None:
            return native_refused(state, EXIT_NATIVE_CREDENTIAL, summary + "native_task=not-started\n")
    if interrupts.received is not None:
        return native_refused(state, 128 + interrupts.received, summary + "native_task=not-started\n")
    append_state(state, summary + f"native_command={shlex.join(command)}\n"
                 f"native_start_utc={utc_now()}\n")

    caller_rc, launch_error = run_foreground(command, attempt, interrupts)
    state_error = append_state(state, f"native_caller_exit={'none' if caller_rc is None else caller_rc}\n")
    snapshot_error = None
    if codex:
        snapshot_error = codex_auth.remove_access_snapshot(credential_dir)
        cleanup["snapshot_cleanup_done"] = True
    result, result_status = read_native_result(out / "result.json")
    text, text_error = "", None
    try:
        if (out / "final.md").exists():
            text = (out / "final.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        text_error = type(error).__name__
    answered = caller_rc == 0 and result.get("class") == "answered"
    final_status, final_error = capture_final(paths["final.md"], text, answered)
    custody_error = launch_error or state_error or final_error or text_error or snapshot_error
    exit_code = native_exit(caller_rc, final_status, custody_error)
    answer = result.get("answer") if isinstance(result.get("answer"), dict) else {}
    counts = result.get("counts") if isinstance(result.get("counts"), dict) else {}
    front_door = result.get("front_door_exit", "unknown")
    completion = ((f"native_launch_error={launch_error}\n" if launch_error else "")
                  + f"native_result={result_status}\n"
                  f"native_class={result.get('class', 'unknown')}\n"
                  f"front_door_exit={front_door}\n"
                  f"front_door_exit_meaning={front_door_meaning(front_door)}\n"
                  "native_status_note=native_caller_exit and native_class are the caller's; "
                  "front_door_exit is the entry or front door's; answered is not correctness\n"
                  f"native_answer={'present' if answer.get('present') is True else 'absent-or-unknown'}\n"
                  f"native_bash_accepted={counts.get('bash_accepted', 'unknown')}\n"
                  f"native_bash_ended={counts.get('bash_ended', 'unknown')}\n"
                  f"native_processing_completion={result.get('processing_completion', 'unknown')}\n"
                  f"native_record={NATIVE_RECORD_NOTE[record['provider']]}\n"
                  "native_retry=do-not-replay; no direct fallback\n"
                  + (f"credential_snapshot_removed={'yes' if snapshot_error is None else 'no:' + snapshot_error}\n"
                     if codex else "")
                  + (f"native_child_results={counts.get('child_results', 'unknown')}\n"
                     f"native_child_accepted={counts.get('child_accepted', 'unknown')}\n"
                     f"native_child_refused={counts.get('child_refused', 'unknown')}\n"
                     f"native_children_note={NATIVE_CHILDREN_NOTE}\n" if children is not None else "")
                  + "delegation_capability=not-established\n"
                  f"delegation_capability_note={NATIVE_TOOLS_NOTE[record['provider']]}\n"
                  + (f"final_read_error={text_error}\n" if text_error else "")
                  + f"final_status={final_status}\n"
                  + (f"final_capture_error={final_error}\n" if final_error else "")
                  + f"custody_status={'incomplete' if custody_error else 'complete'}\n"
                  f"dispatcher_exit={exit_code}\nend_utc={utc_now()}\n")
    completion_error = append_state(state, completion)
    if completion_error:
        exit_code = native_exit(caller_rc, final_status, completion_error)
        report(f"direct-child: incomplete custody: state_capture_error={completion_error}",
                      sys.stderr)
    report(f"DIRECT_CHILD_EXIT={exit_code} NATIVE_CALLER_EXIT={caller_rc} "
                  f"NATIVE_CLASS={result.get('class', 'unknown')} FRONT_DOOR_EXIT={front_door} "
                  f"FINAL_STATUS={final_status} "
                  f"CUSTODY_STATUS={'incomplete' if custody_error or completion_error else 'complete'}")
    return exit_code


def native_refused(state, code, text):
    """Refused after the attempt record exists and before any native task."""
    append_state(state, text + f"dispatcher_exit={code}\nend_utc={utc_now()}\n")
    report(f"DIRECT_CHILD_EXIT={code} NATIVE_TASK=not-started STATE={state}")
    return code


def run_foreground(command, cwd, interrupts):
    """The caller in the foreground; SIGINT/SIGTERM/SIGHUP are passed on as its
    own cancel and the wait continues (the caller bounds its collection)."""
    if interrupts.received is not None:
        return None, "interrupted-before-launch"
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, cwd=cwd)
    except OSError as error:
        return None, f"{type(error).__name__}"
    interrupts.collect(process)
    try:
        while True:
            try:
                return process.wait(), None
            except InterruptedError:
                continue
    finally:
        interrupts.process = None


def read_native_result(path):
    try:
        if path.stat().st_size > 16 * 1024 * 1024:
            return {}, "oversized"
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, "missing"
    except (OSError, ValueError) as error:
        return {}, f"unreadable:{type(error).__name__}"
    return (value, "present") if isinstance(value, dict) else ({}, "unreadable:not-object")


def native_exit(caller_rc, final_status, custody_error):
    """The caller's documented code; 6 (incomplete) when its answer could not be
    kept; 128+N for a signal."""
    if caller_rc is None:
        return 8
    if caller_rc < 0:
        return 128 - caller_rc
    if caller_rc == 0 and (final_status != "present" or custody_error):
        return 6
    return caller_rc


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
        record.update(resolve_transport(config, args, record))
        provider = record["provider"]
        if provider == "claude" and record["transport"] == "direct":
            wrapper = args.profile or config["providers"]["claude"]["pool"][0]
            if not args.dry_run and shutil.which(wrapper) is None:
                raise Refusal(f"Claude wrapper {wrapper!r} is not on PATH")
        if args.dry_run:
            if args.profile is not None:
                profile, source = args.profile, "explicit"
            else:
                profile, source = preview_profile(config, provider)
            record.update(profile=profile, profile_source=source)
            child_grant = (record["transport"] == "native" and provider == "claude"
                           and record["native_children"] is not None)
            if child_grant:
                child, child_source = preview_profile(config, "codex")
                record.update(child_profile=child, child_profile_source=child_source)
            if record["transport"] == "native" and (provider == "codex" or child_grant):
                need, margin = credential_need(config, record["native_deadline_s"])
                command = native_command(record, args.cwd, "<attempt>/prompt.md", "<attempt>/native",
                                         "<attempt>/native-child-credential" if child_grant
                                         else "<attempt>/native-credential", margin)
            elif record["transport"] == "native":
                command = native_command(record, args.cwd, "<attempt>/prompt.md", "<attempt>/native")
            elif provider == "claude":
                command = claude_command(record, profile)
            else:
                command = codex_command(args, record, profile, config)
            print("DRY RUN: " + json.dumps(record, sort_keys=True))
            print("DRY RUN: would run: " + shlex.join(command))
            if provider == "claude" and record["transport"] == "direct":
                print("DRY RUN: denial arguments are conditional on pre-task private help metadata")
            if child_grant:
                print("DRY RUN: the Claude parent's store is not read or leased; one separate "
                      f"access-only Codex child grant from {child} (not reserved) must cover {need}s "
                      "under that profile's lease, or one official renewal is attempted first")
            elif record["transport"] == "native" and provider == "claude":
                print("DRY RUN: no credential, store read or profile lease; the site route fixes the store")
            elif record["transport"] == "native":
                print(f"DRY RUN: at launch, under the profile lease, the access token must cover "
                      f"{need}s or one official renewal is attempted first")
            print("DRY RUN: no files written, rotation not advanced, no model launched")
            return 0
        if args.profile is not None:
            profile, source = args.profile, "explicit"
        else:
            profile, source = allocate_profile(config, provider)
        record.update(profile=profile, profile_source=source)
        if (record["transport"] == "native" and provider == "claude"
                and record["native_children"] is not None):
            # Only after every input check: the opted-in Claude parent's one
            # separate child grant takes the next Codex pool profile.
            child, child_source = allocate_profile(config, "codex")
            record.update(child_profile=child, child_profile_source=child_source)
    except Refusal as error:
        print(f"direct-child: {error}", file=sys.stderr)
        return 2
    route_json = json.dumps(record, sort_keys=True)
    print(f"DIRECT_CHILD_ROUTE={route_json}", flush=True)
    if record["transport"] == "native":
        return run_native(args, config, record, profile)
    if provider == "codex":
        command = codex_command(args, record, profile, config, route_json)
        os.execv(command[0], command)
    try:
        return run_claude(args, record, claude_command(record, profile))
    except Refusal as error:
        print(f"direct-child: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
