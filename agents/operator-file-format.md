# Operator Prompt File Format

## Declared roles

`validator`, `parser`, `formatter`.

This file-local declaration reflects this document's ownership of operator schema validation rules, YAML contract parse shape, and canonical format examples.

Operator prompts are `.md` files invoked via the `agents` CLI. See `~/ai/workflows/agents-cli.md` for local usage notes. This doc specifies the format for operator prompt files in `~/ai/agents/` and `~/work/agents/`.

Use this as the reference shape for new operators. For CLI resolution order, see `/home/nes/projects/agent-runner/README.md`.

## Frontmatter

Every operator file starts with a required YAML frontmatter block (this is the shape the `agents` CLI expects — see `/home/nes/projects/agent-runner/README.md` §"Adding an Agent"):

```yaml
---
description: '<one-sentence role statement>'
model: <default-model-id>
output_format: ''
---
```

Frontmatter is the CLI metadata contract. Preserve these three keys exactly.

- `description` tells another operator or a human when to choose this file. Single-quoted to keep YAML parsing simple even when the description contains colons or other punctuation.
- `model` sets the default model. The caller can override it with `-m <other-model>` at invocation time.
- `output_format` is usually the empty string. Non-empty values are for operators that produce a structured output schema (e.g., JSON) — leave empty unless you need this.

The operator's **name is the filename stem** (e.g., `coderabbit-operator.md` → named `coderabbit-operator`). There is no separate `name:` frontmatter key.

Example:

```yaml
---
description: 'Run the CodeRabbit review loop until review value converges'
model: gpt-high
output_format: ''
---
```

## Contract block (`operator-contract-v1`)

Every operator or workflow Markdown file MUST contain a `## Contract` heading with a single fenced YAML block whose first key is `schema: operator-contract-v1`. The contract block is the machine-readable call interface for dispatchers.

The schema fields are:

- `inputs:` - required and optional input keys per task, with type and default-source annotations. Each input has `name`, `type`, `required`, `default_source`, and `description`.
- `defaults:` - project-specific or wrapper-declared default values. Each default has `name`, `value`, and `source`.
- `secrets:` - environment variables the operator reads.
- `outputs:` - return envelope shape by task. Each output has `task`, `success_shape`, and `wrote_lines`.
- `errors:` - known error envelope shapes. Each error has `class`, `cause`, and `recovery`.
- `side_effects:` - file, system, or external-API mutations.
- `must_delegate:` - operations callers MUST invoke through this operator.
- `may_direct:` - operations callers MAY invoke directly.
- `forbidden_direct:` - operations callers MUST NEVER do directly.
- `inherits:` - project-wrapper-only base operator path or identity.
- `base_procedure:` - project-wrapper-only base operator procedure-file path.

Schema reference:

```yaml
schema: operator-contract-v1
inputs:
  - name: <input-key>
    type: <string | int | bool | enum | path>
    required: <true | false>
    default_source: <wrapper:<name> | env:<VAR> | caller | prompt | derived | base>
    description: <one-line description>
defaults:
  - name: <input-key>
    value: <default-value>
    source: <wrapper:<name> | env:<VAR> | base>
secrets:
  - <ENV_VAR_NAME>
outputs:
  - task: <task-name>
    success_shape: <one-line description of stdout or return shape>
    wrote_lines: [<artifact-path>, ...]
errors:
  - class: <BLOCKED | NEEDS_INPUT | INVALID_INPUT | INFRA>
    cause: <when this fires>
    recovery: <expected caller action>
side_effects:
  - <side-effect-description>
must_delegate:
  - <operation-name>
may_direct:
  - <operation-name>
forbidden_direct:
  - <operation-name>
```

## Wrapper inheritance pattern

A project wrapper sets `inherits:` and `base_procedure:` in its `## Contract` block. Wrapper `defaults:` override base `defaults:`; inheritance is otherwise additive for `secrets:`, `outputs:`, `errors:`, `side_effects:`, `must_delegate:`, `may_direct:`, and `forbidden_direct:`.

