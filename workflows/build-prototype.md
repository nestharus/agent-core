---
workflow:
  id: build-prototype
workflow_dispatch_contract:
  orchestrator: "prototype-orchestrator"
  inputs:
    - "prototype question, project planning path, branch or worktree context, and any defer-source ticket"
    - "evidence that the implementation pipeline or roadmap layer is too unclear to scope directly"
  expectations:
    - "uses unconstrained exploration to arrive at a concrete answer before imposing review discipline"
    - "stabilizes the demonstrable state and organizes findings into a prototype dossier"
    - "runs prototype presentation checks for proof tests, one-question coherence, answer trace, and commit hygiene"
  outputs:
    - "dossier with answer.md, evidence, risk-profile.md, challenges.md, spawned-tickets.md, and branch-disposition.md"
    - "recommended downstream tickets, roadmap revisions, or scope-cut decisions"
  non_goals:
    - "does not bypass the implementation pipeline for ordinary well-scoped work"
    - "does not treat the prototype branch as the load-bearing deliverable"
    - "does not run proposal-based PR review gates during the hack phase"
---
# Build Prototype Workflow

A workflow for **arriving at an answer fast** when the framing of work is too unclear, too large, or too ambiguous for the implementation pipeline to scope. Distinct from `~/ai/workflows/implementation-pipeline.md` — same goal of "land working code" eventually, very different shape getting there.

The principle: when you don't know what to build, you can't run a pipeline that gates on whether the proposal is sound. The proposal doesn't exist yet; the answer doesn't exist yet. **Build the answer, then learn from what you built.** Discipline applies retroactively: organization, risk assessment, and review are end-state work, not in-flight gates.

This workflow does not replace the implementation pipeline. It precedes it. A prototype produces a **dossier** that drives the implementation pipeline, the roadmap workflow, or a scope-cut decision — not a draft PR ready for merge.

## Workflow Dispatch Surface

### Orchestrator

prototype-orchestrator

### Inputs

- prototype question, project planning path, branch or worktree context, and any defer-source ticket
- evidence that the implementation pipeline or roadmap layer is too unclear to scope directly

### Expectations

- uses unconstrained exploration to arrive at a concrete answer before imposing review discipline
- stabilizes the demonstrable state and organizes findings into a prototype dossier
- runs prototype presentation checks for proof tests, one-question coherence, answer trace, and commit hygiene

### Outputs

- dossier with answer.md, evidence, risk-profile.md, challenges.md, spawned-tickets.md, and branch-disposition.md
- recommended downstream tickets, roadmap revisions, or scope-cut decisions

### Non-goals

- does not bypass the implementation pipeline for ordinary well-scoped work
- does not treat the prototype branch as the load-bearing deliverable
- does not run proposal-based PR review gates during the hack phase

## When to use

A prototype is the right tool when at least two of the following are true:

- The "plan" of the work is unclear. You can't write `proposals/NN-*.md` because you don't know what the proposal would say.
- There are many ambiguities. Phase 2.5 of the implementation pipeline would surface so many `NEEDS_INPUT`s that the user spends more time answering questions than the work would take.
- The risk is uniformly HIGH on the touched surfaces (per `~/ai/conventions/risk-profile.md`) — implementation in exhaustive mode would balloon the work to multiples of its real cost.
- The research alone exceeds what a Phase 1 / Phase 2 / Phase 2.5 can accommodate. Reading the code and tests doesn't tell you what to do next.
- The work is too large for one Work Unit but you don't know how to split it. Decomposition itself is the unknown.
- The boundary is unclear. You can't write a Code Boundary or Test Boundary because you don't know which files you'll touch.
- You're at Layer 2 or Layer 3 of `~/ai/workflows/roadmap.md` and the next layer can't be written without evidence the previous-layer decision is feasible.

A prototype is the **wrong** tool when:

- The work is small and well-scoped. The implementation pipeline handles that.
- The framing is clear; you just don't know which approach is best. That's a Phase 3 alternatives section, not a prototype.
- You want to "play with the code." Hacking without an answer to arrive at is exploration, not a prototype.
- The user can answer the ambiguities by talking. A prototype is for ambiguities only the running code can resolve.

## Output: the prototype dossier

