"""Safe process-level tests; the fake CLI never contacts Codex or MCP servers."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).with_name("launch.sh")
FAKE_CODEX = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
import tomllib

args = sys.argv[1:]
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"args": args, "home": os.environ["CODEX_HOME"],
                            "cwd": os.getcwd()}) + "\n")
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
if args[0] != "exec":
    sys.exit(91)
assert "--dangerously-bypass-approvals-and-sandbox" in args
assert args[args.index("-m") + 1] == "gpt-6-sol"
assert 'model_reasoning_effort="xhigh"' in args
assert args[args.index("-C") + 1] == os.environ["EXPECTED_CWD"]
assert args[-1] == "-"
prompt = sys.stdin.read()
Path(args[args.index("-o") + 1]).write_text("final: " + prompt, encoding="utf-8")
print("live: " + prompt.strip())
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

    def test_dry_run_is_no_op(self):
        result = self.run_launcher(".codex", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertFalse(self.runs.exists())
        self.assertFalse(self.calls.exists())

    def test_rejects_bad_arguments_before_any_effect(self):
        for profile, extra in ((".codex5", ()), (".codex", ("--unknown",)),
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
        calls = self.calls_readback()
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
        for call in self.calls_readback()[1:]:
            self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])
            self.assertIn('mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"', call["args"])

    def test_additional_configured_server_is_disabled(self):
        with (self.home / ".codex4" / "config.toml").open("a", encoding="utf-8") as config_file:
            config_file.write("[mcp_servers.extraServer]\nenabled = true\n")
        result = self.run_launcher(".codex4")
        self.assertEqual(result.returncode, 0, result.stderr)
        for call in self.calls_readback()[1:]:
            self.assertIn("mcp_servers.extraServer.enabled=false", call["args"])
            self.assertIn("mcp_servers.openaiDeveloperDocs.enabled=false", call["args"])

    def test_effective_server_absent_from_profile_config_is_disabled(self):
        env = self.env.copy()
        env["FAKE_INJECT_SERVER"] = "openaiDeveloperDocs"
        result = self.run_launcher(".codex2", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls_readback()
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


if __name__ == "__main__":
    unittest.main()