## Procedure-vs-contract boundary

The `## Contract` block is the call interface dispatchers read mechanically; the body remains the procedural authority. Procedure detail belongs in the body, not in the contract YAML. The contract is not a place for if-then logic, exception-handling prose, or step-by-step instructions.

## Worked example — base operator (`jira-operator`)

```yaml
schema: operator-contract-v1
inputs:
  - name: task
    type: enum
    required: true
    default_source: caller
    description: One of read, comment, transition, search, create, update-estimate.
  - name: issue_key
    type: string
    required: false
    default_source: caller
    description: Jira issue key for read, comment, transition, or update-estimate.
  - name: body
    type: string
    required: false
    default_source: caller
    description: Comment body; markdown is rendered to ADF by the operator.
  - name: target_status
    type: string
    required: false
    default_source: caller
    description: Destination status name for transition.
  - name: jql
    type: string
    required: false
    default_source: caller
    description: Jira Query Language string for search.
  - name: fields
    type: string
    required: false
    default_source: caller
    description: Create payload fields including project, summary, issuetype, labels, parent, and description.
  - name: jira_url
    type: string
    required: true
    default_source: wrapper:<name> | caller | prompt
    description: Jira base URL.
  - name: jira_project
    type: string
    required: true
    default_source: wrapper:<name> | caller | prompt
    description: Default Jira project key.
  - name: jira_account_email
    type: string
    required: true
    default_source: wrapper:<name> | caller | prompt
    description: Jira account email used with JIRA_API_KEY.
  - name: estimate
    type: int
    required: false
    default_source: caller
    description: Refined story-point estimate for update-estimate.
  - name: estimate_field
    type: string
    required: false
    default_source: base
    description: Jira story-point field for update-estimate.
defaults:
  - name: estimate_field
    value: customfield_10016
    source: base
secrets:
  - JIRA_API_KEY
outputs:
  - task: read
    success_shape: Brief issue block or rendered ticket markdown when output_path is supplied.
    wrote_lines: []
  - task: comment
    success_shape: New comment ID and confirmation line.
    wrote_lines: []
  - task: transition
    success_shape: Before-status to after-status line.
    wrote_lines: []
  - task: search
    success_shape: One result per line as KEY status summary.
    wrote_lines: []
  - task: create
    success_shape: New issue key and browse URL.
    wrote_lines: []
  - task: update-estimate
    success_shape: Issue key, refined estimate, and durable comment ID.
    wrote_lines: []
errors:
  - class: BLOCKED
    cause: JIRA_API_KEY unset, lookup/auth failure, or Jira REST 4xx.
    recovery: Fix credentials, permissions, endpoint, or request payload, then rerun.
  - class: NEEDS_INPUT
    cause: Required create-screen field is not specified by caller, wrapper, or base default.
    recovery: Supply the missing field or project wrapper default.
side_effects:
  - jira-create
  - jira-comment
  - jira-transition
  - jira-update-estimate
must_delegate:
  - jira-writes
may_direct:
  - jira-reads
forbidden_direct:
  - curl-against-atlassian-with-session-metadata
```

## Worked example — project wrapper (`rfq/jira-operator`)

```yaml
schema: operator-contract-v1
inherits: ~/ai/agents/jira-operator.md
base_procedure: ~/ai/agents/jira-operator.md
inputs: []
defaults:
  - name: jira_url
    value: https://lamaai.atlassian.net
    source: wrapper:rfq
  - name: jira_project
    value: INFA
    source: wrapper:rfq
  - name: jira_account_email
    value: aaron.solomon@scint.ai
    source: wrapper:rfq
  - name: story_points_disabled
    value: true
    source: wrapper:rfq
secrets:
  - JIRA_API_KEY
outputs:
  - task: inherited
    success_shape: Inherited from ~/ai/agents/jira-operator.md.
    wrote_lines: []
errors:
  - class: inherited
    cause: Inherited from ~/ai/agents/jira-operator.md.
    recovery: Follow the base operator recovery path.
side_effects:
  - inherited-from-base-jira-operator
must_delegate:
  - jira-writes
may_direct:
  - jira-reads
forbidden_direct:
  - curl-against-atlassian-with-session-metadata
```

