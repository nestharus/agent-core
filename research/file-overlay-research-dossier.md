# File overlay research dossier for NES-145

## 1. Problem

`~/ai` has a context-composition problem, not merely a file lookup problem. A normal agent session starts with the umbrella `AGENTS.md`, follows conventions such as workflow routing, git policy, gate ownership, project layout, bootstrap wrappers, and code quality, then adds an operator file, a project `AGENTS.md`, project-local wrappers, branch-local copies, and invocation-specific prompts. The problem map identifies the overlay path as umbrella `AGENTS.md` -> conventions -> operator overrides -> project `AGENTS.md` -> project local. That chain is intentionally modular, but the effective rule set is currently produced inside the agent's context window by reading several files and mentally reconciling defaults, overrides, and exceptions. Examples already exist: the umbrella says project files should reference shared routing and add only local overrides; project files such as RFQ opt into `tickets_first_variant: true`; the implementation-pipeline orchestrator declares default values such as `tickets_first_variant=false`; operator wrappers carry `Base procedure: ~/ai/agents/<name>.md` and then add local defaults; and some project files are standalone manuals rather than explicit shared-base overlays. When both a base default and a local override are visible, the model has to infer which wins while still spending context on the losing instruction. A materialized stitch is better than a runtime cognitive merge because it moves precedence and contradiction handling out of the model's working memory and into a deterministic, inspectable step before the agent begins the task.

The desired primitive should preserve the current shape of the workflow library: shared files stay shared, project-local policy stays local, and project wrappers remain thin. NES-145 should not flatten the source tree, delete the umbrella, or turn every prose file into a schema. The failure being addressed is that the reader sees the input graph, not the effective result. A future resolver should let the source graph remain modular while providing one resolved byte stream for the session: the effective instructions, with no unresolved contradiction surviving just because two source files were both included.

## 2. Use case for `~/ai`

For `~/ai`, the chosen approach needs to materialize one logical entry point into one byte stream. The practical target is something like "the effective `AGENTS.md` for project X, branch Y, role Z, and invocation W." The agent should consume that as a normal instruction document, without having to recursively read base files and then decide whether a project default supersedes an umbrella default. It is acceptable if the materialized output also links to source documents for deeper reading, but the first read should be the resolved view, not the full unmerged graph.

The resolver needs deterministic conflict and precedence semantics. Project-local overrides should win where the policy says they win, but hard base rules must remain hard when the conventions say local style rules do not replace them. "Project-local override wins" is not enough by itself; the resolver needs to know the difference between a replaceable default, an additive local rule, a narrowed anti-scope, a role-specific exception, and an unresolved contradiction that should fail the materialization or be surfaced explicitly.

The result must be debuggable. A human should be able to ask "where did this line come from?" and get a useful answer. That can be an inline source marker, a sidecar provenance manifest, an `explain` command, or a combination. Provenance matters because the point is not just shorter prompt context; it is reviewer trust. If the resolved view says tickets-first projects defer PR creation, a reviewer should be able to trace that to the shared git convention plus the project `tickets_first_variant: true` declaration.

The approach must coexist with structured project flags such as `ticket_system`, `linear_team_key`, `jira_url`, `skip_problem_map_gate`, `auto_merge_after_phase_9`, and `tickets_first_variant`. Those flags are already consumed by orchestrators as project-level opt-ins. The file-overlay primitive should not require restructuring all of them into prose overlays or hiding them inside generated Markdown. It should either preserve them as structured inputs or read them as structured metadata while rendering their consequences into the effective instruction stream.

The implementation direction should add no runtime dependency that the `agents` CLI does not already have, or it should keep new dependencies minimal and justified. A tool that requires `CAP_SYS_ADMIN`, a long-running daemon, FUSE mount permissions, a Node runtime in an otherwise Python workflow, or a new configuration language for every contributor is a poor default. The behavior should live in the repo so humans, CI, and future agents can reproduce it without per-machine kernel features. The primitive can use temporary files, generated files, or streamed output, but the resolution semantics must be portable and versioned with the workflow library.

