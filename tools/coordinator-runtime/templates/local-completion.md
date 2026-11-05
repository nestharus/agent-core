# Staged producer completion and later workflow duties

This contract applies to routine staged file workers. DONE means their current
local construction/verification obligations are satisfied; it does not mean
canonical publication, actual consumer processing, review or goal acceptance.
PARTIAL/FAILED/UNKNOWN preserve genuine local blockers. Retain full original
failures/unknowns, including resolved history. Never empty those arrays to obtain
publication. The service preserves originals and uses the same assessment in the
publisher, task finisher and delegated routine collector.

Every role task also uses the shared OUTER contract emitted by
contracts.task_result_instructions(). Its required keys are semantic, summary,
category, findings, failures, unknowns and artifacts; only handoffs,
no_handoff_reason and completion are optional. Dissent belongs in findings as
attributed data, for example {kind:"dissent",author,source,meaning}. If it exposes
unresolved local work, retain that work in failures/unknowns and remain truthfully
partial/blocked. Neither a finding nor data conservation resolves a local defect.

Live clarification and final collection share concrete missing-field, extra-field,
type, category and array diagnostics. For a repairable outer mismatch, the SAME
owned producer can use its ONE supported idle continuation. The complete original
decoded JSON value and the later return remain separate, with issues and command
identity. Preserve valid original findings/failures/unknowns/artifacts/handoffs as
verbatim prefixes; malformed non-list findings/failures/unknowns become the first
item of their corrected list, never fabricated []. Unsupported/malformed array
fields must also be conserved exactly in findings, for example:

```json
{"kind":"outer-contract-original","fields":{"dissent":[{"author":"original reviewer","meaning":"Exact original dissent"}]}}
```

This is the producer's explicit new representation of original data, not automatic
key stripping, runtime normalization, effect authority or independent semantic
acceptance. The original stays untouched. For a non-object original use fields
{"$result":ORIGINAL_JSON_VALUE}. Final collection refuses erased history, omitted
original-field data or a still-invalid outer contract. It never runs a second
clarification or resumes an ended owner. no_handoff_reason:null is valid with
nonempty handoffs; empty/no handoffs retain the existing meaningful-reason policy.
The payload_json provider envelope is unchanged.

Artifact items are explicit absolute paths or {path,...metadata}; nonempty
{files:[items],...metadata} groups retain their grouping/common metadata, without
an invented group path. Limits are depth4 and 64 leaves. Handoffs retain exact
recipient/kind/text/ref/required=settled. An unfamiliar bounded kind label travels
only as an addressed question retaining the original handoff, never an execution
or acceptance grant. If artifact/handoff items are malformed, conserve the entire
original array in outer-contract-original.fields and keep its valid items as
verbatim prefixes of the repaired list. Missing paths require genuine evidence;
the original data and adverse history cannot be dropped to repair representation.

Add completion with version1, local=ready|blocked, failures, unknowns and tools.
Each failure/unknown index must be covered exactly once. Unknowns may contain
original prose or objects combining several responsibilities. Preserve that
original entry and split its proof into individual typed duties. For example,
when unknowns index0 describes later publication/custody and index1 describes
review/acceptance this producer does not establish:

```json
{
  "version": 1,
  "local": "ready",
  "failures": [],
  "unknowns": [
    {"index": 0, "duties": [
      {"status": "deferred", "owner": "controller", "duty": "publication",
       "reason": "Controller still checks canonical preimages and publishes."},
      {"status": "deferred", "owner": "controller", "duty": "artifact-custody",
       "reason": "Controller still conserves required bytes and witnesses."}
    ]},
    {"index": 1, "duties": [
      {"status": "boundary", "owner": "outside-workflow", "duty": "review",
       "reason": "This local result does not establish the selected owner's review."},
      {"status": "boundary", "owner": "outside-workflow", "duty": "acceptance",
       "reason": "Outside acceptance remains unclaimed."}
    ]}
  ],
  "tools": []
}
```

