---
workflow:
  id: mutable-review
workflow_dispatch_contract:
  orchestrator: "CRW new-run default via workflows/mutable-review.py; explicit adapters retain their own selection"
  inputs:
    - "delivered CRW default CLI (or explicit trusted adapter) and its current configuration contract"
    - "actual purpose, why, actors, environment, access, decision authority, owner/collector and private run destination"
  expectations:
    - "read back delivered provider and linked adapter sources and resolve actual runtime authority before start"
    - "preserve adapter-owned execution, inspection, recovery and disposition semantics"
  outputs:
    - "private adapter/provider run records, original evidence and execution disposition"
  non_goals:
    - "no saved-run migration, semantic policy copy, engine, live efficacy claim or merge authority"
---
# Script-backed new-run default

For new general protected-change runs, the [consumer](../AGENTS.md) selects CRW's
`perspective-lives-v1` with `after-act-domain-v1`. The default `start` entry routes
to CRW's **`start-default`**, which owns those configuration defaults and bounded
domain activation authority. No accounting algorithm lives here. This is not the
manual domain-pass loop. Explicit manual/standalone selections and active/historical
runs remain unchanged; `--adapter` preserves an explicitly selected CLI unchanged.

No resident root agent is needed: the controller asks for judgment on demand. An
actual accepting caller still owns answers, effects, verification and delivery.
Selection supplies no access, Decide, child, graph-edit, worker, secret/capture or
real-runner grant. Missing required inputs and explicit conflicting denials fail
visibly before initialization; they are not overwritten or silently routed to manual
review. Root must dispose runtime compatibility and consequence/design observation
before merge/activation. A candidate worktree is not deployment.

## Read back before selection

Discover the deployed provider at `~/ai/tools/mutable-workflow` and the CRW owner
at `/home/nes/projects/code-review-workflows/trunk`. Read the actual selected
provider's [README](../tools/mutable-workflow/README.md),
[agent contract](../tools/mutable-workflow/agent-adapter.md), and
[inspection contract](../tools/mutable-workflow/inspection.md), then CRW's
`README.md`, `AGENTS.md`, and
`risk-axis-reviewers/workflows/corrected-cohort/{README.md,submission.md,inspection.md,cli.py,provider.py}`.
Follow their role/method links; CRW alone owns semantics. Confirm the delivered
provider exposes `cli.py`, `agent_cli.py`, `inspection_cli.py` and the public
operations used by that adapter. Record actual source locations/readback and
conditions with the caller's existing notes **before starting**. Missing or changed
interfaces reopen integration conclusions; stop affected execution rather than
substituting a guessed CLI or old evidence. No fetch, deployment or automatic
compatibility attestation is performed by this launcher.

The default CRW entry selects **`perspective-lives-v1`** and **`after-act-domain-v1`**.
Its directory name does not make it the manual domain-pass corrected cohort.
Neither fake execution nor availability satisfies the general protected-change
review lifecycle; actual required returns still matter. CRW owns its selection and
retirement rules; this file does not reproduce them. A different adapter requires its own authority and readback.

## Invocation

Python 3.10+, POSIX, local private storage and the provider's dependencies (including
PyYAML) are required. Use the installed `~/ai` path after authorized deployment, or
explicitly select an isolated candidate path for fake verification. No daemon or
new scheduler is needed. Authorized paired deployment and readback
are required before activating the consumer default.

```sh
ENTRY="$HOME/ai/workflows/mutable-review.py"
python "$ENTRY" -- --help
python "$ENTRY" -- start /private/review --file /private/config.json
python "$ENTRY" -- drive /private/review
python "$ENTRY" -- summary /private/review
python "$ENTRY" -- inspect /private/review
```

`/private/...` are caller-resolved placeholders, not created directories. Construct
config from the **current CRW README**, not a second schema here. For the default
start, omit the three CRW-owned default fields (`selection`,
`reactivation_policy`, `allow_activation`), or supply their exact default values.
Explicitly supply actual provider path, trusted runner argv, applicable capture contract
with real secret declarations, project/access, purpose/why/question/material,
actors/environment, actual accepting owner/collector, obligations and bounded
Decide authority. The private run directory is the collecting artifact destination;
`owner` names the responsible recipient, not a delivery service. Confirm recipient
access. Choose child and graph-edit grants explicitly; the default grants only CRW-bounded
domain activation. An explicit activation denial conflicts with this default and
requires an explicitly selected alternate procedure, not an override. Optional
registered worker argv executes with inherited process privileges. This is not a sandbox.

