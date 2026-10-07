"""Native transport on registered original-store account routes, with a fake
Codex CLI and a fake native caller. No real CLI, profile, store, issuer or
model is reached, and no credential exists to read: the fake profiles hold
only an unreadable sentinel."""

import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest


HERE = Path(__file__).parent
DISPATCH = HERE / "dispatch.py"
CONFIG = HERE / "routes.toml"
LEASE = ".oulipoly-direct-child.lease"
PROFILES = (".codex", ".codex2", ".codex3", ".codex4", ".codex5")
POOL = (".codex2", ".codex3", ".codex4", ".codex5")
# A second Claude store the dispatcher accepts, which no native binding names.
TWO_STORES = ('manual_profiles = ["claude5"]', 'manual_profiles = ["claude5", "claude6"]')
# ROOT's selected produced package path: installation selection, not a
# compatibility check or evidence that this executable is installed.
PRODUCED_CALLER = ("/opt/oulipoly-native/oulipoly-native-linux-x86_64-"
                   "9bf6d295f2d5-de23d83ac522/bin/oulipoly-native-call")
RETIRED_FLAGS = ("--credential-codex-profile", "--child-credential-codex-profile",
                 "--credential-margin", "--credential-opencode-auth", "--child-route",
                 "--child-max-starts", "--child-max-concurrent", "--model", "--effort")
CHILD_REFUSAL = "native children are refused before any effect"

LEASE_PROBE = r'''
def lease_probe(home):
    """Which of our Codex profile leases are held now, and whether this
    process inherited any of their descriptors."""
    held, inherited = {}, False
    links = set()
    for fd in os.listdir("/proc/self/fd"):
        try:
            links.add(os.path.realpath(f"/proc/self/fd/{fd}"))
        except OSError:
            pass
    for profile in (".codex", ".codex2", ".codex3", ".codex4", ".codex5"):
        path = os.path.join(home, profile, ".oulipoly-direct-child.lease")
        if not os.path.exists(path):
            continue
        inherited |= os.path.realpath(path) in links
        probe = os.open(path, os.O_RDWR)
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            held[profile] = False
        except BlockingIOError:
            held[profile] = True
        finally:
            os.close(probe)
    return {"leases_held": sorted(p for p, h in held.items() if h), "lease_inherited": inherited}
'''

FAKE_CODEX = r'''#!/usr/bin/env python3
import fcntl, json, os, sys, tomllib
from pathlib import Path
''' + LEASE_PROBE + r'''
args = sys.argv[1:]
home = Path(os.environ["CODEX_HOME"])
def note(**fields):
    with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
        calls.write(json.dumps({"tool": "codex", "args": args, "home": str(home), **fields}) + "\n")
if args[-3:] == ["mcp", "list", "--json"]:
    note()
    names = list(tomllib.load(open(home / "config.toml", "rb")).get("mcp_servers", {}))
    if any("openaiDeveloperDocs.url" in arg for arg in args):
        names.append("openaiDeveloperDocs")
    print(json.dumps([{"name": n, "enabled": f"mcp_servers.{n}.enabled=false" not in args} for n in names]))
    sys.exit(0)
if args[-2:] == ["features", "list"]:
    note()
    print("multi_agent    stable    " + ("false" if "features.multi_agent=false" in args else "true"))
    sys.exit(0)
assert args[:1] == ["exec"], args
note(**lease_probe(os.environ["HOME"]))
prompt = sys.stdin.read()
Path(args[args.index("-o") + 1]).write_text("final: " + prompt, encoding="utf-8")
print("live: " + prompt.strip())
'''

# A signal delivered to this fake attempt's dispatcher just after the caller
# is spawned, so cancellation forwarding and collection are exercised.
CONTROL_WRAPPER = r'''
import json, os, runpy, subprocess, sys
popen = subprocess.Popen
def interrupted(command, *args, **kwargs):
    proc = popen(command, *args, **kwargs)
    if os.path.basename(command[0]) == "native-call":
        with open(os.environ["FAKE_CALLS"], "a") as calls:
            calls.write(json.dumps({"tool": "caller-spawn", "pid": proc.pid}) + "\n")
        os.kill(os.getpid(), int(os.environ["FAKE_SIGNAL"]))
    return proc
subprocess.Popen = interrupted
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
'''

