# Corrected combined candidate — F1–F5 and explicitly selected Work V2

This candidate combines the original six core files and twelve adapter files.
The original sources are conserved byte-for-byte in this task's output/originals
and remain unchanged at their producer paths. This is a source candidate for
/home/nes/ai/tools/branch-stack; it has not been installed, committed or published.

## Changed contracts and rationale

| Finding | Correction | Boundary |
| --- | --- | --- |
| F1 | Lock acquisition never writes or truncates the opened inode. After flock, fstat binds the actual lock; the journal must be a distinct regular, nonsymlink state file. CLI once and adapter check_once pass the protected journal and held FD. Constructor/save recheck collision. | Stable owner-controlled directory entries and the common locking discipline remain caller duties. No hostile-rename/global race exclusion is claimed. |
| F2 | Inactivity/PR number cannot suppress explicit whole_landing. Exemption requires explicit deferred=true, authoritative trigger=false and a validated deferral reference. cloud_demo and other critical records remain independent and actionable. | Ordinary upstream landing/inactivity scope only; a current Main/cloud-stage/demo/conservation/review/repair obligation is not recast as ordinary landing. |
| F3 | A selected active descendant with a necessary unlanded ineligible ancestor produces UNKNOWN, held_units and manual_frontier, with dependency/order intact and no operation for that group. | Conservative interpretation pending Work9595, not an owner-confirmed rule. No new operation-specific override is invented. |
| F4 | Probe versions must be exactly a dict before key/value access. | Narrow container-type fix; not a claim of complete hostile-schema validation. |
| F5 | One effective unordered pair at current versions/Main is resolved per check; latest applicable clean clears it. Pair spelling is normalized for plan identity. | History chronology stays significant. Distinct check IDs repeat; same-check ambiguous attempts never blindly replay. |

Held/inactive tips remain DEFERRED. Shared held ancestors block all dependent
groups; independent eligible groups continue. Positive current reactivation
eligibility or an existing exact landed/ancestry mapping is required by the
ordinary existing schema to remove the hold. There is no generic authorization
to preserve/materialize a still-held unlanded ancestor. A future operation-specific
selection needs its actual parent/Work contract; this candidate does not invent one.
Unknown/held groups receive no EXACT_ORDER_AND_SEMANTIC qualification.

F1 no longer stores owner/PID bytes in lock files, including existing lock
content. flock is still the process-lifetime cooperative lease. Never unlink or
replace the canonical lock inode while callers can run. Use:
owner_lock(lock_path, owner, journal_path=journal_path) as lock_fd, then
DeliveryJournal(journal_path, lock_fd=lock_fd). The previous two-argument lock API
still flocks without writing, but cannot validate an unsupplied journal binding.
The actual CLI/runtime paths always supply that binding. Symlink lock paths are
rejected by O_NOFOLLOW; journal symlinks are rejected before loading/writing.
Atomic journal replacement does not truncate a linked inode. Rechecks improve
cooperative diagnostics; they are not a global concurrent directory-freeze proof.

Pair normalization affects the planner's semantic snapshot_digest and plan_id:
only pair units operand spelling is sorted. Probe chronology, evidence references,
exact versions and Main remain bound. once's startup snapshot_sha256 still checks
the original raw immutable bytes separately.

## Deliberate Work V2 selection

V1 remains rfq.branch-deferral-eligibility-projection/1 and is the default.
A missing V1 caller trigger remains UNKNOWN with the original snapshot unchanged.
V2 is not interpreted under V1 selection.

Select capability=rfq.branch-deferral-eligibility-projection/2 in
apply_on_encounter, or deferral_capability with that literal in check_once.
Also supply work_owner and work_decision from the separately admitted current
coordination decision. The supplied exact V2 fixture and work-trigger-decision.json
bind the decision received for this correction. The caller authenticates actual
authority/currentness; arbitrary self-asserted JSON is not authenticated here.

Validation binds repository/PR, the encountered current branch, one entry,
classification, retained active obligations, exact Boolean trigger, explicit
Work owner, identical current decision, decision basis type/nonempty basis,
UTC assertion timestamp and durable-until-explicit-supersession semantics.
There is no heartbeat expiration or inference about code/foundation readiness.
The supplied satisfied=false is the durable authoritative Work selection to keep
whole-upstream deferral, even though foundation readiness itself is UNKNOWN.
A conflicting caller trigger is rejected rather than overriding Work.

Unlisted repository/PRs retain ordinary input rules. Only encountered units are
adapted; the canonical_source is an opaque provenance pointer, never followed.
No ASSIGNMENTS/global inventory, new task/CI ledger or live state is acquired.

