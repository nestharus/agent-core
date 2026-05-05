# Risk Profile — Conventions

A risk profile is the artifact that decides how rigorously the implementation pipeline runs. It is produced in **Phase 2.5** of `~/ai/workflows/implementation-pipeline.md` and consumed by Phases 3, 4, and 5. It is not just a number — it is a **per-surface scored map** of where on the touched terrain the work is risky and where it is not, plus a single rolled-up verdict.

The principle is simple: when there is real risk, be exhaustive. When there is not, lean on tests and move fast. Per-surface scoring is what lets a single ticket be lean in some places and exhaustive in others without choosing the wrong global mode.

A project that adopts this convention also maintains a **project-level risk profile** (`<project>/planning/risk-profile.md`) that aggregates per-WU profiles into the project's high-risk surfaces, which then drive `~/ai/workflows/risk-reduction.md` work between tickets.

**Prototypes score risk at the end, not during.** Per `~/ai/workflows/build-prototype.md`, a prototype run produces its risk profile in Phase P3 (Present), against the surfaces the prototype actually touched (which may be different from what was anticipated). Prototypes do **not** run per-surface mode during the hack phase; lean/exhaustive mode is irrelevant when there are no mid-flight gates to apply it to. The prototype's `dossier/risk-profile.md` follows the same scoring rules as a Phase-2.5 risk profile and aggregates into the project profile the same way; the only difference is the timing.

## Scoring axes

Each touched surface (file, symbol, endpoint, job, workflow, contract) is scored on these axes. Score each `LOW` / `MEDIUM` / `HIGH`. Every `MEDIUM` or `HIGH` requires evidence — a path or symbol or query the next reader can verify.

| Axis | LOW | MEDIUM | HIGH |
|---|---|---|---|
| **Coverage gap** | The surface has **behavior tests** that exercise the surface's code paths and assert outputs against intended behavior. | Tests exist but are smoke-only or assertion-thin, OR the surface is a behavior-having component covered only by **structural shape-guards** (tests that read a config / YAML / schema and assert its shape rather than running the surface). Shape-guards catch deletion regressions but do not verify behavior; on a behavior-having surface they are not equivalent to behavior tests. | No tests, OR tests exist but encode the wrong behavior, OR the behavior is asserted only by integration tests that mask the unit-level contract. |
| **Behavioral ambiguity** | A reader can determine the intended behavior from code + tests alone. No "what should this do?" remains. | One or two well-circumscribed ambiguities. The reader can name what is unclear and the rest is clear. | Multiple ambiguities, or the central behavior of the surface is unclear without reading commit history / tracker / asking a person. |
| **Blast radius** | Surface is internal-only, single-caller, no external observability. Change cannot affect anything outside the surface itself. | Multiple internal callers, OR one external observability surface (a log line consumers parse, an HTTP response field consumers depend on). Change can affect known adjacent surfaces. | External public contract (API, config schema, file format, IPC). Change affects unknown number of consumers, possibly outside this repo. |
| **Language fragmentation** | Surface lives in one language and stays there. | Surface crosses one language boundary (e.g. Python emits JSON consumed by TypeScript) but the contract is explicit. | Surface crosses multiple language boundaries with implicit contracts (JSON shapes mirrored in three places, env var formats parsed by shell + Python + PowerShell, etc.). |
| **Duplicate-system count** | One implementation. | One primary plus a deprecated/legacy parallel that we know about and have a deletion plan for. | Two or more parallel implementations, possibly in different languages, with no deletion plan. Risk that the change makes the duplicates diverge further. |
| **Brittleness markers** | None of the markers below. | One or two markers. | Three or more markers, or any single marker named in `~/ai/conventions/no-deferred-stubs.md` or `no-backwards-compatibility.md` exemption notes. Markers: `# TODO` / `FIXME` / `HACK` density on the surface; recent revert commits; `Refs: <ticket>` trailers showing repeated re-work; tests with `xfail` / `skip` / `pytest.skip` decorators on this surface; commented-out code blocks; type-ignore comments; "this is wrong but it works" patterns. |
| **Change-path entropy** | The change touches one piece, one place, one time. | The change touches a small number of pieces, mostly in one place, with predictable propagation. | The change requires editing N parallel sites for the same logical change (entrypoints, schemas mirrored across languages, validation rules duplicated in front + back). Editing N sites is itself a brittleness signal — one of them will be missed. |
| **Lifecycle visibility** | The full lifecycle of the touched process is named: where it starts, every entrypoint, every state transition, where it ends, who reads each output. | One end of the lifecycle is clear, the other is murky (e.g. we know the entrypoints, not who reads the outputs). | The lifecycle map cannot be drawn from the code alone. Outputs go to consumers we cannot identify, or inputs come from sources we cannot enumerate. |

The set of axes is not a checklist to fill; it is the lens. New axes can be added as the project's failure modes accumulate. Removing axes requires a project-level decision recorded in `DECISIONS.md`.

## Per-surface verdict

Each touched surface gets a verdict computed from its axis scores, by the following rule:

- **HIGH** — any single axis is HIGH, OR three or more axes are MEDIUM.
- **MEDIUM** — one or two axes are MEDIUM and none is HIGH.
- **LOW** — all axes are LOW.