## 3. Candidate landscape

### overlayfs

OverlayFS is the Linux kernel union filesystem that presents an upper directory over one or more lower directories, with whiteouts and copy-up behavior defining which path is visible. It is mature and heavily used in container ecosystems because it composes directory trees efficiently at the path level. For `~/ai`, the important limitation is that OverlayFS composes file visibility, not instruction semantics. It can make one `AGENTS.md` path visible, but it cannot decide whether `tickets_first_variant=false` was superseded, whether a local wrapper is additive or replacing, or why a line appeared in the effective output.

Concrete instances: Linux OverlayFS itself, documented by the Linux kernel; rootless overlay implementations such as `fuse-overlayfs`; and the broader union-filesystem pattern used by container storage layers. The canonical citations are the Linux kernel OverlayFS documentation and the `containers/fuse-overlayfs` source repository.

### Mount-namespace tricks

Mount namespaces and bind mounts can create a per-process filesystem view. A launcher can create a private namespace, bind a synthesized file over `AGENTS.md`, expose different project trees, or mount a temporary overlay at a path that ordinary file reads already use. This family is attractive when the consuming tool cannot accept an alternate path and must see a normal filesystem location. It is weak as a semantic solution because the namespace is only a delivery layer. Something still has to compute the synthesized file, detect conflicts, and explain provenance.

Concrete instances: Linux mount namespaces as described in `mount_namespaces(7)`; bind mounts inside a private namespace; libfuse filesystems that synthesize files in user space; and `fuse-overlayfs` as a rootless union filesystem. These are real tools, but they bring mount permissions, daemon lifecycle, cache invalidation, and Linux-specific behavior into a problem that can likely be solved by writing or streaming a generated Markdown document.

### In-memory virtual filesystems

In-memory virtual filesystems provide file-like hierarchies without touching disk. They are useful in tests, local simulations, and library code that wants a uniform filesystem abstraction. They do not naturally help an external agent or shell tool that reads real local files unless the whole reader is wired through that same virtual filesystem abstraction. For `~/ai`, this family is best viewed as test substrate for a future resolver, not as the agent-facing primitive.

Concrete instances: `pyfakefs`, which patches Python filesystem modules for tests; `fsspec` and its `memory://` filesystem; PyFilesystem2 `MemoryFS`; and Node `memfs`. These can stage generated content, test path resolution, and avoid temporary disk writes in unit tests. They do not remove the need for explicit source ordering, semantic merge policy, materialized Markdown, and provenance.

### Explicit merge tooling for layered configs

Explicit merge tooling treats the overlay problem as data transformation. Inputs are JSON, YAML, TOML, or another structured representation; a reducer applies ordered precedence rules and emits a result. This family is more relevant than filesystem overlays because `~/ai` already has structured knobs alongside prose. The risk is that generic merge tools rarely know the domain-specific semantics: some fields should append, some replace, some should fail if both sides set conflicting values, and some hard base rules should not be overridden at all.

Concrete instances: `jq` for JSON transforms; Mike Farah `yq` for YAML/JSON/TOML/HCL and its merge operator; `dasel` for querying and updating JSON, YAML, TOML, XML, and CSV; `dprint` as a formatting step after generated Markdown; Python `tomllib` from PEP 680 for parsing TOML policy blocks; and custom deterministic deep-merge code such as the nearby `/home/nes/projects/videos/tools/policy.py` precedent. The local videos loader is not an AGENTS resolver, but it demonstrates a viable pattern: human-readable Markdown containing TOML blocks, parsed and deep-merged by Python.

### Source-of-truth resolvers

A source-of-truth resolver is an explicit code path that knows the domain model, the ordered input graph, and the output shape. It does not pretend files magically overlay each other. It says: these files are source inputs; this precedence rule applies; this conflict policy applies; this output and this provenance manifest are derived artifacts. This is the strongest fit for `~/ai` because the problem is domain-specific. The resolver can keep source documents prose-first while progressively adding structured fields where deterministic semantics matter.

