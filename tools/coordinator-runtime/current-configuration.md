# Prospective current configuration on the original journal

`draft-current-configuration`, `current-configuration-basis`,
`select-current-configuration` and `current-configuration-status` support a
Work-selected release/configuration change on the **same original journal**.
They do not enroll, deploy files, change the pool, recover historical execution,
revoke capabilities, send messages or clear any hold. The actual Work issuer
must operate the selection. No additional Source, cold-reader, human or Root
permission gate is introduced.

## Selectors and permitted changes

Invoke the corrected `coordinator` in the selected existing release checkout.
The draft relocates Board SDK, operator CLI, receive instructions, runtime
procedure templates, and classifier/diagnosis CWD to that checkout. Persistent
role CWDs and non-runtime procedure templates remain explicit. Each
`--source-task NAME` adds the four public release tool directories to an
already source-authorized task's read roots. For already package-scoped Branch
or QA tasks it also admits this exact repository root as a scope ceiling for
CWD/ref organization. Each actual package still needs its narrower procedure,
paths and resource evidence through existing admission; no canonical write
root, network capability or operation is added.

For already source-authorized Branch tasks it also adds exact read paths for
`tools/branch_release.py`, `tools/operational_contracts.py` and
`tools/coordinator-runtime/final-release-risk.md`. The release manifest pins these
final-consumer dependencies alongside all existing static sources; it grants no
general `tools/` ancestor access. This is the final PR-risk check used by the
existing Branch repository template, not an added task or first-four admission.

Roles/owners/receive profiles, actor, original state directory and board,
software grantor/authority, recipients, task bindings/effects/capacities,
routine publication targets, limits, original exclusions, holds and policies
remain conserved. Explicit future read narrowing, neutral startup, associated
common Git ceilings and additional exclusions use the scope options below. Work selects the prospective task allowlist
with repeated `--task`; newly added source scopes must be in it. Current
processing can use only those tasks and genuinely future sources. It cannot
select retained events, historical control recovery or legacy-hold disposition.

The draft prospectively authorizes the five known public execution labels:
`.codex`, `.codex2`, `.codex3`, `.codex4`, `.codex5`. This changes only future
execution authority in the separate selected config. It does not enable an
account, establish its availability or registered site binding, or change any
original config, grant, receive address, job or running account.

Retention is a separately selected provider: this repository has no
`tools/message-board/retention.py`. The draft retains the existing
`canonical_publication.library`, or Work can choose an actual compatible public
provider using `--retention-library DIRECTORY`. The contract remains
`retention.snapshot_lock()` with cooperative, nonblocking same-inode publication.
The source manifest pins the selected file; this is not interface execution or
proof of installed compatibility. Runtime/Board/catalog/retention, dispatcher,
launcher, pool adapter/control file, operator configuration and procedure
sources need coherent actual deployment. No peer checkout overwrite is required
or authorized by these commands.

## Operator sequence

Use real paths and current owner evidence; the tokens below are placeholders.
Keep the original effective configuration immutable. Save the prospective draft
as a separate actual file **at its declared operator-config path** before taking
the basis. The draft command only prints JSON.

```sh
RELEASE/tools/coordinator-runtime/coordinator --config ORIGINAL_CONFIG \
  draft-current-configuration --operator-config CURRENT_CONFIG \
  --source-task branch-proposer --source-task branch-integrator \
  --source-task qa-execution
# Work saves/inspects that returned draft at CURRENT_CONFIG, adding other
# genuinely needed source tasks through the draft command's repeated option.
RELEASE/tools/coordinator-runtime/coordinator --config ORIGINAL_CONFIG \
  current-configuration-basis --candidate CURRENT_CONFIG \
  --task work-proposer --task work-integrator \
  --task branch-proposer --task branch-integrator \
  --task reviews-proposer --task reviews-integrator \
  --task qa-execution --task qa-cleanup
# Selection JSON is exactly {"basis": THE_FULL_RETURN, "authority": REAL_DECISION_AND_WHY}.
RELEASE/tools/coordinator-runtime/coordinator --config ORIGINAL_CONFIG \
  select-current-configuration --candidate CURRENT_CONFIG --selection WORK_SELECTION
RELEASE/tools/coordinator-runtime/coordinator --config CURRENT_CONFIG \
  current-configuration-status
RELEASE/tools/coordinator-runtime/coordinator --config CURRENT_CONFIG processing-basis
# Work selects a fresh delegate-processing policy against that whole basis:
# retained_events=[], recover_controls={}, future_intake=true; actual tasks,
# capacity, scopes, software admission and service policies, never placeholder clearances.
```

