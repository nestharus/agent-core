# Connection Abstraction

This convention defines the shared `~/ai` vocabulary for service API and
CLI account access. It separates protocol shape, credential binding,
system reachability, project-facing scope, and the user's aggregate
Project context.

`Connection` is the umbrella term. The two concrete Connection shapes are
`System-conn` and `Project-conn`.

## Use When

Use this convention when describing how an operator, client, workflow, or
project wrapper reaches an external service API or CLI provider account and
needs to distinguish protocol, Auth, whole-system access, and scoped access.
It applies to ticket integrations, service clients, GitHub access, and
`agents`-launched CLI providers where account identity and project-facing
scope would otherwise be collapsed into one name.

Use it as vocabulary before designing storage, discovery, lookup, service
schemas, or CLI provider schemas. Those downstream designs should cite this
file rather than redefine the layers.

## Do Not Use When

Do not use this convention to rename ordinary workflow scope, git branch
scope, worktree location, planning artifacts, model-role selection, or
provider conversation sessions into connections. Those owning documents keep
their existing terms unless a service or CLI Project-conn genuinely targets
that space.

Do not treat this file as implementation authority. It names the model, not
a registry, resolver, config format, secret store, state machine, or runtime
contract.

## Layered Model

The layers are ordered from reusable protocol shape to user-facing aggregate
context:

1. `Client`
2. `Auth`
3. `System-conn`
4. `Project-conn`
5. `Project (user layer)`

### Client

`Client` is the stateless protocol, library, executable, or invocation
family that knows how to speak to a service or CLI provider class.

`Client` is NOT an auth holder, account selector, secret source, service
project, repository layout, scope bundle, or workflow policy.

Service example: the Linear GraphQL code under `clients/linear/` is the
current Linear Client family even though today's `LinearClient` object also
carries auth in implementation.

CLI example: the `claude` executable plus its basic invocation pattern is a
Client family for Claude CLI access; `codex` is a separate Client family for
Codex CLI access.

### Auth

`Auth` is one credential set or login binding usable with exactly one
Client family.

`Auth` is NOT credential storage, secret lookup, project scope, workspace
selection, model selection, or account discovery.

Service example: `LINEAR_API_KEY` is an Auth implementation/source form for
Linear, while `jira_account_email` plus `JIRA_API_KEY` is an Auth
implementation/source form for JIRA.

CLI example: an upstream OAuth login or credential file used by `claude2`
is Auth for that CLI account; the convention does not define where that
credential is stored or how it refreshes.

### System-Conn

`System-conn` is `Client + Auth`: credentialed reachability to a whole
external system, site, workspace, account, provider account, or public
endpoint family.

`System-conn` does not target a specific space such as a Linear team, JIRA
project, GitHub repository, branch, working directory, model alias, or
session id.

Service example: the Linear Client plus one `LINEAR_API_KEY` is a
System-conn that reaches the whole Linear workspace available to that key.

CLI example: the `claude3` executable/invocation family plus its upstream
login is a System-conn for that provider account before choosing a working
directory, model alias, or session id.

### Project-Conn

`Project-conn` is `System-conn + one project-facing scope shape` for that
service or CLI family.

`Project-conn` does NOT span multiple System-conns and is not a bundle of
labels, filters, views, workflow branch scope, or local worktree location.

Service example: Linear Project-conn = Linear System-conn + team key, with
optional project UUID or `slugId` as a Linear scope element when the
Linear-specific schema makes that part of the route. Labels remain filters
or conventions; they do not define connection identity.

CLI example: a `codex` Project-conn is the `codex` System-conn plus CLI
scope facts such as working directory, model alias, and optional session id;
the detailed field schema belongs to G6.

### Project (User Layer)

`Project (user layer)` is the user's aggregate working context governed by
one or more Project-conns plus optional service-owned labels, views,
filters, routing defaults, and wrapper facts.

`Project (user layer)` is NOT GitHub Projects, a Linear project, a JIRA
project, the `~/projects/<name>` umbrella directory, agent-runner
`--project`, a branch, or a worktree.

Service example: a user-facing project can combine a Linear team
Project-conn, a JIRA project Project-conn, and a GitHub repository
Project-conn without making any one Project-conn cross systems.

