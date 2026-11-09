"""Finite public program reading and named trusted runtime admission.

This prospective representation extends existing source-reading authority only.
It grants no execution, does not hash-close runtime directories, and cannot
replace the later genuine future-only capability/grant/configuration checks.
"""
import os
from pathlib import Path
import re
import stat

from .contracts import Refusal
from .resource_scopes import root
from .public_program import identity

VERSION = 'public-program-runtime-read-v1'
RUNTIME_DIRECTORIES = frozenset(('/usr/lib/python3.12',
    '/usr/lib/x86_64-linux-gnu', '/usr/lib64'))
PROGRAM_FIELDS = {'path', 'bytes', 'max_bytes', 'sha256'}


def public_path(value, exclusions):
    path = root(value, exclusions, metadata=False)
    if (str(path) != value or set(path.parts) & {'.ssh', '.aws', '.config', '.local'}
            or any(p.startswith(('.codex', '.claude')) for p in path.parts)):
        raise Refusal('exact public operand required before metadata')
    return path


def program_declaration(value, exclusions=()):
    if (not isinstance(value, dict) or set(value) != PROGRAM_FIELDS
            or not isinstance(value['sha256'], str)
            or not re.fullmatch('[0-9a-f]{64}', value['sha256'])
            or type(value['bytes']) is not int or type(value['max_bytes']) is not int
            or not 0 < value['bytes'] <= value['max_bytes'] <= 1024**3):
        raise Refusal('exact finite complete public executable identity required')
    public_path(value['path'], exclusions)


def trusted_directory(value, exclusions=()):
    if value not in RUNTIME_DIRECTORIES:
        raise Refusal('only explicitly named public runtime directories; no broad OS root')
    path = public_path(value, exclusions)
    # No traversal/tree hashing. The complete named directory is deliberately
    # trusted; adjacent finite pins do not establish immutable OS-tree identity.
    root(str(path), exclusions)
    for part in (path, *path.parents):
        info = part.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise Refusal('public runtime directory chain must remain root-owned and nonwritable')


def check_program(value, exclusions=(), *, trusted=False):
    program_declaration(value, exclusions)
    if trusted:
        path = root(value['path'], exclusions)
        for part in (path, *path.parents):
            info = part.stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise Refusal('public helper chain must remain root-owned and nonwritable')
    result = identity(value['path'], value['bytes'], value['max_bytes'], exclusions)
    if result['sha256'] != value['sha256']:
        raise Refusal('selected public program changed')
    return result


def helper_declaration(value):
    if (not isinstance(value, dict) or set(value) != PROGRAM_FIELDS | {'runtime_directories', 'startup'}
            or value['path'] != '/usr/bin/python3.12'
            or value['startup'] != 'python-isolated-no-site-no-bytecode'
            or not isinstance(value['runtime_directories'], list)
            or set(value['runtime_directories']) != RUNTIME_DIRECTORIES
            or len(value['runtime_directories']) != len(RUNTIME_DIRECTORIES)):
        raise Refusal('canonical public Python helper with explicit isolated startup/runtime required')
    program_declaration({k:value[k] for k in PROGRAM_FIELDS})


def check_helper(value, exclusions):
    helper_declaration(value)
    operands = [value['path'], *value['runtime_directories']]
    for path in operands:
        public_path(path, exclusions)
    observed = check_program({k:value[k] for k in PROGRAM_FIELDS}, exclusions, trusted=True)
    for directory in value['runtime_directories']:
        trusted_directory(directory, exclusions)
    return observed


def extend(runtime, original, candidate, entries):
    """Draft/apply binding; unchanged ProcessingBoard authenticates real grants.

    A NEW future capability must select the resulting exact configuration and
    source before any use. This is no actual capability ID, lease or consent.
    Execute-only QA cannot acquire source-reading rights through this route.
    """
    from .configuration import read_ceiling_extensions
    if not isinstance(entries, dict) or set(entries) - set(original['tasks']):
        raise Refusal('public runtime reads require exact existing tasks')
    exclusions = candidate.get('artifact_exclusions', [])
    for name, entry in entries.items():
        if (not isinstance(entry, dict) or set(entry) !=
                {'version', 'binding', 'programs', 'runtime_directories', 'capability'}
                or entry['version'] != VERSION or entry['capability'] != 'future-only-new'
                or 'read-source' not in original['tasks'][name]['effect_authority']['operations']
                or not isinstance(entry['binding'], dict) or not entry['binding'].get('source')):
            raise Refusal('existing source-read authority and exact future-only source binding required')
        programs, directories = entry['programs'], entry['runtime_directories']
        if (not isinstance(programs, list) or not 1 <= len(programs) <= 8
                or not isinstance(directories, list) or len(directories) > 16
                or len({p.get('path') for p in programs if isinstance(p, dict)}) != len(programs)
                or len({d.get('path') for d in directories if isinstance(d, dict)}) != len(directories)):
            raise Refusal('finite distinct program/runtime operands required')
        for program in programs:
            program_declaration(program, exclusions)
        if sum(p['max_bytes'] for p in programs) > 2*1024**3:
            raise Refusal('finite total public program identity allowance exceeded')
        for directory in directories:
            if (not isinstance(directory, dict) or set(directory) != {'path', 'trust'}
                    or directory['trust'] != 'named-public-runtime-directory'
                    or directory['path'] not in RUNTIME_DIRECTORIES):
                raise Refusal('explicit named public runtime trust required, not a hash-closed OS tree')
            public_path(directory['path'], exclusions)
        # The existing small-file route binds current configuration/owner/stopped
        # original grant and exact immutable source. Its byte caps stay unchanged.
        read_ceiling_extensions(runtime, original, candidate, {name:entry['binding']})
        for program in programs:
            check_program(program, exclusions)
        for directory in directories:
            trusted_directory(directory['path'], exclusions)
        paths = [p['path'] for p in programs] + [d['path'] for d in directories]
        task = candidate['tasks'][name]
        task['effect_authority']['read_roots'] = list(dict.fromkeys([
            *task['effect_authority']['read_roots'], *paths]))
        if task.get('package_narrowing'):
            task['scope_roots'] = list(dict.fromkeys([*task['scope_roots'], *paths]))
