# Values — `~/ai/`

Architectural and design values for the `~/ai/` ecosystem.

## Small specialized tools form an ecosystem

`~/ai/` is an ecosystem of small specialized tools. Each tool focuses on doing **one** particular concern really well. This is the Unix philosophy applied at the workflow / agent / client layer.

Concrete implications:

- **Operators** (`~/ai/agents/`) do one operator-shaped thing. `coverage-analyzer` does coverage. `process-tree-auditor` audits process trees. They do not bundle unrelated capabilities.
- **Clients** (`~/ai/clients/`) wrap one external service each. `clients/linear/` talks to Linear. A future `clients/github/` will talk to GitHub. They do not multiplex services.
- **Tools** (`~/ai/tools/`) are small specialized utilities used by agents, scripts, or workflows. A future scheduler tool schedules tasks. A future PR-batch poller batches PR status queries. They do not grow into coordinators.
- **Workflows** (`~/ai/workflows/`) compose operators, clients, and tools into multi-step procedures. Workflows reach across concerns; the components they compose do not.
- **Conventions** (`~/ai/conventions/`) encode rules; they are not where capability lives.

Anti-patterns:

- An operator that does both research AND synthesis (split into two operators).
- A client that wraps two external services to "save a directory" (split into two clients).
- A tool that grows orchestration logic (lift the orchestration into a workflow; keep the tool simple).
- A workflow that grows utility functions (extract them into a tool).

When a tool / operator / client starts to grow, the question is "is this still one concern?" If two concerns are entangled, split before the entanglement compounds.

## Lean clients

Application-layer projects (e.g. `agent-runner`) are clients of the `~/ai/` ecosystem. They are lean: they consume the ecosystem's capabilities and contribute their own domain logic, but they do not host ecosystem-wide infrastructure (scheduling, polling, ticket integration, etc.). Ecosystem-wide infrastructure lives in `~/ai/`. Cross-cutting concerns belong in the ecosystem, not in any single project.

Example: a wake-up mechanism that polls GitHub for merged PRs is ecosystem-wide infrastructure (every project that uses the WU session lifecycle benefits from it). It belongs in `~/ai/tools/`. It does not belong in any single project's repository.

## Composition over flag-stuffing

When a tool grows new capabilities, prefer composing it with another small tool over adding flags. A scheduler that schedules tasks is one tool. A PR poller that queries GitHub is another tool. A workflow that "schedule-poll PRs hourly and wake the resumer per session" is the composition. Adding `--poll-prs --resume-sessions` flags to the scheduler entangles concerns; composition keeps each tool single-purpose.

## TODO sections are first-class

Skeletal docs and TODO sections in convention / workflow / tool files are part of the ecosystem's lifecycle. They are deliberately written even before the implementation lands so the architecture is pinned. When a TODO closes (a tool is built, a convention is fleshed out), the doc is updated; new TODOs may emerge from the closure. This is intentional: the ecosystem grows through deliberate skeletons that get filled in, not through bursts of unscoped activity.