Concrete instances and analogies: the local `~/ai/tools/workflow_index` generator, which projects workflow Markdown frontmatter into deterministic `workflows/index.json` and supports `generate` and `check`; a future custom `AGENTS.md` resolver; Bazel-style content-addressed action and cache models; Git object identity as a model for content-addressed inputs; and SLSA provenance as a reference for separating artifact content from provenance metadata. Broader configuration systems also belong here as prior art: Helm values layering, Kubernetes Kustomize overlays, and the NixOS module system.

### Structured override formats

Structured override formats encode policy in parseable data, then optionally render it into Markdown. They are attractive because they make precedence, typing, validation, and conflict detection much easier than merging freeform prose. The cost is authoring discipline and migration: `~/ai` is currently Markdown-heavy, and a sudden switch to a new DSL would harm local maintainability. The best version of this family keeps Markdown as the agent-facing output while using structured fragments for the load-bearing policy knobs.

Concrete instances: YAML frontmatter, already used in workflow and operator files; JSON fragments per RFC 8259; TOML fenced blocks in Markdown, backed by TOML 1.0 and Python `tomllib`; CommonMark as the rendered Markdown output target; Jsonnet as an object-layering configuration language; CUE for schema and validation; Dhall for typed, total configuration expressions; and Nickel as an adjacent programmable configuration language. These tools show a spectrum from simple data fragments to full configuration languages. For `~/ai`, simple frontmatter or fenced TOML/YAML fragments fit better than a new language unless D2 discovers that typed composition must become the primary source format.

### Markdown preprocessors and template systems

Markdown preprocessors stitch prose by includes, variables, partials, and conditionals. They can produce one document quickly and feel natural for documentation-heavy systems. Their weakness is that they are often textual, not semantic. A template can include a project override after a base section, but it will not know that two policy statements contradict unless the inputs were structured and validated before rendering.

Concrete instances: Jinja templates and includes; mdBook preprocessors; Docusaurus Markdown/frontmatter transforms; and Markdoc, which adds structured tags and partials to Markdown. These are useful references for rendering and authoring ergonomics, but a pure template pipeline should not be the core resolver unless it is constrained by a semantic data model.

### Content-addressed materialization and wrapper delivery

Content-addressed materialization is not a separate merge semantics family; it is a lifecycle family for making generated outputs reproducible. The resolver hashes its declared inputs, emits a stitched artifact, and records provenance. A CLI or editor wrapper can then pass the resolved artifact to `agents` instead of passing raw unmerged files. This family matters because `~/ai` already uses agent-runner invocations, planning scratch directories, generated metadata, and review-by-artifact workflows.

Concrete instances: the local `workflow_index` generated-artifact pattern; Bazel remote caching as an action/cache prior; Git object addressing as a durable content identity model; and SLSA provenance as a machine-readable provenance precedent. The delivery hook could be an `agents` CLI preflight, a `~/ai/tools/file-overlay/ generate/check/explain` tool, or a wrapper that writes the resolved context bundle under a per-WU scratch directory.

### Worktree and branch-local overlays

Git worktrees are not a context resolver, but they are overlay-adjacent in `~/ai` because parallel-agent work is already isolated by worktree. Branch-local `AGENTS.md` copies exist under several projects. Worktrees answer "which branch-local files does this session see?" but not "how do base and project rules merge?" They should be treated as an input-selection mechanism: D2 must decide whether branch-local AGENTS files are authoritative overlays, snapshots, or ignored unless explicitly selected.

Concrete instances: `git worktree` itself; the `~/ai` worktree-isolation convention; and observed worktree-local `AGENTS.md` files under project worktrees. The canonical external citation is the Git worktree documentation.

## 4. Evaluation axes

The evaluation uses seven axes. The proposal named six; this dossier splits prior-art and local fit so the table does not hide the most important question.

Portability: Does the approach work on developer machines and CI without privileged setup, Linux-only assumptions, daemons, or hidden local state?

Agent-runtime ergonomics: Does the agent see one logical file or context bundle, or does it still need to compose at read time?

