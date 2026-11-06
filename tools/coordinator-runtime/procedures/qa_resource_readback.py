"""UNSELECTED independent readback; never imports candidate or runner code.
Seal a separate copy and sibling TEST-SELECTION.json as documented in
qa_selected_tests.py. Compatible schema538 is preserved for the public adapter.
Validates actual artifacts/source and exact original process absence in the
SAME PID namespace as runner (the public builder does not unshare PID). Its
stdout attests bounded completion/resource readback, not success or acceptance.
The caller must first collect the CURRENT original END (known exits [0,1]) and
bind that collection via qa_source.verify. Readback alone can validate an older
retained result after a refused second runner attempt. Preserve complete tool
streams in addition to Python capture; no cross-namespace closure claim.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

SELECTION_SHA256 = "$input.independently_selected_final_selection_file_sha256"
SELECTION_PATH = Path(__file__).with_name("TEST-SELECTION.json")
REPOSITORY = Path("$input.final_repository")
OUTPUT = Path("$input.owned_output_root")


def encode(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def unique(entries):
    result = {}
    for key, value in entries:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def bytes_at(path, limit):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("noncanonical readback path")
    for part in (path, *path.parents):
        if stat.S_ISLNK(part.lstat().st_mode):
            raise ValueError("readback symlink refused")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(descriptor)
        if not stat.S_ISREG(first.st_mode) or first.st_size > limit:
            raise ValueError("nonregular/overbudget readback")
        chunks, count = [], 0
        while True:
            piece = os.read(descriptor, min(65536, limit + 1 - count))
            if not piece:
                break
            count += len(piece)
            if count > limit:
                raise ValueError("readback grew")
            chunks.append(piece)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if fields(first) != fields(os.fstat(descriptor)) or fields(first) != fields(path.lstat()):
            raise ValueError("readback identity changed")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def object_id(kind, content, width):
    algorithm = {40: hashlib.sha1, 64: hashlib.sha256}[width]
    return algorithm(kind + b" " + str(len(content)).encode() + b"\0" + content).hexdigest()


def inspect_source(source):
    listing = source["files"]
    if (not isinstance(listing, list) or not 1 <= len(listing) <= 5000
            or hashlib.sha256(encode(listing).encode()).hexdigest() != source["manifest_sha256"]):
        raise ValueError("missing/different complete manifest")
    width = len(source["tree"])
    tree, names, total = {}, set(), 0
    for record in listing:
        if set(record) != {"path", "mode", "blob", "size", "sha256"}:
            raise ValueError("manifest shape")
        path = PurePosixPath(record["path"])
        if (not path.parts or path.is_absolute() or str(path) != record["path"]
                or any(x in (".", "..", ".git") for x in path.parts)
                or str(path) in names or record["mode"] not in ("100644", "100755")
                or type(record["size"]) is not int or not 0 <= record["size"] <= 4194304
                or len(record["blob"]) != width):
            raise ValueError("unsupported/duplicate blob")
        names.add(str(path))
        body = bytes_at(REPOSITORY / path, 4194304)
        if (len(body) != record["size"] or hashlib.sha256(body).hexdigest() != record["sha256"]
                or object_id(b"blob", body, width) != record["blob"]):
            raise ValueError("independent actual source byte mismatch")
        total += len(body)
        if total > 134217728:
            raise ValueError("aggregate source overflow")
        branch = tree
        for component in path.parts[:-1]:
            branch = branch.setdefault(component, {})
            if not isinstance(branch, dict):
                raise ValueError("tree path collision")
        if path.name in branch:
            raise ValueError("duplicate tree member")
        branch[path.name] = (record["mode"], record["blob"])
    def walk(branch):
        contents = []
        for name, entry in branch.items():
            is_dir = isinstance(entry, dict)
            mode, digest = ("40000", walk(entry)) if is_dir else entry
            sort_key = name.encode() + (b"/" if is_dir else b"")
            contents.append((sort_key, mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(digest)))
        return object_id(b"tree", b"".join(x[1] for x in sorted(contents)), width)
    if walk(tree) != source["tree"]:
        raise ValueError("independent complete Git tree reconstruction differs")
    return {"manifest_sha256": source["manifest_sha256"], "tree": source["tree"],
            "files": len(listing), "bytes": total}


def main():
    if not re.fullmatch(r"[0-9a-f]{64}", SELECTION_SHA256):
        raise ValueError("UNSELECTED independent seal missing")
    raw = bytes_at(SELECTION_PATH, 4194304)
    if hashlib.sha256(raw).hexdigest() != SELECTION_SHA256:
        raise ValueError("selection bytes changed")
    if b"$input." in raw or b"$observed." in raw:
        raise ValueError("unfilled actual operands remain")
    selection = json.loads(raw, object_pairs_hook=unique)
    if (selection["schema"] != "ordinary-qa-selection538-v1" or selection["selection_complete"] is not True
            or selection["selected_by"] != "01a18bac-b565-7742-86bc-0f9ba5ffc831"
            or not selection["selection_authority"] or not selection["selection_rationale"]
            or selection["output_root"] != str(OUTPUT) or Path.cwd() != REPOSITORY
            or selection["resource_boundary"] != "selected-python-no-child-process-no-new-thread-v1"):
        raise ValueError("independent selected scope missing")
    expected_ids = []
    manifest = {r["path"]: r for r in selection["source"]["files"]}
    for item in selection["tests"]:
        path = PurePosixPath(item["path"])
        if (path.parent != PurePosixPath("tools/coordinator-runtime/tests") or path.suffix != ".py"
                or item["sha256"] != manifest[str(path)]["sha256"] or not item["ids"]):
            raise ValueError("test source selection mismatch")
        for identity in item["ids"]:
            if not re.fullmatch(re.escape(path.stem) + r"\.[A-Za-z0-9_]+\.test_[A-Za-z0-9_]+", identity):
                raise ValueError("invalid selected identity")
        expected_ids.extend(item["ids"])
    if not 1 <= len(expected_ids) <= 512 or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("empty/duplicate selection")
    source = inspect_source(selection["source"])
    maximum = selection["limits"]["result_bytes"]
    if type(maximum) is not int or not 1 <= maximum <= 4194304:
        raise ValueError("invalid result bound")
    raw_result = bytes_at(OUTPUT / "result.json", maximum)
    result = json.loads(raw_result, object_pairs_hook=unique)
    if raw_result != (encode(result) + "\n").encode():
        raise ValueError("noncanonical/incomplete runner artifact")
    if (result["schema"] != "ordinary-qa-result538-v1" or result["selection_sha256"] != SELECTION_SHA256
            or result["source"] != source or result["selected_ids"] != expected_ids
            or result["started"] != expected_ids or result["stopped"] != expected_ids
            or type(result["tests_run"]) is not int or result["tests_run"] != len(expected_ids)):
        raise ValueError("incomplete selected execution/source association")
    events = result["events"]
    statuses = {"passed", "failed", "error", "skipped", "expected-failure", "unexpected-success",
                "subtest-passed", "subtest-failed"}
    if not isinstance(events, list) or not events:
        raise ValueError("no real assertion outcomes")
    for event in events:
        if (set(event) != {"id", "status", "detail"} or event["id"] not in expected_ids
                or event["status"] not in statuses or not isinstance(event["detail"], str)):
            raise ValueError("invalid/unselected assertion record")
    for identity in expected_ids:
        rows = [e for e in events if e["id"] == identity]
        terminal = [e for e in rows if not e["status"].startswith("subtest-")]
        if len(terminal) > 1 or not terminal and not any(e["status"] == "subtest-failed" for e in rows):
            raise ValueError("selected test has no conclusive outcome")
    terminal = [e for e in events if not e["status"].startswith("subtest-")]
    strict = (len(terminal) == len(expected_ids) and all(e["status"] == "passed" for e in terminal)
              and not any(e["status"] == "subtest-failed" for e in events))
    if (type(result["strict_pass"]) is not bool or result["strict_pass"] != strict
            or type(result["exit"]) is not int or result["exit"] != (0 if strict else 1)):
        raise ValueError("runner outcome contradicts actual selected outcomes")
    captured = result["capture"].encode()
    if (len(captured) > selection["limits"]["capture_bytes"]
            or hashlib.sha256(captured).hexdigest() != result["capture_sha256"]):
        raise ValueError("test-output integrity/bound differs")
    imports = result["imported"]
    if not isinstance(imports, list) or not imports:
        raise ValueError("actual candidate import evidence missing")
    for item in imports:
        if item["path"] not in manifest or item["sha256"] != manifest[item["path"]]["sha256"]:
            raise ValueError("candidate import evidence differs from actual source")
    imported_paths = {r["path"] for r in imports}
    if any(t["path"] not in imported_paths for t in selection["tests"]):
        raise ValueError("selected source not actually imported")
    runner = result["runner"]
    if (type(runner["pid"]) is not int or runner["pid"] <= 0
            or type(runner["start_ticks"]) is not int or runner["start_ticks"] <= 0
            or runner["pid"] == os.getpid() or runner["python_threads_at_completion"] != 1
            or runner["boundary"] != selection["resource_boundary"]):
        raise ValueError("original resource identity/closure missing")
    # Only the exact original PID handed back by the pinned runner is queried.
    # Permission/read failures are UNKNOWN; PID reuse is not the original process.
    try:
        current = Path(f"/proc/{runner['pid']}/stat").read_text()
    except FileNotFoundError:
        pass
    else:
        current_start = int(current.rsplit(")", 1)[1].split()[19])
        if current_start == runner["start_ticks"]:
            raise ValueError("actual original runner still present")
    # Success and known failure share this exact COMPLETE token. Outcome remains
    # in the captured actual runner report/exit; this token cannot mean PASS.
    completion = {"schema": "ordinary-qa-readback538-v1", "selection_sha256": SELECTION_SHA256,
        "source": source, "selected_ids": expected_ids, "completed_tests": len(expected_ids),
        "outcome": "validated-in-actual-runner-report-and-exit",
        "resource_boundary": selection["resource_boundary"], "original_runner_not_live": True}
    sys.stdout.write(encode(completion) + "\n")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except BaseException as exc:
        sys.stderr.write("QA_READBACK_INCOMPLETE:" + type(exc).__name__ + "\n")
        code = 2
    sys.exit(code)