The prototype's deliverable is a **dossier** — a markdown bundle of artifacts that captures what was built, what was learned, what risks remain, and what tickets fall out. The dossier is what downstream consumers (implementation pipeline, roadmap workflow, the user, future agents) read. **The dossier is the load-bearing artifact, not the prototype branch.** The branch may be merged, may be discarded, may be cherry-picked into multiple downstream tickets — that's a hand-off decision, not a prototype-completion decision.

Dossier structure (`<project>/planning/<prototype-id>/dossier/`):

- `answer.md` — what the prototype set out to learn, what it learned, in 1-3 pages. The headline. Read this first.
- `evidence/` — the raw outputs that prove the answer: command transcripts, test runs, screenshots, log excerpts, benchmark numbers. Cited from `answer.md` by relative path.
- `risk-profile.md` — per `~/ai/conventions/risk-profile.md`, scored at the end of the prototype, applied to the surfaces the prototype touched. The proper Phase-2.5-equivalent for prototypes happens HERE, not during.
- `challenges.md` — what was hard, what blocked, what surprised. Often the most useful section for downstream consumers.
- `spawned-tickets.md` — the list of tickets the prototype recommends filing: implementation tickets, hardening tickets, scope-cut decisions, additional prototype tickets if the answer surfaced new unknowns.
- `branch-disposition.md` — what to do with the prototype branch: merge as-is (rare), cherry-pick into spawned tickets (common), keep for reference (small percentage), discard (when the answer was "this approach doesn't work"). The branch disposition enum remains `merge | cherry-pick | keep | discard`.
- `reading-list.md` (optional) — pointers to existing code/docs/tests that anyone implementing on the dossier's recommendation should read first.

When the prototype was started with `defer_source`, `branch-disposition.md` also includes a separate section for the original deferred ticket. The existing branch disposition section and enum are preserved; the new section is only the original-ticket lifecycle recommendation:

```markdown
## Original ticket disposition

Disposition: <close-as-superseded | keep-as-meta-tracker | re-defer>

Rationale: <one or more sentences>

Spawned ticket references:
- <key1>: <one-line summary>
- <key2>: <one-line summary>

Backend caveats: <comment naming missing primitives, or n/a>
```

## Phases

The prototype runs in four phases. They are not gated on each other — they are linear in time but the gates between them are about answer-quality, not artifact-completeness.

### Phase P1 — Hack / Explore

The work happens here. The hacking is unconstrained except by the question being investigated.

- **Goal**: arrive at the answer. Build something that proves it. Use any means: parallel hacking agents on different surfaces, hand-edits, jupyter-style iteration, scratch scripts, throwaway forks of files, log-driven probing.
- **Branch convention**: prototype branches use `prototype-<short>` (e.g. `prototype-cloudfront-replication-feasibility`) or `proto-<TICKET-ID>` if a tracker ticket already exists. Branch names do not need to be evergreen; the dossier survives branch deletion.
- **Commit policy**: commits during P1 are work-in-progress. They are not expected to be reviewable. Commit messages can be `wip`, `try X`, `revert Y`, `huh, that worked`. The presentation phase reorganizes them.
- **Gate policy**: **none.** No risk gates. No audit gates. No scope gates. No code review. The orchestrator does not dispatch process-tree-auditor mid-flight. The orchestrator does not block on test pass / lint pass / type-check during P1 — failing builds during exploration are normal.
- **Agent dispatch**: the prototype-orchestrator dispatches `gpt-high` hack agents in parallel on different surfaces or different approaches. Each agent's prompt is the question + the surface + a directive to "make it work, capture the evidence, don't worry about hygiene." Agents can dispatch sub-agents (research, code-tracer) when they need to.
- **Iteration**: the human running the prototype reviews progress informally — not as a gate, as collaboration. "I tried X and it didn't work because Y; let me try Z" is the cadence. The orchestrator surfaces NEEDS_INPUTs only when an agent genuinely cannot decide between two paths and the user must arbitrate.
- **Exit condition**: the question has an answer. The answer can be `it works, here's how` / `it doesn't work, here's why` / `the real constraint is X, not Y` / `we need a different approach entirely (re-frame)`. Exit is a human decision; the orchestrator asks "do we have an answer?" when an agent reports it has hit a stable conclusion, and the human says yes/no.