CLI example: a user-facing project can use multiple CLI Project-conns such
as `claude`, `claude2`, `claude3`, and `codex` accounts for the same work,
while still keeping provider account, model alias, and session id distinct.

## Cardinality

- One Client supports N System-conns.
- One System-conn has exactly 1 Auth.
- One Auth binds to exactly 1 Client.
- One System-conn supports N Project-conns.
- Each Project-conn has exactly 1 scope shape for its service or CLI family.
- Each Project-conn has exactly 1 System-conn parent.
- A Project-conn does NOT span multiple System-conns.
- A Project-conn is not automatically created by every issue id, branch,
  worktree, local path, label, filter, or workflow scope value.
- A user-facing Project that needs multiple systems is modeled as one
  Project governed by multiple Project-conns.
- When multiple systems participate in the same user-facing Project, the
  connection graph is still multiple Project-conns, never one multi-system
  Project-conn.

## Service-API Connections

This section maps current service examples to the shared vocabulary. It does
not specify per-service schemas, storage, discovery, or lookup.

Linear: Client = the GraphQL client family at `clients/linear/`. Auth =
`LINEAR_API_KEY`. System-conn = Client + key, reaching the whole Linear
workspace available to that key. Project-conn = System-conn + team key, with
optional project UUID or `slugId` only when a downstream Linear schema
chooses to include it as scope. Labels, views, and filters live on the
underlying Linear space or Project (user layer) metadata, not Project-conn
identity.

JIRA: Client = the JIRA REST/curl/API family. Auth = `jira_account_email`
plus `JIRA_API_KEY`. System-conn = Client + Auth + site/base URL, reaching
that JIRA site. Project-conn = System-conn + JIRA project key. Board,
transition, column, labels, and filters remain JIRA-specific behavior or
Project (user layer) metadata until a downstream schema names otherwise.

GitHub: Client = a future GitHub API client or `gh` CLI/API family. Auth =
the token or `gh` login binding for that Client. System-conn = Client +
Auth, reaching the GitHub account, organization set, or endpoint family
available to the credential. Project-conn = System-conn + repository scope
and, only when the service schema needs it, branch scope. `Project (user
layer)` is NOT GitHub Projects.

Issue IDs and resource targets are not automatically Project-conns. A JIRA
issue key, Linear issue id, GitHub issue number, PR number, branch name, or
file path is usually a resource target below or beside a Project-conn, not
the Project-conn itself.

Env vars such as `LINEAR_API_KEY` and `JIRA_API_KEY` are current Auth
implementation/source forms. The Auth concept is what this convention names;
Storage and lookup belong to G2 (NES-175).

## CLI Connections

This section maps named CLI provider accounts to the shared vocabulary. It
does not specify executable path tables, prompt mode, session capture,
quota scripts, refresh commands, storage, discovery, or lookup.

For CLI surfaces, agent-runner's `provider` remains agent-runner vocabulary.
A CLI Client+Auth+System-conn corresponds to what agent-runner today calls
a `provider`: for example, `claude2` is a System-conn under the `claude`
Client family with its own credential/Auth. The model alias is a
Project-conn scope element, not the System-conn identity.

`claude`: Client = the Claude CLI executable plus invocation pattern such
as `claude -p <cwd> -f <prompt>`. Auth = the Claude CLI login/credential
binding. System-conn = executable/invocation family + Auth, reaching the
provider account. Project-conn = System-conn + working directory, model
alias, and optional session id.

`claude2`: Client = the same Claude CLI family when it uses the same
executable/invocation shape. Auth = the second Claude account's credential
or login binding. System-conn = Claude Client + that Auth, matching the
agent-runner `provider` account named `claude2`. Project-conn = that
System-conn + working directory, model alias, and optional session id.

`claude3`: Client = the Claude CLI family. Auth = the third Claude
account's credential or login binding. System-conn = Claude Client + that
Auth, matching the agent-runner `provider` account named `claude3`.
Project-conn = that System-conn + working directory, model alias, and
optional session id.

`codex`: Client = the Codex CLI executable plus invocation pattern. Auth =
the Codex CLI login/credential binding. System-conn = Codex Client + Auth,
reaching the provider account. Project-conn = System-conn + working
directory, model alias, and optional session id.

The phrase "session id" is only a possible CLI Project-conn scope element
for resume/conversation targeting. It is not a synonym for Connection,
System-conn, or Project-conn, and it does not replace the session vocabulary
owned by adjacent session conventions.

