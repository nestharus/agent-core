"""Native transport, gated official renewal and profile lease, with a fake Codex
CLI (including a fake stdio app-server) and a fake native caller. No real CLI,
profile, issuer or model is reached."""

import base64
import fcntl
import json
import os
from pathlib import Path
import re
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
import base64, fcntl, json, os, signal, sys, time, tomllib
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
note(**lease_probe(home))
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
        if mode in ("renew", "insufficient") and message.get("params") == {"refreshToken": True}:
            lifetime = int(os.environ.get("FAKE_NEW_LIFETIME", "864000"))
            payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + lifetime}).encode()).decode().rstrip("=")
            auth = json.load(open(home / "auth.json"))
            auth["tokens"]["access_token"] = "hdr." + payload + ".NEW-ACCESS"
            auth["tokens"]["refresh_token"] = "SECRET-REFRESH-2"
            auth["last_refresh"] = "2026-10-04T00:00:00Z"
            open(home / "auth.json", "w").write(json.dumps(auth))
        send({"id": message["id"], "result": {
            "account": {"type": "chatgpt", "email": "person@example.com", "planType": "pro"},
            "requiresOpenaiAuth": True}})
'''

FAKE_CALLER = r'''#!/usr/bin/env python3
import fcntl, json, os, sys
''' + LEASE_PROBE + r'''
args = sys.argv[1:]
value = lambda flag: args[args.index(flag) + 1]
credential = os.path.join(value("--credential-codex-profile"), "auth.json")
snapshot = json.load(open(credential))
mode_bits = oct(os.stat(credential).st_mode & 0o777)
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"tool": "native-call", "args": args, "snapshot": snapshot,
                            "snapshot_mode": mode_bits, **lease_probe(os.environ["PROBE_HOME"])}) + "\n")
mode = os.environ.get("FAKE_CALLER", "answered")
out = value("--out")
os.mkdir(out, 0o700)
if mode == "partial":
    sys.exit(6)
answered = mode == "answered"
json.dump({"class": "answered" if answered else "front-door-refused",
           "front_door_exit": 0 if answered else 90,
           "answer": {"present": answered}, "counts": {"bash_accepted": 2, "bash_ended": 2},
           "processing_completion": "not-observed"}, open(os.path.join(out, "result.json"), "w"))
if answered:
    open(os.path.join(out, "final.md"), "w").write("final: " + open(value("--prompt-file")).read())
sys.exit(0 if answered else 4)
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

    def write_config(self, **replace):
        text = CONFIG.read_text(encoding="utf-8")
        text = re.sub(r'(?m)^caller = ".*"$', f'caller = "{self.bin / "native-call"}"', text)
        for key, value in replace.items():
            text, count = re.subn(rf'(?m)^{key} = .*$', f"{key} = {value}", text)
            self.assertEqual(count, 1, key)
        path = self.root / f"routes-{len(list(self.root.glob('routes-*')))}.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def dispatch(self, *extra, env=None, config=None, timeout=60, runs=None):
        return subprocess.run(
            [str(DISPATCH), "--config", config or self.config, "--cwd", str(self.cwd),
             "--prompt", str(self.prompt), "--runs-dir", str(runs or self.runs), "--id", "child",
             *extra],
            env=env or self.env, capture_output=True, text=True, check=False, timeout=timeout)

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
        return self.dispatch("--transport", "native", "--profile", ".codex4",
                             "--override-reason", "fixed profile for the control", *extra,
                             env=env, config=config, timeout=timeout, runs=runs)

    # ------------------------------------------------------------ selection

    def test_default_stays_direct_and_native_is_an_explicit_opt_in(self):
        record, _ = self.resolved()
        self.assertEqual((record["transport"], record["transport_rule"], record["site_route"]),
                         ("direct", "default-direct", None))
        record, out = self.resolved("--transport", "native")
        self.assertEqual((record["transport"], record["transport_rule"], record["site_route"],
                          record["model"], record["effort"], record["native_deadline_s"]),
                         ("native", "explicit-native", "sol-high", "gpt-6.1-sol", "high", 7200))
        command = next(l for l in out.splitlines() if l.startswith("DRY RUN: would run: "))
        self.assertIn(f"{self.bin / 'native-call'} --route sol-high", command)
        self.assertIn("--trusted-task --deadline 7200", command)
        self.assertIn(f"--credential-margin {NEED - 7200 - 150}", command)
        self.assertNotIn("--model", command)
        self.assertIn(f"must cover {NEED}s", out)
        record, _ = self.resolved("--transport", "native", "--native-deadline", "1800")
        self.assertEqual(record["native_deadline_s"], 1800)
        self.assertFalse(self.runs.exists() or self.calls.exists())

    def test_explicit_native_without_a_declared_site_route_is_refused_before_effects(self):
        for extra in (("--seat", "scout"),
                      ("--seat", "framer"),
                      ("--seat", "maker", "--kind", "creative"),
                      ("--model", "gpt-xhigh", "--override-reason", "CRW opaque alias"),
                      ("--effort", "medium", "--override-reason", "cheaper")):
            with self.subTest(extra=extra):
                result = self.dispatch("--transport", "native", *extra)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("no native site route", result.stderr)
        result = self.dispatch("--native-deadline", "60")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.runs.exists() or self.calls.exists())

    def test_default_native_runs_unmapped_bindings_direct_by_rule_with_identity_kept(self):
        config = self.write_config(default='"native"')
        for extra, expected in (((), ("native", "default-native", "codex", "gpt-6.1-sol", "high")),
                                (("--seat", "scout"), ("direct", "default-native-unmapped-direct",
                                                       "codex", "gpt-6-luna", "max")),
                                (("--model", "gpt-xhigh", "--override-reason", "CRW"),
                                 ("direct", "default-native-unmapped-direct", "codex", "gpt-6.1-sol", "xhigh")),
                                (("--seat", "maker", "--kind", "creative"),
                                 ("direct", "default-native-unmapped-direct", "claude", "claude-opus-5-5", "high")),
                                (("--transport", "direct"), ("direct", "explicit-direct", "codex",
                                                             "gpt-6.1-sol", "high"))):
            with self.subTest(extra=extra):
                record, _ = self.resolved(*extra, config=config)
                self.assertEqual((record["transport"], record["transport_rule"], record["provider"],
                                  record["model"], record["effort"]), expected)
        result = self.dispatch("--seat", "scout", config=config)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls_of("codex")), 1)
        self.assertEqual(self.calls_of("native-call"), [])

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
                         ("helper-timeout", "unknown", "none", "killed"))
        self.assertEqual(self.calls_of("native-call"), [])

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
        direct = self.dispatch("--profile", ".codex2", "--override-reason", "contended profile",
                               config=config)
        self.assertEqual(direct.returncode, 75, direct.stdout + direct.stderr)
        self.assertIn("lease", direct.stderr)
        self.assertEqual(self.calls_of("codex") + self.calls_of("native-call"), [])
        fcntl.flock(lease, fcntl.LOCK_UN)
        direct = self.dispatch("--profile", ".codex2", "--override-reason", "free profile",
                               config=config)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        (task,) = self.calls_of("codex")
        self.assertEqual((task["lease_held"], task["lease_inherited"]), (True, False),
                         "the direct task runs under the lease without inheriting it")


if __name__ == "__main__":
    unittest.main()
