# Feature-development workflow

Canonical convention for shipping a feature that decomposes into 2+ tickets, has a user-facing surface, or ships behavioral change. Sits *above* manager flavors (max/pragmatic/hackerman), not as a replacement.

## When to use

Use feature-development by default when the work decomposes into 2+ tickets, has a user-facing surface, or ships behavioral change. Use the direct-to-trunk exception only for bounded single-ticket markdown, convention, or auditor refinement work with no user-facing prototype.

| Strategy | When | Flavor relationship | Evidence pack |
|---|---|---|---|
| max | Critical infrastructure, regression-prone work, or work where a defect cascades across other WUs. | `manager-max` remains the safest flavor inside each ticket and at final review; feature-development still controls branch and evidence topology when the work qualifies as a feature. | Full PR-body evidence for each ticket PR and the final feature PR. |
| pragmatic | Bounded single-ticket work with low blast radius and no user-facing surface. | `manager-pragmatic` may stay direct-to-trunk only while the work remains bounded to one ticket and has no feature-level integration need. | Minimal correct PR-body evidence for the bounded change. |
| feature-development | 2+ tickets, user-facing surface, or shipped behavioral change. | Strategy layer above the active manager flavor; the flavor decides risk posture, while this strategy decides branch topology, evidence expectations, prototype payload, and QA record. | Universal PR-body evidence on every ticket PR plus the final feature-to-trunk PR. |
| hackerman | Throwaway, internal-only, speed-biased work where the user explicitly accepts narrow proof and residual risk. | `manager-hackerman` does not waive feature-development when the result is a shipped multi-ticket feature. | Immediate functional proof for internal throwaway work; universal PR-body evidence for shipped feature work. |

## The 12-step pipeline

1. Roadmap: start from a feature brief, market/product roadmap, or strategy record; output the feature problem, candidate shapes, acceptance criteria, and open questions; gate on whether the feature is clear enough to prototype, scope, or terminate.
2. Prototype: when feasibility, shape, or behavior is uncertain, build a small prototype to answer the open questions; output a prototype dossier with findings; gate on whether the result says pursue, change scope, or stop.
3. Scope: use roadmap and prototype evidence to choose the actual feature slice; output a scoped feature definition with explicit anti-scope; gate on whether the slice is coherent and reviewable.
4. Ticket decomposition: split the scoped feature into ticket-sized Work Units, one bounded surface or contract per ticket; output the scoped ticket list and dependencies; gate on whether every ticket can run through the implementation pipeline.
5. Feature branch: create or verify the feature branch from the repo integration trunk; output the feature branch and feature worktree; gate on branch baseline correctness and worktree isolation.
6. Ticket PR target: each ticket runs as its own implementation-pipeline WU and opens its PR against the feature branch, not trunk; output one draft ticket PR per ticket; gate on the PR base matching the feature branch.
7. Validate and merge immediately: once a ticket PR passes its active manager-flavor gates and review policy, merge it into the feature branch; output the merged ticket PR and evidence; gate on the same validated state that would have allowed the ticket to ship.
8. No cascading rebases: keep subsequent ticket work based on the feature branch so each ticket absorbs prior ticket merges through the shared branch; output a current feature branch; gate on avoiding manual DAG management unless a conflict demands normal rebase verification.
9. Final feature PR: after all scoped ticket PRs are merged, open the feature-branch-to-trunk PR; output the final PR; gate on all tickets being represented and the final diff matching the feature scope.
10. Final evidence pack: assemble the ticket evidence and final integrated evidence in the final PR body; output the reviewer-facing evidence pack; gate on evidence being sized to the PR type and understandable without local planning artifacts.
11. Prototype payload upload: when the feature has a runnable prototype, place the payload under `prototype/<feature-slug>/` and link it from the final PR; output the payload directory; gate on bring-up and smoke-test instructions being present.
12. QA evaluation: run the Playwright-driven QA agent against the prototype when operational and attach the verdict to the final PR; output the QA verdict, or a recorded placeholder gap when the agent is not yet operational; gate on the gap being explicit rather than hidden.

## Universal evidence-pack rule

Evidence packs live on PR bodies, not on branches. Size the PR-body evidence to the PR type:

- UI / user-facing: screenshots plus a text tour of the action and result.
- Service / API: API call examples such as curl or httpie, response snapshots, and relevant logs.
- Workflow / convention / Markdown: diff narrative, DECISIONS entry, and allowed command output; do not add markdown shape tests for this evidence.
- Test-only: test output plus failure-then-pass demonstration.

## Branch baseline

Feature branches start from the repo's integration trunk. For `nestharus/ai`, trunk is `master`, not `dev`.

## Prototype payload

Runnable prototype payloads live under `prototype/<feature-slug>/` and include `docker-compose.yml` plus `README.md`. The README names prerequisites, environment variables, bring-up commands, a smoke-test command, and expected output screenshots when screenshots are applicable. Link the prototype directory from the final PR body.

## QA evaluation

The required end-to-end check is a Playwright-driven QA agent run against the prototype. If that agent is not yet operational, record the gap explicitly in the final PR body's evidence pack and continue under the active manager flavor's review policy. This WU only records the requirement; operational wiring belongs to a downstream ticket.

## Risk note (AI-execution inverts the divergence calculus)

Traditional feature branches can accumulate costly divergence. AI-driven tickets land quickly enough that the feature branch should stay close to trunk, while the integration benefit of ticket PRs targeting a shared feature branch outweighs the divergence cost and avoids cascading rebases across in-flight ticket work.

## Direct-to-trunk exception

Bypass the feature branch only for bounded single-ticket work with no feature-level integration need, such as:

- single-file convention or Markdown patches;
- single-ticket workflow document edits;
- single-ticket auditor refinements;
- small internal-only cleanup that does not ship a user-facing prototype or behavioral feature.

If the work grows into 2+ tickets, gains a user-facing surface, or ships behavioral change, return to feature-development.

## Cross-references

- `~/ai/conventions/worktree-isolation.md`
- `~/ai/conventions/workflow-aliases.md`
- `~/ai/agents/work-manager-operator-max.md`
- `~/ai/agents/work-manager-operator-pragmatic.md`
- `~/ai/agents/work-manager-operator-hackerman.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/build-prototype.md`
- `~/ai/workflows/feature-development.md`
- `~/ai/agents/feature-orchestrator.md`
- ACR-156
- ACR-157
- ACR-173
- ACR-175
