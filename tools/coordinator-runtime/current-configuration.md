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
routine publication targets, limits, exclusions, holds and policies cannot
change through this narrow API. Work selects the prospective task allowlist
with repeated `--task`; newly added source scopes must be in it. Current
processing can use only those tasks and genuinely future sources. It cannot
select retained events, historical control recovery or legacy-hold disposition.

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
completed processing frontier. Pool control must remain automatic 2/3/5, excluding
0/4; receive authorization is distinct. Each future input/allocation still checks
membership; admitted originals retain their accounts/collectors.

Actual rollout still needs compatible installed protocol/caller/route/model and
resource capacity, legal current method/material/history, genuine receiving,
accepting responsible Root and delegated builders/testers, separate continuing
ordinary review and sole report integration, Work/Branch/Reviews sole integrators,
five separately admitted QA packages then separate consolidation, real full
returns and downstream processing. Source/hash/fixture success proves none of
those encounters. No physical reclamation, exact read isolation, multi-file
atomicity or noncooperating-writer CAS is claimed.