### Phase P2 — Stabilize

The hacking phase ends with the prototype branch in a messy state. P2 puts a known-good marker down before the chaos of presentation.

- **Goal**: get the working state to compile / run / pass any tests that exist on the surface. The state is reproducible.
- **What to fix**: actual breakage that prevents the answer from being demonstrated — failing imports, missing fixtures, missing config files, environment variables that exist in the prototyper's shell but not in the dossier.
- **What NOT to fix**: stylistic issues, lint warnings, suboptimal code, missing tests for code that wasn't part of the answer, refactor opportunities. Those land later.
- **Tests**: write the minimum tests that **demonstrate the answer**. Not characterization tests, not regression tests — proof tests. "Run this test, it passes, that's the evidence the answer is correct." These tests go into the dossier's `evidence/` even if they end up in the spawned implementation tickets later.
- **Branch state**: at end of P2, the prototype branch is at a commit you'd be willing to share for someone else to reproduce the answer. It is NOT necessarily a commit you'd merge.
- **Gate policy**: still none. P2 is a stabilization step, not a review.

### Phase P3 — Present

Discipline applies here, retroactively. P3 is the prototype's analog of `~/ai/workflows/pr-review.md`: it makes the work consumable for downstream readers. The two workflows share `commit-hygiene-operator` but are otherwise distinct — PR-review's gates presuppose a proposal contract; P3's analog gates presuppose an answer.

- **Goal**: organize the prototype's work into reviewable units that future readers (implementers, the user, the next prototype) can understand. Risk assessment happens at this phase, on the surfaces the prototype actually touched (which may be different from what was anticipated).

P3 has six sub-steps. The first three are the prototype-specific authoring (risk profile, challenges, spawned tickets); the next three are the **analogs of PR-review gates** without requiring a proposal. The sixth (commit-hygiene) is shared with PR-review wholesale.

#### P3.1 — Risk profile authoring

Dispatch a `gpt-high` researcher with the post-stabilize branch and the touched surfaces as input, to produce `dossier/risk-profile.md` per `~/ai/conventions/risk-profile.md`. Per-surface scoring on all axes, evidence-cited. **This is the only Phase-2.5-equivalent the prototype runs.**

#### P3.2 — Challenges authoring

Dispatch a researcher (or self-author) to capture `dossier/challenges.md` — what was hard, what blocked, what surprised. Include false starts. The challenges section is often the most useful artifact for spawned tickets because it lists the cliffs the implementation will hit.

#### P3.3 — Spawned-tickets authoring

Review what the prototype produced. For each piece of value the prototype demonstrated, propose a downstream ticket. For each high-risk surface, propose a hardening ticket. If the answer was "this approach doesn't work," propose a scope-cut decision. Write these into `dossier/spawned-tickets.md` with: target board, summary, recommended description, parent epic, labels, blocking-vs-related links.

Each spawned-ticket entry also includes:

- `story_point_estimate`: integer selected from `1, 2, 3, 5, 8, 13, 21, 40, 100`, chosen from the prototype evidence as a coarse dossier estimate.
- `estimate_rationale`: one sentence citing prototype evidence that explains why the estimate fits the spawned-ticket surface.
- `confidence`: `high | medium | low`, based on how directly the prototype evidence demonstrates the spawned-ticket surface.

Render those fields in each entry as:

- `**Story Point Estimate:** <int from 1, 2, 3, 5, 8, 13, 21, 40, 100>`
- `**Estimate Rationale:** <one sentence citing prototype evidence>`
- `**Confidence:** high | medium | low`

#### P3.4 — Proof-test audit (analog of PR-review test-audit)

PR-review's test-audit verifies the test set covers the proposal's test-intent track. Prototypes have no proposal, but they DO have an answer the dossier claims. Proof-test audit verifies the proof tests in `dossier/evidence/` actually demonstrate the answer.

