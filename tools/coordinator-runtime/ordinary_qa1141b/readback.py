"""Separate observation reader; never imports or reruns candidate behavior."""
from pathlib import Path
from common import CANDIDATE, encode, exclusive, load, load_json, record, require


def readback(instance, pin):
    m = load(instance, pin)
    output = Path(m['output'])
    evidence = output / 'OBSERVATIONS.json'
    observed = load_json(evidence)
    oracle = load_json(Path(instance) / 'ORACLE.json')
    require(set(observed) == {'version', 'run_id', 'manifest_sha256', 'candidate_files', 'complete',
                              'observations', 'namespace', 'modules', 'descendants_started'}, 'observation schema changed')
    require(observed['version'] == 1 and observed['run_id'] == m['run_id'] and observed['manifest_sha256'] == pin,
            'observation belongs to a different original instance')
    require(observed['complete'] is True and observed['candidate_files'] == CANDIDATE, 'incomplete/source-mismatched observation')
    require(observed['modules'] == ['coordinator_runtime', 'coordinator_runtime.contracts'] and observed['descendants_started'] == 0,
            'undeclared candidate/descendant closure')
    require(observed['namespace'] == {'cwd': m['candidate'], 'git_hidden': True,
            'aliases': {'cwd': 'read-only'}}, 'namespace observation incomplete')
    require(encode(observed['observations']) == encode(oracle['expected']), 'candidate behavior differs from independent oracle')
    require(len(observed['observations']) == oracle['case_count'], 'missing/extra case')
    # Exclusive receipt prevents a stale readback from silently being reused.
    exclusive(output / 'READBACK.json', encode({'version': 1, 'run_id': m['run_id'],
        'manifest_sha256': pin, 'observation': record(evidence), 'cases': sorted(observed['observations']),
        'accepted': False, 'processing_complete': False,
        'meaning': 'bounded candidate contract observations match; actual independent QA decision still owed'}))
    print('ordinary1152 readback: 31 contract cases and CWD witness verified; outer source association and acceptance owed')
