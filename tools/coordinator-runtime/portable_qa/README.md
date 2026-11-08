# Portable QA procedure1047

This is an offline constructor and standard `unittest` adapter. It does not
export source, select runtime authority, create a new coordinator engine, or
perform acceptance, ref changes or cleanup. Existing local-QA full-tree export,
capture/resource limits, exclusions and authority guards are unchanged.

An authorized preparer imports `prepare.prepare(spec)` with this directory on
`sys.path`. All operands are concrete; there are no guessed defaults, Git calls,
producer-checkout fallback or provider invocations. Prepare creates a fresh
instance with frozen scripts, a manifest, explicit fixture inputs, and
`COMMANDS.json`. Both commands use the supported exact form
`["/usr/bin/python3.12", "-B", ABSOLUTE_SCRIPT]`, without runner arguments.
The command and separate readback must run at the actual admitted export CWD.
The readback's exact successful stdout is in COMMANDS.json. The execution stdout
is an informative status record; it is not the readback oracle.

The exact constructor fields are:

| Field | Required meaning |
| --- | --- |
| candidate | Actual admitted read-only candidate export CWD, without `.git` |
| candidate_identity | origin, ref, head, tree, ordered parents, method, history and changed_paths, supplied by the actual source owner; pins alone do not authenticate these assertions |
| candidate_files | Complete positive semantic test/input closure: repository-relative path to `{bytes, sha256}`; no candidate traversal is used to invent this list |
| instance / output | Distinct canonical fresh paths outside candidate; parents must exist; output is created once at execution, mode0700 |
| tools | python/bwrap, each `{path, pin: {bytes, sha256}}`; all identities checked before launch and readback |
| selected_selectors | Later Work-chosen genuine current test selectors, additive to REGRESSIONS in common.py |
| expected_ids | Every distinct full unittest ID after expanding the selectors; nonempty, no missing/extra/skipped tests; exact duplicate IDs from imported classes are executed once |
| effects | Nonempty declarative retained `file` UTF8 and/or read-only `sqlite` SELECT expected rows; paths are relative to output |
| historical_files | Every candidate production module filename to an exact public old704 `{commit, path, pin}` blob record or `{commit, absent: true}` genuine absence record; absence never supplies an old hash |
| caller | `{path, pin}` for the exact admitted inert public caller bytes needed by native fixture tests |
| limits | Positive finite timeout, output_bytes, effect_bytes and effect_files; these are procedure instance allowances, not changes to existing runtime ceilings or grants |
| scope_rationale | Actual selected behavioral claim and adequacy rationale |

The fixture SDK is explicitly composed outside the candidate from its four
current message-board modules plus its tracked fictional retention.py. It is
mounted at `/sdk`. The support.fixture_publication test seam selects those exact
five files. Candidate production and test files remain unchanged, read-only,
at their actual CWD; `/src` and `/actualsrc` are read-only aliases to the same
export. There is no shadow checkout. `/public` contains the inert caller,
fictional71 exclusions and source-derived original/candidate production hashes.
The public history also retains an `absent` map with the exact old commit and
explicit absence facts. The preparer must establish those facts against the
public Git tree; this offline constructor cannot authenticate Git provenance.
Current modules stay in `candidate` even when absent from `original`. Every
current module needs one history record, including explicit absence where true.
An omitted blob record is not implicitly treated as absence. Existing complete
blob-only histories remain valid and keep their original hashes.

Absence is not evidence satisfying an assertion that needs an old hash. In
particular, the inherited Future1008 setup and Integration1012 transition case
index every candidate module in `original`. A genuinely new module leaves those
assertions unsupported: the unchanged test raises an error, execution fails,
and readback refuses. Such a dependent run stays partial. No historical value
is filled in from current source and no assertion is skipped or softened.
The private host HOME, profiles, native stores and network are absent. Tests
write solely inside the fresh output bind `/fixtures`, plus ephemeral sandbox
`/tmp`; they may retain fictional symlinks, which accounting never follows.
System interpreter/stdlib and OS sandbox implementation are trusted dependencies.

Execution retains transcript.txt, events.jsonl, execution.json and all fictional
test effects. Overflow/timeout kills and waits the owned sandbox and returns
failure, with incomplete status and retained prefix explicitly marked. Output
is never truncated into a pass. Source/tool/script/input identity is rechecked.
The worker checks exact loaded test IDs, refuses writable/noGit violations,
records start/success/finish, checks actual imported candidate module origins,
and rejects skip/expected-failure/unexpected-success outcomes.

Separate readback rehashes current inputs/scripts/tools and complete output,
checks invocation identity and actual OS exit, exact starts/successes and complete
unittest transcript, verifies declared source origins, independently reads the
retained file/SQLite expectations without importing candidate code, and accounts
the entire proven-owned output. It does not accept producer `wasSuccessful`,
an echo or a matching Git ref as behavioral proof. Results remain cooperative
local evidence: hashes do not defend against a malicious privileged writer
rewriting both records and data, and test assertions/oracles require independent
adequacy review. This does not authenticate native principals or old physical
state. SQLite effects must be closed/checkpointed; immutable readback does not
claim to merge pending WAL state.

For genuine final1041, Work must supply the actual returned candidate and chosen
new tests plus complete dependency/history/method inputs, select substantive
behavior-specific effects, and independently qualify the instantiated procedure.
The inherited regressions are a floor, not a claim that this known baseline
covers unknown future changes. Missing inputs or newly needed consequential
dependencies return to Work. No current1041, live QA, wholeRepo coverage or
full-cutover result follows from a successful fixture.

The current local-QA path still needs whole-tree listing/body rights *before*
export, measured finite fit, actual package/tool/procedure/resource admission,
complete collection and fresh currentness. accepted-qa-branch-cleanup-v1 still
requires same-package local-qa/local-ref and separate independent acceptances.
Parent owns enclosing END and independent consequence Review/Frame/WorkDecide
before use. Retain processing completion +24h AND all holds; KEEP, no cleanup.
