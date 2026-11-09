# Protected continuing review

`ContinuingReview` is an explicit public continuing contract. Ordinary
`dispatch.py` invocations still create fresh seats. No saved-session attachment,
resume-after-owner-exit, automatic fallback, replay or identity attestation is
provided here.

A caller supplies the opaque `gpt-xhigh` consumer selection to the dispatcher's
`open_opaque_execution(public_config, selector, original_profile)` boundary. The
returned capability is passed to `ExecEndpoint`; ordinary configured provider
internals prepare execution without exporting the underlying binding. A binding
incompatible with this original profile refuses before a task. Callers neither
inspect private accounts nor reinterpret the selector. This does not establish
which model/provider actually served an answer.

The caller composes `Originals`, actual current `Pool.admission`, current-authority
checking, a capacity check, exact public executable/runtime read dependencies,
`SandboxProtection`, `ExecEndpoint` and `ContinuingReview`. The caller remains
responsible for admitting each supplied immutable byte string and for its source,
consumer, effect, recovery and retention duties. A source directory is not itself
permission to inventory it. No installed configuration or service is changed.


## Canonical helper and current ordinary use

A new `protected-continuing-v3` composition retains v2's finite complete
executable identity and adds `probe_helper`: canonical Python program
`path`, exact `bytes`, finite `max_bytes`, `sha256`, the three named
`runtime_directories`, and `startup: python-isolated-no-site-no-bytecode`.
The same `probe_command` builds local controls and the provider's expected
command with `-I -S -B -c`. Current source-read rights, complete helper identity
and root-owned nonwritable public runtime chains are checked before use. Isolated
startup ignores account/cwd Python injection and site hooks; trusted loader and
runtime directories remain OS premises, not hash-closed trees. Legacy v1/v2
contracts retain their earlier invocation and its qualification limits.

`public_runtime_reads` is a separate prospective configuration option for
finite complete programs and expressly trusted named runtime directories. Its
`public-program-runtime-read-v1` entries bind the existing small source-file
configuration/owner/stopped-original-grant proof, exact immutable source,
program sizes/hashes and `capability: future-only-new`. The genuine next
capability must select that resulting exact configuration and source before
new use. This representation creates no current grant or execution right.
Execute-only QA remains execute-only; its public tool/run/export contract is
separate. Evidence-file limits remain one MiB per file and four MiB total.

For ordinary AppServer analysis, the Peer rechecks current launch authority and
whole report eligibility/resources synchronously immediately before the local
`turn/start` input write, after RPC scheduling and all setup awaits. Continuation
uses the same boundary. Cooperating journal mutation cannot interleave that
check; external changes, wall-clock passage and remote execution retain a finite
race window. The check is no lease renewal or global atomicity guarantee. A
later result/delivery check can truthfully refuse after an authorized start,
retaining the same original, whole reports, failed captures and recovery duties.

## Before substantive input

`turn()` refuses until the single `qualify()` attempt succeeds. That attempt
opens the sole owned context and submits only generated nonsecret canaries.
Before each provider process, local public sandbox controls actually compare:

- permitted immutable canary reading;
- denied reading of an owned outside neighbor;
- denied material-file writing;
- denied connection to an owned live loopback listener.

An unprotected control performs all four operations, retaining the newly written
fixture. Every subprocess is registered before fallible capture setup, collected
using its actual wait handle, and retains numeric END separately from stdout and
stderr EOF. A failed control withholds the provider invocation.

The real qualification turn must then execute the exact canary program. The
caller requires a uniquely matching runtime-attributed completed command with
actual discriminating output, successful numeric END and complete captures.
Agent prose, printing expected JSON, omission of an operation, emitted setting
constants and the requested flags cannot qualify it. A parser mismatch is a
precise dependency and leaves substantive input withheld. It is not replayed.

These controls rely on the trusted installed CLI, sandbox implementation, OS,
public executable dependencies and caller/interpreter. Invocation-local user
config bypass, empty external-tool configuration, startup suppression and
restriction flags are requested; canaries qualify the observed acting boundary,
not universal resistance to a malicious runtime or all possible tool surfaces.
Normal provider authentication/storage internals remain outside the model tool
read policy. They are not copied, queried, inspected or treated as identity proof.
The sandbox's minimal runtime and the explicitly admitted public system read
roots are dependencies; the proof does not claim that only snapshot bytes exist.

## Continued work and custody

After qualification, compatible `turn(text, materials)` calls use the SAME live
Dialogue, endpoint handle, public thread, original profile, collector, creation
origin and expiry. Transport-export read events describe the endpoint copying
admitted bytes, not model reading or reasoning. Actual model operations stay in
the complete bounded per-process capture. The original lifetime includes
preparation, qualification, pool admission waits and all follow-on turns.

Only NEW context creation uses current cooperating pool admission. That guard
covers actual process creation and Originals registration and releases before
input, processing, capture, publication and numeric collection. Existing contexts
do not migrate or acquire a new lifetime when pool membership changes. The busy
Dialogue and Originals retain the whole turn's incurred obligations after the
creation fence releases. The outer caller still owns collection of its enclosing
native invocation; an inner process result does not replace that original END.

