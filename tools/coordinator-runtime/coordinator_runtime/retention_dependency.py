"""Exact cooperative retention provider closure, separate from the Board SDK.

No task scope, provider selection or execution authority is granted here. The
interpreter/standard library is trusted; provider-local Python imports must all
resolve to captured, pinned modules, including deferred and circular imports.
"""
import builtins
import hashlib
import inspect
from pathlib import Path
import re
import sys
import types

from .contracts import Refusal

# Dependency order for the inspected retention-same-inode-v1 interface. This is
# deliberately closed, rather than a recursive import/path discovery mechanism.
FILES = ('queue_transport.py', 'active_listener.py', 'catalog.py',
         'board_store.py', 'retention.py')
MAX_SOURCE_BYTES = 2 * 1024 * 1024


def validate_pins(pins):
    if (not isinstance(pins, dict) or set(pins) != set(FILES)
            or any(not isinstance(p, str) or re.fullmatch('[0-9a-f]{64}', p) is None
                   for p in pins.values())):
        raise Refusal('exact five-file retention dependency source_pins required')


def capture(directory, exclusions):
    from .configuration import _path
    from .custody import read_file
    sources = {}
    for name in FILES:
        path = _path(str(Path(directory) / name), exclusions)
        try:
            sources[name] = (path, read_file(path, MAX_SOURCE_BYTES)[0])
        except OSError as exc:
            raise Refusal('selected retention dependency unavailable: ' + name) from exc
    return sources


def source_pins(directory, exclusions):
    return {name: hashlib.sha256(body).hexdigest()
            for name, (_, body) in capture(directory, exclusions).items()}


def verify(sources, pins):
    validate_pins(pins)
    for name, (_, body) in sources.items():
        if hashlib.sha256(body).hexdigest() != pins[name]:
            raise Refusal('selected retention dependency source changed: ' + name)


def load(directory, pins, exclusions):
    """Compile verified snapshots, never re-read provider code through imports."""
    validate_pins(pins)
    sources = capture(directory, exclusions)
    verify(sources, pins)  # Check the whole closure before executing any module.
    modules = {}
    prior = {}
    for name, (path, _) in sources.items():
        stem = Path(name).stem
        identity = hashlib.sha256((str(path) + pins[name]).encode()).hexdigest()
        module = types.ModuleType('coordinator_retention_' + stem + '_' + identity)
        module.__file__ = str(path)
        module.__package__ = ''
        modules[stem] = module
        prior[module.__name__] = sys.modules.get(module.__name__)

    def selected_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and name in modules:
            return modules[name]
        if level != 0 or name.split('.')[0] not in sys.stdlib_module_names:
            raise Refusal('retention import outside exact dependency closure: ' + name)
        return builtins.__import__(name, globals, locals, fromlist, level)

    try:
        for module in modules.values():
            sys.modules[module.__name__] = module  # dataclasses/annotations
            module.__builtins__ = {**vars(builtins), '__import__': selected_import}
        for name, (path, body) in sources.items():
            module = modules[Path(name).stem]
            exec(compile(body, str(path), 'exec'), module.__dict__)
            module.__coordinator_source_sha256__ = hashlib.sha256(body).hexdigest()
        for name, (path, _) in sources.items():
            module = modules[Path(name).stem]
            if (module.__file__ != str(path)
                    or module.__coordinator_source_sha256__ != pins[name]):
                raise Refusal('compiled retention dependency identity differs: ' + name)
        provider = modules['retention']
        if getattr(provider, 'SOURCE_SHA256', pins['retention.py']) != pins['retention.py']:
            raise Refusal('retention source self-read differs from compiled identity')
        try:
            inspect.signature(provider.snapshot_lock).bind()
        except (AttributeError, TypeError, ValueError) as exc:
            raise Refusal('selected retention lacks the zero-argument snapshot_lock interface') from exc
        return provider
    except BaseException:
        for module in modules.values():
            old = prior[module.__name__]
            if old is None:
                sys.modules.pop(module.__name__, None)
            else:
                sys.modules[module.__name__] = old
        raise
