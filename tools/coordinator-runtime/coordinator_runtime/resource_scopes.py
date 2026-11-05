"""Compare actual scoped resources without disposing historical role debt."""
from pathlib import Path

from .contracts import PROFILES, Refusal, required_text, scoped_task


def root(value, exclusions=()):
    path = Path(required_text(value, 'resource root', 4000))
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('absolute resource root required')
    if any(path == Path(p) or path.is_relative_to(Path(p)) or Path(p).is_relative_to(path)
           for p in [*exclusions, *[Path.home()/p for p in PROFILES]]):
        raise Refusal('resource overlaps an excluded store before metadata')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal('resource aliases need their actual custodian; no symlink inference')
    # Existing ancestry is compared by identity too (including bind aliases).
    return path


def overlaps(left, right):
    if left == right or left.is_relative_to(right) or right.is_relative_to(left):
        return True
    def ancestors(path):
        return {(p.stat().st_dev, p.stat().st_ino) for p in (path, *path.parents) if p.exists()}
    def identity(path):
        return (path.stat().st_dev, path.stat().st_ino) if path.exists() else None
    return identity(left) in ancestors(right) or identity(right) in ancestors(left)


def validate(runtime, policy):
    for role, record in policy.items():
        if (role not in runtime.config['roles'] or not isinstance(record, dict)
                or set(record) != {'original_hold', 'roots', 'unbounded', 'evidence'}
                or type(record['unbounded']) is not bool or not isinstance(record['roots'], list)):
            raise Refusal('legacy resource account needs exact hold, roots, unbounded and evidence')
        if runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))['legacy_hold'] != record['original_hold']:
            raise Refusal('resource account does not describe the actual retained hold')
        required_text(record['evidence'], 'supported original resource scope, not a renamed package')
        if not record['unbounded'] and not record['roots']:
            raise Refusal('unknown legacy scope cannot be declared independent')
        for value in record['roots']:
            root(value, runtime.config.get('artifact_exclusions', []))


def blocked(runtime, row, task=None):
    enrollment = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (row['role'],))
    if not enrollment or not enrollment['legacy_hold']:
        return False
    task = task or runtime.config['tasks'][row['task']]
    if runtime.processing and row['phase'] == 'proposer' and task['effects'] == 'none':
        return False
    if not runtime.processing:
        return True
    selection = runtime.processing.current()[1]
    record = selection.get('service', {}).get('legacy_resources', {}).get(row['role'])
    if not record or record['unbounded'] or record['original_hold'] != enrollment['legacy_hold']:
        return True
    admission = runtime.one('SELECT * FROM admissions WHERE package=?', (row['package'],))
    # Independence needs a genuine narrowed admission, not a package label.
    if task.get('require_package_scope'):
        if not admission:
            return True
        task = scoped_task(row['task'], task, admission)
    elif not task.get('effect_authority'):
        return True  # No actual configured resource boundary to compare.
    if task.get('network') or 'organize-authorized-refs' in task['effect_authority'].get('operations', []):
        return True  # Path separation alone cannot prove external/shared-ref independence.
    exclusions = runtime.config.get('artifact_exclusions', [])
    selected = [root(p, exclusions) for p in task['effect_authority']['read_roots'] + task['effect_authority']['write_roots'] + [task['cwd']]]
    held = [root(p, exclusions) for p in record['roots']]
    # Actual unresolved local jobs remain owners of their configured/admitted
    # roots even when an external legacy inventory was narrower.
    for job in runtime.rows("SELECT * FROM jobs WHERE role=? AND effects NOT IN ('none','reconciled')", (row['role'],)):
        if row.get('id') == job['id']:
            continue  # Reconcile this operation against OTHER unresolved owners.
        prior = runtime.config['tasks'][job['task']]
        prior_admission = runtime.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
        try:
            prior = scoped_task(job['task'], prior, prior_admission)
            authority = prior['effect_authority']
        except (Refusal, KeyError):
            return True
        held.extend(root(p, exclusions) for p in authority['read_roots'] + authority['write_roots'] + [prior['cwd']])
    return not selected or any(overlaps(a, b) for a in selected for b in held)
