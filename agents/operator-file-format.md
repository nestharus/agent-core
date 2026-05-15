# Operator Prompt File Format

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

The contract is the three keys above. Preserve them exactly.

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
