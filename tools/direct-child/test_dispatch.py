"""Process-level dispatcher tests with fake Codex and Claude CLIs; no model is contacted."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


DISPATCH = Path(__file__).with_name("dispatch.py")
CONFIG = Path(__file__).with_name("routes.toml")
FAKE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys, tomllib
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"tool": "codex", "args": args, "home": os.environ["CODEX_HOME"],
                            "cwd": os.getcwd()}) + "\n")
if args[-3:] == ["mcp", "list", "--json"]:
    with open(Path(os.environ["CODEX_HOME"]) / "config.toml", "rb") as config_file:
        names = list(tomllib.load(config_file).get("mcp_servers", {}))
    if any("openaiDeveloperDocs.url" in arg for arg in args):
        names.append("openaiDeveloperDocs")
    print(json.dumps([{"name": name, "enabled": f"mcp_servers.{name}.enabled=false" not in args
                       or name == os.environ.get("FAKE_FORCE_ENABLED")} for name in names]))
    sys.exit(0)
prompt = sys.stdin.read()
Path(args[args.index("-o") + 1]).write_text("final: " + prompt, encoding="utf-8")
print("live: " + prompt.strip())
'''
FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
prompt = sys.stdin.read()
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"tool": os.path.basename(sys.argv[0]), "args": args,
                            "cwd": os.getcwd(), "prompt": prompt}) + "\n")
mode = os.environ.get("FAKE_CLAUDE_MODE", "success")
print(json.dumps({"type": "system", "subtype": "init", "mcp_servers": []}))
print("not json noise")
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}))
print("claude warning", file=sys.stderr)
if mode == "success":
    print(json.dumps({"type": "result", "is_error": False, "result": "done: " + prompt}))
elif mode == "error":
    print(json.dumps({"type": "result", "is_error": True, "result": "API refused"}))
elif mode == "exit5":
    sys.exit(5)
'''
RUN_ARGS = ("--runs-dir", "--id")


class DispatchTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home, self.bin = self.root / "home", self.root / "bin"
        self.cwd = self.root / "work tree $(touch pwned) 'q'"
        self.prompt = self.root / "prompt; rm -rf x.md"
        self.runs = self.root / "runs"
        self.calls = self.root / "calls.jsonl"
        for directory in (self.home, self.bin, self.cwd):
            directory.mkdir()
        self.prompt.write_text("Do the bounded task.\n", encoding="utf-8")
        for name, body in (("codex", FAKE_CODEX), ("claude5", FAKE_CLAUDE)):
            (self.bin / name).write_text(body, encoding="utf-8")
            (self.bin / name).chmod(0o755)
        for profile in (".codex", ".codex2", ".codex3", ".codex4", ".codex5"):
            (self.home / profile).mkdir()
            (self.home / profile / "config.toml").write_text(
                "[mcp_servers.firecrawl]\nenabled = true\n", encoding="utf-8")
        self.state_dir = self.home / ".local" / "state" / "direct-child"
        self.env = os.environ | {"HOME": str(self.home), "FAKE_CALLS": str(self.calls),
                                 # Never reach real codex or claude wrappers.
                                 "PATH": os.pathsep.join((str(self.bin), "/usr/bin", "/bin"))}

    def dispatch(self, *extra, env=None):
        return subprocess.run(
            [str(DISPATCH), "--cwd", str(self.cwd), "--prompt", str(self.prompt),
             "--runs-dir", str(self.runs), "--id", "child", *extra],
            env=env or self.env, capture_output=True, text=True, check=False)

    def resolved(self, *extra):
        result = self.dispatch("--dry-run", *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith("DRY RUN: {"))
        return json.loads(line.removeprefix("DRY RUN: "))

    def assert_no_effects(self):
        self.assertFalse(self.runs.exists())
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.state_dir.exists())

    def calls_readback(self):
        return [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()]

    def write_config(self, text):
        path = self.root / "routes.toml"
        path.write_text(text, encoding="utf-8")
        return str(path)

    # ------------------------------------------------------------ resolution

    def test_same_maker_takes_different_model_by_class(self):
        expected = {
            ("--class", "new-foundation", "--basis", "facts.md#L3"):
                ("direction", "claude", "claude-opus-5-5", "medium", "seat-class:maker/new-foundation"),
            ("--class", "correction", "--basis", "review.md#F2"):
                ("refine", "codex", "gpt-6.1-sol", "high", "seat-class:maker/correction"),
            ("--class", "unknown"):
                ("direction", "claude", "claude-opus-5-5", "medium", "seat-class:maker/unknown"),
            ():
                ("direction", "claude", "claude-opus-5-5", "medium", "seat-class:maker/unknown"),
        }
        for extra, (route, provider, model, effort, rule) in expected.items():
            with self.subTest(extra=extra):
                record = self.resolved("--seat", "maker", "--pass", "corrective", *extra)
                self.assertEqual((record["route"], record["provider"], record["model"],
                                  record["effort"], record["rule"]),
                                 (route, provider, model, effort, rule))
                self.assertEqual(record["pass"], "corrective")
        self.assert_no_effects()

    def test_seat_class_legacy_and_explicit_precedence(self):
        framer = self.resolved("--seat", "framer", "--class", "correction", "--basis", "b")
        self.assertEqual((framer["route"], framer["rule"]), ("direction", "seat:framer"))
        scout = self.resolved("--seat", "scout", "--class", "new-foundation", "--basis", "b")
        self.assertEqual((scout["model"], scout["effort"]), ("gpt-6-luna", "max"))
        by_class = self.resolved("--class", "correction", "--basis", "b")
        self.assertEqual((by_class["route"], by_class["rule"]), ("refine", "class:correction"))
        unknown = self.resolved("--class", "unknown")
        self.assertEqual((unknown["route"], unknown["class_source"]), ("default", "supplied"))
        legacy = self.resolved()
        self.assertEqual((legacy["route"], legacy["rule"], legacy["class"], legacy["model"],
                          legacy["effort"]),
                         ("default", "legacy-unspecified", "unknown", "gpt-6.1-sol", "high"))
        explicit = self.resolved("--seat", "framer", "--route", "explore",
                                 "--override-reason", "cheap reread")
        self.assertEqual((explicit["route"], explicit["rule"], explicit["override_reason"]),
                         ("explore", "explicit-route", "cheap reread"))
        self.assert_no_effects()

    def test_class_evidence_and_unknown_names_are_refused(self):
        for extra, message in (
                (("--seat", "maker", "--class", "new-foundation"), "requires --basis"),
                (("--class", "correction", "--basis", "  "), "requires --basis"),
                (("--basis", "x"), "--basis needs --class"),
                (("--class", "novel"), "unknown class"),
                (("--seat", "reviewer"), "unknown seat"),
                (("--pass", "second"), "--pass must be"),
                (("--route", "direction"), "requires --override-reason"),
                (("--profile", ".codex2"), "requires --override-reason"),
                (("--override-reason", "x"), "without an override"),
                (("--seat", "maker", "--seat", "framer"), "duplicate --seat")):
            with self.subTest(extra=extra):
                result = self.dispatch(*extra)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
        self.assert_no_effects()

    def test_literal_aliases_native_models_and_effort_overrides(self):
        reason = ("--override-reason", "CRW contract names gpt-xhigh")
        xhigh = self.resolved("--model", "gpt-xhigh", *reason)
        self.assertEqual((xhigh["model"], xhigh["effort"], xhigh["model_alias"], xhigh["rule"]),
                         ("gpt-6.1-sol", "xhigh", "gpt-xhigh", "explicit-model"))
        gpt = self.resolved("--model", "gpt", *reason)
        self.assertEqual((gpt["model"], gpt["effort"]), ("gpt-6.1-sol", "high"))
        native = self.resolved("--model", "claude-sonnet-5-5", "--provider", "claude",
                               "--effort", "high", *reason)
        self.assertEqual((native["provider"], native["model"], native["effort"], native["profile"]),
                         ("claude", "claude-sonnet-5-5", "high", "claude5"))
        effort = self.resolved("--seat", "scout", "--effort", "low", *reason)
        self.assertEqual((effort["model"], effort["effort"], effort["overrides"]),
                         ("gpt-6-luna", "low", ["--effort"]))
        for extra, message in (
                (("--model", "gpt-6-luna", "--effort", "max"), "needs --provider and --effort"),
                (("--model", "gpt", "--provider", "codex"), "is an alias"),
                (("--route", "default", "--model", "gpt"), "not both"),
                (("--model", "claude-opus-5-5", "--provider", "claude", "--effort", "extreme"),
                 "not a configured claude effort"),
                (("--route", "direction", "--profile", ".codex"), "not a claude profile"),
                (("--profile", ".codex9"), "not a codex profile")):
            with self.subTest(extra=extra):
                result = self.dispatch(*extra, *reason)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
        self.assert_no_effects()

    def test_future_sonnet_binding_is_one_config_edit(self):
        text = CONFIG.read_text(encoding="utf-8").replace(
            '[routes.refine]\nprovider = "codex"\nmodel = "gpt-6.1-sol"\neffort = "high"',
            '[routes.refine]\nprovider = "claude"\nmodel = "claude-sonnet-5-5"\neffort = "high"')
        config = self.write_config(text)
        record = self.resolved("--config", config, "--seat", "maker",
                               "--class", "correction", "--basis", "b")
        self.assertEqual((record["route"], record["provider"], record["model"], record["effort"],
                          record["profile"]),
                         ("refine", "claude", "claude-sonnet-5-5", "high", "claude5"))
        self.assertEqual(record["config"], config)

    def test_malformed_config_refuses_before_effects(self):
        base = CONFIG.read_text(encoding="utf-8")
        mutations = {
            "unparseable": base + "\n[routes\n",
            "unknown route": base.replace('[seats.framer]\nroute = "direction"',
                                          '[seats.framer]\nroute = "nowhere"'),
            "bad effort": base.replace('effort = "max"', 'effort = "maximum"'),
            "incomplete by_class": base.replace('[seats.maker.by_class]\n', '[seats.maker.by_class]\n#', 1)
                                       .replace('#new-foundation = "direction"\n', ''),
            "unknown basis": base.replace('[classes.unknown]\nrequires_basis = false',
                                          '[classes.unknown]\nrequires_basis = true'),
            "pool outside manual": base.replace('pool = [".codex", ".codex3", ".codex4"]',
                                                'pool = [".codex", ".codex7"]'),
            "bad provider": base.replace('[routes.explore]\nprovider = "codex"',
                                         '[routes.explore]\nprovider = "gemini"'),
        }
        for name, text in mutations.items():
            with self.subTest(name=name):
                self.assertNotEqual(text, base)
                result = self.dispatch("--config", self.write_config(text), "--seat", "scout")
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("config", result.stderr)
        result = self.dispatch("--config", str(self.root / "missing.toml"))
        self.assertEqual(result.returncode, 2)
        self.assert_no_effects()

    # -------------------------------------------------------------- rotation

    def test_concurrent_rotation_is_atomic_and_fair_across_sol_and_luna(self):
        seats = [("--seat", "scout")] * 6 + [()] * 6
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda extra: self.dispatch(*extra), seats))
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads((attempt / "route.json").read_text())
                   for attempt in self.runs.iterdir()]
        self.assertEqual(sorted(r["profile_source"] for r in records),
                         sorted(f"rotation:{n}" for n in range(12)))
        for profile in (".codex", ".codex3", ".codex4"):
            self.assertEqual(sum(r["profile"] == profile for r in records), 4, profile)
        self.assertEqual({r["model"] for r in records}, {"gpt-6.1-sol", "gpt-6-luna"})
        for record in records:
            expected = {".codex": 0, ".codex3": 1, ".codex4": 2}[record["profile"]]
            self.assertEqual(int(record["profile_source"].split(":")[1]) % 3, expected)
        self.assertEqual((self.state_dir / "codex.counter").read_text(), "12\n")
        exec_homes = sorted(call["home"] for call in self.calls_readback() if call["args"][0] == "exec")
        self.assertEqual(exec_homes, sorted(str(self.home / r["profile"]) for r in records))

        dry = self.resolved()
        self.assertEqual((dry["profile"], dry["profile_source"]),
                         (".codex", "rotation-preview:12 (not reserved)"))
        explicit = self.dispatch("--profile", ".codex5", "--override-reason", "manual history")
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual((self.state_dir / "codex.counter").read_text(), "12\n")
        self.assertEqual(len(list(self.runs.iterdir())), 13)

    # ----------------------------------------------------------------- codex

    def test_codex_route_keeps_mcp_preflight_and_records_route(self):
        result = self.dispatch("--seat", "maker", "--class", "correction", "--basis", "F2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DIRECT_CODEX_EXIT=0", result.stdout)
        attempt = next(self.runs.iterdir())
        record = json.loads((attempt / "route.json").read_text())
        self.assertEqual((record["seat"], record["class"], record["basis"], record["rule"],
                          record["profile"]),
                         ("maker", "correction", "F2", "seat-class:maker/correction", ".codex"))
        state = (attempt / "state.txt").read_text()
        self.assertIn("profile=.codex\nmodel=gpt-6.1-sol\neffort=high\n", state)
        self.assertIn(f"cwd={self.cwd}\n", state)
        calls = self.calls_readback()
        self.assertEqual(len(calls), 3)
        exec_args = calls[-1]["args"]
        self.assertEqual(exec_args[exec_args.index("-m") + 1], "gpt-6.1-sol")
        self.assertIn('model_reasoning_effort="high"', exec_args)
        self.assertEqual(exec_args[exec_args.index("-C") + 1], str(self.cwd))
        for flag in ("mcp_servers.firecrawl.enabled=false",
                     "mcp_servers.openaiDeveloperDocs.enabled=false",
                     'mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"'):
            self.assertIn(flag, exec_args)
        self.assertFalse((self.root / "pwned").exists())

    def test_codex_enabled_mcp_refuses_launch(self):
        result = self.dispatch("--seat", "scout", env=self.env | {"FAKE_FORCE_ENABLED": "firecrawl"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("MCP preflight", result.stderr)
        self.assertFalse(self.runs.exists())
        self.assertFalse(any(call["args"][0] == "exec" for call in self.calls_readback()))

    # ---------------------------------------------------------------- claude

    def claude_attempt(self, mode):
        result = self.dispatch("--seat", "framer", env=self.env | {"FAKE_CLAUDE_MODE": mode})
        attempt = next(self.runs.iterdir())
        state = dict(line.split("=", 1) for line in
                     (attempt / "state.txt").read_text().splitlines())
        return result, attempt, state

    def test_claude_exact_wrapper_model_effort_and_empty_mcp(self):
        result, attempt, state = self.claude_attempt("success")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = self.calls_readback()[0]
        self.assertEqual(call["tool"], "claude5")
        self.assertEqual(call["args"], ["-p", "--model", "claude-opus-5-5", "--effort", "medium",
                                        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                                        "--settings", '{"autoMemoryEnabled":false}',
                                        "--no-session-persistence",
                                        "--output-format", "stream-json", "--verbose"])
        self.assertEqual((call["cwd"], call["prompt"]), (str(self.cwd), "Do the bounded task.\n"))
        self.assertEqual((attempt / "final.md").read_text(), "done: Do the bounded task.\n")
        log = (attempt / "log.txt").read_text()
        self.assertIn('"tool_use"', log)
        self.assertIn("not json noise", log)
        self.assertIn('"type": "result"', log)
        self.assertEqual((attempt / "stderr.txt").read_text(), "claude warning\n")
        self.assertEqual((state["claude_exit"], state["result_event"], state["semantic_is_error"],
                          state["final_status"], state["dispatcher_exit"], state["log_capture_exit"]),
                         ("0", "present", "false", "present", "0", "0"))
        self.assertEqual((state["seat"], state["rule"], state["profile"]),
                         ("framer", "seat:framer", "claude5"))
        self.assertEqual(json.loads((attempt / "route.json").read_text())["model"], "claude-opus-5-5")
        self.assertIn("DIRECT_CHILD_FINAL_BEGIN=", result.stdout)
        self.assertEqual(oct((attempt / "prompt.md").stat().st_mode & 0o777), "0o400")

    def test_claude_semantic_error_with_zero_exit_is_not_success(self):
        result, attempt, state = self.claude_attempt("error")
        self.assertEqual(result.returncode, 3)
        self.assertEqual((state["claude_exit"], state["semantic_is_error"], state["dispatcher_exit"]),
                         ("0", "true", "3"))
        self.assertEqual((attempt / "final.md").read_text(), "API refused")

    def test_claude_missing_result_stays_missing(self):
        result, attempt, state = self.claude_attempt("nofinal")
        self.assertEqual(result.returncode, 4)
        self.assertEqual((state["claude_exit"], state["result_event"], state["final_status"]),
                         ("0", "missing", "missing"))
        self.assertEqual((attempt / "final.md").read_text(), "")
        self.assertIn("DIRECT_CHILD_FINAL_MISSING_OR_EMPTY=", result.stdout)
        self.assertIn('"tool_use"', (attempt / "log.txt").read_text())

    def test_claude_native_exit_propagates_and_keeps_raw_output(self):
        result, attempt, state = self.claude_attempt("exit5")
        self.assertEqual(result.returncode, 5)
        self.assertEqual((state["claude_exit"], state["dispatcher_exit"]), ("5", "5"))
        self.assertIn("not json noise", (attempt / "log.txt").read_text())

    def test_missing_claude_wrapper_refuses_before_attempt(self):
        (self.bin / "claude5").unlink()
        result = self.dispatch("--seat", "decider")
        self.assertEqual(result.returncode, 2)
        self.assertIn("claude5", result.stderr)
        self.assertFalse(self.runs.exists())

    def test_dry_run_command_round_trips_hostile_paths(self):
        for extra in (("--seat", "decider"), ("--seat", "scout")):
            with self.subTest(extra=extra):
                result = self.dispatch("--dry-run", *extra)
                line = next(l for l in result.stdout.splitlines()
                            if l.startswith("DRY RUN: would run: "))
                argv = shlex.split(line.removeprefix("DRY RUN: would run: "))
                if extra[1] == "scout":
                    self.assertEqual(argv[argv.index("--cwd") + 1], str(self.cwd))
                    self.assertEqual(argv[argv.index("--prompt") + 1], str(self.prompt))
                else:
                    self.assertEqual(argv[argv.index("--mcp-config") + 1], '{"mcpServers":{}}')
        self.assert_no_effects()
        self.assertFalse((self.root / "pwned").exists())


if __name__ == "__main__":
    unittest.main()
