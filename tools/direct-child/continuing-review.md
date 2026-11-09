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