Detailed CLI schema belongs to G6 (NES-187). G6 owns executable path,
prompt mode, session capture, quota, refresh, provider/model/session/cwd
field identity, and any agent-runner-specific renaming.
<!-- INTENTIONAL: This is schema-design ownership, not an operator runtime
sub-step; no orchestrator wiring belongs in this G1 vocabulary convention. -->

## Lifecycle Vocabulary

Implementations in G2..G6 should use these lifecycle words consistently.
This convention does not specify how any transition happens and does not
introduce a runtime state machine.

- `unbound` means the Client exists as a protocol/library/executable family,
  but no Auth has been attached.
- `bound` means Client + Auth exists and a System-conn has been instantiated.
- `scoped` means a System-conn has been combined with one scope shape and a
  Project-conn has been instantiated.
- `in-use` means an operator, workflow, client command, or CLI launch is
  currently using the Project-conn.
- `refreshing` means Auth is being refreshed, rotated, or re-established;
  examples include OAuth token rotation, env-var rotation, or upstream CLI
  login refresh.
- `revoked` means Auth is no longer valid; the System-conn and dependent
  Project-conns are unusable until Auth is re-bound.

Expiry, archive, deletion, and re-bind mechanics are downstream lifecycle
implementation concerns. The convention only names the states so tests and
contracts in G2..G6 can speak the same language.

## Anti-Scope

- No Connection class, registry, resolver, lookup, storage, secret store,
  migration, CLI flag, config schema, validator, runtime state machine,
  health check, refresh behavior, retry behavior, or executable mechanism is
  introduced here.
- No resolver/lookup/storage/secret-store/config-schema work is introduced
  by this convention.
- No refactor of `clients/linear/client.py`, `clients/linear/cli.py`, JIRA
  operator usage, implementation-pipeline ticket-system dispatch,
  agent-runner provider config, `AGENTS.md`, `README.md`, `models/roles.md`,
  workflow files, operator files, or H-group surfaces is part of this WU.
- No test scaffolding for future G2..G6 implementations is added here.
- No definition of Linear/JIRA/GitHub/agent-runner schemas belongs in this
  G1 convention.
- No project-layout/worktree/branch scope is part of Connection identity
  unless a service Project-conn genuinely targets a repository/branch, as
  a GitHub Project-conn may.
- Branch/worktree/local filesystem scope remains workflow or project-layout
  vocabulary unless a service Project-conn genuinely targets a
  repository/branch.
- Storage, discovery, and lookup belong to G2 (NES-175).
  <!-- INTENTIONAL: G2 defines connection persistence/discovery mechanics;
  this G1 convention does not introduce an operator procedural sub-step. -->
- Per-service schemas for Linear, JIRA, and GitHub belong to G3..G5.
  <!-- INTENTIONAL: G3..G5 define service-specific schema contracts;
  this G1 convention does not introduce orchestrator dispatch wiring. -->
- Detailed CLI schema belongs to G6 (NES-187).
  <!-- INTENTIONAL: G6 defines CLI provider schema details; this G1
  convention does not introduce runtime dispatch or enforcement wiring. -->

## Adjacent References

- [project-layout.md](project-layout.md) owns the project, trunk, planning,
  and worktree topology; Connection vocabulary does not redefine it.
- [bootstrap-pattern.md](bootstrap-pattern.md) owns project-specific wrapper
  lifecycle and stable wrapper facts; future wrappers may cite this
  convention for Client/Auth/System-conn/Project-conn vocabulary.
- [agent-questions-and-session-graph.md](agent-questions-and-session-graph.md)
  owns provider conversation session ID and session graph vocabulary;
  connection scope may mention `session id` only as a CLI Project-conn scope
  element.
- [wu-session-lifecycle.md](wu-session-lifecycle.md) owns WU session
  identity; Connection vocabulary does not redefine it.
- [../agents/linear-operator.md](../agents/linear-operator.md) can cite this
  convention in future work when describing current Linear Auth, System-conn,
  and Project-conn inputs.
- [../agents/jira-operator.md](../agents/jira-operator.md) can cite this
  convention in future work when describing current JIRA Auth, System-conn,
  and Project-conn inputs.
- [../models/roles.md](../models/roles.md) is informational only; model-role
  selection is not Connection identity.