Conflict-detection semantics: Can the approach express ordered overrides, additive rules, non-overridable hard rules, and unresolved conflicts?

Materialization cost: How expensive is it to compute, cache, invalidate, and regenerate the stitched output?

Debuggability and provenance: Can a human trace a resolved instruction back to source files and understand why it won?

Prior-art weight: Is the family mature and battle-tested, or niche and experimental?

Match for `~/ai`: Does the family actually reduce cognitive contradiction for agents reading rules, while respecting the repo's prose-first conventions and structured project flags?

## 5. Per-candidate evaluation

| Family | Portability | Agent ergonomics | Conflict semantics | Cost | Provenance | Prior art | `~/ai` match |
|---|---|---|---|---|---|---|---|
| overlayfs | LOW overall | MEDIUM | LOW | LOW once mounted | LOW | HIGH | LOW |
| Mount namespaces / bind / FUSE | LOW to MEDIUM | HIGH once active | LOW | MEDIUM | LOW | HIGH | LOW |
| In-memory VFS | MEDIUM | LOW | LOW | LOW | LOW | MEDIUM | LOW as delivery, MEDIUM as tests |
| Explicit merge tooling | HIGH | MEDIUM | MEDIUM | LOW | MEDIUM | HIGH | MEDIUM |
| Source-of-truth resolver | HIGH | HIGH | HIGH | LOW to MEDIUM | HIGH | HIGH by analogy | HIGH |
| Structured override formats | HIGH | MEDIUM | HIGH | LOW | HIGH | HIGH | HIGH as substrate, MEDIUM as primary |
| Markdown preprocessors | HIGH | HIGH | LOW to MEDIUM | LOW | MEDIUM | HIGH | MEDIUM |
| Content-addressed materialization / wrapper | HIGH | HIGH | Depends on resolver | LOW to MEDIUM | HIGH | HIGH | HIGH as lifecycle |
| Worktree overlays | HIGH | MEDIUM | LOW | LOW | MEDIUM | HIGH | LOW as resolver |

OverlayFS is HIGH on maturity and efficient materialization for Linux directory trees, but LOW on portability for non-Linux developer environments and CI containers without mount capabilities such as `CAP_SYS_ADMIN`. It also fails the most important semantic axis. OverlayFS decides which path exists; it does not know whether a project-local `tickets_first_variant: true` supersedes a base default, whether a local section is additive, or whether an operator anti-scope has been narrowed by a manager role. It is a credible fallback only if D2 discovers that the delivery problem is "make an unmodified program read a normal path from a layered filesystem." For `~/ai`, that is not the main problem.

Mount namespaces, bind mounts, libfuse, and `fuse-overlayfs` improve agent ergonomics by letting the agent read a normal path. They lose on portability and operational simplicity. A private mount namespace is elegant in a Linux launcher but awkward in CI, on macOS, or in constrained sandboxes. FUSE adds a daemon lifecycle and mount permissions. These options are delivery wrappers around a semantic resolver, not substitutes for one. If the resolver can write or stream a file, a namespace is usually needless complexity.

In-memory virtual filesystems are useful engineering tools but poor user-facing primitives. `pyfakefs`, `MemoryFS`, `fsspec` `memory://`, and Node `memfs` are strongest when testing path behavior, staging generated content, or isolating a resolver's filesystem effects. They do not help a model session that receives normal local files through the agent runner unless the runner itself is rewritten to read from the same abstraction. They score LOW on agent-runtime ergonomics and provenance as a primary mechanism, but MEDIUM as a D2 testing aid.

Explicit merge tooling is better aligned with the actual problem. `jq`, `yq`, `dasel`, and Python parsers can merge structured inputs deterministically. This family is portable and cheap, and it can be prototyped quickly. It still needs a `~/ai`-specific policy layer. Generic deep merge usually means "last writer wins for scalar values and recursive merge for objects." That is too weak for AGENTS semantics, where some rules append, some replace, and some must fail on contradiction. The right lesson is to reuse structured reducers where they fit, not to outsource the domain model to a generic CLI.

