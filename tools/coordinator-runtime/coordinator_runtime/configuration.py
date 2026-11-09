"""Work-selected prospective configuration on the original journal.

Append-only local selection, not historical recovery, enrollment or deployment.
Board grants and all original duties remain bound to their original bytes.
"""
from . import observations

from contextlib import contextmanager
import copy
import fcntl
import hashlib
from importlib.util import cache_from_source
import json
import os
import re
import subprocess
from pathlib import Path

from .contracts import Refusal, digest, encode, regular_path, required_text, validate_config, parse_json, PROFILES, scoped_startup

SCHEMA = """
CREATE TABLE IF NOT EXISTS configuration_transitions(
 position INTEGER PRIMARY KEY AUTOINCREMENT,previous TEXT NOT NULL,current TEXT NOT NULL UNIQUE,
 original TEXT NOT NULL,configuration TEXT NOT NULL,selection TEXT NOT NULL,
 issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS configuration_transitions_no_update
 BEFORE UPDATE ON configuration_transitions BEGIN SELECT RAISE(ABORT,'immutable configuration transition'); END;
CREATE TRIGGER IF NOT EXISTS configuration_transitions_no_delete
 BEFORE DELETE ON configuration_transitions BEGIN SELECT RAISE(ABORT,'immutable configuration transition'); END;
CREATE TABLE IF NOT EXISTS configuration_source_selections(
 position INTEGER PRIMARY KEY AUTOINCREMENT,configuration_position INTEGER NOT NULL,
 selection TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS configuration_source_selections_no_update
 BEFORE UPDATE ON configuration_source_selections BEGIN SELECT RAISE(ABORT,'immutable source selection'); END;
CREATE TRIGGER IF NOT EXISTS configuration_source_selections_no_delete
 BEFORE DELETE ON configuration_source_selections BEGIN SELECT RAISE(ABORT,'immutable source selection'); END;
"""


def _source_selection(runtime, row, *, body=False):
    if not row or not runtime.one("SELECT name FROM sqlite_master WHERE name='configuration_source_selections'"):
        return None
    fields = 'position,issuer,created' + (',selection' if body else '')
    return runtime.one('SELECT ' + fields + ' FROM configuration_source_selections '
                       'WHERE configuration_position=? ORDER BY position DESC LIMIT 1', (row['position'],))


def _with_source_selection(row, source):
    if not source:
        return row
    # Separate ordinals: never invent a different configuration digest/version.
    return {**row, **{k: v for k, v in source.items() if k != 'position'},
            'previous': row['current'], 'source_selection': source['position']}


def latest(runtime):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='configuration_transitions'"):
        return None  # Older read-only protocol fixtures; Store always installs the schema.
    row = runtime.one('SELECT * FROM configuration_transitions ORDER BY position DESC LIMIT 1')
    return _with_source_selection(row, _source_selection(runtime, row, body=True))


def current_binding(runtime):
    """Startup integrity fields without acquiring the historical selection."""
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='configuration_transitions'"):
        return None
    return runtime.one('SELECT current,original,configuration FROM configuration_transitions ORDER BY position DESC LIMIT 1')


def version_metadata(runtime):
    """Current public version identifiers without acquiring historical selections."""
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='configuration_transitions'"):
        return None
    row = runtime.one('SELECT position,previous,current,original,issuer FROM configuration_transitions ORDER BY position DESC LIMIT 1')
    return _with_source_selection(row, _source_selection(runtime, row))


def processing_tasks(runtime):
    assert_current(runtime)
    if not version_metadata(runtime):
        return None
    row = runtime.one("SELECT json_extract(selection,'$.basis.tasks') AS tasks "
                      'FROM configuration_transitions ORDER BY position DESC LIMIT 1')
    return json.loads(row['tasks'])


@observations.observe('configuration-current')
def assert_current(runtime):
    row = version_metadata(runtime)
    if row and row['current'] != digest(runtime.config):
        raise Refusal('configuration is historical; reopen with the selected current configuration, never replay old authority')


def original_digest(runtime):
    row = version_metadata(runtime)
    return row['original'] if row else digest(runtime.config)


def selected(runtime):
    assert_current(runtime)
    row = latest(runtime)
    return json.loads(row['selection']) if row else None


def original_binding(runtime, role, grant):
    """Only ProcessingBoard bridges current authority to a still-revoked grant."""
    assert_current(runtime)
    if not version_metadata(runtime):
        return digest(runtime.config)
    row = runtime.one('SELECT json_extract(selection,?) AS binding FROM configuration_transitions ORDER BY position DESC LIMIT 1',
                      ('$.basis.processing.roles.' + role + '.original.binding',))
    if not row['binding'] or json.loads(row['binding']) != grant:
        raise Refusal('current selection cannot replace the immutable original grant binding')
    return original_digest(runtime)


class _PathExclusions:
    """Lexical operands for one release call, never a validation result cache.

    Component prefixes preserve canonical Path equality/ancestry. POSIX's
    implementation-defined // root is refused before metadata, on both sides
    of the comparison; Linux must not treat it as a separate exclusion root.
    Rebuild from current exclusions/home at every release boundary. No stat,
    alias, byte-pin, pool or authority outcome is retained here.
    """
    def __init__(self, exclusions):
        paths = [Path(p) for p in
                 [*exclusions, *(Path.home()/p for p in PROFILES)]]
        if any(p.anchor == '//' for p in paths):
            raise Refusal('canonical single-root release exclusions required')
        self.prefixes = frozenset(p.parts for p in paths)

    def contains(self, path):
        parts = path.parts
        return any(parts[:end] in self.prefixes for end in range(1, len(parts)+1))


def _path(value, exclusions):
    path = Path(required_text(value, 'current selection path', 4000))
    if not path.is_absolute() or '..' in path.parts or path.anchor == '//':
        raise Refusal('absolute canonical current selection path required')
    excluded = exclusions if isinstance(exclusions, _PathExclusions) else _PathExclusions(exclusions)
    if excluded.contains(path):
        raise Refusal('current selector is excluded before metadata')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal('current selection cannot follow aliases')
    return path


def branch_release_sources(root):
    """Exact public final-consumer dependencies outside the runtime module glob."""
    return [root/'tools/branch_release.py', root/'tools/operational_contracts.py',
            root/'tools/coordinator-runtime/final-release-risk.md']


