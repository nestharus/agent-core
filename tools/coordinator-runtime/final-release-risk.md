# Final Branch release risk

This stage assesses the final integrated package after ordinary Reviews and QA
and before final approval/release. Branch's existing repository template is its
consumer. Reuse the proposer task and its existing proposal-to-integrator route;
reuse the sole Branch integrator for disposition/consumption. No fifth persistent
coordinator, new journal table, extra task capacity or automatic risk acceptance.
The public source check is `tools/branch_release.py`. Current configurations are
not edited by this source change: actual owners must select/deliver these source
and template bytes through the existing source-upgrade/admission procedure before
use. A candidate commit is not deployment.

Assess suspicious complexity and strange, opaque or bespoke implementation,
surprising ownership/state/lifecycles, hidden coupling, brittle contracts and how
confidently consequences can be understood. Explain justification, supporting
evidence, counterevidence and limits. Novelty, unfamiliarity, style and line count
alone are not condemnation. Risk is not bug hunting; a zero-bug assessment can
block on consequential uncertainty. No numerical likelihood/calibration claim.

For every factor describe the worst plausible customer consequence; affected
users/customers/tenants and actual cross-tenant reach; update/sign-in availability;
data correctness, confidentiality and sensitivity; duration, real recovery and
rollback. Separate tenants are relevant evidence, not proof of harmless access.
No outage or zero findings does not establish low data-access impact. Compare
likelihood separately from consequence. A bounded UI quirk can reasonably be
accepted or followed up; failed sign-in/update, irreversible corruption and
confidentiality exposure require their own consequential judgment.

The actual authorized release decision distinguishes BLOCKERS, explicitly
ACCEPTED risks with rationale/accountable owner, bounded nonblocking FOLLOWUPS,
and evidence of reduction. Risk need not reach zero. Every factor, consequential
unknown and requested return must be accounted for. The assessor recommends;
only the actual delegated decision owner accepts risk. The validator verifies
structural correspondence, not the truth of prose or an actor's real authority.
Branch acquires/authenticates originals and decisions under existing authority;
do not let the assessor select its own acceptance owner or fabricate evidence.
Hard privacy/unknown-effect custody cannot be waived. Preserve source, collector,
current user-controlled pool membership and pinned static controls,
branch/profile/Work7/QA5, sole-slot, all-hold and 24h
whole-processing retention rules. No check supplies native/provider identity,
processing completion, a missing numeric END or authority for effects/replay.

## Existing result and decision inputs

The proposer returns the complete `final-release-risk-v1` assessment nested in
`findings` of the ordinary result (`kind=final-release-risk`, `category=proposal`).
Branch extracts this value without normalization, retains the whole original and
records its attempt, actual collector and original reference. The existing static
proposal route delivers it to Branch integrator. No new task/config grant is
needed. An existing owned-artifact lane may supply the exact witnessed JSON
instead. All inputs are bounded at 65,536 UTF-8 bytes each; too large means scoped
partial with all originals retained, never silent omission. Duplicate JSON keys,
non-JSON numbers and malformed data refuse. Check output uses a fresh owned path.

`branch_release.py` takes `--current`, `--assessment`, `--disposition`, optional
`--unaffected` and `--output`. See `tests/test_branch_release326.py`'s `packet()`
for a complete synthetic schema example; logical fixture owners are not native
sessions. Schema field sets are exact. No private, held or discovered file inputs.

CURRENT (`schema=branch-release-current-v1`) contains:

- `material`: repository, PR URL/number, ref/incarnation, base/head/tree/ALLparents
  (`parents`), ordered constituents with explicit dependencies, combined_tip and
  relevant contract/config/schema/dependency path-to-SHA256 map (`contracts`). Each
  constituent has pr_url/base/head/tree/depends_on. The last constituent's head,
  tree and PR must be the actual final package; no wrapper PR.
- `evidence`: exactly `reviews` and `qa`, each with kind/original/sha256/method/
  status/material/owner/acceptance/limits/correspondence. `material` is the full
  examined identity, not merely the same head. Reviews status is `satisfied` under
  its OWN method; QA is independently `accepted`. `owner` has actor/authority;
  `acceptance` references the actual prerequisite decision/result. Hashes bind
  acquired original bytes. Coverage/limits remain in the originals and `limits`.
- `gates`: separate ci/stack/approval evidence using the same fields and
  status=satisfied; the check does not replace their actual procedures.
- `release_owner`: actor/authority from actual delegated release authority.
  `recipients`: Work/Root/Reviews, each actor/binding/evidence from current accepted
  responsibility. Root is the actual build coordinator, never a relabeled builder.
- `hard_holds`: explicit privacy/unknown_effects/custody lists from actual
  custodians, each empty only when supported. Nonempty blocks irrespective of
  acceptance. Other retained historical/retention holds stay with their owners;
  this check neither removes nor retires anything.
- `pr_currentness`: reviewed/immediate/fetched_base_sha/fetched_head_sha/
  expected_draft as in the existing production PR currentness validator. This
  check composes that validator and compares the actual package identity too.

