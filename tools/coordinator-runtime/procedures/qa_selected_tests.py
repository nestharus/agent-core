"""UNSELECTED reusable local-QA template; compatible with public qa_source.command.

The outside independent selector must seal SELECTION_SHA256 and substitute
REPOSITORY/OUTPUT in a separately pinned copy, with sibling TEST-SELECTION.json
using ordinary-qa-selection538-v1. Review the actual immutable source, meaningful
method IDs, whole tracked manifest, resources and original collector separately.
A completed report can contain failures/errors/skips; strict_pass cannot judge
whether a selected test is meaningful. Current original END and complete tool
streams remain required (direct fd output is outside Python capture). Existing
exclusive output is never a new attempt. No admission/acceptance authority here.
"""
import ast
import asyncio
import hashlib
import importlib.machinery
import io
import json
import linecache
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import threading
import _thread
import unittest

SELECTION_SHA256 = "$input.independently_selected_final_selection_file_sha256"
SELECTION_PATH = Path(__file__).with_name("TEST-SELECTION.json")
REPOSITORY = Path("$input.final_repository")
OUTPUT = Path("$input.owned_output_root")
MAX_FILE = 4 * 1024 * 1024


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_regular(path, maximum):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("noncanonical path")
    for parent in reversed(path.parents):
        if stat.S_ISLNK(parent.lstat().st_mode):
            raise ValueError("symlink ancestor")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        a = os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_size > maximum:
            raise ValueError("unbounded/nonregular file")
        data = bytearray()
        while True:
            block = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not block:
                break
            data.extend(block)
            if len(data) > maximum:
                raise ValueError("file grew")
        z = os.fstat(fd)
        witness = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if witness(a) != witness(z) or witness(a) != witness(path.lstat()):
            raise ValueError("file changed during read")
        return bytes(data)
    finally:
        os.close(fd)


def git_hash(kind, body, width):
    algorithm = hashlib.sha1 if width == 40 else hashlib.sha256
    return algorithm(kind.encode() + b" " + str(len(body)).encode() + b"\0" + body).hexdigest()


def source_readback(source):
    files = source["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 5000:
        raise ValueError("whole tracked manifest missing")
    if hashlib.sha256(canon(files).encode()).hexdigest() != source["manifest_sha256"]:
        raise ValueError("source manifest digest differs")
    width = len(source["tree"])
    if width not in (40, 64) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source["head"]):
        raise ValueError("final source identity missing")
    tree, total, seen = {}, 0, set()
    for item in files:
        if set(item) != {"path", "mode", "blob", "size", "sha256"}:
            raise ValueError("wrong source manifest fields")
        path = PurePosixPath(item["path"])
        if (str(path) != item["path"] or path.is_absolute() or not path.parts
                or any(p in (".", "..", ".git") for p in path.parts) or str(path) in seen
                or item["mode"] not in ("100644", "100755") or type(item["size"]) is not int
                or not 0 <= item["size"] <= MAX_FILE or len(item["blob"]) != width):
            raise ValueError("unsupported/duplicate tracked path")
        seen.add(str(path))
        body = read_regular(REPOSITORY / path, MAX_FILE)
        if (len(body) != item["size"] or hashlib.sha256(body).hexdigest() != item["sha256"]
                or git_hash("blob", body, width) != item["blob"]):
            raise ValueError("actual exported blob differs")
        total += len(body)
        if total > 128 * 1024 * 1024:
            raise ValueError("whole source byte limit")
        node = tree
        for part in path.parts[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise ValueError("file/directory collision")
        if path.name in node:
            raise ValueError("tree collision")
        node[path.name] = (item["mode"], item["blob"])
    def tree_id(node):
        records = []
        for name, value in node.items():
            directory = isinstance(value, dict)
            mode, oid = ("40000", tree_id(value)) if directory else value
            records.append((name.encode() + (b"/" if directory else b""),
                            mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid)))
        return git_hash("tree", b"".join(v for _, v in sorted(records)), width)
    if tree_id(tree) != source["tree"]:
        raise ValueError("whole exported Git tree differs")
    return {"manifest_sha256": source["manifest_sha256"], "tree": source["tree"],
            "files": len(files), "bytes": total}


class BoundedText(io.TextIOBase):
    def __init__(self, maximum):
        self.maximum, self.data, self.overflow = maximum, bytearray(), False
    def write(self, text):
        body = text.encode("utf-8", "strict")
        if len(self.data) + len(body) > self.maximum:
            self.overflow = True
            raise RuntimeError("selected-test capture overflow")
        self.data.extend(body)
        return len(text)
    def flush(self):
        pass


class RecordedResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.started, self.stopped, self.events = [], [], []
    def startTest(self, test):
        super().startTest(test)
        self.started.append(test.id())
    def stopTest(self, test):
        self.stopped.append(test.id())
        super().stopTest(test)
    def event(self, test, status, detail=""):
        self.events.append({"id": test.id(), "status": status, "detail": detail[:8192]})
    def addSuccess(self, test):
        super().addSuccess(test); self.event(test, "passed")
    def addFailure(self, test, err):
        super().addFailure(test, err); self.event(test, "failed", self._exc_info_to_string(err, test))
    def addError(self, test, err):
        super().addError(test, err); self.event(test, "error", self._exc_info_to_string(err, test))
    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.event(test, "skipped", reason)
    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self.event(test, "expected-failure")
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self.event(test, "unexpected-success")
    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.events.append({"id": test.id(), "status": "subtest-passed" if err is None else "subtest-failed",
                            "detail": str(subtest)[:8192]})


def main():
    if not re.fullmatch("[0-9a-f]{64}", SELECTION_SHA256):
        raise ValueError("UNSELECTED: independent final selection seal missing")
    raw = read_regular(SELECTION_PATH, MAX_FILE)
    if hashlib.sha256(raw).hexdigest() != SELECTION_SHA256:
        raise ValueError("independent selection file changed")
    if b"$input." in raw or b"$observed." in raw:
        raise ValueError("unfilled actual operands remain")
    cfg = json.loads(raw, object_pairs_hook=pairs)
    if (cfg["schema"] != "ordinary-qa-selection538-v1" or cfg["selection_complete"] is not True
            or cfg["selected_by"] != "01a18bac-b565-7742-86bc-0f9ba5ffc831"
            or not cfg["selection_authority"] or not cfg["selection_rationale"]
            or cfg["output_root"] != str(OUTPUT) or Path.cwd() != REPOSITORY
            or cfg["resource_boundary"] != "selected-python-no-child-process-no-new-thread-v1"):
        raise ValueError("exact independent scope/selection missing")
    before = source_readback(cfg["source"])
    chosen, modules = [], []
    if not isinstance(cfg["tests"], list) or not cfg["tests"]:
        raise ValueError("nonempty test selection required")
    manifest = {f["path"]: f for f in cfg["source"]["files"]}
    for selected in cfg["tests"]:
        path = PurePosixPath(selected["path"])
        if (path.parent != PurePosixPath("tools/coordinator-runtime/tests") or path.suffix != ".py"
                or not re.fullmatch(r"test_[A-Za-z0-9_]+", path.stem)
                or selected["sha256"] != manifest[str(path)]["sha256"] or not selected["ids"]):
            raise ValueError("unreviewed selected test source")
        body = read_regular(REPOSITORY / path, MAX_FILE)
        ast.parse(body)  # Syntax is checked before candidate execution.
        for ident in selected["ids"]:
            if not re.fullmatch(re.escape(path.stem) + r"\.[A-Za-z0-9_]+\.test_[A-Za-z0-9_]+", ident):
                raise ValueError("exact selected test identity required")
            chosen.append(ident)
        modules.append(path.stem)
    if not 1 <= len(chosen) <= 512 or len(set(chosen)) != len(chosen) or len(set(modules)) != len(modules):
        raise ValueError("empty/duplicate/overbroad selection")
    limits = cfg["limits"]
    if (type(limits["capture_bytes"]) is not int or not 1 <= limits["capture_bytes"] <= 1048576
            or type(limits["result_bytes"]) is not int or not 1 <= limits["result_bytes"] <= 4*1048576):
        raise ValueError("bounded capture/result required")
    for p in (OUTPUT, *OUTPUT.parents):
        if p.is_symlink():
            raise ValueError("output symlink")
    if not OUTPUT.is_dir():
        raise ValueError("actual pre-owned output directory required")
    # Exclusive marker is kept if anything interrupts; no overwrite/retry.
    fd = os.open(OUTPUT / "result.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    pid = os.getpid()
    # Exact own PID only, not a process census; oracle rechecks this identity.
    proc = Path(f"/proc/{pid}/stat").read_text()
    start = int(proc.rsplit(")", 1)[1].split()[19])
    capture = BoundedText(limits["capture_bytes"])
    oldout, olderr = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = capture
    stdlib = Path(sys.base_prefix) / "lib" / ("python%d.%d" % sys.version_info[:2])
    sys.path[:] = [str(REPOSITORY / "tools/coordinator-runtime"),
                   str(REPOSITORY / "tools/coordinator-runtime/tests"), str(stdlib), str(stdlib / "lib-dynload")]
    def denied(*args, **kwargs):
        raise RuntimeError("selected procedure forbids child processes/new threads")
    threading.Thread.start = denied
    _thread.start_new_thread = denied
    allowed_files = {str(REPOSITORY / f["path"]) for f in cfg["source"]["files"]}
    def audit(event, args):
        if (event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
                      "os.exec", "sqlite3.connect", "ctypes.dlopen", "socket.connect", "socket.bind",
                      "socket.getaddrinfo", "os.remove", "os.rename", "os.rmdir", "os.mkdir",
                      "os.link", "os.symlink", "os.truncate", "os.chmod", "os.chown"}):
            raise RuntimeError("resource boundary refused " + event)
        if event == "open":
            path, mode, flags = args
            if (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                raise RuntimeError("candidate file write refused")
            if isinstance(path, (str, bytes)):
                p = os.fsdecode(path)
                if p not in allowed_files and not p.startswith(str(stdlib) + "/"):
                    raise RuntimeError("candidate read outside selected source/stdlib refused")
        if event == "socket.__new__" and args[1] != 1:  # AF_UNIX for asyncio's owned self-pipe only.
            raise RuntimeError("network socket refused")
    # Debug asyncio task creation and unittest error formatting inspect stack
    # frames in this external procedure. Cache only this exact, already pinned
    # public script BEFORE installing the audit hook. mtime=None keeps linecache
    # from re-opening it during checkcache; this grants no candidate file read.
    # In particular the script directory is never added to allowed_files.
    procedure_path = str(Path(__file__).absolute())
    procedure_bytes = read_regular(Path(procedure_path), MAX_FILE)
    linecache.cache[procedure_path] = (len(procedure_bytes), None,
        procedure_bytes.decode("utf-8").splitlines(keepends=True), procedure_path)
    sys.addaudithook(audit)
    # Import actual .py source, never an untracked bytecode-cache attempt.
    def source_only(loader, fullname):
        filename = loader.get_filename(fullname)
        return compile(loader.get_data(filename), filename, "exec", dont_inherit=True)
    importlib.machinery.SourceFileLoader.get_code = source_only
    result = RecordedResult()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(chosen)
    if loader.errors or suite.countTestCases() != len(chosen):
        raise RuntimeError("selected tests failed to load exactly")
    for name in modules:
        module = sys.modules[name]
        if Path(module.__file__).absolute() != REPOSITORY / "tools/coordinator-runtime/tests" / (name + ".py"):
            raise RuntimeError("selected module did not load from exported candidate")
    suite.run(result)
    if capture.overflow:
        raise RuntimeError("incomplete selected-test capture")
    after = source_readback(cfg["source"])
    closed_threads = len(threading.enumerate()) == 1
    if before != after or not closed_threads or result.started != chosen or result.stopped != chosen:
        raise RuntimeError("incomplete suite/source/resource closure")
    imported = []
    for name, module in sorted(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and Path(file).is_relative_to(REPOSITORY):
            rel = str(Path(file).relative_to(REPOSITORY))
            if rel not in manifest:
                raise RuntimeError("import outside whole tracked manifest")
            imported.append({"module": name, "path": rel, "sha256": manifest[rel]["sha256"]})
    terminal = [e for e in result.events if not e["status"].startswith("subtest-")]
    strict_pass = (len(terminal) == len(chosen) and all(e["status"] == "passed" for e in terminal)
                   and all(e["status"] != "subtest-failed" for e in result.events)
                   and result.testsRun == len(chosen))
    report = {"schema": "ordinary-qa-result538-v1", "selection_sha256": SELECTION_SHA256,
        "source": before, "selected_ids": chosen, "started": result.started, "stopped": result.stopped,
        "events": result.events, "tests_run": result.testsRun, "strict_pass": strict_pass,
        "exit": 0 if strict_pass else 1, "imported": imported,
        "runner": {"pid": pid, "start_ticks": start, "python_threads_at_completion": 1,
                   "boundary": cfg["resource_boundary"]},
        "capture": capture.data.decode("utf-8"), "capture_sha256": hashlib.sha256(capture.data).hexdigest()}
    body = (canon(report) + "\n").encode()
    if len(body) > limits["result_bytes"]:
        raise RuntimeError("result capture exceeded selected budget")
    offset = 0
    while offset < len(body):
        offset += os.write(fd, body[offset:])
    os.fsync(fd)
    os.close(fd)
    sys.stdout, sys.stderr = oldout, olderr
    sys.stdout.write(body.decode())
    return report["exit"]


if __name__ == "__main__":
    try:
        code = main()
    except BaseException as exc:
        # Exit 2 is deliberately outside [0,1]: unknown/interrupted is not known failure.
        sys.__stderr__.write("QA_PROCEDURE_INCOMPLETE:" + type(exc).__name__ + "\n")
        code = 2
    sys.exit(code)
