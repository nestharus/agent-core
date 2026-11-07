# Work-collected independent code review

Actual outside Work owns all operational decisions. This additive path permits
Work to collect a distinct dispatched readonly `code-review-workflow` reviewer
without using persistent native Reviews receive paths. It is source-code review
evidence, never native Reviews impersonation, Source acceptance or rights renewal.
Existing genuine native Reviews review remains optional. Neither path inspects
private platform stores or reconstructs old captures.

Work must independently observe its original numeric process END. Model DONE,
a reviewer's claimed END, file existence and a summary are insufficient. The
trusted local account authenticates Work using its existing actual session and
Board acting-session check. This is an explicit trusted Work declaration of
outside observation, not cryptographic verification of an OS process. Never set
another real actor's CODEX_SESSION_ID; fixture identities below are synthetic only.

Stop the original using its existing control path, collect the SAME original to
numeric END and execute original `processing-release` before source installation.
Then install independently reviewed code at the existing release location and
acquire an exact basis. Stop, release, basis, collection and selection dispatch
before ordinary old-source Access checks. They still enforce original journal,
capability, config, grant, epoch, all original END/releases, finite counters,
expiry, exact preceding binding, Git ancestry, ALLparents and module blobs.
No second lease, hot edit, pin replacement, policy reset or changed release root.

These are inert templates, not commands executed by this worker. Set every path
and value from actual owner-collected records. No example supplies an actor,
original handle, candidate hash or authority on the owner's behalf.

```sh
"$COORDINATOR" --config "$SAME_CONFIG" processing-service-control "$CAP" stop
# Actual original collector waits on SAME original handle, records numeric END.
"$COORDINATOR" --config "$SAME_CONFIG" processing-release "$CAP" \
  --controller "$ORIGINAL_CONTROLLER" --receipt "$ORIGINAL_END_JSON"
# Parent installs exact reviewed candidate at the unchanged public release root.
"$COORDINATOR" --config "$SAME_CONFIG" owner-source-amendment-basis "$CAP" \
  --controller "$ORIGINAL_CONTROLLER" --previous "$PREVIOUS_JSON" \
  --manifest "$CANDIDATE_SAFE5_HASHES_JSON" --module cli.py \
  --module report_repair.py --purpose "$ACTUAL_PURPOSE" > "$BASIS_JSON"
# --module list above is ONLY this candidate's two production modules.
# Use every actual changed module, sorted, for each future candidate.
"$COORDINATOR" --config "$SAME_CONFIG" collect-owner-source-review \
  --selection "$OUTSIDE_COLLECTION_JSON" > "$REVIEW_RECEIPT_JSON"
"$COORDINATOR" --config "$SAME_CONFIG" select-owner-source-amendment \
  --selection "$SOURCE_SELECTION_JSON" > "$SOURCE_RECEIPT_JSON"
```

`PREVIOUS_JSON` contains exact `commit`, `tree`, `parents` (all parents in Git
order). Initial prior source must authenticate every original plan module blob;
subsequent prior source must equal the last selected source exactly. The original
lease did not contain a Git commit field: the actual prior-publication identity
remains Work's independently authenticated binding, alongside the Git/blob proof.

The independent reviewer receives the whole BASIS object and candidate safe5
hash manifest. Its separate public report directory contains exactly these
selected inputs: PRIMARY.md, RESULT.json, LIMITS.md, PUBLICATION.json,
WRITER-RELEASE.json. Whole public files are retained in the immutable journal
review receipt, including partial overall coverage, failures, risks and remaining
duties. Complete coverage of the exact changed code is mandatory; incomplete
module coverage refuses. PRIMARY/LIMITS are retained losslessly, not treated as
an authority-bearing summary. An approved code delta may retain adverse history
and overall rollout PARTIAL without concealing either.

Reviewer RESULT.json must contain these exact fields (additional original review
fields are retained). Replace expressions with actual values, not literal tokens:

