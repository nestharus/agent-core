"""Offline constructor. Caller supplies complete admitted concrete operands.

No Git, discovery of candidate files, operational selection, or provider use.
"""
from pathlib import Path
import re
import secrets

from common import (REGRESSIONS, SEAMS, canonical, file_pin, plain, relative,
                    require, sha, verify_pin, write_json, entry_script, commands_for)
from history import production_history

KEYS = {'candidate', 'candidate_identity', 'candidate_files', 'instance', 'output',
        'tools', 'selected_selectors', 'expected_ids', 'effects', 'historical_files',
        'caller', 'limits', 'scope_rationale'}
BOARD = ('active_listener.py', 'queue_transport.py', 'catalog.py', 'board_store.py')


def validate_effect(effect):
    require(effect['kind'] in {'file', 'sqlite'}, 'unsupported effect oracle')
    relative(effect['path'])
    if effect['kind'] == 'file':
        require(set(effect) == {'kind', 'path', 'utf8'}, 'exact file oracle required')
        return
    require(set(effect) == {'kind', 'path', 'query', 'rows'}
            and effect['query'].lstrip().upper().startswith('SELECT '), 'read-only SELECT oracle required')


def prepare(spec):
    require(set(spec) == KEYS, 'complete exact constructor fields required')
    candidate = plain(spec['candidate'])
    require(not (candidate/'.git').exists(), 'constructor needs no-Git candidate export')
    instance, output = canonical(spec['instance']), canonical(spec['output'])
    for a, b in [(instance, candidate), (output, candidate), (instance, output)]:
        require(a != b and not a.is_relative_to(b) and not b.is_relative_to(a), 'overlapping roots refused')
    plain(instance.parent)
    plain(output.parent)
    require(not instance.exists() and not output.exists(), 'fresh instance and output required')
    require(spec['scope_rationale'] and spec['selected_selectors'], 'chosen current behavior scope required')
    identity = spec['candidate_identity']
    require(set(identity) == {'origin', 'ref', 'head', 'tree', 'parents', 'method', 'history', 'changed_paths'},
            'explicit source identity/method/history/changed paths required')
    require(all(identity.values()), 'missing candidate provenance')
    require(set(spec['tools']) == {'python', 'bwrap'}, 'exact Python and sandbox tools required')
    for tool in spec['tools'].values():
        verify_pin(tool['path'], tool['pin'])
    require(spec['tools']['python']['path'] == '/usr/bin/python3.12', 'supported canonical public Python required')
    require(set(spec['limits']) == {'timeout', 'output_bytes', 'effect_bytes', 'effect_files'}, 'finite limits required')
    require(all(type(n) is int and n > 0 for n in spec['limits'].values()), 'positive finite limits required')
    require(spec['effects'], 'substantive retained effect expectations required')
    for e in spec['effects']:
        validate_effect(e)
    ids = spec['expected_ids']
    require(ids and len(ids) == len(set(ids)) and all(re.fullmatch(r'[A-Za-z_][\w.]+', x) for x in ids),
            'nonempty distinct exact expected test identities required')
    for selector in spec['selected_selectors']:
        require(re.fullmatch(r'[A-Za-z_][\w.]+', selector), 'unsupported test selector')
    for rel, pin in spec['candidate_files'].items():
        verify_pin(candidate/relative(rel), pin)
    for name in BOARD:
        require('tools/message-board/'+name in spec['candidate_files'], 'complete board input missing')
    require('tools/coordinator-runtime/tests/fixture_snapshot/retention.py' in spec['candidate_files'], 'retention fixture missing')
    production = {Path(p).name: pin['sha256'] for p, pin in spec['candidate_files'].items()
                  if Path(p).parent.as_posix() == 'tools/coordinator-runtime/coordinator_runtime' and p.endswith('.py')}
    history = production_history(production, spec['historical_files'])
    verify_pin(spec['caller']['path'], spec['caller']['pin'])
    instance.mkdir(mode=0o700)
    (instance/'sdk').mkdir()
    (instance/'public').mkdir()
    for name in BOARD:
        (instance/'sdk'/name).write_bytes((candidate/'tools/message-board'/name).read_bytes())
    (instance/'sdk/retention.py').write_bytes((candidate/'tools/coordinator-runtime/tests/fixture_snapshot/retention.py').read_bytes())
    (instance/'public/caller.py').write_bytes(Path(spec['caller']['path']).read_bytes())
    write_json(instance/'public/production-pins.json', history)
    write_json(instance/'public/exclusions.json', ['/fictional-held-boundary1047/'+str(i) for i in range(71)])
    scripts = {}
    for name in ('common.py', 'execution.py', 'worker.py', 'readback.py'):
        target = instance/name
        target.write_bytes(Path(__file__).with_name(name).read_bytes())
        scripts[name] = file_pin(target)
    inputs = {str(p.relative_to(instance)): file_pin(p) for p in [
        *[instance/'sdk'/n for n in (*BOARD, 'retention.py')],
        *[instance/'public'/n for n in ('caller.py', 'production-pins.json', 'exclusions.json')]]}
    m = {k: spec[k] for k in ('candidate', 'candidate_identity', 'candidate_files', 'instance', 'output',
                             'expected_ids', 'effects', 'limits', 'scope_rationale')}
    m.update(version='portable-unittest1047-v1', run_id=secrets.token_hex(16), scripts=scripts, inputs=inputs,
             tools={v['path']: v['pin'] for v in spec['tools'].values()},
             python=spec['tools']['python']['path'], bwrap=spec['tools']['bwrap']['path'],
             selectors=list(dict.fromkeys(REGRESSIONS+spec['selected_selectors'])), seams=SEAMS,
             input_provenance={'historical_files': spec['historical_files'], 'caller': spec['caller']})
    write_json(instance/'manifest.json', m)
    mh = sha((instance/'manifest.json').read_bytes())
    for role, module in [('command', 'execution'), ('readback', 'readback')]:
        script = instance/(role+'_entry.py')
        # The wrapper pins the complete manifest; tool admission separately pins this wrapper.
        script.write_text(entry_script(module, str(instance), mh))
    commands = commands_for(m, mh)
    write_json(instance/'COMMANDS.json', commands)
    return commands
