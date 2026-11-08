"""Portable unittest procedure data, not runtime authority or an exporter."""
import hashlib
import json
import os
from pathlib import Path
import stat

REGRESSIONS = [
    'test_budget_context1021', 'test_future_boundaries1014',
    'test_integration1012', 'test_future_software1008', 'test_source_duty1009',
    'test_source_continuity688.Continuity.test_exact_eight_module_ceiling_accepts_local_integration_and_store',
    'test_source_continuity688.Continuity.test_exact_delta_does_not_expand_modules_location_pool_or_dependencies',
]
SEAMS = ['fictional principals, authority, clocks and collected native/model answers in candidate tests',
         'support.fixture_publication uses the declared five-file /sdk composition',
         '/public/caller.py is inert public fixture input, never a provider',
         'old704 production pins describe public historical code, not physical runtime state']


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def canonical(path):
    p = Path(path)
    require(p.is_absolute() and str(p) == os.path.normpath(str(p)), 'canonical absolute path required')
    return p


def plain(path):
    p = canonical(path)
    for q in [*reversed(p.parents), p]:
        require(not stat.S_ISLNK(q.lstat().st_mode), 'symlink operand refused')
    return p


def relative(path):
    p = Path(path)
    require(not p.is_absolute() and str(p) == path and '..' not in p.parts
            and not {'.git', 'AGENTS.md', 'WORK_LOG.md', 'runs', 'captures', '__pycache__'}.intersection(p.parts),
            'unsupported relative input/output scope')
    return p


def file_pin(path):
    p = plain(path)
    s = p.stat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'ordinary singly owned file required')
    body = p.read_bytes()
    require(len(body) == s.st_size, 'input changed during capture')
    return {'bytes': len(body), 'sha256': sha(body)}


def verify_pin(path, pin):
    require(file_pin(path) == pin, 'source/input/tool/script identity mismatch: '+str(path))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')


def entry_script(module, directory, manifest_hash):
    return ('import sys\nif len(sys.argv) != 1: raise SystemExit("no runner arguments supported")\n'
            'from '+module+' import main\nmain('+repr(directory)+', '+repr(manifest_hash)+')\n')


def commands_for(m, manifest_hash):
    commands = {}
    for role, module in [('command', 'execution'), ('readback', 'readback')]:
        commands[role] = {'argv': [m['python'], '-B', m['instance']+'/'+role+'_entry.py'],
                          'executable_sha256': m['tools'][m['python']]['sha256'],
                          'script_sha256': sha(entry_script(module, m['instance'], manifest_hash).encode())}
    commands['manifest_sha256'] = manifest_hash
    commands['command']['stdout'] = json.dumps({'exit': 0, 'complete': True, 'output': m['output']})+'\n'
    commands['readback']['stdout'] = 'portable QA1047: declared tests and retained effects verified\n'
    commands['public_executables'] = {role: {'path': m['python'], **m['tools'][m['python']]}
                                       for role in ('command', 'readback')}
    return commands


def load_instance(directory, expected):
    d = plain(directory)
    body = plain(d/'manifest.json').read_bytes()
    require(sha(body) == expected, 'procedure instance changed')
    m = json.loads(body)
    require(m['version'] == 'portable-unittest1047-v1', 'unsupported procedure version')
    require(str(d) == m['instance'], 'wrong procedure instance')
    for rel, pin in m['scripts'].items():
        verify_pin(d/relative(rel), pin)
    for name, pin in m['tools'].items():
        verify_pin(name, pin)
    return m


def verify_inputs(m):
    c = plain(m['candidate'])
    require(Path.cwd() == c, 'actual admitted candidate CWD required')
    require(not (c/'.git').exists(), 'candidate must be an export without .git')
    for rel, pin in m['candidate_files'].items():
        verify_pin(c/relative(rel), pin)
    d = Path(m['instance'])
    for rel, pin in m['inputs'].items():
        verify_pin(d/relative(rel), pin)
    expected = commands_for(m, sha(plain(d/'manifest.json').read_bytes()))
    require(json.loads(plain(d/'COMMANDS.json').read_text()) == expected,
            'derived command input identity mismatch')
    for role in ('command', 'readback'):
        require(file_pin(d/(role+'_entry.py'))['sha256'] == expected[role]['script_sha256'],
                'derived entry script identity mismatch')


def output_root(m):
    out = plain(m['output'])
    require(out.stat().st_uid == os.getuid() and out.stat().st_mode & 0o077 == 0,
            'private owned output required')
    require(json.loads(plain(out/'OWNER.json').read_text()) ==
            {'instance': m['instance'], 'run_id': m['run_id']}, 'wrong output ownership')
    return out
