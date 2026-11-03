# Staged producer completion and later workflow duties

This contract applies to routine staged file workers. DONE means their current
local construction/verification obligations are satisfied; it does not mean
canonical publication, actual consumer processing, review or goal acceptance.
PARTIAL/FAILED/UNKNOWN preserve genuine local blockers. Retain full original
failures/unknowns, including resolved history. Never empty those arrays to obtain
publication. The service preserves originals and uses the same assessment in the
publisher, task finisher and delegated routine collector.

Add completion with version1, local=ready|blocked, failures, unknowns and tools.
Each failure/unknown index must be covered exactly once. For example, when unknowns
index0 describes the still-pending controller publication duty:

```json
{
  "version": 1,
  "local": "ready",
  "failures": [],
  "unknowns": [{
    "index": 0,
    "status": "deferred",
    "owner": "controller",
    "duty": "publication",
    "reason": "Local staged files verified; the real controller must still check current canonical preimages and publish."
  }],
  "tools": []
}
```

Controller duties are publication, artifact-custody, effect-reconciliation and
delivery, bound to the actual runtime actor. A necessary external deferred duty
must name an allowlisted real recipient and its required=settled handoff. A review/
acceptance statement this local result does not establish may be status=boundary,
owner=outside-workflow, duty=review|acceptance. Boundary is NOT a new assignment,
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
universal correctness, review acceptance or absence of other defects.

If actual item IDs are not visible to the producer, or an otherwise DONE return
lacks a coherent explicit contract, the service may use its one existing supported
same-owned-idle continuation. It supplies bounded safe actual item metadata and
asks for faithful clarification/remaining verification in the SAME context. The
original arrays must remain verbatim prefixes of the final arrays; no blind stage
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
