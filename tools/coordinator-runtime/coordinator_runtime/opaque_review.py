"""Explicit public opaque Reviews integration; no native-root correspondence.

The shared launcher owns exec processes and public thread continuity. This
adapter owns current task admission, exact source/method/history export, and
the existing sole Reviews proposal route. It never certifies a native root.
"""
import json
from pathlib import Path
from types import ModuleType

from .contracts import Refusal, encode, required_text
from .custody import read_file

VERSION = 'opaque-cli-v1'
BINDING = {'model': 'gpt-xhigh', 'provider': 'opaque', 'effort': 'opaque'}
SITUATION = {'actors', 'environment', 'goals', 'conflicts', 'constraints'}


def launcher_path():
    return Path(__file__).parents[2] / 'direct-child' / 'review_context.py'


def launcher(policy):
    from .reviews import sha
    body, _ = read_file(launcher_path(), 256 * 1024)
    if sha(body) != policy.get('launcher_sha256'):
        raise Refusal('selected public opaque launcher changed; no substitute')
    module = ModuleType('owned_public_review_context')
    module.__file__ = str(launcher_path())
    exec(compile(body, str(launcher_path()), 'exec'), module.__dict__)
    return module


def binding(task):
    if (task.get('execution') != 'owner' or task.get('binding') != BINDING
            or task.get('role') != 'Reviews' or task.get('phase') != 'proposer'
            or task.get('effects') != 'none' or task.get('sandbox') != 'read-only'
            or task.get('network') or task.get('effect_authority', {}).get('write_roots')):
        raise Refusal('opaque CLI requires the exact selected read-only owner Reviews binding')
    return dict(BINDING)


def validate(policy):
    fields = {'transport', 'launcher_sha256', 'deadline', 'method', 'method_files', 'method_closure', 'components'}
    if set(policy) != fields or policy['transport'] != VERSION or type(policy['deadline']) is not int or not 1 <= policy['deadline'] <= 7200:
        raise Refusal('exact opaque CLI policy and whole-context deadline required')
    from .method_closure import VERSION as CLOSURE
    if policy['method_closure'] != CLOSURE:
        raise Refusal('opaque Reviews requires complete current unified definition closure')
    launcher(policy)
    for material in policy['components'].values():
        situation = material.get('situation')
        if not isinstance(situation, dict) or set(situation) != SITUATION:
            raise Refusal('authentic actors/environment/goals/conflicts/constraints required')
        for name in SITUATION:
            required_text(situation[name], 'situated independent inquiry ' + name, 16000)


def snapshot(policy, acquired):
    """No path from the reviewer is an acquisition operand."""
    from .reviews import git, sha
    result = []
    paths = [(acquired['history'], acquired['history_sha256']), *acquired['prior_histories'].items()]
    for path, expected in paths:
        if Path(path).exists():
            body, _ = read_file(Path(path), 32 * 1024 * 1024)
        else:
            body = b''
        if sha(body) != expected:
            raise Refusal('whole admitted history changed before public snapshot')
        result.append(('history:' + path, body))
    for path, expected in acquired['method_files'].items():
        body, _ = read_file(Path(path), 256 * 1024)
        if sha(body) != expected:
            raise Refusal('selected method changed before public snapshot')
        result.append(('method:' + path, body))
    result.append(('correction-diff', acquired['correction_diff'].encode()))
    for operand, expected in acquired['source'].items():
        body = git(acquired['repository'], 'show', operand)
        if len(body) != expected['bytes'] or sha(body) != expected['sha256']:
            raise Refusal('admitted immutable source differs before public snapshot')
        result.append(('source:' + operand, body))
    return result


def prompt(policy, acquired):
    return (
        'You personally perform the unified static reviewer seat for the actual collecting Work. '
        'gpt-xhigh is an opaque launch reference, not an instruction to launch another seat. '
        'Use the complete current method and every incorporated definition in the snapshot. '
        'ONE history-informed context: read whole history first; return architecture FIRST '
        'through organization, cross-change and purpose, then await continuation in this same context. '
        'The authenticated situation below supplies actors/environment/goals/conflicts/constraints; '
        'challenge premises and constraints when evidence warrants. It prescribes no findings or repairs. '
        'Do not run tests, mutate source, delegate, inspect private settings or acquire outside material. '
        'Return JSON with exactly semantic (DONE/PARTIAL/FAILED/UNKNOWN), summary, report, '
        'history_entry, coverage, stage (architecture/complete). report and history_entry are full '
        'attributable nonempty strings, not receipts. coverage has exactly families (all nine slugs '
        'to full/partial/unread/not-applicable), core_files_not_read (list), observations '
        '(located objects with unique id), answered_ids (the actual supplied IDs), limits (list). '
        'Preserve dissent, causal evidence, counterevidence, uncertainties, and all unfinished work. '
        'Reading labels/counts/hashes are not semantic work. DONE is inquiry status, never acceptance.\n' +
        encode({k: v for k, v in acquired.items() if k != 'commands'}))


