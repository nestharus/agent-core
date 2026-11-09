"""Prepare fresh inert package files. Not a runtime API or an admission tool."""
import argparse
import os
from pathlib import Path
import uuid
from common import BASE, TREE, PARENT, CANDIDATE, SCRIPTS, TOOLS, encode, exclusive, plain, record, require


def prepare(candidate, area):
    candidate = plain(candidate, True)
    area = Path(area)
    require(area.is_absolute() and '..' not in area.parts and not area.exists(), 'new absolute owned allocation required')
    plain(area.parent, True)
    free = os.statvfs(area.parent)
    require(free.f_bavail * free.f_frsize >= 100 * 1024**3 + 16 * 1024**2 and free.f_favail >= 1000256,
            'leave 100GiB/1M before package allocation')
    for name, expected in CANDIDATE.items():
        require(record(candidate / name) == expected, 'released candidate differs; final rebind/revalidation required')
    for name, expected in TOOLS.items():
        require(record(name, 32 * 1024 * 1024) == expected, 'public tools differ')
    area.mkdir(mode=0o700)
    instance = area / 'instance'; instance.mkdir(mode=0o700)
    writable = area / 'writable'; writable.mkdir(mode=0o700)
    source = Path(__file__).absolute().parent
    for name in SCRIPTS:
        exclusive(instance / name, (source / name).read_bytes())
    scripts = {name: record(instance / name) for name in SCRIPTS}
    manifest = {'version': 2, 'component_release': {'base': BASE, 'tree': TREE, 'parent': PARENT},
                'run_id': uuid.uuid4().hex, 'candidate': str(candidate),
                'candidate_files': CANDIDATE, 'scripts': scripts, 'tools': TOOLS,
                'output': str(writable / 'result')}
    exclusive(instance / 'MANIFEST.json', encode(manifest))
    pin = record(instance / 'MANIFEST.json')['sha256']
    # Script-only argv, with dependency verification before any package import.
    for name, module, function in (('command_entry.py', 'runner', 'run'), ('readback_entry.py', 'readback', 'readback')):
        body = ('import hashlib, pathlib, sys\n'
                f'instance = pathlib.Path({str(instance)!r})\n'
                f'pins = {scripts!r}\n'
                'for name, pin in pins.items():\n'
                ' p = instance / name\n'
                ' if p.is_symlink() or p.stat().st_size != pin["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest() != pin["sha256"]:\n'
                '  raise RuntimeError("package dependency identity changed")\n'
                'sys.path.insert(0, str(instance))\n'
                f'from {module} import {function}\n'
                f'{function}(instance, {pin!r})\n').encode()
        exclusive(instance / name, body)
    commands = {'command': {'argv': ['/usr/bin/python3.12', '-B', str(instance / 'command_entry.py')],
                            'executable_sha256': TOOLS['/usr/bin/python3.12']['sha256'],
                            'script_sha256': record(instance / 'command_entry.py')['sha256'],
                            'stdout': 'ordinary1141b observations retained; separate readback required\n'},
                'readback': {'argv': ['/usr/bin/python3.12', '-B', str(instance / 'readback_entry.py')],
                             'executable_sha256': TOOLS['/usr/bin/python3.12']['sha256'],
                             'script_sha256': record(instance / 'readback_entry.py')['sha256'],
                             'stdout': 'ordinary1152 readback: 31 contract cases and CWD witness verified; outer source association and acceptance owed\n'},
                'manifest_sha256': pin,
                'public_executables': {role: {'path': '/usr/bin/python3.12', **TOOLS['/usr/bin/python3.12']}
                                       for role in ('command', 'readback')}}
    exclusive(instance / 'COMMANDS.json', encode(commands))
    return manifest, commands


def namespace(m, commands, role, export):
    instance = str(Path(commands[role]['argv'][2]).parent)
    return ['/usr/bin/bwrap', '--unshare-net', '--die-with-parent', '--new-session',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib',
            '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
            '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
            '--ro-bind', instance, instance,
            '--bind', str(Path(m['output']).parent), str(Path(m['output']).parent),
            '--ro-bind', str(export), str(export), '--ro-bind', str(export), m['candidate'],
            '--chdir', m['candidate'], '--', *commands[role]['argv']]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True); parser.add_argument('--new-area', required=True)
    args = parser.parse_args()
    m, commands = prepare(args.candidate, args.new_area)
    print(encode({'manifest': m, 'commands': commands}).decode(), end='')