Source-of-truth resolvers score best because they can model the real source graph. A custom resolver can understand that project `AGENTS.md` files may be inherited overlays or standalone manuals; that operator wrappers use `Base procedure`; that structured flags remain authoritative inputs; that hard conventions are non-overridable unless a higher-level convention says otherwise; and that emitted Markdown should be one logical agent-facing byte stream. The local `workflow_index` tool is the closest `~/ai` precedent: source Markdown remains authoritative, derived output is deterministic, and `check` can detect staleness. The difference is that AGENTS materialization needs richer provenance and conflict policy than a metadata index.

Structured override formats score HIGH on conflict detection and provenance when used for the load-bearing parts. YAML frontmatter, TOML fenced blocks, and JSON fragments are all portable and parseable. TOML has strong local appeal because Python 3.11+ ships `tomllib`, and the videos project already demonstrates Markdown plus TOML blocks plus deep merge. YAML frontmatter fits existing workflow and operator files but introduces dependency and schema discipline questions if PyYAML is the parser. Full languages such as Jsonnet, CUE, Dhall, and Nickel are powerful but likely too heavy for D2 unless the project decides that typed configuration must replace prose policy as the primary source. The best fit is structured fragments plus rendered Markdown, not a wholesale DSL migration.

Markdown preprocessors score HIGH on agent ergonomics because they naturally emit one document. They score LOW to MEDIUM on conflict semantics. Jinja, mdBook preprocessors, Docusaurus transforms, and Markdoc can include, parameterize, and render. They do not automatically detect policy conflicts. Markdoc is the most interesting of this family because it supports structured Markdown concepts, but adopting it would still require a policy model underneath. A preprocessor can be the renderer after resolution; it should not be the resolver by itself.

Content-addressed materialization and wrapper delivery score HIGH as the lifecycle layer paired with a resolver. Input hashing gives deterministic cache keys; a sidecar manifest can record input paths, content hashes, winning layers, replaced defaults, and unresolved conflicts; a `check` command can make drift reviewable; and an `explain` command can answer provenance questions. This is not enough alone because it does not define merge semantics, but it is the right operational shape for D2. It keeps behavior in the repo and avoids per-machine filesystem features.

Worktree overlays are necessary context but not a solution. Worktrees provide branch-local filesystem state and parallel-agent isolation. They can decide which `AGENTS.md` file is visible for a branch. They do not resolve the shared-base plus project-local instruction graph. A future resolver should take worktree path as an input and explicitly decide how to treat branch-local instructions, but worktrees should not be confused with semantic materialization.

## 6. Recommendation

Primary recommendation: NES-146 should implement a source-of-truth resolver with explicit ordered inputs, deterministic Markdown materialization, conflict/provenance reporting, and content-addressed lifecycle checks. The resolver should consume the existing source graph rather than requiring an immediate rewrite of every policy file. It should know about umbrella `AGENTS.md`, project `AGENTS.md`, conventions, operator wrappers with `Base procedure`, project-local wrapper overrides, branch-local selection, and structured project flags. It should emit one agent-facing Markdown byte stream plus provenance sufficient for a human to trace resolved instructions back to source.

This wins on the load-bearing axes for `~/ai`: conflict semantics, provenance, portability, and match to the problem shape. The current failure is not that files cannot be overlaid at the POSIX layer. It is that policy precedence is embedded in prose and partially structured declarations, and the model is asked to resolve that in context. A resolver can be conservative at first: declare inputs, materialize sections in a stable order, preserve source citations, support explicit replacement markers or structured flags for known overrides, and fail or warn on ambiguous contradictions. It can also mimic local generated-artifact discipline from `workflow_index`: source files remain authoritative; generated output is deterministic; `check` reports drift; and no runtime behavior changes unless an invocation chooses the generated context.

Implementation implications for NES-146, without prescribing the final API:

