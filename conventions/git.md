# Git Conventions

## Branches

- All work happens on branches, never directly on `main`.
- All non-trivial work happens in a git worktree. See `~/ai/conventions/worktree-isolation.md`.
- The primary `main` checkout stays clean.

### Naming

Choose one naming scheme based on the project's tracker:

- **`feat/<short-description>`** is the default when there is no ticket system or when the project does not require ticket-linked branches.
- **`<TICKET-ID>-<short-description>`** is the variant for Linear or Jira work. Match the ticket ID casing exactly so the tracker auto-links.
- Keep branch names short enough to stay legible in the GitHub UI. Cap total length at about 50 characters.
- Use lowercase hyphenated descriptions after the prefix or ticket ID.

Examples:

- `feat/add-caching-layer`
- `ENG-4321-add-caching-layer`

### Topology for Multi-PR Initiatives

When one initiative ships as multiple stacked PRs, use explicit supporting branches:

- **`basis/<name>`** is a shared base branch when several child PRs depend on one common delta.
- **`integration/<name>`** is a temporary branch that merges multiple child PRs for cross-PR or end-to-end testing before any of them land on `main`.
- Child feature branches still use the normal naming schemes above.

Track the stack in the initiative's planning doc with a short table:

```markdown
| PR | Branch | Depends on | Merge order | Status |
|----|--------|------------|-------------|--------|
| #123 | feat/caching-repository | main | 1 | ready |
| #124 | feat/caching-service | #123 | 2 | draft |
| #125 | feat/caching-endpoint | #124 | 3 | draft |
| — | integration/caching-rollup | #123, #124, #125 | test only | testing |
```

- Merge order follows the dependency chain.
- If a branch depends on another PR, it stays stacked on that parent until the parent lands.

## Commits

- **GPG-sign every commit.** Configure signing globally:

```bash
git config --global user.signingkey <your-key-id>
git config --global commit.gpgsign true
```

- Store the signing key under `~/.gnupg/`.
- Use an RSA 4096-bit key unless the repository documents a different standard.
- Upload the public key to GitHub so signatures show as verified in the UI.
- **Prefer new commits over amends.** Amend only when the previous commit has not been pushed, or during the CodeRabbit loop described in `~/ai/workflows/coderabbit-loop.md`.
- Never amend a pushed commit outside that narrow loop.
- **No agent authorship attribution.** Agents do not add `Co-Authored-By:`, `Generated-By:`, "Claude wrote this", "Generated with ...", or similar trailers.
- The commit author is the human operator who ran the pipeline; agents are tools.
- Prefer small, testable commits. Each commit should build, pass tests, and represent one concern.

## Pull Requests

- Open PRs in draft mode first.
- **Draft PR creation is routine.** Opening a draft PR is a normal pipeline step and is not treated as a special approval-gated action.
- **Promotion is human.** Moving a draft PR to ready-for-review requires an explicit human decision.
- Keep one concern per PR. For multi-concern split rules, see `~/ai/workflows/pr-review.md`.
- A large deletion is its own PR unless the repo documents a stronger exception.
- Dependency order matters. If PR B depends on PR A, PR A merges first and PR B remains stacked until that happens.

## Public Visibility

When a repository's PR list is visible to a public audience beyond the internal team:

- Draft PRs still remain routine.
- Promoting a draft to ready-for-review is Tier-3.
- Opening a new non-draft PR is also Tier-3.
- See `~/ai/workflows/tiered-approval.md` for the approval model.

## Summary Rules

- Work on branches, not `main`.
- Use worktrees for non-trivial work.
- Keep `main` clean.
- Sign commits with GPG.
- Do not add agent authorship trailers.
- Use `feat/...` or exact-case ticket branches.
- Use `basis/...` and `integration/...` only when the branch topology needs them.
- Open draft PRs routinely; humans decide when review visibility changes.