def release(runtime, candidate):
    """Guard this call's acquisitions, not the caller's prior Python bootstrap.

    The caller/configuration module and trusted interpreter are already loaded.
    Exclusions cannot retroactively unread them. Deferred local imports below
    have a closed source/cache footprint, checked before their loader runs.
    """
    exclusions = _PathExclusions(candidate.get('artifact_exclusions', []))
    # Derive the release lexically: resolve() would acquire excluded metadata
    # and erase an alias before _path could refuse it.
    module = _path(__file__, exclusions)
    directory = module.parents[1]
    root = directory.parent.parent
    modules = _path(str(module.parent), exclusions)
    expected = {'board_library': str(root/'tools/message-board'),
                'operator_cli': str(directory/'coordinator')}
    if any(candidate.get(k) != v for k, v in expected.items()):
        raise Refusal('current operator and Board SDK must select this same release checkout')
    if candidate.get('canonical_publication', {}).get('method') != 'retention-same-inode-v1':
        raise Refusal('current retention must preserve the same-inode snapshot lock contract')
    # Retention capture imports custody -> cleanup. scoped_startup also imports
    # bounded_log -> custody/cleanup when templates are selected. Check this
    # exact local closure's source and current-interpreter caches before either
    # call, even when warm; import hits never cache exclusion/alias permission.
    # contracts/configuration and the interpreter are already bootstrapped.
    for name in ('retention_dependency.py', 'custody.py', 'cleanup.py', 'bounded_log.py'):
        source = _path(str(modules/name), exclusions)
        _path(cache_from_source(str(source)), exclusions)
    from . import retention_dependency
    retention = candidate['canonical_publication']
    retention_dependency.validate_pins(retention.get('source_pins'))
    sources = retention_dependency.capture(retention['library'], exclusions)
    retention_dependency.verify(sources, retention.get('source_pins'))
    receive = candidate.get('control_receive', {})
    if receive.get('instructions') != str(directory/'templates/coordinator-receive.md'):
        raise Refusal('current receive instructions must select this release')
    operator = regular_path(str(_path(candidate.get('operator_config'), exclusions)))
    if parse_json(operator.read_text()) != candidate:
        raise Refusal('operator config file must contain this exact selected current configuration')
    # Guard the source directory before glob enumeration as well as each file
    # before metadata/bytes. This index never memoizes either guard's outcome.
    paths = [*sorted(modules.glob('*.py')), directory/'coordinator',
             *(root/'tools/message-board'/p for p in ('catalog.py', 'board_store.py', 'active_listener.py', 'queue_transport.py', 'managed_owner.py')),
             root/'tools/direct-child/execution_pool.py', root/'tools/direct-child/dispatch.py',
             root/'tools/direct-child/review_context.py',
             *protected_review_sources(root, candidate),
             root/'tools/direct-codex-child/launch.sh', directory/'templates/coordinator-receive.md',
             *(p for p, _ in sources.values()), operator,
             *branch_release_sources(root)]
    for task in candidate['tasks'].values():
        paths.extend(Path(p) for p in task['templates']
                     if not (scoped_startup(task) and Path(p).name in {'AGENTS.md', 'WORK_LOG.md'}))
    from .custody import refuse_log
    files = {}
    for p in sorted(set(paths)):
        refuse_log(p)
        files[str(p)] = hashlib.sha256(regular_path(str(_path(str(p), exclusions))).read_bytes()).hexdigest()
    if any(files[str(path)] != retention['source_pins'][name]
           for name, (path, _) in sources.items()):
        raise Refusal('retention dependencies changed during release acquisition')
    # Membership is user-owned hot control, including an empty paused pool.
    # Pin all other bytes and the exact public location, without touching state.
    control = regular_path(str(_path(candidate['execution_pool_routes'], exclusions)))
    # The adapter cold-loads the shared public pool module after its source has
    # passed the same byte/alias guards above. Guard both loader caches too.
    for source in (modules/'execution_pool.py', root/'tools/direct-child/execution_pool.py'):
        _path(cache_from_source(str(source)), exclusions)
    from .execution_pool import _module
    try:
        pool = _module.Pool(control)
        raw, _, _ = pool.read()
        pool_control = pool.control_binding(raw)
    except _module.PoolError as exc:
        raise Refusal('current public pool unavailable: '+str(exc)) from exc
    return {'root': str(root), 'files': files, 'pool_control': pool_control,
            'qualification': 'source bytes only; no installed provider/native or deployment claim'}


def protected_review_sources(root, candidate):
    """Pin the lazy shared import closure whenever owner Reviews can be selected.

    Template-only historical fixtures and nonopaque consumers do not import the
    continuing endpoint. An actual opaque owner configuration always binds it,
    before any service policy can choose the protected caller.
    """
    selected = any(task.get('role') == 'Reviews' and task.get('phase') == 'proposer'
                   and (task.get('execution') == 'owner'
                        or task.get('binding', {}).get('provider') == 'opaque')
                   for task in candidate['tasks'].values())
    if not selected:
        return []
    return [root/'tools/direct-child'/name for name in
            ('continuing_review.py', 'opaque_dialogue.py', 'profile_lease.py')]


def candidate(runtime, operator_config, scope_tasks, retention_library=None, bounded_work_log=False, scope_options=None):
    """Produce a draft for Work inspection; does not select or write a config."""
    if scope_options is not None and not isinstance(scope_options, dict):
        raise Refusal('explicit prospective scope options object required')
    value = copy.deepcopy(runtime.config)
    directory = Path(__file__).resolve().parents[1]
    root = directory.parent.parent
    old_directory = Path(value['operator_cli']).parent
    value.update(board_library=str(root/'tools/message-board'), operator_cli=str(directory/'coordinator'),
                 operator_config=operator_config, profiles=sorted(PROFILES))
    value['release_scope_tasks'] = list(scope_tasks)
    # Retention is separately supplied. Draft its exact closed dependency map;
    # this neither selects the draft nor grants tasks new external source roots.
    if retention_library is not None:
        value['canonical_publication']['library'] = retention_library
    from .retention_dependency import source_pins
    value['canonical_publication']['source_pins'] = source_pins(
        value['canonical_publication']['library'],
        [*value.get('artifact_exclusions', []),
         *(scope_options or {}).get('exclusions', [])])
    value['control_receive']['instructions'] = str(directory/'templates/coordinator-receive.md')
    for kind in ('classifier', 'diagnosis'):
        value[kind]['cwd'] = str(root)
    for name, task in value['tasks'].items():
        task['templates'] = [str(directory/Path(p).relative_to(old_directory))
                             if Path(p).is_relative_to(old_directory) else p for p in task['templates']]
        if name in scope_tasks:
            authority = task['effect_authority']
            if 'read-source' not in authority['operations']:
                raise Refusal('source scope requires an already source-authorized task')
            for name in ('coordinator-runtime', 'message-board', 'direct-child', 'direct-codex-child'):
                path = str(root/'tools'/name)
                if path not in authority['read_roots']:
                    authority['read_roots'].append(path)
            if task['role'] == 'Branch':
                # Existing Branch source authority, exact files only. No tools/
                # ancestor grant, additional task, write, network or capacity.
                for source in branch_release_sources(root):
                    if str(source) not in authority['read_roots']:
                        authority['read_roots'].append(str(source))
            if task.get('require_package_scope'):
                if task['role'] not in {'Branch', 'QA'}:
                    raise Refusal('only scoped Branch/QA tasks may acquire the release repository scope')
                if str(root) not in task['scope_roots']:
                    task['scope_roots'].append(str(root))
    if bounded_work_log:
        from .bounded_log import KIND
        matches = [t for t in value['tasks'].values() if t['role']=='Work' and t['phase']=='integrator' and t.get('routine_completion')]
        if len(matches) != 1:
            raise Refusal('one existing seven-duty Work integrator required')
        matches[0]['templates'] = [p for p in matches[0]['templates'] if Path(p).name not in {'AGENTS.md','WORK_LOG.md'}]
        policy = matches[0]['routine_completion']
        logs = [p for p in policy['targets'] if Path(p).name == 'WORK_LOG.md']
        if len(logs) != 1 or len(policy['targets']) != 7:
            raise Refusal('existing seven real targets and exact log target required')
        matches[0]['routine_completion'] = {'kind': KIND, 'targets': policy['targets'],
            'bounded_log': {'target': logs[0], 'max_lines': 12, 'max_bytes': 8192, 'max_entry_bytes': 16384}}
    if set(scope_tasks) - set(value['tasks']):
        raise Refusal('unknown task in current configuration draft')
    if scope_options is not None:
        apply_scope_options(runtime.config, value, scope_options, runtime=runtime)
    for task in value['tasks'].values():
        if task.get('require_package_scope'):
            task['scope_exclusions'] = list(value.get('artifact_exclusions', []))
    return value


