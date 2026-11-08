# Existing historical software journal verification

Current metadata residency uses the original max_result_bytes/max_jobs ceilings
and the existing metadata-only journal-page headroom check. It does not walk or
measure old captures. Expiry/revocation never implies retirement or starts the
processing-completion retention clock.

This operator interface uses preexisting db1 journal records. No witness had to
be recorded before expiry. It does not call processing/prospective currentness,
reissue authority, acquire old source/task/packet/return bodies or opaque native
identifiers, or change an original record. Its integrity model is the existing
cooperative same-account journal and Board model, not adversarial authentication.
Never synthesize a session environment or treat possession of a scope UUID as
principal authentication.

The original Reviews data owner can select current access to their original
software journal metadata. Both that owner and the configured Work principal
must still have current visibility of the exact original Board post. Original
stopped software grant, issuer, journal file identity and original configuration
binding must authenticate using ProcessingBoard. Issuer status alone supplies
neither source access nor native ownership. If this specific owner/visibility
relationship is unavailable, return it to its actual custodian; there is no
universal user/globalRoot consent requirement and no fallback to body-reading.

Use an already initialized original journal, with the explicitly selected
current configuration/source. The additive current metadata table can be
initialized by Store on that journal. This is a current data delegation, not a
new historical witness. The existing configuration bridge must still bind the
original stopped grants; a metadata selection cannot manufacture that bridge.

Prepare one small public selection JSON with exactly these keys:

* `identity`: exact `job`, `attempt`, `event`, `source_hash`, `task`, `capability`,
  `epoch`, `component`, `collector`, `post` from the original collector's safe
  metadata. No discovery, opaque handle or fresh task/source substitution.
* `principal`: configured actual Work session UUID.
* `configuration`, `implementation`: explicit current configuration digest and
  coordinator module SHA256 map nominated from the genuinely selected current
  public source. They must match on selection and every use. Do not infer source
  adoption by automatically pinning whatever happens to be installed.
* `purpose`, `authority`: current bounded purpose and actual data-owner authority.
* `expires`: a finite Unix timestamp within one hour.
* `public_roots`: at most 32 unique independently public absolute roots whose
  original read-membership may be compared. All current exclusions apply before
  metadata. Selecting a root does not grant its contents or establish membership.
* `fields`: exactly `job-lineage`, `source-header`, `launch-proof`,
  `original-epoch-birth`, `frozen-standalone-policy`, `context-collector-links`,
  `public-read-membership`, in that order.

In the **actual original Reviews owner's session**:

```
coordinator --config CURRENT.json historical-metadata-authorize --selection SCOPE.json
```

In the **actual current Work session**, use the returned metadata_access UUID:

```
coordinator --config CURRENT.json historical-metadata-project UUID
coordinator --config CURRENT.json historical-metadata-compare UUID --candidate PUBLIC-OPERANDS.json
```

Comparison operands are exactly `{"reads":[],"writes":["/public/proposed/path"]}`.
Original data owner revokes with `historical-metadata-revoke UUID`. Current
principal, owner, visibility, expiry, revocation, source and configuration checks
repeat on every use. The Python functions are `authorize`, `project`, `compare`,
`revoke` in `coordinator_runtime.historical_verification` with explicit runtime
and Work/Reviews ProcessingBoard arguments. No service or processing capability
is installed by these calls.

Projection verifies only the stated relationships in the cooperative journal:
exact source hash/header/member, job/attempt/controller, original Work grant,
original configuration/task hashes and absent admission, original epoch and
observed source/job births, and call/context/snapshot component/capability/
collector. Frozen task row immutability is inherited from db1, not newly imposed
as historical evidence. Full task/body hashes are not recomputed. Original
grant/task/epoch hash agreement is an attributed preexisting proof, not a native
signature. Context rows remain cooperative mutable evidence. Changes outside
the projected relationships cannot be detected by this API.

An original Source may have launched under a later Work-selected configuration
than the initial stopped software grant. The API authenticates that original
immutable configuration transition's Work issuer, original configuration and
task allowlist, and matches the original epoch/task hash to the launch proof.
It does not demand that a newly admitted task appeared in the initial grant
catalog, or use a current task as its substitute. Missing transitions refuse.

Only positive read-root membership for the caller's authorized public operands
is projected. SQL compares explicitly named public operands within the frozen
policy; it never exports unmatched roots or cwd. No opaque identity is acquired
even to hash it or return equality. Native identity/material and source-body
integrity consequently remain unverified. Unknown executor writes, unbounded
retained resources, native owner/physical state and original holds persist.
This is logical SQL field projection, not a claim about isolated physical
SQLite page reads. The public projection is explicitly incomplete.
A public overlap gives CONFLICT. Public subset disjointness gives UNKNOWN with
eligible:false. The interface gives no old input/closure/execution, new operation
admission, resource release or ordinary effect permission.

Actual fa6 access/verification is not performed by development. Its supplied
END6/incomplete/interrupted/effects:none/conserved hold/physical UNKNOWN and old
a99 QA unperformed remain. No service is active; bounded14801 was END0/released
and3d97/c025 revoked, as supplied. Source adoption and independent consequence
review/Frame/WorkDecide remain outside this interface.

Offline qualification: `python -B tools/coordinator-runtime/tests/run_historical_verification1041.py`.
Owned fictional originals use real db1 intake/reservation/frozen-policy/birth and
software proof binding; native call/context transport and Board session/lifecycle
are explicit fiction. No actual provider, live journal or native state is used.
All qualification outputs KEEP: actual processing completion+24h AND all holds.