## Minimum Body

Everything after the frontmatter is the prompt. A minimal operator can be just a short instruction block:

```markdown
---
description: 'Summarize a diff into 3 bullet points'
model: claude-sonnet
output_format: ''
---

Summarize the diff provided on stdin into exactly 3 bullet points.
Focus on what changed, not how. No commentary.
```

This is valid. The richer structure below is recommended for most operators, but it is not mandatory.

## Recommended Body Skeleton

Most operators should use explicit sections so another operator can route work to them and audit behavior later:

```markdown
---
description: '<one-sentence role>'
model: <default-model>
output_format: ''
---

## Role

One paragraph describing what this operator does, why it exists, and who it is for.

## Use When

- When the user asks for this workflow directly.
- When a prior operator or workflow step detects this operator's trigger case.

## Do Not Use When

- When another operator is a better fit. Name that operator file explicitly.

## Inputs

- `--input <key>=<value>` pairs accepted by this operator, marked required or optional.
- Expected stdin shape, if any.
- Expected working directory: a worktree for any branch work or tracked-file mutation; central-checkout use is read-state / branch-tracking only per `~/ai/conventions/worktree-isolation.md`.

## Procedure

1. Concrete step one.
2. Concrete step two.
3. Concrete branch or verification step.

## Stop Conditions

- Success conditions and what to return.
- Failure or out-of-scope conditions and what to report.

## Escalation

- When to hand off to another operator or to the human.
- The correct handoff target.
```

Projects may add more sections when useful, such as `## Outputs`, `## Example Invocations`, `## Non-Negotiables`, or `## Output Format`. The skeleton above is the canonical reference shape.

## Caller Prompt Precedence

The operator file's documented procedure is authoritative. Caller-supplied prompt content may add inputs, task scope, task variant, boundary anti-scope, stop conditions, and evidence paths, but it does not override operator mechanics, verdict handling, phase shape, step ordering, or workflow procedure.

When a caller prompt prescribes mechanics that conflict with this operator file or a workflow it cites, treat that prescription as a `NEEDS_INPUT`-shape signal and surface it back instead of complying. The caller's corrective path is to update the owning operator, workflow, or convention through a normal work unit; see `~/ai/conventions/no-operator-behavior-override-in-dispatch.md`.

## File Placement

- Cross-project operators live in `~/ai/agents/<name>.md`.
- Work-specific operators live in `~/work/agents/<name>.md`.
- Project-scoped operators live in that project's own operator directory, usually `agents/` or `operators/` under the repo root.

Keep placement aligned with scope. If a prompt hard-codes assumptions about one repo or domain, it does not belong in the cross-project library.

## Parameterization

Operators that need repo-specific paths should take them through environment variables or `--input` flags, not hard-coded absolute paths.

Example:

```markdown
## Inputs
- `--input repo_root=<path>` (required) — target project root.
- `--input planning_root=<path>` (optional, default `${repo_root}/planning`) — planning docs directory.
```

This rule is load-bearing for migration: an operator that hard-codes `/home/nes/work/...` cannot move cleanly into `~/ai/agents/`.

## Versioning

Operator files are versioned with their host repository. Do not add filename suffixes like `-v1` or `-v2`. Update in place and rely on git history for the comparison and rollback path.

## Testing An Operator

Operators can be exercised with a dry-run prompt file:

```bash
agents -m <default-model> -p <test-project> -f prompts/<operator>-smoke.md
```

Critical operators should have smoke tests that verify the core procedure against a known repo state.