def read_ceiling_extensions(runtime, original, value, entries):
    """Exact pinned files only; source-owner testimony is attributed, not authenticated.

    Draft checks local enrollment; basis/apply additionally validate the actual
    original Board grant through the unchanged ProcessingBoard bridge.
    """
    from .resource_scopes import root
    if not isinstance(entries, dict) or set(entries) - set(original['tasks']):
        raise Refusal('read ceiling extensions require existing tasks')
    if not entries:
        return
    if runtime is None:
        raise Refusal('read ceiling extension requires the current enrolled runtime')
    assert_current(runtime)
    exclusions = value.get('artifact_exclusions', [])
    # Representation uses the already selected finite file budget, never a
    # capacity increase requested alongside this draft. Byte acquisition keeps
    # its independent, stricter per-file and aggregate bounds below.
    max_files = original['limits']['max_files']
    def path(text, *, metadata=False):
        p = root(text, exclusions, metadata=False)
        if (str(p) != text or p.anchor == '//' or
                set(p.parts) & {'AGENTS.md', 'WORK_LOG.md', '.ssh', '.aws', '.config', '.local'}):
            raise Refusal('exact canonical public material path required')
        return root(text, exclusions) if metadata else p
    def sha(text):
        if not isinstance(text, str) or not re.fullmatch('[0-9a-f]{64}', text):
            raise Refusal('exact material SHA256 required')
    for name, entry in entries.items():
        fields = {'configuration', 'role_owner', 'original_grant', 'authority',
                  'source_authority', 'read_roots', 'repository_reads', 'components', 'source', 'safe_files'}
        if not isinstance(entry, dict) or set(entry) != fields:
            raise Refusal('exact read ceiling binding and pinned material required')
        task, prior = value['tasks'][name], original['tasks'][name]
        owner = prior['effect_authority']['owner']
        enrolled = runtime.one('SELECT owner,grant_id,intake FROM enrollments WHERE role=?', (prior['role'],))
        if (entry['configuration'] != digest(original) or entry['role_owner'] != owner
                or owner != original['roles'][prior['role']]['owner'] or not enrolled
                or enrolled['owner'] != owner or enrolled['grant_id'] != entry['original_grant']
                or enrolled['intake'] != 0):
            raise Refusal('read ceiling requires exact current configuration, owner and stopped original grant')
        if not set(prior['effect_authority']['operations']) & {'read-source', 'read-reports'}:
            raise Refusal('existing source/report authority required')
        required_text(entry['authority'], 'attributed Work read ceiling choice', 4000)
        required_text(entry['source_authority'], 'attributed concrete source-owner binding', 4000)
        roots, safe_files, source = entry['read_roots'], entry['safe_files'], entry['source']
        if (not isinstance(roots, list) or not 1 <= len(roots) <= max_files
                or not all(isinstance(p, str) for p in roots) or len(set(roots)) != len(roots)
                or not isinstance(safe_files, dict) or not isinstance(entry['components'], dict)
                or not isinstance(entry['repository_reads'], list)):
            raise Refusal('bounded exact material lists required')
        files = dict(safe_files)
        repository = None
        # Complete lexical exclusion checks precede all material metadata.
        for p, pin in safe_files.items():
            path(p); sha(pin)
        if source is not None:
            if (not isinstance(source, dict) or set(source) != {'repository', 'commit', 'files'}
                    or not isinstance(source['commit'], str) or not re.fullmatch('[0-9a-f]{40}', source['commit'])
                    or not isinstance(source['files'], dict) or not source['files']
                    or not entry['components']):
                raise Refusal('exact immutable repository/component/file binding required')
            if 'read-source' not in prior['effect_authority']['operations']:
                raise Refusal('repository source needs existing read-source authority')
            repository = path(source['repository'])
            path(str(repository/'.git'))
            component_files = []
            for component, members in entry['components'].items():
                required_text(component, 'source component', 128)
                if not isinstance(members, list) or not members or not all(isinstance(p, str) for p in members):
                    raise Refusal('exact component file list required')
                component_files.extend(members)
            if set(component_files) != set(source['files']):
                raise Refusal('components must bind every exact tracked file')
            source_bytes = 0
            for relative, pin in source['files'].items():
                p = Path(relative)
                if (p.is_absolute() or str(p) != relative or '..' in p.parts
                        or relative.startswith('-') or '.git' in p.parts):
                    raise Refusal('exact repository-relative material file required')
                absolute = str(repository/p)
                path(absolute); sha(pin)
                if absolute in files:
                    raise Refusal('source and safe report bindings must be distinct')
                files[absolute] = pin
        elif entry['components'] or entry['repository_reads']:
            raise Refusal('repository identities/components need exact immutable source material')
        if set(roots) != set(files) or len(files) > max_files:
            raise Refusal('read roots must equal the exact pinned material files')
        for p in roots:
            path(p)
            if '.git' in Path(p).parts:
                raise Refusal('Git metadata is not source material')
        identities = entry['repository_reads']
        if identities and (identities != [str(repository)] or prior['role'] not in {'Branch', 'Reviews'}
                or prior['phase'] != 'proposer' or prior['effects'] != 'none'
                or prior['sandbox'] != 'read-only' or prior.get('network')
                or prior['effect_authority']['write_roots']):
            raise Refusal('repository identities require an existing read-only source proposer')
        if source is not None:
            path(str(repository), metadata=True)
            gitdir = path(str(repository/'.git'), metadata=True)
            if not gitdir.is_dir():
                raise Refusal('read extension currently requires a standalone repository; linked Git needs separate owner binding')
            def git(*args):
                try:
                    return subprocess.run(['git', '--no-replace-objects', '--literal-pathspecs', '-C', str(repository), *args],
                                          check=True, capture_output=True, timeout=10).stdout
                except (subprocess.SubprocessError, OSError) as exc:
                    raise Refusal('immutable tracked material unavailable') from exc
            for relative in ('objects', 'objects/info', 'objects/pack', 'objects/info/alternates', 'objects/info/http-alternates'):
                checked = path(str(gitdir/relative), metadata=True)
                if relative.endswith(('alternates', 'http-alternates')) and checked.exists():
                    raise Refusal('external Git object stores need separate concrete owner binding')
            if git('cat-file', '-t', source['commit']).strip() != b'commit':
                raise Refusal('source requires an immutable commit object')
            for relative, pin in source['files'].items():
                record = git('ls-tree', '-z', source['commit'], '--', relative)
                try:
                    metadata, actual = record[:-1].split(b'\t')
                    mode, kind, oid = metadata.decode().split()
                except (ValueError, UnicodeError) as exc:
                    raise Refusal('exact tracked regular file required') from exc
                if (not record.endswith(b'\0') or actual != relative.encode()
                        or mode not in {'100644', '100755'} or kind != 'blob'):
                    raise Refusal('only exact tracked regular immutable files may extend reads')
                size = int(git('cat-file', '-s', oid))
                source_bytes += size
                if size > 1048576 or source_bytes > 4194304:
                    raise Refusal('immutable source blob exceeds material bound')
                if hashlib.sha256(git('cat-file', 'blob', oid)).hexdigest() != pin:
                    raise Refusal('tracked immutable source differs from selected material')
        total = 0
        for p, pin in files.items():
            checked = path(p, metadata=True)
            regular = regular_path(str(checked))
            size = regular.stat().st_size
            total += size
            if size > 1048576 or total > 4194304:
                raise Refusal('read extension material exceeds bounded acquisition')
            from .custody import read_file
            if hashlib.sha256(read_file(regular, 1048576)[0]).hexdigest() != pin:
                raise Refusal('read ceiling material changed from its exact pin')
        task['effect_authority']['read_roots'] = list(dict.fromkeys([*task['effect_authority']['read_roots'], *roots]))
        if task.get('package_narrowing'):
            task['scope_roots'] = list(dict.fromkeys([*task['scope_roots'], *roots]))
        if identities:
            task['repository_reads'] = list(dict.fromkeys([*task.get('repository_reads', []), *identities]))