A `HIGH` surface forces the rest of the pipeline into **exhaustive mode** for that surface. A `LOW` surface allows **lean mode** for that surface — `MEDIUM` is the buffer zone where the orchestrator may proceed in lean mode but the proposer must explicitly call out the MEDIUM axes in the proposal's risk-section so a reviewer sees them.

## Pipeline mode

Mode is **per-surface, not per-ticket.** The same ticket can have one HIGH surface that drives Phase 3-5 exhaustively for that surface, and a LOW surface that runs lean for that surface, in the same WU.

| Phase | Lean mode | Exhaustive mode |
|---|---|---|
| Phase 3 (proposal) | Anti-scope, supported-surface track, assumption register, test-intent track, net-value statement — ALL phases produce these regardless of mode. **Mode-conditional**: the test-intent track in lean mode lists the smoke-level coverage; in exhaustive mode it lists every named behavior + a fixture-source per item. | As lean, plus per-axis MEDIUM/HIGH evidence the proposal addresses, plus a residual-risk section naming what the proposal does NOT reduce. |
| Phase 4 (risk gates) | Run all four risk gates, but the supported-surface gate may pass at LOW with a single-paragraph supported-surface track; the audit gate may pass at LOW without a per-AC residual entry. | Standard: all four gates require full evidence per the rules in `~/ai/workflows/implementation-pipeline.md` Phase 4. |
| Phase 5 (hookpoints) | Reuse points + conflicting systems + deletion candidates as headers. Empty subsections are explicitly marked "none observed." | Standard: full per-section enumeration, plus a cross-language trace for any surface scored HIGH on language-fragmentation or change-path-entropy. |
| Phase 6b (tests) | Smoke + AC coverage. Residuals named but not blocking. | Per-named-risk + per-AC + property-based / mutation / fuzz where the surface scored HIGH on coverage-gap or behavioral-ambiguity. Residual tests are blocking unless explicitly accepted in `risk/<wu>-test-residuals.md`. |

Lean mode is not "skip phases." Lean mode is "produce smaller artifacts that still cover the contract." The phase still runs, the artifact is still required, the gate is still evaluated. Lean is a budget, not an exemption.

## Discoveries during Phase 2.5

Phase 2.5 is the surface where pre-existing bugs and ambiguities get discovered. The convention is:

- **Bug** (incorrect behavior, contract violation, observable defect): file a JIRA ticket via `jira-operator` (`task=create`, type=`Bug` per the project's routing rules) with summary, reproduction, observed-vs-expected, and a `Blocks` link **from** the new ticket **to** the current WU's ticket. The current WU halts at Phase 2.5 until the user decides whether to proceed (acknowledge the bug, file as separate work, continue) or pause (block on the new ticket landing).
- **Ambiguity** (a behavior that cannot be determined without asking): file a ticket on the project's product-question board (PROD for the rfqautomation umbrella per `~/projects/rfq/AGENTS.md` § JIRA routing; equivalent on other projects) with the question, the surface where it surfaces, and the cost of leaving it unresolved. `Blocks` link from new ticket to current WU.
- **Drift** (two parallel implementations have diverged silently): file a tracker ticket. Whether it `Blocks` the current WU depends on whether the divergence affects the touched surface. The orchestrator presents the divergence to the user as a NEEDS_INPUT with options: `block on consolidation`, `proceed with current scope (note in DECISIONS.md)`, `expand current scope to consolidate`.
- **Test gap on touched surface** (behavior the WU will change has no captured behavior): the gap itself is not a bug; it's a precondition for safe work. The orchestrator dispatches a `gpt-high` test-writer to produce **characterization tests** on the current behavior before any change is proposed. Those tests land on the WU's branch (or a precursor branch). The current behavior they capture is the contract Phase 3 will work against. Bugs found during characterization-test writing follow the bug rule above.

The `Blocks` link is the load-bearing piece. A blocking ticket halts the current WU at the orchestrator level — the orchestrator emits a `NEEDS_INPUT` to the root and waits.

## Project-level profile

The project's risk profile lives at `<project>/planning/risk-profile.md` and aggregates per-WU profiles into the project's HIGH-risk surfaces. It is consumed by `~/ai/workflows/risk-reduction.md` to choose the next risk-reduction work between tickets.

The aggregation rule is straightforward: any surface that any WU has scored MEDIUM or HIGH gets an entry. Entries name the surface, the axes that scored MEDIUM/HIGH, the WU(s) that scored it, and a recommended risk-reduction action (write the missing tests, consolidate the duplicates, document the contract, etc.).

Entries are removed only when the underlying axes return to LOW with evidence. "Looks fine now" is not evidence.

## Anti-pattern

- **Single-number risk score**. A single integer flattens the per-surface insight that drives lean vs. exhaustive mode. Scores are per-surface, per-axis.
- **Risk score without evidence**. A `HIGH` on language-fragmentation that does not name the languages and the boundaries is just a feeling. Every non-LOW score names evidence.
- **Project-level profile as a wishlist**. The profile only contains what the WU evidence has surfaced. Speculative entries belong on a backlog board, not in the profile.
- **Lean mode as "skip the phase"**. Lean is a smaller artifact, not a missing one. If a phase is genuinely not needed, that is a `DECISIONS.md` skip with justification, not a lean-mode shortcut.
