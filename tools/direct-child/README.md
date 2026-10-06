# Contextual direct dispatcher (temporary outage transport)

`dispatch.py` picks a route for **one** child from its run context, then runs a Codex or Claude session in the foreground, through the installed Linux native ACP v2 caller for exactly mapped bindings (Sol 6.1 high, and Opus 5.5 medium or high on the original `claude5` store) by default, otherwise directly through the CLI ([Transport](#transport)). It implements the [shared temporary dispatch rule](../../AGENTS.md#temporary-direct-codex-dispatch-during-agent-runner-outage) while `agents` / `agent-runner` is down. The same seat can take a different model depending on its class and on the kind of work. [`routes.toml`](routes.toml) is the single place to change providers, models, efforts, seat mappings, class mappings, and profile pools.

It does not decide seat authority or context boundaries, and it does not check that a class or kind claim is true. The caller asserts both and owns them. It does not select tasks, allocate worktrees, authorize effects, or replace the review and delivery lifecycle.

## Observe, Frame, Decide and Act

At this consumer dispatch point, root applies the existing [separation of contexts](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#separation-of-contexts) through the full loop. The recipients are root at briefing and the agents root dispatches. Read the linked seat contracts with the [Core entry point](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/AGENTS.md); the [route resolution below](#resolution) supplies this transport's model defaults, and the [launcher README](../direct-codex-child/README.md) supplies native launch and collection.

1. **Observe:** observers return evidence from realized work; they do not choose corrections or admit it. Root's own source observations also enter as evidence, rather than becoming class, scope or direction from root's own look.
2. **Frame:** an independent [Framer](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#framer) reads the person's words verbatim before any reading of them, then integrates the literal returns in hand. It interprets evidence; it does not inspect the work or select implementation.
3. **Decide:** an authorized [Decider](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#decider) sets the goal and direction, resolves consequential choices and authority, and carries target, why, necessary bounds and freedom in means into Act. Decide does not write the implementation specification. An unchanged valid Decision may be reaffirmed against the current Frame; a new decision item returns to authorized Decide.
4. **Act:** a separately dispatched [Maker](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#maker) chooses and makes the means within those decisions, then returns editable work, a construction witness and known gaps to root. Independent consequence observation returns through Frame and Decide; the producer does not validate or admit its own work.

**Every observer return goes through independent Frame and then authorized Decide before anything is corrected**, including clean checks of root's own briefs and findings described as small local defects. Root does not repair a checked brief directly from its observer's return. No Act launch comes between an observer return and its Frame. Where the current authorized Decision already permits dispatch after a Frame with no new decision item, root cites that Frame and the continuing Decision; the clean check itself supplies no correction authority.

This is a stricter local selection of [Core return routing](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#the-loop), which also permits a direct observation settling its requested use to go straight to Decide. It does not change Core. [Finding integration](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/core/DISCOVERY.md#integrating-a-finding) and [ownership](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/core/KERNEL.md#ownership) remain with their existing seats.

Act may use read-only Luna locators within its inherited authority and budget to find files, understand wiring and investigate implementation areas. They cannot independently validate or admit their parent's work. Negative or surprising findings, and findings that change target, scope, constraints or acceptance, return to root for independent Frame and authorized Decide before correction.

### Before briefing corrective Act

Every corrective Act brief cites the actual Frame return integrating the observations it acts on and the current authorized Decision. Each class, scope and direction item traces to that Frame or recorded Decide, never solely to root's own look. A located-correction class selects the model; it supplies neither readiness nor permission to skip Frame. Root supplies the [Runtime dispatch contract and observer packet](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#runtime), including verbatim words, declared use and recipient, material and method versions, map region, owned open questions or recorded Frame waivers, and the reading-check-first return with the Maker's construction witness.

The brief receives its independent cold check before dispatch. That check's literal return goes to Frame, then to authorized Decide for any decision item; a Decision already permitting continuation after a clean Frame remains the authority for that continuation. After making, anything a person or recipient will meet receives the Runtime first look in a cold context with only the person's words and goal, and the method change receives the independent alignment check at admission. Root collects the actual returns and preserves missing work and review debt.

Keep the actual observation → Frame → Decision → brief → cold check → Frame → Act trail, with any reopened Decision and subsequent consequence returns. Flags, native route records, producer verification and revised prose do not establish framing, admission or efficacy; the witness is the actual return under the existing [guarantee chain](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/core/KERNEL.md#the-guarantee-chain). This binds the full loop within the [shared selected method and delivery lifecycle](../../AGENTS.md#selected-reasoning-and-change-support); it adds no runtime enforcement or replacement review procedure.

### Briefing the receiving seat

The invocation that receives a seat brief is assigned to perform that seat itself. Write the brief to the receiver in the second person: "You are the Maker receiving this invocation; execute it yourself." Name ROOT as the campaign caller outside this session to make that authority boundary explicit. This convention aims at correct recognition; it does not guarantee it. A model, effort or seat label in the brief is launch provenance, not a request to create a session with that configuration. A bound such as "no children" binds the receiver and every layer that acts for it, not only a described seat.

This addresses an [actual failure](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/direct-seat-correction-root-decision.md) (machine-local evidence): a native Codex session given a third-person, model-labelled seat brief took the ROOT seat and spawned the described seat as a child. The transport requests restrictions on known built-in delegation (see [Execution and records](#execution-and-records)). A completed Codex observation still received collaboration schemas despite all five matched features reading back false; the cause is unexamined. A seat with a shell can also start `codex`, `claude` or this dispatcher itself. Only the brief reaches that layer, and nothing technically prevents it.

ROOT assesses single-seat provenance by joining the receiver's account to its completed attempt record and actual call evidence, preserving capture limits. The brief, requested flags, metadata and self-report alone do not attest sole execution.

### Current campaign selection

For the `context-routing-20260929` minimal prose/entry closure, the [actual Decision](/home/nes/projects/agent-runner/planning/context-routing-20260929/development-return-decider-return.md) selects **no per-prompt cold check**, accepting its cost tradeoff and remaining debts for fast closure. This campaign selection takes precedence over the per-brief cold-check requirement and trail above; it does not replace independent consequence Observe → Frame → Decide after making. The [actual Frame](/home/nes/projects/agent-runner/planning/context-routing-20260929/development-return-frame-return.md) diagnoses the earlier observer → Act bypass as root treating small local defects as exempt and carrying its own interpretation into dispatch. The Decision accepts that diagnosis without establishing cold-agent compliance. Full Core adoption, efficacy and `.claude5` / `.codex2`–`.codex5` import loading remain debt; the wider inherited observation obligations remain explicit gaps, not completed work. This bounded selection changes neither Core nor other campaigns' obligations.

## Resolution

The first rule that applies decides the route:

1. **Explicit override.** `--route NAME`, or `--model ALIAS|NATIVE_ID`, wins. A native ID also needs `--provider` and `--effort`. `--effort` may override the effort of any resolved route. Every override, including `--profile`, requires `--override-reason`, and the reason is recorded. Under `--kind creative`, an override that resolves to anything but `claude-opus-5-5` at `high` is refused (see [Kind](#kind)).
2. **Creative kind.** `--kind creative` on `maker`, `investigator` or `method-steward`, or with no seat, uses `create`, whatever the class.
3. **Seat with a fixed route.**
   - `framer` and `decider` use `direction`, whatever their class.
   - `scout` and `explorer` use `explore`.
   - `observer` uses `refine`.
4. **Seat with a per-class route.** `maker`, `method-steward`, and `investigator` use:
   - `direction` for `new-foundation`;
   - `refine` for `correction`;
   - `direction` for `unknown`. Missing evidence must not certify routine correction.
5. **Class alone.**
   - `new-foundation` uses `direction`.
   - `correction` uses `refine`.
   - `unknown` uses `default`.
6. **Plain legacy invocation** (no seat, no class) uses `default`, and records the class as `unknown`.

Rules for class:

- `--class` is `new-foundation`, `correction`, or `unknown`.
- `new-foundation` and `correction` require `--basis` with an evidence reference. The dispatcher refuses them without one.
- Class is never guessed from prompt text.
- `--pass generative|corrective` is recorded separately and never routes. A corrective pass that creates a new mechanism is `new-foundation`.
- Unknown seat or class names are refused.

Current bindings:

| Route | Provider | Model and effort | Profile |
|---|---|---|---|
| `default` | Codex | `gpt-6.1-sol`, `high` | round-robin over `.codex2`, `.codex3`, `.codex4`, `.codex5` |
| `refine` | Codex | `gpt-6.1-sol`, `high` | round-robin over `.codex2`, `.codex3`, `.codex4`, `.codex5` |
| `explore` | Codex | `gpt-6-luna`, `max` | round-robin over `.codex2`, `.codex3`, `.codex4`, `.codex5` |
| `direction` | Claude | `claude-opus-5-5`, `medium` | original `claude5` store: native names it through the site route (no wrapper); direct runs the `claude5` wrapper |
| `create` | Claude | `claude-opus-5-5`, `high` | original `claude5` store: native names it through the site route (no wrapper); direct runs the `claude5` wrapper |

**Moving `refine` to Sonnet** later is one edit: set its binding in `routes.toml` to `claude` / `claude-sonnet-5-5` / `high`.

**Model aliases.** `gpt` resolves to Sol 6.1 at `high`. `gpt-medium`, `gpt-high`, and `gpt-xhigh` keep their literal effort. The provider-neutral default is the `default` route, not the Codex `gpt` alias.

### Kind

The person's standing rule for Acts, including corrections: **if the result is non-text OR the work is artistic, declare `--kind creative` and use Opus 5.5 at high effort through `claude5`; work that is SCIENTIFIC AND TEXTUAL may stay on Sol.** Scientific charts and plots are creative under the non-text rule. A text file extension does not make artistic writing, UI rendering, CSS or SVG work technical; UI state and logic corrections and technical documentation are technical.

Their reason is that Sol does not create or act as well as Opus in creative domains. That is the person's preference and our basis, not a measured result, and routing establishes nothing about quality. The two kind boundaries are:

- **Creative:** anything artistic, or whose result is not text. UI/UX and visual design; the code that defines how a UI looks and renders (layout, styling, markup appearance, rendering code); SVG and other graphics; sound design; artistic writing. Code and text are creative when what they make is the look, the sound or the art.
- **Technical:** work that is both scientific and textual, where correctness is the judgement. Math, science, engineering, code correctness, technical writing, and UI state management, data and logic.

Not all writing is creative and not all UI work is technical: a UI state bug or a technical document correction is technical, and prose written as art is creative.

The caller owns the claim, as it owns class. The dispatcher never infers kind from prompt text or file extension.

- Pass `--kind creative` for **any** Act that includes creative work. No evidence basis is required. Omitting it for creative work violates the person's rule. The dispatcher does not catch the omission: an undeclared launch still resolves by seat and class and may launch Sol.
- **Mixed work** (a creative part and a technical part) is declared creative, and the whole Act goes to Opus 5.5 high in one context. Where the parts separate cleanly, the caller may instead launch a technical Act and a separate creative Act. Splitting is optional, never required.
- `--kind technical` is recorded and routes exactly as a launch with no kind.
- With no `--kind`, the route is exactly today's, and the record says `kind: "unstated"`, not technical.
- `--kind creative` routes the Act seats `maker`, `investigator` and `method-steward`, and launches with no seat, to `create`. On `framer`, `decider`, `observer`, `scout` and `explorer` it is **refused**: those seats look rather than make, and keep their routes.
- An override under `--kind creative` that resolves to any other provider, model or effort is **refused**, whatever the reason. Overrides that keep `claude` / `claude-opus-5-5` / `high` (for example `--profile claude5` or `--effort high`) stay allowed with their reason. To change where creative work goes, change `[kinds.creative]` or `routes.create` in `routes.toml`.

## Transport

Transport is chosen after the route and before anything starts. It never changes provider, model, effort, alias, kind, seat, class or profile.

- **Default `native`** (`[transport] default` in `routes.toml`). Exactly these resolved bindings map, recorded as `default-native`:

  | Resolved binding | Site route | Typical contexts | Credential |
  |---|---|---|---|
  | `codex` / `gpt-6.1-sol` / `high`, from a rotated pool profile or an explicit manual profile (`.codex`–`.codex5`) | `sol-high` | Observers, corrections, plain launches | access-only snapshot from that profile ([below](#native-credentials-and-renewal)) |
  | `claude` / `claude-opus-5-5` / `medium`, store `claude5` | `opus-medium` | Framer, Decider, new-foundation and unknown-class Acts | none (unless [children](#explicit-native-child-opt-in) are opted in) |
  | `claude` / `claude-opus-5-5` / `high`, store `claude5` | `opus-high` | creative Acts | none (unless children are opted in) |

  A native request names a **site route** only; the root-owned site config, not this declaration, fixes the actual provider, model, effort and, for Claude, the store (`config_dir` `.claude5`). `[[native.bindings]]` is the requester's declaration, not backend model/effort attestation. The shipped declarations are written to match the shipped example site configuration (`frontdoor.example.json` in the pinned package); the dispatcher neither reads nor validates the installed site, so it does not enforce their agreement. Whoever edits these bindings, or installs a different site, owns that agreement; a custom binding that was not checked against the site has no equivalence guarantee. For Claude the store is part of the binding: the shipped declarations map only the original `claude5` store. The dispatcher checks that each declared Claude binding profile is in `manual_profiles` and that the Claude pool has one entry; it does not check that the pool entry equals the binding profile. Transport matches the explicit parent profile or the single pool entry against the declared binding, so another store (configured or `--profile`) is a different binding, never silently replaced by the site's. Pool profiles are separate accounts; rotation treats them as interchangeable for allocation only.
- **Unmapped bindings run direct by rule**, recorded as `default-native-unmapped-direct`: Luna, literal `gpt-xhigh`, other Sol efforts, other Claude models or efforts, and any other Claude store. Codex direct runs through [`launch.sh`](../direct-codex-child/README.md), and Claude through `claude5`. This is a pre-launch selection, never a fallback after a native attempt.
- **Context chooses the model; transport follows.** Seat, class and kind resolve provider, model and effort first ([Resolution](#resolution)); transport never changes them. The creative rule refuses moves off Opus 5.5 high on either transport.
- **`--transport direct`** explicitly selects the CLI, recorded with `transport_source: "explicit"` and `transport_rule: "explicit-direct"`. It preserves the resolved provider, model, effort and profile. This transport choice needs no `--override-reason`; route/model/effort/profile overrides still require one. It is the escape when native is unsuitable for a launch.
- **`--transport native`** explicitly selects the native caller (`[native] caller`, the versioned P6 `a02520122600-213cac2323d7` package path), recorded as `explicit-native`. Any binding without a declared native site route is refused before effects (exit 2).
- **No automatic fallback or replay.** Native preparation refusals and caller failures return their status. A later direct launch requires a new explicit caller choice.
- `--native-deadline SECONDS` overrides `[native] deadline_s` (7200, the front door's deadline and kill bound) for a launch that runs native. It must be an integer from 1 to `[native] max_deadline_s` (declared 7200, the pinned caller's own ceiling). An invalid value is refused on every transport, and the flag is refused when the launch resolves direct, by rule or by explicit choice: direct launches have no deadline, and the dispatcher selects no direct timeout. These refusals (exit 2) come before profile allocation, lease, credential preparation, any attempt write and the caller's launch, so a too-large deadline can no longer allocate, renew or snapshot first. A non-integer or overlong number is refused by argument parsing. The site's own `max_deadline_s` may be lower than the declaration; the front door then refuses (caller 4). The dispatcher does not read the site.

The caller path is the exact versioned **P6** pin: Runner `a02520122600`, agent-bash `213cac2323d7`, at `/opt/oulipoly-native/oulipoly-native-linux-x86_64-a02520122600-213cac2323d7/bin/oulipoly-native-call`. The [U71 ROOT Decision](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u71-native-async-route-cutover/root-decision.md), after the [U70 Frame](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u70-native-async-public-claude/frame-return.md), selects this installed pair for all mapped bindings. ROOT's source delivery must advance the live `/home/nes/ai` checkout; a feature worktree or remote merge alone does not activate local routing. This source correction does not perform the operational cutover or P5 retirement.

**P6 qualification is bounded.** The [U70 public readback](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u70-native-async-public-claude/root-public-readback.json) records one public Opus-medium Claude async flow: caller 0 / `answered`, front door 87, true work `code:7`, and harness SIGKILL 9 followed by drain. Its 3000-byte retained-file-rehash receipt and completion ACK/tagged turn end do not establish semantic consumption, general correctness, OpenCode/Sol, ordinary-path or migration qualification; those later needed observations remain owed.

**Historical P5 pin:** the caller path was the exact versioned **P5** pin: Runner `0a24a50e6f080efcdf198c29ba01f2e0ce84caab`, agent-bash `ff76fa62e750412503ee63fab75bd291d4f02d6a`, at `/opt/oulipoly-native/oulipoly-native-linux-x86_64-0a24a50e6f08-ff76fa62e750/bin/oulipoly-native-call`. U44 records this pair as installed with source/default-release-build and installed-byte evidence. Installing another package ID while retaining this package leaves the pin selecting its existing absolute path; there is no stable caller resolution or shim. Retiring/removing the pinned package or otherwise losing that path is the launch hazard. If execution reaches the caller launch with the pinned executable absent, it fails to launch (8), without fallback; Sol can instead refuse earlier during profile, lease or credential preparation (including 70/75). The historical U19 `8c48c7eecb69` caller did not offer children.

**Historical U46 activation.** The [U46 ROOT Decision](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u46-native-caller-pin-root-decision.md), after the [U45 Observer](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u45-opencode-runtime-observer-return.md) and independent [U45 Frame](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u45-opencode-runtime-frame-return.md), selects **whole P5 pin activation for all mapped Sol and original-`claude5` Opus medium/high bindings** in ROOT's delivery window. Context still selects the model first. Activation requires advancing the live `/home/nes/ai` checkout to this `routes.toml`: subsequent local default launches read that checkout's config. A remote PR merge alone does not advance local routing, and an editable worktree is not activation. First ordinary needed P5 Sol/Opus launches supply finite consequences; no extra dedicated witness window or automatic fallback/replay is selected.

**Historical P5 evidence is bounded.** U45 independently observed and Framed one synchronous, single-input, no-child OpenCode 1.18.30 default-config ASCII large→small instance: the entire exact **49,152-byte prefix** is present in a **49,842-byte persisted body**, with separate true command wait **`code:7`**; the full-stream count is **1,048,576 bytes**, comprising 49,152 inline + 16,384 adapter-omitted + 983,040 producer-discarded bytes. The whole hidden 65,536-byte producer prefix and 1 MiB stream were not recovered as byte witnesses. The small follow-up is exact **66 bytes** in a 404-byte body, wait **`code:0`**, later in the same session/input. Both persisted bodies have `truncated:false`, no `outputPath` and no generic cut/spill. These are persisted consumer bodies, not this dispatcher's ordinary exports of Bash argv/events, and not proof of later model-context contents.

U44/U45 join the P5 images, adapter and source; the byte-identical `375e6704…` Claude receiver is statically located in P5 Runner and joined to `provision_claude`. **That is not P5 Claude runtime evidence.** U38's finite P4 Opus-medium witness and U40's P4 OpenCode witness retain their original scope; all four P5 images differ from P4. U40's generic second cut left no payload in an 856-byte persisted body and made the earlier `65536 bytes shown` claim false. That historical counterevidence is not the current P5 default-path result. P5 Claude, Opus-high and child runtime remain unqualified; requester mapping and fake controls do not qualify them. ROOT accepts that bounded activation cost rather than keeping split pins.

**Accepted residuals and debt remain.** Smaller custom `tool_output` caps can re-cut output and leave stale pre-cut shown claims; oversized diagnostics can exhaust header headroom; later context transformations are outside this boundary; omitted suffixes have no recovery spill. Hidden producer bytes remain unobserved, and the nonempty-only general usefulness floor and format-oracle upkeep remain accepted. Binary/hex, UTF-8 and line boundaries, custom caps and oversized cases were not exercised by U45. Native ACK/dedup/recovery/cancel remain unqualified. U43's warm/concurrent CI registration negative (`readlink /proc/18/fd/9`, ENOENT) remains open, with availability versus authority/protection purpose and descriptor-history evidence unresolved; U45's synchronous result neither fixes nor answers it. Broad CRW/all-nine/cohort, Core/admission, security, full CI, Linux async, E2, prework, stress and benchmark work remain missing, not passes or waived work. U46 retains independent consequence Observe → Frame → Decide and the campaign's no-per-prompt-cold-check choice for this precise pin continuation. Current SITE/custom-cap/selector/retirement dependencies require ROOT's later bounded readback and disposition; this pin declaration does not attest them.

### Explicit native child opt-in

A mapped native parent (Sol high, or Opus 5.5 medium or high on the original `claude5` store) can be given registered orientation explorers inside its own root, for example cheap Luna-max orientation for an Act that then reads the important areas itself. Nothing is opted in by default, by seat or by kind: the caller asks explicitly for each launch.

- `--native-child-route NAME` (repeatable) names a site child route. The shipped declaration is `luna-max`, offered on all three mapped bindings (`[native.children]` and each binding's `children`). `--native-child-max-starts N` and `--native-child-max-concurrent N` may only lower the declared limits (4 starts, 2 concurrent). They need `--native-child-route`.
- These options are native-only. An unoffered route, a duplicate, an out-of-range limit, or any child option on a launch that resolves direct (by rule, for example Luna's own standalone `explore` route, or by explicit choice) is refused (exit 2) before allocation, lease, credential preparation, writes or the caller's launch. It is never silently dropped, and a direct launch is never presented as having children.
- The caller receives `--child-route` and any lowered limits. The site, not this declaration, decides what it offers and admits (its `child_routes`, per-route `children` and `child_limits`, depth 1, the root's lifetime). The no-child `8c48` site was the historical U19 state, superseded by U24's paired package/site window. ROOT's U41 context (2026-10-05) reports that the shared site (`08d90…`) has explicit Luna-max offers with 4 starts / 2 concurrent, preserved through U37 and U40's original-byte restore. This is dated ROOT-supplied context, not fresh site attestation; the dispatcher does not read the site, and ROOT owns the fresh activation-window site/rule checks.
- **Sol parent:** its children reuse the parent's one access-only snapshot. There is no second profile, rotation step, lease, renewal or snapshot.
- **Claude parent, opted in:** Claude Code still uses its own login in `~/.claude5`, which is never read, leased or passed. The dispatcher takes **one** separate Codex profile from the same rotation counter and prepares one access-only child grant under that profile's lease, with the same freshness need and conditional official renewal as a Sol parent (the grant must cover the whole declared deadline plus site terms). It passes the grant as `--child-credential-codex-profile` and removes it after the caller ends, on success, refusal or failure, within the limits [below](#execution-and-records). Local expiry is not provider validity.
- **Claude parent, not opted in:** unchanged: no profile, lease or Codex credential.

Child records stay qualified: the caller's `children.json` holds owner exports, which can lag the parent's local result while Bash drains; zero exports does not mean zero local results; Bash counts combine parent and child; and caller `0`/`answered` says nothing of answer correctness, the model, the account or the issuer, or that the parent consumed a child's answer. Child answers, ends, drains and unknowns are reported by the owner, not verified here. No child capability is exercised by this dispatcher's fake controls beyond argv and grant preparation.

Transport is **mixed**: native covers the three bindings above, and explicitly opted-in registered children inside them. Standalone Luna and other bindings run direct by rule. On P5, Claude, Opus-high and child runtime remain unqualified; requester-side mapping checks are not runtime evidence. Neither the historical U38 P4 Opus-medium witness nor U45's no-child P5 OpenCode body witness establishes those capabilities.

The following is the **historical U19/U24 campaign witness account**. Its “yet”, “first ordinary” and “after merge” refer to that activation, not current P5 readiness; its proof and limits retain their original scope:

Children have no installed or model witness yet: the first ordinary opted-in Luna-max use after ROOT's installation is that witness. Native Claude has one useful Opus-medium Frame witness, called straight through the installed caller (caller 0, `answered`, front door 87, normal close collected 0.578 s after close was queued); it did not exercise this dispatcher's mapping, and Opus high has no native witness. The first ordinary mapped launches after merge are those witnesses. Known Claude receiver limits stay open: the receiver can exit before its descendants drain, so close can take until the deadline; a long silent thinking phase may hit the 120 s ACK bound and end without an answer; `answered` does not establish the model, a denial or the task. ROOT's [activation decision](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u19-native-default-root-decision.md) follows one [installed conditional-renewal witness](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u18-installed-renewal-root-observation.md) on `.codex2`: local expiry metadata advanced to 863999 s remaining, covering the default 7862 s need, and the helper's EOF exit 0 and empty original group were collected. That one sample supports keeping 7200 s on the expiry axis; it does not establish token validity, writer attribution, issuer rotation count, other profiles, task fit or future site/CLI compatibility. Source, fake controls and actual native task evidence are distinct.

### Native credentials and renewal

**Native Claude does none of this for itself.** Its site route sets `"credential": "none"` and fixes the store; Claude Code inside the run uses its own login in `~/.claude5`, which pays and refreshes there, and its transcripts land there. The dispatcher reads no store and passes no credential for the parent. Its state records `credential=none` and `profile_lease=none`. Without children it also takes no profile lease and renews nothing. With [children opted in](#explicit-native-child-opt-in), the steps below run once on one rotated Codex profile for the separate child grant (state `child_grant_profile`, `lease_scope=child grant profile`), and the grant goes to `native-child-credential/` instead of `native-credential/`. Concurrent direct and native use of `.claude5` is unexamined.

For **native Codex**, the path sends an access token only, and the front door refuses a token that will not outlast the run. So under the [profile lease](#profiles), before the call:

1. Read the profile's `auth.json` (the caller's own regular file, no symlink) for the access token's JWT `exp`. A profile with no file-store ChatGPT access token is refused (exit 70).
2. The token must cover `need = deadline + 2 × site_grace_s + site_collection_s + site_margin_s + slack_s` (7862 s by default). The site terms are declarations, not root-config readback; the front door's own check decides. Actual lifetime, site binding and admission delay remain conditional. A shorter lifetime can renew and refuse on every new attempt.
3. Only below `need`, ask the installed Codex CLI through one client RPC sequence: `codex app-server --listen stdio://`, newline-delimited JSON-RPC `initialize` (requesting `explicitGatewayOauth` to suppress gateway browser sign-in), `initialized`, then `account/read {"refreshToken": true}`. The handshake follows the public `openai/codex` source at `rust-v0.159.2`. Older servers may ignore the capability; ROOT witnessed this sequence on codex-cli 0.159.2 for one `.codex2` renewal, not future compatibility. Startup itself can contact the issuer, discover backends and perform other profile/config/plugin work; it is outside the direct task's MCP-disable preflight claim. One client sequence does not prove one issuer rotation.
4. `account/read` answers even when the refresh failed, and it does not say why. `renewed` and `renewed-insufficient` mean expiry metadata changed and respectively covers or falls short of `need`; they establish neither issuer validity, advancement nor writer attribution. `profile_written=yes` is metadata observation only. `not-renewed` means unchanged expiry (expired, reused, revoked or transient, indistinguishable here). RPC errors, malformed output, timeouts, interruptions and launch failure give `helper-*`, with possible writes retained as unknown. Once app-server launches, `issuer_contact=possible`, including initialize failures and timeouts; no launch means `none`.
5. Close the server's pipes and wait for its leader, then bounded TERM/KILL of its original process group, including after leader exit. An unobserved leader exit or remaining/unknown group gives `helper-stop-unconfirmed` and refuses (70), even with an answered RPC and sufficient changed expiry. No fresh token also refuses. Nothing is repeated, forced again, sent direct or replayed, and no OAuth request of our own is made. Empty original group and collected leader are bounded local observations, not whole-session/kernel proof: escaped process groups, PID/group reuse, zombies, SIGKILL and kernel-uninterruptibility remain limits. Cleanup discovers no global processes and touches no external daemon.
6. If the token is fresh, write an access-only snapshot (`tokens.access_token`, plus `account_id` when present; no refresh grant or id token) to `native-credential/auth.json` (0600 in 0700). Release the lease, run the caller with `--credential-codex-profile` pointing there and a `--credential-margin` keeping half the slack, and remove the snapshot after the caller exits.

Nothing prints or records token text, account fields, JSON-RPC error messages or server stderr. The server's stderr is discarded unread. `renewal.json` holds classes, remaining seconds, error codes and stop status only.

`codex login status` loads credentials and never refreshes ChatGPT tokens in that source. Runner's `auth_refresh_command = codex login status` assumption is stale and should not be relied on. Direct Codex use refreshes only within five minutes of expiry, so it cannot keep a profile fresh enough for native.

`codex_auth.py status|renew --profile P [--need-s N]` exposes the same lease, freshness read and gated renewal for ROOT's separately funded witness. Its output holds no token text. This standalone interface relies on finite positive wait/timeout/need arguments from its caller; it lacks the dispatcher's finite range validation. Server callbacks are skipped without replies, initialize result shape and id types are not fully validated, and the nominal line cap has a newline-boundary edge; total capture and read waits remain bounded. Fixed small pipe writes are blocking. These are development protocol limitations, not compatibility certification.

## Profiles

- Sol, Luna and opted-in Claude parents' child grants share one Codex counter. Each real launch takes the next profile under an exclusive `flock`, so allocation is atomic and cycles evenly. The counter lives at `~/.local/state/direct-child/codex.counter`.
- Configured Codex profiles must be `.codex`, `.codex2`, `.codex3`, `.codex4`, or `.codex5`; unsupported names are refused before dry-run or allocation.
- Allocation happens before the MCP preflight, so a refused preflight still uses its turn.
- Rotation spreads starts across accounts. It knows nothing about rate limits or token health, and runs no health probe; a profile whose refresh token is still live can recover through the official renewal above.
- **Profile lease.** Every cooperating Codex profile writer this tool launches takes an advisory exclusive `flock` on `<profile>/.oulipoly-direct-child.lease`. Direct launches hold it from MCP preflight through task exit and capture until launcher exit, because Codex can refresh mid-task. Native launches hold it for the freshness check, any renewal and the snapshot only; their access-only task path does not write the source profile, though a trusted task's shell is not constrained from doing so. A launch waits at most `[lease] wait_s` (120 s), then exits **75** without starting a task. There is no queue.
- Direct tasks serialize per profile through task exit and capture. Four busy direct profile writers can make later launches wait for their rotated profile or refuse; allocation does not search for a free profile. A free-profile search could not preserve more than four simultaneous profile writers when all four are busy. Native access-only tasks can overlap after preparation releases the lease. There is no new scheduler or fan-out guarantee.
- The lease descriptor is close-on-exec in Python and closed for each Codex call in `launch.sh`. Codex, the app-server, the native caller and their descendants never inherit it, so an orphaned descendant cannot keep a profile locked. Writes by such a descendant after the task exits are not covered either.
- The lease does **not** cover writers we do not launch: interactive Codex, editors, desktop apps, other machines or copies of a profile. A refresh there can still rotate the grant and race ours. Keeping a profile single-writer is an ownership choice for the person and ROOT, not a guarantee of this tool.
- It also does not cover external per-profile daemons. Their presence was historically reported, not freshly attested; the previously cited `HANDOFF_ENV` source does not establish direct-exec daemon handoff. Lease identity assumes trusted user-owned profile directories and an unchanged regular lease inode. Existing modes/type/owner are not revalidated; Bash check/open replacement, FIFO blocking, symlinked ancestry and replaced inodes remain conditional limits. Waits are application bounds, not kernel/filesystem guarantees.
- To pick a profile yourself, pass `--profile` with `--override-reason`. Selecting an explicit parent profile does not advance the parent's allocation counter. An opted-in native Claude parent still takes one separate rotated Codex child grant and advances the shared Codex counter, even with `--profile claude5`. `.codex` is manual-only; the automatic pool is `.codex2`, `.codex3`, `.codex4`, `.codex5`.
- Direct Claude runs only through the `claude5` wrapper, which sets `CLAUDE_CONFIG_DIR=~/.claude5`. Native Claude names the same store through its site route and does not use the wrapper. Rotation and the lease above apply to Codex profiles only.

## Example

```bash
/home/nes/ai/tools/direct-child/dispatch.py \
  --seat maker --class new-foundation --basis /abs/facts.md#launcher-gap --pass generative \
  --cwd /absolute/worktree --prompt /absolute/prompt.md \
  --runs-dir /absolute/runs --id maker-routing
```

Other forms:

- `--seat scout` for a Luna explorer.
- `--seat maker --class correction --basis /abs/frame-return.md#F3` for a Sol refinement under the cited Frame and current Decision in its brief.
- `--seat maker --class correction --basis /abs/frame-return.md#F4 --kind creative` for a correction to a UI's look, which goes to Opus 5.5 high.
- `--model gpt-xhigh --override-reason 'CRW contract names gpt-xhigh'` for a literal alias.
- `--seat maker --native-child-route luna-max` for an Act whose mapped native parent may use Luna-max orientation children ([opt-in](#explicit-native-child-opt-in)); add `--native-child-max-starts 2` to lower the allowance.

- Sol high and Opus 5.5 medium/high (`claude5`) launches use the installed native caller by default; `--transport direct` records an explicit CLI choice, and `--transport native` records an explicit native choice ([Transport](#transport)).

Add `--dry-run` to print:

- the resolution record, including transport;
- the exact quoted native command (for native, the caller command with `<attempt>` placeholders; for Codex also the freshness the token must cover, for Claude a note that no credential is used);
- the next pool profile, marked "not reserved".

A dry run writes no files, advances no counter, takes no lease, reads no credential, launches nothing, and does not check whether the Claude wrapper is installed.

## Execution and records

**Direct Codex routes** hand off with `exec` to [`direct-codex-child/launch.sh`](../direct-codex-child/README.md), passing `--model`, `--effort`, `--lease-wait` and the resolution record. That launcher keeps its behavior, now under the profile lease:

- effective MCP discovery, per-server disable flags, and the injected docs-server disable;
- the preflight refusal;
- the attempt files `prompt.md`, `log.txt`, `final.md`, and `state.txt`;
- `DIRECT_CODEX_*` markers, with Codex's own exit as the process exit;
- requested restrictions and feature readback, separate from `delegation_capability=not-established` (see the [launcher README](../direct-codex-child/README.md#built-in-delegation)).

**Direct Claude routes** first run `claude5 --disallowedTools Agent,Task,Workflow --help` with no prompt in an attempt-private HOME/XDG/CODEX_HOME/CLAUDE_CONFIG_DIR. This metadata call has a ten-second timeout. Rejection, unavailable help or an undocumented flag omits the denial arguments before the sole task invocation; selection, command, exit and available help output are retained. It checks no version and never replays a possibly started task.

When help accepts those arguments and documents the flag, the sole task command is:

```bash
claude5 -p --model M --effort E --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --settings '{"autoMemoryEnabled":false}' --no-session-persistence \
  --disallowedTools Agent,Task,Workflow --output-format stream-json --verbose
```

`--disallowedTools` requests denial of Agent, Task and Workflow; those names come from observed session tool lists. The current changed Frame command was accepted, and its init omitted all three names. That evidence does not prove support in future task parsers: help may accept arguments without validating tool names as a task would. A subsequent native task rejection is propagated without replay. Other existing flags retain their compatibility limits. Other coordination tools such as SendMessage, RemoteTrigger and CronCreate are outside this restriction.

The attempt directory holds:

- `prompt.md`, read-only;
- `log.txt`, every stream event, written live;
- `stderr.txt`;
- `final.md`, available result text (invalid or ambiguous results remain diagnostic text);
- `route.json`;
- `restriction-metadata/`, the private help context and available stdout/stderr;
- `state.txt`, which records the actual native command, `requested_disallowed_tools` (empty if omitted), restriction selection and help evidence, raw `claude_exit`, result count and semantics, delegation provenance, final/custody status, capture errors, and `dispatcher_exit`. The awaited native status is appended before final capture. Available raw stdout continues to the terminal even when log storage fails.

Claude exit codes:

- A nonzero native exit is propagated; a signal wait status `-SIG` becomes terminal status `128+SIG`, with the raw status retained.
- Success requires native exit 0, exactly one result event, boolean `is_error=false`, subtype `success`, and nonempty text with usable final capture. Missing, malformed, or multiple results remain unknown/failure; available text is preserved without a valid-final marker.
- Native exit 0 returns **3** for an unambiguous boolean error, **4** for missing/invalid results or failed final capture, and **1** for other incomplete custody.
- Final write/read/output or encoding errors report `final_capture_error` and `final_status=capture-error`. State errors report `state_capture_error` to the terminal. Failed storage cannot guarantee durable metadata: available terminal metadata preserves the observed native status, while custody is explicitly incomplete.

**Native attempts** (exactly mapped bindings, by default or explicit choice) run the caller in the foreground, for Codex after the credential step above, for Claude directly. Their records are created 0600 in a 0700 attempt directory:

- `prompt.md`, read-only, and the request's prompt file;
- `route.json`;
- `renewal.json`, the freshness and renewal classes (Codex, and an opted-in Claude parent's child grant);
- `native/`, the caller's own output: `request.public.json` (credential reduced to provider and expiry), `events.jsonl`, `caller.jsonl`, `stderr.log`, `result.json` and `final.md`;
- `final.md`, the caller's answer text, read back and printed between `DIRECT_CHILD_FINAL_BEGIN`/`END` markers only when the caller answered;
- `state.txt`, which records, for Codex, the lease (`lease_status`, `lease_waited_s`, `lease_released_utc`), `renewal`, `issuer_contact`, `profile_written`, remaining seconds and `credential_snapshot_removed`, and for Claude `credential=none` and `profile_lease=none` (plus the same lease and renewal fields for an opted-in child grant, with `child_grant_profile`); with children, `native_child_routes`, any lowered limits, `native_child_grant`, and after the call `native_child_accepted`, `native_child_refused`, `native_child_results` with `native_children_note`; then the exact `native_command`, `native_caller_exit`, the caller's `native_class`, `front_door_exit` with `front_door_exit_meaning`, answer presence, Bash counts, `final_status`, `custody_status` and `dispatcher_exit`.

**Three statuses, kept apart.** `native_caller_exit` and `native_class` are the caller's classification of the call (below). `front_door_exit` is the native entry's status as relayed by the front door, or the front door's own 90–94. They answer different questions: for example the Claude witness above had caller 0 / `answered` with front door **87**, which in the [Runner entry source](/home/nes/projects/agent-runner/trunk/src-tauri/src/commands/native_root.rs) is the owner's `closed` class: the caller's close after the linked turn end was followed through and the host ended by a kill. It is the expected end of a call the caller closes, not a fault and not evidence that anything was processed; 0 means every harness end was observed with nothing owed. The caller treats 0 and 87 alike. `front_door_exit_meaning` quotes the documented meaning, or says `undocumented status` / `not observed`.

This is a **qualified native record**: answer text, turn and owner events, and Bash argv. There are no Bash output bodies or reasoning, so it is not a complete log. Arbitrary task output in `native/` may still contain secrets; the caller has no redactor. Sol's native tool configuration is Bash-only. Claude's trusted-task configuration, used uniformly for every Claude seat, also offers built-in Read, Write and Edit: their effects are the harness's own and their bodies are not in the record, and Claude Code's managed settings still apply. On both, a trusted shell can still start processes, CLIs and this dispatcher (nested dispatch is bounded only by the brief), so `delegation_capability=not-established` here too.

Native exit codes:

- **2**: input/selection/setup refusal; unmapped native and input checks precede launch, but allocation or partial attempt setup may already have written state;
- **75** (Codex, or an opted-in Claude parent's child grant): profile lease not acquired within the bound, or the lease file was unusable; no task;
- **70** (likewise): no admissible fresh access token (unavailable, not renewed, insufficient, helper failure or unconfirmed helper stop); no native task;
- otherwise the caller's own code: 0 answered, 1 no answer, 3 local refusal, 4 front-door refusal, 5 cancelled, 6 incomplete, 7 cleanup failed, 8 launch failed, 9 ended otherwise, **10 `async-undelivered`**; **6** also when the caller answered but its final could not be kept; `128+N` for a signal.

**Caller 10** means the collected, relay-complete call has a consistent async account reporting an undelivered completion (on front-door 0, 83 or 87), after higher-priority cleanup, collection, cancellation and async-account error checks. Missing or contradictory async evidence is `incomplete` (6), not 10. The dispatcher already propagates the caller's 10; no replay or direct fallback follows. This caller classification is separate from front-door **87**, owner **`closed` tag 7**, a true work command's nonzero **`code:7`**, and harness **SIGKILL 9**; caller 7 still means cleanup failed.

Answered (0) means linked text and collected transport, not that the task was done. Catchable SIGINT, SIGTERM and SIGHUP are recorded throughout preparation, snapshot creation, caller launch and collection. Preparation cancellation cleans the helper/snapshot and starts no task; once a caller exists cancellation is forwarded, including a signal received during Popen, and collection continues within its bound. Snapshot removal is in a finally spanning the attempt. Cancellation returns `128+N`, with caller exit retained when started. The installed caller handles INT/TERM; HUP may terminate it without graceful native cancel. This is dispatcher cleanup, not native/kernel cancel certification; SIGKILL can leave private access-only residue. A native attempt is never replayed, never sent direct afterwards, and its pre-launch refusals are new decisions for the caller, not retries.

Some initial/prelaunch state writes can fail or discard append errors; final custody checks cover selected later writes, not every record. Terminal capture failure is not itself accounted for. Partial records and storage errors remain development limitations; `custody_status=complete` does not certify every prior append.

**Every attempt** has a `route.json` recording:

- the config path and its sha256;
- seat, class, class source, basis, and pass;
- kind and kind source (`unstated` / `not supplied` when no kind was given);
- the rule that fired and the route or alias;
- provider, model, and effort;
- overrides and their reason;
- profile and profile source;
- transport, its source and rule, the site route and native caller (or null), the native deadline, and `native_children` (null, or the opted-in routes, limits, grant source and declaration note; an opted-in Claude parent adds `child_profile`). Native records add `native_credential` (`codex-access-snapshot` or `none`) and `site_binding_source`, which notes that the binding is our declaration: the root-owned site config fixes the actual model, effort and any Claude store and is not read.

**Delegation provenance** in `state.txt` is a record, never a launch gate or a reason to rerun:

- `delegation_capability=not-established` qualifies capability absence separately from restriction requests and metadata, with a `delegation_capability_note`. Older `withheld` records describe metadata only and cannot be read as actual model-facing absence.
- Codex records the listed features, requested settings, parsed readback and `delegation_feature_readback`. Complete false metadata does not establish absent schemas.
- Claude retains every recorded init `tools` value in `delegation_init_tools`, including missing or malformed values. `delegation_init_status` distinguishes known names offered, not listed in valid consistent nonempty lists, unknown metadata, and emitted uses contradicting init omission. These are stream observations, not a complete tool-surface certificate.
- Detection leads: `delegation_tool_uses` counts emitted Claude tool-use blocks naming Agent/Task/Workflow, not completed work or distinct children. `log_collab_lines` counts literal line-start `collab:` text, where Codex renders Wait but not spawn. Quoted command output can cause false positives, and absent markers do not establish absent delegation. Neither counter is a child count.
- `delegation_scope` states what was not covered: shell-launched processes, hooks, plugins and skills.

These fields do not certify that a seat ran alone. ROOT joins actual attempt evidence and retains what its capture cannot establish.

Launch through a native persistent terminal, and record the terminal handle in the emitted `DIRECT_CHILD_STATE` or `DIRECT_CODEX_STATE`. Await that handle until it exits. Each seat is a fresh session, with no resume and no background runs. Collection works as in the [launcher README](../direct-codex-child/README.md).

## Limits

- **No health checks or recovery.** There is no health check, provider or transport fallback, queue, scheduler, or Claude rotation. A launch is never replayed automatically once the native task may have started.
- **Renewal witness is bounded.** One installed `.codex2` sample shows conditional entry, advanced local expiry metadata and collected helper startup/stop. Issuer semantics, token validity, writer attribution, external-writer exclusion, the other profiles and future lifetimes/CLI compatibility remain unestablished. Cross-process refresh races are source readings, not observations.
- **No version guard.** Neither tool checks or pins a native CLI version. Codex restriction requests use listed features; Claude denial arguments use pre-task private help metadata. Unavailable restriction metadata proceeds with qualified provenance. This is bounded compatibility selection, not universal upgrade support or removal of a product provider guard elsewhere.
- **Routing is not validation.** Deterministic routing tests do not show that a class or kind was right or that a model was effective. Records exist for a later benchmark.
- **Not yet in Runner.** This is not Runner or `agents` integration. Frontmatter still selects models inside `agents`.
- **CRW is unchanged.** Its opaque `gpt-xhigh` contract stays as it is; see [`models/roles.md`](../../models/roles.md).
- **Outcome is the caller's to judge.** Process custody proves that the process completed. It does not prove the task was done.

Tests use fake CLIs, a fake stdio app-server and a fake native caller (the CLI tests replace the configured caller with a failing stand-in). They never launch a model, read a real profile or Claude store, or contact an issuer:

```bash
python3 -m unittest discover -s tools/direct-child -p 'test_*.py'
```