PROTOCOL_SCHEMA_FIELDS = {
    'v2/ThreadStartParams.json': {'ephemeral', 'model', 'config'},
    'v2/ConfigReadParams.json': {'includeLayers'},
    'v2/ConfigReadResponse.json': {'config'},
    'v2/ThreadUnsubscribeParams.json': {'threadId'},
    'v2/ThreadDeleteParams.json': {'threadId'},
}


def select_protocol(runtime, original, value, choice):
    """Recheck Work-selected public evidence, never infer native compatibility.

    Package provenance is the genuine Work issuer's explicit attestation after
    trusted public acquisition. Local JSON cannot authenticate a registry or
    establish behavior; byte pins and the actual version are checked here.
    """
    fields = {'configuration', 'owner', 'authority', 'public_package', 'codex',
              'executable_sha256', 'cli_version', 'qualification',
              'qualification_sha256', 'schema_files', 'settings_check', 'settings_sha256'}
    if not isinstance(choice, dict) or set(choice) != fields or runtime is None:
        raise Refusal('exact explicit protocol upgrade choice required')
    if (choice['configuration'] != digest(original)
            or choice['owner'] != original['roles']['Work']['owner']
            or choice['owner'] != original['software_delegation']['grantor']):
        raise Refusal('protocol upgrade requires current configuration and genuine Work owner')
    required_text(choice['authority'], 'Work trusted public package selection and rationale', 4000)
    package = choice['public_package']
    if (not isinstance(package, dict) or set(package) != {'name', 'version', 'registry', 'integrity', 'tarball'}
            or package['name'] != '@openai/codex'
            or package['registry'] != 'https://registry.npmjs.org'
            or not isinstance(package['version'], str)
            or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?', package['version'])
            or package['tarball'] != 'https://registry.npmjs.org/@openai/codex/-/codex-'+package['version']+'.tgz'
            or not isinstance(package['integrity'], str)
            or not re.fullmatch(r'sha512-[A-Za-z0-9+/]{86}==', package['integrity'])
            or choice['cli_version'] != 'codex-cli '+package['version']
            or choice['cli_version'] == original.get('protocol_cli_version')
            or choice['qualification'] == original.get('protocol_qualification')
            or choice['codex'] == original.get('codex', 'codex')):
        raise Refusal('new exact public Codex package, executable, version and receipt required')
    exclusions = value.get('artifact_exclusions', [])
    def pinned(path, sha, maximum=None):
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise Refusal('protocol evidence SHA256 required')
        p = Path(required_text(path, 'public protocol evidence path', 4000))
        if str(p) != path or set(p.parts) & {'AGENTS.md', 'WORK_LOG.md', '.ssh', '.aws', '.config', '.local'}:
            raise Refusal('exact canonical public protocol evidence required')
        p = regular_path(str(_path(path, exclusions)))
        if maximum is not None and p.stat().st_size > maximum:
            raise Refusal('bounded public protocol evidence required')
        h = hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
        if h.hexdigest() != sha:
            raise Refusal('protocol evidence bytes changed')
        return p
    executable = pinned(choice['codex'], choice['executable_sha256'])
    receipt_path = pinned(choice['qualification'], choice['qualification_sha256'], 1048576)
    receipt = parse_json(receipt_path.read_text())
    if (not isinstance(receipt, dict) or receipt.get('cli_version') != choice['cli_version']
            or receipt.get('settings_check') != choice['settings_check']
            or not isinstance(receipt.get('checked'), dict)):
        raise Refusal('qualified public receipt/version/settings differ')
    schemas = choice['schema_files']
    if not isinstance(schemas, dict) or set(schemas) != set(PROTOCOL_SCHEMA_FIELDS):
        raise Refusal('exact qualified public schema file pins required')
    for name, fields in PROTOCOL_SCHEMA_FIELDS.items():
        p = pinned(str(receipt_path.parent/name), schemas[name], 1048576)
        schema = parse_json(p.read_text())
        declared = receipt['checked'].get(name)
        if (not isinstance(schema, dict) or not isinstance(schema.get('properties'), dict)
                or not fields <= set(schema['properties']) or not isinstance(declared, list)
                or not all(isinstance(f, str) for f in declared) or not fields <= set(declared)):
            raise Refusal('actual pinned generated schema lacks required protocol fields')
    settings = pinned(choice['settings_check'], choice['settings_sha256'], 1048576)
    if not isinstance(parse_json(settings.read_text()), dict):
        raise Refusal('public strict metadata record required')
    try:
        version = subprocess.run([str(executable), '--version'], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=True,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C'}, cwd=receipt_path.parent).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refusal('actual selected public executable version unavailable') from exc
    if len(version) > 256 or version.decode('utf-8', errors='replace').strip() != choice['cli_version']:
        raise Refusal('actual selected executable version differs from qualified version')
    # Recheck executable bytes after the version child; cooperative byte pins,
    # not a claim of noncooperating-writer atomicity or OS sandbox enforcement.
    pinned(choice['codex'], choice['executable_sha256'])
    value.update(codex=choice['codex'], protocol_cli_version=choice['cli_version'],
                 protocol_qualification=choice['qualification'])


def apply_scope_options(original, value, options, *, runtime=None):
    """Explicit future narrowing and associated resource ceilings, never old policy edits."""
    if not isinstance(options, dict) or set(options) - {'protocol_upgrade', 'public_runtime_reads', 'read_ceiling_extensions', 'read_roots', 'neutral_startup', 'exclusions', 'linked_repositories', 'capacity', 'cwd', 'local_integration', 'package_scoped_cleanup', 'package_scoped_proposals', 'repository_reads', 'task_text', 'operations', 'qa_branch_sequence'}:
        raise Refusal('unsupported prospective scope option')
    if 'protocol_upgrade' in options and set(options) != {'protocol_upgrade'}:
        raise Refusal('protocol upgrade must preserve all existing task rights and scope options')
    select_task_text(original, value, options.get('task_text', {}))
    operations = options.get('operations', {})
    if not isinstance(operations, dict) or set(operations) - {'qa-execution'}:
        raise Refusal('operation selection only narrows the existing QA execution task')
    for name, selected in operations.items():
        task = value['tasks'].get(name)
        prior = original['tasks'].get(name)
        if (not task or not prior or selected != ['execute-admitted-qa']
                or task['role'] != 'QA' or task['phase'] != 'execution'
                or task['effects'] != 'owner-reconcile' or not task.get('require_package_scope')
                or 'execute-admitted-qa' not in prior['effect_authority']['operations']):
            raise Refusal('exact already-authorized least-authority QA operation required')
        task['effect_authority']['operations'] = list(selected)
    if 'local_integration' in options:
        from .local_integration import policy
        value['local_integration'] = copy.deepcopy(options['local_integration'])
        policy(value)
    select_capacity(original, value, options.get('capacity'))
    exclusions = options.get('exclusions', [])
    if not isinstance(exclusions, list):
        raise Refusal('explicit additional exclusions required')
    # Lexical exclusion union only. Never stat an exclusion or seek its aliases.
    for p in exclusions:
        path = Path(required_text(p, 'known exclusion', 4000))
        if not path.is_absolute() or '..' in path.parts:
            raise Refusal('absolute known exclusion required')
        if p not in value.setdefault('artifact_exclusions', []):
            value['artifact_exclusions'].append(p)
    if 'protocol_upgrade' in options:
        select_protocol(runtime, original, value, options['protocol_upgrade'])
    def safe(p):
        from .resource_scopes import root
        return root(p, value.get('artifact_exclusions', []))
    read_ceiling_extensions(runtime, original, value, options.get('read_ceiling_extensions', {}))
    from .public_runtime import extend as extend_public_runtime
    extend_public_runtime(runtime, original, value, options.get('public_runtime_reads', {}))
    repositories = options.get('repository_reads', {})
    if not isinstance(repositories, dict) or set(repositories) - set(value['tasks']):
        raise Refusal('exact associated repository read task map required')
    release_root = str(Path(__file__).resolve().parents[3])
    for name, roots in repositories.items():
        task = value['tasks'][name]
        admitted = options.get('read_ceiling_extensions', {}).get(name, {}).get('repository_reads', [])
        if (not isinstance(roots, list) or not roots or len(set(roots)) != len(roots)
                or set(roots) - {release_root, *admitted} or task['role'] not in {'Branch', 'Reviews'}
                or task['phase'] != 'proposer' or task['effects'] != 'none'
                or task['sandbox'] != 'read-only' or task.get('network')
                or task['effect_authority']['write_roots']
                or 'read-source' not in task['effect_authority']['operations']):
            raise Refusal('repository reads require release or exact extended identities and a read-only source proposer')
        for repository in roots:
            safe(repository)
        # A repository identity operand, NOT a filesystem read root. Material
        # paths, immutable pins, package/association and context guards stay separate.
        task['repository_reads'] = list(roots)
    reads = options.get('read_roots', {})
    linked = options.get('linked_repositories', {})
    neutral = options.get('neutral_startup', [])
    if not isinstance(reads, dict) or not isinstance(linked, dict) or not isinstance(neutral, list):
        raise Refusal('exact task read scopes, linked repositories and startup selections required')
    if (set(reads) | set(linked) | set(neutral)) - set(value['tasks']):
        raise Refusal('unknown prospective scoped task')
    for name, roots in reads.items():
        if not isinstance(roots, list) or not roots:
            raise Refusal('nonempty explicit future read roots required')
        allowed = value['tasks'][name]['effect_authority']['read_roots']
        retention = str(Path(value['canonical_publication']['library'])/'retention.py')
        from .retention_dependency import FILES, validate_pins
        validate_pins(value['canonical_publication'].get('source_pins'))
        dependency_files = {str(Path(value['canonical_publication']['library'])/f) for f in FILES}
        source_task = ('read-source' in value['tasks'][name]['effect_authority']['operations']
                       and value['tasks'][name].get('phase') != 'cleanup')
        for p in roots:
            path = safe(p)
            if not (p == retention or source_task and p in dependency_files
                    or any(path.is_relative_to(Path(r)) for r in allowed)):
                raise Refusal('read roots may only narrow existing/release authority or select exact pinned retention dependencies for source tasks')
            # No broad ancestor containing a known exclusion is a safe read scope.
            if any(Path(e).is_relative_to(path) for e in value.get('artifact_exclusions', [])):
                raise Refusal('read root contains a known exclusion; select exact safe inputs')
        value['tasks'][name]['effect_authority']['read_roots'] = list(dict.fromkeys(roots))
    for name in neutral:
        task = value['tasks'][name]
        task['startup'] = 'explicit-packet'
        task['templates'] = [p for p in task['templates'] if Path(p).name not in {'AGENTS.md','WORK_LOG.md'}]
    for name, records in linked.items():
        task = value['tasks'][name]
        if task['role'] not in {'Branch','QA'} or not task.get('require_package_scope') or not isinstance(records, list) or not records:
            raise Refusal('associated common Git ceiling needs an existing scoped Branch/QA task')
        for record in records:
            if not isinstance(record, dict) or set(record) != {'repository','common_git'}:
                raise Refusal('exact repository/common Git pair required')
            repo, common = safe(record['repository']), safe(record['common_git'])
            if (not any(repo.is_relative_to(Path(p)) for p in task['scope_roots'])
                    or common.name != '.git' or common == repo or repo.is_relative_to(common)):
                raise Refusal('narrow associated common Git path and already admitted repository required')
            # No general home/AI grant. This separate ceiling is usable only with
            # its paired cwd and freshly verified actual topology in scoped_task.
        task['linked_repositories'] = copy.deepcopy(records)
    directories = options.get('cwd', {})
    if not isinstance(directories, dict) or set(directories) - set(value['tasks']):
        raise Refusal('exact future task working-directory map required')
    for name, directory in directories.items():
        path = safe(directory)
        allowed = original['tasks'][name]['effect_authority']['read_roots'] + [original['tasks'][name]['cwd']]
        if (not any(path.is_relative_to(Path(p)) for p in allowed)
                or any(Path(e).is_relative_to(path) for e in value.get('artifact_exclusions', []))):
            raise Refusal('future cwd must narrow existing nonexcluded authority; no new resource grant')
        value['tasks'][name]['cwd'] = str(path)
    cleanup = options.get('package_scoped_cleanup', [])
    if (not isinstance(cleanup, list) or not all(isinstance(t, str) for t in cleanup)
            or len(set(cleanup)) != len(cleanup)):
        raise Refusal('exact prospective package-scoped cleanup task selection required')
    proposals = options.get('package_scoped_proposals', [])
    if (not isinstance(proposals, list) or not all(isinstance(t, str) for t in proposals)
            or len(set(proposals)) != len(proposals)):
        raise Refusal('exact prospective package-scoped proposal selection required')
    for name in proposals:
        task = value['tasks'].get(name)
        if (not task or task['role'] != 'Branch' or task['phase'] != 'proposer'
                or task['effects'] != 'none' or task['sandbox'] != 'read-only'
                or task.get('network') or task['effect_authority']['write_roots']
                or task.get('execution') == 'owner'):
            raise Refusal('package-scoped proposals only narrow the genuine read-only software Branch proposer')
    for name in [*cleanup, *proposals]:
        task = value['tasks'].get(name)
        if name in cleanup and (not task or task['role'] != 'QA' or task['phase'] != 'cleanup' or task.get('execution') == 'owner'):
            raise Refusal('package-scoped cleanup only narrows the genuine software QA cleanup task')
        # No added read/write/network/effect/procedure/ordinary permission. The
        # cwd is only a permitted working directory, not a new read ceiling;
        # scoped_task separately enforces each existing access root below.
        roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
        task.update(require_package_scope=True, package_narrowing=True,
                    scope_roots=list(dict.fromkeys([*roots, task['cwd']])))
    if 'qa_branch_sequence' in options:
        from .contracts import QA_BRANCH_SEQUENCE, qa_branch_sequence
        if options['qa_branch_sequence'] != QA_BRANCH_SEQUENCE:
            raise Refusal('supported same-package QA/Branch sequence required')
        value['qa_branch_sequence'] = QA_BRANCH_SEQUENCE
        for name, category, destination in (
                ('qa-execution', 'consolidated', 'branch-integrator'),
                ('branch-integrator', 'complete', 'qa-cleanup'),
                ('qa-cleanup', 'qualification', 'work-proposer')):
            value['tasks'][name]['responses'][category] = [destination]
        qa_branch_sequence(value)
    value['prospective_scope_selection'] = copy.deepcopy(options)


def task_text_fields(original, fields):
    """Validate existing semantic leaves; text cannot replace typed rights."""
    if not isinstance(fields, dict) or not fields or set(fields) - {'authority', 'purpose'}:
        raise Refusal('task_text selects only existing authority/purpose text fields')
    if set(fields) - set(original):
        raise Refusal('task_text cannot add a task field')
    for name, text in fields.items():
        required_text(original[name], 'existing task ' + name)
        required_text(text, 'selected task ' + name)
    authority = fields.get('authority', original['authority'])
    prefix = original['authority'] + '\n\n'
    if authority != original['authority'] and (not authority.startswith(prefix) or not authority[len(prefix):].strip()):
        raise Refusal('task_text authority must retain the exact prior bounds and append a clarification paragraph')
    return fields


def select_task_text(original, value, selection):
    """Explicit semantic-only task selection, reconstructed by validate_changes."""
    if not isinstance(selection, dict) or set(selection) - set(original['tasks']):
        raise Refusal('task_text requires an explicit existing task map')
    for name, fields in selection.items():
        value['tasks'][name].update(task_text_fields(original['tasks'][name], fields))


def select_capacity(original, value, policy):
    """Explicit bounded prospective ceilings; original rows/grants stay charged.

    This declaration is not physical entitlement, allocation or headroom proof.
    Work selects it through the existing exact configuration basis/decision.
    """
    if policy is None:
        return
    bounds = {'max_bytes': 1024 * 1024 * 1024, 'max_files': 50000,
              'max_events': 65536, 'max_jobs': 65536, 'max_attempts': 65536,
              'max_outboxes': 65536, 'max_alerts': 65536, 'max_alert_debt': 65536,
              'max_board_deliveries': 65536}
    if (not isinstance(policy, dict) or set(policy) != {'authority', 'evidence', 'limits'}
            or not isinstance(policy['limits'], dict) or not policy['limits'] or set(policy['limits']) - set(bounds)):
        raise Refusal('exact bounded Work prospective capacity authority/evidence/limits required')
    for key in ('authority', 'evidence'):
        required_text(policy[key], 'genuine prospective capacity ' + key, 16000)
    for key, limit in policy['limits'].items():
        if type(limit) is not int or not 1 <= limit <= bounds[key]:
            raise Refusal('prospective capacity exceeds supported finite ceiling: ' + key)
        value['limits'][key] = limit


def validate_changes(runtime, value, tasks):
    validate_config(value)
    if (not isinstance(tasks, list) or not tasks or len(set(tasks)) != len(tasks)
            or set(tasks) - set(value['tasks'])):
        raise Refusal('exact prospective task allowlist required')
    if value == runtime.config:
        return  # Source-only compatibility is checked against the immutable release below.
    # Reconstruct the permitted change. All other identities, grants, task
    # effects/bindings/concurrency, recipients, policies and fences freeze.
    # Only the explicit bounded capacity option may amend residency ceilings.
    root = str(Path(__file__).resolve().parents[3])
    additions = value.get('release_scope_tasks', [])
    if not isinstance(additions, list) or len(set(additions)) != len(additions) or set(additions) - set(value['tasks']):
        raise Refusal('exact release source-task list required')
    bounded = any(t.get('routine_completion') != runtime.config['tasks'][name].get('routine_completion') for name,t in value['tasks'].items())
    options = value.get('prospective_scope_selection')
    expected = candidate(runtime, value['operator_config'], additions, value.get('canonical_publication', {}).get('library'), bounded, options)
    if bounded and any(name not in tasks for name,t in value['tasks'].items() if t.get('routine_completion') != runtime.config['tasks'][name].get('routine_completion')):
        raise Refusal('changed bounded completion policy needs selected prospective Work task')
    if value != expected:
        raise Refusal('unsupported current configuration delta; only coherent selectors and exact release scopes may change')
    if any(name not in tasks for name in additions):
        raise Refusal('every added scope needs an explicitly selected prospective task')
    if options and (set(options.get('public_runtime_reads', {})) | set(options.get('read_ceiling_extensions', {})) | set(options.get('read_roots', {})) | set(options.get('neutral_startup', [])) | set(options.get('linked_repositories', {})) | set(options.get('cwd', {})) | set(options.get('package_scoped_cleanup', [])) | set(options.get('package_scoped_proposals', [])) | set(options.get('repository_reads', {}))) - set(tasks):
        raise Refusal('every changed future scope/startup needs an explicitly selected task')
    if options and 'protocol_upgrade' in options:
        if (set(tasks) != set(value['tasks']) or additions
                or value['tasks'] != runtime.config['tasks']):
            raise Refusal('protocol upgrade requires every conserved task and unchanged task rights')
    if options and 'local_integration' in options and set(options['local_integration']['tasks']) - set(tasks):
        raise Refusal('every future local integration policy needs an explicitly selected prospective task')
    if options and set(options.get('task_text', {})) - set(tasks):
        raise Refusal('every task_text selection needs an explicitly selected prospective task')
    if options and set(options.get('operations', {})) - set(tasks):
        raise Refusal('every operation selection needs an explicitly selected prospective task')
    if options and 'qa_branch_sequence' in options and {'qa-execution', 'branch-integrator', 'qa-cleanup', 'work-proposer'} - set(tasks):
        raise Refusal('every same-package sequence task needs explicit prospective selection')
    # Scoped_task still narrows each actual package; this grants no writes or
    # Root acceptance. Broad ancestors and peer checkout roots cannot enter.
    if any(root not in value['tasks'][name]['scope_roots'] for name in additions
           if value['tasks'][name].get('require_package_scope')):
        raise Refusal('exact release scope required')


def journal(runtime):
    """Protocol mutation witnesses; no retained body/key/size acquisition.

    Applicable guarded body validation stays at source use. These tokens bind
    writes since bootstrap, not historical truth, integrity or whole reads.
    """
    from . import windows
    witness = windows.revision(runtime)
    result = {}
    for table in runtime.rows("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = table['name']
        token = (digest(witness['sequences']) if name == 'sqlite_sequence' else
                 'revision infrastructure; no source rows' if name == 'allocation_revision' else witness['tokens'][name])
        result[name] = {'revision': token, 'schema': digest(table['sql'])}
        if table['name'] == 'artifact_blobs':
            result[name]['body_observation'] = 'no body/key/size acquisition; body integrity unobserved'
    return result


def basis(runtime, boards, value, tasks):
    from . import processing
    assert_current(runtime)
    validate_changes(runtime, value, tasks)
    source_only = None
    if value == runtime.config:
        # Guard the new path's release before processing.implementation() can
        # acquire its module bytes. Bootstrap inputs remain already loaded.
        measured = release(runtime, value)
        source_only = source_change(runtime, measured, tasks)
    identity = runtime.path.stat()
    result = {'configuration': digest(runtime.config), 'candidate': digest(value),
            'runtime': {'path': str(runtime.path), 'dev': identity.st_dev, 'ino': identity.st_ino,
                        'actor': runtime.config['actor']},
            'processing': processing.basis(runtime, boards, future_only=True), 'journal': journal(runtime),
            'release': measured if source_only else release(runtime, value), 'tasks': tasks}
    if source_only:
        result['source_only'] = source_only
    return result


def source_change(runtime, after, tasks):
    """Only measured existing runtime code may differ; Work owns semantic review."""
    previous = selected(runtime)
    if not previous:
        raise Refusal('source-only selection requires an existing immutable selected release')
    before = previous['basis']['release']
    if tasks != previous['basis']['tasks']:
        raise Refusal('source-only selection preserves the exact prospective task allowlist')
    if set(before) != set(after) or any(before[k] != after[k] for k in before if k != 'files'):
        raise Refusal('source-only selection preserves release root, pool and static dependencies')
    old, new = before['files'], after['files']
    if set(old) != set(new):
        raise Refusal('source-only selection preserves the exact known release file extent')
    module_root = Path(before['root'])/'tools/coordinator-runtime/coordinator_runtime'
    allowed = {p for p in old if Path(p).parent == module_root and Path(p).suffix == '.py'}
    changed = sorted(p for p in new if old[p] != new[p])
    if not changed or set(changed) - allowed:
        raise Refusal('source-only selection requires different runtime code and unchanged static dependencies')
    return {'previous_release': digest(before), 'release': digest(after), 'changed': changed,
            'qualification': 'measured code change only; genuine Work owns reviewed semantic selection'}


def _outgoing_source_originals(runtime):
    """Resolve the outgoing source generation, retaining unrelated original duties.

    Resolve relationships from public version/source metadata before acquiring
    any lifecycle state. Legacy bases have no source ordinal: their immutable
    implementation must identify exactly one selected generation. The stop
    lock and separate active-authority guards still apply to every selection.
    """
    version = version_metadata(runtime)
    configuration = digest(runtime.config)
    ambiguous = 'source-only selection requires unambiguous outgoing source/configuration generation'
    if not version or version['current'] != configuration:
        raise Refusal(ambiguous)
    generations = {}
    for row in runtime.rows(
            "SELECT 0 AS ordinal,json_extract(selection,'$.basis.release.root') AS root,"
            "json_extract(selection,'$.basis.release.files') AS files FROM configuration_transitions WHERE position=? "
            "UNION ALL SELECT position,json_extract(selection,'$.basis.release.root'),"
            "json_extract(selection,'$.basis.release.files') FROM configuration_source_selections WHERE configuration_position=?",
            (version['position'], version['position'])):
        try:
            root = Path(row['root'])/'tools/coordinator-runtime/coordinator_runtime'
            files = json.loads(row['files'])
            implementation = {Path(p).name: h for p, h in files.items()
                              if Path(p).parent == root and Path(p).suffix == '.py'}
        except (ValueError, TypeError, AttributeError):
            raise Refusal(ambiguous)
        if not implementation or row['ordinal'] in generations:
            raise Refusal(ambiguous)
        generations[row['ordinal']] = implementation
    outgoing = version.get('source_selection', 0)
    if outgoing not in generations:
        raise Refusal(ambiguous)
    # Exclude other exact configuration digests in SQL, before returning even
    # their implementation metadata. Missing/inconsistent relationships refuse;
    # a free cooperative lock or revoked capability cannot qualify them.
    originals = runtime.rows(
        "WITH originals AS (SELECT controller,capability FROM processing_runs UNION "
        "SELECT controller,capability FROM service_runs), metadata AS ("
        "SELECT o.controller,o.capability,json_extract(c.selection,'$.basis.configuration') AS configuration,"
        "json_extract(c.selection,'$.basis.configuration_transition.position') AS position,"
        "json_extract(c.selection,'$.basis.configuration_transition.current') AS current,"
        "json_type(c.selection,'$.basis.configuration_transition.position') AS position_type,"
        "json_extract(c.selection,'$.basis.configuration_transition.source_selection') AS ordinal,"
        "json_type(c.selection,'$.basis.configuration_transition.source_selection') AS ordinal_type,"
        "json_extract(c.selection,'$.basis.implementation') AS implementation "
        "FROM originals o LEFT JOIN processing_capabilities c ON c.id=o.capability) "
        "SELECT * FROM metadata WHERE configuration=? OR current=? OR typeof(configuration)!='text' "
        "OR length(configuration)!=64 OR configuration GLOB '*[^0-9a-f]*'",
        (configuration, configuration))
    relevant = []
    for original in originals:
        if (original['configuration'] != configuration or original['position_type'] != 'integer'
                or original['position'] != version['position']
                or original['current'] != configuration):
            raise Refusal(ambiguous)
        try:
            implementation = json.loads(original['implementation'])
        except (ValueError, TypeError):
            raise Refusal(ambiguous)
        ordinal = original['ordinal']
        if ordinal is None:
            if original['ordinal_type'] is not None:
                raise Refusal(ambiguous)
            matches = [n for n, pins in generations.items() if implementation == pins]
            if len(matches) != 1:
                raise Refusal(ambiguous)
            ordinal = matches[0]
        elif original['ordinal_type'] != 'integer':
            raise Refusal(ambiguous)
        if type(ordinal) is not int or generations.get(ordinal) != implementation:
            raise Refusal(ambiguous)
        if ordinal == outgoing:
            relevant.append((original['controller'], original['capability']))
    # Validate the complete relevant relationship set before the first state
    # read, including service-only or mismatched-capability originals.
    for controller, capability in relevant:
        if (not runtime.one('SELECT controller FROM processing_runs WHERE controller=? AND capability=?', (controller, capability))
                or runtime.one('SELECT controller FROM service_runs WHERE controller=? AND capability!=?', (controller, capability))):
            raise Refusal(ambiguous)
    return relevant


def _original_parent_released(runtime, controller, capability):
    """Read supported processing-release evidence, never infer effect completion."""
    run = runtime.one('SELECT state FROM processing_runs WHERE controller=? AND capability=?', (controller, capability))
    try:
        receipt = json.loads(run['state'])['parent_END']
    except (ValueError, KeyError, TypeError):
        receipt = None
    return (isinstance(receipt, dict) and type(receipt.get('actual_END')) is int
            and isinstance(receipt.get('evidence'), list) and bool(receipt['evidence'])
            and all(isinstance(e, str) and e.strip() for e in receipt['evidence'])
            and not runtime.one('SELECT id FROM attempts WHERE controller=? AND collected IS NULL LIMIT 1', (controller,)))


def source_originals_stopped(runtime):
    """Source-only repair still requires the original service's return marker."""
    for controller, capability in _outgoing_source_originals(runtime):
        service = runtime.one('SELECT state,returned FROM service_runs WHERE controller=? AND capability=?', (controller, capability))
        if (not _original_parent_released(runtime, controller, capability)
                or service and (service['state'] != 'returned-awaiting-parent-END' or service['returned'] is None)):
            raise Refusal('source-only selection requires original stop, numeric parent END and processing-release')


def protocol_originals_stopped(runtime):
    """Future executable selection needs parent END, not old reconciliation.

    processing-release authenticates the original issuer and collected attempts.
    A finalizer failure can leave serving/NULL after actual parent collection;
    retain that service row and every unresolved duty without replay or repair.
    The caller still owns the stop lock and active-authority checks.
    """
    for controller, capability in _outgoing_source_originals(runtime):
        if not _original_parent_released(runtime, controller, capability):
            raise Refusal('protocol upgrade requires original stop, numeric parent END and processing-release')


@contextmanager
def stopped(runtime):
    fd = os.open(runtime.home/'service.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('original cooperative service owns its lock; collect/control it, never displace it') from exc
        yield
    finally:
        os.close(fd)


def apply(runtime, boards, value, selection):
    if not isinstance(selection, dict) or set(selection) != {'basis', 'authority'}:
        raise Refusal('exact current transition basis and genuine Work authority required')
    required_text(selection['authority'], 'Work current configuration decision and rationale', 4000)
    issuer = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    tasks = selection['basis']['tasks']
    with stopped(runtime), runtime.tx():
        current = basis(runtime, boards, value, tasks)
        if current != selection['basis']:
            raise Refusal('current transition source/basis changed; no automatic retry')
        if (current['processing']['current'] or runtime.one('SELECT id FROM prospective_authorities WHERE revoked IS NULL')
                or any(r['original']['continuation'] for r in current['processing']['roles'].values())):
            raise Refusal('explicitly revoke existing processing/prospective/retained capabilities; no implicit supersession')
        if any(r['original']['binding']['issued_by'] != issuer for r in current['processing']['roles'].values()):
            raise Refusal('same genuine original Work issuer required')
        if 'source_only' in current:
            source_originals_stopped(runtime)
        elif 'protocol_upgrade' in value.get('prospective_scope_selection', {}):
            protocol_originals_stopped(runtime)
        record = {**selection, 'previous_configuration': runtime.config,
                  'event_boundary': current['processing']['event_boundary'],
                  'jobs': [r['id'] for r in runtime.rows('SELECT id FROM jobs')],
                  'outboxes': [r['id'] for r in runtime.rows('SELECT id FROM outboxes')],
                  'collectors': {r['id']: r['controller'] for r in runtime.rows('SELECT id,controller FROM attempts')},
                  'alert_boundary': runtime.one('SELECT COALESCE(MAX(rowid),0) AS n FROM alerts')['n']}
        encoded = encode(record)
        runtime.budget(None, len(encoded.encode()) + len(encode(value).encode()) + 4096)
        if 'source_only' in current:
            source_position = runtime.db.execute('INSERT INTO configuration_source_selections(configuration_position,selection,issuer,created) VALUES(?,?,?,?)',
                                                 (version_metadata(runtime)['position'], encoded, issuer, runtime.clock())).lastrowid
        else:
            runtime.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
                               (current['configuration'], current['candidate'], original_digest(runtime), encode(value), encoded, issuer, runtime.clock()))
    return {'configuration': current['candidate'], 'previous': current['configuration'],
            **({'source_only': current['source_only'], 'source_selection': source_position} if 'source_only' in current else {}),
            'runtime': current['runtime'], 'normal_grants': 'unchanged and still revoked',
            'next': 'reopen this same journal with selected current config; take fresh processing-basis and delegate prospective authority',
            'historical_recovery': False}


def validate_processing(runtime, selection):
    tasks = processing_tasks(runtime)
    if tasks is None:
        return
    from .selected_source import selected_pins
    pins = selected_pins(selection)
    if (selection['retained_events'] and selection['retained_events'] != [p['event'] for p in pins]
            or selection['recover_controls'] or not selection['future_intake']
            or set(selection['tasks']) - set(tasks)
            or any(r['kind'] != 'admit-package' for r in selection.get('owner_operations', []))):
        raise Refusal('current configuration authority is prospective only; historical recovery/holds remain original')


def event_allowed(runtime, event):
    transition = selected(runtime)
    if not transition:
        return True
    row = runtime.one('SELECT COALESCE(p.position,e.rowid) AS position FROM events e LEFT JOIN processing_source_positions p ON p.event=e.id WHERE e.id=?', (event['id'],))
    from .selected_source import permits_original
    return not row or row['position'] > transition['event_boundary'] or permits_original(runtime, event)


def event_candidate_scope(runtime):
    """SQL exclusion for existing events aliased e, never an authority proof.

    Apply the same logical-birth boundary as event_allowed before acquiring
    candidate bodies or doing per-candidate release/grant work. No transition
    means no exclusion, including explicitly selected retained processing.
    Callers still validate every candidate and its actual effect boundaries.
    The returned predicate is local to this query; it is not cached authority.
    """
    transition = selected(runtime)
    if not transition:
        return '1', ()
    from .selected_source import selected_pins
    pins = selected_pins(runtime.processing.current()[1]) if runtime.processing else []
    ids = [p['event'] for p in pins]
    extra = ' OR e.id IN (' + ','.join('?' for _ in ids) + ')' if ids else ''
    return ('(COALESCE((SELECT p.position FROM processing_source_positions p '
            'WHERE p.event=e.id),e.rowid)>?' + extra + ')', (transition['event_boundary'], *ids))


def task_for_job(runtime, job):
    """Retained resource debt uses its historical policy, never new selectors."""
    for row in runtime.rows('SELECT selection FROM configuration_transitions ORDER BY position'):
        transition = json.loads(row['selection'])
        if job['id'] in transition['jobs']:
            return transition['previous_configuration']['tasks'][job['task']]
    return runtime.config['tasks'][job['task']]


def owned_service_conflict(runtime):
    """A new version never adopts or disposes an old collector.

    The cooperative lock still excludes a live owner. Other-version originals
    remain owned with their attempts/resources/contexts; scoped gates decide
    whether any particular new work can proceed. Same-version recovery is strict.
    """
    transition = selected(runtime)
    known = {row['previous'] for row in runtime.rows('SELECT previous FROM configuration_transitions')} if transition else set()
    for run in runtime.rows("SELECT * FROM processing_runs WHERE state='owned'"):
        cap = runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (run['capability'],))
        if (not transition or not cap or json.loads(cap['selection'])['basis']['configuration'] not in known
                or json.loads(cap['selection'])['basis']['configuration'] == digest(runtime.config)):
            return True
    return False


def require_current_job(runtime, job):
    transition = selected(runtime)
    if not transition:
        return
    attempt = runtime.attempt(job['active_attempt']) if job['active_attempt'] else None
    proof = json.loads(attempt['detail']).get('processing_capability') if attempt else None
    if not runtime.processing or proof != runtime.processing.key or any(
            not event_allowed(runtime, runtime.event(m['event'])) for m in json.loads(job['members'])):
        raise Refusal('historical job/effect cannot inherit current configuration authority')
    runtime.processing.authorize(attempt)


def outbox_allowed(runtime, outbox):
    transition = selected(runtime)
    if not transition:
        return True
    if outbox['id'] in transition['outboxes']:
        return False
    if outbox.get('event') and not event_allowed(runtime, runtime.event(outbox['event'])):
        return False
    if outbox.get('job'):
        try:
            require_current_job(runtime, runtime.job(outbox['job']))
        except Refusal:
            return False
    if outbox.get('alert'):
        row = runtime.one('SELECT rowid AS n FROM alerts WHERE id=?', (outbox['alert'],))
        if not row or row['n'] <= transition['alert_boundary']:
            return False
    return True


@observations.observe('source-release')
def assert_release(runtime):
    transition = selected(runtime)
    from .report_repair import selected_release
    expected = selected_release(runtime) or (transition['basis']['release'] if transition else None)
    if expected and release(runtime, runtime.config) != expected:
        raise Refusal('selected public release/dependencies changed; duties held pending an explicit current transition')


def authorize_collection(runtime, attempt):
    """Original collectors may record actual returns, never acquire new effects."""
    row = latest(runtime)
    if not row or row['current'] == digest(runtime.config):
        return
    for version in runtime.rows('SELECT previous,selection FROM configuration_transitions ORDER BY position'):
        record = json.loads(version['selection'])
        if (version['previous'] == digest(runtime.config)
                and record['collectors'].get(attempt) == runtime.controller
                and runtime.attempt(attempt)['controller'] == runtime.controller):
            return
    raise Refusal('historical collection belongs only to the actual original attempt/controller; no takeover')
