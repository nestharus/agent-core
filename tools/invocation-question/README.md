# Invocation-owned protected question binding

This caller contribution uses immutable runtime
`7ec63c8bbb24e5844f246b98af0624383166f793`, tree
`adddb794c4f3a7fe8845e5b268a1f459b65edd67`. This runtime enforces the fixed
processing cutoff after synchronous feed preparation and authorization. The
caller refreshes current permission after complete identity work. Earlier
caller3592/runtime82de and caller16d/runtime44c remain historical evidence. No
installation or current global control is changed by this source contribution.
`runtime-pins.json` contains 81 finite public implementation pins, including the
seven actual direct-child modules (now including `fast_tier`). The coordinator
modules are an import allowlist; only modules actually needed are loaded. The
loaded closure is recorded separately from that allowlist. Host bootstrap and
imports require authority before the later model sandbox exists.

The only provider-capable entry is an explicit `Question.create()` followed by
`await question.run(first, continuation, materials)` in the genuine invoking
owner's process. There is no executable provider CLI, default identity, fake
coordinator, Store, Board, role grant, native proof or replacement service here.
Importing the driver has no provider/control/allocation effect. It does not launch
the actual question during source preparation. The builder must not create the
assigned `actual-question` directory or issue a scope for genuine Work.

## Actual APIs

The source-specific namespace uses the existing `review_composition.modules`
loader to import the seven admitted byte strings together. The binding uses:

- `dispatch.open_opaque_execution(routes, 'gpt-xhigh', profile, force_fast=force,
  config_reader=question.control_read)`;
- `appserver.Originals().scope()`;
- `execution_pool.ExecutionPool(config, pool=admitted_pool,
  pool_module=admitted_module, expected_control=pool_control).admission(profile)` and the supported
  underlying `Pool.allocate(..., expected_control=...)`;
- `SandboxProtection(root, executable, runtime_reads, capacity_check,
  probe_helper=...)`;
- `ExecEndpoint(root, executable, originals, admission, authority, protection,
  capacity_check, publish, execution=execution)`;
- `ContinuingReview(endpoint, 'gpt-xhigh', profile, collector, authority,
  lifetime=7200, clock=clock, origin=origin,
  material_authority=question.authorize_material)`;
- `public_program.identity` and `public_runtime.check_helper` for the actual
  complete program, common canonical helper and expressly trusted OS runtime.

The three-argument execution constructor does **not** snapshot the shared switch.
The driver reads `fast_tier.enabled(fast_control['path'])` at initial preparation,
binds the selected helper hash and passes the boolean through `force_fast`.
The genuine scope must select the actual shared
`/home/nes/ai/tools/direct-child/fast-tier`, not an adjacent checkout replica.
Later values are validated without retiering the original context. Requested
fast remains distinct from served tier (UNOBSERVED).

NEW allocation uses only the currently admitted 2/3/4/5 pool and its actual
public counter/lock destination. The existing asynchronous ExecutionPool guard
covers process creation and Originals registration. Continuing turns use the
original account without a NEW admission. The original creation time includes
preparation, qualification and all waits; it is never renewed.
The routes-declared public counter/lock parent may be under `.local`; only that
exact currently authorized persistence parent receives a narrow path exception.
It adds no private store access or model filesystem read root. Without that exact
current authority the parent is refused before target metadata acquisition.
Each lock acquisition attempt rechecks current parent rights and full allowance,
including busy-admission retries; static control is checked before effects and
under the lock. Later counter mutations within the entered synchronous guard
do not each invoke a separate parent callback.

## Current owner scope

`Question` receives `owner`, `authenticate`, `current`, `home`, `runtime`, `pins`,
`caller_pins`, `program`, `helper`, `runtime_reads`, `pool_control`, `fast_control`,
`exclusions`, `io_budget`, and optionally the monotonic `clock`.

The genuine Work invocation must supply its own real owner identity, genuine
Authority1258 and current lawful bindings. `authenticate_invoker(owner)` directly
compares the current `CODEX_THREAD_ID`; it never sets it or `CODEX_SESSION_ID`.
Missing/mismatched identity refuses. This is a finite trusted-host association,
not cryptographic identity or model attestation. The additional `authenticate()`
callback must perform the invoking owner's real current check; a successful
checker may conventionally return None. A no-op callback supplies no evidence.

`current(action)` returns the actual **current**, owner-controlled scope:

```text
owner: actual invoking identity
operations: explicitly allowed prepare/source/dependencies/allocate/control/
            qualify/analysis/material/collect/publish actions
revoked: current boolean
expires_at: finite wall-clock expiry; never a renewal of the original lifetime
write_roots: [exact positively new question home]
pool_write_parents: [actual public counter/lock parent]
read_files: exact admitted source/caller/program/helper/control/material files
runtime_directories: three expressly trusted canonical public OS directories
binding: exact independently admitted Question.describe_binding() value
control_effects: list(CONTROL_EFFECTS), for the actual owned nonsecret controls
questions: [exact first question, exact SAME-context continuation]
materials: [{label, path, bytes, sha256}, ...], the selected positive snapshot
custody_allowed: explicit continuing collection/publication permission
```

This is a runtime checking representation of genuine permission. Copying the
description above or copying `describe_binding()` into an unexamined scope does
not issue authority or establish currentness. Work must reconcile its genuine
permission and current source/program/helper/runtime/control/material/resource
facts before issuing these exact positive bindings, and maintain actual
revocation/expiry/rights during use. No all-source permission or old stopped
global grant is invented.

`scope_reader(exact_scope_file, owner, exclusions)` supplies a concrete finite
file-backed current callback. It opens the caller-owned regular file through
no-follow parents, requires private mode and a single link, and rereads up to
64KiB on every check. Work alone later creates/maintains that nonsecret current
scope file outside the not-yet-created question home. It is mutable current
authority data, not model material or a builder-issued grant. A callback may
instead consult an already supported actual current authority source.

The driver checks actual current positive paths before source acquisition;
rechecks the loaded runtime closure, published caller bytes, complete program,
helper, runtime trust, shared-control contract and material rights at supported
use boundaries; checks source bindings again after awaited creation admission;
and checks again on the feed task immediately before stdin.write, after process
creation and original registration. A refusal closes stdin without a prompt,
then retains the same original through wait, capture and publication. It binds
the actual endpoint, profile, collector and original lifetime. Complete
program identity uses the existing two-pass reader. Explicit finite I/O is
charged **before** each acquisition. Public routes are capped at 1MiB and
existing counters at 4096 bytes; later pool/config reads use the same cumulative
budget, including failed counter reads. Unbuffered control reads keep actual
acquisition within the charged byte ceiling. Scope-file checking remains the
external callback's separately bounded responsibility. A 32MiB evidence cap cannot admit the
320575976-byte program. Program bodies are streamed, not retained as copies.

Complete identity work is retained. After source/control/program/helper checks,
`authorize` reacquires current analysis permission; scope expiry and original
lifetime are sampled after scope/binding validation. `Context` checks its fixed
original cutoff again after that callback. The feed task encodes the prompt
before the callback and checks its fixed processing deadline after both, before
`stdin.write`, without an intervening await. Expiry or revocation observed there
closes stdin without delivering the prompt while retaining the original for
collection/publication. An event-loop timeout need not run first. These finite
point checks do not make external changes atomic with delivery and cannot
retract previously delivered input.

Collection/publication can continue after processing expiry/revocation only on
the actual current scope's explicit custody permission for those actions and
the retained original binding. This does not authorize another analysis turn.

The caller injects the exact Pool class compiled from the admitted direct-child
bytes. Importing the coordinator adapter performs no second filesystem load.
Ordinary runtime consumers retain the lazy filesystem fallback unless they
explicitly inject their own admitted pool; this change makes no universal import
closure claim.

Material-channel chunk authorization retains current rights, lifetime, source,
caller and public-control validation. Because immutable bytes move synchronously
inside the host, chunks do not each rehash the complete executable/helper.
Complete two-pass identities remain checked before the export, after export,
after local qualification/admission and immediately before provider stdin feed.
No identity cache or metadata-only substitute certifies later execution. The
optional material_authority argument defaults to the original full authority
callback for other consumers.

All driver operands must have a single '/' anchor before any metadata. This
narrows lexical spelling; it is no alias closure or generic filesystem theorem.

## Reproducible real-caller procedure (inert until Work supplies bindings)

1. Genuine Work reads the final source/header and this build's limits, incorporates
   any actual later Frame/Decide outcome, and selects the newly published runtime pin above. It admits
   the new helper commit separately as caller code, with its exact `driver.py`
   hash in `caller_pins`. It reads all actual current bounds and includes every
   identified held scope/derivative before any acquisition, not a stale count.
2. Work positively admits the exact question parent and public pool persistence
   parent, actual source/imports, public complete program, canonical helper and
   OS runtime, actual shared global switch, authority/current-scope file and
   finite positive source/method/history snapshot. It supplies current resource
   fit, original/capture/proof/failure/publication/consumer duties and explicit
   scope. No old capture, screen pointer, private profile or account query fills
   a missing operand. Missing necessary history remains a partial question.
