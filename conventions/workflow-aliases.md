# Workflow Aliases Convention

## Purpose

Workflow alias declarations reduce the cost of resolving shorthand such as "RCA workflow" or "review workflow" by giving workflow docs a compact lookup surface for identity, alias targets, disambiguation, and dispatch facts. This convention is not the alias index data file, not a discovery tool, and not a runtime resolver.

## Use When / Do Not Use When

Use these blocks when a workflow doc under `~/ai/workflows/` needs stable identity, human alias declarations, phase or section targets, or a concise dispatch surface for agents deciding whether to read or dispatch that workflow.

Do not use these blocks to restate the workflow procedure, centralize project-specific routing cues, record absence, or add metadata to non-workflow operator files. Workflow docs with no declared aliases omit `workflow_aliases`; do not write `workflow_aliases: []`.

## Workflow identity

Every workflow doc that declares `workflow_aliases` or `workflow_dispatch_contract` must declare `workflow.id`.

```yaml
workflow:
  id: implementation-pipeline
```

`workflow.id` is lowercase kebab-case. When first introduced, it matches the workflow filename stem. After introduction, it is stable: if a file is renamed, keep the existing `workflow.id` until aliases, future index data, and consumers are migrated together.

Required shape:

| Key | Required | Type | Constraint |
|---|---|---|---|
| `workflow.id` | required when `workflow_aliases` or `workflow_dispatch_contract` is present | string | lowercase-kebab-case; matches filename stem when introduced; stable thereafter |

## Workflow alias declarations

`workflow_aliases` is an ordered array of human phrases and target tuples. Use an array, not an object keyed by alias, so related or ambiguous aliases can be reviewed side by side.

```yaml
workflow_aliases:
  - alias: "<human phrase>"
    target:
      workflow_id: "<stable workflow.id>"
      path: "workflows/<file>.md"
      anchor: "<optional markdown anchor>"
      phase: "<optional phase or step label>"
    disambiguation:
      - context: "<static one-sentence predicate>"
        preferred_target:
          workflow_id: "<workflow.id>"
          path: "workflows/<file>.md"
          anchor: "<optional markdown anchor>"
          phase: "<optional phase or step label>"
        competing_targets:
          - workflow_id: "<workflow.id>"
            path: "workflows/<file>.md"
            anchor: "<optional markdown anchor>"
            phase: "<optional phase or step label>"
        fallback_question: "<one user-facing question>"
```

Alias entry schema:

| Key | Required | Type | Constraint |
|---|---|---|---|
| `workflow_aliases` | optional | array | omit when there are no aliases; author order is preserved |
| `workflow_aliases[].alias` | required | string | human phrase before normalization |
| `workflow_aliases[].target.workflow_id` | required | string | stable `workflow.id` |
| `workflow_aliases[].target.path` | required | string | repo-root-relative path from `~/ai/` |
| `workflow_aliases[].target.anchor` | optional | string | Markdown anchor form for a heading target |
| `workflow_aliases[].target.phase` | optional | string | human-stable phase label such as `Phase 0` or `Phase 2.5` |
| `workflow_aliases[].disambiguation` | optional | array | required when the alias is ambiguous across workflows |

Normalize aliases by lowercasing, trimming, replacing punctuation separators with spaces, and collapsing repeated whitespace. Do not stem words, expand synonyms, or apply fuzzy matching.

Within one workflow doc, no two entries may share a normalized alias unless they differ by `target.phase` or `target.anchor`. Across workflow docs, a normalized alias should be globally unique unless every competing declaration includes a `disambiguation` record. Ambiguous aliases without `disambiguation` are out-of-spec under this convention.

Simple example:

```yaml
workflow:
  id: verified-rebase
workflow_aliases:
  - alias: "rebase verification"
    target:
      workflow_id: verified-rebase
      path: "workflows/verified-rebase.md"
```

Ambiguous example:

```yaml
workflow:
  id: implementation-pipeline
workflow_aliases:
  - alias: "RCA workflow"
    target:
      workflow_id: implementation-pipeline
      path: "workflows/implementation-pipeline.md"
      anchor: "phase-0---rca-bugs-only"
      phase: "Phase 0"
    disambiguation:
      - context: "The user is asking about a defect, regression, or unexplained behavior inside a WU."
        preferred_target:
          workflow_id: implementation-pipeline
          path: "workflows/implementation-pipeline.md"
          anchor: "phase-0---rca-bugs-only"
          phase: "Phase 0"
        competing_targets:
          - workflow_id: risk-reduction
            path: "workflows/risk-reduction.md"
        fallback_question: "Do you mean RCA inside the implementation pipeline, or a separate risk-reduction workflow?"
```

## Per-context disambiguation

`disambiguation` records are static hints for aliases that overlap across workflows. They identify when one target should win, which targets compete, and what single question to ask when context is still insufficient.

| Key | Required | Type | Constraint |
|---|---|---|---|
| `workflow_aliases[].disambiguation[].context` | required when entry present | string | static one-sentence predicate |
| `workflow_aliases[].disambiguation[].preferred_target` | required when entry present | object | same shape as `target` |
| `workflow_aliases[].disambiguation[].competing_targets` | required when entry present | array | entries use the same shape as `target` |
| `workflow_aliases[].disambiguation[].fallback_question` | required when entry present | string | one user-facing question |

