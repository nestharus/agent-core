"""Safe process-level tests; the fake CLI never contacts Codex or MCP servers."""

import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


LAUNCHER = Path(__file__).with_name("launch.sh")
FAKE_CODEX = r'''#!/usr/bin/env python3
import fcntl
import json
import os
from pathlib import Path
import sys
import time
import tomllib

DEFAULT_FEATURES = ("agent_message_board:under development:false,collaboration_modes:removed:true,"
                    "goals:stable:true,multi_agent:stable:true,multi_agent_v2:stable:false")
args = sys.argv[1:]


def lease_probe():
    """Whether some open file holds the retired profile lease file, and whether
    this process inherited a descriptor for it."""
    path = os.path.join(os.environ["CODEX_HOME"], ".oulipoly-direct-child.lease")
    if not os.path.exists(path):
        return None, None
    inherited = any(os.path.realpath(f"/proc/self/fd/{fd}") == os.path.realpath(path)
                    for fd in os.listdir("/proc/self/fd") if os.path.exists(f"/proc/self/fd/{fd}"))
    probe = os.open(path, os.O_RDWR)
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return False, inherited
    except BlockingIOError:
        return True, inherited
    finally:
        os.close(probe)


held, inherited = lease_probe()
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"args": args, "home": os.environ["CODEX_HOME"],
                            "cwd": os.getcwd(), "lease_held": held,
                            "lease_inherited": inherited}) + "\n")
if args[-3:] == ["mcp", "list", "--json"]:
    with open(Path(os.environ["CODEX_HOME"]) / "config.toml", "rb") as config_file:
        servers = tomllib.load(config_file).get("mcp_servers", {})
    names = list(servers)
    injected = os.environ.get("FAKE_INJECT_SERVER")
    if injected:
        names.append(injected)
    if ("mcp_servers.openaiDeveloperDocs.url=\"https://developers.openai.com/mcp\"" in args
            and "openaiDeveloperDocs" not in names):
        names.append("openaiDeveloperDocs")
    if os.environ.get("FAKE_PREFLIGHT_EXTRA") and any(
        arg.endswith(".enabled=false") for arg in args
    ):
        names.append(os.environ["FAKE_PREFLIGHT_EXTRA"])
    rows = []
    for name in names:
        enabled = f"mcp_servers.{name}.enabled=false" not in args
        if name == os.environ.get("FAKE_FORCE_ENABLED"):
            enabled = True
        rows.append({"name": name, "enabled": enabled})
    print(json.dumps(rows))
    sys.exit(0)
if args[-2:] == ["features", "list"]:
    disabling = any(arg.startswith("features.") and arg.endswith("=false") for arg in args)
    if os.environ.get("FAKE_FEATURES_FAIL") or (disabling and os.environ.get("FAKE_READBACK_FAIL")):
        sys.exit(1)
    if disabling and "FAKE_READBACK_TEXT" in os.environ:
        print(os.environ["FAKE_READBACK_TEXT"])
        sys.exit(0)
    for item in filter(None, os.environ.get("FAKE_FEATURES", DEFAULT_FEATURES).split(",")):
        name, stage, state = item.split(":")
        if f"features.{name}=false" in args and name != os.environ.get("FAKE_STUCK"):
            state = "false"
        print(f"{name:<40} {stage:<18} {state}")
    sys.exit(0)
if args[0] != "exec":
    sys.exit(91)
assert "--dangerously-bypass-approvals-and-sandbox" in args
assert args[args.index("-m") + 1] == os.environ.get("EXPECTED_MODEL", "gpt-6.1-sol")
assert f'model_reasoning_effort="{os.environ.get("EXPECTED_EFFORT", "high")}"' in args
assert args[args.index("-C") + 1] == os.environ["EXPECTED_CWD"]
assert args[-1] == "-"
prompt = sys.stdin.read()
if os.environ.get("FAKE_RELEASE"):
    # Hold this task open until the test releases it, so other launches on the
    # same profile are observed while it runs.
    Path(os.environ["FAKE_STARTED_DIR"], str(os.getpid())).touch()
    deadline = time.monotonic() + 30
    while not os.path.exists(os.environ["FAKE_RELEASE"]) and time.monotonic() < deadline:
        time.sleep(0.05)
Path(args[args.index("-o") + 1]).write_text("final: " + prompt, encoding="utf-8")
print("live: " + prompt.strip())
for _ in range(int(os.environ.get("FAKE_COLLAB", "0"))):
    print("collab: Wait")
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
'''


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.cwd = self.root / "worktree"
        self.prompt = self.root / "source.md"
        self.runs = self.root / "runs"
        self.calls = self.root / "calls.jsonl"
        self.bin.mkdir()
        self.cwd.mkdir()
        self.home.mkdir()
        self.prompt.write_text("Do the bounded task.\n", encoding="utf-8")
        fake = self.bin / "codex"
        fake.write_text(FAKE_CODEX, encoding="utf-8")
        fake.chmod(0o755)
        for profile, servers in {
            ".codex": ("firecrawl", "openaiDeveloperDocs"),
            ".codex2": ("firecrawl",),
            ".codex3": ("firecrawl",),
            ".codex4": ("firecrawl",),
            ".codex5": ("firecrawl",),
        }.items():
            directory = self.home / profile
            directory.mkdir()
            (directory / "config.toml").write_text(
                "".join(f"[mcp_servers.{server}]\nenabled = true\n" for server in servers),
                encoding="utf-8",
            )
        self.env = os.environ.copy()
        self.env.update({
            "HOME": str(self.home), "PATH": str(self.bin) + os.pathsep + self.env["PATH"],
            "FAKE_CALLS": str(self.calls), "EXPECTED_CWD": str(self.cwd),
        })

    def run_launcher(self, profile=".codex", *extra, env=None):
        return subprocess.run(
            [str(LAUNCHER), "--profile", profile, "--cwd", str(self.cwd),
             "--prompt", str(self.prompt), "--runs-dir", str(self.runs),
             "--id", "child", *extra],
            env=env or self.env, capture_output=True, text=True, check=False,
        )

    def calls_readback(self):
        return [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()]

    def mcp_and_exec_calls(self):
        return [call for call in self.calls_readback() if call["args"][-2:] != ["features", "list"]]

    def exec_args(self):
        execs = [call["args"] for call in self.calls_readback() if call["args"][0] == "exec"]
        self.assertEqual(len(execs), 1)
        return execs[0]

    def test_dry_run_is_no_op(self):
        result = self.run_launcher(".codex", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertFalse(self.runs.exists())
        self.assertFalse(self.calls.exists())

    def test_rejects_bad_arguments_before_any_effect(self):
        for profile, extra in ((".codex6", ()), (".codex", ("--unknown",)),
                               (".codex", ("--id", "duplicate"))):
            with self.subTest(profile=profile, extra=extra):
                result = self.run_launcher(profile, *extra)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.runs.exists())
                self.assertFalse(self.calls.exists())
        self.prompt.unlink()
        result = self.run_launcher()
        self.assertEqual(result.returncode, 2)
        self.assertIn("prompt must be a readable nonempty file", result.stderr)
        self.assertFalse(self.calls.exists())

    def test_success_captures_unique_attempt_and_disables_all_servers(self):
        first = self.run_launcher()
        second = self.run_launcher()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        attempts = sorted(self.runs.iterdir())
        self.assertEqual(len(attempts), 2)
        for attempt in attempts:
            self.assertEqual((attempt / "prompt.md").read_text(), self.prompt.read_text())
            self.assertEqual((attempt / "final.md").read_text(), "final: Do the bounded task.\n")
            self.assertIn("live: Do the bounded task.", (attempt / "log.txt").read_text())
            self.assertIn("codex_exit=0", (attempt / "state.txt").read_text())
            self.assertIn("log_capture_exit=0", (attempt / "state.txt").read_text())
        self.assertIn("DIRECT_CODEX_FINAL_BEGIN=", first.stdout)
        self.assertEqual(len(self.calls_readback()), 10)
        calls = self.mcp_and_exec_calls()
        self.assertEqual(len(calls), 6)
        self.assertEqual([call["args"][-3:] for call in calls if call["args"][0] != "exec"],
                         [["mcp", "list", "--json"]] * 4)
        for call in calls:
            self.assertEqual(call["home"], str(self.home / ".codex"))
            if call["args"][0] == "exec" or "mcp_servers.firecrawl.enabled=false" in call["args"]:
                self.assertIn("mcp_servers.firecrawl.enabled=false", call["args"])
                self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])
        self.assertEqual([call["cwd"] for call in calls if call["args"][0] == "exec"],
                         [str(self.cwd)] * 2)

    def test_other_profile_propagates_exit(self):
        env = self.env.copy()
        env["FAKE_EXIT"] = "7"
        result = self.run_launcher(".codex2", env=env)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("DIRECT_CODEX_EXIT=7", result.stdout)
        self.assertIn("codex_exit=7", next(self.runs.iterdir()).joinpath("state.txt").read_text())
        for call in self.mcp_and_exec_calls()[1:]:
            self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])
            self.assertIn('mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"', call["args"])
        self.exec_args()  # a failed task is never replayed

    def test_codex5_profile_launches_with_mcp_disabled(self):
        result = self.run_launcher(".codex5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DIRECT_CODEX_EXIT=0", result.stdout)
        self.assertTrue(all(call["home"] == str(self.home / ".codex5")
                            for call in self.calls_readback()))
        calls = self.mcp_and_exec_calls()
        self.assertEqual(len(calls), 3)
        for call in calls[1:]:
            self.assertIn("mcp_servers.firecrawl.enabled=false", call["args"])
            self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])

    def test_explicit_model_effort_and_route_record(self):
        env = self.env.copy()
        env.update({"EXPECTED_MODEL": "gpt-6-luna", "EXPECTED_EFFORT": "max"})
        result = self.run_launcher(".codex3", "--model", "gpt-6-luna", "--effort", "max",
                                   "--route-json", '{"rule": "seat:scout"}', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = next(self.runs.iterdir())
        state = (attempt / "state.txt").read_text()
        self.assertIn("model=gpt-6-luna\neffort=max\n", state)
        self.assertEqual((attempt / "route.json").read_text(), '{"rule": "seat:scout"}\n')
        self.assertIn("mcp_servers.firecrawl.enabled=false", self.calls_readback()[-1]["args"])

    def test_model_without_effort_is_refused(self):
        for extra in (("--model", "gpt-6-luna"), ("--effort", "max"),
                      ("--model", "bad model", "--effort", "high")):
            with self.subTest(extra=extra):
                result = self.run_launcher(".codex", *extra)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.calls.exists())

    def test_additional_configured_server_is_disabled(self):
        with (self.home / ".codex4" / "config.toml").open("a", encoding="utf-8") as config_file:
            config_file.write("[mcp_servers.extraServer]\nenabled = true\n")
        result = self.run_launcher(".codex4")
        self.assertEqual(result.returncode, 0, result.stderr)
        for call in self.mcp_and_exec_calls()[1:]:
            self.assertIn("mcp_servers.extraServer.enabled=false", call["args"])
            self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])

    def test_effective_server_absent_from_profile_config_is_disabled(self):
        env = self.env.copy()
        env["FAKE_INJECT_SERVER"] = "openaiDeveloperDocs"
        result = self.run_launcher(".codex2", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.mcp_and_exec_calls()
        self.assertEqual(len(calls), 3)
        self.assertNotIn("mcp_servers.openaiDeveloperDocs.enabled=false", calls[0]["args"])
        for call in calls[1:]:
            self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])
            self.assertIn('mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"', call["args"])

    def test_preflight_only_checks_effective_state_without_attempt(self):
        env = self.env.copy()
        env["FAKE_INJECT_SERVER"] = "openaiDeveloperDocs"
        result = self.run_launcher(".codex2", "--preflight-only", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("count=2", result.stdout)
        self.assertFalse(self.runs.exists())
        self.assertEqual(len(self.calls_readback()), 2)

    def test_unexpected_server_in_preflight_refuses_exec(self):
        env = self.env.copy()
        env["FAKE_PREFLIGHT_EXTRA"] = "surprise"
        result = self.run_launcher(env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("MCP preflight", result.stderr)
        self.assertFalse(self.runs.exists())
        self.assertEqual(len(self.calls_readback()), 2)

    def test_enabled_mcp_refuses_exec_and_creates_no_attempt(self):
        env = self.env.copy()
        env["FAKE_FORCE_ENABLED"] = "firecrawl"
        result = self.run_launcher(env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("MCP preflight", result.stderr)
        self.assertFalse(self.runs.exists())
        self.assertEqual(len(self.calls_readback()), 2)

    def state(self):
        return next(self.runs.iterdir()).joinpath("state.txt").read_text()

    def test_feature_readback_does_not_claim_model_facing_absence(self):
        result = self.run_launcher(".codex3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DELEGATION_CAPABILITY=not-established", result.stdout)
        args = self.exec_args()
        for name in ("multi_agent", "multi_agent_v2", "agent_message_board", "collaboration_modes"):
            self.assertIn(f"features.{name}=false", args)
        self.assertNotIn("features.goals=false", args)
        self.assertNotIn("--disable", args)
        state = self.state()
        self.assertIn("delegation_capability=not-established\n", state)
        self.assertIn("delegation_feature_readback=all-listed-false\n", state)
        self.assertIn("model-facing delegation capability not established", state)
        self.assertIn("delegation_features_listed=", state)
        self.assertIn("delegation_restriction_args=-c features.", state)
        self.assertIn("delegation_features=agent_message_board=false,collaboration_modes=false,"
                      "multi_agent=false,multi_agent_v2=false\n", state)
        self.assertIn("delegation_scope=", state)
        self.assertIn("log_collab_lines=0\n", state)

    def test_renamed_feature_restriction_is_requested_without_a_version_check(self):
        env = self.env.copy()
        env["FAKE_FEATURES"] = "multi_agent_v3:stable:true,subagents:experimental:true,goals:stable:true"
        result = self.run_launcher(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.exec_args()
        self.assertIn("features.multi_agent_v3=false", args)
        self.assertIn("features.subagents=false", args)
        self.assertNotIn("features.multi_agent=false", args)
        self.assertIn("delegation_capability=not-established\n", self.state())
        self.assertIn("delegation_feature_readback=all-listed-false\n", self.state())

    def test_unestablished_capability_still_launches_once_and_says_so(self):
        cases = (
            ("FAKE_FEATURES_FAIL", "1", "feature listing unavailable or unparsed", False),
            ("FAKE_READBACK_FAIL", "1",
             "feature readback with disable flags failed; flags not passed", False),
            ("FAKE_STUCK", "multi_agent",
             "feature readback incomplete or still enabled; model-facing delegation capability not established", True),
            ("FAKE_FEATURES", "goals:stable:true", "no delegation-like feature listed", False),
        )
        for number, (variable, value, note, flags_passed) in enumerate(cases):
            with self.subTest(variable=variable):
                self.runs = self.root / f"runs{number}"
                self.calls.unlink(missing_ok=True)
                env = self.env.copy()
                env[variable] = value
                result = self.run_launcher(env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("DELEGATION_CAPABILITY=not-established", result.stdout)
                state = self.state()
                self.assertIn("delegation_capability=not-established\n", state)
                self.assertIn(f"delegation_capability_note={note}\n", state)
                passed = any(arg.startswith("features.") for arg in self.exec_args())
                self.assertEqual(passed, flags_passed)

    def test_partial_or_duplicate_readback_does_not_claim_complete_metadata(self):
        for number, readback in enumerate((
                "multi_agent stable false",
                "multi_agent stable true\nmulti_agent stable false")):
            with self.subTest(readback=readback):
                self.runs = self.root / f"partial{number}"
                self.calls.unlink(missing_ok=True)
                result = self.run_launcher(env=self.env | {"FAKE_READBACK_TEXT": readback})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.exec_args()
                self.assertIn("delegation_capability=not-established\n", self.state())
                self.assertNotIn("delegation_feature_readback=all-listed-false", self.state())

    def test_launches_take_no_profile_lock_and_run_concurrently_on_one_profile(self):
        # A foreign holder of the retired lock file (e.g. a launcher from before
        # its removal) neither blocks nor is inherited by new launches.
        lease = self.home / ".codex2" / ".oulipoly-direct-child.lease"
        foreign = os.open(lease, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, foreign)
        fcntl.flock(foreign, fcntl.LOCK_EX)
        started, release = self.root / "started", self.root / "release"
        started.mkdir()
        env = self.env | {"FAKE_STARTED_DIR": str(started), "FAKE_RELEASE": str(release)}
        command = [str(LAUNCHER), "--profile", ".codex2", "--cwd", str(self.cwd),
                   "--prompt", str(self.prompt), "--runs-dir", str(self.runs), "--id", "child"]
        launches = [subprocess.Popen(command + extra, env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
                    for extra in ([], ["--lease-wait", "0.5"])]  # retired option, ignored
        try:
            deadline = time.monotonic() + 20
            while len(list(started.iterdir())) < 2 and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual(len(list(started.iterdir())), 2, "both tasks must run at once")
        finally:
            release.touch()
            results = [launch.communicate(timeout=60) for launch in launches]
        for launch, (out, err) in zip(launches, results):
            self.assertEqual(launch.returncode, 0, out + err)
        attempts = sorted(self.runs.iterdir())
        self.assertEqual(len(attempts), 2, "distinct attempts")
        for attempt in attempts:
            state = (attempt / "state.txt").read_text()
            self.assertIn("profile_lock=none\n", state)
            self.assertNotIn("lease", state)
            self.assertIn("codex_exit=0\n", state)
        calls = self.calls_readback()
        self.assertEqual(len(calls), 10)
        for call in calls:
            self.assertEqual((call["lease_held"], call["lease_inherited"]), (True, False), call["args"])
        # Another profile gains no lock file.
        self.assertEqual(self.run_launcher(".codex4").returncode, 0)
        self.assertFalse((self.home / ".codex4" / ".oulipoly-direct-child.lease").exists())

    def test_collab_lines_in_log_are_counted(self):
        env = self.env.copy()
        env["FAKE_COLLAB"] = "2"
        result = self.run_launcher(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("log_collab_lines=2\n", self.state())


if __name__ == "__main__":
    unittest.main()
