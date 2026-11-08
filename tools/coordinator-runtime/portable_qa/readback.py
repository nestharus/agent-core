"""Separate retained outcome/source/resource/effect oracle. No producer pass flag."""
import json
from pathlib import Path
import re
import sqlite3
import os
import stat

from common import (file_pin, load_instance, output_root, plain, relative, require,
                    sha, verify_inputs)
from execution import sandbox


def main(directory, expected):
    m = load_instance(directory, expected)
    verify_inputs(m)
    out = output_root(m)
    r = json.loads(plain(out/'execution.json').read_text())
    body = plain(out/'transcript.txt').read_bytes()
    require(r['manifest_sha256'] == expected and r['run_id'] == m['run_id'] and r['argv'] == sandbox(m),
            'stale/wrong execution binding')
    require(r['exit'] == 0 and r['reason'] is None and r['complete'] is True,
            'failed/incomplete execution')
    require(len(body) == r['observed_output_bytes'] == r['retained_output_bytes']
            and len(body) <= m['limits']['output_bytes'] and sha(body) == r['transcript_sha256'],
            'incomplete/altered retained output')
    events = [json.loads(line) for line in plain(out/'events.jsonl').read_text().splitlines()]
    ids = sorted(m['expected_ids'])
    require(events[0] == {'kind': 'scope', 'ids': ids, 'read_only': True, 'seams': m['seams']}, 'wrong declared scope')
    require([e['id'] for e in events if e['kind'] == 'start'] == ids, 'missing/duplicate/wrong test start')
    require([e['id'] for e in events if e['kind'] == 'success'] == ids, 'failed/skipped/missing test success')
    require(len(events) == 2+2*len(ids) and events[-1]['kind'] == 'finish'
            and events[-1]['tests'] == len(ids), 'incomplete/extra test outcomes')
    modules = events[-1]['modules']
    require(modules and modules.get('coordinator_runtime.store') == 'tools/coordinator-runtime/coordinator_runtime/store.py',
            'actual candidate runtime was not exercised')
    for name, rel in modules.items():
        require(rel in m['candidate_files'], 'wrong loaded source')
    for test in ids:
        require(modules.get(test.split('.')[0]) == 'tools/coordinator-runtime/tests/'+test.split('.')[0]+'.py',
                'test did not load from candidate')
    text = body.decode('utf8')
    require(re.findall(r'\nRan ([0-9]+) tests? in [0-9.]+s\n\nOK\n', text) == [str(len(ids))],
            'retained unittest output is not a complete successful run')
    # These are actual retained fictional effects, checked directly without
    # importing candidate code or believing an assertion/producer success label.
    for effect in m['effects']:
        path = plain(out/relative(effect['path']))
        require(path.is_relative_to(out), 'effect outside output ownership')
        if effect['kind'] == 'file':
            require(path.read_bytes() == effect['utf8'].encode(), 'wrong retained file effect')
        else:
            with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
                db.execute('PRAGMA query_only=ON')
                require([list(row) for row in db.execute(effect['query'])] == effect['rows'], 'wrong retained journal effect')
    count = total = 0
    pending = [out]
    while pending:
        directory = pending.pop()
        for p in directory.iterdir():
            s = p.lstat()
            require(s.st_uid == os.getuid(), 'foreign output ownership')
            require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode),
                    'unsupported retained output type')
            # Existing refusal tests retain fictional symlinks. Never follow
            # them or acquire their target metadata/body, including accounting.
            if stat.S_ISDIR(s.st_mode):
                pending.append(p)
            count += 1
            total += s.st_size
            require(count <= m['limits']['effect_files'] and total <= m['limits']['effect_bytes'],
                    'owned retained output exceeds declared resource scope')
    print('portable QA1047: declared tests and retained effects verified')
