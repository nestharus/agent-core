# Project Layout — `~/projects/<name>/{trunk,planning,worktrees}/`

Projects organized for agent-driven workflows live under
`~/projects/<name>/` as an umbrella directory with three peer
sub-directories:

```
~/projects/<name>/
├── trunk/           # the git repository (project source)
├── planning/        # local-only planning artifacts (not committed)
└── worktrees/       # git worktrees per ~/ai/conventions/worktree-isolation.md
```

## What goes where

### `trunk/`
The git repository itself. Source code, committed docs (README,
DECISIONS, etc.), CI workflows, the project's own `AGENTS.md`,
all live here. `git clone` of the project produces this directory's
content; `cd ~/projects/<name>/trunk` is the working copy.

### `planning/`
Local research, proposals, risk reports, hookpoint research,
audit history, scratch logs from agent dispatches, and any
intermediate artifacts that the implementation pipeline (per
`~/ai/workflows/implementation-pipeline.md`) produces. **Not
committed** — `planning/` is gitignored at `trunk/.gitignore`.
Survives indefinitely as project memory; lives in user's home
directory, not on the remote.

### `worktrees/`
Git worktrees created for branch-work isolation per
`~/ai/conventions/worktree-isolation.md`; central checkout/trunk stays
read-state / branch-tracking only. Per-PR worktrees
(`worktrees/<branch>/`), CodeRabbit/risk-gate isolated checkouts,
etc. Listed in `trunk/.gitignore`'s `/worktrees/`. Often empty
between active workflows.

## Why three peers, not three subdirectories of `trunk/`

- **`planning/` outside `trunk/`** so plan content (which can be
  voluminous and noisy) doesn't pollute the committed tree. The
  remote stays focused on shippable artifacts.
- **`worktrees/` outside `trunk/`** so `git worktree` siblings
  don't sit inside the primary worktree (`git` rejects nested
  worktree creation; siblings sidestep that and keep `cd
  worktrees/<name>` predictable).
- **`trunk/` as the repository name** so `cd ~/projects/<name>/`
  drops into the umbrella, not into the working copy. This makes
  cross-cutting operations (`ls ~/projects/<name>/` to see all
  three peers, `du -sh ~/projects/<name>/*` to see their sizes)
  natural.

## Tooling implications

- Claude Code derives its project-memory directory from the cwd
  (`~/.claude*/projects/-home-nes-projects-<name>-trunk/`).
  Rename the memory directory if the project moves between
  layouts.
- CI workflows assume the repo's working directory is the
  current cwd of the worker; they don't reference any
  umbrella-level path.
- `git worktree add` typically takes absolute paths
  (per `feedback_worktree_paths.md` memory). With this layout,
  worktrees go to `~/projects/<name>/worktrees/<branch>/`.

## When to apply

- New projects under `~/projects/`: start with this layout.
- Existing projects with everything at `~/projects/<name>/`:
  migrate when the project has a planning workflow active OR
  when worktrees become a regular pattern. The migration is a
  filesystem operation: `mkdir trunk/`, move all current
  contents into `trunk/` except `planning/` and `worktrees/`,
  rename Claude Code's project-memory directory. One-time cost,
  reversible by `mv` back.

## Multi-repo umbrella variant

Some projects span multiple repositories that ship together (e.g. an
application repo plus an installation/packaging repo). For these,
`trunk/` becomes a container directory rather than the repo itself,
and worktrees live alongside each repo as named siblings:

```
~/projects/<name>/
├── trunk/
│   ├── <repo-1>/                 # full checkout of repo 1
│   ├── <repo-1>-worktrees/
│   │   └── <branch-name>/        # one git worktree per active branch
│   ├── <repo-2>/
│   └── <repo-2>-worktrees/
│       └── <branch-name>/
├── planning/
│   └── <branch-name>/            # planning artifacts keyed by branch
└── AGENTS.md
```

Differences from the single-repo layout:

- **`trunk/` is a directory, not a repo.** No `git` operations run
  against `~/projects/<name>/trunk/`; they run against
  `~/projects/<name>/trunk/<repo>/`.
- **Worktrees are nested under `trunk/` as siblings of each repo's
  checkout** (`trunk/<repo>-worktrees/<branch>/`), not at the umbrella
  level. This keeps each repo's worktrees co-located with its primary
  checkout — `git worktree list` from inside a repo lists only that
  repo's worktrees, which matches operator intuition.
- **`planning/` is keyed by branch name, not by repo.** A branch that
  spans both repos shares one `planning/<branch>/` directory.
  Most branches touch one repo, so this is structural rather than
  load-bearing — but cross-repo branches don't need a parallel planning
  tree per repo.
- **`AGENTS.md` lives at the umbrella root** (`~/projects/<name>/AGENTS.md`)
  rather than inside any one repo. Operator wrappers, project-local
  agent files, and routing tables also live at the umbrella level
  (typically `~/projects/<name>/agents/`) so they are not duplicated
  per repo and are not committed into any one repo.

Projects on this variant declare `multi_repo: true` (or equivalent)
in their `AGENTS.md` and list each repo + its origin URL in the
project preamble. Workflow operators that take a `repo_root` input
must be told which repo of the umbrella applies; in single-repo
projects the orchestrator can default `repo_root = ~/projects/<name>/trunk/`.

## Planning artifacts keyed by branch

For both variants, planning artifacts (problem maps, proposals, risk
reports, hookpoint research, contracts, audit history, dispatch
logs, question/answer artifacts) live under `planning/<branch>/` —
**not** inside the worktree. This is non-negotiable for projects on
the tickets-first review variant (`~/ai/workflows/tickets-first-review.md`)
because every file inside the worktree ends up in the eventual PR
diff; planning artifacts polluting that diff is a recurring failure
mode, not a one-off.

Operators that produce planning artifacts (orchestrator phases 0–5,
6a contract, 4 risk gates, etc.) must be supplied a `planning_dir`
input that points at `~/projects/<name>/planning/<branch>/`. They
write artifacts there, not under `${worktree_path}/research/`,
`${worktree_path}/proposals/`, etc.

Tests (Phase 6b) and product code (Phase 6c) **do** live inside the
worktree — that's the whole point of those phases. The test/code
boundary is also the planning-vs-product boundary.

## Anti-pattern

- Putting `planning/` under `trunk/planning/` and gitignoring it.
  This works mechanically but creates a confusing `trunk/`
  layout where some directories are tracked and some aren't, and
  trunk moves later become harder.
- Using `~/work/` or anonymous tmp dirs for planning. The
  `~/projects/<name>/` umbrella is the canonical home; planning
  outside it loses the project association.
- Writing planning artifacts under `${worktree_path}/research/`,
  `${worktree_path}/proposals/`, etc. They end up in the PR diff
  and have to be stripped via `git filter-repo` later. Operators
  must take `planning_dir` as input and write there.
