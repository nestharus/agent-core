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
`--source-task NAME` adds only the four public release tool directories to an
already source-authorized task's read roots. For already package-scoped Branch
or QA tasks it also admits this exact repository root as a scope ceiling for
CWD/ref organization. Each actual package still needs its narrower procedure,
paths and resource evidence through existing admission; no canonical write
root, network capability or operation is added.

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
replay the selection; old-config writers refuse and the selected digest is
unique. An unsupported rollback refuses; a later compatible release uses a
fresh explicit configuration path/basis/selection, preserving all versions.
The API offers no restoration of old grants or incompatible old selectors.

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
completed processing frontier. Today's selected pool is automatic 2/3/5, excluding
0/4. The user can change ordered membership live through the existing public
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