Before selection, use existing supported revoke/control/collection operations
for owned active processing, prospective and retained capabilities. Selection
requires them explicitly revoked and the cooperative collector lock available.
Both finite processing and continuing service hold that lock while active.
The lock is not evidence of original END, inactivity, settled effects or native
closure. Dead/unavailable original collectors and every unresolved context,
attempt, resource, effect and outbox keep their real custodians. Genuine
collection and installed compatibility are operating work, not new permission
requests. Any original-owner resource disposition needed for future effects must
use its genuinely applicable existing authority while that configuration is
current; this transition supplies no cross-configuration hold-clearing path. If
that disposition or independence remains unknown, preserve the hold and report
the affected effect as blocked. Do not blindly retry a launch or publication to manufacture evidence.

The basis binds exact local protocol rows/schema, original grant identities,
revocations, frontiers, current public source bytes, candidate config and inode.
Selection rechecks it in a local transaction and appends one immutable record.
`meta.configuration`, original configuration snapshots and shared grant digests
are never rewritten. Schema additions occur through `Store`/the supported API;
never issue operational SQL or edit a stored hash. This source correction has
executed schema changes only in isolated fixtures, not real stores.

Before commit, failure rolls back the local transition. After commit, even if
the response was lost, reopen with CURRENT_CONFIG and inspect status. Do not
replay the selection; old-config writers refuse and configuration-transition
digests remain unique. An unsupported rollback refuses; a later compatible
selection uses a fresh exact basis and genuine Work decision, preserving all versions.
The API offers no restoration of old grants or incompatible old selectors.

### Same configuration, new source release

For a reviewed runtime code correction at the **same physical public release
root**, use the existing basis/selection commands with `--config` and
`--candidate` both naming the unchanged selected configuration file. Do not
change `operator_config` or another selector to manufacture a configuration
delta. An existing immutable selected release is required; initial bootstrap
and ordinary different-configuration transitions keep their existing behavior.

The basis includes `source_only`: the previous and measured new release
digests and exact changed files. Every known release filename, root, pool
control binding, non-runtime dependency, template, task and configuration byte
must remain identical. Only bytes of existing runtime Python modules may
change. Identical releases and added/removed modules refuse. This closed extent
does not support a static dependency or policy upgrade; such work needs its
applicable configuration/review procedure. Hot pool membership retains its
existing independent meaning.

Actual Work must review and select the exact code for its current purpose in
the selection's `authority` rationale. Measured hashes or a filename prove
neither semantic correctness nor owner review. The same genuine native issuer,
original grant bindings, cooperative lock, fresh whole basis, revocations and
budget checks still apply. Additionally, every recorded processing run must
have its original supported `processing-release` receipt with numeric parent
END, no uncollected owned attempt, and any associated service must have returned.
A free lock, model DONE or revoked capability supplies no missing original END.

Selection appends an immutable `configuration_source_selections` row associated
with the current configuration transition. No old transition or configuration
body is rewritten. Status reports its separate `source_selection` ordinal and
the honest equal previous/current config digests; the selected release and
future-source boundary advance. Config digests used by existing metadata
terminal-reader fences stay unchanged. A subsequent configuration transition
selects its own release; earlier source selections remain retained history.
Fresh processing authority still requires a separate explicit delegation.
There is no epoch renewal, old-capability transfer, old-job upgrade, input
replay, metadata-fence rewrite, or disposition of historical unknowns/outboxes.