The old cloud-demo-to-repair compatibility bridge is removed. The corrected
core retains the original cloud_demo record once, without synthetic duplication.

## Two original expectation replacements

The first joint run used all 72 unchanged original tests and retained its exit1:
70 pass, 2 fail. Both original test sources remain intact under output/originals.

* test_non1230_whole_landing_not_exempt becomes
  test_explicit_whole_landing_deferral_not_PR_number. The correction brief requires
  a positive explicit deferral/false trigger rather than PR-number permission.
  It now checks both exemption and inactive undeferred whole_landing alerts.
* test_new_deferral_entry_active_cloud_closure_still_alerts retains its ID and
  checks exactly the original cloud_demo plus closure/conservation alerts, with
  one cloud reason and no repair compatibility duplicate.

No test is skipped, xfailed or weakened to hide the observed pair-identity failure.
The original five defect controls are also run against the exact original core
as a bounded red reproduction (all five fail), not as a new unchanged full suite.

## Qualification limits and handoff

Use actual per-case results and numeric ends in taskhome reports; historical
counts in the producer reports apply only to their original identities.
The original 36 core/36 adapter behaviors (with the two explicit replacements)
and 27 focused regression cases are selected jointly for the corrected hash.
The histogram fixture retains THREE clean real Git pairs and a conflicting
ordered triple. Native CLEAN remains text-only, semantic=false.

All external board transport in tests is explicitly mocked. Normal enqueue,
notice ACK and manual BOARDWATCH/read do not establish model push. The prior
QA-BRANCH-ROUTE-20261102-01 remains FAIL / NOT WORKING; no live retest ran.
Parent owns proper existing task/account/feed/branch receipt, current authority,
actual native admission, canonical journal retention and installation. QA owns
the announced actual pushed Branch response within30s; that frontier is pending.
No SourcePASS, Ready, actual nativeRFQ, CI, scheduler/service/registration or
people effect is claimed or authorized by this candidate.


## Reviewed occurrence, frontier and Git-format corrections

The R1 acceptance path binds the full immutable snapshot and adapter context to
an occurrence ID, computes observation/plan without persistence, and saves the
accepted observation and check together under the canonical owner lock before
transport. A changed occurrence input is rejected without any journal write.
`accept` returns stored plan/notices/receipt for exact historical replays without
re-observing or sending; `receipt(check_id)` retrieves a legacy check without
inventing a missing input binding. Legacy prepare-only rows cannot be adopted by
an unbound accept. A previously PLANNED runtime replay is receipt-only: callers
must use an explicitly bound delivery operation if intentionally dispatching an
unsent accepted check. AMBIGUOUS is still durable before sender entry; distinct
occurrences continue to repeat actual violations.

R2 runtime status is UNKNOWN for unresolved encountered policy/decoder frontiers.
Known violations and notices remain present and use the normal delivery path;
`known_violations` distinguishes these facts from qualification of the whole
check. The exact outside-explicit-pr-scope-UNKNOWN coverage marker does not make
an otherwise healthy bounded check UNKNOWN. No global PR inventory is required.

R3 this Git backend rejects non-SHA1 Main and selected head/tree/ordered-parent/
physical-base OIDs before initialization or source_getter. Its outer envelope
retains the unsupported-format reason when no strict core probe can be formed.
The core still accepts 64-hex metadata; content/resolution/version/evidence
SHA256 digests are not Git object-format operands. Native CLEAN remains text-only
and semantic=false. No SHA256 backend support or actual RFQ Git input is implied.

The existing F1-F5 and Work V2 boundaries remain. Parent targeted review of these
changed boundaries, commit/signing, installation, actual typed collector feed
binding and live QA remain separate. Prior QA FAIL / NOT WORKING and the later
Work9698 / notice9734 AMBIGUOUS observation are not passes.


## TR-R1-P2-01 — post-replacement directory EIO

The correction conserves the published state instead of restoring stale memory.
Pre-replacement failures remain rejections. Post-replacement failures return or
raise a typed accepted-but-durability-unconfirmed outcome. See ADAPTERS.md for
exact CLI/API status semantics, current receipt binding, the mandatory durable
pre-send marker, historical receipt-only replay and explicit owner recovery.
R2/R3 graph/feed/object-format decisions are unchanged. All F1-F5 regressions
remain applicable; Work9595 remains an unheld interpretation, not a new gate.

The original 113 cases were each qualified: first whole run 107 passed and six
harness errors (missing admitted fixture/mask environment bindings); the six
source-corrected harness cases then passed. Twenty additional controls cover
only this journal publication/durability boundary. The actual initial native1
and setup failures are retained in the task report, not relabeled as passes.
