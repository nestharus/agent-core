"""Native transport, gated official renewal and profile lease, with a fake Codex
CLI (including a fake stdio app-server) and a fake native caller. No real CLI,
profile, issuer or model is reached."""

import base64
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
# deadline 7200 + 2 x 30 + 2 + 300 + 300
NEED = 7862
# A second Claude store the dispatcher accepts, which no native binding names.
TWO_STORES = ('manual_profiles = ["claude5"]', 'manual_profiles = ["claude5", "claude6"]')
SECRETS = ("SECRET-REFRESH", "person@example.com", "SECRET-STDERR", "SECRET-ID-TOKEN")

LEASE_PROBE = r'''
def lease_probe(home):
    path = os.path.join(home, ".oulipoly-direct-child.lease")
    if not os.path.exists(path):
        return {"lease_exists": False}
    inherited = False
    for fd in os.listdir("/proc/self/fd"):
        try:
            inherited |= os.path.realpath(f"/proc/self/fd/{fd}") == os.path.realpath(path)
        except OSError:
            pass
    probe = os.open(path, os.O_RDWR)
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held = False
    except BlockingIOError:
        held = True
    finally:
        os.close(probe)
    return {"lease_exists": True, "lease_held": held, "lease_inherited": inherited}
'''

FAKE_CODEX = r'''#!/usr/bin/env python3
import base64, fcntl, json, os, signal, subprocess, sys, time, tomllib
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
if args[:1] == ["exec"]:
    note(**lease_probe(home))
    prompt = sys.stdin.read()
    Path(args[args.index("-o") + 1]).write_text("final: " + prompt, encoding="utf-8")
    print("live: " + prompt.strip())
    sys.exit(0)
assert args == ["app-server", "--listen", "stdio://"], args
mode = os.environ.get("FAKE_APP_SERVER", "renew")
note(pid=os.getpid(), **lease_probe(home))
print("SECRET-STDERR refresh_token=SECRET-REFRESH person@example.com", file=sys.stderr, flush=True)
if mode == "hang":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(120)
received = []
def send(value):
    sys.stdout.write(json.dumps(value) + "\n")
    sys.stdout.flush()
for raw in sys.stdin:
    message = json.loads(raw)
    received.append(message)
    with open(os.environ["FAKE_RPC"], "a", encoding="utf-8") as rpc:
        rpc.write(raw if raw.endswith("\n") else raw + "\n")
    if message.get("method") == "initialize":
        if mode == "lingering-member":
            member = subprocess.Popen([sys.executable, "-c",
                "import os,signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "print(os.getpgrp(), flush=True); time.sleep(120)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            group = int(member.stdout.readline())
            member.stdout.close()
            note(pid=os.getpid(), member_pid=member.pid, member_group=group)
        if mode == "garbage":
            print("this is not json", flush=True)
            continue
        if mode == "init-error":
            send({"id": message["id"], "error": {"code": -32600, "message": "person@example.com"}})
            continue
        send({"method": "account/updated", "params": {"email": "person@example.com"}})
        send({"id": 999, "result": {"unrelated": True}})
        send({"id": message["id"], "result": {"userAgent": "fake/0"}})
    elif message.get("method") == "account/read":
        if mode == "rpc-error":
            send({"id": message["id"], "error": {"code": -32601, "message": "SECRET-REFRESH person@example.com"}})
            continue
        if mode in ("renew", "insufficient", "signal-renew", "lingering-member") and message.get("params") == {"refreshToken": True}:
            lifetime = int(os.environ.get("FAKE_NEW_LIFETIME", "864000"))
            payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + lifetime}).encode()).decode().rstrip("=")
            auth = json.load(open(home / "auth.json"))
            auth["tokens"]["access_token"] = "hdr." + payload + ".NEW-ACCESS"
            auth["tokens"]["refresh_token"] = "SECRET-REFRESH-2"
            auth["last_refresh"] = "2026-10-04T00:00:00Z"
            open(home / "auth.json", "w").write(json.dumps(auth))
        if mode == "signal-renew":
            os.kill(os.getppid(), int(os.environ["FAKE_SIGNAL"]))
        send({"id": message["id"], "result": {
            "account": {"type": "chatgpt", "email": "person@example.com", "planType": "pro"},
            "requiresOpenaiAuth": True}})
'''

# Faults and signals affect only this fake attempt's dispatcher. Unknown stop
# controls still perform real cleanup, then replace the observation, so a
# failed assertion cannot leave a writer behind.
CONTROL_WRAPPER = r'''
import json, os, runpy, signal, sys
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import codex_auth
mode = os.environ["CONTROL_MODE"]
if mode in ("unknown-stop", "outstanding-group"):
    stop = codex_auth._stop
    def unconfirmed(proc):
        observed = stop(proc)
        return ("unknown", None, "unknown") if mode == "unknown-stop" else (observed[0], observed[1], "present")
    codex_auth._stop = unconfirmed
elif mode == "snapshot-signal":
    opening = os.open
    def interrupted(path, *args, **kwargs):
        fd = opening(path, *args, **kwargs)
        if str(path).endswith("native-credential/auth.json"):
            os.kill(os.getpid(), int(os.environ["FAKE_SIGNAL"]))
        return fd
    os.open = interrupted
elif mode == "caller-start-signal":
    import subprocess
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
import fcntl, json, os, sys
''' + LEASE_PROBE + r'''
args = sys.argv[1:]
value = lambda flag: args[args.index(flag) + 1]
snapshot = mode_bits = child_snapshot = None
if "--credential-codex-profile" in args:
    credential = os.path.join(value("--credential-codex-profile"), "auth.json")
    snapshot = json.load(open(credential))
    mode_bits = oct(os.stat(credential).st_mode & 0o777)
if "--child-credential-codex-profile" in args:
    credential = os.path.join(value("--child-credential-codex-profile"), "auth.json")
    child_snapshot = json.load(open(credential))
    mode_bits = oct(os.stat(credential).st_mode & 0o777)
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"tool": "native-call", "args": args, "snapshot": snapshot,
                            "child_snapshot": child_snapshot,
                            "snapshot_mode": mode_bits, **lease_probe(os.environ["PROBE_HOME"])}) + "\n")
mode = os.environ.get("FAKE_CALLER", "answered")
out = value("--out")
os.mkdir(out, 0o700)
if mode == "partial":
    sys.exit(6)
classes = {"answered": ("answered", 0, 0), "refused": ("front-door-refused", 90, 4),
           "no-answer": ("no-answer", 0, 1)}
native_class, front_door, code = classes[mode]
answered = mode == "answered"
counts = {"bash_accepted": 2, "bash_ended": 2}
if "--child-route" in args:
    counts.update(child_accepted=1, child_refused=0, child_results=0)
json.dump({"class": native_class,
           "front_door_exit": int(os.environ.get("FAKE_FRONT_DOOR", front_door)),
           "answer": {"present": answered}, "counts": counts,
           "processing_completion": "not-observed"}, open(os.path.join(out, "result.json"), "w"))
if answered:
    open(os.path.join(out, "final.md"), "w").write("final: " + open(value("--prompt-file")).read())
sys.exit(code)
'''