- Dispatch a `gpt-high` reviewer with the dossier's `answer.md` (claimed answer + evidence pointers) and the proof tests written during P2 stabilization.
- For each evidence pointer in `answer.md`, the reviewer verifies a corresponding proof test exists, the test is scoped to the claimed behavior, and the test passes against the post-stabilize branch.
- Verdict: `LOW` (every evidence pointer has a passing proof test scoped to the claim) / `MEDIUM` (one or two pointers covered by adjacent tests rather than direct ones) / `HIGH` (a claim is asserted by no test, OR a test does not actually exercise the claimed behavior — the answer is unproven).
- Output: `dossier/proof-test-audit.md`. A HIGH verdict halts P3 — the dossier cannot claim an answer the tests don't demonstrate.

#### P3.5 — One-question check (analog of PR-review multi-concern)

PR-review's multi-concern asks "is this one PR or several?" The prototype analog asks "is this one prototype or several?" — a prototype that drifted to answer multiple questions in one run produces a confused dossier; the right move is to split into two dossiers or two follow-up prototypes.

- Dispatch a `claude-opus` reviewer with `answer.md` + `spawned-tickets.md` + the diff.
- The reviewer checks whether the answer reads as one coherent question with one coherent answer, or whether the work actually answered N questions and the dossier conflates them. The spawned-tickets list is a hint: if it's decomposing the prototype's work into K downstream tickets where K > 1 and they don't share a common dependency, the prototype was multi-question.
- Verdict: `SINGLE_QUESTION` (one prototype, one answer, coherent) / `MULTI_QUESTION` (the prototype answered N questions; recommend splitting the dossier into N separate dossiers OR re-framing `answer.md` as a multi-part answer with explicit sub-question structure).
- Output: `dossier/one-question-check.md`. A `MULTI_QUESTION` verdict either splits the dossier (re-runs P3.1–P3.6 per sub-dossier) or rewrites `answer.md` to have explicit sub-question structure.

#### P3.6 — Answer-trace check (analog of PR-review justification)

PR-review's justification verifies every change in the diff traces to ticket / proposal / contract / hookpoints. The prototype analog verifies every piece of code on the prototype branch traces to the answer.

