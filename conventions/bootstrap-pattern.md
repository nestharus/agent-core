# Project Bootstrap Pattern

## Purpose and Scope

This convention defines the lifecycle for converting a general operator into a project-specific wrapper. It tells a workflow when later WUs use that wrapper instead of the general operator, and when a wrapper is stale enough that the bootstrap cycle restarts through re-bootstrap.

Project-wrapper bootstrap is different from implementation-pipeline Phase 0 ticket bootstrap. Phase 0 ticket bootstrap prepares or normalizes ticket inputs for a Work Unit; project-wrapper bootstrap turns repeated project facts into a reusable operator wrapper.

## Adjacent Owner Documents

This convention is an integration point. It defers to these owner documents rather than restating their rules:

- `~/ai/AGENTS.md` owns the shared routing layer, the Project Setup Pattern, How Projects Extend This, and Per-Project Policy knobs.
- `~/ai/agents/operator-file-format.md` owns operator frontmatter, body shape, and file-placement rules.
- `~/ai/conventions/project-layout.md` owns the `~/projects/<name>/{trunk,planning,worktrees}/` layout and the single-repo versus multi-repo umbrella variants.
- `~/ai/conventions/gate-ownership.md` owns human versus model gate ownership.
- `~/ai/conventions/worktree-isolation.md` owns unconditional branch-work isolation and central-checkout read-state limits.
- `~/ai/conventions/workflow-routing.md` owns cue routing precedence and project-specific routing-table expectations.

## Lifecycle

### Open Path

The open path is the first-WU or re-bootstrap path. On the first WU touching a category for a project, or when a re-bootstrap trigger appears, the general operator in `~/ai/agents/<name>.md` is dispatched directly with the project's facts as inputs.

During the open path, the general operator may emit a wrapper or refresh a wrapper at `<project>/trunk/agents/<name>.md`. That thin wrapper captures stable project facts that would otherwise be rediscovered. This is the slower path because it pays for full project analysis before deciding whether a wrapper should exist.

### Closed Path

The closed path is the steady-state expectation. On subsequent WUs in the same category, the workflow should dispatch the project-specific wrapper directly when it is current.

The project-specific wrapper carries stable project facts, so the agent does not re-discover ticket fields, routing assumptions, commands, or artifact destinations that are already settled. This is the fast path because the wrapper narrows the operator to the known project shape.

### Re-Bootstrap Triggers

Re-bootstrap triggers are qualitative signs that the open path should run again. Examples include a project environment change such as a new linter, new ticket system, new code-quality convention, or new workflow alias index.

Re-bootstrap should also be considered when the shared base operator procedure in `~/ai/agents/<name>.md` materially changes, or when policy knobs in `AGENTS.md` change in a way that invalidates wrapper assumptions.

This convention does not mandate a freshness file, checksum, or commit marker. Category-specific WUs may choose their own refresh mechanism when they implement a concrete wrapper family.

## Applicable Categories

Ticketing applies when a project benefits from a ticket-operator wrapper around `~/ai/agents/linear-operator.md` or `~/ai/agents/jira-operator.md`; stable project facts might include team key, board id, label conventions, and parent-issue routing. For Linear wrappers, the team key is required, the optional project token may be a UUID or `slugId`, per-team labels are stable facts, and parent routing remains explicit rather than inferred.

Code quality applies when a quality wrapper can carry stable project facts such as audit commands, report locations, quality gates, and project-specific review conventions.

Linting applies when a lint-runner wrapper can carry stable linter facts such as the lint command, package manager, config path, and expected invocation directory.

Workflow aliases / routing apply when an alias wrapper or routing-table helper can carry stable alias names, routing-table location, workflow variants, and project-specific cue conventions.

These examples identify categories and stable facts only. They do not specify implementations.

## Wrapper Shape and Placement

Wrappers live at `<project>/trunk/agents/<name>.md` in the single-repo layout, or the equivalent project operator directory in the multi-repo umbrella described by `~/ai/conventions/project-layout.md`.

A wrapper carries frontmatter, an H1, a `Base procedure: ~/ai/agents/<name>.md` pointer, and project-specific defaults, examples, and overrides only. It does not re-inline the shared procedure.

The operator-file contract remains in `~/ai/agents/operator-file-format.md`. A Project wrappers subsection may be added by a future WU; that format expansion is out of scope here.

## Stale-Wrapper Signals

Stale-wrapper signals are qualitative, not mechanical. Re-bootstrap should be considered when the wrapper's `Base procedure:` pointer references a file whose procedure materially changed since the wrapper was authored.

Other signals include project-specific defaults that changed, policies changed in `<project>/trunk/AGENTS.md`, or a new shared subcommand or input that the wrapper does not propagate.

This convention does not prescribe an automated detection mechanism. A category-specific implementation may add checks later, but this pattern is usable without them.

## Gate Ownership

Gate ownership for bootstrap follows `~/ai/conventions/gate-ownership.md`. Routine wrapper creation or refresh from already-known project facts is model-owned because it is artifact generation within an approved scope.

If the open path discovers a new value, scope, or trade-off question, that question is user-owned and must surface as `NEEDS_INPUT` per `~/ai/conventions/agent-questions-and-session-graph.md`. The wrapper writer stops before taking action that depends on that answer.

## Worktree and Artifact Placement

Wrapper files are committed under `<project>/trunk/agents/` according to `~/ai/conventions/project-layout.md`. Planning notes, dispatch logs, and scratch artifacts stay in the project's planning tree, not in the product diff.

When agents write wrappers, follow `~/ai/conventions/worktree-isolation.md` and do branch work in a git worktree, regardless of concurrency.

## Non-Wrapper Outcomes

The open path may decide no wrapper is worth producing. That is legitimate when the category has only ad-hoc per-WU inputs or when the stable facts are too small to justify a project-specific operator.

In that case, facts stay in the project's `AGENTS.md` Per-Project Policy block or equivalent, and the general operator continues to be dispatched directly.

## Anti-Scope

This convention codifies the pattern only. It does not implement and does not specify implementations for ticketing, code quality, linting, workflow aliases, routing, or any other category.

It does not define a wrapper format beyond `~/ai/agents/operator-file-format.md`. It does not define a freshness marker, checksum, or registry; those are downstream category-specific concerns.

It does not enumerate per-project bootstrap state in `~/ai/AGENTS.md`. Migration of existing project wrappers, including RFQ, is out of scope.
