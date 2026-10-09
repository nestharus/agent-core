"""Process-level dispatcher tests with fake Codex and Claude CLIs; no model is contacted."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import sys
import unittest


DISPATCH = Path(__file__).with_name("dispatch.py")
CONFIG = Path(__file__).with_name("routes.toml")
# Stand-in for the installed native caller: these tests exercise direct CLI
# behaviour, so any native launch is recorded and fails instead of reaching
# the real front door.
FAKE_NATIVE_CALLER = r'''#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"tool": "native-call", "args": sys.argv[1:]}) + "\n")
sys.exit(99)
'''
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
if args[-2:] == ["features", "list"]:
    state = "false" if "features.multi_agent=false" in args else "true"
    print(f"goals    stable    true\nmulti_agent    stable    {state}")
    sys.exit(0)
prompt = sys.stdin.read()
Path(args[args.index("-o") + 1]).write_text("final: " + prompt, encoding="utf-8")
print("live: " + prompt.strip())
'''
FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, signal, sys
args = sys.argv[1:]
if "--help" in args:
    with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
        calls.write(json.dumps({"tool": os.path.basename(sys.argv[0]), "args": args,
                                "cwd": os.getcwd(), "home": os.environ["HOME"],
                                "claude_config": os.environ["CLAUDE_CONFIG_DIR"]}) + "\n")
    help_mode = os.environ.get("FAKE_CLAUDE_HELP", "supported")
    if help_mode in ("rejected-flag", "rejected-name"):
        print(help_mode, file=sys.stderr)
        sys.exit(2)
    if help_mode == "unavailable":
        sys.exit(1)
    print("  --disallowedTools <tools...>  Deny tools" if help_mode == "supported" else "Usage: claude")
    sys.exit(0)
prompt = sys.stdin.read()
with open(os.environ["FAKE_CALLS"], "a", encoding="utf-8") as calls:
    calls.write(json.dumps({"tool": os.path.basename(sys.argv[0]), "args": args,
                            "cwd": os.getcwd(), "prompt": prompt}) + "\n")
mode = os.environ.get("FAKE_CLAUDE_MODE", "success")
if mode == "reject-denial" and "--disallowedTools" in args:
    print("task parser rejects denial", file=sys.stderr)
    sys.exit(2)
init = {"type": "system", "subtype": "init", "mcp_servers": []}
if "FAKE_CLAUDE_TOOLS" in os.environ:
    init["tools"] = os.environ["FAKE_CLAUDE_TOOLS"].split(",")
if "FAKE_CLAUDE_INIT_TOOLS_JSON" in os.environ:
    init["tools"] = json.loads(os.environ["FAKE_CLAUDE_INIT_TOOLS_JSON"])
print(json.dumps(init))
for tools in json.loads(os.environ.get("FAKE_CLAUDE_LATER_INIT", "[]")):
    print(json.dumps({"type": "system", "subtype": "init", "tools": tools}))
print("not json noise")
for name in ["Bash"] + os.environ.get("FAKE_CLAUDE_TOOL_USES", "").split(","):
    if name:
        print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name}]}}))
print("claude warning", file=sys.stderr)
if os.environ.get("FAKE_CLAUDE_LARGE_STREAM"):
    print("drain evidence " * 20000)
if "FAKE_CLAUDE_EVENTS" in os.environ:
    for event in json.loads(os.environ["FAKE_CLAUDE_EVENTS"]):
        print(json.dumps(event))
elif mode in ("success", "signal"):
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "done: " + prompt}))
elif mode == "error":
    print(json.dumps({"type": "result", "subtype": "error_during_execution", "is_error": True, "result": "API refused"}))
elif mode == "exit5":
    sys.exit(5)
if mode == "signal":
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGTERM)
sys.exit(int(os.environ.get("FAKE_CLAUDE_EXIT", "0")))
'''

# Faults affect the dispatcher only; the fake CLI runs in a separate interpreter.
FAULT_WRAPPER = r'''
import builtins, errno, os, runpy, sys
from pathlib import Path
faults = os.environ["CUSTODY_FAULT"].split(",")
write_text, read_text, path_open, native_print = Path.write_text, Path.read_text, Path.open, builtins.print
def failing_write(path, *args, **kwargs):
    if path.name == "final.md" and "final-write" in faults:
        raise OSError(errno.ENOSPC, "injected final write: no space left")
    return write_text(path, *args, **kwargs)
def failing_read(path, *args, **kwargs):
    if path.name == "final.md" and "final-read" in faults:
        raise OSError(errno.EIO, "injected final read failure")
    return read_text(path, *args, **kwargs)
class BrokenLog:
    def __init__(self, handle):
        self.handle = handle
    def __enter__(self):
        self.handle.__enter__()
        return self
    def __exit__(self, *args):
        return self.handle.__exit__(*args)
    def write(self, data):
        raise OSError(errno.ENOSPC, "injected live log failure")
state_appends = 0
def failing_open(path, mode="r", *args, **kwargs):
    global state_appends
    if path.name == "state.txt" and mode == "a":
        state_appends += 1
        if state_appends == 2 and "state-completion" in faults:
            raise OSError(errno.ENOSPC, "injected completion state failure")
    if path.name == "log.txt" and mode == "ab" and "log-write" in faults:
        return BrokenLog(path_open(path, mode, *args, **kwargs))
    if path.name == "state.txt" and mode == "a" and "state-append" in faults:
        raise OSError(errno.ENOSPC, "injected state append: no space left")
    return path_open(path, mode, *args, **kwargs)
def failing_print(*args, **kwargs):
    if args and args[0] == "done: Do the bounded task.\n" and "final-output" in faults:
        raise UnicodeEncodeError("ascii", args[0], 0, 1, "injected final output encoding failure")
    return native_print(*args, **kwargs)
Path.write_text, Path.read_text, Path.open = failing_write, failing_read, failing_open
builtins.print = failing_print
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
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
        for name, body in (("codex", FAKE_CODEX), ("claude5", FAKE_CLAUDE),
                           ("native-call", FAKE_NATIVE_CALLER)):
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
        self.config = self.write_config(CONFIG.read_text(encoding="utf-8"), "routes-base.toml")

    def dispatch(self, *extra, env=None):
        selected_env = env or self.env
        command = ([sys.executable, "-c", FAULT_WRAPPER, str(DISPATCH)]
                   if "CUSTODY_FAULT" in selected_env else [str(DISPATCH)])
        config = () if "--config" in extra else ("--config", self.config)
        return subprocess.run(
            [*command, *config, "--cwd", str(self.cwd), "--prompt", str(self.prompt),
             "--runs-dir", str(self.runs), "--id", "child", *extra],
            env=selected_env, capture_output=True, text=True, check=False)

    def resolved(self, *extra):
        result = self.dispatch("--dry-run", *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith("DRY RUN: {"))
        return json.loads(line.removeprefix("DRY RUN: "))

    def assert_no_effects(self):
        self.assertFalse(self.runs.exists())
        self.assertFalse(self.calls.exists())
        self.assertFalse(self.state_dir.exists())

    def calls_readback(self, include_help=False):
        calls = [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()]
        return calls if include_help else [call for call in calls if "--help" not in call["args"]]

    def write_config(self, text, name="routes.toml"):
        text = re.sub(r'(?m)^caller = ".*"$', f'caller = "{self.bin / "native-call"}"', text)
        path = self.root / name
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

    def test_observer_and_investigator_bindings(self):
        for klass, route in (("new-foundation", "direction"), ("unknown", "direction"),
                             ("correction", "refine")):
            extra = ("--class", klass) + (("--basis", "decision.md") if klass != "unknown" else ())
            observer = self.resolved("--seat", "observer", *extra)
            investigator = self.resolved("--seat", "investigator", *extra)
            self.assertEqual((observer["route"], observer["rule"]), ("refine", "seat:observer"))
            self.assertEqual((investigator["route"], investigator["rule"]),
                             (route, f"seat-class:investigator/{klass}"))
        self.assertEqual(self.resolved("--seat", "investigator")["route"], "direction")
        self.assert_no_effects()

    def test_creative_kind_takes_opus_high_for_every_class_act_seat_and_seatless(self):
        classes = (("--class", "new-foundation", "--basis", "decision.md#1"),
                   ("--class", "correction", "--basis", "frame.md#F2"),
                   ("--class", "unknown"), ())
        for seat in ("maker", "investigator", "method-steward", None):
            for klass in classes:
                seat_args = ("--seat", seat) if seat else ()
                with self.subTest(seat=seat, klass=klass):
                    record = self.resolved(*seat_args, *klass, "--kind", "creative")
                    self.assertEqual((record["route"], record["provider"], record["model"],
                                      record["effort"], record["profile"]),
                                     ("create", "claude", "claude-opus-5-5", "high", "claude5"))
                    self.assertEqual((record["kind"], record["kind_source"], record["rule"]),
                                     ("creative", "supplied",
                                      f"seat-kind:{seat}/creative" if seat else "kind:creative"))
                    self.assertEqual(record["overrides"], [])
        self.assert_no_effects()

    def test_technical_and_unstated_kind_keep_current_bindings(self):
        cases = [(), ("--seat", "framer"), ("--seat", "decider"), ("--seat", "observer"),
                 ("--seat", "scout"), ("--seat", "explorer"), ("--class", "unknown"),
                 ("--class", "correction", "--basis", "b"), ("--class", "new-foundation", "--basis", "b")]
        for seat in ("maker", "investigator", "method-steward"):
            cases += [("--seat", seat), ("--seat", seat, "--class", "correction", "--basis", "b"),
                      ("--seat", seat, "--class", "new-foundation", "--basis", "b")]
        fields = ("rule", "route", "provider", "model", "effort", "class", "class_source")
        for extra in cases:
            with self.subTest(extra=extra):
                unstated = self.resolved(*extra)
                technical = self.resolved(*extra, "--kind", "technical")
                self.assertEqual([unstated[f] for f in fields], [technical[f] for f in fields])
                self.assertEqual((unstated["kind"], unstated["kind_source"]), ("unstated", "not supplied"))
                self.assertEqual((technical["kind"], technical["kind_source"]), ("technical", "supplied"))
        self.assertEqual(self.resolved("--seat", "maker", "--class", "correction", "--basis", "b",
                                       "--kind", "technical")["model"], "gpt-6.1-sol")
        self.assert_no_effects()

    def test_creative_kind_refused_on_look_seats(self):
        for seat in ("framer", "decider", "observer", "scout", "explorer"):
            with self.subTest(seat=seat):
                result = self.dispatch("--dry-run", "--seat", seat, "--kind", "creative")
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(f"does not route seat '{seat}'", result.stderr)
                self.assertNotIn("DRY RUN", result.stdout)
        self.assert_no_effects()

    def test_creative_kind_refuses_overrides_that_leave_opus_high(self):
        reason = ("--override-reason", "caller wants something else")
        for extra in (("--route", "refine"), ("--route", "direction"), ("--route", "default"),
                      ("--model", "gpt-xhigh"), ("--model", "gpt"),
                      ("--model", "claude-sonnet-5-5", "--provider", "claude", "--effort", "high"),
                      ("--model", "claude-opus-5-5", "--provider", "claude", "--effort", "xhigh"),
                      ("--model", "gpt-6.1-sol", "--provider", "codex", "--effort", "high"),
                      ("--effort", "medium"), ("--effort", "max"),
                      ("--profile", ".codex2")):
            for seat in (("--seat", "maker"), ()):
                with self.subTest(extra=extra, seat=seat):
                    for dry in (("--dry-run",), ()):
                        result = self.dispatch(*dry, *seat, "--kind", "creative", *extra, *reason)
                        self.assertEqual(result.returncode, 2, result.stdout)
                        self.assertNotIn("DRY RUN", result.stdout)
                        if extra[0] != "--profile":
                            self.assertIn("--kind creative requires claude / claude-opus-5-5 / high",
                                          result.stderr)
        self.assert_no_effects()
        for extra in (("--route", "create"), ("--effort", "high"), ("--profile", "claude5"),
                      ("--model", "claude-opus-5-5", "--provider", "claude", "--effort", "high"),
                      ("--route", "direction", "--effort", "high")):
            with self.subTest(kept=extra):
                record = self.resolved("--seat", "maker", "--kind", "creative", *extra, *reason)
                self.assertEqual((record["provider"], record["model"], record["effort"],
                                  record["kind"], record["override_reason"]),
                                 ("claude", "claude-opus-5-5", "high", "creative", reason[1]))

    def test_legacy_aliases_and_crw_gpt_xhigh_unchanged_without_creative(self):
        reason = ("--override-reason", "CRW contract names gpt-xhigh")
        for kind in ((), ("--kind", "technical")):
            with self.subTest(kind=kind):
                record = self.resolved("--model", "gpt-xhigh", *kind, *reason)
                self.assertEqual((record["provider"], record["model"], record["effort"],
                                  record["model_alias"], record["rule"]),
                                 ("codex", "gpt-6.1-sol", "xhigh", "gpt-xhigh", "explicit-model"))
        self.assert_no_effects()

    def test_unknown_kind_and_malformed_kind_config_refused(self):
        result = self.dispatch("--kind", "artistic")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown kind 'artistic'", result.stderr)
        result = self.dispatch("--kind", "creative", "--kind", "technical")
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate --kind", result.stderr)
        base = CONFIG.read_text(encoding="utf-8")
        for name, text in {
                "unknown route": base.replace('route = "create"\nseats', 'route = "nowhere"\nseats'),
                "unknown seat": base.replace('seats = ["maker",', 'seats = ["painter", "maker",'),
                "route without seats": base.replace('\nseats = ["maker", "investigator", "method-steward"]', ''),
                "unexpected key": base.replace('[kinds.technical]\n', '[kinds.technical]\nroute_hint = "x"\n'),
        }.items():
            with self.subTest(name=name):
                self.assertNotEqual(text, base)
                result = self.dispatch("--config", self.write_config(text), "--dry-run")
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("config: kinds.", result.stderr)
        self.assert_no_effects()

    def test_unsupported_configured_profile_refused_before_dry_run_or_allocation(self):
        base = CONFIG.read_text(encoding="utf-8")
        for profile in (".codex1", ".codex6", ".codex99"):
            for add_to_pool in (False, True):
                text = base.replace('manual_profiles = [".codex",', f'manual_profiles = ["{profile}", ".codex",', 1)
                if add_to_pool:
                    text = text.replace('pool = [".codex2",', f'pool = ["{profile}", ".codex2",', 1)
                config = self.write_config(text)
                for extra in ((), ("--dry-run",)):
                    with self.subTest(profile=profile, pool=add_to_pool, extra=extra):
                        result = self.dispatch("--config", config, *extra)
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn("codex profiles", result.stderr)
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
            "pool outside manual": base.replace('pool = [".codex2", ".codex4", ".codex5"]',
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
        self.state_dir.mkdir(parents=True)
        (self.state_dir / "codex.counter").write_text("7\n", encoding="utf-8")
        seats = [("--seat", "scout")] * 6 + [()] * 6
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda extra: self.dispatch("--transport", "direct", *extra), seats))
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads((attempt / "route.json").read_text())
                   for attempt in self.runs.iterdir()]
        self.assertEqual(sorted(r["profile_source"] for r in records),
                         sorted(f"rotation:{n}" for n in range(7, 19)))
        expected_pool = (".codex2", ".codex4", ".codex5")
        self.assertEqual({r["profile"] for r in records}, set(expected_pool))
        for profile in expected_pool:
            self.assertEqual(sum(r["profile"] == profile for r in records), 4, profile)
        self.assertEqual({r["model"] for r in records}, {"gpt-6.1-sol", "gpt-6-luna"})
        for record in records:
            turn = int(record["profile_source"].split(":")[1])
            self.assertEqual(record["profile"], expected_pool[turn % 3])
        self.assertEqual((self.state_dir / "codex.counter").read_text(), "19\n")
        exec_homes = sorted(call["home"] for call in self.calls_readback() if call["args"][0] == "exec")
        self.assertEqual(exec_homes, sorted(str(self.home / r["profile"]) for r in records))

        dry = self.resolved()
        self.assertEqual((dry["profile"], dry["profile_source"]),
                         (".codex4", "rotation-preview:19 (not reserved)"))
        explicit_preview = self.resolved("--profile", ".codex",
                                         "--override-reason", "manual history")
        self.assertEqual((explicit_preview["profile"], explicit_preview["profile_source"]),
                         (".codex", "explicit"))
        previous = set(self.runs.iterdir())
        explicit = self.dispatch("--transport", "direct", "--profile", ".codex", "--override-reason", "manual history")
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        attempt = (set(self.runs.iterdir()) - previous).pop()
        record = json.loads((attempt / "route.json").read_text())
        self.assertEqual((record["profile"], record["profile_source"]), (".codex", "explicit"))
        self.assertEqual((self.state_dir / "codex.counter").read_text(), "19\n")
        self.assertEqual(len(list(self.runs.iterdir())), 13)

    # ----------------------------------------------------------------- codex

    def test_codex_route_keeps_mcp_preflight_and_records_route(self):
        result = self.dispatch("--transport", "direct", "--seat", "maker", "--class", "correction", "--basis", "F2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DIRECT_CODEX_EXIT=0", result.stdout)
        self.assertIn('"transport_rule": "explicit-direct"', result.stdout)
        attempt = next(self.runs.iterdir())
        record = json.loads((attempt / "route.json").read_text())
        self.assertEqual((record["seat"], record["class"], record["basis"], record["rule"],
                          record["profile"]),
                         ("maker", "correction", "F2", "seat-class:maker/correction", ".codex2"))
        state = (attempt / "state.txt").read_text()
        self.assertIn("profile=.codex2\nmodel=gpt-6.1-sol\neffort=high\n", state)
        self.assertIn(f"cwd={self.cwd}\n", state)
        self.assertIn("delegation_capability=not-established\n", state)
        self.assertIn("delegation_feature_readback=all-listed-false\n", state)
        calls = self.calls_readback()
        self.assertEqual(len(calls), 5)
        exec_args = calls[-1]["args"]
        self.assertIn("features.multi_agent=false", exec_args)
        self.assertEqual(exec_args[exec_args.index("-m") + 1], "gpt-6.1-sol")
        self.assertIn('model_reasoning_effort="high"', exec_args)
        self.assertEqual(exec_args[exec_args.index("-C") + 1], str(self.cwd))
        for flag in ("mcp_servers.firecrawl.enabled=false",
                     "mcp_servers.openaiDeveloperDocs.enabled=false",
                     'mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"'):
            self.assertIn(flag, exec_args)
        self.assertFalse((self.root / "pwned").exists())

    def test_codex_enabled_mcp_refuses_launch(self):
        result = self.dispatch("--transport", "direct", "--seat", "scout",
                               env=self.env | {"FAKE_FORCE_ENABLED": "firecrawl"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("MCP preflight", result.stderr)
        self.assertFalse(self.runs.exists())
        self.assertFalse(any(call["args"][0] == "exec" for call in self.calls_readback()))

    # ---------------------------------------------------------------- claude

    def claude_attempt(self, mode, **environment):
        previous = set(self.runs.iterdir()) if self.runs.exists() else set()
        result = self.dispatch("--transport", "direct", "--seat", "framer",
                               env=self.env | {"FAKE_CLAUDE_MODE": mode} | environment)
        attempt = (set(self.runs.iterdir()) - previous).pop()
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
                                        "--disallowedTools", "Agent,Task,Workflow",
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

    def test_claude_delegation_provenance_comes_from_the_session_record(self):
        cases = (
            ({"FAKE_CLAUDE_TOOLS": "Bash,Read,Edit"}, "not-listed",
             "known names absent from recorded init lists; capability absence unproven", "0"),
            ({}, "unknown", "init tool metadata missing, empty or malformed", "0"),
            ({"FAKE_CLAUDE_TOOLS": "Bash,Agent,Workflow", "FAKE_CLAUDE_TOOL_USES": "Agent,Agent"},
             "offered", "init offered Agent,Workflow", "2"),
        )
        for environment, status, note, uses in cases:
            with self.subTest(environment=environment):
                result, attempt, state = self.claude_attempt("success", **environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(state["requested_disallowed_tools"], "Agent,Task,Workflow")
                self.assertEqual(state["delegation_capability"], "not-established")
                self.assertEqual(state["delegation_init_status"], status)
                self.assertEqual(state.get("delegation_capability_note"), note)
                self.assertEqual(state["delegation_tool_uses"], uses)
                self.assertIn("shell-launched processes", state["delegation_scope"])

    def test_claude_unavailable_restriction_is_omitted_before_one_task(self):
        for help_mode in ("rejected-flag", "rejected-name", "unavailable", "undocumented"):
            with self.subTest(help_mode=help_mode):
                self.calls.unlink(missing_ok=True)
                result, attempt, state = self.claude_attempt("success", FAKE_CLAUDE_HELP=help_mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = self.calls_readback(include_help=True)
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[0]["args"], ["--disallowedTools", "Agent,Task,Workflow", "--help"])
                self.assertTrue(Path(calls[0]["home"]).is_relative_to(attempt))
                self.assertTrue(Path(calls[0]["claude_config"]).is_relative_to(attempt))
                self.assertNotIn("--disallowedTools", calls[1]["args"])
                self.assertIn("--strict-mcp-config", calls[1]["args"])
                self.assertEqual(state["restriction_selection"], "omitted")
                self.assertEqual(state["requested_disallowed_tools"], "")
                self.assertEqual(state["delegation_capability"], "not-established")

    def test_claude_ambiguous_or_contradictory_init_does_not_claim_absence(self):
        cases = (
            ({"FAKE_CLAUDE_INIT_TOOLS_JSON": "[]"}, "unknown"),
            ({"FAKE_CLAUDE_INIT_TOOLS_JSON": '[{"name":"Agent"}]'}, "unknown"),
            ({"FAKE_CLAUDE_TOOLS": "Bash", "FAKE_CLAUDE_LATER_INIT": '[["Bash","Agent"]]'}, "offered"),
            ({"FAKE_CLAUDE_TOOLS": "Bash", "FAKE_CLAUDE_LATER_INIT": '[["Read"]]'}, "unknown"),
            ({"FAKE_CLAUDE_TOOLS": "Bash", "FAKE_CLAUDE_TOOL_USES": "Agent"}, "contradicted"),
        )
        for environment, init_status in cases:
            with self.subTest(environment=environment):
                result, attempt, state = self.claude_attempt("success", **environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(state["delegation_capability"], "not-established")
                self.assertEqual(state["delegation_init_status"], init_status)
                self.assertTrue(json.loads(state["delegation_init_tools"]))

    def test_creative_launch_carries_effort_high_to_claude5_and_records_kind(self):
        for extra in (("--seat", "maker", "--class", "correction", "--basis", "frame.md#F1"), ()):
            with self.subTest(extra=extra):
                previous = set(self.runs.iterdir()) if self.runs.exists() else set()
                result = self.dispatch("--transport", "direct", *extra, "--kind", "creative")
                self.assertEqual(result.returncode, 0, result.stderr)
                attempt = (set(self.runs.iterdir()) - previous).pop()
                call = self.calls_readback()[-1]
                self.assertEqual(call["tool"], "claude5")
                self.assertEqual(call["args"][:5], ["-p", "--model", "claude-opus-5-5", "--effort", "high"])
                record = json.loads((attempt / "route.json").read_text())
                self.assertEqual((record["kind"], record["kind_source"], record["route"], record["effort"]),
                                 ("creative", "supplied", "create", "high"))
                state = (attempt / "state.txt").read_text()
                self.assertIn("model=claude-opus-5-5\neffort=high\n", state)
                self.assertIn("kind=creative\n", state)
        self.assertFalse(self.state_dir.exists())

    def test_technical_codex_route_json_records_unstated_kind(self):
        result = self.dispatch("--transport", "direct", "--seat", "observer")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((next(self.runs.iterdir()) / "route.json").read_text())
        self.assertEqual((record["kind"], record["kind_source"], record["model"], record["effort"]),
                         ("unstated", "not supplied", "gpt-6.1-sol", "high"))

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
        self.assertEqual(len(self.calls_readback()), 1)

    def test_claude_help_acceptance_does_not_replay_a_rejected_task(self):
        result, attempt, state = self.claude_attempt("reject-denial")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(self.calls_readback()), 1)
        self.assertEqual(state["restriction_selection"], "requested")
        self.assertEqual(state["claude_exit"], "2")
        self.assertEqual(state["delegation_capability"], "not-established")

    def test_claude_signal_exit_uses_shell_status_and_retains_raw_wait(self):
        result, attempt, state = self.claude_attempt("signal")
        self.assertEqual(result.returncode, 143, result.stderr)
        self.assertEqual((state["claude_exit"], state["dispatcher_exit"]), ("-15", "143"))
        self.assertIn("CLAUDE_EXIT=-15", result.stdout)
        self.assertIn('"subtype": "success"', (attempt / "log.txt").read_text())
        self.assertNotIn("DIRECT_CHILD_FINAL_BEGIN=", result.stdout)

    def test_claude_malformed_or_duplicate_results_never_certify_success(self):
        good = {"type": "result", "subtype": "success", "is_error": False, "result": "available text"}
        candidates = [
            {k: v for k, v in good.items() if k != "is_error"},
            good | {"is_error": None}, good | {"is_error": 0},
            good | {"is_error": "false"}, good | {"is_error": []},
            {k: v for k, v in good.items() if k != "subtype"},
            good | {"subtype": "error_during_execution"},
            good | {"result": None}, good | {"result": 7}, good | {"result": "  "},
        ]
        streams = [[event] for event in candidates] + [
            [good, good],
            [good | {"is_error": True, "result": "refused"}, good],
            [good, good | {"is_error": True, "result": "refused"}],
        ]
        for events in streams:
            with self.subTest(events=events):
                result, attempt, state = self.claude_attempt(
                    "success", FAKE_CLAUDE_EVENTS=json.dumps(events))
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertEqual(state["claude_exit"], "0")
                self.assertEqual(state["semantic_is_error"], "unknown")
                self.assertIn(state["final_status"], ("missing", "invalid-result"))
                self.assertNotIn("DIRECT_CHILD_FINAL_BEGIN=", result.stdout)
                self.assertIn(json.dumps(events[0]), (attempt / "log.txt").read_text())
                if any(event.get("result") == "available text" for event in events):
                    self.assertIn("available text", (attempt / "final.md").read_text())

    def test_claude_final_custody_faults_preserve_native_exit_and_raw_stream(self):
        for fault in ("final-write", "final-read", "final-output"):
            for mode, native_exit, terminal_exit in (("success", "0", 4),
                                                     ("success", "5", 5),
                                                     ("signal", "-15", 143)):
                with self.subTest(fault=fault, native_exit=native_exit):
                    result, attempt, state = self.claude_attempt(
                        mode, CUSTODY_FAULT=fault,
                        FAKE_CLAUDE_EXIT="5" if native_exit == "5" else "0")
                    self.assertEqual(result.returncode, terminal_exit, result.stderr)
                    self.assertEqual(state["claude_exit"], native_exit)
                    self.assertEqual(state["dispatcher_exit"], str(terminal_exit))
                    self.assertEqual(state["final_status"], "capture-error")
                    self.assertEqual(state["custody_status"], "incomplete")
                    self.assertIn("final_capture_error", state)
                    self.assertIn("final_capture_error", result.stderr)
                    self.assertIn(f"CLAUDE_EXIT={native_exit}", result.stdout)
                    self.assertIn('"type": "result"', result.stdout)
                    self.assertIn('"type": "result"', (attempt / "log.txt").read_text())
                    self.assertNotIn("Traceback", result.stderr)

    def test_claude_unencodable_final_is_incomplete_after_native_wait(self):
        event = {"type": "result", "subtype": "success", "is_error": False, "result": "\ud800"}
        result, attempt, state = self.claude_attempt("success", FAKE_CLAUDE_EVENTS=json.dumps([event]))
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertEqual(state["claude_exit"], "0")
        self.assertEqual(state["final_status"], "capture-error")
        self.assertIn("final_capture_error", state)
        self.assertIn("\\ud800", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_claude_unwritable_state_reports_available_terminal_metadata(self):
        for fault in ("state-append", "state-append,final-write"):
            for native_exit in ("0", "5"):
                with self.subTest(fault=fault, native_exit=native_exit):
                    result, attempt, state = self.claude_attempt(
                        "success", CUSTODY_FAULT=fault, FAKE_CLAUDE_EXIT=native_exit)
                    expected = 5 if native_exit == "5" else (4 if "final-write" in fault else 1)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertNotIn("claude_exit", state)
                    self.assertIn(f"CLAUDE_EXIT={native_exit}", result.stdout)
                    self.assertIn("CUSTODY_STATUS=incomplete", result.stdout)
                    self.assertIn("state_capture_error", result.stderr)
                    self.assertIn('"type": "result"', result.stdout)
                    self.assertNotIn("Traceback", result.stderr)

    def test_claude_log_failure_keeps_draining_to_result_and_reaps_native_process(self):
        result, attempt, state = self.claude_attempt(
            "success", CUSTODY_FAULT="log-write", FAKE_CLAUDE_LARGE_STREAM="1")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual((state["claude_exit"], state["result_event_count"]), ("0", "1"))
        self.assertEqual((state["log_capture_exit"], state["custody_status"]), ("1", "incomplete"))
        self.assertIn("drain evidence " * 1000, result.stdout)
        self.assertIn('"subtype": "success"', result.stdout)
        self.assertEqual((attempt / "final.md").read_text(), "done: Do the bounded task.\n")
        self.assertNotIn("Traceback", result.stderr)

    def test_claude_completion_state_failure_retains_earlier_wait_metadata(self):
        for native_exit in ("0", "5"):
            with self.subTest(native_exit=native_exit):
                result, attempt, state = self.claude_attempt(
                    "success", CUSTODY_FAULT="state-completion", FAKE_CLAUDE_EXIT=native_exit)
                self.assertEqual(result.returncode, 1 if native_exit == "0" else 5, result.stderr)
                self.assertEqual(state["claude_exit"], native_exit)
                self.assertNotIn("dispatcher_exit", state)
                self.assertIn(f"CLAUDE_EXIT={native_exit}", result.stdout)
                self.assertIn("CUSTODY_STATUS=incomplete", result.stdout)
                self.assertIn("state_capture_error", result.stderr)
                self.assertIn('"type": "result"', (attempt / "log.txt").read_text())
                self.assertNotIn("Traceback", result.stderr)

    def test_missing_claude_wrapper_refuses_before_attempt(self):
        (self.bin / "claude5").unlink()
        result = self.dispatch("--transport", "direct", "--seat", "decider")
        self.assertEqual(result.returncode, 2)
        self.assertIn("claude5", result.stderr)
        self.assertFalse(self.runs.exists())

    def test_dry_run_command_round_trips_hostile_paths(self):
        for extra in (("--transport", "direct", "--seat", "decider"), ("--transport", "direct", "--seat", "scout")):
            with self.subTest(extra=extra):
                result = self.dispatch("--dry-run", *extra)
                line = next(l for l in result.stdout.splitlines()
                            if l.startswith("DRY RUN: would run: "))
                argv = shlex.split(line.removeprefix("DRY RUN: would run: "))
                if extra[-1] == "scout":
                    self.assertEqual(argv[argv.index("--cwd") + 1], str(self.cwd))
                    self.assertEqual(argv[argv.index("--prompt") + 1], str(self.prompt))
                else:
                    self.assertEqual(argv[argv.index("--mcp-config") + 1], '{"mcpServers":{}}')
        self.assert_no_effects()
        self.assertFalse((self.root / "pwned").exists())


if __name__ == "__main__":
    unittest.main()