- Dispatch a `claude-opus` reviewer with the diff (`git diff main..HEAD`) and the dossier's `answer.md` + `evidence/`.
- For each file/hunk in the diff, the reviewer asks: does this serve the answer, or is it hack-debris that survived stabilization but doesn't belong? Common debris: scratch print statements, test-mode flags, hardcoded local paths, commented-out experimentation, files added during P1 to test something that is no longer reachable from the answer.
- Verdict: `LOW_DEBRIS` (every change serves the answer) / `MEDIUM_DEBRIS` (one or two minor leftovers; flag for cleanup before P4) / `HIGH_DEBRIS` (substantive code on the branch is not traceable to the answer; the branch needs cleanup before the dossier can claim it as the answer's evidence).
- Output: `dossier/answer-trace.md`. A `HIGH_DEBRIS` verdict halts P3 and re-enters P2 to clean up the unjustified content.

#### P3.7 — Commit reorganization (shared with PR-review wholesale)

Rebase / squash / split the P1 commits into logical units. Commit messages now describe what each unit does and why, in real prose. The `commit-hygiene-operator` (`~/ai/agents/commit-hygiene-operator.md`) is the right tool — same operator PR-review uses, no prototype-specific adaptation needed. The reorganization preserves the cumulative diff; only history shape changes.

#### P3.8 — Branch-disposition decision

Write `dossier/branch-disposition.md` with the recommendation: merge / cherry-pick / keep / discard. The dossier authors recommend; the user decides.

#### P3 gate

ONE human gate at the end of P3 — the user reviews the dossier (`answer.md` + `risk-profile.md` + `spawned-tickets.md` + the three analog-gate verdicts + `branch-disposition.md`) and either approves or asks for revisions. Revisions are handled like Phase 2.5 in the implementation pipeline: dispatch a revision pass against the specific dossier section, do not re-do P1-P2. If P3.4 / P3.5 / P3.6 returned a halting verdict, the gate cannot present "approve" as an option until the halting condition is resolved.

### Phase P4 — Hand-off

The prototype produces tickets and updates downstream artifacts. Then it's done.

- **File spawned tickets**: dispatch the project ticket-system operator for each entry in `dossier/spawned-tickets.md`. Jira is the default path: dispatch `jira-operator` (`task=create`) and write the integer `story_point_estimate` to Jira `customfield_10016`. When the ticket-system is Linear, write the integer `story_point_estimate` to the Linear `estimate` field. The rendered ticket description must preserve `Story Point Estimate:`, `Estimate Rationale:`, and `Confidence:` lines from the dossier entry. Apply project label conventions (`hardening` for risk-reduction tickets per `~/projects/<name>/AGENTS.md`). Capture each new key + URL in the dossier.
- **Update project risk profile**: append the prototype's risk-profile entries to `<project>/planning/risk-profile.md` per `~/ai/conventions/risk-profile.md` § Project-level profile.
- **Apply branch disposition**:
  - **merge**: the prototype branch is rare-but-valid feature work. Run it through the implementation pipeline starting at Phase 6 (the test-and-code structure already exists). The dossier is the proposal-equivalent.
  - **cherry-pick**: each spawned implementation ticket cherry-picks the relevant commits from the prototype branch into its own branch. The prototype branch becomes a reference, not a merge candidate.
  - **keep**: the prototype branch lives on origin under `prototype-*` for reference. Spawned tickets reference it.
  - **discard**: the prototype branch is deleted from origin. The dossier survives in `<project>/planning/<prototype-id>/`.
- **Execute original-ticket disposition** when `defer_source` is set:
  1. Parse the approved `## Original ticket disposition` section after P3 approval.
  2. Reuse the keys from the prior **File spawned tickets** step; do not re-file tickets in this step.
  3. Execute `close-as-superseded`, `keep-as-meta-tracker`, or `re-defer` mechanically and without a second human gate:
     - `close-as-superseded` closes or supersedes the original ticket where the backend supports it and records spawned-ticket links/comments.
     - `keep-as-meta-tracker` keeps or restores the original as the parent/meta tracker and relates spawned tickets.
     - `re-defer` keeps the deferred marker, comments remaining unknowns, and queues the next prototype using existing dispatch conventions.
  4. Write `${planning_dir}/dossier/original-ticket-disposition-execution.md` with the parsed disposition, spawned ticket keys, ticket-operator prompt/log paths, backend operations attempted, fallback reasons, created link evidence, final comment target, and `actor=prototype-orchestrator`.
- **Update roadmap if applicable**: when the prototype was triggered by a roadmap-layer decision (Layer 2 substrate validation, Layer 3 WU decomposition gate), update the roadmap layer with the prototype's findings. The roadmap workflow's relevant proposer / risk operator re-runs against the updated layer artifacts.
- **Gate policy**: no further gate. P4 is mechanical — the human-gate decision was P3.

## Relationship to other workflows

### Defer-from-implementation

The implementation pipeline at `~/ai/workflows/implementation-pipeline.md` Phase 2.5 may discover the framing is unworkable. The signals:

- The Phase 2.5 risk profile rolls up to HIGH across **most** touched surfaces, not just one or two. The exhaustive mode would expand the WU to multiple WUs.
- Phase 2.5 sub-step 2.5.4 (duplicates inventory) finds a sprawling parallel-systems landscape that the WU's scope cannot navigate without architectural decisions.
- The lifecycle map (sub-step 2.5.2) cannot be drawn — too much of the touched process is operational knowledge, not repo-derivable.
- The proposer in Phase 3 cannot stay within a coherent scope; the proposal keeps growing.

When any of these fire, the orchestrator emits a `NEEDS_INPUT` to the root with options: `proceed in exhaustive mode (the WU is just big)`, `defer to prototype (framing is too unclear, prototype to clarify, then re-ticket)`, `terminate WU (the work is wrong-shaped, abandon)`. The user picks. If `defer to prototype` is picked, the orchestrator dispatches the prototype-orchestrator (`~/ai/agents/prototype-orchestrator.md`) with the WU's question as the prototype's question, and the implementation orchestrator halts. The prototype's dossier later spawns new tickets that re-enter the implementation pipeline with clearer scope.

### Roadmap workflow

`~/ai/workflows/roadmap.md` Layer 2 (engineering-roadmap) and Layer 3 (per-phase ai-roadmap) are the most common upstream of prototypes. Specifically:

- A Layer 2 engineering-roadmap names a substrate for foundation phases. If the substrate's feasibility is unclear (will this database/queue/runtime work for our load? does this third-party integrate at all?), a prototype validates it before the layer's risk gates pass. The prototype's dossier informs the engineering-roadmap revision.
- A Layer 3 ai-roadmap decomposes a phase into Work Units. If a WU's contract / parallelizability / schema cannot be named without trying it, a prototype clarifies it. The dossier then drives the WU's eventual ticket and the WU's contract.

The roadmap-orchestrator (when wired to recognize prototype-needs) can dispatch the prototype-orchestrator as a sub-flow. The prototype's dossier is then consumed by the roadmap proposer in the next revision round.

A prototype dispatched from a roadmap layer (Layer 2 or Layer 3 escape hatch) typically produces more spawned-tickets than an implementation-deferred prototype, and many of those tickets land at lower confidence because the surface was being explored, not characterized. That's expected. The dossier's job is to seed the implementation backlog with a coarse but honest estimate; later P3 refinement (Phase 3 of the consumed implementation pipeline) raises confidence per ticket.

### Implementation pipeline

The implementation pipeline consumes the prototype's spawned tickets via standard ticket-driven entry. The dossier becomes the WU's pre-Phase-1 research input — it pre-answers questions Phase 1 would otherwise need to ask. Phase 2.5 still runs on the implementation WU, but it can lean heavily on dossier content for the touched surface (the prototype already characterized it).

Implementation WUs spawned from a prototype dossier should:

- Reference the dossier in the JIRA description (path or summary excerpt — local paths are not externally citable, so summarize).
- Inherit the dossier's risk profile as a starting point; Phase 2.5 may revise scores but should cite dossier evidence to do so.
- Stay narrower than the prototype if the prototype's answer included scope-cut. The dossier's `spawned-tickets.md` is the canonical decomposition; the implementation WUs should not re-aggregate.

## Anti-pattern

- **Prototype as feature-bypass**: using a prototype to skip the implementation pipeline's gates because the gates are inconvenient. The signal that this is happening: the prototype's branch is being merged directly to main without spawned-ticket implementations. Prototypes do not skip implementation; they precede it.
- **Endless P1**: hacking without an exit condition. P1's exit is "we have an answer." If the team can't articulate what answer they're looking for, the prototype is research disguised as code. Stop, write the question down, restart.
- **Skipping P3**: jumping from P2 directly to merging the prototype branch. The dossier doesn't exist; the next team to touch this surface has no record of what was learned. If P2's stable state is mergeable as-is, P3 is still required to capture the dossier — even if the dossier's `branch-disposition.md` says "merge as-is."
- **Risk assessment during P1**: applying risk gates during the hack phase. This defeats the purpose. Risk-aware prototyping is a contradiction; either you know enough to be risk-aware (use implementation pipeline) or you don't (don't gate the exploration).
- **Discarding the dossier**: the prototype branch was a dead end (`branch-disposition: discard`) so the dossier is also discarded. Wrong. The dead end is the answer; the dossier captures *why* this approach didn't work, which prevents the next team from re-running the same prototype.
- **Single-agent prototype**: only the orchestrator and one hack agent. Prototypes are most effective with parallel agents on different surfaces or different approaches; serializing them defeats the speed advantage. (One-agent prototypes are valid for very narrow questions; the anti-pattern is doing it by default.)

## Operational notes

- The prototype branch lives in a worktree per `~/ai/conventions/worktree-isolation.md`. Multi-repo umbrella projects (`~/ai/conventions/project-layout.md` § Multi-repo umbrella variant) place prototype worktrees alongside other branch worktrees: `<project>/trunk/<repo>-worktrees/prototype-<short>/`.
- The dossier lives in the project's planning tree, not in the worktree: `<project>/planning/<prototype-id>/dossier/`. This ensures the dossier survives branch deletion.
- The prototype-orchestrator (`~/ai/agents/prototype-orchestrator.md`) is the operator. It is **not** the implementation-pipeline-orchestrator with gates disabled; it is its own thing, with very different procedure.
- Prototype JIRA tickets (when one exists) use issue-type `Spike` if the project's board supports it; otherwise `Task` with label `prototype`. The label is the searchable handle that distinguishes prototype work from feature work.