## Authority, receiving and conservation

New ProcessingBoard authority verifies the same original path/device/inode,
actor, owner and revoked grant against the transition. Its basis distinguishes
the current configuration from the grant's historical digest. Normal
RetainedBoard and `service_recovery.predecessor_authority` remain strict: the
current config cannot impersonate old recovery. Incompatible historical
recovery remains original-owner custody, with truthful unavailable/null values.

An old run stays owned in the journal. A new-version collector may start on the
free cooperative lock without disposing that old run; same-version owned runs
still require their existing exact recovery/collection procedure. Resource,
branch, context and package fences still apply. Historical resource comparisons
use each old job's recorded configuration, rather than refreshed task roots.
Unknown or overlapping resources, network/shared-ref uncertainty and unaccepted
Root associations still block the affected construction/effect. They cannot be
empty-cleared by the configuration transition. Independent eligible read-only
work can proceed.

Original live collector objects can record their own original attempt's actual
session/semantic/collection observations after a transition. This narrow custody
path permits no new start or business effect; a new collector gets no borrowed
name, native identity, END or historical recovery authority. It also cannot
supply a missing original return. Normal result validation and controller checks
remain in force.

Existing outboxes/pointers/intents preserve payloads, destinations, operator
prefixes and custody. New current delivery skips historical outboxes and rejects
their reuse through its grant path. Current receiving still needs the exact
persisted source/delivery/grant/consumer intent; a capability marker alone is
insufficient. Current publication requires a current job/attempt and the
unchanged canonical preimage, original collection, effect, custody and snapshot
lock controls. Interrupted publication is not repaired by a config change.

Original four-role sources/outboxes and all other historical records, unknowns,
holds, frontiers, accounting and required histories stay conserved and charged.
Retirement still requires actual whole processing completion plus 24 hours and
all source/consumer/outbox/recovery/effect/privacy holds, with archives' own
completed processing frontier. Enabled membership is the current user-controlled
ordered public pool, distinct from the five supported labels authorized above.
Historical selections and examples do not fix membership. The user can change
ordered membership live through the existing public
`execution_pool.py --routes PUBLIC_CONTROL set [PROFILE ...]` interface; an empty
selection pauses new execution. Inspect through its `status` or the runtime's
`execution-pool` command. No service restart, regrant or account migration is
needed for membership updates after selecting this corrected configuration.

The release pins the exact control path and every static control byte, masking
only the supported `providers.codex.pool` value. Other route/model/effort/provider,
manual authorization, caller and rotation-state bindings remain pinned, alongside
all implementation, procedure, operator-config and dependency bytes. Even static
formatting changes require a fresh coherent selection. Malformed or unsupported
controls refuse. Allocation and admission recheck the selected static control
before state access and under the cooperating lock. They retain the original
monotonic counter and apply its next turn modulo the new ordered pool.

Each future creation and input checks current membership, including bound review
inputs and same-session continuations. Excluded bound contexts refuse without
substitution; running calls retain their actual accounts and collectors. Actual
close may drain after exclusion. Empty capacity and missing declared review routes
hold the affected operation. Partial review route declarations need not claim
bindings for every possible account; a future opening needs its own selected
declaration, and bound inputs must match their original route. Public labels and
declarations alone prove no registered site, available account or native identity.

Actual rollout still needs compatible installed protocol/caller/route/model and
resource capacity, legal current method/material/history, genuine receiving,
accepting responsible Root and delegated builders/testers, separate continuing
ordinary review and sole report integration, Work/Branch/Reviews sole integrators,
five separately admitted QA packages then separate consolidation, real full
returns and downstream processing. Source/hash/fixture success proves none of
those encounters. No physical reclamation, exact read isolation, multi-file
atomicity or noncooperating-writer CAS is claimed.