FAKE_CALLER = r'''#!/usr/bin/env python3
import fcntl, json, os, sys, time
''' + LEASE_PROBE + r'''
args = sys.argv[1:]
value = lambda flag: args[args.index(flag) + 1]
mode = os.environ.get("FAKE_CALLER", "answered")
def note(**fields):
    with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
        calls.write(json.dumps({"tool": "native-call", "args": args, "pid": os.getpid(),
                                **lease_probe(os.environ["HOME"]), **fields}) + "\n")
note()
if mode == "block":
    # Hold the call open until the test releases it, so the lease is
    # observed from outside while the caller runs.
    started = os.environ["FAKE_STARTED"]
    open(started, "w").close()
    deadline = time.monotonic() + 30
    while not os.path.exists(os.environ["FAKE_RELEASE"]) and time.monotonic() < deadline:
        time.sleep(0.05)
    mode = "answered"
out = value("--out")
os.mkdir(out, 0o700)
if mode == "partial":
    sys.exit(6)
classes = {"answered": ("answered", 0, 0), "refused": ("front-door-refused", 90, 4),
           "no-answer": ("no-answer", 0, 1)}
native_class, front_door, code = classes[mode]
answered = mode == "answered"
json.dump({"class": native_class,
           "front_door_exit": int(os.environ.get("FAKE_FRONT_DOOR", front_door)),
           "answer": {"present": answered}, "counts": {"bash_accepted": 2, "bash_ended": 2},
           "processing_completion": "not-observed"}, open(os.path.join(out, "result.json"), "w"))
if answered:
    open(os.path.join(out, "final.md"), "w").write("final: " + open(value("--prompt-file")).read())
sys.exit(code)
'''


def state_of(attempt):
    return dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())


class NativeTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home, self.bin = self.root / "home", self.root / "bin"
        self.cwd, self.runs = self.root / "tree", self.root / "runs"
        self.prompt = self.root / "prompt.md"
        self.calls = self.root / "calls.jsonl"
        for directory in (self.home, self.bin, self.cwd):
            directory.mkdir()
        self.prompt.write_text("Do the bounded task.\n", encoding="utf-8")
        for name, body in (("codex", FAKE_CODEX), ("native-call", FAKE_CALLER)):
            (self.bin / name).write_text(body, encoding="utf-8")
            (self.bin / name).chmod(0o755)
        for profile in PROFILES:
            (self.home / profile).mkdir()
            (self.home / profile / "config.toml").write_text("", encoding="utf-8")
            # Any dispatcher read of the store's login would fail on this.
            sentinel = self.home / profile / "auth.json"
            sentinel.write_text("SECRET-ORIGINAL-STORE", encoding="utf-8")
            sentinel.chmod(0)
        self.env = os.environ | {
            "HOME": str(self.home), "FAKE_CALLS": str(self.calls),
            "PATH": os.pathsep.join((str(self.bin), "/usr/bin", "/bin"))}
        self.config = self.write_config()

    def write_config(self, raw=(), **replace):
        text = CONFIG.read_text(encoding="utf-8")
        text = re.sub(r'(?m)^caller = ".*"$', f'caller = "{self.bin / "native-call"}"', text)
        for old, new in raw:
            self.assertEqual(text.count(old), 1, old)
            text = text.replace(old, new)
        for key, value in replace.items():
            text, count = re.subn(rf'(?m)^{key} = .*$', f"{key} = {value}", text)
            self.assertEqual(count, 1, key)
        path = self.root / f"routes-{len(list(self.root.glob('routes-*')))}.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def dispatch(self, *extra, env=None, config=None, timeout=60, runs=None, wait=True):
        env = env or self.env
        prefix = [sys.executable, "-c", CONTROL_WRAPPER] if "FAKE_SIGNAL" in env else []
        command = [*prefix, str(DISPATCH), "--config", config or self.config, "--cwd", str(self.cwd),
                   "--prompt", str(self.prompt), "--runs-dir", str(runs or self.runs), "--id", "child",
                   *extra]
        if not wait:
            return subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
        return subprocess.run(command, env=env, capture_output=True, text=True, check=False,
                              timeout=timeout)

    def resolved(self, *extra, config=None):
        result = self.dispatch("--dry-run", *extra, config=config)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith("DRY RUN: {"))
        command = next(l for l in result.stdout.splitlines() if l.startswith("DRY RUN: would run: "))
        return (json.loads(line.removeprefix("DRY RUN: ")),
                shlex.split(command.removeprefix("DRY RUN: would run: ")), result.stdout)

    def calls_of(self, tool):
        if not self.calls.exists():
            return []
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        return [call for call in calls if call["tool"] == tool
                and (tool != "codex" or call["args"][:1] == ["exec"])]

    def attempt(self, runs=None):
        attempts = list((runs or self.runs).iterdir())
        self.assertEqual(len(attempts), 1)
        return attempts[0], state_of(attempts[0])

    def counter(self):
        path = self.home / ".local" / "state" / "direct-child" / "codex.counter"
        return path.read_text().strip() if path.exists() else None

    def no_effects(self):
        """Nothing allocated, leased, written or launched."""
        self.assertFalse(self.runs.exists(), "attempt written")
        self.assertFalse(self.calls.exists(), "a codex or caller process ran")
        self.assertFalse((self.home / ".local").exists(), "rotation counter touched")
        for profile in PROFILES:
            self.assertFalse((self.home / profile / LEASE).exists(), profile)

    def assert_no_credential_args(self, argv):
        for flag in RETIRED_FLAGS:
            self.assertNotIn(flag, argv)
        self.assertFalse(any("credential" in arg for arg in argv), argv)

    def claude_native(self, *extra, env=None, runs=None, config=None):
        # An unreadable original store: any dispatcher read of it would fail.
        store = self.home / ".claude5"
        if not store.exists():
            store.mkdir()
            (store / ".credentials.json").write_text("SECRET-CLAUDE-STORE", encoding="utf-8")
            store.chmod(0)
            self.addCleanup(store.chmod, 0o700)
        return self.dispatch(*extra, env=env, runs=runs, config=config)

    # ------------------------------------------------------------ selection

    def test_sol_contexts_map_the_chosen_profile_onto_its_account_route(self):
        cases = [(), ("--class", "correction", "--basis", "frame.md"), ("--seat", "observer")]
        cases += [("--seat", seat, "--class", "correction", "--basis", "frame.md", "--kind", "technical")
                  for seat in ("maker", "investigator", "method-steward")]
        reason = ("--override-reason", "selection control")
        cases += [("--route", route, *reason) for route in ("default", "refine")]
        cases += [("--model", alias, *reason) for alias in ("gpt", "gpt-high")]
        cases += [("--model", "gpt-6.1-sol", "--provider", "codex", "--effort", "high", *reason)]
        for extra in cases:
            with self.subTest(extra=extra):
                record, argv, out = self.resolved(*extra)
                self.assertEqual((record["transport"], record["transport_rule"], record["site_route"],
                                  record["profile"], record["profile_source"], record["model"],
                                  record["effort"], record["native_credential"], record["native_deadline_s"]),
                                 ("native", "default-native", "sol-high-codex2", ".codex2",
                                  "rotation-preview:0 (not reserved)", "gpt-6.1-sol", "high", "none", 7200))
                self.assertEqual(argv, [str(self.bin / "native-call"), "--route", "sol-high-codex2",
                                        "--prompt-file", "<attempt>/prompt.md", "--cwd", str(self.cwd),
                                        "--out", "<attempt>/native", "--trusted-task", "--deadline", "7200"])
                self.assertIn("lease is held for the whole caller operation", out)
                self.assertNotIn("must cover", out)
        # .codex is explicit-only and maps to its own route; each profile to its own.
        for profile in PROFILES:
            with self.subTest(profile=profile):
                record, argv, _ = self.resolved("--profile", profile, *reason)
                self.assertEqual((record["profile"], record["profile_source"], record["site_route"]),
                                 (profile, "explicit", "sol-high-" + profile[1:]))
                self.assertEqual(record["native_account_routes"], {profile: "sol-high-" + profile[1:]})
                self.assertEqual(argv[1:3], ["--route", "sol-high-" + profile[1:]])
        record, _, _ = self.resolved("--transport", "native")
        self.assertEqual((record["transport_source"], record["transport_rule"]), ("explicit", "explicit-native"))
        record, argv, _ = self.resolved("--native-deadline", "1800")
        self.assertEqual((record["native_deadline_s"], argv[-1]), (1800, "1800"))
        self.no_effects()

    def test_standalone_luna_contexts_map_natively_on_the_same_account_routes(self):
        reason = ("--override-reason", "explicit route")
        for extra in (("--seat", "scout"), ("--seat", "explorer"),
                      ("--seat", "scout", "--class", "new-foundation", "--basis", "b"),
                      ("--route", "explore", *reason),
                      ("--model", "gpt-6-luna", "--provider", "codex", "--effort", "max", *reason)):
            with self.subTest(extra=extra):
                record, argv, _ = self.resolved(*extra)
                self.assertEqual((record["transport"], record["transport_rule"], record["provider"],
                                  record["model"], record["effort"], record["site_route"]),
                                 ("native", "default-native", "codex", "gpt-6-luna", "max", "luna-max-codex2"))
                self.assertEqual(argv[1:3], ["--route", "luna-max-codex2"])
                self.assert_no_credential_args(argv)
        # Context still chooses the model first: an effort override leaves Luna max.
        record, _, _ = self.resolved("--seat", "scout", "--effort", "low", "--override-reason", "cheaper")
        self.assertEqual((record["transport"], record["transport_rule"], record["model"], record["effort"]),
                         ("direct", "default-native-unmapped-direct", "gpt-6-luna", "low"))
        self.no_effects()

    def test_unmapped_bindings_run_direct_by_rule_and_explicit_native_is_refused(self):
        config = self.write_config(raw=[TWO_STORES, ('".codex" = "sol-high-codex"\n', '')])
        reason = ("--override-reason", "unmapped binding")
        cases = [(("--seat", "framer", "--effort", e, *reason), "claude", "claude-opus-5-5", e)
                 for e in ("low", "xhigh", "max")]
        cases += [(("--model", "claude-sonnet-5-5", "--provider", "claude", "--effort", "high", *reason),
                   "claude", "claude-sonnet-5-5", "high"),
                  (("--seat", "decider", "--profile", "claude6", *reason), "claude", "claude-opus-5-5", "medium"),
                  (("--model", "gpt-xhigh", *reason), "codex", "gpt-6.1-sol", "xhigh"),
                  (("--model", "gpt-medium", *reason), "codex", "gpt-6.1-sol", "medium"),
                  # An explicit profile the binding does not map is a different binding.
                  (("--profile", ".codex", *reason), "codex", "gpt-6.1-sol", "high")]
        for extra, provider, model, effort in cases:
            with self.subTest(extra=extra):
                record, _, _ = self.resolved(*extra, config=config)
                self.assertEqual((record["transport"], record["transport_rule"], record["provider"],
                                  record["model"], record["effort"], record["site_route"]),
                                 ("direct", "default-native-unmapped-direct", provider, model, effort, None))
                result = self.dispatch("--transport", "native", *extra, config=config)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("no native site route", result.stderr)
        # Unmapped .codex still maps Luna on its own declared route.
        record, _, _ = self.resolved("--seat", "scout", "--profile", ".codex", *reason, config=config)
        self.assertEqual(record["site_route"], "luna-max-codex")
        self.no_effects()

    def test_explicit_direct_choice_is_recorded_and_launches_only_direct(self):
        for seat in ("observer", "scout"):
            with self.subTest(seat=seat):
                self.calls.unlink(missing_ok=True)
                runs = self.root / seat
                default, _, _ = self.resolved("--seat", seat)
                direct, _, _ = self.resolved("--seat", seat, "--transport", "direct")
                for field in ("route", "rule", "provider", "model", "effort", "profile"):
                    self.assertEqual(direct[field], default[field], field)
                self.assertEqual((direct["transport"], direct["transport_rule"], direct["site_route"]),
                                 ("direct", "explicit-direct", None))
                result = self.dispatch("--seat", seat, "--transport", "direct", runs=runs)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                (task,) = self.calls_of("codex")
                self.assertEqual(self.calls_of("native-call"), [])
                self.assertEqual(task["lease_inherited"], False)
                _, state = self.attempt(runs)
                self.assertEqual(state["transport"], "direct")

    def test_native_deadline_is_refused_unless_the_launch_runs_native(self):
        for extra in (("--seat", "observer", "--transport", "direct"), ("--seat", "scout", "--transport", "direct"),
                      ("--seat", "framer", "--effort", "low", "--override-reason", "unmapped"),
                      ("--model", "gpt-xhigh", "--override-reason", "CRW opaque alias")):
            for dry in ((), ("--dry-run",)):
                with self.subTest(extra=extra, dry=dry):
                    result = self.dispatch(*dry, "--native-deadline", "600", *extra)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("applies only to a native launch", result.stderr)
        for value in ("0", "-5", "7201"):
            with self.subTest(value=value):
                result = self.dispatch("--native-deadline", value, "--seat", "scout")
                self.assertEqual(result.returncode, 2, result.stdout)
        lower = self.write_config(max_deadline_s=3600, deadline_s=3600)
        result = self.dispatch("--native-deadline", "3601", config=lower)
        self.assertEqual(result.returncode, 2)
        self.assertIn("at most 3600", result.stderr)
        self.no_effects()

    def test_binding_config_requires_an_account_route_per_codex_pool_profile(self):
        sol = '[[native.bindings]]\nprovider = "codex"\nmodel = "gpt-6.1-sol"\neffort = "high"\n'
        claude = ('[[native.bindings]]\nprovider = "claude"\nmodel = "claude-opus-5-5"\n'
                  'effort = "medium"\nprofile = "claude5"\n')
        cases = (([('".codex3" = "sol-high-codex3"\n', '')], "must map every Codex pool profile"),
                 ([('".codex3" = "sol-high-codex3"\n', '".codex3" = "sol-high-codex3"\n".codex9" = "x"\n')],
                  "only configured Codex profiles"),
                 ([(sol, sol + 'site_route = "sol-high"\n')], "site_routes for a Codex binding"),
                 ([(sol, sol + 'profile = ".codex2"\n')], "site_routes for a Codex binding"),
                 ([(claude, claude.replace('profile = "claude5"\n', ''))], "profile"),
                 ([(claude, claude.replace('"claude5"', '"claude6"'))], "not a configured Claude profile"),
                 ([('"luna-max-codex4"', '"sol-high-codex4"')], "distinct site routes"),
                 ([('".codex2" = "sol-high-codex2"', '".codex2" = "bad route"')], "site route names"),
                 ([('\ndeadline_s = 7200\n', '\ndeadline_s = 7200\nslack_s = 300\n')], "slack_s retired"),
                 ([('\ndeadline_s = 7200\n', '\ndeadline_s = 7200\nrenew_timeout_s = 60\n')], "renew_timeout_s retired"),
                 ([('max_deadline_s = 7200\n', 'max_deadline_s = 7200\n\n[native.children]\nroutes = ["luna-max"]\n')],
                  "children retired"),
                 ([(claude + 'site_route = "opus-medium"\n', claude + 'site_route = "opus-medium"\n'
                    'children = ["luna-max"]\n')], "needs exactly"))
        for raw, message in cases:
            with self.subTest(message=message):
                result = self.dispatch("--dry-run", "--seat", "framer", config=self.write_config(raw=raw))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(message, result.stderr)
        self.no_effects()

    # ------------------------------------------------------- native attempts

    def test_rotation_selects_each_profile_and_its_route_under_a_whole_call_lease(self):
        launches = [("--seat", "scout"), ("--seat", "observer"), ("--seat", "explorer"),
                    (), ("--seat", "scout")]
        for index, extra in enumerate(launches):
            result = self.dispatch(*extra, runs=self.root / f"runs-{index}")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.counter(), "5")
        calls = self.calls_of("native-call")
        expected = [(".codex2", "luna-max-codex2"), (".codex3", "sol-high-codex3"),
                    (".codex4", "luna-max-codex4"), (".codex5", "sol-high-codex5"),
                    (".codex2", "luna-max-codex2")]
        self.assertEqual([call["args"][call["args"].index("--route") + 1] for call in calls],
                         [route for _, route in expected])
        for index, (call, (profile, route)) in enumerate(zip(calls, expected)):
            with self.subTest(index=index):
                self.assert_no_credential_args(call["args"])
                # The chosen profile, and only it, is leased while the caller runs,
                # and the caller does not inherit the lease descriptor.
                self.assertEqual((call["leases_held"], call["lease_inherited"]), ([profile], False))
                attempt, state = self.attempt(self.root / f"runs-{index}")
                self.assertEqual((state["profile"], state["site_route"], state["credential"],
                                  state["account_store"], state["lease_scope"], state["lease_status"],
                                  state["native_caller_exit"], state["final_status"],
                                  state["custody_status"], state["dispatcher_exit"]),
                                 (profile, route, "none", str(self.home / profile),
                                  "whole caller operation", "acquired", "0", "present", "complete", "0"))
                self.assertIn("lease_released_utc", state)
                for key in ("renewal", "issuer_contact", "credential_need_s", "credential_snapshot_removed"):
                    self.assertNotIn(key, state)
                self.assertEqual(sorted(p.name for p in attempt.iterdir()),
                                 ["final.md", "native", "prompt.md", "route.json", "state.txt"])
                route_json = json.loads((attempt / "route.json").read_text())
                self.assertEqual((route_json["site_route"], route_json["profile"],
                                  route_json["native_credential"]), (route, profile, "none"))
                self.assertEqual(stat.S_IMODE(attempt.stat().st_mode), 0o700)
        # After every call each lease is free again, and no store login was read.
        for profile in POOL:
            with open(self.home / profile / LEASE, "a") as probe:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(stat.S_IMODE((self.home / profile / "auth.json").stat().st_mode), 0)
        self.assertFalse((self.home / ".codex" / LEASE).exists(), ".codex is explicit-only")
        self.assertEqual(self.calls_of("codex"), [], "no app-server, CLI or direct fallback")

    def test_the_lease_spans_the_running_call_and_a_second_writer_waits_or_refuses(self):
        started, release = self.root / "started", self.root / "release"
        env = self.env | {"FAKE_CALLER": "block", "FAKE_STARTED": str(started), "FAKE_RELEASE": str(release)}
        fixed = ("--profile", ".codex3", "--override-reason", "one contended profile")
        config = self.write_config(wait_s=1)
        first = self.dispatch("--seat", "scout", *fixed, env=env, config=config,
                              runs=self.root / "first", wait=False)
        try:
            deadline = time.monotonic() + 20
            while not started.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(started.exists(), "first caller did not start")
            # While the first caller runs, native and direct writers of .codex3 refuse (75).
            native = self.dispatch("--seat", "observer", *fixed, config=config, runs=self.root / "second")
            self.assertEqual(native.returncode, 75, native.stdout + native.stderr)
            self.assertIn("NATIVE_TASK=not-started", native.stdout)
            _, state = self.attempt(self.root / "second")
            self.assertEqual((state["lease_status"], state["dispatcher_exit"]), ("timeout", "75"))
            self.assertNotIn("native_command", state)
            direct = self.dispatch("--seat", "observer", "--transport", "direct", *fixed, config=config,
                                   runs=self.root / "direct")
            self.assertEqual(direct.returncode, 75, direct.stdout + direct.stderr)
            # Another profile is not blocked.
            other = self.dispatch("--seat", "observer", "--profile", ".codex4", "--override-reason", "free",
                                  config=config, runs=self.root / "other")
            self.assertEqual(other.returncode, 0, other.stdout + other.stderr)
        finally:
            release.touch()
            out, err = first.communicate(timeout=60)
        self.assertEqual(first.returncode, 0, out + err)
        self.assertEqual(len(self.calls_of("native-call")), 2)
        self.assertEqual(self.calls_of("codex"), [])
        # Released after the call: the same profile is usable again.
        again = self.dispatch("--seat", "observer", *fixed, config=config, runs=self.root / "again")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)

    def test_caller_outcomes_propagate_once_without_replay_or_direct_fallback(self):
        for mode, code, result_status, native_class in (("refused", 4, "present", "front-door-refused"),
                                                        ("no-answer", 1, "present", "no-answer"),
                                                        ("partial", 6, "missing", "unknown")):
            for seat in ("scout", "observer"):
                with self.subTest(mode=mode, seat=seat):
                    self.calls.unlink(missing_ok=True)
                    runs = self.root / f"runs-{mode}-{seat}"
                    result = self.dispatch("--seat", seat, env=self.env | {"FAKE_CALLER": mode}, runs=runs)
                    self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                    self.assertEqual(len(self.calls_of("native-call")), 1)
                    self.assertEqual(self.calls_of("codex"), [], "no direct fallback")
                    _, state = self.attempt(runs)
                    self.assertEqual((state["native_caller_exit"], state["native_result"],
                                      state["native_class"], state["final_status"], state["dispatcher_exit"]),
                                     (str(code), result_status, native_class, "missing", str(code)))
                    self.assertIn("do-not-replay", state["native_retry"])
                    self.assertIn("lease_released_utc", state)

    def test_signals_reach_the_caller_and_the_lease_is_released_after_collection(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig):
                self.calls.unlink(missing_ok=True)
                runs = self.root / f"signal-{sig}"
                env = self.env | {"FAKE_SIGNAL": str(int(sig))}
                result = self.dispatch("--seat", "scout", "--profile", ".codex4", "--override-reason", "fixed",
                                       env=env, runs=runs)
                self.assertEqual(result.returncode, 128 + sig, result.stdout + result.stderr)
                _, state = self.attempt(runs)
                self.assertEqual(state["native_signal"], str(int(sig)))
                self.assertNotEqual(state["native_caller_exit"], "none", "started caller must be collected")
                self.assertIn("lease_released_utc", state)
                self.assertEqual(len(self.calls_of("caller-spawn")), 1)
                with open(self.home / ".codex4" / LEASE, "a") as probe:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_signal_while_waiting_for_the_lease_starts_nothing(self):
        lease = os.open(self.home / ".codex2" / LEASE, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, lease)
        fcntl.flock(lease, fcntl.LOCK_EX)
        proc = self.dispatch("--seat", "scout", "--profile", ".codex2", "--override-reason", "busy", wait=False)
        deadline = time.monotonic() + 20
        while not any(self.runs.rglob("state.txt")) and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.3)
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 128 + signal.SIGTERM, out + err)
        _, state = self.attempt()
        self.assertEqual((state["native_task"], state["native_signal"]), ("not-started", str(int(signal.SIGTERM))))
        self.assertNotIn("lease_status", state)
        self.assertEqual(self.calls_of("native-call"), [])

    # --------------------------------------------------------------- claude

    def test_claude_native_uses_no_credential_lease_store_read_or_rotation(self):
        for extra, site_route in ((("--seat", "decider"), "opus-medium"),
                                  (("--seat", "maker", "--kind", "creative"), "opus-high")):
            with self.subTest(site_route=site_route):
                self.calls.unlink(missing_ok=True)
                runs = self.root / site_route
                result = self.claude_native(*extra, runs=runs)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                (call,) = self.calls_of("native-call")
                self.assertEqual(call["args"][:2], ["--route", site_route])
                self.assert_no_credential_args(call["args"])
                self.assertEqual(call["leases_held"], [])
                attempt, state = self.attempt(runs)
                self.assertEqual((state["provider"], state["profile"], state["site_route"],
                                  state["credential"], state["profile_lease"], state["dispatcher_exit"]),
                                 ("claude", "claude5", site_route, "none", "none", "0"))
                for key in ("lease_status", "lease_scope", "account_store", "lease_released_utc"):
                    self.assertNotIn(key, state)
                self.assertIn("Read/Write/Edit bodies", state["native_record"])
                route = json.loads((attempt / "route.json").read_text())
                self.assertEqual((route["native_credential"], route["profile_source"]), ("none", "fixed"))
        self.assertFalse((self.home / ".local").exists())
        for profile in PROFILES:
            self.assertFalse((self.home / profile / LEASE).exists(), profile)
        self.assertFalse((self.bin / "claude5").exists())
        self.assertEqual(stat.S_IMODE((self.home / ".claude5").stat().st_mode), 0)

    def test_claude_native_outcomes_are_legible_without_replay_or_direct_fallback(self):
        wrapper = self.bin / "claude5"
        wrapper.write_text("#!/bin/sh\necho direct >> \"$FAKE_CALLS.claude5\"\nexit 0\n", encoding="utf-8")
        wrapper.chmod(0o755)
        cases = (("answered", "87", 0, "answered", "present", "owner closed"),
                 ("answered", "0", 0, "answered", "present", "entry ended"),
                 ("refused", "90", 4, "front-door-refused", "missing", "refused admission"),
                 ("partial", None, 6, "unknown", "missing", "not observed"))
        for mode, front_door, code, native_class, final_status, meaning in cases:
            with self.subTest(mode=mode, front_door=front_door):
                self.calls.unlink(missing_ok=True)
                runs = self.root / f"{mode}-{front_door}"
                env = self.env | {"FAKE_CALLER": mode} | ({"FAKE_FRONT_DOOR": front_door} if front_door else {})
                result = self.claude_native("--seat", "framer", env=env, runs=runs)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertEqual(len(self.calls_of("native-call")), 1, "never replayed")
                _, state = self.attempt(runs)
                self.assertEqual((state["native_caller_exit"], state["native_class"],
                                  state["front_door_exit"], state["final_status"], state["dispatcher_exit"]),
                                 (str(code), native_class, front_door or "unknown", final_status, str(code)))
                self.assertIn(meaning, state["front_door_exit_meaning"])
        self.assertFalse(Path(str(self.calls) + ".claude5").exists(), "no direct fallback")

    def test_claude_native_signal_reaches_the_caller_and_is_collected(self):
        env = self.env | {"FAKE_SIGNAL": str(int(signal.SIGTERM))}
        result = self.claude_native("--seat", "framer", env=env)
        self.assertEqual(result.returncode, 128 + signal.SIGTERM, result.stdout + result.stderr)
        _, state = self.attempt()
        self.assertEqual(state["native_signal"], str(int(signal.SIGTERM)))
        self.assertNotEqual(state["native_caller_exit"], "none")
        self.assertEqual(len(self.calls_of("caller-spawn")), 1)

    # ------------------------------------------------------ children, config

    def test_every_native_child_option_is_refused_before_any_effect(self):
        options = (("--native-child-route", "luna-max"),
                   ("--native-child-route", "luna-max", "--native-child-max-starts", "2"),
                   ("--native-child-max-concurrent", "1"),
                   ("--native-child-max-starts", "9"))
        contexts = (("--seat", "observer"), ("--seat", "maker", "--class", "correction", "--basis", "f"),
                    ("--seat", "scout"), ("--seat", "framer"), ("--seat", "maker", "--kind", "creative"),
                    ("--seat", "observer", "--transport", "native"),
                    ("--seat", "observer", "--transport", "direct"),
                    ("--seat", "framer", "--effort", "low", "--override-reason", "unmapped"))
        for option in options:
            for context in contexts:
                for dry in ((), ("--dry-run",)):
                    with self.subTest(option=option, context=context, dry=dry):
                        result = self.claude_native(*dry, *context, *option)
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                        self.assertIn(CHILD_REFUSAL, result.stderr)
                        self.assertIn("ROOT-owned unfinished work", result.stderr)
                        self.assertNotIn("DIRECT_CHILD_ROUTE", result.stdout)
                        self.no_effects()
        self.assertFalse((self.bin / "claude5").exists())

    def test_shipped_config_selects_produced_caller_and_declares_account_routes(self):
        import tomllib
        config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["native"]["caller"], PRODUCED_CALLER)
        self.assertEqual(set(config["native"]), {"caller", "deadline_s", "max_deadline_s", "bindings"})
        bindings = {(b["provider"], b["model"], b["effort"]): b for b in config["native"]["bindings"]}
        for (model, effort), prefix in ((("gpt-6.1-sol", "high"), "sol-high-"), (("gpt-6-luna", "max"), "luna-max-")):
            self.assertEqual(bindings[("codex", model, effort)]["site_routes"],
                             {profile: prefix + profile[1:] for profile in PROFILES})
        self.assertEqual({k[2]: (b["profile"], b["site_route"]) for k, b in bindings.items() if k[0] == "claude"},
                         {"medium": ("claude5", "opus-medium"), "high": ("claude5", "opus-high")})
        self.assertEqual(config["providers"]["codex"]["pool"], list(POOL))
        # Resolve the shipped config itself (the other controls replace its caller).
        for seat, extra, site_route in (("scout", (), "luna-max-codex2"), ("explorer", (), "luna-max-codex2"),
                                        ("observer", (), "sol-high-codex2"), ("framer", (), "opus-medium"),
                                        ("maker", ("--kind", "creative"), "opus-high"),
                                        ("scout", ("--profile", ".codex", "--override-reason", "explicit account"), "luna-max-codex"),
                                        ("observer", ("--profile", ".codex", "--override-reason", "explicit account"), "sol-high-codex")):
            with self.subTest(seat=seat):
                record, argv, _ = self.resolved("--seat", seat, *extra, config=str(CONFIG))
                self.assertEqual((record["site_route"], record["native_caller"]), (site_route, PRODUCED_CALLER))
                self.assertEqual(argv[:3], [PRODUCED_CALLER, "--route", site_route])
                self.assert_no_credential_args(argv)
        self.no_effects()


if __name__ == "__main__":
    unittest.main()