```text
schema: independent-source-code-review-v1
basis_hash: SHA256(canonical BASIS)
candidate: BASIS.current                     # head/tree/ALLparents
previous: BASIS.previous
modules: BASIS.modules
module_diff: BASIS.changed
plan_hash: BASIS.plan_hash                   # immutable OLD plan
reviewer: actual distinct reviewer session UUID
invocation: actual dispatched reviewer invocation identity
writer: actual source writer session UUID
writer_invocation: actual source writer invocation identity
workflow: code-review-workflow
readonly: true
disposition: approve-exact-code-delta
native_acceptance: false
coverage: {complete: true, modules: BASIS.modules, unreviewed: []}
risks: [whole original risks]
failures: [whole original failed qualifications]
remaining_obligations: [whole original retained duties]
```

PUBLICATION.json binds `reviewed_candidate=BASIS.current`, `basis_hash`,
`reviewer`, `invocation`. WRITER-RELEASE.json binds the same reviewer/invocation
with `source_writes_complete=true`, `report_writes_complete=true`,
`pending_owned_children=[]`. A release file does not substitute for parent END.

OUTSIDE_COLLECTION_JSON is an object with exactly:

```text
schema: outside-work-collected-source-review-v1
basis: entire unchanged BASIS
authority: actual Work attribution and selection rationale
collection:
  collector: actual authenticated Work session UUID
  independently_observed: true
  reviewer: same actual distinct reviewer UUID
  invocation: same actual reviewer invocation
  writer: same actual source writer UUID
  writer_invocation: same actual source writer invocation
  original_numeric_id: actual positive integer original collection handle
  actual_END: 0                               # integer, independently observed
  evidence: [actual original dispatch/collection evidence references]
public_manifest:
  PRIMARY.md: {path: absolute reviewer PRIMARY.md, sha256: exact file SHA256}
  RESULT.json: {path: absolute reviewer RESULT.json, sha256: exact file SHA256}
  LIMITS.md: {path: absolute reviewer LIMITS.md, sha256: exact file SHA256}
  PUBLICATION.json: {path: absolute reviewer PUBLICATION.json, sha256: exact file SHA256}
  WRITER-RELEASE.json: {path: absolute reviewer WRITER-RELEASE.json, sha256: exact file SHA256}
```

All five paths share one exact public report parent and refuse symlink ancestors.
The reviewer differs from Work and the source writer; the invocations differ.
Collection authenticates current basis before bodies and rechecks after reads.
Selection checks the immutable review hash, original public bytes and current
basis again inside the cooperative stopped lock and journal transaction. Changed
reports require a fresh basis/review, never replacing an existing review row.
Custody bytes remain inside original result/total budgets. No hostile-writer CAS
or multi-file filesystem atomicity is claimed.

SOURCE_SELECTION_JSON is exactly `{schema: "stopped-owner-source-amendment-v1",
basis: BASIS, authority: ACTUAL_WORK_DECISION, review_hash: REVIEW_RECEIPT.review_hash}`.
Preserve its returned exact source/plan/amendment/manifest/review hashes. Original
lease, history, source births, consumers, counters, grants and native expiries
remain unchanged. Future inputs/local integration/native report guard repairs
repeat this path using the previous appended source and a fresh independent
review, inside the finite closed module ceiling; SDK/config/dependency additions
and arbitrary modules refuse.

Qualification: set SOURCE_AMENDMENT822_FIXTURES to a fresh owned absolute temp
directory and run `python3 tools/coordinator-runtime/tests/run_source_amendment822.py`.
The suite includes real subprocess CLI config-load/Store-reopen/Board-auth/JSON-END
basis, external safe5 collection and selection. Its clock, actors, original END
and installed release/Git metadata are explicit synthetic seams; a separate real
Git fixture checks ancestry/ALLparents/blob closure. Kernel read-only source and
SDK5 closure, private TMPDIR before imports and network isolation apply. This
qualifies source behavior only; no live source install, native call or selection
has been performed. Diagnosis814/815 motivated future local/input repairs;
their proposed semantic fixes are not implemented by this source-selection patch.
Earlier818 path failures and failed tests remain historical failures, despite the
successful exact-path diagnosis reads in this task.