Prospective bounded Work catalog completion is an explicitly selected draft delta:
`draft-current-configuration --bounded-work-log` retains all seven original targets
and changes only the Work integrator completion method. Original policies/grants
remain immutable. Fresh basis/selection and real prospective completion authority
are still required; no old job can inherit it. The exact catalog/ref custody APIs,
receipt shapes and interruption limits are in [bounded-catalog.md](bounded-catalog.md).

## Narrow future operating scopes

`draft-current-configuration --scope-options PUBLIC_JSON` can be combined with
`--source-task`, `--bounded-work-log` and the exact `--retention-library` selector.
The optional JSON has only these fields:

```json
{
  "read_roots": {"work-proposer": ["/authorized/exact/report.md"]},
  "neutral_startup": ["work-proposer", "work-integrator"],
  "package_scoped_cleanup": ["qa-cleanup"],
  "task_text": {
    "work-proposer": {
      "authority": "EXACT EXISTING AUTHORITY TEXT\n\nApproved phase clarification within existing rights.",
      "purpose": "Bounded phase intent and rationale."
    }
  },
  "exclusions": ["/known/held/path"],
  "linked_repositories": {
    "branch-integrator": [{"repository": "/authorized/release", "common_git": "/associated/.git"}]
  }
}
```

Read roots replace future task reads with nonempty narrower existing/release
scopes. The selected provider's exact `retention.py` is also permitted; its
parent library, home and AI are not general read grants. Choose exact safe report
files/directories and needed source directories, not an ancestor containing an
exclusion. Keep the six catalog reads explicit; the bounded old log has its own
prefix/opaque-conservation procedure and needs no whole-log read grant.
Exclusions are a lexical monotonic union with the original list. Supply every
actually identified current exclusion from the operating bounds, including
known mixed streams and the held Root runs subtree; do not query them or seek
aliases. Unknown derivatives remain held, never implicitly cleared.

Neutral startup selects `explicit-packet` for named coordinator tasks and removes
AGENTS/WORK_LOG templates before source-manifest acquisition. The release and
prompt also filter them before access, and app-server startup disables project
doc loading. Necessary source/report operations remain typed as before; this
is not a relabeling as report-only, an exact model read-isolation claim, or a
change to the genuine coding Root's context. Select neutral startup for every
coordinator whose startup must use explicit packets. Every scoped/read/startup
change must belong to the prospective task allowlist.

`task_text` is an explicit map of existing task IDs to nonempty selections of
their existing `authority` and/or `purpose` string fields. It adds no task field.
Selected text uses the existing nonempty 16000-byte text limit. An authority
replacement must retain the entire prior string verbatim and append a nonempty
clarification after two newlines; an identical authority is also allowed when
reconstructing an existing selection. Purpose may be replaced with bounded phase
intent. Every named task must appear in the basis's prospective `--task` list.
Unknown tasks, fields, nontext values, blank/oversize text and shortened or
rewritten authority refuse. Messages and attachments cannot select this option.

Use the actual reviewed clarification and actual existing authority prefix in a
separate public scope-options file, then pass it to the draft command. Save the
returned candidate at its declared path, obtain a fresh basis and select using
the existing Work procedure above. Both drafting and validation reconstruct the
exact explicit text map. Editing candidate text without that selection refuses;
typed access/effects, bindings, models, roles, routes, scopes, consumers, limits,
debts and retention are still controlled by their existing independent fields.
No selector (or an empty `task_text` map) leaves task text unchanged. This is
source support for prospective selection, not deployment or evidence that a
classifier, consumer or receiving encounter succeeded.

`package_scoped_cleanup` is an **UNSELECTED opt-in narrowing**, limited to the
existing software QA cleanup phase. It adds required per-package admission and
`package_narrowing:true`; reads/writes/procedure must remain under the task's
existing access roots, writes under its write roots, and ordinary execution
cannot enter the cleanup receipt. Its configured cwd is a working directory,
not a new read grant. It changes no role, effect, network, capacity or native
owner right and must belong to the selected prospective task allowlist.
Software admission must separately include that exact cleanup task scope and
evidence. Execution-only admission does not imply cleanup. Preserve actual
consolidation/cleanup, independent acceptance and current qualification/Branch
receiving; metadata selection grants none of them. The unchanged ordinary
acceptor rules may admit a genuinely selected Work actor distinct from the
actual worker, controller and software actor. No outside-Work/Root gate is added.