def answered(code, receipt, answer, thread, opening):
    return (code == 0 and isinstance(receipt, dict) and receipt.get('transport') == VERSION
            and receipt.get('actual_END') == code and receipt.get('answered') is True
            and receipt.get('capture_complete') is True and receipt.get('errors') == []
            and receipt.get('thread') == thread and receipt.get('turn_completed') == 1
            and receipt.get('turn_failed') is False and receipt.get('lifetime_exceeded') is False
            and type(receipt.get('input')) is int and (receipt['input'] == 0 if opening else receipt['input'] > 0)
            and isinstance(answer, str) and bool(answer.strip()))


async def call(native, runtime, attempt, policy, context, directory, text, opening=False, close=False):
    """Reuse the original collector without inventing live-root ACK/close proof."""
    from .reviews import _existing
    module = launcher(policy)
    await native.collect_pending(runtime)
    owner = native.public_contexts.get(context['handle'])
    if close:
        if owner is None:
            raise Refusal('original public context object unavailable; no store recovery')
        receipt = owner.close(runtime.controller)
        receipt['run'] = context['run']
        return None, receipt, None  # Close starts no process; no invented END0.
    runtime.authorize_launch(attempt)
    binding(runtime.config['tasks'][runtime.job(runtime.attempt(attempt)['job'])['task']])
    acquired = json.loads(runtime.one('SELECT packet FROM review_calls WHERE attempt=?', (attempt,))['packet'])
    items = snapshot(policy, acquired)
    size = sum(len(body) for _, body in items)
    maximum = runtime.config['limits']['max_result_bytes']
    runtime.admit_artifact_write(attempt, size + len(text.encode()) + 2 * maximum +
                                8 * 1024 * 1024 + 1024 * len(items) + 65536, len(items) + 20)
    module.make_directory(directory.parent)
    guard = runtime.execution_pool.admission(context['profile']) if opening else _existing()
    async with guard:
        runtime.authorize_launch(attempt)
        if opening:
            if owner is not None:
                raise Refusal('public context already created; no replay')
            owner = module.Context(context['handle'], context['profile'], runtime.controller,
                                   policy['deadline'], native.originals, clock=runtime.clock)
            owner.created = context['created']
            native.public_contexts[context['handle']] = owner
        if (owner is None or owner.thread != context['run'] or owner.profile != context['profile']
                or owner.collector != runtime.controller or owner.lifetime != policy['deadline']):
            raise Refusal('original public context/account/lifetime unavailable or changed')
        with runtime.tx():
            runtime.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?", (attempt,))

        def started():
            if runtime.attempt(attempt)['begin'] is None:
                runtime.begin(attempt, {'process_handle': 'owned-asyncio-subprocess',
                    'original_collector': runtime.controller, 'identity_scope': VERSION + '; not native-root END'})

        code, receipt, answer = await owner.turn(directory, items, text,
            collector=runtime.controller, profile=context['profile'],
            current_authority=lambda: runtime.authorize_launch(attempt),
            current_profiles=[context['profile']] if opening else [],
            publish=lambda observation: runtime.record_original_end(attempt, observation),
            maximum=maximum, capture_max=4*1024*1024,
            shutdown=runtime.config['deadlines']['shutdown'], started=started)
    receipt['run'] = receipt['thread']
    return code, receipt, answer


def proof(runtime, job, attempt, call, context, actual):
    """Current CLI proof is useful to generic integration, never native proof."""
    if (not context or context['route'] != VERSION or not context['run']
            or attempt['session'] != context['run'] or attempt['controller'] != call['collector']
            or attempt['profile'] != context['profile']
            or json.loads(attempt['binding']) != BINDING or attempt['begin'] is None
            or attempt['ended'] is None or attempt['collected'] is None or attempt['exit'] != 0
            or attempt['capture'] != 'complete' or attempt['error'] or not actual
            or any(not answered(t['actual_END'], t['receipt'], t.get('full_answer'), context['run'],
                                t['receipt'].get('input') == 0)
                   or t['receipt'].get('profile') != context['profile']
                   or t['receipt'].get('collector') != context['collector'] for t in actual)):
        raise Refusal('actual opaque context/original/material return incomplete')
    binding(runtime.config['tasks'][job['task']])
    policy = runtime.processing.current()[1]['service']['reviews'][job['task']]
    launcher(policy)
    return dict(kind='selected-opaque-cli-review', component=call['component'], run=context['run'],
                collector=call['collector'], attempt=attempt['id'], calls=actual,
                material=json.loads(call['packet']), native_owner_execution=False,
                provider_session='public CLI thread; no underlying model attestation')