3. Through Work's own authenticated tool invocation, load the published driver
   using admitted host source and isolated Python (`-I -S -B`). Naturally inherit
   the actual invoking association; never set or override an identity to make a
   new agent or foreign launcher appear as Work. Load the immutable manifest and supply
   the admitted constructor arguments. Keep the `Question` object and its
   in-memory original owner for the entire operation. Do not create a fake
   callback or claim a separate shell is the same genuine owner without the
   actual invoking association.
4. Work calls `question.create()` once. This is the positive exclusive creation
   of the exact `actual-question` home by the authenticated invoking owner. It
   performs current full-allowance admission first, admits imports and program
   identity, snapshots the actual global fast request and reserves a current
   pool profile. No provider runs in create. A failed create is preserved;
   there is no path adoption or automatic retry.
5. Work calls `await question.run(authority['questions']['first'],
   authority['questions']['same_context_continuation'], selected_materials)`.
   The exact strings/hashes must match the actual current scope. This performs
   the single real qualification and two SAME substantive transport turns,
   using existing canaries, local controls, runtime-attributed exact-command
   oracle, proof persistence and listener finalization. No source/method/history
   bytes are acquired for model export until successful qualification.
   `runtime_reads` must be exactly the canonical helper and the three named OS
   runtime directories, never repository/method roots during input0.
6. Assess the actual two source-located engineering answers, counterevidence,
   limitations and SAME lineage. `UNASSESSED` is deliberate: the driver cannot
   certify substantive analysis from two transport replies. Check numeric END,
   EOF, complete captures, command attribution, proof, listener finalization and
   local close independently. Read the whole owned publication/captures at their
   admitted scope. Raw captures remain separate from safe handback.
7. On failure keep this exact owner object, pending originals, physical failed
   receipts and adverse captures. No automatic model retry, replacement context,
   new lifetime, lost-handle recovery or original migration exists. An explicitly
   permitted publication-only retry invokes the SAME publisher, whose next
   exclusive name preserves earlier attempts. `await question.close()` collects
   only this original's known pending processes; it closes the idle local owner
   and may itself remain pending. Successful push/END/close is not whole
   processing, independent acceptance, rollout or retention release.

Suggested finite real-run preparation: <=512KiB selected source/method/history
snapshot (hard binding ceiling 2MiB/128 items); 128GiB total acquisition/identity-read I/O
(an explicit ceiling, not disk allocation); 512MiB/8192 whole owned output with
256MiB/4096 context envelope and 8MiB per process capture stream. Each identity
check charges two full maxima, including the helper. More demands return a
precise limit before the affected acquisition; no allowance silently grows.
Before each write/use phase the real owned parent must admit the whole question
allowance and leave 100GiB plus 1M available OS inodes. Retained own footprint
and a next-write margin are checked, separately from fresh filesystem headroom.
The public pool counter/lock destination needs its own lawful current placement
and full-allowance check. These are point observations, not reservations or a
private/provider/prior/concurrent census.

## Owned mock mechanism checks

From the admitted caller checkout, use an exact positively new fixture name:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B tools/invocation-question/test_driver.py \
  --runtime /home/nes/rfq-runtime-qualification-20261109/invocation-current-use-repair1277/repo \
  --fixtures /home/nes/rfq-runtime-qualification-20261109/invocation-current-use-repair1277/NEW-OWNED-MOCK-NAME
```

Do not copy that placeholder into an already occupied path. Tests use the actual
builder's invoking identity, an explicitly synthetic own question, tiny owned
program, owned pool/policy fixtures, mocked canonical-helper acceptance, mock
listeners and authored provider events. They never set identity variables or use
genuine Work scope. They run the actual runtime transport/parser/material/original
and pool code with mock provider processes. Real local stdlib processes and pipes check refused prompt delivery, including
blocked authorization, encoding cost and expiry of a one-second original.
Additional controls expire/revoke scope during complete owned-program identity
work, include scope-validation cost, and preserve useful delayed valid delivery.
They observe prompt byte counts and retained END/EOF/publication. No real provider, socket/listener or actual
qualification canary is run. Earlier generations and all failure fixtures stay
retained. Test success proves bounded mechanism discrimination under these
premises, not actual authority/protection/provider/semantic acceptance.

Finite checks do not establish all-world atomicity, future knowledge, a trusted
OS-tree hash, arbitrary crash recovery, escaped-descendant settlement or provider
storage reclamation. Keep whole processing completion +24h AND all source,
original, effect, consumer, outbox, recovery, privacy and resource holds. No END,
ACK, report, push, local close or writer cessation starts that clock.