A linked-repository pair adds a separate conditional common-Git ceiling for an
already package-scoped Branch/QA task. It does not add general scope_roots,
canonical writes, network, refs or acceptance. The paired repository must already
be under its task's ceiling. A package using that common path must have that
exact repository cwd and freshly matching `git rev-parse --path-format=absolute
--git-common-dir`; mismatch refuses. Admission still supplies the exact read and
write roots, local-ref procedure/resources and accepted association. For the
existing AI linked checkout, the known common path is `/home/nes/ai/.git`, not
an ancestor grant to `/home/nes/ai`. The declared association is checked at use;
it is not a historical map or deployment qualification.

`repository_reads` is an **unselected opt-in repository identity capability**.
The scope-options map names existing read-only Branch/Reviews source proposers
and selects `[RELEASE]` or a subset of the exact identities admitted for that task
by `read_ceiling_extensions`. Each named task must be in the prospective task allowlist.
This records `repository_reads` on that task without changing its effect read
roots. For a package-scoped task the admission must separately select a subset
in its own `repository_reads` list; absence grants no repository identity read.

Only native Branch association and original Reviews component checks use this
capability for the exact repository operand. A child file or procedure cannot
use it as a read root. Actual source material paths and immutable Git pins keep
their existing authority, history and acquisition guards. The original package,
accepted association, context, capability, collector, resources and native
lifecycle are still checked. It grants no general repository filesystem read,
write, native turn, old-hold disposition or ordinary acceptance.

`read_ceiling_extensions` is a normal configuration transition for existing
source/report-authorized tasks. Every affected task must appear in the fresh
`current-configuration-basis --task` selection. For example (pins are placeholders):

```json
{"read_ceiling_extensions":{"branch-proposer":{
  "configuration":"CURRENT_DIGEST", "role_owner":"UNCHANGED_OWNER",
  "original_grant":"ACTUAL_ORIGINAL_GRANT_ID",
  "authority":"Attributed genuine Work choice and rationale",
  "source_authority":"Attributed concrete source owner's repository/component/material binding",
  "read_roots":["/exact/repository/src/component.py","/exact/safe/procedure.md"],
  "repository_reads":["/exact/repository"],
  "components":{"component":["src/component.py"]},
  "source":{"repository":"/exact/repository","commit":"FULL_40_HEX_COMMIT",
            "files":{"src/component.py":"SHA256"}},
  "safe_files":{"/exact/safe/procedure.md":"SHA256"}
}}}
```

The compatible shape deliberately requires additional pins beyond authority
strings: exact regular tracked files at one immutable commit in a standalone
repository, and/or explicitly supplied safe report/procedure files. For reports
alone use `source:null`, `components:{}`, `repository_reads:[]`. Roots equal these
files exactly (maximum 64, 1 MiB each, 4 MiB total per task); directories, Git
metadata, startup AGENTS/WORK_LOG, profile/excluded/ancestor and symlink paths
are refused before material acquisition. A linked worktree currently requires
a separate concrete source-owner Git binding and is unsupported by this option.
Tracked source is verified before working-file bytes are read; no untracked
body discovery is used. Repository identities confer no directory access.

The extension adds the same exact files to package-narrowing `scope_roots`;
actual admissions must still narrow read/procedure/repository rights. It keeps
cwd, writes, sandbox, network, operations, model, owners, recipients and capacity
unchanged. Separate existing narrowing options can further restrict reads/cwd.
It does not add QA execution authority. Original grants, revocations, frozen
historical policies and current-to-original configuration bridging stay intact.

