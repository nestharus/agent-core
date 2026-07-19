# ACR-279 agentsmd-curator missing-contract regression prompt

You are running the `agentsmd-curator` audit behavior for ACR-279 lint-promotion regression evidence.

Inputs:

- `mode=audit`
- `repo_root=/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures`
- `agents_md=/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures/AGENTS.md`
- `agents_dir=/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures`

Required behavior:

1. Read `/home/nes/ai/agents/agentsmd-curator.md` as the operator procedure and severity reference.
2. Audit the fixture AGENTS routing row and the fixture operator file.
3. Confirm `/home/nes/ai/worktrees/acr-279-operator-contract-rollout/evals/acr-279-lint-promotion-regression/fixtures/high-risk-operator-missing-contract.md` is high-risk because it references Jira credentials, ticket writes, branch topology, and worktrees.
4. Confirm the fixture operator has no exact `## Contract` heading.
5. Emit finding identifier `ACR279-CURATOR-MISSING-CONTRACT-BLOCKING` with blocking severity if the promoted ACR-279 rule is implemented.
6. Return a blocking aggregate signal if the expected finding fires.