- Expected artifacts: a resolver, fixtures, generated or streamed Markdown output, and a provenance sidecar or `explain` surface.
- Expected integration points: `agents` CLI preflight, a `~/ai/tools/file-overlay/` command, or a wrapper that writes into per-WU scratch.
- Expected source model: ordered input graph with typed metadata for project flags and wrapper base procedures.
- Expected verification: golden-output fixtures for representative overlay chains and conflict cases, plus checks that provenance points to real source paths.
- Expected migration posture: run alongside the existing prose-based composition for at least one cycle unless D2 proves a clean replacement path.

Fallback recommendation: structured override fragments plus a renderer. If D2 determines that freeform Markdown cannot support reliable replacement and conflict detection, the fallback should shift the source of truth for load-bearing policy into typed fragments, probably YAML frontmatter or TOML fenced blocks, while rendering CommonMark for agent consumption. This would beat the primary if ambiguous prose conflicts dominate and the resolver cannot safely infer section semantics. It would also be better if future orchestrators need machine-readable policy more than humans need prose-local editing. The cost is migration and schema design, so it should be fallback rather than first step.

Rejected approaches:

- overlayfs loses on portability and semantic conflict detection. It solves path composition, not policy composition.
- Mount namespaces, bind mounts, and FUSE lose on operational complexity. They are delivery mechanisms that still need the resolver underneath.
- In-memory virtual filesystems lose as the primary because agents and shell tools read the real filesystem. Keep them for tests if useful.
- Generic explicit merge tooling loses as the whole solution because `~/ai` needs domain-specific precedence and provenance. Use it only as parser/reducer support.
- Pure Markdown preprocessors lose because includes and templates can generate one document while preserving contradictions.
- Full configuration languages such as Jsonnet, CUE, Dhall, and Nickel lose for now on authoring friction and dependency weight, despite strong semantics.
- Worktrees lose as a resolver because they isolate branch state, not base/project/operator policy precedence.

## 7. Open questions for D2

NES-146 must decide the exact API shape of the materializer: CLI subcommand, library function, pre-prompt hook in the `agents` runner, or a combination. A CLI modeled on `workflow_index` is attractive, but a preflight hook may be needed if every operator invocation should consume the resolved view automatically.

NES-146 must decide whether the materialized output is a cached file on disk, a committed generated artifact, a scratch artifact, or a streamed read. A committed file improves reviewability but can drift. A scratch file avoids repo noise but needs a reproducible command and stable logs. A stream keeps state small but weakens post-run inspection unless provenance is persisted.

NES-146 must decide how to express override schema. Options include YAML frontmatter, TOML fenced blocks, JSON fragments, structured patch files, section-level markers in Markdown, or a hybrid. The schema must represent replace, append, narrow, hard-rule, and conflict behaviors without making common authoring painful.

NES-146 must decide how agents ask for "effective `AGENTS.md` for context X." A single canonical path is simple. A context-keyed lookup is more precise for project, branch, role, and operator combinations. The wrong abstraction could either hide needed context or recreate the current cognitive merge under another name.

NES-146 must decide test strategy. Golden-output fixtures with `(base, override) -> expected` triples are necessary for reviewer trust. Property tests for merge associativity, idempotence, and provenance completeness may be useful once the merge model is structured enough. Tests should include inherited projects, standalone projects, operator wrappers, branch-local files, and structured flags such as `tickets_first_variant`.

NES-146 must decide migration behavior. The safest path is to ship alongside existing prose-based composition for one cycle, compare generated output against current human expectations, and only then replace prompts that currently tell agents to read several files. Immediate replacement is only appropriate if D2 keeps the first version very narrow.

NES-146 must decide how far beyond `AGENTS.md` the resolver reaches. The problem map shows conventions, workflows, operators, and project wrappers participate in effective instructions. A narrow resolver for the entry-point AGENTS chain is easier to ship; a broader resolver is more valuable but risks scope growth.

NES-146 must decide how strict conflict handling should be. A first version might warn on unresolved prose conflicts and fail only on structured contradictions. A stricter version might require explicit resolution markers for any section that overrides a base instruction. The right answer depends on how much policy moves into structured fragments.