Draft validates current digest and enrolled owner/grant; normal basis/apply
revalidate material, actual original Board bindings, issuer and the whole fresh
journal basis. Only the existing genuine Work issuer can select. Neither the
Work/source authority text nor a safe-file hash authenticates an external source
owner's consent or proves absence of secrets. That owner supplies the public
material classification and concrete binding; Work selects it. Filesystem/Git
immutability and absence of hidden Git object-store indirection are cooperative
owner obligations, not OS read isolation or noncooperating-writer CAS. Preserve
all known exclusions. This policy change cannot use source-only/fixed8 repair.

`package_scoped_proposals: [EXISTING_BRANCH_PROPOSER]` is an **unselected opt-in
narrowing** for the existing read-only software Branch proposer. It requires
per-package admission with `package_narrowing:true`. Its reads, writes, cwd and
procedure obey the same narrowing guard as cleanup; no ordinary adapter can
enter that proposal scope. Role, phase, binding, capacity and response routes
stay unchanged. Software admission must explicitly include this proposal task
alongside the actual QA tasks under the ORIGINAL package. Its scope supplies
the exact accepted `branch_binding`, and, when needed, the separately selected
`repository_reads`. No separate Branch package or Work-role substitution is used.

For software-admitted downstream proposals, scheduling checks the original
accepted association and exact collected QA cleanup qualification return or
configured Branch handoff, every original member, package, attempt, source
result and current authority. A body claiming ancestry is insufficient. An
internal response retains its whole original result; an addressed handoff
retains the nested whole `source_result`. Actual QA execution and independent
acceptance remain prerequisites for cleanup qualification. Admission itself
asserts neither native owner consent nor semantic acceptance. Omitting these
options preserves the existing direct owner-admission and Work/Reviews routes.

The draft records its source-task list and scope options so exact-delta
validation can reconstruct them, including read narrowing after source additions.
Original configs/grants/job policies remain immutable. Configuration basis binds
historical artifact blobs by their retained key and length only: it never
acquires or rehashes those bodies. Their body integrity remains unobserved there;
needed permitted bodies are validated at their own acquisition boundary.

## Exact original owner disposition before transition

Prefer the existing procedure when its real local conditions truthfully permit
the next operation. The current-config transition grants no historical-owner
operation. While ORIGINAL_CONFIG is still current, actual Work can take
`processing-basis`, issue an appropriate bounded preparation capability with
`delegate-processing --selection PREPARATION`, then request:

```sh
RELEASE/tools/coordinator-runtime/coordinator --config ORIGINAL_CONFIG \
  processing-owner-source PREPARATION_CAP Work legacy-disposition Work
```

ProcessingBoard verifies retained owner authority; the source projection no
longer requires reopening revoked intake. This returns the exact prior hold,
effect jobs and `local_resource_disposition`:
all unresolved local role effect jobs, uncollected originals linked through jobs
OR events (including classifier/ACK/control attempts), nonpublished file intents,
unreconciled ordinary intents and retained resource leases. ALL local epoch165
obligations count, not just an apparently quiet next job. A free service lock,
old numeric END or absent publication intent supplies no missing fact.

Collect/release and explicitly revoke preparation authority; take a fresh
`processing-basis`. Actual Work selects the exact request in `owner_operations`
of a fresh `delegate-processing --selection OWNER_SELECTION`. The request shape
is `{kind:"legacy-disposition",role:"Work",target:"Work",prior:EXACT_HOLD,
receipt:{collector:ACTUAL_ORIGINAL_COLLECTOR,evidence:[ACTUAL_EVIDENCE],
remaining_holds:[UNDISPOSED_RESOURCE_CONSTRAINTS]}}`. The genuine original Work
owner, under its existing verified processing-owner authority, then invokes:

```sh
RELEASE/tools/coordinator-runtime/coordinator --config ORIGINAL_CONFIG \
  processing-owner-apply OWNER_CAP --request EXACT_REQUEST
```