Each indexed unknown has either one {index,status,owner,duty,reason} or one
{index,duties:[{status,owner,duty,reason},...]}, with 1..16 distinct members. Duty
values for controller are EXACTLY publication, artifact-custody,
effect-reconciliation or delivery, bound to the actual runtime actor. A necessary external deferred duty
must name an allowlisted real recipient and its required=settled handoff. A review/
acceptance statement this local result does not establish may be status=boundary,
owner=outside-workflow, duty EXACTLY review OR acceptance; split a combined
statement as above. Never put a prose sentence or combined list in these enums.
Boundary is NOT a new assignment,
acceptance claim or waiver of a required handoff. Unresolved current local issues
stay status=unresolved and local=blocked; they do not become deferred by renaming.

For each resolved failures[index], return status=resolved, evidence consisting of
exact own declared report {path,sha256} entries, and verification_items containing
explicit actually observed successful command-item IDs. Every failed/nonzero tool
item also needs its own tools entry {id,status,reason,evidence,verification_items},
with status=resolved|expected. Preserve failed verifier IDs, numeric ends, report
repair evidence and original text. Do not select an unrelated later zero. Own
artifact hashes are checked against conserved exact bytes; actual successful item
IDs are checked against the owned control's captured metadata. These qualify the
producer's resolution claim, not independent proof of the semantic explanation,
universal correctness, review acceptance or absence of other defects. Unknown or
unsettled tool metadata remains a separate hard fence even if a later item exits0.

Inherited failures may instead use {index,status:"inherited",source,reason}.
The source is an exact object supplied in TASK_CONTEXT.inherited_failure_sources:
kind, id, sha256 and a typed JSON path into a frozen event or linked prior result.
The failure entry must equal the supplied original JSON value. No filename, prose
historical label or producer-invented source qualifies. Explain why it creates no
unmet current local duty; this is a producer scope attestation, subject to later
independent interpretation, never semantic proof of non-applicability. Original
facts, owners, source/effect/consumer holds remain unchanged. This disposition
does not mark the failure resolved or settle its old job. If it also causes a
current local defect, retain a separate current unresolved entry and local=blocked.
Current observed adverse tools retain their separate proof obligations regardless
of an inherited failure. Live and collected checks bind the same frozen sources.

tools covers ONLY observed adverse protocol items, exactly once. When all observed
commands succeeded, tools MUST be []; successful commands require no adverse
disposition. Visible exec_command chunk labels are a different namespace from
provider protocol-item IDs. Neither establishes an OS handle. Never guess a
correlation. Optional completion.reported_commands may retain uncorrelated producer
claims as {namespace:"producer-visible",label,status,exit_code,reason}; exit_code is
numeric or null. Those claims cannot discharge adverse items or prove verification.

If actual item IDs are not visible to the producer, or an otherwise DONE return
lacks a coherent explicit contract, the service uses the same grammar/ownership/
evidence checks while live as it does after collection, within its one supported
same-owned-idle continuation. It supplies bounded safe actual item metadata and
asks for faithful clarification/remaining verification in the SAME context. A
semantic PARTIAL/FAILED/UNKNOWN continuation for a staged task also supplies its
available own metadata, within that same single idle continuation budget. This
does not infer missing commands, provider failure or a reason to promote DONE.
Live checks read only declared or mapped staged own files under the current attempt;
they are preliminary byte checks, not capture, process collection or publication.
Post-collection assessment requires complete tool metadata and conserved bytes.
Specific clarification issues and the full original return, including original
completion/labels and history, remain durable. The
original valid arrays must remain verbatim prefixes of the final arrays (malformed
artifact/handoff items use the explicit conservation rule above); no blind stage
rewrite, canonical write, new session, profile handoff, repeated clarification or
per-job human permission follows. Exhausted/ambiguous/unresolved evidence stays
held and causally delivered. No text heuristic auto-classifies RESOLVED strings.

The model writes only mapped staged proposals/reports. The true service owns
retention.snapshot_lock, exact regular-file byte/inode/mode/owner preconditions,
durable compressed BEFORE-only canonical recovery backups, same-inode writes,
fsync/readback and publication/effect receipts. Staged checks cannot claim that
canonical discipline. Source/resource/revocation/current actor fences remain.
Same-inode partial writes and multi-file uncertainty retain all original/proposed/
backup evidence; never blindly replay, roll back peers or infer a lost receipt.