NES-146 must decide whether provenance is inline, sidecar, command-driven, or all three. Inline comments help the agent and reviewer while reading the materialized Markdown. A sidecar manifest is better for tooling. An `explain` command is better for targeted questions.

NES-146 must decide whether branch-local `AGENTS.md` copies are authoritative overlays, snapshots, or ignored unless explicitly selected. This matters because `~/ai` already uses worktree isolation heavily, and branch-local policy can be either intentional or stale.

### Research limits

This dossier surveys the candidate families named in NES-145 and the obvious adjacent families surfaced by the problem map and hookpoints research. It is not an exhaustive history of union filesystems, virtual filesystems, Markdown processors, or configuration-management systems. It also does not implement or prescribe the final D2 API. The recommendation is intentionally about direction: explicit resolver first, structured fragments as fallback, filesystem overlays only as delivery mechanisms if a later constraint requires them.

## 8. References

- Linux kernel documentation, "Overlay Filesystem": https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html
- Michael Kerrisk, `mount_namespaces(7)`: https://man7.org/linux/man-pages/man7/mount_namespaces.7.html
- libfuse source repository: https://github.com/libfuse/libfuse
- `containers/fuse-overlayfs` source repository: https://github.com/containers/fuse-overlayfs
- `pyfakefs` project page: https://pypi.org/project/pyfakefs/
- `fsspec` source repository: https://github.com/fsspec/filesystem_spec
- PyFilesystem2 `MemoryFS` documentation: https://pyfilesystem2.readthedocs.io/en/v2.4.13/reference/memoryfs.html
- Node `memfs` source repository: https://github.com/streamich/memfs
- `jq` manual: https://jqlang.github.io/jq/manual/
- Mike Farah `yq` source repository: https://github.com/mikefarah/yq
- `yq` multiply/merge operator documentation: https://mikefarah.gitbook.io/yq/operators/multiply-merge
- `dasel` source repository: https://github.com/TomWright/dasel
- `dprint` project page: https://dprint.dev/
- `dprint` Markdown plugin documentation: https://dprint.dev/plugins/markdown
- PEP 680, `tomllib`: https://peps.python.org/pep-0680/
- Python `tomllib` documentation: https://docs.python.org/3/library/tomllib.html
- YAML 1.2.2 specification: https://yaml.org/spec/1.2.2/
- RFC 8259, The JavaScript Object Notation Data Interchange Format: https://www.rfc-editor.org/rfc/rfc8259
- TOML v1.0.0 specification: https://toml.io/en/v1.0.0
- CommonMark specification: https://spec.commonmark.org/
- Jsonnet language reference: https://jsonnet.org/ref/language.html
- CUE documentation: https://cue.dev/docs/official-modules/
- Dhall safety guarantees: https://docs.dhall-lang.org/discussions/Safety-guarantees.html
- Nickel documentation: https://nickel-lang.org/
- Jinja template documentation: https://jinja.palletsprojects.com/en/latest/templates/
- mdBook preprocessor documentation: https://rust-lang.github.io/mdBook/for_developers/preprocessors.html
- Docusaurus Markdown features: https://docusaurus.io/docs/markdown-features
- Markdoc documentation: https://markdoc.dev/docs
- NixOS manual: https://nixos.org/nixos/manual/index.html
- Helm values files documentation: https://helm.sh/docs/chart_template_guide/values_files/
- Kubernetes Kustomize documentation: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/
- etcd Watch API documentation: https://etcd.io/docs/v3.7/learning/api/
- Bazel remote caching documentation: https://bazel.build/remote/caching
- Git book, "Git Internals - Git Objects": https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
- Git worktree documentation: https://git-scm.com/docs/git-worktree.html
- SLSA provenance specification: https://slsa.dev/spec/v1.0/provenance
- Local precedent: `tools/workflow_index/README.md`
- Local precedent: `tools/workflow_index/generator.py`
- External local precedent: `~/projects/videos/tools/policy.py` demonstrates the Markdown-plus-TOML deep-merge pattern.