Nonempty holds record disposition without clearing the fence or altering old
jobs/effects. Empty remaining_holds is truthful only for an independently
supported exact prospective-resource disposition AND no listed local blocker;
apply rechecks all local conditions transactionally. External old44/17 custody
is separate and remains conserved. It is neither automatically cleared nor a
reason to invent local blockers. Source-only work cannot establish actual
eligibility, owner availability, collection, consent or exact-resource evidence.
Do not fill an unknown with `[]`, reopen revoked intake, borrow an owner or
fabricate a historical scope map. If conditions do not pass, retain the affected
effect hold and return the concrete missing fact to actual Work. This correction
adds no Work-account framework or blanket waiver.


### Explicit public protocol upgrade (774)

The previous selectors freeze `codex`, `protocol_cli_version` and
`protocol_qualification`; neither editing those fields nor changing a config
label is an accepted protocol transition. To preserve 0.166.0, keep its actual
executable available and leave these selectors unchanged. This mechanism does
not install, retain, move or manage old binaries. Replacing the globally selected
binary would break its actual-version preflight until an accepted selection.

A protocol upgrade uses the same draft/basis/select commands with an exclusive
`--scope-options` object `{"protocol_upgrade": CHOICE}` and no `--source-task`.
Select all eight existing tasks with `--task`. Task owners, rights, models, CWD,
network, effects, original grants and historical policies must remain identical.
The ordinary release relocation still applies; whole-source and protocol
acceptance by the actual parent/Work remain necessary before use.

CHOICE has exactly these fields:

* `configuration`: digest of the actual current configuration; `owner`: its
  genuine Work owner/software grantor; `authority`: that owner's concrete
  decision and trusted public acquisition/provenance evidence.
* `public_package`: `{name:"@openai/codex", version:EXACT_VERSION,
  registry:"https://registry.npmjs.org", integrity:EXACT_SHA512_SRI,
  tarball:"https://registry.npmjs.org/@openai/codex/-/codex-VERSION.tgz"}`.
  The real Work issuer must verify this public package and the extracted
  executable mapping. These recorded facts are attributed owner evidence, not
  registry authentication by this offline code. A publication or mutable JSON
  claim alone supplies no compatibility or selection authority.
* `codex`: new absolute canonical executable file, `executable_sha256`: its
  actual bytes, `cli_version`: its exact `codex-cli VERSION` output. Use the
  actual extracted public executable, with no mutable wrapper/symlink.
* `qualification`: new absolute public receipt file,
  `qualification_sha256`: its bytes. The receipt must name that exact
  `cli_version`, the `checked` fields below, and `settings_check`.
* `schema_files`: exact relative filenames below mapped to SHA256. These are
  the installed candidate's generated experimental JSON schemas beside the
  receipt: `v2/ThreadStartParams.json` (`ephemeral`, `model`, `config`),
  `v2/ConfigReadParams.json` (`includeLayers`), `v2/ConfigReadResponse.json`
  (`config`), `v2/ThreadUnsubscribeParams.json` (`threadId`), and
  `v2/ThreadDeleteParams.json` (`threadId`).
* `settings_check`: the exact public own-empty-config strict-metadata record;
  `settings_sha256`: its actual bytes. This record is pinned and parsed, while
  its substantive strict-metadata acceptance remains the parent's explicit
  qualification decision.

Draft, basis and apply independently recheck these pins, real schema properties
and the actual executable's `--version` (10-second child bound, collected before
return). This executes no app-server, model, profile, store or provider probe.
The existing app-server preflight still checks actual runtime version; this
schema/metadata receipt makes no app-server/model/store compatibility claim.
Pins provide cooperative change detection, not atomicity against another writer.

Application additionally uses the existing source-generation stop fence: every
outgoing selected controller must have its numeric parent END and supported
processing release, with no uncollected attempt or active service. Existing
active-capability and cooperative-lock refusals still apply. Old contexts,
callers, collectors, jobs, grants and binary qualifications remain their actual
originals. Only future admissions after parent END/release may use the new
selection. Source staging and fixture success are not live adoption.