Failed, cancelled, oversized or incomplete work interrupts continuation. Handles,
captures, fixtures and partial answers remain conserved. `close()` collects known
pending originals and closes the idle local owner. It neither deletes provider
storage nor settles external effects, consumers, descendants outside the trusted
runtime, processing completion or the full delivery goal. Collection/publication
failure retains the exact in-memory capability; there is no PID/file/history
recovery or fresh replacement.

Current source/method/history and situated architecture-first all-nine-family
work must be substantively assessed from the returned account. Prompt presence,
read events, transport completion and a successful canary do not establish that
reasoning. Independent consequence observation and consumer acceptance remain
separate from this engineering contribution.

## Focused tests

Run `test_continuing_review.py` with an explicitly owned retained fixture root,
public sandbox-policy input and task root. Fixtures never auto-delete. Its
fictional transport/shape cases are separate from actual local sandbox controls;
none is a provider qualification. Use one source-bound focused final record at
readiness rather than restamping earlier results or running unrelated suites.

## Qualification failure and receipt progress

Qualification commits next-input admission after proof persistence and owned
listener finalization both succeed. A raised qualification call leaves
`protection_qualified` false even when its favorable command and proof bytes
survive. The single-attempt restriction still prevents replay. Local close can
collect the original handle; failure gives no new context or lifetime.

The acting oracle counts every runtime-attributed exact command completion
before interpreting its result. There must be exactly one, with successful END,
completed status and all four discriminating operation results. A contradictory,
failed or malformed exact execution beside a favorable one refuses admission.
Unrelated commands retain their own outcomes; they are not protection proof.

Each original evidence-persistence attempt reserves its receipt name first.
Post-create write, flush or fsync failure keeps the failed physical file and
exact in-memory original. A normal same-owner `Originals.finish` retry writes the
next name if persistence is available, carrying earlier receipt-attempt names
and failure observations. No prior file is reopened, overwritten or removed.
Capacity failure can still leave collection pending. Publication-only retries
reuse the completed evidence and do not create another evidence receipt.
Numeric process END, evidence-finalizer completion, pipe EOF, publication, local
close and whole processing retain their different meanings. This supplies no
hard-crash successor, escaped-descendant theorem or automatic recovery loop.

A local sandbox-control drain that ends with an admission, read or write failure
can finalize unsuccessfully on the same original once numeric END, settled drain
tasks, truthful evidence persistence and publication are available. Its receipt
records each failed stream and actual EOF independently; complete capture and
protection are not inferred from a completed finalizer. Required partial capture
files remain retained. A failed evidence write leaves the original pending and
uses a fresh exclusive receipt name on same-owner retry. Publication-only retry
reuses completed evidence. Unknown END or unavailable persistence/publication
still prevents discharge and local close. No capture replay, replacement context,
lifetime renewal or whole-processing closure follows.

## Coordinator composition and receiving boundary

The selected coordinator caller composes this continuing owner through
`opaque_review.call -> review_composition.call -> ContinuingReview -> ExecEndpoint
-> Context -> Originals -> Store.record_original_end`; see
[protected continuing Reviews](../coordinator-runtime/protected-continuing-reviews.md).
Its factory supplies the execution capability, actual SandboxProtection, scoped
original collector, capacity checks and original-specific publisher. Store admits
`owned-sandbox-control` as its own true numeric-original kind. Reviews keeps the
observed reviewer distinct from the responsible Root and builders and sends the
whole proposal to the sole integrator.

This is source construction. Actual service selection, current admitted operands,
live qualification and receiving acceptance remain separate. Generic proof is
`selected-opaque-cli-review`, with `native_owner_execution=false`.
`native_review_scope._authenticate` still requires `selected-ordinary-review` and
refuses generic CLI proof; a truly selected native receiver needs real native
proof. Neither a new Store kind nor a publication grants that proof.

### Historical composition account

The following earlier account described the coordinator before the selected
continuing factory and Store control-kind admission. It is retained as transition
history; its present-tense wording does not describe the current source above.
The original wording and its changes remain in Git history.

> The current coordinator source has a distinct `opaque-cli-v1` selection contract
> in `coordinator_runtime/opaque_review.py`. It pins the public Context launcher and
> constructs it without this endpoint's protection/execution dependencies. The
> Reviews executor separately associates an observed reviewer with its branch and
> keeps it different from the responsible Root and builders; it transports the
> whole proposal to the sole Reviews integrator. Sharing Context does not select
> this protected composition.
>
> The local-control publisher emits `owned-sandbox-control`. The existing Store
> numeric-original callback admits only `appserver-model`, `preflight-metadata`,
> `native-caller` and `opaque-cli-process`; choosing that callback directly is
> incompatible. Relabeling a control process does not supply compatibility.
> Likewise `native_review_scope._authenticate` requires
> `selected-ordinary-review` and explicitly refuses generic CLI proof. Changing
> that receiver or claiming native proof is not part of this contribution.

A caller must establish the applicable selection, current task/source authority,
admitted material, protection dependencies, publisher and receiving contract
before claiming adoption. The generic endpoint cannot satisfy a selected native
receiver's native-proof requirement. Source availability and focused local tests
do not select a caller, install it or establish operating/receiving applicability.
