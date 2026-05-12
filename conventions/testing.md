# Testing conventions

Every test, whether unit, integration, end-to-end, prototype, or production, is split into setup and contract: setup lives outside the test function and may change as the environment evolves, while the test body contains the action or actions and assertions that change only when the requirement changes.

## Setup lives outside the test

The test body contains only the action or actions being tested and the assertions that validate the behavioral constraints. Setup, including fixtures, seeded data, mocked services, environment preconditions, and harness wiring, lives outside the test function in framework-native lifecycle hooks, a separate function the test calls explicitly, or dedicated setup modules. Input values that are themselves the contract under test, such as boundary values being verified or specific payload shapes being validated, may stay inline; durable test state, service configuration, and environmental preconditions remain external.

## Setup must be swappable

Multiple setup variants for the same contract, such as different operating systems, real or mocked services, containerized or local execution, must be expressible by swapping fixtures or helpers without editing the test body. The test body stays unchanged across setup variants; only the fixture or harness layer changes.

## Cross-module setup is allowed

When setup is reused across many tests, it may live in its own module, such as test helpers, fixture libraries, setup directories, factories, builders, runner configuration, or project-standard equivalents. Each test imports or calls the setup surface; the test itself remains the contract. Project-local conventions may pin specific module paths.

## Cross-references

- `~/ai/workflows/build-prototype.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/agents/test-writer.md`
- `~/ai/agents/coverage-expansion-operator.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/agents/test-audit-gate.md`
- `~/ai/agents/coverage-auditor.md`
- ACR-132
- ACR-134
- ACR-135
