"""Case-Root factual disposition of captured software preparation only.

This is not native consent, general effect reconciliation or fresh authority.
The original result/detail and every legacy duty remain untouched. Current
admission, source, collector, resources and effect ceilings are prerequisites.
"""
import json
import subprocess

from .contracts import Refusal, collected_task_result, digest, encode
from . import branches, local_integration, ordinary, processing_admission, resource_scopes

KIND = 'software-read-only-preparation-v1'


def basis(store, job, token, attempt, actor):
    """Bounded positive evidence plus negative checks, in the caller's tx."""
    if not store.db.in_transaction:
        with store.tx():
            return basis(store, job, token, attempt, actor)
    store.require_execution_open(job)
    row = store.job(job, token)
    local_integration.current_sources(store, row)  # Before original bodies.
    store.require_active_sources(job=job)
    if not store.processing or row['task'] != 'qa-execution' or row['role'] != 'QA':
        raise Refusal('only current software-admitted QA preparation can use case-Root disposition')
    cap, selected = store.processing.current()
    if actor != cap['issuer'] or actor != store.config['roles']['Work']['owner']:
        raise Refusal('actual current Work issuer and accepted case Root required')
    boards = store.processing.boards
    boards['Work'].verify_authority(store)
    admission = store.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    receipt = json.loads(admission['receipt']) if admission else {}
    applied = receipt.get('software_admission', {})
    if (applied.get('issuer') != actor or applied.get('native_owner_consent') is not False
            or applied.get('capability') != cap['id']):
        raise Refusal('current unchanged software admission required; native/old-capability jobs stay held')
    processing_admission.resolved(store, row['package'], applied['scope'], applied['scope_hash'])
    old = store.attempt(attempt)
    if row['active_attempt'] != attempt or row['state'] != 'held' or old['job'] != job or old['kind'] != 'task':
        raise Refusal('exact active held preparation original required')
    # This checks the actual original proof against current grant/task/admission,
    # epoch, birth and processing selection; nothing is rebound or renewed.
    boards['QA']._software_job_grant(store, row)
    epoch = ordinary.selected(store, row)
    if not epoch or epoch['selection'].get('processing_capability') != cap['id']:
        raise Refusal('exact current scoped ordinary software epoch required')
    task, policy = ordinary.policy_for(store, row)
    scope = task['admitted_scope']
    key = scope.get('branch_binding') or branches.job_branch_key(store, row)
    branch = branches.association(store, key) if key else None
    if (not branch or branch['root'] != actor or not branch['accepted']
            or branch['scope'] != row['package'] or branch['repository'] != policy['repository']):
        raise Refusal('actual accepted branch Root, package and source repository required')
    if row['controller'] != old['controller'] and not store.owns_disposition(row, old):
        raise Refusal('original current collector or proved collected closure required')
    detail = json.loads(old['detail'])
    tools = detail.get('tool_completion', {})
    items = tools.get('items')
    answer = collected_task_result(old)
    sandbox = detail.get('sandbox_readback')
    if (old['state'] != 'collected' or old['begin'] is None or old['ended'] is None
            or old['collected'] is None or type(old['exit']) is not int or old['exit'] != 0
            or old['capture'] != 'complete' or old['error'] or old['cleanup'] not in {'done', 'owned-ephemeral-lifecycle-observed'}
            or not old['session'] or detail.get('root_identity_observed') is not True
            or not isinstance(sandbox, dict) or set(sandbox) != {'type', 'networkAccess'}
            or sandbox.get('type') != 'readOnly' or sandbox.get('networkAccess') is not False
            or detail.get('ephemeral') is not True
            or detail.get('ephemeral_readback') is not True
            or detail.get('creation') != 'owned'
            or detail.get('teardown') != 'actual-owned-process-exit-collected'
            or detail.get('resume_disposition') != 'unavailable-after-ephemeral-owner-exit'
            or tools.get('complete') is not True or tools.get('unknown_types') != []
            or tools.get('nonzero_completions') != [] or not isinstance(items, list) or not items
            or any(not isinstance(t, dict) or t.get('type') != 'commandExecution' or t.get('status') != 'completed'
                   or t.get('completed_notification') is not True or type(t.get('exit_code')) is not int
                   or t['exit_code'] != 0 or t.get('thread') != old['session'] for t in items)
            or answer['semantic'] != 'DONE' or answer['failures'] or answer['artifacts']
            or answer.get('completion', {}).get('preparation_only') is not True):
        raise Refusal('complete original collected kernel read-only/no-network preparation and all known zero tools required')
    if store.one('SELECT id FROM attempts WHERE (job=? OR event IN '
                 "(SELECT json_extract(value,'$.event') FROM json_each(?))) "
                 'AND (ended IS NULL OR collected IS NULL OR exit IS NULL)', (job, row['members'])):
        raise Refusal('uncollected/unknown related original retains its collector')
    if store.one("SELECT id FROM attempts WHERE job=? AND kind='task' AND id!=?", (job, attempt)):
        raise Refusal('other original task effects are outside this preparation disposition')
    if (store.one('SELECT attempt FROM ordinary_runs WHERE job=?', (job,))
            or store.one('SELECT p.attempt FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=?', (job,))
            or store.one('SELECT r.attempt FROM routine_runs r JOIN attempts a ON a.id=r.attempt WHERE a.job=?', (job,))
            or store.one('SELECT attempt FROM local_commits WHERE attempt IN (SELECT id FROM attempts WHERE job=?)', (job,))
            or store.one("SELECT id FROM outboxes WHERE job=? AND kind IN ('work','result')", (job,))):
        raise Refusal('actual/possible ordinary, publication or outgoing work effect prevents preparation disposition')
    if store.one("SELECT id FROM branch_turns WHERE branch=? AND state IN ('active','unknown')", (branch['id'],)):
        raise Refusal('unaccounted branch turn/writer remains held')
    if row['effect_receipt']:
        prior = json.loads(row['effect_receipt'])
        if prior.get('kind') != KIND or prior.get('unknown_effects') != []:
            raise Refusal('actual/unknown prior effect disposition cannot be replaced')
    store.require_recoverable_hold(row, old)
    record = selected.get('service', {}).get('legacy_resources', {}).get('QA', {})
    if not resource_scopes.qa_accounts(record):
        raise Refusal('current exact operation-relative QA resource account required')
    try:
        resource_scopes.qa_operation(store, row, record)
    except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError):
        raise Refusal('current exact source/resource account unavailable or changed') from None
    if resource_scopes.blocked(store, row):
        raise Refusal('current resource/legacy overlap or unknown scope remains binding')
    # policy_for/blocked authenticate current source/ref/tree and leases before
    # this record can resolve this preparation's default effects=unknown.
    return {'kind': KIND, 'job': job, 'attempt': attempt, 'token': token,
            'actor': actor, 'capability': cap['id'], 'epoch': epoch['id'],
            'configuration': digest(store.config), 'task': digest(store.config['tasks'][row['task']]),
            'admission': digest(admission), 'members': digest(json.loads(row['members'])),
            'original': digest(old), 'policy': digest(policy),
            'branch': digest({k: branch[k] for k in ('id', 'root', 'accepted', 'scope', 'repository', 'ref', 'incarnation')}),
            'native_owner_consent': False, 'new_encounter': True}


def disposition(store, row, old, actor, value):
    if (not isinstance(value, dict) or set(value) != {'basis', 'fact'}
            or value['fact'] != 'captured-read-only-preparation-no-ordinary-effect'):
        raise Refusal('explicit typed factual preparation disposition required')
    current = basis(store, row['id'], row['token'], old['id'], actor)
    if value['basis'] != current:
        raise Refusal('preparation disposition basis changed; no stale authority/evidence')
    return {'kind': KIND, 'actor': actor, 'basis': current, 'fact': value['fact'],
            'unknown_effects': [], 'native_owner_consent': False,
            'meaning': 'this captured preparation only; original unknowns and all legacy duties remain'}


def current_disposition(store, row, old):
    value = json.loads(row['effect_receipt']) if row['effect_receipt'] else {}
    if value.get('kind') != KIND:
        return False
    expected = disposition(store, row, old, value.get('actor'),
                           {'basis': value.get('basis'), 'fact': value.get('fact')})
    if encode(value) != encode(expected):
        raise Refusal('exact bounded preparation disposition required')
    return True