ASSESSMENT (`schema=final-release-risk-v1`) contains `basis` with method (same
schema string), material and evidence; `original` with attempt/collector/reference;
status (complete/partial/unknown); `coverage` with nonempty source-bound accounts
for complexity_coupling, lifecycle_recovery, representation_migration,
interfaces_consumers, integrated_interactions and evidence_strength; understanding,
confidence, limits[], unassessed[], factors[] and requests[]. These are assessment
concerns, not a duplicate CRW family/coverage protocol. Unassessed work prevents
completion. Record residual analyzed uncertainty as factors even with no bugs.

Each factor has id/surface/mechanism/likelihood/confidence/understood,
uncertainties[]/support[]/counterevidence[], consequence, recommendation and
hard_boundary (`none`, `privacy`, `unknown-effects-custody`). Consequence has
nonempty accounts for worst_plausible_impact/users/customers/tenants/cross_tenant/
update/sign_in/data_correctness/confidentiality/sensitivity/duration/recovery/
rollback. An inapplicable dimension needs its reason, not an empty string.

DISPOSITION (`schema=final-release-disposition-v1`) has assessment_sha256 and
basis_sha256, actor/authority/record, decision (`release` or `hold`), factors[],
requests[] and limits_rationale. Compute fingerprints with the public module's
`fingerprint`: sorted compact UTF-8 JSON, ensure_ascii=False, allow_nan=False.
This hashing convention is not a new ledger. Bind the exact assessment and CURRENT
basis; repeat the decision after changed material/evidence or explicit unaffected
correspondence. Every factor gets id/outcome/rationale/owner/evidence[]/acceptance/
followup. Outcomes: blocker, accepted, followup, reduced. Accepted requires actual
acceptance actor/authority/record matching delegated release authority. Other
outcomes have acceptance=null. Followup requires owner/scope/due/completion;
otherwise followup=null. Reduction needs actual completion/verification evidence;
an acknowledgment or a hoped-for rollback is insufficient. No factor is erased.

## Material changes and confidence inquiry

Changed head, base, composition, contract/dependency or relevant review/QA evidence
normally requires current assessment and decision. Preserve unchanged originals
proportionately; do not re-review unrelated work solely for a new hash. Explicit
unaffected correspondence has from/to fingerprints, exact `changes` paths from
the module's `changes(before, after)`, rationale, evidence[], actor/authority and
record. Risk correspondence compares full bases and belongs to release authority;
each ordinary gate's own material correspondence belongs to that gate's owner
and procedure. It must explain why the changed relationship leaves the retained
reasoning valid. If affected, reassess affected scope and rerun ordinary gates as
their methods require. A correspondence cannot cross PR/ref/incarnation or change
the risk method. It is an accountable semantic judgment, not proof that a new
hash is safe. New adverse information belongs in current evidence; never hide it
behind an old material hash. Preserve the prior assessment, decision and check.

Risk requests use id/kind/question/why/factor_ids[]/blocking (boolean). Kind scope
routes to actual Work; reduction to the accepted actual build Root; confidence to
Reviews. Output includes those exact recipients and required=settled, for existing
allowed work/result/question delivery only. It does not dispatch or grant effects.
Supply real alternatives to Work; bounded reduction requires separately authorized
implementation. Focused CRW questions ask for reasoned clarity, fragility and
confidence plus any findings, including an honest zero-finding result. Preserve
the unified review procedure and actual original returns, dissent and gaps.

Decision requests have id/state/original/answer/followup. A returned confidence
answer has findings[]/clarity/fragility/confidence/limits[]. Other returned answers
are nonempty text. Pending blocking returns prevent release; a nonblocking request
may become a bounded followup, with state=followup and actual followup fields.
Original/answer may be null while pending; never infer a return from dispatch.
FinalRisk documents these future requests; it launches none itself.

## Operating and rollout boundary

Branch's integrator runs the command in the repository template with fresh exact
owner-acquired inputs immediately before the effect, then checks exit 0 and
ELIGIBLE_FOR_EXISTING_FINAL_GATE. Exit 2, partial/missing/stale evidence, blockers
or a hold stops that exact release. Eligibility is not final approval, CI, QA,
ordinary review completion, risk acceptance, native PASS or permission to merge.
No actual release/admin adapter is added here; ordinary effect authority remains
required. Preserve interruption/currentness uncertainty without replay.

Future authorized deployment: select this commit's tested source/template bytes
through the existing source-upgrade procedure, verify linked source readback,
then have actual Branch owners supply the existing proposal/integrator packet
and accepted recipient bindings. Run the command with actual owned paths; collect
its real original wait, full output and disposition, and recheck currentness just
before the effect. This source-only delivery runs no service, Board, journal,
configuration, CI, Stage, native/provider encounter or PR mutation. Its isolated
fixtures establish refusal/eligibility behavior, not risk calibration or efficacy.