These notes compose with [workflow-routing.md](../conventions/workflow-routing.md). That convention still owns cue precedence and the fallback rule to ask the user when ambiguity remains. Alias declarations identify candidate workflows and phase or section targets; they do not replace project `AGENTS.md` routing tables.

If a delegated sub-agent must ask the user, it follows [agent-questions-and-session-graph.md](../conventions/agent-questions-and-session-graph.md). `fallback_question` is only the question text, not the JSON question artifact envelope.

## Workflow dispatch contract

`workflow_dispatch_contract` is concise metadata for deciding whether a workflow is the right dispatch target. It is not the workflow procedure and does not replace the workflow body.

The block has a fixed key set. The only keys allowed are `orchestrator`, `inputs`, `expectations`, `outputs`, and `non_goals`; no other keys are allowed.

```yaml
workflow_dispatch_contract:
  orchestrator: "<operator-or-workflow-owner>"
  inputs:
    - "<dispatch input>"
  expectations:
    - "<what the workflow will do at dispatch scale>"
  outputs:
    - "<observable result or artifact>"
  non_goals:
    - "<what this workflow must not be used for>"
```

Dispatch contract schema:

| Key | Required | Type | Constraint |
|---|---|---|---|
| `workflow_dispatch_contract.orchestrator` | required when block present | string | operator or workflow owner |
| `workflow_dispatch_contract.inputs` | required when block present | array of strings | concise; target 1-5 entries |
| `workflow_dispatch_contract.expectations` | required when block present | array of strings | concise |
| `workflow_dispatch_contract.outputs` | required when block present | array of strings | concise |
| `workflow_dispatch_contract.non_goals` | required when block present | array of strings | concise |

Example for [implementation-pipeline](../workflows/implementation-pipeline.md):

```yaml
workflow:
  id: implementation-pipeline
workflow_dispatch_contract:
  orchestrator: "implementation-pipeline-orchestrator"
  inputs:
    - "ticket id and branch/worktree/planning paths"
    - "non-empty ticket description from the configured ticket system"
  expectations:
    - "runs research, proposal, risk, implementation, review, PR, and audit phases"
    - "uses model-owned gates; only Phase 2.5 review and NEEDS_INPUT new-value questions reach the user"
  outputs:
    - "planning artifacts under the per-WU planning directory"
    - "tested repository diff and PR URL when the work proceeds"
  non_goals:
    - "does not use git-resident ticket files as the source of truth"
    - "does not skip phases implicitly"
```

Example for [verified-rebase](../workflows/verified-rebase.md):

```yaml
workflow:
  id: verified-rebase
workflow_dispatch_contract:
  orchestrator: "jj-operator"
  inputs:
    - "BRANCH and TARGET"
    - "optional SOURCE and stacked parent bundle"
  expectations:
    - "produces a deterministic bundle for rebase review"
    - "does not push and does not resolve conflicts"
  outputs:
    - "bundle under .tmp/verified-rebase/<branch-slug>/<timestamp>/"
    - "stdout verdict CLEAN, DIRTY-EXPLAINED, DIRTY-UNPROVENANCED, or BLOCKED"
  non_goals:
    - "does not provide a plain rebase fallback"
    - "does not decide whether the caller should push"
```

## Naming: "workflow dispatch contract" vs "contract"

A workflow dispatch contract is only the concise lookup surface for deciding whether to dispatch a workflow. It is distinct from implementation contracts, proposal contracts, test contracts, rebase contracts, and other in-prose uses of `contract`.

Use the full phrase `workflow dispatch contract` in prose and the key `workflow_dispatch_contract` in YAML. Do not shorten the block to `contract` or `workflow_contract`.

## Composition with adjacent conventions

[workflow-routing.md](../conventions/workflow-routing.md) is not replaced. Project `AGENTS.md` still owns cue routing, workflow precedence, and project-local routing tables.

[operator-file-format.md](../agents/operator-file-format.md) is not replaced. Operator frontmatter applies to `~/ai/agents/*.md` prompt files; workflow aliases and workflow dispatch contracts apply to `~/ai/workflows/*.md` topology and procedure docs.

[agent-questions-and-session-graph.md](../conventions/agent-questions-and-session-graph.md) is not replaced. Delegated-agent question artifacts, answer artifacts, and continuation evidence are still owned by that convention.

## Anti-pattern / Non-goals

Do not treat this convention as a runtime resolver, scanner, validator, or CLI contract. It does not resolve aliases programmatically, validate future declarations programmatically, or change current dispatch behavior.

Do not edit existing workflow docs solely because this convention exists. Adoption happens when a workflow doc is intentionally updated by a scoped workflow-doc or data-authoring change.

Do not infer aliases from body prose, add empty alias blocks, or use fuzzy matching to paper over unclear declarations. If an alias is ambiguous, declare `disambiguation` or ask through the existing routing and question conventions.

## Lifecycle / Maintenance

Change this convention when a future workflow-doc metadata surface needs new fields, future B2 alias data cannot represent a real workflow ambiguity, or future validator/tooling work needs a documented rule before enforcement.

Drift is detected through broken cross-references, repeated agent confusion around the same aliases, workflow docs using non-conforming metadata shapes, and future validator failures.

Supersession happens by replacing this convention with a new explicit convention and migrating declared workflow metadata, future alias/index data, and consumers in the same scoped change. Do not leave duplicate active schemas for the same workflow alias surface.