def jwt(exp, tag):
    payload = base64.urlsafe_b64encode(json.dumps({
        "exp": exp, "https://api.openai.com/auth": {"chatgpt_account_id": "acct-fake"}}).encode())
    return "hdr." + payload.decode().rstrip("=") + "." + tag


class NativeTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home, self.bin = self.root / "home", self.root / "bin"
        self.cwd, self.runs = self.root / "tree", self.root / "runs"
        self.prompt = self.root / "prompt.md"
        self.calls, self.rpc = self.root / "calls.jsonl", self.root / "rpc.jsonl"
        for directory in (self.home, self.bin, self.cwd):
            directory.mkdir()
        self.prompt.write_text("Do the bounded task.\n", encoding="utf-8")
        for name, body in (("codex", FAKE_CODEX), ("native-call", FAKE_CALLER)):
            (self.bin / name).write_text(body, encoding="utf-8")
            (self.bin / name).chmod(0o755)
        for profile in (".codex", ".codex2", ".codex3", ".codex4", ".codex5"):
            (self.home / profile).mkdir()
            (self.home / profile / "config.toml").write_text("", encoding="utf-8")
            self.write_auth(profile, 30 * 86400)
        self.env = os.environ | {
            "HOME": str(self.home), "FAKE_CALLS": str(self.calls), "FAKE_RPC": str(self.rpc),
            "PROBE_HOME": str(self.home / ".codex4"),
            "PATH": os.pathsep.join((str(self.bin), "/usr/bin", "/bin"))}
        self.config = self.write_config()

    def write_auth(self, profile, remaining, tokens=None):
        self.old_access = jwt(int(time.time()) + remaining, "OLD-ACCESS")
        self.accesses = getattr(self, "accesses", []) + [self.old_access]
        auth = {"OPENAI_API_KEY": None, "last_refresh": "2026-09-01T00:00:00Z", "tokens": tokens or {
            "id_token": "SECRET-ID-TOKEN person@example.com", "access_token": self.old_access,
            "refresh_token": "SECRET-REFRESH-1", "account_id": "acct-fake"}}
        path = self.home / profile / "auth.json"
        path.write_text(json.dumps(auth), encoding="utf-8")
        path.chmod(0o600)

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

    def dispatch(self, *extra, env=None, config=None, timeout=60, runs=None):
        env = env or self.env
        prefix = [sys.executable, "-c", CONTROL_WRAPPER] if "CONTROL_MODE" in env else []
        command = [*prefix, str(DISPATCH), "--config", config or self.config, "--cwd", str(self.cwd),
             "--prompt", str(self.prompt), "--runs-dir", str(runs or self.runs), "--id", "child",
             *extra]
        result = subprocess.run(command,
            env=env, capture_output=True, text=True, check=False, timeout=timeout)
        if capture := os.environ.get("NATIVE_CONTROL_CAPTURE"):
            saved = Path(tempfile.mkdtemp(prefix=self._testMethodName + ".", dir=capture))
            evidence = {"command": command, "cwd": os.getcwd(), "returncode": result.returncode,
                        "stdout": result.stdout, "stderr": result.stderr,
                        "control_mode": env.get("CONTROL_MODE"),
                        "fake_app_server": env.get("FAKE_APP_SERVER"),
                        "signal": env.get("FAKE_SIGNAL"), "records": {}}
            for path in (runs or self.runs).rglob("*"):
                if path.is_file() and path.name in ("renewal.json", "state.txt", "route.json"):
                    evidence["records"][str(path)] = path.read_text()
            for path in (self.calls, self.rpc):
                if path.exists():
                    evidence["records"][str(path)] = path.read_text()
            (saved / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
            (saved / "result.json").chmod(0o600)
        return result

    def resolved(self, *extra, config=None):
        result = self.dispatch("--dry-run", *extra, config=config)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith("DRY RUN: {"))
        return json.loads(line.removeprefix("DRY RUN: ")), result.stdout

    def calls_of(self, tool):
        if not self.calls.exists():
            return []
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        return [call for call in calls if call["tool"] == tool
                and (tool != "codex" or call["args"][:1] in (["exec"], ["app-server"]))]

    def attempt(self):
        attempts = list(self.runs.iterdir())
        self.assertEqual(len(attempts), 1)
        state = dict(line.split("=", 1) for line in (attempts[0] / "state.txt").read_text().splitlines())
        return attempts[0], state

    def native(self, *extra, env=None, config=None, timeout=60, runs=None):
        return self.dispatch("--profile", ".codex4",
                             "--override-reason", "fixed profile for the control", *extra,
                             env=env, config=config, timeout=timeout, runs=runs)

    # ------------------------------------------------------------ selection

    def test_default_native_covers_existing_sol_high_contexts_and_aliases(self):
        cases = [(), ("--class", "correction", "--basis", "frame.md"),
                 ("--seat", "observer")]
        cases += [("--seat", seat, "--class", "correction", "--basis", "frame.md",
                   "--kind", "technical")
                  for seat in ("maker", "investigator", "method-steward")]
        reason = ("--override-reason", "selection control")
        cases += [("--route", route, *reason) for route in ("default", "refine")]
        cases += [("--model", alias, *reason) for alias in ("gpt", "gpt-high")]
        cases += [("--model", "gpt-6.1-sol", "--provider", "codex", "--effort", "high", *reason),
                  ("--profile", ".codex", *reason)]
        for extra in cases:
            with self.subTest(extra=extra):
                record, out = self.resolved(*extra)
                self.assertEqual((record["transport"], record["transport_source"],
                                  record["transport_rule"], record["site_route"],
                                  record["provider"], record["model"], record["effort"],
                                  record["native_deadline_s"]),
                                 ("native", "default", "default-native", "sol-high",
                                  "codex", "gpt-6.1-sol", "high", 7200))
                command = next(l for l in out.splitlines() if l.startswith("DRY RUN: would run: "))
                self.assertIn(f"{self.bin / 'native-call'} --route sol-high", command)
                self.assertIn("--trusted-task --deadline 7200", command)
                self.assertIn(f"--credential-margin {NEED - 7200 - 150}", command)
                self.assertNotIn("--model", command)
                self.assertIn(f"must cover {NEED}s", out)
        self.assertEqual((record["profile"], record["profile_source"]), (".codex", "explicit"))
        record, _ = self.resolved("--transport", "native")
        self.assertEqual((record["transport_source"], record["transport_rule"]),
                         ("explicit", "explicit-native"))
        record, _ = self.resolved("--native-deadline", "1800")
        self.assertEqual(record["native_deadline_s"], 1800)
        self.assertFalse(self.runs.exists() or self.calls.exists() or
                         (self.home / ".local").exists())

    def test_explicit_native_without_a_declared_site_route_is_refused_before_effects(self):
        config = self.write_config(raw=[TWO_STORES])
        for extra in (("--seat", "scout"),
                      ("--model", "gpt-xhigh", "--override-reason", "CRW opaque alias"),
                      ("--effort", "medium", "--override-reason", "cheaper"),
                      ("--seat", "framer", "--effort", "low", "--override-reason", "cheaper"),
                      ("--seat", "decider", "--model", "claude-sonnet-5-5", "--provider", "claude",
                       "--effort", "high", "--override-reason", "other model"),
                      ("--seat", "framer", "--profile", "claude6", "--override-reason", "other store")):
            with self.subTest(extra=extra):
                result = self.dispatch("--transport", "native", *extra, config=config)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("no native site route", result.stderr)
        # A direct-default configuration still requires native transport for a deadline.
        result = self.dispatch("--native-deadline", "60", config=self.write_config(default='"direct"'))
        self.assertEqual(result.returncode, 2)
        self.assertIn("applies only to a native launch", result.stderr)
        self.assertFalse(self.runs.exists() or self.calls.exists() or
                         (self.home / ".local").exists())

    def test_default_native_runs_unmapped_bindings_direct_by_rule_with_identity_kept(self):
        cases = [(("--seat", seat), "codex", "gpt-6-luna", "max")
                 for seat in ("scout", "explorer")]
        reason = ("--override-reason", "unmapped Claude binding")
        cases += [(("--seat", "framer", "--effort", effort, *reason), "claude", "claude-opus-5-5", effort)
                  for effort in ("low", "xhigh", "max")]
        cases += [(("--model", "claude-sonnet-5-5", "--provider", "claude", "--effort", "high",
                    *reason), "claude", "claude-sonnet-5-5", "high"),
                  (("--seat", "decider", "--profile", "claude6", *reason),
                   "claude", "claude-opus-5-5", "medium")]
        config = self.write_config(raw=[TWO_STORES])
        cases += [(("--model", alias, "--override-reason", "literal alias"),
                   "codex", "gpt-6.1-sol", effort)
                  for alias, effort in (("gpt-medium", "medium"), ("gpt-xhigh", "xhigh"))]
        cases += [(("--effort", effort, "--override-reason", "literal effort"),
                   "codex", "gpt-6.1-sol", effort)
                  for effort in ("minimal", "low", "medium", "xhigh", "max")]
        for extra, provider, model, effort in cases:
            with self.subTest(extra=extra):
                record, _ = self.resolved(*extra, config=config)
                self.assertEqual((record["transport"], record["transport_source"],
                                  record["transport_rule"], record["provider"],
                                  record["model"], record["effort"]),
                                 ("direct", "default", "default-native-unmapped-direct",
                                  provider, model, effort))
                self.assertIsNone(record["site_route"])
                self.assertIsNone(record["native_caller"])
                self.assertIsNone(record["native_deadline_s"])
        result = self.dispatch("--seat", "scout")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls_of("codex")), 1)
        self.assertEqual(self.calls_of("native-call"), [])

    def test_explicit_direct_choice_is_recorded_and_launches_only_direct(self):
        default, _ = self.resolved("--seat", "observer")
        direct, _ = self.resolved("--seat", "observer", "--transport", "direct")
        for field in ("route", "rule", "seat", "class", "kind", "provider", "model", "effort", "profile"):
            self.assertEqual(direct[field], default[field], field)
        self.assertEqual((direct["transport"], direct["transport_source"], direct["transport_rule"]),
                         ("direct", "explicit", "explicit-direct"))
        self.assertIsNone(direct["site_route"])
        self.assertIsNone(direct["native_deadline_s"])
        result = self.dispatch("--seat", "observer", "--transport", "direct")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.calls_of("codex")), 1)
        self.assertEqual(self.calls_of("native-call"), [])
        attempt, state = self.attempt()
        record = json.loads((attempt / "route.json").read_text())
        self.assertEqual((record["transport_source"], record["transport_rule"], state["transport"]),
                         ("explicit", "explicit-direct", "direct"))

    def test_default_native_maps_exactly_the_original_claude5_opus_contexts(self):
        medium = [("--seat", seat) for seat in ("framer", "decider")]
        medium += [("--seat", seat, *klass) for seat in ("maker", "investigator", "method-steward")
                   for klass in ((), ("--class", "new-foundation", "--basis", "frame.md"))]
        medium += [("--class", "new-foundation", "--basis", "frame.md"),
                   ("--route", "direction", "--override-reason", "explicit route"),
                   ("--seat", "framer", "--profile", "claude5", "--override-reason", "same store")]
        high = [("--seat", seat, "--kind", "creative", *klass)
                for seat in ("maker", "investigator", "method-steward")
                for klass in ((), ("--class", "correction", "--basis", "frame.md"))]
        high += [("--kind", "creative"), ("--seat", "framer", "--effort", "high",
                                          "--override-reason", "high effort")]
        for site_route, effort, cases in (("opus-medium", "medium", medium), ("opus-high", "high", high)):
            for extra in cases:
                with self.subTest(extra=extra):
                    record, out = self.resolved(*extra)
                    self.assertEqual((record["transport"], record["transport_rule"], record["site_route"],
                                      record["provider"], record["model"], record["effort"],
                                      record["profile"], record["native_credential"],
                                      record["native_deadline_s"]),
                                     ("native", "default-native", site_route, "claude",
                                      "claude-opus-5-5", effort, "claude5", "none", 7200))
                    command = next(l for l in out.splitlines() if l.startswith("DRY RUN: would run: "))
                    argv = shlex.split(command.removeprefix("DRY RUN: would run: "))
                    self.assertEqual(argv, [str(self.bin / "native-call"), "--route", site_route,
                                            "--prompt-file", "<attempt>/prompt.md", "--cwd", str(self.cwd),
                                            "--out", "<attempt>/native", "--trusted-task",
                                            "--deadline", "7200"])
                    self.assertIn("no credential, store read or profile lease", out)
                    self.assertNotIn("must cover", out)
        # Context still chooses the model first; the creative rule holds on every transport.
        for transport in ((), ("--transport", "native"), ("--transport", "direct")):
            with self.subTest(transport=transport):
                result = self.dispatch("--dry-run", *transport, "--seat", "maker", "--kind", "creative",
                                       "--effort", "medium", "--override-reason", "cheaper")
                self.assertEqual(result.returncode, 2)
                self.assertIn("--kind creative requires claude / claude-opus-5-5 / high", result.stderr)
        record, _ = self.resolved("--seat", "framer", "--transport", "direct")
        self.assertEqual((record["transport"], record["transport_rule"], record["site_route"],
                          record["profile"], record["effort"]),
                         ("direct", "explicit-direct", None, "claude5", "medium"))
        self.assertFalse(self.runs.exists() or self.calls.exists() or
                         (self.home / ".local").exists())

    def test_native_deadline_is_refused_unless_the_launch_runs_native(self):
        cases = [("--seat", "scout"), ("--seat", "observer", "--transport", "direct"),
                 ("--seat", "framer", "--transport", "direct"),
                 ("--seat", "framer", "--effort", "low", "--override-reason", "unmapped"),
                 ("--model", "gpt-xhigh", "--override-reason", "CRW opaque alias")]
        for extra in cases:
            for dry in ((), ("--dry-run",)):
                with self.subTest(extra=extra, dry=dry):
                    result = self.dispatch(*dry, "--native-deadline", "600", *extra)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("applies only to a native launch", result.stderr)
                    self.assertIn("direct launches have no deadline", result.stderr)
        for value in ("0", "-5"):
            for extra in ((), ("--seat", "framer"), ("--seat", "scout"), ("--transport", "direct")):
                with self.subTest(value=value, extra=extra):
                    result = self.dispatch("--dry-run", "--native-deadline", value, *extra)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("must be a positive number of seconds", result.stderr)
        result = self.dispatch("--dry-run", "--native-deadline", "soon")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid int value", result.stderr)
        for extra in ((), ("--seat", "framer"), ("--kind", "creative")):
            with self.subTest(extra=extra):
                record, out = self.resolved("--native-deadline", "1800", *extra)
                self.assertEqual((record["transport"], record["native_deadline_s"]), ("native", 1800))
                self.assertIn("--deadline 1800", out)
        self.assertFalse(self.runs.exists() or self.calls.exists() or
                         (self.home / ".local").exists())

    def test_native_binding_config_keeps_store_identity(self):
        claude = ('[[native.bindings]]\nprovider = "claude"\nmodel = "claude-opus-5-5"\n'
                  'effort = "medium"\nprofile = "claude5"\n')
        codex = '[[native.bindings]]\nprovider = "codex"\nmodel = "gpt-6.1-sol"\neffort = "high"\n'
        cases = (([(claude, claude.replace('profile = "claude5"\n', ''))], "plus profile for a Claude"),
                 ([(codex, codex + 'profile = ".codex2"\n')], "plus profile for a Claude"),
                 ([(claude, claude.replace('"claude5"', '"claude6"'))], "not a configured Claude profile"),
                 ([TWO_STORES, ('pool = ["claude5"]', 'pool = ["claude5", "claude6"]')],
                  "one-store Claude pool"),
                 ([('site_route = "opus-high"', 'site_route = "opus-medium"'),
                   ('effort = "high"\nprofile = "claude5"', 'effort = "medium"\nprofile = "claude5"')],
                  "repeats a binding"))
        for raw, message in cases:
            with self.subTest(message=message):
                result = self.dispatch("--dry-run", "--seat", "framer", config=self.write_config(raw=raw))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(message, result.stderr)
        # A second store is valid when only claude5 is bound, and never maps.
        record, _ = self.resolved("--seat", "framer", "--profile", "claude6", "--override-reason", "other",
                                  config=self.write_config(raw=[TWO_STORES]))
        self.assertEqual((record["transport"], record["transport_rule"], record["profile"]),
                         ("direct", "default-native-unmapped-direct", "claude6"))

    # ------------------------------------------------------- native attempts

    def test_fresh_token_skips_renewal_and_hands_over_an_access_only_snapshot(self):
        result = self.native()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls_of("codex"), [], "a fresh token needs no app-server")
        (call,) = self.calls_of("native-call")
        self.assertEqual(call["snapshot"], {"tokens": {"access_token": self.old_access,
                                                       "account_id": "acct-fake"}})
        self.assertEqual(call["snapshot_mode"], "0o600")
        self.assertEqual((call["lease_held"], call["lease_inherited"]), (False, False))
        args = call["args"]
        self.assertEqual(args[args.index("--route") + 1], "sol-high")
        attempt, state = self.attempt()
        self.assertFalse((attempt / "native-credential").exists())
        self.assertEqual((state["renewal"], state["issuer_contact"], state["profile_written"]),
                         ("not-needed", "none", "no"))
        self.assertEqual((state["native_caller_exit"], state["native_class"], state["final_status"],
                          state["credential_snapshot_removed"], state["custody_status"],
                          state["dispatcher_exit"], state["profile"], state["transport"]),
                         ("0", "answered", "present", "yes", "complete", "0", ".codex4", "native"))
        self.assertIn("not a complete log", state["native_record"])
        self.assertEqual((attempt / "final.md").read_text(), "final: Do the bounded task.\n")
        route = json.loads((attempt / "route.json").read_text())
        self.assertEqual((route["transport"], route["site_route"], route["profile_source"]),
                         ("native", "sol-high", "explicit"))
        self.assertEqual((route["transport_source"], route["transport_rule"]),
                         ("default", "default-native"))
        self.assertEqual(stat.S_IMODE(attempt.stat().st_mode), 0o700)
        for name in ("state.txt", "renewal.json", "route.json", "final.md"):
            self.assertEqual(stat.S_IMODE((attempt / name).stat().st_mode), 0o600, name)

    def test_stale_token_renews_once_through_the_app_server_protocol(self):
        self.write_auth(".codex4", 100)
        result = self.native()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (server,) = self.calls_of("codex")
        self.assertEqual((server["lease_held"], server["lease_inherited"]), (True, False))
        lines = self.rpc.read_text().splitlines()
        messages = [json.loads(line) for line in lines]
        self.assertEqual(messages, [
            {"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "oulipoly_direct_child", "title": None, "version": "1"},
                "capabilities": {"explicitGatewayOauth": True}}},
            {"method": "initialized"},
            {"id": 2, "method": "account/read", "params": {"refreshToken": True}}])
        (call,) = self.calls_of("native-call")
        self.assertTrue(call["snapshot"]["tokens"]["access_token"].endswith(".NEW-ACCESS"))
        self.assertNotIn("refresh_token", call["snapshot"]["tokens"])
        attempt, state = self.attempt()
        renewal = json.loads((attempt / "renewal.json").read_text())
        self.assertEqual((renewal["renewal"], renewal["issuer_contact"], renewal["profile_written"],
                          renewal["app_server"]["rpc"], renewal["app_server"]["unsolicited_lines"]),
                         ("renewed", "possible", "yes", "answered", 2))
        self.assertGreater(int(state["credential_remaining_s_after"]), NEED)
        self.assertEqual(state["dispatcher_exit"], "0")

    def test_threshold_renews_only_below_the_launch_need(self):
        for remaining, renews in ((NEED + 60, False), (NEED - 60, True)):
            with self.subTest(remaining=remaining):
                for path in (self.calls, self.rpc):
                    path.unlink(missing_ok=True)
                self.write_auth(".codex4", remaining)
                result = self.native(runs=self.root / f"runs-{remaining}")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(self.calls_of("codex")), int(renews))
        self.calls.unlink()
        self.write_auth(".codex4", 2000)
        result = self.native("--native-deadline", "600", runs=self.root / "short")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls_of("codex"), [], "a shorter deadline needs less freshness")

    def test_failed_or_unclear_renewal_refuses_once_without_repeat_or_fallback(self):
        cases = (("renew-without-change", "not-renewed", "not-observed", None),
                 ("rpc-error", "helper-error", "unknown", -32601),
                 ("init-error", "helper-error", "unknown", -32600),
                 ("garbage", "helper-protocol-error", "unknown", None),
                 ("insufficient", "renewed-insufficient", "yes", None))
        for mode, renewal_class, written, code in cases:
            with self.subTest(mode=mode):
                for path in (self.calls, self.rpc):
                    path.unlink(missing_ok=True)
                self.write_auth(".codex4", 100)
                runs = self.root / f"runs-{mode}"
                env = self.env | {"FAKE_APP_SERVER": mode, "FAKE_NEW_LIFETIME": "1000"}
                result = self.native(env=env, runs=runs)
                self.assertEqual(result.returncode, 70, result.stdout + result.stderr)
                self.assertIn("NATIVE_TASK=not-started", result.stdout)
                self.assertEqual(len(self.calls_of("codex")), 1, "one app-server, never repeated")
                self.assertEqual(self.calls_of("native-call"), [])
                (attempt,) = runs.iterdir()
                renewal = json.loads((attempt / "renewal.json").read_text())
                self.assertEqual((renewal["renewal"], renewal["profile_written"]),
                                 (renewal_class, written))
                self.assertEqual(renewal["app_server"]["error_code"], code)
                self.assertEqual(renewal["issuer_contact"], "possible", "startup may contact issuer")
                self.assertFalse((attempt / "native-credential").exists())

    def test_caller_outcomes_propagate_once_without_replay_or_direct_fallback(self):
        for mode, code, result_status, native_class in (("refused", 4, "present", "front-door-refused"),
                                                        ("partial", 6, "missing", "unknown")):
            with self.subTest(mode=mode):
                self.calls.unlink(missing_ok=True)
                runs = self.root / f"runs-{mode}"
                result = self.native(env=self.env | {"FAKE_CALLER": mode}, runs=runs)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertEqual(len(self.calls_of("native-call")), 1)
                self.assertEqual(self.calls_of("codex"), [], "no direct fallback")
                (attempt,) = runs.iterdir()
                state = dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())
                self.assertEqual((state["native_caller_exit"], state["native_result"],
                                  state["native_class"], state["final_status"],
                                  state["credential_snapshot_removed"], state["dispatcher_exit"]),
                                 (str(code), result_status, native_class, "missing", "yes", str(code)))
                self.assertIn("do-not-replay", state["native_retry"])
                self.assertFalse((attempt / "native-credential").exists())

    def claude_native(self, *extra, env=None, runs=None, config=None):
        # An unreadable original store: any dispatcher read of it would fail.
        store = self.home / ".claude5"
        if not store.exists():
            store.mkdir()
            (store / ".credentials.json").write_text("SECRET-CLAUDE-STORE", encoding="utf-8")
            store.chmod(0)
            self.addCleanup(store.chmod, 0o700)
        return self.dispatch(*extra, env=env, runs=runs, config=config)

    def test_claude_native_uses_no_credential_lease_store_read_or_rotation(self):
        for extra, site_route in ((("--seat", "decider"), "opus-medium"),
                                  (("--seat", "maker", "--kind", "creative"), "opus-high")):
            with self.subTest(site_route=site_route):
                self.calls.unlink(missing_ok=True)
                runs = self.root / site_route
                result = self.claude_native(*extra, runs=runs)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.calls_of("codex"), [], "no app-server or direct Codex")
                (call,) = self.calls_of("native-call")
                args = call["args"]
                self.assertEqual(args[args.index("--route") + 1], site_route)
                self.assertIsNone(call["snapshot"])
                for flag in ("--credential-codex-profile", "--credential-margin",
                             "--credential-opencode-auth", "--model", "--effort"):
                    self.assertNotIn(flag, args)
                (attempt,) = runs.iterdir()
                state = dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())
                self.assertEqual((state["transport"], state["provider"], state["profile"],
                                  state["site_route"], state["credential"], state["profile_lease"],
                                  state["native_caller_exit"], state["native_class"],
                                  state["final_status"], state["dispatcher_exit"]),
                                 ("native", "claude", "claude5", site_route, "none", "none",
                                  "0", "answered", "present", "0"))
                for key in ("renewal", "lease_status", "credential_need_s", "credential_snapshot_removed"):
                    self.assertNotIn(key, state)
                self.assertIn("Read/Write/Edit bodies", state["native_record"])
                self.assertIn("Read, Write and Edit", state["delegation_capability_note"])
                self.assertFalse((attempt / "renewal.json").exists())
                self.assertFalse((attempt / "native-credential").exists())
                self.assertEqual((attempt / "final.md").read_text(), "final: Do the bounded task.\n")
                route = json.loads((attempt / "route.json").read_text())
                self.assertEqual((route["native_credential"], route["profile_source"]), ("none", "fixed"))
        # No Codex lease, counter or store state was created; the claude5 wrapper was not needed.
        self.assertFalse((self.home / ".local").exists())
        for profile in (".codex", ".codex2", ".codex3", ".codex4", ".codex5"):
            self.assertFalse((self.home / profile / LEASE).exists(), profile)
        self.assertFalse((self.bin / "claude5").exists())
        self.assertEqual(stat.S_IMODE((self.home / ".claude5").stat().st_mode), 0)

    def test_claude_native_outcomes_are_legible_without_replay_or_direct_fallback(self):
        wrapper = self.bin / "claude5"
        wrapper.write_text("#!/bin/sh\necho direct >> \"$FAKE_CALLS.claude5\"\nexit 0\n", encoding="utf-8")
        wrapper.chmod(0o755)
        cases = (("answered", "87", 0, "answered", "present", "owner closed"),
                 ("answered", "0", 0, "answered", "present", "entry ended"),
                 ("no-answer", "87", 1, "no-answer", "missing", "owner closed"),
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
                (attempt,) = runs.iterdir()
                state = dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())
                self.assertEqual((state["native_caller_exit"], state["native_class"],
                                  state["front_door_exit"], state["final_status"], state["dispatcher_exit"]),
                                 (str(code), native_class, front_door or "unknown", final_status, str(code)))
                self.assertIn(meaning, state["front_door_exit_meaning"])
                self.assertIn("answered is not correctness", state["native_status_note"])
                self.assertIn("do-not-replay", state["native_retry"])
                self.assertIn(f"FRONT_DOOR_EXIT={front_door or 'unknown'}", result.stdout)
        self.assertFalse(Path(str(self.calls) + ".claude5").exists(), "no direct fallback")
        self.assertEqual(self.calls_of("codex"), [])

    def test_claude_native_signal_reaches_the_caller_and_is_collected(self):
        env = self.env | {"CONTROL_MODE": "caller-start-signal", "FAKE_SIGNAL": str(int(signal.SIGTERM))}
        result = self.claude_native("--seat", "framer", env=env)
        self.assertEqual(result.returncode, 128 + signal.SIGTERM, result.stdout + result.stderr)
        attempt, state = self.attempt()
        self.assertEqual(state["native_signal"], str(int(signal.SIGTERM)))
        self.assertNotEqual(state["native_caller_exit"], "none")
        self.assertNotIn("credential_snapshot_removed", state)
        self.assertEqual(len(self.calls_of("caller-spawn")), 1)

    def test_profile_without_a_chatgpt_access_token_is_refused_without_issuer_contact(self):
        self.write_auth(".codex4", 0, tokens={"access_token": "not-a-jwt", "refresh_token": "SECRET-REFRESH"})
        result = self.native()
        self.assertEqual(result.returncode, 70, result.stdout)
        self.assertEqual(self.calls_of("codex") + self.calls_of("native-call"), [])
        attempt, state = self.attempt()
        self.assertEqual((state["renewal"], state["issuer_contact"]), ("unavailable", "none"))

    def test_hung_app_server_is_bounded_killed_and_left_unknown(self):
        self.write_auth(".codex4", 100)
        config = self.write_config(renew_timeout_s=1)
        started = time.monotonic()
        result = self.native(env=self.env | {"FAKE_APP_SERVER": "hang"}, config=config, timeout=40)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(result.returncode, 70, result.stdout + result.stderr)
        attempt, _ = self.attempt()
        renewal = json.loads((attempt / "renewal.json").read_text())
        self.assertEqual((renewal["renewal"], renewal["profile_written"], renewal["issuer_contact"],
                          renewal["app_server"]["server_stop"]),
                         ("helper-timeout", "unknown", "possible", "killed"))
        self.assertEqual(self.calls_of("native-call"), [])

    def test_answered_fresh_token_with_unconfirmed_stop_never_launches(self):
        for mode in ("unknown-stop", "outstanding-group"):
            with self.subTest(mode=mode):
                self.calls.unlink(missing_ok=True)
                self.write_auth(".codex4", 100)
                runs = self.root / mode
                result = self.native(env=self.env | {"CONTROL_MODE": mode}, runs=runs)
                self.assertEqual(result.returncode, 70, result.stdout + result.stderr)
                self.assertEqual(len(self.calls_of("codex")), 1)
                self.assertEqual(self.calls_of("native-call"), [])
                (attempt,) = runs.iterdir()
                renewal = json.loads((attempt / "renewal.json").read_text())
                self.assertEqual(renewal["app_server"]["rpc"], "answered")
                self.assertGreater(renewal["remaining_s_after"], NEED)
                self.assertEqual((renewal["renewal"], renewal["profile_written"],
                                  renewal["issuer_contact"], renewal["expiry_changed"]),
                                 ("helper-stop-unconfirmed", "unknown", "possible", True))
                self.assertFalse((attempt / "native-credential").exists())

    def test_catchable_signals_clean_renewal_snapshot_and_caller_launch(self):
        for phase in ("renewal", "snapshot-signal", "caller-start-signal"):
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                with self.subTest(phase=phase, signal=sig):
                    self.calls.unlink(missing_ok=True)
                    self.write_auth(".codex4", 100 if phase == "renewal" else NEED + 600)
                    runs = self.root / f"{phase}-{sig}"
                    env = self.env | {"FAKE_SIGNAL": str(int(sig))}
                    env |= ({"FAKE_APP_SERVER": "signal-renew"} if phase == "renewal"
                            else {"CONTROL_MODE": phase})
                    result = self.native(env=env, runs=runs)
                    self.assertEqual(result.returncode, 128 + sig, result.stdout + result.stderr)
                    (attempt,) = runs.iterdir()
                    state = dict(line.split("=", 1) for line in
                                 (attempt / "state.txt").read_text().splitlines())
                    self.assertEqual(state["native_signal"], str(int(sig)))
                    self.assertEqual(state["credential_snapshot_removed"], "yes")
                    self.assertFalse((attempt / "native-credential").exists())
                    if phase == "renewal":
                        renewal = json.loads((attempt / "renewal.json").read_text())
                        self.assertEqual(renewal["issuer_contact"], "possible")
                        self.assertIsNotNone(renewal["app_server"]["server_exit"])
                        self.assertEqual(renewal["app_server"]["server_group_stop"], "empty")
                        self.assertEqual(len(self.calls_of("codex")), 1)
                        self.assertEqual(self.calls_of("native-call"), [])
                    elif phase == "snapshot-signal":
                        self.assertEqual(self.calls_of("codex") + self.calls_of("native-call"), [])
                    else:
                        self.assertIn("native_caller_exit", state, "started caller must be collected")
                        self.assertNotEqual(state["native_caller_exit"], "none")
                        self.assertEqual(len(self.calls_of("caller-spawn")), 1)
                        self.assertEqual(self.calls_of("codex"), [])
                    # Another own writer can acquire the ordinary lease after cleanup.
                    with open(self.home / ".codex4" / LEASE, "a") as probe:
                        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_leader_exit_still_cleans_an_outstanding_group_member(self):
        self.write_auth(".codex4", 100)
        result = self.native(env=self.env | {"FAKE_APP_SERVER": "lingering-member"})
        attempt, _ = self.attempt()
        renewal = json.loads((attempt / "renewal.json").read_text())
        self.assertEqual(renewal["app_server"]["rpc"], "answered")
        self.assertEqual(renewal["app_server"]["server_exit"], 0)
        if renewal["app_server"]["server_group_stop"] == "empty":
            self.assertEqual(renewal["app_server"]["server_stop"], "killed")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(self.calls_of("native-call")), 1)
        else:
            self.assertEqual(result.returncode, 70, result.stdout + result.stderr)
            self.assertEqual(renewal["renewal"], "helper-stop-unconfirmed")
            self.assertEqual(self.calls_of("native-call"), [])
        self.assertFalse((attempt / "native-credential").exists())
        members = [call for call in self.calls_of("codex") if "member_pid" in call]
        self.assertEqual(len(members), 1)
        member = members[0]
        self.assertEqual(member["member_group"], member["pid"])
        # Own fake PID only: an orphan zombie is residual uncertainty, not a writer.
        status = Path(f"/proc/{member['member_pid']}/stat")
        try:
            fields = status.read_text().rsplit(")", 1)[1].split()
        except FileNotFoundError:
            pass
        else:
            self.assertEqual(fields[0], "Z")

    def test_no_token_account_or_server_stderr_text_reaches_records_or_terminal(self):
        outputs = []
        for mode in ("renew", "rpc-error"):
            self.write_auth(".codex4", 100)
            result = self.native(env=self.env | {"FAKE_APP_SERVER": mode}, runs=self.runs / mode)
            outputs += [result.stdout, result.stderr]
        texts = outputs + [path.read_text(errors="replace") for path in self.runs.rglob("*")
                           if path.is_file()]
        for secret in SECRETS + tuple(self.accesses) + (".NEW-ACCESS",):
            for text in texts:
                self.assertNotIn(secret, text)

    # ------------------------------------------------- explicit child opt-in

    def no_effects(self):
        """Nothing allocated, leased, prepared, written or launched."""
        self.assertFalse(self.runs.exists(), "attempt written")
        self.assertFalse(self.calls.exists(), "a codex or caller process ran")
        self.assertFalse((self.home / ".local").exists(), "rotation counter touched")
        for profile in (".codex", ".codex2", ".codex3", ".codex4", ".codex5"):
            self.assertFalse((self.home / profile / LEASE).exists(), profile)

    def counter(self):
        path = self.home / ".local" / "state" / "direct-child" / "codex.counter"
        return path.read_text().strip() if path.exists() else None

    def test_shipped_config_pins_the_versioned_caller_and_declares_child_offers(self):
        import tomllib
        config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["native"]["caller"], "/opt/oulipoly-native/oulipoly-native-linux-"
                         "x86_64-0a24a50e6f08-924a48e58a59/bin/oulipoly-native-call")
        self.assertEqual(config["native"]["max_deadline_s"], 7200)
        self.assertEqual(config["native"]["children"],
                         {"routes": ["luna-max"], "max_starts": 4, "max_concurrent": 2})
        self.assertEqual({b["site_route"]: b["children"] for b in config["native"]["bindings"]},
                         {"sol-high": ["luna-max"], "opus-medium": ["luna-max"],
                          "opus-high": ["luna-max"]})
        # Standalone Luna still resolves direct by rule; no child flag is implied.
        for seat in ("scout", "explorer", "maker", "framer", "observer"):
            record, out = self.resolved("--seat", seat)
            self.assertIsNone(record["native_children"], seat)
            self.assertNotIn("--child-", out)
        record, _ = self.resolved("--seat", "scout")
        self.assertEqual((record["transport"], record["transport_rule"], record["model"]),
                         ("direct", "default-native-unmapped-direct", "gpt-6-luna"))

    def test_sol_opt_in_reuses_the_one_snapshot_without_more_preparation(self):
        self.write_auth(".codex2", 100)
        env = self.env | {"PROBE_HOME": str(self.home / ".codex2")}
        result = self.dispatch("--seat", "maker", "--class", "correction", "--basis", "frame.md",
                               "--native-child-route", "luna-max", "--native-child-max-starts", "3",
                               env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.counter(), "1", "exactly one rotation step")
        servers = self.calls_of("codex")
        self.assertEqual(len(servers), 1, "one renewal for the one grant")
        self.assertTrue(servers[0]["home"].endswith("/.codex2"))
        (call,) = self.calls_of("native-call")
        attempt, state = self.attempt()
        out = str(attempt / "native")
        self.assertEqual(call["args"], [
            "--route", "sol-high", "--prompt-file", str(attempt / "prompt.md"), "--cwd", str(self.cwd),
            "--out", out, "--trusted-task", "--deadline", "7200",
            "--child-route", "luna-max", "--child-max-starts", "3",
            "--credential-codex-profile", str(attempt / "native-credential"),
            "--credential-margin", str(NEED - 7200 - 150)])
        self.assertIsNone(call["child_snapshot"])
        self.assertEqual(set(call["snapshot"]["tokens"]), {"access_token", "account_id"})
        self.assertEqual((call["lease_held"], call["lease_inherited"]), (False, False))
        self.assertFalse((attempt / "native-child-credential").exists())
        self.assertFalse((attempt / "native-credential").exists())
        for profile in (".codex", ".codex3", ".codex4", ".codex5"):
            self.assertFalse((self.home / profile / LEASE).exists(), profile)
        self.assertEqual((state["native_child_routes"], state["native_child_max_starts"],
                          state["renewal"], state["credential_snapshot_removed"],
                          state["native_child_accepted"], state["native_child_results"],
                          state["dispatcher_exit"]),
                         ("luna-max", "3", "renewed", "yes", "1", "0", "0"))
        self.assertIn("reuses the parent's one", state["native_child_grant"])
        self.assertIn("zero exports is not zero local results", state["native_children_note"])
        self.assertNotIn("native_child_max_concurrent", state)
        self.assertNotIn("child_grant_profile", state)
        route = json.loads((attempt / "route.json").read_text())
        self.assertEqual((route["native_children"]["routes"], route["native_children"]["max_starts"],
                          route["native_children"]["max_concurrent"], route["native_credential"]),
                         (["luna-max"], 3, None, "codex-access-snapshot"))

    def test_claude_opt_in_takes_one_separate_grant_and_no_children_takes_none(self):
        self.write_auth(".codex2", 100)
        env = self.env | {"PROBE_HOME": str(self.home / ".codex2")}
        # Without children: nothing prepared (the existing no-credential contract).
        result = self.claude_native("--seat", "decider", env=env, runs=self.root / "plain")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(self.counter())
        self.assertEqual(self.calls_of("codex"), [])
        (plain,) = self.calls_of("native-call")
        self.assertFalse(any(arg.startswith("--child") or arg.startswith("--credential")
                             for arg in plain["args"]))
        self.calls.unlink()
        # Opted in: one rotated Codex profile, one renewal, one access-only child grant.
        runs = self.root / "opted"
        result = self.claude_native("--seat", "maker", "--kind", "creative",
                                    "--native-child-route", "luna-max",
                                    "--native-child-max-concurrent", "1", env=env, runs=runs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.counter(), "1")
        (server,) = self.calls_of("codex")
        self.assertTrue(server["home"].endswith("/.codex2"))
        self.assertEqual((server["lease_held"], server["lease_inherited"]), (True, False))
        (call,) = self.calls_of("native-call")
        (attempt,) = runs.iterdir()
        self.assertEqual(call["args"], [
            "--route", "opus-high", "--prompt-file", str(attempt / "prompt.md"), "--cwd", str(self.cwd),
            "--out", str(attempt / "native"), "--trusted-task", "--deadline", "7200",
            "--child-route", "luna-max", "--child-max-concurrent", "1",
            "--child-credential-codex-profile", str(attempt / "native-child-credential"),
            "--credential-margin", str(NEED - 7200 - 150)])
        self.assertIsNone(call["snapshot"], "the Claude parent gets no credential")
        self.assertEqual(set(call["child_snapshot"]["tokens"]), {"access_token", "account_id"})
        self.assertTrue(call["child_snapshot"]["tokens"]["access_token"].endswith(".NEW-ACCESS"))
        self.assertEqual(call["snapshot_mode"], "0o600")
        self.assertEqual((call["lease_held"], call["lease_inherited"]), (False, False))
        self.assertFalse((attempt / "native-child-credential").exists())
        state = dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())
        self.assertEqual((state["profile"], state["credential"], state["profile_lease"],
                          state["child_grant_profile"], state["child_grant_profile_source"],
                          state["lease_scope"], state["lease_status"], state["renewal"],
                          state["credential_snapshot_removed"], state["dispatcher_exit"]),
                         ("claude5", "none", "none", ".codex2", "rotation:0", "child grant profile",
                          "acquired", "renewed", "yes", "0"))
        self.assertIn("never the Claude store's login", state["native_child_grant"])
        route = json.loads((attempt / "route.json").read_text())
        self.assertEqual((route["profile"], route["native_credential"], route["child_profile"]),
                         ("claude5", "none", ".codex2"))
        # The original store was never read (it is unreadable) and no other profile was leased.
        self.assertEqual(stat.S_IMODE((self.home / ".claude5").stat().st_mode), 0)
        for profile in (".codex", ".codex3", ".codex4", ".codex5"):
            self.assertFalse((self.home / profile / LEASE).exists(), profile)

    def test_claude_child_grant_refusals_and_failures_clean_up_without_replay(self):
        env = self.env | {"PROBE_HOME": str(self.home / ".codex2")}
        opt = ("--seat", "framer", "--native-child-route", "luna-max")
        # No admissible token on the rotated profile: 70, no caller.
        self.write_auth(".codex2", 0, tokens={"access_token": "not-a-jwt"})
        result = self.claude_native(*opt, env=env, runs=self.root / "no-token")
        self.assertEqual(result.returncode, 70, result.stdout + result.stderr)
        self.assertEqual(self.calls_of("native-call"), [])
        (attempt,) = (self.root / "no-token").iterdir()
        self.assertFalse((attempt / "native-child-credential").exists())
        # Lease busy for the bound on the next rotated profile (.codex3): 75, no caller.
        lease = os.open(self.home / ".codex3" / LEASE, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, lease)
        fcntl.flock(lease, fcntl.LOCK_EX)
        result = self.claude_native(*opt, env=env, runs=self.root / "busy",
                                    config=self.write_config(wait_s=1))
        self.assertEqual(result.returncode, 75, result.stdout + result.stderr)
        self.assertEqual(self.calls_of("native-call"), [])
        fcntl.flock(lease, fcntl.LOCK_UN)
        # Caller incomplete after launch (.codex4): its code, snapshot removed, never replayed.
        result = self.claude_native(*opt, env=env | {"FAKE_CALLER": "partial"}, runs=self.root / "partial")
        self.assertEqual(result.returncode, 6, result.stdout + result.stderr)
        self.assertEqual(len(self.calls_of("native-call")), 1)
        (attempt,) = (self.root / "partial").iterdir()
        state = dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())
        self.assertEqual((state["child_grant_profile"], state["native_caller_exit"],
                          state["native_class"], state["credential_snapshot_removed"]),
                         (".codex4", "6", "unknown", "yes"))
        self.assertFalse((attempt / "native-child-credential").exists())
        # A signal at caller start is forwarded and collected; the grant is still removed.
        sig = signal.SIGTERM
        result = self.claude_native(*opt, env=env | {"CONTROL_MODE": "caller-start-signal",
                                                     "FAKE_SIGNAL": str(int(sig))},
                                    runs=self.root / "signal")
        self.assertEqual(result.returncode, 128 + sig, result.stdout + result.stderr)
        (attempt,) = (self.root / "signal").iterdir()
        state = dict(line.split("=", 1) for line in (attempt / "state.txt").read_text().splitlines())
        self.assertEqual((state["child_grant_profile"], state["credential_snapshot_removed"]),
                         (".codex5", "yes"))
        self.assertNotEqual(state["native_caller_exit"], "none")
        self.assertFalse((attempt / "native-child-credential").exists())
        self.assertEqual(self.counter(), "4", "one rotation step per opted-in attempt")
        self.assertFalse(Path(str(self.calls) + ".claude5").exists(), "no direct fallback")

    def test_invalid_or_direct_native_only_requests_are_refused_before_any_effect(self):
        # Executables that would record any launch; nothing may run.
        huge = "9" * 30
        cases = [
            (("--native-deadline", "7201"), "at most 7200"),
            (("--native-deadline", huge), "at most 7200"),
            (("--native-deadline", "0", "--seat", "scout"), "positive number of seconds"),
            (("--native-deadline", "9" * 5000), "invalid int value"),
            (("--native-child-max-starts", "2"), "need --native-child-route"),
            (("--native-child-route", "luna-max", "--native-child-route", "luna-max"), "distinct"),
            (("--native-child-route", "other"), "not declared as offered by site route sol-high"),
            (("--seat", "framer", "--native-child-route", "luna-max",
              "--native-child-max-starts", "5"), "max-starts must be 1..4"),
            (("--native-child-route", "luna-max", "--native-child-max-concurrent", "3"),
             "max-concurrent must be 1..2"),
            (("--native-child-route", "luna-max", "--native-child-max-starts", "0"),
             "max-starts must be 1..4"),
            (("--native-child-route", "luna-max", "--native-child-max-starts", huge),
             "max-starts must be 1..4"),
            (("--seat", "scout", "--native-child-route", "luna-max"), "applies only to a native launch"),
            (("--seat", "framer", "--transport", "direct", "--native-child-route", "luna-max"),
             "applies only to a native launch"),
            (("--seat", "observer", "--transport", "direct", "--native-child-route", "luna-max"),
             "applies only to a native launch"),
            (("--seat", "framer", "--effort", "low", "--override-reason", "unmapped",
              "--native-child-route", "luna-max"), "applies only to a native launch"),
            (("--seat", "scout", "--transport", "native", "--native-child-route", "luna-max"),
             "no native site route"),
        ]
        for extra, message in cases:
            for dry in ((), ("--dry-run",)):
                with self.subTest(extra=extra[:4], dry=dry):
                    result = self.claude_native(*dry, *extra)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn(message, result.stderr)
                    self.assertNotIn("DIRECT_CHILD_ROUTE", result.stdout)
                    self.no_effects()
        # A lower declared site bound is applied before effects as well.
        lower = self.write_config(max_deadline_s=3600, deadline_s=3600)
        result = self.dispatch("--native-deadline", "3601", config=lower)
        self.assertEqual(result.returncode, 2)
        self.assertIn("at most 3600", result.stderr)
        self.no_effects()
        record, _ = self.resolved("--native-deadline", "3600", config=lower)
        self.assertEqual(record["native_deadline_s"], 3600)
        for replace, message in (({"max_deadline_s": 7201}, "max_deadline_s must be 1..7200"),
                                 ({"max_deadline_s": 1800}, "deadline_s exceeds"),
                                 ({"max_starts": 5}, "children.max_starts must be 1..4")):
            with self.subTest(replace=replace):
                result = self.dispatch("--dry-run", config=self.write_config(**replace))
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
        result = self.dispatch("--dry-run", config=self.write_config(
            raw=[('site_route = "sol-high"\nchildren = ["luna-max"]',
                  'site_route = "sol-high"\nchildren = ["undeclared"]')]))
        self.assertEqual(result.returncode, 2)
        self.assertIn("must list distinct [native.children] routes", result.stderr)
        self.no_effects()

    # ----------------------------------------------------------------- lease

    def test_our_direct_and_native_writers_exclude_each_other_on_one_profile(self):
        config = self.write_config(wait_s=1)
        lease = os.open(self.home / ".codex2" / LEASE, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, lease)
        fcntl.flock(lease, fcntl.LOCK_EX)
        native = self.dispatch("--transport", "native", "--profile", ".codex2",
                               "--override-reason", "contended profile", config=config)
        self.assertEqual(native.returncode, 75, native.stdout + native.stderr)
        attempt, state = self.attempt()
        self.assertEqual((state["lease_status"], state["dispatcher_exit"]), ("timeout", "75"))
        self.assertFalse((attempt / "renewal.json").exists())
        direct = self.dispatch("--transport", "direct", "--profile", ".codex2", "--override-reason", "contended profile",
                               config=config)
        self.assertEqual(direct.returncode, 75, direct.stdout + direct.stderr)
        self.assertIn("lease", direct.stderr)
        self.assertEqual(self.calls_of("codex") + self.calls_of("native-call"), [])
        fcntl.flock(lease, fcntl.LOCK_UN)
        direct = self.dispatch("--transport", "direct", "--profile", ".codex2", "--override-reason", "free profile",
                               config=config)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        (task,) = self.calls_of("codex")
        self.assertEqual((task["lease_held"], task["lease_inherited"]), (True, False),
                         "the direct task runs under the lease without inheriting it")


if __name__ == "__main__":
    unittest.main()
