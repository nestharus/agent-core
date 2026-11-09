"""One synchronous candidate observation, exclusively retained before stdout."""
import importlib
import os
from pathlib import Path
import sys
from common import CANDIDATE, encode, exclusive, load, require
from behavior import observe


def run(instance, pin):
    m = load(instance, pin)
    output = Path(m['output'])
    # No candidate import or effect before exclusive output ownership.
    output.mkdir(mode=0o700, exist_ok=False)
    require(not (Path.cwd() / '.git').exists(), 'Git must be hidden in candidate namespace')
    # Existing namespace clears the environment; use no account lookup/profile.
    os.environ['HOME'] = '/fictional-ordinary-home'
    sys.path.insert(0, str(Path.cwd() / 'tools/coordinator-runtime'))
    c = importlib.import_module('coordinator_runtime.contracts')
    require(Path(c.__file__) == Path.cwd() / 'tools/coordinator-runtime/coordinator_runtime/contracts.py', 'foreign candidate import')
    observations = observe(c, output)
    # Prove both candidate aliases are read-only with a new file, never an existing body.
    protection = {}
    for name, root in (('cwd', Path.cwd()), ('retained', Path(m['export']))):
        try:
            exclusive(root / ('ordinary-qa-protection-' + m['run_id']), b'forbidden\n')
        except PermissionError:
            protection[name] = 'read-only'
        except OSError as exc:
            import errno
            if exc.errno != errno.EROFS:
                raise
            protection[name] = 'read-only'
        else:
            raise RuntimeError('candidate alias unexpectedly writable; retain failed fixture')
    modules = sorted(name for name in sys.modules if name == 'coordinator_runtime' or name.startswith('coordinator_runtime.'))
    require(modules == ['coordinator_runtime', 'coordinator_runtime.contracts'], 'undeclared candidate import')
    exclusive(output / 'OBSERVATIONS.json', encode({
        'version': 1, 'run_id': m['run_id'], 'manifest_sha256': pin,
        'candidate_files': CANDIDATE, 'complete': True, 'observations': observations,
        'namespace': {'cwd': str(Path.cwd()), 'git_hidden': True, 'aliases': protection},
        'modules': modules, 'descendants_started': 0}))
    print('ordinary1141b observations retained; separate readback required')
