"""Shared isolated adapter primitives. No import-time provider or state access."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

CORE_SHA256 = "9ad637dd6a3677b17894726e9f6e655f6f1b19e2ce8d9b3f4725fb18cfb697a0"
BOARD = "cdb7c432-a0a0-4fc3-aba4-068b20a02c88"
RECIPIENT = "01a18bb3-2d8f-7eb0-a1ef-31b62ae96198"
MAX_JSON = 2 * 1024**2

class AdapterError(ValueError):
    pass

def need(condition, reason):
    if not condition:
        raise AdapterError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def exact_json(raw):
    need(len(raw) <= MAX_JSON, "metadata-byte-budget")
    def pairs(items):
        out = {}
        for k, v in items:
            need(k not in out, "duplicate-json-key")
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=pairs)

def private_write(path, raw):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())

def record(path, value):
    private_write(path, json.dumps(value, sort_keys=True, indent=2).encode())

def load_core(path):
    """Caller freezes exact file and aliases kernel RO before Python startup."""
    path = Path(path)
    need(path.is_absolute(), "literal-core-path-required")
    raw = path.read_bytes()
    need(sha(raw) == CORE_SHA256, "core-compatibility-hash-mismatch")
    spec = importlib.util.spec_from_file_location("branch_stack_fixed_core", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (2*1024**2, 2*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512*1024**2, 512*1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

class ProcessCapture:
    """Private complete stdout/stderr files precede any technical projection.

    A killed producer's files are its complete observed streams, never a success.
    Only a trusted program supplies argv/env; no shell and no inherited environment.
    """
    def __init__(self, directory, *, timeout=10, max_launches=300):
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700)
        need(0 < timeout <= 20, "process-time-budget")
        self.timeout = timeout
        self.max_launches = max_launches
        self.ends = []

    def run(self, argv, *, env, input_bytes=None, cwd=None):
        need(len(self.ends) < self.max_launches, "launch-retention-budget")
        folder = self.directory / ("%04d" % len(self.ends))
        folder.mkdir(mode=0o700)
        record(folder/"launch.json", {"argv": list(argv), "env": env, "cwd": str(cwd) if cwd else None,
                                     "timeout": self.timeout})
        private_write(folder/"stdin.bin", b"" if input_bytes is None else input_bytes)
        started = time.monotonic()
        timed_out = False
        code = None
        error = None
        with os.fdopen(os.open(folder/"stdout.bin", os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), "wb") as out, \
             os.fdopen(os.open(folder/"stderr.bin", os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), "wb") as err:
            try:
                p = subprocess.Popen(list(argv), stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                                     stdout=out, stderr=err, env=env, cwd=cwd, shell=False,
                                     start_new_session=True, preexec_fn=limits)
                try:
                    p.communicate(input=input_bytes, timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(p.pid, signal.SIGKILL)
                    p.communicate()
                code = p.returncode
            except OSError as exc:
                error = type(exc).__name__
        result = {"exit_code": code, "timed_out": timed_out, "launch_error": error,
                  "elapsed_seconds": time.monotonic()-started}
        record(folder/"result.json", result)
        self.ends.append(result)
        return dict(result, stdout=(folder/"stdout.bin").read_bytes(),
                    stderr=(folder/"stderr.bin").read_bytes(), capture=str(folder))

def git_environment(home, objects=None):
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "XDG_CONFIG_HOME": str(home),
           "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_NO_LAZY_FETCH": "1", "GIT_PROTOCOL_FROM_USER": "0",
           "GIT_ALLOW_PROTOCOL": "", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_CONFIG_COUNT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
           "GIT_CONFIG_SYSTEM": "/dev/null"}
    if objects is not None:
        env["GIT_OBJECT_DIRECTORY"] = str(objects)
    return env