`start` invokes no semantic role. `drive` may invoke the selected runner. Real
invocation requires separately granted authority and compatible
[runtime dispatch instructions](agents-cli.md#purpose-built-workflow-runtime-dispatch).
Do not use it to evade parent-visible delegation restrictions. The launcher maps
only default `start` to CRW `start-default`, then
execs the trusted adapter CLI with preserved output/exit/signal handling;
it does not itself dispatch an agent, supply prompts or import private storage.

The default adapter is the authoritative CRW trunk CLI above. `CRW_CHECKOUT` may
name an **absolute trusted** alternative checkout, e.g. the isolated candidate for
fake verification; it selects code, not additional authority. Missing adapters fail
without fallback. To retain explicit CLI behavior (including legacy explicit-only
activation), use `--adapter /absolute/trusted/cli.py -- start ...` and that adapter's
configuration contract. Default `drive`, inspection, answer and recovery commands
load the saved selection unchanged; never add defaults to saved configuration.

## Inspect, reconcile, continue

Use `inspect` for original state/evidence references and `summary` for compact
status. Use adapter `record --revision N` for original source revisions, and the
public provider evidence/owner/show/collect commands returned by those interfaces.
These contain private metadata and potentially sensitive evidence; do not publish
them blindly. Changed source rosters require the owner's explicit full rebaseline,
not dropping old suffixes. Publication lag does not imply lost original evidence.

For a returned question, the accepting caller can invoke `drive --answer 'actual
bounded answer'`. After an interruption, invoke a fresh `drive` against the same
run: the adapter owns exact historical collection and current-material continuation.
For an **actual material change**, `interrupt --file ...` records the caller's
reconciled decision context under CRW's contract; it is not a process-kill claim.
`act`, `amend`, `retry-unsubmitted` and all other operations retain their current
owner contracts and authority requirements. No automatic retry/repair is added.
An authorized edit changes execution intent, not original evidence or obligations.

Unknown provider keys and finite-owner loss before complete capture can remain
blocked. Preserve the original request, answer, diagnostics and named owner;
unknown is not `not_submitted`. Do not launch obsolete intent, invent a new key,
edit private tables or infer recovery from a successful trace. Controller loss,
owner loss and host/storage loss are different conditions. Historical unsupported
runs are not silently migrated.

The adapter's exit codes and payloads pass through unchanged: currently CRW uses
0 for initialization/inspection/progress/qualification, 4 for blocked/pending/
departed, and 5 for not-confirmed errors. Read the payload. Alternate graph success
can coexist with unfulfilled original policy. Qualified no-Act is not all-retired,
consumer acceptance, delivery completion or permission to merge. Root retains the
normal consequence review and final disposition.

## Evidence and limits

`tests/test_mutable_review_entry.py` invokes this actual selected file through
Python, starts through the public CLI (no imported initializer), and uses the
CRW-owned fake runner. It covers historical question/material interruption and
same-conversation continuation, actual Frame/Decide inputs with exact evidence text
and basis, authorized executable graph departure with an independent local effect,
and original retained records/final execution disposition. Negative controls cover
invalid explicit adapters and rejected submissions. `tests/test_mutable_review_default.py`
uses the actual **new default** path without `--adapter` or policy configuration:
initial9/27, bounded automatic activation, question/answer/same-session resume,
original return ownership, denial/error handling, required caller inputs and saved
explicit selection preservation. CRW_CHECKOUT redirects only the candidate code
location. Tests never run `agents` or a model.

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_mutable_review_entry.py tests/test_mutable_review_default.py
```

`CRW_CHECKOUT` can explicitly select a compatible CRW test checkout (default: the
owner path above); `MUTABLE_WORKFLOW_PROVIDER` selects the shared provider
(default: `/home/nes/ai/tools/mutable-workflow`). Absent fixtures fail visibly.
Fake command stdout/stderr and exit records stay in pytest temporary storage.
Candidate selection is not deployment.
Tests establish bounded mechanical behavior, not reviewer judgment quality/recall,
real-runner compatibility, arbitrary-effect exactly-once, unknown-key repair,
host/power/storage survival, hostile multi-principal protection, production scale
or SLA. All source/return history grows locally. Live evaluation is separately
selected. These tests supply neither runtime compatibility qualification nor
root's deployment/activation disposition.
