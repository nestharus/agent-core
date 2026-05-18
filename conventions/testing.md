# Testing conventions

Every test, whether unit, integration, end-to-end, prototype, or production, is split into setup and contract: setup lives outside the test function and may change as the environment evolves, while the test body contains the action or actions and assertions that change only when the requirement changes.

## Setup lives outside the test

The test body contains only the action or actions being tested and the assertions that validate the behavioral constraints. Setup, including fixtures, seeded data, mocked services, environment preconditions, and harness wiring, lives outside the test function in framework-native lifecycle hooks, a separate function the test calls explicitly, or dedicated setup modules. Input values that are themselves the contract under test, such as boundary values being verified or specific payload shapes being validated, may stay inline; durable test state, service configuration, and environmental preconditions remain external.

## Setup must be swappable

Multiple setup variants for the same contract, such as different operating systems, real or mocked services, containerized or local execution, must be expressible by swapping fixtures or helpers without editing the test body. The test body stays unchanged across setup variants; only the fixture or harness layer changes.

## Cross-module setup is allowed

When setup is reused across many tests, it may live in its own module, such as test helpers, fixture libraries, setup directories, factories, builders, runner configuration, or project-standard equivalents. Each test imports or calls the setup surface; the test itself remains the contract. Project-local conventions may pin specific module paths.

## Declared test patterns

This section declares the test-pattern interface consumed by test-writing and Phase 6b dispatches. It operates in lockstep with the setup-externality, swappability, and cross-module setup sections above: the pattern records the contract-bearing shape of a test while setup remains external and replaceable.

### Unit-test shape

A unit-test pattern records the test body, the external setup surface it depends on, the assertion location, and behavior-oriented naming for the behavior under test. Setup, including fixtures, seeded data, mocked services, environment preconditions, and harness wiring, remains outside the test body; only contract input values that are themselves under test may stay inline.

### Characterization-test shape

A characterization-test pattern records a current-behavior capture for existing behavior: the behavior being characterized, the evidence source, the fixture source, the fixture application point, and the intended use as a Phase 3 contract input. This shape cites `~/ai/workflows/implementation-pipeline.md` § Phase 2.5 step 2.5.1 coverage-inventory behavior; it declares the schema for characterization evidence, not runtime test work for this convention change.

### Fixture catalog

A fixture catalog records framework lifecycle hooks, seeded data, factories, builders, service or dependency fakes and mocks, external-system harnesses, environment/configuration preconditions, reusable setup helper modules, runner configuration, and project-standard equivalents. Discovery sources are project-local convention docs, project `AGENTS.md`, existing fixture modules, and representative tests; incidental filesystem layout is evidence for project-local discovery, not the canonical schema itself.

### Fixture-module naming convention

Shared fixture modules live in framework-native or project-standard setup surfaces such as `conftest.py`, test helper modules, fixture libraries, setup directories, factories, builders, runner configuration, or project-local equivalents. Allowed project-local overrides are data supplied by the project, such as pinned module paths or naming rules.

### Runner command discovery

Runner commands are discovered from the project `AGENTS.md` test instructions or project-local runner docs. This convention does not hardcode a global runner command; inline command examples in consumers are examples or follow-up consolidation terrain, not canonical commands.

### Naming policy

The default naming policy is pytest `test_*.py` paths, such as `tests/test_foo.py`, and frontend `*.test.ts` or `*.spec.ts` files. Allowed project-local overrides are data supplied by the project. This policy declares default names; broader operational search heuristics may scan additional files without changing the canonical naming policy.

### WRITE-state eval citation

Declared test patterns may cite WRITE-state eval specifications as adjacent proof-contract inputs. For eval lifecycle and output shape, cite `~/ai/conventions/evals.md` § Lifecycle states plus the ACR-174 and ACR-175 eval output shape instead of redeclaring eval definitions, finding schemas, lifecycle states, or evidence-source stability here.

Downstream consumer revisions in `test-writer.md`, `coverage-auditor.md`, `test-audit-gate.md`, `coverage-expansion-operator.md`, `pr-review.md`, `build-prototype.md`, and `implementation-pipeline.md` are follow-up consolidation tickets outside this section's scope.

## Cross-references

- `~/ai/workflows/build-prototype.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/conventions/evals.md`
- `~/ai/conventions/code-quality.md` § Push-vs-pull system coupling
- `~/ai/agents/test-writer.md`
- `~/ai/agents/coverage-expansion-operator.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/agents/test-audit-gate.md`
- `~/ai/agents/coverage-auditor.md`
- ACR-132
- ACR-134
- ACR-135
